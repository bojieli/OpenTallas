#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd)
y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x "$y" ]]||y=$(command -v yosys)
"$y" -Q -T -p "read_verilog -sv -defer rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv rtl/qwen_sys/host_20261013/qkd_host_native_engine.sv rtl/qwen_sys/host_20261013/qkd_host_native_qm.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1_bb.v; hierarchy -top qkd_host_native_qm -chparam RMW_EN 0 -chparam QPIPE 2 -chparam NATIVE_ROWS 1; proc; opt; memory_map; opt; flatten; opt; write_json $out/native.json" > "$out/build.log" 2>&1
python3 - "$out" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'native.json').read_text())['modules']['qkd_host_native_qm'];clock={tuple(m['netnames'][n]['bits']):n for n in ['ck','clk_h','clk_i','clk_i_out']};clock.update({(b,):f'clk_i_bank[{k}]' for k,b in enumerate(m['netnames']['clk_i_bank']['bits'])});roots={n:0 for n in clock.values()};macros={n:0 for n in clock.values()}
for c in m['cells'].values():
 t=c['type'];con=c['connections']
 if 'dff' in t.lower():
  bits=tuple(con.get('CLK',con.get('C',[])));root=clock.get(bits,str(bits));roots[root]=roots.get(root,0)+len(con['Q'])
 elif t=='ot_sram_1r1w_32x128_m1':
  root=clock.get(tuple(con['clk']),str(tuple(con['clk'])));macros[root]=macros.get(root,0)+1
j=dict(status='NATIVE_SOURCE_CENSUS_ONLY_NO_PHYSICAL_QUALIFICATION',params=dict(QPIPE=2,NATIVE_ROWS=1,RMW_EN=0,HDMAX=128,KVHMAX=2),flop_roots=roots,macro_clock_pins=macros)
(p/'census.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
