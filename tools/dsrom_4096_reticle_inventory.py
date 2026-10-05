#!/usr/bin/env python3
"""Pinned current4096 packing inputs and per-element storage/compute envelopes. No RTL/P&R/payload."""
import argparse,collections,hashlib,json,math,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PIN='4c8b7f2d8e246bd09250051fc8f7cb3e3340f574'
PINS={}
def read(path):
 b=subprocess.check_output(['git','show',PIN+':'+path],cwd=ROOT);PINS[path]=hashlib.sha256(b).hexdigest();return b

def js(path):return json.loads(read(path))
def lef_view(text):
 size=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text)
 symmetry=re.search(r'\bSYMMETRY\s+([^;]+)',text)
 pins=[]
 for match in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*(?:\n|$)',text,re.S):
  name,body=match.groups();use=re.search(r'\bUSE\s+(\w+)',body);direction=re.search(r'\bDIRECTION\s+(\w+)',body)
  layers=re.findall(r'\bLAYER\s+(\w+)',body)
  pins.append({'name':name,'use':use[1] if use else None,'direction':direction[1] if direction else None,'layers':sorted(set(layers)),'rectangles_um':[list(map(float,r)) for r in re.findall(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body)]})
 obs=text.split('\n  OBS',1)[1] if '\n  OBS' in text else ''
 obstruction=[];layer=None
 for line in obs.splitlines():
  m=re.search(r'\bLAYER\s+(\w+)',line)
  if m:layer=m[1]
  r=re.search(r'\bRECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',line)
  if r:obstruction.append({'layer':layer,'rectangle_um':list(map(float,r.groups()))})
 return {'outline_um':[float(size[1]),float(size[2])],'symmetry':symmetry[1].split() if symmetry else [],'pin_count':len(pins),'pin_uses':dict(collections.Counter(p['use'] for p in pins)),'signal_pin_layers':sorted({l for p in pins if p['use']=='SIGNAL' for l in p['layers']}),'clock_and_PG_pins':[p for p in pins if p['use'] in ('CLOCK','POWER','GROUND')],'OBS':obstruction,'signal_port_names':[p['name'] for p in pins if p['use'] in ('CLOCK','SIGNAL')]}
def placement(text):
 body=re.search(r'set ot_macros\s*\{(.*?)\n\}',text,re.S)[1]
 return [{'relative_instance':n,'requested_origin_um':[float(x),float(y)],'orientation':o,'capture_fix':int(c)} for n,x,y,o,c in re.findall(r'\{([^}]+)\}\s+([\d.]+)\s+([\d.]+)\s+(\w+)\s+(\d+)',body)]
def fixed_capacity(required_bits,depth,width):
 return math.ceil(required_bits/(depth*width))
