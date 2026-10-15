#!/usr/bin/env python3
"""Lower fixed stage programs to native VM calendars using explicit owner bindings.

No fixture values or observed ready/credit signals enter compilation. Missing
producer mappings or phase-specific native service templates block the entire
stage. This compiler never invents ports, latencies or an operand allocation.
The separate static_vm_reservations checker validates the generated calendar.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
from static_vm_reservations import check


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def integer(value, label, low=0):
    if type(value) is not int or value < low:
        raise ValueError(f'{label} requires integer >= {low}')
    return value


def validate_evidence(evidence, root):
    if not evidence:
        raise ValueError('missing source-pinned native evidence')
    for item in evidence:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('evidence outside source tree')
        if digest(path) != item['sha256']:
            raise ValueError(f'stale native evidence {item["path"]}')


def compile_program(program, binding, contract, root=ROOT):
    """Atomic lowering; every program op, even a non-VM op, needs a binding.

    Binding tensors have fixed rows, sizes, producer job (or declared external
    input / resident constant), and consumers. Job accesses reference tensors
    and explicit row offsets. Their source-pinned templates contain every exact
    edge relative to start, separately for stream and VM domains. A template is
    only valid for its declared start phase; no latency rounding is performed.
    """
    rejected, schedule = [], dict(events=[], jobs=[], dependencies=[], groups=[], trace_complete=False)
    def reject(kind, **extra):
        rejected.append(dict(kind=kind, **extra))
    ops = program.get('ops', [])
    jobs = binding.get('jobs', {})
    tensors = binding.get('tensors', {})
    by_id = {op['id']: op for op in ops}
    if len(by_id) != len(ops) or not ops:
        reject('invalid_program_ids')
    if binding.get('stage') != program.get('stage'):
        reject('stage_binding_mismatch')
    for ident in sorted(set(jobs) - set(by_id)):
        reject('extra_native_binding', job=ident)
    for ident, op in by_id.items():
        if ident not in jobs:
            reject('missing_native_job_binding', job=ident, engine=op['eng'])
    # Physical addresses are explicit: never adopt su_gate's snapshot allocator.
    valid_tensors = {}
    for name, tensor in tensors.items():
        try:
            base = integer(tensor['base_row'], 'base_row')
            size = integer(tensor['nrows'], 'nrows', 1)
            if base + size > 16384:
                raise ValueError('tensor exceeds VM address space')
            source = tensor['source']
            if source not in ('native_job', 'external_input', 'resident_constant'):
                raise ValueError('reference/fixture-produced tensor forbidden')
            if source == 'native_job' and tensor.get('producer') not in by_id:
                raise ValueError('tensor producer absent from stage')
            if not isinstance(tensor.get('consumers'), list):
                raise ValueError('tensor consumers must be explicit')
            if any(c not in by_id for c in tensor['consumers']):
                raise ValueError('tensor consumer absent from stage')
            validate_evidence(tensor.get('evidence'), root)
            valid_tensors[name] = tensor
        except (ValueError, KeyError, TypeError, OSError) as exc:
            reject('invalid_tensor_binding', tensor=name, reason=str(exc))
    # Refuse allocation aliasing whenever tensor live intervals overlap.
    names = sorted(valid_tensors)
    def lifetime(t):
        start = by_id[t['producer']]['start'] if t['source'] == 'native_job' else 0
        end = max([by_id[c]['end'] for c in t['consumers']] + [start])
        return start, end
    for i, name in enumerate(names):
        a = valid_tensors[name]
        for other in names[i+1:]:
            b = valid_tensors[other]
            if max(a['base_row'], b['base_row']) >= min(a['base_row']+a['nrows'], b['base_row']+b['nrows']):
                continue
            la, lb = lifetime(a), lifetime(b)
            if max(la[0], lb[0]) <= min(la[1], lb[1]):
                reject('live_tensor_address_alias', tensors=[name, other])
    writes, reads = {}, []
    for ident, op in by_id.items():
        if ident not in jobs:
            continue
        job = jobs[ident]
        try:
            validate_evidence(job.get('evidence'), root)
            if job.get('implementation') != 'native_rtl':
                raise ValueError('operation requires native RTL')
            if job.get('engine') != op['eng'] or not job.get('endpoint'):
                raise ValueError('native engine/endpoint mismatch')
            start = integer(op['start'], 'start')
            duration = integer(job['duration_cycles'], 'duration', 1)
            if op['end'] != start + duration:
                raise ValueError('program duration differs from native fixed duration; recompile graph')
            period = integer(job['phase_period_stream'], 'phase period', 1)
            if start % period != integer(job['start_phase_stream'], 'start phase'):
                raise ValueError('native template does not match scheduled clock phase')
            sp, vp = Fraction(str(contract['stream_period_ps'])), Fraction(str(contract['vm_period_ps']))
            if period * sp % vp:
                raise ValueError('phase period does not repeat VM phase')
            tstart = Fraction(str(contract['stream_phase_ps'])) + start * sp
            vm_origin = (tstart - Fraction(str(contract['vm_phase_ps']))) // vp
            events = job['accesses']
            if not isinstance(events, list):
                raise ValueError('accesses must be explicit, including empty lists')
            for i, access in enumerate(events):
                tensor = valid_tensors[access['tensor']]
                offset = integer(access['row_offset'], 'row_offset')
                if offset >= tensor['nrows']:
                    raise ValueError('access outside tensor allocation')
                kind = access['kind']
                if kind not in ('read', 'write'):
                    raise ValueError('unsupported native access kind')
                if kind == 'write' and (tensor['source'] != 'native_job' or tensor.get('producer') != ident):
                    raise ValueError('write has wrong native producer')
                if kind == 'read' and ident not in tensor['consumers']:
                    raise ValueError('read has undeclared tensor consumer')
                event = dict(id=f'{ident}/access/{i}', client=job['client'], job=ident,
                             kind=kind, tensor=access['tensor'], row=tensor['base_row']+offset,
                             slot=integer(access['slot'], 'slot'), tag=integer(job['tag'], 'tag'))
                for field in ('issue_cycle', 'deadline_cycle', 'response_cycle' if kind == 'read' else 'commit_cycle'):
                    event[field] = start + integer(access[field], field)
                for field in ('ingress_cycle', 'bank_enqueue_cycle', 'service_cycle'):
                    event[field] = int(vm_origin) + integer(access[field], field)
                if event['deadline_cycle'] > op['end']:
                    raise ValueError('access deadline extends beyond native job completion')
                event['mask'] = integer(access.get('mask', 65535), 'mask', 1)
                if event['mask'] > 65535:
                    raise ValueError('mask exceeds physical row width')
                if 'group' in access:
                    event['group'] = f'{ident}/{access["group"]}'
                schedule['events'].append(event)
                key = access['tensor'], offset
                if kind == 'write':
                    writes.setdefault(key, []).append(event)
                elif tensor['source'] == 'native_job':
                    reads.append((key, event))
            schedule['jobs'].append(dict(client=job['client'], job=ident, tag=job['tag'], done_cycle=op['end']))
        except (ValueError, KeyError, TypeError, OSError) as exc:
            reject('invalid_native_job_binding', job=ident, reason=str(exc))
    for key, event in reads:
        producers = writes.get(key, [])
        covered = 0
        for producer in producers:
            if producer['mask'] & event['mask']:
                schedule['dependencies'].append(dict(producer=producer['id'], consumer=event['id']))
                covered |= producer['mask']
        if covered & event['mask'] != event['mask']:
            reject('unproduced_native_read', event=event['id'], tensor=key[0], row_offset=key[1])
    # Native engine port occupancy must also fit the fixed graph.
    ports = {}
    for op in ops:
        for old in ports.setdefault(op['port'], []):
            if max(old['start'], op['start']) < min(old['end'], op['end']):
                reject('engine_overlap', jobs=[old['id'], op['id']], port=op['port'])
        ports[op['port']].append(op)
        for pred in op.get('preds', []):
            if type(pred) is not int or not 0 <= pred < len(ops) or ops[pred]['end'] > op['start']:
                reject('invalid_job_dependency', job=op['id'], predecessor=pred)
    schedule['trace_complete'] = not rejected
    checked = check(schedule, contract) if not rejected else None
    ready = not rejected and checked['status'] == 'pass'
    return dict(status='COMPILED_STATIC_CALENDAR' if ready else 'STATIC_COMPILE_BLOCKED',
                dispatch_eligible=ready, qualified=False, stage=program.get('stage'),
                jobs_required=len(ops), jobs_bound=len(schedule['jobs']), rejections=rejected,
                reservations=checked, schedule=schedule if ready else None,
                note='Compiler lowering only; actual native RTL replay and die timing remain mandatory.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    bindings = json.loads(args.bindings.read_text())
    contract = json.loads(args.contract.read_text())
    reports = []
    for source in sorted(args.programs.glob('S[0-9][0-9][0-9].json')):
        program = json.loads(source.read_text())
        report = compile_program(program, bindings.get(program['stage'], {}), contract)
        report['program_sha256'] = digest(source)
        reports.append(report)
    result = dict(status='COMPILED_STATIC_CALENDARS' if reports and all(r['dispatch_eligible'] for r in reports)
                  else 'STATIC_COMPILE_BLOCKED', stages=len(reports), reports=reports,
                  bindings_sha256=digest(args.bindings), contract_sha256=digest(args.contract))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(f"{result['status']}: {len(reports)} stages, {sum(r['jobs_bound'] for r in reports)}/{sum(r['jobs_required'] for r in reports)} native jobs bound")
    return 0 if result['status'] == 'COMPILED_STATIC_CALENDARS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
