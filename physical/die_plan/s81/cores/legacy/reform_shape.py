#!/usr/bin/env python3
"""S81-RF1 RE-FORM shape tool (DIE-S81-51/RF-A, 2026-11-03).

Re-shape one hard core's plan pin table onto a new outline (fill band 0.35-0.45, aspect <= 3:1):
  * every pin keeps its face, layer and order along the face; the along-face coordinate is scaled by L_new / L_old
    and snapped to the layer track lattice (the die tracks after the S81 core offset, gen_core_kit_legacy.TRACKS);
  * the edge coordinate keeps its distance to its own edge (N / E pins move with the new edge);
  * PG-aware pin band (vs S81-041 DRT class): a pin whose along-face track lies over a core M5 strap pair (VDD/VSS,
    pdn.tcl: pitch 4.32, offset 2.064 from the core origin, width 0.12, spacing 0.072) plus a keep-out is moved to
    the next free track, so the pin escape never lands on the strap's VIA23/34/45 ladder pads;
  * minimum along-face pitch per layer is kept (greedy sweep in face order).
Writes the new pins json (same schema) and a plan copy whose rows of the module get the new outline / pins_file.
"""
import argparse, json, math, re
from pathlib import Path

TRACK = {"M3": (0.009, 0.036), "M4": (0.012, 0.048), "M5": (0.012, 0.048)}
MIN_PITCH = {"M3": 0.072, "M4": 0.096, "M5": 0.096}
CORE_M = 4.32
STRAP_PITCH, STRAP_OFF, STRAP_SPAN = 4.32, 2.064, 0.312   # VSS 0.12 + 0.072 + VDD 0.12
KEEP = 0.15                                                 # keep-out beyond the pair edges (>= 3 M5 tracks)


def face(x, y, w, h):
    if y < 0.5: return "S"
    if y > h - 0.5: return "N"
    if x < 0.5: return "W"
    if x > w - 0.5: return "E"
    raise SystemExit(f"interior pin at {x},{y}")


def on_strap(v, along_is_x):
    """True when along-face coordinate v (core-frame um) lies over a vertical M5 strap pair (+keep-out)."""
    if not along_is_x:
        return False                      # M5 straps are vertical: only N/S faces cross them
    r = (v - CORE_M - STRAP_OFF) % STRAP_PITCH
    return r <= STRAP_SPAN + KEEP or r >= STRAP_PITCH - KEEP


def snap(v, layer, up=False):
    o, p = TRACK[layer]
    k = (v - o) / p
    k = math.ceil(k - 1e-9) if up else round(k)
    return round(o + k * p, 4)


RECT = {"M3": (0.018, 0.038), "M4": (0.084, 0.024), "M5": (0.024, 0.084)}   # gen_core_kit_legacy.RECT (w, h)


