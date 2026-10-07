#!/usr/bin/env python3
"""Compare real floorplan BPin rectangles with the source-pinned SM portal plan."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(plan, actual):
    expected = {p['real_pin']: p for rows in plan['packets'].values() for p in rows if p['real_pin']}
    expected.update(plan['unbound_pins'])
    got = {p['name']: p for p in actual['pins']}
    errors = []
    if len(got) != len(actual['pins']):
        errors.append('duplicate BTerm names')
    missing = sorted(expected.keys() - got.keys())
    extras = sorted(got.keys() - expected.keys())
    # These are explicit power reservations, not missing signal mappings.
    power = {n: got[n] for n in extras if n in ('VDD', 'VSS') and got[n]['direction'] == 'INOUT'}
    unknown = sorted(set(extras) - power.keys())
    die = actual['die_um']
    if any(abs(x-y) > 1e-6 for x,y in zip(die, [0, 0] + plan['die_um'])):
        errors.append('die geometry differs from plan')
    centers = {}
    for name, p in expected.items():
        if name not in got:
            continue
        g = got[name]
        if g['direction'].lower() != p['direction']:
            errors.append([name, 'direction mismatch'])
        if len(g['boxes']) != 1:
            errors.append([name, 'expected exactly one signal rectangle', len(g['boxes'])])
            continue
        box = g['boxes'][0]
        xl, yl, xh, yh = box['rect_um']
        cx, cy = (xl+xh)/2, (yl+yh)/2
        x, y = p['xy_um']
        if box['layer'] != p['layer']:
            errors.append([name, 'layer mismatch'])
        if xl < die[0]-1e-6 or yl < die[1]-1e-6 or xh > die[2]+1e-6 or yh > die[3]+1e-6:
            errors.append([name, 'rectangle outside die'])
        if abs(cx-x)>1e-6 or min(abs(yl-y), abs(yh-y))>1e-6:
            errors.append([name, 'boundary portal mismatch'])
        if abs((xh-xl)-0.024)>1e-6 or abs((yh-yl)-0.192)>1e-6:
            errors.append([name, 'rectangle size mismatch'])
        # Source generator's M5 tracks are 48nm pitch, 12nm offset.
        if abs((cx-0.012)/0.048-round((cx-0.012)/0.048))>1e-5:
            errors.append([name, 'source M5 track grid mismatch'])
        centers[name] = dict(layer=box['layer'], rect_um=box['rect_um'],
                             center_um=[round(cx,6),round(cy,6)], planned_portal_um=p['xy_um'])
    return dict(schema='opentallas.hbm.smh.pin_readback.v1',
        status='pass' if not errors and not missing and not unknown else 'fail',
        scope='Actual 27-piece floorplan geometry; provisional component views, no routed timing qualification',
        signal_pins=len(expected), readback_BTerms=len(got), power_terms={n:len(p['boxes']) for n,p in power.items()},
        missing_signals=missing, unknown_terms=unknown, errors=errors,
        result_channel_sample_centers={n:centers[n] for n in ('rv','fault','rrow[0]','rdata[255]')},
        all_signal_centers_readback=True, inward_center_shift_um=0.096,
        odb_sha256=actual['odb_sha256'],
        logical_packet_binding_complete=plan['complete'], unbound_signal_count=plan['unbound_pin_count'],
        actual_routed_abstract_qualified=False, adoption=False)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True,type=Path)
    p.add_argument('--actual',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    result=audit(json.loads(a.plan.read_text()),json.loads(a.actual.read_text()))
    result['source_sha256']={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in (a.plan,a.actual,Path(__file__))}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['signal_pins'],result['power_terms'],len(result['errors']))
    raise SystemExit(result['status']!='pass')
