#!/bin/bash
# Near-HBM attention service f46073090 (frozen source, same top/defines as
# tools/qwen_tp8_attention_service_build.sh) with the project's RTL FP units
# instead of the C-DPI stand-ins, hierarchical Verilation, PIC shared library.
# Usage: build_attn_hier.sh <frozen f460 root> <out>
set -euo pipefail
root=$1; out=$2; here=$(cd "$(dirname "$0")" && pwd)
vl=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
e_read_latency=${E_READ_LATENCY:-1}
[[ "$e_read_latency" =~ ^[1-9][0-9]*$ ]] || { echo 'E_READ_LATENCY must be positive' >&2; exit 2; }
v_return_latency=${V_RETURN_LATENCY:-$((16 + e_read_latency))}
src='rtl/hdc/nearhbm/ot_qwen_tp8_vrow_capture.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_k_request_static.sv rtl/hdc/nearhbm/ot_qwen_tp8_attention_service.sv rtl/hdc/nearhbm/ot_qwen_tp8_vrow_merge.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_pair.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_slice.sv rtl/hdc/nearhbm/ot_qwen_tp8_pv256_finalize.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_stack_h.sv rtl/hdc/nearhbm/ot_qkd_ectl_parts.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_attn_hub_p.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_prod.sv rtl/hdc/ot_hdc_sfu_q.sv rtl/hdc/nearhbm/ot_qwen_nearhbm_sfu_p.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_fp32_add_lat_nr.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv rtl/model/hbm_pc40_native_sim_20261003/ot_sram_1r1w_128x256_m1_r2c2_sim.sv'
out=$(realpath -m "$out")
[[ ! -e "$out" ]] || { echo "Output must be fresh: $out" >&2; exit 2; }
mkdir -p "$out"; cd "$root"
sha256sum $src "$here/qwen_tp8_attention_service_rtl.vlt" "$0" > "$out/source.sha256"
start=$(date +%s)
cpp_jobs=${CPP_JOBS:-16}
[[ "$cpp_jobs" =~ ^[1-9][0-9]*$ ]] || { echo 'CPP_JOBS must be positive integer' >&2; exit 2; }
$vl --cc --hierarchical -j 1 -O2 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN --top-module ot_qwen_tp8_attention_service \
 -GSTATIC_IO_TIMING="${STATIC_IO_TIMING:-0}" -GSTATIC_K_TRANSPORT="${STATIC_K_TRANSPORT:-0}" -GK_RETURN_LATENCY="${K_RETURN_LATENCY:-16}" \
 -GSTATIC_V_TRANSPORT="${STATIC_V_TRANSPORT:-0}" -GE_READ_LATENCY="$e_read_latency" -GV_RETURN_LATENCY="$v_return_latency" \
 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 +define+KVD_ECTL3 -CFLAGS "-O2 -fPIC" --Mdir "$out/obj" "$here/qwen_tp8_attention_service_rtl.vlt" $src > "$out/build.log" 2>&1
# Keep the outer hierarchy serial: each real stack elaboration needs107GB.
# Only the C++ compile child gets parallel jobs. A global -j16 would launch
# several huge elaborations and exceed the admitted memory reservation.
make -C "$out/obj" -f Vot_qwen_tp8_attention_service_hier.mk -j1 "MAKE=make -j$cpp_jobs" hier_build >> "$out/build.log" 2>&1
cd "$out/obj"
# The embedding executable owns the common Verilator runtime. Including its
# archive here duplicates runtime definitions when a component links that same
# runtime explicitly, and can give two independent runtime states in a host.
libs=$(find . -name "*.a" ! -name libverilated.a | sort)
g++ -shared -o "$out/libot_qwen_tp8_attention_service.so" -Wl,--whole-archive $libs -Wl,--no-whole-archive >> "$out/build.log" 2>&1
echo "{\"seconds\": $(( $(date +%s) - start )), \"fp_units\": \"RTL ot_hdc_fp32_add_lat/mul_lat/add_fast/mul_fast\", \"hierarchical\": true}" > "$out/receipt.json"
sha256sum "$out/libot_qwen_tp8_attention_service.so"

# A native arithmetic library must not import or define the old C FP helpers.
nm -D "$out/libot_qwen_tp8_attention_service.so" > "$out/dynamic-symbols.txt"
if grep -E "nhb_f(add|mul)|ot_v41x_f(add|mul)|fastfp_dpi" "$out/dynamic-symbols.txt"; then
 echo "Forbidden behavioral FP symbol in native attention library" >&2; exit 3
fi
find "$out/obj" -name "*.cpp" -print0 | sort -z | xargs -0 sha256sum > "$out/generated_sources.sha256"
sha256sum "$out/libot_qwen_tp8_attention_service.so" > "$out/binary.sha256"
