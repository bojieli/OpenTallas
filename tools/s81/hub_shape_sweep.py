#!/usr/bin/env python3
"""S81 hub-shape / more-dies sweep (S81-AGGRO, 2026-10-15).

Owner questions 20:45-21:xx: how far can 'more dies, fewer ROM pairs a die' go before more dies stop buying hub room;
does a central square / near-circular / plus-shaped or a compact VM-centred hub beat the full-height strip; and what
does TILE-FILL's re-packed ROM field (results/arch/tile_fill_audit_1015) change.

FIELD (exact, canonical code): root frames are the canonical slot stacks (q slot 304.56 um holds 2 pairs, BF slot
289.44 holds 1; pack order as dsrom_s81_fulldie.pack_frame) over 128 uniform roots r*P//128 with BF sites i*P//B,
exactly the allocator's RaggedPool; columns are packed by tools/s81/canonical_capacity.pack_columns into the free
intervals (canonical_capacity.free_intervals) left by the released hard boxes of plan_r8c (SW PHY/ctrl/svc, links,
svcj) and the hub shape.  'refill' = TILE-FILL's no-re-closure field: node strip 86.4 -> 43.2 um (column pitch
-43.2 um) and BF cfg band re-slotted (-21.6 um a BF slot; TILE-FILL +-10 mm2), roots kept uniform.  refill="parity"
also gives each odd-q root one more pair in its empty R lane (ragged +-1 roots, allocator --regions-json): measured
to buy almost no stages, because the allocator stripes each matrix over all 128 roots and is bounded by the smallest.
STAGES: the real allocator tools/dsrom_s73_pair1.py (subcommand `alloc` prints the runs; results read back here).
HUB / ROADS / RELAYS: centre-line SCREEN on the block-level dataflow graph results/arch/s81_globalfp_1015/graph.json
(12 collect trees 690-761 b -> sp_gather, 2 broadcast trees 566 b from sp_pq, 8 die links x 1,027 b -> collective,
SW service 2,875 b, hub star edges); bits = tracks at 21.09 tracks/um; 500 um per registered stage.  No GEN, no GRT.
"""
from __future__ import annotations

import argparse
import contextlib
import gzip
import io
import json
import math
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "tools"))
sys.path.insert(0, str(R / "tools/s81"))
import canonical_capacity as CC  # noqa: E402

PLAN = R / "results/physical/die_iter_1012/s81/hcp_home_growth_1015/plan_r8c.json.gz"
GRAPH = R / "results/arch/s81_globalfp_1015/graph.json"
FIRST, BETWEEN = 259.2, 388.8
DIE_W, DIE_H = 33000.0, 26000.0
BF_SHARE = 519 / 2417
TRK = 21.09375
STAGE_UM = 500.0
CUT_T = 0.45
HUB_Y0, HUB_Y1 = 1786.3, 23608.4
SLOT_Q, SLOT_BF = 304.56, 289.44
COL_W8, PITCH = 1182.816, 1191.456
REFILL = dict(node_strip_um=43.2, bf_slot_um=21.6)

_plan = json.load(gzip.open(PLAN))
FIXED = [(i[0], i[2], i[3], i[4], i[5]) for i in _plan["insts"] if i[7] in ("hub", "phy", "ctrl", "svc", "svcj", "band_blk", "link")]
XS0 = sorted({r["rect"][0] for r in _plan["regions"] if r.get("kind") == "field"})
assert len(XS0) == 22 and abs(XS0[1] - XS0[0] - PITCH) < 0.01
FIELD_FIXED = [f for f in FIXED if not f[0].startswith(("sp_", "bk_"))]
BOX = {f[0]: f[1:] for f in FIXED}
HCP_ROW = [(f"hcp{i}", 9417.6 + 1814.4 * i, 24624.0, 1728.0, 1296.0) for i in range(6)]
GR = json.loads(GRAPH.read_text())

# hub blocks (w, h): A2-F VM (S-VM 19:34), SU closure (a), a2_fit capture group / collective, HC v19 slots
B = dict(su=(1935.36, 10463.04), vm=(4104.0, 4115.0), mix4=(3229.2, 1321.92), capg=(1728.0, 3207.6),
         coll=(1728.0, 2894.4), host=(1728.0, 129.6), hc_t=(1816.56, 9849.6), hc_corr=(1816.56, 799.2),
         hc_s=(1816.56, 9324.7), bk=(5270.376, 1203.072), hcp=(6 * 1728.0 + 5 * 86.4, 1296.0))
STATIONS_IN_HUB_MM2 = 1.3
SVC_BITS = 1542 + 303 + 515 + 515        # VM/host/bk_selector/bk_collector <-> svc_SW
K_BITS = 1027
CH = 216.0                               # HC | capture channel (S-ROMTRADE)


