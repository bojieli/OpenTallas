#!/usr/bin/env python3
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
PIN_DENSITY = 6.0           # pins / um per face, averaged over the face (COORD 10-23 02:33, was 3): only on a face whose
                            # pins alternate over >= 2 signal layers (face_pin_layers); a one-layer face keeps
                            # PIN_DENSITY_PER_LAYER
PIN_DENSITY_PER_LAYER = 3.0 # owner review 10-23: <= ~3 pins / um on one layer
PIN_WINDOW_UM = 10.0        # local density window (GEOM-REVIEW: <= 6 pins / um in any 10-um window of a face)
PIN_WINDOW_MAX = 6.0
PIN_TRACK_RATIO_MAX = 0.6   # pins / um over the face's routing tracks / um, both pin layers counted
PIN_PITCH_UM = {"M2": 0.036, "M3": 0.036, "M4": 0.048, "M5": 0.048, "M6": 0.064, "M7": 0.064}   # ASAP7
H_PIN_LAYERS = ("M4", "M6")             # E / W faces: horizontal layers (M2 carries the M1/M2 followpin rails)
V_PIN_LAYERS = ("M3", "M5", "M7")       # N / S faces: vertical layers, the top two under the cap
PIN_CORNER_UM = 1.0         # run_abi3_physical OT_PIN_CORNER_UM: balanced pins stay 1 um off each face corner
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
OVER_MACRO_UTIL = 0.45      # share of the over-macro layer's tracks the back-face wires may take (the PG stripes of the
                            # cap layer and the 0.6 cut rule keep the rest)
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


# ------------------------------------------------------------------------------------------------ pin layers / density
def _mn(layer: str) -> int:
    m = re.fullmatch(r"M(\d+)", str(layer))
    if not m:
        raise ValueError(f"tile_plan: not a metal layer: {layer!r}")
    return int(m.group(1))


def face_pin_layers(cap: str) -> dict:
    """{"h": E / W face layers, "v": N / S face layers} the pin generator alternates over under a tile's signal cap:
    E / W M4 (+ M6 from cap M6), N / S the top two of M3 / M5 / M7 under the cap.  Cap M5: E / W keep ONE layer (M4)
    -> PIN_DENSITY_PER_LAYER there; cap M6 (granted): M4+M6 / M3+M5; cap M7: M4+M6 / M5+M7."""
    c = _mn(cap)
    return {"h": [x for x in H_PIN_LAYERS if _mn(x) <= c], "v": [x for x in V_PIN_LAYERS if _mn(x) <= c][-2:]}


def layers_of(face: str, layers: dict | None) -> list:
    if layers is None:
        return []
    return list(layers.get("h" if face in ("E", "W") else "v") or [])


def tracks_per_um(layers: list) -> float:
    return sum(1.0 / PIN_PITCH_UM[x] for x in layers if x in PIN_PITCH_UM)


def face_cap(face: str, layers: dict | None, pin_density: float = PIN_DENSITY) -> float:
    """allowed average pins / um of a face: pin_density on >= 2 pin layers, PIN_DENSITY_PER_LAYER on one; layers None
    (unknown) = two layers"""
    n = 2 if layers is None else len(layers_of(face, layers))
    return min(float(pin_density), PIN_DENSITY_PER_LAYER * max(1, n))


