"""DIE-QC-39 A0: estimate on the ACTUAL generated plan tree (slice JSON), not on the V2 topology.
Per planned edge parent->child the stage delay is drawn from the measured V2 bin of the parent's fanout and max leg
(stage_std.json: buf_fo{1..4}_lmax{bin}, icg_fo1_lmax{bin}; mean, sd); register leaf stage = DIE-QC-38 FF fits
(leaf cell 31.49 + 0.0035*Lsum - 0.28*n, sink wire -1.28 + 0.2823*leg) + N(0, 4.5); macro leaf -> pin = V2 measured.
Calibration: the same model on the V2 slice vs the measured V2 FF arrivals (bias / rms reported, CHECKED as a model
check).  Hold: slack_new = slack_V2 + (launch_new - launch_V2) - (capture_new - capture_V2) on every probed path.
    python3 -I est_plan.py DATA PLANDIR OUT NTRIAL tile:v2slice:newslice ..."""
import json, sys, csv, random, statistics as st, collections, math
D, PD, OUT, NTR = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
SS = json.load(open(f"{D}/stage_std.json"))["ff"]
BINS = ((0, 20), (20, 40), (40, 60), (60, 80), (80, 100), (100, 400))
TC = {"tt": -172.53, "nl_fails": 2370, "nk": -571.84, "nk_fails": 3082}
def binstat(kind, fo, lmax):
    fo = min(max(fo, 1), 4) if kind == "buf" else 1
    for lo, hi in BINS:
        if lo <= lmax < hi or hi == 400:
            k = f"{kind}_fo{fo}_lmax{lo}-{hi}"
            if k in SS: return SS[k]["mean"], SS[k]["sd"]
            break
    # nearest available bin of this kind/fanout
    c = [(abs((int(k.split("lmax")[1].split("-")[0]) + 10) - lmax), v) for k, v in SS.items() if k.startswith(f"{kind}_fo{fo}_")]
    v = min(c, key=lambda x: x[0])[1]; return v["mean"], v["sd"]
man = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
nm = lambda s: s.replace("\\", "").rsplit("/", 1)[0]
def model(sl, rng, lastleg):
    ct = sl["core_tree"]
    xy = {n["name"]: n["xy_um"] for n in ct["nodes"]}; xy.update({g["inst"]: g["xy_um"] for g in ct["gates"]})
    mst = {n["name"]: n["master"] for n in ct["nodes"]}; mst.update({g["inst"]: g["master"] for g in ct["gates"]})
    par = {n["name"]: n["parent"] for n in ct["nodes"]}; par.update({g["inst"]: g["parent"] for g in ct["gates"]})
    kids = collections.defaultdict(list)
    for n, p in par.items(): kids[p].append(n)
    leafs = {l["node"]: l for l in ct["leaves"]}
    sxy = model.sxy
    arr = {}
    order = list(kids["port:ck"]); i = 0
    for n in order: arr[n] = 0.15
    while i < len(order):
        p = order[i]; i += 1
        ks = kids.get(p, [])
        if not ks: continue
        lmax = max(man(xy[p], xy[k]) for k in ks)
        kind = "icg" if mst[p].startswith("ICG") else "buf"
        mu, sd = binstat(kind, len(ks), lmax)
        for k in ks:
            arr[k] = arr[p] + (mu if rng is None else rng.gauss(mu, sd)); order.append(k)
    out = {}
    for ln, lf in leafs.items():
        if lf.get("load_class") == "macro":
            for s in lf["sinks"]: out[nm(s)] = arr[ln] + lastleg[nm(s)]
            continue
        if lf.get("load_class") == "gated_domain": continue
        legs = [man(xy[ln], sxy[nm(s)]) for s in lf["sinks"]]
        cell = 31.49 + 0.0035 * sum(legs) - 0.28 * len(legs)
        for s, L in zip(lf["sinks"], legs):
            out[nm(s)] = arr[ln] + cell + max(0.0, -1.28 + 0.2823 * L) + (0 if rng is None else rng.gauss(0, 4.5))
    for g in ct["gates"]: out[g["inst"]] = arr[g["inst"]]          # ICG clock pin (enable-hold endpoints)
    return out
