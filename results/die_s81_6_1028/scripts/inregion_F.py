#!/usr/bin/env python3
"""DIE-S81-6: per-region intra (in-region) spread incl OCV+droop from the SHARED die_sta_related run (MR2 spice copy):
re-runs it with the same args as post.sh and captures every intra pair's clock damage (the 'skew' diagnostic),
grouped by partition (= region).  Diagnostic only: the gate numbers are the run's own SUMMARY."""
import builtins, collections, json, re, sys
MR = "/srv/opentallas-scratch2/claude/die-s81-4/mr2/tools/die_plan"
sys.path.insert(0, MR)
import die_sta_related as DS
cap = []
_sorted = builtins.sorted
def spy(x, *a, **k):
    if k.get("reverse") and isinstance(x, list) and x and isinstance(x[0], tuple) and len(x[0]) == 3:
        cap.append(list(x))
    return _sorted(x, *a, **k)
DS.sorted = spy
O = "/srv/opentallas-scratch2/claude/die-s81-5"; V = sys.argv[1]; OUT = sys.argv[2]
PR = f"{O}/proof_{V}"
args = [PR, "--plan", f"{O}/plan_s5.json", "--out", OUT, "--cppr-lca", "--clock-ocv", "table", "--clock-droop", "shared",
        "--clock-cal", "spice", "--droop-regions", f"{PR}/droop_regions.json", "--core-latency-ff", "202.5",
        "--hold-buffers", "HB4", "--landing-window-ps", "416.5"]
DS.main(args)
d = json.load(open(f"{OUT}/die_sta_related.json"))
plan = json.load(open(f"{O}/plan_s5.json"))
ptype = {p["name"]: p["type"] for p in plan["partitions"]}
tree = json.load(open(f"{O}/clk_{V}/tree.json"))
tap_part = {t["port"]: t["part"] for t in tree["taps"]}
imb = collections.defaultdict(float)
for n in tree["nodes"].values():
    r = n.get("region_root")
# region of every node: walk to region_root
N = tree["nodes"]; memo = {}
def reg(i):
    path = []
    while i is not None and i not in memo:
        n = N[str(i)]
        if "region_root" in n:
            memo[i] = n["region_root"]; break
        path.append(i); i = n["parent"]
    v = memo.get(i)
    for p in path: memo[p] = v
    return v
for k, n in N.items():
    if n.get("balance_imbalance_um"):
        r = reg(int(k)); imb[r] = max(imb[r], n["balance_imbalance_um"])
# intra captures: first TT intra then FF intra (time_class order: intra, landed, landed_nearest per corner)
intra_sets = [c for c in cap if all(tap_part.get(a) == tap_part.get(b) for _, a, b in c[:50])]
res = {}
for C, rows in zip(("TT", "FF"), intra_sets[:2]):
    for v, a, b in rows:
        p = tap_part[a]
        res.setdefault(p, {}).setdefault(C, 0.0)
        res[p][C] = max(res[p][C], v)
def kind(p):
    t = plan["partition_types"][ptype[p]]
    hc = t.get("hard_cores", [])
    mods = " ".join(h["module"] for h in hc).lower()
    big = max([h["outline_um"][0] * h["outline_um"][1] for h in hc] + [0])
    m = re.search(r"sram|ram\b|rom|mem|serdes|phy|bank|macro", mods)
    return ("SRAM/macro" if (m or big > 40000) else "logic"), len(hc), round(big), (m.group(0) if m else "")
rows = []
for p, v in res.items():
    k = kind(p)
    rows.append(dict(region=p, type=ptype[p], tt=round(v.get("TT", 0), 1), ff=round(v.get("FF", 0), 1), kind=k[0],
                     hard_cores=k[1], max_core_um2=k[2], match=k[3], worst_merge_imbalance_um=round(imb.get(p, 0), 1)))
rows.sort(key=lambda r: -r["tt"])
over = [r for r in rows if r["tt"] > 150 or r["ff"] > 150]
summ = dict(regions=len(rows), over150=len(over), over150_by_kind=collections.Counter(r["kind"] for r in over),
            max_tt=rows[0]["tt"], max_ff=max(r["ff"] for r in rows),
            p50_tt=_sorted(r["tt"] for r in rows)[len(rows) // 2], intra_sets_captured=len(intra_sets))
json.dump(dict(summary=summ, rows=rows), open(f"{OUT}/inregion_{V}.json", "w"), indent=1)
print("INREGION", json.dumps(summ))
for r in over[:40]:
    print(json.dumps(r))
