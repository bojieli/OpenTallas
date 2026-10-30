#!/usr/bin/env python3
"""Relocate real three-lane KVUNION/QK/SU/PV phases without splitting plan lanes.

Native fragments retain actual NL3, slot groups, plan dimensions and HBM
operands. Boundary publication and whole-programme scheduling remain separate.
"""
import argparse,copy,hashlib,json,sys
from pathlib import Path


def conservative_span(d):
    if any(getattr(d,k,0) for k in ('indexed','dyn_sel','n_sel','lstride','l1stride')):
        raise ValueError('dynamic descriptor outside bounded attention-plan contract')
    if d.stride<0 or d.istride not in (0,1):raise ValueError('unsupported descriptor stride')
    size=max(d.n*max(1,d.m),(max(1,d.m)-1)*d.stride+(d.n-1)*max(1,d.istride)+1)
    return d.base,d.base+size


def merge(intervals):
    out=[]
    for a,b in sorted(intervals):
        if out and a<=out[-1][1]:out[-1][1]=max(b,out[-1][1])
        else:out.append([a,b])
    return out


def construct(records,group,IR,capacity=262144,reserve=0):
    if group not in (0,3):raise ValueError('actual source has exactly NL3 slot groups0/3')
    indices=[1528+group//3,1530+group//3,1532,1533,1534,1535+group//3]
    originals=[];ivs=[]
    for index in indices:
        _,r,x,_=records[index];q=copy.deepcopy(r);qx=copy.deepcopy(x)
        if q.unit=='IDX':
            if q.op!='KVUNION' or (q.param&15)+1!=3 or ((q.param>>4)&15)!=group:
                raise ValueError('actual IDX plan no longer matches NL3 group')
        elif q.unit=='ATT':
            if not qx.rsel or qx.n!=3 or qx.slot0!=group or qx.emask:
                raise ValueError('requires actual bounded three-lane attention plan mode')
        else:
            if qx is None or qx.rsel or qx.n!=6 or qx.slot0!=0:
                raise ValueError('requires actual six-row scalar stage')
            qx.n=3;qx.slot0=group;q.slot=group&7
            for k,d in q.desc.items():d.base+=group*(x.rs.get(k,0)<<(x.hsh if d.space=='HBM' else 0))
        if qx:
            conflict=IR.check_rows_independent(q,qx)
            if conflict:raise ValueError(f'source rows are not independent: {conflict}')
        rows=IR.expand(q,qx)
        for _,row in rows:
            for d in row.desc.values():
                if d.space=='VM':ivs.append(conservative_span(d))
        originals.append((index,q,qx))
    producer=originals[0][1]
    if producer.desc['R'].n!=IR.PLAN_WORDS or producer.desc['R'].m!=32:
        raise ValueError('plan dimension changed')
    old_table=producer.desc['R'].base
    if any(x.rtab!=old_table for _,r,x in originals if r.unit=='ATT'):
        raise ValueError('attention table lacks this actual producer')
    mapping=[];cursor=reserve
    for a,b in merge(ivs):
        # Preserve all modulo32 addresses, including implicit rtab references.
        cursor += (a-cursor)%32
        mapping.append(dict(source=[a,b],destination=[cursor,cursor+b-a]));cursor+=b-a
    if cursor>capacity:raise ValueError(f'attention phase needs {cursor} words > {capacity}')
    def remap(value):
        for item in mapping:
            a,b=item['source']
            if a<=value<b:return item['destination'][0]+value-a
        raise ValueError('unmapped implicit plan or explicit descriptor')
    native=[];blob=bytearray();checks=0
    for index,r,x in originals:
        q=copy.deepcopy(r);qx=copy.deepcopy(x)
        before=IR.expand(r,x)
        for k,d in q.desc.items():
            if d.space=='VM':
                mapped=[remap(row.desc[k].base)for _,row in before]
                d.base=mapped[0]
                if qx and len(mapped)>1:
                    step={mapped[i]-mapped[i-1]for i in range(1,len(mapped))}
                    if len(step)!=1:raise ValueError('mapped row bases not affine')
                    qx.rs[k]=step.pop()
        if q.unit=='ATT':qx.rtab=remap(x.rtab)
        IR.check(q,qx)
        if qx and IR.check_rows_independent(q,qx):raise ValueError('mapped row dependency')
        after=IR.expand(q,qx)
        for (slot,orig),(newslot,actual) in zip(before,after):
            expected=copy.deepcopy(orig)
            for d in expected.desc.values():
                if d.space=='VM':d.base=remap(d.base)
            if slot!=newslot or vars(expected)!=vars(actual):raise ValueError('native expanded semantics changed')
            checks+=1
        encoded=IR.encode(q,qx);native.append(dict(source_record=index,offset=len(blob),bytes=len(encoded),native_hex=encoded.hex()))
        blob.extend(encoded)
    return bytes(blob),dict(group_slot0=group,nl=3,vm_high_water_words=cursor,external_reserve_words=reserve,
                            free_words=capacity-cursor,source_table=old_table,mapped_table=remap(old_table),
                            plan_words=producer.desc['R'].n*producer.desc['R'].m,lane_map_words=producer.desc['D'].n,
                            source_intervals=mapping,records=native,expanded_rows_checked=checks,
                            arithmetic_alias_slots_hbm_and_plan_lanes_preserved=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--reserve',type=int,default=0);a=ap.parse_args()
    p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import isa_rows as IR,image_check as IC
    raw=Path(a.image).read_bytes();rr=IC.decode_all(raw);out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);phases=[]
    for group in (0,3):
        blob,info=construct(rr,group,IR,reserve=a.reserve);name=f'attention_{group}.hgi1r';(out/name).write_bytes(blob);info['fragment']=name;phases.append(info)
    packet=dict(schema='opentallas.hbm.vm_nl3_phase.v1',executable=False,full_programme_fits=None,
                source_image_sha256=hashlib.sha256(raw).hexdigest(),phases=phases,
                holds=['publish boundary inputs and retire outputs across actual producer phases',
                       'outside live values must fit reserved space or be explicitly spilled',
                       'native programme source and physical plan calendar must be composed before adoption'])
    (out/'attention.json').write_text(json.dumps(packet,indent=1)+'\n')
    print(json.dumps(dict(status='NATIVE_NL3_PHASES_READY',high_water=[p['vm_high_water_words']for p in phases],reserve=a.reserve)))

if __name__=='__main__':main()
