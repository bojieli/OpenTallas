#!/usr/bin/env python3
"""Admitted exact native pin identity, mirror-track and topology inventory gate.

This validates native abstracts; it does not establish routed timing or replace
the source-owned service/selector producer joins.
"""
import argparse
import json
from pathlib import Path

import hbm_accel_die_fp as F


def native_pins(m):
    out = []
    for it in m['insts']:
        if not it.name.startswith(('idx_score_', 'idx_selector')):
            continue
        rec = json.loads((F.ROOT / 'physical/hbm_accel_die_views/index/native' / it.master / 'ports.json').read_text())
        mst = F.Q.Master(it.master, it.w, it.h, 7, 'native')
        m['fixed_ports'][it.master](mst, 1)
        widths = {n:p['bits'] for n,p in rec['ports'].items()}
        generated = F.S.pin_rects(mst, 1, widths)
        expected = [(p[0],p[1],tuple(p[2:])) for port in rec['ports'].values() for p in port['pins']]
        if generated != expected:
            raise ValueError(f'{it.name}: assembled pin identity/rectangles differ from hardened record')
        failures=[]
        for nm,ly,(x0,y0,x1,y1) in generated:
            x,y=(x0+x1)/2,(y0+y1)/2
            if it.orient in ('MY','R180'): x=it.w-x
            if it.orient in ('MX','R180'): y=it.h-y
            x,y=x+it.x,y+it.y
            coord = y if ly in ('M4','M6') else x
            phase,pitch = (0.012,0.048) if ly in ('M4','M5') else (0.016,0.064)
            error=abs((coord-phase)/pitch-round((coord-phase)/pitch))*pitch
            if error>1e-6: failures.append(dict(pin=nm,layer=ly,track_error_um=round(error,6)))
        out.append(dict(instance=it.name,master=it.master,orient=it.orient,
            origin_um=[it.x,it.y],outline_um=[it.w,it.h],pins=len(generated),
            exact_record_identity=True,offtrack_count=len(failures),examples=failures[:3]))
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    historical=F.build(F.R25IQ,geometry_only=True)
    negative=native_pins(historical)
    selected=F.build(F.R25IQG)
    pins=native_pins(selected)
    instances=selected['insts']
    overlaps=[]
    for i,a in enumerate(instances):
        for b in instances[i+1:]:
            if min(a.x+a.w,b.x+b.w)>max(a.x,b.x)+1e-6 and min(a.y+a.h,b.y+b.h)>max(a.y,b.y)+1e-6:
                overlaps.append([a.name,b.name])
    outside=[a.name for a in instances if a.x<0 or a.y<0 or a.x+a.w>selected['geo']['W']+1e-6 or a.y+a.h>selected['geo']['H']+1e-6]
    native_buses=[b for b in selected['buses'] if b[1]=='index_native']
    verdict='PASS' if all(x['offtrack_count']==0 for x in pins) and not overlaps and not outside and any(x['offtrack_count'] for x in negative) else 'FAIL'
    record=dict(schema='opentallas.hbm_native_pin_gate.v1',variant='R25IQG',verdict=verdict,
        native_pins=pins,historical_R25IQ_negative=negative,instances=len(instances),
        native_bus_segments=len(native_buses),overlaps=overlaps,outside=outside,
        qualification='Exact native abstract identity and track/bbox gate only; routed timing, legacy pins, service joins and actual clock arrival remain unqualified')
    args.out.write_text(json.dumps(record,indent=1)+'\n')
    print(verdict, 'instances',len(instances),'native_segments',len(native_buses),'native_pins',sum(x['pins'] for x in pins),'offtrack',sum(x['offtrack_count'] for x in pins),'overlaps',len(overlaps),'outside',len(outside))
    if verdict!='PASS': raise SystemExit(1)


if __name__=='__main__': main()
