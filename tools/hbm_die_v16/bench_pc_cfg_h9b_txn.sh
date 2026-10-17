#!/usr/bin/env bash
# H9b transaction equivalence vs H9 (tb_hbm_pc_h9b_txn.sv). Usage: bench_pc_cfg_h9b_txn.sh OUT [RMUT]
set -euo pipefail
out=${1:?output}; m=${2:-0}; mkdir -p "$out"; d=rtl/hbm_accel/loader/service_native
iverilog -g2012 -s tb -Ptb.RMUT=$m -o "$out/m$m.vvp" rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv \
 "$d/ot_hbm_svc_pin_skid2_h9.sv" "$d/ot_hbm_svc_ring_h9b.sv" "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9.sv" \
 "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv" results/arch/hbm_pc_cfg_h8_1623/source/ot_hbm_r14_stream_pc_strap_h7.sv \
 rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 "$d/tb_hbm_pc_h9b_txn.sv" > "$out/m$m.build.log" 2>&1 || { cat "$out/m$m.build.log"; exit 2; }
vvp "$out/m$m.vvp" 2>&1 | tee "$out/m$m.log"
