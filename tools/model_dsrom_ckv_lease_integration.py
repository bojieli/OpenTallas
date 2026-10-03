#!/usr/bin/env python3
"""Implementable full-L20 CKV lease model; functional preparation, not signoff."""
import argparse
import hashlib
import gzip
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_ckv_receive_lease_g0_20261003'
E,K,KW=16,512,10


def verify(base=BASE):
    m=json.loads((base/'source_manifest.json').read_text())
    for pin in m['origins']:
        if hashlib.sha256((base/pin['archive']).read_bytes()).hexdigest()!=pin['sha256']:
            raise ValueError('source pin mismatch: '+pin['path'])
    return m


class Publication:
    """Source-required serial write completion oracle; never a memory provider."""
    def __init__(self):
        self.sector=0; self.wait=False; self.done=False
    def request(self):
        if self.wait or self.done: raise ValueError('one outstanding write only')
        self.wait=True
        return self.sector
    def complete(self):
        if not self.wait: raise ValueError('unowned completion')
        self.wait=False; self.sector+=1; self.done=self.sector==9


class Ownership:
    def __init__(self):
        self.epoch=0; self.active=False; self.rows={}; self.started=0; self.retired=0
        self.stream_done=False; self.pending=set(); self.pub=Publication()
    def select(self,reset_drained, routes_drained):
        if self.active or not reset_drained or not routes_drained:
            raise ValueError('selection not ready')
        self.epoch=(self.epoch+1)%2**E
        self.active=True; self.rows={}; self.started=self.retired=0
        self.stream_done=False; self.pending=set(); self.pub=Publication()
    def receive(self,epoch,rank,gid,expected_gid,payload,owner,expected_owner):
        if (not self.active or epoch!=self.epoch or not 0<=rank<K or
                gid!=expected_gid or owner!=expected_owner or rank in self.rows):
            raise ValueError('receive not accepted; must not write or count')
        self.rows[rank]=payload
    def reserve_broadcast(self,rank):
        for dst in range(3):
            token=(self.epoch,rank,dst)
            if token in self.pending: raise ValueError('duplicate broadcast')
            self.pending.add(token)
    def ack(self,epoch,rank,dst):
        token=(epoch,rank,dst)
        if token not in self.pending: raise ValueError('stale or duplicate stored ACK')
        self.pending.remove(token)
    def start(self,is_pv):
        if not self.active or self.started!=self.retired or self.started>=2 or bool(is_pv)!=bool(self.started):
            raise ValueError('QK then PV only, no premature reuse')
        self.started+=1
    def emit_done(self): self.stream_done=True
    def retire(self,actual_desc_done, engine_idle):
        if not actual_desc_done or not engine_idle or not self.stream_done or self.started!=self.retired+1:
            raise ValueError('actual final descriptor/output retirement required')
        self.retired+=1; self.stream_done=False
    def close(self,routes_drained):
        if self.retired!=2 or len(self.rows)!=K or self.pending or not self.pub.done or not routes_drained:
            raise ValueError('immutable row lease still owned')
        self.active=False


class GroupGrant:
    """Latch old-epoch barrier BEFORE any of four callers enters next selection.

    New-generation activity cannot revoke permission from a slower fourth caller.
    """
    def __init__(self):self.epoch=0;self.permits=set()
    def open(self,all_old_leases_closed,old_routes_drained,reset_drained):
        if self.permits or not all_old_leases_closed or not old_routes_drained or not reset_drained:
            raise ValueError('all4 old-generation barrier required')
        self.epoch=(self.epoch+1)%2**E;self.permits=set(range(4))
    def accept(self,rank):
        if rank not in self.permits:raise ValueError('selection permit missing/duplicate')
        self.permits.remove(rank)
        return self.epoch


