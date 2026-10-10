#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_att_issue (ATT.QK / ATT.PV -> the attention controller job).
--out DIR: att_rec.mem {pos1 21, O, C, B, A (4 x 256), header 128} (1,173 b); att_ref.mem {kind 2, job 161}; att_case.mem.
Reference: spec 6.6 / 6.7 (ATT param [3:0] lanes, 0 encodes 16; [7:4] slices - 1; [8] ring) and hgi_sim u_att_qk /
u_att_pv (QK hd = A.n, PV hd = O.n and P = A.n = the row count), written independently of the RTL.
Sources: all 24 hbm-sim CF-ATT conformance vectors (43 dispatches), the Qwen3-8B token program's ATT records (144).
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def ref(d):
    h = d['hdr']
    A, B, Cd, O = d['eff'][0], d['eff'][1], d['eff'][2], d['eff'][4]
    op, opnd, p = C.fld(h, 'op', C.UOP), C.fld(h, 'opnd', C.UOP), C.fld(h, 'param', C.UOP)
    cp = bool(opnd & 4)
    lanes = (p & 15) or 16
    slices = ((p >> 4) & 15) + 1
    hd = C.fld(O, 'n') if op == 1 else C.fld(A, 'n')
    nrows = C.fld(B, 'n') + (C.fld(Cd, 'n') if cp else 0)
    bf = C.fld(B, 'fmt')
    bad = (op > 1 or C.fld(A, 'space') != 1 or C.fld(O, 'space') != 1 or hd != 64 * slices or hd > 512
           or (op == 1 and C.fld(A, 'n') != nrows) or bf > 3 or (cp and C.fld(Cd, 'fmt') > 3))
    if bad:
        return 2 << 161
    f = [(op, 1), (lanes, 5), (slices & 15, 4), ((p >> 8) & 1, 1), (hd, 10), (nrows, 21), (bf, 3), (C.fld(A, 'base'), 18),
         (C.fld(A, 'stride'), 32), (C.fld(O, 'base'), 18), (C.fld(O, 'stride'), 32), (d['pos1'], 13), (C.fld(Cd, 'fmt') if cp else 0, 3)]
    w, sh = 0, 0
    for v, b in f:
        w |= (v & ((1 << b) - 1)) << sh
        sh += b
    return w


def pack(d):
    w = d['hdr'] | d['eff'][0] << 128 | d['eff'][1] << 384 | d['eff'][2] << 640 | d['eff'][4] << 896
    return w | (d['pos1'] & 0x1FFFFF) << 1152


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_att_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    recs, refs, cases, ids = [], [], [], []

    def add(kind, ident, ds):
        cases.append((kind, len(recs), len(ds)))
        ids.append((ident, len(ds), sum(1 for d in ds if ref(d) >> 161 == 2)))
        for d in ds:
            recs.append(pack(d))
            refs.append(ref(d))
    for v, tr, cpl, vm in C.conformance(lambda v: any(r['unit'] == 'ATT' for r in v['records'])):
        add(0, v['id'], [d for d in tr if C.unit_of(d) == 5])
    tr, _ = C.qwen_dispatch()
    add(0, 'qwen3_8b_token_att', [d for d in tr if C.unit_of(d) == 5])
    g = [d for d in tr if C.unit_of(d) == 5][0]
    # DS 16-head lanes (param [3:0] = 0 encodes 16, HGI-1.1) on every CF-ATT DS ring record
    ds16 = []
    for v, tr2, cpl, vm in C.conformance(lambda v: v['id'].startswith('att_ring')):
        for d in tr2:
            if C.unit_of(d) == 5:
                h = d['hdr']
                ds16.append(dict(d, hdr=C.SV.header(5, C.fld(h, 'op', C.UOP), opnd=C.fld(h, 'opnd', C.UOP),
                                                     param=C.fld(h, 'param', C.UOP) & ~15)))
    add(0, 'ds_ring_16_lanes', ds16)
    neg = [dict(g, hdr=C.SV.header(5, 2, opnd=C.fld(g['hdr'], 'opnd', C.UOP), param=C.fld(g['hdr'], 'param', C.UOP))),
           dict(g, hdr=C.SV.header(5, 0, opnd=C.fld(g['hdr'], 'opnd', C.UOP), param=C.fld(g['hdr'], 'param', C.UOP) + 16)),
           dict(g, eff=[g['eff'][0] & ~3] + g['eff'][1:]),                                  # A in HBM
           dict(g, eff=[g['eff'][0], g['eff'][1] | (4 << 2)] + g['eff'][2:])]              # B INT8 rows
    for k, d in enumerate(neg):
        add(2, f'negative_{k}', [d])
    (out / 'att_rec.mem').write_text(''.join(C.hexw(r, 1173) + '\n' for r in recs))
    (out / 'att_ref.mem').write_text(''.join(C.hexw(r, 163) + '\n' for r in refs))
    (out / 'att_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'att_sizes.svh').write_text(f'localparam integer NREC = {len(recs)};\nlocalparam integer NCASE = {len(cases)};\n')
    print(f"{len(cases)} cases, {len(recs)} records; refused in run cases: "
          f"{sum(r for i, n, r in ids if not i.startswith('negative'))}")


if __name__ == '__main__':
    main()
