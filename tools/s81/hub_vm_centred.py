#!/usr/bin/env python3
"""S81 hub: VM-centred 2-D cluster vs the C5 W->E strip, on actual outlines and actual port faces (S81-AGGRO 2026-10-15).

PLANNING SCREEN ONLY (no GEN/GRT).  Inputs:
  * C5 strip = Codex combined_2118 hub_layout.json (origin/codex/s81-widehub-2118, rm5_p1973 hub x 9,850.0-21,941.7 um).
  * actual outlines: wide_hub_layout.BLOCKS, VM split4 reservation 4,104 x 4,644, HC 10,160.6 / 9,583.9 (combined_2118).
  * actual closed-port faces (S-DIE 2210 from the pin JSONs + capture_face_review_2118): capture t_vm 13,376 b S face
    (M3+M5), f_gather 6,947 b N; gather t_capture S, rW* 4,446 b W, rE* 5,072 b E; SU all 17,137 VM bits on its N face;
    PQ f_vm 2,069 b on E, xw/xe 1,101 b W/E; WFC 2,739 b on E (1,589 VM + 1,030 collective + ...); host f/t_collective E.
    Unclosed parents (VM, MIX4, HC_s, HC_t, collective) take die-assigned pins (owner 10-13 top-down pin rule): '*'.
  * hub flows: results/arch/s81_globalfp_1015/graph.json (block-level, measured from the construction plan).
Tracks: W/E faces M4+M6 (0.048/0.064 um pitch) = 36.46 t/um; N/S faces M3+M5 (0.036/0.048) = 48.61 t/um
(capture_face_review_2118 convention).  Relay boundaries on a hop = ceil(gap/500 um) - 1 (registered pins both ends).
Roads: field-tree demand at the hub edge from the hub_shape_sweep screen calibrated to option C (W 7,779 b, E 4,207 b),
21.09 t/um, sized at 0.45.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

HUB = (9850.032, 21941.712)          # rm5_p1973 hub x
IO_BAND = (9850.032, 0.0, 1535.0, 3041.256)   # SW PHY/CTRL/SVC reaching into the hub foot
BK_SEL = (13872.384, 1464.48, 5270.376, 321.816)
BK_COL = (13872.384, 23654.16, 5270.376, 881.256)
SE_IO = (21615.048, 0.0, 8500.056, 3041.256)
HCP_ROW_Y = 24624.0
TOP_LIMIT = BK_COL[1] - 172.8
T_EW, T_NS, T_ROAD = 1 / 0.048 + 1 / 0.064, 1 / 0.036 + 1 / 0.048, 21.09375
HOP = 500.0
DEMAND = dict(W=7779, E=4207)        # calibrated rm5 hub-edge demand (hub_shape_sweep, option C calibration)

OUT = dict(su=(1889.976, 10709.256), vm=(4104.0, 4644.0), mix4=(3229.2, 1321.92), capture=(1727.976, 561.576),
           gather=(1727.976, 1045.416), pq=(1672.248, 449.256), wfc=(1727.976, 328.296), sseq=(1727.976, 88.536),
           collective=(1727.976, 2721.576), host=(1727.976, 129.576), hc_t=(1816.536, 10160.616),
           hc_s=(1816.536, 9583.896))

# (name, a, a_face, b, b_face, bits, class) -- '*' = die-assigned face (unclosed parent)
FLOWS = [("SU-VM", "su", "N", "vm", "*", 17137, "su"),
         ("HC_s-HC_t", "hc_s", "*", "hc_t", "*", 15660, "su"),
         ("capture-VM", "capture", "S", "vm", "*", 13376, "field"),
         ("MIX4-VM", "mix4", "*", "vm", "*", 12732, "engram"),
         ("collective-HC_s", "collective", "*", "hc_s", "*", 8225, "coll"),
         ("capture-gather", "capture", "N", "gather", "S", 6959, "field"),
         ("HC_s-VM", "hc_s", "*", "vm", "*", 5401, "su"),
         ("collective-VM", "collective", "*", "vm", "*", 4921, "coll"),
         ("PQ-VM", "pq", "E", "vm", "*", 2069, "field"),
         ("WFC-VM", "wfc", "E", "vm", "*", 1589, "field"),
         ("WFC-collective", "wfc", "E", "collective", "*", 1030, "coll"),
         ("host-collective", "host", "E", "collective", "*", 597, "coll")]
OWNER_FLOWS = ["capture-VM", "SU-VM", "HC_s-HC_t", "MIX4-VM", "collective-HC_s", "capture-gather"]


def c5_layout():
    B = {"su": [10511.856, 3818.88], "vm": [12423.456, 7989.84], "hc_t": [19573.056, 13599.36],
         "hc_s": [19573.056, 3216.24], "capture": [16549.056, 12072.24], "gather": [16549.056, 12677.04],
         "wfc": [16549.056, 11722.32], "pq": [16549.056, 13895.28], "sseq": [16549.056, 14517.36],
         "collective": [14821.056, 5246.64], "host": [14821.056, 4944.24], "mix4": [12423.456, 12655.44]}
    rects = {k: (x, y, *OUT[k]) for k, (x, y) in B.items()}
    return dict(name="C5 strip (Codex combined_2118)", key="c5", rects=rects,
                order="S14W | SU | VM (+MIX4 N) | capture column | VCH 1,296 | HC tower (hc_s low, hc_t high) | S14E",
                roads=dict(W=round(rects["su"][0] - HUB[0], 1), E=round(HUB[1] - (rects["hc_t"][0] + OUT["hc_t"][0]), 1)),
                gather_open=dict(W=None, E=None))


def vmc_layout(road_w=None, ch=432.0, vs=432.0, mix_over=875.0, su_under="W"):
    """VM-centred column: Wcol (PQ, WFC, sseq on the VM W face) | VM (MIX4 N-W, capture N-E, gather over capture;
    SU under the VM with a `vs` channel) | Ecol (collective on the VM E face low, host under it) | ch | HC tower
    flipped (hc_t LOW, corridor, hc_s HIGH so hc_s faces the collective and the VM)."""
    cw = 1728.0
    blocks_w = cw + OUT["vm"][0] + 86.4 + cw + ch + OUT["hc_s"][0]
    spare = HUB[1] - HUB[0] - blocks_w
    rw = road_w if road_w is not None else spare * DEMAND["W"] / (DEMAND["W"] + DEMAND["E"])
    wx = HUB[0] + rw
    vx = wx + cw
    ex = vx + OUT["vm"][0] + 86.4          # 86.4-um VM|collective-column seam (WFC->collective drop, host riser)
    hx = ex + cw + ch
    # vertical: stack top (gather) under bk_collector; SU at the bottom
    stack_h = OUT["su"][1] + vs + OUT["vm"][1] + 21.6 + OUT["capture"][1] + 43.2 + OUT["gather"][1]
    y_top = TOP_LIMIT - 400.0
    su_y = y_top - stack_h
    vm_y = su_y + OUT["su"][1] + vs
    vm_t = vm_y + OUT["vm"][1]
    cap = (vx + OUT["vm"][0] - OUT["capture"][0], vm_t + 21.6)
    gat = (cap[0], cap[1] + OUT["capture"][1] + 43.2)
    mix = (cap[0] - 21.6 - OUT["mix4"][0], vm_t + 21.6)
    su_x = vx if su_under == "W" else vx + OUT["vm"][0] - OUT["su"][0]
    coll = (ex, vm_y)
    host = (ex, vm_y - 21.6 - OUT["host"][1])
    # PQ / WFC / sseq on the VM W face, bottom-up from the VM floor: sseq, WFC, PQ (right-aligned on the VM)
    sseq = (vx - OUT["sseq"][0], vm_y + 21.6)
    pq = (vx - OUT["pq"][0], sseq[1] + OUT["sseq"][1] + 21.6)
    # WFC mirrored (MY: its E-face ports land on the W face) on the VM E face just above the collective; its
    # collective-bound bits drop 43.2 um into the collective's N face
    wfc = (ex, vm_y + OUT["collective"][1] + 43.2)
    # HC flipped tower: hc_s top aligned 300 um under the stack top, corridor 799.2, hc_t below
    hs_y = min(vm_y - 600.0, HCP_ROW_Y - 432.0 - OUT["hc_s"][1])
    ht_y = hs_y - 799.2 - OUT["hc_t"][1]
    P = dict(su=(su_x, su_y), vm=(vx, vm_y), mix4=mix, capture=cap, gather=gat, collective=coll, host=host,
             sseq=sseq, wfc=wfc, pq=pq, hc_s=(hx, hs_y), hc_t=(hx, ht_y))
    rects = {k: (x, y, *OUT[k]) for k, (x, y) in P.items()}
    return dict(name="VM-centred column (recommended)", key="vmc", rects=rects,
                order="S14W | PQ/WFC/sseq col | VM (MIX4 N-W, capture+gather N-E, SU under) | collective col | ch | "
                      "HC tower flipped (hc_t low, hc_s high) | S14E",
                roads=dict(W=round(rw, 1), E=round(HUB[1] - (hx + OUT["hc_s"][0]), 1)), params=dict(ch=ch, vs=vs),
                face_over=dict(wfc={"E": "W"}), mirrored=["sp_wfc (MY)"],
                seams=["WFC-collective", "host-collective"])


def vmc2_layout():
    """S-DIE 2210 deltas on vmc: D1 PQ on top of the gather (capture | 43.2 | gather | 172.8 | PQ), SU|VM gap 216
    (VM, N stack, collective column move down 216); D2 HC tower down so hc_s top sits below the gather
    (hc_t 1,216.5-11,377, corridor 799.2, hc_s 12,176-21,760): E returns run straight W over the HC top."""
    L = vmc_layout()
    r = dict(L["rects"])
    for k in ("vm", "capture", "gather", "mix4", "collective", "wfc", "host", "su"):
        x, y, w, h = r[k]
        r[k] = (x, y - 216.0, w, h)   # AGGRO r2: SU drops with the VM so the SU|VM channel stays 432 (S-DIE had 216)
    h_ = r["host"]
    r["host"] = (h_[0], h_[1] - 216.0, h_[2], h_[3])     # 237.6-um channel under the collective for the 8 die-link ports (screen hot row)
    g = r["gather"]
    r["pq"] = (g[0], g[1] + g[3] + 172.8, *OUT["pq"])
    hs_top = g[1] - 60.0
    r["hc_s"] = (r["hc_s"][0], hs_top - OUT["hc_s"][1], *OUT["hc_s"])
    r["hc_t"] = (r["hc_t"][0], r["hc_s"][1] - 799.2 - OUT["hc_t"][1], *OUT["hc_t"])
    L.update(name="VM-centred column v2 (S-DIE D1+D2, SU|VM 432)", key="vmc2", rects=r,
             order=L["order"].replace("PQ/WFC/sseq col", "sseq col").replace("capture+gather N-E", "capture+gather+PQ N-E")
             + "; hc_s top under the gather",
             channels=["PQ-VM"])
    return L


def vmc3_layout(ch=432.0, vs=216.0, su_bottom=300.0):
    """VM-centred SQUARE, low (S81-AGGRO r2): the forced vertical chain gather|capture|VM|SU placed as LOW as the die
    allows (bk_selector moved under the collective column / HC), MIX4 on the VM S face E part (beside the SU top), no
    W column (PQ on the gather per S-DIE D1, sseq under the host), HC_t | HC_s SIDE BY SIDE E of the collective column
    with both tops under the gather so E returns run straight W at gather height; W returns reach the gather W face
    over the free VM-N-W part.  VM W face takes the SW service (svc) and the selector."""
    W_ = OUT["vm"][0] + 86.4 + 1728.0 + ch + OUT["hc_s"][0] + 21.6 + OUT["hc_t"][0]
    spare = HUB[1] - HUB[0] - W_
    rw = max(spare * DEMAND["W"] / (DEMAND["W"] + DEMAND["E"]), IO_BAND[0] + IO_BAND[2] + 21.6 - HUB[0])
    vx = HUB[0] + rw
    ex = vx + OUT["vm"][0] + 86.4
    hx = ex + 1728.0 + ch
    su_y = su_bottom
    vm_y = su_y + OUT["su"][1] + vs
    vm_t = vm_y + OUT["vm"][1]
    cap = (vx + OUT["vm"][0] - OUT["capture"][0], vm_t + 21.6)
    gat = (cap[0], cap[1] + OUT["capture"][1] + 86.4)
    pq = (gat[0], gat[1] + OUT["gather"][1] + 172.8)
    mix = (vx + OUT["su"][0] + 21.6, vm_y - 21.6 - OUT["mix4"][1])
    coll = (ex, vm_y)
    wfc = (ex, vm_y + OUT["collective"][1] + 86.4)
    host = (ex, wfc[1] + OUT["wfc"][1] + 43.2)
    sseq = (ex, mix[1] - 21.6 - OUT["sseq"][1]) if False else (ex, host[1] + OUT["host"][1] + 43.2)
    hs_top = gat[1] - 60.0
    hc_s = (hx, hs_top - OUT["hc_s"][1])
    hc_t = (hx + OUT["hc_s"][0] + 21.6, hs_top - OUT["hc_t"][1])
    P = dict(su=(vx, su_y), vm=(vx, vm_y), mix4=mix, capture=cap, gather=gat, pq=pq, collective=coll, wfc=wfc,
             host=host, sseq=sseq, hc_s=hc_s, hc_t=hc_t)
    rects = {k: (x, y, *OUT[k]) for k, (x, y) in P.items()}
    return dict(name="VM-centred square, low (HC side by side)", key="vmc3", rects=rects,
                order="S14W | VM (capture+gather+PQ N-E, SU S-W, MIX4 S-E) | collective col (WFC MY, host, sseq) | "
                      "ch | hc_s | hc_t | S14E",
                roads=dict(W=round(rw, 1), E=round(HUB[1] - (hc_t[0] + OUT["hc_t"][0]), 1)),
                params=dict(ch=ch, vs=vs, su_bottom=su_bottom), face_over=dict(wfc={"E": "W"}),
                mirrored=["sp_wfc (MY)"], seams=["WFC-collective", "host-collective"], channels=["PQ-VM"],
                svc_face="W", moved_fixed=dict(bk_selector="to x 15,900-21,170, y 0-322 (under the collective column/HC)"))


def vmsq_layout(ch=216.0, vs=216.0):
    """VM-centred square: as vmc but hc_t | hc_s SIDE BY SIDE (each ~10 mm tall) E of the collective -> 11.6 mm of
    blocks across; needs a >= 12.7 mm hub (rm6, or rm5 with the TILE-FILL node-strip refill)."""
    L = vmc_layout(road_w=0.0, ch=ch, vs=vs)
    r = L["rects"]
    hx = r["collective"][0] + 1728.0 + ch
    vm_y = r["vm"][1]
    r["hc_s"] = (hx, vm_y + OUT["vm"][1] - OUT["hc_s"][1] + 900.0, *OUT["hc_s"])
    r["hc_t"] = (hx + OUT["hc_s"][0] + 21.6, r["hc_s"][1] - 300.0, *OUT["hc_t"])
    width = r["hc_t"][0] + OUT["hc_t"][0] - r["pq"][0] + (r["pq"][0] - r["wfc"][0])
    L.update(name="VM-centred square (HC side by side)", key="vmsq",
             order="PQ/WFC col | VM (+N stack, SU under) | collective col | ch | hc_s | hc_t",
             roads=dict(W=0.0, E=round(HUB[1] - (r["hc_t"][0] + OUT["hc_t"][0]), 1)), blocks_width_um=round(width, 1))
    return L


# ------------------------------------------------------------------ geometry
def face_seg(r, f):
    x, y, w, h = r
    return dict(N=((x, y + h), (x + w, y + h)), S=((x, y), (x + w, y)), W=((x, y), (x, y + h)), E=((x + w, y), (x + w, y + h)))[f]


OPP = dict(N="S", S="N", W="E", E="W")


def facing(ra, fa, rb):
    """overlap and gap if face fa of A looks straight at B"""
    ax, ay, aw, ah = ra
    bx, by, bw, bh = rb
    if fa in "NS":
        ov = (max(ax, bx), min(ax + aw, bx + bw))
        gap = by - (ay + ah) if fa == "N" else ay - (by + bh)
    else:
        ov = (max(ay, by), min(ay + ah, by + bh))
        gap = bx - (ax + aw) if fa == "E" else ax - (bx + bw)
    return ov, gap


def blocked(ov, fa, ra, gap, rects, skip, segments=False):
    """subtract from the overlap interval every other block that sits in the gap between the faces"""
    if gap <= 1.0:
        return [ov] if segments else ov[1] - ov[0]
    ax, ay, aw, ah = ra
    if fa in "NS":
        g0, g1 = (ay + ah, ay + ah + gap) if fa == "N" else (ay - gap, ay)
    else:
        g0, g1 = (ax + aw, ax + aw + gap) if fa == "E" else (ax - gap, ax)
    segs = [ov]
    for k, (x, y, w, h) in rects.items():
        if k in skip:
            continue
        if fa in "NS":
            if y < g1 and y + h > g0:
                cut = (x, x + w)
            else:
                continue
        else:
            if x < g1 and x + w > g0:
                cut = (y, y + h)
            else:
                continue
        nxt = []
        for s in segs:
            if cut[1] <= s[0] or cut[0] >= s[1]:
                nxt.append(s)
            else:
                if cut[0] > s[0]:
                    nxt.append((s[0], cut[0]))
                if cut[1] < s[1]:
                    nxt.append((cut[1], s[1]))
        segs = nxt
    if segments:
        return segs
    return sum(max(0.0, s[1] - s[0]) for s in segs)


def dist(ra, rb):
    ax, ay, aw, ah = ra
    bx, by, bw, bh = rb
    return max(0.0, max(ax, bx) - min(ax + aw, bx + bw)) + max(0.0, max(ay, by) - min(ay + ah, by + bh))


def relays(g):
    return max(0, math.ceil(g / HOP) - 1) if g > 25 else 0


def eval_flow(L, fl):
    name, a, fa, b, fb, bits, cls = fl
    R = L["rects"]
    fo = L.get("face_over", {})
    fa = fo.get(a, {}).get(fa, fa)
    fb = fo.get(b, {}).get(fb, fb)
    ra, rb = R[a], R[b]
    cands = [fa] if fa != "*" else ["N", "S", "W", "E"]
    best = None
    for f in cands:
        if fb not in ("*", OPP[f]):
            continue
        ov, gap = facing(ra, f, rb)
        if ov[1] - ov[0] <= 1.0 or gap < -1.0:
            continue
        win = blocked(ov, f, ra, gap, R, {a, b})
        if win <= 1.0:
            continue
        t = T_NS if f in "NS" else T_EW
        row = dict(face_a=f, face_b=OPP[f], direct=True, window_um=round(win, 1), gap_um=round(max(gap, 0), 1),
                   layers="M3+M5" if f in "NS" else "M4+M6", cut=round(bits / (win * t), 3), relays=relays(max(gap, 0)))
        if best is None or row["cut"] + 0.05 * row["relays"] < best["cut"] + 0.05 * best["relays"]:
            best = row
    if best is None:   # the fixed face does not look at B: L-turn / detour
        f = fa if fa != "*" else "N"
        (x0, y0), (x1, y1) = face_seg(ra, f)
        flen = abs(x1 - x0) + abs(y1 - y0)
        t = T_NS if f in "NS" else T_EW
        d = dist(ra, rb)
        if name in L.get("channels", ()):   # turn through a reserved free channel (free column top)
            best = dict(face_a=f, face_b="channel", direct=False, window_um=round(flen, 1), gap_um=round(d + 300, 1),
                        layers="M3+M5" if f in "NS" else "M4+M6", cut=round(bits / (flen * t), 3),
                        relays=relays(d + 300), status="L-turn through the reserved free column (screen-routed)")
        elif name in L.get("seams", ()):     # short L in a reserved seam next to both blocks
            best = dict(face_a=f, face_b="L-seam", direct=False, window_um=round(flen, 1), gap_um=round(d, 1),
                        layers="M3+M5" if f in "NS" else "M4+M6", cut=round(bits / (flen * t), 3), relays=0,
                        status="short L-turn through the reserved seam")
        else:
            need = bits / (T_EW * 0.45)
            best = dict(face_a=f, face_b="TURN", direct=False, window_um=round(flen, 1), gap_um=round(d + need, 1),
                        layers="M3+M5" if f in "NS" else "M4+M6", cut=None, relays=relays(d + need),
                        turn_channel_um_at_045=round(need, 1),
                        status=f"STRUCTURAL: face {f} does not look at {b}; needs a {need:.0f}-um turn channel "
                               "(none reserved)")
    best.update(name=name, a=a, b=b, bits=bits, cls=cls, bit_mm=round(bits * (best["gap_um"]) / 1e3))
    return best


FIXED = dict(io_band=IO_BAND, se_io=SE_IO, bk_selector=BK_SEL, bk_collector=BK_COL, hcp_row=(9417.6, HCP_ROW_Y, 10800.0, 1296.0))


def fixed_for(L):
    f = dict(FIXED)
    if "bk_selector" in L.get("moved_fixed", {}):
        f["bk_selector"] = (15900.0, 0.0, BK_SEL[2], BK_SEL[3])
    return f


def checks(L):
    R = L["rects"]
    bad = []
    ks = list(R)
    for i, k in enumerate(ks):
        x, y, w, h = R[k]
        if x < HUB[0] - 1 or x + w > HUB[1] + 1:
            bad.append(f"{k} outside hub x")
        if y < 0 or y + h > 26000:
            bad.append(f"{k} outside die y")
        for fn, b in fixed_for(L).items():
            if min(x + w, b[0] + b[2]) - max(x, b[0]) > 0.5 and min(y + h, b[1] + b[3]) - max(y, b[1]) > 0.5:
                bad.append(f"{k} overlaps {fn}")
        for j in ks[i + 1:]:
            a, b = R[k], R[j]
            if min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]) > 0.5 and min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]) > 0.5:
                bad.append(f"overlap {k}/{j}")
    return bad


def evaluate(L):
    R = L["rects"]
    fl = [eval_flow(L, f) for f in FLOWS]
    xs = [r[0] for r in R.values()] + [r[0] + r[2] for r in R.values()]
    ys = [r[1] for r in R.values()] + [r[1] + r[3] for r in R.values()]
    bbox = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    blk = sum(r[2] * r[3] for r in R.values()) / 1e6
    hub_mm2 = (HUB[1] - HUB[0]) * (TOP_LIMIT - BK_SEL[1] - BK_SEL[3]) / 1e6
    roads = L["roads"]
    road_cut = {k: (round(DEMAND[k] / (T_ROAD * roads[k]), 3) if roads[k] > 1 else None) for k in roads}
    own = [f for f in fl if f["name"] in OWNER_FLOWS]
    return dict(name=L["name"], key=L["key"], order=L["order"], rects={k: [round(v, 3) for v in r] for k, r in R.items()},
                checks=checks(L), bbox_um=[round(v, 1) for v in bbox], bbox_mm2=round(bbox[2] * bbox[3] / 1e6, 1),
                blocks_mm2=round(blk, 1), cluster_fill=round(blk / (bbox[2] * bbox[3] / 1e6), 3),
                hub_mm2=round(hub_mm2, 1), hub_whitespace=round(1 - blk / hub_mm2, 3), roads_um=roads, road_cut=road_cut,
                flows=fl, worst_owner_flow_cut=max((f["cut"] for f in own if f["cut"] is not None), default=None),
                worst_flow_cut=max((f["cut"] for f in fl if f["cut"] is not None), default=None),
                structural_turns=[f["name"] for f in fl if f.get("face_b") == "TURN"],
                turns=[f["name"] for f in fl if not f["direct"]],
                relays_owner_flows=sum(f["relays"] for f in own), relays_all=sum(f["relays"] for f in fl),
                bit_mm=sum(f["bit_mm"] for f in fl), bit_mm_owner=sum(f["bit_mm"] for f in own))


def layouts():
    return [c5_layout(), vmc_layout(), vmc2_layout(), vmc3_layout(), vmsq_layout()]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    res = [evaluate(L) for L in layouts()]
    for r in res:
        print(f"== {r['name']}  bbox {r['bbox_um'][2]:.0f}x{r['bbox_um'][3]:.0f}  roads {r['roads_um']} cut {r['road_cut']}  "
              f"turns {r['structural_turns']} worst owner cut {r['worst_owner_flow_cut']}  relays {r['relays_owner_flows']}/{r['relays_all']}  "
              f"bit.mm {r['bit_mm']}  checks {r['checks']}")
        for f in r["flows"]:
            print(f"   {f['name']:16s} {f['bits']:6d} {f['face_a']}->{f['face_b']:4s} win {f['window_um']:8.1f} "
                  f"gap {f['gap_um']:7.1f} cut {str(f['cut']):8s} relays {f['relays']} {f.get('status', '')}")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(dict(schema="opentallas.s81.hub_vm_centred.v1", hub_x_um=HUB, demand_bits=DEMAND,
                                     tracks=dict(EW=T_EW, NS=T_NS, road=T_ROAD), layouts=res), indent=1) + "\n")


if __name__ == "__main__":
    main()
