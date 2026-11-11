#!/bin/bash
# STM-DQ EQ gate driver.  From the repo root:  bash rtl/test/qwen_dv/static_stream/stmdq_eq.sh <out_dir>  (needs yosys)
# PASS: "STMDQ_EQ_GATE PROVEN" (every $equiv proven for the tile and the chain-END se0 stream half).
set -uo pipefail
OUT=${1:?out_dir}; mkdir -p "$OUT"; H=rtl/test/qwen_dv/static_stream
sed 's/^module qfd_dv_stream_tile #(/module qfd_dv_stream_tile_def #(/' rtl/qwen_dv/qfd_dv_stream_tile.sv > "$OUT/tile_def.sv"
sed 's/^module qfd_dv_stream_tile #(/module qfd_dv_stream_tile_dq #(/' rtl/qwen_dv/qfd_dv_stream_tile.sv > "$OUT/tile_dq.sv"
python3 -I - rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv "$OUT" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
m = re.search(r"^module qfd_dv_stream_tile_se0\b.*?^endmodule\b", t, re.S | re.M).group(0)
for tag in ("def", "dq"):
    open(f"{sys.argv[2]}/se0_{tag}.sv", "w").write("`timescale 1ns/1ps\n" + m.replace("module qfd_dv_stream_tile_se0", f"module qfd_dv_stream_tile_se0_{tag}", 1) + "\n")
PY
cp $H/stmdq_eq_wrap.sv $H/stmdq_eq.ys $H/stmdq_eq.blacklist "$OUT/"
sha256sum rtl/qwen_dv/qfd_dv_stream_tile.sv rtl/qwen_dv/s5/s8/qfd_dv_s8_ce.sv
( cd "$OUT" && yosys -q -l stmdq_eq.log stmdq_eq.ys ); rc=$?
cat "$OUT/stmdq_eq_status_tile.txt" "$OUT/stmdq_eq_status_se0.txt" 2>/dev/null | grep -i "found\|proven"
[ $rc -eq 0 ] && echo "STMDQ_EQ_GATE PROVEN" || echo "STMDQ_EQ_GATE NOT_PROVEN rc=$rc"
exit $rc
