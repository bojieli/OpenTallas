#!/bin/bash
# usage: run.sh <name> <M1> <M2> <M3> <M4>; PASS = ok holds on every cycle after the first clock edge (30 cycles, free initial state)
n=$1
printf '`define M1 %s\n`define M2 %s\n`define M3 %s\n`define M4 %s\n' "$2" "$3" "$4" "$5" > d_$n.vh
cat > p_$n.ys <<Y
read_verilog d_$n.vh blk.v
hierarchy -top miter; proc; async2sync; flatten; opt_clean
sat -seq 30 -prove-skip 1 -prove ok 1 -show-inputs -verify miter
Y
if yosys -q p_$n.ys > p_$n.log 2>&1; then echo "$n PASS"; else echo "$n FAIL"; fi
