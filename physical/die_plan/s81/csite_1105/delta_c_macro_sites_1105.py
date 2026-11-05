#!/usr/bin/env python3
"""S81 C-band macro sites (DIE-S81-59 11-05, form of delta_macro_sites_1029.py).

xs4 stays soft in the 16 slice C types, so each bound netlist holds 24 ot_sram_1r1w_128x256_m1_r2c2, 7 ot_rom_4096x72_m8
and 6 ot_sram_1r1w2c_128x64_m1 that no plan row declares: 14 rows stop ORD-2013 at floorplan.  Each type gets static
sites as contents[] rows (PG: core_pg_connect default-on, unset as before).  No outline, bus, ft slot, clock tap, reset, neighbour or die datum
changes (3 types raise tap_radius_um, RADIUS).  Column packer: 8.64 lattice + per-master track offset, columns never x-overlap, >= 10.8 channels and stack
gaps, clear of ft corridors and their actual bit sites, landing rects, cores (+10.8), clock / reset points (+21.6), 43.2 edge band.  Instance
list: csite_1105/instances.json (flattened kit netlist paths).  A second run refuses.

usage: delta_c_macro_sites_1105.py PLAN_IN PLAN_OUT INSTANCES_JSON
"""
import json
import math
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
G, CH, EDGE, HALO, PT_HALO = 8.64, 10.8, 43.2, 10.8, 21.6
# A macro clock pin is farther from its nearest added tap than the type's tap_radius_um (taps.grid_explicit_taps):
# 263.38 / 241.39 / 211.41 um measured.  Each type's budget is raised; tap sites and the reset tree stay as they are.
RADIUS = {"dsdv_slice_c1x_C__t3": 265, "dsdv_slice_iq_C__t1": 245, "dsdv_slice_lepw_mus_C__t1": 215}
TAG = "DIE-S81-59 11-05 C-band macro site (delta_c_macro_sites_1105.py)"
MEM = "physical/asap7_memory_macros_v2"
TRK = {"M4": ("H", 0.048, 0.024, (0.024,)), "M5": ("V", 0.048, 0.024, (0.024,)), "M6": ("H", 0.064, 0.032, (0.032,)),
       "M7": ("V", 0.064, 0.032, (0.032,)), "M3": ("V", 0.036, 0.018, (0.009,)),
       "M2": ("H", 0.270, 0.018, (0.045, 0.081, 0.117, 0.153, 0.189, 0.225, 0.270))}


def lef_info(lef):
    t = (ROOT / lef).read_text()
    m = re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t)
    pins = []
    for pm in re.finditer(r"^\s*PIN\s+(\S+)(.*?)^\s*END\s+\1\b", t, re.M | re.S):
        if re.search(r"\bUSE\s+(POWER|GROUND)\b", pm.group(2)):
            continue
        layer = None
        for tok in re.finditer(r"LAYER\s+(\S+)\s*;|RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", pm.group(2)):
            if tok.group(1):
                layer = tok.group(1)
            elif layer in TRK:
                pins.append((layer, *map(float, tok.groups()[1:])))
    return (float(m.group(1)), float(m.group(2))), pins


def on_grid(pins, ox, oy):
    for layer, x0, y0, x1, y1 in pins:
        d, p, w, offs = TRK[layer]
        lo, hi = (oy + y0, oy + y1) if d == "H" else (ox + x0, ox + x1)
        ok = False
        for of in offs:
            t = of + round(((lo + hi) / 2 - of) / p) * p
            ok = ok or any(lo + w / 2 - 5e-4 <= tt <= hi - w / 2 + 5e-4 for tt in (t - p, t, t + p))
        if not ok:
            return False
    return True


def track_offset(pins):
    for k in range(40):
        for dx in (0.0, 0.108, 0.216, 0.324, 0.432):
            if on_grid(pins, dx, round(0.012 * k, 3)):
                return dx, round(0.012 * k, 3)
    raise SystemExit("no on-grid offset")


def keepouts(t):
    W, H = t["outline_um"]
    rects, pts = [], []

    def band(face, win, other=None):
        lo, hi = win[0] - HALO, win[1] + HALO
        if face in "NS":
            if other is None:
                return [lo, 0, hi, H]
            return [lo, other[0] - HALO, hi, H] if face == "N" else [lo, 0, hi, other[1] + HALO]
        if other is None:
            return [0, lo, W, hi]
        return [0, lo, other[1] + HALO, hi] if face == "W" else [other[0] - HALO, lo, W, hi]

    for s in t.get("ft_slots", []):
        fi, fo, wi, wo = s["in_face"], s["out_face"], s["in_window_um"], s["out_window_um"]
        if {fi, fo} in ({"N", "S"}, {"E", "W"}):
            rects += [band(fi, wi), band(fo, wo)]
        else:
            rects += [band(fi, wi, wo), band(fo, wo, wi)]

    for s in t.get("ft_slots", []):            # stations outside the window: the actual bit sites (G0 'geometry')
        for stage in s.get("bit_sites_um") or []:
            xs, ys = [q[0] for q in stage], [q[1] for q in stage]
            rects.append([min(xs) - HALO, min(ys) - HALO, max(xs) + HALO, max(ys) + HALO])
        for q in s.get("regs_um") or []:
            pts.append(tuple(q[:2]))

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "rect_um" and isinstance(v, list) and len(v) == 4:
                    rects.append([v[0] - HALO, v[1] - HALO, v[2] + HALO, v[3] + HALO])
                elif k in ("xy", "xy_um", "tap_um", "root") and isinstance(v, list) and len(v) == 2 \
                        and all(isinstance(a, (int, float)) for a in v):
                    pts.append(tuple(v))
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(t.get("clock", {}))
    walk(t.get("reset", {}))
    walk(t.get("internal_stations", []))
    for c in t.get("contents", []) + t.get("hard_cores", []):
        if "origin_um" in c and "outline_um" in c:
            x, y = c["origin_um"]
            w, h = c["outline_um"]
            rects.append([x - HALO, y - HALO, x + w + HALO, y + h + HALO])
    return rects, pts


