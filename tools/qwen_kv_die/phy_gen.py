#!/usr/bin/env python3
"""kv-die 2026-10-09: the ROM die <-> KV die UCIe PHY abstract, ot_qkvd_ucie_x64_phy (licensed UCIe-A x64 module +
its D2D adapter, FDI side only), with the conventions of tools/qwen_missing/link_phy_gen.py (LEF / LIB / blackbox /
cycle model / graded datasheet).  Differences from ot_qfd_ucie_x64_phy: the FDI runs on the 1.2 GHz core clock of each
die (no core <-> FDI clock crossing in our logic; the macro retimes the forwarded lane clock into the local clock, as
the UCIe RDI/FDI does) and the flit is the 548-bit ot_qkvd_d2d flit {seq 8, credits 4 x 2, dv, class 3, word 528}.

    python3 tools/qwen_kv_die/phy_gen.py --out physical/qwen_kv_die_phy
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "mem_compiler"))
sys.path.insert(0, str(ROOT / "tools" / "qwen_missing"))
import asap7  # noqa: E402
import link_phy_gen as G  # noqa: E402
from views import Timing, blackbox_verilog, write_liberty  # noqa: E402

NAME = "ot_qkvd_ucie_x64_phy"
FW = 8 + 8 + 1 + 3 + 528          # ot_qkvd_d2d flit
FDI_GHZ = 1.2
LAT = dict(best=3, typical=5, worst=9)   # FDI cycles at 1.2 GHz, one way, FDI to far FDI
SPEC = dict(
    width_um=777.6, height_um=777.6,
    published=[
        ("UCIe advanced-package transceiver, 3 nm CoWoS, IEEE JSSC 2026 (doi:10.1109/JSSC.2026.3651425; registry "
         "sct:r-ucie-jssc26)", "0.29 pJ/bit, 5.27 Tb/s/mm, 3.5 ns measured FDI-to-FDI latency, 16 Gb/s/pin"),
        ("D. Das Sharma et al., UCIe, IEEE Trans. CPMT 12(9):1423, 2022, Table I (registry sct:r-ucie-tcpmt)",
         "latency (Tx + Rx) < 2 ns including D2D adapter and PHY; advanced reach <= 2 mm; CRC + retry in the D2D "
         "adapter"),
        ("UCIe Consortium, Hot Chips 2023 tutorial (registry sct:r-ucie-hc23)", "0.3-0.6 pJ/b at Adv 16-32 GT/s")],
    derived={
        "lanes": "one x64 advanced module, 64 TX + 64 RX lanes at 16 GT/s = 1,024 Gb/s each way; the 548-bit flit at "
                 "1.2 GHz is 657.6 Gb/s (64 % of raw, ~70 % after the UCIe flit-format overhead)",
        "latency_typical": "3.5 ns FDI-to-FDI (JSSC 2026) = 4.2 -> 5 cycles at 1.2 GHz",
        "latency_best": "< 2 ns (CPMT 2022 spec bound) -> 3 cycles",
        "energy_pj_per_bit": 0.29},
    assumed={
        "latency_worst": "9 cycles (7.5 ns): 2x the measured figure, covering a slower PHY / longer reach; a D2D "
                         "retry (CRC NAK + replay, ~2 x 5 + 2 cycles) is an error event, not the latency budget",
        "footprint": "777.6 x 777.6 um (0.60 mm2), as ot_qfd_ucie_x64_phy: two 388.8 um module widths of shoreline "
                     "(bump field + D2D adapter); 777.6 um of die edge on each die",
        "fdi_clock": "1.2 GHz, the local core clock of each die (both dies run off the KV-die PLL; the macro's receiver "
                     "retimes the forwarded lane clock into it)",
        "boundary_timing": "registered FDI pins: ASAP7 flop clk->q / setup + 3 FO4"})


def generate(out: Path) -> dict:
    cal = asap7.calibration()
    plist = G.pins(FW)
    w = asap7.snap_up(SPEC["width_um"], asap7.METAL["width_snap_um"])
    h = asap7.snap_up(SPEC["height_um"], asap7.METAL["height_snap_um"])
    lef, pin_info = G.write_lef(NAME, w, h, plist, 0.192)
    lef = lef.replace("tools/qwen_missing/link_phy_gen.py", "tools/qwen_kv_die/phy_gen.py")
    per = {}
    for c in asap7.CORNERS:
        k = cal["corners"][c]
        fo4 = k["fo4_ps"]
        per[c] = Timing(corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
                        clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
                        out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4,
                        hold_ps=k["dff_hold_ps"] + fo4, min_period_ps=1000.0 / FDI_GHZ * 0.8,
                        min_pulse_ps=300.0, read_energy_fj=SPEC["derived"]["energy_pj_per_bit"] * 1e3 * FW,
                        write_energy_fj=0.0, leakage_nw=0.0, pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0,
                        breakdown={"fo4_ps": fo4})
    d = out / NAME
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{NAME}.lef").write_text(lef)
    comment = f"{NAME}: licensed UCIe PHY + D2D adapter abstract, FDI boundary timing only (ASSUMED registered pins)"
    for c, t in per.items():
        (d / f"{NAME}_{c}.lib").write_text(write_liberty(NAME, t, plist, w * h, None, comment))
    (d / f"{NAME}_bb.v").write_text(blackbox_verilog(NAME, plist, comment))
    (d / f"{NAME}_model.sv").write_text(G.model_sv(NAME, FW, LAT["typical"]).replace(
        "tools/qwen_missing/link_phy_gen.py", "tools/qwen_kv_die/phy_gen.py"))
    sheet = dict(schema="opentallas.qwen-kv-die.link-phy-abstract.v1", generator="tools/qwen_kv_die/phy_gen.py",
                 name=NAME, footprint=dict(width_um=w, height_um=h, area_mm2=round(w * h / 1e6, 4), edge_um=w),
                 fdi=dict(clock_ghz=FDI_GHZ, flit_bits=FW, latency_fdi_cycles_one_way=LAT),
                 published=[dict(source=a, figure=b) for a, b in SPEC["published"]], derived=SPEC["derived"],
                 assumed=SPEC["assumed"], pins=pin_info, timing={c: asdict(t) for c, t in per.items()},
                 claim_boundary="a placement / connection / timing abstract of licensed IP: no PHY design, no GDS, no "
                                "SI or bump-map analysis; footprint and boundary timing ASSUMED as stated")
    files = sorted(p.name for p in d.iterdir() if p.name != f"{NAME}.json")
    sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
    (d / f"{NAME}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    s = generate(a.out)
    print(json.dumps(dict(s["footprint"], **s["fdi"])))


if __name__ == "__main__":
    main()
