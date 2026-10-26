#!/usr/bin/env python3
"""Exact centerline relay *requests*, never a placement/route qualification.

The lane file defines a three-leg rectilinear centerline per link. Uniform
arclength stations give the minimum relay count for that fixed centerline and
reach. All crossed blocks, including the endpoint blocks, are reported. A
40-um SU column is checked geometrically; its prose reservation does not prove
available cells, pins, clock delivery, wiring, or timing.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT = ROOT / 'results/arch/hbm_die_v15/compact660_v5'


def segments(p, q, lane):
    a = (p['x'], p['y'])
    d = (q['x'], q['y'])
    if set(lane) == {'h'}:
        points = [a, (a[0], lane['h']), (d[0], lane['h']), d]
    elif set(lane) == {'v'}:
        points = [a, (lane['v'], a[1]), (lane['v'], d[1]), d]
    else:
        raise ValueError(f'Invalid lane: {lane}')
    return [(a, b) for a, b in zip(points, points[1:]) if a != b]


def length(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def stations(segs, reach):
    """Minimal number of relays; carry distance through corners, not per leg."""
    if not math.isfinite(reach) or reach <= 0:
        raise ValueError('Reach must be positive and finite')
    total = sum(length(a, b) for a, b in segs)
    hops = max(1, math.ceil(total / reach))
    result = []
    for i in range(1, hops):
        target = total * i / hops
        offset = 0.0
        for j, (a, b) in enumerate(segs):
            span = length(a, b)
            if target <= offset + span + 1e-9:
                fraction = (target - offset) / span
                result.append(dict(index=i, arclength_um=target, segment=j,
                                   x=a[0] + fraction * (b[0] - a[0]),
                                   y=a[1] + fraction * (b[1] - a[1])))
                break
            offset += span
    return total, total / hops, result


def intersection(a, b, rect):
    """Positive-length interior intersection, in the original travel direction."""
    x0, y0 = rect['x'], rect['y']
    x1, y1 = x0 + rect['w'], y0 + rect['h']
    vertical = a[0] == b[0]
    if vertical:
        if not x0 < a[0] < x1:
            return None
        lo, hi = max(min(a[1], b[1]), y0), min(max(a[1], b[1]), y1)
        points = [(a[0], lo), (a[0], hi)]
        reverse = b[1] < a[1]
    else:
        if not y0 < a[1] < y1:
            return None
        lo, hi = max(min(a[0], b[0]), x0), min(max(a[0], b[0]), x1)
        points = [(lo, a[1]), (hi, a[1])]
        reverse = b[0] < a[0]
    if hi <= lo:
        return None
    if reverse:
        points.reverse()
    return dict(axis='v' if vertical else 'h', entry=points[0], exit=points[1], length_um=hi-lo)


def inside(point, rect):
    # Boundary sites need a seam owner too, so include them, explicitly.
    return (rect['x'] <= point['x'] <= rect['x'] + rect['w'] and
            rect['y'] <= point['y'] <= rect['y'] + rect['h'])


def peak_cut(crossings, axis):
    """Maximum aggregate bits through one block cut, not a physical track proof."""
    events = defaultdict(int)
    dimension = 1 if axis == 'v' else 0
    for c in crossings:
        if c['axis'] != axis:
            continue
        lo, hi = sorted([c['entry'][dimension], c['exit'][dimension]])
        events[lo] += c['bits']
        events[hi] -= c['bits']
    live = peak = 0
    at = None
    keys = sorted(events)
    for i, coordinate in enumerate(keys[:-1]):
        live += events[coordinate]
        if live > peak:
            peak, at = live, [coordinate, keys[i+1]]
    return dict(bits=peak, interval_um=at)


def build(pins, plan, lanes, reach=480.0, tracks=14.0625, utilization=0.60, ff_area=None):
    if tracks <= 0 or not 0 < utilization <= 1:
        raise ValueError('Positive tracks and utilization in (0,1] required')
    if ff_area is not None and (not math.isfinite(ff_area) or ff_area <= 0):
        raise ValueError('FF area assumption must be positive and finite')
    ends = defaultdict(list)
    for block, record in pins['blocks'].items():
        for face in record['faces'].values():
            for pin in face['pins']:
                ends[pin['link']].append((block, pin))
    requests = {b: dict(crossings=[], sites=[]) for b in plan}
    routes, invalid, channel_sites = {}, [], []
    total_ff = total_sites = 0
    for link, lane in sorted(lanes.items()):
        if len(ends[link]) != 2:
            invalid.append(dict(link=link, reason='Expected exactly two pin records'))
            continue
        (b1, p1), (b2, p2) = ends[link]
        if p1['bits'] != p2['bits']:
            invalid.append(dict(link=link, reason='Endpoint bit widths differ'))
            continue
        segs = segments(p1, p2, lane)
        total, spacing, sites = stations(segs, reach)
        bits = p1['bits']
        total_sites += len(sites)
        total_ff += bits * len(sites)
        routes[link] = dict(endpoint_blocks=[b1,b2], bits=bits, total_um=total,
                            max_centerline_hop_um=spacing, relay_stages=len(sites),
                            polyline=[list(segs[0][0])] + [list(b) for _,b in segs] if segs else [],
                            sites=sites)
        for block, rect in plan.items():
            for index, (a,b) in enumerate(segs):
                cross = intersection(a,b,rect)
                if cross:
                    requests[block]['crossings'].append(dict(
                        link=link, segment=index, bits=bits, endpoint_block=block in (b1,b2), **cross))
        for site in sites:
            owners = [block for block, rect in plan.items() if inside(site,rect)]
            site['block_owners'] = owners
            site['status'] = 'REQUESTED'
            if not owners:
                channel_sites.append(dict(link=link, bits=bits, **site))
            for block in owners:
                r = plan[block]
                axis = 'v' if segs[site['segment']][0][0] == segs[site['segment']][1][0] else 'h'
                in_column = block.startswith('su_') and axis == 'v' and abs(site['x']-(r['x']+r['w']/2)) <= 20
                requests[block]['sites'].append(dict(link=link, bits=bits, ff_bits=bits,
                    endpoint_block=block in (b1,b2), axis=axis,
                    inside_prose_su_40um_column=bool(in_column), **site))
    by_kind = defaultdict(lambda: dict(blocks=0, relay_sites=0, ff_bits=0, endpoint_sites=0))
    for block, request in requests.items():
        request['status'] = 'REQUESTED_NOT_RESERVED'
        request['relay_sites'] = len(request['sites'])
        request['ff_bits'] = sum(s['ff_bits'] for s in request['sites'])
        request['ff_cell_area_um2'] = None if ff_area is None else request['ff_bits'] * ff_area
        request['endpoint_sites'] = sum(s['endpoint_block'] for s in request['sites'])
        request['su_sites_inside_prose_column'] = sum(s['inside_prose_su_40um_column'] for s in request['sites'])
        request['cut_lower_bounds'] = {}
        for axis in ('h','v'):
            cut = peak_cut(request['crossings'],axis)
            cut['required_aggregate_width_um'] = cut['bits'] / (tracks * utilization)
            full_width = plan[block]['h' if axis == 'h' else 'w']
            cut['full_block_transverse_width_um'] = full_width
            cut['full_block_cut_ratio'] = cut['bits'] / (tracks * full_width)
            if block.startswith('su_') and axis == 'v':
                cut['prose_40um_column_cut_ratio_if_all_traffic_used_it'] = cut['bits'] / (tracks * 40)
            request['cut_lower_bounds'][axis] = cut
        kind = block.split('_')[0]
        group = by_kind[kind]
        group['blocks'] += 1
        for field in ('relay_sites','ff_bits','endpoint_sites'):
            group[field] += request[field]
    return dict(schema='opentallas.hbm_v15.feedthrough_requests.v1',
        verdict='REQUESTED_NOT_PHYSICALLY_QUALIFIED', reach_um=reach,
        scope='Lane-file centerlines only; unlaned links are not certified',
        planning_cut=dict(tracks_per_um=tracks, max_utilization=utilization,
                          meaning='Aggregate routing-width lower bound; no layer/obstacle/PG allocation'),
        ff_cell_area_um2_assumption=ff_area,
        limitations=['Pin spans/individual bit routes are not instantiated; centerline reach is a lower bound.',
                     'Requested sites are not reserved cells, RTL stages, clocks or compiler schedule entries.',
                     'Cut widths do not prove local channel fit or detailed route.',
                     'SU prose column overlap is geometric only; no available area proof.',
                     'Boundary/multiple-owner sites require a seam owner; macro/PHY sites require rerouting.',
                     'Uniform stations are one minimum-depth candidate, not an optimal legal placement.'],
        summary=dict(laned_links=len(lanes), emitted_links=len(routes),
                     omitted_unlaned_links=len(set(ends)-set(lanes)), invalid_links=invalid,
                     relay_sites=total_sites, ff_bits=total_ff,
                     ff_cell_area_um2=None if ff_area is None else total_ff*ff_area,
                     channel_sites=len(channel_sites), channel_ff_bits=sum(s['bits'] for s in channel_sites),
                     overlapping_owner_sites=sum(len(s['block_owners'])>1 for r in routes.values() for s in r['sites']),
                     max_centerline_hop_um=max((r['max_centerline_hop_um'] for r in routes.values()),default=0),
                     by_block_kind=dict(sorted(by_kind.items()))),
        blocks=requests, channel_requests=channel_sites, routes=routes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pins',type=Path,default=DEFAULT/'pins/compact660_v5.pins.json')
    parser.add_argument('--plan',type=Path,default=DEFAULT/'compact.P.json')
    parser.add_argument('--lanes',type=Path,default=DEFAULT/'lanes2.json')
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reach',type=float,default=480.0)
    parser.add_argument('--tracks-per-um',type=float,default=14.0625)
    parser.add_argument('--max-utilization',type=float,default=0.60)
    parser.add_argument('--ff-area-um2',type=float,help='Explicit cell-area assumption only; placement area remains open')
    args = parser.parse_args()
    paths = dict(pins=args.pins,plan=args.plan,lanes=args.lanes)
    raw = {k:p.read_bytes() for k,p in paths.items()}
    result = build(*(json.loads(raw[k]) for k in ('pins','plan','lanes')),
                   reach=args.reach,tracks=args.tracks_per_um,utilization=args.max_utilization,
                   ff_area=args.ff_area_um2)
    result['sources'] = {k:dict(path=str(p),sha256=hashlib.sha256(raw[k]).hexdigest()) for k,p in paths.items()}
    result['sources']['tool'] = dict(sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.out.write_text(json.dumps(result,indent=1)+'\n')
    print(json.dumps(result['summary'],indent=1))


if __name__ == '__main__':
    main()
