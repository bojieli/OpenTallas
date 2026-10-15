#!/usr/bin/env python3
"""Lower fixed stage programs to native VM calendars using explicit owner bindings.

No fixture values or observed ready/credit signals enter compilation. Missing
producer mappings or phase-specific native service templates block the entire
stage. This compiler never invents ports, latencies or an operand allocation.
The separate static_vm_reservations checker validates the generated calendar.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
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


# Actual ot_s81_fixed_issue row semantics (single source for every engine):
# 'issue' is the context age whose edge loads the command register, so the
# command pin rises at issue+1; 'done' is the age whose edge samples the
# completion pin. A native owner's duration_cycles is its measured
# command-pin -> done-pin latency (timing_boundary sequencer_cmd_pin_to_done_pin),
# hence done = issue + 1 + pin_to_pin. done = issue + pin_to_pin misses the
# completion by one edge (issuer fault 8; MIX4 layer run 10-15, reproduced by
# tb_s81_engram_mix4_fixed: 1428 FAIL code 8, 1429 PASS, 1430 FAIL code 6).
ISSUE_TO_CMD_PIN_EDGES = 1


def issuer_done_row(issue, pin_to_pin):
    """Compiled done row of an issuer command with measured pin-to-pin latency."""
    if type(issue) is not int or issue < 0 or type(pin_to_pin) is not int or pin_to_pin < 1:
        raise ValueError('integer issue row and measured command-pin -> done-pin latency required')
    return issue + ISSUE_TO_CMD_PIN_EDGES + pin_to_pin


def validate_evidence(evidence, root):
    if not evidence:
        raise ValueError('missing source-pinned native evidence')
    for item in evidence:
        path = (root / item['path']).resolve()
        if not path.is_relative_to(root.resolve()):
            raise ValueError('evidence outside source tree')
        if digest(path) != item['sha256']:
            raise ValueError(f'stale native evidence {item["path"]}')


def check_persistent_state(program, binding, root):
    """Validate finite CP context ownership across native store/pool jobs."""
    errors=[]
    ops={o['id']:o for o in program['ops']}
    jobs=binding.get('jobs',{})
    reservations=binding.get('persistent_buffers',[])
    required={name for name,job in jobs.items() if job.get('opcode')==14 or name.endswith('.attn.cmp.pool')}
    covered=set();physical={};seen=set()
    for state in reservations:
        try:
            ident=state['id']
            if ident in seen: raise ValueError('duplicate persistent reservation')
            seen.add(ident)
            if state['cache']!='CP': raise ValueError('unowned persistent cache')
            instance=state['physical_cache_instance']
            declared=binding.get('persistent_cache_instances',{}).get(instance)
            if not declared or declared.get('type')!='CP' or declared.get('physical_groups')!=1:
                raise ValueError('physical CP instance lacks actual one-group contract')
            validate_evidence(declared.get('evidence'),root)
            # The implemented CP cache holds one history group. More users
            # require distinct actual physical banks, not larger dictionary IDs.
            if state['physical_bank']!=0: raise ValueError('CP physical bank not implemented')
            context=integer(state['context_id'],'CP context')
            if context>=1<<32 or not isinstance(state['context_key'],str) or not state['context_key']:
                raise ValueError('full CP logical context and uint32 identity required')
            begin=integer(state['live_from_cycle'],'context live begin')
            end=integer(state['live_until_cycle'],'context live end')
            if end<=begin: raise ValueError('invalid CP state lifetime')
            producer=state['producer_job']
            if producer not in ops or jobs.get(producer,{}).get('implementation')!='native_rtl':
                raise ValueError('missing actual native first-slot store/restore producer')
            commit=integer(state['producer_commit_cycle'],'native state commit')
            if not ops[producer]['start']<=commit<=ops[producer]['end'] or not begin<=commit<end:
                raise ValueError('state commit outside native producer/lifetime')
            # A restore must itself read prior state produced by actual native
            # execution in retained VM. Golden initialization is never a source.
            inputs=state['state_input_tensors']
            if set(inputs)!={'kv','score'}: raise ValueError('CP requires actual prior K and score producers')
            for tensor_name in inputs.values():
                tensor=binding.get('tensors',{}).get(tensor_name,{})
                source=tensor.get('producer')
                if tensor.get('source')!='native_job' or source not in ops or jobs.get(source,{}).get('implementation')!='native_rtl':
                    raise ValueError('prior CP state has no native tensor producer')
            consumers=state['consumer_jobs']
            if not consumers: raise ValueError('persistent state has no native pool consumer')
            for consumer in consumers:
                if consumer not in required or not commit<ops[consumer]['start'] or ops[consumer]['end']>end:
                    raise ValueError('pool outside fixed committed-state lifetime')
                covered.add(consumer)
            validate_evidence(state.get('evidence'),root)
            key=instance,state['physical_bank']
            for old_begin,old_end,old_context in physical.setdefault(key,[]):
                if max(begin,old_begin)<min(end,old_end):
                    raise ValueError('overlapping open contexts on single physical CP cache')
            physical[key].append((begin,end,state['context_key']))
        except (ValueError,KeyError,TypeError,OSError) as exc:
            errors.append(dict(kind='invalid_persistent_state',reservation=state.get('id'),reason=str(exc)))
    for consumer in sorted(required-covered):
        errors.append(dict(kind='missing_native_persistent_state',job=consumer))
    return errors


def tensor_span_end(tensor):
    """Exclusive reserved physical bound; nrows counts actual logical rows."""
    base = integer(tensor['base_row'], 'base_row')
    size = integer(tensor['nrows'], 'nrows', 1)
    stride = integer(tensor.get('row_stride', 1), 'row_stride', 1)
    actual_span = (size - 1) * stride + 1
    reserved = integer(tensor.get('reserved_span_rows', actual_span), 'reserved_span_rows', 1)
    if reserved < actual_span:
        raise ValueError('reserved span excludes sparse physical rows')
    return base + reserved


def tensor_physical_row(tensor, logical_offset):
    offset = integer(logical_offset, 'row_offset')
    if offset >= integer(tensor['nrows'], 'nrows', 1):
        raise ValueError('access outside tensor allocation')
    return integer(tensor['base_row'], 'base_row') + offset * integer(tensor.get('row_stride', 1), 'row_stride', 1)


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
    rejected.extend(check_persistent_state(program,binding,root))
    # Physical addresses are explicit: never adopt su_gate's snapshot allocator.
    valid_tensors = {}
    for name, tensor in tensors.items():
        try:
            base = integer(tensor['base_row'], 'base_row')
            size = integer(tensor['nrows'], 'nrows', 1)
            if tensor_span_end(tensor) > 16384:
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
            if max(a['base_row'], b['base_row']) >= min(tensor_span_end(a), tensor_span_end(b)):
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
            if op['end'] != issuer_done_row(start, duration):
                raise ValueError('done row must be issue + 1 + native command-pin -> done-pin latency; recompile graph')
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
                physical_row = tensor_physical_row(tensor, offset)
                kind = access['kind']
                if kind not in ('read', 'write'):
                    raise ValueError('unsupported native access kind')
                if kind == 'write' and (tensor['source'] != 'native_job' or tensor.get('producer') != ident):
                    raise ValueError('write has wrong native producer')
                if kind == 'read' and ident not in tensor['consumers']:
                    raise ValueError('read has undeclared tensor consumer')
                event = dict(id=f'{ident}/access/{i}', client=job['client'], job=ident,
                             kind=kind, tensor=access['tensor'], row=physical_row,
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
                if 'read_visibility' in access:
                    event['read_visibility'] = access['read_visibility']
                if 'ingress_resource' in access:
                    event['ingress_resource'] = access['ingress_resource']
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
    checked = check(schedule, contract, root) if not rejected else None
    ready = not rejected and checked['status'] == 'pass'
    return dict(status='COMPILED_STATIC_CALENDAR' if ready else 'STATIC_COMPILE_BLOCKED',
                dispatch_eligible=ready, qualified=False, stage=program.get('stage'),
                jobs_required=len(ops), jobs_bound=len(schedule['jobs']), rejections=rejected,
                reservations=checked, schedule=schedule if ready else None,
                note='Compiler lowering only; actual native RTL replay and die timing remain mandatory.')


def schedule_jobs(program, binding):
    """Compile engine issue times offline from owned durations and clock phases.

    Memory/transfer reservations are subsequently lowered and checked; a
    conflict is a compile failure, never runtime waiting. The ordering is the
    emitted program order, with one in-flight job per physical engine port.
    Owner lowering must first fuse graph nodes that the real native job fuses.
    """
    result = deepcopy(program)
    ops = result.get('ops', [])
    bindings = binding.get('jobs', {})
    if not ops or set(bindings) != {op['id'] for op in ops}:
        raise ValueError('offline scheduling requires every native job binding exactly once')
    ends, ports = {}, {}
    for index, op in enumerate(ops):
        owner = bindings[op['id']]
        duration = integer(owner['duration_cycles'], 'native duration', 1)
        phase_period = integer(owner['phase_period_stream'], 'phase period', 1)
        phase = integer(owner['start_phase_stream'], 'start phase')
        if phase >= phase_period:
            raise ValueError('start phase outside recurring phase period')
        predecessors = op.get('preds', [])
        if any(type(p) is not int or p not in ends for p in predecessors):
            raise ValueError(f"{op['id']} requires topologically ordered native predecessors")
        earliest = max([integer(op.get('ext', 0), 'external arrival'), ports.get(op['port'], 0)]
                       + [ends[p] for p in predecessors])
        start = earliest + (phase - earliest) % phase_period
        # end is the issuer done row; the engine port is occupied until it.
        op.update(start=start, end=issuer_done_row(start, duration), dur=duration)
        ends[index] = op['end']
        ports[op['port']] = op['end']
    previous = program.get('makespan', max(o['end'] for o in program['ops']))
    result['makespan'] = max(ends.values())
    result['offline_schedule'] = dict(policy='done = issue + 1 + native pin-to-pin duration, single inflight per port, explicit clock phase',
                                     original_makespan=previous, native_makespan=result['makespan'],
                                     added_cycles=result['makespan']-previous,
                                     performance_accepted=False)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--schedule-native-jobs', action='store_true',
                        help='Compile offline port/phase issue times using actual owned native durations')
    args = parser.parse_args()
    bindings = json.loads(args.bindings.read_text())
    contract = json.loads(args.contract.read_text())
    reports = []
    for source in sorted(args.programs.glob('S[0-9][0-9][0-9].json')):
        program = json.loads(source.read_text())
        binding = bindings.get(program['stage'], {})
        try:
            if args.schedule_native_jobs:
                program = schedule_jobs(program, binding)
            report = compile_program(program, binding, contract)
            if args.schedule_native_jobs:
                report['compiled_program'] = program
        except (ValueError, KeyError, TypeError) as error:
            report = dict(stage=program['stage'], dispatch_eligible=False, qualified=False,
                          jobs_required=len(program['ops']), jobs_bound=0,
                          rejections=[dict(kind='native_schedule_blocked', reason=str(error))])
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
