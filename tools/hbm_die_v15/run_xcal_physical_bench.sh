#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
mut=${1:-0}; out=${2:?output directory}; mkdir -p "$out"
iverilog -g2012 -DMUT="$mut" -o "$out/bench" rtl/test/hbm_netlist_v16/tb_hbm_svc_sm_xcal.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_xcal.sv rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_issuer.sv rtl/hbm_accel/sm/static/ot_smh_calendar_static.sv physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
vvp -n "$out/bench" | tee "$out/bench.log"
grep -q 'XCAL_LOCKSTEP PASS' "$out/bench.log"
