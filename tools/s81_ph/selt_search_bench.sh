#!/bin/bash
set -euo pipefail
out=$1; qw=${2:-21}; mkdir -p "$out"
verilator --binary --timing -j "${JOBS:-8}" -Wno-fatal -Wno-lint -Wno-style --top-module tb_s81ph_sel_search_pipe -GQW="$qw" -Mdir "$out/obj" \
 rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_hdc_v41x_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_lib.sv rtl/dsrom_sys/s81_ph/selector_native/ot_s81ph_native_sel_slice.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_pipeline.sv rtl/dsrom_sys/s81_ph/test/tb_s81ph_sel_search_pipe.sv > "$out/build.log" 2>&1
"$out/obj/Vtb_s81ph_sel_search_pipe" > "$out/run.log" 2>&1
grep 'SEARCH_PIPE PASS' "$out/run.log"
