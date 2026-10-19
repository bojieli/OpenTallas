#!/usr/bin/env python3
"""HBM-NEXT-UNITS-IDX 2026-10-19: N-row IDX.INDEX calendar (HGI-1R) for ot_hnx_idx_calendar_rows.

    hnx_idx_rows_calendar.py OUT [--rgap G]

Takes the d4g single-row INDEX microprogram (tools/hbm_idx_static_calendar.py compile_program, registered pins, GAP 100,
UNCHANGED) and derives ONE row frame that the rows issuer launches every `pitch` edges:
  * the selector frame clear (op 1, d4g: instruction 0) moves to 2 edges before the key-scan start (op 3), so the
    selector is busy only from its own scan to its last compaction slot (it is the per-row bottleneck);
  * a link clear ([5] & [4], decoded by ot_hnx_idx_scheduled_static) is placed 8 edges before the first compaction
    slot (op 6): after the previous row's last link emit, before this row's first link ingest.
The minimum pitch (= the MEASURABLE row II) is the largest busy span of a unit that one row must own exclusively
(selector, link, scorer array, query unit / operand reader) and the smallest shift with no field-class collision between
two overlapping rows (index/flag, selector, link classes = the hardware collision check); pitch >= ceil(F / 2) (two
issue streams). Writes OUT/frame (row frame) and OUT/d4g (the unchanged d4g programme, for the N = 1 equivalence run).
"""
import argparse, json, math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hbm_idx_static_calendar as CAL  # noqa: E402  (d4g compiler, read-only)

f = lambda w, lo, nb: (w >> lo) & ((1 << nb) - 1)
CLS = dict(idx=lambda w: f(w, 28, 4) != 0, sel=lambda w: f(w, 6, 14) != 0, link=lambda w: f(w, 0, 6) != 0)


def write(d, prog, meta):
    d.mkdir(parents=True, exist_ok=True)
    (d / 'calendar_instructions.hex').write_text(''.join(f'{w:08x}\n' for w in prog))
    (d / 'calendar.json').write_text(json.dumps(meta, indent=1) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--rgap', type=int, default=0)
    a = ap.parse_args()
    out = Path(a.out)
    prog, meta = CAL.compile_program('registered', 100, 0)
    write(out / 'd4g', prog, meta)
    sh, marks, F = meta['calendar_shift'], meta['marks'], len(prog)
    w = list(prog)
    e1 = sh['sel']                                         # d4g selector frame clear (historical edge 0)
    assert f(w[e1], 16, 4) == 1, hex(w[e1])
    w[e1] &= ~(15 << 16)
    scan = marks['scan_start'] + sh['sel']
    assert f(w[scan], 16, 4) == 3
    n1 = scan - 2
    assert f(w[n1], 6, 14) == 0
    w[n1] |= 1 << 16
    sel_edges = [t for t in range(F) if CLS['sel'](w[t])]
    op6 = [t for t in range(F) if f(w[t], 16, 4) == 6]
    link_edges = [t for t in range(F) if CLS['link'](w[t])]
    c = op6[0] - 8
    assert f(w[c], 0, 6) == 0
    w[c] |= (1 << 5) | (1 << 4)
    heads = [t for t in range(F) if f(w[t], 29, 1)]
    beats = [t for t in range(F) if f(w[t], 28, 1)]
    vmq = [t for t in range(F) if f(w[t], 30, 2)]
    spans = dict(
        selector=(n1, sel_edges[-1] + 4),                  # + the selector's compaction drain into the link
        link=(c, link_edges[-1]),
        array=(heads[0], beats[-1]),                       # next row's query load after this row's last key beat
        query_unit=(0, heads[-1] + 16),                    # row_start (seen clear) after this row's last head emit
        operand=(vmq[0], vmq[-1]),
    )
    p = max(max(b - x + 1 for x, b in spans.values()), math.ceil(F / 2))
    bind = max(spans, key=lambda k: spans[k][1] - spans[k][0] + 1)

    def collide(p):
        return [t for t in range(p, F) if any(CLS[k](w[t]) and CLS[k](w[t - p]) for k in CLS)]
    while collide(p):
        p += 1
    assert not collide(p) and 2 * p >= F
    pitch = p + a.rgap
    pred = meta['predicted']
    fm = dict(meta)
    fm.update(scope='HBM-NEXT-UNITS-IDX row frame (ot_hnx_idx_calendar_rows): d4g programme with the selector clear moved '
                    'to scan_start - 2 and a link clear before the first compaction slot',
              frame_length=F, row_ii=p, rgap=a.rgap, pitch=pitch, binding_unit=bind,
              unit_spans={k: dict(first=x, last=b, span=b - x + 1) for k, (x, b) in spans.items()},
              selector_clear_instruction=n1, link_clear_instruction=c,
              first_key_edge_row0=pred['first_key_instruction'] + 3, first_tx_edge_row0=pred['first_tx_from_instruction0'] + 3,
              cycles_formula='record edges(N) = (N - 1) x pitch + last TX of row 0 (measured by tb_hnx_idx_rows)')
    write(out / 'frame', w, fm)
    print(json.dumps(dict(F=F, row_ii=p, pitch=pitch, binding=bind, spans=fm['unit_spans'],
                          key0=fm['first_key_edge_row0'], tx0=fm['first_tx_edge_row0'])))


if __name__ == '__main__':
    main()
