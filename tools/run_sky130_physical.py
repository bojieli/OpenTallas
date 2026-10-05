#!/usr/bin/env python3
"""Run and archive the governed SKY130A physical ROM-slice experiment.

This runner proves only the claims in ``physical_contract.json``.  In
particular, it refuses to create or apply an N7/N4 scaling rule.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spice" / "sky130_rom_slice" / "physical_contract.json"
PDK_VERIFIER = ROOT / "tools" / "verify_sky130_pdk.py"


class PhysicalExperimentError(RuntimeError):
    """A governed input, tool identity, or acceptance gate failed."""


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
        raise PhysicalExperimentError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise PhysicalExperimentError(
            f"duplicate JSON keys in {path}: {sorted(set(duplicates))}"
        )
    return parsed


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def repository_path(value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PhysicalExperimentError(f"repository path must be relative and contained: {value}")
    resolved = (ROOT / relative).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise PhysicalExperimentError(f"repository path escapes the repository: {value}") from exc
    return resolved


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise PhysicalExperimentError("physical contract schema_version must be 1")
    if contract.get("experiment_id") != "sky130_via_rom_physical_v1":
        raise PhysicalExperimentError("unexpected physical experiment_id")
    if lock.get("schema_version") != 1:
        raise PhysicalExperimentError("PDK lock schema_version must be 1")
    if lock.get("pdk", {}).get("variant") != "sky130A":
        raise PhysicalExperimentError("physical experiment requires the locked sky130A variant")
    if repository_path(contract["pdk_lock"]) != repository_path(
        "configs/pdk/sky130_physical_lock.json"
    ):
        raise PhysicalExperimentError("physical contract must use the governed PDK lock")

    inputs = contract.get("inputs", {})
    if set(inputs) != {"generator", "schematic"}:
        raise PhysicalExperimentError("physical contract must name generator and schematic inputs")
    for path in inputs.values():
        if not repository_path(path).is_file():
            raise PhysicalExperimentError(f"missing physical input: {path}")

    ports = contract.get("top_ports")
    if not isinstance(ports, list) or len(ports) != 10 or len(set(ports)) != 10:
        raise PhysicalExperimentError("physical contract must declare ten unique top ports")
    acceptance = contract.get("acceptance", {})
    if acceptance.get("drc_errors_max") != 0:
        raise PhysicalExperimentError("zero DRC errors is a mandatory physical gate")
    if acceptance.get("lvs_final_result") != "Circuits match uniquely.":
        raise PhysicalExperimentError("unique LVS match is a mandatory physical gate")
    if acceptance.get("programming_via1", {}).get("expected_delta") != 1:
        raise PhysicalExperimentError("contract must require exactly one programming-via delta")
    bbox = acceptance.get("bbox_um")
    if (
        not isinstance(bbox, list)
        or len(bbox) != 4
        or any(not isinstance(value, (int, float)) or not math.isfinite(value) for value in bbox)
        or bbox[2] <= bbox[0]
        or bbox[3] <= bbox[1]
    ):
        raise PhysicalExperimentError("invalid physical bounding box")

    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class") != "open_pdk_drc_lvs_and_extraction"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
    ):
        raise PhysicalExperimentError("claim boundary must prohibit target-node scaling")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for required in ("N7", "N4", "GPU speedup", "silicon"):
        if required not in forbidden:
            raise PhysicalExperimentError(f"claim boundary does not cover {required}")

    reports = contract.get("reports", {})
    if set(reports) != {"artifacts", "json", "markdown"}:
        raise PhysicalExperimentError("physical report destinations are incomplete")
    for path in reports.values():
        repository_path(path)


def first_existing(candidates: Iterable[Path], description: str) -> Path:
    checked: list[str] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        checked.append(str(resolved))
        if resolved.exists():
            return resolved
    raise PhysicalExperimentError(f"cannot find {description}; checked {checked}")


def locate_pdk(explicit: Path | None) -> Path:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get("OPENTALLAS_PDK_ROOT")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            ROOT / ".cache" / "pdk-root",
            Path.home() / ".local" / "opentallas-pdk",
        ]
    )
    expanded: list[Path] = []
    for candidate in candidates:
        expanded.append(candidate if candidate.name == "sky130A" else candidate / "sky130A")
    variant = first_existing(expanded, "enabled SKY130A PDK")
    required = (
        variant / "libs.tech" / "magic" / "sky130A.magicrc",
        variant / "libs.tech" / "netgen" / "sky130A_setup.tcl",
    )
    if not all(path.is_file() for path in required):
        raise PhysicalExperimentError(f"incomplete SKY130A physical decks under {variant}")
    return variant


def locate_tools(
    lock: dict[str, Any], explicit_root: Path | None, magic_override: Path | None, netgen_override: Path | None
) -> tuple[Path, Path]:
    roots: list[Path] = []
    if explicit_root is not None:
        roots.append(explicit_root)
    env_root = os.environ.get("OPENTALLAS_TOOL_ROOT")
    if env_root:
        roots.append(Path(env_root))
    roots.extend([ROOT / ".cache" / "physical-tools", Path.home() / ".local" / "opentallas-tools"])

    magic_commit = lock["tools"]["magic"]["commit"]
    netgen_version = lock["tools"]["netgen_lvs"]["version"]
    magic_candidates = [magic_override] if magic_override else [
        root / f"magic-{magic_commit[:7]}" / "bin" / "magic" for root in roots
    ]
    netgen_candidates = [netgen_override] if netgen_override else [
        root / f"netgen-{netgen_version}" / "bin" / "netgen" for root in roots
    ]
    magic = first_existing((path for path in magic_candidates if path is not None), "pinned Magic")
    netgen = first_existing((path for path in netgen_candidates if path is not None), "pinned Netgen")
    if not os.access(magic, os.X_OK) or not os.access(netgen, os.X_OK):
        raise PhysicalExperimentError("physical tools must be executable")
    return magic, netgen


def completed_output(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    if completed.returncode != 0:
        raise PhysicalExperimentError(
            f"identity command failed ({completed.returncode}): {command!r}\n{completed.stdout}"
        )
    return completed.stdout


def tool_identities(magic: Path, netgen: Path, lock: dict[str, Any]) -> dict[str, Any]:
    expected_magic = lock["tools"]["magic"]
    magic_version = completed_output([str(magic), "--version"]).strip()
    magic_commit = completed_output([str(magic), "--commit"]).strip()
    if magic_version != expected_magic["version"] or magic_commit != expected_magic["commit"]:
        raise PhysicalExperimentError(
            f"Magic identity mismatch: version={magic_version!r}, commit={magic_commit!r}"
        )

    expected_netgen = lock["tools"]["netgen_lvs"]
    netgen_output = completed_output([str(netgen), "-batch", "quit"])
    match = re.search(r"(?m)^Netgen\s+([^\s]+)\s+compiled\s+on\s+(.+)$", netgen_output)
    if match is None or match.group(1) != expected_netgen["version"]:
        raise PhysicalExperimentError(f"Netgen version mismatch:\n{netgen_output}")

    def executable_record(path: Path) -> dict[str, Any]:
        return {
            "path": str(path),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }

    magic_record: dict[str, Any] = {
        "commit": magic_commit,
        "version": magic_version,
        "launcher": executable_record(magic),
    }
    magic_engine = magic.parent.parent / "lib" / "magic" / "tcl" / "magicdnull"
    if magic_engine.is_file():
        magic_record["engine"] = executable_record(magic_engine)

    netgen_record: dict[str, Any] = {
        "compiled_on": match.group(2),
        "expected_source_commit": expected_netgen["commit"],
        "source_identity_boundary": (
            "Netgen does not embed its Git commit; the version is checked at runtime, "
            "the exact executable is hashed, and the governed bootstrap pins this commit"
        ),
        "version": match.group(1),
        "launcher": executable_record(netgen),
    }
    netgen_engine = netgen.parent.parent / "lib" / "netgen" / "tcl" / "netgenexec"
    if netgen_engine.is_file():
        netgen_record["engine"] = executable_record(netgen_engine)
    return {"magic": magic_record, "netgen": netgen_record}


def verify_pdk(variant: Path, lock: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        ["python3", str(PDK_VERIFIER), str(variant)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
    )
    if completed.returncode != 0:
        raise PhysicalExperimentError(f"PDK tree verification failed:\n{completed.stdout}")
    try:
        observed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise PhysicalExperimentError(f"invalid PDK verifier output: {completed.stdout}") from exc
    if observed.get("status") != "pass":
        raise PhysicalExperimentError(f"PDK verifier did not pass: {observed}")
    return {
        "family": lock["pdk"]["family"],
        "variant": lock["pdk"]["variant"],
        "release": lock["pdk"]["release"],
        "open_pdks_commit": lock["pdk"]["open_pdks_commit"],
        "root": str(variant),
        "tree": {
            "bytes": observed["bytes"],
            "files": observed["files"],
            "manifest_sha256": observed["manifest_sha256"],
        },
        "magic_deck_sha256": sha256_file(
            variant / "libs.tech" / "magic" / "sky130A.tech"
        ),
        "netgen_setup_sha256": sha256_file(
            variant / "libs.tech" / "netgen" / "sky130A_setup.tcl"
        ),
    }


def run_checked(
    command: list[str], *, cwd: Path, log: Path, env: dict[str, str] | None = None, timeout: int = 120
) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise PhysicalExperimentError(
            f"command failed ({completed.returncode}): {command!r}; see {log}"
        )
    return completed.stdout


def parse_magic(log_text: str, maximum: int) -> dict[str, Any]:
    counts = [int(value) for value in re.findall(r"Total DRC errors found:\s*(\d+)", log_text)]
    if counts != [maximum]:
        raise PhysicalExperimentError(f"expected one DRC count of {maximum}, observed {counts}")
    details = re.findall(r"(?m)^OT_DRC_DETAILS=(.*)$", log_text)
    if details != [""]:
        raise PhysicalExperimentError(f"DRC detail marker is non-empty or missing: {details}")
    fatal_markers = [line for line in log_text.splitlines() if line.startswith("Magic error:")]
    if fatal_markers:
        raise PhysicalExperimentError(f"Magic emitted error diagnostics: {fatal_markers}")
    if "Error parsing" in log_text:
        raise PhysicalExperimentError("Magic failed while parsing the generator")
    return {"errors": counts[0], "status": "pass"}


def spice_statements(path: Path) -> list[list[str]]:
    statements: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("*"):
            continue
        if stripped.startswith("+"):
            if not statements:
                raise PhysicalExperimentError(f"orphan SPICE continuation in {path}")
            statements[-1] += " " + stripped[1:].strip()
        else:
            statements.append(stripped)
    return [statement.split() for statement in statements]


def parse_extracted_topology(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    statements = spice_statements(path)
    top = contract["top_cell"]
    subckts = [tokens for tokens in statements if tokens[0].lower() == ".subckt"]
    if len(subckts) != 1 or subckts[0][1] != top:
        raise PhysicalExperimentError(f"extracted netlist lacks one {top} wrapper")
    ports = subckts[0][2:]
    if ports != contract["top_ports"]:
        raise PhysicalExperimentError(f"extracted port order mismatch: {ports}")

    devices = [tokens for tokens in statements if tokens[0][0].upper() == "X"]
    counts: Counter[str] = Counter()
    nets: set[str] = set(ports)
    parsed_devices: list[dict[str, Any]] = []
    for tokens in devices:
        if len(tokens) < 7:
            raise PhysicalExperimentError(f"unexpected extracted device statement: {tokens}")
        nodes = tokens[1:5]
        model = tokens[5]
        nets.update(nodes)
        counts[model] += 1
        parsed_devices.append({"instance": tokens[0], "model": model, "nodes_dgsb": nodes})
    expected_counts = contract["acceptance"]["device_counts"]
    if dict(sorted(counts.items())) != dict(sorted(expected_counts.items())):
        raise PhysicalExperimentError(
            f"extracted device counts {dict(counts)} != {expected_counts}"
        )
    expected_nets = contract["acceptance"]["net_count"]
    if len(nets) != expected_nets:
        raise PhysicalExperimentError(f"extracted net count {len(nets)} != {expected_nets}")

    def gate_device(gate: str) -> dict[str, Any]:
        selected = [device for device in parsed_devices if device["nodes_dgsb"][1] == gate]
        if len(selected) != 1:
            raise PhysicalExperimentError(f"expected one extracted device gated by {gate}")
        return selected[0]

    present = gate_device("WL_PRESENT")
    absent = gate_device("WL_ABSENT")
    if "BL_PRESENT" not in present["nodes_dgsb"]:
        raise PhysicalExperimentError("programmed row device is not connected to BL_PRESENT")
    if "ROM_DRAIN_ABSENT" not in absent["nodes_dgsb"] or "BL_ABSENT" in absent["nodes_dgsb"]:
        raise PhysicalExperimentError(
            "unprogrammed row device does not preserve a distinct floating ROM drain"
        )
    return {
        "device_count": len(devices),
        "device_counts": dict(sorted(counts.items())),
        "devices": parsed_devices,
        "net_count": len(nets),
        "ports": ports,
        "programmed_row_device": present,
        "unprogrammed_row_device": absent,
    }


def parse_lvs(log_text: str, expected: str) -> dict[str, Any]:
    final = re.findall(r"(?m)^Final result:\s*(?:\n\s*)?([^\n]+)$", log_text)
    if not final:
        # Netgen commonly prints the result on the same line in the dedicated log.
        final = re.findall(r"Final result:\s*([^\n]+)", log_text)
    final = [value.strip() for value in final]
    if final != [expected]:
        raise PhysicalExperimentError(f"LVS final result mismatch: {final}")
    if "Netlists match uniquely." not in log_text:
        raise PhysicalExperimentError("LVS did not report a unique netlist match")
    if "Cell pin lists are equivalent." not in log_text:
        raise PhysicalExperimentError("LVS did not report equivalent pins")
    return {
        "final_result": final[0],
        "netlists_match_uniquely": True,
        "pin_lists_equivalent": True,
        "status": "pass",
    }


def parse_mag(path: Path, contract: dict[str, Any]) -> dict[str, Any]:
    sections: dict[str, list[tuple[int, int, int, int]]] = {}
    current: str | None = None
    fixed_bbox: list[int] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        section = re.fullmatch(r"<<\s+([^>]+?)\s+>>", stripped)
        if section:
            current = section.group(1)
            sections.setdefault(current, [])
            continue
        if stripped.startswith("string FIXED_BBOX "):
            fixed_bbox = [int(value) for value in stripped.split()[2:6]]
        if current is not None and stripped.startswith("rect "):
            values = tuple(int(value) for value in stripped.split()[1:5])
            sections[current].append(values)
    if fixed_bbox is None:
        raise PhysicalExperimentError("layout lacks FIXED_BBOX")

    expected_um = contract["acceptance"]["bbox_um"]
    dx_units = fixed_bbox[2] - fixed_bbox[0]
    dy_units = fixed_bbox[3] - fixed_bbox[1]
    x_scale = (expected_um[2] - expected_um[0]) / dx_units
    y_scale = (expected_um[3] - expected_um[1]) / dy_units
    if not math.isclose(x_scale, y_scale, rel_tol=0, abs_tol=1e-12):
        raise PhysicalExperimentError("layout coordinate scales differ by axis")
    scale_um = x_scale

    def union_area(rectangles: list[tuple[int, int, int, int]]) -> int:
        if not rectangles:
            return 0
        x_values = sorted({x for rectangle in rectangles for x in (rectangle[0], rectangle[2])})
        area = 0
        for left, right in zip(x_values, x_values[1:]):
            if left == right:
                continue
            intervals = sorted(
                (bottom, top)
                for x1, bottom, x2, top in rectangles
                if x1 < right and x2 > left and top > bottom
            )
            if not intervals:
                continue
            covered = 0
            start, stop = intervals[0]
            for next_start, next_stop in intervals[1:]:
                if next_start > stop:
                    covered += stop - start
                    start, stop = next_start, next_stop
                else:
                    stop = max(stop, next_stop)
            covered += stop - start
            area += (right - left) * covered
        return area

    layers: dict[str, Any] = {}
    for layer in ("metal1", "metal2", "metal3", "via1", "via2"):
        rectangles = sections.get(layer, [])
        layers[layer] = {
            "rectangle_count": len(rectangles),
            "union_area_um2": union_area(rectangles) * scale_um * scale_um,
        }

    via1 = sections.get("via1", [])
    midpoint = (fixed_bbox[0] + fixed_bbox[2]) / 2
    present_count = sum(1 for x1, _, x2, _ in via1 if (x1 + x2) / 2 < midpoint)
    absent_count = sum(1 for x1, _, x2, _ in via1 if (x1 + x2) / 2 > midpoint)
    via_gate = contract["acceptance"]["programming_via1"]
    observed = {
        "present_column_count": present_count,
        "absent_column_count": absent_count,
        "delta": present_count - absent_count,
    }
    required = {
        "present_column_count": via_gate["present_column_count"],
        "absent_column_count": via_gate["absent_column_count"],
        "delta": via_gate["expected_delta"],
    }
    if observed != required:
        raise PhysicalExperimentError(f"programming-via geometry {observed} != {required}")

    width_um = dx_units * scale_um
    height_um = dy_units * scale_um
    return {
        "bbox_database_units": fixed_bbox,
        "bbox_um": [expected_um[0], expected_um[1], expected_um[2], expected_um[3]],
        "coordinate_unit_um": scale_um,
        "footprint_area_um2": width_um * height_um,
        "footprint_density_status": "roomy_two_column_test_slice_not_a_ROM_cell_density",
        "layers": layers,
        "programming_via1": observed,
    }


def parse_pex(path: Path) -> dict[str, Any]:
    capacitors: list[dict[str, Any]] = []
    for tokens in spice_statements(path):
        if not tokens[0].upper().startswith("C") or len(tokens) != 4:
            continue
        match = re.fullmatch(r"([-+0-9.eE]+)([fpnumk]?)", tokens[3], re.IGNORECASE)
        if match is None:
            raise PhysicalExperimentError(f"unrecognized extracted capacitance: {tokens}")
        value = float(match.group(1))
        suffix = match.group(2).lower()
        factors_to_ff = {
            "": 1e15,
            "f": 1.0,
            "p": 1e3,
            "n": 1e6,
            "u": 1e9,
            "m": 1e12,
            "k": 1e18,
        }
        value_ff = value * factors_to_ff[suffix]
        if value_ff < 0 or not math.isfinite(value_ff):
            raise PhysicalExperimentError(f"invalid extracted capacitance: {tokens}")
        capacitors.append(
            {"element": tokens[0], "nodes": tokens[1:3], "value_ff": value_ff}
        )
    if not capacitors:
        raise PhysicalExperimentError("PEX netlist contains no extracted capacitance")

    incident: dict[str, float] = {}
    for node in ("BL_PRESENT", "BL_ABSENT", "Q_PRESENT", "Q_ABSENT"):
        incident[node] = sum(
            capacitor["value_ff"] for capacitor in capacitors if node in capacitor["nodes"]
        )
    return {
        "capacitance_element_count": len(capacitors),
        "nonzero_capacitance_element_count": sum(
            capacitor["value_ff"] > 0 for capacitor in capacitors
        ),
        "total_extracted_capacitance_ff": sum(
            capacitor["value_ff"] for capacitor in capacitors
        ),
        "incident_capacitance_ff": incident,
        "resistance_extraction_status": (
            "not_in_this_gate; base Magic extraction supplies device and coupling capacitance, "
            "while detailed extresist wiring is a separate campaign"
        ),
    }


def archive_files(build: Path, contract: dict[str, Any]) -> list[dict[str, Any]]:
    destination = repository_path(contract["reports"]["artifacts"])
    required_names = set(contract["artifacts"])
    required_paths = [build / name for name in sorted(required_names)]
    missing = [path.name for path in required_paths if not path.is_file()]
    if missing:
        raise PhysicalExperimentError(f"missing required physical artifacts: {missing}")

    generated_views = sorted({*build.glob("*.mag"), *build.glob("*.ext")})
    sources = sorted({*required_paths, *generated_views}, key=lambda path: path.name)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix="artifacts.staging.", dir=destination.parent)
    )
    try:
        for source in sources:
            shutil.copy2(source, staging / source.name)
        if destination.exists():
            if destination != repository_path("results/spice/sky130_physical/artifacts"):
                raise PhysicalExperimentError(f"refusing to replace unexpected path {destination}")
            shutil.rmtree(destination)
        staging.replace(destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    records = []
    for path in sorted(destination.iterdir()):
        if path.is_file():
            records.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
    return records


def markdown_report(result: dict[str, Any]) -> str:
    metrics = result["metrics"]
    boundary = result["claim_boundary"]
    caps = metrics["parasitics"]
    lines = [
        "# SKY130A physical via-ROM slice",
        "",
        f"**Result:** **{result['status'].upper()}**  ",
        "**Evidence class:** open-PDK DRC, LVS, and capacitance extraction; not silicon  ",
        f"**PDK:** `{result['pdk']['variant']}` / open_pdks `{result['pdk']['open_pdks_commit']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}` / `{result['toolchain']['magic']['commit']}`  ",
        f"**Netgen:** `{result['toolchain']['netgen']['version']}`",
        "",
        "## Closed gates",
        "",
        f"- Magic DRC: **{result['verification']['drc']['errors']} errors**.",
        f"- Netgen LVS: **{result['verification']['lvs']['final_result']}**",
        f"- Extracted topology: **{metrics['topology']['device_count']} MOS devices, {metrics['topology']['net_count']} nets, {len(metrics['topology']['ports'])} ports**.",
        f"- Programming geometry: present column has {metrics['layout']['programming_via1']['present_column_count']} via1 shapes; absent column has {metrics['layout']['programming_via1']['absent_column_count']}; the controlled delta is exactly one.",
        f"- PEX: **{caps['capacitance_element_count']} capacitance elements** ({caps['nonzero_capacitance_element_count']} nonzero), totaling {caps['total_extracted_capacitance_ff']:.6g} fF across this test slice.",
        "",
        "The programmed row device is physically connected to `BL_PRESENT`. The matched",
        "unprogrammed row device terminates at the distinct floating",
        "`ROM_DRAIN_ABSENT` node and is not connected to `BL_ABSENT`. Netgen compares",
        "all declared top-level pins and reports a unique match.",
        "",
        "## Geometry and parasitics",
        "",
        f"The fixed demonstration footprint is {metrics['layout']['bbox_um'][2]:.3f} × {metrics['layout']['bbox_um'][3]:.3f} µm = {metrics['layout']['footprint_area_um2']:.3f} µm².",
        "It is deliberately roomy and **must not be reported as a ROM cell density**.",
        "",
        "| Net | Incident extracted capacitance |",
        "|---|---:|",
    ]
    for node, value in caps["incident_capacitance_ff"].items():
        lines.append(f"| `{node}` | {value:.6g} fF |")
    lines.extend(
        [
            "",
            "Detailed distributed wire resistance is not closed by this run; that requires",
            "the separate Magic `extresist` campaign. The PEX netlist here contains the",
            "drawn-device and coupling capacitances supplied by the base extractor.",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            "There is no SKY130→N7/N4 feature-size scaling rule. Target-node PPA remains",
            "dependent on a characterized target-foundry ROM macro, extracted target",
            "interconnect and sense path, a reticle test vehicle, and silicon correlation.",
            "",
            "## Reproduction",
            "",
            "```bash",
            "python3 tools/run_sky130_physical.py",
            "```",
            "",
            f"The machine-readable result is `{result['reports']['json']}`. The exact PDK tree,",
            "tool executables, generator, schematic, decks, and every archived output are",
            "identified by SHA-256 in that file.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(contract: dict[str, Any], result: dict[str, Any]) -> None:
    json_path = repository_path(contract["reports"]["json"])
    markdown_path = repository_path(contract["reports"]["markdown"])
    json_path.parent.mkdir(parents=True, exist_ok=True)
    result["reports"] = {
        "artifacts": contract["reports"]["artifacts"],
        "json": contract["reports"]["json"],
        "markdown": contract["reports"]["markdown"],
    }
    json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown_report(result), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdk-root", type=Path, help="PDK root or enabled sky130A variant")
    parser.add_argument("--tool-root", type=Path, help="root containing pinned Magic and Netgen prefixes")
    parser.add_argument("--magic", type=Path, help="explicit Magic executable")
    parser.add_argument("--netgen", type=Path, help="explicit Netgen executable")
    parser.add_argument("--keep-build", action="store_true", help="retain the controlled temporary build")
    parser.add_argument("--validate-only", action="store_true", help="validate contracts without running tools")
    args = parser.parse_args()

    contract = strict_json(CONTRACT_PATH)
    lock_path = repository_path(contract["pdk_lock"])
    lock = strict_json(lock_path)
    validate_contract(contract, lock)
    if args.validate_only:
        print("PASS: SKY130 physical contract and claim boundary")
        return 0

    variant = locate_pdk(args.pdk_root)
    magic, netgen = locate_tools(lock, args.tool_root, args.magic, args.netgen)
    pdk_identity = verify_pdk(variant, lock)
    identities = tool_identities(magic, netgen, lock)

    build_parent = ROOT / "spice" / "build"
    build_parent.mkdir(parents=True, exist_ok=True)
    build = Path(tempfile.mkdtemp(prefix="sky130_rom_slice_physical.", dir=build_parent))
    try:
        input_records: dict[str, Any] = {}
        for name, relative in contract["inputs"].items():
            source = repository_path(relative)
            destination = build / source.name
            shutil.copy2(source, destination)
            input_records[name] = {
                "path": relative,
                "sha256": sha256_file(source),
                "size_bytes": source.stat().st_size,
            }

        magic_log = build / "magic.log"
        environment = os.environ.copy()
        environment.update(
            {
                "LC_ALL": "C",
                "MAGTYPE": "mag",
                "PDK_ROOT": str(variant.parent),
                "TZ": "UTC",
            }
        )
        magic_output = run_checked(
            [
                str(magic),
                "-dnull",
                "-noconsole",
                "-rcfile",
                str(variant / "libs.tech" / "magic" / "sky130A.magicrc"),
                Path(contract["inputs"]["generator"]).name,
            ],
            cwd=build,
            log=magic_log,
            env=environment,
        )
        drc = parse_magic(magic_output, contract["acceptance"]["drc_errors_max"])

        top = contract["top_cell"]
        netgen_stdout = build / "netgen.stdout"
        run_checked(
            [
                str(netgen),
                "-batch",
                "lvs",
                f"{top}.extracted.spice {top}",
                f"{Path(contract['inputs']['schematic']).name} {top}",
                str(variant / "libs.tech" / "netgen" / "sky130A_setup.tcl"),
                "lvs.log",
            ],
            cwd=build,
            log=netgen_stdout,
        )
        lvs_log = build / "lvs.log"
        if not lvs_log.is_file():
            raise PhysicalExperimentError("Netgen did not create the governed LVS log")
        lvs = parse_lvs(
            lvs_log.read_text(encoding="utf-8", errors="replace"),
            contract["acceptance"]["lvs_final_result"],
        )

        topology = parse_extracted_topology(build / f"{top}.extracted.spice", contract)
        layout = parse_mag(build / f"{top}.mag", contract)
        parasitics = parse_pex(build / f"{top}.pex.spice")
        artifacts = archive_files(build, contract)

        result = {
            "artifacts": artifacts,
            "claim_boundary": contract["claim_boundary"],
            "contract": {
                "path": str(CONTRACT_PATH.relative_to(ROOT)),
                "sha256": sha256_file(CONTRACT_PATH),
            },
            "experiment_id": contract["experiment_id"],
            "inputs": input_records,
            "metrics": {
                "layout": layout,
                "parasitics": parasitics,
                "topology": topology,
            },
            "pdk": pdk_identity,
            "pdk_lock": {
                "path": str(lock_path.relative_to(ROOT)),
                "sha256": sha256_file(lock_path),
            },
            "run_utc": datetime.now(timezone.utc).isoformat(),
            "runner": {
                "path": str(Path(__file__).resolve().relative_to(ROOT)),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "schema_version": 1,
            "status": "pass",
            "toolchain": identities,
            "verification": {"drc": drc, "lvs": lvs},
        }
        write_reports(contract, result)
        print(
            "PASS: SKY130A physical ROM slice; "
            f"DRC={drc['errors']} LVS={lvs['final_result']} "
            f"devices={topology['device_count']} caps={parasitics['capacitance_element_count']}"
        )
        print(f"report: {contract['reports']['markdown']}")
        if args.keep_build:
            print(f"build: {build}")
        return 0
    finally:
        if not args.keep_build and build.exists():
            shutil.rmtree(build)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PhysicalExperimentError, subprocess.TimeoutExpired) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
