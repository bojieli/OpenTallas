#!/bin/bash
# bench_s81_rst_window.sh [REPO]: iverilog runs of tb_s81_rst_window (S81 die reset window at the hard-core rst_n pin).
# Step 0 re-extracts ot_dp_rsync_s2 / ot_dp_rrelay from REPO/tools/die_plan/gen_rtl.py CELLS and requires the committed
# s81_reset_cells.v to be identical (the bench measures the generator RTL actually emitted for the S81 die).
set -u
D=$(cd "$(dirname "$0")" && pwd)
R=${1:-$(cd "$D/../../.." && pwd)}
T=$(mktemp -d)
python3 -I - "$R/tools/die_plan/gen_rtl.py" "$T/cells.v" <<'PY'
import re, sys
t = open(sys.argv[1]).read()
out = []
for name in ["ot_dp_rsync_s2", "ot_dp_rrelay"]:
    m = re.search(r"((?:\(\*[^\n]*\*\)\n)*module " + name + r"\b.*?\nendmodule\n)", t, re.S)
    out.append(m.group(1))
open(sys.argv[2], "w").write("// extracted verbatim from tools/die_plan/gen_rtl.py CELLS (origin/main)\n`timescale 1ns/1ps\n" + "\n".join(out))
PY
if cmp -s "$T/cells.v" "$D/s81_reset_cells.v"; then echo "CELLS_MATCH gen_rtl.py"; else echo "FATAL: s81_reset_cells.v differs from gen_rtl.py CELLS"; fi
run() { iverilog -g2012 -o "$T/sim_$1" "${@:2}" "$D/s81_reset_cells.v" "$D/tb_s81_rst_window.sv" && vvp -n "$T/sim_$1" > "$T/$1.log";
        echo "--- $1 (${*:2})"; grep -E "S81RST" "$T/$1.log"; echo "FATAL lines: $(grep -c FATAL "$T/$1.log")"; grep -m1 FATAL "$T/$1.log" || true; }
run pos2    -Ptb_s81_rst_window.CONTRACT=2
run tight3  -Ptb_s81_rst_window.CONTRACT=3
run need8   -Ptb_s81_rst_window.CONTRACT=8
run mut1    -Ptb_s81_rst_window.CONTRACT=2 -Ptb_s81_rst_window.MUT=1
run prop16  -Ptb_s81_rst_window.CONTRACT=16 -Ptb_s81_rst_window.PROP=16
run prop8m  -Ptb_s81_rst_window.CONTRACT=16 -Ptb_s81_rst_window.PROP=8
rm -rf "$T"
