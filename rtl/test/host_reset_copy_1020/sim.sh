#!/bin/bash
set -eu
out=$PWD/reset_copy_sim;mkdir -p "$out"
verilator --binary --timing -Wno-fatal --top-module tb -j 2 --Mdir "$out/obj" rtl/test/host_reset_copy_1020/{common_reset,tb_reset}.sv >"$out/build.log" 2>&1
"$out/obj/Vtb" >"$out/run.log" 2>&1
cat "$out/run.log"
