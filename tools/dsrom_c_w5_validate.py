#!/usr/bin/env python3
"""Small W5 replay with immutable output directory and input hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/uarch/dsrom_c_w5_pg_20261003'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    out = a.out.resolve()
    out.mkdir(parents=True, exist_ok=False)  # completed failures are never overwritten
    paths = ['rtl/v41rom/ot_dsrom_c_w5_pg.sv', 'rtl/test/tb_dsrom_c_w5_pg.sv',
             'tools/dsrom_c_w5_pg.py', 'tools/dsrom_c_w5_validate.py', 'tools/uarch_model.py',
             'tests/test_dsrom_c_w5_pg.py', 'configs/hardware/dsrom_c_w5_pg.json',
             'results/uarch/dsrom_return_storage_hbm_20261003/model.json',
             'results/uarch/dsrom_c_w5_pg_20261003/synth_generic_final/netlist.json']
    paths += [str(f.relative_to(ROOT)) for f in sorted((BASE / 'inputs/liberty').iterdir())]
    pins = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in paths}
    (out / 'inputs.json').write_text(json.dumps(pins, indent=2, sort_keys=True) + '\n')
    commands = [
        [sys.executable, 'tests/test_dsrom_c_w5_pg.py', '-v'],
        ['iverilog', '-g2012', '-s', 'tb_dsrom_c_w5_pg', '-o', str(out / 'pg.vvp'),
         'rtl/v41rom/ot_dsrom_c_w5_pg.sv', 'rtl/test/tb_dsrom_c_w5_pg.sv'],
        ['vvp', str(out / 'pg.vvp')],
        [sys.executable, 'tools/dsrom_c_w5_pg.py', '--contract', 'configs/hardware/dsrom_c_w5_pg.json',
         '--liberty', *[str(f.relative_to(ROOT)) for f in sorted((BASE / 'inputs/liberty').iterdir())],
         '--netlist', 'results/uarch/dsrom_c_w5_pg_20261003/synth_generic_final/netlist.json',
         '--out', str(out / 'model')]]
    rows = []
    passed = True
    for idx, cmd in enumerate(commands):
        run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (out / f'command{idx}.log').write_text(run.stdout + run.stderr)
        rows.append({'argv': cmd, 'returncode': run.returncode})
        if run.returncode:
            passed = False
            break
    after = {f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in paths}
    passed = passed and pins == after
    if passed:
        transcript = (out / 'command2.log').read_text()
        passed = ('added_token_cycles=0 payload_exact=1' in transcript and
                  'late_wake added_token_cycles=7' in transcript and 'analog_guarantee=0' in transcript)
    receipt = {'scope': 'DIRECTED_DIGITAL_FIXTURE_AND_LIBERTY_SCREEN', 'host': socket.gethostname(),
               'passed': passed, 'inputs_unchanged': pins == after, 'commands': rows,
               'max_child_RSS_MiB_measured': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 1024,
               'scheduled_added_cycles_measured': 0 if passed else None,
               'late_wake_added_cycles_measured': 7 if passed else None,
               'production_calendar_qualified': False, 'analog_guarantee': False}
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
