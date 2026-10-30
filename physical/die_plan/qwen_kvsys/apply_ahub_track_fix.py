#!/usr/bin/env python3
"""Create the one-block AHUB track repair; never edits the source plan or pin table."""
import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'tools/die_plan'))
import schema as S
import landing_contract as LC


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--plan-out', type=Path, required=True)
    ap.add_argument('--pins-out', type=Path, required=True)
    a = ap.parse_args()
    assert a.plan.resolve() != a.plan_out.resolve(), 'source plan is immutable'
    assert a.plan_out.parent.resolve() == a.plan.parent.resolve(), 'retain relative-reference base'
    raw = json.loads(a.plan.read_text())
    P = S.Plan(raw)
    c = next(h for h in raw['partition_types']['kv3_hub_C']['hard_cores'] if h['inst'] == 'ahub')
    source = a.plan.parent / c['pins_file']
    assert source.resolve() != a.pins_out.resolve(), 'source pins are immutable'
    old = json.loads(source.read_text())
    pins = copy.deepcopy(old)
    changed = []
    for q in pins['pins']:
        if q['name'] not in ('ck[3]', 'ck[4]', 'ck[5]', 'ck[6]'):
            continue
        before = copy.deepcopy(q)
        x, y = LC.on_track(P, q['layer'], q['x'] + c['origin_um'][0], q['y'] + c['origin_um'][1])
        q['x'], q['y'] = round(x - c['origin_um'][0], 6), round(y - c['origin_um'][1], 6)
        assert q['y'] == before['y'] and abs(q['x'] - before['x']) <= .024001
        changed.append(dict(pin=q['name'], before=before, after=q))
    assert len(changed) == 4
    a.pins_out.write_text(json.dumps(pins, indent=1) + '\n')
    c['pins_file'] = str(a.pins_out.resolve().relative_to(a.plan.parent.resolve()))
    a.plan_out.write_text(json.dumps(raw, indent=1) + '\n')
    print(json.dumps(changed, indent=1))


if __name__ == '__main__':
    main()
