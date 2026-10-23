#!/usr/bin/env python3
"""layout_review.py -- physical-design review picture + statistics for every ref_tile gate (TILE-REVIEW 2026-10-23).

The owner ordered a visual PD review of every unclosed tile (10-23).  The review found tiles whose outline was set far
larger than their logic (std-cell fill of the free area < 10 %) and parents whose pin registers sit hundreds of um away
from their pins.  This module makes the pre-route gate ALWAYS write

    <kit>/gate_layout/review.png         std-cell density heatmap (bins), macros (grey; red outline = signal pins face
                                         away from their logic), top pins (cyan), pin-register flops (green), pin ->
                                         register links > 100 um (yellow), clock root buffers (red) and 2nd level (orange)
    <kit>/gate_layout/review_stats.json  outline, aspect, macro %, std-cell area and fill of the free area, FF and buf/inv
                                         counts, pins per face and per um, pin -> register median / p90, empty-area %,
                                         pin / macro OBS layers, suspicion flags

and judges two rules:
    * std-cell fill of the free (non-macro) area < 20 %   (FILL_FREE_FAIL; WARN with a spec "low_fill_reason", a
                                                           measured parent band, or a GEOM-REVIEW PASS/PASS-CONDITIONAL
                                                           for the kit's content hash)
    * pin -> pin-register p90 distance > 150 um            (PIN_REG_P90_FAIL; WARN only with a GEOM-REVIEW PASS /
                                                           PASS-CONDITIONAL for the content hash or a spec "pin_reg_reason")

Input: a tools/ref_tile/layout_dump.tcl JSON dump (opentallas.layout.occupancy.v1) of a PLACED design; the dump's
optional "pin_regs" [[pin, kind R|M|N, px, py, fx, fy, depth]] and "clock_roots" [[inst, master, x0, y0, x1, y1, level]]
come from the same dump script.  Floorplan-only dumps get a picture and stats but are not judged (no placement).

    python3 tools/ref_tile/layout_review.py DUMP.json OUTDIR [--title T] [--spec spec.json]
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout_png as LP  # noqa: E402

FILL_FREE_FAIL = 0.20
PIN_REG_P90_FAIL = 150.0
PIN_REG_P90_FLAG = 100.0
EMPTY_FLAG = 0.50
BUF_FLAG = 0.40
PIN_PER_UM_FLAG = 4.0
EMPTY_BIN_DENSITY = 0.05
FILL_PREFIX = ("TAPCELL", "FILLER", "DECAP", "FILL")
SEQ_RE = re.compile(r"^(DFF|DHL|DLL|SDF|ASYNC|ICG)")
BUF_RE = re.compile(r"^(BUF|INV|HB|CKINV|CKBUF)")


def _q(vals, q):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def face_of(x, y, die, tol=2.0):
    X0, Y0, X1, Y1 = die
    if x < X0 + tol:
        return "W"
    if x > X1 - tol:
        return "E"
    if y < Y0 + tol:
        return "S"
    if y > Y1 - tol:
        return "N"
    return "area"


def _std(d):
    """placed, non-filler std cells as (name, master, x0, y0, x1, y1)"""
    out = []
    for c in d.get("std_cells") or []:
        name, master, status, *r = c
        if str(master).startswith(FILL_PREFIX) or str(status).upper() in ("NONE", "UNPLACED"):
            continue
        out.append((name, master, *map(float, r)))
    return out


def review_stats(d: dict, bins: int = 80) -> dict:
    X0, Y0, X1, Y1 = map(float, d["die"])
    W, H = X1 - X0, Y1 - Y0
    blocks = [(b[0], b[1], *map(float, b[2:6])) for b in d.get("blocks") or []]

    def clip(r):
        return max(0.0, min(r[2], X1) - max(r[0], X0)) * max(0.0, min(r[3], Y1) - max(r[1], Y0))
    barea = sum(clip(b[2:6]) for b in blocks)
    free = max(0.0, W * H - barea)
    cells = _std(d)
    placed = bool(cells)
    sarea = sum((c[4] - c[2]) * (c[5] - c[3]) for c in cells)
    masters = Counter(str(c[1]).split("_ASAP7")[0] for c in cells)
    ff = sum(v for k, v in masters.items() if SEQ_RE.match(k))
    buf = sum(v for k, v in masters.items() if BUF_RE.match(k))
    # density bins (square, >= 2 um) -> empty-area share of the macro-free bins
    bw = max(max(W, H) / bins, 2.0)
    nx, ny = max(1, int(math.ceil(W / bw))), max(1, int(math.ceil(H / bw)))
    grid = [0.0] * (nx * ny)
    for c in cells:
        i = min(nx - 1, max(0, int(((c[2] + c[4]) / 2 - X0) / bw)))
        j = min(ny - 1, max(0, int(((c[3] + c[5]) / 2 - Y0) / bw)))
        grid[j * nx + i] += (c[4] - c[2]) * (c[5] - c[3])
    cov = [False] * (nx * ny)
    for b in blocks:
        for j in range(max(0, int((b[3] - Y0) / bw)), min(ny, int(math.ceil((b[5] - Y0) / bw)))):
            cy = Y0 + (j + .5) * bw
            if not b[3] <= cy <= b[5]:
                continue
            for i in range(max(0, int((b[2] - X0) / bw)), min(nx, int(math.ceil((b[4] - X0) / bw)))):
                if b[2] <= X0 + (i + .5) * bw <= b[4]:
                    cov[j * nx + i] = True
    freeb = emptyb = 0
    for j in range(ny):
        for i in range(nx):
            k = j * nx + i
            area = (min(X1, X0 + (i + 1) * bw) - (X0 + i * bw)) * (min(Y1, Y0 + (j + 1) * bw) - (Y0 + j * bw))
            if cov[k] or area < 0.25 * bw * bw:
                continue
            freeb += 1
            if grid[k] / area < EMPTY_BIN_DENSITY:
                emptyb += 1
    # pins
    pins = {}
    for p in d.get("pins") or []:
        name, layer, *r = p
        r = list(map(float, r))
        pins.setdefault(name, ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2, layer))
    faces, layers, pos = Counter(), Counter(), {}
    for name, (x, y, layer) in pins.items():
        if name in ("VDD", "VSS"):
            continue
        f = face_of(x, y, (X0, Y0, X1, Y1))
        faces[f] += 1
        layers[layer] += 1
        pos.setdefault(f, []).append(x if f in "NS" else y)
    flen = {"N": W, "S": W, "E": H, "W": H}
    per_um = {f: round(faces[f] / flen[f], 3) for f in "NSEW" if faces.get(f) and flen[f] > 0}
    peak = {}
    for f, v in pos.items():
        if f == "area":
            continue
        v.sort()
        j = best = 0
        for i in range(len(v)):
            while v[i] - v[j] > 10.0:
                j += 1
            best = max(best, i - j + 1)
        peak[f] = round(best / 10.0, 2)
    # pin -> register
    pr = d.get("pin_regs")
    dist = [abs(r[2] - r[4]) + abs(r[3] - r[5]) for r in (pr or []) if r[1] == "R"]
    kinds = Counter(r[1] for r in (pr or []))
    # macro pin facing (optional "macro_faces": [[inst, cx, cy, pinx, piny, logicx, logicy]])
    away = []
    for m in d.get("macro_faces") or []:
        inst, cx, cy, px, py, lx, ly = m[:7]
        vp, vl = (px - cx, py - cy), (lx - cx, ly - cy)
        npn, nl = math.hypot(*vp), math.hypot(*vl)
        if npn >= 1 and nl >= 1 and (vp[0] * vl[0] + vp[1] * vl[1]) / npn / nl < -0.2:
            away.append(inst)
    st = dict(
        schema="opentallas.ref_tile.layout_review.v1", top=d.get("top"), placed=placed,
        outline_um=[round(W, 3), round(H, 3)], aspect=round(max(W, H) / max(1e-9, min(W, H)), 3),
        die_area_um2=round(W * H, 1), macros=len(blocks), macro_area_pct=round(100 * barea / max(1e-9, W * H), 2),
        std_cells=len(cells), std_area_um2=round(sarea, 1),
        std_fill_of_free=round(sarea / free, 4) if placed and free > 1 else None,
        ff=ff, buf_inv=buf, buf_share=round(buf / max(1, len(cells)), 4) if placed else None,
        pins_per_face=dict(faces), pins_per_um=per_um, pin_peak_per_um_10um=peak, pin_layers=dict(layers),
        pins_registered=kinds.get("R", 0), pins_to_macro=kinds.get("M", 0), pins_unregistered=kinds.get("N", 0),
        pin_to_reg_median_um=None if not dist else round(_q(dist, .5), 2),
        pin_to_reg_p90_um=None if not dist else round(_q(dist, .9), 2),
        pin_to_reg_max_um=None if not dist else round(max(dist), 2),
        empty_area=round(emptyb / freeb, 4) if placed and freeb else None, density_bin_um=round(bw, 3),
        macro_obs=d.get("macro_obs") or {}, macros_pins_facing_away=away,
        clock_roots=len([c for c in d.get("clock_roots") or [] if c[-1] == 1]),
    )
    st["flags"] = flags(st)
    return st


def flags(st: dict) -> list:
    out = []
    f = st.get("std_fill_of_free")
    if f is not None and f < FILL_FREE_FAIL:
        out.append(f"low fill {100 * f:.1f}% of free area")
    p = st.get("pin_to_reg_p90_um")
    if p is not None and p > PIN_REG_P90_FLAG:
        out.append(f"pin->register p90 {p:.0f} um")
    e = st.get("empty_area")
    if e is not None and e > EMPTY_FLAG:
        out.append(f"empty {100 * e:.0f}%")
    b = st.get("buf_share")
    if b is not None and b > BUF_FLAG:
        out.append(f"buf/inv {100 * b:.0f}%")
    hi = {k: v for k, v in (st.get("pins_per_um") or {}).items() if v > PIN_PER_UM_FLAG}
    if hi:
        out.append("pin density " + ",".join(f"{k} {v:.1f}/um" for k, v in hi.items()))
    if st.get("macros_pins_facing_away"):
        out.append(f"{len(st['macros_pins_facing_away'])} macros' pins face away from their logic")
    return out


def judge(st: dict, spec: dict, parent: bool = False, review: dict | None = None, band_reason: str = "") -> list:
    """[(level, item, msg, fix)] for the gate: FAIL on fill < 20 % of free or pin->register p90 > 150 um; floorplan-only
    (unplaced) dumps are not judged.  Parents / clusters (hard children) are judged by macro packing and the existing
    parent fill rule, not by std-cell fill (TILE-REVIEW coordinator 10-23): only the pin-register rule applies to them.

    Exemptions (WARN instead of FAIL), per rule:
      * low fill  : the kit spec's non-empty "low_fill_reason", a measured lattice / channel band (band_reason), or a
                    GEOM-REVIEW PASS / PASS-CONDITIONAL verdict recorded for THIS kit's content hash (review);
      * pin->reg  : only a GEOM-REVIEW PASS / PASS-CONDITIONAL for this content hash or an explicit spec
                    "pin_reg_reason" -- a fill reason or a measured band never excuses far pin registers (COORD 10-23:
                    the parent band exemption must not let a BAD parent through).  A GEOM-REVIEW FAIL excuses nothing."""
    if not st.get("placed"):
        return [("INFO", "layout_review", "floorplan-only dump: review picture written, fill / pin-register not judged", "")]
    rv = review if review and review.get("verdict") in ("PASS", "PASS-CONDITIONAL") else None
    rv_txt = (f"GEOM-REVIEW {rv['verdict']} hash {str(rv.get('hash'))[:12]} ({rv.get('kit', '')})" if rv else "")
    fill_reason = str(spec.get("low_fill_reason") or "").strip() or band_reason or rv_txt
    reg_reason = rv_txt or str(spec.get("pin_reg_reason") or "").strip()
    out = []
    f = st.get("std_fill_of_free")
    p = st.get("pin_to_reg_p90_um")
    fails, warns = [], []
    if f is not None and f < FILL_FREE_FAIL and not parent:
        m = (f"std-cell fill {100 * f:.1f}% of the free (non-macro) area < {100 * FILL_FREE_FAIL:.0f}% "
             f"({st['std_area_um2']} um2 std cells in {st['outline_um'][0]}x{st['outline_um'][1]} um, macros "
             f"{st['macro_area_pct']}%)")
        (warns.append(m + f" (reason: {fill_reason})") if fill_reason else fails.append(m))
    if p is not None and p > PIN_REG_P90_FAIL:
        m = (f"pin->pin-register p90 {p:.0f} um > {PIN_REG_P90_FAIL:.0f} um (median {st['pin_to_reg_median_um']} um, "
             f"{st['pins_registered']} registered pins)")
        (warns.append(m + f" (reason: {reg_reason})") if reg_reason else fails.append(m))
    if warns:
        out.append(("WARN", "layout_review", "; ".join(warns), ""))
    if fails:
        out.append(("FAIL", "layout_review", "; ".join(fails),
                    "shrink the outline / regroup macros so the logic fills its area and pin registers sit at their pins, "
                    "or record \"low_fill_reason\" in the kit spec (fill only) / get a GEOM-REVIEW PASS for this kit "
                    "(lanes/GEOM-REVIEW.md)"))
    if review and review.get("verdict") == "FAIL":
        out.append(("INFO", "layout_review", f"GEOM-REVIEW FAIL recorded for this content hash ({review.get('kit', '')}): "
                                             "no exemption", ""))
    msg = ((f"parent: macro packing {st['macro_area_pct']}% of outline, " if parent else "") + f"{st['outline_um'][0]}x{st['outline_um'][1]} um, fill {None if f is None else round(100 * f, 1)}% of free, "
           f"empty {None if st.get('empty_area') is None else round(100 * st['empty_area'])}%, buf/inv "
           f"{None if st.get('buf_share') is None else round(100 * st['buf_share'])}%, pin->reg p50/p90 "
           f"{st.get('pin_to_reg_median_um')}/{p} um, pins/um {st.get('pins_per_um')}")
    out.append(("INFO", "layout_review", msg + (("; flags: " + "; ".join(st["flags"])) if st["flags"] else ""), ""))
    return out


def render_review(d: dict, st: dict, out, title: str = "") -> str:
    v = LP.View(d["die"], top=64)
    c = LP.Canvas(v.cw, v.ch, bg=(16, 16, 24))
    X0, Y0, X1, Y1 = map(float, d["die"])
    bw = st["density_bin_um"]
    nx, ny = max(1, int(math.ceil((X1 - X0) / bw))), max(1, int(math.ceil((Y1 - Y0) / bw)))
    grid = [0.0] * (nx * ny)
    cells = _std(d)
    for cl in cells:
        i = min(nx - 1, max(0, int(((cl[2] + cl[4]) / 2 - X0) / bw)))
        j = min(ny - 1, max(0, int(((cl[3] + cl[5]) / 2 - Y0) / bw)))
        grid[j * nx + i] += (cl[4] - cl[2]) * (cl[5] - cl[3])
    for j in range(ny):
        for i in range(nx):
            val = grid[j * nx + i] / (bw * bw)
            if val > 0:
                c.fill(*v.rect((X0 + i * bw, Y0 + j * bw, min(X1, X0 + (i + 1) * bw), min(Y1, Y0 + (j + 1) * bw))),
                       LP.ramp(min(1.0, val / 0.8)))
    away = set(st.get("macros_pins_facing_away") or [])
    for b in d.get("blocks") or []:
        x0, y0, x1, y1 = v.rect(list(map(float, b[2:6])))
        c.fill(x0, y0, x1, y1, (120, 120, 135))
        c.box(x0, y0, x1, y1, (230, 30, 30) if b[0] in away else (230, 230, 230), 2 if b[0] in away else 1)
    c.box(*v.rect(d["die"]), (200, 200, 200), 1)
    for r in d.get("pin_regs") or []:
        if r[1] == "R" and abs(r[2] - r[4]) + abs(r[3] - r[5]) > PIN_REG_P90_FLAG:
            c.line(v.x(r[2]), v.y(r[3]), v.x(r[4]), v.y(r[5]), (230, 220, 40), 1)
    for p in d.get("pins") or []:
        r = list(map(float, p[2:6]))
        cx, cy = v.x((r[0] + r[2]) / 2), v.y((r[1] + r[3]) / 2)
        c.fill(cx - 1, cy - 1, cx + 2, cy + 2, (0, 230, 230))
    for r in d.get("pin_regs") or []:
        if r[1] == "R":
            cx, cy = v.x(r[4]), v.y(r[5])
            c.fill(cx - 1, cy - 1, cx + 2, cy + 2, (60, 240, 60))
    for k in d.get("clock_roots") or []:
        x0, y0, x1, y1 = map(float, k[2:6])
        cx, cy = v.x((x0 + x1) / 2), v.y((y0 + y1) / 2)
        s = 6 if k[-1] == 1 else 3
        c.fill(cx - s, cy - s, cx + s, cy + s, (240, 30, 30) if k[-1] == 1 else (255, 150, 0))
    # 100 um scale bar (or 20 / 500 um)
    W = X1 - X0
    sb = 500.0 if W > 2000 else 100.0 if W >= 250 else 50.0 if W >= 120 else 20.0
    c.fill(v.x(X0), v.y(Y0) + 4, v.x(X0 + sb), v.y(Y0) + 7, (255, 255, 255))
    f = st.get("std_fill_of_free")
    c.text(6, 4, (title or d.get("top") or "")[:110], (255, 255, 255), 2)
    c.text(6, 22, f"{st['outline_um'][0]}x{st['outline_um'][1]} um  macros {st['macros']} ({st['macro_area_pct']}%)  cells "
                  f"{st['std_cells']}  fill {None if f is None else round(100 * f, 1)}% of free  empty "
                  f"{None if st.get('empty_area') is None else round(100 * st['empty_area'])}%  FF {st['ff']}  buf/inv "
                  f"{None if st.get('buf_share') is None else round(100 * st['buf_share'])}%  bar {sb:.0f} um", (220, 220, 220))
    c.text(6, 34, f"pins {st['pins_per_face']}  per um {st['pins_per_um']}  pin->reg p50/p90 {st['pin_to_reg_median_um']}/"
                  f"{st['pin_to_reg_p90_um']} um", (220, 220, 220))
    c.text(6, 46, ("FLAGS: " + "; ".join(st["flags"]))[:200] if st["flags"] else "no flags", (255, 200, 80))
    return c.save(out)


def review(d: dict, outdir, title: str = "", spec: dict | None = None, parent: bool = False,
           geom_review: dict | None = None, band_reason: str = ""):
    """write review.png + review_stats.json into outdir; return (stats, png path, judge items)"""
    od = Path(outdir)
    od.mkdir(parents=True, exist_ok=True)
    st = review_stats(d)
    png = render_review(d, st, od / "review.png", title)
    st["png"] = png
    st["kind"] = "parent" if parent else "tile"
    items = judge(st, spec or {}, parent, geom_review, band_reason)
    if geom_review:
        st["geom_review"] = {k: geom_review.get(k) for k in ("verdict", "hash", "kit", "element", "src")}
    st["verdict_items"] = [list(x) for x in items]
    (od / "review_stats.json").write_text(json.dumps(st, indent=1) + "\n")
    return st, png, items


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dump")
    ap.add_argument("outdir")
    ap.add_argument("--title", default="")
    ap.add_argument("--spec", default=None)
    a = ap.parse_args(argv)
    p = Path(a.dump)
    d = json.loads(p.read_text())
    spec = json.loads(Path(a.spec).read_text()) if a.spec else {}
    st, png, items = review(d, a.outdir, a.title, spec)
    for lvl, item, msg, fix in items:
        print(f"{lvl} {item}: {msg}" + (f" -> {fix}" if fix else ""))
    print(png)
    return 1 if any(x[0] == "FAIL" for x in items) else 0


if __name__ == "__main__":
    sys.exit(main())
