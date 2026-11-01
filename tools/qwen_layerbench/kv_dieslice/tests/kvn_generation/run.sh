#!/bin/bash
set -euo pipefail
R=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
O=${1:?output directory required}
mkdir -p "$O"
python3 - "$R" "$O" <<'PYCODE'
import re,sys
from pathlib import Path
r,o=map(Path,sys.argv[1:])
s=(r/'rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv').read_text()
mods=[]
for n in ['ot_qwen_d2d_kvn_tx','ot_qwen_d2d_kvn_rx']:
 m=re.search(r'(?m)^module '+n+r'\b.*?\bendmodule',s,re.S)
 assert m,n
 mods.append(m.group())
(o/'native.sv').write_text('\n'.join(mods))
PYCODE
cp "$(dirname "$0")/tb.sv" "$O/tb.sv"
cd "$O"
verilator --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir obj tb.sv native.sv >build.log 2>&1
./obj/Vtb >sim.log 2>&1
cat sim.log
