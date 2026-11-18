#!/usr/bin/env bash
# S81-CORES-R3 11-17: bk_sel bench of the merged dsdv_bksel_c.sv with the eco3 quarter parameter set (OT_BKQ_ECO3: dsdv_bksel_q
# OLL 2 RFH 2 HLAT 1, control QRX 1) against its negative controls.  Run from the source root.  usage: run_bksel_rfh_qrx.sh <out>
#   base   : no defines (hq3 parameter set, as built)                         must PASS
#   eco3   : +OT_BKQ_ECO3                                                       must PASS
#   qrxmut : +OT_BKQ_ECO3 +OT_BKQ_QRX_MUT (control ignores the RFH 2 edge)      must FAIL
#   p2mut  : +OT_BKQ_ECO3 +OT_RFH_MUT_P2 (f_cr bypasses the RFH 2 stage)        info only (ROWS=...): credits 1 edge EARLY
#            are benign at cycle level, so this bench cannot see it (11-17 r1: PASS); it is a face-flop (LEC) mutant
#   facemut: +OT_BKQ_ECO3 +OT_RFH_MUT_FACE (face flops on the rising edge)      info only: +1 more edge on every input sits
#            inside the control's ceil((RC + RS + QRX) / 2) slack (11-17 r1: PASS); a hold-window (STA / LEC) mutant
#   lqhmut : +OT_RFD_MUT_LQH (control one-hot landing count moves on push + pop) must FAIL (control LQH 1 is bound)
# 11-17 r1 (epyc2): base PASS, eco3 PASS 6/6, qrxmut FAIL (606 / 274 errors): the control MUST take QRX 1 with eco3 quarters.
# verdict line: "BKSEL_RFH_QRX PASS" when every row matches its expectation.
set -u
OUT=$1; mkdir -p "$OUT"; T=rtl/dsrom_sys/s81_dv/unit/bk/test/run_bk_bench.sh
ROWS=${ROWS:-base eco3 qrxmut lqhmut}
declare -A D=([base]="" [eco3]="+define+OT_BKQ_ECO3" [qrxmut]="+define+OT_BKQ_ECO3 +define+OT_BKQ_QRX_MUT"
              [p2mut]="+define+OT_BKQ_ECO3 +define+OT_RFH_MUT_P2" [facemut]="+define+OT_BKQ_ECO3 +define+OT_RFH_MUT_FACE"
              [lqhmut]="+define+OT_RFD_MUT_LQH")
declare -A X=([base]=PASS [eco3]=PASS [qrxmut]=FAIL [p2mut]=PASS [facemut]=PASS [lqhmut]=FAIL)
for k in $ROWS; do
  ( BK_DEFS="${D[$k]}" JOBS=${JOBS:-8} bash $T sel "$OUT/$k" 0 > "$OUT/$k.log" 2>&1 ) &
done
wait
bad=0
for k in $ROWS; do
  v=$(grep -ho 'DSDV_BK_SEL \(PASS\|FAIL\)' "$OUT/$k.log" | tail -1 | awk '{print $2}')
  [ "$v" = "${X[$k]}" ] && ok=OK || { ok=BAD; bad=1; }
  echo "$k: got ${v:-NONE} want ${X[$k]} $ok | $(grep -h '^sel m0' "$OUT/$k.log" | tr '\n' ';' | cut -c1-600)"
done
[ $bad = 0 ] && echo "BKSEL_RFH_QRX PASS" || { echo "BKSEL_RFH_QRX FAIL"; exit 1; }
