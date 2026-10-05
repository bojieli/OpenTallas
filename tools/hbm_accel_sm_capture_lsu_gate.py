#!/usr/bin/env python3
"""One SM capture/LSU component, no host image or token replay.

Run on an admitted remote host. --rtl-root selects the owner's corrected tree;
the bench always comes from this script's tree. Exit nonzero on any mismatch.
"""
import argparse
import ast
import os
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parents[1]
TOP = 'tb_hbm_accel_sm_capture_lsu'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rtl-root', type=Path, required=True)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--jobs', type=int, default=16, choices=range(1, 17))
    p.add_argument('--threads', type=int, default=8, choices=range(1, 25))
    a = p.parse_args()
    root = a.rtl_root.resolve()
    work = a.work.resolve()
    work.mkdir(parents=True, exist_ok=False)
    # Read the existing dependency literal, without importing its model/golden.
    tree = ast.parse((root / 'tools/gpu_sys/run_system.py').read_text())
    deps = next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id == 'DEP_SRC' for t in n.targets))
    src = ['rtl/gpu_sys/ot_gpu_simt_lane.sv',
           'rtl/gpu_sys/ot_gpu_simt_divlane.sv',
           'rtl/gpu_sys/ot_gpu_bd_line.sv',
           'rtl/hbm_accel/collective/ot_hbm_accel_simt_sm.sv'] + deps
    verilator = Path(os.environ.get('OPENTALLAS_TOOL_ROOT',
                     str(Path.home() / '.local/opentallas-tools'))) / 'verilator-5.050/bin/verilator'
    cmd = [str(verilator), '--binary', '--timing', '-O2', '-j', str(a.jobs),
           '--threads', str(a.threads), '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '-Wno-WIDTH', '--x-assign', '0', '--x-initial', '0',
           '--top-module', TOP, '--Mdir', str(work / 'obj')]
    cmd += [str(root / s) for s in dict.fromkeys(src)]
    cmd += [str(HERE / 'rtl/test/hbm_accel' / (TOP + '.sv'))]
    with (work / 'build.log').open('w') as log:
        rc = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT).returncode
    if rc:
        return rc
    with (work / 'run.log').open('w') as log:
        rc = subprocess.run([str(work / 'obj' / ('V' + TOP))], cwd=work,
                            stdout=log, stderr=subprocess.STDOUT).returncode
    text = (work / 'run.log').read_text()
    print(text, end='')
    return rc if rc else (0 if 'PASS sm_capture_lsu ' in text else 1)


if __name__ == '__main__':
    raise SystemExit(main())
