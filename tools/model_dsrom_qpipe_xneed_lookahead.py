#!/usr/bin/env python3
"""Source-sized x-need lookahead proposal. No RTL build or timing qualification."""
from dataclasses import dataclass
from pathlib import Path
import argparse
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'results/uarch/dsrom_qpipe_xneed_lookahead_20261003'


def verify_inputs(root=RECORD):
    manifest = json.loads((root / 'source_inputs.json').read_text())
    for item in manifest['origins'] + list(manifest['ss_cell_blocks'].values()):
        data = (root / item['archive']).read_bytes()
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('source input changed: ' + item['archive'])
    return manifest


def first(mask, n):
    for c in range(n):
        if mask & (1 << c):
            return c
    return 0  # source first_w10 returns zero when none is live


def priority_table(mask, n):
    return tuple((bool(mask >> (c + 1)), first(mask & ~((1 << (c + 1)) - 1), n))
                 for c in range(n))


@dataclass(frozen=True)
class State:
    run: int
    q: int
    b: int
    c: int
    j: int
    pos: int = 0


def baseline_next(s, live, next_live, count, qlast):
    """Independent transcription of archived ot_v41_walk2_w10 always block."""
    nc, nf = 0, False
    for k in range(len(count)-1, -1, -1):
        if live & (1 << k) and k > s.c:
            nc, nf = k, True
    livn = next_live if s.b == 7 else live
    fc = 0
    for k in range(len(count)-1, -1, -1):
        if livn & (1 << k):
            fc = k
    if s.j + 1 < count[s.c]:
        return State(1, s.q, s.b, s.c, (s.j+1) & 7, s.pos)
    if nf:
        return State(1, s.q, s.b, nc, 0, s.pos)
    if s.b == 7 and s.q == qlast:
        return State(0, 0, 0, 0, 0, s.pos)
    return State(1, (s.q+1) & 7 if s.b == 7 else s.q, (s.b+1) & 7, fc, 0, s.pos)


@dataclass(frozen=True)
class Facts:
    last_unit: bool
    has_next_class: bool
    next_class: int
    first_current: int
    first_next: int
    last_round: bool
    last_subblock: bool
    last_position: bool


def facts_for(s, live, next_live, count, qlast, plast):
    valid, successor = priority_table(live, len(count))[s.c]
    return Facts(s.j+1 >= count[s.c], valid, successor,
                 first(live, len(count)), first(next_live, len(count)),
                 s.b == 7, s.q == qlast, s.pos == plast)


def candidate_next(s, f):
    """Registered facts feed a shallow branch mux; no priority scan here."""
    if not f.last_unit:
        return State(1, s.q, s.b, s.c, (s.j+1) & 7, s.pos)
    if f.has_next_class:
        return State(1, s.q, s.b, f.next_class, 0, s.pos)
    if f.last_round and f.last_subblock:
        return State(0, 0, 0, 0, 0, s.pos)
    return State(1, (s.q+1) & 7 if f.last_round else s.q,
                 (s.b+1) & 7, f.first_next if f.last_round else f.first_current, 0, s.pos)


def subblock(units, enabled, q):
    counts = tuple(min(8, max(0, u - 8*q)) for u in units)
    live = sum(1 << c for c, count in enumerate(counts) if count and enabled[c])
    return live, counts


