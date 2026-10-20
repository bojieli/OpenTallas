#!/usr/bin/env python3
"""TOKSIM-S81D/APSP (10-20): place the sparse-layer a_proj NODE's extra rows -- compressor.wkv (+ compressor.wgate at
ratio 2) and indexer.weights_proj, BF16 [rows, 5120], x = attn_norm (the a_proj x) -- in the DV field compiler, as BF16
pair phases emitted FIRST after the a_proj phase (field phases 1..5), and write bench vectors of the whole node.

xs_place.py (TOK-S81-GAPS/XS) places none of these rows (not in XS_OPS / BF_OPS).  This module adds ONE die-wide BF op
`attn.cmp_idx` to xs_bf (no edit of xs_place / xs_bf: registered at import):
  rows      every tensor's rank rows dealt as every xs op (deal over the 16 slices, then over the 8 frames of the slice):
            compressor.wkv 128 -> 1 / frame, compressor.wgate 128 -> 1 / frame, weights_proj 32 (replicated on every
            rank, die_slices) -> frames 0 and 1 of every slice; the frame's rows of all tensors form ONE BF row chunk
            (<= 2 x BF_PAIRS_DIE = 6 rows: super row R on BF pair R), so the node costs one chunk x 5 BSEG segments =
            5 BF phases per frame (xs_bf ABI: one 1,024-element K segment per phase), not 5 per tensor
  golden    xs_bf.bf_vals (exact BF16 products, csum per BSEG segment, segment-tree fold = hdc_golden_v41 mv chunk8)
  tie       compressor rows: ops/attn.cmp.wkv (ratio 2 FP32 = mv; ratio 1 BF16 = linear_bf16);
            weights_proj rows: ops/attn.idx.weights = to_bf16(mul(bf16(acc), index_w_scale)) -- tied by this module's
            check (tie_scaled), the xs_place tie skips them
  order     XP.compile_frame(ops=['attn.cmp_idx', ...]): phase 0 = a_proj (lower_xs), phases 1..5 = attn.cmp_idx (the
            BF list runs before any other BF op), i.e. the rows that gate the compressor / indexer chain go FIRST.

    toksim_apsp_place.py gen --layer L2 --frame u_f_0L00 --fixtures FIX --die-src DIE --out VEC [--ops ...]
        -> VEC/p0 (a_proj phase 0 in the SAME multi-phase field images), VEC/p<k> per cmp_idx phase, m_{swap,shift}_p<k1>,
           seq_all/ (phase 0 + the cmp_idx phases, +PHASE_VM per-phase x), seq_bf/ (cmp_idx phases only), frame.json
    toksim_apsp_place.py seqcheck --seq SEQ --vec VEC --log RUN.LOG --out RES.json --per P   (toksim_fgu_check seq +
        the weights_proj tie_scaled check)
"""
import argparse
import hashlib
import json
import re
import shutil
import struct
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
import xs_place as XP  # noqa: E402
import xs_bf as XB  # noqa: E402
import lower_xs as LX  # noqa: E402
import numpy as np  # noqa: E402

OP = 'attn.cmp_idx'
NSLICE, NFRAME = XB.NSLICE, XB.NFRAME

# an op chunk with no rows on a frame gives a float64 empty index (as toksim_fsmall_gen.py)
_fm_init = XP.FMat.__init__


def _fm_init_int(self, name, fmt, arr, sc, rows, phase):
    _fm_init(self, name, fmt, arr, sc, np.asarray(rows, dtype=np.int64), phase)


XP.FMat.__init__ = _fm_init_int


