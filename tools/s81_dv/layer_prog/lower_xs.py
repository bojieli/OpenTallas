#!/usr/bin/env python3
"""LB2-S81/CC-xs (10-18): frame matvec lowering -- per-frame DV ROM images + the frame return plan (+ the slice xs
phase / stream ROM images) for the frame-held matrices of one layer, from the layer fixtures (real checkpoint rows).

SCOPE (this module claims OPS only):  attn.a_proj (wq_a ++ wkv, K 5120, FP8 E4M3 + UE8M0 32x32 blocks).

PLACEMENT (SPEC section 2 "Ownership": the compiler places each matrix's output rows in the frames of the owning slice,
every frame holds rows / 128):  the rank's a_proj rows are the concatenation wq_a[tp rows] ++ wkv[tp rows] (448 rows at
TP4); slice g (= the slice's sid strap, else its die order) holds rows [28 g, 28 g + 28).  The frame return legaliser
(tools/s81_dv/frame_return_plan.py plan_phase) places 2 x pairs / nseg rows per frame; K 5120 has golden-aligned
segment counts 1, 2, 3, 5, 10, 20 only (tools/v41_rom_ksplit_bankmap.segments: chunk groups are powers of two), so
3.5 rows / frame is not placeable; the lowering uses NSEG 5 on 10 of a frame's 12 q elements (2 super rows = 4 rows,
2 rows x 1024 K per element: the same per-element work as 3 or 4 rows) on the slice's first 7 frames (7 x 4 = 28) and
leaves the 8th frame without an a_proj phase (it still forwards the x chain).  The phase stream (x broadcast order) does
not depend on the placement (plan_phase), so all frames of a slice share one stream = the slice xs stream.

ABI (derived from the built RTL of record, not docs):
  * element ROM / cfg ROM images: the image writer tools/v41_die_images_w17w10.add_phase / write_field (FP8 block words
    {exp byte, 32 codes}: tools/rtl_v41_rom_array.Mat.block_word), cfg7 il7 banking LAYOUT 1 (word w of phase p in bank
    w % 7 at row 4 p + w // 7; tools/s81_static_control/field_cfg7_image.encode_bank) read by ot_s81_cfg7_seq(_bfp)
    LAYOUT 1 inside the frame masters (rtl/dsrom_sys/s81_dv/frame/col_h9.sv, col_h10.sv, built by frame_wrap.py).
    Frame image names are per die instance: <die frame inst>_e<k>{,b}_<parity>.viamap.hex, <inst>_c<k>_<bank>.viamap.hex
    (the die must bind .INSTANCE(<die inst>) on every frame: gap G4 of the die, owned by the die lane).
  * return calendar: frame_return_plan.plan_phase (ot_s81_retn_static WIN 2 / RST 1 fixed-slot rule per node,
    tools/s81/static_return_calendar.node), dsfd_cfifo_crs4 landing E = the instance's lk strap (lane k = lk[3k +: 3];
    all four lanes of a die frame carry one K): frame_return_plan.x_shift.
  * slice xs ROMs: ot_s81sl_xs reads the production phase / stream images (rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv:164
    u_phase0 addr {0, ph, 0} = phase word 2 ph; :167-172 ot_s81_pq_stream_rom4_sel + pq_stream0..3 = stream word w in
    ROM w >> 12 row w & 4095), the same spine_phase / spine_stream words the image writer emits (tools/s81_slice/
    xs_program.py loads them that way), via-map encoded (tools/s81_static_control/pq_calendar.viamap).

    lower_xs.py gen   --frame u_f_0L00 --out DIR [--fixtures D] [--mutant swap|shift]   bench vectors of one die frame
    lower_xs.py check --dir DIR --log RUN.LOG                                             frame bench check + fixture
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import struct
import sys
from pathlib import Path

os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
ROOT = Path(__file__).resolve().parents[3]
for p in ('tools', 'tools/s81_dv', 'tools/s81', 'tools/s81_static_control'):
    sys.path.insert(0, str(ROOT / p))

import numpy as np  # noqa: E402
from rtl_v41_rom_array import Mat  # noqa: E402

OPS = [r'^attn\.a_proj$', r'^attn\.(wq_b|wo_a|wo_b|idx\.q|cmp\.wk)$', r'^ffn\.(router|shared_gu|experts_gu|down)$',
       r'^eng\.wkv$']   # the others: xs_place.py (TOK-S81-GAPS/XS)
FIX = Path.home() / 'scratch/layerbench-s81/fixtures/L0'
BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_xs'
NSEG = 5
NPAIRS = 10                     # q elements per frame used by a_proj (2 super rows x NSEG)
ROWS_PER_FRAME = 2 * NPAIRS // NSEG
ROWS_PER_SLICE = 28
CYCLES = 3000
SEED = 1
ITERS = 4000
# element work term of the emission rule (frame_return_plan.emission e0_bench was fitted on 1-unit (512-element) segments,
# 2 rows per element): a 2-unit (1024-element) segment with 2 rows per element emits ELEM_EXTRA edges later.  MEASURED on
# the bench of record (bench_xs base, ot-epyc4 10-18: all 10 ret words exactly +33 vs e0_bench, every relative edge exact);
# per (units per segment, rows per element) class -- other classes need their own measurement (lowering refuses them).
ELEM_EXTRA = {(2, 2): 33}


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ fixture matrices
class FixMat(Mat):
    """rows of a fixture FP8 matrix as the image writer's Mat (codes, raw UE8M0 exp per (row, 32-col block), Q8 w)"""

    def __init__(self, name, codes, sc, rows):
        import hdc_golden_v41 as G
        self.name, self.fmt, self.K, self.r0, self.k0, self.phase = name, 'fp8', codes.shape[1], 0, 0, 'a_proj'
        self.rows = len(rows)
        self.codes = codes[rows]
        self.exp = np.repeat(sc, 32, axis=0)[rows]                        # 32 x 32 blocks -> per row
        self.w = G.Q8(G.E4M3[self.codes].astype(np.float64), self.exp.astype(np.int64) - 127)
        self.src = [(name, int(r)) for r in rows]


