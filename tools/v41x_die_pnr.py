#!/usr/bin/env python3
"""Place-and-route cases of the adopted V4.1 layer die at the design clock (1.087 GHz, 0.92 ns), ASAP7.

Each case is a floorplan derived from the die-assembly study (docs/ARCH_V41_DIE_ASSEMBLY.md,
results/arch/v41_die_assembly.json) and run through tools/run_abi3_physical.py, so every record has the
repository's physical.json schema, source pins and acceptance verdict.

  karb_strip   ot_chip_v41x_hbm_karb (one HBM3E stack's K-port arbiter, NPC = 32) as the strip the
               die-assembly floorplan draws beside each HBM3E PHY ("KV/key streamer + staging", along the
               PHY's 12.0 mm core-facing edge).  Pins follow the floorplan: pseudo-channel p's stack-side
               (h_*, r_*) bits on the bottom edge and its bridge-side (b_*) bits on the top edge, both inside
               p's 375 um window of the PHY edge (PHY_PC_WINDOW_UM); the KV prefetch's one K channel and
               the status counters at the spine end (x = 12 mm).  The standalone attempt
               (results/physical_abi3/asap7/chip/v41x_hbm_karb/physical.json) left the 40,332 pins to the
               default placer on a 122 um square and failed PPL-0024.

    python3 tools/v41x_die_pnr.py karb_strip --print          # the run_abi3_physical argv
    OT_ORFS_NUM_CORES=8 python3 tools/v41x_die_pnr.py karb_strip --run --work /home/ubuntu/v41dpnr/work
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLOCK_NS = 0.92                    # 1.087 GHz (results/arch/v41_die_assembly.json clock_hz)
PHY_EDGE_UM = 12000.0              # HBM3E PHY core-facing edge (die assembly: 12.0 x 0.8335 mm per stack)
NPC = 32
PHY_PC_WINDOW_UM = PHY_EDGE_UM / NPC
PC_PIN_SPAN = (20.0, 195.0)        # pin sub-window inside each pseudo-channel window, um from its left end
ROW_UM = 0.27


def bits(name: str, width: int, lo: int = 0) -> list[str]:
    return [f"{name}[{i}]" for i in range(lo, lo + width)]


def pin_regex(pins: list[str]) -> str:
    """A Tcl regexp matching exactly these bus bits (grouped per bus)."""
    by_bus: dict[str, list[str]] = {}
    for p in pins:
        n, _, rest = p.partition("[")
        by_bus.setdefault(n, []).append(rest.rstrip("]"))
    alts = [f"^{n}\\[({'|'.join(ix)})\\]$" for n, ix in by_bus.items()]
    return "|".join(alts)


def karb_pc_pins(p: int, side: str, aw: int = 28, tagw: int = 16, lenw: int = 4, beatw: int = 4,
                 dw: int = 256) -> list[str]:
    """Pseudo-channel p's bits on one side of ot_chip_v41x_hbm_karb: 'b' the pooled bridge, 'h' the stack."""
    if side == "b":
        spec = [("b_v", 1), ("b_rdy", 1), ("b_addr", aw), ("b_len", lenw), ("b_tag", tagw), ("b_we", 1),
                ("b_wdata", dw), ("b_wstrb", dw // 8), ("b_wr_done", 1), ("b_rsp_v", 1), ("b_rsp_rdy", 1),
                ("b_rsp_tag", tagw), ("b_rsp_beat", beatw), ("b_rsp_data", dw)]
    else:
        spec = [("h_v", 1), ("h_rdy", 1), ("h_addr", aw), ("h_len", lenw), ("h_tag", tagw + 1), ("h_we", 1),
                ("h_wdata", dw), ("h_wstrb", dw // 8), ("h_wr_done", 1), ("r_v", 1), ("r_rdy", 1),
                ("r_tag", tagw + 1), ("r_beat", beatw), ("r_data", dw)]
    out = []
    for name, w in spec:
        out += bits(name, w, p * w)
    return out


def karb_strip(height_um: float = 30.24) -> dict:
    w, h = PHY_EDGE_UM, height_um
    m = 8 * ROW_UM
    regions = []
    for p in range(NPC):
        x0 = p * PHY_PC_WINDOW_UM
        span = f"{x0 + PC_PIN_SPAN[0]:g}-{x0 + PC_PIN_SPAN[1]:g}"
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h'))}=bottom:{span}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b'))}=top:{span}")
    k = r"^k_(v|rdy|we|wr_done|rsp_v|rsp_rdy)$|^k_(addr|len|tag|wdata|wstrb|rsp_tag|rsp_beat|rsp_data)\[\d+\]$"
    regions.append(f"{k}=top:{w - 165:g}-{w - 5:g}")
    regions.append(r"^(k_grants|b_grants|contended)\[\d+\]$" + f"=top:{w - 540:g}-{w - 370:g}")
    regions.append(f"^(clk|rst_n)$=top:{w / 2 - 20:g}-{w / 2 + 20:g}")
    args = ["--view", "asap7", "--top", "ot_chip_v41x_hbm_karb", "--source", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
            "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2", "--stages", "synth,pnr",
            "--die-area", "0", "0", f"{w:g}", f"{h:g}",
            "--core-area", f"{m:g}", f"{m:g}", f"{w - m:g}", f"{h - m:g}",
            "--place-density", "0.60"]
    for r in regions:
        args += ["--pin-region", r]
    return {"args": args, "nickname": "claude_v41x_karb_strip",
            "output": "results/asap7_physical/v41x_die_karb/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM, "pc_pin_span_um": PC_PIN_SPAN}}


# ------------------------------------------------------------------------------------------------ physical tile
MACRO_DIR = "physical/asap7_memory_macros"
MACROS = {   # name: (width, height) um, from the compiler LEFs
    "ot_rom_8192x266_m8": (122.256, 119.340),
    "ot_rom_8192x274_m8": (125.712, 119.340),
    "ot_sram_1r1w_64x512_m1_r2c2": (171.288, 77.760),
    "ot_sram_1r1w_512x128_m4_r2c2": (174.096, 29.700),
}
# routed standard-cell area of the engine tiles (post-route, results/physical_abi3/asap7/hdc/v41x/*)
QTILE_UM2, MTILE_UM2 = 21076.0, 53894.7
FLOP_UM2 = 0.29                     # ASAP7 DFFHQNx1 (0.2916 um^2)
ENGINE_SOURCES = ["rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_fastfp.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_bdot.sv",
                  "rtl/hdc/v41x/ot_hdc_v41x_wgt_mac.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_red.sv",
                  "rtl/hdc/v41x/ot_hdc_v41x_wgt_tile.sv", "rtl/hdc/v41x/ot_hdc_v41x_wgt_tops.sv"]
CHANNEL_UM = 15.0                   # routing / capture-register channel beside every macro column
LANE_ASPECT = 1.5648 / 3.9937       # the die assembly's tile lane column, width / height


def snap(v: float, g: float = 0.192) -> float:
    return round(round(v / g) * g, 3)


def ptile_macros(nq: int, nm: int) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(instance, master) per side: side A (west, the spine side) and side B (east)."""
    a, b = [], []
    for g in range(nq):
        side = a if g < (nq + 1) // 2 else b
        side += [(f"g_q[{g}].g_rom[{c}].u_rom", "ot_rom_8192x266_m8") for c in range(8)]
    a += [(f"g_act[{c}].u_act", "ot_sram_1r1w_64x512_m1_r2c2") for c in range(4)]
    b += [(f"g_act[{c}].u_act", "ot_sram_1r1w_64x512_m1_r2c2") for c in range(4, 8)]
    if nm:
        for c in range(8):
            side = a if c < 4 else b
            side += [(f"g_m.g_mc[{c}].u_rom", "ot_rom_8192x274_m8"),
                     (f"g_m.g_mc[{c}].u_act", "ot_sram_1r1w_512x128_m4_r2c2")]
    return a, b


def pack_columns(items: list[tuple[str, str]], height: float, gap: float = 4.0) -> list[list[tuple[str, str]]]:
    cols, cur, h = [], [], 0.0
    for it in sorted(items, key=lambda x: -MACROS[x[1]][1]):
        mh = MACROS[it[1]][1] + gap
        if cur and h + mh > height:
            cols.append(cur)
            cur, h = [], 0.0
        cur.append(it)
        h += mh
    if cur:
        cols.append(cur)
    return cols


def ptile(nq: int = 2, nm: int = 0, np_: int = 2, util: float = 0.68, density: float | None = None) -> dict:
    regs = (nq * 8 * 264 + 8 * 264 + nm * 8 * (272 + 128)
            + np_ * (106 + 274 + nq * 70 + nm * (107 + 141 + 221)))
    a_std = nq * QTILE_UM2 + nm * MTILE_UM2 + regs * FLOP_UM2
    a_lane = a_std / util
    side_a, side_b = ptile_macros(nq, nm)
    height = max((a_lane / LANE_ASPECT) ** 0.5, max(MACROS[m][1] for _, m in side_a + side_b) + 8)
    cols_a, cols_b = pack_columns(side_a, height), pack_columns(side_b, height)
    col_h = max(sum(MACROS[m][1] + 4.0 for _, m in c) for c in cols_a + cols_b)
    core_h = snap(max(height, col_h + 8.0), 0.27 * 4)
    lane_w = a_lane / core_h
    margin = 2.16
    placements, x = [], margin + CHANNEL_UM
    for col in cols_a:
        y = margin + 4.0
        for inst, m in col:
            placements.append((inst, snap(x), snap(y, 0.27), "R0"))
            y += MACROS[m][1] + 4.0
        x += max(MACROS[m][0] for _, m in col) + CHANNEL_UM
    lane_x0 = x
    x = lane_x0 + lane_w + CHANNEL_UM
    for col in cols_b:
        y = margin + 4.0
        for inst, m in col:
            placements.append((inst, snap(x), snap(y, 0.27), "MY"))
            y += MACROS[m][1] + 4.0
        x += max(MACROS[m][0] for _, m in col) + CHANNEL_UM
    die_w, die_h = snap(x + margin), snap(core_h + 2 * margin, 0.27)
    tcl = ["# Macro placement of ot_chip_v41x_ptile (tools/v41x_die_pnr.py): ROM | lane column | ROM.",
           "proc ot_place {want x y orient} {",
           "  foreach inst [[ord::get_db_block] getInsts] {",
           "    set n [$inst getName]",
           "    if {[string map {\\\\ {}} $n] eq $want} {",
           "      place_macro -macro_name $n -location [list $x $y] -orientation $orient",
           "      return",
           "    }",
           "  }",
           "  error \"macro placement: no instance $want\"",
           "}"]
    tcl += [f"ot_place {{{i}}} {px:g} {py:g} {o}" for i, px, py, o in placements]
    masters = sorted({m for _, m in side_a + side_b})
    sources = ENGINE_SOURCES + [f"{MACRO_DIR}/{m}/{m}_bb.v" for m in masters] + ["rtl/chip/ot_chip_v41x_ptile.sv"]
    args = ["--view", "asap7", "--top", "ot_chip_v41x_ptile"]
    for s in sources:
        args += ["--source", s]
    args += ["--param", f"NQ={nq}", "--param", f"NM={nm}", "--param", f"NP={np_}",
             "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2", "--stages", "synth,pnr",
             "--die-area", "0", "0", f"{die_w:g}", f"{die_h:g}",
             "--core-area", f"{margin:g}", f"{margin:g}", f"{die_w - margin:g}", f"{die_h - margin:g}",
             "--place-density", f"{density if density else min(0.95, util + 0.1):g}",
             "--macro-place-halo", "2", "2", "--pin-region", ".*=left"]
    for m in masters:
        args += ["--macro-view", f"{m}={MACRO_DIR}/{m}"]
    macro_area = sum(MACROS[m][0] * MACROS[m][1] for _, m in side_a + side_b)
    tag = f"q{nq}m{nm}_u{int(round(util * 100))}"
    return {"args": args, "nickname": f"claude_v41x_ptile_{tag}", "hook": ("PRE_MACRO_PLACE", "\n".join(tcl) + "\n"),
            "output": f"results/asap7_physical/v41x_tile_{tag}/physical.json",
            "floorplan": {"die_um": [die_w, die_h], "lane_region_um": [round(lane_x0, 3), margin,
                                                                       round(lane_x0 + lane_w, 3), die_h - margin],
                          "lane_area_um2": round(a_lane, 1), "target_lane_utilisation": util,
                          "estimated_stdcell_um2": round(a_std, 1), "macro_area_um2": round(macro_area, 1),
                          "macros": [{"inst": i, "x": px, "y": py, "orient": o} for i, px, py, o in placements],
                          "columns": {"A": len(cols_a), "B": len(cols_b)}, "channel_um": CHANNEL_UM}}


CASES = {"karb_strip": karb_strip,
         "tile_q2_u68": lambda: ptile(2, 0, 2, 0.68),
         "tile_q2_u75": lambda: ptile(2, 0, 2, 0.75),
         "tile_q4m1_u68": lambda: ptile(4, 1, 2, 0.68)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("case", choices=sorted(CASES))
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--work", type=Path, default=Path(os.environ.get("OT_V41PNR_WORK", "/home/ubuntu/v41dpnr/work")))
    ap.add_argument("--output")
    a = ap.parse_args()
    c = CASES[a.case]()
    argv = [sys.executable, str(ROOT / "tools/run_abi3_physical.py"), *c["args"], "--nickname-tag", c["nickname"],
            "--output", a.output or c["output"], "--keep-workdir", str(a.work / a.case), "--force"]
    if c.get("hook"):
        hook, text = c["hook"]
        hdir = a.work / f"{a.case}_hooks"
        hdir.mkdir(parents=True, exist_ok=True)
        (hdir / "macro_placement.tcl").write_text(text)
        argv += ["--step-tcl", f"{hook}={hdir / 'macro_placement.tcl'}"]
    if a.print:
        print(json.dumps(c.get("floorplan"), indent=1))
    if a.print or not a.run:
        print(" ".join(x if len(x) < 200 else x[:80] + f"...<{len(x)} chars>" for x in argv))
        print(f"{len(argv)} arguments, {sum(len(x) for x in argv)} bytes")
    if a.run:
        (a.work / a.case).mkdir(parents=True, exist_ok=True)
        return subprocess.run(argv, cwd=ROOT).returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
