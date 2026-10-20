#!/usr/bin/env python3
"""Source-primitive census only; the new raw-por contract is not admitted."""
from pathlib import Path
import json
import subprocess

top = 'qkd_hr_core_prompt_mu4p2_n32_guard'
libs = sorted(Path('libs').glob('*.lib'))
commands = ['read_liberty -lib '+str(p) for p in libs]
commands += ['read_verilog -lib macro_bb.v', 'read_verilog '+top+'.sv',
             'hierarchy -check -top '+top, 'write_verilog -noattr guard_serialized.v']
Path('guard_serialize.ys').write_text('\n'.join(commands)+'\n')
with Path('guard_serialize.log').open('w') as f:
    subprocess.run(['yosys', '-s', 'guard_serialize.ys'], stdout=f, stderr=subprocess.STDOUT, check=True)
args = ['python3', 'native_census.py', '--netlist', 'guard_serialized.v', '--top', top, '--out', 'guard_native.json']
for p in sorted([*Path('libs').glob('*.lib'), *Path('macro_libs').glob('*.lib')]):
    args += ['--liberty', str(p)]
subprocess.run(args, check=True)
d = json.loads(Path('guard_native.json').read_text())
root = [r for r in d['driver_counts'] if r['driver'] == 'u_rank__u_control__por_n']
assert len(root) == 1 and root[0]['loads'] == 11, root
assert d['status'] == 'PASS' and d['max_dynamic_loads'] <= 32
summary = dict(status=d['status'], root=root[0], max_dynamic_loads=d['max_dynamic_loads'],
               scope='actual Liberty-aware source-primitive connectivity; NO resynthesis/layout/reset admission')
Path('guard_native_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary), flush=True)
