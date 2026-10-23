#!/usr/bin/env python3
# FROZEN (ROOT-MERGE2 10-23, COORD batch 15): byte copy of tools/ref_tile/tile_plan.py at main 62e70058c, the planner of
# recipe-5 kits generated before TILE-FLOW2 (tile_plan.planner_version 1, 3 pins/um).  ref_tile.py dispatches to it so
# an in-flight kit regenerates byte-identically; never edit it -- new behaviour goes in tile_plan.py (version 2).
"""Content-driven tile planning (TILE-FLOW 2026-10-23, coordinator tile review of 109 unclosed tiles).

The review found the same failures on 65 standard-cell tiles: outlines 3-10x larger than their content (2-15 % fill),
pin registers floating 300-630 um from their pins, thousands of unregistered boundary pins, macros whose pins face away
from their logic with wide fixed channels, and one logic blob in the middle with pins on four faces.  Every one of them
had a hand-written spec "outline" and hand "at" macro coordinates.  This module derives those numbers the way a
hierarchical floorplan does (content-driven sizing, pin-driven shaping, edge macros facing their logic):

  content_outline()   area = std / target util + macro footprints (with halos) + pin-register band; aspect from the
                      per-face pin demand (<= PIN_DENSITY pins/um on every face, aspect <= ASPECT_MAX); grown until the
                      macro plan fits; checked against the parent slot (too small -> slot_change_request text)
  plan_macros()       macro array: N-S abutted columns hung from the face with the least pin demand, every pin face
                      oriented into a logic channel sized from its pin count (channel_um), compact rows choice
  fence_depth_um()    pin-register band depth per face (physical/common_flow/pin_reg_face_fence.tcl builds the bands)
  outline_flag()      audit / gate: a spec outline > OUTLINE_RATIO_MAX x the computed one without "outline_reason"

Pure Python, no OpenROAD; ref_tile.py (gen), pre_route_gate.py and outline_audit.py call it.
"""
from __future__ import annotations

import math
import re

TARGET_UTIL = 0.65          # std-cell utilisation of the logic area (industry 0.60-0.70)
UTIL_RANGE = (0.60, 0.70)
PIN_DENSITY = 3.0           # pins / um per face (owner review 10-23: <= ~3)
ASPECT_MAX = 2.0            # no long-thin tiles (owner 10-16 / tile checklist 10-17)
FF_AREA_UM2 = 0.2916        # DFFHQNx1_ASAP7_75t_R 1.08 x 0.27
BAND_FILL = 0.50            # pin-register band fill (flops only, staggered columns)
BAND_MIN_UM = 4.32          # 16 rows
BAND_MAX_UM = 14.04         # 52 rows: stays inside the 20 um macro keep-off of a pin face (minus the 5.4 um halo)
ROW_UM = 0.27
OUTLINE_RATIO_MAX = 1.3     # spec outline area / computed area above this needs "outline_reason"
CORE_MARGIN = 2.16
CHANNEL_MIN_UM = 20.0       # the gate's channel rule (ref_tile.CHANNEL_UM)
PIN_EDGE_UM = 20.0          # the gate's macro keep-off of a pin face (ref_tile.PIN_EDGE_UM)
KEEP_SLACK_UM = 2.16        # added to every planned keep-off / channel: lattice snapping + track shift never cut one
ABUT_PITCH_UM = 0.024       # abutted N-S stack: pitch = array height + 0.024 (ref_tile abutted_stack)
CH_TRACK_UM = 0.048         # channel routing pitch (M3 0.036 / M5 0.048: the coarser one)
CH_LAYERS = 2               # vertical / horizontal layers of a channel under the M5 cap
CH_UTIL = 0.5               # channel track utilisation
CH_ESCAPE_FRAC = 0.5        # share of a channel's facing macro pins whose wires run ALONG the channel (the rest end
                            # on logic placed in the channel itself)
GRID = 2.16                 # tile outline lattice (ref_tile.GRID_Y)
FACES = ("N", "S", "E", "W")
OPP = {"N": "S", "S": "N", "E": "W", "W": "E"}


def snap_up(v: float, g: float = GRID) -> float:
    return round(math.ceil(v / g - 1e-9) * g, 4)


