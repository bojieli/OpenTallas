#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): END-TO-END SM.MATVEC bench vectors: record -> ot_hgi_sm_record (NSM 2) -> ot_hgi_sm_xload
-> 2 REAL ot_hbm_accel_smh (INT8 front) -> ot_hgi_sm_pub -> the REAL HGI VM; VM O == golden.
--out DIR: e2e_case.mem {first rec, recs, first vmi, vmi, first vme, vme} (6 x 32 b); e2e_rec.mem {n_B, n_A, O, B, A,
header} (938 b); e2e_vmi / e2e_vme {addr 32, value 32}; e2e_lines.mem {line index 32, line 1,088} (the weight lines, every
SM block written at d_base_s = B.base / LB + s Q LPR in the element's issue order).
Weights, x and golden: tools/dshbm_matched_sm_seq.gen_op (the smh benches' construction: INT8 fmt3 = csum8(bf16(x) x
code); BF16 fmt0 = csum8(bf16(x) x w)) per SM row block, with the same X for every block.
"""
import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
sys.path.insert(0, str(C.ROOT / 'tools'))
import dshbm_matched_sm_seq as MS  # noqa: E402

NSM = 2
DS = False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_sme2e_tb')
    ap.add_argument('--ds', action='store_true', help='add the DS block-dot (FP8 / FP4) cases')
    a_ = ap.parse_args()
    out = Path(a_.out)
    global DS
    DS = a_.ds
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(31)
    cases, recs, vmi, vme, lines = [], [], [], [], {}
    line_cursor = 1000
    # (fmt, K, M, P, O BF16): fmt 3 INT8 / 0 BF16 (Qwen class), 1 FP8 / 2 FP4 block-dot (DS: x quantised by the
    # x-load, hgi-1010/d), O BF16 = the DS records' output format (the publication rounds; hgi_sim: to_bf16(csum))
    shapes = [(3, 512, 7, 1, 0), (3, 1024, 16, 3, 0), (3, 4096, 3, 1, 0), (3, 512, 1, 2, 0), (0, 600, 5, 2, 0),
              (0, 2048, 2, 8, 0), (0, 512, 9, 1, 0)]
    if DS:
        shapes += [(1, 1024, 7, 1, 1), (1, 4096, 5, 2, 1), (2, 2048, 6, 1, 1), (2, 4096, 3, 3, 0), (1, 7168, 4, 1, 1),
                   (2, 1024, 2, 8, 1), (1, 96, 3, 1, 0)]
    for pf, K, M, P, obf in shapes:
        Gn = -(-K // {0: 512, 3: 512, 1: 1024, 2: 2048}[pf])
        lpr = (4 if pf == 3 else 8) * Gn
        lb = 160 if pf == 3 else 136
        Q = -(-M // NSM)
        X = [rng.standard_normal(K).astype(np.float32) * np.float32(rng.choice([0.1, 1.0, 4.0])) for _ in range(8)]
        abase, astride = 8 * rng.integers(0, 1000), 8 * (-(-K // 8) + rng.integers(0, 4))
        obase, ostride = 100000 + rng.integers(0, 1000), M + rng.integers(0, 50)
        line0 = line_cursor
        line_cursor += NSM * Q * lpr + 7
        vin, vexp = {}, {}
        for p in range(P):
            for k in range(K):
                vin[int(abase + p * astride + k)] = int(X[p][k].view(np.uint32))
        for s in range(NSM):
            R = max(0, min(Q, M - s * Q))
            if not R:
                continue
            g = MS.gen_op({3: 'v41_int8', 0: 'v41_bf16', 1: 'v41_fp8', 2: 'v41_fp4'}[pf], R, K, 8, rng, X=X)
            assert len(g['lines']) == R * lpr, (len(g['lines']), R, lpr)
            for i, w in enumerate(g['lines']):
                lines[line0 + s * Q * lpr + i] = int(w)
            for p in range(P):
                for r in range(R):
                    v = int(np.float32(g['gold'][p][r]).view(np.uint32))
                    if obf:                                   # to_bf16 RNE (finite)
                        v = ((v + 0x7FFF + ((v >> 16) & 1)) >> 16) << 16 & 0xFFFFFFFF
                    vexp[int(obase + p * ostride + s * Q + r)] = v
        A = C.SV.mdesc(space=1, fmt=0, base=int(abase), n=K, m=P, stride=int(astride))
        B = C.SV.mdesc(space=0, fmt={3: 4, 0: 1, 1: 2, 2: 3}[pf], base=line0 * lb, n=K, m=M, stride=lpr * lb)
        O = C.SV.mdesc(space=1, fmt=1 if obf else 0, base=int(obase), n=M, m=P, stride=int(ostride))
        h = C.SV.header(1, 0, opnd=0b10011, param=pf | (P - 1) << 2)
        cases.append((len(recs), 1, len(vmi), len(vin), len(vme), len(vexp)))
        recs.append(h | A << 128 | B << 384 | O << 640 | K << 896 | K << 917)
        vmi.extend(sorted(vin.items()))
        vme.extend(sorted(vexp.items()))
    (out / 'e2e_rec.mem').write_text(''.join(C.hexw(r, 938) + '\n' for r in recs))
    (out / 'e2e_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'e2e_vmi.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vmi))
    (out / 'e2e_vme.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vme))
    (out / 'e2e_lines.mem').write_text(''.join(f'{a:08X}' + C.hexw(w, 1088) + '\n' for a, w in sorted(lines.items())))
    (out / 'e2e_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NREC = {len(recs)};\n'
                                       f'localparam integer NVMI = {len(vmi)};\nlocalparam integer NVME = {len(vme)};\n'
                                       f'localparam integer NLINE = {len(lines)};\n'
                                       f'localparam integer LBASE = {min(lines)};\nlocalparam integer LSPAN = {max(lines) - min(lines) + 1};\n')
    print(f"{len(cases)} cases, {len(lines)} weight lines, {len(vmi)} x words, {len(vme)} result words")


if __name__ == '__main__':
    main()
