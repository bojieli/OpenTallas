#!/usr/bin/env python3
"""HBM-MU-QUAD-4: re-site root internal stations at u_col_idx after the 108^2 -> 86.4^2 collar re-pack (COORD ruling 1).
Each station end on the collar moves to the centroid of its bus pins on the new pins_r5 faces (die frame, R0); the
register next to the collar moves onto the straight leg toward that pin when needed so every hop stays <= reach.
Register count is preserved (no cycle change).  Usage: resite_collar.py PLAN_DIR [REACH]"""
import json, sys, hashlib, re
from pathlib import Path
pd = Path(sys.argv[1]); reach = float(sys.argv[2]) if len(sys.argv) > 2 else 405.0
P = json.loads((pd / "die_plan.json").read_text()); t = P["partition_types"]["root"]
hc = next(h for h in t["hard_cores"] if h["inst"] == "u_col_idx"); ox, oy = hc["origin_um"]
pins = json.loads((pd / hc["pins_file"]).read_text()); pins = pins.get("pins", pins) if isinstance(pins, dict) else pins
bus = {}
for p in pins:
    bus.setdefault(p.get("bus") or re.sub(r"\[\d+\]$", "", p["name"]), []).append((ox + p["x"], oy + p["y"]))
md = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
rows = []
for e in t.get("internal_stations", []):
    for end, key in (("launch", "from_um"), ("capture", "to_um")):
        v = e.get(end, "")
        if not v.startswith("u_col_idx"):
            continue
        pt = e[key]; W0, H0 = hc["_old"] if "_old" in hc else (108.0, 108.0); W1, H1 = hc["outline_um"]
        in_old = ox - 1 <= pt[0] <= ox + W0 + 1 and oy - 1 <= pt[1] <= oy + H0 + 1
        in_new = ox - 1e-3 <= pt[0] <= ox + W1 + 1e-3 and oy - 1e-3 <= pt[1] <= oy + H1 + 1e-3
        if not in_old:
            continue  # end is a partition-edge bus port, not on the collar
        if in_new:
            rows.append(dict(conn=e.get("conn"), end=end, status="UNCHANGED", pt=pt)); continue
        b = v.split(".", 1)[1] if "." in v else None
        if b is None:  # capture names only the core: bus = conn's launch port? use conn field
            m = re.search(r"\.(\w+)\|u_col_idx$", e.get("conn", ""))
            b = m.group(1) if m else None
        if b in bus:
            xs = bus[b]; new = [round(sum(x for x, _ in xs) / len(xs), 3), round(sum(y for _, y in xs) / len(xs), 3)]
        else:  # port named by its launcher: nearest point of the new box
            new = [round(min(max(pt[0], ox), ox + W1), 3), round(min(max(pt[1], oy), oy + H1), 3)]
        old = e[key]; e[key] = new
        regs = e.get("regs_um", [])
        if regs:
            i = 0 if key == "from_um" else -1
            pts = [e["from_um"]] + regs + [e["to_um"]]
            if max(md(a, c) for a, c in zip(pts, pts[1:])) > reach:
                nb = regs[i + 1] if key == "from_um" and len(regs) > 1 else (regs[i - 1] if len(regs) > 1 else (e["to_um"] if key == "from_um" else e["from_um"]))
                regs[i] = [round((new[0] + nb[0]) / 2, 3), round((new[1] + nb[1]) / 2, 3)]
        pts = [e["from_um"]] + regs + [e["to_um"]]
        mh = max(md(a, c) for a, c in zip(pts, pts[1:]))
        rows.append(dict(conn=e.get("conn"), end=end, bus=b, old=old, new=new, moved_um=round(md(old, new), 2), max_hop=round(mh, 2),
                         status="PASS" if mh <= reach + 1e-6 else "FAIL"))
        e["note"] = (e.get("note", "") + " | HBM-MU-QUAD-4: collar end re-sited on pins_r5 face").strip(" |")
s = json.dumps(P, indent=1) + "\n"; (pd / "die_plan.json").write_text(s)
(pd / "die_plan.sha256").write_text(hashlib.sha256(s.encode()).hexdigest() + "  die_plan.json\n")
(pd / "collar_resite_report.json").write_text(json.dumps(rows, indent=1) + "\n")
import collections
print(dict(collections.Counter(r["status"] for r in rows)), "max_moved", max((r.get("moved_um", 0) for r in rows), default=0),
      "max_hop", max((r.get("max_hop", 0) for r in rows), default=0), hashlib.sha256(s.encode()).hexdigest()[:12])
for r in rows:
    if r["status"] != "PASS": print(r)
