#!/usr/bin/env python3
"""Inventory actual serialized DS HGI Quant records without inventing clocks.

Reads committed full-rank0 token and per-rank layer exports. These establish
operation/descriptor evidence only; current RTL binding, global timestamps,
residency and all-rank full-token coverage are deliberately separate obligations.
"""
import argparse
import collections
import dataclasses
import hashlib
import json
import subprocess
from pathlib import Path
from hgi_sim.records import decode_one
from hgi_static_quant_calendar import lower_record

SOURCES=[
 ('full_rank0_released_listing','results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json'),
 ('full_rank0_g24','results/arch/hgi_sim_20261010/g24_proof/ds_rank0_program.json'),
 ('full_rank0_g25','results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json'),
 ('full_rank0_fused','results/rtl/hbm_forks_20261009/ds_fused_rank0_program.json'),
 ('allrank_layer00','results/arch/hgi_sim_20261009/programs/ds_v41_1M_L00_per_die.json'),
 ('allrank_layer20','results/arch/hgi_sim_20261009/programs/ds_v41_1M_L20_per_die.json'),
 ('stacked_layer00','results/rtl/tput_map_1011/hbm_smmv_xp/compiler_stacked_1013/images/ds_v41_1M_L00_per_die.json'),
 ('stacked_layer01','results/rtl/tput_map_1011/hbm_smmv_xp/compiler_stacked_1013/images/ds_v41_1M_L01_per_die.json')]


def reference(rows,index):
    r,x=rows[index]
    return dict(index=index,unit=r.unit,op=r.op,tag=x.get('tag',''),
                source_sha256=hashlib.sha256(bytes.fromhex(x['hex'])).hexdigest())


def streams(doc):
    if 'ranks' in doc:
        for rank in doc['ranks']:
            image=bytes.fromhex(rank['image_hex'])
            assert hashlib.sha256(image).hexdigest()==rank['image_sha256']
            off=0;rows=[];i=0
            tags=rank.get('record_tags',[])
            while off<len(image):
                start=off;r,off=decode_one(image,off)
                rows.append((r,dict(hex=image[start:off].hex(),tag=tags[i] if i<len(tags) else '',reads=[],writes=[])))
                i+=1
            yield rank['rank'],doc['layer'],rows
    else:
        for layer in doc['layers']:
            rows=[]
            for x in layer['records']:
                raw=bytes.fromhex(x['hex']);r,end=decode_one(raw,0)
                assert end==len(raw)
                rows.append((r,x))
            yield doc['rank'],layer['layer'],rows