def parts_of(fx):
    """[(tensor, u16 [rows, K], tie op, tie index base, tie kind)] of the node's BF rows present in the fixture"""
    F, out = fx.files, []
    if 'weights/compressor.wkv.bin' in F:
        r2 = 'weights/compressor.wgate.bin' in F
        r0 = (F['weights/compressor.wkv.bin'].get('rows') or [0])[0]
        n = fx.op('attn.cmp.wkv').size // (2 if r2 else 1)
        out.append(('compressor.wkv', fx.w('compressor.wkv').view('<u2'), 'attn.cmp.wkv', r0, 'fp32' if r2 else 'bf16'))
        if r2:
            out.append(('compressor.wgate', fx.w('compressor.wgate').view('<u2'), 'attn.cmp.wkv', n + r0, 'fp32'))
    if 'weights/indexer.weights_proj.bin' in F:
        out.append(('indexer.weights_proj', fx.w('indexer.weights_proj').view('<u2'), 'attn.idx.weights', 0,
                    'bf16_scaled'))
    return out


def cmp_idx_group(fx):
    parts = parts_of(fx)
    assert parts, 'fixture holds no compressor / indexer weights_proj rows'
    u, tie, kinds, src, groups = [], [], [], [], [[[] for _ in range(NFRAME)] for _ in range(NSLICE)]
    off = 0
    for name, w, top, base, kind in parts:
        n = w.shape[0]
        for gi, js in enumerate(XB.deal(n, NSLICE)):
            for fi, fr in enumerate(XB.deal_into(js, NFRAME)):
                groups[gi][fi] += [off + r for r in fr]
        u.append(w)
        tie += [(top, base + r) for r in range(n)]
        kinds += [kind] * n
        src += [(name, r) for r in range(n)]
        off += n
    u = np.concatenate(u)
    return dict(mat='cmp_idx', u16=u, rows=list(range(u.shape[0])), x=fx.op('attn.norm.scale'), tie=tie,
                tie_kind='fp32' if 'fp32' in kinds else 'bf16', tie_kinds=kinds, src=src, groups=groups, out='mixed',
                parts=[(p[0], p[1].shape[0], p[2], p[3], p[4]) for p in parts])


_bfg = XB._bf_groups


def _bf_groups(fx, op):
    return [cmp_idx_group(fx)] if op == OP else _bfg(fx, op)


XB._bf_groups = _bf_groups
XB.BF_OPS = (OP,) + tuple(XB.BF_OPS)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def gen_p0(rec, field, fixd, frame, out, die):
    """the a_proj phase 0 as an xs_place-format vector of the SAME multi-phase field (its images = every phase's)"""
    import v41_die_images_w17w10 as I
    ph0 = rec['phases'][0]
    assert ph0['op'] == 'attn.a_proj' and ph0['phase'] == 0
    out.mkdir(parents=True, exist_ok=True)
    fxa = LX.load_fixture(fixd)
    _, pl = LX.placement(die, rec['slice'])
    p0 = pl[rec['frame_index']]
    mats, gidx = LX.frame_mats(fxa, p0['rows'])
    _f, _ph, plan, qa, _q, _bf = LX.frame_programme(rec['master'], rec['lk'], mats, fxa['x'])
    assert [list(w) for w in plan['ret']] == [list(w) for w in ph0['ret']], 'phase-0 replan differs from the field'
    names, tmp = XP.write_images(field, rec['pairs'], rec['q_pairs'], rec['bf_pairs'], frame, out)
    xsn = LX.xs_roms(tmp, out)
    for n in names:
        (out / ('f' + n[len(frame):])).write_text((out / n).read_text())
    gold = I.golden_phase(mats, fxa['x'])
    rows = {str(r): dict(vals=plan['rows_vals'][str(r)], acc=gold[r][0], bf16=gold[r][1], src=list(mats[0].src[r]),
                         out_index=gidx[r], tie=['attn.a_proj', gidx[r]], tie_kind='bf16') for r in range(len(gidx))}
    vm = [int(struct.unpack('<I', struct.pack('<f', float(v)))[0]) for v in fxa['x']]
    (out / 'vm.hex').write_text(''.join(f'{v:08x}\n' for v in vm))
    pl_ = {k: v for k, v in plan.items() if k != 'stream'}
    T = max(w[0] for w in pl_['ret']) + 600
    meta = dict(op='attn.a_proj', field_phase=0, nphases=rec['nphases'], chunk=0, mat=mats[0].name, fmt='fp8',
                calendar='measured_class', master=LX.base_master(rec['master']), die_frame=frame,
                die_master=rec['master'], lk=rec['lk'], land_e=LX.land_e(rec['lk']), slice=rec['slice'],
                slice_index=rec['slice_index'], frame_index=rec['frame_index'], K=mats[0].K, nseg=LX.NSEG,
                pairs=rec['pairs'], nrows=len(gidx), rows=rows, cycles=T, plan=pl_, mutant=None, fill=rec['fill'],
                fixture=dict(dir=str(fixd), meta_sha256=sha(Path(fixd) / 'meta.json')),
                images={n: sha(out / n) for n in names + xsn + ['spine_phase.hex', 'spine_stream.hex']})
    (out / 'meta.json').write_text(json.dumps(meta, indent=1) + '\n')
    (out / 'ARGS').write_text(f'+OT_ROM_DIR={out.resolve()} +T={T} +K={mats[0].K} +OPS={len(gidx)} +PH=0\n')
    return meta


