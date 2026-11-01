#!/bin/bash
set -euo pipefail
D=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$D/../.." && pwd)
for f in ot_hbm_svc_vm_kshare_splitstrap.sv ot_hbm_svc_async_fifo.sv ot_hbm_svc_pc_ctrl_leaf.sv ot_hbm_svc_ring_h9b_ff.sv; do
  test -f "$D/$f" || cp "$REPO/rtl/hbm_accel/loader/service_native/$f" "$D/$f"
done
test -f "$D/ot_reset_sync.sv" || cp "$REPO/rtl/lib/ot_reset_sync.sv" "$D/ot_reset_sync.sv"
vl=$HOME/.local/opentallas-tools/bin/verilator
"$vl" --binary --timing -j 4 -O1 -Wno-fatal -Wno-lint -Wno-style -Werror-WIDTH -Werror-SELRANGE --top-module tb_kshare_binary --Mdir "$D/obj" -o sim "$D/tb.sv" "$D/gold.sv" "$D/ot_hbm_svc_vm_kshare_splitstrap.sv" "$D/ot_hbm_svc_async_fifo.sv" "$D/ot_hbm_svc_pc_ctrl_leaf.sv" "$D/ot_hbm_svc_ring_h9b_ff.sv" "$D/ot_reset_sync.sv" > "$D/build.log" 2>&1
"$D/obj/sim" > "$D/result.log" 2>&1
cat "$D/result.log"
