#!/usr/bin/env python3
"""Compile the fixed INDEX microprogram, preserving implemented native latencies.

Usage: hbm_idx_static_calendar.py OUT [--pins registered|none] [--gap N]

The program is one 32-bit instruction per edge (ot_hbm_idx_calendar_static). Every field drives one die tile of
ot_hbm_idx_parent_static at a compiler-fixed edge; no field waits for data, ready or credits.

PIN-REGISTERED TILES (OWNER RULE 19:50 PT 10-15, H-NETLIST/idxreg 2026-10-16): idx_op (ot_hbm_idx_vm_query_static),
idx_q (ot_hbm_idx_query_static), idx_sel (ot_hbm_idx_selector_static) and idx_link (ot_hbm_idx_topk_link_static)
register every data input and output at the pin (+1 edge each; the VM round trip of idx_op crosses two of them,
+2, absorbed in its face). The scorer clusters idx_s0..s3 have no pin registers. The compiler re-times each tile's
fields so that every tile CORE sees exactly the relative timeline it had before (same exact arithmetic, same
internal fixed latencies); the shift of tile X is D_X = the summed pin edges on the path from the calendar to X's
core minus X's own input edge. '--pins none' compiles the historical unregistered timeline (bench mutant).

PIPELINED TOPK LINK (HBM-IDXPIPE 2026-10-18): the die link is ot_hbm_idx_topk_link_static_p (5-stage pack/rotate/
write pipeline, rtl/hbm_accel/index/ot_hbm_idx_topk_link_static_p.sv). It takes the historical input timeline
unchanged (its fixed control delay line re-aligns clear/flush/emit internally) and delivers EVERY output (tx_v/tx,
fault, selected_count) exactly link_core_out = 5 edges later. The compiler keeps every field edge, adds 5 to the
predicted first TX edge and the scan->TX latency, and lengthens the frame tail by 5 so the last TX beat lands inside
the frame. '--pins none' and --link-pipe 0 compile for the historical link (OT_IDX_HIST_LINK parents).

PIPELINED SELECTOR CORE (H-NETLIST/IDXP-SEL 2026-10-16, gate hidx_sel_pr REFUSE 55 levels): the selector core registers
the SRAM read and pipelines compare / tie mask / pack / histogram. Two constant edges reach this schedule (the
SEL_CORE entries of the table): sel_core_out = +2 edges on the selected stream (selected_v/selected_line -> link core,
so every link field moves +2 with it), sel_scan_drain = +2 idle edges after each op4 scan before the first op5 (the
histogram lands 4 edges after the last scan read instead of 2). op5's internal +2 (hist read, sums, recurrence) is
covered by the existing 1-edge gap: its consumers (op3 found-clear, next op4's threshold, op6's ties) ride the same
pipeline or come >= 2 edges later. '--pins none' keeps the historical core (both 0).

SAFE FANOUT SELECTOR (LEAD2-HBM/L2H-IDXSEL 2026-10-19, route hidx_sel_g4p EARLY_FAIL_SETUP -570 ps from one pin flop per
control bit broadcast to 4 quadrants + 12 SRAMs): the selector core takes every input through a kept relay copy (P1) and
a per-consumer kept one-hot copy (P2), uniformly, so sel_in = 1 (pin) + 2; the shell adds an output relay before the pin
flop (q0/q1 -> E/S faces up to ~500 um), sel_out = 2. Every selector-relative field edge is unchanged; the selected
stream, link fields and TX move +3 edges and the frame grows +3 edges.
"""
import argparse, json
from pathlib import Path

PIN_TABLES = {
    'registered': dict(vmq_in=1, vmq_out=1, vm_rt=2, q_in=1, q_out=1, sel_in=3, sel_out=2, link_in=1, link_out=1,
                       link_core_out=5, sel_core_out=2, sel_scan_drain=2),
    'none': dict(vmq_in=0, vmq_out=0, vm_rt=0, q_in=0, q_out=0, sel_in=0, sel_out=0, link_in=0, link_out=0,
                 link_core_out=0, sel_core_out=0, sel_scan_drain=0),
}
FIELDS = dict(weight=(31, 1), query=(30, 1), head=(29, 1), beat=(28, 1), index=(20, 8), op=(16, 4), ps=(14, 2),
              addr=(6, 8), flush=(5, 1), link=(4, 1), group=(0, 4))
# tile that consumes each field (index is shared by query slots, head emits and key beats: owner set per use)
TILE = dict(weight='vmq', query='vmq', head='q', beat='s', op='sel', ps='sel', addr='sel', flush='link', link='link',
            group='link')


def shifts(pin, chain=0):
    """Calendar-edge shift per consuming tile: the tile core sees the historical relative timeline."""
    core = {}
    core['vmq'] = pin['vmq_in']                                   # slot -> vm_query core
    core['q'] = core['vmq'] + pin['vm_rt'] + pin['vmq_out'] + pin['q_in']   # operand block -> query core
    core['s'] = core['q'] + pin['q_out']                          # ql_* -> scorer (no pin regs)
    core['sel'] = core['s'] + chain + pin['sel_in']               # score (+ IDX-SCORE cluster seam chain) -> selector core
    core['link'] = core['sel'] + pin['sel_core_out'] + pin['sel_out'] + pin['link_in']  # selected -> link core
    own_in = dict(vmq=pin['vmq_in'], q=pin['q_in'], s=0, sel=pin['sel_in'], link=pin['link_in'])
    cal = {t: core[t] - own_in[t] for t in core}
    base = min(cal.values())
    return {t: v - base for t, v in cal.items()}, core


