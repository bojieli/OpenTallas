#!/usr/bin/env python3
"""DIE-S81-17: ROOT CAUSE of the go15 intra-region skew/hold (ESTIMATE/diagnostic, fixes nothing).
Runs main tools/die_plan/die_sta_related.py UNCHANGED (args after --), wraps time_class to capture the exact intra-class
arguments for TT and FF, then re-times every intra pair with the same formulas (arr4/credit/endpoint models) and splits
  hold damage D = (lc + latB_late) - (ea + latA_early) - cr        (what hold actually pays, incl. declared core insertion)
    = tree_ee (ec - ea)              nominal tree early-early difference
    + unc_spread (lc - ec - cr)      capture late/early spread not credited by CPPR
    + lat (latB_late - latA_early)   endpoint insertion difference (declared core insertion, 0 for plain register taps)
  skew_diag (tool) = max(la - ec - cr, lc - ea - cr)  = raw tap arrivals, WITHOUT the declared core insertion.
Each pair is classified by endpoint kind: reg (plain tap t_<part>__clk), core:<module> (early core tap), and ROM vs
non-ROM (either endpoint a rom_elem_q* core tap).
usage: skew_root.py TOOLS MAP.json OUT.json -- <die_sta_related args>"""
import collections, inspect, json, sys
tools, mp, outp = sys.argv[1], sys.argv[2], sys.argv[3]
args = sys.argv[sys.argv.index("--") + 1:]
sys.path.insert(0, tools)
import die_sta_related as R
part_region = json.load(open(mp))["part_region"]
orig, calls = R.time_class, []
sig = inspect.signature(orig)


def wrap(*a, **k):
    calls.append(sig.bind(*a, **k).arguments)
    return orig(*a, **k)


