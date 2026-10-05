#!/usr/bin/env python3
"""Source-pinned receive/lease sizing. No HDL, transport or timing qualification."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_ckv_receive_credit_model_20261003'
K, ROW, GROUP_ROW, LANES = 512, 2304, 16 * 265, 4


def verify_inputs(base=BASE):
    origins = json.loads((base / 'origins.json').read_text())
    for pin in origins['origins']:
        raw = (base / pin['archive']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('archived source changed: ' + pin['path'])
    return origins


class Lease:
    """Independent proposed contract oracle; NOT installed RTL or a transport provider."""
    def __init__(self, gids, epoch=0):
        if len(gids) != K or any(a >= b for a, b in zip(gids, gids[1:])):
            raise ValueError('512 strictly increasing IDs required')
        self.gids = list(gids)
        self.epoch = epoch
        self.rows = {}
        self.phase = 0
        self.cursor = 0
        self.retired = 0

    def accept(self, epoch, rank, gid, payload):
        if (epoch != self.epoch or not 0 <= rank < K or
                gid != self.gids[rank] or rank in self.rows):
            raise ValueError('unowned/stale/duplicate row')
        self.rows[rank] = payload

    def take(self, ready, count=LANES):
        if not ready:
            return []
        if self.phase >= 2:
            raise ValueError('extra descriptor')
        end = self.cursor
        while end < min(self.cursor + count, K) and end in self.rows:
            end += 1
        values = [(i, self.rows[i]) for i in range(self.cursor, end)]
        self.cursor = end
        return values

    def retire_descriptor(self, engine_idle):
        if self.cursor != K or not engine_idle:
            raise ValueError('merger completion is not engine retirement')
        self.retired += 1
        self.phase += 1
        self.cursor = 0

    def release(self, peer_and_reverse_drained, visible_sectors):
        if self.retired != 2 or not peer_and_reverse_drained or visible_sectors != set(range(9)):
            raise ValueError('lease/final consumer/publication not drained')


def merger_control_calendar():
    """Literal two-buffer nonblocking control transcription, all rows present/ready1.

    Edges counted from first logical intake, excluding job-start/caller/window.
    This is a static control calculation, NOT an actual RTL runtime trace.
    """
    full, rdy = [False, False], [False, False]
    f = o = next_row = edge = 0
    cq, cq_b = False, 0
    accepted, emitted = [], []
    while True:
        emit = rdy[o]
        take = 4 if not full[f] and next_row < K else 0
        done = emit and next_row == K and not full[1-o]
        nf, nr = list(full), list(rdy)
        if cq:
            nr[cq_b] = True
        if emit:
            nr[o] = nf[o] = False
            emitted.append(edge)
        if take:
            nf[f] = True
            accepted.append(edge)
        cq, cq_b = bool(take), f
        next_row += take
        if take:
            f = 1-f
        if emit:
            o = 1-o
        full, rdy = nf, nr
        edge += 1
        if done:
            return dict(edges_first_intake_through_final_emit=edge, intake_edges=accepted,
                        emit_edges=emitted, interpretation='static source control only; caller/window/stalls/engine drain excluded')


def build(base=BASE):
    origins = verify_inputs(base)
    def source(path):
        return (base / 'inputs' / path).read_text()
    service = source('rtl/chip/ot_chip_v41x_ckv_die_service.sv')
    die = source('rtl/chip/ckvsel/ot_chip_v41x_die.sv')
    merge = source('rtl/chip/ot_chip_v41x_ckv_stream_merge.sv')
    host = source('rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp')
    current_inventory = source('tools/w17_current_fastpp_l20_sources.txt').split()
    if ('rtl/chip/ot_chip_v41x_ckv_die_service.sv' not in current_inventory or
            any('ckv_count_clear' in p for p in current_inventory)):
        raise ValueError('current runtime service binding changed')
    core = source('rtl/w17_runtime/hdc/v41x/fastpp_pc21/l20/ot_hdc_core_v41x.sv')
    if 'assign ckv_sel_v = ckv_issue && dst == 2\'d3' not in core:
        raise ValueError('current selection caller changed')
    # Refuse accidental rebinding to a different handshake or a repaired service.
    for literal in ['if (sel_v && !rd_act)', 'npresent <= npresent + (KW+1)\'(nwr)',
                    'if (wv[i] && wrank[i*KW +: KW] < KW\'(K))', 'assign c_srdy[st] = 1\'b1']:
        if literal not in service:
            raise ValueError('service equation changed')
    if 'ag_rx_ready' in service or '.K(512)' not in die or 'wire open_ = run && !full[f]' not in merge:
        raise ValueError('receive/geometry/merger binding changed')
    if 'd->ckv_ag_tx_ready = 1' not in host or 'q.pop_front();' not in host:
        raise ValueError('host delivery contract changed')
    historical = json.loads((base / 'inputs/historical_ckv_b93_r1.json').read_text())
    core_storage = dict(collector_payload=K*ROW, collector_present=K,
                        selection_ID_table=K*21, owned_rank_gid_list=K*(10+21),
                        merger_output_two_beats=2*LANES*GROUP_ROW,
                        merger_input_CKV_register=LANES*ROW,
                        attention_staging=640*GROUP_ROW,
                        fetch_slot_payload_lower_bound=64*ROW,
                        fetch_output_payload=ROW, own_capture=8192, own_encoded_row=ROW)
    total = sum(core_storage.values())
    uarch = source('tools/uarch_model.py')
    if 'DFF_UM2 = 0.2916' not in uarch:
        raise ValueError('unified FF area basis changed')
    # Full K is a capacity bound, not a chosen finite stall/throughput promise.
    return dict(schema='dsrom_ckv_receive_credit/1', status='SOURCE_BOUND_MODEL_RECEIVE_OWNERSHIP_GAP_NO_RTL_ADMISSION',
        frozen_main_commit=origins['frozen_main_commit'], archived_input_count=len(origins['origins']),
        scope=dict(target='DS ROM full selected-KV K512, D512, TP4; QK then PV per rank',
                   Qwen_ROM='not a selected-CKV service; no price transfer', Qwen_HBM='not applicable',
                   DS_HBM='GPU organisation retained; this ROM die path not adopted',
                   RTL_changed=False, launch_allowed=False, installed_binary_binding='UNPROVEN',
                   full_die_qualification=False, physical_qualification=False),
        bindings=dict(source_inventory='tools/w17_current_fastpp_l20_sources.txt names original service, CKV die/tile, fastpp_pc21/l20 core, runtime adapter; historical w11 and PC21 inventories also archived',
                      instantiated_service='rtl/chip/ot_chip_v41x_ckv_die_service.sv, K512 NSLOT64 in g_ckv',
                      unused_standalone_collector='ot_chip_v41x_ckv_sel_collect is not instantiated by this service',
                      die_default='CKV_SELECTED=0; L20 wrapper sets1/FULL_SHAPE1/X_ATT1',
                      adapter='V41_ATT_CUT uses att_from.kv_ready; else same-clock full attention engine',
                      engine_defaults=dict(TROWS=640, D=512, H=16, NL=4, TD=32, ILV=0, NSTAGE=1, SRAM_MACRO=0),
                      installed_link_map=None, Hubble_frozen_build_source_equivalence=None),
        equations=dict(TX_accept='f_ov && ag_tx_ready; same handshake writes local row',
                       RX_write='ag_rx_valid[i] && rank<K; no ready/epoch/step/go/id_done qualification',
                       RX_fault='duplicate/present, range or gid mismatch; in-range faulty row STILL writes buf_row/present',
                       RX_count='nwr counts offered valid sources, including rejected/out-of-range/duplicates; rows_ready=npresent==512',
                       clear='sel_v&&!rd_act clears present and rel_on; later unconditional npresent update overrides clear (NBA priority)',
                       selection_caller='current fastpp_pc21/l20: ckv_issue=su_go&&ckv_su_match, sel_v=ckv_issue&&dst3; scalar unit ready, no service selection ready input',
                       release='rel_on and consecutive present ranks offer up to4; rel advances only by c_take',
                       merge='c_take only while run&&!full[f]; two full beats stop intake even if kv_ready stays0',
                       packed_accept='svc_kv_v && ckv_ph && tile_packed_ready',
                       tile_ready='PACKED_KV && adapter A_RUN && adapter kv_v && engine kv_ready',
                       staging_write='kv_stream_v&&engine kv_ready, wr_en=mask, wr_addr=wptr/4',
                       merge_done='last beat accepted; NOT attention arithmetic/output retirement',
                       descriptor_done='actual lifecycle DRAIN then engine_idle; wrap_drained currently window predicate, not CKV peer ACKs',
                       owner_write='9 requests; wr_act clears on c_rdy of sector8; c_wr_done is an input but unused by service'),
        historical=dict(service_gate=historical['status'], runs=[dict(rows_checked=r['rows_checked'], cycles=r['fields']['cycles']) for r in historical['runs']],
                        limitation='all4x512 rows twice, kv_ready tied1, behavioural links; not installed full die/CDC/physical',
                        preserved_failures=['original clear count override', 'same rank/gid delayed old row stores with fault0 after count-only fix',
                                            'permanent output stall refuses finite drain', 'engine not retired refuses drain'],
                        historical_retained_engine='metadata record says current source revision mismatch and original binary linkage unproven'),
        occupancy=dict(max_unique_rows_per_rank=K, payload_bytes_per_rank=K*ROW//8,
                       all4_rank_payload_bytes=4*K*ROW//8, phases=2,
                       lifetime='selection IDs/rows immutable from accepted selection through both replay descriptors, engine final drain, peer/hop/reverse drain and9 visible writes',
                       QK_PV_additional_collector_buffers=0,
                       worst_stall_cycles=None, stall_reason='ready/score/probability/output credits may stay0 without a source-proved bound',
                       safe_single_epoch='all512 unique ranks can arrive with zero downstream drain without overflow; present persists for PV',
                       no_alias='collector and 640-row expanded engine staging coexist; QK/PV replay is not a destructive pop/free',
                       merger_full_stall_rows=8, slots_not_freed_by_merge=True,
                       mutable_row_risk='no epoch/selection ready/barrier; reselection/late peers can change rows during replay'),
        ports=dict(MACs_per_cycle=0, operation='transport/reformat only; engine arithmetic unchanged',
                   remote_payload_bits_per_edge=3*ROW, remote_payload_bytes_per_edge=3*ROW//8,
                   remote_tag_bits_per_edge=3*31, remote_valid_bits=3,
                   local_payload_bits_per_edge=ROW, normal_combined_payload_bits=4*ROW,
                   own_insert_extra_payload_bits=ROW, peak_service_write_sources=5,
                   replay_read_payload_bits=4*ROW, expanded_stage_write_bits=4*GROUP_ROW,
                   expanded_stage_bytes_per_edge=4*GROUP_ROW//8,
                   ID_VM_read_bits=512, ID_VM_beats=32, HBM_payload_bits=4*256,
                   physical_multiwrite='5 arbitrary rank writes; requires steering/arbitration or multiport FF ledger, not four lane SRAM credit',
                   read_muxes='4 K512 x2304 selects; ID validation5 K512x21 ports; not free SRAM ports',
                   route_track_lower_bounds=dict(remote_payload_and_tags_and_valid=3*(ROW+31+1), replay_payload=4*ROW,
                                                 packed_beat_and_mask_valid_ready=4*GROUP_ROW+6),
                   channel_capacity=None, root_replicas=4, peer_directed_routes=12, fanout='one TX row copied to3 destinations; 512present bits into contiguous-rank release'),
        storage_area=dict(existing_declared_live_bits_by_instance=core_storage, subset_gross_bits_per_rank=total,
                          constant_window_register_bits_not_charged=LANES*4224,
                          basis='unified tools/uarch_model.py DFF_UM2=.2916 gross screening only; excludes tied-zero window input register and other DMA/encoder/control state; CKV format constant-bit optimization not credited. NOT mapped-area lower bound',
                          FF_screen_um2_per_rank=round(total*.2916,6), FF_screen_um2_all4=round(4*total*.2916,6),
                          screen_50pct_slot_um2_per_rank=round(2*total*.2916,6),
                          macro_credit=0, actual_library_mapping=None, actual_slot=None,
                          proposed_control='existing512present seats reused; no new row buffers. Generation E, active/lease flags, two-pass retirement,9 visible-write scoreboard and1536 per-copy stored/reverse-ACK bits/source',
                          proposed_control_bits_formula='E + 1(active) + 2(retired count) + 9(visible sectors) +1536(copy ACK) = E+1548 per rank; interface/check pipeline/CDC state additional, unpriced',
                          proposed_control_FF_screen_um2_formula='.2916*(E+1548); no numeric E chosen without no-wrap/reset contract',
                          proposed_receive_checker_logic='3*(E+10+21+2) compare widths; at most10 pairwise rank comparisons among5sources; arbitration5x512 write seats; actual synthesis/placement unknown',
                          added_wire_formula='RX3*(E+ready1)+3storedACK*(E+rank10+status1+valid1)+ACK reverse routing/framing; endpoints source/destination2bits each if not implicit',
                          context_fit=False),
        CDC=dict(local_service_merge_staging='same clk/rn in uncut source; external ATT_CUT actual shared clock binding required',
                 host_transport='std::deque[4][4], TX ready=1, scheduled RX then pop regardless acceptance; not hardware CDC or credits',
                 physical_link_clocks=None, synchronizers_or_async_FIFO_cost=None, reset_old_queue_drain=None),
        latency=dict(accept_beats_per_descriptor=128, full_window_plus_selected_beats=160,
                     selected_replay_beats_QK_PV=256, all4_parallel_not_serial=1024,
                     minimum_data_transfer_ns_at_833ps=256*.833,
                     ready1_all_present_selected_control_calendar=merger_control_calendar(),
                     interpretation='transfer lower bound only; no rate/latency qualification. Two-buffer bubbles, startup, row holes, all stalls, arithmetic and retirement added',
                     merge_residency='logical accept t, B write t+1, offered t+2; no same-edge freed-buffer reuse',
                     full_token_added_cycles=None, composed_bound='sum actual per-pass accepted edges + stalls + engine output drain + route/reverse drain + visible writes, respecting caller order',
                     nine_sector_owner_publication_overlap=False),
        successor_contract=dict(default_off=True, name='CKV_RX_LEASE (proposed, not RTL)',
                                no_larger_FIFO=True, selection_accept='new sel_ready requires closed old lease, all4 peer stored/hop/reverse drain,9visible writes, actual final engine/output retirement; table clear atomic before ready',
                                receive_accept='valid&&ready&&matching epoch&&table complete&&expected rank/gid/source owner&&unique reserved seat; only accept writes/counts; faulty inputs never mutate',
                                stored_ACK='registered after actual row write, not TX launch or queue departure; no credit reuse before retained-row lease closes',
                                stalled_offer='hold rank/gid/epoch/payload until ready; host dequeue only on accept',
                                reset='must invalidate/drain all old forward/reverse queues before accepting generation reuse',
                                epoch_width=None, numerical_order='unchanged window then selected ascending rank; QK/PV stored FP4 codes/scales unchanged'),
        required_admission=['Hubble actual installed source/binary manifest and accepted RX/packed/staging/output trace',
                            'Maxwell actual field boundary seat ownership, forward/reverse route reservation and CDC/reset',
                            'caller sel_v converted to actual accepted selection handshake, engine drain +9visible WR authority',
                            'generation/no-wrap proof and full control/wire/clock/PG/area slot in unified composition',
                            'finite consumer/calendar stall bound or explicit unbounded-liveness classification'],
        gate_plan=dict(state='PREPARE_ONLY_NOT_HDL_EXECUTABLE', geometry='4 ranks, service K512 NSLOT64, mixed staging640 D512 H16 NL4 TD32, original actual caller adapter',
                       inputs='immutable synthetic packed ROM/HBM rows and IDs ONLY; expected rows/assertions independent, never injected into datapath',
                       assertions='each rank512 QK +512 PV =4096 selected-row equality checks plus exact accepts/counts/stage addresses/held beats/fault/reset/ACKs/final engine retirement',
                       cases=['full512 arbitrary arrival permutation, one missing earliest rank, full all512 resident with downstream0',
                              'stall A/B completion, middle beat and last beat; then actual consumption/engine drain',
                              'new selection while replay, clear plusRX, delayed previous epoch same rank/gid',
                              'duplicate same-edge sources, bad ID/owner, ranks512/1023, extra ACK/duplicate ACK',
                              'QK complete PV stalled, ninth visible write missing, engine output stalled, reset with peer queued'],
                       mutants=['remove epoch compare must stale-row DIFF', 'count offered instead of accepted must count DIFF',
                                'free seat at QK take must PV payload DIFF', 'retire on merge_done must engine-drain DIFF'],
                       diagnostics='preserve unchanged original negative witnesses separately; no retroactive PASS',
                       run_resources='no launch now; owner-reviewed measured host lease, no duplicate CKV job, no PVE2/3; source-bound command and GO required'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    result = build()
    with args.out.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')
    print(result['status'])
