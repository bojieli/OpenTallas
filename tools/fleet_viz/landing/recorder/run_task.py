"""Run one dsh headless task in a sandbox repo through the recording proxy; timestamp every --json event."""
import json, os, subprocess, sys, time, threading
name, repo, task = sys.argv[1], sys.argv[2], sys.argv[3]
S = '/home/ubuntu/landing-scratch'; out = f'{S}/rec/{name}'; os.makedirs(out, exist_ok=True)
for f in ('proxy.jsonl', 'events.jsonl', 'stderr.txt'):
    if os.path.exists(f'{out}/{f}'): os.remove(f'{out}/{f}')
port = 18800 + abs(hash(name)) % 100
px = subprocess.Popen([sys.executable, f'{S}/tools/recproxy.py', str(port), f'{out}/proxy.jsonl'])
time.sleep(1)
env = dict(os.environ, PATH=f'{S}/node/bin:' + os.environ['PATH'], DSH_HOME=f'{S}/home', DSH_TELEMETRY_DISABLED='1',
           DEEPSEEK_BASE_URL=f'http://127.0.0.1:{port}/anthropic')
t0 = time.time()
p = subprocess.Popen(['node', f'{S}/dsh/node_modules/@deepseek-ai/dsh/lib/bin.js', '--profile', 'headless', '--json', task],
                     cwd=repo, env=env, stdout=subprocess.PIPE, stderr=open(f'{out}/stderr.txt', 'w'), text=True)
with open(f'{out}/events.jsonl', 'w') as ev:
    for line in p.stdout:
        ev.write(json.dumps(dict(t=time.time(), line=line.rstrip('\n'))) + '\n'); ev.flush()
rc = p.wait(); t1 = time.time(); px.terminate()
json.dump(dict(name=name, repo=repo, task=task, t0=t0, t1=t1, rc=rc), open(f'{out}/meta.json', 'w'))
print(name, 'rc', rc, 'wall', round(t1 - t0, 1))
