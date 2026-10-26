#!/usr/bin/env python3
"""HBM-CORE-LAT 2026-10-26 (COORD ruling 3 / METHODOLOGY 12.7c): island-aware hard-core abstract.

    ODB=6_final.odb LEF=<core>.lef ISL=/work/infra_islands.json OUT=/work/island_abstract.json \
        openroad -python -exit island_abstract.py

write_abstract_lef bloats every occupied layer to one full-outline OBS rectangle, which hides the die-owned INFRA
STRIP and VIA WINDOWS of an island kit (gen_core_kit_hbm.py --infra-islands).  This step rewrites the LEF in place:
  * OBS: the strip is cut out of the strip layers (M1-M2, core_blockage.routing_strip) and every via window out of
    the window layers (M3-M5); the remaining OBS is the exact rectangle difference (<= 4 rects per cut);
  * PG: the core's VDD/VSS followpin rails inside the strip (read from the routed ODB special wires on the strip
    layers, clipped to the strip) are added as PORTs of PIN VDD / PIN VSS, so die cells placed in the strip
    connect to them (followpin abutment) and the die router sees them as PG, not as hidden metal.
Fail-closed (exit 1): no rail of either net in the strip, a non-RECT OBS shape on a cut layer, or any OBS rect left
overlapping the strip / a window on its layers.  The pure functions (subtract, rewrite_lef) carry the unit test.
"""
import json
import os
import re
import sys


def subtract(r, c):
    """Rect r minus rect c (x0,y0,x1,y1) -> list of disjoint rects covering r \\ c."""
    x0, y0, x1, y1 = r
    cx0, cy0, cx1, cy1 = max(c[0], x0), max(c[1], y0), min(c[2], x1), min(c[3], y1)
    if cx0 >= cx1 or cy0 >= cy1:
        return [tuple(r)]
    out = []
    if y0 < cy0:
        out.append((x0, y0, x1, cy0))
    if cy1 < y1:
        out.append((x0, cy1, x1, y1))
    if x0 < cx0:
        out.append((x0, cy0, cx0, cy1))
    if cx1 < x1:
        out.append((cx1, cy0, x1, cy1))
    return out


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def cuts_for(isl):
    """{layer: [cut rects]} from the island entry (core frame, um)."""
    cb = isl["core_blockage"]
    cuts = {ly: [tuple(isl["strip_um"])] for ly in cb["routing_strip"]}
    for ly in cb["routing_windows"]:
        if ly in cb["routing_strip"]:
            continue                                   # windows lie inside the strip: already cut there
        cuts.setdefault(ly, []).extend(tuple(w) for w in isl["windows_um"])
    return cuts


def _fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".")


