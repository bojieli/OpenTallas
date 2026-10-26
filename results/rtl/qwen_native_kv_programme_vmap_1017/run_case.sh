#!/bin/bash
# usage: run.sh MUT BAD VMAP WVMAP
W=/home/ubuntu/wt/kvj-a-1017; S=/home/ubuntu/wt/kvj-a-scratch/p1; top=tb_qkd_kv_native_programme
n=m$1_b$2_v$3_w$4
iverilog -g2012 -s $top -P$top.MUT=$1 -P$top.BAD=$2 -P$top.VMAP=$3 -P$top.WVMAP=$4 -o $S/$n.sim $W/rtl/lib/ot_rst_relay.sv $W/rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv $W/rtl/qwen_sys/static_kv_20261014/qkd_kv_static_writer.sv $W/rtl/physical/ot_qkd_kv_static_writer_native.sv $W/rtl/test/qwen_static_kv/tb_qkd_kv_native_programme.sv || exit 2
cd $S && vvp -n $n.sim > $n.log 2>&1; echo "$n exit=$? $(tail -1 $n.log)"; rm -f $n.sim
