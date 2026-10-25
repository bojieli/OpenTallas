#!/usr/bin/env python3
"""PATH-QC-NL 10-25 A0 NL v10 core clock = the NL twin of gen_a0c10_core_clock.py (NK R6, GEOM [PATH-QC-NK-R6] PASS-COND).

NL has no node; its 8 LSL fp1 + 10 ROM leaves are the hard cores.  Same structural form as NK v9/v10 (no hold buffers):
  * core-only taps (OT_CORE_ONLY_TAPS: no flop is ever split onto them; tap_balance balances them on pin + OT_CORE_LAT):
    LSL sl0..sl7 and the bottom ROM-leaf pair rb0c0/rb0c1 on taps AT their clock pins (6 um outside the macro edge the
    pin is on, past the 5.4 um halo, on the M7 lattice).  Ports: the flop-free grid taps ck_t1/ck_t2/ck_t3 (over the ROM
    bodies / ROM-row gap, as in NK r4) are moved, plus new ck_t41..ck_t47 (RTL OT_A0_CK_TAPS48, no loads).
  * every other ROM leaf: the flop tap nearest its CLOCK PIN (OT_CORE_TAPS; v9 rule, not the instance origin).
  * OT_CORE_LAT = TT pin-register means (romleaf 206.9 / lsl 165.7; results/core_clock_contract_0719).
The NK R6 re-pitch flop taps (ck_t50..52) were measured on the NK placement; NL gets its own only from an NL CTS.

    gen_a0c10_nl_core_clock.py SRC_ROOT SPEC OUTDIR
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1]); SPEC = Path(sys.argv[2]); OUT = Path(sys.argv[3])
PINS8 = SRC / "tools/qwen_romleaf/a0core/qfd_tile_nl_a0c8_pins.tcl"
PREFIX = "u_ot_pr_core."
MEAN_TT = {"ot_qwen_tile_romleaf": 206.9, "ot_qwen_tile_lsl_fp1": 165.7}
M7_X0, M7_P = 0.016, 0.064
LSL_PORTS = ["ck_t1", "ck_t3", "ck_t41", "ck_t42", "ck_t43", "ck_t44", "ck_t45", "ck_t46"]   # sl0..sl7
LEAF_PORTS = {"g_rb[0].g_single.g_col[0].u_leaf": "ck_t2", "g_rb[0].g_single.g_col[1].u_leaf": "ck_t47"}
MOVED = {"ck_t1", "ck_t2", "ck_t3"}
NO_FLOPS = {"ck"} | MOVED          # flop-free grid taps: never a core's flop tap


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
    pins = PINS8.read_text().splitlines()
    taps = {}
    for l in pins:
        m = re.search(r"-pin_name \{(ck(?:_t\d+)?)\} -layer M7 -location \{([\d.]+) ([\d.]+)\}", l)
        if m:
            taps[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    sites, rows = {}, []
    for c in spec["children"]:
        view = SRC / c["view"]; cell = view.name
        w, h, px, py = lef(view / f"{cell}.lef")
        ox, oy = c["at"]; o = c.get("orient", "R0")
        if o not in ("R0", "MY", "MX"):
            raise SystemExit(f"orient {o}")
        x = ox + (w - px if o == "MY" else px); y = oy + (h - py if o == "MX" else py)
        inst = "{" + PREFIX + c["inst"].replace("[", "\\[").replace("]", "\\]") + "}"
        port = None
        if cell == "ot_qwen_tile_lsl_fp1":
            port = LSL_PORTS[int(re.search(r"g_sl\[(\d+)\]", c["inst"]).group(1))]
        else:
            for suf, p in LEAF_PORTS.items():
                if c["inst"].endswith(suf):
                    port = p
        if port is None:
            d, t = min((abs(x - tx) + abs(y - ty), t) for t, (tx, ty) in taps.items() if t not in NO_FLOPS)
            rows.append((inst, cell, t, x, y, d)); continue
        west = (x - ox) < w / 2
        tx = lat(x - 6.0 if west else x + 6.0); ty = round(y / 0.016) * 0.016
        tag = ".".join(c["inst"].split(".")[-4:-1]) if "g_rb" in c["inst"] else re.search(r"g_sl\[\d\]", c["inst"]).group(0)
        sites[port] = (tx, ty, f"core-only {cell} {tag} clk pin ({x:.3f},{y:.3f})")
        rows.append((inst, cell, port, x, y, abs(tx - x) + abs(ty - y)))
    assert len(sites) == 10, sites
    out, seen = [], set()
    for l in pins:
        m = re.search(r"-pin_name \{(ck_t\d+)\} ", l)
        if m and m.group(1) in sites:
            p = m.group(1); x, y, why = sites[p]; seen.add(p)
            old = re.search(r"-location \{([\d.]+ [\d.]+)\}", l).group(1)
            l = re.sub(r"-location \{[\d.]+ [\d.]+\}", f"-location {{{x:.3f} {y:.3f}}}", l)
            l = re.sub(r";#.*$", f";# {why}, moved from {{{old}}} (PATH-QC-NL A0 NL v10)", l)
        out.append(l)
        if m and m.group(1) == "ck_t40":
            for p in sorted((p for p in sites if p not in MOVED), key=lambda s: int(s[4:])):
                x, y, why = sites[p]; seen.add(p)
                out.append(f"place_pin -pin_name {{{p}}} -layer M7 -location {{{x:.3f} {y:.3f}}} -pin_size {{0.032 0.768}}"
                           f"   ;# {why} (added, PATH-QC-NL A0 NL v10)")
    assert seen == set(sites), set(sites) - seen
    out[0:0] = ["# PATH-QC-NL 10-25 A0 NL v10 = qfd_tile_nl_a0c8_pins.tcl with ck_t1/ck_t2/ck_t3 moved to core clock pins and "
                "ck_t41..ck_t47 added (tools/qwen_romleaf/a0core/gen_a0c10_nl_core_clock.py).  All other pins byte-identical."]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "qfd_tile_nl_a0c10_pins.tcl").write_text("\n".join(out) + "\n")
    hdr = "# generated by tools/qwen_romleaf/a0core/gen_a0c10_nl_core_clock.py (PATH-QC-NL 10-25)\n"
    (OUT / "a0c10_nl_core_taps.txt").write_text(hdr + "# port inst pin\n" + "".join(f"{r[2]} {r[0]} clk\n" for r in rows))
    (OUT / "a0c10_nl_core_lat.txt").write_text(hdr + "# inst pin internal_latency_ps(TT pin-register mean) tap\n" + "".join(
        f"{r[0]} clk {MEAN_TT[r[1]]} {r[2]}\n" for r in rows))
    core_only = sorted(sites, key=lambda s: int(s[4:]))
    (OUT / "a0c10_nl_core_clock.json").write_text(json.dumps({
        "core_only_taps": core_only,
        "sites": {p: {"xy": [round(v[0], 3), round(v[1], 3)], "why": v[2]} for p, v in sites.items()},
        "cores": [{"inst": r[0], "cell": r[1], "tap": r[2], "pin": [round(r[3], 3), round(r[4], 3)], "dist_um": round(r[5], 1)}
                  for r in rows]}, indent=1) + "\n")
    print("OT_CORE_ONLY_TAPS=" + ",".join(core_only))
    for r in rows:
        print(f"{r[2]:7s} {r[1]:22s} pin ({r[3]:6.1f},{r[4]:6.1f}) d {r[5]:6.1f}  {r[0]}")


main()
