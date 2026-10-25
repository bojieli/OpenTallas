#!/usr/bin/env python3
"""PATH-QC-NK2 10-25 A0 v10 (NK, R6): every LSL fp1 clock pin and the bottom ROM-leaf pair on CORE-ONLY taps at their
clock pins (the v9 node treatment), plus 3 flop taps that re-pitch the over-long flop trees.  Structural, CTS/pin only.

GEOM-REVIEW-2 2026-10-25 10:06 [PATH-QC-NK-R5] FAIL (R5 = v9, post-CTS FF -57.00 / 1807):
  (a) XTAP 418: ck_t24 carries the LSL sl3 clock pin, CTS balances its flops to the macro branch -> late cluster
      x 305-330 / y 689-742 (r5 sinks: 360 of 1445 > mean+15) captures from ck_t39;
  (b) trees > 290 TT: ck_t6 (LSL sl2 + W pin-flop column top, 255 sinks at x 4-13 / y 1052-1103, 75 um from the tap),
      ck_t24, ck_t7/ck_t8 (ROM leaf rb0 c0/c1 pins 93/128 um from their taps through the centre channel), ck_t18
      (957 sinks, E strip x 440-455 = 716 of them, tap at x 366);
  (c) the W input column is split over ck_t28/ck_t35/ck_t6.
v10 taps (pins tcl = v9 + the moves/adds below; every other pin byte-identical):
  core-only (OT_CORE_ONLY_TAPS, no flop is ever split onto them; tap_balance balances them on pin + OT_CORE_LAT):
    LSL sl0..sl7 -> ck_t1, ck_t3 (flop-free v9 grid taps, moved) and new ck_t42..ck_t47; ROM leaf rb0c0/rb0c1 -> new
    ck_t48/ck_t49; node stays on ck_t2.  Each site = the core clock pin, 6 um outside the macro edge the pin is on
    (past the 5.4 um halo), on the M7 lattice.
  flop taps (new): ck_t50 W pin-flop column top (x 16.912 like ck_t28/ck_t35), ck_t51 ck_t24 east strip centroid,
    ck_t52 E strip of ck_t18 (x 440.656 like ck_t21/ck_t29).
RTL: ports ck_t42..ck_t52 under OT_A0_CK_TAPS53 (no RTL loads, as every tap port).

    gen_a0c10_core_clock.py SRC_ROOT OUTDIR
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1]); OUT = Path(sys.argv[2])
SPEC = SRC / "physical/ref_tile/qfd_tile_nk_a0cv9/spec.json"
PINS9 = SRC / "tools/qwen_romleaf/a0core/qfd_tile_nk_a0c9_pins.tcl"
TAPS9 = SRC / "tools/qwen_romleaf/a0core/a0c9_nk_core_taps.txt"
PREFIX = "u_ot_pr_core."
MEAN_TT = {"ot_qwen_tile_romleaf": 206.9, "ot_qwen_tile_lsl_fp1": 165.7, "ot_qwen_tile_node": 245.9}
M7_X0, M7_P = 0.016, 0.064
LSL_PORTS = ["ck_t1", "ck_t3", "ck_t42", "ck_t43", "ck_t44", "ck_t45", "ck_t46", "ck_t47"]   # sl0..sl7
LEAF_PORTS = {"g_rb[0].g_single.g_col[0].u_leaf": "ck_t48", "g_rb[0].g_single.g_col[1].u_leaf": "ck_t49"}
FLOP_ADD = {"ck_t50": (16.912, 1078.0, "W pin-flop column top (from ck_t6: 255 sinks x 4-13 / y 1052-1103)"),
            "ck_t51": (387.0, 664.0, "ck_t24 east strip (476 sinks, centroid 387,664)"),
            "ck_t52": (440.656, 523.5, "ck_t18 E strip (716 sinks, centroid 444,524)")}


def lat(x):
    return round((x - M7_X0) / M7_P) * M7_P + M7_X0


def lef(lef_path):
    t = lef_path.read_text()
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t).groups())
    blk = re.search(r"PIN clk\b(.*?)END clk", t, re.S).group(1)
    r = list(map(float, re.search(r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", blk).groups()))
    return w, h, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def main():
    spec = json.loads(SPEC.read_text())
    sites, rows = {}, []
    lsl_i = 0
    node_line = None
    for c in spec["children"]:
        view = SRC / c["view"]; cell = view.name
        w, h, px, py = lef(view / f"{cell}.lef")
        ox, oy = c["at"]; o = c.get("orient", "R0")
        x = ox + (w - px if o == "MY" else px); y = oy + (h - py if o == "MX" else py)
        inst = "{" + PREFIX + c["inst"].replace("[", "\\[").replace("]", "\\]") + "}"
        if cell == "ot_qwen_tile_node":
            rows.append((inst, cell, "ck_t2")); continue
        port = None
        if cell == "ot_qwen_tile_lsl_fp1":
            k = int(re.search(r"g_sl\[(\d+)\]", c["inst"]).group(1)); port = LSL_PORTS[k]; lsl_i += 1
        else:
            for suf, p in LEAF_PORTS.items():
                if c["inst"].endswith(suf):
                    port = p
        if port is None:   # other ROM leaves: v9 assignment (flop tap nearest the clock pin), unchanged
            v9 = {l.split()[1]: l.split()[0] for l in TAPS9.read_text().splitlines() if l and not l.startswith("#")}
            rows.append((inst, cell, v9[inst])); continue
        west = (x - ox) < w / 2
        tx = lat(x - 6.0 if west else x + 6.0); ty = round(y / 0.016) * 0.016
        sites[port] = (tx, ty, f"core-only {cell} {c['inst']} clk pin ({x:.3f},{y:.3f})")
        rows.append((inst, cell, port))
    assert lsl_i == 8 and len(sites) == 10, (lsl_i, sites)
    for p, (x, y, why) in FLOP_ADD.items():
        sites[p] = (lat(x), round(y / 0.016) * 0.016, "flop tap: " + why)
    out, seen = [], set()
    for l in PINS9.read_text().splitlines():
        m = re.search(r"-pin_name \{(ck_t\d+)\} ", l)
        if m and m.group(1) in sites:
            p = m.group(1); x, y, why = sites[p]; seen.add(p)
            old = re.search(r"-location \{([\d.]+ [\d.]+)\}", l).group(1)
            l = re.sub(r"-location \{[\d.]+ [\d.]+\}", f"-location {{{x:.3f} {y:.3f}}}", l)
            l = re.sub(r";#.*$", f";# {why}, moved from {{{old}}} (PATH-QC-NK2 A0 v10)", l)
        out.append(l)
        if m and m.group(1) == "ck_t41":
            for p in sorted((p for p in sites if p not in ("ck_t1", "ck_t3")), key=lambda s: int(s[4:])):
                x, y, why = sites[p]; seen.add(p)
                out.append(f"place_pin -pin_name {{{p}}} -layer M7 -location {{{x:.3f} {y:.3f}}} -pin_size {{0.032 0.768}}"
                           f"   ;# {why} (added, PATH-QC-NK2 A0 v10)")
    assert seen == set(sites), set(sites) - seen
    out[0:0] = ["# PATH-QC-NK2 10-25 A0 v10 (NK R6) = qfd_tile_nk_a0c9_pins.tcl with ck_t1/ck_t3 moved and ck_t42..ck_t52 added "
                "(tools/qwen_romleaf/a0core/gen_a0c10_core_clock.py).  All other pins byte-identical."]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qfd_tile_nk_a0c10_pins.tcl").write_text("\n".join(out) + "\n")
    hdr = "# generated by tools/qwen_romleaf/a0core/gen_a0c10_core_clock.py (PATH-QC-NK2 10-25)\n"
    (OUT / "a0c10_nk_core_taps.txt").write_text(hdr + "# port inst pin\n" + "".join(f"{t} {i} clk\n" for i, c, t in rows))
    (OUT / "a0c10_nk_core_lat.txt").write_text(hdr + "# inst pin internal_latency_ps(TT pin-register mean) tap\n" + "".join(
        f"{i} clk {MEAN_TT[c]} {t}\n" for i, c, t in rows))
    core_only = ["ck_t2"] + [p for p in sites if p not in FLOP_ADD]
    (OUT / "a0c10_nk_core_clock.json").write_text(json.dumps({
        "core_only_taps": core_only,
        "sites": {p: {"xy": [round(v[0], 3), round(v[1], 3)], "why": v[2]} for p, v in sites.items()},
        "cores": [{"inst": i, "cell": c, "tap": t} for i, c, t in rows]}, indent=1) + "\n")
    print("OT_CORE_ONLY_TAPS=" + " ".join(core_only))
    for p, v in sorted(sites.items(), key=lambda s: int(s[0][4:])):
        print(f"{p:7s} ({v[0]:8.3f},{v[1]:8.3f}) {v[2]}")


main()
