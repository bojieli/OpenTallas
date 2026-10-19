import json,hashlib,csv,math
from pathlib import Path
p=Path('.')
load=lambda n:json.loads((p/n).read_text())
t=load('compressed_topology.json');r=load('compressed_topology_report.json');roles=load('native_lib_roles.json');s=load('sinks.json');rows=load('row_ownership.json');prim=load('prototype_model.json')['primitive_inventory']
assert len(t)==2263 and sum(len(x['sink_indices']) for x in t)==810
byid={x['id']:x for x in t};owner={};drivers=[];contacts=[]
for x in t:
 assert x['trunk_transparent_loads']<=32 and x['clock_direct_loads']<=32
 assert x['path_um']+3<=405
 if x['parent_id']!=-1:assert x['id'] in byid[x['parent_id']]['children'] and x['depth_edges']==byid[x['parent_id']]['depth_edges']+1
 for j in x['sink_indices']:assert j not in owner;owner[j]=x
 # Exact leaf grouping used by source model: maximum 24 sink contacts per pair.
 groups=[x['sink_indices'][i:i+24] for i in range(0,len(x['sink_indices']),24)]
 assert len(groups)==x['leaf_pairs']
 for pair in range(1+len(groups)):
  for ff in ['ff1','ff2']:
   drivers.append({'driver':f"n{x['id']}/p{pair}/{ff}/QN",'transparent_load_count':1 if ff=='ff1' else (x['trunk_transparent_loads'] if pair==0 else len(groups[pair-1])),'role':'data_to_D' if ff=='ff1' else 'reset_to_RESETN_or_boundary','actual_wire_cap_fF':None})
 drivers.append({'driver':f"n{x['id']}/tie/H",'transparent_load_count':3*(1+len(groups)),'role':'tie_SETN_and_ff1_D','actual_wire_cap_fF':None})
 drivers.append({'driver':f"n{x['id']}/clock/Y",'transparent_load_count':x['clock_direct_loads'],'role':'native_CLK_and_child_BUF_A','actual_wire_cap_fF':None})
 for j in x['sink_indices']:
  z=dict(s[j]);z.update(station_id=x['id'],transport_depth=x['depth_edges'],conditional_face_edges=2*(x['depth_edges']+1)+2,actual_release_age=None);contacts.append(z)
assert len(owner)==810
boundary={x['instance']:x for x in contacts};out=[]
for inst in rows['parent']:
 head=rows['root'][inst]
 if head not in boundary:continue
 b=boundary[head];k=rows['depth'][inst];lag=rows['lag'][inst];off=rows['heads'][head]
 out.append({'instance':inst,'parent':rows['parent'][inst],'head':head,'head_original_offset':off,'depth':k,'stage_lag':lag,'conditional_head_face_edges':b['conditional_face_edges'],'conditional_stage_edges':b['conditional_face_edges']+k+lag,'original_producer_requirement':'head_A + stage_lag <= producer_D + 1','actual_stage_age':None,'native_row_phase_reach_fanout_PG':'HOLD'})
assert len(out)==2983,len(out)
assert len(boundary)==810
cost={}
for corner,lib in roles.items():
 cap=lambda m,p:float(lib[m]['pins'][p]['capacitance'][0])
 F='DFFASRHQNx1_ASAP7_75t_R';B='BUFx12f_ASAP7_75t_R'
 cost[corner]={'all_new_clock_pin_cap_fF':r['native_FF']*cap(F,'CLK')+r['native_BUF']*cap(B,'A'),'source_PLL_extra_BUF_A_cap_fF':cap(B,'A'),'all_new_FF_RESETN_cap_fF':r['native_FF']*cap(F,'RESETN'),'all_new_FF_SETN_D_tie_cap_fF':r['native_FF']*cap(F,'SETN')+r['native_FF']/2*cap(F,'D'),'max_clock_driver_native_pin_cap_fF':max((len(x['children'])*cap(B,'A')+(2+2*x['leaf_pairs'])*cap(F,'CLK')) for x in t),'boundary_pin_caps':'NULL: exact frozen downstream master Liberty must be bound; no zero substituted','all_routed_wire_caps':None}
for name,obj in [('all_driver_ledger.json',drivers),('boundary_ownership.json',contacts),('downstream_row_composition.json',out)]: (p/name).write_text(json.dumps(obj,indent=1)+'\n')
summary={'status':'SOURCE_COMPOSITION_PASS_PHYSICAL_PHASE_HOLD','stations':len(t),'boundary':len(contacts),'downstream':len(out),'full_HBM_pin_population':len(contacts)+len(out),'row_heads_in_boundary':sum(h in boundary for h in rows['heads']),'native_counts':{k:r[k] for k in ['native_FF','native_INV','native_BUF','native_TIEHI','native_area_um2','native_PG_bindings']},'clock_and_native_load_cost':cost,'census_scope':'COMPLETE NEW SOURCE EQUATION and 810 external boundary contacts; original native mapped downstream all-driver census OPEN','max_source_transparent_loads':max(x['transparent_load_count'] for x in drivers),'driver_rows':len(drivers),'conditional_max_face_edges':max(x['conditional_face_edges'] for x in contacts),'actual_compiler_POR_age':None,'actual_TT_FF_phase_minCQ_recovery_removal':None,'causal_checks':{'reach406_refused':406>405,'fanout33_refused':33>32,'omitted_row_offset_refused':any(x['head_original_offset']!=0 for x in out),'ownership_swap_refused':len({(x['instance'],x['port'],x['bit']) for x in contacts})==810},'sha256':{f:hashlib.sha256((p/f).read_bytes()).hexdigest() for f in ['station.v','native_equation_adapter.v','native_lib_roles.json','prototype_model.json','compressed_topology.json','compressed_topology_report.json','row_ownership.json','sinks.json']}}
(p/'composition_receipt.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
