#!/usr/bin/env python3
"""Pack existing canonical INT8 codes/BF16 scale bits for opt-in r25 fmt3.

No quantization, norm folding, scale arithmetic or checkpoint loading occurs.
Codes/scales are already selected TP4 data. Weight lines are 1088-bit bulk-copy
responses (128 code bytes plus eight zero sidecar bytes); optional storage
stride is explicit and is not a guessed installed address mapping.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import numpy as np

@dataclass(frozen=True)
class Geometry:
    rows: int
    k: int
    il: int = 8
    c: int = 8
    lanes: int = 64
    group_slot: bool = True

    def __post_init__(self):
        if not 1 <= self.rows <= 4096 or self.k <= 0 or self.k % 64:
            raise ValueError('production rows 1..4096 and K divisible by 64 required')
        if (self.il, self.c, self.lanes) != (8, 8, 64):
            raise ValueError('production IL8/C8/64 BF16 lanes required')
        if self.groups > 16 or self.groups * self.c > 128:
            raise ValueError('group stack/x-store capacity exceeded')

    @property
    def groups(self):
        return (self.k + self.c * self.lanes - 1) // (self.c * self.lanes)

    @property
    def beats(self):
        return self.rows * self.groups * self.c

    @property
    def lines(self):
        return self.beats // 2

    def issuer(self):
        if self.group_slot:
            for base in range(0, self.rows * self.groups, self.il):
                for t in range(self.c):
                    for item in range(base, min(base + self.il, self.rows * self.groups)):
                        row, group = divmod(item, self.groups)
                        yield row, group, t
        else:
            for base in range(0, self.rows, self.il):
                for group in range(self.groups):
                    for t in range(self.c):
                        for row in range(base, min(base + self.il, self.rows)):
                            yield row, group, t

    def columns(self, group, t):
        # Matches literal tools/dshbm_matched_sm_seq.py gen_op BF16 mapping.
        return (group * self.lanes + np.arange(self.lanes)) * self.c + t


def pack_lines(codes, geometry):
    if codes.dtype != np.int8 or codes.shape != (geometry.rows, geometry.k):
        raise ValueError('canonical signed INT8 matrix geometry mismatch')
    first = None
    for row, group, t in geometry.issuer():
        cols = geometry.columns(group, t)
        beat = np.zeros(geometry.lanes, dtype=np.int8)
        valid = cols < geometry.k
        beat[valid] = codes[row, cols[valid]]
        raw = beat.tobytes()
        if first is None:
            first = raw
        else:
            yield first + raw + bytes(8)
            first = None
    if first is not None:
        raise ValueError('unpaired issue beat')


def unpack_lines(lines, geometry):
    result = np.zeros((geometry.rows, geometry.k), dtype=np.int8)
    order = iter(geometry.issuer())
    count = 0
    for line in lines:
        if len(line) != 136 or any(line[128:]):
            raise ValueError('bad response width or nonzero fmt3 sidecar')
        for offset in (0, 64):
            try:
                row, group, t = next(order)
            except StopIteration as error:
                raise ValueError('extra packed line') from error
            cols = geometry.columns(group, t)
            valid = cols < geometry.k
            beat = np.frombuffer(line[offset:offset+64], dtype=np.int8)
            if np.any(beat[~valid]):
                raise ValueError('nonzero padded weight')
            result[row, cols[valid]] = beat[valid]
        count += 1
    if count != geometry.lines:
        raise ValueError('truncated packed image')
    return result


def qwen_tp4_shapes(sms=32):
    # Dimensions from PLAN section 3; NC=8 are activation columns, not rows.
    full = dict(q=(1024,4096), k=(256,4096), v=(256,4096), o=(4096,1024),
                gate=(3072,4096), up=(3072,4096), down=(4096,3072), head=(37984,4096))
    answer = {}
    for name, (rows,k) in full.items():
        if rows % sms:
            raise ValueError('chosen contiguous equal SM split must divide rows')
        g = Geometry(rows//sms,k)
        answer[name] = dict(tp=4, sm_replicas=sms, die_rows=rows, k=k,
            rows_per_sm=g.rows, groups=g.groups, c=g.c, group_slot=True,
            bf16_issue_beats_per_sm=g.beats, packed_lines_per_sm=g.lines,
            useful_code_bytes_per_die=rows*k,
            response_bytes_per_die=g.lines*136*sms,
            row_scale_bytes_per_die=2*rows, nc=8,
            nc_contract='independent activation columns sharing each weight line',
            x_addresses_per_sm=g.groups*g.c)
    return answer


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20), b''): h.update(chunk)
    return h.hexdigest()


def emit(codes_path, scales_path, out, sm, sms=32, stride=136):
    codes=np.load(codes_path,mmap_mode='r'); scales=np.load(scales_path,mmap_mode='r')
    if codes.ndim!=2 or codes.dtype!=np.int8 or scales.dtype!=np.uint16 or scales.shape!=(codes.shape[0],):
        raise ValueError('signed INT8 codes and opaque uint16 BF16 row-scale bits required')
    if not 0<=sm<sms or codes.shape[0]%sms or stride<136 or stride%8:
        raise ValueError('equal contiguous SM split and explicit >=136-byte aligned stride required')
    rows=codes.shape[0]//sms; lo=sm*rows; hi=lo+rows; geometry=Geometry(rows,codes.shape[1])
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    packed=out/'weights.bin'
    with packed.open('wb') as f:
        for line in pack_lines(codes[lo:hi],geometry): f.write(line+bytes(stride-136))
    scale_path=out/'row_scales_bf16.bin'
    scale_path.write_bytes(scales[lo:hi].astype('<u2',copy=False).tobytes())
    manifest=dict(schema='opentallas.qwen.r25.fmt3.image.v1',geometry=asdict(geometry),
        sm=sm,sms=sms,canonical_rows=[lo,hi],op_rows=rows,op_c=8,op_g=geometry.groups,
        op_gs=1,op_fmt=3,bulk_copy_lines=geometry.lines,response_bytes=136,storage_stride_bytes=stride,
        storage_base=None,linked_entry_pc=None,host_installation='caller must bind existing service address mapping',
        scale_contract='unchanged BF16 scale per output row; SU multiply after FP32 sum',
        source_sha256={'codes':sha(codes_path),'scales':sha(scales_path),'producer':sha(__file__)},
        output_sha256={'weights':sha(packed),'scales':sha(scale_path)})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--codes',type=Path,required=True)
    p.add_argument('--scales',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--sm',type=int,required=True);p.add_argument('--sms',type=int,default=32)
    p.add_argument('--stride',type=int,default=136)
    a=p.parse_args();print(json.dumps(emit(a.codes,a.scales,a.out,a.sm,a.sms,a.stride),indent=2))
if __name__=='__main__':main()
