#!/usr/bin/env python3
"""HBM-NEXT-UNITS-IDXN 2026-10-19: IDX.INDEX row frame + row II for ONE key stream (ot_hnx_idxn_calendar / _parent).

    hnx_idxn_calendar.py OUT [--gap G] [--g2 G2] [--sel S] [--streams K] [--pitch P] [--score-chain C]

--score-chain C (IDXQ 2026-10-19): the d4g compiler's scorer->selector chain (0 = the IDXN bench's score_static; 8 = the
chained 16-leaf cluster; 14 = the quad form: cluster 8 + quarter pins 2 + XQ tree 4). Default 0 = unchanged output.

Takes the d4g single-row INDEX microprogram (tools/hbm_idx_static_calendar.py compile_program, registered pins,
UNCHANGED fields and latencies) with the head-emit -> first-key gap G (d4g 100; the scorer needs >= 3: engine settle
3 edges after the last ql_v, the hslice writes its query 2 edges after the beat) and derives ONE row frame that the
issuer launches every `pitch` edges, rows PIPELINED (up to K = 8 in flight):
  * selector frame clear (op 1) + histogram clear (op 3) move to 3 / 2 edges before the first ingest (op 2): the
    selector is busy only from its own ingest to its last compaction slot (row r runs on selector r mod S);
  * a link row clear ([5] & [4]) 8 edges before the first compaction slot (op 6) opens the row's link slot.
Row II = the smallest pitch p with, for every pair of overlapping rows (j = 1 .. K-1, j p < F):
  * no collision in any routed class (OPR, QEM, KEY, LIN, LOUT; SEL only between rows on one selector, j mod S = 0);
  * exclusive spans: scorer array = first head emit .. last key beat + G2 (the hslices hold ONE query: the next row's
    head emits may only follow this row's last key by >= G2 issue slots: the head weight is used 28 edges after the
    key at the slice and the new one lands 2 edges after its beat, beats reach the scorer 3 edges before an emitted
    head would -> G2 >= 23; ot_hnx_idxn_calendar faults below G2MIN = 23); query unit (row start after the last emit + 16);
    operand reader (+12: last block returned before the next weight slot); link ingest (compaction, + drain);
    selector (op 1 .. last selector slot + 4) between rows j = S apart; K x p >= F + 3 (a stream is free again).
Writes OUT/frame (row frame, calendar.json with the spans / II / predicted first key and TX edges) and OUT/d4g (the
unchanged d4g programme, gap 100, for the N = 1 equivalence run).
"""
import argparse, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_idx_static_calendar as CAL  # noqa: E402  (d4g compiler, read-only)

f = lambda w, lo, nb: (w >> lo) & ((1 << nb) - 1)
CLS = dict(opr=lambda w: f(w, 30, 2) != 0, qem=lambda w: f(w, 29, 1) != 0, key=lambda w: f(w, 28, 1) != 0,
           lin=lambda w: f(w, 5, 1) != 0, lout=lambda w: f(w, 4, 1) != 0 and f(w, 5, 1) == 0)
SEL = lambda w: f(w, 6, 14) != 0


def write(d, prog, meta):
    d.mkdir(parents=True, exist_ok=True)
    (d / 'calendar_instructions.hex').write_text(''.join(f'{w:08x}\n' for w in prog))
    (d / 'calendar.json').write_text(json.dumps(meta, indent=1) + '\n')


def frame(gap, chain=0):
    prog, meta = CAL.compile_program('registered', gap, chain)
    sh, F = meta['calendar_shift'], len(prog)
    w = list(prog)
    e1 = sh['sel']
    assert f(w[e1], 16, 4) == 1, hex(w[e1])
    w[e1] &= ~(15 << 16)
    scan = meta['marks']['scan_start'] + sh['sel']
    assert f(w[scan], 16, 4) == 3 and f(w[scan], 6, 14) == 3 << 10
    w[scan] &= ~(15 << 16)
    op2 = [t for t in range(F) if f(w[t], 16, 4) == 2]
    for t, op in ((op2[0] - 3, 1), (op2[0] - 2, 3)):
        assert not SEL(w[t]), t
        w[t] |= op << 16
    op6 = [t for t in range(F) if f(w[t], 16, 4) == 6]
    c = op6[0] - 8
    assert f(w[c], 0, 6) == 0
    w[c] |= (1 << 5) | (1 << 4)
    return w, meta, dict(sel_clear=op2[0] - 3, hist_clear=op2[0] - 2, link_clear=c)


