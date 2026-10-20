#!/usr/bin/env python3
"""Compile one no-reset four-row exp/sum programme as two real two-row phases."""
import argparse
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import prod_compile as C


def lines(path):
    return path.read_text().splitlines()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out', type=Path)
    ap.add_argument('--mutant', choices=['none', 'phase2_source_alias', 'phase2_scalar_stale'], default='none')
    a = ap.parse_args()
    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(0x504834)
    shared = (rng.integers(-2000, 2000, size=(512, 512)).astype(C.F) / C.F(1024)).astype(C.F)
    shared = np.where(np.abs(shared) < C.F(1 / 64), C.F(.75), shared).astype(C.F)
    mans = []
    for phase in range(2):
        seed = shared.copy()
        if phase:
            seed[:128] = shared[256:384]
            seed[499, :2] = shared[498, :2]
        opts = SimpleNamespace(out=str(out / f'phase{phase}'), rec='qw_softmax_exp_sum_r2',
                               rr=12, wr=10, fill_slack=1, drain_slack=2, side_ii=0,
                               rfd_slack=1, pretree=True, qpr=2, seed_override=seed)
        C.compile_rec(opts)
        mans.append(json.loads((out / f'phase{phase}/programme.json').read_text()))
    # Independent four-row golden from the shared external image and logical row identity.
    perm = []
    for begin in range(0, 64, 10):
        end = min(64, begin + 10)
        perm += [2 * k for k in range(begin, end)] + [2 * k + 1 for k in range(begin, end)]
    inverse = {block: issue for issue, block in enumerate(perm)}
    mods = C.RECS['qw_softmax_exp_sum_r2'][4]
    golden = []
    for global_row in range(4):
        phase, row = divmod(global_row, 2)
        vals = np.array([shared[(256 if phase else 0) + inverse[(i % 4096) // 32],
                               (row * 2 + i // 4096) * 128 + i % 32]
                         for i in range(8192)], dtype=C.F)
        scalar = shared[498 if phase else 499, row]
        zeros = np.zeros(8192, dtype=C.F)
        pointwise = C.golden(mods, vals, np.full(8192, scalar, dtype=C.F), zeros, zeros)
        ref = C.model_reduce('sum', pointwise)
        assert int(mans[phase]['reduction']['finals'][str(row)], 16) == ref
        golden.append(f'{ref:08x}')
    barrier = 32  # explicit charged guard after phase0's WR-complete retirement and tail
    offset = mans[0]['edges'] + barrier
    merged = {n: [] for n in ['prog.mem', 'tree.mem', 'explw.mem', 'expw.mem', 'exps.mem']}
    maskq = (1 << C.QW) - 1
    for phase in range(2):
        base = out / f'phase{phase}'
        t = offset if phase else 0
        for raw in lines(base / 'prog.mem'):
            value = int(raw, 16)
            result = 0
            for q in range(4):
                qword = value >> (q * C.QW) & maskq
                red = qword & ((1 << 74) - 1)
                rf = qword >> 74 & ((1 << 54) - 1)
                vmw = qword >> 128 & ((1 << 312) - 1)
                vmr = qword >> 440 & ((1 << 240) - 1)
                ctl = qword >> 680
                for port in range(8):
                    r = vmr >> (30 * port) & ((1 << 30) - 1)
                    if phase and r >> 29:
                        sec = r >> 13 & 0xffff
                        row = sec >> 4 & 511
                        newrow = (row + 256 if row < 128 else 498 if row == 499 else row)
                        if a.mutant == 'phase2_source_alias' and row < 128:
                            newrow = row
                        if a.mutant == 'phase2_scalar_stale' and row == 499:
                            newrow = 499
                        sec = (sec & ~(511 << 4)) | newrow << 4
                        r = (r & ~(0xffff << 13)) | sec << 13
                        vmr = (vmr & ~(((1 << 30) - 1) << (30 * port))) | r << (30 * port)
                    w = vmw >> (39 * port) & ((1 << 39) - 1)
                    if w >> 38:
                        sec = w >> 8 & 0xffff
                        row = sec >> 4 & 511
                        # Tensor destinations are disjoint; final scalar sectors reuse dead input rows0/1.
                        newrow = phase if row == 498 else row + (256 if phase else 0)
                        assert 0 <= newrow < 512
                        sec = (sec & ~(511 << 4)) | newrow << 4
                        w = (w & ~(0xffff << 8)) | sec << 8
                        vmw = (vmw & ~(((1 << 39) - 1) << (39 * port))) | w << (39 * port)
                qword = ((((ctl << 240 | vmr) << 312 | vmw) << 54 | rf) << 74) | red
                result |= qword << (q * C.QW)
            merged['prog.mem'].append(f'{result:0{4 * C.QW // 4}x}')
        for n in ['tree.mem', 'explw.mem']:
            merged[n] += lines(base / n)
        for n in ['expw.mem', 'exps.mem']:
            for raw in lines(base / n):
                edge = int(raw[:8], 16) + t
                if n == 'expw.mem':
                    sec = int(raw[10:14], 16)
                    row = sec >> 4 & 511
                    newrow = phase if row == 498 else row + (256 if phase else 0)
                    sec = (sec & ~(511 << 4)) | newrow << 4
                    raw = raw[:10] + f'{sec:04x}' + raw[14:]
                merged[n].append(f'{edge:08x}' + raw[8:])
        if not phase:
            for n, width in [('prog.mem', 4 * C.QW // 4), ('tree.mem', 48), ('explw.mem', 8)]:
                merged[n] += ['0' * width] * barrier
    for name, content in merged.items():
        (out / name).write_text('\n'.join(content) + '\n')
    (out / 'arith').mkdir(exist_ok=True)
    (out / 'arith/seed.mem').write_text('\n'.join(f'{x:08x}' for x in shared.view(np.uint32).ravel()) + '\n')
    retire = offset + mans[1]['retire_edge']
    manifest = dict(schema='toksim.hbm.su_phase4.v1', record='qw_softmax_exp_sum_r4_phased', rows=4,
                    phases=mans, edges=len(merged['prog.mem']), expected_vm_writes=len(merged['expw.mem']),
                    expected_scalars=len(merged['exps.mem']), cycles_serial=retire,
                    cycles_stream_833ps=round(retire * 4 / 3, 2), dispatch_edge=0,
                    phase2_offset=offset, charged_barrier_edges=barrier, reset_between_phases=False,
                    golden_model_rows=golden, mutant=a.mutant,
                    admission='256 local operand/output rows per phase; source0..127/256..383; tensor output128..255/384..511; final scalar VM rows0/1; scalar sources499/498 read before later writes')
    (out / 'programme.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({k: manifest[k] for k in ['record', 'edges', 'cycles_serial', 'golden_model_rows', 'mutant']}))


if __name__ == '__main__':
    main()
