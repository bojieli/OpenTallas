#!/usr/bin/env python3
"""Prospective PC40 actual physical ACK model; written before additive RTL.

Existing protected control padding is reused by exact index/lifetime; no free
provider FFs, codec, matcher, routes, clock/reset or latency. No physical claim.
"""
import json,hashlib,argparse,math
from pathlib import Path
import h4_hbm_c0_pc40_exact_gate_r2 as R2
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/h4_hbm_pc40_physical_ack_r3_20261003'
INPUT_SHA='561dd44105178535e18a6c3db9a0ac894a76a5047eb9157bb34e56ed826940f8'
def canonical(x):return (json.dumps(x,sort_keys=True,indent=2)+'\n').encode()
def inputs():
 raw=(BASE/'inputs.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=INPUT_SHA:raise ValueError('input manifest pin')
 out={}
 for r in json.loads(raw):
  p=ROOT/r['archive']
  if not p.resolve().is_relative_to((BASE/'inputs').resolve()):raise ValueError('archive scope')
  b=p.read_bytes()
  if hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('input SHA')
  out[p.name]=b
 return out

def compose(provider_extra_edges=1,matcher_edges=1,wait_edges=4,period_ns=1/1.2):
 if min(provider_extra_edges,matcher_edges)<1:raise ValueError('positive source/model ACK stages required')
 source=inputs();r=R2.compose(wait_edges,period_ns)
 w4=json.loads(source['component-price-r3.json'])
 if w4['latency']['added_local_RF_edges_vs_existing_ACK']!=1:raise ValueError('selected W4 provider')
 # RF-only branch: raw accepted tuple55 + pending1 + protected ACK72.
 # FullSM SIMD shadow/matcher is absent: do not charge its full gross.
 provider_ff=128;codec_gate_eq=2*768;ff_mux_gate_eq=127*3
 matcher_gate_eq=55*2+54+9*2+8+64 # XNOR,AND and phase/current flags.
 control_gate_eq=256;clock_buffers=math.ceil(provider_ff/64)
 reset_area_ASSUMED=provider_ff*2
 cell=provider_ff*.2916+(codec_gate_eq+ff_mux_gate_eq+matcher_gate_eq+control_gate_eq)*.3+clock_buffers*2+reset_area_ASSUMED
 footprint=cell/.5/1e6
 events=dict(r['cost_events']);events['W4_provider_extra_ACK']=5*provider_extra_edges;events['physical_ACK_matcher_stage']=5*matcher_edges
 return dict(schema='PC40_ACTUAL_PHYSICAL_ACK_R3',model_precedes_RTL=True,default_enabled=False,
  source_r2='8c3dfbf7910cb74cbc74497c787c3fc3b790bc82',W4_source='main selfcontained-peer-r10/design/ot_gpu_rf_service.sv ACK_ID1',
  source_slots=[17,18,17,18,19],owner_bits=46,slot_bits=9,ACK_tuple_bits=55,
  retained_control=dict(storage='existing SECDED256->288 row',accepted_root_owner46='raw59:14, immutable from request acceptance to retirement',
   actual_write_slot9='raw204:196 captured at actual write_go',pending='raw205',checked='raw206',remaining_padding='raw255:207 must zero',
   new_coded_words=0,new_physical_FFs=0,reused_padding_bits=11,reason='same control4word indices/lifetime/clock/update ports already priced in R2'),
  W6_receiver_join=dict(protocol_source='214d0a9924788b654cabb84ccb7006abd09d824c',protected_bits=144,new_coded_words=0,receiver_replicas=1,internal_SIMD_sources=0,price_rule='existing one144bit W6 row and its codecs/control already in R2; retained same index/lifetime/ports, no gross added'),
  adapter_selection=dict(clock='one clk input shared by actual W4/RF SRAM/PC40/FMIN/W6; no asynchronous boundary in selected module',CDC_seats=0,CDC_area=0,CDC_latency=0,CDC_zero_proof='same literal clock port on all selected instantiated modules, no remote RF port active; external reverseCDC still external authority, not installed CDC proof',held_owner55='W4 protected_ACK72 plus accepted root55 within original caller row; hold provider ACK until exact receiver take',admission_stop='local sticky raw188 gates all normal endpoints; error output stops parent issuer; external admission_stop OR local fault. Global drain producer Claude',error_route='same-edge mismatch/identity_fault blocks ACK and W6 boundary; protected sticky fault retains owner, workspace and pending tuple; reset/rearm only issuer-allcopy matched fence',added_route_sinks='one owner46 output to W4; one heldtuple55/fault return into protected comparator, final host ACK tuple into one W6',reset_wait_scope='W6 RESET_REQ/RESET_WAIT/IDLE each2 age+take edges, caller fenced rearm1: minimum7local edges after reset restoration; actual global allcopy/reset duration UNKNOWN and cannot become zero',reset_rearm_local_minimum_edges=7,reset_rearm_global_upper_edges=None),
  match=dict(expected='retained accepted owner46 + retained actual write slot9; explicit phase slot17/18/17/18/19 crosscheck',
   input='actual W4 held ACKowner46/slot9/fault',no_current_write_address=True,
   ACK_stage='one checked edge, current tuple still rechecked before every handshake; checked boolean alone cannot authorize',
   fault='same-edge block all normal grants/ACK/visibility/consumer/reverse/retire; sticky protected raw188 retains source debt',
   W6='req identity retained root owner46+RF19; final host ACK identity from validated physical tuple, not control retag',
   reset='runtime reset with pending debt faults; coordinated source reset/rearm after allcopy quiescence only; no coldPOR production waiver'),
  ports=dict(new_forward_owner46=46,new_reverse_owner_slot55=55,new_reverse_fault=1,additional_boundary_bits=102,
   RF_read_commands=4,RF_write_commands=5,RF_mirror_write_bytes=5120,RF_MACs=0,HBM_commands=0,additional_RF_macros=0,
   provider_replica_count_per_SM=1,SMs=32,matcher_lookup_ports=1,ACK_outstanding_per_SM=1),
  costs=dict(provider_raw_accepted_tuple_bits=55,provider_pending_bits=1,provider_protected_ACK_bits=72,provider_total_new_FFs=provider_ff,
   provider_codecs=2,codec_gate_eq_ASSUMED=codec_gate_eq,provider_FF_mux_gate_eq_ASSUMED=ff_mux_gate_eq,
   matcher_gate_eq_ASSUMED=matcher_gate_eq,control_gate_eq_ASSUMED=control_gate_eq,clock_buffers_ASSUMED=clock_buffers,
   async_reset_buffer_cell_area_um2_ASSUMED=reset_area_ASSUMED,cell_um2_ASSUMED=cell,footprint_mm2_50pct_ASSUMED=footprint,
   actual_cell_net=None,once_only='replace original RF provider branch; no fullSM SIMD shadow or fullW4 comparator gross added',
   full32SM_extra_mm2_ASSUMED=32*footprint),
  calendar=dict(events=events,cycles_conditional=sum(events.values()),ns_conditional=sum(events.values())*period_ns,
   provider_extra_edges_per_write=provider_extra_edges,matcher_edges_per_write=matcher_edges,
   whole_token_ns=None,eligibility=r['eligibility'],once_only='replace selected r2 fivewrite ACK subtree and r9 selected events once, do not add gross twice'),
  physical=dict(target_ns=period_ns,setup_ps=60,hold_ps=25,lower_additional_routing_tracks=102,
   allowed_local_slot_extra_mm2=footprint,slot_fit=None,channel_capacity=None,loaded_SSFF=False,clock_buffer_sizing='2 positive allowance buffers, actual CTS fanout/clock routes still unqualified',
   provisional_service_enclosure_mm2_per_SM=r['total_controller_consumer_footprint_mm2_ASSUMED']+footprint),
  scope=dict(functional_defaultoff_source_preparation=True,physical_build=False,production_native_allocator=False,
   production_entering_leases=False,full_system=False,mutable_upset_qualification=False,
   selected_arithmetic_scope=r['exception_scope'],provider_raw_transient_warning='W4 accepted_identity55 is raw prior to protected_ACK; no protected route qualification or hidden protection claim'),
  qualifications='prospective positive component cost model enables additive functional source; physical and fullprogram admission FALSE')

class ACKReference:
 """Control-only exact accepted-tuple reference for negative tests, no oracle."""
 def __init__(self):self.owner=None;self.slot=None;self.pending=False;self.checked=False;self.fault=False
 def accept_root(self,owner):
  if self.pending or self.fault:raise ValueError('owned debt')
  if not 0<=owner<2**46:raise ValueError('owner46')
  self.owner=owner
 def write(self,slot):
  if self.owner is None or self.pending or self.fault:raise ValueError('write exclusion')
  if slot not in [17,18,19]:raise ValueError('source slot')
  self.slot=slot;self.pending=True;self.checked=False
 def ack(self,owner,slot,phase_slot,provider_fault=False):
  if self.fault:return False
  if provider_fault or not self.pending or (owner,slot)!=(self.owner,self.slot) or slot!=phase_slot:
   self.fault=True;return False
  if not self.checked:self.checked=True;return False
  self.pending=False;self.checked=False;return True
 def reset(self):
  if self.pending:self.fault=True

def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 raw=canonical(dict(model=compose(),sensitivity=[compose(p,m)['calendar']['ns_conditional'] for p in [1,2,3] for m in [1,2,3]]))
 out=BASE/'model.json'
 if a.verify:
  if out.read_bytes()!=raw:raise ValueError('cold replay')
 else:out.write_bytes(raw)
 print('PASS model replay' if a.verify else 'WROTE priced model BEFORE R3 RTL')
if __name__=='__main__':main()
