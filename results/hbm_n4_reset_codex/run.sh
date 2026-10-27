#!/bin/bash
set -euo pipefail
ROOT=$(git rev-parse --show-toplevel);HERE=$ROOT/results/hbm_n4_reset_codex;SNAP=$ROOT/results/hbm_n4_native_1027;OUT=${1:?scratchout}
mkdir -p "$OUT/source";tar -xzf "$SNAP/source_snapshot.tar.gz" -C "$OUT/source"
cp "$HERE/tb_n4_extract.sv" "$OUT/source/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_tree.sv" "$OUT/source/rtl/hbm_next/fused/"
cp "$ROOT/rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv" "$OUT/source/rtl/hbm_next/fused/"
cd "$OUT/source"
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
SRC=(tb_n4_extract.sv rtl/hbm_next/fused/ot_hnx_fused_hub_n4ext.sv rtl/hbm_next/fused/ot_hnx_fused_tree.sv rtl/hbm_next/fused/ot_hnx_fused_eng.sv
 physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
 rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_delay_ring.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
 rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_f12.sv
 rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv
 rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41/ot_hdc_actquant.sv
 rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/lib/ot_rst_relay.sv)
verilator --binary --timing -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT --top-module tb_n4_extract -Mdir "$OUT/obj" -o native "${SRC[@]}" > "$OUT/build.log" 2>&1
"$OUT/obj/native" > "$OUT/positive.log" 2>&1
cat "$OUT/positive.log"
if "$OUT/obj/native" +MUT_PAIR > "$OUT/mutant.log" 2>&1;then echo MUTANT_ESCAPED;exit 1;else echo MUTANT_CAUGHT;fi

"$OUT/obj/native" +PADS > "$OUT/padded_positive.log" 2>&1
cat "$OUT/padded_positive.log"
if "$OUT/obj/native" +PADS +MUT_PAIR > "$OUT/padded_mutant.log" 2>&1;then echo PADDED_MUTANT_ESCAPED;exit 1;else echo PADDED_MUTANT_CAUGHT;fi
