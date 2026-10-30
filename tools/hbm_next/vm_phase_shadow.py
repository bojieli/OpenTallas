#!/usr/bin/env python3
"""Emit native whole-sector prefetch and retirement around finite VM phases.

An immutable entry snapshot and separate per-phase output banks prevent a phase
from overwriting another phase's pending input epoch. This is a component ABI;
the full programme must publish the right value epoch and consume the outputs.
"""
import argparse,copy,json,sys
from pathlib import Path


def epoch_plan(phases,raws,original,base,bank_bytes,IR):
    """Resolve boundary sectors against the ORIGINAL all-six-row write order."""
    import numpy as np
    from vm_value_phase import engine_span
    by_anchor={};phase_of={p['start_row']+j:p['start_row']for p in phases for j in range(p['rows'])}
    for ph in phases:
        for load in ph['boundary_loads']:
            by_anchor.setdefault(tuple(load['source_anchor'][:2]),[]).append((ph,load))
    current=np.full(1<<19,-1,np.int32);requirements={};dependencies=[]
    first=min(m['source_record']for p in phases for m in p['records']);last=max(m['source_record']for p in phases for m in p['records'])
    for index in range(first,last+1):
        _,r,x,_=original[index]
        for slot,row in IR.expand(r,x):
            for ph,load in by_anchor.get((index,slot),[]):
                a,b=load['source_words']
                for sector in range(a,b,8):
                    ids=np.unique(current[sector:sector+8]);producers=[int(v)for v in ids if v>=0]
                    anchor=max(producers)if producers else None
                    key=(ph['start_row'],tuple(load['source_anchor']),sector)
                    if anchor is not None:
                        rec,source_slot=divmod(anchor,16);provider=phase_of[source_slot]
                        if provider>=ph['start_row']:raise ValueError('source epoch is cyclic or not an external earlier phase')
                        requirements[key]=(provider,rec,source_slot,sector)
                        dependencies.append(dict(consumer_phase=ph['start_row'],before_source_record=index,consumer_slot=slot,source_sector=sector,provider_phase=provider,producer_record=rec,producer_slot=source_slot))
            for k in IR.written_operands(row):
                if k in row.desc and row.desc[k].space=='VM':
                    a,b=engine_span(row,k);current[a:b]=index*16+slot
    epochbase=base+3*bank_bytes;publications=[];locations={}
    unique=sorted(set(requirements.values()))
    for number,(provider,index,slot,sector)in enumerate(unique):
        ph=next(p for p in phases if p['start_row']==provider);raw=raws[provider];found=None
        for meta in ph['records']:
            if meta['source_record']!=index:continue
            q,x,_=IR.decode_one(raw,meta['offset'])
            for emitted_slot,row in IR.expand(q,x):
                if emitted_slot!=slot:continue
                source=dict(IR.expand(original[index][1],original[index][2]))[slot]
                for k in IR.written_operands(source):
                    if k not in source.desc or source.desc[k].space!='VM':continue
                    a,b=engine_span(source,k)
                    if max(a,sector)<min(b,sector+8):
                        vm=sector+row.desc[k].base-source.desc[k].base
                        if vm%8 or not 0<=vm<vm+8<=262144:raise ValueError('epoch lacks physical sector ownership')
                        found=vm
        if found is None:raise ValueError('producer epoch has no actual native output')
        addr=epochbase+32*number;locations[(provider,index,slot,sector)]=addr
        publications.append(dict(provider_phase=provider,after_source_record=index,producer_slot=slot,source_words=[sector,sector+8],vm_words=[found,found+8],hbm_range=[addr,addr+32]))
    loads={}
    for ph in phases:
        resolved=[]
        for load in ph['boundary_loads']:
            a,b=load['source_words'];dst=load['destination_words'][0]
            for sector in range(a,b,8):
                req=requirements.get((ph['start_row'],tuple(load['source_anchor']),sector))
                hb=locations[req]if req else base+4*sector
                entry=dict(source_words=[sector,sector+8],destination_words=[dst+sector-a,dst+sector-a+8],before_source_record=load['before_source_record'],source_epoch='producer'if req else'entry',hbm_range=[hb,hb+32])
                # Merge only consecutive same-epoch, same-translation transfers.
                if resolved and all(resolved[-1][k]==entry[k]for k in('before_source_record','source_epoch'))and resolved[-1]['source_words'][1]==sector and resolved[-1]['destination_words'][1]==entry['destination_words'][0]and resolved[-1]['hbm_range'][1]==hb:
                    for k in('source_words','destination_words','hbm_range'):resolved[-1][k][1]=entry[k][1]
                else:resolved.append(entry)
        loads[ph['start_row']]=resolved
    # A caller can select the phase-private final sector by the last canonical
    # writer, instead of replaying phase outputs over each other's input epochs.
    finals=[];selected=set()
    for ph in phases:
        for ret in ph['retirements']:
            for sector in range(*ret['source_words'],8):selected.add(sector)
    for sector in sorted(selected):
        ids=current[sector:sector+8];writers=[int(v)for v in ids if v>=0]
        if not writers:continue
        rec,slot=divmod(max(writers),16);provider=phase_of[slot];ph=next(p for p in phases if p['start_row']==provider)
        if not any(a<=sector<sector+8<=b for a,b in(ret['source_words']for ret in ph['retirements'])):raise ValueError('final source sector has no retained output')
        pi=next(i for i,p in enumerate(phases)if p['start_row']==provider);addr=base+(pi+1)*bank_bytes+4*sector
        item=dict(source_words=[sector,sector+8],phase=provider,hbm_range=[addr,addr+32])
        if finals and finals[-1]['phase']==provider and finals[-1]['source_words'][1]==sector and finals[-1]['hbm_range'][1]==addr:
            finals[-1]['source_words'][1]+=8;finals[-1]['hbm_range'][1]+=32
        else:finals.append(item)
    return loads,publications,dict(dependencies=dependencies,producer_epoch_range=[epochbase,epochbase+32*len(unique)],final_output_sectors=finals)

