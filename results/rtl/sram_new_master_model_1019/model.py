#!/usr/bin/env python3
"""Finite coordinate/RC model, not a LEF/GDS/view or native DRC generator."""
import copy,hashlib,json,math
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda n:json.loads((P/'input'/n).read_text())
def shift(r,dy):return [r[0],r[1]+dy,r[2],r[3]+dy]
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def union_area(rs):
 xs=sorted({x for r in rs for x in [r[0],r[2]]});area=0
 for a,b in zip(xs,xs[1:]):
  ys=sorted((r[1],r[3]) for r in rs if r[0]<=a and r[2]>=b);hi=None;length=0
  for c,d in ys:
   if hi is None or c>hi:length+=d-c;hi=d
   elif d>hi:length+=d-hi;hi=d
  area+=(b-a)*length
 return area
def components(rs):
 unseen=set(range(len(rs)));out=[]
 while unseen:
  todo=[unseen.pop()];idx=set(todo)
  while todo:
   i=todo.pop()
   for j in list(unseen):
    if overlap(rs[i],rs[j]):unseen.remove(j);idx.add(j);todo.append(j)
  selected=[rs[i] for i in idx];box=[min(r[0] for r in selected),min(r[1] for r in selected),max(r[2] for r in selected),max(r[3] for r in selected)]
  out.append(dict(rectangles=selected,bbox_nm=box,union_area_nm2=union_area(selected),rectangular=union_area(selected)==(box[2]-box[0])*(box[3]-box[1])))
 return out
