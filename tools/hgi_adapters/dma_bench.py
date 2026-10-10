#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_dma_record (DMA.* -> mover / fence commands).

--out DIR: dma_rec.mem {pos1 21, n_O 21, n_A 21, O 256, A 256, header 128} (703 b); dma_ref.mem {kind 2, move 227}
(kind 0 move, 1 fence, 2 refuse); dma_case.mem {kind, first, count}.  Reference = the spec text (6.4, 6.7) and
hgi_sim u_dma_load / u_dma_store / u_dma_kvwb_ds, written independently of the RTL.
Sources: hbm-sim conformance DMA vectors (cf-emb, cf-idxd_n_from_vm, cf-kv x 3), the Qwen3-8B token program's DMA
records (257), DS KVWB at the 1M position, negatives.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def ist(d):
    return 0 if C.fld(d, 'ibcast') else (C.fld(d, 'istride') or 1)


def ref(d):
    h = d['hdr']
    A, O = d['eff'][0], d['eff'][4]
    unit, op, opnd = C.fld(h, 'unit', C.UOP), C.fld(h, 'op', C.UOP), C.fld(h, 'opnd', C.UOP)
    asp, afm, osp, ofm = C.fld(A, 'space'), C.fld(A, 'fmt'), C.fld(O, 'space'), C.fld(O, 'fmt')
    na, no = d['n'][0], d['n'][4]
    am, om = C.fld(A, 'm'), C.fld(O, 'm')
    pres = (opnd & 1) and (opnd & 16)
    if unit != 8 or op > 3:
        return 2 << 227
    if op == 2:
        return 1 << 227
    if op == 0:
        ok = (pres and asp in (0, 1) and afm in (0, 1, 2, 4, 5) and osp == 1 and ofm in (0, 5) and (ofm == 5) == (afm == 5)
              and na == no and am == om)
    else:
        ok = (pres and asp == 1 and afm in (0, 5) and osp == 0 and ofm in (0, 1, 2, 5) and (ofm == 5) == (afm == 5)
              and na == no)
        ok = ok and (am == om if op == 1 else (om and not (om & (om - 1)) and am == 1))
    if not ok:
        return 2 << 227
    obase, m = C.fld(O, 'base'), am
    if op == 3:
        obase = (obase + ((d['pos1'] - 1) % om) * C.fld(O, 'stride')) & ((1 << 40) - 1)
        m = 1
    f = [(asp, 2), (afm, 3), (C.fld(A, 'base'), 40), (C.fld(A, 'stride'), 32), (ist(A), 16), (osp, 2), (ofm, 3),
         (obase, 40), (C.fld(O, 'stride'), 32), (ist(O), 16), (m, 20), (na, 21)]
    w, sh = 0, 0
    for v, b in f:
        w |= (v & ((1 << b) - 1)) << sh
        sh += b
    return w


def rec(op, A=None, O=None, pos1=1, n_a=None, n_o=None, unit=8):
    opnd = (1 if A is not None else 0) | (16 if O is not None else 0)
    eff = [A or 0, 0, 0, 0, O or 0, 0, 0]
    return dict(hdr=C.SV.header(unit, op, opnd=opnd), sut=0, eff=eff, pos1=pos1,
                n=[n_a if n_a is not None else C.fld(eff[0], 'n'), 0, 0, 0,
                   n_o if n_o is not None else C.fld(eff[4], 'n'), 0, 0])


def md(**kw):
    return C.SV.mdesc(**kw)


def pack(d):
    return (d['hdr'] | d['eff'][0] << 128 | d['eff'][4] << 384 | (d['n'][0] & 0x1FFFFF) << 640
            | (d['n'][4] & 0x1FFFFF) << 661 | (d['pos1'] & 0x1FFFFF) << 682)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_dma_tb')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    recs, refs, cases, man = [], [], [], []

    def add(kind, ident, ds):
        cases.append((kind, len(recs), len(ds)))
        for d in ds:
            recs.append(pack(d))
            refs.append(ref(d))
        man.append(dict(id=ident, records=len(ds), kinds=[ref(d) >> 227 for d in ds][:16]))
    for v, tr, cpl, vm in C.conformance(lambda v: any(r['unit'] == 'DMA' for r in v['records'])):
        add(0, v['id'], [d for d in tr if C.unit_of(d) == 8])
    tr, _ = C.qwen_dispatch()
    add(0, 'qwen3_8b_token_dma', [d for d in tr if C.unit_of(d) == 8])
    ring = md(space=0, fmt=2, base=0x7_0000_0000, n=512, m=128, stride=576)
    row = md(space=1, fmt=0, base=1000, n=512, m=1)
    add(0, 'ds_kvwb_positions', [rec(3, row, ring, pos1=p + 1) for p in (0, 1, 127, 128, 130, 1048575, 1000000)]
        + [rec(2), rec(0, md(space=0, fmt=4, base=0x100, n=4096, m=1, stride=4096), md(space=1, base=0, n=4096, m=1)),
           rec(1, md(space=1, base=0, n=128, m=8, stride=128), md(space=0, fmt=1, base=0x2000, n=128, m=8, stride=256))])
    neg = {'unit_not_dma': rec(0, row, md(space=1, base=0, n=512), unit=2),
           'op_4': dict(rec(0, row, md(space=1, base=0, n=512)), hdr=C.SV.header(8, 4, opnd=17)),
           'load_to_hbm': rec(0, row, md(space=0, base=0, n=512)),
           'store_from_hbm': rec(1, md(space=0, base=0, n=512), md(space=0, base=64, n=512)),
           'load_fp4_src': rec(0, md(space=0, fmt=3, base=0, n=512), md(space=1, base=0, n=512)),
           'load_u32_to_fp32': rec(0, md(space=0, fmt=5, base=0, n=8), md(space=1, fmt=0, base=0, n=8)),
           'n_mismatch': rec(0, md(space=0, fmt=1, base=0, n=512), md(space=1, base=0, n=511)),
           'kvwb_ring_96': rec(3, row, md(space=0, fmt=2, base=0, n=512, m=96, stride=576), pos1=5),
           'kvwb_two_rows': rec(3, md(space=1, base=0, n=512, m=2, stride=512), ring, pos1=5),
           'store_no_o': rec(1, row, None)}
    for k, d in neg.items():
        add(2, k, [d])
    (out / 'dma_rec.mem').write_text(''.join(C.hexw(r, 703) + '\n' for r in recs))
    (out / 'dma_ref.mem').write_text(''.join(C.hexw(r, 229) + '\n' for r in refs))
    (out / 'dma_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'dma_sizes.svh').write_text(f'localparam integer NREC = {len(recs)};\nlocalparam integer NCASE = {len(cases)};\n')
    (out / 'dma_bench.json').write_text(json.dumps(dict(cases=man), indent=1))
    print(f"{len(cases)} cases, {len(recs)} records; " + ', '.join(f"{m['id']} {m['records']}" for m in man[:5]))


if __name__ == '__main__':
    main()
