#!/bin/bash
# Resume the existing source-exact hierarchy after a compiler OOM. Reuse every
# successful actual child; never replace a child with a model or raise its cap.
set -euo pipefail
out=$(realpath -m "$1")
wrapper=$(realpath tools/qwen_kv_die/native_endpoint_verilator.sh)
sha256sum -c "$out/source.sha256" > "$out/resume_source_verify.log"
sha256sum tools/qwen_kv_die/native_endpoint_verilator.sh \
 tools/qwen_kv_die/native_endpoint_noinline.vlt \
 tools/qwen_kv_die/resume_native_endpoint.sh > "$out/compiler_override.sha256"
make -C "$out/obj" -f Vtb_native_attention_endpoint_hier.mk -j 1 \
 "VM_HIER_VERILATOR=$wrapper" hier_verilation > "$out/resume.log" 2>&1
make -C "$out/obj" -f Vtb_native_attention_endpoint_hier.mk -j 1 \
 'MAKE=make -j8' OBJCACHE=ccache "VM_HIER_VERILATOR=$wrapper" hier_build >> "$out/resume.log" 2>&1
sha256sum "$out/obj/Vtb_native_attention_endpoint" > "$out/binary.sha256"
