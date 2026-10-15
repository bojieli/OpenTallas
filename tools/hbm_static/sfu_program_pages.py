#!/usr/bin/env python3
"""Encode real paged SFU programme planes, including global PC protection.

The raw engine ABI remains1742 bits. This format is distinct from the old
1024-word VM calendar: protected PC width is11/12 and payload stripes222/221.
The host must use its wide F20/F28 target format; truncation is refused.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from sfu_control_image import WIDTH, encode


def encode_planes(words: list[int], page_aw: int=1) -> dict:
    if page_aw not in (1,2):
        raise ValueError('PAGE_AW must select actual two/four-page SRAM geometry')
    aw=10+page_aw
    chunk=223-page_aw
    widths=[chunk]*7+[WIDTH-7*chunk]
    if not words or len(words)>1<<aw:
        raise ValueError(f'programme length must fit the actual {1<<aw} rows')
    planes=[[] for _ in widths]
    for pc,word in enumerate(words):
        if not isinstance(word,int) or not 0<=word<1<<WIDTH:
            raise ValueError('raw control word exceeds the actual ABI')
        for stripe,width in enumerate(widths):
            payload=word>>(chunk*stripe)&((1<<width)-1)
            planes[stripe].append((0xc7a1<<240)|(pc<<(234-aw))|payload)
    return dict(page_aw=page_aw,pc_width=aw,payload_widths=widths,
                instructions=len(words),real_1024x256_SRAMs=8*(1<<page_aw),planes=planes)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('schedule',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--page-aw',type=int,choices=(1,2),default=1)
    args=parser.parse_args()
    result=encode_planes(encode(json.loads(args.schedule.read_text())),args.page_aw)
    args.out.mkdir(parents=True,exist_ok=True)
    hashes={}
    for stripe,words in enumerate(result.pop('planes')):
        payload=''.join(f'{word:064x}\n' for word in words)
        name=f'plane{stripe}.hex'
        (args.out/name).write_text(payload)
        hashes[name]=hashlib.sha256(payload.encode()).hexdigest()
    result.update(plane_sha256=hashes,host_address_bits=result['pc_width'],
                  target_namespace='80+8*quadrant+stripe',layer_qualified=False)
    (args.out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
