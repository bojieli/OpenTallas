#!/usr/bin/env python3
"""Extract actual120 matrix placements without inventing native operation homes."""
import argparse
import gzip
import json
from pathlib import Path
from native_stage_lowering import sha


def census(directory):
    directory = Path(directory)
    pins = {p: sha(directory/p) for p in
            ('matrix_map.jsonl.gz', 'stage_map.json', 'inventory.json')}
    if pins['matrix_map.jsonl.gz'] != 'd9f84be93d9d701b445ffd70d0c2f3f54e78d1b2f9a54111a22355abc540da56':
        raise ValueError('actual120 canonical matrix SHA changed')
    inventory = json.loads((directory/'inventory.json').read_text())
    count = inventory['stages']
    if count != 120:
        raise ValueError('this census is for the actual120 candidate only')
    stage_map = json.loads((directory/'stage_map.json').read_text())
    if (inventory['TP'] != 4 or inventory['layer_dies'] != 4*count or
        len(stage_map['PHW_required_by_stage']) != count or
        {(d['stage'],d['rank'],d['die_id']) for d in stage_map['rank_dies']} !=
        {(s,r,4*s+r) for s in range(count) for r in range(4)}):
        raise ValueError('actual120 rank/die allocation mismatch')
    stages = [{'stage':s,'flavour':stage_map['stage_flavour'][str(s)]
               if isinstance(stage_map['stage_flavour'],dict) else stage_map['stage_flavour'][s],
               'matrices':[], 'native_operations':None, 'vm_regions':None}
              for s in range(count)]
    seen = set()
    with gzip.open(directory/'matrix_map.jsonl.gz', 'rt') as stream:
        for line in stream:
            m = json.loads(line)
            identity = (m['layer'],m['alias'])
            if identity in seen or not 0 <= m['stage'] < count:
                raise ValueError('duplicate or out-of-stage matrix identity')
            seen.add(identity)
            stages[m['stage']]['matrices'].append({k:m.get(k) for k in
                ('layer','alias','format','K','expert','conversion')})
    layers = [{'layer':int(layer), 'matrix_stages':assigned,
               'dense_stage':stage_map['dense_stage'][layer],
               'provider_home':stage_map['provider_homes'][layer],
               'scan_home':stage_map['scan_service_homes'].get(layer),
               'source_operation_schedule':None,
               'expert_dense_concurrency_binding':None,
               'h_pf_multicast_materialization':None}
              for layer,assigned in sorted(stage_map['layer_matrix_stages'].items(),
                                           key=lambda kv:int(kv[0]))]
    return {'schema':'opentallas.s81.native120.allocation-census.v1',
            'status':'MATRIX_PLACEMENTS_VERIFIED_OPERATION_BINDINGS_MISSING',
            'candidate_only':True, 'adopted':False, 'allocation_sha256':pins,
            'stages':stages, 'layers':layers,
            'scan_service_home_provisional':stage_map['scan_home_is_provisional_not_source_service_binding'],
            'native_executed_transfer_count':None,
            'remaining_bindings':['complete canonical operation identities and dependencies',
                'actual emitted CFG field phase numbers, BF lane transport',
                'dynamic COEF/NORM VM regions and two-slot nonaliasing',
                'actual POST spill and reload before each VM reader',
                'PF4 dynamic producer and source-bound 40976-byte boundary',
                'dense/expert source concurrency and service ownership',
                'GAIN boot-completion fence independent of artificial PGAP']}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();result=census(args.binding)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    payload = json.dumps(result,separators=(',',':'))+'\n'
    if args.out.suffix == '.gz':
        with gzip.open(args.out,'wt') as stream: stream.write(payload)
    else:
        args.out.write_text(payload)
