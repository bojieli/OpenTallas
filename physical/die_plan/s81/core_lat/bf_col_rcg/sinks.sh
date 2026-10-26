#!/bin/bash
# usage: sinks.sh <srcroot> <out.json>   (inside orfs image)
S=$1; O=$2; cd $(dirname $0)
P=""; for kv in $(cat params.txt); do P="$P -set ${kv%%=*} ${kv#*=}"; done
F=""; for f in $(cat files.txt); do F="$F $S/$f"; done
cat > /tmp/s.ys <<YS
read_verilog -sv -DSYNTHESIS icg_bb.v $F
chparam $P ot_v41_bf_col
hierarchy -check -top ot_v41_bf_col
proc
flatten
opt_clean -purge
write_json $O
YS
yosys -q -l ${O%.json}.log /tmp/s.ys
