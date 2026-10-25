#!/usr/bin/env python3
"""PATH-QC-NK 10-25 A0 v9 (NK) core clock: hard-child clock pins get their own clock-tap assignment.

Finding (nk_r4 autopilot 8fffd9b75f35, FF -316.66 / 2066; rebuild path-qc-nk/r5d): clock_taps.tcl assigns every sink to
the tap nearest its instance ORIGIN.  For a 173 x 110 um ROM leaf that is the lower-left corner, ~170 um from its clock
pin, so the W leaves rb[0..1] col0 landed on the flop-free grid tap `ck` (over the leaf bodies).  tap_balance.tcl then
padded that core-only tap like a flop tap to 250 ps (no OT_CORE_LAT table in the A0 kits), so the leaf's internal
registers sit at 259 + 207 = 466 ps TT: ROM reset hold -94.64 (g_lrr launch 179.8 vs leaf clk 201.2 + lib hold 106.7).
The node (internal 246 TT mean / 268 ETM max) shared flop tap ck_t28 131 ps from its pin; TritonCTS balanced that
tap's 906 registers (the W input pin flops) to node pin + ETM insertion = 396 ps (tap target 250).

Fix (industry practice: latency-aware sink balancing; macro clock pins at their own insertion):
  * core taps (OT_CORE_TAPS, existing CP2 mechanism): every ROM leaf / LSL clock pin goes to the flop tap nearest its
    CLOCK PIN (TritonCTS builds the macro branch from that tap root and balances the registers to macro insertion,
    as it already did correctly for the 13 cores whose origin happened to be near their pin);
  * the node, whose internal latency alone (246 TT) fills the 250 target, gets a CORE-ONLY tap next to its pin:
    tap ck_t2 (flop-free grid tap over the W ROM column, 1 core sink in r4) moves to the node clock pin and is listed
    in OT_CORE_ONLY_TAPS (clock_taps.tcl: no flop is split onto it), so no register is skewed by the node;
  * OT_CORE_LAT (measured pin-register MEAN, TT; results/core_clock_contract_0719, NOT the ETM max): tap_balance.tcl
    measures flop statistics without core pins and balances core-only taps on effective arrival (pin + internal).

    gen_a0c9_core_clock.py SRC_ROOT OUTDIR
"""
import json
import re
import sys
from pathlib import Path

SRC = Path(sys.argv[1]); OUT = Path(sys.argv[2])
SPEC = SRC / "physical/ref_tile/qfd_tile_nk_a0cv8/spec.json"
PINS8 = SRC / "tools/qwen_romleaf/a0core/qfd_tile_nk_a0c8_pins.tcl"
PREFIX = "u_ot_pr_core."
# TT pin-register means (codex/core-clock-contract0719 485897d27 results/core_clock_contract_0719, diagnostic basis)
MEAN_TT = {"ot_qwen_tile_romleaf": 206.9, "ot_qwen_tile_lsl_fp1": 165.7, "ot_qwen_tile_node": 245.9}
NODE_TAP = "ck_t2"
# flop-free in r4 (grid taps over the ROM leaf bodies): never chosen as a core's flop tap
NO_FLOPS = {"ck", "ck_t1", "ck_t3", NODE_TAP}
M7_X0, M7_P = 0.016, 0.064


def lef_clk(lef):
    t = lef.read_text()
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t).groups())
    blk = re.search(r"PIN clk\b(.*?)END clk", t, re.S).group(1)
    r = list(map(float, re.search(r"RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)", blk).groups()))
    return w, h, (r[0] + r[2]) / 2, (r[1] + r[3]) / 2


