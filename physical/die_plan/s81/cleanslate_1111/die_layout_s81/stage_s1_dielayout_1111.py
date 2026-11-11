"""DIE-LAYOUT-S81 S1 stage (DO_NOT_COUNT): (A) station-column margin slide; (C) svc ft re-site, re-legalised on the current
svc_rs cores (positions only: regs_um / bit_sites_um; station counts asserted).  usage: in out report delta.json"""
import json, sys
src, out, rep, dpath = sys.argv[1:5]
P = json.load(open(src)); D = json.load(open(dpath)); T = P["partition_types"]
R = {"slide": {}, "resite_applied": [], "resite_skipped": []}
for p in P["partitions"]:
    dy = D["slide"].get(p["name"])
    if dy:
        y0 = p["origin_um"][1]; p["origin_um"][1] = round(y0 + dy, 4); R["slide"][p["name"]] = [y0, p["origin_um"][1]]
assert len(R["slide"]) == len(D["slide"]), R["slide"]
# die channels: the slid station splits its declared svcband gap in two; keep one declared channel per gap
PT = {q["name"]: q for q in P["partitions"]}
top = lambda m: m["origin_um"][1] + T[m["type"]]["outline_um"][1]
chans = P["die"]["channels"]; R["channels"] = []
for n, dy in D["slide"].items():
    q = PT[n]; x, y = q["origin_um"]
    col = [m for m in P["partitions"] if abs(m["origin_um"][0] - x) < 0.1 and m["name"] != n]
    bl = max([m for m in col if m["origin_um"][1] < y], key=lambda m: m["origin_um"][1])
    ab = min([m for m in col if m["origin_um"][1] > y], key=lambda m: m["origin_um"][1])
    up = [c for c in chans if c.get("between") == [n, ab["name"]]]
    assert len(up) == 1, (n, ab["name"])
    up[0]["width_um"] = round(ab["origin_um"][1] - top(q), 4)
    gap_dn = round(y - top(bl), 4)
    ports = [po["id"] for po in P["ports"] if {po["src"].get("part"), po["dst"].get("part")} == {n, bl["name"]}]
    new = {"name": f"svcband_{bl['name']}__{n}", "between": [bl["name"], n], "ports": ports, "width_um": gap_dn,
           "layers": list(up[0].get("layers") or ["M7", "M5", "M3"]),
           "reason": f"DIE-LAYOUT-S81 11-11 S1 margin slide: {n} +{dy} um splits the svc band gap ({up[0]['name']}) into {gap_dn} + {up[0]['width_um']} um"}
    chans.append(new); R["channels"].append([up[0]["name"], up[0]["width_um"], new["name"], gap_dn, len(ports)])

def inside(x, y, rects, m=0.5):
    return any(a + m < x < c - m and b + m < y < d - m for a, b, c, d in rects)

for t, slots in D["types"].items():
    ty = T.get(t)
    if not ty:
        R["resite_skipped"].append([t, "*", "type missing"]); continue
    rects = [(h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1])
             for h in ty.get("hard_cores", [])]
    rects += [(c["origin_um"][0], c["origin_um"][1], c["origin_um"][0] + c["outline_um"][0], c["origin_um"][1] + c["outline_um"][1])
              for c in ty.get("contents", []) if c.get("origin_um") and c.get("outline_um")]
    by = {f["name"]: f for f in ty.get("ft_slots", [])}
    for sn, upd in slots.items():
        f = by.get(sn)
        if not f:
            R["resite_skipped"].append([t, sn, "slot missing after revert"]); continue
        if len(f.get("regs_um") or []) != len(upd["regs_um"]):
            R["resite_skipped"].append([t, sn, f"reg count {len(f.get('regs_um') or [])} != {len(upd['regs_um'])}"]); continue
        regs = [list(r) for r in upd["regs_um"]]
        snapped = []
        W, H = ty["outline_um"]
        for k in range(1, len(regs) - 1):
            x, y = regs[k][0], regs[k][1]
            hit = [q for q in rects if q[0] + 0.5 < x < q[2] - 0.5 and q[1] + 0.5 < y < q[3] - 0.5]
            if not hit:
                continue
            a, b, c, d = hit[0]
            cands = [(a - 2.16, y), (c + 2.16, y), (x, b - 2.16), (x, d + 2.16)]
            cands = [p for p in cands if 1 < p[0] < W - 1 and 1 < p[1] < H - 1 and not inside(p[0], p[1], rects)]
            if not cands:
                snapped = None; break
            p = min(cands, key=lambda p: abs(p[0] - x) + abs(p[1] - y))
            snapped.append([k, [round(x, 3), round(y, 3)], [round(p[0], 3), round(p[1], 3)]])
            regs[k][0], regs[k][1] = round(p[0], 3), round(p[1], 3)
        if snapped is None:
            R["resite_skipped"].append([t, sn, "no legal street point next to a reg"]); continue
        bs_ok = True
        if "bit_sites_um" in upd:
            cw, chh = (f.get("bit_site_cell_um") or upd.get("bit_site_cell_um") or [1.404, 0.27])[:2]
            tmp = json.loads(json.dumps(upd["bit_sites_um"]))
            for k, o, n in snapped:
                if 0 <= k - 1 < len(tmp):
                    tmp[k - 1] = [[p[0] + n[0] - o[0], p[1] + n[1] - o[1]] for p in tmp[k - 1]]
            hits = sum(1 for g in tmp for p in g if any(a < p[0] + cw and p[0] < c and b < p[1] + chh and p[1] < d for a, b, c, d in rects))
            if hits:
                R["resite_skipped"].append([t, sn, f"{hits} bit sites intersect macros on the current cores"]); continue
        f["regs_um"] = regs
        if "bit_sites_um" in upd:
            bs = json.loads(json.dumps(upd["bit_sites_um"]))
            for k, o, n in snapped:          # bit_sites_um[k-1] belongs to station k (check.py): move it with its reg
                dx, dy = n[0] - o[0], n[1] - o[1]
                if 0 <= k - 1 < len(bs):
                    bs[k - 1] = [[round(p[0] + dx, 3), round(p[1] + dy, 3)] for p in bs[k - 1]]
            f["bit_sites_um"] = bs
        hop = lambda rr: max((abs(rr[i+1][0]-rr[i][0]) + abs(rr[i+1][1]-rr[i][1]) for i in range(len(rr)-1)), default=0)
        R["resite_applied"].append([t, sn, snapped, round(hop(upd["regs_um"]), 1), round(hop(regs), 1)])
json.dump(P, open(out, "w"))
json.dump(R, open(rep, "w"), indent=1)
print(f"slide {len(R['slide'])}; resite applied {len(R['resite_applied'])} skipped {len(R['resite_skipped'])}")
