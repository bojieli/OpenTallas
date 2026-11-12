"""EQ check of the bound-RTL diffs s25 -> s26.  Every rst_rl_N reference is replaced by rst@<its reset-tree depth> (from
the bind's own rtl/<type>.reset_tree.json); the reset-tree relay instances themselves (u_rrl_*) are compared only as a
depth histogram.  PASS = the canonical non-tree lines are equal as a multiset in every changed .sv, i.e. every reset
consumer sees the same relay depth (same-cycle copy of the same reset) and nothing else changed."""
import json, re, sys, os, collections
A, B = sys.argv[1], sys.argv[2]
files = [l.split()[1][2:] for l in open(sys.argv[3]) if l.startswith("DIFF") and l.rstrip().endswith(".sv")]
RX = re.compile(r"\brst_rl_(\d+)\b")
def tree(bdir, tn):
    p = f"{bdir}/rtl/{tn}.reset_tree.json"
    if not os.path.exists(p):
        return None
    t = json.load(open(p))["tree"]
    return {r["q"]: r["depth"] for r in t["relays"]}
res = {}
ok = True
for f in files:
    tn = os.path.basename(f)[:-3]
    out = {}
    for side, bdir in (("a", A), ("b", B)):
        dep = tree(bdir, tn)
        if dep is None:
            out[side] = None; continue
        canon, relays = collections.Counter(), collections.Counter()
        for l in open(f"{bdir}/{f}"):
            c = RX.sub(lambda m: f"rst@{dep.get('rst_rl_' + m.group(1), '?')}", l.strip())
            if re.search(r"\bu_rrl_\d+\b", l):
                relays[c.split("(")[0].split()[-1][:0] + str(dep.get("rst_rl_" + (re.search(r"\.q\(rst_rl_(\d+)\)", l) or [None, "x"])[1], "?"))] += 1
            else:
                canon[c] += 1
        out[side] = (canon, relays)
    if out["a"] is None or out["b"] is None:
        res[f] = "no reset_tree.json (native station file)"; continue
    eq = out["a"][0] == out["b"][0]
    ok &= eq
    res[f] = {"consumers_equal_by_depth": eq, "tree_relays_by_depth_s25": dict(sorted(out["a"][1].items())),
              "tree_relays_by_depth_s26": dict(sorted(out["b"][1].items()))}
    if not eq:
        d1 = out["a"][0] - out["b"][0]; d2 = out["b"][0] - out["a"][0]
        res[f]["only_s25"] = [k[:200] for k in list(d1)[:3]]; res[f]["only_s26"] = [k[:200] for k in list(d2)[:3]]
print(json.dumps({"files": len(files), "all_consumers_equal_by_depth": ok}, indent=None))
print(json.dumps(res, indent=1)[:6000])
