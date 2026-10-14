#!/usr/bin/env python3
"""Necessary placement screen from every actual bit of a retained relay fanout.

The LP omits obstacles and wire cuts: feasible positions are requests, never
legal placements. An infeasible fanout needs topology or endpoint changes even
before occupancy is considered. Neighbor instances remain at retained positions.
"""
import argparse
import gzip
import hashlib
import json
import re
import math
from collections import defaultdict
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.optimize import linprog

from die_hop_gate import _loc, read_pins


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('plan', type=Path)
    ap.add_argument('lef', type=Path)
    ap.add_argument('gate', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--frame', type=int, default=0)
    ap.add_argument('--check-infeasible-orientation-sites', action='store_true')
    args = ap.parse_args()
    plan = json.load(gzip.open(args.plan, 'rt'))
    gate = json.loads(args.gate.read_text())
    by = {row[0]: SimpleNamespace(name=row[0], master=row[1], x=row[2],
                                y=row[3], w=row[4], h=row[5], orient=row[6])
          for row in plan['insts']}
    prefix = tuple(f'{kind}_{lane}_{args.frame}_' for kind in ('y', 'g')
                   for lane in ('xa', 'xb'))
    relays = {name for name in by if name.startswith(prefix)}
    hops = [row for row in plan['hops'] if row[1] == 'x_lane'
            and (row[3] in relays or row[5] in relays)]
    needed = {by[row[index]].master for row in hops for index in (3, 5)}
    texts = []
    current = None
    lines = []
    with gzip.open(args.lef, 'rt') as stream:
        for line in stream:
            words = line.split()
            if words and words[0] == 'MACRO':
                current = words[1]
                lines = []
            if current in needed:
                lines.append(line)
            if words == ['END', current]:
                if lines:
                    texts.append(''.join(lines))
                current = None
    pins = read_pins(texts)
    strip = lambda value: re.sub(r'\d+', '#', value)
    limits = {(r['drv'], r['load'], r['cls']): r['limit_um']
              for r in gate['classes']}
    fallback_hops = []
    for row in hops:
        if (strip(row[3])+'.'+row[4], strip(row[5])+'.'+row[6], row[1]) not in limits:
            fallback_hops.append(dict(bus=row[0], driver=row[3]+'.'+row[4], load=row[5]+'.'+row[6], bits=row[2]))
    constraints = defaultdict(list)
    missing = defaultdict(int)
    for row in hops:
        bus, cls, bits, driver, dp, load, lp = row[:7]
        # Retained operand hops use whole ports, never silently reinterpret a
        # slice as a whole bus. The full gate remains responsible for slices.
        assert '[' not in dp and '[' not in lp, (bus, dp, lp)
        limit = limits.get((strip(driver)+'.'+dp, strip(load)+'.'+lp, cls), gate['limit_um'])
        for bit in range(bits):
            pa = _loc(by[driver], pins, f'{dp}[{bit}]')
            pb = _loc(by[load], pins, f'{lp}[{bit}]')
            for own, point, other in ((driver, pa, pb), (load, pb, pa)):
                if own not in relays:
                    continue
                if point is None or other is None:
                    missing[own] += 1
                    continue
                local = (point[0]-by[own].x, point[1]-by[own].y)
                constraints[own].append((local, other, limit, bus, bit,
                                         abs(pa[0]-pb[0])+abs(pa[1]-pb[1])))
    rows = []
    for name in sorted(relays):
        items = constraints[name]
        if not items:
            rows.append(dict(instance=name, status='NO_BOUND_ENDPOINTS', unbound_bits=missing[name]))
            continue
        it = by[name]
        alternatives = []
        for orientation in (it.orient, *[o for o in ('R0', 'MY', 'MX', 'R180') if o != it.orient]):
            oriented = []
            for local, other, limit, *tail in items:
                px, py = local
                if it.orient in ('MY', 'R180'): px = it.w-px
                if it.orient in ('MX', 'R180'): py = it.h-py
                if orientation in ('MY', 'R180'): px = it.w-px
                if orientation in ('MX', 'R180'): py = it.h-py
                oriented.append(((px, py), other, limit, *tail))
            matrix, rhs = [], []
            for local, other, limit, *_ in oriented:
                for sx, sy in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                    matrix.append([sx, sy, -1])
                    rhs.append(limit-sx*(local[0]-other[0])-sy*(local[1]-other[1]))
            result = linprog([0, 0, 1], A_ub=np.asarray(matrix), b_ub=np.asarray(rhs),
                             bounds=[(0, 33000-it.w), (0, 26000-it.h), (None, None)], method='highs')
            assert result.success, result.message
            alternatives.append((float(result.x[2]), orientation, result.x, oriented))
        fixed_excess = alternatives[0][0]
        excess, orientation, vector, oriented = min(alternatives, key=lambda row: row[0])
        x, y, _ = map(float, vector)
        before = sum(item[5] > item[2]+1e-7 for item in items)
        after = sum(abs(x+local[0]-other[0])+abs(y+local[1]-other[1]) > limit+1e-7
                    for local, other, limit, *_ in oriented)
        site_screen = None
        if args.check_infeasible_orientation_sites and fixed_excess > 1e-7:
            import sys
            sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
            from dsrom_s81_fulldie import Occ
            occ = Occ()
            for other in by.values():
                if other.name != name:
                    occ.add((other.x, other.y, other.x+other.w, other.y+other.h))
            site_screen = []
            for site_excess, site_ori, _, site_items in alternatives:
                if site_excess > 1e-7:
                    continue
                signs = ((1, 1), (1, -1), (-1, 1), (-1, -1))
                rhs = [min(limit-sx*(local[0]-other[0])-sy*(local[1]-other[1]) for local, other, limit, *_ in site_items) for sx, sy in signs]
                yy = []
                for direction in (1, -1):
                    bound = linprog([0, direction], A_ub=signs, b_ub=rhs, bounds=[(0, 33000-it.w), (0, 26000-it.h)], method='highs')
                    assert bound.success
                    yy.append(float(bound.x[1]))
                tested = blocked = 0
                first_free = None
                for yi in range(math.ceil(yy[0]/.576), math.floor(yy[1]/.576)+1):
                    sy = yi*.576
                    lo = max(0, *[(r-ay*sy)/ax for (ax, ay), r in zip(signs, rhs) if ax < 0])
                    hi = min(33000-it.w, *[(r-ay*sy)/ax for (ax, ay), r in zip(signs, rhs) if ax > 0])
                    for xi in range(math.ceil(lo/.432), math.floor(hi/.432)+1):
                        sx = xi*.432
                        tested += 1
                        if not occ.free((sx, sy, sx+it.w, sy+it.h), .432):
                            blocked += 1
                        elif first_free is None:
                            first_free = [sx, sy]
                site_screen.append(dict(requested_orientation=site_ori, candidate_lattice_um=[.432, .576], exact_endpoint_feasible_sites=tested, occupancy_blocked_sites=blocked, first_free_site=first_free, pin_access_and_global_lattice_admission=False))
        rows.append(dict(instance=name, master=it.master, bound_endpoint_bits=len(items),
                         unbound_bits=missing[name], before_over_pair_limit=before,
                         obstacle_free_optimum_over_pair_limit=after,
                         minimum_worst_excess_um=round(excess, 6),
                         original_orientation=it.orient, requested_orientation=orientation, site_screen=site_screen,
                         orientation_lower_bounds=[dict(orientation=o, worst_excess_um=round(e, 6)) for e, o, _, _ in alternatives],
                         fixed_orientation_minimum_worst_excess_um=round(fixed_excess, 6),
                         requested_origin_um=[x, y],
                         status='ENDPOINT_TOPOLOGY_REPAIR_REQUIRED' if excess > 1e-7 else
                         'OBSTACLE_FREE_REQUEST_OCCUPANCY_AND_CUTS_OPEN'))
    requested = {r['instance']: r for r in rows if 'requested_origin_um' in r}
    for name, row in requested.items():
        it = by[name]
        x, y = row['requested_origin_um']
        blockers = [other.name for other in by.values() if other.name != name
                    and x < other.x+other.w-1e-7 and other.x < x+it.w-1e-7
                    and y < other.y+other.h-1e-7 and other.y < y+it.h-1e-7]
        row['retained_occupancy_blockers'] = blockers[:20]
        row['retained_occupancy_blocker_count'] = len(blockers)
    # Independent LP requests hold neighbors fixed. Recheck the simultaneous
    # requests separately rather than presenting individual optima as a plan.
    candidate_by = {name: SimpleNamespace(**vars(it)) for name, it in by.items()}
    for name, row in requested.items():
        candidate_by[name].x, candidate_by[name].y = row['requested_origin_um']
        candidate_by[name].orient = row['requested_orientation']
    joint_bound = joint_missing = joint_over = before_unique_over = 0
    joint_max = 0.0
    for row in hops:
        bus, cls, bits, driver, dp, load, lp = row[:7]
        limit = limits.get((strip(driver)+'.'+dp, strip(load)+'.'+lp, cls), gate['limit_um'])
        for bit in range(bits):
            pa = _loc(candidate_by[driver], pins, f'{dp}[{bit}]')
            pb = _loc(candidate_by[load], pins, f'{lp}[{bit}]')
            if pa is None or pb is None:
                joint_missing += 1
                continue
            joint_bound += 1
            distance = abs(pa[0]-pb[0])+abs(pa[1]-pb[1])
            joint_max = max(joint_max, distance)
            joint_over += distance > limit+1e-7
            a = _loc(by[driver], pins, f'{dp}[{bit}]')
            b = _loc(by[load], pins, f'{lp}[{bit}]')
            before_unique_over += abs(a[0]-b[0])+abs(a[1]-b[1]) > limit+1e-7
    receipt = dict(schema='opentallas.s81.operand_endpoint_necessary_screen.v1',
                   frame=args.frame, die_outline_um=[33000, 26000],
                   route_admission=False, placement_admission=False,
                   sources={str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in (args.plan, args.lef, args.gate)},
                   joint_request=dict(bound_bits=joint_bound, unbound_bits=joint_missing,
                                      before_over_pair_limit=before_unique_over, after_over_pair_limit=joint_over,
                                      max_um=round(joint_max, 6), occupancy_blocked_requests=sum(r.get('retained_occupancy_blocker_count', 0)>0 for r in rows)),
                   pair_limit_provenance=dict(recorded_class_limits=limits.__len__(), fallback_ceiling_hops=fallback_hops, fallback_rule='flat ceiling only; missing per-pair table lookup remains unqualified'),
                   rows=rows, bound_endpoint_bits=sum(r.get('bound_endpoint_bits', 0) for r in rows),
                   unbound_endpoint_bits=sum(r['unbound_bits'] for r in rows),
                   before_over_pair_limit=sum(r.get('before_over_pair_limit', 0) for r in rows),
                   topology_infeasible_relays=sum(r['status']=='ENDPOINT_TOPOLOGY_REPAIR_REQUIRED' for r in rows),
                   open=['actual native Q replacement endpoints', 'full per-pair limits for fallback-ceiling hops', 'simultaneous neighbor relocation',
                         'occupancy and manufacturing grid', 'candidate orientation actual pin access', 'pin access/alignment',
                         'full and local corridor cuts', 'registered-stage cost and source proof'])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k: receipt[k] for k in ('bound_endpoint_bits', 'unbound_endpoint_bits',
                                             'before_over_pair_limit', 'topology_infeasible_relays')}))


if __name__ == '__main__':
    main()
