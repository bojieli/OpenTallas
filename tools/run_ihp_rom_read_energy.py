#!/usr/bin/env python3
"""Measure mask-ROM array read energy from extracted IHP SG13G2 geometry.

`energy.rom_read_j_per_byte` has been an ASSUMED scalar.  This runner replaces
the assumption with a measurement inside one installed open foundry PDK, and in
doing so shows the constant is under-specified: read energy per bit is affine in
column height, not constant, and at the minimum legal column pitch most of the
bitline capacitance is coupling to the neighbouring bitlines, so the energy is
also data-pattern dependent.

IHP SG13G2 is a 130 nm process.  Nothing here is scaled to N7/N6/N5/N4.
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from itertools import product
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
CONTRACT_PATH = ROOT / "spice" / "ihp_sg13g2" / "bitcell" / "read_energy_contract.json"

CAP_RE = re.compile(r"(?mi)^C\S*\s+(\S+)\s+(\S+)\s+([0-9.eE+-]+)([a-zA-Z]*)\s*$")
SUFFIX = {"": 1.0, "f": 1e-15, "p": 1e-12, "n": 1e-9, "a": 1e-18, "u": 1e-6}
WARNING_RE = re.compile(r"(?mi)^\s*warning:\s*(.+)$")
# Exactly the warnings this deck is expected to raise, matched precisely. A broad
# prefix filter here would be the same defect class this program keeps finding:
# legal values, no trap, nothing refused.
BENIGN_WARNING_RES = (
    re.compile(r"^m=xx on \.subckt line will override multiplier m hierarchy!$"),
    re.compile(r"^v\w+: no dc value, transient time 0 value used$"),
)


class ReadEnergyError(RuntimeError):
    """A governed read-energy input or acceptance gate failed."""


def repository_path(value: str) -> Path:
    try:
        return common.repository_path(value)
    except common.PhysicalExperimentError as exc:
        raise ReadEnergyError(str(exc)) from exc


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise ReadEnergyError("read-energy contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_rom_array_read_energy_v1":
        raise ReadEnergyError("unexpected read-energy experiment_id")
    if contract.get("pdk_lock") != "configs/pdk/ihp_sg13g2_physical_lock.json":
        raise ReadEnergyError("read-energy contract must use the governed IHP lock")
    if lock.get("pdk", {}).get("variant") != "ihp-sg13g2":
        raise ReadEnergyError("read-energy measurement requires IHP SG13G2")
    for value in contract["inputs"].values():
        if not repository_path(value).is_file():
            raise ReadEnergyError(f"missing governed input: {value}")
    dims = contract["dimensions"]
    if set(dims) != {"process_corner", "vdd_v", "temperature_c", "selected_row"}:
        raise ReadEnergyError("incomplete read-energy dimensions")
    if any(value >= 1.5 for value in dims["vdd_v"]):
        raise ReadEnergyError("IHP LV sweep must stay below the published 1.5-V VDS maximum")
    rows = contract["array"]["pvt_rows"]
    if any(value >= rows or value < 0 for value in dims["selected_row"]):
        raise ReadEnergyError("selected_row values must index the simulated array")
    boundary = contract["claim_boundary"]
    if (
        boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("boundary_of_the_measured_quantity")
    ):
        raise ReadEnergyError("read-energy claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for marker in ("N7", "GPU speedup", "silicon"):
        if marker not in forbidden:
            raise ReadEnergyError(f"claim boundary does not cover {marker}")
    for value in contract["reports"].values():
        repository_path(value)


def build_array(
    contract: dict[str, Any],
    magic: Path,
    variant: Path,
    pdk: Path,
    build: Path,
    rows: int,
) -> dict[str, Any]:
    array = contract["array"]
    generator = repository_path(contract["inputs"]["generator"])
    overrides = {
        "NROW": rows,
        "NCOL": array["columns"],
        "PATTERN": array["pattern"],
    }
    run = bitcell.run_generator(
        magic, variant, pdk, generator, overrides, build / f"array_{rows}", extract=True
    )
    if run["drc_errors"] != contract["acceptance"]["drc_errors_max"]:
        raise ReadEnergyError(
            f"{rows}-row array is not DRC clean: {run['drc_errors']} errors"
        )
    pex = run["workdir"] / "ihp_rom_bitarray.pex.spice"
    if not pex.is_file():
        raise ReadEnergyError(f"{rows}-row array did not produce a PEX netlist")
    ports = bitcell.check_ports(pex, rows, array["columns"], ReadEnergyError)
    bits_path = run["workdir"] / "programmed_bits.txt"
    programmed = {
        (int(a), int(b))
        for a, b in (
            line.split() for line in bits_path.read_text(encoding="utf-8").split("\n") if line.strip()
        )
    }
    expected_devices = rows * array["columns"]
    devices = sum(
        1
        for line in (run["workdir"] / "ihp_rom_bitarray.extracted.spice")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.startswith("X") and "sg13_lv_nmos" in line
    )
    if devices != expected_devices:
        raise ReadEnergyError(f"{rows}-row array extracted {devices} of {expected_devices} devices")
    return {
        "rows": rows,
        "columns": array["columns"],
        "pex": pex,
        "workdir": run["workdir"],
        "programmed": programmed,
        "devices": devices,
        "ports": ports,
        "capacitance": bitline_capacitance(pex, array["columns"]),
    }


def bitline_capacitance(pex: Path, columns: int) -> dict[str, Any]:
    incident: dict[str, float] = {}
    to_bitline: dict[str, float] = {}
    wordline: dict[str, float] = {}
    elements = 0
    for line in pex.read_text(encoding="utf-8").splitlines():
        match = CAP_RE.match(line.strip())
        if match is None:
            continue
        left, right, value, suffix = match.groups()
        farads = float(value) * SUFFIX.get(suffix.lower(), 1.0)
        elements += 1
        for node, other in ((left, right), (right, left)):
            if node.upper().startswith("WL"):
                wordline[node] = wordline.get(node, 0.0) + farads
            if not node.upper().startswith("BL"):
                continue
            incident[node] = incident.get(node, 0.0) + farads
            if other.upper().startswith("BL"):
                to_bitline[node] = to_bitline.get(node, 0.0) + farads
    interior = [f"BL{index}" for index in range(1, columns - 1)]
    values = [incident[name] for name in interior if name in incident]
    if not values:
        raise ReadEnergyError(f"{pex}: no interior bitline capacitance extracted")
    mean = sum(values) / len(values)
    coupled = sum(to_bitline.get(name, 0.0) for name in interior if name in incident) / len(values)
    return {
        "elements": elements,
        "interior_bitlines": interior,
        "interior_mean_total_ff": mean * 1e15,
        "interior_mean_neighbour_coupled_ff": coupled * 1e15,
        "neighbour_coupled_fraction": coupled / mean,
        "per_bitline_ff": {name: incident[name] * 1e15 for name in sorted(incident)},
        # Interconnect only. ext2spice writes the wiring parasitics; the row
        # transistors' gate capacitance is inside the device model and is NOT a
        # C element here, so this number is a floor on the wordline load and
        # must never be used as the Liberty pin capacitance.
        "wordline_interconnect_mean_ff": (
            sum(wordline.values()) / len(wordline) * 1e15 if wordline else 0.0
        ),
    }


def linear_fit(points: list[tuple[float, float]]) -> dict[str, float]:
    n = len(points)
    sx = sum(x for x, _ in points)
    sy = sum(y for _, y in points)
    sxx = sum(x * x for x, _ in points)
    sxy = sum(x * y for x, y in points)
    denominator = n * sxx - sx * sx
    slope = (n * sxy - sx * sy) / denominator
    intercept = (sy - slope * sx) / n
    mean = sy / n
    ss_total = sum((y - mean) ** 2 for _, y in points)
    ss_residual = sum((y - (slope * x + intercept)) ** 2 for x, y in points)
    r2 = 1.0 if ss_total == 0 else 1.0 - ss_residual / ss_total
    return {"slope": slope, "intercept": intercept, "r2": r2}


ABSOLUTE_PATH_RE = re.compile(r"/\S+")


def canonical_deck(text: str) -> str:
    """The deck with every absolute path reduced to its file name.

    `deck_sha256` looks like a reproducibility anchor and is not one: the deck
    written for each case carries `.include "<mkdtemp>/array_64/...pex.spice"`
    and `.lib "<pdk root>/..."`, so its hash changes on every run of an
    unchanged experiment. That is the same trap the bitcell runner already found
    in Magic's clock-stamped `.mag` -- a hash a reader cannot reproduce on a
    correct run, and which therefore proves nothing whether they check it or
    not.

    Stripping the directories leaves exactly the part of the deck that is the
    experiment: the models, the sources, the instances and the `.measure`
    statements. `canonical_deck_sha256` IS reproducible, and the runner refuses
    to record it unless the canonicalisation actually removed every absolute
    path -- otherwise the new hash would inherit the old one's defect while
    looking like the fix.
    """
    return ABSOLUTE_PATH_RE.sub(lambda match: Path(match.group(0)).name, text)


def canonical_deck_digest(deck: Path, error: type[Exception]) -> str:
    text = canonical_deck(deck.read_text(encoding="utf-8"))
    stray = ABSOLUTE_PATH_RE.search(text)
    if stray is not None:
        raise error(
            f"{deck}: the canonical deck still contains the absolute path "
            f"{stray.group(0)!r}, so its digest would change with the build directory "
            "and would not be a reproducibility anchor"
        )
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def write_deck(
    contract: dict[str, Any], array: dict[str, Any], case: dict[str, Any], path: Path, model_lib: Path
) -> None:
    timing = contract["timing"]
    rows, columns = array["rows"], array["columns"]
    vdd = case["vdd_v"]
    period = timing["period_ns"]
    cycles = timing["cycles"]
    selected = case["selected_row"]
    access = case["access"]

    pre = [(0.0, 0.0)]
    wl = [(0.0, 0.0)]
    for index in range(cycles):
        start = index * period
        pre += [
            (start + period / 2 - 0.05, 0.0),
            (start + period / 2, vdd),
            (start + period - 0.05, vdd),
            (start + period, 0.0),
        ]
        if access:
            wl += [
                (start + period / 2 + 0.05, 0.0),
                (start + period / 2 + 0.10, vdd),
                (start + period - 0.15, vdd),
                (start + period - 0.10, 0.0),
            ]

    def pwl(points: list[tuple[float, float]]) -> str:
        return "PWL(" + " ".join(f"{t:g}n {v:g}" for t, v in points) + ")"

    lines = [
        ".title OpenTallas IHP SG13G2 extracted mask-ROM array read energy",
        f".temp {case['temperature_c']:g}",
        f'.lib "{model_lib}" mos_{case["process_corner"]}',
        f'.include "{array["pex"]}"',
        f".param VDDVAL={vdd:g}",
        "VDDA VDDA 0 {VDDVAL}",
        "VSSA VSS 0 0",
        "VPRE PRE 0 " + pwl(pre),
    ]
    for row in range(rows):
        if row == selected and access:
            lines.append(f"VWL{row} WL{row} 0 " + pwl(wl))
        else:
            lines.append(f"VWL{row} WL{row} 0 0")
    for column in range(columns):
        lines.append(
            f"XPRE{column} BL{column} PRE VDDA VDDA {contract['array']['precharge_device']}"
        )
    lines.append(
        "XARRAY VSS "
        + " ".join(f"WL{row}" for row in range(rows))
        + " "
        + " ".join(f"BL{column}" for column in range(columns))
        + " ihp_rom_bitarray"
    )
    lines.append(".ic " + " ".join(f"v(BL{column})=0" for column in range(columns)))
    lines.append(f".tran 2p {cycles * period:g}n")
    start = (cycles - 1) * period
    stop = cycles * period
    lines.append(f".measure tran e_cycle INTEG par('-v(VDDA)*i(VDDA)') FROM={start:g}n TO={stop:g}n")
    lines.append(f".measure tran q_cycle INTEG par('-i(VDDA)') FROM={start:g}n TO={stop:g}n")
    if access:
        lines.append(
            f".measure tran e_wl INTEG par('-v(WL{selected})*i(VWL{selected})') "
            f"FROM={start:g}n TO={stop:g}n"
        )
        # Charge delivered by the wordline driver across the RISING edge only.
        # e_wl above integrates over the whole cycle, so it is a dissipated
        # energy and NOT 1/2 C V^2: it cannot be inverted for a pin
        # capacitance.  The macro Liberty needs an input capacitance, so
        # measure the charge and divide by the rail, which is the definition of
        # an effective capacitance and does not depend on the gate being
        # linear.
        #
        # TWO windows, because they are not the same number and the difference
        # is a real effect rather than noise.  `q_wl` closes 50 ps after the
        # wordline reaches the rail: it is the transition charge and it is what
        # a Liberty pin capacitance means.  `q_wl_hold` runs on to just before
        # the wordline falls, so it also contains the charge the DISCHARGING
        # bitlines pull back out through the row transistors' gate-drain
        # overlap.  Reporting only the second would understate the wordline
        # load by that coupling, size the wordline drivers small, and quietly
        # flatter the macro's array efficiency.
        rise_open = start + period / 2 + 0.04
        rise_shut = start + period / 2 + 0.15
        hold_shut = start + period - 0.15
        lines.append(
            f".measure tran q_wl INTEG par('-i(VWL{selected})') "
            f"FROM={rise_open:g}n TO={rise_shut:g}n"
        )
        lines.append(
            f".measure tran q_wl_hold INTEG par('-i(VWL{selected})') "
            f"FROM={rise_open:g}n TO={hold_shut:g}n"
        )
    for column in range(columns):
        lines.append(f".measure tran v_bl{column} FIND v(BL{column}) AT={stop - 0.15:g}n")
    lines.append(".end")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


MEASURE_RE = re.compile(r"(?m)^\s*(e_cycle|q_cycle|e_wl|q_wl_hold|q_wl|v_bl\d+)\s*=\s*([-+0-9.eE]+)")


def run_case(
    contract: dict[str, Any],
    array: dict[str, Any],
    case: dict[str, Any],
    case_dir: Path,
    ngspice: Path,
    init: Path,
    pdk: Path,
    osdi: Path,
    model_lib: Path,
) -> dict[str, Any]:
    case_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(init, case_dir / ".spiceinit")
    deck = case_dir / "read.sp"
    write_deck(contract, array, case, deck, model_lib)
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "TZ": "UTC",
            "OPENTALLAS_IHP_PDK_ROOT": str(pdk),
            "OPENTALLAS_IHP_OSDI_ROOT": str(osdi),
        }
    )
    completed = subprocess.run(
        [str(ngspice), "-b", deck.name],
        cwd=case_dir,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3600,
    )
    log = case_dir / "ngspice.log"
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise ReadEnergyError(f"{case['case_id']}: ngspice failed ({completed.returncode}); see {log}")
    measures = {name: float(value) for name, value in MEASURE_RE.findall(completed.stdout)}
    required = {"e_cycle", "q_cycle"} | {f"v_bl{c}" for c in range(array["columns"])}
    missing = sorted(required - set(measures))
    if missing:
        raise ReadEnergyError(f"{case['case_id']}: ngspice did not produce {missing}")
    if any(not math.isfinite(value) for value in measures.values()):
        raise ReadEnergyError(f"{case['case_id']}: ngspice emitted non-finite measures")
    observed_warnings = [text.strip().lower() for text in WARNING_RE.findall(completed.stdout)]
    warnings = [
        text for text in observed_warnings
        if not any(pattern.match(text) for pattern in BENIGN_WARNING_RES)
    ]
    return {
        "measures": measures,
        "warnings": warnings,
        "all_warnings": sorted(set(observed_warnings)),
        "deck_sha256": common.sha256_file(deck),
        "canonical_deck_sha256": canonical_deck_digest(deck, ReadEnergyError),
        "log_sha256": common.sha256_file(log),
    }


def evaluate_case(
    contract: dict[str, Any], array: dict[str, Any], case: dict[str, Any], observed: dict[str, Any]
) -> dict[str, Any]:
    acceptance = contract["acceptance"]
    columns = array["columns"]
    vdd = case["vdd_v"]
    measures = observed["measures"]
    programmed = [c for c in range(columns) if (c, case["selected_row"]) in array["programmed"]]
    unprogrammed = [c for c in range(columns) if c not in programmed]
    low = [measures[f"v_bl{c}"] / vdd for c in programmed]
    high = [measures[f"v_bl{c}"] / vdd for c in unprogrammed]
    checks = []
    if programmed:
        checks.append(
            (max(low) <= acceptance["programmed_bitline_fraction_max"],
             "programmed bitline did not discharge")
        )
    if programmed and unprogrammed:
        checks.append(
            (min(high) - max(low) >= acceptance["read_margin_fraction_min"],
             "read margin below the declared floor")
        )
    energy_fj = measures["e_cycle"] * 1e15
    checks.append(
        (acceptance["read_energy_fj_min"] < energy_fj <= acceptance["read_energy_fj_max"],
         "read energy outside the declared bounds")
    )
    checks.append(
        (len(observed["warnings"]) <= acceptance["unexpected_warnings_max"],
         "unexpected ngspice warning observed")
    )
    failures = [reason for ok, reason in checks if not ok]
    return {
        "case_id": case["case_id"],
        "process_corner": case["process_corner"],
        "vdd_v": vdd,
        "temperature_c": case["temperature_c"],
        "selected_row": case["selected_row"],
        "ones_in_selected_row": len(programmed),
        "columns": columns,
        "read_energy_fj": energy_fj,
        "read_energy_fj_per_bit": energy_fj / columns,
        "read_energy_j_per_byte": (measures["e_cycle"] / columns) * 8.0,
        "wordline_energy_fj": measures.get("e_wl", 0.0) * 1e15,
        "wordline_charge_fc": measures.get("q_wl", 0.0) * 1e15,
        "wordline_hold_charge_fc": measures.get("q_wl_hold", 0.0) * 1e15,
        "wordline_capacitance_ff_per_column": (
            measures["q_wl"] / vdd / columns * 1e15 if "q_wl" in measures else None
        ),
        "wordline_capacitance_hold_ff_per_column": (
            measures["q_wl_hold"] / vdd / columns * 1e15 if "q_wl_hold" in measures else None
        ),
        "supply_charge_fc": measures["q_cycle"] * 1e15,
        "programmed_bitline_fraction_max": max(low) if low else None,
        "unprogrammed_bitline_fraction_min": min(high) if high else None,
        "read_margin_fraction": (min(high) - max(low)) if (low and high) else None,
        "warnings": observed["warnings"],
        "all_warnings": observed["all_warnings"],
        "deck_sha256": observed["deck_sha256"],
        "canonical_deck_sha256": observed["canonical_deck_sha256"],
        "log_sha256": observed["log_sha256"],
        "status": "pass" if not failures else "fail",
        "failures": failures,
    }


def enumerate_cases(contract: dict[str, Any]) -> list[dict[str, Any]]:
    dims = contract["dimensions"]
    seen: dict[tuple, dict[str, Any]] = {}
    for campaign in contract["campaigns"]:
        axes = campaign["dimensions"]
        fixed = campaign["fixed"]
        for combination in product(*(dims[axis] for axis in axes)):
            case = dict(fixed)
            case.update(dict(zip(axes, combination)))
            key = (
                case["process_corner"],
                case["vdd_v"],
                case["temperature_c"],
                case["selected_row"],
            )
            if key not in seen:
                case["access"] = True
                case["campaigns"] = [campaign["name"]]
                seen[key] = case
            else:
                seen[key]["campaigns"].append(campaign["name"])
    cases = []
    for index, key in enumerate(sorted(seen), start=1):
        case = seen[key]
        case["case_id"] = f"case_{index:03d}"
        cases.append(case)
    return cases


def markdown_report(result: dict[str, Any]) -> str:
    energy = result["energy"]
    caps = result["capacitance_model"]
    boundary = result["claim_boundary"]
    ref = result["reference"]
    lines = [
        "# IHP SG13G2 extracted mask-ROM array read energy",
        "",
        f"**Status:** **{result['status'].upper()}** ({energy['cases_passed']}/{energy['case_count']} cases)",
        "**Evidence class:** deterministic simulation of an extracted minimum-pitch ROM bit array; **130 nm**; not silicon",
        f"**PDK:** `{result['pdk']['variant']}` / `{result['pdk']['release']}` / `{result['pdk']['commit']}`",
        "**Simulator:** ngspice 43 with the pinned official PSP103 OSDI modules",
        "",
        "## What was measured, and what the constant claims",
        "",
        "| Quantity | Value |",
        "|---|---:|",
        f"| Array simulated over PVT | {result['array']['rows']} rows × {result['array']['columns']} columns, minimum legal pitch |",
        f"| Extracted bitline capacitance | {caps['slope_ff_per_row']:.4f} fF per row + {caps['intercept_ff']:.4f} fF (R² = {caps['r2']:.6f}) |",
        f"| Of that, coupling to the two neighbours | **{caps['neighbour_coupled_fraction'] * 100:.1f}%** |",
        f"| Read energy, nominal case | {energy['nominal']['read_energy_fj']:.2f} fJ per access of {result['array']['columns']} bits |",
        f"| Read energy per bit, nominal | **{energy['nominal']['read_energy_fj_per_bit']:.3f} fJ/bit** |",
        f"| Read energy per byte, nominal | **{energy['nominal']['read_energy_j_per_byte']:.3e} J/B** |",
        f"| Wordline effective input capacitance | **{result['wordline_capacitance']['ff_per_column']:.4f} fF per column** |",
        f"| Of which extracted interconnect | {result['wordline_capacitance']['extracted_interconnect_only_ff_per_column']:.4f} fF per column |",
        f"| Assumed `energy.rom_read_j_per_byte` | {ref['assumed_j_per_byte']:.3e} J/B, graded `{ref['assumed_grade']}` |",
        f"| Measured ÷ assumed, at {result['array']['rows']} rows | {energy['nominal']['read_energy_j_per_byte'] / ref['assumed_j_per_byte']:.2f}× |",
        "",
        f"Across the full grid the read energy spans "
        f"{energy['min']['read_energy_fj']:.2f} fJ ({energy['min']['case_id']}, "
        f"{energy['min']['process_corner']}, {energy['min']['vdd_v']} V, {energy['min']['temperature_c']} C) to "
        f"{energy['max']['read_energy_fj']:.2f} fJ ({energy['max']['case_id']}, "
        f"{energy['max']['process_corner']}, {energy['max']['vdd_v']} V, {energy['max']['temperature_c']} C).",
        "",
        "## The constant is under-specified, and this is the finding that matters",
        "",
        "Read energy per bit is **not** a technology constant. It is affine in column height,",
        "because a read discharges a whole bitline whatever the array stores:",
        "",
        "| Column height | Read energy | Per bit | Per byte |",
        "|---:|---:|---:|---:|",
    ]
    for entry in result["height_sweep"]:
        lines.append(
            f"| {entry['rows']} rows | {entry['read_energy_fj']:.2f} fJ | "
            f"{entry['read_energy_fj_per_bit']:.3f} fJ/bit | {entry['read_energy_j_per_byte']:.3e} J/B |"
        )
    fit = result["height_fit"]
    lines.extend(
        [
            "",
            f"A straight line through those points has slope **{fit['slope_fj_per_row']:.4f} fJ per row of "
            f"column height** and intercept {fit['intercept_fj']:.3f} fJ, with R² = {fit['r2']:.6f}. "
            + "Per-interval slopes are "
            + ", ".join(f"{s['fj_per_row']:.4f} fJ/row ({s['from_rows']}→{s['to_rows']})" for s in fit["interval_slopes"])
            + f"; {fit['slope_trend']}.",
            f"At the measured {result['selected_row_ones']} stored ones in the accessed row of "
            f"{result['array']['columns']} columns, that is "
            f"{fit['slope_fj_per_row'] / result['selected_row_ones']:.4f} fJ per row per discharging bitline.",
            "",
            "A single scalar per byte therefore names a column height without saying so. At this",
            f"node, and at the {result['selected_row_ones']}-of-{result['array']['columns']} stored-one density of the",
            f"accessed row, the assumed {ref['assumed_j_per_byte']:.0e} J/B corresponds to a column of about",
            f"**{result['implied_column_height_rows']:.0f} rows**. That is short: the shipped",
            "single-port memories in this same PDK are built at column heights up to 512 rows",
            "(`results/spice/ihp_sg13g2_bitcell/bitcell.json#sram_bitcell.macros[].physical_rows`),",
            "and an unstated column height is the reason",
            "the model needs a column-height term, not a better scalar. The number is quoted here",
            "to size the gap in the model's *shape*, not to restate a 130 nm energy as an N6 one.",
            "",
            "## The wordline load the macro flow is entitled to",
            "",
            "`physical/ihp_sg13g2_rom_macro/macro_contract.json` needs one number from this run:",
            "the wordline load of the bit array, which sizes the wordline drivers the periphery",
            "synthesises and therefore part of the macro area. It is measured as charge delivered",
            "by the wordline driver divided by the rail \u2014 an effective capacitance, which does",
            "not assume the gate is linear \u2014 over two windows:",
            "",
            "| Window | Effective capacitance |",
            "|---|---:|",
            f"| the wordline transition alone | {result['wordline_capacitance']['ff_per_column_transition_only']:.4f} fF/column |",
            f"| transition **and** the bitline discharge that follows it | {result['wordline_capacitance']['ff_per_column_including_hold']:.4f} fF/column |",
            f"| **given to the macro flow** | **{result['wordline_capacitance']['ff_per_column']:.4f} fF/column** |",
            "",
            "The two windows differ because the falling bitlines pull charge through the row",
            "transistors' gate-drain overlap, and the wordline driver really does supply it on",
            "every access. **The larger of the two is handed to the macro flow.** That sizes the",
            "wordline drivers up, makes the periphery larger and makes the array efficiency this",
            "chain reports lower; the smaller number would have improved it, which is exactly why",
            "it is not the one used.",
            "",
            "The extracted interconnect capacitance on the same nets is only",
            f"{result['wordline_capacitance']['extracted_interconnect_only_ff_per_column']:.4f} fF per column,",
            "because `ext2spice` writes wiring parasitics and the row transistors' gate capacitance",
            "lives inside the device model rather than in a `C` element. **Reading the wordline load",
            "off the parasitic netlist would therefore understate it by design.** That is the reason",
            "this number is measured in simulation and not counted out of the netlist.",
            "",
            "## The second finding: minimum pitch buys density and loses margin",
            "",
            f"At the minimum legal column pitch, **{caps['neighbour_coupled_fraction'] * 100:.1f}%** of a",
            "bitline's extracted capacitance is coupling to its two neighbours. A stored one on both",
            "neighbours therefore drags an unselected bitline down with them: in the nominal case the",
            f"unselected bitline holds only **{energy['nominal']['unprogrammed_bitline_fraction_min'] * 100:.1f}%**",
            "of the supply at the sample point rather than the full rail. The read still resolves — the",
            f"measured margin is {energy['nominal']['read_margin_fraction'] * 100:.1f}% of the supply — but a",
            "manufacturable array would spend area on shielding, a wider pitch, or twisted bitlines, and",
            "**that area is not in the bitcell pitch**. A density number taken from bitcell geometry alone",
            "does not carry this cost.",
            "",
            "## PVT grid",
            "",
            "| Case | Corner | VDD | T | Row | Energy | Per bit | Margin |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for case in result["cases"]:
        margin = case["read_margin_fraction"]
        lines.append(
            f"| `{case['case_id']}` | {case['process_corner']} | {case['vdd_v']} V | "
            f"{case['temperature_c']:g} C | {case['selected_row']} | {case['read_energy_fj']:.2f} fJ | "
            f"{case['read_energy_fj_per_bit']:.3f} fJ | "
            f"{'—' if margin is None else f'{margin * 100:.1f}%'} |"
        )
    lines.extend(
        [
            "",
            "## Claim boundary",
            "",
            f"- Measured boundary: {boundary['boundary_of_the_measured_quantity']}",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_ihp_rom_read_energy.py",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--netgen", type=Path)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--osdi-root", type=Path)
    parser.add_argument("--keep-build", action="store_true")
    parser.add_argument(
        "--rewrite-report",
        action="store_true",
        help="regenerate the markdown from the archived JSON without re-simulating; "
             "it may not change a single recorded value",
    )
    args = parser.parse_args()

    build: Path | None = None
    try:
        contract = common.strict_json(CONTRACT_PATH)
        lock = common.strict_json(repository_path(contract["pdk_lock"]))
        validate_contract(contract, lock)
        if args.validate_only:
            print("PASS: IHP ROM read-energy contract and no-scaling boundary")
            return 0
        if args.rewrite_report:
            json_path = repository_path(contract["reports"]["json"])
            if not json_path.is_file():
                raise ReadEnergyError(f"no archived result to render at {json_path}")
            archived = json.loads(json_path.read_text(encoding="utf-8"))
            before = json.dumps(archived, sort_keys=True)
            markdown = markdown_report(archived)
            if json.dumps(archived, sort_keys=True) != before:
                raise ReadEnergyError("rendering the report mutated the archived result")
            repository_path(contract["reports"]["markdown"]).write_text(markdown, encoding="utf-8")
            print(f"PASS: re-rendered {contract['reports']['markdown']} from the archived JSON")
            return 0

        pdk, variant = bitcell.locate_pdk(args.pdk_root)
        magic, netgen = common.locate_tools(lock, args.tool_root, args.magic, args.netgen)
        pdk_identity = bitcell.verify_pdk(pdk, lock)
        identities = common.tool_identities(magic, netgen, lock)
        ngspice = (
            args.ngspice
            if args.ngspice
            else Path.home() / ".local" / "opentallas-tools" / "ngspice-43-osdi" / "bin" / "ngspice"
        ).expanduser().resolve()
        if not os.access(ngspice, os.X_OK):
            raise ReadEnergyError(f"pinned ngspice is not executable at {ngspice}")
        expected_ngspice = lock["tools"]["ngspice"]
        if common.sha256_file(ngspice) != expected_ngspice["executable_sha256"]:
            raise ReadEnergyError("pinned ngspice binary hash mismatch")
        osdi = (
            args.osdi_root
            if args.osdi_root
            else Path.home() / ".local" / "opentallas-tools" / "ihp-sg13g2-v0.3.0-osdi"
        ).expanduser().resolve()
        for name, expected in lock["osdi_models"]["models"].items():
            module = osdi / f"{name}.osdi"
            if not module.is_file() or common.sha256_file(module) != expected["output_sha256"]:
                raise ReadEnergyError(f"pinned OSDI module {name} is missing or changed")
        model_lib = pdk / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models" / "cornerMOSlv.lib"
        if not model_lib.is_file():
            raise ReadEnergyError("missing official low-voltage MOS corner library")
        init = repository_path(contract["inputs"]["spice_init"])

        build_parent = ROOT / "spice" / "build"
        build_parent.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix="ihp_sg13g2_rom_energy.", dir=build_parent))

        arrays = {
            rows: build_array(contract, magic, variant, pdk, build, rows)
            for rows in sorted(
                set(contract["array"]["height_sweep_rows"]) | {contract["array"]["pvt_rows"]}
            )
        }
        cap_points = [
            (float(rows), entry["capacitance"]["interior_mean_total_ff"])
            for rows, entry in sorted(arrays.items())
        ]
        cap_fit = linear_fit(cap_points)
        if cap_fit["r2"] < contract["acceptance"]["capacitance_linear_fit_r2_min"]:
            raise ReadEnergyError(
                f"extracted bitline capacitance is not linear in rows: R2={cap_fit['r2']}"
            )

        pvt_rows = contract["array"]["pvt_rows"]
        primary = arrays[pvt_rows]
        cases = enumerate_cases(contract)
        evaluated = []
        for case in cases:
            observed = run_case(
                contract, primary, case, build / "cases" / case["case_id"],
                ngspice, init, pdk, osdi, model_lib,
            )
            evaluated.append(evaluate_case(contract, primary, case, observed))
        failures = [case for case in evaluated if case["status"] != "pass"]

        # An idle cycle proves the measured energy is the read, not the background.
        idle_case = dict(evaluated[0])
        idle_spec = {
            "case_id": "idle",
            "process_corner": "tt",
            "vdd_v": 1.2,
            "temperature_c": 27.0,
            "selected_row": pvt_rows // 2,
            "access": False,
        }
        idle_observed = run_case(
            contract, primary, idle_spec, build / "cases" / "idle",
            ngspice, init, pdk, osdi, model_lib,
        )
        idle_energy_fj = idle_observed["measures"]["e_cycle"] * 1e15

        # Column-height sweep at the nominal corner.
        height = []
        for rows in sorted(contract["array"]["height_sweep_rows"]):
            entry = arrays[rows]
            spec = {
                "case_id": f"height_{rows}",
                "process_corner": "tt",
                "vdd_v": 1.2,
                "temperature_c": 27.0,
                "selected_row": rows // 2,
                "access": True,
            }
            observed = run_case(
                contract, entry, spec, build / "heights" / f"rows_{rows}",
                ngspice, init, pdk, osdi, model_lib,
            )
            record = evaluate_case(contract, entry, spec, observed)
            record["rows"] = rows
            height.append(record)
        ones = {entry["ones_in_selected_row"] for entry in height}
        if len(ones) != 1:
            raise ReadEnergyError(
                f"the column-height sweep does not hold the stored-one count fixed: {sorted(ones)}"
            )
        height_points = [(float(e["rows"]), e["read_energy_fj"]) for e in height]
        height_fit_raw = linear_fit(height_points)
        floor = contract["acceptance"]["energy_height_fit_r2_min"]
        if height_fit_raw["r2"] < floor:
            raise ReadEnergyError(
                f"read energy is not affine in column height: R2={height_fit_raw['r2']} < {floor}"
            )
        interval_slopes = [
            {
                "from_rows": int(height_points[i][0]),
                "to_rows": int(height_points[i + 1][0]),
                "fj_per_row": (height_points[i + 1][1] - height_points[i][1])
                / (height_points[i + 1][0] - height_points[i][0]),
            }
            for i in range(len(height_points) - 1)
        ]

        nominal = next(
            case
            for case in evaluated
            if case["process_corner"] == "tt"
            and case["vdd_v"] == 1.2
            and case["temperature_c"] == 27.0
            and case["selected_row"] == pvt_rows // 2
        )
        if idle_energy_fj > contract["acceptance"]["idle_cycle_energy_fraction_max"] * nominal["read_energy_fj"]:
            raise ReadEnergyError(
                f"idle-cycle energy {idle_energy_fj} fJ is not negligible against the read"
            )

        wl_transition = nominal["wordline_capacitance_ff_per_column"]
        wl_hold = nominal["wordline_capacitance_hold_ff_per_column"]
        for name, value in (("transition", wl_transition), ("hold", wl_hold)):
            if value is None or not math.isfinite(value) or value <= 0.0:
                raise ReadEnergyError(
                    f"the nominal case produced no usable {name}-window wordline "
                    "capacitance; the macro Liberty would then be built from a number "
                    "this run did not measure"
                )
        # Deliberately the larger. See `selection_rule` below.
        wl_cap = max(wl_transition, wl_hold)

        technology = common.strict_json(ROOT / "configs" / "hardware" / "technology.json")
        assumed = float(technology["energy"]["rom_read_j_per_byte"]["value"])
        ones_count = next(iter(ones))
        implied_rows = (
            (assumed * 1e15 / 8.0 * primary["columns"]) - height_fit_raw["intercept"]
        ) / height_fit_raw["slope"]

        destination = repository_path(contract["reports"]["artifacts"])
        destination.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for name in ("ihp_rom_bitarray.pex.spice", "programmed_bits.txt", "ihp_rom_bitarray.gds"):
            source = primary["workdir"] / name
            if source.is_file():
                target = destination / f"rows{pvt_rows}_{name}"
                shutil.copy2(source, target)
                artifacts.append(
                    {
                        "path": target.relative_to(ROOT).as_posix(),
                        "sha256": common.sha256_file(target),
                        "size_bytes": target.stat().st_size,
                    }
                )

        by_energy = sorted(evaluated, key=lambda case: case["read_energy_fj"])
        result = {
            "schema_version": 1,
            "experiment_id": contract["experiment_id"],
            "status": "pass" if not failures else "fail",
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
                "ngspice": {"path": str(ngspice), "sha256": common.sha256_file(ngspice)},
            },
            "array": {
                "rows": pvt_rows,
                "columns": primary["columns"],
                "pattern": contract["array"]["pattern"],
                "extracted_devices": primary["devices"],
                "precharge_device": contract["array"]["precharge_device"],
                "precharge_device_note": contract["array"]["precharge_device_note"],
                "extracted_ports": primary["ports"],
            },
            "wordline_capacitance": {
                "ff_per_column": wl_cap,
                "ff_per_column_transition_only": wl_transition,
                "ff_per_column_including_hold": wl_hold,
                "charge_fc": nominal["wordline_charge_fc"],
                "hold_charge_fc": nominal["wordline_hold_charge_fc"],
                "selection_rule": (
                    "the LARGER of the two windows is the one the macro flow is given. "
                    "The transition window is what a Liberty pin capacitance means; the "
                    "hold window additionally contains the charge the discharging "
                    "bitlines pull through the row transistors' gate-drain overlap, which "
                    "the wordline driver really does have to supply on every access. "
                    "Taking the larger sizes the wordline drivers UP, which makes the "
                    "periphery larger and the macro's array efficiency LOWER. Choosing "
                    "the smaller would have improved the number this chain reports, which "
                    "is the reason it is not chosen."
                ),
                "from_case": nominal["case_id"],
                "method": (
                    "charge delivered by the selected wordline driver, divided by the rail "
                    "and by the column count. This is an EFFECTIVE capacitance and does "
                    "not assume the gate is linear; it is not the extracted interconnect "
                    "capacitance, which omits the row transistors' gate capacitance "
                    "entirely"
                ),
                "extracted_interconnect_only_ff_per_column": (
                    primary["capacitance"]["wordline_interconnect_mean_ff"] / primary["columns"]
                ),
                "consumer": "physical/ihp_sg13g2_rom_macro/macro_contract.json"
                            "#wordline_capacitance_ff_per_column",
                "extrapolation_note": (
                    "measured on this array's column count and consumed by the macro flow as "
                    "ff_per_column x cols, which on the 128-column macro is a 16x "
                    "extrapolation. The gate term is exactly linear in columns; the wiring "
                    "term is linear plus end effects that a narrow array carries a "
                    "disproportionate share of, so the extrapolation slightly OVERSTATES the "
                    "load per column on a wide macro. It was not measured at 128 columns"
                ),
                "measured_at_columns": primary["columns"],
            },
            "capacitance_model": {
                "points_ff": {str(rows): value for rows, value in cap_points},
                "slope_ff_per_row": cap_fit["slope"],
                "intercept_ff": cap_fit["intercept"],
                "r2": cap_fit["r2"],
                "neighbour_coupled_fraction": primary["capacitance"]["neighbour_coupled_fraction"],
                "interior_mean_total_ff": primary["capacitance"]["interior_mean_total_ff"],
            },
            "cases": evaluated,
            "idle_cycle": {"energy_fj": idle_energy_fj, "measures": idle_observed["measures"]},
            "height_sweep": height,
            "height_fit": {
                "slope_fj_per_row": height_fit_raw["slope"],
                "intercept_fj": height_fit_raw["intercept"],
                "r2": height_fit_raw["r2"],
                "interval_slopes": interval_slopes,
                "slope_trend": (
                    "the per-interval slope falls as the column grows, so the affine fit is "
                    "slightly conservative at large heights: the precharge device does not "
                    "fully restore the far end of a long bitline inside a fixed window"
                    if interval_slopes[-1]["fj_per_row"] < interval_slopes[0]["fj_per_row"]
                    else "the per-interval slope rises as the column grows"
                ),
            },
            "selected_row_ones": ones_count,
            "implied_column_height_rows": implied_rows,
            "energy": {
                "case_count": len(evaluated),
                "cases_passed": len(evaluated) - len(failures),
                "nominal": nominal,
                "min": by_energy[0],
                "max": by_energy[-1],
            },
            "reference": {
                "assumed_j_per_byte": assumed,
                "assumed_grade": technology["energy"]["rom_read_j_per_byte"]["grade"],
                "assumed_source": "configs/hardware/technology.json#energy.rom_read_j_per_byte",
                # Recorded rather than left to a reader's arithmetic: it is quoted
                # in three documents and each one used to compute it by hand from
                # two numbers that can move independently.
                "measured_over_assumed_at_this_column_height": (
                    nominal["read_energy_j_per_byte"] / assumed
                ),
                "measured_over_assumed_note": (
                    "the measured side EXCLUDES address decode, sense amplification and the "
                    "macro output latch, all three of which this constant's own stated "
                    "boundary INCLUDES, so the quotient is a LOWER bound on the disagreement "
                    "-- and it is a 130 nm measurement against a leading-node constant, which "
                    "is why it must not move that constant"
                ),
                "measured_at_column_height_rows": pvt_rows,
            },
            "artifacts": artifacts,
            # Which simulator warnings this run is willing to see and still pass,
            # written into the artifact rather than left in the runner's source.
            # A suppression list that only exists in code is a suppression list
            # nobody reviewing the result can see. Every warning any case emitted
            # is recorded per case under `all_warnings` whether it was suppressed
            # or not, so the filter can be audited against what actually happened.
            "case_hash_stability": (
                "`deck_sha256` and `log_sha256` are ARCHIVAL IDENTITY ONLY. Every deck "
                "carries the absolute path of this run's temporary build directory in its "
                "`.include` and `.lib` lines, and the log carries the simulator's own "
                "timings, so both change on every run of an unchanged experiment. "
                "`canonical_deck_sha256` is the reproducible one: it is the deck with every "
                "absolute path reduced to its file name, and the run refuses to record it "
                "unless that canonicalisation removed every absolute path"
            ),
            "benign_warnings_allowed": [
                pattern.pattern for pattern in BENIGN_WARNING_RES
            ],
            "benign_warnings_note": (
                "matched whole and anchored, never by prefix. Anything else fails the case. "
                "These patterns were dead for a while -- they were written with a doubled "
                "backslash in a raw string, so they matched nothing and every case would "
                "have failed on the PSP103 subckt multiplier note. Fixing the escaping made "
                "two named warnings benign again; it is recorded here so that the widening "
                "is visible in the result and not only in a diff"
            ),
            "claim_boundary": contract["claim_boundary"],
            "reports": dict(contract["reports"]),
        }
        json_path = repository_path(contract["reports"]["json"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        repository_path(contract["reports"]["markdown"]).write_text(
            markdown_report(result), encoding="utf-8"
        )
        if failures:
            print(f"FAIL: {len(failures)} read-energy cases failed: {[c['case_id'] for c in failures]}")
            return 1
        print(
            f"PASS: IHP SG13G2 ROM read energy; {len(evaluated)} cases; "
            f"nominal {nominal['read_energy_fj_per_bit']:.3f} fJ/bit at {pvt_rows} rows "
            f"({nominal['read_energy_j_per_byte']:.3e} J/B vs assumed {assumed:.1e})"
        )
        return 0
    except (ReadEnergyError, bitcell.BitcellError, common.PhysicalExperimentError, OSError, subprocess.SubprocessError) as exc:
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
