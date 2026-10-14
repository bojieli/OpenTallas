#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};hot=${2:-0};mut=${3:-0};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator";[[ -x "$v" ]]||v=$(command -v verilator)
k=rtl/qwen_sys/kv_die_20261009;e=rtl/qwen_sys/emb_hbm_20261008;h=rtl/qwen_sys/host_20261013
"$v" --binary --timing -O1 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
 --top-module tb_qkd_host_ingest_actual -GHOT="$hot" -GMUT="$mut" --Mdir "$out/obj" \
 "$h/qkd_host_ingest_chain.sv" "$h/qkd_host_ingest_map.sv" "$h/qkd_host_ingest_station.sv" "$h/qkd_host_static_pc.sv" "$h/qkd_ctrl_pc_host.sv" \
 "$k/ot_qkvd_kcmd_tap.sv" "$e/ot_qwen_ctrl_pc_emb.sv" "$e/ot_hbm_r14_stream_pc_srow.sv" "$e/synth/ot_qfd_emb_pcport.sv" "$e/ot_qfd_emb_cdc.sv" \
 rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv rtl/test/qwen_host/tb_qkd_host_ingest_actual.sv > "$out/build.log" 2>&1
for mode in 0 1;do
 "$out/obj/Vtb_qkd_host_ingest_actual" +HOT="$mode" > "$out/run-hot-$mode.log" 2>&1
 cat "$out/run-hot-$mode.log";grep -q '^PASS HOST_INGEST_ACTUAL' "$out/run-hot-$mode.log"
done
if "$out/obj/Vtb_qkd_host_ingest_actual" +EVENT_MUT=1 > "$out/mutant.log" 2>&1;then echo 'FAIL undetected physical completion polarity';exit 1;fi
cat "$out/mutant.log"
