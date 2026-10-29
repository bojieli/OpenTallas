#!/usr/bin/env python3
"""DIE-HEAD-26 hk5_ctl plan event (COORD 10-29 rulings: hd_ctl crop + ft strips; hd_host/hd_mesh join the same event).

Crop the low-fill 1442.88 x 1226.88 slot types hd_ctl / hd_host / hd_mesh to a core rectangle anchored at the type-frame
origin (SW in type frame) that keeps every bus window it already touches, and fill the rest of the old slot with ft strip
types that carry the remaining slot-face windows to the core faces.  Every old slot-boundary window keeps its die
coordinate (strip faces lie on the old slot edges), so NO neighbour pin moves.  The part of the old slot outside core and
strips becomes a die channel.  Latency rows are regenerated with schema.Plan.lane_latency (the only source).

usage: gen_hk5_ctl.py BASE_PLAN.json OUT_PLAN.json REGIONS_IN.json REGIONS_OUT.json REPORT.json   (run from a repo root)
"""
import copy
import json
import math
import sys

sys.path.insert(0, "tools/die_plan")
import schema  # noqa: E402

G = 8.64
REACH = 364.0          # 0.9 x 405 (G0C reach.py margin)

# ------------------------------------------------------------------ the event (type frame, um)
# core: kept rect [0,0,W,H].  strips: name -> rect, moved core buses -> (strip, new core face, new core window or None=same)
EVENT = {
    "hd_ctl": dict(
        core=(587.52, 518.4),
        strips={"n": (0.0, 518.4, 1296.0, 1226.88), "e": (587.52, 371.52, 1442.88, 475.2)},
        move={"n_tx_o": ("e", "E", None), "n_rx_i": ("e", "E", None),
              "lepf_o0": ("n", "N", [8.64, 28.64]), "unit_o0": ("n", "N", [38.64, 58.74]),
              "ctrl_i0": ("n", "N", [68.74, 88.74]), "lep_fault_i": ("n", "N", [98.74, 118.84]),
              "lw_i": ("n", "N", [128.84, 148.94])},
        ft={"w3u": "n", "w3d": "n"}),
    "hd_host": dict(
        core=(1296.0, 570.24),
        strips={"n": (0.0, 570.24, 1442.88, 1226.88)},
        move={"h_tx_i": ("n", "N", None), "h_rx_o": ("n", "N", None)},
        ft={"au": "n", "ad": "n", "bu": "n", "bd": "n"}),
    "hd_mesh": dict(
        core=(604.8, 1226.88),
        strips={"e": (604.8, 371.52, 1442.88, 457.92)},
        move={"m_tx_i": ("e", "E", None), "m_rx_o": ("e", "E", None)},
        ft={}),
}
LAYERS = {"W": ["M4", "M6"], "E": ["M4", "M6"], "N": ["M5", "M7"], "S": ["M5", "M7"]}
OPP = {"W": "E", "E": "W", "N": "S", "S": "N"}


def r2(x):
    return round(x, 4)


def face_point(face, w, rect):
    """centre of window w on face of rect (x0,y0,x1,y1), type frame"""
    x0, y0, x1, y1 = rect
    m = (w[0] + w[1]) / 2.0
    return {"W": (x0, m), "E": (x1, m), "S": (m, y0), "N": (m, y1)}[face]


def to_local(face, w, rect):
    """window along a face of the old slot (type frame) -> window in the strip frame"""
    x0, y0 = rect[0], rect[1]
    off = y0 if face in ("W", "E") else x0
    return [r2(w[0] - off), r2(w[1] - off)]


def place(part, rect, W, H, name, tname):
    """instance of a sub-rect (type frame) of a placed part with the same orient (origin = lower-left of bbox)"""
    ox, oy = part["origin_um"]
    o = part["orient"]
    a, c, b, d = rect
    x = ox + a if o in ("R0", "MX") else ox + W - b
    y = oy + c if o in ("R0", "MY") else oy + H - d
    q = {"name": name, "type": tname, "origin_um": [r2(x), r2(y)], "orient": o}
    return q


