#!/usr/bin/env python3
"""S81 SerDes analog PMA hard-macro ABSTRACTS for the column parent ot_pdie_serdes_col (S81-CTRL-SVC 10-19).

The PMA is analog IP (owner rule: hard PHY analog may be behavioural), so -- as tools/mem_compiler/hbm_phy_gen.py does for
the HBM PHY -- this writes only what the column parent flow needs to reserve, place and connect it:

* ot_s81_pma_txm: digital face N (core side, toward the KP4 stack): ck, d_v, d[543:0] (registered on ck);
                  pad face S (die edge): pma_tx[543:0], pma_tck (launched on ck).
* ot_s81_pma_rxm: pad face S: pma_rck (recovered clock), pma_rx[543:0] (captured on pma_rck);
                  digital face N: q[543:0] (launched on pma_rck).
Each macro: one clock, registered boundary (ASAP7 flop clk->q / setup + 3 FO4), footprint = half of the 250 x 2250 um
analog model of results/arch/serdes_parent_recovery_1019/model.json, snapped to the 43.2 um lattice (129.6 x 2246.4).
Behavioural model of the same interface: ot_s81_pma_txm / ot_s81_pma_rxm in rtl/dsrom_sys/s81_link/col/ (LAT 4 cycles).
Pins: M5 (vertical layer: N / S faces), 0.024 x 0.192 um, pitch a multiple of the M5 pitch 0.048; M1-M4 + M5 interior OBS.

    python3 tools/mem_compiler/s81_pma_gen.py --out physical/asap7_memory_macros
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asap7  # noqa: E402
from views import Pin, Timing, blackbox_verilog, write_liberty  # noqa: E402

W_UM, H_UM = 129.6, 2246.4
M5_PITCH = 0.048
PW, PL = 0.024, 0.192


def macros():
    tx = [Pin("ck", 1, "input", "clock", "ck"), Pin("d_v", 1, "input", "data_in", "ck"),
          Pin("d", 544, "input", "data_in", "ck"),
          Pin("pma_tx", 544, "output", "data_out", "ck"), Pin("pma_tck", 1, "output", "data_out", "ck")]
    rx = [Pin("pma_rck", 1, "input", "clock", "pma_rck"), Pin("pma_rx", 544, "input", "data_in", "pma_rck"),
          Pin("q", 544, "output", "data_out", "pma_rck")]
    face = {"ot_s81_pma_txm": {"N": ["ck", "d_v", "d"], "S": ["pma_tx", "pma_tck"]},
            "ot_s81_pma_rxm": {"S": ["pma_rck", "pma_rx"], "N": ["q"]}}
    return {"ot_s81_pma_txm": tx, "ot_s81_pma_rxm": rx}, face


def write_lef(name, plist, face):
    w, h = W_UM, H_UM
    L = [f"# OpenTallas tools/mem_compiler/s81_pma_gen.py: S81 SerDes analog PMA ABSTRACT {name} (assumed footprint/timing)",
         "VERSION 5.7 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', f"MACRO {name}", f"  FOREIGN {name} 0 0 ;",
         "  SYMMETRY X Y ;", f"  SIZE {w:.3f} BY {h:.3f} ;", "  CLASS BLOCK ;"]
    by = {p.name: p for p in plist}
    info = {}
    for f, names in face.items():
        bits = [(by[n], b) for n in names for b in by[n].bits()]
        span = w - 4.0
        pitch = max(M5_PITCH, int(span / len(bits) / M5_PITCH) * M5_PITCH)
        x0 = round(2.0 + (span - pitch * (len(bits) - 1)) / 2.0, 3)
        x0 = round(round(x0 / M5_PITCH) * M5_PITCH - PW / 2, 3)
        for i, (p, b) in enumerate(bits):
            x = x0 + i * pitch
            y0, y1 = (h - PL, h) if f == "N" else (0.0, PL)
            L += [f"  PIN {b}", f"    DIRECTION {p.direction.upper()} ;",
                  "    USE CLOCK ;" if p.kind == "clock" else "    USE SIGNAL ;", "    SHAPE ABUTMENT ;",
                  "    PORT", "      LAYER M5 ;", f"      RECT {x:.3f} {y0:.3f} {x + PW:.3f} {y1:.3f} ;", "    END",
                  f"  END {b}"]
        info[f] = {"pins": len(bits), "pitch_um": round(pitch, 3), "pins_per_um": round(len(bits) / span, 3)}
    sw, sp = 0.288, 2.4
    for k, (net, use) in enumerate((("VDD", "POWER"), ("VSS", "GROUND"))):
        L += [f"  PIN {net}", "    DIRECTION INOUT ;", f"    USE {use} ;", "    PORT", "      LAYER M4 ;"]
        y = 2.0 + k * sp / 2
        while y + sw < h - 2.0:
            L.append(f"      RECT 0.500 {y:.3f} {w - 0.5:.3f} {y + sw:.3f} ;")
            y += sp
        L += ["    END", f"  END {net}"]
    L += ["  OBS"]
    for layer in ("M1", "M2", "M3", "M4"):
        L += [f"    LAYER {layer} ;", f"    RECT 0 0 {w:.3f} {h:.3f} ;"]
    L += ["    LAYER M5 ;", f"    RECT 0 0.6 {w:.3f} {h - 0.6:.3f} ;"]
    L += ["  END", f"END {name}", "", "END LIBRARY"]
    return "\n".join(L) + "\n", info


def generate(out: Path):
    ms, faces = macros()
    cal = asap7.calibration()
    res = {}
    for name, plist in ms.items():
        lef, info = write_lef(name, plist, faces[name])
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
        comment = f"{name}: S81 SerDes analog PMA abstract, registered digital boundary (assumed)"
        for c, t in per.items():
            (d / f"{name}_{c}.lib").write_text(write_liberty(name, t, plist, W_UM * H_UM, None, comment))
        (d / f"{name}_bb.v").write_text(blackbox_verilog(name, plist, comment + "; behavioural model: "
                                                         "rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv"))
        sheet = {"schema": "opentallas.s81-pma-abstract.v1", "generator": "tools/mem_compiler/s81_pma_gen.py v1.0",
                 "name": name, "footprint_um": [W_UM, H_UM], "faces": faces[name], "pins": info,
                 "timing": {c: asdict(t) for c, t in per.items()},
                 "basis": "results/arch/serdes_parent_recovery_1019/model.json analog 250 x 2250 (two halves)",
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
