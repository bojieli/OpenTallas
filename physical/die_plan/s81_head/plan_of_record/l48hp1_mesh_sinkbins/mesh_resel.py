"""DIE-LAYOUT-KVHEAD 11-11: hd_mesh sink-bins event, reset re-select (rt_resel.py / compose.py RAWSEL rule, HEAD-94 cut).
The density taps (now from clock.sink_bins_file) re-solve the hd_mesh reset tree; re-select every reset_start_raw export
and its landing_contract pin source on the regenerated tree (same role + depth, nearest the old declared xy, pin offset kept),
then every stage / local-reset raw reference (keep the Q if it survives at the same depth within 25 um of the best)."""
import sys, json, math
from pathlib import Path
sys.path.insert(0, sys.argv[3] + "/tools/die_plan")
import schema as S, reset_tree as RT
TN = "hd_mesh"
def tree(raw, path):
    return RT.for_type(S.Plan(raw, Path(path)), TN)
def start_relays(t):
    st = bool(t.get("start"))
    rl = RT.start_relays(t) if st else t["relays"]
    return [r for r in rl if not st or r.get("role") in ("raw", "boot", "bootstrap_transport")]
base_p, new_p = sys.argv[1], sys.argv[2]
A = json.load(open(base_p)); B = json.load(open(new_p))
ta, tb = tree(A, base_p), tree(B, new_p)
ra = {r["name"]: r for r in start_relays(ta)}; rb = start_relays(tb)
t = B["partition_types"][TN]
pins = {x["name"]: x for x in t["clock"]["landing_contract"]["pins"]}
shared, used = {}, set()
for e in t.get("reset_start_raw_exports", []):
    o = ra[e["instance"]]
    if e["instance"] in shared:
        n = shared[e["instance"]]
    else:
        c = [r for r in rb if r.get("role") == o.get("role") and r.get("depth") == o.get("depth") and r["name"] not in used]
        n = min(c, key=lambda r: math.dist(r["xy"], e["xy_um"])); used.add(n["name"]); shared[e["instance"]] = n
    pn = pins.get(e["port"])
    print("RESEL", e["port"], o["name"], o.get("role"), o.get("depth"), "->", n["name"], n["q"], n["xy"], "dist %.1f" % math.dist(n["xy"], e["xy_um"]))
    if pn is not None:
        off = [pn["xy_um"][0] - e["xy_um"][0], pn["xy_um"][1] - e["xy_um"][1]]
        pn["source_instance"], pn["source_copy_from_net"] = n["name"], n["q"]
        pn["xy_um"] = [round(n["xy"][0] + off[0], 4), round(n["xy"][1] + off[1], 4)]
    e["instance"], e["net"], e["xy_um"] = n["name"], n["q"], list(n["xy"])
ra_q = {r["q"]: r for r in ta["relays"]}; rb_all = tb["relays"]; rb_q = {r["q"]: r for r in rb_all}
clk = t["clock"]; refs = []
for key in ("landing_reader_start", "landing_writer_start"):
    for bus, br in clk.get(key, {}).get("branches", {}).items():
        for i, st in enumerate(br.get("stages", [])):
            refs.append((f"{key}.{bus}.{i}", st, "raw_reset"))
for i, lr in enumerate(clk.get("landing_local_resets", [])):
    refs.append((f"landing_local_resets.{i}", lr, "raw"))
for tag, obj, fld in refs:
    q = obj.get(fld); o = ra_q.get(q)
    if o is None:
        print("RAWSEL skip", tag, q); continue
    pt = obj.get("xy_um") or o["xy"]
    n = min([r for r in rb_all if r.get("depth") == o.get("depth")], key=lambda r: math.dist(r["xy"], pt))
    k = rb_q.get(q)
    if k is not None and k.get("depth") == o.get("depth") and math.dist(k["xy"], pt) <= math.dist(n["xy"], pt) + 25.0:
        continue
    print("RAWSEL", tag, q, "->", n["q"], n["xy"]); obj[fld] = n["q"]
json.dump(B, open(new_p, "w"), indent=1)
