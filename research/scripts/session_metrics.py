"""Process metrics from Claude Code session logs (~/.claude/projects/<project>/<session>.jsonl).

usage: python3 session_metrics.py P1=<log.jsonl> P2=<log.jsonl> P3=<log.jsonl> > ../data/sessions.json

Time is measured from the first real user prompt to the last logged event. Output tokens are
summed once per assistant message id (logs repeat a message across streamed chunks).
"""
import json, re, sys, collections, datetime as dt

CAT = {'Write': 'write'}

def classify(name, inp):
    if name == 'Read' and re.search(r'\.(png|jpe?g)$', inp.get('file_path', ''), re.I):
        return 'review'                      # the agent looked at its own rendered frames
    if name == 'Bash' and re.search(r'render|puppeteer|ffmpeg.*(libx264|-c:v)', inp.get('command', '')):
        return 'render'
    return CAT.get(name, 'other')

def user_text(m):
    c = m.get('content')
    if isinstance(c, str): return c
    return ' '.join(b.get('text', '') for b in (c or []) if isinstance(b, dict) and b.get('type') == 'text')

def analyse(path):
    rows = []
    for line in open(path):
        try: rows.append(json.loads(line))
        except ValueError: pass
    stamp = lambda d: dt.datetime.fromisoformat(d['timestamp'].replace('Z', '+00:00'))
    users = [(stamp(d), user_text(d.get('message', {}))) for d in rows if d.get('type') == 'user' and d.get('timestamp')]
    users = [(t, s) for t, s in users if s and not s.startswith('<') and not s.startswith('[Image')]
    t0 = users[0][0]
    last = max(stamp(d) for d in rows if d.get('timestamp'))
    msgs, events = {}, []
    for d in rows:
        if d.get('type') != 'assistant' or not d.get('timestamp'): continue
        m = d.get('message', {})
        if m.get('id'): msgs[m['id']] = m.get('usage', {})
        for b in m.get('content', []) or []:
            if b.get('type') == 'tool_use':
                events.append([round((stamp(d) - t0).total_seconds() / 60, 2), classify(b['name'], b.get('input', {}))])
    kinds = collections.Counter(k for _, k in events)
    return dict(
        prompt=users[0][1].strip(),
        minutes=round((last - t0).total_seconds() / 60, 1),
        turns=len(msgs),
        out_tokens=sum(u.get('output_tokens', 0) for u in msgs.values()),
        tools=len(events), renders=kinds['render'], reviews=kinds['review'], writes=kinds['write'],
        interventions=[[round((t - t0).total_seconds() / 60, 1), s[:120]] for t, s in users[1:]],
        events=events,
    )

if __name__ == '__main__':
    out = {}
    for arg in sys.argv[1:]:
        k, p = arg.split('=', 1)
        out[k] = analyse(p)
    json.dump(out, sys.stdout, indent=1)
