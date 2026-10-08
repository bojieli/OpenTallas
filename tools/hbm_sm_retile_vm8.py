#!/usr/bin/env python3
"""Compose full VM8 with the SM retile, preserving old overlap failure evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def seam_pin_join(contract):
    """Join every ordered requested pin across the actual nonoverlapping seam."""
    rows=[]
    for q in ('sw','se','nw','ne'):
        south,north=(contract['masters'][f'hfd_vm_{q}_{h}'] for h in ('s','n'))
        for bus in ('s2n','n2s'):
            sp,np=south['ports'][bus],north['ports'][bus]
            if sp['bits']!=np['bits'] or {sp['direction'],np['direction']}!={'input','output'}:
                raise ValueError(f'incompatible seam interface: {q}/{bus}')
            distances=[];xs=[]
            for bit in range(sp['bits']):
                pin=f'{bus}[{bit}]';a=south['pins'][pin];b=north['pins'][pin]
                if a[0]!='M5' or b[0]!='M5' or abs(a[1]-b[1])>1e-6:
                    raise ValueError(f'seam requested pins do not align: {q}/{pin}')
                distances.append(abs(south['height_um']+b[2]-a[2]));xs.append(a[1])
            if len(set(xs))!=len(xs):
                raise ValueError(f'duplicate seam track: {q}/{bus}')
            rows.append(dict(quadrant=q,bus=bus,bits=sp['bits'],layer='M5',
                requested_pin_x_range_um=[min(xs),max(xs)],
                requested_pin_center_gap_um=[round(min(distances),6),round(max(distances),6)],
                unique_tracks=len(xs),native_pitch_um=.048,
                occupied_track_window_um=round(max(xs)-min(xs)+.048,6),
                ordered_bit_join='PASS',routed_pin_readback='OPEN'))
    return rows


def generate(contract_path):
    path=Path(contract_path);contract=json.loads(path.read_text())
    old=H.build(dict(H.R24SM3,vm_split8=True),network_probe=True)
    m=H.build(H.R24SM3V,network_probe=True)
    vm=[i for i in m['insts'] if i.master in contract['masters']]
    if len(vm)!=8:
        raise ValueError('expected all eight full VM masters')
    for i in vm:
        c=contract['masters'][i.master]
        if abs(i.w-c['width_um'])>1e-6 or abs(i.h-c['height_um'])>1e-6:
            raise ValueError(f'VM dimension mismatch: {i.name}')
    check=H.legality(m)
    if check['overlaps'] or check['outside']:
        raise ValueError(check)
    return dict(status='GEOMETRY_ONLY_PASS_ROUTE_AND_LATENCY_ADOPTION_OPEN',selected=False,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(H.__file__),path]},
        prior_unrepaired_geometry=H.legality(old),legality=check,
        outline_um=[m['geo']['W'],m['geo']['H']],
        north_half_displacement_um=.024,pair_height_um=1000.08,
        allocated_macro_area_increment_um2=round(4*699.816*.024,9),
        north_south_quadrant_gap_um=0,
        geometry_change_added_cycles=0,
        measured_latency=contract['measured_latency'],
        exactness=contract['exactness'],
        vm_instances=[dict(name=i.name,master=i.master,x=i.x,y=i.y,w=i.w,h=i.h,orientation=i.orient) for i in vm],
        seam_buses=[b for b in m['buses'] if '_seam_' in b[0]],
        requested_seam_pin_join=seam_pin_join(contract),
        blockers=['all eight routed SS/FF physical masters and actual BPin readback',
            'joint abutting-seam and shared corridor track capacity; zero gap is not free routing area',
            'per-bit latency differences require real packet/control alignment before die adoption',
            'compose measured VM path increments into selected single-user schedule',
            'clock CTS rebind eight VM entries, retaining source/reset phase gates'])

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--contract',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();r=generate(a.contract);p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['legality']))
