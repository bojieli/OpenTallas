#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);HERE=$ROOT/results/hbm_fused_boot_1351_1027;OUT=${1:?scratchout}
mkdir -p "$OUT/source";tar -xzf "$ROOT/results/hbm_n4_native_1027/source_snapshot.tar.gz" -C "$OUT/source"
cp "$HERE/tb_native_boot.sv" "$OUT/source/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_tree.sv" "$OUT/source/rtl/hbm_next/fused/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv" "$OUT/source/rtl/hbm_next/fused/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_job217_provider.sv" "$OUT/source/"
cp "$HERE/actual_post_jobs.mem" "$OUT/source/"
cp "$ROOT/results/hbm_fused_provider_1027/sram256.v" "$OUT/source/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_host_boot.sv" "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_host_program.sv" "$OUT/source/"
cp "$ROOT/rtl/hbm_accel/host_static_20261015/ot_hbm_host_static_ingress.sv" "$ROOT/rtl/hbm_accel/host_static_20261015/ot_hbm_host_cfg_leaf.sv" "$OUT/source/"
cp "$ROOT/rtl/lib/ot_rst_relay.sv" "$OUT/source/rtl/lib/"
cd "$OUT/source"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
SRC=(tb_native_boot.sv ot_hnx_fused_host_boot.sv ot_hnx_fused_host_program.sv ot_hbm_host_static_ingress.sv ot_hbm_host_cfg_leaf.sv ot_hnx_fused_job217_provider.sv sram256.v rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
 rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
 rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_native_boot -Mdir "$OUT/obj" -o native "${SRC[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/native" > "$OUT/positive.log" 2>&1;cat "$OUT/positive.log"
for m in DATA HIGH;do if "$OUT/obj/native" +MUT_$m > "$OUT/mut_$m.log" 2>&1;then echo MUTANT_${m}_ESCAPED;exit 1;else echo MUTANT_${m}_CAUGHT;fi;done
