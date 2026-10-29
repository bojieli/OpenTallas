#!/bin/bash
# TOK-HBM-2 root-local service probe. Usage: run_root_service.sh <repo-root> <scratch-out>. Source = the same snapshot +
# current rtl/hbm_next/fused files as results/hbm_n4_native_1027/run.sh (production root wrapper, DELIVERED_RESET=1).
set -euo pipefail
ROOT=${1:?repo};OUT=${2:?out};HERE=$ROOT/results/tok_hbm_2_1028
mkdir -p "$OUT/source";tar -xzf "$ROOT/results/hbm_n4_native_1027/source_snapshot.tar.gz" -C "$OUT/source"
cp "$HERE/tb_lane_service.sv" "$OUT/source/"
cp "$ROOT"/rtl/hbm_next/fused/ot_hnx_fused_{tree,hub_n4ext,eng}.sv "$OUT/source/rtl/hbm_next/fused/"
cd "$OUT/source"
SRC=(tb_lane_service.sv rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
 rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
 rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_lane_service -Mdir "$OUT/obj" -o ls "${SRC[@]}" > "$OUT/build.log" 2>&1
: > "$OUT/lane_service.log"
for op in PRE POST; do for n in 1 2 3 4 5 6 7 8; do for w in 150 200; do
  a="+N=$n +RD=$w"; [ $op = POST ] && a="$a +POST"
  "$OUT/obj/ls" $a | grep LANE_SERVICE >> "$OUT/lane_service.log"
done; done; done
cat "$OUT/lane_service.log"
