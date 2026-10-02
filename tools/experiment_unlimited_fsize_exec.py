#!/usr/bin/env python3
"""Future native/container job entry; check unlimited FSIZE before exec only."""
import os,resource,sys
from experiment_unlimited_fsize_policy import check_exec_argv

def prepare_argv(argv,limits=None):
    if not argv or argv[0]!='--' or len(argv)<2:raise ValueError('explicit -- command required')
    limits=resource.getrlimit(resource.RLIMIT_FSIZE) if limits is None else limits
    if tuple(limits)!=(resource.RLIM_INFINITY,resource.RLIM_INFINITY):raise ValueError('inherited file-size limit must be unlimited')
    check_exec_argv(argv[1:])
    return argv[1:]
if __name__=='__main__':
    try:command=prepare_argv(sys.argv[1:])
    except ValueError as e:raise SystemExit(str(e))
    os.execvp(command[0],command)
