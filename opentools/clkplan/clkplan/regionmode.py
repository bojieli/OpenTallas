"""Region-mode clock predictor (METHODOLOGY 12.13 LOCALITY FIRST: regions from connectivity, clock follows data).

Input (shared schema opentools.plan/1):
  regions[]  {name, rect, partition?, clock?{root_xy?, local_insertion_ps{TT,FF}?}}
  feeds[]    {name?, src, dst, len_um, kind 'forward'|'spine', tap 'root'|'leaf', stages?}  src = a region or 'root' (the die
             clock entry); every region has at most one incoming feed, so feeds form a tree (the feed graph).
             'forward' = neighbour-forwarded region clock; 'spine' = a tap off a shared spine running along the links.
  sinks / macro clock pins (with their own insertion_ps), crossings[] (a, b, kind landed|sync, budget_ps?).
Prediction, analytic, no placement tool:
  region local insertion  = repeated wire (model.wire_ps) over the region's longest root->sink Manhattan path
                            (a balanced local tree delivers every sink at the longest path), or the declared
                            regions[].clock.local_insertion_ps;
  region root arrival     = sum over the feed path from 'root' of model.wire_ps(len_um) (+ declared stages), plus the
                            parent's local insertion for a feed with tap 'leaf' (fed from a leaf of the parent tree, the
                            tools/die_plan/locality.py 'fwd' form: T_root(c) = T_root(p) + I_p + v |t - centre(c)|);
  latency(sink)           = root arrival + local insertion + the sink's own insertion (macro signed view);
  crossing a -> b         : common point = the deepest region on both feed paths (or the region itself if
                            a, b share a region: the plan-level bound then is a split at the region root);
                            unshared(a) = latency(a) - arrival(common point) - own insertion(a)  (die/region part);
                            OCV + droop with the SAME math as clkplan.ocv (= main tools/die_plan/clk_aocv.py and
                            tools/s81_head/landed_phase_ocv.py): derated |d| and margin = budget - derated |d|.
  The plan FAILS a landed crossing below clock.min_crossing_margin_ps (default 100 ps).
  --crossing-mode count_aligned (or clock.crossing_mode / crossings[].mode): the margin is the count-aligned ring
  margin instead (ocv.count_aligned_margin: K from the derated lag, L inside [0.5T+ap, (DEPTH-0.5)T-ap], DEPTH 4/8,
  one K for all corners); --crossing-mode ring_phase = the superseded one-period setup+hold window (kept for
  phase-placed samplers only).
  Arrivals are SPICE-SCALED by default (model.spice_cal, x1.0485 TT / x1.0552 FF on STA-basis delays); --no-spice-scale.
"""
import math

from . import ocv

CROSSING_MODES = ("phase", "count_aligned", "ring_phase")


def _centre(r):
    return ((r[0] + r[2]) / 2.0, (r[1] + r[3]) / 2.0)


def feed_tree(P):
    """-> parent{region: (src, feed)}; raises on a region with two feeds or a cycle."""
    par = {}
    for f in P.get("feeds", []):
        if f["dst"] in par:
            raise ValueError(f"region {f['dst']} has two incoming feeds")
        par[f["dst"]] = (f["src"], f)
    for r in par:
        seen, x = set(), r
        while x in par:
            if x in seen:
                raise ValueError(f"feed cycle through {x}")
            seen.add(x)
            x = par[x][0]
    return par


def path_to_root(par, reg):
    out = [reg]
    while out[-1] in par:
        out.append(par[out[-1]][0])
    return out          # reg ... top (normally 'root')


