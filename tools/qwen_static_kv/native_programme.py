#!/usr/bin/env python3
"""Compile the native K/V writer's four fixed slots from actual layer bytes.

This is a writer-only candidate. Explicit path ages, never observation traces,
set its timeline. Controller/front/ring calendars are unsupported and refused.
Component-test images are marked noninstallable; they cannot acquire production
status by passing a functional simulator.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qwen_static_schedule.calendar import ScheduleError, pins, sha
from qwen_static_schedule.segments import MissingPhysicalProfile, program_segments, physical_profile
from qwen_static_schedule.dense_image import native_capability

ROOT = Path(__file__).resolve().parents[2]
PRODUCER = 'rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv'
WRITER = 'rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv'
PATHS = ('formatter_to_writer', 'expectation_to_writer', 'reset_release')
FOOTER = 0x514b565052473031  # QKVPRG01


def source_contract(program, descriptors, plan, stage):
    if plan.get('schema') != 'opentallas.qwen-tp8-token-source-plan.v1' or \
       tuple(plan.get(k) for k in ('tp', 'groups', 'layers', 'stage_count', 'layer_candidate_words')) != (8, 3072, 36, 38, 25):
        raise ScheduleError('actual TP8/GT3072/all36/38-stage/25-word source plan required')
    pins(ROOT, plan.get('source_sha256', {}))
    if hashlib.sha256(program).hexdigest() != plan.get('files_sha256', {}).get('layer_candidate_program.hex'):
        raise ScheduleError('layer programme differs from actual source-plan bytes')
    desc = [int(w, 16) for w in descriptors.split()]
    if len(desc) > 8:
        raise ScheduleError('actual descriptor capacity exceeded')
    if hashlib.sha256(descriptors).hexdigest() != plan.get('files_sha256', {}).get('layer_candidate_segments.hex'):
        raise ScheduleError('descriptors differ from actual source-plan bytes')
    seg = program_segments(program, desc + [0] * (8-len(desc)))
    if [x['first_pc'] for x in seg] != [0, 14, 22] or not native_capability([int(w,16) for w in program.split()], stage):
        raise ScheduleError('actual native PC11 decoder segment required')
    return seg


def ages(profile, program, component_test):
    required = ('period_fs', 'phase_fs', 'segment_start_cycle', 'word_producer_age_fs',
                'word_stride_fs', 'stop_cycle', 'source_sha256')
    missing = [k for k in required if profile.get(k) is None]
    if not component_test:
        missing += [k for k in ('receipt_path', 'receipt_sha256') if profile.get(k) is None]
        if profile.get('physical_profile_status') != 'MEASURED':
            missing.append('physical_profile_status=MEASURED')
    if missing:
        raise MissingPhysicalProfile(missing)
    pins(ROOT, profile['source_sha256'])
    for path in (PRODUCER, WRITER, 'rtl/qwen_split/qfd_kvn_static_transport.sv', 'rtl/qwen_split/qfd_native59_compute_service.sv',
                 'rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv',
                 'rtl/physical/ot_qkd_kv_static_writer_native.sv','rtl/lib/ot_rst_relay.sv'):
        if path not in profile['source_sha256']:
            raise MissingPhysicalProfile(['source_sha256.' + path])
    if component_test:
        measured = profile.get('component_path_ages_fs', {})
    else:
        receipt_path = ROOT / profile['receipt_path']
        if not receipt_path.is_file() or sha(receipt_path) != profile['receipt_sha256']:
            raise ScheduleError('measured receipt missing or changed')
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('status') != 'QUALIFIED' or receipt.get('program_sha256') != hashlib.sha256(program).hexdigest():
            raise ScheduleError('physical receipt not qualified for actual programme')
        for key in required:
            if receipt.get(key) != profile[key]:
                raise ScheduleError('physical receipt/profile mismatch: ' + key)
        measured = {}
        for name in PATHS:
            path = receipt.get('qualified_paths', {}).get(name, {})
            if path.get('status') != 'QUALIFIED' or path.get('age_fs') is None:
                raise MissingPhysicalProfile(['receipt.qualified_paths.' + name])
            evidence = ROOT / path.get('evidence_path', '')
            if not evidence.is_file() or sha(evidence) != path.get('evidence_sha256'):
                raise ScheduleError('physical path evidence missing or changed: ' + name)
            measured[name] = path['age_fs']
    for name in PATHS:
        if name not in measured:
            raise MissingPhysicalProfile(['path_age_fs.' + name])
        if type(measured[name]) is not int or measured[name] < 0:
            raise ScheduleError('invalid explicit path age: ' + name)
    return measured


def compile_programme(program, descriptors, plan, profile, stage, *, component_test=False):
    source_contract(program, descriptors, plan, stage)
    if profile.get('scope', 'writer') != 'writer':
        raise MissingPhysicalProfile(['unsupported_controller_front_ring_profiles'])
    path_ages = ages(profile, program, component_test)
    if not component_test:
        physical_profile(profile.get('segment_profile', {}), program)
        if any(profile['segment_profile'][k] != profile[k] for k in ('period_fs','phase_fs')):
            raise MissingPhysicalProfile(['implemented_segment_to_writer_clock_conversion'])
        if profile['segment_profile']['segments'][0]['core_start_cycle'] != profile['segment_start_cycle']:
            raise ScheduleError('writer origin differs from actual segment0 core start')
    for key in ('period_fs', 'phase_fs', 'segment_start_cycle', 'word_producer_age_fs', 'word_stride_fs', 'stop_cycle'):
        if type(profile[key]) is not int:
            raise ScheduleError('integer femtosecond/cycle profile required: ' + key)
    period = profile['period_fs']; phase = profile['phase_fs']
    if period <= 0 or not 0 <= phase < period or profile['segment_start_cycle'] < 0 or profile['word_producer_age_fs'] < 0 or profile['word_stride_fs'] <= 0:
        raise ScheduleError('invalid source writer clock/timeline')
    # Source producer emits K low/high then V low/high. No payload/ready/credit
    # input participates in either the compile-time or runtime slot equations.
    first_fs = phase + profile['segment_start_cycle'] * period + profile['word_producer_age_fs'] + path_ages['formatter_to_writer']
    times = [first_fs + n * profile['word_stride_fs'] for n in range(4)]
    if any(t < phase or (t-phase) % period for t in times):
        raise ScheduleError('actual formatter words do not land on assigned writer edges')
    cycles = [(t-phase)//period for t in times]
    reset_edges = max(4, (path_ages['reset_release'] + period-1)//period)
    expectation_age = path_ages['expectation_to_writer']
    # This revision has a direct registered root next to the writer. A routed
    # expectation hop must be represented in RTL, rather than subtracted away.
    if expectation_age >= period:
        raise MissingPhysicalProfile(['implemented_expectation_relay_for_age_ge_period'])
    stop = profile['stop_cycle']
    if not reset_edges <= cycles[0] or not cycles[-1]+2 < stop < 1<<32:
        raise ScheduleError('writer slots violate reset release, drain, or stop32')
    writes = [dict(address=n, data_hex=f'{cycle:016x}') for n,cycle in enumerate(cycles)]
    writes += [dict(address=4, data_hex=f'{((stage<<32)|stop):016x}'), dict(address=5, data_hex=f'{FOOTER:016x}')]
    return dict(schema='opentallas.qwen-native-kv-programme.v1',
                status='COMPONENT_TEST_NOT_PRODUCTION_INSTALLABLE' if component_test else 'SOURCE_AND_PHYSICAL_PROFILE_BOUND_RECEIVER_WITNESS_REQUIRED',
                stage=stage, segment=0, native_pc=11, word_order=['K_low','K_high','V_low','V_high'],
                source_kv_pcs=[3,8,10],
                source_program_sha256=hashlib.sha256(program).hexdigest(), profile_sha256=hashlib.sha256(json.dumps(profile,sort_keys=True).encode()).hexdigest(),
                word_cycles=cycles, stop_cycle=stop, writes=writes,
                root_fields={'epoch':16,'token':18,'position':13,'generation':2},
                tag_fields={'epoch':[58,43],'stage':[42,37],'token':[36,19],'position':[18,6],'segment':[5,0]},
                implementation_source_sha256=dict(profile['source_sha256']),
                source_plan_sha256=hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest(),
                expectation_inputs=['compiled_word_slot','compiled_word_index','compiled_identity','compiled_generation'],
                unsupported=['controller command/refresh/reservations','HBM front blk_go','ring return slots','full-stage timing and token performance'],
                production_qualified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('program','descriptors','plan','profile','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--stage',type=int,required=True)
    parser.add_argument('--component-test',action='store_true')
    a=parser.parse_args()
    try:
        result=compile_programme(a.program.read_bytes(),a.descriptors.read_bytes(),json.loads(a.plan.read_text()),json.loads(a.profile.read_text()),a.stage,component_test=a.component_test)
        code=0
    except MissingPhysicalProfile as e:
        result=dict(status='REFUSED_MISSING_PHYSICAL_PROFILE',missing_fields=e.missing_fields);code=2
    except (ScheduleError,KeyError,ValueError) as e:
        result=dict(status='REFUSED_INVALID_SOURCE_OR_PROFILE',error=str(e));code=2
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status']);return code

if __name__=='__main__':sys.exit(main())
