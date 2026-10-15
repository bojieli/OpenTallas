#!/bin/bash
# Near-HBM attention service f46073090 (frozen source, same top/defines as
# tools/qwen_tp8_attention_service_build.sh) with the project's RTL FP units
# instead of the C-DPI stand-ins, hierarchical Verilation, PIC shared library.
# Usage: build_attn_hier.sh <frozen f460 root> <out>
set -eu
root=$1; out=$2; here=$(cd "$(dirname "$0")" && pwd)
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src='rtl/hdc/nearhbm/ot_qwen_tp8_attention_service.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_merge.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv'
mkdir -p "$out"; cd "$root"
sha256sum $src "$here/hier_attn.vlt" "$0" > "$out/source.sha256"
start=$(date +%s)
$vl --cc --build --hierarchical -j ${JOBS:-32} -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module ot_qwen_tp8_attention_service \
 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 +define+KVD_ECTL3 -CFLAGS "-O2 -fPIC" --Mdir "$out/obj" "$here/hier_attn.vlt" $src > "$out/build.log" 2>&1
cd "$out/obj"
libs=$(find . -name "*.a" | sort)
g++ -shared -o "$out/libot_qwen_tp8_attention_service.so" -Wl,--whole-archive $libs -Wl,--no-whole-archive >> "$out/build.log" 2>&1
echo "{\"seconds\": $(( $(date +%s) - start )), \"fp_units\": \"RTL ot_hdc_fp32_add_lat/mul_lat/add_fast/mul_fast\", \"hierarchical\": true}" > "$out/receipt.json"
sha256sum "$out/libot_qwen_tp8_attention_service.so"
