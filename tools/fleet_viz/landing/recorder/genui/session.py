"""Drive one generative-UI case through dsh headless (one Session, resumed per interaction), recording each interaction
via the header-free proxy. usage: session.py CASE_DIR OUT_DIR PLAN.json PORT"""
import json, os, re, subprocess, sys, time, shutil
case, out, plan, port = sys.argv[1], sys.argv[2], json.load(open(sys.argv[3])), int(sys.argv[4])
S = '/home/ubuntu/landing-scratch'; os.makedirs(out, exist_ok=True)
screen = os.path.join(case, 'ui', 'screen.html')
def buttons():
    if not os.path.exists(screen): return []
    h = open(screen).read(); out = []
    for m in re.finditer(r'<button\b([^>]*)>(.*?)</button>', h, re.S | re.I):
        a = dict(re.findall(r'(data-[\w-]+)="([^"]*)"', m.group(1))); lab = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', m.group(2))).strip()
        if 'data-action' in a: out.append(dict(action=a['data-action'], arg=a.get('data-arg'), label=lab))
    return out
sid = None
for i, it in enumerate(plan, 1):
    d = os.path.join(out, f'{i:02d}'); 
    if os.path.exists(os.path.join(d, 'meta.json')):
        m0 = json.load(open(os.path.join(d, 'meta.json')))
        if m0['rc'] == 0: sid = m0['session']; continue
        shutil.rmtree(d)
    os.makedirs(d, exist_ok=True)
    for f in ('proxy.jsonl', 'events.jsonl'):
        if os.path.exists(f'{d}/{f}'): os.remove(f'{d}/{f}')
    click = None
    if 'click' in it:
        rx = re.compile(it['click'], re.I)
        click = next((b for b in buttons() if rx.search(' '.join(filter(None, [b['label'], b['action'], b['arg']])))), None)
    if click:
        msg = f'UI event: click data-action="{click["action"]}"' + (f' data-arg="{click["arg"]}"' if click['arg'] is not None else '') + f' label="{click["label"][:120]}"'
    else:
        msg = it.get('say') or it.get('else')
    before = open(screen).read() if os.path.exists(screen) else None
    if before is not None: open(f'{d}/screen_before.html', 'w').write(before)
    px = subprocess.Popen([sys.executable, f'{S}/tools/recproxy.py', str(port), f'{d}/proxy.jsonl']); time.sleep(1)
    env = dict(os.environ, PATH=f'{S}/node/bin:' + os.environ['PATH'], DSH_HOME=os.environ.get('CASE_DSH_HOME', f'{S}/home'), DSH_TELEMETRY_DISABLED='1', DEEPSEEK_BASE_URL=f'http://127.0.0.1:{port}/anthropic')
    cmd = ['node', f'{S}/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js', '--profile', 'headless', '--json'] + (['--session-id', sid] if sid else []) + [msg]
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=case, env=env, stdout=subprocess.PIPE, stderr=open(f'{d}/stderr.txt', 'w'), text=True)
    with open(f'{d}/events.jsonl', 'w') as ev:
        for line in p.stdout:
            ev.write(json.dumps(dict(t=time.time(), line=line.rstrip('\n'))) + '\n'); ev.flush()
            if sid is None and '"type":"session"' in line: sid = json.loads(line)['sessionId']
    rc = p.wait(); t1 = time.time(); px.terminate(); px.wait()
    if os.path.exists(screen): open(f'{d}/screen_after.html', 'w').write(open(screen).read())
    json.dump(dict(i=i, intended=it['type'], message=msg, click=click, plan=it, session=sid, t0=t0, t1=t1, rc=rc, case=case), open(f'{d}/meta.json', 'w'), indent=1)
    print(f'{i:02d} {it["type"]:5s} rc={rc} {t1 - t0:6.1f} s  {msg[:100]}', flush=True)
    if rc != 0: print('stopping on error'); break
