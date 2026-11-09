#!/bin/bash
# IRG rg3 PRIME bench (intel2).  usage: run.sh <noprime|prime|mut> <KR> [plusargs...]
# u  = dsdv_idx_rg3 at 9b6810c755 (git show), the reference reader;
# up = this tree's dsdv_idx_rg3.sv renamed dsdv_idx_rg3_p, with the variant's defines;
# chk_ref = original dsdv_idx_rg2_chunk, chk_fp = OT_IDX_HSLICE_FASTPAD chunk of b9200f3611 (no 9b6810c755 guard).
set -euo pipefail
cd "$(dirname "$0")"
B=$PWD; V=/home/ubuntu/.local/opentallas-tools/bin/verilator
G=$(git rev-parse --show-toplevel); R=$G/rtl
var=$1; kr=$2; shift 2
W=$B/build_${var}_kr$kr; mkdir -p $W
case $var in
  noprime) PDEF= ; TDEF= ;;
  prime)   PDEF='`define OT_IDX_RG3_PRIME' ; TDEF=+define+PRIME=6 ;;
  mut)     PDEF='`define OT_IDX_RG3_PRIME
`define OT_IDX_RG3_PRIME_MUT' ; TDEF=+define+PRIME=3 ;;
  *) exit 3 ;;
esac
RG2=$R/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv
ext() { awk '/^module dsdv_idx_rg2_chunk \(/{p=1} p{print} p&&/^endmodule/{exit}'; }
git -C $G show 9b6810c755:rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv > $W/rg3_ref.sv
{ echo "$PDEF"; sed 's/^module dsdv_idx_rg3 #(/module dsdv_idx_rg3_p #(/' $R/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv;
  echo '`undef OT_IDX_RG3_PRIME'; echo '`undef OT_IDX_RG3_PRIME_MUT'; } > $W/rg3_p.sv
ext < $RG2 | sed 's/^module dsdv_idx_rg2_chunk (/module chk_ref (/' > $W/chk_ref.sv
{ echo '`define OT_IDX_HSLICE_FASTPAD'; git -C $G show b9200f3611:rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv | ext |
  sed 's/^module dsdv_idx_rg2_chunk (/module chk_fp (/'; echo '`undef OT_IDX_HSLICE_FASTPAD'; } > $W/chk_fp.sv
if [ ! -x $W/obj/Vtb ]; then
$V --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD --x-initial unique \
   --top-module tb -GKR=$kr $TDEF -Mdir $W/obj \
   $R/lib/ot_rst_relay.sv $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_prefix.sv $R/hdc/ot_hdc_fastfp.sv \
   $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/ot_hdc_fp32_add_lat_nr.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv \
   $R/hdc/v41x/ot_hdc_v41x_idx_hslice.sv $R/hdc/v41x/ot_hdc_v41x_idx_hslice_fp.sv \
   $RG2 $W/rg3_ref.sv $W/rg3_p.sv $W/chk_ref.sv $W/chk_fp.sv $B/tb.sv > $W/build.log 2>&1 \
   || { grep -m10 '%Error' $W/build.log; tail -5 $W/build.log; exit 2; }
fi
tag=$(echo "$*" | tr -d '+ =' ); tag=${tag:-default}
$W/obj/Vtb +verilator+rand+reset+0 "$@" > $W/sim_$tag.log 2>&1 || echo "SIM_RC $?" >> $W/sim_$tag.log
grep -E "^(D |kr|mismatch|fail_open|out_diff|PASS|FAIL|PFWRONG|ODIFF|PK |MIS|SIM_RC)" $W/sim_$tag.log | sed "s|^|[$var kr$kr $tag] |"