def write_contract_lef(lef_in, lef_out, macro, pins, w, h):
    """Contract LEF of the re-formed outline: SIZE + one edge rectangle per pin (directions / USE from lef_in), no OBS
    (a plan contract, replaced by the signed abstract after sign-off)."""
    txt = Path(lef_in).read_text()
    dirs = {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(
        r"PIN (\S+)\s+DIRECTION (\w+) ;\s+USE (\w+) ;", txt)}
    fl = re.search(r"FOREIGN (\S+)", txt)
    sizes = {}
    for m in re.finditer(r"PIN (\S+)\s.*?RECT\s+([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) ;", txt, re.S):
        if m.group(1) not in sizes:
            x0, y0, x1, y1 = map(float, m.group(2, 3, 4, 5))
            sizes[m.group(1)] = (round(x1 - x0, 4), round(y1 - y0, 4))
    L = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "UNITS", "    DATABASE MICRONS 1000 ;",
         "END UNITS", "", f"MACRO {macro}", f"  FOREIGN {fl.group(1) if fl else macro} 0 0 ;", "  CLASS BLOCK ;",
         f"  SIZE {w:g} BY {h:g} ;"]
    for q in pins:
        dr, use = dirs.get(q["name"], ("INPUT", "SIGNAL"))
        rw, rh = RECT[q["layer"]]
        f = face(q["x"], q["y"], w, h)
        if q["name"] in sizes:
            sw, sh = sizes[q["name"]]
            # keep the declared rectangle only when the pin centre sits half its depth from the edge (as declared)
            depth = sh if f in "SN" else sw
            off = q["y"] if f == "S" else (h - q["y"]) if f == "N" else q["x"] if f == "W" else (w - q["x"])
            if abs(off - depth / 2) < 1e-3:
                rw, rh = sw, sh
        if f in "SN":
            x0, x1 = q["x"] - rw / 2, q["x"] + rw / 2
            y0, y1 = (0.0, rh) if f == "S" else (h - rh, h)
            if q["name"] == "clk" and f == "S" and q["y"] > 0.1:
                x0, x1, y0, y1 = q["x"] - 0.024, q["x"] + 0.024, 0.0, 0.48
        else:
            y0, y1 = q["y"] - rh / 2, q["y"] + rh / 2
            x0, x1 = (0.0, rw) if f == "W" else (w - rw, w)
        L += [f"  PIN {q['name']}", f"    DIRECTION {dr} ;", f"    USE {use} ;", "    PORT", f"      LAYER {q['layer']} ;",
              f"        RECT  {x0:.4f} {y0:.4f} {x1:.4f} {y1:.4f} ;", "    END", f"  END {q['name']}"]
    L += [f"END {macro}", "END LIBRARY", ""]
    Path(lef_out).write_text("\n".join(L))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pins", required=True)
    ap.add_argument("--old", nargs=2, type=float, required=True)
    ap.add_argument("--new", nargs=2, type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--plan")
    ap.add_argument("--plan-out")
    ap.add_argument("--module")
    ap.add_argument("--pins-rel", help="plan pins_file value of the new table (relative to physical/die_plan/s81)")
    ap.add_argument("--old-pins-rel")
    ap.add_argument("--strap-guard", action="store_true")
    ap.add_argument("--subset-of", help="take positions from this already re-formed table (master = plan pins minus removed ports)")
    ap.add_argument("--lef-in")
    ap.add_argument("--lef-out")
    ap.add_argument("--lef-rel", help="lef value written into the new pins json (repo-relative)")
    a = ap.parse_args()
    (W, H), (W2, H2) = a.old, a.new
    d = json.load(open(a.pins))
    groups = {}
    for q in d["pins"]:
        f = face(q["x"], q["y"], W, H)
        groups.setdefault((f, q["layer"]), []).append(q)
    moved_strap = 0
    out = []
    for (f, layer), qs in groups.items():
        ax = f in "SN"
        key = (lambda q: q["x"]) if ax else (lambda q: q["y"])
        qs.sort(key=key)
        sc = (W2 / W) if ax else (H2 / H)
        lim = (W2 if ax else H2) - 0.3
        prev = -1e9
        for q in qs:
            t = snap(key(q) * sc, layer)
            t = max(t, snap(prev + MIN_PITCH[layer], layer, up=True)) if prev > -1e8 else t
            if q["name"] in ("clk",) or not a.strap_guard or layer != "M5":
                pass
            else:
                n0 = t
                while on_strap(t, ax):
                    t = round(t + TRACK[layer][1], 4)
                moved_strap += t != n0
            if t > lim:
                raise SystemExit(f"face {f} {layer} overflow at {q['name']} {t} > {lim}")
            prev = t
            n = dict(q)
            if ax:
                n["x"] = t
                if f == "N": n["y"] = round(q["y"] - H + H2, 4)
            else:
                n["y"] = t
                if f == "E": n["x"] = round(q["x"] - W + W2, 4)
            out.append(n)
    if a.subset_of:
        pos = {q["name"]: q for q in json.load(open(a.subset_of))["pins"]}
        out = [dict(pos[q["name"]]) for q in d["pins"]]
    order = {q["name"]: i for i, q in enumerate(d["pins"])}
    out.sort(key=lambda q: order[q["name"]])
    nd = dict(d, pins=out)
    nd["source"] = (f"S81-RF1 RE-FORM (DIE-S81-51/RF-A 2026-11-03, reform_shape.py): outline {W}x{H} -> {W2}x{H2}; "
                    f"faces/order kept, along-face scaled + track-snapped, strap_guard={a.strap_guard} "
                    f"({moved_strap} M5 pins moved off strap pairs); from {Path(a.pins).name}")
    nd.pop("pinhash", None)
    if a.lef_out:
        write_contract_lef(a.lef_in, a.lef_out, d["module"], out, W2, H2)
        if a.lef_rel: nd["lef"] = a.lef_rel
    Path(a.out).write_text(json.dumps(nd, indent=1) + "\n")
    print(json.dumps({"pins": len(out), "moved_strap": moved_strap, "faces": {f"{k[0]}/{k[1]}": len(v) for k, v in groups.items()}}))
    if a.plan:
        p = json.load(open(a.plan))
        n = 0
        for t, v in p["partition_types"].items():
            for h in v.get("hard_cores", []):
                if h["module"] == a.module and (a.old_pins_rel is None or h.get("pins_file") == a.old_pins_rel):
                    h["outline_um"] = [W2, H2]
                    if a.pins_rel: h["pins_file"] = a.pins_rel
                    if a.lef_rel: h["lef"] = a.lef_rel
                    n += 1
        Path(a.plan_out).write_text(json.dumps(p, indent=1) + "\n")
        print(f"plan rows changed {n}")


if __name__ == "__main__":
    main()
