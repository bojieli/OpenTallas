#!/usr/bin/env python3
"""Run the prepared full36 token after the parallel32 gate and host admission.

A failed build or simulation stops immediately; completed artifacts are retained.
64 GiB build reservation covers the measured 32.53 GiB predecessor build plus
expanded raw landing lanes. Runtime reserves 16 GiB against measured 13.35 GiB.
These are admission reservations, never per-process limits.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def fit(workers):
    def ticks():
        return list(map(int, Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
    a = ticks()
    time.sleep(1)
    b = ticks()
    d = [y-x for x, y in zip(a, b)]
    idle = os.cpu_count() * (d[3]+d[4]) / sum(d[:8])
    return os.getloadavg()[0]+workers <= 110 and idle >= workers


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--mechanism-terminal', type=Path, required=True)
    p.add_argument('--workers', type=int, default=16)
    p.add_argument('--admitted-stage', choices=['build', 'runtime'])
    a = p.parse_args()
    if a.admitted_stage:
        if not fit(a.workers):
            return 75  # capacity changed in the guard; no build/run started
        return subprocess.call([sys.executable, str(a.source/'tools/qwen_rom_combined_p0_20261005/run_full.py'),
                                '--output', str(a.output), '--source', str(a.source),
                                '--stage', a.admitted_stage, '--workers', str(a.workers)])
    gate = json.loads(a.mechanism_terminal.read_text())
    if gate.get('status') != 'PASS_RELEASED_PARALLEL32_COMPONENT' or gate.get('exit') != 0:
        raise ValueError('actual parallel32 mechanism must pass before full36 build')
    prepared = json.loads((a.output/'prepared.json').read_text())
    if not prepared.get('parallel_transport'):
        raise ValueError('parallel full36 build required')
    # Same actual production RTL that passed the remote component, even when
    # the two jobs use different absolute snapshot roots on different hosts.
    import hashlib
    for name, digest in gate['source_sha256'].items():
        if '/rtl/' not in name:
            continue
        local = a.source/'rtl'/name.split('/rtl/', 1)[1]
        if not local.is_file() or hashlib.sha256(local.read_bytes()).hexdigest() != digest:
            raise ValueError('parallel gate source mismatch: '+str(local))
    for stage, gib in [('build', 64), ('runtime', 16)]:
        while True:
            while not fit(a.workers):
                time.sleep(30)
            cmd = ['/srv/opentallas-scratch/admit.sh', str(gib), '--', sys.executable,
                   str(Path(__file__).resolve()), '--output', str(a.output),
                   '--source', str(a.source), '--mechanism-terminal', str(a.mechanism_terminal),
                   '--workers', str(a.workers), '--admitted-stage', stage]
            with (a.output/(stage+'_admission.log')).open('a') as log:
                rc = subprocess.call(cmd, stdout=log, stderr=subprocess.STDOUT)
            if rc == 75:
                continue
            if rc:
                return rc
            break
    return subprocess.call([sys.executable, str(a.source/'tools/qwen_rom_combined_p0_20261005/check_fullwidth.py'),
                            '--output', str(a.output)])


if __name__ == '__main__':
    raise SystemExit(main())
