#!/usr/bin/env python3
"""Move raw reset export pins off real same-layer pin rectangles; no RTL edits."""
import argparse
import json
import math
from pathlib import Path
import re

PIN = re.compile(r'place_pin -pin_name (\{[^}]*\}|\S+) -layer (\w+) -location \{([\d.-]+) ([\d.-]+)\} -pin_size \{([\d.]+) ([\d.]+)\}')

def overlap(a, b, gap=0.):
    return a['layer'] == b['layer'] and abs(a['x']-b['x']) < (a['w']+b['w'])/2+gap-1e-8 and abs(a['y']-b['y']) < (a['h']+b['h'])/2+gap-1e-8

def fix(raw, io_dir):
    changes, before, after = [], [], []
    for path in sorted(Path(io_dir).glob('*.io.tcl')):
        tn = path.name.removesuffix('.io.tcl')
        if tn not in raw['partition_types']:
            continue
        pins = [dict(name=m[1].strip('{}'), layer=m[2], **dict(zip(('x','y','w','h'),map(float,m.group(3,4,5,6))))) for m in PIN.finditer(path.read_text())]
        raw_pins = [p for p in pins if p['name'].startswith('rst_start_raw_')]
        for a in raw_pins:
            for b in pins:
                if a['name'] < b['name'] or not b['name'].startswith('rst_start_raw_'):
                    if a != b and overlap(a,b):
                        before.append(dict(type=tn, ports=[a['name'], b['name']], centres=[[a['x'],a['y']],[b['x'],b['y']]]))
        declared = {p['name']:p for p in raw['partition_types'][tn].get('clock',{}).get('landing_contract',{}).get('pins',[])}
        taken = [p for p in pins if not p['name'].startswith('rst_start_raw_')]
        for pin in sorted(raw_pins, key=lambda p:p['name']):
            original = [pin['x'],pin['y']]
            if any(overlap(pin,b,.032) for b in taken):
                assert pin['layer'] == 'M7', (tn,pin)
                centre = (pin['x']-.032)/.064
                tracks = sorted({round(.032+.064*k,4) for k in range(math.floor(centre)-32,math.ceil(centre)+33)}, key=lambda x:(abs(x-pin['x']),x))
                if tn == 'hd_mesh_e' and pin['name'] == 'rst_start_raw_1':
                    tracks = [558.880] + [x for x in tracks if x != 558.880]
                width = raw['partition_types'][tn]['outline_um'][0]
                for x in tracks:
                    candidate = dict(pin,x=x)
                    if pin['w']/2 <= x <= width-pin['w']/2 and not any(overlap(candidate,b,.032) for b in taken):
                        pin['x'] = x
                        break
                else:
                    raise ValueError(f'{tn}.{pin["name"]}: no free M7 pin rectangle')
                declared[pin['name']]['xy_um'] = [pin['x'],pin['y']]
                changes.append(dict(type=tn,port=pin['name'],old_um=original,new_um=[pin['x'],pin['y']],pin_size_um=[pin['w'],pin['h']],dx_um=round(pin['x']-original[0],4)))
            taken.append(pin)
        for a in raw_pins:
            for b in pins:
                if a != b and overlap(a,b):
                    after.append(dict(type=tn,ports=[a['name'],b['name']]))
    if after:
        raise ValueError(after)
    return dict(changes=changes,overlaps_before=before,overlaps_after=after,added_cycles=0,rtl_changed=False,clock_pins_moved=False,min_rectangle_gap_um=.032)

if __name__ == '__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan');ap.add_argument('io_dir');ap.add_argument('out')
    args=ap.parse_args()
    raw=json.loads(Path(args.plan).read_text())
    report=fix(raw,args.io_dir)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    (out/'source_plan.json').write_text(json.dumps(raw,indent=1)+'\n')
    (out/'pin_rect_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
