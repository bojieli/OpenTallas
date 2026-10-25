#!/bin/bash
# HBM-HC 2026-10-24: B2 128-lane half engine (ot_hbm_hc_qeng_static W 128, TERM7 1, die params) vs two UNCHANGED 64-lane
# quarter engines + the 7th FP add (tb_hbm_hc_half128.sv).  Usage (repo root of the branch):
#   run_hc_half128.sh OUT [MUT] [BASE]     MUT 0 must print HC_HALF128 ... PASS; MUT 1 3 4 5 6 7 must FAIL.
#   BASE = commit with the 64-lane originals (default fc76a2c42).  Build: Verilator --hierarchical, --x-initial unique
#   (owner decision 13: datapath flops carry no reset -> uninitialised datapath state must not reach a valid output).
set -uo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); mut=${2:-0}; base=${3:-fc76a2c42}; mkdir -p "$out/ref"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
ren='s/\bot_hbm_hc_qcen_static\b/&_orig/g; s/\bot_hbm_hc_bankq_core\b/&_orig/g; s/\bot_hbm_hc_bankq_static\b/&_orig/g;
     s/\bot_hbm_hc_bankq_ft_static\b/&_orig/g; s/\bot_hbm_hc_bankq0_static\b/&_orig/g; s/\bot_hbm_hc_qeng_static\b/&_orig/g'
for f in ot_hbm_hc_qcen_static ot_hbm_hc_bankq_static ot_hbm_hc_qeng_static; do
  git show $base:$H/$f.sv | sed -E "$ren" > "$out/ref/${f}_orig.sv" || exit 2; done
src=($H/tb_hbm_hc_half128.sv $H/ot_hbm_hc_qcen_static.sv $H/ot_hbm_hc_bankq_static.sv $H/ot_hbm_hc_bankq_term_static.sv
 $H/ot_hbm_hc_qeng_static.sv "$out"/ref/*.sv $H/ot_hbm_hc_bank_static.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv rtl/hbm_accel/die_glue/ot_hbm_rly.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
printf '`verilator_config\nhier_block -module "ot_hdc_v41x_hcp_lanes"\nhier_block -module "ot_hbm_hc_bank_static"\n' > "$out/hier.vlt"
"$vl" --binary --timing --hierarchical -j ${HC_BUILD_JOBS:-16} -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN \
  --x-assign unique --x-initial unique --top-module tb_hbm_hc_half128 -GMUT=$mut +define+OT_FP_DATA_NORST \
  -Mdir "$out/obj" -o Vhalf "$out/hier.vlt" "${src[@]}" > "$out/build.log" 2>&1 || { tail -20 "$out/build.log"; echo "HC_HALF128 MUT=$mut BUILD FAIL"; exit 3; }
"$out/obj/Vhalf" +SEED=${SEED:-7} +verilator+seed+${SEED:-7} +verilator+rand+reset+2 > "$out/run.log" 2>&1; rc=$?
grep -E "^(HC_HALF128|MISMATCH|FAULT)" "$out/run.log" | head -12
rm -rf "$out/obj"
grep -q "^HC_HALF128 MUT=$mut .* PASS$" "$out/run.log"
