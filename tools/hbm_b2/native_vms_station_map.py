#!/usr/bin/env python3
"""Prepare source-directed HBM VMS station rows from the actual native bit graph.

Candidate only: corrects old core aliases, direction and whole-bus assumptions.
A retained station path still needs pin/clock/geometry composition on the die event.
Missing South-role geometry stays missing; no copy of North geometry is invented.
The full-width option removes unimplemented serialization for the selected links.
"""
import argparse
import copy
from collections import Counter
import hashlib
import json
from pathlib import Path
import re


def is_vms_edge(e):
    return ((e['src_path'].startswith('vmb_') and e['dst_path'].startswith('hb_vms_')) or
            (e['src_path'].startswith('hb_vms_') and e['dst_path'].startswith('vmb_')))


def bit_runs(pairs):
    """Lossless contiguous [source_lo,destination_lo,width] runs, in source-bit order."""
    pairs=sorted(map(tuple,pairs))
    if len(pairs)!=len(set(pairs)):
        raise ValueError('duplicate native bit pair')
    runs=[]
    for s,d in pairs:
        if runs and s==runs[-1][0]+runs[-1][2] and d==runs[-1][1]+runs[-1][2]:
            runs[-1][2]+=1
        else:runs.append([s,d,1])
    return runs


def prepare(plan,graph,full_width=False):
    out=copy.deepcopy(plan)
    tnames={p['name']:p['type'] for p in plan['partitions']}
    selected={t:[] for t in ('q_hub_nw','q_hub_ne')}
    mapping=[]
    used={t:set() for t in selected}
    for e in graph['edges']:
        if not is_vms_edge(e):continue
        if e['src_partition']!=e['dst_partition']:
            raise ValueError('VMS/bank native edge crosses partitions')
        typ=tnames[e['src_partition']]
        if typ not in selected:raise ValueError('unexpected VMS partition type')
        bank=e['src_plan_instance'] if e['src_path'].startswith('vmb_') else e['dst_plan_instance']
        src=e['src_plan_instance']+'.'+e['src_port']
        dst=e['dst_plan_instance']+'.'+e['dst_port']
        if e['width']!=len(e['bit_pairs']):raise ValueError('native width does not match bit map')
        item=dict(type=typ,source_path=e['src_path'],source_port=e['src_port'],
                  destination_path=e['dst_path'],destination_port=e['dst_port'],
                  source=src,destination=dst,width=e['width'],bit_runs=bit_runs(e['bit_pairs']),
                  source_intermediate_stages=0)
        # The old rows describe only the original North-role bank positions.
        if bank.endswith('_mu1'):
            item.update(status='MISSING_SOUTH_ROLE_GEOMETRY',candidates=[])
            mapping.append(item);continue
        k=int(re.fullmatch(r'u_vmb_Q(\d)',bank).group(1))
        port=e['src_port'] if e['src_path'].startswith('vmb_') else e['dst_port']
        bank_launch=f'{bank}.{port}|u_hb_vms_Q'
        hub_launch=f'u_hb_vms_Q.b{k}_{port}|{bank}'
        wanted=bank_launch if e['src_path'].startswith('vmb_') else hub_launch
        opposite=hub_launch if wanted==bank_launch else bank_launch
        stations=plan['partition_types'][typ].get('internal_stations',[])
        matches=[(i,s,False)for i,s in enumerate(stations)if s.get('conn')==wanted]
        if not matches:matches=[(i,s,True)for i,s in enumerate(stations)if s.get('conn')==opposite]
        if len(matches)!=1:
            item.update(status='MISSING_OR_AMBIGUOUS_STATION',candidates=[x[0]for x in matches])
            mapping.append(item);continue
        i,old,reverse=matches[0]
        if i in used[typ]:raise ValueError('one old row assigned to multiple native connections')
        used[typ].add(i)
        new=copy.deepcopy(old)
        if reverse:
            new['from_um'],new['to_um']=new['to_um'],new['from_um']
            new['regs_um']=list(reversed(new['regs_um']))
            if 'r9_segments'in new:new['r9_segments']=list(reversed(new['r9_segments']))
        new['conn']=src+'|'+e['dst_plan_instance']
        new['launch']=src
        new['capture']=e['dst_plan_instance']
        if full_width:
            new['bits']=e['width']
            for field in ('serial_k','bits_parallel','r11_cc_serial'):new.pop(field,None)
        new['note']=new.get('note','')+' | NATIVE VMS CANDIDATE: exact source-directed bit mapping; actual pin/clock/geometry composition REQUIRED'
        selected[typ].append(new)
        item.update(status='PREPARED_GEOMETRY_UNQUALIFIED',old_index=i,old_conn=old['conn'],
                    reversed_geometry=reverse,station_count=len(new['regs_um']),serial_k=new.get('serial_k',1),
                    planned_wires=new['bits'],plan_source_bits=old.get('bits_parallel',old['bits']))
        mapping.append(item)
    removed=[]
    for typ,newrows in selected.items():
        oldrows=out['partition_types'][typ]['internal_stations']
        keep=[]
        for i,s in enumerate(oldrows):
            if 'u_vmb_'in s.get('conn','') and 'u_hb_vms_'in s.get('conn',''):
                if i not in used[typ]:removed.append(dict(type=typ,index=i,conn=s['conn'],reason='redundant/reversed old North-role alias; actual directed bit link selected once'))
            else:keep.append(s)
        out['partition_types'][typ]['internal_stations']=keep+newrows
    counts=Counter(x['status']for x in mapping)
    report=dict(schema='opentallas.hbm.native_vms_station_map.v1',status='SOURCE_PREPARATION_ONLY',
                executable=False,full_width=full_width,totals=dict(counts),removed=removed,connections=mapping,
                caveats=['pin endpoints and all clock/reset/budget dates still need die composition',
                         'South-role station geometry absent; source links remain present in the map',
                         'only VMS/bank connections changed; other inherited internal station rows unchanged'])
    return out,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',required=True)
    ap.add_argument('--graph',required=True)
    ap.add_argument('--out-plan',required=True)
    ap.add_argument('--report',required=True)
    ap.add_argument('--full-width',action='store_true')
    a=ap.parse_args()
    pb,gb=Path(a.plan).read_bytes(),Path(a.graph).read_bytes()
    p,r=prepare(json.loads(pb),json.loads(gb),a.full_width)
    r['inputs_sha256']=dict(plan=hashlib.sha256(pb).hexdigest(),graph=hashlib.sha256(gb).hexdigest())
    Path(a.out_plan).write_text(json.dumps(p,indent=1)+'\n')
    Path(a.report).write_text(json.dumps(r,indent=1)+'\n')
    print(json.dumps(dict(totals=r['totals'],removed=len(r['removed']))))


if __name__=='__main__':main()
