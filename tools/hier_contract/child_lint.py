#!/usr/bin/env python3
"""Hard-child abstract lint for the TOP-DOWN HIERARCHY CONTRACT (owner 2026-10-11, tools/hier_contract/schema.md).

A parent may only be submitted when every hard child it instantiates passes this lint.  Checks (FAIL unless noted):
  (a) bloat      no OBS rect covering >= 90% of the macro area on a layer >= the child's PG layer
                 (write_abstract_lef -bloat_occupied_layers; preamble UPDATE 2, PDN-0006).  Full-tile M1 cell-row OBS
                 below the PG layer is normal and allowed.
  (b) pg         VDD and VSS each have full-length stripes (>= 90% of the macro span) on ONE common top layer;
                 reports stripe count, spread across the macro and coverage (full-stripe share of top-layer PG metal).
  (c) strap      no OBS and no signal-pin shape on the parent strap layer or above (preamble UPDATE 3, PDN-0233/0232) and
                 no signal pin above the cap.  Cap (2026-10-12 layer contract): --cap, else the contract slot's
                 layer_cap (new routes, M5 default / M6 granted) or view_cap (the closed view's own recorded cap, valid
                 only while it passes here) -- whichever the view's PG top layer matches; strap = cap + 1.  Without a
                 cap: pg_layer + 1 (or the slot's strap_layer), signals <= the slot's signal_max_layer.
  (d) libs       <cell>_tt.lib, <cell>_ff.lib and <cell>_ss.lib exist in --libs (only when --libs is given).
  (e) contract   with --contract/--slot: outline, PG layer and every pin's face / layer (and offset when given) match the
                 slot; pins missing from or extra to the contract are mismatches.
  (f) face       face-pin access: a signal pin on a boundary face whose footprint is overlapped by OBS on the layer
                 directly above it leaves the parent no via access (DRT-0073 at the DS cbh parent: c2e836720-p2 tiles
                 cbq0 12 / cbq 17 / cbr 51 / cbf 0).  Fix in the child: el1011-ds-coll's pin-access plan hook
                 physical/redesign_ds/coll_split/pin_access_pregrt.tcl (bf0080873).  The layer below is reported only.
  (g) clock      WARN only: clock-pin insertion delay (max/min_clock_tree_path) from the TT lib; missing, or more than
                 100 ps from the contract slot's target_insertion_ps (preamble CLOCK LATENCY ACROSS THE HIERARCHY).

exit 0 = PASS (warnings allowed), 1 = FAIL, 2 = usage / unreadable input.  --json prints the machine record.
Usage: child_lint.py CHILD.lef [--libs DIR] [--contract DIE.json --slot NAME] [--json] [--skip f,g]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AREA_FRAC = 0.90          # (a) bloat threshold and (b) full-stripe span fraction
MIN_STRIPES = 2           # (b) per net
MIN_SPREAD = 0.50         # (b) first..last full stripe must span this fraction of the perpendicular dimension
INSERTION_TOL_PS = 100.0  # (g)
EPS = 0.0015              # um: boundary touch tolerance
FACE_FIX = ("physical/redesign_ds/coll_split/pin_access_pregrt.tcl (bf0080873): obstruct the adjacent layers over the "
            "outer face-pin column before GRT, remove after DRT")


def metal(layer: str | None) -> int | None:
    m = re.fullmatch(r"M(\d+)", layer or "")
    return int(m.group(1)) if m else None


def _rects(body: str) -> list[tuple]:
    out, lay = [], None
    for ln in body.splitlines():
        t = ln.replace(";", " ").split()
        if not t:
            continue
        if t[0] == "LAYER":
            lay = t[1]
        elif t[0] == "RECT" and lay:
            v = [x for x in t[1:] if x not in ("MASK",)]
            try:
                x0, y0, x1, y1 = map(float, v[-4:])
            except ValueError:
                continue
            out.append((lay, min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)))
    return out


def parse_lef(text: str, cell: str | None = None) -> dict:
    """the (named or first) MACRO: name, W, H, pins {name: {use, direction, rects}}, obs [(layer, x0, y0, x1, y1)]"""
    macros = list(re.finditer(r"(?m)^\s*MACRO\s+(\S+)\s*$", text))
    if not macros:
        raise ValueError("no MACRO in the LEF")
    pick = next((m for m in macros if m.group(1) == cell), macros[0]) if cell else macros[0]
    name = pick.group(1)
    end = re.search(r"(?m)^\s*END\s+" + re.escape(name) + r"\s*$", text[pick.end():])
    body = text[pick.end(): pick.end() + end.start()] if end else text[pick.end():]
    sz = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", body)
    if not sz:
        raise ValueError(f"MACRO {name} has no SIZE")
    W, H = float(sz.group(1)), float(sz.group(2))
    pins = {}
    for m in re.finditer(r"(?m)^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$", body, re.S):
        pb = m.group(2)
        use = re.search(r"USE\s+(\w+)", pb)
        d = re.search(r"DIRECTION\s+(\w+)", pb)
        pins[m.group(1)] = {"use": (use.group(1).upper() if use else "SIGNAL"), "direction": d.group(1) if d else "",
                            "rects": _rects(pb)}
    obs = []
    for m in re.finditer(r"(?m)^\s*OBS\s*$(.*?)^\s*END\s*$", body, re.S):
        obs += _rects(m.group(1))
    return {"name": name, "W": W, "H": H, "pins": pins, "obs": obs, "bloat_comment": "bloat" in text.lower()}


def is_pg(name: str, p: dict) -> bool:
    return p["use"] in ("POWER", "GROUND") or name in ("VDD", "VSS")


def face_of(r, W, H) -> str | None:
    _, x0, y0, x1, y1 = r
    if y0 <= EPS:
        return "S"
    if y1 >= H - EPS:
        return "N"
    if x0 <= EPS:
        return "W"
    if x1 >= W - EPS:
        return "E"
    return None


def _overlaps(r, rects) -> bool:
    _, x0, y0, x1, y1 = r
    return any(q[1] < x1 - 1e-6 and q[3] > x0 + 1e-6 and q[2] < y1 - 1e-6 and q[4] > y0 + 1e-6 for q in rects)


# ---------------------------------------------------------------------------------------------------------- checks
def check_pg(m: dict) -> dict:
    W, H = m["W"], m["H"]
    nets = {n: p for n, p in m["pins"].items() if is_pg(n, p)}
    rec = {"nets": {}, "top_layer": None, "ok": True, "why": []}
    if not nets:
        rec.update(ok=False, why=["no VDD/VSS pins"])
        return rec
    tops = {}
    for n, p in nets.items():
        lv = [metal(r[0]) for r in p["rects"] if metal(r[0])]
        tops[n] = max(lv) if lv else None
    top = max((t for t in tops.values() if t), default=None)
    rec["top_layer"] = f"M{top}" if top else None
    for n, p in sorted(nets.items()):
        sh = [r for r in p["rects"] if metal(r[0]) == top]
        full_h = [r for r in sh if (r[3] - r[1]) >= AREA_FRAC * W]       # horizontal stripes across the width
        full_v = [r for r in sh if (r[4] - r[2]) >= AREA_FRAC * H]
        full, horiz = (full_h, True) if len(full_h) >= len(full_v) else (full_v, False)
        area = sum((r[3] - r[1]) * (r[4] - r[2]) for r in sh) or 1.0
        cov = sum((r[3] - r[1]) * (r[4] - r[2]) for r in full) / area
        if full:
            cs = [((r[2] + r[4]) / 2 if horiz else (r[1] + r[3]) / 2) for r in full]
            spread = (max(cs) - min(cs)) / (H if horiz else W)
        else:
            spread = 0.0
        e = {"top_layer": f"M{tops[n]}" if tops[n] else None, "stripes": len(full), "dir": "H" if horiz else "V",
             "spread": round(spread, 3), "coverage": round(cov, 3), "shapes_on_top": len(sh)}
        rec["nets"][n] = e
        if tops[n] != top:
            rec["why"].append(f"{n} top layer {e['top_layer']} != {rec['top_layer']}")
        if len(full) < MIN_STRIPES:
            rec["why"].append(f"{n}: {len(full)} full-length stripes on {rec['top_layer']} (< {MIN_STRIPES})")
        elif spread < MIN_SPREAD:
            rec["why"].append(f"{n}: stripes span only {spread:.0%} of the macro")
    for need in ("VDD", "VSS"):
        if need not in nets and not any(p["use"] == ("POWER" if need == "VDD" else "GROUND") for p in nets.values()):
            rec["why"].append(f"no {need} pin")
    rec["ok"] = not rec["why"]
    return rec


def face_access(m: dict) -> dict:
    W, H = m["W"], m["H"]
    obs = {}
    for r in m["obs"]:
        obs.setdefault(r[0], []).append(r)
    faces, above, below, examples = 0, set(), set(), []
    for n, p in m["pins"].items():
        if is_pg(n, p):
            continue
        for r in p["rects"]:
            L = metal(r[0])
            if L is None or face_of(r, W, H) is None:
                continue
            faces += 1
            if _overlaps(r, obs.get(f"M{L + 1}", [])):
                if n not in above and len(examples) < 6:
                    examples.append(f"{n} {r[0]} ({r[1]:.3f},{r[2]:.3f})")
                above.add(n)
            if _overlaps(r, obs.get(f"M{L - 1}", [])):
                below.add(n)
    return {"face_pins": faces, "blocked_above": len(above), "covered_below": len(below), "examples": examples}


def clock_insertion(lib_text: str) -> dict:
    """{pin: {"max_ps", "min_ps"}} for every clock : true pin with *_clock_tree_path arcs (lib time unit honoured)"""
    unit = re.search(r'time_unit\s*:\s*"?1(ps|ns)"?', lib_text)
    scale = 1000.0 if unit and unit.group(1) == "ns" else 1.0
    out = {}
    for m in re.finditer(r'pin\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', lib_text):
        i, depth = m.end(), 1
        while depth and i < len(lib_text):
            c = lib_text[i]
            depth += (c == "{") - (c == "}")
            i += 1
        body = lib_text[m.end():i]
        if not re.search(r"clock\s*:\s*true", body):
            continue
        vals = {}
        for t in re.finditer(r"timing_type\s*:\s*(max|min)_clock_tree_path\s*;(.*?)(?=timing\s*\(|\Z)", body, re.S):
            nums = [float(v) * scale for v in re.findall(r'values\s*\(\s*"([-\d.eE+]+)', t.group(2))]
            if nums:
                vals.setdefault(t.group(1), []).extend(nums)
        allv = vals.get("max", []) + vals.get("min", [])
        out[m.group(1)] = ({"max_ps": round(max(allv), 2), "min_ps": round(min(allv), 2)} if allv else None)
    return out


def expand_bus(name: str) -> list[str]:
    m = re.fullmatch(r"(.*)\[(\d+):(\d+)\]", name)
    if not m:
        return [name]
    a, b = int(m.group(2)), int(m.group(3))
    return [f"{m.group(1)}[{i}]" for i in range(min(a, b), max(a, b) + 1)]


def contract_slot(path: str, slot: str) -> dict:
    d = json.loads(Path(path).read_text())
    for s in d.get("slots", []):
        if s.get("name") == slot:
            s = dict(s)
            s["_die"] = d.get("die")
            s["_version"] = s.get("version", d.get("version"))
            return s
    raise ValueError(f"slot {slot} not in {path}")


def check_contract(m: dict, s: dict, pg_top: str | None) -> list[str]:
    bad = []
    ow, oh = float(s["outline"]["w"]), float(s["outline"]["h"])
    if abs(ow - m["W"]) > 0.001 or abs(oh - m["H"]) > 0.001:
        bad.append(f"outline {m['W']} x {m['H']} != contract {ow} x {oh}")
    if s.get("pg_layer") and pg_top and s["pg_layer"] != pg_top:
        bad.append(f"PG layer {pg_top} != contract {s['pg_layer']}")
    want = {}
    for p in s.get("pins", []):
        for n in expand_bus(p["name"]):
            want[n] = p
    have = {n: p for n, p in m["pins"].items() if not is_pg(n, p)}
    miss = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    if want and miss:
        bad.append(f"{len(miss)} contract pins missing from the LEF (e.g. {', '.join(miss[:4])})")
    if want and extra:
        bad.append(f"{len(extra)} LEF pins not in the contract (e.g. {', '.join(extra[:4])})")
    wrong = []
    for n in sorted(set(want) & set(have)):
        p, rs = want[n], have[n]["rects"]
        ok = [r for r in rs if (not p.get("layer") or r[0] == p["layer"]) and
              (not p.get("face") or face_of(r, m["W"], m["H"]) == p["face"])]
        if not ok:
            got = ", ".join(sorted({f"{r[0]}/{face_of(r, m['W'], m['H']) or 'interior'}" for r in rs}))
            wrong.append(f"{n} {got} (contract {p.get('layer')}/{p.get('face')})")
        elif p.get("offset") is not None and "[" not in p["name"]:
            r = ok[0]
            c = (r[1] + r[3]) / 2 if p.get("face") in ("N", "S") else (r[2] + r[4]) / 2
            tol = max(float(p.get("width", 0.0)), 0.001)
            if abs(c - float(p["offset"])) > tol:
                wrong.append(f"{n} offset {c:.3f} (contract {p['offset']})")
    if wrong:
        bad.append(f"{len(wrong)} pins off their contract face/layer/offset: {'; '.join(wrong[:4])}")
    return bad


# ---------------------------------------------------------------------------------------------------------- driver
def pick_cap(s: dict | None, pg_top: str | None, cap: str | None = None) -> int | None:
    """the cap (top layer of the child's signals AND PG) to lint at: explicit, else the slot's layer_cap / view_cap that the
    view's PG top layer matches (layer_cap when neither does, so the mismatch fails), else None (pre-1012 behaviour)"""
    if cap:
        return metal(cap)
    s = s or {}
    caps = [c for c in (s.get("layer_cap"), s.get("view_cap")) if c]
    if not caps:
        return None
    for c in caps:
        if pg_top and metal(c) == metal(pg_top):
            return metal(c)
    for c in caps:      # legacy views whose PG sits one layer above their signals (PG-only M7 over M6 signals)
        if pg_top and metal(c) and metal(pg_top) and metal(c) >= metal(pg_top):
            return metal(c)
    return metal(caps[0])


def lint(lef_path: str, libs: str | None = None, contract: str | None = None, slot: str | None = None,
         skip: set | None = None, cap: str | None = None) -> dict:
    skip = skip or set()
    text = Path(lef_path).read_text(errors="replace")
    m = parse_lef(text, slot_cell(contract, slot))
    s = contract_slot(contract, slot) if contract and slot else None
    W, H, cell = m["W"], m["H"], m["name"]
    fails, warns, info = [], [], {"cell": cell, "W": W, "H": H}
    pg = check_pg(m)
    info["pg"] = pg
    cap_L = pick_cap(s, pg["top_layer"], cap)
    if cap_L:
        pg_L, strap_L = cap_L, cap_L + 1
    else:
        pg_L = metal((s or {}).get("pg_layer")) or metal(pg["top_layer"])
        strap_L = metal((s or {}).get("strap_layer")) or ((pg_L + 1) if pg_L else None)
    info["pg_layer"], info["strap_layer"] = (f"M{pg_L}" if pg_L else None), (f"M{strap_L}" if strap_L else None)
    info["cap"] = f"M{cap_L}" if cap_L else None
    if cap_L and s and s.get("layer_cap") and cap_L != metal(s["layer_cap"]):
        info["cap_basis"] = f"view_cap (legacy closed view; slot layer_cap {s['layer_cap']} for new routes)"
    # (a)
    if "a" not in skip and pg_L:
        for r in m["obs"]:
            L = metal(r[0])
            if L and L >= pg_L and (r[3] - r[1]) * (r[4] - r[2]) >= AREA_FRAC * W * H:
                fails.append(f"(a) bloat: one OBS rect covers {(r[3]-r[1])*(r[4]-r[2])/(W*H):.0%} of the macro on {r[0]} "
                             f"(>= PG layer M{pg_L}); re-export WITHOUT -bloat_occupied_layers")
                break
    # (b)
    if "b" not in skip and not pg["ok"]:
        fails.append("(b) pg: " + "; ".join(pg["why"]))
    # (c)
    if "c" not in skip and strap_L:
        hi_obs = sorted({r[0] for r in m["obs"] if (metal(r[0]) or 0) >= strap_L})
        hi_sig = sorted({n for n, p in m["pins"].items() if not is_pg(n, p)
                         for r in p["rects"] if (metal(r[0]) or 0) >= strap_L})
        hi_pg = sorted({r[0] for n, p in m["pins"].items() if is_pg(n, p) for r in p["rects"]
                        if (metal(r[0]) or 0) >= strap_L})
        n_obs = sum(1 for r in m["obs"] if (metal(r[0]) or 0) >= strap_L)
        if hi_obs or hi_sig or hi_pg:
            fails.append(f"(c) strap layer M{strap_L}+ not clear: {n_obs} OBS on {'/'.join(hi_obs) or '-'}, "
                         f"{len(hi_sig)} signal pins, PG on {'/'.join(hi_pg) or '-'} (child signals must stop below "
                         f"the parent strap layer, or own M{strap_L - 1} as full PG stripes and leave M{strap_L} free)")
        smax = cap_L or metal((s or {}).get("signal_max_layer"))
        if smax:
            over = sorted({n for n, p in m["pins"].items() if not is_pg(n, p)
                           for r in p["rects"] if (metal(r[0]) or 0) > smax})
            if over:
                fails.append(f"(c) {len(over)} signal pins above the {'cap' if cap_L else 'contract signal_max_layer'} M{smax} "
                             f"(e.g. {over[0]})")
    # (d)
    tt_lib = None
    if libs:
        missing = [c for c in ("tt", "ff", "ss") if not (Path(libs) / f"{cell}_{c}.lib").exists()]
        if "d" not in skip and missing:
            fails.append(f"(d) libs: {', '.join(f'{cell}_{c}.lib' for c in missing)} missing in {libs}")
        p = Path(libs) / f"{cell}_tt.lib"
        tt_lib = p if p.exists() else None
    # (e)
    if s and "e" not in skip:
        sc = dict(s, pg_layer=f"M{cap_L}") if cap_L else s
        if cap_L and pg["top_layer"] and metal(pg["top_layer"]) < cap_L:
            sc["pg_layer"] = pg["top_layer"]       # a legacy view with PG one layer below its recorded cap
        fails += [f"(e) contract {s.get('_die')}/{slot} v{s.get('_version')}: {b}" for b in check_contract(m, sc, pg["top_layer"])]
    # (f)
    fa = face_access(m)
    info["face"] = fa
    if "f" not in skip and fa["blocked_above"]:
        fails.append(f"(f) face-pin access: {fa['blocked_above']} of {fa['face_pins']} face pins have OBS on the layer "
                     f"above over the pin (DRT-0073 class; e.g. {', '.join(fa['examples'][:3])}); fix: {FACE_FIX}")
    # (g)
    if "g" not in skip:
        target = (s or {}).get("target_insertion_ps")
        if tt_lib is None:
            warns.append("(g) clock insertion: no TT lib (pass --libs) - parent CTS cannot see the tile's insertion delay")
        else:
            ins = clock_insertion(tt_lib.read_text(errors="replace"))
            info["clock_insertion"] = ins
            if not ins or all(v is None for v in ins.values()):
                warns.append(f"(g) clock insertion: no *_clock_tree_path arc on a clock pin in {tt_lib.name}")
            elif target is not None:
                for pin, v in ins.items():
                    if v and abs(v["max_ps"] - float(target)) > INSERTION_TOL_PS:
                        warns.append(f"(g) clock insertion {pin} {v['max_ps']:.0f} ps vs contract target {float(target):.0f} ps "
                                     f"(> {INSERTION_TOL_PS:.0f} ps off): re-budget the slot or the parent CTS")
    verdict = "FAIL" if fails else "PASS"
    summ = (f"{cell} {W} x {H}: PG {pg['top_layer']} "
            + " / ".join(f"{n} {e['stripes']} stripes ({e['spread']:.0%} spread, {e['coverage']:.0%} cov)"
                         for n, e in pg["nets"].items())
            + f"; strap {info['strap_layer']}; face pins {fa['face_pins']} blocked-above {fa['blocked_above']}"
            + "".join(f"; clock {k} insertion {v['max_ps']:.0f} ps" for k, v in (info.get("clock_insertion") or {}).items() if v))
    return {"schema": "opentallas.hier_contract.child_lint.v1", "lef": str(lef_path), "verdict": verdict,
            "fails": fails, "warns": warns, "summary": summ, "info": info}


def slot_cell(contract, slot):
    if not (contract and slot):
        return None
    try:
        return contract_slot(contract, slot).get("cell")
    except (OSError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("lef")
    ap.add_argument("--libs", help="directory holding <cell>_{tt,ff,ss}.lib")
    ap.add_argument("--contract", help="results/arch/hier_contract_1011/<die>.json")
    ap.add_argument("--slot")
    ap.add_argument("--skip", default="", help="comma list of checks to skip (a..g)")
    ap.add_argument("--cap", help="lint at this layer cap (M5 / M6 ...): strap = cap + 1, no signal pin above the cap")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if bool(a.contract) != bool(a.slot):
        ap.error("--contract and --slot go together")
    try:
        r = lint(a.lef, a.libs, a.contract, a.slot, {x.strip() for x in a.skip.split(",") if x.strip()}, a.cap)
    except (OSError, ValueError, KeyError) as ex:
        print(f"ERROR: {ex}")
        return 2
    if a.json:
        print(json.dumps(r, indent=1))
    else:
        print(f"{r['verdict']}: {r['summary']}")
        for x in r["fails"]:
            print("  FAIL " + x)
        for x in r["warns"]:
            print("  WARN " + x)
    return 1 if r["verdict"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
