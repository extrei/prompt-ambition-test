"""Assemble research/results.html from page/template.html and the data files."""
import base64, html, json, os
HERE = os.path.dirname(os.path.abspath(__file__)); R = os.path.dirname(HERE)
ld = lambda p: json.load(open(os.path.join(R, p)))
ses, vm, sc = ld('data/sessions.json'), ld('data/video_metrics.json'), ld('data/scores.json')
K = ['P1', 'P2', 'P3']
e = html.escape
norm = lambda k: ' '.join(ses[k]['prompt'].split()).replace("'", '’')   # the raw prompts differ only in whitespace
base = norm('P1')
assert norm('P2').startswith(base) and norm('P3').endswith(norm('P2'))
amb = norm('P2')[len(base):]
per = norm('P3')
per = per[:per.index('Create')]
prompts = [e(base), f'<span class="old">{e(base)}</span><mark>{e(amb)}</mark>', f'<mark>{e(per)}</mark><span class="old">{e(base + amb)}</span>']
runs = []
for i, k in enumerate(K):
    r, s = sc['runs'][k], ses[k]
    thumb = base64.b64encode(open(os.path.join(R, f'page/thumbs/{k.lower()}.jpg'), 'rb').read()).decode()
    marks = [[m, 'user stepped in'] for m, t in s['interventions'] if not t.startswith('[Request') and not t.startswith('Check render')]
    runs.append(dict(id=k, label=r['label'], file=r['file'], score=r['score'], sub=r['sub'], promptHtml=prompts[i],
                     thumb='data:image/jpeg;base64,' + thumb, minutes=s['minutes'], events=s['events'], marks=marks))
lyr = json.loads('[' + open(os.path.join(R, '..', 'LYRICS.md')).read() + ']')
v = lambda f: [f(k) for k in K]
pct = lambda a, b: round((a / b - 1) * 100)
S1, S2, S3 = (ses[k] for k in K)
D = dict(
    runs=runs, axes=sc['axes'], motion=v(lambda k: vm[k]['motion_sec']),
    chorus=[[23, 36], [59, 69], [95.4, 105], [123.5, 136], [140.3, 152]], lyrics=lyr,
    findings=[
        dict(k='P2 · Ambition vs P1', c='var(--p2)', big=f"+{sc['runs']['P2']['score'] - sc['runs']['P1']['score']:.1f} points, {S2['minutes'] / S1['minutes']:.1f}× the time",
             p=f"{vm['P2']['cuts']} hard cuts instead of {vm['P1']['cuts']} and about twice the motion. A single stage became a new scene for almost every lyric line, and energy went from 6.5 to 9.8."),
        dict(k='P3 · + Persona vs P2', c='var(--p3)', big=f"+{sc['runs']['P3']['score'] - sc['runs']['P2']['score']:.1f} points, same budget",
             p=f"Same {S3['minutes']:.0f} minutes and {pct(S3['out_tokens'], S2['out_tokens'])}% more output tokens than ambition, but {pct(S3['turns'], S2['turns'])}% more turns and {S3['renders']} renders instead of {S2['renders']}. The video got calmer: {vm['P3']['still_pct']:.0f}% still frames, a third of the colour, and the top craft and type scores."),
        dict(k='Overall', c='var(--ink)', big=' → '.join(f"{sc['runs'][k]['score']:.1f}" for k in K),
             p='Asking for ambition bought the biggest jump. The persona changed the taste of the work more than its size: fewer colours, more restraint, more checking.')],
    cost=[dict(t='Session time', n='Prompt to last logged event', v=v(lambda k: ses[k]['minutes']), f='min'),
          dict(t='Output tokens', v=v(lambda k: ses[k]['out_tokens']), f='k'),
          dict(t='Assistant turns', v=v(lambda k: ses[k]['turns']), f='int'),
          dict(t='Tool calls', v=v(lambda k: ses[k]['tools']), f='int'),
          dict(t='Render runs', n='Shell calls that ran the renderer or encoder', v=v(lambda k: ses[k]['renders']), f='int'),
          dict(t='Frame reviews', n='Times the agent opened its own rendered frames', v=v(lambda k: ses[k]['reviews']), f='int'),
          dict(t='Code in final build', n='Lines · P1 Python, P2 and P3 JavaScript', v=[1463, 2298, 2404], f='int')],
    look=[dict(t='Hard cuts', n='Abrupt full-frame changes', v=v(lambda k: vm[k]['cuts']), f='int'),
          dict(t='Average motion', n='Mean pixel change per frame', v=v(lambda k: round(vm[k]['motion'], 1)), f='d1'),
          dict(t='Still frames', n='Share of time the picture barely moves', v=v(lambda k: vm[k]['still_pct']), f='pct'),
          dict(t='Colourfulness', n='Hasler–Süsstrunk, mean per frame', v=v(lambda k: vm[k]['colorful']), f='d1'),
          dict(t='Hue families', n='Hue bins holding over 2% of saturated pixels', v=v(lambda k: vm[k]['hue_bins']), f='int'),
          dict(t='Frame rate', v=[30, 60, 60], f='fps')],
)
F = lambda x, d=0: f'{x:,.{d}f}'
cell = {'min': lambda x: F(x, 1) + ' min', 'pct': lambda x: F(x, 1) + '%', 'd1': lambda x: F(x, 1), 'fps': lambda x: f'{x} fps', 'k': F, 'int': F}
D['table'] = [
    dict(g='Result', rows=[['Output file'] + [r['file'] for r in runs], ['Coolness'] + [F(r['score'], 1) for r in runs]]
         + [[a] + [F(r['sub'][j], 1) for r in runs] for j, a in enumerate(D['axes'])]),
    dict(g='Effort', rows=[[c['t']] + [cell[c['f']](x) for x in c['v']] for c in D['cost']]),
    dict(g='On screen', rows=[[c['t']] + [cell[c['f']](x) for x in c['v']] for c in D['look']] + [['Bitrate', '20.0 Mbps', '23.7 Mbps', '35.5 Mbps']]),
]
t = open(os.path.join(R, 'page/template.html')).read().replace('/*DATA*/null', json.dumps(D, ensure_ascii=False))
open(os.path.join(R, 'results.html'), 'w').write(t)
json.dump({k: dict(score=sc['runs'][k]['score'], sub=sc['runs'][k]['sub'], **{x: ses[k][x] for x in ('minutes', 'turns', 'out_tokens', 'tools', 'renders', 'reviews')},
                   **{x: vm[k][x] for x in ('cuts', 'motion', 'still_pct', 'colorful', 'hue_bins')}) for k in K},
          open(os.path.join(R, 'data/summary.json'), 'w'), indent=1)
print('wrote results.html', len(t))
