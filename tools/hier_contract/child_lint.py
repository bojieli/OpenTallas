#!/usr/bin/env python3
"""Hard-child abstract lint for the TOP-DOWN HIERARCHY CONTRACT (owner 2026-10-11, tools/hier_contract/schema.md).

A parent may only be submitted when every hard child it instantiates passes this lint.  Checks (FAIL unless noted):
  (a) bloat      no OBS rect covering >= 90% of the macro area on a layer >= the child's PG layer
                 (write_abstract_lef -bloat_occupied_layers; preamble UPDATE 2, PDN-0006).  Full-tile M1 cell-row OBS
                 below the PG layer is normal and allowed.
  (b) pg         VDD and VSS each have full-length stripes (>= 90% of the macro span) on ONE common top layer;
                 reports stripe count, spread across the macro and coverage (full-stripe share of top-layer PG metal).
                 A stripe crossing every standard-cell row (the M1 row region, itself within one row of the 2.16-um
                 insets) also counts: off-lattice outlines lose up to one row to quantisation (S81 fill 10-15).
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
                 Also FAIL: an OBS rect on the pin's OWN layer overlapping that pin (positive area; edge touch ignored)
                 and no other pin -- the exporter wrote the pin net's route stub as OBS (ot_qkvd_sbuf, DRT-0073); fix
                 abstract_pin_stub.py.  A same-layer OBS rect spanning several pins is WARN only (edge-band decomposition).
  (g) clock      WARN only: clock-pin insertion delay (max/min_clock_tree_path) from the TT lib; missing, or more than
                 100 ps from the contract slot's target_insertion_ps (preamble CLOCK LATENCY ACROSS THE HIERARCHY).
  (h) pockets    interior own-layer pockets: on the child's OWN TOP SIGNAL LAYER (highest metal layer with OBS) no free gap
                 narrower than D (32 routing pitches, 2.048 um on M6) between two of the child's own obstacles (OBS + PG
                 pin rects; never obstacle-to-boundary, never within a pitch of a signal pin on that layer or the one
                 below) -- a parent router that enters one shorts against the child (hc_tile_xl-c4-550082537-hs: DRC 11
                 in one M6 pocket of ot_hdc_v41x_hcp_lanes).  Detection is abstract_pin_stub.find_pockets (the sibling
                 file; not importable = FAIL).  A LEF carrying the exporter's `# OT_OBS_CLOSED` marker (every export
                 since 2026-10-13): any pocket = FAIL.  A LEF without it (exported before the fix; accepted closed views
                 stand): WARN with the count, the largest pocket and the fix command -- FAIL under --strict-pockets,
                 which a parent that routes on the child's own top layer should use on its children.

exit 0 = PASS (warnings allowed), 1 = FAIL, 2 = usage / unreadable input.  --json prints the machine record.
Usage: child_lint.py CHILD.lef [--libs DIR] [--contract DIE.json --slot NAME] [--json] [--skip f,g] [--strict-pockets]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

AREA_FRAC = 0.90          # (a) bloat threshold and (b) full-stripe span fraction
MIN_STRIPES = 2           # (b) per net
EPS_UM = 0.001            # 1 DBU: LEF microns are decimal, floats are not (43.2-um tile, 2.16-um insets: 38.88 < 0.9*43.2 in floats)
EDGE_INSET_UM = 2.16      # (b) ref_tile stops PG stripes this far short of each edge; a stripe reaching within the inset of both edges is full-length (thin tiles < 43.2 um failed the 90% rule: ctfx 12.96 um tall = 67%)
ROW_QUANT_UM = 0.27      # (b) one ASAP7 cell row: the PDN core (rows) of an outline that is not a multiple of the row/PG lattice
                         # ends up to one row short of the 2.16-um inset (S81 fill dsfd_hstnh_112 17.256 um tall: rows and
                         # stripes 2.151..14.859/14.873, 0.237 um short at the top) -- see row_span() / check_pg
MIN_SPREAD = 0.50         # (b) first..last full stripe must span this fraction of the perpendicular dimension
INSERTION_TOL_PS = 100.0  # (g)
EPS = 0.0015              # um: boundary touch tolerance
FACE_FIX = ("physical/redesign_ds/coll_split/pin_access_pregrt.tcl (bf0080873): obstruct the adjacent layers over the "
            "outer face-pin column before GRT, remove after DRT")

SAME_FIX = ("tools/hier_contract/abstract_pin_stub.py IN.lef OUT.lef (73e17f447): move the pin's own same-layer stub "
            "from OBS into its PORT")
POCKET_FIX = ("tools/hier_contract/abstract_pin_stub.py IN.lef OUT.lef: closes own-top-layer gaps between the child's own "
              "obstacles and writes the OT_OBS_CLOSED marker (then re-run child_lint)")


def pockets(text: str) -> dict:
    """(h): abstract_pin_stub.find_pockets on the LEF text; {'error': why} when the sibling detector is unusable"""
    src = Path(__file__).resolve().parent / "abstract_pin_stub.py"
    try:
        # never import a pre-2026-10-13 copy: that one is a bare script acting on sys.argv at import time
        if "def find_pockets" not in src.read_text(errors="replace"):
            return {"error": f"{src} is a pre-pocket-closing copy (no find_pockets)"}
        if str(src.parent) not in sys.path:
            sys.path.insert(0, str(src.parent))
        import abstract_pin_stub as APS
        if not hasattr(APS, "find_pockets"):
            return {"error": f"abstract_pin_stub imported from {getattr(APS, '__file__', '?')} has no find_pockets"}
        r = APS.find_pockets(text)
    except Exception as ex:  # noqa: BLE001 - any detector failure must fail the check, not skip it
        return {"error": f"{src.name}: {type(ex).__name__}: {ex}"}
    rs = sorted(r["rects"], key=lambda q: -(q[2] - q[0]) * (q[3] - q[1]))
    return {"layer": r["layer"], "d_um": r["d_um"], "marker": r["marker"], "count": len(rs),
            "area_um2": round(sum((q[2] - q[0]) * (q[3] - q[1]) for q in rs), 3),
            "examples": [f"({q[0]:g},{q[1]:g})-({q[2]:g},{q[3]:g})" for q in rs[:3]]}


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


def row_span(m: dict):
    """(x0, y0, x1, y1) of the standard-cell row region = bbox of the M1 OBS (the cell-row blockage every routed-tile
    abstract carries below the PG layer), or None when the abstract has no M1 OBS"""
    r1 = [r for r in m["obs"] if r[0] == "M1"]
    if not r1:
        return None
    return (min(r[1] for r in r1), min(r[2] for r in r1), max(r[3] for r in r1), max(r[4] for r in r1))


# ---------------------------------------------------------------------------------------------------------- checks
def check_pg(m: dict) -> dict:
    """(b).  A stripe is full-length when it spans >= 90% of the macro or reaches within EDGE_INSET_UM of both edges, OR
    -- the physical criterion those proxies stand for -- it crosses EVERY standard-cell row (covers the whole M1 row
    region along its direction) and that row region itself reaches within EDGE_INSET_UM + ROW_QUANT_UM of both edges
    (row quantisation of an off-lattice outline, never a shrunken core).  Such a stripe connects every row's follow-pin
    rails, which is what the parent's strap needs; a stripe that misses a row still fails."""
    W, H = m["W"], m["H"]
    rs = row_span(m)
    def rows_ok(a0, a1, span):
        return a0 <= EDGE_INSET_UM + ROW_QUANT_UM + EPS_UM and a1 >= span - EDGE_INSET_UM - ROW_QUANT_UM - EPS_UM
    def crosses_rows(r, horiz):
        if rs is None:
            return False
        if horiz:
            return rows_ok(rs[0], rs[2], W) and r[1] <= rs[0] + EPS_UM and r[3] >= rs[2] - EPS_UM
        return rows_ok(rs[1], rs[3], H) and r[2] <= rs[1] + EPS_UM and r[4] >= rs[3] - EPS_UM
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
        full_h = [r for r in sh if (r[3] - r[1]) + EPS_UM >= min(AREA_FRAC * W, W - 2 * EDGE_INSET_UM)
                  or (r[3] - r[1]) > (r[4] - r[2]) and crosses_rows(r, True)]       # horizontal stripes across the width
        full_v = [r for r in sh if (r[4] - r[2]) + EPS_UM >= min(AREA_FRAC * H, H - 2 * EDGE_INSET_UM)
                  or (r[4] - r[2]) > (r[3] - r[1]) and crosses_rows(r, False)]
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
    # only OBS reaching into the edge band of the deepest face pin can overlap a face pin: index those alone (a
    # routed tile has 10^5 OBS rects; pins x all OBS took minutes per view)
    band = max((max(r[3] - r[1], r[4] - r[2]) for n, p in m["pins"].items() if not is_pg(n, p) for r in p["rects"]
                if face_of(r, W, H)), default=0.0) + EPS
    obs = {}
    for r in m["obs"]:
        if r[1] < band or r[2] < band or r[3] > W - band or r[4] > H - band:
            obs.setdefault(r[0], []).append(r)
    faces, above, below, same, examples, same_ex = 0, set(), set(), set(), [], []
    band, band_ex, same_hits = set(), [], {}
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
            for o in obs.get(r[0], []):            # same-layer OBS over the pin (positive area; edge touch ignored)
                if _overlaps(r, [o]):
                    same_hits.setdefault(o, set()).add(n)
    # an OBS rect overlapping exactly ONE face pin on its layer is that pin's own route stub written as OBS (ot_qkvd_sbuf
    # pop, 73e17f447: DRT-0073 reproduced standalone) -> blocked.  A rect spanning several pins is the exporter's
    # decomposition of the occupied edge band (it cannot be metal: it would short different nets); 126 of the 128
    # views passing on 2026-10-12, every ref_tile view included, carry it, and the sbuf repro's din pins under it got
    # access -> reported (WARN) only.
    for o, ns in same_hits.items():
        tgt = same if len(ns) == 1 else band
        for n in sorted(ns):
            if n not in tgt and len(same_ex if tgt is same else band_ex) < 6:
                (same_ex if tgt is same else band_ex).append(f"{n} {o[0]} ({o[1]:.3f},{o[2]:.3f})")
            tgt.add(n)
    return {"face_pins": faces, "blocked_above": len(above), "covered_below": len(below), "examples": examples,
            "blocked_same": len(same), "same_examples": same_ex, "band_same": len(band - same), "band_examples": band_ex}


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


