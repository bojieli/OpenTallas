#!/usr/bin/env python3
"""Recover a failed R5a CTS path from its legal full-shape placement, without rerouting.

Run through unchanged admit.sh 120 on EPYC2. Output must be a new NVMe directory.
Copies the old ORFS work directory; original failures and objects remain untouched.
This intentionally exits before timing repair and never creates a signoff verdict.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prior-orfs', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    if os.getloadavg()[0] >= 128:
        raise SystemExit('EPYC2 load >=128 after admission: no execution')
    prior = args.prior_orfs.resolve()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    base = next((prior / 'results/asap7').glob('*/base'))
    inputs = [prior / 'config.mk', base / '3_place.odb', base / '3_place.sdc']
    # Pin evaluator helpers alongside the exact current physical driver, even though
    # this diagnostic stops before extraction and never uses a finish evaluator.
    helpers = [ROOT / p for p in (
        'physical/hbm_accel/r5a_cts_diagnose.py',
        'physical/hbm_accel/r5a_cts_capture.tcl',
        'tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py')]
    macro = ROOT / 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2'
    helpers += sorted(macro.glob('*.lib')) + sorted(macro.glob('*.lef'))
    image = subprocess.check_output(['docker', 'image', 'inspect', 'openroad/orfs:latest',
                                     '--format', '{{.Id}}'], text=True).strip()
    receipt = dict(source_commit=args.source_commit, prior_orfs=str(prior),
                   load_after_guard=os.getloadavg(), diagnostic_only=True,
                   constraints_changed=False, cores=16, image=image,
                   sha256={str(p): sha(p) for p in inputs + helpers})
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    work = out / 'orfs'
    subprocess.run(['cp', '-a', '--reflink=auto', str(prior), str(work)], check=True)
    command = ['docker', 'run', '--rm', '-v', f'{ROOT}:/src:ro',
               '-v', f'{work}:/work', '-w', '/OpenROAD-flow-scripts/flow', image,
               'bash', '-lc',
               'source /OpenROAD-flow-scripts/env.sh; '
               'make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base '
               'NUM_CORES=16 PRE_CTS_TCL=/src/physical/hbm_accel/r5a_cts_capture.tcl '
               'CTS_SNAPSHOTS=1 do-4_1_cts']
    receipt['command'] = command
    receipt['load_at_execution'] = os.getloadavg()
    if os.getloadavg()[0] >= 128:
        raise SystemExit('EPYC2 load >=128 at execution: preserved copy, no CTS')
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (out / 'run.log').open('w') as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    (out / 'exit').write_text(str(result.returncode) + '\n')
    capture = work / base.relative_to(prior) / 'r5a_pre_repair.odb'
    if result.returncode or not capture.exists():
        raise SystemExit('CTS diagnostic failed; original evidence preserved')
    print('R5A_CTS_CAPTURE_COMPLETE diagnostic only:', capture)


if __name__ == '__main__':
    main()
