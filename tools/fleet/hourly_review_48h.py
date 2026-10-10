#!/usr/bin/env python3
"""Concurrent fleet health/48h scratch review, with central-only git reads."""
import concurrent.futures, datetime, json, os, re, subprocess, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent; REPO=Path('/home/ubuntu/OpenTallas')
OUT=Path(os.environ.get('OT_FLEET_REVIEW_OUTPUT','/home/ubuntu/codex-takeover-20261010/fleet'))
OUT.mkdir(parents=True,exist_ok=True)
pattern=r'/(?:srv|home/ubuntu|tmp)/[A-Za-z0-9_.+@:=,-]+(?:/[A-Za-z0-9_.+@:=,-]+)*'
protected=set()
for base in (Path.home()/'.local/state/closure_loop',Path('/home/ubuntu/claude-takeover-20261007'),OUT.parent):
    for f in base.rglob('*'):
        if f.is_file() and f.suffix in ('.json','.log','.md','.txt') and 'fleet' not in f.parts[len(base.parts):]:
            try: protected.update(re.findall(pattern,f.read_text(errors='replace')))
            except OSError: pass
r=subprocess.run(['git','-C',str(REPO),'grep','-ohIE',pattern,'HEAD','--','physical','tools'],capture_output=True,text=True)
protected.update(r.stdout.splitlines())
protected.update((str(REPO),str(OUT.parent),'/tmp/claude-1000/bfarch','/tmp/bfpinclk'))
hosts=json.loads((REPO/'tools/closure_loop/hosts.json').read_text())['hosts']
for name in ('ot-pve2','ot-pve3'):
    hosts.append({'name':name,'base':'/srv/opentallas-scratch'})
source=(HERE/'host_review_48h.py').read_text()
scratch=['/srv/opentallas-scratch/claude','/srv/opentallas-scratch2/scratch/claude','/srv/opentallas-scratch2/claude','/srv/opentallas-data/claude','/srv/opentallas/scratch-overflow/claude','/srv/opentallas-scratch/codex','/srv/opentallas-scratch2/codex']
def review(h):
    name=h['name']; roots=scratch if name!='localhost' else ['/tmp/claude-1000']
    cfg={'apply':'--apply' in sys.argv,'uid':1000,'protected':sorted(protected),'roots':roots,'disk_roots':sorted({'/',h['base'],*h.get('disk_roots',{})})}
    payload=source.replace('cfg=json.load(sys.stdin);', 'cfg='+repr(cfg)+';')
    cmd=['sudo','-n','python3','-'] if name=='localhost' else ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','-o','ConnectionAttempts=1',name,'sudo -n python3 -']
    try:
        r=subprocess.run(cmd,input=payload,capture_output=True,text=True)
        return {'host':name,'result':json.loads(r.stdout)} if r.returncode==0 else {'host':name,'error':r.stderr[-400:]}
    except (ValueError,OSError) as e: return {'host':name,'error':str(e)}
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as pool:
    results=list(pool.map(review,hosts))
out=OUT/('review-'+stamp+'.json'); out.write_text(json.dumps(results,indent=2)+'\n')
(OUT/'latest.json').write_text(json.dumps(results,indent=2)+'\n')
for row in results:
    result=row.get('result',{})
    print(json.dumps({'host':row['host'],'error':row.get('error'),'mem_available_gib':result.get('mem_available_gib'),'load':result.get('load'),'disks':result.get('disks'),'actions':[x for x in result.get('audit',[]) if x['action']!='KEEP']}))
print('AUDIT '+str(out))
