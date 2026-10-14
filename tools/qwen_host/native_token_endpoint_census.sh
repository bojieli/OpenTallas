#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output};mkdir -p "$out";out=$(cd "$out"&&pwd)
y=${YOSYS:-$HOME/.local/opentallas-tools/yosys/bin/yosys};[[ -x "$y" ]]||y=$(command -v yosys)
"$y" -Q -T -p "read_verilog -sv rtl/qwen_sys/host_20261013/qkd_host_native_token_endpoint.sv; chparam -set ENABLE_NATIVE 1 qkd_host_native_token_endpoint; hierarchy -top qkd_host_native_token_endpoint; proc; opt; write_json $out/net.json; stat" > "$out/yosys.log" 2>&1
python3 - "$out" <<'PY'
import sys,json,pathlib,hashlib
p=pathlib.Path(sys.argv[1]);m=json.loads((p/'net.json').read_text())['modules']['qkd_host_native_token_endpoint']
ff=sum(len(c['connections']['Q']) for c in m['cells'].values() if 'dff' in c['type'].lower())
src=pathlib.Path('rtl/qwen_sys/host_20261013/qkd_host_native_token_endpoint.sv')
j={'master':'qkd_host_native_token_endpoint','ENABLE_NATIVE':1,'default':0,'flop_bits':ff,'clock_entries':['ck'],'port_bits':sum(len(v['bits']) for v in m['ports'].values()),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'physical_status':'UNQUALIFIED_OUTLINE_PENDING_MAPPED_AREA_PIN_CAPACITY','identity':'TAG59 epoch16/stage6/token18/position13/segment6; sole allocator external','drain_flags':['kv_drained','vm_drained','collective_drained','host_drained']}
(p/'census.json').write_text(json.dumps(j,indent=2)+'\n');print(json.dumps(j,indent=2))
PY
