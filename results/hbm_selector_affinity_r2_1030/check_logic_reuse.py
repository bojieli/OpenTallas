#!/usr/bin/env python3
"""Check exact staged logic against a preserved EQUIVALENT proof; geometry is rerun."""
import hashlib
import json
import re
import sys
from pathlib import Path

k = Path(sys.argv[1])
r = json.loads(Path(sys.argv[2] if len(sys.argv)>2 else k/'lec/reuse.json').read_text())
h = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
actual = {p.name:h(p) for p in (k/'rtl').iterdir() if p.is_file()}
assert actual == r['rtl_sha256'], 'complete RTL inventory/digests changed'
assert h(k/'lec/lec.json') == r['source_qualified_proof_sha256'], 'proof changed'
assert json.loads((k/'lec/lec.json').read_text())['verdict'] == 'EQUIVALENT'
assert h(k/'lec/gold.ys') == r['formal_gold_script_sha256'], 'formal script changed'
assert h(k/'lec/gold.aig') == r['formal_gold_aig_sha256'], 'formal gold AIG changed'
assert h(next((k/'run/results').glob('*/*/base/1_synth.v'))) == r['synth_v_sha256'], 'gate changed'
assert h(next((k/'run/results').glob('*/*/base/1_2_yosys.v'))) == r['formal_netlist_sha256'], 'formal netlist changed'
assert h(k/'lec/gate.ys') == r['formal_gate_script_sha256'], 'formal gate script changed'
assert h(k/'lec/gate.aig') == r['formal_gate_aig_sha256'], 'formal gate AIG changed'
macro_actual={str(p.relative_to(k/'macros')):h(p) for p in (k/'macros').rglob('*') if p.is_file()}
assert macro_actual == r['macro_inventory_sha256'], 'macro views/model inventory changed'
f=json.loads((k/'freeze.json').read_text())
assert f['design']==r['new_top']==r['old_top']
assert (f.get('params') or {})==r['new_params']==r['old_params']
c=(k/'config.mk').read_text()
assert re.search(r'^export VERILOG_FILES = (.*)$',c,re.M).group(1).split()==r['verilog_files'], 'RTL_FILES changed'
defines=re.search(r'^export VERILOG_DEFINES = (.*)$',c,re.M).group(1).split()
assert defines==['-D'+d for d in r['new_defines']]
assert r['new_defines']==r['old_defines']
print('LEC_REUSE_EQ: complete RTL/top/params/defines and original formal gold/gate proof unchanged')
