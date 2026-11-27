#!/usr/bin/env python3
r"""adv_fence_geom.py -- PRECHECK-R2 static advisory ADV-FENCE-GEOM (C-FENCE-GEOM-ILLEGAL, R3-FENCE 11-27; REPORT-ONLY, never a gate; the plan part also feeds the blocking PRE class FENCEGEOM below).

Rejects (reports), before place, the fence / region shapes that ended runs in the OpenROAD placers:
  ZERO      zero-area or inverted rect                      (HEAD East 23:15 nine-flop zero-area band; GPL-0304 NaN)
  SUBROW    rect under one row (0.27 um) high               (no row to seat a member: DPL-0033 / GPL-0304)
  SUBSITE   rect under one site (0.054 um) wide
  SINGLETON a region that holds ONE instance (region_guide.tsv: one "I" row and no "G" glob)   (QC TT GPL-0304 iteration 0: six
            singleton flop fences; XS4 same symptom).  Pin the one cell FIRM instead of fencing it.
  UNSNAPPED an edge off the site grid (x from the core origin in 0.054 um, y in 0.27 um) (HEAD East DPL-0033: six cells 0.016-0.034 um
            outside unsnapped fence bounds).  The generators (ot_fence_snap, logic_cluster ot_lc_box, place_regions.tcl) now snap every
            emitted box OUTWARD, so this is informational for kits built after that fix.
  OUTSIDE   rect not inside the type outline [0, 0, W, H]
Sources (static data only; regions a hook derives at run time, e.g. pin_reg_face_fence bands, are not visible here):
  plan   partition_types[].logic_cluster_rects_um[].rect_um, partition_types[].rck_island.rect_um,
         partition_types[].place_regions[].box_um (all kinds; a SINGLETON is a fence / soft region with cone between or exact whose
         inst_re statically resolves to ONE instance: an anchored ^...$ literal or one-literal alternation, e.g. the QC TT compact
         ^(?:u_bound\.u_core\.u_91236/Q\$_DFF_P_)$ fences; kind fixed (fixed_sites reservations) is exempt from SINGLETON)
  kit    under --tree: logic_cluster.tcl "ot_logic_cluster name x0 y0 x1 y1 ..." rows, region_guide.tsv "R/I/G" rows

FENCEGEOM (plan_gate_pre.py blocking class, C-FENCE-GEOM-ILLEGAL / FABLE-FLOW-0910 a8, 11-27): pre_findings(raw) on the plan sources:
  FAIL FENCEGEOM for ZERO / SUBROW / SUBSITE / OUTSIDE / SINGLETON (PRE-DIFF blocks only NEW ones); UNSNAPPED stays a WARN
  FENCEGEOM-UNSNAPPED (place_regions.tcl, ot_fence_snap and ot_lc_box snap every emitted box OUTWARD, so it cannot reach the placer).
  Each FAIL names type, region, reason and the outward-snapped box.

    findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-FENCE-GEOM ..."]
    pre_findings(raw) -> ["FAIL FENCEGEOM ...", "WARN FENCEGEOM-UNSNAPPED ..."]
"""
import math
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
        for row in t.get("place_regions") or []:
            r = _rect(row.get("box_um")) if isinstance(row, dict) else None
            if r:
                out.append((tn, f"place_regions {row.get('name', '')}".strip(), r, o))
    return out


_META = set(".^$*+?{}[]|()")


def _members(s, i=0, top=True):
    """static member count of an alternation of anchored literal terms starting at s[i] -> (count | None, next index).
    A term is ^ literal [ (?:alt|alt) ] literal $ at the top level (anchors required: an unanchored or prefix pattern matches many);
    inside a group the alternatives are literals or nested groups.  Anything else (classes, quantifiers, wildcards) -> None."""
    total, n = 0, len(s)
    while True:
        mult, start = 1, i
        if top:
            if i >= n or s[i] != "^":
                return None, i
            i += 1
        while i < n and s[i] not in "|)":
            c = s[i]
            if c == "\\":
                if i + 1 >= n or s[i + 1].isalnum():
                    return None, i
                i += 2
            elif c == "(":
                i += 3 if s.startswith("(?:", i) else 1
                k, i = _members(s, i, top=False)
                if k is None or i >= n or s[i] != ")":
                    return None, i
                mult *= k
                i += 1
            elif top and c == "$" and (i + 1 == n or s[i + 1] == "|"):
                i += 1
                break
            elif c in _META:
                return None, i
            else:
                i += 1
            if i < n and s[i] in "*+?{":
                return None, i
        else:
            if top:
                return None, i                    # no closing $: a prefix match
        if top and s[i - 1] != "$":
            return None, i
        total += mult
        if i < n and s[i] == "|":
            i += 1
            continue
        return total, i


