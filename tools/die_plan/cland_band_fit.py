#!/usr/bin/env python3
"""DIE-KV-80/PLAN 11-05 CLAND-BAND class fix (COORD 19:37 (3a)): a clock-landing ring band must hold >= 1.25 x its
ring reserve in free rows.

Failure (KV kv3_hub_Eo a6, kv3_hub_Wo a8, 3_3 place): 'u_cland_monitor_0 (ring:monitor_0): 361 cells reserve 120.5 um2
> band upper bound 60.7 / 54.6 um2'.  The band is not small (25.92 x 8.64 = 224 um2): a later kv3_astk outline put
the hard core over it, leaving a 5.8 / 6.5 um strip of rows.  The planner sizes bands once (_storage_band) and later
core moves / regrows never re-check them; DIE-KV-64's band grow also skips monitor_ bands.

Rule (die-agnostic, any plan): a single-rect band that a placed macro overlaps (placement_boxes, no halo: the kit cuts
rows at the macro edge, which is the 'band upper bound' landing_placement.tcl checks) and whose macro-free area is
below FACTOR x reserve is re-sited.  reserve = measured ring reserve (--reserve TSV: type, bus, um2) or the KV-measured
envelope 7.25 * width + 125 um2 (DIE-KV-64, 1,040 bands).  The new rect keeps the band's size (grown along x only
if FACTOR x reserve exceeds it), moves by the least Manhattan shift to a spot clear of every planning obstacle (macros
+ reset clearance, clock keepouts, other bands, ft station sites, die islands / clock reserved sites, PHY supply,
reset relay / start / status groups), inside the 17.28-um margin, row/site aligned, with pin hop <= 402.84 um.
Bands no macro overlaps are reported, never moved, so the event moves only broken bands.

DIE-QC-97 11-11 HARD-CHILD band (QC cbn_q00__cl622f65d2 / __cldbcda913: 10 bands "macro-free 0.0 um2"): a band with
"hard_core" (QC-SLECTL-B, RING-SPLIT-1106) is the footprint of the hard cland child that implements the ring; the ring
cells live inside that child, not in rows under it.  face-home (clock_landing_plan) and landing_place already skip such
bands; this check counted the child as the macro that blocks its own band.  A hard-child band is never moved; it is
checked instead: the child is placed, its box equals the band (<= HARD_TOL_UM, the track offset), no other macro
overlaps it, and its pin hop is <= REACH.  Any miss is a failure.  Kept in rep["hard_child"].

DIE-QC-97 11-11 ROW-CUT set (QC coll_core / coll_s: 10 bands "macro-free 0.0 / 1351.9 um2" under u_coll_face_p /
u_coll_face_s2): the band blocker set is the set the kit cuts rows at, schema.placed_macro_boxes (hard cores, LEF-bearing
contents and their physical parts).  placement_boxes also adds probe blockages for content leaves WITHOUT a LEF
(qfd_coll_static_face: no LEF, built flat, coll_s a19 placed all 2886 rec_tx_s1_i ring flops FIRM in the "blocked" band
and routed); those are planning obstacles of a re-site (obstacles()), not row cuts.  A leaf that becomes a hard core or
gets a LEF is in the set again by construction.
usage: cland_band_fit.py PLAN SIDECAR OUT_PLAN REPORT [--types REGEX] [--reserve TSV] [--factor 1.25] [--check]
"""
import argparse, copy, json, re, sys
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parents[1]))
import clock_landing_plan as C  # noqa: E402
import reset_tree as RT  # noqa: E402
import schema as S  # noqa: E402
import landing_place as LP  # noqa: E402
from placement_obstacles import placement_boxes  # noqa: E402

A_W, B_0 = 7.25, 125.0           # DIE-KV-64 measured ring reserve envelope (um2 = A_W * width + B_0)
MARGIN, REACH = 17.28, 405 - 2.16
INSET, ROW, SITE = 4.32, 0.27, 0.054
HARD_TOL_UM = 0.05               # hard child box vs band rect: the child track offset (12 nm on QC) stays inside


def model_reserve(w):
    return A_W * float(w) + B_0


