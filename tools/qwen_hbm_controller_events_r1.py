#!/usr/bin/env python3
"""Finite source-bound controller prerequisite, opt-in analytical witness only.

Column times are supplied legal DRAM events, not a substitute DRAM scheduler.
No RTL, checkpoint execution, rate credit, or epoch-reuse proof is supplied.
"""
from collections import Counter
from dataclasses import dataclass, replace
from fractions import Fraction
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

BASE = 'e72abea5a'
REV = '4535be1001d69bc43669e0fdf0401896be4034a6'
SOURCE = 'rtl/hdc/kv/ot_hdc_hbm_model.sv'
SOURCE_SHA = 'd19116e6485266aef997ae52c82a46421267f5de9bb6d0b380d7348b30ffd57d'
DIR = 'results/rtl/qwen_hbm_complete_20261001/'
MACRO = 'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2'
ROOT = Path(__file__).resolve().parents[1]

def pinned(repo, rev, path):
    return subprocess.check_output(['git', 'show', rev + ':' + path], cwd=repo)

def source_timing(repo=ROOT):
    raw = pinned(repo, REV, SOURCE)
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError('controller pin changed')
    timing = {k: int(v) for k, v in re.findall(rb'parameter integer (\w+_PS)\s*=\s*(\d+)', raw)}
    return {k.decode(): v for k, v in timing.items()}

@dataclass(frozen=True)
class Beat:
    addr: int
    tag: int
    producer_epoch: int
    transport_epoch: int
    beat: int = 0
    write: bool = False
    data: int = 0
    accepted_ps: int = 0

@dataclass(frozen=True)
class Return:
    request: Beat
    data: int
    due_ps: int
    kind: str

@dataclass(frozen=True)
class Pending:
    request: Beat
    column_ps: int
    visible_ps: int
    visible: bool = False

