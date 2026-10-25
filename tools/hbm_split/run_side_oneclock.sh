#!/bin/bash
# HBM-P5-RTLB 10-23: side split twin lock-step bench (Verilator 5.050). usage: run_side_s.sh OUT [SMUT] [N] [SEED]
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); smut=${2:-0}; n=${3:-20000}; seed=${4:-1}; mkdir -p "$out"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; [ -x "$vl" ] || vl=verilator
S=rtl/hbm_accel/generic/adapters/static_su
src=($S/arithmetic/ot_hbm_su_static_side.sv $S/arithmetic/ot_hbm_su_static_side_s.sv
 rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat_c12.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv
 rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_side_rest_core.sv
 rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg/ot_hbm_su_side_softplus_core.sv
 rtl/test/hbm_accel/generic/tb_hbm_side_oneclock.sv)
sha256sum "${src[@]}" "$0" > "$out/sources.sha256"
obj="$out/obj_smut$smut"
[ -x "$obj/Vtb_hbm_side_oneclock" ] || "$vl" --binary --timing -j "${JOBS:-8}" -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD \
  --top-module tb_hbm_side_oneclock --Mdir "$obj" "${src[@]}" > "$out/build_smut$smut.log" 2>&1 || { tail -20 "$out/build_smut$smut.log"; exit 3; }
"$obj/Vtb_hbm_side_oneclock" ${MUT_ARGS:-} > "$out/side_s_smut${smut}_s$seed.log" 2>&1 || true
grep -E "SIDE_ONECLOCK" "$out/side_s_smut${smut}_s$seed.log" | head -6
grep -q "SIDE_ONECLOCK PASS" "$out/side_s_smut${smut}_s$seed.log"
