# Final report outline — Dilara HW3 (structured retry ablation)

STATUS: **outline only; no PDF generated.** The formal HW3 assignment was verified at
`/Users/dafaritova/Downloads/homework3.md` and at the identical copy in
`/Users/dafaritova/Downloads/RecSys-LLMs-HW2-faritova/project/far-trans/instructions/homework3.md`
(SHA-256 `c6d9fa3cfc78e93088a400a0dc11c9186d4a22a5c47453d6b72bfd02390e4803`).
It requires an individual PDF of at most five pages excluding references plus an
AI-session export; required sections are Title, Abstract, Introduction, Related Work,
Method, Experiments, Discussion, AI Usage Disclosure and References. Measured metrics
must be shown to four decimal places. Include name, team, repository and experiment
commit; explain team decisions, unresolved issues, personal contributions/verification
and AI use.

Working title:

> Does validation-aware retry repair source-grounded asset descriptions and improve
> financial recommendations? A development ablation on FAR-Trans

## Page plan (max five pages excluding references)

1. **Abstract + I. Introduction** — 0.75 page
   - Team question: when do LLM-generated asset descriptions help FAR-Trans users,
     especially users with short histories?
   - My question: one extra validation-aware LLM attempt after strict JSON/grounding
     rejection: does it reduce fallback use and improve future-purchase nDCG@10?
   - State result early: 520 assets were originally rejected; 271 were successfully
     recovered and 249 remained on source-only fallback; primary DW B−A is small
     negative with CI including zero, so schema repair is not the same as recommendation
     improvement.
   - Contributions: frozen protocol before run; exact replay gate; full DW retry run;
     paired bootstrap and failure decomposition; personal verification notes.
2. **II. Related Work** — 0.5 page
   - LLM-Rec: four prompting strategies for description enrichment; enriched text fed
     into final recommendation module (personal C1 check, printed p. 585).
   - FAR-Trans, binary nDCG@10, baseline methods, Qwen3-1.7B.
   - Team context: my Structured Encoder vs Maria's paraphrase encoder and Anastasia's
     alternative representations; do not compare teammate numbers as if same run.
3. **III. Method** — 1 page
   - Six as-of fields, strict JSON arrays, validator rules, source-only fallback.
   - Retry prompt: exact validator error + rejected response + six source fields only;
     no ISIN, customer, price or future information.
   - Replay backend for method A; 520 failures -> 480 unique retry prompts -> 480 calls;
     shared retries are not 520 independent samples.
   - Cohorts: D100 reproduction and DW primary (10,404 warm users, 1,178 with future
     Buy), cutoff `2021-06-01`, window to `2021-07-01`.
   - Baselines: popularity, CBF, latest buy, latest buy or sell, original-text CBF,
     all-fallback structured, A = `structured_encoder_v1`, B = `structured_retry_once`.
   - Evaluation: binary nDCG@10, all-user and nonempty means, paired percentile bootstrap
     over users (10,000 draws, `random.Random(20261120)`), matching `PROTOCOL.md` §6,
     `analyze_hw3.py` and `outputs/analysis_DW.json` / `outputs/analysis_D100.json`.
   - Pre-registration: protocol commit `d644f56`; implementation Amendment 1 after
     freeze; no endpoint, cohort, prompt, scorer or model-output changes after freezing.
4. **IV. Experiments** — 2 pages
   - Setup: model revision `70d244cc...`, MPS float16, greedy, `PYTHONHASHSEED=0`;
     replay gate passed with byte-exact D100 metrics/per-user results.
   - Absolute results table (rounded in main text; exact values archived below).
   - Primary ablation: B−A all-user mean, CI, improved/worsened/unchanged counts.
   - Baseline comparisons and nonempty-truth subgroup; emphasize Latest buy remains
     strongest.
   - Failure analysis: recovery by original error, retry errors, 0 recovery for
     grounding errors, exposure of repaired assets.
   - Single audited case: user `59E9527FA16DB58874C8`; state explicitly that it is a
     positive outlier and not representative of the mean result. Dilara personally
     checked the arithmetic (`0.63092975` vs `1.00000000`, difference `+0.36907025`)
     and eligibility. Do not imply that `GRS120003009` was repaired: it failed retry
     validation and remained source-only fallback; its rank improved indirectly.
5. **V. Discussion + VI. AI Usage Disclosure + References** — 0.75 page
   - Interpretation: the retry fixes formatting/schema errors but not unsupported-name
     or unsupported-market grounding errors; top-10 churn does not translate into a
     convincing metric gain.
   - Limitations: development study, not official test; DW already seen by teammates;
     9,226 empty-truth users dilute all-user mean; D100 has only 11 nonempty users;
     prompt knowledge cutoff; feedback vs second-sample confound; bootstrap and subgroup
     results taken from assistant and not independently rederived by Dilara.
   - Individual contribution: my protocol, code, full run, analyses and verification
     notes; teammates' work kept separate.
   - AI disclosure: assistant wrote/checked code, prepared commands, ran analyses and
     drafted text; Dilara chose question, reviewed protocol, personally checked C1/C2,
     case inputs, arithmetic and eligibility results. State team decisions, unresolved
     issues and personal verification; AI-session export is still to be prepared.

## Exact absolute nDCG@10 table (archive; use 4 decimals in main text)

Values are copied from `outputs/D100_all/metrics.json` and
`outputs/DW_all/metrics.json`. `all` counts empty truth as 0. D100 nonempty `n=11`;
DW nonempty `n=1178`.

