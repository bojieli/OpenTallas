#!/usr/bin/env bash
set -euo pipefail
out=${1:?output};mkdir -p "$out";out=$(realpath "$out")
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
D=rtl/hbm_accel/index/quad_1017
verilator --version
for m in 0 1 2 3; do
 verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GMUT=$m --top-module tb_idx_score_fault --Mdir "$out/obj$m" -o tb "$D/test/tb_idx_score_fault.sv" "$D/ot_hbm_idx_score_fault_static.sv" > "$out/build$m.log" 2>&1
 if "$out/obj$m/tb" > "$out/run$m.log" 2>&1;then
  test "$m" = 0 || { echo "IDX_SCORE_MUTANT_SURVIVED $m";exit 1; }
  grep '^IDX_SCORE_FAULT_PASS cases=37' "$out/run$m.log"
 else
  test "$m" != 0 || { tail -8 "$out/run$m.log";exit 1; }
  grep 'IDX_SCORE_FAULT_FAIL' "$out/run$m.log"
 fi
done
R=(rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_rf.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/gpu/ot_gpu_fadd.sv rtl/hdc/v41x/ot_hbm_idx_owned_native.sv rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv)
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD --top-module tb_idx_tail_score_fault --Mdir "$out/obj_tail" -o tb "$D/test/tb_idx_tail_score_fault.sv" "$D/ot_hbm_idx_score_fault_static.sv" "${R[@]}" > "$out/build_tail.log" 2>&1
"$out/obj_tail/tb" > "$out/run_tail.log" 2>&1
grep '^IDX_TAIL_FAULT_PASS cases=4' "$out/run_tail.log"
