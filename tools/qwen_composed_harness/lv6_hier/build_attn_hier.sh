#!/bin/bash
# Near-HBM attention service f46073090 (frozen source, same top/defines as
# tools/qwen_tp8_attention_service_build.sh) with the project's RTL FP units
# instead of the C-DPI stand-ins, hierarchical Verilation, PIC shared library.
# Usage: build_attn_hier.sh <frozen f460 root> <out>
set -euo pipefail
root=$1; out=$2; here=$(cd "$(dirname "$0")" && pwd)
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
src='rtl/hdc/nearhbm/ot_qwen_tp8_attention_service.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_merge.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv'
mkdir -p "$out"; out=$(realpath "$out"); cd "$root"
# One admitted owner may plan/build this cache. Preserve failed logs and the
# original source receipt before regenerating only the hierarchy plan.
exec 9>"$out/build.lock"
flock -n 9 || { echo 'Attention cache already has a live builder' >&2; exit 2; }
if [[ -e "$out/source.sha256" ]]; then
 sha256sum -c "$out/source.sha256" > "$out/previous-source-check.log"
 prior="$out/previous-$(date +%s)"; mkdir "$prior"
 for name in source.sha256 build.log parallel-resume.log receipt.json; do
  [[ ! -e "$out/$name" ]] || cp -p "$out/$name" "$prior/"
 done
fi
sha256sum $src "$here/hier_attn.vlt" "$0" > "$out/source.sha256"
start=$(date +%s)
$vl --cc --hierarchical -j 1 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module ot_qwen_tp8_attention_service \
 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 +define+KVD_ECTL3 -CFLAGS "-O2 -fPIC" --Mdir "$out/obj" "$here/hier_attn.vlt" $src > "$out/build.log" 2>&1
cd "$out/obj"
make -f Vot_qwen_tp8_attention_service_hier.mk -j1 "MAKE=make -j${JOBS:-16}" hier_build >> "$out/build.log" 2>&1
mapfile -t libs < <(find . -name '*.a' ! -name libverilated.a | sort)
g++ -shared -o "$out/libot_qwen_tp8_attention_service.so" -Wl,--whole-archive "${libs[@]}" -Wl,--no-whole-archive >> "$out/build.log" 2>&1
nm -D "$out/libot_qwen_tp8_attention_service.so" > "$out/dynamic-symbols.txt"
if grep -Eq '\b(nhb_fadd|nhb_fmul|ot_v41x_fadd|ot_v41x_fmul)\b' "$out/dynamic-symbols.txt"; then exit 3; fi
sha256sum "$out/libot_qwen_tp8_attention_service.so" > "$out/binary.sha256"
find . -name '*.a' -print0 | sort -z | xargs -0 sha256sum > "$out/archives.sha256"
find . -name '*.cpp' -print0 | sort -z | xargs -0 sha256sum > "$out/generated_sources.sha256"
echo "{\"seconds\": $(( $(date +%s) - start )), \"fp_units\": \"RTL ot_hdc_fp32_add_lat/mul_lat/add_fast/mul_fast\", \"hierarchical\": true, \"serial_hierarchy_jobs\": 1, \"parallel_cpp_jobs\": ${JOBS:-16}}" > "$out/receipt.json"
sha256sum "$out/libot_qwen_tp8_attention_service.so"