# ------------------------------------------------------------------------------------------------ pin demand
def port_widths(sources_text: dict, top: str, params: dict | None = None) -> dict | None:
    """{port: width} from the top's ANSI header with the spec parameters (closure_loop/submit_lint.top_ports, the
    parser pin_fit trusts), None when unresolved.  sources_text: {path: text}"""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "closure_loop"))
    import submit_lint as SL  # noqa: E402
    for _path, text in sources_text.items():
        if not re.search(r"\bmodule\s+(?:automatic\s+)?" + re.escape(top) + r"\b", text):
            continue
        try:
            ports = SL.top_ports(text, top, {k: str(v) for k, v in (params or {}).items()})
            return {n: w for n, w, _lsb in ports} or None
        except Exception:  # noqa: BLE001
            return non_ansi_widths(text, top)
    return None


_DECL = re.compile(r"^\s*(input|output|inout)\s+(?:wire\s+|reg\s+|logic\s+)?(?:signed\s+)?"
                   r"(?:\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*)?([A-Za-z_][\w$]*(?:\s*,\s*[A-Za-z_][\w$]*)*)\s*;", re.M)


def non_ansi_widths(text: str, top: str) -> dict | None:
    """{port: width} of a NON-ANSI top (a mapped / generated netlist: `module top (a, b); input [7:0] a; ...`), literal
    ranges only; None when the header is not of that form"""
    m = re.search(r"\bmodule\s+" + re.escape(top) + r"\s*\(([^;]*)\)\s*;", text)
    if not m:
        return None
    names = [n.strip() for n in m.group(1).split(",") if n.strip()]
    if not names or any(not re.fullmatch(r"[A-Za-z_][\w$]*", n) for n in names):
        return None
    end = text.find("endmodule", m.end())
    body = text[m.end(): end if end > 0 else len(text)]
    out = {}
    for d in _DECL.finditer(body):
        w = abs(int(d.group(2)) - int(d.group(3))) + 1 if d.group(2) is not None else 1
        for n in d.group(4).split(","):
            out[n.strip()] = w
    return out if all(n in out for n in names) else None


def face_demand(spec: dict, widths: dict | None) -> tuple[dict, bool]:
    """({face: pin bits}, exact) of a spec's pin plan; clock ports excluded.  Unknown widths count 1 (exact False)."""
    clocks = {spec.get("clock_port")} | set(spec.get("clock_ports") or [])
    out, exact = {f: 0 for f in FACES}, widths is not None
    for f, names in (spec.get("pins") or {}).items():
        if f not in FACES:
            continue
        for n in names or []:
            if n in clocks:
                continue
            w = (widths or {}).get(n)
            if w is None:
                exact = False
                w = 1
            out[f] += int(w)
    return out, exact


def fence_depth_um(n_regs: int, face_len_um: float, ff_area: float = FF_AREA_UM2) -> float:
    """pin-register band depth of one face: the face's register area at BAND_FILL, in whole rows, BAND_MIN..BAND_MAX"""
    if n_regs <= 0 or face_len_um <= 0:
        return 0.0
    d = n_regs * ff_area / (BAND_FILL * face_len_um)
    d = math.ceil(d / ROW_UM - 1e-9) * ROW_UM
    return round(min(BAND_MAX_UM, max(BAND_MIN_UM, d)), 4)


# ------------------------------------------------------------------------------------------------ macros
def macro_pin_faces(tm: dict, uses=("SIGNAL", "CLOCK", None, "")) -> dict:
    """{face: pin count} of a LEF macro (check_macro_track_alignment.parse_lef dict, nm) in R0; uses=None: every use
    (power / ground too: the bare-face test of an E-W abutment)"""
    W, H = tm["W"], tm["H"]
    c = {f: 0 for f in FACES}
    for p in tm["pins"]:
        if uses is not None and p.get("use") not in uses:
            continue
        hit = set()
        for _l, (x0, y0, x1, y1) in p["rects"]:
            if x0 <= 200:
                hit.add("W")
            if x1 >= W - 200:
                hit.add("E")
            if y0 <= 200:
                hit.add("S")
            if y1 >= H - 200:
                hit.add("N")
        for f in hit:
            c[f] += 1
    return c


