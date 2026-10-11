#!/usr/bin/env python3
"""Exact gate + throughput bench of the S81 VM master dsfd_sp_vm_m (s81-vm-1011, 2026-10-11).

    python3 tools/s81_vm/s81_vm_gate.py one CASE --out DIR      -> exit 0 iff the case meets its expectation
    python3 tools/s81_vm/s81_vm_gate.py all --out DIR           -> every case, DIR/summary.json

Cases: gold_s{1,2,3} (exact, 60k cycles), tp (throughput, production-shaped streams), and the negative controls
mut_stale / mut_dropw / mut_early (must FAIL).  Bench rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm.sv (Verilator)."""
import argparse, json, re, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
SRCS = ['rtl/dsrom_sys/s81_ph/test/tb_dsfd_sp_vm.sv', 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv',
        'rtl/dsrom_sys/s81_ph/vm/dsfd_vm_bgq_sys.sv', 'rtl/dsrom_sys/mtp/dsfd_vm_wfc_ep.sv',
        'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_rtt.sv', 'rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv',
        'rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
CASES = {
    'gold_s1': dict(params=dict(SEED=1), expect='pass'),
    'gold_s2': dict(params=dict(SEED=2), expect='pass'),
    'gold_s3': dict(params=dict(SEED=3, NCYC=120000), expect='pass'),
    'tp': dict(params=dict(MODE=1, TP_ROWS=64), expect='pass'),
    'tp128': dict(params=dict(MODE=1, TP_ROWS=128), expect='pass'),
    'mut_stale': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_STALE'], expect='fail'),
    'mut_dropw': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_DROPW'], expect='fail'),
    'mut_early': dict(params=dict(SEED=1, NCYC=20000), defines=['OT_SPVM_MUT_EARLY'], expect='fail'),
    'mut_early_s2': dict(params=dict(SEED=2, NCYC=20000), defines=['OT_SPVM_MUT_EARLY'], expect='fail'),
    'neg_early_consumer': dict(params=dict(SEED=1, NCYC=20000, EARLYC=1), expect='fail', regex='EARLY_READ'),
}


def build(out, tag, defines, params):
    obj = out / f'obj_{tag}'
    cmd = ['verilator', '--binary', '--timing', '-O1', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '8',
           '--top-module', 'tb_dsfd_sp_vm', '--Mdir', str(obj), *[f'+define+{d}' for d in defines],
           *[f'-G{k}={v}' for k, v in params.items()], *[str(ROOT / s) for s in SRCS]]
    b = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    (out / f'build_{tag}.log').write_text(' '.join(cmd) + '\n' + b.stdout + b.stderr)
    return b.returncode, obj / 'Vtb_dsfd_sp_vm', b.stdout + b.stderr


def one(name, out):
    c = CASES[name]
    out.mkdir(parents=True, exist_ok=True)
    rc, exe, blog = build(out, name, c.get('defines', []), c['params'])
    if rc:
        print(f'SPVM_{name}: BUILD_FAIL'); print('\n'.join([l for l in blog.splitlines() if 'rror' in l][:20]))
        return dict(case=name, ok=False, build_fail=True)
    r = subprocess.run([str(exe)], capture_output=True, text=True)
    log = r.stdout + r.stderr
    (out / f'run_{name}.log').write_text(log)
    keep = [l for l in log.splitlines() if l.startswith(('RESULT', 'THROUGHPUT', 'PASS', 'FAIL', 'MISMATCH', 'FAULT', 'MIRROR', '%Error'))
            or 'EARLY_READ' in l]
    passed = any(l.strip() == 'PASS' for l in log.splitlines())
    ok = passed if c['expect'] == 'pass' else (not passed and (not c.get('regex') or re.search(c['regex'], log) is not None))
    res = dict(case=name, expect=c['expect'], passed=passed, ok=ok, tail=keep[-12:])
    m = re.search(r'THROUGHPUT .*', log)
    if m:
        res['throughput'] = m.group(0)
    print('\n'.join(keep[-12:]))
    print(f'SPVM_{name}: {"PASS" if passed else "FAIL"} (expect {c["expect"]}) -> {"OK" if ok else "BAD"}')
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['one', 'all']); ap.add_argument('case', nargs='?'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    out = Path(a.out)
    if a.mode == 'one':
        r = one(a.case, out)
        sys.exit(0 if r['ok'] else 1)
    res = [one(n, out / n) for n in CASES]
    (out / 'summary.json').write_text(json.dumps(res, indent=1))
    ok = all(r['ok'] for r in res)
    print('SPVM_GATE', 'PASS' if ok else 'FAIL')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
