"""Latency budgets per macro, skew per region, derated phase margin per crossing (on a planned Tree)."""
import math

from . import ocv
from . import tree as TR


def budgets(T, target_ps=None, corner="TT"):
    """per sink: tap arrival target = common latency target - own insertion (macro insertion-delay balancing,
    METHODOLOGY 12.3 v5.0 early taps); balance_ps = target tap arrival - predicted tree arrival
    (> 0: delay to add at the tap; < 0: the macro needs an earlier tap than the tree gives -> tap higher up)."""
    lat = [s["latency"][corner] for s in T.sinks]
    tgt = target_ps if target_ps is not None else (max(lat) if lat else 0.0)
    rows = []
    for s in T.sinks:
        ins = float(s["insertion_ps"].get(corner, 0.0))
        tap = tgt - ins
        rows.append(dict(sink=s["name"], macro=s.get("macro"), region=s.get("region"), insertion_ps=round(ins, 1),
                         tree_arrival_ps=round(s["arr"][corner], 1), tap_target_ps=round(tap, 1),
                         balance_ps=round(tap - s["arr"][corner], 1)))
    early = [r for r in rows if r["balance_ps"] < -1e-6]
    return dict(corner=corner, target_latency_ps=round(tgt, 1), rows=rows, early_taps=len(early),
                pad_total_ps=round(sum(max(0.0, r["balance_ps"]) for r in rows), 1),
                worst_early_ps=round(min((r["balance_ps"] for r in early), default=0.0), 1))


def region_skew(T, corners=("TT", "FF")):
    """nominal latency spread inside each region (arrival + own insertion), worst pair OCV not included."""
    regs = {}
    for s in T.sinks:
        regs.setdefault(s.get("region") or "-", []).append(s)
    out = []
    for r, ss in sorted(regs.items()):
        row = dict(region=r, sinks=len(ss))
        for c in corners:
            lat = [s["latency"][c] for s in ss]
            row[f"skew_{c}_ps"] = round(max(lat) - min(lat), 1)
            row[f"latency_{c}_ps"] = [round(min(lat), 1), round(max(lat), 1)]
        out.append(row)
    return out


def crossings(T, model, plan_crossings, period_ps, min_margin_ps=100.0, corners=("TT", "FF"), droop="regions"):
    """plan_crossings: [dict(name, a, b, kind='landed'|'sync', budget_ps?, bits?)].  a/b = sink names.
    droop 'regions' = shared-droop rule (0 if a, b in one region, else one-sided on the late branch); 'always' = charge
    one-sided droop on every pair (conservative, for plans without a region/PDN map)."""
    Tb = model.T
    by = {s["name"]: s for s in T.sinks}
    rows = []
    for x in plan_crossings:
        a, b = by.get(x["a"]), by.get(x["b"])
        if a is None or b is None:
            rows.append(dict(name=x.get("name"), a=x["a"], b=x["b"], error="sink not in tree"))
            continue
        l = TR.lca(T, a, b)
        lxy = T.cells[l]["xy"]
        pts = [a["xy"], b["xy"], lxy]
        dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
        na, nb = TR.stages_below(T, a, l), TR.stages_below(T, b, l)
        same = (droop != "always") and (a.get("region") is not None and a.get("region") == b.get("region"))
        budget = float(x.get("budget_ps") or period_ps / 2.0)
        r = dict(name=x.get("name"), a=a["name"], b=b["name"], kind=x.get("kind", "landed"), bits=x.get("bits"),
                 lca=T.cells[l].get("name", T.cells[l]["kind"]), lca_level=T.cells[l]["level"], dist_um=round(dist, 1),
                 stages_a=na, stages_b=nb, same_region=same, budget_ps=budget)
        worst = None
        for c in corners:
            ua = a["arr"][c] - T.cells[l]["arr"][c]
            ub = b["arr"][c] - T.cells[l]["arr"][c]
            bra = ocv.branch(Tb, c, ua, na, float(a["insertion_ps"].get(c, 0.0)))
            brb = ocv.branch(Tb, c, ub, nb, float(b["insertion_ps"].get(c, 0.0)))
            d = b["latency"][c] - a["latency"][c]
            p_up, p_dn, der, mg = ocv.landed_margin(Tb, c, d, bra, brb, dist, same, budget)
            r[c] = dict(unshared_a_ps=round(ua, 1), unshared_b_ps=round(ub, 1), d_ps=round(d, 1), p_up_ps=round(p_up, 1),
                        p_dn_ps=round(p_dn, 1), derated_abs_ps=round(der, 1), margin_ps=round(mg, 1))
            if worst is None or mg < worst:
                worst = mg
        r["worst_margin_ps"] = round(worst, 1)
        r["pass"] = (r["kind"] != "landed") or worst >= min_margin_ps
        rows.append(r)
    rows.sort(key=lambda r: r.get("worst_margin_ps", -1e9))
    landed = [r for r in rows if r.get("kind") == "landed" and "error" not in r]
    summ = dict(crossings=len(rows), landed=len(landed), min_margin_ps=min_margin_ps,
                fail=sum(1 for r in landed if not r["pass"]), errors=sum(1 for r in rows if "error" in r))
    for c in corners:
        ok = [r for r in rows if c in r]
        if ok:
            summ[c] = dict(worst_margin_ps=min(r[c]["margin_ps"] for r in ok if r["kind"] == "landed") if landed else None,
                           max_unshared_ps=round(max(max(r[c]["unshared_a_ps"], r[c]["unshared_b_ps"]) for r in ok), 1),
                           under_min=sum(1 for r in ok if r["kind"] == "landed" and r[c]["margin_ps"] < min_margin_ps),
                           under_0=sum(1 for r in ok if r["kind"] == "landed" and r[c]["margin_ps"] < 0))
    return dict(summary=summ, rows=rows)
