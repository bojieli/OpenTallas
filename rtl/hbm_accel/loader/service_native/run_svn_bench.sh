#!/bin/bash
# [svc-ep] 2026-10-10: the loader kport (ot_hfd_loader_kport, NO 16 / RB 64 as on the die) against the PS native endpoint
# (ot_svn_ep + ot_svn_st stations + ot_svs_pcsn PC units, physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_nep_lib.sv) and the
# refresh-aware PHY model, through CH-stage lq / lr chains and HS-stage station hops.  run from the repo root:
#   run_svn_bench.sh <out>        SIM=verilator (default) | iverilog
#   pos_rtt104 / pos_rtt160: writes + one-sector reads + random bursts exact + fetch rate (gate RATE_MIN, B/cycle x 1000)
#   neg_drop  (EPMUT 1: a read-data flit dropped)        -> must FAIL
#   neg_order (EPMUT 2: beats returned out of order)       -> must FAIL
#   neg_land  (EPMUT 3: a write lands at the wrong PC)     -> must FAIL
set -u
O=$1; mkdir -p $O; rm -f $O/summary.txt
D=rtl/hbm_accel/loader/service_native; V=physical/hbm_accel_die_views/svc/rtl
SRC="$D/tb_svn_kport.sv $V/ot_hbm_svc_nep_lib.sv $V/ot_hbm_svc_core.sv rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv rtl/hbm_accel/service/ot_hbm_kport_map.sv"
Y="-y $D -y rtl/hbm_accel/service -y rtl/hbm_accel/ingest -y rtl/hdc/v41x -y rtl/hdc/kv"
GATE=${RATE_MIN:-12400}
run() { local L=$1; shift
  local P=(); for a in "$@"; do P+=("-G${a}"); done
  verilator --binary --timing -j 4 -Wno-fatal -Wno-TIMESCALEMOD -Wno-WIDTH "${P[@]}" --top-module tb_svn_kport --Mdir $O/vlt_$L \
    +libext+.sv $Y $SRC > $O/build_$L.log 2>&1 || { echo "$L build FAIL" >> $O/summary.txt; return 3; }
  $O/vlt_$L/Vtb_svn_kport > $O/$L.log 2>&1; }
run pos_rtt104 NO=16 RB=64 XLAT=39000 RATE_MIN=$GATE & run pos_rtt160 NO=16 RB=64 XLAT=76000 RATE_MIN=$GATE &
run neg_drop NO=16 RB=64 EPMUT=1 RATE_MIN=0 & run neg_order NO=16 RB=64 EPMUT=2 RATE_MIN=0 & run neg_land NO=16 RB=64 EPMUT=3 RATE_MIN=0 &
wait
rc=0
for L in pos_rtt104 pos_rtt160; do grep -q "^PASS SVN-KPORT" $O/$L.log; r=$?
  echo "$L rc=$r $(grep -h FETCH_RATE $O/$L.log)" >> $O/summary.txt; [ $r -ne 0 ] && rc=1; done
for L in neg_drop neg_order neg_land; do grep -q "^PASS SVN-KPORT" $O/$L.log && r=0 || r=1
  echo "$L rc=$r (must be nonzero) $(grep -m1 FATAL $O/$L.log)" >> $O/summary.txt; [ $r -eq 0 ] && rc=1; done
echo "SVN_GATE rc=$rc" >> $O/summary.txt; cat $O/summary.txt; exit $rc
