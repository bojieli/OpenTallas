#!/usr/bin/env python3
"""Relocate the actual six-row expert UNION/indexed/LOOP entry, preserving rsel.

This is a bounded source component, not an executable whole-programme image.
The declared indexed extent comes from the actual preceding producer1560 reads.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path


def layout(records):
    union=records[1559][1];indexed=records[1560][1];producer,px=records[1554][1:3]
    if(union.unit,union.op,indexed.unit,indexed.op)!=('IDX','UNION','SU','VOP'):raise ValueError('source expert entry changed')
    if not indexed.desc['A'].indexed or indexed.desc['A'].dyn_mul!=1:raise ValueError('indexed source contract changed')
    if producer.desc['O'].base!=indexed.desc['A'].base or producer.desc['O'].n!=384 or px.n!=6 or px.rs['O']!=384:raise ValueError('indexed extent lacks actual six-row producer')
    ranges=[(147696,147744,'combine_weights'),(270592,375040,'expert_workspace'),(483552,484800,'union_count_table'),(506112,506160,'ids')]
    result=[];base=0
    for lo,hi,name in ranges:
        base=(base+31)//32*32;result.append(dict(source_words=[lo,hi],vm_words=[base,base+hi-lo],name=name));base+=hi-lo
    return result,base


def translate(address,segments):
    for s in segments:
        a,b=s['source_words']
        if a<=address<b:return s['vm_words'][0]+address-a
    raise ValueError(f'expert source pointer lacks bounded region: {address}')


def lower(records):
    segments,high=layout(records);blob=bytearray();manifest=[]
    for index in range(1559,1591):
        _,r,x,_=records[index];r=copy.deepcopy(r);x=copy.deepcopy(x)
        for d in r.desc.values():
            if d.space=='VM':d.base=translate(d.base,segments)
        if x and x.rsel:x.rtab=translate(x.rtab,segments)
        if(r.unit,r.op)==('CTL','LOOP'):
            if not r.param&(1<<17):raise ValueError('expected native runtime loop count')
            r.imm_a=translate(r.imm_a,segments)
        import isa_rows as IR
        raw=IR.encode(r,x);manifest.append(dict(source_record=index,offset=len(blob),bytes=len(raw)));blob.extend(raw)
    return bytes(blob),dict(schema='opentallas.hbm.vm_expert_entry.v1',source_range=[1559,1590],segments=segments,high_water_words=high,capacity_words=262144,records=manifest,index_bound=384,rows=6,topk=6,combine_pitch=7,union_capacity=36,table_stride=32,whole_programme_executable=False,scratch_reserved=False,holds=['publish actual source input epochs and retire expert output before workspace reuse','whole-programme dynamic data, numerical RTL and calendar composition remain open'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import image_check as IC
    source=Path(a.image).read_bytes();blob,packet=lower(IC.decode_all(source));packet['source_sha256']=hashlib.sha256(source).hexdigest()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);(out/'expert.hgi1r').write_bytes(blob);(out/'expert.json').write_text(json.dumps(packet,indent=1)+'\n');print(json.dumps(dict(high_water_words=packet['high_water_words'],commands=len(packet['records']),whole_programme_executable=False)))

if __name__=='__main__':main()
