#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_sm_record (SM.MATVEC -> 32 per-SM command words).

--out DIR gets:
  sm_rec.mem   {n_B 21, n_A 21, O 256, B 256, A 256, header 128} a line (938 bits)
  sm_ref.mem   {kind 4, x {base 40, n 21, p 4, stride 32, space 2}, pub {base 40, stride 32, space 2, m 20, q 13, p 4},
                op_g 8, fmt 2, 32 x {rows 13, d_base 32, d_lines 24}} a line; kind 0 run, 2 refuse
  sm_case.mem  {kind, first, count} ; kind 0 run cases (stub SMs with random latencies), 2 negative (reset after)
The reference applies the adapter's SM layout rule (rtl/hbm_accel/generic/adapters/ot_hgi_sm_record.sv header):
Q = ceil(M / 32) contiguous rows a SM, d_base = (B.base + s Q B.stride) >> 5, op_g = ceil(K / 8W), d_lines = R_s 8 op_g.
Sources: hbm-sim conformance SM vectors (cf-idxd: indexed expert fetch), the Qwen3-8B token program's SM.MATVECs
(INT8, 145), DS-shaped MATVECs (FP8 / FP4 block-dot and BF16 at the DS per-die row counts) and random legal records.
"""
import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

NSM = 32
REF_BITS = 4 + 99 + 111 + 10 + NSM * 69
LW8 = {0: 9, 1: 10, 2: 11, 3: 9}
WANT = {0: 1, 1: 2, 2: 3, 3: 4}          # param fmt -> descriptor fmt (BF16, FP8E4M3, FP4E2M1, INT8)


def ref(d, mut_rows=False):
    h = d['hdr']
    A, B, O = d['eff'][0], d['eff'][1], d['eff'][4]
    opnd = C.fld(h, 'opnd', C.UOP)
    param = C.fld(h, 'param', C.UOP)
    pf, P = param & 3, ((param >> 2) & 7) + 1
    na, nb = d['n'][0], d['n'][1]
    M = C.fld(B, 'm')
    g = ((nb - 1) >> LW8[pf]) + 1 if nb else 0
    Q = (M >> 5) if mut_rows else (M + 31) >> 5
    bad = (C.fld(h, 'unit', C.UOP) != 1 or C.fld(h, 'op', C.UOP) != 0 or not (opnd & 1) or not (opnd & 2)
           or not (opnd & 16) or C.fld(B, 'space') != 0 or C.fld(A, 'space') not in (1, 2)
           or C.fld(O, 'space') not in (1, 2) or C.fld(B, 'fmt') != WANT[pf] or C.fld(B, 'ibcast')
           or C.fld(B, 'istride') > 1 or na != nb or nb == 0 or M == 0 or g > 255 or Q > 4095
           or (P > 1 and (C.fld(A, 'm') != P or C.fld(O, 'm') != P)) or (pf in (1, 2) and nb % 32))
    lb = 160 if pf == 3 else 136
    lpr = (4 if pf == 3 else 8) * g
    bad = bad or C.fld(B, 'stride') != lpr * lb or C.fld(B, 'base') % lb
    if bad:
        return 2 << (REF_BITS - 4)
    w = 0
    for s in reversed(range(NSM)):
        r = max(0, min(Q, M - s * Q))
        base = (C.fld(B, 'base') // lb + s * Q * lpr) & 0xFFFFFFFF if r else 0
        lines = r * lpr if r else 0
        w = w << 69 | r << 56 | base << 24 | lines
    w |= (g << 2 | pf) << (NSM * 69)
    pub = (C.fld(O, 'base') << 71 | C.fld(O, 'stride') << 39 | C.fld(O, 'space') << 37 | M << 17 | (Q & 0x1FFF) << 4 | P)
    x = C.fld(A, 'base') << 59 | na << 38 | P << 34 | C.fld(A, 'stride') << 2 | C.fld(A, 'space')
    w |= pub << (NSM * 69 + 10)
    w |= x << (NSM * 69 + 10 + 111)
    return w


def rec(unit=1, op=0, param=0, A=None, B=None, O=None, I=None, n_a=None, n_b=None):
    ds = dict(A=A, B=B, O=O, I=I)
    opnd = sum(1 << j for j, nm in enumerate(C.OPND) if ds.get(nm) is not None)
    h = C.SV.header(unit, op, opnd=opnd, param=param)
    eff = [ds.get(nm) or 0 for nm in C.OPND]
    return dict(hdr=h, sut=0, eff=eff, n=[n_a if n_a is not None else C.fld(eff[0], 'n'),
                                         n_b if n_b is not None else C.fld(eff[1], 'n'), 0, 0, 0, 0, 0])


def md(**kw):
    return C.SV.mdesc(**kw)


def matvec(pf, K, M, bbase, P=1, abase=0, obase=8192, space_a=1, stride=None, rng=None):
    g = ((K - 1) >> LW8[pf]) + 1
    lb = 160 if pf == 3 else 136
    st = stride if stride is not None else (4 if pf == 3 else 8) * g * lb
    bbase = bbase // lb * lb
    return rec(param=pf | (P - 1) << 2, A=md(space=space_a, fmt=0, base=abase, n=K, m=P, stride=K),
               B=md(space=0, fmt=WANT[pf], base=bbase, n=K, m=M, stride=st), O=md(space=1, fmt=0, base=obase, n=M, m=P,
                                                                                  stride=M))


def pack(d):
    return (d['hdr'] | d['eff'][0] << 128 | d['eff'][1] << 384 | d['eff'][4] << 640 | (d['n'][0] & 0x1FFFFF) << 896
            | (d['n'][1] & 0x1FFFFF) << 917)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_sm_tb')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs, refs, cases, man = [], [], [], []

    def add(kind, ident, ds):
        cases.append((kind, len(recs), len(ds)))
        for d in ds:
            recs.append(pack(d))
            refs.append(ref(d))
        man.append(dict(id=ident, kind=['run', '', 'negative'][kind], records=len(ds),
                        refused=sum(1 for d in ds if ref(d) >> (REF_BITS - 4) == 2)))
    # hbm-sim CF-IDXD images are raw rows (refused: not the line layout); their line-layout re-lay runs
    cf = [d for v, tr0, cpl, vm in C.conformance(lambda v: any(r['unit'] == 'SM' for r in v['records'])) for d in tr0
          if C.unit_of(d) == 1]
    tr, _ = C.qwen_dispatch()
    # the Qwen token's MATVECs with B re-laid in the SM line layout (hbm-sim images hold raw K-byte INT8 rows; the SM
    # reads 160-byte transport lines: stride = LPR x 160, base a multiple of 160) -- same shapes, slots and operands
    def relay(d):
        B = d['eff'][1]
        K, pf = d['n'][1], C.fld(d['hdr'], 'param', C.UOP) & 3
        g = ((K - 1) >> LW8[pf]) + 1
        lb = 160 if pf == 3 else 136
        st = (4 if pf == 3 else 8) * g * lb
        nb = md(space=0, fmt=C.fld(B, 'fmt'), base=C.fld(B, 'base') // lb * lb, n=C.fld(B, 'n'), m=C.fld(B, 'm'), stride=st)
        return dict(d, eff=[d['eff'][0], nb] + d['eff'][2:])
    add(0, 'qwen3_8b_token_sm_matvec_line_layout', [relay(d) for d in tr if C.unit_of(d) == 1])
    add(2, 'qwen3_8b_token_sm_raw_image_refused', [d for d in tr if C.unit_of(d) == 1][:1])
    add(0, 'cf_idxd_line_layout', [relay(d) for d in cf])
    ds = []
    for pf in (0, 1, 2):                    # DS: per-die rows of the 1/96 slices and the o-group K split
        for K, M in ((7168, 12), (7168, 40), (4096, 64), (2048, 7168 // 96 + 1), (1024, 1), (7168, 1536 // 96), (512, 33)):
            ds.append(matvec(pf, K, M, bbase=0x1_0000_0000 + 4096 * M))
    for P in (2, 5, 8):                     # G18 slots
        ds.append(matvec(3, 4096, 1536 // 4 * 4, bbase=0x2000_0000, P=P))
    ds.append(matvec(3, 4096, 37984, bbase=0x3000_0000))    # the Qwen head shard (Q = 1,187)
    ds.append(matvec(0, 128, 32 * 4095, bbase=0x4000_0000))  # Q = 4,095, the op_rows limit
    add(0, 'ds_shapes_and_slots', ds)
    rng = random.Random(9)
    rl = []
    for _ in range(48):
        pf = rng.randint(0, 3)
        K = rng.randrange(1, 8 * 255 * {0: 64, 1: 128, 2: 256, 3: 64}[pf])
        if pf in (1, 2):
            K = max(32, K // 32 * 32)
        M = rng.randrange(1, 4096)
        rl.append(matvec(pf, K, M, bbase=rng.randrange(1 << 35) << 5, P=rng.randint(1, 8), abase=rng.randrange(1 << 17),
                         space_a=rng.choice([1, 2])))
    add(0, 'random_legal_48', rl)
    g = matvec(0, 4096, 64, bbase=0x1000)
    neg = {'unit_not_sm': dict(g, hdr=g['hdr'] ^ (3 << 124)),
           'fmt_mismatch': dict(g, eff=[g['eff'][0], md(space=0, fmt=3, base=0, n=4096, m=64, stride=8 * 8 * 136)] + g['eff'][2:]),
           'b_in_vm': dict(g, eff=[g['eff'][0], md(space=1, fmt=1, base=0x1000, n=4096, m=64)] + g['eff'][2:]),
           'k_mismatch': dict(g, n=[4095, 4096, 0, 0, 0, 0, 0]),
           'b_unaligned': dict(matvec(0, 4096, 64, bbase=136 * 1000), eff=[matvec(0, 4096, 64, bbase=0)['eff'][0],
                               md(space=0, fmt=1, base=136 * 1000 + 8, n=4096, m=64, stride=8 * 8 * 136)] + [0, 0, matvec(0, 4096, 64, bbase=0)['eff'][4], 0, 0]),
           'stride_not_dense': dict(matvec(0, 4096, 64, bbase=0), eff=[matvec(0, 4096, 64, bbase=0)['eff'][0],
                               md(space=0, fmt=1, base=0, n=4096, m=64, stride=8192)] + [0, 0, matvec(0, 4096, 64, bbase=0)['eff'][4], 0, 0]),
           'fp8_k_not_32': matvec(1, 4010, 8, bbase=0),
           'op_g_256': matvec(0, 8 * 64 * 256, 64, bbase=0x1000),
           'q_4096': matvec(0, 128, 32 * 4096, bbase=0x1000),
           'p2_a_m1': rec(param=4, A=md(space=1, base=0, n=4096, m=1), B=md(space=0, fmt=1, base=0, n=4096, m=8, stride=8 * 8 * 136),
                          O=md(space=1, base=9000, n=8, m=2)),
           'no_o': rec(param=0, A=md(space=1, base=0, n=4096, m=1), B=md(space=0, fmt=1, base=0, n=4096, m=8, stride=8 * 8 * 136)),
           'm_zero': matvec(0, 4096, 0, bbase=0x1000)}
    for k, d in neg.items():
        add(2, k, [d])
    (out / 'sm_rec.mem').write_text(''.join(C.hexw(r, 938) + '\n' for r in recs))
    (out / 'sm_ref.mem').write_text(''.join(C.hexw(r, REF_BITS) + '\n' for r in refs))
    (out / 'sm_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'sm_sizes.svh').write_text(f'localparam integer NREC = {len(recs)};\nlocalparam integer NCASE = {len(cases)};\n'
                                      f'localparam integer REFB = {REF_BITS};\n')
    (out / 'sm_bench.json').write_text(json.dumps(dict(schema='opentallas.hgi_adapters.sm_bench.v1', cases=man), indent=1))
    print(f"{len(cases)} cases, {len(recs)} records: " + ', '.join(f"{m['id']} {m['records']} (refused {m['refused']})" for m in man))


if __name__ == '__main__':
    main()
