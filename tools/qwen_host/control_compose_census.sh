#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:?out};mkdir -p "$OUT";OUT=$(cd "$OUT"&&pwd)
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x $Y ]]||Y=$(command -v yosys)
"$Y" -Q -T -p "read_verilog -defer -sv rtl/qwen_sys/host_20261013/*.sv rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv rtl/physical/ot_qwen_host_ctl.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv; read_verilog -lib physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2_bb.v; hierarchy -top qkd_host_control_packet; proc; opt; memory_map; opt; write_json $OUT/net.json" > "$OUT/yosys.log" 2>&1
python3 - "$OUT" <<'PY'
import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);d=json.loads((p/'net.json').read_text());rows={}
for n,m in d['modules'].items():rows[n]={'flop_bits':sum(len(c['connections']['Q'])for c in m.get('cells',{}).values()if 'dff' in c['type'].lower())}
def count(n):return rows[n]['flop_bits']+sum(count(c['type'])for c in d['modules'][n].get('cells',{}).values()if c['type']in d['modules'])
rows['roots']={i:{'master':c['type'],'hierarchical_flop_bits':count(c['type'])}for i,c in d['modules']['qkd_host_control_packet']['cells'].items()if c['type']in d['modules']}
rows['ports']=d['modules']['qkd_host_control_packet']['ports']
(p/'census.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows['roots'],indent=2));print('parent_flops',rows['qkd_host_control_packet']['flop_bits'])
PY
