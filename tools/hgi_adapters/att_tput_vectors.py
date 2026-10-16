#!/usr/bin/env python3
"""hgi-1010/g (2026-10-10): THROUGHPUT vectors for the ATT unit die body ot_hgi_att_unit at production record shapes.

Same mem format as att_unit_bench.py (au_case / au_rec / au_vmi / au_hbm / au_exp + au_sizes.svh, read by
tb_hgi_att_tput.sv), plus tput_cases.json describing every case (vehicle, shape, records, the simulator's price).

Cases (records run back to back, golden = hgi_sim.lib att_qk / att_pv, exactly machine.u_att_qk / u_att_pv):
  qwen_T<T>   Qwen3-8B P8191 attention of one die (qwen_compiler records 16, 17, 21, 22): ATT.QK kv0, ATT.QK kv1,
              ATT.PV kv0, ATT.PV kv1; 4 lanes (4 query heads per KV head), hd 128, FP8 E4M3 K / V planes, no ring;
              T rows (n_sel = POS1; the production shape is T = 8,192)
  ds_L0       DS-V4.1 1M rank 0 layer 0 (exp_gf ds_L0 meta k 21 / 25): QK, PV over the window ring
              (B: HBM FP32 rows of 512, n 128, ring m 128, stride 2,048), lanes 1, POS1 = 1,048,576
  ds_L20      DS-V4.1 1M rank 0 layer 20 (programs/ds_v41_1M_L20_per_die.json trace 52 / 57): the window ring then
              C = 512 selected compressed rows (HBM FP32, stride 2,048): T = 640
  ring_wrap   exactness only: ds_L0's shape at POS1 = 1,000 (the ring wraps; the MUT_RING mutant must fail here)
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
from att_unit_bench import pack, sectors  # noqa: E402
from hgi_sim import lib as A  # noqa: E402
from hgi_sim import machine as MC  # noqa: E402

F = np.float32
FMT = dict(FP32=0, BF16=1, FP8E4M3=2)
FIRST_ACCESS, BW, ATT_FIXED = 104.0, 3166.7, 225.0      # hgi_sim.timing: MEAS hbm.first_access, hbm B/cyc, ATT.fixed
DS_PRICE = {128: 147.144, 640: 339.144}                   # NativeCost ATT = walk(attend tile rows) / 2 (T128 / T640)


def qwen_price(T):
    """hgi_sim.timing.cost ATT for the Qwen record at T rows (hd 128, FP8)"""
    return FIRST_ACCESS + T * 128 * 1 / BW + ATT_FIXED


def rows_bytes(M, fmt):
    if fmt == 'FP8E4M3':
        return bytes(MC.fp8_encode(M.reshape(-1)))
    return M.astype(F).tobytes()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cases', default='qwen_T512,qwen_T1024,ds_L0,ds_L20,ring_wrap')
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    cases, recs, vmi, hbm, exp, meta = [], [], [], [], [], []

    def add(name, rs, vm, hb, ex, info):
        cases.append((len(recs), len(rs), len(vmi), len(vm), len(hbm), len(hb), len(exp), len(ex)))
        recs.extend(pack(d) for d in rs)
        vmi.extend(sorted(vm.items()))
        hbm.extend(sorted(hb.items()))
        exp.extend(sorted(ex.items()))
        meta.append(dict(name=name, **info))
    rng = np.random.default_rng(1010)

    def att_pair(lanes, hd, nb, nc, fmt, ring_m, pos1, kbase, vbase, cbk, cbv, qbase, pbase, sbase, obase, sstr, tag,
                 heads_kv=1):
        """records QK x heads_kv then PV x heads_kv; returns (records, vm, hbm, expected, record info)"""
        T = nb + nc
        st = hd * (4 if fmt == 'FP32' else 1)
        rs, vm, hb, ex, info = [], {}, [], {}, []
        prm = lanes | ((hd // 64 - 1) << 4) | ((1 << 8) if ring_m else 0)
        pending_pv = []
        for kv in range(heads_kv):
            K = A.to_fp8(rng.standard_normal((T, hd)).astype(F))
            V = A.to_fp8(rng.standard_normal((T, hd)).astype(F))
            q = A.to_bf16(rng.standard_normal((lanes, hd)).astype(F))
            p = A.to_bf16(rng.uniform(0, 1, (lanes, T)).astype(F))
            kb, vb = kbase + kv * (1 << 26), vbase + kv * (1 << 26)
            for base, M in ((kb, K), (vb, V)):
                if ring_m:                             # list row t (t < nb) lives at slot (pos1 - nb + t) mod m
                    ring = np.zeros((ring_m, hd), F)
                    for t in range(nb):
                        ring[(pos1 - nb + t) % ring_m] = M[t]
                    hb.append((base, rows_bytes(ring, fmt)))
                else:
                    hb.append((base, rows_bytes(M[:nb], fmt)))
                if nc:
                    hb.append((base + (cbk - kbase), rows_bytes(M[nb:], fmt)))
            qa, pa = qbase + kv * lanes * hd, pbase + kv * lanes * sstr
            sa, oa = sbase + kv * lanes * sstr, obase + kv * lanes * hd
            for h in range(lanes):
                for i in range(hd):
                    vm[qa + h * hd + i] = int(q[h, i].view(np.uint32))
                for t in range(T):
                    vm[pa + h * sstr + t] = int(p[h, t].view(np.uint32))
                s = A.att_qk(q[h], K)
                for t in range(T):
                    ex[sa + h * sstr + t] = int(F(s[t]).view(np.uint32))
                o = A.att_pv(p[h], V)
                for i in range(hd):
                    ex[oa + h * hd + i] = int(F(o[i]).view(np.uint32))
            opnd = 0b10111 if nc else 0b10011

            def bdesc(base):
                return C.SV.mdesc(space=0, fmt=FMT[fmt], base=base, n=nb, m=ring_m or nb, stride=st)

            def cdesc(base):
                return C.SV.mdesc(space=0, fmt=FMT[fmt], base=base + (cbk - kbase), n=nc, m=1, stride=st) if nc else 0
            rs.append(dict(hdr=C.SV.header(5, 0, opnd=opnd, param=prm),
                           eff=[C.SV.mdesc(space=1, base=qa, n=hd, m=lanes, stride=hd), bdesc(kb), cdesc(kb), 0,
                                C.SV.mdesc(space=1, base=sa, n=T, m=lanes, stride=sstr), 0, 0],
                           n=[hd, nb, nc, 0, T, 0, 0], pos1=pos1))
            info.append(dict(op=0, tag=f'{tag}.qk.kv{kv}'))
            pending_pv.append((dict(hdr=C.SV.header(5, 1, opnd=opnd, param=prm),
                                    eff=[C.SV.mdesc(space=1, base=pa, n=T, m=lanes, stride=sstr), bdesc(vb), cdesc(vb),
                                         0, C.SV.mdesc(space=1, base=oa, n=hd, m=lanes, stride=hd), 0, 0],
                                    n=[T, nb, nc, 0, hd, 0, 0], pos1=pos1), dict(op=1, tag=f'{tag}.pv.kv{kv}')))
        for d, i in pending_pv:
            rs.append(d)
            info.append(i)
        return rs, vm, sectors(hb), ex, info

    for name in a.cases.split(','):
        if name.startswith('qwen_T'):
            T = int(name[6:])
            rs, vm, hb, ex, info = att_pair(4, 128, T, 0, 'FP8E4M3', 0, T, 1 << 34, (1 << 34) + (1 << 30), 0, 0,
                                            0, 20000, 20000 + 8 * T + 64, 4096, T + 8, 'qwen', heads_kv=2)
            for i in info:
                i.update(price=round(qwen_price(T), 1), price_at_8192=round(qwen_price(8192), 1))
            add(name, rs, vm, hb, ex, dict(vehicle='qwen', T=T, lanes=4, hd=128, fmt='FP8E4M3', ring=0, records=info))
        elif name in ('ds_L0', 'ring_wrap'):
            pos1 = 1048576 if name == 'ds_L0' else 1000
            rs, vm, hb, ex, info = att_pair(1, 512, 128, 0, 'FP32', 128, pos1, 1 << 34, (1 << 34) + (1 << 30), 0, 0,
                                            0, 4096, 8192, 12288, 136, 'ds_L0' if name == 'ds_L0' else 'wrap')
            for i in info:
                i.update(price=DS_PRICE[128])
            add(name, rs, vm, hb, ex, dict(vehicle='ds', T=128, lanes=1, hd=512, fmt='FP32', ring=128, pos1=pos1,
                                           records=info))
        elif name == 'ds_L20':
            rs, vm, hb, ex, info = att_pair(1, 512, 128, 512, 'FP32', 128, 1048576, 1 << 34, (1 << 34) + (1 << 30),
                                            (1 << 34) + (1 << 29), 0, 0, 4096, 8192, 12288, 648, 'ds_L20')
            for i in info:
                i.update(price=DS_PRICE[640])
            add(name, rs, vm, hb, ex, dict(vehicle='ds', T=640, lanes=1, hd=512, fmt='FP32', ring=128, nc=512,
                                           records=info))
        else:
            raise SystemExit(f'unknown case {name}')
    (out / 'au_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    (out / 'au_rec.mem').write_text(''.join(C.hexw(r, 1216) + '\n' for r in recs))
    (out / 'au_vmi.mem').write_text(''.join(f'{a_:08X}{w:08X}\n' for a_, w in vmi))
    (out / 'au_exp.mem').write_text(''.join(f'{a_:08X}{w:08X}\n' for a_, w in exp))
    (out / 'au_hbm.mem').write_text(''.join(f'{a_:010X}{d:064X}\n' for a_, d in hbm))
    (out / 'au_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NREC = {len(recs)};\n'
                                      f'localparam integer NVMI = {max(1, len(vmi))};\nlocalparam integer NHBM = {len(hbm)};\n'
                                      f'localparam integer NEXP = {len(exp)};\n')
    (out / 'tput_cases.json').write_text(json.dumps(meta, indent=1) + '\n')
    print(f'{len(cases)} cases, {len(recs)} records, {len(hbm)} HBM sectors, {len(exp)} expected words')


if __name__ == '__main__':
    main()
