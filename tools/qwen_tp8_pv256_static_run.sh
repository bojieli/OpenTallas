#!/usr/bin/env bash
# Native arithmetic/SRAM component proof; run through ot-run. Equal-phase test
# roots do not qualify the final physical clock insertion profile.
set -euo pipefail
vectors=$(realpath "${1:?declared PV vector directory}")
out=$(realpath -m "${2:?fresh output directory}")
root=$(cd "$(dirname "$0")/.." && pwd)
[[ ! -e "$out" ]] || { echo 'Output must be fresh' >&2; exit 2; }
mkdir -p "$out"
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
vroot=${VERILATOR_ROOT:-$HOME/.local/opentallas-tools/verilator-5.050/share/verilator}/include
src=(rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv
 rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fastfp.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv
 rtl/test/nearhbm/ot_qwen_tp8_pv256_pair_tb.sv)
for i in "${!src[@]}"; do src[$i]="$root/${src[$i]}"; done
tb="$root/rtl/test/nearhbm/tb_qwen_tp8_pv256_pair.cpp"
printf '%s\n' '`verilator_config' 'hier_block -module "ot_qwen_tp8_pv256_slice"' \
 'hier_block -module "ot_hdc_fp32_add_lat"' > "$out/native.vlt"
sha256sum "${src[@]}" "$tb" "$0" > "$out/source.sha256"
cd "$out"
for pair in 0 1; do
 "$vl" --cc --hierarchical --build -j "${CPP_JOBS:-4}" -Wno-fatal \
  --top-module ot_qwen_tp8_pv256_pair_tb -GPAIR="$pair" -GTREE=1 -GSTATIC_SCHEDULE=1 \
  --Mdir "$out/obj-$pair" "$out/native.vlt" "${src[@]}" > "build-$pair.log" 2>&1
 mapfile -t libs < <(find "$out/obj-$pair" -name '*.a' ! -name libverilated.a | sort)
 g++ -O1 -std=c++20 -pthread -DPV_TREE -DPV_STATIC -I"$out/obj-$pair" -I"$vroot" -I"$vroot/vltstd" \
  "$tb" -Wl,--start-group "${libs[@]}" -Wl,--end-group \
  "$vroot/verilated.cpp" "$vroot/verilated_threads.cpp" -o "check-$pair" > "link-$pair.log" 2>&1
 for mode in steady reframe epoch order first last data restart gap early output_late; do
  "./check-$pair" "$vectors" "$pair" "$mode" > "p$pair-$mode.json"
 done
 for ctx in 1 127 128 129 255 256 257 513 8191; do
  "./check-$pair" "$vectors" "$pair" steady "$ctx" > "p$pair-ctx$ctx.json"
 done
done
sha256sum check-* > binary.sha256
