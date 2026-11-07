"""PINBAND-1 (COORD ruling 17:4x 11-06, class found by QC-A0C-B6): gen-time hard-child siting check, default-on.

Class: a hard child's signal M5 pin that lies under a parent M6 PG stripe band (add_pdn_stripe -grid top -layer M6:
offset + k*pitch, band = 2*width + spacing wide) has no via up to M6 that does not short VDD/VSS.  QC NL (DRC 3) and NK
(DRC 50) were this class: the rawfault clk pin sits mid-macro inside the macro's M5 OBS, so the via up is its only
access.

Check (same numbers as QC-A0C-B6 pinband.py): a signal M5 pin row (y0, y1) is BAD when its longest y segment clear of
every band (+-MARG) is shorter than min(VIA, y1 - y0).  Edge rows count too: NK's 50 VSS shorts were the 0.084-tall
edge pin row of R180/MX rawleafs under a band (QC-A0C-B6 17:35), so an in-plane M5 exit does not save it.

Fix: the smallest y move of the child that clears every pin row (when no grid-keeping move clears all of them, the
legal move that leaves the fewest bad rows, reported as partial).  The step keeps the child on its grids: a
multiple of the 0.27 um placement row and of the y pitch of each horizontal layer that carries one of its signal pins
(M4 0.048, M6 0.064, M8 0.08; M2 rows 0.27), so an M4-track-snapped site stays snapped.  A move must keep the child
inside the core and its gap to every other child / macro >= min(original gap, MIN_GAP).  No legal move = the child
stays and the row is reported as refused (advisory; only sign-off blocks).

OT_PINBAND_SITE=0 in the environment turns the move off (check + report only)."""
import json
import math
import os
import re

VIA, MARG, ROW, MIN_GAP, MAX_DY = 0.144, 0.05, 0.27, 1.0, 4.32   # MAX_DY = one band pitch
FLAT = ("R0", "MY", "MX", "R180", "N", "FN", "S", "FS")      # 90-degree rotated children are reported, not checked
Y_PITCH_NM = {"M2": 270, "M4": 48, "M6": 64, "M8": 80}     # horizontal layers (y tracks) of the ASAP7 kit stack


# the partition / core top-grid M6 stripe pair every ASAP7 kit generator here writes (gen_phys PDN, core PDN_* texts)
PARTITION_M6 = "add_pdn_stripe -grid {top} -layer {M6} -width {0.288} -spacing {0.096} -pitch {4.32} -offset {1.968}\n"


def enabled():
    return os.environ.get("OT_PINBAND_SITE", "1") not in ("0", "off", "false")


def stripes(pdn_text):
    """[(offset, pitch, band)] of the M6 stripes of the non-macro grids of a pdn.tcl text"""
    macro_grids = set(re.findall(r"define_pdn_grid\s+-macro\b.*?-name\s+\{?([^\s}]+)", pdn_text))
    out = []
    for ln in pdn_text.splitlines():
        if not ln.lstrip().startswith("add_pdn_stripe") or not re.search(r"-layer\s+\{?M6\}?(\s|$)", ln):
            continue
        g = re.search(r"-grid\s+\{?([^\s}]+)", ln)
        if g and g.group(1) in macro_grids:
            continue
        v = {k: float(re.search(r"-%s\s+\{?([-\d.]+)" % k, ln).group(1)) if re.search(r"-%s\s" % k, ln) else None
             for k in ("width", "spacing", "pitch", "offset")}
        if not v["pitch"]:
            continue
        band = round(2 * v["width"] + v["spacing"] if v["spacing"] is not None else v["width"], 6)
        out.append((v["offset"] or 0.0, v["pitch"], band))
    return sorted(set(out))


def macro_body(lef_text, master=None):
    ms = re.findall(r"^\s*MACRO\s+(\S+)(.*?)^\s*END\s+\1\b", lef_text, re.S | re.M)
    for n, b in ms:
        if master is None or n == master:
            return b
    return ms[0][1] if len(ms) == 1 else None


