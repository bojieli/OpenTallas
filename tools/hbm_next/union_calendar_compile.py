#!/usr/bin/env python3
"""Compile U-keyed static model-record launch calendars; no runtime waits.

Production DS L2/N6/P3, measured v2+frames/tree/SM3. Every expert reserves N rows.
Payloads reference model records, not native descriptors; the manifest states this gap.
"""
import argparse, dataclasses, json, math, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from hbm_next import plane_compiler as PC, static_check as SC, emitter as E
from hgi_sim import hbm_plane_model as M

def compile_all(out,layer='2'):
    out.mkdir(parents=True,exist_ok=True)
    PC.CUR['hist']=PC.lane_hists()
    kn=PC.Knobs(**dict(PC.HEAD,P=3,rpl=False),union_safe=True,
        meas=PC.MEAS_ALL2+('idx_frame','fused_frame','fused_tree','sm3'))
    PC.apply_knobs(kn)
    variants=[]; all_meta=[]
    for u in range(6,37):
        PC.CUR['mode']='verify'
        prog,_=M.ds_compile(6,M.plane_cfg(3),u,'upper',False)
        M.P5._count_slots(prog);M.P5._consumers(prog)
        # apply_meas updates spans; keep the row-II metadata consistent for C3.
        for r in prog:
            if getattr(r,'orig_op','')=='COLL.ROW_GATHER' and getattr(r,'ii',None) is not None:
                r.ii *= 623.0/1449.0
        key,seg,s=SC.schedule_segments(prog,{str(layer)})[0]
        # Integer event serialization, preserving all original relative delays.
        ss=dict(s,start=list(s['start']),end=list(s['end']))
        seq=sorted(range(len(s['ex'])),key=lambda i:(s['start'][i],i))
        prev=-3;delta=0
        for i in seq:
            t=s['start'][i]
            d=math.ceil(max(t+delta,prev+3));delta=d-t;prev=d
            ss['start'][i]=d;ss['end'][i]=s['end'][i]+delta
        check=SC.check(seg,ss,n_rows=6,vm_capacity=1<<19)
        assert check['PASS'],check['violations']
        ri=[i for i,(k,*_) in enumerate(s['ex']) if getattr(seg[k],'mtp_kind','')=='expert_union'][0]
        epoch=math.ceil(ss['end'][ri]);events=[];records=[]
        for i in seq:
            k=s['ex'][i][0];r=seg[k]
            if ss['start'][i]<epoch or r.unit=='CTL':continue
            at=ss['start'][i]-epoch+3
            token=len(records)
            unit=E.UNIT_BIT[r.unit]
            events.append((int(at)<<48)|(unit<<32)|token)
            records.append(dict(id=token,tag=r.tag,op=r.orig_op,kind=r.mtp_kind,
                model_index=k,cycle=at,span=ss['end'][i]-ss['start'][i]))
        final=math.ceil(max(ss['end']))-epoch+6
        if events:final=max(final,((events[-1]>>48)&0xffffffff)+3)
        events.append((1<<80)|(final<<48))
        variants.append(events)
        all_meta.append(dict(U=u,events=len(events),end_cycle=final,records=records,
            static_check=check['counts'],common_prefix_end=epoch))
        print('U',u,'events',len(events),'end',final,flush=True)
    stride=1<<(max(map(len,variants))-1).bit_length()
    words=[]
    for v in variants:words+=v+[0]*(stride-len(v))
    assert len(words)<=1<<14, '14-bit calendar store capacity'
    (out/'calendar.mem').write_text(''.join(f'{w:021x}\n' for w in words))
    result=dict(layer=layer,N=6,P=3,U_min=6,U_max=36,stride=stride,words=len(words),
        capacity_words=1<<14,word_bits=81,bytes=math.ceil(len(words)*81/8),
        native_descriptor_binding=False,ss_ff_closed=False,variants=all_meta)
    lines=[f'{len(words)} {stride}']
    for v in all_meta:
        lines.append(f"{len(v['records'])} {v['end_cycle']}")
        lines.extend(f"{r['cycle']} {E.UNIT_BIT[r['op'].split('.')[0]]} {r['id']}" for r in v['records'])
    (out/'cases.txt').write_text('\n'.join(lines)+'\n')
    (out/'calendar.json').write_text(json.dumps(result,indent=1)+'\n')
    return result
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();r=compile_all(a.out)
    print('UNION_STATIC_COMPILE PASS',r['words'],'of',r['capacity_words'],'words')
