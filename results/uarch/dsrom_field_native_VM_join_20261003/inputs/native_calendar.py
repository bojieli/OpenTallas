#!/usr/bin/env python3
"""Finite source-ordered DS VM frame calendar. Analytical model, not engine RTL.

A sealed frame is a retained logical edge. All reads complete before any frame
write issues. One native consecutive-four-word read port and four bank writes
are modeled; this is not a 1520-port SRAM. Each accepted frame reserves all reply
and retirement seats. Consumer stalls cannot stop its backend completion.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_finite_vm_calendar_20261003'
READ_CAP, WRITE_CAP, CONTEXT = 1520, 593, 169


def inputs():
    rows = json.loads((BASE / 'inputs/origins.json').read_text())
    for r in rows:
        if hashlib.sha256((BASE / 'inputs' / r['copy']).read_bytes()).hexdigest() != r['sha256']:
            raise ValueError('Source drift: ' + r['copy'])
    return rows


def reference():
    inputs()
    p = BASE / 'inputs/4_dsrom_split_vm_order_model.py'
    spec = importlib.util.spec_from_file_location('pinned_vm_order', p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def word_home(address):
    if type(address) is not int or not 0 <= address < (1 << 19):
        raise ValueError('Expanded FP32 address outside AW19')
    word = address >> 4
    return dict(word=word, bank=word & 3, group=word >> 11,
                row=(word >> 2) & 511, lane=address & 15)


def native_read_base(word):
    # Align to four words, avoiding upper-bound over-read of the retained port.
    return word & ~3


def resolve_winners(writes):
    """One compare per edge during frame fill; literal last-write-wins."""
    flags = [True] * len(writes)
    comparisons = 0
    for i, (_, address, _) in enumerate(writes):
        for j in range(i):
            comparisons += 1
            if writes[j][1] == address:
                flags[j] = False
    return flags, comparisons


def calendar(memory, reads, writes, epoch=0):
    """Reference execution and exact finite issue/visible events for one frame.

    Input writes are literal retained source NBA order. Storage values are
    unsigned raw FP32 bits; no arithmetic performed. Superseded receipt is not
    a visibility ACK. IDs remain one-to-one even for same-address read fanout.
    """
    reads, writes = tuple(reads), tuple(writes)
    if type(epoch) is not int or not 0 <= epoch < (1 << 32):
        raise ValueError('Epoch outside uint32')
    if len(reads) > READ_CAP or len(writes) > WRITE_CAP:
        raise ValueError('Frame seat capacity exceeded; reject before acceptance')
    for _, _, v in writes:
        if type(v) is not int or not 0 <= v < (1 << 32):
            raise ValueError('Write is not raw FP32 bits')
    replies, image, status = reference().ordered_edge(memory, reads, writes)
    read_events = []
    for cycle, (rid, address) in enumerate(reads):
        h = word_home(address)
        read_events.append(dict(id=rid, epoch=epoch, address=address,
                                base_word=native_read_base(h['word']),
                                select_bank=h['bank'], select_lane=h['lane'],
                                issue=cycle, reply_capture=cycle + 4))
    # Conservative barrier: drain the entire last read before first write.
    write_start = len(reads) + 4 if reads else 0
    flags, comparisons = resolve_winners(writes)
    write_events = []
    # Selected finite implementation: scan source-order entries one per edge.
    # No unpriced associative word gather or four arbitrary-bank dispatch.
    for i, (rid, address, value) in enumerate(writes):
        if not flags[i]:
            continue
        h = word_home(address)
        issue = write_start + i
        write_events.append(dict(word=h['word'], bank=h['bank'],
                                 lane_mask=1 << h['lane'], lanes={h['lane']: value},
                                 owners=[rid], epoch=epoch, issue=issue,
                                 macro_visible=issue+2, visible_ack_capture=issue+3))
    receipts = {}
    for rid, _, _ in writes:
        if status[rid] == 'SUPERSEDED_NOT_VISIBLE':
            receipts[rid] = dict(kind=status[rid], epoch=epoch, at=write_start)
        else:
            e = next(e for e in write_events if rid in e['owners'])
            receipts[rid] = dict(kind='VISIBLE_WINNER', epoch=epoch,
                                at=e['visible_ack_capture'])
    end = max([e['reply_capture'] for e in read_events] +
              [e['visible_ack_capture'] for e in write_events] + [0])
    return dict(replies=replies, image=image, receipts=receipts,
                read_events=read_events, write_events=write_events,
                backend_last_capture=end, busy_edges=end+1 if reads or writes else 0,
                winner_compare_edges=comparisons,
                fill_edges=len(reads)+len(writes)+comparisons)


class FrameLease:
    """Finite reference seats. Actual consumer receipts, never engine idle alone."""
    def __init__(self, frame, epoch):
        self.frame, self.epoch = frame, epoch
        self.reads = {e['id']: e['reply_capture'] for e in frame['read_events']}
        self.writes = {rid: r['at'] for rid, r in frame['receipts'].items()}
        self.closed = False

    def receipt(self, direction, rid, epoch, edge):
        if self.closed or epoch != self.epoch:
            raise ValueError('Closed or stale frame receipt')
        seats = self.reads if direction == 'read' else self.writes if direction == 'write' else None
        if seats is None or rid not in seats or edge < seats[rid]:
            raise ValueError('Unknown, duplicate or premature receipt')
        del seats[rid]

    def rearm(self, engine_retired):
        if self.reads or self.writes or not engine_retired or self.closed:
            raise ValueError('Frame not drained and retired')
        self.closed = True


def build():
    rows = inputs()
    macro = json.loads((BASE/'inputs/1_ot_sram_1r1w_512x128_m4_r2c2.json').read_text())
    parent = json.loads((BASE/'inputs/5_model.json').read_text())
    cell = parent['area']['actual_master_body_um2']
    # Source-sized frame seats: request metadata/data and retained response.
    read_bits = READ_CAP * (19 + CONTEXT + 11 + 32 + 1)
    write_bits = WRITE_CAP * (19 + CONTEXT + 10 + 32 + 2)
    mask_bits = 4*16 + 4*16*16  # cmd + bank/group local 16-lane masks
    # One frame context and per-command tags through read4/write3 pipeline.
    tag_bits = CONTEXT + 4*(CONTEXT+11) + 4*3*(CONTEXT+10+16)
    control_bits = 64  # counters, scanner state and registered ready/epoch-control reserve
    bits = read_bits + write_bits + mask_bits + tag_bits + WRITE_CAP + control_bits
    backend_bits = 4*(26+512+16*(512+9+1+512+64)+4*512)+2082
    ff = cell['DFFHQNx1_ASAP7_75t_R']
    buf = cell['BUFx4_ASAP7_75t_R']
    upper_edges = READ_CAP + 4 + WRITE_CAP + 3
    hbm = json.loads((BASE/'inputs/hbm_model-r1.json').read_text())
    hbm_clocks = {k: v['clock'] for k,v in hbm['models'].items()}
    return dict(schema='opentallas.dsrom.finite-vm-calendar.v1',
      candidate='DS4096-TP4-S58-PAR2-NP2048', source_pins=rows,
      selected_backend=dict(source='ot_v41_vm_bank4_macro_pipe', DEPTH_GROUPS=16, AW=15,
        element_AW=19, macros=256, banks=4, groups_per_bank=16, columns_per_group=4,
        bits=16777216, macro_body_mm2=256*macro['area']['macro_area_um2']/1e6,
        MACs_per_cycle=0, read_bytes_per_cycle=256, write_bytes_per_cycle=256,
        read_boundary_bits=2048, write_boundary_bits=2048,
        read_port='One base word; four consecutive words, physical-bank order + rotation',
        write_port='At most one 512-bit word per bank per edge; 16 FP32 lane masks expanded to 512 native mask bits',
        masked_write_required=True, retained_wrapper_mask='ALL_ONES: cannot preserve untouched scalar lanes',
        primitive_collision='Actual behavioral primitive read-before-write; selected frame calendar also separates read drain and write issue',
        read_accept_to_capture_edges=4, write_accept_to_macro_visible_edges=2,
        write_accept_to_ack_capture_edges=3),
      calendar=dict(frame='One source logical edge, sole VM ownership until sealed backend completion',
        order='Pre-edge reads then source-order winning writes, one masked lane command per entry; no source waitmask strengthening',
        read_seats=READ_CAP, write_seats=WRITE_CAP, accepted_frames=1,
        admission='Reserve every reply/retirement seat before seal; excess frame refused before acceptance',
        ingress='One typed read or write descriptor per chain edge; logical source snapshot frozen across frame fill',
        fill_upper_edges=READ_CAP+WRITE_CAP+WRITE_CAP*(WRITE_CAP-1)//2, winner_compare_edges=WRITE_CAP*(WRITE_CAP-1)//2, backend_upper_edges=upper_edges,
        backend_upper_ns=upper_edges/0.9, fill_plus_backend_upper_ns=(READ_CAP+WRITE_CAP+WRITE_CAP*(WRITE_CAP-1)//2+upper_edges)/0.9,
        service='Read issue one per edge; retained native4-bank ports, selected source-entry scanner issues at most one masked write per edge. During fill one19bit comparator scans earlier writes and clears overwritten winner flags before seal.',
        worst_write_conflict='All593 writes different words of one bank =>593 issue edges',
        stale='Epoch32 and context169 checked before reply/ACK delivery; no stale receipt frees live lease',
        reset='Close admission; drain accepted frame and delivered receipts under old epoch before coordinated reset/release. Reset mid-frame is explicit cancellation, never retirement or a rollback claim.',
        consumer='Backend capture bound independent of consumer stalls because all response seats reserved. Reuse/retirement needs matched receipts and owner positive consumer bound; no finite arbitrary-stall retirement claim.',
        compiler='Common LINQ rearm after owned rows VM-visible and actual packet/credit debt0; VM version lease remains through accepted SU read and R+2 tail. Bank rearm is not VM version reuse.',
        latency_scope='Per accepted logical frame; whole-token event count/calendar join required, not multiplied by port count or old fixed4/5 crossing cycles'),
      area=dict(frame_read_state_bits=read_bits, frame_write_state_bits=write_bits,
        added_mask_state_bits=mask_bits, context_pipeline_state_bits=tag_bits, winner_flags_bits=WRITE_CAP, sequential_winner_comparator_bits=19, control_state_reserve_bits=control_bits, retained_backend_declared_state_bits=backend_bits, retained_backend_FF_body_floor_mm2=backend_bits*ff/1e6,
        additional_state_bits=bits, FF_body_floor_mm2=bits*ff/1e6,
        clock_buffer_groups8_floor=(bits+7)//8,
        clock_buffer_body_floor_mm2=((bits+7)//8)*buf/1e6,
        FF_sink_capacitance='Use actual mapped FF CLK capacitance, no gateway-only or omitted macro loads',
        macro_clock_cap_SS_fF=256*macro['timing']['ss']['clk_cap_ff'],
        macro_clock_cap_FF_fF=256*macro['timing']['ff']['clk_cap_ff'],
        containment='New frame staging not credited against existing bridge seats or phase journal/return reserve. Existing backend FF not silently omitted from full slot union.',
        mux='Four bank 16:1 group returns (retained pipelined OR); selected read word16:1 lane select32bits; source-tag/receipt demux1520/593; sequential19bit equality,593-entry scan/select datapath. Logic/mux area needs mapping, FF floor is not total',
        floorplan='256 full-size native macros plus existing backend FF and above new state/control. Named co-resident slot and pin/OBS/PG/clock union still required.'),
      physical=dict(macro_timing=macro['timing'], macro_abstract_only=True,
        clock_GHz=0.9, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
        SS_CLKQ_nominal_ps=macro['timing']['ss']['clk_to_q_ps'],
        SS_remaining_after_nominal_CLKQ_and_uncertainty_ps=1000/0.9-60-macro['timing']['ss']['clk_to_q_ps'],
        remaining_is_not_slack='Must deduct source flop setup, mask mux/wire and clock skew; use actual slew/load grids',
        lower_bound_native_signal_tracks=dict(read_data=2048,write_data=2048,write_masks_expanded=2048,write_masks_lane=64,read_addr=15,write_addr=60),
        capacity='Named routes/layer tracks, literal OBS/PG/pin-via exclusions not yet bound. No universal PG reserve or route-fit credit.'),
      HBM_owner_join=dict(owner_commit='c8dafdfe0', clock_inventory=hbm_clocks,
        action='Join retained matrix+compute+gateway endpoints into selected fullSM clock/reset/PG census; no service-clock-only qualification.',
        Popper='PHY LEN/BEAT and DS staging corrections; no competing edits', qualification=False),
      target_applicability=dict(DS_ROM='Selected candidate prospective VM provider only',DS_HBM='HBM inventory consumed, GPU VM organisation remains owner-selected',Qwen_ROM='No DS source-priority or topology transfer',Qwen_HBM='FullSM matrix clock endpoints included in inventory, no hardware qualification'),
      Maxwell_fence_binding=dict(source_git='5f5e4a310', receipt='inputs/maxwell_existing_fences.json', scope='Conditional existing12LINQ fences; no new SU guard charged, actual positive visible/credit callback still required'),
      next_component=dict(default_parameter='VM_BANK4_MASKED_FRAME=0',
        source_copy='Additive copy of full16-group bank4_macro_pipe, mask cmd/local16bit registers and native lane expansion; tagged4edge replies and3edge visible ACK',
        no_engine_RTL_written=True, model_review_required=True,
        sized_contract_ready=True, whole_parent_physical_closure_not_prerequisite_to_component_RTL=True,
        parent_integration_blockers=['Nonstall engine preloads/output phase reservations and actual request-valid adapter timing', 'Maxwell accepted version/address leases and compiler positive interval/event join', 'Claude selected two-clock packet widths/seats/reset drain contract', 'Named complete slot/clock/reset/PG/OBS/native pin union']),
      admission=dict(component_model_for_review=True, RTL_GO=False, parent_PnR=False, SSFF_closure=False, whole_token=False),
      live_solver_unchanged=True, new_PVE2_PVE3_jobs=0)


if __name__ == '__main__':
    path = BASE/'model.json'
    path.write_text(json.dumps(build(), indent=2, sort_keys=True)+'\n')
    print(path)
