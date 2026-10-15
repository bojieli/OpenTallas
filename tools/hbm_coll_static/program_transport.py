"""Exact host F20 frame encoding for the actual1536b H-COLL issuer target."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def decode_issuer_cfg(commands: list[int]) -> dict[int, tuple[int, int]]:
    """Recover complete rows from native cfg37 without losing loop metadata."""
    words: dict[tuple[int, int], int] = {}
    metas: dict[int, int] = {}
    halves: dict[int, int] = {}
    selected = None
    fragments: list[int] = []
    for command in commands:
        if not 0 <= command < 1 << 37:
            raise ValueError('cfg command exceeds37bits')
        if not command >> 36:
            continue
        op, value = (command >> 32) & 15, command & 0xffffffff
        if op == 0:
            if fragments or value >> 8 or value >> 6 == 3:
                raise ValueError('invalid/incomplete issuer bank selection')
            selected = (value & 63, value >> 6)
        elif op == 1:
            if selected is None:
                raise ValueError('data without selected bank')
            fragments.append(value)
            if len(fragments) == 16:
                if selected in words:
                    raise ValueError('conflicting/repeated completed bank')
                words[selected] = sum(v << (32*i) for i, v in enumerate(fragments))
                fragments.clear()
        elif op in (2, 3):
            if selected is None or fragments or (op == 3 and value >> 19):
                raise ValueError('invalid issuer metadata')
            row = selected[0]
            bit = 1 << (op-2)
            if halves.get(row, 0) & bit:
                raise ValueError('conflicting/repeated metadata')
            metas[row] = metas.get(row, 0) | value << (32*(op-2))
            halves[row] = halves.get(row, 0) | bit
        else:
            raise ValueError('unsupported issuer command')
    if fragments:
        raise ValueError('incomplete issuer bank')
    rows = {r for r, _ in words} | set(metas)
    result = {}
    for row in sorted(rows):
        if halves.get(row) != 3 or any((row, b) not in words for b in range(3)):
            raise ValueError(f'incomplete row{row}')
        result[row] = (sum(words[row, b] << (512*b) for b in range(3)), metas[row])
    return result


def encode_program(rows: dict[int, tuple[int, int]], qid: int, base: int, limit: int) -> dict:
    if qid not in range(4) or not 0 <= base < limit <= 64:
        raise ValueError('qid/descriptor range invalid')
    if any(r not in rows for r in range(base, limit)):
        raise ValueError('descriptor includes incomplete row')
    for row in range(base, limit):
        meta = rows[row][1]
        halt = (meta >> 44) & 1
        next_pc, target_pc, count = meta & 63, (meta >> 6) & 63, (meta >> 12) & 0xffffffff
        if (row == limit-1 and not halt) or (not halt and
                (not base <= next_pc < limit or (count and not base <= target_pc < limit))):
            raise ValueError(f'row{row} metadata escapes descriptor or lastrow lacks halt')
    frames = []
    for row, (uop, meta) in sorted(rows.items()):
        if row not in range(64) or not 0 <= uop < 1 << 1536 or not 0 <= meta < 1 << 51:
            raise ValueError('row/instruction/metadata width invalid')
        for segment in range(7):
            word = meta if segment == 6 else (uop >> (256*segment)) & ((1 << 256)-1)
            frames.append({'target':52+qid, 'address':row*8+segment,
                           'data_hex':f'{word:064x}',
                           'next_frame_gap_edges':55 if segment == 6 else 1})
    # F24 increments the frame address. Segment7 is reserved, so F20 selects
    # each next row explicitly instead of silently streaming through address7.
    csr = []
    for row in sorted(rows):
        csr.append({'op':'write32','address_hex':'f20','data_hex':f'{(row*8<<8)|(52+qid):08x}'})
        for frame in (f for f in frames if f['address']//8 == row):
            word = int(frame['data_hex'],16)
            for piece in range(8):
                csr.append({'op':'write32','address_hex':'f24','data_hex':f'{(word>>(piece*32))&0xffffffff:08x}'})
        csr.append({'op':'idle_core_edges','edges':55,'anchor':'after acknowledgement of the final F24 write for this row'})
    csr.extend([
        {'op':'write32','address_hex':'f28','data_hex':f'{(limit<<12)|base:08x}'},
        {'op':'write32','address_hex':'f2c','data_hex':'00000001'},
        {'op':'idle_core_edges','edges':66,'anchor':'after acknowledgement of F2C descriptor write'},
    ])
    return {'abi':'hcoll-f20-1536-v1', 'descriptor_units':'instructions',
            'frames':frames, 'csr_programming_plan':csr,
            'global_launch_doorbell':{'address_hex':'c10','data_hex':'00000001','prerequisite':'caller must also configure all VM and engine targets participating in this kernel'},
            'descriptor':{'target':52+qid,'base':base,'limit':limit,'loops':1},
            'descriptor_to_launch_gap_edges':66,
            'launch':'global launch at least66edges after descriptor capture, after fixed64row validation',
            'runtime_loop_count_source':'native64b metadata, not descriptorloops'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--cfg', type=Path, required=True, help='one hexadecimal cfg37 command perline')
    ap.add_argument('--qid', type=int, required=True)
    ap.add_argument('--base', type=int, default=0)
    ap.add_argument('--limit', type=int, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    commands = [int(line.strip(), 16) for line in args.cfg.read_text().splitlines() if line.strip()]
    args.out.write_text(json.dumps(encode_program(decode_issuer_cfg(commands),args.qid,args.base,args.limit),indent=2)+'\n')


if __name__ == '__main__':
    main()
