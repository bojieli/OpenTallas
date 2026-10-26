#!/usr/bin/env bash
# SFU-lane full N512 bench (exp/sigmoid/SiLU/divider on the 32 SFU lanes per quarter); see su_arith_sfu_compile.py.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1")
mkdir -p "$out"
mlat=${SU_ARITH_MLAT:-3}
alat=${SU_ARITH_ALAT:-3}
leaf=${SU_ARITH_LEAF:-0}
python3 tools/hbm_static/su_arith_sfu_compile.py "$out/vectors" "$mlat" "$alat" "$leaf"
printf 'MLAT=%s ALAT=%s LEAF=%s\n' "$mlat" "$alat" "$leaf" > "$out/native_profile.txt"
nops=$(python3 -c 'import json,sys;print(len(json.load(open(sys.argv[1]))["ops"]))' "$out/vectors/programme.json")
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$vl" --binary --timing --hierarchical -O1 -j 4 -CFLAGS -O0 -Wno-fatal \
 --top-module tb_su_static_arithmetic_sfu -GNOPS="$nops" -GMLAT="$mlat" -GALAT="$alat" -GLEAF="$leaf" --Mdir "$out/obj" \
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_ins.sv \
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_lane.sv \
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/ot_hbm_su_static_arithmetic.sv \
 rtl/hbm_accel/generic/adapters/static_su/arithmetic/tb_su_static_arithmetic_sfu.sv \
 rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_data_store.sv \
 rtl/hbm_accel/generic/adapters/static_su/data_store/ot_hbm_su_static_pinned_bank.sv \
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv \
 rtl/hdc/v41x/ot_hdc_v41x_sfu.sv \
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv \
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv \
 rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv \
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv \
 rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v \
 > "$out/build.log" 2>&1
bash tools/hbm_static/su_arith_validate.sh "$out/obj/Vtb_su_static_arithmetic_sfu" "$out/vectors" "$out/validation"
