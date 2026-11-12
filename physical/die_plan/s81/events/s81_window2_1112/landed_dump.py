"""WINDOW-2: same invocation as DIE-RECHECK-1 post_kit.sh, plus a dump of every landed pair whose clock damage exceeds the landing window."""
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
        for x, y, tag in pairs:
            A, B = taps[x], taps[y]
            node = D.pair_node(A, B)
            la, ea, lc, ec = D.arr4(A, B, node)
            cr = D.credit(rng, node, la, ea, lc, ec)
            dmg = max(la - ec - cr, lc - ea - cr)
            if dmg > win:
                k = (str(tag), A.get("part"), B.get("part"), A.get("region"), B.get("region"))
                r = agg.setdefault(k, [0, 0.0, x, y])
                r[0] += 1
                if dmg > r[1]:
                    r[1], r[2], r[3] = dmg, x, y
        calls.append({"window": win, "n_pairs": len(pairs), "rows": [[*k, v[0], round(v[1], 2), v[2], v[3]] for k, v in agg.items()]})
    return orig(pairs, taps, rng, *a, **kw)
D.time_class = tc
sys.argv = ["die_sta_related.py", f"{W}/s81/proof_auto_{V}", "--plan", PLAN, "--out", f"{OUT}/sta", "--corner", "TT", "--corner", "FF", "--core-insertion", "declared"]
try:
    D.main()
except SystemExit:
    pass
json.dump(calls, open(f"{OUT}/landed_over_window.json", "w"))
print("DUMP calls", len(calls), [len(c["rows"]) for c in calls])
