from pathlib import Path
import json,gzip,sys,collections,bisect
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
T=json.load(open(R/'targets.json'));cells=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];by={c[0]:c for c in cells};rows=json.load(open(P/'rows.json'));rs=collections.defaultdict(list)
for row in rows:rs[row['origin_dbu'][1]].append(row)
# Independent interval sweep of the complete projected native population, including all137673 TAPs.
allboxes=[];rowbad=[];masterbad=[];byrow=collections.defaultdict(list);ys=sorted(rs)
for c in cells:
 name=c[0];t=T.get(name);bb=t['bbox_dbu']if t else c[2];allboxes.append((name,bb));
 if t:
  old=c[2];oldor={r['orient']for r in rs[old[1]]};legal=[r for r in rs[bb[1]]if r['bbox_dbu'][0]<=bb[0]and bb[2]<=r['bbox_dbu'][2]and bb[3]<=r['bbox_dbu'][3]and(bb[0]-r['origin_dbu'][0])%r['spacing_dbu']==0 and r['orient']in oldor]
  if not legal:rowbad.append(name)
  if t['master']!=c[1]or t['orient']!=c[4]or[bb[2]-bb[0],bb[3]-bb[1]]!=[old[2]-old[0],old[3]-old[1]]:masterbad.append(name)
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:byrow[y].append((bb[0],bb[2],name))
collisions=[];seen=set()
for y,ints in byrow.items():
 active=[]
 for a,b,name in sorted(ints):
  active=[p for p in active if p[1]>a]
  for x,z,other in active:
   if name not in T and other not in T:continue
   key=tuple(sorted((name,other)))
   if key not in seen:seen.add(key);collisions.append(dict(names=key,row_y_dbu=y))
  active.append((a,b,name))
D=G.Design(P/'geom.tsv');idof={c[6]:i for i,c in D.cells.items()};oldxy={i:G.ctr(c)for i,c in D.cells.items()};
for name,t in T.items():
 i=idof[name];c=list(D.cells[i]);c[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[i]=tuple(c)
demand=G.demand_metrics(D,max_layer='M7',min_layer='M2');land=G.land_ring_captures(D,json.load(open(P/'land_slots.json')),json.load(open(P/'face_guard.json')));ring=[]
for p in D.pins:
 if not p['name'].startswith('ft2_i['):continue
 ids=land['caps'][p['name']];ring.append(dict(pin=p['name'],slots=len(ids),max_um=max(abs(G.ctr(D.cells[i])[0]-p['x'])+abs(G.ctr(D.cells[i])[1]-p['y'])for i in ids)))
rootcache={}
def clockroot(n,seen=frozenset()):
 if n in rootcache:return rootcache[n]
 if n in seen:return None
 dr=D.nets[n][1]
 if not dr:return None
 if dr[0]=='p':return dr[1]
 if D.kind(dr[1])!='B':return None
 ins=[nn for nn,ck in D.cell_in.get(dr[1],[])];res=clockroot(ins[0],seen|{n})if len(ins)==1 else None;rootcache[n]=res;return res
clock=[]
for name,t in T.items():
 i=idof[name];nets=[n for n,ck in D.cell_in.get(i,[])if ck];rt=clockroot(nets[0])if len(nets)==1 else None;p=D.pin_by_k.get(rt);xy=G.ctr(D.cells[i]);old=oldxy[i]
 clock.append(dict(name=name,family=t['family'],root=p['name']if p else None,root_xy=[p['x'],p['y']]if p else None,old_root_distance_um=abs(old[0]-p['x'])+abs(old[1]-p['y'])if p else None,new_root_distance_um=abs(xy[0]-p['x'])+abs(xy[1]-p['y'])if p else None))
summary={}
for family in sorted({x['family']for x in clock}):
 q=[x for x in clock if x['family']==family];known=[x for x in q if x['root']];summary[family]=dict(count=len(q),known_clock_roots=len(known),root_names=sorted({x['root']for x in known}),old_direct_root_distance_max_um=max((x['old_root_distance_um']for x in known),default=None),new_direct_root_distance_max_um=max((x['new_root_distance_um']for x in known),default=None),new_max_witness=max(known,key=lambda x:x['new_root_distance_um'])if known else None)
out=dict(scope='Independent exact integer native-row/site/master/orientation/full-footprint sweep + projected graph demand from unchanged source; MODEL only, no CAD',targets=len(T),native_population=len(cells),tap_count=sum(c[1].startswith('TAPCELL')for c in cells),row_site_failures=rowbad,master_orient_dimension_failures=masterbad,new_target_footprint_overlaps=collisions,ft2_slot_pins=len(ring),ft2_farthest_slot_max_um=max(x['max_um']for x in ring),ft2_over150=sum(x['max_um']>150for x in ring),projected_placed_M2M7_demand=demand,actual_clock_root_distance_INFO=summary,holds=['savedactualGRT4843 unchanged; projectedcuts are no routing result','clock roots/distances are explicit preCTSINFO, not phase/leaf/internalclock qualification','actualPGshapes/nets unchanged; futurePGlanding/wholeDBguard remains;95696bufferPGnull terms explicit','E/W61of123bins remain2partialfaceFAIL; actualsparsefill remains'])
(R/'model_collection.json').write_text(json.dumps(out,indent=2));(R/'moved_clock_root_distances_INFO.json').write_text(json.dumps(clock,indent=2));print(json.dumps(out,indent=2))
