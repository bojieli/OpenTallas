#!/bin/bash
# usage: run_bench.sh <srcroot> <name> <cycles>   (inside verilator image; bench dir = this script's dir)
S=$1; NM=$2; N=$3; B=$(cd $(dirname $0); pwd); O=$B/$NM; mkdir -p $O
P=""; for kv in $(cat $B/params.txt); do P="$P -G${kv}"; done
F=""; for f in $(grep -v _bb.v $B/files.txt); do F="$F $S/$f"; done
verilator --cc --exe --build -j 16 -O1 --no-timing -Wno-fatal -Wno-lint -Wno-style --top-module ot_v41_bf_col $P \
  -Mdir $O/obj $B/rom_bench.v $F $B/tb.cpp -o vbench > $O/build.log 2>&1 || { echo BUILD_FAIL; tail -20 $O/build.log; exit 3; }
$O/obj/vbench $N $O/out.txt > $O/run.log 2>&1; echo "run rc=$?"
