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
        lab = lambda r: r['name'] + '(' + ', '.join(f'{k}={json.dumps(v)}' for k, v in r['arguments'].items()) + ')'
        tv = [dict(name=r['name'], label=lab(r), result=json.dumps(r['result'])[:600], ms=r['ms'], args=r['arguments'], effect=r['result']) for r in t.get('tool_results', [])]
        tv += [dict(name=r['name'], label=lab(r) + ' rejected by the harness', result=r['error'], ms=0.0, args=r['arguments'], effect={'error': r['error']})
               for r in t.get('rejected_calls', [])]                     # invalid arguments: never sent to the home
        pre = t.get('new_prompt_tokens') or t['prompt_tokens']
        out.append(dict(prefill_tokens=pre, cached_tokens=t['prompt_tokens'] - pre, output_tokens=t['output_tokens'], reasoning_tokens=t['reasoning_tokens'],
                        thinking=t['thinking'], text=t['content'], tool_calls=tv, tools_ms=t.get('tool_wall_ms', 0.0), **({'think_capped': bool(t['think_capped'])} if 'think_capped' in t else {})))
    if callable(model_note): model_note = model_note(d)
    extra = dict(backend=d['backend'], provider=d.get('provider'), quantization=d.get('quantization'),
                 thinking_mode=bool((d.get('sampling') or {}).get('enable_thinking')), think_budget=d.get('think_budget')) if 'backend' in d else {}
    return dict(kind='home', model=d['model'], model_note=model_note, **extra, request=d['request'], system=d['system'], recorded=d['recorded'],
                initial_state=d['initial_state'], final_state=d['final_state'], steps=out,
                served_models=sorted({t.get('served_model') for t in d['turns'] if t.get('served_model')}))

def write(name, obj):
    s = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    if KEY_RE.search(s) or os.environ.get('DEEPSEEK_API_KEY', '@@none@@')[:12] in s: sys.exit(f'refusing to write {name}: key-like string')
    open(os.path.join(OUT, name), 'w').write(s); print(name, len(s))

def qwen_note(d):
    think = (d.get('sampling') or {}).get('enable_thinking')
    mode = f"thinking mode on, budget {d['think_budget']} tokens per turn" if think and d.get('think_budget') else ('thinking mode on' if think else 'thinking mode off')
    if d.get('backend') == 'openrouter':
        return f"Qwen3-8B via OpenRouter ({', '.join(d.get('provider') or ['?'])}, quantisation reported: {', '.join(map(str, d.get('quantization') or ['?']))}), {mode}"
    return f"Qwen3-8B, released weights, BF16, run locally on CPU, {mode}"


GENUI_CASES = [('bi', 'Business intelligence', 'A sales analytics app over a live SQLite database: 1.0M orders, 2.1M order lines, 120K customers. The model explores the schema, runs SQL with the sandbox\'s ./sql tool and draws the dashboard as HTML with inline SVG.'),
               ('desk', 'Desktop and file manager', 'Every window of a desktop is generated: a real home directory in the sandbox (documents, photos with EXIF, git projects, downloads). The model reads it with ls, stat, du, find, cat, git and an EXIF reader.'),
               ('edit', 'Editing a report', 'Report pages built from CSV files (web analytics, project hours, inventory), then edited: chart type, filters, columns, theme.')]
