#!/bin/bash
# fill2_host_bench.sh <base|mut1|mut4> <out>: one run of the S-BIND r6 static layer-die host bench
# (rtl/dsrom_sys/s81_ingest/test/tb_dsfd_host_c_static.sv, +DSFD_HOST_C_STATIC: 40 program words over the ck->ckv
# crossing, 12 ingest words, lane-fault fold) for the closure-loop bench pair of dsfd_host_c.
# base -> "HOST BENCH PASS base"; mut1 (program words dropped) / mut4 (lane faults not folded) -> "HOST BENCH FAIL <m>"
set -u
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
M=$1; OUT=$2; mkdir -p $OUT
F=$(python3 tools/die_port_bind.py none --closure dsfd_host_c | tr '\n' ' ')
case $M in base) G="" ;; mut1) G="-GMUT=1" ;; mut4) G="-GMUT=4" ;; *) echo "unknown $M"; exit 2 ;; esac
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +define+DSFD_HOST_C_STATIC --top-module tb_dsfd_host_c_static $G --Mdir $OUT/obj -o tb $F rtl/dsrom_sys/s81_ingest/test/tb_dsfd_host_c_static.sv > $OUT/build.log 2>&1 || { tail -3 $OUT/build.log; echo "HOST BENCH BUILD_FAIL $M"; exit 1; }
$OUT/obj/tb > $OUT/run.log 2>&1
r=$(grep TB_DSFD_HOST_C_STATIC $OUT/run.log | tail -1); echo "$r"
case "$r" in *" PASS") echo "HOST BENCH PASS $M"; exit 0 ;; *) echo "HOST BENCH FAIL $M"; exit 1 ;; esac
