#!/usr/bin/env python3
"""Relocate the actual six-row expert UNION/indexed/LOOP entry, preserving rsel.

This is a bounded source component, not an executable whole-programme image.
The declared indexed extent comes from the actual preceding producer1560 reads.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path


def expert_end(records,first):
    seen=0
    for index in range(first+1,len(records)):
        _,r,x,_=records[index]
        if x and x.rsel and r.unit=='SM':seen+=1
        if seen==3 and r.unit=='COLL':return index
        if index>first+100 or(r.unit=='IDX'and r.op=='UNION'):break
    raise ValueError('expert source block lacks known three-rsel/final-collective boundary')


def layout(records,first,last):
    from vm_value_phase import engine_span
    import isa_rows as IR
    union=records[first][1]
    if(union.unit,union.op)!=('IDX','UNION'):raise ValueError('source entry is not expert UNION')
    n,k,pitch,experts=union.desc['A'].m,union.desc['A'].n,union.imm_b,union.imm_a
    if(n,k,pitch,experts)!=(6,6,7,384):raise ValueError('unqualified expert union shape')
    capacity=union.desc['O'].n
    if capacity!=36 or union.desc['R'].stride!=32:raise ValueError('unqualified expert table capacity')
    spans=[]
    for index in range(first,last+1):
        _,r,x,_=records[index]
        if x and x.rsel:
            if r.unit!='SM' or x.rtab!=union.desc['R'].base or x.n!=n or x.emask not in(16,17):raise ValueError('unknown dynamic row-table semantics')
            spans.append((x.rtab,x.rtab+capacity*32))
        for name,d in r.desc.items():
            if d.space!='VM':continue
            step=x.rs.get(name,0)if x else 0
            maxrow=(n-1)*pitch+k-1 if x and x.rsel and x.emask>>IR.OPND.index(name)&1 else((x.n-1)if x else 0)
            if step<0:raise ValueError('negative row address stride requires explicit proof')
            q=copy.deepcopy(r)
            if d.indexed:
                if r.unit!='SU' or name!='A' or d.dyn_mul!=1:raise ValueError('unknown indexed VM footprint')
                q.desc[name].indexed=0;q.desc[name].dyn_mul=0
            lo,hi=engine_span(q,name);hi+=maxrow*step
            if d.indexed:hi+=experts-1
            # SM I+L is an implicit full-union ID stream, not a scalar.
            if x and x.rsel and name=='I':hi=max(hi,d.base+capacity)
            spans.append((lo//32*32,(hi+31)//32*32))
        if(r.unit,r.op)==('CTL','LOOP'):
            if not r.param&(1<<17) or r.imm_a!=union.desc['D'].base:raise ValueError('unknown expert loop source count')
            spans.append((r.imm_a//32*32,(r.imm_a//32+1)*32))
    merged=[]
    for lo,hi in sorted(spans):
        if not 0<=lo<hi<=1<<19:raise ValueError('expert footprint exceeds source VM ABI')
        if merged and lo<=merged[-1][1]:merged[-1][1]=max(hi,merged[-1][1])
        else:merged.append([lo,hi])
    result=[];base=0
    for i,(lo,hi)in enumerate(merged):result.append(dict(source_words=[lo,hi],vm_words=[base,base+hi-lo],name=f'actual_region_{i}'));base+=hi-lo
    if base>262144:raise ValueError(f'expert source component needs{base}words')
    return result,base


def translate(address,segments):
    for s in segments:
        a,b=s['source_words']
        if a<=address<b:return s['vm_words'][0]+address-a
    raise ValueError(f'expert source pointer lacks bounded region: {address}')


def lower(records,first=1559,last=None):
    if last is None:last=expert_end(records,first)
    segments,high=layout(records,first,last);blob=bytearray();manifest=[]
    for index in range(first,last+1):
        _,r,x,_=records[index];r=copy.deepcopy(r);x=copy.deepcopy(x)
        for d in r.desc.values():
            if d.space=='VM':d.base=translate(d.base,segments)
        if x and x.rsel:x.rtab=translate(x.rtab,segments)
        if(r.unit,r.op)==('CTL','LOOP'):
            if not r.param&(1<<17):raise ValueError('expected native runtime loop count')
            r.imm_a=translate(r.imm_a,segments)
        import isa_rows as IR
        raw=IR.encode(r,x);manifest.append(dict(source_record=index,offset=len(blob),bytes=len(raw)));blob.extend(raw)
    return bytes(blob),dict(schema='opentallas.hbm.vm_expert_entry.v1',source_range=[first,last],segments=segments,high_water_words=high,capacity_words=262144,records=manifest,index_bound=384,rows=6,topk=6,combine_pitch=7,union_capacity=36,table_stride=32,whole_programme_executable=False,scratch_reserved=False,holds=['publish actual source input epochs and retire expert output before workspace reuse','whole-programme dynamic data, numerical RTL and calendar composition remain open'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--first',type=int,default=1559);ap.add_argument('--last',type=int)
    a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import image_check as IC
    source=Path(a.image).read_bytes();blob,packet=lower(IC.decode_all(source),a.first,a.last);packet['source_sha256']=hashlib.sha256(source).hexdigest()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);(out/'expert.hgi1r').write_bytes(blob);(out/'expert.json').write_text(json.dumps(packet,indent=1)+'\n');print(json.dumps(dict(high_water_words=packet['high_water_words'],commands=len(packet['records']),whole_programme_executable=False)))

if __name__=='__main__':main()
