#!/usr/bin/env python3
"""TOK-S81-GAPS/XS (10-18): the DV field placement compiler -- every frame-held matrix of a layer placed into the
frames of the S81 DV die (bind_p4l3_g8), as multi-phase ROM fields (element via-maps + il7 cfg banks + the slice xs
phase / stream ROMs) with a legalised, cycle-exact return calendar per phase.  lower_xs.py keeps the a_proj lowering
(phase 0 of every frame); this module adds the other frame matvecs of the layer as further phases of the SAME field.

OWNERSHIP (SPEC.md section 2): output rows go to the frames of the owning slice (sid g), every frame of the slice takes
an equal share (+-1 row group):
  attn.wq_b         head h of the rank -> slice h (512 rows, 64 / frame), K 1280 (q_norm output)           FP8
  attn.wo_b         h rows [320 g, 320 g + 320) -> slice g (40 / frame), K 2048 (the rank's wo_a columns)    FP8
  ffn.shared_gu     ff j in [36 g, 36 g + 36): gate j AND up j in slice g (SwiGLU slice-local), K 5120        FP8
  ffn.experts_gu    per routed expert as shared_gu (6 experts x 72 rows / slice), K 5120                     FP4
  ffn.down          per expert / shared: the rank's 1,280 output rows, 80 / slice, K 2304                    FP4 / FP8
  ffn.router        96 rows, 6 / slice, BF16 K 5120 (bf pairs)                                               BF16
  attn.wo_a         grouped BF16 matvec (golden matvec_c: fp32 mul of the dequantised weight x bf16(o))      BF16
A phase holds 2 x (pairs // nseg) rows (frame_return_plan.plan_phase: one segment per q pair); nseg is the smallest
golden-aligned split whose segments all share one unit class.  The element-work term of the return calendar is
MEASURED per phase shape (fmt, K, nseg) and per segment (ELEM_SEG; frame bench + PV trace) and legalised in; a shape
without a measurement is placed and imaged but its calendar is reported 'calendar_unmeasured' (no cycle-exact claim).
Every FP8 / FP4 shape of L0 is measured (bench_xsp*: 13 phases of u_f_0L00 PASS cycle-exact + fixture BF16).

    xs_place.py tie   [--fixtures D]                         golden of every placed row == the layer fixture (no RTL)
    xs_place.py frame --frame u_f_0L00 --out DIR [--ops ...]  compile one frame's multi-phase field + images
    xs_place.py gen   --frame F (--op OP [--nth N] | --phase K ...) --out VEC [--mutant swap|shift]   bench vectors
    xs_place.py check --dir VEC --log RUN.LOG                  cycle-exact + bit-exact check (lower_xs.check_words)
    xs_place.py collect --out BENCH_OUT [--res DIR] VEC...      bench record (check.json + witnesses)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lower_xs as LX  # noqa: E402  (sets sys.path for tools/, s81_dv, s81, s81_static_control)
import numpy as np  # noqa: E402

ROOT = LX.ROOT
NSLICE, NFRAME = 16, 8


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


# ------------------------------------------------------------------------------------------------ fixture matrices
class FMat(LX.FixMat):
    """rows of a fixture weight as the image writer's Mat: fp8 (32 x 32 block scales [rows/32, K/32] or per-row
    [rows, K/32]), fp4 (packed low nibble first, per-row scales), bf16 (raw u16, or an fp8 tensor dequantised)"""

    def __init__(self, name, fmt, arr, sc, rows, phase):
        import hdc_golden_v41 as G
        rows = np.asarray(rows)
        self.name, self.fmt, self.r0, self.k0, self.phase = name, fmt, 0, 0, phase
        self.rows = len(rows)
        self.src = [(name, int(r)) for r in rows]
        if fmt == 'fp8':
            self.K = arr.shape[1]
            self.codes = arr[rows]
            e = np.repeat(sc, 32, axis=0) if sc.shape[0] * 32 == arr.shape[0] else sc
            self.exp = e[rows]
            q = G.E4M3[self.codes]
        elif fmt == 'fp4':
            self.K = arr.shape[1] * 2
            p = arr[rows]
            self.nib = np.stack([p & 15, p >> 4], axis=-1).reshape(len(rows), self.K)
            self.exp = sc[rows]
            q = G.E2M1[self.nib]
        else:
            raise ValueError(fmt)
        self.w = G.Q8(q.astype(np.float64), self.exp.astype(np.int64) - 127)


class FMatBF(LX.FixMat):
    """BF16 rows (u16) for the bf pairs"""

    def __init__(self, name, u16, rows, phase):
        import hdc_golden_v41 as G
        rows = np.asarray(rows)
        self.name, self.fmt, self.r0, self.k0, self.phase = name, 'bf16', 0, 0, phase
        self.rows, self.K = len(rows), u16.shape[1]
        self.u16 = u16[rows]
        self.wf = G.from_bits(self.u16.astype(np.uint32) << 16)
        self.src = [(name, int(r)) for r in rows]


class Fix:
    def __init__(self, d):
        self.d = Path(d)
        self.files = json.loads((self.d / 'files.json').read_text())
        self.meta = json.loads((self.d / 'meta.json').read_text())

    def arr(self, rel):
        f = self.files[rel]
        return np.fromfile(self.d / rel, dtype=np.dtype(f['dtype'])).reshape(f['shape'])

    def w(self, n):
        return self.arr(f'weights/{n}.bin')

    def sc(self, n):
        return self.arr(f'weights/{n}.scale.bin')

    def op(self, n):
        return self.arr(f'ops/{n}.bin')


def fmt_of(fx, n):
    """fp8 (K = cols) or fp4 (packed: per-row scales, K / 32 = scale cols = 2 cols / 32)"""
    a, s = fx.w(n), fx.sc(n)
    if s.shape[0] == a.shape[0] and s.shape[1] * 16 == a.shape[1]:
        return 'fp4'
    return 'fp8'


# ------------------------------------------------------------------------------------------------ op table
def deal(n, parts):
    """n items over `parts` owners, +-1 (first owners get the extra)"""
    b, e = divmod(n, parts)
    out, s = [], 0
    for i in range(parts):
        k = b + (1 if i < e else 0)
        out.append(list(range(s, s + k)))
        s += k
    return out


def op_groups(fx, op):
    """[(matrix name, fmt, rank-local rows, x vector, golden tie: list of (fixture op, index) or None, groups)] where
    groups[g][f] = indices into rows placed on slice g frame f"""
    m = fx.meta
    exps = m['experts']
    ffs = {}
    if op == 'attn.wq_b':
        x = fx.op('attn.q_norm.scale')
        rows = list(range(fx.w('wq_b').shape[0]))
        heads = m['tp_split']['heads'][m['rank']]
        hd = len(rows) // (heads[1] - heads[0])
        g = [[[h * hd + r for r in fr] for fr in deal(hd, NFRAME)] for h in range(NSLICE)]
        q0 = m['tp_split']['wq_b_rows'][m['rank']][0]
        return [dict(mat='wq_b', rows=rows, x=x, tie=[('attn.wq_b', q0 + r) for r in rows], groups=g, out='bf16')]
    if op == 'attn.wo_b':
        c0, c1 = m['tp_split']['wo_b_cols'][m['rank']]
        x = fx.op('attn.wo_a')[c0:c1]
        rows = list(range(fx.w('wo_b').shape[0]))
        per = len(rows) // NSLICE
        g = [[[s * per + r for r in fr] for fr in deal(per, NFRAME)] for s in range(NSLICE)]
        return [dict(mat='wo_b', rows=rows, x=x, tie=None, groups=g, out='fp32',
                     note='rank partial (wo_b by input columns): the fixture holds the all-reduced sum only')]
    if op in ('ffn.shared_gu', 'ffn.experts_gu'):
        x = fx.op('ffn.norm.scale')
        out = []
        for e in (['shared'] if op == 'ffn.shared_gu' else [f'exp{e}' for e in exps]):
            n1, n3 = f'{e}.w1', f'{e}.w3'
            nff = fx.w(n1).shape[0]
            j0 = (m['tp_split']['shared_ff_rows'] if e == 'shared' else m['tp_split']['expert_ff_rows'])[m['rank']][0]
            tot = 4 * nff
            tie_op = 'ffn.shared_gu' if e == 'shared' else f'ffn.experts.{e[3:]}.gu'
            # one matrix per tensor (plan_phase takes one matrix per phase): gate j and up j in the same slice/frame
            for n, base in ((n1, 0), (n3, tot)):
                rows = list(range(nff))
                g = [[[j for j in fr] for fr in deal_into(js, NFRAME)] for js in deal(nff, NSLICE)]
                out.append(dict(mat=n, rows=rows, x=x, tie=[(tie_op, base + j0 + r) for r in rows], groups=g,
                                out='bf16', expert=e))
        return out
    if op == 'ffn.down':
        out = []
        for e in ['shared'] + [f'exp{e}' for e in exps]:
            n2 = f'{e}.w2'
            rows = list(range(fx.w(n2).shape[0]))
            xop = 'ffn.shared.swiglu' if e == 'shared' else f'ffn.experts.{e[3:]}.route_w'
            r0 = m['tp_split']['expert_down_rows'][m['rank']][0]
            tie_op = 'ffn.shared.down' if e == 'shared' else f'ffn.experts.{e[3:]}.down'
            g = [[[j for j in fr] for fr in deal_into(js, NFRAME)] for js in deal(len(rows), NSLICE)]
            import hdc_golden_v41 as G   # down reads bf16(a) (dv_layer_fixtures.expert)
            out.append(dict(mat=n2, rows=rows, x=G.to_bf16(fx.op(xop)), tie=[(tie_op, r0 + r) for r in rows], groups=g,
                            out='bf16', expert=e))
        return out
    if op in ('attn.idx.q', 'eng.wkv'):
        n, xop = {'attn.idx.q': ('indexer.wq_b', 'attn.q_norm.scale'), 'eng.wkv': ('engram.wkv', 'eng.rows_allgather')}[op]
        rows = list(range(fx.w(n).shape[0]))
        g = [[[j for j in fr] for fr in deal_into(js, NFRAME)] for js in deal(len(rows), NSLICE)]
        if op == 'eng.wkv':     # the rank's contiguous quarter of the 4 x 6,400 (k copies ++ v) rows
            tie = [('eng.wkv', m['rank'] * len(rows) + r) for r in rows]
            return [dict(mat=n, rows=rows, x=fx.op(xop), tie=tie, groups=g, out='bf16')]
        return [dict(mat=n, rows=rows, x=fx.op(xop), tie=None, groups=g, out='bf16',
                     note='the fixture holds q after RoPE + FP4 qdq only: golden tie, no fixture tie')]
    raise KeyError(op)


def deal_into(items, parts):
    return [[items[i] for i in idx] for idx in deal(len(items), parts)]


XS_OPS = {'L0': ['attn.wq_b', 'attn.wo_b', 'ffn.shared_gu', 'ffn.experts_gu', 'ffn.down']}
XS_OPS['L2'] = XS_OPS['L20'] = XS_OPS['L0'][:1] + ['attn.idx.q'] + XS_OPS['L0'][1:]
XS_OPS['L14'] = ['eng.wkv'] + XS_OPS['L2']
# TOK-S81-GAPS/XS2: the BF16 pair phases (xs_bf.py) are APPENDED after the FP8 / FP4 phases of the field, so the q phase
# indices (and the bench_xsp* records) are unchanged
BF_OPS = {'L0': ['attn.wo_a', 'ffn.router']}
BF_OPS['L2'] = BF_OPS['L14'] = BF_OPS['L20'] = ['attn.cmp.wk'] + BF_OPS['L0']
NOT_PLACED = {}


def make_mat(fx, grp, sel, phase):
    n = grp['mat']
    f = fmt_of(fx, n)
    return FMat(n, f, fx.w(n), fx.sc(n), [grp['rows'][i] for i in sel], phase)


def nseg_for(fmt, K, npairs):
    """smallest golden-aligned split with one unit class and at most 2 units per segment, that fits the pairs"""
    import v41_rom_ksplit_bankmap as S
    for n in range(1, npairs + 1):
        segs = S.segments(K, n)
        if len(segs) != n:
            continue
        cls = {S.unit_range(fmt, a, e)[1] - S.unit_range(fmt, a, e)[0] for a, e in segs}
        if len(cls) == 1 and max(cls) <= 2:
            return n, cls.pop()
    raise ValueError(('no single-class split', fmt, K))


# ------------------------------------------------------------------------------------------------ tie (no RTL)
def cmd_tie(a):
    import hdc_golden_v41 as G
    import v41_die_images_w17w10 as I
    fx = Fix(a.fixtures)
    rep = {}
    for op in a.ops or XS_OPS[a.layer]:
        for grp in op_groups(fx, op):
            mat = make_mat(fx, grp, list(range(len(grp['rows']))), op)
            gold = I.golden_phase([mat], grp['x'])
            bad, n = [], 0
            if grp['tie']:
                for r, (top, idx) in enumerate(grp['tie']):
                    fb = int(G.bits(G.F(fx.op(top).reshape(-1)[idx])))
                    if fb >> 16 != gold[r][1] or fb & 0xFFFF:
                        bad.append((r, top, idx, f'{fb:08x}', f'{gold[r][1]:04x}'))
                    n += 1
            nseg, units = nseg_for(mat.fmt, mat.K, 10)
            rep[f'{op}:{grp["mat"]}'] = dict(fmt=mat.fmt, K=mat.K, rows=mat.rows, nseg=nseg, units=units, tied=n,
                                             bad=len(bad), first_bad=bad[:3], note=grp.get('note'))
            print(op, grp['mat'], mat.fmt, 'K', mat.K, 'rows', mat.rows, 'nseg', nseg, 'units', units, 'tied', n,
                  'bad', len(bad), bad[:2])
    if a.out:
        Path(a.out).write_text(json.dumps(rep, indent=1) + '\n')
    return 0 if all(v['bad'] == 0 for v in rep.values()) else 1


# ------------------------------------------------------------------------------------------------ frame field
NPAIRS = LX.NPAIRS          # q pairs per phase (a_proj's choice; every phase of the frame uses the same field slots)
# element-work term per (fmt, units / segment, rows / element): MEASURED on the frame bench only (lower_xs.ELEM_EXTRA is
# the fp8 a_proj measurement); a class missing here is placed and imaged with calendar_unmeasured
ELEM_EXTRA = {('fp8',) + k: v for k, v in LX.ELEM_EXTRA.items()}
# The class-only term is FALSIFIED by bench_xsp (ot-epyc4 10-18, run with the spine ROMs present): wo_b (fp8, 2 units,
# K 2048 nseg 2) returned every word exactly 20 edges before the class term (+13, not +33), values exact.  The PV trace
# (bench_xsp_pv, -DTB_PVTRACE: every element's emission edge) shows the term is per SEGMENT: fp8 K 2304 / K 1280 emit
# their 256-element last segment 14 edges before the full 512-element ones (the others exactly on the e0 rule).  So the
# compiler keys the MEASURED term by phase shape (fmt, K, nseg) -> one value per segment, and legalises with it
# (frame_return_plan.plan_phase seg_extra); a shape measured on one phase is the prediction for every other phase of
# that shape (bench_xsp2 / bench_xsp_pv: other phases / rows of the same shapes PASS cycle-exact).
ELEM_SEG = {('fp8', 5120, 5): [33] * 5,        # a_proj bench_xs + shared_gu bench_xsp sgu; PV trace p16 exact
            ('fp8', 2048, 2): [13] * 2,        # wo_b bench_xsp wob (phase 12); predicts phase 13 (bench_xsp2)
            ('fp4', 5120, 5): [18] * 5,        # experts_gu bench_xsp egu (phase 20); predicts phase 24
            ('fp4', 2304, 5): [-14] * 5,       # down bench_xsp down (phase 47); predicts phase 50; PV trace p50 exact
            ('fp8', 2304, 5): [0, 0, 0, 0, -14],   # shared down, PV trace p44 (bench_xsp_pv)
            ('fp8', 1280, 3): [0, 0, -14]}     # wq_b, PV trace p1 (bench_xsp_pv)


def frame_slot(die, frame):
    for sl in sorted(die.slices()):
        fr = die.frames_of(sl)
        if frame in fr:
            return sl, LX.slice_index(die, sl), fr.index(frame)
    raise KeyError(frame)


def phase_plan(die_frame_master, lk, pairs, off, mat, x, nseg, iters):
    """legalise one phase on pairs (a contiguous run qa[off:off + n]); assign_slots in field-slot indexing"""
    import frame_return_plan as P
    import v41_rom_ksplit_bankmap as S
    sx = ELEM_SEG.get((mat.fmt, mat.K, nseg))
    plan = P.plan_phase(LX.base_master(die_frame_master), pairs, mat, x, nseg, iters=iters, land_e=LX.land_e(lk),
                        seg_extra=sx)
    plan['assign_slots'] = [(i + off, R, sg) for i, R, sg in plan['assign_slots']]
    units = {S.unit_range(mat.fmt, a0, el)[1] - S.unit_range(mat.fmt, a0, el)[0] for a0, el in S.segments(mat.K, nseg)}
    plan['elem_class'] = [mat.fmt, max(units), 2]
    plan['calendar'] = 'measured_class' if sx is not None else 'calendar_unmeasured'
    plan['emission'] = dict(plan['emission'], elem_extra=sx)
    return plan


def add_planned(field, plan, mat, nseg):
    import frame_return_plan as P
    import v41_die_images_w17w10 as I
    orig = I._place
    I._place = P.place_fn(plan['assign_slots'], nseg)
    try:
        ph = I.add_phase(field, [mat])
    finally:
        I._place = orig
    assert field.stream[ph['sbase']:ph['sbase'] + ph['nbeat']] == plan['stream'], 'stream differs from the plan'
    return ph


def phase_list(fx, ops, npairs=NPAIRS):
    """die-wide phase sequence (identical on every frame: one slice xs stream, one phase index per op chunk):
    [(op, group index, chunk index, nseg, rows per phase)]"""
    seq = []
    for op in ops:
        for gi, grp in enumerate(op_groups(fx, op)):
            f = fmt_of(fx, grp['mat'])
            K = fx.w(grp['mat']).shape[1] * (2 if f == 'fp4' else 1)
            nseg, _ = nseg_for(f, K, npairs)
            R = 2 * (npairs // nseg)
            most = max(len(fr) for sl in grp['groups'] for fr in sl)
            for c in range(-(-most // R)):
                seq.append((op, gi, c, nseg, R))
    return seq


def compile_frame(die, frame, fixd, ops, iters=LX.ITERS, only=None):
    """the frame's multi-phase field: phase 0 = a_proj (lower_xs), then every op chunk of phase_list.  only = a set of
    field phase indices to legalise (others are placed with the identity assignment: images exact, calendar not
    legalised) -- the full legalise of a frame is ~1-3 s per phase."""
    import frame_bench as B
    import v41_die_images_w17w10 as I
    sl, g, j = frame_slot(die, frame)
    master, lk = die.inst[frame]['master'], die.strap(frame, 'lk')
    q, bf = B.frame_pairs(LX.base_master(master))
    fxa = LX.load_fixture(fixd)
    fx = Fix(fixd)
    _, pl = LX.placement(die, sl)
    p0 = pl[j]
    phases = []
    if p0['rows']:
        mats, gidx = LX.frame_mats(fxa, p0['rows'])
        _f, _ph, plan0, qa, _q, _bf = LX.frame_programme(master, lk, mats, fxa['x'])
    else:
        qa = q[:NPAIRS]
    import xs_bf as XB
    nbf = len(bf) if any(o in XB.BF_OPS for o in ops) else 0
    field = I.Field(16, 1, nbf, depth=8192, active=len(qa) + nbf, pp=True, fast=True)
    field.bf[:] = False
    field.bf[len(qa):len(qa) + nbf] = True                  # field slots len(qa).. = the frame's BF pairs (bf order)
    field.bf_desc = {}                                      # field phase -> {field slot: 82-bit BF programme descriptor}
    if p0['rows']:
        ph = add_planned(field, dict(plan0, assign_slots=plan0['assign_slots'],
                                     stream=_f.stream[_ph['sbase']:_ph['sbase'] + _ph['nbeat']]), mats[0], LX.NSEG)
        phases.append(dict(phase=0, op='attn.a_proj', mat=mats[0].name, rows=len(gidx), out_index=gidx, nseg=LX.NSEG,
                           nbeat=ph['nbeat'], faults=plan0['faults'], ret_words=plan0['ret_words'],
                           calendar='measured_class', ret=plan0['ret']))
    groups = {op: op_groups(fx, op) for op in ops if op not in XB.BF_OPS}
    for op, gi, c, nseg, R in phase_list(fx, [o for o in ops if o not in XB.BF_OPS]):
        grp = groups[op][gi]
        sel_all = grp['groups'][g][j]
        sel = sel_all[c * R:(c + 1) * R]
        mat = make_mat(fx, grp, sel, op)
        npair = (len(qa) // nseg) * nseg
        k = len(field.phases)
        if only is None or k in only:
            plan = phase_plan(master, lk, qa[:npair], 0, mat, grp['x'], nseg, iters)
        else:
            plan = phase_plan(master, lk, qa[:npair], 0, mat, grp['x'], nseg, 0)
            plan['calendar'] = 'not_legalised'
        ph = add_planned(field, plan, mat, nseg)
        tie = [grp['tie'][grp['rows'].index(grp['rows'][i])] if grp['tie'] else None for i in sel]
        phases.append(dict(phase=k, op=op, mat=grp['mat'], fmt=mat.fmt, K=mat.K, chunk=c, rows=len(sel),
                           row_index=[grp['rows'][i] for i in sel], tie=tie, nseg=nseg, rows_per_phase=R,
                           nbeat=ph['nbeat'], sbase=ph['sbase'], faults=plan['faults'], ret_words=plan['ret_words'],
                           calendar=plan['calendar'], elem_class=plan['elem_class'], ret=plan['ret'],
                           emission=plan['emission'], placement=plan['placement'], plan=plan, sel=sel, gi=gi))
    bfo = [o for o in ops if o in XB.BF_OPS]
    if bfo:
        phases += compile_bf(field, fx, bfo, g, j, LX.base_master(master), LX.land_e(lk), bf, len(qa))
    fill = [int(v) for v in field.fill]
    return dict(frame=frame, master=master, lk=lk, slice=sl, slice_index=g, frame_index=j, pairs=qa, q_pairs=q,
                bf_pairs=bf, phases=phases, fill=fill, depth=field.depth, nphases=len(field.phases),
                slots=list(qa) + list(bf[:nbf])), field


def bf_phase_list(fx, ops, npairs):
    """die-wide BF phase sequence: [(op, group, row chunk c, segment s, segments n, rows per phase, most rows on a frame)]:
    per chunk of <= 2 x npairs rows of each frame, one phase per BSEG segment of K (one x slice per phase)"""
    import xs_bf as XB
    seq = []
    for op in ops:
        for gi, grp in enumerate(XB.bf_groups(fx, op)):
            most = max(len(fr) for sl in grp['groups'] for fr in sl)
            n, _ = XB.nseg_total(grp['u16'].shape[1])
            R = 2 * npairs
            for c in range(-(-most // R)):
                for s in range(n):
                    seq.append((op, gi, c, s, n, R, most))
    return seq


def compile_bf(field, fx, ops, g, j, master, land_e, bf, off):
    """the BF16 pair phases of this frame (xs_bf.py): one BSEG segment of up to 2 x 3 rows per phase, super row R on BF
    pair R; the programme (measured descriptor of the master / lane latency, this phase's ROM base) rides the cfg spare
    columns.  A frame without rows in a die-wide phase gets the phase's stream and an EMPTY configuration."""
    import v41_die_images_w17w10 as I
    import xs_bf as XB
    meas, how = XB.meas_for(XB.load_meas(), master, land_e)
    if meas is not None:
        meas = dict(meas, calendar=how)
    out = []
    for op, gi, c, s, n, R, most in bf_phase_list(fx, ops, XB.BF_PAIRS_DIE):
        grp = XB.bf_groups(fx, op)[gi]
        sel = grp['groups'][g][j][c * R:(c + 1) * R]
        k = len(field.phases)
        x = XB.x_of(grp, g)
        cols = slice(s * XB.BSEG, (s + 1) * XB.BSEG)
        if sel:
            u = grp['u16'][[grp['rows'][i] for i in sel]]
            vals, acc, b16 = XB.bf_vals(u, x)
        else:      # the stream of a frame holding rows; no configuration, no ROM words kept
            u, vals = np.zeros((1, grp['u16'].shape[1]), np.uint16), [[0] * n]
        mat = FMatBF(grp['mat'], np.ascontiguousarray(u[:, cols]), list(range(len(u))), op)
        nsr = -(-mat.rows // 2)
        base = [int(field.fill[off + R_]) + (int(field.fill[off + R_]) & 1) for R_ in range(nsr)]   # PP: even start
        plan = XB.bf_plan(master, bf, vals, s, n, meas if sel else None, base)
        orig = I._place
        I._place = XB.place_bf([(off + R_, R_) for R_ in range(nsr)], s, n)
        try:
            words0, fill0 = [dict(w) for w in field.words], field.fill.copy()
            ph = I.add_phase(field, [mat])
        finally:
            I._place = orig
        if not sel:
            field.cfg[-1] = [[0] * I.CW for _ in range(field.np)]
            field.words, field.fill = words0, fill0
            plan['calendar'] = 'empty_frame'
        else:
            for R_ in range(nsr):     # the descriptor's ROM base is the pair's phase start (PP reorder from there)
                assert (field.cfg[-1][off + R_][2 * I.NSEG] >> 6) == base[R_], ('BF phase start', base[R_])
        sys.path.insert(0, str(ROOT / 'tools/s81'))
        import bf_programme_compile as BC
        field.bf_desc[k] = {off + bf.index(int(p_)): BC.pack(d) for p_, d in plan['desc'].items()}
        out.append(dict(phase=k, op=op, mat=grp['mat'], fmt='bf16', K=grp['u16'].shape[1], k_pad=grp['k_pad'],
                        kseg=[cols.start, cols.stop],
                        xbase=cols.start, chunk=c, seg=s, nseg=n, rows=len(sel), row_index=[grp['rows'][i] for i in sel],
                        tie=[grp['tie'][i] for i in sel], tie_kind=grp['tie_kind'], rows_per_phase=R,
                        nbeat=ph['nbeat'], sbase=ph['sbase'], faults=plan['faults'], ret_words=plan['ret_words'],
                        calendar=plan['calendar'], elem_class=['bf16', XB.BSEG], ret=plan['ret'],
                        shape=XB.shape_key(master, land_e), bf_pairs=plan['pairs'], assign=plan['assign'],
                        desc=plan['desc'], plan=dict(plan, rows_vals={str(r): v for r, v in enumerate(vals)},
                                                     acc=acc if sel else [], bf16=b16 if sel else []),
                        sel=sel, gi=gi))
    return out


def write_images(field, qa, q, bf, inst, out):
    """all phases: element via-maps + il7 cfg banks (word w of phase p in bank w % 7 row 4 p + w // 7) + xs ROMs"""
    import v41_die_images_w17w10 as I
    from field_cfg7_image import encode_bank
    out = Path(out)
    tmp = out / '_field'
    I.write_field(field, tmp, 10, flat_viamaps=True)
    slot_of = {k: s for s, k in enumerate(qa)}
    nbf = int(field.bf.sum())
    bslot = {k: len(qa) + i for i, k in enumerate(bf[:nbf])}
    names = []
    for k, s in slot_of.items():
        for mb in ('', 'b'):
            for par in (0, 1):
                (out / f'{inst}_e{k}{mb}_{par}.viamap.hex').write_text((tmp / f'e{s}{mb}_{par}.viamap.hex').read_text())
                names.append(f'{inst}_e{k}{mb}_{par}.viamap.hex')
    # BF pair columns (dsfd_bf_col u_e<k>w = front c0 = macro 0 = row 2R; u_e<k>e = c1 = macro 1 = row 2R + 1), PP banks
    for k, s in bslot.items():
        for mb, col in (('', 'w'), ('b', 'e')):
            for par in (0, 1):
                (out / f'{inst}_e{k}{col}_{par}.viamap.hex').write_text((tmp / f'e{s}{mb}_{par}.viamap.hex').read_text())
                names.append(f'{inst}_e{k}{col}_{par}.viamap.hex')
    slot_all = {**slot_of, **bslot}
    nph = len(field.cfg)
    assert 4 * nph <= 4096, ('cfg7 bank rows', nph)
    bdesc = getattr(field, 'bf_desc', {})
    for k in q + bf:
        banked = [[0] * 4096 for _ in range(7)]
        for p in range(nph):
            words = list(field.cfg[p][slot_all[k]]) if k in slot_all else [0] * 25
            d = bdesc.get(p, {}).get(slot_all.get(k))
            if d:     # ot_s81_cfg7_seq_bfp: desc[24 w +: 24] in the spare columns [71:48] of cfg word w = 0..3
                for w_ in range(4):
                    words[w_] |= ((d >> (24 * w_)) & 0xFFFFFF) << 48
            for w_, v in enumerate(words):
                banked[w_ % 7][4 * p + w_ // 7] = v
        for jb in range(7):
            (out / f'{inst}_c{k}_{jb}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in encode_bank72(banked[jb])))
            names.append(f'{inst}_c{k}_{jb}.viamap.hex')
    # the bench's spine reads its phase / stream ROMs from OT_ROM_DIR (missing -> no go, no returns: XS 10-18 bench)
    for f in ('spine_phase.hex', 'spine_stream.hex'):
        (out / f).write_text((tmp / f).read_text())
    return names, tmp


def encode_bank72(words):
    """field_cfg7_image.encode_bank with the 24 spare columns (the BF programme descriptor): 72-bit rows"""
    from field_cfg7_image import decode_bank
    assert len(words) == 4096 and all(0 <= w < 1 << 72 for w in words)
    phys = [0] * 512
    for addr, word in enumerate(words):
        b = 0
        while word:
            if word & 1:
                phys[addr // 8] |= 1 << (8 * b + addr % 8)
            word >>= 1
            b += 1
    if any(w >> 48 for w in words):
        assert decode_bank(phys) == words
    return phys


def cmd_frame(a):
    import dv_layer_compile as C
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    rec, field = compile_frame(die, a.frame, a.fixtures, a.ops or XS_OPS['L0'] + BF_OPS['L0'], iters=a.iters,
                               only=None if a.only is None else set(a.only))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for ph in rec['phases']:
        ph.pop('plan', None)
    (out / 'frame.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_FRAME {a.frame} phases {rec["nphases"]} max fill {max(rec["fill"])}/{rec["depth"]} faults '
          f'{sum(p["faults"] for p in rec["phases"] if p["calendar"] != "not_legalised")}')
    return 0

def cmd_gen(a):
    """bench vectors of ONE phase of the frame's full multi-phase field (every phase legalised, as compiled)"""
    import dv_layer_compile as C
    import hdc_golden_v41 as G
    import v41_die_images_w17w10 as I
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    rec, field = compile_frame(die, a.frame, a.fixtures, a.ops or XS_OPS['L0'] + BF_OPS['L0'], iters=a.iters)
    if a.phase:
        rc = 0
        for k_ in a.phase:
            ph = next(p for p in rec['phases'] if p['phase'] == k_)
            rc |= gen_one(a, rec, field, ph, Path(a.out) / f'p{k_}')
        return rc
    cand = [p for p in rec['phases'] if p['op'] == a.op and p['rows'] > 0]
    return gen_one(a, rec, field, cand[a.nth], out)


def gen_one(a, rec, field, ph, out):
    import hdc_golden_v41 as G
    import v41_die_images_w17w10 as I
    out.mkdir(parents=True, exist_ok=True)
    op = ph['op']
    k = ph['phase']
    fx = Fix(a.fixtures)
    if ph['fmt'] == 'bf16':
        return gen_bf(a, rec, field, ph, out, fx)
    grp = op_groups(fx, op)[ph['gi']]
    mat = make_mat(fx, grp, ph['sel'], op)
    names, tmp = write_images(field, rec['pairs'], rec['q_pairs'], rec['bf_pairs'], a.frame, out)
    xsn = LX.xs_roms(tmp, out)
    plan = ph['plan']
    if a.mutant == 'swap':
        r_of = {d['pair']: d['rows'] for d in plan['placement']}
        e1, e2 = next((u, v) for u in rec['pairs'] for v in rec['pairs'] if u < v and u in r_of and v in r_of
                      and r_of[u] != r_of[v])
    for n in names:
        dst = 'f' + n[len(a.frame):]
        if a.mutant == 'swap':
            dst = re.sub(rf'^f_e({e1}|{e2})(b?_\d)', lambda m: f'f_e{e2 if int(m.group(1)) == e1 else e1}{m.group(2)}', dst)
        (out / dst).write_text((out / n).read_text())
    gold = I.golden_phase([mat], grp['x'])
    rows = {}
    for r in range(mat.rows):
        tie = ph['tie'][r]
        rows[r] = dict(vals=plan['rows_vals'][str(r)], acc=gold[r][0], bf16=gold[r][1], src=list(mat.src[r]),
                       out_index=tie[1] if tie else None, tie=tie)
    vm = [int(struct.unpack('<I', struct.pack('<f', float(v)))[0]) for v in np.asarray(grp['x'], dtype=np.float32)]
    (out / 'vm.hex').write_text(''.join(f'{v:08x}\n' for v in vm))
    plan = {k_: v for k_, v in plan.items() if k_ != 'stream'}
    if a.mutant == 'shift':
        plan['ret'] = [[e + 1] + list(rest) for e, *rest in plan['ret']]
    T = max(w_[0] for w_ in plan['ret']) + 600
    meta = dict(op=op, field_phase=k, nphases=rec['nphases'], chunk=ph['chunk'], mat=ph['mat'], fmt=mat.fmt,
                calendar=ph['calendar'], elem_class=ph['elem_class'], master=LX.base_master(rec['master']),
                die_frame=a.frame, die_master=rec['master'], lk=rec['lk'], land_e=LX.land_e(rec['lk']),
                slice=rec['slice'], slice_index=rec['slice_index'], frame_index=rec['frame_index'], K=mat.K,
                nseg=ph['nseg'], pairs=rec['pairs'], nrows=mat.rows, rows={str(r): v for r, v in rows.items()},
                cycles=T, plan=plan, mutant=a.mutant, fill=rec['fill'],
                fixture=dict(dir=str(a.fixtures), meta_sha256=sha((Path(a.fixtures) / 'meta.json').read_bytes())),
                images={n: sha((out / n).read_bytes()) for n in names + xsn + ['spine_phase.hex', 'spine_stream.hex']})
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={T} +K={mat.K} +OPS={mat.rows} +PH={k}\n')
    print(f'XS_PLACE_GEN {a.frame} op {op} phase {k}/{rec["nphases"]} mat {ph["mat"]} rows {mat.rows} nseg {ph["nseg"]} '
          f'faults {plan["faults"]} ret_words {plan["ret_words"]} calendar {ph["calendar"]} T {T} mutant {a.mutant}')
    return 0


def gen_bf(a, rec, field, ph, out, fx):
    """bench vectors of one BF16 pair phase.  --bf-measure: the measurement vector (the bench build BF_LEGACY=1 issues
    on the walker; no calendar claim, values checked); mutants: swap (two BF columns' ROM images exchanged), shift
    (calendar +1 edge), desc (one pair's descriptor OFF 1 edge EARLY -> programme fault)"""
    import xs_bf as XB
    k = ph['phase']
    plan = ph['plan']
    measure = bool(getattr(a, 'bf_measure', False))
    if a.mutant == 'desc':
        p0 = ph['bf_pairs'][0]
        slot = rec['slots'].index(p0)
        v = field.bf_desc[k][slot]
        off = (v >> 15) & 0xFF
        field.bf_desc[k][slot] = (v & ~(0xFF << 15)) | ((off - 1) << 15)
    names, tmp = write_images(field, rec['pairs'], rec['q_pairs'], rec['bf_pairs'], a.frame, out)
    xsn = LX.xs_roms(tmp, out)
    if a.mutant == 'swap':      # the first pair's two columns (rows 0 / 1; a 1-row phase: row 0 reads the empty column)
        c1, c2 = f'e{ph["bf_pairs"][0]}w', f'e{ph["bf_pairs"][0]}e'
    for n in names:
        dst = 'f' + n[len(a.frame):]
        if a.mutant == 'swap':
            dst = re.sub(rf'^f_({c1}|{c2})(_\d)', lambda m: f'f_{c2 if m.group(1) == c1 else c1}{m.group(2)}', dst)
        (out / dst).write_text((out / n).read_text())
    rows = {}
    for r in range(ph['rows']):
        rows[r] = dict(vals=plan['rows_vals'][str(r)], acc=plan['acc'][r], bf16=plan['bf16'][r],
                       src=[ph['mat'], ph['row_index'][r]], out_index=ph['tie'][r][1], tie=ph['tie'][r],
                       tie_kind=ph['tie_kind'], seg=ph['seg'])
    # the bench spine reads x at i_xbase 0: vm.hex = the phase's x slice (the die issues xbase = ph['xbase'])
    xs_ = XB.x_of(XB.bf_groups(fx, ph['op'])[ph['gi']], rec['slice_index'])[ph['kseg'][0]:ph['kseg'][1]]
    vm = [int(struct.unpack('<I', struct.pack('<f', float(v)))[0]) for v in np.asarray(xs_, dtype=np.float32)]
    (out / 'vm.hex').write_text(''.join(f'{v:08x}\n' for v in vm))
    pl = dict(ret=[list(w) for w in plan['ret']], faults=plan['faults'], ret_words=plan['ret_words'],
              nodes=plan.get('nodes'), emission=plan.get('emission'), assign=plan['assign'], desc=ph['desc'])
    if a.mutant == 'shift':
        pl['ret'] = [[e + 1] + list(rest) for e, *rest in pl['ret']]
    T = (max(w_[0] for w_ in pl['ret']) + 600) if pl['ret'] and not measure else 3000
    meta = dict(op=ph['op'], field_phase=k, nphases=rec['nphases'], chunk=ph['chunk'], mat=ph['mat'], fmt='bf16',
                calendar='bf_measure' if measure else ph['calendar'], elem_class=ph['elem_class'], shape=ph['shape'],
                master=LX.base_master(rec['master']), die_frame=a.frame, die_master=rec['master'], lk=rec['lk'],
                land_e=LX.land_e(rec['lk']), slice=rec['slice'], slice_index=rec['slice_index'],
                frame_index=rec['frame_index'], K=ph['K'], kseg=ph['kseg'], xbase=ph['xbase'], seg=ph['seg'],
                nseg=ph['nseg'], pairs=rec['pairs'], nrows=ph['rows'],
                rows={str(r): v for r, v in rows.items()}, cycles=T, plan=pl, mutant=a.mutant, measure=measure,
                bf=dict(pairs=ph['bf_pairs'], assign=ph['assign'], desc=ph['desc'],
                        desc_images={str(rec['slots'][s]): f'{v:021x}' for s, v in field.bf_desc.get(k, {}).items()}),
                fill=rec['fill'], fixture=dict(dir=str(a.fixtures), meta_sha256=sha((Path(a.fixtures) / 'meta.json').read_bytes())),
                images={n: sha((out / n).read_bytes()) for n in names + xsn + ['spine_phase.hex', 'spine_stream.hex']})
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={T} +K={ph["kseg"][1] - ph["kseg"][0]} '
                              f'+OPS={max(1, ph["rows"])} +PH={k}\n')
    print(f'XS_PLACE_GEN {a.frame} op {ph["op"]} phase {k}/{rec["nphases"]} mat {ph["mat"]} BF16 rows {ph["rows"]} seg '
          f'{ph["seg"]}/{ph["nseg"]} pairs {ph["bf_pairs"]} faults {pl["faults"]} ret_words {pl["ret_words"]} calendar '
          f'{meta["calendar"]} shape {ph["shape"]} T {T} mutant {a.mutant}')
    return 0


def cmd_check(a):
    import hdc_golden_v41 as G
    d = Path(a.dir)
    meta = json.loads((d / 'meta.json').read_text())
    log = Path(a.log).read_text()
    errs, summ = LX.check_words(meta, log)
    if meta.get('measure'):      # BF_LEGACY measurement run: values / tiling / faults only, the calendar is what it measures
        errs = [e for e in errs if not e.startswith(('PLAN_MISMATCH', 'PLAN_FAULTS'))]
    if meta['fmt'] == 'bf16':    # a BF phase computes ONE golden segment of every row: coverage = {seg}, exactly once
        errs = [e for e in errs if not e.startswith('COVERAGE')]
        from static_return_calendar import _f, norm
        cov = {}
        for m_ in re.finditer(r'^RET (\d+) ([0-9a-f]+)$', log, re.M):
            w = int(m_.group(2), 16)
            row19, lo, k_, n_ = _f(norm((w >> 1) & 0xFFFFFFFF))
            cov.setdefault(row19 & 0x3FFF, []).extend(range(lo, min(lo + (1 << k_), n_)))
        for r in meta['rows']:
            if sorted(cov.get(int(r), [])) != [meta['seg']]:
                errs.append(f'COVERAGE row {r} segments {sorted(cov.get(int(r), []))} want [{meta["seg"]}]')
    errs += [l for l in re.findall(r'^BFP_BAD .*$', log, re.M)[:4]]
    fx = Fix(a.fixtures or meta['fixture']['dir'])
    tied = 0
    for r, v in meta['rows'].items():
        if not v['tie']:
            continue
        fb = int(G.bits(G.F(fx.op(v['tie'][0]).reshape(-1)[v['tie'][1]])))
        if v.get('tie_kind') == 'fp32':
            if fb != v['acc']:
                errs.append(f'FIXTURE row {r} {v["tie"]} fixture {fb:08x} acc {v["acc"]:08x}')
            tied += 1
            continue
        acc_bf = int(G.bits(G.to_bf16(np.array([v['acc']], dtype=np.uint32).view(np.float32))[0])) >> 16
        if fb >> 16 != acc_bf or fb >> 16 != v['bf16'] or fb & 0xFFFF:
            errs.append(f'FIXTURE row {r} {v["tie"]} fixture {fb >> 16:04x} acc->bf16 {acc_bf:04x}')
        tied += 1
    ok = not errs
    chk = dict(summary=summ, fixture_rows=tied, errors=errs[:200], frame=meta['die_frame'], op=meta['op'],
               field_phase=meta['field_phase'], mutant=meta.get('mutant'))
    chk['pass'] = ok
    (d / 'check.json').write_text(json.dumps(chk, indent=1) + '\n')
    for e in errs[:8]:
        print(e)
    print(f'XS_PLACE_CHECK {"PASS" if ok else "FAIL"} {meta["die_frame"]} {meta["op"]} phase {meta["field_phase"]} '
          f'mutant={meta.get("mutant")} rows={len(meta["rows"])} fixture_rows={tied} errors={len(errs)} {summ["end"]}')
    return 0 if ok else 1
def cmd_collect(a):
    """bench_xsp record: per vector the check verdict; base runs of measured classes must PASS, every mutant must FAIL;
    an unmeasured-class run is a MEASUREMENT of its element-work term (constant ret-edge offset vs the e0 rule)"""
    res = ROOT / (a.res or BENCHP)
    res.mkdir(parents=True, exist_ok=True)
    out = Path(a.out)
    import shutil
    for f in ('sources.sha256', 'verilator.version'):
        if (out / f).exists():
            shutil.copy(out / f, res / f)
    runs = []
    for vd in a.vec:
        vd = Path(vd)
        n = vd.name
        log = out / f'run_{n}.log'
        meta = json.loads((vd / 'meta.json').read_text())
        rc = cmd_check(argparse.Namespace(dir=str(vd), log=str(log), fixtures=a.fixtures))
        chk = json.loads((vd / 'check.json').read_text())
        lines = log.read_text().splitlines()
        got = [int(m.group(1)) for m in re.finditer(r'^RET (\d+) ', log.read_text(), re.M)]
        want = [w_[0] for w_ in meta['plan']['ret']]
        offs = sorted({gg - ww for gg, ww in zip(got, want)}) if len(got) == len(want) else None
        wit = res / f'run_{n}.log'
        wit.write_text('\n'.join([l for l in lines if l.startswith(('RET ', 'FAULT', 'XO_MISMATCH'))][:200] + lines[-5:]
                                  + [f'CHECK {e}' for e in chk['errors'][:20]]
                                  + [f'XS_PLACE_CHECK {"PASS" if rc == 0 else "FAIL"} {n}']) + '\n')
        (res / f'check_{n}.json').write_text(json.dumps(chk, indent=1) + '\n')
        (res / f'meta_{n}.json').write_text(json.dumps({k: v for k, v in meta.items() if k != 'plan'}, indent=1) + '\n')
        runs.append(dict(name=n, op=meta['op'], mat=meta['mat'], fmt=meta['fmt'], field_phase=meta['field_phase'],
                         nphases=meta['nphases'], calendar=meta['calendar'], elem_class=meta['elem_class'],
                         mutant=meta.get('mutant'), pass_=rc == 0, words=chk['summary']['words'],
                         fixture_rows=chk['fixture_rows'], value_errors=[e for e in chk['errors'] if
                                                                         e.startswith(('MISMATCH', 'FIXTURE', 'COVERAGE'))][:3],
                         ret_edge_offsets_vs_plan=offs, witness=str(wit.relative_to(ROOT))))
    for r in runs:
        r['pass'] = r.pop('pass_')
    base = [r for r in runs if not r['mutant'] and r['calendar'] in ('measured_class', 'measured_shape',
                                                                     'predicted_lane_shift')]
    muts = [r for r in runs if r['mutant']]
    rec = dict(schema='opentallas.s81_dv.bench_xsp.v1', bench='tools/s81_dv/layer_prog/xs/xs_bench.sh (+PH)',
               lowering='tools/s81_dv/layer_prog/xs_place.py', host=a.host, die_frame='u_f_0L00', runs=runs,
               base_pass=all(r['pass'] for r in base) and bool(base), mutants_fail=all(not r['pass'] for r in muts),
               measurements=[dict(name=r['name'], elem_class=r['elem_class'], offsets=r['ret_edge_offsets_vs_plan'],
                                  values_exact=not r['value_errors']) for r in runs
                             if not r['mutant'] and r['calendar'] not in ('measured_class', 'measured_shape',
                                                                              'predicted_lane_shift')])
    rec['pass'] = rec['base_pass'] and rec['mutants_fail'] and bool(muts)
    (res / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_PLACE_COLLECT pass={rec["pass"]} base={[(r["name"], r["pass"]) for r in base]} '
          f'mutants={[(r["name"], r["pass"]) for r in muts]} measurements={rec["measurements"]}')
    return 0 if rec['pass'] else 1


# ------------------------------------------------------------------------------------------------ compiler hook
BENCHP = 'results/rtl/s81_layer_tput_1018/compiler/bench_xsp'
BENCH_RECORDS = [BENCHP + '4', BENCHP + '2', BENCHP]   # bench_xsp4 = current field (per-segment terms legalised in)
OPS = [r'^attn\.(wq_b|wo_a|wo_b|idx\.q|cmp\.wk)$', r'^ffn\.(router|shared_gu|experts_gu|down)$', r'^eng\.wkv$']
REST = ('per-phase slice xs programme (calendar action / time ROMs, is_d GO, gathers: xs_calendar.py gen) and cap cfg_d '
        '(xs_calendar.py cap) are emitted and benched (bench_xs_slice: ot_s81sl_xs drives the frame, cycle-exact = plan + D); '
        'open: xs_place frame images still tag rows phase-local 0..R-1 (the cap needs the rank-local row: gen --tags rank '
        'proves the rewrite, the image writer must emit it), and the die-wide multi-phase xs calendar (all phases of the '
        'layer + one gather per x vector in one calendar) is not compiled')
XS_SLICE_BENCH = 'results/rtl/s81_layer_tput_1018/compiler/bench_xs_slice'


def lower_placed(die, op, ctx):
    name = op['op']
    rec = dict(unit='frames (multi-phase cfg7 field, element ROMs) + frame return plan + slice xs phase / stream ROMs',
               insts=[], rows=[], templates=[], gunit_rows=[], svc_jobs=[], events=[], bench=BENCHP, files={})
    if name in NOT_PLACED:
        return dict(rec, status='GAP', gap=dict(module='tools/s81_dv/layer_prog/xs_place.py', port='bf pairs',
                                                missing=NOT_PLACED[name]))
    if not ctx.get('fixtures'):
        return dict(rec, status='GAP', gap=dict(module='xs_place', port='fixtures', missing='no --fixtures'))
    fx = Fix(ctx['fixtures'])
    sl = ctx['slice']
    g = LX.slice_index(die, sl)
    rec['insts'] = die.frames_of(sl) + [sl]
    import xs_bf as XB
    if name in XB.BF_OPS:
        return lower_placed_bf(die, op, ctx, rec, fx, sl, g)
    seq = phase_list(fx, [name])
    mats = []
    for gi, grp in enumerate(op_groups(fx, name)):
        f = fmt_of(fx, grp['mat'])
        K = fx.w(grp['mat']).shape[1] * (2 if f == 'fp4' else 1)
        nseg, units = nseg_for(f, K, NPAIRS)
        mats.append(dict(mat=grp['mat'], fmt=f, K=K, nseg=nseg, rows_per_phase=2 * (NPAIRS // nseg),
                         phases=sum(1 for x in seq if x[1] == gi), rows_per_frame=[len(fr) for fr in grp['groups'][g]],
                         calendar='measured_class' if (f, K, nseg) in ELEM_SEG else 'calendar_unmeasured',
                         tie='fixture' if grp['tie'] else 'golden', note=grp.get('note')))
    bench = None
    for bd in BENCH_RECORDS:          # newest first: the per-segment calendar record, then the validation / first runs
        bp = ROOT / bd / 'check.json'
        if bench is None and bp.exists():
            b = json.loads(bp.read_text())
            bench = next((dict(r, record=bd) for r in b.get('runs', []) if r['op'] == name and r.get('pass')), None)
    rec['files'] = {f'prog/xs/{op["id"]}.json': json.dumps(dict(
        schema='opentallas.s81_dv.xs_place.v1', op=op, slice=sl, slice_index=g, phases_die_wide=len(seq), mats=mats,
        bench=bench, images='python3 tools/s81_dv/layer_prog/xs_place.py frame --frame <inst> --out DIR (all phases of '
        'the frame field; gen --op OP for one phase\'s bench vectors)'), indent=1) + '\n'}
    unm = sorted({m['mat'] for m in mats if m['calendar'] != 'measured_class'})
    miss = REST + ('' if bench else '; this op has no frame bench of its own (the placement compiler is benched on '
                   'another op of the same field)') + (f'; element-work term unmeasured for {unm} (calendar not '
                                                      'cycle-exact until one bench of that class)' if unm else '')
    return dict(rec, status='PARTIAL', gap=dict(module='ot_s81sl_xs / ot_s81sl_cap', port='pq_calendar_action / '
                                                'pq_calendar_time ROMs, is_d (GO ph np), cap cfg_d', missing=miss))


BENCHB = 'results/rtl/s81_layer_tput_1018/compiler/bench_xsb'


def lower_placed_bf(die, op, ctx, rec, fx, sl, g):
    """a BF16 pair op (xs_bf.py): placed on the slice's frames' BF pairs; per frame and die-wide phase the shape key
    (master, lane latency, K, nseg, rows) is MEASURED (xs_bf.MEAS: programme descriptors + emission) or not"""
    import frame_bench as B
    import xs_bf as XB
    name = op['op']
    meas = XB.load_meas()
    rec = dict(rec, unit='frames: BF pairs (dsfd_bf_front_roots + 2 dsfd_bf_col, cfg7_seq_bfp static programme in the cfg '
                          'spare columns) + frame return plan + slice xs phase / stream ROMs', bench=BENCHB)
    seq = bf_phase_list(fx, [name], XB.BF_PAIRS_DIE)
    frames = []
    unm = set()
    for j, fr in enumerate(die.frames_of(sl)):
        master, E = LX.base_master(die.inst[fr]['master']), LX.land_e(die.strap(fr, 'lk'))
        _, bfp = B.frame_pairs(master)
        key = XB.shape_key(master, E)
        _, how = XB.meas_for(meas, master, E)
        if how is None:
            unm.add(key)
        rows = [len(XB.bf_groups(fx, op_)[gi]['groups'][g][j][c * R:(c + 1) * R]) for op_, gi, c, s, n, R, most in seq]
        frames.append(dict(frame=fr, master=master, land_e=E, bf_pairs=bfp, shape=key, calendar=how or 'calendar_unmeasured',
                           phases=len(seq), rows_per_phase=rows))
    bench = None
    bp = ROOT / BENCHB / 'check.json'
    if bp.exists():
        b = json.loads(bp.read_text())
        bench = next((dict(r, record=BENCHB) for r in b.get('runs', []) if r['op'] == name and r.get('pass')
                      and not r.get('mutant') and not r.get('measure')), None)
    rec['files'] = {f'prog/xs/{op["id"]}.json': json.dumps(dict(
        schema='opentallas.s81_dv.xs_place_bf.v1', op=op, slice=sl, slice_index=g, phases_die_wide=len(seq),
        frames=frames, bench=bench, measured_shapes=sorted({f['shape'] for f in frames} - unm),
        unmeasured_shapes=sorted(unm),
        images='python3 tools/s81_dv/layer_prog/xs_place.py frame --frame <inst> --out DIR (BF phases appended after '
        'the FP8 / FP4 phases; gen --op OP for one phase\'s bench vectors)'), indent=1) + '\n'}
    miss = REST + ('' if bench else '; no production frame bench PASS of this op yet') + (
        f'; programme / emission unmeasured for shapes {sorted(unm)} (BF_LEGACY measurement run of each shape owed)'
        if unm else '')
    return dict(rec, status='PARTIAL', gap=dict(module='ot_s81sl_xs / ot_s81sl_cap', port='pq_calendar_action / '
                                                'pq_calendar_time ROMs, is_d (GO ph np), cap cfg_d', missing=miss))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    t = sp.add_parser('tie')
    t.add_argument('--fixtures', default=str(LX.FIX))
    t.add_argument('--ops', nargs='*')
    t.add_argument('--layer', default='L0')
    t.add_argument('--out')
    import dv_layer_compile as C
    f = sp.add_parser('frame')
    f.add_argument('--frame', default='u_f_0L00')
    f.add_argument('--out', required=True)
    f.add_argument('--fixtures', default=str(LX.FIX))
    f.add_argument('--die-ref', default=C.DIE_REF)
    f.add_argument('--die-src', default=None)
    f.add_argument('--ops', nargs='*')
    f.add_argument('--iters', type=int, default=LX.ITERS)
    f.add_argument('--only', type=int, nargs='*', default=None)
    g = sp.add_parser('gen')
    g.add_argument('--frame', default='u_f_0L00')
    g.add_argument('--op', default=None)
    g.add_argument('--nth', type=int, default=0, help='the nth non-empty phase of the op on this frame')
    g.add_argument('--phase', type=int, nargs='*', default=None, help='field phase indices: one vector dir OUT/p<k> each')
    g.add_argument('--out', required=True)
    g.add_argument('--fixtures', default=str(LX.FIX))
    g.add_argument('--die-ref', default=C.DIE_REF)
    g.add_argument('--die-src', default=None)
    g.add_argument('--ops', nargs='*')
    g.add_argument('--iters', type=int, default=LX.ITERS)
    g.add_argument('--mutant', choices=('swap', 'shift', 'desc'), default=None)
    g.add_argument('--bf-measure', action='store_true', help='BF phase: measurement vector (BF_LEGACY bench build)')
    c = sp.add_parser('check')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    c.add_argument('--fixtures', default=None)
    k = sp.add_parser('collect')
    k.add_argument('--out', required=True)
    k.add_argument('--host', default=None)
    k.add_argument('--res', default=None, help='results dir (repo-relative); default the bench_xsp record')
    k.add_argument('--fixtures', default=None)
    k.add_argument('vec', nargs='+')
    a = ap.parse_args(argv)
    return {'tie': cmd_tie, 'frame': cmd_frame, 'gen': cmd_gen, 'check': cmd_check, 'collect': cmd_collect}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
