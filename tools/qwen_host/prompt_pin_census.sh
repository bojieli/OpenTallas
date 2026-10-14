#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:?out};mkdir -p "$OUT";OUT=$(cd "$OUT"&&pwd)
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x $Y ]]||Y=$(command -v yosys)
"$Y" -Q -T -p "read_verilog -sv rtl/qwen_sys/host_20261013/qkd_host_prompt_pins.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv; read_verilog -lib physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v; hierarchy -top qkd_host_prompt_pins; proc; opt; write_json $OUT/net.json" > "$OUT/yosys.log" 2>&1
python3 - "$OUT" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);d=json.loads((p/'net.json').read_text());rows={}
for n,m in d['modules'].items():
 rows[n]={'flop_bits':sum(len(c['connections']['Q'])for c in m.get('cells',{}).values()if 'dff' in c['type'].lower()),'blackbox':m.get('attributes',{}).get('blackbox',0)}
rows['total_logic_sinks']=sum(v['flop_bits']for v in rows.values());rows['macro_clock_pins']=1
(p/'census.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
PY
