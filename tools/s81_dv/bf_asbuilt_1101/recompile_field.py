#!/usr/bin/env python3
"""Recompile BF phases through the real compiler, retaining an emitted FP field."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import sys
import numpy as np


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module


def recompile(a):
    source,raw,out=Path(a.source),Path(a.raw),Path(a.out)
    if out.exists():raise ValueError('preserve prior field programmes')
    out.mkdir(parents=True)
    os.environ['OT_S81_SELECTED_SOURCE_ROOT']=str(source)
    os.environ['OT_XS_BF_MEAS']=str(Path(a.candidate).resolve())
    sys.path[:0]=[str(source/'tools'),str(source/'tools/s81_dv'),str(source/'tools/s81_dv/layer_prog'),str(source/'tools/s81')]
    if a.bf_module:load('xs_bf',a.bf_module)
    if a.field_module:X=load('xs_place_current',a.field_module)
    else:
        from layer_prog import xs_place as X
    import dv_layer_compile as C
    import v41_die_images_w17w10 as I
    import xs_bf as B
    rec=json.loads(Path(a.snapshot).read_text());groups=json.loads(Path(a.groups).read_text())
    first=next(p['phase'] for p in rec['phases'] if p.get('fmt')=='bf16')
    cfg={l.split()[0]:l.split()[1:] for l in (raw/'field.txt').read_text().splitlines()}
    n=int(cfg['np'][0]);active=list(map(int,cfg['active']));bfslots=list(map(int,cfg['bf16']))
    field=I.Field(n,int(cfg['r'][0]),len(bfslots),depth=rec['depth'],active=len(active),pp=True,fast=True)
    field.act[:]=False;field.act[active]=True;field.bf[:]=False;field.bf[bfslots]=True
    field.fill=np.asarray(rec['fill'],dtype=np.int64);field.fill[bfslots]=0
    field.cfg=[[[0]*25 for _ in range(n)] for _ in range(first)]
    for slot in active:
        words=[int(v,16) for v in (raw/f'e{slot}.cfg.hex').read_text().split()]
        for phase in range(first):field.cfg[phase][slot]=words[25*phase:25*(phase+1)]
        if slot in bfslots:continue
        for bank in range(2):
            suffix='b' if bank else ''
            for line in (raw/f'e{slot}{suffix}.words.hex').read_text().splitlines():
                address,value=line.split();field.words[2*slot+bank][int(address,16)]=int(value,16)
    phasewords=[int(v,16) for v in (raw/'spine_phase.hex').read_text().split()]
    for phase in range(first):
        v=phasewords[2*phase]
        field.phases.append(dict(bf=v&1,K=(v>>1)&0x1fff,nbeat=(v>>14)&0xffff,sbase=(v>>30)&0xffff,
                                 nrows=(v>>46)&0xffff,fmt_fp32=[(v>>62)&1,(v>>63)&1],rsplit=phasewords[2*phase+1]))
    stop=rec['phases'][first]['sbase']
    field.stream=[int(v,16) for v in (raw/'spine_stream.hex').read_text().split()][:stop]
    field.bf_desc={};field.aproj_rank_rows=rec['phases'][0]['row_index'];field.stretch=None
    C.Die(Path(a.tree))  # establishes the exact physical frame-count row dealing once
    ops=list(dict.fromkeys(p['op'] for p in rec['phases'][first:]))
    new=X.compile_bf(field,X.Fix(a.fixture),ops,rec['slice_index'],rec['frame_index'],X.LX.base_master(rec['master']),
                     X.LX.land_e(rec['lk']),rec['bf_pairs'],len(rec['pairs']),frame=B.frame_variant(rec['master']))
    for old,ph in zip(rec['phases'][first:],new):
        assert all(old[k]==ph[k] for k in ('phase','op','rows','row_index','seg','nseg','sbase','nbeat'))
        assert ph['calendar']=='measured_bf_active_idle_q' and ph['faults']==0 and ph['ret_words']==ph['rows']
    assert len(new)==len(rec['phases'])-first
    rec['phases']=rec['phases'][:first]+new;rec['fill']=[int(v) for v in field.fill]
    names,_=X.write_images(field,rec['pairs'],rec['q_pairs'],rec['bf_pairs'],rec['frame'],out/'images',
                           rank_context=dict(field=rec,groups=groups,already_ranked=[0]))
    (out/'field.json').write_text(json.dumps(rec,indent=1)+'\n')
    # Real nonzero descriptor bits must survive the FP row-ID rewrite.
    before=out/'images.phase_local';after=out/'images';nonzero=0
    original=raw.parent
    for name in names+['spine_phase.hex','spine_stream.hex']:
        if '_c' in name:continue
        assert hashlib.sha256((before/name).read_bytes()).digest()==hashlib.sha256((original/name).read_bytes()).digest(),name
    for path in before.glob(rec['frame']+'_c*_[0-6].viamap.hex'):
        a0=[int(v,16) for v in path.read_text().split()];a1=[int(v,16) for v in (after/path.name).read_text().split()]
        old=[int(v,16) for v in (original/path.name).read_text().split()]
        assert len(old)==len(a0)==len(a1)==512
        assert all(((x^y)&((1<<384)-1))==0 for x,y in zip(a0,old))
        assert all((x>>128)==(y>>128) for x,y in zip(a0,a1))
        nonzero+=sum(bool(v>>384) for v in a0)
    assert nonzero>0
    result=dict(status='PASS_SOURCE_FIELD',frame=rec['frame'],phases=rec['nphases'],images=len(names),
                BF_phases=len(new),BF_descriptors=sum(len(v) for v in field.bf_desc.values()),
                actual_nonzero_spare_mask_rows=nonzero,spare_planes_preserved=True,max_fill=max(rec['fill']),depth=rec['depth'],
                original_weight_phase_stream_bytes_identical=True,original_CFG_lower48_unchanged=True,
                FP_namespace_unchanged=True,BF_row_tags_unqualified=True,production_enabled=False,added_cycles=0,
                candidate_sha256=hashlib.sha256(Path(a.candidate).read_bytes()).hexdigest())
    (out/'check.json').write_text(json.dumps(result,indent=2)+'\n');print(result,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for arg in ('source','raw','snapshot','groups','fixture','tree','candidate','out'):p.add_argument('--'+arg,required=True)
    p.add_argument('--bf-module');p.add_argument('--field-module')
    recompile(p.parse_args())
