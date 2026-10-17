#!/usr/bin/env bash
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
d=rtl/hbm_accel/loader/service_native
for m in 0 1;do
 cp "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h8.sv" "$out/candidate$m.sv"
 if [ "$m" = 1 ];then
  sed -i 's/if(lrst_n \&\& pending_count<32)/if(lrst_n)/' "$out/candidate$m.sv"
  cmp -s "$out/candidate0.sv" "$out/candidate1.sv" && { echo MUTANT_NOT_APPLIED;exit 3; }
 fi
 iverilog -g2012 -s tb -o "$out/m$m.vvp" rtl/lib/ot_rst_relay.sv results/arch/hbm_pc_cfg_h8_1623/source/ot_hbm_r14_stream_pc_strap_h7.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$out/candidate$m.sv" "$d/tb_hbm_pc_cfg_h8_full.sv" > "$out/m$m.build.log" 2>&1
 if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1;then
  test "$m" = 0 || { echo PC_H8_FULL_MUTANT_SURVIVED;exit 1; }
  grep 'PC_H8_FULL PASS' "$out/m$m.log"
 else
  test "$m" = 1 || { cat "$out/m$m.log";exit 1; }
  grep 'PC_H8_FULL_LIVE_ENTRY_OVERWRITTEN' "$out/m$m.log"
  echo PC_H8_FULL_GUARD_MUTANT_REJECTED
 fi
done
