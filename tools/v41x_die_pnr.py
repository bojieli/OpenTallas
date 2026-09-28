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
    alts = [f"^{n}$" if ix == [""] else f"^{n}\\[({'|'.join(ix)})\\]$"
            for n, ix in by_bus.items()]
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
    fit = height_um <= 17.28
    return {"args": args, "nickname": "codex_v41x_karb_strip_fit" if fit else "claude_v41x_karb_strip",
            "output": "results/asap7_physical/v41x_die_karb_fit/physical.json" if fit
                      else "results/asap7_physical/v41x_die_karb/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM, "pc_pin_span_um": PC_PIN_SPAN}}


def karb_bank4(height_um: float = 30.24, high_layers: bool = False, pipe_out: bool = False,
               wide_pins: bool = False, low_density: bool = False) -> dict:
    """A four-PC local arbitration partition for a bounded physical route.

    This uses the real parameterized arbiter RTL with NPC=4. Its K address-to-PC
    hash is the four-PC configuration, so it characterizes the local bank and
    cannot replace the NPC=32 strip's functional or timing gate.
    """
    npc = 4
    w, h = npc * PHY_PC_WINDOW_UM, height_um
    m = 8 * ROW_UM
    regions = []
    pin_span = (10.0, 350.0) if wide_pins else PC_PIN_SPAN
    for p in range(npc):
        x0 = p * PHY_PC_WINDOW_UM
        span = f"{x0 + pin_span[0]:g}-{x0 + pin_span[1]:g}"
        regions.append(f"{pin_regex(karb_pc_pins(p, 'h'))}=bottom:{span}")
        regions.append(f"{pin_regex(karb_pc_pins(p, 'b'))}=top:{span}")
    k = r"^k_(v|rdy|we|wr_done|rsp_v|rsp_rdy)$|^k_(addr|len|tag|wdata|wstrb|rsp_tag|rsp_beat|rsp_data)\[\d+\]$"
    regions.append(f"{k}=top:{w - 165:g}-{w - 5:g}")
    regions.append(r"^(k_grants|b_grants|contended)\[\d+\]$" + f"=top:{w - 540:g}-{w - 370:g}")
    regions.append(f"^(clk|rst_n)$=top:{w / 2 - 20:g}-{w / 2 + 20:g}")
    args = ["--view", "asap7", "--top", "ot_chip_v41x_hbm_karb", "--source", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
            "--param", f"NPC={npc}", "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2",
            "--stages", "synth,pnr", "--die-area", "0", "0", f"{w:g}", f"{h:g}",
            "--core-area", f"{m:g}", f"{m:g}", f"{w - m:g}", f"{h - m:g}",
            "--place-density", "0.40" if low_density else "0.60"]
    if high_layers:
        args += ["--routing-layers", "M2", "M9"]
    if pipe_out:
        args += ["--param", "PIPE_OUT=1"]
    if wide_pins:
        # Characterize the new internal register boundary separately.  The
        # original 0.2-T IO case above remains the external-timing gate.
        args += ["--false-path-io"]
    for r in regions:
        args += ["--pin-region", r]
    if pipe_out and high_layers and wide_pins and low_density:
        name = "karb_bank4_pipe_wide_lowdens_m9"
    elif pipe_out and high_layers and wide_pins:
        name = "karb_bank4_pipe_wide_m9"
    elif pipe_out and high_layers:
        name = "karb_bank4_pipe_m9"
    else:
        name = "karb_bank4_m9" if high_layers else "karb_bank4"
    return {"args": args, "nickname": f"codex_v41x_{name}",
            "output": f"results/asap7_physical/v41x_die_{name}/physical.json",
            "floorplan": {"die_um": [w, h], "npc": npc, "pc_window_um": PHY_PC_WINDOW_UM,
                          "pc_pin_span_um": pin_span, "scope": "local bank characterization only"}}


def collective_fifo128() -> dict:
    """Representative routed collective boundary with the measured depth-128 receive FIFO.

    This is one engine, not the eight-engine die assembly.  The generous
    850-um square exposes its actual standard-cell cost and 0.92-ns timing
    before a die floorplan credits it.
    """
    args = ["--view", "asap7", "--top", "ot_rom_oneshot_die_px",
            "--source", "rtl/rom/ot_rom_oneshot_px.sv",
            "--source", "rtl/hdc/ot_hdc_fastfp.sv",
            "--source", "rtl/proto/ot_fp32_add_rne_pipe.sv",
            "--param", "N=4", "--param", "RANK=0", "--param", "LANES=16",
            "--param", "DEPTH=128", "--param", "RELAY=1", "--param", "ADD_LAT=3",
            "--param", "PAIRWISE=1", "--param", "GW=1", "--param", "FW=512",
            "--param", "TAGW=32", "--clock-period-ns", f"{CLOCK_NS:g}",
            "--io-delay-fraction", "0.2", "--stages", "synth,pnr",
            "--die-area", "0", "0", "850", "850",
            "--core-area", "20", "20", "830", "830", "--place-density", "0.60",
            "--routing-layers", "M2", "M9"]
    return {"args": args, "nickname": "codex_v41x_collective_fifo128",
            "output": "results/asap7_physical/v41x_collective_fifo128/physical.json",
            "floorplan": {"die_um": [850.0, 850.0], "core_um": [20.0, 20.0, 830.0, 830.0],
                          "scope": "one standalone 16-lane engine; no eight-engine die placement"}}


def karb_pc1_pipe_m9(slew_repair: bool = False) -> dict:
    """One-PC local request/response slice, with its own registered HBM output.

    This physical boundary is a partition study.  NPC=1 removes the 32-way K
    demux/response select and therefore cannot certify the parent arbiter.
    """
    w, h = PHY_PC_WINDOW_UM, 30.24
    m = 8 * ROW_UM
    scalar = {"b_v", "b_rdy", "b_we", "b_wr_done", "b_rsp_v", "b_rsp_rdy",
              "h_v", "h_rdy", "h_we", "h_wr_done", "r_v", "r_rdy"}
    def local_pins(side: str) -> list[str]:
        return [x[:-3] if x.endswith("[0]") and x[:-3] in scalar else x
                for x in karb_pc_pins(0, side)]
    regions = [f"{pin_regex(local_pins('h'))}=bottom:20-195",
               f"{pin_regex(local_pins('b'))}=top:20-195",
               r"^k_(v|rdy|we|wr_done|rsp_v|rsp_rdy)$|^k_(addr|len|tag|wdata|wstrb|rsp_tag|rsp_beat|rsp_data)\[\d+\]$=top:210-370",
               r"^(k_grants|b_grants|contended)\[\d+\]$=bottom:210-370",
               r"^(clk|rst_n)$=left:10-20"]
    args = ["--view", "asap7", "--top", "ot_chip_v41x_hbm_karb",
            "--source", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
            "--param", "NPC=1", "--param", "PIPE_OUT=1",
            "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2",
            "--stages", "synth,pnr", "--die-area", "0", "0", f"{w:g}", f"{h:g}",
            "--core-area", f"{m:g}", f"{m:g}", f"{w-m:g}", f"{h-m:g}",
            "--place-density", "0.40", "--routing-layers", "M2", "M9"]
    if slew_repair:
        args += ["--max-transition-ns"]
    for r in regions:
        args += ["--pin-region", r]
    name = "karb_pc1_pipe_slew_m9" if slew_repair else "karb_pc1_pipe_m9"
    return {"args": args, "nickname": f"codex_v41x_{name}",
            "output": f"results/asap7_physical/v41x_die_{name}/physical.json",
            "floorplan": {"die_um": [w, h], "pc_window_um": PHY_PC_WINDOW_UM,
                          "scope": "one PC with NPC=1; excludes full 32-way K demux/response mux"}}


def karb_group4_m9(height_um: float = 30.24, outpipe: bool = False) -> dict:
    """Four adjacent PC slices with registered K ingress/return and local PHY pins."""
    c = karb_bank4(height_um=height_um, high_layers=True)
    args = c["args"].copy()
    args[args.index("--top") + 1] = "ot_chip_v41x_hbm_karb_group4"
    i = args.index("--source")
    args[i + 1:i + 2] = ["rtl/chip/ot_chip_v41x_hbm_karb_group4.sv",
                         "--source", "rtl/chip/ot_chip_v41x_hbm_karb.sv",
                         "--source", "rtl/chip/ot_chip_v41x_hbm_rsp_pipe.sv"]
    # Yosys 0.68 hits an RTLIL duplicate-module assertion when `hierarchy`
    # reprocesses this parameterized top with -chparam.  The top's defaults
    # are NPC=4, PIPE_OUT=1 and PIPE_RSP=1, checked by the exact RTL gate.
    j = args.index("NPC=4")
    assert args[j - 1] == "--param"
    del args[j - 1:j + 1]
    args += ["--max-transition-ns"]
    args[args.index("--place-density") + 1] = "0.40"
    name = ("karb_group4_fit_m9" if height_um <= 17.28 else
            "karb_group4_outpipe_m9" if outpipe else "karb_group4_m9")
    return {"args": args, "nickname": f"codex_v41x_{name}",
            "output": f"results/asap7_physical/v41x_die_{name}/physical.json",
            "floorplan": {**c["floorplan"], "scope": "four local PC slices and registered K group boundary"}}


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


def ptile(nq: int = 2, nm: int = 0, np_: int = 2, util: float = 0.68, density: float | None = None,
          fit_um: tuple[float, float] | None = None) -> dict:
    """fit_um (w, h): build the tile to fit that footprint (the die route's tile slot): the core height is the
    slot's, the macro columns are packed to it, and the case fails if the width does not fit."""
    regs = (nq * 8 * 264 + 8 * 264 + nm * 8 * (272 + 128)
            + np_ * (106 + 274 + nq * 70 + nm * (107 + 141 + 221)))
    a_std = nq * QTILE_UM2 + nm * MTILE_UM2 + regs * FLOP_UM2
    a_lane = a_std / util
    side_a, side_b = ptile_macros(nq, nm)
    margin = 2.16
    if fit_um:
        core_h = snap(fit_um[1] - 2 * margin - 0.54, 0.27 * 4)
        if core_h + 2 * margin > fit_um[1]:
            core_h -= 1.08
        height = core_h - 8.0
    else:
        height = max((a_lane / LANE_ASPECT) ** 0.5, max(MACROS[m][1] for _, m in side_a + side_b) + 8)
    cols_a, cols_b = pack_columns(side_a, height), pack_columns(side_b, height)
    col_h = max(sum(MACROS[m][1] + 4.0 for _, m in c) for c in cols_a + cols_b)
    if not fit_um:
        core_h = snap(max(height, col_h + 8.0), 0.27 * 4)
    lane_w = a_lane / core_h
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
    if fit_um and (die_w > fit_um[0] or die_h > fit_um[1]):
        raise ValueError(f"tile {die_w} x {die_h} um does not fit the {fit_um[0]} x {fit_um[1]} um slot")
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
             "--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2", "--stages", "pnr",
             "--die-area", "0", "0", f"{die_w:g}", f"{die_h:g}",
             "--core-area", f"{margin:g}", f"{margin:g}", f"{die_w - margin:g}", f"{die_h - margin:g}",
             "--place-density", f"{density if density else min(0.95, util + 0.1):g}",
             "--macro-place-halo", "2", "2", "--pin-region", ".*=left"]
    for m in masters:
        args += ["--macro-view", f"{m}={MACRO_DIR}/{m}"]
    macro_area = sum(MACROS[m][0] * MACROS[m][1] for _, m in side_a + side_b)
    tag = f"q{nq}m{nm}_u{int(round(util * 100))}" + ("_s4slot" if fit_um else "")
    return {"args": args, "nickname": f"claude_v41x_ptile_{tag}", "hook": ("PRE_MACRO_PLACE", "\n".join(tcl) + "\n"),
            "output": f"results/asap7_physical/v41x_tile_{tag}/physical.json",
            "floorplan": {"die_um": [die_w, die_h], "lane_region_um": [round(lane_x0, 3), margin,
                                                                       round(lane_x0 + lane_w, 3), die_h - margin],
                          "lane_area_um2": round(a_lane, 1), "target_lane_utilisation": util,
                          "estimated_stdcell_um2": round(a_std, 1), "macro_area_um2": round(macro_area, 1),
                          "macros": [{"inst": i, "x": px, "y": py, "orient": o} for i, px, py, o in placements],
                          "columns": {"A": len(cols_a), "B": len(cols_b)}, "channel_um": CHANNEL_UM}}


