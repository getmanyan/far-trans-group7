# C1 — manual verification of a cited paper method/result

STATUS: **PERSONALLY VERIFIED BY DILARA (reported 2026-11-27).**

Citation from my HW2 report (`report/report.md:165-166`):

> [2] Chenyang Lyu et al. LLM-Rec: Personalized Recommendation via Prompting Large
> Language Models. Findings of NAACL 2024. https://arxiv.org/abs/2307.15780

The final report should use the official ACL Anthology version/URL below; the arXiv
preprint is the same line of work but is not the version checked here.

## Task

Verify one specific method or result that my HW2/HW3 method is compared against. Target:
the LLM-Rec *description enrichment* method that motivates turning item metadata into
generated text used by a content-based recommender.

## Recorded observation

- PDF URL / version / date: `https://aclanthology.org/2024.findings-naacl.39.pdf`;
  Findings of the Association for Computational Linguistics: NAACL 2024, pp. 583–612,
  June 2024; accessed 2026-11-27. Downloaded PDF SHA-256:
  `1d7ba6b0717c1a6315c8af7a371cbf181c8e0623dc4e10a1afe0a269c357cebf`.
- Exact section number: **3 LLM-Rec**.
- Exact PDF page: **printed page 585**, **viewer page 3**.
- Verbatim sentences:

  > Specifically, our study focuses on investigating four distinct LLM prompting
  > strategies for description enrichment, namely basic prompting,
  > recommendation-driven prompting, engagement-guided prompting, and the combination
  > of recommendation-driven and engagement-guided prompting. The enriched text is then
  > fed into the final recommendation module.

- My own judgement of the difference: LLM-Rec enriches item descriptions with four
  prompt strategies and feeds the augmented text into a recommendation module; my
  Structured Encoder instead asks Qwen3-1.7B for six source-grounded fields as strict
  JSON, validates every non-unknown term against the as-of source fields, and uses a
  field-namespaced TF-IDF view with deterministic source-only fallback. I do not train
  a text encoder or MLP, and I do not reproduce LLM-Rec's trained recommendation module.
- Verdict on the HW2 claim "LLM-Rec motivates language-model transformations of item
  text, but this work does not reproduce its trained text encoder or MLP": **accurate**
  for the checked Section 3 passage.
- Executed by: **Dilara Faritova** (personally reported).
- Date: **2026-11-27**.

## Agent-prepared evidence (not the personal check)

Section number, printed page, quotation, PDF URL and file hash were independently
recovered from the ACL Anthology PDF/web index by the AI assistant. `pdftotext` was not
available and Python PDF libraries were not installed, so extraction confirmation came
from indexed ACL PDF text; Dilara's own reading is the personal verification recorded
above.
