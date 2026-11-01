#!/usr/bin/env python3
"""Stream released TP4 w2 row slices for missing ranks; no golden recomputation.

First reproduce all fourteen rank0 source payload hashes exactly. Only then
emit bounded raw rank1..3 tensor slices as a tar stream to fleet scratch.
Global op data is reused separately; no state or producer authority is granted.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import re
import sys
import tarfile

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools'))
from rtl_v41_fullshape_layer_campaign import Checkpoint,_raw


def extract(base,checkpoint):
    base=json.loads(Path(base).read_text());meta=base['meta'];files=base['files']
    if meta['rank']!=0 or meta['tp']!=4 or not all(meta['checks'].values()):
        raise ValueError('requires the passed rank0 TP4 global golden fixture')
    selected={k:v for k,v in files.items() if re.fullmatch(r'weights/(?:shared|exp\d+)\.w2(?:\.scale)?\.bin',k)}
    if len(selected)!=14:raise ValueError('expected exactly seven released w2 matrices and scales')
    ck=Checkpoint(Path(checkpoint));headers={}
    for rel,spec in selected.items():
        if spec['rows'][0]!=0 or spec['cols'] is not None:raise ValueError('unexpected original TP4 w2 split')
        arr,dtype=_raw(ck,spec['tensor'],spec['rows'],None)
        if dtype!=spec['format'] or list(arr.shape)!=spec['shape'] or hashlib.sha256(arr.tobytes()).hexdigest()!=spec['sha256']:
            raise ValueError('released rank0 extraction differs from original source fixture: '+rel)
        header,offset,shard=ck.meta(spec['tensor'])
        if header['shape'][0]!=4*spec['rows'][1]:raise ValueError('w2 source tensor is not split into four equal output row ranges')
        headers[rel]=dict(tensor=spec['tensor'],dtype=dtype,shape=header['shape'],shard=shard,data_offsets=header['data_offsets'])
    def add(tar,name,data):
        info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;tar.addfile(info,io.BytesIO(data))
    report=dict(status='PASS_RELEASED_DOWN_SOURCE_SLICES',checkpoint=str(Path(checkpoint).resolve()),
                baseline_rank0_hashes_matched=14,tp=4,emitted_ranks=[1,2,3],headers=headers,
                scope='raw down w2/scales only; global op reuse is not source residency, state or programme authority',
                production_enabled=False,ranks={})
    with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as tar:
        for rank in (1,2,3):
            rankfiles={}
            for rel,spec in selected.items():
                count=spec['rows'][1];rows=[rank*count,(rank+1)*count]
                arr,dtype=_raw(ck,spec['tensor'],rows,None);data=arr.tobytes()
                new=dict(spec,rows=rows,sha256=hashlib.sha256(data).hexdigest(),shape=list(arr.shape))
                rankfiles[rel]=new;add(tar,f'rank{rank}/'+rel,data)
            report['ranks'][rank]=rankfiles
            add(tar,f'rank{rank}/weights_files.json',(json.dumps(rankfiles,indent=2)+'\n').encode())
        add(tar,'source.json',(json.dumps(report,indent=2)+'\n').encode())
    print('RELEASED_DOWN_SOURCE_SLICES_PASS rank0_hashes14 ranks1,2,3',file=sys.stderr)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--base',required=True);p.add_argument('--checkpoint',required=True)
    a=p.parse_args();extract(a.base,a.checkpoint)
