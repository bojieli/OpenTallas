"""Normalise the raw landing-page recordings into the replay schema the page reads.

    python3 build_recordings.py RAW_DIR OUT_DIR

RAW_DIR holds what recorder/ wrote: <task>/{meta.json,events.jsonl,proxy.jsonl} for the dsh sessions,
qwen_long.json, home_*.json. The proxy never records headers, so no credential reaches RAW_DIR; this script
still refuses to write anything that looks like an API key.

Replay schema (one file per scenario):
  steps[]: one model call each, then that call's tool calls
    prefill_tokens  uncached prompt tokens the server had to prefill (cached prefix excluded)
    cached_tokens   prompt tokens served from the prefix cache
    output_tokens   all generated tokens (reasoning + visible text + tool-call JSON)
    reasoning_tokens  the reasoning share (dsh: the thinking text re-tokenised with the DeepSeek-V4.1 tokenizer)
    tools_ms        measured wall time of the step's tool calls (parallel calls overlap)
    tool_calls[]    {name, label, detail, result, ms, diff?, effect?}
"""
import json, os, re, sys, glob

RAW, OUT = sys.argv[1], sys.argv[2]
SANDBOX = '/home/ubuntu/landing-scratch/sandbox/'
KEY_RE = re.compile(r'sk-[A-Za-z0-9]{8,}')
DS_TOK = glob.glob(os.path.expanduser('~/.cache/huggingface/hub/models--deepseek-ai--DeepSeek-V4.1-Flash/snapshots/*/tokenizer.json'))
tok = None
if DS_TOK:
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(DS_TOK[0])

def clean(s, n=None):
    s = (s or '').replace(SANDBOX, '~/sandbox/').replace('/home/ubuntu/landing-scratch', '~/scratch')
    if n and len(s) > n: s = s[:n] + '\n…'
    return s

def ntok(s): return len(tok.encode(s).ids) if (tok and s) else 0

def tool_view(name, inp, result):
    d = dict(name=name, result=clean(result if isinstance(result, str) else json.dumps(result), 900))
    if name == 'bash': d.update(label='$ ' + clean(inp.get('command', ''), 200), detail=inp.get('description', ''))
    elif name in ('read', 'write'): d.update(label=f'{name} {clean(inp.get("file_path", ""))}')
    elif name == 'edit':
        d.update(label=f'edit {clean(inp.get("file_path", ""))}', diff=dict(old=clean(inp.get('old_string', ''), 1200), new=clean(inp.get('new_string', ''), 1200)))
    elif name == 'glob': d.update(label=f'glob {inp.get("pattern", "")}')
    elif name == 'todo_write': d.update(label='todo: ' + '; '.join(t.get('content', '') for t in inp.get('todos', []))[:200])
    else: d.update(label=name + ' ' + clean(json.dumps(inp), 160))
    if name == 'write': d['diff'] = dict(old='', new=clean(inp.get('content', ''), 1200))
    return d

def dsh(task):
    base = os.path.join(RAW, task); meta = json.load(open(f'{base}/meta.json'))
    ev = [(o['t'], json.loads(o['line'])) for o in map(json.loads, open(f'{base}/events.jsonl'))]
    reqs, resps = {}, []
    for o in map(json.loads, open(f'{base}/proxy.jsonl')):
        if o['kind'] == 'req': reqs[o['n']] = o
        else: resps.append(o)
    served = set(); calls = []
    for o in sorted(resps, key=lambda o: o['n']):
        b = reqs[o['n']]['body'] or {}
        if 'tools' not in b: continue                                   # the parallel session-title request
        st = [e for _, e in o['events'] if e.get('type') == 'message_start'][0]['message']; served.add(st.get('model'))
        u = [e for _, e in o['events'] if e.get('type') == 'message_delta'][-1]['usage']
        calls.append(dict(u=u, api_s=o['t1'] - o['t0'], req_model=b.get('model')))
    steps = []; cur = None
    for t, e in ev:
        if e['type'] == 'status' and e.get('phase') == 'step_start': cur = dict(t0=t, think='', text='', calls=[], res={}, tc=None)
        elif e['type'] in ('thinking', 'text'): cur['think' if e['type'] == 'thinking' else 'text'] += e.get('text', ''); cur['tc'] = cur['tc'] or t
        elif e['type'] == 'tool_call': cur['calls'].append(e); cur['tc'] = cur['tc'] or t
        elif e['type'] == 'tool_result': cur['res'][e['callId']] = (t, e)
        elif e['type'] == 'status' and e.get('phase') == 'step_end': cur['t1'] = t; steps.append(cur)
    assert len(steps) == len(calls), (task, len(steps), len(calls))
    out = []
    for s, c in zip(steps, calls):
        u = c['u']; tc = s['tc'] or s['t1']; prev = tc; tv = []
        for call in s['calls']:
            tr, r = s['res'].get(call['callId'], (tc, {}))
            v = tool_view(call['tool'], call.get('input') or {}, r.get('result', '')); v['ms'] = round((tr - prev) * 1000, 1); v['status'] = r.get('status'); prev = max(prev, tr); tv.append(v)
        rt = min(ntok(s['think']), u['output_tokens'])
        out.append(dict(prefill_tokens=u['input_tokens'], cached_tokens=u.get('cache_read_input_tokens', 0), output_tokens=u['output_tokens'],
                        reasoning_tokens=rt, thinking=clean(s['think'], 4000), text=clean(s['text'], 4000), tool_calls=tv,
                        tools_ms=round((s['t1'] - tc) * 1000, 1) if s['calls'] else 0.0, recorded_api_s=round(c['api_s'], 2)))
    final = [e for _, e in ev if e['type'] == 'final']
    return dict(kind='agent', harness='DeepSeek Harness (dsh) 0.2.0-rc.2, headless profile, npm @deepseek-ai/dsh',
                model_requested=sorted({c['req_model'] for c in calls}), model_served=sorted(served),
                task=meta['task'], repo=os.path.basename(meta['repo']), recorded=ev[0][0], wall_s=round(meta['t1'] - meta['t0'], 1),
                final=clean(final[-1]['text'] if final else '', 3000), steps=out)

