"""KW-FIX-44 11-10 (COORD, DIE-S81-85 dsdv_bksel_q vC2): snap static macro origins to the parent routing-track grid.

The parent placed child P (u_q.u_s.u_pk, ot_s81ph_hq_pk2) FIRM at y 201.96: 201.96 / 0.048 = 4207.5, so every P pin sat
half an M4 pitch off the parent tracks -> 1000 (capped) DRT-0418 'no pins on routing grid' and DRT-0073 at GRT.  The
plan origin was on the 0.27 row grid but not on the 2.16 macro grid every other macro in that kit used.

At kit generation (gen_phys write_type_kit, every die) each statically placed macro is checked with the same test as
kit_contract.macro_pin_grid (a preferred-direction track of the pin's layer inside every signal pin, kit make_tracks
else platform tracks).  A macro with off-track pins moves to the nearest origin that puts all of them on track:
  y: on the 0.27 row grid when the plan origin is on it (ties -> the 2.16 multiple), else (or when no row-grid origin
     puts the pins on track, receipt off_row) 1-nm steps
  x: on the 0.054 site grid when the plan origin is on it, else 1-nm steps
  at most SNAP_MAX_UM away, inside the type outline, not overlapping another placed macro.
On-grid macros are untouched (the kit is byte-identical).  A macro with no such origin keeps its plan origin and is listed
'unresolved' in the receipt (kit_contract.macro_pin_grid still reports it).  OT_MACRO_GRID_SNAP=0 turns it off.
"""
import json
import math
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))   # CLI under python3 -I
import kit_contract as KC  # noqa: E402

SNAP_MAX_UM = 4.32
ROW_UM, SITE_UM, MACRO_ROW_UM = 0.27, 0.054, 2.16
RECEIPT = "macro_grid_snap.json"


