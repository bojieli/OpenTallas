#!/usr/bin/env python3
"""Link finite-VM native components by source-sector epochs, without VM copies."""
import argparse,copy,json,sys
from pathlib import Path
import numpy as np
from vm_value_phase import engine_span


def written_sectors(original,first,last,IR):
    mask=np.zeros(1<<19,bool)
    for index in range(first,last+1):
        _,r,x,_=original[index]
        for slot,row in IR.expand(r,x):
            for k in IR.written_operands(row):
                if k in row.desc and row.desc[k].space=='VM':
                    a,b=engine_span(row,k);mask[a:b]=True
    return mask


def route(sector,selector,written,entry):
    if not written[sector:sector+8].any():return entry+4*sector
    for item in selector:
        a,b=item['source_words']
        if a<=sector<sector+8<=b:return item['hbm_range'][0]+4*(sector-a)
    raise ValueError(f'upstream has no published source sector {sector}')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in('upstream','downstream','downstream-values','image','compiler-tools','out-dir'):ap.add_argument('--'+k,required=True)
    a=ap.parse_args();p=Path(a.compiler_tools);sys.path[:0]=[str(p/'hbm_next'),str(p)]
    import isa_rows as IR,image_check as IC
    paths=[Path(a.upstream),Path(a.downstream)];packets=[json.loads(p.read_text())for p in paths]
    for packet in packets:
        if 'source_epoch_checks'in packet:packet['source_epochs']={'dependencies':packet['source_epoch_checks'],'final_output_sectors':packet['final_output_sectors']}
    original=IC.decode_all(Path(a.image).read_bytes());out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
    first=min(m['source_record']for p in packets[0]['phases']for m in p['records']if m['kind']=='body')
    cut=max(m['source_record']for p in packets[0]['phases']for m in p['records']if m['kind']=='body')
    last=max(m['source_record']for p in packets[1]['phases']for m in p['records']if m['kind']=='body')
    nextfirst=min(m['source_record']for p in packets[1]['phases']for m in p['records']if m['kind']=='body')
    if nextfirst!=cut+1:raise ValueError('components do not cover adjacent original source ranges')
    written=written_sectors(original,first,cut,IR);nextwritten=written_sectors(original,nextfirst,last,IR)
    entry=packets[0]['phases'][0]['input_snapshot'][0];phases=[];regions=copy.deepcopy(packets[0].get('memory_regions',[dict(name='entry',range=packets[0]['phases'][0]['input_snapshot'])]));epochs=[];routed_words=0;entry_words=0
    next_stage=max(p.get('stage',0)for p in packets[0]['phases'])+1
    for stage,(path,packet)in enumerate(zip(paths,packets)):
        epochs+=packet['source_epochs']['dependencies']
        if 'producer_epoch_range'in packet['source_epochs']:
            regions.append(dict(name=f'epochs{stage}',range=packet['source_epochs']['producer_epoch_range']))
        for ph in packet['phases']:
            output_stage=ph.get('stage',0)if stage==0 else next_stage
            raw=(path.parent/ph['fragment']).read_bytes();blob=bytearray();manifest=[]
            if not(stage==0 and 'memory_regions'in packet):regions.append(dict(name=f'out{output_stage}_{ph["slot0"]}',range=ph['output_bank']))
            for meta in ph['records']:
                r,x,end=IR.decode_one(raw,meta['offset']);variants=[(r,x,copy.deepcopy(meta))]
                ia,ib=ph['input_snapshot']
                if stage==1 and meta['kind']=='load'and ia<=r.desc['A'].base<ib:
                    variants=[];lo,hi=meta['source_words'];dest=meta['vm_words'][0]
                    groups=[]
                    for sector in range(lo,hi,8):
                        hb=route(sector,packets[0]['source_epochs']['final_output_sectors'],written,entry)
                        if written[sector:sector+8].any():routed_words+=8
                        else:entry_words+=8
                        if groups and groups[-1][1]==sector and groups[-1][2]+4*(groups[-1][1]-groups[-1][0])==hb:groups[-1][1]+=8
                        else:groups.append([sector,sector+8,hb])
                    for begin,finish,hb in groups:
                        q=copy.deepcopy(r);q.desc['A'].base=hb;q.desc['A'].n=finish-begin;q.desc['O'].base=dest+begin-lo;q.desc['O'].n=finish-begin
                        mm=copy.deepcopy(meta);mm.update(source_words=[begin,finish],vm_words=[q.desc['O'].base,q.desc['O'].base+finish-begin],hbm_range=[hb,hb+4*(finish-begin)],linked_upstream_epoch=True)
                        variants.append((q,None,mm))
                for q,qx,mm in variants:
                    enc=IR.encode(q,qx);mm.update(offset=len(blob),bytes=len(enc));manifest.append(mm);blob.extend(enc)
            name=f'stage{output_stage}_{ph["slot0"]}.hgi1r';(out/name).write_bytes(blob)
            item=copy.deepcopy(ph);item.update(stage=output_stage,fragment=name,records=manifest,native_records=len(manifest));phases.append(item)
    # Select all statically declared final boundary sectors, including untouched
    # input values, from the newest actual source writer's publication bank.
    boundary=json.loads(Path(a.downstream_values).read_text())['boundary']['known_boundary_intervals'];selected=set()
    for lo,hi in boundary:selected.update(range(lo//8*8,(hi+7)//8*8,8))
    finals=[]
    for sector in sorted(selected):
        if nextwritten[sector:sector+8].any():hb=route(sector,packets[1]['source_epochs']['final_output_sectors'],nextwritten,entry)
        else:hb=route(sector,packets[0]['source_epochs']['final_output_sectors'],written,entry)
        if finals and finals[-1]['source_words'][1]==sector and finals[-1]['hbm_range'][1]==hb:finals[-1]['source_words'][1]+=8;finals[-1]['hbm_range'][1]+=32
        else:finals.append(dict(source_words=[sector,sector+8],hbm_range=[hb,hb+32]))
    result=dict(schema='opentallas.hbm.vm_native_chain.v1',source_range=[first,last],entry_snapshot=regions[0]['range'],memory_regions=regions,phases=phases,source_epoch_checks=epochs,final_output_sectors=finals,routed_upstream_words=routed_words,unchanged_entry_words=entry_words,whole_programme_executable=False,full_programme_fits=None,scratch_reserved=False,
                holds=['publish actual entry value epoch and reserve real scratch', 'numerical RTL execution, mutable HBM effects and dynamic remaining regions still need full composition','price native drains, source issue and data movement before adoption'])
    (out/'chain.json').write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(dict(source_range=result['source_range'],commands=sum(p['native_records']for p in phases),routed_words=routed_words,unchanged_entry_words=entry_words)))

if __name__=='__main__':main()
