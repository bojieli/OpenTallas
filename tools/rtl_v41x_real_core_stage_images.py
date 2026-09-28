#!/usr/bin/env python3
"""Deterministic 4-rank, 8-word V4.1x SU -> all-reduce -> SU microstage images."""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path
import hdc_isa_v41 as I

WORDS = 8
LANES = 16
IN_BASE, PRODUCED, REDUCED, CONSUMED = 0, 256, 512, 768

def bits(value: float) -> int:
    return struct.unpack('<I', struct.pack('<f', value))[0]

def line(elements: list[int]) -> str:
    return ''.join(f'{x:08x}' for x in reversed(elements))

def write_lines(path: Path, items: list[str]) -> str:
    path.write_text('\n'.join(items) + '\n')
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    init = [bits(float((j % 8) + 1)) for j in range(WORDS * LANES)]
    # Every rank's partial is finite and exactly representable in binary32.
    part = [[init[j] if rank == 0 else bits(float(rank)) for j in range(WORDS * LANES)]
            for rank in range(4)]
    expect = [bits(float((j % 8) + 7)) for j in range(WORDS * LANES)]
    consumed = [bits(float((j % 8) + 8)) for j in range(WORDS * LANES)]
    producer = I.encode(unit=I.UNIT_SU, su_nout=1, su_nin=WORDS * LANES,
                        a_base=IN_BASE, a_si=1, dst=I.DST_VM, o_base=PRODUCED, o_si=1,
                        su_vec=I.VEC_I)
    end = I.encode(unit=I.UNIT_END, wait=1 << (I.UNIT_SU - 1))
    prog = [producer, end]
    for k in range(WORDS):
        prog.append(I.encode(unit=I.UNIT_SU, su_nout=1, su_nin=LANES,
                             a_base=REDUCED + k * LANES, a_si=1, ad=I.AD_IMM,
                             imm2=bits(1.0), dst=I.DST_VM,
                             o_base=CONSUMED + k * LANES, o_si=1, su_vec=I.VEC_I))
        prog.append(end)
    assert len(prog) == 2 + 2 * WORDS
    manifest = {
        'schema': 'opentallas.rtl.v41x_real_core_stage_images.v1',
        'words': WORDS, 'lanes': LANES, 'ranks': 4,
        'addresses': {'input': IN_BASE, 'produced': PRODUCED, 'reduced': REDUCED, 'consumed': CONSUMED},
        'producer_entry': 0,
        'consumer_entries': [2 + 2 * k for k in range(WORDS)],
        'oracle': 'rank-order FP32 fold of real rank-0 values and synthetic rank-1/2/3 constants 1/2/3; consumer adds +1',
        'files': {},
    }
    manifest['files']['program.hex'] = write_lines(out / 'program.hex', [f'{p:0384x}' for p in prog])
    manifest['files']['init.hex'] = write_lines(out / 'init.hex', [f'{v:08x}' for v in init])
    manifest['files']['part.hex'] = write_lines(out / 'part.hex', [line(part[r][k*LANES:(k+1)*LANES])
                                                               for r in range(4) for k in range(WORDS)])
    manifest['files']['expect.hex'] = write_lines(out / 'expect.hex', [line(expect[k*LANES:(k+1)*LANES])
                                                                     for k in range(WORDS)])
    manifest['files']['consumed.hex'] = write_lines(out / 'consumed.hex', [f'{v:08x}' for v in consumed])
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return manifest

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    print(json.dumps(build(ap.parse_args().out), sort_keys=True))