def face_pin_check(face: str, face_len: float, regions: list, layers: dict | None,
                   pin_density: float = PIN_DENSITY, corner: float = PIN_CORNER_UM) -> dict:
    """The pin-density rule of one face (COORD 10-23): average <= face_cap, every PIN_WINDOW_UM window <= PIN_WINDOW_MAX
    (<= PIN_DENSITY_PER_LAYER x layers), pins alternating over >= 2 layers when above PIN_DENSITY_PER_LAYER, pin/track
    ratio (window peak over both layers' tracks) <= PIN_TRACK_RATIO_MAX, and no two balanced regions overlapping (the
    balanced placer spreads each region uniformly over its own range: overlapping regions stack pins).
    regions: [(n_pins, lo, hi)] with lo / hi None for a full-face region (spread over [corner, len - corner]).
    -> {"face", "pins", "avg", "peak", "layers", "tracks_per_um", "ratio", "cap", "ok", "why": [...], "overlap": [...]}"""
    lays = layers_of(face, layers) if layers is not None else []
    spans = []
    for n, lo, hi in regions:
        if n <= 0:
            continue
        if lo is None or hi is None:
            lo, hi = (corner, face_len - corner) if face_len > 2 * corner else (0.0, face_len)
        lo, hi = max(0.0, float(lo)), min(float(face_len), float(hi))
        spans.append((int(n), lo, max(hi, lo + 1e-6)))
    total = sum(n for n, _lo, _hi in spans)
    usable = max(1e-9, face_len - 2 * corner if face_len > 2 * corner else face_len)
    avg = total / usable
    win = min(PIN_WINDOW_UM, face_len) if face_len > 0 else PIN_WINDOW_UM
    starts = {0.0, max(0.0, face_len - win)}
    for _n, lo, hi in spans:
        for x in (lo, hi, lo - win, hi - win):
            starts.add(min(max(0.0, x), max(0.0, face_len - win)))
    peak = 0.0
    for a in starts:
        b = a + win
        tot = sum(n * max(0.0, min(b, hi) - max(a, lo)) / (hi - lo) for n, lo, hi in spans)
        peak = max(peak, tot / win)
    overlap = []
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            (n1, a1, b1), (n2, a2, b2) = spans[i], spans[j]
            if min(b1, b2) - max(a1, a2) > 1e-6:
                overlap.append((i, j, min(n1, n2)))
    cap = face_cap(face, layers, pin_density)
    nl = 2 if layers is None else len(lays)
    wmax = min(PIN_WINDOW_MAX, PIN_DENSITY_PER_LAYER * max(1, nl))
    tpu = tracks_per_um(lays) if lays else None
    ratio = (peak / tpu) if tpu else None
    why = []
    if avg > cap + 1e-6:
        why.append(f"average {avg:.2f} pins/um > {cap:g} ({nl} pin layer{'s' if nl != 1 else ''})")
    if peak > wmax + 1e-6:
        why.append(f"{win:g}-um window peak {peak:.2f} pins/um > {wmax:g}")
    if layers is not None and max(avg, peak) > PIN_DENSITY_PER_LAYER + 1e-6 and nl < 2:
        why.append(f"{max(avg, peak):.2f} pins/um on ONE layer ({'/'.join(lays) or '-'}): above "
                   f"{PIN_DENSITY_PER_LAYER:g}/um the pins must alternate over >= 2 layers")
    if ratio is not None and ratio > PIN_TRACK_RATIO_MAX + 1e-6:
        why.append(f"pin/track ratio {ratio:.2f} > {PIN_TRACK_RATIO_MAX:g} ({'+'.join(lays)}: {tpu:.1f} tracks/um)")
    if any(k > 2 for _i, _j, k in overlap):
        why.append(f"{len(overlap)} overlapping pin regions (the balanced placer stacks their pins): give disjoint "
                   "pin_ranges or one region per face")
    return {"face": face, "pins": total, "avg": round(avg, 3), "peak": round(peak, 3), "layers": lays,
            "tracks_per_um": round(tpu, 2) if tpu else None, "ratio": round(ratio, 3) if ratio is not None else None,
            "cap": cap, "window_max": wmax, "ok": not why, "why": why, "overlap": overlap}


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


def primary_face(tm: dict) -> str | None:
    """the macro's CONTROL face in its LEF (R0): the face that carries its clock pin (use CLOCK or a clk / clock name),
    else the face with the most signal pins.  A 1r1w SRAM with wd_in split over both sides (ot_sram_1r1w_512x128:
    W clk / addr / ce / rd_out / wd half, E wd half / mask / repair) has its logic on the W (control) face."""
    W, H = tm["W"], tm["H"]
    for p in tm["pins"]:
        if p.get("use") == "CLOCK" or re.fullmatch(r"(?i)clk|clock|ck|clk_in", str(p.get("name", ""))):
            for _l, (x0, y0, x1, y1) in p["rects"]:
                if x0 <= 200:
                    return "W"
                if x1 >= W - 200:
                    return "E"
                if y0 <= 200:
                    return "S"
                if y1 >= H - 200:
                    return "N"
    c = macro_pin_faces(tm)
    best = max(FACES, key=lambda f: c[f])
    return best if c[best] else None


