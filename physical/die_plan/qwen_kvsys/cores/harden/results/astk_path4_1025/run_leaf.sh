#!/bin/bash
# PATH-KV-ASTK4: leaf lockstep (nominal + 2 mutants). usage: run_leaf.sh <outdir> <harden dir> <old kit rtl>
export PATH=/srv/opentallas-scratch2/claude/kv-cores-1025r/bin:$PATH
set -u
O=$1; H=$2; OLD=$3
for v in nom mut_zn mut_ctl; do
  d=$O/leaf_$v; rm -rf $d; mkdir -p $d/rtl; cp $OLD/*.sv $OLD/*.v $d/rtl/ 2>/dev/null
  # old copies, renamed
  sed 's/module qkd_astk_zn_head_p /module qkd_astk_zn_head_p_o /' $OLD/qkd_astk_zn_head_p.sv > $d/old_zn0.sv
  python3 - $OLD/qkd_astk_static_leaves.sv $d/old_ctl.sv <<'PY'
import sys
t = open(sys.argv[1]).read(); i = t.index("module qkd_astk_ctl_s "); j = t.index("endmodule", i) + 9
open(sys.argv[2], "w").write("`timescale 1ns/1ps\n" + t[i:j].replace("module qkd_astk_ctl_s ", "module qkd_astk_ctl_s_o ", 1) + "\n")
PY
  m=""; [ $v != nom ] && m=$v
  ( cd $H && python3 astk_path4.py $d/rtl $m ) || { echo "$v TRANSFORM FAIL"; continue; }
  files=$(ls $d/rtl/*.sv $d/rtl/*.v | grep -v -e asap7sc7p5t -e kv3_astk.sv)
  ( cd $d && verilator --binary --timing -j 8 -MAKEFLAGS "OBJCACHE=" -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Irtl --top-module tb --Mdir obj \
      $files old_zn0.sv old_ctl.sv /srv/opentallas-scratch2/claude/path-kv-astk4/leaf/tb_astk4.sv > build.log 2>&1 ) || { echo "$v BUILD FAIL"; grep -m8 %Error $d/build.log; continue; }
  ( docker run --rm --memory=8g -u $(id -u):$(id -g) -v $O:$O -w $d --entrypoint ./obj/Vtb verilator/verilator:v5.032 > $d/sim.log 2>&1 ); echo "== $v: $(grep -h 'ASTK4 LEAF' $d/sim.log)"; grep -m3 MISMATCH $d/sim.log
  rm -rf $d/obj
done
