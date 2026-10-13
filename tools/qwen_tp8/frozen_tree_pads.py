#!/usr/bin/env python3
"""Add registered tree pads without re-planning existing chains.
Preserve every original instance and non-tree binding. First repair over-reach tree
segments, then balance the actual resulting graph. Generated pin-centroid reach is
checked; actual macro lattice, clock regeneration, real views and STA remain gates.
"""
import argparse, collections, json, math, re, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_die_seam'))
import extract,tree_alignment
ap=argparse.ArgumentParser();ap.add_argument('physical_model');ap.add_argument('die_v');ap.add_argument('out');a=ap.parse_args()
out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
D=json.load(open(a.physical_model));I={i['n']:i for i in D['insts']};P=D['endpoint_pos'];original=Path(a.die_v).read_text();inst,bus=extract.parse(a.die_v)
chains={};width={}
for b,d in bus.items():
 if d['cls']!='tree':continue
 assert len(d['src'])==len(d['dst'])==1
 chains[b]=(d['src'][0],[r['name'] for r in d['relays']],d['dst'][0]);width[b]=d['w']
G=collections.defaultdict(list);new=[];newclock={};serial=0

def rect(i):return i['x'],i['y'],i['x']+i['w'],i['y']+i['h']
def add(i):
 x,y,X,Y=rect(i)
 for gx in range(int(x//250),int(X//250)+1):
  for gy in range(int(y//250),int(Y//250)+1):G[gx,gy].append((x,y,X,Y))
for i in I.values():add(i)

def free(i):
 x,y,X,Y=rect(i)
 if min(x,y)<0 or X>31785.696 or Y>25870.32:return False
 for gx in range(int(x//250),int(X//250)+1):
  for gy in range(int(y//250),int(Y//250)+1):
   for u,v,U,V in G[gx,gy]:
    if u<X+.024 and x<U+.024 and v<Y+.024 and y<V+.024:return False
 return True

def mh(p,q):return abs(p[0]-q[0])+abs(p[1]-q[1])
# Prefer small existing two-face relay masters; no new abstract or assumed pin geometry.
T={}
for n,i in I.items():
 if i['m'].startswith('qfd_rly_512_') and i.get('orient','R0')=='R0' and n+'.a' in P and n+'.b' in P:
  T.setdefault(i['m'],(i,[P[n+'.a'][0]-i['x'],P[n+'.a'][1]-i['y']],
                           [P[n+'.b'][0]-i['x'],P[n+'.b'][1]-i['y']]))
assert T

def allocate(src,dst,count,clk):
 global serial
 names=[];prev=P[src];sink=P[dst]
 for j in range(count):
  target=[prev[k]+(sink[k]-prev[k])/(count-j+1) for k in (0,1)];chosen=None
  for ring in range(24):
   offsets=[(0,0)] if not ring else [(u*56,v*32) for u in range(-ring,ring+1) for v in range(-ring,ring+1) if max(abs(u),abs(v))==ring]
   best=None
   for dx,dy in offsets:
    for master,(sample,aa,bb) in T.items():
     x=sample['x']+round((target[0]+dx-sample['w']/2-sample['x'])/.216)*.216
     y=sample['y']+round((target[1]+dy-sample['h']/2-sample['y'])/2.16)*2.16
     r=dict(n='pending',m=master,x=round(x,6),y=round(y,6),w=sample['w'],h=sample['h'],orient='R0')
     pa=[x+aa[0],y+aa[1]];pb=[x+bb[0],y+bb[1]]
     if mh(prev,pa)>498 or mh(pb,sink)>498*(count-j) or not free(r):continue
     score=mh(pb,target)+.1*mh(prev,pa)+.05*mh(pb,sink)
     if best is None or score<best[0]:best=(score,r,pa,pb)
   if best:chosen=best;break
  if chosen is None:raise RuntimeError(f'No <=498um legal pad slot: {src}->{dst}, stage{j}/{count}')
  _,r,pa,pb=chosen;serial+=1;r['n']=f'cx_tree_pad_{serial}';I[r['n']]=r;D['insts'].append(r);new.append(r['n']);add(r)
  P[r['n']+'.a']=pa;P[r['n']+'.b']=pb;newclock[r['n']]=clk;names.append(r['n']);prev=pb
 assert mh(prev,sink)<=498+1e-6
 return names

def allocate_legal(src,dst,count,clk,extra=12):
 global serial
 first=serial;start=len(new)
 for total in range(count,count+extra):
  try:return allocate(src,dst,total,clk)
  except RuntimeError:
   # Undo a partial attempt before changing depth. No orphan placement or clock.
   for n in list(new[start:])[::-1]:
    r=I[n];x,y,X,Y=rect(r)
    for gx in range(int(x//250),int(X//250)+1):
     for gy in range(int(y//250),int(Y//250)+1):G[gx,gy].remove((x,y,X,Y))
    del I[n];newclock.pop(n);P.pop(n+'.a');P.pop(n+'.b');D['insts'].pop()
   del new[start:];serial=first
 raise RuntimeError(f'No legal registered detour after 12 depth candidates: {src}->{dst}')

def balance_distributed(src,rs,dst,count,clk):
 # A delay may sit on any chain segment. Spread it across the existing corridor
 # instead of concentrating every frame at a crowded tile input.
 rs=list(rs);remaining=count
 for batch in (3,2,1):
  for sweep in range(8):
   if not remaining:break
   ends=[src]+[r+'.b' for r in rs]
   sinks=[r+'.a' for r in rs]+[dst]
   order=sorted(range(len(ends)),key=lambda k:-mh(P[ends[k]],P[sinks[k]]))
   changed=False
   for k in order:
    n=min(batch,remaining)
    try:added=allocate_legal(ends[k],sinks[k],n,clk,extra=1)
    except RuntimeError:continue
    rs[k:k]=added;remaining-=n;changed=True
    # Recompute segment indices after each insertion.
    break
   if not changed:break
  if not remaining:break
 if remaining:
  raise RuntimeError(f'No distributed space for {remaining}/{count} pads: {src}->{dst}')
 return rs

def emit(path):
 binds={};decl=[];treeb=[]
 for b,(src,rs,dst) in chains.items():
  nets=[b]+[b+f'__r{k}' for k in range(1,len(rs)+1)]
  decl += [f'  wire [{width[b]-1}:0] {n};' for n in nets]
  binds[src]=nets[0];binds[dst]=nets[-1]
  points=[src]+sum(([r+'.a',r+'.b'] for r in rs),[])+[dst]
  for k,r in enumerate(rs):binds[r+'.a']=nets[k];binds[r+'.b']=nets[k+1]
  for k,n in enumerate(nets):
   e0=src if not k else rs[k-1]+'.b';e1=dst if k==len(rs) else rs[k]+'.a'
   treeb.append([n[2:],'tree_block',width[b],[e0.split('.'),e1.split('.')]])
 byinst=collections.defaultdict(dict)
 for ep,net in binds.items():
  nn,p=ep.split('.');byinst[nn][p]=net
 text=re.sub(r'^\s*wire \[\d+:0\] n_tree_\w+;\n','',original,flags=re.M)
 def rewrite(m):
  master,n,ports=m.groups()
  for p,net in byinst[n].items():
   ports=re.sub(r'\.'+re.escape(p)+r'\(\w*\)',f'.{p}({net})',ports)
  return f'  {master} {n} ({ports});'
 text=re.sub(r'^\s+(\w+) (\w+) \((.*)\);$',rewrite,text,flags=re.M)
 lines=decl+[f"  {I[n]['m']} {n} (.a({binds[n+'.a']}), .b({binds[n+'.b']}), .ck({newclock[n]}));" for n in new]
 text=text.replace('endmodule','\n'.join(lines)+'\nendmodule');Path(path).write_text(text)
 return treeb

# Repair reach without moving any old relay; insert into the affected stage only.
repairs=0
for b,(src,rs,dst) in list(chains.items()):
 expanded=[];prev=src;clk=inst[dst.split('.')[0]][1]['ck']
 for next_ep in [r+'.a' for r in rs]+[dst]:
  distance=mh(P[prev],P[next_ep]);n=max(0,math.ceil(distance/450)-1)
  if n:
   added=allocate_legal(prev,next_ep,n,clk);expanded+=added;repairs+=len(added)
  if next_ep!=dst:
   r=next_ep.split('.')[0];expanded.append(r);prev=r+'.b'
 chains[b]=(src,expanded,dst)
emit(out/'reach_repaired.v');before=tree_alignment.audit(str(out/'reach_repaired.v'))
current=before;rounds=[]
for iteration in range(12):
 if current['misaligned']==0:break
 prior=len(new)
 for b,pad in sorted(current['proposed_pads'].items(),key=lambda t:-t[1]['extra_cycles']):
  src,rs,dst=chains[b];prev=rs[-1]+'.b' if rs else src;clk=inst[dst.split('.')[0]][1]['ck']
  rs=balance_distributed(src,rs,dst,pad['extra_cycles'],clk)
  chains[b]=(src,rs,dst)
 emit(out/f'balance_round{iteration}.v');current=tree_alignment.audit(str(out/f'balance_round{iteration}.v'))
 rounds.append(dict(round=iteration,added=len(new)-prior,misaligned=current['misaligned']))
 if current['misaligned']==0:break
treeb=emit(out/'die.v');after=tree_alignment.audit(str(out/'die.v'))
assert after['misaligned']==0,dict(misaligned=after['misaligned'],rounds=rounds)
hops=[]
for b,c,w,eps in treeb:
 e0,e1=['.'.join(e) for e in eps];dist=mh(P[e0],P[e1]);hops.append(dict(bus=b,stage_um=dist));assert dist<=500+1e-6,(b,dist)
D['buses']=[b for b in D['buses'] if not b[0].startswith('tree_')]+treeb
for n,clk in newclock.items():
 for b in D['buses']:
  if 'n_'+b[0]==clk:b[3].append([n,'ck']);break
D['endpoint_pos']=P
(out/'physical_model.json').write_text(json.dumps(D))
(out/'rom_tp8b.json').write_text(json.dumps(dict(insts=D['insts'],buses=[(b,c,w,[e[0] for e in eps]) for b,c,w,eps in D['buses']])))
rec=dict(source_model=a.physical_model,new_relays=len(new),reach_repair_relays=repairs,balance_rounds=rounds,
         balance_relays=len(new)-repairs,before_misaligned=before['misaligned'],after_misaligned=after['misaligned'],
         max_tree_stage_um=max(h['stage_um'] for h in hops),existing_instances_moved=0,
         limitation='Generated pin-centroid reach only; actual macro-lattice, clock regeneration, real abstract views, full cuts, STA and exact die seam gate remain required')
(out/'summary.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