_T_FACE = {"N": "E", "E": "N", "S": "W", "W": "S"}          # transpose (x, y) -> (y, x)
_T_ORIENT = {"R0": "R0", "MY": "MX", "MX": "MY", "R180": "R180"}


def _transpose_tm(tm: dict) -> dict:
    pins = [{**p, "rects": [(lay, (y0, x0, y1, x1)) for lay, (x0, y0, x1, y1) in p["rects"]]} for p in tm["pins"]]
    return {**tm, "W": tm["H"], "H": tm["W"], "pins": pins}


REPAIR_PINS = ("cr_en", "cr_sel", "rr_en", "rr_addr")   # ASAP7 fakeram redundancy-repair pins: always tied (tie_audit)


def strip_pins(tm: dict, tied=REPAIR_PINS) -> dict:
    """the macro without the pins its instances tie to constants (bus base names; repair pins by default, plus the spec's
    tile_plan.tied_macro_pins, e.g. a full-word w_mask_in the RTL ties to all-ones): they need no channel or band"""
    tied = set(tied or ())
    if not tied:
        return tm
    return {**tm, "pins": [p for p in tm["pins"] if re.sub(r"\[.*$", "", str(p.get("name", ""))) not in tied]}


def obs_top(tm: dict) -> int:
    """highest metal the macro obstructs (pins included), 0 when unknown"""
    top = 0
    for lay in list((tm.get("obs") or {}).keys()) + [l for p in tm["pins"] for l, _r in p["rects"]]:
        m = re.fullmatch(r"M(\d+)", str(lay))
        if m:
            top = max(top, int(m.group(1)))
    return top


def over_pitch_for(pin_layers: dict | None, axis: str) -> dict | None:
    """{metal: pitch} of the layers that can cross OVER a macro array to its back face: E-W wires over N-S columns need
    a horizontal layer (M6 when the tile cap allows it: pin_layers h), N-S wires over E-W rows a vertical one (M5 /
    M7 from pin_layers v); plan_macros keeps only layers above the macro's own OBS"""
    if pin_layers is None:
        return None
    lays = pin_layers.get("h" if axis == "WE" else "v") or []
    return {int(x[1:]): PIN_PITCH_UM[x] for x in lays if x in PIN_PITCH_UM and int(x[1:]) >= 5}


def _over_fits(col: list, pf: str | None, over: dict | None, o: str | None = None) -> bool:
    """every macro of the column can have the pins of its back face (the LEF face opposite its control face pf)
    reached OVER the macro: a crossing layer above its OBS, back pins <= OVER_MACRO_UTIL x height / pitch"""
    if not pf or not over or not over.get("WE"):
        return False
    back_lef = OPP[pf]
    for m, _s in col:
        lay = [pt for mt, pt in over["WE"].items() if mt > obs_top(m["tm"])]
        if not lay or macro_pin_faces(m["tm"])[back_lef] > m["h"] / min(lay) * OVER_MACRO_UTIL:
            return False
    return True


