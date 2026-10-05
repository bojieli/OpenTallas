#!/usr/bin/env python3
"""Run governed IHP SG13G2 detailed-RC extraction and local PVT simulation."""

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
import tempfile
from typing import Any

import run_ihp_extracted_pvt as pvt
import run_ihp_physical as physical


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "spice" / "ihp_sg13g2" / "rom_slice" / "resistance_contract.json"
)
BUILD = ROOT / "spice" / "build" / "ihp_sg13g2_resistance"
MEASURE_NAMES = pvt.MEASURE_NAMES


class IhpResistanceError(RuntimeError):
    """A governed IHP detailed-RC input, run, or acceptance gate failed."""


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
        raise IhpResistanceError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise IhpResistanceError(
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
        raise IhpResistanceError(f"repository path must be contained: {value}")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise IhpResistanceError(f"repository path escapes root: {value}") from exc
    return resolved


def validate_contract(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if contract.get("schema_version") != 1:
        raise IhpResistanceError("resistance contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_via_rom_distributed_rc_v1":
        raise IhpResistanceError("unexpected IHP resistance experiment_id")
    if contract.get("top_cell") != "ihp_sg13g2_rom_slice":
        raise IhpResistanceError("unexpected IHP resistance top cell")
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
        raise IhpResistanceError("IHP RC ports are incomplete, reordered, or changed")

    expected_inputs = {
        "deterministic_pvt_contract",
        "deterministic_pvt_result",
        "extractor_script",
        "nfet_layout",
        "pdk_lock",
        "pfet_layout",
        "physical_result",
        "spice_init",
        "testbench_template",
        "top_layout",
    }
    inputs = contract.get("inputs", {})
    if set(inputs) != expected_inputs:
        raise IhpResistanceError("IHP resistance input set is incomplete")
    for value in inputs.values():
        if not repo_path(value).is_file():
            raise IhpResistanceError(f"missing IHP resistance input: {value}")

    expected_styles = [
        {"id": "nominal", "magic_style": "ngspice()"},
        {"id": "high_r_high_c", "magic_style": "ngspice(hrhc)"},
        {"id": "high_r_low_c", "magic_style": "ngspice(hrlc)"},
        {"id": "low_r_high_c", "magic_style": "ngspice(lrhc)"},
        {"id": "low_r_low_c", "magic_style": "ngspice(lrlc)"},
    ]
    extraction = contract.get("extraction", {})
    if extraction.get("styles") != expected_styles:
        raise IhpResistanceError("declared IHP Magic RC style matrix changed")
    expected_note = (
        "All five styles emit the same 10-device, 41-resistor, 68-capacitor RC "
        "netlist element counts. The two high-R styles extract and output 15 of "
        "41 top-cell networks; nominal and both low-R styles extract and output "
        "14 of 41. Both primitive subcells extract and output one substrate/well "
        "network."
    )
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
        or extraction.get("style_total_net_note") != expected_note
    ):
        raise IhpResistanceError("IHP v1 detailed-RC policy was weakened or changed")

    acceptance = contract.get("acceptance", {})
    if (
        acceptance.get("resistor_element_count") != 41
        or acceptance.get("capacitor_element_count") != 68
        or acceptance.get("device_count") != 10
        or acceptance.get("model_counts")
        != {"sg13_lv_nmos": 6, "sg13_lv_pmos": 4}
        or acceptance.get("electrical_cases_per_style") != 33
        or acceptance.get("electrical_cases_failed_max") != 0
        or acceptance.get("extraction_feedback_errors_max") != 0
        or acceptance.get("unexpected_ngspice_warnings_max") != 0
        or acceptance.get("semantic_replay_required") is not True
    ):
        raise IhpResistanceError("IHP v1 element, electrical, or replay gates changed")
    expected_stats = {
        "common_subcells": {
            "sg13_lv_nmos_3CGW2K": {
                "nets_total": 4,
                "nets_extracted": 1,
                "nets_output": 1,
            },
            "sg13_lv_pmos_GBCT8S": {
                "nets_total": 5,
                "nets_extracted": 1,
                "nets_output": 1,
            },
        },
        "top_by_style": {
            "nominal": {
                "nets_total": 41,
                "nets_extracted": 14,
                "nets_output": 14,
            },
            "high_r_high_c": {
                "nets_total": 41,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "high_r_low_c": {
                "nets_total": 41,
                "nets_extracted": 15,
                "nets_output": 15,
            },
            "low_r_high_c": {
                "nets_total": 41,
                "nets_extracted": 14,
                "nets_output": 14,
            },
            "low_r_low_c": {
                "nets_total": 41,
                "nets_extracted": 14,
                "nets_output": 14,
            },
        },
    }
    if acceptance.get("extraction_stats") != expected_stats:
        raise IhpResistanceError("IHP v1 per-cell extraction statistics changed")
    if acceptance.get("programming_connectivity") != {
        "absent_forbidden_nodes": ["BL_ABSENT", "BL_PRESENT"],
        "absent_required_node": "ROM_DRAIN_ABSENT",
        "absent_row_gate": "WL_ABSENT",
        "gate_terminal_index": 1,
        "present_forbidden_nodes": ["BL_ABSENT", "ROM_DRAIN_ABSENT"],
        "present_required_node": "BL_PRESENT",
        "present_row_gate": "WL_PRESENT",
        "programmed_terminal_index": 2,
    }:
        raise IhpResistanceError("IHP programming-connectivity gate changed")
    if acceptance.get("nmos_body_paths") != {
        "body_terminal_index": 3,
        "ground_node": "VGND",
        "non_ground_body_count": 6,
    }:
        raise IhpResistanceError("IHP extracted NMOS body-path gate changed")

    if contract.get("simulation") != {
        "case_timeout_seconds": 300,
        "default_workers": 4,
        "pvt_case_source": "deterministic_pvt_contract",
        "threshold_source": "deterministic_pvt_contract",
    }:
        raise IhpResistanceError("IHP RC simulation policy changed")
    if set(contract.get("reports", {})) != {"artifacts", "json", "markdown"}:
        raise IhpResistanceError("IHP resistance report paths are incomplete")
    for value in contract["reports"].values():
        repo_path(value)

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class")
        != "independent_public_open_pdk_distributed_rc_extraction_and_simulation_of_local_demonstration_slice"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise IhpResistanceError("IHP RC claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for phrase in ("N7", "N4", "GPU speedup", "silicon"):
        if phrase not in forbidden:
            raise IhpResistanceError(f"IHP RC claim boundary does not cover {phrase}")

    pvt_contract = strict_json(repo_path(inputs["deterministic_pvt_contract"]))
    try:
        pvt.validate_contract(pvt_contract)
        cases = pvt.generated_cases(pvt_contract)
    except pvt.IhpPvtError as exc:
        raise IhpResistanceError(f"invalid upstream IHP PVT contract: {exc}") from exc
    if len(cases) != acceptance["electrical_cases_per_style"]:
        raise IhpResistanceError("upstream IHP PVT case count changed")
    return pvt_contract, cases


def verify_upstream(
    contract: dict[str, Any], lock: dict[str, Any]
) -> tuple[dict[str, Any], dict[tuple[Any, ...], dict[str, Any]]]:
    inputs = contract["inputs"]
    physical_path = repo_path(inputs["physical_result"])
    pvt_path = repo_path(inputs["deterministic_pvt_result"])
    physical_result = strict_json(physical_path)
    pvt_result = strict_json(pvt_path)
    if physical_result.get("status") != "pass":
        raise IhpResistanceError("upstream IHP physical result did not pass")
    if physical_result.get("verification", {}).get("drc") != {
        "errors": 0,
        "status": "pass",
    }:
        raise IhpResistanceError("upstream IHP full DRC is not clean")
    lvs = physical_result.get("verification", {}).get("lvs", {})
    if (
        lvs.get("final_result") != "Circuits match uniquely."
        or lvs.get("pin_lists_equivalent") is not True
    ):
        raise IhpResistanceError("upstream IHP LVS is not unique and pin-complete")
    manifest = physical_result.get("pdk", {}).get("tree", {}).get("manifest_sha256")
    locked_manifest = lock.get("pdk", {}).get("installed_tree", {}).get(
        "manifest_sha256"
    )
    if not manifest or manifest != locked_manifest:
        raise IhpResistanceError("upstream IHP physical result is not PDK-locked")

    artifacts = {item["path"]: item for item in physical_result.get("artifacts", [])}
    layout_records: list[dict[str, Any]] = []
    for role in ("top_layout", "nfet_layout", "pfet_layout"):
        relative = inputs[role]
        path = repo_path(relative)
        record = artifacts.get(relative)
        if (
            record is None
            or record.get("sha256") != sha256_file(path)
            or record.get("size_bytes") != path.stat().st_size
        ):
            raise IhpResistanceError(f"{role} differs from IHP physical manifest")
        layout_records.append(
            {
                "role": role,
                "path": relative,
                "sha256": record["sha256"],
                "size_bytes": record["size_bytes"],
            }
        )

    if pvt_result.get("status") != "pass" or pvt_result.get("summary", {}).get(
        "cases_failed"
    ) != 0:
        raise IhpResistanceError("IHP capacitance-only PVT baseline did not pass")
    if pvt_result.get("upstream_physical", {}).get("sha256") != sha256_file(
        physical_path
    ):
        raise IhpResistanceError("IHP PVT baseline is not bound to physical result")
    if pvt_result.get("contract", {}).get("sha256") != sha256_file(
        repo_path(inputs["deterministic_pvt_contract"])
    ):
        raise IhpResistanceError("IHP PVT result is not bound to current contract")
    if pvt_result.get("pdk", {}).get("tree_manifest_sha256") != manifest:
        raise IhpResistanceError("IHP PVT and physical results use different PDK trees")

    order = ("process_corner", "vdd_v", "temperature_c", "output_load_ff")
    baselines: dict[tuple[Any, ...], dict[str, Any]] = {}
    for case in pvt_result.get("cases", []):
        key = tuple(case[name] for name in order)
        if key in baselines:
            raise IhpResistanceError(f"duplicate IHP PVT baseline point: {key}")
        baselines[key] = case
    if len(baselines) != 33 or any(
        case.get("status") != "pass" for case in baselines.values()
    ):
        raise IhpResistanceError("IHP baseline PVT matrix is incomplete")
    return (
        {
            "deterministic_pvt": {
                "path": inputs["deterministic_pvt_result"],
                "sha256": sha256_file(pvt_path),
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
                raise IhpResistanceError(f"orphan SPICE continuation in {path}")
            combined[-1] += " " + stripped[1:].strip()
        else:
            combined.append(stripped)
    return [statement.split() for statement in combined]


def scaled_number(token: str, *, target: str) -> float:
    match = re.fullmatch(r"([-+0-9.eE]+)([fpnumk]?)", token, re.IGNORECASE)
    if match is None:
        raise IhpResistanceError(f"cannot parse extracted numeric token: {token}")
    value = float(match.group(1))
    suffix = match.group(2).lower()
    factors = {
        "ohm": {"": 1.0, "m": 1e-3, "k": 1e3},
        "ff": {"": 1e15, "f": 1.0, "p": 1e3, "n": 1e6, "u": 1e9, "m": 1e12},
    }
    if suffix not in factors[target]:
        raise IhpResistanceError(f"unsupported {target} suffix in {token}")
    result = value * factors[target][suffix]
    if not math.isfinite(result):
        raise IhpResistanceError(f"non-finite extracted numeric token: {token}")
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
        raise IhpResistanceError("RC netlist lacks exactly one expected subcircuit")
    ports = subcircuits[0][2:]
    if ports != contract["top_ports"]:
        raise IhpResistanceError(f"IHP RC ports differ from contract: {ports}")

    devices: list[dict[str, Any]] = []
    resistors: list[dict[str, Any]] = []
    capacitors: list[dict[str, Any]] = []
    adjacency: defaultdict[str, set[str]] = defaultdict(set)
    for tokens in statements:
        initial = tokens[0][0].upper()
        if initial == "X":
            if len(tokens) < 6:
                raise IhpResistanceError(f"malformed extracted device: {tokens}")
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
                raise IhpResistanceError(f"malformed extracted resistor: {tokens}")
            value = scaled_number(tokens[3], target="ohm")
            if value <= 0:
                raise IhpResistanceError(f"nonpositive extracted resistor: {tokens}")
            resistors.append({"nodes": sorted(tokens[1:3]), "value_ohm": value})
            adjacency[tokens[1]].add(tokens[2])
            adjacency[tokens[2]].add(tokens[1])
        elif initial == "C":
            if len(tokens) != 4:
                raise IhpResistanceError(f"malformed extracted capacitor: {tokens}")
            value = scaled_number(tokens[3], target="ff")
            if value < 0:
                raise IhpResistanceError(f"negative extracted capacitor: {tokens}")
            capacitors.append({"nodes": sorted(tokens[1:3]), "value_ff": value})

    acceptance = contract["acceptance"]
    if len(devices) != acceptance["device_count"]:
        raise IhpResistanceError(f"IHP RC device count changed: {len(devices)}")
    if len(resistors) != acceptance["resistor_element_count"]:
        raise IhpResistanceError(f"IHP RC resistor count changed: {len(resistors)}")
    if len(capacitors) != acceptance["capacitor_element_count"]:
        raise IhpResistanceError(f"IHP RC capacitor count changed: {len(capacitors)}")
    model_counts = Counter(device["model"] for device in devices)
    if dict(sorted(model_counts.items())) != acceptance["model_counts"]:
        raise IhpResistanceError(f"unexpected IHP RC device models: {model_counts}")

    connectivity = acceptance["programming_connectivity"]
    gate_index = connectivity["gate_terminal_index"]
    programmed_index = connectivity["programmed_terminal_index"]

    def row_device(gate: str) -> dict[str, Any]:
        matches = [
            device
            for device in devices
            if device["model"] == "sg13_lv_nmos"
            and device["terminals"][gate_index] == gate
        ]
        if len(matches) != 1:
            raise IhpResistanceError(
                f"expected one IHP row device gated by {gate}, got {len(matches)}"
            )
        return matches[0]

    present_device = row_device(connectivity["present_row_gate"])
    absent_device = row_device(connectivity["absent_row_gate"])
    present_start = present_device["terminals"][programmed_index]
    absent_start = absent_device["terminals"][programmed_index]
    present_nodes = component(adjacency, present_start)
    absent_nodes = component(adjacency, absent_start)
    connectivity_checks = {
        "present_required_connected": connectivity["present_required_node"]
        in present_nodes,
        "present_forbidden_disconnected": all(
            node not in present_nodes for node in connectivity["present_forbidden_nodes"]
        ),
        "absent_required_connected": connectivity["absent_required_node"]
        in absent_nodes,
        "absent_forbidden_disconnected": all(
            node not in absent_nodes for node in connectivity["absent_forbidden_nodes"]
        ),
        "program_states_are_disjoint": present_nodes.isdisjoint(absent_nodes),
    }
    if not all(connectivity_checks.values()):
        raise IhpResistanceError(
            f"IHP programming topology failed in resistor graph: {connectivity_checks}"
        )

    body_contract = acceptance["nmos_body_paths"]
    body_index = body_contract["body_terminal_index"]
    ground = body_contract["ground_node"]
    nmos_bodies = [
        device["terminals"][body_index]
        for device in devices
        if device["model"] == "sg13_lv_nmos"
    ]
    non_ground_bodies = sorted(set(body for body in nmos_bodies if body != ground))
    body_checks = {
        "all_nmos_bodies_are_non_ground_nodes": len(non_ground_bodies)
        == len(nmos_bodies),
        "non_ground_body_count_matches": len(non_ground_bodies)
        == body_contract["non_ground_body_count"],
        "all_body_components_reach_ground": all(
            ground in component(adjacency, body) for body in non_ground_bodies
        ),
    }
    if not all(body_checks.values()):
        raise IhpResistanceError(
            f"IHP extracted NMOS body paths were lost: {body_checks}"
        )

    canonical = {
        "capacitors": sorted(
            (item["nodes"], item["value_ff"].hex()) for item in capacitors
        ),
        "devices": sorted(
            (device["terminals"], device["model"], device["parameters"])
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
            "absent_programmed_terminal": absent_start,
            "present_component_node_count": len(present_nodes),
            "present_programmed_terminal": present_start,
        },
        "devices": {
            "count": len(devices),
            "model_counts": dict(sorted(model_counts.items())),
        },
        "nmos_body_paths": {
            **body_checks,
            "body_nodes": non_ground_bodies,
            "count": len(non_ground_bodies),
            "ground_node": ground,
        },
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
        raise IhpResistanceError(
            f"IHP res.ext lacks detailed resistance records: {counts}"
        )
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
    observed_markers: dict[str, str] = {}
    for key, expected in required_markers.items():
        matches = re.findall(rf"(?m)^{re.escape(key)}=(.*)$", text)
        if matches != [expected]:
            raise IhpResistanceError(
                f"IHP Magic marker {key}={matches} != {[expected]}"
            )
        observed_markers[key] = matches[0]
    feedback_errors = sorted(
        {
            line.strip()
            for line in text.splitlines()
            if re.search(
                r"(?i)(^\s*(error|fatal)(:|\s)|illegal overlap|"
                r"error while extracting|magic error:|exttospice failed)",
                line,
            )
        }
    )
    if len(feedback_errors) > contract["acceptance"]["extraction_feedback_errors_max"]:
        raise IhpResistanceError(
            f"IHP detailed extraction emitted geometry/tool errors: {feedback_errors}"
        )
    if "is not one of the extraction styles Magic knows" in text:
        raise IhpResistanceError("IHP Magic rejected the requested RC style")
    if text.count("exttospice finished.") != 1:
        raise IhpResistanceError("IHP Magic did not finish ext2spice exactly once")

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
            raise IhpResistanceError(f"IHP cell extracted more than once: {name}")
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
        raise IhpResistanceError(
            f"IHP per-cell extraction statistics {observed_stats} != {expected_stats}"
        )
    return {
        "feedback_error_count": len(feedback_errors),
        "feedback_errors": feedback_errors,
        "markers": observed_markers,
        "per_cell": observed_stats,
    }


def run_magic_extraction(
    *,
    style: dict[str, str],
    pass_name: str,
    contract: dict[str, Any],
    pdk_root: Path,
    variant: Path,
    magic: Path,
) -> dict[str, Any]:
    target = BUILD / "extraction" / style["id"] / pass_name
    target.mkdir(parents=True, exist_ok=False)
    for role in ("top_layout", "nfet_layout", "pfet_layout", "extractor_script"):
        source = repo_path(contract["inputs"][role])
        shutil.copy2(source, target / source.name)
    log = target / "magic.log"
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "MAGTYPE": "mag",
            "OPENTALLAS_RC_STYLE": style["magic_style"],
            "PDK_ROOT": str(pdk_root),
            "TZ": "UTC",
        }
    )
    completed = subprocess.run(
        [
            str(magic),
            "-dnull",
            "-noconsole",
            "-rcfile",
            str(variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc"),
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
        raise IhpResistanceError(
            f"IHP Magic RC extraction failed for {style['id']}/{pass_name}: "
            f"{completed.returncode}\n{completed.stdout}"
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
    missing = [role for role, path in required.items() if not path.is_file()]
    if missing:
        raise IhpResistanceError(f"IHP Magic RC artifacts missing: {missing}")
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


def model_dependencies(pdk_root: Path) -> tuple[Path, list[dict[str, Any]]]:
    model_root = pdk_root / "ihp-sg13g2" / "libs.tech" / "ngspice" / "models"
    corner = model_root / "cornerMOSlv.lib"
    files = [
        corner,
        model_root / "sg13g2_moslv_mod.lib",
        model_root / "sg13g2_moslv_parm.lib",
    ]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise IhpResistanceError(
            f"official IHP low-voltage model closure is incomplete: {missing}"
        )
    return (
        corner,
        [
            {
                "path": path.relative_to(pdk_root).as_posix(),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in files
        ],
    )


def run_electrical_case(
    *,
    style: dict[str, str],
    case: dict[str, Any],
    rc_pex: Path,
    template: str,
    corner_library: Path,
    spice_init: Path,
    pvt_contract: dict[str, Any],
    baseline: dict[str, Any],
    executable: Path,
    pdk_root: Path,
    osdi_root: Path,
    timeout_seconds: int,
) -> dict[str, Any]:
    target = BUILD / "cases" / style["id"] / case["case_id"]
    target.mkdir(parents=True, exist_ok=False)
    deck = target / "read.spice"
    deck.write_text(
        pvt.render_deck(template, case, corner_library, rc_pex), encoding="utf-8"
    )
    shutil.copy2(spice_init, target / ".spiceinit")
    environment = os.environ.copy()
    environment.update(
        {
            "LC_ALL": "C",
            "OPENTALLAS_IHP_PDK_ROOT": str(pdk_root),
            "OPENTALLAS_IHP_OSDI_ROOT": str(osdi_root),
            "TZ": "UTC",
        }
    )
    completed = subprocess.run(
        [str(executable), "-b", deck.name],
        cwd=target,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
    )
    log = target / "ngspice.log"
    log.write_text(completed.stdout, encoding="utf-8")
    failures: list[str] = []
    values: dict[str, float] = {}
    if completed.returncode != 0:
        failures.append(f"ngspice_return_code:{completed.returncode}")
    try:
        values = pvt.parse_measures(completed.stdout)
    except pvt.IhpPvtError as exc:
        failures.append(f"measure_parse:{exc}")
    all_warnings = sorted(set(pvt.WARNING_RE.findall(completed.stdout)))
    expected_warnings = sorted(set(all_warnings) & pvt.EXPECTED_BENIGN_WARNINGS)
    unexpected_warnings = sorted(set(all_warnings) - pvt.EXPECTED_BENIGN_WARNINGS)
    simulator_errors = [
        line.strip()
        for line in completed.stdout.splitlines()
        if re.match(r"^(Error|Fatal|ERROR|FATAL)(:|\s)", line.strip())
    ]
    if simulator_errors:
        failures.extend(f"simulator_error:{line}" for line in simulator_errors)
    if values:
        failures.extend(
            pvt.evaluate(case, values, unexpected_warnings, pvt_contract)
        )
    if len(unexpected_warnings) > contract_warning_limit(pvt_contract):
        failures.append("unexpected_warning_limit_exceeded")

    baseline_values = baseline["measures_si"]
    measure_deltas = (
        {name: values[name] - baseline_values[name] for name in MEASURE_NAMES}
        if values
        else {}
    )
    metrics = (
        {
            "discharge_delay_ns": values["discharge_delay"] * 1e9,
            "inactive_leakage_ua": values["inactive_leakage"] * 1e6,
            "read_energy_fj": values["read_energy"] * 1e15,
            "read_margin_fraction_vdd": values["read_margin"] / case["vdd_v"],
        }
        if values
        else None
    )
    baseline_metrics = {
        "discharge_delay_ns": baseline_values["discharge_delay"] * 1e9,
        "inactive_leakage_ua": baseline_values["inactive_leakage"] * 1e6,
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
        "failures": sorted(set(failures)),
        "measure_deltas_vs_capacitance_only_si": measure_deltas,
        "measures_si": values,
        "metric_deltas_vs_capacitance_only": metric_deltas,
        "metrics": metrics,
        "ngspice_log_sha256": sha256_file(log),
        "status": "pass" if not failures else "fail",
        "style_id": style["id"],
        "unexpected_warnings": unexpected_warnings,
    }


def contract_warning_limit(pvt_contract: dict[str, Any]) -> int:
    value = pvt_contract.get("acceptance", {}).get("unexpected_warnings_max")
    if value != 0:
        raise IhpResistanceError("upstream IHP PVT warning policy is not zero")
    return int(value)


def extremum(
    cases: list[dict[str, Any]], metric: str, maximum: bool
) -> dict[str, Any]:
    usable = [case for case in cases if case["metrics"] is not None]
    if not usable:
        raise IhpResistanceError(f"no usable electrical cases for {metric}")
    selected = (max if maximum else min)(
        usable, key=lambda case: case["metrics"][metric]
    )
    return {
        "case_id": selected["case_id"],
        "style_id": selected["style_id"],
        "value": selected["metrics"][metric],
    }


def nominal_case(cases: list[dict[str, Any]], style_id: str) -> dict[str, Any]:
    matches = [
        case
        for case in cases
        if case["style_id"] == style_id
        and case["process_corner"] == "tt"
        and case["vdd_v"] == 1.2
        and case["temperature_c"] == 27.0
        and case["output_load_ff"] == 20.0
    ]
    if len(matches) != 1:
        raise IhpResistanceError(
            f"cannot identify nominal IHP electrical case for {style_id}"
        )
    return matches[0]


def archive_extraction_artifacts(
    extractions: list[dict[str, Any]], contract: dict[str, Any]
) -> list[dict[str, Any]]:
    destination = repo_path(contract["reports"]["artifacts"])
    expected = repo_path("results/spice/ihp_sg13g2_resistance/artifacts")
    if destination != expected:
        raise IhpResistanceError(
            f"refusing unexpected IHP RC artifact destination: {destination}"
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix="artifacts.staging.", dir=destination.parent)
    )
    try:
        records: list[dict[str, Any]] = []
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
                target = staging / f"{prefix}{suffix}"
                shutil.copy2(source, target)
                records.append(
                    {
                        "pass": extraction["pass_name"],
                        "path": (
                            Path(contract["reports"]["artifacts"]) / target.name
                        ).as_posix(),
                        "role": role,
                        "sha256": sha256_file(target),
                        "size_bytes": target.stat().st_size,
                        "style_id": extraction["style_id"],
                    }
                )
        if len(records) != 50 or len({item["path"] for item in records}) != 50:
            raise IhpResistanceError("IHP RC artifact set is incomplete or duplicated")
        if destination.exists():
            shutil.rmtree(destination)
        staging.replace(destination)
        return sorted(records, key=lambda item: item["path"])
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def markdown(result: dict[str, Any]) -> str:
    summary = result["summary"]
    style_map = {style["id"]: style for style in result["input_model"]["styles"]}
    lines = [
        "# IHP SG13G2 distributed-RC extraction and local PVT campaign",
        "",
        f"**Result:** **{result['status'].upper()}** "
        f"({summary['electrical']['cases_passed']}/"
        f"{summary['electrical']['cases_total']} full-RC electrical cases passed)  ",
        "**Evidence class:** independent public open-PDK distributed-RC extraction and simulation of the archived local demonstration slice; not silicon  ",
        f"**Physical input:** `{result['upstream']['physical']['sha256']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}` / "
        f"`{result['toolchain']['magic']['commit']}`  ",
        "**Simulator:** pinned ngspice 43 with four hash-verified IHP OSDI modules",
        "",
        "## Extracted styles and electrical effect",
        "",
        "Every style has 10 MOS instances, 41 explicit resistor elements, and 68",
        "capacitors. The resistor sum is only an extraction diagnostic; it is not",
        "an end-to-end or equivalent network resistance.",
        "",
        "| IHP public RC style | Sum of R elements (ohm, diagnostic) | Total C (fF) | Nominal TT delay (ns) | Nominal delay vs C-only | Worst delay over 33 cases (ns) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    by_style = summary["electrical"]["by_style"]
    extraction_by_style = summary["extraction"]["by_style"]
    for style in result["input_model"]["styles"]:
        style_id = style["id"]
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
            "This is a full-RC-versus-capacitance-only comparison. Network",
            "subdivision redistributes capacitance as well as adding resistors, so the",
            "difference is not reported as a pure resistance penalty.",
            "",
            "## Extraction controls",
            "",
            "- Magic's integrated `extract do extresist` path runs exactly once per style and pass.",
            "- Network threshold, delay threshold, and individual-resistor pruning threshold are zero; simplification is off.",
            "- Each style is extracted twice in a fresh directory. The exact multisets of ports, MOS terminals/parameters, resistor edges/values, and capacitor edges/values must match.",
            f"- All {summary['extraction']['styles_total']} style replays pass semantic equality.",
            f"- {result['input_model']['extraction']['style_total_net_note']}",
            "- Every extraction reports zero geometry/tool feedback errors.",
            "- The programmed row terminal belongs only to the `BL_PRESENT` resistor component. The absent row terminal belongs to `ROM_DRAIN_ABSENT`, not either physical bitline, and the two program-state components are disjoint.",
            "- All six extracted non-ground NMOS body nodes retain positive-resistance paths to `VGND`; substrate/body resistance is not discarded.",
            "",
            "## Electrical sweep",
            "",
            "Each primary full-RC netlist is simulated over the same 33 SS/TT/FF,",
            "1.08/1.20/1.32-V, -40/27/125-C, and 5/20/80-fF points used by",
            "the capacitance-only IHP campaign. The official PSP103 models and exact",
            "pinned OSDI modules are used in every case.",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(
        f"- Establishes: {item}." for item in result["claim_boundary"]["establishes"]
    )
    lines.append("")
    lines.extend(
        f"- Does not establish: {item}."
        for item in result["claim_boundary"]["forbidden_inferences"]
    )
    lines.extend(
        [
            "",
            "The 32.5 × 11.5-µm layout is a deliberately roomy demonstration slice.",
            "No IHP or SKY130 RC value may be feature-size-scaled into N7/N4, a",
            "whole array, a wafer, or a GPU speedup.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_ihp_resistance.py",
            "```",
            "",
            "The JSON result records exact primary/replay artifacts, PDK and tool",
            "identities, per-case measures, baseline deltas, and SHA-256 values.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--ngspice", type=Path)
    parser.add_argument("--osdi-root", type=Path)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    contract = strict_json(CONTRACT_PATH)
    pvt_contract, cases = validate_contract(contract)
    if args.validate_only:
        print(
            "PASS: IHP resistance contract; five public RC styles, semantic "
            f"replay, {len(cases)} electrical cases per style"
        )
        return 0

    workers = args.workers or contract["simulation"]["default_workers"]
    if not 1 <= workers <= 16:
        raise IhpResistanceError("workers must be between 1 and 16")
    lock = strict_json(repo_path(contract["inputs"]["pdk_lock"]))
    pdk_root, variant = physical.locate_pdk(args.pdk_root)
    magic, netgen = physical.common.locate_tools(
        lock, args.tool_root, args.magic, None
    )
    pdk_identity = physical.verify_pdk(pdk_root, variant, lock)
    physical_tools = physical.common.tool_identities(magic, netgen, lock)
    upstream, baselines = verify_upstream(contract, lock)

    ngspice = pvt.locate_tool(
        args.ngspice,
        "OPENTALLAS_IHP_NGSPICE",
        Path.home()
        / ".local"
        / "opentallas-tools"
        / "ngspice-43-osdi"
        / "bin"
        / "ngspice",
        "pinned ngspice 43 OSDI simulator",
    )
    ngspice_identity = pvt.verify_tool(
        ngspice, lock["tools"]["ngspice"], "ngspice-43"
    )
    osdi_root = (
        args.osdi_root.expanduser().resolve()
        if args.osdi_root is not None
        else Path.home()
        / ".local"
        / "opentallas-tools"
        / "ihp-sg13g2-v0.3.0-osdi"
    )
    osdi_identity = pvt.verify_osdi(osdi_root, lock)
    corner_library, model_files = model_dependencies(pdk_root)

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
            pdk_root=pdk_root,
            variant=variant,
            magic=magic,
        )
        print(f"[RC] extracting {style['id']} replay", flush=True)
        replay = run_magic_extraction(
            style=style,
            pass_name="replay",
            contract=contract,
            pdk_root=pdk_root,
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
            raise IhpResistanceError(
                f"semantic IHP extraction replay failed for {style['id']}"
            )
        primary_by_style[style["id"]] = primary
        replay_checks[style["id"]] = replay_check
        extraction_runs.extend([primary, replay])

    template_path = repo_path(contract["inputs"]["testbench_template"])
    template = template_path.read_text(encoding="utf-8")
    spice_init = repo_path(contract["inputs"]["spice_init"])
    order = ("process_corner", "vdd_v", "temperature_c", "output_load_ff")
    jobs: list[
        tuple[dict[str, str], dict[str, Any], Path, dict[str, Any]]
    ] = []
    for style in contract["extraction"]["styles"]:
        rc_pex = primary_by_style[style["id"]]["artifact_paths"]["rc_pex"]
        for case in cases:
            key = tuple(case[name] for name in order)
            baseline = baselines.get(key)
            if baseline is None:
                raise IhpResistanceError(
                    f"missing IHP capacitance-only baseline for {key}"
                )
            jobs.append((style, case, rc_pex, baseline))

    electrical: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {
            executor.submit(
                run_electrical_case,
                style=style,
                case=case,
                rc_pex=rc_pex,
                template=template,
                corner_library=corner_library,
                spice_init=spice_init,
                pvt_contract=pvt_contract,
                baseline=baseline,
                executable=ngspice,
                pdk_root=pdk_root,
                osdi_root=osdi_root,
                timeout_seconds=contract["simulation"]["case_timeout_seconds"],
            ): (style["id"], case["case_id"])
            for style, case, rc_pex, baseline in jobs
        }
        for completed_count, future in enumerate(as_completed(pending), start=1):
            result = future.result()
            electrical.append(result)
            if (
                completed_count == 1
                or completed_count % 15 == 0
                or completed_count == len(jobs)
            ):
                print(
                    f"[PVT {completed_count:03d}/{len(jobs)}] "
                    f"{result['style_id']}/{result['case_id']} {result['status']}",
                    flush=True,
                )
    style_order = {
        style["id"]: index
        for index, style in enumerate(contract["extraction"]["styles"])
    }
    electrical.sort(
        key=lambda case: (style_order[case["style_id"]], case["case_id"])
    )
    failures = [case for case in electrical if case["status"] != "pass"]
    warning_counts = Counter(
        warning for case in electrical for warning in case["unexpected_warnings"]
    )
    expected_total = len(contract["extraction"]["styles"]) * len(cases)
    status = (
        "pass"
        if len(failures)
        <= contract["acceptance"]["electrical_cases_failed_max"]
        and len(electrical) == expected_total
        and not warning_counts
        else "fail"
    )

    extraction_summary = {
        "by_style": {
            style["id"]: {
                "magic_style": style["magic_style"],
                "metrics": primary_by_style[style["id"]]["metrics"],
                "replay": replay_checks[style["id"]],
                "res_ext_counts": primary_by_style[style["id"]][
                    "res_ext_counts"
                ],
                "magic": primary_by_style[style["id"]]["magic"],
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
        subset = [
            case for case in electrical if case["style_id"] == style["id"]
        ]
        electrical_by_style[style["id"]] = {
            "cases_failed": sum(case["status"] != "pass" for case in subset),
            "cases_passed": sum(case["status"] == "pass" for case in subset),
            "cases_total": len(subset),
            "max_discharge_delay_ns": extremum(
                subset, "discharge_delay_ns", True
            ),
            "max_inactive_leakage_ua": extremum(
                subset, "inactive_leakage_ua", True
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
            "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(CONTRACT_PATH),
        },
        "dependencies": {
            "extractor_script": {
                "path": contract["inputs"]["extractor_script"],
                "sha256": sha256_file(
                    repo_path(contract["inputs"]["extractor_script"])
                ),
            },
            "extracted_pvt_runner": {
                "path": Path(pvt.__file__).resolve().relative_to(ROOT).as_posix(),
                "sha256": sha256_file(Path(pvt.__file__).resolve()),
            },
            "physical_runner": {
                "path": Path(physical.__file__)
                .resolve()
                .relative_to(ROOT)
                .as_posix(),
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
            "corner_sections": {
                corner: f"mos_{corner}" for corner in ("ss", "tt", "ff")
            },
            "model_files": model_files,
            "model_scope": "official IHP SG13G2 low-voltage PSP103 corner library and dependencies",
        },
        "pdk_lock": {
            "path": contract["inputs"]["pdk_lock"],
            "sha256": sha256_file(repo_path(contract["inputs"]["pdk_lock"])),
        },
        "runner": {
            "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "sha256": sha256_file(Path(__file__).resolve()),
            "workers": workers,
        },
        "schema_version": 1,
        "spice_init": {
            "path": contract["inputs"]["spice_init"],
            "sha256": sha256_file(spice_init),
        },
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
            "ngspice": ngspice_identity,
            "osdi_modules": osdi_identity,
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
        f"{electrical_summary['cases_total']} full-RC cases passed; semantic "
        f"replay {extraction_summary['styles_passed_semantic_replay']}/"
        f"{extraction_summary['styles_total']}",
        flush=True,
    )
    if failures:
        for case in failures:
            print(
                f"  {case['style_id']}/{case['case_id']}: {case['failures']}",
                flush=True,
            )
    return 0 if status == "pass" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (
        IhpResistanceError,
        physical.IhpPhysicalError,
        physical.common.PhysicalExperimentError,
        pvt.IhpPvtError,
        subprocess.TimeoutExpired,
    ) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