def main():
    spec = json.loads(SPEC.read_text())
    taps = {}
    pins_txt = PINS8.read_text().splitlines()
    for l in pins_txt:
        m = re.search(r"-pin_name \{(ck(?:_t\d+)?)\} -layer M7 -location \{([\d.]+) ([\d.]+)\}", l)
        if m:
            taps[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    rows, node = [], None
    for c in spec["children"]:
        view = SRC / c["view"]
        cell = view.name
        w, h, px, py = lef_clk(view / f"{cell}.lef")
        ox, oy = c["at"]
        o = c.get("orient", "R0")
        if o == "R0":
            x, y = ox + px, oy + py
        elif o == "MY":
            x, y = ox + (w - px), oy + py
        elif o == "MX":
            x, y = ox + px, oy + (h - py)
        else:
            raise SystemExit(f"orient {o} unsupported")
        # ODB names keep the hierarchy-bracket escapes; braced so the Tcl list parse (lassign/lindex) keeps them
        inst = "{" + PREFIX + c["inst"].replace("[", "\\[").replace("]", "\\]") + "}"
        if cell == "ot_qwen_tile_node":
            node = (inst, x, y)
            rows.append((inst, cell, NODE_TAP, x, y, 0.0))
            continue
        best = min((abs(x - tx) + abs(y - ty), t) for t, (tx, ty) in taps.items() if t not in NO_FLOPS)
        rows.append((inst, cell, best[1], x, y, best[0]))
    assert node, "no node child"
    # ck_t2 -> next to the node clock pin, in the channel past the 5.4 um halo, on the M7 track lattice
    nx = round((node[1] + 6.0 - M7_X0) / M7_P) * M7_P + M7_X0
    ny = round(node[2] / 0.016) * 0.016
    OUT.mkdir(parents=True, exist_ok=True)
    out = []
    moved = False
    for l in pins_txt:
        if re.search(r"-pin_name \{%s\} " % NODE_TAP, l):
            old = re.search(r"-location \{([\d.]+ [\d.]+)\}", l).group(1)
            l = re.sub(r"-location \{[\d.]+ [\d.]+\}", f"-location {{{nx:.3f} {ny:.3f}}}", l)
            l = re.sub(r";#.*$", f";# core-only node tap, moved from {{{old}}} (PATH-QC-NK A0 v9)", l)
            moved = True
        out.append(l)
    assert moved
    out.insert(0, "# PATH-QC-NK 10-25 A0 v9 (NK) = qfd_tile_nk_a0c8_pins.tcl with ck_t2 moved to the node clock pin "
                  "(core-only tap; tools/qwen_romleaf/a0core/gen_a0c9_core_clock.py).  All other pins byte-identical.")
    (OUT / "qfd_tile_nk_a0c9_pins.tcl").write_text("\n".join(out) + "\n")
    hdr = "# generated by tools/qwen_romleaf/a0core/gen_a0c9_core_clock.py (PATH-QC-NK 10-25)\n"
    (OUT / "a0c9_nk_core_taps.txt").write_text(hdr + "# port inst pin   (core clock pin -> tap; distance um)\n" + "".join(
        f"{t} {i} clk   ;# {d:.1f} um, pin ({x:.1f},{y:.1f}) {c}\n".replace("   ;#", "\n#")
        if False else f"{t} {i} clk\n" for i, c, t, x, y, d in rows))
    (OUT / "a0c9_nk_core_lat.txt").write_text(hdr + "# inst pin internal_latency_ps(TT pin-register mean) tap\n" + "".join(
        f"{i} clk {MEAN_TT[c]} {t}\n" for i, c, t, x, y, d in rows))
    (OUT / "a0c9_nk_core_clock.json").write_text(json.dumps({
        "node_tap": {"port": NODE_TAP, "from": list(taps[NODE_TAP]), "to": [round(nx, 3), round(ny, 3)],
                     "node_pin": [round(node[1], 3), round(node[2], 3)]},
        "cores": [{"inst": i, "cell": c, "tap": t, "pin": [round(x, 3), round(y, 3)], "dist_um": round(d, 1),
                   "mean_tt_ps": MEAN_TT[c]} for i, c, t, x, y, d in rows]}, indent=1) + "\n")
    for r in rows:
        print(f"{r[2]:7s} {r[1]:22s} pin ({r[3]:6.1f},{r[4]:6.1f}) d {r[5]:6.1f}  {r[0]}")
    print(f"{NODE_TAP}: {taps[NODE_TAP]} -> ({nx:.3f},{ny:.3f})")


main()
