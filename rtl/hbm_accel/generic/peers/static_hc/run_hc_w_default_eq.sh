#!/bin/bash
# HBM-HC 2026-10-24: default (W 64) bit-exactness of the W-parameterised HC hub / bank masters vs the unchanged originals
# (tb_hbm_hc_w_default_eq.sv, random lockstep, every output every edge).  Usage (repo root of the branch):
#   run_hc_w_default_eq.sh OUT [BASE] [TERMREF]
#     BASE    = commit holding the originals (default fc76a2c42 = claude/hbm-bind-1024r branch point)
#     TERMREF = commit of the scoped die terminal bank hcbt.sv (default 4418ce6ff)
# Builds MUTB 0 (must PASS) and bench mutants 1..3 (must FAIL) in parallel; prints HC_W_DEFAULT_EQ_GATE PASS|FAIL.
set -uo pipefail
root=$(cd "$(dirname "$0")/../../../../.." && pwd); cd "$root"
out=$(realpath -m "${1:?OUT}"); base=${2:-fc76a2c42}; tref=${3:-4418ce6ff}; mkdir -p "$out/ref"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
ren='s/\bot_hbm_hc_qhub_static\b/&_orig/g; s/\bot_hbm_hc_qcen_static\b/&_orig/g; s/\bot_hbm_hc_bankq_core\b/&_orig/g;
     s/\bot_hbm_hc_bankq_static\b/&_orig/g; s/\bot_hbm_hc_bankq_ft_static\b/&_orig/g; s/\bot_hbm_hc_bankq0_static\b/&_orig/g;
     s/\bot_hbm_hc_qeng_static\b/&_orig/g'
for f in ot_hbm_hc_qhub_static ot_hbm_hc_qcen_static ot_hbm_hc_bankq_static ot_hbm_hc_qeng_static; do
  git show $base:$H/$f.sv | sed -E "$ren" > "$out/ref/${f}_orig.sv" || exit 2; done
git show $tref:rtl/hbm_accel/die_glue/scoped_d4g/hcbt.sv | sed -E 's/\bot_hbm_hc_bankq_term_static\b/&_orig/g' > "$out/ref/hcbt_orig.sv" || exit 2
src=($H/tb_hbm_hc_w_default_eq.sv $H/ot_hbm_hc_qhub_static.sv $H/ot_hbm_hc_qcen_static.sv $H/ot_hbm_hc_bankq_static.sv
 $H/ot_hbm_hc_bankq_term_static.sv $H/ot_hbm_hc_qeng_static.sv "$out"/ref/*.sv
 $H/ot_hbm_hc_q_static.sv $H/ot_hgi_hc_residual_vm_static.sv $H/ot_hgi_hc_gathered_mix_reader_static.sv $H/ot_hgi_hc_result_vm_static.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static.sv rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv
 $H/ot_hbm_hc_bank_static.sv rtl/hdc/v41x/ot_hdc_v41x_hcp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/lib/ot_rst_relay.sv
 rtl/hbm_accel/die_glue/ot_hbm_rly.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v)
printf '`verilator_config\nhier_block -module "ot_hdc_v41x_hcp_lanes"\nhier_block -module "ot_hbm_hc_bank_static"\n' > "$out/hier.vlt"
J=()
for m in 0 1 2 3; do
  ( "$vl" --binary --timing --hierarchical -j ${HC_BUILD_JOBS:-8} -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --x-initial 0 \
      --top-module tb_hbm_hc_w_default_eq -GMUTB=$m +define+OT_FP_DATA_NORST -Mdir "$out/obj$m" -o Veq \
      "$out/hier.vlt" "${src[@]}" > "$out/build$m.log" 2>&1 && "$out/obj$m/Veq" > "$out/run$m.log" 2>&1; rm -rf "$out/obj$m" ) & J+=($!)
done
for j in "${J[@]}"; do wait $j; done
v=PASS
grep -q "^HC_W_DEFAULT_EQ MUTB=0 .* PASS$" "$out/run0.log" || v=FAIL
for m in 1 2 3; do grep -q "^HC_W_DEFAULT_EQ MUTB=$m .* FAIL$" "$out/run$m.log" || v=FAIL; done
for m in 0 1 2 3; do grep -h "^HC_W_DEFAULT_EQ" "$out/run$m.log" || { echo "MUTB=$m no result"; tail -5 "$out/build$m.log"; }; done
echo "HC_W_DEFAULT_EQ_GATE $v"
[ $v = PASS ]
