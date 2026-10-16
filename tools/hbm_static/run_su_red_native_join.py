#!/usr/bin/env python3
"""Tiny actual qcore -> cxport -> RF component gate (two mapped SRAMs).

External boundaries: slice operands, collective returned words. No collective,
full SU, physical, or production qualification. Runs in <1 second locally.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('--out', type=Path, required=True)
a = ap.parse_args()
a.out.mkdir(parents=True, exist_ok=True)
s = 'rtl/hbm_accel/generic/adapters/static_su/'
sources = ['results/rtl/hbm_su_red_fork_1016/tb_su_red_native_join.sv']
sources += [s+p+'.sv' for p in ['top/ot_hbm_su_static_qcore',
    'register_file/ot_hbm_su_static_rf', 'reduction/ot_hbm_su_reduce_static',
    'collport/ot_hbm_su_static_cxport']]
sources += ['rtl/hdc/'+p+'.sv' for p in [
    'ot_hdc_fp32_add_lat', 'ot_hdc_prefix', 'ot_hdc_fastfp']]
sources += ['physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/'
            'ot_sram_1r1w_128x256_m1_r2c2.v']
exe = a.out.resolve()/'native.vvp'
build = subprocess.run(['iverilog', '-g2012', '-s', 'tb_su_red_native_join',
                        '-o', str(exe), *sources], cwd=ROOT,
                       capture_output=True, text=True)
(a.out/'build.log').write_text(build.stdout+build.stderr)
build.check_returncode()
rows = []
for name, args, negative in [('positive', [], False), ('late', ['+LATE'], False),
                            ('equal_depth_mutant', ['+MUT_EQUAL_DEPTH'], True)]:
    r = subprocess.run(['vvp', str(exe), *args], cwd=ROOT,
                       capture_output=True, text=True)
    text = r.stdout+r.stderr
    (a.out/(name+'.log')).write_text(text)
    passed = (r.returncode != 0 and 'SU_RED_NATIVE_JOIN FAIL' in text) if negative else (
        r.returncode == 0 and 'SU_RED_NATIVE_JOIN PASS' in text)
    rows.append(dict(case=name, negative=negative, passed=passed, exit=r.returncode))
receipt = dict(cases=rows, source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                                       for p in sources},
               scope='actual qcore two mapped SRAMs -> cxport carry -> returned RF sector; external slice operands and collective return',
               whole_layer_native_qualified=False, physical_qualified=False,
               production_rate_qualified=False)
(a.out/'native_receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
assert all(r['passed'] for r in rows), rows
print('SU_RED_NATIVE_COMPONENT_GATE_PASS')
