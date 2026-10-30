import sys, json
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import die_trial as D, schema as S
plan = sys.argv[2]
RAW = json.load(open(plan)); P = S.Plan(RAW)
print("validate", S.validate(RAW))
res = {}
for flag in (False, True):
    D.CLOCK_TYPE_KEEPOUTS = flag; D.CLOCK_BODY_SITES = True
    site = D.clock_site(P)
    # the 89 old PHY-interior cells (Codex phy_window_census)
    bad = json.load(open(sys.argv[3]))["windows"]
    n_illegal = sum(1 for w in bad.values() for xy in w["cells"].values() if not site.legal(tuple(xy)))
    probes = {"io_serdes_2 clk": (753.018, 2319.96), "io_serdes_1 clk": (753.018, 2324.16 + 2324.064),
              "io_serdes clk": (753.018, 14005.44 + 0.096), "ucie_kv clk": (276.396, 10022.304),
              "coll_ucie clk": (188.844, 8380.704)}
    near = {k: site.nearest(v) for k, v in probes.items()}
    gap = [x for x in range(0, 1600, 5) if any(site.legal((x + 0.0, y / 1000)) for y in range(2320000, 2330000, 54))]
    res[str(flag)] = dict(old89_now_illegal=n_illegal, forb=len(site.forb),
                          nearest={k: [round(v[0], 3), round(v[1], 3)] if v else None for k, v in near.items()},
                          dist={k: round(abs(near[k][0] - probes[k][0]) + abs(near[k][1] - probes[k][1]), 3) if near[k] else None for k in probes},
                          serdes_gap_legal_x=[min(gap), max(gap), len(gap)] if gap else None)
print(json.dumps(res, indent=1))