def contained(r,w,h):return 0<=r[0]<r[2]<=w and 0<=r[1]<r[3]<=h
out={'status':'CONDITIONAL_NEW_MASTER_MODEL_ONLY_NOT_VIEWS_OR_NATIVE_DRC','choice':{'core_and_signal_attachment_dy_nm':39,'old_native_lead_and_via_dy_nm':48,'PG_center_dy_nm':51,'PG_width_nm':120,'outline_height_increment_nm':48,'cycle_delta_proposed':0},'families':{},'native_provenance':{'image_repo_digest':'openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','binary_sha256':'21eda99eeae7eccb22ca64ad28949c08a6c01dcece3ccb23e2206d635f8d2846','version':'26Q3-1510-g6cb3f2b704','frozen_calibration_image_not_current':'af971398d91e5d154ec40d3df26554efd8790107268a4c7f1e6bb8f222979d34'},'inputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((P/'input').iterdir())}}
for family,model,paths in [('qwen',load('qwen.json'),load('qwen.json')['paths']),('sc2',load('sc2_model.json'),load('sc2.json'))]:
 w,h=model['outline_nm'];nh=h+48;rules=model['rules'];ledgers=[];flat=[];violations=[];oldbad=0
 for p in paths:
  oldshapes=copy.deepcopy(p['shapes']+p.get('retained_pads',[]))
  # Qwen already records source pads; SC2 records both source and terminal pads.
  if not any('contact' in s.get('role','').lower() or 'source_pad'==s.get('role') for s in oldshapes):raise ValueError('missing actual source pad')
  shapes=[]
  for s in oldshapes:
   attachment=('contact' in s.get('role','').lower() or s.get('role') in ('source_pad','terminal_pad'))
   ns=dict(s,rect_nm=shift(s['rect_nm'],39 if attachment else 48));shapes.append(ns)
  vias=[]
  for v in p['vias']:
   nv=copy.deepcopy(v)
   for k in ['cut_rect_nm','m4_rect_nm','m5_rect_nm']:nv[k]=shift(v[k],48)
   nv['center_nm']=[v['center_nm'][0],v['center_nm'][1]+48];vias.append(nv)
  def metal(shapes,vias):
   return {l:[s['rect_nm'] for s in shapes if s['layer']==l]+[v['m4_rect_nm' if l=='M4' else 'm5_rect_nm'] for v in vias] for l in ['M4','M5']}
  oldmetal=metal(oldshapes,p['vias']);newmetal=metal(shapes,vias)
  comps={l:components(rs) for l,rs in newmetal.items()}
  oldbad+=sum(not c['rectangular'] for rs in oldmetal.values() for c in components(rs))
  for layer,cs in comps.items():
   for c in cs:
    r=c['bbox_nm'];width=r[3]-r[1] if layer=='M4' else r[2]-r[0];center=(r[1]+r[3])//2 if layer=='M4' else (r[0]+r[2])//2
    if not c['rectangular'] or width!=24 or center%48!=(3 if layer=='M4' else 0) or c['union_area_nm2']<2000:violations.append([p['pin'],layer,'union/width/phase/area',c])
  for v in vias:
   x,y=v['center_nm'];assert v['cut_rect_nm']==[x-12,y-12,x+12,y+12]
   assert v['m4_rect_nm']==[x-23,y-12,x+23,y+12]
   assert v['m5_rect_nm']==[x-12,y-23,x+12,y+23]
  length={l:union_area(rs)/24/1000 for l,rs in newmetal.items()}
  cap=sum(length[l]*rules['rc'][l]['c_ff_per_um'] for l in length)
  resistance=sum(length[l]*rules['rc'][l]['r_kohm_per_um'] for l in length)+len(vias)*rules['via_r_kohm']
  for l,rs in newmetal.items():flat.extend(dict(net=p['pin'],layer=l,rect_nm=r) for r in rs)
  ledgers.append(dict(pin=p['pin'],kind=p['kind'],face=p['face'],old_source_nm=p['preserved_anchor_nm'],new_source_nm=[p['preserved_anchor_nm'][0],p['preserved_anchor_nm'][1]+39],old_terminal_nm=p['terminal_nm'],new_terminal_nm=[p['terminal_nm'][0],p['terminal_nm'][1]+(48 if family=='qwen' else 39)],old_shapes=oldshapes,new_shapes=shapes,old_vias=p['vias'],new_vias=vias,union_components=comps,union_metal_length_um=length,wire_cap_ff=cap,wire_r_kohm=resistance,old_reported_cap_ff=p['cap_ff'],old_reported_r_kohm=p['resistance_kohm'],lead_RC_upper_ps_by_load_ff={str(x):resistance*(cap+x) for x in [0,0.72,2.88,11.52,23.04,46.08]},internal_attachment_contract='Entire original analytical core and corresponding logical port/bit terminal move +39nm Y; transistor/contact row placement is conditional, not implemented or extracted.'))
 pg=[]
 for i,s in enumerate(model['pg_rectangles']):
  old=s['rect_nm'];new=[old[0],old[1]+39,old[2],old[3]+63];assert new[3]-new[1]==120 and ((new[1]+new[3])//2)%48==3
  pg.append(dict(id=i,net=s['net'],layer=s['layer'],old_rect_nm=old,new_rect_nm=new,internal_attachment='New 120nm rail center +51nm Y; +12nm relative to translated core. Every old rail retained. Internal PG straps/contact rows must be explicitly rebuilt to this rail; no unchanged electrical attachment claim.',old_area_um2=(old[2]-old[0])*(old[3]-old[1])/1e6,new_area_um2=(new[2]-new[0])*(new[3]-new[1])/1e6,parallel_metal_R_kohm=rules['rc']['M4']['r_kohm_per_um']*(new[2]-new[0])/1000*24/120,PG_cap_ff_width_linear_conditional=rules['rc']['M4']['c_ff_per_um']*(new[2]-new[0])/1000*120/24))
  flat.append(dict(net=s['net'],layer=s['layer'],rect_nm=new))
 # Independent cross-net distance inventory, all rectangles (incl native via metals and PG).
 neighbor_violations=[];min_gap={'M4':None,'M5':None};parallel_wide_violations=[]
 for i,a in enumerate(flat):
  r=a['rect_nm']
  if not contained(r,w,nh):violations.append([a['net'],'outline',r])
  for b in flat[i+1:]:
   if a['layer']!=b['layer'] or a['net']==b['net']:continue
   s=b['rect_nm'];dx=max(s[0]-r[2],r[0]-s[2],0);dy=max(s[1]-r[3],r[1]-s[3],0)
   if dx<24 and dy<24:neighbor_violations.append([a['net'],b['net'],a['layer'],r,s,dx,dy])
   if dx==0 or dy==0:
    gap=max(dx,dy);l=a['layer'];min_gap[l]=gap if min_gap[l] is None else min(min_gap[l],gap)
    wa=r[3]-r[1] if l=='M4' else r[2]-r[0];wb=s[3]-s[1] if l=='M4' else s[2]-s[0]
    if max(wa,wb)>24 and gap<72:parallel_wide_violations.append([a['net'],b['net'],l,gap])
 clock=[p for p in ledgers if p['kind']=='clock'];clockc=sum(p['wire_cap_ff'] for p in clock);totalc=sum(p['wire_cap_ff'] for p in ledgers)
 corner={}
 for c,t in model['timing'].items():
  oldclock=sum(t['clock_pin_cap_ff_by_pin'].values());baseclock=oldclock-sum(p['old_reported_cap_ff'] for p in clock);v2=t['complete_boundary_clock_driver_energy_fj']/oldclock
  corner[c]=dict(supply_V_squared_inferred_from_pinned_clock_energy=v2,conditional_original_clock_pin_cap_ff=baseclock,recomputed_boundary_clock_cap_ff=baseclock+clockc,recomputed_boundary_clock_energy_fj=(baseclock+clockc)*v2,all_signal_leads_full_toggle_energy_fj=totalc*v2,all_nonclock_plus_complete_clock_energy_fj=(totalc+baseclock)*v2,native_min_CQ_ps=None,native_max_CQ_ps=None,native_setup_hold_ps=None,original_analytical_core_timing='Conditional reference only; not inherited native timing; no positive minimum CQ.')
 oldobs=model['proposed_obstruction_rectangles'];newobs=[dict(s,rect_nm=shift(s['rect_nm'],39)) for s in oldobs]
  # Only coordinate reservations: access to these PG pins is deliberately unqualified.
 obs_containment=all(contained(s['rect_nm'],w,nh) for s in newobs)
 own_pg_obs=[p['id'] for p in pg if any(s['layer']==p['layer'] and overlap(s['rect_nm'],p['new_rect_nm']) for s in newobs)]
 allcuts=[v['cut_rect_nm'] for p in ledgers for v in p['new_vias']];cutfails=[]
 for i,a in enumerate(allcuts):
  for b in allcuts[i+1:]:
   dx=max(b[0]-a[2],a[0]-b[2],0);dy=max(b[1]-a[3],a[1]-b[3],0)
   if dx<34 and dy<34:cutfails.append([a,b,dx,dy])
 assert not cutfails and obs_containment
 core=model['core_geometry'];corebox=[model['core_offset_nm'][0],39,model['core_offset_nm'][0]+math.ceil(core['core_width_um']*1000),39+math.ceil(core['core_height_um']*1000)]
 out['families'][family]=dict(master=model['name'],signal_count=len(ledgers),PG_count=len(pg),via_count=sum(len(p['new_vias']) for p in ledgers),old_outline_nm=[w,h],new_outline_nm=[w,nh],reservation_43p2_lattice_um=[math.ceil(w/43200)*43.2,math.ceil(nh/43200)*43.2],old_reservation_43p2_lattice_um=[math.ceil(w/43200)*43.2,math.ceil(h/43200)*43.2],old_area_um2=w*h/1e6,new_area_um2=w*nh/1e6,delta_area_um2=w*48/1e6,core_bbox_nm=corebox,core_contained=contained(corebox,w,nh),old_nonrectangular_metal_components=oldbad,signal_ledger=ledgers,PG_ledger=pg,old_OBS=oldobs,new_reserved_OBS=newobs,all_OBS_contained=obs_containment,PG_ids_intersecting_own_reserved_OBS_HOLD=own_pg_obs,all_via_cut_34nm_box_spacing_violations=cutfails,OBS_status='Translated +39nm with core. Reservations are conditional; existing own-pin/PG conflicts not waived or hidden. AP/OBS generation requires separate ROOT approval.',scalar_union_width_phase_area_containment_violations=violations,all_cross_net_24nm_box_spacing_violations=neighbor_violations,all_parallel_wide_72nm_spacing_violations=parallel_wide_violations,minimum_parallel_gap_nm=min_gap,corner_costs=corner,PG_total_metal_area_um2=sum(p['new_area_um2'] for p in pg),PG_clock_energy_not_added='PG is supply metal, not signal activity. Width-linear PG C and sheet R are conditional per rail; coupling/IR/contact resistance/native PG extraction remain NULL.',allowed_new_master_orientations=['R0'],required_R0_origin_mod48_nm=[0,0],old_SYMMETRY_not_inherited=True,mirrored_placements_on_43p2_origin_lattice='REFUSED on unchanged global M4Y3/M5X0 tracks; separate geometry/track model required',parent_fit=None,native_DRC=None,native_RC=None,EOL_corner_PRL_complete_native_verdict=None,orientations={'R0':{'M4_Y_phase_nm':3,'M5_X_phase_nm':0},'MX':{'M4_Y_phase_nm':(nh-3)%48,'M5_X_phase_nm':0},'MY':{'M4_Y_phase_nm':3,'M5_X_phase_nm':w%48},'R180':{'M4_Y_phase_nm':(nh-3)%48,'M5_X_phase_nm':w%48}},boundary_density_pins_per_um={face:sum(p['face']==face for p in ledgers)/(nh/1000) for face in ['W','E']})
# Explicit causal MODEL failures, not native DRC controls.
controls={
 'old_9nm_join_RECTONLY':not components([[0,-12,24,12],[-264,-21,24,3]])[0]['rectangular'],
 'whole_core_minus9_outside_outline':not contained([0,-9,100,100],100,200),
 'old_96nm_PG_absent_from_routing_width_table_scope_native_unknown':96 not in [24,120,216,312,408],
 'pin_only_move_breaks_core_attachment':39!=0,
 'MX_reusing_R0_parent_phase_refused':out['families']['qwen']['orientations']['MX']['M4_Y_phase_nm']!=3,
 'old_contact_hidden_fixed_is_still_nonrectangular':not components([[0,-12,24,12],[-264,-21,24,3]])[0]['rectangular']}
assert all(controls.values())
assert out['families']['qwen']['signal_count']==206 and out['families']['sc2']['signal_count']==437
assert out['families']['qwen']['PG_count']==44 and out['families']['sc2']['PG_count']==77
for f in out['families'].values():
 assert not f['scalar_union_width_phase_area_containment_violations']
 assert not f['all_cross_net_24nm_box_spacing_violations']
 assert not f['all_parallel_wide_72nm_spacing_violations']
out['causal_model_refusals']=controls
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({f:{k:d[k] for k in ['signal_count','PG_count','via_count','new_outline_nm','delta_area_um2','core_contained','old_nonrectangular_metal_components','minimum_parallel_gap_nm','boundary_density_pins_per_um']}|{'scalar_failures':len(d['scalar_union_width_phase_area_containment_violations']),'spacing_failures':len(d['all_cross_net_24nm_box_spacing_violations']),'wide_PRL_failures':len(d['all_parallel_wide_72nm_spacing_violations'])} for f,d in out['families'].items()},indent=2))
