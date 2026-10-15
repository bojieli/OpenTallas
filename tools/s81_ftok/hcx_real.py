#!/usr/bin/env python3
"""HC COEFFICIENT CHAIN on RTL with the 1M token's REAL data (S81 die item F12; s81-ftok r5, 2026-10-14).

The S81 layer vehicle (tb_s81_die_layer) runs <blk>.hc.fn / sumsq / rsqrt / pre_post / sinkhorn behaviourally (port 9,
golden coefficient rows).  The RTL that computes this chain exactly exists: ot_hgi_hc_unit (HBM generic HC.HC_MIX:
x staging -> the r25 HCP (2,048-lane class FP32 csum projection + ss / rsqrt scale) -> pre / post sigmoids on the r25
exp / divider -> row-max exp -> the r25 Sinkhorn -> drain), bit-exact to tools/hdc_golden_v41.py Model.hc_mixes
(chunk8).  This builds its bench vectors (tools/hgi_unit_tput/hc_vectors.py formats, tb_hgi_hc_tput) from the REAL
operands of every main-model layer: x = the hyper-connection residual the golden layer replay fed hc_mixes (snap_LNN.pkl
of tools/dsrom_1m_su.py golden, whose layer output equals the w17 shard), fn / scale / base = the released checkpoint's
layers.L.hc_{attn,ffn}_{fn,scale,base}; expected = the snapshot's own pre / post / comb (asserted == a fresh
Model.hc_mixes on the same operands).  One vector dir per layer, two legacy HC_MIX records (attn, ffn).

    python3 tools/s81_ftok/hcx_real.py --snaps DIR --out OUT [--layers 0,1,...]      (needs the checkpoint)
    tools/hgi_unit_tput/run_hc.sh-style build once (sizes are layer independent), run +DIR=OUT/Lnn for every layer;
    +define+MUT_POST (pre without + hc_eps) must FAIL.
"""
import argparse
import os
import pickle
import struct
import sys
from pathlib import Path

os.environ.setdefault("HDC_V41_ARITH", "chunk8")
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hgi_adapters'))
import hdc_golden_v41 as G  # noqa: E402
import common as C  # noqa: E402
import hc_bench as H  # noqa: E402
import rtl_hdc_v41x_hcp_campaign as HC  # noqa: E402
from hc_unit_bench import Stand, u32, W  # noqa: E402

F = np.float32
D = 5120
K = 4 * D


def weight_set(bsec, fn, scale, base):
    hbm = []
    nchunk = K // 8
    R = -(-nchunk // W)
    SPW = W // 8
    RS = R * SPW
    idx = np.arange(R * W)
    ok = idx < nchunk
    for row in range(24):
        for k in range(8):
            flat = np.zeros(R * W, F)
            flat[ok] = fn[row, 8 * idx[ok] + k]
            lanes = flat.reshape(R, W)
            for r in range(R):
                wv = u32(lanes[r])
                for s in range(SPW):
                    hbm.append((bsec + 4 + (8 * row + k) * RS + r * SPW + s,
                                sum(int(wv[8 * s + q]) << (32 * q) for q in range(8))))
    pv = np.zeros(32, F)
    pv[0:3] = scale
    pv[8:32] = base
    pw = u32(pv)
    for s in range(4):
        hbm.append((bsec + s, sum(int(pw[8 * s + q]) << (32 * q) for q in range(8))))
    return hbm, 4 + 24 * 8 * RS


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--snaps', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--layers', default=','.join(map(str, range(40))))
    a = ap.parse_args()
    G.set_arith('chunk8')
    import rtl_v41_fullshape_layer_campaign as LC
    ck = LC.Checkpoint()
    eps_bits = None
    for L in [int(x) for x in a.layers.split(',')]:
        s = pickle.loads((a.snaps / f'snap_L{L:02d}.pkl').read_bytes())
        out = a.out / f'L{L:02d}'
        out.mkdir(parents=True, exist_ok=True)
        eb = struct.unpack('<I', struct.pack('<f', float(s['eps'])))[0]
        assert eps_bits in (None, eb)
        eps_bits = eb
        assert float(s['hc_eps']) == float(F(1e-6)), s['hc_eps']           # the unit's HC_EPS parameter
        vmi, exp, cases, hbm, tags = [], [], [], [], []
        bsec = 0x300000
        for j, blk in enumerate(('attn', 'ffn')):
            c = s['hc'][f'hc.{blk}']
            fn = np.asarray(ck.get(f'layers.{L}.hc_{blk}_fn'), F)
            scale = np.asarray(ck.get(f'layers.{L}.hc_{blk}_scale'), F)
            base = np.asarray(ck.get(f'layers.{L}.hc_{blk}_base'), F)
            assert np.array_equal(u32(scale), u32(c['scale'])) and np.array_equal(u32(base), u32(c['base'])), (L, blk)
            x = np.asarray(c['x'], F).reshape(4, D)
            st = Stand(fn, scale, base)
            st.eps = F(s['eps'])
            pre, post, comb = G.Model.hc_mixes(st, x, L, blk)
            want = np.concatenate([np.asarray(c['pre'], F), np.asarray(c['post'], F), np.asarray(c['comb'], F).reshape(-1)])
            got = np.concatenate([np.asarray(pre, F), np.asarray(post, F), np.asarray(comb, F).reshape(-1)])
            assert np.array_equal(u32(want), u32(got)), (L, blk, 'fresh hc_mixes != the replay snapshot')
            ws, nsec = weight_set(bsec, fn, scale, base)
            hbm += ws
            v0 = len(vmi)
            ab, ob = 20480 * j, 200000 + 32 * j
            vmi.extend((ab + i, int(w)) for i, w in enumerate(u32(x)))
            d = H.rec(K, op=0, imm_a=0, n_o=24, A_base=ab, B_base=bsec << 5, O_base=ob)
            e0 = len(exp)
            ex = u32(want)
            exp.extend((ob + i, int(ex[i])) for i in range(24))
            cases.append((K, v0, len(vmi) - v0, 0, len(hbm), e0, 24, H.pack(d)))
            tags.append(f'L{L} {blk} HC_MIX')
            bsec += -(-nsec // 1024) * 1024
        (out / 'hu_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c[:7]) + C.hexw(c[7], 938) + '\n' for c in cases))
        (out / 'hu_vmi.mem').write_text(''.join(f'{a_:08X}{w:08X}\n' for a_, w in vmi))
        (out / 'hu_hbm.mem').write_text(''.join(f'{a_:010X}{d_:064X}\n' for a_, d_ in hbm))
        (out / 'hu_exp.mem').write_text(''.join(f'{a_:08X}{w:08X}\n' for a_, w in exp))
        (out / 'hu_cost.mem').write_text(''.join(f'{1160008:08X}\n' for _ in cases))
        (out / 'hu_tags.txt').write_text('\n'.join(tags) + '\n')
        (out / 'hu_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NVMI = {len(vmi)};\n'
                                          f'localparam integer NHBM = {len(hbm)};\nlocalparam integer NEXP = {len(exp)};\n'
                                          f"localparam [31:0] NEPS = 32'h{eps_bits:08X};\n")
        print(f'L{L:02d}: 2 records, {len(hbm)} HBM sectors, x/pre/post/comb from the replay, fresh hc_mixes equal',
              flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
