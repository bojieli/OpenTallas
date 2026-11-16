#!/usr/bin/env python3
"""Snap a hard core's declared pins onto the plan track grid by shifting the pin metal along the track axis
(S81-T51-PINFIX-1 / S81-T51-BUILD-1; DRT-0073 class: a pin whose centre is off the routing track of its layer).

The shift is derived, not given: for the core row (origin_um, track_offset_um, outline, orient) of a plan, the
residue (origin + offset + pin centre - track offset) mod pitch of the selected pins must be ONE value (all selected
pins off by the same amount), and the shift is the smaller of (-r, pitch - r) nm.  The same shift is applied to
  * pins.json  (list rows: x and every native_rects box of the pin, layer + name selected), and the
    declared_pin_contract/pins.json ({"pins": [...]}) copy, and
  * io.tcl     (the native multiPORT `dbBox_create ... findLayer <L>` boxes of the selected BTerms),
so the kit places exactly the snapped metal.  Pin width, y and the logical anchor are unchanged (the anchor moves with
the metal so it stays inside its rect).

  python3 -I pin_track_snap.py KITDIR --layer M7 --names '^clk_' --origin X Y --offset DX DY --orient R0
                                [--check]     (--check: report only)
"""
import argparse
import json
import re
import sys
from pathlib import Path

# M7: die/parent lattice (pitch 64, offset 32 nm) = gen_core_kit_legacy.M7_LATTICE = plan die.layers M7 (was 16: stale,
# every shift was 16 nm off; test_m7_track_matches_gen_lattice pins it to the generator).
TRACKS = {"M7": ("x", 32, 64), "M9": ("x", 20, 80), "M8": ("y", 20, 80)}


def nm(v):
    return int(round(float(v) * 1000))


def local_nm(p, w, h, orient, axis):
    x, y = nm(p["x"]), nm(p["y"])
    if orient in ("MY", "R180"):
        x = nm(w) - x
    if orient in ("MX", "R180"):
        y = nm(h) - y
    return x if axis == "x" else y


def derive_shift(pins, layer, rx, origin, offset, outline, orient="R0"):
    """-> (shift_nm in the pin's own (core) frame, {residue: count}); raises if the selected pins disagree"""
    axis, off, pitch = TRACKS[layer]
    ai = 0 if axis == "x" else 1
    res = {}
    for p in pins:
        if p["layer"] != layer or not rx.search(p.get("bus", p.get("name", ""))):
            continue
        g = nm(origin[ai]) + nm(offset[ai]) + local_nm(p, outline[0], outline[1], orient, axis)
        r = (g - off) % pitch
        res[r] = res.get(r, 0) + 1
    if not res:
        raise SystemExit("no pins selected")
    if len(res) != 1:
        raise SystemExit(f"selected pins have different residues {res}; refusing to snap")
    r = next(iter(res))
    if r == 0:
        return 0, res
    s = -r if r <= pitch // 2 else pitch - r            # shift of the die/type-frame coordinate
    flip = (orient in ("MY", "R180")) if axis == "x" else (orient in ("MX", "R180"))
    return (-s if flip else s), res                      # a mirrored core moves its own-frame pin the other way


def shift_pin_rows(rows, layer, rx, dnm, axis="x"):
    d = dnm / 1000.0
    n = 0
    for p in rows:
        if p["layer"] != layer or not rx.search(p.get("bus", p.get("name", ""))):
            continue
        p[axis] = round(p[axis] + d, 4)
        ai = 1 if axis == "x" else 2
        for b in p.get("native_rects") or []:
            if b[0] == layer:
                b[ai] = round(b[ai] + d, 4)
                b[ai + 2] = round(b[ai + 2] + d, 4)
        n += 1
    return n


NUM = r"[-0-9.]+"
IO_BOX = re.compile(r"(?P<pre>odb::dbBox_create \$ot_mp_bp \[\[ord::get_db_tech\] findLayer (?P<layer>\w+)\] "
                    r"\[expr \{int\(round\()(?P<x0>" + NUM + r")(?P<mid>\*\$ot_mp_u\)\)\}\] "
                    r"\[expr \{int\(round\(" + NUM + r"\*\$ot_mp_u\)\)\}\] "
                    r"\[expr \{int\(round\()(?P<x1>" + NUM + r")(?P<post>\*\$ot_mp_u\)\)\}\])")


