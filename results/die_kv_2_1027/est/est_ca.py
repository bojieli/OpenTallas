#!/usr/bin/env python3
"""DIE-KV-2 12.14b ESTIMATE: KV locality clock form in COUNT-ALIGNED mode (MESO-COUNT-1 ruling 20:35 definition).

For each map x feed: locality.score() (shared derate: clk_aocv g021 + droop + core-lat class, LP.analyse) gives per
crossing d_tt/d_ff and p_tt/p_ff; the derated lag interval is the UNION over TT and FF (one K for both corners);
count_align_plan.plan() then picks the start tree, K and DEPTH.  Margins per crossing (both sides, ap = T/8 inside L):
  lo = L_lo - 0.5T      hi = (DEPTH - 0.5)T - L_hi        gate >= 100 ps both sides.
usage: est_ca.py PLAN OUTDIR v_ps_mm TAG=MAP [TAG=MAP ...]   (MAP = regions json | part | tree:S:C | v1:S)
"""
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src" / "tools" / "die_plan"))
import locality as LO  # noqa: E402
import count_align_plan as CAP  # noqa: E402

T = 833.0
AP = T / 8


def ca_rows(S):
    rows = []
    for r in S["crossings"]:
        lo = min(r["d_tt"] - r["p_tt"], r["d_ff"] - r["p_ff"])
        hi = max(r["d_tt"] + r["p_tt"], r["d_ff"] + r["p_ff"])
        d = r["d_tt"]
        rows.append(dict(port=r["id"], src=r["ra"], dst=r["rb"], d_ps=d, p_dn_ps=d - lo, p_up_ps=hi - d,
                         margin_ps=min(r["raw_tt"], r["raw_ff"]), unshared_a_ps=r["unshared_tt"],
                         unshared_b_ps=r["unshared_tt"], width=r["width"], on_feed=r["on_feed"]))
    return rows


def main():
    plan, out, v = sys.argv[1], Path(sys.argv[2]), float(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    D = LO.load_plan(plan)
    padj = LO.part_adjacency(D)
    M = LO.traffic(D)
    Ttab = LO.CA.load(LO.TABLE)
    res = []
    for spec in sys.argv[4:]:
        tag, m = spec.split("=", 1)
        if m.startswith("tree:"):
            _, s0, cap = m.split(":")
            reg, _ = LO.propose_tree(D, float(s0), float(cap), M, padj)
        elif m.startswith("v1:"):
            reg = LO.propose(D, float(m.split(":")[1]), M, padj)
        else:
            reg = LO.load_regions(m, D)
        (out / f"{tag}_regions.json").write_text(json.dumps(dict(part_region=reg), indent=0, sort_keys=True))
        for feed in ("fish", "spine", "top"):
            S = LO.score(D, reg, v, feed, padj, M, Ttab)
            rows = ca_rows(S)
            summ, cx = CAP.plan([dict(r) for r in rows], T, AP, 0.05)
            byp = {r["port"]: r for r in rows}
            lo_m, hi_m = [], []
            for o in cx:
                if o["depth"] is None:
                    continue
                lo_m.append(o["L_lo_ps"] - 0.5 * T)
                hi_m.append((o["depth"] - 0.5) * T - o["L_hi_ps"])
            s = S["summary"]
            row = dict(map=tag, feed=feed, regions=s["regions"], crossing_ports=s["crossing_ports"],
                       crossing_pairs=s["crossing_pairs"], bits_across=s["bits_across"],
                       frac_bits_inside=s["frac_bits_inside"], frac_bitmm_inside=s["frac_bitmm_inside"],
                       max_span_mm=round(s["max_span_mm"], 2), off_feed_ports=s["off_feed_ports"],
                       worst_unshared_on_ns=round(s["worst_unshared_on_feed_tt"] / 1000, 2),
                       worst_unshared_off_ns=round(s["worst_unshared_off_feed_tt"] / 1000, 2),
                       cur_ring_tt=s["raw_worst_tt"], cur_ring_ff=s["raw_worst_ff"],
                       ca_depth4=summ["depth4"], ca_depth8=summ["depth8"], ca_fail=summ["fail"],
                       ca_tree_components=summ["tree_components"],
                       ca_margin_lo=round(min(lo_m), 1) if lo_m else None,
                       ca_margin_hi=round(min(hi_m), 1) if hi_m else None,
                       ca_under100=sum(1 for a, b in zip(lo_m, hi_m) if min(a, b) < 100),
                       ca_max_path_amb=summ["max_path_ambiguous_cycles"], ca_max_Lw=summ["max_L_width_ps"],
                       lat_hist=summ["lat_hist"], lat_total_vs_old3=summ["lat_total_vs_old3"],
                       lat_bitcycles_vs_old3=sum(((o["lat_cycles"] or 0) - 3) * byp[o["port"]]["width"] for o in cx),
                       tracks_over_1=s["tracks_over_1"], feed_root=s["feed_root"])
            print(json.dumps(row), flush=True)
            res.append(row)
            json.dump(dict(summary=summ, crossings=cx), open(out / f"ca_{tag}_{feed}.json", "w"), indent=0)
            if feed == "fish":
                json.dump(S["feed"], open(out / f"feed_{tag}_{feed}.json", "w"), indent=0)
                try:
                    LO.render(D, S, out / f"{tag}_{feed}.png", f"KV {tag} feed {feed} (CA est)", "raw")
                except Exception as e:  # render is evidence only
                    print("render failed", e)
    json.dump(res, open(out / "est_ca.json", "w"), indent=1)


if __name__ == "__main__":
    main()
