#!/bin/bash
# Behavioural gate of the static x2-pair column entry dsfd_cfifo (S-ELEM-PQ/COLL 2026-10-16, VIS-ROM S81F-02).
# usage: cfifo_x2pair_gate.sh pass|warm|mut_payload|mut_valid|mut_clock|mut_ripin|mut_stop_s <outdir>
#   mut_ripin    r3: rr takes ri directly (no north pin register) -> status latency mutant must fail
#   pass         5 forwarded-clock phase pairs (xf, xf2 vs cr): every word exact on both lanes, fixed epoch, status
#   warm         same five phases across explicit cold and warm resets, fixed first-output epoch
#   mut_clock    invert the actual xf2 source of u_x2 -> clock/epoch mutant must fail
#   mut_payload  x2 lane takes cc/x1 bits for x2[3:1]           -> must print CFIFO_X2 FAIL
#   mut_valid    x2 lane valid forced 0 (lane-pair fault path)  -> must print CFIFO_X2 FAIL
set -euo pipefail
MODE=${1:?mode}; OUT=${2:?outdir}; mkdir -p "$OUT"
R=$(cd "$(dirname "$0")/../.." && pwd)
DUT=$R/rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_x2pair.sv
LIB="$R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress.sv $R/rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross.sv"
TB=$R/rtl/dsrom_sys/s81_die_bind/test/tb_dsfd_cfifo_x2pair.sv
STOP_S=0
case $MODE in
  pass|warm) PAIRS="2:2 0:0 3:4 7:7 9:8";;
  mut_payload) sed 's/xw_\[568:566\]/xw_[566:564]/' "$DUT" > "$OUT/dut.sv"; cmp -s "$DUT" "$OUT/dut.sv" && { echo "MUTANT NOT APPLIED"; exit 3; }; DUT=$OUT/dut.sv; PAIRS="2:2";;
  mut_valid) sed "s/\.i(xd2)/.i({xd2[537:2], xd2[1:0] \& 2'b01})/" "$DUT" > "$OUT/dut.sv"; cmp -s "$DUT" "$OUT/dut.sv" && { echo "MUTANT NOT APPLIED"; exit 3; }; DUT=$OUT/dut.sv; PAIRS="2:2";;
  mut_clock) sed 's/\.f_ck(xf2)/.f_ck(~xf2)/' "$DUT" > "$OUT/dut.sv"; cmp -s "$DUT" "$OUT/dut.sv" && { echo "MUTANT NOT APPLIED"; exit 3; }; DUT=$OUT/dut.sv; PAIRS="2:2";;
  mut_stop_s) STOP_S=1; PAIRS="2:2";;
  mut_ripin) sed 's/sti\[0\], ri_q}/sti[0], ri}/' "$DUT" > "$OUT/dut.sv"; cmp -s "$DUT" "$OUT/dut.sv" && { echo "MUTANT NOT APPLIED"; exit 3; }; DUT=$OUT/dut.sv; PAIRS="2:2";;
  *) echo "bad mode $MODE"; exit 2;;
esac
WARM=0; [ "$MODE" != warm ] || WARM=1
fail=0; n=0
for p in $PAIRS; do
  a=${p%:*}; b=${p#*:}
  iverilog -g2012 -Ptb_dsfd_cfifo_x2pair.PHA=$a -Ptb_dsfd_cfifo_x2pair.PHB=$b -Ptb_dsfd_cfifo_x2pair.WARM=$WARM -Ptb_dsfd_cfifo_x2pair.STOP_S=$STOP_S -o "$OUT/sim_$a$b" "$TB" "$DUT" $LIB
  line=$(vvp -n "$OUT/sim_$a$b" | grep -E "CFIFO_X2 (PASS|FAIL)" | tail -1); echo "$line"
  case "$line" in *PASS*) n=$((n+1));; *) fail=1;; esac
done
if [ $fail = 0 ]; then echo "CFIFO_X2_GATE PASS $n phase pairs"; else echo "CFIFO_X2_GATE FAIL"; exit 1; fi
