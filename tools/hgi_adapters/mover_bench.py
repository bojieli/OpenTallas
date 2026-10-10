#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for the DMA path ot_hgi_dma_record -> ot_hgi_dma_mover (data exact).
--out DIR: mo_case.mem {first rec, recs, first vmi, vmi, first hbi, hbi, first vme, vme, first hbe, hbe} (10 x 32 b);
mo_rec.mem {pos1 21, n_O 21, n_A 21, O 256, A 256, header 128} (703 b); mo_vmi / mo_vme {addr 32, value 32};
mo_hbi / mo_hbe {word address 38 (byte / 4), value 32}.
Expected memories: hbm-sim conformance (cf-idxd n_from_vm vm_out, cf-kv x 3 hbm_out) and, for random LOAD / STORE
records over every format, stride and alignment, hgi_sim machine.decode_fmt / encode_fmt (to_bf16 RNE, to_fp8 RNE
saturating) applied to the initial memories.
"""
import argparse
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
sys.path.insert(0, str(C.ROOT / 'tools'))
from hgi_sim import machine as MC  # noqa: E402

FMT = {0: 'FP32', 1: 'BF16', 2: 'FP8E4M3', 4: 'INT8', 5: 'U32'}
ES = {0: 4, 1: 2, 2: 1, 4: 1, 5: 4}


def words_of_bytes(bmap):
    w = {}
    for a, v in bmap.items():
        w.setdefault(a >> 2, 0)
        w[a >> 2] |= v << (8 * (a & 3))
    return w


def pack(d):
    return (d['hdr'] | d['eff'][0] << 128 | d['eff'][4] << 384 | (d['n'][0] & 0x1FFFFF) << 640
            | (d['n'][4] & 0x1FFFFF) << 661 | (d['pos1'] & 0x1FFFFF) << 682)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_mover_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    cases, recs, L = [], [], dict(vmi=[], hbi=[], vme=[], hbe=[])

    def add(ds, vmi, hbi_bytes, vme, hbe_bytes):
        c = [len(recs), len(ds)]
        for k, m in (('vmi', vmi), ('hbi', words_of_bytes(hbi_bytes)), ('vme', vme), ('hbe', words_of_bytes(hbe_bytes))):
            c += [len(L[k]), len(m)]
            L[k].extend(sorted(m.items()))
        cases.append(c)
        recs.extend(pack(d) for d in ds)
    for v, tr, cpl, vm in C.conformance(lambda v: v['id'] in ('idxd_n_from_vm', 'kv_linear_append_pos127',
                                                               'kvwb_ds_pos130', 'kvwb_ds_pos1048575')):
        die, ex = v['dies'][0], v['expect']['dies'][0]
        hbi = {}
        for ent in die.get('hbm_in', []):
            base, hexs = ent[0], ent[1]
            if hexs is None:                                  # a zero region (the HBM model reads 0 by default)
                continue
            for q, b in enumerate(bytes.fromhex(hexs)):
                hbi[base + q] = b
        hbe = {}
        import json
        for base, hexs in json.loads(ex['hbm_out']) if isinstance(ex['hbm_out'], str) else ex['hbm_out']:
            for q, b in enumerate(bytes.fromhex(hexs)):
                hbe[base + q] = b
        vme = C.vm_out_of(ex) if ex.get('vm_out') else {}
        add([d for d in tr if C.unit_of(d) == 8], vm, hbi, vme, hbe)
    rng = random.Random(77)
    for t in range(60):
        load = rng.random() < 0.5
        f = rng.choice([0, 1, 2, 4, 5]) if load else rng.choice([0, 1, 2, 5])
        n, m = rng.randint(1, 70), rng.randint(1, 4)
        es = ES[f]
        hist = rng.choice([0, 1, 1, 2, 3])
        hb = rng.randrange(0, 1 << 20) * 32 + 0x2_0000_0000      # HBM bases 32-byte aligned (spec 6.10)
        hst = (n * max(1, hist) * es + rng.randint(0, 40)) // es * es   # elements naturally aligned
        vb = rng.randrange(0, 200000)
        vist = rng.choice([0, 1, 1, 2])
        vst = n * max(1, vist) + rng.randint(0, 9)
        hdesc = C.SV.mdesc(space=0, fmt=f, base=hb, n=n, m=m, stride=hst, istride=hist)
        vdesc = C.SV.mdesc(space=1, fmt=5 if f == 5 else 0, base=vb, n=n, m=m, stride=vst, istride=vist)
        A, O = (hdesc, vdesc) if load else (vdesc, hdesc)
        d = dict(hdr=C.SV.header(8, 0 if load else 1, opnd=0b10001), eff=[A, 0, 0, 0, O, 0, 0], n=[n, 0, 0, 0, n, 0, 0], pos1=1)
        hbi, vmi = {}, {}
        hist_e, vist_e = hist or 1, vist or 1
        haddr = [[hb + o * hst + i * hist_e * es for i in range(n)] for o in range(m)]
        vaddr = [[vb + o * vst + i * vist_e for i in range(n)] for o in range(m)]
        for o in range(m):                                  # background bytes so partial writes are visible
            for b in range(haddr[o][0] - 4, haddr[o][-1] + es + 4):
                hbi[b] = rng.getrandbits(8)
        vme, hbe = {}, dict(hbi)
        if load:
            for o in range(m):
                for i in range(n):
                    raw = bytes(hbi[haddr[o][i] + k] for k in range(es))
                    if f == 2 and raw[0] & 0x7F == 0x7F:
                        raw = bytes([raw[0] & 0x80])         # avoid NaN codes (the mover returns qNaN; golden NaN)
                        for k in range(es):
                            hbi[haddr[o][i] + k] = raw[k]
                    val = MC.decode_fmt(np.frombuffer(raw, dtype=np.uint8), FMT[f])
                    w = int(np.asarray(val).astype(np.uint32)[0]) if f == 5 else int(np.asarray(val, dtype=np.float32).view(np.uint32)[0])
                    vme[vaddr[o][i]] = w
            hbe = dict(hbi)
        else:
            for o in range(m):
                for i in range(n):
                    kind = rng.random()
                    if f == 2:
                        x = rng.choice([rng.uniform(-500, 500), rng.uniform(-1, 1) * 2 ** rng.randint(-12, 0),
                                        rng.choice([448.0, 464.0, 480.0, 0.0, 2 ** -10, 3 * 2 ** -11, 2 ** -9 * 1.5])])
                    else:
                        x = rng.uniform(-1e3, 1e3) if kind < 0.8 else rng.choice([0.0, 1.0 + 2 ** -8, 1.0 + 3 * 2 ** -8])
                    w = int(np.float32(x).view(np.uint32)) if f != 5 else rng.getrandbits(32)
                    vmi[vaddr[o][i]] = w
                    raw = MC.encode_fmt(np.asarray([w], dtype=np.uint32).view(np.float32), FMT[f])
                    for k in range(es):
                        hbe[haddr[o][i] + k] = int(raw[k])
        add([d], vmi, hbi, vme, hbe)
    (out / 'mo_rec.mem').write_text(''.join(C.hexw(r, 703) + '\n' for r in recs))
    (out / 'mo_case.mem').write_text(''.join(''.join(f'{x:08X}' for x in c) + '\n' for c in cases))
    for k in ('vmi', 'vme'):
        (out / f'mo_{k}.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in L[k]) or '0' * 16 + '\n')
    for k in ('hbi', 'hbe'):
        (out / f'mo_{k}.mem').write_text(''.join(f'{a:010X}{x:08X}\n' for a, x in L[k]) or '0' * 18 + '\n')
    (out / 'mo_sizes.svh').write_text(''.join(f'localparam integer {k.upper()} = {max(1, len(v))};\n' for k, v in L.items())
                                      + f'localparam integer NCASE = {len(cases)};\nlocalparam integer NREC = {len(recs)};\n')
    print(f"{len(cases)} cases, {len(recs)} records")


if __name__ == '__main__':
    main()
