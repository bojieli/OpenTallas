"""cb_rows_s4q7.py (QC-CB-GEN-1115, FABLE-PD-QC-1545 F4 + F6b): rows for the next QC event, from a plan.
 (b) SW-corner clump (na_i22 + bc_i22 stacked in the W strip, nb_i22 a sliver in the S strip): one ring per strip -
     na_i22 alone in the W strip (its x extent kept, y from the strip foot to the core-free top), bc_i22 in the S strip under its own pins
     (x from the core W edge to the pin window end + SLACK), nb_i22 in the S strip east of bc_i22 up to the core E edge; rects are the
     strip rows (y 17.28 .. core bottom - HALO), checked against every other band and hard core; density reported (target 0.45..0.6).
 (c) a bus station row whose hops exceed 405 um (cbf_q00_s2 bc_i10: 1 station, hops 1022 um): equal-hop stations on the plan's own route
     polyline, snapped to the 4.32 um row grid.  Rows only; the lane fixed_cycles bump (+ added stations) is the owner's gen.py latency step.
usage: cb_rows_s4q7.py PLAN.json OUT.json [CLAND_BIN_SITES.json]"""
import json, math, re, sys

DENS_NA = 0.5; MIN_HOP = 600.0; G = 2.16; EDGE = 17.28; HALO = 4.32; HOP = 405.0; GRID = 4.32
FPB = 5400 / 576.0


def ov(a, b, g=1.5):
    return min(a[2], b[2]) + g > max(a[0], b[0]) and min(a[3], b[3]) + g > max(a[1], b[1])


def grid(v, lo=True):
    return (math.floor if lo else math.ceil)(v / G - 1e-9) * G


def reshape(t, tn):
    bands = t["clock"]["landing_contract"]["bands"]
    if not all(k in bands for k in ("na_i22", "bc_i22", "nb_i22")):
        return None
    cores = [[h["origin_um"][0], h["origin_um"][1], h["origin_um"][0] + h["outline_um"][0], h["origin_um"][1] + h["outline_um"][1]]
             for h in t.get("hard_cores", [])]
    W, H = t["outline_um"]
    c0 = min(cores, key=lambda c: (c[1], c[0]))          # the SW core (u_t22)
    win = {b["name"]: b["window_um"] for b in t["buses"] if b["name"] in ("na_i22", "bc_i22", "nb_i22")}
    top = grid(c0[1] - HALO, True)                       # strip top: core bottom minus halo
    lw = grid(c0[0] - HALO, True)                        # W strip right edge
    new = {}
    wa = lw - (EDGE + 2.16)
    ha = grid(bands["na_i22"]["ring_width"] * FPB / DENS_NA / wa, False) + G         # W strip, as deep as DENS_NA needs
    new["na_i22"] = [EDGE + 2.16, EDGE, lw, EDGE + ha]
    # S strip: bc under its own pin window plus slack, nb east of it
    bc_x1 = grid(max(win["bc_i22"][1] + 106.0, c0[0] + 190.0), False)
    new["bc_i22"] = [grid(c0[0], True), EDGE, bc_x1, top]
    new["nb_i22"] = [bc_x1 + G, EDGE, grid(c0[2], True), top]
    others = [v["rect_um"] for k, v in bands.items() if k not in new and v.get("rect_um")] + cores
    rows, rep = {}, []
    for k, r in new.items():
        if any(ov(r, o) for o in others) or any(ov(r, new[j]) for j in new if j != k):
            rep.append((tn, k, "OVERLAP", [round(v, 3) for v in r])); continue
        px = sum(win[k]) / 2.0
        hop = max(abs(x - px) + abs(y) for x in (r[0], r[2]) for y in (r[1], r[3]))
        # the W-strip ring's pins are on the S face at x 4.3-93: hop to the far corner of the W strip column
        area = (r[2] - r[0]) * (r[3] - r[1])
        nb = dict(bands[k]); nb["rect_um"] = [round(v, 6) for v in r]; nb["area_reserve_um2"] = round(area, 3)
        nb["resized_from_um"] = list(bands[k]["rect_um"]); nb["max_pin_to_band_hop_um"] = round(hop, 3)
        nb["resize"] = "QC-CB-GEN-1115 one ring per strip (FABLE-PD-QC-1545 F4)"
        rows[f"clock.landing_contract.bands.{k}"] = nb
        rep.append((tn, k, [round(v, 2) for v in r], round(area), round(bands[k]["ring_width"] * FPB / area, 2), round(hop)))
    return rows, rep


def stations(t, tn, side):
    out = []
    split = (side.get("types", {}).get(tn) or {})
    for r in t.get("internal_stations") or []:
        hops = re.search(r"hops \[([\d., ]+)\]", r.get("note", ""))
        if not hops or not r["conn"].startswith("bus:"):
            continue
        h = [float(x) for x in hops.group(1).split(",")]
        if max(h) < MIN_HOP or r["conn"].split(":", 1)[1] in split:   # hop 405-600 um: baseline ledger; sidecar u_bin already splits the rest
            continue
        # the route: from -> (via the station column x) -> to, vertical first (the plan's E/W-margin / middle-channel route)
        (fx, fy), (tx, ty) = r["from_um"], r["to_um"]
        sx = r["regs_um"][0][0] if r.get("regs_um") else fx
        pts = [(fx, fy), (sx, fy), (sx, ty), (tx, ty)]
        seg = [abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(3)]
        L = sum(seg)
        n = math.ceil(L / (HOP - 5)) - 1
        regs = []
        for k in range(1, n + 1):
            d = L * k / (n + 1); i = 0
            while d > seg[i] + 1e-9: d -= seg[i]; i += 1
            a, b = pts[i], pts[i + 1]; f = d / seg[i] if seg[i] else 0
            x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
            regs.append([round(round(x / GRID) * GRID, 2) if abs(x - sx) > 1e-6 else sx, round(round(y / GRID) * GRID, 2)])
        nr = dict(r); nr["regs_um"] = regs
        nr["note"] = f"QC-CB-GEN-1115 (FABLE-PD-QC-1545 F6b): {len(r.get('regs_um') or [])} -> {n} station(s) on the {L:.0f} um route, equal hops {L / (n + 1):.0f} um; lane fixed_cycles +{n - len(r.get('regs_um') or [])}"
        out.append((r["conn"], nr, len(r.get("regs_um") or []), n, round(L / (n + 1))))
    return out


if __name__ == "__main__":
    plan = json.load(open(sys.argv[1])); res = {}; rep = []
    side = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
    for tn, t in plan["partition_types"].items():
        if not re.match(r"^cb[nfx]_", tn):
            continue
        rs = reshape(t, tn)
        if rs and rs[0]:
            res.setdefault(tn, {})["bands"] = rs[0]; rep += rs[1]
        elif rs:
            rep += rs[1]
        for conn, nr, n0, n1, hop in stations(t, tn, side):
            res.setdefault(tn, {}).setdefault("stations", {})[conn] = nr
            rep.append((tn, conn, f"stations {n0}->{n1}", f"hop {hop}"))
    json.dump(res, open(sys.argv[2], "w"), indent=1)
    for r in rep: print(r)
