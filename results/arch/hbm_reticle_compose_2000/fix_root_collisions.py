#!/usr/bin/env python3
"""Repair only named root collisions in the existing full-count candidate."""
import hashlib,json,time,math
from pathlib import Path
start=time.time()
D=json.loads(Path('input.json').read_text());P=D['placement'];W,H=D['die_um']
S=json.loads(Path('source_geometry.json').read_text())
C=json.loads(Path('column_geometry.json').read_text())
R=json.loads(Path('root_sites.json').read_text())
O=json.loads(Path('columns_repack.json').read_text())
CLEAR,TILE,GRID=21.6,432.,216.
auto=O['automatic_relays_requiring_regeneration']
fixed={n:dict(a) for n,a in P.items() if n not in auto and n!='hc_eng'}
moved=O['existing_bodies_moved'];fixed.update(moved)
placed=O['placed_service_envelopes'];rectangles=O['individual_source_rectangles']
def hit(a,b):
 return a['x']-CLEAR<b['x']+b['w'] and b['x']<a['x']+a['w']+CLEAR and a['y']-CLEAR<b['y']+b['h'] and b['y']<a['y']+a['h']+CLEAR
roots={s['region']:dict(x=s['keepout'][0],y=s['keepout'][1],w=s['keepout'][2]-s['keepout'][0],h=s['keepout'][3]-s['keepout'][1]) for s in R['sites']}
named=[n for n,a in placed.items() if any(hit(a,b) for b in roots.values())]
for n,a in placed.items():
 if n not in named:fixed['service:'+n]=a
for n,a in roots.items():fixed['root:'+n]=a
for i,b in enumerate(S['last_step_postcut_bands']):
 fixed['corridor:'+str(i)]=dict(x=b['start_um'] if b['axis']=='x' else 0,y=b['start_um'] if b['axis']=='y' else 0,w=b['width_um'] if b['axis']=='x' else W,h=b['width_um'] if b['axis']=='y' else H)
locked={n for n,a in fixed.items() if n.startswith(('service:','root:','corridor:','hb_idx__s_')) or a['w']*a['h']>4e6 or a.get('m','').startswith(('ot_hbm3e_phy','ot_pdie_','hfd_ckgen','hfd_ep_'))}
buckets={}
def keys(a):
 for x in range(int((a['x']-CLEAR)//TILE),int((a['x']+a['w']+CLEAR)//TILE)+1):
  for y in range(int((a['y']-CLEAR)//TILE),int((a['y']+a['h']+CLEAR)//TILE)+1):yield x,y
def add(n,a):
 fixed[n]=a
 for k in keys(a):buckets.setdefault(k,set()).add(n)
def remove(n):
 a=fixed.pop(n)
 for k in keys(a):buckets[k].discard(n)
 return a
for n,a in list(fixed.items()):add(n,a)
def blockers(a,all_locked=False):
 seen=set();out=[]
 for k in keys(a):
  for n in buckets.get(k,()):
   if n not in seen:
    seen.add(n)
    if hit(a,fixed[n]):
     if all_locked or n in locked:return None
     out.append(n)
 return out
anchors=[(x*GRID,y*GRID) for x in range(1,int(W/GRID)) for y in range(1,int(H/GRID))]
evicted={};failed=[];repairs={}
for n in named:
 old=placed[n];best=None
 for x,y in anchors:
  a=dict(old,x=x,y=y)
  if x+a['w']>W or y+a['h']>H:continue
  bs=blockers(a)
  if bs is None:continue
  score=(sum(fixed[k]['w']*fixed[k]['h'] for k in bs),len(bs),abs(x-old['x'])+abs(y-old['y']))
  if best is None or score<best[0]:best=score,a,bs
 if best is None:failed.append(n);continue
 _,a,bs=best
 for k in bs:evicted[k]=remove(k)
 placed[n]=a;add('service:'+n,a);locked.add('service:'+n)
 repairs[n]=dict(before=old,after=a,delta_um=[a['x']-old['x'],a['y']-old['y']])
 if n!='hc_eng':
  for r in C['rectangles']:rectangles[n+'/'+r['name']]=dict(r,x_um=round(a['x']+r['x_um'],6),y_um=round(a['y']+r['y_um'],6))
for n,old in sorted(evicted.items(),key=lambda v:-v[1]['w']*v[1]['h']):
 for x,y in sorted(anchors,key=lambda p:abs(p[0]-old['x'])+abs(p[1]-old['y'])):
  a=dict(old,x=x,y=y)
  if x+a['w']<=W and y+a['h']<=H and blockers(a,True)==[]:
   moved[n]=a;add(n,a);break
 else:failed.append(n)
root_hits=[(n,r) for n,a in {**placed,**moved}.items() for r,b in roots.items() if hit(a,b)]
O.update(status='FULL_COUNT_DIAGNOSTIC_WITH_45_ROOT_KEEPOUTS' if not failed and not root_hits else 'NAMED_ROOT_REPAIR_INCOMPLETE',placed_service_envelopes=placed,individual_source_rectangles=rectangles,existing_bodies_moved=moved,named_root_repair_transforms=repairs,root_keepout_sha256=hashlib.sha256(Path('root_sites.json').read_bytes()).hexdigest(),root_keepout_count=len(roots),remaining_root_intersections=root_hits,repair_failures=failed,baseline_roots_within_existing_bodies=R.get('inside_blocks'),active_clock_inputs_per_quarter=143,clock_scope=C['clock_scope'],runtime_s=time.time()-start)
Path('columns_root_corrected.json').write_text(json.dumps(O,indent=1)+'\n')
print(json.dumps({k:O[k] for k in ['status','root_keepout_count','remaining_root_intersections','repair_failures','runtime_s']}))
