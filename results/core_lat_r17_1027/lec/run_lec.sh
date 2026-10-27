#!/bin/bash
# usage: run_lec.sh <repo root> <MUT> -> SORT_SEQ_EQ PROVED / FAIL
R=$1; M=${2:-0}; Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; [ -x $Y ] || Y=yosys
D=$(cd "$(dirname "$0")" && pwd)
$Y -q -l $D/lec_m$M.log -p "
read_verilog -sv $R/rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_sel.sv $D/ref_sort.sv
chparam -set MUT $M new_sort
hierarchy -check
proc; flatten; opt_clean; async2sync; dffunmap
rename ref_sort gold; rename new_sort gate
miter -equiv -flatten -make_assert -ignore_gold_x gold gate miter
hierarchy -top miter
sat -verify -prove-asserts -set-init-zero -seq 10 -prove-skip 3 -set-at 1 in_rst_n 0 $(for k in 2 3 4 5 6 7 8 9 10; do echo -n "-set-at $k in_rst_n 1 "; done) -show-ports miter
" > /dev/null 2>&1 && echo "SORT_SEQ_EQ PROVED (MUT=$M)" || echo "SORT_SEQ_EQ FAIL (MUT=$M)"
