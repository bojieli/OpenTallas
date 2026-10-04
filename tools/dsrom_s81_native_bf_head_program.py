#!/usr/bin/env python3
"""Control/address packing for the retained native BF pair; no FP arithmetic."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

K = 5120
ROWS = 32320

def phase(grain: int) -> dict:
    if type(grain) is not int or grain not in (0, 1):
        raise ValueError('head grain must be 4096 or 1024 ordinal')
    u0, nu = ((0, 32), (32, 8))[grain]
    cfg = [0] * 25
    # Literal W17/W10 packing: local row0 / row1, one complete return segment.
    # EARLY=1 preserves subtree depth. Padding is in native carried merge ONLY.
    cfg[0] = (1 << 21) | (1 << 42)
    cfg[8] = 1 | (u0 << 1) | (nu << 9) | (1 << 22)
    cfg[16] = (nu + 7) // 8 - 1
    cfg[17] = 1
    stream = []
    for q in range((nu + 7) // 8):
        units = list(range(u0 + 8*q, min(u0+nu, u0+8*q+8)))
        groups = [units[i:i+4] for i in range(0, len(units), 4)]
        # Exact FAST W17 scheduling: LAT8 recurrence, one word/edge PB port.
        rl = max(8, len(groups)+1, len(units))
        for b in range(8):
            slots = [0]*rl
            for i, group in enumerate(groups):
                word = 1 | (b << 1)
                for j, unit in enumerate(group):
                    word |= (1 << (4+j)) | (unit << (8+8*j))
                slots[(i*(rl-1))//len(groups)] = word
            stream.extend(slots)
    # Format1 for both local row tags: actual returned FP32, no BF16 round.
    phrom = [1 | (K << 1) | (len(stream) << 14) | (2 << 46) | (3 << 62), 0]
    return {'grain': grain, 'elements': nu*128, 'u0': u0, 'units': nu,
            'cfg': cfg, 'phrom': phrom, 'stream': stream,
            'rom_words_per_macro': nu*8, 'local_rows': [0, 1]}

def address(grain: int, address: int) -> tuple[int, int]:
    p = phase(grain)
    if type(address) is not int or not 0 <= address < p['rom_words_per_macro']:
        raise ValueError('native head read outside accepted grain')
    q, tail = divmod(address, 64)
    b, j = divmod(tail, 8)
    return p['u0'] + 8*q + j, b

def generate(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    phases = [phase(0), phase(1)]
    (output/'cfg.hex').write_text(''.join(f'{w:012x}\n' for p in phases for w in p['cfg']))
    for p in phases:
        (output/f"stream_{p['grain']}.hex").write_text(''.join(f'{w:012x}\n' for w in p['stream']))
    model = {'schema':'dsrom.s81.native_bf_head_program.v1', 'phases':phases,
             'rank_rows': ROWS, 'ranks':4, 'xn_source_words':K,
             'source_snapshot_bytes':K*4, 'weight_raw_reads_per_native_word':8,
             'weight_raw_bytes_per_native_word':256, 'native_word_bits':274,
             'macs_per_rank':ROWS*K, 'native_words_per_rank_macro_pair':(ROWS//2)*320,
             'arithmetic':'retained PB BF multiply/chunk8/ordered tree EARLY1; actual return nseg1; carried B+0+0 then A+B',
             'producer_roots':'two FP32 roots per output row; never host addition',
             'physical_latency_qualified':False, 'provider_bandwidth_qualified':False}
    (output/'program.json').write_text(json.dumps(model, indent=2)+'\n')
    return model



def prepare_host(source: Path, output: Path) -> None:
    """Copy current main's actual pair-source host byte-exact; do not patch it."""
    text=source.read_text()
    for needle in ('void dsrom_s81_minimum::bind_native_pair_source(',
                   'owner.source_rom(binding.second,unsigned(address))',
                   'owner.source_cfg(unsigned(address))'):
        if text.count(needle)!=1:
            raise ValueError('current concrete native pair host dependency absent: '+needle)
    output.write_bytes(source.read_bytes())

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--host-source',type=Path)
    args=parser.parse_args()
    generate(args.output)
    if args.host_source:
        prepare_host(args.host_source,args.output/'s81_minimum_head_element.cpp')
