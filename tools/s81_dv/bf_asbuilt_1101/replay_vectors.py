#!/usr/bin/env python3
"""Embed fitted BF descriptors in copied 72-bit CFG masks; preserve failed vectors."""
from pathlib import Path
import argparse
import json
import os
import shutil
import sys


def word(data,address):
    return sum(((data[address//8]>>(8*b+address%8))&1)<<b for b in range(72))


def put(data,address,value):
    index,slot=divmod(address,8)
    mask=sum(1<<(8*b+slot) for b in range(72))
    data[index]=(data[index]&~mask)|sum(((value>>b)&1)<<(8*b+slot) for b in range(72))


def emit(vector,measurement,out,descriptor_fault=False,payload_fault=False):
    vector,measurement,out=Path(vector),Path(measurement),Path(out)
    if out.exists():raise ValueError('preserve previous vector output')
    out.mkdir(parents=True)
    for path in vector.iterdir():
        if path.is_file():os.link(path,out/path.name)
    meta=json.loads((vector/'meta.json').read_text())
    records=json.loads(measurement.read_text())
    rec=records[meta['shape']]
    if not rec['ok']:raise ValueError('a failed measurement cannot programme a replay')
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'s81'))
    import bf_programme_compile as BC
    desc={}
    for pair in meta['bf']['pairs']:
        d=dict(rec['fits'][str(pair)]['descriptor'])
        # The measured issue shape is reusable; the actual full field's
        # per-pair ROM base is part of this phase's native CFG word sixteen.
        base_cfg=[int(v,16) for v in (vector/f'f_c{pair}_2.viamap.hex').read_text().split()]
        d['base']=word(base_cfg,4*meta['field_phase']+2)>>6
        if descriptor_fault and pair==meta['bf']['pairs'][0]:d['off']+=1
        desc[str(pair)]=d;packed=BC.pack(d)
        for prefix in (meta['die_frame'],'f'):
            for w in range(4):
                path=out/f'{prefix}_c{pair}_{w%7}.viamap.hex'
                data=[int(v,16) for v in path.read_text().split()]
                address=4*meta['field_phase']+w//7
                before=word(data,address)
                value=(before&((1<<48)-1))|(((packed>>(24*w))&0xffffff)<<48)
                put(data,address,value)
                if word(data,address)&((1<<48)-1)!=before&((1<<48)-1):
                    raise AssertionError('descriptor rewrite changed native CFG fields')
                path.unlink();path.write_text(''.join(f'{v:0144x}\n' for v in data))
    if payload_fault:
        pair=meta['bf']['pairs'][0]
        for bank in (0,1):
            a=out/f'f_e{pair}w_{bank}.viamap.hex';b=out/f'f_e{pair}e_{bank}.viamap.hex'
            av,bv=a.read_bytes(),b.read_bytes()
            if av==bv:raise ValueError('payload swap must alter real emitted weights')
            a.unlink();b.unlink();a.write_bytes(bv);b.write_bytes(av)
    meta.update(measure=False,calendar='measured_shape',mutant='desc' if descriptor_fault else ('swap' if payload_fault else None))
    meta['bf']['desc']=desc
    # Retain measured values/dates as the independent replay oracle.
    from layer_prog import xs_bf as XB
    ph=json.loads((vector/'meta.json').read_text())
    rows=[ph['rows'][str(r)]['vals'] for r in range(ph['nrows'])]
    bases=[desc[str(p)]['base'] for p in meta['bf']['pairs']]
    plan=XB.bf_plan(meta['master'],meta['bf']['pairs'],rows,meta['seg'],meta['nseg'],rec,bases,frame=rec['frame'])
    meta['plan'].update(ret=plan['ret'],faults=plan['faults'],ret_words=plan['ret_words'])
    for name,value in [('meta.json',json.dumps(meta,indent=1)+'\n'),('ARGS',(vector/'ARGS').read_text().replace(str(vector),str(out)))]:
        path=out/name;path.unlink();path.write_text(value)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--vector',required=True);p.add_argument('--measurement',required=True)
    p.add_argument('--out',required=True);p.add_argument('--descriptor-fault',action='store_true');p.add_argument('--payload-fault',action='store_true')
    a=p.parse_args();emit(a.vector,a.measurement,a.out,a.descriptor_fault,a.payload_fault)
