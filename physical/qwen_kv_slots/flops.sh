#!/usr/bin/env bash
# Generic-yosys flop count of one top (clock rule: <= 15,000 sinks per clock root).
#   flops.sh OUT_DIR TOP "PARAM=V ..." file.sv ...      macros as *_bb.v black boxes
# Prints "FLOPS <top> flat=<n> mem_bits=<n>" and the 12 largest modules by own flops (hierarchical stat in OUT_DIR/hier.txt).
set -u
OUT=$1; TOP=$2; PAR=$3; shift 3
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}; [ -x "$Y" ] || Y=yosys
mkdir -p "$OUT"
CH=""; for p in $PAR; do CH="$CH chparam -set ${p%%=*} ${p#*=} $TOP;"; done
RD=""; for f in "$@"; do RD="$RD read_verilog -sv -defer $f;"; done
"$Y" -q -l "$OUT/yosys.log" -p "$RD $CH hierarchy -top $TOP; proc; opt_clean; memory_dff; tee -o $OUT/hier.txt stat -width; flatten; opt -fast; memory_collect; tee -o $OUT/flat.txt stat -width" > "$OUT/run.log" 2>&1 || { tail -5 "$OUT/run.log"; echo "FLOPS $TOP FAILED"; exit 1; }
"$Y" -q -p "$RD $CH hierarchy -top $TOP; proc; opt_clean; memory_dff; flatten; opt -fast; dffunmap; simplemap t:\$dff t:\$adff t:\$sdff t:\$dffe t:\$adffe t:\$sdffe t:\$sdffce t:\$aldff t:\$aldffe t:\$dffsr t:\$dffsre %u; tee -o $OUT/bits.txt stat" >> "$OUT/run.log" 2>&1
F=$(grep -E '\$_(S|A)?DFF' "$OUT/bits.txt" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+$/){s+=$i; break}} END{print s+0}')
MB=$(grep -iE 'memory bits' "$OUT/bits.txt" | grep -oE '[0-9]+' | tail -1)
echo "FLOPS $TOP flat=$F mem_bits=${MB:-0}"
