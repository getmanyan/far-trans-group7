# Does validation-aware retry repair grounded asset descriptions or only output validity?

Dilara Faritova — Group 7  
Repository: https://github.com/getmanyan/far-trans-group7  
Experiment commit: `2e4a253`

## Abstract

This individual Homework 3 study tests whether one validation-aware second LLM attempt can improve strict, source-grounded asset descriptions and thereby improve recommendations on FAR-Trans. The method uses the LLM as an Encoder: Qwen3-1.7B returns six as-of fields as strict JSON, a validator checks names and markets against source fields, and invalid responses fall back deterministically to source text. The ablation adds one retry to rejected responses, using the validator error, the rejected response, and the same six source fields. On the deterministic 100-user teaching sample (D100), replay reproduces the saved structured encoder. On the larger development cohort (DW; 10,404 warm users, 1,178 with future Buy), retry recovers 271 of 520 originally invalid asset responses (52.1%) and leaves 249 on fallback. However, the primary all-user B−A nDCG@10 difference is −0.0002879 with a 95% paired bootstrap interval [−0.0006272, +0.0000485] over 10,000 resamples (seed 20261120). The interval includes zero; retry improves output validity but does not establish an overall recommendation-quality gain.

## 1. Introduction

Group 7 asked when LLM-generated asset descriptions help FAR-Trans users, especially those with short histories. My individual question is narrower: after a strict grounded JSON encoder rejects an asset description, does one validation-aware retry reduce source-only fallback and improve future-purchase nDCG@10? This is a focused ablation that changes one component—the second attempt—while keeping the cohort, prompt family, candidate assets, labels, scorer, and model outputs frozen after protocol commit `d644f56` [4].

The primary DW difference is slightly negative, but its confidence interval includes zero. Retry substantially improves output validity without establishing either a recommendation-quality gain or a reliable degradation. The selected positive user case is a hand-checked outlier, not representative of the mean. I report development results only; the official final evaluation set was not available for this homework.

**Contributions.** I selected the research question, reviewed and approved the frozen protocol, supervised the D100 replay and DW experiment, interpreted paired bootstrap and failure-analysis results, and personally verified a paper claim, a data record and a user-level result. OpenCode assisted with implementation, tests, analytical computations and drafting; the verification worksheets and exported session document that assistance.

## 2. Related work

FAR-Trans is an investment dataset for financial asset recommendation with as-of metadata and future transaction labels [1]. The teaching setup uses a 1 June 2021 cutoff, a 30-day evaluation window, repeat purchases, binary nDCG@10, and required baselines.

LLM-Rec enriches item descriptions with prompting strategies and feeds enriched text into a recommendation module [2]. I personally checked Section 3 (“LLM-Rec”), printed page 585 of the ACL Anthology PDF: the paper describes four description-enrichment strategies—basic, recommendation-driven, engagement-guided and combined—and states that the enriched text is fed into the final recommendation module. My method is inspired by description transformation but does not reproduce LLM-Rec’s trained text encoder or MLP.

Qwen3 is an open-weight model family; this work uses `Qwen/Qwen3-1.7B`, revision `70d244cc86ccca08cf5af4e1e306ecf908b1ad5e` [3]. Team context: my Structured Encoder and retry ablation are separate from teammates’ paraphrase and alternative-representation runs; their numbers are not compared here as if they came from the same experiment.

## 3. Data, temporal protocol and evaluation

The eligible candidate universe contains 767 assets. D100 is the deterministic 100-user warm-start teaching sample; DW contains 10,404 warm users, of whom 1,178 have at least one future Buy in the 30-day window. Metadata must be strictly before the cutoff, and no user is selected using future purchases or observed scores before the run. All methods use the same users, cutoff, end date, eligible assets, labels and scorer. The frozen protocol hash stored in saved runs is `50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417`.