def envelope(inventory,wake):
 """Keep physical ROM area, frame reservation and repair increments separate."""
 macro=inventory['macro_catalog']['ot_rom_4096x274_m8']['area_breakdown']
 classes={}
 for name,key in [('q_pair','q'),('BF16_column_pair','column')]:
  c=inventory['composite_classes'][name];w=wake['elements'][key]
  area=math.prod(c['outline_um']);rom=4*macro['macro_area_um2'];cells=4*macro['data_array_area_um2']
  classes[name]={'outline_um':c['outline_um'],'frame_area_um2':area,
   'logical_slots':2,'ROMs_per_logical_slot':2,'physical_ROMs':4,
   'ROM_rows':4096,'ROM_word_bits':274,'gross_storage_bits':4*4096*274,
   'gross_storage_bytes':4*4096*274//8,'gross_storage_is_not_tensor_payload':True,
   'ROM_macro_area_um2':rom,'ROM_data_bitcell_area_um2':cells,
   'ROM_peripheral_taps_control_outline_area_um2':rom-cells,
   'adjacent_compute_control_wires_margin_reservation_um2':area-rom,
   'pure_compute_measured_area_um2':None,
   'boundary_bits_per_cycle':w['boundary_bits_per_cycle'],
   'local_signal_tracks_needed':w['local_signal_tracks_needed'],
   'channel_tracks_estimate':w['channel_tracks_estimate'],
   'existing_boundary_register_bits':w['existing_boundary_register_bits'],
   'local_ICGs':inventory['clock_PG']['local_ICGs_per_element'],
   'WAKE_opt_in_separate_increment':{k:w[k] for k in ['extra_register_bits','extra_gate_count','extra_area_um2_upper','incremental_placement_um2_at_50pct']},
   'repair_increment_not_added_to_frame_without_shared_placement_accounting':True,
   'orientations':inventory['placement_contract']['template_orientations'],
   'whole_element_hard_abstract_available':False}
  classes[name]['source_port_contract']={
   'q_activation_codes_bits':512,'q_activation_exponents_bits':20,
   'q_stream_valid_pair_block_slotvalid_position_bits':17,
   'q_stream_total_bits':549,
   'BF16_stream_data_bits':1024 if key=='column' else 0,
   'BF16_stream_metadata_bits':43 if key=='column' else 0,
   'config_valid_address_data_bits':54,
   'return_partial_per_NB_bits':63,'return_partial_NB2_bits':126,
   'busy_fault_bits':2,'clk_reset_pins':2,
   'weight_ROM_captured_bits_per_active_cycle':548,
   'weight_ROM_captured_bytes_per_active_cycle':68.5,
   'pingpong_each_leaf_period_cycles':2,
   'source_XD_pipeline_parameter_cycles':3,
   'source':'rtl/v41rom/ot_v41_rom_elem_w10.sv and ot_v41_rom_elem_q_w10.sv',
   'boundary_excludes_config_return_status_clock_reset':True,
   'fanout_replication_requires_shared_parent_routing_budget':True}
  if key=='column':
   classes[name]['retained_BF16_c8_anchor']={k:w[k] for k in ['baseline_core_um2','baseline_stdcell_um2','baseline_macro_um2','spare_placement_um2']}
   classes[name]['arithmetic']=wake['compute']['bf16_modes']['columns']
  else:
   classes[name]['arithmetic']={k:v for k,v in wake['compute'].items() if k!='bf16_modes'}
 return {'schema':'opentallas.DSROM4096.element_envelope.v1','source_commit':PIN,
  'classes':classes,'whole_model_capacity_must_be_conserved':True,
  'reference_total_physical_ROMs_layer_dies':sum(s['total_ROM4096_instances'] for s in inventory['per_stage_per_rank']),
  'reference_total_complete_pairs_layer_dies':sum(s['reservation_pairs'] for s in inventory['per_stage_per_rank']),
  'candidate_id':None,'minimum_partitions':None,
  'candidate_sizing_contract':{
   'per_die_constraint':'q_pairs*Aq + BF16_pairs*Ab + service + routes + clockPG + nonoverlapping repair reservations <= legal usable die area',
   'capacity_constraint':'Sum candidate complete-element gross storage and bank-specific payload capacities must preserve all reference tensors/scales/constants; packing efficiency cannot substitute for bank ownership.',
   'granularity_constraint':'Every largest indivisible operator/bank/ordered reduction owner must fit one assigned die; split only at a proven legal ownership boundary.',
   'count_lower_bound':'ceil(total conserved area / per-die field area after service/routes/clockPG) is only an area lower bound, not a legal minimum partition count.',
   'latency_contract':'Price added stage-hop traffic/CDC separately from any changed TP collectives, preserve exact reduction order and per-element MACs/byte.',
   'fixed_depth':4096,'depth_sweeps_allowed':False,'arithmetic_intensity_changes':False,
   'head_and_table_die_capacity_not_in_layer_ROM_sum':True},
  'source_sha256':inventory['source_sha256'],'physical_admission':False}
def validate_inventory(x):
 """Reject omitted classes, changed geometry, and false ownership/packing claims."""
 assert x['product']['rows']==4096 and x['product']['macros_per_pair']==4
 assert x['selected_primary_lever']['physical_macros_per_logical_slot']==2
 assert x['selected_primary_lever']['no_depth_sweep']
 assert not x['physical_admission']
 assert x['product']['layer_dies']==len(x['per_stage_per_rank'])==164
 for s in x['per_stage_per_rank']:
  assert s['q_pairs']+s['BF16_column_pairs']==s['reservation_pairs']
  assert s['BF16_column_pairs']==1024
  assert s['total_ROM4096_instances']==4*s['reservation_pairs']
  assert s['q_ROM4096_instances']==4*s['q_pairs']
  assert s['BF16_ROM4096_instances']==4*s['BF16_column_pairs']
 assert len(x['nonexpert_and_BF16_ownership']['layer_candidate_obligations'])==40
 for l in x['nonexpert_and_BF16_ownership']['layer_candidate_obligations']:
  ids=[i for o in l['routed_expert_candidate_owners'] for i in range(o['expert_ids'][0],o['expert_ids'][1]+1)]
  assert sorted(ids)==list(range(384))
 for c in x['composite_classes'].values():
  assert len(c['source_placement_template'])==4
  assert {p['orientation'] for p in c['source_placement_template']}=={'R0','MX','MY','R180'}
 assert x['busiest_die']['ROM_storage_bits']==x['busiest_die']['total_macros']*4096*274
 assert x['area_ledgers']['separate_analytical_capacity_ledger']['do_not_add_to_leaf_frame_ledger']
 assert x['macro_catalog']['ot_rom_4096x274_m8']['pin_uses']['CLOCK']==1
 return True
