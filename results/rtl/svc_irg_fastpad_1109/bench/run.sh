#!/bin/bash
# IRG fastpad bench (epyc7).  usage: run.sh <variant: good|mut_m1|mut_p1> <seed> <rows> <hb...>
# one variant per build dir; run variants in parallel, seeds of one variant in sequence.
# src/ = git archive of claude/die-s81-85-irg-fastpad-1109 (rtl only).  Chunk copies are extracted verbatim from
# src/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv: chk_ref (default text) and chk_fp (same text, OT_IDX_HSLICE_FASTPAD).
set -euo pipefail
cd "$(dirname "$0")"
B=$PWD; V=/home/ubuntu/.local/opentallas-tools/bin/verilator
var=$1; seed=$2; rows_req=$3; shift 3
W=$B/build_$var; mkdir -p $W
RG2=$B/src/rtl/dsrom_sys/s81_dv/idx/dsdv_idx_rg2.sv
awk '/^module dsdv_idx_rg2_chunk \(/{p=1} p{print} p&&/^endmodule/{exit}' $RG2 > $W/chunk.sv
sed 's/^module dsdv_idx_rg2_chunk (/module chk_ref (/' $W/chunk.sv > $W/chk_ref.sv
{ echo '`define OT_IDX_HSLICE_FASTPAD'; echo '`define OT_IDX_HSLICE_FP_CS'; sed 's/^module dsdv_idx_rg2_chunk (/module chk_fp (/' $W/chunk.sv; echo '`undef OT_IDX_HSLICE_FP_CS'; echo '`undef OT_IDX_HSLICE_FASTPAD'; } > $W/chk_fp.sv
# DIE-S81-85 11-10: the census-safe S81 svc copy (OT_IDX_HSLICE_FP_CS) is the DUT
FP=$B/src/rtl/dsrom_sys/s81_svc/ot_s81_svc_idx_hslice_fp.sv
case $var in
  good)   cp $FP $W/hslice_fp.sv ;;
  mut_m1) sed -e 's/default: pad_q = pad\[TW\*(7\*FPL)-1 -: TW\];/default: pad_q = pad[TW*(7*FPL-1)-1 -: TW];/' \
              -e 's/default: pad_q\[pb\] = pad\[TW\*(7\*FPL-1) + pb\];/default: pad_q[pb] = pad[TW*(7*FPL-2) + pb];/' $FP > $W/hslice_fp.sv ;;
  mut_p1) sed -e 's/localparam integer PD = FPL \* (HC - 1);/localparam integer PD = FPL * (HC - 1) + 1;/' \
              -e 's/default: pad_q = pad\[TW\*(7\*FPL)-1 -: TW\];/default: pad_q = pad[TW*(7*FPL+1)-1 -: TW];/' \
              -e 's/default: pad_q\[pb\] = pad\[TW\*(7\*FPL-1) + pb\];/default: pad_q[pb] = pad[TW*(7*FPL) + pb];/' $FP > $W/hslice_fp.sv ;;
esac
if [ $var != good ] && cmp -s $FP $W/hslice_fp.sv; then echo "mutant sed did not apply"; exit 3; fi
diff $FP $W/hslice_fp.sv > $W/mutant.diff || true
R=$B/src/rtl
$V --binary --timing -j 16 -Wno-fatal -Wno-lint -Wno-style --x-initial unique --top-module tb -Mdir $W/obj \
   $R/lib/ot_reset_sync.sv $R/lib/ot_rst_relay.sv $R/hdc/ot_hdc_delay.sv $R/hdc/ot_hdc_prefix.sv $R/hdc/ot_hdc_fastfp.sv \
   $R/hdc/ot_hdc_fp32_add_lat.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith.sv $R/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv \
   $R/hdc/v41x/ot_hdc_v41x_idx_hslice.sv $R/dsrom_sys/s81_svc/ot_s81_svc_fp32_add_lat_cs.sv $W/hslice_fp.sv $W/chk_ref.sv $W/chk_fp.sv $B/tb.sv > $W/build.log 2>&1 \
   || { tail -30 $W/build.log; exit 2; }
T=$W/s$seed; mkdir -p $T
python3 -I $B/gen_trace.py $seed $rows_req $T/trace.hex > $T/gen.log
rows=$(wc -l < $T/trace.hex)
for hb in "$@"; do
  ( cd $T && $W/obj/Vtb +verilator+rand+reset+0 +hb=$hb +rows=$rows > $T/sim_hb${hb}.log 2>&1 ) || true
  grep -E "^(hb|all_cycle|PASS|FAIL)" $T/sim_hb${hb}.log | sed "s|^|[$var s$seed] |"
done
