#!/usr/bin/env python3
"""Run every bench of the kit job.json files exactly (cmd with {RUN}), in parallel; log + regex verdicts."""
import json, os, re, subprocess, sys, concurrent.futures as cf
R = os.path.dirname(os.path.abspath(__file__)); S = os.path.join(R, 'src')
env = dict(os.environ); vb = os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin')
env['PATH'] = vb + ':' + env['PATH']; env['VERILATOR'] = vb + '/verilator'; env['VJ'] = '4'
jobs = []
for kit in sys.argv[1:]:
    j = json.load(open(f'{S}/physical/ref_tile/{kit}/job.json'))
    for b in j['stages']['bench']:
        jobs.append((kit, b))
def run(kb):
    kit, b = kb
    run = f'{R}/kb/{kit}/{b["name"]}'; os.makedirs(run, exist_ok=True)
    cmd = b['cmd'].replace('{RUN}', run)
    p = subprocess.run(['bash', '-c', cmd], cwd=S, env=env, capture_output=True, text=True)
    out = p.stdout + p.stderr
    open(f'{run}.log', 'w').write(out)
    if b['expect'] == 'pass':
        ok = p.returncode == 0 and (not b.get('pass_regex') or re.search(b['pass_regex'], out, re.M))
    else:
        ok = p.returncode != 0 and re.search(b['fail_regex'], out, re.M)
    return f'{kit} {b["name"]} expect={b["expect"]} rc={p.returncode} {"OK" if ok else "BAD"}'
with cf.ThreadPoolExecutor(max_workers=20) as ex:
    for r in ex.map(run, jobs): print(r, flush=True)
