from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUT = Path('/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw3/submission')
QA = OUT / 'qa'
PDF = OUT / 'Faritova_HW3_Final_Report.pdf'
S = 3
PW, PH = 612, 792
W, H = PW * S, PH * S
M = 52
CW = PW - 2 * M
REG = '/System/Library/Fonts/Times.ttc'
BOLD = '/System/Library/Fonts/Times.ttc'
ITAL = '/System/Library/Fonts/Times.ttc'
BLACK = (18, 18, 18)
GREY = (92, 92, 92)
RULE = (205, 205, 205)
SHADE = (239, 239, 239)
FONT_CACHE = {}


def font(size, bold=False, italic=False):
    key = (size, bold, italic)
    if key not in FONT_CACHE:
        idx = 1 if bold else (2 if italic else 0)
        FONT_CACHE[key] = ImageFont.truetype(REG, int(size * S), index=idx)
    return FONT_CACHE[key]


def pt(v):
    return int(v * S)


def wrap(text, fnt, width):
    out = []
    for raw in text.split('\n'):
        words = raw.split()
        if not words:
            out.append('')
            continue
        line = ''
        for word in words:
            candidate = word if not line else f'{line} {word}'
            if draw.textlength(candidate, font=fnt) <= pt(width):
                line = candidate
            else:
                if line:
                    out.append(line)
                line = word
        if line:
            out.append(line)
    return out


def new_page(page_no, refs=False):
    global img, draw, y
    img = Image.new('RGB', (W, H), 'white')
    draw = ImageDraw.Draw(img)
    y = M
    if page_no > 1:
        head = 'References' if refs else 'Dilara Faritova -- HW3 validation-aware retry ablation'
        draw.text((pt(M), pt(32)), head, font=font(8, italic=True), fill=GREY)
        draw.line((pt(M), pt(42), pt(PW - M), pt(42)), fill=RULE, width=1)
        y = M + 8
    footer = 'References' if refs else f'{page_no} / 5'
    draw.text((pt(M), pt(PH - 34)), 'Development study -- not an official benchmark', font=font(7, italic=True), fill=GREY)
    draw.text((pt(PW - M - 42), pt(PH - 34)), footer, font=font(7), fill=GREY)
    return page_no


def emit(lines, size=9.2, leading=11.6, bold=False, italic=False, indent=0, gap=0):
    global y
    fnt = font(size, bold, italic)
    for line in lines:
        draw.text((pt(M + indent), pt(y)), line, font=fnt, fill=BLACK)
        y += leading
    y += gap


def para(text, **kw):
    emit(wrap(text, font(kw.get('size', 9.2), kw.get('bold', False), kw.get('italic', False)), CW - kw.get('indent', 0)), **kw)


def heading(text, number=None):
    global y
    y += 5
    label = f'{number}. {text}' if number else text
    draw.line((pt(M), pt(y + 10), pt(PW - M), pt(y + 10)), fill=RULE, width=1)
    draw.text((pt(M), pt(y)), label, font=font(10.6, bold=True), fill=BLACK)
    y += 18


def subheading(text):
    para(text, size=9.2, bold=True, gap=0)


def labeled(label, text):
    global y
    fnt_b = font(9.1, bold=True)
    fnt_r = font(9.1)
    lines = wrap(text, fnt_r, CW - 92)
    draw.text((pt(M), pt(y)), label, font=fnt_b, fill=BLACK)
    if lines:
        draw.text((pt(M + 92), pt(y)), lines[0], font=fnt_r, fill=BLACK)
        y += 11.4
        for line in lines[1:]:
            draw.text((pt(M + 92), pt(y)), line, font=fnt_r, fill=BLACK)
            y += 11.4
    else:
        y += 11.4
    y += 2


def table(headers, rows, widths, row_h=15.5):
    global y
    x0 = M
    fnt_h = font(7.5, bold=True)
    fnt_b = font(7.6)
    draw.rectangle((pt(x0), pt(y), pt(x0 + sum(widths)), pt(y + row_h)), fill=SHADE)
    x = x0
    for hdr, w in zip(headers, widths):
        draw.text((pt(x + 4), pt(y + 3)), hdr, font=fnt_h, fill=BLACK)
        x += w
    y += row_h
    draw.line((pt(x0), pt(y), pt(x0 + sum(widths)), pt(y)), fill=RULE, width=1)
    for i, row in enumerate(rows):
        if i % 2 == 1:
            draw.rectangle((pt(x0), pt(y), pt(x0 + sum(widths)), pt(y + row_h)), fill=(248, 248, 248))
        x = x0
        for cell, w, align in zip(row, widths, ['left'] + ['right'] * 4):
            text_w = draw.textlength(cell, font=fnt_b) / S
            tx = x + 4 if align == 'left' else x + w - 4 - text_w
            draw.text((pt(tx), pt(y + 3)), cell, font=fnt_b, fill=BLACK)
            x += w
        y += row_h
        draw.line((pt(x0), pt(y), pt(x0 + sum(widths)), pt(y)), fill=RULE, width=1)
    y += 5


