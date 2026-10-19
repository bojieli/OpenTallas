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
golden-aligned split whose segments all share one unit class.  The phase's element-work term (lower_xs.ELEM_EXTRA) is
MEASURED per (units / segment, rows / element) class on the frame bench; a class without a measurement is placed and
imaged but its calendar is reported 'calendar_unmeasured' (no cycle-exact claim).

    xs_place.py tie   [--fixtures D]                         golden of every placed row == the layer fixture (no RTL)
    xs_place.py frame --frame u_f_0L00 --out DIR [--ops ...]  compile one frame's multi-phase field + images
    xs_place.py gen   --frame F --op OP --phase-of-op N --out VEC [--mutant swap|shift]   bench vectors of one phase
    xs_place.py check --dir VEC --log RUN.LOG                  cycle-exact + bit-exact check (lower_xs.check_words)
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
NOT_PLACED = {
    'attn.wo_a': 'grouped BF16 matvec (golden matvec_c = csum(mul(dequant fp8 w, bf16(o)))): needs BF16-pair phases '
                 '(bf elements, i_fmt bf16 x family) and the 8-head group x per row group; not placed',
    'attn.cmp.wk': 'compressor wkv / wgate are BF16 [128, 10240 B]: BF16-pair phases (bf elements); not placed',
    'ffn.router': 'BF16 gate (96 rows) on the bf pairs, FP32 output (no BF16 round): needs BF16-pair phases; not placed',
}


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
    plan = P.plan_phase(LX.base_master(die_frame_master), pairs, mat, x, nseg, iters=iters, land_e=LX.land_e(lk))
    plan['assign_slots'] = [(i + off, R, sg) for i, R, sg in plan['assign_slots']]
    units = {S.unit_range(mat.fmt, a0, el)[1] - S.unit_range(mat.fmt, a0, el)[0] for a0, el in S.segments(mat.K, nseg)}
    cls = (mat.fmt, units.pop(), 2)
    x_ = ELEM_EXTRA.get(cls)
    plan['elem_class'] = list(cls)
    plan['calendar'] = 'measured_class' if x_ is not None else 'calendar_unmeasured'
    if x_ is not None:
        plan['ret'] = [[w_[0] + x_] + list(w_[1:]) for w_ in plan['ret']]
        plan['emission'] = dict(plan['emission'], elem_extra=x_,
                                edges={k: v + x_ for k, v in plan['emission']['edges'].items()})
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
    field = I.Field(16, 1, 0, depth=8192, active=len(qa), pp=True, fast=True)
    if p0['rows']:
        ph = add_planned(field, dict(plan0, assign_slots=plan0['assign_slots'],
                                     stream=_f.stream[_ph['sbase']:_ph['sbase'] + _ph['nbeat']]), mats[0], LX.NSEG)
        phases.append(dict(phase=0, op='attn.a_proj', mat=mats[0].name, rows=len(gidx), out_index=gidx, nseg=LX.NSEG,
                           nbeat=ph['nbeat'], faults=plan0['faults'], ret_words=plan0['ret_words'],
                           calendar='measured_class', ret=plan0['ret']))
    groups = {op: op_groups(fx, op) for op in ops}
    for op, gi, c, nseg, R in phase_list(fx, ops):
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
    fill = [int(v) for v in field.fill]
    return dict(frame=frame, master=master, lk=lk, slice=sl, slice_index=g, frame_index=j, pairs=qa, q_pairs=q,
                bf_pairs=bf, phases=phases, fill=fill, depth=field.depth, nphases=len(field.phases)), field