def place_region_members(inst_re):
    """-> number of instances an exact-alternation inst_re names, None when it is a pattern (many / unknown)"""
    if not isinstance(inst_re, str) or not inst_re:
        return None
    k, i = _members(inst_re)
    return k if k is not None and i == len(inst_re) else None


def _snap_out(r, o):
    def dn(v, org, p):
        return org + math.floor(round((v - org) * DBU) / round(p * DBU)) * p
    def up(v, org, p):
        return org + math.ceil(round((v - org) * DBU) / round(p * DBU)) * p
    return [round(dn(r[0], o[0], SITE_W), 4), round(dn(r[1], o[1], ROW_H), 4), round(up(r[2], o[0], SITE_W), 4), round(up(r[3], o[1], ROW_H), 4)]


def pre_findings(raw):
    """FENCEGEOM (blocking PRE class): -> ["FAIL FENCEGEOM <type>: <region> <reason> box [...] snapped [...]", "WARN FENCEGEOM-UNSNAPPED ..."]"""
    fails, unsnapped = [], {}
    pt = (raw.get("partition_types") if isinstance(raw, dict) else None) or {}
    for tn, t in sorted(pt.items()):
        if not isinstance(t, dict):
            continue
        o = _origin(t)
        ol = t.get("outline_um")
        shapes = [(lab, r, None) for owner, lab, r, _o in plan_regions({"partition_types": {tn: t}})]
        kinds = {f"place_regions {row.get('name', '')}".strip(): row for row in (t.get("place_regions") or []) if isinstance(row, dict)}
        for lab, r, _ in shapes:
            row = kinds.get(lab) if lab.startswith("place_regions") else None
            why = [c for c in shape_problems(r, o) if c != "UNSNAPPED"]
            if row is not None and row.get("kind") == "fixed":
                why = [c for c in why if c == "ZERO"]          # a reservation rect may be one site / one row; only a zero box is illegal
            if isinstance(ol, (list, tuple)) and len(ol) == 2 and (min(r) < -EPS or r[2] > ol[0] + EPS or r[3] > ol[1] + EPS):
                why.append("OUTSIDE")
            if "UNSNAPPED" in shape_problems(r, o) and not why:
                unsnapped.setdefault(tn, []).append(lab)
            if why:
                fails.append(f"FAIL FENCEGEOM {tn}: {lab} {','.join(why)} box {[round(v, 4) for v in r]} snapped {_snap_out(r, o)}"
                             + (f" outline {list(ol)}" if "OUTSIDE" in why else ""))
        for row in t.get("place_regions") or []:
            if not isinstance(row, dict) or row.get("kind") == "fixed" or row.get("cone", "auto") not in ("between", "exact"):
                continue
            if place_region_members(row.get("inst_re")) == 1:
                b = _rect(row.get("box_um"))
                fails.append(f"FAIL FENCEGEOM {tn}: place_regions {row.get('name')} SINGLETON (cone {row.get('cone')}, inst_re names one "
                             f"instance: GPL-0304 zero-gradient region; pin the cell FIRM or fold it into its neighbour's region)"
                             + (f" box {[round(v, 4) for v in b]} snapped {_snap_out(b, o)}" if b else ""))
    warns = [f"WARN FENCEGEOM-UNSNAPPED {tn}: {len(v)} region box(es) off the site/row grid, snapped outward by the generator: "
             + ", ".join(v[:MAX_EX]) + (" ..." if len(v) > MAX_EX else "") for tn, v in sorted(unsnapped.items())]
    return fails + warns


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
