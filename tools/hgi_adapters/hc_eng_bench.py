#!/usr/bin/env python3
"""hgi-1010/b-hc (2026-10-10): vectors for the standalone ot_hgi_hc_eng bench (tb_hgi_hc_eng) on the real wide VM lanes.
DS-V4.1 d 5,120: HC_POST (y, res[4], post | comb) and HC_PRE_NORM (h[4], gain FP32 or packed BF16, pre) at several bank
phases, against hdc_golden_v41 (chunk8): Model.hc_post / Model.hc_pre + rmsnorm_bf16 (the fused_bench references).
--out DIR: hc_case.mem {job 149 (hex 38), init first 32, init count 32, exp first 32, exp count 32}; hc_init.mem and
hc_exp.mem {sector 16, data 256} (whole sectors; guard sectors around every output expect their preload pattern).
"""
import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import hdc_golden_v41 as GV  # noqa: E402
from hgi_sim import lib as LB  # noqa: E402


def f32w(x):
    return np.asarray(x, dtype=np.float32).view(np.uint32)


def sectors(words):
    """{word addr: value} -> {sector: 256-bit int} (missing words of a touched sector = 0)"""
    out = {}
    for a, v in words.items():
        out[a >> 3] = out.get(a >> 3, 0) | (int(v) << (32 * (a & 7)))
    return out