def write_images(field, qa, q, bf, inst, out):
    """all phases: element via-maps + il7 cfg banks (word w of phase p in bank w % 7 row 4 p + w // 7) + xs ROMs"""
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
    nph = len(field.cfg)
    assert 4 * nph <= 4096, ('cfg7 bank rows', nph)
    for k in q + bf:
        banked = [[0] * 4096 for _ in range(7)]
        for p in range(nph):
            words = field.cfg[p][slot_of[k]] if k in slot_of else [0] * 25
            for w_, v in enumerate(words):
                banked[w_ % 7][4 * p + w_ // 7] = v
        for jb in range(7):
            (out / f'{inst}_c{k}_{jb}.viamap.hex').write_text(''.join(f'{w:0144x}\n' for w in encode_bank(banked[jb])))
            names.append(f'{inst}_c{k}_{jb}.viamap.hex')
    return names, tmp


def cmd_frame(a):
    import dv_layer_compile as C
    die = C.Die(C.die_tree(a.die_ref, a.die_src))
    rec, field = compile_frame(die, a.frame, a.fixtures, a.ops or XS_OPS['L0'], iters=a.iters,
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
    rec, field = compile_frame(die, a.frame, a.fixtures, a.ops or XS_OPS['L0'], iters=a.iters)
    cand = [p for p in rec['phases'] if p['op'] == a.op and p['rows'] > 0]
    ph = cand[a.nth]
    k = ph['phase']
    fx = Fix(a.fixtures)
    grp = op_groups(fx, a.op)[ph['gi']]
    mat = make_mat(fx, grp, ph['sel'], a.op)
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
    meta = dict(op=a.op, field_phase=k, nphases=rec['nphases'], chunk=ph['chunk'], mat=ph['mat'], fmt=mat.fmt,
                calendar=ph['calendar'], elem_class=ph['elem_class'], master=LX.base_master(rec['master']),
                die_frame=a.frame, die_master=rec['master'], lk=rec['lk'], land_e=LX.land_e(rec['lk']),
                slice=rec['slice'], slice_index=rec['slice_index'], frame_index=rec['frame_index'], K=mat.K,
                nseg=ph['nseg'], pairs=rec['pairs'], nrows=mat.rows, rows={str(r): v for r, v in rows.items()},
                cycles=T, plan=plan, mutant=a.mutant, fill=rec['fill'],
                fixture=dict(dir=str(a.fixtures), meta_sha256=sha((Path(a.fixtures) / 'meta.json').read_bytes())),
                images={n: sha((out / n).read_bytes()) for n in names + xsn})
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={T} +K={mat.K} +OPS={mat.rows} +PH={k}\n')
    print(f'XS_PLACE_GEN {a.frame} op {a.op} phase {k}/{rec["nphases"]} mat {ph["mat"]} rows {mat.rows} nseg {ph["nseg"]} '
          f'faults {plan["faults"]} ret_words {plan["ret_words"]} calendar {ph["calendar"]} T {T} mutant {a.mutant}')
    return 0


def cmd_check(a):
    import hdc_golden_v41 as G
    d = Path(a.dir)
    meta = json.loads((d / 'meta.json').read_text())
    errs, summ = LX.check_words(meta, Path(a.log).read_text())
    fx = Fix(a.fixtures or meta['fixture']['dir'])
    tied = 0
    for r, v in meta['rows'].items():
        if not v['tie']:
            continue
        fb = int(G.bits(G.F(fx.op(v['tie'][0]).reshape(-1)[v['tie'][1]])))
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
    res = ROOT / BENCHP
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
    base = [r for r in runs if not r['mutant'] and r['calendar'] == 'measured_class']
    muts = [r for r in runs if r['mutant']]
    rec = dict(schema='opentallas.s81_dv.bench_xsp.v1', bench='tools/s81_dv/layer_prog/xs/xs_bench.sh (+PH)',
               lowering='tools/s81_dv/layer_prog/xs_place.py', host=a.host, die_frame='u_f_0L00', runs=runs,
               base_pass=all(r['pass'] for r in base) and bool(base), mutants_fail=all(not r['pass'] for r in muts),
               measurements=[dict(name=r['name'], elem_class=r['elem_class'], offsets=r['ret_edge_offsets_vs_plan'],
                                  values_exact=not r['value_errors']) for r in runs
                             if not r['mutant'] and r['calendar'] != 'measured_class'])
    rec['pass'] = rec['base_pass'] and rec['mutants_fail'] and bool(muts)
    (res / 'check.json').write_text(json.dumps(rec, indent=1) + '\n')
    print(f'XS_PLACE_COLLECT pass={rec["pass"]} base={[(r["name"], r["pass"]) for r in base]} '
          f'mutants={[(r["name"], r["pass"]) for r in muts]} measurements={rec["measurements"]}')
    return 0 if rec['pass'] else 1


# ------------------------------------------------------------------------------------------------ compiler hook
BENCHP = 'results/rtl/s81_layer_tput_1018/compiler/bench_xsp'
OPS = [r'^attn\.(wq_b|wo_a|wo_b|idx\.q|cmp\.wk)$', r'^ffn\.(router|shared_gu|experts_gu|down)$', r'^eng\.wkv$']
REST = ('the slice xs CALENDAR images (75-b action words: stream requests, VM responses, cfg / launch / retire), the is_d '
        'GO word per phase and the cap write-back cfg_d (row tag -> owning slice row) for the DV placement are not '
        'emitted; no bench drives ot_s81sl_xs into a frame (the frame bench drives the frame through the w17w10 spine '
        'with the same phase / stream words)')


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
    seq = phase_list(fx, [name])
    mats = []
    for gi, grp in enumerate(op_groups(fx, name)):
        f = fmt_of(fx, grp['mat'])
        K = fx.w(grp['mat']).shape[1] * (2 if f == 'fp4' else 1)
        nseg, units = nseg_for(f, K, NPAIRS)
        mats.append(dict(mat=grp['mat'], fmt=f, K=K, nseg=nseg, rows_per_phase=2 * (NPAIRS // nseg),
                         phases=sum(1 for x in seq if x[1] == gi), rows_per_frame=[len(fr) for fr in grp['groups'][g]],
                         calendar='measured_class' if (f, units, 2) in ELEM_EXTRA else 'calendar_unmeasured',
                         tie='fixture' if grp['tie'] else 'golden', note=grp.get('note')))
    bench = None
    bp = ROOT / BENCHP / 'check.json'
    if bp.exists():
        b = json.loads(bp.read_text())
        bench = next((r for r in b.get('runs', []) if r['op'] == name and r.get('pass')), None)
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
    g.add_argument('--op', required=True)
    g.add_argument('--nth', type=int, default=0, help='the nth non-empty phase of the op on this frame')
    g.add_argument('--out', required=True)
    g.add_argument('--fixtures', default=str(LX.FIX))
    g.add_argument('--die-ref', default=C.DIE_REF)
    g.add_argument('--die-src', default=None)
    g.add_argument('--ops', nargs='*')
    g.add_argument('--iters', type=int, default=LX.ITERS)
    g.add_argument('--mutant', choices=('swap', 'shift'), default=None)
    c = sp.add_parser('check')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    c.add_argument('--fixtures', default=None)
    k = sp.add_parser('collect')
    k.add_argument('--out', required=True)
    k.add_argument('--host', default=None)
    k.add_argument('--fixtures', default=None)
    k.add_argument('vec', nargs='+')
    a = ap.parse_args(argv)
    return {'tie': cmd_tie, 'frame': cmd_frame, 'gen': cmd_gen, 'check': cmd_check, 'collect': cmd_collect}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