def plan_macros(W: float, H: float, macros: list, demand: dict, halo: float = 5.4, rows: int | None = None,
                logic_face: str | None = None, over: dict | None = None, pack_cap: float | None = None) -> dict:
    """Macro ARRAY plan: macros pinned on W / E faces (SRAM / ROM arrays) form N-S abutted COLUMNS of `rows` arrays;
    columns sit side by side with a LOGIC CHANNEL in front of every pin face, sized from the pins facing it
    (channel_um), and a 20 um gap where both faces are pin-free; the array hangs from the N or S face with the lower
    pin demand and is centred along it, so the logic is one band between the macro pins and the face pins.
    Single-face arrays are mirrored in pairs so two pin faces share one channel.  N / S pinned arrays: the same plan
    transposed (E-W rows).  macros: [{"w","h","tm","key"}] (um; tm = parse_lef dict, nm).  rows None: the most compact
    choice.  -> {"ok", "edge", "axis", "rows", "bbox", "need": [w, h] (outline the array needs), "placed": [{key, x, y,
    orient, pin_faces, col, abut_below}], "why"}.  Positions are pre-lattice: ref_tile snaps / track-aligns every column
    and keeps its N-S pitch, then re-runs the gate's geometry checks.
    logic_face ("E" / "W" for column arrays, "N" / "S" for row arrays; spec tile_plan.logic_face): ONE logic band
    between the macro array and that face -- every macro's control face (primary_face) is oriented toward it, no
    mirrored pairs, and the array sits against the opposite face (its keep-off and back channel), so the whole free
    width is the band (GEOM-REVIEW 10-23 lep: 10 dual-face banks with their pins away from the logic).  over ({metal:
    pitch} per axis {"WE": columns, "NS": rows} of the layers crossing the array, over_pitch_for): with logic_face, a column's BACK-face pins (the face away
    from the band) whose wires fit over the macro (pins per macro <= OVER_MACRO_UTIL x its height / pitch on a layer
    above its OBS) are reached over the macro from the band -- their channel shrinks to the keep-off."""
    if logic_face is not None and logic_face not in FACES:
        raise ValueError(f"tile_plan logic_face {logic_face!r}: one of N S E W")
    if not macros:
        return {"ok": True, "edge": None, "axis": None, "rows": 0, "bbox": None, "need": [0.0, 0.0], "placed": [],
                "why": "no macros"}
    sig = [_sig_faces(m["tm"]) for m in macros]
    if sum(1 for s in sig if s and s <= {"N", "S"}) > len(macros) / 2:
        tdem = {_T_FACE[f]: v for f, v in demand.items() if f in _T_FACE}
        tms = [{**m, "w": m["h"], "h": m["w"], "tm": _transpose_tm(m["tm"])} for m in macros]
        if logic_face in ("E", "W"):
            raise ValueError(f"tile_plan logic_face {logic_face}: N / S pinned macros form E-W rows (logic_face N or S)")
        r = plan_macros(H, W, tms, tdem, halo, rows, _T_FACE.get(logic_face) if logic_face else None,
                        {"WE": (over or {}).get("NS")} if over else None)
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
        if logic_face in ("N", "S"):
            raise ValueError(f"tile_plan logic_face {logic_face}: W / E pinned macros form N-S columns (logic_face E or W)")
        # candidates: columns of n macros in master order, and first-fit-decreasing columns packed up to a height cap
        # (mixed heights: two tall arrays side by side with the short ones stacked beside them -- hr_core_prompt)
        caps = set()
        by = {}
        for m in macros:
            by.setdefault((m["tm"]["name"], round(m["h"], 3)), []).append(m["h"])
        hmax = max(m["h"] for m in macros)
        for hs in by.values():
            for j in range(1, len(hs) + 1):
                for g in (ABUT_PITCH_UM, CHANNEL_MIN_UM):
                    c = j * hs[0] + (j - 1) * g
                    if c >= hmax - 1e-6:
                        caps.add(round(c, 3))
        cands = [(n, None) for n in range(1, len(macros) + 1)] + [(len(macros), c) for c in sorted(caps)]
        for n, cap in cands:
            r = plan_macros(W, H, macros, demand, halo, n, logic_face, over, cap)
            nw, nh = max(W, r["need"][0]), max(H, r["need"][1])
            # one logic band: among equal outlines the fewest columns (the band keeps the width)
            key = (round(nw * nh, 1), -n if logic_face else 0, max(nw, nh) / min(nw, nh))
            if best is None or key < best[0]:
                best = (key, r)
        return best[1]
    pin_faces = {f for f in FACES if demand.get(f, 0) > 0}
    edge = macro_edge(demand, "WE")
    cols, cur = [], []          # columns of <= rows arrays, widest master first (abutted_stack needs only x overlap)
    order = sorted(range(len(macros)), key=lambda i: (-macros[i]["w"], macros[i]["tm"]["name"], i))
    if pack_cap:
        for m, s in ((macros[i], sig[i]) for i in order):
            for c in cols:
                pitch = ABUT_PITCH_UM if _stackable(c[0][0]["tm"]) else CHANNEL_MIN_UM
                if sum(x["h"] for x, _ in c) + len(c) * pitch + m["h"] <= pack_cap + 1e-6:
                    c.append((m, s))
                    break
            else:
                cols.append([(m, s)])
    else:
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
        front = None
        pf = primary_face(m0["tm"])
        if logic_face and we:   # one logic band: the control face points at it
            front = logic_face
            o = orient_for(pf if pf in we else sorted(we)[0], logic_face)
            faces = {face_after(o, f) for f in we}
        elif we == {"W", "E"} and pf in we and _over_fits(c, pf, over):
            # dual-face arrays whose back face (data half / tied mask) can be reached over the macro: mirrored pairs
            # like single-face arrays, control faces sharing one channel (rg3 bx 10-23: 2 x 4 SRAM, read faces centred)
            front = "E" if k % 2 == 0 else "W"
            o = orient_for(pf, front)
            faces = {"W", "E"}
            k += 1
        elif we == {"W", "E"} or not we:
            o, faces = "R0", set(we)
        else:                    # single-face arrays alternate: pairs of pin faces share one channel
            want = "E" if k % 2 == 0 else "W"
            o = orient_for(next(iter(we)), want)
            faces = {want}
            k += 1
        cnt = macro_pin_faces(m0["tm"])
        per = {face_after(o, f): cnt[f] for f in ("W", "E")}
        tot = {"W": 0, "E": 0}           # the whole column's pins per tile face (mixed masters summed one by one)
        for m, _s in c:
            cm = macro_pin_faces(m["tm"])
            for f in ("W", "E"):
                tot[face_after(o, f)] += cm[f]
        stack = _stackable(m0["tm"])
        hts = [m["h"] for m, _ in c]
        h = sum(hts) + (len(hts) - 1) * (ABUT_PITCH_UM if stack else CHANNEL_MIN_UM)
        over_ok = bool(front) and OPP[front] in faces and _over_fits(c, pf if pf in we else None, over, o)
        spec_cols.append({"items": c, "o": o, "faces": faces, "w": max(m["w"] for m, _ in c), "h": h,
                          "pins_w": tot["W"] if "W" in faces and not (over_ok and front == "E") else 0,
                          "pins_e": tot["E"] if "E" in faces and not (over_ok and front == "W") else 0,
                          "stack": stack, "over": over_ok})
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
    # centred, or against the face opposite the logic band (the free width is then the band)
    x = x0c + kw + lead + (max(0.0, free) if logic_face == "W" else 0.0 if logic_face == "E" else max(0.0, free / 2))
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
            "logic_face": logic_face, "over_macro_cols": [j for j, c in enumerate(spec_cols) if c.get("over")],
            "pack_cap": pack_cap,
            "why": (f"{len(macros)} macros in {len(spec_cols)} N-S columns of "
                    + (f"<= {pack_cap:g} um" if pack_cap else f"<= {rows}") + f" (abutted) hung from the {edge} "
                    f"face; logic channels {', '.join(f'{g:.0f}' for g in [lead] + gaps + [trail])} um in front of the "
                    "pin faces" + (f"; control faces toward ONE logic band at the {logic_face} face" if logic_face
                                   else "") + ("; back-face pins reached over the macros" if any(
                                       c.get("over") for c in spec_cols) else ""))}