def _prefill_model(repo):
    sys.path.insert(0, os.path.join(repo, 'tools')); import arch_prefill as AP, subprocess
    m, rates = AP.V41(), AP.gpu_rates(); rc, ro = rates['rates']['conservative']['b200_flops'], rates['rates']['optimistic']['b200_flops']
    head = subprocess.run(['git', '-C', repo, 'log', '-1', '--format=%h %cs', '--', 'tools/arch_prefill.py', 'results/arch/prefill_ingest.json'], capture_output=True, text=True).stdout.strip()
    floor = m.layers * AP.EP_LAYER_FLOOR_S; link = 2 * AP.NIC400_Bps
    def turn(new, ctx0):
        fl = m.prefill_flops(new, ctx0)['total']; kv = m.sent_bytes(new, ctx0)['total']
        return dict(prefill_s=max(fl / (8 * rc), floor), prefill_s_low=fl / (8 * ro), kv_bytes=kv, kv_s=kv / link + AP.FENCE_S)
    A = dict(prefill_model=f'tools/arch_prefill.py v41_turn ({head}): max(FLOPs / (8 x B200 at the LMSYS-calibrated {rc/1e15:.2f} PFLOP/s each), {m.layers} layers x {AP.EP_LAYER_FLOOR_S*1e3:.1f} ms EP floor); low end = FLOPs / (8 x B200 at {ro/1e15:.2f} PFLOP/s), no floor',
             ep_floor_s=floor, ep_layer_floor_s=AP.EP_LAYER_FLOOR_S, layers=m.layers, gpus=8,
             kv_model=f'tools/arch_prefill.py V41.sent_bytes: {m.row_B} B per compressed KV row the new tokens create (288 main + 68 index key, results/arch/v41_rack.json kv_replication.row_bytes), plus the {m.layers} x 128 x 528 B sliding-window rings re-sent each call; serial after prefill, plus a {AP.FENCE_S*1e6:.0f} us fence',
             link_Bps=link, link_note='2 x ConnectX-7 400G, GPUDirect RDMA goodput 391.47 Gb/s each (results/arch/prefill_ingest.json citations.cx7_gdr)',
             prefill_cite='results/arch/prefill_ingest.json citations.lmsys_gb200_dsv3 (LMSYS GB200 DeepSeek-V3 prefill, 26,156 / 18,471 tok/s per GPU), converted to a per-GPU FLOP rate (gpu_calibration)')
    return turn, A