def spans_of(w, g2):
    F = len(w)
    ev = lambda lo, nb: [t for t in range(F) if f(w[t], lo, nb)]
    heads, beats, vmq = ev(29, 1), ev(28, 1), ev(30, 2)
    sel = [t for t in range(F) if SEL(w[t])]
    op6 = [t for t in range(F) if f(w[t], 16, 4) == 6]
    return dict(
        array=(heads[0], beats[-1] + g2 - 1),              # next row's first head emit >= this row's last key + G2
        query_unit=(0, heads[-1] + 16),                    # row_start (seen clear) after this row's last head emit
        operand=(vmq[0], vmq[-1] + 12),                    # the next weight slot after this row's last block returned
        link_ingest=(op6[0], op6[-1] + 4),                 # selector compaction -> link (one ingesting row)
    ), (sel[0], sel[-1] + 4)


def min_pitch(w, g2, S, K, floor=1):
    F = len(w)
    ex, sel_span = spans_of(w, g2)
    lo = max([floor] + [b - a + 1 for a, b in ex.values()] + [math.ceil((F + 3) / K)])

    def bad(p):
        out = []
        for j in range(1, K):
            d = j * p
            if d >= F:
                break
            for t in range(d, F):
                a, b = w[t], w[t - d]
                for k, c in CLS.items():
                    if c(a) and c(b):
                        out.append((j, t, k))
                if j % S == 0 and SEL(a) and SEL(b):
                    out.append((j, t, 'sel'))
            if j % S == 0 and d < sel_span[1] - sel_span[0] + 1:
                out.append((j, None, 'selector_span'))
        return out
    p = lo
    while bad(p):
        p += 1
    return p, bad, ex, sel_span


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--gap', type=int, default=4)
    ap.add_argument('--g2', type=int, default=23)
    ap.add_argument('--sel', type=int, default=4)
    ap.add_argument('--streams', type=int, default=8)
    ap.add_argument('--score-chain', type=int, default=0)
    ap.add_argument('--pitch', type=int, default=0, help='force this pitch (bench mutants), 0 = the compiled row II')
    a = ap.parse_args()
    out = Path(a.out)
    prog, meta = CAL.compile_program('registered', 100, a.score_chain)
    write(out / 'd4g', prog, meta)
    w, fm, moved = frame(a.gap, a.score_chain)
    F = len(w)
    ii, bad, ex, sel_span = min_pitch(w, a.g2, a.sel, a.streams)
    pitch = a.pitch or ii
    spans = {k: dict(first=x, last=b, span=b - x + 1) for k, (x, b) in ex.items()}
    spans['selector'] = dict(first=sel_span[0], last=sel_span[1], span=sel_span[1] - sel_span[0] + 1,
                             per_row=math.ceil((sel_span[1] - sel_span[0] + 1) / a.sel))
    bind = max(list(ex) + ['selector'], key=lambda k: spans[k]['span'] if k != 'selector' else spans[k]['per_row'])
    pred = fm['predicted']
    fm.update(scope='HBM-NEXT-UNITS-IDXN row frame (ot_hnx_idxn_calendar): d4g programme at gap G, selector clears '
                    'before the first ingest, link row clear before the first compaction; rows pipelined, ONE key stream',
              frame_length=F, score_chain=a.score_chain, gap=a.gap, g2=a.g2, selectors=a.sel, streams=a.streams, row_ii=ii, pitch=pitch,
              binding_unit=bind, unit_spans=spans, moved=moved, collisions_at_pitch=len(bad(pitch)),
              first_key_edge_row0=pred['first_key_instruction'] + 3, first_tx_edge_row0=pred['first_tx_from_instruction0'] + 3,
              cycles_formula='record edges(N) = (N - 1) x pitch + last TX of row 0 (measured by tb_hnx_idxn_rows)')
    write(out / 'frame', w, fm)
    print(json.dumps(dict(F=F, gap=a.gap, g2=a.g2, row_ii=ii, pitch=pitch, binding=bind, spans=spans,
                          collisions_at_pitch=fm['collisions_at_pitch'], key0=fm['first_key_edge_row0'], tx0=fm['first_tx_edge_row0'])))


if __name__ == '__main__':
    main()