def rewrite_lef(text, cuts, ports):
    """Return (new_text, stats).  cuts {layer: [rects]}; ports {"VDD"|"VSS": {layer: [rects]}} (um)."""
    lines = text.split("\n")
    try:
        o0 = next(i for i, ln in enumerate(lines) if ln.strip() == "OBS")
    except StopIteration:
        raise SystemExit("island_abstract: LEF has no OBS section")
    o1 = next(i for i in range(o0 + 1, len(lines)) if lines[i].strip() == "END")
    layers, cur = [], None
    for ln in lines[o0 + 1:o1]:
        t = ln.strip()
        m = re.match(r"^LAYER\s+(\S+)\s*;$", t)
        if m:
            cur = [m.group(1), [], []]
            layers.append(cur)
            continue
        m = re.match(r"^RECT\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*;$", t)
        if m and cur is not None:
            cur[1].append(tuple(float(v) for v in m.groups()))
        elif t:
            if cur is None:
                raise SystemExit(f"island_abstract: OBS statement outside a LAYER: {t}")
            cur[2].append(t)                            # other statements kept verbatim (checked below on cut layers)
    stats = dict(obs_rects_before=0, obs_rects_after=0, cut_layers=sorted(cuts), ports={})
    body = []
    for ly, rects, other in layers:
        stats["obs_rects_before"] += len(rects)
        if ly in cuts:
            if other:
                raise SystemExit(f"island_abstract: non-RECT OBS on cut layer {ly}: {other[:2]}")
            for c in cuts[ly]:
                rects = [p for r in rects for p in subtract(r, c)]
            bad = [r for r in rects for c in cuts[ly] if overlaps(r, c)]
            if bad:
                raise SystemExit(f"island_abstract: OBS still overlaps a cut on {ly}: {bad[:2]}")
        stats["obs_rects_after"] += len(rects)
        body.append(f"    LAYER {ly} ;")
        body += [f"     RECT  {' '.join(_fmt(v) for v in r)} ;" for r in rects]
        body += [f"     {t}" for t in other]
    lines[o0 + 1:o1] = body
    for net, by_layer in ports.items():
        n = sum(len(v) for v in by_layer.values())
        if n == 0:
            raise SystemExit(f"island_abstract: no {net} rail in the strip")
        try:
            e = next(i for i, ln in enumerate(lines) if ln.strip() == f"END {net}")
        except StopIteration:
            raise SystemExit(f"island_abstract: LEF has no PIN {net}")
        add = ["    PORT"]
        for ly in sorted(by_layer):
            add.append(f"      LAYER {ly} ;")
            add += [f"        RECT  {' '.join(_fmt(v) for v in r)} ;" for r in by_layer[ly]]
        add.append("    END")
        lines[e:e] = add
        stats["ports"][net] = n
    return "\n".join(lines), stats


def strip_rails(block, isl):
    """VDD/VSS special-wire rects on the strip layers inside the strip, clipped to it (um, core frame)."""
    u = block.getDbUnitsPerMicron()
    die = block.getDieArea()
    ox, oy = die.xMin(), die.yMin()
    s = isl["strip_um"]
    lys = set(isl["core_blockage"]["routing_strip"])
    out = {}
    for net in ("VDD", "VSS"):
        n = block.findNet(net)
        got = {}
        for sw in (n.getSWires() if n else []):
            for b in sw.getWires():
                if b.isVia() or b.getTechLayer().getName() not in lys:
                    continue
                r = ((b.xMin() - ox) / u, (b.yMin() - oy) / u, (b.xMax() - ox) / u, (b.yMax() - oy) / u)
                if not overlaps(r, s):
                    continue
                c = (max(r[0], s[0]), max(r[1], s[1]), min(r[2], s[2]), min(r[3], s[3]))
                got.setdefault(b.getTechLayer().getName(), []).append(c)
        out[net] = got
    return out


def main():
    import odb                                        # openroad -python only
    isl = json.load(open(os.environ["ISL"]))
    db = odb.read_db(odb.dbDatabase.create(), os.environ["ODB"])
    ports = strip_rails(db.getChip().getBlock(), isl)
    lef = os.environ["LEF"]
    new, st = rewrite_lef(open(lef).read(), cuts_for(isl), ports)
    open(lef, "w").write(new)
    st.update(module=isl.get("module"), strip_um=isl["strip_um"], windows=len(isl["windows_um"]), lef=os.path.basename(lef),
              verdict="PASS")
    json.dump(st, open(os.environ.get("OUT", "/work/island_abstract.json"), "w"), indent=1)
    print("OT_ISLAND_ABSTRACT PASS", json.dumps(st))


if os.environ.get("ISL") and os.environ.get("ODB"):          # openroad -python runs the file; the test imports it
    try:
        main()
    except SystemExit as e:
        if e.code not in (None, 0):
            print(f"OT_ISLAND_ABSTRACT FAIL {e.code}")
            json.dump(dict(verdict="FAIL", reason=str(e.code)), open(os.environ.get("OUT", "/work/island_abstract.json"), "w"))
            sys.exit(1)
