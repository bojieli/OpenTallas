#!/usr/bin/env bash
# DIE-HBM-92-LAT gate: the chain bench at the event's hook values per quadrant (legs = landed stages of the event bind)
# + calibration at zero legs + +-1 mutants (consumer parameter and leg).  Positive rows must PASS, mutants FAIL.
set -u
H=$(cd "$(dirname "$0")" && pwd); R=$H/run_lat_chain.sh
B="-Ptb_hbm_lat_chain.BRD=8 -Ptb_hbm_lat_chain.BWD=5"     # faces bank pins (l12 law: SU tap 11/8 at zero lanes)
hx() { printf "32'h%02x%02x%02x%02x" $4 $3 $2 $1; }        # LG0..3 -> packed parameter (LG k at [8k+:8])
P=tb_hbm_lat_chain
row() { exp=$1; shift; out=$(nice $R "$@"); echo "$exp $out" | cut -c1-230
  case "$exp:$out" in PASS:*LATCHAIN\ PASS*|FAIL:*LATCHAIN\ FAIL*) ;; *) echo "GATE_MISMATCH $1"; bad=1;; esac; }
bad=0
q() {  # q NAME NRQ NRR CRQ CRR HRQ HRR (each "a b c d")
  local n=$1; set -- $2 $3 $4 $5 $6 $7 $8 $9 ${10} ${11} ${12} ${13} ${14} ${15} ${16} ${17} ${18} ${19} ${20} ${21} ${22} ${23} ${24} ${25}
  local nrq=($1 $2 $3 $4) nrr=($5 $6 $7 $8) crq=($9 ${10} ${11} ${12}) crr=(${13} ${14} ${15} ${16}) hrq=(${17} ${18} ${19} ${20}) hrr=(${21} ${22} ${23} ${24})
  local N=() su=() suw=() sf=() sfw=() hc=() hcw=() k
  for k in 0 1 2 3; do N[$k]=$(( ${nrq[$k]} + ${nrr[$k]} )); su[$k]=$((11+N[k])); suw[$k]=$((8+N[k])); sf[$k]=$((15+N[k])); sfw[$k]=$((12+N[k]))
    hc[$k]=$((19+N[k])); hcw[$k]=$((16+N[k])); done
  local br=$((2+sf[0]+crq[0]+crr[0])) bw=$((2+sfw[0]+crq[0]+crr[0])) hr=$((23+hc[0]-18+hrq[0]+hrr[0])) hd=$((19+hcw[0]-15+hrq[0]+hrr[0]))
  for k in 1 2 3; do [ $((2+sf[k]+crq[k]+crr[k])) = $br ] && [ $((23+hc[k]-18+hrq[k]+hrr[k])) = $hr ] || { echo "GATE_MISMATCH $n: LG$k loop differs"; bad=1; }; done
  echo "== $n: N ${N[*]} su ${su[*]} sfu ${sf[*]} hc ${hc[*]} bridge $br/$bw hc_q $hr/$hr/$hd"
  local L="-P$P.DNRQ=$(hx ${nrq[*]}) -P$P.DNRR=$(hx ${nrr[*]}) -P$P.DCRQ=$(hx ${crq[*]}) -P$P.DCRR=$(hx ${crr[*]}) -P$P.DHRQ=$(hx ${hrq[*]}) -P$P.DHRR=$(hx ${hrr[*]})"
  local T="-P$P.SU_RR=$(hx ${su[*]}) -P$P.SU_WR=$(hx ${suw[*]}) -P$P.SFU_RR=$(hx ${sf[*]}) -P$P.SFU_WR=$(hx ${sfw[*]}) -P$P.HC_RR=$(hx ${hc[*]}) -P$P.HC_WR=$(hx ${hcw[*]})"
  local C="-P$P.BR_RR=$br -P$P.BR_WR=$bw -P$P.HQ_RD=$hr -P$P.HQ_GP=$hr -P$P.HQ_DONE=$hd"
  row PASS ${n}_sfu 0 $B $L $T $C &
  row PASS ${n}_hcq 1 $B $L $T $C &
  row PASS ${n}_su 2 $B $L $T $C &
  wait
  row FAIL ${n}_br_rr+1 0 $B $L $T $C -P$P.BR_RR=$((br+1)) &
  row FAIL ${n}_br_rr-1 0 $B $L $T $C -P$P.BR_RR=$((br-1)) &
  row FAIL ${n}_br_wr+1 0 $B $L $T $C -P$P.BR_WR=$((bw+1)) &
  row FAIL ${n}_br_wr-1 0 $B $L $T $C -P$P.BR_WR=$((bw-1)) &
  row FAIL ${n}_sfu0_rr+1 0 $B $L $T $C -P$P.SFU_RR=$(hx $((sf[0]+1)) ${sf[1]} ${sf[2]} ${sf[3]}) &
  row FAIL ${n}_leg_crr2+1 0 $B $C $T -P$P.DNRQ=$(hx ${nrq[*]}) -P$P.DNRR=$(hx ${nrr[*]}) -P$P.DCRQ=$(hx ${crq[*]}) -P$P.DCRR=$(hx ${crr[0]} ${crr[1]} $((crr[2]+1)) ${crr[3]}) -P$P.DHRQ=$(hx ${hrq[*]}) -P$P.DHRR=$(hx ${hrr[*]}) &
  wait
  row FAIL ${n}_hq_rd+1 1 $B $L $T $C -P$P.HQ_RD=$((hr+1)) -P$P.HQ_GP=$((hr+1)) &
  row FAIL ${n}_hq_rd-1 1 $B $L $T $C -P$P.HQ_RD=$((hr-1)) -P$P.HQ_GP=$((hr-1)) &
  row FAIL ${n}_hq_done+1 1 $B $L $T $C -P$P.HQ_DONE=$((hd+1)) &
  row FAIL ${n}_hq_done-1 1 $B $L $T $C -P$P.HQ_DONE=$((hd-1)) &
  row FAIL ${n}_hc0_rr-1 1 $B $L $T $C -P$P.HC_RR=$(hx $((hc[0]-1)) ${hc[1]} ${hc[2]} ${hc[3]}) &
  row FAIL ${n}_leg_hrr0+1 1 $B $C $T -P$P.DNRQ=$(hx ${nrq[*]}) -P$P.DNRR=$(hx ${nrr[*]}) -P$P.DCRQ=$(hx ${crq[*]}) -P$P.DCRR=$(hx ${crr[*]}) -P$P.DHRQ=$(hx ${hrq[*]}) -P$P.DHRR=$(hx $((hrr[0]+1)) ${hrr[1]} ${hrr[2]} ${hrr[3]}) &
  wait
  row FAIL ${n}_su0_rr+1 2 $B $L $T $C -P$P.SU_RR=$(hx $((su[0]+1)) ${su[1]} ${su[2]} ${su[3]}) &
  row FAIL ${n}_su0_rr-1 2 $B $L $T $C -P$P.SU_RR=$(hx $((su[0]-1)) ${su[1]} ${su[2]} ${su[3]}) &
  row FAIL ${n}_su2_wr+1 2 $B $L $T $C -P$P.SU_WR=$(hx ${suw[0]} ${suw[1]} $((suw[2]+1)) ${suw[3]}) &
  row FAIL ${n}_su2_wr-1 2 $B $L $T $C -P$P.SU_WR=$(hx ${suw[0]} ${suw[1]} $((suw[2]-1)) ${suw[3]}) &
  row FAIL ${n}_leg_nrr0+1 2 $B $C $T -P$P.DNRQ=$(hx ${nrq[*]}) -P$P.DNRR=$(hx $((nrr[0]+1)) ${nrr[1]} ${nrr[2]} ${nrr[3]}) -P$P.DCRQ=$(hx ${crq[*]}) -P$P.DCRR=$(hx ${crr[*]}) -P$P.DHRQ=$(hx ${hrq[*]}) -P$P.DHRR=$(hx ${hrr[*]}) &
  wait
}
# legs (landed stages, LG0..3) read from the event bind: NRQ NRR CRQ CRR HRQ HRR
if [ $# -ge 1 ]; then while read -r n rest; do q $n $rest; done < "$1"
else q ZERO 0 0 0 0  0 0 0 0  0 0 0 0  0 0 0 0  0 0 0 0  0 0 0 0; fi
[ $bad = 0 ] && echo "LAT_CHAIN GATE PASS" || echo "LAT_CHAIN GATE FAIL"
exit $bad
