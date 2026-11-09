#!/usr/bin/env python3
"""Private HCOL-H1 clock-pin metadata correction to its unchanged signed LEF.

No timing, RTL, physical view or clock latency changes. The plan pin file's
clk_pair[0] centre is 48 nm west of the signed native M5 rectangle centre.
Usage: hcol_h1_clkpin_1113.py INPUT_PINS OUTPUT_PINS RECEIPT
Apply the output only in a private plan overlay before a fresh GEN dry.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

SIGNED_LEF_SHA256 = 'dc71009de0928876c0b46498e151178a91436795f84c1443f2c8f5658ba12192'

def apply(rows):
    out = copy.deepcopy(rows)
    selected = [p for p in out if p.get('name') == 'clk_pair[0]']
    if len(selected) != 1:
        raise ValueError('expected exactly one native clk_pair[0]')
    p = selected[0]
    if p.get('layer') != 'M5' or p.get('y') != 95.04 or p.get('x') not in (107.928, 107.976):
        raise ValueError('native HCOL-H1 geometry differs from the measured signed view')
    p['x'] = 107.976
    return out

def main(argv):
    src, dst, receipt = map(Path, argv)
    if src.resolve() == dst.resolve() or dst.exists() or receipt.exists():
        raise ValueError('write fresh private outputs; preserve the input and prior receipts')
    raw = src.read_bytes(); rows = json.loads(raw); new = apply(rows)
    data = (json.dumps(new, indent=1) + '\n').encode()
    dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(data)
    receipt.write_text(json.dumps(dict(event='HCOL-H1-CLKPIN-1113', pin='clk_pair[0]',
        old_xy=[107.928,95.04], actual_signed_xy=[107.976,95.04], layer='M5',
        input_sha256=hashlib.sha256(raw).hexdigest(), output_sha256=hashlib.sha256(data).hexdigest(),
        signed_lef_sha256=SIGNED_LEF_SHA256, pin_cycles=0,
        note='Metadata only; signed LEF, source clocks, latency and other pins unchanged; private overlay, no POR adoption'), indent=1)+'\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
