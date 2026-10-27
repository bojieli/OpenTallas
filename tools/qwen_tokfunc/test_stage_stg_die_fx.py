#!/usr/bin/env python3
"""stage_stg_die.sh fixture staging (TOK-QK-2 10-27): QCLM r2a ran 252/259 cases with no stgdie/fx and got NO RESULT.

The stage must stage E/stgdie/fx itself (--fx DIR, or dirname(STG_RESULT)/fx) and fail closed (exit 7, result.json FAIL)
before any build check or sim when a fixture the runlist names is missing.  No simulation: E has no build, so a
staged-OK case stops at the build check (exit 2) after the preflight passed.
"""
import json
from pathlib import Path
import subprocess
import tempfile

SCRIPT = Path(__file__).with_name('stage_stg_die.sh')
RUNLIST = ('pos L0_resid1 tree/rtl/test/qwen_dv/dv_lower_vec_bench.py --mode resid --ages pos/build/vec_ages.json'
           ' --fixture fx/L0_resid1.npz\n'
           'pos L0_qkv tree/rtl/test/qwen_dv/dv_lower_mat_bench.py --run qkv --ages pos/cal_mat/stn_ages.json'
           ' --fixture fx/L0_mat_qkv.npz\n')


def run(root, *extra, stg_fx=False):
    e = root / 'E'; (e / 'tree').mkdir(parents=True, exist_ok=True)
    stg = root / 'stg'; stg.mkdir(exist_ok=True)
    (stg / 'result.json').write_text('{}')
    if stg_fx:
        (stg / 'fx').mkdir(exist_ok=True)
        for f in ('L0_resid1.npz', 'L0_mat_qkv.npz'):
            (stg / 'fx' / f).write_bytes(b'x')
    (root / 'rl.txt').write_text(RUNLIST)
    p = subprocess.run(['bash', str(SCRIPT), str(e), str(stg / 'result.json'), str(root / 'rl.txt'), *extra],
                       capture_output=True, text=True)
    return p, e / 'stgdie'


def main():
    with tempfile.TemporaryDirectory() as d:          # 1: nothing staged -> fail closed
        p, s = run(Path(d))
        assert p.returncode == 7, (p.returncode, p.stdout, p.stderr)
        r = json.loads((s / 'result.json').read_text())
        assert r['verdict'] == 'FAIL' and r['missing'] == ['L0_mat_qkv.npz', 'L0_resid1.npz'], r
    with tempfile.TemporaryDirectory() as d:          # 2: --fx with one file missing -> fail closed, names it
        fx = Path(d) / 'fxsrc'; fx.mkdir(); (fx / 'L0_resid1.npz').write_bytes(b'x')
        p, s = run(Path(d), '--fx', str(fx))
        assert p.returncode == 7 and json.loads((s / 'result.json').read_text())['missing'] == ['L0_mat_qkv.npz'], p.stdout
        assert (s / 'fx').resolve() == fx.resolve()
    with tempfile.TemporaryDirectory() as d:          # 3: --fx complete -> staged, stops at the build check
        fx = Path(d) / 'fxsrc'; fx.mkdir()
        for f in ('L0_resid1.npz', 'L0_mat_qkv.npz'):
            (fx / f).write_bytes(b'x')
        p, s = run(Path(d), '--fx', str(fx))
        assert p.returncode == 2 and 'fixtures 2/2 staged' in p.stdout and 'need built' in p.stdout, p.stdout
        assert (s / 'fx').resolve() == fx.resolve() and not (s / 'result.json').exists()
    with tempfile.TemporaryDirectory() as d:          # 4: default = fx/ next to STG_RESULT
        p, s = run(Path(d), stg_fx=True)
        assert p.returncode == 2 and 'fixtures 2/2 staged' in p.stdout, p.stdout
        assert (s / 'fx').resolve() == (Path(d) / 'stg/fx').resolve()
    print('test_stage_stg_die_fx PASS 4/4')


if __name__ == '__main__':
    main()
