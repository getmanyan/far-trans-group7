#!/usr/bin/env python3
"""Independent re-implementation (pandas/numpy/scipy; imports no course code) of the
headline DW numbers: Popularity, Latest buy, original_text_cbf, llmrec_encoder and the
ablation. Written from the method descriptions in PROTOCOL.md, not by copying code.

  python independent_check.py DATA_DIR inputs/hw2_generations.jsonl outputs/DW/metrics.json
"""
import hashlib
import json
import math
import re
import sys
from collections import Counter

import numpy as np
import pandas as pd
from scipy import sparse

data, gen_log, metrics_path = sys.argv[1], sys.argv[2], sys.argv[3]
CUT, END = '2021-06-01', '2021-07-01'
MISSING = {'', 'Not_Available', 'nan'}

# --- assets as of cutoff with a positive price before cutoff ---
ai = pd.read_csv(f'{data}/asset_information.csv', dtype=str, keep_default_na=False)
ai = ai[ai.timestamp.str[:10] < CUT]
# Latest record before cutoff; among records with the same latest timestamp keep the first in file order.
ai = ai.sort_values('timestamp', kind='stable').drop_duplicates(['ISIN', 'timestamp'], keep='first')
ai = ai.groupby('ISIN').tail(1).set_index('ISIN')
cp = pd.read_csv(f'{data}/close_prices.csv', dtype={'ISIN': str, 'timestamp': str})
priced = set(cp[(cp.timestamp.str[:10] < CUT) & (cp.closePrice > 0)].ISIN)
ai = ai[ai.index.isin(priced)].sort_index()
isins = list(ai.index)
idx = {i: k for k, i in enumerate(isins)}

# --- transactions: drop exact duplicates and negative IDs ---
tx = pd.read_csv(f'{data}/transactions.csv', dtype=str, keep_default_na=False).drop_duplicates()
tx = tx[tx.transactionID.astype(int) >= 0]
tx = tx[tx.ISIN.isin(idx)]
day = tx.timestamp.str[:10]
buys = tx[tx.transactionType == 'Buy']
past = buys[buys.timestamp.str[:10] < CUT]
fut = buys[(buys.timestamp.str[:10] >= CUT) & (buys.timestamp.str[:10] < END)]
hist = past.groupby(['customerID', 'ISIN']).size()
truth = fut.groupby('customerID').ISIN.agg(set).to_dict()

# --- users: profile known before cutoff, at least one past buy; order by sha256('42:'+id) ---
ci = pd.read_csv(f'{data}/customer_information.csv', dtype=str, keep_default_na=False)
known = set(ci[ci.timestamp.str[:10] < CUT].customerID)
users = sorted((u for u in hist.index.get_level_values(0).unique() if u in known),
               key=lambda u: (hashlib.sha256(('42:' + u).encode()).hexdigest(), u))
print('users', len(users), 'assets', len(isins))

def ndcg(rank, t):
    if not t:
        return 0.0
    g = sum(1 / math.log2(k + 2) for k, i in enumerate(rank[:10]) if i in t)
    return g / sum(1 / math.log2(k + 2) for k in range(min(10, len(t))))

# --- documents and TF-IDF (raw counts x (1+ln((1+n)/(1+df))), L2) ---
def doc(r):
    f = {'name': r.assetName, 'category': r.assetCategory, 'subcategory': r.assetSubCategory,
         'sector': r.sector, 'industry': r.industry, 'market': r.marketID}
    return json.dumps({k: ('unknown' if v.strip() in MISSING else v.strip()) for k, v in f.items()},
                      sort_keys=True, ensure_ascii=False)
docs = [doc(r) for r in ai.itertuples()]
gen = {}
for line in open(gen_log, encoding='utf-8'):
    rec = json.loads(line)
    gen[rec['prompt'].split('\nSource: ', 1)[1]] = rec['response']['text'].strip()
gtexts = [gen[d] for d in docs]

