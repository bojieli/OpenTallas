#!/usr/bin/env python3
"""Full-width minimum credit mechanism sweep; no whole endpoint simulation."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
TOP = 'tb_ha2_truecredit'
FILES = ['rtl/hbm_accel/ha2_ar/' + n + '.sv' for n in (
    'ot_ha2_prims', 'ot_ha2_parent_quiet_prims', 'ot_ha2_truecredit', TOP)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    pins = {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    cases = [(f'f{f}_r{r}', f, r, 0, 192, 16)
             for f,r in itertools.product([0,1,7,64], repeat=2)]
    cases += [('sequence_wrap', 7, 64, 0, 640, 8),
              ('ignore_reservations', 7, 7, 1, 192, 16),
              ('corrupt_retire_id', 7, 7, 2, 192, 16),
              ('corrupt_forward_id', 7, 7, 3, 192, 16)]
    checks = {}
    for name, fwd, ret, mutant, rows, tag in cases:
        binary = out/(name+'.vvp')
        params = dict(FWD=fwd, RET=ret, MUTANT=mutant, ROWS=rows, TAGW=tag)
        cmd = ['iverilog','-g2012','-s',TOP,
               *[f'-P{TOP}.{k}={v}' for k,v in params.items()],
               '-o',str(binary),*FILES]
        build = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        (out/(name+'.compile.log')).write_text(build.stdout+build.stderr)
        if build.returncode:
            raise RuntimeError(name+': compile failure is not a negative verdict')
        run = subprocess.run(['vvp',str(binary)],cwd=ROOT,capture_output=True,text=True)
        text = run.stdout+run.stderr
        (out/(name+'.log')).write_text(text)
        good = (run.returncode != 0 and 'TRUECREDIT_FAULT' in text) if mutant else (
            run.returncode == 0 and 'PASS_TRUECREDIT ' in text)
        checks[name] = dict(parameters=params, returncode=run.returncode,
                            passed=good, output=text)
        print(name, 'PASS' if good else 'FAIL', flush=True)
    assert pins == {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in FILES}
    record = dict(passed=all(c['passed'] for c in checks.values()), checks=checks,
        source_sha256=pins,
        scope='Full-width two-injector mechanism and negative controls; synchronized clean reset. Not full numerical endpoint qualification, SRAM protection, mapped area, physical closure or actual latency composition.')
    (out/'terminal.json').write_text(json.dumps(record,indent=2)+'\n')
    return 0 if record['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
