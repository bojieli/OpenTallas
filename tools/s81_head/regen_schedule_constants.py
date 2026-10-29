#!/usr/bin/env python3
"""Generate HEAD transport schedule constants from a raw plan and optional CA table.

This is a plan-derived source schedule, with no START dates or token-rate claim.
Raw lane costs use die_plan.schema.Plan.lane_latency, including its R8 pads.
Each CA port contributes its declared added_cycles once to its containing lane.
The HEAD transport estimate follows DIE-HEAD-27 a1_price.py: longest spine
round trip plus twice the worst gather leg. HOST and LEP legs stay separate.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'die_plan'))
from schema import Plan


def ca_lane_cycles(raw, table):
    """Count actual per-port additions, never the table's default crossing cost."""
    if table is None:
        return {}, []
    if raw.get('clock', {}).get('landing_network'):
        raise ValueError('CA table requires the raw pre-landing plan (avoid double charging)')
    ports = {p['id']: p for p in raw['ports']}
    lanes = {l['id']: set(l['ports']) for l in raw['lanes']}
    additions, seen, rows = defaultdict(int), set(), []
    for row in table['ports']:
        port, lane, cycles = row['port'], row['lane'], row['added_cycles']
        if port in seen or port not in ports or lane not in lanes or port not in lanes[lane]:
            raise ValueError('duplicate or mismatched CA port/lane: ' + str(port))
        if type(cycles) is not int or cycles < 0:
            raise ValueError('CA added_cycles must be an explicit nonnegative integer: ' + port)
        actual = ports[port]
        if (row['src'] != actual['src']['part'] or row['dst'] != actual['dst']['part']):
            raise ValueError('CA endpoints differ from the selected raw plan: ' + port)
        configured = table.get('count_aligned', {}).get('ports', {}).get(port)
        if configured is not None and configured['sched_lat'] != cycles:
            raise ValueError('CA added_cycles differs from count-aligned sched_lat: ' + port)
        seen.add(port)
        additions[lane] += cycles
        rows.append(dict(port=port, lane=lane, added_cycles=cycles))
    return dict(additions), rows


def head_transport(latencies):
    indices = sorted(int(m.group(1)) for lane in latencies
                     if (m := re.fullmatch(r'sp_x(\d+)', lane)))
    if not indices or indices != list(range(indices[-1] + 1)):
        raise ValueError('HEAD spine indices must be present and contiguous')
    candidates = []
    for k in indices:
        spine = [name for i in range(k + 1) for name in (f'sp_x{i}', f'sp_b{i}')]
        if any(name not in latencies for name in spine):
            raise ValueError('HEAD spine return lane missing')
        for side in 'WE':
            chain = sorted(name for name in latencies if name.startswith(f'ch{side}{k}_'))
            if chain:
                path = spine + chain
                candidates.append(dict(cycles=sum(latencies[name] for name in path),
                                       slice=k, side=side, lanes=path))
    gather = {lane: cycles for lane, cycles in latencies.items()
              if re.match(r'^(m\d[SN]_|coll_|kd|ku|unit_lep|ctrl_lep|lepf)', lane)}
    if not candidates or not gather:
        raise ValueError('HEAD spine chains and gather legs are required')
    spine = max(candidates, key=lambda row: row['cycles'])
    worst = max(gather, key=gather.get)
    return dict(spine=spine, gather_worst=dict(lane=worst, cycles=gather[worst]),
                total_cycles=spine['cycles'] + 2 * gather[worst],
                formula='longest_spine_round_trip + 2 * worst_gather_leg')


def generate(raw, ca=None):
    plan = Plan(raw)
    if plan.name != 's81_head':
        raise ValueError('s81_head raw plan required')
    extra, crossings = ca_lane_cycles(raw, ca)
    lanes = {}
    for lane in sorted(plan.lanes):
        components = plan.lane_latency(lane)
        lanes[lane] = dict(raw_cycles=components['cycles'], ca_cycles=extra.get(lane, 0),
                           cycles=components['cycles'] + extra.get(lane, 0),
                           raw_components=components)
    raw_lats = {name: row['raw_cycles'] for name, row in lanes.items()}
    landed = {name: row['cycles'] for name, row in lanes.items()}
    separate = {name: lanes[name] for name in lanes
                if name in ('host_tx', 'host_rx') or name.startswith('head_lep_')}
    return dict(schema='opentallas.s81_head.schedule_constants.v1',
                status='PLAN_DERIVED_SOURCE_SCHEDULE', lanes=lanes,
                ca_ports=crossings, ca_applied=ca is not None,
                raw_transport=head_transport(raw_lats), transport=head_transport(landed),
                separate_legs=separate, start_dates=None, token_rate=None,
                physical_qualified=False, programme_installable=False)


def delta(baseline, candidate):
    if set(baseline['lanes']) != set(candidate['lanes']):
        raise ValueError('lane identities differ; cannot report a pure lane-cost delta')
    changed = {lane: dict(before=row['cycles'], after=candidate['lanes'][lane]['cycles'],
                          delta=candidate['lanes'][lane]['cycles'] - row['cycles'])
               for lane, row in baseline['lanes'].items()
               if candidate['lanes'][lane]['cycles'] != row['cycles']}
    return dict(lanes=changed, lanes_changed=len(changed),
                aggregate_lane_cycles=sum(row['delta'] for row in changed.values()),
                transport_delta=candidate['transport']['total_cycles'] - baseline['transport']['total_cycles'],
                raw_transport_delta=candidate['raw_transport']['total_cycles'] - baseline['raw_transport']['total_cycles'])


def sv(result):
    lines = ['// Plan-derived transport only; START/programme installation remains unqualified.',
             'package s81_head_sched_pkg;']
    names = set()
    for lane, row in result['lanes'].items():
        name = re.sub('[^A-Za-z0-9_]', '_', lane).upper()
        if name in names:
            raise ValueError('SV constant names collide after normalization: ' + lane)
        names.add(name)
        for suffix, key in (('_RAW', 'raw_cycles'), ('_CA', 'ca_cycles'), ('', 'cycles')):
            lines.append(f'  localparam integer LAT_{name}{suffix} = {row[key]};')
    lines.append(f"  localparam integer HEAD_TRANSPORT_CYCLES = {result['transport']['total_cycles']};")
    lines.append('endpackage')
    return '\n'.join(lines) + '\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--ca', type=Path)
    parser.add_argument('--compare-plan', type=Path,
                        help='candidate raw plan; same CA table applied to both')
    parser.add_argument('--out-json', type=Path, required=True)
    parser.add_argument('--out-sv', type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.plan.read_text())
    ca = json.loads(args.ca.read_text()) if args.ca else None
    result = generate(raw, ca)
    result['inputs'] = dict(plan=str(args.plan), plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest(),
                            ca=str(args.ca) if args.ca else None)
    if args.compare_plan:
        candidate = generate(json.loads(args.compare_plan.read_text()), ca)
        result['candidate'] = candidate
        result['candidate_delta'] = delta(result, candidate)
    package = sv(result)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(result, indent=2) + '\n')
    args.out_sv.parent.mkdir(parents=True, exist_ok=True)
    args.out_sv.write_text(package)
    print(json.dumps(dict(status=result['status'], lanes=len(result['lanes']),
                          raw_transport=result['raw_transport']['total_cycles'],
                          transport=result['transport']['total_cycles'],
                          candidate_delta=result.get('candidate_delta'))))


if __name__ == '__main__':
    main()
