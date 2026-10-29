"""DIE-QC-38 A0: analytic estimate of variants A (same_leaf_pairs) and B (leaf span <= 60 um) on the measured V2
FF hold failures (diag hold_fail.tsv + this lane's FF clock dump). Per failing pair:
  A: zero-logic pair on different leaves -> capture moved to the launch leaf: slack += (launch_ck - capture_ck)
     (same leaf => clock arrival difference = the two sink-leg wires only, taken as 0 here; optimistic for A)
  B: every register sink leg capped at 60 um: sink wire delay recomputed with the measured FF fit
     wire_sink = -1.28 + 0.2823*leg (ps, rms 2.9); leaves keep their arrival (optimistic for B: smaller leaves
     need more leaves/levels).  Other classes unchanged."""
import csv, sys, json, collections
D = sys.argv[1]
ws = lambda leg: max(0.0, -1.28 + 0.2823 * leg)
out = {}
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    P = {r["endpoint"]: r for r in csv.DictReader(open(f"{D}/{t}_holdpairs_ff.tsv"), delimiter="\t")}
    H = list(csv.DictReader(open(f"{D}/{t}_hold_fail.tsv"), delimiter="\t"))
    man = lambda a, b: abs(float(a["x"]) - float(b["x"])) + abs(float(a["y"]) - float(b["y"]))
    def ck(i): return float(T[i]["in_min_r"])
    def legcut(i):
        r = T[i]; leg = man(T[r["parent"]], r)
        return ws(leg) - ws(min(leg, 60.0))      # arrival reduction when capped
    res = {}
    for v in ("base", "A", "B"):
        cls = collections.defaultdict(list)
        for h in H:
            sl = float(h["slack_ps"]); sp, ep = h["startpoint"], h["endpoint"]
            si = sp.rsplit("/", 1)[0] if "/" in sp else None; ei = ep.rsplit("/", 1)[0] if "/" in ep else None
            reg = lambda i: i in T and not T[i]["master"].startswith("ot_")
            k = ("port->*" if si is None else "reg->outport" if ei is None else "reg->macro" if ei in T and T[ei]["master"].startswith("ot_")
                 else "reg->async" if ep.endswith("SETN") else "zero_logic" if P.get(ep, {}).get("drv_inst") == si else "logic")
            if v == "A" and k == "zero_logic" and reg(si) and reg(ei) and T[si]["parent"] != T[ei]["parent"]:
                sl += ck(ei) - ck(si)
            if v == "B":
                if si and reg(si): sl -= legcut(si)          # launch earlier -> hold worse
                if ei and reg(ei): sl += legcut(ei)          # capture earlier -> hold better
            cls[k].append(sl)
        allv = [x for vv in cls.values() for x in vv]
        res[v] = dict(ws=round(min(allv), 2), fails=sum(x < 0 for x in allv),
                      by_class={k: dict(n_fail=sum(x < 0 for x in vv), worst=round(min(vv), 2)) for k, vv in cls.items()})
    out[t] = res
    for v, r in res.items(): print(t, v, r["ws"], r["fails"], {k: (x["n_fail"], x["worst"]) for k, x in r["by_class"].items()})
json.dump(out, open(f"{D}/estimate_ab.json", "w"), indent=1)