The primary metric is mean binary nDCG@10 across all evaluated users, counting users with no future purchases as zero. Mean nDCG@10 over nonempty-truth users is reported separately with its count. Measured metrics are shown to four decimals. The paired percentile bootstrap over users uses 10,000 draws with `random.Random(20261120)`, as specified in Protocol §6 and saved in `analysis_D100.json` and `analysis_DW.json`.

## 4. Method: Structured Encoder and validation-aware retry

Method A (`structured_encoder_v1`) asks the LLM, used as an Encoder, to return exactly six allowlisted as-of fields as a strict JSON object. A validator rejects extra fields, invalid JSON, unsupported names and unsupported markets. Accepted fields form a field-namespaced TF-IDF view for content-based retrieval; rejected assets use deterministic source-only fallback. No model is trained.

Method B (`structured_retry_once`) adds one retry for each rejected asset. The retry prompt contains only the validator error, the rejected response and the six source fields; it includes no ISIN, customer, price or future information. If the retry also fails validation, the source-only fallback remains. There were 520 originally invalid asset responses but only 480 unique retry prompts; shared retries are not treated as 520 independent samples.

The eight evaluated methods are Popularity, CBF, Latest buy, Latest buy or sell, Original-text CBF, All-fallback structured, A (Structured Encoder), and B (Structured + retry). The ablation is B versus A; the matched controls are All-fallback structured and Original-text CBF.

**Setup.** Inference used Apple MPS with `torch.float16`, greedy decoding (`do_sample=false`) and `PYTHONHASHSEED=0`. There was no training. Retry generation took 1,545.896 s; backend load plus run took 1,553.636 s; mean generation time was 3.221 s per call (median 3.151 s). Runnable code is in `run_hw3.py`, `retry_encoder.py`, `retry_prompt.py` and `analyze_hw3.py`.

## 5. Results: D100 reproduction and DW evaluation

The D100 replay reproduced the saved `metrics.json` and `per_user.json` files byte-for-byte. Separately, the ranked-ID comparison detected tie-order differences for seven users in the untouched official CBF baseline; other methods' ranked IDs matched. D100 B−A is −0.0018920 with interval [−0.0055565, 0.0000000] (0 improved, 2 worsened, 98 unchanged); D100 has only 11 nonempty-truth users, so it is continuity evidence, not primary evidence.

DW is the main development evaluation. A scores 0.0432 all-user nDCG@10 and B scores 0.0429. The primary paired B−A difference is −0.0002879, interval [−0.0006272, +0.0000485], with 56 improved, 115 worsened and 10,233 unchanged. The interval includes zero. On the predefined 1–3-history subgroup, B−A is +0.0000178, interval [−0.0002532, +0.0003034], labelled exploratory. Latest buy remains the strongest mean method on DW (0.0526).

| Method | D100 all | D100 nonempty | DW all | DW nonempty |
|---|---:|---:|---:|---:|
| Popularity | 0.0286 | 0.2599 | 0.0262 | 0.2312 |
| CBF (starter) | 0.0201 | 0.1827 | 0.0286 | 0.2526 |
| Latest buy | 0.0277 | 0.2520 | 0.0526 | 0.4648 |
| Latest buy or sell | 0.0271 | 0.2464 | 0.0509 | 0.4496 |
| Original-text CBF | 0.0235 | 0.2140 | 0.0420 | 0.3710 |
| All-fallback structured | 0.0292 | 0.2652 | 0.0423 | 0.3732 |
| A: structured encoder | 0.0398 | 0.3622 | 0.0432 | 0.3818 |
| B: structured + retry | 0.0379 | 0.3450 | 0.0429 | 0.3793 |

*Table 1. Absolute nDCG@10, rounded to four decimals from the saved `metrics.json` files. “all” counts empty truth as zero; D100 nonempty n=11, DW nonempty n=1178.*

Against All-fallback structured, A−C is +0.0009810 [+0.0003313, +0.0016433] and B−C is +0.0006932 [+0.0000471, +0.0013427]. Against Original-text CBF, A−D is +0.0012326 [+0.0005358, +0.0019492] and B−D is +0.0009447 [+0.0002472, +0.0016542]. Thus grounded structured views help relative to these controls, but the extra retry does not improve on A.

