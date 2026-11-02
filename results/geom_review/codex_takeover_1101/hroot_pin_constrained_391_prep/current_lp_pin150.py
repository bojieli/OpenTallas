from pathlib import Path
import sys,json
from collections import deque
import numpy as np
from scipy.optimize import linprog
sys.path.insert(0,'/home/ubuntu/OpenTallas/tools/autopilot');import geom_rules as g
import os
P=Path(__file__).parent;results=[];reset_movable=os.environ.get('RESET_MOVABLE')=='1';all19=os.environ.get('ALL19')=='1';margin=os.environ.get('MARGIN_CAPTURE')=='1';target_um=float(os.environ.get('TARGET_UM','390'))
for variant,dy,dx in [('A',-146.88,172.8),('B',-151.2,181.44)]:
 D=g.Design('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/geom.tsv')
 def move(cid,x,y):
  cc=list(D.cells[cid]);a,b=g.ctr(cc);cc[2]+=x-a;cc[4]+=x-a;cc[3]+=y-b;cc[5]+=y-b;D.cells[cid]=tuple(cc)
 for cid,c in list(D.cells.items()):
  x,y=g.ctr(c)
  if 'u_cland_i_seq__g_fan_N__u_fan_kc/' in c[6]:move(cid,x,y+dy)
  elif 'u_cland_i_fch_pc_Q_N_q/' in c[6] or 'u_cland_i_kvpc_Q_N_pc__fo/' in c[6]:move(cid,x+dx,y)
 selected=[cid for cid,c in D.cells.items() if c[0]=='S' and ('u_u_efault.' in c[6] or ('u_bin_' in c[6] and '/eq$' in c[6]) or 'u_bin_i_fch_pc_Q_N_q/q$' in c[6] or 'u_u_fch.q$' in c[6] or 'u_bin_i_kvpc_Q_N_pc__fo/q$' in c[6] or 'u_bout_o_fch_hroot_Q_q/q$' in c[6] or 'u_bin_i_seq__g_fan_N__u_fan_kc/q' in c[6])]
 if margin:
  guardcaps=[];g.r2r_metrics(D,capture_pairs=guardcaps,collect_above=390);mn={z['capture'] for z in guardcaps};selected.extend(cid for cid,c in D.cells.items() if c[6] in mn and cid not in selected)
 if all19:
  bn={z['capture'] for z in json.load(open('/srv/opentallas-scratch/claude/codex-hroot-ff-place-2338/all19_final_comparison.json'))};selected.extend(cid for cid,c in D.cells.items() if c[6] in bn and cid not in selected)
 if reset_movable:selected.extend(cid for cid,c in D.cells.items() if c[0]=='S' and 'u_rrl_101/' in c[6] and cid not in selected)
 index={cid:k for k,cid in enumerate(selected)};n=len(selected);edges=set()
 for target in selected:
  for reverse in [True,False]:
   stack=[target];seen=set()
   while stack:
    cur=stack.pop();nbs=[]
    if reverse:
     for net,ck in D.cell_in.get(cur,[]):
      dr=D.nets[net][1]
      if not ck and dr and dr[0]=='i':nbs.append(dr[1])
    else:
     for net in D.drives.get(cur,[]):nbs.extend(s[1] for s in D.nets[net][2] if s[0]=='i' and not s[2])
    for cid in nbs:
     if D.kind(cid)=='S':edges.add((cid,target) if reverse else (target,cid))
     elif cid not in seen:seen.add(cid);stack.append(cid)
 A=[];B=[]
 for a,b in edges:
  for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
   row=np.zeros(4*n);const=0
   for cid,sgn in [(a,1),(b,-1)]:
    if cid in index:k=index[cid];row[2*k]+=sgn*sx;row[2*k+1]+=sgn*sy
    else:x,y=g.ctr(D.cells[cid]);const+=sgn*(sx*x+sy*y)
   A.append(row);B.append(target_um-const)
 for cid,k in index.items():
  for axis,val in enumerate(g.ctr(D.cells[cid])):
   for sgn in [-1,1]:
    row=np.zeros(4*n);row[2*k+axis]=sgn;row[2*n+2*k+axis]=-1;A.append(row);B.append(sgn*val)
 # Static closure of the newly worsened public output; unchanged E-face geometry.
 pins=[p for p in D.pins if p['name']=='o_fch_hroot_Q_q[0]']
 assert len(pins)==1
 pin=pins[0];cid=next(i for i,c in D.cells.items()if c[6]=='u_bound.u_bout_o_fch_hroot_Q_q/q$_DFF_P_');k=index[cid]
 for sx,sy in [(1,1),(1,-1),(-1,1),(-1,-1)]:
  row=np.zeros(4*n);row[2*k]=sx;row[2*k+1]=sy;A.append(row);B.append(150+sx*pin['x']+sy*pin['y'])
 r=linprog(np.r_[np.zeros(2*n),np.ones(2*n)],A_ub=np.asarray(A),b_ub=np.asarray(B),bounds=[(12,1888),(12,826)]*n+[(0,None)]*(2*n),method='highs')
 res=dict(variant=variant,scope='STATIC current graph LP; no occupancy/PG/site/clock or source-event qualification',selected_existing_ff=n,shared_reset101_movable=reset_movable,all19_captures_movable=all19,margin_capture_movable=margin,exact_touching_pairs=len(edges),target_touching_radius_um=target_um,success=r.success,message=r.message,landing_dx_um=dx,landing_dy_um=dy)
 if r.success:
  targets=[]
  for cid,k in index.items():
   old=g.ctr(D.cells[cid]);x,y=r.x[2*k:2*k+2];dist=abs(x-old[0])+abs(y-old[1])
   if dist>.1:targets.append(dict(name=D.cells[cid][6],old=list(old),new=[float(x),float(y)],distance_um=float(dist)))
   move(cid,x,y)
  bad=[];res.update(targets=targets,metrics=g.r2r_metrics(D,capture_pairs=bad),remaining_bad=bad)
 if margin and not r.success:
  aa=np.c_[np.asarray(A),np.r_[-np.ones(4*len(edges)),np.zeros(len(A)-4*len(edges))]];bb=np.asarray(B).copy();bb[:4*len(edges)]-=target_um
  rr=linprog(np.r_[np.zeros(4*n),1.0],A_ub=aa,b_ub=bb,bounds=[(12,1888),(12,826)]*n+[(0,None)]*(2*n)+[(0,None)],method='highs')
  res['minimum_touching_radius_success']=rr.success
  if rr.success:res['minimum_touching_radius_um']=float(rr.x[-1])
 results.append(res);print({k:v for k,v in res.items() if k not in ['targets','remaining_bad']},flush=True)
(P/'current_graph_lp_margin391_pin150.json').write_text(json.dumps(results,indent=1)+'\n')
