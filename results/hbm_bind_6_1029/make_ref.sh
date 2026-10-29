#!/usr/bin/env bash
# HBM-BIND-6: Yosys elaboration of the reference integration ot_hnx_fused_tree_top (N4EXT=1) with blackbox leaves.
# Two mechanical, value-preserving source edits for Yosys only: hops() integer-array table -> case table (values parsed
# from the original t[k] = v lines, asserted complete), and the N4EXT default 0 -> 1 (yosys 0.68 asserts on -chparam here).
set -eu
REF=${1:?ref dir with rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv (results/hbm_n4_native_1027/source_snapshot.tar.gz)}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$REF"
python3 - <<'PY'
import re
s = open("rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv").read()
m = re.search(r"function automatic integer hops\(input integer q, input integer kind\);.*?endfunction", s, re.S)
tab = dict((int(k), int(v)) for k, v in re.findall(r"t\[(\d+)\] = (\d+);", m.group(0)))
assert sorted(tab) == list(range(20))
new = ("function automatic integer hops(input integer q, input integer kind);\n        begin\n            case (5 * q + kind)\n"
       + "".join(f"                {k}: hops = {tab[k]};\n" for k in range(20))
       + "                default: hops = 0;\n            endcase\n        end\n    endfunction")
s = s.replace(m.group(0), new)
assert s.count("parameter integer N4EXT = 0") == 1
open("tree_top_yosys.sv", "w").write(s.replace("parameter integer N4EXT = 0", "parameter integer N4EXT = 1"))
PY
yosys -q -p "read_verilog -sv -DSYNTHESIS $HERE/ref_stubs.v tree_top_yosys.sv; hierarchy -top ot_hnx_fused_tree_top; proc; opt_clean; write_json ref_n4ext1.json"
sha256sum rtl/hbm_next/fused/tb/ot_hnx_fused_tree_top.sv tree_top_yosys.sv ref_n4ext1.json
