#!/usr/bin/env python3
"""Declared data landing islands (CLOCK-KV-R22, COORD RULING CLOCK-KV-R21 04:02 ASK1).

A landing island is a small DIE-TOP-owned std-cell reservation inside a partition type's frame, at the face pin of an
ft slot / bus input, that holds die-top hold cells (HB4, METHODOLOGY 12.4a a1 data hold buffers) for a seam whose
receiver AND sender are hard partitions without a P&R kit (KV: the PHY->PHY ft0 relay kv3_phy_v1 -> kv3_phy_v1), so
neither the receiver input (default die_sta hold demand placement) nor the sender output stage (sender-side rule,
CLOCK-KV-R21) can host the demand.  Like clock.die_islands_um it is a uniform per-type physical reservation (every
instance of the type gets it; the demand is type-hardened = worst instance), not extra tile IO; the hard partition's
abstract must leave the rect free of OBS (owner of the macro view).

Plan form (partition_types[T].landing_islands[]):
  {name, port (<slot>_i | input bus), rect_um [x0,y0,x1,y1] type frame, cells {lib_cell: count}, owner "die_top",
   demand {source, sha256, k, bits, ff_hold_ps}, note}
check(P) -> [error strings] (G0, via check.py):
  rect on the ASAP7 site/row grid (0.054 / 0.27), inside the outline, within FACE_REACH_UM of the port's face,
  no overlap with clock.die_islands_um / hard cores / another landing island, capacity (sites) >= cells x width,
  port is an input of the type, cells = bits x k of the declared demand, owner die_top.
propose(...) builds the declared island at the port's face centre window (CLOCK-KV-R22 plan delta)."""
import math

SITE_X, ROW_Y = 0.054, 0.27
FACE_REACH_UM = 4.32            # island edge to the port's face (the island lands the bit before the pin register)
CELL_SITES = {"HB4xp67_ASAP7_75t_R": 7}     # 0.1021 um2 / 0.27 row = 0.378 um = 7 sites
CELL_GAP_SITES = 1
FACES = ("N", "S", "E", "W")


def _on(v, g):
    return abs(v / g - round(v / g)) < 1e-6


def _overlap(a, b):
    return a[0] < b[2] - 1e-9 and b[0] < a[2] - 1e-9 and a[1] < b[3] - 1e-9 and b[1] < a[3] - 1e-9