def load_fixture(fx):
    fx = Path(fx)
    files = json.loads((fx / 'files.json').read_text())
    meta = json.loads((fx / 'meta.json').read_text())

    def arr(rel):
        f = files[rel]
        return np.fromfile(fx / rel, dtype=np.dtype(f['dtype'])).reshape(f['shape'])
    w = {n: (arr(f'weights/{n}.bin'), arr(f'weights/{n}.scale.bin')) for n in ('wq_a', 'wkv')}
    return dict(meta=meta, x=arr('ops/attn.norm.scale.bin'), a_proj=arr('ops/attn.a_proj.bin'), w=w, files=files)


def a_proj_rows(fx):
    """rank-local a_proj row r -> (tensor, tensor-local row, global a_proj output index)"""
    m = fx['meta']
    (q0, q1), (k0, k1) = m['tp_split']['a_proj.wq_a_rows'][m['rank']], m['tp_split']['a_proj.wkv_rows'][m['rank']]
    nq = fx['w']['wq_a'][0].shape[0]
    assert nq == q1 - q0 and fx['w']['wkv'][0].shape[0] == k1 - k0
    return [('wq_a', r, q0 + r) for r in range(q1 - q0)] + [('wkv', r, 1280 + k0 + r) for r in range(k1 - k0)]


def frame_mats(fx, rows):
    """FixMats (one per tensor touched, row order kept) for the a_proj rows `rows` (rank-local indices)"""
    allr = a_proj_rows(fx)
    sel = [allr[r] for r in rows]
    mats = []
    for name in ('wq_a', 'wkv'):
        rr = [t for n, t, _ in sel if n == name]
        if rr:
            c, s = fx['w'][name]
            mats.append(FixMat(name, c, s, np.array(rr)))
    return mats, [g for _, _, g in sel]


