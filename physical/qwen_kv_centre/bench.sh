#!/usr/bin/env bash
# Qwen ROM TP8 KV-centre cells: benches through the cells' own ports (iverilog).
#   bench.sh OUT_DIR seq_equiv [mut|fmut4|fmut5|cov]   cluster qkd_seq == flat ot_qkvd_kv_seq_merged, cycle for cycle
#        mut: the parent's wiring mutant (OT_QKD_SEQ_MUT); fmut4: credit join = OR in the flat side (row credit
#        overrun); fmut5: the ROM sequencer's program copy lands one address up in the flat side; cov: a run too short to cover the traffic (+NL=8) -> must be REFUSED ("coverage refused")
#   bench.sh OUT_DIR rstseq [mut]                qkd_rstseq == ot_qwen_sys_rst_seq + order properties
# Prints "PASS kv_centre <cell> ..." (rc 0) or "FAIL kv_centre <cell> ..." (rc 1).
set -u
OUT=$1; CELL=$2; MODE=${3:-}
R=$(cd "$(dirname "$0")/../.." && pwd)
mkdir -p "$OUT"
SRC="$R/rtl/physical/ot_qwen_kv_centre_slots.sv $R/rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_seq_merged.sv
 $R/rtl/qwen_sys/kv_die_20261009/ot_qkvd_fifo.sv $R/rtl/qwen_sys/system_20261008/ot_qfd_dctl.sv
 $R/rtl/qwen_sys/kv_die_20261009/ot_qkvd_kv_desc.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/qwen_sys/ot_qwen_sys_rst_seq.sv
 $R/rtl/lib/ot_reset_sync.sv"
D=""; A=""
case "$CELL" in
  seq_equiv) TB=tb_qkd_seq_equiv
     case "$MODE" in mut) D="-DOT_QKD_SEQ_MUT";; fmut4) D="-Ptb_qkd_seq_equiv.FMUT=4";; fmut5) D="-Ptb_qkd_seq_equiv.FMUT=5";; cov) A="+NL=8";; "") ;; *) echo "FAIL kv_centre $CELL unknown mode $MODE"; exit 1;; esac ;;
  rstseq) TB=tb_qkd_rstseq
     case "$MODE" in mut) D="-DOT_QKD_RSTSEQ_MUT";; "") ;; *) echo "FAIL kv_centre $CELL unknown mode $MODE"; exit 1;; esac ;;
  *) echo "FAIL kv_centre $CELL unknown cell"; exit 1 ;;
esac
iverilog -g2012 $D -o "$OUT/tb_$CELL$MODE" "$R/rtl/test/$TB.sv" $SRC > "$OUT/$CELL$MODE.build.log" 2>&1 || {
  cat "$OUT/$CELL$MODE.build.log"; echo "FAIL kv_centre $CELL build"; exit 1; }
vvp "$OUT/tb_$CELL$MODE" $A > "$OUT/$CELL$MODE.log" 2>&1
grep -E '^COUNTS' "$OUT/$CELL$MODE.log" | tail -1
L=$(grep -E '^(PASS|FAIL) kv_centre' "$OUT/$CELL$MODE.log" | tail -1)
case "$L" in
  PASS*) echo "$L"; exit 0 ;;
  FAIL*) echo "$L${MODE:+ [mode $MODE]}"; exit 1 ;;
  *) tail -5 "$OUT/$CELL$MODE.log"; echo "FAIL kv_centre $CELL no verdict"; exit 1 ;;
esac
