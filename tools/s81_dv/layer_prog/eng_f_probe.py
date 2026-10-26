#!/usr/bin/env python3
"""Apply ONLY the reviewed ENG F attachment/station delta to an owned 877 diagnostic snapshot.

This is not a canonical plan update. The reused 877 ELAB is historical source;
new current-source elaboration must include all subsequently adopted RTL fixes.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))


def apply(src, f_plan):
    sys.path.insert(0,str(src/'tools/die_plan'))
    import gen
    import schema
    plan_path=src/'physical/die_plan/s81/die_plan.json'
    manifest_path=src/'physical/die_plan/s81/bind/asbuilt_b178_coll.json'
    raw=json.loads(plan_path.read_text())
    f=json.loads(f_plan.read_text());old=raw['partition_types']['eng__t1'];new=f['partition_types']['eng__t1']
    if old['outline_um']!=new['outline_um']:raise ValueError('ENG F changes the parent outline')
    cores=[c for c in old['hard_cores']if c['module']=='dsdv_eng_rr_e']
    fc=[c for c in new['hard_cores']if c['module']=='dsdv_eng_rr_e']
    if len(cores)!=1 or len(fc)!=1:raise ValueError('one exact engine core required')
    if cores[0]['outline_um']!=fc[0]['outline_um']:raise ValueError('ENG F changes the core outline')
    for k in('pins_file','lef'):cores[0][k]=fc[0][k]
    old['internal_stations']=copy.deepcopy(new['internal_stations'])
    target={'unit_i0':2,'unit_o0':1,'unit_i1':1,'xtier_i0':1,'flt_o0':1}
    got={e['conn'][4:]:len(e['regs_um'])for e in old['internal_stations']if e['conn'].startswith('bus:')}
    if got!=target:raise ValueError(f'ENG F station contract changed: {got}')
    # F4 retires four obsolete planning-only PCI/RCO bits on each endpoint.
    # These two peer types are unique; never change another replica's ABI.
    for bus,width in [('unit_i0',264),('unit_o0',39)]:
        fb=next(b for b in new['buses']if b['name']==bus)
        if fb['width']!=width:raise ValueError('F4 public payload width is not canonical: '+bus)
        next(b for b in old['buses']if b['name']==bus)['width']=width
    pp={p['id']:p for p in raw['ports']};changes=[]
    for bus,count in target.items():
        direction=next(b['dir']for b in old['buses']if b['name']==bus)
        side,index=('dst',-1)if direction=='in'else('src',0)
        ls=[l for l in raw['lanes']if pp[l['ports'][index]][side]=={'part':'eng','bus':bus}]
        if len(ls)!=1:raise ValueError(f'ENG F lane not unique: {bus}')
        lane=ls[0];changes.append(dict(lane=lane['id'],bus=bus,old_fixed=lane.get('fixed_cycles',0),new_fixed=count))
        lane['fixed_cycles']=count
        if bus in ('unit_i0','unit_o0'):
            width=next(v['width']for v in old['buses']if v['name']==bus)
            for pid in lane['ports']:
                port=pp[pid];port['width']=width
                for end in ('src','dst'):
                    ep=port[end]
                    if ep['part']=='eng':continue
                    part=next(p for p in raw['partitions']if p['name']==ep['part'])
                    typ=part['type']
                    if sum(p['type']==typ for p in raw['partitions'])!=1:
                        raise ValueError('F4 peer public ABI would change another replica: '+typ)
                    next(v for v in raw['partition_types'][typ]['buses']if v['name']==ep['bus'])['width']=width
    raw['latency']={'lanes':gen.latency_table(schema.Plan(raw))}
    manifest=json.loads(manifest_path.read_text())
    manifest['internal_stations_types']=sorted(set(manifest.get('internal_stations_types',[]))|{'eng__t1'})
    # Source proof is an actual dependency of the strict binder, not optional
    # documentation. Check the complete copied 877 bundle before launching.
    for path in manifest.get('dead_input_proofs',[]):
        if not(src/path).is_file():raise ValueError('missing source proof bundle: '+path)
    plan_path.write_text(json.dumps(raw,indent=1)+'\n');manifest_path.write_text(json.dumps(manifest,indent=1)+'\n')
    return dict(scope='DIAGNOSTIC_877_SOURCE_ONLY_NOT_ADOPTED',f_sha256=hashlib.sha256(f_plan.read_bytes()).hexdigest(),
                word_stage_budget_vs_877=sum(c['new_fixed']-c['old_fixed']for c in changes if c['bus']!='flt_o0'),
                parallel_valid_stage=1,raw_lane_fixed_delta=sum(c['new_fixed']-c['old_fixed']for c in changes),lanes=changes,
                materialization='PCI2/FKS1/VI_S1 at receivers; RCO data1 + parallel valid1 native source stations; payload/epoch together',
                current_source_note='Next new ELAB must include subsequent f8 fault-width and other adopted RTL fixes')


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--src',type=Path,required=True)
    ap.add_argument('--f-plan',type=Path,required=True);ap.add_argument('--receipt',type=Path,required=True)
    a=ap.parse_args();r=apply(a.src,a.f_plan);a.receipt.write_text(json.dumps(r,indent=1)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
