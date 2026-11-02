#!/usr/bin/env python3
"""Independent new-return forest check against fresh released-weight K segments.

No producer evaluator or old80 norm partials are imported. Each returned tag
owns a canonical padded binary subtree, checked before finishing the row.
"""
import argparse,json,struct,hashlib
from pathlib import Path
import numpy as np


def add(a,b):
    x=np.frombuffer(struct.pack('<II',a,b),dtype='<f4')
    with np.errstate(all='ignore'):v=np.float32(x[0]+x[1])
    if not np.isfinite(x).all() or not np.isfinite(v):raise ValueError('nonfinite source arithmetic')
    u=struct.unpack('<I',v.tobytes())[0]
    return u if u&0x7fffffff else 0


def padded(values,start,width):
    if start>=len(values):return None
    if width==1:return int(values[start])
    a=padded(values,start,width//2);b=padded(values,start+width//2,width//2)
    return b if a is None else a if b is None else add(a,b)


def inspect(field,kseg,bf16,expert=6):
    plan=field['plan'];n=plan['nseg'];width=1<<(n-1).bit_length();out=[]
    if n!=5 or len(field['source_rows'])!=plan['rows']:raise ValueError('source row/Ksegment contract changed')
    for local,global_row in enumerate(field['source_rows']):
        values=kseg[expert,global_row];declared=plan['rows_vals'][str(local)]
        if declared!=values.tolist():raise ValueError('plan original Ksegment order differs from fresh source witness')
        words=[w for w in plan['ret']if ((int(w[1])>>13)&0x3fff)==local]
        nodes={};coverage=[];rowtags=set()
        for cycle,tag,data,fault in words:
            tag=int(tag);lo=(tag>>8)&31;level=(tag>>5)&7;arity=tag&31;span=1<<level
            if fault or arity!=n or span>width or lo%span or lo>=n:raise ValueError('invalid/faulted canonical source interval')
            key=(lo,span)
            if key in nodes:raise ValueError('duplicate canonical source subtree')
            expected=padded(values,lo,span)
            if int(data)!=expected:raise ValueError(f'partial FP32 ownership/order mismatch row{global_row} lo{lo} span{span}')
            nodes[key]=int(data);coverage.extend(range(lo,min(lo+span,n)));rowtags.add(tag>>13)
        if sorted(coverage)!=list(range(n)) or len(rowtags)!=1:raise ValueError('source forest coverage/row-tag ownership differs')
        consumed=set()
        def finish(start,span):
            if start>=n:return None
            key=(start,span)
            if key in nodes:consumed.add(key);return nodes[key]
            if span==1:raise ValueError('missing canonical leaf')
            a=finish(start,span//2);b=finish(start+span//2,span//2)
            return b if a is None else a if b is None else add(a,b)
        actual=finish(0,width);expected=padded(values,0,width)
        if consumed!=set(nodes) or actual!=expected:raise ValueError('actual source forest cannot finish in canonical FP32 association')
        rounded=(actual+0x7fff+((actual>>16)&1))&0xffff0000
        if rounded!=int(bf16[expert,global_row]):raise ValueError('fresh source BF16 identity differs')
        out.append(dict(global_row=global_row,returned_subtrees=len(words),FP32=f'{actual:08x}',BF16_in_FP32=f'{rounded:08x}'))
    return dict(frame=field['frame'],phase=field['phase'],rows=out,canonical_Ksegment_order=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plans',type=Path,nargs='+',required=True);p.add_argument('--kseg',type=Path,required=True);p.add_argument('--bf16',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('fresh output directory required')
    k=np.fromfile(a.kseg,'<u4').reshape(7,5120,5);b=np.fromfile(a.bf16,'<u4').reshape(7,5120)
    fields=[json.loads(f.read_text())for f in a.plans];results=[inspect(f,k,b)for f in fields]
    from copy import deepcopy
    payload=deepcopy(fields[0]);payload['plan']['ret'][0][2]^=1
    controls={}
    try:inspect(payload,k,b)
    except ValueError as e:controls['payload_lsb']=str(e)
    else:raise ValueError('wrong partial payload was not caught')
    swapped=deepcopy(fields[0]);words=swapped['plan']['ret'];pair=None
    for i,x in enumerate(words):
        for j,y in enumerate(words[i+1:],i+1):
            if x[1]>>13==y[1]>>13 and ((x[1]>>5)&7)==((y[1]>>5)&7) and ((x[1]>>8)&31)!=((y[1]>>8)&31):pair=(i,j);break
        if pair:break
    if not pair:raise ValueError('independent equal-span tag ownership control unavailable')
    i,j=pair;words[i][1],words[j][1]=words[j][1],words[i][1]
    try:inspect(swapped,k,b)
    except ValueError as e:controls['tag_ownership_swap_preserves_payload_multiset']=str(e)
    else:raise ValueError('wrong subtree ownership was not caught')
    a.out.mkdir(parents=True)
    result=dict(status='PASS_INDEPENDENT_FRESH_SOURCE_RETURN_FOREST_ORDER',fields=results,checked_rows=sum(len(r['rows'])for r in results),controls_caught=controls,
        fresh_Kseg_sha256=hashlib.sha256(a.kseg.read_bytes()).hexdigest(),fresh_BF16_sha256=hashlib.sha256(a.bf16.read_bytes()).hexdigest(),
        source_plan_sha256={str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in a.plans},producer_evaluator_imported=False,old_norm_partial_files_read=False,
        numeric_source_only=True,actual_CAP_runtime_qualified=False,actual_CW_RD_arrival_leases_qualified=False,physical_phase_qualified=False,HOST_START_authority=False)
    (a.out/'check.json').write_text(json.dumps(result,indent=1)+'\n');print(result['status'],result['checked_rows'],'rows',controls)
