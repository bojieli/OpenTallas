#!/usr/bin/env python3
"""el1013-s81-vmfe/B6 (S3): dsfd_vm_cl RT 1 (the M5 dsfd_vm_clt) against RT 0 (the closed clt8a expressions), every cycle.

    python3 tools/s81_vm/cl_rt_bench.py exact  --out DIR     -> exit 0 iff PASS (0 mismatches, cover counts met)
    python3 tools/s81_vm/cl_rt_bench.py mutant --out DIR     -> exit 0 iff the forward-less mutant FAILS
Bench rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_cl_rt.sv (Verilator >= 5.050)."""
import argparse, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s81_vm_gate as G  # noqa: E402
ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['exact', 'mutant']); ap.add_argument('--out', required=True)
ap.add_argument('--ncyc', type=int, default=1000000); ap.add_argument('--seed', type=int, default=1)
a = ap.parse_args(); out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
vbin, vver = G.verilator_bin()
if vbin is None:
    print('CLRT: TOOL_VERSION', vver); sys.exit(2)
cmd = [vbin, '--binary', '--timing', '-O2', '-Wno-fatal', '-Wno-lint', '-Wno-style', '-j', '4', '--top-module', 'tb_dsfd_vm_cl_rt',
       '--Mdir', str(out / f'obj_{a.mode}'), f'-GNCYC={a.ncyc}', f'-GSEED={a.seed}', *(['+define+OT_SPVM_MUT_CLRT'] if a.mode == 'mutant' else []),
       str(G.ROOT / 'rtl/dsrom_sys/s81_ph/test/tb_dsfd_vm_cl_rt.sv'), str(G.ROOT / 'rtl/dsrom_sys/s81_ph/vm/dsfd_sp_vm.sv'),
       *[str(G.ROOT / s) for s in G.SRCS[2:]]]
b = subprocess.run(cmd, capture_output=True, text=True, cwd=G.ROOT)
(out / f'build_{a.mode}.log').write_text(' '.join(cmd) + '\n' + b.stdout + b.stderr)
if b.returncode:
    print('CLRT: BUILD_FAIL'); print('\n'.join([l for l in (b.stdout + b.stderr).splitlines() if 'rror' in l][:20])); sys.exit(2)
r = subprocess.run([str(out / f'obj_{a.mode}' / 'Vtb_dsfd_vm_cl_rt')], capture_output=True, text=True)
log = r.stdout + r.stderr; (out / f'run_{a.mode}.log').write_text(log)
keep = [l for l in log.splitlines() if l.startswith(('CLRT', 'PASS', 'FAIL', 'MISMATCH'))]
print('\n'.join(keep[-10:]))
passed = any(l.strip() == 'PASS' for l in log.splitlines())
ok = passed if a.mode == 'exact' else (not passed and 'mismatches=' in log)
print(f'CLRT_{a.mode}: {"PASS" if passed else "FAIL"} (expect {"pass" if a.mode == "exact" else "fail"}) -> {"OK" if ok else "BAD"}')
sys.exit(0 if ok else 1)
