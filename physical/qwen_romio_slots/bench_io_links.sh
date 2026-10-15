#!/usr/bin/env bash
# Qwen ROM-side IO slot cells: bench through the cell's own ports (two cells back to back through the PHY pipe model,
# rtl/test/tb_qfd_link_adp512.sv = tb_qfd_link_adapter.sv with the DUT swapped by sed for qfd_link_adp512).
#   bench.sh OUT_DIR CASE      CASE = exact | rate | stall | mut | mut2
#     exact  1,500 words each way, random traffic + back-pressure, LAT 223, bit-exact in order, no fault
#     rate   line-rate sweep point at LAT 229 (223 PHY + 6 FDI relay stages of the cluster parent), >= 0.950 words/cycle
#     stall  3,000 words, long receiver stalls
#     mut    stall + MUT=1 (one extra link credit): must FAIL
#     mut2   exact + MUT=2 (slice 7's replicated skid read pointer does not advance): must FAIL
# Prints "PASS romio_slots <case> ..." (rc 0) or "FAIL romio_slots <case> ..." (rc 1).
set -u
OUT=$1; CASE=$2
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
T=tb_qfd_io_serdes
P="-P$T.RXD=512 -P$T.SRAM=1 -P$T.PINREG=1"
case "$CASE" in
  exact) P="$P -P$T.LAT=223 -P$T.N=1500" ;;
  rate)  P="$P -P$T.LAT=229 -P$T.N=2000 -P$T.RATE=1 -P$T.MINRATE=950" ;;
  stall) P="$P -P$T.LAT=223 -P$T.N=3000 -P$T.STALL=1 -P$T.SW=1500" ;;
  mut)   P="$P -P$T.LAT=223 -P$T.N=3000 -P$T.STALL=1 -P$T.SW=1500 -P$T.MUT=1" ;;
  mut2)  P="$P -P$T.LAT=223 -P$T.N=1500 -P$T.MUT=2" ;;
  *) echo "FAIL romio_slots $CASE unknown case"; exit 1 ;;
esac
iverilog -g2012 -s $T $P -o "$OUT/$T.$CASE" "$R/rtl/test/$T.sv" "$R/rtl/physical/ot_qwen_romio_slots.sv" "$R/rtl/physical/ot_qfd_link_adp512_split.sv" "$R/rtl/physical/ot_qfd_io_links.sv" \
    "$R/rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv" "$R/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv" \
    "$R/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" \
    > "$OUT/$CASE.build.log" 2>&1 || { cat "$OUT/$CASE.build.log"; echo "FAIL romio_slots $CASE build"; exit 1; }
vvp -n "$OUT/$T.$CASE" > "$OUT/$CASE.log" 2>&1
grep -E '^RATE' "$OUT/$CASE.log"
L=$(grep -E '^(PASS|FAIL) qfd_link_adp512' "$OUT/$CASE.log" | tail -1)
case "$L" in
  PASS*) echo "PASS romio_slots $CASE ${L#PASS qfd_link_adp512}"; exit 0 ;;
  FAIL*) echo "FAIL romio_slots $CASE ${L#FAIL qfd_link_adp512}"; exit 1 ;;
  *) tail -5 "$OUT/$CASE.log"; echo "FAIL romio_slots $CASE no verdict"; exit 1 ;;
esac
