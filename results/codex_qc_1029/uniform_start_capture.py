#!/usr/bin/env python3
"""Use the actual origin RTL clk input, with a uniform adjacent physical START pin."""
import argparse
import collections
import json
import re
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'tree', 'bind', 'tools', 'out'):
        ap.add_argument('--'+name, type=Path, required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(a.tools))
    import schema as S
    import gen_phys as GP
    raw = json.loads(a.plan.read_text())
    plan = S.Plan(raw)
    tree = json.loads(a.tree.read_text())
    bind = json.loads(a.bind.read_text())
    taps = collections.defaultdict(dict)
    for tap in tree['taps']:
        if re.fullmatch(r'clk(?:_t\d+)?', tap['tap']):
            taps[tap['part']][tap['tap']] = tap
    captures = {e['dst']: e['capture_part'] for e in bind['start_ports'].values()
                if e.get('capture_part')}
    by_type = collections.defaultdict(set)
    for part in captures.values():
        by_type[plan.parts[part]['type']].add(part)
    choice, details = {}, []
    for tn, parts in sorted(by_type.items()):
        # _origin_rtl and landing rings consume .clk(clk). Selecting a different
        # measured GLUE tap without an actual hardware clock rebind would make
        # the phase model fictitious, even if its geometry were preferable.
        common = set.intersection(*(set(taps[p]) for p in parts)) & {'clk'}
        root = plan.types[tn]['clock']['tap_um']
        candidates = []
        for name in common:
            local = [plan.to_type(p, taps[p][name]['xy']) for p in sorted(parts)]
            if any(max(abs(x-y) for x,y in zip(local[0], xy)) > 1e-5 for xy in local):
                continue
            dist = sum(abs(x-y) for x,y in zip(local[0],root))
            candidates.append((dist,name,local[0]))
        if not candidates:
            raise ValueError(f'no uniform measured native RTL clk for {tn}: {parts}')
        _, name, xy = min(candidates)
        choice[tn] = name
        pins = plan.types[tn]['clock']['landing_contract']['pins']
        pin = next(p for p in pins if p['name']=='cland_tstart_in')
        old = pin['xy_um']
        # Physical input is beside the actual existing capture clock pin.
        # Internal FF placement and register-clock leg remain a kit gate.
        found = None
        w,h = plan.types[tn]['outline_um']
        for dx,dy in ((2.16,0),(-2.16,0),(0,2.16),(0,-2.16)):
            point = list(GP._snap_tap(plan,xy[0]+dx,xy[1]+dy))
            if not (.432 < point[0] < w-.432 and .432 < point[1] < h-.432):
                continue
            if any(p['name'] != pin['name'] and p.get('layer')==pin.get('layer')
                   and abs(p['xy_um'][0]-point[0]) < .08
                   and abs(p['xy_um'][1]-point[1]) < .432 for p in pins):
                continue
            found = point
            break
        if found is None:
            raise ValueError(f'no noncolliding capture-adjacent pin for {tn}')
        pin['xy_um'] = found
        details.append(dict(type=tn,instances=len(parts),capture_tap=name,
            capture_xy_um=xy,old_pin_xy_um=old,pin_xy_um=found,
            pin_to_tap_um=sum(abs(x-y) for x,y in zip(xy,found))))
    overrides = {region: taps[part][choice[plan.parts[part]['type']]]['port']
                 for region,part in sorted(captures.items())}
    a.out.mkdir(parents=True,exist_ok=True)
    (a.out/'capture_taps.json').write_text(json.dumps(overrides,indent=1)+'\n')
    (a.out/'capture_pins.json').write_text(json.dumps(dict(types=details,
        regions=len(overrides),physical_internal_reach='NOT RUN',
        adoption='REQUIRES new CA plan, boot price, actual FF placement and phase gate'),indent=1)+'\n')
    (a.out/'plan.json').write_text(json.dumps(raw,indent=1)+'\n')
    print(f'{len(overrides)} regions, {len(details)} uniform capture types; REPLAN REQUIRED')


if __name__=='__main__':
    main()
