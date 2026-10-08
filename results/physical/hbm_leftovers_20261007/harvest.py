#!/usr/bin/env python3
"""Read-only SSH harvest. New snapshots only; never modifies remote runs."""
import base64, concurrent.futures, datetime, hashlib, json, pathlib, re, subprocess
ROOT='/srv/opentallas-scratch2/scratch/claude/'
SU='/home/ubuntu/wt-hbm-suattn'
AT='/home/ubuntu/wt-hbm-attn'
RT='/home/ubuntu/wt-claude-hbm-router-dv'
SPECS=[
 ('q8hc','ot-epyc2','hbm-abstracts/hub/routes/q8hc','hbm-abstracts/hub/src_q8',SU),
 ('tm3','ot-epyc2','hbm-su/red/rm/routes/tm3_io_u30','hbm-su/src_red13',SU),
 ('sm3','ot-epyc2','hbm-su/red/rm/routes/sm3_io_u30','hbm-su/src_red13',SU),
 ('safe_top','ot-epyc2','hbm-su/red/rm/routes/ts4_pin','hbm-su/src_red14',SU),
 ('safe_slice','ot-epyc2','hbm-su/red/rm/routes/ss1_safe','hbm-su/src_red14',SU),
 ('dt2','ot-epyc3','hbm-attn/routes_dt/dt2_bd150','hbm-attn/src_qb',AT),
 ('dv10','ot-epyc2','hbm-router/routes/dv10_ih60','hbm-router/src_dv9',RT),
 ('dv11','ot-epyc2','hbm-router/routes/dv11_idly','hbm-router/src_dv11',RT),
 ('dv12','ot-epyc2','hbm-router/routes/dv12_idly2','hbm-router/src_dv12',RT),
]
REMOTE=r'''
import base64,datetime,hashlib,json,pathlib,re,subprocess
r=pathlib.Path(ROUTE); s=pathlib.Path(SOURCE)
files={}; missing=[]
def take(p,tail=False):
 if not p.is_file(): return
 b=p.read_bytes(); original=len(b)
 if tail: b=b''.join(b.splitlines(keepends=True)[-35:])
 files[str(p)]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'original_bytes':original,'tail_only':tail,'data':base64.b64encode(b).decode()}
for name in ['SOURCE_COMMIT','args','exit','physical.json','corner_sta.json','corner_sta_833.json','corner.log','check.json','ports/summary.json','view/abstract.json','io150.txt']:
 p=r/name
 if p.is_file(): take(p)
 else: missing.append(name)
take(r/'run.log',True)
for pat in ['work/orfs/config.mk','work/orfs/constraint.sdc','work/orfs/hooks/*.tcl','work/orfs/logs/asap7/*/base/*.json','work/orfs/reports/asap7/*/base/6_finish.rpt','view/*.lib','view/*.lef','view/export*.tcl','pa/pa.log']:
 for p in r.glob(pat): take(p)
logs=sorted(r.glob('work/orfs/logs/asap7/*/base/*.log'),key=lambda p:p.stat().st_mtime)
for p in logs[-2:]: take(p,True)
# Preserve configured RTL, source Tcl dependencies and macro inputs. Also retain
# post-SDCs and recipes, which may not appear in the route-time config.
queue=[]
for v in list(files.values()):
 text=base64.b64decode(v['data']).decode(errors='replace')
 queue += [s/x for x in re.findall(r'/src/([^\s\"\}\)]+)',text)]
for d in ['physical/hbm_su_c12','physical/hbm_attn_tile_r/die_tile','physical/hbm_accel_die_views/router/rtl','physical/hbm_accel_die_views/common']:
 if (s/d).is_dir():
  queue += [p for p in (s/d).rglob('*') if p.suffix in ('.tcl','.sdc','.sv','.sh','.json')]
for p in queue:
 if p.is_file(): take(p)
for base in [r.parents[1],r.parents[2],s.parent]: take(base/'STATUS.md')
if 'hbm-su/' in ROUTE:
 take(s.parent/'safe_bench.out');take(s.parent/'safe_bench.sh')
ps=subprocess.check_output(['ps','-eo','pid,etimes,args'],text=True)
matching=[x for x in ps.splitlines() if (str(r) in x or r.name in x) and 'python3 -' not in x and 'sshd:' not in x]
print(json.dumps({'observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'route':str(r),'source_root':str(s),'source_root_exists':s.exists(),'files':files,'missing':missing,'processes':matching}))
'''
def run(spec):
 name,host,route,source,tree=spec
 script='ROUTE='+repr(ROOT+route)+'\nSOURCE='+repr(ROOT+source)+'\n'+REMOTE
 obj=json.loads(subprocess.run(['ssh',host,'python3 -'],input=script,text=True,capture_output=True,check=True).stdout)
 dest=pathlib.Path(tree)/'results/physical/hbm_leftovers_20261007'/name
 dest.mkdir(parents=True,exist_ok=False)
 for remote,v in obj['files'].items():
  b=base64.b64decode(v.pop('data'))
  assert hashlib.sha256(b).hexdigest()==v['sha256']
  if remote.startswith(ROOT+source+'/'):
   rel=remote[len(ROOT+source)+1:]; key='source/'+rel
   local=pathlib.Path(tree)/rel
   v['local_source_matches']=local.is_file() and hashlib.sha256(local.read_bytes()).hexdigest()==v['sha256']
  elif remote.startswith(ROOT+route+'/'): key='route/'+remote[len(ROOT+route)+1:]
  else: key='context/'+remote[len(ROOT):]
  p=dest/key;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);v['saved_as']=key
 obj['host']=host
 (dest/'manifest.json').write_text(json.dumps(obj,indent=2)+'\n')
 return {'name':name,'files':len(obj['files']),'processes':len(obj['processes']),'source_exists':obj['source_root_exists'],'path':str(dest)}
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for result in pool.map(run,SPECS): print(json.dumps(result),flush=True)