def area(r):
    return (r[2] - r[0]) * (r[3] - r[1])


def ov(a, o):
    return min(a[2], o[2]) > max(a[0], o[0]) + 1e-6 and min(a[3], o[3]) > max(a[1], o[1]) + 1e-6


def free_area(r, boxes, step=ROW):
    """Area of r not covered by the union of boxes (raster at one row pitch)."""
    nx, ny = max(1, int(round((r[2] - r[0]) / step))), max(1, int(round((r[3] - r[1]) / step)))
    X, Y = np.meshgrid(r[0] + (np.arange(nx) + .5) * (r[2] - r[0]) / nx, r[1] + (np.arange(ny) + .5) * (r[3] - r[1]) / ny)
    m = np.zeros(X.shape, bool)
    for o in boxes:
        m |= (X > o[0]) & (X < o[2]) & (Y > o[1]) & (Y < o[3])
    return float((~m).mean() * area(r))


def obstacles(t, tn, plan_obj, side, lc, skip):
    """The planning obstacle union (same set as the KV-64 band grow); clock keepouts that are the bands themselves
    (kv3_pv_v8 pvband form) are not obstacles of a band."""
    ck = t.get("clock") or {}
    own = [tuple(o["rect_um"]) for o in lc.get("bands", {}).values() if o.get("rect_um")]
    obs = [list(r) for r in placement_boxes(t, halo=RT.CLEAR_UM).values()]
    halo = max(RT.CLEAR_UM, 8.64)
    obs += [[x0 - halo, y0 - halo, x1 + halo, y1 + halo] for x0, y0, x1, y1 in ck.get("keepouts_um", [])
            if (x0, y0, x1, y1) not in own and [x0, y0, x1, y1] not in [list(o) for o in own]]
    obs += [list(r) for k, o in lc.get("bands", {}).items() if k != skip and o.get("rect_um")
            for r in (o.get("rects_um") or [o["rect_um"]])]
    obs += [list(r) for r in ck.get("die_islands_um", [])]
    obs += [list(r["rect_um"]) for r in ck.get("reserved_sites_um", []) if r.get("kind") == "die_clock_tree"]
    for slot in t.get("ft_slots", []):
        cell = slot.get("bit_site_cell_um", [1.404, .27])
        for st in slot.get("bit_sites_um", []) or []:
            if st:
                obs.append([min(p[0] for p in st) - cell[0] / 2, min(p[1] for p in st) - cell[1] / 2,
                            max(p[0] for p in st) + cell[0] * 1.5, max(p[1] for p in st) + cell[1] * 1.5])
        if not slot.get("bit_sites_um"):
            obs += [[x - 2.16, y - 2.16, x + 2.16, y + 2.16] for x, y in slot.get("regs_um", []) or []]
    if plan_obj is not None:
        obs += C.phy_supply_rects(plan_obj, tn)
    obs += C.reset_site_rects(lc.get("collector_tree"))
    if side is not None:
        obs += C.reset_site_rects((((side.get("collector") or {}).get("types") or {}).get(tn) or {}).get("tree"))
    obs += [list(r) for _p, r, _t in LP._reader_start_groups(t) + LP._writer_start_groups(t) + LP._status_reset_groups(t)]
    obs += [list(r) for r in lc.get("group_rects_um", {}).values()]
    return obs


def pin_xy(t, lc, bus):
    """Landing pin of a band: the data bus face window, else the monitor's cland_dn_ready_<i> pin, else None."""
    try:
        return tuple(C._bus_xy(t, bus))
    except Exception:
        pass
    m = re.match(r"monitor_(\d+)$", bus)
    names = {bus} | ({f"cland_dn_ready_{m.group(1)}"} if m else set())
    for p in lc.get("pins", []) or []:
        if p.get("name") in names and p.get("xy_um"):
            return tuple(p["xy_um"])
    return None


def hop(r, p):
    return max(abs(x - p[0]) + abs(y - p[1]) for x in (r[0], r[2]) for y in (r[1], r[3]))


