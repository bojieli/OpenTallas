#!/usr/bin/env python3
"""Both-leg point-capture region screen with explicit future-native budgets, no borrowed ETM."""
import argparse,json,re,subprocess,collections
from pathlib import Path
import numpy as np
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();O=a.out;R=Path(__file__).resolve().parents[3];g=json.loads((O/'connected_geometry.json').read_text());boxes=g['results']['Q_cooptimized_capsules']['placement'];graph=json.loads((O/'cluster_graph.json').read_text());cells=next(v['cells']for v in graph['modules'].values()if v.get('attributes',{}).get('top')in[1,'1','00000000000000000000000000000001']);metrics=json.loads((O/'perpin_native_metrics.json').read_text())['metrics'];pins={}
for m,v in g['leaf_views'].items():
 s=subprocess.check_output(['git','show',v['record']+':'+v['path']],cwd=R).decode();pins[m]={}
 for pm in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',s,re.M|re.S):pins[m][pm[1]]=[((float(x)+float(z))/2,(float(y)+float(w))/2)for x,y,z,w in re.findall(r'RECT\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)\s+([\d.e+-]+)',pm[2])]
D=collections.defaultdict(list);S=collections.defaultdict(list)
for n,c in cells.items():
 for p,bits in c['connections'].items():
  for i,bit in enumerate(bits):
   if isinstance(bit,int):(D if c['port_directions'][p]=='output'else S)[bit].append((n,p if len(bits)==1 else f'{p}[{i}]'))
def coord(ep):
 n,p=ep;b=boxes[n];return[(b['x']+x,b['y']+y)for x,y in pins[cells[n]['type']][p]]
def constraints(port,indices,side):
 result=[]
 for bit in indices:
  node=cells['mix.relay']['connections'][port][bit]
  eps=D[node]if side=='input'else S[node]
  eps=[ep for ep in eps if ep[0]!='mix.relay'];assert eps
  for ep in eps:
   m=cells[ep[0]]['type'];v=metrics[m]['tt'][ep[1]];native=v['out'if side=='input'else'inp'];assert native is not None
   reach=(833.333-60-150-native-(190 if side=='input'else 220))/.76
   result.append({'existing_endpoint':ep,'direction':'producer_to_capture'if side=='input'else'capture_to_consumer','existing_native_ps':native,'allocated_new_leaf_native_ps':190 if side=='input'else 220,'reach_um':reach,'points_um':coord(ep)})
 return result
groups=[]
for k in range(8):groups.append((f'mul{k}',constraints('up_i',[61+k,53+k],'input')+constraints('up_o',[61+k,53+k],'output')))
for k in range(4):groups.append((f'add{k}',constraints('up_i',[45+2*k,46+2*k,41+k,37+k],'input')+constraints('up_o',[45+2*k,46+2*k,41+k,37+k],'output')))
groups.append(('shell_up',constraints('up_i',range(37),'input')+constraints('up_o',range(37),'output')))
for k in range(4):
 incoming=constraints('dn_i',range(4,36),'input');outgoing=constraints('dn_o',range(4,36),'output');outgoing=[c for c in outgoing if c['existing_endpoint'][0]==f'mix.g_add[{k}].leaf'];assert len(outgoing)==32;groups.append((f'gate{k}',incoming+outgoing))
groups.append(('shell_dn',constraints('dn_i',range(4),'input')+constraints('dn_o',range(4),'output')))
# Whole parent candidate region; existing hard-child outlines excluded.
x,y=np.meshgrid(np.arange(0,1431.624,2.16),np.arange(0,851.04,2.16));x=x.ravel();y=y.ravel();free=np.ones(len(x),dtype=bool)
for b in boxes.values():free&=~((x>b['x']-.036)&(x<b['x']+b['w']+.036)&(y>b['y']-.036)&(y<b['y']+b['h']+.036))
rows=[]
for name,cs in groups:
 worst=np.full(len(x),-1e99);bounds={'x+y':[-1e99,1e99],'x-y':[-1e99,1e99]}
 for c in cs:
  points=c['points_um'];reach=c['reach_um'];d=np.minimum.reduce([np.abs(x-u)+np.abs(y-v)for u,v in points]);worst=np.maximum(worst,d-reach)
  for axis,vals in [('x+y',[u+v for u,v in points]),('x-y',[u-v for u,v in points])]:bounds[axis][0]=max(bounds[axis][0],min(vals)-reach);bounds[axis][1]=min(bounds[axis][1],max(vals)+reach)
 feasible=(worst<=1e-6)&free;best=int(np.argmin(np.where(free,worst,np.inf)));rows.append({'group':name,'both_leg_constraints':len(cs),'necessary_strip_bounds_um':bounds,'empty_even_before_obstacles':any(lo>hi for lo,hi in bounds.values()),'free_point_candidates':int(feasible.sum()),'best_free_point_um':[float(x[best]),float(y[best])],'best_worst_excess_um':float(worst[best]),'constraints':cs})
r={'status':'FUTURE_NATIVE_BUDGET_BOTH_LEG_POINT_SCREEN_ONLY','new_capture_native_budgets_ps':{'capture':190,'launch':220,'unknown_new_root_skew':150},'uses_old_relay_ETM_for_new_leaf':False,'groups':rows,'scope':['Actual existing producer/consumer ETM/pins; proposed leaf pins and footprint are unknown, represented as a point only. Not a newleaf native PASS.','Both capture edges are screened, not merely producer adjacency. Empty region rejects current fixed endpoints under allocated native budgets.','Nonempty points require actual tiny-leaf source synthesis/LEF/arcs/clock/reset/PG/fanout and all incident pin access proof. No actual area estimate or adopted physical root delivery.','Grid includes Etransport reserve; using these points consumes channel and requires joint fullparent route/cut regrant.']};(O/'split_relay_regions.json').write_text(json.dumps(r,indent=1)+'\n');print([(v['group'],v['free_point_candidates'],round(v['best_worst_excess_um'],2))for v in rows])
