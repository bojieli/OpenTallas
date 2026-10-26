#!/usr/bin/env bash
# Slot cells of the Qwen ROM TP8 KV-centre masters qkd_embgw / qkd_host: bit-exact bench through the cell's own ports
# (packing mutant with a 3rd argument).
#   bench.sh OUT_DIR CELL [mut|headq]      CELL = embgw
# Prints "PASS kv_gwhost <cell> ..." (rc 0) or "FAIL kv_gwhost <cell> ..." (rc 1).
set -u
OUT=$1; CELL=$2; MUT=${3:-}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
D=""; [ -n "$MUT" ] && D="-DOT_QKD_SLOT_MUT"; [ "$MUT" = headq ] && D="-DOT_QKD_HEADQ_MUT"   # headq: stale-head mutant (Q-KVFIX 0130)
E=$R/rtl/qwen_sys/emb_hbm_20261008/synth
K=$R/rtl/qwen_sys/kv_die_20261009
case "$CELL" in
  embgw) TB=tb_qkd_embgw_slot; SRC="$K/ot_qkvd_embgw_m.sv $E/ot_qfd_emb_gw.sv $E/ot_qfd_emb_strip.sv" ;;
  *) echo "FAIL kv_gwhost $CELL unknown cell"; exit 1 ;;
esac
iverilog -g2012 $D -s $TB -o "$OUT/tb_$CELL" "$R/rtl/test/$TB.sv" "$R/rtl/physical/ot_qwen_kv_gwhost_slots.sv" $SRC \
    > "$OUT/$CELL.build.log" 2>&1 || { cat "$OUT/$CELL.build.log"; echo "FAIL kv_gwhost $CELL build"; exit 1; }
vvp "$OUT/tb_$CELL" > "$OUT/$CELL.log" 2>&1
L=$(grep -E '^(PASS|FAIL) kv_gwhost' "$OUT/$CELL.log" | tail -1)
case "$L" in
  PASS*) echo "$L"; exit 0 ;;
  FAIL*) grep -E '^FAIL' "$OUT/$CELL.log" | head -5; echo "FAIL kv_gwhost $CELL${MUT:+ mutant detected} ${L#FAIL kv_gwhost $CELL}"; exit 1 ;;
  *) tail -5 "$OUT/$CELL.log"; echo "FAIL kv_gwhost $CELL no verdict"; exit 1 ;;
esac
