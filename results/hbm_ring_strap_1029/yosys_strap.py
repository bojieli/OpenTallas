#!/usr/bin/env python3
"""strap_qid ECO on the Yosys netlist 1_2_yosys.v (LEC view): drop the kept u_bin_qid face register instance, rename the top
port qid -> strap_qid, and drive the former qid__fq loads from the port. Fail-closed counts."""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
t = open(src).read()
m = re.search(r"\n  \\\$paramod\\ot_hbm_face_reg\\W=s32'0+10  u_bin_qid \(\n    \.clk\(clk\),\n    \.d\(qid\),\n    \.q\(\{ \\qid__fq\[1\] , \\qid__fq\[0\]  \}\)\n  \);", t)
if not m:
    i = t.find("u_bin_qid ("); raise SystemExit("u_bin_qid instance shape not found:\n" + t[i-120:i+200])
t = t[:m.start()] + t[m.end():]
n = {}
for a, b in [(r", qid\n", ", strap_qid\n"), (r"\n  input \[1:0\] qid;", "\n  input [1:0] strap_qid;"), (r"\n  wire \[1:0\] qid;", "\n  wire [1:0] strap_qid;"),
             (r"\n  wire \\qid__fq\[0\] ;", ""), (r"\n  wire \\qid__fq\[1\] ;", ""),
             (r"\\qid__fq\[0\] ", "strap_qid[0] "), (r"\\qid__fq\[1\] ", "strap_qid[1] ")]:
    t, k = re.subn(a, b.replace("\\", "\\\\"), t); n[a] = k
print(n)
assert all(v >= 1 for v in n.values()), n
assert "qid__fq" not in t and "u_bin_qid" not in t and not re.search(r"[^_\w]qid\b", t.replace("strap_qid", "")), "leftover qid"
open(dst, "w").write(t); print("YOSYS_STRAP_OK")