def pin_rows(body):
    """(w, h, m5 rows [(y0, y1, touches the bottom/top edge)], horizontal signal pin layers) of a LEF MACRO body"""
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body).groups())
    rows, hl = set(), set()
    for n, b in re.findall(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", body, re.S | re.M):
        if re.search(r"USE\s+(POWER|GROUND)", b):
            continue
        cur = None
        for ln in b.splitlines():
            ml = re.search(r"LAYER\s+(\S+)", ln)
            if ml:
                cur = ml.group(1)
                if cur in Y_PITCH_NM:
                    hl.add(cur)
            mr = re.search(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", ln)
            if mr and cur == "M5":
                y0, y1 = float(mr.group(2)), float(mr.group(4))
                rows.add((y0, y1, y0 <= 1e-6 or y1 >= h - 1e-6))
    return w, h, sorted(rows), sorted(hl)


def step_um(layers):
    s = Y_PITCH_NM["M2"]
    for L in layers:
        s = s * Y_PITCH_NM[L] // math.gcd(s, Y_PITCH_NM[L])
    return s / 1000.0


def row_bad(y0, y1, bands):
    segs = [(y0, y1)]
    for off, pi, bw in bands:
        k0 = int((y0 - off - bw - MARG) // pi) - 1
        for k in range(k0, k0 + int((y1 - y0) // pi) + 4):
            b0, b1 = off + k * pi - MARG, off + k * pi + bw + MARG
            nxt = []
            for a, b in segs:
                if b <= b0 or a >= b1:
                    nxt.append((a, b))
                else:
                    if a < b0:
                        nxt.append((a, b0))
                    if b > b1:
                        nxt.append((b1, b))
            segs = nxt
    return max([b - a for a, b in segs] + [0]) < min(VIA, y1 - y0) - 1e-9


def abs_rows(rows, h, orient, y):
    flip = orient in ("MX", "R180", "FS", "S")
    return [(y + (h - r1 if flip else r0), y + (h - r0 if flip else r1), e) for r0, r1, e in rows]


def _gap(a, b):
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return math.hypot(dx, dy) if dx and dy else max(dx, dy)


def site(children, pdn_text, core, lef_text, others=(), move=None):
    """children: [dict(inst, master, orient, x, y)] (core-frame lower-left sites); y is changed in place for a moved
    child.  pdn_text: the kit pdn.tcl text (top-grid M6 stripes); core: (x0, y0, x1, y1) = CORE_AREA (the pdn grid
    origin); lef_text(master) -> LEF text; others: [(x0, y0, x1, y1)] fixed boxes the moves keep their gap to.
    Returns the report dict (schema opentallas.pinband_site.v1)."""
    move = enabled() if move is None else move
    st = stripes(pdn_text)
    bands = [(core[1] + o, p, b) for o, p, b in st]
    rep = dict(schema="opentallas.pinband_site.v1", rule=__doc__.split("\n")[0], move=bool(move),
               bands=[list(s) for s in st], checked=len(children), moved=[], refused=[])
    if not bands or not children:
        return rep
    geo = {}
    for c in children:
        if c["master"] not in geo:
            body = macro_body(lef_text(c["master"]), c["master"])
            geo[c["master"]] = pin_rows(body) if body else None
    box = lambda c, dy=0.0: (c["x"], c["y"] + dy, c["x"] + geo[c["master"]][0], c["y"] + dy + geo[c["master"]][1])
    kids = [c for c in children if geo.get(c["master"]) and c["orient"] in FLAT]
    rep["not_checked_rotated"] = sorted(c["inst"] for c in children if c["orient"] not in FLAT)
    others = [tuple(o) for o in others]
    for c in kids:
        w, h, rows, hl = geo[c["master"]]
        ab = abs_rows(rows, h, c["orient"], c["y"])
        nint = sum(1 for a, b, e in ab if row_bad(a, b, bands))
        if not nint:
            continue
        s = step_um(hl)
        g0 = [(_gap(box(c), box(d)), d) for d in kids if d is not c] + [(_gap(box(c), o), o) for o in others]
        cand = []
        for k in range(1, int(MAX_DY / s) + 1):
            for dy in (k * s, -k * s):
                r2 = abs_rows(rows, h, c["orient"], c["y"] + dy)
                nb = sum(1 for a, b, e in r2 if row_bad(a, b, bands))
                if nb >= nint:
                    continue
                bx = box(c, dy)
                if bx[1] < core[1] - 1e-6 or bx[3] > core[3] + 1e-6:
                    continue
                if any(_gap(bx, box(d) if isinstance(d, dict) else d) < min(g, MIN_GAP) - 1e-9 for g, d in g0):
                    continue
                cand.append((nb, abs(dy), -dy, dy))
        row = dict(inst=c["inst"], master=c["master"], orient=c["orient"], x=c["x"], y=c["y"], rows=nint, step=s)
        if not cand:
            rep["refused"].append(dict(row, why=f"no legal {s:g}-um-multiple move within {MAX_DY:g} um"))
            continue
        nb, _, _, dy = min(cand)
        dy = round(dy, 4)
        row.update(dy=dy, y_new=round(c["y"] + dy, 4), rows_left=nb)
        if nb:
            # rows at spacings no grid-keeping step can clear together (e.g. two edge rows 2.16 apart mod 4.32 with
            # a 2.16 M4/row step): take the legal move with the fewest rows left and report the rest
            row["partial"] = f"{nb} row(s) stay under a band: no {s:g}-um-multiple move within {MAX_DY:g} um clears all"
            rep.setdefault("partial", []).append(row["inst"])
        if move:
            c["y"] = row["y_new"]
            rep["moved"].append(row)
        else:
            rep["refused"].append(dict(row, why="OT_PINBAND_SITE=0 (check only)"))
    return rep


def write_report(kd, rep):
    with open(os.path.join(str(kd), "pinband_sites.json"), "w") as f:
        f.write(json.dumps(rep, indent=1) + "\n")
    return rep


def site_rows(kd, rows, pdn_text, core, lef_dir=None, others=(), move=None, xy="at", master="master", inst="inst",
              lef_fn=None):
    """generator form: rows = the generator's own site dicts (QC/S81 hard children {inst, master, at, orient}, KV
    blocks {inst, master, x, y, orient} with xy=None, HBM macro_placement {inst, macro, xy_um} with xy="xy_um",
    master="macro"); y is rewritten in place for each moved row.  LEFs: lef_dir (default kd/macros)/<master>.lef, or
    lef_dir(master) -> LEF path when callable.
    Writes kd/pinband_sites.json and returns the report."""
    from pathlib import Path
    lp = lef_dir if callable(lef_dir) else (lambda m, d=Path(lef_dir) if lef_dir else Path(kd) / "macros": d / f"{m}.lef")
    lt = lambda m: (lef_fn or (lambda t: t))(Path(lp(m)).read_text(errors="replace"))
    kids, back = [], []
    for r in rows:
        x, y = (r[xy][0], r[xy][1]) if xy else (r["x"], r["y"])
        if not Path(lp(r[master])).is_file():
            continue
        k = dict(inst=r[inst], master=r[master], orient=r.get("orient", "R0"), x=float(x), y=float(y))
        kids.append(k)
        back.append((r, k))
    rep = site(kids, pdn_text, core, lt, others=others, move=move)
    for r, k in back:
        if abs(k["y"] - float(r[xy][1] if xy else r["y"])) > 1e-9:
            if xy and isinstance(r[xy], list):
                r[xy][1] = k["y"]          # in place: callers may share the site list (S81 spec macros[].at)
            elif xy:
                r[xy] = (r[xy][0], k["y"])
            else:
                r["y"] = k["y"]
    return write_report(kd, rep)
