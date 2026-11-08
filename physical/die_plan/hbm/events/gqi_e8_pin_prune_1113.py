#!/usr/bin/env python3
"""Private physical pin projection onto the existing signed GQI exponent-byte shell.

The four high exponent inputs do not affect any result: the sole use is the
low byte of exponent+bias. The existing signed shell already has 8-bit ports
and zero-pads the two internal high bits. See codex/hbm-gqi-e8-1113@33114d8b04f.
No RTL, view, latency, route or source bus width changes. Run a private bind/GEN
and count dry after overlaying this output into all four GQI plan instances.
Usage: gqi_e8_pin_prune_1113.py INPUT_PINS OUTPUT_PINS RECEIPT
"""
import hashlib
import json
import sys
from pathlib import Path

DROP = {'aq0_e[8]', 'aq0_e[9]', 'aq1_e[8]', 'aq1_e[9]'}

def apply(pins):
    names = [p['name'] for p in pins]
    present = DROP.intersection(names)
    if present and (present != DROP or any(names.count(n) != 1 for n in DROP)):
        raise ValueError('expected exactly the four proved unused exponent pins')
    for bus in ('aq0_e', 'aq1_e'):
        if any(f'{bus}[{i}]' not in names for i in range(8)):
            raise ValueError('all eight functional exponent bits must remain')
    return [p for p in pins if p['name'] not in DROP]

def main(argv):
    src,dst,receipt=map(Path,argv)
    if src.resolve()==dst.resolve() or dst.exists() or receipt.exists():
        raise ValueError('fresh private outputs only; retain original pins and evidence')
    data=src.read_bytes();old=json.loads(data);new=apply(old)
    out=(json.dumps(new,indent=1)+'\n').encode()
    dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(out)
    receipt.write_text(json.dumps(dict(event='GQI-E8-PINS-1113',removed=sorted(DROP),
        input_pins=len(old),output_pins=len(new),pin_cycles=0,
        input_sha256=hashlib.sha256(data).hexdigest(),output_sha256=hashlib.sha256(out).hexdigest(),
        source_proof='codex/hbm-gqi-e8-1113@33114d8b04f75e4f84e7b42b2f17c5f6f773be29',
        projection={b:list(range(8)) for b in ('aq0_e','aq1_e')},
        note='Only physical pin metadata; source bus bits remain. Actual signed native shell and all other pin shapes are unchanged; no POR adoption'),indent=1)+'\n')
    return 0

if __name__=='__main__':
    raise SystemExit(main(sys.argv[1:]))