R.time_class = wrap
R.main(args)
out = args[args.index("--out") + 1]
plan = args[args.index("--plan") + 1]
J = json.load(open(out + "/die_sta_related.json"))
res = dict(tool_summary=J["summary"], corners={})
ecm_all = None
for ci, C in enumerate(("TT", "FF")):
    n = J["corners"][C]["classes"]["intra"]["pairs"]
    cand = [c for c in calls if len(c["pairs"]) == n]
    A_ = cand[ci] if len(cand) == 2 else cand[0]
    taps, rng, reg, ocv, views = A_["taps"], A_["rng"], A_["reg"], A_.get("ocv"), A_.get("views")
    if ecm_all is None:
        ecm_all = R.early_core_map(json.load(open(plan)), taps)
    kind = {}
    for p in taps:
        if p in ecm_all:
            mods = sorted({str(e.get("module")) for e in ecm_all[p]})
            kind[p] = "core:" + "+".join(mods)
        else:
            kind[p] = "reg" if p.endswith("__clk") else "other:" + p.rsplit("__", 1)[-1]
    rows = []
    for a, b, tag in A_["pairs"]:
        TA, TB = taps[a], taps[b]
        node = R.pair_node(TA, TB)
        la, ea, lc, ec = R.arr4(TA, TB, node)
        cr = R.credit(rng, node, la, ea, lc, ec)
        ma_l = views[a] if views else [R.budget_model(reg, 0.0)]
        mb_l = views[b] if views else [R.budget_model(reg, 0.0)]
        best = None
        for ma in ma_l:
            for mb in mb_l:
                h = (ea + ma["lat_early"] + ma["clkq_min"]) - (lc + mb["lat_late"] + mb["hold"]) - A_["unc_h"] + cr
                if best is None or h < best[0]:
                    best = (h, ma, mb)
        h, ma, mb = best
        oh = ocv(a, b, "hold") if ocv else 0.0
        h -= oh
        ka, kb = kind[a], kind[b]
        rom = "rom" in ka or "rom" in kb
        cls = "rom" if rom else ("core" if ka.startswith("core") or kb.startswith("core") else "reg-reg")
        rows.append(dict(h=h, a=a, b=b, tag=tag, region=part_region.get(tag, tag), ka=ka, kb=kb, cls=cls,
                         tree_ee=ec - ea, unc_spread=lc - ec - cr, lat=mb["lat_late"] - ma["lat_early"], ocv=oh,
                         data=ma["clkq_min"] - mb["hold"], cr=cr, D=(lc + mb["lat_late"]) - (ea + ma["lat_early"]) - cr,
                         diag=max(la - ec - cr, lc - ea - cr), lat_a=ma["lat_early"], lat_b=mb["lat_late"],
                         ea=ea, lc=lc, st_a=TA.get("stages_from_root"), st_b=TB.get("stages_from_root"),
                         lca=len(node), dist=abs(TA["xy_um"][0] - TB["xy_um"][0]) + abs(TA["xy_um"][1] - TB["xy_um"][1])))
    # per region
    byr = collections.defaultdict(list)
    for r in rows:
        byr[r["region"]].append(r)
    reg_rows = {}
    for g, rs in byr.items():
        w = min(rs, key=lambda r: r["h"])
        wd = max(rs, key=lambda r: r["diag"])
        wD = max(rs, key=lambda r: r["D"])
        percls = {}
        for k in ("rom", "core", "reg-reg"):
            sub = [r for r in rs if r["cls"] == k]
            if sub:
                x = min(sub, key=lambda r: r["h"])
                percls[k] = dict(n=len(sub), worst_hold=round(x["h"], 1), neg=sum(r["h"] < 0 for r in sub),
                                 max_D=round(max(r["D"] for r in sub), 1), max_diag=round(max(r["diag"] for r in sub), 1))
        # tap arrival spread inside the region (early arrivals at taps, by kind)
        tps = {r["a"] for r in rs} | {r["b"] for r in rs}
        arr = collections.defaultdict(list)
        for p in tps:
            arr[kind[p]].append(taps[p].get("abs_early_ps", taps[p]["early_ps"]))
        reg_rows[g] = dict(pairs=len(rs), worst_hold=round(w["h"], 1), hold_neg=sum(r["h"] < 0 for r in rs),
                           worst=dict({k: (round(v, 1) if isinstance(v, float) else v) for k, v in w.items()}),
                           max_diag=round(wd["diag"], 1), max_diag_pair=[wd["a"], wd["b"], wd["ka"], wd["kb"]],
                           max_D=round(wD["D"], 1), max_D_pair=[wD["a"], wD["b"], wD["ka"], wD["kb"]],
                           per_class=percls,
                           tap_early_by_kind={k: dict(n=len(v), min=round(min(v), 1), max=round(max(v), 1))
                                              for k, v in arr.items()})
    allneg = [r for r in rows if r["h"] < 0]

    def agg(rs):
        if not rs:
            return None
        return {x: round(sum(r[x] for r in rs) / len(rs), 1) for x in
                ("h", "tree_ee", "unc_spread", "lat", "ocv", "data", "cr", "D", "diag")} | dict(n=len(rs))
    dom = collections.Counter()
    for r in allneg:
        t = dict(tree_ee=r["tree_ee"], unc_spread=r["unc_spread"], lat=r["lat"], ocv=r["ocv"])
        dom[max(t, key=t.get)] += 1
    cls_sum = {}
    for k in ("rom", "core", "reg-reg"):
        sub = [r for r in rows if r["cls"] == k]
        if sub:
            cls_sum[k] = dict(pairs=len(sub), neg=sum(r["h"] < 0 for r in sub), worst_hold=round(min(r["h"] for r in sub), 1),
                              max_D=round(max(r["D"] for r in sub), 1), max_diag=round(max(r["diag"] for r in sub), 1),
                              mean_neg=agg([r for r in sub if r["h"] < 0]))
    res["corners"][C] = dict(pairs=len(rows), neg=len(allneg), worst_hold=round(min(r["h"] for r in rows), 2),
                             max_diag=round(max(r["diag"] for r in rows), 2), max_D=round(max(r["D"] for r in rows), 2),
                             dominant_all_neg=dom, mean_all_neg=agg(allneg), by_class=cls_sum,
                             neg_if_no_unc_spread=sum(1 for r in allneg if r["h"] + r["unc_spread"] < 0),
                             neg_if_no_unc_spread_no_ocv=sum(1 for r in allneg if r["h"] + r["unc_spread"] + r["ocv"] < 0),
                             regions=dict(sorted(reg_rows.items(), key=lambda kv: kv[1]["worst_hold"])))
json.dump(res, open(outp, "w"), indent=1, default=str)
for C, v in res["corners"].items():
    print(C, {k: v[k] for k in ("pairs", "neg", "worst_hold", "max_diag", "max_D", "dominant_all_neg", "mean_all_neg")})
    for k, s in v["by_class"].items():
        print("  class", k, s)
    for g in list(v["regions"])[:12]:
        x = v["regions"][g]
        w = x["worst"]
        print(f"  {g:12s} hold {x['worst_hold']:8.1f} neg {x['hold_neg']}/{x['pairs']} diag {x['max_diag']} D {x['max_D']} | "
              f"worst {w['ka']}->{w['kb']} tree_ee {w['tree_ee']} unc_spread {w['unc_spread']} lat {w['lat']} ocv {w['ocv']} "
              f"st {w['st_a']}/{w['st_b']} dist {w['dist']} | {x['tap_early_by_kind']}")
