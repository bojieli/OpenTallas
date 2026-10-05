#!/usr/bin/env python3
"""Run the governed SKY130 via-programmed NOR-ROM read-path experiment.

The PDK circuit is a methodology/topology proxy.  Its lumped bitline loads are
explicitly synthetic and the result may not be scaled into an N7/N4 product
claim.  The target-node correlation boundary lives in the machine-readable
contract and is copied verbatim into every report.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from itertools import product
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
CONTRACT_PATH = HERE / "sky130_rom_read_contract.json"
BUILD = HERE / "build" / "sky130_rom_read"
DEFAULT_CACHE = ROOT / ".cache" / "sky130_fd_pr"
MEASURE_NAMES = (
    "v_present",
    "v_absent",
    "v_masked",
    "sense_present_v",
    "sense_absent_v",
    "sense_masked_v",
    "read_margin",
    "discharge_delay",
    "read_energy",
    "inactive_leakage",
)
MEASURE_RE = re.compile(r"(?m)^\s*({})\s*=\s*([-+0-9.eE]+)".format("|".join(MEASURE_NAMES)))
WARNING_RE = re.compile(r"(?mi)^\s*warning:\s*(.+)$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ExperimentError(RuntimeError):
    """A governed experiment input or acceptance gate failed."""


def strict_json(path: Path) -> Any:
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        value: dict[str, Any] = {}
        for key, child in items:
            if key in value:
                duplicates.append(key)
            value[key] = child
        return value

    try:
        parsed = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise ExperimentError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise ExperimentError(f"duplicate JSON keys in {path}: {sorted(set(duplicates))}")
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_contract(contract: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise ExperimentError("SKY130 ROM contract schema_version must be 1")
    if contract.get("experiment_id") != "sky130_via_nor_read_v1":
        raise ExperimentError("unexpected experiment_id")
    pdk = contract.get("pdk", {})
    if not re.fullmatch(r"[0-9a-f]{40}", str(pdk.get("commit", ""))):
        raise ExperimentError("PDK commit must be a full Git SHA-1")
    files = pdk.get("files")
    if not isinstance(files, list) or len(files) != 14:
        raise ExperimentError("PDK file manifest must contain the fourteen required model files")
    paths: set[str] = set()
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "sha256", "size_bytes"}:
            raise ExperimentError("invalid PDK file manifest entry")
        path = item["path"]
        if (
            not isinstance(path, str)
            or path.startswith("/")
            or ".." in Path(path).parts
            or path in paths
            or SHA256_RE.fullmatch(str(item["sha256"])) is None
            or not isinstance(item["size_bytes"], int)
            or item["size_bytes"] < 1
        ):
            raise ExperimentError(f"invalid PDK file entry {item!r}")
        paths.add(path)
    for corner in ("ff", "tt", "ss"):
        required = {
            f"cells/nfet_01v8/sky130_fd_pr__nfet_01v8__{corner}.corner.spice",
            f"cells/pfet_01v8/sky130_fd_pr__pfet_01v8__{corner}.corner.spice",
        }
        if not required <= paths:
            raise ExperimentError(f"PDK manifest lacks {corner} device corners")

    dimensions = contract.get("dimensions", {})
    expected_dimensions = {
        "array_rows",
        "output_load_ff",
        "process_corner",
        "temperature_c",
        "vdd_v",
    }
    if set(dimensions) != expected_dimensions:
        raise ExperimentError("experiment dimensions are incomplete")
    if dimensions["process_corner"] != ["ss", "tt", "ff"]:
        raise ExperimentError("process corners must be deterministically ordered ss/tt/ff")
    for name, values in dimensions.items():
        if not isinstance(values, list) or not values or len(values) != len(set(values)):
            raise ExperimentError(f"dimension {name} must be a non-empty unique list")
        if name != "process_corner" and any(
            not isinstance(value, (int, float)) or not math.isfinite(value) for value in values
        ):
            raise ExperimentError(f"dimension {name} must be finite numeric")
    if any(not isinstance(value, int) or value < 1 for value in dimensions["array_rows"]):
        raise ExperimentError("array_rows must contain positive integers")
    if any(value <= 0 for value in dimensions["output_load_ff"] + dimensions["vdd_v"]):
        raise ExperimentError("load and supply values must be positive")

    campaigns = contract.get("campaigns")
    if not isinstance(campaigns, list) or len(campaigns) != 4:
        raise ExperimentError("the four governed sweep campaigns are required")
    names: set[str] = set()
    for campaign in campaigns:
        if not isinstance(campaign, dict) or set(campaign) != {"name", "dimensions", "fixed"}:
            raise ExperimentError("invalid sweep campaign")
        name = campaign["name"]
        swept = campaign["dimensions"]
        fixed = campaign["fixed"]
        if not isinstance(name, str) or not name or name in names:
            raise ExperimentError("campaign names must be unique non-empty strings")
        names.add(name)
        if (
            not isinstance(swept, list)
            or len(swept) != len(set(swept))
            or set(swept) | set(fixed) != expected_dimensions
            or set(swept) & set(fixed)
        ):
            raise ExperimentError(f"campaign {name} does not cover each dimension exactly once")
        for key, value in fixed.items():
            if value not in dimensions[key]:
                raise ExperimentError(f"campaign {name} fixes {key} outside its dimension")

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class") != "simulated"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or "prohibited" not in boundary.get("target_node_scaling_status", "")
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise ExperimentError("claim boundary must prohibit unreviewed target-node scaling")
    acceptance = contract.get("acceptance", {})
    for key, value in acceptance.items():
        if not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ExperimentError(f"acceptance threshold {key} must be finite numeric")
    if acceptance.get("unexpected_warnings_max") != 0:
        raise ExperimentError("unexpected ngspice warnings must be fatal")


def pdk_root(contract: dict[str, Any]) -> Path:
    override = os.environ.get(contract["pdk"]["cache_environment_variable"])
    if override:
        return Path(override).expanduser().resolve()
    return (DEFAULT_CACHE / contract["pdk"]["commit"]).resolve()


def verify_file(path: Path, item: dict[str, Any]) -> None:
    if not path.is_file():
        raise ExperimentError(f"missing pinned PDK file: {path}")
    if path.stat().st_size != item["size_bytes"]:
        raise ExperimentError(
            f"PDK file size mismatch for {item['path']}: {path.stat().st_size} "
            f"!= {item['size_bytes']}"
        )
    actual = sha256_file(path)
    if actual != item["sha256"]:
        raise ExperimentError(f"PDK hash mismatch for {item['path']}: {actual}")


def acquire_pdk(contract: dict[str, Any], *, fetch: bool) -> tuple[Path, list[dict[str, Any]]]:
    root = pdk_root(contract)
    commit = contract["pdk"]["commit"]
    base = f"https://raw.githubusercontent.com/google/skywater-pdk-libs-sky130_fd_pr/{commit}"
    identities: list[dict[str, Any]] = []
    for item in contract["pdk"]["files"]:
        target = root / item["path"]
        if not target.is_file() and fetch:
            target.parent.mkdir(parents=True, exist_ok=True)
            url = f"{base}/{item['path']}"
            with urlopen(url, timeout=60) as response:
                payload = response.read()
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
                temporary.write(payload)
                temporary_path = Path(temporary.name)
            try:
                verify_file(temporary_path, item)
                os.replace(temporary_path, target)
            finally:
                temporary_path.unlink(missing_ok=True)
        verify_file(target, item)
        identities.append({**item})
    return root, identities


def tool_identity(contract: dict[str, Any]) -> dict[str, Any]:
    executable_text = os.environ.get("OPENTALLAS_NGSPICE", "ngspice")
    resolved = shutil.which(executable_text)
    if resolved is None:
        raise ExperimentError(f"ngspice executable not found: {executable_text}")
    executable = Path(resolved).resolve()
    completed = subprocess.run(
        [str(executable), "--version"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise ExperimentError(f"ngspice identity command failed: {completed.stdout}")
    expected = contract["toolchain"]["ngspice"]
    digest = sha256_file(executable)
    if expected["version_contains"] not in completed.stdout:
        raise ExperimentError("ngspice version does not match the governed version family")
    if digest != expected["canonical_executable_sha256"]:
        raise ExperimentError(
            f"ngspice executable hash {digest} != canonical "
            f"{expected['canonical_executable_sha256']}"
        )
    return {
        "executable": str(executable),
        "executable_sha256": digest,
        "version_output": completed.stdout.strip(),
        "canonical_package": expected["canonical_package"],
    }


def generated_cases(contract: dict[str, Any]) -> list[dict[str, Any]]:
    dimensions = contract["dimensions"]
    by_key: dict[tuple[Any, ...], dict[str, Any]] = {}
    membership: defaultdict[tuple[Any, ...], list[str]] = defaultdict(list)
    order = tuple(dimensions)
    for campaign in contract["campaigns"]:
        swept = campaign["dimensions"]
        for values in product(*(dimensions[name] for name in swept)):
            case = dict(campaign["fixed"])
            case.update(dict(zip(swept, values, strict=True)))
            key = tuple(case[name] for name in order)
            by_key[key] = case
            membership[key].append(campaign["name"])
    cases = []
    for index, key in enumerate(sorted(by_key), start=1):
        case = by_key[key]
        case["campaigns"] = sorted(membership[key])
        case["case_id"] = f"case_{index:03d}"
        cases.append(case)
    if len(cases) != 51:
        raise ExperimentError(f"governed campaign must generate 51 unique cases, got {len(cases)}")
    return cases


def flatten_pdk(pdk: Path, contract: dict[str, Any]) -> Path:
    flat = BUILD / "pdk_flat"
    if flat.exists():
        shutil.rmtree(flat)
    flat.mkdir(parents=True)
    for item in contract["pdk"]["files"]:
        source = pdk / item["path"]
        target_name = (
            f"{source.parent.name}_{source.name}" if source.name == "nonfet.spice" else source.name
        )
        target = flat / target_name
        if target.exists():
            raise ExperimentError(f"PDK flattening filename collision: {target.name}")
        shutil.copyfile(source, target)
    compatibility = contract["toolchain"]["ngspice"]["compatibility_mode"]
    (flat / ".spiceinit").write_text(f"set ngbehavior={compatibility}\n", encoding="utf-8")
    return flat


def netlist_text(case: dict[str, Any], contract: dict[str, Any], flat: Path) -> str:
    corner = case["process_corner"]
    netlist = contract["netlist"]
    geo = netlist["device_geometry_um"]
    timing = netlist["timing_ns"]
    bitline_cap_ff = (
        netlist["bitline_fixed_cap_ff"]
        + netlist["bitline_per_row_cap_ff"] * case["array_rows"]
    )
    wordline_width = timing["wordline_deassert"] - timing["wordline_assert"]
    return f"""* Governed SKY130 via-programmed NOR-ROM read-path proxy
