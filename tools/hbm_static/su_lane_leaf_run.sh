#!/usr/bin/env bash
# Exact bench of one hardened static-SU lane leaf (physical wrapper) on its production lane shape (tb_su_static_lane_leaf).
# Usage: su_lane_leaf_run.sh OUT LEAF_TOP MLAT ALAT LEAF LANE [MUT]   MUT: ADDR | DATA | PHASE (expect FAIL), empty = positive
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); top=$2; mlat=$3; alat=$4; leaf=$5; lane=$6; mut=${7:-}
mkdir -p "$out"
[ -f "$out/vec/control.mem" ] || python3 tools/hbm_static/su_arith_compile.py "$out/vec" > "$out/vec.log"
S=rtl/hbm_accel/generic/adapters/static_su
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
obj="$out/obj_$top"
if [ ! -x "$obj/Vtb_su_static_lane_leaf" ]; then
"$vl" --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_su_static_lane_leaf \
 +define+LEAF_TOP="$top" -GMLAT="$mlat" -GALAT="$alat" -GLEAF="$leaf" -GLANE="$lane" --Mdir "$obj" \
 $S/arithmetic/tb_su_static_lane_leaf.sv $S/arithmetic/${top}.sv $S/arithmetic/ot_hbm_su_static_lane.sv \
 $S/arithmetic/ot_hbm_su_static_ins.sv $S/data_store/ot_hbm_su_static_pinned_bank.sv $S/data_store/ot_hbm_su_static_data_store.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv \
 rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/build_$top.log" 2>&1
fi
"$obj/Vtb_su_static_lane_leaf" +DIR="$out/vec" ${mut:++MUT_$mut}
