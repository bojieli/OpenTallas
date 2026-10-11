#!/bin/bash
# hbm-phys [svc] 2026-10-10: ot_hfd_loader_kport gate (bursts + multi-outstanding, CP fetch rate).  run from the repo
# root: run_kport_bench.sh <out>.  SIM=iverilog (four-state, default) | verilator.  Cases:
#   all cases: CH 12 register stages each way on lq / lr (the die's forwarded chains), credited native channel
#   pos_rtt104   NO 8 RB 16, PHY latency set for a fetch round trip ~104 cycles: fetch rate >= 2 x 0.867 B/cycle
#   pos_rtt160   NO 8 RB 16, round trip ~160 cycles: fetch rate >= 2 x 0.867
#   pos_rb32     NO 8 RB 32, round trip ~160 (rate reported)
#   pos_no1      NO 1 (one native transaction a stack, bursts on): exact (rate reported, not gated)
#   neg_lane0    MUT 1 (every response to lane 0)          -> must FAIL
#   neg_stack    MUT 2 (stack bit 1 ignored)                -> must FAIL
#   neg_row      MUT 3 (bursts cross the row / PC boundary) -> must FAIL
#   neg_credit   MUT 4 (issue ignores the svc queue credits) -> must FAIL
set -u
O=$1; mkdir -p $O; rm -f $O/summary.txt
D=rtl/hbm_accel/loader/service_native
Y="-y $D -y rtl/hbm_accel/service -y rtl/hbm_accel/ingest -y rtl/hdc/v41x -y rtl/hdc/kv -y physical/hbm_accel_die_views/svc/rtl"
run() {   # run <label> <params...>
  local L=$1; shift
  if [ "${SIM:-iverilog}" = verilator ]; then
    local P=(); for a in "$@"; do P+=("-G${a}"); done
    verilator --binary --timing -j 4 -Wno-fatal -Wno-TIMESCALEMOD "${P[@]}" --top-module tb_hfd_loader_kport --Mdir $O/vlt_$L \
      +libext+.sv $Y $D/tb_hfd_loader_kport.sv > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    $O/vlt_$L/Vtb_hfd_loader_kport > $O/$L.log 2>&1
  else
    local P=(); for a in "$@"; do P+=("-Ptb_hfd_loader_kport.${a}"); done
    iverilog -g2012 -Y .sv "${P[@]}" -o $O/$L.vvp -s tb_hfd_loader_kport $Y $D/tb_hfd_loader_kport.sv > $O/build_$L.log 2>&1 \
      || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
    vvp -n $O/$L.vvp > $O/$L.log 2>&1
  fi
}
L104=${L104:-39000}; L160=${L160:-76000}
run pos_rtt104 NO=8 XLAT=$L104 & run pos_rtt160 NO=8 XLAT=$L160 & run pos_rb32 NO=8 RB=32 XLAT=$L160 &
run pos_no1 NO=1 RATE_MIN=0 &
run neg_lane0 MUT=1 & run neg_stack MUT=2 & run neg_row MUT=3 & run neg_credit MUT=4 &
wait
rc=0
for L in pos_rtt104 pos_rtt160 pos_rb32 pos_no1; do grep -q "^PASS HFD-LOADER-KPORT" $O/$L.log; r=$?
  echo "$L rc=$r $(grep -h FETCH_RATE $O/$L.log)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1; done
for L in neg_lane0 neg_stack neg_row neg_credit; do grep -q "^PASS HFD-LOADER-KPORT" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep -m1 FATAL $O/$L.log)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1; done
echo "KPORT_GATE rc=$rc" >> $O/summary.txt; cat $O/summary.txt; exit $rc