* Case {case['case_id']}; synthetic lumped loads, no extracted layout
.title OpenTallas SKY130 via-ROM read {case['case_id']}
.option scale=1u
.temp {case['temperature_c']}
.include \"{flat / 'invariant.spice'}\"
.include \"{flat / f'{corner}_nonfet.spice'}\"
.include \"{flat / f'sky130_fd_pr__nfet_01v8__{corner}.corner.spice'}\"
.include \"{flat / f'sky130_fd_pr__pfet_01v8__{corner}.corner.spice'}\"

.param VDDVAL={case['vdd_v']}
.param LCH={geo['channel_length']}
.param WREAD={geo['read_nfet_width']}
.param WPRE={geo['precharge_pfet_width']}
.param WSENSE_N={geo['sense_nfet_width']}
.param WSENSE_P={geo['sense_pfet_width']}
.param WGATE_N={geo['wordline_gate_nfet_width']}
.param WGATE_P={geo['wordline_gate_pfet_width']}

VDD vdd 0 {{VDDVAL}}
VPRE pre_n 0 DC 0 PULSE(0 {{VDDVAL}} {timing['precharge_release']}n 40p 40p 7.5n 20n)
VWL_RAW wl_raw 0 DC 0 PULSE(0 {{VDDVAL}} {timing['wordline_assert']}n 40p 40p {wordline_width}n 20n)
VENABLED expert_enabled 0 {{VDDVAL}}
VMASKED expert_masked 0 0

