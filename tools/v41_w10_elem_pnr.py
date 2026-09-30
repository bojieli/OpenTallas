#!/usr/bin/env python3
"""Floorplan, placement hook and run_abi3_physical argv for ONE V4.1 ROM-array element (W10 item 3).

    python3 tools/v41_w10_elem_pnr.py --write-hook     # physical/abi3/v41_w10_elem_place.tcl
    python3 tools/v41_w10_elem_pnr.py --print          # the run_abi3_physical argv (JSON)

Element = ot_v41_rom_elem: one ot_rom_8192x274_m8 (125.712 x 119.340 um) + capture register + 2 block-dot
lanes + chunk chains + pair adder + segment tree + x FIFO.  Layout (x left to right), as one half of a W1 pair
column [ROM R0 | MAC strip | ROM MY]:
    channel CH | ROM (R0; rd_out pins on its west and east M4 edges) | channel CH | logic strip LOGIC_W
The capture flop of every rd_out pin is FIXED beside its pin in the channel (the W2 lesson, tools/
v41_w2_romac_pnr.py hook).  The W1 slot gives each macro half of a 158.544 um strip (79.272 um) at the
120.96 um row pitch; LOGIC_W is set by the element's synthesised logic area at a placeable density and the
difference is recorded against that slot.  Ports (x stream, configuration, partial out) enter on the south edge
under the logic strip, as the column's x broadcast and result return run vertically.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import v41_w2_romac_pnr as W2  # noqa: E402

MACRO_DIR = "physical/asap7_memory_macros"
ROM = ("ot_rom_8192x274_m8", 125.712, 119.340)
ROM4K = ("ot_rom_4096x274_m8", 125.28, 62.91)          # PP: two per macro slot, read alternately (ping-pong)
PP_GAP = 0.0                                          # stacked 4096-word macros abut (a sub-halo sliver cannot be legalised)
SOURCES_FAST = ["rtl/v41rom/ot_v41_fadd.sv", "rtl/common/ot_prefix.sv", "rtl/v41rom/ot_v41_bterm2.sv", "rtl/v41rom/ot_v41_chain2.sv",
                "rtl/v41rom/ot_v41_segtree2.sv"]
MARGIN, CH, GAP = 2.16, 12.0, 4.0
W1_HALF_STRIP_UM = 158.544 / 2
W1_ROW_PITCH_UM = 120.96
SOURCES = ["rtl/v41rom/ot_v41_rom_elem_q.sv", "rtl/v41rom/ot_v41_rom_elem.sv", "rtl/v41rom/ot_v41_bterm.sv", "rtl/v41rom/ot_v41_chain.sv",
           "rtl/v41rom/ot_v41_segtree.sv", "rtl/v41rom/ot_v41_bf16_lanes.sv", "rtl/hdc/ot_hdc_fpu.sv",
           "rtl/hdc/ot_hdc_fp32_mul_pipe.sv", "rtl/hdc/ot_hdc_delay.sv", "rtl/hdc/ot_hdc_cg.sv", "rtl/proto/ot_fp32_add_rne_pipe.sv",
           f"{MACRO_DIR}/ot_rom_8192x274_m8/ot_rom_8192x274_m8_bb.v"]


def plan(logic_w: float, pair: bool = False, wrapped: bool = False, outline=None, ch_o: float = 5.4,
         fast: bool = False, pp: bool = False) -> dict:
    """pair: a W1 pair column [ROM R0 | logic strip | ROM MY] sharing one front end (ot_v41_rom_elem NB = 2).
    outline (W, H): the block IS the pack's pair tile (W1 pitch, no margin, no pin channel): channels of ch_o
    beside each ROM edge hold the capture flops, the strip takes the rest, and the tiles abut."""
    rom, rw, rh = ROM4K if pp else ROM
    if pp:
        rh = 2 * rh + PP_GAP                          # a slot = two stacked 4096-word macros
    if outline:
        die_w, die_h = outline
        x_rom = ch_o
        x_logic0 = x_rom + rw + ch_o
        logic_w = die_w - 2 * rw - 4 * ch_o
        x_rom1 = x_logic0 + logic_w + ch_o
        y_rom = round((die_h - rh) / 2, 3)
        margin = 0.0
    else:
        die_h = W2.snap(2 * MARGIN + 2 * GAP + rh, 0.27)
        x_rom = MARGIN + CH
        x_logic0 = x_rom + rw + CH
        x_rom1 = x_logic0 + logic_w + CH
        die_w = W2.snap((x_rom1 + rw + CH if pair else x_logic0 + logic_w) + MARGIN, 0.054)
        y_rom = MARGIN + GAP
        margin = MARGIN
    pre = "u_e." if wrapped else ""
    macros = []
    for mb, (x, orient) in enumerate([(x_rom, "R0")] + ([(x_rom1, "MY")] if pair else [])):
        if pp:
            for k in (0, 1):
                macros.append({"inst": f"{pre}g_mac[{mb}].g_pp.u_rom{k}", "master": ROM4K, "x": x,
                               "y": y_rom + k * (ROM4K[2] + PP_GAP), "orient": orient if k == 0 else
                               {"R0": "MX", "MY": "R180"}[orient], "capture": True})
        else:
            macros.append({"inst": f"{pre}g_mac[{mb}].g_one.u_rom", "master": ROM, "x": x, "y": y_rom,
                           "orient": orient, "capture": True})
    return {"case": "w10_elem_pair" if pair else "w10_elem", "top": "ot_v41_rom_elem", "die_um": [die_w, die_h],
            "logic_region_um": [round(x_logic0, 3), margin, round(x_logic0 + logic_w, 3), die_h - margin],
            "margin_um": margin, "outline": bool(outline),
            "pin_span_um": [round(x_logic0, 3), round(x_logic0 + logic_w, 3)],
            "macros": macros, "pair": pair, "wrapped": wrapped,
            "sources": SOURCES + (SOURCES_FAST if (fast or pp) else [])
            + ([f"{MACRO_DIR}/ot_rom_4096x274_m8/ot_rom_4096x274_m8_bb.v"] if pp else []),
            "macro_views": [rom] + (["ot_rom_8192x274_m8"] if pp else []), "fast": fast, "pp": pp,
            "w1_slot_um": [round((2 * rw if pair else rw) + (2 if pair else 1) * W1_HALF_STRIP_UM, 3), W1_ROW_PITCH_UM],
            "w1_slot_logic_um2": round(W1_HALF_STRIP_UM * W1_ROW_PITCH_UM, 1)}


def hook_name(p: dict) -> str:
    """The hook fixes macro positions, which depend on the logic width for a pair: the width is in the name."""
    lw = int(round(p["logic_region_um"][2] - p["logic_region_um"][0]))
    tile = f"_tile{int(round(p['die_um'][0]))}x{int(round(p['die_um'][1]))}" if p.get("outline") else ""
    return (f"physical/abi3/v41_w10_elem{'_pair' if p['pair'] else ''}{'_q' if p['wrapped'] else ''}"
            f"{'_pp' if p.get('pp') else ''}{f'_lw{lw}' if p['pair'] else ''}{tile}_place.tcl")


def hook_tcl(p: dict) -> str:
    t = W2.hook_tcl(p)
    # the element's words use 272 of the macro's 274 output bits: rd_out[273:272] have no capture flop
    # PP: a bank's capture flop loads only when its word arrives, so an enable gate may sit between pin and flop:
    # look one cell further before calling the bit unused
    t = t.replace('if {$ff eq {}} { error "capture flop missing on [$net getName]" }',
                  'if {$ff eq {}} {\n'
                  '            foreach o [$net getITerms] {\n'
                  '                set oi [$o getInst]\n'
                  '                if {$oi eq $inst} { continue }\n'
                  '                foreach ot [$oi getITerms] {\n'
                  '                    if {![$ot isOutputSignal]} { continue }\n'
                  '                    set n2 [$ot getNet]\n'
                  '                    if {$n2 eq "NULL" || $n2 eq ""} { continue }\n'
                  '                    foreach o2 [$n2 getITerms] {\n'
                  '                        if {[string match *DFF* [[[$o2 getInst] getMaster] getName]]} { set ff [$o2 getInst]; break }\n'
                  '                    }\n'
                  '                    if {$ff ne {}} { break }\n'
                  '                }\n'
                  '                if {$ff ne {}} { break }\n'
                  '            }\n'
                  '        }\n'
                  '        if {$ff eq {}} { incr nunused; continue }')
    t = t.replace("set nfixed 0", "set nfixed 0\nset nunused 0")
    nm = sum(1 for m in p['macros'] if m['capture'])
    # rd_out[273:272] are unused (2 per macro); synthesis may drop a few more constant or merged bits
    t = t.replace(f"if {{$nfixed != {274 * nm}}}",
                  f"if {{$nfixed + $nunused != {274 * nm} || $nunused > {4 * nm}}}")
    return t.replace("W2 V4.1 w10_elem ROM/MAC neighborhood (tools/v41_w2_romac_pnr.py)",
                     "W10 V4.1 ROM-array element (tools/v41_w10_elem_pnr.py; hook body from tools/v41_w2_romac_pnr.py)") \
            .replace("OT_W2_ROMAC_PLACE", "OT_W10_ELEM_PLACE")


def argv(p: dict, tag: str, keep: str, output: str, density: float, params=(), stop=None,
         setup_only=False, hold_ns=0.025, period=0.92, corner=None) -> list[str]:
    w, h = p["die_um"]
    top = "ot_v41_rom_elem_q" if p["wrapped"] else p["top"]      # an FP8/FP4 macro has no BF16 x port
    params = [q for q in params if not (p["wrapped"] and q.startswith("BF16="))]
    a = ["tools/run_abi3_physical.py", "--view", "asap7", "--top", top]
    params = list(params) + (["FAST=1"] if p.get("fast") else []) + (["PP=1"] if p.get("pp") else [])
    for s in p["sources"]:
        a += ["--source", s]
    a += ["--clock-period-ns", f"{period:g}", "--clock-uncertainty-ns", "0.06", "--io-delay-fraction", "0.2",
          "--stages", "pnr", "--die-area", "0", "0", f"{w:g}", f"{h:g}",
          "--core-area", f"{p['margin_um']:g}", f"{p['margin_um']:g}", f"{w - p['margin_um']:g}", f"{h - p['margin_um']:g}",
          "--place-density", f"{density:g}", "--macro-place-halo", "2", "2",
          *(["--pin-region", f"^(p|busy|fault).*=top:{p['pin_span_um'][0]:g}-{p['pin_span_um'][1]:g}",
             "--pin-region", f"^(clk|rst|cfg|go|x).*=bottom:{p['pin_span_um'][0]:g}-{p['pin_span_um'][1]:g}"]
            if p.get("outline") else
            ["--pin-region", f".*=bottom:{p['pin_span_um'][0]:g}-{p['pin_span_um'][1]:g}"]),
          "--max-transition-ns", "0.32", "--slew-margin-percent", "40", "--hold-margin-ns", "0.02",
          "--step-tcl", f"POST_MACRO_PLACE={hook_name(p)}",
          "--step-tcl", "POST_DETAIL_PLACE=physical/abi3/check_pg_before_route.tcl",
          "--orfs-var", "PDN_TCL=/src/tools/chip_assembly/tcl/pdn_w10_elem_m7.tcl",
          "--nickname-tag", tag, "--keep-workdir", keep, "--output", output]
    if p.get("pp"):
        a += ["--sdc-append", "physical/abi3/v41_w10_elem_pp_multicycle.sdc"]
    for m in p["macro_views"][:1]:
        a += ["--macro-view", f"{m}={MACRO_DIR}/{m}"]
    for q in params:
        a += ["--param", q]
    if stop:
        a += ["--pnr-stop-after", stop]
    if corner:
        a += ["--orfs-corner", corner]
    if setup_only:
        a += ["--clock-uncertainty-setup-only"]
    elif hold_ns is not None:
        a += ["--clock-uncertainty-hold-ns", f"{hold_ns:g}"]
    return a


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--logic-w", type=float, default=120.0)
    ap.add_argument("--density", type=float, default=0.6)
    ap.add_argument("--write-hook", action="store_true")
    ap.add_argument("--print", action="store_true")
    ap.add_argument("--tag", default="w10_elem")
    ap.add_argument("--keep", default="/tmp/claude-1000/w10out/w10_elem_work")
    ap.add_argument("--output", default="results/physical_abi3/asap7/chip/v41_w10_elem/elem_physical.json")
    ap.add_argument("--param", action="append", default=[], help="RTL parameter, e.g. BF16=1")
    ap.add_argument("--pair", action="store_true", help="a W1 macro pair sharing one front end (NB=2)")
    ap.add_argument("--outline", type=float, nargs=2, metavar=("W", "H"),
                    help="harden the pair as exactly the pack tile W x H um (abutting, no margins or pin channel)")
    ap.add_argument("--channel", type=float, default=5.4, help="with --outline: capture channel beside each ROM edge")
    ap.add_argument("--stop-after", choices=["floorplan", "cts", "finish"], help="timing iteration: stop the flow after CTS")
    ap.add_argument("--hold-uncertainty-ns", type=float, default=0.025,
                    help="hold clock uncertainty (project SDC policy: 60 ps setup / 25 ps hold)")
    ap.add_argument("--setup-only-uncertainty", action="store_true",
                    help="60 ps uncertainty on setup only (W5 semantics); the unified default also times hold "
                         "with it, which costs ~16k hold buffers per element")
    ap.add_argument("--fast", action="store_true", help="the 1.2 GHz element pipeline (FAST=1)")
    ap.add_argument("--pp", action="store_true", help="ping-pong 2 x ot_rom_4096x274_m8 per macro slot (PP=1)")
    ap.add_argument("--period", type=float, default=0.92, help="clock period, ns")
    ap.add_argument("--corner", choices=["TC", "WC", "BC"], help="ORFS primary corner (sign-off: WC)")
    ap.add_argument("--no-wrap", dest="wrap", action="store_false",
                    help="FP8/FP4: harden ot_v41_rom_elem itself (with the unused BF16 x port) instead of ot_v41_rom_elem_q")
    a = ap.parse_args()
    p = plan(a.logic_w, a.pair, wrapped=not any(q.startswith("BF16=1") for q in a.param) and a.wrap,
             outline=a.outline, ch_o=a.channel, fast=a.fast, pp=a.pp)
    if a.pair and "NB=2" not in a.param:
        a.param.append("NB=2")
    if a.write_hook or a.print:
        (ROOT / hook_name(p)).write_text(hook_tcl(p))      # the hook always matches the plan it is run with
    if a.print:
        print(json.dumps({"plan": p, "argv": argv(p, a.tag, a.keep, a.output, a.density, a.param, a.stop_after,
                                                     a.setup_only_uncertainty, a.hold_uncertainty_ns,
                                                     a.period, a.corner)}, indent=1))


if __name__ == "__main__":
    main()
