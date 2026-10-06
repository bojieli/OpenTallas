#!/bin/bash
# run_bench.sh <views/stations dir> <master> <src root> <bench out dir>: Verilator (--timing, x-initial unique: the meso ring counters are
# never reset by design) positive run + mutant negative control
G=$1; m=$2; R=$3
T=$4/$m; mkdir -p $T; python3 $R/tools/hbm_die_station_bench.py tb --gen $G --master $m --out $T > /dev/null; cd $T; rm -f result.txt
for v in pos neg; do
  src=$G/$m/${m}_sim.sv; [ $v = neg ] && src=$G/$m/${m}_mutant_sim.sv
  rm -rf $v; mkdir -p $v; cp order.json $v/
  (cd $v && verilator --binary --timing -j 4 -Wno-fatal -Wno-lint -Wno-style --x-initial unique --x-assign unique -O1 \
     --top-module tb_$m $R/rtl/common/ot_fwd_link_stage.sv $R/rtl/common/ot_meso_fifo.sv $R/physical/hbm_accel_die_views/stations/rtl/ot_hbm_stn_lib.sv $src ../tb_$m.sv -Mdir obj -o sim > comp.log 2>&1 && ./obj/sim +verilator+seed+1062026 +verilator+rand+reset+2 > run.log 2>&1)
  python3 $R/tools/hbm_die_station_bench.py check --gen $G --master $m --log $v/trace.log > $v/check.json; echo "$v rc=$?" >> result.txt
done
