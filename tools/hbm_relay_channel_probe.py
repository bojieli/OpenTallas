#!/usr/bin/env python3
"""Probe one real HBM endpoint slice against macro-obstructed die geometry.

Only model evidence. Assumed slice geometry cannot establish hardware area or
pin reach. Explicit failures remain failures and are emitted as JSON.
"""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_die_views as V
import hbm_die_relays as R
from hbm_relay_channel_model import channel_path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bus',default='rl_sm0')
    ap.add_argument('--slice-bits',type=int,default=64)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    m,*_=V.model()
    by={it.name:it for it in m['insts']}
    bus=next(b for b in m['buses'] if b[0]==a.bus)
    points=[]
    evidence=[]
    for name,port in bus[3]:
        it=by[name]
        candidates=list((V.ROOT/'physical/hbm_accel_die_views').rglob(f'{it.master}.lef'))
        if len(candidates)!=1:
            raise ValueError(f'{it.master}: expected unique real LEF, found {candidates}')
        p=candidates[0];w,h,pp=R.lef_pins(p.read_text())[it.master]
        base=V.H.port_base(port)
        indices=V.H.port_idx(port) or list(range(bus[2]))
        rp=V.H.real_ports(m)
        names=rp.get(it.master,{}).get(base)
        pts=[]
        for i in indices[:a.slice_bits]:
            pin=names[i] if names and i<len(names) else f'{base}[{i}]'
            if pin not in pp:
                raise ValueError(f'{it.master}: missing physical pin {pin}')
            pts.append(R.to_die(it,*pp[pin][0],w,h))
        centre=(sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts))
        faces=[(abs(centre[0]-it.x),(-1,0)),(abs(centre[0]-it.x-w),(1,0)),
               (abs(centre[1]-it.y),(0,-1)),(abs(centre[1]-it.y-h),(0,1))]
        _,unit=min(faces)
        # 25um is a declared analytical centre clearance, not a hardened slice.
        portal=(centre[0]+unit[0]*25,centre[1]+unit[1]*25)
        points.append(portal)
        evidence.append(dict(instance=name,master=it.master,port=port,
            lef=str(p.relative_to(V.ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
            physical_pins_um=pts,portal_um=portal,
            max_pin_to_portal_um=max(abs(q[0]-portal[0])+abs(q[1]-portal[1]) for q in pts)))
    result=dict(schema='opentallas.hbm_relay_channel_probe.v1',bus=a.bus,
        status='geometry-probe-not-RTL-or-placement-qualified',
        obstacle_source='generator instance boxes; real endpoint LEF pin positions',
        input_sha256={str(Path(p).relative_to(V.ROOT)):hashlib.sha256(Path(p).read_bytes()).hexdigest()
                      for p in (V.__file__,V.H.__file__,V.L.__file__)},
        assumed_station_centre_clearance_um=20,assumed_portal_offset_um=25,
        endpoints=evidence,all_endpoint_pins_within_100um=all(
            e['max_pin_to_portal_um']<=100 for e in evidence))
    try:
        result['path_um']=channel_path(*points,[it.box() for it in m['insts']],
                                     (m['geo']['W'],m['geo']['H']),20)
    except ValueError as e:
        result['geometry_failure']=str(e)
    result['next_gate']='real matched slice dimensions/pin locations; no route or hardware adoption authorized by this probe'
    Path(a.out).parent.mkdir(parents=True,exist_ok=True)
    Path(a.out).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='endpoints'}))

if __name__=='__main__':
    main()
