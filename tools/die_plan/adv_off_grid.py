#!/usr/bin/env python3
"""adv_off_grid.py -- PRECHECK-R2 static advisory ADV-OFF-GRID (COORD 11-23; an estimator, never a gate).

Every plan-specified cell / flop / bank / macro site must sit on the placement grid of its type: x on the 0.054-um site
grid and y on a 0.27-um row, both counted from the CORE_AREA corner (kit_fit.kit_core_area; default inset 4.32 um), in
the kit's own DBU arithmetic (4000 / um: kit_istations "(cx - ff_x0) % ff_sw" and "dict exists ff_orient cy").
Real positive: KV sys_c row C (FAM-KV-HUBC-SYSC-R2 a6fb0ce2baf0, 11-23): the R-DOB o_dcal_dob exact bank sites were moved
by +DX per bit without snapping; plan_gate_pre passed, the probe kit died in global_place: "exact internal bank site is
not on row/site: u_ist_o_dcal_dob_0/eq 1111.404 985.5".  The fix (08be3955c5c7) snapped them to the 0.054 grid.

Classes (sites outside CORE_AREA are ADV-BANK-OFFAREA's, not repeated here):
  EXACT  the kit places these exactly and refuses an off-grid one (global_place error):
         internal_stations[].bit_sites_um / face_bit_sites_um, soft_reg_banks[].bit_sites_um
  CELL   other plan-specified cell sites the kit places as hints and legalises (is_place / relay seats / tap sinks):
         relay_sites{}, reg_leaf_split[].copies[].site_um, count_straps[].sites_um, clock.reserved_sites_um / sink_sites_um,
         reset.consumer_sites_um
  MACRO  hard_cores[] / lef contents[] / contents[].physical_parts[] origin_um: x off the site grid or y off a row
  Only EXACT gets per-type lines by default (KV D29 / S81 J8: 70k relay / tap-sink hints and ~200 macro origins are off the
  grid in plans whose kits place, so those two classes are counted in the summary; kw all_classes=True lists them).
Not checked: ft_slots bit_sites_um (gen snaps them: ft_bit_sites.snap_slots), reset_spine_pins / bus windows (pins).

    findings(raw, plan_path, tree=None, **kw) -> ["WARN ADV-OFF-GRID ..."]
"""
import os
import sys
import time

CHECK = "ADV-OFF-GRID"
DBU = 4000
SITE_W, ROW_H = 0.054, 0.27
CORE_MARGIN = 4.32
MAX_LINES = 20
MAX_EX = 3


def _core(t):
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        from kit_fit import kit_core_area
        return [float(v) for v in kit_core_area(t)]
    except Exception:  # noqa: BLE001 -- fixture / older tree: the default inset
        w, h = t["outline_um"]
        return [CORE_MARGIN, CORE_MARGIN, float(w) - CORE_MARGIN, float(h) - CORE_MARGIN]


def _pt(p):
    if isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p[:2]):
        return float(p[0]), float(p[1])
    return None


def _pts(o, depth=0):
    """every [x, y] point inside a (nested) list."""
    p = _pt(o)
    if p:
        yield p
    elif isinstance(o, (list, tuple)) and depth < 4:
        for v in o:
            yield from _pts(v, depth + 1)


def sites(t):
    """-> [(class, label, x, y)] of a type's plan-specified sites."""
    out = []
    for k, e in enumerate(t.get("internal_stations") or []):
        if isinstance(e, dict):
            lab = f"internal_stations[{k}] {e.get('conn', '')}".strip()
            for key in ("bit_sites_um", "face_bit_sites_um"):
                out += [("EXACT", lab, x, y) for x, y in _pts(e.get(key) or [])]
    for k, e in enumerate(t.get("soft_reg_banks") or []):
        if isinstance(e, dict):
            out += [("EXACT", f"soft_reg_banks[{k}] {e.get('id', '')}".strip(), x, y) for x, y in _pts(e.get("bit_sites_um") or [])]
    for k, e in enumerate(t.get("reg_leaf_split") or []):
        if isinstance(e, dict):
            for j, c in enumerate(e.get("copies") or []):
                p = _pt(c.get("site_um")) if isinstance(c, dict) else None
                if p:
                    out.append(("CELL", f"reg_leaf_split[{k}].copies[{j}]", p[0], p[1]))
    rs = t.get("relay_sites")
    if isinstance(rs, dict):
        for name, v in rs.items():
            p = _pt(v)
            if p:
                out.append(("CELL", f"relay_sites[{name}]", p[0], p[1]))
    for k, e in enumerate(t.get("count_straps") or []):
        if isinstance(e, dict):
            out += [("CELL", f"count_straps[{k}] {e.get('name', '')}".strip(), x, y) for x, y in _pts(e.get("sites_um") or [])]
    ck = t.get("clock") if isinstance(t.get("clock"), dict) else {}
    for key in ("reserved_sites_um", "sink_sites_um"):
        out += [("CELL", f"clock.{key}", x, y) for x, y in _pts(ck.get(key) or [])]
    rst = t.get("reset") if isinstance(t.get("reset"), dict) else {}
    out += [("CELL", "reset.consumer_sites_um", x, y) for x, y in _pts(rst.get("consumer_sites_um") or [])]
    for c in t.get("hard_cores") or []:
        p = _pt(c.get("origin_um")) if isinstance(c, dict) else None
        if p:
            out.append(("MACRO", f"hard_cores {c.get('inst')}", p[0], p[1]))
    for c in t.get("contents") or []:
        if not isinstance(c, dict):
            continue
        parts = [q for q in c.get("physical_parts") or [] if isinstance(q, dict)]
        for q in parts:
            p = _pt(q.get("origin_um"))
            if p:
                out.append(("MACRO", f"contents {q.get('physical_inst') or c.get('inst')}", p[0], p[1]))
        if not parts and c.get("lef"):
            p = _pt(c.get("origin_um"))
            if p:
                out.append(("MACRO", f"contents {c.get('inst')}", p[0], p[1]))
    return out


