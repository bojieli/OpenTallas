"""re-select each reset_start_raw export on the regenerated reset tree: same role + same depth as the old source
relay, nearest to the old (mapped) declared xy; distinct relays per port unless the old ports shared one."""
import sys, json, math
sys.path.insert(0, sys.argv[3] + "/tools/die_plan")
import schema as S, reset_tree as RT
from pathlib import Path
def relays(raw, path, tn):
    P = S.Plan(raw, Path(path))
    tree = RT.for_type(P, tn)
    st = bool(tree.get("start"))
    rl = RT.start_relays(tree) if st else tree["relays"]
    return [r for r in rl if not st or r.get("role") in ("raw", "boot", "bootstrap_transport")]
base_p, new_p = sys.argv[1], sys.argv[2]
A = json.load(open(base_p)); B = json.load(open(new_p))
for tn in ("hd_lep0N", "hd_st_n4"):
    ra = {r["name"]: r for r in relays(A, base_p, tn)}
    rb = relays(B, new_p, tn)
    shared = {}
    used = set()
    for e in B["partition_types"][tn]["reset_start_raw_exports"]:
        o = ra[e["instance"]]
        key = e["instance"]
        if key in shared:
            n = shared[key]
        else:
            cands = [r for r in rb if r.get("role") == o.get("role") and r.get("depth") == o.get("depth") and r["name"] not in used]
            n = min(cands, key=lambda r: math.dist(r["xy"], e["xy_um"]))
            used.add(n["name"]); shared[key] = n
        print(tn, e["port"], o["name"], o.get("role"), o.get("depth"), "->", n["name"], n["q"], n["xy"], "dist %.1f" % math.dist(n["xy"], e["xy_um"]))
        e["instance"], e["net"], e["xy_um"] = n["name"], n["q"], list(n["xy"])
json.dump(B, open(new_p, "w"), indent=1)
