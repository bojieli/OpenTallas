#!/usr/bin/env python3
"""Expand selected ASTK homes into a die plan and check actual child rectangles.

This is a geometry check, not native or timing qualification. In particular the
selected non-PV inventory does not contain the new PV/result/clock-relay leaves.
The north profile's canonical coordinates already encode its child ordering;
only the emitted parent orientation is applied here.
"""
import argparse
import hashlib
import itertools
import json
from pathlib import Path


def overlaps(a, b):
    return (min(a['x'] + a['w'], b['x'] + b['w']) > max(a['x'], b['x']) + 1e-6
            and min(a['y'] + a['h'], b['y'] + b['h']) > max(a['y'], b['y']) + 1e-6)


def check(instances, inventory):
    parents = {i['name']: i for i in instances if i['name'].startswith('astk_')}
    if set(parents) != {'astk_' + s for s in ('WS', 'WN', 'ES', 'EN')}:
        raise ValueError('expected exactly four ASTK parent homes')
    children, outside = [], []
    for home in inventory['children']:
        p = parents['astk_' + home['stack']]
        x, y = home['canonical_x'], home['canonical_y']
        w, h = home['outline']
        if min(x, y) < 0 or x + w > p['w'] + 1e-6 or y + h > p['h'] + 1e-6:
            outside.append(dict(parent=p['name'], child=home['name'],
                                required_extent=[x + w, y + h], available=[p['w'], p['h']]))
        if p['orient'] in ('MY', 'R180'):
            x = p['w'] - x - w
        if p['orient'] in ('MX', 'R180'):
            y = p['h'] - y - h
        if p['orient'] not in ('R0', 'MY', 'MX', 'R180'):
            raise ValueError('unsupported ASTK orientation ' + p['orient'])
        children.append(dict(name=p['name'] + '__' + home['name'], master=home['master'],
                             parent=p['name'], x=round(p['x'] + x, 6), y=round(p['y'] + y, 6),
                             w=w, h=h, orient=p['orient'], straps=home['straps']))
    names = [c['name'] for c in children]
    if len(names) != len(set(names)):
        raise ValueError('duplicate selected child')
    peers = [i for i in instances if i['name'] not in parents]
    collisions = [[a['name'], b['name']] for a, b in itertools.combinations(children, 2) if overlaps(a, b)]
    collisions += [[a['name'], b['name']] for a in children for b in peers if overlaps(a, b)]
    return dict(schema='opentallas.astk_selected_home_fit.v1',
                scope='SELECTED_NON_PV_GEOMETRY_ONLY', native_qualified=False,
                selected_children=len(children), parent_outside=outside, overlaps=collisions,
                parents=list(parents.values()), children=children,
                open=['Selected source/profile/view join and measured pin/phi-R timing',
                      'New PV and result-collector homes', 'Actual ck_r relay physical home'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--instances', type=Path, required=True)
    ap.add_argument('--homes', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    r = check(json.loads(a.instances.read_text()), json.loads(a.homes.read_text()))
    r['inputs'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (a.instances, a.homes)}
    a.out.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({k: r[k] for k in ('scope', 'selected_children', 'parent_outside', 'overlaps')}))
    return int(bool(r['parent_outside'] or r['overlaps']))


if __name__ == '__main__':
    raise SystemExit(main())