def off_grid(x, y, core):
    """-> (x off, y off) in the kit's DBU arithmetic, or None when the point is outside CORE_AREA."""
    x0, y0, x1, y1 = core
    cx, cy = round(x * DBU), round(y * DBU)
    X0, Y0 = round(x0 * DBU), round(y0 * DBU)
    if cx < X0 or cy < Y0 or cx > round(x1 * DBU) or cy > round(y1 * DBU):
        return None
    return (cx - X0) % round(SITE_W * DBU) != 0, (cy - Y0) % round(ROW_H * DBU) != 0


def type_findings(tn, t):
    core = _core(t)
    bad = {}
    for cls, lab, x, y in sites(t):
        r = off_grid(x, y, core)
        if r and (r[0] or r[1]):
            bad.setdefault(cls, []).append((lab, x, y, r))
    return core, bad


def findings(raw, plan_path, tree=None, **kw):
    """WARN ADV-OFF-GRID lines (capped) + one summary line; never raises."""
    try:
        t0 = time.time()
        types = raw.get("partition_types") if isinstance(raw, dict) else None
        if not types:
            return [f"WARN {CHECK} not checked: plan has no partition_types"]
        lines, tot, ntypes = [], {"EXACT": 0, "CELL": 0, "MACRO": 0}, 0
        for tn, t in sorted(types.items()):
            if not isinstance(t, dict) or not t.get("outline_um"):
                continue
            ntypes += 1
            core, bad = type_findings(tn, t)
            for cls in ("EXACT", "MACRO", "CELL"):
                b = bad.get(cls)
                if not b:
                    continue
                tot[cls] += len(b)
                if cls != "EXACT" and not kw.get("all_classes"):
                    continue
                rows = sorted({e[0] for e in b})
                what = {"EXACT": "exact flop / bank site(s): place refuses them (\"exact ... site is not on row/site\")",
                        "MACRO": "macro origin(s) off the site grid / rows",
                        "CELL": "plan cell site(s) off the site grid / rows"}[cls]
                ex = "; ".join(f"{lab} ({x:g},{y:g}){' x' if r[0] else ''}{' y' if r[1] else ''}" for lab, x, y, r in b[:MAX_EX])
                lines.append((0 if cls == "EXACT" else 1 if cls == "MACRO" else 2, -len(b),
                              f"WARN {CHECK} {tn}: {cls} {len(b)} {what} on {len(rows)} row(s) "
                              f"({', '.join(rows[:3])}{' ...' if len(rows) > 3 else ''}); grid x0 {core[0]:g} + k x {SITE_W}, "
                              f"y0 {core[1]:g} + k x {ROW_H}; e.g. {ex}; fix: snap x to x0 + round((x - x0) / {SITE_W}) x {SITE_W} "
                              f"and y to a row in the row generator"))
        lines.sort()
        cap = int(kw.get("max_lines") or MAX_LINES)
        out = [ln[2] for ln in lines[:cap]]
        if lines or tot["MACRO"] or tot["CELL"]:
            out.append(f"WARN {CHECK} summary: {tot['EXACT']} EXACT off-grid bank site(s) in {len(lines)} type(s) (listed); "
                       f"counted only: {tot['MACRO']} MACRO origin(s), {tot['CELL']} CELL hint site(s) off the grid; "
                       f"{ntypes} types in {time.time() - t0:.1f} s"
                       f"{' (first ' + str(cap) + ' listed)' if len(lines) > cap else ''}")
        return out
    except Exception as e:  # noqa: BLE001
        return [f"WARN {CHECK} not checked: {type(e).__name__}: {str(e)[:200]}"]


if __name__ == "__main__":
    import json
    t0 = time.time()
    raw = json.load(open(sys.argv[1]))
    t1 = time.time()
    for ln in findings(raw, sys.argv[1], sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else None,
                       max_lines=100000 if "--all" in sys.argv else None, all_classes="--all-classes" in sys.argv):
        print(ln)
    print(f"# load {t1 - t0:.1f} s, check {time.time() - t1:.2f} s")