# ------------------------------------------------------------------------------------------------ reduced die
PDIE_DIR = "physical/asap7_v41x_pdie_macros"
S4 = 0.25                                         # linear scale of the reduced die
TILE_CHANNEL_UM = 20.0                            # die-level channel between tiles (repeaters, pipeline flops)
OPW, RESW, RECW, FLW = 380, 140, 547, 512


def s4_tile_slot() -> tuple[float, float]:
    """The reduced die's tile footprint (ot_pdie_tile_io), um."""
    s = pdie_specs()["ot_pdie_tile_io"]
    return s.width_um, s.height_um


def die_assembly_rects() -> dict:
    d = json.loads((ROOT / "results/arch/v41_die_assembly.json").read_text())
    return d["floorplan"]["layer"]


def pdie_specs() -> dict:
    """The reduced die's hard-macro abstracts (tools/chip_assembly/macros.py MacroSpec)."""
    sys.path.insert(0, str(ROOT / "tools"))
    from chip_assembly import macros as mc
    sys.path.insert(0, str(ROOT / "tools/mem_compiler"))
    import hbm_phy_gen
    fp = die_assembly_rects()
    tw, th = fp["tiles"]["w_mm"] * 1000 * S4 - TILE_CHANNEL_UM, fp["tiles"]["h_mm"] * 1000 * S4 - TILE_CHANNEL_UM
    phy = next(r for r in fp["rects"] if r["name"] == "HBM3E PHY 0")
    pw, ph = mc.snap(phy["w"] * 1000 * S4, mc.SITE_W), mc.snap(phy["h"] * 1000 * S4, mc.SITE_H)
    win = pw / NPC
    plist, place = hbm_phy_gen.v41x_pins()
    pins = []
    for p in plist:
        if p.kind == "clock":
            continue
        edges = []
        for i in range(p.width):
            wi, grp = place[p.name if p.width == 1 else f"{p.name}[{i}]"]
            span = (wi * win + 2.0, wi * win + 0.66 * win) if grp == "k" else (wi * win + 0.68 * win, wi * win + win - 2)
            edges.append((i, i, "N", span))
        pins.append(mc.Pin(p.name, p.direction, p.width, edges))
    phy_t = hbm_phy_gen.v41x_pins()  # noqa: F841  (the same list the full-size abstract uses)
    specs = {
        "ot_hbm3e_phy_v41x_s4": mc.MacroSpec(
            "ot_hbm3e_phy_v41x_s4", pw, ph, pins, clk_to_q_ns=0.117, setup_ns=0.065, hold_ns=0.031,
            obs_layers=("M1", "M2", "M3", "M4"), kind="phy",
            basis="ot_hbm3e_phy_v41x (the adopted port list) at 1/4 of the die assembly's 12.0 x 0.8335 mm; "
                  "pseudo-channel p's K bits in the first two-thirds of its edge window, W bits in the rest; "
                  "boundary timing as the full-size abstract (assumed)"),
        "ot_pdie_tile_io": mc.MacroSpec(
            "ot_pdie_tile_io", mc.snap(tw, mc.SITE_W), mc.snap(th, mc.SITE_H),
            mc.pins(("op_in", "input", OPW, "E"), ("res_out", "output", RESW, "E")),
            clk_to_q_ns=0.10, setup_ns=0.08, obs_layers=tuple(f"M{i}" for i in range(1, 8)), kind="tile",
            basis="a die-assembly tile at 1/4 scale less the die channel; operand in and result out registered at "
                  "its spine-facing edge (the physical tile's edge registers, ot_chip_v41x_ptile NP stages); "
                  "routes M2-M7 inside (obstructed), die wiring passes over it on M8/M9"),
        "ot_pdie_tile_bk": mc.MacroSpec(
            "ot_pdie_tile_bk", mc.snap(tw, mc.SITE_W), mc.snap(th, mc.SITE_H), [],
            obs_layers=tuple(f"M{i}" for i in range(1, 8)), kind="tile",
            basis="as ot_pdie_tile_io without die-level pins: an M1-M7 blockage"),
        "ot_pdie_coll": mc.MacroSpec(
            "ot_pdie_coll", mc.snap(900 * S4, mc.SITE_W), mc.snap(442.4 * S4, mc.SITE_H),
            mc.pins(("rec_in", "input", RECW, "W"), ("rec_out", "output", RECW, "W"),
                    ("link_out", "output", FLW, "E"), ("link_in", "input", FLW, "E")),
            obs_layers=tuple(f"M{i}" for i in range(1, 7)), kind="collective",
            basis="the die assembly's one-shot collective engine block (0.9 x 0.4424 mm) at 1/4; records of "
                  "32 x CL_LANES + 3 + CL_TAGW = 547 bits (ot_chip_v41x_die CL_PW), 512-bit link flits"),
        "ot_pdie_ucie": mc.MacroSpec(
            "ot_pdie_ucie", mc.snap(1043 * S4, mc.SITE_W), mc.snap(6609.6 * S4, mc.SITE_H),
            mc.pins(("tx", "input", FLW, "W"), ("rx", "output", FLW, "W")),
            obs_layers=("M1", "M2", "M3", "M4"), kind="link",
            basis="UCIe-A shoreline (die assembly 1.043 x 6.61 mm) at 1/4, one 512-bit flit port each way"),
        "ot_pdie_serdes": mc.MacroSpec(
            "ot_pdie_serdes", mc.snap(1000 * S4, mc.SITE_W), mc.snap(9000 * S4, mc.SITE_H),
            mc.pins(("tx", "input", FLW, "E"), ("rx", "output", FLW, "E")),
            obs_layers=("M1", "M2", "M3", "M4"), kind="link",
            basis="half of the 112G SerDes strip (die assembly 1.0 x 18.0 mm) at 1/4: the package-pair "
                  "collective lanes, or the stage-hop lanes"),
    }
    return specs


