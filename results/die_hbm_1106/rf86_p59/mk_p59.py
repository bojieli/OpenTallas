#!/usr/bin/env python3
"""DIE-HBM-82-RF d44v part 59: ot_svgr_top obs_max M5 -> M6 on its 8 sites (q_hub_nw + q_hub_ne, u_svg_Q0..3__t).
Writes the new plan + a ledger of parent demand on M6 over each site.   mk_p59.py POR_PLAN NEW_PLAN LEDGER"""
import json, sys
por, new, led = sys.argv[1:4]
p = json.load(open(por))
TYPES = ("q_hub_nw", "q_hub_ne"); MOD = "ot_svgr_top"; rows = []; n = 0


def seg_box(a, b, box, pad=0.0):
    x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
    # L route either way: test the bbox of the hop, then report the entry as a candidate
    return min(x1, box[2]) > max(x0, box[0]) - pad and min(y1, box[3]) > max(y0, box[1]) - pad


def crosses(a, b, box):
    # hop must cross the core: both L routes between a and b enter the core box (a Z around it is not assumed)
    def leg(u, v):
        return min(max(u[0], v[0]), box[2]) > max(min(u[0], v[0]), box[0]) - 1e-6 and min(max(u[1], v[1]), box[3]) > max(min(u[1], v[1]), box[1]) - 1e-6
    return (leg(a, (b[0], a[1])) or leg((b[0], a[1]), b)) and (leg(a, (a[0], b[1])) or leg((a[0], b[1]), b))


def inside(q, box):
    return box[0] < q[0] < box[2] and box[1] < q[1] < box[3]


for tn in TYPES:
    t = p["partition_types"][tn]
    for c in t["hard_cores"]:
        if c.get("module") != MOD:
            continue
        assert c.get("obs_max", "M5") == "M5", (tn, c["inst"], c.get("obs_max"))
        c["obs_max"] = "M6"; n += 1
        dx, dy = c.get("track_offset_um", [0, 0])
        box = [c["origin_um"][0] + dx, c["origin_um"][1] + dy, c["origin_um"][0] + dx + c["outline_um"][0], c["origin_um"][1] + dy + c["outline_um"][1]]
        r = {"type": tn, "inst": c["inst"], "bbox_um": box, "orient": c.get("orient"), "ft_slots_over": [], "stations_inside": 0, "clock_points_inside": []}
        for s in t.get("ft_slots", []):
            regs = s.get("regs_um") or []
            hits = [i for i, q in enumerate(regs) if inside(q, box)]
            hops = [i for i in range(len(regs) - 1) if seg_box(regs[i], regs[i + 1], box)]
            if hits or hops:
                r["ft_slots_over"].append({"name": s["name"], "width": s.get("width"), "in_layers": s.get("in_layers"), "out_layers": s.get("out_layers"),
                                           "layers": s.get("layers"), "regs_inside": len(hits), "hops_over": len(hops)})
        r["conns_over"] = []
        for st in t.get("internal_stations", []):
            path = [st["from_um"]] + (st.get("regs_um") or []) + [st["to_um"]]
            r["stations_inside"] += sum(inside(q, box) for q in st.get("regs_um") or [])
            # straight-hop crossing only: an L hop whose bbox touches the core has a route around it
            for a, b in zip(path, path[1:]):
                if seg_box(a, b, box):
                    horiz = abs(a[0] - b[0]) >= abs(a[1] - b[1])
                    r["conns_over"].append({"conn": st["conn"], "bits": st.get("bits"), "hop_um": [a, b], "dir": "H" if horiz else "V", "forced": crosses(a, b, box)})
                    break
        for k in (t.get("clock") or {}).get("taps", []):
            if inside(k["xy"], box):
                r["clock_points_inside"].append([k["name"], k["xy"], k.get("kind")])
        rows.append(r)
assert n == 8, n
open(new, "w").write(json.dumps(p) + "\n")
json.dump({"sites": rows}, open(led, "w"), indent=1)
for r in rows:
    print(r["type"], r["inst"], [round(x, 1) for x in r["bbox_um"]], "ft", [(s["name"], s["width"], s["regs_inside"], s["hops_over"]) for s in r["ft_slots_over"]], "stations", r["stations_inside"], "clk", r["clock_points_inside"][:4], "conns", len(r["conns_over"]), "forced bitsH", sum(q["bits"] or 0 for q in r["conns_over"] if q["forced"] and q["dir"] == "H"), "forced bitsV", sum(q["bits"] or 0 for q in r["conns_over"] if q["forced"] and q["dir"] == "V"))