def compile_program(pins='registered', gap=100, score_chain=0, link_pipe=None):
    pin = dict(PIN_TABLES[pins])
    if link_pipe is not None:
        pin['link_core_out'] = link_pipe
    sh, core = shifts(pin, score_chain)
    events = []          # (historical edge, tile, field values)
    t = [0]
    marks = {}

    def emit(tile=None, **f):
        if f:
            events.append((t[0], tile, f))
        t[0] += 1

    def wait(n, selector_pass=None):
        if selector_pass is None:
            t[0] += n
        else:
            for _ in range(n):
                emit('sel', ps=selector_pass)

    emit('vmq', weight=1)
    events.append((0, 'sel', dict(op=1)))                         # clear frame (selector) in the first slot
    wait(16)
    for q in range(128):
        emit('vmq', query=1, index=q)
    wait(28)
    for h in range(32):
        emit('q', head=1, index=h)
    wait(gap)
    marks['scan_start'] = t[0]
    emit('sel', op=3)
    marks['first_key'] = t[0]
    for k in range(294):
        if k < 171:
            events.append((t[0], 's', dict(beat=1, index=k)))
        if k >= 123:
            events.append((t[0], 'sel', dict(op=2, addr=k - 123)))
        t[0] += 1
    wait(2)
    for b in range(31, -1, -1):
        emit('sel', op=5, addr=b)
    wait(1)
    for ps in (1, 2):
        emit('sel', op=3, ps=ps)
        for a in range(171):
            emit('sel', op=4, ps=ps, addr=a)
        # The final synchronous SRAM result is consumed on the first drain edge.
        # Its histogram decode uses the live pass field, even while op is idle.
        wait(2 + pin['sel_scan_drain'], selector_pass=ps)
        for b in range(63 if ps == 2 else 31, -1, -1):
            emit('sel', op=5, ps=ps, addr=b)
        wait(1)
    for a in range(171):
        emit('sel', op=6, ps=2, addr=a)
    wait(3)
    emit('link', flush=1)
    wait(1)
    marks['first_emit_historical'] = t[0]
    for b in range(16):
        emit('link', link=1, group=b)
        wait(7)
    wait(4)
    hist_len = t[0]
    tail = pin['link_core_out']           # pipelined link: last TX beat lands link_core_out edges later

    words = {}
    owner = {}
    for e, tile, f in events:
        n = e + sh[tile]
        w = words.setdefault(n, {})
        for k, v in f.items():
            if k in w and (w[k] != v or owner[(n, k)] != tile):
                raise SystemExit(f'field collision at edge {n}: {k} {w[k]}/{owner[(n, k)]} vs {v}/{tile}')
            w[k] = v
            owner[(n, k)] = tile
    length = max(hist_len + max(sh.values()) + tail, max(words) + 1)
    assert length <= 2048, length
    prog = []
    for n in range(length):
        word = 0
        for k, v in words.get(n, {}).items():
            lo, wd = FIELDS[k]
            assert 0 <= v < (1 << wd), (k, v)
            word |= v << lo
        prog.append(word)
    # predicted pin-edge timeline, counted in instruction slots from instruction 0 (calendar issue = start + 3)
    emit0 = marks['first_emit_historical'] + sh['link']
    pred = dict(
        first_emit_instruction=emit0,
        first_tx_from_instruction0=emit0 + pin['link_in'] + 2 + pin['link_core_out'] + pin['link_out'],   # link core: emit -> read -> tx
        scan_start_instruction=marks['scan_start'] + sh['sel'],
        first_key_instruction=marks['first_key'] + sh['s'],
        added_edges_scan_to_tx=sh['link'] + pin['link_in'] + pin['link_core_out'] + pin['link_out'] - sh['sel'],
        added_edges_frame=length - hist_len,
    )
    meta = dict(length=length, historical_length=hist_len, pins=pins, pin_table=pin, score_chain=score_chain, calendar_shift=sh,
                core_shift=core, gap=gap, marks=marks, predicted=pred,
                scope='source-compiled schedule for the pin-registered IDX tiles; exact timeline proven by '
                      'rtl/test/hbm_idx_static/run_scheduled.sh (calendar SRAM + parent, full shape)')
    return prog, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--pins', choices=sorted(PIN_TABLES), default='registered')
    ap.add_argument('--gap', type=int, default=100)
    ap.add_argument('--score-chain', type=int, default=0,
                    help='IDX-SCORE chained cluster: scorer outputs this many edges later (ot_hbm_idx_score_cluster: 4)')
    ap.add_argument('--link-pipe', type=int, default=None,
                    help='link core output latency (default: the pin table: registered 5 = ot_hbm_idx_topk_link_static_p, '
                         'none 0); 0 = the historical ot_hbm_idx_topk_link_static (OT_IDX_HIST_LINK)')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    p, meta = compile_program(a.pins, a.gap, a.score_chain, a.link_pipe)
    rows = [sum((p[i + j] if i + j < len(p) else 0) << (32 * j) for j in range(8)) for i in range(0, len(p), 8)]
    meta['rows'] = len(rows)
    (out / 'calendar.hex').write_text(''.join(f'{r:064x}\n' for r in rows))
    (out / 'calendar_instructions.hex').write_text(''.join(f'{r:08x}\n' for r in p))
    (out / 'calendar.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(json.dumps(dict(length=meta['length'], pins=a.pins, gap=a.gap, shift=meta['calendar_shift'],
                          predicted=meta['predicted'])))


if __name__ == '__main__':
    main()
