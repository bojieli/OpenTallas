#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=${1:?out};mkdir -p "$OUT";OUT=$(cd "$OUT" && pwd)
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x $Y ]] || Y=$(command -v yosys)
"$Y" -Q -T -p "read_verilog -sv rtl/qwen_sys/host_20261013/qkd_host_ctl_pins.sv rtl/qwen_sys/host_20261013/qkd_host_if_pins.sv rtl/qwen_sys/host_20261013/qkd_host_csr_pins.sv rtl/qwen_sys/host_20261013/qkd_host_rst_pins.sv rtl/qwen_sys/host_20261013/qkd_host_pin_channel.sv rtl/qwen_sys/host_20261013/qkd_host_fullcontrol.sv rtl/qwen_sys/host_20261013/qkd_host_sys_csr.sv rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/physical/ot_qwen_host_ctl.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv; hierarchy -top qkd_host_fullcontrol; proc; opt; memory_map; opt; write_json $OUT/net.json" > "$OUT/yosys.log" 2>&1
python3 - "$OUT" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1]);d=json.loads((p/'net.json').read_text());rows={}
for name,m in d['modules'].items():
 flops={}
 for c in m.get('cells',{}).values():
  if 'dff' in c['type'].lower():
   clk=','.join(map(str,c['connections'].get('CLK',[])))
   flops[clk]=flops.get(clk,0)+len(c['connections']['Q'])
 rows[name]={'flop_bits':sum(flops.values()),'clock_root_sinks':flops}
def total(name):
 m=d['modules'][name]
 return rows[name]['flop_bits']+sum(total(c['type']) for c in m.get('cells',{}).values() if c['type'] in d['modules'])
roots={}
for instance,cell in d['modules']['qkd_host_fullcontrol']['cells'].items():
 if cell['type'] in d['modules']:
  roots[instance]={'master':cell['type'],'hierarchical_flop_bits':total(cell['type'])}
rows['physical_partition_roots']=roots
(p/'census.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
PY
