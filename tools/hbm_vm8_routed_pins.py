#!/usr/bin/env python3
"""Compare a real VM8 routed LEF against the complete requested pin contract."""
import argparse
import hashlib
import json
from pathlib import Path
from hbm_die_views import parse_lef


def audit(lef, contract):
    real = parse_lef(lef)
    want = contract['masters'][real['name']]
    pins = {k.replace('\\', ''): v for k, v in real['pins'].items()}
    missing = sorted(set(want['pins']) - set(pins))
    extra = sorted(set(pins) - set(want['pins']))
    mismatch = []
    for name in sorted(set(pins) & set(want['pins'])):
        layer, x, y, w, h = want['pins'][name]
        target = (x-w/2, y-h/2, x+w/2, y+h/2)
        direction = want['ports'][name.split('[')[0]]['direction'].upper()
        shape_ok = any(ly == layer and max(abs(a-b) for a,b in zip(rect,target)) <= 0.00011 for ly,rect in pins[name]['rects'])
        if not shape_ok or pins[name]['dir'] != direction:
            mismatch.append(dict(pin=name, requested=dict(layer=layer,rect=target,direction=direction),actual=pins[name]))
    outline_ok = abs(real['w']-want['width_um'])<=0.00011 and abs(real['h']-want['height_um'])<=0.00011
    return dict(master=real['name'],lef=str(lef),lef_sha256=hashlib.sha256(Path(lef).read_bytes()).hexdigest(),
        verdict='PASS' if outline_ok and not (missing or extra or mismatch) else 'FAIL',
        scope='Exact routed LEF pin names, directions, layer and rectangle against requested placement; does not qualify timing.',
        outline_ok=outline_ok,expected_pins=len(want['pins']),actual_pins=len(pins),missing=missing,extra=extra,mismatches=mismatch)


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('lef',type=Path);p.add_argument('--contract',type=Path,default=Path('results/physical/hbm_vm8_contract_20261007/contract.json'));p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=audit(a.lef,json.loads(a.contract.read_text()));a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['verdict'],result['master'],len(result['mismatches']));raise SystemExit(result['verdict']!='PASS')
