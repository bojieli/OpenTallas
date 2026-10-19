#!/usr/bin/env python3
"""dv_layer_fixture: REAL stage operands + ISA-golden stage outputs for the Qwen compute-die DV slice benches
(QW-REALSTG 10-19; rtl/test/qwen_dv/dv_lower_vec_bench.py / dv_lower_mat_bench.py --fixture).

    dv_layer_fixture.py tp4  --img 'IMG/L{layer}-d{die}' --realmem fx/realmem/P8191 --layer N --out DIR
    dv_layer_fixture.py tp8w --img 'TP8IMG/L{layer}/die{die}' --layer N --out DIR     (weight-row identity check)

tp4 (env QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8, sys.path = the pinned gold tools tree
OT_GOLD_ROOT/tools, as fx/realmem was made): re-executes layer N of the TP4 ISA golden at the recorded position P
(qwen_rom_position_oracle_w12 machines: FastDieMachine dense = G.matvec order, ISA SU / attention, TP all-reduce =
G.fold in descriptor order) on all 4 dies, from the RECORDED state -- X = layer input (x_preload.hex for L0,
L<N-1>_die<d>_x.hex otherwise), KV window = kv_pre/L<N>_die<d>.npy -- with a VM snapshot after every PC and every
all-reduce.  Fail-closed reproduction checks: X after the layer == L<N>_die<d>_x.hex and the K / V rows written ==
kv_at_P/L<N>_die<d>.json on every die (so every snapshot IS the recorded ISA golden's state).

The stage operands are cut for the TP8 compute die 0 (4 q heads / kv head 0 / gate-up rows 0..1535 = a row subset of
TP4 die 0: q rows 0..511, k rows 1024..1151, v rows 1280..1407, GU interleaved rows 0..3071, ATTN 0..511):

  resid1 / resid2  x (X before the residual add), t (the all-reduce return T1), ps (CROM post-TP scale),
                   gold x' (X after PC20 / PC29) and r (RX: PC22 / PC2 of the same programme executed on the post-PC29 VM)
  qk               qkv (QKV after PC1, 768 TP8 rows), r (RX after PC2), q_norm / k_norm (CROM 4096.. gains), pos,
                   gold q (QR heads 0..3 after PC9), k / v (kv_at_P head 0 FP8-as-FP32 bits)
  silu             gu (GU after PC21, rows 0..3071), r (RX after PC22), gold act (ACT 0..1535 after PC24)
  mat_qkv / mat_gu w (int8 rows), s (BF16 row scales), x (the matvec input: X), gold y (QKV / GU after PC1 / PC21)
  mat_od           o: w (4096 x ATTN cols 0..511), x = ATTN 0..511; down: w (4096 x ACT cols 0..1535), x = ACT 0..1535;
                   s = CROM post-TP scales.  The TP8 partial sums (split 256) are TP8-gold-only: the TP4 golden folds
                   1,024 / 3,072-column partials (split 512), so no TP4 value exists for them.
TP-dependence: every stage FUNCTION above is TP-agnostic (row-local or whole-vector on every die); only the
all-reduce returns t (and so x', r of the residuals, gu / act downstream of resid1) carry the TP4 fold order.  With
TP4-folded inputs the stage outputs equal the TP4 golden's; the TP8 values need the TP8 golden (qwen_tp8_layer_gold).

tp8od (env QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8; QW-ODSCALE 10-19):
    dv_layer_fixture.py tp8od --img 'TP8IMG/L{layer}/die{die}' --tp8gold GOLD/P8191 --layer N --out DIR
  the od stage on the TP8 ISA golden (qwen_tp8_layer_gold --pc-dump, production TP8 fold): o x = die-0 ATTN_fp32.hex
  (the o-proj input), down x = ACT 0..1535 of die 0's VM after source PC24 (candidate_pc<k>_vm.npz, k from oracle.json
  original_to_candidate_pc), gold = collective<s>_partial.hex of die 0 (the RAW partial the die all-reduces: the AR
  segments of the image's descriptors, in order o then down); w / s = the TP8 die-0 image's own o / down columns
  (identical to the tp4 cut: tp8w).  Writes L<N>_mat_od_tp8.npz (bench keys o_* / down_* + o_gold_y / down_gold_y).

tp8w (env QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64): decodes the TP8 die-0 matrices and checks that the rows /
columns cut above are byte-identical to the TP8 die's own weights and scales (qkv, gu, o, down).

Not an RTL verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np

GROOT = Path(os.environ.get('OT_GOLD_ROOT', Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(GROOT / 'tools'))
import hdc_golden as G  # noqa: E402
import hdc_isa as I  # noqa: E402
import hdc_program as P  # noqa: E402
import hdc_qwen_fullshape_isa_w12 as QI  # noqa: E402
import hdc_qwen_fullshape_program_w12 as FP  # noqa: E402
import qwen_o4_layer0_oracle_w12 as L0  # noqa: E402
import qwen_rom_position_oracle_w12 as PO  # noqa: E402

F = np.float32
QKV_ROWS = np.r_[0:512, 1024:1152, 1280:1408]      # TP8 die 0 rows inside TP4 die 0 QKV (q h0..3 | k h0 | v h0)
GU_ROWS = np.r_[0:3072]                            # 12 (gate, up) 128-row pairs
O_COLS, DOWN_COLS = np.r_[0:512], np.r_[0:1536]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_hex(path):
    rows = [r.strip() for r in Path(path).read_text().split() if r.strip() and not r.startswith('@')]
    return G.from_bits(np.array([int(s, 16) for s in rows], dtype=np.uint32))


class Img(PO.StageImage):
    """the restored stage image (img_p1 manifests carry no tp / image_sha256: consumed by the digests recorded here)"""

    def __init__(self, directory, layer, tp):
        self.dir = Path(directory)
        self.manifest = json.loads((self.dir / f'layer{layer}_rom.json').read_text())
        if self.manifest['layer'] != layer:
            raise ValueError(f'layer mismatch in {directory}')
        self.manifest.setdefault('tp', tp)
        self.image_sha = {n: sha(self.dir / n) for n in ('program.hex', 'segments.hex', 'crom.hex',
                                                         'matrix_scale_bf16.hex', 'layer%d_rom.json' % layer)}
        self.layout = {row['base']: row for row in self.manifest['matrix_layout']}
        self.program = [QI.decode_instruction(int(x, 16)) for x in (self.dir / 'program.hex').read_text().split()]
        self.descriptors = [QI.decode_descriptor(int(x, 16)) for x in (self.dir / 'segments.hex').read_text().split()]
        lo, hi = [], []
        with (self.dir / 'crom.hex').open() as stream:
            for line in stream:
                line = line.strip()
                if not line or line.startswith('@'):
                    continue
                line = line.rjust(16, '0')
                hi.append(int(line[:8], 16))
                lo.append(int(line[8:16], 16))
        self.crom = np.stack((G.from_bits(np.array(lo, dtype=np.uint32)),
                              G.from_bits(np.array(hi, dtype=np.uint32))), axis=1)
        self._mat = {}

    def mat(self, name):
        meta = [m for m in self.layout.values() if m['name'] == name][0]
        return self.matrix(meta)


def run_tp4(a):
    if PO.TP != 4 or PO.GROUPS != 6144 or G.KV_FMT != 'fp8':
        raise SystemExit('tp4 needs QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8')
    n, rm = a.layer, Path(a.realmem)
    pos = int(rm.name.lstrip('P'))
    tok = json.loads((rm / 'embedding_row.json').read_text())['token']
    VM, W = L0.VM, L0.W
    ims = [Img(a.img.format(layer=n, die=d), n, 4) for d in range(4)]
    if any(im.descriptors != ims[0].descriptors for im in ims):
        raise SystemExit('TP4 descriptor mismatch')
    ms = [PO.FastDieMachine(im) for im in ims]
    src = {}
    for d, m in enumerate(ms):
        xf = rm / ('x_preload.hex' if n == 0 else f'L{n - 1:02d}_die{d}_x.hex')
        m.vm[:] = 0
        m.vm[VM['X']:VM['X'] + 4096] = read_hex(xf)
        kvf = rm / 'kv_pre' / f'L{n}_die{d}.npy'
        kv = np.load(kvf).astype(np.uint32)
        if kv.shape != m.kv.shape:
            raise SystemExit(f'kv_pre shape {kv.shape} != {m.kv.shape}')
        m.kv[:] = G.from_bits(kv)
        m.pos = pos
        src[f'die{d}'] = {'x_in': f'{xf.name} {sha(xf)}', 'kv_pre': f'{kvf.name} {sha(kvf)}'}
    snaps = {}                                      # die 0 VM after each PC ('pc<k>') and each all-reduce ('ar<i>')
    with FP.program_geometry(VM):
        dyns = [P.dyn_values(m.lay, token=tok, pos=pos) for m in ms]
        desc = ims[0].descriptors
        for si, seg in enumerate(desc):
            first = seg['program_base']
            end = desc[si + 1]['program_base'] if si + 1 < len(desc) else len(ims[0].program)
            for d, (m, im, dyn) in enumerate(zip(ms, ims, dyns)):
                for pc in range(first, end):
                    f = im.program[pc]
                    if f['unit'] == I.UNIT_ME:
                        m.me(f, dyn)
                    elif f['unit'] == I.UNIT_SU:
                        m.su(f, dyn)
                    if d == 0:
                        snaps[f'pc{pc}'] = m.vm.copy()
            if seg['kind'] == P.COLL_ALLREDUCE:
                lo, hi = seg['vm_word'] * W, (seg['vm_word'] + seg['words']) * W
                folded = G.fold([m.vm[lo:hi].copy() for m in ms])
                for m in ms:
                    m.vm[lo:hi] = folded
                snaps[f'ar{si}'] = ms[0].vm.copy()
            elif seg['kind'] != P.COLL_END:
                raise SystemExit('unexpected collective')
        # r of the second residual = PC2 (RX = rsqrt(SSX 2^-12 + eps)) of the same programme on the post-PC29 VM
        nxt = PO.FastDieMachine(ims[0])
        nxt.vm[:] = ms[0].vm
        nxt.pos = pos
        if ims[0].program[2]['unit'] != I.UNIT_SU or ims[0].program[2]['sfu'] != 3:
            raise SystemExit('PC2 is not the RX rsqrt')
        nxt.su(ims[0].program[2], dyns[0])
        r2 = F(nxt.vm[VM['RX']])
    # ---- reproduction of the recorded golden (fail closed)
    repro = {}
    for d, m in enumerate(ms):
        ref = read_hex(rm / f'L{n:02d}_die{d}_x.hex')
        ok_x = bool(np.array_equal(G.bits(ref), G.bits(m.vm[VM['X']:VM['X'] + 4096])))
        kp = json.loads((rm / 'kv_at_P' / f'L{n}_die{d}.json').read_text())
        ok_k = [f'{int(b):08x}' for b in G.bits(m.kv[kp['k_elem']])] == kp['k_bits']
        ok_v = [f'{int(b):08x}' for b in G.bits(m.kv[kp['v_elem']])] == kp['v_bits']
        repro[f'die{d}'] = dict(layer_x=ok_x, k_row=ok_k, v_row=ok_v)
    print('REPRO', json.dumps(repro), flush=True)
    if not all(all(v.values()) for v in repro.values()):
        raise SystemExit('the re-executed layer does not reproduce the recorded golden')
    kp0 = json.loads((rm / 'kv_at_P' / f'L{n}_die0.json').read_text())
    s = snaps
    im0 = ims[0]
    X, T1, RX = VM['X'], VM['T1'], VM['RX']
    ptsb = im0.manifest['post_tp_scale_bases']
    ps1, ps2 = im0.crom[ptsb[0]:ptsb[0] + 4096, 0].copy(), im0.crom[ptsb[1]:ptsb[1] + 4096, 0].copy()
    cb = im0.program[6]['c_base']                    # PC6 QN gains (CROM lo, one 128 row per head)
    q_norm, k_norm = im0.crom[cb:cb + 128, 0].copy(), im0.crom[cb + 8 * 128:cb + 9 * 128, 0].copy()
    if not np.array_equal(G.bits(im0.crom[cb + 128:cb + 256, 0]), G.bits(q_norm)):
        raise SystemExit('q_norm rows differ by head')
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    L = f'L{n}'
    stages = {}

    def save(name, **arrs):
        p = out / f'{L}_{name}.npz'
        np.savez_compressed(p, **arrs)
        stages[name] = dict(file=p.name, sha256=sha(p), keys=sorted(arrs))

    # the add / SSQ checks: T1 after the AR, X before / after the fused add (PC19 scale + PC20 add)
    save('resid1', x=s['pc18'][X:X + 4096], t=s['ar1'][T1:T1 + 4096], ps1=ps1,
         gold_x=s['pc20'][X:X + 4096], gold_r=np.array([s['pc22'][RX]], dtype=F), pos=pos)
    save('resid2', x=s['pc20'][X:X + 4096], t=s['ar3'][T1:T1 + 4096], ps1=ps2,
         gold_x=s['pc29'][X:X + 4096], gold_r=np.array([r2], dtype=F), pos=pos)
    qkv_all = s['pc1'][VM['QKV']:VM['QKV'] + 1536]
    qr = s['pc9'][VM['QR']:VM['QR'] + 512]
    save('qk', qkv=qkv_all[QKV_ROWS], r=np.array([s['pc2'][RX]], dtype=F), q_norm=q_norm, k_norm=k_norm, pos=pos,
         gold_q=qr, gold_k=G.from_bits(np.array([int(b, 16) for b in kp0['k_bits'][:128]], dtype=np.uint32)),
         gold_v=G.from_bits(np.array([int(b, 16) for b in kp0['v_bits'][:128]], dtype=np.uint32)))
    save('silu', gu=s['pc21'][VM['GU']:VM['GU'] + 3072], r=np.array([s['pc22'][RX]], dtype=F),
         gold_act=s['pc24'][VM['ACT']:VM['ACT'] + 1536], gu_r=s['pc23'][VM['GU']:VM['GU'] + 3072])
    wq, sq = im0.mat('qkv')
    save('mat_qkv', w=wq[QKV_ROWS].astype(np.int8), s=sq[QKV_ROWS], x=s['pc0'][X:X + 4096],
         gold_y=s['pc1'][VM['QKV']:VM['QKV'] + 1536][QKV_ROWS], split=512)
    wg, sg = im0.mat('gu')
    save('mat_gu', w=wg[GU_ROWS].astype(np.int8), s=sg[GU_ROWS], x=s['pc20'][X:X + 4096],
         gold_y=s['pc21'][VM['GU']:VM['GU'] + 3072], split=128)
    wo, so = im0.mat('o')
    wd, sd = im0.mat('down')
    save('mat_od', o_w=wo[:, O_COLS].astype(np.int8), o_s=so, o_x=s['pc15'][VM['ATTN']:VM['ATTN'] + 512],
         down_w=wd[:, DOWN_COLS].astype(np.int8), down_s=sd, down_x=s['pc24'][VM['ACT']:VM['ACT'] + 1536])
    rec = dict(schema='opentallas.qwen.dv-layer-fixture.v1', tool='tools/qwen_layerbench/dv_layer_fixture.py',
               layer=n, position=pos, token=tok, tp_gold=4, tp8_die=0,
               golden='TP4 ISA golden (fx/realmem, qwen_rom_position_oracle_w12 machines) re-executed for layer N at '
                      'P from the recorded X and kv_pre; reproduction checked bit-exact on every die',
               reproduction=repro, inputs=src,
               image_sha256={f'die{d}': im.image_sha for d, im in enumerate(ims)},
               gold_source_sha256={p: sha(GROOT / p) for p in (
                   'tools/hdc_golden.py', 'tools/hdc_program.py', 'tools/hdc_isa.py', 'tools/hdc_qwen_fullshape_isa_w12.py',
                   'tools/hdc_qwen_fullshape_program_w12.py', 'tools/qwen_rom_position_oracle_w12.py',
                   'tools/qwen_o4_layer0_oracle_w12.py')} | {'tools/qwen_layerbench/dv_layer_fixture.py': sha(__file__)},
               cut=dict(qkv_rows='0..511, 1024..1151, 1280..1407', gu_rows='0..3071', o_cols='0..511',
                        down_cols='0..1535'),
               tp_dependence='t (all-reduce return) is TP4-folded; x\'/r of both residuals, gu and act carry it; '
                             'the od partial sums are TP8-only (no TP4 value)',
               stages=stages)
    (out / f'{L}_fixture.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('FIXTURE', L, 'OK', json.dumps({k: v['sha256'][:12] for k, v in stages.items()}))


def run_tp8w(a):
    if PO.TP != 8 or PO.GROUPS != 3072:
        raise SystemExit('tp8w needs QWEN_O4_TP=8 QWEN_O4_GROUPS=3072')
    n, out = a.layer, Path(a.out)
    im = Img(a.img.format(layer=n, die=0), n, 8)
    res = {}
    for name, f, keys in (('qkv', 'mat_qkv', ('w', 's')), ('gu', 'mat_gu', ('w', 's')),
                          ('o', 'mat_od', ('o_w', 'o_s')), ('down', 'mat_od', ('down_w', 'down_s'))):
        z = np.load(out / f'L{n}_{f}.npz')
        w, sc = im.mat(name)
        okw = bool(np.array_equal(w.astype(np.int8), z[keys[0]]))
        oks = bool(np.array_equal(G.bits(sc), G.bits(z[keys[1]])))
        res[name] = dict(shape=list(w.shape), weights_equal=okw, scales_equal=oks)
    rec = dict(schema='opentallas.qwen.dv-layer-fixture-tp8w.v1', layer=n, tp8_die=0, image=a.img.format(layer=n, die=0),
               image_sha256=im.image_sha, result=res, verdict='PASS' if all(all(v[k] for k in ('weights_equal', 'scales_equal'))
                                                                          for v in res.values()) else 'FAIL')
    (out / f'L{n}_tp8w.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('TP8W', rec['verdict'], json.dumps(res))
    return 0 if rec['verdict'] == 'PASS' else 1


def run_tp8od(a):
    if PO.TP != 8 or PO.GROUPS != 3072:
        raise SystemExit('tp8od needs QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 HDC_SU_WIDTH=64 HDC_KV_FMT=fp8')
    n, out, gd = a.layer, Path(a.out), Path(a.tp8gold)
    pos = int(gd.name.lstrip('P'))
    orc = json.loads((gd.parent / 'oracle.json').read_text())
    if orc.get('tp') != 8 or str(pos) not in orc['per_position']:
        raise SystemExit(f'{gd.parent}/oracle.json: not a TP8 gold recording position {pos}')
    im = Img(a.img.format(layer=n, die=0), n, 8)
    if orc['layer_image_sha256'][f'L{n}'][0] != {k: v for k, v in im.image_sha.items() if k in
                                                   orc['layer_image_sha256'][f'L{n}'][0]}:
        raise SystemExit('TP8 image digests differ from the gold run')
    ar = [si for si, seg in enumerate(im.descriptors) if seg['kind'] == P.COLL_ALLREDUCE]
    if len(ar) != 2:
        raise SystemExit(f'expected 2 all-reduce segments (o, down), got {ar}')
    dd = gd / 'die0' / f'L{n}'
    vm_map, _ = FP.vm_map()
    cpc = orc['original_to_candidate_pc']['24']
    snap = np.load(dd / f'candidate_pc{cpc}_vm.npz')['vm_bits']
    act = G.from_bits(snap[vm_map['ACT']:vm_map['ACT'] + 1536].astype(np.uint32))
    attn = read_hex(dd / 'ATTN_fp32.hex')
    if len(attn) != 512:
        raise SystemExit(f'ATTN {len(attn)} != 512')
    gold = {nm: read_hex(dd / f'collective{si}_partial.hex') for nm, si in zip(('o', 'down'), ar)}
    wo, so = im.mat('o')
    wd, sd = im.mat('down')
    if wo.shape[1] != 512 or wd.shape[1] != 1536:
        raise SystemExit(f'TP8 die-0 o / down columns {wo.shape} / {wd.shape}')
    p = out / f'L{n}_mat_od_tp8.npz'
    np.savez_compressed(p, o_w=wo.astype(np.int8), o_s=so, o_x=attn, down_w=wd.astype(np.int8), down_s=sd, down_x=act,
                        o_gold_y=gold['o'], down_gold_y=gold['down'])
    # informative: hdc_golden G.matvec at split 256 (the DV ownership split) vs the gold partials (the bench decides)
    rep = {nm: int(np.sum(G.bits(G.matvec(w.astype(F), x, 256)) == G.bits(gold[nm])))
           for nm, w, x in (('o', wo, attn), ('down', wd, act))}
    rec = dict(schema='opentallas.qwen.dv-layer-fixture-tp8od.v1', layer=n, position=pos, tp8_die=0,
               gold=str(gd), oracle_collective_profile=orc['collective_profile'],
               allreduce_segments=dict(o=ar[0], down=ar[1]), act_snapshot=f'candidate_pc{cpc}_vm.npz (source PC24)',
               image_sha256=im.image_sha, inputs_sha256={f.name: sha(f) for f in (
                   dd / 'ATTN_fp32.hex', dd / f'candidate_pc{cpc}_vm.npz', dd / f'collective{ar[0]}_partial.hex',
                   dd / f'collective{ar[1]}_partial.hex', gd.parent / 'oracle.json')},
               hdc_matvec_split256_equal_rows=rep, file=p.name, sha256=sha(p),
               tool_sha256=sha(__file__))
    (out / f'L{n}_tp8od.json').write_text(json.dumps(rec, indent=1) + '\n')
    print('TP8OD', n, json.dumps(rep))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('what', choices=('tp4', 'tp8w', 'tp8od'))
    ap.add_argument('--img', required=True)
    ap.add_argument('--realmem')
    ap.add_argument('--tp8gold', help='tp8od: the TP8 gold position dir (qwen_tp8_layer_gold OUT/P<p>)')
    ap.add_argument('--layer', type=int, required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    return dict(tp4=run_tp4, tp8w=run_tp8w, tp8od=run_tp8od)[a.what](a)


if __name__ == '__main__':
    raise SystemExit(main())