def inventory(rows,profile,path,rank,layer):
    entries=[]
    for i,(r,x) in enumerate(rows):
        if r.unit!='FUSED' or not r.op.startswith('QDQ'):continue
        sids=sorted({d.base>>16 for d in r.desc.values() if d.space=='VM'})
        support=[]
        for sid in range(4):
            try:
                # Zero here is a shape-validator argument, never emitted as an
                # issue timestamp. No issue_cycle field exists in the inventory.
                beats=lower_record(r,0,sid)
                support.append(dict(resident_sid=sid,shape_supported=True,beats=len(beats),
                                    compact_contiguous=all(c['src']==beats[0]['src']+4*j and c['dst']==beats[0]['dst']+4*j for j,c in enumerate(beats))))
            except ValueError as e:support.append(dict(resident_sid=sid,shape_supported=False,reason=str(e)))
        good=[v for v in support if v['shape_supported']]
        previous=[];following=[]
        # Original source symbolic buffer dependencies are carried if present;
        # interval intersections additionally identify real serialized operands.
        for j,(p,px) in enumerate(rows[:i]):
            if set(px.get('writes',[]))&set(x.get('reads',[])):
                previous.append(reference(rows,j))
        for j in range(i+1,len(rows)):
            p,px=rows[j]
            if set(x.get('writes',[]))&set(px.get('reads',[])):
                following.append(reference(rows,j))
        a=r.desc.get('A');o=r.desc.get('O')
        if a and not previous:
            for j,(p,px) in enumerate(rows[:i]):
                pd=p.desc.get('O')
                if pd and pd.space==a.space and pd.base<=a.base<pd.base+pd.n*pd.m:
                    previous.append(reference(rows,j))
        if o and not following:
            for j in range(i+1,len(rows)):
                p,px=rows[j]
                if any(dd.space==o.space and dd.base<=o.base<dd.base+dd.n*dd.m for name,dd in p.desc.items() if name!='O'):
                    following.append(reference(rows,j))
        entries.append(dict(id=f'{profile}:rank{rank}:L{layer}:record{i}',source_path=path,
            source_profile=profile,rank=rank,layer=layer,record_index=i,
            record_hex=x['hex'],record_sha256=hashlib.sha256(bytes.fromhex(x['hex'])).hexdigest(),
            tag=x.get('tag',''),family=x.get('family',''),op=r.op,predicate=r.pred,wait_mask=r.wait,
            param=r.param,descriptors={name:dataclasses.asdict(d) for name,d in r.desc.items()},
            original_vm_sids=sids,lowerer_checks=support,
            actual_quant_quadrant='NW',actual_quant_vm_sid=2,
            original_residency_matches_actual_quant=any(v['resident_sid']==2 for v in good),
            required_real_residency_work='none for original SID2 descriptor; still allocation/calendar ownership required' if any(v['resident_sid']==2 for v in good) else 'source SID0 read/staging into actual NW SID2 before Quant, actual result publication back to declared consumer SID; no modulo relocation',
            shape_status='SUPPORTED_AT_ORIGINAL_SID' if good else 'UNSUPPORTED_ORIGINAL_DESCRIPTOR',
            production_qualified=False,
            storage_requirement='streaming32FP32 sectors through actual VM; no Quant private PAY store for this descriptor class' if good else 'native redesign/staging required; never route to legacy dynamic fallback',
            nearest_source_producer=previous[-1] if previous else None,
            first_source_consumer=following[0] if following else None,
            missing_authority=[
                'actual native global issue timestamp and predecessor result visibility/commit cycles',
                'authoritative Quant NW VM SID and actual local operand allocation or real scheduled staging transfer',
                'source-pinned executed compact Quant/NW bank-calendar image bound to this source record',
                'actual physical bank/station and producer/consumer clock phase latencies',
                'full native producer/SU or collective and consumer/DMA source binding, including their storage',
                'global dependency-loop execution context and whole-token coverage across all ranks']))
    return entries


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ref',default='origin/main');ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    commit=subprocess.check_output(['git','rev-parse',a.ref],text=True).strip()
    records=[];sources=[];fused=[]
    for profile,path in SOURCES:
        data=subprocess.check_output(['git','show',f'{commit}:{path}']);doc=json.loads(data)
        start=len(records);groups=[];allops=collections.Counter();nonqdq=collections.Counter()
        for rank,layer,rows in streams(doc):
            selected=inventory(rows,profile,path,rank,layer)
            records+=selected;groups.append(dict(rank=rank,layer=layer,total_records=len(rows),quant_records=len(selected)))
            for r,x in rows:
                allops[(r.unit,r.op)]+=1
                if r.unit=='FUSED' and not r.op.startswith('QDQ'):
                    nonqdq[r.op]+=1
                    fused.append(dict(source_profile=profile,source_path=path,rank=rank,layer=layer,op=r.op,
                        tag=x.get('tag',''),record_hex=x['hex'],descriptors={k:dataclasses.asdict(v) for k,v in r.desc.items()},
                        quant_replacement_coverage=False,
                        missing='Actual native fused/SU/HC/mover implementation and PAY dependency owned elsewhere; QDQ decoder does not implement this operation'))
        entries=records[start:]
        sources.append(dict(profile=profile,path=path,git_commit=commit,source_sha256=hashlib.sha256(data).hexdigest(),
            source_bytes=len(data),streams=groups,quant_records=len(entries),
            quant_ops=dict(collections.Counter(x['op'] for x in entries)),
            shape_supported=sum(x['shape_status']=='SUPPORTED_AT_ORIGINAL_SID' for x in entries),
            shape_unsupported=sum(x['shape_status']!='SUPPORTED_AT_ORIGINAL_SID' for x in entries),
            original_sid_counts=dict(collections.Counter(str(x['original_vm_sids']) for x in entries)),
            original_residency_matches_actual_NW=sum(x['original_residency_matches_actual_quant'] for x in entries),
            requires_actual_staging_or_allocator_relocation=sum(not x['original_residency_matches_actual_quant'] for x in entries),
            fused_nonqdq_ops=dict(nonqdq)))
    summary=dict(schema='opentallas.hbm-quant-native-record-inventory.v1',source_ref_commit=commit,
        issue_timestamps_invented=False,source_profiles=sources,
        total_export_records_including_distinct_historical_profiles=len(records),
        source_record_hashes_distinct=len({r['record_sha256'] for r in records}),
        full_token_rank_coverage=[0],full_allrank_token_export_found=False,
        native_NW_sid_authority='h_vm confirmation SW0 SE1 NW2 NE3; actual native NW sid2',
        native_global_timestamp_authority_available=False,
        whole_token_paged_VM_calendar_implemented=False,
        full_token_scope='40backbone layers+head only; complete all-rank and MTP continuation exports not present in enumerated sources',
        production_qualified_records=0,
        PAY_status='Static QDQ removes its private legacy transport dependency for supported class only. FUSED non-QDQ and native predecessor/consumer PAY stores remain separate required elements; no system-level PAY retirement proven.',
        gate='Inventory only. No simulation, arithmetic golden result injection, route or completed gate was rerun.')
    for name,value in [('summary',summary),('records',records),('fused_nonqdq',fused)]:
        (a.out/f'{name}.json').write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({s['profile']:dict(records=s['quant_records'],ops=s['quant_ops'],supported=s['shape_supported'],unsupported=s['shape_unsupported']) for s in sources},indent=2))


if __name__=='__main__':main()
