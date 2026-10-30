#!/bin/bash
set -e
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
R=/srv/opentallas-scratch2/claude/codex-hbm-residual-1030
W=/srv/opentallas-scratch2/claude/wt/codex-hbm-residual-1030
iverilog -g2012 -s tb -o "$R/query/lockstep.vvp" "$R/lockstep.sv" "$R/vm_query_rt_views.sv" "$W/rtl/hbm_accel/index/ot_hbm_idx_vm_query_static_n12.sv" "$W/rtl/hbm_accel/index/ot_hbm_idx_vm_query_static.sv" "$W/rtl/hbm_accel/index/ot_hbm_idx_vm_static.sv" "$W/rtl/lib/ot_rst_relay.sv"
vvp "$R/query/lockstep.vvp" | tee "$R/query/lockstep.log"
