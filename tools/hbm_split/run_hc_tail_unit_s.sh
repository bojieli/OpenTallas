#!/bin/bash
# HBM-P5-RTLB 10-23: hc tail unit split twin vs pinned lock-step (Verilator 5.050). usage: run_hc_tail_unit_s.sh OUT [SMUT] [NL] [SEED]
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd); cd "$root"
out=$(realpath -m "${1:?out}"); smut=${2:-0}; nl=${3:-40}; seed=${4:-1}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
H=rtl/hbm_accel/generic/peers/static_hc
src=(rtl/test/tb_hbm_hc_tail_unit_s.sv $H/ot_hbm_hc_tail_unit_static.sv $H/ot_hbm_hc_tail_unit_static_s.sv
 $H/ot_hgi_hc_tail_static.sv $H/ot_hgi_hc_tail_static_s.sv rtl/hdc/v41/ot_hdc_sinkhorn.sv rtl/hdc/v41/ot_hdc_sinkhorn_s.sv
 rtl/hdc/v41/ot_hdc_sk_arith.sv rtl/hdc/v41/ot_hdc_sk_recip_rom.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv)
sha256sum "${src[@]}" "$0" > "$out/sources.sha256"
obj="$out/obj_smut$smut"
"$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -GSMUT=$smut \
  --top-module tb_hbm_hc_tail_unit_s --Mdir "$obj" "${src[@]}" > "$out/build_smut$smut.log" 2>&1 || { tail -20 "$out/build_smut$smut.log"; exit 3; }
"$obj/Vtb_hbm_hc_tail_unit_s" +NL=$nl +SEED=$seed > "$out/run_smut$smut.log" 2>&1 || true
grep -E "TAIL_UNIT_S|MISMATCH|FAULT" "$out/run_smut$smut.log" | head -8
grep -q "TAIL_UNIT_S PASS" "$out/run_smut$smut.log"
