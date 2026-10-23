#!/usr/bin/env python3
"""Path latencies (flop-stage counts) of the CB16 region c1r1 tops from plan.json priced_cycles, for bench_reg1.sh.

Token prices: land_r / land_w = one landed crossing (D4/K2 = the 'new_edges' of the crossing class, 3); ring(N) and
'stn xN' = N; stn, rlyK, x = 1; endpoints (n_a, n_b, t_out, n_y) = 0.  Prints Verilator -G flags; both tops must agree.
"""
import json, re, sys

def price(tok, cross):
    tok = re.sub(r"\(\d+ hops\)", "", tok).strip()
    if tok in ("land_r", "land_w"):
        return cross
    m = re.fullmatch(r"ring\((\d+)\)", tok) or re.fullmatch(r"stn x(\d+)", tok)
    if m:
        return int(m.group(1))
    if tok == "stn" or tok == "x" or re.fullmatch(r"rly\d+", tok):
        return 1
    if tok in ("n_a", "n_b", "t_out", "n_y"):
        return 0
    raise SystemExit(f"reg1_latency: unknown path token {tok!r}")

def lat(top):
    pc = {e["edge_class"]: e for e in top["priced_cycles"]}
    cross = int(pc["crossing (landed, any seam)"]["new_edges"].split()[0].lstrip("+"))
    def path(cls, upto=None):
        toks = [t.strip() for t in pc[cls]["new"].split("->")]
        if upto:
            toks = toks[: toks.index(upto) + 1]
        return sum(price(t, cross) for t in toks)
    return dict(L_BC=path("column run bc -> bco through c1r1"),
                L_TAP=path("column run bc -> bco through c1r1", "x"),
                L_NA=path("leg 2_0a (c1r0 -> n_a)"), L_NB=path("leg 2_0b_y (c0r1 -> n_b)"),
                L_TO=path("leg 1_1b_y (t_out -> c0r1)"), L_NY=path("leg 3_0a (n_y -> c2r1)"),
                L_LF=path("leg 4_0b feedthrough (c1r2 -> c1r0)"))

plan = json.load(open(sys.argv[1]))
a, b = lat(plan["qfd_c_b16_reg1"]), lat(plan["qfd_c_b16_reg1b"])
if a != b:
    raise SystemExit(f"reg1_latency: tops priced differently {a} vs {b}")
print(" ".join(f"-G{k}={v}" for k, v in a.items()))