.subckt INV input output vdd ground wn=0.5 wp=1.0
XINVN output input ground ground sky130_fd_pr__nfet_01v8 l={{LCH}} w={{wn}}
XINVP output input vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{wp}}
.ends INV

.subckt NAND2 input_a input_b output vdd ground wn=0.5 wp=1.0
XNANDN0 output input_a nseries ground sky130_fd_pr__nfet_01v8 l={{LCH}} w={{wn}}
XNANDN1 nseries input_b ground ground sky130_fd_pr__nfet_01v8 l={{LCH}} w={{wn}}
XNANDP0 output input_a vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{wp}}
XNANDP1 output input_b vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{wp}}
.ends NAND2

* Transistor-level wordline-mask path: selected and deliberately masked copies.
XWLNAND_SEL wl_raw expert_enabled wl_sel_n vdd 0 NAND2 wn={{WGATE_N}} wp={{WGATE_P}}
XWLINV_SEL wl_sel_n wl_selected vdd 0 INV wn={{WGATE_N}} wp={{WGATE_P}}
XWLNAND_MASK wl_raw expert_masked wl_mask_n vdd 0 NAND2 wn={{WGATE_N}} wp={{WGATE_P}}
XWLINV_MASK wl_mask_n wl_masked vdd 0 INV wn={{WGATE_N}} wp={{WGATE_P}}

