from pathlib import Path
import json,sys,math
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import maximum_flow
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as G
P=Path(sys.argv[1]) if len(sys.argv)>1 else Path('/home/ubuntu/coord/tmp/codex-hist-anchor-2100');D=G.Design(P/'projected_geom_joint_B.tsv');C=json.load(open(P/'repack_B_complete.json'));macroports={}
for m in C['macros'].values():
 for p in m['ports']:
  if p['geom_net_index']is not None:macroports.setdefault(p['geom_net_index'],[]).append(p['xy'])
comb=[cid for cid,c in D.cells.items()if c[0]in('B','L','K')];ci={cid:i for i,cid in enumerate(comb)};signal=[i for i,n in enumerate(D.nets)if n[0]not in('CLOCK','POWER','GROUND')];netnodes={ni:(len(comb)+2*k,len(comb)+2*k+1)for k,ni in enumerate(signal)};s=len(comb)+2*len(signal);t=s+1;nn=t+1;INF=1000000
ii=[];jj=[];val=[];fixed=[];pins={p['k']:p for p in D.pins}
for ni in signal:
 a,b=netnodes[ni];ii.append(a);jj.append(b);val.append(1);sig,dr,sinks=D.nets[ni];refs=list(sinks)+([dr]if dr else[])
 if ni in D.multi_drv:refs.extend(('i',v,False)for v in D.multi_drv[ni])
 pts=list(macroports.get(ni,[]))
 for r in refs:
  if r[0]=='p':
   p=pins[r[1]];pts.append((p['x'],p['y']))
  elif not r[2]:
   cid=r[1];kind=D.kind(cid)
   if cid in ci:
    v=ci[cid];ii.extend([v,b]);jj.extend([a,v]);val.extend([INF,INF])
   elif kind=='S':pts.append(G.ctr(D.cells[cid]))
 fixed.append((a,b,np.array(pts).reshape(-1,2)))
print('graph',nn,'nodes',len(ii),'edges',flush=True)
core=C['core_um'];mobs=D.extra['mobs'];tech=D.extra['tech'];results=[]
for axis in (0,1):
 positions=[50,100,137,190,223,288,330,377,430,500,600]if axis==1 else[50,100,150,200,250,300,350,400,450,500,550,600]
 for cut in positions:
  es=[];ed=[]
  for a,b,pts in fixed:
   if not len(pts):continue
   # Ignore terminals inside a1.404um guard about the cut: lowerbound cannot overcount FF/pin-width uncertainty.
   if np.any(pts[:,axis]<cut-1.404):es.append(s);ed.append(a)
   if np.any(pts[:,axis]>cut+1.404):es.append(b);ed.append(t)
  graph=coo_matrix((np.array(val+[INF]*len(es),np.int32),(np.array(ii+es),np.array(jj+ed))),shape=(nn,nn)).tocsr()
  flow=maximum_flow(graph,s,t).flow_value
  # Integrate exact native master obstructions across the full cut.75% derate, then separately reserve known PG duty.
  crossaxis=1-axis;segments=[core[crossaxis],core[crossaxis+2]]
  macros=[m for m in C['macros'].values()if m['bbox_um'][axis]<cut<m['bbox_um'][axis+2]]
  for m in macros:segments.extend([m['bbox_um'][crossaxis],m['bbox_um'][crossaxis+2]])
  segments=sorted(set(max(core[crossaxis],min(core[crossaxis+2],v))for v in segments));capacity=0
  for left,right in zip(segments,segments[1:]):
   mid=(left+right)/2;obs=set()
   for m in macros:
    b=m['bbox_um']
    if b[crossaxis]<mid<b[crossaxis+2]:obs|=mobs[m['master']]
   for ly,(direction,pitch)in tech.items():
    if ly not in ('M2','M3','M4','M5')or ly in obs:continue
    if (axis==0 and direction.upper().startswith('H'))or(axis==1 and direction.upper().startswith('V')):
     pg=2*.12/4.32 if ly=='M5'else 2*.018/.54 if ly=='M2'else 0
     capacity+=(right-left)*.75*(1-pg)/pitch
  row=dict(axis='vertical_x'if axis==0 else'horizontal_y',cut_um=cut,necessary_crossing_nets=int(flow),nominal_derated_PG_duty_capacity_tracks=round(capacity,3),lowerbound_util=round(float(flow/capacity),5),necessary_condition_pass=bool(flow<=capacity))
  results.append(row);print(row,flush=True)
(P/'cut_lowerbounds_B.json').write_text(json.dumps(dict(scope='Necessary global-cut lowerbounds only; unconstrained freecomb, fullspan capacities, not local-window congestion or PG via-landing pass',guard_um=1.404,signal_ceiling='M5',track_derate=.75,PG='M5 duty2*.12/4.32, M2 followpin duty2*.018/.54; exact future via/blockage may reduce',rows=results),indent=2))
