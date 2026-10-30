#!/usr/bin/env python3
"""Relocate a complete explicit-row producer/consumer slice into finite VM.

This generates native region fragments and a boundary map, not a full programme.
Alias relations inside the slice are preserved by an injective interval mapping.
External live values and publication into/out of the slice need composition.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path


def span(d):
    if any(getattr(d,k,0)for k in ('indexed','dyn_sel','n_sel','lstride','l1stride')):
        raise ValueError('dynamic VM descriptor requires resolved boundary values')
    if d.stride<0 or d.istride<0:raise ValueError('negative descriptor stride unsupported')
    # Conservative cover: retain full n*m even for broadcast/overlapping rows.
    size=max(d.n*max(1,d.m),(max(1,d.m)-1)*d.stride+(d.n-1)*max(1,d.istride)+1)
    return d.base,d.base+size


def merge_intervals(intervals):
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
        else:out.append([a,b])
    return out


def addresses(d):
    if d.istride not in (0,1):raise ValueError('boundary census requires unit inner stride')
    return merge_intervals([(d.base+j*d.stride,d.base+j*d.stride+(1 if d.ibcast else d.n))for j in range(max(1,d.m))])


def uncovered(a,b,covered):
    out=[];cursor=a
    for lo,hi in covered:
        if hi<=cursor:continue
        if lo>=b:break
        if lo>cursor:out.append([cursor,min(lo,b)])
        cursor=max(cursor,hi)
        if cursor>=b:break
    if cursor<b:out.append([cursor,b])
    return out


def make(records,first,last,start,count,IR,capacity=262144,reserve=0):
    originals=[];intervals=[];written=[];boundary=[]
    for i in range(first,last+1):
        _,r,x,_=records[i]
        if x is None or x.rsel or start+count>x.n:raise ValueError('region requires explicit aligned row records')
        expanded=IR.expand(r,x)[start:start+count]
        originals.append((i,r,x,expanded))
        for _,row in expanded:
            write_ops=IR.written_operands(row)
            for k,d in row.desc.items():
                if d.space=='VM' and k not in write_ops:
                    for lo,hi in addresses(d):boundary.extend(uncovered(lo,hi,written))
            written=merge_intervals(written+[iv for k,d in row.desc.items()if d.space=='VM'and k in write_ops for iv in addresses(d)])
            for d in row.desc.values():
                if d.space=='VM':intervals.append(span(d))
    regions=[]
    for a,b in sorted(intervals):
        if regions and a<=regions[-1][1]:regions[-1][1]=max(b,regions[-1][1])
        else:regions.append([a,b])
    cursor=(reserve+7)//8*8;mapping=[]
    for a,b in regions:
        mapping.append(dict(source=[a,b],destination=[cursor,cursor+b-a]))
        cursor=(cursor+b-a+7)//8*8
    if cursor>capacity:raise ValueError(f'region needs {cursor} words > {capacity}')
    def relocated(d):
        a,b=span(d)
        for m in mapping:
            lo,hi=m['source']
            if lo<=a<b<=hi:return m['destination'][0]+a-lo
        raise ValueError('descriptor crosses mapping boundary')
    blob=bytearray();proof=[]
    for index,r,x,expanded in originals:
        q=copy.deepcopy(r);qx=copy.deepcopy(x);qx.n=count;qx.slot0=x.slot0+start;q.slot=qx.slot0&7
        if q.unit=='SM':q.param=(q.param&3)|((count-1)<<2)
        for k,d in q.desc.items():
            bases=[]
            for _,row in expanded:
                rd=row.desc[k];bases.append(relocated(rd)if rd.space=='VM'else rd.base)
            d.base=bases[0]
            if count>1:
                diffs={bases[j]-bases[j-1]for j in range(1,count)}
                if len(diffs)!=1:raise ValueError('row bases no longer affine')
                delta=diffs.pop()
                if d.space=='HBM':
                    if delta%(1<<qx.hsh):raise ValueError('HBM stride scale mismatch')
                    delta>>=qx.hsh
                if delta:qx.rs[k]=delta
                else:qx.rs.pop(k,None)
        IR.check(q,qx);IR.check_rows_independent(q,qx)
        actual=IR.expand(q,qx)
        for (slot,before),(after_slot,after) in zip(expanded,actual):
            expect=copy.deepcopy(before)
            for d in expect.desc.values():
                if d.space=='VM':d.base=relocated(d)
            if slot!=after_slot or vars(expect)!=vars(after):raise ValueError('native row semantics changed')
        encoded=IR.encode(q,qx);proof.append(dict(source_record=index,offset=len(blob),bytes=len(encoded),unit=r.unit,op=r.op))
        blob.extend(encoded)
    return bytes(blob),dict(start_row=start,rows=count,vm_high_water_words=cursor,other_live_reserve_words=reserve,
                            unallocated_words=capacity-cursor,source_intervals=mapping,records=proof,
                            boundary_input_source_intervals=merge_intervals(boundary),
                            written_source_intervals=written,
                            boundary_input_words=sum(b-a for a,b in merge_intervals(boundary)),
                            arithmetic_row_expansion_and_aliases_preserved=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--first',type=int,default=1458);ap.add_argument('--last',type=int,default=1473)
    ap.add_argument('--rows',type=int,default=2);ap.add_argument('--reserve',type=int,default=0)
    a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import isa_rows as IR,image_check as IC
    raw=Path(a.image).read_bytes();records=IC.decode_all(raw);n=records[a.first][2].n
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);phases=[]
    for start in range(0,n,a.rows):
        blob,info=make(records,a.first,a.last,start,min(a.rows,n-start),IR,reserve=a.reserve)
        name=f'phase_{start}.hgi1r';(out/name).write_bytes(blob);info['native_fragment']=name;phases.append(info)
    packet=dict(schema='opentallas.hbm.vm_native_region.v1',source_image_sha256=hashlib.sha256(raw).hexdigest(),
                source_record_range=[a.first,a.last],executable=False,full_programme_fits=None,phases=phases,
                holds=['boundary inputs must be published/reloaded to mapped region addresses',
                       'outside live values must fit the reserved space and survive all phases',
                       'boundary outputs must be retired to their actual later consumers',
                       'phase reordering requires interphase dependency check and composed schedule'])
    (out/'region.json').write_text(json.dumps(packet,indent=1)+'\n')
    print(json.dumps(dict(status='NATIVE_REGION_FRAGMENTS_READY',high_water=[p['vm_high_water_words']for p in phases],
                         outside_reserve=a.reserve,full_programme_fits=None)))

if __name__=='__main__':main()