# orientation that maps the LEF face `lef` onto tile direction `want` (R0 / MX / MY / R180 only: track-safe, abutment-safe)
_ORIENT_FACE = {"R0": {"N": "N", "S": "S", "E": "E", "W": "W"}, "MY": {"N": "N", "S": "S", "E": "W", "W": "E"},
                "MX": {"N": "S", "S": "N", "E": "E", "W": "W"}, "R180": {"N": "S", "S": "N", "E": "W", "W": "E"}}


def orient_for(lef_face: str, want: str) -> str:
    for o in ("R0", "MY", "MX", "R180"):
        if _ORIENT_FACE[o][lef_face] == want:
            return o
    raise ValueError(f"no R0/MY/MX/R180 orientation maps {lef_face} to {want}")


def face_after(o: str, lef_face: str) -> str:
    return _ORIENT_FACE[o][lef_face]


def channel_um(facing_pins: int) -> float:
    """channel between two macro faces that carry pins, from the routing demand of the pins facing it"""
    need = facing_pins * CH_ESCAPE_FRAC * CH_TRACK_UM / (CH_LAYERS * CH_UTIL)
    return max(CHANNEL_MIN_UM, round(math.ceil(need / 0.432 - 1e-9) * 0.432, 4)) + KEEP_SLACK_UM


def macro_edge(demand: dict, axis: str) -> str:
    """tile face the macro array hangs from: for N-S columns (W / E pinned arrays) the N or S face with the lower pin
    demand (ties: N)"""
    pref = ("N", "S") if axis == "WE" else ("W", "E")
    return min(pref, key=lambda f: (demand.get(f, 0), pref.index(f)))


def _sig_faces(tm: dict) -> set:
    """LEF faces that carry >= 10 % of the macro's signal pins"""
    c = macro_pin_faces(tm)
    tot = max(1, max(c.values()))
    return {f for f in FACES if c[f] and c[f] >= 0.1 * tot}


def _pins_only_at_sides(tm: dict, lef_face: str) -> bool:
    """every signal pin on the N / S LEF face also reaches a W / E side (ref_tile.abutted_stack's exemption)"""
    W, H = tm["W"], tm["H"]
    for p in tm["pins"]:
        if p.get("use") not in ("SIGNAL", "CLOCK"):
            continue
        for _l, (x0, y0, x1, y1) in p["rects"]:
            on = (y1 >= H - 200) if lef_face == "N" else (y0 <= 200)
            if on and not (x0 <= 200 or x1 >= W - 200):
                return False
    return True


def _stackable(tm: dict) -> bool:
    """N-S abutment allowed (ref_tile.abutted_stack)"""
    return _pins_only_at_sides(tm, "N") and _pins_only_at_sides(tm, "S")


_T_FACE = {"N": "E", "E": "N", "S": "W", "W": "S"}          # transpose (x, y) -> (y, x)
_T_ORIENT = {"R0": "R0", "MY": "MX", "MX": "MY", "R180": "R180"}


def _transpose_tm(tm: dict) -> dict:
    pins = [{**p, "rects": [(lay, (y0, x0, y1, x1)) for lay, (x0, y0, x1, y1) in p["rects"]]} for p in tm["pins"]]
    return {**tm, "W": tm["H"], "H": tm["W"], "pins": pins}


