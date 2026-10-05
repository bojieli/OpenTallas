#!/usr/bin/env python3
"""Synthesise and fully route a mask-ROM macro in IHP SG13G2, and measure its
array efficiency instead of assuming it.

`rom.array_efficiency` is a single scalar that does not say which boundary it
means.  This runner draws the bit array
at the measured minimum legal pitch, adds the substrate tap bands the public
latch-up rule actually requires, straps the wordlines and escapes the bitlines
to a routable layer, synthesises a periphery from RTL and routes the whole thing
with OpenROAD.  The efficiency then falls out of the routed die area.

IHP SG13G2 is a 130 nm process.  Nothing here is scaled to N7/N6/N5/N4.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_sky130_physical as common
import run_ihp_bitcell_density as bitcell


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "physical" / "ihp_sg13g2_rom_macro" / "macro_contract.json"
ROW_HEIGHT_UM = 3.78
SITE_WIDTH_UM = 0.48
HALO_UM = 2.0

# The placer's target density. It is a RUNNER CONSTANT, not a property of the
# design, and naming it here rather than burying it in an f-string is the first
# half of a fix: the die-floor probe used to report "the standard cells stopped
# fitting" when what had actually happened was that they stopped fitting AT
# 0.85, and OpenROAD's own GPL-0302 diagnostic says "Use a higher -density" in
# so many words. A floor set by a number in this file is not a measured floor.
# The second half is `die_floor_probe_place_densities` in the contract, which
# this run escalates through before it is allowed to call a probe a refusal.
PLACE_DENSITY_HEADROOM = 0.15
PLACE_DENSITY_NOMINAL_CAP = 0.85
# The substring OpenROAD's global placer uses when the remedy it names is the
# constant above. If this appears in a probe's diagnostic, the probe measured
# this runner and not the design.
DENSITY_BLAMING_DIAGNOSTIC = "higher -density"


class MacroRouteError(RuntimeError):
    """A governed macro place-and-route input or acceptance gate failed."""


def repository_path(value: str) -> Path:
    try:
        return common.repository_path(value)
    except common.PhysicalExperimentError as exc:
        raise MacroRouteError(str(exc)) from exc


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise MacroRouteError("macro contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_rom_macro_routed_area_v1":
        raise MacroRouteError("unexpected macro experiment_id")
    if contract.get("pdk_lock") != "configs/pdk/ihp_sg13g2_physical_lock.json":
        raise MacroRouteError("macro contract must use the governed IHP lock")
    if lock.get("pdk", {}).get("variant") != "ihp-sg13g2":
        raise MacroRouteError("macro route requires IHP SG13G2")
    for value in contract["inputs"].values():
        if not repository_path(value).is_file():
            raise MacroRouteError(f"missing governed input: {value}")
    if not contract.get("macros"):
        raise MacroRouteError("the contract names no macro geometry")
    for macro in contract["macros"]:
        if macro["cols"] % macro["mux"] or macro["rows"] & (macro["rows"] - 1):
            raise MacroRouteError(f"{macro['name']}: rows must be a power of two and cols divisible by mux")
    boundary = contract["claim_boundary"]
    if (
        boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
    ):
        raise MacroRouteError("macro claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for marker in (
        "N7", "GPU speedup", "silicon", "LOWER bound", "power distribution",
        "placement density",
    ):
        if marker not in forbidden:
            raise MacroRouteError(f"claim boundary does not cover {marker}")
    ladder = contract.get("die_floor_probe_utilizations")
    if not ladder:
        raise MacroRouteError(
            "the contract names no die-floor probe: without one the reported die area is "
            "sized from `utilization` and the array efficiency taken from it is a restatement "
            "of that constant rather than a measurement"
        )
    for macro in contract["macros"]:
        if any(step <= macro["utilization"] for step in ladder):
            raise MacroRouteError(
                f"{macro['name']}: a die-floor probe must be TIGHTER than the nominal "
                f"utilization {macro['utilization']}; the ladder {ladder} is not"
            )
    densities = contract.get("die_floor_probe_place_densities")
    if not densities:
        raise MacroRouteError(
            "the contract names no `die_floor_probe_place_densities`. The placer's target "
            f"density is a constant this runner chose ({PLACE_DENSITY_NOMINAL_CAP} at the "
            "top), OpenROAD's GPL-0302 names it as the remedy when it refuses a die, and a "
            "die floor found at that constant is a measurement of this file rather than of "
            "the design."
        )
    if any(
        value <= PLACE_DENSITY_NOMINAL_CAP or value > 1.0 for value in densities
    ) or list(densities) != sorted(densities):
        raise MacroRouteError(
            f"the placement-density escalation ladder {densities} must be ascending and every "
            f"rung must lie above the runner's nominal cap {PLACE_DENSITY_NOMINAL_CAP} and at "
            "or below 1.0; a rung at or below the cap escalates nothing"
        )
    for value in contract["reports"].values():
        repository_path(value)


BITCELL_RESULT = ROOT / "results" / "spice" / "ihp_sg13g2_bitcell" / "bitcell.json"
READ_ENERGY_RESULT = (
    ROOT / "results" / "spice" / "ihp_sg13g2_rom_read_energy" / "read_energy.json"
)


def measured_bitcell_area_um2(contract: dict[str, Any]) -> dict[str, Any]:
    """The ROM bitcell area, read from the run that measured it.

    It used to be the literal 0.390150 in this file. A number transcribed by
    hand out of one artifact and into the source of another runner is silently
    decoupled from it: re-measure the bitcell, and the macro efficiency keeps
    quoting the old cell area with nothing to say so. So read it, and refuse
    unless the bitcell was drawn by the SAME generator this run is about to
    draw with -- otherwise the two areas describe two different cells.
    """
    if not BITCELL_RESULT.is_file():
        raise MacroRouteError(
            f"{BITCELL_RESULT.relative_to(ROOT)} is missing; run "
            "tools/run_ihp_bitcell_density.py first. The bit-array area is measured "
            "there and is not restated here."
        )
    measured = json.loads(BITCELL_RESULT.read_text(encoding="utf-8"))
    generator = repository_path(contract["inputs"]["generator"])
    theirs = measured.get("inputs", {}).get("generator", {})
    if theirs.get("sha256") != common.sha256_file(generator):
        raise MacroRouteError(
            "the bitcell measurement was taken with a different revision of "
            f"{contract['inputs']['generator']} than this run uses "
            f"({theirs.get('sha256')} vs {common.sha256_file(generator)}); its cell area "
            "does not describe the array this run draws"
        )
    cell = measured["rom_bitcell"]
    return {
        "cell_area_um2": float(cell["cell_area_um2"]),
        "column_pitch_nm": cell["column_pitch_nm"],
        "row_pitch_nm": cell["row_pitch_nm"],
        "source": "results/spice/ihp_sg13g2_bitcell/bitcell.json#rom_bitcell.cell_area_um2",
        "generator_sha256": theirs.get("sha256"),
    }


def measured_wordline_capacitance(contract: dict[str, Any]) -> dict[str, Any]:
    """The wordline pin capacitance the macro Liberty needs, read from the run
    that measured it, and cross-checked against the contract's declared value.

    The contract carried `wordline_capacitance_ff_per_column` as a literal and
    named `results/spice/ihp_sg13g2_rom_read_energy` as its source. That
    artifact recorded no such quantity, so the citation could not be checked
    and the number was, in effect, ungrounded. It now is recorded, and this
    refuses a contract value that the artifact does not support.
    """
    if not READ_ENERGY_RESULT.is_file():
        raise MacroRouteError(
            f"{READ_ENERGY_RESULT.relative_to(ROOT)} is missing; run "
            "tools/run_ihp_rom_read_energy.py first. The wordline load is measured there."
        )
    energy = json.loads(READ_ENERGY_RESULT.read_text(encoding="utf-8"))
    block = energy.get("wordline_capacitance")
    if not block or block.get("ff_per_column") is None:
        raise MacroRouteError(
            "the read-energy artifact records no wordline capacitance, so the macro "
            "Liberty would be built from a number no run in this repository measured"
        )
    measured = float(block["ff_per_column"])
    declared = contract.get("wordline_capacitance_ff_per_column")
    tolerance = float(contract.get("wordline_capacitance_tolerance", 0.05))
    if declared is not None and abs(declared - measured) > tolerance * measured:
        raise MacroRouteError(
            f"the contract declares a wordline capacitance of {declared} fF/column but the "
            f"run it cites measured {measured:.4f} fF/column. The contract is not allowed "
            "to carry a number its own source does not support."
        )
    return {
        "ff_per_column": measured,
        "source": "results/spice/ihp_sg13g2_rom_read_energy/read_energy.json"
                  "#wordline_capacitance.ff_per_column",
        "method": block.get("method"),
        "from_case": block.get("from_case"),
    }


LEF_SIZE_RE = re.compile(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)")
YOSYS_AREA_RE = re.compile(r"Chip area for module '\\\\?ot_rom_macro':\s*([0-9.]+)")
OR_RE = re.compile(r"(?m)^OT_([A-Z_0-9]+)=(.+)$")


def draw_array(
    contract: dict[str, Any],
    macro: dict[str, Any],
    magic: Path,
    variant: Path,
    pdk: Path,
    work: Path,
    bitcell_area: dict[str, Any],
) -> dict[str, Any]:
    generator = repository_path(contract["inputs"]["generator"])
    overrides = {
        "NROW": macro["rows"],
        "NCOL": macro["cols"],
        "PATTERN": "prand",
        "TAP_EVERY": macro["tap_every"],
        "WL_STRAP": 1,
        "LEF": 1,
    }
    run = bitcell.run_generator(magic, variant, pdk, generator, overrides, work, extract=False)
    # The macro array is drawn from the generator's DEFAULT dimensions; the
    # bitcell area it is multiplied by was measured from the bitcell contract's
    # nominal dimensions. Those are two independent sets of numbers that happen
    # to agree today, and nothing noticed. If either drifts, `bits x cell area`
    # silently describes a cell this macro does not contain, so check the pitch
    # the generator actually reports against the pitch that was measured.
    drawn_px = float(run["params"]["PX"])
    drawn_py = float(run["params"]["PY"])
    if (
        abs(drawn_px - float(bitcell_area["column_pitch_nm"])) > 1e-6
        or abs(drawn_py - float(bitcell_area["row_pitch_nm"])) > 1e-6
    ):
        raise MacroRouteError(
            f"{macro['name']}: this array is drawn on a {drawn_px} x {drawn_py} nm cell pitch "
            f"but the measured bitcell is {bitcell_area['column_pitch_nm']} x "
            f"{bitcell_area['row_pitch_nm']} nm. The bit-array area would be computed from a "
            "cell this macro does not contain."
        )
    if run["drc_errors"] != contract["acceptance"]["array_drc_errors_max"]:
        raise MacroRouteError(
            f"{macro['name']}: bit array is not DRC clean: {run['drc_errors']} errors, {run['drc_rules']}"
        )
    lef = work / "ihp_rom_bitarray.lef"
    if not lef.is_file():
        raise MacroRouteError(f"{macro['name']}: magic did not write the macro LEF")
    size = LEF_SIZE_RE.search(lef.read_text(encoding="utf-8"))
    if size is None:
        raise MacroRouteError(f"{macro['name']}: macro LEF has no SIZE record")
    width, height = float(size.group(1)), float(size.group(2))
    pins = re.findall(r"(?m)^\s*PIN\s+(\S+)\s*$", lef.read_text(encoding="utf-8"))
    wanted = bitcell.expected_ports(macro["rows"], macro["cols"])
    if sorted(pins) != sorted(wanted):
        missing = [name for name in wanted if name not in pins]
        extra = [name for name in pins if name not in wanted]
        raise MacroRouteError(
            f"{macro['name']}: the macro LEF declares {len(pins)} of {len(wanted)} pins; "
            f"missing {missing[:8]}, unexpected {extra[:8]}"
        )
    return {
        "pin_count": len(pins),
        "cell_column_pitch_nm": drawn_px,
        "cell_row_pitch_nm": drawn_py,
        "lef": lef,
        "macro_width_um": width,
        "macro_height_um": height,
        "macro_area_um2": width * height,
        "drc_errors": run["drc_errors"],
        "magic_log_sha256": run["log_sha256"],
    }


def tapless_control(
    contract: dict[str, Any], macro: dict[str, Any], magic: Path, variant: Path, pdk: Path, work: Path
) -> dict[str, Any]:
    """Draw the same array with no tap bands and record what the deck says.

    The claim that periodic taps are mandatory has to be a measurement, not an
    assertion, so this runs the control and refuses to record a result unless
    the control actually fails on the latch-up rule.
    """
    generator = repository_path(contract["inputs"]["generator"])
    overrides = {
        "NROW": macro["rows"],
        "NCOL": macro["cols"],
        "PATTERN": "prand",
        "TAP_EVERY": 0,
        "WL_STRAP": 1,
    }
    control = work / "no_taps"
    try:
        run = bitcell.run_generator(magic, variant, pdk, generator, overrides, control, extract=False)
    except bitcell.BitcellError as exc:
        raise MacroRouteError(f"{macro['name']}: tapless control did not run: {exc}") from exc
    rules = sorted({entry["rule"] for entry in run["drc_rules"]})
    latchup = [rule for rule in rules if "LU.a" in rule or "LU.b" in rule]
    if run["drc_errors"] == 0 or not latchup:
        raise MacroRouteError(
            f"{macro['name']}: the tapless control produced {run['drc_errors']} errors and rules "
            f"{rules}; the tap bands cannot be justified by a control that passes"
        )
    return {
        "tap_every": 0,
        "drc_errors": run["drc_errors"],
        "violated_rules": rules,
        "latch_up_rules": latchup,
        "magic_log_sha256": run["log_sha256"],
    }


def write_views(
    contract: dict[str, Any],
    macro: dict[str, Any],
    drawn: dict[str, Any],
    work: Path,
    wordline: dict[str, Any],
) -> None:
    rows, cols, mux = macro["rows"], macro["cols"], macro["mux"]
    out = cols // mux
    aw = int(math.log2(rows)) + (int(math.log2(mux)) if mux > 1 else 0)

    blackbox = ["`default_nettype none", "module ihp_rom_bitarray (", "  inout wire VSS,"]
    blackbox += [f"  input wire WL{i}," for i in range(rows)]
    blackbox += [f"  output wire BL{i}," for i in range(cols - 1)]
    blackbox += [f"  output wire BL{cols - 1}", ");", "endmodule", "`default_nettype wire"]
    (work / "ihp_rom_bitarray_bb.v").write_text("\n".join(blackbox) + "\n", encoding="utf-8")

    wrapper = [
        "`default_nettype none",
        "module ot_rom_macro (input wire clk, input wire rst_n, input wire req,",
        f"  input wire [{aw - 1}:0] addr, output wire [{out - 1}:0] dout, output wire valid);",
        f"  wire [{rows - 1}:0] wl;  wire [{cols - 1}:0] bl;  wire pre_n;  wire vss;",
        "  assign vss = 1'b0;",
        f"  ot_rom_macro_periphery #(.ROWS({rows}), .COLS({cols}), .MUX({mux})) u_periphery (",
        "    .clk(clk), .rst_n(rst_n), .req(req), .addr(addr),",
        "    .wl(wl), .pre_n(pre_n), .bl(bl), .dout(dout), .valid(valid));",
        "  ihp_rom_bitarray u_array (.VSS(vss),",
    ]
    wrapper += [f"    .WL{i}(wl[{i}])," for i in range(rows)]
    wrapper += [f"    .BL{i}(bl[{i}])," for i in range(cols - 1)]
    wrapper += [f"    .BL{cols - 1}(bl[{cols - 1}]));", "endmodule", "`default_nettype wire"]
    (work / "ot_rom_macro_wrapper.v").write_text("\n".join(wrapper) + "\n", encoding="utf-8")

    # Minimal macro Liberty. The wordline capacitance is measured, not guessed:
    # it is the integrated wordline charge of the extracted array, per column.
    wl_pf = wordline["ff_per_column"] * 1e-3 * cols
    lib = [
        "library (ihp_rom_bitarray) {",
        "  technology (cmos);",
        "  delay_model : table_lookup;",
        '  time_unit : "1ns"; voltage_unit : "1V"; current_unit : "1mA";',
        "  capacitive_load_unit (1, pf);",
        '  pulling_resistance_unit : "1kohm"; leakage_power_unit : "1nW";',
        "  input_threshold_pct_rise : 50; input_threshold_pct_fall : 50;",
        "  output_threshold_pct_rise : 50; output_threshold_pct_fall : 50;",
        "  slew_lower_threshold_pct_rise : 20; slew_lower_threshold_pct_fall : 20;",
        "  slew_upper_threshold_pct_rise : 80; slew_upper_threshold_pct_fall : 80;",
        "  slew_derate_from_library : 1.0; default_max_transition : 1.5;",
        "  nom_voltage : 1.2; nom_temperature : 25; nom_process : 1;",
        "  operating_conditions (typ) { process : 1; voltage : 1.2; temperature : 25; }",
        "  default_operating_conditions : typ;",
        "  cell (ihp_rom_bitarray) {",
        "    is_macro_cell : true; dont_touch : true; dont_use : true;",
        f"    area : {drawn['macro_area_um2']:.4f};",
        '    pg_pin (VSS) { pg_type : primary_ground; voltage_name : "VSS"; }',
    ]
    for i in range(rows):
        lib.append(
            f'    pin (WL{i}) {{ direction : input; capacitance : {wl_pf:.6f}; related_ground_pin : "VSS"; }}'
        )
    for i in range(cols):
        lib.append(
            f'    pin (BL{i}) {{ direction : output; max_capacitance : 0.5; function : "0"; related_ground_pin : "VSS"; }}'
        )
    lib += ["  }", "}"]
    (work / "ihp_rom_bitarray.lib").write_text("\n".join(lib) + "\n", encoding="utf-8")


def substitute(template: Path, mapping: dict[str, str], out: Path) -> None:
    text = template.read_text(encoding="utf-8")
    for key, value in mapping.items():
        text = text.replace(key, value)
    if "@" in re.sub(r"[^@]", "", text) and re.search(r"@[A-Z_0-9]+@", text):
        raise MacroRouteError(f"unsubstituted placeholder left in {out}: {re.findall(r'@[A-Z_0-9]+@', text)}")
    out.write_text(text, encoding="utf-8")


def synthesise(contract: dict[str, Any], variant: Path, work: Path, yosys: Path) -> dict[str, Any]:
    stdcell_lib = variant / "libs.ref" / "sg13g2_stdcell" / "lib" / "sg13g2_stdcell_typ_1p20V_25C.lib"
    script = work / "synth.ys"
    substitute(
        repository_path(contract["inputs"]["synthesis_script"]),
        {
            "@STDCELL_LIB@": str(stdcell_lib),
            "@MACRO_LIB@": str(work / "ihp_rom_bitarray.lib"),
            "@ARRAY_BLACKBOX@": str(work / "ihp_rom_bitarray_bb.v"),
            "@PERIPHERY_RTL@": str(repository_path(contract["inputs"]["periphery_rtl"])),
            "@WRAPPER_RTL@": str(work / "ot_rom_macro_wrapper.v"),
            "@NETLIST@": str(work / "netlist.v"),
        },
        script,
    )
    completed = subprocess.run(
        [str(yosys), "-s", script.name],
        cwd=work, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=7200,
    )
    log = work / "yosys.log"
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise MacroRouteError(f"yosys failed ({completed.returncode}); see {log}")
    area = YOSYS_AREA_RE.search(completed.stdout)
    if area is None:
        raise MacroRouteError(f"yosys did not report a chip area; see {log}")
    version = re.search(r"(?m)^Yosys\s+(\S+)\s+\(git sha1 (\S+),", completed.stdout)
    # What the array's ground pin is actually connected to in the netlist that
    # gets routed. It is a logic constant, not a rail: this flow builds no PDN,
    # so the router has nothing to tie the array's ground to. Recording it
    # stops "fully routed, zero violations" from being read as "powered".
    netlist_text = (work / "netlist.v").read_text(encoding="utf-8")
    vss_net = re.search(r"(?m)^\s*\.VSS\((.+?)\)", netlist_text)
    if vss_net is None:
        raise MacroRouteError(
            "the synthesised netlist does not connect the bit array's VSS pin at all; "
            "the array would be routed with a floating source rail"
        )
    # Where the measured wordline load is, and is NOT, consumed. `abc` is handed
    # the standard-cell Liberty only, and the array is a blackbox by then, so the
    # wordline pin capacitance cannot move the synthesised standard-cell area and
    # therefore cannot move the floorplanned die. It reaches OpenROAD's
    # `repair_design` and nothing else. Recording that stops the number from
    # being read as load-bearing for an area it cannot touch.
    mapper = re.search(r"(?m)^abc\s+.*$", script.read_text(encoding="utf-8"))
    macro_lib = str(work / "ihp_rom_bitarray.lib")
    return {
        "array_vss_connected_to": vss_net.group(1).strip(),
        "macro_liberty_reaches_technology_mapper": bool(
            mapper and macro_lib in mapper.group(0)
        ),
        "macro_liberty_consumption_note": (
            "the wordline pin capacitance measured by the read-energy run reaches "
            "OpenROAD's repair_design and nothing else. yosys maps against the "
            "standard-cell Liberty alone and the bit array is a blackbox by then, so "
            "that number cannot change standard_cell_area_um2 and cannot change the "
            "floorplanned die area. Its only reachable effect is on whether a given "
            "die closes routing, i.e. on the die-floor probe."
        ),
        "array_vss_note": (
            "a logic constant, tied by insert_tiecells. This flow builds no power "
            "distribution network, so the bit array's ground is a signal-level tie and "
            "not a rail. A manufacturable macro connects it to the PDN and spends area "
            "on straps that are not in any die area reported here."
        ),
        "standard_cell_area_um2": float(area.group(1)),
        "yosys_version": version.group(1) if version else None,
        "yosys_commit": version.group(2).rstrip(",") if version else None,
        "log_sha256": common.sha256_file(log),
    }


def route(
    contract: dict[str, Any],
    macro: dict[str, Any],
    drawn: dict[str, Any],
    synth: dict[str, Any],
    variant: Path,
    work: Path,
    openroad: Path,
    util: float | None = None,
    tag: str = "",
    timeout: int = 43200,
    must_close: bool = True,
    density: float | None = None,
) -> dict[str, Any]:
    mw, mh = drawn["macro_width_um"], drawn["macro_height_um"]
    cells = synth["standard_cell_area_um2"]
    util = macro["utilization"] if util is None else util
    if density is None:
        density = min(PLACE_DENSITY_NOMINAL_CAP, util + PLACE_DENSITY_HEADROOM)
    total = mw * mh + cells / util
    core_w = max(math.sqrt(total * (mw / mh)), mw + 6.0 + 2 * HALO_UM)
    core_h = max(total / core_w, mh + 2 * HALO_UM)
    core_w = math.ceil(core_w / SITE_WIDTH_UM) * SITE_WIDTH_UM
    core_h = math.ceil(core_h / ROW_HEIGHT_UM) * ROW_HEIGHT_UM
    die_w, die_h = core_w + 2 * HALO_UM, core_h + 2 * HALO_UM
    macro_x = core_w - mw - HALO_UM
    macro_y = core_h - mh - HALO_UM

    tracks = "\n".join(
        f"make_tracks {layer} -x_offset 0 -x_pitch 0.48 -y_offset 0 -y_pitch 0.42"
        for layer in ("Metal1", "Metal2", "Metal3", "Metal4", "Metal5")
    )
    (work / "tracks.tcl").write_text(tracks + "\n", encoding="utf-8")

    suffix = f"_{tag}" if tag else ""
    script = work / f"route{suffix}.tcl"
    substitute(
        repository_path(contract["inputs"]["route_script"]),
        {
            "@TECH_LEF@": str(variant / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
            "@STDCELL_LEF@": str(variant / "libs.ref/sg13g2_stdcell/lef/sg13g2_stdcell.lef"),
            "@MACRO_LEF@": str(drawn["lef"]),
            "@STDCELL_LIB@": str(variant / "libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"),
            "@MACRO_LIB@": str(work / "ihp_rom_bitarray.lib"),
            "@NETLIST@": str(work / "netlist.v"),
            "@SDC@": str(repository_path(contract["inputs"]["sdc"])),
            "@TRACKS_TCL@": str(work / "tracks.tcl"),
            "@DIE_W@": f"{die_w:.3f}", "@DIE_H@": f"{die_h:.3f}",
            "@CORE_X0@": f"{HALO_UM:.3f}", "@CORE_Y0@": f"{HALO_UM:.3f}",
            "@CORE_X1@": f"{HALO_UM + core_w:.3f}", "@CORE_Y1@": f"{HALO_UM + core_h:.3f}",
            "@MACRO_X@": f"{HALO_UM + macro_x:.3f}", "@MACRO_Y@": f"{HALO_UM + macro_y:.3f}",
            "@PLACE_DENSITY@": f"{density:.2f}",
            "@DRC_RPT@": str(work / f"route_drc{suffix}.rpt"),
            "@DEF@": str(work / f"final{suffix}.def"),
        },
        script,
    )
    try:
        completed = subprocess.run(
            [str(openroad), "-no_init", "-exit", script.name],
            cwd=work, check=False, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
        )
        stdout = completed.stdout
        returncode = completed.returncode
        timed_out = False
    except subprocess.TimeoutExpired as expired:
        if must_close:
            raise
        stdout = (expired.stdout or b"").decode("utf-8", "replace") if isinstance(
            expired.stdout, bytes
        ) else (expired.stdout or "")
        returncode = -1
        timed_out = True
    log = work / f"openroad{suffix}.log"
    log.write_text(stdout, encoding="utf-8")
    markers = dict(OR_RE.findall(stdout))
    converged = markers.get("ROUTE_DONE") == "1"
    if must_close and not converged:
        raise MacroRouteError(
            f"{macro['name']}: OpenROAD did not finish routing (exit {returncode}); see {log}. "
            "This is reported as a failure to converge, not silently replaced with a synthesis estimate."
        )
    drc_report = work / f"route_drc{suffix}.rpt"
    violations = 0
    if drc_report.is_file():
        violations = sum(
            1 for line in drc_report.read_text(encoding="utf-8").splitlines() if line.startswith("\tviolation")
        )
    limit = contract["acceptance"]["route_drc_violations_max"]
    if must_close and violations > limit:
        raise MacroRouteError(f"{macro['name']}: detailed route left {violations} violations")
    version = re.search(r"(?m)^OpenROAD (\S+)", stdout)
    # A probe that fails has to name its failure, exactly as the bitcell floor
    # probes name the DRC rule that stops a shrink. "Did not converge" with no
    # reason is not a measurement; it is indistinguishable from a crash.
    errors = re.findall(r"(?m)^\[ERROR\s+[A-Z]+-\d+\].*$", stdout)
    if not errors:
        errors = re.findall(r"(?m)^Error:.*$", stdout)
    tail = [line for line in stdout.splitlines() if line.strip()][-1:]
    # Which stage refused the die. A floor found at global placement means the
    # standard cells stopped fitting; a floor found at routing means the wires
    # stopped fitting. They are different claims and the report must not blur
    # them.
    stages = {"GPL": "global placement", "GRT": "global routing", "DRT": "detailed routing",
              "DPL": "detailed placement", "RSZ": "resizer", "CTS": "clock tree synthesis"}
    stage = None
    for line in errors:
        code = re.search(r"\[ERROR\s+([A-Z]+)-\d+\]", line)
        if code:
            stage = stages.get(code.group(1), code.group(1))
    failure_text = " ".join(errors[-3:] or tail)
    record = {
        "requested_utilization": util,
        "tag": tag,
        # The placer's target density is a constant this runner chose. It is
        # recorded on every route so that a die area can never be read as a
        # property of the design alone.
        "place_density": density,
        "place_density_is_a_runner_constant": True,
        "failure_blames_place_density": bool(
            not converged and DENSITY_BLAMING_DIAGNOSTIC in failure_text
        ),
        "converged": converged,
        "timed_out": timed_out,
        "failure_reason": (
            None if converged else (errors[-3:] or tail or ["no diagnostic emitted"])
        ),
        "failure_stage": None if converged else stage,
        "detailed_route_violations": violations,
        "closed_clean": bool(converged and violations <= limit),
        "openroad_version": version.group(1) if version else None,
        "log_sha256": common.sha256_file(log),
        # No power distribution network is built in this flow: no `pdngen`, no
        # `global_connect`, no straps. The macro's VSS pin is declared in the
        # LEF and, in the netlist that is routed, is tied to a logic constant by
        # `insert_tiecells` rather than to a rail, so the die below holds SIGNAL
        # routing only. A manufacturable macro also carries power straps, so
        # this area is a lower bound on that account as well as on the
        # standard-cell-periphery account.
        "power_distribution": (
            "none: signal routing only. No pdngen, no global_connect, no straps; the bit "
            "array's VSS pin is tied to a logic constant by insert_tiecells rather than to a "
            "rail, so this die area carries no power distribution at all"
        ),
    }
    if converged:
        record.update(
            {
                "die_width_um": float(markers["DIE_W"]),
                "die_height_um": float(markers["DIE_H"]),
                "die_area_um2": float(markers["DIE_AREA_UM2"]),
                "core_area_um2": float(markers["CORE_AREA_UM2"]),
                "worst_slack_ns": float(markers["WNS"]) if "WNS" in markers else None,
                "total_negative_slack_ns": float(markers["TNS"]) if "TNS" in markers else None,
            }
        )
    else:
        record["requested_die_area_um2"] = die_w * die_h
    return record


def die_floor_probe(
    contract: dict[str, Any],
    macro: dict[str, Any],
    drawn: dict[str, Any],
    synth: dict[str, Any],
    variant: Path,
    work: Path,
    openroad: Path,
    nominal: dict[str, Any],
) -> dict[str, Any]:
    """Find how much of the reported die area is a choice.

    The nominal die is not measured: it is sized from the contract's requested
    utilization, so `bit array / die` is partly a restatement of that constant.
    Nothing in the flow refused it, and an efficiency that moves when you edit
    one number in a contract is not a measurement.

    So squeeze. Re-route the identical netlist on progressively smaller dies
    and record, for each, whether detailed routing still closes with zero
    violations. The tightest one that closes is a MEASURED floor for this
    netlist under this flow; the first one that does not is the named failure
    that brackets it. If nothing fails, that is reported too -- the floor is
    then not bracketed and the reported efficiency is only known to be
    pessimistic.

    THE TRAP THIS FUNCTION WALKED INTO ONCE. The probe replaced one chosen
    constant (`utilization`) with another (`min(0.85, util + 0.15)`, the
    placer's target density, written in this file). Every probe that "did not
    close" failed at global placement with GPL-0302, whose text is *Use a
    higher -density or re-floorplan with a larger core area* -- OpenROAD naming
    this runner's own constant as the remedy. The report called that a measured
    cell-area floor. It was a floor at 0.85. So a probe is no longer allowed to
    be recorded as a refusal while its diagnostic still blames the density:
    the contract's escalation ladder is walked first, and if the top of the
    ladder still blames it, the step is marked `floor_limited_by_place_density`
    and the report has to say so instead of claiming the cells stopped fitting.
    """
    ladder = list(contract.get("die_floor_probe_utilizations") or [])
    densities = list(contract.get("die_floor_probe_place_densities") or [])
    steps: list[dict[str, Any]] = []
    timeout = int(contract.get("die_floor_probe_timeout_s", 3600))
    for util in ladder:
        if util <= macro["utilization"]:
            raise MacroRouteError(
                f"{macro['name']}: a die-floor probe at utilization {util} is not tighter "
                f"than the nominal {macro['utilization']} and proves nothing"
            )
        attempts: list[dict[str, Any]] = []
        nominal_density = min(PLACE_DENSITY_NOMINAL_CAP, util + PLACE_DENSITY_HEADROOM)
        for density in [nominal_density] + [
            value for value in densities if value > nominal_density
        ]:
            record = route(
                contract, macro, drawn, synth, variant, work, openroad,
                util=util,
                tag=f"u{int(round(util * 100)):03d}d{int(round(density * 100)):03d}",
                timeout=timeout, must_close=False, density=density,
            )
            attempts.append(record)
            if record["closed_clean"] or not record["failure_blames_place_density"]:
                break
        final = dict(attempts[-1])
        # A timeout is not a refusal. It says nothing about whether the die is
        # feasible, and recording it as "did not close" would let a slow machine
        # manufacture a die floor out of nothing.
        if any(attempt["timed_out"] for attempt in attempts):
            raise MacroRouteError(
                f"{macro['name']}: a die-floor probe at utilization {util} timed out after "
                f"{timeout}s. A timeout is not a refusal and must not be recorded as one; "
                "raise `die_floor_probe_timeout_s` or run on a machine that finishes it."
            )
        final["density_attempts"] = [
            {
                "tag": attempt["tag"],
                "place_density": attempt["place_density"],
                "converged": attempt["converged"],
                "closed_clean": attempt["closed_clean"],
                "failure_stage": attempt.get("failure_stage"),
                "failure_blames_place_density": attempt["failure_blames_place_density"],
                "failure_reason": attempt.get("failure_reason"),
            }
            for attempt in attempts
        ]
        final["floor_limited_by_place_density"] = bool(
            not final["closed_clean"] and final["failure_blames_place_density"]
        )
        steps.append(final)
    closed = [step for step in steps if step["closed_clean"]]
    failed = [step for step in steps if not step["closed_clean"]]
    density_limited = [step for step in failed if step["floor_limited_by_place_density"]]
    tightest = min(closed, key=lambda step: step["die_area_um2"]) if closed else nominal
    if failed and not densities:
        raise MacroRouteError(
            f"{macro['name']}: a die-floor probe refused the die, but the contract names no "
            "`die_floor_probe_place_densities` escalation ladder. Every such refusal so far "
            "has come from OpenROAD's global placer naming this runner's own target density "
            "as the remedy, so without a ladder the reported floor is a property of "
            "run_ihp_rom_macro_route.py and not of the design."
        )
    return {
        "ladder": ladder,
        "place_density_ladder": densities,
        "steps": steps,
        "bracketed": bool(failed),
        "tightest_closing": tightest,
        "tightest_closing_is_the_nominal_die": not closed,
        "first_failing": failed[0] if failed else None,
        "floor_limited_by_place_density": bool(density_limited),
        "interpretation": (
            (
                "the nominal die is bracketed: a tighter die of the same netlist does not "
                "route, and the refusal survives every placement density the contract "
                "escalates through"
                if not density_limited
                else "the nominal die is bracketed only AT THE TOP OF THIS RUNNER'S PLACEMENT "
                     "DENSITY LADDER: the tightest refusal still names the target density as "
                     "its remedy, so the floor is a property of the ladder as much as of the "
                     "design"
            )
            if failed
            else "NOT bracketed: every probed die routed clean, so the reported die area is "
                 "an upper bound with no measured floor under it and the efficiency taken "
                 "from it is only known to be pessimistic"
        ),
    }


def _stage_note(measured: list[dict[str, Any]]) -> str:
    """Which stage refused each die, and what that licenses.

    A refusal at placement says the standard cells stopped fitting; a refusal at
    routing would say the wires stopped fitting. They are different claims about
    a different bottleneck and the report must not blur them, so the stages are
    enumerated from what actually happened rather than asserted.
    """
    stages = sorted(
        {
            step["failure_stage"]
            for entry in measured
            for step in entry["die_floor_probe"]["steps"]
            if step.get("failure_stage")
        }
    )
    preamble = (
        "a floor found at placement means the standard cells stopped fitting on the "
        "smaller die; a floor found at routing would mean the wires stopped fitting. "
        "Every refusal was re-tried at each rung of the contract's placement-density "
        "ladder before it was allowed to count, because the placer's target density is "
        "a constant this runner chose and GPL-0302 names it as the remedy. "
    )
    if not stages:
        return preamble + (
            "NO PROBE REFUSED A DIE AT ALL, so nothing here is a floor and every "
            "efficiency reported is only known to be pessimistic."
        )
    listed = stages[0] if len(stages) == 1 else (
        ", ".join(stages[:-1]) + " and " + stages[-1]
    )
    routing = [name for name in stages if "routing" in name]
    if routing:
        return preamble + (
            f"These probes fail at {listed}. The {', '.join(routing)} refusals are "
            "ROUTABILITY floors; the placement refusals are CELL-AREA floors for this "
            "periphery, which a custom periphery with fewer cells would move."
        )
    return preamble + (
        f"These probes fail at {listed} — never at routing — so what is measured is a "
        "CELL-AREA floor for this periphery and not a routability floor. A custom "
        "periphery with fewer cells would move it."
    )


def markdown_report(result: dict[str, Any]) -> str:
    boundary = result["claim_boundary"]
    lines = [
        "# IHP SG13G2 routed mask-ROM macro area",
        "",
        f"**Status:** **{result['status'].upper()}**  ",
        "**Evidence class:** drawn bit array plus synthesised, placed and fully routed standard-cell periphery; **130 nm**; not silicon  ",
        f"**PDK:** `{result['pdk']['variant']}` / `{result['pdk']['release']}` / `{result['pdk']['commit']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}`  **OpenROAD:** `{result['macros'][0]['route']['openroad_version']}`  "
        f"**Yosys:** `{result['macros'][0]['synthesis']['yosys_version']}`",
        "",
        "## What routing found that bitcell geometry could not",
        "",
        "@TAPLESS@",
        "",
        "## Inputs this run did not invent",
        "",
        "@INPUTS@",
        "",
        "## Measured areas",
        "",
        "| Macro | Bits | Bit-array area | Drawn macro | Macro-internal efficiency | Std-cell periphery | Routed die | **Array efficiency** |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for macro in result["macros"]:
        lines.append(
            f"| `{macro['name']}` ({macro['rows']}×{macro['cols']}, c{macro['mux']}) | {macro['bits']:,} | "
            f"{macro['bit_array_area_um2']:.1f} µm² | {macro['drawn']['macro_area_um2']:.1f} µm² | "
            f"{macro['macro_internal_efficiency'] * 100:.2f}% | "
            f"{macro['synthesis']['standard_cell_area_um2']:.1f} µm² | "
            f"{macro['route']['die_area_um2']:.1f} µm² | **{macro['array_efficiency'] * 100:.2f}%** |"
        )
    comparison = result["comparison"]
    lines.extend(
        [
            "",
            "Every routed macro closed detailed routing with "
            f"{max(m['route']['detailed_route_violations'] for m in result['macros'])} violations.",
            "",
            "## Against the assumed constant, and against a real memory",
            "",
            f"- `rom.array_efficiency` is **{comparison['assumed']:.2f}**, graded `{comparison['assumed_grade']}`.",
            f"- **Macro-internal efficiency** — bit array ÷ drawn macro, i.e. what the custom",
            f"  part costs in tap bands, wordline strap and bitline escape — is",
            f"  **{comparison['macro_internal_range'][0] * 100:.1f}–{comparison['macro_internal_range'][1] * 100:.1f}%**.",
            f"  On that boundary alone the model's {comparison['assumed']:.2f} is "
            + (
                "*conservative*"
                if comparison["macro_internal_range"][0] > comparison["assumed"]
                else "*not reached at every macro measured*"
            )
            + ".",
            f"- **Whole-macro efficiency** with a synthesised standard-cell periphery is",
            f"  **{comparison['whole_macro_range'][0] * 100:.1f}–{comparison['whole_macro_range'][1] * 100:.1f}%**.",
            f"  On that boundary the model's {comparison['assumed']:.2f} is "
            + (
                "*unreachable*"
                if comparison["whole_macro_range"][1] < comparison["assumed"]
                else "*inside the measured range*"
            )
            + ".",
            "",
            "The two numbers differ by more than a factor of two and the constant does not say",
            "which boundary it means. That ambiguity, not the value, is the defect.",
            "",
            "## How much of the die area is a measurement, and how much is a choice",
            "",
            "The nominal die is **sized from the contract's requested utilization**, so the",
            "whole-macro efficiency above is partly a restatement of that constant rather than a",
            "measurement. To bound how much, this run re-routes the identical netlist on",
            "progressively smaller dies and records whether detailed routing still closes with",
            "zero violations.",
            "",
            "**The placer's target density is a second chosen constant, and the first version of",
            "this probe measured it by accident.** Every refusal that version recorded arrived as",
            "OpenROAD's `GPL-0302`, whose text is *Use a higher -density or re-floorplan with a",
            "larger core area* — the global placer naming this runner's own target density as the",
            "remedy — and the report called the result a measured cell-area floor. A probe is",
            "therefore now re-tried at every rung of "
            f"`{comparison['place_density_ladder']}` before it is allowed to count as a refusal,",
            "and the density each row actually ran at is printed. Read the rows that say *tried*:",
            "each one is a die the first version would have reported as refused.",
            "",
            "| Macro | Utilization | Place density | Die | Detailed route | Array efficiency |",
            "|---|---:|---:|---:|---|---:|",
        ]
    )
    for macro in result["macros"]:
        nominal = macro["route"]
        lines.append(
            f"| `{macro['name']}` | {nominal['requested_utilization']:.2f} (nominal) | "
            f"{nominal['place_density']:.2f} | "
            f"{nominal['die_area_um2']:.1f} µm² | closed, "
            f"{nominal['detailed_route_violations']} violations | "
            f"{macro['array_efficiency'] * 100:.2f}% |"
        )
        for step in macro["die_floor_probe"]["steps"]:
            if step["closed_clean"]:
                outcome = f"closed, {step['detailed_route_violations']} violations"
                die = f"{step['die_area_um2']:.1f} µm²"
                eff = f"{macro['bit_array_area_um2'] / step['die_area_um2'] * 100:.2f}%"
            elif step["converged"]:
                outcome = f"**{step['detailed_route_violations']} violations**"
                die = f"{step['die_area_um2']:.1f} µm²"
                eff = "—"
            else:
                reason = "; ".join(step.get("failure_reason") or ["no diagnostic"])
                outcome = f"**did not close**: {reason}"
                die = f"{step.get('requested_die_area_um2', float('nan')):.1f} µm² requested"
                eff = "—"
            tried = ", ".join(
                f"{attempt['place_density']:.2f}" for attempt in step["density_attempts"]
            )
            density = (
                f"{step['place_density']:.2f}"
                if len(step["density_attempts"]) == 1
                else f"{step['place_density']:.2f} (tried {tried})"
            )
            lines.append(
                f"| `{macro['name']}` | {step['requested_utilization']:.2f} | {density} | "
                f"{die} | {outcome} | {eff} |"
            )
    lines.extend(
        [
            "",
            "At the tightest die that still closes, array efficiency is "
            f"**{comparison['whole_macro_range_at_measured_floor'][0] * 100:.2f}–"
            f"{comparison['whole_macro_range_at_measured_floor'][1] * 100:.2f}%**"
            + (
                ", and a tighter die of the same netlist does not close. That brackets the "
                "reported number between a measured floor and the contract's request: the "
                "efficiency is no longer a restatement of the utilization constant."
                if comparison["die_floor_bracketed"]
                else ". **No probed die failed**, so the floor is not bracketed and "
                     "every efficiency reported here is only known to be pessimistic."
            ),
            "",
            "**Read the stage each probe failed at.** "
            + comparison["die_floor_failure_stages_note"][:1].upper()
            + comparison["die_floor_failure_stages_note"][1:],
            "",
            (
                "**The floor is still partly this runner's.** At least one refusal above "
                "survived to the top rung of the placement-density ladder and its diagnostic "
                "still names the target density as the remedy, so that step brackets the die "
                "at the ladder's top rung and not at a property of the design. Read it as a "
                "floor CONDITIONAL ON the ladder, and widen the ladder to move it."
                if comparison.get("die_floor_limited_by_place_density")
                else "**No refusal above is attributable to the placement density.** Every "
                     "probe that did not close was re-tried up the density ladder and its "
                     "final diagnostic no longer names the target density as the remedy, so "
                     "the refusals are properties of the netlist and the floorplan rather "
                     "than of a constant in this runner."
            ),
            "",
            (
                "**And read the density the tightest die closed at.** The efficiency at the "
                "measured floor is reported at placement densities of "
                + ", ".join(
                    f"`{macro['name']}` {macro['die_floor_probe']['tightest_closing']['place_density']:.2f}"
                    for macro in result["macros"]
                )
                + ". A die that only closes at a high target density has no slack left in it: "
                "no room for an ECO, and none for the power distribution network the next "
                "paragraph says this flow does not build. The floor brackets the die; it does "
                "not propose a floorplan."
            ),
            "",
            "**No power distribution network is built.** This flow runs no `pdngen`, no",
            "`global_connect` and lays no straps. The macro's `VSS` pin is declared in the LEF",
            "and, in the netlist that is routed, is tied to "
            + f"`{result['macros'][0]['synthesis']['array_vss_connected_to']}`"
            + " — a logic constant inserted by",
            "`insert_tiecells`, not a rail. Every die area above is therefore signal routing",
            "only, and a manufacturable macro carries power, so these areas are lower bounds on",
            "that account too.",
            "",
        ]
    )
    if comparison.get("foundry_sram"):
        lines.extend(
            [
                "For scale, IHP's own SRAM macros at comparable capacity, measured the same way",
                "(bitcell pitch area ÷ LEF footprint), reach:",
                "",
                "| Foundry SRAM macro | Bits | Array efficiency |",
                "|---|---:|---:|",
            ]
        )
        for entry in comparison["foundry_sram"]:
            lines.append(
                f"| `{entry['macro']}` | {entry['bits']:,} | {entry['array_efficiency'] * 100:.2f}% |"
            )
        lines.extend(
            [
                "",
                "A memory compiler's periphery is custom layout; this one is standard cells at a",
                "placement density the router would accept. **That is why the routed number is a",
                "lower bound and must not be quoted as the efficiency a ROM product would have.**",
                "",
            ]
        )
    lines.extend(["## Claim boundary", ""])
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_ihp_rom_macro_route.py",
            "```",
            "",
        ]
    )
    controls = [m for m in result["macros"] if m.get("tapless_control")]
    if controls:
        control = controls[0]["tapless_control"]
        tapless = (
            "**A minimum-pitch ROM array is not legal without periodic substrate taps.** This run "
            "drew the same "
            f"{controls[0]['rows']} × {controls[0]['cols']} array with the tap bands removed and "
            f"the installed public deck returned **{control['drc_errors']:,} DRC errors**, all of them "
            + " and ".join(f"*{rule}*" for rule in control["latch_up_rules"])
            + ". The tap bands that fix it are real area, they scale with array height, and a density "
            "number taken from bitcell pitch alone does not contain them."
        )
    else:
        tapless = (
            "**Nothing in this run measured what happens without tap bands.** The control was not "
            "requested, so the necessity of the tap bands is asserted here rather than shown."
        )
    inputs = result["measured_inputs"]
    inputs_block = "\n".join(
        [
            "Two numbers enter this run from elsewhere. Neither is written in this runner's",
            "source or in its contract; both are read from the artifact of the run that measured",
            "them, and the run refuses to start if that artifact is missing or was produced by a",
            "different revision of the layout generator.",
            "",
            "| Quantity | Value | Read from |",
            "|---|---:|---|",
            f"| ROM bitcell area | {inputs['rom_bitcell_area']['cell_area_um2']:.6f} µm² "
            f"| `{inputs['rom_bitcell_area']['source']}` |",
            f"| Wordline pin capacitance | {inputs['wordline_capacitance']['ff_per_column']:.4f} fF/column "
            f"| `{inputs['wordline_capacitance']['source']}` |",
        ]
    )
    return "\n".join(lines).replace("@TAPLESS@", tapless).replace("@INPUTS@", inputs_block)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--netgen", type=Path)
    parser.add_argument("--yosys", type=Path)
    parser.add_argument("--openroad", type=Path, default=Path("/usr/bin/openroad"))
    parser.add_argument("--only", action="append")
    parser.add_argument("--keep-build", action="store_true")
    args = parser.parse_args()

    build: Path | None = None
    try:
        contract = common.strict_json(CONTRACT_PATH)
        lock = common.strict_json(repository_path(contract["pdk_lock"]))
        validate_contract(contract, lock)
        if args.validate_only:
            print("PASS: IHP ROM macro contract and no-scaling boundary")
            return 0

        pdk, variant = bitcell.locate_pdk(args.pdk_root)
        magic, netgen = common.locate_tools(lock, args.tool_root, args.magic, args.netgen)
        pdk_identity = bitcell.verify_pdk(pdk, lock)
        identities = common.tool_identities(magic, netgen, lock)
        yosys = (
            args.yosys
            if args.yosys
            else Path.home() / ".local" / "opentallas-tools" / "yosys-0.68" / "bin" / "yosys"
        ).expanduser().resolve()
        openroad = args.openroad.expanduser().resolve()
        for tool in (yosys, openroad):
            if not os.access(tool, os.X_OK):
                raise MacroRouteError(f"required tool is not executable: {tool}")

        build_parent = ROOT / "spice" / "build"
        build_parent.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix="ihp_sg13g2_rom_macro.", dir=build_parent))

        bitcell_area = measured_bitcell_area_um2(contract)
        wordline = measured_wordline_capacitance(contract)

        selected = [
            macro for macro in contract["macros"]
            if args.only is None or macro["name"] in args.only
        ]
        measured = []
        for macro in selected:
            work = build / macro["name"]
            work.mkdir(parents=True, exist_ok=True)
            drawn = draw_array(contract, macro, magic, variant, pdk, work, bitcell_area)
            control = (
                tapless_control(contract, macro, magic, variant, pdk, work)
                if macro.get("run_tapless_control")
                else None
            )
            write_views(contract, macro, drawn, work, wordline)
            synth = synthesise(contract, variant, work, yosys)
            routed = route(contract, macro, drawn, synth, variant, work, openroad)
            floor = die_floor_probe(
                contract, macro, drawn, synth, variant, work, openroad, routed
            )
            bits = macro["rows"] * macro["cols"]
            bit_area = bits * bitcell_area["cell_area_um2"]
            if bit_area > drawn["macro_area_um2"]:
                raise MacroRouteError(
                    f"{macro['name']}: {bits} bits at {bitcell_area['cell_area_um2']} um2 is "
                    f"{bit_area:.1f} um2, larger than the drawn macro {drawn['macro_area_um2']:.1f} um2; "
                    "the bit array and the drawn macro are not the same layout"
                )
            drawn_record = dict(drawn)
            drawn_record.pop("lef")
            floor_die = floor["tightest_closing"]["die_area_um2"]
            measured.append(
                {
                    **{k: macro[k] for k in ("name", "rows", "cols", "mux", "tap_every", "utilization")},
                    "bits": bits,
                    "bit_array_area_um2": bit_area,
                    "bitcell_area_um2": bitcell_area["cell_area_um2"],
                    "drawn": drawn_record,
                    "tapless_control": control,
                    "synthesis": synth,
                    "route": routed,
                    "die_floor_probe": floor,
                    "macro_internal_efficiency": bit_area / drawn["macro_area_um2"],
                    "array_efficiency": bit_area / routed["die_area_um2"],
                    "array_efficiency_at_measured_floor": bit_area / floor_die,
                }
            )

        technology = common.strict_json(ROOT / "configs" / "hardware" / "technology.json")
        assumed = float(technology["rom"]["array_efficiency"]["value"])
        sram_path = ROOT / "results" / "spice" / "ihp_sg13g2_bitcell" / "bitcell.json"
        foundry = []
        if sram_path.is_file():
            sram = json.loads(sram_path.read_text(encoding="utf-8"))
            wanted = {macro["bits"] for macro in measured}
            for entry in sram["sram_array_efficiency"]["per_macro"]:
                if entry["family"] == "1P" and entry["bits"] in wanted:
                    foundry.append(entry)
            foundry.sort(key=lambda entry: (entry["bits"], entry["macro"]))

        result = {
            "schema_version": 1,
            "experiment_id": contract["experiment_id"],
            "status": "pass",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "contract": {
                "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
                "sha256": common.sha256_file(CONTRACT_PATH),
            },
            "inputs": {
                name: {
                    "path": value,
                    "sha256": common.sha256_file(repository_path(value)),
                    "size_bytes": repository_path(value).stat().st_size,
                }
                for name, value in sorted(contract["inputs"].items())
            },
            "pdk": pdk_identity,
            "toolchain": {
                **identities,
                "yosys": {"path": str(yosys), "sha256": common.sha256_file(yosys)},
                "openroad": {"path": str(openroad), "sha256": common.sha256_file(openroad)},
            },
            "macros": measured,
            "measured_inputs": {
                "rom_bitcell_area": bitcell_area,
                "wordline_capacitance": wordline,
                "note": (
                    "both are read from the runs that measured them and neither is "
                    "restated in this runner's source or in its contract"
                ),
            },
            "comparison": {
                "assumed": assumed,
                "assumed_grade": technology["rom"]["array_efficiency"]["grade"],
                "assumed_source": "configs/hardware/technology.json#rom.array_efficiency",
                "macro_internal_range": [
                    min(m["macro_internal_efficiency"] for m in measured),
                    max(m["macro_internal_efficiency"] for m in measured),
                ],
                "whole_macro_range": [
                    min(m["array_efficiency"] for m in measured),
                    max(m["array_efficiency"] for m in measured),
                ],
                "whole_macro_range_at_measured_floor": [
                    min(m["array_efficiency_at_measured_floor"] for m in measured),
                    max(m["array_efficiency_at_measured_floor"] for m in measured),
                ],
                "die_floor_bracketed": all(
                    m["die_floor_probe"]["bracketed"] for m in measured
                ),
                "die_floor_limited_by_place_density": any(
                    m["die_floor_probe"]["floor_limited_by_place_density"]
                    for m in measured
                ),
                "place_density_ladder": (
                    measured[0]["die_floor_probe"]["place_density_ladder"]
                ),
                # The runner's own constants, recorded rather than left in the
                # source. A die area sized under a target density that appears
                # nowhere in the result is a die area a reader cannot audit,
                # and that is how the first die-floor probe came to report a
                # floor at 0.85 as a property of the design.
                "place_density_nominal_cap": PLACE_DENSITY_NOMINAL_CAP,
                "place_density_headroom_over_utilization": PLACE_DENSITY_HEADROOM,
                "place_density_formula": (
                    "min(place_density_nominal_cap, utilization + "
                    "place_density_headroom_over_utilization), then escalated up "
                    "place_density_ladder for any die-floor probe whose refusal names the "
                    "target density as its remedy"
                ),
                "die_floor_failure_stages": sorted(
                    {
                        step["failure_stage"]
                        for m in measured
                        for step in m["die_floor_probe"]["steps"]
                        if step.get("failure_stage")
                    }
                ),
                "die_floor_failure_stages_note": _stage_note(measured),
                "foundry_sram": foundry,
            },
            "claim_boundary": contract["claim_boundary"],
            "reports": dict(contract["reports"]),
        }

        destination = repository_path(contract["reports"]["artifacts"])
        destination.mkdir(parents=True, exist_ok=True)
        artifacts = []
        probe_reports = {
            entry["name"]: [
                f"route_drc_{attempt['tag']}.rpt"
                for step in entry["die_floor_probe"]["steps"]
                for attempt in step["density_attempts"]
            ]
            for entry in measured
        }
        for macro in selected:
            names = ["ihp_rom_bitarray.lef", "netlist.v", "route_drc.rpt"]
            # The probes' own DRC reports are archived too: a probe that fails is
            # the evidence that the nominal die is a floor, and evidence nobody
            # can open is not evidence.
            names += probe_reports.get(macro["name"], [])
            # Anything this macro left behind on a previous run and does not
            # produce now is deleted. A probe renamed or removed used to leave
            # its old report sitting in the results directory, indistinguishable
            # from evidence this run actually produced, and the manifest below
            # would simply not mention it.
            keep = {f"{macro['name']}_{name}" for name in names}
            for stale in sorted(destination.glob(f"{macro['name']}_*")):
                if stale.name not in keep:
                    stale.unlink()
            for name in names:
                source = build / macro["name"] / name
                if source.is_file():
                    target = destination / f"{macro['name']}_{name}"
                    shutil.copy2(source, target)
                    artifacts.append(
                        {
                            "path": target.relative_to(ROOT).as_posix(),
                            "sha256": common.sha256_file(target),
                            "size_bytes": target.stat().st_size,
                        }
                    )
        result["artifacts"] = artifacts

        json_path = repository_path(contract["reports"]["json"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        repository_path(contract["reports"]["markdown"]).write_text(
            markdown_report(result), encoding="utf-8"
        )
        for macro in measured:
            print(
                f"PASS: {macro['name']} {macro['bits']} bits; drawn macro "
                f"{macro['drawn']['macro_area_um2']:.1f} um2 ({macro['macro_internal_efficiency']*100:.1f}% internal); "
                f"routed die {macro['route']['die_area_um2']:.1f} um2 "
                f"({macro['array_efficiency']*100:.1f}% array efficiency)"
            )
        return 0
    except (MacroRouteError, bitcell.BitcellError, common.PhysicalExperimentError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        if build is not None and build.exists():
            if args.keep_build:
                print(f"Kept build directory: {build}")
            else:
                shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