class Controller:
    """One stack, NPC32/QD64/RQD32, shared four retained write slots.

    Immutable Beat is the acceptance snapshot. RAW waits until visibility.
    WR slots persist through completion ready, bounding ACK backpressure too.
    Calls to column must be from an external bank/refresh/turnaround calendar.
    FRFCFS estimates are externally supplied, matching the pinned selection
    algorithm; this object checks ordering and lifecycle, not timing legality.
    """
    def __init__(self, timing, write_depth=4):
        if write_depth < 1:
            raise ValueError('finite write depth')
        self.timing = timing
        self.write_depth = write_depth
        self.q = [[] for _ in range(32)]
        self.r = [[] for _ in range(32)]
        self.skip = [0]*32
        self.pending = []
        self.mem = {}  # sparse simulation oracle, never modulo MEM_WORDS
        self.now = 0
        self.rr = 0
        self.held = None
        self.events = []
        self.external = {k: 0 for k in ('CDC_forward', 'CDC_reverse', 'RMW', 'reader', 'consumer')}

    @staticmethod
    def pc(addr):
        return ((addr >> 2) ^ (addr >> 7) ^ (addr >> 12)) & 31

    def advance(self, now):
        if now < self.now:
            raise ValueError('time reversal')
        self.now = now
        for i, p in enumerate(self.pending):
            if not p.visible and p.visible_ps <= now:
                self.mem[p.request.addr] = p.request.data
                self.pending[i] = replace(p, visible=True)
                self.events.append(('WR_visible', p.request, now))

    def accept(self, request, now):
        self.advance(now)
        fields = ((request.addr, 34), (request.tag, 16), (request.producer_epoch, 64),
                  (request.transport_epoch, 32), (request.beat, 5), (request.data, 256))
        if any(not 0 <= value < 1 << bits for value, bits in fields):
            raise ValueError('request width')
        pc = self.pc(request.addr)
        if len(self.q[pc]) == 64:
            return False
        self.q[pc].append(replace(request, accepted_ps=now))
        self.events.append(('accept', self.q[pc][-1], now))
        return True

    def reorder(self, pc, estimates):
        q = self.q[pc]
        n = min(16, len(q))
        if len(estimates) != n or not n:
            raise ValueError('one estimate for every RW16 candidate')
        selected = 0
        best = estimates[0]
        if self.skip[pc] < 16:
            for i in range(1, n):
                b = q[i]
                blocked = any(a.addr == b.addr and (a.write or b.write) for a in q[:i])
                if not blocked and estimates[i] < best:
                    best, selected = estimates[i], i
        if selected:
            # Descending shifts mirror every source swap, including both epochs.
            b = q[selected]
            for i in range(selected, 0, -1):
                q[i] = q[i-1]
            q[0] = b
            self.skip[pc] += 1
        else:
            self.skip[pc] = 0
        return selected

    def column(self, pc, now):
        self.advance(now)
        if not self.q[pc]:
            return False
        b = self.q[pc][0]
        # Same-sector WAW/RAW cannot outrun a delayed older backing write.
        if any(p.request.addr == b.addr and not p.visible for p in self.pending):
            return False
        if b.write:
            if len(self.pending) >= self.write_depth:
                return False  # before column mutation AND head pop
            visible = now + self.timing['CWL_PS'] + self.timing['BURST_PS']
            self.pending.append(Pending(b, now, visible))  # reservation first
            self.events.append(('WR_reserved', b, now))
        else:
            if len(self.r[pc]) >= 32:
                return False  # return reservation before read column
            due = now + self.timing['CL_PS'] + self.timing['BURST_PS'] + self.timing['RSP_PS']
            self.r[pc].append(Return(b, self.mem.get(b.addr, 0), due, 'RD'))
        self.events.append(('column', b, now))
        self.q[pc].pop(0)
        return True

    def offer(self, now):
        self.advance(now)
        if self.held is not None:
            return self.held[2]
        # One ordinary shared stack return arbiter, locked until handshake.
        for offset in range(32):
            pc = (self.rr + offset) % 32
            if self.r[pc] and self.r[pc][0].due_ps <= now:
                self.held = ('RD', pc, self.r[pc][0])
                return self.held[2]
        return None

    def take(self, now, ready):
        offered = self.offer(now)
        if offered is not None and ready:
            _, pc, result = self.held
            assert self.r[pc].pop(0) == result
            self.events.append(('RD_accept', result.request, now))
            self.rr = (pc+1) % 32
            self.held = None
        return offered

    def write_offer(self, now):
        self.advance(now)
        if not self.pending:
            return None
        p = self.pending[0]
        due = p.visible_ps + self.timing['RSP_PS']
        if not p.visible or due > now:
            return None
        return Return(p.request, p.request.data, due, 'WR_visible')

    def write_take(self, now, ready):
        offered = self.write_offer(now)
        if offered is not None and ready:
            self.pending.pop(0)
            self.events.append(('WR_visible_accept', offered.request, now))
        return offered

    def drained(self):
        return (not any(self.q) and not any(self.r) and not self.pending
                and self.held is None and not any(self.external.values()))


def queue_port_schedule(selected, window=16):
    """One 1R1W bank: scan snapshot, then stable descending shift.

    Logical slots are relative to q_rp; caller translates modulo QD64.
    Read-before-write semantics apply. Selected full word is cached in scan.
    Empty bank and concurrent enqueue are excluded by explicit PC freeze.
    """
    if not 1 <= window <= 16 or not 0 <= selected < window:
        raise ValueError('RW16 selection')
    events = [dict(read=i, write=None, stage='scan') for i in range(window)]
    events.append(dict(read=None, write=None, stage='scan_result'))
    if selected:
        for i in range(selected+2):
            events.append(dict(read=selected-1-i if i < selected else None,
                               write=selected+1-i if 1 <= i <= selected else (0 if i == selected+1 else None),
                               stage='shift'))
    events.append(dict(read=None,write=None,stage='reserved_column'))
    return events