def write_pdie_views(out: Path | None = None) -> dict:
    sys.path.insert(0, str(ROOT / "tools"))
    from chip_assembly import macros as mc
    out = out or ROOT / PDIE_DIR
    rec = {}
    for name, spec in pdie_specs().items():
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(mc.lef_text(spec))
        (d / f"{name}_tt.lib").write_text(mc.liberty_text(spec))
        (d / f"{name}_bb.v").write_text(mc.verilog_stub(spec))
        rec[name] = mc.describe(spec)
    (out / "index.json").write_text(json.dumps({"generator": "tools/v41x_die_pnr.py write_pdie_views",
                                                "scale": S4, "macros": rec}, indent=1, sort_keys=True) + "\n")
    return rec


RT_TILE = "ot_chip_v41x_ptile"
RT_TILE_DIR = f"{PDIE_DIR}/{RT_TILE}_q2s4"         # the routed tile_q2_s4slot's ORFS abstract (write_rt_tile_view)


def ptile_ports(nq: int = 2, nm: int = 0) -> list[tuple[str, str, int]]:
    """(direction, name, width) of ot_chip_v41x_ptile at NQ / NM, in declaration order."""
    import re
    text = (ROOT / "rtl/chip/ot_chip_v41x_ptile.sv").read_text()
    body = text[text.index("module ot_chip_v41x_ptile"):]
    ports = body[body.index(") (") + 3:body.index(");")]
    env = {"NQ": nq, "NM": nm}
    out = []
    for m in re.finditer(r"(input|output)\s+(?:wire|reg)?\s*(?:\[([^\]]+):0\])?\s*(\w+)", ports):
        w = eval(m.group(2), {}, env) + 1 if m.group(2) else 1
        out.append((m.group(1), m.group(3), w))
    return out


