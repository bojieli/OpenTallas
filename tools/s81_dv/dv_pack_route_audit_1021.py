#!/usr/bin/env python3
"""Measure actual planned paths, enforce registered arcs <=405, price deltas.

Station anchors are macro-free construction points. Actual relay-master bodies,
pin reprojection and placement legalization remain required and are not waived.
"""
import argparse
import collections
import copy
import json
import math
from pathlib import Path


def path_of(link):
    pts = [tuple(link['h'][0][:2])]
    for h in link['h']:
        q = tuple(h[2:4])
        if q == pts[-1]:
            continue
        if len(pts) > 1 and (pts[-2][0] == pts[-1][0] == q[0] or pts[-2][1] == pts[-1][1] == q[1]):
            pts[-1] = q
        else:
            pts.append(q)
    edges = []
    length = 0.0
    for a, b in zip(pts, pts[1:]):
        end = length + abs(b[0] - a[0]) + abs(b[1] - a[1])
        edges.append((length, end, a, b)); length = end
    return edges, length


def at(edges, distance):
    for lo, hi, a, b in edges:
        if distance <= hi + 1e-7:
            z = (distance - lo) / (hi - lo) if hi > lo else 0
            return [a[0] + z * (b[0] - a[0]), a[1] + z * (b[1] - a[1])]
    return list(edges[-1][3])


def spans(link):
    result, distance, i = [], 0.0, 0
    stations = link.get('sp', [])
    for x0, y0, x1, y1, _ in link['h']:
        distance += abs(x1 - x0) + abs(y1 - y0)
        if i < len(stations) and abs(x1 - stations[i][0]) + abs(y1 - stations[i][1]) < 1e-3:
            result.append(distance); distance = 0.0; i += 1
    assert i == len(stations), (link['i'], i, len(stations))
    result.append(distance)
    return result


def strict_stations(plan):
    result = copy.deepcopy(plan)
    changed = []
    for link in result['links']:
        if 'h' not in link:
            continue
        edges, length = path_of(link)
        corners = [e[1] for e in edges[:-1]]
        cuts, last = [], 0.0
        while length - last > 405.0 + 1e-6:
            preferred = last + 350.0
            candidates = [preferred] + [c + side * 50.0 for c in corners for side in (-1, 1)]
            valid = [t for t in candidates if last + 50 <= t <= last + 405 and t < length and all(abs(t - c) >= 50 - 1e-6 for c in corners)]
            if not valid:
                raise ValueError(('no 405um station site away from bends', link['i'], last, length))
            last = min(valid, key=lambda t: (abs(t - preferred), t)); cuts.append(last)
        old_s = link.get('s', 0)
        link['sp'] = [at(edges, t) for t in cuts]
        link['s'] = len(cuts)
        marks = sorted({0.0, length, *corners, *cuts})
        link['h'] = [[*at(edges, a), *at(edges, b), link['b']] for a, b in zip(marks, marks[1:])]
        link.pop('station_dirs', None)
        assert max(spans(link)) <= 405 + 1e-4
        if old_s != link['s']:
            changed.append(dict(link=link['i'], old=old_s, new=link['s'], delta_edges=link['s'] - old_s))
    result['facts']['physical72']['relay_405_constructor'] = dict(max_arclength_um=405, target_um=350, bend_clearance_um=50,
        changes=changed, scope='Actual path arclength between planned registered anchors; real relay bodies/pins/placement remain unqualified')
    return result


def measure(plan):
    vertical, horizontal = collections.Counter(), collections.Counter()
    contributors = collections.defaultdict(set)
    window = 260.0
    capacity = window * (0.75 / 0.080 + 0.75 / 0.064)
    arc_violations = []
    maximum = 0.0
    for link in plan['links']:
        if 'h' not in link:
            continue
        arc = spans(link); maximum = max(maximum, max(arc))
        if max(arc) > 405 + 1e-4:
            arc_violations.append(dict(link=link['i'], max_arc_um=max(arc)))
        seen = set()
        for x0, y0, x1, y1, bits in link['h']:
            for k in range(int(min(x0, x1) // window) + 1, int(math.ceil(max(x0, x1) / window))):
                seen.add(('V', k, int(y0 // window)))
            for k in range(int(min(y0, y1) // window) + 1, int(math.ceil(max(y0, y1) / window))):
                seen.add(('H', k, int(x1 // window)))
        for direction, k, j in seen:
            target = vertical if direction == 'V' else horizontal
            target[(k, j)] += link['b']; contributors[(direction, k, j)].add(link['i'])
    cuts = [(value, direction, k, j) for direction, counter in [('V', vertical), ('H', horizontal)] for (k, j), value in counter.items()]
    top = sorted(cuts, reverse=True)[:20]
    return dict(blocks=len(plan['blocks']), links=len(plan['links']), frames=sum(b['kind'] == 'frame' for b in plan['blocks']),
        routing_failures=plan['facts']['physical72'].get('routing_failures'), relay_stations=sum(l.get('s', 0) for l in plan['links']),
        relay_bit_stages=sum(l.get('s', 0) * l['b'] for l in plan['links']), bit_mm=sum(l.get('L', 0) * l['b'] for l in plan['links']) / 1000,
        max_registered_arc_um=maximum, arc_violations=arc_violations,
        cut_method=dict(window_um=window, raw_tracks=capacity, layers_pitch_um=[0.080, 0.064], available_fraction_each=0.75,
            source='existing tools/fleet_viz/dataflow_links.py cut construction; diagnostic traffic count, not PG/via/electrical or GRT admission'),
        worst_cut_ratio=top[0][0] / capacity if top else 0,
        windows_above_historical_0_60=sum(value / capacity > 0.60 for value, _, _, _ in cuts),
        top_cuts=[dict(direction=d, coordinate_um=k * window, interval_um=[j * window, (j + 1) * window], bits=value,
            ratio=value / capacity, links=sorted(contributors[(d, k, j)])) for value, d, k, j in top])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--baseline', required=True)
    ap.add_argument('--main', required=True)
    ap.add_argument('--fallback', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args(); out = Path(args.out_dir); out.mkdir(parents=True, exist_ok=True)
    plans = {k: json.loads(Path(getattr(args, k)).read_text()) for k in ('baseline', 'main', 'fallback')}
    record = {}
    baseline_stages = {l['i']: l.get('s', 0) for l in plans['baseline']['links']}
    for variant, plan in plans.items():
        repaired = strict_stations(plan)
        original, strict = measure(plan), measure(repaired)
        delta = [dict(link=l['i'], old_edges=baseline_stages[l['i']], candidate_edges=l.get('s', 0),
                      delta_edges=l.get('s', 0) - baseline_stages[l['i']]) for l in repaired['links'] if l.get('s', 0) != baseline_stages[l['i']]]
        record[variant] = dict(original=original, strict=strict, delta_vs_original_G8=delta,
            pricing='Every relay is an actual source relay stage in the plan; compiler/landed calendar must consume each per-link delta before adoption')
        (out / f'{variant}_routed_405.json').write_text(json.dumps(repaired, indent=1) + '\n')
    (out / 'routing_audit.json').write_text(json.dumps(record, indent=1) + '\n')
    print(json.dumps({v: {k: data['strict'][k] for k in ('relay_stations', 'max_registered_arc_um', 'worst_cut_ratio', 'windows_above_historical_0_60')}
                      for v, data in record.items()}))


if __name__ == '__main__':
    main()
