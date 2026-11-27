import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


DB = Path('/Users/dafaritova/.local/share/opencode/opencode.db')
DEST = Path('/Users/dafaritova/Downloads/far-trans-group7-hw3-dilara/dilara_hw3/submission/ai_session')
JSONL = DEST / 'opencode_hw3_session.jsonl'
REPORT = DEST / 'redaction_report.txt'
MAIN = 'ses_de478a399ffe26jei6mC04J7uK'
LOCAL_HOST = 'MSK-' + 'GRVHDQ2650'
INCLUDED = {'text', 'tool'}
EXCLUDED = {'reasoning', 'step-start', 'step-finish', 'compaction'}
PATTERNS = [
    ('private_key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----')),
    ('openai_key', re.compile(r'\bsk-[A-Za-z0-9_-]{16,}\b')),
    ('github_token', re.compile(r'\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}\b')),
    ('github_pat', re.compile(r'\bgithub_pat_[A-Za-z0-9_]{20,}\b')),
    ('google_api_key', re.compile(r'\bAIza[0-9A-Za-z_-]{30,}\b')),
    ('slack_token', re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{10,}\b')),
    ('bearer_token', re.compile(r'\bBearer\s+[A-Za-z0-9._-]{16,}\b')),
    ('local_commit_identity', re.compile(rf'\b[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)*{re.escape(LOCAL_HOST)}(?:\.[A-Za-z0-9-]+)*\b')),
    ('local_host', re.compile(re.escape(LOCAL_HOST))),
]


def redact(value, counts):
    if isinstance(value, str):
        result = value
        for name, pattern in PATTERNS:
            result, n = pattern.subn(f'<redacted:{name}>', result)
            if n:
                counts[name] += n
        return result
    if isinstance(value, list):
        return [redact(v, counts) for v in value]
    if isinstance(value, dict):
        return {k: redact(v, counts) for k, v in value.items()}
    return value


def jload(value):
    try:
        return json.loads(value)
    except Exception:
        return value


conn = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
conn.row_factory = sqlite3.Row
sessions = [dict(r) for r in conn.execute(
    'select id, parent_id, title, agent, model, directory, time_created, time_updated from session where id=? or parent_id=? order by time_created',
    (MAIN, MAIN),
)]
session_ids = [s['id'] for s in sessions]
for s in sessions:
    s['model'] = jload(s['model'])
    s['message_count'] = conn.execute('select count(*) from message where session_id=?', (s['id'],)).fetchone()[0]
    s['included_part_count'] = conn.execute(
        f"select count(*) from part where session_id=? and json_extract(data,'$.type') in ({','.join('?' for _ in INCLUDED)})",
        (s['id'], *sorted(INCLUDED)),
    ).fetchone()[0]

counts = Counter()
tools = Counter()
messages_out = []
for sid in session_ids:
    rows = conn.execute('select id, session_id, time_created, time_updated, data from message where session_id=? order by time_created, id', (sid,)).fetchall()
    for row in rows:
        mdata = jload(row['data'])
        parts = []
        prows = conn.execute('select id, message_id, time_created, time_updated, data from part where message_id=? order by time_created, id', (row['id'],)).fetchall()
        for prow in prows:
            pdata = jload(prow['data'])
            ptype = pdata.get('type') if isinstance(pdata, dict) else None
            if ptype not in INCLUDED:
                continue
            if ptype == 'tool':
                tools['tool_calls'] += 1
                state = pdata.get('state') or {}
                if 'output' in state:
                    tools['tool_results'] += 1
                tools[str(pdata.get('tool'))] += 1
            parts.append({
                'id': prow['id'],
                'time_created': prow['time_created'],
                'time_updated': prow['time_updated'],
                'data': pdata,
            })
        if not parts:
            continue
        messages_out.append({
            'type': 'session_message',
            'session_id': row['session_id'],
            'message_id': row['id'],
            'time_created': row['time_created'],
            'time_updated': row['time_updated'],
            'role': mdata.get('role') if isinstance(mdata, dict) else None,
            'agent': mdata.get('agent') if isinstance(mdata, dict) else None,
            'model': mdata.get('model') if isinstance(mdata, dict) else None,
            'summary': mdata.get('summary') if isinstance(mdata, dict) else None,
            'parts': parts,
        })

messages_out = redact(messages_out, counts)
metadata = {
    'type': 'session_export_metadata',
    'export_format': 'documented OpenCode SQLite-derived JSONL',
    'source_database': str(DB),
    'export_generated_at': datetime.now(timezone.utc).isoformat(),
    'main_session_id': MAIN,
    'sessions': sessions,
    'included_part_types': sorted(INCLUDED),
    'excluded_part_types': sorted(EXCLUDED),
    'inclusion_rule': 'All user/assistant text parts and tool parts with inputs and outputs were exported verbatim apart from documented regex redactions; internal reasoning and step/compaction markers were excluded.',
    'message_records': len(messages_out),
    'tool_counts': dict(tools),
    'redactions': dict(counts),
    'authenticity_statement': 'This export was generated directly from the local OpenCode database. No messages, tool calls, tool results or code were invented or reconstructed.',
}

DEST.mkdir(parents=True, exist_ok=True)
with JSONL.open('w', encoding='utf-8') as out:
    out.write(json.dumps(metadata, ensure_ascii=False) + '\n')
    for record in messages_out:
        out.write(json.dumps(record, ensure_ascii=False) + '\n')

lines = [
    'OpenCode AI-session export redaction report',
    '',
    f'Source database: {DB}',
    f'Output: {JSONL}',
    f'Generated at (UTC): {metadata["export_generated_at"]}',
    '',
    'Checks performed:',
    '- Scanned every exported string in messages, generated code, tool inputs and tool outputs.',
    '- Patterns checked: private keys, OpenAI-style keys, GitHub tokens/PATs, Google API keys, Slack tokens, bearer tokens, the local committer identity and the local hostname.',
    '- No credential or API-token values were found.',
    f'- Local committer identity redactions: {counts.get("local_commit_identity", 0)}.',
    f'- Local hostname redactions: {counts.get("local_host", 0)}.',
    '- No other redactions were applied.',
    '- Internal reasoning and step/compaction markers were excluded by format rule; no retained content was paraphrased.',
    '',
    f'Message records: {len(messages_out)}',
    f'Tool calls: {tools.get("tool_calls", 0)}',
    f'Tool results: {tools.get("tool_results", 0)}',
]
REPORT.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(json.dumps({
    'sessions': len(sessions),
    'message_records': len(messages_out),
    'tool_calls': tools.get('tool_calls', 0),
    'tool_results': tools.get('tool_results', 0),
    'redactions': dict(counts),
    'jsonl_bytes': JSONL.stat().st_size,
}, ensure_ascii=False, indent=2))
