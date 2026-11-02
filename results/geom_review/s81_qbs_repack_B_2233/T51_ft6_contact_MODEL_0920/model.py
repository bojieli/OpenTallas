"""One existing-FF clock contact repair. Keep every existing proposed tap membership; no native DB/CAD."""
from pathlib import Path
import json,gzip,collections,bisect,math,sys,re
R=Path(__file__).parent;P=R/'inputs';sys.path.insert(0,str(R/'tools'));import geom_rules as G
C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];N={c[0]:c for c in C};F=json.load(open(P/'joint_FF_targets.json'));T=json.load(open(P/'DATA_targets.json'));A=dict(F);A.update(T);regions={r['name']:r for r in json.load(open(P/'ft6_clock_regions.json'))['records']};assign=json.load(gzip.open(P/'joint_model_mission_assignment_MODEL.json.gz','rt'));asg={r['name']:r['tap']for r in assign};taps={t['name']:[round(v*1000)for v in t['xy']]for t in json.load(open(P/'current_plan.json'))['partition_types']['slice_station__t51']['clock']['taps']};rows=json.load(open(P/'rows.json'));rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for r in rows:rs[r['origin_dbu'][1]].append(r)
ys=sorted(rs);core=json.load(open(P/'native_census.json'))['core_dbu'];M=set();before={}
def distances(n,bb):
 c=N[n];tx,ty=taps[asg[n]];cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2;lx=c[3][0]+bb[0]-c[2][0];ly=c[3][1]+bb[1]-c[2][1];return(abs(cx-tx)+abs(cy-ty))/1000,(abs(lx-tx)+abs(ly-ty))/1000
for n in regions:
 d,ld=distances(n,F[n]['bbox_dbu']);before[n]=[d,ld]
 if max(d,ld)>150+1e-8:M.add(n)
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for c in C:
 if c[0]in M:continue
 occupy(A[c[0]]['bbox_dbu']if c[0]in A else c[2])
bands=json.load(open(P/'other_declared_band_reservations.json'))['rectangles']
for b in bands:occupy(b['bbox_dbu'])
for y in occ:occ[y].sort()
changed={};fail=[]
for n in sorted(M,key=lambda n:(-max(before[n]),n)):
 c=N[n];w=c[2][2]-c[2][0];h=c[2][3]-c[2][1];phases={r['orient']for r in rs[c[2][1]]};u0,u1,v0,v1=regions[n]['UV_fixed405_bounds_dbu'];cx,cy=[v*1000for v in F[n]['xy_um']];tx,ty=taps[asg[n]];ox=c[3][0]-c[2][0];oy=c[3][1]-c[2][1];best=None
 # Bound the complete row search by the fixed SAME tap's centre and actual-native location150 diamonds.
 yl=max(core[1],ty-150000-h/2,ty-150000-oy,(u0-v1-h)/2);yh=min(core[3]-h,ty+150000-h/2,ty+150000-oy,(u1-v0-h)/2)
 for y in ys[bisect.bisect_left(ys,yl):bisect.bisect_right(ys,yh)]:
  yy=y+h/2;cr=150000-abs(yy-ty);lr=150000-abs(y+oy-ty)
  if min(cr,lr)<0:continue
  for row in rs[y]:
   if row['orient']not in phases:continue
   lo=max(core[0],row['bbox_dbu'][0],u0-yy-w/2,v0+yy-w/2,tx-cr-w/2,tx-lr-ox);hi=min(core[2]-w,row['bbox_dbu'][2]-w,u1-yy-w/2,v1+yy-w/2,tx+cr-w/2,tx+lr-ox)
   if lo>hi:continue
   gaps=[];last=lo
   for aa,bb in occ[y]:
    if bb<=lo:continue
    if aa>=hi+w:break
    if aa>last:gaps.append((last,min(aa,hi+w)))
    last=max(last,bb)
   if last<hi+w:gaps.append((last,hi+w))
   for aa,bb in gaps:
    step=row['spacing_dbu'];rx=row['origin_dbu'][0];ia=math.ceil((aa-rx)/step);ib=math.floor((bb-w-rx)/step)
    if ib<ia:continue
    k=min(ib,max(ia,round((cx-w/2-rx)/step)));x=rx+k*step;key=(abs(x+w/2-cx)+abs(yy-cy),y,x)
    if best is None or key<best[0]:best=(key,[x,y,x+w,y+h],row)
 if not best:fail.append(dict(name=n,tap=asg[n],original_distances_um=before[n],UV=[u0,u1,v0,v1]));continue
 key,bb,row=best;occupy(bb)
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].sort()
 t=dict(F[n]);t.update(bbox_dbu=bb,xy_um=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000],old_model_bbox_dbu=F[n]['bbox_dbu'],same_fixed_proposed_tap=asg[n],source_root_unchanged='clk',jog_um=key[0]/1000,row=row['name']);F[n]=t;changed[n]=t;A[n]=t
