#!/usr/bin/env python3
"""Source r3 mirror in existing charged PAR2 padding, not extra ROMs.
Preserves additive-replica evidence. No source generation, payload, RTL or P&R.
"""
import gzip,hashlib,importlib.util,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_PAR2_padding_parity_binding_20261002'
PRIOR=ROOT/'results/uarch/dsrom_PAR2_shard_physical_binding_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(name):
 p=OUT/'inputs'/name;b=p.read_bytes()
 return [json.loads(x) for x in gzip.decompress(b).splitlines()] if name.endswith('.jsonl.gz') else json.loads(b)
def module(name,file):
 s=importlib.util.spec_from_file_location(name,file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def local_address(plan,bit):
 if not 0<=bit<plan['bits']:raise ValueError('source mirror bit outside allocation')
 idx,within=divmod(bit,4194304);word,data_bit=divmod(within,256);mb,a=divmod(word,8192)
 return plan['mirror_pairs'][idx],mb,a%2,a//2,data_bit

def build():
 receipt=json.loads((OUT/'input_receipt.json').read_text())
 for name,pin in receipt['inputs'].items():assert sha(OUT/'inputs'/name)==pin['sha256'],name
 parent_tool=module('physical',ROOT/'tools/dsrom_PAR2_shard_physical_binding.py');parity=module('parity',ROOT/'tools/dsrom_PAR2_local_parity_model.py');helpers=module('shapes',PRIOR/'inputs/parent_shapes_tool.py')
 parent,macros,obs,templates,field,escapes=parent_tool.build(1)
 prior=json.loads((PRIOR/'local_parity_model.json').read_text());plans=load('mirror.jsonl.gz');contract=load('source_contract.json');readback=load('provider_readback.json')['compiled_field']
 assert contract['candidate']==parent['candidate'] and len(plans)==58
 padding=set(readback['padding_site_IDs']);active=set(readback['weight_active_site_IDs']);bf=set(readback['BF_DUAL_site_IDs'])
 assert padding.isdisjoint(active) and padding|active==set(range(4096))
 available={p for p in padding if p>=2048 and p not in bf};assert len(available)==384
 for plan in plans:
  assert len(set(plan['mirror_pairs']))==len(set(plan['original_pairs']))==103
  assert set(plan['mirror_pairs'])<=available
  assert set(plan['original_pairs'])<=active and all(p<2048 for p in plan['original_pairs'])
  assert plan['extra_weight_macro_instances']==0 and plan['remaining_shard1_padding_pairs']==281
  assert plan['useful_data_bits_per_word']==256 and plan['sidecar_SECDED_bits_per_word']==10
 assert len({tuple(p['mirror_pairs']) for p in plans})==1
 pair_map={r['source_pair']:r for r in field};macro_map={(r.get('source_pair'),r.get('slot'),r.get('PP')):r for r in macros if r['template']=='ROM'}
 roles=[];translated=[];pairs=plans[0]['mirror_pairs']
 for index,pair in enumerate(pairs):
  assert pair_map[pair]['source_class']=='q_pair'
  for mb in range(2):
   for pp in range(2):
    original=macro_map[(pair,mb,pp)];role=dict(original,role='LOCAL_RAW_PROTECTED_PARITY',mirror_pair_index=index,source_original_pair_all58=[p['original_pairs'][index] for p in plans],new_macro_instance=False,arithmetic_compute_role=False,protected_bits=[256,10],candidate_source_hierarchy_exists=False)
    roles.append(role)
    for shape in templates['ROM']['OBS']:translated.append(dict(instance=role['name'],layer=shape['layer'],bbox_DBU=helpers.translate(shape['bbox_DBU'],*role['origin_DBU'],templates['ROM']['size_DBU'],role['orientation'])))
 assert len({r['name'] for r in roles})==412
 assert all(r['bbox_DBU']==macro_map[(r['source_pair'],r['slot'],r['PP'])]['bbox_DBU'] for r in roles)
 # Exact existing placement and collar charges are retained; no body/halo debit.
 identity_bits=10+12+10+32+11+13+4+1
 components={'address_bank_arbitration':412*(128*identity_bits+128*12),'gather_reply_mux':128*(103*16+544),'sidecar_leaf_SECDED256_check10':412*256*10,'main_pair_SECDED272_check10':2*128*272*10}
 gate_bits=sum(components.values());coefficient=prior['area']['retained_FF50_mm2_per_bit']
 logic=(prior['area']['state_bits']+gate_bits)*coefficient
 named_logic_costs={name:bits*coefficient for name,bits in components.items()};named_logic_costs['capture_request_identity_state']=prior['area']['state_bits']*coefficient
 height=parent_tool.snap(logic*1e12/33000000);y=parent_tool.snap(parent['geometry']['last_field_cfg_return_repair_end_DBU']+2*parent['geometry']['halo_DBU']);logic_rect=[0,y,33000000,y+height];assert logic_rect[3]<16000000
 helpers.disjoint([(r['name'],r['bbox_DBU']) for r in macros]+[('PARITY_ADDED_LOGIC_AREA_RESERVE',logic_rect)])
 allowance=33*height/1e6;screen=parent['area']['revised_conservative_screen_mm2']+allowance
 # Actual source-address witness translated to existing macro pins, not routed.
 witness=prior['finite_service']['first_address_batch_witness'];p=plans[0];incidence=[]
 clock_pin=next(r for r in templates['ROM']['pins'] if r['pin']=='clk')
 for consumer,bit in witness['requests_pair_linearbit']:
  pair,mb,pp,row,data_bit=local_address(p,bit);src=macro_map[(pair,mb,pp)];dest=pair_map[consumer]
  # rd_out[data_bit] exact M4 shape, consumer frame boundary only: its
  # actual new terminal pin does not yet exist. Distance is a geometry proxy.
  shape=next(r for r in templates['ROM']['pins'] if r['pin']==f'rd_out[{data_bit}]');r=helpers.translate(shape['bbox_DBU'],*src['origin_DBU'],templates['ROM']['size_DBU'],src['orientation']);srcpoint=[(r[0]+r[2])//2,(r[1]+r[3])//2];d=dest['bbox_DBU'];destpoint=[(d[0]+d[2])//2,(d[1]+d[3])//2]
  incidence.append(dict(consumer_global_pair=consumer,linear_bit=bit,mirror_instance=src['name'],physical_row=row,data_bit=data_bit,exact_source_pin_DBU=r,consumer_frame_center_DBU=destpoint,Manhattan_pin_to_frame_center_um=sum(abs(a-b) for a,b in zip(srcpoint,destpoint))/1000,consumer_terminal_pin_bound=False))
 rounds,words=parity.service_batch({'pairs':p['mirror_pairs'],'bits':p['bits']},witness['requests_pair_linearbit'])
 assert rounds==64 and words==64
 # Track demand of independent16-bit parity replies crossing representative
 # vertical cuts. This is a source-incidence screen, not a routed capacity.
 cut_x=sorted({v['exact_source_pin_DBU'][0] for v in incidence}|{v['consumer_frame_center_DBU'][0] for v in incidence})
 cuts=[]
 for left,right in zip(cut_x,cut_x[1:]):
  x=(left+right)//2;cross=[v for v in incidence if min(v['exact_source_pin_DBU'][0],v['consumer_frame_center_DBU'][0])<x<max(v['exact_source_pin_DBU'][0],v['consumer_frame_center_DBU'][0])]
  cuts.append(dict(x_DBU=x,independent_pair_reply_nets=len(cross),reply_bits_if_fully_parallel=16*len(cross)))
 peak=max(cuts,key=lambda v:v['reply_bits_if_fully_parallel'])
 result=dict(schema='opentallas.dsrom.PAR2.padding-parity-binding.v1',candidate=parent['candidate'],variant='R3_LOCAL_RAW_PARITY_IN_ALREADY_CHARGED_Q_ONLY_PADDING',source_commit='124e870c5be4f9958e8aa8bebe6a14b6e386d886',source_receipt_sha256=sha(OUT/'input_receipt.json'),prerequisite_commit=receipt['prerequisite_commit'],generator_sha256=sha(Path(__file__)),
  applicability=prior['applicability'],
  ownership=dict(all58_original103_shard0_pairs_preserved=True,mirror_pairs_global=pairs,mirror_pairs_local=[g-2048 for g in pairs],all58_identical_mirror_site_map=True,formerly_padding_Q_ONLY_pairs=103,original_shard1_padding=384,remaining_shard1_padding=281,NP=2048,NBF=362,serial_stage_owners=58,logical_TP=4,added_serial_hops=0,added_collective_levels=0,source_weight_active_IDs_unchanged=True,no_aggregate_weight_compute_or_order_loss=True),
  storage=dict(already_counted_macros_repurposed=412,incremental_macro_instances=0,incremental_macro_body_mm2=0,incremental_macro_halo_mm2=0,role_body_mm2=prior['geometry']['raw_body_mm2'],role_body_is_already_in_field_catalog=True,protected_payload_data_bits=256,protected_check_bits=10,physical_word_bits=274,remaining8bits_not_relabelled_as_payload=True,capacity_bits=412*4096*256,immutable_copy_provenance_ROM_init_qualified=False),
  area=dict(original_per_shard_screen_mm2=parent['area']['original_per_shard_screen_mm2'],prior_macro_clearance_debits_retained_mm2=parent['area']['total_added_debit_mm2'],before_parity_added_logic_mm2=parent['area']['revised_conservative_screen_mm2'],state_bits=prior['area']['state_bits'],gate_bit_equivalents=gate_bits,named_logic_allowance_mm2=named_logic_costs,sidecar_leaf_decoder_replicas=412,main_codeword_decoder_replicas=256,gather_reply_lanes=128,address_arbiters=412,FF50_proxy_mm2_per_bit=prior['area']['retained_FF50_mm2_per_bit'],incremental_logic_allowance_mm2=logic,logic_reserve_rounding_mm2=allowance-logic,total_incremental_allowance_mm2=allowance,with_existing_clearances_screen_mm2=screen,remaining_for_unpriced_physical_endpoints_exclusions_mm2=858-screen,original163_margin_after_logic_only_mm2=parent['area']['original_extra_budget_mm2']-allowance,prior_separate_storage_body_halo_debit_removed_mm2=prior['geometry']['halo_grid_mm2'],difference_from_prior_extra_replica_screen_mm2=prior['area']['screen_with_variant_mm2']-screen,logic_is_prospective_conservative_construction_not_measured_area=True,inherited418_residual47_and_complete_q_padding_frame_charges_retained=True,no_embedding_or_logic_credit=True,fit_certified=False),
  geometry=dict(placement_artifact='reused_macro_roles.json.gz',OBS_artifact='reused_macro_OBS.json.gz',pin_templates_prerequisite='macro_templates.json',all412_macro_bodies_and_OBS_equal_existing_shard1=True,macro_pin_shape_count=412*len(templates['ROM']['pins']),additional_macro_clock_pin_count=0,additional_macro_clock_cap_fF=0,additional_logic_clock_cap_and_toggling_PG_unbound=True,logic_area_reserve_DBU=logic_rect,reserve_is_not_centralized_decoder_layout=True,decoder_should_be_leaf_local_before16bit_reply_but_new_local_pin_collar_missing=True,existing_full_macro_halo_debit_retained=True,actual_PG_via_CTS_exclusions_qualified=False),
  source_service=dict(protected256_plus10_word_must_decode_before_parity_use=True,paired_mainword272plus10_must_terminal_before_arithmetic=True,aligned16bit_gather_no_word_straddle=True,single_read_port_per_leaf=True,retained_first_address_bank_conflict_read_rounds=rounds,conditional_max_read_rounds_per128seat_batch=128,request_seats=128,capture_seats=412,next_batch_only_after_all_ECC_terminal_and_ordered_retire=True,actual_simultaneous_engine_issue_proven=False,current_source_accept_ready_sidecar_and_decoder_absent=True,macro_SS_clk_to_q_ps=parent['PG_via_clock']['source_macro_timing']['ROM']['SS_clk_to_q_ps'],stream_cycle_margin_after60ps_uncertainty_before_setup_route_ps=parent['PG_via_clock']['source_macro_timing']['ROM']['one_stream_cycle_after60ps_uncertainty_minus_macro_cq_ps'],common_controller_plus2cycles_still_priced=True,no_loss_original_deadline_proof=False,source_read_calendar_qualified=contract['actual_provider_and_remote_event_calendar_qualified'],latency_contract='128 read rounds is a conditional finite batch service upper bound only. Capture/sidecar SECDED/gather/mainword ECC/visibleACK latency and original dependent deadline required; no zero transport implies zero compute latency.'),
  routing=dict(witness_incidence_artifact='parity_pin_to_consumer_incidence.json',pin_to_consumer_frame_center_max_Manhattan_um=max(x['Manhattan_pin_to_frame_center_um'] for x in incidence),pin_to_consumer_frame_center_is_not_routed_wirelength=True,representative_vertical_reply_cut_peak=peak,cut_artifact='parity_reply_cut_screen.json',full_peak_parity_reply_bits_per_cycle=2048,private_leaf_command_bits_per_cycle=412*13,raw_leaf_return_bits_per_cycle=412*274,raw_return_is_leaf_local_requirement_not_free_shared_bus=True,source_command_packet_and_generation_routes_need_pricing=True,clock_PG_via_pin_escape_and_admissible_cut_capacity_bound=False,universal50pct_reserve_used=False,collector_band_capacity_credit_taken=0),
  preserved_prior_variant=dict(path=str(PRIOR.relative_to(ROOT)/'local_parity_model.json'),sha256=sha(PRIOR/'local_parity_model.json'),reason='Prior separate extra-storage proposal preserved. r3 chooses already charged Q_ONLY padding instead; do not add that body/halo charge again.'),
  next_source_bound_prerequisites=['Freeze actual immutable protected256+10 copy/provider word initialization and matching mainword/parity identities.','Source acceptance/backpressure and finite epoch/fault/drain fence; per-event address/coalescer/ECC terminal and original consumer deadlines in the common calendar.','Named local decoder/capture/address router logic, actual pin collars/OBS/PG/vias/CTS and representative hardest incidence cut capacity within positive allowance; source SS/FF context.'],physical_GO=False,new_RTL_compile_PR_jobs=0,verdict='EXISTING_MACRO_REUSE_AND_INCREMENTAL_LEDGER_BOUND_FINITE_SERVICE_AND_PHYSICAL_GATES_OPEN')
 return result,roles,translated,incidence,cuts

def main():
 result,roles,obs,incidence,cuts=build()
 for name,obj in [('model.json',result),('reused_macro_roles.json.gz',roles),('reused_macro_OBS.json.gz',obs),('parity_pin_to_consumer_incidence.json',incidence),('parity_reply_cut_screen.json',cuts)]:
  data=(json.dumps(obj,indent=2,sort_keys=True)+'\n').encode();data=gzip.compress(data,mtime=0) if name.endswith('.gz') else data;p=OUT/name
  if p.exists() and p.read_bytes()!=data:raise ValueError('immutable verdict changed '+name)
  p.write_bytes(data)
 print(json.dumps(result['area'],sort_keys=True))
if __name__=='__main__':main()