* Matched precharge devices and declared array-size capacitance proxy.
XPRE_PRESENT bl_present pre_n vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{WPRE}}
XPRE_ABSENT bl_absent pre_n vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{WPRE}}
XPRE_MASKED bl_masked pre_n vdd vdd sky130_fd_pr__pfet_01v8 l={{LCH}} w={{WPRE}}
CBL_PRESENT bl_present 0 {bitline_cap_ff}f
CBL_ABSENT bl_absent 0 {bitline_cap_ff}f
CBL_MASKED bl_masked 0 {bitline_cap_ff}f

* Programmed cell: the drain via connects the selected read NFET to the bitline.
XBIT_PRESENT bl_present wl_selected 0 0 sky130_fd_pr__nfet_01v8 l={{LCH}} w={{WREAD}}
* Unprogrammed cell: identical transistor on a floating diffusion, but no drain via to BL.
XBIT_ABSENT floating_drain wl_selected 0 0 sky130_fd_pr__nfet_01v8 l={{LCH}} w={{WREAD}}
CFLOAT floating_drain 0 2f
* Programmed but unselected expert: the mask path must prevent discharge.
XBIT_MASKED bl_masked wl_masked 0 0 sky130_fd_pr__nfet_01v8 l={{LCH}} w={{WREAD}}

XSENSE_PRESENT bl_present sense_present vdd 0 INV wn={{WSENSE_N}} wp={{WSENSE_P}}
XSENSE_ABSENT bl_absent sense_absent vdd 0 INV wn={{WSENSE_N}} wp={{WSENSE_P}}
XSENSE_MASKED bl_masked sense_masked vdd 0 INV wn={{WSENSE_N}} wp={{WSENSE_P}}
CLOAD_PRESENT sense_present 0 {case['output_load_ff']}f
CLOAD_ABSENT sense_absent 0 {case['output_load_ff']}f
CLOAD_MASKED sense_masked 0 {case['output_load_ff']}f

