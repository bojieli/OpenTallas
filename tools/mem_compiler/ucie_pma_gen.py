#!/usr/bin/env python3
"""HBM host UCIe analog PMA hard-macro ABSTRACTS for the column parent ot_pdie_ucie_col (HBM-UCIE8 10-20).

Same method as tools/mem_compiler/s81_pma_gen.py (the S81 SerDes PMA abstracts): the UCIe-A PMA is analog IP (owner rule:
hard PHY analog may be behavioural), so this writes only what the column parent flow needs to reserve, place and connect:

* ot_ucie_pma_txm: digital face N (core side): ck, d[512:0] = {valid, beat} (registered on ck);
                   pad face S (bump side): pma_tx[512:0], pma_tck (launched on ck).
* ot_ucie_pma_rxm: pad face S: pma_rck (forwarded / recovered clock), pma_rx[512:0] (captured on pma_rck);
                   digital face N: q[512:0] (launched on pma_rck).
Each macro: one clock, registered boundary (ASAP7 flop clk->q / setup + 3 FO4).  Footprint basis: the HBM die grant slot
host_N 260.9 x 1653.5 um = the placeholder physical/asap7_v41x_pdie_macros_v2/ot_pdie_ucie (UCIe-A shoreline 1.043 x
6.61 mm at 1/4); the two PMA halves take the lower 1252.8 um of a 259.2-wide column (108.0 x 1252.8 each, origins on the
43.2 um lattice), the digital adapter / rate matcher the upper band.  Behavioural model of the same interface:
rtl/dsrom_sys/s81_link/ucie/ot_ucie_pma_models.sv (LAT 2 cycles, as ot_pdie_ucie PMA_LAT).
Pins: M5 (vertical layer: N / S faces), 0.024 x 0.192 um, pitch a multiple of the M5 pitch 0.048; PG = M5 stripes on the
parent 5.4 um M5 PG lattice; M1-M4 OBS, M5 OBS between the PG stripes (s81_pma_gen v1.1 LEF writer).

    python3 tools/mem_compiler/ucie_pma_gen.py --out physical/asap7_memory_macros
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
import s81_pma_gen as base  # noqa: E402
from views import Pin, Timing, blackbox_verilog, write_liberty  # noqa: E402

W_UM, H_UM = 108.0, 1252.8
GEN = "tools/mem_compiler/ucie_pma_gen.py v1.0"
BASIS = ("HBM GEN2e4 r11 grant slot host_N 260.928 x 1653.48 (placeholder ot_pdie_ucie: UCIe-A shoreline 1.043 x 6.61 mm "
         "at 1/4); two PMA halves 108.0 x 1252.8 in a 259.2 x 1641.6 column")


def macros():
    tx = [Pin("ck", 1, "input", "clock", "ck"), Pin("d", 513, "input", "data_in", "ck"),
          Pin("pma_tx", 513, "output", "data_out", "ck"), Pin("pma_tck", 1, "output", "data_out", "ck")]
    rx = [Pin("pma_rck", 1, "input", "clock", "pma_rck"), Pin("pma_rx", 513, "input", "data_in", "pma_rck"),
          Pin("q", 513, "output", "data_out", "pma_rck")]
    face = {"ot_ucie_pma_txm": {"N": ["ck", "d"], "S": ["pma_tx", "pma_tck"]},
            "ot_ucie_pma_rxm": {"S": ["pma_rck", "pma_rx"], "N": ["q"]}}
    return {"ot_ucie_pma_txm": tx, "ot_ucie_pma_rxm": rx}, face


def generate(out: Path):
    base.W_UM, base.H_UM = W_UM, H_UM          # the s81 LEF writer reads its module footprint
    ms, faces = macros()
    cal = asap7.calibration()
    res = {}
    for name, plist in ms.items():
        lef, info = base.write_lef(name, plist, faces[name])
        lef = lef.replace("tools/mem_compiler/s81_pma_gen.py: S81 SerDes analog PMA ABSTRACT",
                          "tools/mem_compiler/ucie_pma_gen.py: HBM host UCIe analog PMA ABSTRACT", 1)
        per = {}
        for c in asap7.CORNERS:
            k = cal["corners"][c]
            fo4 = k["fo4_ps"]
            per[c] = Timing(corner=c, voltage=k["voltage_v"], temperature=k["temperature_c"],
                            clk_to_q_ps=k["dff_clk_to_q_ps"] + 3 * fo4, out_r_kohm=k["inv4_r_kohm"] / 2.0,
                            out_slew_intrinsic_ps=1.5 * fo4, setup_ps=k["dff_setup_ps"] + 3 * fo4,
                            hold_ps=k["dff_hold_ps"] + fo4, min_period_ps=800.0, min_pulse_ps=300.0,
                            read_energy_fj=0.0, write_energy_fj=0.0, leakage_nw=0.0,
                            pin_cap_ff=k["inv1_cin_ff"] * 2, clk_cap_ff=50.0, breakdown={"fo4_ps": fo4})
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{name}.lef").write_text(lef)
        comment = f"{name}: HBM host UCIe analog PMA abstract, registered digital boundary (assumed)"
        for c, t in per.items():
            (d / f"{name}_{c}.lib").write_text(write_liberty(name, t, plist, W_UM * H_UM, None, comment))
        (d / f"{name}_bb.v").write_text(blackbox_verilog(name, plist, comment + "; behavioural model: "
                                                         "rtl/dsrom_sys/s81_link/ucie/ot_ucie_pma_models.sv"))
        sheet = {"schema": "opentallas.s81-pma-abstract.v1", "generator": GEN, "name": name,
                 "footprint_um": [W_UM, H_UM], "faces": faces[name], "pins": info,
                 "timing": {c: asdict(t) for c, t in per.items()}, "basis": BASIS,
                 "claim_boundary": "placement/connection abstract of analog IP; footprint and timing assumed"}
        files = sorted(p.name for p in d.iterdir() if p.name != f"{name}.json")
        sheet["views"] = {f: asap7.sha256_file(d / f) for f in files}
        (d / f"{name}.json").write_text(json.dumps(sheet, indent=2, sort_keys=True) + "\n")
        res[name] = info
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=asap7.ROOT / "physical/asap7_memory_macros")
    a = ap.parse_args()
    print(json.dumps(generate(a.out), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
