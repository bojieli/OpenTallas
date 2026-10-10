#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): data vectors for the D1 HC unit ot_hgi_hc_unit (HC.HC_MIX end to end).
Golden: tools/hdc_golden_v41.py Model.hc_mixes itself (R-ARITH chunk8, the HCP's contract) on random fn [24, K] FP32,
x [4, D] BF16, scale [3], base [24], norm eps 1e-6, hc_eps 1e-6, 20 Sinkhorn iterations -> [pre 4 | post 4 | comb 16].
HBM image in the HC unit's weight-set format (see ot_hgi_hc_unit.sv); VM: A = x (FP32 words), O = 24 words.
--out DIR: hu_case.mem {K 32, first vmi 32, n vmi 32, first hbm 32, n hbm 32, first exp 32, rec 938};
hu_vmi.mem {addr 32, word 32}; hu_hbm.mem {sector 40, data 256}; hu_exp.mem {addr 32, word 32}.
"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hdc_golden_v41 as G  # noqa: E402
import common as C  # noqa: E402
import hc_bench as H  # noqa: E402
import rtl_hdc_v41x_hcp_campaign as HC  # noqa: E402

F = np.float32
W = 32
EPS = 1e-6


class Stand:
    def __init__(self, fn, scale, base):
        self.hc, self.eps, self.hc_eps, self.sinkhorn_iters = 4, F(EPS), F(1e-6), 20
        self._w = {'fn': fn, 'scale': scale, 'base': base}

    def lw(self, L, name):
        return self._w[name.rsplit('_', 1)[1]]


def u32(a):
    return np.asarray(a, dtype=F).reshape(-1).view(np.uint32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_hcu_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    G.set_arith('chunk8')
    rng = np.random.default_rng(1009)
    cases, vmi, hbm, exp = [], [], [], []
    for D, abase, obase, bsec, ops in ((64, 0, 5000, 0x100000, ((0, 0, 24), (1, 0, 1), (1, 23, 1), (1, 5, 7), (2, 0, 24))),
                                       (200, 13, 9001, 0x200000, ((0, 0, 24), (1, 3, 1), (1, 0, 24), (2, 0, 24))),
                                       (5120, 40, 60003, 0x300000, ((0, 0, 24), (1, 7, 1), (2, 0, 24)))):
        K = 4 * D
        fn = rng.normal(0, .03, (24, K)).astype(F)
        x = G.to_bf16(rng.normal(0, 1, (4, D)).astype(F))
        scale = rng.uniform(.5, 2, 3).astype(F)
        base = rng.normal(0, .5, 24).astype(F)
        with HC.recording() as rc:
            pre, post, comb = G.Model.hc_mixes(Stand(fn, scale, base), x, 0, 'attn')
        mixes = np.asarray(G.mul(rc['raw'], rc['r']), F)
        o = np.concatenate([np.asarray(pre, F), np.asarray(post, F), np.asarray(comb, F).reshape(-1)])
        nchunk = K // 8
        R = -(-nchunk // W)
        SPW = W // 8
        RS = R * SPW
        h0 = len(hbm)
        for row in range(24):
            for k in range(8):
                for r in range(R):
                    lanes = np.zeros(W, F)
                    for l in range(W):
                        c = r * W + l
                        if c < nchunk:
                            lanes[l] = fn[row, 8 * c + k]
                    wv = u32(lanes)
                    for s in range(SPW):
                        sec = bsec + 4 + (8 * row + k) * RS + r * SPW + s
                        hbm.append((sec, sum(int(wv[8 * s + q]) << (32 * q) for q in range(8))))
        pv = np.zeros(32, F)
        pv[0:3] = scale
        pv[8:32] = base
        pw = u32(pv)
        for s in range(4):
            hbm.append((bsec + s, sum(int(pw[8 * s + q]) << (32 * q) for q in range(8))))
        nh = len(hbm) - h0
        for op, r0, nr in ops:
            v0 = len(vmi)
            if op == 2:
                vmi.extend((abase + i, int(u32(mixes)[i])) for i in range(24))
                d = H.rec(24, op=2, A_base=abase, B_base=bsec << 5, O_base=obase)
                ex = u32(o)
            else:
                xf = u32(x)
                vmi.extend((abase + i, int(xf[i])) for i in range(K))
                d = H.rec(K, op=op, imm_a=r0, n_o=nr, A_base=abase, B_base=bsec << 5, O_base=obase)
                ex = u32(o) if op == 0 else u32(mixes)[r0:r0 + nr]
            e0 = len(exp)
            exp.extend((obase + i, int(ex[i])) for i in range(len(ex)))
            cases.append((K if op != 2 else 24, v0, len(vmi) - v0, h0, nh, e0, len(ex), H.pack(d)))
    (out / 'hu_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c[:7]) + C.hexw(c[7], 938) + '\n' for c in cases))
    (out / 'hu_vmi.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in vmi))
    (out / 'hu_hbm.mem').write_text(''.join(f'{a:010X}{d:064X}\n' for a, d in hbm))
    (out / 'hu_exp.mem').write_text(''.join(f'{a:08X}{w:08X}\n' for a, w in exp))
    (out / 'hu_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NVMI = {len(vmi)};\n'
                                      f'localparam integer NHBM = {len(hbm)};\nlocalparam integer NEXP = {len(exp)};\n'
                                      f"localparam [31:0] NEPS = 32'h{struct.unpack('<I', struct.pack('<f', EPS))[0]:08X};\n")
    print(f'{len(cases)} cases, {len(hbm)} HBM sectors, {len(vmi)} VM words')


if __name__ == '__main__':
    main()
