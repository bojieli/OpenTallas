#!/bin/bash
# GUNIT-CORE-1 11-13: gf4 lock-step bench.  PASS = N1 PASS; N0, N2 and MUT FAIL.
P=$(cd "$(dirname "$0")" && pwd); cd $P
T=${RTL_ROOT:-$P/../../../../../../../../rtl}; U=$T/dsrom_sys/s81_dv/unit
R="$T/lib/ot_rst_relay.sv $U/dsdv_gunit_sel_n32.sv $U/dsdv_gunit_l1f.sv"
for m in N1 N0 N2 MUT; do (
  D="-DNDLY=1"; [ $m = N0 ] && D="-DNDLY=0"; [ $m = N2 ] && D="-DNDLY=2"; [ $m = MUT ] && D="-DNDLY=1 -DOT_GUNIT_BF_C1REG_MUT"
  iverilog -g2012 -s tb_bf4 -DNCYC=${NCYC:-1500} -DOT_GUNIT_BF_M1REG -DOT_GUNIT_BF_C1REG $D -o tb4_$m.vvp tb_bf4.sv gold_bf3.sv $R 2> comp_$m.log || { echo "COMPILE_FAIL $m $(head -3 comp_$m.log)"; exit; }
  vvp -n tb4_$m.vvp > bench_$m.log 2>&1; echo "RUN $m rc $?: $(grep -m1 BENCH bench_$m.log) $(grep -m1 MISMATCH bench_$m.log)" ) &
done; wait
