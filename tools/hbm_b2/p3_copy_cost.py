#!/usr/bin/env python3
"""Cost real operand-copy records emitted by the opt-in P3 FUSED lowering.

Uses the selected cohort's existing hgi_sim.timing.cost, never the old claimed
MU throughput. Summed unit work is not a token schedule: all-unit waits, FUSED
row serialization, physical binding and eight-SM costs remain separate.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import sys


def price(model_root: Path, image_dir: Path, fused_model=None):
    sys.path[:0] = [str(model_root/'tools/hbm_next'), str(model_root/'tools')]
    import isa_rows as IR
    from hgi_sim import timing as T
    meta = json.loads((image_dir/'emitter.json').read_text())
    raw = (image_dir/meta['token']['image']).read_bytes()
    recs=[]; off=0
    while off<len(raw):
        r,rx,nxt=IR.decode_one(raw,off); recs.append((off,r,rx));off=nxt
    byoff={off:i for i,(off,_,_) in enumerate(recs)}
    selected={}
    mat=meta['fused_materialization']
    for block in mat['records']:
        i=byoff[block['offset']]
        for off,r,rx in recs[i:i+block['new_records']]:
            if r.unit in ('SU','DMA'):selected[off]=(r,rx,'FUSED_MATERIALIZATION')
    rid=mat.get('rid_materialization')
    if rid:
        lo,hi=rid['base'],rid['base']+rid['words']
        for off,r,rx in recs:
            o=r.desc.get('O')
            if r.unit=='SU' and o and o.space=='VM' and lo<=o.base<hi:
                selected.setdefault(off,(r,rx,'RID_MATERIALIZATION'))
    kinds=Counter();cycles=Counter();words=Counter();details=[]
    dyn=T.Dyn(1048575,0)
    rowx_records=0
    for off,(r,rx,origin) in sorted(selected.items()):
        if rx is not None:rowx_records+=1
        for row,rr in IR.expand(r,rx):
            n=rr.desc['A'].n*max(1,rr.desc['A'].m)
            c,grade,how=T.cost(rr,dyn,0)
            unit=rr.unit+'.'+rr.op
            kinds[unit]+=1;cycles[unit]+=c;words['VM_copy' if rr.unit=='SU' else 'HBM_load']+=n
            if rr.unit=='DMA':words['HBM_bytes']+=n*T.ESZ[rr.desc['A'].fmt]
            details.append(dict(offset=off,row=row,origin=origin,unit=unit,words=n,cycles=c,grade=grade,how=how))
    fused=None
    if fused_model:
        hist=Counter();before=after=0
        for block in mat['records']:
            c1,ii=fused_model[block['op']]
            before+=c1+(block['original_rows']-1)*ii
            i=byoff[block['offset']];nrows=0
            for off,r,rx in recs[i:i+block['new_records']]:
                if r.unit!='FUSED':continue
                count=rx.n if rx else 1;nrows+=count
                hist[(r.op,count)]+=1;after+=c1+(count-1)*ii
            if nrows!=block['original_rows']:
                raise ValueError('lowered FUSED chunk rows do not cover the original frame')
        fused=dict(firstrow_II=fused_model,original_cycles=before,lowered_cycles=after,
                   added_cycles=after-before,
                   chunks=[dict(op=op,rows=rows,count=n) for (op,rows),n in sorted(hist.items())],
                   scope='explicit supplied first-row/II model; no selected native or eight-SM claim')
    bw=T.cv('hbm','bytes_per_cycle')
    return dict(schema='opentallas.p3.materialization_cost.v1',input_image=str(image_dir),
        status='CONDITIONAL_EXISTING_MODEL_UNIT_WORK_NOT_TOKEN_RATE',
        scope='selected cohort cost; FUSED row overlap, all-unit drain delays, physical replay and eight-SM model not included',
        instructions_selected=len(selected),rowx_instructions_expanded_serially=rowx_records,
        records_per_unit=dict(kinds),cycles_per_unit=dict(cycles),unit_work_serial_sum_cycles=sum(cycles.values()),
        vm_copy_words=words['VM_copy'],hbm_load_words=words['HBM_load'],hbm_load_bytes=words['HBM_bytes'],HBM_bytes_per_cycle=bw,
        HBM_traffic_floor_cycles=words['HBM_bytes']/bw,
        fused_chunk_model=fused,record_costs=details)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model-root',type=Path,required=True)
    p.add_argument('--image',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--fused-pre',help='explicit HC_PRE_NORM firstrow,II cycles (optional diagnostic)')
    p.add_argument('--fused-post',help='explicit HC_POST firstrow,II cycles (optional diagnostic)')
    a=p.parse_args()
    if bool(a.fused_pre)!=bool(a.fused_post):p.error('supply both FUSED first-row/II models')
    fm=None
    if a.fused_pre:
        fm={k:tuple(map(float,v.split(','))) for k,v in [('HC_PRE_NORM',a.fused_pre),('HC_POST',a.fused_post)]}
        if any(len(v)!=2 or min(v)<0 for v in fm.values()):p.error('expected non-negative firstrow,II pairs')
    result=price(a.model_root,a.image,fm)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='record_costs'},indent=2))


if __name__=='__main__':main()
