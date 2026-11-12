"""PIN_FACE_BLOCKED guard (HBM-GEOM-2 11-12, COORD ruling on hbm-phy-face-blocked).

A face pin window that lies flush against a hard macro leaves no std-cell rows between the pins and the macro: the
kit cuts rows within the macro halo, the boundary flops of those pins have nowhere legal to go, and detail_place does
not converge (DPL-1102 / DPL-0033 / DPL-0201 in PHY_NW 5854/5854 pins, PHY_NC 7028/7028, q_b010 3167/3655 S pins).

Checks, on the kit's FINAL macro poses (after the plan pose, macro_moves and the track snap) and the exact pins:
  (a) every face pin within `clear` um (Chebyshev) of a placed hard-macro bbox is BLOCKED; per (bus, face) the guard
      reports the blocked count / span and the unblocked spans of that face (the window a plan delta should use);
  (b) the pin windows come from the plan (both partitions of a face compute them with schema.pin_positions, so a kit
      cannot clip its side alone without breaking abutment): the guard reports the free spans, the clip itself is a
      plan delta (the phy_flip q_mcb_nw re-lay is the worked example);
  (c) every interior clock / reset tap pin strictly inside a placed macro bbox is BLOCKED as well.
Mode (env OT_PIN_FACE_BLOCKED): warn (default; OWNER 11-03 "targets, not gates": only sign-off blocks) prints the
PIN_FACE_BLOCKED lines and writes pin_face_blocked.json; error raises ValueError before any build step; off skips.
OT_PIN_FACE_CLEAR_UM (default 10) is the clearance; a kit with no hard macro or no blocked pin is unchanged (no file).
"""
import json
import os
import re
from pathlib import Path

ROTATED = ("R90", "R270", "MXR90", "MYR90")
DEFAULT_CLEAR_UM = 10.0


def lef_size(path, macro=None):
    """(w, h) of the first (or the named) MACRO in a LEF file."""
    text = Path(path).read_text(errors="replace")
    if macro:
        m = re.search(r"MACRO\s+" + re.escape(macro) + r"\b(.*?)END\s+" + re.escape(macro), text, re.S)
        if m:
            text = m.group(1)
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", text)
    if not m:
        raise ValueError(f"{path}: no SIZE")
    return float(m.group(1)), float(m.group(2))


def macro_boxes(placed):
    """[(inst, (x0, y0, x1, y1))] of kit macro placements {inst, lef, master, x, y, o}."""
    out = []
    for q in placed:
        if not q.get("lef"):
            continue
        w, h = lef_size(q["lef"], q.get("master"))
        if q.get("o", "R0") in ROTATED:
            w, h = h, w
        out.append((q["inst"], (float(q["x"]), float(q["y"]), float(q["x"]) + w, float(q["y"]) + h)))
    return out


def _near(x, y, b, clear):
    return b[0] - clear <= x <= b[2] + clear and b[1] - clear <= y <= b[3] + clear


def _spans(vals, gap):
    """merge sorted coordinates into [lo, hi] runs (a gap > `gap` starts a new run)."""
    out = []
    for v in sorted(vals):
        if out and v - out[-1][1] <= gap:
            out[-1][1] = v
        else:
            out.append([v, v])
    return [[round(a, 4), round(b, 4)] for a, b in out]


def free_spans(face, outline, boxes, clear):
    """unblocked [lo, hi] spans along one face (type frame): the face minus every box within `clear` of that edge."""
    w, h = outline
    ext = h if face in "EW" else w
    cuts = []
    for _, b in boxes:
        d = {"W": b[0], "E": w - b[2], "S": b[1], "N": h - b[3]}[face]
        if d < clear:
            lo, hi = (b[1], b[3]) if face in "EW" else (b[0], b[2])
            cuts.append((max(0.0, lo - clear), min(ext, hi + clear)))
    spans, at = [], 0.0
    for lo, hi in sorted(cuts):
        if lo > at:
            spans.append([round(at, 4), round(lo, 4)])
        at = max(at, hi)
    if at < ext:
        spans.append([round(at, 4), round(ext, 4)])
    return spans


def check(tn, outline, pins, taps, boxes, clear=DEFAULT_CLEAR_UM):
    """report dict: rows per (bus, face) with blocked pins, blocked taps, free spans per face."""
    rows, per = [], {}
    for bus, bit, ln, x, y, f in pins:
        r = per.setdefault((bus, f), {"bus": bus, "face": f, "pins": 0, "blocked": 0, "coords": [], "by": set()})
        r["pins"] += 1
        hit = [i for i, b in boxes if _near(x, y, b, clear)]
        if hit:
            r["blocked"] += 1
            r["coords"].append(y if f in "EW" else x)
            r["by"].update(hit)
    faces = set()
    for (bus, f), r in sorted(per.items()):
        if r["blocked"]:
            faces.add(f)
            rows.append({"bus": bus, "face": f, "pins": r["pins"], "blocked": r["blocked"],
                         "blocked_spans_um": _spans(r["coords"], 2 * clear), "macros": sorted(r["by"])[:8]})
    tap_rows = []
    for name, x, y in taps:
        hit = [i for i, b in boxes if b[0] + 0.5 < x < b[2] - 0.5 and b[1] + 0.5 < y < b[3] - 0.5]
        if hit:
            tap_rows.append({"pin": name, "xy_um": [x, y], "inside": hit[:4]})
    return {"schema": "pin_face_blocked.v1", "type": tn, "clear_um": clear, "outline_um": list(outline),
            "blocked_pins": sum(r["blocked"] for r in rows), "face_pins": len(pins), "rows": rows,
            "taps": tap_rows, "free_spans_um": {f: free_spans(f, outline, boxes, clear) for f in sorted(faces)}}


def lines(rep):
    out = []
    for r in rep["rows"]:
        out.append(f"PIN_FACE_BLOCKED type {rep['type']} bus {r['bus']} face {r['face']}: {r['blocked']}/{r['pins']} "
                   f"pins within {rep['clear_um']:g} um of {','.join(r['macros'][:3])} at {r['blocked_spans_um']}; "
                   f"free face spans {rep['free_spans_um'].get(r['face'])}")
    for t in rep["taps"]:
        out.append(f"PIN_FACE_BLOCKED type {rep['type']} tap {t['pin']} at {t['xy_um']} inside {','.join(t['inside'])}")
    return out


def apply(tn, kd, outline, pins, taps, placed, mode=None, clear=None):
    """run the guard for one kit; returns the report (None when off or no macro)."""
    mode = (mode or os.environ.get("OT_PIN_FACE_BLOCKED", "warn")).lower()
    if mode == "off" or not placed:
        return None
    clear = float(clear if clear is not None else os.environ.get("OT_PIN_FACE_CLEAR_UM", DEFAULT_CLEAR_UM))
    rep = check(tn, outline, pins, taps, macro_boxes(placed), clear)
    if not rep["rows"] and not rep["taps"]:
        return rep
    rep["mode"] = mode
    Path(kd, "pin_face_blocked.json").write_text(json.dumps(rep, indent=1) + "\n")
    msg = lines(rep)
    for m in msg:
        print(m)
    if mode == "error":
        raise ValueError(f"type {tn}: PIN_FACE_BLOCKED {rep['blocked_pins']} face pin(s), {len(rep['taps'])} tap(s) "
                         f"blocked by hard macros (pin_face_blocked.json; OT_PIN_FACE_BLOCKED=warn to build anyway)")
    return rep
