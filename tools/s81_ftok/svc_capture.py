#!/usr/bin/env python3
"""Assemble actual SVC pin words for the real SU; reject gaps/duplicates/faults.

Input traces are written by tb_dsfd_svc_c +trace=DIR. Four stack traces
form one die's H=16 scores and D=512 PV words. This is a component handoff,
not native token qualification: the component bench currently supplies
probabilities and peer rows as stimuli and models the external controller.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def collect(paths: list[Path], size: int, kind: str) -> tuple[np.ndarray, list[dict]]:
    bits = np.zeros((16, size), dtype=np.uint32)
    seen = np.zeros((16, size), dtype=bool)
    receipts = []
    for path in paths:
        data = path.read_bytes()
        count, first, last = 0, None, None
        for lineno, line in enumerate(data.decode().splitlines(), 1):
            fields = line.split()
            if len(fields) != 5:
                raise ValueError(f'{path}:{lineno}: expected cycle index head bits flag')
            cycle, index, head = map(int, fields[:3])
            word, flag = int(fields[3], 16), int(fields[4])
            if cycle < 0 or not 0 <= index < size or not 0 <= head < 16 or not 0 <= word < 2**32:
                raise ValueError(f'{path}:{lineno}: invalid coordinate or FP32 word')
            if last is not None and cycle < last:
                raise ValueError(f'{path}:{lineno}: nonmonotonic pin cycle')
            if flag != 0:
                raise ValueError(f'{path}:{lineno}: hardware arithmetic fault {flag}')
            if seen[head, index]:
                raise ValueError(f'{path}:{lineno}: duplicated {kind}[{head},{index}]')
            seen[head, index] = True
            bits[head, index] = word
            count += 1
            first = cycle if first is None else first
            last = cycle
        receipts.append(dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(),
                             words=count, first_cycle=first, last_cycle=last))
    if not seen.all():
        missing = np.argwhere(~seen)
        raise ValueError(f'{kind}: {len(missing)} missing hardware words; first head,index={missing[0].tolist()}')
    return bits.view(np.float32), receipts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--traces', type=Path, nargs=4, required=True, metavar='STACK_DIR')
    ap.add_argument('--rows', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if not 1 <= a.rows <= 640:
        ap.error('--rows must be 1..640')
    scores, sr = collect([p/'scores.tsv' for p in a.traces], a.rows, 'scores')
    pv, pr = collect([p/'pv.tsv' for p in a.traces], 512, 'pv')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(a.out, s_raw=scores, pv=pv)
    manifest = dict(native_token_qualified=False, scope='actual SVC component output handoff',
                    substitutions=['component inputs q/peer_rows/probabilities', 'external PC controller model'],
                    rows=a.rows, heads=16, dimensions=512, scores=sr, pv=pr)
    a.out.with_suffix('.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(verdict='PASS', scope=manifest['scope'], native_token_qualified=False,
                          score_words=scores.size, pv_words=pv.size)))

if __name__ == '__main__':
    main()