# ------------------------------------------------------------------------------------------------ placement
def slice_index(die, sl):
    s = die.slices()
    if s.get(sl, {}).get('sid') is not None:
        return s[sl]['sid']
    return sorted(s).index(sl)


def placement(die, sl):
    frames = die.frames_of(sl)
    g = slice_index(die, sl)
    out = []
    for j, f in enumerate(frames):
        r0 = ROWS_PER_SLICE * g + ROWS_PER_FRAME * j
        rows = list(range(r0, r0 + ROWS_PER_FRAME)) if ROWS_PER_FRAME * (j + 1) <= ROWS_PER_SLICE else []
        out.append(dict(frame=f, master=die.inst[f]['master'], lk=die.strap(f, 'lk'), rows=rows))
    return g, out


def base_master(m):
    return re.sub(r'(_MX)?_l4$', '', m)


def land_e(lk):
    ks = {(lk >> (3 * k)) & 7 for k in range(4)}
    assert len(ks) == 1, f'one landing E per frame expected, lk {lk:03x}'
    return ks.pop()


# ------------------------------------------------------------------------------------------------ one frame programme
def frame_programme(master, lk, mats, x, seed=SEED, iters=ITERS, pairs=None):
    """legalise + place one a_proj phase on one frame (field phase 0); returns (field, ph, plan, pairs)"""
    import frame_bench as B
    import frame_return_plan as P
    import v41_die_images_w17w10 as I
    import v41_rom_ksplit_bankmap as S
    q, _bf = B.frame_pairs(base_master(master))
    assert len(mats) == 1, 'a frame phase mixing wq_a and wkv rows: plan_phase takes one matrix (not needed at 28 / slice)'
    best = None
    for cand in ([pairs] if pairs else [q[:NPAIRS], q[len(q) - NPAIRS:], q[1:1 + NPAIRS]]):
        plan = P.plan_phase(base_master(master), cand, mats[0], x, NSEG, seed=seed, iters=iters, land_e=land_e(lk))
        key = (plan['faults'], plan['ret_words'])
        if best is None or key < best[0]:
            best = (key, cand, plan)
        if plan['faults'] == 0 and pairs is None:
            break
    _, qa, plan = best
    seg_units = {S.unit_range('fp8', a0, el)[1] - S.unit_range('fp8', a0, el)[0] for a0, el in S.segments(mats[0].K, NSEG)}
    cls = (seg_units.pop(), 2)
    assert not seg_units and cls in ELEM_EXTRA, ('no measured element-work term for segment class', cls)
    x_ = ELEM_EXTRA[cls]
    plan['ret'] = [[w_[0] + x_] + list(w_[1:]) for w_ in plan['ret']]
    plan['emission'] = dict(plan['emission'], elem_extra=x_, elem_class=list(cls),
                            edges={k: v + x_ for k, v in plan['emission']['edges'].items()})
    field = I.Field(16, 1, 0, depth=8192, active=len(qa), pp=True, fast=True)
    orig = I._place
    I._place = P.place_fn(plan['assign_slots'], NSEG)
    try:
        ph = I.add_phase(field, mats)
    finally:
        I._place = orig
    assert field.stream[ph['sbase']:ph['sbase'] + ph['nbeat']] == plan['stream'], 'stream differs from the plan'
    return field, ph, plan, qa, q, _bf


