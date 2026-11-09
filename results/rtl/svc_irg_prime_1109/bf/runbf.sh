#!/bin/bash
# banded flat (bf) reader bench, KR 1.  usage: runbf.sh <noprime|prime|mut> [plusargs]; inputs in src/ (stagebf.sh)
# u = dsdv_idx_rg3 #(KR 1, OH 1, RH 1) (no define), up = dsdv_idx_rg3_bf #(KR 1, RH 1, LX 0, PD 0) whose R band
# dsdv_idx_rg3_br is built with the variant's defines; tb = ../tb.sv +BF.
set -euo pipefail
cd "$(dirname "$0")"
B=$PWD; V=${VERILATOR:-/home/ubuntu/.local/opentallas-tools/bin/verilator}; S=$B/src; R=$S/rtl
var=$1; shift
W=$B/build_$var; mkdir -p $W
case $var in
  noprime) PDEF= ; TDEF= ;;
  prime)   PDEF='`define OT_IDX_RG3_PRIME' ; TDEF=+define+PRIME=6 ;;
  mut)     PDEF='`define OT_IDX_RG3_PRIME
`define OT_IDX_RG3_PRIME_MUT' ; TDEF=+define+PRIME=3 ;;
  *) exit 3 ;;
esac
{ echo "$PDEF"; cat $R/dsdv_idx_rg3_br.sv; echo '`undef OT_IDX_RG3_PRIME'; echo '`undef OT_IDX_RG3_PRIME_MUT'; } > $W/br.sv
if [ ! -x $W/obj/Vtb ]; then
$V --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD --x-initial unique \
   --top-module tb -GKR=1 +define+BF $TDEF -Mdir $W/obj \
   $R/lib/ot_rst_relay.sv $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_prefix.sv $R/hdc/ot_hdc_fastfp.sv \
   $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/ot_hdc_fp32_add_lat_nr.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv \
   $R/hdc/v41x/ot_hdc_v41x_idx_hslice.sv $R/hdc/v41x/ot_hdc_v41x_idx_hslice_fp.sv \
   $R/dsdv_idx_rg2.sv $S/ref_rg3.sv $W/br.sv $R/dsdv_idx_rg3_band.sv $R/dsdv_idx_rg3_bf.sv $S/chk_ref.sv $S/chk_fp.sv \
   $B/../tb.sv > $W/build.log 2>&1 || { grep -m10 '%Error' $W/build.log; tail -5 $W/build.log; exit 2; }
fi
tag=$(echo "$*" | tr -d '+ =' ); tag=${tag:-default}
$W/obj/Vtb +verilator+rand+reset+0 "$@" > $W/sim_$tag.log 2>&1 || echo "SIM_RC $?" >> $W/sim_$tag.log
grep -E "^(D |kr|mismatch|fail_open|out_diff|PASS|FAIL|PFWRONG|ODIFF|PK |MIS|SIM_RC)" $W/sim_$tag.log | sed "s|^|[bf $var $tag] |"
