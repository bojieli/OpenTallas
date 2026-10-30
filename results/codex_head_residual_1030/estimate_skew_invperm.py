import sys,json,collections,copy
from pathlib import Path
sys.path.insert(0,sys.argv[1]);import geom_rules as G
D=G.Design(sys.argv[2]);gd=json.load(open(sys.argv[3]));nm={c[6]:i for i,c in D.cells.items()};ids=[nm[n] for n in gd['groups']['a_early_skew']];orig={i:list(c) for i,c in D.cells.items()};items={}
for i in ids:
 for n in D.drives.get(i,[]):
  for e in D.nets[n][2]:
   if e[0]=='i' and not e[2] and D.kind(e[1])=='B':
    b=e[1];assert b not in items or items[b]==i;items[b]=i
caps={}
for b in items:
 todo=list(D.drives.get(b,[]));seen=set();ss=set()
 while todo:
  n=todo.pop()
  if n in seen:continue
  seen.add(n)
  for e in D.nets[n][2]:
   if e[0]!='i' or e[2]:continue
   if D.kind(e[1])=='S':ss.add(e[1])
   elif D.kind(e[1]) in ('B','L'):todo.extend(D.drives.get(e[1],[]))
 caps[b]=ss
best=None
for mode in ['launch','mid']:
 for size in [5,10,20,40]:
  cls=collections.defaultdict(list);goal={}
  for b,i in items.items():
   x,y=G.ctr(orig[i])
   if mode=='mid' and caps[b]:
    cs=[G.ctr(orig[j]) for j in caps[b]];x=(x+sum(v[0] for v in cs)/len(cs))/2;y=(y+sum(v[1] for v in cs)/len(cs))/2
   goal[b]=(x,y);cls[(orig[b][1],int(y//size))].append(b)
  mapping={}
  for key,bs in cls.items():
   targets=sorted(bs,key=lambda b:goal[b]);slots=sorted(bs,key=lambda b:G.ctr(orig[b]))
   for b,slot in zip(targets,slots):
    c=orig[b].copy();c[2:6]=orig[slot][2:6];D.cells[b]=c;mapping[b]=slot
  m=G.demand_metrics(D,'M7');score=max(m['channel_h_max'],m['channel_v_max'],m['col_v_max']);print(mode,size,len(mapping),m,flush=True)
  if best is None or score<best[0]:best=(score,mode,size,m,mapping.copy())
  D.cells={i:c.copy() for i,c in orig.items()}
score,mode,size,m,mapping=best
out=dict(kind='READ_ONLY_SAME_MASTER_COMB_SLOT_PERMUTATION',score=score,mode=mode,bin_um=size,metrics=m,pairs=[dict(cell=orig[i][6],slot=orig[j][6],master=orig[i][1]) for i,j in mapping.items() if i!=j],all_ff_and_clock_sites_unchanged=True)
Path(sys.argv[4]).write_text(json.dumps(out,indent=1)+'\n');print('BEST',score,mode,size,'moved',len(out['pairs']))
