"""DIE-KV-20: re-derive the KV phy-tap pad counts from the CURRENT routed die tree (DIE-KV-15 kit_fb_inv_r150 + GRT arr_TT/FF),
not the DIE-KV-5 tree.  Per phy tap: unpadded arrival u_C = routed tap arrival - measured pad-chain delay (node driver ->
last pad), per-pad stage delay d_C = this tap's measured mean pad stage (TT/FF separately: pad BUF stage FF/TT ~0.77 vs tree
~0.88, so one count must serve both corners).  n = argmin over 0..8 of max_C(region tap spread incl. the phy tap), region =
the phy tap's tree region (phy_X + pc_X, 13 taps); ties -> fewer pads.  Estimate only (UNCHECKED until a re-kit + GRT).
usage: pad_rederive.py OUT.json RUNDIR TAG (TAG = kit_<TAG>/out_<TAG>_<C>); on a re-padded tree n=its own count is the measured spread"""
import json, sys, collections
R = sys.argv[2]; TG = sys.argv[3]
T = json.load(open(f"{R}/kit_{TG}/clock/tree.json"))
nodes = {int(k): v for k, v in T["nodes"].items()}
def region_of(i):
    while i is not None:
        if nodes[i].get("region_root") is not None: return nodes[i]["region_root"]
        i = nodes[i]["parent"]
reg = collections.defaultdict(list)
for t in T["taps"]: reg[region_of(t["node"])].append(t)
A = {}
for C in ("TT", "FF"):
    rows = [l.split() for l in open(f"{R}/out_{TG}_{C}/arr_{C}.txt")]
    A[C] = ({p[1]: float(p[2]) for p in rows if p[0] == "N"}, {p[1]: float(p[2]) for p in rows if p[0] == "T"})
old = json.load(open("/srv/opentallas-scratch2/claude/die-kv-5-1027/pad/pad_it2.json"))["pad"]
res, new = {}, {}
for t in T["taps"]:
    if not t["port"].startswith("t_phy_"): continue
    ts = [x for x in reg[region_of(t["node"])] if x["port"] != t["port"]]
    pp = [x for x in t["path"] if x.startswith("p")]
    nb = T["node_buf"][str(t["node"])]
    r = dict(region=region_of(t["node"]), old=len(pp), old_file=old.get(t["port"]), corners={})
    for C in ("TT", "FF"):
        arr, tarr = A[C]
        dp = arr[pp[-1]] - arr[nb] if pp else 0.0
        d = dp / len(pp)
        u = tarr[t["port"]] - dp
        o = [tarr[x["port"]] for x in ts]
        r["corners"][C] = dict(pad_stage_ps=round(d, 2), unpadded_ps=round(u, 1), others_min=round(min(o), 1),
                               others_max=round(max(o), 1), others_spread=round(max(o) - min(o), 1))
    best = None
    for n in range(0, 9):
        sp, late = {}, {}
        for C in ("TT", "FF"):
            c = r["corners"][C]; a = c["unpadded_ps"] + n * c["pad_stage_ps"]
            sp[C] = round(max(c["others_max"], a) - min(c["others_min"], a), 1)
            late[C] = round(a - c["others_max"], 1)
        k = (max(sp.values()), n)
        if best is None or k < best[0]:
            best = (k, n, sp, late)
        if n == len(pp):
            r["spread_old"], r["late_vs_max_old"] = sp, late
    r["new"], r["spread_new"], r["late_vs_max_new"] = best[1], best[2], best[3]
    res[t["port"]] = r; new[t["port"]] = best[1]
s = dict(pad=new, note="DIE-KV-20: re-derived from the current tree (DIE-KV-15 kit_fb_inv_r150 GRT TT+FF), min max-corner region spread; replaces DIE-KV-5 pad_it2")
json.dump(dict(pad_json=s, detail=res), open(sys.argv[1], "w"), indent=1)
w = lambda k: max(max(r[k].values()) for r in res.values())
print("pads old", sum(r["old"] for r in res.values()), "new", sum(new.values()), "changed", sum(r["old"] != r["new"] for r in res.values()))
print("worst region spread (max TT/FF) old", w("spread_old"), "new", w("spread_new"),
      "| phy late vs region max old TT", max(r["late_vs_max_old"]["TT"] for r in res.values()), "new TT", max(r["late_vs_max_new"]["TT"] for r in res.values()),
      "old FF", max(r["late_vs_max_old"]["FF"] for r in res.values()), "new FF", max(r["late_vs_max_new"]["FF"] for r in res.values()))
print("others-only spread max TT", max(r["corners"]["TT"]["others_spread"] for r in res.values()), "FF", max(r["corners"]["FF"]["others_spread"] for r in res.values()))
print("late-after-max regions old TT", sum(r["late_vs_max_old"]["TT"] > 0 for r in res.values()), "new TT", sum(r["late_vs_max_new"]["TT"] > 0 for r in res.values()))
for p, r in sorted(res.items()):
    print(p, r["old"], "->", r["new"], "spread", r["spread_old"], "->", r["spread_new"], "late", r["late_vs_max_old"], "->", r["late_vs_max_new"])
