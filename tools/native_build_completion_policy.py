"""Opt-in validation for future native builds; no process or limit mutation.

Native compilation runs until completion or error. Resource failures remain
errors and incremental objects must be retained. Simulation limits are separate.
"""
import resource
import os
from experiment_unlimited_fsize_policy import (
    aggregate_disk_budget, check_exec_argv, check_service_and_process, is_infinity,
)


def validate_model(model):
    if model.get('scope') != 'native_build':
        raise ValueError('native build scope required')
    if 'elapsed_time_limit' not in model or model['elapsed_time_limit'] is not None:
        raise ValueError('native elapsed time limit must explicitly be null')
    if model.get('file_size_limit') != 'unlimited':
        raise ValueError('unlimited FSIZE required')
    if 'per_process_address_space_limit' not in model or model['per_process_address_space_limit'] is not None:
        raise ValueError('no guessed per-process address-space cap')
    for key in ['CXX_AS', 'link_AS']:
        if model.get(key) is not None:
            raise ValueError('historical AS cap cannot carry into future continuation')
    evidence = model.get('admission_evidence', {})
    for key in ['host_snapshot_sha256', 'source_inventory_sha256',
                'capacity_reservation_basis']:
        if not evidence.get(key):
            raise ValueError('measured capacity and real inventory evidence required: ' + key)
    if model.get('retain_incremental_objects') is not True:
        raise ValueError('retain incremental objects on completion and failure')
    for key in ['memory_bytes', 'pids', 'workers', 'output_bytes',
                'host_disk_reserve', 'host_memory_reserve']:
        if type(model.get(key)) is not int or model[key] <= 0:
            raise ValueError('explicit positive resource bound required: ' + key)
    cpus = model.get('affinity')
    if not isinstance(cpus, list) or not cpus or any(type(c) is not int or c < 0 for c in cpus):
        raise ValueError('explicit CPU affinity required')
    if len(set(cpus)) != len(cpus) or model['workers'] > len(cpus):
        raise ValueError('workers exceed distinct affinity CPUs')
    if model.get('swap_bytes') != 0:
        raise ValueError('swap0 required')
    return True


def future_service_properties(model):
    validate_model(model)
    return {'RuntimeMaxSec': 'infinity', 'LimitFSIZE': 'infinity', 'LimitAS': 'infinity',
            'MemoryMax': str(model['memory_bytes']), 'MemorySwapMax': '0',
            'TasksMax': str(model['pids']),
            'CPUAffinity': ' '.join(map(str, model['affinity']))}


def validate_execution(service, model, *, process_fsize=None, process_as=None,
                       process_affinity=None, subprocess_timeout=None):
    validate_model(model)
    if not is_infinity(service.get('RuntimeMaxUSec')) or subprocess_timeout is not None:
        raise ValueError('native build wall deadline prohibited')
    if not is_infinity(service.get('LimitAS')) or not is_infinity(service.get('LimitASSoft')):
        raise ValueError('finite native service address-space cap')
    limits = resource.getrlimit(resource.RLIMIT_AS) if process_as is None else process_as
    if tuple(limits) != (resource.RLIM_INFINITY, resource.RLIM_INFINITY):
        raise ValueError('inherited finite native address-space cap')
    cpus = set()
    for token in service.get('CPUAffinity', '').split():
        parts = token.split('-')
        if len(parts) == 1:
            cpus.add(int(parts[0]))
        elif len(parts) == 2:
            lo, hi = map(int, parts)
            if hi < lo:
                raise ValueError('invalid CPU range')
            cpus.update(range(lo, hi + 1))
        else:
            raise ValueError('invalid CPU affinity')
    actual = os.sched_getaffinity(0) if process_affinity is None else process_affinity
    if cpus != set(model['affinity']) or set(actual) != cpus:
        raise ValueError('native CPU affinity mismatch')
    for key, expected in [('MemoryMax', model['memory_bytes']), ('MemorySwapMax', 0),
                          ('TasksMax', model['pids'])]:
        if service.get(key) != str(expected):
            raise ValueError('resource property mismatch: ' + key)
    return check_service_and_process(service, process_fsize)


def validate_native_argv(argv):
    """Explicit wrappers only; opaque shell payloads still require source review."""
    check_exec_argv(argv)
    for index, arg in enumerate(argv):
        if arg.rsplit('/', 1)[-1] in {'timeout', 'gtimeout'}:
            raise ValueError('timeout wrapper prohibited for native build')
        if argv and argv[0].rsplit('/', 1)[-1] == 'ulimit' and arg == '-v':
            if index + 1 >= len(argv) or not is_infinity(argv[index + 1]):
                raise ValueError('finite shell address-space cap')
        for key in ['RuntimeMaxSec=', 'RuntimeMaxUSec=']:
            if key in arg and not is_infinity(arg.split(key, 1)[1]):
                raise ValueError('finite native service deadline')
        for key in ['--as=', 'LimitAS=']:
            if key in arg and not all(is_infinity(v) for v in arg.split(key, 1)[1].split(':')):
                raise ValueError('finite native address-space wrapper')
        if arg == '--as' and (index + 1 >= len(argv) or
                               not all(is_infinity(v) for v in argv[index + 1].split(':'))):
            raise ValueError('finite or unspecified address-space wrapper')
    return True


def validate_admission_headroom(model, *, available_memory, free_disk, sampled_output,
                                accounted_existing_output=0):
    """Pre-build admission only; do not subtract peak reservation again during execution."""
    validate_model(model)
    if available_memory < model['memory_bytes'] + model['host_memory_reserve']:
        raise ValueError('aggregate memory/headroom insufficient')
    return aggregate_disk_budget(model['output_bytes'], free_disk,
                                 model['host_disk_reserve'], sampled_output,
                                 accounted_existing_output)
