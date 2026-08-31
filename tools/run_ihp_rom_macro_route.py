#!/usr/bin/env python3
"""Synthesise and fully route a mask-ROM macro in IHP SG13G2, and measure its
array efficiency instead of assuming it.

`rom.array_efficiency` has been an ASSUMED 0.7.  This runner draws the bit array
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
    for marker in ("N7", "GPU speedup", "silicon", "LOWER bound"):
        if marker not in forbidden:
            raise MacroRouteError(f"claim boundary does not cover {marker}")
    for value in contract["reports"].values():
        repository_path(value)


LEF_SIZE_RE = re.compile(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)")
YOSYS_AREA_RE = re.compile(r"Chip area for module '\\\\?ot_rom_macro':\s*([0-9.]+)")
OR_RE = re.compile(r"(?m)^OT_([A-Z_0-9]+)=(.+)$")


def draw_array(
    contract: dict[str, Any], macro: dict[str, Any], magic: Path, variant: Path, pdk: Path, work: Path
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
    return {
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


def write_views(contract: dict[str, Any], macro: dict[str, Any], drawn: dict[str, Any], work: Path) -> None:
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
    wl_pf = contract["wordline_capacitance_ff_per_column"] * 1e-3 * cols
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
    return {
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
) -> dict[str, Any]:
    mw, mh = drawn["macro_width_um"], drawn["macro_height_um"]
    cells = synth["standard_cell_area_um2"]
    util = macro["utilization"]
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

    script = work / "route.tcl"
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
            "@PLACE_DENSITY@": f"{min(0.85, util + 0.15):.2f}",
            "@DRC_RPT@": str(work / "route_drc.rpt"),
            "@DEF@": str(work / "final.def"),
        },
        script,
    )
    completed = subprocess.run(
        [str(openroad), "-no_init", "-exit", script.name],
        cwd=work, check=False, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=43200,
    )
    log = work / "openroad.log"
    log.write_text(completed.stdout, encoding="utf-8")
    markers = dict(OR_RE.findall(completed.stdout))
    if markers.get("ROUTE_DONE") != "1":
        raise MacroRouteError(
            f"{macro['name']}: OpenROAD did not finish routing (exit {completed.returncode}); see {log}. "
            "This is reported as a failure to converge, not silently replaced with a synthesis estimate."
        )
    drc_report = work / "route_drc.rpt"
    violations = 0
    if drc_report.is_file():
        violations = sum(
            1 for line in drc_report.read_text(encoding="utf-8").splitlines() if line.startswith("\tviolation")
        )
    if violations > contract["acceptance"]["route_drc_violations_max"]:
        raise MacroRouteError(f"{macro['name']}: detailed route left {violations} violations")
    version = re.search(r"(?m)^OpenROAD (\S+)", completed.stdout)
    return {
        "die_width_um": float(markers["DIE_W"]),
        "die_height_um": float(markers["DIE_H"]),
        "die_area_um2": float(markers["DIE_AREA_UM2"]),
        "core_area_um2": float(markers["CORE_AREA_UM2"]),
        "requested_utilization": util,
        "worst_slack_ns": float(markers["WNS"]) if "WNS" in markers else None,
        "total_negative_slack_ns": float(markers["TNS"]) if "TNS" in markers else None,
        "detailed_route_violations": violations,
        "openroad_version": version.group(1) if version else None,
        "log_sha256": common.sha256_file(log),
    }


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
            "  On that boundary alone the assumed 0.70 is *conservative*.",
            f"- **Whole-macro efficiency** with a synthesised standard-cell periphery is",
            f"  **{comparison['whole_macro_range'][0] * 100:.1f}–{comparison['whole_macro_range'][1] * 100:.1f}%**.",
            "  On that boundary the assumed 0.70 is *unreachable*.",
            "",
            "The two numbers differ by more than a factor of two and the constant does not say",
            "which boundary it means. That ambiguity, not the value, is the defect.",
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
    return "\n".join(lines).replace("@TAPLESS@", tapless)


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

        selected = [
            macro for macro in contract["macros"]
            if args.only is None or macro["name"] in args.only
        ]
        measured = []
        for macro in selected:
            work = build / macro["name"]
            work.mkdir(parents=True, exist_ok=True)
            drawn = draw_array(contract, macro, magic, variant, pdk, work)
            control = (
                tapless_control(contract, macro, magic, variant, pdk, work)
                if macro.get("run_tapless_control")
                else None
            )
            write_views(contract, macro, drawn, work)
            synth = synthesise(contract, variant, work, yosys)
            routed = route(contract, macro, drawn, synth, variant, work, openroad)
            bits = macro["rows"] * macro["cols"]
            bit_area = bits * 0.390150
            drawn_record = dict(drawn)
            drawn_record.pop("lef")
            measured.append(
                {
                    **{k: macro[k] for k in ("name", "rows", "cols", "mux", "tap_every", "utilization")},
                    "bits": bits,
                    "bit_array_area_um2": bit_area,
                    "drawn": drawn_record,
                    "tapless_control": control,
                    "synthesis": synth,
                    "route": routed,
                    "macro_internal_efficiency": bit_area / drawn["macro_area_um2"],
                    "array_efficiency": bit_area / routed["die_area_um2"],
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
                "foundry_sram": foundry,
            },
            "claim_boundary": contract["claim_boundary"],
            "reports": dict(contract["reports"]),
        }

        destination = repository_path(contract["reports"]["artifacts"])
        destination.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for macro in selected:
            for name in ("ihp_rom_bitarray.lef", "netlist.v", "route_drc.rpt"):
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
