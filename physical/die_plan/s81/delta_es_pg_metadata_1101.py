#!/usr/bin/env python3
"""Reconcile ES0/ES1 PHY metadata with the existing MY placed u_phy.

Same correction as pg_es_fix_1029.py, including its missing IO-window update.
No geometry, netlist, domain grid, period or latency is changed.  The old
pg_es_fix_ir_1029.json measures this unchanged domain with the corrected bump
box (worst core VDD 17.59 mV, PHY 9.82 mV).  Run on the current plan in place.
"""
import copy
import json
import math
import sys
from pathlib import Path


def update(plan):
    before = copy.deepcopy(plan)
    parts = {q['name']: q for q in plan['partitions']}
    windows = {q['name']: q for q in plan['die']['io']}
    report = []
    for domain in plan['die']['pg']['domains']:
        if domain['name'] not in ('phy_lk_ES0', 'phy_lk_ES1'):
            continue
        part = parts[domain['name'][4:]]
        typ = plan['partition_types'][part['type']]
        contents = typ['contents']
        contents = json.loads(contents) if isinstance(contents, str) else contents
        macro = next(c for c in contents if c['inst'] == 'u_phy')
        assert part['orient'] == 'MY'
        ox, oy = part['origin_um']; w, h = typ['outline_um']
        x, y = macro['origin_um']; mw, mh = macro['outline_um']
        phy = [round(ox+w-x-mw, 4), round(oy+y, 4),
               round(ox+w-x, 4), round(oy+y+mh, 4)]
        r = domain['rect_um']
        assert r[0] <= phy[0] < phy[2] <= r[2]
        assert r[1] <= phy[1] < phy[3] <= r[3]
        strips = [[ox, oy, ox+w, r[1]]]
        if ox < r[0]: strips.append([ox, r[1], r[0], oy+h])
        if r[2] < ox+w: strips.append([r[2], r[1], ox+w, oy+h])
        domain['phy_macro_um'] = phy
        domain['bumps']['rect_um'] = phy[:]
        domain['core_strip_um'] = [[round(v, 4) for v in s] for s in strips]
        for name in domain['io']:
            win = windows[name]
            win['rect_um'] = phy[:]
            pitch = win['pitch_um']
            win['sites'] = math.floor(mw/pitch+1e-6)*math.floor(mh/pitch+1e-6)
            assert win['sites'] >= win['signals']
        report.append(dict(domain=domain['name'], phy_macro_um=phy,
                           unchanged_domain_um=r, core_strip_um=domain['core_strip_um']))
    # Exactly the stale geometry metadata is permitted to change.
    for key in plan:
        if key != 'die': assert plan[key] == before[key], key
    assert len(report) == 2
    return report


def main():
    path = Path(sys.argv[1]); text = path.read_text(); plan = json.loads(text)
    before = copy.deepcopy(plan); report = update(plan)
    # Keep the 49-MB plan's existing compact subtrees byte-identical.
    start = text.index(' "die": {')
    end = text.index(' "partition_types": {', start)
    die = json.dumps({'die': plan['die']}, indent=1).splitlines()[1:-1]
    text = text[:start] + '\n'.join(die) + ',\n' + text[end:]
    assert json.loads(text) == plan
    path.write_text(text)
    print(json.dumps(report, indent=1))


if __name__ == '__main__': main()
