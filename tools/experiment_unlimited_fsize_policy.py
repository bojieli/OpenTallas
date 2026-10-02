#!/usr/bin/env python3
"""Future experiment launch policy: unlimited files, explicit aggregate budgets.
Additive helper only. Historical/live runners are never edited or restarted.
"""
import resource

INFINITY_STRINGS={'infinity','unlimited','-1','18446744073709551615'}


def is_infinity(value):
    return isinstance(value,str) and value.strip().lower() in INFINITY_STRINGS


def systemd_properties(properties):
    """Copy future properties, changing only FSIZE to unlimited soft/hard."""
    out=dict(properties)
    out['LimitFSIZE']='infinity'
    return out


def check_service_and_process(service, process_limits=None):
    """Call within newly launched bounded child before compiler/simulator exec."""
    if not is_infinity(service.get('LimitFSIZE')) or not is_infinity(service.get('LimitFSIZESoft')):
        raise ValueError('future service must set unlimited soft and hard FSIZE')
    limits=resource.getrlimit(resource.RLIMIT_FSIZE) if process_limits is None else process_limits
    if tuple(limits)!=(resource.RLIM_INFINITY,resource.RLIM_INFINITY):
        raise ValueError('inherited finite process FSIZE; refuse before build, do not change live job')
    return {'service_soft':service['LimitFSIZESoft'],'service_hard':service['LimitFSIZE'],
            'kernel_soft':limits[0],'kernel_hard':limits[1],'file_size_limit':'unlimited'}


def check_exec_argv(argv):
    """Catch explicit finite wrappers; opaque shell payload requires review."""
    def unlimited_pair(value):
        parts=value.split(':')
        return len(parts) in (1,2) and all(is_infinity(x) for x in parts)
    for i,arg in enumerate(argv):
        if arg.startswith('--fsize=') or arg.startswith('fsize='):
            if not unlimited_pair(arg.split('=',1)[1]):
                raise ValueError('finite fsize wrapper')
        if arg=='--fsize':
            if i+1>=len(argv) or not unlimited_pair(argv[i+1]):
                raise ValueError('finite or unspecified fsize wrapper')
        if arg=='-f' and i and argv[0].split('/')[-1]=='ulimit':
            if i+1>=len(argv) or not is_infinity(argv[i+1]):
                raise ValueError('finite shell per-file limit')
        if 'LimitFSIZE=' in arg:
            value=arg.split('LimitFSIZE=',1)[1]
            if not is_infinity(value):raise ValueError('finite systemd FSIZE in argv')
    return True


def aggregate_disk_budget(workdir_budget_bytes, disk_free_bytes, live_reserve_bytes,
                          sampled_bytes, accounted_existing_bytes=0):
    """Sampled aggregate accounting, explicitly not a hard storage quota."""
    values=(workdir_budget_bytes,disk_free_bytes,live_reserve_bytes,sampled_bytes,accounted_existing_bytes)
    if any(type(x) is not int or x<0 for x in values) or workdir_budget_bytes==0:
        raise ValueError('explicit positive aggregate workdir budget and nonnegative samples required')
    if accounted_existing_bytes>workdir_budget_bytes:raise ValueError('already accounted aggregate budget exceeded')
    if sampled_bytes>workdir_budget_bytes:raise ValueError('aggregate workdir budget exceeded')
    remaining=max(0,workdir_budget_bytes-accounted_existing_bytes)
    if disk_free_bytes<remaining+live_reserve_bytes:raise ValueError('aggregate disk/headroom insufficient')
    return {'budget_bytes':workdir_budget_bytes,'sampled_bytes':sampled_bytes,
      'live_reserve_bytes':live_reserve_bytes,'enforcement':'sampled aggregate accounting; overshoot possible',
      'per_file_cap':None,'kernel_fsize':'unlimited'}