.tran 2p {timing['simulation_stop']}n
.measure tran v_present FIND v(bl_present) AT={timing['read_sample']}n
.measure tran v_absent FIND v(bl_absent) AT={timing['read_sample']}n
.measure tran v_masked FIND v(bl_masked) AT={timing['read_sample']}n
.measure tran sense_present_v FIND v(sense_present) AT={timing['read_sample']}n
.measure tran sense_absent_v FIND v(sense_absent) AT={timing['read_sample']}n
.measure tran sense_masked_v FIND v(sense_masked) AT={timing['read_sample']}n
.measure tran read_margin PARAM='v_absent-v_present'
.measure tran discharge_delay TRIG v(wl_selected) VAL='VDDVAL/2' RISE=1 TARG v(bl_present) VAL='VDDVAL/2' FALL=1
.measure tran read_energy INTEG par('-v(vdd)*i(VDD)') FROM=0n TO={timing['read_sample']}n
.measure tran inactive_leakage RMS i(VDD) FROM=8.5n TO=9.5n
.end
"""


def parse_measures(log_text: str) -> dict[str, float]:
    values = {match.group(1): float(match.group(2)) for match in MEASURE_RE.finditer(log_text)}
    missing = set(MEASURE_NAMES) - set(values)
    if missing:
        raise ExperimentError(f"missing ngspice measures: {sorted(missing)}")
    if any(not math.isfinite(value) for value in values.values()):
        raise ExperimentError("ngspice emitted non-finite measures")
    return values


def evaluate_case(case: dict[str, Any], values: dict[str, float], warnings: list[str], contract: dict[str, Any]) -> list[str]:
    threshold = contract["acceptance"]
    vdd = case["vdd_v"]
    failures: list[str] = []
    checks = (
        (values["v_present"] <= threshold["present_bitline_fraction_max"] * vdd, "selected programmed bitline did not discharge"),
        (values["v_absent"] >= threshold["absent_bitline_fraction_min"] * vdd, "via-absent bitline did not retain high"),
        (values["v_masked"] >= threshold["masked_bitline_fraction_min"] * vdd, "masked programmed bitline did not retain high"),
        (values["read_margin"] >= threshold["read_margin_fraction_min"] * vdd, "dynamic bitline separation is below threshold"),
        (values["sense_present_v"] >= threshold["sense_high_fraction_min"] * vdd, "present-bit sense output did not resolve high"),
        (values["sense_absent_v"] <= threshold["sense_low_fraction_max"] * vdd, "absent-bit sense output did not resolve low"),
        (values["sense_masked_v"] <= threshold["sense_low_fraction_max"] * vdd, "masked-bit sense output did not resolve low"),
        (0.0 < values["discharge_delay"] <= threshold["discharge_delay_ns_max"] * 1e-9, "discharge delay is outside the bounded read window"),
        (threshold["read_energy_fj_min"] * 1e-15 < values["read_energy"] <= threshold["read_energy_fj_max"] * 1e-15, "read energy is outside the topology-proxy sanity bound"),
        (0.0 <= values["inactive_leakage"] <= threshold["inactive_leakage_ua_max"] * 1e-6, "inactive leakage is outside the topology-proxy sanity bound"),
        (len(warnings) <= threshold["unexpected_warnings_max"], "unexpected ngspice warning observed"),
    )
    for passed, message in checks:
        if not passed:
            failures.append(message)
    return failures


def run_case(case: dict[str, Any], contract: dict[str, Any], flat: Path, executable: str) -> dict[str, Any]:
    case_dir = BUILD / "cases" / case["case_id"]
    case_dir.mkdir(parents=True, exist_ok=True)
    deck = case_dir / "read.spice"
    deck.write_text(netlist_text(case, contract, flat), encoding="utf-8")
    log = case_dir / "ngspice.log"
    completed = subprocess.run(
        [executable, "-b", "-o", str(log), str(deck)],
        cwd=flat,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    if completed.returncode != 0:
        raise ExperimentError(
            f"{case['case_id']}: ngspice failed ({completed.returncode}); "
            f"stdout={completed.stdout!r} stderr={completed.stderr!r}; log={log}"
        )
    values = parse_measures(log_text)
    warnings = sorted(set(WARNING_RE.findall(log_text + "\n" + completed.stderr)))
    failures = evaluate_case(case, values, warnings, contract)
    normalized = {
        "discharge_delay_ns": values["discharge_delay"] * 1e9,
        "inactive_leakage_ua": values["inactive_leakage"] * 1e6,
        "read_energy_fj": values["read_energy"] * 1e15,
        "read_margin_fraction_vdd": values["read_margin"] / case["vdd_v"],
    }
    return {
        **case,
        "bitline_cap_ff": contract["netlist"]["bitline_fixed_cap_ff"]
        + contract["netlist"]["bitline_per_row_cap_ff"] * case["array_rows"],
        "deck_sha256": sha256_file(deck),
        "failures": failures,
        "measures_si": values,
        "metrics": normalized,
        "ngspice_log_sha256": sha256_file(log),
        "status": "pass" if not failures else "fail",
        "warnings": warnings,
    }


def extremum(cases: list[dict[str, Any]], metric: str, *, maximum: bool) -> dict[str, Any]:
    selected = (max if maximum else min)(cases, key=lambda case: case["metrics"][metric])
    return {
        "case_id": selected["case_id"],
        "value": selected["metrics"][metric],
    }


def build_result(contract: dict[str, Any], tool: dict[str, Any], pdk_files: list[dict[str, Any]], cases: list[dict[str, Any]]) -> dict[str, Any]:
    failures = [case for case in cases if case["status"] != "pass"]
    summary = {
        "cases_failed": len(failures),
        "cases_passed": len(cases) - len(failures),
        "cases_total": len(cases),
        "max_discharge_delay_ns": extremum(cases, "discharge_delay_ns", maximum=True),
        "max_inactive_leakage_ua": extremum(cases, "inactive_leakage_ua", maximum=True),
        "max_read_energy_fj": extremum(cases, "read_energy_fj", maximum=True),
        "min_read_margin_fraction_vdd": extremum(cases, "read_margin_fraction_vdd", maximum=False),
    }
    return {
        "acceptance": contract["acceptance"],
        "cases": cases,
        "claim_boundary": contract["claim_boundary"],
        "contract": {
            "path": str(CONTRACT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "experiment_id": contract["experiment_id"],
        "input_model": {
            "campaigns": contract["campaigns"],
            "dimensions": contract["dimensions"],
            "netlist": contract["netlist"],
        },
        "pdk": {
            **{key: value for key, value in contract["pdk"].items() if key != "files"},
            "files": pdk_files,
        },
        "runner": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "schema_version": 1,
        "status": "pass" if not failures else "fail",
        "summary": summary,
        "toolchain": {"ngspice": tool},
    }


def case_label(case: dict[str, Any]) -> str:
    return (
        f"{case['case_id']} ({case['process_corner']}, {case['vdd_v']:.2f} V, "
        f"{case['temperature_c']:.0f} C, {case['array_rows']} rows, "
        f"{case['output_load_ff']:.0f} fF port load)"
    )


def markdown_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    cases_by_id = {case["case_id"]: case for case in result["cases"]}

    def describe(extreme: dict[str, Any], unit: str) -> str:
        case = cases_by_id[extreme["case_id"]]
        return f"{extreme['value']:.6g} {unit} — {case_label(case)}"

    boundary = result["claim_boundary"]
    lines = [
        "# Governed SKY130 via-ROM read-path experiment",
        "",
        f"**Result:** **{result['status'].upper()}** ({summary['cases_passed']}/{summary['cases_total']} cases passed)  ",
        "**Evidence class:** simulated open-PDK circuit proxy; not measured silicon  ",
        f"**PDK pin:** SKY130 primitive library `{result['pdk']['tag']}` / commit `{result['pdk']['commit']}`  ",
        f"**Simulator:** `{result['toolchain']['ngspice']['version_output'].splitlines()[0]}`",
        "",
        "## Outcome",
        "",
        "The pinned BSIM campaign validates the via-present/via-absent NOR-ROM topology,",
        "the transistor-level expert-wordline mask, and sense polarity over the declared",
        "PVT and synthetic capacitive-load envelope. It does not characterize a ROM macro.",
        "The `array_rows` dimension changes only the explicitly declared lumped bitline",
        "capacitance; it is not extracted array geometry.",
        "",
        "| Limiting metric | Observed case |",
        "|---|---|",
        f"| Minimum dynamic bitline separation / VDD | {describe(summary['min_read_margin_fraction_vdd'], 'V/V')} |",
        f"| Maximum VDD/2 discharge delay | {describe(summary['max_discharge_delay_ns'], 'ns')} |",
        f"| Maximum read-window supply energy | {describe(summary['max_read_energy_fj'], 'fJ')} |",
        f"| Maximum inactive local-circuit leakage | {describe(summary['max_inactive_leakage_ua'], 'uA')} |",
        "",
        "The energy number covers the three matched bitlines, their static sense inverters,",
        "the two wordline-mask paths, and output loads from time zero through the 5-ns",
        "sample. Leakage is the same local circuit after the read pulse; neither quantity",
        "is a per-bit macro number or a whole-wafer power estimate.",
        "",
        "## Governed sweep",
        "",
        "- Full 3 × 3 × 3 FF/TT/SS, 1.62/1.80/1.98-V, -40/25/125-C PVT sweep at 256 rows and 20-fF output load.",
        "- 64/256/1,024-row × 5/20/80-fF output-load sweeps at nominal PVT, slow-low-hot, and fast-high-cold.",
        "- Duplicate points are executed once, yielding 51 deterministic cases.",
        "- Every case checks programmed discharge, absent-via retention, masked retention, normalized separation, sense polarity, delay, positive bounded energy, nonnegative bounded leakage, and zero warnings.",
        "",
        "## What maps—and what does not",
        "",
    ]
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            "There is deliberately **no target-node scaling rule** in the contract. SKY130",
            "cannot be converted to an N7 or N4 density, bandwidth, delay, or energy point",
            "with a feature-size multiplier. Target studies remain blocked on characterized",
            "N7/N4 ROM macros, extracted interconnect/sense paths, PVT/mismatch/aging data,",
            "simultaneous-activity power integrity, test-chip correlation, and silicon.",
            "",
            "## Reproduction and machine evidence",
            "",
            "```bash",
            "python3 spice/run_sky130_rom_read.py --fetch-pdk",
            "```",
            "",
            f"The contract SHA-256 is `{result['contract']['sha256']}` and the runner",
            f"SHA-256 is `{result['runner']['sha256']}`. Exact case inputs, measures,",
            "deck/log hashes, thresholds, PDK file hashes, and tool identity are in",
            "`results/spice/sky130_rom_read.json`. Downloaded PDK files live only in the",
            "ignored `.cache/` directory and are hash-checked before every run.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(contract: dict[str, Any], result: dict[str, Any]) -> None:
    json_path = ROOT / contract["reports"]["json"]
    markdown_path = ROOT / contract["reports"]["markdown"]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(result), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-pdk", action="store_true", help="download missing pinned PDK model files")
    parser.add_argument("--fetch-only", action="store_true", help="fetch/verify PDK inputs, then stop")
    parser.add_argument("--validate-only", action="store_true", help="validate the contract without tools or PDK")
    args = parser.parse_args()

    contract = strict_json(CONTRACT_PATH)
    validate_contract(contract)
    cases = generated_cases(contract)
    if args.validate_only:
        print(f"PASS: governed SKY130 contract; {len(cases)} deterministic cases")
        return 0
    pdk, pdk_files = acquire_pdk(contract, fetch=args.fetch_pdk or args.fetch_only)
    if args.fetch_only:
        print(f"PASS: {len(pdk_files)} pinned SKY130 model files at {pdk}")
        return 0
    tool = tool_identity(contract)
    if BUILD.exists():
        shutil.rmtree(BUILD)
    flat = flatten_pdk(pdk, contract)
    results: list[dict[str, Any]] = []
    for index, case in enumerate(cases, start=1):
        print(f"[{index:02d}/{len(cases)}] {case_label(case)}", flush=True)
        results.append(run_case(case, contract, flat, tool["executable"]))
    result = build_result(contract, tool, pdk_files, results)
    write_outputs(contract, result)
    print(
        f"{result['status'].upper()}: {result['summary']['cases_passed']}/"
        f"{result['summary']['cases_total']} SKY130 read-path cases passed"
    )
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ExperimentError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