def resite(r, tgt, W, H, obs, pxy, reach=REACH):
    """Least-shift rect of r's height and width >= area tgt, clear of obs, in the margin, row/site aligned."""
    h = r[3] - r[1]; w = max(r[2] - r[0], SITE * np.ceil(tgt / h / SITE - 1e-9))
    O = np.asarray(obs, float).reshape(-1, 4)
    xs = {r[0]} | {o[2] for o in O} | {o[0] - w for o in O} | {MARGIN, W - MARGIN - w}
    ys = {r[1]} | {o[3] for o in O} | {o[1] - h for o in O} | {MARGIN, H - MARGIN - h}
    sx = lambda v: INSET + SITE * np.ceil((v - INSET) / SITE - 1e-6)
    sy = lambda v: INSET + ROW * np.ceil((v - INSET) / ROW - 1e-6)
    xs = np.array(sorted({round(sx(v), 4) for v in xs if MARGIN - 1e-6 <= v <= W - MARGIN - w + 1e-6}
                         | {round(sx(r[0]), 4)}))
    ys = np.array(sorted({round(sy(v), 4) for v in ys if MARGIN - 1e-6 <= v <= H - MARGIN - h + 1e-6}
                         | {round(sy(r[1]), 4)}))
    X, Y = np.meshgrid(xs, ys); X, Y = X.ravel(), Y.ravel()
    ok = (X >= MARGIN - 1e-6) & (Y >= MARGIN - 1e-6) & (X + w <= W - MARGIN + 1e-6) & (Y + h <= H - MARGIN + 1e-6)
    if pxy is not None:
        hp = np.maximum.reduce([np.abs(X + dx - pxy[0]) + np.abs(Y + dy - pxy[1]) for dx in (0, w) for dy in (0, h)])
        ok &= hp <= reach
    X, Y = X[ok], Y[ok]
    order = np.argsort(np.abs(X - r[0]) + np.abs(Y - r[1]), kind="stable")
    X, Y = X[order], Y[order]
    for i0 in range(0, len(X), 4096):
        x, y = X[i0:i0 + 4096, None], Y[i0:i0 + 4096, None]
        hit = ((np.minimum(x + w, O[:, 2]) > np.maximum(x, O[:, 0]) + 1e-6)
               & (np.minimum(y + h, O[:, 3]) > np.maximum(y, O[:, 1]) + 1e-6)).any(axis=1) if len(O) else \
            np.zeros(len(x), bool)
        free = np.flatnonzero(~hit)
        if len(free):
            j = i0 + free[0]
            return [round(float(X[j]), 4), round(float(Y[j]), 4), round(float(X[j] + w), 4), round(float(Y[j] + h), 4)]
    return None


def row_cut_boxes(t):
    """Macros the kit cuts placement rows at (no halo): hard cores + LEF-bearing contents + physical parts."""
    return dict(S.placed_macro_boxes(t, halo=0.0))


def hard_child_row(t, lc, tn, bus, b, boxes):
    """Check of a band implemented by a hard cland child (b["hard_core"]): (row, error or None)."""
    r, hc = b["rect_um"], b["hard_core"]
    own = boxes.get(hc)
    pxy = pin_xy(t, lc, bus)
    hp = round(hop(r, pxy), 3) if pxy is not None else b.get("max_pin_to_band_hop_um")
    row = dict(type=tn, bus=bus, hard_core=hc, rect_um=r, child_box_um=None if own is None else [round(v, 4) for v in own],
               others=sorted(k for k, o in boxes.items() if k != hc and ov(r, o)), hop_um=hp,
               hop_from="pin" if pxy is not None else "plan")
    if own is None:
        return row, f"hard child {hc} is not placed"
    if max(abs(a - c) for a, c in zip(own, r)) > HARD_TOL_UM:
        return row, f"hard child {hc} box {row['child_box_um']} is not the band {r}"
    if row["others"]:
        return row, f"hard child band overlaps {row['others']}"
    if hp is None or hp > REACH + 1e-6:
        return row, f"pin hop {hp} > {REACH}"
    return row, None


