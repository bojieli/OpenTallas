#!/usr/bin/env python3
"""Compare completed native I7/I8 readbacks on their actual produced I6 input.

Reuses the retained golden QE arithmetic and released weight tensors. No
expected intermediate enters the native caller, and no prefix is rerun.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np
os.environ.setdefault('HDC_V41_ARITH', 'chunk8')
import v41_fullshape_isa as M
from dsrom_s81_execution_binding import CanonicalS81Execution


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rank', type=int, choices=range(4), default=0)
    p.add_argument('--owner', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--inputs', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    terminal = json.loads((a.run/'terminal.json').read_text())
    if terminal.get('exit_code') != 0:
        raise ValueError('completed native field caller required before comparison')
    manifest = json.loads((a.inputs/'native_field_inputs.json').read_text())
    if terminal.get('rank', 0) != a.rank:
        raise ValueError('completed caller rank differs from requested comparison')
    path = a.inputs/f'I6.XN_rank{a.rank}.u32'
    if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['files'][path.name]:
        raise ValueError('produced XN changed')
    x = np.fromfile(path, dtype='<u4').view(M.F)
    if x.size != 5120 or M.V.ARITH != 'chunk8' or M.V.FUSE:
        raise ValueError('actual XN/chunk8 arithmetic binding')
    execution = CanonicalS81Execution(a.owner)
    checkpoint = M.LC.Checkpoint(a.checkpoint)
    xq, xe = M.V.quant_fp8(x)
    results = []
    for pc in (7, 8):
        node = execution.source.nodes[f'L20.I{pc}']
        fragments = execution.source.resolve(node['id'], a.rank)['fragments']
        if len(fragments) != 1:
            raise ValueError('one full canonical field matrix required')
        matrix = fragments[0]['matrix']
        f = node['instruction']
        raw = M.V._blocked(checkpoint.get(matrix['tensor']),
                           checkpoint.get(matrix['source_scale_tensor']), matrix['tensor'])
        shard = matrix['rank_slices'][a.rank]
        r0, r1 = shard['rows']
        c0, c1 = shard['cols']
        w = M.V.Q8(raw.q[r0:r1, c0:c1], raw.e[r0:r1, c0//32:c1//32])
        if w.shape != (f['qe_nout'], 5120):
            raise ValueError('actual released matrix/source dimensions')
        blocks = [np.ldexp((w.q[:, b*32:(b+1)*32] @ xq[b*32:(b+1)*32]).astype(M.F),
                           w.e[:, b]+xe[b]).astype(M.F) for b in range(160)]
        reference = M.V.csum(np.stack(blocks, axis=-1))
        if not f.get('qe_unrounded', 0):
            reference = M.G.to_bf16(reference)
        reference = M.G.bits(reference).astype('<u4')
        output = a.run/'runtime'/f'native_L20_I{pc}.u32'
        actual = np.fromfile(output, dtype='<u4')
        if actual.shape != reference.shape:
            raise ValueError('native full field readback extent')
        different = np.flatnonzero(actual != reference)
        results.append(dict(node=node['id'], rows=int(actual.size),
            bit_mismatches=int(different.size), native_output_sha256=M.sha(output),
            source_template_sha256=node['template_word_sha256'],
            first_differences=[dict(row=int(i), actual=int(actual[i]), reference=int(reference[i]))
                               for i in different[:16]]))
    record = dict(scope=f'rank{a.rank} stage37 full native I7/I8 on produced SIM_ONLY I6 XN', rank=a.rank,
                  position=1048575, token=16754, full_token=False,
                  exact=all(r['bit_mismatches'] == 0 for r in results), results=results,
                  input_sha256=manifest['files'][path.name],
                  source_inputs_sha256=execution.input_sha256)
    with (a.run/'comparison.json').open('x') as stream:
        json.dump(record, stream, indent=2)
        stream.write('\n')
    print(json.dumps(record), flush=True)
    return 0 if record['exact'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
