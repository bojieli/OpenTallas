#!/usr/bin/env python3
"""HC unit THROUGHPUT vectors (hgi-1010/g): back-to-back HC records with the real DS-V4.1 1M per-die shapes
(G22 lowering, compiler 6dd28b4a7: HC_MIX_ROWS = one 20,480-K mix row of h [4 x 5,120], HC_MIX_POST = sigmoid +
Sinkhorn on the 24 gathered mixes; plus one legacy full HC_MIX), golden = tools/hdc_golden_v41.py Model.hc_mixes
(R-ARITH chunk8), priced by hgi_sim.ds_native_timing.NativeCost as of 6dd28b4a7:
  HC_MIX_POST  calibration HC.HC_MIX_POST = 540
  HC_MIX_ROWS  walk(hc_mixes) / 24 = 1,160.008 / 24  (walk: HCP 328 cyc at spec W256 + SU pre/post 0.166 us + Sinkhorn 0.528 us)
  HC_MIX       walk(hc_mixes) = 1,160.008
Same file formats as tools/hgi_adapters/hc_unit_bench.py (hu_case / hu_vmi / hu_hbm / hu_exp / hu_sizes) plus
hu_cost.mem (one price a record, x1000, hex).  Every record's operands are preloaded; the bench runs them back to back.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools/hgi_adapters'))
import hdc_golden_v41 as G  # noqa: E402
import common as C  # noqa: E402
import hc_bench as H  # noqa: E402
import rtl_hdc_v41x_hcp_campaign as HC  # noqa: E402
from hc_unit_bench import Stand, u32, W, EPS  # noqa: E402

F = np.float32
WALK = 1160.008
PRICE = {0: WALK, 1: WALK / 24, 2: 540.0}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--nx', type=int, default=4)
    out = Path(ap.parse_args().out)
    nx = ap.parse_args().nx
    out.mkdir(parents=True, exist_ok=True)
    G.set_arith('chunk8')
    rng = np.random.default_rng(20261010)
    D = 5120
    K = 4 * D
    bsec = 0x300000
    fn = rng.normal(0, .03, (24, K)).astype(F)
    scale = rng.uniform(.5, 2, 3).astype(F)
    base = rng.normal(0, .5, 24).astype(F)
    xs, mixes, outs = [], [], []
    for j in range(nx):
        x = G.to_bf16(rng.normal(0, 1, (4, D)).astype(F))
        with HC.recording() as rc:
            pre, post, comb = G.Model.hc_mixes(Stand(fn, scale, base), x, 0, 'attn')
        xs.append(x)
        mixes.append(np.asarray(G.mul(rc['raw'], rc['r']), F))
        outs.append(np.concatenate([np.asarray(pre, F), np.asarray(post, F), np.asarray(comb, F).reshape(-1)]))
    # HBM weight set (ot_hgi_hc_unit format)
    hbm = []
    nchunk = K // 8
    R = -(-nchunk // W)
    SPW = W // 8
    RS = R * SPW
    for row in range(24):
        for k in range(8):
            lanes_all = np.zeros((R, W), F)
            idx = np.arange(R * W)
            ok = idx < nchunk
            flat = np.zeros(R * W, F)
            flat[ok] = fn[row, 8 * idx[ok] + k]
            lanes_all = flat.reshape(R, W)
            for r in range(R):
                wv = u32(lanes_all[r])
                for s in range(SPW):
                    sec = bsec + 4 + (8 * row + k) * RS + r * SPW + s
                    hbm.append((sec, sum(int(wv[8 * s + q]) << (32 * q) for q in range(8))))
    pv = np.zeros(32, F)
    pv[0:3] = scale
    pv[8:32] = base
    pw = u32(pv)
    for s in range(4):
        hbm.append((bsec + s, sum(int(pw[8 * s + q]) << (32 * q) for q in range(8))))
    vmi, exp, cases, costs, tags = [], [], [], [], []
    rows = [0, 7, 15, 23, 3, 11, 19, 21][:nx]
    seq = []
    for j in range(nx):
        seq += [(1, j), (2, j)]
    seq.append((0, 0))
    for op, j in seq:
        v0 = len(vmi)
        if op == 2:
            ab, ob = 145088 + 32 * j, 41024 + 64 * j
            vmi.extend((ab + i, int(u32(mixes[j])[i])) for i in range(24))
            d = H.rec(24, op=2, A_base=ab, B_base=bsec << 5, O_base=ob)
            ex = u32(outs[j])
            tags.append(f'HC_MIX_POST x{j}')
        else:
            ab = 20480 * j if op == 1 else 20480 * nx
            ob = 200000 + 32 * len(cases)
            vmi.extend((ab + i, int(w)) for i, w in enumerate(u32(xs[j])))
            r0, nr = (rows[j], 1) if op == 1 else (0, 24)
            d = H.rec(K, op=op, imm_a=r0, n_o=nr, A_base=ab, B_base=bsec << 5, O_base=ob)
            ex = u32(outs[j]) if op == 0 else u32(mixes[j])[r0:r0 + nr]
            tags.append(f'HC_MIX_ROWS x{j} row {r0}' if op == 1 else f'HC_MIX x{j}')
        e0 = len(exp)
        exp.extend((ob + i, int(ex[i])) for i in range(len(ex)))
        cases.append((K if op != 2 else 24, v0, len(vmi) - v0, 0, len(hbm), e0, len(ex), H.pack(d)))
        costs.append(PRICE[op])
    (out / 'hu_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c[:7]) + C.hexw(c[7], 938) + '\n' for c in cases))
    (out / 'hu_vmi.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in vmi))
    (out / 'hu_hbm.mem').write_text(''.join(f'{a:010X}{d:064X}\n' for a, d in hbm))
    (out / 'hu_exp.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in exp))
    (out / 'hu_cost.mem').write_text(''.join(f'{int(round(c * 1000)):08X}\n' for c in costs))
    (out / 'hu_tags.txt').write_text('\n'.join(tags) + '\n')
    (out / 'hu_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NVMI = {len(vmi)};\n'
                                      f'localparam integer NHBM = {len(hbm)};\nlocalparam integer NEXP = {len(exp)};\n'
                                      f"localparam [31:0] NEPS = 32'h{struct.unpack('<I', struct.pack('<f', EPS))[0]:08X};\n")
    print(f'{len(cases)} records, {len(hbm)} HBM sectors, {len(vmi)} VM words')


if __name__ == '__main__':
    main()
