#!/usr/bin/env python3
"""DIE-HBM-28: add L202m = NE mirror of L202 (root -> NE_hub -> NE_b000, 180 b scorer prm col_idx -> hb_idx__s_SE input
reg), REMAP class of HBM-004 (DIE-HBM-27 sec. 4).  Same type-frame windows/stations as L202 (MY mirror keeps y of E/W
faces).  Fails closed if any new declaration overlaps an existing one on the same type face.
usage: add_l202m.py TOOLS PLAN_JSON"""
import sys, json, copy
sys.path.insert(0, sys.argv[1])
import schema as S
plan = sys.argv[2]
raw = json.load(open(plan)); T = raw["partition_types"]; pt = {p["name"]: p["type"] for p in raw["partitions"]}
assert not any(l["id"] == "L202m" for l in raw["lanes"]), "L202m exists"
def find(tn, nm, key):
    return next(x for x in T[tn][key] if x["name"] == nm)
root_b = copy.deepcopy(find("root", "L202_o", "buses")); root_b["name"] = "L202m_o"; root_b["face"] = "E"
slot = copy.deepcopy(find(pt["NW_hub"], "L202x1", "ft_slots"))
b0 = copy.deepcopy(find(pt["NW_b000"], "L202_i", "buses"))
def occ(tn, face):
    out = []
    for b in T[tn].get("buses", []):
        if b.get("face") == face and "window_um" in b: out.append((b["name"], b["window_um"]))
    for s in T[tn].get("ft_slots", []):
        for f, w in (("in_face", "in_window_um"), ("out_face", "out_window_um")):
            if s.get(f) == face and w in s: out.append((s["name"], s[w]))
    return out
def clash(tn, face, win):
    return [(n, w) for n, w in occ(tn, face) if w[0] < win[1] and win[0] < w[1]]
errs = []
errs += [("root", "E", c) for c in clash("root", "E", root_b["window_um"])]
for f, w in (("E", slot["in_window_um"]), ("W", slot["out_window_um"])):
    errs += [(pt["NE_hub"], f, c) for c in clash(pt["NE_hub"], f, w) if c[0] != "L202x1"]
errs += [(pt["NE_b000"], "E", c) for c in clash(pt["NE_b000"], "E", b0["window_um"]) if c[0] != "L202_i"]
if errs:
    raise SystemExit(f"window clash: {errs}")
T["root"]["buses"].append(root_b)
if not any(s["name"] == "L202x1" for s in T[pt["NE_hub"]].get("ft_slots", [])):
    T[pt["NE_hub"]].setdefault("ft_slots", []).append(slot)
if not any(b["name"] == "L202_i" for b in T[pt["NE_b000"]]["buses"]):
    T[pt["NE_b000"]]["buses"].append(b0)
raw["ports"] += [dict(id="L202m_0", src=dict(part="root", bus="L202m_o"), dst=dict(part="NE_hub", bus="L202x1_i"), width=180, kind="data"),
                 dict(id="L202m_1", src=dict(part="NE_hub", bus="L202x1_o"), dst=dict(part="NE_b000", bus="L202_i"), width=180, kind="data")]
raw["lanes"].append(dict(id="L202m", ports=["L202m_0", "L202m_1"],
                         note="DIE-HBM-28: NE mirror of L202 (root->NE_hub->NE_b000 180 b scorer prm), HBM-004 REMAP root->NE_b000"))
raw["latency"]["lanes"]["L202m"] = dict(raw["latency"]["lanes"]["L202"], param="LAT_L202M")
P = S.Plan(raw)
for q in ("L202m_0", "L202m_1"):
    pr = next(p for p in raw["ports"] if p["id"] == q)
    print(q, P.port_geom_from(pr, "src"), P.port_geom_from(pr, "dst"))
json.dump(raw, open(plan, "w"), indent=1)
print("L202m added")
