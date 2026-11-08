#!/bin/bash
P=$(cd "$(dirname "$0")" && pwd); cd $P
R="ot_rst_relay.sv dsdv_gunit_sel_n32.sv"
for m in none MUT; do (
  D=""; [ $m = MUT ] && D="-DOT_GUNIT_BF_M1REG_MUT"
  iverilog -g2012 -s tb_bf -DNCYC=1500 -DOT_GUNIT_BF_M1REG $D -o tbs_$m.vvp tb_bf.sv gold_bf.sv dsdv_gunit_l1f.sv $R 2> comps_$m.log || { echo "COMPILE_FAIL $m"; exit; }
  vvp -n tbs_$m.vvp > benchs_$m.log 2>&1; echo "RUN $m rc $?: $(grep -m3 'BENCH\|MISMATCH' benchs_$m.log)" ) &
done; wait
