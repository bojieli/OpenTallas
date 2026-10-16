#!/usr/bin/env python3
"""hgi-1010/g (2026-10-10): SM.MATVEC THROUGHPUT bench vectors (rtl/hbm_accel/generic/adapters/tb/tb_hgi_sm_tput.sv).

Production die organisation: ot_hgi_sm_record NSM 32 -> ot_hgi_sm_xload (NXC 4) -> 32 SMs -> ot_hgi_sm_pub (NPC 4) -> the
REAL HGI VM.  SMs 0 and 1 are REAL ot_hbm_accel_smh at their production row slice Q = ceil(M / 32) and full K; SMs 2..31
are SHADOWS: SM s replays real SM (s mod 2)'s ports cycle for cycle (start_ready / d_ready / arrive / fault, and its
result rows r < R_s = clamp(M - s Q, 0, Q)), because the 32 SMs are identical, take the same op fields, the same x
(broadcast) and, under the per-SM HBM share, the same line stream rate.  The weight block of SM s IS block (s mod 2), so
every published O word has a golden; the adapter's 32-wide reductions, the per-SM fields and the publication's 32-SM
coalescing / flush serialisation are measured at full width.

Records back to back per vehicle, real shapes:
  qwen  Qwen3-8B P8191 TP4 layer program (hgi_sim.qwen_compiler): qkv / o / gu / down, INT8 fmt3, priced by
        hgi_sim.timing.cost (measured SM rate + first access + overhead + drain);
  ds    DS-V4.1 1M rank 0 L0 SM records (hgi-e2e export meta, NativeCost walk price per record), FP8 / FP4 / BF16.
B is the SM line image (D2: 136 B lines, INT8 160 B transport lines; B.stride = LPR x LB): the compiler exports carry
raw-row strides, which the adapter refuses (gap noted in the report, owner hbm-sim / D2).
FP8 / FP4 x: ot_hgi_sm_xload refuses fmt 1 / 2 (the activation quantiser is not in RTL), so for those records the bench
runs the real x-load in BF16 mode on the same A (identical VM reads, twice the beats) for TIMING and the tb writes the
quantised fragments (gen_op xw) into the SMs while it runs (x-load proxy, labelled).
Golden: tools/dshbm_matched_sm_seq.gen_op per real block (the smh benches' construction).

Files: tput_rec.mem {n_B, n_A, O, B, A, header} 938 b; tput_info.mem {fmt 4, Q 16, M 20, R0 16, R1 16, xw0 32,
nxw 16} per record; tput_xw.mem {addr 7, grp 7, beat 2048}; tput_vmi.mem {sector addr 32, 8 x 32 data}; tput_vme.mem
{addr 32, value 32}; tput_lines.mem {line 32, line 1088}.  meta.json: shapes, prices, sources.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
sys.path.insert(0, str(C.ROOT / 'tools'))
import dshbm_matched_sm_seq as MS  # noqa: E402

NSM, NREAL = 32, 2
FMT = {'INT8': 3, 'BF16': 0, 'FP8E4M3': 1, 'FP4E2M1': 2}
GEN = {3: 'v41_int8', 0: 'v41_bf16', 1: 'v41_fp8', 2: 'v41_fp4'}
BFMT = {0: 1, 1: 2, 2: 3, 3: 4}                         # adapter 'want': B.fmt code per param fmt


def qwen_records():
    from hgi_sim import qwen_compiler as QC, timing as T
    cfg = json.loads((C.ROOT / 'compiler/models/qwen3-8b/config.json').read_text())
    recs = QC.program(QC.Geometry(cfg, 8192), QC.qwen_params(cfg), 1)
    dyn = T.Dyn(8191)
    out = []
    for r in recs:
        if r.unit == 'SM' and r.desc['O'].space == 'VM':
            b = r.desc['B']
            c, g, how = T.cost(r, dyn, 0)
            out.append(dict(tag=r.tag, fmt=b.fmt, M=b.m, K=b.n, P=1, cost=round(c, 1), cost_grade=g, cost_how=how,
                            src_stride=b.stride))
    return out, 'hgi_sim.qwen_compiler.program(P8191, layer 0) + hgi_sim.timing.cost'


def ds_records(meta):
    d = json.loads(Path(meta).read_text())
    out = []
    for x in d['records']:
        if x['unit'] != 'SM':
            continue
        b = x['eff']['B']
        out.append(dict(tag=x['tag'], k=x['k'], fmt=b[6], M=b[2], K=b[1], P=1, cost=x['cost'], cost_how=x['cost_how'],
                        src_stride=b[3], indexed='I' in x['eff']))
    return out, f"hgi-e2e export meta {Path(meta).name} sha256 {hashlib.sha256(Path(meta).read_bytes()).hexdigest()}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vehicle', choices=['qwen', 'ds'])
    ap.add_argument('--meta', help='ds: hgi-e2e export meta.json (exp_gf ds_L0)')
    ap.add_argument('--only', type=int, default=0, help='first N records only (smoke)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # tput2-sm (10-10 late): both vehicles take the records AND their S2 price from an hgi-e2e export meta when given
    # (qwen: exp_* qwen_L0, priced by the current qwen timing: SM-bound lines + drain)
    recs_in, src = ds_records(a.meta) if a.meta else qwen_records()
    if a.only:
        recs_in = recs_in[:a.only]
    rng = np.random.default_rng(1010)
    recs, info, xws, vmi, vme, lines = [], [], [], {}, {}, {}
    line_cursor, abase, obase = 1000, 0, 200000
    for i, r in enumerate(recs_in):
        pf = FMT[r['fmt']]
        K, M, P = r['K'], r['M'], r['P']
        Q = -(-M // NSM)
        lb = 160 if pf == 3 else 136
        X = [rng.standard_normal(K).astype(np.float32) * np.float32(rng.choice([0.1, 1.0, 4.0])) for _ in range(8)]
        blocks = {}
        for s in range(NREAL):
            R = max(0, min(Q, M - s * Q))
            if R:
                blocks[s] = MS.gen_op(GEN[pf], R, K, 8, rng, X=X)
        g0 = blocks[0]
        lpr = len(g0['lines']) // min(Q, M)
        line0 = line_cursor
        line_cursor += NSM * Q * lpr + 7
        for s, g in blocks.items():
            for j, w in enumerate(g['lines']):
                lines[line0 + s * Q * lpr + j] = int(w)
        astride = 8 * (-(-K // 8))
        for p in range(P):
            for k in range(K):
                vmi[abase + p * astride + k] = int(X[p][k].view(np.uint32))
        ostride = M
        for s in range(NSM):
            R = max(0, min(Q, M - s * Q))
            gb = blocks[s % NREAL]
            for p in range(P):
                for rr in range(R):
                    vme[obase + p * ostride + s * Q + rr] = int(np.float32(gb['gold'][p][rr]).view(np.uint32))
        A = C.SV.mdesc(space=1, fmt=0, base=abase, n=K, m=P, stride=astride)
        B = C.SV.mdesc(space=0, fmt=BFMT[pf], base=line0 * lb, n=K, m=M, stride=lpr * lb)
        O = C.SV.mdesc(space=1, fmt=0, base=obase, n=M, m=P, stride=ostride)
        h = C.SV.header(1, 0, opnd=0b10011, param=pf | (P - 1) << 2)
        recs.append(h | A << 128 | B << 384 | O << 640 | K << 896 | K << 917)
        xw0 = len(xws)
        if pf in (1, 2):                                   # the quantised fragments the tb writes (x-load proxy)
            nb = -(-P * MS.XC // 2048)
            for ad, wd in enumerate(g0['xw']):
                for b in range(nb):
                    xws.append((ad, b, (wd >> (2048 * b)) & ((1 << 2048) - 1)))
        R0 = min(Q, M)
        R1 = max(0, min(Q, M - Q))
        info.append((pf, Q, M, R0, R1, xw0, len(xws) - xw0))
        r.update(Q=Q, LPR=lpr, LB=lb, line_image_stride=lpr * lb, rows_real=[R0, R1],
                 x_load='real' if pf in (0, 3) else 'proxy: real BF16 x-load of the same A + tb-written quantised fragments')
        abase += P * astride + 64
        obase += P * ostride + 64
        assert abase < 200000 and obase < 262000, (abase, obase)
    secs = {}
    for ad, v in vmi.items():
        secs.setdefault(ad >> 3, [0] * 8)[ad & 7] = v
    (out / 'tput_rec.mem').write_text(''.join(C.hexw(r, 938) + '\n' for r in recs))
    (out / 'tput_info.mem').write_text(''.join(f'{f:01X}{q:04X}{m:05X}{r0:04X}{r1:04X}{x0:08X}{nx:04X}\n'
                                               for f, q, m, r0, r1, x0, nx in info))
    (out / 'tput_xw.mem').write_text(''.join(f'{a_:02X}{b:02X}' + C.hexw(w, 2048) + '\n' for a_, b, w in xws) or '0\n')
    (out / 'tput_vmi.mem').write_text(''.join(f'{s:08X}' + ''.join(f'{v[7 - j]:08X}' for j in range(8)) + '\n'
                                              for s, v in sorted(secs.items())))
    (out / 'tput_vme.mem').write_text(''.join(f'{a_:08X}{x:08X}\n' for a_, x in sorted(vme.items())))
    (out / 'tput_lines.mem').write_text(''.join(f'{a_:08X}' + C.hexw(w, 1088) + '\n' for a_, w in sorted(lines.items())))
    (out / 'tput_sizes.svh').write_text(
        f'localparam integer NREC = {len(recs)};\nlocalparam integer NXW = {max(1, len(xws))};\n'
        f'localparam integer NVMI = {len(secs)};\nlocalparam integer NVME = {len(vme)};\n'
        f'localparam integer NLINE = {len(lines)};\nlocalparam integer LBASE = {min(lines)};\n'
        f'localparam integer LSPAN = {max(lines) - min(lines) + 1};\n')
    (out / 'meta.json').write_text(json.dumps(dict(vehicle=a.vehicle, source=src, records=recs_in), indent=1) + '\n')
    print(f"{len(recs)} records, {len(lines)} weight lines, {len(secs)} x sectors, {len(vme)} result words, "
          f"{len(xws)} proxy x beats")


if __name__ == '__main__':
    main()
