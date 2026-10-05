"""ASAP7 technology inputs of the OpenTallas memory compilers.

Everything a compiled macro's area, timing and power is computed from lives
here, each constant with its grade and source:

* ``measured``  -- read from an artifact this repository produced
  (the DRC-clean ASAP7 bitcell pitches in
  ``results/asap7_physical/bitcell_density/bitcell_density.json``) or from the
  pinned ORFS image's own ASAP7 files (standard-cell liberty, ``setRC.tcl``).
* ``published`` -- a number from a cited publication.
* ``assumed``   -- an engineering choice with no measurement behind it; the
  compiler's report carries these forward so nobody mistakes them for data.

The standard-cell numbers (FO4 delay, inverter drive, flop timing per corner)
are extracted by ``python3 tools/mem_compiler/asap7.py --calibrate`` from the
liberty files inside the pinned ORFS image and frozen in
``tools/mem_compiler/asap7_calibration.json`` with the liberty hashes, so the
generators themselves never need Docker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BITCELL_JSON = ROOT / "results/asap7_physical/bitcell_density/bitcell_density.json"
TECH_JSON = ROOT / "configs/hardware/technology.json"
CALIBRATION_JSON = Path(__file__).resolve().parent / "asap7_calibration.json"
ORFS_IMAGE = "openroad/orfs:latest"
NLDM_DIR = "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM"

CORNERS = {
    # name: (liberty corner tag, the ASAP7 library's own PVT)
    "tt": "TT",
    "ss": "SS",
    "ff": "FF",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


# ---------------------------------------------------------------------------
# measured bitcells (this repository's DRC-clean ASAP7 layouts)
# ---------------------------------------------------------------------------

def bitcells() -> dict[str, Any]:
    """The 6T SRAM and via-programmed NOR ROM bitcell pitches, in micrometres.

    The drawn cells put the transistor gates vertically (ASAP7's poly
    direction).  The compiler orients each array so the bitline runs across
    the rows and the wordline across the columns: ``row_pitch_um`` is the
    pitch one more row adds to a bitline, ``col_pitch_um`` the pitch one more
    column adds to a wordline.  For the 6T thin cell that is 0.108 um per row
    and 0.216 um per column (the long side carries the wordline, as in every
    thin cell); for the ROM cell 0.108 um per row (two contacted poly pitches:
    gate plus its programmable drain contact) and 0.054 um per column.
    """
    data = json.loads(BITCELL_JSON.read_text())
    cases = data["cases"]
    sram = cases["sram_6t"]
    rom = cases["rom_via_programmed"]
    for case in (sram, rom):
        if case["drc_violation_total"] != 0 or not case["expected_drc_clean"]:
            raise SystemExit(f"bitcell case {case['case']} is not DRC-clean; refusing to compile")
    sram_x, sram_y = sram["x_pitch_nm"] / 1000.0, sram["y_pitch_nm"] / 1000.0
    rom_x, rom_y = rom["x_pitch_nm"] / 1000.0, rom["y_pitch_nm"] / 1000.0
    return {
        "source": str(BITCELL_JSON.relative_to(ROOT)),
        "source_sha256": sha256_file(BITCELL_JSON),
        "sram_6t": {
            "drawn_x_um": sram_x, "drawn_y_um": sram_y,
            "row_pitch_um": min(sram_x, sram_y), "col_pitch_um": max(sram_x, sram_y),
            "area_um2": sram_x * sram_y, "gds_sha256": sram["gds_sha256"], "grade": "measured",
        },
        "rom_via": {
            "drawn_x_um": rom_x, "drawn_y_um": rom_y,
            "row_pitch_um": max(rom_x, rom_y), "col_pitch_um": min(rom_x, rom_y),
            "area_um2": rom_x * rom_y, "gds_sha256": rom["gds_sha256"], "grade": "measured",
        },
    }


def technology() -> dict[str, Any]:
    return json.loads(TECH_JSON.read_text())


def tech_value(path: str) -> Any:
    node: Any = technology()
    for key in path.split("."):
        node = node[key]
    return node["value"] if isinstance(node, dict) and "value" in node else node


# ---------------------------------------------------------------------------
# published calibration points
# ---------------------------------------------------------------------------

PUBLISHED = {
    "n7_hd_6t_bitcell_um2": {
        "value": 0.027, "grade": "published",
        "source": "configs/hardware/technology.json nodes.N7.sram_hd_bitcell_um2 (TSMC N7 HD 6T; "
                  "Jeong et al., IEDM 2016 / Chang et al., ISSCC 2017 256 Mb 7 nm SRAM)",
    },
    "n7_sram_macro_density_mb_mm2": {
        "value": 29.2, "grade": "published",
        "macro": "one 512 x 512 cell array (256 kbit), dual-edge driven wordline and bitline",
        "source": "Yokoyama et al., 'A 29.2 Mb/mm2 Ultra High Density SRAM Macro using 7nm FinFET "
                  "Technology with Dual-Edge Driven Wordline/Bitline and Write/Read-Assist Circuit', "
                  "IEEE Symposium on VLSI Circuits 2020, doi:10.1109/VLSICircuits18222.2020.9162985",
    },
    "fakeram7_256x32": {
        "value": {"area_um2": 343.985, "clk_to_q_ns": 0.218, "min_period_ns": 0.157,
                  "lef_size_um": [8.36, 42.0]},
        "grade": "published",
        "source": "ORFS platforms/asap7 lib/NLDM/fakeram7_256x32.lib and lef/fakeram7_256x32.lef in "
                  f"{ORFS_IMAGE}; FakeRAM2.0 output whose own config says 'VALUES NOT REALISTIC'",
    },
}


def published_macro_efficiency() -> float:
    """Array efficiency implied by the published 7 nm macro: cell-limited density over macro density."""
    cell_limited_mb_mm2 = 1.0 / PUBLISHED["n7_hd_6t_bitcell_um2"]["value"]  # Mb/mm2 = 1/(um2 per bit)
    return PUBLISHED["n7_sram_macro_density_mb_mm2"]["value"] / cell_limited_mb_mm2


# ---------------------------------------------------------------------------
# assumed circuit constants (every one is carried into the compiler report)
# ---------------------------------------------------------------------------

ASSUMED = {
    "sram_cell_read_current_ua": {
        "value": 20.0, "grade": "assumed",
        "note": "1-fin pass-gate/pull-down read stack of a 7 nm HD cell at 0.70 V, TT; published 7 nm "
                "HD cells report read currents of this order; no ASAP7 SRAM SPICE was run",
    },
    "rom_cell_read_current_ua": {
        "value": 25.0, "grade": "assumed",
        "note": "one 1-fin NMOS pull-down (no stack) per programmed NOR-ROM cell at 0.70 V, TT",
    },
    "drain_cap_per_cell_ff": {
        "value": 0.045, "grade": "assumed",
        "note": "bitline junction plus contact load one cell adds; the IHP 130 nm extraction "
                "(results/spice/ihp_sg13g2_rom_read_energy) measured 0.50 fF/row and is NOT scaled here",
    },
    "gate_cap_per_fin_ff": {
        "value": None, "grade": "derived",
        "note": "INVx1 input capacitance / its 6 fins (3 n + 3 p), from the calibration liberty",
    },
    "sram_sense_swing_v": {"value": 0.10, "grade": "assumed",
                           "note": "differential sense-amplifier input swing"},
    "rom_sense_swing_v": {"value": 0.15, "grade": "assumed",
                          "note": "single-ended bitline swing against a reference at the sense amplifier"},
    "wordline_layer": {"value": "M2", "grade": "assumed", "note": "wordline strap on M2, bitline on M1"},
    "periphery_fo4_budget": {
        "value": {"clock_and_latch": 3.0, "sense": 2.0, "output": 2.5, "mux_per_level": 0.5,
                  "decoder_per_address_bit": 0.55, "decoder_fixed": 1.5, "precharge": 2.0,
                  "write_driver": 3.0},
        "grade": "assumed",
        "note": "logic depth of the periphery in ASAP7 FO4 delays at each corner",
    },
    "periphery_geometry_um": {
        "value": {"decoder_fixed": 4.0, "decoder_per_row_bit": 0.45, "column_fixed": None,
                  "column_per_mux_bit": 0.5, "control_extra": 1.5, "fuse_compare_per_spare": 0.6,
                  "rom_decoder_fixed": 3.2, "rom_column_fixed": 5.0},
        "grade": "calibrated",
        "note": "column_fixed is solved so a 512 x 512 SRAM array with mux 4 reproduces the published "
                "7 nm macro efficiency (Yokoyama et al., VLSI 2020); the other entries are assumed",
    },
    "sram_leakage_w_per_mm2": {
        "value": None, "grade": "assumed",
        "note": "configs/hardware/technology.json power.static_leakage_w_per_mm2.sram_array",
    },
    "rom_leakage_w_per_mm2": {
        "value": None, "grade": "assumed",
        "note": "configs/hardware/technology.json power.static_leakage_w_per_mm2.rom_array",
    },
    "periphery_energy_ff_per_bit": {
        "value": 1.2, "grade": "assumed",
        "note": "switched capacitance of sense amplifier, output latch and IO driver per output bit",
    },
    "dual_port_cell_area_ratio": {
        "value": {"1r1w": 1.40, "2rw": 2.00}, "grade": "assumed",
        "note": "8T 1R1W (decoupled read stack) and 8T 2RW (two pass-gate pairs) cells relative to "
                "the measured 6T; the ASAP7 run drew only the 6T",
    },
}

# ASAP7 routing geometry, from the platform the flow routes against
# (platforms/asap7: M4 horizontal, 48 nm pitch; M5 vertical; setRC.tcl).
METAL = {
    "pin_layer": "M4",
    "pin_width_um": 0.024,
    "pin_pitch_um": 0.096,        # every other 48 nm M4 track, for pin access
    "m4_track_pitch_um": 0.048,
    "strap_width_um": 0.096,
    "strap_pitch_um": 0.768,      # VDD/VSS M4 straps the ORFS macro grid connects to with M4-M5 vias
    "obs_layers": ["M1", "M2", "M3", "M4"],
    "grid_um": 0.001,
    "width_snap_um": 0.216,       # 4 contacted poly pitches
    "height_snap_um": 0.270,      # one ASAP7 standard-cell row
}

SETRC = {  # kohm/um and fF/um, ORFS platforms/asap7/setRC.tcl
    "M1": (7.04175e-02, 1e-10 * 0 + 0.160),  # M1 capacitance is set to 1e-10 in setRC.tcl; M2's
    "M2": (2.97127e-02, 0.174942),           # value is used for the vertical M1 bitline
    "M3": (3.12870e-02, 0.155554),
    "M4": (1.80365e-02, 0.178475),
}


# ---------------------------------------------------------------------------
# standard-cell calibration, frozen from the pinned image
# ---------------------------------------------------------------------------

_NUM = r"[-+0-9.eE]+"


def _cell_block(text: str, cell: str) -> str:
    start = text.index(f"cell ({cell})")
    depth = 0
    i = text.index("{", start)
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[start:j + 1]
    raise ValueError(cell)


def _tables(block: str, kind: str) -> list[tuple[list[float], list[float], list[list[float]]]]:
    out = []
    for m in re.finditer(kind + r"\s*\([^)]*\)\s*\{(.*?)\}", block, re.S):
        body = m.group(1)
        i1 = [float(x) for x in re.search(r'index_1\s*\("([^"]*)"\)', body).group(1).split(",")]
        i2m = re.search(r'index_2\s*\("([^"]*)"\)', body)
        i2 = [float(x) for x in i2m.group(1).split(",")] if i2m else []
        vals = re.search(r"values\s*\((.*?)\)\s*;", body, re.S).group(1)
        rows = [[float(x) for x in r.split(",")] for r in re.findall(r'"([^"]*)"', vals)]
        out.append((i1, i2, rows))
    return out


def _interp(xs: list[float], ys: list[float], x: float) -> float:
    if x <= xs[0]:
        k = 0
    elif x >= xs[-1]:
        k = len(xs) - 2
    else:
        k = max(i for i in range(len(xs) - 1) if xs[i] <= x)
    t = (x - xs[k]) / (xs[k + 1] - xs[k])
    return ys[k] + t * (ys[k + 1] - ys[k])


def _lookup2(table, x1: float, x2: float) -> float:
    i1, i2, rows = table
    col = [_interp(i2, r, x2) for r in rows]
    return _interp(i1, col, x1)


def _pin_cap(block: str, pin: str) -> float:
    m = re.search(r"pin \(" + pin + r"\)\s*\{.*?\bcapacitance\s*:\s*(" + _NUM + ");", block, re.S)
    return float(m.group(1))


def calibrate_from_text(invbuf: str, seq: str) -> dict[str, Any]:
    inv = _cell_block(invbuf, "INVx1_ASAP7_75t_R")
    cin = _pin_cap(inv, "A")
    rise = _tables(inv, "cell_rise")[0]
    fall = _tables(inv, "cell_fall")[0]
    slew = 20.0
    fo4 = 0.5 * (_lookup2(rise, slew, 4 * cin) + _lookup2(fall, slew, 4 * cin))
    d_lo = 0.5 * (_lookup2(rise, slew, 4 * cin) + _lookup2(fall, slew, 4 * cin))
    d_hi = 0.5 * (_lookup2(rise, slew, 16 * cin) + _lookup2(fall, slew, 16 * cin))
    r_inv1 = (d_hi - d_lo) / (12 * cin)  # ps per fF = kohm
    inv4 = _cell_block(invbuf, "INVx4_ASAP7_75t_R")
    c4 = _pin_cap(inv4, "A")
    r4 = _tables(inv4, "cell_rise")[0]
    f4 = _tables(inv4, "cell_fall")[0]
    r_inv4 = (0.5 * (_lookup2(r4, slew, 16 * c4) + _lookup2(f4, slew, 16 * c4))
              - 0.5 * (_lookup2(r4, slew, 4 * c4) + _lookup2(f4, slew, 4 * c4))) / (12 * c4)
    dff = _cell_block(seq, "DFFHQNx1_ASAP7_75t_R")
    ck = [t for t in _tables(dff, "cell_rise")][0]
    clk_q = _lookup2(ck, slew, 4 * cin)
    setup = hold = None
    for m in re.finditer(r"timing \(\)\s*\{(.*?)\n\s{6}\}", dff, re.S):
        body = m.group(1)
        both = _tables(body, "rise_constraint") + _tables(body, "fall_constraint")
        if "setup_rising" in body:
            setup = max(_lookup2(t, slew, slew) for t in both)
        if "hold_rising" in body:
            hold = max(_lookup2(t, slew, slew) for t in both)
    vm = re.search(r"nom_voltage\s*:\s*(" + _NUM + ")", invbuf)
    tm = re.search(r"nom_temperature\s*:\s*(" + _NUM + ")", invbuf)
    return {
        "voltage_v": float(vm.group(1)), "temperature_c": float(tm.group(1)),
        "inv1_cin_ff": cin, "fo4_ps": fo4, "inv1_r_kohm": r_inv1, "inv4_r_kohm": r_inv4,
        "inv4_cin_ff": c4, "dff_clk_to_q_ps": clk_q, "dff_setup_ps": setup, "dff_hold_ps": hold,
        "slew_ps_used": slew,
    }


def run_calibration() -> dict[str, Any]:
    result: dict[str, Any] = {"image": ORFS_IMAGE, "corners": {}}
    for corner, tag in CORNERS.items():
        texts = {}
        for kind, name in (("invbuf", f"asap7sc7p5t_INVBUF_RVT_{tag}_nldm_220122.lib.gz"),
                           ("seq", f"asap7sc7p5t_SEQ_RVT_{tag}_nldm_220123.lib")):
            cmd = "zcat" if name.endswith(".gz") else "cat"
            proc = subprocess.run(["docker", "run", "--rm", ORFS_IMAGE, cmd, f"{NLDM_DIR}/{name}"],
                                  check=True, capture_output=True)
            texts[kind] = (name, proc.stdout)
        entry = calibrate_from_text(texts["invbuf"][1].decode(), texts["seq"][1].decode())
        entry["liberty"] = {name: sha256_bytes(data) for (name, data) in texts.values()}
        result["corners"][corner] = entry
    image = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", ORFS_IMAGE],
                           check=True, capture_output=True, text=True).stdout.strip()
    result["image_id"] = image
    return result


def calibration() -> dict[str, Any]:
    if not CALIBRATION_JSON.is_file():
        raise SystemExit(f"{CALIBRATION_JSON} missing: run python3 tools/mem_compiler/asap7.py --calibrate")
    return json.loads(CALIBRATION_JSON.read_text())


def gate_cap_per_fin_ff(cal: dict[str, Any]) -> float:
    return cal["corners"]["tt"]["inv1_cin_ff"] / 6.0


def snap_up(value: float, step: float) -> float:
    return round(math.ceil(value / step - 1e-9) * step, 6)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--calibrate", action="store_true",
                    help="extract the standard-cell calibration from the pinned ORFS image")
    args = ap.parse_args()
    if args.calibrate:
        cal = run_calibration()
        CALIBRATION_JSON.write_text(json.dumps(cal, indent=2, sort_keys=True) + "\n")
        for c, e in cal["corners"].items():
            print(c, {k: (round(v, 3) if isinstance(v, float) else v) for k, v in e.items() if k != "liberty"})
        return 0
    print(json.dumps({"bitcells": bitcells(), "published_efficiency": published_macro_efficiency()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
