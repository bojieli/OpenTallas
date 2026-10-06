#!/usr/bin/env bash
# Minimum full-width32-SM mux mechanism; remote admission belongs to launcher.
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal \
 --top-module tb_item9_mux32_tree_ls -Mdir "$out/obj" \
 rtl/gpu_sys/ot_gpu_coll_mux.sv rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
 rtl/gpu_sys/ot_gpu_coll_mux_item9_tree.sv rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
 rtl/link/ot_link_afifo.sv results/rtl/hbm_item9_closure_20261005/tb_item9_mux32_tree_ls.sv \
 > "$out/build.log" 2>&1
"$out/obj/Vtb_item9_mux32_tree_ls" > "$out/run.log" 2>&1
python3 - "$out/run.log" <<'PY'
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
m=re.search(r'MUXLS owner64=1 nsm=32 cycles=2048 grants=(\d+) mismatches=(\d+)',s)
assert m and int(m[1])>=32 and int(m[2])==0, s
PY
python3 - "$out" <<'PYREC'
import hashlib,json,sys,re
from pathlib import Path
p=Path(sys.argv[1]);m=re.search(r'cycles=(\d+) grants=(\d+) mismatches=(\d+)',(p/'run.log').read_text());assert m and int(m[3])==0
files=['rtl/gpu_sys/ot_gpu_coll_mux_item9_tree.sv','results/rtl/hbm_item9_closure_20261005/tb_item9_mux32_tree_ls.sv']
(p/'result.json').write_text(json.dumps(dict(verdict='PASS_TREE_FULL32_LOCKSTEP',NSM=32,NL=128,cycles=int(m[1]),grants=int(m[2]),new_cycles=0,source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},adopted=False),indent=2)+'\n')
PYREC
