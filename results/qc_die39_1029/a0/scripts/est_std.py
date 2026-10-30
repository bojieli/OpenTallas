"""DIE-QC-39 A0: analytic + Monte-Carlo estimate of a STANDARD-STAGE A0 core clock tree (equal stage count to every
register; every non-leaf stage a standard stage: fanout 1-2 with a leg window, so one delay mu +- sigma), on the
measured V2 hold paths.

Inputs (FF):  {t}_tree_ff.tsv  (DIE-QC-38 clock dump of the kept V2 cts_prehold.odb: per node/sink input arrival, parent)
              {t}_hold_all_ff.tsv (DIE-QC-39 probe: every FF hold path with slack <= +250 ps, same session setup)
              stage_std.json  (measured standard-stage basis from stage_std.py)
Model per trial (all UNCHECKED predictions):
  * the V2 topology (who shares which ancestor) is kept; every V2 stage driven by a non-leaf node is replaced by an
    independent draw N(mu, sigma) per edge (mu/sigma = measured fo2/40-60 um window); leaf->sink stages keep the
    measured V2 value with sink legs capped at LEGCAP um (measured sink-wire fit, DIE-QC-38);
  * a common trunk of E extra standard stages (the generator's T) shifts every register and is chosen per tile from
    the expected (mean) arrivals to maximise the predicted worst slack (grid E);
  * macros: tap after k standard stages, k = round((plan reg insertion - macro FF max insertion)/mu) + j (grid j), pin
    arrival = sum of k independent draws + the measured V2 last leg (independent of the registers: conservative);
  * hold slack_new = slack_V2 + (launch_new - launch_V2) - (capture_new - capture_V2); ports keep the vclk frame.
Paths with V2 slack > +250 ps are not in the probe; their bound is reported (250 - max |delta| seen)."""
import csv, sys, json, random, statistics as st, collections, math
D, OUT = sys.argv[1], sys.argv[2]
NTRIAL = int(sys.argv[3]) if len(sys.argv) > 3 else 200
LEGCAP = 60.0
LEAFMODE = sys.argv[4] if len(sys.argv) > 4 else "std"
INS_FF_MAX = {"ot_qwen_tile_lsl_rawfault_m3": 210.59, "ot_qwen_tile_romleaf": 243.27, "ot_qwen_tile_node": 209.51}   # kit macros/*_ff.lib (DIE-QC-38)
SS = json.load(open(f"{D}/stage_std.json"))["ff"]
MU, SIG = SS["STD_fo2_leg40-60"]["mean"], SS["STD_fo2_leg40-60"]["sd"]
SIG = float(sys.argv[5]) if len(sys.argv) > 5 else SIG
GENDIR = sys.argv[6] if len(sys.argv) > 6 else "."
KMODE = sys.argv[7] if len(sys.argv) > 7 else "free"
# core_infra k = round(mid/stage) from the kit libs (lib_insertion: min of rise/fall .. max of rise/fall), stage FF 25.02 / TT 32.10:
# FF mid LSL 201.68 node 195.89 romleaf 223.56; TT mid 261.97 / 254.90 / 284.62 -> k 8 / 8 / 9 at both corners
KCI = {"ot_qwen_tile_lsl_rawfault_m3": 8, "ot_qwen_tile_node": 8, "ot_qwen_tile_romleaf": 9}
# macro reach (plan geometry): the path port -> gate -> corridor -> pin must be covered by (T-1-k) legs; legs over the
# window cost more per stage (measured FF fo1 bins: 70 um 26.19, 90 um 29.90, 110 um 39.67 ps; DIE-QC-39 stage_std.json)
CENSUS = sys.argv[8] if len(sys.argv) > 8 else None
PLANDIR = sys.argv[9] if len(sys.argv) > 9 else None
def stage_cost(leg):
    pts = [(70.0, 26.19), (90.0, 29.90), (110.0, 39.67)]
    if leg <= pts[0][0]: return MU if leg <= 60 else MU + (leg - 60) / 10 * (pts[0][1] - MU)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if leg <= x1: return y0 + (leg - x0) * (y1 - y0) / (x1 - x0)
    return pts[-1][1] + (leg - 110.0) * 0.49
