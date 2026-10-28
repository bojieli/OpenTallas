#!/usr/bin/env python3
"""DIE-S81-2: 12.14b estimate of an S81 region map in COUNT-ALIGNED mode (MESO-COUNT-1 ruling 10-27 20:35).

    s81_ca_estimate.py --plan PLAN --map MAP.json --v-ps-mm 335 --feed fish --out OUT.json [--map-key proposed_map]

No new model: crossings, feed tree, branches and the derated TT/FF phase intervals come from the shared
tools/die_plan/locality.py (main d1037e4d41: score/branches/margins -> tools/s81_head/landed_phase_ocv.analyse, clk_aocv
g021 + droop 'regions'); the count-aligned window, start tree, path ambiguity, K and DEPTH come from
tools/die_plan/count_align_plan.plan (claude/meso-count-1027@258bc16208), TT and FF intervals UNIONED (one K for both
corners, as count_align_plan main).  Margins per the ruling: low = L_lo - 0.5T, high = (DEPTH-0.5)T - L_hi
(L_lo/L_hi include the aperture ap = T/8 = 104.1 ps, so DEPTH != None <=> both margins >= ap >= 100 ps).
Every crossing port is a row (loop-closing links included: they are 'nontree' rows whose K must be consistent around
the loop -> path ambiguity cycles of the start tree are charged to them).
"""
import argparse
import collections
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = [p for p in HERE.parents if (p / "tools" / "die_plan" / "locality.py").exists()][0]
sys.path.insert(0, str(ROOT / "tools" / "die_plan"))
import locality as LO  # noqa: E402
import count_align_plan as CAP  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--map", required=True)
    ap.add_argument("--map-key", default=None)
    ap.add_argument("--v-ps-mm", type=float, default=335.0)
    ap.add_argument("--feed", default="fish")
    ap.add_argument("--period", type=float, default=833.0)
    ap.add_argument("--aperture", type=float, default=833.0 / 8)
    ap.add_argument("--out", required=True)
    ap.add_argument("--png", default=None, help="render map/feed/crossings coloured by the count-aligned margin")
    ap.add_argument("--hop-fail", action="store_true", help="12.13c only where needed: crossings that fail the direct "
                    "count-aligned window become hop chains along the feed tree; all others stay direct")
    ap.add_argument("--hop", action="store_true", help="12.13c: off-feed crossings re-timed as hop chains along the "
                    "feed tree (locality.hop_rows); only on-feed + synthetic feed-edge crossings are rows")
    a = ap.parse_args()
    D = LO.load_plan(a.plan)
    m = json.loads(Path(a.map).read_text())
    if a.map_key:
        m = m[a.map_key]
    reg = LO.load_regions(m, D)
    padj = LO.part_adjacency(D)
    M = LO.traffic(D)
    Ttab = LO.CA.load(LO.TABLE)
    # capture the full landed_phase_ocv rows (d, p_up, p_dn per corner) of the shared margin model
    cap = collections.defaultdict(list)
    real = LO.LP.analyse

    def wrap(*args, **kw):
        rows = real(*args, **kw)
        cap[args[5]].append(rows)  # corner
        return rows
    LO.LP.analyse = wrap
    if a.feed == "fishspt":
        # spine_fishbone feed whose spine follows the SHORTEST-PATH tree of the region links (spine delays) instead of
        # the max-bit spanning tree; region trees = fishbone (same leaf/shared model as 'fish')
        oft, ohd = LO.feed_tree, LO.hop_delay

        def ft(G, E, X, v, kind="fwd"):
            LO.hop_delay = lambda G_, p, c, t, v_, k: ohd(G_, p, c, t, v_, "spine")
            try:
                F = oft(G, E, X, v, "spt")
            finally:
                LO.hop_delay = ohd
            F["kind"] = "fish"
            return F
        LO.feed_tree = ft
        LO.SPINE_FEEDS = LO.SPINE_FEEDS + ("fishspt",)
    S = LO.score(D, reg, a.v_ps_mm, a.feed, padj, M, Ttab)
    s = S["summary"]
    # first call per corner = the nopad crossing rows (spine feeds have no pad reading)
    tt = {int(r["port"]): r for r in cap["TT"][0]}
    ff = {int(r["port"]): r for r in cap["FF"][0]}
    per = S["crossings"]
    assert len(per) == len(tt) == len(ff)
    pairs = [(x, tt[i], ff[i]) for i, x in enumerate(per)]
    if a.hop:
        pairs = [p for p in pairs if p[0]["on_feed"]]
        syn = [r for r in S["crossings_hop"] if r.get("synthetic")]
        if syn:
            tt2 = {int(r["port"]): r for r in cap["TT"][1]}
            ff2 = {int(r["port"]): r for r in cap["FF"][1]}
            pairs += [(x, tt2[i], ff2[i]) for i, x in enumerate(syn)]
        s["hop_chains"], s["hop_max_hops"] = s.get("hop_chains"), s.get("hop_max_hops")
    def mkrows(pairs):
        rows = []
        for x, t, f in pairs:
            lo = min(t["d_ps"] - t["p_dn_ps"], f["d_ps"] - f["p_dn_ps"])
            hi = max(t["d_ps"] + t["p_up_ps"], f["d_ps"] + f["p_up_ps"])
            rows.append(dict(port=str(x["id"]), src=x["ra"], dst=x["rb"], d_ps=t["d_ps"], p_dn_ps=t["d_ps"] - lo,
                             p_up_ps=hi - t["d_ps"], margin_ps=min(t["margin_ps"], f["margin_ps"]),
                             unshared_a_ps=x["unshared_tt"], unshared_b_ps=x["unshared_tt"],
                             width=x["width"], on_feed=x["on_feed"], tree_hops=x["tree_hops"]))
        return rows
    if a.hop_fail:
        _, o0 = CAP.plan([dict(r) for r in mkrows(pairs)], a.period, a.aperture, 0.05)
        bad = {o["port"] for o in o0 if not o["depth"]}
        X = LO.crossings(D, reg, S["G"], padj)
        idx = [i for i, x in enumerate(per) if str(x["id"]) in bad]
        Tr, _ = LO.arrivals(S["G"], S["F"], a.v_ps_mm, None)
        n0 = len(cap["TT"])
        HR, hst = LO.hop_rows(S["G"], S["F"], Tr, a.v_ps_mm, [X[i] for i in idx], [per[i] for i in idx], Ttab,
                              D["period"])
        syn = [r for r in HR if r.get("synthetic")]
        keep = [p for p in pairs if str(p[0]["id"]) not in bad]
        if syn:
            tt2 = {int(r["port"]): r for r in cap["TT"][n0]}
            ff2 = {int(r["port"]): r for r in cap["FF"][n0]}
            keep += [(x, tt2[i], ff2[i]) for i, x in enumerate(syn)]
        pairs = keep
        hst["hop_failed_direct"] = len(bad)
        hst["hop_chain_bits"] = sum(per[i]["width"] for i in idx)
        s.update(hst)
    rows = []
    for x, t, f in pairs:
        lo = min(t["d_ps"] - t["p_dn_ps"], f["d_ps"] - f["p_dn_ps"])
        hi = max(t["d_ps"] + t["p_up_ps"], f["d_ps"] + f["p_up_ps"])
        rows.append(dict(port=str(x["id"]), src=x["ra"], dst=x["rb"], d_ps=t["d_ps"], p_dn_ps=t["d_ps"] - lo,
                         p_up_ps=hi - t["d_ps"], margin_ps=min(t["margin_ps"], f["margin_ps"]),
                         unshared_a_ps=x["unshared_tt"], unshared_b_ps=x["unshared_tt"],
                         width=x["width"], on_feed=x["on_feed"], tree_hops=x["tree_hops"]))
    summ, out = CAP.plan([dict(r) for r in rows], a.period, a.aperture, 0.05)
    T = a.period
    meta = {r["port"]: r for r in rows}
    for o in out:
        if o["depth"]:
            o["margin_lo_ps"] = round(o["L_lo_ps"] - 0.5 * T, 1)
            o["margin_hi_ps"] = round((o["depth"] - 0.5) * T - o["L_hi_ps"], 1)
        else:
            o["margin_lo_ps"] = round(o["L_lo_ps"] - 0.5 * T, 1)
            o["margin_hi_ps"] = round(7.5 * T - o["L_hi_ps"], 1)
        o["width"] = meta[o["port"]]["width"]
        o["on_feed"] = meta[o["port"]]["on_feed"]
        o["unshared_tt_ps"] = meta[o["port"]]["unshared_a_ps"]
    ok = [o for o in out if o["depth"]]
    summ.update(
        loc_summary={k: s.get(k) for k in ("feed", "v_ps_per_mm", "regions", "crossing_ports", "crossing_pairs",
                                           "frac_bits_inside", "frac_bitmm_inside", "off_feed_ports", "loop_pairs",
                                           "max_span_mm", "max_ins_ps", "worst_unshared_tt",
                                           "worst_unshared_on_feed_tt", "worst_unshared_off_feed_tt", "max_tree_hops",
                                           "raw_worst_tt", "raw_worst_ff", "ca_worst_tt", "ca_worst_ff",
                                           "tracks_over_1", "tracks_worst_ratio", "hop_chains", "hop_max_hops", "hop_extra_bit_hops", "hop_synthetic_edges", "hop_failed_direct", "hop_chain_bits")},
        worst_margin_lo_ps=min((o["margin_lo_ps"] for o in ok), default=None),
        worst_margin_hi_ps=min((o["margin_hi_ps"] for o in ok), default=None),
        under100=sum(1 for o in out if not o["depth"] or min(o["margin_lo_ps"], o["margin_hi_ps"]) < 100),
        offfeed_depth8=sum(1 for o in out if o["depth"] == 8 and not o["on_feed"]),
        plan=a.plan, map=a.map, aperture_ps=a.aperture)
    regs = {r["region"]: r for r in S["regions"]}
    summ["phy_region"] = [r for r in S["regions"] if r["hard"] or r["w_mm"] > 8]
    Path(a.out).write_text(json.dumps(dict(summary=summ, crossings=out, regions=S["regions"],
                                           feed=S["feed"]), indent=0, default=str))
    print(json.dumps({k: v for k, v in summ.items() if k != "tree_edges_ambiguous"}, indent=1, default=str))
    worst = sorted(out, key=lambda o: min(o["margin_lo_ps"], o["margin_hi_ps"]))[:10]
    for o in worst:
        print(o["port"], o["src"], o["dst"], o["kind"], o["depth"], o["path_ambiguous_cycles"], o["L_lo_ps"],
              o["L_hi_ps"], o["margin_lo_ps"], o["margin_hi_ps"], round(o["unshared_tt_ps"]), o["on_feed"])
    _ = regs
    if a.png:
        cm = {o["port"]: (min(o["margin_lo_ps"], o["margin_hi_ps"]) if o["depth"] else -999.0) for o in out}
        rr = []
        for r in S["crossings"]:
            if str(r["id"]) in cm:
                r["cam_tt"] = r["cam_ff"] = cm[str(r["id"])]
                rr.append(r)
        S["crossings"], S["crossings_pad"] = rr, []
        S["_reg"] = reg
        LO.render(D, S, a.png, f"S81 98-region map, feed {a.feed} @ {a.v_ps_mm:g} ps/mm, COUNT-ALIGNED (D4/D8) margin "
                  f"min(lo,hi): {summ['depth4']} D4 / {summ['depth8']} D8 / {summ['fail']} fail", "cam")
    return 0


if __name__ == "__main__":
    sys.exit(main())
