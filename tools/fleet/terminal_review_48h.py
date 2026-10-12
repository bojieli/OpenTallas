#!/usr/bin/env python3
"""Measure/release terminal >48h intermediates; retain every source/final/receipt.

Uses the closure loop's existing classification, near-miss, committed-receipt,
shared-run and .keep gates. Additional live dependencies include fd/environment
and container mounts. No git commands run outside the central checkout.
"""
import concurrent.futures, datetime, json, os, re, shlex, subprocess, sys
from pathlib import Path
REPO=Path('/home/ubuntu/OpenTallas')
sys.path.insert(0,str(REPO/'tools/closure_loop'))
import closure_loop as cl

cl.DEEP_RELEASE_AGE_H=48
APPLY='--apply' in sys.argv
HOST=sys.argv[sys.argv.index('--host')+1] if '--host' in sys.argv else None
OUT=Path(os.environ.get('OT_FLEET_REVIEW_OUTPUT','/home/ubuntu/codex-takeover-20261010/fleet'))
OUT.mkdir(parents=True,exist_ok=True)
LIVE=r'''
import subprocess
for pid in os.listdir('/proc'):
    if not pid.isdigit(): continue
    pp='/proc/'+pid
    try:
        cwd=os.readlink(pp+'/cwd')
        cmd=open(pp+'/cmdline','rb').read().decode(errors='replace')
        env=open(pp+'/environ','rb').read().decode(errors='replace')
        fds=[]
        for fd in os.listdir(pp+'/fd'):
            try: fds.append(os.readlink(pp+'/fd/'+fd))
            except OSError: pass
        if any(x==R or x.startswith(R+'/') for x in [cwd]+fds) or R in cmd+' '+env:
            print('LIVE_DEPENDENCY',pid); sys.exit(3)
    except FileNotFoundError: pass
    except PermissionError:
        print('INACCESSIBLE_PROCESS',pid); sys.exit(3)
ps=subprocess.run(['docker','ps','-q'],capture_output=True,text=True)
if ps.returncode:
    print('DOCKER_PROBE_FAILED'); sys.exit(3)
if ps.stdout.split():
    mounts=subprocess.run(['docker','inspect','-f','{{range .Mounts}}{{.Source}}\n{{end}}',*ps.stdout.split()],capture_output=True,text=True)
    if mounts.returncode: print('DOCKER_INSPECT_FAILED'); sys.exit(3)
    if any(x==R or x.startswith(R+'/') or R.startswith(x.rstrip('/')+'/') for x in mounts.stdout.split()):
        print('LIVE_CONTAINER_MOUNT'); sys.exit(3)
'''
source=cl.DEEP_RELEASE_PY
source=source.replace('refs = [r.rstrip',LIVE+'\nrefs = [r.rstrip',1)
source=source.replace('if top == "src" and mode','if False and top == "src" and mode',1)
source=source.replace('elif top.startswith("bench_src"):', 'elif False and top.startswith("bench_src"):')
source=source.replace('if f in FINAL and (mode != "closed" or "/routes/" in dp or any(dp.startswith(x + "/") for x in finals + soft)):', 'if f in FINAL:')

jobs=cl.all_jobs(); closed=cl.closed_blocks(jobs); ev=cl._main_evidence()
shared={}
for j in jobs:
    if j.get('run'): shared.setdefault((j.get('host'),j['run'].rstrip('/')),[]).append(j)
candidates=[]
for j in jobs:
    if HOST and j.get('host')!=HOST: continue
    if cl._terminal_age_h(j)<48 or not j.get('run'): continue
    mode=cl.deep_release_mode(j,closed,ev)
    if not mode or any(x['status'] not in cl.TERMINAL or cl._terminal_age_h(x)<48 for x in shared[(j.get('host'),j['run'].rstrip('/'))]): continue
    candidates.append((j,mode))
def one(pair):
    old,mode=pair
    with cl.job_lock(old['name']):
        j=cl.load_job(old['name'])
        if cl._terminal_age_h(j)<48 or mode!=cl.deep_release_mode(j,closed,ev): return {'name':old['name'],'skip':'state changed'}
        # Recheck every sibling under its actual current state before modifying a shared run.
        for s in shared[(j.get('host'),j['run'].rstrip('/'))]:
            s=cl.load_job(s['name'])
            if s['status'] not in cl.TERMINAL or cl._terminal_age_h(s)<48: return {'name':j['name'],'skip':'active/recent sibling'}
        run=j['run'].rstrip('/')
        cfg={'run':run,'mode':mode,'dry':not APPLY,'refs':[r for r in ev['refs'] if r.startswith(run+'/')]}
        payload=source.replace('a = json.loads(os.environ["OT_DR"])','a = '+repr(cfg),1)
        cmd=['sudo','-n','python3','-'] if j['host']=='localhost' else ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',j['host'],'sudo -n python3 -']
        r=subprocess.run(cmd,input=payload,capture_output=True,text=True)
        m=re.search(r'DEEP_FREED (\d+)',r.stdout)
        row={'name':j['name'],'host':j['host'],'run':run,'mode':mode,'age_h':round(cl._terminal_age_h(j),1),'apply':APPLY,'rc':r.returncode,'mib':int(m.group(1)) if m else 0,'result':r.stdout.strip()[-200:]}
        if APPLY and r.returncode==0 and m and row['mib']>0:
            cl.event(j,'route bulk released (safe 48h): '+m.group(1)+' MiB; sources, all 6_final artifacts, near-miss route checkpoints, .keep, receipt paths and logs retained')
            j['safe_48h_bulk_release']={'at':cl.now_iso(),'freed_mib':row['mib']}
            cl.save_job(j)
        return row
# One lane per host avoids disk-probe fanout while hosts progress independently.
byhost={}
for pair in candidates: byhost.setdefault(pair[0]['host'],[]).append(pair)
def host(items): return [one(pair) for pair in items]
with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,len(byhost))) as pool:
    rows=[r for group in pool.map(host,byhost.values()) for r in group]
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
p=OUT/('terminal-review-'+stamp+'.json')
p.write_text(json.dumps({'committed_receipts_sha':ev['sha'],'apply':APPLY,'rows':rows},indent=2)+'\n')
for h in byhost:
    group=[r for r in rows if r.get('host')==h]
    print(json.dumps({'host':h,'jobs':len(group),'mib':sum(r['mib'] for r in group),'live_skip':sum(r['rc']==3 for r in group)}))
print('AUDIT '+str(p))
