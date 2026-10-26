#!/usr/bin/env python3
"""Run only the HC event-sequencer mapped-SRAM component gate and bad-magic negative control.
The full HC engine arithmetic, throughput and physical integration remain separate gates.
"""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    a = ap.parse_args()
    a.run.mkdir(parents=True, exist_ok=True)
    obj = (a.run / 'seq.vvp').resolve()
    sources = ['rtl/test/tb_hbm_hc_eng_seq_static.sv',
               'rtl/hbm_accel/generic/peers/static_hc/ot_hbm_hc_eng_seq_static.sv',
               'physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
    subprocess.run(['iverilog', '-g2012', '-s', 'tb_hbm_hc_eng_seq_static', '-o', str(obj), *sources],
                   cwd=ROOT, check=True)
    runs = []
    for mutant in (0, 1):
        cmd = ['vvp', str(obj), f'+MUT={mutant}']
        p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        (a.run / f'mut{mutant}.log').write_text(p.stdout + p.stderr)
        valid = (p.returncode == 0 and 'HC_ENG_SEQ PASS' in p.stdout) if not mutant else (
            p.returncode != 0 and 'SEQ FAIL fault=1' in p.stdout)
        runs.append(dict(mutant=mutant, rc=p.returncode, expected_outcome_observed=valid))
    report = dict(scope='HC event sequencer only; real mapped SRAM; 16 consecutive fixed-cycle events',
                  qualified_full_engine=False, passed=all(r['expected_outcome_observed'] for r in runs), runs=runs)
    (a.run / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
