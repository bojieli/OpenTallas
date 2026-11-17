#!/usr/bin/env python3
"""Measured per-interface frame variants, explicitly selected by a plan/type cohort.

A profile carries native-tracer before/after depths, never a blanket frame delay.
Only a source-matching, explicitly enabled cohort may use it. Mixed cohorts need
separate schedules. Physical bind/LAT and production throughput still gate use.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

SCHEMA = 'opentallas.s81.frame_visibility_profile.v1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def interfaces(measure):
    out = {}
    for elem, st in measure['stations'].items():
        for kind in ('inputs', 'control'):
            for pin, labels in st[kind].items():
                out[f'stations/{elem}/{kind}/{pin}'] = labels
    for node, pins in measure['nodes'].items():
        for pin, labels in pins.items():
            out[f'nodes/{node}/{pin}'] = labels
    if measure.get('root') is not None:
        out['root'] = measure['root']
    for key, labels in measure.get('links', {}).items():
        # Seam summaries are lists of depths; boundary links are source/depth pairs.
        out['links/' + key] = labels
    return out


def difference(before, after, path):
    if before and isinstance(before[0], (list, tuple)):
        a, b = dict(before), dict(after)
        if a.keys() != b.keys():
            raise ValueError(f'{path}: source labels changed')
        return sorted({b[k] - v for k, v in a.items()})
    if len(before) != len(after):
        raise ValueError(f'{path}: depth summary shape changed')
    return sorted({b - a for a, b in zip(before, after)})


def build(before, after, *, cohort, top, source_sha256, partition_types,
          parameters=None, evidence=None):
    before, after = (json.loads(json.dumps(m)) for m in (before, after))
    a, b = interfaces(before), interfaces(after)
    if a.keys() != b.keys():
        raise ValueError('native frame endpoints changed; a depth profile cannot remap ports')
    rows, station_deltas = [], {}
    for path in sorted(a):
        delta = difference(a[path], b[path], path)
        if len(delta) > 1:
            raise ValueError(f'{path}: unequal added delays within one interface: {delta}')
        if path.startswith('stations/'):
            station_deltas.setdefault(path.split('/')[1], set()).update(delta)
        if a[path] != b[path]:
            rows.append(dict(interface=path, before=a[path], after=b[path], delta_edges=delta[0]))
    for elem, delta in station_deltas.items():
        if len(delta) != 1:
            raise ValueError(f'{elem}: data/go/cfg/tag alignment changed: {sorted(delta)}')
    return dict(schema=SCHEMA, cohort=cohort, top=top, source_sha256=source_sha256,
                partition_types=sorted(partition_types), band_module=top.replace('_asb_x', '_r0').replace('_asb_nx', '_r0'), parameters=parameters or {'COLRELAY_P1': 1},
                rows=rows, station_delta_edges={e: next(iter(ds)) for e, ds in station_deltas.items()},
                evidence=evidence or {}, qualification='MEASURED DEPTH PROFILE ONLY: explicit cohort, native bind/LAT, '
                'exact root-consumer calendar and production throughput required')


def validate_selection(profile, root, plan, cohort, top):
    if profile.get('schema') != SCHEMA or profile.get('cohort') != cohort or profile.get('top') != top:
        raise ValueError('internal frame profile/top/cohort mismatch')
    if not cohort:
        raise ValueError('an internal frame variant needs an explicit cohort')
    for path, sha in profile['source_sha256'].items():
        if digest(Path(root) / path) != sha:
            raise ValueError('internal frame profile source changed: ' + path)
    selected = set(profile['partition_types'])
    if not selected:
        raise ValueError('empty internal frame type cohort')
    types = plan['partition_types']
    missing = selected - types.keys()
    if missing:
        raise ValueError('internal frame profile types missing: ' + str(sorted(missing)))
    for name in selected:
        if len([c for c in types[name].get('contents', []) if c.get('module') == profile['band_module']]) != 1:
            raise ValueError('internal frame type must have exactly one selected band: ' + name)
    for name, typ in types.items():
        bands = [c for c in typ.get('contents', []) if c.get('module') == profile['band_module']]
        for band in bands:
            enabled = all(band.get('params', {}).get(k, 0) == v for k, v in profile['parameters'].items())
            if (name in selected) != enabled:
                raise ValueError('internal frame cohort parameter selection differs: ' + name)
    used = {p['type'] for p in plan.get('partitions', [])}
    if used and not selected <= used:
        raise ValueError('internal frame profile includes unused types')


def apply(measure, profile):
    """Apply only native-measured interface changes, refusing a stale before-depth."""
    out = copy.deepcopy(measure)
    got = interfaces(out)
    for row in profile['rows']:
        path = row['interface']
        # JSON tuples/lists are equivalent depth records.
        if json.dumps(got.get(path)) != json.dumps(row['before']):
            raise ValueError('internal frame profile before-depth changed: ' + path)
        keys = path.split('/')
        if keys[0] == 'links':
            out['links'][path[len('links/'):]] = copy.deepcopy(row['after'])
        else:
            target = out
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = copy.deepcopy(row['after'])
    return out


def link_delta(profile, link):
    rows = [r for r in profile['rows'] if r['interface'] == 'links/' + link]
    return rows[0]['delta_edges'] if rows else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before', type=Path, required=True)
    ap.add_argument('--after', type=Path, required=True)
    ap.add_argument('--cohort', required=True)
    ap.add_argument('--top', required=True)
    ap.add_argument('--source-map', type=Path, required=True, help='canonical selected-source relative paths -> SHA256')
    ap.add_argument('--cohort-map', type=Path, required=True, help='plan-derived cohorts with type fields')
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    cohort_map = json.loads(a.cohort_map.read_text())
    result = build(json.loads(a.before.read_text()), json.loads(a.after.read_text()),
                   cohort=a.cohort, top=a.top, source_sha256=json.loads(a.source_map.read_text()),
                   partition_types=[c['type'] for c in cohort_map['cohorts']],
                   evidence=dict(before_measure_sha256=digest(a.before), after_measure_sha256=digest(a.after),
                                 cohort_plan_sha256=cohort_map['source_plan_sha256']))
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print('FRAME_VISIBILITY_PROFILE', a.cohort, len(result['rows']), 'changed interfaces')


if __name__ == '__main__':
    main()
