#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?usage: run_rt2_calendar_bench.sh OUT_DIR}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p "$O"
"$VL" --binary --timing --top-module tb_svc_rt2_load_calendar -Mdir "$O/obj" -j 2 \
    -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD \
    rtl/dsrom_sys/s81_svc/ot_s81_svc_attn_s.sv \
    rtl/hdc/v41x/ot_s81c_attn_h8_rt2.sv \
    rtl/dsrom_sys/s81_dv/svc_rs/tb_svc_rt2_load_calendar.sv >"$O/build.log" 2>&1
for requested_origin in 0 1; do
    "$O/obj/Vtb_svc_rt2_load_calendar" +requested_origin=$requested_origin >"$O/run_r${requested_origin}.log" 2>&1
    cat "$O/run_r${requested_origin}.log"
    grep -q '^RT2_CALENDAR PASS:' "$O/run_r${requested_origin}.log"
done
cp "$O/run_r0.log" "$O/run.log"
