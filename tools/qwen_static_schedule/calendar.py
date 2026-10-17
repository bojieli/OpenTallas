#!/usr/bin/env python3
"""Compile native instruction microcalendars; observed traces never set issue times.

Times are integer femtoseconds. A microcalendar describes fixed, implemented
ports relative to instruction issue, including physical/CDC pipelines. Each
instruction is bound by its complete encoded word, not its opcode alone.
Unknown implementations are errors, not zero-latency operations.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA


class ScheduleError(ValueError):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pins(root, source_pins):
    if not source_pins:
        raise ScheduleError('missing implementation source pins')
    for filename, digest in source_pins.items():
        path = (root / filename).resolve()
        if not path.is_file() or sha(path) != digest:
            raise ScheduleError(f'source mismatch: {filename}')


def edge_after(time, domain):
    period, phase = domain['period_fs'], domain['phase_fs']
    return phase + max(0, (time - phase + period - 1) // period) * period


def inventory(programs):
    """Inventory actual words; never reconstruct instructions from a trace."""
    result = []
    for stage, program in enumerate(programs):
        raw = program.read_bytes()
        for pc, text in enumerate(raw.decode().split()):
            word = int(text, 16)
            if not 0 <= word < 1 << 1024:
                raise ScheduleError('instruction exceeds actual 1024-bit ISA')
            result.append(dict(stage=stage, pc=pc, word=f'{word:0256x}', unit=ISA.decode(word)['unit'],
                               program_sha256=hashlib.sha256(raw).hexdigest()))
    return result


def compile_calendar(programs, contract, root):
    if contract.get('schema') != 'opentallas.qwen-native-microcalendar.v1':
        raise ScheduleError('unknown microcalendar schema')
    pins(root, contract['source_sha256'])
    # Apply hardware deltas before dependencies and native resources are solved.
    from qwen_static_schedule.b2_timing import fold
    contract = fold(contract, root)
    clocks = contract['clocks']
    if not clocks or any(d['period_fs'] <= 0 or not 0 <= d['phase_fs'] < d['period_fs'] for d in clocks.values()):
        raise ScheduleError('invalid implemented clock periods/phases')
    resources = contract['resources']
    if any(r.get('capacity', 0) < 1 or r['clock'] not in clocks for r in resources.values()):
        raise ScheduleError('invalid implemented resource/clock')
    if not 0 <= contract.get('start_fs', 0) <= contract['deadline_fs']:
        raise ScheduleError('invalid compiler startup/deadline')
    expected = inventory(programs)
    implementations = {(v['stage'], v['pc']): v for v in contract['instructions']}
    if len(implementations) != len(contract['instructions']):
        raise ScheduleError('duplicate instruction implementation')
    missing = [(v['stage'], v['pc']) for v in expected if (v['stage'], v['pc']) not in implementations]
    if missing or len(expected) != len(implementations):
        raise ScheduleError(f'incomplete actual instruction coverage: {missing}')
    # Keys identify immutable values/epochs, not physical addresses reused later.
    produced = {}
    for value in contract.get('external_inputs', []):
        if value['boundary'] not in ('offchip', 'reset'):
            raise ScheduleError('internal live-in must have actual preceding-stage producer')
        if value['key'] in produced:
            raise ScheduleError('duplicate external input')
        produced[value['key']] = value['available_fs']
    occupied = {}
    events = []
    issues = []
    last_issue = 0
    # This explicit compiler startup region permits pre-producer arm transport.
    # It is part of charged execution, never a hidden runtime wait.
    earliest = contract.get('start_fs', 0)
    for actual in expected:
        key = actual['stage'], actual['pc']
        impl = implementations[key]
        if impl['word'].lower().zfill(256) != actual['word']:
            raise ScheduleError(f'encoded instruction mismatch: {key}')
        if impl['unit'] != actual['unit']:
            raise ScheduleError(f'native owner differs from actual instruction unit: {key}')
        if not impl.get('rtl_instance') or not impl.get('rtl_module'):
            raise ScheduleError(f'missing native instance/module: {key}')
        clock = clocks[impl['clock']]
        relative = impl['events']
        # Resource occupancy is a compiler reservation, not a fabricated RTL
        # port event in the timeline consumed by native trace verification.
        reserve_only = impl.get('b2_copy_reservations', [])
        slots = relative + reserve_only
        if not relative and not impl.get('control_only', False):
            raise ScheduleError(f'missing native port events: {key}')
        ids = [e['id'] for e in relative]
        if len(ids) != len(set(ids)):
            raise ScheduleError('duplicate microevent id')
        for e in slots:
            if e['offset_fs'] < 0 or e['resource'] not in resources:
                raise ScheduleError('negative/unmapped native event')
            if e.get('dynamic', False):
                raise ScheduleError('runtime arbitration/credits cannot schedule production')
        candidate = max(earliest, last_issue)
        for event in relative:
            for dependency in event.get('requires', []):
                if dependency not in produced:
                    raise ScheduleError(f'incomplete producer {dependency} at {key}/{event["id"]}')
                # Read edge must be strictly after the committed write edge.
                candidate = max(candidate, produced[dependency] + 1 - event['offset_fs'])
        candidate = edge_after(candidate, clock)
        alignment_period = math.lcm(clock['period_fs'], *(clocks[resources[e['resource']]['clock']]['period_fs'] for e in slots))
        alignment_start = candidate
        while any(edge_after(candidate + e['offset_fs'], clocks[resources[e['resource']]['clock']]) != candidate + e['offset_fs'] for e in slots):
            candidate += clock['period_fs']
            if candidate - alignment_start >= alignment_period:
                raise ScheduleError('incompatible clock/phase microcalendar')
        # Reservations are solved HERE at compile time. No ready input exists.
        while True:
            local = {}
            conflict = False
            for event in slots:
                time = candidate + event['offset_fs']
                resource = resources[event['resource']]
                if edge_after(time, clocks[resource['clock']]) != time:
                    conflict = True
                    continue
                slot = event['resource'], time
                demand = event.get('amount', 1)
                if not 1 <= demand <= resource['capacity']:
                    raise ScheduleError('event exceeds physical port capacity')
                local[slot] = local.get(slot, 0) + demand
                if local[slot] > resource['capacity']:
                    raise ScheduleError(f'instruction inherently oversubscribes resource {slot}')
                if local[slot] + occupied.get(slot, 0) > resource['capacity']:
                    conflict = True
            if not conflict:
                break
            candidate += clock['period_fs']
            if candidate > contract['deadline_fs']:
                raise ScheduleError('resource reservations exceed compiled deadline')
        if candidate > contract['deadline_fs']:
            raise ScheduleError('instruction issue exceeds compiled deadline')
        if 'issue_at_fs' in impl and candidate != impl['issue_at_fs']:
            raise ScheduleError(f'fixed issue slot conflicts with dependencies/resources: {key}')
        issues.append(dict(stage=key[0], pc=key[1], time_fs=candidate, unit=impl['unit']))
        for reservation in reserve_only:
            time = candidate + reservation['offset_fs']
            if time > contract['deadline_fs']:
                raise ScheduleError('native copy reservation exceeds compiled deadline')
            slot = reservation['resource'], time
            occupied[slot] = occupied.get(slot, 0) + 1
        for event in relative:
            time = candidate + event['offset_fs']
            if time > contract['deadline_fs']:
                raise ScheduleError('native event exceeds compiled deadline')
            slot = event['resource'], time
            occupied[slot] = occupied.get(slot, 0) + event.get('amount', 1)
            for value in event.get('produces', []):
                if value in produced:
                    raise ScheduleError(f'value/epoch produced twice: {value}')
                produced[value] = time
            events.append(dict(event, stage=key[0], pc=key[1], time_fs=time,
                               event_id=f'{key[0]}:{key[1]}:{event["id"]}'))
        # The physical instruction issue port is never double-booked.
        last_issue = candidate + clock['period_fs']
    # Check exact buffer occupancy, including edge order defined by hardware.
    buffers = contract.get('buffers', {})
    levels = {name: spec.get('initial', 0) for name, spec in buffers.items()}
    peaks = dict(levels)
    for event in sorted(events, key=lambda e: (e['time_fs'], e.get('edge_order', 0), e['event_id'])):
        for name, delta in event.get('buffer_delta', {}).items():
            if name not in buffers:
                raise ScheduleError('unmapped finite buffer')
            levels[name] += delta
            peaks[name] = max(peaks[name], levels[name])
            if not 0 <= levels[name] <= buffers[name]['capacity']:
                raise ScheduleError(f'static buffer overflow/underflow: {name} at {event["event_id"]}')
    for name, spec in buffers.items():
        if levels[name] != spec.get('final', 0):
            raise ScheduleError(f'undrained native buffer: {name}')
    return dict(schema='opentallas.qwen-compiled-static-calendar.v1',
                status='COMPILED_NOT_NATIVE_VERIFIED', source_sha256=contract['source_sha256'],
                program_sha256=[sha(p) for p in programs],
                contract_sha256=hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest(),
                issues=issues, events=events, buffer_peaks=peaks,
                b2_timing_applied=contract.get('b2_timing_applied'),
                end_fs=max([e['time_fs'] for e in events] + [i['time_fs'] for i in issues]),
                claim='Compiler reservations only. Native RTL trace, complete hardware binding and physical qualification remain required.')


def verify_trace(calendar, trace, root):
    """Compare real port/issue observations against a pre-existing calendar."""
    pins(root, calendar['source_sha256'])
    if trace['program_sha256'] != calendar['program_sha256'] or trace['source_sha256'] != calendar['source_sha256']:
        raise ScheduleError('native trace program/implementation differs from compiler inputs')
    if trace.get('producer') != 'native_rtl_ports' or not trace.get('elaboration_sha256'):
        raise ScheduleError('modeled/reference execution cannot verify native calendar')
    if any(trace.get(k, 0) for k in ('credit_stalls', 'ready_stalls', 'unplanned_stalls', 'reference_substitutions')):
        raise ScheduleError('production trace contains stalls/reference substitutions')
    def signature(e):
        fields = ('event_id', 'time_fs', 'resource', 'kind', 'address', 'mask', 'lanes', 'stride', 'beat', 'epoch')
        return json.dumps({k:e[k] for k in fields if k in e}, sort_keys=True)
    expected = sorted(signature(e) for e in calendar['events'])
    observed = sorted(signature(e) for e in trace['events'])
    if expected != observed or calendar['issues'] != trace['issues']:
        raise ScheduleError('actual native port/issue timeline differs from compiled calendar')
    return dict(status='NATIVE_TIMELINE_MATCH', events=len(expected), issues=len(calendar['issues']),
                claim='Exact supplied native port timeline match; full die functionality and physical closure are separate gates.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--program', type=Path, action='append', required=True)
    p.add_argument('--contract', type=Path, required=True)
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    p.add_argument('--trace', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    result = compile_calendar(a.program, json.loads(a.contract.read_text()), a.root)
    if a.trace:
        result['verification'] = verify_trace(result, json.loads(a.trace.read_text()), a.root)
    a.out.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
