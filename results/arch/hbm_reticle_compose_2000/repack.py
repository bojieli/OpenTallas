#!/usr/bin/env python3
import json,math,time
from pathlib import Path
D=json.loads(Path('input.json').read_text());P=D['placement'];W,H=D['die_um'];G=43.2;CLEAR=21.6;TILE=216.0
start=time.time()
def area(a,b):
 return max(0,min(a['x']+a['w']+CLEAR,b['x']+b['w'])-max(a['x']-CLEAR,b['x']))*max(0,min(a['y']+a['h']+CLEAR,b['y']+b['h'])-max(a['y']-CLEAR,b['y']))
auto={k:r for k,r in P.items() if r['m'].startswith(('hbfd_rly_','hbfd_land_','hbfd_lh_','hbfd_lh0_'))}
cor={r['name']:r for r in D['corridors']}
base={k:r for k,r in P.items() if k not in D['replacements'] and k not in auto}
locked={k:r for k,r in base.items() if r['w']*r['h']>4e6 or r['m'].startswith(('ot_hbm3e_phy','ot_pdie_','hfd_ckgen','hfd_ep_'))}
movable={k:r for k,r in base.items() if k not in locked};placed={};evicted={};failed=[]
# One explicit greedy composition, with all large compute/PHY/off-die/clock-source
# bodies fixed and all six declared full-reticle corridor bands preserved.
for n,s in D['replacements'].items():
 old=P[n];best=None
 xs={i*388.8 for i in range(1,int((W-s['w'])/388.8)+1)}|{math.ceil(old['x']/G)*G}
 ys={i*388.8 for i in range(1,int((H-s['h'])/388.8)+1)}|{math.ceil(old['y']/G)*G}
 for x in sorted(xs):
  for y in sorted(ys):
   a={'x':x,'y':y,**s}
   if x+s['w']>W or y+s['h']>H:continue
   if any(area(a,b) for b in list(cor.values())+list(locked.values())+list(placed.values())):continue
   bs=[(k,area(a,b)) for k,b in movable.items() if area(a,b)]
   score=(sum(v for _,v in bs),len(bs),abs(x-old['x'])+abs(y-old['y']))
   if best is None or score<best[0]:best=(score,a,bs)
 if best is None:failed.append(n);continue
 _,a,bs=best;placed[n]=a
 for k,_ in bs:evicted[k]=movable.pop(k)
occupied={**locked,**movable,**placed,**{'corridor:'+k:v for k,v in cor.items()}};buckets={}
def keys(a):
 for i in range(int((a['x']-CLEAR)//TILE),int((a['x']+a['w']+CLEAR)//TILE)+1):
  for j in range(int((a['y']-CLEAR)//TILE),int((a['y']+a['h']+CLEAR)//TILE)+1):yield i,j
def add(n,a):
 occupied[n]=a
 for k in keys(a):buckets.setdefault(k,set()).add(n)
for n,a in list(occupied.items()):add(n,a)
def collides(a):
 seen=set()
 for k in keys(a):
  for n in buckets.get(k,()):
   if n not in seen:
    seen.add(n)
    if area(a,occupied[n]):return True
 return False
replaced={}
for n,r in sorted(evicted.items(),key=lambda t:-t[1]['w']*t[1]['h']):
 points={(i*TILE,j*TILE) for i in range(1,int((W-r['w'])/TILE)+1) for j in range(1,int((H-r['h'])/TILE)+1)}
 # Reuse the four vacated score grants on the exact43.2 lattice before consuming
 # additional clear space; shapes are unchanged and no density squeeze occurs.
 for q in ['SW','SE','NW','NE']:
  s=P['hb_idx__s_'+q]
  for i in range(int(math.ceil(s['x']/G)),int((s['x']+s['w']-r['w'])/G)+1):
   for j in range(int(math.ceil(s['y']/G)),int((s['y']+s['h']-r['h'])/G)+1):points.add((i*G,j*G))
 found=None
 for x,y in sorted(points,key=lambda p:abs(p[0]-r['x'])+abs(p[1]-r['y'])):
  a={**r,'x':x,'y':y}
  if x+r['w']<=W and y+r['h']<=H and not collides(a):found=a;break
 if found is None:failed.append(n)
 else:add(n,found);replaced[n]=found
out={'status':'CANDIDATE_REPLACE_READY_FOR_GEN_CLOCK_AND_RELAY_REBUILD' if not failed else 'CONCRETE_REPACK_HAS_UNPLACED_BODIES','manifest_sha256':D['manifest_sha256'],'die_um':[W,H],'new_parents':placed,'replaced_other_bodies':replaced,'evicted_bodies':list(evicted),'unplaced':failed,'unchanged_fixed_bodies':len(locked),'unchanged_other_bodies':len(movable),'auto_relay_rebuild_required':len(auto),'elapsed_s':time.time()-start,'explicit_open':['All moved block phase and link ages need normal GEN/S4/S8 repricing.','All covered old relays must be regenerated, not dropped.','New parents must implement actual feedthrough corridors; bounding rectangles alone do not establish them.','No outline was changed or functional unit removed; this is one concrete composition attempt, not signoff.']}
Path('repack.json').write_text(json.dumps(out,indent=1)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['replaced_other_bodies','evicted_bodies']}))
