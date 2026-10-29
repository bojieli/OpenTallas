#!/usr/bin/env python3
"""L2 pin-only proposal: align actual registered bit links within all external405um constraints."""
import copy,json,sys
from pathlib import Path
import numpy as np
from scipy.optimize import linear_sum_assignment
r=Path(sys.argv[1]);o=Path(sys.argv[2]);o.mkdir(parents=True,exist_ok=True)
# Reuse the orientation-aware actual parent RTL-net correspondence, not port guesses.
ns={'__name__':'l2_source_census'};saved=sys.argv;sys.argv=['census',str(r),str(o)]
exec((r/'results/codex_s81_cores_1028/l2_outline_estimate.py').read_text().split('old=cores')[0],ns);sys.argv=saved
cs=copy.deepcopy(ns['cores']);ps=copy.deepcopy(ns['pins']);cs['u_l2'].update(outline_um=[216,43.2],origin_um=[1149.12,613.44])
p=json.load(open(r/'physical/die_plan/s81/inputs/core_pins/dsdv_gunit_l2_compact_1028.json'));q=copy.deepcopy(p);d={x['name']:x for x in q['pins']};point=ns['point']

for n,v in d.items():
 if n=='clk':v['x']=108.012
 elif v['x']>258:v['x']=215.958
 else:v['x']=round(v['x']-43.2,6)
limits={n:[-1e6,1e6] for n in d}
for net,e in ns['conn'].items():
 if len(e)!=2 or not any(i=='u_l2' for i,p in e):continue
 (i,a),(j,b)=sorted(e,key=lambda v:v[0]!='u_l2')
 assert i=='u_l2'
 other={x['name']:x for x in ps[j]}
 for n,v in d.items():
  if n!=a and not n.startswith(a+'['):continue
  pn=b+n[len(a):]
  if pn not in other:continue
  x,y=point(cs[j],other[pn]);gy=cs[i]['origin_um'][1]+v['y'];dx=405-abs(y-gy)
  limits[n]=[x-1149.12-dx,x-1149.12+dx]
fixedcw=[v['x'] for n,v in d.items() if n=='cw_v' or n.startswith(('cw_d[','cw_a['))]
left=[round(.012+round((2.16+(min(fixedcw)-.144-2.16)*j/1468-.012)/.048)*.048,6) for j in range(1469)]
slots=sorted(set(left+fixedcw));assert len(slots)==1734
fixed={n for n in d if n=='cw_v' or n.startswith(('cw_d[','cw_a['))};fixedx={d[n]['x'] for n in fixed}
original={n:v['x'] for n,v in d.items()}
def assign(names,available,targets,weights):
 av=np.array(sorted(available));cost=np.empty((len(names),len(av)))
 for k,(n,target,weight) in enumerate(zip(names,targets,weights)):
  lo,hi=limits[n];cost[k]=weight*(av-target)**2+.001*(av-original[n])**2
  cost[k,(av<lo-1e-8)|(av>hi+1e-8)]=1e12
 rows,cols=linear_sum_assignment(cost)
 if len(rows)!=len(names) or any(cost[i,j]>=1e12 for i,j in zip(rows,cols)):raise ValueError('no legal all-bit site assignment')
 for i,j in zip(rows,cols):d[names[i]]['x']=float(av[j])
pairs=[(f'{s}[{b}]',f'{n}[{b}]') for s,n in [('rs_i','rn_o'),('rs_o','rn_i')] for b in range(276)]
mate={a:b for a,b in pairs};mate.update({b:a for a,b in pairs})
nfixed={n.replace('cw_','cwn_') for n in fixed}
for n in fixed:d[n.replace('cw_','cwn_')]['x']=d[n]['x']
for iteration in range(6):
 for face,exclude in [('N',nfixed),('S',fixed)]:
  names=[n for n,v in d.items() if (v['y']<1 if face=='S' else v['y']>40) and n not in exclude]
  targets=[d[mate[n]]['x'] if n in mate else d[n.replace('cws_','cw_')]['x'] if n.startswith('cws_') else original[n] for n in names]
  weights=[10 if n in mate else 3 if n.startswith('cws_') else .1 for n in names]
  assign(names,set(slots)-fixedx,targets,weights)
for face,rows in [('N',[v for v in d.values() if v['y']>40]),('S',[v for v in d.values() if v['y']<1])]:assert len({v['x'] for v in rows})==len(rows)
q['source']='Private all-bit connectivity aligned L2 pin proposal; geometry only, no timing/abstract release'
ps['u_l2']=q['pins'];report=ns['census'](cs,ps)
assert sum(v['over405'] for v in report.values())==0
station=next(v for v in ns['type_']['internal_stations'] if v.get('conn')=='bus:unit_i0')['regs_um'][0]
legs=[abs(1149.12+d[n]['x']-station[0])+abs(613.44+d[n]['y']-station[1]) for n in fixed]
assert max(legs)<=405
json.dump(q,open(o/'pins.json','w'),indent=1)
json.dump(dict(direct_bundles=report,through_bits=552,through_x_delta_max_um=max(abs(d[a]['x']-d[b]['x']) for a,b in pairs),through_x_delta_mean_um=sum(abs(d[a]['x']-d[b]['x']) for a,b in pairs)/len(pairs),station_bits=len(legs),station_max_um=max(legs),old_clock_unchanged=d['clk'],outline=[216,43.2],origin=[1149.12,613.44]),open(o/'census.json','w'),indent=1)
print('PASS minimum-offset552 throughbits; maxlateral',max(abs(d[a]['x']-d[b]['x']) for a,b in pairs),';26 external bundles0>405 max',max(v['maximum_um'] for v in report.values()),';265 station max',max(legs))
