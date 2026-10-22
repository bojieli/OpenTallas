#!/usr/bin/env python3
"""Fleet-only actual VP SRAM + production KV512 consumer component proof.

--baseline is an immutable kv_bank_1021/gate.py output with its vector files and
source inventory. This gate never overwrites that run or its compiled objects.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--baseline', required=True, type=Path)
p.add_argument('--out', required=True, type=Path)
p.add_argument('--resume-objects', type=Path, help='completed Verilator model from terminated attempt; reuses its objects')
p.add_argument('--jobs', type=int, default=2)
a = p.parse_args()
ROOT = Path(__file__).resolve().parents[3]
a.out.mkdir(parents=True, exist_ok=False)
base = json.loads((a.baseline/'result.json').read_text())
assert base['status'] == 'PASS'
src = [s for s in base['source_sha256'] if not s.endswith('tb_s81sl_kv_leaf.sv')]
src += ['rtl/lib/ot_rst_relay.sv', 'rtl/hdc/ot_hdc_delay.sv',
        'rtl/dsrom_sys/s81_dv/slice/ot_s81sl_vp.sv',
        'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',
        'rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v',
        'tools/s81_dv/kv_vp_1021/tb_kv_vp.sv']
src = list(dict.fromkeys(src))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
pins = {s: sha(ROOT/s) for s in src}
for s, digest in base['source_sha256'].items():
    if s in pins: assert pins[s] == digest, s
vectors = {}
for name in ('gain_vm.mem', 'kv_vm.mem', 'expected.mem'):
    shutil.copyfile(a.baseline/name, a.out/name)
    vectors[name] = sha(a.out/name)
obj = a.resume_objects or a.out/'obj'
if a.resume_objects:
    prior = json.loads((obj.parent/'result.json').read_text())
    assert prior['source_sha256'] == pins, 'resume sources differ'
    assert (obj/'Vtb_kv_vp.mk').is_file(), 'frontend incomplete'
v = str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
cmd = [v, '--binary', '--timing', '-O1', '-fno-dfg', '--unroll-count', '4',
       '-Wno-fatal', '-Wno-WIDTH', '--top-module', 'tb_kv_vp', '-Mdir', str(obj),
       '-j', str(a.jobs), *[str(ROOT/s) for s in src], '-CFLAGS', '-O1']
if a.resume_objects:
    cmd = ['make', '-C', str(obj), '-f', 'Vtb_kv_vp.mk', '-j', str(a.jobs)]
result = dict(status='RUNNING', full_token=False, full_layer=False,
              source_sha256=pins, vector_sha256=vectors, argv=cmd,
              scope='actual VP storage/extension/dispatch + KV512 bank; boundary fixture preload',
              open=['XS producer/capture', 'distributed transport', 'interrank carriage', 'SO', 'full layer replay'])
def save(): (a.out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
save()
b = subprocess.run(cmd, capture_output=True, text=True)
(a.out/'build.log').write_text(b.stdout+b.stderr)
if b.returncode:
    result.update(status='FAIL', reason='build', exit_code=b.returncode);save();sys.exit(1)
# Resuming make bypasses the installed Verilator wrapper; repeat its exact NBA
# model scan explicitly before any simulation and preserve the complete result.
guard_dir = Path.home()/'.local/opentallas-tools/verilator-5.050/share/ot_nba_guard'
sys.path.insert(0, str(guard_dir))
import verilator_nba_guard as G
guard = G.scan(str(obj))
(a.out/'nba_guard.json').write_text(json.dumps(guard, indent=2)+'\n')
result['nba_guard_sha256'] = sha(guard_dir/'verilator_nba_guard.py')
if guard['findings']:
    result.update(status='FAIL', reason='NBA guard');save();sys.exit(86)
checks = {}
for name, flags in [('positive', []), ('negative_exp', ['+MUT_DROP_EXP'])]:
    r = subprocess.run([str(obj/'Vtb_kv_vp'), *flags], cwd=a.out, capture_output=True, text=True)
    (a.out/(name+'.log')).write_text(r.stdout+r.stderr)
    checks[name] = dict(exit_code=r.returncode, passed=(r.returncode == 0 and 'KV_VP PASS' in r.stdout)
                        if not flags else (r.returncode != 0 and 'KV_VP FAIL' in r.stdout+r.stderr))
assert pins == {s: sha(ROOT/s) for s in src}
ok = all(v['passed'] for v in checks.values())
result.update(status='PASS' if ok else 'FAIL', checks=checks);save()
print((a.out/'positive.log').read_text());print(json.dumps(checks));sys.exit(int(not ok))
