#!/bin/bash
# usage: relay_bench.sh PLAN BOUND_RTL_DIR CELLS_DIR WORK
cd /srv/opentallas-scratch2/claude/kvtf1
PLAN=$1; BR=$2; CD=$3; W=$4; mkdir -p $W
for row in "kv3_phy none" "kv3_phy deep_bout" "kv3_phy_v1 none" "kv3_phy_v1 deep_bout"; do
 set -- $row; tn=$1; mut=$2; mod=${tn}_part
 for st in early late; do
  d=$W/${tn}_${mut}_$st; mkdir -p $d
  m=(); [ $mut = none ] || m=(--mutant $mut)
  python3 -I mk_relay_bench.py $PLAN $tn $BR/$mod.sv $d/new.sv "${m[@]}" > $d/make.log 2>&1 || { echo "$tn $mut $st MAKE_FAIL $(tail -1 $d/make.log)"; continue; }
  s=(); [ $st = late ] && s=(--late-start)
  python3 -I $CD/gen_tb0.py $BR/$mod.sv $mod 0 $d/tb.sv "${s[@]}"
  iverilog -g2012 -o $d/sim $d/tb.sv $BR/$mod.sv $d/new.sv $CD/phy_stub.sv $BR/bind_cells.sv $CD/ot_dp_clk_landing.sv $CD/ot_dp_clk_landing_ca.sv $CD/ot_meso_fifo.sv $CD/ot_reset_sync.sv > $d/iverilog.log 2>&1 || { echo "$tn $mut $st COMPILE_FAIL $(head -3 $d/iverilog.log|tr '\n' ' ')"; continue; }
  timeout 900 vvp -n $d/sim > $d/sim.log 2>&1
  echo "$tn mutant=$mut start=$st $(cat $d/make.log | tail -1) -> $(grep '^BENCH' $d/sim.log) | first mismatches: $(grep -m3 MISMATCH $d/sim.log | tr '\n' ';')"
 done
done
