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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=asap7.ROOT / "physical/asap7_memory_macros")
    args = ap.parse_args()
    s = generate(args.out)
    f = s["footprint"]
    print(f"{NAME}: {f['width_um']:.1f} x {f['height_um']:.1f} um ({f['area_mm2']:.2f} mm2), "
          f"{s['pins']['signal_pins']} controller-side pins spanning {s['pins']['pin_span_um']:.0f} um")
    return 0


if __name__ == "__main__":
    sys.exit(main())
