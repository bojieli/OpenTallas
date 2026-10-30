#!/usr/bin/env python3
"""Lower bounded source operations against one canonical HBM VM backing image.

This conservative source compiler preserves instruction/row order. It trades
memory traffic/overlap for a bounded old-VM workspace. It is NOT installed by
this tool: backend namespace/stack coverage, scratch reservation, source entry
publication and numerical RTL/calendar qualification remain explicit holds.
"""
import argparse,copy,json,sys,hashlib
import numpy as np
from pathlib import Path
from vm_value_phase import build,engine_span
from vm_expert_entry import lower as expert_lower,expert_end
from vm_phase_shadow import native_capacity


def static_group_end(records,first,last,IR):
    """Largest source prefix with no reverse dependency between row groups.

    Group0's later records move before group3's earlier records. Only those
    inversions need a RAW/WAR/WAW check; conservative descriptor spans include
    implicit attention plan reads. DMA, controls and streams are boundaries.
    """
    reads3=[];writes3=[];end=first
    def overlap(spans,prior):return any(max(a,c)<min(b,d)for a,b in spans for c,d in prior)
    for index in range(first,last+1):
        _,r,x,_=records[index]
        if r.unit in('DMA','CTL')or(r.unit,r.op)==('IDX','UNION')or any(d.space=='STREAM'for d in r.desc.values()):break
        groups={0:([],[]),3:([],[])}
        if(r.unit,r.op)==('IDX','KVUNION'):expanded=[(((r.param>>4)&15),r)]
        else:expanded=IR.expand(r,x)
        for slot,row in expanded:
            group=0 if slot<3 else 3
            if group==3 and slot>=6:raise ValueError('unqualified source row group')
            reads,writes=groups[group];wo=IR.written_operands(row)
            if x and x.rsel:
                if row.unit!='ATT':raise ValueError('unqualified row-table grouping')
                reads.append((x.rtab,x.rtab+32*IR.PLAN_WORDS))
            for name,d in row.desc.items():
                if d.space=='VM':(writes if name in wo else reads).append(engine_span(row,name))
        rd,wr=groups[0]
        if overlap(rd,writes3)or overlap(wr,reads3)or overlap(wr,writes3):break
        reads3+=groups[3][0];writes3+=groups[3][1];end=index
    return end



def source_scope(records):
    """Report programme units from actual row/control evidence, never token rates."""
    accept=[];tokx=[];positions=1
    for index,(_,record,rowx,_) in enumerate(records):
        if rowx:positions=max(positions,rowx.n)
        if(record.unit,record.op)==('CTL','ACCEPT'):accept.append(index)
        if(record.unit,record.op)==('CTL','TOKX'):
            tokx.append(dict(record=index,A_n=record.desc['A'].n if'A'in record.desc else None))
    return dict(kind='MTP_VERIFY' if accept and tokx else 'UNSPECIFIED',
                row_positions=positions,rate_unit='programme_steps_per_second',
                accepted_outputs_data_dependent=bool(accept),
                evidence=dict(ACCEPT_records=accept,TOKX_records=tokx),
                normalization='Observe actual native ACCEPT/TOKX outputs and include draft/seed costs; no fixed acceptance gamma or AR-token equivalence is assumed.')

