#!/usr/bin/env python3
"""Source-derived AR family gaps; descriptors never count as executed kernels."""
import argparse, collections, hashlib, json
from pathlib import Path

def inventory(program, registry, cp_map):
    ops={o['id']:o for b in program['batches'] for o in b['operations']}
    entries=registry['entries']
    if len(ops)!=len(entries) or set(ops)!={o['id'] for o in entries}:
        raise ValueError('graph and registry IDs differ')
    cp_by_kernel={o['kernel']:o['CP_PC'] for o in cp_map['operations']}
    grouped=collections.defaultdict(list)
    for e in entries:
        if e['kernel']!=ops[e['id']]['kernel'] or e['unit']!=ops[e['id']]['unit']:
            raise ValueError('registry and source operation differ')
        grouped[e['kernel']].append(e)
    rows=[]
    for family, items in sorted(grouped.items()):
        descriptors=[e['production_entry'] for e in items if e['production_entry'] is not None]
        dependencies={ops[e['id']]['dependency'] for e in items}
        upstream=sorted({ops[x]['kernel'] for x in dependencies if x is not None})
        reads=sorted({x for e in items for x in ops[e['id']]['reads']})
        writes=sorted({x for e in items for x in ops[e['id']]['writes']})
        ranges=sorted({(d['ROM_PC'],d['ROM_count']) for d in descriptors})
        rows.append(dict(family=family,operation_count=len(items),
            units=sorted({e['unit'] for e in items}),source_operation_ids=[e['id'] for e in items],
            upstream_graph_families=upstream,source_reads=reads,source_writes=writes,
            descriptor_join_count=len(descriptors),
            source_assigned_CP_entry=cp_by_kernel.get(family),
            native_ROM_ranges=[dict(PC=p,count=n) for p,n in ranges],
            required_owner_bits=74,descriptor_owner_bits=sorted({d['owner_bits'] for d in descriptors}),
            engineering_owner=next((e['owner'] for e in items if 'owner' in e),'UNASSIGNED_IN_SOURCE'),
            actual_producer_binding='descriptor_only_unqualified' if descriptors else 'NOT_IMPLEMENTED_IN_REGISTRY',
            actual_CP_map_installed=False,numerical_RTL_qualified=False,
            real_kernel_completion_proven=False,resolved=False,
            status='JOINED_DESCRIPTOR_NOT_QUALIFIED' if descriptors else 'UNRESOLVED'))
    return dict(schema='opentallas.qwen.r25.AR.family_inventory.v1',
        graph_operations=len(entries),descriptor_joined_operations=sum(r['descriptor_join_count'] for r in rows),
        unresolved_family_count=sum(r['status']=='UNRESOLVED' for r in rows),
        families=rows,full_decode_executable=False,
        grading='Resolved requires installed numerical kernel plus its real completion. CPU ROM and mock provider control gates alone are insufficient.')

def main():
    p=argparse.ArgumentParser()
    for name in ('program','registry','cp-map','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();paths={'program':a.program,'registry':a.registry,'cp_map':a.cp_map}
    result=inventory(*(json.loads(paths[x].read_text()) for x in ('program','registry','cp_map')))
    result['source_sha256']={x:hashlib.sha256(path.read_bytes()).hexdigest() for x,path in paths.items()}
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('AR_FAMILY_INVENTORY',result['graph_operations'],result['descriptor_joined_operations'],result['unresolved_family_count'])
if __name__=='__main__':main()