def run(raw, side, types=r".", reserve=None, factor=1.25, check=False):
    out = copy.deepcopy(raw)
    P = S.Plan(out) if (out.get("die") or {}).get("pg", {}).get("domains") and out.get("partitions") else None
    used = {p["type"] for p in out.get("partitions", [])}
    rep = dict(moved=[], failed=[], blocked_not_moved=[], hard_child=[])
    for tn in sorted(out["partition_types"]):
        if not re.search(types, tn) or (used and tn not in used):
            continue
        t = out["partition_types"][tn]
        lc = ((t.get("clock") or {}).get("landing_contract") or {})
        bands = lc.get("bands") or {}
        if not bands:
            continue
        boxes = row_cut_boxes(t)
        macros = [list(b) for b in boxes.values()]
        W, H = t["outline_um"]
        for bus in sorted(bands):
            b = bands[bus]
            if not b.get("rect_um") or b.get("rects_um") or "width" not in b:
                continue
            r = b["rect_um"]
            if b.get("hard_core"):
                row, err = hard_child_row(t, lc, tn, bus, b, boxes)
                (rep["failed"].append(dict(row, error=err)) if err else rep["hard_child"].append(row))
                continue
            if not any(ov(r, m) for m in macros):
                continue
            res = (reserve or {}).get((tn, bus)) or model_reserve(b["width"])
            fa = free_area(r, macros)
            row = dict(type=tn, bus=bus, width=b["width"], rect_um=r, area_um2=round(area(r), 1),
                       macro_free_um2=round(fa, 1), reserve_um2=round(res, 1), need_um2=round(factor * res, 1))
            if fa + 1e-6 >= factor * res:
                rep["blocked_not_moved"].append(row); continue
            pxy = pin_xy(t, lc, bus)
            obs = obstacles(t, tn, P, side, lc, bus)
            nr = None if check else resite(r, max(area(r), factor * res), W, H, obs, pxy)
            if nr is None:
                rep["failed"].append(dict(row, error="check only" if check else "no clear rect within reach")); continue
            nb = dict(b); nb["resited_from_um"] = list(r); nb["rect_um"] = nr
            if pxy is not None:
                nb["max_pin_to_band_hop_um"] = round(hop(nr, pxy), 3)
            nb["resite"] = (f"CLAND-BAND 11-05 cland_band_fit: macro-free {fa:.1f} um2 < {factor} x reserve {res:.1f}; "
                            f"moved clear of macros/obstacles (least shift)")
            bands[bus] = nb
            rep["moved"].append(dict(row, new_rect_um=nr, shift_um=round(abs(nr[0] - r[0]) + abs(nr[1] - r[1]), 3),
                                     new_area_um2=round(area(nr), 1), pin_um=pxy,
                                     hop_um=None if pxy is None else round(hop(nr, pxy), 1)))
    return out, rep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan"); ap.add_argument("sidecar"); ap.add_argument("out"); ap.add_argument("report")
    ap.add_argument("--types", default=r"."); ap.add_argument("--reserve"); ap.add_argument("--factor", type=float, default=1.25)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    raw = json.loads(Path(a.plan).read_text())
    side = json.loads(Path(a.sidecar).read_text()) if a.sidecar not in ("", "-", "none") else None
    reserve = None
    if a.reserve:
        reserve = {}
        for ln in Path(a.reserve).read_text().splitlines():
            f = ln.split("\t")
            if len(f) >= 3 and not ln.startswith("#"):
                try:
                    reserve[(f[0], f[1])] = float(f[2])
                except ValueError:
                    pass
    out, rep = run(raw, side, a.types, reserve, a.factor, a.check)
    if not a.check:
        Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    Path(a.report).write_text(json.dumps(rep, indent=1) + "\n")
    print(f"moved {len(rep['moved'])} failed {len(rep['failed'])} blocked-but-fits {len(rep['blocked_not_moved'])} "
          f"hard-child ok {len(rep['hard_child'])}")
    for m in rep["moved"]:
        print("MOVED", m["type"], m["bus"], m["rect_um"], "->", m["new_rect_um"], "shift", m["shift_um"], "hop", m["hop_um"])
    for f in rep["failed"]:
        print("FAIL", f["type"], f["bus"], f.get("error"))
    return 1 if rep["failed"] and not a.check else 0


if __name__ == "__main__":
    sys.exit(main())
