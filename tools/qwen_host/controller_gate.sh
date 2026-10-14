#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output dir};mut=${2:-0};evmut=${3:-0};mkdir -p "$out";out=$(cd "$out"&&pwd)
export TMPDIR="$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator";[[ -x "$v" ]]||v=$(command -v verilator)
k=rtl/qwen_sys/kv_die_20261009;e=rtl/qwen_sys/emb_hbm_20261008;h=rtl/qwen_sys/host_20261013
"$v" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
 -Irtl/test/qwen_host --top-module tb_qkd_ctrl_pc_host -GPCI=13 -GMUT="$mut" -GEVMUT="$evmut" --Mdir "$out/obj" \
 "$h/qkd_ctrl_pc_host.sv" "$h/qkd_host_static_pc.sv" "$k/ot_qkvd_kcmd_tap.sv" \
 "$e/ot_qwen_ctrl_pc_emb.sv" "$e/ot_hbm_r14_stream_pc_srow.sv" "$e/synth/ot_qfd_emb_pcport.sv" \
 "$e/ot_qfd_emb_cdc.sv" rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv \
 rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/test/qwen_host/tb_qkd_ctrl_pc_host.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_qkd_ctrl_pc_host" > "$out/run.log" 2>&1
cat "$out/run.log"
grep -q '^PASS qkd_ctrl_pc' "$out/run.log"&&! grep -q '^FAIL' "$out/run.log"
