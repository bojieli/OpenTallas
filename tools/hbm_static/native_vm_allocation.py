#!/usr/bin/env python3
"""Inventory exact native programme VM operands without inventing residency or ticks.

Encoded records are the address authority. This does not execute a simulator or
turn operation order into a physical clock schedule. Indexed/dynamic operands
remain unresolved until their actual producers are bound.
"""
import argparse
import dataclasses
import hashlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from hgi_sim.records import decode_one


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extent(desc):
    if desc.indexed or desc.dyn_sel or desc.dyn_mul or desc.n_sel or desc.lstride or desc.l1stride:
        return dict(status='runtime indexed/dynamic address requires real source binding')
    if desc.n <= 0 or desc.m <= 0:
        return dict(status='empty/unresolved shape')
    outer = (desc.m-1)*desc.stride
    inner = 0 if desc.ibcast else (desc.n-1)*(desc.istride or 1)
    lo = desc.base + min(0, outer) + min(0, inner)
    hi = desc.base + max(0, outer) + max(0, inner) + 1
    if lo < 0 or hi > 4*65536:
        return dict(status='outside actual main VM; explicit special aperture lowering required', word_begin=lo, word_end=hi)
    return dict(status='static source range, no relocation granted', word_begin=lo, word_end=hi,
                sector_begin=lo//8, sector_end=(hi+7)//8,
                sids=list(range(lo//65536, (hi-1)//65536+1)),
                first_bank=(lo//8)&7, element_word_bytes=4,
                layout_note='native VM32-bit word slots; BF16-valued words are not silently packed')


def inventory(source):
    programme=json.loads(source.read_text())
    records=[];edges=[];last_writer={};external=set();fixed={}
    for layer in programme['layers']:
        for local,item in enumerate(layer['records']):
            raw=bytes.fromhex(item['hex']);rec,end=decode_one(raw,0)
            if end != len(raw) or rec.encode() != raw:
                raise ValueError('Native record decoder roundtrip mismatch')
            ordinal=len(records)
            operands={name:dict(descriptor=dataclasses.asdict(desc),allocation=extent(desc))
                      for name,desc in rec.desc.items() if desc.space=='VM'}
            for name in item.get('reads',[]):
                if name in last_writer:
                    edges.append(dict(producer=last_writer[name],consumer=ordinal,tensor=name,
                                      timing='actual hardware producer/consumer calendar not yet bound'))
                else:external.add(name)
            for name in item.get('writes',[]):last_writer[name]=ordinal
            records.append(dict(ordinal=ordinal,layer=layer['layer'],local_record=local,
                tag=item['tag'],family=item['family'],unit=rec.unit,op=rec.op,predicate=rec.pred,
                param=rec.param,record_sha256=hashlib.sha256(raw).hexdigest(),
                reads=item.get('reads',[]),writes=item.get('writes',[]),operands=operands,
                issue_cycle=None,issue_cycle_authority='OPEN; source order is not a clock timestamp'))
            if layer['layer']==0 and item['family'] in ('hc_pre_norm','hc_mixes','hc_post','attend'):
                fixed[item['tag']]=dict(record=ordinal,unit=rec.unit,op=rec.op,
                   operands={k:v['allocation'] for k,v in operands.items()})
    sources={str(source.relative_to(ROOT)):digest(source),
             'tools/hgi_sim/records.py':digest(ROOT/'tools/hgi_sim/records.py'),
             'tools/hbm_generic_iface.py':digest(ROOT/'tools/hbm_generic_iface.py')}
    return dict(schema='opentallas.hbm.native-vm-allocation-source.v1',profile='frozen_g25_rank0',
      rank=programme['rank'],source_sha256=sources,record_count=len(records),
      authority='Exact encoded native HGI records. Source-version inventory; no change of addresses, implicit copy or timing assumption.',
      VM_geometry=dict(quarters=4,main_words_per_quarter=65536,banks_per_quarter=8,
          word_to_sector='word>>3',sector_to_sid='sector[14:13]',sector_to_bank='sector[2:0]'),
      records=records,dataflow_edges=edges,external_tensor_boundaries=sorted(external),
      layer0_boundary_allocations=fixed,
      integration_requirements=[
        'Frozen G25 rank0 source and newer Layout literals differ; do not combine source profiles.',
        'This per-rank programme is one head, one position; H16/P8 component maxima require explicit versioned grouping, no inferred tensor replication.',
        'Actual ATT fixed NE SID3 interfaces cannot access canonical SID0 tensors without implemented explicit transport or versioned relocation with all producers/consumers.',
        'Actual HC whole32bank residual assembly must match canonical contiguous h/RES SID0; do not replace with striped component fixtures.',
        'HC native row ownership floor(24*rank/96)..floor(24*(rank+1)/96); rank0 rows are disabled, not a 24-row projection producer.',
        'Global fixed read/write owner reservations and measured stage launch/capture/commit epochs remain to be bound to real instruction producers.'
      ],wholekernel_qualified=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'results/arch/hgi_sim_20261010/g25_proof/ds_rank0_program.json')
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    result=inventory(args.source.resolve());args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2)+'\n')
    print(f"PASS exact decoder roundtrip {result['record_count']} records; {len(result['dataflow_edges'])} source tensor edges; physical calendar OPEN")
