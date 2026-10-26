#!/usr/bin/env python3
"""ECTL A/B row-bus + rs pin grant (Q-KVSYS-DIE 2026-10-16 ECTL A pin grant): exact place_pin files for the two
SRAM leaves of the KV-die row-engine control cell, plus the ectl parent face map.

Grant (KV die lead Q-KVSYS-DIE, 2026-10-16; same outlines, same RTL, 0 cycles):
  1. each 256-bit half of the 512-bit row buses t0_row (S) / t1_row (N) sits over its own SRAM: bits [255:0] over
     u_rows.g_macro[0] (x 22.464..117.288), bits [511:256] over g_macro[1] (x 137.592..232.416).  The ring stores
     row bits [m*256 +: 256] in macro m (ot_qkd_static_row_ring), so each half leaves the tile above the SRAM that
     holds it (VIS-ROM QKV-02: both halves on the right half of N/S = 48 % of the face, left-SRAM bits ran 120+ um
     along the macro edges);
  2. ECTL A's 1,025-bit rs bus on W over M4 + M6 (even bits M4, odd bits M6), <= 8 pins/um/layer (was 8.6 /um M4
     only); M6 face pins need the die lead's layer_cap_grant (tools/ref_tile/README.md layer contract);
  3. A and B carry the same row-pin map (same bit order, same tile-local x, same faces), so in the parent
     (A | B | C abutting, all R0) the A and B row columns repeat at the 254.88-um leaf pitch; every row bus is
     bit-ascending in x like the CLOSED leaf C h13 t0_q / t1_q (kept unchanged).
Every other pin is copied byte-exact (layer, centre, size) from the leaf's CLOSED view LEF.

  python3 tools/qwen_kv_die/ectl_pin_grant_1016.py [--out results/arch/qwen_split_1014/ectl_pin_grant_1016]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRANT = "Q-KVSYS-DIE 2026-10-16 ECTL A pin grant"
LEAF_W, LEAF_H = 254.88, 129.6
SLOT_X = {"A": 0.0, "B": 254.88, "C": 509.76}          # parent qkd_ectl3 (A | B | C), all R0
VIEWS = {
    "A": ("qkd_ectl_a_tp8_epoch_direct", "physical/ref_tile/qkd_ectl_a_tp8_epoch_direct_h5/views/qkd_ectl_a_tp8_epoch_direct/qkd_ectl_a_tp8_epoch_direct.lef"),
    "B": ("qkd_ectl_b_tp8_direct", "physical/ref_tile/qkd_ectl_b_tp8_direct_h5/views/qkd_ectl_b_tp8_direct/qkd_ectl_b_tp8_direct.lef"),
    "C": ("qkd_ectl_c_tp8_direct", "physical/ref_tile/qkd_ectl_c_tp8_direct_h13/views/qkd_ectl_c_tp8_direct/qkd_ectl_c_tp8_direct.lef"),
}
SRAM_X = ((22.464, 117.288), (137.592, 232.416))       # spec macros at x 22.464 / 137.592, LEF width 94.824
ROW_INSET = 1.0                                         # keep the end pins 1 um inside the SRAM's x span
RS_SPAN = (6.0, 124.0)                                  # A W face rs range (unchanged)
TRACK = {"M4": (0.012, 0.048), "M5": (0.012, 0.048), "M6": (0.016, 0.064)}   # asap7 make_tracks (y for M4/M6, x for M5)
MIN_TRACKS = 2                                          # PIN_MIN_TRACKS of the ref_tile flow
SIZE = {"M4": (0.084, 0.024), "M6": (0.084, 0.032), "M5": (0.024, 0.084)}  # (x, y) = closed-view pin rects; M6 0.032 wide
# M6 PG stripes of a layer_cap M6 leaf (tools/ref_tile/ref_tile.py gen_pdn / pg_stripe_spread): horizontal, width 0.288,
# VDD at CORE_MARGIN 2.16 + 2.0, VSS +0.384, pitch 10.8.  M6 face pins keep >= 0.2 um off them.
PG6 = dict(first=2.16 + 2.0, step=0.384, width=0.288, pitch=10.8, clear=0.2)
MAX_PER_UM_LAYER = 8.0


def lef_pins(path):
    text = (ROOT / path).read_text()
    out = {}
    for m in re.finditer(r"(?ms)^\s*PIN\s+(\S+)\s*$(.*?)^\s*END\s+\1\s*$", text):
        r = re.search(r"LAYER\s+(\S+)\s*;\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", m.group(2))
        use = re.search(r"USE\s+(\w+)", m.group(2))
        if not r or (use and use.group(1) in ("POWER", "GROUND")):
            continue
        layer, x0, y0, x1, y1 = r.group(1), *map(float, r.groups()[1:])
        out[m.group(1)] = dict(layer=layer, x=round((x0 + x1) / 2, 4), y=round((y0 + y1) / 2, 4),
                               w=round(x1 - x0, 4), h=round(y1 - y0, 4))
    return out


def face_of(p, W, H):
    if p["x"] < 0.2:
        return "W"
    if p["x"] > W - 0.2:
        return "E"
    return "S" if p["y"] < 0.2 else "N"


def snap(v, layer, up=True):
    off, pitch = TRACK[layer]
    k = (v - off) / pitch
    k = int(k) + (1 if up and k != int(k) else 0)
    return round(off + k * pitch, 4)


def spread(n, lo, hi, layer, allowed=None):
    """n track-aligned centres, bit-ascending, evenly over [lo, hi] (allowed: predicate on a centre)"""
    off, pitch = TRACK[layer]
    tracks = [round(off + k * pitch, 4) for k in range(int((lo - off) / pitch), int((hi - off) / pitch) + 2)]
    tracks = [t for t in tracks if lo - 1e-9 <= t <= hi + 1e-9 and (allowed is None or allowed(t))]
    if len(tracks) < n:
        raise SystemExit(f"{n} pins do not fit {lo}..{hi} on {layer}")
    pos = [tracks[round(i * (len(tracks) - 1) / (n - 1))] for i in range(n)] if n > 1 else [tracks[len(tracks) // 2]]
    gap = min(b - a for a, b in zip(pos, pos[1:])) if n > 1 else 9
    if gap < MIN_TRACKS * pitch - 1e-9:
        raise SystemExit(f"{layer} pins closer than {MIN_TRACKS} tracks ({gap})")
    return pos


def off_pg6(y):
    d = (y - PG6["first"]) % PG6["pitch"]
    band = (-PG6["clear"] - 0.016, PG6["step"] + PG6["width"] + PG6["clear"] + 0.016)
    return not (band[0] <= d <= band[1] or band[0] <= d - PG6["pitch"] <= band[1])


def row_map():
    """{bit: x} of a 512-bit row bus: [255:0] over SRAM 0, [511:256] over SRAM 1, bit-ascending in x"""
    xs = []
    for lo, hi in SRAM_X:
        xs += spread(256, lo + ROW_INSET, hi - ROW_INSET, "M5")
    return {b: x for b, x in enumerate(xs)}


def plan(leaf):
    cell, lef = VIEWS[leaf]
    closed = lef_pins(lef)
    pins = {}
    for n, p in closed.items():                       # untouched ports: the closed view's exact rect
        pins[n] = dict(p, face=face_of(p, LEAF_W, LEAF_H), src="closed")
    rows = row_map()
    for bus, face, y in (("t0_row", "S", 0.0), ("t1_row", "N", LEAF_H)):
        for b, x in rows.items():
            w, h = SIZE["M5"]
            pins[f"{bus}[{b}]"] = dict(layer="M5", x=x, y=round(y + (h / 2 if face == "S" else -h / 2), 4), w=w, h=h,
                                       face=face, src="grant(1,3)")
    if leaf == "A":
        n = 1025
        even = spread((n + 1) // 2, RS_SPAN[0], RS_SPAN[1], "M4")
        odd = spread(n // 2, RS_SPAN[0], RS_SPAN[1], "M6", off_pg6)
        for b in range(n):
            layer, y = ("M4", even[b // 2]) if b % 2 == 0 else ("M6", odd[b // 2])
            w, h = SIZE[layer]
            pins[f"rs[{b}]"] = dict(layer=layer, x=round(w / 2, 4), y=y, w=w, h=h, face="W", src="grant(2)")
    return cell, closed, pins


def checks(leaf, closed, pins):
    out = {"same_port_set": sorted(closed) == sorted(pins)}
    by = {}
    for n, p in pins.items():
        by.setdefault((p["face"], p["layer"]), []).append((p["x"] if p["face"] in "NS" else p["y"], n))
    dens, gaps = {}, {}
    for (f, l), v in sorted(by.items()):
        v.sort()
        pitch = TRACK[l][1]
        gap = min((b[0] - a[0] for a, b in zip(v, v[1:])), default=99)
        gaps[f"{f}/{l}"] = round(gap, 4)
        if gap < MIN_TRACKS * pitch - 1e-9:
            raise SystemExit(f"{leaf}: {f}/{l} pins {gap} apart < {MIN_TRACKS} tracks")
        # densest 10-um window
        best = 0
        j = 0
        for i in range(len(v)):
            while v[i][0] - v[j][0] > 10.0:
                j += 1
            best = max(best, i - j + 1)
        dens[f"{f}/{l}"] = dict(pins=len(v), max_per_um_10um_window=round(best / 10.0, 2))
        if best / 10.0 > MAX_PER_UM_LAYER + 0.6 and any(pins[n]["src"] != "closed" for _, n in v):
            raise SystemExit(f"{leaf}: {f}/{l} {best / 10.0} pins/um > {MAX_PER_UM_LAYER}")
    out["face_layer_density"] = dens
    out["min_same_layer_gap_um"] = gaps
    m6 = [p for p in pins.values() if p["layer"] == "M6"]
    out["m6_pins"] = len(m6)
    out["m6_off_pg_stripes"] = all(off_pg6(p["y"]) for p in m6)
    for bus in ("t0_row", "t1_row"):
        xs = [pins[f"{bus}[{b}]"]["x"] for b in range(512)]
        out[f"{bus}_bit_ascending"] = all(a < b for a, b in zip(xs, xs[1:]))
        for h, (lo, hi) in enumerate(SRAM_X):
            seg = xs[h * 256:(h + 1) * 256]
            out[f"{bus}_half{h}_over_sram{h}"] = lo <= min(seg) and max(seg) <= hi
    return out


def tcl(cell, pins):
    lines = [f"# {cell}: exact pin plan, {GRANT} (tools/qwen_kv_die/ectl_pin_grant_1016.py). Do not edit; regenerate."]
    for n in sorted(pins, key=lambda s: (re.sub(r"\[\d+\]$", "", s), int(re.search(r"\[(\d+)\]$", s).group(1)) if "[" in s else -1)):
        p = pins[n]
        lines.append(f"place_pin -pin_name {{{n}}} -layer {p['layer']} -location {{{p['x']:.4f} {p['y']:.4f}}} "
                     f"-pin_size {{{p['w']:.3f} {p['h']:.3f}}} -force_to_die_boundary")
    return "\n".join(lines) + "\n"


def parent_map(plans):
    """t0 / t1 = {q 519 (C), c[15:4] 12 (B), b_row 512 (B), a_row 512 (A), c[3:0] 4 (B)} (qkd_ectl3_direct_s)"""
    segs = [("c_lo", "B", "t{p}_cl", 0, 4), ("a_row", "A", "t{p}_row", 0, 512), ("b_row", "B", "t{p}_row", 0, 512),
            ("c_hi", "B", "t{p}_cl", 4, 12), ("q", "C", "t{p}_q", 0, 519)]
    out = {}
    for p, face in (("0", "S"), ("1", "N")):
        bit, rows = 0, []
        for name, leaf, port, lo, n in segs:
            pp = plans[leaf][port.format(p=p)] if isinstance(plans[leaf], dict) and port.format(p=p) in plans[leaf] else None
            xs = [plans[leaf][f"{port.format(p=p)}[{lo + i}]"]["x"] + SLOT_X[leaf] for i in range(n)]
            rows.append(dict(segment=name, leaf=leaf, leaf_port=f"{port.format(p=p)}[{lo + n - 1}:{lo}]",
                             parent_bits=f"t{p}[{bit + n - 1}:{bit}]", face=face, layer="M5",
                             parent_x_um=[round(min(xs), 3), round(max(xs), 3)], ascending=all(a < b for a, b in zip(xs, xs[1:]))))
            bit += n
        assert bit == 1559
        out[f"t{p}"] = rows
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="results/arch/qwen_split_1014/ectl_pin_grant_1016")
    a = ap.parse_args()
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    plans, report = {}, {"schema": "opentallas.qwen.ectl_pin_grant.v1", "grant": GRANT,
                         "scope": "same outline, same RTL, 0 cycles; pin geometry only", "leaves": {}}
    for leaf in ("A", "B"):
        cell, closed, pins = plan(leaf)
        chk = checks(leaf, closed, pins)
        if not all(v for k, v in chk.items() if isinstance(v, bool)):
            raise SystemExit(f"{leaf}: check failed {chk}")
        (out / f"{cell}.tcl").write_text(tcl(cell, pins))
        moved = sorted({re.sub(r"\[\d+\]$", "", n) for n, p in pins.items() if p["src"] != "closed"})
        report["leaves"][leaf] = dict(cell=cell, io_tcl=f"{a.out}/{cell}.tcl", closed_view=VIEWS[leaf][1],
                                      moved_ports=moved, checks=chk)
        plans[leaf] = pins
    plans["C"] = {n: dict(p, face=face_of(p, 138.24, LEAF_H)) for n, p in lef_pins(VIEWS["C"][1]).items()}
    # A / B row maps identical (tile-local) -> columns repeat at the leaf pitch in the parent
    report["a_b_row_maps_identical"] = all(plans["A"][f"{b}[{i}]"]["x"] == plans["B"][f"{b}[{i}]"]["x"]
                                           for b in ("t0_row", "t1_row") for i in range(512))
    report["parent_face_map"] = dict(parent="qkd_ectl3_direct_s / qkd_ectl3_epoch_direct_s (647.976 x 129.576)",
                                     leaf_origin_x=SLOT_X, orient="R0", **parent_map(plans))
    (out / "pin_grant.json").write_text(json.dumps(report, indent=1) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "parent_face_map"}, indent=1)[:4000])
    for t in ("t0", "t1"):
        for r in report["parent_face_map"][t]:
            print(t, r["segment"], r["parent_bits"], r["leaf_port"], r["parent_x_um"], r["ascending"])


if __name__ == "__main__":
    sys.exit(main())
