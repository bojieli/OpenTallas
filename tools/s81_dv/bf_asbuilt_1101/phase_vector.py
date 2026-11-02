#!/usr/bin/env python3
"""Select another BF phase from the SAME already-emitted full field."""
from pathlib import Path
import argparse
import json
import os
import numpy as np


def select(snapshot,vector,fixture,phase,out):
    snapshot,vector,fixture,out=map(Path,(snapshot,vector,fixture,out))
    if out.exists():raise ValueError('preserve previous vectors')
    field=json.loads(snapshot.read_text());old=json.loads((vector/'meta.json').read_text())
    if field['frame']!=old['die_frame']:raise ValueError('vector must hold this exact field')
    ph=next(p for p in field['phases'] if p['phase']==phase)
    if ph.get('fmt')!='bf16':raise ValueError('this selector only covers BF phases')
    out.mkdir(parents=True)
    for p in vector.iterdir():
        if p.is_file():os.link(p,out/p.name)
    rows={}
    for r in range(ph['rows']):
        rows[str(r)]=dict(vals=ph['plan']['rows_vals'][str(r)],acc=ph['plan']['acc'][r],bf16=ph['plan']['bf16'][r],
                          src=[ph['mat'],ph['row_index'][r]],out_index=ph['tie'][r][1],tie=ph['tie'][r],
                          tie_kind=ph['tie_kind'],seg=ph['seg'])
    meta=dict(old,op=ph['op'],field_phase=phase,chunk=ph['chunk'],mat=ph['mat'],K=ph['K'],kseg=ph['kseg'],
              xbase=ph['xbase'],seg=ph['seg'],nseg=ph['nseg'],nrows=ph['rows'],rows=rows,
              bf=dict(pairs=ph['bf_pairs'],assign=ph['assign'],desc=ph['desc'],desc_images={}),
              plan={k:ph['plan'].get(k) for k in ('ret','faults','ret_words','nodes','emission','assign','desc')})
    files=json.loads((fixture/'files.json').read_text())
    if ph['op']=='attn.wo_a':
        name='ops/attn.normalize.unrope.bin'
        f=files[name];values=np.fromfile(fixture/name,dtype=np.dtype(f['dtype'])).reshape(-1)
        fm=json.loads((fixture/'meta.json').read_text())
        ranges=fm['tp_split']['wo_a_rows'];rank=fm['rank'];groups=values.size//ph['K']
        rows_per_group=ranges[-1][1]//groups
        source_groups={(ranges[rank][0]+r)//rows_per_group for r in ph['row_index']}
        if len(source_groups)!=1:raise ValueError('actual wo_a phase spans input head groups')
        values=values.reshape(groups,ph['K'])[source_groups.pop()]
    elif ph['op']=='ffn.router':
        name='ops/ffn.norm.scale.bin'
        f=files[name];values=np.fromfile(fixture/name,dtype=np.dtype(f['dtype'])).reshape(f['shape']).reshape(-1)
    else:raise ValueError('phase vector needs an explicitly supported actual input source')
    vm=''.join(f'{int(v):08x}\n' for v in np.asarray(values[ph['kseg'][0]:ph['kseg'][1]],dtype=np.float32).view(np.uint32))
    if ph['phase']==old['field_phase'] and vm!=(vector/'vm.hex').read_text():
        raise ValueError('actual input-group reconstruction differs from original native vector')
    args=f'+OT_ROM_DIR={out} +T=3000 +K={ph["kseg"][1]-ph["kseg"][0]} +OPS={max(1,ph["rows"])} +PH={phase}\n'
    for name,value in [('meta.json',json.dumps(meta,indent=1)+'\n'),('vm.hex',vm),('ARGS',args)]:
        p=out/name;p.unlink();p.write_text(value)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--snapshot',required=True);p.add_argument('--vector',required=True)
    p.add_argument('--fixture',required=True);p.add_argument('--phase',required=True,type=int);p.add_argument('--out',required=True)
    a=p.parse_args();select(a.snapshot,a.vector,a.fixture,a.phase,a.out)
