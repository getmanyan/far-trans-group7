# Group 7 — FAR-Trans team project (LLM4Rec, HSE University)

Team: Anastasia Getman (Гетман Анастасия), Maria Senenko (Сененко Мария),
Dilara Faritova (Фаритова Дилара).

Common task: for each evaluated customer, a Top-10 list of assets from the FAR-Trans dataset,
scored by nDCG@10 against the assets bought in the evaluation window. Track: **Encoder** — an
LLM turns each asset's as-of metadata into a representation used by a content-based recommender.

Joint question (Session 1): do LLM-derived asset representations improve nDCG@10 over the same
recommender on raw FAR-Trans metadata, in particular for customers with 1–3 past purchases?
After Session 2 we narrowed it to *under which conditions* such representations help.

## Where each member's work is

| Member | Session 2 (HW2) change | Location |
|---|---|---|
| Anastasia Getman | LLM attribute extraction into a closed vocabulary (asset class, sector, region, currency), with a rule-based no-LLM control | [`anastasia_hw2/`](anastasia_hw2/) on `main` |
| Dilara Faritova | Structured attributes copied from the source fields, with validation, fallback and a no-LLM control | branch [`dilara/hw2-structured-encoder`](https://github.com/getmanyan/far-trans-group7/tree/dilara/hw2-structured-encoder), folder `dilara_hw2/` (pull request #1) |
| Maria Senenko | Course LLM-Rec paraphrase encoder run and subgroup analysis | branch [`maria/hw2-paraphrase-encoder`](https://github.com/getmanyan/far-trans-group7/tree/maria/hw2-paraphrase-encoder) |

Each member submits an individual report and AI-session export; this repository holds the code.

## Common protocol for HW2

Course starter [`dryjins/RecSys-LLMs`](https://github.com/dryjins/RecSys-LLMs/tree/main/project)
defaults: deterministic sample of 100 warm users, cutoff 2021-06-01, 30-day window, repeat
purchases allowed, binary nDCG@10 with empty truth counted as zero; protocol hash prefix
`50efd4aeb415`. Model in all three runs: `Qwen/Qwen3-1.7B`, revision
`70d244cc86ccca08cf5af4e1e306ecf908b1ad5e`.

The dataset (FAR-Trans, University of Glasgow, CC BY 4.0) is not stored here:
<https://researchdata.gla.ac.uk/1658/>. No user-level outputs with customer IDs are committed.
