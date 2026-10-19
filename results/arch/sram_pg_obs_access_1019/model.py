#!/usr/bin/env python3
"""Finite conditional access model. No EDA, view generator, or adoption."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
src=json.loads((P/'input/c634_model.json').read_text())
def overlap(a,b): return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def contains(a,b): return a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]
def gap(a,b): return [max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0)]
result={'status':'CONDITIONAL_INTERNAL_TRUNK_MODEL_EXTERNAL_M5_APPROACH_ONLY_INTERNAL_OBS_HOLD','source_commit':'c634d1540','checker_source_commit':'6cb3f2b704','families':{},'native_engine_run':False,'production_views_generated':False}
for family,v in src['families'].items():
 w,h=v['new_outline_nm']; base=round((w//2)/48)*48
 trunks=[{'id':family+':candidate:M5:'+net,'net':net,'layer':'M5','rect_nm':[x-12,0,x+12,h],'center_x_nm':x,'north_port_nm':[x-12,h-84,x+12,h],'south_port_nm':[x-12,0,x+12,84]} for net,x in [('VDD',base),('VSS',base+96)]]
 original=[]; original_cuts=[]
 for p in v['signal_ledger']:
  for i,s in enumerate(p['new_shapes']): original.append(dict(id=f"{family}:signal:{p['pin']}:{i}",net=p['pin'],layer=s['layer'],rect_nm=s['rect_nm']))
  for i,via in enumerate(p['new_vias']):
   for layer,key in [('M4','m4_rect_nm'),('M5','m5_rect_nm')]: original.append(dict(id=f"{family}:via:{p['pin']}:{i}:{layer}",net=p['pin'],layer=layer,rect_nm=via[key]))
   original_cuts.append(dict(id=f"{family}:via:{p['pin']}:{i}",net=p['pin'],rect_nm=via['cut_rect_nm']))
 for p in v['PG_ledger']: original.append(dict(id=f"{family}:PG:{p['id']}",net=p['net'],layer=p['layer'],rect_nm=p['new_rect_nm']))
 rows=[]; additions=list(trunks); cuts=[]; duplicates={}; allpg=[]
 for p in v['PG_ledger']:
  key=p['net']+':'+str(p['new_rect_nm']); duplicates.setdefault(key,[]).append(p['id'])
  rail=p['new_rect_nm']; t=next(t for t in trunks if t['net']==p['net']);x=t['center_x_nm'];y=(rail[1]+rail[3])//2
  via={'id':f"{family}:candidate:V4:{p['id']}",'net':p['net'],'center_nm':[x,y],'cut_rect_nm':[x-12,y-12,x+12,y+12],'m4_rect_nm':[x-23,y-12,x+23,y+12],'m5_rect_nm':[x-12,y-23,x+12,y+23]}
  assert contains(rail,via['m4_rect_nm']) and contains(t['rect_nm'],via['m5_rect_nm'])
  assert x%48==0 and y%48==3
  assert (t['north_port_nm'][2]-t['north_port_nm'][0])*(t['north_port_nm'][3]-t['north_port_nm'][1])>=2000
  assert (t['south_port_nm'][2]-t['south_port_nm'][0])*(t['south_port_nm'][3]-t['south_port_nm'][1])>=2000
  obs=[dict(id=f"{family}:OBS:{i}",layer=o['layer'],rect_nm=o['rect_nm']) for i,o in enumerate(v['new_reserved_OBS']) if o['layer']=='M4' and overlap(o['rect_nm'],via['m4_rect_nm'])]
  row={'id':f"{family}:PG:{p['id']}",'net':p['net'],'source_original_M4_rect_nm':p['old_rect_nm'],'source_core_plus39_M4_rect_nm':[rail[0],p['old_rect_nm'][1]+39,rail[2],p['old_rect_nm'][3]+39],'c634_M4_rail_unchanged_nm':rail,'c634_internal_attachment_plus12_nm_preserved':True,'candidate_internal_V4':via,'candidate_shared_M5_trunk_id':t['id'],'external_approach':['N_M5','S_M5'],'source_internal_contact_and_strap_status':'CONDITIONAL_NOT_IMPLEMENTED_OR_EXTRACTED','via_enclosure_geometry_pass':True,'M4_bottom_metal_contained_in_existing_rail':True,'M5_top_metal_contained_in_shared_trunk':True,'own_M4_OBS_conflicts':obs,'external_M5_port_OBS_conflicts':[f"{family}:OBS:{i}" for i,o in enumerate(v['new_reserved_OBS']) if o['layer']=='M5' and overlap(o['rect_nm'],t['rect_nm'])],'internal_OBS_native_exception':'NONE_DEMONSTRATED; routing OBS has independent owner; CUT-only parser exception does not apply','qualification':'HOLD_INTERNAL_M4_OBS_ATTACHMENT; EXTERNAL_M5_COORDINATES_ONLY'}
  assert len(obs)==1 and not row['external_M5_port_OBS_conflicts']
  rows.append(row);cuts.append(dict(id=via['id'],net=p['net'],rect_nm=via['cut_rect_nm']))
  additions.extend([dict(id=via['id']+':M4',net=p['net'],layer='M4',rect_nm=via['m4_rect_nm']),dict(id=via['id']+':M5',net=p['net'],layer='M5',rect_nm=via['m5_rect_nm'])])
 failures=[];mindist={};cutfails=[]
 for i,a in enumerate(additions):
  for b in original+additions[i+1:]:
   if a['net']==b['net'] or a['layer']!=b['layer']:continue
   d=gap(a['rect_nm'],b['rect_nm']);key=a['layer'];mindist[key]=min(mindist.get(key,10**12),max(d))
   if d[0]<24 and d[1]<24:failures.append([a['id'],b['id'],'24nm_box_spacing',d])
   # Conservative 72nm spacing whenever projections overlap, including minimum-width pair.
   if min(d)==0 and max(d)<72:failures.append([a['id'],b['id'],'conservative_72nm_parallel',d])
 for i,a in enumerate(cuts):
  for b in original_cuts+cuts[i+1:]:
   d=gap(a['rect_nm'],b['rect_nm'])
   if max(d)<34:cutfails.append([a['id'],b['id'],d])
 assert not failures and not cutfails
 assert all(contains([0,0,w,h],s['rect_nm']) for s in additions)
 total_m5_um=2*h/1000;totalarea=2*24*h/1e6
 # V4 M4/M5 metal is wholly contained in existing M4 rail/new shared M5 trunk.
 # No duplicate area charged for via enclosure rectangles.
 result['families'][family]={'source_master':v['master'],'outline_unchanged_nm':[w,h],'core_unchanged_nm':v['core_bbox_nm'],'allowed_orientation':['R0'],'origin_mod48_nm':[0,0],'contact_count':len(rows),'unique_original_same_net_rails':len(duplicates),'duplicate_contact_groups':[a for a in duplicates.values() if len(a)>1],'trunks':trunks,'contact_ledger':rows,'candidate_crossnet_spacing_failures':failures,'candidate_cut34_spacing_failures':cutfails,'minimum_new_to_crossnet_box_max_distance_nm':mindist,'added_internal_V4_count':len(cuts),'added_M4_union_area_um2':0,'added_M5_union_area_um2':totalarea,'added_cut_union_area_um2':len(cuts)*24*24/1e6,'new_outline_area_um2':0,'additional_clock_pins':0,'cycle_delta_model':0,'PG_no_toggle_energy_claim':True,'conditional_added_M5_wire_C_ff':total_m5_um*0.164264,'conditional_each_full_height_M5_R_kohm':h/1000*0.0189935,'conditional_each_V4_R_kohm':0.0118,'contact_R_coupling_IR_EM_supply_drop':None,'timing_min_max_CQ_setup_hold':None,'external_M5_ports':'Two 84nm-long port subsets per trunk, exactly >=2000nm2; both need parent supply geometry and native PG access qualification','native_internal_M4_OBS_status':'ALL_CONTACTS_HOLD_NO_EXCEPTION','native_rule_coverage':'Not executed. RECTONLY/spacing/enclosure coordinates are finite models; EOL/corner/table/OBS/PG native checks remain open.'}
assert sum(v['contact_count'] for v in result['families'].values())==121
result['finite_geometry_controls']={'direct_M4_approach_intersects_OBS_all121':all(len(r['own_M4_OBS_conflicts'])==1 for v in result['families'].values() for r in v['contact_ledger']),'coincident_VDD_VSS_candidate_trunks_overlap':overlap([0,0,24,100],[0,0,24,100]),'adjacent48nm_track_gap24_below_conservative72':gap([0,0,24,100],[48,0,72,100])[0]<72,'positive_area_full_ports':all((t['north_port_nm'][2]-t['north_port_nm'][0])*(t['north_port_nm'][3]-t['north_port_nm'][1])>=2000 for v in result['families'].values() for t in v['trunks'])}
assert all(result['finite_geometry_controls'].values())
result['policy_refusals_not_native_tests']=['unsupported routing-OBS same-net waiver','erase reservations','infer internal legality from clear external port','double-count contained via enclosures','inherit mirrored orientation']
(P/'model.json').write_text(json.dumps(result,indent=2)+'\n')
(P/'summary.json').write_text(json.dumps({f:{k:v[k] for k in ['contact_count','unique_original_same_net_rails','added_internal_V4_count','added_M5_union_area_um2','added_cut_union_area_um2','conditional_added_M5_wire_C_ff','conditional_each_full_height_M5_R_kohm','native_internal_M4_OBS_status']} for f,v in result['families'].items()},indent=2)+'\n')
print((P/'summary.json').read_text())
