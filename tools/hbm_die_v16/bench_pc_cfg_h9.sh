#!/usr/bin/env bash
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
p=results/arch/hbm_pc_cfg_h8_1623/source
d=rtl/hbm_accel/loader/service_native
for mut in 0 1; do
  sed 's/module ot_hbm_svc_pc_ctrl_leaf_cfg_h9 #(/module ot_hbm_svc_pc_ctrl_leaf_cfg_faults #(/' "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9.sv" > "$out/candidate$mut.sv"
  if [ "$mut" = 1 ];then
    sed -i "s/pending_identity\[pending_wp\]<=head\[308:288\];/pending_identity[pending_wp^5'd1]<=head[308:288];/" "$out/candidate$mut.sv"
    cmp -s "$out/candidate0.sv" "$out/candidate1.sv" && { echo MUTANT_NOT_APPLIED; exit 3; }
  fi
  src=(rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv "$d/ot_hbm_svc_pin_skid2_h9.sv" "$p/ot_hbm_r14_stream_pc_strap_h7.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$p/reference.sv" "$out/candidate$mut.sv" "$p/miter_wrapper.sv")
  iverilog -g2012 -s tb -o "$out/m$mut.vvp" "${src[@]}" "$p/tb_hbm_pc_ctrl_leaf_faults_miter.sv" > "$out/m$mut.build.log" 2>&1
  if vvp "$out/m$mut.vvp" > "$out/m$mut.log" 2>&1; then
    test "$mut" = 0 || { echo PC_H8_MUTANT_SURVIVED; exit 1; }
    grep 'PC_CTRL_FAULTS_MITER PASS' "$out/m$mut.log"
  else
    test "$mut" = 1 || { cat "$out/m$mut.log"; exit 1; }
    grep -E 'mismatch|MISMATCH' "$out/m$mut.log"
    echo PC_H8_PENDING_ID_MUTANT_REJECTED
  fi
done
