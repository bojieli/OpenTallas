#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_hc_record (HC.HC_MIX -> the HC unit's HCP job).
--out DIR: hc_rec.mem {n_O 21, n_A 21, O 256, B 256, A 256, header 128} (938 b); hc_ref.mem {kind 2, job 229}; hc_case.mem.
Reference from the spec / hgi_sim ds_native (HC_MIX A = h VM, B = HC weight set HBM, O = 24-word mix VM) and
ot_hdc_v41x_hcp's command contract (nchunk = K / 8, nf = binary32 K, scale 1), independent of the RTL.
"""
import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402

EPS = 0x3727C5AC          # the cfg_hc_eps strap the bench drives (binary32 1e-5)


def ref(d):
    h = d['hdr']
    A, B, O = d['eff'][0], d['eff'][1], d['eff'][4]
    opnd = C.fld(h, 'opnd', C.UOP)
    K, no = d['n'][0], d['n'][4]
    if (C.fld(h, 'unit', C.UOP) != 10 or C.fld(h, 'op', C.UOP) != 0 or (opnd & 0b10011) != 0b10011
            or C.fld(A, 'space') != 1 or C.fld(O, 'space') != 1 or C.fld(B, 'space') != 0 or K == 0 or K % 8
            or K >= 1 << 18 or no != 24 or C.fld(B, 'base') & 31):
        return 2 << 229
    nf = struct.unpack('<I', struct.pack('<f', float(K)))[0]
    f = [(1, 1), (24, 5), (K // 8, 18), (1, 1), (nf, 32), (EPS, 32), (0, 16), (C.fld(A, 'base'), 18),
         (C.fld(B, 'base') >> 5, 35), (24 * K // 8, 24), (C.fld(O, 'base'), 18)]
    w, sh = 0, 0
    for v, b in f:
        w |= (v & ((1 << b) - 1)) << sh
        sh += b
    return w


def rec(K, A_base=0, B_base=0x5_0000_0000, O_base=200000, n_o=24, unit=10, op=0, sa=1, sb=0, so=1, opnd=0b10011):
    A = C.SV.mdesc(space=sa, base=A_base, n=K, m=1)
    B = C.SV.mdesc(space=sb, fmt=1, base=B_base, n=1)
    O = C.SV.mdesc(space=so, base=O_base, n=n_o)
    eff = [A, B, 0, 0, O, 0, 0]
    return dict(hdr=C.SV.header(unit, op, opnd=opnd), eff=[e if opnd >> j & 1 else 0 for j, e in enumerate(eff)],
                n=[K, 0, 0, 0, n_o, 0, 0])


def pack(d):
    return (d['hdr'] | d['eff'][0] << 128 | d['eff'][1] << 384 | d['eff'][4] << 640 | (d['n'][0] & 0x1FFFFF) << 896
            | (d['n'][4] & 0x1FFFFF) << 917)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_hc_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    recs, refs, cases = [], [], []

    def add(kind, ds):
        cases.append((kind, len(recs), len(ds)))
        for d in ds:
            recs.append(pack(d))
            refs.append(ref(d))
    # DS V4.1-Flash: HC = 4 copies x D 4,096 (h = 16,384 FP32 words), the attn / ffn mixes of every layer
    add(0, [rec(4 * 4096, A_base=0, B_base=0x5_0000_0000 + 0x40000 * L, O_base=100000 + 24 * (L % 2)) for L in range(8)]
        + [rec(8), rec(4 * 7168, A_base=4096), rec((1 << 18) - 8)])
    for d in [rec(4096, unit=2), rec(4096, op=1), rec(4096, sa=0), rec(4096, sb=1), rec(4096, so=0), rec(4100),
              rec(0), rec(4096, n_o=20), rec(4096, B_base=0x5_0000_0010), rec(4096, opnd=0b10001), rec(1 << 18)]:
        add(2, [d])
    (out / 'hc_rec.mem').write_text(''.join(C.hexw(r, 938) + '\n' for r in recs))
    (out / 'hc_ref.mem').write_text(''.join(C.hexw(r, 231) + '\n' for r in refs))
    (out / 'hc_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'hc_sizes.svh').write_text(f'localparam integer NREC = {len(recs)};\nlocalparam integer NCASE = {len(cases)};\n'
                                      f'localparam [31:0] EPS = 32\'h{EPS:08X};\n')
    print(f"{len(cases)} cases, {len(recs)} records")


if __name__ == '__main__':
    main()
