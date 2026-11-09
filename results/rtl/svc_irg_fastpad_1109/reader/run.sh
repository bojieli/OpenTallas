#!/bin/bash
# IRG fastpad READER bench (epyc7).  usage: run.sh <unguarded|guarded> <KR> [plusargs...]
# src/ = git archive of claude/die-s81-85-irg-fastpad-1109 (b9200f3611, rtl); rg2_guard.sv = dsdv_idx_rg2.sv + guard.
# The reader (dsdv_idx_rg3, original chunks) is from src/; chk_ref = original chunk text, chk_fp = the same chunk text
# under OT_IDX_HSLICE_FASTPAD from src/ (unguarded) or rg2_guard.sv (guarded).
set -euo pipefail
cd "$(dirname "$0")"
B=$PWD; V=/home/ubuntu/.local/opentallas-tools/bin/verilator
var=$1; kr=$2; shift 2
W=$B/build_${var}_kr$kr; mkdir -p $W
R=$B/src/rtl
RG2=$R/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv
case $var in unguarded) FPSRC=$RG2; DEF= ;; guarded) FPSRC=$B/rg2_guard.sv; DEF=+define+GUARD ;; *) exit 3 ;; esac
ext() { awk '/^module dsdv_idx_rg2_chunk \(/{p=1} p{print} p&&/^endmodule/{exit}' $1; }
ext $RG2 | sed 's/^module dsdv_idx_rg2_chunk (/module chk_ref (/' > $W/chk_ref.sv
{ echo '`define OT_IDX_HSLICE_FASTPAD'; ext $FPSRC | sed 's/^module dsdv_idx_rg2_chunk (/module chk_fp (/'; echo '`undef OT_IDX_HSLICE_FASTPAD'; } > $W/chk_fp.sv
if [ ! -x $W/obj/Vtb ]; then
$V --binary --timing -j 32 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-TIMESCALEMOD --x-initial unique \
   --top-module tb -GKR=$kr $DEF -Mdir $W/obj \
   $R/lib/ot_rst_relay.sv $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_prefix.sv $R/hdc/ot_hdc_fastfp.sv \
   $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/ot_hdc_fp32_add_lat_nr.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv \
   $R/hdc/v41x/ot_hdc_v41x_idx_hslice.sv $R/hdc/v41x/ot_hdc_v41x_idx_hslice_fp.sv \
   $RG2 $R/dsrom_sys/s81_dv/idx/dsdv_idx_rg3.sv $W/chk_ref.sv $W/chk_fp.sv $B/tb.sv > $W/build.log 2>&1 \
   || { grep -m10 '%Error' $W/build.log; tail -5 $W/build.log; exit 2; }
fi
tag=$(echo "$*" | tr -d '+ =' ); tag=${tag:-default}
$W/obj/Vtb +verilator+rand+reset+0 "$@" > $W/sim_$tag.log 2>&1 || true
grep -E "^(D |kr|mismatch|PASS|FAIL|QBAD)" $W/sim_$tag.log | sed "s|^|[$var kr$kr $tag] |"