def compile_phase(ph,raw,base,bank_bytes,phase_index,IR,RC,resolved_loads=None,publications=()):
    if base%32 or base<0 or base>>37 or (base+3*bank_bytes-1)>>37:
        raise ValueError('scratch must be aligned native LINEAR HBM (stripe code0)')
    if bank_bytes<4*(1<<19)or bank_bytes%32:raise ValueError('snapshot bank too small for source VM ABI')
    outbase=base+(phase_index+1)*bank_bytes
    all_wait=(1<<len(RC.UNITS))-1
    # Decode directly: each source fragment record is already pinned by offsets.
    blob=bytearray();manifest=[];seen=set()
    def emit(r,x,kind,**meta):
        encoded=IR.encode(r,x);manifest.append(dict(kind=kind,offset=len(blob),bytes=len(encoded),**meta));blob.extend(encoded)
    def transfer(kind,old_lo,old_hi,new_lo,hbm_override=None):
        words=old_hi-old_lo
        if old_lo%8 or words%8 or new_lo%8 or not 0<=new_lo<new_lo+words<=262144:
            raise ValueError('transfer must own whole sectors inside old VM')
        vm=RC.MDesc(space='VM',fmt='U32',base=new_lo,n=words,m=1)
        hb=RC.MDesc(space='HBM',fmt='U32',base=hbm_override if hbm_override is not None else(base if kind=='load'else outbase)+4*old_lo,n=words,m=1)
        desc={'A':hb,'O':vm}if kind=='load'else{'A':vm,'O':hb}
        emit(RC.Rec('DMA','LOAD'if kind=='load'else'STORE',wait=all_wait,desc=desc),None,kind,
             source_words=[old_lo,old_hi],vm_words=[new_lo,new_lo+words],hbm_range=[hb.base,hb.base+words*4])
    for record_position,recmeta in enumerate(ph['records']):
        index=recmeta['source_record']
        if index not in seen:
            for load in(ph['boundary_loads']if resolved_loads is None else resolved_loads):
                if load['before_source_record']==index:
                    transfer('load',*load['source_words'],load['destination_words'][0],load.get('hbm_range',[None])[0])
            seen.add(index)
        a=recmeta['offset'];r,x,end=IR.decode_one(raw,a)
        if end-a!=recmeta['bytes']:raise ValueError('source fragment record boundary mismatch')
        r.wait |= all_wait
        emit(r,x,'body',source_record=index,slots=recmeta['slots'])
        if record_position+1==len(ph['records'])or ph['records'][record_position+1]['source_record']!=index:
            for pub in publications:
                if pub['provider_phase']==ph['start_row']and pub['after_source_record']==index:
                    transfer('epoch_store',*pub['source_words'],pub['vm_words'][0],pub['hbm_range'][0])
    emit(RC.Rec('DMA','FENCE',wait=all_wait),None,'source_drain')
    for ret in ph['retirements']:transfer('store',*ret['source_words'],ret['vm_words'][0])
    emit(RC.Rec('DMA','FENCE',wait=all_wait),None,'retirement_drain')
    return bytes(blob),dict(slot0=ph['start_row'],native_records=len(manifest),records=manifest,
                            input_snapshot=[base,base+bank_bytes],output_bank=[outbase,outbase+bank_bytes],
                            high_water_words=ph['high_water_words'],shared_weight_sm_rows=ph['shared_weight_sm_rows_preserved'],
                            transferred_bytes=sum(m['hbm_range'][1]-m['hbm_range'][0]for m in manifest if 'hbm_range'in m),
                            serial_unit_barriers=True,unpriced_overlap_loss=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('values','image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    ap.add_argument('--scratch-base',type=lambda x:int(x,0),required=True);a=ap.parse_args()
    p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import isa_rows as IR,image_check as IC
    from hgi_sim import records as RC
    valuepath=Path(a.values);packet=json.loads(valuepath.read_text());out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True);phases=[]
    raws={p['start_row']:(valuepath.parent/p['fragment']).read_bytes()for p in packet['phases']}
    resolved,publications,epochs=epoch_plan(packet['phases'],raws,IC.decode_all(Path(a.image).read_bytes()),a.scratch_base,4*(1<<19),IR)
    for index,ph in enumerate(packet['phases']):
        raw=(valuepath.parent/ph['fragment']).read_bytes();blob,info=compile_phase(ph,raw,a.scratch_base,4*(1<<19),index,IR,RC,resolved[ph['start_row']],publications)
        name=f'shadow_{ph["start_row"]}.hgi1r';(out/name).write_bytes(blob);info['fragment']=name;phases.append(info)
    result=dict(schema='opentallas.hbm.vm_phase_shadow.v1',executable_component_requires_input_epoch=True,
                whole_programme_executable=False,full_programme_fits=None,scratch_reserved=False,
                source_image_sha256=packet['source_sha256'],phases=phases,source_epochs=epochs,
                holds=['caller must reserve actual HBM scratch and publish the correct immutable entry epoch',
                       'bounded source slice cross-phase epochs are resolved; all other programme regions still need composition',
                       'caller must consume declared retired outputs; dynamic live-out set remains unresolved',
                       'price serial unit drains and explicit byte traffic on the current source calendar'])
    (out/'shadow.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(native_records=[p['native_records']for p in phases],transferred_bytes=sum(p['transferred_bytes']for p in phases),scratch_reserved=False)))

if __name__=='__main__':main()
