#!/usr/bin/env bash
# H-NETLIST/cp1: ot_static_cmd_target bench through the real host ingress.  run_static_cmd_target.sh OUT_DIR
# MUT 0 must PASS; MUT 1 (late fire) and MUT 2 (target id ignored) must FAIL.
set -uo pipefail
cd "$(dirname "$0")/../../.."
out=${1:?output directory}; mkdir -p "$out"
D=rtl/hbm_accel/host_static_20261015
SRC="$D/tb_static_cmd_target.sv $D/ot_static_cmd_target.sv $D/ot_hbm_host_static_ingress.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv"
rc=0
for m in 0 1 2; do
  iverilog -g2012 -DMUT=$m -o "$out/sim$m" $SRC > "$out/build$m.log" 2>&1 || { echo "BUILD FAIL mut=$m"; rc=1; continue; }
  vvp -n "$out/sim$m" > "$out/run$m.log" 2>&1; r=$(tail -1 "$out/run$m.log"); echo "$r"
  case "$m:$r" in 0:*PASS*|1:*FAIL*|2:*FAIL*) ;; *) rc=1;; esac
done
[ $rc = 0 ] && echo "RUN_STATIC_CMD_TARGET PASS (positive PASS, 2 mutants FAIL)" || echo "RUN_STATIC_CMD_TARGET FAIL"
exit $rc
