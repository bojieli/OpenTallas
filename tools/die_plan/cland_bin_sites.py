"""cland_bin_sites.py (QC-CB-GEN-1115, COORD 11-15): the opentallas.cland_bin_sites.v1 sidecar generator for the cb landing buses.

A landing ring (band) -> u_bin -> u_st... -> tile tap pin route: F (the bus pin window centre on its face) -> channel row -> margin column
-> tap.  When a band moves (reshape / regrow rows) the u_bin / u_st sites are re-derived here instead of by hand:
  u_bin  one site INSIDE the ring's own band, at the band edge that faces the route (east end if the route runs east, else west end;
         8.64 um in from the edge, channel row nearest the route, 4.32 um grid)
  u_st.. extra FIRM stations, equal hops along the route polyline between fixed points (u_bin, the plan's own internal_stations
         regs_um of that bus, the tap): k = ceil(len / (405 - SLACK)) - 1 per leg, so every hop <= 405 um
  rule   every site on the 4.32 um grid, outside every hard core + halo, outside every OTHER band (+gap) and not on a station site;
         a site that lands on one slides along the route (+- 4.32 um steps) while all its hops stay <= 405 um
Route source, in order: (1) the plan's internal_stations row of the bus (from_um, regs_um, to_um) - those stations are counted first
(plan_stations); (2) the previous sidecar entry of the bus: the margin column x = its u_st.x, the channel row = its u_bin.y, the tap
reconstructed from its route_um with F = the pin window centre.  Band rects come from the plan, overridden by --rows (rows_s4q7.json).
Entry: {u_bin, u_st (first extra, or the plan station), u_st_more [...], route_um, equal_hop_um (the longest hop), hops [...], plan_stations}.
python3 -I tools/die_plan/cland_bin_sites.py PLAN.json OUT.json [--prev SIDECAR.json] [--rows ROWS.json] [--types a,b] [--buses bc_i22,nb_i22]"""
import argparse
import json
import math
import re

GRID = 4.32
HOP = 405.0
SLACK = 5.0
HALO = 4.32
BGAP = 1.08
IN_UM = 8.64


def snap(v):
    return round(round(v / GRID) * GRID, 2)


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def pin_xy(face, win, W, H):
    c = sum(win) / 2.0
    return {"S": (c, 0.0), "N": (c, H), "W": (0.0, c), "E": (W, c)}[face]


