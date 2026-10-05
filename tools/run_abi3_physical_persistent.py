#!/usr/bin/env python3
"""Launch admitted physical work without wall caps or temporary-directory cleanup.

This additive adapter leaves the source-pinned driver, clocks, macros, mapping
policy and verdicts unchanged. It does not admit hardware or reclaim any files.
Every invocation requires a fresh persistent directory and receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def remove_inherited_runtime_caps():
    limits = {}
    for name in ('RLIMIT_CPU', 'RLIMIT_AS', 'RLIMIT_FSIZE'):
        kind = getattr(resource, name)
        soft, hard = resource.getrlimit(kind)
        if hard != resource.RLIM_INFINITY:
            raise ValueError('finite inherited hard limit: ' + name)
        if soft != hard:
            resource.setrlimit(kind, (hard, hard))
        limits[name] = 'unlimited'
    return limits


def launch(driver, driver_args, *, workdir, receipt):
    workdir, receipt = Path(workdir), Path(receipt)
    if not workdir.is_absolute() or not receipt.is_absolute():
        raise ValueError('absolute persistent workdir and receipt required')
    if any(a == '--keep-workdir' or a.startswith('--keep-workdir=') for a in driver_args):
        raise ValueError('workdir is owned by this launcher')
    if workdir.exists() or workdir.is_symlink() or receipt.exists() or receipt.is_symlink():
        raise ValueError('fresh workdir and receipt required; preserve existing jobs')
    limits = remove_inherited_runtime_caps()
    # Exclusive creation prevents accidental reuse, including an orphaned run.
    workdir.mkdir(parents=False, exist_ok=False)
    with receipt.open('x') as handle:
        record = dict(schema='ABI3_PERSISTENT_UNCAPPED_LAUNCH_V1', status='RUNNING',
            pid=os.getpid(), process_start_ticks=Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19],
            started_ns=time.time_ns(), workdir=str(workdir), driver_args=driver_args,
            wrapper_sha256=digest(__file__), driver_sha256=digest(driver.__file__),
            runtime_limits=limits, subprocess_wall_timeout=None,
            persistent_workdir=True, cleanup_performed=False,
            hardware_admitted_by_launcher=False)
        def save():
            handle.seek(0); handle.truncate()
            json.dump(record, handle, sort_keys=True, indent=2)
            handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
        save()
        original_run = driver.run
        original_flow, original_synth = driver.flow_timeout_seconds, driver.synth_timeout_seconds
        def uncapped_run(*args, **kwargs):
            kwargs['timeout'] = None
            return original_run(*args, **kwargs)
        driver.run = uncapped_run
        driver.flow_timeout_seconds = lambda: None
        driver.synth_timeout_seconds = lambda: None
        try:
            code = driver.main([*driver_args, '--keep-workdir', str(workdir)])
            record.update(status='DRIVER_RETURNED', exit_code=code)
            return code
        except BaseException as exc:
            record.update(status='EXCEPTION_WORKDIR_PRESERVED',
                exception_type=type(exc).__name__, exception_message=str(exc))
            raise
        finally:
            driver.run = original_run
            driver.flow_timeout_seconds, driver.synth_timeout_seconds = original_flow, original_synth
            record.update(ended_ns=time.time_ns(), driver_sha256_after=digest(driver.__file__))
            save()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--persistent-workdir', type=Path, required=True)
    parser.add_argument('--launch-receipt', type=Path, required=True)
    args, forwarded = parser.parse_known_args(argv)
    import run_abi3_physical as driver
    return launch(driver, forwarded, workdir=args.persistent_workdir, receipt=args.launch_receipt)


if __name__ == '__main__':
    sys.exit(main())
