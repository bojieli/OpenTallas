#!/usr/bin/env python3
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[2]
d=root/'results/rtl/qwen_compute_native_glue_1014/tx_rne207_1015'
for name,want in json.loads((d/'source_hashes.json').read_text()).items():
 assert hashlib.sha256((root/name).read_bytes()).hexdigest()==want,name
for name,want in json.loads((d/'ARTIFACT_HASHES.json').read_text()).items():
 assert hashlib.sha256((d/name).read_bytes()).hexdigest()==want,name
r=json.loads((d/'receipt.json').read_text())
assert r['harness_exit_code']==0 and r['formal_inputs_unconstrained_bits']==267
assert r['total_data_edges']==2 and r['extra_compiler_edges']==0 and r['real_pipe_widths']==[207,198]
assert len(r['formal'])==5 and len(r['bench'])==7
assert all(x['status']=='PASS'for x in r['formal']+r['bench'])
assert r['coverage']['checks']==8196 and r['coverage']['async_assertions']==4
assert 'RAN on ot-epyc4 (unit oth-ubuntu-2074936-1792063672): exit 0'in(d/'job.log').read_text()
print('PASS standalone RNE207to198 receipt: all267inputs formal,4formal mutants,8196edge/reset checks,6bench mutants; parent/native qualificationOPEN')
