#!/usr/bin/env python3
"""Reconcile current HBM functional clusters and physical coverage.

A partial graph is useful only if missing native joins, masters and pins survive
as explicit gaps. No historical slot is silently assigned to a changed master.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path
import die_top_lint as L

BASE=Path('/home/ubuntu/wt')
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def module(p,top):
 r=L.parse_module(str(p),top);return {'master':top,'source':str(p),'source_sha256':digest(p),'ports':{n:{'direction':d,'bits':w} for n,(d,w) in r['ports'].items()},'clock_roots_declared':sum(w for n,(d,w) in r['ports'].items() if d=='input' and ('clk' in n or n.endswith('_rck'))),'geometry':None,'native_parent_join_proved':False}

def graph(root):
 root=Path(root);refs={};nodes={};edges=[];gaps=[]
 def get(name,p):refs[name]={'path':str(p),'sha256':digest(p)};return load(p)
 c=get('die_source_contract',BASE/'hbm-die-feas-1014/results/arch/hbm_die_v15/source_contract/contract.json')
 vmgeo=get('VM_actual_bank_geometry',BASE/'hbm-vm-static-1014/results/arch/hbm_vm_bank_static_1015/native_geometry_for_die_1015.json')
 vmclock_path=BASE/'hbm-vm-static-hub-1014/results/arch/hbm_vm_bank_static_1015/qualified_payload_initial_pin_full_cts/native_qualification.json'
 vmclock=get('VM_native_clock_actual_failure',vmclock_path) if vmclock_path.exists() else None
 abi=get('VM_ABI',BASE/'hbm-vm-static-1014/results/arch/hbm_vm_static_1014/quadrant_abi.json')
 service=get('native_service_bands',BASE/'hbm-die-feas-1014/physical/hbm_accel_die_views/svc/v15/native_bands/contract.json')
 sm=get('actual_SM35_frame',BASE/'sm-dense-pack-1015/results/hbm_sm_dense_pack/complete35.json')
 sm_detail_path=BASE/'sm-dense-pack-1015/results/hbm_sm_dense_pack/canonical_system_inventory.json'
 sm_detail=get('SM_actual_child_inventory',sm_detail_path) if sm_detail_path.exists() else None
 sm_component=get('SM_source_component',Path(sm_detail['source_root'])/sm_detail['source_component']) if sm_detail else None
 eng=get('Engram_8home_candidate',BASE/'hbm-engram-repartition-1015/results/arch/hbm_engram_partition_1015/allocation_manifest.json')
 lg=get('LG_actual_pin_manifest',BASE/'hbm-vm-static-1014/results/arch/hbm_vm_lg_split_1015/pin_manifest.json')
 bridge=get('COLL_bridge_model',BASE/'hcoll-quarter-bridge-1015/results/arch/hcoll_quarter_bridge_1015/model.json')
 legacy=get('historical_geometry',BASE/'hbm-die-feas-1014/results/arch/hbm_die_v14/sm32_repack_probe_1014.json')['full_repack_candidate']['instances']
 # Retain current exact source records except superseded flat LG and service.
 for n,v in c['instances'].items():
  if n.startswith(('lg_','svc_')):continue
  nodes[n]={**copy.deepcopy(v),'source_snapshot':'die_source_contract','geometry':None,'native_parent_join_proved':False}
  if n.startswith('hb_coll_'):nodes[n]['historical_interface_only']=True
  if n.startswith('phy_') and n in legacy and legacy[n][0]==v['master']:
   a=legacy[n];p=root/'physical/asap7_memory_macros_v2'/v['master']/(v['master']+'.lef')
   nodes[n]['geometry']={'xy_um':a[2:4],'outline_um':a[4:6],'orientation':a[6],'status':'FIXED_SHORELINE_MASTER_MATCH_ONLY','pin_geometry_verified':False,'lef':str(p),'lef_sha256':digest(p) if p.exists() else None}
 for top,rec in service['masters'].items():
  for n in rec['instances']:
   instance='svc_'+n.split('hfd_svc_native_')[1]
   nodes[instance]={'master':top,'source':str(BASE/'hbm-die-feas-1014'/rec['source']),'source_sha256':rec['sha256'],'ports':rec['ports'],'clock_sinks_per_leaf':rec['clock_sinks'],'PC_or_ordinal_ids':rec['physical_PC_ids'],'geometry':None,'native_parent_join_proved':False,'source_snapshot':'native_service_bands'}
 # Replace old collective containers with the actual hostV3 source ports.
 host=get('COLL_host_V3',BASE/'hcoll-static-program-1015/results/arch/hcoll_program_join_1015/host_v3_join.json')
 for q in ['SW','SE','NW','NE']:
  top='ot_hfd_coll_q3_static_host_v3' if q=='SW' else 'ot_hfd_coll_q2_static_host_v3';v=host[top]
  nodes['hb_coll_'+q]={'master':top,'ports':{n:{'direction':p['direction'],'bits':p['width']} for n,p in v['ports'].items()},'clock_roots_declared':v['logical_clock_roots'],'source_snapshot':'COLL_host_V3','geometry':None,'native_parent_join_proved':False,'physical_QID':q}
 # Materialize the real native owner/FIFO/SRAM leaf inventory in every band.
 for top,rec in service['masters'].items():
  for inst in rec['instances']:
   parent='svc_'+inst.split('hfd_svc_native_')[1]
   for bid in rec['physical_PC_ids']:
    for role,leaf in service['leaves'].items():
     n=f'{parent}_{role}{bid}'
     nodes[n]={'master':leaf['top'],'source_sha256':leaf['sha256'],'ports':{p:{'direction':v[0],'bits':v[1]} for p,v in leaf['ports'].items()},'parent':parent,'logical_bank_or_PC_id':bid,'geometry':None,'clock_roots_declared':1 if role=='owner' else 2,'logic_sinks_per_root':[1577] if role=='owner' else [2294,213],'native_parent_join_proved':False}
     if role=='bank':
      nodes[n+'_SRAM']={'master':'ot_sram_1r1w_128x256_m1_r2c2','parent':n,'geometry':None,'clock_pins':1,'literal_source_instance':'u_payload','native_parent_join_proved':False}
 # Real command/refresh controllers are SHARED per physical PC, not cloned
 # per client. Current hard PHY abstract includes a different K-port controller
 # interface and cannot silently absorb these command-level outputs.
 queuedroot=BASE/'hbm-die-feas-1014'
 queuedpath=queuedroot/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_sector_queued_stack.sv'
 countpath=queuedroot/'results/arch/hbm_die_v15/native_queued_controller/structure/receipt.json'
 if queuedpath.exists() and countpath.exists():
  queued=get('actual_shared_PC_controller_structure',countpath)
  for q in ['SW','SE','NW','NE']:
   n='HBM_shared_controller_'+q;nodes[n]=module(queuedpath,'ot_hbm_svc_native_sector_queued_stack');nodes[n].update(role='shared per-stack32PC controller container',geometry=None,total_actual_FF=queued['total_FF'],clock_roots_declared=33,clock_period_ps=1024,pc_root_frequency_phase_must_match_status_root=True,protected_state_admitted=False)
   for pc in range(32):nodes[n+f'/pc{pc}']={'role':'one real shared DRAM PC controller + ownerFIFO','parent':n,'geometry':None,'actual_FF_sinks':queued['root_FF_bits'][f'pc_clk[{pc}]'],'ownerFIFO_FF_bits':32*316,'controller_WQ_FF_bits':32*11,'read_reply_FF_bits':273,'clock_roots_declared':1,'clock_period_ps':1024,'actual_R_or_spread':None}
   nodes['phy_'+q]['native_command_interface_missing']=True;nodes['phy_'+q]['role']='historical PHY+controller K-port abstract; native commandPHY not bound'
   for p in ['row_v','row_op','row_bank','row_row','col_v','col_we','col_bank','col_col','col_data','col_strb']:gaps.append({'kind':'missing_command_level_PHY_port','controller':n,'controller_port':p,'bits':nodes[n]['ports'][p]['bits'],'historical_PHY':'phy_'+q})
   gaps.append({'kind':'burst_owner_to_len1_controller_unjoined','controller':n,'native_burst_owner_k_len_max':4,'queued_controller_supported_len':1,'actual_converter_required':True})
 # Revalidate every inherited edge; native band and host ports differ.
 for e in c['known_actual_edges']:
  a,b=e['source'][:2],e['sink'][:2]
  if a[0].startswith('lg_') or b[0].startswith('lg_'):continue
  reason=None
  for n,p in (a,b):
   if n not in nodes or p not in nodes[n].get('ports',{}):reason='CURRENT_MASTER_HAS_NO_SUCH_PORT'
  if not reason:
   for endpoint in [e['source'],e['sink']]:
    width=nodes[endpoint[0]]['ports'][endpoint[1]]['bits']
    if len(endpoint)>2:
     if endpoint[2]<0 or endpoint[2]+e['bits']>width:reason='CURRENT_MASTER_SLICE_OUTSIDE_PORT'
    elif width!=e['bits']:reason='CURRENT_MASTER_PORT_WIDTH_CHANGED'
  if reason:gaps.append({'kind':'superseded_connection','edge':e['name'],'source':a,'sink':b,'bits':e['bits'],'reason':reason})
  else:edges.append({**copy.deepcopy(e),'binding':'original_source_contract','actual_pins_verified':False,'production_transfer_activity':None})
 def edge(name,src,dst,bits,proof,**extra):
  for end in [src,dst]:
   if end[0] not in nodes:raise ValueError('missing node '+str(end))
  edges.append(dict(name=name,source=src,sink=dst,bits=bits,binding=proof,actual_pins_verified=False,production_transfer_activity=None,**extra))
 # Actual 96 bank tap leaves. Each leaf owns its own clock root and three faces.
 ports={p['name']:{'direction':p['direction'],'bits':p['bits']} for p in lg['ports']}
 for q in ['SW','SE','NW','NE']:
  vm='hb_vms_'+q
  for stage in range(3):
   for bank in range(8):
    n=f'lg_{q}_{stage}_bank{bank}'
    nodes[n]={'master':lg['module'],'source_sha256':lg['source_sha256'],'ports':ports,'clock_roots_declared':1,'geometry':None,'scalar_pins':lg['scalar_pin_count'],'quarter':q,'bank':bank,'stage':stage,'read_return':10+4*stage,'write_return':7+4*stage,'native_parent_join_proved':False}
    near=vm if stage==0 else f'lg_{q}_{stage-1}_bank{bank}'
    for role,w in [('rq',17),('wq',281)]:edge(n+'_'+role,[n,'near_'+role],[near,role if stage==0 else 'far_'+role],w,'actual_bank_tap_source_split',source_lsb=0,sink_lsb=bank*w if stage==0 else 0,fixed_tap_edges=2)
    for role,nearport,w in [('rr','rr',257),('w_done','wq_done',1)]:edge(n+'_'+role,[near,nearport if stage==0 else 'far_'+role],[n,'near_'+role],w,'actual_bank_tap_source_split',source_lsb=bank*w if stage==0 else 0,sink_lsb=0,fixed_tap_edges=2)
  for b in range(8):
   n=f'vm_{q}_bank{b}';nodes[n]={'role':'VM physical bank leaf','master':None,'quarter':q,'bank':b,'source_parent':vm,'geometry':None,'provisional_body_um':vmgeo['outline_um'] if q.startswith('N') else [356.4,365.04],'physical_face_groups':vmgeo['faces'] if q.startswith('N') else None,'logic_clock_sink_count':vmgeo['mapped_DFF_sinks'] if q.startswith('N') else None,'SRAM_clock_pins':3,'provisional_body_qualified':False,'actual_initial_native_clock_failure':vmclock if q.startswith('N') else None,'clock_roots_declared':1,'parent_bank_pin_binding_complete':False}
  # Local client roles are real architectural obligations; no invented wrapper.
  for stage,role in enumerate(['SU','SFU','HC']):
   n=f'{role}_{q}';nodes[n]={'role':role,'quarter':q,'master':None,'geometry':None,'source_binding_missing':True}
   for b in range(8):
    tap=f'lg_{q}_{stage}_bank{b}'
    for port,w in [('rq',17),('wq',281)]:edge(f'{n}_{b}_{port}',[n,f'vm_{port}[{b}]'],[tap,'local_'+port],w,'mandatory_local_client_boundary_UNJOINED',fixed_read_return=10+4*stage,fixed_write_return=7+4*stage)
    for port,w in [('rr',257),('w_done',1)]:edge(f'{n}_{b}_{port}',[tap,'local_'+port],[n,f'vm_{port}[{b}]'],w,'mandatory_local_client_boundary_UNJOINED')
 # Four HC_Q names are architectural LG client obligations, not arithmetic copies.
 for q in ['SW','SE','NW','NE']:
  nodes['HC_'+q].update(role='HC local LG tap/client obligation; NOT an arithmetic engine',arithmetic_instance_count=0,engine_binding='HC_ENGINE proposed singleNEengine; kernel join open')
 hcbase=BASE/'hc-static-engine-1014/rtl/hbm_accel/generic/peers/static_hc'
 if (hcbase/'ot_hgi_hc_projection_sys1_static.sv').exists():
  nodes['HC_ENGINE']=module(hcbase/'ot_hgi_hc_projection_sys1_static.sv','ot_hgi_hc_projection_sys1_static')
  nodes['HC_ENGINE'].update(role='ONE actual shared8bank arithmetic engine container',arithmetic_instance_count=1,proposed_VM_quarter='NE',proposed_RG=4,proposed_WG=2,physical_parent_qualified=False,arithmetic_MACs=32,memory_shells=8,arithmetic_SRAMs=80,weight_store64_is_subset_of80=True,maximum_accepted_sum_hop_um=406.491)
  nodes['HC_NATIVE_WRAPPER']=module(hcbase/'ot_hgi_hc_native_sys1_mtp_static.sv','ot_hgi_hc_native_sys1_mtp_static')
  nodes['HC_NATIVE_WRAPPER'].update(role='container, NOT a second arithmetic engine',arithmetic_instance_count=0,contains='HC_ENGINE plus128prefetchSRAM plus2programmeSRAM',native_kernel_instantiated=False,physical_clock_partition_admitted=False,declared_clock_ports_not_physical_root_admission=True)
  for bank in range(8):
   n=f'HC_ENGINE/bank{bank}'
   nodes[n]={'role':'sharedmemory/stage-control shell+4MAC composition obligation','parent':'HC_ENGINE','geometry':None,'MACs':4,'weight_SRAMs':8,'residual_SRAMs':2,'physical_composition_qualified':False,'native_parent_join_proved':False}
  gaps.append({'kind':'single_HC_engine_native_VM_join_open','engine':'HC_ENGINE','LG_tap_roles':['HC_'+q for q in ['SW','SE','NW','NE']],'proposed_quarter':'NE','no_four_engine_replication':True})
  gaps.append({'kind':'HC_commonHBM_root_requires_actual_partition','wrapper':'HC_NATIVE_WRAPPER','prefetch_SRAMs':128,'programme_SRAMs':2,'prefetch_legacy_owner_FF_per_stack':21136,'new_region_source_census_pending':True})
 # Source-exact successor PC prototype profile; predecessor is historical only.
 assignment=root/'results/arch/hbm_system_geometry_1015/physical_assignments/native_PC_340cfd747.json'
 if assignment.exists():
  pcprofile=get('current_native_PC_prototype_assignment',assignment)
  for n,v in nodes.items():
   if n.startswith('HBM_shared_controller_'):
    v['superseded_predecessor']=True;v['replacement_profile']='340cfd747 read1..4 responseSRAM owner; nativefunctional/physical unqualified'
  for q,frame in pcprofile['system_candidate_homes'].items():
   for pc,xy in enumerate(frame['pc_origins_um']):
    n=f'HBM_current_PC_{q}_{pc}'
    nodes[n]={'role':'current candidate sharedPC controller ONEperphysicalPC acrossclients','source_snapshot':'340cfd747','source_assignment_sha256':digest(assignment),'geometry':{'xy_um':xy,'outline_um':pcprofile['outline_um'],'orientation':'R0','status':'PROTOTYPE_RESERVATION_ONLY'},'source_census_FF':13649,'macro_clock_pins':1,'clock_roots_declared':1,'shared_K_mux_extra_logical_FF_not_yet_composed':233,'native_parent_join_proved':False,'physical_qualified':False}
    nodes[n+'/responseSRAM']={'parent':n,'role':'ONEactual128x256 responseSRAM, commoncontroller inventory','geometry':None,'outline_um':[94.824,41.064],'clock_pins':1,'native_parent_join_proved':False}
 # Current IDX parent and literal internal functional clusters from actual source.
 idxbase=root/'rtl/hbm_accel/index';idx='IDX'
 nodes[idx]=module(idxbase/'ot_hbm_idx_parent_static.sv','ot_hbm_idx_parent_static');nodes[idx]['role']='container_not_additional_physical_area'
 for name,top in [('operand','ot_hbm_idx_vm_query_static'),('query','ot_hbm_idx_query_static'),('selector','ot_hbm_idx_selector_static'),('link','ot_hbm_idx_topk_link_static')]+[(f'score{q}','ot_hbm_idx_score_static') for q in range(4)]:
  n='IDX_'+name;nodes[n]=module(idxbase/(top+'.sv'),top);nodes[n]['parent']=idx
 for p in ['block_v','block_head','block_number','block_data','head_weight']:edge('IDX_operand_'+p,['IDX_operand',p],['IDX_query',p],nodes['IDX_operand']['ports'][p]['bits'],'literal_ot_hbm_idx_parent_static')
 for q in range(4):
  for p in ['ql_v','ql_head','ql_codes','ql_sc','ql_w']:edge(f'IDX_query_{q}_{p}',['IDX_query',p],[f'IDX_score{q}',p],nodes['IDX_query']['ports'][p]['bits'],'literal_ot_hbm_idx_parent_static')
  edge(f'IDX_score{q}_selection',[f'IDX_score{q}','score'],['IDX_selector','in_line'],592,'literal_score_field_selection37x16',source_fields='score[290+l*20+:20],score[34+l*16+:16],score[18+l]',sink_lsb=q*592)
 edge('IDX_selected_line',['IDX_selector','selected_line'],['IDX_link','selected_line'],2368,'literal_ot_hbm_idx_parent_static')
 edge('IDX_selected_v',['IDX_selector','selected_v'],['IDX_link','ingest_v'],4,'literal_AND_reduction_in_parent',reduction='AND4_to1')
 # ATT source and canonical NE external boundaries, explicitly not yet parent joined.
 attroot=BASE/'hbm-static-attn-quant-1014';nodes['ATT']=module(attroot/'rtl/hdc/v41x/static/ot_hbm_attention_physical_static_engine.sv','ot_hbm_attention_physical_static_engine');nodes['ATT']['role']='container_not_additional_physical_area'
 nodes['PV_serializer']=module(attroot/'rtl/hdc/v41x/static/ot_hbm_attn_pv_serializer.sv','ot_hbm_attn_pv_serializer')
 edge('ATT_query_request',['ATT','query_rq'],['hb_vms_NE','rq'],136,'canonical_RG3_UNJOINED',sink_lsb=3*136)
 edge('ATT_query_response',['hb_vms_NE','rr'],['ATT','query_rr'],2056,'canonical_RG3_UNJOINED',source_lsb=3*2056)
 for a,b,w in [('pv_data','capture_data',16384),('pv_fault','capture_flags',512)]:edge('ATT_'+a,['ATT',a],['PV_serializer',b],w,'source_layout_matches_component_UNJOINED',production_bit_beats_per_record=w*16)
 edge('ATT_PV_WG1',['PV_serializer','write_data'],['hb_vms_NE','wq'],2048,'canonical_headmajor_WG1_adapter_UNJOINED',required_write_flags=64,commit_edges=128,source_payload_only=True)
 nodes['KV_multistack_service']={'role':'allocation and real producer boundary unresolved','master':None,'geometry':None}
 edge('ATT_KV',['KV_multistack_service','kv_words'],['ATT','kv_words'],8480,'required_real_producer_UNJOINED',current_source_service_bits_per_edge=2048)
 activity_path=attroot/'results/arch/hbm_attention_static_1015/source_activity_model.json'
 activity=get('ATT_actual_source_activity',activity_path) if activity_path.exists() else None
 for tile in range(32):
  n=f'ATT_transpose{tile}';nodes[n]={'role':'mandatory PV transpose payload state','parent':'ATT','master':None,'geometry':None,'payload_DFF_bits':18432,'proposed_half_roots':2,'payload_sinks_per_half_root':9216,'actual_mapped_or_clock_qualified':False}
  for lane in range(2):
   edge(f'ATT_PVfill_transpose_{tile}_{lane}',['ATT',f'staging_lane{lane}_group{tile//2}'],[n,f'fill_lane{lane}'],265,'literal_g_tr_source',XOFF=(tile*16)%32)
  for quad in range(4):edge(f'ATT_transpose_quad_{tile}_{quad}',[n,'expanded_576'],[f'ATT_phys_q{tile}_{quad}','ib'],576,'mandatory_physical_binding_UNJOINED') if f'ATT_phys_q{tile}_{quad}' in nodes else None
 nodes['ATT_PV_flags']={'role':'mandatory PV serializer exact status state','parent':'PV_serializer','geometry':None,'payload_DFF_bits':16384,'minimum_roots_by_15000_limit':2,'mapped_or_clock_qualified':False}
 # Explicit physical inventory from the selected structural precursor. These
 # are local candidate coordinates, never absolute die placements or proof that
 # logical tile to physical pair mapping already exists in a parent netlist.
 candidate_path=root/'results/arch/hbm_system_geometry_1015/candidates.json'
 candidates=get('ATT_structural_precursors',candidate_path)
 att=next(x for x in candidates['candidates'] if x['name']=='bank_affinity')
 for name,b in att['blocks'].items():
  n='ATT_phys_'+name
  nodes[n]={'role':b['role'],'parent':'ATT','master':{'quad':'ot_attn_tile_m6h1q','PVbank':'ot_sram_1r1w_32x128_m1','query':'ot_sram_1r1w_32x128_m1','staging':'ot_sram_1r1w_1024x256_m2_r2c2','programme':'ot_sram_1r1w_1024x256_m2_r2c2'}[b['role']],'geometry':{'outline_um':[b['w'],b['h']],'local_candidate_xy_um':[b['x'],b['y']],'absolute_xy_um':None,'coordinate_frame':'ATT_bank_affinity_candidate','orientation':'R0','pin_geometry_verified':False},'physical_candidate_only':True,'source_hierarchy_binding_proved':False}
 for tile in range(32):
  for quad in range(4):edge(f'ATT_transpose_quad_{tile}_{quad}',[f'ATT_transpose{tile}','expanded_576'],[f'ATT_phys_q{tile}_{quad}','ib'],576,'mandatory_physical_binding_UNJOINED')
 psource=attroot/'results/arch/hbm_attention_static_1015/p_source_model.json'
 if psource.exists():
  get('ATT_P_gather_candidate',psource)
  for b in range(128):nodes[f'ATT_P_candidate_bank{b}']={'role':'additional P gather candidate NOT adopted','master':'ot_sram_1r1w_32x128_m1','geometry':None,'source_hierarchy_binding_proved':False,'parent':'ATT'}
 else:gaps.append({'kind':'missing_P_gather_source_model','required_macros_candidate':128,'additional_macro_area_mm2':0.13680285696})
 # Preserve real full-SM frame instead of inherited smaller slots.
 for s in range(32):
  q=['SW','SE','NW','NE'][s//8];nodes[f'SM{s}']={'role':'SM physical frame','quarter':q,'geometry':{'outline_um':sm['frame_outline_um'],'xy_um':None,'orientation':'R0','status':sm['verdict'],'pin_geometry_verified':False},'source_snapshot':'actual_SM35_frame','current_static_front_binding_pending':True,'retained_child_count':len(sm['children']),'master':sm_component['logical_module'] if sm_component else None,'ports':{p:{'direction':v['direction'],'bits':v['width']} for p,v in sm_component['boundary_ports'].items()} if sm_component else {}}
  edge(f'SM{s}_VM_xload',['hb_vms_'+q,'rr'],[f'SM{s}','xw_data'],2048,'required_native_parent_UNJOINED')
 if sm_detail:
  for s in range(32):
   parent=f'SM{s}'
   for csm in sm_detail['children']:
    n=parent+'/'+csm['instance']
    nodes[n]={'master':csm['logical_module'],'parent':parent,'source_commit':csm['source_commit'],'ports':{p:{'direction':v['direction'],'bits':v['width']} for p,v in csm['boundary_ports'].items()},'geometry':{'local_xy_um':csm['xy_um'],'outline_um':[csm['w_um'],csm['h_um']],'orientation':csm['orientation'],'coordinate_frame':parent,'absolute_xy_um':None,'actual_pin_manifest_available':bool(csm.get('actual_pins')),'actual_pin_reference':'SM_actual_child_inventory/children/'+csm['instance'],'actual_LEF_sha256':csm.get('actual_lef_sha256')},'native_complete_qualified':False,'geometry_status':csm['geometry_status'],'clock_roots_declared':len(csm['clock_roots'])}
   for ce in sm_detail['edges']:
    ds=[e for e in ce['endpoints'] if e['direction']=='output'];ls=[e for e in ce['endpoints'] if e['direction']=='input']
    for d in ds:
     for e in ls:edge(parent+'/'+ce['net'],[parent+'/'+d['instance'],d['port']],[parent+'/'+e['instance'],e['port']],ce['width_bits'],'actual_SM_component_source_candidate',source_lsb=d['lsb'],sink_lsb=e['lsb'],actual_component_pin_distance_max_um=ce['actual_pin_distance_max_um'],actual_component_over500_bits=ce['actual_over500_bit_count'],component_qualification=ce['qualification'])
 # Actual nine SerDes masters and source-defined endpoint groups. The current
 # 544-bit coded coded PMA boundary to 512-pin PHY connection stays an explicit gap.
 capture=get('COLL_capture_group',BASE/'hcoll-static-seq-1015/physical/hcoll_pinreg_ctl_1015/capture_geometry.json')
 serdes=L.S.real_lef(L.S.SERDES_LEF);serdes_path=root/L.S.SERDES_LEF
 refs['actual_SerDes_LEF']={'path':str(serdes_path),'sha256':digest(serdes_path)}
 for n,a in legacy.items():
  if n.startswith('lk_') and a[0]=='ot_pdie_serdes':
   assert [serdes['w'],serdes['h']]==a[4:6]
   nodes[n]={'master':serdes['name'],'geometry':{'xy_um':a[2:4],'outline_um':a[4:6],'orientation':a[6],'actual_local_pin_count':len(serdes['pins']),'source_bound_pin_shapes':True,'status':'ACTUAL_LEF_MATCH_HISTORICAL_SHORELINE_CANDIDATE'},'clock_roots_declared':1,'package_wiring_bound':False}
   ep='COLL_endpoint_'+n
   nodes[ep]={'role':'endpoint physical group candidate','master':'ot_hgi_coll_static_link_capture','geometry':{'outline_um':capture['composed_outline_um'],'absolute_xy_um':None,'physical_native_qualified':False},'roots':5,'actual_parent_join_proved':False,'status':'three store face pins blocked; HOLD adoption'}
   nodes[ep+'_ctl']={'master':'ot_hgi_coll_static_capture_ctl','parent':ep,'logic_DFF_sinks':4421,'geometry':{'local_xy_um':capture['controller']['bbox_um'][:2],'outline_um':capture['controller']['outline_um'],'coordinate_frame':ep,'requested_pins_only':True},'clock_roots_declared':1}
   for st in capture['stores']:
    bn=ep+f'_store{st["bank"]}';nodes[bn]={'role':'one actual64x512SRAM pinreg store','parent':ep,'geometry':{'local_xy_um':st['origin_um'],'outline_um':st['outline_um'],'coordinate_frame':ep,'native_physical_adoption_on_hold':True},'clock_roots_declared':1}
   nodes[ep+'_FEC']=module(root/'rtl/hbm_accel/io_static_20261015/hfd_serdes487_static_window.sv','hfd_serdes487_static_window');nodes[ep+'_FEC']['parent']=ep
   nodes[ep+'_gearbox']=module(root/'rtl/hbm_accel/io_static_20261015/ot_hbm_static_frame_transport.sv','ot_hbm_static_frame_transport');nodes[ep+'_gearbox']['parent']=ep
   edge(ep+'_frame',[ep,'tx_pin_flit'],[ep+'_gearbox','endpoint_tx_frame'],612,'required_endpoint_frame_transport_UNJOINED')
   edge(ep+'_valid',[ep,'tx_pin_v'],[ep+'_gearbox','endpoint_tx_v'],1,'required_inband613th_bit_UNJOINED')
   edge(ep+'_encode',[ep+'_gearbox','transport_tx_word'],[ep+'_FEC','tx'],487,'actual_component_ABI_parentcalendar_UNJOINED')
   edge(ep+'_decode',[ep+'_FEC','rx'],[ep+'_gearbox','transport_rx_word'],487,'actual_component_ABI_parentcalendar_UNJOINED')
   edge(ep+'_PHY_join',[ep+'_FEC','pma_tx'],[n,'tx512'],544,'REQUIRED_PIN_MAP_UNBOUND',physical_pin_width=512)
   edge(ep+'_PHY_return',[n,'rx512'],[ep+'_FEC','pma_rx'],544,'REQUIRED_PIN_MAP_UNBOUND',physical_pin_width=512)
   gaps.append({'kind':'missing_actual_FEC_SerDes_pin_mapping','endpoint':ep,'SerDes':n,'coded_PMA_bits':544,'message_payload_bits':487,'protected_message_bits':512,'actual_PHY_pins':512})
 # Quarter bridge topology uses actual new component widths and root census.
 ring=['SW','SE','NE','NW']
 for rec,q in zip(bridge['quarters'],['SW','SE','NW','NE']):
  n='COLL_bridge_'+q;nodes[n]={'role':'quarter bridge candidate','master':'ot_hgi_coll_quarter_bridge','geometry':None,'quarter':q,'clock_roots_declared':rec['router_clock_roots']+rec['rx_select_roots'],'flops':rec['total_flops'],'max_router_root_flops':rec['max_router_root_flops'],'source_snapshot':'COLL_bridge_model','native_parent_join_proved':False}
 for i,q in enumerate(ring):
  for step in [-1,1]:edge(f'quarter_bridge_{q}_{step}', ['COLL_bridge_'+q,'directional_out'],['COLL_bridge_'+ring[(i+step)%4],'directional_in'],546,'actual_bridge_candidate_UNJOINED',reserved_slots_per_edge=1,clock_reach_required=True)
 # Keep the real8home/rank split; this is an allocation candidate, not sixteen
 # extra engine instances or a replacement for all other96rank duties.
 for rec in eng['intervals']:
  n=f'Engram_L{rec["layer"]}_home{rec["home"]}';nodes[n]={'role':'off_die_memory_extent_candidate','rank':rec['rank'],'stack':rec['stack'],'stack_local_begin':rec['stack_local_begin'],'stack_local_end':rec['stack_local_end'],'geometry':None,'is_on_die_area':False}
  edge(n+'_service',[n,'row_response'],['KV_multistack_service','Engram_dispatch_UNBOUND'],None,'8home_protocol_source_candidate_UNJOINED',bytes_per_row=288)
 # Keep exclusive architecture successors in separate profiles, never sum
 # baseline128 and D2048 or duplicate one shared PC controller per client.
 profiles={}
 profile_sources={
  'D_local_PV_model':attroot/'results/arch/hbm_attention_static_1015/pv_local_D_model.json',
  'D_actual_mapped_TT':attroot/'results/arch/hbm_attention_static_1015/pv_local_D_mapped_TT/record.json',
  'D_actual_NE_join':attroot/'results/arch/hbm_attention_static_1015/pv_local_D_current7b2_NE_gate/receipt.json',
  'QK_score_store':attroot/'results/arch/hbm_attention_static_1015/qk_score_serializer_model.json',
  'SW_Quant_replica':BASE/'hbm-static-quant-engine-1015/results/hbm_static_quant_1015/SW_replica/model_before_RTL.json',
  'PMA_stream_adapter':BASE/'pma-544-512-1015/results/arch/pma512_stream_1015/receipt.json',
  'native_checkpoint_address_plan':BASE/'hbm-die-feas-1014/results/arch/hbm_die_v15/full_native_checkpoint_plan/book.json',
  'HCOLL_actual1180_pin_join':root/'results/arch/hbm_system_geometry_1015/HCOLL_actual_1180_pin_join.json',
 }
 for name,path in profile_sources.items():
  if path.exists():profiles[name]=get(name,path)
  else:gaps.append({'kind':'missing_owned_profile_export','profile':name,'path':str(path)})
 profiles['selection_and_limits']={
  'primary_PV':'D2048 source655f63e8d, functional NE join6d3d380e1; mapped307f0a9cc; physical placement/CTS open',
  'fallback_PV':'canonical128 XOR C; mutually exclusive payload storage with D',
  'SW_Quant':'target125 sourcee219c9689 RG6/WG2 count candidate; RG5/WG1 zero-based both W; NW48 preserved',
  'D_unplaced_critical_logic':['four512b eight-way tile-output muxes','headgroup/lane local selectors','53FF global control','four6688-sink bank clock trees'],
  'whole_system_qualified':False,
  'additional_QK_store':'256 real32x128 macros +32768 statusFF +1024 readflagFF; omitted from current known-box figure and must be reserved before full fit',
  'PMA':'544coded to512PHY ratio16:17 streaming sourceproof; physical oneclk/recovered-clock contract and analog rate remain unbound',
 }
 h1path=root/'results/arch/hbm_system_geometry_1015/forward_D_geometry.json'
 canonical_h1=load(h1path).get('canonical_HEADS1_binding_gap') if h1path.exists() else None
 # Source activity H16 fixture is not canonical G25 production H1 activity.
 profiles['canonical_H1_report_not_native_joined']=canonical_h1
 # Every unknown remains actionable in one report; no fabricated global count.
 for n,v in nodes.items():
  if v.get('geometry') is None or v.get('geometry',{}).get('xy_um') is None:gaps.append({'kind':'missing_current_physical_placement','node':n})
  if not v.get('native_parent_join_proved',False):v['whole_native_qualification']=False
 return {'schema':'opentallas.hbm.system_geometry.current_graph.v1','complete':False,'adoption_allowed':False,'references':refs,'nodes':nodes,'edges':edges,'gaps':gaps,'ATT_H16_component_activity':activity,'ATT_production_activity':{'status':'canonicalG25logicalH1 actualwriter/wholearith/physicaljoinOPEN','owner_report':canonical_h1},'exclusive_successor_profiles':profiles,'mandatory_transpose_payload_FF_bits':589824,'mandatory_PV_flags_FF_bits':16384,'counts':{'functional_or_physical_records':len(nodes),'edges_including_explicit_required_unjoined':len(edges),'actual_pin_verified_edges':0,'native_service_placements':service['instance_count'],'LG_bank_leaves':96,'SM_full_frames':32,'IDX_literal_parent_clock_roots':nodes['IDX']['clock_roots_declared']},'limits':['Mixed hierarchical container/leaf/obligation graph; do not sum node count as physical instances or area.','Inherited contract connections are port-checked only; new native source joins remain explicit.','Unknown widths are null, never zero-width wires or free services.','No complete global wirelength/cut/clock/performance score while any outside paths or physical views are absent.']}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',default='.');p.add_argument('--out',required=True);a=p.parse_args();r=graph(Path(a.root).resolve());Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['counts']))
if __name__=='__main__':main()
