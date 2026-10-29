#!/usr/bin/env python3
"""Encode explicit regular VM regions into existing target78 boot frames.

Regions are real uint32 payloads, not pointer promises. Roles/replicas must be
supplied by the caller; no replication, mirror substitution or numeric casting.
"""
import argparse,json
from pathlib import Path

def compile_regions(regions):
    frames=[];occupied=set();words=0
    for region in regions:
        addr=region['word_address'];data=region['words']
        if type(addr)is not int or addr<0 or addr%8 or not data or len(data)%8 or addr+len(data)>1<<19:raise ValueError('aligned bounded19bit word region required')
        if any(type(x)is not int or not 0<=x<1<<32 for x in data):raise ValueError('payload must be exact uint32 bitpatterns')
        slots=set(range(addr,addr+len(data)))
        if occupied&slots:raise ValueError('overlapping explicit publication regions')
        occupied|=slots;words+=len(data)
        header=addr|((len(data)//8)<<19)|(255<<36)
        frames.append(dict(target=120,address=3840,data=f'{header:064x}'))
        for offset in range(0,len(data),8):
            packet=sum(v<<(32*i) for i,v in enumerate(data[offset:offset+8]))
            frames.append(dict(target=120,address=3841,data=f'{packet:064x}'))
    return dict(schema='ot.vm.f20_boot_frames.v1',frames=frames,word_count=words,header_count=len(regions),payload_count=words//8,boot_frame_count=len(frames),drain_edges_after_final_bank_sample=5,extra_steady_cycles=0,runtime_A_replication_qualified=False,source_selected=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.write_text(json.dumps(compile_regions(json.loads(a.input.read_text())),indent=2)+'\n')
if __name__=='__main__':main()
