"""QC-PLAN-F4A G1 macro-pin track check (COORD RULING QC-PLAN-F4A (1)).

Every signal pin shape of every placed macro must sit on the kit routing track of its layer:
vertical M5 -> pin centre x on (x - 0.012) % 0.048 == 0, horizontal M4 -> pin centre y on (y - 0.012) % 0.048 == 0
(ASAP7 kit tracks, make_tracks M4/M5 offset 0.012 pitch 0.048).  Orientation per DEF (R0, MY, MX, R180).
usage: macro_tracks.py LEF_DIR GEO.json  -> JSON verdict;  snap_origin_x(...) used by the floorplan generator."""
import json
import re
import sys
from pathlib import Path

TRK = {"M5": ("x", 0.012, 0.048), "M4": ("y", 0.012, 0.048), "M3": ("x", 0.012, 0.036), "M2": ("y", 0.0, 0.036)}


def lef_pins(lef):
    t = Path(lef).read_text()
    size = [float(v) for v in re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t).groups()]
    pins = []
    for m in re.finditer(r"\n\s*PIN\s+(\S+)(.*?)\n\s*END\s+\1", t, re.S):
        name, body = m.group(1), m.group(2)
        if re.search(r"USE\s+(POWER|GROUND)", body):
            continue
        lay = None
        for ln in body.splitlines():
            ln = ln.strip()
            if ln.startswith("LAYER"):
                lay = ln.split()[1]
            elif ln.startswith("RECT") and lay:
                x0, y0, x1, y1 = [float(v) for v in ln.split()[1:5]]
                pins.append((name, lay, (x0 + x1) / 2, (y0 + y1) / 2))
    return size, pins


def place(size, x, y, o, px, py):
    w, h = size
    if o == "R0":
        return x + px, y + py
    if o == "MY":
        return x + w - px, y + py
    if o == "MX":
        return x + px, y + h - py
    if o == "R180":
        return x + w - px, y + h - py
    raise ValueError(o)


def off_track(v, off, pitch):
    r = (v - off) / pitch
    return abs(r - round(r)) * pitch


def check(size, pins, x, y, o, tol=1e-4):
    bad = []
    for n, lay, px, py in pins:
        if lay not in TRK:
            continue
        ax, off, pitch = TRK[lay]
        gx, gy = place(size, x, y, o, px, py)
        d = off_track(gx if ax == "x" else gy, off, pitch)
        if d > tol:
            bad.append((n, lay, round(gx, 4), round(gy, 4), round(d, 4)))
    return bad


def snap_origin_x(size, pins, x, y, o, prefer=-1, step=0.012):
    """nearest origin x (prefer = -1 west / +1 east on ties) with every M5 pin on track; macro origin stays on 0.012."""
    for k in range(0, 9):
        for s in ((prefer, -prefer) if k else (0,)):
            xc = round(x + s * k * step, 4)
            if not [b for b in check(size, pins, xc, y, o) if b[1] == "M5"]:
                return xc
    raise RuntimeError("no on-track origin within 0.1 um")


if __name__ == "__main__":
    lefdir, geo = sys.argv[1], sys.argv[2]
    g = json.loads(Path(geo).read_text())
    out = dict(check="G1_macro_pin_on_track", geo=geo, macros=[])
    for name, cell, box, o, _ck in g["macros"]:
        size, pins = lef_pins(next(Path(lefdir).glob(f"{cell}/{cell}.lef")))
        bad = check(size, pins, box[0], box[1], o)
        out["macros"].append(dict(inst=name, cell=cell, origin=[round(box[0], 4), round(box[1], 4)], orient=o,
                                  pins_checked=sum(1 for p in pins if p[1] in TRK), off_track=len(bad), first=bad[:3]))
    out["verdict"] = "PASS" if all(m["off_track"] == 0 for m in out["macros"]) else "FAIL"
    print(json.dumps(out, indent=1))
    sys.exit(0 if out["verdict"] == "PASS" else 1)
