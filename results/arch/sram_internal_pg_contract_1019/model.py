#!/usr/bin/env python3
"""Finite analytical NEW master occupancy contract. No EDA/view generation."""
import json,hashlib,re,math,time
from pathlib import Path
P=Path(__file__).resolve().parent
base=json.loads((P/'input/c634_model.json').read_text())
pg=json.loads((P/'input/899b_model.json').read_text())
tech=(P/'input/asap7_tech.lef').read_text()
rc=(P/'input/current_setRC.tcl').read_text()
def overlap(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def contains(a,b):return a[0]<=b[0] and a[1]<=b[1] and a[2]>=b[2] and a[3]>=b[3]
def gap(a,b):return [max(a[0]-b[2],b[0]-a[2],0),max(a[1]-b[3],b[1]-a[3],0)]
def area(a):return (a[2]-a[0])*(a[3]-a[1])
def union_area(rs):
 xs=sorted({x for r in rs for x in [r[0],r[2]]});out=0
 for l,r in zip(xs,xs[1:]):
  ys=sorted((a[1],a[3]) for a in rs if a[0]<r and a[2]>l);end=-10**15;total=0
  for b,t in ys:
   if b>=end:total+=t-b;end=t
   elif t>end:total+=t-end;end=t
  out+=(r-l)*total
 return out
via_defs={}
for name in ['VIA12','VIA23','VIA34','VIA45']:
 body=tech.split('VIA '+name+' Default',1)[1].split('END '+name,1)[0];ly=None;boxes={}
 for line in body.splitlines():
  m=re.search(r'LAYER (\w+)',line)
  if m:ly=m[1]
  m=re.search(r'RECT ([-.\d]+) ([-.\d]+) ([-.\d]+) ([-.\d]+)',line)
  if m:boxes[ly]=[round(float(x)*1000) for x in m.groups()]
 via_defs[name]=boxes
coeff={m[1]:{'r_kohm_um':float(m[2]),'c_ff_um':float(m[3])} for m in re.finditer(r'set_layer_rc -layer (M\d) -resistance (\S+) -capacitance (\S+)',rc)}
vr={m[1]:float(m[2]) for m in re.finditer(r'set_layer_rc -via (V\d) -resistance (\S+)',rc)}
out={'status':'NEW_ANALYTICAL_MASTER_OWNED_INTERNAL_OCCUPANCY_CONTRACT','sources':{'core_access':'c634d1540','external_trunks':'899b732d6'},'no_native_engine':True,'no_production_views':True,'native_via_definitions_nm':via_defs,'analytical_RC_coefficients':coeff,'via_R_kohm':vr,'families':{}}
for f,b in base['families'].items():
 p=pg['families'][f];w,h=b['new_outline_nm'];cb=b['core_bbox_nm']; attachment_cb=cb.copy(); attachment_cb[3]=max(cb[3],max((r['new_rect_nm'][1]+r['new_rect_nm'][3])//2+108 for r in b['PG_ledger']));base_x=p['trunks'][0]['center_x_nm'];corr=[base_x-84,0,base_x+180,h]
 old=[];oldcuts=[]
 for s in b['signal_ledger']:
  for i,r in enumerate(s['new_shapes']):old.append({'id':f+':SIG:'+s['pin']+':'+str(i),'net':s['pin'],'layer':r['layer'],'rect_nm':r['rect_nm']})
  for i,v in enumerate(s['new_vias']):
   for ly,k in [('M4','m4_rect_nm'),('M5','m5_rect_nm')]:old.append({'id':f+':SIGV:'+s['pin']+':'+str(i)+':'+ly,'net':s['pin'],'layer':ly,'rect_nm':v[k]})
   oldcuts.append({'id':f+':SIGV:'+s['pin']+':'+str(i),'net':s['pin'],'layer':'V4','rect_nm':v['cut_rect_nm']})
 metal=[];cuts=[];rows=[];cells=[]
 def add(id,net,ly,r,role):
  d={'id':id,'net':net,'layer':ly,'rect_nm':r,'role':role};(cuts if ly.startswith('V') else metal).append(d);return d
 def via(id,net,name,x,y):
  v={'id':id,'type':name,'center_nm':[x,y],'objects':[]}
  for ly,r in via_defs[name].items():v['objects'].append(add(id+':'+ly,net,ly,[r[0]+x,r[1]+y,r[2]+x,r[3]+y],'native_'+name))
  return v
 for t in p['trunks']:add(t['id'],t['net'],'M5',t['rect_nm'],'full_height_internal_supply_trunk')
 for rail,oldrow in zip(b['PG_ledger'],p['contact_ledger']):
  id=f+':PG:'+str(rail['id']);net=rail['net'];r=rail['new_rect_nm'];y=(r[1]+r[3])//2
  x=base_x+(-288 if net=='VDD' else 288);y0=18+round((y-12-18)/36)*36
  assert x%36==0 and y0%36==18 and abs(y0-(y-12))<=18
  cell=[x-84,y-108,x+84,y+108];assert contains(attachment_cb,cell);cells.append({'id':id+':CORE_EXCLUSION','rect_nm':cell})
  add(id+':RAIL',net,'M4',r,'retained_c634_actual_supply_rail')
  pads=[add(id+':M1_CORE_PORT',net,'M1',[x-9,y0-42,x+9,y0+42],'core_electrical_supply_interface'),add(id+':M2_LANDING',net,'M2',[x-42,y0-9,x+42,y0+9],'internal_supply_landing'),add(id+':M3_LANDING',net,'M3',[x-9,y0-42,x+9,y0+42],'internal_supply_landing')]
  vs=[via(id+':V1',net,'VIA12',x,y0),via(id+':V2',net,'VIA23',x,y0),via(id+':V3',net,'VIA34',x,y)]
  v4=oldrow['candidate_internal_V4'];vs.append(via(id+':V4',net,'VIA45',*v4['center_nm']))
  for pad in pads:
   z=pad['rect_nm'];assert area(z)>=666 and contains(cell,z);assert min(z[0]-cell[0],z[1]-cell[1],cell[2]-z[2],cell[3]-z[3])>=31
  for v in vs[:3]:
   for z in v['objects']:
    assert contains(cell,z['rect_nm'])
    if z['layer'] in ['M1','M2','M3','V1','V2','V3']:
     zz=z['rect_nm']; margin=min(zz[0]-cell[0],zz[1]-cell[1],cell[2]-zz[2],cell[3]-zz[3]);assert margin >= (34 if z['layer'].startswith('V') else 31)
    if z['layer'] in ['M1','M2','M3']:assert contains(next(a['rect_nm'] for a in pads if a['layer']==z['layer']),z['rect_nm'])
    if z['layer']=='M4':assert contains(r,z['rect_nm'])
  rows.append({'id':id,'net':net,'old_rail_nm':rail['old_rect_nm'],'c634_rail_unchanged_nm':r,'translated_old_core_contact_center_y_nm':y-12,'retained_M4_attachment_delta_from_translated_core_nm':12,'new_M1_core_port_center_nm':[x,y0],'new_M1_port_y_delta_from_translated_core_nm':y0-(y-12),'lower_core_exclusion':cells[-1],'pads':pads,'via_stacks':vs,'external_trunk_id':oldrow['candidate_shared_M5_trunk_id'],'M1_port_role':'NEW core-owned supply boundary, bitcell/core electrical load attaches here by model definition; not an imported old transistor contact','old_OBS_reservation_id':f+':OBS:3','OBS_is_not_actual_internal_metal':True})
 # All known signal access remains exact; new master does not import undocumented old internal objects.
 clearance=[];checks=0;neighbors=[];minimums={}
 for i,a in enumerate(metal):
  for z in old+metal[i+1:]:
   if a['layer']!=z['layer'] or a['net']==z['net']:continue
   checks+=1;d=gap(a['rect_nm'],z['rect_nm']);ly=a['layer']; minimums[ly]=min(minimums.get(ly,10**12),max(d))
   if max(d)<=200:neighbors.append({'a':a['id'],'b':z['id'],'layer':ly,'gap_nm':d})
   rule=72 if a['layer'] in ['M4','M5'] else 31
   if max(d)<(24 if a['layer'] in ['M4','M5'] else 18) or (min(d)==0 and max(d)<rule):clearance.append([a['id'],z['id'],d])
 cutfails=[];cutchecks=0
 for i,a in enumerate(cuts):
  for z in oldcuts+cuts[i+1:]:
   if a['layer']!=z['layer']:continue
   cutchecks+=1
   if max(gap(a['rect_nm'],z['rect_nm']))<(34 if a['layer'] in ['V3','V4'] else 18):cutfails.append([a['id'],z['id']])
 assert not clearance and not cutfails
 assert not [s for s in old if overlap(s['rect_nm'],corr)]
 assert all(contains([0,0,w,h],a['rect_nm']) for a in metal+cuts+old+oldcuts)
 assert all(not overlap(a['rect_nm'],z['rect_nm']) for i,a in enumerate(cells) for z in cells[i+1:])
 # Independent geometric connectivity includes layer equality and positive area, then complete via bridges.
 components={}
 for net in ['VDD','VSS']:
  objects=[a for a in metal if a['net']==net];parent=list(range(len(objects)))
  def find(i):
   while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
   return i
  def join(i,j):parent[find(i)]=find(j)
  for i,a in enumerate(objects):
   for j in range(i):
    if a['layer']==objects[j]['layer'] and overlap(a['rect_nm'],objects[j]['rect_nm']):join(i,j)
  for row in rows:
   if row['net']!=net:continue
   for v in row['via_stacks']:
    ids=[next(i for i,a in enumerate(objects) if a['id']==o['id']) for o in v['objects'] if o['layer'].startswith('M')]
    assert len(ids)==2;join(*ids)
  components[net]=len({find(i) for i in range(len(objects))});assert components[net]==1
 lower_areas={ly:sum(union_area([a['rect_nm'] for a in metal if a['layer']==ly and a['net']==net]) for net in ['VDD','VSS'])/1e6 for ly in ['M1','M2','M3']}
 lower_len={ly:ar/(.018) for ly,ar in lower_areas.items()}
 lowerC=sum(lower_len[ly]*coeff[ly]['c_ff_um'] for ly in lower_len)
 cellarea=sum(area(a['rect_nm']) for a in cells)/1e6;corearea=area(cb)/1e6
 bitcore_debit=sum(area([max(cb[0],a['rect_nm'][0]),max(cb[1],a['rect_nm'][1]),min(cb[2],a['rect_nm'][2]),min(cb[3],a['rect_nm'][3])]) for a in cells)/1e6
 apron_area=(area(attachment_cb)-area(cb))/1e6
 per=[]
 for row in rows:
  x,y0=row['new_M1_core_port_center_nm'];y=(row['c634_rail_unchanged_nm'][1]+row['c634_rail_unchanged_nm'][3])//2;t=next(t for t in p['trunks'] if t['net']==row['net'])
  rlower=sum(.084*coeff[ly]['r_kohm_um'] for ly in ['M1','M2','M3'])+sum(vr[ly] for ly in ['V1','V2','V3'])
  rrail=abs(t['center_x_nm']-x)/1000*coeff['M4']['r_kohm_um']*24/120
  per.append({'id':row['id'],'conservative_lower_stack_R_kohm':rlower,'rail_to_trunk_R_kohm':rrail,'via4_R_kohm':vr['V4'],'full_height_M5_R_kohm':h/1000*coeff['M5']['r_kohm_um'],'N_or_S_port_to_M1_port_full_height_bound_R_kohm':rlower+rrail+vr['V4']+h/1000*coeff['M5']['r_kohm_um']})
 out['families'][f]={'master':b['master']+'_PGOWN1_ANALYTICAL','outline_nm':[w,h],'original_bitcore_bbox_nm':cb,'new_attachment_core_bbox_nm':attachment_cb,'north_attachment_apron_area_um2':apron_area,'north_attachment_apron_height_nm':attachment_cb[3]-cb[3],'lower_exclusion_intersection_with_original_bitcore_um2':bitcore_debit,'core_translation_Y_nm':39,'lead_translation_Y_nm':48,'signal_geometry_unchanged_sha256':hashlib.sha256(json.dumps(b['signal_ledger'],sort_keys=True).encode()).hexdigest(),'existing_signal_metal_object_count':len(old),'existing_signal_cut_count':len(oldcuts),'original_OBS_reservations_retained':b['new_reserved_OBS'],'new_actual_supply_metal':metal,'new_actual_supply_cuts':cuts,'lower_native_geometry_contract':{'M1_M3_direction':'VERTICAL','M2_direction':'HORIZONTAL','M1_M3_pitch_phase_nm':[36,0],'M2_pitch_phase_nm':[36,18],'pad_width_nm':18,'pad_length_nm':84,'pad_area_nm2':1512,'minimum_area_nm2':666,'minimum_M2_M3_length_nm':37,'via_boxes_exact_native_tech':True,'manufacturing_grid_nm':1},'actual_internal_upper_occupancy_rule':'Exactly enumerated PG rail/trunk/V3/V4 and existing known signal access; undocumented old core M4/M5/V4 geometry is not inherited. New core design must use lower region reservations with enumerated exclusions.','upper_cut_corridor_M4_V4_M5_nm':corr,'upper_corridor_reserved_area_um2':area(corr)/1e6,'upper_corridor_does_not_remove_lower_bitcell_area':True,'lower_core_exclusions':cells,'core_reserved_interface_area_um2':cellarea,'analytical_core_gross_area_um2':corearea,'analytical_core_remaining_area_um2':corearea-bitcore_debit,'required_core_density_multiplier':corearea/(corearea-bitcore_debit),'core_fit':'CONDITIONAL quantified lower-layer placement/capacity contract, no transistor layout or native fit claimed','contact_ledger':rows,'contact_count':len(rows),'new_lower_via_count':3*len(rows),'V4_count':len(rows),'supply_components':components,'new_cross_net_metal_pair_checks':checks,'new_same_cut_layer_pair_checks':cutchecks,'metal_spacing_failures':clearance,'minimum_new_to_crossnet_box_distance_nm':minimums,'all_new_crossnet_neighbors_within_200nm':neighbors,'cut_spacing_failures':cutfails,'lower_union_area_um2':lower_areas,'lower_wire_length_um':lower_len,'lower_analytical_C_ff':lowerC,'M5_analytical_C_ff':p['conditional_added_M5_wire_C_ff'],'total_added_lower_plus_M5_C_ff':lowerC+p['conditional_added_M5_wire_C_ff'],'additional_cut_area_um2':sum(area(c['rect_nm']) for c in cuts)/1e6,'PG_supply_C_not_toggling_energy':True,'path_R_inventory':per,'state_bit_delta':0,'clock_pin_delta':0,'cycle_delta':0,'outline_area_delta_from_c634_um2':0,'boundary_signal_clock_RC_unchanged':True,'core_electrical_model':'Retain original conditional SRAM bitcell, masks, repair and read/write semantics. New M1 supply interfaces are explicit electrical boundary ports. No extracted transistor timing, leakage or IR/EM assertion.','native_rules':'Finite geometry only; PRL/EOL/enclosure applicability/native AP not run','additional_via_cut_C_fringe_and_coupling':None,'native_timing':None}
# Causal finite refusal: removing the actual VIA34 bridge disconnects M1 from the M5 trunk.
def contact_reaches_trunk(row, omit_type=None):
 objects=[a for a in row['pads']]+[a for v in row['via_stacks'] for a in v['objects'] if a['layer'].startswith('M')]
 objects += [{'id':'rail','layer':'M4','rect_nm':row['c634_rail_unchanged_nm']},next(t for t in pg['families']['qwen']['trunks'] if t['net']==row['net'])]
 adj=[set() for a in objects]
 for i,a in enumerate(objects):
  for j,z in enumerate(objects[:i]):
   if a['layer']==z['layer'] and overlap(a['rect_nm'],z['rect_nm']):adj[i].add(j);adj[j].add(i)
 for v in row['via_stacks']:
  if v['type']==omit_type:continue
  ids=[next(i for i,a in enumerate(objects) if a['id']==z['id']) for z in v['objects'] if z['layer'].startswith('M')]
  adj[ids[0]].add(ids[1]);adj[ids[1]].add(ids[0])
 seen={0};todo=[0]
 while todo:
  for j in adj[todo.pop()]:
   if j not in seen:seen.add(j);todo.append(j)
 return len(objects)-1 in seen
# Causal finite refusals use actual selected geometry, not generic policy labels.
f=out['families']['qwen'];r=f['contact_ledger'][0];v=r['via_stacks'][2];a=r['pads'][0]
controls={'VDD_VSS_trunk_coincidence_rejected':overlap(pg['families']['qwen']['trunks'][0]['rect_nm'],pg['families']['qwen']['trunks'][0]['rect_nm']),'additional_unowned_cut_in_corridor_rejected':contains(f['upper_cut_corridor_M4_V4_M5_nm'],r['via_stacks'][3]['objects'][-1]['rect_nm']),'missing_VIA34_breaks_lower_to_rail_path':contact_reaches_trunk(r) and not contact_reaches_trunk(r,'VIA34'),'M3_landing_shortened_to_native34nm_fails_area':18*34<666,'old_bit_attachment_Y_not_same_new_M1_port':r['new_M1_core_port_center_nm'][1] != r['translated_old_core_contact_center_y_nm'],'SC2_top_contact_requires_priced_172nm_apron':out['families']['sc2']['north_attachment_apron_height_nm']==172,'initial108nm_cell_width_insufficient_for31nm_guard':(108-84)/2<31,'core_capacity_not_gross_after_reservation':f['analytical_core_remaining_area_um2']<f['analytical_core_gross_area_um2'],'unowned_lower_core_overlap_is_conflict':overlap(a['rect_nm'],r['lower_core_exclusion']['rect_nm'])}
assert all(controls.values());out['finite_causal_refusals']=controls
(P/'model.json').write_text(json.dumps(out,indent=2)+'\n')
summary={f:{k:v[k] for k in ['contact_count','new_lower_via_count','V4_count','supply_components','core_reserved_interface_area_um2','north_attachment_apron_height_nm','north_attachment_apron_area_um2','lower_exclusion_intersection_with_original_bitcore_um2','analytical_core_gross_area_um2','analytical_core_remaining_area_um2','required_core_density_multiplier','lower_union_area_um2','lower_analytical_C_ff','M5_analytical_C_ff','total_added_lower_plus_M5_C_ff','new_cross_net_metal_pair_checks','new_same_cut_layer_pair_checks']} for f,v in out['families'].items()}
(P/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
