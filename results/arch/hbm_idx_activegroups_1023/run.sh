#!/bin/bash
set -euo pipefail
V=/opt/verilator-5.050/bin/verilator
[ -x "$V" ] || V=$(command -v verilator)
SRC="rtl/hbm_accel/index/ot_hbm_idx_selector_static.sv rtl/hbm_accel/index/ot_hbm_idx_selector_static_sel.sv rtl/hbm_accel/index/tb/tb_hbm_idx_selector_activegroups_eq.sv physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v rtl/lib/ot_rst_relay.sv"
for m in 0 10 11; do
 "$V" --binary -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb_hbm_idx_selector_activegroups_eq -GSMUT=$m -GNRUN=2 -Mdir obj$m $SRC > build$m.log 2>&1
 if ./obj$m/Vtb_hbm_idx_selector_activegroups_eq >run$m.log 2>&1; then
  [ "$m" = 0 ] || { echo MUTANT_SURVIVED_$m; exit 1; }
  grep 'TB_ACTIVE_GROUPS_EQ PASS' run$m.log
 else
  [ "$m" != 0 ] || { tail -20 run$m.log; exit 1; }
  grep 'TB_ACTIVE_GROUPS_EQ FAIL' run$m.log
 fi
done
