#!/usr/bin/env python3
"""Small full-width/depth exact gate for the SM request FIFO candidate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['rtl/hbm_accel/sm/ot_hbm_accel_smh.sv',
           'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
           'rtl/hbm_accel/sm/ot_hbm_accel_smh_csnk_ne.sv',
           'rtl/test/tb_hbm_smh_csnk_ne.sv',
           'rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    cases = {}
    for name in ('positive', 'mutant_last_pop'):
        paths = [ROOT / s for s in SOURCES]
        if name != 'positive':
            text = paths[2].read_text()
            assert text.count('nonempty <= (cnt != 1);') == 1
            mutant = a.out / 'mutant.sv'
            mutant.write_text(text.replace('nonempty <= (cnt != 1);', 'nonempty <= (cnt != 2);'))
            paths[2] = mutant
        exe = a.out / (name + '.vvp')
        cmd = ['iverilog', '-g2012', '-s', 'tb_hbm_smh_csnk_ne', '-o', str(exe)] + list(map(str, paths))
        build = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
        (a.out / (name + '_build.log')).write_text(build.stdout + build.stderr)
        if build.returncode:
            raise RuntimeError(build.stderr)
        run = subprocess.run(['vvp', str(exe)], cwd=ROOT, text=True, capture_output=True)
        (a.out / (name + '.log')).write_text(run.stdout + run.stderr)
        passed = run.returncode == 0 and 'PASS cycles=' in run.stdout if name == 'positive' else (
            run.returncode != 0 and ('equivalence failure' in run.stdout or 'cached occupancy invariant failure' in run.stdout))
        cases[name] = dict(returncode=run.returncode, gate_pass=passed, output=run.stdout + run.stderr, compile=cmd)
    record = dict(schema='opentallas.hbm.smh.csnk_ne_exact.v1',
        status='pass' if all(c['gate_pass'] for c in cases.values()) else 'fail',
        scope='one full W42 depth9 sink, actual credit source and pipeline stages; cycle equivalence plus independent FIFO data/order scoreboard',
        source_sha256={s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES},
        tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        cases=cases, physical_closure=False, state_protection_qualified=False)
    (a.out/'gate.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(record, indent=2))
    return 0 if record['status']=='pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
