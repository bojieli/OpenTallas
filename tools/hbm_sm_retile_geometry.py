#!/usr/bin/env python3
"""Export the full-size 32-SM placement candidate; no network/closure claim."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def report():
    m = H.build(H.R24SM3, geometry_only=True)
    sms = [i for i in m['insts'] if i.kind == 'sm']
    regions = H.clock_regions(m)
    return dict(status='geometry-only-unqualified-network', selected=False,
        source_sha256=hashlib.sha256(Path(H.__file__).read_bytes()).hexdigest(),
        sizing_model='tools/hbm_w2_slot_model.py at ac7d9ee59',
        outline=[m['geo']['W'], m['geo']['H']], geo=m['geo'],
        insts=[dict(name=i.name, master=i.master, x=i.x, y=i.y, w=i.w, h=i.h,
                    box=i.box(), orient=i.orient, kind=i.kind,
                    sm=getattr(i, 'sm', None)) for i in m['insts']],
        legality=H.legality(m), clock_regions=regions, buses=[],
        full_shape_sm_count=len(sms), sm_dimensions_um=list(H.R24SM3['sm_wh']),
        active_sites_per_group=8, empty_sites_per_group=1,
        perimeter_clearance=dict(padding_per_side_um=H.R24SM3['side_padding_um'],
            reason='SerDes end reaches 5971.896um; unpadded south band only5767.76um',
            added_height_um=2*H.R24SM3['side_padding_um'],
            added_area_mm2=2*H.R24SM3['side_padding_um']*m['geo']['W']/1e6),
        preserved_contract='sm0..sm31 identity, logical4x2 row/col and orientations; no port remapping',
        remaining_gates=['actual fixed-pin binding', 'logical network to physical channels',
            'shared corridor capacity and balanced relay latency',
            'physical clock delivery for three geometric column regions per stack',
            'token latency and energy composition', 'SS/FF timing, DRC and IR'])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    r = report()
    assert r['legality']['overlaps'] == r['legality']['outside'] == 0
    assert r['full_shape_sm_count'] == 32
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({k: r[k] for k in ('status', 'outline', 'legality', 'full_shape_sm_count')}))
