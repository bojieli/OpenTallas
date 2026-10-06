#!/usr/bin/env python3
"""Extract actual released L0/rank0 sectors for a32-PC boundary gate.

Stimulus only: this does not model a PHY or claim full-layer numerical credit.
Uses the already accepted exact E4M3 inverse, no new quantization.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
from fixture import fp8, ELEMENTS


def sector(pc, j):
    return ((j & 1) << 16) | ((pc >> 4) << 15) | ((j >> 1) << 6) | ((pc & 15) << 2)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--history', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    raw = args.history.read_bytes()
    if len(raw) != ELEMENTS * 4:
        raise ValueError('actual complete released L0/rank0 source required')
    rows = []
    for j in range(4):
        for pc in range(32):
            sec = sector(pc, j)
            payload = bytes(fp8(x[0]) for x in struct.iter_unpack('<I', raw[sec*128:(sec+1)*128]))
            rows.append(payload[::-1].hex())
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'gold.hex').write_text('\n'.join(rows)+'\n')
    record = dict(scope='released-sector stimulus only, no PHY/fulltoken verdict',
                  layer=0, rank=0, position_contract=8191, PCs=32,
                  sectors_each_PC=4, includes_K_and_V=True,
                  history_path=str(args.history),
                  history_sha256=hashlib.sha256(raw).hexdigest(),
                  gold_sha256=hashlib.sha256((args.output/'gold.hex').read_bytes()).hexdigest())
    (args.output/'source.json').write_text(json.dumps(record, indent=2)+'\n')