def genui_case(cdir, turn, sandbox_root):
    """one dsh generative-UI session: <cdir>/NN/{meta.json, events.jsonl, proxy.jsonl, screen_before.html, screen_after.html}"""
    pages, inter, served = [], [], set(); prev_end = None; page_ix = None
    def add_page(h):
        if pages and pages[-1] == h: return len(pages) - 1
        pages.append(h); return len(pages) - 1
    for d in sorted(x for x in os.listdir(cdir) if x.isdigit() and os.path.exists(os.path.join(cdir, x, 'meta.json'))):
        base = os.path.join(cdir, d); meta = json.load(open(f'{base}/meta.json'))
        ev = [(o['t'], json.loads(o['line'])) for o in map(json.loads, open(f'{base}/events.jsonl')) if o['line'].startswith('{')]
        reqs, resps = {}, []
        for o in map(json.loads, open(f'{base}/proxy.jsonl')):
            (reqs.__setitem__(o['n'], o) if o['kind'] == 'req' else resps.append(o))
        calls = []; full_inputs = {}
        for o in sorted(resps, key=lambda o: o['n']):
            b = reqs[o['n']]['body'] or {}
            if 'tools' not in b: continue
            st = [e for _, e in o['events'] if e.get('type') == 'message_start'][0]['message']; served.add(st.get('model'))
            blocks = {}
            for _, e in o['events']:                                    # full tool inputs: dsh's --json events truncate long ones
                if e.get('type') == 'content_block_start' and e['content_block'].get('type') == 'tool_use': blocks[e['index']] = [e['content_block']['id'], '']
                elif e.get('type') == 'content_block_delta' and e['delta'].get('type') == 'input_json_delta' and e['index'] in blocks: blocks[e['index']][1] += e['delta']['partial_json']
            for bid, js in blocks.values():
                try: full_inputs[bid] = json.loads(js)
                except Exception: pass
            dl = [e['delta'] for _, e in o['events'] if e.get('type') == 'content_block_delta']
            calls.append(dict(u=[e for _, e in o['events'] if e.get('type') == 'message_delta'][-1]['usage'], t0=o['t0'], t1=o['t1'],
                              think=''.join(d.get('thinking', '') for d in dl if d.get('type') == 'thinking_delta'), text=''.join(d.get('text', '') for d in dl if d.get('type') == 'text_delta')))
        steps = []; cur = None
        for t, e in ev:
            if e['type'] == 'status' and e.get('phase') == 'step_start': cur = dict(think='', text='', calls=[], res={})
            elif e['type'] in ('thinking', 'text') and cur is not None: cur['think' if e['type'] == 'thinking' else 'text'] += e.get('text', '')
            elif e['type'] == 'tool_call': cur['calls'].append((t, e))
            elif e['type'] == 'tool_result': cur['res'][e['callId']] = (t, e)
            elif e['type'] == 'status' and e.get('phase') == 'step_end': steps.append(cur)
        assert len(steps) == len(calls), (cdir, d, len(steps), len(calls))
        bf = f'{base}/screen_before.html'; before = open(bf).read() if os.path.exists(bf) else None
        page = before; pb = add_page(before) if before is not None else None; out = []; kinds = set()
        for s, c in zip(steps, calls):
            u = c['u']; P = u['input_tokens'] + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0); O = u['output_tokens']
            new = P if prev_end is None else P - prev_end
            if new <= 0: new = u['input_tokens']                       # history rewritten: fall back to the API's cache miss
            prev_end = P + O
            tv, raw = [], dict(tool=0, html=0, patch=0)
            res_tok = 0; tool_end = c['t1']; page_after = None
            for tc, call in s['calls']:
                inp = full_inputs.get(call['callId']) or call.get('input') or {}; name = call['tool']; tr, r = s['res'].get(call['callId'], (tc, {}))
                fp = str(inp.get('file_path', '')); on_screen = fp.endswith('ui/screen.html')
                k = 'html' if (name == 'write' and on_screen) else 'patch' if (name == 'edit' and on_screen) else 'tool'
                n_in = ntok(json.dumps(inp, ensure_ascii=False)); raw[k] += n_in + ntok(name)
                ok = r.get('status') == 'completed'
                if ok and k == 'html': page = inp['content']; page_after = add_page(page); kinds.add('full')
                elif ok and k == 'patch' and page is not None and inp.get('old_string', '') in page:
                    page = page.replace(inp['old_string'], inp['new_string']) if inp.get('replace_all') else page.replace(inp['old_string'], inp['new_string'], 1)
                    page_after = add_page(page); kinds.add('patch')
                rtxt = r.get('result', '') if isinstance(r.get('result', ''), str) else json.dumps(r.get('result'))
                res_tok += ntok(rtxt); tool_end = max(tool_end, tr)
                v = tool_view(name, inp, rtxt); v.update(kind=k, status=r.get('status'), result_tokens=ntok(rtxt), page=page_after if k != 'tool' else None)
                if k == 'html': v.pop('diff', None); v['label'] = 'write ui/screen.html (new screen)'
                if k == 'patch': v['diff'] = dict(old=clean(inp.get('old_string', ''), 600), new=clean(inp.get('new_string', ''), 600)); v['label'] = 'edit ui/screen.html'
                tv.append(v)
            s['think'], s['text'] = c['think'] or s['think'], c['text'] or s['text']      # the proxy's stream is complete; dsh's events truncate
            raw['text'] = ntok(s['text']); r_t = min(ntok(s['think']), O); rest = O - r_t; tot = sum(raw.values()) or 1
            split = {k: int(rest * v / tot) for k, v in raw.items()}; big = max(raw, key=raw.get); split[big] += rest - sum(split.values())
            tw = max(0.0, tool_end - c['t1']) if s['calls'] else 0.0
            out.append(dict(prompt_tokens=P, new_tokens=new, api_cache_miss=u['input_tokens'], output_tokens=O, reasoning_tokens=r_t,
                            tool_tokens=split['tool'], html_tokens=split['html'], patch_tokens=split['patch'], text_tokens=split['text'],
                            tool_result_tokens=res_tok, tool_s=round(tw, 3), thinking=clean(s['think'], 5000), text=clean(s['text'], 600),
                            tool_calls=tv, api_s=round(c['t1'] - c['t0'], 2), **turn(new, P - new)))
        af = f'{base}/screen_after.html'
        if os.path.exists(af):
            after = open(af).read()
            if page != after: print('  note', cdir, d, 'reconstructed page differs from the saved screen; using the saved one'); add_page(after)
        kind = 'full' if 'full' in kinds else 'patch' if 'patch' in kinds else 'none'
        ev0 = meta['click'] and dict(kind='click', action=meta['click']['action'], arg=meta['click']['arg'], label=meta['click']['label']) or dict(kind='say', text=meta['message'])
        inter.append(dict(i=meta['i'], kind=kind, intended=meta['intended'], event=ev0, message=meta['message'], page_before=pb, page_after=len(pages) - 1 if pages else None,
                          wall_s=round(meta['t1'] - meta['t0'], 1), calls=out))
    return dict(interactions=inter, pages=pages, served=sorted(served))

