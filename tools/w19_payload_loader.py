#!/usr/bin/env python3
"""Default-off host loader for the unified-model V4.1 compact SM payload layout.

Input: existing golden issue-order 1088-bit records (128 weight bytes, then
8 UE8M0 bytes), already produced by the checkpoint/SM packer. No arithmetic or
row permutation occurs here. Output: addressed 32-byte readmemh sectors for a
single (expert, SM, operation) descriptor, padded only at its final 128-byte line.
This is a loader boundary, not a complete checkpoint loader or router runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path

RECORD_BYTES = 136
LINE_BYTES = 128
SECTOR_BYTES = 32
MAX_PAYLOADS = (65535 * LINE_BYTES) // RECORD_BYTES


def compact_sectors(records, payloads):
    """Stream with at most one record plus a residual sector buffered."""
    if not isinstance(payloads, int) or not 1 <= payloads <= MAX_PAYLOADS:
        raise ValueError('Payload count exceeds the existing 16-bit fetch descriptor')
    buffer = bytearray()
    count = 0
    emitted = 0
    for record in records:
        if count >= payloads:
            raise ValueError('Extra payload record')
        if len(record) != RECORD_BYTES:
            raise ValueError('Payload must contain exactly 136 bytes')
        buffer.extend(record)
        count += 1
        while len(buffer) >= SECTOR_BYTES:
            yield bytes(buffer[:SECTOR_BYTES])
            del buffer[:SECTOR_BYTES]
            emitted += 1
    if count != payloads:
        raise ValueError('Missing payload record')
    sectors = ((payloads * RECORD_BYTES + LINE_BYTES - 1) // LINE_BYTES) * 4
    while emitted < sectors:
        yield bytes(buffer) + bytes(SECTOR_BYTES - len(buffer))
        buffer.clear()
        emitted += 1


def logical_records(path):
    with Path(path).open() as source:
        for line in source:
            word = line.strip()
            if len(word) != RECORD_BYTES * 2 or any(c not in '0123456789abcdefABCDEF' for c in word):
                raise ValueError('Expected exactly 272 hex digits per logical SM record')
            yield int(word, 16).to_bytes(RECORD_BYTES, 'little')


def load_image(source, output, *, expected_sha256, payloads, expert_id, base_line=0,
               expert_stride_lines=None, sm_offset_lines=0, address_bits=24):
    """Write exclusively; failure removes only this call's incomplete output."""
    source, output = Path(source), Path(output)
    if not 0 <= expert_id < 384:
        raise ValueError('Expert ID outside the released V4.1 routed expert table')
    if address_bits != 24:
        raise ValueError('Only the existing model/fetch 24-bit sector port is supported')
    if not isinstance(payloads, int) or not 1 <= payloads <= MAX_PAYLOADS:
        raise ValueError('Invalid payload count')
    lines = (payloads * RECORD_BYTES + LINE_BYTES - 1) // LINE_BYTES
    stride = lines if expert_stride_lines is None else expert_stride_lines
    if any(not isinstance(v,int) or v < 0 for v in (base_line, stride, sm_offset_lines)):
        raise ValueError('Negative or noninteger layout field')
    if stride > 65535 or sm_offset_lines > 65535 or sm_offset_lines + lines > stride:
        raise ValueError('SM operation segment does not fit the existing expert stride/offset ports')
    first_sector = (base_line + expert_id * stride + sm_offset_lines) * 4
    if first_sector + lines * 4 > 1 << address_bits:
        raise ValueError('Descriptor exceeds the existing HBM sector address port')
    digest = hashlib.sha256()
    with source.open('rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != expected_sha256:
        raise ValueError('Logical payload source hash mismatch')
    created = False
    image_hash = hashlib.sha256()
    try:
        with output.open('x') as out:
            created = True
            header = f'@{first_sector:06x}\n'
            out.write(header); image_hash.update(header.encode())
            for sector in compact_sectors(logical_records(source), payloads):
                text = f'{int.from_bytes(sector,"little"):064x}\n'
                out.write(text); image_hash.update(text.encode())
        # Detect a source change between attestation and the streaming read.
        digest = hashlib.sha256()
        with source.open('rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                digest.update(chunk)
        if digest.hexdigest() != expected_sha256:
            raise ValueError('Logical payload source changed during loading')
    except BaseException:
        if created: output.unlink()
        raise
    return dict(schema='opentallas.w19.payload_loader.v1',format='v41_128B_weights_8B_UE8M0',
                source_sha256=expected_sha256,image_sha256=image_hash.hexdigest(),payloads=payloads,
                expert_id=expert_id,cfg_base=base_line,cfg_exp_lines=stride,cfg_off=sm_offset_lines,
                cfg_lines=lines,first_sector=first_sector,sector_count=lines*4,
                logical_bytes=payloads*RECORD_BYTES,physical_bytes=lines*LINE_BYTES,
                buffer_bytes_bound=RECORD_BYTES+SECTOR_BYTES-1,
                adoption=False,scope='One SM operation descriptor; checkpoint packing and router scheduling are prerequisites')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--enable',action='store_true',help='Explicit opt-in for candidate transport')
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--source-sha256',required=True)
    ap.add_argument('--payloads',type=int,required=True)
    ap.add_argument('--expert-id',type=int,required=True)
    ap.add_argument('--base-line',type=int,default=0)
    ap.add_argument('--expert-stride-lines',type=int)
    ap.add_argument('--sm-offset-lines',type=int,default=0)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--record',type=Path,required=True)
    a=ap.parse_args()
    if not a.enable: raise SystemExit('Candidate loader is off; --enable required')
    if a.record.exists(): raise SystemExit('Refusing to overwrite loader evidence')
    result=load_image(a.source,a.out,expected_sha256=a.source_sha256,payloads=a.payloads,
                      expert_id=a.expert_id,base_line=a.base_line,expert_stride_lines=a.expert_stride_lines,
                      sm_offset_lines=a.sm_offset_lines)
    with a.record.open('x') as f: f.write(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':
    main()