def plan_macros(W: float, H: float, macros: list, demand: dict, halo: float = 5.4, rows: int | None = None) -> dict:
    """Macro ARRAY plan: macros pinned on W / E faces (SRAM / ROM arrays) form N-S abutted COLUMNS of `rows` arrays;
    columns sit side by side with a LOGIC CHANNEL in front of every pin face, sized from the pins facing it
    (channel_um), and a 20 um gap where both faces are pin-free; the array hangs from the N or S face with the lower
    pin demand and is centred along it, so the logic is one band between the macro pins and the face pins.
    Single-face arrays are mirrored in pairs so two pin faces share one channel.  N / S pinned arrays: the same plan
    transposed (E-W rows).  macros: [{"w","h","tm","key"}] (um; tm = parse_lef dict, nm).  rows None: the most compact
    choice.  -> {"ok", "edge", "axis", "rows", "bbox", "need": [w, h] (outline the array needs), "placed": [{key, x, y,
    orient, pin_faces, col, abut_below}], "why"}.  Positions are pre-lattice: ref_tile snaps / track-aligns every column
    and keeps its N-S pitch, then re-runs the gate's geometry checks."""
    if not macros:
        return {"ok": True, "edge": None, "axis": None, "rows": 0, "bbox": None, "need": [0.0, 0.0], "placed": [],
                "why": "no macros"}
    sig = [_sig_faces(m["tm"]) for m in macros]
    if sum(1 for s in sig if s and s <= {"N", "S"}) > len(macros) / 2:
        tdem = {_T_FACE[f]: v for f, v in demand.items() if f in _T_FACE}
        tms = [{**m, "w": m["h"], "h": m["w"], "tm": _transpose_tm(m["tm"])} for m in macros]
        r = plan_macros(H, W, tms, tdem, halo, rows)
        for p in r["placed"]:
            p["x"], p["y"] = p["y"], p["x"]
            p["w"], p["h"] = p["h"], p["w"]
            p["orient"] = _T_ORIENT[p["orient"]]
            p["pin_faces"] = sorted(_T_FACE[f] for f in p["pin_faces"])
            p["abut_right"] = p.pop("abut_below")
            p["abut_below"] = False
        if r["bbox"]:
            x0, y0, x1, y1 = r["bbox"]
            r["bbox"] = [y0, x0, y1, x1]
        r["need"] = r["need"][::-1]
        r["edge"] = _T_FACE.get(r["edge"], r["edge"])
        r["axis"] = "NS"
        r["why"] = r["why"].replace("N-S columns", "E-W rows")
        return r
    if rows is None:
        best = None
        for n in range(1, len(macros) + 1):
            r = plan_macros(W, H, macros, demand, halo, n)
            nw, nh = max(W, r["need"][0]), max(H, r["need"][1])
            key = (round(nw * nh, 1), max(nw, nh) / min(nw, nh))
            if best is None or key < best[0]:
                best = (key, r)
        return best[1]
    pin_faces = {f for f in FACES if demand.get(f, 0) > 0}
    edge = macro_edge(demand, "WE")
    cols, cur = [], []          # columns of <= rows arrays, widest master first (abutted_stack needs only x overlap)
    order = sorted(range(len(macros)), key=lambda i: (-macros[i]["w"], macros[i]["tm"]["name"], i))
    for m, s in ((macros[i], sig[i]) for i in order):
        if cur and len(cur) >= rows:
            cols.append(cur)
            cur = []
        cur.append((m, s))
    if cur:
        cols.append(cur)
    spec_cols, k = [], 0
    for c in cols:
        m0, s0 = c[0]
        we = s0 & {"W", "E"}
        if we == {"W", "E"} or not we:
            o, faces = "R0", set(we)
        else:                    # single-face arrays alternate: pairs of pin faces share one channel
            want = "E" if k % 2 == 0 else "W"
            o = orient_for(next(iter(we)), want)
            faces = {want}
            k += 1
        cnt = macro_pin_faces(m0["tm"])
        per = {face_after(o, f): cnt[f] for f in ("W", "E")}
        stack = _stackable(m0["tm"])
        hts = [m["h"] for m, _ in c]
        h = sum(hts) + (len(hts) - 1) * (ABUT_PITCH_UM if stack else CHANNEL_MIN_UM)
        spec_cols.append({"items": c, "o": o, "faces": faces, "w": max(m["w"] for m, _ in c), "h": h,
                          "pins_w": per["W"] * len(c) if "W" in faces else 0,
                          "pins_e": per["E"] * len(c) if "E" in faces else 0, "stack": stack})
    gaps = []
    for a, b in zip(spec_cols, spec_cols[1:]):
        dem = a["pins_e"] + b["pins_w"]
        gaps.append(channel_um(dem) if dem else CHANNEL_MIN_UM + KEEP_SLACK_UM)
    lead = channel_um(spec_cols[0]["pins_w"]) if spec_cols[0]["pins_w"] else 0.0
    trail = channel_um(spec_cols[-1]["pins_e"]) if spec_cols[-1]["pins_e"] else 0.0
    kw = (PIN_EDGE_UM if "W" in pin_faces else (0.0 if lead else CHANNEL_MIN_UM)) + KEEP_SLACK_UM
    ke = (PIN_EDGE_UM if "E" in pin_faces else (0.0 if trail else CHANNEL_MIN_UM)) + KEEP_SLACK_UM
    aw = sum(c["w"] for c in spec_cols) + sum(gaps)
    ah = max(c["h"] for c in spec_cols)
    k_edge = (PIN_EDGE_UM if edge in pin_faces else CHANNEL_MIN_UM) + KEEP_SLACK_UM
    need_w = kw + lead + aw + trail + ke + 2 * CORE_MARGIN
    need_h = (k_edge + ah + CHANNEL_MIN_UM + KEEP_SLACK_UM + (PIN_EDGE_UM if OPP[edge] in pin_faces else 0.0)
              + 2 * CORE_MARGIN)
    x0c, y0c, x1c, y1c = CORE_MARGIN, CORE_MARGIN, W - CORE_MARGIN, H - CORE_MARGIN
    free = (x1c - x0c) - (kw + lead + aw + trail + ke)
    x = x0c + kw + lead + max(0.0, free / 2)
    placed = []
    for j, c in enumerate(spec_cols):
        y = (y1c - k_edge - c["h"]) if edge == "N" else (y0c + k_edge)
        for i, (m, _s) in enumerate(c["items"]):
            placed.append({"key": m.get("key"), "x": round(x, 4), "y": round(y, 4), "orient": c["o"],
                           "pin_faces": sorted(c["faces"]), "col": j, "w": m["w"], "h": m["h"],
                           "abut_below": bool(i and c["stack"])})
            y += m["h"] + (ABUT_PITCH_UM if c["stack"] else CHANNEL_MIN_UM)
        x += c["w"] + (gaps[j] if j < len(gaps) else 0.0)
    box = (min(p["x"] for p in placed), min(p["y"] for p in placed),
           max(p["x"] + p["w"] for p in placed), max(p["y"] + p["h"] for p in placed))
    ok = need_w <= W + 1e-6 and need_h <= H + 1e-6
    return {"ok": ok, "edge": edge, "axis": "WE", "rows": rows, "bbox": [round(v, 4) for v in box],
            "need": [round(need_w, 4), round(need_h, 4)], "placed": placed, "gaps": [round(g, 3) for g in gaps],
            "lead": round(lead, 3), "trail": round(trail, 3),
            "why": (f"{len(macros)} macros in {len(spec_cols)} N-S columns of <= {rows} (abutted) hung from the {edge} "
                    f"face; logic channels {', '.join(f'{g:.0f}' for g in [lead] + gaps + [trail])} um in front of the "
                    "pin faces")}