class CompletionSink:
    """Four finite ACK/CDC records attached to one model stack.

    Domain crossings are explicit caller events; no automatic clock assumption.
    Common36 addressed all272 scoreboard/publication stays an external gate.
    """
    def __init__(self, controller, depth=4):
        if depth < 1:
            raise ValueError('finite sink depth')
        self.controller = controller
        self.depth = depth
        self.records = {}

    def capture(self, now):
        offered = self.controller.write_offer(now)
        if offered is None or len(self.records) == self.depth:
            return None
        if offered.request in self.records:
            raise ValueError('duplicate ACK identity')
        self.records[offered.request] = 'CDC_forward'
        self.controller.external['CDC_forward'] += 1
        assert self.controller.write_take(now, True) == offered
        return offered

    def transition(self, identity, event):
        transitions = {
            'forward_crossed': ('CDC_forward', 'store_pending'),
            'stored': ('store_pending', 'retire_pending'),
            'retired': ('retire_pending', 'CDC_reverse'),
            'reverse_crossed': ('CDC_reverse', 'released'),
        }
        if event not in transitions:
            raise ValueError('unknown consumer event')
        old, new = transitions[event]
        if self.records.get(identity) != old:
            raise ValueError('identity or event order mismatch')
        counts = self.controller.external
        if old == 'CDC_forward':
            counts['CDC_forward'] -= 1
            counts['consumer'] += 1
        if new == 'CDC_reverse':
            counts['consumer'] -= 1
            counts['CDC_reverse'] += 1
        if new == 'released':
            counts['CDC_reverse'] -= 1
            del self.records[identity]
        else:
            self.records[identity] = new


