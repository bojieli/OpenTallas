#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd)
y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x "$y" ]]||y=$(command -v yosys)
for top in qkd_host_rx_class qkd_host_tx_class qkd_host_rx_pad qkd_host_axi_packet qkd_host_ctrl_packet qkd_host_static_pc qkd_host_ingest_map qkd_host_ingest_station qkd_host_visibility_fence;do
 file=rtl/qwen_sys/host_20261013/$top.sv
 opts="";case "$top" in qkd_host_ctrl_packet|qkd_host_rx_class) opts="chparam -set STRAPPED 1 $top;";;esac
 "$y" -Q -T -p "read_verilog -sv $file; $opts hierarchy -top $top; proc; opt; memory_map; opt; write_json $out/$top.json" > "$out/$top.log" 2>&1
done
python3 - "$out" <<'PY'
import json,sys,pathlib
out=pathlib.Path(sys.argv[1]);rows={}
for p in out.glob('qkd_host_*.json'):
 d=json.loads(p.read_text());m=d['modules'][p.stem];n=0;types={}
 for c in m['cells'].values():
  t=c['type'];types[t]=types.get(t,0)+1
  if 'dff' in t.lower():n+=len(c['connections']['Q'])
 rows[p.stem]={'flop_bits':n,'cells':types}
(out/'census.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(rows,indent=2))
PY
