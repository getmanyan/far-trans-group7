#!/usr/bin/env python3
"""Rule-based audit of all paraphrases against their source JSON (no LLM).

For each asset: (a) known source fields whose value words are all absent from the
paraphrase (omission); (b) a field the source knows but the paraphrase calls
'unknown <field>' (false unknown); (c) paraphrase that is a JSON copy, not a text.
  python paraphrase_audit.py outputs/DW
"""
import json, re, sys
from collections import Counter
from pathlib import Path

run = Path(sys.argv[1])
FIELDS = ('name', 'category', 'subcategory', 'sector', 'industry', 'market')
omit, false_unknown, json_copy, rows = Counter(), [], [], []
known_total = Counter()
for line in (run / 'paraphrases.jsonl').read_text(encoding='utf-8').splitlines():
    p = json.loads(line)
    src, gen = json.loads(p['source']), p['paraphrase']
    words = set(re.findall(r'\w+', gen.casefold()))
    if gen.strip().startswith('{'):
        json_copy.append(p['asset_id'])
    missing = []
    for f in FIELDS:
        v = src[f]
        if v == 'unknown':
            continue
        known_total[f] += 1
        toks = [t for t in re.findall(r'\w+', v.casefold()) if len(t) > 1]
        if toks and not any(t in words for t in toks):
            omit[f] += 1
            missing.append(f)
    # subcategory/market excluded: manual reading showed only false positives
    # ('other subcategory' is the value itself; 'listed on the XATH market').
    for f in ('category', 'sector', 'industry'):
        g = gen.casefold()
        m = re.search(r'unknown (\w+,? |\w+ and )*(and )?' + f + r'\b(.{0,30})', g)
        # A field word followed closely by its own known value (e.g. 'market XATH') is not a false unknown.
        if src[f] != 'unknown' and m and src[f].casefold() not in m.group(3):
            false_unknown.append({'asset_id': p['asset_id'], 'field': f, 'value': src[f], 'paraphrase': gen})
    rows.append({'asset_id': p['asset_id'], 'meta_state': p['meta_state'], 'omitted_fields': missing})
summary = {'assets': len(rows), 'known_field_counts': known_total, 'omitted_by_field': omit,
           'assets_with_any_omission': sum(bool(r['omitted_fields']) for r in rows),
           'false_unknown_cases': len(false_unknown),
           'false_unknown_assets': len({x['asset_id'] for x in false_unknown}),
           'false_unknown_by_field': Counter(x['field'] for x in false_unknown),
           'json_copy_outputs': json_copy}
(run / 'paraphrase_audit.json').write_text(json.dumps(
    {'summary': summary, 'false_unknown': false_unknown, 'per_asset': rows},
    ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
print(json.dumps(summary, ensure_ascii=False))
for x in false_unknown[:8]:
    print(x)
