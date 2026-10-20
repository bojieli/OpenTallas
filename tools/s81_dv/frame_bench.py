#!/usr/bin/env python3
"""S81-DV frame bench (S81U-3F, 2026-10-17): x-chain words in -> return root words out, exact against the golden.

ONE frame master (col_h9 / col_h10 from tools/s81_dv/frame_wrap.py) is driven exactly as the die drives it: the x-chain
word of ot_s81sl_slice ({xw[1100:565], xw[0], marker, xw[564:0], marker}) whose xw is the packed static lane word of
dsfd_pq_lx (+DSFD_PQ_STATIC_X2 +DSFD_PQ_HAS_BF_X2, the die's lane encoder) fed by the existing PQ field spine
ot_v41_spine_pq_static_w17w10 (PQ 1: cfg broadcast, go, the static x stream from its phase / stream ROMs, the x read
from a vector-memory model and quantised in the spine).  The frame's ret (dsfd_cfifo_crs rd) is captured every edge.

CONTENT (gen): one FP8 phase placed by the existing image writer tools/v41_die_images_w17w10.add_phase on a Field of
the frame's q pairs only (NP 16, 12 active = the frame's 12 q elements in pair order; FAST / PP as the bound element),
weights synthetic E4M3 codes and UE8M0 block exponents (seeded), x seeded FP32.  Images: the element macros
(<INSTANCE>_e<k>{,b}_<parity>.viamap.hex), every pair's seven cfg ROMs in the il7 layout of the bound sequencers
(LAYOUT 1: word w of phase p in bank w % 7 at row 4p + w // 7; tools/s81_static_control/field_cfg7_image.encode_bank),
BF pairs with their all-zero (empty) programme, spine_phase.hex / spine_stream.hex, vm.hex.

GOLDEN (check): golden_phase (hdc_golden_v41 R-ARITH chunk8, the image writer's own golden) gives every row's FP32
accumulator; the segment values are G.csum over each golden-aligned segment's blocks, and golden_row(segments) must
equal the accumulator (the segment model is checked against the golden first).  Every root word the frame emits
({e, d32, t32, v}) must carry a tag of a real row and the EXACT value golden_node(segments, lo, k, n) of its normalised
tag, e = 0; per row the emitted words must tile [0, nseg) exactly once (no lost, duplicated or overlapping partial);
xo must equal x one edge later on every edge; the frame status must show no fault.

    frame_bench.py gen   --master col_h9 --out DIR [--seed S] [--rows R] [--K K]
    frame_bench.py check --dir DIR --log RUN.LOG              exit 0 = PASS
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/s81'))
sys.path.insert(0, str(ROOT / 'tools/s81_static_control'))
import hdc_golden_v41 as G  # noqa: E402
import v41_die_images_w17w10 as I  # noqa: E402
import v41_rom_ksplit_bankmap as S  # noqa: E402
from field_cfg7_image import encode_bank, decode_bank  # noqa: E402
from static_return_calendar import _f, norm, fadd  # noqa: E402

INST = 'f'
PHW = 10
CW = 25


class SynMat(I.Mat):
    """synthetic FP8 matrix slice (same fields the image writer and golden_phase read from a checkpoint Mat)"""

    def __init__(self, rng, name, rows, K):
        self.name, self.fmt, self.rows, self.K, self.r0, self.k0, self.phase = name, 'fp8', rows, K, 0, 0, 'syn'
        codes = rng.integers(0, 256, size=(rows, K), dtype=np.uint8)
        codes[(codes & 0x7F) == 0x7F] = 0x3C                         # no E4M3 NaN codes
        self.codes = codes
        self.exp = rng.integers(120, 132, size=(rows, K // 32)).astype(np.uint8)
        self.w = G.Q8(G.E4M3[self.codes].astype(np.float64), self.exp.astype(np.int64) - 127)


def frame_pairs(master):
    """frame-local pair index -> kind, from the emitted wrapper (q = ot_v41_rom_elem_q_qxpq_w10 u_e<k>)"""
    txt = (ROOT / f'rtl/dsrom_sys/s81_dv/frame/{master}.sv').read_text()
    q = sorted(int(m.group(1)) for m in re.finditer(r'^\s*ot_v41_rom_elem_q_qxpq_w10 #\(.*?\) u_e(\d+) ', txt, re.M))
    bf = sorted(int(m.group(1)) for m in re.finditer(r'^\s*dsfd_bf_front_(?:static|roots) #\(.*?\) u_e(\d+) ', txt, re.M))
    assert q and bf and not set(q) & set(bf) and sorted(q + bf) == list(range(len(q) + len(bf))), (q, bf)
    return q, bf


def cmd_gen(a):
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    q, bf = frame_pairs(a.master)
    if a.only is not None:         # one active q element (frame pair a.only) on Field slot 0
        assert a.only in q, (a.only, q)
        qa = [a.only]
    else:
        qa = q
    field = I.Field(16, 1, 0, depth=8192, active=len(qa), pp=True, fast=True)
    plan = None
    if a.plan:                     # D2: the frame return legaliser places the K-split rows (one hw slot per element)
        assert a.only is None
        nsr, rem = divmod(len(qa), a.nseg)
        assert rem == 0, ('q pairs must be a multiple of nseg', len(qa), a.nseg)
        a.rows, a.mats = 2 * nsr, 1
    mats = [SynMat(rng, f'syn{i}', a.rows, a.K) for i in range(a.mats)]
    x = (rng.standard_normal(a.K) * np.exp2(rng.integers(-3, 4, size=a.K))).astype(np.float32)
    if a.plan:
        import frame_return_plan as P
        plan = P.plan_phase(a.master, qa, mats[0], x, a.nseg, seed=a.seed, iters=a.iters, land_e=a.land_e, frame_schedule=a.frame_schedule)
        orig = I._place
        I._place = P.place_fn(plan['assign_slots'], a.nseg)
        try:
            ph = I.add_phase(field, mats)
        finally:
            I._place = orig
        assert field.stream[ph['sbase']:ph['sbase'] + ph['nbeat']] == plan['stream'], 'stream differs from the plan'
        plan.pop('stream')
    else:
        ph = I.add_phase(field, mats)
    gold = I.golden_phase(mats, x)
    # ---- element ROM images (frame INSTANCE "f": element f_e<k>, macros f_e<k>{,b}_<parity>)
    tmp = out / 'field'
    I.write_field(field, tmp, PHW, flat_viamaps=True)
    slot_of = {k: s for s, k in enumerate(qa)}
    for k, s in slot_of.items():
        for mb in ('', 'b'):
            for par in (0, 1):
                src = tmp / f'e{s}{mb}_{par}.viamap.hex'
                (out / f'{INST}_e{k}{mb}_{par}.viamap.hex').write_text(src.read_text())
    # ---- cfg ROMs (il7, phase 0 only; BF pairs and unused phases zero)
    for k in q + bf:
        words = field.cfg[0][slot_of[k]] if k in slot_of else [0] * CW
        assert len(words) == CW
        banked = [[0] * 4096 for _ in range(7)]
        for w_, v in enumerate(words):
            banked[w_ % 7][w_ // 7] = v
        for j in range(7):
            phys = encode_bank(banked[j])
            assert decode_bank(phys)[:4] == banked[j][:4]
            (out / f'{INST}_c{k}_{j}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in phys))
    # ---- spine ROMs + vector memory (x at 0)
    for f in ('spine_phase.hex', 'spine_stream.hex'):
        (out / f).write_text((tmp / f).read_text())
    vm = [int(struct.unpack('<I', struct.pack('<f', float(v)))[0]) for v in x]
    (out / 'vm.hex').write_text(''.join(f'{v:08x}\n' for v in vm))
    # ---- golden segments
    rows = {}
    off = 0
    for mi, m in enumerate(mats):
        s = ph['matrices'][mi]['split']
        segs = S.segments(m.K, s)
        xq, xe = G.quant_fp8(x)
        blocks = np.stack([np.ldexp((m.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                                    m.w.e[:, b] + xe[b]).astype(G.F) for b in range(m.K // 32)], axis=-1)
        for r in range(m.rows):
            vals = [int(G.bits(G.csum(blocks[r, e0 // 32:(e0 + el) // 32]))) for e0, el in segs]
            rows[off + r] = dict(vals=vals, acc=gold[off + r][0])
        off += m.rows
    meta = dict(master=a.master, seed=a.seed, only=a.only, K=a.K, rows_per_mat=a.rows, mats=a.mats, q_pairs=q, bf_pairs=bf,
                phase=dict((k, v) for k, v in ph.items() if k != 'matrices'), matrices=ph['matrices'],
                nrows=off, ops=off, rows={str(k): v for k, v in rows.items()},
                cycles=a.cycles, plan=plan)
    if plan:
        for r, v in rows.items():          # the plan's leaf values are the same golden segment sums
            assert plan['rows_vals'][str(r)] == v['vals'], r
        (out / 'return_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'T').write_text(f'{a.cycles}\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={a.cycles} +K={a.K} +OPS={off}\n')
    segn = sorted({len(v['vals']) for v in rows.values()})
    print(f'GEN {a.master} only={a.only} rows={off} K={a.K} segments/row={segn} q_pairs={len(q)} bf_pairs={len(bf)} '
          f'beats={ph["nbeat"]} max_segments_per_pair={ph["segments_per_pair_max"]}')


def golden_node(vals, lo, k, n):
    if k == 0:
        return vals[lo], 0
    h = 1 << (k - 1)
    l, el = golden_node(vals, lo, k - 1, n)
    if lo + h >= n:
        return l, el
    r, er = golden_node(vals, lo + h, k - 1, n)
    s, e = fadd(l, r)
    return s, el | er | e


def cmd_check(a):
    d = Path(a.dir)
    meta = json.loads((d / 'meta.json').read_text())
    rows = {int(k): v for k, v in meta['rows'].items()}
    errs = []
    # the segment model against the golden accumulator first
    for r, v in rows.items():
        n = len(v['vals'])
        k = max(0, (n - 1).bit_length())
        g, e = golden_node(v['vals'], 0, k, n)
        if g != v['acc'] or e:
            errs.append(f'SEGMENT_MODEL row {r} {g:08x} != acc {v["acc"]:08x}')
    log = Path(a.log).read_text()
    words, cov, tags = [], {}, set()
    for m in re.finditer(r'^RET (\d+) ([0-9a-f]+)$', log, re.M):
        edge, w = int(m.group(1)), int(m.group(2), 16)
        e_, d_, t_, v_ = (w >> 65) & 1, (w >> 33) & 0xFFFFFFFF, (w >> 1) & 0xFFFFFFFF, w & 1
        assert v_ == 1
        words.append((edge, t_, d_, e_))
    for edge, t_, d_, e_ in words:
        nt = norm(t_)
        row19, lo, k, n = _f(nt)
        pos, optag, row = row19 >> 16, (row19 >> 14) & 3, row19 & 0x3FFF     # row [15:14] = the op's PQ tag
        tags.add(optag)
        if pos or row not in rows:
            errs.append(f'BAD_TAG edge {edge} t {t_:08x}')
            continue
        vals = rows[row]['vals']
        if n != len(vals) or lo + (1 << k) > max(n, 1 << k) or lo % (1 << k):
            errs.append(f'BAD_SHAPE edge {edge} row {row} lo {lo} k {k} n {n} nseg {len(vals)}')
            continue
        g, ge = golden_node(vals, lo, k, n)
        if d_ != g or e_ != ge:
            errs.append(f'MISMATCH edge {edge} row {row} lo {lo} k {k} n {n} got {d_:08x}/{e_} want {g:08x}/{ge}')
        for s in range(lo, min(lo + (1 << k), n)):
            cov.setdefault(row, []).append(s)
    for r, v in rows.items():
        c = sorted(cov.get(r, []))
        if c != list(range(len(v['vals']))):
            errs.append(f'COVERAGE row {r} segments {c} of {len(v["vals"])}')
    if len(tags) > 1:
        errs.append(f'OP_TAGS {sorted(tags)} (one op: one tag)')
    plan = meta.get('plan')
    if plan:                       # cycle-exact against the compiler's return calendar (tools/s81_dv/frame_return_plan.py)
        if plan['faults']:
            errs.append(f'PLAN_FAULTS {plan["faults"]} (the legaliser found no fault-free placement)')
        want = [(e, _f(norm(t))[0] & 0x3FFF, _f(norm(t))[1:], d, er) for e, t, d, er in plan['ret']]
        got = [(e, _f(norm(t))[0] & 0x3FFF, _f(norm(t))[1:], d, er) for e, t, d, er in words]
        if want != got:
            errs.append(f'PLAN_MISMATCH predicted {len(want)} ret words, got {len(got)}; first diff '
                        f'{next(((w, g) for w, g in zip(want, got) if w != g), (want[len(got):len(got) + 1], got[len(want):len(want) + 1]))}')
    xo_bad = re.findall(r'^XO_MISMATCH .*$', log, re.M)
    errs += xo_bad[:4]
    flt = re.findall(r'^FAULT .*$', log, re.M)
    errs += flt[:4]
    done = re.search(r'^END edges=(\d+) ret_words=(\d+) xo_checked=(\d+) fault=(\d+)', log, re.M)
    if not done:
        errs.append('NO_END')
    complete = sum(1 for _, t_, _, _ in words if (_f(norm(t_))[1] == 0 and (1 << _f(norm(t_))[2]) >= _f(norm(t_))[3]))
    summ = dict(words=len(words), rows=len(rows), complete_rows_at_root=complete, plan_exact=bool(plan) and not
                any(e.startswith('PLAN_') for e in errs),
                partial_words=len(words) - complete, errors=len(errs),
                end=done.group(0) if done else None)
    (d / 'check.json').write_text(json.dumps(dict(summary=summ, errors=errs[:200]), indent=1) + '\n')
    for e in errs[:12]:
        print(e)
    if errs:
        print(f'FRAME_BENCH FAIL {meta["master"]} errors={len(errs)} words={len(words)} rows={len(rows)}')
        return 1
    print(f'FRAME_BENCH PASS {meta["master"]} rows={len(rows)} words={len(words)} complete_at_root={complete} '
          f'partials={len(words) - complete} {done.group(0)}')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--master', default='col_h9')
    g.add_argument('--out', required=True)
    g.add_argument('--seed', type=int, default=1)
    g.add_argument('--rows', type=int, default=8)
    g.add_argument('--mats', type=int, default=1)
    g.add_argument('--K', type=int, default=2048)
    g.add_argument('--cycles', type=int, default=3000)
    g.add_argument('--only', type=int, help='frame pair index of the one active q element (else all 12 share the phase)')
    g.add_argument('--plan', action='store_true', help='all q elements, one K-split phase placed by the frame return '
                   'legaliser (tools/s81_dv/frame_return_plan.py): rows = 2 x pairs / nseg, one segment per element; '
                   'check then requires the ret words to equal the predicted calendar cycle for cycle')
    g.add_argument('--nseg', type=int, default=4)
    g.add_argument('--iters', type=int, default=4000)
    g.add_argument('--land-e', type=int, default=None, help='LANDFIX-SQ/F: plan for the _l4 successor (dsfd_cfifo_crs4) '
                   'with frame lane landing latency E (= the bench strap LK); default: dsfd_cfifo_crs')
    g.add_argument('--frame-schedule', help='source-pinned landed frame station and return topology record')
    c = sp.add_parser('check')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'gen':
        cmd_gen(a)
        return 0
    return cmd_check(a)


if __name__ == '__main__':
    sys.exit(main())
