import json, sys, collections
sys.path.insert(0, sys.argv[4])
import schema as S
old = json.load(open(sys.argv[1] + "/mesh.json")); new_place = json.load(open(sys.argv[2] + "/place.json"))
old_place = json.load(open(sys.argv[1] + "/place.json"))
raw = json.load(open(sys.argv[3])); P = S.Plan(raw)
ids_new = {x["name"] for x in json.load(open(sys.argv[2] + "/mesh.json"))["pushdown"]}
mod = {}
gone = [x for x in old["pushdown"] if x["name"] not in ids_new]
rects = {n: P.rect(n) for n in P.parts}
def part_at(x, y):
    for n, r in rects.items():
        if r[0] <= x < r[2] and r[1] <= y < r[3]:
            return n
def core_at(part, x, y):
    t = P.ptype(part); lx, ly = P.to_type(part, (x, y))
    for h in t.get("hard_cores", []) or []:
        ox, oy = h["origin_um"]; w, hh = h["outline_um"]
        if ox <= lx < ox + w and oy <= ly < oy + hh:
            return h["inst"], h["module"], (round(lx - ox, 3), round(ly - oy, 3))
    return None, None, None
pat = collections.Counter(); rows = []
for x in gone:
    n = x["name"]
    c = new_place[n]; o = old_place[n]
    pn = part_at(c["x"], c["y"])
    inst, m, loc = core_at(pn, c["x"], c["y"])
    lx, ly = P.to_type(pn, (c["x"], c["y"]))
    rows.append(dict(name=n, level=x["level"], old_xy=[o["x"], o["y"]], new_xy=[c["x"], c["y"]], part=pn,
                     type=P.parts[pn]["type"], type_xy=[round(lx, 3), round(ly, 3)], in_core=inst,
                     moved_um=round(abs(c["x"] - o["x"]) + abs(c["y"] - o["y"]), 3), old_core=x["core"]))
    pat[(x["level"], P.parts[pn]["type"] == P.parts[x["core"].split("/")[0]]["type"], inst is None, rows[-1]["moved_um"])] += 1
print(json.dumps({str(k): v for k, v in pat.items()}))
tp = collections.Counter((r["level"], r["type"], tuple(r["type_xy"])) for r in rows)
print(len(tp), list(tp.items())[:12])
json.dump(rows, open(sys.argv[5], "w"), indent=0)
