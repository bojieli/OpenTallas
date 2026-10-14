#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?absolute output directory required}
mkdir -p "$out"
out=$(cd "$out" && pwd)
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"
[[ -x "$v" ]] || v=$(command -v verilator)
h=rtl/qwen_sys/host_20261013
k=rtl/qwen_sys/kv_die_20261009
e=rtl/qwen_sys/emb_hbm_20261008
sources=("$h/qwen_native_hbm_pc_provider.sv" "$h/qkd_host_static_pc.sv" "$h/qkd_ctrl_pc_host.sv"
 "$k/ot_qkvd_kcmd_tap.sv" "$e/ot_qwen_ctrl_pc_emb.sv" "$e/ot_hbm_r14_stream_pc_srow.sv"
 "$e/synth/ot_qfd_emb_pcport.sv" "$e/ot_qfd_emb_cdc.sv" rtl/lib/ot_async_fifo.sv
 rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv)
sha256sum "${sources[@]}" > "$out/source_pins.sha256"
"$v" --cc --build -O1 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
 --top-module qwen_native_hbm_pc_provider --Mdir "$out/obj" "${sources[@]}" > "$out/build.log" 2>&1
sha256sum "$out/obj/Vqwen_native_hbm_pc_provider__ALL.a" "$out/obj/Vqwen_native_hbm_pc_provider.h" > "$out/library.sha256"
echo "LIBRARY_READY $out/obj/Vqwen_native_hbm_pc_provider__ALL.a"
