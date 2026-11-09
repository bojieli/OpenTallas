#!/bin/bash
# bound-b178 reader bench (any host; inputs in src/ from stage178.sh).  usage: run178.sh <noprime|prime|mut> <m> [plusargs]
# m = dsdv_idx_rg3 (u_irg_00..06) | dsdv_idx_rg3_nq_native (u_irg_07 via dsdv_idx_rg3_nq).  KR 0 (as bound).
# u = rg3_ref_m (bound source as is), up = rg3_p_m (bound source + prime patch, variant defines); tb = ../tb.sv +PF178.
set -euo pipefail
cd "$(dirname "$0")"
B=$PWD; V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/bin/verilator}; S=$B/src; R=$S/rtl
var=$1; m=$2; shift 2
W=$B/build_${var}_$m; mkdir -p $W
case $var in
  noprime) PDEF= ; TDEF= ;;
  prime)   PDEF='`define OT_IDX_RG3_PRIME' ; TDEF=+define+PRIME=6 ;;
  mut)     PDEF='`define OT_IDX_RG3_PRIME
`define OT_IDX_RG3_PRIME_MUT' ; TDEF=+define+PRIME=3 ;;
  *) exit 3 ;;
esac
{ echo "$PDEF"; cat $S/p_$m.sv; echo '`undef OT_IDX_RG3_PRIME'; echo '`undef OT_IDX_RG3_PRIME_MUT'; } > $W/rg3_p.sv
if [ ! -x $W/obj/Vtb ]; then
$V --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD --x-initial unique \
   --top-module tb -GKR=0 +define+PF178 $TDEF -Mdir $W/obj \
   $R/lib/ot_rst_relay.sv $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_prefix.sv $R/hdc/ot_hdc_fastfp.sv \
   $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/ot_hdc_fp32_add_lat_nr.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv \
   $R/hdc/v41x/ot_hdc_v41x_idx_hslice.sv $R/hdc/v41x/ot_hdc_v41x_idx_hslice_fp.sv \
   $R/dsdv_idx_rg2.sv $S/ref_$m.sv $W/rg3_p.sv $S/chk_ref.sv $S/chk_fp.sv $B/../tb.sv > $W/build.log 2>&1 \
   || { grep -m10 '%Error' $W/build.log; tail -5 $W/build.log; exit 2; }
fi
tag=$(echo "$*" | tr -d '+ =' ); tag=${tag:-default}
$W/obj/Vtb +verilator+rand+reset+0 "$@" > $W/sim_$tag.log 2>&1 || echo "SIM_RC $?" >> $W/sim_$tag.log
grep -E "^(D |kr|mismatch|fail_open|out_diff|PASS|FAIL|PFWRONG|ODIFF|PK |MIS|SIM_RC)" $W/sim_$tag.log | sed "s|^|[$var $m $tag] |"
