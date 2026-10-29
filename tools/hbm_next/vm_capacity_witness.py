#!/usr/bin/env python3
"""Prove a concrete simultaneous-live VM capacity lower bound in a decoded HGI-1R image.

Uses exact addressed words, not descriptor bounding boxes or allocator high-water.
A dependent SU chain keeps future inputs live while the first SU reads its inputs.
No aliasing, instruction reordering, new streaming contract or payload recomputation
is assumed; those would be separately compiled alternatives, not fixed relocation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def words(record, rowx, operand):
    d=record.desc[operand]
    if d.space!='VM':raise ValueError('witness needs VM operands')
    if any(getattr(d,k,0)for k in ('dyn_sel','n_sel','lstride','l1stride','indexed')):
        raise ValueError('dynamic witness operand needs its own exact source bound')
    if rowx and rowx.rsel:raise ValueError('selected-row witness is not statically explicit')
    step=0 if d.ibcast else (d.istride or 1)
    n=1 if step==0 else d.n
    return {d.base+q*(rowx.rs.get(operand,0)if rowx else 0)+j*d.stride+i*step
            for q in range(rowx.n if rowx else 1)for j in range(max(d.m,1))for i in range(n)}


def ranges(xs):
    result=[]
    for v in sorted(xs):
        if result and result[-1][1]==v:result[-1][1]=v+1
        else:result.append([v,v+1])
    return result


def prove(recs,at,bridge,future,capacity):
    if not 0<=at<bridge<future<len(recs):raise ValueError('witness ordering')
    ra,rb,rc=(recs[j][1]for j in (at,bridge,future))
    xa,xb,xc=(recs[j][2]for j in (at,bridge,future))
    if any((r.unit,r.op)!=('SU','VOP')or r.pred!='ALWAYS'for r in (ra,rb,rc)):
        raise ValueError('witness needs unconditional SU VOP chain')
    if words(ra,xa,'R')!=words(rb,xb,'A'):
        raise ValueError('current R is not the bridge A dependency')
    if words(rb,xb,'O')!=words(rc,xc,'B'):
        raise ValueError('bridge O is not the future B dependency')
    sets=[('current_A',at,'A',words(ra,xa,'A')),('current_B',at,'B',words(ra,xa,'B')),
          ('deferred_C',future,'C',words(rc,xc,'C')),('deferred_A',future,'A',words(rc,xc,'A'))]
    union=set()
    for name,index,op,ws in sets:
        if union & ws:raise ValueError(f'{name} aliases a different simultaneously live input')
        union |= ws
        if index==future:
            for j in range(at,future):
                _,r,x,_=recs[j]
                for k in ('O','R'):
                    if k in r.desc and r.desc[k].space=='VM' and words(r,x,k)&ws:
                        raise ValueError(f'intervening writer {j}.{k} changes deferred value')
    return dict(schema='opentallas.hbm.vm_capacity_witness.v1',
                scope='fixed relocation preserving this programme record/row-array lifetimes',
                lower_bound_words=len(union),capacity_words=capacity,
                deficit_words=max(0,len(union)-capacity),fits=len(union)<=capacity,
                statement='No fixed address rebase can fit these distinct simultaneously live values.',
                dependencies=[dict(producer=at,producer_operand='R',consumer=bridge,consumer_operand='A',words=len(words(ra,xa,'R'))),
                              dict(producer=bridge,producer_operand='O',consumer=future,consumer_operand='B',words=len(words(rb,xb,'O')))],
                inputs=[dict(name=name,record_index=i,image_offset=recs[i][0],operand=k,words=len(ws),ranges=ranges(ws),
                             descriptor=vars(recs[i][1].desc[k]),row_count=recs[i][2].n if recs[i][2]else 1,
                             row_stride=recs[i][2].rs.get(k,0)if recs[i][2]else 0)for name,i,k,ws in sets],
                remedies=['qualified larger regular VM with real address/interface/boot-source plan event',
                          'separately emitted finite phases/rescheduling with actual payload publication and priced transfers'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--image',required=True)
    ap.add_argument('--compiler-tools',required=True)
    ap.add_argument('--at',type=int,default=1470)
    ap.add_argument('--bridge',type=int,default=1472)
    ap.add_argument('--future',type=int,default=1473)
    ap.add_argument('--capacity',type=int,default=262144)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    compiler=Path(a.compiler_tools)
    sys.path[:0]=[str(compiler/'hbm_next'),str(compiler)]
    import image_check as IC
    raw=Path(a.image).read_bytes()
    result=prove(IC.decode_all(raw),a.at,a.bridge,a.future,a.capacity)
    result['image_sha256']=hashlib.sha256(raw).hexdigest()
    Path(a.out).write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps({k:result[k]for k in ('lower_bound_words','capacity_words','deficit_words','fits')}))


if __name__=='__main__':main()
