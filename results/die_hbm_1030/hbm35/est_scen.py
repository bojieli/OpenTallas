#!/usr/bin/env python3
"""DIE-HBM-35 targeted row-order scenarios (same demand model as est_rows.py). usage: est_scen.py PLAN BIND_LATENCY BIND_REPORT"""
import sys, json, importlib.util
spec = importlib.util.spec_from_file_location("er", sys.argv[0].replace("est_scen.py", "est_rows.py"))
sys.argv = [sys.argv[0], sys.argv[1], sys.argv[2], sys.argv[3], "/dev/null", ""]
import io, contextlib
with contextlib.redirect_stdout(io.StringIO()):
    er = importlib.util.module_from_spec(spec); spec.loader.exec_module(er)
S, N = er.SROW, er.NROW
def mv(order, name, after):
    o = [x for x in order if x != name]; o.insert(o.index(after) + 1 if after else 0, name); return o
sc = {
 "base": (S, N),
 "N: b113 to west end (after b112)": (S, mv(N, "NE_b113", "NE_b112")),
 "N: b113 first, b112 second": (S, ["NE_b113"] + [x for x in N if x != "NE_b113"]),
 "S: b102,b103 after b100": (mv(mv(S, "NE_b102", "NE_b100"), "NE_b103", "NE_b102"), N),
 "S: b111 after b110": (mv(S, "NE_b111", "NE_b110"), N),
 "S: b102,b103 after b100 + b111 after b110": (mv(mv(mv(S, "NE_b102", "NE_b100"), "NE_b103", "NE_b102"), "NE_b111", "NE_b103"), N),
 "ALL: S b100,b102,b103,b110,b111 west + N b113 after b112": (mv(mv(mv(S, "NE_b102", "NE_b100"), "NE_b103", "NE_b102"), "NE_b111", "NE_b110") if False else ["NE_b101","NE_b100","NE_b102","NE_b103","NE_b110","NE_b111","NE_su31","NE_su30","NE_spu1","NE_su21","NE_su20"], mv(N, "NE_b113", "NE_b112")),
}
for k, (s, n) in sc.items():
    g = {a: list(b) for a, b in er.geo.items()}
    er.place(g, S, s); er.place(g, N, n)
    hubface = {m: round(max(0, min(g[m][0] + g[m][2], 23258.88) - max(g[m][0], 15042.24)), 1) for m in s + n}
    print(f"{k:60s} cost {er.cost(g)/1e9:6.3f}G unpl {er.unpl_cost(g)/1e6:7.1f}M bit-um column {er.column_bits(g):6d}  "
          f"under-hub: " + ",".join(f"{m[3:]}" for m in s + n if hubface[m] > 0))
