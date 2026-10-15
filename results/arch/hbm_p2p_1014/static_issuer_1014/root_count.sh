#!/usr/bin/env bash
set -euo pipefail
OUT=/tmp/hbm-static-issuer-root-count-1014
mkdir -p "$OUT"
python3 - <<'PYPORT'
import pathlib
p=pathlib.Path('physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v')
s=p.read_text();s=s[s.index('module '):];s=s[:s.index(');')+2]
pathlib.Path('/tmp/hbm-static-issuer-root-count-1014/macro_ports.v').write_text('(* blackbox *) '+s+'\nendmodule\n')
PYPORT
P=rtl/hbm_accel/generic/collective/p2p
for top in ot_hgi_coll_static_issuer ot_hgi_coll_static_program_bank;do
 yosys -Q -T -p "read_verilog -lib -sv $OUT/macro_ports.v; read_verilog -sv $P/ot_hgi_coll_static_issuer.sv; hierarchy -top $top; proc; memory_map; opt; write_json $OUT/$top.json" > "$OUT/$top.log" 2>&1
done
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('/tmp/hbm-static-issuer-root-count-1014');out={}
for f in p.glob('ot_*.json'):
 v=json.loads(f.read_text())['modules'];m=v[f.stem]
 own=sum(int(c['parameters']['WIDTH'],2) for c in m['cells'].values() if 'dff' in c['type'].lower())
 qbits={b for c in m['cells'].values() if 'dff' in c['type'].lower() for b in c['connections']['Q']}
 outputbits={b for port in m['ports'].values() if port['direction']=='output' for b in port['bits']}
 out[f.stem]={'own_register_bits':own,'direct_register_Q_output_bits':len(outputbits&qbits),'output_bits':len(outputbits),'status':'Yosys proc/memory_map/opt, actual catalog SRAM treated as blackbox; not CTS or timing qualification'}
(p/'summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
PY
