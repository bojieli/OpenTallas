"""Finite read-only collection of the single saved disabled model; no new layout or demand sweep."""
from pathlib import Path
import json,gzip,collections,bisect,sys,math
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];native={c[0]:c for c in C};F=json.load(open(P/'joint_FF_targets.json'));T=json.load(open(R/'DATA_targets.json'));A=dict(F);A.update(T);rows=json.load(open(P/'rows.json'));rs=collections.defaultdict(list);byrow=collections.defaultdict(list)
for row in rows:rs[row['origin_dbu'][1]].append(row)
ys=sorted(rs);rowbad=[];masterbad=[];bandbad=[];bands=json.load(open(P/'other_declared_band_reservations.json'))['rectangles']
for c in C:
 n=c[0];t=A.get(n);bb=t['bbox_dbu']if t else c[2]
 if t:
  phases={r['orient']for r in rs[c[2][1]]};legal=[r for r in rs[bb[1]]if r['bbox_dbu'][0]<=bb[0]and bb[2]<=r['bbox_dbu'][2]and bb[3]<=r['bbox_dbu'][3]and(bb[0]-r['origin_dbu'][0])%r['spacing_dbu']==0 and r['orient']in phases]
  if not legal:rowbad.append(n)
  if t['master']!=c[1]or t['orient']!=c[4]or[bb[2]-bb[0],bb[3]-bb[1]]!=[c[2][2]-c[2][0],c[2][3]-c[2][1]]:masterbad.append(n)
  for band in bands:
   a=band['bbox_dbu']
   if bb[0]<a[2]and a[0]<bb[2]and bb[1]<a[3]and a[1]<bb[3]:bandbad.append(dict(name=n,band=band['owner']))
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:byrow[y].append((bb[0],bb[2],n))
overlaps=[];seen=set()
for y,ints in byrow.items():
 active=[]
 for a,b,n in sorted(ints):
  active=[p for p in active if p[1]>a]
  for aa,bb,nn in active:
   if n not in A and nn not in A:continue
   k=tuple(sorted((n,nn)))
   if k not in seen:seen.add(k);overlaps.append(dict(names=k,row_y_dbu=y))
  active.append((a,b,n))
clock={};sets={};detail=[]
for label in ['actual_baseline','joint_model']:
 a=json.load(gzip.open(R/(label+'_mission_assignment_MODEL.json.gz'),'rt'));bad=[];fam=collections.Counter();llbad=0
 # Exact stored candidate binding. Separate centre planning from Tcl-location sensitivity; no installed-binding claim.
 tapxy={t['name']:t['xy']for t in json.load(open(P/'current_plan.json'))['partition_types']['slice_station__t51']['clock']['taps']}
 for q in a:
  n=q['name'];cc=native[n];bb=F[n]['bbox_dbu']if label=='joint_model'and n in F else cc[2];tx,ty=tapxy[q['tap']];d=abs((bb[0]+bb[2])/2000-tx)+abs((bb[1]+bb[3])/2000-ty);ll=cc[3]if label=='actual_baseline'or n not in F else [cc[3][0]+bb[0]-cc[2][0],cc[3][1]+bb[1]-cc[2][1]];dl=abs(ll[0]/1000-tx)+abs(ll[1]/1000-ty)
  if dl>150+1e-8:llbad+=1
  if d>150+1e-8:
   family=F[n]['family']if n in F else n.replace('\\','').split('/')[0];fam[family]+=1;bad.append(n)
   if label=='joint_model'and n in F:detail.append(dict(name=n,family=family,tap=q['tap'],distance_um=d,same_assignment_TCL_location_distance_um=dl))
 sets[label]=set(bad);clock[label]=dict(radius_violation_FFs=len(bad),by_native_family=dict(fam),same_candidate_assignment_TCL_location_over150=llbad,actual_fixed_source_root_family='clk(_tN)? only; source hook configured root clk; forwarded fclk excluded')
clock['delta']=dict(newly_bad=len(sets['joint_model']-sets['actual_baseline']),resolved=len(sets['actual_baseline']-sets['joint_model']),new_bad_names=sorted(sets['joint_model']-sets['actual_baseline']),resolved_names=sorted(sets['actual_baseline']-sets['joint_model']),candidate_moved_bad_details=detail)
print('OCCUPANCY',len(overlaps),len(rowbad),len(masterbad),'CLOCK_DELTA',clock['delta']['newly_bad'],clock['delta']['resolved'],flush=True)
D=G.Design(P/'geom.tsv')
for cid,c in list(D.cells.items()):
 t=A.get(c[6])
 if t:
  a=list(c);a[2:6]=[v/1000 for v in t['bbox_dbu']];D.cells[cid]=tuple(a)
x0,x1,ycut=240,250,1207.5;weights=collections.Counter();families=collections.Counter();witness=[];total=0.
def role(c):return'owned_DATA'if c[6]in T else'moved_'+F[c[6]]['family']if c[6]in F else'held_FF'if c[0]=='S'else'held_comb'
for ni,(sig,dr,sk)in enumerate(D.nets):
 if sig=='CLOCK':continue
 pts=[];eps=[]
 for ep in([dr]if dr else[])+sk:
  if ep[0]=='p':
   p=D.pin_by_k.get(ep[1])
   if p:pts.append((p['x'],p['y']));eps.append(dict(name=p['name'],role='fixedPIO',xy=pts[-1]))
  elif ep[1]in D.cells:
   c=D.cells[ep[1]];xy=G.ctr(c);pts.append(xy);eps.append(dict(name=c[6],master=c[1],role=role(c),xy=xy))
 if len(pts)<2 or not min(y for x,y in pts)<ycut<max(y for x,y in pts):continue
 a=math.floor(min(x for x,y in pts));b=math.floor(max(x for x,y in pts));hit=max(0,min(x1-1,b)-max(x0,a)+1)
 if not hit:continue
 w=hit/(b-a+1);total+=w;driver=eps[0]if dr else dict(name='NO_DRIVER',role='unknown');weights[driver['role']]+=w;families[driver['name'].replace('\\','').split('/')[0]]+=w;witness.append(dict(geom_net_index=ni,weight=w,driver=driver,endpoints=eps))
witness.sort(key=lambda x:-x['weight']);cap=10*sum(G.TRACK_DERATE/p for n,(di,p)in D.extra['tech'].items()if di.upper().startswith('V')and 2<=G._layer_idx(n)<=7)
report=dict(scope='Independent integer fullpopulation source-model audit and attribution of already-computed remaining240/1207.5 cut; no layout/capacity rerun/CAD',all_native_bodies=len(C),targets=len(A),FFtargets=len(F),DATA_targets=len(T),TAP137673_fixed=True,all_other_actual_bodies_fixed=len(C)-len(A),row_site_failures=rowbad,master_orient_dimension_failures=masterbad,new_target_overlaps=overlaps,other_band_hits=bandbad,clock_source_membership_limit='Actual native FF roots unchanged. Proposed clock assignment is source planning taps.assign using FF centres, not installed Tcl PRE_CTS or phase. Actual TCL uses instance location and optional reset-follow. Both geometric radius results and same-candidate LL sensitivity explicitly retained.',clock_diagnosis=clock,remaining_original_NW_cut=dict(x_window_um=[x0,x1],cut_y_um=ycut,weighted_crossings=total,capacity=cap,util=total/cap,driver_roles=dict(weights),native_driver_families=dict(families),net_count=len(witness),witnesses=witness[:12]))
(R/'collection.json').write_text(json.dumps(report,indent=2));print('NW',total/cap,'ROLES',dict(weights),'FAMILIES',families.most_common(5),flush=True)
