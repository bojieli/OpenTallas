#!/usr/bin/env bash
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
python3 tools/hbm_die_v16/bench_pc_cfg_all.py "$out/tb.sv"
d=rtl/hbm_accel/loader/service_native
for m in 0 1 2; do
  iverilog -g2012 -s tb -Ptb.MUT=$m -o "$out/m$m.vvp" "$out/tb.sv" rtl/lib/ot_rst_relay.sv "$d/ot_hbm_svc_pc_ctrl_leaf.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h8.sv" results/arch/hbm_pc_cfg_h8_1623/source/ot_hbm_r14_stream_pc_strap_h7.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/m$m.build.log" 2>&1
  if vvp "$out/m$m.vvp" > "$out/m$m.log" 2>&1; then
    test "$m" = 0 || { echo "PC_CFG_MUTANT_SURVIVED $m"; exit 1; }
    grep 'PC_CFG_ALL32 PASS' "$out/m$m.log"
  else
    test "$m" != 0 || { cat "$out/m$m.log"; exit 1; }
    grep -E 'PC_CFG_(MISMATCH|ROW_MISMATCH|COL_MISMATCH)' "$out/m$m.log"
    echo "PC_CFG_MUTANT_REJECTED mut=$m"
  fi
done
