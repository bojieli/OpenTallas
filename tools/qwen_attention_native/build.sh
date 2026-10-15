#!/bin/bash
# Q-ATTN: build the static native attention service bench (Verilator hierarchical, --binary).
# Usage (in a source root that holds these paths): build.sh <out dir> [-Gparam=value ...]
set -euo pipefail
out=$(realpath -m "$1"); shift
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
here=$(cd "$(dirname "$0")" && pwd)
SRC="rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_sfu.sv
rtl/hdc/ot_hdc_delay.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qkh_subtiles.sv
rtl/hdc/nearhbm/ot_qwen_nearhbm_head_hs.sv rtl/lib/ot_rst_relay.sv rtl/lib/ot_rst_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv
rtl/qwen_sys/split_20261014/ot_qkh_head_native.sv rtl/qwen_sys/split_20261014/ot_qkh_head_native_r3.sv
rtl/qwen_sys/split_20261014/ot_qkh_head_native_r4.sv rtl/qwen_sys/split_20261014/qkd_ectl_native_direct_tp8.sv
rtl/qwen_sys/split_20261014/qkd_ectl_a_tp8_epoch_direct.sv rtl/qwen_sys/split_20261014/qkd_ectl3_epoch_direct_s.sv
rtl/qwen_sys/split_20261014/qkd_astk_native_er_service.sv rtl/qwen_sys/split_20261014/qkd_astk_native_stack_s.sv
rtl/qwen_sys/kv_die_20261009/qkd_astk_leaves.sv rtl/qwen_sys/split_20261014/qkd_astk_cal_gen.sv
physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
physical/qkd_astk_strip/macros/ot_sram_1r1w_256x128_m1_r2c2/ot_sram_1r1w_256x128_m1_r2c2.v
physical/qkd_astk_strip/macros/ot_sram_1r1w_64x128_m1_r2c2/ot_sram_1r1w_64x128_m1_r2c2.v
rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_stack.sv
rtl/hdc/nearhbm/ot_qkd_ahub_static.sv rtl/hdc/nearhbm/ot_qkd_ahub_static_cal_gen.sv rtl/hdc/nearhbm/ot_qkd_ahub_core.sv rtl/hdc/nearhbm/ot_nhb_tiles.sv
rtl/hdc/nearhbm/ot_qkh_recip_leaf.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv
rtl/hdc/nearhbm/ot_qwen_tp8_vrow_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_capture.sv
rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv
rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize_static_cal_gen.sv
rtl/hdc/nearhbm/ot_qwen_tp8_attention_native_service.sv
rtl/test/nearhbm/tb_qwen_tp8_attention_native_service.sv"
mkdir -p "$out"
python3 "$here/gen_astk_cal.py" --check > "$out/generated_check.log"
sha256sum $SRC "$here/native_service.vlt" "$0" > "$out/source.sha256"
start=$(date +%s)
"$vl" --binary --timing --hierarchical -j 1 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 --top-module tb_qwen_tp8_attention_native_service \
 --Mdir "$out/obj" "$@" "$here/native_service.vlt" $SRC > "$out/verilate.log" 2>&1
echo "verilate_seconds $(( $(date +%s) - start ))" >> "$out/verilate.log"
make -C "$out/obj" -f Vtb_qwen_tp8_attention_native_service_hier.mk -j${OUTER_JOBS:-1} "MAKE=make -j${JOBS:-32}" OBJCACHE=ccache hier_build >> "$out/verilate.log" 2>&1 || \
 make -C "$out/obj" -f Vtb_qwen_tp8_attention_native_service.mk -j"${JOBS:-32}" OBJCACHE=ccache >> "$out/verilate.log" 2>&1
ls -la "$out/obj/Vtb_qwen_tp8_attention_native_service"
sha256sum "$out/obj/Vtb_qwen_tp8_attention_native_service" > "$out/binary.sha256"
echo "{\"build_seconds\": $(( $(date +%s) - start ))}" > "$out/receipt.json"
