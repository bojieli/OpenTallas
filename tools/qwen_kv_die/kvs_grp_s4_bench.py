#!/usr/bin/env python3
"""KV-GRP5 2026-10-19: equivalence bench of the s4 group tile qkd_kvs_grp_h_s4 (kv_grp_safe4.py).

Same oracle, ages, stimulus and comparison as kvs_grp_s2_bench.py (the unchanged sha-pinned DOMSPLIT MU/BOOT_AGES tiles,
tb/qkd_kvs_grp_s2_ref.sv): the H tile under test is qkd_kvs_grp_h_s4 (rsp / krsp from separate kept exit copies, +0
cycles), the core tile stays qkd_kvs_grp_s2 (unchanged, so m1..m8 keep their meaning).  Every retained output of both
tiles is compared bit-exact at every core AND every HBM falling edge.  m0 must PASS; m1..m8 (kv_grp_safe2.MUTANTS) and
m9 / m10 (kv_grp_safe4.MUTANTS: the krsp / rsp exit copies on the compared path) must each FAIL with S2_FAIL.

    python3 tools/qwen_kv_die/kvs_grp_s4_bench.py --out DIR [--cases m0,m9,...] [--raw]   (fleet: Verilator 5.050)
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_grp_safe2 as S2  # noqa: E402
import kv_grp_safe4 as S4  # noqa: E402
import kvs_grp_s2_bench as B  # noqa: E402

SOURCES = [S2.OUT, S4.OUT, S2.REF] + B.LEAVES
MUTANTS = {**S2.MUTANTS, **S4.MUTANTS}


def tb(edges, out):
    ports_file = out / 'dut_ports.sv'                     # port lists of both DUT masters (B.tb reads one file)
    ports_file.write_text((ROOT / S2.OUT).read_text() + '\n' + (ROOT / S4.OUT).read_text())
    shim = types.SimpleNamespace(OUT=str(ports_file), REF=S2.REF,
                                 KINDS=(('qkd_kvs_grp', 'qkd_kvs_grp_s2'), ('qkd_kvs_grp_h', S4.TOP)))
    real, B.S2 = B.S2, shim
    try:
        return B.tb(edges)
    finally:
        B.S2 = real


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--cases', default=','.join(f'm{i}' for i in [0] + sorted(MUTANTS)))
    ap.add_argument('--edges', type=int, default=6000)
    ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    ap.add_argument('--tb-only', action='store_true')
    ap.add_argument('--raw', action='store_true', help='one case: echo the simulator verdict line, exit with its rc')
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for gen in ('kv_grp_safe2.py', 'kv_grp_safe4.py'):     # source identity + generated files current
        if subprocess.run([sys.executable, str(ROOT / 'tools/qwen_kv_die' / gen), '--check'], cwd=ROOT).returncode:
            raise SystemExit(f'generated tile stale ({gen})')
    results = []
    for case in a.cases.split(','):
        m = int(case[1:])
        txt = tb(a.edges, out).replace('module tb;', f'module tb;\nlocalparam integer MUT = {m};', 1)
        (out / f'tb_{case}.sv').write_text(txt)
        if a.tb_only:
            continue
        ver = subprocess.check_output([a.verilator, '--version'], text=True).strip()
        cmd = [a.verilator, '--binary', '--timing', '-j', '8', '-Wno-fatal', '-Wno-lint', '-Wno-style', '--x-assign', '0',
               '--x-initial', '0', '--top-module', 'tb', '--Mdir', str(out / f'build_{case}'), str(out / f'tb_{case}.sv')] + \
              [str(ROOT / s) for s in SOURCES]
        with open(out / f'{case}.build.log', 'w') as lg:
            rc = subprocess.run(cmd, stdout=lg, stderr=subprocess.STDOUT).returncode
        if rc:
            results.append(dict(case=case, verdict='BUILD_FAIL', rc=rc))
            print(json.dumps(results[-1]), flush=True)
            if a.raw:
                sys.exit(rc)
            continue
        with open(out / f'{case}.log', 'w') as lg:
            rc = subprocess.run([str(out / f'build_{case}' / 'Vtb')], stdout=lg, stderr=subprocess.STDOUT).returncode
        log = (out / f'{case}.log').read_text()
        ok = (rc == 0 and 'S2_PASS' in log) if m == 0 else (rc != 0 and 'S2_FAIL' in log)
        line = next((ln for ln in log.splitlines() if 'S2_' in ln), '')
        print(line, flush=True)
        shutil.rmtree(out / f'build_{case}', ignore_errors=True)
        if a.raw:
            sys.exit(rc)
        results.append(dict(case=case, mut=m, what=MUTANTS.get(m, 'positive'), rc=rc,
                            verdict=('PASS' if m == 0 else 'FAIL (expected)') if ok else 'UNEXPECTED',
                            witness=line[:400], verilator=ver))
        print(json.dumps(results[-1]), flush=True)
    src = {s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest() for s in SOURCES}
    (out / 'results.json').write_text(json.dumps(dict(edges=a.edges, sources=src, cases=results), indent=1) + '\n')
    bad = [r for r in results if r.get('verdict') in ('UNEXPECTED', 'BUILD_FAIL')]
    print('S4_BENCH', 'ALL_OK' if not bad else f'BAD {bad}')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