def exercise(units, enabled, qlast, plast, stalls=(), mutant=None):
    """Executable MODEL trace, not RTL evidence. Accepted beats are consecutive."""
    live, _ = subblock(units, enabled, 0)
    s = State(int(bool(live)), 0, 0, first(live, len(units)), 0)
    base = s
    trace, edges = [], 0
    cached = None
    while s.run:
        live, count = subblock(units, enabled, s.q)
        nxt, _ = subblock(units, enabled, (s.q+1) & 7)
        if cached is None:
            cached = facts_for(s, live, nxt, count, qlast, plast)
        if edges not in stalls:
            assert s == base, (edges, s, base)
            trace.append((edges, s.pos, s.q, s.b, s.c, s.j))
            expected = baseline_next(base, live, nxt, count, qlast)
            got = candidate_next(s, cached)
            if not expected.run and base.pos != plast:
                live0, _ = subblock(units, enabled, 0)
                expected = State(1, 0, 0, first(live0, len(units)), 0, base.pos+1)
            if not got.run and not cached.last_position:
                live0, _ = subblock(units, enabled, 0)
                got = State(1, 0, 0, first(live0, len(units)), 0, s.pos+1)
            old = cached
            base, s = expected, got
            live, count = subblock(units, enabled, s.q)
            nxt, _ = subblock(units, enabled, (s.q+1) & 7)
            cached = facts_for(s, live, nxt, count, qlast, plast)
            if mutant == 'stale_last':
                cached = Facts(old.last_unit, *tuple(cached.__dict__.values())[1:])
            if mutant == 'two_cycle' and edges % 2:
                s = State(1, trace[-1][2], trace[-1][3], trace[-1][4], trace[-1][5], trace[-1][1])
            assert s == base, (edges, s, base)
        # Stalls hold both state and its facts. No second clock is consumed.
        edges += 1
    return trace, edges


def fanout_tree(sinks, maximum=8):
    count = 0
    while sinks > 1:
        sinks = math.ceil(sinks / maximum)
        count += sinks
    return count