def shift_io_tcl(text, layer, rx, dnm):
    """shift x0/x1 of every native multiPORT box on `layer` whose BTerm name matches rx"""
    d = dnm / 1000.0
    out, name, n = [], None, 0
    for line in text.split("\n"):
        m = re.search(r"findBTerm \{([^}]+)\}", line)
        if m:
            name = m.group(1)
        if name and rx.search(name) and "dbBox_create $ot_mp_bp" in line:
            mm = IO_BOX.search(line)
            if mm and mm.group("layer") == layer:
                seg = mm.group(0)
                seg = seg.replace(mm.group("x0") + mm.group("mid"), f"{float(mm.group('x0')) + d:.6f}" + mm.group("mid"), 1)
                seg = seg[:seg.rindex(mm.group("x1"))] + f"{float(mm.group('x1')) + d:.6f}" + seg[seg.rindex(mm.group("x1")) + len(mm.group("x1")):]
                line = line[:mm.start()] + seg + line[mm.end():]
                n += 1
        out.append(line)
    return "\n".join(out), n


def shift_clock_roots(d, layer, rx, dnm):
    """clock_roots.json entries[].plan_xy_um = [x, y, layer] of the root pins (kit CTS root map)"""
    n = 0
    for e in d.get("entries") or []:
        xy = e.get("plan_xy_um")
        if xy and xy[2] == layer and rx.search(e.get("pin", "")):
            xy[0] = round(xy[0] + dnm / 1000.0, 4)
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("--layer", default="M7")
    ap.add_argument("--names", default=r"^clk_")
    ap.add_argument("--origin", nargs=2, type=float, required=True)
    ap.add_argument("--offset", nargs=2, type=float, required=True)
    ap.add_argument("--outline", nargs=2, type=float, required=True)
    ap.add_argument("--orient", default="R0")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--roots-only-shift-nm", type=int, default=None,
                    help="only patch clock_roots.json by this shift (kits already snapped by an older version)")
    a = ap.parse_args(argv)
    kit = Path(a.kit)
    rx = re.compile(a.names)
    if a.roots_only_shift_nm is not None:
        cr = json.loads((kit / "clock_roots.json").read_text())
        n = shift_clock_roots(cr, a.layer, rx, a.roots_only_shift_nm)
        (kit / "clock_roots.json").write_text(json.dumps(cr, indent=1) + "\n")
        print(f"pin_track_snap: clock_roots.json entries {n}")
        return 0
    pins = json.loads((kit / "pins.json").read_text())
    shift, res = derive_shift(pins, a.layer, rx, a.origin, a.offset, a.outline, a.orient)
    axis = TRACKS[a.layer][0]
    print(f"pin_track_snap: residues {res} -> shift {shift} nm along {axis}")
    if a.check or shift == 0:
        return 0
    n1 = shift_pin_rows(pins, a.layer, rx, shift, axis)
    (kit / "pins.json").write_text(json.dumps(pins, indent=1) + "\n")
    dc = kit / "declared_pin_contract/pins.json"
    n2 = 0
    if dc.is_file():
        d = json.loads(dc.read_text())
        n2 = shift_pin_rows(d["pins"], a.layer, rx, shift, axis)
        dc.write_text(json.dumps(d, indent=1) + "\n")
    t, n3 = shift_io_tcl((kit / "io.tcl").read_text(), a.layer, rx, shift)
    (kit / "io.tcl").write_text(t)
    n4 = 0
    if (kit / "clock_roots.json").is_file():
        cr = json.loads((kit / "clock_roots.json").read_text())
        n4 = shift_clock_roots(cr, a.layer, rx, shift)
        (kit / "clock_roots.json").write_text(json.dumps(cr, indent=1) + "\n")
    print(f"pin_track_snap: pins.json {n1}, declared_pin_contract {n2}, io.tcl boxes {n3}, clock_roots entries {n4}")
    if not (n1 == n3 and (n2 in (0, n1))):
        raise SystemExit("snap counts disagree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
