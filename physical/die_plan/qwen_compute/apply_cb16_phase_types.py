#!/usr/bin/env python3
"""Apply the measured CB16 delay-vector classes as explicit unsigned frame types.

Run after base geometry changes and before per-type FT/pad clock-density generation. No hard A0 body, data pin,
outline or control/reset depth is changed. The manifest is generated from the complete original R8 table plus the
DAG overlay; every distinct nonzero leaf delay vector receives one deterministic physical type.
"""
import argparse,copy,hashlib,json,re
from collections import defaultdict
from pathlib import Path

def vector_key(m):return (m['sink'].split('.',1)[1],m['sink_port'],tuple(map(tuple,m['sink_bits'])))
def tag(key,depth):
    leaf,port,bits=key
    m=re.fullmatch(r'u_t_(\d)_(\d)',leaf)
    if m:return port.replace('_','')+m[1]+m[2]+'d'+str(depth)
    m=re.fullmatch(r'u_fab\.u_x_(\d)_(\d)',leaf)
    if m:return 'xb'+m[1]+m[2]+'d'+str(depth)
    raise ValueError(f'unknown phase site {key}')

def classify(plan,table,overlay):
    ptype={p['name']:p['type'] for p in plan['partitions']};patch={m['id']:m for m in overlay['members']}
    families={ptype[m['sink_part']] for m in table['members'] if m['sink'].startswith('c16_')}
    vectors={part:{} for part,typ in ptype.items() if typ in families};extras=defaultdict(int)
    for old in table['members']:
        if not old['sink'].startswith('c16_'):continue
        m=patch.get(old['id'],old);part=m['sink_part']
        if m['pad']:vectors[part][vector_key(m)]=m['pad']
        if m['id'] in patch:extras[part]+=m['tree_align']*sum(b-a+1 for a,b in m['sink_bits'])
    byfamily=defaultdict(lambda:defaultdict(list))
    for part,v in vectors.items():byfamily[ptype[part]][tuple(sorted(v.items()))].append(part)
    classes=[];assignments={}
    for family,groups in sorted(byfamily.items()):
        # The most replicated exact vector retains the original family name; ties use the first physical partition.
        base=max(groups,key=lambda v:(len(groups[v]),tuple(-ord(c) for c in min(groups[v]))))
        b=dict(base)
        for v,parts in sorted(groups.items(),key=lambda q:min(q[1])):
            vv=dict(v);changes=[tag(k,vv.get(k,0)) for k in sorted(b.keys()|vv.keys()) if b.get(k,0)!=vv.get(k,0)]
            name=family if v==base else family+'_'+'_'.join(changes)
            rows=[dict(leaf=k[0],port=k[1],bits=[list(x) for x in k[2]],pad=d) for k,d in v]
            h=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            classes.append(dict(type=name,family=family,profile_sha256=h,parts=sorted(parts),pad_vector=rows,
                added_ff_min=min(extras[p] for p in parts),added_ff_max=max(extras[p] for p in parts),
                per_part_added_ff={p:extras[p] for p in sorted(parts)}))
            assignments.update({p:name for p in parts})
    if len(assignments)!=192 or len(classes)!=18:raise ValueError(f'unexpected measured classes: {len(assignments)} parts/{len(classes)} classes')
    return dict(schema='opentallas.qwen.cb16.phase_types.v1',classes=classes,assignments=assignments,
        original_families=sorted(byfamily),new_type_count=len(classes)-len(byfamily),
        root_added_cycles_max=overlay['summary']['root_added_max'],logical_added_ff=overlay['summary']['logical_pad_flops'],
        qualification='CANDIDATE: actual type-uniform bind, wrapper cell/cut/slot/clock budgets and G0/G2/GEOM required')

def apply(raw,manifest):
    out=copy.deepcopy(raw);types=out['partition_types'];base={f:copy.deepcopy(types[f]) for f in manifest['original_families']}
    for c in manifest['classes']:
        name,family=c['type'],c['family'];t=copy.deepcopy(base[family])
        if name!=family:
            if name in types:raise ValueError(f'phase type collision {name}; regenerate from the unmodified base plan')
            t['module']=t['module']+'_'+name[len(family)+1:]
        t['note']=t.get('note','')+' CB16 whole-port DAG phase profile '+c['profile_sha256']+'; unsigned frame, hard A0 unchanged.'
        types[name]=t
    parts={p['name']:p for p in out['partitions']}
    for part,typ in manifest['assignments'].items():
        if part not in parts or parts[part]['type'] not in manifest['original_families']:raise ValueError(f'base partition changed: {part}')
        parts[part]['type']=typ
    return out

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',type=Path,required=True);a.add_argument('--r8',type=Path,required=True);a.add_argument('--overlay',type=Path,required=True);a.add_argument('--manifest',type=Path,required=True);a.add_argument('--out-plan',type=Path)
    q=a.parse_args();raw=json.loads(q.plan.read_text());m=classify(raw,json.loads(q.r8.read_text()),json.loads(q.overlay.read_text()))
    if q.manifest.exists() or (q.out_plan and q.out_plan.exists()):raise ValueError('refuse existing outputs')
    q.manifest.write_text(json.dumps(m,indent=1)+'\n')
    if q.out_plan:q.out_plan.write_text(json.dumps(apply(raw,m),indent=1)+'\n')
    print('CB16_PHASE_TYPES',len(m['classes']),'classes',m['new_type_count'],'new',len(m['assignments']),'parts')
if __name__=='__main__':main()
