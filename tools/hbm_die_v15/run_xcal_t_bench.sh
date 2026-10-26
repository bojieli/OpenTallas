#!/usr/bin/env bash
# H-SM svc helper 2026-10-16: bench of the hardened xcal wrapper ot_hbm_svc_sm_xcal_t through the real host ingress.
#   run_xcal_t_bench.sh MUT OUT_DIR   (MUT 0 must print XCAL_T_LOCKSTEP PASS; 1..4 must FAIL)
set -euo pipefail
cd "$(dirname "$0")/../.."
mut=${1:-0}; out=${2:?output directory}; mkdir -p "$out"
H=rtl/hbm_accel/host_static_20261015; N=rtl/hbm_accel/loader/service_native
iverilog -g2012 -DMUT="$mut" -s tb_hbm_svc_sm_xcal_t -o "$out/bench" rtl/test/hbm_netlist_v16/tb_hbm_svc_sm_xcal_t.sv \
  $N/ot_hbm_svc_sm_xcal_t.sv $N/ot_hbm_svc_sm_xcal.sv $N/ot_hbm_svc_sm_issuer.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv \
  $H/ot_static_cmd_target.sv $H/ot_hbm_host_static_ingress.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
vvp -n "$out/bench" | tee "$out/bench.log"
grep -q 'XCAL_T_LOCKSTEP PASS' "$out/bench.log"
