#!/usr/bin/env bash
set -euo pipefail
O=${1:?fresh output};B=${2:?sealed TOKEN vectors};mkdir -p "$O"
V=verilator
[ ! -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] || V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
H=rtl/dsrom_sys/s81_dv/hostb
"$V" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD --top-module tb_hostb \
 -Mdir "$O/obj" rtl/lib/ot_reset_sync.sv "$H/dsdv_hostb_hold.sv" "$H/dsdv_hostb_crc512.sv" "$H/dsdv_hostb_rx.sv" "$H/dsdv_hostb_tx.sv" \
 "$H/dsdv_hostb_stage.sv" "$H/dsdv_hostb_return.sv" "$H/dsdv_hostb_head.sv" tools/s81_dv/hostb_1021/tb_hostb.sv \
 --build-jobs 4 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' >"$O/build.log" 2>&1
for mode in 0 1 2 3 4 5 6 7 8 9 10 13 14 15 16 17 18 19 20;do
 n=$(python3 tools/s81_dv/hostb_1021/prepare_bench.py --vectors "$B" --out "$O/v$mode" --mode "$mode")
 "$O/obj/Vtb_hostb" +VECTORS="$O/v$mode" +STOP="$n" +MODE="$mode" >"$O/bench$mode.log" 2>&1
 cat "$O/bench$mode.log"
done
