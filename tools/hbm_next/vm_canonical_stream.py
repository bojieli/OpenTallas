#!/usr/bin/env python3
"""Lower bounded source operations against one canonical HBM VM backing image.

This conservative source compiler preserves instruction/row order. It trades
memory traffic/overlap for a bounded old-VM workspace. It is NOT installed by
this tool: backend namespace/stack coverage, scratch reservation, source entry
publication and numerical RTL/calendar qualification remain explicit holds.
"""
import argparse,copy,json,sys,hashlib
from pathlib import Path
from vm_value_phase import build
from vm_expert_entry import lower as expert_lower,expert_end
from vm_phase_shadow import native_capacity


def compile_stream(records,first,last,backing,IR,RC,emit_dir=None):
    native_capacity(backing,4*(1<<19));ALL=(1<<len(RC.UNITS))-1
    blob=bytearray();manifest=[];phases=[];source=first
    def emit(r,x,kind,**meta):
        q=copy.deepcopy(r)
        if not any(d.space=='STREAM'for k,d in q.desc.items()if k not in IR.written_operands(q)):q.wait|=ALL
        raw=IR.encode(q,x);manifest.append(dict(kind=kind,offset=len(blob),bytes=len(raw),**meta));blob.extend(raw)
    def transfer(kind,lo,hi,target):
        if lo%8 or hi%8 or target%8 or not 0<=target<target+hi-lo<=262144:raise ValueError('nonsector or excessive canonical transfer')
        hb=RC.MDesc(space='HBM',fmt='U32',base=backing+lo*4,n=hi-lo,m=1);vm=RC.MDesc(space='VM',fmt='U32',base=target,n=hi-lo,m=1)
        emit(RC.Rec('DMA','LOAD'if kind=='load'else'STORE',desc=dict(A=hb,O=vm)if kind=='load'else dict(A=vm,O=hb)),None,kind,source_words=[lo,hi],vm_words=[target,target+hi-lo],hbm_range=[hb.base,hb.base+4*(hi-lo)])
    while source<=last:
        _,r,x,_=records[source]
        if(r.unit,r.op)==('IDX','UNION'):
            end=expert_end(records,source)
            if end>last:raise ValueError('range ends inside actual expert region')
            raw,p=expert_lower(records,source,end);before=len(manifest)
            for seg in p['segments']:transfer('load',*seg['source_words'],seg['vm_words'][0])
            for m in p['records']:
                q,qx,_=IR.decode_one(raw,m['offset']);emit(q,qx,'body',source_record=m['source_record'],source_slots=None)
            emit(RC.Rec('DMA','FENCE'),None,'source_drain')
            for seg in p['segments']:transfer('store',*seg['source_words'],seg['vm_words'][0])
            emit(RC.Rec('DMA','FENCE'),None,'retirement_drain')
            phases.append(dict(source_range=[source,end],kind='expert',high_water_words=p['high_water_words'],commands=len(manifest)-before,command_range=[before,len(manifest)]));source=end+1;continue
        # Plain fixed control has no workspace. Runtime loops are accepted only
        # inside the already bounded expert source component above.
        if r.unit=='CTL' and r.op not in('ACCEPT','TOKX'):
            if r.op not in('NOP','END','ACCEPT'):raise ValueError(f'unknown standalone control{source}:{r.op}')
            emit(r,x,'body',source_record=source,source_slots=[r.slot]);source+=1;continue
        end=source
        if any(d.space=='STREAM'for k,d in r.desc.items()if k in IR.written_operands(r)):
            if source+1>last or(records[source+1][1].unit,records[source+1][1].op)!=('ARGMAX','LOCAL'):raise ValueError('unknown streamed source coupling')
            consumer=records[source+1][1]
            if consumer.desc['A'].space!='STREAM' or consumer.desc['A'].base!=r.desc['O'].base:raise ValueError('stream source/consumer differs')
            end=source+1
        if(r.unit,r.op)==('IDX','KVUNION'):groups=[((r.param>>4)&15,(r.param&15)+1)]
        elif x is None:groups=[(0,1)]
        elif x.rsel:
            if r.unit!='ATT':raise ValueError(f'unknown row selection{source}')
            groups=[(x.slot0,x.n)]
        else:groups=[(j,min(3,x.n-j))for j in range(0,x.n,3)]
        for start,count in groups:
            before=len(manifest)
            try:raw,p=build(records,source,end,start,count,IR,[(0,1<<19)])
            except ValueError as ex:raise ValueError(f'source{source}/{r.unit}.{r.op}/rows{start}:{start+count}: {ex}')from ex
            for load in p['boundary_loads']:transfer('load',*load['source_words'],load['destination_words'][0])
            for m in p['records']:
                q,qx,_=IR.decode_one(raw,m['offset']);emit(q,qx,'body',source_record=m['source_record'],source_slots=m['slots'])
            emit(RC.Rec('DMA','FENCE'),None,'source_drain')
            for ret in p['retirements']:transfer('store',*ret['source_words'],ret['vm_words'][0])
            emit(RC.Rec('DMA','FENCE'),None,'retirement_drain')
            phases.append(dict(source_range=[source,end],kind='stream_pair'if end!=source else'static',source_slots=[start,start+count],high_water_words=p['high_water_words'],commands=len(manifest)-before,command_range=[before,len(manifest)]))
        source=end+1
    packet=dict(schema='opentallas.hbm.vm_canonical_stream.v1',source_range=[first,last],backing_range=[backing,backing+4*(1<<19)],phases=phases,records=manifest,native_commands=len(manifest),transfer_bytes=sum(m['hbm_range'][1]-m['hbm_range'][0]for m in manifest if'hbm_range'in m),max_vm_words=max(p['high_water_words']for p in phases),source_order_preserved=True,whole_programme_executable=False,full_programme_fits=None,scratch_reserved=False,backend_qualified=False,holds=['actual backend DMA stack/VM namespace must cover canonical backing loads and stores','scratch must be reserved and correct source entry epoch published','native source arithmetic/mutable HBM execution and full source calendar need qualification'])
    return bytes(blob),packet


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--backing-base',type=lambda s:int(s,0),required=True);ap.add_argument('--first',type=int,default=0);ap.add_argument('--last',type=int)
    a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import isa_rows as IR,image_check as IC
    from hgi_sim import records as RC
    raw=Path(a.image).read_bytes();records=IC.decode_all(raw);last=len(records)-1 if a.last is None else a.last
    blob,packet=compile_stream(records,a.first,last,a.backing_base,IR,RC);packet['source_sha256']=hashlib.sha256(raw).hexdigest()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);(out/'stream.hgi1r').write_bytes(blob);(out/'stream.json').write_text(json.dumps(packet,indent=1)+'\n');print(json.dumps({k:packet[k]for k in('source_range','native_commands','transfer_bytes','max_vm_words','backend_qualified','whole_programme_executable')}))

if __name__=='__main__':main()
