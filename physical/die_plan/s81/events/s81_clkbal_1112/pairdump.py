"""S81-CLKBAL-1: dump per-partition-pair landed damage components (P=la-ec-cr, Q=lc-ea-cr) and per-tap over-window pairs
so the insertion-balance offsets can be solved offline.  Same invocation as WINDOW-2 landed_dump_w2.py (die_sta_related)."""
import sys, json
V = "db1da17a93ab"
W = "/srv/opentallas-scratch2/claude/die-recheck-1"
TOOLS = f"{W}/s81/auto/{V}/repo/tools/die_plan"
PLAN = f"{W}/s81/auto/{V}/repo/physical/die_plan/s81/events/s81_ready11r_1112/plan_ready11r_db1da17a93ab.json"
OUT = sys.argv[1]
sys.path.insert(0, TOOLS)
import die_sta_related as D
orig = D.time_class
calls = []
def tc(pairs, taps, rng, *a, **kw):
    if kw.get("landed") and kw.get("window") is not None:
        win = float(kw["window"])
        agg = {}
        over = []
        for x, y, tag in pairs:
            A, B = taps[x], taps[y]
            node = D.pair_node(A, B)
            la, ea, lc, ec = D.arr4(A, B, node)
            cr = D.credit(rng, node, la, ea, lc, ec)
            P = la - ec - cr
            Q = lc - ea - cr
            k = (A.get("part"), B.get("part"))
            r = agg.get(k)
            if r is None:
                agg[k] = [P, Q, 1, str(tag)]
            else:
                if P > r[0]: r[0] = P
                if Q > r[1]: r[1] = Q
                r[2] += 1
            if max(P, Q) > win:
                over.append([x, y, round(P, 2), round(Q, 2), A.get("part"), B.get("part"), str(tag)])
        calls.append({"window": win, "n_pairs": len(pairs), "agg": [[k[0], k[1], round(v[0], 2), round(v[1], 2), v[2], v[3]] for k, v in agg.items()], "over": over})
    return orig(pairs, taps, rng, *a, **kw)
D.time_class = tc
sys.argv = ["die_sta_related.py", f"{W}/s81/proof_auto_{V}", "--plan", PLAN, "--out", f"{OUT}/sta", "--corner", "TT", "--corner", "FF", "--core-insertion", "declared"]
try:
    D.main()
except SystemExit:
    pass
json.dump(calls, open(f"{OUT}/pairdump.json", "w"))
print("DUMP calls", len(calls), [(c["window"], len(c["agg"]), len(c["over"])) for c in calls])