EMIN, KMIN = -5, 3      # realisable depth: >= 16 register stages (6 root fo2 levels + gate + 8 domain levels + leaf); macro tap >= root+gate+1
ws = lambda leg: max(0.0, -1.28 + 0.2823 * leg)          # DIE-QC-38 measured FF sink-wire fit
res = dict(model=dict(macro_reach=bool(CENSUS), kmode=KMODE, leafmode=LEAFMODE, mu_ff=MU, sigma_ff=SIG, emin=EMIN, kmin=KMIN, legcap_um=LEGCAP, ntrial=NTRIAL, basis="stage_std.json ff STD_fo2_leg40-60 (CHECKED measured)"))
for t in ("nl", "nk"):
    T = {r["inst"]: r for r in csv.DictReader(open(f"{D}/{t}_tree_ff.tsv"), delimiter="\t")}
    ch = collections.defaultdict(list)
    for r in T.values(): ch[r["parent"]].append(r["inst"])
    isleafdrv = {p: all(T[c]["kind"] == "sink" for c in cs) for p, cs in ch.items() if p != "port:ck"}
    man = lambda a, b: abs(float(a["x"]) - float(b["x"])) + abs(float(a["y"]) - float(b["y"]))
    order = []                                             # BFS order
    q = list(ch["port:ck"])
    while q:
        n = q.pop(0); order.append(n); q.extend(ch.get(n, []))
    v2 = {n: float(T[n]["in_min_r"]) for n in order}
    macros = [n for n in order if T[n]["kind"] == "sink" and T[n]["master"].startswith("ot_")]
    regs = [n for n in order if T[n]["kind"] == "sink" and not T[n]["master"].startswith("ot_")]
    # fixed (measured) part of a reg: leaf input -> sink pin, with sink leg capped
    # leaf stage (leaf input -> register pin, measured).  LEAFMODE "keep": V2 value with the sink leg capped at LEGCAP;
    # "std": regs whose leaf spans > LEGCAP (or own leg > LEGCAP) are regrouped onto a standard (compact) leaf, so their
    # leaf stage is drawn from the measured distribution of compact leaves (span <= LEGCAP).
    lspan = {p: max(man(T[p], T[c]) for c in cs) for p, cs in ch.items() if p != "port:ck" and isleafdrv.get(p)}
    def lp_v2(n): return v2[n] - float(T[T[n]["parent"]]["in_min_r"])
    compact = [lp_v2(n) for n in regs if lspan.get(T[n]["parent"], 1e9) <= LEGCAP]
    outlier = {n for n in regs if lspan.get(T[n]["parent"], 1e9) > LEGCAP}
    # "gen:<n>": the generator's own equal-count leaves (split(), n sinks, per clock domain) on the V2 register xy,
    # leaf stage from the DIE-QC-38 measured FF fits: leaf cell 31.49 + 0.0035*Lsum - 0.28*nsink, sink wire
    # -1.28 + 0.2823*leg (real leg, no cap), + N(0, 4.5) residual (fit rms) -- stragglers keep their long legs.
    if LEAFMODE.startswith("gen:"):
        sys.path.insert(0, GENDIR); from gen_a0_tree21 import split, equal_counts, centroid
        size = int(LEAFMODE[4:])
        def dom(n):
            m = T[n]["parent"]
            while m != "port:ck":
                if T[m]["master"].startswith("ICG"): return m
                m = T[m]["parent"]
            return "root"
        doms = collections.defaultdict(list)
        for n in regs: doms[dom(n)].append((float(T[n]["x"]), float(T[n]["y"]), n))
        genlp = {}
        for g, pts in doms.items():
            for grp in split(pts, equal_counts(len(pts), math.ceil(len(pts) / size))):
                c = centroid(grp); legs = [abs(p[0] - c[0]) + abs(p[1] - c[1]) for p in grp]
                cell = 31.49 + 0.0035 * sum(legs) - 0.28 * len(grp)
                for p, L in zip(grp, legs): genlp[p[2]] = cell + max(0.0, -1.28 + 0.2823 * L)
    def leafpart(n, rng=None):
        if LEAFMODE.startswith("gen:"):
            return genlp[n] + (0.0 if rng is None else rng.gauss(0.0, 4.5))
        if LEAFMODE == "std" and n in outlier:
            return st.median(compact) if rng is None else rng.choice(compact)
        r = T[n]; p = T[r["parent"]]; leg = man(p, r)
        return lp_v2(n) - (ws(leg) - ws(min(leg, LEGCAP)))
    P = list(csv.DictReader(open(f"{D}/{t}_hold_all_ff.tsv"), delimiter="\t"))
    inst = lambda pin: pin.rsplit("/", 1)[0] if "/" in pin else None
    def sample(rng, mean_only=False):
        a = {}
        for n in order:
            r = T[n]; p = r["parent"]
            if p == "port:ck": a[n] = v2[n]; continue
            if r["kind"] == "sink" and not r["master"].startswith("ot_"):
                a[n] = a[p] + leafpart(n, None if mean_only else rng)
            elif r["kind"] == "sink":
                a[n] = None                                 # macros placed below
            else:
                a[n] = a[p] + (MU if mean_only else rng.gauss(MU, SIG))
        return a
    mean = sample(None, True)
    reg_mean_med = st.median(mean[n] for n in regs)
    lastleg = {m: v2[m] - float(T[T[m]["parent"]]["in_min_r"]) for m in macros}
    mpath = {}
    if CENSUS:
        import gzip
        port, gxy = None, {}
        for line in gzip.open(f"{CENSUS}/{t}.tsv.gz", "rt"):
            f = line.rstrip("\n").split("\t")
            if line.startswith("port "): port = list(map(float, line.split()[2:4]))
            elif f[0] == "S" and f[2] == "0" and f[5].startswith("ICG"): gxy[f[3]] = [float(f[6]), float(f[7])]
        corr = {e["gate"]: e["corridor_um"] for e in json.load(open(f"{PLANDIR}/{t}_v2_report.json"))["early"]}
        for m in macros:
            g = T[m]["parent"]
            while not T[g]["master"].startswith("ICG"): g = T[g]["parent"]
            mpath[m] = abs(port[0] - gxy[g][0]) + abs(port[1] - gxy[g][1]) + corr[g]
    def macro_pin(rng, m, E, j, mean_only=False):
        if KMODE == "ci":     # core_infra _early_tap: view stages kv = round(mid/stage) at TT and FF (measured std stage)
            k = max(KMIN, (21 + E) - 1 - KCI[T[m]["master"]])
        else:
            k = max(KMIN, round((reg_mean_med + E * MU - INS_FF_MAX[T[m]["master"]]) / MU) + j)
        mu_k = MU
        if m in mpath:      # k legs (R..leaf) cover the planned path; over-window legs cost more
            mu_k = stage_cost(mpath[m] / max(k, 1))
        s = k * mu_k if mean_only else sum(rng.gauss(mu_k, SIG) for _ in range(k))
        return v2["mp_a0_R1"] + s + lastleg[m], k
    def slacks(a, E, j, rng, mean_only=False):
        new = {}
        for m in macros: new[m] = macro_pin(rng, m, E, j, mean_only)[0]
        def arr(i):
            if i is None or i not in T: return None
            if i in new: return new[i]
            return a[i] + E * MU
        out = collections.defaultdict(list)
        for p in P:
            s0 = float(p["slack_ps"]); si, ei = inst(p["startpoint"]), inst(p["endpoint"])
            ln, cn = arr(si), arr(ei)
            d = 0.0
            if ln is not None: d += ln - v2[si]
            if cn is not None: d -= cn - v2[ei]
            k = ("port->*" if si is None else "reg->outport" if ei is None else
                 "->macro" if ei in T and T[ei]["master"].startswith("ot_") else "macro->" if si in T and T[si]["master"].startswith("ot_")
                 else "unclocked" if (si not in T or ei not in T) else "reg->async" if p["endpoint"].endswith("SETN") else "reg->reg")
            out[k].append((s0 + d, d))
        return out
    # pick E (extra common stages, may be negative = fewer stages) and j (macro tap offset) on the mean model
    best = None; grid = []
    for E in range(EMIN, 11):
        for j in ((0,) if KMODE == "ci" else (-4, -3, -2, -1, 0, 1, 2)):
            o = slacks(mean, E, j, None, True)
            w = min(x[0] for v in o.values() for x in v)
            w2 = min(x[0] for k_, v in o.items() if k_ != "port->*" for x in v)      # tie-break: worst outside the IO-frame class
            grid.append((E, j, round(w, 2), round(w2, 2)))
            if best is None or (round(w, 1), round(w2, 1)) > (round(best[2], 1), round(best[3], 1)): best = (E, j, w, w2)
    E, j = best[0], best[1]
    o = slacks(mean, E, j, None, True)
    worst_mean = sorted(((x[0], k) for k, v in o.items() for x in v))[:3]
    rng = random.Random(39)
    trials = []
    for _ in range(NTRIAL):
        a = sample(rng)
        o = slacks(a, E, j, rng)
        trials.append({k: (min(x[0] for x in v), sum(x[0] < 0 for x in v), max(abs(x[1]) for x in v)) for k, v in o.items()})
    cls = sorted(trials[0])
    q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]
    by = {k: dict(worst_p50=round(q([tr[k][0] for tr in trials], 0.5), 1), worst_p05=round(q([tr[k][0] for tr in trials], 0.05), 1),
                  fails_p50=q([tr[k][1] for tr in trials], 0.5), n_paths=sum(1 for p in P)) for k in cls}
    ws_tr = [min(tr[k][0] for k in cls) for tr in trials]
    nf_tr = [sum(tr[k][1] for k in cls) for tr in trials]
    maxd = max(tr[k][2] for tr in trials for k in cls)
    regs_new = [mean[n] + E * MU for n in regs]
    o_v2 = collections.Counter()
    res[t] = dict(E_extra_stages=E, macro_tap_j=j, reg_stage_count_v2=21, reg_stage_count_new=21 + E,
                  reg_insertion_mean_model=dict(median=round(st.median(regs_new), 1), min=round(min(regs_new), 1), max=round(max(regs_new), 1)),
                  macro_leg_um={m.replace("u_g.u_tile.u_tile.u_logic.", ""): round(mpath[m] / max(macro_pin(None, m, E, j, True)[1], 1), 1) for m in macros} if mpath else None,
                  macro_k={T[m]["master"][13:]: sorted(set(macro_pin(None, mm, E, j, True)[1] for mm in macros if T[mm]["master"] == T[m]["master"])) for m in macros},
                  ws_v2=round(min(float(p["slack_ps"]) for p in P), 2), n_paths=len(P),
                  ws_pred_p50=round(q(ws_tr, 0.5), 1), ws_pred_p05=round(q(ws_tr, 0.05), 1), ws_pred_min=round(min(ws_tr), 1), fail_paths_p50=q(nf_tr, 0.5),
                  by_class=by, n_outlier_leaf_regs=len(outlier), worst_mean_model=[(round(a, 1), b) for a, b in worst_mean], unprobed_bound_ps=round(250 - maxd, 1),
                  grid_mean_model=[g for g in grid if g[1] == j])
    print(t, json.dumps({k: v for k, v in res[t].items() if k != "grid_mean_model"}, indent=None))
json.dump(res, open(OUT, "w"), indent=1)
