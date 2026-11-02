"""DISABLED exact-owned DATA-cone geometry proposal. All FFs/held infrastructure immutable; no CAD."""
from pathlib import Path
import json,gzip,sys,collections,bisect,math,re
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
C=[json.loads(x)for x in gzip.open(P/'cells.jsonl.gz','rt')];N={c[0]:i for i,c in enumerate(C)};F=json.load(open(P/'FF_targets.json'));graph=json.load(gzip.open(P/'classification_graph.json.gz','rt'));assert graph['names']==[c[0]for c in C];E=set(graph['eligible']);nets=graph['net_data'];ins={int(k):v for k,v in graph['ins'].items()};outs={int(k):v for k,v in graph['outs'].items()};rows=json.load(open(P/'rows.json'));core=json.load(open(P/'native_census.json'))['core_dbu'];ys=sorted({r['origin_dbu'][1]for r in rows});rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for r in rows:rs[r['origin_dbu'][1]].append(r)
print('INPUT_OWNED_DATA',len(E),'CELLS',len(C),'FFtargets',len(F),flush=True)
origxy={i:((c[2][0]+c[2][2])/2000,(c[2][1]+c[2][3])/2000)for i,c in enumerate(C)};newxy=dict(origxy)
for name,t in F.items():newxy[N[name]]=t['xy_um']
PXY={}
for name,io,sig,net,boxes in json.load(open(P/'BTerms.json')):
 if boxes:PXY[name]=((min(b[0]for l,b in boxes)+max(b[2]for l,b in boxes))/2000,(min(b[1]for l,b in boxes)+max(b[3]for l,b in boxes))/2000)
# Boundaries of the actual eligible subgraph remain immutable. Unique first-boundary anchors prevent path-multiplicity weighting.
pred=collections.defaultdict(set);succ=collections.defaultdict(set);upbase=collections.defaultdict(set);dnbase=collections.defaultdict(set)
for i in E:
 for ni,pin in ins.get(i,[]):
  for typ,j,p in nets[ni][3]:
   if typ=='c'and j in E:pred[i].add(j);succ[j].add(i)
   elif typ=='c':upbase[i].add(('c',j))
   elif j in PXY:upbase[i].add(('p',j))
 for ni in outs.get(i,[]):
  for typ,j,p in nets[ni][4]:
   if typ=='c'and j in E:succ[i].add(j);pred[j].add(i)
   elif typ=='c':dnbase[i].add(('c',j))
   elif j in PXY:dnbase[i].add(('p',j))
left={i:len(pred[i])for i in E};q=collections.deque(i for i in E if left[i]==0);order=[]
while q:
 i=q.popleft();order.append(i)
 for j in succ[i]:left[j]-=1;q.append(j)if left[j]==0 else None
assert len(order)==len(E),'eligible graph must be acyclic'
up={};down={}
for i in order:
 s=set(upbase[i])
 for j in pred[i]:s.update(up[j])
 up[i]=s
print('UPSTREAM_ANCHORS_READY',len(up),flush=True)
for i in reversed(order):
 s=set(dnbase[i])
 for j in succ[i]:s.update(down[j])
 down[i]=s
print('DOWNSTREAM_ANCHORS_READY',len(down),flush=True)
# Shared-control hyperedges count once. Native fanout downweights immutable common boundaries, without moving them.
fanout={i:sum(len(nets[n][4])for n in outs.get(i,[]))for i in range(len(C))};pfanout=collections.Counter()
for nname,sig,dnt,drivers,sinks in nets:
 for typ,j,pin in drivers:
  if typ=='p':pfanout[j]+=len(sinks)
def anchors_desired(i):
 anchors=up[i]|down[i];cx,cy=origxy[i];a=[]
 for typ,j in anchors:
  old=origxy[j]if typ=='c'else PXY[j];new=newxy[j]if typ=='c'else old;distance=max(2.,abs(cx-old[0])+abs(cy-old[1]));degree=1
  if typ=='p':degree=max(1,pfanout.get(j,1))
  elif C[j][0]not in F:degree=max(1,fanout.get(j,1))
  w=1/(distance*math.sqrt(degree));a.append((w,new))
 assert a,('no physical boundary anchors',C[i][0])
 sw=sum(w for w,p in a);return[sum(w*p[k]for w,p in a)/sw for k in(0,1)]
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for i,c in enumerate(C):
 if i in E:continue
 occupy(F[c[0]]['bbox_dbu']if c[0]in F else c[2])
