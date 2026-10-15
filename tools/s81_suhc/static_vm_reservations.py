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
import hashlib
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import vm_service_profile as VSP  # noqa: E402


def bank_of(row: int, contract: dict) -> int:
    mapping = contract.get('bank_mapping', 'rowmod')
    if mapping == 'rowmod':
        return row % contract['banks']
    if mapping == 'xor_row7_5_shift2' and contract['banks'] == 32:
        return (row & 31) ^ (((row >> 5) & 7) << 2)
    raise ValueError('Unsupported bank mapping or incompatible bank count')


def check(schedule: dict, contract: dict, source_root: Path | None = None) -> dict:
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
    positive = ['stream_period_ps', 'vm_period_ps', 'banks', 'bank_ops_per_cycle',
                'read_ingress_per_cycle', 'write_ingress_per_cycle']
    try:
        invalid = [x for x in positive if Fraction(str(contract[x])) <= 0]
        invalid += [x for x in ('request_min_ps', 'read_min_ps', 'commit_min_ps')
                    if Fraction(str(contract[x])) < 0]
        for kind in ('slot_capacity', 'client_capacity'):
            if not isinstance(contract[kind], dict) or any(type(v) is not int or v <= 0 for v in contract[kind].values()):
                invalid.append(kind)
        if any(type(contract[x]) is not int for x in ('banks', 'bank_ops_per_cycle',
                  'read_ingress_per_cycle', 'write_ingress_per_cycle')):
            invalid.append('integer_resource_capacity')
    except (ValueError, TypeError, ZeroDivisionError):
        invalid = ['invalid_numeric_contract']
    try:
        bank_of(0, contract)
    except (ValueError, TypeError, ZeroDivisionError):
        invalid.append('bank_mapping')
    ingress_caps = contract.get('ingress_capacities')
    if ingress_caps is not None and (not isinstance(ingress_caps, dict) or
            any(type(k) is not str or type(v) is not int or v <= 0 for k, v in ingress_caps.items())):
        invalid.append('ingress_capacities')
    ports = contract.get('bank_port_capacities')
    if ports is not None:
        # This profile describes the actual new 1R1W macro, not two generic
        # interchangeable operations. Legacy shared-port accounting stays exact.
        if ports != {'read': 1, 'write': 1} or any(type(v) is not int for v in ports.values()):
            invalid.append('bank_port_capacities_requires_actual_1r1w')
        if contract.get('same_address_policy') not in ('forbid', 'read_before_write'):
            invalid.append('missing_same_address_policy')
        evidence = contract.get('bank_port_evidence')
        if not evidence:
            invalid.append('missing_1r1w_source_evidence')
        else:
            root = (source_root or Path(__file__).resolve().parents[2]).resolve()
            try:
                for item in evidence:
                    path = (root / item['path']).resolve()
                    if not path.is_relative_to(root) or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
                        invalid.append('stale_1r1w_source_evidence')
            except (KeyError, TypeError, OSError):
                invalid.append('invalid_1r1w_source_evidence')
    # opt-in exact service profile (selected native VM 4/2/W1 etc.): absent = legacy minima behaviour unchanged
    profile, profile_bad = VSP.resolve(contract, source_root)
    invalid += profile_bad
    if invalid:
        return dict(status='fail', violations=[dict(kind='invalid_contract', fields=invalid)], qualified=False, events=0)
    def when(cycle, domain):
        return Fraction(str(contract[f'{domain}_phase_ps'])) + cycle * Fraction(str(contract[f'{domain}_period_ps']))
    def jobkey(x):
        return (x['client'], x.get('job'), x['tag'])
    bank_use, ingress_use = defaultdict(list), defaultdict(list)
    queues, rows, bank_queues = defaultdict(list), defaultdict(list), defaultdict(list)
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
        if any(type(event[x]) is not int or event[x] < 0 for x in cycle_keys):
            error('invalid_cycle', event=eid); continue
        if type(event['tag']) not in (str, int) or type(event['client']) is not str or type(event['slot']) is not int or event['slot'] < 0:
            error('invalid_identity', event=eid); continue
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
        if retire <= issue:
            error('retire_before_issue', event=eid)
        if retire > deadline:
            error('missed_fixed_deadline', event=eid, actual=retire_cycle, deadline=event['deadline_cycle'])
        if profile is not None:
            errors.extend(VSP.check_event(profile, dict(event, id=eid)))
            # Port occupancy and visibility must name the SAME physical macro
            # edge. Otherwise a caller can hide a real bank collision by moving
            # service_cycle while leaving a correct raw_cycle on the event.
            raw_cycle = event.get('raw_cycle')
            if type(raw_cycle) is int and raw_cycle >= 0 and service != when(raw_cycle, 'stream'):
                error('profile_service_raw_edge_mismatch', event=eid,
                      service_cycle=event['service_cycle'], raw_cycle=raw_cycle)
        bank = bank_of(event['row'], contract)
        bank_use[(event['service_cycle'], bank)].append(eid)
        if 'bank_enqueue_cycle' not in event:
            error('missing_bank_enqueue', event=eid)
        elif type(event['bank_enqueue_cycle']) is not int or event['bank_enqueue_cycle'] < 0:
            error('invalid_bank_enqueue', event=eid)
        else:
            enqueue = when(event['bank_enqueue_cycle'], 'vm')
            if enqueue < ingress or enqueue > service:
                error('bank_enqueue_outside_path', event=eid)
            elif enqueue < service:
                bank_queues[bank].append((enqueue, service, eid))
        if ingress_caps is None:
            ingress_use[(event['ingress_cycle'], kind)].append(eid)
        else:
            resource = event.get('ingress_resource')
            if resource is None:
                error('missing_ingress_resource', event=eid)
            elif resource not in ingress_caps:
                error('unknown_ingress_resource', event=eid, resource=resource)
            else:
                ingress_use[(event['ingress_cycle'], resource)].append(eid)
        slot = (event['client'], kind, event['slot'])
        queues[slot].append((issue, retire, eid))
        rows[event['row']].append((kind, issue, retire, eid))
        if kind == 'write': job_writes[jobkey(event)].append((retire, eid))
    for (cycle, bank), ids in bank_use.items():
        if ports is None:
            if len(ids) > contract['bank_ops_per_cycle']:
                error('bank_collision', vm_cycle=cycle, bank=bank, events=ids)
            continue
        for direction in ('read', 'write'):
            directional = [eid for eid in ids if event_by_id[eid]['kind'] == direction]
            if len(directional) > ports[direction]:
                error('bank_port_collision', vm_cycle=cycle, bank=bank,
                      operation=direction, events=directional)
        reads = [event_by_id[eid] for eid in ids if event_by_id[eid]['kind'] == 'read']
        writes = [event_by_id[eid] for eid in ids if event_by_id[eid]['kind'] == 'write']
        for read in reads:
            for write in writes:
                if read['row'] != write['row']:
                    continue
                if contract['same_address_policy'] == 'forbid':
                    error('same_edge_read_write_address_collision', read=read['id'], write=write['id'])
                elif read.get('read_visibility') != 'before_same_edge_write':
                    error('same_edge_read_visibility_unbound', read=read['id'], write=write['id'])
    for (cycle, resource), ids in ingress_use.items():
        capacity = ingress_caps[resource] if ingress_caps is not None else contract[f'{resource}_ingress_per_cycle']
        if len(ids) > capacity:
            error('ingress_collision', vm_cycle=cycle, resource=resource, events=ids)
    bank_peaks = {}
    bank_capacity = contract.get('bank_queue_capacity')
    if type(bank_capacity) is not int or bank_capacity <= 0:
        error('missing_bank_queue_capacity')
    else:
        for bank, intervals in bank_queues.items():
            edges = [(start, 1, eid) for start, _, eid in intervals] + [(end, -1, eid) for _, end, eid in intervals]
            occupancy, peak, live = 0, 0, set()
            for time, delta, eid in sorted(edges):
                occupancy += delta
                if delta > 0: live.add(eid)
                else: live.discard(eid)
                peak = max(peak, occupancy)
                if occupancy > bank_capacity:
                    error('bank_queue_overflow', bank=bank, occupancy=occupancy,
                          capacity=bank_capacity, events=sorted(live))
            bank_peaks[bank] = peak
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
        if 'start_cycle' in job and 'done_cycle' not in job:
            continue
        if not all(x in job for x in ('client', 'tag', 'done_cycle')):
            error('missing_job_boundary', job=job); continue
        done = when(job['done_cycle'], 'stream')
        late = [eid for retire, eid in job_writes[jobkey(job)] if retire > done]
        if late: error('done_before_commit', client=job['client'], job=job.get('job'), tag=job['tag'], events=late)
    bounded_jobs = {jobkey(x) for x in schedule.get('jobs', [])
                    if 'client' in x and 'tag' in x and 'done_cycle' in x}
    for key, writes in job_writes.items():
        if key not in bounded_jobs:
            error('missing_producer_done', client=key[0], job=key[1], tag=key[2], events=[eid for _, eid in writes])
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
        if profile is not None:
            # raw macro edges decide visibility; the returned commit (commit_cycle) is the producer-done fence only
            errors.extend(VSP.check_dependency(profile, p, c))
        elif when(c['service_cycle'], 'vm') < when(p['commit_cycle'], 'stream'):
            error('consume_before_commit', producer=producer, consumer=consumer)
        elif (ports is not None and contract.get('same_address_policy') == 'read_before_write'
              and when(c['service_cycle'], 'vm') == when(p['commit_cycle'], 'stream')
              and c['service_cycle'] == p.get('service_cycle') and c['row'] == p['row']):
            error('consume_before_same_edge_write_visibility', producer=producer, consumer=consumer)
    # Pair/batch consumers require the original mask at one fixed response edge.
    groups = list(schedule.get('groups', []))
    traced_groups = defaultdict(list)
    for event in schedule.get('events', []):
        if event.get('kind') == 'read' and 'group' in event:
            traced_groups[event['group']].append(event['id'])
    groups += [dict(id=key, events=ids) for key, ids in traced_groups.items()]
    for group in groups:
        members = [event_by_id.get(eid) for eid in group.get('events', [])]
        if not members or any(x is None or x.get('kind') != 'read' for x in members):
            error('invalid_response_group', group=group); continue
        if any('response_cycle' not in x for x in members):
            error('missing_response_group_timing', group=group); continue
        if len({x['response_cycle'] for x in members}) != 1:
            error('response_group_split', group=group)
    measured = profile is not None or contract.get('measured_native_bounds') is True
    coverage = all(schedule.get(x) for x in ('events', 'jobs')) and (schedule.get('trace_complete') is True or schedule.get('complete_actual_trace') is True)
    gaps = {'missing_reservation', 'missing_slot_capacity', 'missing_client_capacity',
            'missing_job_boundary', 'missing_producer_done', 'missing_dependency_retirement',
            'missing_response_group_timing', 'missing_bank_enqueue', 'missing_bank_queue_capacity',
            'missing_ingress_resource'}
    contradictory = any(x['kind'] not in gaps for x in errors)
    status = 'fail' if contradictory else 'pass' if not errors and measured and coverage else 'incomplete'
    return dict(status=status, qualified=False, events=len(schedule.get('events', [])), violations=errors,
                slot_peaks=peaks, bank_queue_peaks=bank_peaks, vm_service_profile=(contract.get('vm_service_profile') or {}).get('name'), bank_mapping=contract.get('bank_mapping', 'rowmod'), measured_native_bounds=measured, trace_complete=coverage,
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
