#!/usr/bin/env bash
# SVC3 (10-19): bench of the S81 hard attention head group ot_hdc_v41x_attn_hgrp_s81 (kit s81svc_attn_hgrp).
# rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv at the S81 engine parameters (H16 TD32 NBANK5 BW3 PWORDS2 FPL4 FML6
# HG4 F12 1): ot_hdc_v41x_attn_tile_s built with -DOT_ATTN_HGRP_HARD (its 4 groups = the hard element) against
# ot_hdc_v41x_attn_tile_l (the reference tile), random loads (both modes) / issues / NaN / pads, every output every
# cycle.  usage: hgrp_bench.sh OUT [MUT] [NCYC]   MUT 0 = PASS expected; 1 (gid ignored), 2 (head-0 fault dropped)
# must FAIL.  Verilator: $VERILATOR (the closure daemon's 5.050).
set -u
OUT=${1:?out}; MUT=${2:-0}; NCYC=${3:-20000}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
V=rtl/hdc/v41x; H=rtl/hdc
mkdir -p "$OUT"; O=$(cd "$OUT" && pwd)/m$MUT; rm -rf "$O"; mkdir -p "$O"
cat > "$O/top.sv" <<'SV'
`timescale 1ns/1ps
module tb_hgrp_top;
    reg clk = 1'b0;
    always #1 clk = ~clk;
    tb_hdc_v41x_attn_tile_s_lockstep u_tb (.clk(clk));
endmodule
SV
MD=""; [ "$MUT" != 0 ] && MD="-DOT_HGRP_MUT=$MUT"
"$VL" --version
# parameters of the lockstep tb are set through its defaults below (Verilator -G applies to the top only)
sed -e 's/parameter integer NBANK = 3;/parameter integer NBANK = 5;/' -e 's/parameter integer BW = 2;/parameter integer BW = 3;/' \
    -e 's/parameter integer PWORDS = 1;/parameter integer PWORDS = 2;/' -e 's/parameter integer FPL = 7;/parameter integer FPL = 4;/' \
    -e 's/parameter integer F12 = 0;/parameter integer F12 = 1;/' -e "s/parameter integer NCYC = 20000;/parameter integer NCYC = $NCYC;/" \
    rtl/test/tb_hdc_v41x_attn_tile_s_lockstep.sv > "$O/tb_s81.sv"
grep -E "parameter integer (H|TD|NBANK|BW|PWORDS|FPL|FML|HG|F12|PCOLP|NCYC) =" "$O/tb_s81.sv"
"$VL" --binary --timing -j 8 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-lint -Wno-style --unroll-count 64 \
    -DOT_ATTN_HGRP_HARD $MD --top-module tb_hgrp_top -Mdir "$O/obj" -o sim \
    "$O/top.sv" "$O/tb_s81.sv" $V/ot_hdc_v41x_attn_hgrp_s81.sv $V/ot_hdc_v41x_attn_tile_s.sv $V/ot_hdc_v41x_attn_tile_lat.sv \
    $V/ot_hdc_v41x_attn_tile.sv $V/ot_hdc_v41x_kreg.sv $H/ot_hdc_fastfp.sv $H/ot_hdc_fp32_add_lat.sv $H/ot_hdc_prefix.sv \
    $H/ot_hdc_fp32_f12.sv $V/ot_dsrom_su_add6.sv > "$O/build.log" 2>&1 || { tail -30 "$O/build.log"; echo "HGRP_BENCH BUILD_FAIL mut=$MUT"; exit 2; }
"$O/obj/sim" > "$O/sim.log" 2>&1; rc=$?
cat "$O/sim.log" | tail -12
if [ $rc -eq 0 ] && grep -q "TILESLOCK cycles=.* mismatches=0 " "$O/sim.log"; then
    echo "HGRP_BENCH PASS mut=$MUT $(grep -o 'TILESLOCK cycles=[^ ]* mismatches=[^ ]* ov=[0-9]*' "$O/sim.log")"
else
    echo "HGRP_BENCH FAIL mut=$MUT rc=$rc $(grep -o 'TILESLOCK.*' "$O/sim.log" | head -2 | tr '\n' ' ')"; exit 1
fi