pages = []
img = draw = y = None

new_page(1)
title = 'Does validation-aware retry repair grounded asset descriptions or only output validity?'
title_lines = wrap(title, font(15.2, bold=True), CW)
emit(title_lines, size=15.2, leading=18.4, bold=True, gap=5)
para('Dilara Faritova | Group 7 | https://github.com/getmanyan/far-trans-group7', size=9.4, italic=True, gap=1)
para('Experiment commit 2e4a253 | Individual Homework 3 submission', size=8.8, italic=True, gap=8)
heading('Abstract')
para('This individual Homework 3 study tests whether one validation-aware second LLM attempt can improve strict, source-grounded asset descriptions and thereby improve recommendations on FAR-Trans. The method uses the LLM as an Encoder: Qwen3-1.7B returns six as-of fields as strict JSON, a validator checks names and markets against source fields, and invalid responses fall back deterministically to source text. The ablation adds one retry to rejected responses, using the validator error, the rejected response, and the same six source fields. On the deterministic 100-user teaching sample (D100), replay reproduces the saved structured encoder. On the larger development cohort (DW; 10,404 warm users, 1,178 with future Buy), retry recovers 271 of 520 originally invalid asset responses (52.1%) and leaves 249 on fallback. However, the primary all-user B−A nDCG@10 difference is −0.0002879 with a 95% paired bootstrap interval [−0.0006272, +0.0000485] over 10,000 resamples (seed 20261120). The interval includes zero; retry improves output validity but does not establish an overall recommendation-quality gain.', size=9.0, leading=11.2, gap=5)
heading('Introduction', 1)
para('Group 7 asked when LLM-generated asset descriptions help FAR-Trans users, especially those with short histories. My individual question is narrower: after a strict grounded JSON encoder rejects an asset description, does one validation-aware retry reduce source-only fallback and improve future-purchase nDCG@10? This is a focused ablation that changes one component—the second attempt—while keeping the cohort, prompt family, candidate assets, labels, scorer, and model outputs frozen after protocol commit d644f56 [4].', size=9.0, leading=11.2)
para('The main result is deliberately inconclusive in the negative direction. Retry substantially improves output validity, but the primary DW recommendation metric is slightly negative and statistically inconclusive. The selected positive user case is a hand-checked outlier, not representative of the mean. I report development results only; the official final evaluation set was not available for this homework.', size=9.0, leading=11.2)
labeled('Contributions.', 'I froze the protocol before running the experiment, replayed D100 as a gate, ran the full DW retry experiment, performed paired bootstrap and failure analysis, and personally verified one paper claim, one data/temporal rule, and one complete user-level result. The AI assistant generated and checked code, commands and draft text; the verification worksheets and exported session distinguish these roles.')
heading('Related work', 2)
para('FAR-Trans is an investment dataset for financial asset recommendation with as-of metadata and future transaction labels [1]. The teaching setup uses a 1 June 2021 cutoff, a 30-day evaluation window, repeat purchases, binary nDCG@10, and required baselines.', size=9.0, leading=11.2)
para('LLM-Rec enriches item descriptions with prompting strategies and feeds enriched text into a recommendation module [2]. I personally checked Section 3 (“LLM-Rec”), printed page 585 of the ACL Anthology PDF: the paper describes four description-enrichment strategies—basic, recommendation-driven, engagement-guided and combined—and states that the enriched text is fed into the final recommendation module. My method is inspired by description transformation but does not reproduce LLM-Rec’s trained text encoder or MLP.', size=9.0, leading=11.2)
para('Qwen3 is an open-weight model family; this work uses Qwen/Qwen3-1.7B, revision 70d244cc86ccca08cf5af4e1e306ecf908b1ad5e [3]. Team context: my Structured Encoder and retry ablation are separate from teammates’ paraphrase and alternative-representation runs; their numbers are not compared here as if they came from the same experiment.', size=9.0, leading=11.2)
print('page1 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

new_page(2)
heading('Data, temporal protocol and evaluation', 3)
para('The eligible candidate universe contains 767 assets. D100 is the deterministic 100-user warm-start teaching sample; DW contains 10,404 warm users, of whom 1,178 have at least one future Buy in the 30-day window. Metadata must be strictly before the cutoff, and no user is selected using future purchases or observed scores before the run. All methods use the same users, cutoff, end date, eligible assets, labels and scorer. The frozen protocol hash stored in saved runs is 50efd4aeb415ba6f0c66dd0793a7c2033cdc32a42b86b58eebbca3e81eaf3417.', size=9.1, leading=11.5)
para('The primary metric is mean binary nDCG@10 across all evaluated users, counting users with no future purchases as zero. Mean nDCG@10 over nonempty-truth users is reported separately with its count. Measured metrics are shown to four decimals. The paired percentile bootstrap over users uses 10,000 draws with random.Random(20261120), as specified in Protocol §6 and saved in analysis_D100.json and analysis_DW.json.', size=9.1, leading=11.5)
heading('Method: Structured Encoder and validation-aware retry', 4)
para('Method A (structured_encoder_v1) asks the LLM, used as an Encoder, to return exactly six allowlisted as-of fields as a strict JSON object. A validator rejects extra fields, invalid JSON, unsupported names and unsupported markets. Accepted fields form a field-namespaced TF-IDF view for content-based retrieval; rejected assets use deterministic source-only fallback. No model is trained.', size=9.1, leading=11.5)
para('Method B (structured_retry_once) adds one retry for each rejected asset. The retry prompt contains only the validator error, the rejected response and the six source fields; it includes no ISIN, customer, price or future information. If the retry also fails validation, the source-only fallback remains. There were 520 originally invalid asset responses but only 480 unique retry prompts; shared retries are not treated as 520 independent samples.', size=9.1, leading=11.5)
para('The eight evaluated methods are Popularity, CBF, Latest buy, Latest buy or sell, Original-text CBF, All-fallback structured, A (Structured Encoder), and B (Structured + retry). The ablation is B versus A; the matched controls are All-fallback structured and Original-text CBF.', size=9.1, leading=11.5)
subheading('Setup.')
para('Inference used Apple MPS with torch.float16, greedy decoding (do_sample=false) and PYTHONHASHSEED=0. There was no training. Retry generation took 1,545.896 s; backend load plus run took 1,553.636 s; mean generation time was 3.221 s per call (median 3.151 s). Runnable code is in run_hw3.py, retry_encoder.py, retry_prompt.py and analyze_hw3.py.', size=9.1, leading=11.5)
print('page2 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

new_page(3)
heading('Results: D100 reproduction and DW evaluation', 5)
para('D100 replay reproduced the saved structured-encoder metrics and per-user results byte-for-byte, except for seven users whose official cbf baseline had an already-documented tie-order difference. D100 B−A is −0.0018920 with interval [−0.0055565, 0.0000000] (0 improved, 2 worsened, 98 unchanged); D100 has only 11 nonempty-truth users, so it is continuity evidence, not primary evidence.', size=9.0, leading=11.2)
para('DW is the main development evaluation. A scores 0.0432 all-user nDCG@10 and B scores 0.0429. The primary paired B−A difference is −0.0002879, interval [−0.0006272, +0.0000485], with 56 improved, 115 worsened and 10,233 unchanged. The interval includes zero. On the predefined 1–3-history subgroup, B−A is +0.0000178, interval [−0.0002532, +0.0003034], labelled exploratory. Latest buy remains the strongest mean method on DW (0.0526).', size=9.0, leading=11.2)
table(
    ['Method', 'D100 all', 'D100 nonempty', 'DW all', 'DW nonempty'],
    [
        ['Popularity', '0.0286', '0.2599', '0.0262', '0.2312'],
        ['CBF (starter)', '0.0201', '0.1827', '0.0286', '0.2526'],
        ['Latest buy', '0.0277', '0.2520', '0.0526', '0.4648'],
        ['Latest buy or sell', '0.0271', '0.2464', '0.0509', '0.4496'],
        ['Original-text CBF', '0.0235', '0.2140', '0.0420', '0.3710'],
        ['All-fallback structured', '0.0292', '0.2652', '0.0423', '0.3732'],
        ['A: structured encoder', '0.0398', '0.3622', '0.0432', '0.3818'],
        ['B: structured + retry', '0.0379', '0.3450', '0.0429', '0.3793'],
    ],
    [156, 78, 90, 78, 102],
)
para('Table 1. Absolute nDCG@10, rounded to four decimals from the saved metrics.json files. “all” counts empty truth as zero; D100 nonempty n=11, DW nonempty n=1178.', size=7.8, leading=9.6, italic=True, gap=3)
para('Against All-fallback structured, A−C is +0.0009810 [+0.0003313, +0.0016433] and B−C is +0.0006932 [+0.0000471, +0.0013427]. Against Original-text CBF, A−D is +0.0012326 [+0.0005358, +0.0019492] and B−D is +0.0009447 [+0.0002472, +0.0016542]. Thus grounded structured views help relative to these controls, but the extra retry does not improve on A.', size=9.0, leading=11.2)
print('page3 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

new_page(4)
heading('Failure and coverage analysis', 6)
para('Retry recovered 264/365 extra-field failures, 7/8 invalid-JSON failures, 0/89 unsupported-name failures, 0/56 unsupported-market failures and 0/2 name-length failures. Retry errors that remained include 167 unsupported-name, 65 unsupported-market, 14 name-length and 3 duplicate-term cases. Validity improved mainly for schema problems, not grounding problems.', size=9.1, leading=11.5)
para('Top-10 rankings changed for 7,445/10,404 users (mean overlap 0.9238). Repaired assets entered the top-10 for 5,263 users (6,224 entries), but only 108 recovered assets were exposed anywhere in history, truth or top-10, and no grounding-repaired asset was exposed. High churn therefore does not imply a quality gain.', size=9.1, leading=11.5)
heading('Individually verified examples', 7)
labeled('C1.', 'I personally checked LLM-Rec Section 3, printed page 585, including the four prompting strategies and the statement that enriched text is fed into the final recommendation module [2]. My implementation does not reproduce its trained encoder/MLP.')
labeled('C2.', 'I personally checked FAR-Trans record FI0009003305 (Sampo Oyj): metadata timestamp 2018-01-02 precedes 2021-06-01; sampoyj is not a substring of sampo oyj, while sampo and oyj are. The saved validator error is unsupported name, and the retry audit still shows failure.')
labeled('HW3.', 'I personally verified user 59E9527FA16DB58874C8, future Buy GRS120003009, A/B top-10 lists, arithmetic and eligibility on 2026-11-27. A nDCG@10 = 0.63092975, B = 1.00000000, B−A = +0.36907025. The eligible universe had 767 assets; the purchased asset and both lists passed eligibility, with ranks 2 (A) and 1 (B). This is a positive outlier. GRS120003009 itself failed retry validation and was not repaired; its rank change was indirect.')
print('page4 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

new_page(5)
heading('Discussion and conclusion', 8)
para('The retry fixes formatting/schema errors but cannot resolve unsupported names or markets because the second sample repeats the same grounding failure. The primary interval includes zero, so the scientific conclusion is that retry improves output validity but does not establish an overall recommendation improvement. The positive hand-checked case must not be generalized.', size=9.1, leading=11.5)
subheading('Limitations.')
para('These are development results on teaching data; DW was visible to teammates; 9,226 DW users have empty truth; D100 has 11 nonempty users; prompt knowledge cutoff and feedback-versus-second-sample effects remain confounds; bootstrap and subgroup summaries were generated by the assistant, while C1/C2/HW3 were personally checked.', size=9.1, leading=11.5)
subheading('Team decisions and unresolved issues.')
para('Keep encoder variants separate, do not compare teammate runs as one experiment, reserve the official final set, and report the inconclusive primary result.', size=9.1, leading=11.5)
heading('Individual contribution and AI usage disclosure', 9)
para('I personally chose the question, reviewed and froze the protocol, wrote and checked the implementation, ran and audited the experiment, executed the personal checks, and wrote the interpretation. The assistant generated and checked code, prepared commands, ran analyses and drafted text. A genuine OpenCode JSONL export preserving prompts, generated code, tool calls and tool results accompanies this report; no fictional transcript was substituted.', size=9.1, leading=11.5)
para('All eight absolute metrics were re-read from the saved metrics.json files; bootstrap parameters were checked against analyze_hw3.py and the saved analysis files. No Qwen inference was rerun during report preparation.', size=9.1, leading=11.5)
print('page5 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

new_page(6, refs=True)
draw.text((pt(M), pt(y)), 'References', font=font(12, bold=True), fill=BLACK)
y += 24
refs = [
    '[1] Javier Sanz-Cruzado, Nikolaos Droukas and Richard McCreadie. “FAR-Trans: An Investment Dataset for Financial Asset Recommendation.” IJCAI-2024 Workshop on Recommender Systems in Finance (Fin-RecSys), Jeju, 2024.',
    '[2] Chenyang Lyu et al. “LLM-Rec: Personalized Recommendation via Prompting Large Language Models.” Findings of the Association for Computational Linguistics: NAACL 2024, pp. 583–612, 2024. https://aclanthology.org/2024.findings-naacl.39.pdf',
    '[3] Qwen Team. “Qwen3 Technical Report.” arXiv:2505.09388, 2025. https://arxiv.org/abs/2505.09388',
    '[4] Dilara Faritova. HW3 protocol and analysis artifacts, branch dilara/hw3-retry-ablation, experiment commit 2e4a253, 2026. https://github.com/getmanyan/far-trans-group7',
]
for ref in refs:
    para(ref, size=9.0, leading=11.8, gap=8)
print('page6 y', round(y, 1))
assert y < PH - 45
pages.append(img.copy())

QA.mkdir(parents=True, exist_ok=True)
for i, page in enumerate(pages, 1):
    page.save(QA / f'page-{i}.png')
pages[0].save(PDF, save_all=True, append_images=pages[1:], resolution=216.0)
print('pdf', PDF)
print('pages', len(pages))
