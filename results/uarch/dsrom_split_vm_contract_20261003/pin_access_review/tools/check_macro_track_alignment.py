#!/usr/bin/env python3
"""Macro pin-access audit against the ORFS ASAP7 routing-track grid, per placement orientation.

Why: the DS-V4.1 ROM q-pair routes (dsrom_qframe A_r1/B_r1, p12q9) failed detail route with DRT-0255 on
the pins of the Y-mirrored ROM macro.  TritonRoute warned DRT-0419 ("No routing tracks pass through the
center of Term") on all 288 signal pins of every MX/R180 macro and on no unmirrored one.  The abstract puts
M4 pin centres at y = 0.780 + k*0.096 (0.012 mod 0.048, on the M4 track at origin 0 in R0) but the macro
height 62.910 um is 0.030 mod 0.048, so a Y mirror moves every pin centre to (H - y) = 0.018 mod 0.048,
6 nm off the track; the placement hook snapped every origin to 0 mod 0.048.

For each abstract this tool computes, per orientation, the set of origin residues that put every signal
pin centre on a preferred-direction track of its layer (the DRT-0419 condition), intersects that with the
placement site/row grid, and evaluates the naive "origin on track grid at 0" snap.  It also checks pin
width/area against the tech minimums, same-layer OBS clearance, upper/lower-layer via access, and the
macro dimension parity that makes mirroring orientation-variant, and prices the generator fix.

All arithmetic is in integer nanometres (LEF database 1000/um, ASAP7 manufacturing grid 1 nm).

Usage:
  tools/check_macro_track_alignment.py [LEF ...] [--json OUT] [--tracks make_tracks.tcl]
  (default LEFs: physical/asap7_memory_macros/*/*.lef)
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ORFS flow/platforms/asap7/openRoad/make_tracks.tcl (byte-identical copies are archived under
# results/uarch/*/inputs/make_tracks.tcl).  Units nm: layer -> list of (x_off, x_pitch, y_off, y_pitch).
# x_* places the VERTICAL track lines (x coordinates), y_* the HORIZONTAL ones.
ASAP7_TRACKS_NM = {
    "M1": [(9, 36, 9, 36)],
    "M2": [(9, 36, o, 270) for o in (45, 81, 117, 153, 189, 225, 270)],
    "M3": [(9, 36, 9, 36)],
    "M4": [(9, 36, 12, 48)],
    "M5": [(12, 48, 12, 48)],
    "M6": [(12, 48, 16, 64)],
    "M7": [(16, 64, 16, 64)],
    "M8": [(116, 80, 116, 80)],
    "M9": [(116, 80, 116, 80)],
}
# asap7_tech_1x_201209.lef: preferred direction, min width (nm), min spacing (nm), min area (nm^2)
ASAP7_LAYERS = {
    "M1": ("V", 18, 18, 666), "M2": ("H", 18, 18, 666), "M3": ("V", 18, 18, 666),
    "M4": ("H", 24, 24, 2000), "M5": ("V", 24, 24, 2000), "M6": ("H", 32, 32, 2000),
    "M7": ("V", 32, 32, 2000), "M8": ("H", 40, 40, 2000), "M9": ("V", 40, 40, 2000),
}
LAYER_ORDER = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
SITE_X_NM = 54      # asap7sc7p5t site width
ROW_Y_NM = 270      # asap7sc7p5t row height
ROW_SNAP_NM = 270   # tools/mem_compiler/asap7.py METAL['height_snap_um']

# DEF orientation -> (x, y) map for a point of a W x H macro, with the placed bbox's lower-left at 0.
ORIENT = {
    "R0": lambda x, y, W, H: (x, y),
    "MX": lambda x, y, W, H: (x, H - y),          # DEF FS: mirror about the X axis (flips y)
    "MY": lambda x, y, W, H: (W - x, y),          # DEF FN: mirror about the Y axis (flips x)
    "R180": lambda x, y, W, H: (W - x, H - y),    # DEF S
    "R90": lambda x, y, W, H: (H - y, x),         # DEF W
    "R270": lambda x, y, W, H: (y, W - x),        # DEF E
    "MXR90": lambda x, y, W, H: (y, x),           # DEF FW
    "MYR90": lambda x, y, W, H: (H - y, W - x),   # DEF FE
}
MIRROR_SET = ("R0", "MX", "MY", "R180")
ROT_SET = ("R90", "R270", "MXR90", "MYR90")


def nm(v: str | float) -> int:
    return int(round(float(v) * 1000))


def parse_tracks(path: str) -> dict:
    out: dict = {}
    for line in Path(path).read_text().splitlines():
        m = re.match(r"\s*make_tracks\s+(\S+)\s+-x_offset\s+(\S+)\s+-x_pitch\s+(\S+)\s+-y_offset\s+(\S+)\s+-y_pitch\s+(\S+)", line)
        if m:
            out.setdefault(m.group(1), []).append(tuple(nm(m.group(i)) for i in range(2, 6)))
    return out


def parse_lef(text: str) -> list[dict]:
    """Minimal LEF MACRO reader: SIZE, SYMMETRY, PIN USE/LAYER/RECT, OBS LAYER/RECT."""
    macros = []
    cur = None
    pin = None
    layer = None
    in_obs = False
    in_propdef = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        tok = line.replace(";", " ").split()
        if not tok:
            continue
        if tok[0] == "PROPERTYDEFINITIONS":
            in_propdef = True
            continue
        if in_propdef:
            in_propdef = not (tok[0] == "END" and len(tok) > 1 and tok[1] == "PROPERTYDEFINITIONS")
            continue
        if tok[0] == "MACRO":
            cur = {"name": tok[1], "W": 0, "H": 0, "symmetry": [], "pins": [], "obs": {}, "class": ""}
            macros.append(cur)
            continue
        if cur is None:
            continue
        if tok[0] == "SIZE":
            cur["W"], cur["H"] = nm(tok[1]), nm(tok[3])
        elif tok[0] == "CLASS" and pin is None and not in_obs:
            cur["class"] = tok[1]
        elif tok[0] == "SYMMETRY":
            cur["symmetry"] = tok[1:]
        elif tok[0] == "PIN" and not in_obs:
            pin = {"name": tok[1], "use": "SIGNAL", "rects": []}
            cur["pins"].append(pin)
        elif tok[0] == "USE" and pin is not None:
            pin["use"] = tok[1]
        elif tok[0] == "OBS":
            in_obs, pin = True, None
        elif tok[0] == "LAYER":
            layer = tok[1]
        elif tok[0] == "RECT":
            r = tuple(nm(v) for v in tok[1:5])
            r = (min(r[0], r[2]), min(r[1], r[3]), max(r[0], r[2]), max(r[1], r[3]))
            if in_obs:
                cur["obs"].setdefault(layer, []).append(r)
            elif pin is not None:
                pin["rects"].append((layer, r))
        elif tok[0] == "END":
            if len(tok) == 1:
                if in_obs:
                    in_obs = False
                layer = None
            elif pin is not None and tok[1] == pin["name"]:
                pin = None
            elif tok[1] == cur["name"]:
                cur = None
    return macros


def allowed_orients(sym: list[str]) -> list[str]:
    s = set(sym)
    o = ["R0"]
    if "X" in s:
        o.append("MX")
    if "Y" in s:
        o.append("MY")
    if "X" in s and "Y" in s:
        o.append("R180")
    if "R90" in s:
        o += ["R90", "R270"] + (["MXR90", "MYR90"] if ("X" in s or "Y" in s) else [])
    return o


def track_residues(grids: list[tuple], axis: str) -> tuple[int, set[int]]:
    """Track coordinates on one axis as (period, residues mod period); axis 'y' = horizontal lines."""
    pairs = [(g[2], g[3]) if axis == "y" else (g[0], g[1]) for g in grids]
    P = 1
    for _, p in pairs:
        P = P * p // math.gcd(P, p)
    res = set()
    for off, p in pairs:
        for k in range(P // p):
            res.add((off + k * p) % P)
    return P, res


def transform_rect(r, orient, W, H):
    (x1, y1), (x2, y2) = ORIENT[orient](r[0], r[1], W, H), ORIENT[orient](r[2], r[3], W, H)
    return (min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2))


def legal_origins(pins_local: list[tuple], period: int, tracks: set[int], mode: str) -> set[int]:
    """Origin residues mod period for which every pin is accessible.

    pins_local: per pin (lo, hi) on the axis perpendicular to the track lines (nm, macro-local, oriented).
    mode 'center': a track passes exactly through the pin centre (DRT-0419 condition; centres at .5 nm
    never qualify).  mode 'cross': a track crosses the pin rect anywhere (via access from the adjacent layer).
    """
    legal = set(range(period))
    for lo, hi in pins_local:
        ok = set()
        if mode == "center":
            if (lo + hi) % 2:
                return set()
            c = (lo + hi) // 2
            for t in tracks:
                ok.add((t - c) % period)
        else:
            for t in tracks:
                for v in range(lo, hi + 1):
                    ok.add((t - v) % period)
        legal &= ok
        if not legal:
            break
    return legal


def joint_grid(legal: set[int], period: int, site: int, site_origin: int = 0) -> dict:
    """Intersect a residue set with the site grid site_origin + n*site."""
    L = period * site // math.gcd(period, site)
    sols = sorted(o for o in range(site_origin % L, L + site_origin % L, site) if (o % period) in legal)
    sols = sorted(s % L for s in sols)
    return {"joint_period_nm": L, "site_pitch_nm": site, "legal_origins_mod_joint_nm": sols,
            "legal_fraction_of_sites": round(len(sols) / (L // site), 4)}


def compress(res: set[int], period: int) -> list:
    """Residue set as sorted list, or as [lo, hi] runs when long."""
    s = sorted(res)
    if len(s) <= 8:
        return s
    runs, a, b = [], s[0], s[0]
    for v in s[1:]:
        if v == b + 1:
            b = v
        else:
            runs.append([a, b]); a = b = v
    runs.append([a, b])
    return runs


def mirror_invariant_fix(c_mod: int, dim: int, pitch: int, snap: int, other_dim: int) -> dict:
    """Generator fix pricing so that the mirror about this axis keeps pins on the same origin residue.

    Condition: (2c - dim) == 0 mod pitch, where c is any pin centre (all congruent mod pitch).
    """
    out = {}
    if (2 * c_mod - dim) % pitch == 0:
        return {"needed": False}
    out["needed"] = True
    best = None
    for k in range(-(-dim // snap), -(-dim // snap) + 2 * pitch):
        d2 = k * snap
        if (2 * c_mod - d2) % pitch == 0:
            best = d2
            break
    best_free = next(d2 for d2 in range(dim, dim + pitch + 1) if (2 * c_mod - d2) % pitch == 0)
    out["grow_dimension_on_snap_grid"] = None if best is None else {
        "new_dim_nm": best, "delta_nm": best - dim, "area_delta_pct": round(100.0 * (best - dim) / dim, 3),
        "area_delta_um2": round((best - dim) * other_dim / 1e6, 3), "snap_nm": snap}
    out["grow_dimension_free"] = {"new_dim_nm": best_free, "delta_nm": best_free - dim,
                                  "area_delta_pct": round(100.0 * (best_free - dim) / dim, 3),
                                  "area_delta_um2": round((best_free - dim) * other_dim / 1e6, 3)}
    shifts = [s for s in range(-pitch // 2, pitch // 2 + 1) if (2 * (c_mod + s) - dim) % pitch == 0]
    out["shift_pins_keep_dim"] = {"pin_shift_options_nm": shifts,
                                  "note": "zero area; unmirrored origin residue changes by -shift"} if shifts else None
    return out


def audit_macro(m: dict, tracks: dict, layers: dict, path: str = "") -> dict:
    W, H = m["W"], m["H"]
    sig = [p for p in m["pins"] if p["use"] not in ("POWER", "GROUND")]
    pg = [p for p in m["pins"] if p["use"] in ("POWER", "GROUND")]
    orients = allowed_orients(m["symmetry"])
    rec: dict = {"macro": m["name"], "lef": path, "size_um": [W / 1000, H / 1000], "symmetry": m["symmetry"],
                 "allowed_orientations": orients, "signal_pins": len(sig), "pg_pins": [p["name"] for p in pg],
                 "pin_layers": {}, "orientations": {}, "pin_checks": {}, "dimension_parity": {}, "findings": []}
    by_layer: dict[str, list] = {}
    for p in sig:
        for lay, r in p["rects"]:
            by_layer.setdefault(lay, []).append((p["name"], r))
    for lay, items in by_layer.items():
        rec["pin_layers"][lay] = len(items)

    for lay, items in by_layer.items():
        if lay not in tracks or lay not in layers:
            rec["findings"].append(f"pins on {lay}: no track/tech data")
            continue
        pdir, minw, minsp, minarea = layers[lay]
        pref_axis = "y" if pdir == "H" else "x"
        Pp, Tp = track_residues(tracks[lay], pref_axis)
        idx = LAYER_ORDER.index(lay)
        adj = [l for l in (LAYER_ORDER[idx + 1] if idx + 1 < len(LAYER_ORDER) else None,
                           LAYER_ORDER[idx - 1] if idx else None) if l]
        # --- pin geometry checks (orientation-independent)
        widths = [min(r[2] - r[0], r[3] - r[1]) for _, r in items]
        areas = [(r[2] - r[0]) * (r[3] - r[1]) for _, r in items]
        obs_same = m["obs"].get(lay, [])

        def gap_to_obs(r):
            g = None
            for o in obs_same:
                dx = max(o[0] - r[2], r[0] - o[2], 0)
                dy = max(o[1] - r[3], r[1] - o[3], 0)
                d = max(dx, dy) if (dx == 0 or dy == 0) else math.hypot(dx, dy)
                g = d if g is None else min(g, d)
            return g
        gaps = [gap_to_obs(r) for _, r in items]
        on_edge = sum(1 for _, r in items if r[0] == 0 or r[1] == 0 or r[2] == W or r[3] == H)
        adj_cov = {}
        for al in adj:
            cov = 0
            for _, r in items:
                if any(o[0] <= r[0] and o[1] <= r[1] and o[2] >= r[2] and o[3] >= r[3] for o in m["obs"].get(al, [])):
                    cov += 1
            adj_cov[al] = cov
        # pin pitch along the pref-perpendicular axis, in tracks
        coords = sorted({((r[1] + r[3]) if pref_axis == "y" else (r[0] + r[2])) / 2 for _, r in items})
        steps = sorted({round(b - a) for a, b in zip(coords, coords[1:])})
        trk_pitch = tracks[lay][0][3] if pref_axis == "y" else tracks[lay][0][1]
        rec["pin_checks"][lay] = {
            "preferred_direction": pdir,
            "pin_width_nm": [min(widths), max(widths)], "min_width_nm": minw,
            "below_min_width": sum(1 for w in widths if w < minw),
            "pin_area_nm2": [min(areas), max(areas)], "min_area_nm2": minarea,
            "below_min_area": sum(1 for a in areas if a < minarea),
            "pins_on_macro_edge": on_edge,
            "same_layer_obs_min_gap_nm": None if all(g is None for g in gaps) else min(g for g in gaps if g is not None),
            "same_layer_obs_overlap_or_within_spacing": sum(1 for g in gaps if g is not None and g < minsp),
            "adjacent_layer_obs_covers_pin": adj_cov,
            "pin_centre_steps_nm": steps[:6], "pref_track_pitch_nm": trk_pitch,
        }
        if any(w < minw for w in widths):
            rec["findings"].append(f"{lay}: {sum(1 for w in widths if w < minw)} pins below min width")
        if any(a < minarea for a in areas):
            rec["findings"].append(f"{lay}: pin rect area {min(areas)} nm^2 < min area {minarea} (router must patch)")
        if rec["pin_checks"][lay]["same_layer_obs_overlap_or_within_spacing"]:
            rec["findings"].append(f"{lay}: same-layer OBS within min spacing of pins")
        if steps and steps[0] < 2 * trk_pitch:
            rec["findings"].append(f"{lay}: pins on adjacent tracks (centre step {steps[0]} nm)")

        # --- per-orientation track alignment
        def side_of(r):  # macro-local (R0) edge the pin abuts
            return ("L" if r[0] == 0 else "R" if r[2] == W else "B" if r[1] == 0 else "T" if r[3] == H else "I")
        sides = [side_of(r) for _, r in items]
        for o in orients:
            loc = [transform_rect(r, o, W, H) for _, r in items]
            perp = [(r[1], r[3]) if pref_axis == "y" else (r[0], r[2]) for r in loc]
            legal = legal_origins(perp, Pp, Tp, "center")
            site = ROW_Y_NM if pref_axis == "y" else SITE_X_NM
            c_res = sorted({((a + b) // 2) % Pp for a, b in perp if (a + b) % 2 == 0})
            naive_off = []
            for a, b in perp:  # origin at 0 mod track pitch (the qframe hook's snap)
                c2 = a + b
                dist = min(min((2 * t - c2) % (2 * Pp), (c2 - 2 * t) % (2 * Pp)) for t in Tp) / 2
                naive_off.append(dist)
            entry = {
                "pref_axis": pref_axis, "track_period_nm": Pp,
                "pin_centre_residues_nm": c_res[:12], "n_distinct_centre_phases": len(c_res),
                "legal_origin_residues_mod_track_nm": compress(legal, Pp),
                "uniform": bool(legal),
                "naive_snap_origin_0_mod_track": {
                    "offtrack_pins": sum(1 for d in naive_off if d > 0),
                    "max_offset_nm": max(naive_off) if naive_off else 0,
                },
                "joint_with_" + ("row" if pref_axis == "y" else "site"): joint_grid(legal, Pp, site),
            }
            # via access from adjacent layers (track crossing the pin rect), where not OBS-blocked
            va = {}
            for al in adj:
                if al not in tracks or al not in layers:
                    continue
                if adj_cov.get(al, 0) == len(items):
                    va[al] = "blocked by OBS over every pin"
                    continue
                aax = "y" if layers[al][0] == "H" else "x"
                if aax == pref_axis:
                    continue
                Pa, Ta = track_residues(tracks[al], aax)
                va[al] = {"axis": aax, "track_period_nm": Pa, "by_edge": {}}
                for side in sorted(set(sides)):
                    aperp = [(r[1], r[3]) if aax == "y" else (r[0], r[2])
                             for r, sd in zip(loc, sides) if sd == side]
                    lg = legal_origins(aperp, Pa, Ta, "cross")
                    va[al]["by_edge"][side] = {"pins": len(aperp),
                                               "crossing_origin_residues_nm": compress(lg, Pa),
                                               "origin_0_crosses_all": 0 in lg}
            entry["adjacent_layer_via_access"] = va
            rec["orientations"].setdefault(lay, {})[o] = entry

        # --- dimension parity: mirror invariance of the preferred-axis residue
        dim = H if pref_axis == "y" else W
        other = W if pref_axis == "y" else H
        cs = sorted({((r[1] + r[3]) if pref_axis == "y" else (r[0] + r[2])) for _, r in items})
        csm = sorted({(c / 2) % trk_pitch for c in cs})
        mirror = "MX" if pref_axis == "y" else "MY"
        par = {"axis_dim_nm": dim, "dim_mod_track_pitch_nm": dim % trk_pitch, "track_pitch_nm": trk_pitch,
               "row_or_site_multiple": dim % (ROW_SNAP_NM if pref_axis == "y" else SITE_X_NM) == 0,
               "orientation_flipping_this_axis": [mirror, "R180"]}
        if len(csm) == 1 and float(csm[0]).is_integer():
            c0 = int(csm[0])
            shift = (2 * c0 - dim) % trk_pitch
            par["mirror_residue_shift_nm"] = min(shift, trk_pitch - shift)
            par["fix"] = mirror_invariant_fix(c0, dim, trk_pitch, ROW_SNAP_NM if pref_axis == "y" else 216, other)
        else:
            par["mirror_residue_shift_nm"] = None
            par["fix"] = {"needed": True, "note": f"pin centres on {len(csm)} phases mod pitch: no origin aligns all pins"}
        rec["dimension_parity"][lay] = par

    # summary per layer
    for lay, per in rec["orientations"].items():
        bad = [o for o in MIRROR_SET if o in per and not per[o]["uniform"]]
        naive_bad = [o for o in MIRROR_SET if o in per and per[o]["naive_snap_origin_0_mod_track"]["offtrack_pins"]]
        rules = {o: per[o]["legal_origin_residues_mod_track_nm"] for o in MIRROR_SET if o in per}
        rec.setdefault("summary", {})[lay] = {
            "no_legal_origin": bad, "offtrack_under_origin_0_snap": naive_bad,
            "origin_rule_mod_track_nm": rules,
            "orientation_invariant": len({json.dumps(v) for v in rules.values()}) == 1,
        }
        if bad:
            rec["findings"].append(f"{lay}: no origin puts all pins on track in {bad} (pin phases vary)")
        if naive_bad:
            rec["findings"].append(f"{lay}: origin-0 track snap leaves pins off-track in {naive_bad}")
    return rec


def snap_joint_nm(value_nm: int, site_origin_nm: int, site_pitch_nm: int, track_origin_nm: int,
                  track_pitch_nm: int, span: int = 1000) -> int:
    """Python twin of the placement hooks' ot_snap_joint: nearest site-grid point that is also
    track_origin mod track_pitch."""
    center = round((value_nm - site_origin_nm) / site_pitch_nm)
    best, bestd = None, None
    for d in range(-span, span + 1):
        c = site_origin_nm + (center + d) * site_pitch_nm
        if (c - track_origin_nm) % track_pitch_nm:
            continue
        if bestd is None or abs(c - value_nm) < bestd:
            best, bestd = c, abs(c - value_nm)
    if best is None:
        raise ValueError("no intersection of site and track grids")
    return best


def check_placement(m: dict, orient: str, ox_nm: int, oy_nm: int, tracks: dict = None, layers: dict = None) -> dict:
    """Off-track signal pins (preferred-direction centre test, the DRT-0419 condition) for one placed instance."""
    tracks = tracks or ASAP7_TRACKS_NM
    layers = layers or ASAP7_LAYERS
    W, H = m["W"], m["H"]
    out = {"orient": orient, "origin_nm": [ox_nm, oy_nm], "layers": {}}
    for p in m["pins"]:
        if p["use"] in ("POWER", "GROUND"):
            continue
        for lay, r in p["rects"]:
            if lay not in tracks:
                continue
            axis = "y" if layers[lay][0] == "H" else "x"
            P, T = track_residues(tracks[lay], axis)
            q = transform_rect(r, orient, W, H)
            c2 = (q[1] + q[3] + 2 * oy_nm) if axis == "y" else (q[0] + q[2] + 2 * ox_nm)
            d = min(min((2 * t - c2) % (2 * P), (c2 - 2 * t) % (2 * P)) for t in T) / 2
            e = out["layers"].setdefault(lay, {"pins": 0, "offtrack": 0, "max_offset_nm": 0.0})
            e["pins"] += 1
            if d > 0:
                e["offtrack"] += 1
                e["max_offset_nm"] = max(e["max_offset_nm"], d)
    return out


def run(lefs: list[str], tracks: dict, layers: dict) -> dict:
    out = []
    for f in lefs:
        rel = str(Path(f).resolve().relative_to(REPO)) if str(Path(f).resolve()).startswith(str(REPO)) else f
        for m in parse_lef(Path(f).read_text()):
            if m["class"] != "BLOCK":   # standard cells are row-placed and outside this audit
                continue
            out.append(audit_macro(m, tracks, layers, rel))
    return {"schema": "opentallas.macro_track_alignment.v1",
            "tracks_source": "ORFS flow/platforms/asap7/openRoad/make_tracks.tcl",
            "site_nm": [SITE_X_NM, ROW_Y_NM], "macros": out}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lef", nargs="*")
    ap.add_argument("--tracks", help="make_tracks.tcl to use instead of the embedded ASAP7 grid")
    ap.add_argument("--json", help="write the full record here")
    ap.add_argument("--fail-on-offtrack", action="store_true",
                    help="exit 1 if any R0/MX/MY/R180 has no legal origin")
    a = ap.parse_args(argv)
    lefs = a.lef or sorted(glob.glob(str(REPO / "physical/asap7_memory_macros/*/*.lef")))
    tracks = parse_tracks(a.tracks) if a.tracks else ASAP7_TRACKS_NM
    res = run(lefs, tracks, ASAP7_LAYERS)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    rc = 0
    for r in res["macros"]:
        for lay, s in r.get("summary", {}).items():
            rule = " ".join(f"{o}:{v}" for o, v in s["origin_rule_mod_track_nm"].items())
            print(f"{r['macro']:34s} {r['size_um'][0]:>10.3f}x{r['size_um'][1]:<9.3f} {lay} pins={r['pin_layers'][lay]:4d} "
                  f"invariant={s['orientation_invariant']!s:5s} offtrack@0={','.join(s['offtrack_under_origin_0_snap']) or '-':10s} "
                  f"rule(nm mod pitch) {rule}")
            if s["no_legal_origin"]:
                rc = 1 if a.fail_on_offtrack else rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