def capacity(rect, cell):
    w = int(round((rect[2] - rect[0]) / SITE_X))
    rows = int(round((rect[3] - rect[1]) / ROW_Y))
    per = CELL_SITES[cell] + CELL_GAP_SITES
    return rows * (w // per)


def port_face(t, port):
    """(face, kind) of an input port of the type: ft slot '<s>_i' -> in_face, input bus -> its face (if declared)."""
    if port.endswith("_i"):
        for s in t.get("ft_slots", []):
            if s["name"] == port[:-2]:
                return s["in_face"], "ft_slot"
    for b in t.get("buses", []):
        if b["name"] == port and b.get("dir") == "in":
            return b.get("face"), "bus"
    return None, None


def face_dist(rect, face, W, H):
    return {"N": H - rect[3], "S": rect[1], "W": rect[0], "E": W - rect[2]}[face]


def check(raw):
    errs = []
    for tn, t in raw["partition_types"].items():
        isl = t.get("landing_islands") or []
        if not isl:
            continue
        W, H = t["outline_um"]
        others = [("die clock island", r) for r in (t.get("clock") or {}).get("die_islands_um", [])]
        for h in t.get("hard_cores", []) or []:
            ox, oy = h["origin_um"]; w, hh = h["outline_um"]
            if h.get("orient") in ("R90", "R270", "MXR90", "MYR90"):
                w, hh = hh, w
            others.append((f"hard core {h['inst']}", [ox, oy, ox + w, oy + hh]))
        seen = []
        for i in isl:
            n, r = i.get("name"), i.get("rect_um")
            tag = f"type {tn} landing island {n}"
            if not (isinstance(r, list) and len(r) == 4 and r[0] < r[2] and r[1] < r[3]):
                errs.append(f"{tag}: invalid rect"); continue
            if not all(_on(r[k], SITE_X if k in (0, 2) else ROW_Y) for k in range(4)):
                errs.append(f"{tag}: rect {r} off the site/row grid ({SITE_X}/{ROW_Y})")
            if not (r[0] >= -1e-9 and r[1] >= -1e-9 and r[2] <= W + 1e-9 and r[3] <= H + 1e-9):
                errs.append(f"{tag}: rect outside the type outline")
            face, kind = port_face(t, i.get("port", ""))
            if face not in FACES:
                errs.append(f"{tag}: port {i.get('port')} is not an input ft slot/bus with a face")
            elif face_dist(r, face, W, H) > FACE_REACH_UM + 1e-9:
                errs.append(f"{tag}: {face_dist(r, face, W, H):.3f} um from the {face} face of {i['port']} "
                            f"(> {FACE_REACH_UM})")
            for what, o in others + seen:
                if _overlap(r, o):
                    errs.append(f"{tag}: overlaps {what}")
            seen.append((f"landing island {n}", r))
            if i.get("owner") != "die_top":
                errs.append(f"{tag}: owner must be die_top")
            cells = i.get("cells") or {}
            if not cells or any(c not in CELL_SITES for c in cells):
                errs.append(f"{tag}: cells must be declared hold cells {sorted(CELL_SITES)}"); continue
            dm = i.get("demand") or {}
            need = sum(cells.values())
            if dm.get("bits") is None or dm.get("k") is None or int(dm["bits"]) * int(dm["k"]) != need:
                errs.append(f"{tag}: cells {need} != demand bits x k ({dm.get('bits')} x {dm.get('k')})")
            if not (isinstance(dm.get("sha256"), str) and len(dm["sha256"]) == 64):
                errs.append(f"{tag}: demand lacks the source sha256")
            cap = sum(capacity(r, c) for c in cells) / max(1, len(cells))
            if cap < need:
                errs.append(f"{tag}: capacity {cap} cells < {need}")
    return errs


def propose(t, port, window_um, bits, k, demand, cell="HB4xp67_ASAP7_75t_R", name=None, inset_rows=2):
    """the declared island for `port` of type t: centred on the port window (type frame, along the face), inset
    `inset_rows` rows from the face, sized to the smallest site/row rect >= 3 rows holding bits x k cells."""
    W, H = t["outline_um"]
    face, _ = port_face(t, port)
    need = bits * k
    rows = 3
    per_row = math.ceil(need / rows)
    w_sites = max(45, per_row * (CELL_SITES[cell] + CELL_GAP_SITES))
    c = (window_um[0] + window_um[1]) / 2
    if face in ("N", "S"):
        x0 = math.floor((c - w_sites * SITE_X / 2) / SITE_X + 1e-9) * SITE_X
        x1 = x0 + w_sites * SITE_X
        if face == "N":
            y1 = math.floor(H / ROW_Y + 1e-9) * ROW_Y - inset_rows * ROW_Y
            y0 = y1 - rows * ROW_Y
        else:
            y0 = inset_rows * ROW_Y
            y1 = y0 + rows * ROW_Y
    else:
        raise ValueError("E/W face islands not needed yet (CLOCK-KV-R22)")
    r = [round(v, 4) for v in (x0, y0, x1, y1)]
    return dict(name=name or f"{port}_hold", port=port, rect_um=r, cells={cell: need}, owner="die_top",
                demand=dict(demand, bits=bits, k=k),
                note=("CLOCK-KV-R22 declared landing island (COORD RULING CLOCK-KV-R21 ASK1): die-top HB4 data hold "
                      "cells for the hard->hard seam into this input (no P&R kit on either side); type-hardened"))
