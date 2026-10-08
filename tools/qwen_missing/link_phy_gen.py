#!/usr/bin/env python3
"""Hard-macro abstracts for the Qwen ROM die's two link PHYs (qwen-missing 2026-10-07): die masters qfd_io_ucie and
qfd_io_serdes are licensed PHY IP plus our routed adapter (rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv).
This writes, per PHY, what the die flow needs to place and connect the IP (same conventions as
tools/mem_compiler/hbm_phy_gen.py):

  <name>.lef                 footprint, the adapter-side FDI pins on M5 along the core-facing (top) edge, VDD/VSS M4
                             straps (the M4-M5 macro grid reaches them), M1-M4 + M5 obstructions.  The package side
                             (bumps, lanes) is a blackbox under the macro.
  <name>_{ss,tt,ff}.lib      registered FDI boundary timing at the PHY's FDI clock (ASSUMED: ASAP7 flop clk->q /
                             setup + 3 FO4 of PHY-side logic, as the HBM PHY abstract).
  <name>_bb.v                blackbox; <name>_model.sv a cycle model (fixed TX->RX latency, loop-back pair in benches).
  <name>.json                datasheet, every number graded (published / derived / ASSUMED).

FDI (both PHYs, this repository's interface, not the UCIe FDI signal list): clk (the PHY's FDI clock, 1.0 GHz),
rst_n, tx_up (link trained, slow status), tx_v + tx_flit[FW-1:0] in, rx_v + rx_flit[FW-1:0] out, FW = 1,024 + credit
+ sequence bits of the adapter flit.

    python3 tools/qwen_missing/link_phy_gen.py --out physical/qwen_missing_phy
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))
import asap7  # noqa: E402
from views import Pin, Timing, blackbox_verilog, write_liberty  # noqa: E402

W = 1024
FDI_CLOCK_GHZ = 1.0


def flit_bits(rxd: int) -> int:
    return W + math.ceil(math.log2(rxd + 1)) + 9


PHYS = {
    "ot_qfd_ucie_x64_phy": dict(
        rxd=32,
        width_um=777.6, height_um=777.6,
        latency_cycles=4,
        published=[
            ("UCIe advanced-package transceiver, 3 nm CoWoS, IEEE JSSC 2026 (doi:10.1109/JSSC.2026.3651425; "
             "registry sct:r-ucie-jssc26)", "0.29 pJ/bit, 5.27 Tb/s/mm, 3.5 ns measured FDI-to-FDI latency, 16 Gb/s/pin"),
            ("D. Das Sharma et al., UCIe, IEEE Trans. CPMT 12(9):1423, 2022, Table I (registry sct:r-ucie-tcpmt)",
             "latency (Tx + Rx) < 2 ns including D2D adapter and PHY (FDI to bump and back); advanced reach <= 2 mm"),
            ("UCIe Consortium, Hot Chips 2023 tutorial (registry sct:r-ucie-hc23)", "0.3-0.6 pJ/b at Adv 16-32 GT/s")],
        derived={
            "lanes": "one x64 advanced module: 64 TX + 64 RX lanes at 16 GT/s = 1,024 Gb/s each way = the adapter's "
                     "1,024-bit flit payload per 1.0 GHz FDI cycle",
            "latency_cycles": "3.5 ns FDI-to-FDI (JSSC 2026, 16 Gb/s/pin) = 4 FDI cycles at 1.0 GHz",
            "energy_pj_per_bit": 0.29},
        assumed={
            "footprint": "777.6 x 777.6 um (0.60 mm2): two 388.8 um module-widths of shoreline (TX+RX bump field and "
                         "the D2D adapter), 2.63 Tb/s/mm of shoreline for 2.05 Tb/s both ways, half the JSSC 2026 "
                         "density; inside the r21 10 mm2 qfd_io_ucie reservation (the ledger's 4.2 TB/s full-edge "
                         "link is ~16 such modules; the RTL die bus carries 1,024 b a cycle each way, one module)",
            "fdi_clock": "1.0 GHz FDI clock (the link_ucie domain), flit = 1,024 b payload + credit + sequence",
            "boundary_timing": "registered FDI pins: ASAP7 flop clk->q / setup + 3 FO4"}),
    "ot_qfd_serdes_112g_x12_phy": dict(
        rxd=128,
        width_um=2400.0, height_um=1512.0,
        latency_cycles=223,
        published=[
            ("Credo, IEEE 802.3cd contribution (registry rack:physical_constants.kp4_fec_latency_ns / sct:r-sun3cd)",
             "RS(544,514) KP4 FEC ~198 ns; RS(272,257) ~99 ns"),
            ("D. Das Sharma et al., CXL, arXiv:2306.11227 (registry sct:r-cxl-survey)",
             "SERDES pin to application layer and back 21 ns (common refclk) / 25 ns (independent refclk)"),
            ("7 nm 112 Gb/s PAM4 LR transceiver, IEEE JSSC Jan 2021 (registry sct:r-serdes-jssc21)",
             "602 mW per channel excluding DSP"),
            ("112 Gb/s PAM4 transceiver with DSP, 5 nm, VLSI 2022 (registry sct:r-serdes-vlsi22)",
             "5.6 pJ/b per lane incl. analog and DSP"),
            ("configs/hardware/technology.json links.rom_board_serdes",
             "112 Gb/s PAM4 lanes, net of RS(544,514) and 256b/257b = 105.4 Gb/s a lane")],
        derived={
            "lanes": "12 x 112G PAM4 = 1,265 Gb/s net >= the adapter's 1,024 b per 1.0 GHz FDI cycle (81 % load)",
            "latency_cycles": "198 ns KP4 + 25 ns PHY/PCS = 223 ns = 223 FDI cycles at 1.0 GHz (one way)",
            "energy_pj_per_bit": 5.6,
            "rx_buffer": "RXD = 128 flits (one 4,096-element FP32 all-reduce message, 128 x 1,024 b) so a message "
                         "streams without a credit stall; full line rate needs RXD >= RTT ~ 460 flits (SRAM; "
                         "not taken: the per-token exchanges are message-latency bound)"},
        assumed={
            "footprint": "2,400 x 1,512 um (3.63 mm2) for 12 lanes = 0.30 mm2 a lane incl. PCS/FEC, inside the r21 "
                         "4.0 mm2 qfd_io_serdes reservation (no published per-lane area in the registry)",
            "fdi_clock": "1.0 GHz FDI clock (the link_serdes domain)",
            "boundary_timing": "registered FDI pins: ASAP7 flop clk->q / setup + 3 FO4"}),
}


def pins(fw: int) -> list[Pin]:
    return [Pin("clk", 1, "input", "clock"), Pin("rst_n", 1, "input", "control"),
            Pin("tx_up", 1, "output", "control"), Pin("tx_v", 1, "input", "control"),
            Pin("tx_flit", fw, "input", "data_in"), Pin("rx_v", 1, "output", "control"),
            Pin("rx_flit", fw, "output", "data_out")]


def write_lef(name: str, w: float, h: float, plist: list[Pin], pitch: float):
    L = [f"# OpenTallas tools/qwen_missing/link_phy_gen.py: {name} hard-macro ABSTRACT (licensed PHY IP; FDI side only)",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}",
         f"  FOREIGN {name} 0 0 ;", "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    bits = [(p, b) for p in plist for b in p.bits()]
    span = len(bits) * pitch
    if span > w - 4.0:
        raise SystemExit(f"{name}: {len(bits)} pins do not fit the {w} um edge at {pitch} um")
    x0 = round((w - span) / 2.0, 3)
    pw, pl = 0.024, 0.192
    for i, (p, b) in enumerate(bits):
        x = x0 + i * pitch
        L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
              "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
              "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {h - pl:.3f} {x + pw:.3f} {h:.3f} ;", "    END",
              f"  END {b}"]
    sw, sp = 0.288, 2.4
    straps = {"VDD": [], "VSS": []}
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
    L += ["  END", f"END {name}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", dict(signal_pins=len(bits), pin_pitch_um=pitch, pin_layer="M5",
                                     pin_edge="top (core-facing)", pin_block_x_um=[x0, round(x0 + span, 3)])


def model_sv(name: str, fw: int, lat: int) -> str:
    return f"""`timescale 1ns/1ps
// SIMULATION MODEL of the {name} hard macro (tools/qwen_missing/link_phy_gen.py): the far end is a second macro;
// a flit launched on tx_* appears on the FAR macro's rx_* {lat} FDI cycles later (link_* ports carry it between the
// pair).  tx_up rises UP cycles after reset.  Not synthesised.
module {name}_model #(parameter integer LAT = {lat}, parameter integer UP = 16) (
    input  wire clk, input wire rst_n,
    output reg  tx_up,
    input  wire tx_v, input wire [{fw - 1}:0] tx_flit,
    output wire rx_v, output wire [{fw - 1}:0] rx_flit,
    output wire link_v, output wire [{fw - 1}:0] link_flit,      // to the far macro
    input  wire far_v,  input  wire [{fw - 1}:0] far_flit
);
    reg [LAT*{fw + 1}-1:0] pipe;
    integer n;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin pipe <= 0; n <= 0; tx_up <= 1'b0; end
        else begin pipe <= {{pipe, far_v, far_flit}}; n <= n + 1; if (n >= UP) tx_up <= 1'b1; end
    assign {{rx_v, rx_flit}} = pipe[LAT*{fw + 1}-1 -: {fw + 1}];
    assign link_v = tx_v; assign link_flit = tx_flit;
endmodule
"""


def generate(out: Path) -> dict:
    cal = asap7.calibration()
    recs = {}
    for name, s in PHYS.items():
        fw = flit_bits(s["rxd"])
        plist = pins(fw)
        w = asap7.snap_up(s["width_um"], asap7.METAL["width_snap_um"])
        h = asap7.snap_up(s["height_um"], asap7.METAL["height_snap_um"])
        lef, pin_info = write_lef(name, w, h, plist, 0.192)
        per = {}
        for c in asap7.CORNERS:
            k = cal["corners"][c]
            fo4 = k["fo4_ps"]
            per[c] = Timing(corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
                            clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
                            out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4,
                            hold_ps=k["dff_hold_ps"] + fo4, min_period_ps=1000.0 / FDI_CLOCK_GHZ * 0.8,
                            min_pulse_ps=300.0, read_energy_fj=s["derived"]["energy_pj_per_bit"] * 1e3 * W,
                            write_energy_fj=0.0, leakage_nw=0.0, pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0,
                            breakdown={"fo4_ps": fo4})
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(lef)
        comment = f"{name}: licensed link PHY abstract, FDI boundary timing only (ASSUMED registered pins)"
        for c, t in per.items():
            (d / f"{name}_{c}.lib").write_text(write_liberty(name, t, plist, w * h, None, comment))
        (d / f"{name}_bb.v").write_text(blackbox_verilog(name, plist, comment))
        (d / f"{name}_model.sv").write_text(model_sv(name, fw, s["latency_cycles"]))
        sheet = dict(schema="opentallas.qwen-missing.link-phy-abstract.v1", generator="tools/qwen_missing/link_phy_gen.py",
                     name=name, footprint=dict(width_um=w, height_um=h, area_mm2=round(w * h / 1e6, 4)),
                     fdi=dict(clock_ghz=FDI_CLOCK_GHZ, flit_bits=fw, payload_bits=W, rx_buffer_flits=s["rxd"],
                              latency_fdi_cycles_one_way=s["latency_cycles"]),
                     published=[dict(source=a, figure=b) for a, b in s["published"]], derived=s["derived"],
                     assumed=s["assumed"], pins=pin_info, timing={c: asdict(t) for c, t in per.items()},
                     claim_boundary="a placement / connection / timing abstract of licensed IP: no PHY design, no "
                                    "GDS, no SI or bump-map analysis; footprint and boundary timing ASSUMED as stated")
        files = sorted(p.name for p in d.iterdir() if p.name != f"{name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
        recs[name] = sheet
    return recs


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    r = generate(a.out)
    print(json.dumps({k: dict(v["footprint"], **v["fdi"]) for k, v in r.items()}, indent=1))


if __name__ == "__main__":
    main()
