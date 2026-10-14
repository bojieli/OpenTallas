#!/usr/bin/env bash
set -eu
OUT=$1;CASE=$2;mkdir -p "$OUT"
SRC=rtl/physical/ot_qfd_cbuf_ready_join8.sv
case "$CASE" in
 exact);;
 identity_mut|fault_cohort_mut)
 python3 - "$SRC" "$OUT/join_mut.sv" "$CASE" <<'PY'
import sys
s=open(sys.argv[1]).read()
a,b=('(&rdy_q)&&same&&!(|flt_q)','(&rdy_q)&&!(|flt_q)')if sys.argv[3]=='identity_mut'else('cb_fault<=|flt_q','cb_fault<=|fault')
assert s.count(a)==1
open(sys.argv[2],'w').write(s.replace(a,b))
PY
 SRC="$OUT/join_mut.sv";;
 *)exit 2;;
esac
sha256sum "$SRC" > "$OUT/source.sha256"
iverilog -g2012 -s tb_qfd_cbuf_ready_join8 -o "$OUT/sim" rtl/test/redesign_qwen/tb_qfd_cbuf_ready_join8.sv "$SRC" > "$OUT/build.log" 2>&1
vvp "$OUT/sim" > "$OUT/run.log" 2>&1
cat "$OUT/run.log"
grep -q '^PASS ready_join8 ' "$OUT/run.log"
