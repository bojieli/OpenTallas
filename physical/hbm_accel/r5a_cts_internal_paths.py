#!/usr/bin/env python3
"""Time internal paths in the saved R5a CTS snapshot; no CTS/route or constraints change."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/w18'))
import corner_sta


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--orfs', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--source-commit', required=True)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    image = subprocess.check_output(['docker', 'image', 'inspect', 'openroad/orfs:latest',
                                     '--format', '{{.Id}}'], text=True).strip()
    base = next((a.orfs / 'results/asap7').glob('*/base'))
    macro = 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2'
    receipt = {'source_commit': a.source_commit, 'image': image, 'diagnostic_only': True,
               'constraints_changed': False, 'orfs': str(a.orfs),
               'helpers_sha256': {p: corner_sta.sha(ROOT / p) for p in (
                   'physical/hbm_accel/r5a_cts_internal_paths.py', 'tools/w18/corner_sta.py',
                   'tools/run_abi3_physical.py', 'tools/orfs_allcorner_spef.py')},
               'snapshot_sha256': {p.name: corner_sta.sha(p) for p in (
                   base / 'r5a_pre_repair.odb', base / 'r5a_pre_repair.sdc')}}
    for corner, check in (('ss', 'max'), ('ff', 'min')):
        if os.getloadavg()[0] >= 128:
            raise SystemExit('EPYC2 load >=128 after guard/at execution')
        tcl = corner_sta.script(corner, '/work/' + str(base.relative_to(a.orfs)), [macro])
        # Preserve the saved SDC and corner-specific macro arcs; only the checkpoint
        # and parasitic source differ from the routed signoff evaluator.
        tcl = tcl[:tcl.index('puts "OT_CORNER')]
        tcl = tcl.replace('6_final.odb', 'r5a_pre_repair.odb').replace('6_final.sdc', 'r5a_pre_repair.sdc')
        tcl = '\n'.join(line for line in tcl.splitlines() if not line.startswith('read_spef'))
        tcl += '\nsource /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl\nestimate_parasitics -placement\n'
        tcl += (f'report_checks -path_delay {check} -from [all_registers -clock_pins] '
                '-to [all_registers -data_pins] -group_path_count 5 -format full_clock_expanded '
                '-fields {slew cap fanout input net} -digits 4\nexit\n')
        script = a.out / f'{corner}.tcl'
        script.write_text(tcl)
        cmd = ['docker', 'run', '--rm', '-v', f'{ROOT}:/src:ro', '-v', f'{a.orfs}:/work:ro',
               '-v', f'{a.out}:/diag', image, 'bash', '-lc',
               f'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads 16 -no_init -exit /diag/{corner}.tcl']
        receipt[corner] = {'command': cmd, 'load_at_execution': os.getloadavg()}
        with (a.out / f'{corner}.log').open('w') as log:
            result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
        receipt[corner]['exit'] = result.returncode
        (a.out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
