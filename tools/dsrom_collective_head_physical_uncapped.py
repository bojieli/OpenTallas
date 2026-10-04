#!/usr/bin/env python3
"""Use the existing physical flow without wall/resource ceilings; no RTL changes.

Launch only after the selected Erdos source's actual functional and serial
context measurements are qualified. NUM_CORES is the owner's16..24 policy.
All corner/uncertainty/IO/route parameters remain the original driver's CLI.
"""
import os
import subprocess
import run_abi3_physical as physical


def uncapped_run(cmd, *, cwd=None, timeout=None):
    # The old driver's timeout argument is deliberately not passed. The tools
    # still write their own incremental ORFS checkpoints/objects in the job dir.
    return subprocess.run(cmd, cwd=str(cwd or physical.ROOT),
                          capture_output=True, text=True, check=False)


def main():
    cores=int(os.environ.get('OT_ORFS_NUM_CORES','16'))
    if not 16 <= cores <= 24:
        raise SystemExit('Owner ORFS policy requires16..24 cores')
    os.environ['OT_ORFS_NUM_CORES']=str(cores)
    physical.run=uncapped_run
    return physical.main()


if __name__=='__main__':raise SystemExit(main())