def tfidf(texts, prefix):
    counts = [Counter(re.findall(r'\w+', t.casefold())) for t in texts]
    df = Counter(w for c in counts for w in c)
    n = len(texts)
    vocab = {w: k for k, w in enumerate(sorted(df))}
    rows, cols, vals = [], [], []
    for r, c in enumerate(counts):
        for w, x in c.items():
            rows.append(r); cols.append(vocab[w]); vals.append(x * (1 + math.log((1 + n) / (1 + df[w]))))
    m = sparse.csr_matrix((vals, (rows, cols)), shape=(n, len(vocab)))
    norms = np.sqrt(m.multiply(m).sum(1)).A1
    norms[norms == 0] = 1
    return sparse.diags(1 / norms) @ m

def l2rows(m):
    norms = np.sqrt(m.multiply(m).sum(1)).A1
    norms[norms == 0] = 1
    return sparse.diags(1 / norms) @ m

O = tfidf(docs, 'o')
G = tfidf(gtexts, 'g')
none_mask = np.array([all(str(v).strip().casefold() in ('', 'not_available', 'nan', 'unknown')
                          for v in (r.sector, r.industry)) for r in ai.itertuples()])
views = {'original_text_cbf': O.tocsr(),
         'llmrec_encoder': l2rows(sparse.hstack([O, G])).tocsr(),
         'llmrec_meta_none_only': l2rows(sparse.hstack([O, sparse.diags(none_mask.astype(float)) @ G])).tocsr()}

pop_users = past.groupby('ISIN').customerID.nunique().reindex(isins).fillna(0).values
pop_rank = sorted(isins, key=lambda i: (-pop_users[idx[i]], i))[:10]

# latest buy: most recent past Buy date per asset, newest first then ISIN, then popularity fill
last = past.assign(d=past.timestamp.str[:10]).groupby(['customerID', 'ISIN']).d.max()

res = {m: [] for m in ['popularity', 'latest_buy', *views]}
uidx = {u: k for k, u in enumerate(users)}
rows = [uidx[u] for u, _ in hist.index if u in uidx]
cols = [idx[i] for u, i in hist.index if u in uidx]
vals = [v for (u, _), v in hist.items() if u in uidx]
W = sparse.csr_matrix((vals, (rows, cols)), shape=(len(users), len(isins)))
for name, V in views.items():
    P = l2rows(W @ V)                      # normalised count-weighted profile
    S = (P @ V.T).toarray()                # cosine to every asset
    for k, u in enumerate(users):
        s = S[k]
        order = np.lexsort((np.array(isins), -np.round(s, 12)))[:10]
        res[name].append(ndcg([isins[j] for j in order], truth.get(u, set())))
for u in users:
    t = truth.get(u, set())
    res['popularity'].append(ndcg(pop_rank, t))
    lb = last.loc[u].sort_index()
    pref = sorted(lb.index, key=lambda i: (-pd.Timestamp(lb[i]).toordinal(), i))[:10]
    fill = [i for i in sorted(isins, key=lambda i: (-pop_users[idx[i]], i)) if i not in pref]
    res['latest_buy'].append(ndcg((pref + fill)[:10], t))

ref = json.load(open(metrics_path))
ne = [bool(truth.get(u)) for u in users]
print(f"{'method':24s} {'independent':>11s} {'course':>8s} {'indep_ne':>9s} {'course_ne':>9s}")
for m, v in res.items():
    a = sum(v) / len(v)
    b = sum(x for x, f in zip(v, ne) if f) / sum(ne)
    print(f"{m:24s} {a:11.6f} {ref[m]['ndcg_at_10']:8.6f} {b:9.6f} {ref[m]['ndcg_at_10_nonempty']:9.6f}"
          f"  {'MATCH' if abs(a - ref[m]['ndcg_at_10']) < 5e-7 else 'DIFF'}")
print('nonempty users', sum(ne))
import gzip
pu = {}
with gzip.open(metrics_path.replace('metrics.json', 'per_user.json.gz'), 'rt') as f:
    for r in json.load(f):
        pu[(r['method'], r['user_id'])] = r['ndcg_at_10']
diff_users = {m: sum(abs(v[k] - pu[(m, u)]) > 1e-9 for k, u in enumerate(users)) for m, v in res.items()}
gap = {m: sum(res[m]) / len(users) - sum(res['original_text_cbf']) / len(users)
       for m in ('llmrec_encoder', 'llmrec_meta_none_only')}
print('users whose nDCG differs from the course run (floating-point ties broken by ISIN here):', diff_users)
print('independent gap vs control:', {m: round(g, 6) for m, g in gap.items()})
