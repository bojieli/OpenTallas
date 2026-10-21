#!/usr/bin/env bash
# HBM-KIND8: lockstep bench of the k8 native-32 multiplier / exp vs the released units (Verilator 5.050).
# Usage: su_k8_units_run.sh OUT [MUT_MUL|MUT_EXP|MUT_ADD|MUT_DIV] [N]   (HBM-KIND9: + n32 adder lockstep)
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mut=${2:-}; n=${3:-400000}
mkdir -p "$out"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
K=rtl/hbm_accel/generic/adapters/static_su/arithmetic/k8
if [ ! -x "$out/obj/Vtb_k8_units" ]; then
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_k8_units +define+OT_QMUL4_INCUT +define+OT_SU_SYNC_RST \
 +define+OT_FP_DATA_NORST --Mdir "$out/obj" $K/tb_k8_units.sv $K/ot_hdc_fp32_mul_lat_k8.sv $K/ot_hdc_fastfp_lat_k8.sv $K/ot_hdc_v41x_exp_k8.sv $K/ot_hdc_v41x_fdiv_k8.sv $K/ot_k9_fam.sv \
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_add_n32.sv \
 rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_sfu.sv > "$out/build.log" 2>&1
fi
"$out/obj/Vtb_k8_units" +N=$n ${mut:++$mut}
