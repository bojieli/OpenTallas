#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=results/codex_hbm_sk_ce/shellrun
mkdir -p "$out"
N=rtl/hbm_accel/cores_split/sk_en_q4
src=(results/codex_hbm_sk_ce/tb_shell.sv results/codex_hbm_sk_ce/shells.sv "$N"/ot_hbm_hc_tail_unit_static_se.sv "$N"/ot_hgi_hc_tail_static_se.sv "$N"/ot_hdc_sinkhorn_se.sv "$N"/ot_hbm_hc_tail_rest_core_ce.sv rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
for mut in 1 0; do
 "$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GLAND=$mut --top-module tb_shell --Mdir "$out/obj$mut" "${src[@]}" > "$out/build$mut.log" 2>&1
 "$out/obj$mut/Vtb_shell" > "$out/result$mut.log"
 tail -3 "$out/result$mut.log"
done
