#!/usr/bin/env python3
"""Preserve real tile children/captures while testing a lower-height aspect ratio."""
import argparse,copy,hashlib,json,math
from pathlib import Path


def separation(a,b):
 return [max(a[k]-b[k]-b[s],b[k]-a[k]-a[s],0)for k,s in [('x','w'),('y','h')]]
def valid(a,others,W,H):
 return a['x']>=5.4-1e-6 and a['y']>=5.4-1e-6 and a['x']+a['w']<=W-5.4+1e-6 and a['y']+a['h']<=H-5.4+1e-6 and all(max(separation(a,b))>=5.4-1e-6 for b in others)
def shift(y):
 return 14.31*min(3,max(0,math.floor((y-330.48+1e-5)/166.32)))

def main():
 p=argparse.ArgumentParser();p.add_argument('inventory',type=Path);p.add_argument('out',type=Path);p.add_argument('--matched-pairs',type=Path);p.add_argument('--views',type=Path);p.add_argument('--parent-repo',type=Path);p.add_argument('--boundaries',type=Path);a=p.parse_args();D=json.loads(a.inventory.read_text());W,H=481.68,1400.22
 children=copy.deepcopy(D['children']);banks=copy.deepcopy(D['data_banks']);reset=copy.deepcopy(D['reset_nodes']);original={b['inst']:copy.deepcopy(b)for b in children+banks+reset}
 for b in children+banks+reset:b['y']=round(b['y']-shift(b['y']),6)
 fixed=children.copy();moving=[]
 constraints=None
 if a.matched_pairs:
  from tile_pin_constraints import PinConstraints
  constraints=PinConstraints(a.inventory,a.matched_pairs,a.views,a.parent_repo,a.boundaries)
 # Keep all existing hard children; relocate only conflicting bank/reset bodies.
 for b in banks+reset:
  if valid(b,fixed,W,H):fixed.append(b)
  else:moving.append(b)
 # Prefer each original capture's own orientation; H256→actual V256 is a
 # different CLOSED orientation variant, not an unsupported 90-degree rotation.
 choices=[]
 for b in moving:
  variants=[(b['master'],b['w'],b['h'])]
  if b['master']=='qkh_packet_h256':variants.append(('qkh_packet_v256',15.12,64.8))
  options=[]
  for master,w,h in variants:
   xs={5.4,W-5.4-w,b['x']};ys={5.4,H-5.4-h,b['y']}
   for q in fixed:
    xs.update([q['x']-5.4-w,q['x']+q['w']+5.4]);ys.update([q['y']-5.4-h,q['y']+q['h']+5.4])
   # Respect .216 X and .27 Y body lattice when relocating.
   for x in sorted(xs):
    x=math.ceil((x-1e-7)/.216)*.216
    for y in sorted(ys):
     y=math.ceil((y-1e-7)/.27)*.27
     q={**b,'master':master,'w':w,'h':h,'x':round(x,6),'y':round(y,6)}
     if valid(q,fixed,W,H):
      displacement=abs(q['x']+w/2-b['x']-b['w']/2)+abs(q['y']+h/2-b['y']-b['h']/2)
      options.append((displacement+10*(master!=b['master']),q))
  if constraints:options=constraints.filter(options,fixed)
  choices.append((len(options),b['inst'],options))
 choices.sort(key=lambda x:x[0])
 # Backtracking protects scarce local corridors from an early greedy choice.
 count=0
 def geometry_filter(opts,placed):
  import numpy as np
  if not opts:return []
  rectangles=np.asarray([[q['x'],q['y'],q['w'],q['h']]for _,q in opts]);ok=np.ones(len(opts),dtype=bool)
  for b in placed:
   dx=np.maximum(np.maximum(rectangles[:,0]-b['x']-b['w'],b['x']-rectangles[:,0]-rectangles[:,2]),0)
   dy=np.maximum(np.maximum(rectangles[:,1]-b['y']-b['h'],b['y']-rectangles[:,1]-rectangles[:,3]),0)
   ok&=np.maximum(dx,dy)>=5.4-1e-6
  return [q for q,keep in zip(opts,ok)if keep]
 def solve(state):
  nonlocal count
  if not state:return True
  name=min(state,key=lambda n:len(state[n]))
  for _,q in sorted(state[name],key=lambda z:z[0]):
   count+=1
   if count>300000:return False
   next_state={}
   for n,opts in state.items():
    if n==name:continue
    options=geometry_filter(opts,[q])
    if constraints:options=constraints.filter(options,[q])
    if not options:break
    next_state[n]=options
   else:
    fixed.append(q)
    if solve(next_state):return True
    fixed.pop()
  return False
 solved=solve({name:opts for _,name,opts in choices});by={b['inst']:b for b in fixed};errors=[]
 if solved:
  for i,b in enumerate(fixed):
   for q in fixed[i+1:]:
    if max(separation(b,q))<5.4-1e-6:errors.append([b['inst'],q['inst']])
 report=dict(schema='opentallas.qwen.compressed-native-tile.v1',status='RECTANGLE_CANDIDATE_REQUIRES_ACTUAL_PIN_TIMING'if solved else'SEARCH_LIMIT_REACHED_NO_FEASIBLE_CANDIDATE'if count>300000 else'NO_SOLUTION_IN_BOUNDED_POOLS',source=str(a.inventory),actual_pin_constraints_applied=bool(constraints),source_sha256=hashlib.sha256(a.inventory.read_bytes()).hexdigest(),outline_um=[W,H],expected_placed_bodies=len(original),placed_bodies=len(fixed),body_5p4_clearance_errors=errors,search_nodes=count,displaced_conflicting_instances=[name for _,name,_ in choices],candidate_pool_sizes={name:len(options)for _,name,options in choices},children=[by[b['inst']]for b in children if b['inst']in by],banks=[by[b['inst']]for b in banks if b['inst']in by],reset_nodes=[by[b['inst']]for b in reset if b['inst']in by],changes=[dict(inst=n,before=original[n],after=b)for n,b in by.items()if b!=original[n]],qualification=False,remaining_gates=['All actual per-bit d/q pins including H→V source-master substitution','Native launch/capture/extrema and compensated phase','Reset source/target reassignment and parent pin ABI','Actual control/combinational logic homes and timing','Full source equivalence, fixed programme ages, all clock roots','Parent route TT/FF/DRC, pin escape and cut capacity','Whole-die DVM strip/head and current actualSU/IO/KV inventory'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ('status','expected_placed_bodies','placed_bodies','search_nodes','displaced_conflicting_instances','candidate_pool_sizes')}))
if __name__=='__main__':main()
