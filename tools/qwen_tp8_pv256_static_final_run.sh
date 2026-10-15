#!/usr/bin/env bash
# Actual RTL arithmetic, compiled input/output slots. Declared component inputs
# do not qualify integrated Z/reciprocal or physical root phases. Use ot-run.
set -euo pipefail
vectors=$(realpath "${1:?declared final-join vector directory}")
out=$(realpath -m "${2:?fresh result directory}")
root=$(cd "$(dirname "$0")/.." && pwd)
[[ ! -e "$out" ]] || { echo 'Output must be fresh' >&2; exit 2; }
mkdir -p "$out"
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
vroot=${VERILATOR_ROOT:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator}/include
src=(rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv
 rtl/test/nearhbm/ot_qwen_tp8_pv256_finalize_tb.sv rtl/hdc/ot_hdc_fp32_add_lat.sv
 rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv)
for i in "${!src[@]}"; do src[$i]="$root/${src[$i]}"; done
tb="$root/rtl/test/nearhbm/tb_qwen_tp8_pv256_finalize.cpp"
printf '%s\n' '`verilator_config' 'hier_block -module "ot_qwen_tp8_pv_join16_static"' \
 'hier_block -module "ot_hdc_fp32_add_lat"' 'hier_block -module "ot_hdc_fp32_mul_lat"' > "$out/native.vlt"
sha256sum "${src[@]}" "$tb" "$0" > "$out/source.sha256"
"$vl" --cc --hierarchical --build -j "${CPP_JOBS:-4}" -Wno-fatal \
 --top-module ot_qwen_tp8_pv256_finalize_tb -GSTATIC_SCHEDULE=1 \
 --Mdir "$out/obj" "$out/native.vlt" "${src[@]}" > "$out/build.log" 2>&1
mapfile -t libs < <(find "$out/obj" -name '*.a' ! -name libverilated.a | sort)
g++ -O1 -std=c++20 -pthread -DPV_STATIC -I"$out/obj" -I"$vroot" -I"$vroot/vltstd" \
 "$tb" -Wl,--start-group "${libs[@]}" -Wl,--end-group \
 "$vroot/verilated.cpp" "$vroot/verilated_threads.cpp" -o "$out/check" > "$out/link.log" 2>&1
for mode in steady epoch reciprocal_epoch data reciprocal_data restart missing0 missing1 missing_r late0 early1 output_late; do
 "$out/check" "$vectors" "$mode" > "$out/$mode.json"
done
sha256sum "$out/check" "$vectors"/*.bin > "$out/binary-and-input.sha256"
