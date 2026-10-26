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


def rb(x, en):
    """ot_hgi_sm_pub rb(): to_bf16 (RNE) as a BF16-valued FP32 word"""
    if not en:
        return x
    if (x >> 23) & 0xFF == 0xFF and x & 0x7FFFFF:
        return ((x >> 16) | 0x40) << 16
    return (((x + 0x7FFF + ((x >> 16) & 1)) & 0xFFFFFFFF) >> 16) << 16


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


def program_records(layers):
    """tput-hbm-1011: the SM records of the priced DS-V4.1 1M rank-0 token program (g25_proof ds_rank0_program.json,
    the program tools/throughput_budget/build.py prices) on the given layers, each with its NativeCost S2 price
    (exactly the per-record price build.py sums into SM.MATVEC)."""
    sys.path.insert(0, str(C.ROOT / 'tools' / 'throughput_budget'))
    import build as BB
    from hgi_sim import ds_native_timing as DT
    d, recs = DT.load(BB.PROG)
    recs = BB.T.rebuild_waits(recs)
    rg = {}
    for x in json.loads(BB.RUN.read_text())["results"]:
        for s_ in x.get("row_gather") or []:
            rg[x["layer"]] = s_
    DT.apply_dyn_counts(recs, rg)
    cf = DT.NativeCost(d["ops"], recs, row_gather=rg)
    out = []

    def g(r, dyn, L):
        c = cf(r, dyn, L)
        lay = getattr(r, 'layer', None)
        if r.unit == 'SM' and r.op == 'MATVEC' and str(lay) in layers:
            b, o, a_ = r.desc['B'], r.desc['O'], r.desc['A']
            out.append(dict(tag=r.tag, layer=str(lay), fmt=b.fmt, M=b.m, K=b.n, P=r.desc['A'].m, cost=round(float(c[0]), 1),
                            cost_how=str(c[2]), src_stride=b.stride, indexed='I' in r.desc, o_bf16=(o.fmt == 'BF16'),
                            o_space=o.space,
                            akey=[str(lay)] + [str(getattr(a_, f, None)) for f in ('space', 'base', 'n', 'm', 'stride', 'fmt')]))
        return c
    BB.T.schedule(recs, DT.POS, "S2", cost_fn=g)
    return out, f"{BB.PROG.relative_to(C.ROOT)} (NativeCost S2 per record) layers {','.join(layers)}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('vehicle', choices=['qwen', 'ds'])
    ap.add_argument('--meta', help='ds: hgi-e2e export meta.json (exp_gf ds_L0)')
    ap.add_argument('--program', help='ds: comma-separated layers of the priced g25 program (e.g. 0,1,2,20,head)')
    ap.add_argument('--match', help='--program: keep only records whose tag matches this regex')
    ap.add_argument('--only', type=int, default=0, help='first N records only (smoke)')
    ap.add_argument('--no-xr', action='store_true', help='smmv 3a: never reuse x (every record loads its own x: the before)')
    ap.add_argument('--fuse', action='store_true',
                    help='el1013 smmv redesign, COMPILER SHAPE: an expert slot\'s w1 and w3 (same x, same format, same K, '
                         'adjacent records) become ONE record [w1; w3] of M1 + M2 rows, price = the two prices added '
                         '(never re-priced).  Why: the SM kernel interleaves IL = 8 (row, group) items; a one-row FP4 '
                         'K5120 op fills 3 of the 8 phases, so two one-row ops cost 2 x 70 issue cycles where the '
                         'stacked op (2 rows = 6 phases) costs 70.  The weight image must hold [w1_e; w3_e] contiguous '
                         'per expert (one indexed B descriptor); results are row-wise identical.')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    # tput2-sm (10-10 late): both vehicles take the records AND their S2 price from an hgi-e2e export meta when given
    # (qwen: exp_* qwen_L0, priced by the current qwen timing: SM-bound lines + drain)
    recs_in, src = (program_records(a.program.split(',')) if a.program else
                    ds_records(a.meta) if a.meta else qwen_records())
    if a.match:
        import re
        recs_in = [r for r in recs_in if re.search(a.match, r['tag'])]
    if a.fuse:
        fused, i = [], 0
        same = ('fmt', 'K', 'P', 'akey', 'o_bf16', 'indexed', 'src_stride', 'layer', 'o_space')
        while i < len(recs_in):
            r = recs_in[i]
            n = recs_in[i + 1] if i + 1 < len(recs_in) else None
            if (n and r['tag'].endswith(' w1') and n['tag'] == r['tag'][:-3] + ' w3'
                    and all(r.get(k) == n.get(k) for k in same)):
                f = dict(r)
                f.update(tag=r['tag'][:-3] + ' w1+w3', M=r['M'] + n['M'], cost=round(r['cost'] + n['cost'], 1),
                         cost_how=f"fused [w1; w3]: {r['cost']} ({r['cost_how']}) + {n['cost']} ({n['cost_how']})",
                         fused_from=[r['tag'], n['tag']], fused_M=[r['M'], n['M']])
                fused.append(f)
                i += 2
            else:
                fused.append(r)
                i += 1
        src += f"; --fuse: {len(recs_in) - len(fused)} w1/w3 pairs stacked (prices added)"
        recs_in = fused
    if a.only:
        recs_in = recs_in[:a.only]
    rng = np.random.default_rng(1010)
    recs, info, xws, vmi, vme, lines = [], [], [], {}, {}, {}
    line_cursor, abase, obase = 1000, 0, 200000
    # smmv 3a X REUSE = the compiler's x-slot allocation (hard to program is fine: the hardware only obeys XR / xb).
    # Records with the same A descriptor (same layer) share one x; the x store (XD 128 fragment addresses) is a ring of
    # slots, one per (A, format) load: base = previous end (wrap to 0 when it does not fit); a load invalidates every slot
    # it overlaps.  XR = 1 when (A, format) still sits in a valid slot: no x load, the SMs read that slot.
    XD, xcur, xslot, xslot_n, xshared, nxr = 128, 0, {}, {}, {}, 0
    for i, r in enumerate(recs_in):
        pf = FMT[r['fmt']]
        K, M, P = r['K'], r['M'], r['P']
        Q = -(-M // NSM)
        lb = 160 if pf == 3 else 136
        ak = tuple(r['akey']) if r.get('akey') and not a.no_xr else ('rec', i)
        if ak in xshared:
            X, a_rec = xshared[ak]
        else:
            X = [rng.standard_normal(K).astype(np.float32) * np.float32(rng.choice([0.1, 1.0, 4.0])) for _ in range(8)]
            a_rec = abase
            xshared[ak] = (X, a_rec)
            abase += P * (8 * (-(-K // 8))) + 64
        nxe = 8 * (-(-K // (512 if pf in (0, 3) else 1024 if pf == 1 else 2048)))     # fragment addresses (op_g x 8)
        assert nxe <= XD, (r['tag'], nxe)
        sk = (ak, pf)
        if sk in xslot:
            xr, xb = 1, xslot[sk]
            nxr += 1
        else:
            if xcur + nxe > XD:
                xcur = 0
            xr, xb = 0, xcur
            for k_ in [k_ for k_, b_ in xslot.items() if b_ < xcur + nxe and xcur < b_ + xslot_n[k_]]:
                del xslot[k_], xslot_n[k_]
            xslot[sk] = xcur
            xcur += nxe
        xslot_n[sk] = nxe
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
                vmi[a_rec + p * astride + k] = int(X[p][k].view(np.uint32))
        ostride = M
        for s in range(NSM):
            R = max(0, min(Q, M - s * Q))
            gb = blocks[s % NREAL]
            for p in range(P):
                for rr in range(R):
                    vme[obase + p * ostride + s * Q + rr] = rb(int(np.float32(gb['gold'][p][rr]).view(np.uint32)), r.get('o_bf16'))
        A = C.SV.mdesc(space=1, fmt=0, base=a_rec, n=K, m=P, stride=astride)
        B = C.SV.mdesc(space=0, fmt=BFMT[pf], base=line0 * lb, n=K, m=M, stride=lpr * lb)
        O = C.SV.mdesc(space=1, fmt=1 if r.get('o_bf16') else 0, base=obase, n=M, m=P, stride=ostride)
        h = C.SV.header(1, 0, opnd=0b10011, param=pf | (P - 1) << 2 | xr << 5 | xb << 6)
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
        r.update(XR=xr, XB=xb, Q=Q, LPR=lpr, LB=lb, line_image_stride=lpr * lb, rows_real=[R0, R1],
                 x_load='real' if pf in (0, 3) else 'proxy: real BF16 x-load of the same A + tb-written quantised fragments')
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
    print(f"{nxr} of {len(recs)} records reuse x (XR);", end=' ')
    print(f"{len(recs)} records, {len(lines)} weight lines, {len(secs)} x sectors, {len(vme)} result words, "
          f"{len(xws)} proxy x beats")


if __name__ == '__main__':
    main()
