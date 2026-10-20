#!/bin/bash
set -euo pipefail
O=${1:?out};M=${2:-0};mkdir -p "$O"
verilator --version
verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -DOT_S81PH_SEL_FAN32 --top-module tb_hist_banked -GMUT="$M" --Mdir "$O/obj" -o bank rtl/lib/ot_rst_relay.sv rtl/hdc/ot_hdc_prefix.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_bank.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_hist_banked.sv results/arch/s81_topk5_1020/tb_hist_banked.sv > "$O/build.log" 2>&1
set +e
"$O/obj/bank" | tee "$O/run.log"
rc=${PIPESTATUS[0]}
set -e
if [ "${3:-}" = raw ];then exit "$rc";fi
if [ "$M" = 0 ];then test "$rc" = 0; grep -q '^HIST_BANKED PASS MUT=0 checks=' "$O/run.log";else test "$rc" != 0; grep -q "^HIST_BANKED FAIL MUT=$M " "$O/run.log"; ! grep -q "^HIST_BANKED PASS" "$O/run.log";fi
