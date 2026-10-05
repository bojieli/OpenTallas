#!/usr/bin/env python3
"""W5 owned gate and W10 addressed fabric model; no endpoint RTL emitted."""
import argparse,hashlib,json,math,collections
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]/'results/uarch/h4_hbm_baseline_bridge_20261003/w5_w10_r4'
PIN='0c4459b4e83a9f07ad3ae3c8f38cee2f83cc81be9bf8e1cba7f1fae95c38ac7f'
def require(x,msg):
 if not x:raise ValueError(msg)
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def inputs():
 raw=(BASE/'input_manifest.json').read_bytes();require(hashlib.sha256(raw).hexdigest()==PIN,'hard manifest pin');out={}
 for r in json.loads(raw)['inputs']:
  p=(BASE/r['archive']).resolve();require(p.is_relative_to((BASE/'inputs').resolve()),'archive origin');v=p.read_bytes();require(len(v)==r['bytes'] and hashlib.sha256(v).hexdigest()==r['sha256'],'exact input');out[p.name]=v
 return out
def protected(n):return math.ceil(n/64)*72
def physical(byte):
 """Exact retained r17 address translation; never alter payload low bits."""
 require(type(byte)is int and 0<=byte<4*20250000000,'global HBM address aperture')
 local=(byte//512)*128+byte%128;sector=local//32
 require(sector<2**31,'retained local sector aperture')
 stack=(byte//128)%4;pc=((sector>>2)^(sector>>7)^(sector>>12))&31
 return dict(stack=stack,local_sector=sector,physical_PC=stack*32+pc,byte_in_sector=local%32)
class BankedSwitch:
 """Candidate conventional crossbar arbitration, one accepted beat/output.

 Bounded directed model, not source fairness qualification. Each input holds
 one destination until acceptance; accepted output beats retain parent owner.
 """
 def __init__(self,ni=36,no=32):
  require(type(ni)is int and 1<=ni<=36 and type(no)is int and 1<=no<=32,'finite switch ports');self.ni=ni;self.no=no;self.head=[0]*no
 def step(self,requests,ready):
  require(len(ready)==self.no and all(type(r)is bool for r in ready),'actual output ready')
  for i,r in requests.items():require(type(i)is int and 0<=i<self.ni and set(r)=={'destination','payload','owner'} and type(r['destination'])is int and 0<=r['destination']<self.no and r['owner'],'source packet/destination/owner')
  accepted={}
  for output in range(self.no):
   if not ready[output]:continue
   winner=next((i for k in range(self.ni) for i in [(self.head[output]+k)%self.ni] if i in requests and requests[i]['destination']==output),None)
   if winner is not None:accepted[winner]=requests[winner];self.head[output]=(winner+1)%self.ni
  return accepted
class W5Gate:
 """Finite candidate retained endpoint gate. No timing or installed credit.

 Exact original client tag and physical-PC namespace retained. The proposed
 phase machine has no acceptance-timer completion, generation wrap or live
 reset credit. W2/W4/W6 must provide actual matched source receipts.
 """
 def __init__(self,SM):
  require(type(SM)is int and 0<=SM<32,'requesting endpoint SM');self.SM=SM;self.owner=None;self.epoch=1;self.closed=set()
 def acquire(self,owner,home):
  require(self.owner is None and len(self.closed)<16 and set(owner)=={'tag32','physical_PC','client','epoch','home_id','requester_SM','target_slot','endpoint_kind'},'finite owner/quarantine and complete source namespace')
  require(type(owner['tag32'])is int and 0<=owner['tag32']<2**32 and type(owner['physical_PC'])is int and 0<=owner['physical_PC']<128 and type(owner['client'])is int and 0<=owner['client']<7,'actual tagged PC/client')
  require(owner['requester_SM']==self.SM and owner['epoch']==self.epoch and type(owner['home_id'])is int and owner['home_id']>0,'requester epoch/home identity')
  require(set(home)=={'kind','home_SM','published','read_lease','immutable_home_id'},'home-kind source receipt')
  require(home['immutable_home_id']==owner['home_id'] and home['kind'] in ('RF','spill','HBM_NATIVE_STATE'),'immutable home identity')
  require(owner['endpoint_kind'] in ('RF','shared64') and type(owner['target_slot'])is int and 0<=owner['target_slot']<(512 if owner['endpoint_kind']=='RF' else 1024),'actual RF9/shared10 endpoint address')
  if home['kind']=='RF':require(home['home_SM']==self.SM,'RF physical source home')
  else:require(home['published']is True and type(home['read_lease'])is int and home['read_lease']>0,'persistent publication and actual reader lease, no homeSM invention')
  key=(owner['epoch'],owner['physical_PC'],owner['client'],owner['tag32']);require(key not in self.closed,'same epoch tag reuse requires independent F0 drain proof')
  self.owner=dict(identity=dict(owner),phase='W2',home=dict(home))
 def event(self,owner,event):
  require(self.owner is not None and owner==self.owner['identity'],'exact retained owner match; unmatched completion never frees credit')
  local_ACK='W4_common_RF_ACK' if owner['endpoint_kind']=='RF' else 'C0_shared64_both_bank_ACK'
  phases={'W2_held_done':('W2','W4'),local_ACK:('W4','W6_VISIBLE'),'W6_visible':('W6_VISIBLE','W6_CONSUMER'),'W6_consumer':('W6_CONSUMER','W6_REVERSE'),'W6_reverse':('W6_REVERSE',None)}
  require(event in phases and self.owner['phase']==phases[event][0],'held backend/commonACK/visible/consumer/reverse order')
  following=phases[event][1]
  if following is None:
   self.closed.add((owner['epoch'],owner['physical_PC'],owner['client'],owner['tag32']));self.owner=None
  else:self.owner['phase']=following
 def reset(self,receipt):
  fields={'W2_live','W4_ACK_held','W6_consumer_live','W6_reverse_live','CDC_forward_live','CDC_return_live','both_domain_reset_accepted'}
  require(self.owner is None and set(receipt)==fields,'no live reset or unilateral source flush credit')
  require(all(type(receipt[k])is int and receipt[k]==0 for k in fields-{'both_domain_reset_accepted'}) and receipt['both_domain_reset_accepted']is True,'actual complete drain and paired reset receipt required')
  require(self.epoch<2**32-1,'no epoch wrap');self.epoch+=1;self.closed.clear()
def CDC_pair(receipt,authority):
 require(set(receipt)=={'sender_domain','receiver_domain','sender_edge','receiver_edge','token'} and set(authority)=={'sender_domain','receiver_domain','token'},'paired source CDC ABI')
 require(all(receipt[k]==authority[k] for k in authority),'actual source sender/receiver domains and owner token, not arbitrary nonempty strings')
 require(all(type(authority[k])is str and authority[k] for k in authority),'nonempty frozen port/domain authority required')
 require(all(type(receipt[k])is int and receipt[k]>=0 for k in ('sender_edge','receiver_edge')),'actual domain edge ordinals')
 return dict(source_pair_matched=True,physical_wait_upper=None,hardware_admitted=False)
def outputs():
 src=inputs();f0=json.loads(src['F0.json']);old=json.loads(src['baseline.json']);system=src['system.sv'].decode();provider=src['provider.sv'].decode()
 require('NC=6' in system and 'CTAGW=32' in system and 'NPC!=128' in system,'actual outer instantiated PC geometry')
 require('return_arb==6' in provider and 'return_arb<6' in provider and 'One real command bus/stack' in provider,'actual serialized source return mapper and command bus')
 require('assign commit_ready=0' not in provider,'W1 corrected successor body')
 require('byte // 512' in src['physical.py'].decode() and 'sector >> 12' in src['physical.py'].decode(),'exact retained translation source')
 request_fields=dict(data=256,original_client_tag32=32,client_class=3,sector=34,length=6,write=1,physical_PC_after_aggregation=7)
 return_fields=dict(data=256,original_client_tag32=32,client_class=3,beat=5,physical_PC_after_aggregation=7)
 req=sum(request_fields.values());ret=sum(return_fields.values());rq=protected(req);rp=protected(ret);producer_ports=36*4
 pipeline_bits=38*producer_ports*(2*(rq+rp)+2*protected(7))
 pipeline_gate=2*pipeline_bits+2*producer_ports*38*768+producer_ports*4*math.ceil((req+ret)/64)*768
 pipeline_area=(pipeline_bits*.2916+pipeline_gate*.3)/.5/1e6
 crossbar_mux=4*(32*35*rq+36*31*rp)*2
 fanout_buffers=4*(36*math.ceil(32/24)*rq+32*math.ceil(36/24)*rp)
 crossbar_regs=4*(32+36)*2*(rq+rp+protected(7))
 crossbar_area=(crossbar_regs*.2916+(crossbar_mux+fanout_buffers)*.3)/.5/1e6
 fifo_bits=producer_ports*2*(16*(rq+rp)+2*protected(50))
 old_fifo=old['actual_consumer_delta']['FIFO_candidate'];oldfifo_bits=sum(row['protected_data_bits']+row['protected_control_bits'] for row in old_fifo.values() if row['payload_bits_per_entry']>100)
 oldpipe=f0['pipeline']['total_pipeline_protected_bits'];oldpipearea=f0['pipeline']['pipeline_FF_control_footprint_mm2_ASSUMED']
 rowfields=old['actual_consumer_delta']['fields_remain_private_context'];row_bits=protected(sum(rowfields.values()))
 metadata_delta=128*16*row_bits;metadata_mux_delta=128*3*16*row_bits
 metadata_area=(metadata_delta*.2916+metadata_mux_delta*.3)/.5/1e6
 fifo_delta=fifo_bits-oldfifo_bits;fifo_area_upper=(max(0,fifo_delta)*.2916+2*fifo_bits*.3)/.5/1e6
 quarantine_bits=32*16*protected(32+7+3+4+1)
 quarantine_gates=32*16*(32+7+3)*2+32*768
 quarantine_area=(quarantine_bits*.2916+quarantine_gates*.3)/.5/1e6
 bits=f0['clock']['complete_control_FF_bits_screen']-oldpipe+pipeline_bits+crossbar_regs+fifo_delta+metadata_delta+quarantine_bits
 clock=f0['clock'];levels=[];n=math.ceil(bits/32)
 while n>1:n=math.ceil(n/24);levels.append(n)
 buf=32*sum(levels)+3;clock_area=buf*clock['buffer_TT_geometric_area_um2']*2/1e6
 # Replace old pipeline area exactly at its screen granularity. Existing FIFO
 # logic overlap is retained as a conservative upper, never duplicate events.
 area=f0['F0_allocations']['Qwen']['candidate_complete_bridge_screen_upper_mm2']-oldpipearea+pipeline_area+crossbar_area+metadata_area+fifo_area_upper+clock_area+quarantine_area
 examples=[dict(byte=b,retained=physical(b),old_outer_low7_PC=(b//32)&127) for b in (0,128,512,16384,33554432)]
 allocation={}
 for name,a in f0['F0_allocations'].items():
  allocation[name]=dict(SMs=32,source_reserved_die_mm2=a['existing_reserved_die_mm2'],source_residual_strip_mm2=a['current_total_service_strip_residual_mm2'],
   candidate_complete_service_bridge_screen_mm2=area,new_reservation_demand_mm2=max(0,area-a['current_total_service_strip_residual_mm2']),
   per_SM_forward_reverse_cut_bits=4*(rq+rp)+16,source_min_local_margin_tracks=a['existing_min_local_margin_tracks'],
   L2_PC_bundle_demand_tracks=32*(rq+rp+4),new_L2_bundle_to_cut_screen_margins=[cap-32*(rq+rp+4) for cap in a['known_existing_L2_cut_capacities']],
   source_L2_cut_capacities=a['known_existing_L2_cut_capacities'],exact_new_pipeline_and_switch_net_to_cut_assignment=None,
   parent_ring_guard_um=2.088,selected_new_slots=None,clock_PG_OBS_via_reservation=None,admitted=False)
 model=dict(schema='HBM_W5_W10_COMPOSED_ADDRESSED_SERVICE_MODEL_R4',status='FAIL_ACTUAL_ALLOCATION_F0_PORT_FREEZE_FINITE_RECEIPTS',
  source_sha256={k:hashlib.sha256(v).hexdigest() for k,v in src.items()},owners={'F0':'Russell','W2':'Nash','W4':'Euclid','W6':'Goodall','W5':'Popper','W10':'Popper','calendar':'Dewey'},
  source_corrections=dict(actual_outer_PC_clients=6,actual_original_client_tag_bits=32,actual_physical_tag_bits=35,candidate_directory_client_count=7,
   old_F0_leaf_default5_is_not_instantiated_geometry=True,source_II40_route_Bpc_FAST=128*32/40,
   source_per_stack_return_mapper_spacing_CORE_edges=7,source_four_stack_return_ceiling_Bpc_CORE=4*32/7,
   old_single_mapper_not_reused_for_candidate_128PC_parallel_returns=True,W1_fixed_successor_archived=True),
  physical_translation=dict(exact_retained_r17_formula=True,examples=examples,
   installed_low7_address_guard_incompatible_with_retained_provider_map=True,requires_explicit_PC_sideband=True,
   original_payload_and_sector_bits_must_not_be_overwritten=True,actual_DS_address_transform_binding=None,credit='mapping source audit, no physical endpoint admission'),
  common_ports_candidate=dict(request_fields=request_fields,return_fields=return_fields,protected_request_bits=rq,protected_return_bits=rp,
   physical_PC_prefix_retained_after_aggregation=True,no_onebit_generation_or_16bit_compression_credit=True,
   original_client_tag32_preserved=True,F0_authority_frozen=False),
  topology=dict(stacks=4,SM_inputs=32,non_SM_control_inputs=4,inputs_per_stack=36,PC_outputs_per_stack=32,
   producer_endpoint_lanes=producer_ports,source_128PC_return_matchers=128,candidate_36x32_forward_32x36_reverse_crossbars=4,
   fixed4PCs_per_SM_forbidden=True,crossbar_mux_gate_equivalents_ASSUMED=crossbar_mux,
   source_fanout32_36_buffer_gate_equivalents_ASSUMED=fanout_buffers,crossbar_registered_bits=crossbar_regs,
   crossbar_footprint_mm2_ASSUMED=crossbar_area,DS_same_36client_body_connection_not_proved=True,
   actual_non_SM_client_directory_class_map=None,steady_payload_upper_Bpc_FAST=4096,
   acceptance_cadence='one beat perPC output peredge,128 total; actual offered packets/eligibility/holds determine realized rate'),
  pipeline=dict(stages=38,seats_per_stage=2,candidate_steady_II=1,protected_bits=pipeline_bits,
   replacement_old_pipeline_bits=oldpipe,replacement_delta_bits=pipeline_bits-oldpipe,footprint_mm2_ASSUMED=pipeline_area,
   endpoint_fifo16_protected_bits=fifo_bits,replaced_old_F0_data_FIFO_bits=oldfifo_bits,delta_fifo_bits=fifo_delta,
   old_FIFO_logic_overlap_not_subtracted_from_screen_upper=True,stage_pop_never_parent_release=True,
   sink_backpressure='registered two-seat per-hop; no ready ripple; downstream wait remains unbounded without calendar receipts'),
  W5=dict(source_W2_context_rows_before=128*6*16,source_candidate_context_rows_after=128*7*16,
   context_row_protected_bits=row_bits,additional_context_bits=metadata_delta,additional_context_mux_gates=metadata_mux_delta,
   unadopted_bounded_quarantine_bits=quarantine_bits,unadopted_bounded_quarantine_area_mm2=quarantine_area,
   finite_16entry_no_reuse_bench_requires_quiescent_epoch_transition=True,
   additional_context_footprint_mm2_ASSUMED=metadata_area,read_update_ports={'allocate':1,'read_completion':1,'write_completion':1,'RF_ACK_consumer_reverse':'finite serialized update port, actual contention join required'},
   owned_gate_phase_order=['W2_held_done','W4_common_RF_ACK','W6_visible','W6_consumer','W6_reverse'],
   gate_keeps_same_requester_and_immutable_home=True,persistent_state_is_not_RF_SM_lifetime=True,
   no_epoch_wrap_or_live_reset_credit=True,installed_source=False,
   missing_actual_common_RF_ACK_reset_W4_contract=True,reset_both_domain_FIFO_pointer_and_backend_drain_required=True),
  resource_ledger=dict(complete_bridge_control_protected_bits=bits,complete_bridge_footprint_mm2_ASSUMED=area,
   clock_connectivity_buffer_count_min=buf,clock_connectivity_buffer_area_min_mm2=clock_area,
   clock_FF_load_ff_ASSUMED=bits*clock['worst_source_SS_FF_CLK_capacitance_ff'],clock_new_route_repeater_inventory=None,
   area_screen_is_not_placed_fit=True,original_RF_shared_L2_macro_area_not_recharged=True),
  floorplan=allocation,positive_RF_ACK_CDC_directory=f0['positive21_stage_inventory'],Dewey21phases=f0['actual21_KV_phase_join'],
  clocks=dict(FAST_target_hz=1200000000,serial_target_hz=900000000,r14_CORE_clock_source_binding=None,
   SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25,no_unsupported_clock_credit=True,
   receiver_synchronizer_edges_must_be_in_receiver_domain=True,source_clock_reset_port_pairs_need_F0_W4_freeze=True),
  latency=dict(forward_reverse_pipeline_target_FAST_edges=76,crossbar_capture_positive_FAST_edges_each=1,
   source_return_ARB7_CORE_edges_not_credited_as_free_parallel_service=True,RF_common_ACK_positive=True,
   CDC_receiver_sync_edges_each=2,directory_hit_and_cold_costs=f0['runtime_directory']['Qwen']['profile'],
   finite_sink_or_backend_eligibility_wait_upper=None,operator_critical_path_ns=None,whole_token_ns=None),
  implementation_dependency_order=['F0_commonports_namespace_reset','W2_exact_done_W4_commonACK_W6_lifecycle','W5_retained_gate_and_joint_calendar','W10_source_parallel_matcher_crossbars_CDC_pipeline_costs','full32SM_slot_clock_PG_cuts_admission','then_only_additive_RTL'],
  minimum_first_gate='C0 then KV read, original source matching + paired clocks + all bank ACK/visible/consumer/reverse; no full token credit',
  hardware_admitted=False,engine_build_allowed=False)
 replay=dict(translations=examples,switch=directed_switch())
 return {'model.json':canonical(model),'directed_replay.json':canonical(replay)}
def directed_switch():
 s=BankedSwitch(36,32);grants=[]
 for i in range(36):
  rows={j:dict(destination=7,payload=bytes([j])*32,owner='owner'+str(j)) for j in range(36)}
  accepted=s.step(rows,[True]*32);require(len(accepted)==1,'hot PC serializes onegrant');grants.extend(accepted)
 require(grants==list(range(36)),'directed all eligible 36way RR order')
 return dict(hot_PC_grants=grants,grant_edges=36,candidate_only=True,installed_fairness_credit=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--verify',action='store_true');a=p.parse_args()
 for n,v in outputs().items():
  if a.verify:require((BASE/n).read_bytes()==v,'exact W5/W10 replay '+n)
  else:
   require(a.output is not None,'explicit output');a.output.mkdir(parents=True,exist_ok=True);(a.output/n).write_bytes(v)
 print('PASS W5/W10 source-correct addressed fabric model; allocation/finite receipts FAIL')
if __name__=='__main__':main()
