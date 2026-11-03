#!/usr/bin/env python3
"""Prepare a default-off R8 extra table for equal-phase native SU write tuples.

The source constraint is per STREAM consumer across both lane groups. This is
SOURCE PREP: actual producer phase qualification and owner adoption are separate.
"""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'die_plan'))
import r8

def build(path):
    j=json.loads(path.read_text());by={};gb={}
    for g in j['landing']:
        if '.u_lrly' in g['sink']:
            for m in g['members']:
                if m['sink_port']in('gb','gv','lv1','pd1'):gb.setdefault(g['sink'].split('.')[0],set()).add(m['landed_stages'])
        if not g['sink'].endswith('.u_stm'):continue
        ms=[m for m in g['members']if m['sink_port']in('vm_we','vm_waddr','vm_wdata')]
        if ms:by.setdefault(g['sink'],[]).extend((g,m)for m in ms)
    if len(by)!=12:raise ValueError('actual12 native STREAM consumers required')
    members=[];rows=[];bits=0
    for sink,gs in sorted(by.items()):
        node=sink.split('.')[0]
        if gb.get(node)!={4}:raise ValueError('candidate equal-phase input transport assumption changed')
        fields={p:[]for p in ('vm_we','vm_waddr','vm_wdata')}
        for g,m in gs:
            if m['asbuilt_stages']!=0:raise ValueError('primary tuple producer phase changed')
            fields[m['sink_port']].append(m)
        if any(sum(r8.nbits(m['sink_bits'])for m in ms)!=b for ms,b in zip(fields.values(),(8,192,256))):raise ValueError('whole8-lane tuple shape missing')
        old={m['landed_stages']for _,m in gs};target=max(old)
        if old!={17,18}:raise ValueError('explicit frozen SOURCE tuple phases required')
        added=0
        for g,m in gs:
            if m['landed_stages']==target:continue
            n=r8.nbits(m['sink_bits']);delta=target-m['landed_stages'];added+=n*delta
            members.append(dict(id=r8.mkey(g,m),sink=sink,sink_part=g['sink_part'],src_part=g['src_part'],sink_port=m['sink_port'],sink_bits=m['sink_bits'],source=m['source'],asbuilt=m['asbuilt_stages'],bound=m['bound_stages'],pad=target-m['bound_stages'],landed=target,cls='NATIVE_SU_STREAM_TUPLE_'+node,lane=m['lane']))
        if added!=228:raise ValueError('expected low4 tuple228bits single additional edge')
        bits+=added;rows.append(dict(node=node,old_group_landed=[17,18],candidate_landed=target,added_FF_bits=added,added_maximum_path_edges=0))
    return dict(schema=r8.SCHEMA,die='qwen_compute',status='SOURCE_PREP_NOT_ADOPTED',default_enabled=False,source_bus_groups_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),consumer_contract='equal-phase eight-lane native SU writes must reach one STREAM beat assembler at equal phase; every we/address/data bit is kept together',qualification='HOLD pending actual producer/selected-wrapper phase review; no selected failure inferred solely from landed depths',activation='explicit future asbuilt.land_r8_extra selection only after review; never mutate frozen table or active jobs',members=members,summary=dict(consumers=12,members=len(members),added_FF_bits=bits,added_maximum_path_edges=0,arithmetic_changes=0,rows=rows))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--groups',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=build(a.groups);a.out.write_text(json.dumps(r,indent=2)+'\n');print(r['summary']['members'],r['summary']['added_FF_bits'],'extra FF bits, maximum edges0, HOLD')
