#!/usr/bin/env python3
"""Source decoder expectations, never directly observed accepted raw words."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

KEYS = ['su_nout', 'su_nin', 'dst', 'red', 'ma', 'mb', 'sfu', 'ad', 'a_src', 'b_src',
        'c_src', 'mc', 'md', 'red_sq', 'imm1', 'imm2', 'a_base', 'a_so', 'a_si',
        'b_base', 'b_so', 'b_si', 'c_base', 'c_so', 'c_si', 'd_base', 'd_so', 'd_si',
        'r_base', 'r_so']

def generate(tools, program, output, position=255):
    os.environ['HDC_SU_WIDTH'] = '64'
    sys.path.insert(0, str(tools))
    import hdc_isa as isa
    # Fixed actual fullshape geometry, independently taken from the admitted
    # core parameters: HID4096 / HALF64 / HD128 / W16 / G3072; token0.
    dynamic = [0, 0, position * 64, (position // 16) * 128 * 16 + position % 16,
               position * 128, position + 1, position // (16 * 3072) + 1, 0]
    ranks = {}
    for rank in range(8):
        path = program / f'die{rank}' / 'program.hex'
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != 'cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796':
            raise ValueError('resolved decoder catalog requires exact actual 25-word image')
        fields = {}
        for pc, word in enumerate(raw.decode().split()):
            f = isa.decode(int(word, 16))
            if f['unit'] != isa.UNIT_SU:
                continue
            f['su_nin'] += dynamic[f['su_d_nin']]
            for operand in ('a', 'b', 'c', 'd'):
                f[f'{operand}_base'] += dynamic[f[f'{operand}_d']]
            fields[str(pc)] = {key: f[key] for key in KEYS}
        ranks[str(rank)] = {'program_sha256': digest, 'resolved_SU_fields': fields}
    report = {'scope': 'SOURCE_DECODED_RESOLVED_FIELDS_NOT_ACCEPTED_RAW_IB', 'keys': KEYS,
              'position': position, 'dynamic': dynamic, 'ranks': ranks,
              'decoder_sha256': hashlib.sha256((tools / 'hdc_isa.py').read_bytes()).hexdigest()}
    output.write_text(json.dumps(report, indent=2) + '\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tools', type=Path, required=True)
    p.add_argument('--program', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    generate(a.tools, a.program, a.out)