def build(base=BASE):
    manifest=verify(base)
    def read(p):return (base/'inputs'/p).read_text()
    outer=read('rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv')
    inner=read('rtl/chip/ot_chip_v41x_kv_reqmux.sv')
    hbm=read('rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv')
    if '!c_we[s]' not in outer or "assign c_wr_done[s] = 1'b0" not in inner or "wr_done[p] <= 1'b1" not in hbm:
        raise ValueError('publication source contract changed')
    state=dict(selection_epoch=E, lease_live=1, passes_started=2, passes_retired=2,
               stream_retire_pending=1, publication_done=1, writer_wait=1,
               reset_release_latch=1, remote_stored_ACK_registers=3*(1+E+KW),
               source_destination_ACK_pending=3*K,
               mux_write_outstanding=4,mux_write_owner=4,mux_fair_turn=4,
               core_issue_ready_capture=1,own_capture_lock=1)
    bits=sum(state.values())
    # Conservatively construct generic mux/equality/decoders from allowed AND2/INV.
    # These prices are source-library areas, not a mapped netlist or timing result.
    def cell(file,master):
        raw=(base/'inputs/library'/file).read_bytes()
        text=(gzip.decompress(raw) if file.endswith('.gz') else raw).decode()
        marker='cell ('+master+')';start=text.index(marker);end=text.find('cell (',start+len(marker))
        block=text[start:] if end<0 else text[start:end]
        area=float(re.search(r'area\s*:\s*([0-9.eE+-]+)',block).group(1))
        cap=None
        if 'pin (CLK)' in block:
            cap=float(re.search(r'\bcapacitance\s*:\s*([0-9.eE+-]+)',block[block.index('pin (CLK)'):]).group(1))
        return area,cap
    and_area,_=cell('asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz','AND2x2_ASAP7_75t_R')
    inv_area,_=cell('asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','INVx1_ASAP7_75t_R')
    ff_area,sscap=cell('asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib','DFFASRHQNx1_ASAP7_75t_R')
    _,ffcap=cell('asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib','DFFASRHQNx1_ASAP7_75t_R')
    buf_area,_=cell('asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','BUFx4_ASAP7_75t_R')
    mux_area=3*and_area+4*inv_area
    xnor_area=4*and_area+5*inv_area
    logic=dict(all_state_hold_muxes=bits,ACK_pending_read_muxes=3*(K-1),
               TX_and_3_ACK_rank_decode_AND2=4*K*(KW-1),
               generation_RX_ACK_XNOR=6*E,owner_RX_XNOR=3*2,
               pending_zero_tree_AND2=3*K-1,qualifier_guard_AND2=256)
    area=bits*ff_area+(bits+logic['ACK_pending_read_muxes'])*mux_area
    area+=logic['TX_and_3_ACK_rank_decode_AND2']*and_area
    area+=(logic['generation_RX_ACK_XNOR']+logic['owner_RX_XNOR'])*xnor_area
    area+=(logic['pending_zero_tree_AND2']+logic['qualifier_guard_AND2'])*and_area
    # Two-register synchronizer screen and explicit reset/hold terminals for ALL new state.
    terminals=bits*(inv_area+and_area)
    clock_buffers=sum((bits+10**n-1)//10**n for n in range(1,5))
    clock_area=clock_buffers*buf_area
    slot=2*(area+terminals+clock_area)
    shared_bits=E+4+1
    shared_slot=2*(shared_bits*(ff_area+mux_area+inv_area+and_area)+3*buf_area)
    forward=E+1; reverse=1+E+KW+1
    cdc_row=2304+31+E
    cdc_ack=1+E+KW
    async_bits=12*(2*cdc_row+2*cdc_ack)+24*(12+4)
    assumptions=[]
    for grant,visible,forward_bound,reverse_bound,consumer_stall in [(2,32,11,11,0),(8,260,142,142,64),(32,1024,1024,1024,4096)]:
        # Explicit assumptions, not asserted product service rates.
        publication=9*(grant+visible+1)
        fetch=512*(9*(grant+visible)+8)
        peer=512*2+forward_bound+reverse_bound+3
        two_pass=2*(193+consumer_stall+2)
        assumptions.append(dict(source_bound=False,grant_gap=grant,write_or_read_sector_completion_bound=visible,
                                forward_bound=forward_bound,reverse_bound=reverse_bound,
                                aggregate_consumer_stall_per_pass=consumer_stall,
                                publication_cycles=publication,owned512_single_stack_fetch_cycles=fetch,
                                peer_cycles=peer,selected_two_pass_cycles=two_pass,
                                serialized_selection_to_release_cycles=32+5+publication+fetch+peer+two_pass,
                                meaning='conditional screen, no overlap credit, engine output/compute and field delivery bounds still additional'))
    h4=json.loads((base/'inputs/russell/cost-inputs.json').read_text())
    if h4['sidecar_source_metadata_bits']!=92 or h4['pipeline_two_seats_38stages_144lanes_increment_bits']!=1575936:
        raise ValueError('frozen H4 lossless ABI/cost changed')
    return dict(schema='dsrom_ckv_fullparent_lease_g0/1',status='SIZED_SOURCE_SELECTED_FUNCTIONAL_SUCCESSOR_PREPARATION_PHYSICAL_OPEN',
      source_commit=manifest['frozen_main_commit'],full_L20_source_files=manifest['full_L20_source_files'],
      target=dict(designs=dict(DS_ROM='full K512 TP4 selected CKV owner',DS_HBM='GPU path unchanged',Qwen_ROM='not this service',Qwen_HBM='not this service'),
                  K=K,D=512,TROWS=640,NL=4,H=16,TD=32,NSLOT=64,selection_epoch_bits=E,
                  CKV_RX_LEASE_default=0,clock_ps=833,SS_setup_uncertainty_ps=60,FF_hold_uncertainty_ps=25),
      source_providers=dict(selection='fastpp_pc21/l20 core S_ISSUE gates selected KVT gather by service sel_ready BEFORE pulsing su_go; ckv_sel_v only resulting accepted pulse',
                            own_capture='QDQ4E mode3 CKV production in hdc_replay_v41; gate next production while old lease owns nw_gid/new_row, capture complete before selection',
                            ID_VM='service32 512-bit VM reads; forbid concurrent collective xb reads via core collective admission while service vm_busy',
                            replay='die window_source_start starts service job; latch QK/PV from accepted descriptor ks, not mutable later decoded fields',
                            staging='actual runtime adapter packed_kv_ready and engine kv_go/wr_addr=wptr/4, both640-row descriptors unchanged',
                            retire='att_packed_desc_done && att_packed_idle; idle includes !(|o_we) after A_WR, not merger job_done',
                            publication='HBM idx_hbm masked memory write precedes wr_done; arbiter tracks actual write owner; add CKV writer mux route, one outstanding write per stack',
                            peer='selection epoch16 rides TX, every forward route, RX, registered stored ACK and reverse route; all4 forward/reverse drain before selection/wrap/reset reuse',
                            group_barrier='one shared group controller latches four selection permits and next epoch after all4 OLD leases/routes retire; slower caller retains its permit even when an early caller starts new work'),
      incremental=dict(existing_payload_bits_charged_again=0,existing_staging_bits_charged_again=0,
                       state_bits_per_die=state,total_state_bits_per_die=bits,all4_state_bits=4*bits,
                       combinational_gate_screen=logic,FF_area_um2=bits*ff_area,logic_and_state_area_um2=round(area,6),
                       terminal_reset_hold_area_um2=round(terminals,6),clock_buffer_screen_count=clock_buffers,
                       clock_buffer_screen_area_um2=round(clock_area,6),new_ASR_clock_pin_load_SS_fF=bits*sscap,new_ASR_clock_pin_load_FF_fF=bits*ffcap,
                       requested_50pct_incremental_slot_um2_per_die=round(slot,6),all4_slot_um2=round(4*slot,6),
                       shared_group_controller_bits=shared_bits,shared_group_controller_slot_um2=round(shared_slot,6),
                       full4_joined_incremental_slot_um2=round(4*slot+shared_slot,6),
                       no_mapped_timing_credit=True,slot_site_assignment=None,
                       screen_basis='AND2x2/INVx1/DFFASRHQNx1 .37908 source-library gross bill, 50% util; all new state conservatively ASR. Generic gates unoptimized, source mapper proof pending. BUFx4 source area screen; actual clock/hold/PG union unqualified'),
      boundaries=dict(MACs_per_cycle=0,flow='existing 2304bit row and rank10/GID21 retained; no new arithmetic',
                      per_directed_route_added_forward_bits=forward,per_directed_route_added_reverse_bits=reverse,
                      all12_routes_incremental_signal_track_floor=12*(forward+reverse),
                      peer_accept_max_rows_per_die_edge=3,stored_ACK_register_max_rows_per_die_two_edges=3,
                      ACK_register_reuse='no same-edge ACK-buffer credit reuse; at least2 edges/source when reverse ready1',
                      local_fetch_payload_bytes_edge=288,remote_payload_bytes_edge=864,
                      replay_bytes_edge=1152,staging_bytes_edge=2120,
                      new_data_buffer_bytes=0,port_capacity_tracks=None,
                      fanout='epoch16 ->3RX +3ACK compares; active ->5 write qualifiers; sel_ready/nw_ready ->one core issue; pending-zero reduction1536 inputs; no direct new reset on old payload arrays'),
      CDC=dict(current_functional_join='all four model endpoints share source clk; no crossing on this source functional gate',
               no_hardware_same_clock_credit=True,
               required_if_independent_clocks=dict(fullrow_forward_two_entry_FIFO_routes=12,reverse_two_entry_FIFO_routes=12,
                    row_width=cdc_row,ACK_width=cdc_ack,total_added_state_bits=async_bits,
                    FF_only_area_um2=round(async_bits*ff_area,6),FF_only_50pct_slot_um2=round(2*async_bits*ff_area,6),
                    omitted_from_nominal='added only when crossing instantiated; storage ports/serializer/mux/clock/PG more, no embedded-memory credit',
                    latency='two destination-clock sync stages plus FIFO/serializer per direction; actual clock ratio/reset/hop bounds required')),
      frozen_H4_connector=dict(commit='1bfbbda5afeafde216ab5c6d79dd3b72efaa2800',consumed_exact_portbook=True,
                    relationship='GPU HBM connector is NOT current CKV L20 idx_hbm backing path. No seventh client, R14/W2 substitution or RF assembler installed by this plan.',
                    no_free_shared_transport_credit=True,existing_clients=6,new_seventh_client_admitted=False,
                    required_if_backing_replaced=dict(child_owner_bits=46,parent_capture_bits=55,parent_reference_bits=32,
                        source_meta_bits=92,backend_token_bits=16,source_generation_bits=4,backend_generation_bits=4,
                        forbid_truncating_high4=True,stable_parent='pre-bound parent55, never reconstructed from last child',
                        R14_bypasses_W2_currently=True,required_lifetime='physical child quarantine through logical held completion, full16sector RF frame/commonACK, visibility, consumer/reverse and both CDC drains',
                        protected_pipeline_increment_bits=h4['pipeline_two_seats_38stages_144lanes_increment_bits'],
                        sidecar_physical_macro_capacity_bits=128*128*256,sidecar_logical_bits=h4['full_context_sidecar_raw96bits_per_die'],
                        RF_new_assembly_data_bits=131072,RF_new_sector_masks=512,RF_existing_macro_area_recharge=False,
                        exact_codec_and_partial_join_required=True,source_owner_client_SM_allocator=None,
                        admission='REFUSE connector replacement until explicit child/client/SM/parent allocation, lossless16 echo, quarantine, reverse and RF frame/codec gates; these costs not silently included in nominal CKV control subtotal')),
      prospective_bounds=dict(consumer_stall_source_proved=False,worst_unrestricted_stall_cycles=None,
                    publication='9*(Gwrite+Vwrite+1); no nine-sector request-accept shortcut',
                    fetch='conservative512*(9*(Gread+Vread)+8), all ownership on one stack, no overlap credit',
                    peer='512*max(forward row admission interval,2 ACK buffer interval)+F+A+3; actual route reservation must bound interval',
                    replay='2*(193+Sqkv+2)+actual engine compute/output drain; no trace inferred from offered beats',
                    full_token_delta_cycles=None,full_token_formula='sum these dependent service costs at each actual selected-CKV call from pinned program calendar, only proven independent work overlaps',
                    sensitivity_assumptions=assumptions,mandatory_exactness_not_optional_1pct_lever=True),
      correctness=dict(storage='512 immutable seats; QK does not return row credit, neither accepted staging write nor merge_done releases lease',
                    receive='id_done&&lease_live&&epoch match&&rank<512&&GID/table/owner match&&!present&&ACK seat free; writes/counts only accepted unique rows',
                    atomic_clear='selection acceptance dominates all writes/counts and cannot coexist RX; old read/peer/publication/consumer ownership drained',
                    grant='shared old-generation barrier latched once; each of four core issue gates consumes its own permit and installs the supplied epoch, avoiding admission deadlock from new traffic at faster ranks',
                    broadcast='atomic3-destination acceptance, source TX handshake and local write on same edge; ready qualified by seats without ready/valid combinational loop',
                    invalid='stale/duplicate/in-range wrong-ID may set fault but never mutate payload/present/count; no expectation weakening',
                    ACK='registered only after actual row store; accept only active generation pending rank/destination; duplicates/stale never clear unrelated pending bit',
                    completion='start QK then PV exactly once each, retain512 rows until both actual descriptor/output retires + all peer ACKs/drain + all9 writes complete',
                    reset='all endpoint resets/queues/CDC acknowledge drain before initial selection or epoch reuse; no timeout treated as success'),
      source_successor_plan=dict(component_functional_RTL_writing_allowed=True,HDL_build_allowed=False,physical_admitted=False,
                    implementation='added namespace copies of service, core, tile, die, runtime wrapper, kv/rope mux + explicit full4 peer route join; one mandatory fix, default0',
                    reuse='original row encoder/fetch/DMA/merge and attention arithmetic exactbytes, existing buffer geometry unchanged',
                    mapped_backend='source read-only/static first; no build until source-package review and fresh GO',
                    full_gate='4 full512 services + actual full attention adapter/staging640 and real core caller/descriptor; immutable raw row/ID inputs, expected only assertions',
                    row_checks_per_legal_pass_pair=4096,
                    cases=['clear plus RX','stale prior selection same rank/GID','duplicate same edge/source','in-range wrong GID/owner no write',
                           'all512resident whileQKstall','QKretired PVstall no reuse','final packed beat vs final actual engine output',
                           'nine actual writes, last completion absent','ACKbackpressure/stale/duplicate','reset queued peer/ACK','wrap with old pending must refuse'],
                    mutants=['omit epoch compare','count offered instead accepted','write despite wrong ID','retire on merge_done','release write on ready instead done'],
                    prior_failures='6675 immutable archive retained; writepath parent blocker retained unchanged',
                    admission_remaining='named physical slot/route/CDC allocation and actual finite calendar/observer measurement are required for physical/fulltoken adoption, not for source-sized functional RTL preparation'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    with a.out.open('x') as f:json.dump(build(),f,indent=2);f.write('\n')
