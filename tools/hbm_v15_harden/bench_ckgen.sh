#!/bin/bash
# hfd_ckgen reset release bench (H-HARDEN 10-15). MUT=1: one-flop release (must FAIL).
set -euo pipefail
out=${1:?};mut=${2:-0};mkdir -p "$out"
d=rtl/hbm_accel/control
cp "$d/hfd_ckgen.sv" "$out/dut.sv"
if [ "$mut" = 1 ];then sed -i "s/else        s <= {s\[0\], 1'b1};/else        s <= 2'b11;/" "$out/dut.sv";cmp -s "$out/dut.sv" "$d/hfd_ckgen.sv" && { echo MUTANT_NOT_APPLIED;exit 3; };fi
iverilog -g2012 -s tb_hfd_ckgen -o "$out/a.vvp" "$out/dut.sv" "$d/tb_hfd_ckgen.sv"
vvp "$out/a.vvp" | tee "$out/run.log";grep -q CKGEN_PASS "$out/run.log"
