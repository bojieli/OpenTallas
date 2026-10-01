#!/usr/bin/env python3
"""Exact same-cycle W10 wake/reset/drain gate and stuck-wake negative control."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from w10_frontend_main_exact import ROOT, RTL


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--jobs', type=int, default=4)
    a = ap.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise SystemExit('exact gate requires clean pinned sources')
    model = ROOT / 'results/uarch/w10_baseline_wake/prebuild.json'
    if json.loads(model.read_text())['verdict'] != 'PASS_SIZING_ONLY':
        raise SystemExit('full-size prebuild required')
    sources = [p for p in RTL if p != 'rtl/test/tb_w10_frontend_main_exact.sv']
    sources += ['rtl/v41rom/ot_v41_rom_elem_wake_w10.sv', 'rtl/test/tb_w10_wake_exact.sv']
    a.work.mkdir(parents=True, exist_ok=False)
    rec = dict(schema='opentallas.w10.wake.exact.v1', verdict='FAIL', adopted=False,
               source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in
                              sources + ['tools/w10_wake_exact.py', str(model.relative_to(ROOT))]},
               compared='original full-arithmetic FRONT_PAR0 versus opt-in WAKE_REG1; same-cycle public controls and valid partial bits',
               coverage_required=['reset initially low','idle-to-work','immediate go/activation beat',
                                  'mid-operation reset','reconfiguration','empty family','final partial and drain','all eight leaf clocks stop'],
               runs=[])
    verilator = Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    cmd = [str(verilator), '--binary', '--timing', '-Wno-fatal', '-Wno-lint', '-Wno-style',
           '--top-module', 'tb_w10_wake_exact', '--Mdir', str(a.work/'build'), '-j', str(a.jobs),
           '-CFLAGS', '-O0'] + [str(ROOT/p) for p in sources]
    with (a.work/'build.log').open('w') as log:
        p = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    rec['build_command'], rec['build_returncode'] = cmd, p.returncode
    if p.returncode == 0:
        for name, extra in [('positive', []), ('negative', ['+WAKE_MUTANT'])]:
            run = subprocess.run([str(a.work/'build/Vtb_w10_wake_exact')] + extra,
                                 cwd=a.work, capture_output=True, text=True)
            log = run.stdout + run.stderr
            (a.work/(name+'.log')).write_text(log)
            cov = re.search(r'PASS cycles=(\d+) hits=(\d+) issues=(\d+) rows=(\d+) nonzero=(\d+) classes=(\d+) wraps=(\d+) qadv=(\d+) restarts=(\d+) rejected=(\d+)',log)
            passed = bool(cov) and run.returncode == 0 if name == 'positive' else run.returncode != 0 and 'public control' in log
            row = dict(name=name, returncode=run.returncode, passed=passed,
                       log_sha256=hashlib.sha256(log.encode()).hexdigest())
            if cov:
                row['coverage'] = dict(zip(['cycles','hits','issues','rows','nonzero','classes','wraps','qadv','restarts','rejected'],map(int,cov.groups())))
                row['added_cycles'] = 0
            rec['runs'].append(row)
        if all(r['passed'] for r in rec['runs']):
            rec['verdict'] = 'PASS'
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        json.dump(rec, f, indent=2); f.write('\n')
    print(json.dumps(rec, indent=2))
    return rec['verdict'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
