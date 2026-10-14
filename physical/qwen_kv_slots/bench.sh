#!/usr/bin/env bash
# Slot-shaped Qwen KV cells: bit-exact bench through the cell's own ports (mutant with a 3rd argument).
#   bench.sh OUT_DIR CELL [mut]      CELL = kvwq_ctl_bin
# Prints "PASS kv_slots <cell> ..." (rc 0) or "FAIL kv_slots <cell> ..." (rc 1).
set -u
OUT=$1; CELL=$2; MUT=${3:-}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
D=""; [ -n "$MUT" ] && D="-DOT_QKD_SLOT_MUT"
case "$CELL" in
  kvwq_ctl_bin) TB=tb_qkd_kvwq_ctl_bin_slot; SRC="$R/rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_wq_ctl_binary.sv" ;;
  *) echo "FAIL kv_slots $CELL unknown cell"; exit 1 ;;
esac
iverilog -g2012 $D -o "$OUT/tb_$CELL" "$R/rtl/test/$TB.sv" "$R/rtl/physical/ot_qwen_kv_slot_wrappers.sv" $SRC \
    > "$OUT/$CELL.build.log" 2>&1 || { cat "$OUT/$CELL.build.log"; echo "FAIL kv_slots $CELL build"; exit 1; }
vvp "$OUT/tb_$CELL" > "$OUT/$CELL.log" 2>&1
L=$(grep -E '^(PASS|FAIL) kv_slots' "$OUT/$CELL.log" | tail -1)
case "$L" in
  PASS*) echo "$L"; exit 0 ;;
  FAIL*) echo "FAIL kv_slots $CELL${MUT:+ mutant detected} ${L#FAIL kv_slots $CELL}"; exit 1 ;;
  *) tail -5 "$OUT/$CELL.log"; echo "FAIL kv_slots $CELL no verdict"; exit 1 ;;
esac
