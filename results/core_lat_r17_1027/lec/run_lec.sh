#!/bin/bash
# S81-CORE-LAT-R17 sorter sequential equivalence: gate = current dsdv_sel_sort8 CPS 2 (repo R), gold = the PRE-R17 sorter
# source (2ad2c9fd3f, modules renamed old_*) at CPS 3 with one register on every output (ref_sort.sv).  From reset,
# outputs compared at cycles 4..10 with free inputs: complete for a depth-3 feed-forward pipeline.
# usage: run_lec.sh <repo root> <MUT> -> SORT_SEQ_EQ PROVED / FAIL
R=$1; M=${2:-0}; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
D=$(cd "$(dirname "$0")" && pwd)
git -C $R show 2ad2c9fd3f:rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_sel.sv | sed -E 's/\b(dsdv_sel_[a-z0-9_]+)\b/old_\1/g' > $D/old_sel.sv
RST=""; for k in 2 3 4 5 6 7 8 9 10; do RST="$RST -set-at $k in_rst_n 1"; done
$Y -q -l $D/lec_m$M.log -p "
read_verilog -sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_sel.sv $D/old_sel.sv $D/ref_sort.sv
chparam -set MUT $M new_sort
hierarchy -check
proc; flatten; opt_clean; async2sync; dffunmap
rename ref_sort gold; rename new_sort gate
miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter
hierarchy -top miter
sat -verify -prove-asserts -set-init-zero -seq 10 -prove-skip 3 -set-at 1 in_rst_n 0 $RST -show-ports miter
" > /dev/null 2>&1 && echo "SORT_SEQ_EQ PROVED (MUT=$M)" || echo "SORT_SEQ_EQ FAIL (MUT=$M)"