def write_rt_tile_view(orfs_results: Path, out: Path | None = None) -> dict:
    """The routed tile_q2_s4slot as a die-level hard macro: ORFS generate_abstract's LEF and timing model
    (orfs_results = the kept work dir's results/asap7/<nickname>/base), plus a black-box stub."""
    import hashlib
    out = out or ROOT / RT_TILE_DIR
    out.mkdir(parents=True, exist_ok=True)
    lef, lib = orfs_results / f"{RT_TILE}.lef", orfs_results / f"{RT_TILE}_typ.lib"
    (out / f"{RT_TILE}.lef").write_bytes(lef.read_bytes())
    (out / f"{RT_TILE}_tt.lib").write_bytes(lib.read_bytes())
    lines = [f"// Black box of the routed {RT_TILE} (NQ = 2, NM = 0; tools/v41x_die_pnr.py tile_q2_s4slot).",
             f"(* blackbox *) module {RT_TILE} ("]
    decl = []
    for d, n, w in ptile_ports(2, 0):
        decl.append(f"    {d} wire {'' if w == 1 else f'[{w - 1}:0] '}{n}")
    lines += [",\n".join(decl), ");", "endmodule", ""]
    (out / f"{RT_TILE}_bb.v").write_text("\n".join(lines))
    rec = {"generator": "tools/v41x_die_pnr.py write_rt_tile_view", "source": "ORFS generate_abstract of the "
           "routed tile_q2_s4slot (write_abstract_lef -bloat_occupied_layers, write_timing_model)",
           "files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.iterdir())
                     if f.name != "index.json"}}
    (out / "index.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    return rec


def die_s4(n_far: int = 5, n_far2: int = 4, n_mid: int = 2, n_near: int = 1, n_key: int = 2, n_coll: int = 3,
           n_ser: int = 3, stop: str | None = None, tile_rt: bool = False) -> dict:
    """tile_rt: the four pinned tiles are the routed physical tile (tile_q2_s4slot's abstract, pins on its
    west edge, so mirrored relative to the placeholder: MY west of the spine, R0 east of it)."""
    fp = die_assembly_rects()
    k = 1000 * S4
    W, H = snap(fp["die_w_mm"] * k), snap(fp["die_h_mm"] * k, 0.27)
    specs = {n: (s.width_um, s.height_um) for n, s in pdie_specs().items()}
    place = []
    # HBM PHYs: the long edges, pins facing the core
    for i, r in enumerate([r for r in fp["rects"] if r["cls"] == "phy_hbm"]):
        top = r["y"] > fp["die_h_mm"] / 2
        y = H - specs["ot_hbm3e_phy_v41x_s4"][1] if top else 0.0
        place.append((f"g_s[{i}].u_phy", r["x"] * k, y, "MX" if top else "R0"))
    # tiles: the lane columns' tiles, shrunk by the channel
    tiles = {}
    for r in fp["rects"]:
        if r.get("tile"):
            key = r["name"].split()[1]
            x0, y0, x1, y1 = r["x"], r["y"], r["x"] + r["w"], r["y"] + r["h"]
            b = tiles.get(key, [x0, y0, x1, y1])
            tiles[key] = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]
    spine = next(r for r in fp["rects"] if r["cls"] == "vector")
    sx = (spine["x"] + spine["w"] / 2) * k
    order = sorted(tiles.items(), key=lambda kv: -(abs((kv[1][0] + kv[1][2]) / 2 * k - sx)
                                                   + abs((kv[1][1] + kv[1][3]) / 2 * k - H / 2)))
    far0 = order[0]
    far1 = next(t for t in order if (t[1][0] * k < sx) != (far0[1][0] * k < sx))
    mid = order[len(order) // 2]
    near = order[-1]
    io = [far0[0], far1[0], mid[0], near[0]]
    bk = 0
    for key, (x0, y0, x1, y1) in sorted(tiles.items()):
        west = x1 * k <= sx
        orient = "R0" if west else "MY"
        if key in io:
            inst = f"g_tio[{io.index(key)}].{'g_rt' if tile_rt else 'g_ph'}.u_tile"
            if tile_rt:
                orient = "MY" if west else "R0"
        else:
            inst = f"g_tbk[{bk}].u_tile"
            bk += 1
        place.append((inst, x0 * k + TILE_CHANNEL_UM / 2, y0 * k + TILE_CHANNEL_UM / 2, orient))
    coll = [r for r in fp["rects"] if r["cls"] == "collective"]
    ucie = next(r for r in fp["rects"] if r["cls"] == "phy_ucie")
    ser = next(r for r in fp["rects"] if r["cls"] == "phy_serdes")
    cu = next(r for r in coll if "UCIe" in r["name"])
    cp = next(r for r in coll if "package-pair" in r["name"])
    place.append(("g_coll[0].u_coll", cu["x"] * k, cu["y"] * k, "R0"))
    place.append(("g_coll[1].u_coll", cp["x"] * k, cp["y"] * k + 10, "MY"))
    place.append(("g_coll[0].g_ucie.u_link", W - specs["ot_pdie_ucie"][0], ucie["y"] * k, "R0"))
    place.append(("g_coll[1].g_ser.u_link", 0.0, ser["y"] * k + specs["ot_pdie_serdes"][1] + 10, "R0"))
    place.append(("u_hop", 0.0, ser["y"] * k, "R0"))
    tcl = ["# Macro placement of ot_chip_v41x_pdie (tools/v41x_die_pnr.py die_s4): the die assembly x 1/4.",
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
    tcl += [f"ot_place {{{i}}} {snap(x):g} {snap(y, 0.27):g} {o}" for i, x, y, o in place]
    srcs = ["rtl/chip/ot_chip_v41x_hbm_karb.sv", "rtl/chip/ot_chip_v41x_kv_prefetch.sv"]
    srcs += [f"{PDIE_DIR}/{n}/{n}_bb.v" for n in specs]
    if tile_rt:
        srcs.append(f"{RT_TILE_DIR}/{RT_TILE}_bb.v")
    srcs.append("rtl/chip/ot_chip_v41x_pdie.sv")
    args = ["--view", "asap7", "--top", "ot_chip_v41x_pdie"]
    for s_ in srcs:
        args += ["--source", s_]
    for n, v in (("N_FAR", n_far), ("N_FAR2", n_far2), ("N_MID", n_mid), ("N_NEAR", n_near), ("N_KEY", n_key),
                 ("N_COLL", n_coll), ("N_SER", n_ser), ("TILE_RT", int(tile_rt))):
        args += ["--param", f"{n}={v}"]
    m = 2.16
    args += ["--clock-period-ns", f"{CLOCK_NS:g}", "--io-delay-fraction", "0.2", "--stages", "pnr",
             "--die-area", "0", "0", f"{W:g}", f"{H:g}", "--core-area", f"{m:g}", f"{m:g}", f"{W - m:g}", f"{H - m:g}",
             "--place-density", "0.60", "--macro-place-halo", "2", "2", "--routing-layers", "M2", "M9",
             "--pin-region", ".*=left:100-800",
             "--orfs-var", "PDN_TCL=/src/tools/chip_assembly/tcl/pdn_v41x_pdie.tcl"]
    for n in specs:
        args += ["--macro-view", f"{n}={PDIE_DIR}/{n}"]
    if tile_rt:
        args += ["--macro-view", f"{RT_TILE}={RT_TILE_DIR}"]
    if stop:
        args += ["--pnr-stop-after", stop]
    tag = f"s4_f{n_far}{n_far2}m{n_mid}n{n_near}k{n_key}c{n_coll}h{n_ser}" + ("_rt" if tile_rt else "")
    return {"args": args, "nickname": f"claude_v41x_pdie_{tag}", "hook": ("PRE_MACRO_PLACE", "\n".join(tcl) + "\n"),
            "output": f"results/asap7_physical/v41x_die_{tag}/physical.json",
            "floorplan": {"die_um": [W, H], "scale": S4, "tile_channel_um": TILE_CHANNEL_UM,
                          "spine_centre_x_um": round(sx, 1),
                          "io_tiles": {"far": far0[0], "far_other_side": far1[0], "mid": mid[0], "near": near[0]},
                          "macros": [{"inst": i, "x": snap(x), "y": snap(y, 0.27), "orient": o}
                                     for i, x, y, o in place]}}


CASES = {"karb_strip": karb_strip,
         "karb_strip_fit": lambda: karb_strip(height_um=17.28),
         "karb_bank4": karb_bank4,
         "karb_bank4_m9": lambda: karb_bank4(high_layers=True),
         "karb_bank4_pipe_m9": lambda: karb_bank4(high_layers=True, pipe_out=True),
         "karb_bank4_pipe_wide_m9": lambda: karb_bank4(high_layers=True, pipe_out=True, wide_pins=True),
         "karb_bank4_pipe_wide_lowdens_m9": lambda: karb_bank4(high_layers=True, pipe_out=True,
                                                                  wide_pins=True, low_density=True),
         "collective_fifo128": collective_fifo128,
         "karb_pc1_pipe_m9": karb_pc1_pipe_m9,
         "karb_pc1_pipe_slew_m9": lambda: karb_pc1_pipe_m9(slew_repair=True),
         "karb_group4_m9": karb_group4_m9,
         "karb_group4_outpipe_m9": lambda: karb_group4_m9(outpipe=True),
         "karb_group4_fit_m9": lambda: karb_group4_m9(height_um=17.28),
         "die_s4": die_s4,
         "die_s4_rt": lambda: die_s4(tile_rt=True),
         "tile_q2_u68": lambda: ptile(2, 0, 2, 0.68),
         "tile_q2_u75": lambda: ptile(2, 0, 2, 0.75),
         "tile_q4m1_u68": lambda: ptile(4, 1, 2, 0.68),
         "tile_q2_s4slot": lambda: ptile(2, 0, 2, 0.68, fit_um=s4_tile_slot())}


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
