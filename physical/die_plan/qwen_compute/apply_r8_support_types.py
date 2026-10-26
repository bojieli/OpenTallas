#!/usr/bin/env python3
"""Declare actual R8 functional variants for the two measured SLE support families.

No timing is changed. Every explicit class is derived from the actual strict-bind
split census and must also have one exact R8 landing vector within the class.
"""
import argparse,copy,json
from pathlib import Path

def apply(plan,report,table):
    out=copy.deepcopy(plan);parts={p['name']:p for p in out['partitions']};changes=[]
    splits={s['type']:s for s in report['type_splits']}
    if set(splits)!={'sle_ctl','sle_fw_v1'}:raise ValueError(f'unexpected support splits {sorted(splits)}')
    for family,s in splits.items():
        if len(s['variants'])!=2:raise ValueError(f'unexpected class count {family}')
        for i,group in enumerate(s['variants']):
            signatures=[]
            for part in group:
                if parts[part]['type']!=family:raise ValueError(f'not baseline {part}')
                v=[]
                for m in table['members']:
                    if m['sink_part']==part and m['pad']:
                        v.append((m['sink'].split('.',1)[1],m['sink_port'],tuple(map(tuple,m['sink_bits'])),m['pad']))
                signatures.append(tuple(sorted(v)))
            if len(set(signatures))!=1:raise ValueError(f'nonuniform landing profile in {family}/{i}')
            if i==0:continue
            name=family+'_r8phase';typ=copy.deepcopy(out['partition_types'][family])
            if name in out['partition_types']:raise ValueError('output already classified')
            typ['module']+='_r8phase';typ['note']=typ.get('note','')+' Actual R8 delay-vector class; no lane timing change.'
            out['partition_types'][name]=typ
            for part in group:parts[part]['type']=name
            changes.append(dict(family=family,type=name,parts=group,profile=[list(v) for v in signatures[0]]))
    return out,dict(kind='r8_support_functional_classes',added_types=len(changes),renamed_parts=sum(len(c['parts']) for c in changes),lane_added_cycles=0,classes=changes)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('plan','report','r8','out','manifest'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or a.manifest.exists():raise ValueError('refuse existing output')
    out,m=apply(json.loads(a.plan.read_text()),json.loads(a.report.read_text()),json.loads(a.r8.read_text()))
    a.out.write_text(json.dumps(out,indent=1)+'\n');a.manifest.write_text(json.dumps(m,indent=1)+'\n');print(json.dumps({k:v for k,v in m.items() if k!='classes'}))
if __name__=='__main__':main()