def patch_bf_meta(d, grp, fx):
    """per-row tie kind of the mixed node; weights_proj rows: tie_scaled (fixture = bf16(acc) x index_w_scale), checked
    here at generation and again by seqcheck; the xs_place tie skips them (tie None)"""
    import hdc_golden_v41 as G
    m = json.loads((d / 'meta.json').read_text())
    sc = G.F(fx.meta.get('index_w_scale') or (128 ** -0.5 * 32 ** -0.5))
    bad = []
    for r, v in m['rows'].items():
        ri = v['src'][1]
        kind = grp['tie_kinds'][ri]
        v['src'] = list(grp['src'][ri])
        v['tie_kind'] = kind
        if kind == 'bf16_scaled':
            want = scaled_tie(G, v['acc'], sc)
            fb = int(G.bits(G.F(fx.op('attn.idx.weights').reshape(-1)[v['tie'][1]])))
            v['tie_scaled'] = dict(op=v['tie'][0], index=v['tie'][1], scale=float(sc), want=f'{want:08x}', fixture=f'{fb:08x}')
            if fb != want:
                bad.append((r, f'{fb:08x}', f'{want:08x}'))
            v['tie'] = None
    (d / 'meta.json').write_text(json.dumps(m, indent=1) + '\n')
    assert not bad, ('weights_proj golden differs from the fixture', bad)
    return m


def scaled_tie(G, acc_bits, sc):
    a = np.array([acc_bits], dtype=np.uint32).view(np.float32)
    return int(G.bits(G.to_bf16(G.mul(G.to_bf16(a), sc)))[0])


