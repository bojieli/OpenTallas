#!/usr/bin/env python3
"""Reject invalid fixed SU/HC VM reservations without rescheduling any event.

An issue trace by itself is insufficient: the compiler must supply each exact
VM ingress/service edge and each observed response/commit edge. The contract
records measured path latency, finite buffers, and the bank and ingress capacity.
This checks a proposed static schedule; it is not a replacement for the native
RTL composition bench or proof that a provisional latency contract is measured.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from fractions import Fraction
import json
from pathlib import Path


def check(schedule: dict, contract: dict) -> dict:
    errors = []
    def error(kind, **witness):
        errors.append(dict(kind=kind, **witness))
    required = ['stream_period_ps', 'vm_period_ps', 'stream_phase_ps', 'vm_phase_ps',
                'banks', 'bank_ops_per_cycle', 'read_ingress_per_cycle', 'write_ingress_per_cycle',
                'request_min_ps', 'read_min_ps', 'commit_min_ps', 'slot_capacity', 'client_capacity']
    missing = [x for x in required if x not in contract]
    if missing:
        return dict(status='incomplete', violations=[dict(kind='missing_contract', fields=missing)],
                    qualified=False, events=0)
    def when(cycle, domain):
        return Fraction(str(contract[f'{domain}_phase_ps'])) + cycle * Fraction(str(contract[f'{domain}_period_ps']))
    bank_use, ingress_use = defaultdict(list), defaultdict(list)
    queues, rows = defaultdict(list), defaultdict(list)
    event_by_id, job_writes = {}, defaultdict(list)
    for index, event in enumerate(schedule.get('events', [])):
        eid = event.get('id', str(index))
        if eid in event_by_id:
            error('duplicate_event_id', event=eid)
        event_by_id[eid] = event
        if event.get('kind') not in ('read', 'write'):
            error('unknown_event', event=eid, kind_value=event.get('kind')); continue
        kind = event['kind']
        needed = ['client', 'slot', 'row', 'tag', 'issue_cycle', 'ingress_cycle', 'service_cycle',
                  'response_cycle' if kind == 'read' else 'commit_cycle', 'deadline_cycle']
        absent = [x for x in needed if x not in event]
        if absent:
            error('missing_reservation', event=eid, fields=absent); continue
        cycle_keys = ['issue_cycle', 'ingress_cycle', 'service_cycle', 'deadline_cycle',
                      'response_cycle' if kind == 'read' else 'commit_cycle']
        if any(not isinstance(event[x], int) or event[x] < 0 for x in cycle_keys):
            error('invalid_cycle', event=eid); continue
        if not isinstance(event['row'], int) or not 0 <= event['row'] < 16384:
            error('invalid_row', event=eid, row=event['row']); continue
        issue = when(event['issue_cycle'], 'stream')
        ingress = when(event['ingress_cycle'], 'vm')
        service = when(event['service_cycle'], 'vm')
        retire_cycle = event['response_cycle' if kind == 'read' else 'commit_cycle']
        retire = when(retire_cycle, 'stream')
        deadline = when(event['deadline_cycle'], 'stream')
        if ingress < issue + Fraction(str(contract['request_min_ps'])):
            error('ingress_before_request', event=eid)
        if service < ingress:
            error('service_before_ingress', event=eid)
        minimum = Fraction(str(contract['read_min_ps' if kind == 'read' else 'commit_min_ps']))
        if retire < service + minimum:
            error('retire_before_physical_path', event=eid)
        if retire > deadline:
            error('missed_fixed_deadline', event=eid, actual=retire_cycle, deadline=event['deadline_cycle'])
        bank_use[(event['service_cycle'], event['row'] % contract['banks'])].append(eid)
        ingress_use[(event['ingress_cycle'], kind)].append(eid)
        slot = (event['client'], kind, event['slot'])
        queues[slot].append((issue, retire, eid))
        rows[event['row']].append((kind, issue, retire, eid))
        if kind == 'write': job_writes[(event['client'], event['tag'])].append((retire, eid))
    for (cycle, bank), ids in bank_use.items():
        if len(ids) > contract['bank_ops_per_cycle']:
            error('bank_collision', vm_cycle=cycle, bank=bank, events=ids)
    for (cycle, kind), ids in ingress_use.items():
        if len(ids) > contract[f'{kind}_ingress_per_cycle']:
            error('ingress_collision', vm_cycle=cycle, operation=kind, events=ids)
    peaks = {}
    client_edges = defaultdict(list)
    for slot, intervals in queues.items():
        key = '/'.join(map(str, slot))
        capacity = contract['slot_capacity'].get(key)
        if capacity is None:
            error('missing_slot_capacity', slot=key); continue
        edges = [(start, 1, eid) for start, _, eid in intervals] + [(end, -1, eid) for _, end, eid in intervals]
        occupancy, peak, live = 0, 0, set()
        for time, delta, eid in sorted(edges):  # retire before issue on the same edge
            occupancy += delta
            if delta > 0: live.add(eid)
            else: live.discard(eid)
            peak = max(peak, occupancy)
            if occupancy > capacity:
                error('slot_overflow', slot=key, occupancy=occupancy, capacity=capacity, events=sorted(live))
        peaks[key] = peak
        client_edges[slot[0]].extend(edges)
        # Responses at native slots must preserve their issue order.
        ordered = sorted(intervals)
        if any(b[1] < a[1] for a, b in zip(ordered, ordered[1:])):
            error('slot_response_reordered', slot=key)
    for client, edges in client_edges.items():
        capacity = contract['client_capacity'].get(client)
        if capacity is None:
            error('missing_client_capacity', client=client); continue
        occupancy, live = 0, set()
        for time, delta, eid in sorted(edges):
            occupancy += delta
            if delta > 0: live.add(eid)
            else: live.discard(eid)
            if occupancy > capacity:
                error('client_overflow', client=client, occupancy=occupancy, capacity=capacity, events=sorted(live))
    # A producer completion is a fixed boundary, not a permission to delay it.
    for job in schedule.get('jobs', []):
        if not all(x in job for x in ('client', 'tag', 'done_cycle')):
            error('missing_job_boundary', job=job); continue
        done = when(job['done_cycle'], 'stream')
        late = [eid for retire, eid in job_writes[(job['client'], job['tag'])] if retire > done]
        if late: error('done_before_commit', client=job['client'], tag=job['tag'], events=late)
    # Explicit data-dependency edges, including cross-client consumers and partial-row writes.
    for dependency in schedule.get('dependencies', []):
        producer, consumer = dependency.get('producer'), dependency.get('consumer')
        p, c = event_by_id.get(producer), event_by_id.get(consumer)
        if p is None or c is None or p.get('kind') != 'write' or c.get('kind') != 'read':
            error('invalid_dependency', dependency=dependency); continue
        if 'commit_cycle' not in p or 'service_cycle' not in c:
            error('missing_dependency_retirement', producer=producer, consumer=consumer); continue
        if p['row'] != c['row']:
            error('dependency_row_mismatch', producer=producer, consumer=consumer)
        if when(c['service_cycle'], 'vm') < when(p['commit_cycle'], 'stream'):
            error('consume_before_commit', producer=producer, consumer=consumer)
    # Pair/batch consumers require the original mask at one fixed response edge.
    for group in schedule.get('groups', []):
        members = [event_by_id.get(eid) for eid in group.get('events', [])]
        if not members or any(x is None or x.get('kind') != 'read' or 'response_cycle' not in x for x in members):
            error('invalid_response_group', group=group); continue
        if len({x['response_cycle'] for x in members}) != 1:
            error('response_group_split', group=group)
    measured = contract.get('measured_native_bounds') is True
    coverage = all(schedule.get(x) for x in ('events', 'jobs')) and schedule.get('trace_complete') is True
    status = 'fail' if errors else 'pass' if measured and coverage else 'incomplete'
    return dict(status=status, qualified=False, events=len(schedule.get('events', [])), violations=errors,
                slot_peaks=peaks, measured_native_bounds=measured, trace_complete=coverage,
                note='Static reservation check only; native RTL, die timing and performance gates remain required.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--schedule', type=Path, required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    report = check(json.loads(a.schedule.read_text()), json.loads(a.contract.read_text()))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2)+'\n')
    print(f"static VM reservations: {report['status']}, events={report['events']}, violations={len(report['violations'])}")
    return 0 if report['status'] == 'pass' else 1

if __name__ == '__main__':
    raise SystemExit(main())
