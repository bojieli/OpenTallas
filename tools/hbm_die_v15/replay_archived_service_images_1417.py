#!/usr/bin/env python3
"""Reconstruct missing simulator image files only from archived exact sectors.

This is external DRAM fixture generation, never an internal on-chip substitute.
Original image hashes must agree before any replay can consume the images.
"""
import argparse,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def restore(out):
    base=ROOT/'results/arch/hbm_die_v15/mapped4_checkpoint'
    hashes=json.loads((base/'image_artifacts.json').read_text());out=Path(out);out.mkdir(parents=True,exist_ok=True)
    seen=[]
    for sm,expected in hashes.items():
        src=base/sm;dest=out/sm;dest.mkdir()
        for name in ('config.json','records.hex','physical.hex','receipt.json'):
            data=(src/name).read_bytes()
            if hashlib.sha256(data).hexdigest()!=expected[name]:raise ValueError('archive identity drift '+sm+'/'+name)
            (dest/name).write_bytes(data)
        physical=(src/'physical.hex').read_text().splitlines();back=[];sectors=[]
        if len(physical)%2:raise ValueError('malformed physical source')
        used=set()
        for i in range(len(physical)//2):
            a=physical[2*i];data=physical[2*i+1]
            if not a.startswith('@'):raise ValueError('missing physical address')
            addr=int(a[1:],16)%65536
            if addr in used:raise ValueError('backing image address alias')
            used.add(addr);back.append(f'@{addr:08x}\n{data}\n');sectors.append(data+'\n')
        for name,data in [('backing.hex',''.join(back).encode()),('sectors.hex',''.join(sectors).encode())]:
            if hashlib.sha256(data).hexdigest()!=expected[name]:raise ValueError('reconstructed image differs '+sm+'/'+name)
            (dest/name).write_bytes(data)
        seen.append(dict(sm=sm,sectors=len(sectors),original_hashes_verified=True))
    print(json.dumps(dict(external_images=seen,hardware_or_price_qualification=False)))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();restore(a.out)