def cmd_gen(a):
    import dv_layer_compile as C
    die = C.Die(C.die_tree(None, a.die_src))
    ops = a.ops or [OP]
    assert ops[0] == OP
    rec, field = XP.compile_frame(die, a.frame, a.fixtures, ops, iters=LX.ITERS)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fx = XP.Fix(a.fixtures)
    grp = cmp_idx_group(fx)
    summ = []
    have0 = bool(rec['phases'] and rec['phases'][0]['op'] == 'attn.a_proj')
    if have0:
        m0 = gen_p0(rec, field, a.fixtures, a.frame, out / 'p0', die)
        summ.append(dict(phase=0, op='attn.a_proj', rows=m0['nrows'], fmt='fp8', K=5120, calendar='measured_class',
                         faults=m0['plan']['faults'], ret_words=m0['plan']['ret_words']))
    ns = types.SimpleNamespace(fixtures=a.fixtures, frame=a.frame, mutant=None, bf_measure=False)
    bfp = [ph for ph in rec['phases'] if ph['op'] == OP and ph['rows'] > 0]
    for ph in bfp:
        assert ph['faults'] == 0 and ph['calendar'] in ('measured_shape', 'predicted_lane_shift'), \
            (ph['phase'], ph['calendar'], ph['faults'])
        XP.gen_one(ns, rec, field, ph, out / f'p{ph["phase"]}')
        patch_bf_meta(out / f'p{ph["phase"]}', grp, fx)
        summ.append(dict(phase=ph['phase'], op=OP, rows=ph['rows'], fmt='bf16', K=ph['K'], seg=ph['seg'], nseg=ph['nseg'],
                         calendar=ph['calendar'], faults=ph['faults'], ret_words=ph['ret_words'],
                         src=[grp['src'][i] for i in ph['row_index']]))
    if bfp:
        for mu in ('swap', 'shift'):
            d = out / f'm_{mu}_p{bfp[0]["phase"]}'
            XP.gen_one(types.SimpleNamespace(fixtures=a.fixtures, frame=a.frame, mutant=mu, bf_measure=False), rec, field,
                       bfp[0], d)
            patch_bf_meta(d, grp, fx)
    seqs = {}
    for name, phs in (('seq_all', ([0] if have0 else []) + [p['phase'] for p in bfp]), ('seq_bf', [p['phase'] for p in bfp])):
        if len(phs) < 2:
            continue
        sd = out / name
        if sd.exists():
            shutil.rmtree(sd)
        d0 = out / f'p{phs[0]}'
        shutil.copytree(d0, sd)
        (sd / 'meta.json').unlink()
        (sd / 'ARGS').unlink()
        ms = [json.loads((out / f'p{k}' / 'meta.json').read_text()) for k in phs]
        for mk in ms[1:]:
            assert mk['images'] == ms[0]['images'], ('field images differ across phases', mk['field_phase'])
        for k in phs:
            (sd / f'p{k}').mkdir()
            shutil.copy(out / f'p{k}' / 'vm.hex', sd / f'p{k}' / 'vm.hex')
        (sd / 'seq.hex').write_text(''.join(f'{(max(1, mk["nrows"]) << 16) | mk["field_phase"]:08x}\n' for mk in ms))
        w = [len(mk['plan']['ret']) for mk in ms]
        (sd / 'seqw.hex').write_text(''.join(f'{x:04x}\n' for x in w))
        (sd / 'seq.json').write_text(json.dumps(dict(op=name, layer=a.layer, frame=a.frame, phases=phs,
                                                     ops=[mk['op'] for mk in ms], rows=[mk['nrows'] for mk in ms],
                                                     K=ms[0]['K'], ret_words=w, phase_vm=True,
                                                     vectors=[f'p{k}' for k in phs]), indent=1) + '\n')
        seqs[name] = dict(dir=str(sd), nph=len(phs), K=ms[0]['K'], ops=max(max(1, mk['nrows']) for mk in ms), ph0=phs[0])
    fr = dict(layer=a.layer, frame=a.frame, master=rec['master'], lk=rec['lk'], base=LX.base_master(rec['master']),
              land_e=LX.land_e(rec['lk']), slice=rec['slice'], slice_index=rec['slice_index'],
              frame_index=rec['frame_index'], nphases=rec['nphases'], field_ops=ops, parts=grp['parts'],
              node_rows_per_rank=448 + len(grp['rows']), phases=summ, seqs=seqs,
              fixture_meta_sha256=sha(Path(a.fixtures) / 'meta.json'))
    (out / 'frame.json').write_text(json.dumps(fr, indent=1) + '\n')
    for k, v in seqs.items():
        print('SEQ', k, v['dir'], v['nph'], v['K'], v['ops'], v['ph0'])
    print('TOKSIM_APSP_GEN', a.layer, a.frame, rec['master'], 'phases', [(s['phase'], s['op'], s['rows']) for s in summ])
    return 0


