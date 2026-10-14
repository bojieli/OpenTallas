#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?out};mkdir -p "$out";out=$(cd "$out"&&pwd)
y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x "$y" ]]||y=$(command -v yosys)
for top in qkd_host_qm_ingress16 qkd_host_qm_credit_pacer;do
 "$y" -Q -T -p "read_verilog -sv rtl/qwen_sys/host_20261013/$top.sv; hierarchy -top $top; proc; opt; memory_map; opt; write_json $out/$top.json" > "$out/$top-build.log" 2>&1
done
python3 - "$out" <<'PY'
import json,sys,pathlib
p=pathlib.Path(sys.argv[1]);roots={}
for top in ['qkd_host_qm_ingress16','qkd_host_qm_credit_pacer']:
 m=json.loads((p/(top+'.json')).read_text())['modules'][top]
 roots[top]=sum(len(c['connections']['Q']) for c in m['cells'].values() if 'dff' in c['type'].lower())
j={'status':'SOURCE_CENSUS_ONLY_PHYSICAL_UNQUALIFIED','flop_roots':roots,'dedicated_W546_CDC_instances':2,'entry_clocks':{'qkd_host_qm_ingress16':'packet_core833','qkd_host_qm_credit_pacer':'QM_host1000'},'raw_count_bus_crossing':False}
(p/'census.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
