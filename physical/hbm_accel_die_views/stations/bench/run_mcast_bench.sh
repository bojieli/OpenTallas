#!/bin/bash
# run_mcast_bench.sh <views/stations dir> <master> <src root> <bench out dir> (views agent, mcast RC/PLREG/RSPLIT fix):
# Verilator, same tb / check as run_bench.sh (transaction-level: one constant latency per output domain, every bit).
#   pos       exact view                                  expect check rc=0 and no PLREG_MISMATCH
#   neg       generator mutant (two data bits swapped)    expect check rc=1
#   neg_pl    +define+OT_MESO_MUTANT_PLREG (one edge late) expect PLREG_MISMATCH in run.log
#   neg_rs    +define+OT_MESO_MUTANT_RSPLIT (half dropped) expect check rc=1
# Prints MCAST_BENCH PASS / MCAST_BENCH FAIL <why>.
G=$1; m=$2; R=$3
T=$4/$m; mkdir -p $T; python3 $R/tools/hbm_die_station_bench.py tb --gen $G --master $m --out $T > /dev/null; cd $T; rm -f result.txt
for v in pos neg neg_pl neg_rs; do
  src=$G/$m/${m}_sim.sv; [ $v = neg ] && src=$G/$m/${m}_mutant_sim.sv
  def=; [ $v = neg_pl ] && def=+define+OT_MESO_MUTANT_PLREG; [ $v = neg_rs ] && def=+define+OT_MESO_MUTANT_RSPLIT
  rm -rf $v; mkdir -p $v; cp order.json $v/
  (cd $v && verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --x-initial unique --x-assign unique -O1 $def \
     --top-module tb_$m $R/rtl/common/ot_fwd_link_stage.sv $R/rtl/common/ot_meso_fifo.sv $R/physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv $src ../tb_$m.sv -Mdir obj -o sim > comp.log 2>&1 && ./obj/sim +verilator+seed+1062026 +verilator+rand+reset+2 > run.log 2>&1)
  python3 $R/tools/hbm_die_station_bench.py check --gen $G --master $m --log $v/trace.log > $v/check.json; rc=$?
  pm=$(grep -c PLREG_MISMATCH $v/run.log 2>/dev/null); echo "$v rc=$rc plreg_mismatch=${pm:-0}" >> result.txt
done
cat result.txt
ok=1
grep -q '^pos rc=0 plreg_mismatch=0$' result.txt || { ok=0; echo "MCAST_BENCH FAIL pos"; }
grep -q '^neg rc=1' result.txt || { ok=0; echo "MCAST_BENCH FAIL neg not detected"; }
grep -q '^neg_pl rc=[01] plreg_mismatch=[1-9]' result.txt || { ok=0; echo "MCAST_BENCH FAIL neg_pl not detected"; }
grep -q '^neg_rs rc=1' result.txt || { ok=0; echo "MCAST_BENCH FAIL neg_rs not detected"; }
python3 -c "import json;[print(k,v['latency_periods'],v['mismatches']) for k,v in json.load(open('pos/check.json'))['domains'].items()]" 2>/dev/null
[ $ok = 1 ] && echo "MCAST_BENCH PASS"
[ $ok = 1 ]