band_reservations=json.load(open(P/'other_declared_band_reservations.json'))['rectangles']
for band in band_reservations:occupy(band['bbox_dbu'])
for y in occ:occ[y].sort()
desired={i:anchors_desired(i)for i in E};targets={};fail=[];MAX_JOG=40000
# Concrete single design: closest free actual native row/site within40um of the dataflow-derived point.
# Every original master/orientation is retained; rows must have the original supply phase.
for i in sorted(E,key=lambda i:(-(C[i][2][2]-C[i][2][0]),-fanout.get(i,0),C[i][0])):
 c=C[i];bb=c[2];w=bb[2]-bb[0];h=bb[3]-bb[1];phase={r['orient']for r in rs[bb[1]]};cx,cy=[v*1000 for v in desired[i]];cx=max(core[0]+w/2,min(core[2]-w/2,cx));cy=max(core[1]+h/2,min(core[3]-h/2,cy));best=None
 for y in ys[bisect.bisect_left(ys,cy-h/2-MAX_JOG):bisect.bisect_right(ys,cy-h/2+MAX_JOG)]:
  dy=abs(y+h/2-cy)
  if dy>MAX_JOG:continue
  for row in rs[y]:
   if row['orient']not in phase:continue
   lo=max(core[0],row['bbox_dbu'][0],cx-w/2-(MAX_JOG-dy));hi=min(core[2]-w,row['bbox_dbu'][2]-w,cx-w/2+(MAX_JOG-dy))
   if lo>hi:continue
   free=[];last=lo
   for a,b in occ[y]:
    if b<=lo:continue
    if a>=hi+w:break
    if a>last:free.append((last,min(a,hi+w)))
    last=max(last,b)
   if last<hi+w:free.append((last,hi+w))
   for a,b in free:
    step=row['spacing_dbu'];rx=row['origin_dbu'][0];ia=math.ceil((a-rx)/step);ib=math.floor((b-w-rx)/step)
    if ib<ia:continue
    k=min(ib,max(ia,round((cx-w/2-rx)/step)));x=rx+k*step;jog=abs(x+w/2-cx)+dy;key=(jog,y,x)
    if best is None or key<best[0]:best=(key,[x,y,x+w,y+h],row)
 if best is None:fail.append(dict(name=c[0],master=c[1],desired_um=desired[i],reason='no40um-jog native-phase row/site free footprint; no obstacle/phase waiver'));continue
 key,bb,row=best;occupy(bb)
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].sort()
 if len(targets)%2000==0:print('LEGAL_ALLOC_PROGRESS',len(targets),'failed',len(fail),flush=True)
 targets[c[0]]=dict(master=c[1],bbox_dbu=bb,orient=c[4],old_bbox_dbu=c[2],desired_um=desired[i],jog_um=key[0]/1000,row=row['name'],actual_status=c[5],actual_DNT=c[6]);newxy[i]=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000]
# Independent complete-population interval sweep; all FF poses and all non-owned cells are immutable by construction.
check=collections.defaultdict(list);badrows=[];badmasters=[]
for i,c in enumerate(C):
 t=targets.get(c[0]);bb=t['bbox_dbu']if t else F[c[0]]['bbox_dbu']if c[0]in F else c[2]
 if t:
  phase={r['orient']for r in rs[c[2][1]]};legal=[r for r in rs[bb[1]]if r['bbox_dbu'][0]<=bb[0]and bb[2]<=r['bbox_dbu'][2]and bb[3]<=r['bbox_dbu'][3]and(bb[0]-r['origin_dbu'][0])%r['spacing_dbu']==0 and r['orient']in phase]
  if not legal:badrows.append(c[0])
  if t['master']!=c[1]or t['orient']!=c[4]or[bb[2]-bb[0],bb[3]-bb[1]]!=[c[2][2]-c[2][0],c[2][3]-c[2][1]]:badmasters.append(c[0])
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:check[y].append((bb[0],bb[2],c[0]))
overlaps=[];seen=set()
for y,ints in check.items():
 active=[]
 for a,b,name in sorted(ints):
  active=[p for p in active if p[1]>a]
  for x,z,other in active:
   if name not in targets and other not in targets:continue
   pair=tuple(sorted((name,other)))
   if pair not in seen:seen.add(pair);overlaps.append(dict(names=pair,row_y_dbu=y))
  active.append((a,b,name))