# ------------------------------------------------------------------------------------------------ outline
def content_outline(std_area: float, macros: list, demand: dict, util: float = TARGET_UTIL, halo: float = 5.4,
                    slot: tuple | None = None, pin_density: float = PIN_DENSITY) -> dict:
    """The tile outline from its content.  std_area: synthesized std-cell area (um2, the pin registers included);
    macros: [{"w","h","tm","key"}]; demand: {face: pin bits}.  -> {"w","h","bound","area_core","fill","breakdown",
    "pin_density", "macro_plan", "slot", "why"}.  Macro channels are logic area (their cells are counted once)."""
    if not UTIL_RANGE[0] - 1e-9 <= util <= UTIL_RANGE[1] + 1e-9:
        raise ValueError(f"tile_plan util {util} outside {UTIL_RANGE}")
    n_regs = sum(demand.values())
    reg_area = min(std_area, n_regs * FF_AREA_UM2)
    band = n_regs * FF_AREA_UM2 / BAND_FILL
    logic = max(std_area - reg_area, 0.0) / util
    mac = sum((m["w"] + 2 * halo) * (m["h"] + 2 * halo) for m in macros)
    core = logic + band + mac
    wmin = max(demand.get("N", 0), demand.get("S", 0)) / pin_density
    hmin = max(demand.get("E", 0), demand.get("W", 0)) / pin_density
    if wmin * hmin >= core:
        bound = "pins"
        w, h = max(wmin, 1.0), max(hmin, 1.0)
    else:
        bound = "area"
        r = (max(demand.get("N", 0), demand.get("S", 0)) + 1.0) / (max(demand.get("E", 0), demand.get("W", 0)) + 1.0)
        r = min(ASPECT_MAX, max(1.0 / ASPECT_MAX, r))
        w = math.sqrt(core * r)
        h = core / w
        if w < wmin:
            w, h = wmin, max(hmin, core / wmin)
            bound = "pins"
        if h < hmin:
            h, w = hmin, max(wmin, core / hmin)
            bound = "pins"
    W, H = snap_up(w + 2 * CORE_MARGIN), snap_up(h + 2 * CORE_MARGIN)
    plan = plan_macros(W, H, macros, demand, halo)
    if macros and not plan["ok"]:
        # the macro array fixes one side; the other keeps the content area (never below its own minimum)
        nw, nh = max(W, plan["need"][0]), max(H, plan["need"][1])
        if nw > W and nh == H:
            nh = max(H if bound == "pins" else 0.0, snap_up(hmin + 2 * CORE_MARGIN), plan["need"][1],
                     snap_up(core / (nw - 2 * CORE_MARGIN) + 2 * CORE_MARGIN))
        elif nh > H and nw == W:
            nw = max(W if bound == "pins" else 0.0, snap_up(wmin + 2 * CORE_MARGIN), plan["need"][0],
                     snap_up(core / (nh - 2 * CORE_MARGIN) + 2 * CORE_MARGIN))
        W, H = snap_up(nw), snap_up(nh)
        bound = "macros" if bound == "area" else bound
        plan = plan_macros(W, H, macros, demand, halo)
    capped = False
    if max(W, H) / min(W, H) > ASPECT_MAX:      # a pin- / macro-bound long-thin tile: widen (the low fill shows)
        capped = True
        if W > H:
            H = snap_up(W / ASPECT_MAX)
        else:
            W = snap_up(H / ASPECT_MAX)
        plan = plan_macros(W, H, macros, demand, halo)
    slot_v = None
    if slot:
        sw, sh = float(slot[0]), float(slot[1])
        if W <= sw + 1e-6 and H <= sh + 1e-6:
            slot_v = {"fits": True, "slot": [sw, sh], "slack_area": round(sw * sh / (W * H), 3)}
        else:
            slot_v = {"fits": False, "slot": [sw, sh], "need": [W, H],
                      "request": f"UNGRANTED: content outline {W:g} x {H:g} um does not fit slot {sw:g} x {sh:g}; "
                                 "parent slot must be re-derived (tile_plan.content_outline)"}
    dens = {f: round(demand.get(f, 0) / max(1e-9, (W if f in "NS" else H) - 2 * CORE_MARGIN), 2) for f in FACES}
    free = (W - 2 * CORE_MARGIN) * (H - 2 * CORE_MARGIN) - sum(m["w"] * m["h"] for m in macros)
    fill = std_area / max(1e-9, free)
    return {"w": W, "h": H, "bound": bound, "aspect_capped": capped, "area_core": round(core, 1),
            "fill": round(fill, 3),
            "breakdown": {"logic_um2": round(logic, 1), "band_um2": round(band, 1), "macro_um2": round(mac, 1),
                          "pin_regs": n_regs, "util": util},
            "pin_density": dens, "macro_plan": plan, "slot": slot_v,
            "why": (f"content: std {std_area:.0f}/{util} + band {band:.0f} ({n_regs} pin regs) + macros {mac:.0f} um2 "
                    f"-> {W:g} x {H:g} ({bound}-bound{', aspect capped' if capped else ''}, std fill {fill:.0%})")}


def outline_flag(spec_wh: tuple, comp: dict, spec: dict) -> tuple | None:
    """(severity, message) when the spec outline is > OUTLINE_RATIO_MAX x the content outline without an
    "outline_reason"; None otherwise"""
    sa = float(spec_wh[0]) * float(spec_wh[1])
    ca = comp["w"] * comp["h"]
    ratio = sa / ca if ca else 0.0
    if ratio <= OUTLINE_RATIO_MAX:
        return None
    if str(spec.get("outline_reason") or "").strip():
        return ("INFO", f"outline {spec_wh[0]:g} x {spec_wh[1]:g} is {ratio:.2f}x the content outline "
                        f"{comp['w']:g} x {comp['h']:g}; outline_reason: {str(spec['outline_reason'])[:160]}")
    return ("FAIL", f"outline {spec_wh[0]:g} x {spec_wh[1]:g} is {ratio:.2f}x the content outline {comp['w']:g} x "
                    f"{comp['h']:g} ({comp['why']}); drop the outline (tile_plan sizes it) or give \"outline_reason\"")
