#!/usr/bin/env bash
# HBM-TIE 10-17: top-k K issued from the IDX collar operand row (col_idx.prm[1459:1450]) into the die selector, + 3 mutants.
set -euo pipefail
out=${1:?output}; mkdir -p "$out"
for m in 0 1 2 3; do
  iverilog -g2012 -s tb -Ptb.MUT=$m -o "$out/m$m.vvp" rtl/test/hbm_idx_static/tb_idx_k_issuer.sv \
    rtl/hbm_accel/host_static_20261015/ot_hbm_static_cfg_collar.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv \
    physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v > "$out/m$m.build.log" 2>&1
  if vvp -n "$out/m$m.vvp" > "$out/m$m.log" 2>&1; then
    test "$m" = 0 || { echo "IDX_K_MUTANT_SURVIVED $m"; exit 1; }
    grep 'IDX_K_ISSUER PASS' "$out/m$m.log"
  else
    test "$m" != 0 || { cat "$out/m$m.log"; exit 1; }
    grep -oE 'IDX_K_[A-Z_]+[^"]*' "$out/m$m.log" | head -1
    echo "IDX_K_MUTANT_REJECTED mut=$m"
  fi
done