def build():
 PINS.clear()
 owners=js('results/arch/v41_stage_owner_product.json');cons=js('results/uarch/consolidation.json')['v41_rom'];wake=js('results/uarch/w10_baseline_wake/fullgoal_bound.json');pack=js('results/floorplan/v41_pack_refit_w18_e8p5.json');mm=js('results/floorplan/v41_die_macromap_expanded_woa.json');banks=js('results/floorplan/v41_stage17_bankmap.json');capacity=js('results/uarch/dsrom_4096_comparable_capacity_20261002/model.json');depths=js('results/uarch/v41_rom_depth_study.json');reticle=js('results/uarch/dsrom_l20_reticle_prerequisite_20261002/model.json')
 read('tools/uarch_model.py');read('rtl/v41rom/ot_v41_rom_elem_w10.sv');read('rtl/v41rom/ot_v41_rom_elem_q_w10.sv');read('rtl/v41rom/ot_v41_rom_elem_wake_w10.sv');read('rtl/v41rom/ot_v41_rom_elem_q_wake_w10.sv');read('rtl/v41rom/ot_v41_rom_elem_w10_rne_wake_prepare.sv');read('rtl/v41rom/ot_v41_rom_array.sv')
 qplace=placement(read('physical/abi3/w10_wake_q_place.tcl').decode());bfplace=placement(read('physical/abi3/w10_wake_column_place.tcl').decode());pdn=read('physical/abi3/w10_wake_pdn.tcl').decode();read('physical/abi3/w10_wake_pp_multicycle.sdc');pinaccess=js('results/uarch/w10_wake_pinaccess_contract_review/inputs.json');anchor=js('results/uarch/w10_baseline_wake/c8_area_anchor.json')
 masters=['ot_rom_4096x274_m8','ot_rom_1024x72_m8','ot_sram_1rw_2048x128_m4_r2c2','ot_sram_1r1w_1024x256_m2_r2c2','ot_hbm3e_phy_v41x_aw30_e8p5']
 catalog={}
 for name in masters:
  prefix='physical/asap7_memory_macros/'+name+'/'+name
  info=js(prefix+'.json');view=lef_view(read(prefix+'.lef').decode())
  timing=info.get('timing',{})
  libs={}
  for corner in ['ss','ff','tt']:
   try:read(prefix+'_'+corner+'.lib');libs[corner]=prefix+'_'+corner+'.lib'
   except subprocess.CalledProcessError:libs[corner]=None
  catalog[name]={'LEF':prefix+'.lef','liberty':libs,'spec':info.get('spec'),'capacity_bits':info.get('capacity_bits'),'area_breakdown':info.get('area'),'timing_calibrated_not_signoff':{k:{a:v[a] for a in ['clk_to_q_ps','min_period_ps','clk_cap_ff','setup_ps','hold_ps'] if a in v} for k,v in timing.items()},**view}
 assert owners['stage_count']==41 and max(owners['pairs_per_die_by_stage'])==wake['full_size']['maximum_pairs_per_die']==4773
 bf=wake['full_size']['bf16_column_pairs_per_die'];assert bf==1024
 stage_inventory=[]
 for s,n in enumerate(owners['pairs_per_die_by_stage']):
  for rank in range(4):stage_inventory.append({'stage':s,'rank':rank,'reservation_pairs':n,'q_pairs':n-bf,'BF16_column_pairs':bf,'q_ROM4096_instances':4*(n-bf),'BF16_ROM4096_instances':4*bf,'total_ROM4096_instances':4*n,'owner_status':owners['status'],'tensor_to_physical_bank_bound':False})
 qoutline=cons['pitches']['w10b_q']['q_um'];bfoutline=cons['pitches']['w10b_q']['bf16_outline_um'];q=4773-bf;macro=catalog[masters[0]]['area_breakdown'];leaf=4*4773;bits=leaf*4096*274
 frame=(q*math.prod(qoutline)+bf*math.prod(bfoutline))/1e6
 data=leaf*macro['data_array_area_um2']/1e6;leafarea=leaf*macro['macro_area_um2']/1e6
 row41=next(r for r in capacity['capacity_rows'] if r['stages']==41)
 groups=collections.Counter((v[1],v[5]) for v in pack['instances'])
 retained=[{'master':m,'owner_group':g,'quantity':n,'binding_scope':'Historical8192pack only; current4096co-resident replication not source-closed'} for (m,g),n in groups.items() if not m.startswith('ot_rom_')]
 histtotals=collections.Counter()
 for d in mm['layer_dies']:
  for g,v in d['macros_by_group'].items():histtotals[g]+=sum(v.values())
 obligations=[{'layer':l['layer'],'dense_owner_stage':l['dense_owner_stage'],'routed_expert_candidate_owners':l['routed_expert_candidate_owners'],'nonexpert_tensor_bank_owner_bound':False} for l in owners['layer_owners']]
 inventory={'schema':'opentallas.DSROM4096.reticle_inventory.v1','source_commit':PIN,'scope':'Current allocation and macro-interface inputs for physical packing; no executable whole-field bank ownership or legal packing claim','status':'PACKING_RESERVATION_INPUTS_READY_COMPLETE_OWNERSHIP_AND_HARD_ABSTRACTS_PENDING','product':{'stages':41,'ranks_per_stage':4,'layer_dies':164,'head_dies':8,'table_dies':36,'total_dies':208,'BF16_mode':'columns','PP':1,'NB':2,'rows':4096,'macros_per_pair':4,'NP_resized':False,'selected_product_changed':False},'per_stage_per_rank':stage_inventory,'busiest_die':{'stages_tied':[i for i,n in enumerate(owners['pairs_per_die_by_stage']) if n==4773],'pairs':4773,'q_pairs':q,'BF16_column_pairs':bf,'q_macros':4*q,'BF16_macros':4*bf,'total_macros':leaf,'ROM_storage_bits':bits,'logical_payload_bits_capacity_basis':row41['required_payload_bits'],'payload_to_bank_exactness':False},'macro_catalog':catalog,'composite_classes':{'q_pair':{'quantity_busiest':q,'outline_um':qoutline,'source_placement_template':qplace,'source_BF16':0,'boundary_bits_cycle':wake['elements']['q']['boundary_bits_per_cycle'],'hard_LEF_ETM_available_in_pinned_physical_catalog':False},'BF16_column_pair':{'quantity_busiest':bf,'outline_um':bfoutline,'source_placement_template':bfplace,'source_BF16':1,'boundary_bits_cycle':wake['elements']['column']['boundary_bits_per_cycle'],'hard_LEF_ETM_available_in_pinned_physical_catalog':False}},'placement_contract':{'template_coordinates':'requested Tcl locations; source snaps to joint site/M4 grid, not literal replicated legal origins','template_orientations':['R0','MX','MY','R180'],'LEF_rotational_symmetry_does_not_prove_parent_pin_access':True,'PDN_macro_halo_um':[2,2,2,2],'PDN_halo_is_not_proved_placement_exclusion_halo':True,'historical_pin_halo_um':pack['geometry']['pin_halo_um'],'current_parent_halo_bound':False,'pin_access_source_tracks':pinaccess['geometry']['tracks'],'pin_access_retained_center_warnings':pinaccess['geometry'].get('center_warning_counts'),'row_grid_frame_snapping_required':True,'fullfield_origins_assigned':False},'clock_PG':{'stream_period_ps':833,'serial_chain_hz':900000000,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,'ROM_PP_capture_setup_cycles':2,'ROM_PP_capture_hold_cycles':1,'local_ICGs_per_element':wake['full_size']['local_icgs_per_element'],'macro_clk_pin':'clk','macro_power_pins':['VDD','VSS'],'leaf_PG_layer':'M4','parent_grid_export_layer':'M7','PDN_source':'physical/abi3/w10_wake_pdn.tcl','domain_CDC_and_reset_owner_fullfield_bound':False,'contextual_SSFF_or_IR_EM_claim':False},'nonexpert_and_BF16_ownership':{'layer_candidate_obligations':obligations,'historical_group_totals':dict(histtotals),'groups_not_to_drop':['ROM_MAC.dense_QE','ROM_MAC.ME','VM.CONSTANT_HE','ENGRAM.spill'],'current_BF16_allocation':1024,'current_BF16_tensor_to_slot_map':None,'coarse_dense_owner_does_not_assign_individual_BF16_code_scale_norm_router_banks':True,'retained_stage17_unbound_dense_tensors':banks['unbound_dense_tensors'],'legacy8192_bankmap_not_current4096':True,'current_selected_engram_spill_zero':True,'head_and_Engram_dies_separate_from_layer_field':True},'co_resident_obligations':{'historical_pack_instances_by_group':retained,'current_SU_VM_hub_mm2':cons['product']['head_fit']['hub_block']['block_mm2'],'full_return_bits_obligation':capacity['full_return_required_bits'],'return_provider_hardmacro_count':None,'return_provider_ports_and_placement_bound':False,'return_FF_no_credit_reservation_mm2':row41['return_FF_no_credit_mm2'],'BF16_c8_anchor':anchor,'HBM_PHY_serdes_UCIE_clocks_reset_PG_do_not_drop':True,'assumed_SERDES_UCIE_abstracts_not_hardened':True},'area_ledgers':{'busiest_current_leaf_and_frame':{'data_bitcell_array_mm2':data,'leaf_macro_total_mm2':leafarea,'leaf_peripheral_taps_control_outline_mm2':leafarea-data,'composite_frame_total_mm2':frame,'compute_local_control_wires_and_margin_unresolved_mm2':frame-leafarea,'not_measured_stdcell_compute_area':True},'separate_analytical_capacity_ledger':{'do_not_add_to_leaf_frame_ledger':True,'field_need_mm2':row41['integer_mixed_field_need_mm2'],'return_no_credit_mm2':row41['return_FF_no_credit_mm2'],'WAKE_increment_mm2':row41['WAKE_increment_mm2'],'RNE_increment_mm2':row41['RNE_construction_increment_mm2'],'full_need_mm2':row41['full_conservative_need_mm2'],'usable_field_mm2':row41['usable_field_mm2'],'field_only_excess_mm2':row41['integer_mixed_field_need_mm2']-row41['usable_field_mm2'],'full_excess_mm2':row41['full_conservative_need_mm2']-row41['usable_field_mm2']}},'selected_primary_lever':{'fixed_depth':4096,'physical_macros_per_logical_slot':2,'physical_macros_per_complete_pair':4,'action':'Fewer complete weight+adjacent compute elements per die, more dies; one shared candidate only.','no_depth_sweep':True,'per_die_capacity_and_MACs_decrease':True,'per_element_arithmetic_intensity_unchanged':True,'golden_reduction_order_unchanged':True,'complete_model_capacity_required':True,'candidate_partition_count':None,'candidate_owner':'Shared model/Arch physical/Maxwell/Kepler designation pending','minimum_partition_count':None,'minimum_binding_gap':'Service/routes/clockPG legal footprint plus actual wholeoperator/BF16/tensor bank ownership granularity not closed. Coarse4773pair target is not a certified exactminimum.','current_BF16_1024_is_reservation_not_proved_unpartitionable_lower_bound':True},'retained_negatives':{'old8192_pack_status':pack['status'],'old8192_pack_not_current4096':True,'reticle_owner_outline':reticle['frozen_owner_proposal'],'user_reported_2550_overlaps':{'count':2550,'exact_receipt_not_located_in_pinned_main':True,'not_reinterpreted_as_zero':True},'no_inventory_admission':True},'remaining_gate':['Bind every current4096tensor/scale/constant/BF16 bank to integer stage/rank/slot and real source hierarchy; coarse41-stage owner alone is insufficient.','Obtain source-matched q/BF16 element hard LEF/OBS/clock/PG/ETMs and actual frame/halo pin access; leafLEF and modelrectangles are not wholeelement abstracts.','Map full138469120returnbits and remaining SRAM/PHY/link/service units to finite provider ports and explicit quantities without doublecount.','Arch: use reservation inventory for constrained packing; preserve8192reticle/2550overlap negatives and reject omitted or over-capacity classes.','Price added stage hops separately from any TP/collective change in one shared full-token single-user calendar. No independent count/depth sweeps or RTL/P&R until common candidate sized.'],'source_sha256':dict(PINS),'no_RTL_PnR':True,'no_checkpoint_payload_reads':True,'physical_admission':False}
 validate_inventory(inventory)
 inventory['element_envelope']=envelope(inventory,wake)
 return inventory
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
 x=build();(out/'inventory.json').write_text(json.dumps(x,indent=2)+'\n')
 (out/'macro_classes.json').write_text(json.dumps({'source_commit':PIN,'classes':x['macro_catalog'],'composite_classes':x['composite_classes'],'source_sha256':x['source_sha256']},indent=2)+'\n')
 (out/'per_element_envelope.json').write_text(json.dumps(x['element_envelope'],indent=2)+'\n')
 print(json.dumps({'max_pairs':x['busiest_die']['pairs'],'ROM4096macros':x['busiest_die']['total_macros'],'q':x['busiest_die']['q_pairs'],'BF16':1024,'physical_admission':False}))