def check_contract(m: dict, s: dict, pg_top: str | None, pin_grant: dict | None = None) -> list[str]:
    bad = []
    granted_ports = {}
    if pin_grant:
        import m6_pin_grant as M6
        granted_ports = M6.validate(pin_grant, m["name"])
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
        ok = [r for r in rs if (not p.get("layer") or r[0] == p["layer"] or
              (granted_ports and M6.approved(n, r, m, granted_ports))) and
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
def cap_str(v) -> str | None:
    """a slot layer_cap / view_cap as a layer name: derived contracts carry the dict form
    {"cap": "M5", "view_max_layer": ..., "conforms": ...} (qwen_rom_tp8 v3; slot_fit.py reads it the same way)"""
    return v.get("cap") if isinstance(v, dict) else v


def pick_cap(s: dict | None, pg_top: str | None, cap: str | None = None) -> int | None:
    """the cap (top layer of the child's signals AND PG) to lint at: explicit, else the slot's layer_cap / view_cap that the
    view's PG top layer matches (layer_cap when neither does, so the mismatch fails), else None (pre-1012 behaviour)"""
    if cap:
        return metal(cap)
    s = s or {}
    caps = [c for c in (cap_str(s.get("layer_cap")), cap_str(s.get("view_cap"))) if c]
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
         skip: set | None = None, cap: str | None = None, pin_grant: dict | None = None,
         routed_def: str | None = None, tech_lef: str | None = None, strict_pockets: bool = False) -> dict:
    skip = skip or set()
    text = Path(lef_path).read_text(errors="replace")
    m = parse_lef(text, slot_cell(contract, slot))
    s = contract_slot(contract, slot) if contract and slot else None
    W, H, cell = m["W"], m["H"], m["name"]
    fails, warns, info = [], [], {"cell": cell, "W": W, "H": H}
    pg = check_pg(m)
    info["pg"] = pg
    grant = pin_grant if pin_grant is not None else (s or {}).get("m6_pin_grant")
    allowed = set()
    if grant is not None:
        import m6_pin_grant as M6
        try:
            ports = M6.validate(grant, cell)
            if cap not in (None, "M5") or cap_str((s or {}).get("layer_cap")) not in (None, "M5"):
                raise ValueError("M6 pin-only grant requires layer_cap M5, never cap/view_cap M6")
            if pg["top_layer"] != "M5":
                raise ValueError("M6 pin-only grant requires PG top M5")
            unknown = set(ports) - set(m["pins"])
            if unknown:
                raise ValueError(f"grant names unknown ports: {sorted(unknown)[:4]}")
            for n, p in m["pins"].items():
                for r in p["rects"]:
                    if (metal(r[0]) or 0) > 5:
                        if not M6.approved(n, r, m, ports):
                            raise ValueError(f"ungranted/oversized high PORT geometry {n}/{r[0]}")
                        allowed.add(n)
            if re.search(r"\b(?:POLYGON|PATH|VIA)\b", text):
                raise ValueError("pin-only audit requires explicit LEF RECT geometry, not unparsed POLYGON/PATH/VIA")
            if not routed_def:
                raise ValueError("pin-only grant requires raw routed DEF evidence")
            bad, evidence = M6.audit_def(routed_def, m, ports, tech_lef)
            fails += ["(c) M6 pin-only: " + b for b in bad]
            import hashlib
            evidence["lef_sha256"] = hashlib.sha256(text.encode()).hexdigest()
            evidence["granted_by"] = grant["granted_by"]
            evidence["m6_ports"] = sorted(allowed)
            info["m6_pin_grant"] = evidence
        except (ValueError, OSError, TypeError, KeyError) as ex:
            fails.append(f"(c) M6 pin-only: {ex}")
            allowed = set()
    cap_L = 5 if grant is not None else pick_cap(s, pg["top_layer"], cap)
    if cap_L:
        pg_L, strap_L = cap_L, cap_L + 1
    else:
        pg_L = metal((s or {}).get("pg_layer")) or metal(pg["top_layer"])
        strap_L = metal((s or {}).get("strap_layer")) or ((pg_L + 1) if pg_L else None)
    info["pg_layer"], info["strap_layer"] = (f"M{pg_L}" if pg_L else None), (f"M{strap_L}" if strap_L else None)
    info["cap"] = f"M{cap_L}" if cap_L else None
    if cap_L and s and cap_str(s.get("layer_cap")) and cap_L != metal(cap_str(s["layer_cap"])):
        info["cap_basis"] = f"view_cap (legacy closed view; slot layer_cap {cap_str(s['layer_cap'])} for new routes)"
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
    if ("c" not in skip or grant is not None) and strap_L:
        hi_obs = sorted({r[0] for r in m["obs"] if (metal(r[0]) or 0) >= strap_L})
        hi_sig = sorted({n for n, p in m["pins"].items() if not is_pg(n, p) and n not in allowed
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
            over = sorted({n for n, p in m["pins"].items() if not is_pg(n, p) and n not in allowed
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
        fails += [f"(e) contract {s.get('_die')}/{slot} v{s.get('_version')}: {b}" for b in check_contract(m, sc, pg["top_layer"], grant if allowed else None)]
    # (f)
    fa = face_access(m)
    info["face"] = fa
    if "f" not in skip and fa["blocked_above"]:
        fails.append(f"(f) face-pin access: {fa['blocked_above']} of {fa['face_pins']} face pins have OBS on the layer "
                     f"above over the pin (DRT-0073 class; e.g. {', '.join(fa['examples'][:3])}); fix: {FACE_FIX}")
    if "f" not in skip and fa["blocked_same"]:
        fails.append(f"(f) face-pin access: {fa['blocked_same']} of {fa['face_pins']} face pins overlapped by OBS on their OWN "
                     f"layer by a stub OBS touching no other pin (the pin's route stub exported as OBS: no access point, DRT-0073 class; e.g. "
                     f"{', '.join(fa['same_examples'][:3])}); fix: {SAME_FIX}")
    if "f" not in skip and fa["band_same"]:
        warns.append(f"(f) face-pin access: {fa['band_same']} of {fa['face_pins']} face pins partly under a same-layer OBS rect "
                     f"spanning several pins (exporter edge-band decomposition; e.g. {', '.join(fa['band_examples'][:3])})")
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
    # (h)
    if "h" not in skip:
        pk = pockets(text)
        info["pockets"] = pk
        if pk.get("error"):
            fails.append(f"(h) pockets: detector unavailable ({pk['error']}); ship tools/hier_contract/abstract_pin_stub.py "
                         f"next to child_lint.py")
        elif pk["count"]:
            msg = (f"(h) pockets: {pk['count']} open own-layer pocket rects on {pk['layer']} ({pk['area_um2']:g} um2; gaps < "
                   f"{pk['d_um']:g} um between the child's own obstacles; largest {', '.join(pk['examples'])})")
            if pk["marker"]:
                fails.append(msg + f" in a LEF marked OT_OBS_CLOSED (edited after the export?); fix: {POCKET_FIX}")
            elif strict_pockets:
                fails.append(msg + f"; --strict-pockets (the parent routes on {pk['layer']}); fix: {POCKET_FIX}")
            else:
                warns.append(msg + f"; view exported before the pocket fix (no OT_OBS_CLOSED marker): a parent routing on "
                             f"{pk['layer']} must lint with --strict-pockets; fix: {POCKET_FIX}")
    verdict = "FAIL" if fails else "PASS"
    summ = (f"{cell} {W} x {H}: PG {pg['top_layer']} "
            + " / ".join(f"{n} {e['stripes']} stripes ({e['spread']:.0%} spread, {e['coverage']:.0%} cov)"
                         for n, e in pg["nets"].items())
            + f"; strap {info['strap_layer']}; face pins {fa['face_pins']} blocked-above {fa['blocked_above']}"
            + f" blocked-same {fa['blocked_same']}"
            + "".join(f"; clock {k} insertion {v['max_ps']:.0f} ps" for k, v in (info.get("clock_insertion") or {}).items() if v)
            + ("" if "pockets" not in info or info["pockets"].get("error") or not info["pockets"]["layer"] else
               f"; pockets {info['pockets']['layer']} {info['pockets']['count']}"
               + (" (closed)" if info["pockets"]["marker"] else " (legacy view)")))
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
    ap.add_argument("--skip", default="", help="comma list of checks to skip (a..h)")
    ap.add_argument("--cap", help="lint at this layer cap (M5 / M6 ...): strap = cap + 1, no signal pin above the cap")
    ap.add_argument("--pin-grant", help="JSON M6 pin-only grant; requires --routed-def")
    ap.add_argument("--tech-lef", help="exact technology LEF read by the route (named via RECT geometry)")
    ap.add_argument("--routed-def", help="raw routed DEF for independent nonpin metal and PORT geometry audit")
    ap.add_argument("--strict-pockets", action="store_true",
                    help="(h) FAIL on own-top-layer pockets even in a view exported before the pocket fix (no OT_OBS_CLOSED "
                         "marker); use when the parent routes on the child's own top layer")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if bool(a.contract) != bool(a.slot):
        ap.error("--contract and --slot go together")
    try:
        r = lint(a.lef, a.libs, a.contract, a.slot, {x.strip() for x in a.skip.split(",") if x.strip()}, a.cap, json.loads(Path(a.pin_grant).read_text()) if a.pin_grant else None, a.routed_def, a.tech_lef, a.strict_pockets)
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
