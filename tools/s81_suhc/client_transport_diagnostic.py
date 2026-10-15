#!/usr/bin/env python3
"""Measure unscheduled SU/HC transport hazards; never a production implementation.

Full-shape arithmetic reference, finite slot transactions, and delayed memory
retirement expose slot reuse and early completion. Mutants remove the read credit
guard (1), write credit guard (2), or commit fence (3). Runtime credits deliberately
exist ONLY in the diagnostic copies, because production uses static reservations.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/s81_suhc'))
import hc_gate as H
import su_gate as S

DIAG = 'rtl/test/s81_client_transport_diagnostic/'

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--client', choices=['su', 'hc'], required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--mutant', type=int, choices=range(4), default=0)
    ap.add_argument('--seed', type=int, default=20261014)
    ap.add_argument('--write-delay', type=int, default=37)
    ap.add_argument('--legacy', action='store_true')
    a = ap.parse_args()
    out = a.out.resolve(); out.mkdir(parents=True, exist_ok=True)
    case = out/'case'; case.mkdir(exist_ok=True)
    rng = np.random.default_rng(a.seed)
    if a.client == 'su':
        r = S.build_run(S.SHAPES['full'], rng)
        r.write(case, dict(seed=a.seed, shape='full'))
        rtl = S.RTL
        top = 'tb_s81_su_master'
        params = dict(S.SHAPES['full'])
    else:
        r = H.Run(256); r.build(H.chains_stress(rng, [0, 1]))
        r.write(case, dict(seed=a.seed, shape='full'))
        rtl = H.RTL
        top = 'tb_s81_hc_master'
        params = dict(NG=256)
    params.update(CREDIT_MODE=int(not a.legacy), PACING_MUT=a.mutant, WDELAY=a.write_delay)
    mapped = []
    for x in rtl:
        if x.endswith((f'/ot_s81_{a.client}_core.sv', f'/dsfd_sp_{a.client}.sv')):
            x = DIAG + Path(x).name
        mapped.append(x)
    tb = DIAG + f'tb_s81_{a.client}_master.sv'
    obj = out/f'obj_{a.client}_m{a.mutant}_wd{a.write_delay}_legacy{int(a.legacy)}'
    obj.mkdir(exist_ok=True)
    sources = H.dpi_rest(obj) + [ROOT/x for x in H.FP['dpi'] + mapped + [tb]]
    exe = obj/f'V{top}'
    cmd = [H.VERILATOR, '--binary', '--timing', '-O2', '-Wno-fatal', '-Wno-WIDTH',
           '--top-module', top, '-Mdir', str(obj), '-j', '16', '--unroll-count', '4', '-fno-dfg',
           *[f'-G{k}={v}' for k,v in params.items()], *map(str,sources), '-CFLAGS','-O1']
    if not exe.exists():
        build = subprocess.run(cmd, capture_output=True, text=True)
        (out/'build.log').write_text(' '.join(cmd)+'\n'+build.stdout+build.stderr)
        if build.returncode:
            print('BUILD FAILED', flush=True); return 2
    run = subprocess.run([str(exe)], cwd=case, capture_output=True, text=True)
    (out/'run.log').write_text(run.stdout+run.stderr)
    pass_line = 'SUG PASS' if a.client == 'su' else 'HCG PASS'
    observed = pass_line in run.stdout and run.returncode == 0
    rec = dict(client=a.client, shape='full', seed=a.seed, params=params, returncode=run.returncode,
               diagnostic_only=True, passed=observed, expected_failure=a.mutant != 0,
               source_sha256={str(x.relative_to(ROOT)):hashlib.sha256(x.read_bytes()).hexdigest()
                              for x in sources if x.is_relative_to(ROOT)})
    (out/'evidence.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(run.stdout[-4500:], flush=True)
    # A mutant must produce an observed assertion or result failure, never a missing-result timeout.
    failed = 'FAIL' in run.stdout or 'before response' in run.stdout or 'before commit' in run.stdout or 'before actual write commit' in run.stdout
    return 0 if (observed if a.mutant == 0 else not observed and failed) else 1

if __name__ == '__main__':
    raise SystemExit(main())