def predict(P, model, sinks, corners=("TT", "FF")):
    """sinks = common.plan.clock_sinks(P).  -> dict(regions{name: {...}}, sinks{name: {...}})"""
    regs = {r["name"]: r for r in P["regions"]}
    par = feed_tree(P)
    by_reg = {}
    for s in sinks:
        by_reg.setdefault(s["region"], []).append(s)
    R = {}
    for name, r in regs.items():
        ck = r.get("clock") or {}
        root = tuple(ck.get("root_xy") or _centre(r["rect"]))
        ss = by_reg.get(name, [])
        L = max((abs(s["xy"][0] - root[0]) + abs(s["xy"][1] - root[1]) for s in ss), default=0.0)
        decl = ck.get("local_insertion_ps") or {}
        # spice-scaled arrivals: a declared (STA-basis) local insertion and the model's own delays (if STA-basis)
        loc = {c: (float(decl[c]) * model.arrival_scale(c, "sta") if c in decl
                   else model.wire_ps(L, c) * model.arrival_scale(c, "model")) for c in corners}
        nst = int(ck.get("local_stages") or max(1, math.ceil(L / model["rep_um"] - 1e-9)))
        R[name] = dict(root_xy=root, local_path_um=round(L, 1), local_insertion_ps={c: round(v, 1) for c, v in loc.items()}, local_stages=nst)
    arr_cache = {}

    def root_arr(name, c):
        k = (name, c)
        if k in arr_cache:
            return arr_cache[k]
        if name not in par:
            v = (0.0, 0)
        else:
            src, f = par[name]
            a, n = root_arr(src, c) if src in regs else (0.0, 0)
            fs = int(f.get("stages") or max(1, math.ceil(f["len_um"] / model["rep_um"] - 1e-9)))
            if src in regs and f.get("tap", "root") == "leaf":     # fed from a LEAF of the parent's region tree
                a += R[src]["local_insertion_ps"][c]
                n += R[src]["local_stages"]
            v = (a + model.wire_ps(f["len_um"], c) * model.arrival_scale(c, "model"), n + fs)
        arr_cache[k] = v
        return v
    for name in R:
        R[name]["root_arrival_ps"] = {c: round(root_arr(name, c)[0], 1) for c in corners}
        R[name]["feed_stages"] = root_arr(name, corners[0])[1]
        R[name]["feed_path"] = path_to_root(par, name)
    S = {}
    for s in sinks:
        g = s["region"]
        if g not in R:
            S[s["name"]] = dict(error=f"sink {s['name']} is in no region")
            continue
        S[s["name"]] = dict(region=g, arr={c: root_arr(g, c)[0] + R[g]["local_insertion_ps"][c] for c in corners},
                            ins={c: float(s["insertion_ps"].get(c, 0.0)) * model.arrival_scale(c, "sta")
                                 for c in corners}, xy=s["xy"],
                            stages=R[g]["feed_stages"] + R[g]["local_stages"])
        S[s["name"]]["latency"] = {c: S[s["name"]]["arr"][c] + S[s["name"]]["ins"][c] for c in corners}
    return dict(regions=R, sinks=S, par=par, spice_cal={c: model.arrival_scale(c, "sta") for c in corners})


