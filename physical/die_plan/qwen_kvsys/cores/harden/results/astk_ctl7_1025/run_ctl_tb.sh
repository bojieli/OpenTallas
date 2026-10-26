#!/bin/bash
# PATH-KV-ASTK7: ctl lockstep nominal + mutant. usage: run_ctl_tb.sh <outdir> <harden dir> <ASTK6 kit rtl>
set -u
O=$1; H=$2; OLD=$3
for v in nom mut; do
  d=$O/ctl_$v; rm -rf $d; mkdir -p $d/rtl; cp $OLD/*.sv $OLD/*.v $d/rtl/
  python3 - $OLD/qkd_astk_static_leaves.sv $d/old_ctl.sv <<'PY'
import sys
t = open(sys.argv[1]).read(); i = t.index("module qkd_astk_ctl_s "); j = t.index("endmodule", i) + 9
open(sys.argv[2], "w").write("`timescale 1ns/1ps\n" + t[i:j].replace("module qkd_astk_ctl_s ", "module qkd_astk_ctl_s_o ", 1) + "\n")
PY
  m=""; [ $v != nom ] && m=mut
  ( cd $H && python3 astk_ctl_slots.py $d/rtl $m ) || { echo "$v TRANSFORM FAIL"; continue; }
  ( cd $d && verilator --binary --timing -j 8 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Irtl --top-module tb --Mdir obj \
      rtl/qkd_astk_static_leaves.sv old_ctl.sv $H/results/astk_ctl7_1025/tb_astk7_ctl.sv > build.log 2>&1 ) || { echo "$v BUILD FAIL"; grep -m8 %Error $d/build.log; continue; }
  ( cd $d && ./obj/Vtb > sim.log 2>&1 ); echo "== $v: $(grep -h 'ASTK7 CTL' $d/sim.log)"; grep -m3 MISMATCH $d/sim.log
  rm -rf $d/obj
done