## 6. Failure and coverage analysis

Retry recovered 264/365 extra-field failures, 7/8 invalid-JSON failures, 0/89 unsupported-name failures, 0/56 unsupported-market failures and 0/2 name-length failures. Retry errors that remained include 167 unsupported-name, 65 unsupported-market, 14 name-length and 3 duplicate-term cases. Validity improved mainly for schema problems, not grounding problems.

Top-10 rankings changed for 7,445/10,404 users (mean overlap 0.9238). Repaired assets entered the top-10 for 5,263 users (6,224 entries), but only 108 recovered assets were exposed anywhere in history, truth or top-10, and there were no successfully grounding-repaired assets. High churn therefore does not imply a quality gain.

## 7. Individually verified examples

**C1.** I personally checked LLM-Rec Section 3, printed page 585, including the four prompting strategies and the statement that enriched text is fed into the final recommendation module [2]. My implementation does not reproduce its trained encoder/MLP.

**C2.** I personally checked FAR-Trans record `FI0009003305` (Sampo Oyj): metadata timestamp `2018-01-02` precedes `2021-06-01`; `sampoyj` is not a substring of `sampo oyj`, while `sampo` and `oyj` are. The saved validator error is unsupported name, and the retry audit still shows failure.

**HW3.** I personally verified user `59E9527FA16DB58874C8`, future Buy `GRS120003009`, A/B top-10 lists, arithmetic and eligibility on 2026-11-27. A nDCG@10 = 0.63092975, B = 1.00000000, B−A = +0.36907025. The eligible universe had 767 assets; the purchased asset and both lists passed eligibility, with ranks 2 (A) and 1 (B). This is a positive outlier. `GRS120003009` itself failed retry validation and was not repaired; its rank change was indirect.

## 8. Discussion and conclusion

In this run, retry fixed many schema/JSON errors but did not resolve any unsupported-name or unsupported-market errors; the second attempt repeatedly reproduced grounding failures. The primary interval includes zero, so the scientific conclusion is that retry improves output validity but does not establish an overall recommendation improvement. The positive hand-checked case must not be generalized.

Limitations: these are development results on teaching data; DW was visible to teammates; 9,226 DW users have empty truth; D100 has 11 nonempty users; prompt knowledge cutoff and feedback-versus-second-sample effects remain confounds; bootstrap and subgroup summaries were generated by the assistant, while C1/C2/HW3 were personally checked. Team decisions and unresolved issues: keep encoder variants separate, do not compare teammate runs, reserve the official final set, and report the inconclusive primary result.

## 9. Individual contribution and AI usage disclosure

I defined the research question, reviewed and approved the frozen protocol, initiated and inspected experiment runs, checked the reported outputs and interpretation, and independently verified the cited method, data record and user-level recommendation example. AI-assisted tools supported code implementation, testing, statistical analysis and report drafting. The accompanying genuine OpenCode JSONL export documents generated code, tool calls and tool results; it is not a reconstructed transcript.

## References

[1] Javier Sanz-Cruzado, Nikolaos Droukas, and Richard McCreadie. “FAR-Trans: An Investment Dataset for Financial Asset Recommendation.” IJCAI-2024 Workshop on Recommender Systems in Finance (Fin-RecSys), Jeju, 2024.

[2] Hanjia Lyu et al. “LLM-Rec: Personalized Recommendation via Prompting Large Language Models.” Findings of the Association for Computational Linguistics: NAACL 2024, pp. 583–612, 2024. https://aclanthology.org/2024.findings-naacl.39.pdf

[3] Qwen Team. “Qwen3 Technical Report.” arXiv:2505.09388, 2025. https://arxiv.org/abs/2505.09388

[4] Dilara Faritova. HW3 protocol and analysis artifacts, branch `dilara/hw3-retry-ablation`, experiment commit `2e4a253`, 2026. https://github.com/getmanyan/far-trans-group7
