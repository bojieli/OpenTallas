#!/usr/bin/env bash
set -euo pipefail
ulimit -c 0
repo=$(cd "$(dirname "$0")/../../../.." && pwd)
build=${1:?separate build directory}; vectors=${2:?directory containing vectors_TOKEN dirs}
mkdir -p "$build/calendar"
cd "$repo"
controller_root=${CONTROLLER_SOURCE_ROOT:-$repo}
base=$controller_root/rtl/qwen_sys/static_kv_20261014
verilator --binary --timing -Wno-fatal --top-module tb_static_embed_controller -j 4 --Mdir "$build/obj" \
 rtl/qwen_sys/static_embedding_20261014/test/tb_static_embed_controller.sv \
 rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_pc.sv \
 rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_map.sv \
 "$base/qkd_ctrl_pc_host_static.sv" "$base/ot_qkd_static_ctrl_pc_emb.sv" "$base/ot_qkd_static_kv_timing.sv" \
 "$base/ot_qkd_static_emb_cdc.sv" "$base/qkd_static_kv_write_observer.sv" \
 rtl/qwen_sys/kv_die_20261009/ot_qkvd_kcmd_tap.sv \
 rtl/qwen_sys/emb_hbm_20261008/synth/ot_qfd_emb_pcport.sv rtl/qwen_sys/emb_hbm_20261008/ot_qfd_emb_cdc.sv \
 rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/qwen_sys/host_20261013/qkd_host_static_pc.sv \
 rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv >"$build/build.log" 2>&1
"$build/obj/Vtb_static_embed_controller" +CALIBRATE=1 +CALENDAR="$build/calendar" +VECTORS="$vectors" >"$build/compiler.log" 2>&1
# Separate process, PROFILE0 controller enabled, frozen files only.
"$build/obj/Vtb_static_embed_controller" +CALIBRATE=0 +CALENDAR="$build/calendar" +VECTORS="$vectors" >"$build/replay.log" 2>&1
for mutant in 1 2 3 4;do
 if "$build/obj/Vtb_static_embed_controller" +CALIBRATE=0 +CALENDAR="$build/calendar" +VECTORS="$vectors" +MUT="$mutant" >"$build/mutant_$mutant.log" 2>&1;then
  echo "FAIL controller timing mutant $mutant escaped";exit 1
 fi
done
echo 'PASS dual-clock actual controller embedding compiler/fresh static replay and four failing timing/address mutants'
