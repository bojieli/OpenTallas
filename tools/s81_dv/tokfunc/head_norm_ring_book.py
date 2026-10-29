#!/usr/bin/env python3
"""Book HEAD partial injections on the actual 16-stop norm exchange.

The two issuer engines keep their own command order. Choose the earliest VS
cohort phase that avoids local-injection/forward collisions. This is a source
calendar candidate; it never changes PDSK, an RTL source, or physical START.
"""
import argparse
import copy
import json
from pathlib import Path


def outgoing(sid, direction):
    col, tier = sid // 2, sid % 2
    if direction == 'E':
        return 'vo' if (tier == 0 and col == 7) or (tier == 1 and col == 0) else ('ro_w' if tier else 'ro_e')
    return 'vo' if (tier == 0 and col == 0) or (tier == 1 and col == 7) else ('ro_e' if tier else 'ro_w')


def book(booking, network):
    for key in ('source_asbuilt_sha256', 'die_sha256'):
        if not booking.get(key) or booking[key] != network.get(key):
            raise ValueError('booking and exchange must use one exact bound source')
    if booking.get('adoption') or network.get('verdict') != 'PASS_SOURCE_NORM_NETWORK':
        raise ValueError('source-qualified unadopted candidate required')
    # Same edge chains used by head_norm_network.py: xstop input/output = 2;
    # ring-stop injection and delivery = 2 each, plus exact bound link age.
    endpoint = {r['sid']: r for r in network['transport']['nx_boundary']}
    ids = set(endpoint)
    groups = {g['sid']: g for g in booking['groups']}
    if ids != set(range(16)) or set(groups) != ids:
        raise ValueError('complete 16-stop source exchange required')
    eps = {r['slice']: r['edges'] for r in network['transport']['xfin_endpoints']}
    if any(any(v != 0 for v in e.values()) for e in eps.values()):
        raise ValueError('nonzero XFIN endpoint needs explicit hop accounting')
    links = {}
    for r in network['transport']['nx_boundary']:
        if r['status'] == 'PASS':
            key = (r['from_sid'], r['from_port'])
            if key in links or type(r['age_edges']) is not int or r['age_edges'] < 0:
                raise ValueError('exchange link must have one destination and exact age')
            links[key] = (r['sid'], r['age_edges'] + 6)
    # The common local arithmetic/collector latency cancels in each equality.
    arrivals = {sid: g['aligned_partial_edge_excluding_common_local_vp_latency'] for sid, g in groups.items()}
    constraints = []
    for source in sorted(ids):
        for direction, reach in (('E', 8), ('W', 7)):
            node, age = source, 0
            for hop in range(1, 17):
                try:
                    node, leg = links[node, outgoing(node, direction)]
                except KeyError as exc:
                    raise ValueError('exchange snake has an open required hop') from exc
                age += leg
                if hop < reach:
                    constraints.append(dict(local=node, forward_origin=source, direction=direction,
                                            hop=hop, forward_delay_edges=age))
                if hop < 16 and node == source:
                    raise ValueError('exchange closes before all 16 stops')
            if node != source:
                raise ValueError('exchange does not form the required 16-stop ring')
    def collides(c, phase):
        src, dst = c['forward_origin'], c['local']
        return arrivals[dst] + (phase if dst % 2 == 0 else 0) == (
            arrivals[src] + (phase if src % 2 == 0 else 0) + c['forward_delay_edges'])
    current = [c for c in constraints if collides(c, 0)]
    if any(c['local'] % 2 == c['forward_origin'] % 2 for c in current):
        raise ValueError('same-issuer injection collision requires a group schedule redesign')
    forbidden = set()
    for c in constraints:
        src, dst = c['forward_origin'], c['local']
        if src % 2 != dst % 2:
            d = arrivals[src] + c['forward_delay_edges'] - arrivals[dst]
            forbidden.add(d if dst % 2 == 0 else -d)
    phase = 0
    while phase in forbidden:
        phase += 1
    result = copy.deepcopy(booking)
    for row in result['rows']:
        if row['engine'] == 'VS':
            for key in ('issue_vo_edge', 'xr_command_pin_edge', 'vp_command_pin_edge'):
                if key in row:
                    row[key] += phase
    for g in result['groups']:
        if g['sid'] % 2 == 0:
            for key in ('start_vo_edge', 'last_vo_edge', 'aligned_partial_edge_excluding_common_local_vp_latency'):
                g[key] += phase
    used = {(r['engine'], r['issue_vo_edge']) for r in result['rows']}
    if len(used) != len(result['rows']):
        raise ValueError('cohort scheduling introduced unsupported issuer multiissue')
    if any(collides(c, phase) for c in constraints):
        raise ValueError('ring schedule still contains a local/forward collision')
    previous_last = result['new_last_vo_edge']
    result['new_last_vo_edge'] = max(r['issue_vo_edge'] for r in result['rows'])
    result['added_control_span_edges'] = result['new_last_vo_edge'] - result['old_consecutive_programme_last_vo_edge']
    result['ring_booking'] = dict(engine_phase_edges={'VN': 0, 'VS': phase},
        original_collisions=current, candidate_collisions=[], constraints=len(constraints),
        extra_control_span_edges=result['new_last_vo_edge']-previous_last,
        hop_model='xstop input/output2 + ring-stop injection2 + bound link age + ring-stop delivery2',
        arithmetic_and_payloads_unchanged=True, rtl_execution_qualified=False,
        physical_START_qualified=False, adoption=False)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('booking', 'network', 'out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    result = book(json.loads(a.booking.read_text()), json.loads(a.network.read_text()))
    with a.out.open('x') as f:
        f.write(json.dumps(result, indent=1)+'\n')
    print(json.dumps(result['ring_booking'], indent=1))


if __name__ == '__main__':
    main()
