#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): bench vectors for ot_hgi_argmax_record (ARGMAX.LOCAL on ot_hgi_argmax18_m + the real VM).
--out DIR: am_case.mem a line {kind 4, rank 8, expect nan 1, expect value 32, expect id 32, first vm word, vm words,
           rec 683}; am_vm.mem {addr 32, value 32}.  kind 0 run, 2 negative.
Expected value / id: hbm-sim conformance vm_out where the vector carries it (cf-arg), else numpy argmax semantics on
FP32 (lowest index of the max, -0 == +0, the first NaN wins; global id = local + RANK * imm_a; hgi_sim u_argmax_local).
"""
import argparse
import random
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402


def am_ref(words, rank, imm):
    v = np.array(words, dtype=np.uint32).view(np.float32)
    nan = np.isnan(v)
    if nan.any():
        i = int(np.argmax(nan))
    else:
        i = int(np.argmax(v))
    return int(words[i]), i + rank * imm, bool(nan.any())


def rec_bus(d):
    A, O = d['eff'][0], d['eff'][4]
    return 1 | d['hdr'] << 1 | A << 129 | O << 385 | (d['n'][0] & 0x1FFFFF) << 641 | (d['n'][4] & 0x1FFFFF) << 662


def mk(A, O, imm=0, unit=7, op=0, n=None):
    eff = [A, 0, 0, 0, O, 0, 0]
    opnd = (1 if A else 0) | (16 if O else 0)
    return dict(hdr=C.SV.header(unit, op, opnd=opnd, imm_a=imm), eff=eff, n=[n if n is not None else C.fld(A, 'n'), 0, 0, 0, 2, 0, 0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_argmax_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    cases, vm = [], []

    def add(kind, d, rank, vmw, exp=(0, 0, False)):
        cases.append((kind, rank, int(exp[2]), exp[0], exp[1] & 0xFFFFFFFF, len(vm), len(vmw), rec_bus(d)))
        vm.extend(sorted(vmw.items()))
    nconf = 0
    for v, tr, cpl, vmi in C.conformance(lambda v: v['row'] == 'CF-ARG'):
        rank = int(v['dies'][0].get('rank', 0))
        for d in tr:
            if C.unit_of(d) != 7:
                continue
            A, O = d['eff'][0], d['eff'][4]
            ab, n, imm = C.fld(A, 'base'), d['n'][0], C.fld(d['hdr'], 'imm_a', C.UOP)
            val, gid, nan = am_ref([vmi.get(ab + i, 0) for i in range(n)], rank, imm)
            vo = C.vm_out_of(v['expect']['dies'][0])
            ob = C.fld(O, 'base')
            if ob in vo:                                  # the vector's own expected O words, where it carries them
                val, gid = vo[ob], vo.get(ob + 1, gid)
            add(0, d, rank, vmi, (val, gid, nan))
            nconf += 1
    rng = random.Random(11)
    tr, _ = C.qwen_dispatch()
    for d in [d for d in tr if C.unit_of(d) == 7]:
        A = d['eff'][0]
        n, ab, imm = d['n'][0], C.fld(A, 'base'), C.fld(d['hdr'], 'imm_a', C.UOP)
        w = [struct.unpack('<I', struct.pack('<f', rng.gauss(0, 4)))[0] for _ in range(n)]
        w[rng.randrange(n)] = w[rng.randrange(n)] = 0x41F00000            # ties at 30.0
        for rank in (0, 3):
            add(0, d, rank, {ab + i: x for i, x in enumerate(w)}, am_ref(w, rank, imm))
    for t in range(40):
        n = rng.choice([1, 2, 7, 8, 9, 63, 64, 65, 1000, 4096, rng.randrange(1, 3000)])
        ab = rng.randrange(0, 200000)
        ob = rng.randrange(210000, 262000)
        imm = rng.choice([0, 37984, 1347, rng.randrange(1 << 18)])
        rank = rng.randrange(0, 96) if imm < 2700 else rng.randrange(0, 4)
        kind = rng.choice(['rand', 'ties', 'zeros', 'nan', 'inf'])
        w = [struct.unpack('<I', struct.pack('<f', rng.uniform(-50, 50)))[0] for _ in range(n)]
        if kind == 'ties':
            for _ in range(min(n, 4)):
                w[rng.randrange(n)] = 0x42C80000
        elif kind == 'zeros':
            w = [rng.choice([0, 0x80000000]) for _ in range(n)]
        elif kind == 'nan':
            w[rng.randrange(n)] = 0x7FC00001
        elif kind == 'inf':
            w[rng.randrange(n)] = 0x7F800000
        val, gid, nan = am_ref(w, rank, imm)
        if gid >= 1 << 18:
            continue
        add(0, mk(C.SV.mdesc(space=1, base=ab, n=n, m=1), C.SV.mdesc(space=1, fmt=5, base=ob, n=2), imm=imm), rank,
            {ab + i: x for i, x in enumerate(w)}, (val, gid, nan))
    A = C.SV.mdesc(space=1, base=0, n=64, m=1)
    O = C.SV.mdesc(space=1, fmt=5, base=100, n=2)
    for d in [mk(A, O, unit=6), mk(A, O, op=1), mk(0, O), mk(A, 0), mk(C.SV.mdesc(space=0, base=0, n=64, m=1), O),
              mk(C.SV.mdesc(space=1, fmt=1, base=0, n=64, m=1), O), mk(C.SV.mdesc(space=1, base=0, n=64, m=2), O),
              mk(C.SV.mdesc(space=1, base=0, n=64, m=1, istride=2), O), mk(A, O, n=0),
              mk(A, C.SV.mdesc(space=0, base=100, n=2)), mk(A, O, imm=1 << 18)]:
        add(2, d, 0, {})
    (out / 'am_case.mem').write_text(''.join(
        f'{k:01X}{r:02X}{nn:01X}{v:08X}{i:08X}{f:08X}{c:08X}' + C.hexw(b, 684) + '\n' for k, r, nn, v, i, f, c, b in cases))
    (out / 'am_vm.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vm) or '0' * 16 + '\n')
    (out / 'am_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NVM = {max(1, len(vm))};\n')
    print(f"{len(cases)} cases ({nconf} conformance), {len(vm)} VM words")


if __name__ == '__main__':
    main()
