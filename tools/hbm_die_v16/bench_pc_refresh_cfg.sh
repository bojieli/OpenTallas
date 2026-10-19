#!/usr/bin/env bash
# HBM-TIE 10-17: refresh_reload producer (ot_hbm_pc_refresh_cfg) feeding 32 die PC masters (H9b) vs the strap miter + 4 mutants.
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
python3 tools/hbm_die_v16/bench_pc_refresh_cfg.py "$out/tb.sv"
d=rtl/hbm_accel/loader/service_native
for m in 0 1 2 3 4; do
  iverilog -g2012 -s tb -Ptb.MUT=$m -o "$out/m$m.vvp" "$out/tb.sv" "$d/ot_hbm_pc_refresh_cfg.sv" "$d/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b.sv" \
    "$d/ot_hbm_svc_ring_h9b.sv" "$d/ot_hbm_svc_pin_skid2_h9.sv" rtl/lib/ot_rst_relay.sv rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/m$m.build.log" 2>&1
  if vvp -n "$out/m$m.vvp" > "$out/m$m.log" 2>&1; then
    test "$m" = 0 || { echo "PC_REFCFG_MUTANT_SURVIVED $m"; exit 1; }
    grep 'PC_REFCFG PASS' "$out/m$m.log"
  else
    test "$m" != 0 || { cat "$out/m$m.log"; exit 1; }
    grep -oE 'PC_REFCFG_[A-Z_]+[^"]*' "$out/m$m.log" | head -1
    echo "PC_REFCFG_MUTANT_REJECTED mut=$m"
  fi
done