def cmd_seqcheck(a):
    """toksim_fgu_check seq (xs_place check of record per phase) + the weights_proj scaled fixture tie of every row"""
    import toksim_fgu_check as FC
    import hdc_golden_v41 as G
    sys.argv = ['toksim_fgu_check.py', 'seq', '--seq', a.seq, '--vec', a.vec, '--log', a.log, '--out', a.out,
                '--ref-go', str(a.ref_go)] + (['--per', str(a.per)] if a.per else [])
    ns = argparse.Namespace(seq=a.seq, vec=a.vec, log=a.log, out=a.out, per=a.per, ref_go=a.ref_go, fixtures=None)
    rc = FC.cmd_seq(ns)
    res = json.loads(Path(a.out).read_text())
    sq = json.loads((Path(a.seq) / 'seq.json').read_text())
    nt, bad = 0, []
    for vec in sq['vectors']:
        m = json.loads((Path(a.vec) / vec / 'meta.json').read_text())
        fx = XP.Fix(m['fixture']['dir'])
        for r, v in m['rows'].items():
            t = v.get('tie_scaled')
            if not t:
                continue
            fb = int(G.bits(G.F(fx.op(t['op']).reshape(-1)[t['index']])))
            if fb != scaled_tie(G, v['acc'], G.F(t['scale'])):
                bad.append((vec, r))
            nt += 1
    res['scaled_tie_rows'], res['scaled_tie_bad'] = nt, bad
    res['pass'] = bool(res['pass'] and not bad)
    Path(a.out).write_text(json.dumps(res, indent=1) + '\n')
    print(f'TOKSIM_APSP_SEQ {"PASS" if res["pass"] else "FAIL"} {sq["op"]} {sq["frame"]} PER {a.per} phases {res["nph"]} '
          f'rows {res["rows"]} fixture_rows {res["fixture_rows"]} scaled_tie {nt - len(bad)}/{nt} go0 {res["go0"]} '
          f'last_ret {res["last_ret"]} span {res["go0_to_last_ret"]} errors {len(res["errors"])} {res["errors"][:2]}')
    return 0 if res['pass'] else 1


def cmd_single(a):
    """xs_place check of a single-phase run + the scaled tie"""
    import hdc_golden_v41 as G
    rc = XP.cmd_check(argparse.Namespace(dir=a.dir, log=a.log, fixtures=None))
    m = json.loads((Path(a.dir) / 'meta.json').read_text())
    fx = XP.Fix(m['fixture']['dir'])
    nt = bad = 0
    for r, v in m['rows'].items():
        t = v.get('tie_scaled')
        if t:
            nt += 1
            bad += int(G.bits(G.F(fx.op(t['op']).reshape(-1)[t['index']]))) != scaled_tie(G, v['acc'], G.F(t['scale']))
    print(f'APSP_SCALED_TIE {nt - bad}/{nt}')
    return rc or (1 if bad else 0)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = p.add_subparsers(dest='cmd', required=True)
    g = s.add_parser('gen')
    g.add_argument('--layer', required=True)
    g.add_argument('--frame', required=True)
    g.add_argument('--fixtures', required=True)
    g.add_argument('--die-src', required=True)
    g.add_argument('--out', required=True)
    g.add_argument('--ops', nargs='*', default=None)
    q = s.add_parser('seqcheck')
    q.add_argument('--seq', required=True)
    q.add_argument('--vec', required=True)
    q.add_argument('--log', required=True)
    q.add_argument('--out', required=True)
    q.add_argument('--per', type=int, default=None)
    q.add_argument('--ref-go', type=int, default=63)
    c = s.add_parser('single')
    c.add_argument('--dir', required=True)
    c.add_argument('--log', required=True)
    a = p.parse_args()
    return {'gen': cmd_gen, 'seqcheck': cmd_seqcheck, 'single': cmd_single}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