def lef_master(path, master):
    """(w, h, [(pin, layer, x0, y0, x1, y1)]) signal pin rects of `master` in a LEF file; None if absent"""
    text = Path(path).read_text(errors="replace")
    for m in re.finditer(r"^MACRO\s+(\S+)(.*?)^END\s+\1", text, re.M | re.S):
        if m.group(1) != master:
            continue
        sz = re.search(r"^\s*SIZE\s+" + KC._NUM + r"\s+BY\s+" + KC._NUM, m.group(2), re.M)
        if not sz:
            return None
        rows = []
        for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", m.group(2), re.M | re.S):
            if re.search(r"\bUSE\s+(POWER|GROUND)\b", pm.group(2)):
                continue
            layer = None
            for tok in re.finditer(r"LAYER\s+(\S+)\s*;|RECT\s+" + r"\s+".join([KC._NUM] * 4), pm.group(2)):
                if tok.group(1):
                    layer = tok.group(1)
                elif layer:
                    x0, y0, x1, y1 = (float(tok.group(i)) for i in range(2, 6))
                    rows.append((pm.group(1), layer, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
        return float(sz.group(1)), float(sz.group(2)), rows
    return None


def tracks_for(make_tracks_text=None):
    """{layer: (dir, pitch, width, offsets)}: platform tracks, overridden by a kit make_tracks text"""
    offs = {k: tuple(v) for k, v in KC.PLATFORM_TRACK_OFFSETS.items()}
    if make_tracks_text:
        kit = {}
        for line in make_tracks_text.splitlines():
            m = re.match(r"\s*make_tracks\s+(M\d)\s+(.*)$", line)
            if not m or m.group(1) not in KC.TECH_LAYERS:
                continue
            d = KC.TECH_LAYERS[m.group(1)][0]
            o = re.search(r"-" + ("y" if d == "H" else "x") + r"_offset\s+" + KC._NUM, m.group(2))
            pt = re.search(r"-" + ("y" if d == "H" else "x") + r"_pitch\s+" + KC._NUM, m.group(2))
            if o and pt and abs(float(pt.group(1)) - KC.TECH_LAYERS[m.group(1)][1]) <= KC.TOL:
                kit.setdefault(m.group(1), []).append(float(o.group(1)))
        offs.update({k: tuple(v) for k, v in kit.items()})
    return {k: (d, p, w, offs[k]) for k, (d, p, w) in KC.TECH_LAYERS.items() if k in offs}


def _on_track(lo, hi, pitch, width, offsets):
    c = (lo + hi) / 2.0
    for of in offsets:
        t = of + round((c - of) / pitch) * pitch
        for tt in (t - pitch, t, t + pitch):
            if lo + width / 2.0 - KC.GRID_TOL <= tt <= hi - width / 2.0 + KC.GRID_TOL:
                return True
    return False


def off_track(spec, x, y, o, tracks):
    """{'x': n, 'y': n}: signal pins off track along x (vertical layers) and y (horizontal layers) at origin x, y"""
    w, h, pins = spec
    out = {"x": 0, "y": 0}
    for _name, layer, *r in pins:
        if layer not in tracks:
            continue
        d, pitch, width, offsets = tracks[layer]
        X0, Y0, X1, Y1 = KC._place_rect(r, x, y, o, w, h)
        lo, hi = (Y0, Y1) if d == "H" else (X0, X1)
        if not _on_track(lo, hi, pitch, width, offsets):
            out["y" if d == "H" else "x"] += 1
    return out


def _unique_axis(spec, o, tracks, axis):
    """pins of one axis reduced to distinct (layer, lo, hi) at origin 0 (a bus repeats one shape many times)"""
    w, h, pins = spec
    seen = set()
    for _n, layer, *r in pins:
        if layer not in tracks or (tracks[layer][0] == "H") != (axis == "y"):
            continue
        X0, Y0, X1, Y1 = KC._place_rect(r, 0.0, 0.0, o, w, h)
        lo, hi = (Y0, Y1) if axis == "y" else (X0, X1)
        p = tracks[layer][1]
        b = math.floor(lo / p) * p                 # shift-invariant key: the phase within the pitch
        seen.add((layer, round(lo - b, 4), round(hi - b, 4)))
    return sorted(seen)


def _axis_ok(shapes, v, tracks):
    for layer, lo, hi in shapes:
        d, pitch, width, offsets = tracks[layer]
        if not _on_track(lo + v, hi + v, pitch, width, offsets):
            return False
    return True


def _grid(v, step):
    return abs(v / step - round(v / step)) < 1e-6


def _candidates(v, step, limit):
    """v, v-step, v+step, ... within limit (rounded to 1 nm)"""
    n = int(limit / step + 1e-9)
    yield round(v, 4)
    for k in range(1, n + 1):
        yield round(v - k * step, 4)
        yield round(v + k * step, 4)


def _box(spec, x, y, o):
    w, h, _ = spec
    return (x, y, x + h, y + w) if o in ("R90", "R270", "MXR90", "MYR90") else (x, y, x + w, y + h)


def _overlap(a, b):
    return a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6


def snap_axis(spec, o, tracks, axis, v, step, limit, fits):
    """nearest value on the step grid (from v) that puts every pin of the axis on track and fits(value); None if none"""
    shapes = _unique_axis(spec, o, tracks, axis)
    best = []
    for c in _candidates(v, step, limit):
        if best and abs(c - v) > abs(best[0] - v) + 1e-9:
            break
        if _axis_ok(shapes, c, tracks) and fits(c):
            best.append(c)
    if not best:
        return None
    if axis == "y" and len(best) > 1:              # equal distance: prefer the 2.16 macro grid
        best.sort(key=lambda c: (not _grid(c, MACRO_ROW_UM), c))
    return best[0]


def snap_all(placements, outline, tracks, env=None):
    """placements: [dict(inst, master, lef, x, y, o)] -> (new placements, receipt rows).  Only off-track macros move."""
    env = os.environ if env is None else env
    if env.get("OT_MACRO_GRID_SNAP", "1") == "0":
        return placements, []
    W, H = outline
    specs, out, rows = {}, [dict(p) for p in placements], []
    for p in out:
        k = (str(p["lef"]), p["master"])
        if k not in specs:
            specs[k] = lef_master(p["lef"], p["master"]) if p.get("lef") and Path(p["lef"]).is_file() else None
    boxes = [(_box(specs[(str(p["lef"]), p["master"])], p["x"], p["y"], p["o"])
              if specs[(str(p["lef"]), p["master"])] else None) for p in out]
    for i, p in enumerate(out):
        spec = specs[(str(p["lef"]), p["master"])]
        if not spec or not spec[2]:
            continue
        off = off_track(spec, p["x"], p["y"], p["o"], tracks)
        if not off["x"] and not off["y"]:
            continue
        x, y = p["x"], p["y"]

        def fits(nx, ny):
            b = _box(spec, nx, ny, p["o"])
            if b[0] < -1e-6 or b[1] < -1e-6 or b[2] > W + 1e-6 or b[3] > H + 1e-6:
                return False
            return not any(j != i and bj is not None and _overlap(b, bj) for j, bj in enumerate(boxes))
        nx, ny, off_row = x, y, False
        if off["y"]:
            ny = snap_axis(spec, p["o"], tracks, "y", y, ROW_UM if _grid(y, ROW_UM) else 0.001, SNAP_MAX_UM,
                           lambda c: fits(x, c))
            if ny is None and _grid(y, ROW_UM):    # no on-track origin on the row grid (pin phase vs rows): 1-nm steps
                ny = snap_axis(spec, p["o"], tracks, "y", y, 0.001, SNAP_MAX_UM, lambda c: fits(x, c))
                off_row = ny is not None
        if ny is not None and off["x"]:
            nx = snap_axis(spec, p["o"], tracks, "x", x, SITE_UM if _grid(x, SITE_UM) else 0.001, SNAP_MAX_UM,
                           lambda c: fits(c, ny))
        row = {"inst": p["inst"], "master": p["master"], "orient": p["o"], "plan_um": [x, y],
               "off_track_pins": off["x"] + off["y"]}
        if ny is None or nx is None:
            row["unresolved"] = f"no on-track origin within {SNAP_MAX_UM} um that fits the outline without overlap"
        else:
            row["snapped_um"] = [nx, ny]
            if off_row:
                row["off_row"] = True
            p["x"], p["y"] = nx, ny
            boxes[i] = _box(spec, nx, ny, p["o"])
        rows.append(row)
    return out, rows


def write_receipt(kd, rows):
    if rows:
        (Path(kd) / RECEIPT).write_text(json.dumps({"schema": "opentallas.macro_grid_snap.v1", "by": "KW-FIX-44",
                                                    "macros": rows}, indent=1) + "\n")


# ---- core-kit CLI (DIE-QC-97 11-11, NK pin-face rebuild: 4 NK + 2 NL rawfault_m3 at x 299.856 / 191.376 had 51 M5
# pins each 24 nm off the M5 tracks; DRC-clean but every V5 access via sat off track) ---------------------------------
# A gen_core_kit_qc.py core kit places its hard children in macro_place.tcl blocks (one 'set hit {}' block per child:
# master by name, setOrient, setLocation from the lower-left of the placed bbox).  --kit KIT reads those blocks, the
# kit ADDITIONAL_LEFS / DIE_AREA / make_tracks.tcl, runs snap_all and prints the receipt (dry run); --write rewrites
# the lower-left numbers of the moved children in macro_place.tcl (old file kept as macro_place.pre_mgs.tcl) and
# writes macro_grid_snap.json.  Exit 2 when a macro stays unresolved.
_BLOCK = re.compile(r"getName\] eq \"(?P<master>[^\"]+)\".*?error \"hard child (?P<inst>[^:\"]+):.*?"
                    r"\$i setOrient (?P<o>\S+).*?round\((?P<x>[-\d.]+) \* \$dbu\) - \[\$bb xMin\]\}\] "
                    r"\[expr \{round\((?P<y>[-\d.]+) \* \$dbu\) - \[\$bb yMin\]\}\]", re.S)


def kit_placements(kd):
    """[(placement dict, (x_span, y_span) of the numbers in macro_place.tcl, puts span or None)] of a core kit"""
    kd = Path(kd)
    cfg = (kd / "config.mk").read_text()
    lefs = []
    m = re.search(r"^export ADDITIONAL_LEFS\s*=\s*(.*)$", cfg, re.M)
    for t in (m.group(1).split() if m else []):
        p = kd / t[len("/work/"):] if t.startswith("/work/") else Path(t)
        lefs.append(p)
    da = re.search(r"^export DIE_AREA\s*=\s*" + r"\s+".join([KC._NUM] * 4), cfg, re.M)
    outline = (float(da.group(3)) - float(da.group(1)), float(da.group(4)) - float(da.group(2)))
    text = (kd / "macro_place.tcl").read_text()
    rows = []
    for b in _BLOCK.finditer(text):
        lef = next((p for p in lefs if p.is_file() and lef_master(p, b.group("master"))), None)
        rows.append((dict(inst=b.group("inst"), master=b.group("master"), lef=lef, x=float(b.group("x")),
                          y=float(b.group("y")), o=b.group("o")), (b.span("x"), b.span("y"))))
    return rows, outline, text


def _fmt(v):
    return ("%.4f" % v).rstrip("0").rstrip(".")


def kit_main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="KW-FIX-44 macro grid snap for a core kit macro_place.tcl")
    ap.add_argument("--kit", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    kd = Path(a.kit)
    rows, outline, text = kit_placements(kd)
    mt = kd / "make_tracks.tcl"
    tracks = tracks_for(mt.read_text() if mt.is_file() else None)
    out, rec = snap_all([r[0] for r in rows], outline, tracks)
    moved = [(rows[i], out[i]) for i in range(len(rows)) if (out[i]["x"], out[i]["y"]) != (rows[i][0]["x"], rows[i][0]["y"])]
    print(json.dumps({"macros": len(rows), "off_track": len(rec), "moved": len(moved),
                      "unresolved": sum(1 for r in rec if "unresolved" in r), "rows": rec}, indent=1))
    if a.write and moved:
        new = text
        for (old, (xs, ys)), p in sorted(moved, key=lambda m: -m[0][1][0][0]):   # right to left keeps spans valid
            new = new[:ys[0]] + _fmt(p["y"]) + new[ys[1]:]
            new = new[:xs[0]] + _fmt(p["x"]) + new[xs[1]:]
        (kd / "macro_place.pre_mgs.tcl").write_text(text)
        (kd / "macro_place.tcl").write_text(new)
        write_receipt(kd, rec)
    return 2 if any("unresolved" in r for r in rec) else 0


if __name__ == "__main__":
    raise SystemExit(kit_main())
