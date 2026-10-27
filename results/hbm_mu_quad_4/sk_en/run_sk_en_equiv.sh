#!/bin/bash
# HBM-MU-QUAD-4 10-27: old (div-7 generated sink clock) vs new (clk + sk_en) lock-step bench, Verilator 5.050.
# usage: run_sk_en_equiv.sh OUT NSTA MUT_EN MODE SEED NL     (run from the repo root)
set -euo pipefail
out=$(realpath -m "$1"); nsta=$2; mut=$3; mode=$4; seed=$5; nl=$6; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
H=rtl/hbm_accel/generic/peers/static_hc; N=rtl/hbm_accel/cores_split/sk_en_q4
src=(results/hbm_mu_quad_4/sk_en/tb_sk_en_equiv.sv $H/ot_hbm_hc_tail_unit_static_s.sv $H/ot_hgi_hc_tail_static_s.sv
 rtl/hdc/v41/ot_hdc_sinkhorn_s.sv $N/ot_hbm_hc_tail_unit_static_se.sv $N/ot_hgi_hc_tail_static_se.sv $N/ot_hdc_sinkhorn_se.sv
 rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
tag=nsta${nsta}_mut${mut}_mode${mode}_seed${seed}
sha256sum "${src[@]}" "$0" > "$out/sources_$tag.sha256"
obj="$out/obj_nsta${nsta}_mut${mut}"
[ -x "$obj/Vtb_sk_en_equiv" ] || "$vl" --binary --timing -j 16 -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  -GNSTA=$nsta -GMUT_EN=$mut --top-module tb_sk_en_equiv --Mdir "$obj" "${src[@]}" > "$out/build_nsta${nsta}_mut${mut}.log" 2>&1 \
  || { tail -30 "$out/build_nsta${nsta}_mut${mut}.log"; exit 3; }
"$obj/Vtb_sk_en_equiv" +NL=$nl +SEED=$seed +MODE=$mode > "$out/run_$tag.log" 2>&1 || true
grep -E "SK_EN (PASS|FAIL)|MISMATCH|FAULT" "$out/run_$tag.log" | head -6