def home(path, model_note):
    d = json.load(open(path)); out = []
    for t in d['turns']:
        tv = [dict(name=r['name'], label=r['name'] + '(' + ', '.join(f'{k}={json.dumps(v)}' for k, v in r['arguments'].items()) + ')',
                   result=json.dumps(r['result'])[:600], ms=r['ms'], args=r['arguments'], effect=r['result']) for r in t.get('tool_results', [])]
        pre = t.get('new_prompt_tokens') or t['prompt_tokens']
        out.append(dict(prefill_tokens=pre, cached_tokens=t['prompt_tokens'] - pre, output_tokens=t['output_tokens'], reasoning_tokens=t['reasoning_tokens'],
                        thinking=t['thinking'], text=t['content'], tool_calls=tv, tools_ms=t.get('tool_wall_ms', 0.0)))
    return dict(kind='home', model=d['model'], model_note=model_note, request=d['request'], system=d['system'], recorded=d['recorded'],
                initial_state=d['initial_state'], final_state=d['final_state'], steps=out,
                served_models=sorted({t.get('served_model') for t in d['turns'] if t.get('served_model')}))

def write(name, obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    if KEY_RE.search(s) or os.environ.get('DEEPSEEK_API_KEY', '@@none@@')[:12] in s: sys.exit(f'refusing to write {name}: key-like string')
    open(os.path.join(OUT, name), 'w').write(s); print(name, len(s))

os.makedirs(OUT, exist_ok=True)
TASKS = [('splitwise', 'Fix a failing test', 'A money-splitting library loses cents. The agent finds the rounding bug and fixes it.'),
         ('csvstat', 'Add a feature', 'Add a --group-by option to a CSV statistics CLI, with tests and docs.'),
         ('ratelimit', 'Hunt three bugs', 'A token-bucket rate limiter lets bursts through. The agent fixes three bugs.')]
idx = dict(agent=[], home=[], long=None)
for task, title, blurb in TASKS:
    if os.path.exists(f'{RAW}/{task}/meta.json'):
        o = dsh(task); o.update(id=task, title=title, blurb=blurb); write(f'agent_{task}.json', o); idx['agent'].append(dict(id=task, title=title, file=f'agent_{task}.json'))
for f, title, design, note in [('home_qwen_bedtime.json', 'Bedtime routine', 'qwen', 'Qwen3-8B, BF16, run locally'),
                               ('home_ds_trip.json', 'Leaving for a trip', 'ds', 'DeepSeek API, model deepseek-flash')]:
    if os.path.exists(f'{RAW}/{f}'):
        o = home(f'{RAW}/{f}', note); o.update(id=f[:-5], title=title, design=design); write(f, o); idx['home'].append(dict(id=f[:-5], title=title, design=design, file=f))
if os.path.exists(f'{RAW}/qwen_long.json'):
    q = json.load(open(f'{RAW}/qwen_long.json')); write('qwen_long.json', q); idx['long'] = 'qwen_long.json'
write('index.json', idx)
