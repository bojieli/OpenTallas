#!/bin/bash
# Actual-source hierarchical component build; no physical job and no substitute.
set -euo pipefail
out=$(realpath -m "$1")
mkdir -p "$out"
python3 tools/qwen_kv_die/native_endpoint_sources.py > "$out/sources.f"
printf '%s\n' rtl/test/qwen_split/tb_native_attention_endpoint.sv >> "$out/sources.f"
sha256sum $(cat "$out/sources.f") tools/qwen_kv_die/native_endpoint.vlt > "$out/source.sha256"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --binary --timing --hierarchical -j 1 --build-jobs 8 -O2 \
 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-WIDTH \
 +define+KVD_HEADS=1 +define+KVD_Q_FP32=1 +define+KVD_QK_ONLY=1 \
 --top-module tb_native_attention_endpoint --Mdir "$out/obj" tools/qwen_kv_die/native_endpoint.vlt \
 -f "$out/sources.f" > "$out/build.log" 2>&1
if [[ ! -x "$out/obj/Vtb_native_attention_endpoint" ]]; then
 make -C "$out/obj" -f Vtb_native_attention_endpoint_hier.mk -j 1 'MAKE=make -j8' OBJCACHE=ccache hier_build >> "$out/build.log" 2>&1
fi
sha256sum "$out/obj/Vtb_native_attention_endpoint" > "$out/binary.sha256"
