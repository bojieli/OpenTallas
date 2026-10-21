#!/usr/bin/env python3
"""Prove independently initialized retained register copies converge at boot.

Run in the fleet lane directory, inside the pinned ORFS image. Correspondence
is a separate proof; this checks only the additional register-copy obligation.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sp = importlib.util.spec_from_file_location('tl', 'textbook_lint.py')
m = importlib.util.module_from_spec(sp)
sys.modules['tl'] = m
sp.loader.exec_module(m)
mods = m.parse_verilog(Path('original.v').read_text())
g, original_top = m.flatten(mods, None)
a = m.build(g, None)
record = json.loads(Path('qkd_hr_core_peer_n32.json').read_text())
eq = []
for row in record['copied_cells']:
    if row['kind'] != 'ff':
        continue
    ci = row['cell']
    for pin, bits in g.cells[ci][2].items():
        if a['pin_dir'][ci][pin] == 'out':
            for net in bits:
                eq += [f'(n{net}_c0 == n{net}_c{k})' for k in range(1, row['copies'])]
assert eq
top = record['top']
source = Path(top+'.sv').read_text()
source = source.replace('module '+top+' (', 'module '+top+' (copies_equal,', 1)
source = source.replace(');', ');\noutput wire copies_equal;\nassign copies_equal = '+ ' & '.join(eq)+';', 1)
ports=mods[original_top]
# Keep only the copied-state proof obligation visible at the proof-only boundary.
# Payload correctness remains with the SRAM exact bench and pin correspondence.
import re
end=source.index("endmodule")
head=source[:end]
ins=[n for n in ports.ports if ports.dirs[n]=="input"]
head=re.sub(r"module "+top+r" \(.*?\);", "module "+top+" (copies_equal,"+",".join(ins)+");",head,count=1,flags=re.S)
for name in ports.ports:
 if ports.dirs[name]=="output":
  head=re.sub(r"(?m)^  output (?:wire )?(.*?)"+re.escape(name)+r";", r"  wire \1"+name+";",head)
source=head+source[end:]

declarations=[]
connections=['.copies_equal(copies_equal)']
for name in ports.ports:
    if ports.dirs[name]!='input':
        continue
    width='' if name not in ports.widths else '[%d:%d] '%ports.widths[name]
    declarations.append('input wire '+width+name)
    connections.append('.'+name+'('+name+')')
source+='\nmodule proof('+','.join(declarations+['output wire copies_equal'])+');\n'+top+' u('+','.join(connections)+');\nendmodule\n'
Path('cold.sv').write_text(source)
cmd = ['read_liberty -ignore_miss_func '+str(p) for p in sorted(Path('libs').glob('*.lib'))]
cmd += ['read_verilog -overwrite canonical_ASR_normalized.v',
        'read_verilog -overwrite canonical_DFF_normalized.v',
        'read_verilog -formal macro_proof.v', 'read_verilog cold.sv',
        'hierarchy -check -top proof', 'setattr -mod -unset keep_hierarchy',
        'setattr -unset keep', 'flatten', 'proc', 'opt_expr', 'opt_clean',
        'write_json cold_pre.json', 'async2sync', 'clk2fflogic', 'opt_clean']
sat = 'sat -seq 24 -prove copies_equal 1 -prove-skip 11 -set host_rst_n 0 -set por_n 0 -verify'
for step in range(1,25):
    sat += f' -set-at {step} ck_core {step%2}'
    if step >= 13:
        sat += f' -set-at {step} host_rst_n 1 -set-at {step} por_n 1'
cmd.append(sat)
Path('cold.ys').write_text('\n'.join(cmd)+'\n')
with Path('cold.log').open('w') as out:
    rc = subprocess.run(['yosys','-s','cold.ys'], stdout=out, stderr=subprocess.STDOUT).returncode
state = json.loads(Path('cold_pre.json').read_text())['modules']['proof']
inits = {n:d['attributes']['init'] for n,d in state['netnames'].items() if 'init' in d.get('attributes',{})}
assert not inits, 'Unexpected fixed initial state in independent-state proof'
result = dict(passed=rc==0, independent_initial_state=True, opt_merge=False,
              ignore_unknown_cells=False,
              macro_abstraction="proof-only singleton shared unconstrained 546bit read stream per actual SRAM; no macro clones", copied_output_pairs=len(eq),
              reset_assert_steps=12, reset_release_steps=12,
              checked_steps='12..24', source_sha256=record['source_sha256'])
Path('cold_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(rc)
