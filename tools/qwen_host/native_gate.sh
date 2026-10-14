#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../..";root=$PWD;out=${1:?out};mut=${2:-0};heads=${3:-2};mode=${4:-edge};native=${5:-1};mkdir -p "$out";out=$(cd "$out"&&pwd)
export TMPDIR="$out";python3 tools/qwen_host/native_fixture.py "$out" "$heads" "$mode" > "$out/fixture.log"
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator";[[ -x "$v" ]]||v=$(command -v verilator)
"$v" --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-TIMESCALEMOD \
 --top-module tb_qkd_host_native_ingest -GRMW_EN=0 -GMUT="$mut" -GNATIVE_ROWS="$native" --Mdir "$out/obj" \
 rtl/lib/ot_reset_sync.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
 rtl/hdc/ingest/ot_hdc_kv_ingest.sv rtl/hdc/ingest/ot_rom_host_ingest.sv \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v \
 rtl/test/qwen_host/tb_qkd_host_native_ingest.sv > "$out/build.log" 2>&1
read -r nd np ns < <(python3 - "$out/fixture.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]));print(j['descriptors'],j['beats'],j['sectors'])
PY
)
(cd "$out";./obj/Vtb_qkd_host_native_ingest +ND="$nd" +NP="$np" +NSECTOR="$ns") > "$out/run.log" 2>&1
cat "$out/run.log";grep -q '^PASS NATIVE_INGEST' "$out/run.log"
