#!/usr/bin/env python3
"""Run governed SKY130A distributed-RC extraction and local PVT simulation."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import run_sky130_extracted_pvt as pvt
import run_sky130_physical as physical


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spice" / "sky130_rom_slice" / "resistance_contract.json"
BUILD = ROOT / "spice" / "build" / "sky130_resistance"
MEASURE_NAMES = pvt.MEASURE_NAMES
WARNING_RE = pvt.WARNING_RE
EXPECTED_BENIGN_WARNINGS = pvt.EXPECTED_BENIGN_WARNINGS


class ResistanceError(RuntimeError):
    """A governed distributed-RC input, execution, or acceptance gate failed."""


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
        raise ResistanceError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise ResistanceError(
            f"duplicate JSON keys in {path}: {sorted(set(duplicates))}"
        )
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def repo_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ResistanceError(f"repository path must be contained: {value}")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ResistanceError(f"repository path escapes root: {value}") from exc
    return resolved


def validate_contract(contract: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if contract.get("schema_version") != 1:
        raise ResistanceError("resistance contract schema_version must be 1")
    if contract.get("experiment_id") != "sky130_via_rom_distributed_rc_v1":
        raise ResistanceError("unexpected resistance experiment_id")
    if contract.get("top_cell") != "sky130_rom_slice":
        raise ResistanceError("unexpected top cell")
    expected_ports = [
        "VGND",
        "VPWR",
        "WL_PRESENT",
        "EN_PRESENT",
        "PRE_PRESENT",
        "Q_PRESENT",
        "WL_ABSENT",
        "EN_ABSENT",
        "PRE_ABSENT",
        "Q_ABSENT",
    ]
    if contract.get("top_ports") != expected_ports:
        raise ResistanceError("top ports are incomplete, reordered, or changed")

    expected_inputs = {
        "deterministic_pvt_contract",
        "deterministic_pvt_result",
        "extractor_script",
        "nfet_layout",
        "pdk_lock",
        "pfet_layout",
        "physical_result",
        "testbench_template",
        "top_layout",
    }
    inputs = contract.get("inputs", {})
    if set(inputs) != expected_inputs:
        raise ResistanceError("resistance inputs are incomplete or contain extras")
    for value in inputs.values():
        if not repo_path(value).is_file():
            raise ResistanceError(f"missing resistance input: {value}")

    extraction = contract.get("extraction", {})
    styles = extraction.get("styles")
    expected_styles = [
        {"id": "nominal", "magic_style": "ngspice()"},
        {"id": "high_r_high_c", "magic_style": "ngspice(hrhc)"},
        {"id": "high_r_low_c", "magic_style": "ngspice(hrlc)"},
        {"id": "low_r_high_c", "magic_style": "ngspice(lrhc)"},
        {"id": "low_r_low_c", "magic_style": "ngspice(lrlc)"},
    ]
    if styles != expected_styles:
        raise ResistanceError("declared Magic RC style matrix changed")
    if (
        extraction.get("integrated_extresist") is not True
        or extraction.get("replay_each_style") is not True
        or extraction.get("simplify") is not False
        or extraction.get("random_seed") != 12345
        or extraction.get("threshold_milliohm") != 0.0
        or extraction.get("mindelay_ps") != 0.0
        or extraction.get("minres_milliohm") != 0.0
        or extraction.get("semantic_comparison")
        != "exact_multiset_of_ports_devices_resistors_and_capacitors"
        or extraction.get("style_total_net_note")
        != "The nominal top-cell .ext statistics include one 1.11022e-16 "
        "gate-to-gate coupling record absent from all four corner-style .ext "
        "files; every style still outputs 15 top-cell nets and the same "
        "10-device, 630-resistor, 269-capacitor RC netlist element counts."
    ):
        raise ResistanceError("v1 extraction policy was weakened or changed")

    acceptance = contract.get("acceptance", {})
    if (
        acceptance.get("resistor_element_count") != 630
        or acceptance.get("capacitor_element_count") != 269
        or acceptance.get("device_count") != 10
        or acceptance.get("electrical_cases_per_style") != 33
        or acceptance.get("electrical_cases_failed_max") != 0
        or acceptance.get("unexpected_ngspice_warnings_max") != 0
        or acceptance.get("semantic_replay_required") is not True
    ):
        raise ResistanceError("v1 element, electrical, or replay gates changed")
    expected_stats = {
        "common_subcells": {
            "sky130_fd_pr__nfet_01v8_MJJGZY": {
                "nets_total": 4,
                "nets_extracted": 4,
                "nets_output": 4,
            },
            "sky130_fd_pr__pfet_01v8_WWEVP9": {
                "nets_total": 5,
                "nets_extracted": 4,
                "nets_output": 4,
            },
        },
        "top_by_style": {
            "high_r_high_c": {
                "nets_total": 36,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "high_r_low_c": {
                "nets_total": 36,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "low_r_high_c": {
                "nets_total": 36,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "low_r_low_c": {
                "nets_total": 36,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "nominal": {
                "nets_total": 37,
                "nets_extracted": 15,
                "nets_output": 15,
            },
        },
    }
    if acceptance.get("extraction_stats") != expected_stats:
        raise ResistanceError("v1 per-cell extraction statistics changed")
    connectivity = acceptance.get("programming_connectivity", {})
    if connectivity != {
        "absent_device_drain": "NROW_ABSENT/D.t0",
        "absent_forbidden_nodes": ["BL_ABSENT", "BL_PRESENT"],
        "absent_required_node": "ROM_DRAIN_ABSENT",
        "present_device_drain": "NROW_PRESENT/D.t0",
        "present_forbidden_nodes": ["BL_ABSENT", "ROM_DRAIN_ABSENT"],
        "present_required_node": "BL_PRESENT",
    }:
        raise ResistanceError("programming connectivity gate changed")

    simulation = contract.get("simulation", {})
    if simulation != {
        "default_workers": 8,
        "pvt_case_source": "deterministic_pvt_contract",
        "threshold_source": "deterministic_pvt_contract",
    }:
        raise ResistanceError("simulation policy changed")
    if set(contract.get("reports", {})) != {"artifacts", "json", "markdown"}:
        raise ResistanceError("resistance report paths are incomplete")
    for value in contract["reports"].values():
        repo_path(value)

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class")
        != "public_open_pdk_distributed_rc_extraction_and_simulation_of_local_demonstration_slice"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise ResistanceError("claim boundary must prohibit target-node scaling")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for phrase in ("N7", "N4", "GPU speedup", "silicon"):
        if phrase not in forbidden:
            raise ResistanceError(f"claim boundary does not cover {phrase}")

    pvt_contract_path = repo_path(inputs["deterministic_pvt_contract"])
    pvt_contract = strict_json(pvt_contract_path)
    try:
        pvt.validate_contract(pvt_contract)
        cases = pvt.generated_cases(pvt_contract)
    except pvt.ExtractedPvtError as exc:
        raise ResistanceError(f"invalid upstream PVT contract: {exc}") from exc
    if len(cases) != acceptance["electrical_cases_per_style"]:
        raise ResistanceError("upstream PVT case count does not match RC contract")
    return pvt_contract, cases


def verify_upstream(
    contract: dict[str, Any], lock: dict[str, Any]
) -> tuple[dict[str, Any], dict[tuple[Any, ...], dict[str, Any]]]:
    inputs = contract["inputs"]
    physical_path = repo_path(inputs["physical_result"])
    pvt_result_path = repo_path(inputs["deterministic_pvt_result"])
    physical_result = strict_json(physical_path)
    pvt_result = strict_json(pvt_result_path)
    if physical_result.get("status") != "pass":
        raise ResistanceError("upstream physical result did not pass")
    if physical_result.get("verification", {}).get("drc") != {
        "errors": 0,
        "status": "pass",
    }:
        raise ResistanceError("upstream DRC is not clean")
    lvs = physical_result.get("verification", {}).get("lvs", {})
    if (
        lvs.get("final_result") != "Circuits match uniquely."
        or lvs.get("pin_lists_equivalent") is not True
    ):
        raise ResistanceError("upstream LVS is not a unique pin-equivalent match")
    manifest = physical_result.get("pdk", {}).get("tree", {}).get("manifest_sha256")
    locked_manifest = lock.get("pdk", {}).get("installed_tree", {}).get(
        "manifest_sha256"
    )
    if not manifest or manifest != locked_manifest:
        raise ResistanceError("upstream physical result is not bound to locked PDK")

    artifacts = {item["path"]: item for item in physical_result.get("artifacts", [])}
    layout_records = []
    for key in ("top_layout", "nfet_layout", "pfet_layout"):
        relative = inputs[key]
        path = repo_path(relative)
        record = artifacts.get(relative)
        if (
            record is None
            or record.get("sha256") != sha256_file(path)
            or record.get("size_bytes") != path.stat().st_size
        ):
            raise ResistanceError(f"{key} does not match physical artifact manifest")
        layout_records.append(
            {
                "role": key,
                "path": relative,
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
            }
        )

    if pvt_result.get("status") != "pass" or pvt_result.get("summary", {}).get(
        "cases_failed"
    ) != 0:
        raise ResistanceError("deterministic capacitance-only PVT result did not pass")
    pvt_upstream = pvt_result.get("upstream_physical", {})
    if pvt_upstream.get("sha256") != sha256_file(physical_path):
        raise ResistanceError("PVT result is not bound to current physical result")
    if pvt_result.get("contract", {}).get("sha256") != sha256_file(
        repo_path(inputs["deterministic_pvt_contract"])
    ):
        raise ResistanceError("PVT result is not bound to current PVT contract")
    order = ("process_corner", "vdd_v", "temperature_c", "output_load_ff")
    baselines: dict[tuple[Any, ...], dict[str, Any]] = {}
    for case in pvt_result.get("cases", []):
        key = tuple(case[name] for name in order)
        if key in baselines:
            raise ResistanceError(f"duplicate baseline PVT point: {key}")
        baselines[key] = case
    if len(baselines) != 33 or any(case.get("status") != "pass" for case in baselines.values()):
        raise ResistanceError("baseline PVT case matrix is incomplete")
    return (
        {
            "deterministic_pvt": {
                "path": inputs["deterministic_pvt_result"],
                "sha256": sha256_file(pvt_result_path),
                "cases": len(baselines),
            },
            "layouts": layout_records,
            "pdk_tree_manifest_sha256": manifest,
            "physical": {
                "path": inputs["physical_result"],
                "sha256": sha256_file(physical_path),
                "experiment_id": physical_result["experiment_id"],
            },
        },
        baselines,
    )


def spice_statements(path: Path) -> list[list[str]]:
    combined: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("*"):
            continue
        stripped = stripped.split(";", 1)[0].strip()
        if not stripped:
            continue
        if stripped.startswith("+"):
            if not combined:
                raise ResistanceError(f"orphan SPICE continuation in {path}")
            combined[-1] += " " + stripped[1:].strip()
        else:
            combined.append(stripped)
    return [statement.split() for statement in combined]


def scaled_number(token: str, *, target: str) -> float:
    match = re.fullmatch(r"([-+0-9.eE]+)([fpnumk]?)", token, re.IGNORECASE)
    if match is None:
        raise ResistanceError(f"cannot parse extracted numeric token: {token}")
    value = float(match.group(1))
    suffix = match.group(2).lower()
    factors = {
        "ohm": {"": 1.0, "m": 1e-3, "k": 1e3},
        "ff": {"": 1e15, "f": 1.0, "p": 1e3, "n": 1e6, "u": 1e9, "m": 1e12},
    }
    if suffix not in factors[target]:
        raise ResistanceError(f"unsupported {target} suffix in {token}")
    result = value * factors[target][suffix]
    if not math.isfinite(result):
        raise ResistanceError(f"non-finite extracted numeric token: {token}")
    return result


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def component(adjacency: dict[str, set[str]], start: str) -> set[str]:
    seen = {start}
    pending = deque([start])
    while pending:
        node = pending.popleft()
        for neighbor in adjacency.get(node, set()):
            if neighbor not in seen:
                seen.add(neighbor)
                pending.append(neighbor)
    return seen


def parse_rc_netlist(
    path: Path, contract: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    statements = spice_statements(path)
    subcircuits = [tokens for tokens in statements if tokens[0].lower() == ".subckt"]
    if len(subcircuits) != 1 or subcircuits[0][1] != contract["top_cell"]:
        raise ResistanceError("RC netlist must contain exactly one expected subcircuit")
    ports = subcircuits[0][2:]
    if ports != contract["top_ports"]:
        raise ResistanceError(f"RC netlist ports differ from contract: {ports}")

    devices: list[dict[str, Any]] = []
    resistors: list[dict[str, Any]] = []
    capacitors: list[dict[str, Any]] = []
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for tokens in statements:
        initial = tokens[0][0].upper()
        if initial == "X":
            if len(tokens) < 6:
                raise ResistanceError(f"malformed extracted device: {tokens}")
            devices.append(
                {
                    "instance": tokens[0],
                    "terminals": tokens[1:5],
                    "model": tokens[5],
                    "parameters": sorted(tokens[6:]),
                }
            )
        elif initial == "R":
            if len(tokens) != 4:
                raise ResistanceError(f"malformed extracted resistor: {tokens}")
            value = scaled_number(tokens[3], target="ohm")
            if value <= 0:
                raise ResistanceError(f"nonpositive extracted resistor: {tokens}")
            resistor = {"nodes": sorted(tokens[1:3]), "value_ohm": value}
            resistors.append(resistor)
            adjacency[tokens[1]].add(tokens[2])
            adjacency[tokens[2]].add(tokens[1])
        elif initial == "C":
            if len(tokens) != 4:
                raise ResistanceError(f"malformed extracted capacitor: {tokens}")
            value = scaled_number(tokens[3], target="ff")
            if value < 0:
                raise ResistanceError(f"negative extracted capacitor: {tokens}")
            capacitors.append({"nodes": sorted(tokens[1:3]), "value_ff": value})

    acceptance = contract["acceptance"]
    if len(devices) != acceptance["device_count"]:
        raise ResistanceError(f"RC device count changed: {len(devices)}")
    if len(resistors) != acceptance["resistor_element_count"]:
        raise ResistanceError(f"RC resistor count changed: {len(resistors)}")
    if len(capacitors) != acceptance["capacitor_element_count"]:
        raise ResistanceError(f"RC capacitor count changed: {len(capacitors)}")
    model_counts = Counter(device["model"] for device in devices)
    if model_counts != {
        "sky130_fd_pr__nfet_01v8": 6,
        "sky130_fd_pr__pfet_01v8": 4,
    }:
        raise ResistanceError(f"unexpected RC device models: {model_counts}")

    connectivity = acceptance["programming_connectivity"]
    present_nodes = component(adjacency, connectivity["present_device_drain"])
    absent_nodes = component(adjacency, connectivity["absent_device_drain"])
    connectivity_checks = {
        "present_required_connected": connectivity["present_required_node"] in present_nodes,
        "present_forbidden_disconnected": all(
            node not in present_nodes
            for node in connectivity["present_forbidden_nodes"]
        ),
        "absent_required_connected": connectivity["absent_required_node"] in absent_nodes,
        "absent_forbidden_disconnected": all(
            node not in absent_nodes
            for node in connectivity["absent_forbidden_nodes"]
        ),
        "program_states_are_disjoint": present_nodes.isdisjoint(absent_nodes),
    }
    if not all(connectivity_checks.values()):
        raise ResistanceError(f"programming topology failed in RC graph: {connectivity_checks}")

    canonical = {
        "capacitors": sorted(
            (item["nodes"], item["value_ff"].hex()) for item in capacitors
        ),
        "devices": sorted(
            (
                device["terminals"],
                device["model"],
                device["parameters"],
            )
            for device in devices
        ),
        "ports": ports,
        "resistors": sorted(
            (item["nodes"], item["value_ohm"].hex()) for item in resistors
        ),
    }
    canonical_bytes = json.dumps(
        canonical, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    resistor_values = [item["value_ohm"] for item in resistors]
    capacitor_values = [item["value_ff"] for item in capacitors]
    metrics = {
        "capacitors": {
            "count": len(capacitors),
            "maximum_ff": max(capacitor_values),
            "nonzero_count": sum(value > 0 for value in capacitor_values),
            "total_ff": sum(capacitor_values),
        },
        "connectivity": {
            **connectivity_checks,
            "absent_component_node_count": len(absent_nodes),
            "present_component_node_count": len(present_nodes),
        },
        "devices": {"count": len(devices), "model_counts": dict(sorted(model_counts.items()))},
        "ports": ports,
        "resistors": {
            "count": len(resistors),
            "maximum_ohm": max(resistor_values),
            "median_ohm": quantile(resistor_values, 0.5),
            "minimum_ohm": min(resistor_values),
            "p95_ohm": quantile(resistor_values, 0.95),
            "sum_of_element_values_ohm_diagnostic_only": sum(resistor_values),
        },
        "semantic_sha256": sha256_bytes(canonical_bytes),
    }
    return metrics, canonical


def parse_res_ext(path: Path) -> dict[str, int]:
    counts = Counter()
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        keyword = stripped.split(maxsplit=1)[0]
        if keyword in {"rnode", "resist", "substrate", "device", "node"}:
            counts[keyword] += 1
    if counts["resist"] < 1 or counts["rnode"] < 1:
        raise ResistanceError(f"res.ext lacks detailed resistance records: {counts}")
    return dict(sorted(counts.items()))


def parse_magic_log(
    text: str, style: dict[str, str], contract: dict[str, Any]
) -> dict[str, Any]:
    required_markers = {
        "OT_EXTRESIST_THRESHOLD_MOHM": "0.0",
        "OT_EXTRESIST_MINDELAY_PS": "0.0",
        "OT_EXTRESIST_MINRES_MOHM": "0.0",
        "OT_EXTRESIST_SIMPLIFY": "off",
        "OT_EXTRACT_INTEGRATED_EXTRESIST": "on",
        "OT_EXTRACTION_STYLE": style["magic_style"],
        "OT_TOP_EXT": "1",
        "OT_TOP_RES_EXT": "1",
    }
    observed: dict[str, str] = {}
    for key, expected in required_markers.items():
        matches = re.findall(rf"(?m)^{re.escape(key)}=(.*)$", text)
        if matches != [expected]:
            raise ResistanceError(f"Magic marker {key}={matches} != {[expected]}")
        observed[key] = matches[0]
    prohibited = (
        "Error parsing",
        "is not one of the extraction styles Magic knows",
        "Magic error:",
        "exttospice failed",
    )
    found = [marker for marker in prohibited if marker in text]
    if found:
        raise ResistanceError(f"Magic full-RC run emitted fatal diagnostics: {found}")
    if text.count("exttospice finished.") != 1:
        raise ResistanceError("Magic did not finish ext2spice exactly once")

    blocks = re.findall(
        r"Processing cell ([^\s]+) for resistance extraction\.\n"
        r"(.*?Total Nets:\s*(\d+)\nNets extracted:\s*(\d+)\s*\([^\n]+\)\n"
        r"Nets output:\s*(\d+)\s*\([^\n]+\))",
        text,
        re.DOTALL,
    )
    observed_stats: dict[str, dict[str, int]] = {}
    for name, _, total, extracted, output in blocks:
        if name in observed_stats:
            raise ResistanceError(f"cell received multiple extraction passes: {name}")
        observed_stats[name] = {
            "nets_total": int(total),
            "nets_extracted": int(extracted),
            "nets_output": int(output),
        }
    contracted_stats = contract["acceptance"]["extraction_stats"]
    expected_stats = {
        **contracted_stats["common_subcells"],
        contract["top_cell"]: contracted_stats["top_by_style"][style["id"]],
    }
    if observed_stats != expected_stats:
        raise ResistanceError(
            f"per-cell extraction statistics {observed_stats} != {expected_stats}"
        )
    return {"markers": observed, "per_cell": observed_stats}


def run_magic_extraction(
    *,
    style: dict[str, str],
    pass_name: str,
    contract: dict[str, Any],
    variant: Path,
    magic: Path,
) -> dict[str, Any]:
    target = BUILD / "extraction" / style["id"] / pass_name
    target.mkdir(parents=True, exist_ok=True)
    for key in ("top_layout", "nfet_layout", "pfet_layout", "extractor_script"):
        source = repo_path(contract["inputs"][key])
        shutil.copyfile(source, target / source.name)
    log = target / "magic.log"
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "MAGTYPE": "mag",
            "OPENTALLAS_RC_STYLE": style["magic_style"],
            "PDK_ROOT": str(variant.parent),
            "TZ": "UTC",
        }
    )
    completed = subprocess.run(
        [
            str(magic),
            "-dnull",
            "-noconsole",
            "-rcfile",
            str(variant / "libs.tech" / "magic" / "sky130A.magicrc"),
            Path(contract["inputs"]["extractor_script"]).name,
        ],
        cwd=target,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise ResistanceError(
            f"Magic RC extraction failed for {style['id']}/{pass_name}: {completed.returncode}"
        )
    parsed_log = parse_magic_log(completed.stdout, style, contract)
    top = contract["top_cell"]
    required = {
        "ext": target / f"{top}.ext",
        "res_ext": target / f"{top}.res.ext",
        "res_lump": target / f"{top}.res.lump",
        "rc_pex": target / f"{top}.rc.pex.spice",
        "magic_log": log,
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise ResistanceError(f"Magic RC artifacts missing: {missing}")
    metrics, canonical = parse_rc_netlist(required["rc_pex"], contract)
    res_ext_counts = parse_res_ext(required["res_ext"])
    return {
        "artifact_paths": required,
        "canonical": canonical,
        "magic": parsed_log,
        "metrics": metrics,
        "pass_name": pass_name,
        "raw_rc_pex_sha256": sha256_file(required["rc_pex"]),
        "res_ext_counts": res_ext_counts,
        "style_id": style["id"],
    }


def prepare_model_decks(pdk_root: Path) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    tech = pdk_root / "libs.tech" / "ngspice"
    primitive = pdk_root / "libs.ref" / "sky130_fd_pr" / "spice"
    decks: dict[str, Path] = {}
    identities: dict[str, dict[str, Any]] = {}
    for corner in ("ss", "tt", "ff"):
        target = BUILD / "models" / corner
        target.mkdir(parents=True, exist_ok=True)
        sources = [
            tech / "parameters" / "invariant.spice",
            tech / "corners" / corner / "nonfet.spice",
            primitive / f"sky130_fd_pr__nfet_01v8__{corner}.corner.spice",
            primitive / f"sky130_fd_pr__nfet_01v8__{corner}.pm3.spice",
            primitive / f"sky130_fd_pr__pfet_01v8__{corner}.corner.spice",
            primitive / f"sky130_fd_pr__pfet_01v8__{corner}.pm3.spice",
        ]
        for source in sources:
            if not source.is_file():
                raise ResistanceError(f"missing installed primitive model: {source}")
            relative = str(source.relative_to(pdk_root))
            identities.setdefault(
                relative,
                {
                    "path": relative,
                    "sha256": sha256_file(source),
                    "size_bytes": source.stat().st_size,
                },
            )
            shutil.copyfile(source, target / source.name)
        deck = target / "models.spice"
        deck.write_text(
            "* Primitive-only installed SKY130A model deck for full-RC campaign\n"
            ".param mc_mm_switch=0\n"
            ".param mc_pr_switch=0\n"
            + "\n".join(
                f'.include "{target / source.name}"'
                for source in (sources[0], sources[1], sources[2], sources[4])
            )
            + "\n",
            encoding="utf-8",
        )
        (target / ".spiceinit").write_text("set ngbehavior=hsa\n", encoding="utf-8")
        decks[corner] = deck
    return decks, [identities[key] for key in sorted(identities)]


def render_testbench(
    template: str,
    case: dict[str, Any],
    model_deck: Path,
    rc_pex: Path,
) -> str:
    replacements = {
        "@TEMPERATURE_C@": str(case["temperature_c"]),
        "@MODEL_DECK@": str(model_deck),
        "@PEX_NETLIST@": str(rc_pex),
        "@VDD_V@": str(case["vdd_v"]),
        "@OUTPUT_LOAD_FF@": str(case["output_load_ff"]),
    }
    rendered = template
    for placeholder, value in replacements.items():
        if rendered.count(placeholder) < 1:
            raise ResistanceError(f"testbench lacks {placeholder}")
        rendered = rendered.replace(placeholder, value)
    if "@" in rendered:
        raise ResistanceError("unrendered testbench placeholder remains")
    return rendered


def run_electrical_case(
    *,
    style: dict[str, str],
    case: dict[str, Any],
    rc_pex: Path,
    model_decks: dict[str, Path],
    template: str,
    pvt_contract: dict[str, Any],
    baseline: dict[str, Any],
    executable: str,
) -> dict[str, Any]:
    target = BUILD / "cases" / style["id"] / case["case_id"]
    target.mkdir(parents=True, exist_ok=True)
    deck = target / "read.spice"
    model_deck = model_decks[case["process_corner"]]
    deck.write_text(
        render_testbench(template, case, model_deck, rc_pex), encoding="utf-8"
    )
    log = target / "ngspice.log"
    completed = subprocess.run(
        [executable, "-b", "-o", str(log), str(deck)],
        cwd=model_deck.parent,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    log_text = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
    failures: list[str] = []
    values: dict[str, float] = {}
    if completed.returncode != 0:
        failures.append(f"ngspice_return_code:{completed.returncode}")
    try:
        values = pvt.parse_measures(log_text)
    except pvt.ExtractedPvtError as exc:
        failures.append(f"measure_parse:{exc}")
    all_warnings = sorted(
        set(WARNING_RE.findall(log_text + "\n" + completed.stdout + "\n" + completed.stderr))
    )
    expected_warnings = sorted(set(all_warnings) & EXPECTED_BENIGN_WARNINGS)
    unexpected_warnings = sorted(set(all_warnings) - EXPECTED_BENIGN_WARNINGS)
    if values:
        failures.extend(pvt.evaluate(case, values, unexpected_warnings, pvt_contract))
    baseline_values = baseline["measures_si"]
    deltas = (
        {name: values[name] - baseline_values[name] for name in MEASURE_NAMES}
        if values
        else {}
    )
    metrics = (
        {
            "discharge_delay_ns": values["discharge_delay"] * 1e9,
            "post_read_supply_current_rms_ua": values["inactive_leakage"] * 1e6,
            "read_energy_fj": values["read_energy"] * 1e15,
            "read_margin_fraction_vdd": values["read_margin"] / case["vdd_v"],
        }
        if values
        else None
    )
    baseline_metrics = {
        "discharge_delay_ns": baseline_values["discharge_delay"] * 1e9,
        "post_read_supply_current_rms_ua": baseline_values["inactive_leakage"] * 1e6,
        "read_energy_fj": baseline_values["read_energy"] * 1e15,
        "read_margin_fraction_vdd": baseline_values["read_margin"] / case["vdd_v"],
    }
    metric_deltas = (
        {name: metrics[name] - baseline_metrics[name] for name in metrics}
        if metrics
        else {}
    )
    return {
        **case,
        "baseline_capacitance_only_case_id": baseline["case_id"],
        "baseline_metrics": baseline_metrics,
        "deck_sha256": sha256_file(deck),
        "expected_benign_warnings": expected_warnings,
        "failures": failures,
        "measure_deltas_vs_capacitance_only_si": deltas,
        "measures_si": values,
        "metric_deltas_vs_capacitance_only": metric_deltas,
        "metrics": metrics,
        "ngspice_log_sha256": sha256_file(log) if log.exists() else None,
        "status": "pass" if not failures else "fail",
        "style_id": style["id"],
        "unexpected_warnings": unexpected_warnings,
    }


def extremum(cases: list[dict[str, Any]], metric: str, maximum: bool) -> dict[str, Any]:
    usable = [case for case in cases if case["metrics"] is not None]
    selected = (max if maximum else min)(usable, key=lambda case: case["metrics"][metric])
    return {
        "case_id": selected["case_id"],
        "style_id": selected["style_id"],
        "value": selected["metrics"][metric],
    }


def archive_extraction_artifacts(
    extractions: list[dict[str, Any]], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    destination = repo_path(contract["reports"]["artifacts"])
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    records = []
    for extraction in extractions:
        prefix = f"{extraction['style_id']}.{extraction['pass_name']}"
        for role, source in extraction["artifact_paths"].items():
            suffix = {
                "ext": ".ext",
                "res_ext": ".res.ext",
                "res_lump": ".res.lump",
                "rc_pex": ".rc.pex.spice",
                "magic_log": ".magic.log",
            }[role]
            target = destination / f"{prefix}{suffix}"
            shutil.copyfile(source, target)
            records.append(
                {
                    "pass": extraction["pass_name"],
                    "path": str(target.relative_to(ROOT)),
                    "role": role,
                    "sha256": sha256_file(target),
                    "size_bytes": target.stat().st_size,
                    "style_id": extraction["style_id"],
                }
            )
    return sorted(records, key=lambda item: item["path"])


def nominal_case(cases: list[dict[str, Any]], style_id: str) -> dict[str, Any]:
    matches = [
        case
        for case in cases
        if case["style_id"] == style_id
        and case["process_corner"] == "tt"
        and case["vdd_v"] == 1.8
        and case["temperature_c"] == 25.0
        and case["output_load_ff"] == 20.0
    ]
    if len(matches) != 1:
        raise ResistanceError(f"cannot identify nominal electrical case for {style_id}")
    return matches[0]


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    style_map = {style["id"]: style for style in result["input_model"]["styles"]}
    lines = [
        "# SKY130A distributed-RC extraction and local PVT campaign",
        "",
        f"**Result:** **{result['status'].upper()}** "
        f"({summary['electrical']['cases_passed']}/{summary['electrical']['cases_total']} full-RC electrical cases passed)  ",
        "**Evidence class:** public open-PDK distributed-RC extraction and simulation of the archived local demonstration slice; not silicon  ",
        f"**Physical input:** `{result['upstream']['physical']['sha256']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}` / `{result['toolchain']['magic']['commit']}`",
        "",
        "## Extracted styles and electrical effect",
        "",
        "Each style has 630 explicit resistor elements, 269 capacitors, and ten",
        "MOS instances. The resistor sum below is only an extraction diagnostic;",
        "it is not an end-to-end or equivalent network resistance.",
        "",
        "| PDK RC style | Sum of R elements (ohm, diagnostic) | Total C (fF) | Nominal TT delay (ns) | Nominal delay vs C-only | Worst delay over 33 cases (ns) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    by_style = summary["electrical"]["by_style"]
    extraction_by_style = summary["extraction"]["by_style"]
    for style_id in [style["id"] for style in result["input_model"]["styles"]]:
        item = by_style[style_id]
        extraction = extraction_by_style[style_id]
        nominal = item["nominal_case"]
        delay = nominal["metrics"]["discharge_delay_ns"]
        baseline_delay = nominal["baseline_metrics"]["discharge_delay_ns"]
        delta_pct = (delay / baseline_delay - 1.0) * 100.0
        lines.append(
            f"| `{style_map[style_id]['magic_style']}` | "
            f"{extraction['metrics']['resistors']['sum_of_element_values_ohm_diagnostic_only']:.6g} | "
            f"{extraction['metrics']['capacitors']['total_ff']:.6g} | "
            f"{delay:.6g} | {delta_pct:+.3f}% | "
            f"{item['max_discharge_delay_ns']['value']:.6g} |"
        )
    lines.extend(
        [
            "",
            "The comparison is full-RC PEX versus the earlier capacitance-only PEX.",
            "Because network subdivision redistributes capacitance as well as adding",
            "resistors, the delta must not be labeled a pure resistance-only penalty.",
            "",
            "## Extraction controls",
            "",
            "- Magic's integrated `extract do extresist` path runs exactly once per style.",
            "- Network threshold, delay threshold, and individual-resistor pruning threshold are all zero; simplification is off.",
            "- Every style is extracted twice in a fresh directory. Raw SPICE statement order may differ, but the exact multiset of ports, devices, resistor edges/values, and capacitor edges/values must match.",
            f"- All {len(result['input_model']['styles'])} style replays pass semantic equality.",
            f"- {result['input_model']['extraction']['style_total_net_note']}",
            "- The resistor graph connects the programmed row drain only to `BL_PRESENT`; the absent row drain terminates at `ROM_DRAIN_ABSENT`, remains disconnected from both physical bitlines, and the two programming-state components are disjoint.",
            "",
            "## Electrical sweep",
            "",
            "For each RC style, the exact archived full-RC netlist is simulated over",
            "the same 33 SS/TT/FF, 1.62/1.80/1.98-V, -40/25/125-C, and",
            "5/20/80-fF points used by the capacitance-only campaign. All local",
            "programmed-discharge, absent-via retention, expert masking, sense polarity,",
            "margin, delay, energy, current, and warning checks pass.",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in result["claim_boundary"]["establishes"])
    lines.append("")
    lines.extend(
        f"- Does not establish: {item}."
        for item in result["claim_boundary"]["forbidden_inferences"]
    )
    lines.extend(
        [
            "",
            "This local 32.5 × 11.5-µm demonstration is deliberately roomy. No RC",
            "number here may be feature-size-scaled into N7/N4, a whole array, a wafer,",
            "or a GPU comparison.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_sky130_resistance.py",
            "```",
            "",
            "Exact primary/replay artifacts, model identities, per-case measures,",
            "comparisons, thresholds, and SHA-256 values are stored in",
            "`results/spice/sky130_resistance/resistance.json`.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    contract = strict_json(CONTRACT_PATH)
    pvt_contract, cases = validate_contract(contract)
    if args.validate_only:
        print(
            "PASS: SKY130 resistance contract; five RC styles, semantic replay, "
            f"{len(cases)} electrical cases per style"
        )
        return 0

    workers = args.workers or contract["simulation"]["default_workers"]
    if not 1 <= workers <= 16:
        raise ResistanceError("workers must be between 1 and 16")
    lock = strict_json(repo_path(contract["inputs"]["pdk_lock"]))
    variant = physical.locate_pdk(args.pdk_root)
    magic, netgen = physical.locate_tools(
        lock, args.tool_root, args.magic, None
    )
    pdk_identity = physical.verify_pdk(variant, lock)
    physical_tools = physical.tool_identities(magic, netgen, lock)
    ngspice = pvt.ngspice_identity()
    upstream, baselines = verify_upstream(contract, lock)

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True)
    extraction_runs: list[dict[str, Any]] = []
    primary_by_style: dict[str, dict[str, Any]] = {}
    replay_checks: dict[str, dict[str, Any]] = {}
    for style in contract["extraction"]["styles"]:
        print(f"[RC] extracting {style['id']} primary", flush=True)
        primary = run_magic_extraction(
            style=style,
            pass_name="primary",
            contract=contract,
            variant=variant,
            magic=magic,
        )
        print(f"[RC] extracting {style['id']} replay", flush=True)
        replay = run_magic_extraction(
            style=style,
            pass_name="replay",
            contract=contract,
            variant=variant,
            magic=magic,
        )
        semantic_equal = primary["canonical"] == replay["canonical"]
        replay_check = {
            "primary_raw_rc_pex_sha256": primary["raw_rc_pex_sha256"],
            "raw_byte_identical": primary["raw_rc_pex_sha256"]
            == replay["raw_rc_pex_sha256"],
            "replay_raw_rc_pex_sha256": replay["raw_rc_pex_sha256"],
            "semantic_sha256": primary["metrics"]["semantic_sha256"],
            "status": "pass" if semantic_equal else "fail",
        }
        if contract["acceptance"]["semantic_replay_required"] and not semantic_equal:
            raise ResistanceError(f"semantic extraction replay failed for {style['id']}")
        primary_by_style[style["id"]] = primary
        replay_checks[style["id"]] = replay_check
        extraction_runs.extend([primary, replay])

    model_decks, model_files = prepare_model_decks(variant)
    template_path = repo_path(contract["inputs"]["testbench_template"])
    template = template_path.read_text(encoding="utf-8")
    order = ("process_corner", "vdd_v", "temperature_c", "output_load_ff")
    jobs: list[tuple[dict[str, str], dict[str, Any], Path, dict[str, Any]]] = []
    for style in contract["extraction"]["styles"]:
        rc_pex = primary_by_style[style["id"]]["artifact_paths"]["rc_pex"]
        for case in cases:
            key = tuple(case[name] for name in order)
            baseline = baselines.get(key)
            if baseline is None:
                raise ResistanceError(f"missing capacitance-only baseline for {key}")
            jobs.append((style, case, rc_pex, baseline))

    electrical: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {
            executor.submit(
                run_electrical_case,
                style=style,
                case=case,
                rc_pex=rc_pex,
                model_decks=model_decks,
                template=template,
                pvt_contract=pvt_contract,
                baseline=baseline,
                executable=ngspice["executable"],
            ): (style["id"], case["case_id"])
            for style, case, rc_pex, baseline in jobs
        }
        for completed_count, future in enumerate(as_completed(pending), start=1):
            result = future.result()
            electrical.append(result)
            if completed_count == 1 or completed_count % 15 == 0 or completed_count == len(jobs):
                print(
                    f"[PVT {completed_count:03d}/{len(jobs)}] "
                    f"{result['style_id']}/{result['case_id']} {result['status']}",
                    flush=True,
                )
    style_order = {style["id"]: index for index, style in enumerate(contract["extraction"]["styles"])}
    electrical.sort(key=lambda case: (style_order[case["style_id"]], case["case_id"]))
    failures = [case for case in electrical if case["status"] != "pass"]
    warning_counts = Counter(
        warning for case in electrical for warning in case["unexpected_warnings"]
    )
    if len(failures) > contract["acceptance"]["electrical_cases_failed_max"]:
        status = "fail"
    elif len(electrical) != len(contract["extraction"]["styles"]) * len(cases):
        status = "fail"
    elif warning_counts:
        status = "fail"
    else:
        status = "pass"

    extraction_summary = {
        "by_style": {
            style["id"]: {
                "magic_style": style["magic_style"],
                "metrics": primary_by_style[style["id"]]["metrics"],
                "replay": replay_checks[style["id"]],
                "res_ext_counts": primary_by_style[style["id"]]["res_ext_counts"],
            }
            for style in contract["extraction"]["styles"]
        },
        "styles_passed_semantic_replay": sum(
            check["status"] == "pass" for check in replay_checks.values()
        ),
        "styles_total": len(replay_checks),
    }
    electrical_by_style: dict[str, Any] = {}
    for style in contract["extraction"]["styles"]:
        subset = [case for case in electrical if case["style_id"] == style["id"]]
        electrical_by_style[style["id"]] = {
            "cases_failed": sum(case["status"] != "pass" for case in subset),
            "cases_passed": sum(case["status"] == "pass" for case in subset),
            "cases_total": len(subset),
            "max_discharge_delay_ns": extremum(subset, "discharge_delay_ns", True),
            "max_post_read_supply_current_rms_ua": extremum(
                subset, "post_read_supply_current_rms_ua", True
            ),
            "max_read_energy_fj": extremum(subset, "read_energy_fj", True),
            "min_read_margin_fraction_vdd": extremum(
                subset, "read_margin_fraction_vdd", False
            ),
            "nominal_case": nominal_case(electrical, style["id"]),
        }
    electrical_summary = {
        "by_style": electrical_by_style,
        "cases_failed": len(failures),
        "cases_passed": len(electrical) - len(failures),
        "cases_total": len(electrical),
        "global_max_discharge_delay_ns": extremum(
            electrical, "discharge_delay_ns", True
        ),
        "global_min_read_margin_fraction_vdd": extremum(
            electrical, "read_margin_fraction_vdd", False
        ),
        "unexpected_warning_counts": dict(sorted(warning_counts.items())),
    }
    artifacts = archive_extraction_artifacts(extraction_runs, contract)
    result = {
        "acceptance": contract["acceptance"],
        "artifacts": artifacts,
        "cases": electrical,
        "claim_boundary": contract["claim_boundary"],
        "contract": {
            "path": str(CONTRACT_PATH.relative_to(ROOT)),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "dependencies": {
            "extractor_script": {
                "path": contract["inputs"]["extractor_script"],
                "sha256": sha256_file(repo_path(contract["inputs"]["extractor_script"])),
            },
            "extracted_pvt_runner": {
                "path": str(Path(pvt.__file__).resolve().relative_to(ROOT)),
                "sha256": sha256_file(Path(pvt.__file__).resolve()),
            },
            "physical_runner": {
                "path": str(Path(physical.__file__).resolve().relative_to(ROOT)),
                "sha256": sha256_file(Path(physical.__file__).resolve()),
            },
        },
        "experiment_id": contract["experiment_id"],
        "input_model": {
            "extraction": {
                key: value
                for key, value in contract["extraction"].items()
                if key != "styles"
            },
            "pvt_campaigns": pvt_contract["campaigns"],
            "pvt_dimensions": pvt_contract["dimensions"],
            "styles": contract["extraction"]["styles"],
        },
        "pdk": {
            **pdk_identity,
            "model_files": model_files,
            "model_scope": "installed invariant/nonfet plus 1V8 NFET/PFET SS/TT/FF primitive files",
        },
        "pdk_lock": {
            "path": contract["inputs"]["pdk_lock"],
            "sha256": sha256_file(repo_path(contract["inputs"]["pdk_lock"])),
        },
        "runner": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "workers": workers,
        },
        "schema_version": 1,
        "status": status,
        "summary": {
            "electrical": electrical_summary,
            "extraction": extraction_summary,
        },
        "template": {
            "path": contract["inputs"]["testbench_template"],
            "sha256": sha256_file(template_path),
        },
        "toolchain": {
            "magic": physical_tools["magic"],
            "ngspice": ngspice,
        },
        "upstream": upstream,
    }
    json_path = repo_path(contract["reports"]["json"])
    markdown_path = repo_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    markdown_path.write_text(markdown(result), encoding="utf-8")
    print(
        f"{status.upper()}: {electrical_summary['cases_passed']}/"
        f"{electrical_summary['cases_total']} full-RC cases passed; "
        f"semantic replay {extraction_summary['styles_passed_semantic_replay']}/"
        f"{extraction_summary['styles_total']}",
        flush=True,
    )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        ResistanceError,
        physical.PhysicalExperimentError,
        pvt.ExtractedPvtError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