def build_model(root=RECORD):
    pins = verify_inputs(root)
    screen = json.loads((root / 'inputs/clock_screen.json').read_text())
    n, sw, hc = 8, 3, 3
    tables = 2 * (n*(sw+1) + sw+1)  # current/next: per-class successor + first/valid
    facts = 2*sw+5  # next_c, firstnext_c, lastu, hasnext, lastb, lastq, lastpos
    # first_current is selected from the existing current table, not charged
    # again as a registered field; all other facts above are dedicated local FF.
    data_ff, valid_ff = hc*(tables+facts), hc
    cells = pins['ss_cell_blocks']
    area = lambda name: cells[name+'_ASAP7_75t_R']['area_um2']
    mux_area = 2*area('AND2x2') + area('OR2x2') + area('INVxp33')
    # Explicit unshared construction reserve, not an observed mapped census.
    # Each priority output has prefix OR, onehot AND and encoder OR logic.
    priority_gate_reserve = 2*hc*(n+1)*(3*n + sw*math.ceil(n/2))
    # Hold/go/shift muxes for every added data FF; class-fact reads use an N:1 mux.
    bitmux_reserve = 2*data_ff + hc*facts*(n-1)
    control_buffers = (fanout_tree(tables+facts) * hc * 2 + fanout_tree(tables) * hc)
    clock_buffers = fanout_tree(data_ff+valid_ff)
    ff_area = data_ff*area('DFFHQNx2') + valid_ff*area('DFFASRHQNx1')
    logic_area = priority_gate_reserve*max(area('AND2x2'),area('OR2x2')) + bitmux_reserve*mux_area
    buffers_area = (control_buffers+clock_buffers)*area('BUFx4')
    total = ff_area + logic_area + buffers_area
    historical = json.loads((root/'inputs/historical_fill_pricing.json').read_text())
    return {
        'schema':'dsrom-qpipe-xneed-lookahead-model-v1',
        'verdict':'MODEL_PREPARED_PHYSICAL_AND_RTL_ADMISSION_PENDING',
        'scope':'successor in existing qpipe branch; unchanged full NB2/MTP1/EARLY1/FAST1/PP1 shape',
        'default_off_parameter':'QP_NEED_LOOKAHEAD=0 (proposed, no RTL yet)',
        'geometry':{'NB':2,'NSEG':n,'NCH':16,'XF':4,'HC':hc,'physical_ROM_instances':4},
        'observed_baseline':{'record_commit':'2078c269c4a14dd566b96a73b52a272582faa13f',
            'source_commit':screen['source_commit'],'fmax_mhz':screen['phases']['rep']['focus']['ctl']['fmax_mhz'],
            'setup_wns_ps':screen['phases']['rep']['focus']['ctl']['setup_wns_ps'],
            'startpoint':screen['phases']['rep']['focus']['ctl']['path']['startpoint'],
            'endpoint':screen['phases']['rep']['focus']['ctl']['path']['endpoint'],
            'scope':'placement parasitics, ideal clock, not routed SS/FF; baseline is not qpipe successor'},
        'construction':{'tables_per_local_copy_bits':tables,'facts_per_local_copy_bits':facts,
            'local_copies':hc,'data_FF_increment':data_ff,'async_valid_FF_increment':valid_ff,
            'total_FF_increment':data_ff+valid_ff,'existing_nA_nB_nQ2_state_charged_again':False,
            'external_ports_increment':0,'SRAM_ROM_bits_increment':0,'adder_or_CSA_change':False,
            'fill_cycles_increment':0,'accepted_beat_II_cycles':1,'recurrence_extra_cycles':0,
            'table_ready_bound':'next-q cache from stable nB must be ready before q changes; at least eight round-end accepts per q',
            'table_update':'go seeds current/next priority tables; q advance copies next to current; next table refreshed from source nB',
            'facts_update':'on each accepted beat, compute facts for EXACT successor; on stalls hold; reset/empty-go invalidate',
            'critical_cones':['registered lastu/hasnext -> local successor mux -> need/shadow state',
                              'successor choice -> parallel selected class metadata -> fact FF',
                              'go/current/next table load -> local table FF',
                              'beat match -> local update enables; no serial priority encoder in this loop']},
        'cost':{'unified_DFF_basis_um2':area('DFFHQNx1'),'state_area_um2':ff_area,
            'priority_elementary_gate_reserve':priority_gate_reserve,'bit_mux_reserve':bitmux_reserve,
            'logic_area_reserve_um2':logic_area,'clock_buffer_reserve':clock_buffers,
            'control_buffer_reserve':control_buffers,'buffer_area_reserve_um2':buffers_area,
            'combined_incremental_cell_area_reserve_um2':total,'placed_area_at_50pct_um2':2*total,
            'method':'source-sized unshared Boolean construction and actual pinned SS cell areas; buffers use eight-sink tree reservation; not an RTL synthesis measurement',
            'MAC_per_cycle_increment':0,'added_memory_bytes_per_cycle':0,'added_external_boundary_bits_per_cycle':0,
            'local_metadata_logical_wire_reserve':hc*(tables+facts+1),
            'track_capacity_and_extracted_RC':'pending physical station placement; storage bits are not proof of routed tracks',
            'replication':'incremental area R*per_element; current Scenario C element count handoff pending, no die/stage regeneration'},
        'latency':{'new_added_cycles_per_qop':0,'existing_Rcap0_added_cycles':2,'existing_Rcap1_added_cycles':3,
            'single_user_delta_formula_s':'new_added_cycles_per_qop * current_source_bound_qops / 1.2e9 = 0 for this proposed successor',
            'existing_pricing_retained':historical['basis'],'historical_pricing_is_current_scenarioC':False,
            'half_field_rate_walker_rejected':True,'nominal_1p2GHz_qualified':False},
        'admission_required':['finite slot/clock/reset/PG/track fit with physical owners',
            'SS60/FF25 loaded recurrence and go/init paths at 0.833ns',
            'full-shape actual immutable-ROM numerical oracle + all public valid/fault/tag/reset/drain signals',
            'consecutive accepted beats, stalls, empty-go, q/round/class/position seams; stale-cache and II2 mutants explicit DIFF',
            'source-bound config decode repair in baseline and candidate: original qpipe still has second-row truncation bug',
            'actual cycle/performance comparison then adoption decision'],
        'hardware_written':False,'compile_launched':False,'stage_or_die_records_regenerated':False,
    }


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.output.write_text(json.dumps(build_model(),indent=2,sort_keys=True)+'\n')

if __name__ == '__main__':
    main()
