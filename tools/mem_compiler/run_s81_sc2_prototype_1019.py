#!/usr/bin/env python3
"""Fleet-only geometry, source consistency, and unchanged functional contract."""
import json
import subprocess
import sys
from pathlib import Path
from build_s81_sc2_prototype_1019 import NEW, PACKET, ROOT

out = PACKET / 'sc2_prototype/generated'
subprocess.run([sys.executable, str(ROOT/'tools/mem_compiler/check_s81_sc2_prototype_1019.py'), str(out)], check=True)
v = str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
version = subprocess.check_output([v, '--version'], text=True).strip()
assert '5.050' in version, version
functional = PACKET / 'sc2_prototype/functional'
functional.mkdir(exist_ok=True)
rtl = (out/(NEW+'.v')).read_text()
old_order = 'if (r_ce_in) rd_out <= word_read(r_addr_in);\n        if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);'
new_order = 'if (w_ce_in) word_write(w_addr_in, wd_in, w_mask_in);\n        if (r_ce_in) rd_out <= word_read(r_addr_in);'
cases = [('positive', None, None), ('write_first', old_order, new_order),
         ('ignore_mask', 'if (m[b] && n != 0)', 'if (n != 0)'),
         ('ignore_read_enable', 'if (r_ce_in) rd_out <=', "if (1'b1) rd_out <=")]
summary = dict(verilator=version, cases=[], status='INCOMPLETE', scope='Source/geometry prototype only, no Liberty or gate')
for name, old, new in cases:
    case = functional/name; case.mkdir(exist_ok=True)
    changed = rtl if old is None else rtl.replace(old, new)
    assert old is None or changed != rtl
    path = case/'dut.v'; path.write_text(changed)
    cmd = [v, '--binary', '--timing', '-Wno-fatal', '--top-module', 'tb', '-j', '4', '--Mdir', str(case/'obj'), str(path), str(PACKET/'sc2_prototype/tb.sv')]
    with (case/'build.log').open('w') as log:
        subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=True)
    cp = subprocess.run([str(case/'obj/Vtb')], capture_output=True, text=True)
    text = cp.stdout + cp.stderr; (case/'witness.log').write_text(text)
    passed = (cp.returncode == 0 and 'SC2_FUNCTION_PASS' in text) if old is None else (cp.returncode != 0 and 'SC2_FUNCTION_MISMATCH' in text)
    summary['cases'].append(dict(name=name, exit=cp.returncode, expected_verdict=passed))
    print(name, 'PASS' if passed else 'FAIL', flush=True)
    (functional/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    assert passed, text
summary['status']='PASS'
(functional/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print('SC2_PROTOTYPE_PASS functional_positive=1 causal_function_mutants=3 causal_geometry_mutants=2 NO_LIBERTY', flush=True)
