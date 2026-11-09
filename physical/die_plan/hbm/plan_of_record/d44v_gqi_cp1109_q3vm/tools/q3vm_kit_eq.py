import json, sys, hashlib
INSET = 0.096
SHIFT = {"W": (INSET, 0.0), "E": (-INSET, 0.0), "S": (0.0, INSET), "N": (0.0, -INSET)}
def kname(x): return x["bus"] if x.get("bit") is None else f"{x['bus']}[{x['bit']}]"
def to_plan(k):
    dx, dy = (0.0, 0.0) if k.get("entry") or k.get("face") not in SHIFT else SHIFT[k["face"]]
    out = dict(name=kname(k), layer=k["layer"], x=round(k["x"] + dx, 3), y=round(k["y"] + dy, 3))
    for a in ("w", "h"):
        if a in k: out[a] = k[a]
    return out
kit = json.load(open(sys.argv[1])); tab = json.load(open(sys.argv[2]))
new = {p["name"]: p for p in map(to_plan, kit)}
old = {p["name"]: p for p in tab}
assert len(new) == len(kit) and len(old) == len(tab)
print("names kit", len(new), "table", len(old), "same set", set(new) == set(old))
def norm(p): return (p["layer"], round(p["x"], 3), round(p["y"], 3), p.get("w"), p.get("h"))
diff = [n for n in old if n in new and norm(new[n]) != norm(old[n])]
lay = [n for n in diff if new[n]["layer"] != old[n]["layer"]]
xy = [n for n in diff if (new[n]["layer"], round(new[n]["x"],3), round(new[n]["y"],3)) != (old[n]["layer"], round(old[n]["x"],3), round(old[n]["y"],3))]
print("diff", len(diff), "layer", len(lay), "xy", len(xy))
for n in diff[:8]: print(" ", n, new[n], old[n])
print("clk kit->plan", new.get("clk"), "table", old.get("clk"))
