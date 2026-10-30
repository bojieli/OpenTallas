"""DIE-QC-47 geometry census of a die clock tree.json: reach (cell-to-parent Manhattan), site lattice, and every clock
cell inside a native PHY body (die_io PHY windows of the Codex census + every type clock.keepouts_um in the die frame)."""
import hashlib, json, sys
from pathlib import Path
tree, plan, census, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
t = json.loads(tree.read_text()); sites = t["sites"]
P = json.loads(plan.read_text()); T = P["partition_types"]
rows = [(sum(abs(x - y) for x, y in zip(sites[c], sites[pa])), pa, c) for c, pa in t["parent_of"].items()]
offx = [k for k, xy in sites.items() if abs(xy[0] / .054 - round(xy[0] / .054)) > 1e-5]
offy = [k for k, xy in sites.items() if abs(xy[1] / .54 - round(xy[1] / .54)) > 1e-5]
def to_die(p, x, y):
    w, h = T[p["type"]]["outline_um"]; o = p.get("orient", "R0")
    if o in ("MX", "R180"): y = h - y
    if o in ("MY", "R180"): x = w - x
    return p["origin_um"][0] + x, p["origin_um"][1] + y
boxes = {}
for p in P["partitions"]:
    for k, (a, b, c, d) in enumerate((T[p["type"]].get("clock", {}) or {}).get("keepouts_um", []) or []):
        (x0, y0), (x1, y1) = to_die(p, a, b), to_die(p, c, d)
        boxes[f"{p['name']}#keepout{k}"] = (min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
for n, w in json.loads(census.read_text())["windows"].items():
    boxes[f"{n}#census_window"] = tuple(w["rect_um"])
inside = {n: {c: xy for c, xy in sites.items() if r[0] < xy[0] < r[2] and r[1] < xy[1] < r[3]} for n, r in boxes.items()}
rec = dict(tree=str(tree), tree_sha256=hashlib.sha256(tree.read_bytes()).hexdigest(), plan_sha256=hashlib.sha256(plan.read_bytes()).hexdigest(),
           clock_cells=len(sites), edges=len(rows), max_edge_um=max(r[0] for r in rows),
           over400=sum(r[0] > 400 + 1e-6 for r in rows), over405=sum(r[0] > 405 + 1e-6 for r in rows),
           off_54nm_x=len(offx), off_540nm_y=len(offy), longest=sorted(rows, reverse=True)[:10],
           phy_body_boxes={n: list(r) for n, r in boxes.items()},
           inside_phy_body={n: len(v) for n, v in inside.items()}, inside_examples={n: dict(list(v.items())[:5]) for n, v in inside.items() if v},
           taps=len(t.get("taps", {})), nodes=len(t.get("nodes", {})))
rec["verdict_phy_interior"] = "PASS" if not any(inside.values()) else "FAIL"
out.write_text(json.dumps(rec, indent=1) + "\n")
print(json.dumps({k: v for k, v in rec.items() if k not in ("phy_body_boxes", "longest")}, indent=1))
