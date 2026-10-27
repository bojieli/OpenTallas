#!/usr/bin/env python3
"""Give actual current R8 support signatures separate unsigned frame types, with zero lane-cycle change."""
import argparse,copy,json
from pathlib import Path

def apply(plan,report,table,allowed=None):
    out=copy.deepcopy(plan);parts={p['name']:p for p in out['partitions']};rows=[]
    splits={s['type']:s for s in report.get('type_splits',[])}
    if set(splits)-set(allowed if allowed is not None else ('sle_ctl','sle_fw_v1')):raise ValueError(f'unexpected support split families: {sorted(splits)}')
    def profile(part):
        return tuple(sorted((m['sink'].split('.',1)[1],m['sink_port'],tuple(map(tuple,m['sink_bits'])),m['pad']) for m in table['members'] if m['sink_part']==part and m['pad']))
    for family,split in sorted(splits.items()):
        original=out['partition_types'][family];first=min(p for p,v in parts.items() if v['type']==family);groups=[]
        for variant in split['variants']:
            byprofile={}
            for part in variant:
                if parts[part]['type']!=family:raise ValueError(f'non-baseline support member {part}')
                byprofile.setdefault(profile(part),[]).append(part)
            groups.extend((sig,sorted(members)) for sig,members in byprofile.items())
        for index,(sig,members) in enumerate(sorted(groups,key=lambda x:min(x[1]))):
            name=family if first in members else f'{family}_r8p{index:02}'
            if name!=family:
                if name in out['partition_types']:raise ValueError(f'output support type exists: {name}')
                typ=copy.deepcopy(original);typ['module']+=name[len(family):];typ['note']=typ.get('note','')+' Exact current native R8 support-class signature; zero lane-cycle change.'
                out['partition_types'][name]=typ
            for part in members:parts[part]['type']=name
            rows.append(dict(type=name,family=family,parts=members,representative=min(members),profile=[[a,b,[list(q) for q in bits],depth] for a,b,bits,depth in sig]))
    return out,dict(schema='opentallas.qc.r8_support_classes.v1',classes=rows,new_type_count=len(out['partition_types'])-len(plan['partition_types']),lane_added_cycles=0)
if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','report','r8','out','manifest'):a.add_argument('--'+n,type=Path,required=True)
    q=a.parse_args()
    if q.out.exists() or q.manifest.exists():raise ValueError('refuse existing output')
    p,m=apply(*[json.loads(x.read_text()) for x in (q.plan,q.report,q.r8)])
    q.out.write_text(json.dumps(p,indent=1)+'\n');q.manifest.write_text(json.dumps(m,indent=1)+'\n');print('SUPPORT_CLASSES',m['new_type_count'],'new',len(m['classes']),'classes; zero new lane cycles')
