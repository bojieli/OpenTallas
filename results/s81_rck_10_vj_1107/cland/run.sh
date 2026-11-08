#!/usr/bin/env bash
# usage: run.sh <rtl dir> <phase ns> [mutant: wch|offset|norst]
set -uo pipefail
R=$1; PH=$2; M=${3:-}; D=$(mktemp -d)
pp(){ verilator -E -P "$@" $D/meso.sv $D/land.sv 2>/dev/null; }
cp $R/ot_meso_fifo.sv $D/meso.sv; cp $R/ot_dp_clk_landing.sv $D/land.sv
ren(){ # suffix every module defined in file $1 with $2
  local f=$1 sfx=$2; for m in $(grep -oP '^\s*module\s+\K\w+' $f | sort -u); do sed -i -E "s/\b$m\b/${m}${sfx}/g" $f; done; }
pp -DSYNTHESIS_OFF > $D/ref.sv; ren $D/ref.sv _r; sed -i 's/\bot_dp_clk_landing_r\b/cl_ref/' $D/ref.sv
EXTRA=""
case "$M" in
  wch) sed -i 's/tcc <= nxt;/tcc <= nxt - 1'"'"'b1;/' $D/meso.sv; grep -c 'nxt - 1' $D/meso.sv >&2;;
  offset) EXTRA="-DOT_MESO_MUTANT_OFFSET";;
  norst) sed -i 's/wire rst_i = rst_l;/wire rst_i = rst_n;/' $D/land.sv;;
esac
pp -DOT_S81_CLAND_WCHK $EXTRA > $D/new.sv; ren $D/new.sv _n; sed -i 's/\bot_dp_clk_landing_n\b/cl_new/' $D/new.sv
verilator --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -Wno-MULTIDRIVEN -GPH=$PH --top-module tb --Mdir $D/obj -o tb $(dirname $0)/tb_cl.sv $D/ref.sv $D/new.sv > $D/build.log 2>&1 || { grep -i error $D/build.log | head; exit 2; }
$D/obj/tb 2>&1 | grep -v '^- ' | tail -3