def genui_all(root, repo):
    turn, A = _prefill_model(repo); cases = []
    for cid, title, blurb in GENUI_CASES:
        if not os.path.isdir(f'{root}/{cid}'): continue
        g = genui_case(f'{root}/{cid}', turn, root)
        g.update(id=cid, title=title, blurb=blurb); cases.append(g)
    return cases, A

os.makedirs(OUT, exist_ok=True)
TASKS = [('csvstat', 'Add a feature', 'Add a --group-by option to a CSV statistics CLI, with tests and docs.'),
         ('splitwise', 'Fix a failing test', 'A money-splitting library loses cents. The agent finds the rounding bug and fixes it.'),
         ('ratelimit', 'Hunt three bugs', 'A token-bucket rate limiter lets bursts through. The agent fixes three bugs.')]
idx = dict(agent=[], home=[], long=None)
for task, title, blurb in TASKS:
    if os.path.exists(f'{RAW}/{task}/meta.json'):
        o = dsh(task); o.update(id=task, title=title, blurb=blurb); write(f'agent_{task}.json', o); idx['agent'].append(dict(id=task, title=title, file=f'agent_{task}.json'))
for f, title, design, note in [('home_ds_trip.json', 'Leaving for a trip · DeepSeek', 'ds', 'DeepSeek API, model deepseek-flash'),
                               ('home_qwen_bedtime.json', 'Bedtime routine · Qwen3-8B', 'qwen', qwen_note)]:
    if os.path.exists(f'{RAW}/{f}'):
        o = home(f'{RAW}/{f}', note); o.update(id=f[:-5], title=title, design=design); write(f, o); idx['home'].append(dict(id=f[:-5], title=title, design=design, file=f))
if os.path.exists(f'{RAW}/qwen_long.json'):
    q = json.load(open(f'{RAW}/qwen_long.json')); write('qwen_long.json', q); idx['long'] = 'qwen_long.json'
idx['genui'] = []
GROOT = os.environ.get('GENUI_RAW', os.path.join(RAW, 'genui'))
if os.path.isdir(GROOT):
    cases, A = genui_all(GROOT, os.environ.get('OT_REPO', '/home/ubuntu/OpenTallas'))
    for c in cases:
        o = dict(kind='genui', harness='DeepSeek Harness (dsh) 0.2.0-rc.2 (npm latest), headless profile, thinking enabled, one Session resumed per interaction',
                 model_served=c.pop('served'), assumptions=A, **c)
        write(f'genui_{c["id"]}.json', o); idx['genui'].append(dict(id=c['id'], title=c['title'], file=f'genui_{c["id"]}.json'))
write('index.json', idx)
