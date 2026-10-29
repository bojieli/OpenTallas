"""DIE-QC-38 A0: classify the V2 FF hold failures (diag hold_fail.tsv of cts_prehold.odb) by clock-leaf relation."""
import csv, sys, collections, json
D = sys.argv[1]
out = {}
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    H = list(csv.DictReader(open(f"{D}/{t}_hold_fail.tsv"), delimiter="\t"))
    P = {r["endpoint"]: r for r in csv.DictReader(open(f"{D}/{t}_holdpairs_ff.tsv"), delimiter="\t")}
    anc = {}
    def path(n):
        if n not in anc:
            p = []; m = n
            while m != "port:ck": p.append(m); m = T[m]["parent"]
            anc[n] = p[::-1]
        return anc[n]
    def man(a, b): return abs(float(T[a]["x"]) - float(T[b]["x"])) + abs(float(T[a]["y"]) - float(T[b]["y"]))
    cls = collections.defaultdict(list); detail = []
    for h in H:
        sl = float(h["slack_ps"]); sp, ep = h["startpoint"], h["endpoint"]
        si = sp.rsplit("/", 1)[0] if "/" in sp else None
        ei = ep.rsplit("/", 1)[0] if "/" in ep else None
        if si is None: k = "port->*"
        elif ei is None: k = "reg->outport" if not T.get(si, {}).get("master", "").startswith("ot_") else "macro->outport"
        else:
            sm = T.get(si, {}).get("master", "?"); em = T.get(ei, {}).get("master", "?")
            if ei not in T: k = "end_unclocked"
            elif si not in T: k = "start_unclocked(" + sm + ")"
            elif em.startswith("ot_qwen"): k = "reg->macro"
            elif sm.startswith("ot_qwen"): k = "macro->reg"
            elif ep.endswith(("RESETN", "SETN")): k = "reg->async"
            else:
                pr = P.get(ep, {}); zl = pr.get("drv_inst") == si
                ls, le = T[si]["parent"], T[ei]["parent"]
                if ls == le: rel = "same_leaf"
                else:
                    a, b = path(ls), path(le); i = 0
                    while i < min(len(a), len(b)) and a[i] == b[i]: i += 1
                    rel = f"diff_leaf"
                    dist = man(ls, le)
                k = ("zero_logic" if zl else "logic") + ":" + rel
                if rel != "same_leaf":
                    detail.append((sl, k, round(dist, 1), len(a) - i, float(T[le]["out_min_r"]) - float(T[ls]["out_min_r"]), round(man(si, ei), 1)))
        cls[k].append(sl)
    res = {k: dict(n=len(v), worst=round(min(v), 2), n_lt_m100=sum(x < -100 for x in v)) for k, v in sorted(cls.items(), key=lambda kv: min(kv[1]))}
    # diff-leaf zero-logic: leaf distance / divergence depth / capture-launch leaf skew
    zl = [d for d in detail if d[0] < -100]
    import statistics as st
    for kk in ("zero_logic:diff_leaf", "logic:diff_leaf"):
        z = [d for d in detail if d[1] == kk]
        if z:
            res[kk].update(leaf_dist_um_median=st.median(d[2] for d in z), leaf_dist_um_max=max(d[2] for d in z),
                           diverge_levels_median=st.median(d[3] for d in z), cap_minus_launch_leaf_ps_median=round(st.median(d[4] for d in z), 1),
                           reg_dist_um_median=st.median(d[5] for d in z),
                           n_regdist_le60=sum(d[5] <= 60 for d in z), n_worse_m100_regdist_le60=sum(d[5] <= 60 and d[0] < -100 for d in z))
    out[t] = res
    print("==", t, len(H))
    for k, v in res.items(): print("  ", k, v)
json.dump(out, open(f"{D}/hold_class.json", "w"), indent=1)
