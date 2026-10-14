#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";out=${1:?out};heads=${2:-2};mode=${3:-price};mut=${4:-0};order_mut=${5:-0};class_mut=${6:-0};io=${7:?authoritative IO source tree};adapter_mut=${8:-0};mkdir -p "$out";out=$(cd "$out"&&pwd);export TMPDIR="$out"
python3 tools/qwen_host/native_fixture.py "$out" "$heads" "$mode" > "$out/fixture.log"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator";[[ -x "$v" ]]||v=$(command -v verilator)
k=rtl/qwen_sys/kv_die_20261009;e=rtl/qwen_sys/emb_hbm_20261008;h=rtl/qwen_sys/host_20261013
"$v" --binary --timing -O1 --output-split 10000 --output-split-cfuncs 100 -CFLAGS -O0 -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-TIMESCALEMOD \
 --top-module tb_qkd_host_native_fdi_pad5 -GRMW_EN=0 -GMUT="$mut" -GORDER_MUT="$order_mut" -GCLASS_MUT="$class_mut" -GADAPTER_MUT="$adapter_mut" --Mdir "$out/obj" \
 "$io/rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv" "$io/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv" "$io/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" "$h/qkd_host_phy_cdc5.sv" "$h/qkd_host_rx_pad5.sv" "$h/qkd_host_rx_pad.sv" "$h/qkd_host_rx_class.sv" "$h/qkd_host_tx_class.sv" rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv "$h/qkd_host_commit_order.sv" "$h/qkd_host_ingest_chain.sv" "$h/qkd_host_ingest_map.sv" "$h/qkd_host_ingest_station.sv" "$h/qkd_host_static_pc.sv" "$h/qkd_host_visibility_fence.sv" "$h/qkd_ctrl_pc_host.sv" \
 "$k/ot_qkvd_kcmd_tap.sv" "$e/ot_qwen_ctrl_pc_emb.sv" "$e/ot_hbm_r14_stream_pc_srow.sv" "$e/synth/ot_qfd_emb_pcport.sv" "$e/ot_qfd_emb_cdc.sv" \
 rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv rtl/qwen_sys/q5_20261009/synth/ot_qfd_kv_landing_ecc.sv \
 rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv "$h/qkd_host_native_engine.sv" "$h/qkd_host_native_qm.sv" \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/test/qwen_host/tb_qkd_host_native_fdi_pad5.sv > "$out/build.log" 2>&1
read -r nd np ns < <(python3 - "$out/fixture.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]));print(j['descriptors'],j['beats'],j['sectors'])
PY
)
(cd "$out";./obj/Vtb_qkd_host_native_fdi_pad5 +ND="$nd" +NP="$np" +NSECTOR="$ns") > "$out/run.log" 2>&1
cat "$out/run.log";grep -q '^PASS NATIVE_FDI1043_PAD5_CLK6_LAT223' "$out/run.log"
