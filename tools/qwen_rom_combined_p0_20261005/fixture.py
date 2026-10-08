#!/usr/bin/env python3
"""Derive numerical images from actual released L0/rank0 P8191 data only.

This is an expected-image generator, not an RTL result or a host memory service.
Canonical byte order: backing logical element order; slice tile/local/byte;
token K[head][dim], then V[head][dim]. Retain untouched slices as A5.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path

P=8191
ELEMENTS=4194304
FNV_OFFSET=14695981039346656037
FNV_PRIME=1099511628211


def fnv(data):
    h=FNV_OFFSET
    for c in data:
        h=((h^c)*FNV_PRIME)&0xffffffffffffffff
    return f'{h:016x}'


def fp8(bits):
    s,e,m=bits>>31,(bits>>23)&255,bits&0x7fffff
    if e==0 and m==0:return s<<7
    if 121<=e<=135 and not m&0xfffff:c=(s<<7)|((e-120)<<3)|(m>>20)
    elif e==120 and not m&0x1fffff:c=(s<<7)|4|(m>>21)
    elif e==119 and not m&0x3fffff:c=(s<<7)|2|(m>>22)
    elif e==118 and not m:c=(s<<7)|1
    else:raise ValueError('history is not exact released E4M3')
    if c&127==127:raise ValueError('nonfinite history')
    return c


def derive(history_path,token_path):
    raw=history_path.read_bytes()
    if len(raw)!=ELEMENTS*4:raise ValueError('released history extent differs')
    history=bytearray(fp8(bits) for bits, in struct.iter_unpack('<I',raw))
    token={}
    for line in token_path.read_text().splitlines():
        kind,h,d,c=line.split();h,d,c=int(h),int(d),int(c,16)
        key=(kind,h,d)
        if kind not in ('K','V') or not 0<=h<2 or not 0<=d<128 or not 0<=c<256 or c&127==127 or key in token:
            raise ValueError('invalid or duplicate actual token KV')
        token[key]=c
    if len(token)!=512:raise ValueError('incomplete actual token KV')
    backing=history.copy()
    for h in range(2):
        for d in range(128):
            backing[((h*512+P//16)*128+d)*16+P%16]=token['K',h,d]
            backing[2097152+(h*8192+P)*128+d]=token['V',h,d]
    slices=bytearray([0xa5])*(1536*128*64)
    for h in range(2):
        for t in range(512):
            for d in range(128):
                g=(t%48)*128+d
                dest=((g//4)*128+(t//48)*2+h)*64+(g%4)*16
                src=((h*512+t)*128+d)*16
                slices[dest:dest+16]=backing[src:src+16]
        for p in range(8192):
            for q in range(8):
                g=q*512+p%512
                dest=((g//4)*128+22+(p//512)*2+h)*64+(g%4)*16
                src=2097152+(h*8192+p)*128+q*16
                slices[dest:dest+16]=backing[src:src+16]
    canonical=bytes(token[k,h,d] for k in ('K','V') for h in range(2) for d in range(128))
    images={'history_fp8':history,'token_K_then_V':canonical,'backing_after_ACK':backing,'registered_slices':slices}
    return dict(scope='EXPECTED_RELEASED_NUMERICAL_IMAGES_ONLY_NOT_RTL_PASS',
        position=P,layer=0,rank=0,history_source_sha256=hashlib.sha256(raw).hexdigest(),
        token_source_sha256=hashlib.sha256(token_path.read_bytes()).hexdigest(),
        images={name:dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),fnv1a64=fnv(data)) for name,data in images.items()},
        expected_handshakes=dict(descriptor=1,GO=1,HCLK_descriptor=1,HCLK_GO=1,write_sectors=136,ACK=136,final_debt=0),
        RTL_core_cycles=None,RTL_controller_cycles=None)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history',type=Path,required=True);p.add_argument('--token',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--header',type=Path,required=True)
    a=p.parse_args();r=derive(a.history,a.token)
    with a.output.open('x') as f:f.write(json.dumps(r,indent=2)+'\n')
    with a.header.open('x') as f:
        f.write('// Generated from actual released L0/rank0 P8191 data by fixture.py.\n#pragma once\n#include <cstdint>\nnamespace qwen_combined_p0 {\n')
        for name,image in r['images'].items():f.write(f'inline constexpr uint64_t expected_{name}=0x{image["fnv1a64"]}ULL;\n')
        f.write('}\n')
    print(json.dumps(r))
