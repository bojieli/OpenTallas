#!/usr/bin/env bash
# Minimum full-width32-SM mux mechanism; remote admission belongs to launcher.
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal \
 --top-module tb_item9_mux32_ls -Mdir "$out/obj" \
 rtl/gpu_sys/ot_gpu_coll_mux.sv rtl/gpu_sys/ot_gpu_coll_mux_f12.sv \
 rtl/gpu_sys/ot_gpu_coll_mux_owner64.sv rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
 rtl/link/ot_link_afifo.sv results/rtl/hbm_item9_closure_20261005/tb_item9_mux32_ls.sv \
 > "$out/build.log" 2>&1
"$out/obj/Vtb_item9_mux32_ls" > "$out/run.log" 2>&1
python3 - "$out/run.log" <<'PY'
import re,sys
from pathlib import Path
s=Path(sys.argv[1]).read_text()
m=re.search(r'MUXLS owner64=1 nsm=32 cycles=2048 grants=(\d+) mismatches=(\d+)',s)
assert m and int(m[1])>=32 and int(m[2])==0, s
PY