def job(op, eps, n, O, Cb, B, A, gpk=0, cq=0):
    return (op << 147) | (eps << 115) | (n << 94) | (O << 76) | (Cb << 58) | (cq << 37) | (gpk << 36) | (B << 18) | A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_hc_eng_tb')
    ap.add_argument('--d', type=int, default=5120)
    ap.add_argument('--ll', action='store_true', help='LL engine: A / B / O at one bank phase, FP32 gain')
    ap.add_argument('--b2', action='store_true',
                    help='B2 engine (ot_hgi_hc_eng_b2): element range [q D/4, (q+1) D/4) of every vector row in VM slice q at\n'
                         'the same LOCAL base (a row = D/4 words), scalars in the scalar-home slice; mem records carry the slice')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    D = a.d
    GV.set_arith("chunk8")
    rng = np.random.default_rng(1010)
    cases, init, exp = [], [], []
    DQ = D // 4

    def b2map(words, D_, rows_at, cq_at):
        """global golden layout {word: v} -> {(slice, local word): v}: rows_at = (global base, local base, rows) of the
        vector operands (row j, element i at global base + j D + i -> slice i // DQ, local base + j DQ + i % DQ);
        cq_at = (global base, local base, slice) of the scalars"""
        out = {}
        for a_, v in words.items():
            for gb_, lb_, nr in rows_at:
                if gb_ <= a_ < gb_ + nr * D_:
                    j, i = divmod(a_ - gb_, D_)
                    out[(i // DQ, lb_ + j * DQ + i % DQ)] = v
                    break
            else:
                gb_, lb_, q_ = cq_at
                assert gb_ <= a_ < gb_ + 32, a_
                out[(q_, lb_ + a_ - gb_)] = v
        return out

    def add_b2(jw, vin, vout):
        si, so = {}, {}
        for (q_, a_), v in vin.items():
            si[(q_, a_ >> 3)] = si.get((q_, a_ >> 3), 0) | (int(v) << (32 * (a_ & 7)))
        for (q_, a_), v in vout.items():
            so[(q_, a_ >> 3)] = so.get((q_, a_ >> 3), 0) | (int(v) << (32 * (a_ & 7)))
        for q_ in range(4):
            ks = [s_ for (qq, s_) in so if qq == q_]
            for g in (min(ks) - 1, max(ks) + 1):
                if (q_, g) not in si and (q_, g) not in so:
                    si[(q_, g)] = int.from_bytes(rng.bytes(32), 'little')
                    so[(q_, g)] = si[(q_, g)]
        cases.append((jw, len(init), len(si), len(exp), len(so)))
        init.extend(sorted(si.items()))
        exp.extend(sorted(so.items()))

    def add(jw, vin, vout):
        si, so = sectors(vin), sectors(vout)
        lo, hi = min(so), max(so)
        for g in (lo - 1, hi + 1):                    # guards: a pattern that must survive
            if g not in si and g not in so:
                si[g] = int.from_bytes(rng.bytes(32), 'little')
                so[g] = si[g]
        cases.append((jw, len(init), len(si), len(exp), len(so)))
        init.extend(sorted(si.items()))
        exp.extend(sorted(so.items()))

    # HC_POST: (y base, res base, C base, O base): bank phases y 0/7, res 0/13, C offset 0/3, O 10/12
    # LL (lane-local engine): every vector operand and the output at one bank phase (sector mod 32): 0 / 7
    post_cases = ((0, 8192, 40000, 49152), (56, 8192 + 56, 40003, 59960)) if (a.ll or a.b2) else \
        ((0, 8192, 40000, 50000), (56, 8192 + 8 * 13, 40003, 60000))
    for yb, rb, mb, ob in post_cases:
        yv = (rng.standard_normal(D) * 2).astype(np.float32)
        res = (rng.standard_normal((4, D)) * 2).astype(np.float32)
        post = (rng.random(4) * 2).astype(np.float32)
        comb = (rng.random((4, 4)) * 0.5).astype(np.float32)
        mix = [GV.seqsum([GV.mul(comb[j, k], res[j]) for j in range(4)]) for k in range(4)]
        hout = GV.to_bf16(np.stack([GV.add(GV.mul(post[k], yv), mix[k]) for k in range(4)]))
        vin = {yb + i: v for i, v in enumerate(f32w(yv))}
        vin.update({rb + i: v for i, v in enumerate(f32w(res.reshape(-1)))})
        vin.update({mb + i: v for i, v in enumerate(f32w(np.concatenate([post, comb.reshape(-1)])))})
        vo = {ob + i: v for i, v in enumerate(f32w(hout.reshape(-1)))}
        if a.b2:
            # golden bases are spread 2^20 apart so the map is unambiguous; local bases = the LL case bases
            G = 1 << 20
            cq = (0, 2)[len(cases) % 2]
            gin = {G + i: v for i, v in enumerate(f32w(yv))}
            gin.update({2 * G + i: v for i, v in enumerate(f32w(res.reshape(-1)))})
            gin.update({3 * G + i: v for i, v in enumerate(f32w(np.concatenate([post, comb.reshape(-1)])))})
            gout = {4 * G + i: v for i, v in enumerate(f32w(hout.reshape(-1)))}
            add_b2(job(1, 0, D, ob, mb, rb, yb, cq=cq), b2map(gin, D, ((G, yb, 1), (2 * G, rb, 4)), (3 * G, mb, cq)),
                   b2map(gout, D, ((4 * G, ob, 4),), (0, 0, 0)))
            continue
        add(job(1, 0, D, ob, mb, rb, yb), vin, vo)
    # HC_PRE_NORM: (h base, gain base, packed, C base, O base)
    pre_cases = ((0, 29696, 0, 20544, 39936), (168, 31144, 0, 25001, 44968)) if (a.ll or a.b2) else \
        ((0, 30000, 0, 20544, 40000), (168, 31000, 1, 25001, 45000))
    for hb, gb, gpk, cb, ob in pre_cases:
        h = (rng.standard_normal((4, D)) * 2).astype(np.float32)
        pre = (rng.random(4) * 1.5).astype(np.float32)
        w = LB.to_bf16((1 + 0.1 * rng.standard_normal(D)).astype(np.float32))
        eps = np.float32(1e-6)
        x = GV.to_bf16(GV.seqsum([GV.mul(pre[j], h[j]) for j in range(4)]))
        y = GV.rmsnorm_bf16(x, w, eps)
        vin = {hb + i: v for i, v in enumerate(f32w(h.reshape(-1)))}
        vin.update({cb + j: v for j, v in enumerate(f32w(pre))})
        wb = f32w(w)
        if a.b2:
            G = 1 << 20
            cq = (1, 3)[len(cases) % 2]
            gin = {G + i: v for i, v in enumerate(f32w(h.reshape(-1)))}
            gin.update({2 * G + i: v for i, v in enumerate(wb)})
            gin.update({3 * G + j: v for j, v in enumerate(f32w(pre))})
            gout = {4 * G + i: v for i, v in enumerate(f32w(y))}
            add_b2(job(0, int(eps.view(np.uint32)), D, ob, cb, gb, hb, 0, cq=cq),
                   b2map(gin, D, ((G, hb, 4), (2 * G, gb, 1)), (3 * G, cb, cq)), b2map(gout, D, ((4 * G, ob, 1),), (0, 0, 0)))
            continue
        if gpk:
            hw = (wb >> 16).astype(np.uint32)
            vin.update({gb + i: int(hw[2 * i]) | (int(hw[2 * i + 1]) << 16) for i in range(D // 2)})
        else:
            vin.update({gb + i: v for i, v in enumerate(wb)})
        add(job(0, int(eps.view(np.uint32)), D, ob, cb, gb, hb, gpk), vin, {ob + i: v for i, v in enumerate(f32w(y))})
    (out / 'hc_case.mem').write_text(''.join(f'{j:038X}{a:08X}{b:08X}{c:08X}{d:08X}\n' for j, a, b, c, d in cases))
    if a.b2:
        (out / 'hc_init.mem').write_text(''.join(f'{q:01X}{s:04X}{v:064X}\n' for (q, s), v in init))
        (out / 'hc_exp.mem').write_text(''.join(f'{q:01X}{s:04X}{v:064X}\n' for (q, s), v in exp))
    else:
        (out / 'hc_init.mem').write_text(''.join(f'{s:04X}{v:064X}\n' for s, v in init))
        (out / 'hc_exp.mem').write_text(''.join(f'{s:04X}{v:064X}\n' for s, v in exp))
    (out / 'hc_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NINIT = {len(init)};\n'
                                      f'localparam integer NEXP = {len(exp)};\nlocalparam integer HD = {D};\n')
    print(f"{len(cases)} cases, {len(init)} init sectors, {len(exp)} expected sectors")


if __name__ == '__main__':
    main()