def plen(pts):
    return sum(man(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def at(pts, d):
    """point at Manhattan distance d along the polyline"""
    for i in range(len(pts) - 1):
        s = man(pts[i], pts[i + 1])
        if d <= s + 1e-9 and s > 0:
            a, b = pts[i], pts[i + 1]
            f = d / s
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        d -= s
    return pts[-1]


def hit(p, cores, bands, sites):
    x, y = p
    for c in cores:
        if c[0] - HALO < x < c[2] + HALO and c[1] - HALO < y < c[3] + HALO:
            return True
    for b in bands:
        if b[0] - BGAP < x < b[2] + BGAP and b[1] - BGAP < y < b[3] + BGAP:
            return True
    return any(abs(x - s[0]) < 8.64 and abs(y - s[1]) < 8.64 for s in sites)


def legs(fixed, cores, bands, avoid, via=None):
    """fixed: polyline nodes (first = u_bin site) whose consecutive hops may exceed HOP -> (all nodes incl. new stations, hops)"""
    out = [fixed[0]]
    new = []
    for a, b in zip(fixed, fixed[1:]):
        cands = [([a] + list(via) + [b])] if via else ([[a, b]] if (a[0] == b[0] or a[1] == b[1]) else [[a, (b[0], a[1]), b], [a, (a[0], b[1]), b]])
        placed, err = None, None
        for seg in cands:
            L = plen(seg)
            k = max(0, math.ceil(L / (HOP - SLACK)) - 1)
            try:
                placed = _place(seg, L, k, a, b, cores, bands, avoid + new)
                break
            except ValueError as e:
                err = e
        if placed is None:
            raise err
        for p in placed:
            new.append(p)
            out.append(p)
        out.append(b)
    hops = [round(man(out[i], out[i + 1]), 1) for i in range(len(out) - 1)]
    return out, hops


def _place(seg, L, k, a, b, cores, bands, avoid):
    new = []
    if True:
        prev = a
        for j in range(1, k + 1):
            d0 = L * j / (k + 1)
            for step in [0] + [s * n for n in range(1, 41) for s in (1, -1)]:
                dd = d0 + step * GRID
                if dd <= 0 or dd >= L:
                    continue
                p = at(seg, dd)
                p = (snap(p[0]), snap(p[1]))
                if hit(p, cores, bands, avoid + new):
                    continue
                if man(prev, p) <= HOP and (j < k or man(p, b) <= HOP):
                    new.append(p)
                    prev = p
                    break
            else:
                raise ValueError(f"no legal station site on leg {a}->{b} (station {j}/{k})")
    return new


def build(plan, prev, rows, types, buses):
    res = {}
    for tn, t in plan["partition_types"].items():
        if types and tn not in types or not re.match(r"^cb[nfx]_", tn):
            continue
        W, H = t["outline_um"]
        bands = {k: dict(v) for k, v in ((t.get("clock") or {}).get("landing_contract") or {}).get("bands", {}).items() if v.get("rect_um")}
        for key, nb in (rows.get(tn, {}).get("bands") or rows.get(tn) or {}).items():
            if key.startswith("clock.landing_contract.bands."):
                bands[key.rsplit(".", 1)[1]] = nb
        cores = [[h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]]
                 for h in t.get("hard_cores", [])]
        stn = {r["conn"].split(":", 1)[-1]: r for r in t.get("internal_stations") or []}
        allst = [tuple(p) for r in stn.values() for p in r.get("regs_um") or []]
        pv = (prev.get("types") or {}).get(tn) or {}
        for bus in [b for b in t.get("buses", []) if b.get("window_um") and b["name"] in bands]:
            bn = bus["name"]
            if buses and bn not in buses:
                continue
            if bn not in pv and bn not in stn:
                continue
            band = bands[bn]["rect_um"]
            F = pin_xy(bus["face"], bus["window_um"], W, H)
            fixed_tail, plan_n, via = None, 0, None
            if bn in stn:                                           # (1) the plan's own route
                r = stn[bn]
                regs = [tuple(p) for p in r.get("regs_um") or []]
                fixed_tail, plan_n = regs + [tuple(r["to_um"])], len(regs)
                first = regs[0] if regs else tuple(r["to_um"])
                east = first[0] > (band[0] + band[2]) / 2
                ych = snap(min(max(F[1] if bus["face"] in "EW" else 34.56, band[1] + GRID), band[3] - GRID))
            else:                                                   # (2) reconstructed from the previous entry
                e = pv[bn]
                xm, ych0 = e["u_st"][0], e["u_bin"][1]
                east = xm > F[0]
                core = next((c for c in cores if c[2] + 1 > xm - 120 and c[2] - 1 < xm), None) or max(cores, key=lambda c: c[2])
                xt = core[2] if east else core[0]
                rest = e["route_um"] - (abs(F[1] - ych0) + abs(F[0] - e["u_bin"][0])) - man(e["u_bin"], e["u_st"])
                dx = abs(xm - xt)
                yt = e["u_st"][1] + max(0.0, rest - dx)
                fixed_tail = [(xt, snap(yt))]
                via = [(xm, ych0), (xm, snap(yt))]
                ych = snap(min(max(ych0, band[1] + GRID), band[3] - GRID))
            others = [b["rect_um"] for k, b in bands.items() if k != bn]
            cands = []
            for dx in range(0, int((band[2] - band[0]) / GRID)):                 # inside the own band, from the edge facing the route
                ubx = snap((band[2] - IN_UM - dx * GRID) if east else (band[0] + IN_UM + dx * GRID))
                for dy in [0] + [s_ * n_ for n_ in range(1, 40) for s_ in (1, -1)]:
                    cy = snap(ych + dy * GRID)
                    if band[1] + GRID <= cy <= band[3] - GRID and band[0] <= ubx <= band[2] and not hit((ubx, cy), cores, others, allst) \
                            and man(F, (ubx, cy)) <= HOP:
                        cands.append(((ubx, cy), False))
            if not cands:                                          # e.g. the band rect is a hard-core ring macro: legal sites within 40 um of it
                box = [band[0] - 40, band[1] - 40, band[2] + 40, band[3] + 40]
                out_c = []
                for ix in range(int(box[0] / GRID), int(box[2] / GRID) + 1):
                    for iy in range(int(max(box[1], 17.28) / GRID), int(box[3] / GRID) + 1):
                        c = (snap(ix * GRID), snap(iy * GRID))
                        if c[1] < 17.28 or hit(c, cores, others, allst) or man(F, c) > HOP:
                            continue
                        d = max(band[0] - c[0], 0, c[0] - band[2]) + max(band[1] - c[1], 0, c[1] - band[3])
                        out_c.append(((d, abs(c[1] - ych), abs(c[0] - (band[2] if east else band[0]))), c))
                cands = [(c, True) for _, c in sorted(out_c)]
            if not cands:
                raise ValueError(f"{tn}.{bn}: no legal u_bin site inside or within 40 um of the band {band}")
            last = None
            for u_bin, outside in cands[:80]:
                try:
                    hop0 = man(F, u_bin)
                    nodes = [u_bin] + fixed_tail
                    allnodes, hops = legs(nodes, cores, others, allst + [u_bin], via)
                    break
                except ValueError as e:
                    last = e
            else:
                raise ValueError(f"{tn}.{bn}: no u_bin candidate gives a legal route: {last}")
            sts = [p for p in allnodes[1:-1]]
            ent = dict(u_bin=list(u_bin), u_st=list(sts[0]) if sts else list(allnodes[-1]), route_um=round(hop0 + plen(allnodes), 1),
                       equal_hop_um=round(max([hop0] + hops), 1), hops=[round(hop0, 1)] + hops, plan_stations=plan_n)
            if outside:
                ent["u_bin_outside_band"] = True
            if len(sts) > 1:
                ent["u_st_more"] = [list(p) for p in sts[1:]]
            res.setdefault(tn, {})[bn] = ent
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--prev", default="")
    ap.add_argument("--rows", default="")
    ap.add_argument("--types", default="")
    ap.add_argument("--buses", default="")
    a = ap.parse_args(argv)
    plan = json.load(open(a.plan))
    prev = json.load(open(a.prev)) if a.prev else {}
    rows = json.load(open(a.rows)) if a.rows else {}
    res = build(plan, prev, rows, set(filter(None, a.types.split(","))), set(filter(None, a.buses.split(","))))
    doc = dict(schema="opentallas.cland_bin_sites.v1", frame="partition type um", types=res,
               rule="ring -> u_bin (inside its own band, at the edge facing the route) -> u_st.. -> tile tap pin: equal-hop sites on the route; plan stations already on the bus are counted first; every hop <= 405 um (tools/die_plan/cland_bin_sites.py)")
    json.dump(doc, open(a.out, "w"), indent=1)
    for tn, d in res.items():
        for bn, e in d.items():
            print(tn, bn, e["u_bin"], e["u_st"], e.get("u_st_more", ""), "hops", e["hops"])


if __name__ == "__main__":
    main()
