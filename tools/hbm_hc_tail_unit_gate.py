#!/usr/bin/env python3
"""Tail component exactness and dropped-epsilon mutant at all seven divider phases.
Use ot-run for this build/run. This gate does not qualify the full HC engine or die.
Vector directory must contain the full-engine generator's P=1 expmix/exptail/tbl.mem.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/test/tb_hbm_hc_tail_unit_static.sv']
SOURCES += ['rtl/hbm_accel/generic/peers/static_hc/' + n + '.sv' for n in (
    'ot_hbm_hc_tail_unit_static', 'ot_hgi_hc_tail_static')]
SOURCES += ['rtl/hdc/' + n + '.sv' for n in (
    'ot_hdc_delay', 'ot_hdc_fastfp', 'ot_hdc_fastfp_lat', 'ot_hdc_fp32_add_lat',
    'ot_hdc_fp32_mul_lat', 'v41x/ot_hdc_v41x_sfu', 'ot_hdc_sfu', 'v41/ot_hdc_fdiv',
    'v41/ot_hdc_sinkhorn', 'v41/ot_hdc_sk_arith', 'v41/ot_hdc_sk_recip_rom')]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--vectors', type=Path, required=True)
    ap.add_argument('--mutants', type=int, choices=(0, 1), nargs='+', default=[0, 1])
    a = ap.parse_args()
    a.run = a.run.resolve()
    a.run.mkdir(parents=True, exist_ok=True)
    inputs = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}
    for n in ('expmix.mem', 'exptail.mem', 'tbl.mem'):
        source = (a.vectors / n).resolve()
        destination = a.run / n
        if source != destination:
            shutil.copyfile(source, destination)
        inputs[n] = hashlib.sha256(source.read_bytes()).hexdigest()
    (a.run / 'input_manifest.json').write_text(json.dumps(inputs, indent=2) + '\n')
    records = []
    for mutant in a.mutants:
        binary = a.run / f'mut{mutant}.vvp'
        cmd = ['iverilog', '-g2012', '-s', 'tb_hbm_hc_tail_unit_static',
               '-P', f'tb_hbm_hc_tail_unit_static.MUT={mutant}', '-o', str(binary), *SOURCES]
        p = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (a.run / f'build_mut{mutant}.log').write_text(p.stdout + p.stderr)
        if p.returncode:
            raise SystemExit(f'tail component build {mutant} failed: {a.run}')
        p = subprocess.run(['vvp', str(binary)], cwd=a.run, capture_output=True, text=True)
        (a.run / f'run_mut{mutant}.log').write_text(p.stdout + p.stderr)
        valid = (p.returncode == 0 and 'HC_TAIL_UNIT PASS phases=7 words=168 fixed timing' in p.stdout
                 if not mutant else p.returncode != 0 and 'TAIL FAIL bad=' in p.stdout
                 and 'TAIL CONTRACT' not in p.stdout)
        records.append(dict(mutant=mutant, rc=p.returncode, expected_outcome_observed=valid))
    result = dict(scope='Tail-unit component; real sigmoid/exp/Sinkhorn RTL; external golden mixes/table',
                  full_engine_qualified=False, phases=7, words=168, launch_to_result_cycles=496,
                  tested_mutants=a.mutants,
                  passed=all(r['expected_outcome_observed'] for r in records), runs=records)
    (a.run / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
