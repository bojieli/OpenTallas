#!/usr/bin/env python3
"""Encode an explicitly scheduled SFU control image; no runtime scheduling.

Input is an object with `cycles` and `rows`: each row has an absolute `cycle`
and a partial `fields` mapping. Unspecified fields are zero on that edge;
there is no persistent/implicit state. All arithmetic stage controls must be
provided at their actual compiler-assigned edges. This tool only encodes and
validates that fixed schedule. It does not lower high-level SFU instructions.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

# In concatenation order, exactly matching ot_hgi_sfu_arithmetic_grid.control.
FIELDS = (
    ('ld', 1), ('ld_bank', 1), ('ld_c', 1200), ('emit', 1), ('bank', 1),
    ('o_v', 24), ('i_v', 24), ('no', 24), ('ni', 24), ('ls', 4), ('lvw', 4),
    ('vb', 120), ('krow', 24), ('obase', 24), ('aibase', 24), ('aind', 2),
    ('gsh', 5), ('cpair', 1), ('dst', 2), ('srcs', 8),
    ('cx_arnd', 1), ('cx_arelu', 1), ('cx_amin', 1), ('cx_cclip', 1),
    ('cx_imm3', 32), ('cp_m1', 3), ('cp_imm1', 32), ('cm_m1', 3),
    ('cm_m2', 2), ('cm_qm', 3), ('cm_imm1', 32), ('ca_ad', 3),
    ('ca_imm2', 32), ('ci_sfu', 3), ('cs_sfu', 3), ('cs_e1', 3),
    ('cs_imm2', 32), ('ce_e2', 2), ('ce_imm1', 32), ('co_rnd', 1), ('co_dst', 2),
)
WIDTH = sum(width for _, width in FIELDS)
assert WIDTH == 1742


def pack(fields: dict[str, int]) -> int:
    unknown = fields.keys() - dict(FIELDS).keys()
    if unknown:
        raise ValueError(f'unknown fields: {sorted(unknown)}')
    word = 0
    for name, width in FIELDS:
        value = fields.get(name, 0)
        if not isinstance(value, int) or value < 0 or value >= 1 << width:
            raise ValueError(f'{name}: value {value!r} does not fit unsigned {width} bits')
        word = word << width | value
    return word


def unpack(word: int) -> dict[str, int]:
    if not 0 <= word < 1 << WIDTH:
        raise ValueError('control word outside ABI width')
    out = {}
    for name, width in reversed(FIELDS):
        out[name] = word & ((1 << width) - 1)
        word >>= width
    return {name: out[name] for name, _ in FIELDS}


def encode(schedule: dict) -> list[int]:
    cycles = schedule['cycles']
    if not isinstance(cycles, int) or cycles <= 0:
        raise ValueError('cycles must be a positive integer')
    words = [0] * cycles
    occupied = set()
    for row in schedule['rows']:
        edge = row['cycle']
        if not isinstance(edge, int) or not 0 <= edge < cycles or edge in occupied:
            raise ValueError(f'invalid/duplicate scheduled edge {edge!r}')
        occupied.add(edge)
        words[edge] = pack(row['fields'])
    return words


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schedule', type=Path)
    parser.add_argument('image', type=Path)
    args = parser.parse_args()
    words = encode(json.loads(args.schedule.read_text()))
    payload = ''.join(f'{word:0436x}\n' for word in words)
    args.image.write_text(payload)
    root = Path(__file__).resolve().parents[2]
    sources = [Path('rtl/hbm_accel/generic/peers/ot_hgi_sfu_static_quarter.sv'),
               Path('rtl/hbm_accel/generic/peers/ot_hgi_sfu_arithmetic_grid.sv')]
    receipt = dict(width=WIDTH, cycles=len(words),
                   sha256=hashlib.sha256(payload.encode()).hexdigest(),
                   source_sha256={str(p): hashlib.sha256((root / p).read_bytes()).hexdigest() for p in sources},
                   instruction_lowering=False, production_calendar_qualification=False)
    args.image.with_suffix(args.image.suffix + '.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
