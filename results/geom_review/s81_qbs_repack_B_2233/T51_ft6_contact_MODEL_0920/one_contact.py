"""Explicit one-existing-tap planning delta for the sole failed contact; no full layout/cut rerun/CAD."""
from pathlib import Path
import json,gzip,collections,bisect,math
R=Path(__file__).parent;P=R/'inputs';prior=json.load(open(R/'model.json'));assert len(prior['failed'])==1;n=prior['failed'][0]['name'];C=[json.loads(s)for s in gzip.open(P/'cells.jsonl.gz','rt')];N={c[0]:c for c in C};c=N[n];F=json.load(open(R/'FF_targets.json'));T=json.load(open(P/'DATA_targets.json'));A=dict(F);A.update(T);q=next(v for v in json.load(open(P/'ft6_clock_regions.json'))['records']if v['name']==n);u0,u1,v0,v1=q['UV_fixed405_bounds_dbu'];tapname='clk_t32';table={t['name']:t['xy']for t in json.load(open(P/'current_plan.json'))['partition_types']['slice_station__t51']['clock']['taps']};tx,ty=[round(v*1000)for v in table[tapname]];rows=json.load(open(P/'rows.json'));rs=collections.defaultdict(list);occ=collections.defaultdict(list)
for row in rows:rs[row['origin_dbu'][1]].append(row)
ys=sorted(rs);core=json.load(open(P/'native_census.json'))['core_dbu']
def occupy(bb):
 for y in ys[bisect.bisect_right(ys,bb[1]-270):bisect.bisect_left(ys,bb[3])]:occ[y].append((bb[0],bb[2]))
for cc in C:
 if cc[0]!=n:occupy(A[cc[0]]['bbox_dbu']if cc[0]in A else cc[2])
for b in json.load(open(P/'other_declared_band_reservations.json'))['rectangles']:occupy(b['bbox_dbu'])
for y in occ:occ[y].sort()
w=c[2][2]-c[2][0];h=c[2][3]-c[2][1];ox=c[3][0]-c[2][0];oy=c[3][1]-c[2][1];cx,cy=[v*1000for v in F[n]['xy_um']];phases={r['orient']for r in rs[c[2][1]]};best=None
for y in ys:
 yy=y+h/2;cr=150000-abs(yy-ty);lr=150000-abs(y+oy-ty)
 if min(cr,lr)<0:continue
 for row in rs[y]:
  if row['orient']not in phases:continue
  lo=max(core[0],row['bbox_dbu'][0],u0-yy-w/2,v0+yy-w/2,tx-cr-w/2,tx-lr-ox);hi=min(core[2]-w,row['bbox_dbu'][2]-w,u1-yy-w/2,v1+yy-w/2,tx+cr-w/2,tx+lr-ox)
  if lo>hi:continue
  gaps=[];last=lo
  for a,b in occ[y]:
   if b<=lo:continue
   if a>=hi+w:break
   if a>last:gaps.append((last,min(a,hi+w)))
   last=max(last,b)
  if last<hi+w:gaps.append((last,hi+w))
  for a,b in gaps:
   rx=row['origin_dbu'][0];step=row['spacing_dbu'];ia=math.ceil((a-rx)/step);ib=math.floor((b-w-rx)/step)
   if ib<ia:continue
   k=min(ib,max(ia,round((cx-w/2-rx)/step)));x=rx+k*step;key=(abs(x+w/2-cx)+abs(yy-cy),y,x)
   if best is None or key<best[0]:best=(key,[x,y,x+w,y+h],row)
assert best,'explicit alternative existing tap has no complete fixed405/native-body legal site'
key,bb,row=best;xy=[(bb[0]+bb[2])/2000,(bb[1]+bb[3])/2000];loc=[(bb[0]+ox)/1000,(bb[1]+oy)/1000];edges=[dict(endpoint=v['name'],xy_um=[z/1000for z in v['xy_dbu']],distance_um=abs(xy[0]-v['xy_dbu'][0]/1000)+abs(xy[1]-v['xy_dbu'][1]/1000))for v in q['fixed_endpoint_witnesses']];cd=abs(xy[0]-tx/1000)+abs(xy[1]-ty/1000);ld=abs(loc[0]-tx/1000)+abs(loc[1]-ty/1000);assert max(cd,ld)<=150+1e-9 and max(v['distance_um']for v in edges)<=405+1e-9
loads=collections.Counter(v['tap']for v in json.load(gzip.open(P/'joint_model_mission_assignment_MODEL.json.gz','rt')));beforeloads=dict(loads);loads['clk_t17']-=1;loads[tapname]+=1;assert max(loads.values())<=1500
allothers=len(C)-1;maxedge=max(v['distance_um']for v in edges);target=dict(F[n]);target.update(bbox_dbu=bb,xy_um=xy,row=row['name'],explicit_proposed_tap=tapname,old_proposed_tap='clk_t17',source_native_root_unchanged='clk',jog_um=key[0]/1000)
report=dict(scope='DISABLED exact onecell source planning contact/membership repair. Prior173/174FAIL preserved; no native DB/full placement/cut/CTS/GRT/STA.',verdict='PASS onepoint geometric witness; overall sourceclock/physical HOLD',name=n,old_model_xy_um=F[n]['xy_um'],new_model_xy_um=xy,new_native_location_um=loc,target=target,explicit_membership_delta=dict(old='clk_t17',new=tapname,native_actual_root_before_after='clk',clock_ports_added=0,clock_control_FFs_added=0,reset_FFs_added=0,cycles_added=0),centre_radius_um=cd,native_location_radius_um=ld,fixed405_incident_edges=edges,all_other_model_cells_and173contacts_exactly_fixed=allothers,original_master_orientation_and_supplyphase_preserved=True,full_prior_body_audit_zero_inherited_only_for_unchanged_cells=True,onecell_body_collision_count=0,onecell_otherband_hit_count=0,current_tap_load_delta=dict(t17_before=beforeloads['clk_t17'],t17_after=loads['clk_t17'],t32_before=beforeloads[tapname],t32_after=loads[tapname],maximum_load=max(loads.values()),cap=1500),combined515stage2_contacts_over150=0,combined_graph_max_um=max(prior['r2r']['r2r_max'],maxedge),combined_graph_captures=prior['r2r']['r2r_captures'],combined_graph_over405=0,combined_pin_max_um=prior['pins']['pin_reg_max'],projected_cut_scope='No global demand rerun; originalNWft3cut remains HOLD, onepoint data-net change is not a new whole-cut result.',remaining_other_source_clock_radius_union=prior['same_existing_assignment']['all_mission_either_centre_or_location_over150']-1,holds=['one changed membership is explicit proposal; current native actualroot remainsclk, no installedclock/source-export/window/phase qualification','909+other clockradius/originalNWft3/4843/PG95696/2partialfaces/sparsefill holds remain','no GEN/helper/RTL/plan/ODB edits or physicalrelease'])
(R/'one_contact.json').write_text(json.dumps(report,indent=2));(R/'one_contact_target.json').write_text(json.dumps({n:target},indent=2));print({k:v for k,v in report.items()if k not in('target','holds')},flush=True)