| Method | D100 all | D100 nonempty | DW all | DW nonempty |
|---|---:|---:|---:|---:|
| Popularity | 0.028590012799467636 | 0.25990920726788763 | 0.02617288807593327 | 0.23115681455179093 |
| CBF (starter) | 0.02010001173607857 | 0.18272737941889608 | 0.02860335990981631 | 0.25262254371963405 |
| Latest buy | 0.027722649787649066 | 0.2520240889786279 | 0.05263282198045581 | 0.464848794469153 |
| Latest buy or sell | 0.02710704869390403 | 0.24642771539912756 | 0.05091088560550386 | 0.4496407927331597 |
| Original-text CBF | 0.023542084151329593 | 0.21401894683026904 | 0.042002042936485295 | 0.3709586202981265 |
| All-fallback structured | 0.02917543961365267 | 0.26523126921502427 | 0.042253562959033215 | 0.37318002463988253 |
| A: structured encoder | 0.039838372363106195 | 0.36216702148278357 | 0.043234608302552144 | 0.3818445371644758 |
| B: structured + retry | 0.03794632780180478 | 0.34496661638004344 | 0.04294673770199183 | 0.3793020874800705 |

Verification for this outline: all eight rows above were re-read from the two saved
`metrics.json` files; bootstrap parameters were checked against `analyze_hw3.py`
(`SEED = 20261120`, `DRAWS = 10000`) and the saved `analysis_D100.json` /
`analysis_DW.json` (`seed = 20261120`, `draws = 10000`). No experiment was rerun.

## Key numbers to report

- Retry: 520 rejected assets, 480 unique prompts/calls, 271 recovered assets (52.1%),
  249 remaining fallbacks; prompt-level recovery 258/480 (53.8%).
- Recovery by error: 264/365 schema-extra-fields, 7/8 invalid JSON, 0/89 unsupported
  name, 0/56 unsupported market, 0/2 name length.
- Primary DW B−A: mean `−0.00028787060056029216`, 95% CI
  `[−0.0006271707328917344, +0.00004849145722758762]`; 56/115/10,233
  improved/worsened/unchanged.
- DW nonempty B−A: mean `−0.002542449684405161`, CI
  `[−0.005513570930865438, +0.00036876638393191477]`.
- Top-10 churn: 7,445/10,404 users changed, mean overlap `0.9238081507111828`;
  5,263 users had a repaired asset enter top-10 (6,224 entries).
- Only 108 recovered assets were exposed in history/truth/top-10; 0 grounding-repaired
  assets were exposed.
- Runtime: 1,545.896 s generation, 1,553.636 s including load; mean 3.221 s/call;
  median 3.151 s.

## Reproducibility artifacts

- Branch `dilara/hw3-retry-ablation`; protocol commit `d644f56`; Phase 2 `aa56f93`;
  Phase 3 analysis `2e4a253`.
- Frozen protocol hash in saved runs:
  `50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417`.
- Preflight: `outputs/phase3_preflight.json`, `outputs/verify_inputs_phase3.json`,
  `outputs/phase3_replay_check/`.
- Full retry evidence: `outputs/full_retry/` (prompts, responses, audit, views, cache,
  manifest, summary).
- Evaluation: `outputs/D100_all/`, `outputs/DW_all/`.
- Analysis: `outputs/analysis_D100.json`, `outputs/analysis_DW.json`,
  `results/phase3_summary.json`.
- Verification: `verification/C1_paper.md`, `verification/C2_data.md`,
  `verification/HW3_case.md`.
- Assignment verified: `/Users/dafaritova/Downloads/homework3.md`; PDF max five pages
  excluding references; native JSONL AI-session export accepted, or a documented
  derivative preserving generated code, tool calls and tool results; repository link
  does not replace either file.
- Still required: prepare the AI-session export/reproduction session and the final PDF.

## Submission checklist

- [x] Protocol frozen before experiment (`d644f56`) and implementation amendment recorded.
- [x] Preflight and D100 replay gate passed; evidence files saved.
- [x] Full retry run, cohort evaluation and paired bootstrap completed.
- [x] Exact nDCG@10 table archived; main-text table can be rounded to four decimals.
- [x] C1 paper check personally verified and recorded.
- [x] C2 FAR-Trans record/temporal check personally verified and recorded.
- [x] HW3 selected user, future Buy row and A/B Top-10 lists personally inspected.
- [x] HW3 nDCG@10 arithmetic personally verified: A `0.63092975`, B `1.00000000`,
      difference `+0.36907025`, matching saved values.
- [x] HW3 eligibility passed and personally reviewed: `GRS120003009` and both A/B Top-10
      lists are in the eligible universe; worksheet marked `VERIFIED`.
- [x] Formal HW3 assignment verified: max five pages excluding references, required
      sections and AI-session export instructions documented above.
- [ ] Prepare the AI-session export: native JSONL, or a documented derivative preserving
      generated code, tool calls and tool results; verify it reproduces all reported numbers.
- [ ] Draft the PDF in English using the outline above: at most five pages excluding
      references, Title/Abstract/Introduction/Related Work/Method/Experiments/Discussion/
      AI Usage Disclosure/References, and measured metrics to four decimals.
- [ ] Include name, team, repository and experiment commit (`2e4a253`); state what the
      team decided, what remains unresolved, Dilara's personal contributions/checks and
      how AI was used.
- [ ] Keep the positive single case explicitly labelled as non-representative and do not
      imply that `GRS120003009` was repaired.
- [ ] Final pass: no official-benchmark claim, no pushed/merge branch, no generated PDF
      until explicitly requested.
