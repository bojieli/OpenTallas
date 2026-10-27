#!/usr/bin/env python3
"""PATH-S81-PD6: per-pair classification of the related-pair die STA negatives (same formulas as
tools/die_plan/die_sta_related.py --cppr-lca --clock-ocv table --clock-droop shared; imports it).

    pd6_sta_classify_1026.py PROOF PLAN STA_OUT_DIR OUT_JSON [--core-view M=DIR ...] [--kit P=json ...] [--nominal]

Per negative pair (TT setup, FF hold) it records class (intra / seam / landed), real-vs-budget (a real endpoint
model is used in the worst combination), and a root cause:
  LANDED-REGION-LATENCY  cross-region pair: clock damage dominated by the two regions' insertion difference; split into
                         region-root arrival difference (H-tree + region-root legs) vs region-tree latency difference
  TREE-DEPTH             same region, the two taps sit at different stage depth below the LCA (unequal region tree)
  WIRE-SKEW              same region, equal depth, clock damage > 80 ps (leg / slew)
  OCV-ZERO-LOGIC         same region, damage <= 80 ps: negative only through AOCV + the zero-logic register model
                         (hold: data-path hold buffers allowed by 12.4a a1)
--nominal (INFO): early := late on every tap/node (removes the OpenSTA min/max delay-calc split, ~1.6 %/stage, that
the AOCV table already covers).
"""
import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools" / "die_plan"))
import die_sta_related as D  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("proof")
    ap.add_argument("plan")
    ap.add_argument("sta_out")
    ap.add_argument("out")
    ap.add_argument("--core-view", action="append", default=[])
    ap.add_argument("--kit", action="append", default=[])
    ap.add_argument("--core-part-delay-ps", type=float, default=0.0)
    ap.add_argument("--nominal", action="store_true")
    a = ap.parse_args()
    D.CPPR_LCA = True
    plan = json.loads(Path(a.plan).read_text())
    core_views = dict(k.split("=", 1) for k in a.core_view)
    kits = {k.split("=", 1)[0]: json.loads(Path(k.split("=", 1)[1]).read_text()) for k in a.kit}
    real = bool(core_views or kits)
    import schema as S_
    res = {}
    for c, check in (("TT", "setup"), ("FF", "hold")):
        meta, taps = D.load_taps(Path(a.proof), c)
        if a.nominal:
            for r in taps.values():
                r["early_ps"] = r["late_ps"]
            meta["node_early_ps"] = dict(meta["node_late_ps"])
            meta["cppr_node_range_ps"] = {k: 0.0 for k in meta["cppr_node_range_ps"]}
        rng = meta["cppr_node_range_ps"]
        slew = max(r["slew_ps"] for r in taps.values())
        reg = D.characterise(Path(a.sta_out), c, slew, 40.0 * 0.15)
        pairs, cov = D.build_pairs(plan, taps)
        lat = S_.common_latency_ps(S_.Plan(plan), c) if real else float(plan["clock"].get("common_latency_ps", 250.0))
        views = None
        if real:
            views, rcov = D.build_views(plan, taps, c, reg, lat, core_views, kits, 40.0 * 0.15, a.core_part_delay_ps)
        ocv = D.clock_ocv_fn("table", "shared", dict(meta, corner=c), taps,
                             float(plan["clock"].get("common_latency_ps", 250.0)))
        nl = meta["node_late_ps"]
        st = meta["node_stages"]
        cr = {}
        for k in ("intra", "seam", "landed"):
            cnt = Counter()
            worst = {}
            npairs = 0
            for x, y, tag in pairs[k]:
                A, B = taps[x], taps[y]
                npairs += 1
                la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
                node = D.pair_node(A, B)
                crd = D.credit(rng, node, la, ea, lc, ec)
                ma = views[x] if views else [D.budget_model(reg, lat)]
                mb = views[y] if views else [D.budget_model(reg, lat)]
                combos = D.endpoint_slacks(A, B, la, ea, lc, ec, crd, D.PERIOD_PS, D.UNC_SETUP_PS, D.UNC_HOLD_PS, ma, mb)
                po = ocv(x, y, check)
                i = 0 if check == "setup" else 1
                cm = min(combos, key=lambda t: t[i])
                s = cm[i] - po
                if s >= 0:
                    continue
                isreal = bool(cm[2])
                dmg = (la - ec - crd) if check == "setup" else (lc - ea - crd)
                if k == "landed":
                    dr = nl[A["cppr_node"]] - nl[B["cppr_node"]]
                    dt = (la - nl[A["cppr_node"]]) - (lc - nl[B["cppr_node"]])
                    cause = "LANDED-REGION-LATENCY:" + ("root-arrival" if abs(dr) >= abs(dt) else "region-tree")
                else:
                    dst = abs((A["stages_from_root"] - st[node]) - (B["stages_from_root"] - st[node]))
                    cause = "TREE-DEPTH" if dst > 0 and dmg > 80 else "WIRE-SKEW" if dmg > 80 else "OCV-ZERO-LOGIC"
                key = ("real" if isreal else "budget", cause)
                cnt[key] += 1
                if key not in worst or s < worst[key][0]:
                    worst[key] = (round(s, 2), x, y, tag, round(dmg, 1), round(po, 1), cm[3], cm[4])
            cr[k] = dict(pairs=npairs, neg=sum(cnt.values()),
                         by=[dict(view=kk[0], cause=kk[1], neg=v, worst_ps=worst[kk][0], launch=worst[kk][1],
                                  capture=worst[kk][2], where=worst[kk][3], clock_damage_ps=worst[kk][4],
                                  aocv_ps=worst[kk][5], models=[worst[kk][6], worst[kk][7]])
                             for kk, v in sorted(cnt.items(), key=lambda kv: -kv[1])])
        res[c + "_" + check] = cr
        if real:
            res[c + "_coverage"] = {k_: v_ for k_, v_ in rcov.items() if k_ != "core_models"}
    res["nominal_INFO"] = a.nominal
    Path(a.out).write_text(json.dumps(res, indent=1) + "\n")
    for k, v in res.items():
        if isinstance(v, dict) and "intra" in v:
            for cl, r in v.items():
                print(k, cl, "pairs", r["pairs"], "neg", r["neg"])
                for b in r["by"][:6]:
                    print("   ", b["view"], b["cause"], b["neg"], "worst", b["worst_ps"], b["where"], "dmg", b["clock_damage_ps"],
                          "aocv", b["aocv_ps"])


if __name__ == "__main__":
    main()
