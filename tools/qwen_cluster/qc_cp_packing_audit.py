#!/usr/bin/env python3
"""Independent geometric witness audit. No reach/timing/clock qualification."""
import argparse,json,itertools,math
from pathlib import Path
from qc_safe_graph import extract
p=argparse.ArgumentParser();p.add_argument('witness');p.add_argument('--out',required=True);a=p.parse_args();d=json.loads(Path(a.witness).read_text());g=extract();W=d['outline_um']['w'];H=d['outline_um']['h'];step=(W-2*172.8-457.92)/3
# Width is rounded to the43.2grid, so use explicit fixed777.6 shelf contract.
assert abs(W-3153.6)<1e-6;cols=[172.8+i*777.6 for i in range(4)]
obs=[dict(inst=t['inst'],at=[cols[int(t['inst'][4])],t['at'][1]],w=457.92,h=1166.4)for t in g['contract']['tiles']];ps=d['placement'];viol=[]
def clash(x,y):
 a,b=x['at'];c,e=y['at'];return not(a+x['w']+20<=c+1e-7 or c+y['w']+20<=a+1e-7 or b+x['h']+20<=e+1e-7 or e+y['h']+20<=b+1e-7)
for x,y in itertools.combinations(ps,2):
 if clash(x,y):viol.append(dict(rule='child_clearance',a=x['inst'],b=y['inst']))
for x in ps:
 u,v=x['at']
 if any(abs(z/43.2-round(z/43.2))>1e-6 for z in [u,v]):viol.append(dict(rule='origin_lattice',a=x['inst']))
 if min(u,v)<20-1e-7 or u+x['w']>W-20+1e-7 or v+x['h']>H-20+1e-7:viol.append(dict(rule='boundary_clearance',a=x['inst']))
 for y in obs:
  if clash(x,y):viol.append(dict(rule='tile_clearance',a=x['inst'],b=y['inst']))
expected=sum(2 if n['kind'].startswith('qfd_c_land_')else 1 for n in g['nodes'].values()if n['bits']>1)
if len(ps)!=expected or len(set(x['inst']for x in ps))!=expected:viol.append(dict(rule='inventory',placed=len(ps),expected=expected))
out=dict(schema='opentallas.cb16.packing_audit.v1',diagnostic_only=True,packing_pass=not viol,release_ready=False,witness=str(a.witness),children=len(ps),tiles=len(obs),outline_um=d['outline_um'],lattice_um=43.2,channel_um=20,violations=viol,scope='Packing/lattice/clearance only; child pin reach, obstacles/routes, clock,reset/native timing remain independent')
Path(a.out).write_text(json.dumps(out,indent=1)+'\n');print('CP_PACKING_AUDIT',len(ps),'children',len(viol),'violations');raise SystemExit(bool(viol))
