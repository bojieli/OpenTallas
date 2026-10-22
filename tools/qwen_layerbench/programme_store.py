#!/usr/bin/env python3
"""Finite four-user, 36-layer table-ROM layout; no default RTL adoption.

This consumes already lowered, bit-exact per-user PROG payloads. It never
rewrites arithmetic or guesses which SU address fields name a user bank.
Input stages contain prog_users[4][6], btab[<=18], crom[<=64] records;
each record is {addr, payload_hex}. PROG addr is a pair index, CROM addr
is a 16-pair row, BTAB addr is a four-word aligned word index. Empty
slots are invalid ROM words, not valid zero table writes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

STAGES, USERS, SLICES = 36, 4, 12
DEPTH, WIDTH, LANES, MUX = 4096, 266, 4, 8
PROG, BTAB, CROM = 6, 18, 64
STRIDE = USERS * PROG + BTAB + CROM
USER_STRIDE = {1: 128, 2: 128, 3: 64}  # source0d4c PIDX_STRIDE128 => 64 instruction pairs
BTAB_COUNTS = (18,16,18,16,18,16,18,16,14,12,14,12)
CROM_COUNTS = (64,)*8 + (48,)*4


def encode(kind, addr, payload_hex):
    if kind not in USER_STRIDE or not isinstance(addr, int) or addr < 0:
        raise ValueError('invalid kind/address')
    if addr >= USER_STRIDE[kind] or (kind == 2 and addr % 4):
        raise ValueError('local table address exceeds user partition')
    payload = int(payload_hex, 16)
    if not 0 <= payload < 1 << 1024:
        raise ValueError('payload exceeds 1024 bits')
    if kind == 3 and payload & (((1 << 55)-1) << 457 | ((1 << 55)-1) << 969):
        raise ValueError('PROG instruction padding must be zero')
    return payload | (1 << 1024) | (kind << 1025) | (addr << 1027)


def relocate_word(word, user, pidx_stride=128):
    """Only the write address changes; all 1024 payload bits are preserved."""
    if user not in range(USERS):
        raise ValueError('invalid user')
    if pidx_stride not in (64,128):
        raise ValueError('unqualified PROG user stride')
    if not (word >> 1024) & 1:
        return 0
    kind, addr = (word >> 1025) & 3, word >> 1027
    if kind not in USER_STRIDE or addr >= USER_STRIDE[kind]:
        raise ValueError('invalid local ROM record')
    stride = pidx_stride//2 if kind == 3 else USER_STRIDE[kind]
    if addr >= stride:
        raise ValueError('local PROG address crosses user partition')
    return (word & ((1 << 1027) - 1)) | ((addr + user * stride) << 1027)


def read_rows(stage, user):
    """Fixed 88 reads per layer/user. Selection needs no readiness decision."""
    if stage not in range(1, STAGES + 1) or user not in range(USERS):
        raise ValueError('stage/user outside finite store')
    base = (stage - 1) * STRIDE
    return (list(range(base + user * PROG, base + (user + 1) * PROG)) +
            list(range(base + USERS * PROG, base + STRIDE)))


def logical_images(manifest):
    if manifest.get('schema') != 'opentallas.qwen.mu-table-input.v1':
        raise ValueError('wrong manifest schema')
    if manifest.get('parameters') != dict(NU=4,PIDX_STRIDE=128,CROM_ROW_STRIDE=128,BTAB_WORD_STRIDE=128):
        raise ValueError('exact production table ABI parameters required')
    # An arbitrary descriptive string is not accepted as checkpoint provenance.
    for key in ('lowering_commit', 'checkpoint_sha256', 'user_relocation_certificate_sha256'):
        val = manifest.get('source', {}).get(key, '')
        if not isinstance(val, str) or len(val) != (40 if key.endswith('commit') else 64):
            raise ValueError('source provenance missing: ' + key)
        int(val, 16)
    stages = manifest['stages']
    if sorted(s['stage'] for s in stages) != list(range(1, STAGES + 1)):
        raise ValueError('exactly 36 distinct stages required')
    images = [[0] * DEPTH for _ in range(SLICES)]
    for st in stages:
        if sorted(s['slice'] for s in st['slices']) != list(range(SLICES)):
            raise ValueError('exactly 12 distinct slices required')
        base = (st['stage'] - 1) * STRIDE
        for sl in st['slices']:
            pu = sl['prog_users']
            if len(pu) != USERS:
                raise ValueError('four already-relocated PROG images required')
            if any(len(records) != PROG for records in pu):
                raise ValueError('six PROG records per production user required')
            if len(sl['btab']) != BTAB_COUNTS[sl['slice']] or len(sl['crom']) != CROM_COUNTS[sl['slice']]:
                raise ValueError('production table family shape does not match slice ownership')
            groups = [(3, i * PROG, PROG, pu[i]) for i in range(USERS)]
            groups += [(2, USERS * PROG, BTAB, sl['btab']),
                       (1, USERS * PROG + BTAB, CROM, sl['crom'])]
            for kind, start, cap, records in groups:
                if len(records) > cap:
                    raise ValueError('table family exceeds finite reservation')
                seen = set()
                for i, rec in enumerate(records):
                    if rec['addr'] in seen:
                        raise ValueError('duplicate table address')
                    seen.add(rec['addr'])
                    images[sl['slice']][base + start + i] = encode(kind, rec['addr'], rec['payload_hex'])
    return images


def physical_rows(words, lane):
    """Actual macro via-mask mapping: arr[row][io*8+column]."""
    if len(words) != DEPTH or lane not in range(LANES):
        raise ValueError('wrong physical macro shape')
    out = [0] * (DEPTH // MUX)
    for a, w in enumerate(words):
        part = (w >> (lane * WIDTH)) & ((1 << WIDTH) - 1)
        for bit in range(WIDTH):
            if (part >> bit) & 1:
                out[a // MUX] |= 1 << (bit * MUX + a % MUX)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    images = logical_images(json.loads(a.manifest.read_text()))
    a.out.mkdir(parents=True, exist_ok=True)
    receipt = dict(schema='opentallas.qwen.mu-table-rom.v1',
                   qualification='PACKING ONLY; native execution and physical closure OPEN',
                   manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
                   used_rows=STAGES * STRIDE, fixed_reads_per_layer=88, images={})
    for s, words in enumerate(images):
        for lane in range(LANES):
            name = f'table_s{s}_m{lane}.viamap.hex'
            data = ''.join(f'{r:0532x}\n' for r in physical_rows(words, lane))
            (a.out / name).write_text(data)
            receipt['images'][name] = hashlib.sha256(data.encode()).hexdigest()
    (a.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    main()