def crossings(P, model, pred, corners=("TT", "FF"), droop="regions", crossing_mode=None):
    """crossing_mode (CROSSING_MODES; crossings[].mode overrides per crossing):
      'phase'         today's one-period landing ring: margin = budget (P/2) - derated |d|;
      'count_aligned' the count-aligned ring: K from the derated lag, window [0.5T+ap, (DEPTH-0.5)T-ap], DEPTH 4/8
                      (ocv.count_aligned_margin; clock.count_aligned {aperture_ps (default T/8), depths [4, 8],
                      wander_frac 0.05}; crossings[].origin_cycles [X, Y] = start-tree whole-cycle ambiguity);
      'ring_phase'    the SUPERSEDED one-period setup+hold window with a design-time count (ocv.ring_phase_margin;
                      clock.ring_phase {half_cycle, aperture_ps per corner (default flop setup + hold)})."""
    Tb = model.T
    mode0 = crossing_mode or P["clock"].get("crossing_mode") or "phase"
    cfg_ca = dict(P["clock"].get("count_aligned") or {})
    cfg_rp = dict(P["clock"].get("ring_phase") or {})
    ap_rp = dict(model.m.get("capture_aperture_ps") or {})
    ap_rp.update(cfg_rp.get("aperture_ps") or {})
    R, S, par = pred["regions"], pred["sinks"], pred["par"]
    per = P["clock"].get("period_ps") or 1000.0
    mm = P["clock"].get("min_crossing_margin_ps", 100.0)
    rows = []
    for x in P["crossings"]:
        a, b = S.get(x["a"]), S.get(x["b"])
        if a is None or b is None or "error" in a or "error" in b:
            rows.append(dict(name=x.get("name"), a=x["a"], b=x["b"], error="sink not predicted"))
            continue
        pa, pb = path_to_root(par, a["region"]), path_to_root(par, b["region"])
        common = next((g for g in pa if g in pb), None)
        same = (droop != "always") and a["region"] == b["region"]
        cxy = R[common]["root_xy"] if common in R else tuple(P["clock"].get("entry") or a["xy"])
        pts = [a["xy"], b["xy"], cxy]
        dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        budget = float(x.get("budget_ps") or per / 2.0)
        r = dict(name=x.get("name"), a=x["a"], b=x["b"], kind=x.get("kind", "landed"), bits=x.get("bits"),
                 region_a=a["region"], region_b=b["region"], common=common, dist_um=round(dist, 1),
                 same_region=same, budget_ps=budget)
        worst = None
        trip = {}
        for c in corners:
            base = R[common]["root_arrival_ps"][c] if common in R else 0.0
            ua, ub = a["arr"][c] - base, b["arr"][c] - base
            na = a["stages"] - (R[common]["feed_stages"] if common in R else 0)
            nb = b["stages"] - (R[common]["feed_stages"] if common in R else 0)
            bra = ocv.branch(Tb, c, ua, na, a["ins"][c])
            brb = ocv.branch(Tb, c, ub, nb, b["ins"][c])
            d = b["latency"][c] - a["latency"][c]
            p_up, p_dn, der, mg = ocv.landed_margin(Tb, c, d, bra, brb, dist, same, budget)
            r[c] = dict(unshared_a_ps=round(ua, 1), unshared_b_ps=round(ub, 1), d_ps=round(d, 1), p_up_ps=round(p_up, 1),
                        p_dn_ps=round(p_dn, 1), derated_abs_ps=round(der, 1), margin_ps=round(mg, 1))
            trip[c] = (d, p_up, p_dn)
            worst = mg if worst is None else min(worst, mg)
        mode = x.get("mode") or mode0
        if mode not in CROSSING_MODES:
            raise ValueError(f"crossing {x.get('name')}: unknown crossing mode {mode!r} (one of {CROSSING_MODES})")
        r["mode"] = mode
        if mode == "count_aligned":
            wf = float(cfg_ca.get("wander_frac", 0.05))
            w = wf * max(max(r[c]["unshared_a_ps"], r[c]["unshared_b_ps"]) for c in corners)
            ca = ocv.count_aligned_margin(trip, per, cfg_ca.get("aperture_ps"), depths=tuple(cfg_ca.get("depths", ocv.CA_DEPTHS)),
                                          origin_cycles=tuple(x.get("origin_cycles") or cfg_ca.get("origin_cycles") or (0, 0)),
                                          wander_ps=w)
            r["count_aligned"] = dict(K=ca["K"], depth=ca["depth"], latency_cycles=ca["latency_cycles"],
                                      aperture_ps=round(ca["aperture_ps"], 2), wander_ps=round(w, 1),
                                      origin_cycles=list(ca["origin_cycles"]), L_lo_ps=round(ca["L_lo_ps"], 1),
                                      L_hi_ps=round(ca["L_hi_ps"], 1), margin_lo_ps=round(ca["margin_lo_ps"], 1),
                                      margin_hi_ps=round(ca["margin_hi_ps"], 1))
            for c in corners:
                r[c]["phase_margin_ps"] = r[c]["margin_ps"]
                r[c]["margin_ps"] = round(ca["corners"][c]["margin_ps"], 1)
            worst = ca["margin_ps"] if ca["depth"] else min(ca["margin_ps"], -1e-3)
        elif mode == "ring_phase":
            rp = ocv.ring_phase_margin(trip, per, {c: float(ap_rp.get(c, 0.0)) for c in corners},
                                       half_cycle=bool(cfg_rp.get("half_cycle", False)))
            r["ring_phase"] = dict(K=rp["K"], step_ps=round(rp["step_ps"], 2), half_cycle=rp["half_cycle"])
            for c in corners:
                r[c]["phase_margin_ps"] = r[c]["margin_ps"]
                r[c]["margin_ps"] = round(rp["corners"][c]["margin_ps"], 1)
            worst = rp["margin_ps"]
        r["worst_margin_ps"] = round(worst, 1)
        r["pass"] = (r["kind"] != "landed") or worst >= mm
        rows.append(r)
    rows.sort(key=lambda r: r.get("worst_margin_ps", -1e9))
    landed = [r for r in rows if r.get("kind") == "landed" and "error" not in r]
    summ = dict(crossings=len(rows), landed=len(landed), min_margin_ps=mm, crossing_mode=mode0,
                spice_cal=pred.get("spice_cal"),
                fail=sum(1 for r in landed if not r["pass"]), errors=sum(1 for r in rows if "error" in r))
    for c in corners:
        if landed:
            summ[c] = dict(worst_margin_ps=min(r[c]["margin_ps"] for r in landed),
                           max_unshared_ps=max(max(r[c]["unshared_a_ps"], r[c]["unshared_b_ps"]) for r in landed))
    return dict(summary=summ, rows=rows)


def analyse(P, model, sinks, droop="regions", crossing_mode=None):
    pred = predict(P, model, sinks)
    xs = crossings(P, model, pred, droop=droop, crossing_mode=crossing_mode)
    regs = {k: dict(v, root_xy=list(v["root_xy"])) for k, v in pred["regions"].items()}
    ok = xs["summary"]["fail"] == 0 and xs["summary"]["errors"] == 0
    return dict(mode="region", verdict="PASS" if ok else "FAIL", regions=regs, crossings=xs)


def write_schema_outputs(P, res):
    import json
    Q = json.loads(json.dumps(P))
    Q["region_clock_plan"] = dict(tool="opentools.clkplan.regionmode", verdict=res["verdict"], regions=res["regions"])
    by = {(r["a"], r["b"]): r for r in res["crossings"]["rows"] if "error" not in r}
    for x in Q["crossings"]:
        r = by.get((x["a"], x["b"]))
        if r:
            x["derated_margin_ps"] = {c: r[c]["margin_ps"] for c in ("TT", "FF") if c in r}
            x["unshared_ps"] = {c: max(r[c]["unshared_a_ps"], r[c]["unshared_b_ps"]) for c in ("TT", "FF") if c in r}
            x["margin_pass"] = r["pass"]
            for k in ("count_aligned", "ring_phase"):
                if k in r:
                    x[k] = dict(r[k])
    return Q
