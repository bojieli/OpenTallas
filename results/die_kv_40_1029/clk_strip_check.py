# DIE-KV-40 die clock check for the event28w q1/q2 widen-east delta: the die clock of record (tree c, kit_e26a/clock,
# ot_clk kv_e26a) must not place any die clock cell or tap inside the two growth strips in any hg instance (they become
# hard-core OBS M1-M5), and the q1/q2 core clock taps (ectl_q*.ck[0]) must be unchanged and inside the new outline.
import json, sys
sys.path.insert(0, "tools/die_plan")
import schema
old = schema.Plan(json.load(open(sys.argv[1]))); new = schema.Plan(json.load(open(sys.argv[2])))
tree = json.load(open(sys.argv[3]))
res = dict(instances=0, strips=[], cells_in_strip=[], taps_in_strip=[], cells_in_new_core=0)
for n, p in new.parts.items():
    t = new.types[p["type"]]
    for h in t.get("hard_cores", []) or []:
        if h["module"] not in ("qkd_ectlk_q1", "qkd_ectlk_q2"): continue
        ho = next(g for g in old.types[p["type"]]["hard_cores"] if g["inst"] == h["inst"])
        assert ho["origin_um"] == h["origin_um"]
        x0, y0 = h["origin_um"]; xo1 = x0 + ho["outline_um"][0]; xn1 = x0 + h["outline_um"][0]; y1 = y0 + h["outline_um"][1]
        def die_rect(a, b, c, d):
            pts = [new.to_die(n, (a, b)), new.to_die(n, (c, d))]
            return (min(q[0] for q in pts), min(q[1] for q in pts), max(q[0] for q in pts), max(q[1] for q in pts))
        s = die_rect(xo1, y0, xn1, y1); core = die_rect(x0, y0, xn1, y1)
        res["instances"] += 1; res["strips"].append([n, h["inst"], [round(v, 3) for v in s]])
        inside = lambda xy, r: r[0] <= xy[0] <= r[2] and r[1] <= xy[1] <= r[3]
        for c, xy in tree["sites"].items():
            if inside(xy, s): res["cells_in_strip"].append([n, h["inst"], c, xy])
            if inside(xy, core): res["cells_in_new_core"] += 1
        for tp in tree["taps"]:
            if inside(tp["xy"], s): res["taps_in_strip"].append([n, h["inst"], tp["port"], tp["xy"]])
taps_old = {tn: [tp for tp in t.get("clock", {}).get("taps", [])] for tn, t in old.types.items()}
taps_new = {tn: [tp for tp in t.get("clock", {}).get("taps", [])] for tn, t in new.types.items()}
res["type_clock_taps_identical"] = taps_old == taps_new
res["die_clock_section_identical"] = old.raw["clock"] == new.raw["clock"] if hasattr(old, "raw") else None
res["ck0_inside_new_outline"] = all(
    h["origin_um"][0] < tp["xy"][0] < h["origin_um"][0] + h["outline_um"][0]
    for t in new.types.values() for tp in t.get("clock", {}).get("taps", []) if tp["name"].startswith("ectl_q1.") or tp["name"].startswith("ectl_q2.")
    for h in t["hard_cores"] if h["inst"] == tp["name"].split(".")[0])
print(json.dumps({k: (v if k != "strips" else v[:2]) for k, v in res.items()}, indent=0)[:3000])
json.dump(res, open(sys.argv[4], "w"), indent=1)
