#!/usr/bin/env python3
"""DS retained 3:4 ratio FIFO source/physical gap. No RTL or physical launch.
Integer VCO-tick event transcription preserves simultaneous-edge pre-NBA state.
This is a source audit, not an executed RTL gate or metastability proof.
"""
import gzip,hashlib,json,math,re
from pathlib import Path
from fractions import Fraction as F
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_ratio_fifo_gap_20261003'

def load(name):return json.loads((BASE/'inputs'/name).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

class FIFO:
 def __init__(self,depth=4):
  self.depth=depth;self.mod=2*depth;self.mem=[None]*depth
  self.wp=self.wp_pub=self.rp=self.rp_pub=self.rp_w=self.wp_r=0;self.rv=False;self.rd=None
 def edge(self,wedge,redge,wv=False,wd=None,ready=True,wrst=True,rrst=True):
  old=self.__dict__.copy();wrdy=(old['wp']-old['rp_w'])%self.mod<self.depth
  take=old['wp_r']!=old['rp'] and (not old['rv'] or ready)
  event=dict(write_fire=wedge and wv and wrdy,read_capture=redge and take,
   consumer_fire=redge and old['rv'] and ready,consumer_word=old['rd'],data_capture_word=None,
   data_capture_slot=old['rp']%self.depth if redge and take else None)
  if redge and take:
   self.rd=old['mem'][old['rp']%self.depth];event['data_capture_word']=self.rd
  # Data arrays have no reset gating, exactly as retained source.
  if wedge and wv and wrdy:self.mem[old['wp']%self.depth]=wd
  if wedge:
   if not wrst:self.wp=self.wp_pub=self.rp_w=0
   else:
    self.wp=(old['wp']+int(wv and wrdy))%self.mod
    self.wp_pub=old['wp'];self.rp_w=old['rp_pub']
  if redge:
   if not rrst:self.rp=self.rp_pub=self.wp_r=0;self.rv=False
   else:
    self.wp_r=old['wp_pub'];self.rp=(old['rp']+int(take))%self.mod
    self.rp_pub=self.rp;self.rv=True if take else (False if old['rv'] and ready else old['rv'])
  return event

def isolated(wperiod,rperiod,write_tick,stall_until=-1):
 f=FIFO();capture=None;consume=None
 for t in range(write_tick+200):
  e=f.edge(t%wperiod==0,t%rperiod==0,wv=t==write_tick,wd=(0,write_tick),ready=t>stall_until)
  if e['read_capture'] and capture is None:capture=t
  if e['consumer_fire']:
   consume=t;assert e['consumer_word']==(0,write_tick);break
 assert capture is not None and consume is not None
 return dict(write_tick=write_tick,data_capture_ticks=capture-write_tick,consumer_accept_ticks=consume-write_tick,
  data_capture_destination_cycles=str(F(capture-write_tick,rperiod)),consumer_accept_destination_cycles=str(F(consume-write_tick,rperiod)))

def stream(wperiod,rperiod,n=2048,stall_mod=0):
 f=FIFO();sent=0;got=[];last_write={};last_read={};overwrite_before_capture=[];output_changed_while_stalled=[];prev=None
 for t in range(200000):
  before=(f.rv,f.rd);ready=not stall_mod or (t//rperiod)%stall_mod!=0
  slot=f.wp%f.depth;readslot=f.rp%f.depth
  e=f.edge(t%wperiod==0,t%rperiod==0,wv=sent<n,wd=sent,ready=ready)
  if e['read_capture']:last_read[readslot]=t
  if e['write_fire']:
   if slot in last_write and last_read.get(slot,-1)<last_write[slot]:overwrite_before_capture.append(t)
   last_write[slot]=t;sent+=1
  if t%rperiod==0 and before[0] and not ready and (f.rv,f.rd)!=before:output_changed_while_stalled.append(t)
  if e['consumer_fire']:got.append(e['consumer_word'])
  if len(got)==n:break
 assert got==list(range(n))
 return dict(words=n,terminal_tick=t,ordered_once=True,overwrite_before_capture=overwrite_before_capture,stalled_output_changes=output_changed_while_stalled,
  max_service_words_per_second=900000000,actual_simulation='Integer source-event transcription, not HDL execution')

def reset_witnesses():
 f=FIFO();e=f.edge(True,False,wv=True,wd=123,wrst=False)
 write=dict(wrst_n=0,w_v=1,w_rdy=True,write_fire=e['write_fire'],wp_after=f.wp,mem_slot0_after=f.mem[0],unpublished_write=True)
 f=FIFO()
 for t in range(40):f.edge(t%3==0,t%4==0,wv=t==0,wd='old_epoch',ready=True)
 assert f.wp==f.rp==1
 f.edge(False,True,rrst=False)
 replay=[]
 for t in range(1,24):
  e=f.edge(t%3==0,t%4==0,wv=False,ready=True)
  if e['consumer_fire']:replay.append(e['consumer_word'])
 return dict(write_during_write_reset=write,reader_only_reset_after_retirement=dict(previously_retired='old_epoch',new_write_count=0,consumer_replay=replay,stale_epoch_replay=bool(replay)))

def build():
 for r in load('origins.json'):
  if sha(BASE/'inputs'/r['copy'])!=r['sha256']:raise ValueError('Source archive drift')
 p=load('6_physical.json');c=load('7_corner_sta.json');clock=load('5_clock_plan.json')
 src=(BASE/'inputs/0_ot_chip_v41_ratio_fifo.sv').read_text();u=(BASE/'inputs/3_uarch_model.py').read_text()
 assert p['design']['sources'][0]['sha256']==sha(BASE/'inputs/0_ot_chip_v41_ratio_fifo.sv')
 assert c['setup_ss']['sdc_sha256']==sha(BASE/'inputs/6_final.sdc')
 assert p['place_and_route']['artifacts']['6_final.v']['sha256']==sha(BASE/'inputs/6_final.v')
 assert 'fast_to_slow_slow_cycles=4, slow_to_fast_fast_cycles=5' in u
 assert 'rp_pub <= take ? rp + 1\'b1 : rp;' in src
 ss=(BASE/'inputs/w18_sta_ss.log').read_text()
 assert 'mem[0][63]' in ss and 'r_d[63]' in ss and '-75.59   slack (VIOLATED)' in ss
 schedules={name:[isolated(w,r,t) for t in range(0,12,w)] for name,w,r in [('fast_to_slow',3,4),('slow_to_fast',4,3)]}
 phase={name:dict(min_data_capture_ticks=min(v['data_capture_ticks'] for v in cases),max_data_capture_ticks=max(v['data_capture_ticks'] for v in cases),max_consumer_ticks=max(v['consumer_accept_ticks'] for v in cases)) for name,cases in schedules.items()}
 sparse=clock['cdc']['bench']['sparse']['result'];stalls=clock['cdc']['bench']['random_stall']['result']
 ports=[dict(name=x['point'],declared_direction=x['from_domain'],fast_bits=x['width_bits'],historical_slow_bits=x['widened_bits'],required_slow_bits_ceil=math.ceil(x['width_bits']*4/3),actual_current_parent_fifo_instance=None,actual_pack_unpack_provider=None) for x in clock['cdc']['points']]
 d=4;w=64;aw=2
 m=dict(schema='DSROM_RATIO_FIFO_FROZEN_SOURCE_GAP_V1',source_main='09984efcab74873e6e03352607ab3d2c6442eccb',source_hash=sha(BASE/'inputs/0_ot_chip_v41_ratio_fifo.sv'),
  retained_physical=dict(SS_setup_ps=c['setup_ss']['worst_register_d_slack_ps'],FF_hold_ps=c['hold_ff']['worst_register_d_slack_ps'],SS_reported_pointer_path_ps=32.042370,failed_path='mem[0][63] -> r_d[63]',source_matches_current=True,full_2clock_final_SDC_hash_verified=True,uncertainty_ps=dict(setup=60,hold=25),source_period_ps=dict(fast=833.333,slow=1111.111),
   record_scope='Standalone W64/DEPTH4 related-clock failure, not actual parent closure. physical.json top corner label TT disagrees with corner_sta SS/FF: use exact retained SS/FF logs/SDC; do not transfer TT label or aggregate fmax.',
   setup_path=dict(launch_edge_ps=833.33,capture_edge_ps=1111.11,launch_clock_arrival_ps=951.33,capture_clock_arrival_ps=1182.03,data_arrival_ps=1193.76,data_required_ps=1118.17),
   standalone_cell_area_um2=p['design']['area_um2'],standalone_core_area_um2=p['design']['core_area_um2'],ODB_hash=c['setup_ss']['odb_sha256'],SPEF_hash=c['setup_ss']['spef_sha256']),
  ports=dict(W=w,DEPTH=d,clock_ports=['wclk','rclk'],reset_ports=['wrst_n','rrst_n'],input_payload_bits=w,output_payload_bits=w,control_ports=['w_v','w_rdy','r_v','r_rdy'],MACs_per_cycle=0,accepted_bytes_per_source_cycle=8,delivered_bytes_per_destination_cycle=8,maximum_sustained_payload_bits_s=900000000*w,max_common_ready_state_seats=5,
   declared_state_bits=(d+1)*w+6*(aw+1)+1,state_breakdown=dict(mem=d*w,output=w,pointers=6*(aw+1),valid=1),mapped_sequential_cells=p['synthesis']['sequential_cell_count'],mapped_state_scope='Declared339 bits vs mapped336 cells: synthesis optimization not yet role-audited; do not equate declared state to retained cell count.',
   structural_cross_domain_bits=dict(data_array_to_mux=d*w,forward_pointer=aw+1,reverse_credit_pointer=aw+1),
   crossing_track_floor_unshielded_one_wire_per_signal=d*w+2*(aw+1),boundary_external_signal_bits=2*w+8,replica_count_in_actual_parent=None,fanout=dict(each_memory_bit_output_mux=1,read_pointer_select_logical_output_bits=w,publication_pointer_receiver_per_bit=1),
   rate_matching='FIFO W identical at both ends. It cannot implement 4/3 pack/unpack, and depth4 cannot sustain producer1.2Gwords/s against consumer0.9Gwords/s without throttling. Separate finite width-conversion hardware is required for unthrottled equal-bit-rate ports.'),
  source_events=dict(write_accept='w_v && w_rdy at wclk',publish='wp_pub samples previous wp one write edge after write',visibility='wp_r samples wp_pub at rclk; take uses previous wp_r',capture='take reads selected mem into r_d and advances rp/rp_pub at rclk',consumer='previous r_v && r_rdy at rclk',credit='rp_w samples rp_pub at wclk; w_rdy from modular wp-rp_w',physical_stability='Consumed slot can be reclaimed after local r_d capture: writer may reuse mem while downstream holds output, but must not overwrite before capture.'),
  exact_phase_event_model=schedules,phase_bounds=phase,phase_unit_ps='2500/9 (one3.6GHzVCO tick)',
  actual_retained_dual_clock_bench=load('../retained_bench_replay.json'),
  actual_reset_witness_record=json.loads((ROOT/'results/rtl/dsrom_ratio_fifo_reset_witness_20261003/record.json').read_text()),
  current_RTL_callers=['rtl/test/tb_chip_v41_ratio_fifo.sv'],parent_FIFO_instantiation_found=False,caller_census=load('8_rtl_ratio_fifo_callers.json'),
  qualified_service_contract=dict(no_stall_sparse_only=True,unbounded_downstream_stall_implies_unbounded_retirement=True,rate_limit_words_s=900000000,conditional_conservative_retirement_bound_destination_cycles='L_sparse + 5*(B+1); L_sparse=4 fast-to-slow or5 slow-to-fast. Only if every rolling B+1 destination-edge window provides r_rdy, both clocks continuous/phase-bound, and no reset/epoch abort; source-model bound not executed service proof.',needed_for_finite_upper_bound=['maximum ready-low duration B in destination cycles','producer maximum burst and sustained word/bit rate','consumer finite acceptance calendar and drain/epoch barrier','payload packing and tag/reset semantics at each actual parent port']),
  existing_model=dict(fast_to_slow_slow_cycles=4,slow_to_fast_fast_cycles=5,fast_to_slow_ns=str(F(4,1)/F('0.9')),slow_to_fast_ns=str(F(5,1)/F('1.2')),scope='Sparse write-to-consumer availability allowance; NOT all queued/stalled service or physical timing proof',archived_sparse=sparse,archived_stalled=stalls,composed_model_rule='Current _cons_adjust charges one CDC latency per destination node with any dependency in the other domain (except hop), not one latency per individual dependency; multiple producers still require joint readiness/calendar and finite service.',current_graph_event_to_parent_FIFO_binding=None),
  historical_port_ledger=ports,stream_event_checks={name:stream(wp,rp,stall_mod=7) for name,wp,rp in [('fast_to_slow',3,4),('slow_to_fast',4,3)]},reset_witnesses=reset_witnesses(),
  minimal_successor=dict(default_off=True,engine_RTL_written=False,repair_priority=[
   'Bind actual parent directions/W/replicas and bounded producer-consumer service. Keep equal-width FIFO as such; explicit pack/unpack and credits if same bit-rate required.',
   'Gate acceptance and all array captures during coordinated reset. Assert flush across both domains, synchronize release locally and require both-domain epoch-ready barrier. Freeze/retire prior epoch source tags/transactions before ready; one-sided pointer reset can replay stale payload.',
   'Phase transcription shows8VCOticks minimum accepted-write to selected data capture, but that is not a mapped timing exception proof. Before changing data hardware, prove each selected slot stable from acceptance through read capture, and prove credit-controlled reuse. Only then investigate exact enable/protocol-sensitization timing constraints for the selected mem->r_d arc with both setup and hold obligations; NO blanket false path or blanket multicycle exception authorized.',
   'If protocol-specific timing proof/actual parent constraints cannot close, model one explicit registered read-mux stage with finite holding/backpressure and credit lifecycle before RTL. It would add W data+valid state per replica and one destination latency cycle, but throughput requires a skid/credit proof; not admitted or assumed necessary.'
  ],planned_capture_cycles_added=0,registered_fallback_added_cycles=dict(fast_to_slow_slow=1,slow_to_fast_fast=1),registered_fallback_per_critical_crossing_added_ns=dict(fast_to_slow=str(F(1)/F('0.9')),slow_to_fast=str(F(1)/F('1.2'))),fallback_state_lower_bound_bits=w+1,removed_state_area_credit=0,
    area_and_route_admission='No actual parent replica/slot/channel/clock/PG provider yet. Standalone291.819um2 is only W64 historical context, cannot linearly qualify widened product. Price actual mux/demux, reset/epoch barrier, any width-converter reservoirs, loads and all replicas before mapping.'),
  target_applicability=dict(DeepSeek_ROM='Direct retained FIFO/source-model gap; no current parent instance binding or physical admission',Qwen_ROM='CDC method reusable after its own clock/port/service/source binding; no DS timing or width transfer',DeepSeek_HBM='Popper bridge ownership retained; methodology exchange only, no ROM FIFO implementation/latency transfer',Qwen_HBM='Popper bridge ownership retained; methodology exchange only, no DS physical qualification transfer'),
  admission=dict(source_audit_complete=True,model_preparation_admitted=True,successor_engine_RTL_admitted=False,physical_build_admitted=False,reason='Current parent FIFO instance map, port adapters, finite service/epoch/reset, disjoint area/routes and loaded related-clock SS60/FF25 parent context are not bound. Existing source timing failure immutable; fixed4/5 is not a worst-case service guarantee.'),
  live_global_solver_unchanged=True,HBM_bridge_ownership_unchanged=True,new_jobs=[],new_source_RTL_files=[])
 (BASE/'model.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n');return m
if __name__=='__main__':print(json.dumps(build()['admission'],indent=2))
