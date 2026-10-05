#!/usr/bin/env python3
"""Priced default-off RF C0 controller; conditional model, never physical admission.

Consumes archived real native/home and RF/W6 source. No numerical callback.
The accepted issuer supplies owner46; its allocator is NOT replaced by PC35.
"""
import argparse, gzip, hashlib, json, math, copy
from functools import lru_cache
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003'
INPUT_SHA='2b5344d2097eb860d465581595bdc88687fb22a29425efdb1c4b8bcda9650410'
def canonical(x): return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
@lru_cache(maxsize=1)
def inputs():
 raw=(BASE/'inputs.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INPUT_SHA: raise ValueError('manifest identity')
 result={}
 for row in json.loads(raw):
  path=ROOT/row['archive']
  if not path.resolve().is_relative_to((BASE/'inputs').resolve()): raise ValueError('archive scope')
  data=path.read_bytes()
  if hashlib.sha256(data).hexdigest()!=row['sha256']: raise ValueError('source identity')
  result[path.name]=data
 return result
@lru_cache(maxsize=1)
def program(): return json.loads(gzip.decompress(inputs()['Qwen_tiled.json.gz']))
def model(wait_edges=4,period_ns=1/1.2):
 if type(wait_edges) is not int or wait_edges<=0: raise ValueError('positive explicit eligibility/stall bound')
 if not math.isfinite(period_ns) or period_ns<=0: raise ValueError('positive clock')
 src=inputs(); n=program(); op=n['operations'][40]
 assert op['opcode']=='SILU_GATE'
 plan=json.loads(src['Ampere_model.json'])['selected_C0_command']
 assert plan['native_command']['source_PC']==40 and plan['native_command']['opcode']=='FMAX'
 assert plan['source_step']==n['microcode']['exp'][0]
 gate=plan['source_gate_home'];assert (gate['storage_rank'],gate['storage_SM'],gate['RFslot9'])==(0,0,38)
 assert plan['parent55'] is None
 views=[gate]+plan['transient_enrollment']
 assert b'ack_valid<=1' in src['ot_gpu_rf_service.sv'] and b'u_operand_b' in src['ot_gpu_rf_service.sv']
 assert b'.LAT(LAT)' in src['ot_gpu_fadd.sv']
 w2=json.loads(src['W2_b846_model.json']); assert w2['calendar']['conservative_new_lookup_II_edges']==5
 w2_fix=json.loads(src['W2_22ec_model.json'])['early_return_calendar']; assert w2_fix['conservative_lookup_II_edges']==8
 # Literal implementation state: 4 SECDED control words, 128 data words, one existing W6 row.
 control_bits=4*72; data_bits=2*64*72; w6_bits=144
 # Conservative cell screen: mutable storage + explicit 2:1 vector selector,
 # all codec encode/decode seats, controller compare+decode, buffered clock tree.
 codec_words=4+128+128
 codec_gate_eq=codec_words*768*2
 mux_gate_eq=4096*3*2
 control_gate_eq=2048
 clock_buffers=math.ceil((control_bits+data_bits+w6_bits+128*72)/64)
 fmax_pipeline_bits=128*72
 fmax_gate_eq=128*(31*8+32*3+40)
 cell_um2=(control_bits+data_bits+fmax_pipeline_bits)*.2916+(codec_gate_eq+mux_gate_eq+control_gate_eq+fmax_gate_eq)*.3+clock_buffers*2
 footprint=cell_um2/.5/1e6
 # 3 paired reads, 5 mirrored writes. Six boundary-grant edges in W6's
 # visible/consumer/reverse/current-allcopies sequence remain positive.
 edges=dict(dispatch=2,RF_read=3*3,RF_write=5*2,NEG_bitcast_XOR_bitcast=3,FMAX=3,W6=19,
            external_wait=(3+5+7)*wait_edges,reverse_CDC_guard=2)
 return dict(schema='HBM_C0_CONNECTED_CONTROLLER_G0_R1',source_PC=40,tile_start=0,active_lanes=128,
   ordered_native_steps=n['microcode']['neg']+[n['microcode']['exp'][0]],
   source_operand_plan=plan,source_views=views,scratch_slots=[17,18,19],
   scope='actual PC40 FMAX source operand/producer plan, default-off controller; no native numerical receipt',
   finite_workspace_calendar=dict(exclusive_slots=[17,18,19],max_outstanding=1,
    acquire='accepted source dispatch before first home read',
    producer_order=['RF38 capture -> RF17', 'mask -> RF18', 'BITCAST_U/XOR/BITCAST_F -> RF17', '-87 -> RF18', 'FMAX -> RF19'],
    release='matched W6 consumer, child reverse, parent reverse, CDC, CURRENT all-copy drain and held retire handshake',
    gate_up_caller_leases='remain with actual SILU caller through reciprocal and ordered final products; NOT released by this callee',
    no_workspace_reuse_before_retire=True,calendar_scope='one source callee, finite conditional wait bounds; whole emitted calendar pending'),
   native_identity_bits=128,owner46_supplied_by='accepted issuer binding, never fabricated HBM PC from source PC40',
   RF_identity_bits=55,replicas=32,selected_output_endpoints=[dict(rank=0,SM=0,RFslot9=19,kind='transient SSA')],
   state=dict(control_protected_bits=control_bits,vector_protected_bits=data_bits,W6_existing_endpoint_bits=w6_bits,
    FMAX_pipeline_protected_bits=fmax_pipeline_bits,new_RF_macros=0,new_RF_workspace_vectors=3,new_HBM_transactions=0,mutable_codec_words=codec_words),
   ports=dict(RF_read_count=3,RF_read_payload_bits=8192,RF_write_count=5,RF_write_payload_bits=4096,
    physical_mirror_write_bits=5*8192,RF_2R1W=True,remote_payload_bits=0,
    RF_write_boundary_bits=4096+9+2,RF_read_boundary_bits=8192+18+4,
    request_metadata_bits=46+128,visible_identity_bits=55,CDC_requires='actual consumer reverse CDC certificate; data path is same selected SM'),
   bandwidth=dict(MAC_per_cycle=0,FMAX_lanes=128,compute_intensity_FMAX_per_RF_byte=128/(3*1024+5*512),
    read_bytes_per_service=1024,write_bytes_per_service=512,peak_remote_bytes_per_grant=0,
    vector_muxes=3,vector_mux_width=4096,identity_fanout_sinks=1),
   area=dict(cell_um2_ASSUMED=cell_um2,controller_footprint_mm2_50pct_ASSUMED=footprint,
    full32SM_controller_footprint_mm2_ASSUMED=32*footprint,codec_gate_eq=codec_gate_eq,
    W6_replaces_existing_rows_not_added_again=True,RF512_reuse_existing_H1=True,FMAX128_new_compare_select_priced=True,
    FMAX_pipeline_bits=fmax_pipeline_bits,FMAX_gate_eq=fmax_gate_eq,clock_buffer_count_ASSUMED=clock_buffers,slot_fit='component budget only; no installed floorplan/PG/exclusion claim'),
   cuts=dict(local_RF_bundle_bits=8192+18+4,remote_bundle_bits=0,
    lower_tracks_one_wire_per_bit=[8192+18+4,4096+9+2],selected_channel_capacity=None,
    route_admission=False,requires='actual SM local pin/cut allocation and aligned placed macro census before physical launch'),
   calendar=dict(event_edges=edges,total_edges=sum(edges.values()),period_ns=period_ns,
    duration_ns=sum(edges.values())*period_ns,clock_scope='source streaming 1.2GHz target; loaded SS/FF NOT qualified',
    setup_uncertainty_ps=60,hold_uncertainty_ps=25,
    eligibility_assumption=f'exclusive connected RF lease and every external ready/consumer/drain/reverse eligible within {wait_edges} edges',
    finite_wholeprogram_contender_bound=None,sensitivity_required=True),
   W2=dict(selected_on_this_RF_path=False,new_bits_charged_on_RF_path=0,
    HBM_candidate_protected_bits_perPC=13608,HBM_candidate_II=w2_fix['conservative_lookup_II_edges'],
    minimum_clean_request_read_write_edges=[w2_fix[k] for k in ('minimum_clean_request_edges','minimum_clean_read_edges','minimum_clean_write_edges')],
    earliest_read_write_edges=[w2_fix['early_read_edges'],w2_fix['early_write_edges']],
    coded_commit_edges=4,repair_contention_extra_edges=None,
    HBM_candidate_read_bytes_per_edge_upper=w2_fix['bytes_per_service_edge_upper'],
    candidate_source='22ec32816 (exact archived origin in inputs.json), replaces b846 minimum calendar',
    old9144_not_selected_for_new_protection=True,actual_HBM_successor_installed=False,
    old_F0_matched_replacement_debit=None),
   component_RTL_scope='functional controller source implementation under explicit conditional finite-bound model',
   physical_build_admitted=False,whole_token_latency_ns=None,
   missing=['source issuer allocation of direct-RF owner46',
    'actual Dewey emitted finite contender/eligibility bound', 'consumer reverse CDC source connection',
    'source sized slot/clock/PG/cut enrollment and mutable protection stage closure'])
def source_plan(owner_tag, generation):
 if any(type(x) is not int or x<=0 or x>=2**64 for x in (owner_tag,generation)):
  raise ValueError('native64 identity')
 plan=json.loads(inputs()['Ampere_model.json'])['selected_C0_command']
 old=plan['native_command']['generation']
 def update(x):
  if isinstance(x,dict):return {k:(generation if k=='generation' else update(v)) for k,v in x.items()}
  if isinstance(x,list):return [update(v) for v in x]
  if isinstance(x,str):return x.replace(f':epoch{old}:',f':epoch{generation}:')
  return x
 plan=update(plan);plan['native_command']['owner_tag']=owner_tag
 plan['native_owner'][-1]=generation
 return plan

def emit_source(plan, *, enabled=False):
 if not enabled:raise ValueError('direct source emitter default off')
 cmd=plan['native_command']
 expected=source_plan(cmd['owner_tag'],cmd['generation'])
 if plan!=expected:raise ValueError('exact Ampere source view/expression/lease packet required')
 return dict(schema='C0_CONNECTED_SOURCE_PACKET_R1',model=cmd['model'],source_PC=40,tile_start=0,
  ordered_producer_actions=copy.deepcopy(plan['ordered_producer_actions']),
  native_command=copy.deepcopy(cmd),RF_source_slot9=38,RF_workspace=[17,18,19],
  source_opcode='FMAX',literal_minus87_U32=0xc2ae0000,
  issuer_owner46=None,issuer_binding='requires actual accepted issuer mapping; NOT allocated from software PC',
  HBM_addresses=[],W2_parent55=None,endpoint='rank0.SM0.RF19 transient',
  original_cdb_production_guard_changed=False,whole_program_supported=False,
  installed_hardware_admitted=False)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true'); a=p.parse_args()
 result=dict(model=model(),sensitivity=[model(b,t)['calendar'] for b in (1,4,16) for t in (1/1.2,1,1/0.9)])
 raw=canonical(result)
 path=a.out or BASE/'model.json'
 if a.verify:
  if path.read_bytes()!=raw: raise ValueError('model replay differs')
  print('PASS byteexact source model; physical admission remains FAIL')
 else: path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
if __name__=='__main__':main()
