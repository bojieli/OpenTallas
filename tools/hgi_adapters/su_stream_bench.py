#!/usr/bin/env python3
"""hgi-adapters (2026-10-09): STREAM bench vectors: the Qwen3-8B head path SM -> STREAM 0 -> SU.VOP head_scale (A = STREAM,
B = VM row scales, O = STREAM) -> ARGMAX.LOCAL (A = STREAM, O = VM {value, id}), the records exactly as the hbm-sim
Qwen token program issues them (shrunk n for the short cases, the full 37,984 for one).
--out DIR: ss_case.mem {n 32, rank 32, imm 32, exp value 32, exp id 32, first stream 32, first vm 32, n vm 32, su rec 2,197,
am rec 683}; ss_stream.mem {idx 32, value 32} in arrival order (shuffled); ss_vm.mem {addr 32, value 32}.
Expected: numpy argmax (lowest index on ties) of the golden products mul(logit, scale) (M1 AB, FP32), id + RANK x imm_a.
"""
import argparse
import random
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common as C  # noqa: E402
import su_bench as S  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default='/tmp/hgi_ss_tb')
    out = Path(ap.parse_args().out)
    out.mkdir(parents=True, exist_ok=True)
    tr, _ = C.qwen_dispatch()
    su = next(d for d in tr if C.unit_of(d) == 2 and C.fld(d['eff'][0], 'space') == 2)
    am = next(d for d in tr if C.unit_of(d) == 7)
    rng = random.Random(4)
    cases, stream, vm = [], [], []
    for n, rank in ((300, 0), (1001, 3), (37984, 2)):
        A, B, O = su['eff'][0], su['eff'][1], su['eff'][4]
        def nn(d, n):
            return d & ~(((1 << 20) - 1) << 48) | (n << 48)
        sud = dict(su, eff=[nn(A, n), nn(B, n), 0, 0, nn(O, n), 0, 0], n=[n, n, 0, 0, n, 0, 0])
        amA = nn(am['eff'][0], n)
        amd = dict(am, eff=[amA] + am['eff'][1:], n=[n] + am['n'][1:])
        logits = np.array([rng.gauss(0, 3) for _ in range(n)], dtype=np.float32)
        scales = np.array([rng.uniform(0.002, 0.02) for _ in range(n)], dtype=np.float32)
        logits[rng.randrange(n)] = logits[rng.randrange(n)] = 25.0
        scales[:] = np.where(logits == 25.0, np.float32(0.01), scales)
        prod = (logits * scales).astype(np.float32)
        j = int(np.argmax(prod))
        imm = C.fld(am['hdr'], 'imm_a', C.UOP)
        order = list(range(n))
        rng.shuffle(order)
        bb = C.fld(B, 'base')
        cases.append((n, rank, imm, int(prod.view(np.uint32)[j]), j + rank * imm, len(stream), len(vm), n,
                      S.pack_rec(sud), 1 | amd['hdr'] << 1 | amd['eff'][0] << 129 | amd['eff'][4] << 385 | n << 641 | 2 << 662))
        stream.extend((i, int(logits.view(np.uint32)[i])) for i in order)
        vm.extend((bb + i, int(scales.view(np.uint32)[i])) for i in range(n))
    (out / 'ss_case.mem').write_text(''.join(''.join(f'{x & 0xFFFFFFFF:08X}' for x in c[:8]) + C.hexw(c[8], 2197) + C.hexw(c[9], 683) + '\n' for c in cases))
    (out / 'ss_stream.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in stream))
    (out / 'ss_vm.mem').write_text(''.join(f'{a:08X}{x:08X}\n' for a, x in vm))
    (out / 'ss_sizes.svh').write_text(f'localparam integer NCASE = {len(cases)};\nlocalparam integer NSTR = {len(stream)};\n'
                                      f'localparam integer NVM = {len(vm)};\n')
    print(f"{len(cases)} cases, {len(stream)} stream beats; su param {hex(C.fld(su['hdr'], 'param', C.UOP))}")


if __name__ == '__main__':
    main()