def hit(b, rects, pts):
    return any(b[0] < r[2] and r[0] < b[2] and b[1] < r[3] and r[1] < b[3] for r in rects) or \
        any(b[0] - PT_HALO < x < b[2] + PT_HALO and b[1] - PT_HALO < y < b[3] + PT_HALO for x, y in pts)


def snap(v):
    return round(math.ceil(v / G - 1e-9) * G, 4)


def place(tn, t, insts, masters):
    """columns left to right, biggest master first; every column holds one master."""
    W, H = t["outline_um"]
    rects, pts = keepouts(t)
    sites, x = [], snap(EDGE)
    order = sorted(insts, key=lambda m: (-masters[m]["size"][0], m))
    for mod in order:
        q = sorted(insts[mod])
        (w, h), (dx, dy) = masters[mod]["size"], masters[mod]["off"]
        while q:
            if x + w > W - EDGE:
                raise SystemExit(f"{tn}: {len(q)} {mod} unplaced")
            y, n = snap(EDGE), 0
            while q and y + h <= H - EDGE:
                if hit((x, y, x + w + dx, y + h + dy), rects, pts):
                    y = round(y + G, 4)
                    continue
                sites.append(dict(inst=q.pop(0), module=mod, status="new", lef=masters[mod]["lef"], lib=masters[mod]["lib"],
                                  origin_um=[round(x + dx, 3), round(y + dy, 3)], outline_um=[w, h], orient="R0",
                                  obs_max="M4", note=TAG))
                n += 1
                y = snap(y + h + dy + CH)
            x = snap(x + w + dx + CH)
    return sites


def compact(o):
    return json.dumps(o, separators=(",", ":"))


def main():
    src, dst, ins = sys.argv[1:4]
    txt = Path(src).read_text()
    plan = json.loads(txt)
    ev = json.loads(Path(ins).read_text())
    masters = {}
    for mod in {m for e in ev.values() for m in e}:
        lef = f"{MEM}/{mod}/{mod}.lef"
        size, pins = lef_info(lef)
        masters[mod] = dict(lef=lef, lib=f"{MEM}/{mod}/{mod}_tt.lib", size=list(size), off=track_offset(pins))
    report = {}
    for tn, insts in ev.items():
        t = plan["partition_types"][tn]
        assert not any(c.get("note") == TAG for c in t["contents"]), (tn, "second run")
        sites = place(tn, t, insts, masters)
        head = f'\n  "{tn}": {{\n'
        assert txt.count(head) == 1, tn
        a = txt.index(head)
        b = txt.index('\n  },', a)
        block = txt[a:b]
        old = '   "contents": [\n' + "".join(f"    {compact(c)}{',' if i < len(t['contents']) - 1 else ''}\n"
                                              for i, c in enumerate(t["contents"])) + '   ],\n'
        assert block.count(old) == 1, (tn, "contents text form")
        rows = t["contents"] + sites
        new = '   "contents": [\n' + "".join(f"    {compact(c)}{',' if i < len(rows) - 1 else ''}\n"
                                              for i, c in enumerate(rows)) + '   ],\n'
        nb = block.replace(old, new)
        if tn in RADIUS:
            nb, n = re.subn(r'("tap_radius_um": )[\d.]+', lambda m: m.group(1) + str(RADIUS[tn]), nb)
            assert n == 1, (tn, "tap_radius_um")
        txt = txt[:a] + nb + txt[b:]
        ys = [s["origin_um"][1] for s in sites]
        xs = [s["origin_um"][0] for s in sites]
        report[tn] = dict(n=len(sites), x=[min(xs), max(s["origin_um"][0] + s["outline_um"][0] for s in sites)],
                          y=[min(ys), max(s["origin_um"][1] + s["outline_um"][1] for s in sites)])
    after = json.loads(txt)
    assert set(after) == set(plan)
    for tn in plan["partition_types"]:
        if tn not in ev:
            assert after["partition_types"][tn] == plan["partition_types"][tn], tn
    Path(dst).write_text(txt)
    print(json.dumps(report, indent=0))


if __name__ == "__main__":
    main()