def compose(repo=ROOT):
    pins = {}
    def get(rev, path):
        raw = pinned(repo, rev, path)
        pins[path] = dict(commit=subprocess.check_output(['git','rev-parse',rev], cwd=repo, text=True).strip(),
                          sha256=hashlib.sha256(raw).hexdigest())
        return raw
    raw = get(REV, SOURCE)
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    timing = source_timing(repo)
    common_source = get(BASE, 'tools/qwen_hbm_complete_common36.py')
    assert b'result<issue+27*SLOW' in common_source
    records = {}
    for name in ('controller_source_prerequisites_r1.json', 'finite_service_adapter_review_r2.json',
                 'finite_service_adapter_r2.json', 'common36_drain_model_r2.json', 'common36_drain_review_r2.json',
                 'actual_two_token_KV_state_r1.json', 'actual_two_token_terminal_r1/receipt.json'):
        records[name] = json.loads(get(BASE, DIR+name))
    trace_path = DIR+'actual_two_token_terminal_r1/token1_execution.json.gz'
    execution = json.loads(gzip.decompress(get(BASE, trace_path)))
    trace = execution['trace']
    assert len(trace) == 1737 and execution['instructions_retired'] == 1737
    adapter = records['finite_service_adapter_r2.json']
    macro = json.loads(get(REV, MACRO+'.json'))
    macro_verilog = get(REV, MACRO+'.v')
    assert macro['spec']['words'] == 64 and macro['spec']['bits'] == 512 and macro['spec']['ports'] == '1r1w'
    assert b'if (r_ce_in) rd_out <= word_read(r_addr_in)' in macro_verilog
    assert b'if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in)' in macro_verilog
    # Retain both epoch32 transport and producer64; no assumption about epoch9.
    q_fields = dict(write=1, sector=34, tag=16, beat=5, data=256, arrival_ps=64,
                    transport_epoch=32, producer_epoch=64)
    r_fields = dict(due_ps=64, tag=16, beat=5, data=256, sector=34,
                    transport_epoch=32, producer_epoch=64)
    pending_fields = dict(valid=1, visible=1, sector=34, tag=16, data=256,
                          due_ps=64, transport_epoch=32, producer_epoch=64)
    q_width, r_width = sum(q_fields.values()), sum(r_fields.values())
    pcs = 8*32
    queue_epoch_bits = pcs*96*(64+32)
    return_address_bits = pcs*32*34
    pending_bits = 8*4*sum(pending_fields.values())
    # Frozen RW16 candidates permit one sequential metadata comparison/cycle;
    # full selected word and predecessor word retained during 1R1W shifts.
    scan_metadata = 1+34+64
    scratch_per_pc = 16*scan_metadata + 2*q_width + 2*64 + 4+5+5+1
    arb_per_stack = r_width+1+5+5
    pointers = 8*(2*2+3)
    ingress_holds = 8*(1+409+6)  # valid, LEN32 request, expansion cursor
    extra_bits = ingress_holds+ queue_epoch_bits+return_address_bits+pending_bits+pcs*scratch_per_pc+8*arb_per_stack+pointers
    # Store original q/r fields too: total macro count, not additive to old q/r.
    macro_count = pcs*2
    area = macro_count*macro['area']['macro_area_um2']/1e6
    boundaries = dict(stack_request_bits=1+34+16+6+256+96,
                      stack_read_return_bits=1+r_width, stack_WR_visible_bits=1+16+34+96+64,
                      all_PC_internal_read_bits_per_stack=32*r_width,
                      all_PC_internal_queue_read_bits_per_stack=32*q_width)
    links = adapter['bindings']
    trace_by_id = {o['id']:o for o in trace}
    for link in links:
        for key, opcode in [('writer','KV_WRITE'),('fence','KV_FENCE'),('read','KV_READ'),('scores','SCORES'),('pv','PV')]:
            assert trace_by_id[link[key]]['opcode'] == opcode
        assert link['writer'] in trace_by_id[link['fence']]['dependencies']
        assert link['fence'] in trace_by_id[link['read']]['dependencies']
        assert link['read'] in trace_by_id[link['scores']]['dependencies']
        assert link['read'] in trace_by_id[link['pv']]['dependencies']
    wr_residence = timing['CWL_PS']+timing['BURST_PS']+timing['RSP_PS']
    demands = []
    for d in adapter['writer_demands']:
        # Independent per-stack work floors; not summed as token latency.
        writes = d['writes_by_stack']
        pending_floor = max((w+3)//4*wr_residence for w in writes)
        demands.append(dict(position=d['position'], writer=d['writer'], fence=d['fence'], read=d['read'],
                            scores=d['scores'], pv=d['pv'], writes_by_stack=writes,
                            RMW_reads_by_stack=d['RMW_reads_by_stack'],
                            stack_ingress_edges_floor=max(d['commands_by_stack']),
                            RD_arbitration_edges_floor=max(d['RMW_reads_by_stack']),
                            RD_empty_head_prefetch_edges=2,
                            WR_ack_arbitration_edges_floor=max(writes),
                            retained_depth4_WR_column_to_last_ACK_work_floor_ps=pending_floor,
                            partial_RMW_serial_edges_per_sector=27,
                            RMW_scope='common36r2 three XOR/AND/XOR instructions at9 serial edges each; candidate callbacks, no engine timing credit',
                            scoreboard_store_serial_edges_floor=272,
                            exact_join='all272 reversecredit completions -> fence -> reader lease -> SCORES/PV visible+retired -> lease release'))
    blockers = [
        'External column calendar must bind ACT/PRE/refresh/RRDS/RRDL/FAW/tCCD/turnaround and all weight+KV traffic to these finite queues; supplied event times alone do not qualify DRAM.',
        'Serialized RW16 scan freezes PC enqueue, preserves source selection order, and costs 18..35 controller edges per selection; loaded occupancy/backpressure and full1737 issue/RF/shared/NoC latency remain uncomposed.',
        'Producer64 plus transport32 are retained conservatively; parent epoch proof and actual common36 owner/epoch ABI, drain mailbox nonce and no-old-callback property remain unbound.',
        'WR-column observer must reserve a finite capture slot before command; ACK/RMW/scoreboard/forward+reverse CDC/consumer providers must obey explicit ready and drain contracts.',
        'Timer64 fields are simulation proxies; hardware timer resolution, wrap/failstop, max ready residence and refresh horizon must be proved before width selection.',
        'Inventory macro views are analytical abstracts: in-context SS setup/FF hold, clock tree, arbitration, route tracks/channel capacity and floorplan fit have no measured closure.',
        'Actual two-token record is software functional evidence and did not retain encoded KV payload; no encoded hardware data path or whole-program timing admission follows.'
    ]
    return dict(schema='Qwen_controller_finite_events_and_queue_ports_r1', source_pins=pins,
        status='NARROW_QUEUE_PORT_AND_RESERVATION_COST_MODEL_ONLY', default_enabled=False,
        proposed_geometry=dict(NPC=32,QD=64,RQD=32,AW=34,TAGW=16,LENW=6,BEATW=5,dies=2,stacks_per_die=4,write_pending_depth_per_stack=4),
        epochs=dict(producer_bits=64,transport_bits=32,epoch9_proof='parent-owned; no narrowing or reuse credit'),
        timing_ps=timing, timing_authority='Pinned model timing presets; REQ/RSP explicitly assumed in source; not measured HBM service',
        finite_service=dict(WR_column_to_visible_ps=timing['CWL_PS']+timing['BURST_PS'],
            WR_column_to_offer_ps=wr_residence, RD_column_to_offer_ps=timing['CL_PS']+timing['BURST_PS']+timing['RSP_PS'],
            refresh_RFC_ps=timing['RFC_PS'],refresh_REFI_ps=timing['REFI_PS'],
            policies='fullAW34 sparse oracle; wait RAW/WAW until visible; reserve4 retained WR slots BEFORE column+pop; keep slot until visible ACK ready; no reset-as-drain',
            no_stall_depth4_WR_ceiling_per_stack_bytes_s=4*32*1e12/wr_residence,
            simultaneous_PC_wave=32, wave_admitted=4, wave_stalled=28,
            completion_pressure='unbounded ready residence backpressures WR columns; finite depth does not guarantee service',
            clock_conversion='Costs are controller edge counts and DRAM ps. Convert with explicit controller T_c and serial T_s/domain phase; do not assume universal CLK_PS1000 or 1.2GHz.'),
        queue_ports=dict(request_fields=q_fields,request_width=q_width,return_fields=r_fields,return_width=r_width,
            independent_PC_replicas=pcs, request_banks=pcs,return_banks=pcs,
            request_port_bits_per_edge=dict(read=q_width,write=q_width), return_port_bits_per_edge=dict(read=r_width,write=r_width),
            request_port_bytes_per_edge=dict(read=q_width/8,write=q_width/8), return_port_bytes_per_edge=dict(read=r_width/8,write=r_width/8),
            MACs_per_cycle=0, intensity='metadata/identity service, zero arithmetic MACs',
            serialized_scan_edges=17, scan_scope='full RW16 window; n queued candidates cost n+1 scan edges', cached_head_column_edges=1, reorder_nonzero_edges='sel+2 for sel1..15',
            selection_total_edges_head=18,selection_total_edges_max=35,
            source_unrolled_worst_per_PC_selection=dict(read_words=16,shift_writes=16,enqueue_writes_up_to=32),
            admission='freeze PC enqueue for scan+shift; queue burst expansion serializes one beat per stack edge with held LEN32 request; no combinational 32-write credit',
            selector='sequential earliest-time scan, oldest ties, same-sector write interlock and MAXSKIP16; snapshot timing state during scan; supplied estimates require external timing provider',
            read_arb=dict(replicas=8,inputs_per_stack=32,outputs_per_edge=1,locked_until_ready=True,
                mux_2to1_bit_equivalents=8*31*r_width, RR_priority_inputs=32, tree_logic_levels=5,
                output_bits_per_edge=r_width, output_payload_bytes_per_edge=32, worst_ready_service_edges_for_wave=32,
                head_prefetch_edges=1, empty_enqueue_to_macro_head_edges=2,
                prefetch_policy='Registered macro rd_out holds each PC head; stop read enable while unchanged. Same-edge empty enqueue reads old word: prefetch next edge, arbitrate following edge. Head advance requires next-word read; no samePC every-edge credit without another head register.',
                wave_scope='32 valid prefetched PC heads, all ready; sustained samePC needs prefetch bubbles'),
            WR_arb=dict(replicas=8,inputs_per_stack=4,outputs_per_edge=1,retained_until_ready=True,
                mux_2to1_bit_equivalents=8*3*(16+34+96+64),service='four due detectors can mark backing visibility independently; one ACK selected per stack edge, FIFO oldest reserved first; pending record keeps identity until downstream accepts',
                downstream='Actual common36 capture/ACK CDC shares four records per DIE, not per stack. CompletionSink test instances are localized protocol witnesses; no added independent per-stack CDC credit.'),
            fanout=dict(accept_epoch_to_beat_slots=32,stack_ingress_target_PC=32,request_valid_to_stack_slots=32,
                pending_RAW_compares_per_candidate=4,pending_RAW_compare_bits_total=8*32*4*34,
                scan_same_sector_compare_pairs_per_PC=120,scan_parallel_older_comparators_per_PC=15,scan_parallel_comparison_bits_total=pcs*15*34,
                due_compare_inputs_per_stack=4, due_compare_bits=64,
                drain_PC_leaf_occupancies=512, stack_leafs=8, two_input_reduction_nodes=511,
                drain_still_requires='held returns, pending writes, ingress expansion, scan shift, CDC, RMW, reader+consumer counters, both dies and fourphase return-zero')),
        additional_state=dict(historical_r1_bits=799384,historical_r1_storage_mm2=.4662007488,
            queue_epoch_bits=queue_epoch_bits, return_full_address_bits=return_address_bits,
            pending_fields=pending_fields,pending_bits=pending_bits,scheduler_scratch_bits=pcs*scratch_per_pc,
            locked_return_arbiter_bits=8*arb_per_stack,write_pointer_bits=pointers,stack_ingress_hold_bits=ingress_holds,total_bits=extra_bits,
            nonqueue_control_FF_bits=pending_bits+pcs*scratch_per_pc+8*arb_per_stack+pointers+ingress_holds,
            FF_proxy_mm2=extra_bits*.2916/.5/1e6,
            scope='Additional to original simulation queues; replaces r1 estimate, never add both. Full macro allocation below already contains queue epoch/address fields; FF scratch+holds are separate. Existing common36r2 costs remain independently charged.'),
        memory_macro_candidate=dict(name=macro['spec']['name'],words=64,bits=512,ports='1R1W',read_latency_edges=1,
            request_macros=pcs, return_macros=pcs,total=macro_count,total_array_bits=macro_count*64*512,
            request_utilization=q_width/512,return_utilization=32*r_width/(64*512),
            macro_area_total_mm2=area,per_die_macro_area_mm2=area/2,
            macro_plus_new_control_subset_mm2=area+(pending_bits+pcs*scratch_per_pc+8*arb_per_stack+pointers+ingress_holds)*.2916/.5/1e6,
            area_subset_scope='queue replacements plus new control proxy only; excludes inherited bank/timing state, existing common36r2, PHY, routing and clock tree; no total controller slot fit',
            SS_clk_to_q_ps=macro['timing']['ss']['clk_to_q_ps'],FF_hold_ps=macro['timing']['ff']['hold_ps'],
            SS_remaining_path_budget_at_target_ps=float(Fraction(2500,3))-60-macro['timing']['ss']['clk_to_q_ps']-macro['timing']['ss']['setup_ps'],
            target_budget_scope='1.2GHz candidate only: assumes same macro destination setup, excludes wires/skew; no setup or hold closure claim',
            inventory_claim_boundary=macro['claim_boundary'],
            slot_fit=False, tracks_required_lower_bound=boundaries, channel_capacity='unbound; width is wire demand before shielding/control/route duplication'),
        program_binding=dict(actual_trace_instructions=len(trace),opcode_counts=dict(Counter(o['opcode'] for o in trace)),
            actual_software_two_tokens=records['actual_two_token_terminal_r1/receipt.json']['whole_two_token_program_completed'],
            writer_bindings=demands, writers_per_token=72,positions=[0,1],
            priced_stage='controller queue/return arbitration and retained WR reservation; per-writer work floors, not additive critical-path token estimate',
            event_DAG=['issue+dependency/RF-ready','accept+producer epoch capture','freeze scan+stable shift','reserve pending/return+WR-column observer','legal DRAM column','backing visibility or read due','locked arbiter ready','ACK capture','forward CDC','store completion bit','consumer retire','reverse CDC credit','all272 fence publication','KV_READ acquire','SCORES/PV visible+retire','lease release','full1737 retire+all domains drain','both-die fourphase return-zero'],
            latency_expression='per transaction: ingress edges*T_c + scan/shift edges*T_c + max(legal DRAM eligibility,capacity/RAW wait) + DRAM tail ps + stack arbitration edges*T_c + explicit CDC phase/ACK-store-retire/reversecredit; compose dependency maxima, never sum parallel work floors'),
        exact_blockers=blockers,hardware_build_ready=False,actual_provider_credit=False,hardware_rate_credit=0,
        whole_program_admission=False,token_cycles=None,headline_rate=None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with args.output.open('x') as f:
        json.dump(compose(),f,indent=2,sort_keys=True);f.write('\n')
