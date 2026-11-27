#!/usr/bin/env python3
"""adv_fence_geom.py -- PRECHECK-R2 static advisory ADV-FENCE-GEOM (C-FENCE-GEOM-ILLEGAL, R3-FENCE 11-27; REPORT-ONLY, never a gate).

Rejects (reports), before place, the fence / region shapes that ended runs in the OpenROAD placers:
  ZERO      zero-area or inverted rect                      (HEAD East 23:15 nine-flop zero-area band; GPL-0304 NaN)
  SUBROW    rect under one row (0.27 um) high               (no row to seat a member: DPL-0033 / GPL-0304)
  SUBSITE   rect under one site (0.054 um) wide
  SINGLETON a region that holds ONE instance (region_guide.tsv: one "I" row and no "G" glob)   (QC TT GPL-0304 iteration 0: six
            singleton flop fences; XS4 same symptom).  Pin the one cell FIRM instead of fencing it.
  UNSNAPPED an edge off the site grid (x from the core origin in 0.054 um, y in 0.27 um) (HEAD East DPL-0033: six cells 0.016-0.034 um
            outside unsnapped fence bounds).  The generators (ot_fence_snap, logic_cluster ot_lc_box, place_regions.tcl) now snap every
            emitted box OUTWARD, so this is informational for kits built after that fix.
Sources (static data only; regions a hook derives at run time, e.g. pin_reg_face_fence bands, are not visible here):
  plan   partition_types[].logic_cluster_rects_um[].rect_um, partition_types[].rck_island.rect_um
  kit    under --tree: logic_cluster.tcl "ot_logic_cluster name x0 y0 x1 y1 ..." rows, region_guide.tsv "R/I/G" rows

    findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-FENCE-GEOM ..."]
"""
import os
import re
import sys
from pathlib import Path

CHECK = "ADV-FENCE-GEOM"
DBU = 4000
SITE_W, ROW_H = 0.054, 0.27
CORE_MARGIN = 4.32
EPS = 1e-6
MAX_EX = 4
MAX_FILES = 400
_NUM = r"-?\d+(?:\.\d+)?"


def _w(*parts):
    return " ".join(["WARN", CHECK] + [str(p) for p in parts])


def _off(v, o, pitch):
    """distance of coordinate v from the nearest grid line o + k * pitch, in dbu-exact arithmetic (4000 dbu / um)"""
    d = round((v - o) * DBU)
    p = round(pitch * DBU)
    r = d % p
    return min(r, p - r) / DBU


def shape_problems(r, origin=(CORE_MARGIN, CORE_MARGIN)):
    """-> sorted [class, ...] of one rect (x0, y0, x1, y1) um"""
    x0, y0, x1, y1 = r
    w, h = x1 - x0, y1 - y0
    out = []
    if w <= EPS or h <= EPS:
        out.append("ZERO")
    else:
        if h < ROW_H - EPS:
            out.append("SUBROW")
        if w < SITE_W - EPS:
            out.append("SUBSITE")
    if any(_off(v, origin[0], SITE_W) > EPS for v in (x0, x1)) or any(_off(v, origin[1], ROW_H) > EPS for v in (y0, y1)):
        out.append("UNSNAPPED")
    return out


def _rect(v):
    if isinstance(v, (list, tuple)) and len(v) == 4 and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v):
        return tuple(float(x) for x in v)
    return None


def _origin(t):
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        from kit_fit import kit_core_area
        c = kit_core_area(t)
        return float(c[0]), float(c[1])
    except Exception:  # noqa: BLE001 -- fixture / older tree: the default inset
        return CORE_MARGIN, CORE_MARGIN