# ------------------------------------------------------------------------------------------------ outline
def content_outline(std_area: float, macros: list, demand: dict, util: float = TARGET_UTIL, halo: float = 5.4,
                    slot: tuple | None = None, pin_density: float = PIN_DENSITY, fixed: list | None = None,
                    pin_layers: dict | None = None, logic_face: str | None = None) -> dict:
    """The tile outline from its content.  std_area: synthesized std-cell area WITHOUT hard macros (um2, the pin
    registers included; pre_route_gate.synthesis_std_area subtracts the macros' Liberty area); macros: the spec's
    LEF macros the plan places [{"w","h","tm","key"}]; fixed: hard blocks at fixed spec positions (macros with "at",
    hard children) [{"w","h"}] -- footprint (with halo) counted as macro area, never as std cells; demand: {face: pin
    bits}; pin_layers: face_pin_layers() of the kit (None: two layers on every face).  The per-face pin limit is
    face_cap() (pin_density on two layers, PIN_DENSITY_PER_LAYER on one).  -> {"w","h","bound","area_core","fill",
    "breakdown", "pin_density", "pin_check", "macro_plan", "slot", "why"}.  Macro channels are logic area (their cells
    are counted once)."""
    if not UTIL_RANGE[0] - 1e-9 <= util <= UTIL_RANGE[1] + 1e-9:
        raise ValueError(f"tile_plan util {util} outside {UTIL_RANGE}")
    fixed = list(fixed or [])
    over = {"WE": over_pitch_for(pin_layers, "WE"), "NS": over_pitch_for(pin_layers, "NS")}
    n_regs = sum(demand.values())
    reg_area = min(std_area, n_regs * FF_AREA_UM2)
    band = n_regs * FF_AREA_UM2 / BAND_FILL
    logic = max(std_area - reg_area, 0.0) / util
    mac = sum((m["w"] + 2 * halo) * (m["h"] + 2 * halo) for m in macros + fixed)
    core = logic + band + mac
    dcap = {f: face_cap(f, pin_layers, pin_density) for f in FACES}
    wmin = max(demand.get("N", 0) / dcap["N"], demand.get("S", 0) / dcap["S"])
    hmin = max(demand.get("E", 0) / dcap["E"], demand.get("W", 0) / dcap["W"])
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
    plan = plan_macros(W, H, macros, demand, halo, logic_face=logic_face, over=over)
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
        plan = plan_macros(W, H, macros, demand, halo, logic_face=logic_face, over=over)
    capped = False
    if max(W, H) / min(W, H) > ASPECT_MAX:      # a pin- / macro-bound long-thin tile: widen (the low fill shows)
        capped = True
        if W > H:
            H = snap_up(W / ASPECT_MAX)
        else:
            W = snap_up(H / ASPECT_MAX)
        plan = plan_macros(W, H, macros, demand, halo, logic_face=logic_face, over=over)
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
    pchk = {f: face_pin_check(f, W if f in "NS" else H, [(demand.get(f, 0), None, None)], pin_layers, pin_density)
            for f in FACES if demand.get(f, 0)}
    free = (W - 2 * CORE_MARGIN) * (H - 2 * CORE_MARGIN) - sum(m["w"] * m["h"] for m in macros + fixed)
    fill = std_area / max(1e-9, free)
    nm = len(macros) + len(fixed)
    return {"w": W, "h": H, "bound": bound, "aspect_capped": capped, "area_core": round(core, 1),
            "fill": round(fill, 3),
            "breakdown": {"logic_um2": round(logic, 1), "band_um2": round(band, 1), "macro_um2": round(mac, 1),
                          "macros": nm, "fixed_blocks": len(fixed), "pin_regs": n_regs, "util": util},
            "pin_density": dens, "pin_cap": dcap, "pin_layers": pin_layers, "pin_check": pchk,
            "macro_plan": plan, "slot": slot_v,
            "why": (f"content: std {std_area:.0f}/{util} + band {band:.0f} ({n_regs} pin regs) + macros {mac:.0f} um2 "
                    f"({nm} hard block{'s' if nm != 1 else ''}) -> {W:g} x {H:g} ({bound}-bound"
                    f"{', aspect capped' if capped else ''}, pins <= "
                    + "/".join(f"{f} {dcap[f]:g}" for f in FACES) + f"/um, std fill {fill:.0%})")}


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
