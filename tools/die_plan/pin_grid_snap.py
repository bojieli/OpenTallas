#!/usr/bin/env python3
"""Snap a kit's io.tcl pins onto their layer's track grid (KW-FIX-44 11-10, COORD; DIE-HBM-97 dma vPose2: a pin
respread put all 2,420 N pins at x = 0.048 k, half a track off the kit's M5 tracks -> 10 M5 shorts).

Every place_pin whose rectangle runs along its layer's preferred direction (the pins kit_gen_lint pin_grid judges) moves
its centre to the nearest track of that layer (kit make_tracks, else the platform offsets; kit_contract._kit_tracks),
across the tracks only.  pins.json rows of the same pin (bus/bit or name, with x/y or xy_um) move with it.  Two pins of
one layer that would land on the same track and overlap along it are not moved (listed as unresolved).

  pin_grid_snap.py KIT            report only
  pin_grid_snap.py KIT --write    rewrite io.tcl (+ pins.json), receipt KIT/pin_grid_snap.json

Run it right after any pin respread script, before kit_gen_lint.  A kit whose pins are plan pins must take the same move
through a plan event (pins_vs_plan compares io.tcl with the plan).
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC  # noqa: E402


def _fmt(v):
    return f"{v:.4f}"


def plan(kd):
    """[(line index, name, layer, axis, old, new)] moves and [unresolved names]"""
    kd = Path(kd)
    tracks, _src = KC._kit_tracks(kd, KC._mk(kd))
    lines = (kd / "io.tcl").read_text(errors="replace").splitlines(keepends=True)
    moves, spans = [], {}
    for i, line in enumerate(lines):
        m = KC._PLACE_PIN.match(KC._strip_tcl_comment(line))
        if not m:
            continue
        name, layer = m.group(1).strip("{}"), m.group(2)
        x, y = float(m.group(3)), float(m.group(4))
        w, h = (float(m.group(5)), float(m.group(6))) if m.group(5) else (None, None)
        if layer not in tracks:
            continue
        d, pitch, _width, offsets = tracks[layer]
        if w is not None and h is not None and ((d == "V" and w > h) or (d == "H" and h > w)):
            continue
        c, along, half = (x, y, (h or 0) / 2) if d == "V" else (y, x, (w or 0) / 2)
        best = min(((of + round((c - of) / pitch) * pitch) for of in offsets), key=lambda t: abs(t - c))
        t = round(best, 4)
        spans.setdefault((layer, t), []).append((along - half, along + half, name))
        if abs(t - c) > KC.GRID_TOL:
            moves.append((i, name, layer, "x" if d == "V" else "y", c, t))
    clash = set()
    for segs in spans.values():
        segs.sort()
        for (a0, a1, n0), (b0, b1, n1) in zip(segs, segs[1:]):
            if b0 < a1 - 1e-6:
                clash.update((n0, n1))
    keep = [mv for mv in moves if mv[1] not in clash]
    return keep, sorted(clash & {mv[1] for mv in moves}), lines


def apply(kd, moves, lines):
    kd = Path(kd)
    by = {}
    for i, name, layer, axis, old, new in moves:
        line = lines[i]
        m = KC._PLACE_PIN.match(line)
        g = 3 if axis == "x" else 4
        lines[i] = line[:m.start(g)] + _fmt(new) + line[m.end(g):]
        by[name] = (axis, old, new)
    (kd / "io.tcl").write_text("".join(lines))
    pj = kd / "pins.json"
    moved_json = 0
    if pj.is_file() and by:
        data = json.loads(pj.read_text())
        rows = data.get("pins", []) if isinstance(data, dict) else data
        for r in rows:
            if not isinstance(r, dict):
                continue
            nm = r.get("name") or (r.get("bus") if r.get("bit") is None else f"{r.get('bus')}[{r.get('bit')}]")
            if nm not in by:
                continue
            axis, old, new = by[nm]
            if axis in r and abs(float(r[axis]) - old) <= 0.05:
                r[axis] = round(new, 4)
                moved_json += 1
            elif isinstance(r.get("xy_um"), list) and abs(float(r["xy_um"][0 if axis == "x" else 1]) - old) <= 0.05:
                r["xy_um"][0 if axis == "x" else 1] = round(new, 4)
                moved_json += 1
        pj.write_text(json.dumps(data, indent=1) + "\n")
    return moved_json


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kit", type=Path)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    moves, clash, lines = plan(a.kit)
    worst = max((abs(n - o) for *_r, o, n in moves), default=0.0)
    rec = dict(schema="opentallas.pin_grid_snap.v1", kit=str(a.kit), moved=len(moves), unresolved=clash,
               worst_move_nm=round(worst * 1000, 1), moves=[dict(pin=n, layer=l, axis=ax, old=round(o, 4), new=t)
                                                             for _i, n, l, ax, o, t in moves[:200]])
    if a.write and moves:
        rec["pins_json_moved"] = apply(a.kit, moves, lines)
        (a.kit / "pin_grid_snap.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(f"PIN_GRID_SNAP {'WROTE' if a.write and moves else 'DRY'} moved {len(moves)} worst {rec['worst_move_nm']} nm "
          f"unresolved {len(clash)}")
    return 1 if clash else 0


if __name__ == "__main__":
    raise SystemExit(main())
