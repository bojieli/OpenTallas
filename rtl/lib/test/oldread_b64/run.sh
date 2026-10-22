#!/bin/bash
# $1 output dir, $2 mutant (0 positive, 1 forwarding removed, 2 collision read not suppressed -> fatal)
set -eu
O=$(realpath -m "$1"); M=${2:-0}; mkdir -p "$O"
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version
D=(); if [ "$M" != 0 ]; then D+=(-DOT_B64_MUT=$M); fi
verilator --binary --timing -j 2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style "${D[@]}" --top-module tb_oldread_b64 --Mdir "$O/obj" \
 rtl/lib/test/oldread_b64/tb_oldread_b64.sv rtl/lib/ot_sram_oldread_b64.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv \
 physical/asap7_memory_macros_v2/ot_sram_1r1w2c_256x64_m1/ot_sram_1r1w2c_256x64_m1.v > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; exit 2; }
set +e; "$O/obj/Vtb_oldread_b64" > "$O/run.log" 2>&1; rc=$?; set -e
tail -8 "$O/run.log"; echo "sim exit $rc"
grep -q '^B64_ORACLE PASS' "$O/run.log"
