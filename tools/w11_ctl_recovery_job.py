#!/usr/bin/env python3
"""Pinned W11 full-size characterization; heavy work stays on the worker."""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--expect-commit', required=True)
    ap.add_argument('--synth-only', action='store_true')
    a = ap.parse_args()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    assert head == a.expect_commit
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    out = ROOT / 'results/physical_abi3/asap7/chip/w11_attn_eng_ctl' / ('endpoint_' + head[:8])
    work = Path('/home/ubuntu') / ('w11ctl_endpoint_' + head[:8]) / 'work'
    assert not work.exists() and not out.exists(), 'Never reuse an attempt or duplicate a live job'
    out.mkdir(parents=True)
    cmd = [sys.executable, str(ROOT / 'tools/run_abi3_physical.py'),
           '--view', 'asap7', '--top', 'ot_v41_attn_eng_ctl_phys',
           '--source', 'rtl/chip/physical/ot_v41_attn_eng_ctl_endpoint_phys.sv',
           '--source', 'rtl/hdc/v41x/ot_hdc_v41x_attn_ctl_phys.sv',
           '--clock-period-ns', '0.833', '--clock-uncertainty-ns', '0.06',
           '--clock-uncertainty-hold-ns', '0.025', '--orfs-corner', 'WC',
           '--hold-corners', 'WC,BC', '--io-delay-fraction', '0', '--false-path-from', 'rst_n',
           '--slew-margin-percent', '40', '--hold-margin-ns', '0.01',
           '--routing-layers', 'M2', 'M5', '--max-transition-ns', '0.32',
           '--purpose', 'characterization', '--core-utilization', '40', '--place-density', '0.6',
           '--orfs-var', 'ADDER_MAP_FILE=', '--preserve-w11-controller-endpoints',
           '--pnr-stop-after', 'finish', '--stages', 'synth' if a.synth_only else 'synth,pnr',
           '--step-tcl', 'PRE_CTS=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
           '--step-tcl', 'PRE_GLOBAL_ROUTE=physical/abi3/v41x_karb_repair_buffer_cap.tcl',
           '--keep-workdir', str(work), '--output', str(out / 'physical.json')]
    for k, v in dict(BREG=1, D=512, NSTAGE=2, PHYS=1, REPL=2).items():
        cmd += ['--param', f'{k}={v}']
    (out / 'launch.json').write_text(json.dumps(dict(source_commit=head, command=cmd,
        worker=os.uname().nodename, pid=os.getpid(), workdir=str(work),
        boundary='Physical stubs only; arithmetic exactness is a separate real-engine gate. '
                 'SS setup and FF hold are pending until terminal records pass.'), indent=2) + '\n')
    env = dict(os.environ, OT_SYNTH_TIMEOUT_SECONDS='43200', OT_FLOW_TIMEOUT_SECONDS='86400')
    with (out / 'driver.log').open('w') as log:
        rc = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT).returncode
    for name in ['stat.txt', 'synth.ys', 'w11_endpoint_guard.json']:
        if (work / name).is_file():
            shutil.copyfile(work / name, out / name)
    (out / 'exit.json').write_text(json.dumps(dict(returncode=rc)) + '\n')
    return rc


if __name__ == '__main__':
    sys.exit(main())
