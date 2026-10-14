#!/usr/bin/env bash
# qfd_io_xfifo leaf partition benches (through the cell's own ports, against the flat module).
#   bench_xf.sh OUT_DIR CASE     CASE = ch | ch_fast | ch_neg | ch_mut
#     ch       qfd_xf_ch == ot_qwen_die_cdc_ch #(1024, 2) on every edge + scoreboard, 3,000 words, wck 2.0 / rck 2.7 ns
#     ch_fast  the same with the faster reader (wck 2.7 / rck 2.0 ns: the RX orientation of the master)
#     ch_neg   the sender ignores credits: must FAIL
#     ch_mut   OT_XF_MUT (two output data bits swapped in the cell): must FAIL
set -u
OUT=$1; CASE=$2; WIDTH=${3:-1024}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
T=tb_qfd_xf_ch; P="-Ptb_qfd_xf_ch.W=$WIDTH"; D=""
case "$CASE" in
  ch) ;;
  ch_fast) P="$P -P$T.HW=1.35 -P$T.HR=1.0" ;;
  ch_neg)  P="$P -P$T.NEG=1" ;;
  ch_mut)  D="-DOT_XF_MUT" ;;
  *) echo "FAIL xfifo_slots $CASE unknown case"; exit 1 ;;
esac
iverilog -g2012 -s $T $P $D -o "$OUT/$T.$CASE" "$R/rtl/test/$T.sv" "$R/rtl/physical/ot_qwen_xfifo_slots.sv" \
    "$R/rtl/physical/ot_qwen_die_cdc_ch.sv" "$R/rtl/physical/ot_qwen_async_fifo_w.sv" "$R/rtl/lib/ot_async_fifo.sv" \
    "$R/rtl/lib/ot_reset_sync.sv" > "$OUT/$CASE.build.log" 2>&1 || { cat "$OUT/$CASE.build.log"; echo "FAIL xfifo_slots $CASE build"; exit 1; }
vvp -n "$OUT/$T.$CASE" > "$OUT/$CASE.log" 2>&1
L=$(grep -E '^(PASS|FAIL) qfd_xf_ch' "$OUT/$CASE.log" | tail -1)
case "$L" in
  PASS*) echo "PASS xfifo_slots $CASE ${L#PASS qfd_xf_ch}"; exit 0 ;;
  FAIL*) echo "FAIL xfifo_slots $CASE ${L#FAIL qfd_xf_ch}"; exit 1 ;;
  *) tail -5 "$OUT/$CASE.log"; echo "FAIL xfifo_slots $CASE no verdict"; exit 1 ;;
esac
