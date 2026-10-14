#!/usr/bin/env python3
"""Lower source-bound stage operations to the real 28-bit stage program.

The operation placement and endpoint arguments are explicit compiler inputs.
This module never uses price durations, graph groups or physical capacity as
operation placement. HALF_PHL is an opt-in candidate; the existing81 source
allocation is unchanged. Accepted transfers are counted at t_head at runtime,
not by counting the generated descriptors.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def load_binding(directory, pins):
    directory = Path(directory)
    for name in ('matrix_map.jsonl.gz', 'stage_map.json', 'inventory.json'):
        require(name in pins and sha(directory / name) == pins[name], 'unpinned actual allocation: '+name)
    stage_map = json.loads((directory/'stage_map.json').read_text())
    inventory = json.loads((directory/'inventory.json').read_text())
    count = inventory['stages']
    require(count == len(stage_map['PHW_required_by_stage']), 'stage allocation extent mismatch')
    require(inventory['TP'] == 4 and inventory['layer_dies'] == 4*count, 'actual TP4 allocation required')
    require({(d['stage'],d['rank'],d['die_id']) for d in stage_map['rank_dies']} ==
            {(s,r,4*s+r) for s in range(count) for r in range(4)}, 'rank/die placement mismatch')
    matrices = {}
    with gzip.open(directory/'matrix_map.jsonl.gz','rt') as source:
        for line in source:
            m = json.loads(line); ident = (m['layer'],m['alias'])
            require(ident not in matrices, 'duplicate native matrix identity')
            require(0 <= m['stage'] < count, 'matrix outside real allocation')
            matrices[ident] = m
    return count, matrices


def lower(request, directory, root=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    count, matrices = load_binding(directory, request['allocation_sha256'])
    stages = request['stages']
    require(len(stages) == count and {s['stage'] for s in stages} == set(range(count)),
            'every real stage requires an explicit program, including idle stages')
    require(request.get('candidate_only') is True, 'native candidate cannot self-adopt')
    require(request.get('hc_hwords') == 640, 'actual H[4,5120] BF16 rows required')
    require(set(request['source_jobs']) and len(request['source_jobs']) == len(set(request['source_jobs'])),
            'explicit complete source job coverage required')
    allocated = {}
    for stage in stages:
        for index, op in enumerate(stage['operations']):
            key=(stage['stage'],op['source_id'])
            require(key not in allocated, 'source operation duplicated on physical stage')
            allocated[key]=(index,op)
    seen = set(); programs = []; descriptor_counts = {'hload':0,'hstore':0}
    for stage in sorted(stages,key=lambda s:s['stage']):
        boot, token = [], []
        # Startup GAIN is separate from steady-token H landing. Delaying a
        # payload by PGAP is not a substitute for actual startup completion.
        for op in stage['boot']:
            arg=op['arg'];require(op['engine']==2 and (arg>>20)&7==5 and 0<=arg<1<<23,
                                'boot only contains actual static HC GAIN arguments')
            boot.append((2<<24)|arg)
        for op in stage['operations']:
            ident=op['source_id'];require(ident in request['source_jobs'], 'invented source operation')
            seen.add(ident);engine,arg=op['engine'],op['arg']
            require(isinstance(op.get('vm_inputs'),list), 'every operation must name its actual VM materialization inputs')
            for dependency in op['vm_inputs']:
                producer=allocated.get((stage['stage'],dependency['producer_source_id']))
                require(producer is not None, 'VM operand producer absent from this actual stage')
                materializer=allocated.get((stage['stage'],dependency['materializer_source_id']))
                require(materializer is not None, 'VM operand has no actual materialization source')
                pi,pop=producer;mi,mop=materializer
                ci=next(i for i,x in enumerate(stage['operations']) if x is op)
                # Resident HC POST changes H SRAM, not VM. A real spill must
                # occur after POST and before every VM reader of that H.
                if pop['engine']==2 and ((pop['arg']>>20)&7)==3:
                    require(mop['engine']==2 and ((mop['arg']>>20)&7)==1 and pi<mi<ci,
                            'resident HC POST requires an actual ordered H_STORE before its VM consumer')
                    require(mop.get('h_region_base')==dependency['base'] and mop.get('h_region_rows')==dependency['rows'],
                            'HC POST spill does not bind the consumed VM region')
                else:
                    require(pi<=mi<ci and mop.get('vm_output')=={'base':dependency['base'],'rows':dependency['rows']},
                            'VM consumer lacks matching actual producer commit')
            require(type(engine) is int and 0<=engine<12 and type(arg) is int and 0<=arg<1<<24,
                    'real engine/arg24 contract required')
            rel=op.get('endpoint_source')
            require(isinstance(rel,str) and not Path(rel).is_absolute() and '..' not in Path(rel).parts,
                    'native endpoint argument needs a repository source contract')
            require(sha(root/rel)==op.get('endpoint_source_sha256'),
                    'native endpoint source contract changed')
            if engine==0:
                require(type(op.get('field_phase')) is int and arg==op['field_phase'],
                        'field argument must be actual emitted CFG phase')
                require(op.get('matrices'), 'field phase needs real matrix identities')
                for key in op['matrices']:
                    m=matrices.get(tuple(key));require(m and m['stage']==stage['stage'],
                            'field fragment assigned to a different physical stage')
            if engine==2:
                require(op.get('endpoint_codec')=='ot_s81_hc_cseq.arg24.v1',
                        'HC port needs explicit cseq codec; capture and other native endpoint schemas cannot be inferred')
                kind=(arg>>20)&7
                require(kind<=5 and not arg&(1<<23), 'HC arg23 reserved for compiler slot rebasing')
                require(kind!=5, 'GAIN reload is not a steady-token operation')
                if kind in (0,1):
                    base=arg&16383
                    require(base+2*request['hc_hwords']<=16384, 'two-slot H region exceeds actual VM')
                    require(op.get('h_region_base')==base and op.get('h_region_rows')==640,
                            'H transfer must bind the actual package/hop VM region')
                    arg |= 1<<23
                    descriptor_counts['hload' if kind==0 else 'hstore']+=1
            token.append((engine<<24)|arg)
        require(len(token)<=128, 'real stage sequencer NOPS128 exceeded')
        programs.append({'stage':stage['stage'],'boot':boot,'token':token,
                         'prog_len':len(token),'hc_slot_rebase':True})
    require(seen==set(request['source_jobs']), 'source jobs omitted from native stage allocation')
    return {'schema':'opentallas.s81.native-stage-program.v1','candidate_only':True,'adopted':False,
            'allocation_sha256':request['allocation_sha256'],'programs':programs,
            'transfer_descriptor_counts':descriptor_counts,'native_executed_transfer_count':None,
            'dispatch_eligible':False,
            'remaining_gate':'actual source completion, VM/HC/hop execution and physical binding'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--request',type=Path,required=True)
    p.add_argument('--binding',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();result=lower(json.loads(a.request.read_text()),a.binding)
    result['request_sha256']=sha(a.request);a.out.mkdir(parents=True,exist_ok=False)
    for program in result['programs']:
        for kind in ('boot','token'):
            (a.out/f"s{program['stage']:03d}.{kind}.hex").write_text(''.join(f'{w:07x}\n' for w in program[kind]))
    (a.out/'native_program.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()
