"""DIE-KV-62/hr 11-02: hard-child signal pins on the core routing tracks, for every planned orient.

The KV core kits use the DIE symmetric M4/M5 tracks (offset 0.024 + k 0.048, gen_core_kit_kv.make_tracks).  The native
SRAM views (tools/mem_compiler track-aligned v2) put each M4 signal pin centre at 0.012 mod 0.048 of the master frame, so
a planned site needs the phase that puts every pin centre on a PREFERRED-direction track of its layer (M4 horizontal:
core y; M5 vertical: core x) AFTER the orient transform.  A 90-degree orient swaps the axes: qkd_hr_phy_adp's R270 SRAM
had only an x phase, so every M4 pin centre was off the M4 tracks (DRT-0419) and pin access stopped the GRT
step (DRT-0073 'No access point for .../clk' -> run_kit_kv 'GRT hold repair step (FF vclk frame) failed').  The kit
generator runs this check on every native (M4-PG) hard child, fail-closed before any P&R, and names the site shift.

    python3 macro_pin_tracks.py PLAN.json LEF [LEF ...]     # OK, or the off-track pins + the site shift
"""
import json
import re
import sys
from pathlib import Path

PITCH = {"M4": 0.048, "M5": 0.048}
OFFSET = {"M4": 0.024, "M5": 0.024}
PREFERRED = {"M4": "y", "M5": "x"}       # ASAP7: M4 horizontal (track = y), M5 vertical (track = x)
EPS = 1e-6


def lef_master(text, master):
    """(W, H, {pin: [(layer, cx, cy)]}) of MACRO master: M4/M5 signal pin shapes (USE POWER / GROUND skipped)."""
    m = re.search(rf"^MACRO\s+{re.escape(master)}\s*$(.*?)^END\s+{re.escape(master)}\s*$", text, re.M | re.S)
    if not m:
        raise ValueError(f"LEF has no MACRO {master}")
    body = m.group(1)
    size = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body)
    pins = {}
    for pm in re.finditer(r"^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+(\S+)\s*$", body, re.M | re.S):
        name, pb = pm.group(1), pm.group(2)
        if pm.group(3) != name or re.search(r"\bUSE\s+(POWER|GROUND)\b", pb):
            continue
        layer = None
        for tok in re.finditer(r"\bLAYER\s+(\S+)\s*;|\bRECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*;", pb):
            if tok.group(1):
                layer = tok.group(1)
            elif layer in PITCH:
                x0, y0, x1, y1 = (float(tok.group(k)) for k in range(2, 6))
                pins.setdefault(name, []).append((layer, (x0 + x1) / 2, (y0 + y1) / 2))
    return float(size.group(1)), float(size.group(2)), pins


def place(x, y, w, h, orient, ox, oy):
    """master point (x, y) of a W x H master -> core point, OpenDB orient with the bbox lower-left at (ox, oy)."""
    t = {"R0": (x, y), "R90": (h - y, x), "R180": (w - x, h - y), "R270": (y, w - x),
         "MX": (x, h - y), "MY": (w - x, y), "MXR90": (y, x), "MYR90": (h - y, w - x)}
    if orient not in t:
        raise ValueError(f"unknown orient {orient}")
    px, py = t[orient]
    return ox + px, oy + py


def _phase(v, layer):
    q = (v - OFFSET[layer]) / PITCH[layer]
    return (q - round(q)) * PITCH[layer]


def off_track(block, w, h, pins):
    """[(pin, layer, cx, cy, dx, dy)] for pin centres off the preferred-direction tracks of their layer (DRT pin access
    needs a preferred track through the pin centre; dx / dy = the phase error on the checked axis, 0 on the other)."""
    bad = []
    for name, shapes in sorted(pins.items()):
        for layer, mx, my in shapes:
            cx, cy = place(mx, my, w, h, block["orient"], block["x"], block["y"])
            dx = _phase(cx, layer) if PREFERRED[layer] == "x" else 0.0
            dy = _phase(cy, layer) if PREFERRED[layer] == "y" else 0.0
            if abs(dx) > EPS or abs(dy) > EPS:
                bad.append((name, layer, round(cx, 4), round(cy, 4), round(dx, 4), round(dy, 4)))
    return bad


def check(blocks, lef_text_of):
    """fail-closed: SystemExit naming the first off-track pins and the site shift that fixes them (the v2 views keep one
    pin phase per master, so one shift fixes the block)."""
    errs = []
    for b in blocks:
        w, h, pins = lef_master(lef_text_of(b["master"]), b["master"])
        bad = off_track(b, w, h, pins)
        if bad:
            sx, sy = -bad[0][4] + 0.0, -bad[0][5] + 0.0
            errs.append(f"{b['inst']} {b['master']} {b['orient']} at ({b['x']}, {b['y']}): {len(bad)} signal pin "
                        f"centres off the M4/M5 tracks, e.g. {bad[:3]}; shift the site by ({sx:+.3f}, {sy:+.3f}) um")
    if errs:
        raise SystemExit("hard-child pins off the core tracks (DRT-0073 at GRT pin access): " + "; ".join(errs))
    return True


def main(argv):
    plan = json.load(open(argv[0]))
    texts = [Path(f).read_text() for f in argv[1:]]

    def lef_of(m):
        for t in texts:
            if re.search(rf"^MACRO\s+{re.escape(m)}\s*$", t, re.M):
                return t
        raise SystemExit(f"no LEF for {m}")
    check(plan["blocks"], lef_of)
    print(f"OK {len(plan['blocks'])} hard child(ren): every signal pin centre on a preferred M4/M5 track")


if __name__ == "__main__":
    main(sys.argv[1:])
