#!/bin/bash
# LAND-HEAD-BIND-1 crossing bench on every leaf-free (station / turn) type: real gen2 landed wrapper vs gen0 reference.
set -u
R=/srv/opentallas-scratch2/claude/land-head-bind-1
W=/srv/opentallas-scratch2/claude/wt/land-head-bind-1
B=$R/bench
export PATH="$HOME/.local/opentallas-tools/bin:$PATH"
mkdir -p $B
: > $B/summary.txt
for m in ot_s81hd_st_k5 ot_s81hd_st_m ot_s81hd_st_n3 ot_s81hd_st_n4 ot_s81hd_st_str ot_s81hd_st_turn ot_s81hd_turn_a ot_s81hd_turn_b; do
  d=$B/$m; rm -rf $d; mkdir -p $d
  python3 -I $R/mk_land_bench.py $R/gen2 $R/gen0 $m $d > $d/gen.log 2>&1 || { echo "$m GEN FAIL" >> $B/summary.txt; continue; }
  verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_$m -o sim \
    $d/tb_$m.sv $R/gen2/$m.sv $d/${m}__ref.sv $R/gen2/ot_dp_cells.sv $W/rtl/common/ot_dp_clk_landing.sv $W/rtl/common/ot_meso_fifo.sv \
    --Mdir $d/obj > $d/build.log 2>&1 || { echo "$m BUILD FAIL" >> $B/summary.txt; continue; }
  for ph in 0 183 201 -183 -201 300 -300; do
    $d/obj/sim +PHASE=$ph 2>&1 | grep -E "^BENCH|^PASS|^FAIL" | tr "\n" " " >> $B/summary.txt; echo >> $B/summary.txt
  done
done
echo DONE >> $B/summary.txt
