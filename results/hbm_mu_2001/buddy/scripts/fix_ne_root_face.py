import json,math,re,sys
from pathlib import Path
sys.path.insert(0,'/srv/opentallas-scratch/claude/wt/codex-hbm-2001/tools/die_plan')
import hub_repack as HR,hbm_r9_delta as R9,hbm_r10_delta as R10
base=Path('/srv/opentallas-scratch/claude/codex-hbm-2001/buddy');t=json.load(open(base/'NE_final.json'));W,H=t['outline_um'];R=HR.Raster(W,H,[HR._core_rect(h)for h in t['hard_cores']]);changes=[]
for s in t['internal_stations']:
 if not s['conn'].startswith('mu_tree_root:'):continue
 q=int(s['conn'].split(':')[1]);up=s['conn'].endswith(':up');old=dict(k=s.get('serial_k',1),wires=s['bits'],regs=len(s.get('regs_um',[])),from_um=s['from_um'],to_um=s['to_um'])
 end='to_um'if up else'from_um';s[end]=[W,s[end][1]]
 k=(4 if up else 5)if q==0 else 1
 width=271if up else 173
 s.update(serial_k=k,bits_parallel=width,bits=math.ceil(width/k),r9_segments=[q,1]if up else[1,q])
 res=HR.route_station(R,s['from_um'],s['to_um'],len(s.get('regs_um',[])),360)
 if res is None:raise RuntimeError('root face path failed '+s['conn'])
 s['regs_um']=[list(p)for p in res['regs']]
 changes.append(dict(conn=s['conn'],old=old,new=dict(k=k,wires=s['bits'],regs=len(s['regs_um']),from_um=s['from_um'],to_um=s['to_um'])))
u=R9.cut(t)['blocked'];segs=[R10.profile(W,H,t,a,b)for a,b in[(0,3957.12),(3957.12,W)]];mx=max([u[a]['max_use']for a in'xy']+[x[a]['max_use']for x in segs for a in'xy'])
r=dict(source='NE_final.json',fix='NE_hub MY: local E faces central root',cut=u,segments=segs,max_axis=mx,changes=changes,verdict='PASS_MODEL_CUT'if mx<=.6+1e-9 else'FAIL_MODEL_CUT')
(base/'NE_rootE.json').write_text(json.dumps(t,indent=1)+'\n');(base/'NE_rootE.report.json').write_text(json.dumps(r,indent=1)+'\n');print(json.dumps({k:v for k,v in r.items()if k not in['changes','cut','segments']}))
