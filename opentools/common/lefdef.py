"""Minimal LEF/DEF readers for planning: macro SIZE + pin rectangles (LEF), DIEAREA + placed COMPONENTS (DEF).

Enough to turn a floorplanned DEF (e.g. an OpenROAD-flow-scripts 2_floorplan.def after macro placement) into an
opentools.plan/1 plan.  Not a general LEF/DEF parser: no vias, no nets, no special nets.
"""
import re
from pathlib import Path


def read_lef_macros(paths):
    """{macro: dict(w, h, cls, pins={pin: dict(use, direction, rects=[(layer, x0, y0, x1, y1)])})}"""
    out = {}
    for p in paths:
        txt = Path(p).read_text(errors="replace")
        for m in re.finditer(r"^\s*MACRO\s+(\S+)(.*?)^\s*END\s+\1\s*$", txt, re.S | re.M):
            name, body = m.group(1), m.group(2)
            sz = re.search(r"\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body)
            cl = re.search(r"\bCLASS\s+(\w+)", body)
            pins = {}
            for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\s*$", body, re.S | re.M):
                pb = pm.group(2)
                use = re.search(r"\bUSE\s+(\w+)", pb)
                dr = re.search(r"\bDIRECTION\s+(\w+)", pb)
                rects, layer = [], None
                for ln in pb.splitlines():
                    t = ln.split()
                    if len(t) >= 2 and t[0] == "LAYER":
                        layer = t[1]
                    elif len(t) >= 5 and t[0] == "RECT":
                        rects.append((layer,) + tuple(float(v) for v in t[1:5]))
                pins[pm.group(1)] = dict(use=use.group(1) if use else None, direction=dr.group(1) if dr else None,
                                         rects=rects)
            if sz:
                out[name] = dict(w=float(sz.group(1)), h=float(sz.group(2)), cls=cl.group(1) if cl else None, pins=pins)
    return out


def read_def(path):
    """dict(units, die=(x0, y0, x1, y1) um, comps=[dict(name, master, x, y, orient, status)] um)"""
    txt = Path(path).read_text(errors="replace")
    u = re.search(r"UNITS\s+DISTANCE\s+MICRONS\s+(\d+)", txt)
    units = float(u.group(1)) if u else 1000.0
    da = re.search(r"DIEAREA\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)", txt)
    die = tuple(float(v) / units for v in da.groups()) if da else None
    comps = []
    sec = re.search(r"^COMPONENTS\s+\d+\s*;(.*?)^END COMPONENTS", txt, re.S | re.M)
    if sec:
        for st in sec.group(1).split(";"):
            m = re.match(r"\s*-\s+(\S+)\s+(\S+)", st)
            if not m:
                continue
            pl = re.search(r"\+\s+(PLACED|FIXED|COVER)\s+\(\s*(-?\d+)\s+(-?\d+)\s*\)\s+(\w+)", st)
            if not pl:
                continue
            comps.append(dict(name=m.group(1).replace("\\", ""), master=m.group(2), status=pl.group(1),
                              x=float(pl.group(2)) / units, y=float(pl.group(3)) / units, orient=pl.group(4)))
    return dict(units=units, die=die, comps=comps)


def oriented_size(w, h, orient):
    return (h, w) if orient in ("E", "W", "FE", "FW") else (w, h)


def pin_point(macro, comp, pin):
    """die-frame centre of the pin's first rect for the 8 DEF orientations."""
    w, h = macro["w"], macro["h"]
    r = macro["pins"][pin]["rects"][0]
    cx, cy = (r[1] + r[3]) / 2, (r[2] + r[4]) / 2
    o = comp["orient"]
    tf = {"N": (cx, cy), "S": (w - cx, h - cy), "FN": (w - cx, cy), "FS": (cx, h - cy),
          "W": (h - cy, cx), "E": (cy, w - cx), "FW": (cy, cx), "FE": (h - cy, w - cx)}[o]
    return comp["x"] + tf[0], comp["y"] + tf[1]