D=G.Design(P/'geom.tsv');idof={c[6]:i for i,c in D.cells.items()}
def setposes(ts):
 for name,t in ts.items():
  i=idof[name];c=list(D.cells[i]);c[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[i]=tuple(c)
def prior_hot_cut():
 total=0.;drivers=collections.Counter();records={};without_data=0.;data_touched=0.
 for ni,(sig,dr,sk)in enumerate(D.nets):
  if sig=='CLOCK':continue
  pts=[];touch=False
  for ep in([dr]if dr else[])+sk:
   if ep[0]=='p':
    pp=D.pin_by_k.get(ep[1])
    if pp:pts.append((pp['x'],pp['y']))
   elif ep[1]in D.cells:
    cc=D.cells[ep[1]];pts.append(G.ctr(cc));touch=touch or cc[6]in targets
  if len(pts)<2 or not min(y for x,y in pts)<967.5<max(y for x,y in pts):continue
  a=math.floor(min(x for x,y in pts));b=math.floor(max(x for x,y in pts));hit=max(0,min(69,b)-max(60,a)+1)
  if not hit:continue
  w=hit/(b-a+1);total+=w
  if touch:data_touched+=w
  else:without_data+=w
  if dr and dr[0]=='i'and D.cells[dr[1]][6]in targets:
   name=D.cells[dr[1]][6];drivers[name]+=w;records.setdefault(name,[]).append(ni)
 capacity=10*sum(G.TRACK_DERATE/p for n,(direction,p)in D.extra['tech'].items()if direction.upper().startswith('V')and 2<=G._layer_idx(n)<=7)
 return dict(weighted_crossings=total,capacity=capacity,util=total/capacity,DATA_touched_weight=data_touched,without_DATA_weight=without_data,DATA_driver_weights=dict(drivers),DATA_driver_net_indices=records)
setposes(F);prior_cut_before=prior_hot_cut();setposes(targets);prior_cut_after=prior_hot_cut()
prior_driver_attribution=[]
for name,w in prior_cut_before['DATA_driver_weights'].items():
 t=targets[name];before=origxy[N[name]];after=newxy[N[name]];aft=prior_cut_after['DATA_driver_weights'].get(name,0.)
 prior_driver_attribution.append(dict(name=name,master=t['master'],weighted_before=w,weighted_after=aft,reduction=w-aft,old_xy_um=before,new_xy_um=after,geom_net_indices=prior_cut_before['DATA_driver_net_indices'][name]))
prior_driver_attribution.sort(key=lambda x:-x['reduction'])
(R/'prior_hot_cut_DATA_driver_attribution.json').write_text(json.dumps(dict(scope='same source graph and fixedFFmodel before/after only the approved ownedDATAcomb placement; not a second model/capacity sweep',before=prior_cut_before,after=prior_cut_after,drivers=prior_driver_attribution),indent=2))
# Exactly one projected capacity calculation for this concrete legal placement; no GRT/CTS/STA.
demand=G.demand_metrics(D,max_layer='M7',min_layer='M2');rp=[];r2r=G.r2r_metrics(D,rp);ck=G.clock_metrics(D);land=G.land_ring_captures(D,json.load(open(P/'land_slots.json')),json.load(open(P/'face_guard.json')));pins=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT),frozenset(ck['tap_sinks'])|frozenset(land['clock_exports']),land['caps'])
band_hits=[]
for name,t in targets.items():
 bb=t['bbox_dbu']
 for band in band_reservations:
  x=band['bbox_dbu']
  if bb[0]<x[2]and x[0]<bb[2]and bb[1]<x[3]and x[1]<bb[3]:band_hits.append(dict(name=name,band_owner=band['owner']))
report=dict(prior_hot_cut_before={k:v for k,v in prior_cut_before.items()if not k.startswith('DATA_driver')},prior_hot_cut_after={k:v for k,v in prior_cut_after.items()if not k.startswith('DATA_driver')},prior_hot_cut_DATA_driver_count=len(prior_driver_attribution),prior_hot_cut_top_DATA_driver_witnesses=prior_driver_attribution[:12],other_actual_declared_band_rectangles_preserved=len(band_reservations),other_band_hits=band_hits,scope='DISABLED single concrete exact-owned ft2 DATA-comb placement; unchanged native graph/master/count/allFFtargets/publicpins/clock-reset-START infrastructure; no DB/CAD',owned_eligible=len(E),allocated=len(targets),failed=len(fail),failures=fail,owned_area_um2=sum((C[i][2][2]-C[i][2][0])*(C[i][2][3]-C[i][2][1])/1e6 for i in E),all_native_cells=len(C),allFF52044_poses_unchanged_from_previous_MODEL=True,all_other_native_cells_fixed=len(C)-len(E),TAP137673_fixed=True,clock_reset_START_shared_FIRM_DNT_nodes_held=True,master_orientation_dimension_failures=badmasters,row_site_failures=badrows,overlaps=overlaps,max_site_jog_um=max((t['jog_um']for t in targets.values()),default=0),projected_M2M7_demand=demand,r2r=r2r,remaining_R2R=rp,pin_metrics=pins,classification=json.load(open(P/'classification.json')),holds=['no actualrouting/clock/source qualification; original GRT4843/fill/partial-face/PG95696bufferopens retained','PGshapes/nets/sourceclockphase remain unchanged/held; exactPGlanding before physicalstage','only actual data-owned exclusive-frontier nonFIRM nonDNT cells eligible; no name-prefix sweep or generic GPL assumption','any remaining capacity/legality failure remains explicit; no additional variants or target relaxation'])
(R/'model.json').write_text(json.dumps(report,indent=2));(R/'DATA_targets.json').write_text(json.dumps(targets,indent=2));print({k:v for k,v in report.items()if k not in('classification','failures','overlaps','remaining_R2R','pin_metrics','holds')});print('PIN',pins)