def compile_stream(records,first,last,backing,IR,RC,emit_dir=None,group_static=False,retain_static=False):
    native_capacity(backing,4*(1<<19));ALL=(1<<len(RC.UNITS))-1
    blob=bytearray();manifest=[];phases=[];source=first
    state=None;pending_expert_writes=None
    if retain_static:
        from vm_static_cache import Values,opaque_expert_writes
        state=Values(backing)
    def resident_bases(o,vals):
        external=[vals[i]for i in o['values']if vals[i]['kind']=='external']
        if state is None or not external:return[]
        anchor=max(external,key=lambda v:v['b']-v['a']);a=anchor['a'];size=o['b']-o['a'];out=[]
        for position in np.flatnonzero(state.vm==state.back[a]):
            c=int(position)-(a-o['a'])
            if not 0<=c<c+size<=262144 or(c-o['a'])%8:continue
            if all(np.array_equal(state.vm[c+v['a']-o['a']:c+v['b']-o['a']],state.back[v['a']:v['b']])for v in external):out.append(c)
        return out
    def allocated(start,count,end):
        if state is None:return build(records,source,end,start,count,IR,[(0,1<<19)])
        try:return build(records,source,end,start,count,IR,[(0,1<<19)],placement_preference=resident_bases)
        except ValueError:return build(records,source,end,start,count,IR,[(0,1<<19)])
    def emit(r,x,kind,**meta):
        nonlocal pending_expert_writes
        q=copy.deepcopy(r)
        if not any(d.space=='STREAM'for k,d in q.desc.items()if k not in IR.written_operands(q)):q.wait|=ALL
        raw=IR.encode(q,x);manifest.append(dict(kind=kind,offset=len(blob),bytes=len(raw),**meta));blob.extend(raw)
        if state is not None:
            if kind in('load','store'):
                a,b=meta['source_words'];u,v=meta['vm_words']
                if kind=='load':state.vm[u:v]=state.back[a:b]
                else:state.back[a:b]=state.vm[u:v]
            elif kind=='body':
                state.body(q,x,meta,pending_expert_writes,IR);pending_expert_writes=None
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
            if state is not None:pending_expert_writes=opaque_expert_writes(records,source,end,IR)
            for seg in p['segments']:transfer('load',*seg['source_words'],seg['vm_words'][0])
            for m in p['records']:
                q,qx,_=IR.decode_one(raw,m['offset']);emit(q,qx,'body',source_record=m['source_record'],source_slots=None,expert_body=True)
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
        if group_static and end==source:end=static_group_end(records,source,last,IR)
        if end>source:
            if any(records[j][2]and(records[j][2].slot0+records[j][2].n)>3 or (records[j][1].unit,records[j][1].op)==('IDX','KVUNION')and((records[j][1].param>>4)&15)>=3 for j in range(source,end+1)):groups=[(0,3),(3,3)]
            else:groups=[(0,3)]
        elif(r.unit,r.op)==('IDX','KVUNION'):groups=[((r.param>>4)&15,(r.param&15)+1)]
        elif x is None:groups=[(0,1)]
        elif x.rsel:
            if r.unit!='ATT':raise ValueError(f'unknown row selection{source}')
            groups=[(x.slot0,x.n)]
        else:groups=[(j,min(3,x.n-j))for j in range(0,x.n,3)]
        prepared=None
        while prepared is None:
            try:prepared=[(start,count,*allocated(start,count,end))for start,count in groups]
            except ValueError:
                if end==source:raise
                end=source+(end-source)//2
        for start,count,raw,p in prepared:
            before=len(manifest)
            loaded=set()
            for m in p['records']:
                if m['source_record']not in loaded:
                    for load in p['boundary_loads']:
                        if load['before_source_record']==m['source_record']:transfer('load',*load['source_words'],load['destination_words'][0])
                    loaded.add(m['source_record'])
                q,qx,_=IR.decode_one(raw,m['offset']);emit(q,qx,'body',source_record=m['source_record'],source_slots=m['slots'])
            emit(RC.Rec('DMA','FENCE'),None,'source_drain')
            for ret in p['retirements']:transfer('store',*ret['source_words'],ret['vm_words'][0])
            emit(RC.Rec('DMA','FENCE'),None,'retirement_drain')
            phases.append(dict(source_range=[source,end],kind='stream_pair'if any(d.space=='STREAM'for d in r.desc.values())else'static',source_slots=[start,start+count],high_water_words=p['high_water_words'],commands=len(manifest)-before,command_range=[before,len(manifest)]))
        source=end+1
    packet=dict(schema='opentallas.hbm.vm_canonical_stream.v1',programme_scope=source_scope(records),source_range=[first,last],backing_range=[backing,backing+4*(1<<19)],phases=phases,records=manifest,native_commands=len(manifest),transfer_bytes=sum(m['hbm_range'][1]-m['hbm_range'][0]for m in manifest if'hbm_range'in m),max_vm_words=max(p['high_water_words']for p in phases),source_order_preserved=not group_static,independent_row_grouping=group_static,resident_placement_preferences=retain_static,whole_programme_executable=False,full_programme_fits=None,scratch_reserved=False,backend_qualified=False,holds=['actual backend DMA stack/VM namespace must cover canonical backing loads and stores','scratch must be reserved and correct source entry epoch published','native source arithmetic/mutable HBM execution and full source calendar need qualification'])
    return bytes(blob),packet


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in('image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=k!='compiler-tools')
    ap.add_argument('--group-static',action='store_true');ap.add_argument('--retain-static',action='store_true')
    ap.add_argument('--backing-base',type=lambda s:int(s,0),required=True);ap.add_argument('--first',type=int,default=0);ap.add_argument('--last',type=int)
    a=ap.parse_args()
    from isa_loader import load_isa
    IR,IC=load_isa(a.compiler_tools)
    from hgi_sim import records as RC
    raw=Path(a.image).read_bytes();records=IC.decode_all(raw);last=len(records)-1 if a.last is None else a.last
    blob,packet=compile_stream(records,a.first,last,a.backing_base,IR,RC,group_static=a.group_static,retain_static=a.retain_static);packet['source_sha256']=hashlib.sha256(raw).hexdigest()
    out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);(out/'stream.hgi1r').write_bytes(blob);(out/'stream.json').write_text(json.dumps(packet,indent=1)+'\n');print(json.dumps({k:packet[k]for k in('source_range','native_commands','transfer_bytes','max_vm_words','backend_qualified','whole_programme_executable')}))

if __name__=='__main__':main()
