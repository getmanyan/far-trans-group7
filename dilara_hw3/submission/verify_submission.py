import json
import re
from pathlib import Path


BASE = Path('/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw3')
SUB = BASE / 'submission'
source = (SUB / 'paper_source.md').read_text(encoding='utf-8')
source_plain = source.replace('`', '')
d100 = json.loads((BASE / 'outputs/D100_all/metrics.json').read_text())
dw = json.loads((BASE / 'outputs/DW_all/metrics.json').read_text())
analysis = json.loads((BASE / 'outputs/analysis_DW.json').read_text())
summary = json.loads((BASE / 'results/phase3_summary.json').read_text())
pdf_bytes = (SUB / 'Faritova_HW3_Final_Report.pdf').read_bytes()

rows = {
    'Popularity': 'Popularity',
    'CBF (starter)': 'CBF (starter)',
    'Latest buy': 'Latest buy',
    'Latest buy or sell': 'Latest buy or sell',
    'Original-text CBF': 'Original-text CBF',
    'All-fallback structured': 'All-fallback structured',
    'A: structured encoder': 'A: structured encoder',
    'B: structured + retry': 'B: structured + retry',
}
keys = {
    'Popularity': 'popularity',
    'CBF (starter)': 'cbf',
    'Latest buy': 'latest_buy',
    'Latest buy or sell': 'latest_buy_or_sell',
    'Original-text CBF': 'original_text_cbf',
    'All-fallback structured': 'all_fallback_structured',
    'A: structured encoder': 'structured_encoder_v1',
    'B: structured + retry': 'structured_retry_once',
}
for label, key in keys.items():
    cells = [f'{d100[key]["ndcg_at_10"]:.4f}', f'{d100[key]["ndcg_at_10_nonempty"]:.4f}',
             f'{dw[key]["ndcg_at_10"]:.4f}', f'{dw[key]["ndcg_at_10_nonempty"]:.4f}']
    line = next(l for l in source.splitlines() if l.startswith(f'| {label} |'))
    for cell in cells:
        assert cell in line, (label, cell, line)

required = [
    '767 assets', '10,404 warm users', '1,178', '520', '480 unique retry prompts',
    '271 of 520', '249', '−0.0002879', '−0.0006272', '+0.0000485', '10,000 draws',
    '20261120', '56 improved, 115 worsened and 10,233 unchanged',
    '0.63092975', '1.00000000', '+0.36907025', 'GRS120003009 itself failed retry validation',
    '10,000 resamples', '1,545.896 s', '1,553.636 s',
]
for item in required:
    assert item in source_plain, item

primary = analysis['bootstrap']['all_users:structured_retry_once_minus_structured_encoder_v1']
assert round(primary['mean'], 7) == -0.0002879
assert round(primary['ci_low'], 7) == -0.0006272
assert round(primary['ci_high'], 7) == 0.0000485
assert (primary['improved'], primary['worsened'], primary['unchanged']) == (56, 115, 10233)
assert analysis['seed'] == 20261120 and analysis['draws'] == 10000
assert summary['inference']['recovered_assets'] == 271
assert summary['inference']['remaining_fallback_assets'] == 249
assert summary['inference']['unique_retry_prompts'] == 480
assert len(re.findall(rb'/Type\s*/Page[^s]', pdf_bytes)) == 6

worksheets = ['C1_paper.md', 'C2_data.md', 'HW3_case.md']
for name in worksheets:
    text = (BASE / 'verification' / name).read_text(encoding='utf-8')
    assert 'PERSONALLY VERIFIED' in text or 'PERSONALLY VERIFIED BY DILARA' in text, name

print(json.dumps({
    'metric_rows_verified': len(rows),
    'verification_worksheets': worksheets,
    'pdf_pages': 6,
    'primary_b_minus_a': primary['mean'],
    'ci': [primary['ci_low'], primary['ci_high']],
    'bootstrap_seed_draws': [analysis['seed'], analysis['draws']],
    'status': 'all numeric checks passed',
}, indent=2))
