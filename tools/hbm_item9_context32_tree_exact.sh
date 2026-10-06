#!/usr/bin/env bash
set -euo pipefail
out=$1
[[ "$out" = /* && ! -e "$out" ]]
mkdir -p "$out"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 2 -Wno-fatal \
 --top-module tb_item9_context32_tree -Mdir "$out/obj" \
 rtl/gpu_sys/ot_gpu_reset_ctrl.sv rtl/link/ot_link_afifo.sv rtl/gpu_sys/ot_gpu_cdc_fifo_oh.sv \
 rtl/gpu_sys/ot_gpu_coll_mux_f12.sv rtl/gpu_sys/ot_gpu_coll_mux_item9_tree.sv \
 rtl/gpu_sys/ot_gpu_coll_endpoint_item9_txctrl.sv rtl/gpu_sys/ot_gpu_coll_item9_context32_tree.sv \
 results/rtl/hbm_item9_closure_20261005/tb_item9_context32_tree.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_item9_context32_tree" > "$out/run.log" 2>&1
python3 - "$out" <<'PY'
from pathlib import Path
import hashlib,json,sys
p=Path(sys.argv[1]);s=(p/'run.log').read_text()
assert 'PASS TREE actual32 caller NL128 exact completed=32 TXrecords=128 RXrecords=256 cycles=789 added_cycles=0' in s,s
files=['rtl/gpu_sys/ot_gpu_coll_mux_item9_tree.sv','rtl/gpu_sys/ot_gpu_coll_endpoint_item9_txctrl.sv','rtl/gpu_sys/ot_gpu_coll_item9_context32_tree.sv','results/rtl/hbm_item9_closure_20261005/tb_item9_context32_tree.sv']
(p/'result.json').write_text(json.dumps(dict(verdict='PASS_TREE_ACTUAL32_GATHER',completed_callers=32,TX_records=128,RX_records=256,cycles=789,new_cycles=0,clocks_period_ps=833,baseline_reused='context32_exact_r1/result.json',unchanged_baseline_rerun=False,source_sha256={f:hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in files},contextual_SS_FF=False,adopted=False),indent=2)+'\n')
PY
