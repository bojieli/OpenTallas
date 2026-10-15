#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd);out=${1:?fresh census directory};mkdir "$out"
sources=(rtl/qwen_split/qfd_native59_compute_service.sv rtl/qwen_split/qfd_native59_command_context.sv rtl/qwen_split/qfd_native59_static_service.sv rtl/qwen_split/qfd_native59_record_endpoint.sv rtl/qwen_split/qfd_kvn_static_transport.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv)
cd "$root"
yosys -Q -T -p "read_verilog -sv ${sources[*]}; hierarchy -check -top qfd_native59_compute_service; flatten; proc; opt; memory_map; opt_clean; stat; write_json $out/net.json" > "$out/yosys.log" 2>&1
python3 - "$out" <<'PY'
import json,sys
from pathlib import Path
p=Path(sys.argv[1]);m=json.loads((p/'net.json').read_text())['modules']['qfd_native59_compute_service']
clockbits={v['bits'][0]:k for k,v in m['ports'].items() if k.startswith('ck_')}
bits={k:0 for k in clockbits.values()};other={}
for c in m['cells'].values():
 if c['type'].startswith(('$dff','$adff','$sdff')):
  clk=c['connections'].get('CLK',[None])[0];n=len(c['connections']['Q'])
  if clk not in clockbits:raise RuntimeError('unowned sequential clock '+repr(c))
  bits[clockbits[clk]]+=n
 elif c['type'].startswith('$mem'):other[c['type']]=other.get(c['type'],0)+1
r={'scope':'inferred real FF and port census only; no mapped area/pin/phase qualification',
 'clock_entries':bits,'total_flop_bits':sum(bits.values()),'unmapped_memories':other,
 'ports':{k:{'direction':v['direction'],'bits':len(v['bits'])} for k,v in m['ports'].items()},
 'physical_qualified':False,'area_um2':None}
(p/'census.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r['clock_entries']),r['total_flop_bits'])
PY