def field_images(field, qa, q, bf, inst, out):
    """the frame's ROM images under its die instance name: element via-maps + il7 cfg banks (phase 0)"""
    import v41_die_images_w17w10 as I
    from field_cfg7_image import encode_bank
    out = Path(out)
    tmp = out / '_field'
    I.write_field(field, tmp, 10, flat_viamaps=True)
    slot_of = {k: s for s, k in enumerate(qa)}
    names = []
    for k, s in slot_of.items():
        for mb in ('', 'b'):
            for par in (0, 1):
                (out / f'{inst}_e{k}{mb}_{par}.viamap.hex').write_text((tmp / f'e{s}{mb}_{par}.viamap.hex').read_text())
                names.append(f'{inst}_e{k}{mb}_{par}.viamap.hex')
    for k in q + bf:
        words = field.cfg[0][slot_of[k]] if k in slot_of else [0] * 25
        banked = [[0] * 4096 for _ in range(7)]
        for w_, v in enumerate(words):
            banked[w_ % 7][w_ // 7] = v
        for j in range(7):
            (out / f'{inst}_c{k}_{j}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in encode_bank(banked[j])))
            names.append(f'{inst}_c{k}_{j}.viamap.hex')
    for f in ('spine_phase.hex', 'spine_stream.hex'):
        (out / f).write_text((tmp / f).read_text())
    return names, tmp


def xs_roms(tmp, out):
    """slice xs ROM images (ot_s81sl_xs.sv:164-172): pq_phase0 = phase words, pq_stream0..3 = stream words"""
    from pq_calendar import viamap
    P = [int(v, 16) for v in (Path(tmp) / 'spine_phase.hex').read_text().split()]
    S = [int(v, 16) for v in (Path(tmp) / 'spine_stream.hex').read_text().split()]
    S += [0] * (16384 - len(S))
    out = Path(out)
    (out / 'pq_phase0.viamap.hex').write_text(viamap(P[:4096] + [0] * (4096 - min(4096, len(P)))))
    for b in range(4):
        (out / f'pq_stream{b}.viamap.hex').write_text(viamap(S[4096 * b:4096 * (b + 1)]))
    return ['pq_phase0.viamap.hex'] + [f'pq_stream{b}.viamap.hex' for b in range(4)]


# ------------------------------------------------------------------------------------------------ compiler hook
def lower(die, op, ctx):
    if op['op'] != 'attn.a_proj':
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import xs_place
        return xs_place.lower_placed(die, op, ctx)
    sl = ctx['slice']
    g, pl = placement(die, sl)
    insts = [p['frame'] for p in pl] + [sl]
    gap_rest = dict(module='ot_s81sl_xs / ot_s81sl_cap', port='pq_calendar_action / pq_calendar_time ROMs, is_d (GO ph '
                    'np, return fields), cap cfg_d',
                    missing='the frame images, the return calendar and the xs phase / stream ROM images are lowered and '
                    'benched (bench_xs PASS: real L0 wq_a rows 0-3 on die frame u_f_0L00, col_h9_l4 E 5, cycle-exact calendar, fixture BF16; the other 6 a_proj frames of the slice (col_h10_l4 E 2, col_h9_MX_l4 E 1) are legalised fault-free but not benched; ELEM_EXTRA is measured for the (2 units, 2 rows) class only); the slice xs CALENDAR images (the 75-b '
                    'action words: stream requests, VM responses, cfg / launch / retire, tools/s81_slice/xs_program.py '
                    'is bench stimulus for the c26l stages only), the is_d GO word and the cap write-back cfg_d for the '
                    'DV placement are not emitted yet, and no bench drives ot_s81sl_xs into a frame (the frame bench '
                    'drives the frame through the w17w10 spine with the same phase / stream words)')
    rec = dict(unit='frames (cfg7 programme, element ROMs) + frame return plan + slice xs phase / stream ROMs',
               insts=insts, rows=[], templates=[], gunit_rows=[], svc_jobs=[], events=[], bench=BENCH, files={})
    fxd = ctx.get('fixtures')
    if not fxd:
        return dict(rec, status='GAP', gap=dict(module='lower_xs', port='fixtures', missing='no --fixtures: the frame '
                                                'ROM images carry the checkpoint rows of the layer'))
    fx = load_fixture(fxd)
    frames = []
    for p in pl:
        if not p['rows']:
            frames.append(dict(p, phase=None, note='no a_proj rows (28 rows / slice = 7 frames x 4)'))
            continue
        mats, gidx = frame_mats(fx, p['rows'])
        field, ph, plan, qa, q, bf = frame_programme(p['master'], p['lk'], mats, fx['x'])
        frames.append(dict(p, out_index=gidx, pairs=qa, nseg=NSEG, faults=plan['faults'], ret_words=plan['ret_words'],
                           merges=plan['merges'], ret=plan['ret'], placement=plan['placement'],
                           cfg_words={str(k): [f'{w:012x}' for w in field.cfg[0][s]] for s, k in enumerate(qa)},
                           phase=dict((k, v) for k, v in ph.items() if k != 'matrices'),
                           emission=plan['emission']))
    ok = all(f['phase'] is None or f['faults'] == 0 for f in frames)
    rec['files'] = {f'prog/xs/{op["id"]}.json': json.dumps(dict(
        schema='opentallas.s81_dv.xs_lowering.v1', op=op, slice=sl, slice_index=g, nseg=NSEG, rows_per_slice=ROWS_PER_SLICE,
        frames=frames, images='per frame: python3 tools/s81_dv/layer_prog/lower_xs.py gen --frame <inst> --out DIR '
        '(element via-maps + il7 cfg banks named <inst>_*, xs pq_phase0 / pq_stream0..3)'), indent=1) + '\n'}
    if not ok:
        return dict(rec, status='GAP', gap=dict(module='tools/s81_dv/frame_return_plan.py', port='legalise',
                                                missing='return plan faults on ' + ', '.join(f['frame'] for f in frames if f['phase'] and f['faults'])))
    return dict(rec, status='PARTIAL', gap=gap_rest)


# ------------------------------------------------------------------------------------------------ bench vectors
def cmd_gen(a):
    import dv_layer_compile as C
    import hdc_golden_v41 as G
    import v41_rom_ksplit_bankmap as S
    import v41_die_images_w17w10 as I
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    sl = a.slice or next(s for s in sorted(die.slices()) if a.frame in die.frames_of(s))
    g, pl = placement(die, sl)
    p = next(x for x in pl if x['frame'] == a.frame)
    assert p['rows'], f'{a.frame}: no a_proj rows'
    fx = load_fixture(a.fixtures)
    mats, gidx = frame_mats(fx, p['rows'])
    field, ph, plan, qa, q, bf = frame_programme(p['master'], p['lk'], mats, fx['x'])
    names, tmp = field_images(field, qa, q, bf, a.frame, out)
    xsn = xs_roms(tmp, out)
    # the frame bench instantiates the master with INSTANCE "f": the same images under the bench name
    if a.mutant == 'swap':      # wrong placement: the ROM images of two elements holding different rows swapped
        r_of = {d['pair']: d['rows'] for d in plan['placement']}
        e1, e2 = next((u, v) for u in qa for v in qa if u < v and r_of[u] != r_of[v])
    for n in names:
        dst = 'f' + n[len(a.frame):]
        if a.mutant == 'swap':
            dst = re.sub(rf'^f_e({e1}|{e2})(b?_\d)', lambda m: f'f_e{e2 if int(m.group(1)) == e1 else e1}{m.group(2)}', dst)
        (out / dst).write_text((out / n).read_text())
    gold = I.golden_phase(mats, fx['x'])
    rows, off = {}, 0
    xq, xe = G.quant_fp8(fx['x'])
    for mi, m in enumerate(mats):
        segs = S.segments(m.K, ph['matrices'][mi]['split'])
        blocks = np.stack([np.ldexp((m.w.q[:, b * 32:(b + 1) * 32] @ xq[b * 32:(b + 1) * 32]).astype(G.F),
                                    m.w.e[:, b] + xe[b]).astype(G.F) for b in range(m.K // 32)], axis=-1)
        for r in range(m.rows):
            vals = [int(G.bits(G.csum(blocks[r, e0 // 32:(e0 + el) // 32]))) for e0, el in segs]
            rows[off + r] = dict(vals=vals, acc=gold[off + r][0], bf16=gold[off + r][1], src=list(m.src[r]),
                                 out_index=gidx[off + r])
        off += m.rows
    for r, v in rows.items():
        assert plan['rows_vals'][str(r)] == v['vals'], r
    vm = [int(struct.unpack('<I', struct.pack('<f', float(v)))[0]) for v in fx['x']]
    (out / 'vm.hex').write_text(''.join(f'{v:08x}\n' for v in vm))
    plan.pop('stream')
    if a.mutant == 'shift':     # the compiler's calendar one edge late: the check must reject the cycle-exact compare
        plan['ret'] = [[e + 1] + list(rest) for e, *rest in plan['ret']]
    meta = dict(master=base_master(p['master']), die_frame=a.frame, die_master=p['master'], lk=p['lk'],
                land_e=land_e(p['lk']), slice=sl, slice_index=g, seed=SEED, only=None, K=mats[0].K,
                rows_per_mat=[m.rows for m in mats], mats=len(mats), q_pairs=q, bf_pairs=bf, pairs=qa,
                phase=dict((k, v) for k, v in ph.items() if k != 'matrices'), matrices=ph['matrices'], nrows=off, ops=off,
                rows={str(k): v for k, v in rows.items()}, cycles=a.cycles, plan=plan, mutant=a.mutant,
                fixture=dict(dir=str(a.fixtures), meta_sha256=sha((Path(a.fixtures) / 'meta.json').read_bytes()),
                             files={k: fx['files'][k]['sha256'] for k in ('weights/wq_a.bin', 'weights/wq_a.scale.bin',
                                                                         'weights/wkv.bin', 'weights/wkv.scale.bin',
                                                                         'ops/attn.norm.scale.bin', 'ops/attn.a_proj.bin')}),
                images={n: sha((out / n).read_bytes()) for n in names + xsn})
    (out / 'return_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'T').write_text(f'{a.cycles}\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={a.cycles} +K={mats[0].K} +OPS={off}\n')
    # the fixture value of every row (the BF16 the frame's FP32 accumulator rounds to)
    ap = fx['a_proj']
    bad = [r for r, v in rows.items() if int(G.bits(G.F(ap[v['out_index']]))) >> 16 != v['bf16']
           or int(G.bits(G.F(ap[v['out_index']]))) & 0xFFFF]
    assert not bad, f'golden rows differ from the fixture: {bad}'
    print(f'XS_GEN {a.frame} ({p["master"]}, lk {p["lk"]:03x} E {land_e(p["lk"])}) slice {sl} g {g} rows {gidx} '
          f'pairs {qa} nseg {NSEG} faults {plan["faults"]} ret_words {plan["ret_words"]} beats {ph["nbeat"]} '
          f'mutant {a.mutant}')
    return 0


def check_words(meta, log):
    """frame ret words vs the golden segment tree and the compiler calendar.  Same rules as tools/s81_dv/frame_bench.py
    check (golden_node values, e flag, tiling of [0, nseg) once per row, one op tag, cycle-exact calendar, xo, faults)
    except the subtree shape: a node (lo, k) is legal iff lo % 2^k == 0 and lo < n (golden csum pads the segment tree to
    a power of two; frame_bench.py's 'lo + 2^k <= max(n, 2^k)' rejects the padded right subtree of nseg 5 / 3)"""
    from frame_bench import golden_node
    from static_return_calendar import _f, norm
    rows = {int(k): v for k, v in meta['rows'].items()}
    errs = []
    for r, v in rows.items():
        n = len(v['vals'])
        g, e = golden_node(v['vals'], 0, max(0, (n - 1).bit_length()), n)
        if g != v['acc'] or e:
            errs.append(f'SEGMENT_MODEL row {r} {g:08x} != acc {v["acc"]:08x}')
    words, cov, tags = [], {}, set()
    for m in re.finditer(r'^RET (\d+) ([0-9a-f]+)$', log, re.M):
        edge, w = int(m.group(1)), int(m.group(2), 16)
        words.append((edge, (w >> 1) & 0xFFFFFFFF, (w >> 33) & 0xFFFFFFFF, (w >> 65) & 1, w & 1))
    for edge, t_, d_, e_, v_ in words:
        row19, lo, k, n = _f(norm(t_))
        pos, optag, row = row19 >> 16, (row19 >> 14) & 3, row19 & 0x3FFF
        tags.add(optag)
        if not v_ or pos or row not in rows:
            errs.append(f'BAD_TAG edge {edge} t {t_:08x}')
            continue
        vals = rows[row]['vals']
        if n != len(vals) or lo % (1 << k) or lo >= n:
            errs.append(f'BAD_SHAPE edge {edge} row {row} lo {lo} k {k} n {n} nseg {len(vals)}')
            continue
        g, ge = golden_node(vals, lo, k, n)
        if d_ != g or e_ != ge:
            errs.append(f'MISMATCH edge {edge} row {row} lo {lo} k {k} got {d_:08x}/{e_} want {g:08x}/{ge}')
        cov.setdefault(row, []).extend(range(lo, min(lo + (1 << k), n)))
    for r, v in rows.items():
        if sorted(cov.get(r, [])) != list(range(len(v['vals']))):
            errs.append(f'COVERAGE row {r} segments {sorted(cov.get(r, []))} of {len(v["vals"])}')
    if len(tags) > 1:
        errs.append(f'OP_TAGS {sorted(tags)}')
    plan = meta['plan']
    if plan['faults']:
        errs.append(f'PLAN_FAULTS {plan["faults"]}')
    key = lambda e, t, d, er: (e, _f(norm(t))[0] & 0x3FFF, _f(norm(t))[1:], d, er)  # noqa: E731
    want = [key(*w_) for w_ in plan['ret']]
    got = [key(e, t, d, er) for e, t, d, er, _ in words]
    if want != got:
        errs.append(f'PLAN_MISMATCH predicted {len(want)} words, got {len(got)}; first diff '
                    f'{next(((w_, g_) for w_, g_ in zip(want, got) if w_ != g_), None)}')
    errs += re.findall(r'^XO_MISMATCH .*$', log, re.M)[:4] + re.findall(r'^FAULT .*$', log, re.M)[:4]
    done = re.search(r'^END edges=(\d+) ret_words=(\d+) xo_checked=(\d+) fault=(\d+)', log, re.M)
    if not done:
        errs.append('NO_END')
    complete = sum(1 for _, t_, _, _, _ in words if _f(norm(t_))[1] == 0 and (1 << _f(norm(t_))[2]) >= _f(norm(t_))[3])
    return errs, dict(words=len(words), rows=len(rows), complete_rows_at_root=complete, partial_words=len(words) - complete,
                      plan_exact=not any(e.startswith('PLAN_') for e in errs), end=done.group(0) if done else None)


def cmd_check(a):
    import hdc_golden_v41 as G
    d = Path(a.dir)
    meta = json.loads((d / 'meta.json').read_text())
    errs, summ = check_words(meta, Path(a.log).read_text())
    # fixture tie: every row's golden accumulator rounds to the fixture's BF16 a_proj output
    fixdir = Path(getattr(a, 'fixtures', None) or meta['fixture']['dir'])
    fix_rows = 0
    if (fixdir / 'ops/attn.a_proj.bin').exists():
        if sha((fixdir / 'ops/attn.a_proj.bin').read_bytes()) != meta['fixture']['files']['ops/attn.a_proj.bin']:
            errs.append('FIXTURE attn.a_proj.bin sha256 differs from the vectors\' fixture')
        ap = np.fromfile(fixdir / 'ops/attn.a_proj.bin', dtype=np.float32)
        for r, v in meta['rows'].items():
            fb = int(G.bits(G.F(ap[v['out_index']])))
            acc_bf = int(G.bits(G.to_bf16(np.array([v['acc']], dtype=np.uint32).view(np.float32))[0])) >> 16
            if fb >> 16 != acc_bf or fb >> 16 != v['bf16'] or fb & 0xFFFF:
                errs.append(f'FIXTURE row {r} out {v["out_index"]} fixture {fb >> 16:04x} acc->bf16 {acc_bf:04x}')
            fix_rows += 1
    else:
        errs.append(f'FIXTURE dir {fixdir} missing')
    ok = not errs
    chk = dict(summary=summ, pass_=ok, fixture_rows=fix_rows, errors=errs[:200], frame=meta['die_frame'],
               mutant=meta.get('mutant'))
    chk['pass'] = chk.pop('pass_')
    (d / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
    for e in errs[:8]:
        print(e)
    print(f'XS_CHECK {"PASS" if ok else "FAIL"} {meta["die_frame"]} mutant={meta.get("mutant")} rows={len(meta["rows"])} '
          f'fixture_rows={fix_rows} errors={len(errs)} {summ["end"]}')
    return 0 if ok else 1


def cmd_collect(a):
    """bench_xs record: base must PASS, every mutant must FAIL; commit each run's check + log tail as witness"""
    import shutil
    res = ROOT / BENCH
    res.mkdir(parents=True, exist_ok=True)
    out = Path(a.out)
    for f in ('sources.sha256', 'verilator.version'):
        shutil.copy(out / f, res / f)
    rec = dict(schema='opentallas.s81_dv.bench_xs.v1', bench='tools/s81_dv/layer_prog/xs/xs_bench.sh',
               lowering='tools/s81_dv/layer_prog/lower_xs.py', host=a.host, mutants=[])
    for vd in a.vec:
        vd = Path(vd)
        n = vd.name
        log = out / f'run_{n}.log'
        rc = cmd_check(argparse.Namespace(dir=str(vd), log=str(log)))
        chk = json.loads((vd / 'check.json').read_text())
        meta = json.loads((vd / 'meta.json').read_text())
        lines = log.read_text().splitlines()
        wit = res / f'run_{n}.log'
        wit.write_text('\n'.join([l for l in lines if l.startswith(('RET ', 'FAULT', 'XO_MISMATCH'))][:200] + lines[-5:]
                                  + [f'CHECK {e}' for e in chk['errors'][:20]]
                                  + [f'XS_CHECK {"PASS" if rc == 0 else "FAIL"} {n}']) + '\n')
        (res / f'check_{n}.json').write_text(json.dumps(chk, indent=1) + '\n')
        if n == 'base':
            rec.update(pass_=rc == 0, frame=meta['die_frame'], die_master=meta['die_master'], lk=meta['lk'],
                       land_e=meta['land_e'], rows=[v['out_index'] for v in meta['rows'].values()], pairs=meta['pairs'],
                       nseg=NSEG, K=meta['K'], summary=chk['summary'], fixture=meta['fixture'], images=meta['images'],
                       ret_calendar=meta['plan']['ret'])
        else:
            rec['mutants'].append(dict(name=n, failed=rc != 0, witness=str(wit.relative_to(ROOT)),
                                       first_errors=chk['errors'][:3],
                                       what={'swap': 'two elements holding different rows get each other\'s ROM images '
                                                     '(wrong placement)',
                                             'shift': 'the compiler\'s return calendar one edge late'}.get(n, n)))
    rec['pass'] = rec.pop('pass_', False) and all(m['failed'] for m in rec['mutants']) and bool(rec['mutants'])
    (res / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_COLLECT pass={rec["pass"]} mutants={[(m["name"], m["failed"]) for m in rec["mutants"]]}')
    return 0 if rec['pass'] else 1


def main(argv=None):
    import dv_layer_compile as C
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    g = sp.add_parser('gen')
    g.add_argument('--frame', default='u_f_0L00')
    g.add_argument('--slice', default=None)
    g.add_argument('--out', required=True)
    g.add_argument('--fixtures', default=str(FIX))
    g.add_argument('--die-ref', default=C.DIE_REF)
    g.add_argument('--die-src', default=None)
    g.add_argument('--cycles', type=int, default=CYCLES)
    g.add_argument('--mutant', choices=('swap', 'shift'), default=None)
    c = sp.add_parser('check')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    k = sp.add_parser('collect')
    k.add_argument('--out', required=True, help='the xs_bench.sh outdir (logs fetched back)')
    k.add_argument('--host', default=None)
    k.add_argument('vec', nargs='+')
    a = ap.parse_args(argv)
    return {'gen': cmd_gen, 'check': cmd_check, 'collect': cmd_collect}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
