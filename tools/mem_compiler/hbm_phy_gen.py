#!/usr/bin/env python3
"""HBM3E PHY + memory controller hard-macro abstract for the HBM comparator.

The PHY is licensed IP, not something this repository can compile, so this
writes only what a full-chip flow needs to reserve and connect it:

* ``ot_hbm3e_phy.lef``: the footprint along the die edge, the controller-side
  signal pins on M5 along the core-facing (top) edge, VDD/VSS as M4 straps
  (the ASAP7 macro PDN grid reaches them with M4-M5 vias, as for the memory
  macros), and M1-M4 obstructions.  The package side -- 1,024 DQ plus
  command/address, clocks and the bump field -- is NOT in the abstract: it
  lies under the macro in the micro-bump field and is a blackbox to the
  core flow.
* ``ot_hbm3e_phy_{tt,ss,ff}.lib``: interface timing at the controller-side
  boundary only (registered outputs, input setup/hold at the controller
  clock); the DRAM-side timing lives in the functional model.
* ``ot_hbm3e_phy_bb.v``: the blackbox.  The functional/timing model of the
  same interface is ``rtl/hdc/kv/ot_hdc_hbm_model.sv`` with NPC = 32.
* ``ot_hbm3e_phy.json``: datasheet, every number graded.

Controller-side interface = the one ``ot_hdc_kv_stream`` drives and
``ot_hdc_hbm_model`` serves: one request port (valid/ready, read of ``len``
32-byte sectors or a one-sector write, tag) and one response port per
pseudo-channel (valid/ready, tag, beat, 256-bit sector).

    python3 tools/mem_compiler/hbm_phy_gen.py --out physical/asap7_memory_macros
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
from views import Pin, Timing, blackbox_verilog, write_liberty  # noqa: E402

NAME = "ot_hbm3e_phy"
GENERATOR_VERSION = "1.0"

PUBLISHED = {
    "hbm3_interface": {
        "value": {"dq_bits": 1024, "channels": 16, "pseudo_channels": 32, "pseudo_channel_dq_bits": 32,
                  "burst_length": 8, "sector_bytes": 32},
        "grade": "published",
        "source": "JEDEC JESD238 (HBM3): 1,024-bit interface as 16 independent 64-bit channels, each two 32-bit "
                  "pseudo-channels, BL8; the same organisation rtl/hdc/kv/ot_hdc_hbm_model.sv models",
    },
}


def tech(path: str) -> dict[str, Any]:
    node: Any = asap7.technology()
    for k in path.split("."):
        node = node[k]
    return node


def pins(npc: int, aw: int, tagw: int, lenw: int, beatw: int, dw: int) -> list[Pin]:
    p = [Pin("clk", 1, "input", "clock"), Pin("rst_n", 1, "input", "control"),
         Pin("req_v", 1, "input", "control"), Pin("req_rdy", 1, "output", "control"),
         Pin("req_we", 1, "input", "control"), Pin("req_addr", aw, "input", "control"),
         Pin("req_len", lenw, "input", "control"), Pin("req_tag", tagw, "input", "control"),
         Pin("req_wdata", dw, "input", "data_in"),
         Pin("rsp_v", npc, "output", "control"), Pin("rsp_rdy", npc, "input", "control"),
         Pin("rsp_tag", npc * tagw, "output", "control"), Pin("rsp_beat", npc * beatw, "output", "control"),
         Pin("rsp_data", npc * dw, "output", "data_out")]
    return p


def write_lef(w: float, h: float, plist: list[Pin], pitch: float) -> tuple[str, dict[str, Any]]:
    L = ["# OpenTallas tools/mem_compiler/hbm_phy_gen.py: HBM3E PHY + controller hard-macro ABSTRACT",
         "# controller-side pins only; the package side (DQ, CA, clocks, bumps) is a blackbox under the macro",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {NAME}",
         f"  FOREIGN {NAME} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    bits = [(p, b) for p in plist for b in p.bits()]
    x0 = round(max(2.0, (w - len(bits) * pitch) / 2.0), 3)      # pin block centred on the core edge
    pw, pl = 0.024, 0.192
    for i, (p, b) in enumerate(bits):
        x = x0 + i * pitch
        L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
              "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
              "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {h - pl:.3f} {x + pw:.3f} {h:.3f} ;", "    END",
              f"  END {b}"]
    span = len(bits) * pitch
    sw, sp = 0.288, 2.4
    straps: dict[str, list[float]] = {"VDD": [], "VSS": []}
    y, k = 1.0, 0
    while y + sw < h - 1.0:
        straps["VDD" if k % 2 == 0 else "VSS"].append(y)
        y += sp / 2
        k += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        L += [f"      RECT 0.500 {yy:.3f} {w - 0.5:.3f} {yy + sw:.3f} ;" for yy in straps[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3", "M4"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    L += ["    LAYER M5 ;", f"    RECT 0 0 {w:.3f} {h - 0.4:.3f} ;"]
    L += ["  END", f"END {NAME}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", {"signal_pins": len(bits), "pin_span_um": round(span, 3),
                                   "pin_pitch_um": pitch, "pin_layer": "M5", "pin_edge": "top (core-facing)",
                                   "pin_block_x_um": [x0, round(x0 + span, 3)], "fits_on_edge": x0 + span <= w - 2.0}


def generate(out: Path | None, npc: int = 32, aw: int = 31, tagw: int = 16, lenw: int = 5, beatw: int = 4,
             dw: int = 256) -> dict[str, Any]:
    area = tech("hbm.hbm3e.phy_area_mm2_per_stack")
    beach = tech("hbm.hbm3e.stack_beachfront_mm")
    bw = tech("hbm.hbm3e.stack_bandwidth_bytes_s")
    cap = tech("hbm.hbm3e.stack_capacity_bytes")
    energy = tech("energy.hbm_j_per_byte")
    iface = PUBLISHED["hbm3_interface"]["value"]
    if npc != iface["pseudo_channels"] or dw != iface["pseudo_channel_dq_bits"] * iface["burst_length"]:
        raise SystemExit("npc/dw must match one HBM3 stack (32 pseudo-channels, 32 bits x BL8 = 256-bit sectors)")
    need_aw = math.ceil(math.log2(cap["value"] / iface["sector_bytes"]))
    if aw < need_aw:
        raise SystemExit(f"address width {aw} cannot reach {cap['value']:.3g} B of 32-byte sectors ({need_aw} bits)")
    w_um = beach["value"] * 1000.0
    h_um = area["value"] * 1e6 / w_um
    w_um = asap7.snap_up(w_um, asap7.METAL["width_snap_um"])
    h_um = asap7.snap_up(h_um, asap7.METAL["height_snap_um"])
    plist = pins(npc, aw, tagw, lenw, beatw, dw)
    lef, pin_info = write_lef(w_um, h_um, plist, 0.192)
    cal = asap7.calibration()
    per_corner = {}
    for c in asap7.CORNERS:
        k = cal["corners"][c]
        fo4 = k["fo4_ps"]
        per_corner[c] = Timing(
            corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
            clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
            out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4, hold_ps=k["dff_hold_ps"] + fo4,
            min_period_ps=1000.0, min_pulse_ps=400.0,
            read_energy_fj=energy["value"] * 1e15 * iface["sector_bytes"], write_energy_fj=0.0,
            leakage_nw=0.0, pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0,
            breakdown={"fo4_ps": fo4})
    sheet: dict[str, Any] = {
        "schema": "opentallas.hbm-phy-abstract.v1",
        "generator": f"tools/mem_compiler/hbm_phy_gen.py v{GENERATOR_VERSION}",
        "kind": "hbm_phy_abstract",
        "name": NAME,
        "footprint": {
            "width_um": w_um, "height_um": h_um, "area_mm2": w_um * h_um / 1e6,
            "width_basis": {"value_mm": beach["value"], "grade": beach["grade"],
                            "source": "configs/hardware/technology.json hbm.hbm3e.stack_beachfront_mm"},
            "area_basis": {"value_mm2": area["value"], "grade": area["grade"],
                           "source": "configs/hardware/technology.json hbm.hbm3e.phy_area_mm2_per_stack",
                           "note": area["note"]},
            "depth_grade": "derived from two assumed values: area / beachfront",
        },
        "interface": {
            "hbm3": PUBLISHED["hbm3_interface"],
            "controller_side": {"pseudo_channels": npc, "sector_bits": dw, "address_bits": aw,
                                "address_basis": f"ceil(log2(stack capacity {cap['value']:.3g} B / 32 B))",
                                "tag_bits": tagw, "len_bits": lenw, "beat_bits": beatw,
                                "protocol": "rtl/hdc/kv/ot_hdc_hbm_model.sv request/response ports",
                                "grade": "defined here (the repository's own controller interface), not DFI 5.x"},
            "package_side": "1,024 DQ + CA + clocks under the macro in the micro-bump field: blackbox, not in the LEF",
            "stack_bandwidth": {"value_bytes_s": bw["value"], "grade": bw["grade"],
                                "source": "configs/hardware/technology.json hbm.hbm3e.stack_bandwidth_bytes_s"},
            "controller_clock_mhz": {"value": 1000.0, "grade": "assumed",
                                     "note": "the core clock the HBM model's time base assumes (CLK_PS = 1000)"},
        },
        "pins": pin_info,
        "timing": {c: asdict(t) for c, t in per_corner.items()},
        "timing_grade": "assumed: registered boundary (ASAP7 flop clock-to-Q / setup plus 3 FO4 of PHY-side "
                        "logic); the request/response latencies (10 ns each) and all DRAM timing are in "
                        "ot_hdc_hbm_model.sv, not in the liberty",
        "energy_per_sector_fj": {"value": energy["value"] * 1e15 * iface["sector_bytes"], "grade": energy["grade"],
                                 "source": "configs/hardware/technology.json energy.hbm_j_per_byte x 32 B "
                                           "(whole-path HBM energy incl. controller and PHY, A100-measured)"},
        "claim_boundary": "a placement and connection abstract for licensed IP; no PHY design, no GDS, no "
                          "signal-integrity or bump-map analysis; footprint and timing are assumed",
    }
    if out is not None:
        d = out / NAME
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{NAME}.lef").write_text(lef)
        comment = "HBM3E PHY + controller abstract, controller-side boundary timing only (assumed)"
        for c, t in per_corner.items():
            (d / f"{NAME}_{c}.lib").write_text(write_liberty(NAME, t, plist, w_um * h_um, None, comment))
        (d / f"{NAME}_bb.v").write_text(blackbox_verilog(NAME, plist, comment + "; functional model: "
                                                          "rtl/hdc/kv/ot_hdc_hbm_model.sv (NPC=32)"))
        files = sorted(p.name for p in d.iterdir() if p.name != f"{NAME}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{NAME}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


# ---------------------------------------------------------------------------------------------------------
# The adopted V4.1 die's stack interface (rtl/chip/ot_chip_v41x_hbm3e_phy.sv, as ot_chip_v41x_die.sv
# instantiates it: KTAGW = 17, NPC_W = 8, LWIN = 10): 32 independent K request / response pseudo-channel
# ports, the QE weight W port, status.  The v1 abstract above has ONE request port and cannot stand in
# for it (docs/V41X_DIE_PHYSICAL_PREFLIGHT.md).
V41X = "ot_hbm3e_phy_v41x"
V41X_WINDOW_SPAN_UM = (20.0, 195.0)     # K pins inside each pseudo-channel's (edge / 32) window
V41X_W_SPAN_UM = (205.0, 360.0)         # W-port pins, windows 0..7 (one W pseudo-channel each)


def v41x_pins(npc: int = 32, ktagw: int = 17, npc_w: int = 8, lwin: int = 10,
               k_aw: int = 28) -> tuple[list[Pin], dict]:
    """(the port list in declaration order, the (window, group) of every bit)."""
    k = [("k_v", 1, "input"), ("k_rdy", 1, "output"), ("k_addr", k_aw, "input"), ("k_len", 4, "input"),
         ("k_tag", ktagw, "input"), ("k_we", 1, "input"), ("k_wdata", 256, "input"), ("k_wstrb", 32, "input"),
         ("k_wr_done", 1, "output"), ("kr_v", 1, "output"), ("kr_rdy", 1, "input"), ("kr_tag", ktagw, "output"),
         ("kr_beat", 4, "output"), ("kr_data", 256, "output")]
    w = [("w_v", 1, "input", "shared"), ("w_rdy", 1, "output", "shared"), ("w_addr", 24, "input", "shared"),
         ("w_len", 6, "input", "shared"), ("w_tag", lwin, "input", "shared"), ("w_room", 1, "output", "pc"),
         ("wr_v", 1, "output", "pc"), ("wr_rdy", 1, "input", "pc"), ("wr_tag", lwin, "output", "pc"),
         ("wr_beat", 5, "output", "pc"), ("wr_data", 256, "output", "pc")]
    kind = {"input": "data_in", "output": "data_out"}
    plist = [Pin("clk", 1, "input", "clock"), Pin("rst_n", 1, "input", "control")]
    plist += [Pin(n, npc * b, d, kind[d]) for n, b, d in k]
    plist += [Pin(n, (npc_w if s == "pc" else 1) * b, d, kind[d]) for n, b, d, s in w]
    plist += [Pin("k_oor", 1, "output", "control"), Pin("w_oor", 1, "output", "control"),
              Pin("refreshes", 64, "output", "control"),
              Pin("w_reads", 32, "output", "control")]
    place: dict[str, tuple[int, str]] = {}
    for n, b, _ in k:
        for p in range(npc):
            for i in range(b):
                place[f"{n}[{p * b + i}]" if npc * b > 1 else n] = (p, "k")
    for n, b, _, s in w:
        reps = npc_w if s == "pc" else 1
        for c in range(reps):
            for i in range(b):
                place[f"{n}[{c * b + i}]" if reps * b > 1 else n] = (c, "w")
    for nm in (["clk", "rst_n", "k_oor", "w_oor"] + [f"refreshes[{i}]" for i in range(64)]
               + [f"w_reads[{i}]" for i in range(32)]):
        place[nm] = (npc // 2, "w")
    return plist, place


def write_lef_v41x(w: float, h: float, plist: list[Pin], place: dict, npc: int,
                   pitch: float, name: str = V41X) -> tuple[str, dict[str, Any]]:
    L = ["# OpenTallas tools/mem_compiler/hbm_phy_gen.py --variant v41x: HBM3E PHY + controller ABSTRACT for the",
         "# adopted V4.1 die (rtl/chip/ot_chip_v41x_hbm3e_phy.sv port list); controller-side pins only",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}",
         f"  FOREIGN {name} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    win = w / npc
    cursor: dict[tuple[int, str], float] = {}
    pw, pl = 0.024, 0.192
    worst = 0.0
    for p in plist:
        for b in p.bits():
            wi, grp = place[b]
            lo, hi = V41X_WINDOW_SPAN_UM if grp == "k" else V41X_W_SPAN_UM
            x = cursor.get((wi, grp), round(wi * win + lo, 3))
            if x + pw > wi * win + hi:
                raise SystemExit(f"{b}: window {wi} group {grp} overflows at {x:.3f} um")
            cursor[(wi, grp)] = round(x + pitch, 3)
            worst = max(worst, x - (wi * win + lo))
            L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
                  "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
                  "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {h - pl:.3f} {x + pw:.3f} {h:.3f} ;",
                  "    END", f"  END {b}"]
    sw, sp = 0.288, 2.4
    straps: dict[str, list[float]] = {"VDD": [], "VSS": []}
    y, kk = 1.0, 0
    while y + sw < h - 1.0:
        straps["VDD" if kk % 2 == 0 else "VSS"].append(y)
        y += sp / 2
        kk += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        L += [f"      RECT 0.500 {yy:.3f} {w - 0.5:.3f} {yy + sw:.3f} ;" for yy in straps[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3", "M4"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    L += ["    LAYER M5 ;", f"    RECT 0 0 {w:.3f} {h - 0.4:.3f} ;"]
    L += ["  END", f"END {name}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", {
        "signal_pins": sum(pp.width for pp in plist), "pin_pitch_um": pitch, "pin_layer": "M5",
        "pin_edge": "top (core-facing)", "pseudo_channel_window_um": round(win, 3),
        "k_pins_in_window_um": list(V41X_WINDOW_SPAN_UM), "w_pins_in_window_um": list(V41X_W_SPAN_UM),
        "longest_window_fill_um": round(worst + pitch, 3),
        "placement": "pseudo-channel p's K request and response bits in [p*window + 20, p*window + 195] um; W "
                     "pseudo-channel c's bits (c < 8) in [c*window + 205, c*window + 360] um, the shared W request "
                     "in window 0's; clk, rst_n and status in window 16's W span",
        "matches": "rtl/chip/ot_chip_v41x_hbm3e_phy.sv ports at KTAGW = 17, NPC_W = 8, LWIN = 10 "
                   "(ot_chip_v41x_die.sv g_hbm[s].u_hbm) and the pin windows of the karb strip "
                   "(tools/v41x_die_pnr.py karb_strip)"}


def generate_v41x(out: Path | None, npc: int = 32, k_aw: int = 28) -> dict[str, Any]:
    if k_aw not in (28, 30):
        raise ValueError("K address width must be the reduced 28-bit or full packed 30-bit profile")
    name = V41X if k_aw == 28 else f"{V41X}_aw30"
    area = tech("hbm.hbm3e.phy_area_mm2_per_stack")
    beach = tech("hbm.hbm3e.stack_beachfront_mm")
    w_um = asap7.snap_up(beach["value"] * 1000.0, asap7.METAL["width_snap_um"])
    h_um = asap7.snap_up(area["value"] * 1e6 / (beach["value"] * 1000.0), asap7.METAL["height_snap_um"])
    plist, place = v41x_pins(npc, k_aw=k_aw)
    lef, pin_info = write_lef_v41x(w_um, h_um, plist, place, npc, 0.192, name=name)
    cal = asap7.calibration()
    energy = tech("energy.hbm_j_per_byte")
    per_corner = {}
    for c in asap7.CORNERS:
        k = cal["corners"][c]
        fo4 = k["fo4_ps"]
        per_corner[c] = Timing(
            corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
            clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
            out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4, hold_ps=k["dff_hold_ps"] + fo4,
            min_period_ps=900.0, min_pulse_ps=360.0,
            read_energy_fj=energy["value"] * 1e15 * 32, write_energy_fj=0.0,
            leakage_nw=0.0, pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0,
            breakdown={"fo4_ps": fo4})
    sheet: dict[str, Any] = {
        "schema": "opentallas.hbm-phy-abstract.v1",
        "generator": f"tools/mem_compiler/hbm_phy_gen.py --variant v41x v{GENERATOR_VERSION}",
        "kind": "hbm_phy_abstract", "name": name,
        "footprint": {"width_um": w_um, "height_um": h_um, "area_mm2": w_um * h_um / 1e6,
                      "basis": "the technology.json entries of ot_hbm3e_phy (beachfront 12.0 mm, 10 mm2 per stack); "
                               "results/arch/v41_die_assembly.json draws each PHY 12.0001 x 0.8335 mm"},
        "interface": {"port_list": "rtl/chip/ot_chip_v41x_hbm3e_phy.sv: K, 32 pseudo-channel request / response "
                                   "ports (ot_hdc_v41x_idx_hbm protocol); W, the QE weight port (ot_hdc_hbm_model "
                                   "protocol, 8 response pseudo-channels); status",
                      "parameters": {"NPC": npc, "KTAGW": 17, "NPC_W": 8, "LWIN": 10,
                                     **({"K_AW": k_aw} if k_aw != 28 else {})},
                      "controller_clock_mhz": {"value": 1087.0, "grade": "assumed",
                                               "note": "the die clock; min_period 900 ps"}},
        "pins": pin_info,
        "timing": {c: asdict(t) for c, t in per_corner.items()},
        "timing_grade": "assumed: registered boundary, as ot_hbm3e_phy (ASAP7 flop clock-to-Q / setup + 3 FO4)",
        "claim_boundary": "a placement and connection abstract for licensed IP; footprint and boundary timing are "
                          "assumed, the port list is the adopted RTL's",
    }
    if out is not None:
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(lef)
        comment = ("HBM3E PHY + controller abstract for the adopted V4.1 die, controller-side boundary timing "
                   "only (assumed)")
        for c, t in per_corner.items():
            (d / f"{name}_{c}.lib").write_text(write_liberty(name, t, plist, w_um * h_um, None, comment))
        (d / f"{name}_bb.v").write_text(blackbox_verilog(name, plist, comment + "; functional model: "
                                                         "rtl/chip/ot_chip_v41x_hbm3e_phy.sv"))
        files = sorted(p.name for p in d.iterdir() if p.name != f"{name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


# ---------------------------------------------------------------------------------------------------------
# v2 (W18): a LEGAL V4.1 abstract.  The v1 views above are kept unchanged as the historical, defective
# abstract that W1's pack check measured (results/floorplan/v41_pack_*.json legality.abstract_defects):
#   * every signal pin was off the M5 track: the pseudo-channel window origin wi * (edge / 32) is not on the
#     0.048 um grid (12,000.096 / 32 = 375.003 um), so the pins fell on 24 distinct phases and no macro origin
#     could put them all on track;
#   * VDD/VSS were M4 straps under a full M5 OBS, so the parent's M5 stripes could never reach them
#     (pdngen PDN-0006 in the platform strategy).
# v2 fixes both by construction and makes the shoreline a parameter:
#   * window pitch, window origins, span offsets and pin pitch are all multiples of the M5 track pitch
#     (0.048 um), and every pin rect starts on a multiple of 0.048, so its centre is on the M5 track
#     (offset 0.012) for any origin on the pack's 0.432 um joint grid, in R0 and MX; the width is a
#     multiple of 0.432 so MY/R180 keep the pins on track as well (asserted below);
#   * the macro obstructs M1-M4 only (as every catalog ROM/SRAM view); VDD/VSS are M4 straps centred on M4
#     tracks, which the parent reaches with M5 stripes and M4-M5 vias (the same ElementGrid connect the
#     catalog macros use).  M5 and above are left to the parent's power grid and over-the-macro routing;
#   * the core-facing edge is a parameter: HBM3E PHYs of ~8-9 mm per stack (GH100 precedent, below).
M5_TRACK_UM = 0.048
M5_TRACK_OFF_UM = 0.012
M4_TRACK_UM = 0.048
M4_TRACK_OFF_UM = 0.012
JOINT_X_UM = 0.432                      # lcm(0.054 placement site, 0.048 M5 track): the pack's macro x grid
V2_EDGE_BASIS = {
    "grade": "assumed",
    "value_mm": 8.5,
    "source": "NVIDIA GH100 (814 mm^2) places six HBM3 sites, three along each long edge of the die (NVIDIA "
              "H100 Tensor Core GPU Architecture whitepaper, 2022, die shot and 'up to 6 HBM3/HBM2e stacks'); "
              "with a ~33 mm long edge that leaves <= 11 mm of shoreline per stack including the keep-out "
              "between PHYs, so the PHY itself is taken as 8-9 mm (8.5 mm default, a parameter).  The "
              "technology table's 12.0 mm is the 11 mm HBM3E package edge plus keep-out, i.e. the package "
              "pitch on the interposer, not the die-side PHY",
}


def _n(v: float, q: float) -> int:
    k = round(v / q)
    if abs(k * q - v) > 1e-6:
        raise ValueError(f"{v} is not a multiple of {q}")
    return k


def write_lef_v41x_legal(w: float, h: float, plist: list[Pin], place: dict, npc: int, pitch: float,
                         name: str) -> tuple[str, dict[str, Any]]:
    """The V4.1 PHY abstract with every signal pin on the M5 track and PDN-reachable M4 power straps."""
    _n(w, JOINT_X_UM)
    _n(pitch, M5_TRACK_UM)
    win = math.floor(w / npc / M5_TRACK_UM) * M5_TRACK_UM          # window pitch on the track grid
    # K and W spans inside each window, packed from the window origin on the track grid.
    k_bits = sum(1 for b, (wi, g) in place.items() if wi == 0 and g == "k")
    w_bits = max(sum(1 for b, (wi, g) in place.items() if wi == c and g == "w") for c in range(npc))
    k_lo = 10 * M5_TRACK_UM * 2                                      # 0.96 um guard from the window edge
    k_hi = k_lo + k_bits * pitch
    w_lo = k_hi + 10 * M5_TRACK_UM * 2
    w_hi = w_lo + w_bits * pitch
    if w_hi + k_lo > win + 1e-9:
        raise SystemExit(f"{name}: {k_bits} K + {w_bits} W pins at {pitch} um need {w_hi + k_lo:.3f} um; "
                         f"window is {win:.3f} um (edge {w:.3f} / {npc})")
    L = ["# OpenTallas tools/mem_compiler/hbm_phy_gen.py --variant v41x_legal (v2): HBM3E PHY + controller",
         "# ABSTRACT for the adopted V4.1 die (rtl/chip/ot_chip_v41x_hbm3e_phy.sv); controller-side pins only.",
         "# Every signal pin centre is on an M5 track; VDD/VSS are M4 straps reachable from M5 (OBS M1-M4).",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}",
         f"  FOREIGN {name} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    cursor: dict[tuple[int, str], float] = {}
    pw, pl = 0.024, 0.192
    off_track = 0
    xs: list[float] = []
    for p in plist:
        for b in p.bits():
            wi, grp = place[b]
            lo, hi = (k_lo, k_hi) if grp == "k" else (w_lo, w_hi)
            x = cursor.get((wi, grp), round(wi * win + lo, 3))
            if x + pw > wi * win + hi + 1e-9:
                raise SystemExit(f"{b}: window {wi} group {grp} overflows at {x:.3f} um")
            cursor[(wi, grp)] = round(x + pitch, 3)
            xc = x + pw / 2
            if abs(((xc - M5_TRACK_OFF_UM) / M5_TRACK_UM) - round((xc - M5_TRACK_OFF_UM) / M5_TRACK_UM)) > 1e-6:
                off_track += 1
            xs.append(x)
            L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
                  "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
                  "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {h - pl:.3f} {x + pw:.3f} {h:.3f} ;",
                  "    END", f"  END {b}"]
    if off_track:
        raise SystemExit(f"{name}: {off_track} pin centres off the M5 track")
    # VDD/VSS: 0.288 um M4 straps, centres on M4 tracks, alternating every 1.2 um (25 tracks), stopping
    # 2.4 um short of the pin edge so no strap sits under the pin band.
    sw, step = 0.288, 25 * M4_TRACK_UM
    y0 = M4_TRACK_OFF_UM + 21 * M4_TRACK_UM - sw / 2                 # centre on track 21 (1.02 um)
    straps: dict[str, list[float]] = {"VDD": [], "VSS": []}
    y, kk = y0, 0
    while y + sw < h - 2.4:
        straps["VDD" if kk % 2 == 0 else "VSS"].append(round(y, 3))
        y += step
        kk += 1
    for net, use in (("VDD", "POWER"), ("VSS", "GROUND")):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        L += [f"      RECT 0.480 {yy:.3f} {w - 0.48:.3f} {yy + sw:.3f} ;" for yy in straps[net]]
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3", "M4"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    L += ["  END", f"END {name}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", {
        "signal_pins": sum(pp.width for pp in plist), "pin_pitch_um": pitch, "pin_layer": "M5",
        "pin_edge": "top (core-facing)", "pseudo_channel_window_um": round(win, 3),
        "k_pins_in_window_um": [round(k_lo, 3), round(k_hi, 3)],
        "w_pins_in_window_um": [round(w_lo, 3), round(w_hi, 3)],
        "pins_off_m5_track": 0, "on_track_orientations": ["R0", "MX"], "pin_phases_mod_48nm": sorted({round(x * 1000) % 48 for x in xs}),
        "power": {"layer": "M4", "strap_width_um": sw, "strap_step_um": step,
                  "straps": {k: len(v) for k, v in straps.items()},
                  "obstructed_layers": ["M1", "M2", "M3", "M4"],
                  "reach": "the parent's M5 stripes over the macro, M4-M5 vias (catalog-macro ElementGrid)"},
        "placement": "pseudo-channel p's K request/response bits in [p*window + K span]; W pseudo-channel c's "
                     "bits (c < 8) in [c*window + W span], the shared W request in window 0's W span; clk, "
                     "rst_n and status in window 16's W span",
        "matches": "rtl/chip/ot_chip_v41x_hbm3e_phy.sv ports at KTAGW = 17, NPC_W = 8, LWIN = 10"}


def v41x_legal_name(k_aw: int, edge_mm: float) -> str:
    return f"{V41X}{'_aw30' if k_aw == 30 else ''}_e{edge_mm:g}".replace(".", "p")


def generate_v41x_legal(out: Path | None, edge_mm: float = V2_EDGE_BASIS["value_mm"], npc: int = 32,
                        k_aw: int = 30, area_mm2: float | None = None) -> dict[str, Any]:
    if k_aw not in (28, 30):
        raise ValueError("K address width must be the reduced 28-bit or full packed 30-bit profile")
    name = v41x_legal_name(k_aw, edge_mm)
    area = tech("hbm.hbm3e.phy_area_mm2_per_stack")
    a_mm2 = area["value"] if area_mm2 is None else area_mm2
    w_um = asap7.snap_up(edge_mm * 1000.0, JOINT_X_UM)
    h_um = asap7.snap_up(a_mm2 * 1e6 / w_um, 2.16)                  # lcm(0.27 row, 0.048 M4 track)
    plist, place = v41x_pins(npc, k_aw=k_aw)
    lef, pin_info = write_lef_v41x_legal(w_um, h_um, plist, place, npc, 0.192, name=name)
    cal = asap7.calibration()
    energy = tech("energy.hbm_j_per_byte")
    per_corner = {}
    for c in asap7.CORNERS:
        k = cal["corners"][c]
        fo4 = k["fo4_ps"]
        per_corner[c] = Timing(
            corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
            clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
            out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4, hold_ps=k["dff_hold_ps"] + fo4,
            min_period_ps=900.0, min_pulse_ps=360.0,
            read_energy_fj=energy["value"] * 1e15 * 32, write_energy_fj=0.0,
            leakage_nw=0.0, pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0,
            breakdown={"fo4_ps": fo4})
    sheet: dict[str, Any] = {
        "schema": "opentallas.hbm-phy-abstract.v2",
        "generator": f"tools/mem_compiler/hbm_phy_gen.py --variant v41x_legal --edge-mm {edge_mm:g} v2.0",
        "kind": "hbm_phy_abstract", "name": name,
        "supersedes": {"views": f"{V41X}{'_aw30' if k_aw == 30 else ''} (v1)",
                       "defects_fixed": ["22,237 signal pins off the M5 track (24 pin phases)",
                                         "M4 power under the macro's own M5 OBS (pdngen PDN-0006)"],
                       "v1_views_kept": "unchanged, as the historical abstract W1's records measured"},
        "footprint": {"width_um": w_um, "height_um": h_um, "area_mm2": w_um * h_um / 1e6,
                      "edge_basis": dict(V2_EDGE_BASIS, value_mm=edge_mm),
                      "area_basis": {"value_mm2": a_mm2, "grade": area["grade"] if area_mm2 is None else "assumed",
                                     "source": "configs/hardware/technology.json hbm.hbm3e.phy_area_mm2_per_stack"
                                     if area_mm2 is None else "--area-mm2", "note": area["note"]},
                      "depth": "area / edge, snapped up to 2.16 um"},
        "interface": {"port_list": "rtl/chip/ot_chip_v41x_hbm3e_phy.sv (as v1)",
                      "parameters": {"NPC": npc, "KTAGW": 17, "NPC_W": 8, "LWIN": 10, "K_AW": k_aw},
                      "controller_clock_mhz": {"value": 1087.0, "grade": "assumed",
                                               "note": "the die clock; min_period 900 ps"}},
        "pins": pin_info,
        "timing": {c: asdict(t) for c, t in per_corner.items()},
        "timing_grade": "assumed: registered boundary, as ot_hbm3e_phy (ASAP7 flop clock-to-Q / setup + 3 FO4)",
        "claim_boundary": "a placement and connection abstract for licensed IP; footprint and boundary timing are "
                          "assumed, the port list is the adopted RTL's",
    }
    if out is not None:
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(lef)
        comment = ("HBM3E PHY + controller abstract (v2, legal pins/PDN) for the adopted V4.1 die, controller-side "
                   "boundary timing only (assumed)")
        for c, t in per_corner.items():
            (d / f"{name}_{c}.lib").write_text(write_liberty(name, t, plist, w_um * h_um, None, comment))
        (d / f"{name}_bb.v").write_text(blackbox_verilog(name, plist, comment + "; functional model: "
                                                         "rtl/chip/ot_chip_v41x_hbm3e_phy.sv"))
        files = sorted(p.name for p in d.iterdir() if p.name != f"{name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=asap7.ROOT / "physical/asap7_memory_macros")
    ap.add_argument("--variant", choices=["v1", "v41x", "v41x_legal"], default="v1")
    ap.add_argument("--edge-mm", type=float, default=V2_EDGE_BASIS["value_mm"],
                    help="v41x_legal: core-facing PHY edge per stack (mm)")
    ap.add_argument("--area-mm2", type=float, default=None, help="v41x_legal: override the PHY area")
    ap.add_argument("--k-aw", type=int, default=28, help="V4.1 K sector address width: 28 reduced or 30 full")
    args = ap.parse_args()
    if args.variant == "v41x_legal":
        s = generate_v41x_legal(args.out, edge_mm=args.edge_mm, k_aw=args.k_aw if args.k_aw != 28 else 30,
                                area_mm2=args.area_mm2)
        f = s["footprint"]
        print(f"{s['name']}: {f['width_um']:.3f} x {f['height_um']:.3f} um ({f['area_mm2']:.2f} mm2), "
              f"{s['pins']['signal_pins']} pins, window {s['pins']['pseudo_channel_window_um']} um, "
              f"K {s['pins']['k_pins_in_window_um']} W {s['pins']['w_pins_in_window_um']}, "
              f"phases {s['pins']['pin_phases_mod_48nm']}")
        return 0
    if args.variant == "v41x":
        s = generate_v41x(args.out, k_aw=args.k_aw)
        f = s["footprint"]
        print(f"{s['name']}: {f['width_um']:.1f} x {f['height_um']:.1f} um ({f['area_mm2']:.2f} mm2), "
              f"{s['pins']['signal_pins']} controller-side pins, {s['pins']['pseudo_channel_window_um']} um windows")
        return 0
    s = generate(args.out)
    f = s["footprint"]
    print(f"{NAME}: {f['width_um']:.1f} x {f['height_um']:.1f} um ({f['area_mm2']:.2f} mm2), "
          f"{s['pins']['signal_pins']} controller-side pins spanning {s['pins']['pin_span_um']:.0f} um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