# ================================================================== field
def lattice(refill):
    """22 canonical column x origins; refill narrows every column by 43.2 um (node strip) and re-pitches both fields
    from the die edges inward (gap 8.64 um), so the freed width lands at the hub."""
    if not refill:
        return list(XS0), COL_W8
    w = COL_W8 - REFILL["node_strip_um"]; p = PITCH - REFILL["node_strip_um"]
    west = [XS0[0] + i * p for i in range(11)]
    e_edge = XS0[-1] + COL_W8
    east = sorted(e_edge - w - i * p for i in range(11))
    return west + east, w


def frames_for(P, refill):
    Bn = math.ceil(P * BF_SHARE)
    bf = {i * P // Bn for i in range(Bn)}
    bounds = [r * P // 128 for r in range(129)]
    hb = SLOT_BF - (REFILL["bf_slot_um"] if refill else 0.0)
    out = []
    for r, (lo, hi) in enumerate(zip(bounds, bounds[1:])):
        n = hi - lo; b = sum(p in bf for p in range(lo, hi)); q = n - b
        if refill == "parity" and q % 2:
            n += 1; q += 1                     # the empty R lane of the last q slot takes one more pair
        out.append(dict(root=r, pair_count=n, bf=b, height_um=round(b * hb + math.ceil(q / 2) * SLOT_Q, 6)))
    return out, sum(f["pair_count"] for f in out), Bn


# ================================================================== shapes
REMOVE_ORDER = [10, 11, 9, 12, 8, 13, 7, 14]     # W10 E11 W9 E12 W8 E13 W7 E14 (x-sorted indices)


def strip(k, refill):
    xs, w = lattice(refill)
    rem = sorted(REMOVE_ORDER[:k])
    kept = [x for i, x in enumerate(xs) if i not in rem]
    x0 = max(x for x in kept if x < 16000) + w; x1 = min(x for x in kept if x >= 16000)
    return dict(name=f"strip-{k}", kind="strip", removed=rem, xs=kept, col_w=w, hub_rects=[(x0, 0.0, x1 - x0, DIE_H)],
                arm=(x0, x1), tier=(x0, x1), hc_tower=True, field_fixed=FIELD_FIXED + HCP_ROW, hcp_in_hub=False,
                hub_area_mm2=(x1 - x0) * (HUB_Y1 - HUB_Y0) / 1e6)


def tier_h(hc_tower):
    h = max(B["su"][1], B["vm"][1] + B["mix4"][1], B["capg"][1] + B["coll"][1] + B["host"][1])
    return h if hc_tower else max(h, B["hc_t"][1], B["hc_s"][1])


def lshape(k_full, extra_idx, refill, name, kind="L"):
    s = strip(k_full, refill)
    xs, w = lattice(refill)
    th = tier_h(True) + 500.0
    ty0 = 13000 - th / 2
    ext = [xs[i] for i in extra_idx]
    x0 = min([s["arm"][0]] + ext); x1 = max([s["arm"][1]] + [x + w for x in ext])
    s.update(name=name, kind=kind, tier=(x0, x1), hub_rects=s["hub_rects"] + [(x0, ty0, x1 - x0, th)],
             hub_area_mm2=((s["arm"][1] - s["arm"][0]) * (HUB_Y1 - HUB_Y0) + (x1 - x0 - (s["arm"][1] - s["arm"][0])) * th) / 1e6)
    return s


def central(rects, refill, name, kind):
    xs, w = lattice(refill)
    x0 = min(r[0] for r in rects); x1 = max(r[0] + r[2] for r in rects)
    area = sum(r[2] * r[3] for r in rects) / 1e6
    return dict(name=name, kind=kind, removed=[], xs=list(xs), col_w=w, hub_rects=rects, arm=(x0, x1), tier=(x0, x1),
                hc_tower=False, field_fixed=FIELD_FIXED, hcp_in_hub=True, hub_area_mm2=area)


def square(area_mm2, refill, name="square", aspect=1.0):
    h = math.sqrt(area_mm2 * 1e6 / aspect); w = h * aspect
    return central([(16500 - w / 2, 13000 - h / 2, w, h)], refill, name, "square")


def circle(area_mm2, refill, name="circle"):
    """near-circle = 3 stacked rectangles (stepped disc: centre band 0.6 d tall at full diameter d, caps 0.2 d tall at
    0.8 d); area = 0.92 d^2"""
    d = math.sqrt(area_mm2 * 1e6 / 0.92)
    cy = 13000; cx = 16500
    rects = [(cx - 0.4 * d, cy - 0.5 * d, 0.8 * d, 0.2 * d), (cx - 0.5 * d, cy - 0.3 * d, d, 0.6 * d),
             (cx - 0.4 * d, cy + 0.3 * d, 0.8 * d, 0.2 * d)]
    return central(rects, refill, name, "circle")


def compact_rect(refill, roads):
    """VM-centred compact hub sized to its blocks: row HC_t | HC_s | ch | capture column | VM (MIX4 on N) | SU, the
    squarest arrangement the hardened outlines allow (SU 1.9 x 10.5 mm and HC 1.8 x 9.8 mm are slivers), plus bk and
    the six HCP homes as rows on the S/N faces, plus ring roads sized to 0.45 (roads = dict W/E/S/N um)."""
    bw = 2 * B["hc_t"][0] + CH + B["capg"][0] + B["vm"][0] + B["su"][0]
    bh = tier_h(False) + B["bk"][1] + B["hcp"][1]
    w = bw + roads["W"] + roads["E"]; h = bh + roads["S"] + roads["N"]
    return central([(16500 - w / 2, 13000 - h / 2, w, h)], refill, "compact-VM", "compact")


# ================================================================== packing
def segments(shape):
    m = 20.001     # free_intervals keeps a 20-um halo; hub rectangles abut the columns, so shrink them by the halo
    obst = list(shape["field_fixed"]) + [("hub", r[0] + m, r[1] + m, r[2] - 2 * m, r[3] - 2 * m) for r in shape["hub_rects"]]
    segs = []
    for x in shape["xs"]:
        for lo, hi in CC.free_intervals(x, shape["col_w"], obst):
            if hi - lo >= FIRST + 2000:
                segs.append(dict(x_um=x, y0_um=lo, y1_um=hi, height_um=hi - lo, roots=0))
    return segs


def place(shape, P, refill):
    frames, Pp, Bn = frames_for(P, refill)
    segs = segments(shape)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            packed = CC.pack_columns(segs, frames, FIRST, BETWEEN, False)
    except SystemExit:
        return dict(ok=False, P=P)
    pl = []
    for i, fs in packed.items():
        c = segs[i]; y = c["y0_um"] + FIRST
        for f in fs:
            pl.append(dict(root=f["root"], x=c["x_um"], y=y, w=shape["col_w"], h=f["height_um"], n=f["pair_count"], b=f["bf"]))
            y += f["height_um"] + BETWEEN
        assert y - BETWEEN <= c["y1_um"] + 1e-6
    assert sorted(p["root"] for p in pl) == list(range(128))
    pl.sort(key=lambda p: p["root"])
    ns = [p["n"] for p in pl]
    return dict(ok=True, P=P, pairs=Pp, bf=Bn, segments=len(segs), placements=pl,
                regions=[[p["n"], p["b"]] for p in pl], ragged=max(ns) - min(ns) > 1)


def pmax(shape, refill, lo=1000, hi=2450):
    """largest base P whose 128 roots place (the worst-fit fallback is not monotone: scan down in 5s, then the 40 above)"""
    P = hi
    while P >= lo and not place(shape, P, refill)["ok"]:
        P -= 5
    assert P >= lo, shape["name"]
    for q in range(P + 40, P, -1):
        r = place(shape, q, refill)
        if r["ok"]:
            return r
    return place(shape, P, refill)


# ================================================================== hub layout (explicit block rectangles)
def layout(shape, demand=None):
    """Strip/L/plus: W->E S14W | HC tower | ch | capture column | VM (MIX4 N) | SU | S14E, VM centred at y 13,000,
    roads full height, sized to 0.45 on `demand` (bits), spare -> 216-um HC|capture channel then roads.
    Central shapes: row HC_t | HC_s | ch | capture column | VM | SU centred, ring roads in the spare."""
    rects = {}
    tx0, tx1 = shape["tier"]
    cy = 13000.0
    if shape["hc_tower"]:
        bw = B["hc_t"][0] + B["capg"][0] + B["vm"][0] + B["su"][0]
        spare = (tx1 - tx0) - bw
        d = demand or dict(W=6977.0, E=4207.0)
        need = {k: d[k] / (TRK * CUT_T) for k in ("W", "E")}
        if spare >= sum(need.values()):
            ch = min(CH, spare - sum(need.values())); rest = spare - sum(need.values()) - ch
            rw = {k: need[k] + rest / 2 for k in need}
        else:
            ch = 0.0; tot = d["W"] + d["E"]
            rw = {k: max(spare, 0) * d[k] / tot for k in ("W", "E")}
        x = shape["arm"][0] + rw["W"]
        hct = B["hc_t"][1] + B["hc_corr"][1] + B["hc_s"][1]
        y0 = cy - hct / 2
        rects["hc_t"] = (x, y0, B["hc_t"][0], B["hc_t"][1])
        rects["hc_s"] = (x, y0 + B["hc_t"][1] + B["hc_corr"][1], B["hc_s"][0], B["hc_s"][1])
        x += B["hc_t"][0] + ch
        roads = dict(W=round(rw["W"], 1), E=round(rw["E"], 1))
    else:
        bw = 2 * B["hc_t"][0] + CH + B["capg"][0] + B["vm"][0] + B["su"][0]
        x = 16500 - bw / 2
        rects["hc_t"] = (x, cy - B["hc_t"][1] / 2, *B["hc_t"])
        rects["hc_s"] = (x + B["hc_t"][0], cy - B["hc_s"][1] / 2, *B["hc_s"])
        x += 2 * B["hc_t"][0] + CH
        ch = CH; spare = None; roads = None
    rects["capg"] = (x, cy - B["capg"][1] / 2, *B["capg"])
    rects["coll"] = (x, cy + B["capg"][1] / 2, *B["coll"])
    rects["host"] = (x, cy + B["capg"][1] / 2 + B["coll"][1], *B["host"])
    x += B["capg"][0]
    rects["vm"] = (x, cy - B["vm"][1] / 2, *B["vm"])
    rects["mix4"] = (x + (B["vm"][0] - B["mix4"][0]) / 2, cy + B["vm"][1] / 2, *B["mix4"])
    x += B["vm"][0]
    rects["su"] = (x, cy - B["su"][1] / 2, *B["su"])
    return dict(rects={k: [round(v, 1) for v in r] for k, r in rects.items()}, hc_cap_channel_um=round(ch, 1),
                tier_blocks_w_um=round(bw, 1), tier_w_um=round(tx1 - tx0, 1),
                tier_spare_um=None if spare is None else round(spare, 1),
                hc_form="tower" if shape["hc_tower"] else "HC_t|HC_s side by side", roads_um=roads)


def ctr(r):
    return (r[0] + r[2] / 2, r[1] + r[3] / 2)


def gap(a, b):
    dx = max(0.0, max(a[0], b[0]) - min(a[0] + a[2], b[0] + b[2]))
    dy = max(0.0, max(a[1], b[1]) - min(a[1] + a[3], b[1] + b[3]))
    return dx + dy


STAR = [("SU-VM", "su", "vm", 17137), ("capture-VM", "capg", "vm", 13376), ("HC_s-HC_t", "hc_s", "hc_t", 15660),
        ("MIX4-VM", "mix4", "vm", 12732), ("collective-HC_s", "coll", "hc_s", 8225),
        ("capture-gather", "capg", "capg", 6959), ("HC_s-VM", "hc_s", "vm", 5401), ("collective-VM", "coll", "vm", 4921),
        ("PQ-VM", "capg", "vm", 2069), ("WFC-VM", "capg", "vm", 1589)]
TODAY_INTERNAL_STAGES = {"MIX4-VM": 2, "collective-VM": 3, "HC_s-VM": 4, "collective-HC_s": 4, "HC_s-HC_t": 2}


def internal(lay):
    r = lay["rects"]
    out = {}
    for nm, a, b, bits in STAR:
        g = 0.0 if a == b else gap(r[a], r[b])
        out[nm] = dict(bits=bits, gap_um=round(g, 1), stages=math.ceil(g / STAGE_UM),
                       today_stages=TODAY_INTERNAL_STAGES.get(nm, 0))
    return out


# ================================================================== field / link dataflow
def boundary_entry(px, py, rects):
    best = None
    for (x, y, w, h) in rects:
        ex = min(max(px, x), x + w); ey = min(max(py, y), y + h)
        d = abs(px - ex) + abs(py - ey)
        if best is None or d < best[0] - 1e-9:
            if px <= x + 1e-6 and abs(ex - x) < 1e-6 and y < ey < y + h:
                side = "W"
            elif px >= x + w - 1e-6 and abs(ex - x - w) < 1e-6 and y < ey < y + h:
                side = "E"
            elif py <= y + 1e-6:
                side = "S"
            else:
                side = "N"
            best = (d, ex, ey, side)
    return best


def port_of(p, rects):
    """frame port = the point of the frame outline nearest the hub"""
    fx, fy, fw, fh = p["x"], p["y"], p["w"], p["h"]
    best = None
    for (x, y, w, h) in rects:
        hx = min(max(fx + fw / 2, x), x + w); hy = min(max(fy + fh / 2, y), y + h)
        px = min(max(hx, fx), fx + fw); py = min(max(hy, fy), fy + fh)
        d = abs(px - hx) + abs(py - hy)
        if best is None or d < best[0]:
            best = (d, px, py)
    return best[1], best[2]


def trees():
    out = []
    for e in GR["edges"]:
        if e["kind"] != "tree":
            continue
        ids = sorted(int(x[1:]) for x in e["ends"] if x.startswith("F"))
        hub = [x for x in e["ends"] if not x.startswith("F")][0]
        out.append(dict(kind="collect" if hub == "sp_gather" else "bcast", width=e["width"], roots=ids))
    return out


def dataflow(shape, lay, pl):
    rects = shape["hub_rects"]
    R_ = lay["rects"]
    tgt = ctr(R_["capg"])               # sp_gather and sp_pq sit in the capture group
    ports = {}
    for p in pl["placements"]:
        px, py = port_of(p, rects)
        d, ex, ey, side = boundary_entry(px, py, rects)
        crossed = 0
        if side in "NS":
            crossed = sum(1 for q in pl["placements"] if abs(q["x"] - p["x"]) < 1 and q is not p and
                          min(py, ey) < q["y"] + q["h"] / 2 < max(py, ey))
        ports[p["root"]] = dict(port=(px, py), field=d, entry=(ex, ey), side=side, crossed=crossed)
    tr_rows = []
    flows = []          # (side, entry coord along the side, target coord along the side, bits)
    tx, ty = tgt
    for t in trees():
        paths = [ports[r]["field"] + abs(ports[r]["entry"][0] - tx) + abs(ports[r]["entry"][1] - ty) for r in t["roots"]]
        sides = {}
        for r in t["roots"]:
            sides.setdefault(ports[r]["side"], []).append(r)
        for side, rs in sides.items():         # one trunk per hub side the tree touches
            e = ports[min(rs, key=lambda r: ports[r]["field"])]["entry"]
            flows.append((side, e[1] if side in "WE" else e[0], ty if side in "WE" else tx, t["width"]))
        tr_rows.append(dict(kind=t["kind"], width=t["width"], frames=len(t["roots"]), max_path_um=round(max(paths)),
                            max_stages=math.ceil(max(paths) / STAGE_UM), sides="".join(sorted(sides))))
    cx_, cy_ = ctr(R_["coll"])
    links = []
    for n in ("lk_W0", "lk_W1", "lk_W2", "lk_W3", "lk_E0", "lk_E1", "lk_E2", "lk_E3"):
        b = BOX[n]; lx, ly = b[0] + b[2] / 2, b[1] + b[3] / 2
        d, ex, ey, side = boundary_entry(lx, ly, rects)
        L = d + abs(ex - cx_) + abs(ey - cy_)
        links.append(dict(link=n, um=round(L), stages=math.ceil(L / STAGE_UM), side=side))
        flows.append((side, ey if side in "WE" else ex, cy_ if side in "WE" else cx_, K_BITS))
    sv = BOX["svc_SW"]; sx, sy = sv[0] + sv[2] / 2, sv[1] + sv[3]
    d, ex, ey, side = boundary_entry(sx, sy, rects)
    vx, vy = ctr(R_["vm"])
    svc = dict(um=round(d + abs(ex - vx) + abs(ey - vy)), side=side)
    svc["stages"] = math.ceil(svc["um"] / STAGE_UM)
    flows.append((side, ey if side in "WE" else ex, vy if side in "WE" else vx, SVC_BITS))
    dem = {}
    for side in "WESN":
        fs = [f for f in flows if f[0] == side]
        if fs:
            lo = sum(f[3] for f in fs if f[1] < f[2]); hi = sum(f[3] for f in fs if f[1] >= f[2])
            dem[side] = max(lo, hi)
    return dict(trees=tr_rows, links=links, svc=svc, demand=dem,
                vertical_crossings=sum(1 for q in ports.values() if q["crossed"]),
                max_frames_crossed=max(q["crossed"] for q in ports.values()),
                sides={s: sum(1 for q in ports.values() if q["side"] == s) for s in "WESN"})


# ================================================================== evaluate one shape
# calibration: the screen's worst-point demand on today's strip vs option C's measured peaks (S14W 6,977 no-TDM,
# S14E 4,207; results/arch/s81_globalfp_1015/optc_r2): the screen assumes every trunk reaches the worst point
OPTC = dict(W=6977.0, E=4207.0)
_CAL = {}


def calib():
    if not _CAL:
        sh = strip(0, False)
        pl = pmax(sh, False)
        df = dataflow(sh, layout(sh), pl)
        _CAL.update(W=OPTC["W"] / df["demand"]["W"], E=OPTC["E"] / df["demand"]["E"],
                    raw_today=dict(df["demand"]))
        _CAL["S"] = _CAL["N"] = (_CAL["W"] + _CAL["E"]) / 2
    return _CAL


def layout_star(shape, demand):
    """VM-centred star stacked in a strip (coordinator 21:xx): SU on the VM W face, capture group (gather/PQ/WFC/sseq)
    on the VM E face facing the E road, MIX4 on the N face, HC_s and the collective under the VM, HC_t beside HC_s
    under the SU; one horizontal crossing channel (W road -> gather) between the VM row and the HC row, sized to
    0.45 on the W demand.  Bounding box 7,767 x (20,313 + channel) um: the hardened SU (1.9 x 10.5 mm) and HC
    (1.8 x 9.3-9.8 mm) slivers make the star a column, not a square."""
    x0, x1 = shape["arm"]
    need = {k: demand[k] / (TRK * CUT_T) for k in ("W", "E")}
    chh = demand["W"] / (TRK * CUT_T)
    slack = (HUB_Y1 - HUB_Y0) - (B["hc_t"][1] + B["su"][1] + chh)
    chh += max(slack, 0) / 2                         # half the vertical slack widens the crossing channel
    bw = B["su"][0] + B["vm"][0] + B["capg"][0]
    spare = (x1 - x0) - bw
    fits_w = spare >= sum(need.values())
    rest = max(spare - sum(need.values()), 0)
    rw = {k: (need[k] + rest / 2) if fits_w else max(spare, 0) * demand[k] / (demand["W"] + demand["E"]) for k in need}
    H = B["hc_t"][1] + chh + B["su"][1]
    fits_h = H <= HUB_Y1 - HUB_Y0
    Y = 13000 - H / 2 + B["hc_t"][1] + chh            # VM / SU bottom
    xs = x0 + rw["W"]; xv = xs + B["su"][0]; xc = xv + B["vm"][0]
    r = dict(su=(xs, Y, *B["su"]), vm=(xv, Y, *B["vm"]),
             mix4=(xv + (B["vm"][0] - B["mix4"][0]) / 2, Y + B["vm"][1], *B["mix4"]),
             capg=(xc, Y + B["vm"][1] / 2 - B["capg"][1] / 2, *B["capg"]),
             host=(xc, Y + B["vm"][1] / 2 + B["capg"][1] / 2, *B["host"]),
             hc_t=(xs, Y - chh - B["hc_t"][1], *B["hc_t"]), hc_s=(xv, Y - chh - B["hc_s"][1], *B["hc_s"]),
             coll=(xv + B["hc_s"][0], Y - chh - B["coll"][1], *B["coll"]))
    return dict(rects={k: [round(v, 1) for v in q] for k, q in r.items()}, arrangement="star",
                hc_cap_channel_um=0.0, crossing_channel_um=round(chh, 1), tier_blocks_w_um=round(bw, 1),
                tier_w_um=round(x1 - x0, 1), tier_spare_um=round(spare, 1), stack_h_um=round(H, 1),
                fits=bool(fits_w and fits_h), hc_form="HC_t|HC_s under SU|VM", roads_um={k: round(v, 1) for k, v in rw.items()})


def blocks_mm2(shape, star=False):
    a = sum(B[k][0] * B[k][1] for k in ("su", "vm", "mix4", "capg", "coll", "host", "hc_t", "hc_s", "bk")) / 1e6
    a += (B["hc_corr"][0] * B["hc_corr"][1] / 1e6) if (shape["hc_tower"] and not star) else 0
    a += STATIONS_IN_HUB_MM2 + (B["hcp"][0] * B["hcp"][1] / 1e6 if shape["hcp_in_hub"] else 0)
    return a


def evaluate(shape, refill, arrangement="tier"):
    cal = calib()
    pl = pmax(shape, refill)
    star = arrangement == "star"
    lay = layout(shape)
    df = dataflow(shape, lay, pl)
    for _ in range(2):
        dem = {k: round(v * cal[k]) for k, v in df["demand"].items()}
        if star:
            lay = layout_star(shape, dict(W=dem.get("W", 0), E=dem.get("E", 0)))
        elif shape["hc_tower"]:
            lay = layout(shape, dict(W=dem.get("W", 0), E=dem.get("E", 0)))
        df = dataflow(shape, lay, pl)
    dem = {k: round(v * cal[k]) for k, v in df["demand"].items()}
    hub = shape["hub_area_mm2"]
    r0 = shape["hub_rects"]
    hx0 = min(r[0] for r in r0); hx1 = max(r[0] + r[2] for r in r0)
    hy0 = max(min(r[1] for r in r0), HUB_Y0); hy1 = min(max(r[1] + r[3] for r in r0), HUB_Y1)
    if shape["hc_tower"] or star:
        rw = lay["roads_um"]
        cuts = {k: round(dem[k] / (TRK * max(rw[k], 1e-3)), 3) for k in ("W", "E") if k in dem}
        if star:
            cuts["crossing"] = round(dem["W"] / (TRK * lay["crossing_channel_um"]), 3)
        road45 = sum(dem.get(k, 0) for k in ("W", "E")) / (TRK * CUT_T) * (hy1 - hy0) / 1e6
        if star:
            road45 += lay["crossing_channel_um"] * lay["tier_blocks_w_um"] / 1e6
        fits = lay.get("fits", (lay["tier_spare_um"] or 0) >= sum(dem.get(k, 0) for k in ("W", "E")) / (TRK * 0.5))
    else:
        mid = max(r0, key=lambda r: r[2])
        sx = mid[2] - lay["tier_blocks_w_um"]
        sy = (hy1 - hy0) - tier_h(False) - B["bk"][1] - B["hcp"][1]

        def split(keys, sp):
            tot = sum(dem.get(k, 0) for k in keys) or 1
            return {k: max(sp, 0) * dem.get(k, 0) / tot for k in keys}
        rw = split("WE", sx) | split("SN", sy)
        cuts = {k: round(dem[k] / (TRK * max(rw[k], 1e-3)), 3) for k in dem}
        road45 = sum(dem.get(k, 0) / (TRK * CUT_T) * ((hy1 - hy0) if k in "WE" else (hx1 - hx0)) for k in dem) / 1e6
        lay["roads_um"] = {k: round(v, 1) for k, v in rw.items()}
        fits = sx > 0 and sy > 0
    bm = blocks_mm2(shape, star)
    il = internal(lay)
    col = [t for t in df["trees"] if t["kind"] == "collect"]; bc = [t for t in df["trees"] if t["kind"] == "bcast"]
    return dict(name=shape["name"] + ("/star" if star else ""), shape=shape["name"], arrangement=arrangement,
                kind=shape["kind"], refill=refill, removed_columns=shape["removed"],
                hub_rects_um=[[round(v, 1) for v in r] for r in shape["hub_rects"]], hub_area_mm2=round(hub, 1),
                hub_width_um=round(hx1 - hx0, 1), fits=bool(fits),
                base_P=pl["P"], pairs=pl["pairs"], bf=pl["bf"], ragged=pl["ragged"], regions=pl["regions"],
                segments=pl["segments"], hub_blocks_mm2=round(bm, 2), roads_at_045_mm2=round(road45, 2),
                whitespace=round(1 - (bm + road45) / hub, 3), road_demand_bits=dem,
                road_demand_raw_bits=df["demand"], road_cuts=cuts,
                worst_road_cut=max(cuts.values()) if cuts else None, layout=lay, internal_links=il,
                internal_max_stages=max(v["stages"] for v in il.values()),
                internal_relay_growth=sum(max(0, v["stages"] - v["today_stages"]) for v in il.values()),
                internal_bit_mm=round(sum(v["bits"] * v["gap_um"] for v in il.values()) / 1e3),
                trees=df["trees"], collect_max_stages=max(t["max_stages"] for t in col),
                collect_max_um=max(t["max_path_um"] for t in col),
                bcast_max_stages=max(t["max_stages"] for t in bc), bcast_max_um=max(t["max_path_um"] for t in bc),
                links=df["links"], link_max_stages=max(l["stages"] for l in df["links"]),
                link_max_um=max(l["um"] for l in df["links"]), svc=df["svc"],
                vertical_field_crossings=df["vertical_crossings"], max_frames_crossed=df["max_frames_crossed"],
                roots_by_side=df["sides"])


def compact(refill):
    """size the compact hub's ring roads to 0.45 on its own demand (three passes)"""
    roads = dict(W=800.0, E=800.0, S=800.0, N=800.0)
    for _ in range(3):
        sh = compact_rect(refill, roads)
        pm = pmax(sh, refill)
        df = dataflow(sh, layout(sh), pm)
        roads = {k: max(df["demand"].get(k, 0) / (TRK * CUT_T), 50.0) for k in "WESN"}
    return compact_rect(refill, roads)


def shapes(refill):
    s = {f"strip-{k}": strip(k, refill) for k in (0, 1, 2, 3, 4, 5, 6, 7, 8)}
    s["L-3+2E"] = lshape(3, [12, 13], refill, "L-3+2E")
    s["L-4+1E"] = lshape(4, [13], refill, "L-4+1E")
    s["plus-3+1W1E"] = lshape(3, [8, 12], refill, "plus-3+1W1E", kind="plus")
    a5 = strip(5, False)["hub_area_mm2"]
    s["square"] = square(a5, refill)
    s["circle"] = circle(a5, refill)
    s["compact-VM"] = compact(refill)
    return s


def min_stages(alloc_dir: Path, tag: str):
    """smallest S whose allocator run <tag>s<S> passes with 0 failures, provided S-1 was run and failed"""
    runs = {}
    for d in alloc_dir.glob(f"{tag}s*"):
        v = d / "mapping_verdict.json"
        if v.exists() and d.name[len(tag) + 1:].isdigit():
            j = json.loads(v.read_text())
            runs[int(d.name[len(tag) + 1:])] = bool(j["decoder_matrix_capacity_PASS"]) and not j["failures"]
    ok = sorted(S for S, p in runs.items() if p)
    if not ok:
        return None, runs
    S = ok[0]
    return (S if runs.get(S - 1) is False else None), runs


def summarise(geo: Path, points: Path, alloc_dir: Path, out: Path):
    import rom_trade as RT
    g = json.loads(geo.read_text())
    pts = json.loads(points.read_text())
    cmp_ = json.loads((R / RT.CMP).read_text())["ds_rom"]
    ref = dict(stages=85, AR_us=cmp_["AR_us"], MTP_step_us=cmp_["MTP_step_us"], tau=cmp_["tau"])
    today = RT.array(81, 2417, ref)
    phases = 400            # ~40 layers x ~10 field phases a token (S-ROMTRADE README section 5)
    base_tree = {False: None}
    rows = []
    for r in g["rows"]:
        tag = None
        for p in pts:
            if p["P"] == r["pairs"] and p["B"] == r["bf"] and p["ragged"] == (r["refill"] == "parity"):
                if r["refill"] != "parity" or json.loads((alloc_dir.parent / "regions" / f"{p['tag']}.json").read_text()) == r["regions"]:
                    tag = p["tag"]
        S, runs = min_stages(alloc_dir, tag) if tag else (None, {})
        r = {k: v for k, v in r.items() if k not in ("regions", "trees", "links")} | dict(alloc_tag=tag, alloc_runs=runs, stages=S)
        if S:
            a_ = RT.array(S, r["pairs"], ref)
            r["array"] = a_
            r["layer_dies"] = a_["layer_dies"]; r["dies"] = a_["dies"]; r["d_dies_vs_today"] = a_["dies"] - today["dies"]
            r["AR_tok_s"] = a_["vs_today_headline"]["AR_tok_s"]; r["MTP_tok_s"] = a_["vs_today_headline"]["MTP_tok_s"]
            r["chips_kW"] = round(a_["chips_w"] / 1e3, 1); r["silicon_mm2"] = a_["total_silicon_mm2"]
            r["silicon_vs_today"] = round(a_["total_silicon_mm2"] / today["total_silicon_mm2"] - 1, 4)
        rows.append(r)
    t0 = [r for r in rows if r["name"] == "strip-0" and not r["refill"]][0]
    for r in rows:
        dtree = (r["collect_max_stages"] - t0["collect_max_stages"]) + (r["bcast_max_stages"] - t0["bcast_max_stages"])
        r["tree_stage_growth_vs_today"] = dtree
        r["tree_latency_us_est"] = round(dtree * phases / 1.2e3, 2)
        if r.get("AR_tok_s"):
            ar_us = 1e6 / r["AR_tok_s"] + r["tree_latency_us_est"]
            r["AR_tok_s_with_tree"] = round(1e6 / ar_us, 1)
            mtp_us = RT.HEADLINE["tau"] * 1e6 / r["MTP_tok_s"] + r["tree_latency_us_est"]
            r["MTP_tok_s_with_tree"] = round(RT.HEADLINE["tau"] * 1e6 / mtp_us, 1)
    res = dict(schema="opentallas.s81.aggro.v1", date="2026-10-15", author="S81-AGGRO (Claude)",
               today=dict(stages=81, pairs=2417, dies=today["dies"], AR_tok_s=today["vs_today_headline"]["AR_tok_s"],
                          MTP_tok_s=today["vs_today_headline"]["MTP_tok_s"], chips_kW=round(today["chips_w"] / 1e3, 1),
                          silicon_mm2=today["total_silicon_mm2"]),
               calibration=g["calibration"], tree_phase_count_assumed=phases, rows=rows,
               tool_sha256=__import__("hashlib").sha256(Path(__file__).read_bytes()).hexdigest())
    out.write_text(json.dumps(res, indent=1) + "\n")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--summarise", nargs=3, type=Path, metavar=("GEO", "POINTS", "ALLOC_RUNS"))
    a = ap.parse_args()
    if a.summarise:
        summarise(*a.summarise, a.out)
        return
    rows = []
    for refill in (False, True, "parity"):
        for name, sh in shapes(refill).items():
            arrs = ["tier", "star"] if sh["kind"] == "strip" else ["tier"]
            for arr in arrs:
                ev = evaluate(sh, refill, arr)
                rows.append(ev)
                print(f"{ev['name']:16s} {str(refill):6s} fit={int(ev['fits'])} P={ev['pairs']:5d} "
                      f"rag={int(ev['ragged'])} hubw={ev['hub_width_um']:7.0f} hub={ev['hub_area_mm2']:6.1f} "
                      f"cut={ev['worst_road_cut']} ws={ev['whitespace']} coll={ev['collect_max_stages']} "
                      f"bc={ev['bcast_max_stages']} lk={ev['link_max_stages']} int={ev['internal_max_stages']}/"
                      f"{ev['internal_relay_growth']} bitmm={ev['internal_bit_mm']} vx={ev['vertical_field_crossings']}",
                      flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(dict(calibration=calib(), rows=rows), indent=1) + "\n")


if __name__ == "__main__":
    main()
