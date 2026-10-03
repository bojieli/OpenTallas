#!/usr/bin/env python3
"""Prospective default-off finite phase bridge; original engine is unchanged.
One selected contract: phase-specific reserve, two shard-local root banks,
existing stage-link framing, native scalar ROM writer-slot0 publication, held
ownership until VM-visible and captured positive credit. No hardware admission.
"""
import argparse,collections,gzip,hashlib,json,math
from fractions import Fraction
from pathlib import Path
import uarch_model_dsrom_field_bridge as B
import dsrom_field_bridge_queue_bounds as Q
ROOT=Path(__file__).resolve().parents[1];OUT=Q.OUT
class PhaseBridge:
    def __init__(self,rows,positions,owner,era=0):
        if len(owner)!=10 or any(type(x) is not int or x<0 for x in owner):raise ValueError('full169 owner tuple')
        widths=[6,2,9,10,32,32,32,32,14,0]
        # Ten fields: stage/rank/EID/phase/key/gen/user/Xversion/PC/resetera.
        for value,bits in zip(owner,widths):
            if bits and value>=1<<bits:raise ValueError('owner field truncation')
        if owner[-1]!=era:raise ValueError('reset handshake era')
        if not 1<=positions<=6 or rows<1:raise ValueError('phase dimensions')
        self.owner=tuple(owner);self.era=era;self.rows=rows;self.positions=positions
        self.depth=[positions*B.root_rows(rows,r) for r in range(128)]
        self.reserved=False;self.go=False;self.native_idle=False;self.poison=False
        self.records={};self.visible={};self.credit={};self.vmlease=True;self.last_edge=-1
    def reserve(self,free_per_root,writer_extent_exclusive,reset_handshake_complete):
        if self.go or self.reserved:raise ValueError('no reservation replacement under phase lease')
        if not writer_extent_exclusive or not reset_handshake_complete:raise ValueError('no GO without writer/reset authority')
        if len(free_per_root)!=128 or any(a<b for a,b in zip(free_per_root,self.depth)):raise ValueError('full phase reserve required')
        self.reserved=True
    def launch(self):
        if not self.reserved or self.go or self.poison:raise ValueError('reservation before GO')
        self.go=True
    def capture(self,edge,owner,shard,root,row,pos,raw):
        if not self.go or tuple(owner)!=self.owner or self.poison:raise ValueError('captured owner not admitted')
        if root!=(row%256)//2 or shard!=root//64 or not 0<=row<self.rows or not 0<=pos<self.positions or not 0<=raw<1<<69:raise ValueError('source root/row/position/shard/raw69')
        key=(pos,row)
        if key in self.records:raise ValueError('duplicate capture cannot retire debt')
        used=sum(1 for p,r in self.records if (r%256)//2==root)
        if used>=self.depth[root]:raise ValueError('reserved root seat overflow')
        self.records[key]=(edge,raw)
    def vm_visible(self,edge,owner,pos,row,writer_exclusion_proved,actual_postNBA):
        key=(pos,row)
        if tuple(owner)!=self.owner or key not in self.records or key in self.visible:raise ValueError('visible identity/debt')
        if not writer_exclusion_proved or not actual_postNBA or edge<=self.records[key][0]:raise ValueError('acceptance is not VM visibility')
        self.visible[key]=edge
    def credit_return(self,edge,owner,pos,row):
        key=(pos,row)
        if tuple(owner)!=self.owner or key not in self.visible or key in self.credit or edge<=self.visible[key]:raise ValueError('positive captured credit after same-owner visibility')
        self.credit[key]=edge
    def rearm(self,edge,native_idle,packet_debts):
        n=self.rows*self.positions
        if not self.go or self.poison or not native_idle or packet_debts or len(self.credit)!=n or edge<=max(self.credit.values(),default=-1):raise ValueError('pre-F native idle plus all visible/credit/packet debts')
        self.native_idle=True;self.go=False;return edge
    def release_vmlease(self,actual_SU_drain_and_Rplus2):
        if not actual_SU_drain_and_Rplus2:raise ValueError('VM version not freed at bank rearm')
        self.vmlease=False
    def reset(self,new_era,peer_quiescent):
        if self.go or not peer_quiescent:raise ValueError('reset cannot erase accepted debt')
        if new_era<=self.era:raise ValueError('no resetera wrap alias')
        self.era=new_era;self.reserved=False;self.poison=True  # fresh reset-qualified owner enrollment required

class ReadTokens:
    """Unstallable registered read launch requires a pre-reserved sink token.
    With blocked local packet/writer service stop issuing, not the native field.
    Transfer may return this local token only after charged packet-memory/sink
    ownership acceptance and positive captured credit; phase debt stays separate.
    """
    def __init__(self,owner,capacity=16,latency=13):
        if capacity<1 or latency<1:raise ValueError('positive finite read service')
        self.owner=tuple(owner);self.capacity=capacity;self.latency=latency;self.pending={};self.returned={}
    def issue(self,edge,seq):
        # Credits sampled strictly before this issue edge, not same-edge.
        for q,t in list(self.returned.items()):
            if t<edge:del self.returned[q];del self.pending[q]
        if seq in self.pending or len(self.pending)>=self.capacity:raise ValueError('no unreserved read token')
        self.pending[seq]=(edge,None)
    def transfer(self,edge,seq,owner,charged_sink_seat_reserved,accepted):
        if tuple(owner)!=self.owner or seq not in self.pending:raise ValueError('readtoken identity')
        issued,old=self.pending[seq]
        if edge<issued+self.latency or old is not None or not charged_sink_seat_reserved or not accepted:raise ValueError('registered return and reserved accepted sink')
        self.pending[seq]=(issued,edge)
    def return_credit(self,edge,seq,owner):
        if tuple(owner)!=self.owner or seq not in self.pending:raise ValueError('read credit identity')
        issued,transfer=self.pending[seq]
        if transfer is None or edge<=transfer or seq in self.returned:raise ValueError('positive local captured credit')
        self.returned[seq]=edge

def packet_service(remote_rows,flit=256,max_flits=256,forward=1337,reverse=1337,timeout=4096,read_pipeline=13):
    if forward<1 or reverse<1:raise ValueError('positive transport')
    # Header231=owner169+shard1+nrow16+npos3+opcode4+base30+seq8.
    # Three raw69 results per256-bit flit;49 padding, no data truncation.
    remaining=remote_rows;total=0;packets=[]
    while remaining:
        n=min(remaining,(max_flits-1)*3);payload=(n+2)//3;N=1+payload
        # One raw row collection/edge, flit send/edge, one VM row visible/edge.
        # header receive1, positive visibility fence1, registered ACK1.
        # Existing RX ACK after last out_fire; new sink withholds last fire until visible.
        duration=read_pipeline+n+N+forward+n+1+1+reverse+1
        wait_after_last_send=forward+n+1+1+reverse+1
        packets.append({'rows':n,'flits':N,'occupied_cycles':duration,
                        'ACK_wait_after_last_send':wait_after_last_send,'timeout_PASS':wait_after_last_send<timeout})
        total+=duration;remaining-=n
    return {'packets':packets,'cycles':total,'forward':forward,'reverse':reverse,
            'all_timeout_PASS':all(p['timeout_PASS'] for p in packets),
            'scope':'Constructive conservative no-overlap service screen, not measured PHY/CDC. Last RX out_fire withheld through actual VM visibility. No infinite ready/grant or ACK=visibility assumption.'}

def finite_edges(root_events,rows,positions,owner,ready_origin,native_idle):
    """Root times are supplied actual events; added path is explicit proposal.
    Local publication scalar1/edge after13 registered read/sink edges +1 visibility edge.
    Remote packet whole-phase bound is conservative, no claimed overlap.
    Credit uses2FF synchronizers + one capture each direction, arbitrary3:4 phase.
    """
    bridge=PhaseBridge(rows,positions,owner);bridge.reserve(bridge.depth,True,True);bridge.launch()
    local=[];remote=[]
    for edge,root,row in root_events:
        shard=root//64;bridge.capture(edge,owner,shard,root,row,0,0)
        (local if shard==0 else remote).append((edge,row))
    cursor=Fraction(ready_origin);local_done=cursor
    for edge,row in sorted(local):
        cursor=max(cursor,Fraction(edge+13))+1
        bridge.vm_visible(cursor,owner,0,row,True,True)
        #3 receiver (.9GHz) clocks plus3 return (1.2GHz) clocks =7stream cycles.
        bridge.credit_return(cursor+7,owner,0,row);local_done=cursor+7
    transport=packet_service(len(remote))
    remote_done=max([Fraction(ready_origin)]+[Fraction(e) for e,r in remote])+transport['cycles']+7
    for i,(edge,row) in enumerate(sorted(remote)):
        v=remote_done-7-len(remote)+i+1
        bridge.vm_visible(v,owner,0,row,True,True);bridge.credit_return(v+7,owner,0,row)
    F=max(Fraction(native_idle),local_done,remote_done)+1
    bridge.rearm(F,True,0)
    return {'phase_seats':sum(bridge.depth),'per_shard_seats':[sum(bridge.depth[:64]),sum(bridge.depth[64:])],
       'capture_count':len(bridge.records),'visible_count':len(bridge.visible),'credit_count':len(bridge.credit),
       'bank_rearm_F':int(F),'VM_addresslease_still_held':bridge.vmlease,'transport':transport,
       'native_idle':native_idle,'added_rearm_dependency_cycles':int(F)-native_idle,
       'same_enrolled_I66_relative_consumer_floor_Fplus7':int(F)+7,
       'actual_wholeprogram_criticalpath_delta':None,'prospective_service_guarantee_not_measured':True}

def allowed_read_area():
    f=json.loads((ROOT/'results/uarch/dsrom_I66_capture_cells_20261002/model.json').read_text())['source_cell_facts']
    nodes=8190;bits=nodes*96
    clock=0;n=bits
    while n>1:n=(n+7)//8;clock+=n
    reset=0;n=nodes
    while n>1:n=(n+7)//8;reset+=n
    counts={'DFFHQNx1_ASAP7_75t_R':nodes*95,'DFFASRHQNx1_ASAP7_75t_R':nodes,
      'INVx1_ASAP7_75t_R':bits+nodes,'NAND2x1_ASAP7_75t_R':nodes*69*3+bits*3,
      'BUFx4_ASAP7_75t_R':bits*(2+3)+clock+reset+nodes*12}
    areas={c:k*f[c]['SS']['area_um2'] for c,k in counts.items()}
    tie=nodes*0.04374
    return {'cell_counts':counts,'source_cell_area_um2':{c:f[c]['SS']['area_um2'] for c in counts},
      'body_um2':sum(areas.values())+tie,'at50pct_cell_reservation_mm2':(sum(areas.values())+tie)*2/1e6,
      'SETN_tie_cells':nodes,'clock_fanout8_buffers':clock,'reset_fanout8_buffers':reset,
      'select_fanout8_buffers':nodes*12,'buffer_debit_contains_distinct_feedback2_and_forward3':True,
      'clock_reset_pins_not_actual_native_escape_or_routes':True,
      'cell_construction_budget_not_mapped_fit_or_SDF_timing':True,
      'excludes':['physical stations/routes and PG/OBS','codec and16token egress FIFO full logic','owner/lease/selector control and branch fanout data','VM arbitration/all12writer guard','actual synchronizer placement/clock/reset phase relation']}

def generate():
    actual=Q.actual_certificate();root_events=[(x['edge'],x['a'],x['b']) for x in Q.rows(Q.ACTUAL) if x['kind']=='root_row_accept']
    owner=(0,0,0,10,2149580800,0,0,0,66,0)
    return {'candidate':'DS4096-TP4-S58-PAR2-NP2048','default_off':True,
      'selected_protocol':'PER_PHASE_NATIVE_ROOT_RESERVATION_AND_VISIBILITY_ANCHORED_REARM',
      'actual_phase_queue_certificate':actual,'prospective_I66':finite_edges(root_events,576,1,owner,60,421),
      'ports':{'source_roots_per_shard':64,'source_capture_record':69,'capture_max_write_ports_per_shard':64,
        'capture_local_read_ports_per_shard':1,'capture_read_pipeline_cycles':13,'capture_read_II':1,
        'VM_publication':'New opt-in interception of native scalar ROM writer-slot0. All128 native ROM writes suppressed ONLY for owned captured phase; other12 writer families veto matching leases. New arbitration/mux is priced obligation, not an existing free port.',
        'VM_writer_data':32,'VM_writer_address':30,'VM_addressable_bits':19,'VM_grant_II':1,
        'owner_context_bits':169,'physical_shard_bits':1,'packet_header_bits':231,'link_forward':330,'link_reverse':12,'duplex_tracks':684,
        'link_one_packet_credit':1,'raw_rows_per_flit':3,'raw_record_bits':69,
        'protocol_source':'ot_stage_link_tx/rx256-flit source, new header/codec/sink ownership default off'},
      'clocks_reset_gen':{'stream_period_ps':'2500/3','serial_period_ps':'10000/9','source_native_observer_single_clock':True,
        'proposed_visibility_credit_roundtrip_max_stream_edges':7,'construction':'Each crossing2 synchronizerFF plus registered captured owner token; worst3 receiving clocks incl arbitrary phase. Payload held stable in source reserved seat until captured credit. Bit bus NOT independent synchronizers.',
        'reset':'both peers quiescent, accepted phase/packet/bank debt0, resetera increased and acknowledged before GO; midphase reset faults/quarantines instead of freeing debt.',
        'generation':'Full32 retained; no reuse/wrap until all peer packets/credits and source phase debt drained. User32 never narrowed.',
        'actual_reset_phase_and_clock_skew_receipts':None},
      'capacity':'Installed single-position maximum8192 raw records (4096/shard,64/root) on each stage/rank; all charged. Reserve only per admitted nrow*(cfg_np+1), each root holds positions*root_rows; no six-position policy allocation. Native retainedI66 uses1 position; verification6 must be separately enrolled.',
      'route_selection':{'raw_homes':'R49 two shard homes are input endpoint references only. Expanded fullfield8192 capture/readpipe enclosure is UNPLACED, cannot borrow old576 home or PG/clock area; no crossdie scalar mux','publisher_home':'prospective original native tile VM owner on shard0, row/address maps unchanged','link':'existing selected stage-link candidate330/12 in65.664um duplex684 logical channel; forward/reverse1337-edge screen, not actual PHY','actual_legal_boundary_pins_and_routes':None,'actual_clock_reset_supply_join_admitted':False},
      'cost_floor':{'registered_read_allowed_cell_budget':allowed_read_area(),'existing_return_storage_recharge':0,'existing_capture_replacement_credit':0,'phase_specific_capacity_unit':B.buffer_price(576,1),'full_shape_singleposition_max_capacity':B.buffer_price(8192,1),
        'registered_read_construction':{'levels_per_shard':12,'sink_edge':1,'II_candidate':1,'capture_raw_rows_per_shard':4096,'banks_per_shard':64,'depth_per_bank':64,'source_static_seat_address':'local_root*64 + 2*(row//256)+(row&1), one position; other positions not admitted by this option','mux_tree_nodes_two_shards':8190,'registered_raw69_row16_seq10_valid1_bits':8190*96,'logical_mux_NAND2':8190*69*3,'QN_restores':8190*96,'feedback_hold_BUF_floor':8190*96*2,'forward_hold_BUF_floor':8190*96*3,'finite_publication_token_seats_per_shard':16,'egress_token_FF_bits':2*16*96,'owner_context_shared_immutable_until_all_tokens_credit_drained':True,'new_phase_blocked_until_all_read_valids_empty':True,'source_hold_repairs_are_typed_lower_bounds_not_wireclosure':True,'register_level_wire_and_control_SSFF_unqualified':True},
        'codec':{'RXheld_flit_FF':256,'TXheader_FF':231,'owner169_per_shard':338,'epoch32_per_shard':64,'two_domain_twoFF_token_synchronizers_and_capture':12,'source_TX_RX_packet_memory_bits':2*256*256,'packet_memory_at50pct_FF_reservation_mm2':2*256*256*float(B.unified_ff_um2())*2/1e6,'existing_packet_memory_debit_not_free_or_automatically_added_twice':'Must reconcile against stage-provider inherited allocation; credit0 until disjoint union. Existing packet CRC/state logic timing not qualified.', 'read_tokens_vs_phase_debt':'16 read-token seats/shard reserved before issue; read token may transfer into the charged TX packet memory. Phase raw seat/source debt remains owned through VM visibility and captured credit; packet acceptance does not release phase debt.','VM_admission_guard':'Before GO require all existing12 writer families and prior SU drain quiescent for exclusive publication port/range; block NEW conflicting unit admission through publication. Unitready is not drain. Serialization cost propagated in program; not assumed free.',
          'counter_widths_and_selector_common_context_extra':'must price typed counters/valids/fault/token/read pipeline/packetSEQ under actual cell policy before RTL'},
        'new_arithmetic_MACs_per_cycle':0,'payload_arithmetic_unchanged':True,'capture_read_pipeline_SSFF_qualified':False,'VM_mux_arbiter_route_area':None},
      'finite_parent_model_ready':True,'engine_RTL_admitted':False,'physical_fit':False,'rate_adopted':False,
      'next_gates':['Admitted pair XFIFO/segment output exact-once bounds currentLAT8; allphase return count certificate below doesnotcover pair input.','Map13-edge scalarread atII1 and visible-credit synchronizers/control under allowed cells; e899 FAILEDreadcut doesnotqualify this new construction.','Actual VMall12writer guard callbacks, packet sink visibleACK and guard exclusion lease until actualSUreadR+2.','Source clock/reset/PG/pin route and contextualSSFF; positive timing inputs are candidate promises pending these gates.','Existing stage-link packet/flit CRC source cone and body must close at actual clock or receive a separately priced multicycle schedule; II1 source service screen is not characterized clock capacity.', 'Fullprogram ordered dependency composition incl MTP6/drafter/commit/rollback; source acceptedrelativeF+7 is not an actual token latency.']}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.write_text(json.dumps(generate(),sort_keys=True,indent=2)+'\n')
