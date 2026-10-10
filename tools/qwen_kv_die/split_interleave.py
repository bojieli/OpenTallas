#!/usr/bin/env python3
"""kv-die 2026-10-09 (review-1149 KV13): can compiler-side interleaving hide the split issue gap?

Decodes one layer program image (program.hex of the token-exact L0-L2 chain image, img_p1/L<n>-d<d>) and classifies every
issue transition of the in-order controller:
  dep      the instruction waits on the previous unit's completion (barrier / wait_su / wait_me) or chases its progress:
           the issue gap is a data dependency; no reorder can fill it without changing the dataflow
  same     back-to-back on the SAME unit with no wait (the stream unit's pipelined same-class issue): the 4-edge RT mask
           of the split shell is paid in full here; a reorder helps only if an independent op of the OTHER unit exists
  cross    the other unit, no wait: already overlapped by the compiler
For every 'same' transition it searches the program for an op of the other unit that has no RAW / WAR / WAW hazard
with the ops it would jump over (VM footprints from base / stride / count, conservative) and no wait flag.

    python3 tools/qwen_kv_die/split_interleave.py --program DIR/program.hex --out results/.../split_interleave.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_isa as I                       # noqa: E402
import hdc_qwen_fullshape_isa as QI       # noqa: E402

UNIT = {v: k[5:] for k, v in vars(I).items() if k.startswith('UNIT_')}


def foot(d, p, nout, nin):
    base, so, si = d.get(p + '_base', 0), d.get(p + '_so', 0), d.get(p + '_si', 0)
    hi = base + max(0, nout - 1) * so + max(0, nin - 1) * si + 1
    return (base, hi)


def fps(d):
    u = UNIT.get(d['unit'])
    if u == 'SU':
        no, ni = d.get('su_nout', 1) or 1, d.get('su_nin', 1) or 1
        rd = [foot(d, x, no, ni) for x in ('a', 'b', 'c') if d.get(x + '_base') or d.get(x + '_si')]
        wr = [foot(d, 'd', no, 1 if not d.get('d_si') else ni)] + ([foot(d, 'r', no, 1)] if d.get('red') else [])
        return rd, wr
    if u == 'ME':
        no = d.get('me_nout', 1) or 1
        rd = [(d.get('me_xbase', 0), d.get('me_xbase', 0) + 4096 * max(1, d.get('me_k', 1)))]
        wr = [(d.get('me_obase', 0), d.get('me_obase', 0) + no * max(1, d.get('me_ots', 1)))]
        return rd, wr
    return [], []


def ov(a, b):
    return any(x0 < y1 and y0 < x1 for x0, x1 in a for y0, y1 in b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--program', type=Path, required=True)
    ap.add_argument('--out', type=Path)
    a = ap.parse_args()
    words = [int(x, 16) for x in a.program.read_text().split() if x.strip()]
    ins = [QI.decode_instruction(w) for w in words]
    rows, cand = [], []
    for n, d in enumerate(ins):
        u = UNIT.get(d['unit'])
        waits = [k for k in ('barrier', 'wait_su', 'wait_me', 'chase') if d.get(k)]
        prev = UNIT.get(ins[n - 1]['unit']) if n else None
        kind = 'start' if n == 0 else ('end' if u == 'END' else 'dep' if waits else
                                       'same' if u == prev else 'cross')
        rows.append(dict(n=n, unit=u, waits=waits, kind=kind))
        if kind == 'same':
            other = 'ME' if u == 'SU' else 'SU'
            found = None
            for m in range(n + 1, len(ins)):
                e = ins[m]
                if UNIT.get(e['unit']) == 'END' or e.get('barrier'):
                    break
                if UNIT.get(e['unit']) != other:
                    continue
                if any(e.get(k) for k in ('wait_su', 'wait_me', 'chase')):
                    continue
                er, ew = fps(e)
                ok = True
                for j in range(n, m):
                    jr, jw = fps(ins[j])
                    if ov(er, jw) or ov(ew, jr) or ov(ew, jw):
                        ok = False
                        break
                if ok:
                    found = m
                    break
            cand.append(dict(at=n, unit=u, independent_other_unit_op=found))
    counts = {k: sum(1 for r in rows if r['kind'] == k) for k in ('dep', 'same', 'cross')}
    movable = [c for c in cand if c['independent_other_unit_op'] is not None]
    out = dict(schema='opentallas.qwen-split-interleave.v1', program=str(a.program), instructions=len(ins),
               transitions=counts, same_unit_transitions=cand, movable=len(movable), rows=rows,
               verdict=(f"{len(movable)} of {counts['same']} same-unit back-to-back issues have an independent op of the "
                        f"other unit to interleave; {counts['dep']} transitions are data dependencies (barrier / wait / "
                        f"chase) that no reorder can fill"))
    if a.out:
        a.out.write_text(json.dumps(out, indent=1) + '\n')
    print(out['verdict'])
    print(json.dumps(counts), [c['at'] for c in cand])


if __name__ == '__main__':
    main()
