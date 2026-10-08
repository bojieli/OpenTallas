#!/usr/bin/env python3
"""Grid-priced north native-owner reservation; south descriptor protocol stays open."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def generate(descriptor=False, sm_readback=None, escape=False, u_corridors=False):
    old=H.build(H.R24SM3V,network_probe=True)
    if escape and not descriptor:
        raise ValueError('control escape reservations require descriptors')
    if u_corridors and not escape:
        raise ValueError('U corridors require endpoint escape reservations')
    m=H.build(H.R24SM3VOCEU if u_corridors else H.R24SM3VOCE if escape else H.R24SM3VOC if descriptor else H.R24SM3VO,network_probe=True)
    bays=m['native_owner_bays']
    descriptor_actual=None
    readback_sources=[]
    if u_corridors:
        readback_sources.append(H.ROOT/'results/uarch/hbm_sm_owner_reservation_20261007/control_u_successor/proposal.json')
    if sm_readback:
        if not descriptor:
            raise ValueError('SM descriptor readback requires descriptor reservations')
        rb_path=Path(sm_readback);rb=json.loads(rb_path.read_text())
        if rb['die_um'] != [0,0,3075.84,1131.84]:
            raise ValueError('SM descriptor BPin dimensions do not match candidate')
        pins=[p for p in rb['pins'] if p['name'].startswith('d_') or p['name']=='fault']
        if len(pins)!=59 or any(len(p['boxes'])!=1 for p in pins):
            raise ValueError('expected all 58 descriptor signals and fault, one box each')
        distances=[]
        for pin in pins:
            x0,y0,x1,y1=pin['boxes'][0]['rect_um']
            x,y=(x0+x1)/2,(y0+y1)/2
            distances.append(max(abs(x-1441.152)+abs(y-edge_y) for edge_y in (-66.96,-2.16)))
        descriptor_actual=dict(scope=rb['scope'],odb_sha256=rb['odb_sha256'],pins=len(pins),
            adapter_east_face_worst_manhattan_um=round(max(distances),6))
        if max(distances)>100:
            raise ValueError('actual descriptor BPin exceeds 100um candidate face bound')
        readback_sources.append(rb_path)
    collisions=[]
    for r in bays+m.get('native_descriptor_bays',[])+m.get('native_control_escape_bays',[])+m.get('native_control_u_corridors',[]):
        x0,y0,x1,y1=r['box_um']
        for i in m['insts']:
            if min(x1,i.x+i.w)>max(x0,i.x)+1e-6 and min(y1,i.y+i.h)>max(y0,i.y)+1e-6:
                collisions.append([r['sm'],i.name])
    check=H.legality(m)
    if collisions or check['overlaps'] or check['outside']:
        raise ValueError(dict(bay_collisions=collisions,legality=check))
    record=dict(status='RESERVATION_ONLY_PHYSICAL_MASTER_AND_CONTROL_PATHS_OPEN',selected=False,
        legality=check,bay_macro_collisions=collisions,bays=bays,
        control_u_corridors=m.get('native_control_u_corridors',[]),
        control_u_area_upper_um2=sum((r['box_um'][2]-r['box_um'][0])*(r['box_um'][3]-r['box_um'][1]) for r in m.get('native_control_u_corridors',[])),
        control_escape_bays=m.get('native_control_escape_bays',[]),
        control_escape_scope='macro keepout for planned flight portals; route corridor, not solid obstacle',
        control_escape_reserved_area_um2=64*40*48 if escape else 0,
        descriptor_actual_bpin=descriptor_actual,
        descriptor_bays=m.get('native_descriptor_bays',[]),
        descriptor_reserved_um=[128.304,64.8] if descriptor else None,
        total_descriptor_reservation_um2=32*128.304*64.8 if descriptor else 0,
        descriptor_pin_face='logical east edge of west-side adapter; physical transform follows SM orientation',
        descriptor_pin_manhattan_upper_um=round(1473.276-1441.152+66.96,6) if descriptor else None,
        descriptor_endpoint_scope='planned d_valid/d_ready/d_base/d_lines/fault pins; actual adapter BPin assignment remains open',
        proposed_owner_um=[256,128],grid_reserved_owner_um=[256.176,129.6],
        grid_um=[H.GX,H.GY],replicas=32,
        total_owner_reservation_um2=32*256.176*129.6,
        cell_budget_um2_per_owner_at_55pct=256.176*129.6*.55,
        additional_existing_network_instances=len(m['insts'])-len(old['insts']),
        additional_existing_network_macro_area_um2=sum(i.w*i.h for i in m['insts'])-sum(i.w*i.h for i in old['insts']),
        latency='No latency adoption: moved/supplemented network paths must be rerouted and balanced. Native descriptor crosses north-to-south outside the SM.',
        remaining_gates=['actual north native-owner physical view and local op/X/start-ready pin binding',
          'south descriptor adapter footprint and finite actual-acceptance acknowledgement',
          'obstacle-aware outside-SM descriptor and fault paths; no straight-through-macro routing',
          'rerun all result/control/X/weight shared corridor capacities and endpoint proximity',
          'clock entries, IO budgets, exactness and SS/FF physical qualification'],
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(H.__file__)]+readback_sources})
    placement=dict(insts=[dict(name=i.name,master=i.master,x=i.x,y=i.y,w=i.w,h=i.h,orient=i.orient,
        kind=i.kind,box_um=i.box()) for i in m['insts']],buses=m['buses'],paths=m['paths'],geo=m['geo'],
        result_pin_bays=m['result_pin_bays'],native_owner_bays=bays,native_descriptor_bays=m.get('native_descriptor_bays',[]),native_control_escape_bays=m.get('native_control_escape_bays',[]),native_control_u_corridors=m.get('native_control_u_corridors',[]),legality=check)
    return record,placement

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);ap.add_argument('--descriptor',action='store_true');ap.add_argument('--sm-readback');ap.add_argument('--escape',action='store_true');ap.add_argument('--u-corridors',action='store_true')
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    record,placement=generate(a.descriptor,a.sm_readback,a.escape,a.u_corridors)
    (out/'model.json').write_text(json.dumps(record,indent=2)+'\n')
    with gzip.open(out/'placement.json.gz','wt') as f:json.dump(placement,f,separators=(',',':'))
    print(json.dumps(record['legality']))
