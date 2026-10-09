#!/bin/bash
set -euo pipefail
work=$1;shift
mkdir -p "$work"
iverilog -g2012 -s tb_s81_native_pc_mux "$@" -o "$work/gate.vvp" \
 rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv rtl/dsrom_sys/s81_ingest/ot_s81_native_pc_mux.sv \
 rtl/test/s81_native_ingest/tb_s81_native_pc_mux.sv >"$work/build.log" 2>&1
vvp "$work/gate.vvp" >"$work/gate.log" 2>&1
cat "$work/gate.log"
