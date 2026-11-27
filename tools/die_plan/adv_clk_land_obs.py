"""ADV-CLK-LAND-OBS (class C-CLK-LAND-OBS, merged with C-SITE-IN-MACRO; report-only estimator, never a gate).

A clock landing, reserved clock site or relay seat that sits inside a hard macro body, inside its halo, or on an OBS of the macro
on the via-stack layers of the landing cannot be placed / accessed: FABLE-FLOW-0847 A1 + A6.
  S81 lepw_mus_C / mu_C t1: core tap clk_c11 (u_c.u_cap.ck_rn, plan xy 200.637,460.073) M7 landing 23.3 um inside capc5r (OBS M1-M7);
        clk_c1 34.8 um inside xrt1; the same buried tap in dsdv_slice_c1x_C t1 t3 t5 t7 t8 t9.
  HEAD  hd_host_w BF50: 10 clock.reserved_sites_um windows inside SRAM bodies, 9 in the halo; hd_lep0N clk_c0/c1 inside tx[3] bank[0];
        2 relay seats inside SRAM tx[3] bank[2].
The older ADV-SITE-IN-MACRO counts CLAND seats as informational because landing_place moves them at gen.  That claim holds for CLAND
seats only; the clock taps (clock.taps incl. core taps clk_c<k>, added_taps, edge_clocks tap_um) are snapped by gen_phys.core_tap_pins
and moved at most ENTRY_CLEAR_MAX_UM = 2 um, so a tap further inside a macro stays inside (kit_contract FAIL / buried M7 landing).

Landing classes (type frame, um):
  tap          clock.taps[].xy, clock.added_taps[].xy, clock.edge_clocks[].tap_um, clock.tap_um   -> BODY of an obstructing macro
  reserved     clock.reserved_sites_um kind die_clock_tree rect_um + stack_um windows              -> body or halo ring of any macro
  relay        relay_sites{name: xy}                                                               -> body (halo ring only with RELAY_HALO)
A macro (hard_cores[] + contents[] with lef) obstructs a landing whose entry layer is `top` (die.layer_budget.partition_signal_max,
default M7) when its highest metal (LEF OBS / PIN layer when the view file is found, else the plan obs_max, else treated as
obstructing) is >= top - 1: the landing via stack crosses that metal (same rule as gen_phys.entry_block_boxes).
Tap and relay points are body hits with a 0.5 um edge inset (an edge pin is legal), halo hits are the ring up to halo_um (default 2.16).

  adv_clk_land_obs.py PLAN [--root DIR] [--json OUT]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "ADV-CLK-LAND-OBS"
HALO_UM = 2.16
INSET = 0.5
ROT = ("R90", "R270", "MXR90", "MYR90")
MAX_EX = 3
RELAY_HALO = False         # a relay seat in the 2.16 um halo ring only is legalised by DPL; body hits are the failure (S81 col, HEAD lep0N SRAM)
_LEF_TOP = {}


def _roots(plan_path=None, root=None):
    out = []
    if root:
        out.append(Path(root))
    import os
    if os.environ.get("OT_REPO_ROOT"):
        out.append(Path(os.environ["OT_REPO_ROOT"]))
    if plan_path:
        s = str(Path(plan_path).resolve())
        i = s.find("/physical/")
        if i > 0:
            out.append(Path(s[:i]))
    out.append(Path(__file__).resolve().parents[2])
    return out


def lef_top(lef, roots):
    """highest LAYER Mn in a one-macro LEF, None when the file is not found"""
    k = (lef, tuple(map(str, roots)))
    if k not in _LEF_TOP:
        top = None
        for r in roots:
            f = r / lef
            if f.is_file():
                try:
                    top = max([int(v) for v in re.findall(r"\bLAYER\s+M(\d+)\b", f.read_text(errors="replace"))] or [0])
                except OSError:
                    top = None
                break
        _LEF_TOP[k] = top
    return _LEF_TOP[k]


_PIN = {}
PIN_TOL_UM = 2.0        # gen_phys.ENTRY_CLEAR_MAX_UM: a tap within this of its own pin is the real entry, not a buried plan point


def pin_rects(lef, pin, roots):
    """[(x0, y0, x1, y1)] RECTs of PIN `pin` in a LEF (macro frame), None when the file / pin is not found"""
    k = (lef, pin, roots)
    if k not in _PIN:
        out = None
        for r in roots:
            f = Path(r) / lef
            if f.is_file():
                try:
                    txt = f.read_text(errors="replace")
                except OSError:
                    break
                m = re.search(r"^\s*PIN\s+" + re.escape(pin) + r"\s*$(.*?)^\s*END\s+" + re.escape(pin) + r"\s*$", txt, re.S | re.M)
                if m:
                    out = [tuple(float(v) for v in q) for q in re.findall(r"RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", m.group(1))] or None
                break
        _PIN[k] = out
    return _PIN[k]


def _orient_rect(r, orient, w, h):
    """LEF macro-frame rect -> placed-frame offset from the DEF origin (lower-left of the oriented box); None for rotations"""
    x0, y0, x1, y1 = r
    if orient == "R0":
        return (x0, y0, x1, y1)
    if orient == "MY":
        return (w - x1, y0, w - x0, y1)
    if orient == "MX":
        return (x0, h - y1, x1, h - y0)
    if orient == "R180":
        return (w - x1, h - y1, w - x0, h - y0)
    return None


def at_own_pin(label, inst, g, view):
    """a core tap `<inst>.<pin>` whose xy lies within PIN_TOL_UM of its own pin is the real pin entry (KV head cores,
    CORE-DIRECT, QC NK tiles), never a buried plan point.  The pin is the plan's clock_entry_access footprints of that pin
    (type frame, every layer; C-CLK-LAND-OBS 11-27: the QC cb* NK tiles are MY, so the old R0-only LEF test reported 36 real
    ck entries as buried and clk_land_clear would have moved them off the pin), else the LEF pin shape placed by the core's
    orientation (R0 / MX / MY / R180).  Unknown pin / 90-degree rotation / no LEF: not at a pin (judged by the body rule)."""
    m = re.match(r"clock\.taps\[(.*)\] core$", label)
    lef, ox, oy, orient, roots = view[:5]
    wh, cea = (view[5], view[6]) if len(view) > 6 else (None, None)
    if not m:
        return False
    name = m.group(1)
    pin = name[len(inst) + 1:] if name.startswith(inst + ".") else None
    if not pin:
        return False

    def near(r):
        return r[0] - PIN_TOL_UM <= g[0] <= r[2] + PIN_TOL_UM and r[1] - PIN_TOL_UM <= g[1] <= r[3] + PIN_TOL_UM
    if isinstance(cea, dict) and cea.get("pin") == pin:
        for rs in (cea.get("footprints_um") or {}).values():
            for r in rs or []:
                if isinstance(r, (list, tuple)) and len(r) == 4 and near([float(v) for v in r]):
                    return True
    if not lef:
        return False
    rs = pin_rects(lef, pin, roots)
    if not rs:
        return False
    if orient != "R0" and not wh:
        return False
    out = []
    for r in rs:
        q = _orient_rect(r, orient, *(wh or (0.0, 0.0)))
        if q is None:
            return False
        out.append((ox + q[0], oy + q[1], ox + q[2], oy + q[3]))
    return any(near(r) for r in out)


def entry_top(raw_or_P):
    lb = ((raw_or_P.get("die") or {}).get("layer_budget") or {}) if isinstance(raw_or_P, dict) else {}
    m = re.fullmatch(r"M(\d+)", str(lb.get("partition_signal_max", "M7")))
    return int(m.group(1)) if m else 7


def macros(t, top, roots=()):
    """-> [(x0, y0, x1, y1, halo, name, obstructs)] hard_cores + contents with lef; obstructs = metal reaches top-1"""
    out = []
    for h in list(t.get("hard_cores") or []) + [c for c in (t.get("contents") or []) if isinstance(c, dict) and c.get("lef")]:
        try:
            (x0, y0), (w, hh) = h["origin_um"], h["outline_um"]
        except (KeyError, TypeError, ValueError):
            continue
        if str(h.get("orient", "R0")) in ROT:
            w, hh = hh, w
        halo = float(h.get("halo_um") or HALO_UM)
        mt = lef_top(h["lef"], roots) if h.get("lef") and roots else None
        if mt is None:
            m = re.fullmatch(r"M(\d+)", str(h.get("obs_max") or ""))
            mt = int(m.group(1)) if m else top
        tr = h.get("track_offset_um") or [0.0, 0.0]
        out.append((float(x0), float(y0), float(x0) + float(w), float(y0) + float(hh), halo, h.get("inst") or h.get("name") or "core", mt >= top - 1,
                    (h.get("lef"), float(x0) + float(tr[0]), float(y0) + float(tr[1]), str(h.get("orient", "R0")), tuple(map(str, roots)),
                     (float(w), float(hh)), h.get("clock_entry_access"))))
    return out


def _xy(p):
    return isinstance(p, (list, tuple)) and len(p) >= 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in p[:2])


def landings(t):
    """-> [(cls, label, (x, y) or rect (x0, y0, x1, y1), setter)]; setter(new_xy_or_rect) writes the plan value in place"""
    out = []
    ck = t.get("clock") or {}

    def pt(cls, label, cont, key):
        v = cont[key]
        if _xy(v):
            out.append((cls, label, (float(v[0]), float(v[1])), lambda n, c=cont, k=key: c.__setitem__(k, [n[0], n[1]] + list(c[k][2:]))))
    for j, e in enumerate(ck.get("taps") or []):
        if isinstance(e, dict) and "xy" in e:
            pt("tap", f"clock.taps[{e.get('name', j)}]" + (" core" if e.get("kind") == "core" else ""), e, "xy")
    for j, e in enumerate(ck.get("added_taps") or []):
        if isinstance(e, dict) and "xy" in e:
            pt("tap", f"clock.added_taps[{e.get('name', j)}]", e, "xy")
    for j, e in enumerate(ck.get("edge_clocks") or []):
        if isinstance(e, dict) and _xy(e.get("tap_um")):
            pt("tap", f"clock.edge_clocks[{e.get('port') or j}].tap_um", e, "tap_um")
    if _xy(ck.get("tap_um")):
        pt("tap", "clock.tap_um", ck, "tap_um")
    for j, e in enumerate(ck.get("reserved_sites_um") or []):
        if isinstance(e, dict) and e.get("kind") == "die_clock_tree" and isinstance(e.get("rect_um"), list) and len(e["rect_um"]) == 4:
            out.append(("reserved", f"clock.reserved_sites_um[{j}]", tuple(float(v) for v in e["rect_um"]), None))
    rel = t.get("relay_sites")
    if isinstance(rel, dict):
        for n, p in rel.items():
            if _xy(p):
                out.append(("relay", f"relay_sites[{n}]", (float(p[0]), float(p[1])), lambda nw, c=rel, k=n: c.__setitem__(k, [nw[0], nw[1]] + list(c[k][2:]))))
    return out


def hit(cls, g, ms, label=""):
    """-> (macro name, 'body'|'halo') or None.  tap: body of an obstructing macro; reserved/relay: body or halo of any macro"""
    best = None
    for x0, y0, x1, y1, halo, nm, obs, view in ms:
        if cls == "tap":
            if not obs:
                continue
            a = g if len(g) == 4 else (g[0], g[1], g[0], g[1])
            inb = a[0] < x1 - INSET and x0 + INSET < a[2] and a[1] < y1 - INSET and y0 + INSET < a[3]
            if inb and not at_own_pin(label, nm, g, view):
                return nm, "body"
            continue
        if len(g) == 4:
            a = g
            body = a[0] < x1 and x0 < a[2] and a[1] < y1 and y0 < a[3]
            ring = a[0] < x1 + halo and x0 - halo < a[2] and a[1] < y1 + halo and y0 - halo < a[3]
        else:
            body = x0 + INSET < g[0] < x1 - INSET and y0 + INSET < g[1] < y1 - INSET
            ring = x0 - halo < g[0] < x1 + halo and y0 - halo < g[1] < y1 + halo
        if body:
            return nm, "body"
        if ring and best is None and (cls != "relay" or RELAY_HALO):
            best = (nm, "halo")
    return best


def classify(t, top, roots=()):
    """-> [(cls, label, geom, macro, 'body'|'halo')] landings hitting a macro"""
    ms = macros(t, top, roots)
    res = []
    for cls, lab, g, _s in landings(t):
        h = hit(cls, g, ms, lab)
        if h:
            res.append((cls, lab, g, h[0], h[1]))
    return res


def counts(raw, plan_path=None, root=None):
    """{type: dict(n, by_cls: {cls: {body, halo}}, hits)} of the types with a hit"""
    top, roots = entry_top(raw), _roots(plan_path, root)
    res = {}
    for tn, t in sorted((raw.get("partition_types") or {}).items()):
        if not isinstance(t, dict) or not t.get("outline_um"):
            continue
        hs = classify(t, top, roots)
        if hs:
            by = {}
            for c, _l, _g, _m, k in hs:
                by.setdefault(c, {"body": 0, "halo": 0})[k] += 1
            res[tn] = dict(n=len(hs), by_cls=by, hits=hs)
    return res


def findings(raw, plan_path=None, tree=None, root=None, **_kw):
    res = counts(raw, plan_path, root)
    out = []
    for tn, r in res.items():
        ex = "; ".join(f"{l} at {tuple(round(v, 2) for v in g)} in {m} ({k})" for _c, l, g, m, k in r["hits"][:MAX_EX])
        by = ", ".join(f"{c} {v['body']}b/{v['halo']}h" for c, v in sorted(r["by_cls"].items()))
        out.append(f"WARN {CHECK} {tn}: {r['n']} clock landing / reserved site / relay seat in a macro body, halo or OBS stack (e.g. {ex}) [{by}] "
                   "(fix: plan flag clk_land_clear {\"enable\": 1}, or clk_land_clear.py)")
    if out:
        tot = {}
        for r in res.values():
            for c, v in r["by_cls"].items():
                tot[c] = tot.get(c, 0) + v["body"] + v["halo"]
        out.append(f"LIST {CHECK} {len(res)} type(s): " + ", ".join(f"{c} {n}" for c, n in sorted(tot.items())))
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("--root"); ap.add_argument("--json")
    a = ap.parse_args()
    raw = json.loads(Path(a.plan).read_text())
    res = counts(raw, a.plan, a.root)
    for line in findings(raw, a.plan, root=a.root):
        print(line)
    if a.json:
        Path(a.json).write_text(json.dumps({tn: dict(n=r["n"], by_cls=r["by_cls"], hits=[[c, l, list(g), m, k] for c, l, g, m, k in r["hits"]])
                                            for tn, r in res.items()}, indent=1))
    print(f"SUMMARY {CHECK} types_hit={len(res)} landings={sum(r['n'] for r in res.values())} types={len(raw.get('partition_types') or {})}")
