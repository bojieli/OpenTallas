#!/usr/bin/env bash
# Slot-shaped Qwen ROM station cells: bit-exact bench (and mutant with a 3rd argument).
#   bench.sh OUT_DIR CELL [mut]      CELL = cst_s | cst_n | chead_w | chead_e
# Prints "PASS station_slots <cell> ..." (rc 0) or "FAIL station_slots <cell> ..." (rc 1).
set -u
OUT=$1; CELL=$2; MUT=${3:-}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
D="-DCELL_$(echo "$CELL" | tr a-z A-Z)"
[ -n "$MUT" ] && D="$D -DOT_QFD_STATION_MUT"
iverilog -g2012 $D -o "$OUT/tb_$CELL" "$R/rtl/test/tb_qwen_die_station_slots.sv" \
    "$R/rtl/physical/ot_qwen_die_station_slots.sv" "$R/rtl/physical/ot_qwen_die_station.sv" > "$OUT/$CELL.build.log" 2>&1 \
    || { cat "$OUT/$CELL.build.log"; echo "FAIL station_slots $CELL build"; exit 1; }
vvp "$OUT/tb_$CELL" > "$OUT/$CELL.log" 2>&1
L=$(grep -E '^(PASS|FAIL) station_slots' "$OUT/$CELL.log" | tail -1)
case "$L" in
  PASS*) echo "PASS station_slots $CELL ${L#PASS station_slots }"; exit 0 ;;
  FAIL*) echo "FAIL station_slots $CELL${MUT:+ mutant detected} ${L#FAIL station_slots }"; exit 1 ;;
  *) tail -5 "$OUT/$CELL.log"; echo "FAIL station_slots $CELL no verdict"; exit 1 ;;
esac
