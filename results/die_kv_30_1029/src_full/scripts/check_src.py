#!/usr/bin/env python3
"""DIE-KV-30-SRC readback: std-cell bodies vs partition master OBS (all layers),
instance/placement census, native signal-pin geometry hash per master, PG pin census.
Run: openroad -python -no_init -exit check_src.py --odb X.odb --out Y.json [--plan-hard constraints.json]"""
import argparse,collections,hashlib,json
import odb
p=argparse.ArgumentParser();p.add_argument('--odb',required=True);p.add_argument('--out',required=True);p.add_argument('--hard',default=None);a=p.parse_args()
d=odb.dbDatabase.create();odb.read_db(d,a.odb);b=d.getChip().getBlock()
def R(r):return (r.xMin(),r.yMin(),r.xMax(),r.yMax())
def RB(x):return (x.xMin(),x.yMin(),x.xMax(),x.yMax())
OR={'R0':lambda x,y:(x,y),'R90':lambda x,y:(-y,x),'R180':lambda x,y:(-x,-y),'R270':lambda x,y:(y,-x),'MY':lambda x,y:(-x,y),'MX':lambda x,y:(x,-y),'MXR90':lambda x,y:(y,x),'MYR90':lambda x,y:(-y,-x)}
def mk(i):
 o=str(i.getOrient());f=OR[o];m=i.getMaster();W,H=m.getWidth(),m.getHeight();bb=RB(i.getBBox())
 c=[f(x,y) for x,y in((0,0),(W,H))];dx=bb[0]-min(p[0] for p in c);dy=bb[1]-min(p[1] for p in c)
 def T(box):
  c=[f(x,y) for x,y in((box[0],box[1]),(box[2],box[3]))];return (min(p[0] for p in c)+dx,min(p[1] for p in c)+dy,max(p[0] for p in c)+dx,max(p[1] for p in c)+dy)
 return T
def xf(T,box):return T(box)
blocks=[];cells=[]
for i in b.getInsts():
 m=i.getMaster()
 if m.isBlock():blocks.append(i)
 else:cells.append(i)
# master signal-pin geometry hash (all non-PG MPins), master OBS census
mh={};mobs={}
for m in {i.getMaster().getName():i.getMaster() for i in blocks}.values():
 sig=[];pg=collections.Counter()
 for t in m.getMTerms():
  for mp in t.getMPins():
   for bx in mp.getGeometry():
    g=(t.getName(),bx.getTechLayer().getName() if bx.getTechLayer() else None,*RB(bx))
    if t.getSigType() in ('POWER','GROUND'):pg[t.getName()]+=1
    else:sig.append(g)
 sig.sort();mh[m.getName()]=dict(signal_pin_shapes=len(sig),signal_pin_sha=hashlib.sha256(json.dumps(sig).encode()).hexdigest(),pg_pin_shapes=dict(pg),size=(m.getWidth(),m.getHeight()))
 mobs[m.getName()]=[(o.getTechLayer().getName() if o.getTechLayer() else 'via',*RB(o)) for o in m.getObstructions()]
 mh[m.getName()]['obs']=len(mobs[m.getName()])
B=20000;grid=collections.defaultdict(list);bad_xf=0
for i in blocks:
 T=mk(i);m=i.getMaster()
 if xf(T,(0,0,m.getWidth(),m.getHeight()))!=RB(i.getBBox()):bad_xf+=1
 for o in mobs[m.getName()]:
  r=xf(T,o[1:])
  for gx in range(r[0]//B,(r[2]-1)//B+1):
   for gy in range(r[1]//B,(r[3]-1)//B+1):grid[gx,gy].append((o[0],r,i.getName()))
hard=[]
if a.hard:
 hard=[tuple(r[1:]) for r in json.load(open(a.hard))['hard_forbidden']]
def hit(r,q):return r[0]<q[2] and q[0]<r[2] and r[1]<q[3] and q[1]<r[3]
hb=collections.defaultdict(list)
for q in hard:
 for gx in range(q[0]//B,(q[2]-1)//B+1):
  for gy in range(q[1]//B,(q[3]-1)//B+1):hb[gx,gy].append(q)
res=collections.Counter();per_layer=collections.Counter();samples=[];hardhit=collections.Counter()
for c in cells:
 kind='clock' if c.getName().startswith('ck_') else 'provider'
 res[kind+'_cells']+=1;r=RB(c.getBBox());keys=[(gx,gy) for gx in range(r[0]//B,(r[2]-1)//B+1) for gy in range(r[1]//B,(r[3]-1)//B+1)]
 ls=set()
 for k in keys:
  for lay,q,owner in grid[k]:
   if hit(r,q):
    ls.add(lay)
    if len(samples)<20:samples.append(dict(cell=c.getName(),layer=lay,owner=owner,cell_bbox=r,obs=q))
 for lay in ls:per_layer[kind+':'+lay]+=1
 if ls:res[kind+'_hit_any_obs']+=1
 if 'M1' in ls:res[kind+'_hit_M1_obs']+=1
 if any(hit(r,q) for k in keys for q in hb[k]):hardhit[kind]+=1
pl=sorted((i.getName(),i.getMaster().getName(),*i.getLocation(),str(i.getOrient()),str(i.getPlacementStatus())) for i in b.getInsts())
blk=sorted((i.getName(),i.getMaster().getName(),*i.getLocation(),str(i.getOrient())) for i in blocks)
ck=sorted((i.getName(),i.getMaster().getName(),*i.getLocation(),str(i.getOrient())) for i in cells if i.getName().startswith('ck_'))
pv=sorted((i.getName(),i.getMaster().getName(),*i.getLocation(),str(i.getOrient())) for i in cells if not i.getName().startswith('ck_'))
H=lambda x:hashlib.sha256(json.dumps(x).encode()).hexdigest()
bt=collections.Counter(str(o.getBBox().getTechLayer().getName()) if o.getBBox().getTechLayer() else 'none' for o in b.getObstructions())
out=dict(odb=a.odb,insts=len(pl),block_insts=len(blocks),std_cells=len(cells),counts=dict(res),obs_hits_by_layer=dict(per_layer),hard_core_hits=dict(hardhit),hard_rects=len(hard),bad_transform=bad_xf,
 block_place_sha=H(blk),clock_place_sha=H(ck),provider_place_sha=H(pv),block_obstructions=dict(bt),nets=len(b.getNets()),masters=mh,samples=samples)
json.dump(out,open(a.out,'w'),indent=1);print(json.dumps({k:v for k,v in out.items() if k not in('masters','samples')},indent=1))
