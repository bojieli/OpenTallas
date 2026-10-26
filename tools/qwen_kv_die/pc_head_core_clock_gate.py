#!/usr/bin/env python3
"""Smallest real PC-head lockstep at common833, with a wrong-PC mutant. Run via ot-run."""
import argparse, copy, json, os, subprocess
from pathlib import Path
import plan_leaf_variants as P

ap = argparse.ArgumentParser()
ap.add_argument('out', type=Path)
a = ap.parse_args()
out = a.out.resolve()
out.mkdir(parents=True, exist_ok=True)
v = copy.deepcopy(next(v for v in P.VARIANTS if v['name'] == 'qkd_static_kv_pc_path_fan_nc_b_head_p'))
v['ov']['CORE_CLOCK'] = '1'
_, ports, params = P.variant(v)
tb = out / 'tb.sv'
tb.write_text(P.bench(v, ports, params))
files = [tb, P.ROOT / v['src'], P.ROOT / P.OUT / (v['name'] + '.sv')]
files += [P.ROOT / f for f in v['libs']]
verilator = os.environ.get('VERILATOR', str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
results = []
for tag, args in [('nominal', ['-GV0=17', '-GMV0=17']), ('mutant', ['-GV0=17', '-GMV0=1', '-GTMUT=1'])]:
    obj = out / tag
    cmd = [verilator, '--binary', '-j', '4', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-Wno-MULTIDRIVEN', '--top-module', 'tb_' + v['name'], '-Mdir', str(obj), '-o', 'Vtb'] + args + [str(f) for f in files]
    with (out / (tag + '.build.log')).open('w') as log:
        p = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT)
    if p.returncode:
        raise SystemExit(f'{tag} build failed: {out}/{tag}.build.log')
    p = subprocess.run([str(obj / 'Vtb')], capture_output=True, text=True)
    (out / (tag + '.log')).write_text(p.stdout + p.stderr)
    expected = 'PASS tb_' if tag == 'nominal' else 'FAIL tb_'
    ok = expected in p.stdout
    results.append(dict(test=tag, passed=ok, output=p.stdout[-1500:]))
    if not ok:
        raise SystemExit(f'{tag}: expected {expected}, see {out}/{tag}.log')
(out / 'result.json').write_text(json.dumps(dict(results=results, added_steady_cycles=0, core_clock=1), indent=2) + '\n')
print(json.dumps(dict(verdict='PASS', results=results)))