print('CONTACT_TARGETS',len(M),'allocated',len(changed),'FAIL',len(fail),flush=True)
# Independent full-population audit, master/orientation/phase and 52band checks.
byrow=collections.defaultdict(list);rowbad=[];masterbad=[];bandbad=[]
for c in C:
 n=c[0];t=A.get(n);bb=t['bbox_dbu']if t else c[2]
 if n in changed:
  phases={r['orient']for r in rs[c[2][1]]};legal=[r for r in rs[bb[1]]if r['bbox_dbu'][0]<=bb[0]and bb[2]<=r['bbox_dbu'][2]and bb[3]<=r['bbox_dbu'][3]and(bb[0]-r['origin_dbu'][0])%r['spacing_dbu']==0 and r['orient']in phases]
  if not legal:rowbad.append(n)
  if t['master']!=c[1]or t['orient']!=c[4]or[bb[2]-bb[0],bb[3]-bb[1]]!=[c[2][2]-c[2][0],c[2][3]-c[2][1]]:masterbad.append(n)
  for band in bands:
   b=band['bbox_dbu']
   if bb[0]<b[2]and b[0]<bb[2]and bb[1]<b[3]and b[1]<bb[3]:bandbad.append(dict(name=n,band=band['owner']))
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:byrow[y].append((bb[0],bb[2],n))
overlaps=[];seen=set()
for y,ints in byrow.items():
 active=[]
 for a,b,n in sorted(ints):
  active=[p for p in active if p[1]>a]
  for aa,bb,nn in active:
   if n not in changed and nn not in changed:continue
   pair=tuple(sorted((n,nn)))
   if pair not in seen:seen.add(pair);overlaps.append(dict(names=pair,row_y_dbu=y))
  active.append((a,b,n))
D=G.Design(P/'geom.tsv');idof={c[6]:i for i,c in D.cells.items()}
for n,t in A.items():
 i=idof[n];c=list(D.cells[i]);c[2:6]=[v/1000for v in t['bbox_dbu']];D.cells[i]=tuple(c)
rb=[];r2r=G.r2r_metrics(D,rb);demand=G.demand_metrics(D,max_layer='M7',min_layer='M2');land=G.land_ring_captures(D,json.load(open(P/'land_slots.json')),json.load(open(P/'face_guard.json')));clk=G.clock_metrics(D);pin=G.pin_reg_metrics(D,re.compile(G.STRAP_RE_DEFAULT),frozenset(clk['tap_sinks'])|frozenset(land['clock_exports']),land['caps']);clockbad=[];stagebad=[];counts=collections.Counter(asg.values());maxcentre=0;maxloc=0
for n in asg:
 c=N[n];bb=F[n]['bbox_dbu']if n in F else c[2];dc,dl=distances(n,bb);maxcentre=max(maxcentre,dc);maxloc=max(maxloc,dl)
 if max(dc,dl)>150+1e-8:
  clockbad.append(dict(name=n,tap=asg[n],centre_um=dc,location_um=dl))
  if n in regions:stagebad.append(clockbad[-1])
report=dict(scope='DISABLED one bounded FT6stage2 contact correction. Preserve all FT2/DATA149342075poses and all already-proposed clocktap memberships; no new node/port/cycle or actual DB/CAD.',requested_contacts=len(M),allocated_contacts=len(changed),failed=fail,max_jog_um=max((t['jog_um']for t in changed.values()),default=0),all515_stage2_same_proposed_tap_membership=True,complete323283body_audit=dict(new_target_overlaps=overlaps,row_site_failures=rowbad,master_orient_dimension_failures=masterbad,other_band_hits=bandbad),same_existing_assignment=dict(cap=1500,max_load=max(counts.values()),all_mission_FFs=len(asg),changed_memberships=0,stage2_over150=len(stagebad),stage2_bad=stagebad,all_mission_either_centre_or_location_over150=len(clockbad),max_centre_um=maxcentre,max_location_um=maxloc,remaining_other_clock_witnesses=sorted(clockbad,key=lambda v:-max(v['centre_um'],v['location_um']))[:10]),r2r=r2r,remaining_r2r=rb,pins=pin,projected_M2M7_demand=demand,holds=['source planning membership is not installed nativeTcl/sourceclockphase qualification','other sourceclock150radius violations/NWft3physical4843/95696PGopens/2partialfaces/sparsefill remain','all SOURCE/FF/master/orient/domain/reset/stages/cycles/pins unchanged; no GEN/physicalrelease'])
(R/'model.json').write_text(json.dumps(report,indent=2));(R/'FF_targets.json').write_text(json.dumps(F,indent=2));(R/'changed_contacts.json').write_text(json.dumps(changed,indent=2));print({k:v for k,v in report.items()if k not in('same_existing_assignment','pins','remaining_r2r','holds')},flush=True);print('CLOCK',report['same_existing_assignment'],flush=True)
