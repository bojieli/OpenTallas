#!/usr/bin/env python3
"""Recheck exploratory instance homes against a current exported physical graph.

This is a compatibility/rectangle check, never a relay, routing or timing receipt.
Every incident bus of a moved or changed instance is enumerated for revalidation.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(old, current, homes):
    oi = {i['n']: i for i in old['insts']}
    ci = {i['n']: i for i in current['insts']}
    hs = homes['homes']
    changed = []
    moved = []
    placed = []
    for name, inst in ci.items():
        h = hs.get(name)
        if h is None:
            continue
        prior = oi.get(name, {})
        fields = [k for k in ('m', 'w', 'h') if prior.get(k) != inst.get(k)]
        if h['m'] != inst['m'] and 'm' not in fields:
            fields.append('m')
        oldmaster = old.get('masters', {}).get(prior.get('m'))
        newmaster = current.get('masters', {}).get(inst['m'])
        if oldmaster != newmaster:
            fields.append('master_pin_geometry')
        if fields:
            changed.append(dict(instance=name, changed=fields, old_master=prior.get('m'), current_master=inst['m']))
        rect = dict(inst, x=h['x'], y=h['y'], o=h['o'])
        placed.append(rect)
        if any(rect[k] != inst[k] for k in ('x', 'y', 'o')):
            moved.append(name)
    affected = set(moved) | {r['instance'] for r in changed}
    oldbus = {b['b']: b for b in old['buses']}
    incident = []
    changed_buses = []
    for b in current['buses']:
        if any(n in affected for n, _ in b['e']):
            incident.append(dict(bus=b['b'], bits=b['n'], endpoints=b['e']))
        if b != oldbus.get(b['b']):
            changed_buses.append(b['b'])
    mapping = homes.get('logical_tile_map', {})
    map_errors = []
    if len(set(mapping.values())) != len(mapping):
        map_errors.append(dict(reason='non_bijective_logical_map'))
    for src, dst in mapping.items():
        if src not in ci or dst not in ci:
            map_errors.append(dict(source=src, destination=dst, reason='missing_current_instance'))
        elif ci[src]['m'] != ci[dst]['m']:
            map_errors.append(dict(source=src, destination=dst, reason='master_mismatch',
                                   source_master=ci[src]['m'], destination_master=ci[dst]['m']))
    overlaps = []
    outside = []
    die = current['die']
    for j, a in enumerate(placed):
        if a['x'] < 0 or a['y'] < 0 or a['x'] + a['w'] > die['w'] + 1e-6 or a['y'] + a['h'] > die['h'] + 1e-6:
            outside.append(a['n'])
        for b in placed[j + 1:]:
            dx = min(a['x'] + a['w'], b['x'] + b['w']) - max(a['x'], b['x'])
            dy = min(a['y'] + a['h'], b['y'] + b['h']) - max(a['y'], b['y'])
            if dx > 1e-6 and dy > 1e-6:
                overlaps.append(dict(a=a['n'], b=b['n'], overlap_um=[round(dx, 6), round(dy, 6)]))
    missing = sorted(set(ci) - set(hs))
    extra = sorted(set(hs) - set(ci))
    return dict(schema='opentallas.qwen.candidate-homes-audit.v1', candidate=homes['candidate'],
        qualification=False, current_source_commit=current.get('source_commit'),
        scope='Current master rectangles and complete incident-bus inventory; no relay allocation, cut, clock, route or timing proof',
        instance_count=len(ci), covered_instances=len(placed), missing_homes=missing, extra_homes=extra,
        changed_instances=changed, moved_instances=moved, changed_buses=changed_buses,
        logical_map_errors=map_errors,
        retired_buses=sorted(set(oldbus) - {b['b'] for b in current['buses']}),
        incident_buses_requiring_recheck=incident, rectangle_overlaps=overlaps, outside_die=outside,
        compatible_for_geometry_recheck=not(missing or extra or changed or changed_buses or map_errors or overlaps or outside),
        unresolved=['Actual registered-pin reach per endpoint', 'Real relay rectangles, ownership and channel cuts',
                    'Clock insertion/phase and reset delivery after movement', 'Current compiler calendar and source producers for newly exposed inputs',
                    'Physical area of train24 banks and new VM writeback ports'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--old-graph', type=Path, required=True)
    p.add_argument('--current-graph', type=Path, required=True)
    p.add_argument('--homes', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    old, current, homes = (json.loads(q.read_text()) for q in (a.old_graph, a.current_graph, a.homes))
    r = audit(old, current, homes)
    r['inputs'] = {k: dict(path=str(v), sha256=digest(v)) for k, v in
                   [('old_graph', a.old_graph), ('current_graph', a.current_graph), ('homes', a.homes)]}
    r['homes_source_matches_old_graph'] = homes['source_graph_sha256'] == digest(a.old_graph)
    r['compatible_for_geometry_recheck'] &= r['homes_source_matches_old_graph']
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps({k: len(r[k]) if isinstance(r[k], list) else r[k] for k in
                     ['candidate', 'covered_instances', 'changed_instances', 'changed_buses', 'rectangle_overlaps', 'outside_die', 'compatible_for_geometry_recheck']}))


if __name__ == '__main__':
    main()
