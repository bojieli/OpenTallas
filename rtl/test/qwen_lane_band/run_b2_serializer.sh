#!/usr/bin/env bash
set -euo pipefail
out=${1:?outdir};shift
cd "$(dirname "$0")/../../.."
mkdir -p "$out"
ver=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$ver" --binary --timing -j 8 -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_qfd_b2_serializer --Mdir "$out/obj" "$@" rtl/test/qwen_lane_band/tb_qfd_b2_serializer.sv rtl/qwen_split/qfd_res_ser_static.sv rtl/qwen_split/qfd_res_ser_half_b2.sv > "$out/build.log" 2>&1 || { tail -30 "$out/build.log";exit 1; }
"$out/obj/Vtb_qfd_b2_serializer" | tee "$out/run.log"
