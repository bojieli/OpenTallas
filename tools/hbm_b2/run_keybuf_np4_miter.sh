#!/bin/bash
# Run through ot-run; use a fresh output directory to retain all earlier verdicts.
set -euo pipefail
KEYBUF_ROOT=$(cd "$(dirname "$0")/../.." && pwd)
KEYBUF_OUT=${1:?usage: run_keybuf_np4_miter.sh NEW_OUTPUT_DIR}
if [ -d "$KEYBUF_OUT" ] && [ -n "$(ls -A "$KEYBUF_OUT")" ];then echo 'refusing nonempty output directory' >&2;exit 2;fi
mkdir -p "$KEYBUF_OUT"
KEYBUF_RTL=$KEYBUF_ROOT/rtl/hbm_next/idxn
KEYBUF_MEM=$KEYBUF_ROOT/physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v
KEYBUF_TB=$KEYBUF_ROOT/rtl/test/hbm_keybuf_np4_1029/tb_keybuf_np4.sv
for mut in 0 1 2 3;do
  iverilog -g2012 -s tb_keybuf_np4 -Ptb_keybuf_np4.MUT=$mut -o "$KEYBUF_OUT/mut${mut}.vvp" "$KEYBUF_TB" "$KEYBUF_RTL/ot_hnx_idxn_keybuf.sv" "$KEYBUF_RTL/ot_hnx_idxn_keybuf_slice.sv" "$KEYBUF_RTL/ot_hnx_idxn_keybuf_sliced_np4.sv" "$KEYBUF_MEM" >"$KEYBUF_OUT/compile${mut}.log" 2>&1
  set +e
  vvp "$KEYBUF_OUT/mut${mut}.vvp" >"$KEYBUF_OUT/mut${mut}.log" 2>&1
  rc=$?
  set -e
  if [ "$mut" = 0 ];then
    [ "$rc" = 0 ] && grep -q '^NP4_PASS' "$KEYBUF_OUT/mut0.log" || { cat "$KEYBUF_OUT/mut0.log";exit 1; }
  else
    [ "$rc" != 0 ] && grep -q 'LOCKSTEP_' "$KEYBUF_OUT/mut${mut}.log" || { cat "$KEYBUF_OUT/mut${mut}.log";exit 1; }
  fi
  echo "MUT=$mut RC=$rc";tail -2 "$KEYBUF_OUT/mut${mut}.log"
done
cat >"$KEYBUF_OUT/rs_bad.sv" <<'SV'
module rs_bad;
 wire [4395:0]k;wire f;
 ot_hnx_idxn_keybuf_sliced_np4 #(.NP(4),.RS(1)) d(.clk(1'b0),.rst_n(1'b0),.clear(1'b0),.pbase(3'd0),.live_v(1'b0),.live_index(8'd0),.key_in(4396'd0),.pre_v(1'b0),.pre_index(8'd0),.replay_v(1'b0),.replay_index(8'd0),.key_out(k),.fault(f));
endmodule
SV
set +e
iverilog -g2012 -s rs_bad -o "$KEYBUF_OUT/rs_bad.vvp" "$KEYBUF_OUT/rs_bad.sv" "$KEYBUF_RTL/ot_hnx_idxn_keybuf_slice.sv" "$KEYBUF_RTL/ot_hnx_idxn_keybuf_sliced_np4.sv" "$KEYBUF_MEM" >"$KEYBUF_OUT/rs_bad.log" 2>&1
rc=$?
set -e
[ "$rc" != 0 ] && grep -q 'ERROR_keybuf_sliced_np4_requires_RS_zero' "$KEYBUF_OUT/rs_bad.log"
python3 - "$KEYBUF_RTL" <<'PY'
from pathlib import Path
import re,sys
r=Path(sys.argv[1]);a=(r/'ot_hnx_idxn_quarter_with_keybuf.sv').read_text();b=(r/'ot_hnx_idxn_quarter_with_keybuf_sliced.sv').read_text()
a=a[re.search(r'^module ',a,re.M).start():];b=b[re.search(r'^module ',b,re.M).start():].replace('module ot_hnx_idxn_quarter_with_keybuf_sliced #(','module ot_hnx_idxn_quarter_with_keybuf #(').replace('ot_hnx_idxn_keybuf_sliced_np4 #(.NP(4),.RS(0)) keybuf','ot_hnx_idxn_keybuf #(.NP(4),.RS(0)) keybuf')
assert a==b,'quarter changed beyond the explicit replay-buffer selector'
print('QUARTER_BODY_IDENTITY PASS')
PY
echo 'NP4_RUN_PASS'