def plan_regions(raw):
    """-> [(type, label, rect, origin)]"""
    out = []
    pt = (raw.get("partition_types") if isinstance(raw, dict) else None) or {}
    for tn, t in pt.items():
        if not isinstance(t, dict):
            continue
        o = _origin(t)
        for k, row in enumerate(t.get("logic_cluster_rects_um") or []):
            r = _rect(row.get("rect_um")) if isinstance(row, dict) else None
            if r:
                out.append((tn, f"logic_cluster_rects_um[{k}] {row.get('name', '')}".strip(), r, o))
        isl = t.get("rck_island")
        r = _rect(isl.get("rect_um")) if isinstance(isl, dict) else None
        if r:
            out.append((tn, "rck_island", r, o))
    return out


def kit_regions(tree):
    """-> ([(kit dir, label, rect, origin)], [(kit dir, label, n_members)]) from generated kit files under tree"""
    regs, singles = [], []
    if not tree or not os.path.isdir(tree):
        return regs, singles
    n = 0
    for dp, dns, fns in os.walk(tree):
        dns[:] = [d for d in dns if not d.startswith(".")]
        for fn in fns:
            if fn not in ("logic_cluster.tcl", "region_guide.tsv"):
                continue
            n += 1
            if n > MAX_FILES:
                return regs, singles
            p = Path(dp) / fn
            try:
                txt = p.read_text(errors="replace")
            except OSError:
                continue
            kd = os.path.relpath(dp, tree)
            if fn == "logic_cluster.tcl":
                for m in re.finditer(rf"^ot_logic_cluster (\S+) ({_NUM}) ({_NUM}) ({_NUM}) ({_NUM}) ", txt, re.M):
                    regs.append((kd, m.group(1), tuple(float(m.group(i)) for i in range(2, 6)), (CORE_MARGIN, CORE_MARGIN)))
            else:
                mem, glob = {}, set()
                for ln in txt.splitlines():
                    f = ln.split("\t")
                    if f[0] == "R" and len(f) >= 6:
                        try:
                            regs.append((kd, f[1], tuple(float(v) for v in f[2:6]), (CORE_MARGIN, CORE_MARGIN)))
                        except ValueError:
                            pass
                        mem.setdefault(f[1], set())
                    elif f[0] == "I" and len(f) >= 3:
                        mem.setdefault(f[1], set()).add(f[2])
                    elif f[0] == "G" and len(f) >= 3:
                        glob.add(f[1])
                singles += [(kd, nm, len(s)) for nm, s in mem.items() if len(s) == 1 and nm not in glob]
    return regs, singles


def findings(raw, plan_path, tree=None, **_kw):
    cls = {}
    per, n_checked = {}, 0
    groups = {}
    for owner, label, r, o in plan_regions(raw) + kit_regions(tree)[0]:
        n_checked += 1
        pr = shape_problems(r, o)
        for c in pr:
            cls[c] = cls.get(c, 0) + 1
        if pr:
            groups.setdefault(owner, []).append((label, r, pr))
    singles = kit_regions(tree)[1]
    for kd, nm, _n in singles:
        cls["SINGLETON"] = cls.get("SINGLETON", 0) + 1
        groups.setdefault(kd, []).append((nm, None, ["SINGLETON"]))
    out = []
    for owner, rows in groups.items():
        ex = "; ".join(f"{lab} {[round(v, 3) for v in r] if r else ''} {','.join(pr)}".replace("  ", " ") for lab, r, pr in rows[:MAX_EX])
        out.append(_w(f"{owner}: {len(rows)} illegal fence/region shape(s): {ex}{' ...' if len(rows) > MAX_EX else ''}"))
    if out:
        out.append(f"LIST {CHECK} {sum(len(v) for v in groups.values())} region(s) on {len(groups)} owner(s) of {n_checked} checked: "
                   + ", ".join(f"{k} {v}" for k, v in sorted(cls.items())))
    return out


if __name__ == "__main__":
    import json
    for line in findings(json.loads(Path(sys.argv[1]).read_text()), sys.argv[1], tree=sys.argv[2] if len(sys.argv) > 2 else None):
        print(line)
