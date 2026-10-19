#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
out=${1:?};mkdir -p "$out"
verilator --version | tee "$out/verilator.txt"
verilator --version | grep -q '5.050'
SRC=(rtl/test/qwen_split/tb_embedding_join.sv rtl/qwen_split/qfd_native59_dv_service.sv rtl/qwen_split/qfd_native59_q_export_control.sv rtl/qwen_split/qfd_native59_command_context.sv rtl/qwen_split/qfd_native59_static_service.sv rtl/qwen_split/qfd_native59_record_endpoint.sv rtl/qwen_split/qfd_kvn_static_transport.sv rtl/qwen_sys/redesign_qwen/ot_qfd_su_kv_static_posted.sv rtl/qwen_sys/vm_nox_20261014/qfd_vm_attention_commit_fence.sv rtl/qwen_sys/split_20261014/qkd_native_attention_record.sv rtl/qwen_split/qfd_embedding_word_provider.sv rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_preload_face.sv rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_store.sv physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
sha256sum "${SRC[@]}" > "$out/source.sha256"
verilator --binary --timing -j 4 -Wno-fatal --top-module tb_embedding_join --Mdir "$out/obj" "${SRC[@]}" > "$out/build.log" 2>&1
for token in 0 65536 151935;do
 "$out/obj/Vtb_embedding_join" +TOKEN="$token" +VECTORS="results/arch/qwen_tp8_native_dispatch_1014/embedding_vectors/token$token" > "$out/token$token.log" 2>&1
 grep '^JOIN_PASS' "$out/token$token.log"
done
for mut in 1 2 3 4 5 6 7 8;do
 if "$out/obj/Vtb_embedding_join" +TOKEN=65536 +VECTORS=results/arch/qwen_tp8_native_dispatch_1014/embedding_vectors/token65536 +MUT="$mut" > "$out/mut$mut.log" 2>&1;then echo "FAIL mutant$mut escaped";exit 1;fi
 grep 'JOIN_FAIL' "$out/mut$mut.log"
done