def inside(pt, rect):
    return rect[0] <= pt[0] <= rect[2] and rect[1] <= pt[1] <= rect[3]


def main(base, outp, reg_in, reg_out, repp):
    P = json.load(open(base))
    raw0 = copy.deepcopy(P)
    lat0 = {k: v["cycles"] for k, v in P["latency"]["lanes"].items()}
    T = P["partition_types"]
    ports = {p["id"]: p for p in P["ports"]}
    lanes = {l["id"]: l for l in P["lanes"]}
    regions = json.load(open(reg_in))
    rep = dict(event="hk5_ctl", types={}, new_parts=[], channels=[], latency_changed={})
    for tn, ev in EVENT.items():
        t = T[tn]
        W, H = t["outline_um"]
        Wc, Hc = ev["core"]
        core_rect = (0.0, 0.0, Wc, Hc)
        buses = {b["name"]: b for b in t["buses"]}
        slots = {s["name"]: s for s in t.get("ft_slots", [])}
        strips = {}
        for sn, rect in ev["strips"].items():
            stn = f"{tn}_{sn}"
            sx, sy = rect[2] - rect[0], rect[3] - rect[1]
            strips[sn] = dict(type=stn, rect=rect, t={
                "module": f"ot_s81hd_{tn[3:]}_{sn}strip", "outline_um": [r2(sx), r2(sy)], "hard": False, "cells": 0,
                "contents": [],
                "clock": {"tap_um": [r2(sx / 2), r2(sy / 2)], "layer": "M9", "insertion_ps": 450, "insertion_ff_ps": 380,
                          "tap_mode": "density", "tap_radius_um": 250},
                "reset": {"sync_stages": 2}, "buses": [], "ft_slots": [],
                "note": f"DIE-HEAD-26 hk5_ctl: ft strip of the old {tn} slot (crop to core {Wc}x{Hc}); carries the old "
                        f"slot-face windows to the core faces; no neighbour pin moves."})
        # existing ft slots -> strips (same windows, strip frame)
        for sl, sn in ev["ft"].items():
            s = copy.deepcopy(slots.pop(sl))
            rect = strips[sn]["rect"]
            for k, f in (("in_window_um", s["in_face"]), ("out_window_um", s["out_face"])):
                p0 = face_point(f, s[k], (0, 0, W, H))
                assert inside(p0, rect), (tn, sl, k, p0, rect)
                s[k] = to_local(f, s[k], rect)
            strips[sn]["t"]["ft_slots"].append(s)
            strips[sn].setdefault("ft_names", []).append(sl)
        # moved core buses -> new ft slot in the strip + new core window
        moved = {}
        for bn, (sn, cface, cwin) in ev["move"].items():
            b = buses[bn]
            rect = strips[sn]["rect"]
            oface, owin = b["face"], list(b["window_um"])
            assert inside(face_point(oface, owin, (0, 0, W, H)), rect), (tn, bn)
            nwin = list(cwin) if cwin else owin
            # strip-side face touching the core
            sface = OPP[cface]
            slot_name = bn.rsplit("_", 1)[0] + "_ft"
            outer = dict(face=oface, win=to_local(oface, owin, rect))
            inner = dict(face=sface, win=to_local(sface, nwin, rect))
            pa = face_point(oface, owin, (0, 0, W, H))
            pb = face_point(cface, nwin, core_rect)
            L = abs(pa[0] - pb[0]) + abs(pa[1] - pb[1])
            st = max(1, math.ceil(L / REACH))   # check.py: route / stations <= 405 and G0C hop <= 0.9 x 405
            if b["dir"] == "out":      # core -> strip(in at core face) -> out at old face
                fi, fo = inner, outer
            else:
                fi, fo = outer, inner
            s = {"name": slot_name, "in_face": fi["face"], "out_face": fo["face"], "width": b["width"], "stations": st,
                 "in_window_um": fi["win"], "out_window_um": fo["win"], "order": b.get("order", "lsb_low")}
            if fi["face"] == OPP[fo["face"]]:
                s["layers"] = list(b.get("layers") or LAYERS[fi["face"]])
            strips[sn]["t"]["ft_slots"].append(s)
            b["face"], b["window_um"] = cface, nwin
            b["layers"] = list(LAYERS[cface]) if cwin else b.get("layers", LAYERS[cface])
            moved[bn] = dict(strip=sn, slot=slot_name, dir=b["dir"], L_um=round(L, 1), stations=st)
        t["ft_slots"] = list(slots.values())
        if not t["ft_slots"]:
            t.pop("ft_slots")
        t["outline_um"] = [Wc, Hc]
        t["note"] = t.get("note", "") + f" | DIE-HEAD-26 hk5_ctl: cropped from the {W}x{H} slot to {Wc}x{Hc} (type-frame SW)," \
                                        f" rest = ft strips {sorted(s['type'] for s in strips.values())} + die channel"
        # hard cores must stay inside the core
        for h in t.get("hard_cores", []):
            x, y = h["origin_um"]
            w, hh = h["outline_um"]
            assert x + w <= Wc and y + hh <= Hc, (tn, h["inst"])
        # clock tap / islands / reset taps: keep inside core, route the rest to the strip holding them, else drop
        ck = t["clock"]
        if not inside(ck["tap_um"], core_rect):
            ck["tap_um"] = [r2(round(Wc / 2 / G) * G), r2(round(Hc / 2 / G) * G)]
        isl = ck.get("die_islands_um", [])
        keep, gone = [], []
        for r in isl:
            c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            if inside(c, core_rect) and r[2] <= Wc and r[3] <= Hc:
                keep.append(r)
                continue
            for sn, s in strips.items():
                R = s["rect"]
                if R[0] <= r[0] and r[2] <= R[2] and R[1] <= r[1] and r[3] <= R[3]:
                    s["t"]["clock"].setdefault("die_islands_um", []).append(
                        [r2(r[0] - R[0]), r2(r[1] - R[1]), r2(r[2] - R[0]), r2(r[3] - R[1])])
                    break
            else:
                gone.append(r)
        if isl:
            ck["die_islands_um"] = keep
        rs = t["reset"]
        if rs.get("local_taps_um"):
            kt = [q for q in rs["local_taps_um"] if q[0] <= Wc - 4.32 and q[1] <= Hc - 4.32]
            rs["local_taps_um"] = kt
        rep["types"][tn] = dict(old=[W, H], core=[Wc, Hc], moved=moved, ft_moved={k: v for k, v in ev["ft"].items()},
                                islands_dropped=gone, reset_taps_kept=len(rs.get("local_taps_um", [])))
        for s in strips.values():
            T[s["type"]] = s["t"]
        # instances, ports, lanes, channels, regions
        for part in [q for q in P["partitions"] if q["type"] == tn]:
            pn = part["name"]
            inst = {}
            part0 = dict(part)
            cq = place(part0, core_rect, W, H, pn, tn)          # mirrored instances: the kept core moves its origin
            if cq["origin_um"] != part["origin_um"]:
                rep.setdefault("core_origin_moved", {})[pn] = [part["origin_um"], cq["origin_um"]]
            part["origin_um"] = cq["origin_um"]
            for sn, s in strips.items():
                q = place(part0, s["rect"], W, H, f"{pn}_{sn}strip", s["type"])
                P["partitions"].append(q)
                inst[sn] = q["name"]
                rep["new_parts"].append(q)
                reg = regions["part_region"].get(pn)
                regions["part_region"][q["name"]] = reg
            # die channels: old slot minus core minus strips, as rects (type frame) -> die
            for cr in free_rects((0, 0, W, H), [core_rect] + [s["rect"] for s in strips.values()]):
                q = place(part0, cr, W, H, "x", "x")
                x, y = q["origin_um"]
                ch = {"rect_um": [x, y, r2(x + cr[2] - cr[0]), r2(y + cr[3] - cr[1])],
                      "reason": f"DIE-HEAD-26 hk5_ctl freed slot of {pn} ({tn} crop)"}
                P["die"]["channels"].append(ch)
                rep["channels"].append(ch)
            # ft slot ports: part -> strip instance
            for p in P["ports"]:
                for end in ("src", "dst"):
                    e = p[end]
                    if e["part"] != pn:
                        continue
                    base_ = e["bus"].rsplit("_", 1)[0]
                    for sn, s in strips.items():
                        if base_ in s.get("ft_names", []):
                            e["part"] = inst[sn]
            # moved buses: split each port through the strip slot
            for bn, m in moved.items():
                hit = [p for p in list(P["ports"]) if (p["src"]["part"] == pn and p["src"]["bus"] == bn)
                       or (p["dst"]["part"] == pn and p["dst"]["bus"] == bn)]
                assert len(hit) == 1, (pn, bn, hit)
                p = hit[0]
                sp = inst[m["strip"]]
                nid = p["id"] + f"__h5{m['strip']}"
                if m["dir"] == "out":   # core.bn -> strip.slot_i (new) ; strip.slot_o -> nbr (old id)
                    new = {"id": nid, "src": {"part": pn, "bus": bn}, "dst": {"part": sp, "bus": m["slot"] + "_i"},
                           "width": p["width"], "kind": p["kind"]}
                    p["src"] = {"part": sp, "bus": m["slot"] + "_o"}
                    before = True
                else:                   # nbr -> strip.slot_i (old id) ; strip.slot_o -> core.bn (new)
                    new = {"id": nid, "src": {"part": sp, "bus": m["slot"] + "_o"}, "dst": {"part": pn, "bus": bn},
                           "width": p["width"], "kind": p["kind"]}
                    p["dst"] = {"part": sp, "bus": m["slot"] + "_i"}
                    before = False
                P["ports"].append(new)
                ln = [l for l in P["lanes"] if p["id"] in l["ports"]]
                assert len(ln) == 1, (p["id"], ln)
                L = ln[0]["ports"]
                i = L.index(p["id"])
                L.insert(i if before else i + 1, nid)
    # latency (only source)
    pl = schema.Plan(P)
    P["latency"]["lanes"] = {lid: pl.lane_latency(lid) for lid in [l["id"] for l in P["lanes"]]}
    for k, v in P["latency"]["lanes"].items():
        if lat0.get(k) != v["cycles"]:
            rep["latency_changed"][k] = [lat0.get(k), v["cycles"]]
    P["note"] = P.get("note", "") + " | DIE-HEAD-26 hk5_ctl: hd_ctl/hd_host/hd_mesh cropped to cores + ft strips (no neighbour pin moves)"
    json.dump(P, open(outp, "w"), indent=1)
    json.dump(regions, open(reg_out, "w"), indent=1)
    json.dump(rep, open(repp, "w"), indent=1)
    print(json.dumps({k: rep[k] for k in ("latency_changed",)}, indent=0))
    for tn, r in rep["types"].items():
        print(tn, r["old"], "->", r["core"], {k: (v["stations"], v["L_um"]) for k, v in r["moved"].items()}, "islands dropped", len(r["islands_dropped"]))


def free_rects(slot, used):
    """slot minus used rects (axis-aligned) as a list of maximal-row rectangles on the used-rect grid"""
    xs = sorted({slot[0], slot[2]} | {r[0] for r in used} | {r[2] for r in used})
    ys = sorted({slot[1], slot[3]} | {r[1] for r in used} | {r[3] for r in used})
    cells = []
    for j in range(len(ys) - 1):
        row = []
        for i in range(len(xs) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if not any(r[0] < cx < r[2] and r[1] < cy < r[3] for r in used):
                row.append(i)
        # merge consecutive x cells
        k = 0
        while k < len(row):
            s = k
            while k + 1 < len(row) and row[k + 1] == row[k] + 1:
                k += 1
            cells.append((xs[row[s]], ys[j], xs[row[k] + 1], ys[j + 1]))
            k += 1
    return cells


if __name__ == "__main__":
    main(*sys.argv[1:6])