res = {}
for spec in sys.argv[5:]:
    t, v2s, news = spec.split(":")
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    v2 = {n: float(r["in_min_r"]) for n, r in T.items()}
    model.sxy = {n: (float(r["x"]), float(r["y"])) for n, r in T.items() if r["kind"] == "sink"}
    lastleg = {n: v2[n] - float(T[r["parent"]]["in_min_r"]) for n, r in T.items() if r["kind"] == "sink" and r["master"].startswith("ot_")}
    SV2, SNEW = json.load(open(f"{PD}/{v2s}")), json.load(open(f"{PD}/{news}"))
    mv2 = model(SV2, None, lastleg)
    regs = [n for n in mv2 if n in T and T[n]["kind"] == "sink" and not T[n]["master"].startswith("ot_")]
    diff = [mv2[n] - v2[n] for n in regs]
    mac = [n for n in mv2 if n in T and T[n]["master"].startswith("ot_")]
    cal = dict(n_regs=len(regs), bias_med=round(st.median(diff), 1), rms=round(math.sqrt(st.mean(d * d for d in diff)), 1),
               v2_meas_spread=round(max(v2[n] for n in regs) - min(v2[n] for n in regs), 1),
               model_spread=round(max(mv2[n] for n in regs) - min(mv2[n] for n in regs), 1),
               macro_bias=round(st.median(mv2[n] - v2[n] for n in mac), 1) if mac else None)
    BIAS = st.median(diff)      # uniform model offset measured on V2 (removed from the new tree; skew unaffected)
    P = list(csv.DictReader(open(f"{D}/{t}_hold_all_ff.tsv"), delimiter="\t"))
    inst = lambda pin: pin.rsplit("/", 1)[0] if "/" in pin else None
    def slacks(a):
        out = collections.defaultdict(list)
        for p in P:
            s0 = float(p["slack_ps"]); si, ei = inst(p["startpoint"]), inst(p["endpoint"]); d = 0.0
            if si in a and si in v2: d += a[si] - BIAS - v2[si]
            if ei in a and ei in v2: d -= a[ei] - BIAS - v2[ei]
            k = ("port->*" if si is None else "reg->outport" if ei is None else
                 "->macro" if ei in T and T[ei]["master"].startswith("ot_") else "macro->" if si in T and T[si]["master"].startswith("ot_")
                 else "unclocked" if (si not in a or ei not in a) else "reg->async" if p["endpoint"].endswith("SETN") else "reg->reg")
            out[k].append((s0 + d, d))
        return out
    rng = random.Random(39); tr = []
    for _ in range(NTR):
        o = slacks(model(SNEW, rng, lastleg))
        tr.append({k: (min(x[0] for x in v), sum(x[0] < 0 for x in v), max(abs(x[1]) for x in v)) for k, v in o.items()})
    om = slacks(model(SNEW, None, lastleg))
    worst = sorted(((x[0], k, i) for k, v in om.items() for i, x in enumerate(v)))[:1]
    wl = [(round(sl_, 1), k) for sl_, k, _ in sorted(((x[0], k, 0) for k, v in om.items() for x in v))[:5]]
    q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
    cls = sorted(tr[0]); ws = [min(x[k][0] for k in cls) for x in tr]; nf = [sum(x[k][1] for k in cls) for x in tr]
    mn = model(SNEW, None, lastleg); rn = [mn[n] - st.median(diff) for n in regs if n in mn]
    res[t] = dict(model_bias_removed_ps=round(BIAS, 1), worst_mean_model=wl, v2_slice=v2s, new_slice=news, calibration_on_v2=cal, ws_v2=round(min(float(p["slack_ps"]) for p in P), 2),
                  reg_insertion_model=dict(min=round(min(rn), 1), median=round(st.median(rn), 1), max=round(max(rn), 1)),
                  ws_mean_model=round(min(x[0] for v in om.values() for x in v), 1),
                  ws_pred_p50=round(q(ws, .5), 1), ws_pred_p05=round(q(ws, .05), 1), ws_pred_min=round(min(ws), 1), fails_p50=q(nf, .5),
                  by_class={k: dict(worst_p50=round(q([x[k][0] for x in tr], .5), 1), worst_p05=round(q([x[k][0] for x in tr], .05), 1),
                                    fails_p50=q([x[k][1] for x in tr], .5)) for k in cls},
                  unprobed_bound_ps=round(250 - max(x[k][2] for x in tr for k in cls), 1))
    print(t, json.dumps(res[t]))
json.dump(res, open(OUT, "w"), indent=1)
