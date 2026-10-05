#!/usr/bin/env python3
"""Collect a bounded, source-hashed IHP SG13G2 Qwen RTL physical campaign.

This collector qualifies only the public-PDK RTL-to-GDS feasibility boundary.
It deliberately keeps formal equivalence, activity-derived power/IR, thermal,
foundry DRC/LVS, package, reliability, yield, and silicon gates open.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Sequence

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_physical_campaign.v1"
PLATFORM = "ihp-sg13g2"
DESIGN = "opentallas_qwen_add_sram"
TOP = "ot_ta_add_bf16_sram_engine"
DEFAULT_VARIANT = "route-v6"
DEFAULT_CONFIG = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/config.mk"
DEFAULT_SDC = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/constraint.sdc"
DEFAULT_LOCK = ROOT / "physical/ihp_sg13g2_qwen_rtl/add_sram/toolchain.lock.json"
SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_physical_campaign_v1.schema.json"
)
RUNNER = Path(__file__).resolve()

RTL_SOURCES = (
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_bf16_add_rne.sv",
    ROOT / "rtl/ot_ta_add_bf16_executor.sv",
    ROOT / "rtl/ot_ta_add_bf16_sram_engine.sv",
)

CORNER_LIBRARIES = {
    "slow": "lib/sg13g2_stdcell_slow_1p08V_125C.lib",
    "typ": "lib/sg13g2_stdcell_typ_1p20V_25C.lib",
    "fast": "lib/sg13g2_stdcell_fast_1p32V_m40C.lib",
}

EXPECTED_PORTS = {
    "abi_major": ("input", 16),
    "abi_minor": ("input", 16),
    "clk": ("input", 1),
    "cmd_ready": ("output", 1),
    "cmd_valid": ("input", 1),
    "command_record": ("input", 512),
    "done_command_index": ("output", 32),
    "done_element_count": ("output", 32),
    "done_error": ("output", 8),
    "done_ready": ("input", 1),
    "done_saturation_count": ("output", 32),
    "done_sram_read_count": ("output", 32),
    "done_sram_write_count": ("output", 32),
    "done_valid": ("output", 1),
    "expected_command_index": ("input", 32),
    "rst_n": ("input", 1),
    "sram_read_address": ("output", 64),
    "sram_read_ready": ("input", 1),
    "sram_read_valid": ("output", 1),
    "sram_response_data": ("input", 16),
    "sram_response_ready": ("output", 1),
    "sram_response_valid": ("input", 1),
    "sram_write_address": ("output", 64),
    "sram_write_byte_enable": ("output", 2),
    "sram_write_data": ("output", 16),
    "sram_write_ready": ("input", 1),
    "sram_write_valid": ("output", 1),
}

ALLOWED_ORFS_DUPLICATES = {
    "finish__design__instance__area": 2,
    "finish__design__instance__count": 2,
    "finish__power__internal__total": 3,
    "finish__power__leakage__total": 3,
    "finish__power__switching__total": 3,
    "finish__power__total": 3,
}

SELECTED_METRICS = (
    "finish__clock__skew__hold",
    "finish__clock__skew__setup",
    "finish__design__core__area",
    "finish__design__die__area",
    "finish__design__instance__area__stdcell",
    "finish__design__instance__count__macros",
    "finish__design__instance__count__stdcell",
    "finish__design__instance__utilization__stdcell",
    "finish__design__io",
    "finish__design__nets",
    "finish__flow__errors__count",
    "finish__flow__warnings__count",
    "finish__timing__drv__hold_violation_count",
    "finish__timing__drv__max_cap",
    "finish__timing__drv__max_fanout",
    "finish__timing__drv__max_slew",
    "finish__timing__drv__setup_violation_count",
    "finish__timing__fmax__clock:core_clock",
    "finish__timing__hold__tns",
    "finish__timing__hold__ws",
    "finish__timing__setup__tns",
    "finish__timing__setup__ws",
)


class CampaignError(RuntimeError):
    """A physical-campaign input or bounded acceptance gate failed."""


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Collect a bounded IHP SG13G2 Qwen RTL physical campaign"
    )
    result.add_argument("--run-root", required=True, type=Path)
    result.add_argument("--variant", default=DEFAULT_VARIANT)
    result.add_argument("--config", default=DEFAULT_CONFIG, type=Path)
    result.add_argument("--sdc", default=DEFAULT_SDC, type=Path)
    result.add_argument("--lock", default=DEFAULT_LOCK, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(8 * 1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise CampaignError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def require_file(path: Path, label: str, *, allow_empty: bool = False) -> Path:
    if not path.is_file():
        raise CampaignError(f"missing {label}: {path}")
    if not allow_empty and path.stat().st_size == 0:
        raise CampaignError(f"empty {label}: {path}")
    return path


def read_text(path: Path, label: str, *, maximum_bytes: int = 16_000_000) -> str:
    require_file(path, label)
    size = path.stat().st_size
    if size > maximum_bytes:
        raise CampaignError(f"oversized {label}: {size} bytes")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CampaignError(f"cannot read {label} {path}: {exc}") from exc


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampaignError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CampaignError(f"{label} must be finite")
    return result


def exact_match(text: str, pattern: str, label: str, cast: Any = str) -> Any:
    matches = re.findall(pattern, text, flags=re.MULTILINE)
    if len(matches) != 1:
        raise CampaignError(f"{label} matched {len(matches)} times, expected one")
    try:
        return cast(matches[0])
    except (TypeError, ValueError) as exc:
        raise CampaignError(f"invalid {label}: {matches[0]!r}") from exc


def artifact(path: Path, run_root: Path) -> dict[str, Any]:
    try:
        relative = path.resolve().relative_to(run_root.resolve())
        name = f"orfs/{relative.as_posix()}"
    except ValueError:
        name = str(path.resolve().relative_to(ROOT.resolve()))
    return {
        "path": name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def validate_variant(variant: str) -> str:
    if re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", variant) is None:
        raise CampaignError(f"invalid ORFS variant {variant!r}")
    return variant


def resolve_run_directories(run_root: Path, variant: str) -> dict[str, Path]:
    variant = validate_variant(variant)
    root = run_root.resolve()
    if not root.is_dir():
        raise CampaignError(f"run root is not a directory: {root}")
    suffix = Path(PLATFORM) / DESIGN / variant
    directories = {
        "logs": root / "logs" / suffix,
        "reports": root / "reports" / suffix,
        "results": root / "results" / suffix,
    }
    for label, path in directories.items():
        if not path.is_dir():
            raise CampaignError(f"missing ORFS {label} directory: {path}")
    return directories


def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("schema") != "opentallas.physical.ihp_sg13g2_toolchain_lock.v1":
        raise CampaignError("unexpected IHP toolchain lock schema")
    container = lock.get("container")
    if not isinstance(container, dict) or set(container) != {
        "image_id",
        "registry_digest",
        "repository",
    }:
        raise CampaignError("toolchain lock container fields are incomplete")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", str(container["image_id"])) is None:
        raise CampaignError("invalid locked container image ID")
    if re.fullmatch(r"sha256:[0-9a-f]{64}", str(container["registry_digest"])) is None:
        raise CampaignError("invalid locked container registry digest")
    if not isinstance(container["repository"], str) or not container["repository"]:
        raise CampaignError("invalid locked container repository")
    platform_root = lock.get("platform_root")
    if not isinstance(platform_root, str) or not platform_root.startswith("/"):
        raise CampaignError("invalid locked platform root")
    files = lock.get("platform_files")
    if not isinstance(files, dict) or set(CORNER_LIBRARIES.values()) - set(files):
        raise CampaignError("locked platform collateral is incomplete")
    for name, digest in files.items():
        if (
            not isinstance(name, str)
            or name.startswith("/")
            or ".." in Path(name).parts
            or re.fullmatch(r"[0-9a-f]{64}", str(digest)) is None
        ):
            raise CampaignError(f"invalid platform lock entry {name!r}")
    tools = lock.get("tools")
    if not isinstance(tools, dict) or set(tools) != {"klayout", "openroad", "yosys"}:
        raise CampaignError("locked tool identities are incomplete")
    for name, identity in tools.items():
        if not isinstance(identity, dict) or set(identity) != {
            "executable",
            "sha256",
            "version",
        }:
            raise CampaignError(f"locked {name} identity is incomplete")
        if (
            not isinstance(identity["executable"], str)
            or not identity["executable"].startswith("/")
            or re.fullmatch(r"[0-9a-f]{64}", str(identity["sha256"])) is None
            or not isinstance(identity["version"], str)
            or not identity["version"]
        ):
            raise CampaignError(f"invalid locked {name} identity")


def container_reference(lock: dict[str, Any]) -> str:
    container = lock["container"]
    return f"{container['repository']}@{container['registry_digest']}"


def run_command(
    command: Sequence[str],
    *,
    input_text: str | None = None,
    timeout_seconds: int = 300,
) -> str:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            input=input_text,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CampaignError(f"command could not complete: {command[0]}: {exc}") from exc
    if completed.returncode != 0:
        tail = "\n".join(completed.stdout.splitlines()[-80:])
        raise CampaignError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{tail}"
        )
    return completed.stdout


def probe_toolchain(lock: dict[str, Any]) -> dict[str, Any]:
    reference = container_reference(lock)
    inspected = run_command(
        ["docker", "image", "inspect", reference, "--format", "{{.Id}}"]
    ).strip()
    if inspected != lock["container"]["image_id"]:
        raise CampaignError(
            f"container image ID {inspected}, expected {lock['container']['image_id']}"
        )

    tools: dict[str, dict[str, str]] = {}
    version_arguments = {
        "openroad": ["-version"],
        "yosys": ["-V"],
        "klayout": ["-v"],
    }
    for name, identity in sorted(lock["tools"].items()):
        output = run_command(
            [
                "docker",
                "run",
                "--rm",
                reference,
                identity["executable"],
                *version_arguments[name],
            ]
        )
        first_line = next((line.strip() for line in output.splitlines() if line.strip()), "")
        if identity["version"] not in first_line:
            raise CampaignError(
                f"{name} version {first_line!r}, expected {identity['version']!r}"
            )
        tools[name] = {
            "executable": identity["executable"],
            "sha256": identity["sha256"],
            "version": first_line,
        }

    paths = [identity["executable"] for identity in lock["tools"].values()]
    paths.extend(
        f"{lock['platform_root']}/{name}" for name in lock["platform_files"]
    )
    hash_output = run_command(
        ["docker", "run", "--rm", reference, "sha256sum", *paths],
        timeout_seconds=600,
    )
    actual: dict[str, str] = {}
    for line in hash_output.splitlines():
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            actual[fields[1]] = fields[0]
    expected = {
        **{
            identity["executable"]: identity["sha256"]
            for identity in lock["tools"].values()
        },
        **{
            f"{lock['platform_root']}/{name}": digest
            for name, digest in lock["platform_files"].items()
        },
    }
    mismatches = {
        path: {"actual": actual.get(path), "expected": digest}
        for path, digest in expected.items()
        if actual.get(path) != digest
    }
    if mismatches:
        raise CampaignError(f"toolchain/collateral hash mismatch: {mismatches}")
    return {
        "container_image_id": inspected,
        "container_reference": reference,
        "platform_collateral_sha256": dict(sorted(lock["platform_files"].items())),
        "status": "pass",
        "tools": tools,
    }


def parse_flat_orfs_metrics(path: Path) -> tuple[dict[str, float], dict[str, int]]:
    text = read_text(path, "ORFS finish metrics")
    try:
        pairs = json.loads(
            text,
            object_pairs_hook=lambda items: items,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CampaignError(f"non-finite ORFS metric {token!r}")
            ),
        )
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise CampaignError(f"malformed ORFS finish metrics: {exc}") from exc
    if not isinstance(pairs, list) or not all(
        isinstance(item, tuple) and len(item) == 2 for item in pairs
    ):
        raise CampaignError("ORFS finish metrics must be one flat JSON object")
    grouped: dict[str, list[Any]] = defaultdict(list)
    for key, value in pairs:
        if not isinstance(key, str) or isinstance(value, (list, dict)):
            raise CampaignError("ORFS finish metrics must contain scalar fields only")
        grouped[key].append(value)
    duplicate_counts = {
        key: len(values) for key, values in grouped.items() if len(values) > 1
    }
    if duplicate_counts != ALLOWED_ORFS_DUPLICATES:
        raise CampaignError(
            "unexpected ORFS metric ambiguity: "
            f"{duplicate_counts}; expected {ALLOWED_ORFS_DUPLICATES}"
        )
    selected: dict[str, float] = {}
    for key in SELECTED_METRICS:
        values = grouped.get(key, [])
        if len(values) != 1:
            raise CampaignError(f"ORFS metric {key!r} occurred {len(values)} times")
        selected[key] = finite_number(values[0], key)
    return selected, duplicate_counts


def parse_synthesis(reports: Path) -> dict[str, Any]:
    check = read_text(reports / "synth_check.txt", "synthesis check")
    matches = re.findall(r"Found and reported (\d+) problems\.", check)
    if matches != ["0"]:
        raise CampaignError(f"synthesis check did not prove zero problems: {matches}")
    stat = read_text(reports / "synth_stat.txt", "synthesis statistics")
    cell_count = exact_match(
        stat,
        r"^\s*(\d+)\s+[0-9.Ee+-]+\s+\d+\s+[0-9.Ee+-]+\s+cells\s*$",
        "synthesized cell count",
        int,
    )
    area = exact_match(
        stat,
        rf"^\s*Chip area for module '\\{TOP}':\s+([0-9.]+)\s*$",
        "synthesized area",
        float,
    )
    sequential_area = exact_match(
        stat,
        r"^\s*of which used for sequential elements:\s+([0-9.]+)",
        "synthesized sequential area",
        float,
    )
    return {
        "area_um2": area,
        "cell_count": cell_count,
        "problems": 0,
        "sequential_area_um2": sequential_area,
    }


def parse_routing(reports: Path, logs: Path) -> dict[str, Any]:
    drc = require_file(reports / "5_route_drc.rpt", "detailed-route DRC report", allow_empty=True)
    if drc.read_bytes() != b"":
        raise CampaignError("detailed-route DRC report is not empty")
    for name in ("drt_antennas.log", "grt_antennas.log"):
        residual = require_file(reports / name, name, allow_empty=True)
        if residual.read_bytes() != b"":
            raise CampaignError(f"residual antenna report is not empty: {name}")
    route = read_text(logs / "5_2_route.log", "detailed-route log")
    route_violations = [int(item) for item in re.findall(r"Number of violations = (\d+)\.", route)]
    wire_lengths = [int(item) for item in re.findall(r"Total wire length = (\d+) um\.", route)]
    vias = [int(item) for item in re.findall(r"Total number of vias = (\d+)\.", route)]
    net_antenna = [int(item) for item in re.findall(r"Found (\d+) net violations\.", route)]
    pin_antenna = [int(item) for item in re.findall(r"Found (\d+) pin violations\.", route)]
    if not all((route_violations, wire_lengths, vias, net_antenna, pin_antenna)):
        raise CampaignError("detailed-route log is missing bounded routing metrics")
    if route_violations[-1] != 0:
        raise CampaignError(f"final detailed-route violations: {route_violations[-1]}")
    if net_antenna[-1] != 0 or pin_antenna[-1] != 0:
        raise CampaignError(
            f"final antenna violations: nets={net_antenna[-1]} pins={pin_antenna[-1]}"
        )
    merge = read_text(logs / "6_1_merge.log", "KLayout merge log")
    for marker in (
        "KLayout 0.30.7",
        "[INFO] All LEF cells have matching GDS/OAS cells",
        "[INFO] No orphan cells in the final layout",
    ):
        if merge.count(marker) != 1:
            raise CampaignError(f"KLayout merge marker count differs for {marker!r}")
    return {
        "antenna_net_violations": 0,
        "antenna_pin_violations": 0,
        "detailed_route_internal_violations": 0,
        "final_vias": vias[-1],
        "final_wire_length_um": wire_lengths[-1],
        "klayout_lef_cells_matched": True,
        "klayout_orphan_cells": 0,
    }


def parse_config_and_constraints(
    config_path: Path, sdc_path: Path, final_sdc: Path
) -> dict[str, Any]:
    config = read_text(config_path, "physical flow config")
    expected_config = {
        "CORE_UTILIZATION": "25",
        "PLACE_DENSITY": "0.55",
        "TNS_END_PERCENT": "100",
        "CTS_BUF_DISTANCE": "60",
        "HOLD_SLACK_MARGIN": "0.10",
        "MAX_ROUTING_LAYER": "Metal5",
        "CORNERS": "slow typ fast",
        "USE_FILL": "1",
        "LEC_CHECK": "0",
    }
    for name, expected in expected_config.items():
        value = exact_match(
            config,
            rf"^export {re.escape(name)}\s*=\s*(.+?)\s*$",
            f"config {name}",
        )
        if value != expected:
            raise CampaignError(f"config {name}={value!r}, expected {expected!r}")

    sdc = read_text(sdc_path, "source timing constraints")
    required_sdc_markers = (
        "create_clock -name $core_clock_name -period $clk_period [get_ports clk]",
        "create_clock -name $io_clock_name -period $clk_period",
        "set_input_delay 1.0 -clock $io_clock_name $data_inputs",
        "set_input_delay 0.0 -clock $io_clock_name [get_ports rst_n]",
        "set_output_delay 1.0 -clock $io_clock_name [all_outputs]",
        "set_false_path -from [get_ports rst_n]",
    )
    for marker in required_sdc_markers:
        if sdc.count(marker) != 1:
            raise CampaignError(f"source SDC marker count differs for {marker!r}")

    serialized = read_text(final_sdc, "serialized final SDC", maximum_bytes=2_000_000)
    serialized_lines = serialized.splitlines()
    input_lines = [line for line in serialized_lines if line.startswith("set_input_delay")]
    output_lines = [line for line in serialized_lines if line.startswith("set_output_delay")]
    input_delays = len(input_lines)
    output_delays = len(output_lines)
    clocks = sum(line.startswith("create_clock") for line in serialized_lines)
    if (input_delays, output_delays, clocks) != (598, 319, 2):
        raise CampaignError(
            "serialized SDC coverage differs: "
            f"inputs={input_delays} outputs={output_delays} clocks={clocks}"
        )
    clock_binding = "-clock [get_clocks {io_clock}]"
    if any(clock_binding not in line for line in (*input_lines, *output_lines)):
        raise CampaignError("serialized SDC lost an io_clock delay association")
    return {
        "clock_names": ["core_clock", "io_clock"],
        "core_clock_period_ns": 20.0,
        "core_clock_uncertainty_ns": 0.2,
        "hold_repair_margin_ns": 0.1,
        "input_delay_ns": 1.0,
        "max_routing_layer": "Metal5",
        "output_delay_ns": 1.0,
        "serialized_input_delay_bits": input_delays,
        "serialized_output_delay_bits": output_delays,
    }


def openroad_tcl(
    run_root: Path, lock: dict[str, Any], script: str, *, timeout_seconds: int = 600
) -> str:
    return run_command(
        [
            "docker",
            "run",
            "--rm",
            "-i",
            "-v",
            f"{run_root.resolve()}:/run:ro",
            container_reference(lock),
            "bash",
            "-lc",
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad -exit",
        ],
        input_text=script,
        timeout_seconds=timeout_seconds,
    )


def timing_paths(variant: str) -> tuple[str, str, str]:
    base = f"/run/results/{PLATFORM}/{DESIGN}/{variant}"
    return f"{base}/6_final.odb", f"{base}/6_final.sdc", f"{base}/6_final.spef"


def parse_corner_audit(output: str, corner: str) -> dict[str, Any]:
    if output.count(f"AUDIT corner {corner}") != 1:
        raise CampaignError(f"missing timing-audit marker for {corner}")
    setup_wns = exact_match(
        output, r"^worst slack max (-?[0-9.]+)$", f"{corner} setup WNS", float
    )
    hold_wns = exact_match(
        output, r"^worst slack min (-?[0-9.]+)$", f"{corner} hold WNS", float
    )
    setup_tns = exact_match(
        output, r"^tns max (-?[0-9.]+)$", f"{corner} setup TNS", float
    )
    hold_tns = exact_match(
        output, r"^tns min (-?[0-9.]+)$", f"{corner} hold TNS", float
    )
    setup_violations = exact_match(
        output,
        r"^AUDIT setup_violations (\d+)$",
        f"{corner} setup violations",
        int,
    )
    hold_violations = exact_match(
        output,
        r"^AUDIT hold_violations (\d+)$",
        f"{corner} hold violations",
        int,
    )
    if (
        setup_wns < 0
        or hold_wns < 0
        or setup_tns < 0
        or hold_tns < 0
        or setup_violations
        or hold_violations
    ):
        raise CampaignError(
            f"{corner} timing failed: setup={setup_wns} hold={hold_wns} "
            f"violations={setup_violations}/{hold_violations}"
        )
    return {
        "hold_tns_ns": hold_tns,
        "hold_violations": hold_violations,
        "hold_wns_ns": hold_wns,
        "log_sha256": sha256_bytes(output.encode("utf-8")),
        "setup_tns_ns": setup_tns,
        "setup_violations": setup_violations,
        "setup_wns_ns": setup_wns,
    }


def run_timing_audit(run_root: Path, variant: str, lock: dict[str, Any]) -> dict[str, Any]:
    odb, sdc, spef = timing_paths(variant)
    per_corner: dict[str, dict[str, Any]] = {}
    for corner, library in CORNER_LIBRARIES.items():
        script = f"""define_corners {corner}
read_liberty -corner {corner} {lock['platform_root']}/{library}
read_db {odb}
read_sdc {sdc}
read_spef -corner {corner} {spef}
puts "AUDIT corner {corner}"
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
report_tns -max -digits 9
report_tns -min -digits 9
puts "AUDIT setup_violations [sta::endpoint_violation_count max]"
puts "AUDIT hold_violations [sta::endpoint_violation_count min]"
"""
        output = openroad_tcl(run_root, lock, script)
        per_corner[corner] = parse_corner_audit(output, corner)

    definitions = "\n".join(
        f"read_liberty -corner {corner} {lock['platform_root']}/{library}"
        for corner, library in CORNER_LIBRARIES.items()
    )
    parasitics = "\n".join(
        f"read_spef -corner {corner} {spef}" for corner in CORNER_LIBRARIES
    )
    coverage_script = f"""define_corners {' '.join(CORNER_LIBRARIES)}
{definitions}
read_db {odb}
read_sdc {sdc}
{parasitics}
puts "AUDIT check_setup_begin"
check_setup -verbose
puts "AUDIT check_setup_end"
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
puts "AUDIT setup_violations [sta::endpoint_violation_count max]"
puts "AUDIT hold_violations [sta::endpoint_violation_count min]"
"""
    coverage = openroad_tcl(run_root, lock, coverage_script)
    marker = re.search(
        r"AUDIT check_setup_begin\s*(.*?)\s*AUDIT check_setup_end",
        coverage,
        flags=re.DOTALL,
    )
    if marker is None:
        raise CampaignError("constraint audit markers are missing or ambiguous")
    diagnostics = [line.strip() for line in marker.group(1).splitlines() if line.strip()]
    if diagnostics:
        raise CampaignError(f"constraint audit diagnostics: {diagnostics}")
    aggregate_setup = exact_match(
        coverage, r"^worst slack max (-?[0-9.]+)$", "aggregate setup WNS", float
    )
    aggregate_hold = exact_match(
        coverage, r"^worst slack min (-?[0-9.]+)$", "aggregate hold WNS", float
    )
    setup_violations = exact_match(
        coverage,
        r"^AUDIT setup_violations (\d+)$",
        "aggregate setup violations",
        int,
    )
    hold_violations = exact_match(
        coverage,
        r"^AUDIT hold_violations (\d+)$",
        "aggregate hold violations",
        int,
    )
    if aggregate_setup < 0 or aggregate_hold < 0 or setup_violations or hold_violations:
        raise CampaignError("aggregate independent timing audit failed")
    return {
        "aggregate_hold_wns_ns": aggregate_hold,
        "aggregate_setup_wns_ns": aggregate_setup,
        "check_setup_diagnostics": diagnostics,
        "constraint_log_sha256": sha256_bytes(coverage.encode("utf-8")),
        "hold_violations": hold_violations,
        "per_corner": per_corner,
        "setup_violations": setup_violations,
        "status": "pass",
        "unconstrained_endpoints": 0,
    }


def yosys_json_ports(data: dict[str, Any], label: str) -> dict[str, tuple[str, int]]:
    modules = data.get("modules")
    if not isinstance(modules, dict) or TOP not in modules:
        raise CampaignError(f"{label} Yosys JSON is missing top module {TOP}")
    ports = modules[TOP].get("ports")
    if not isinstance(ports, dict):
        raise CampaignError(f"{label} Yosys JSON is missing ports")
    result: dict[str, tuple[str, int]] = {}
    for name, port in ports.items():
        if not isinstance(port, dict) or port.get("direction") not in {"input", "output"}:
            raise CampaignError(f"invalid {label} port {name!r}")
        bits = port.get("bits")
        if not isinstance(bits, list) or not bits:
            raise CampaignError(f"invalid {label} port width for {name!r}")
        result[name] = (port["direction"], len(bits))
    return result


def yosys_json_counts(data: dict[str, Any]) -> tuple[int, int, int]:
    modules = data.get("modules", {})
    cell_types: list[str] = []
    process_count = 0
    for module in modules.values():
        cells = module.get("cells", {})
        if isinstance(cells, dict):
            cell_types.extend(
                str(cell.get("type", ""))
                for cell in cells.values()
                if isinstance(cell, dict)
            )
        processes = module.get("processes", {})
        if isinstance(processes, dict):
            process_count += len(processes)
    latch_count = sum("LATCH" in cell.upper() for cell in cell_types)
    return len(cell_types), latch_count, process_count


def run_yosys_json(
    run_root: Path,
    lock: dict[str, Any],
    script: str,
    output_dir: Path,
    filename: str,
) -> tuple[dict[str, Any], str]:
    command = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ROOT.resolve()}:/work:ro",
        "-v",
        f"{run_root.resolve()}:/run:ro",
        "-v",
        f"{output_dir.resolve()}:/audit",
        container_reference(lock),
        lock["tools"]["yosys"]["executable"],
        "-q",
        "-p",
        script,
    ]
    log = run_command(command, timeout_seconds=600)
    path = require_file(output_dir / filename, f"Yosys {filename}")
    try:
        data = load_strict_json(path)
    except ValueError as exc:
        raise CampaignError(f"invalid Yosys JSON {filename}: {exc}") from exc
    return data, log


def run_structural_integrity_audit(
    run_root: Path, variant: str, lock: dict[str, Any]
) -> dict[str, Any]:
    source_args = " ".join(f"/work/{path.relative_to(ROOT)}" for path in RTL_SOURCES)
    mapped = f"/run/results/{PLATFORM}/{DESIGN}/{variant}/1_2_yosys.v"
    typ_lib = f"{lock['platform_root']}/{CORNER_LIBRARIES['typ']}"
    with tempfile.TemporaryDirectory(prefix="opentallas-structural-audit-") as tmp:
        output_dir = Path(tmp)
        source_script = (
            f"read_verilog -sv -DSYNTHESIS {source_args}; "
            f"hierarchy -check -top {TOP}; proc; flatten; opt_clean; "
            "check -assert; write_json /audit/source.json"
        )
        mapped_script = (
            f"read_liberty -lib {typ_lib}; read_verilog {mapped}; "
            f"hierarchy -check -top {TOP}; check -assert; "
            "write_json /audit/mapped.json"
        )
        source_data, source_log = run_yosys_json(
            run_root, lock, source_script, output_dir, "source.json"
        )
        mapped_data, mapped_log = run_yosys_json(
            run_root, lock, mapped_script, output_dir, "mapped.json"
        )
        source_json_hash = sha256_file(output_dir / "source.json")
        mapped_json_hash = sha256_file(output_dir / "mapped.json")

    source_ports = yosys_json_ports(source_data, "source")
    mapped_ports = yosys_json_ports(mapped_data, "mapped")
    if source_ports != EXPECTED_PORTS:
        raise CampaignError(f"source top interface differs: {source_ports}")
    if mapped_ports != EXPECTED_PORTS:
        raise CampaignError(f"mapped top interface differs: {mapped_ports}")
    source_cells, source_latches, source_processes = yosys_json_counts(source_data)
    mapped_cells, mapped_latches, mapped_processes = yosys_json_counts(mapped_data)
    if source_latches or mapped_latches:
        raise CampaignError(
            f"structural audit found latches: source={source_latches} mapped={mapped_latches}"
        )
    if source_processes or mapped_processes:
        raise CampaignError(
            "structural audit left processes: "
            f"source={source_processes} mapped={mapped_processes}"
        )
    return {
        "formal_equivalence": False,
        "interface_bit_count": sum(width for _, width in EXPECTED_PORTS.values()),
        "interface_port_count": len(EXPECTED_PORTS),
        "interfaces_match": True,
        "mapped_cell_count": mapped_cells,
        "mapped_json_sha256": mapped_json_hash,
        "mapped_latch_count": mapped_latches,
        "mapped_process_count": mapped_processes,
        "method": "independent_yosys_source_and_mapped_structural_check",
        "source_cell_count_after_proc_flatten": source_cells,
        "source_json_sha256": source_json_hash,
        "source_latch_count": source_latches,
        "source_process_count": source_processes,
        "status": "pass",
        "tool_log_sha256": sha256_bytes((source_log + mapped_log).encode("utf-8")),
    }


def parse_die_dimensions(def_path: Path) -> tuple[float, float]:
    require_file(def_path, "final DEF")
    try:
        with def_path.open("rt", encoding="utf-8") as handle:
            header = handle.read(64 * 1024)
    except (OSError, UnicodeError) as exc:
        raise CampaignError(f"cannot read final DEF header: {exc}") from exc
    units = exact_match(
        header,
        r"^UNITS DISTANCE MICRONS (\d+) ;$",
        "DEF database units",
        int,
    )
    die = re.findall(
        r"^DIEAREA \( (-?\d+) (-?\d+) \) \( (-?\d+) (-?\d+) \) ;$",
        header,
        flags=re.MULTILINE,
    )
    if len(die) != 1:
        raise CampaignError(f"DEF DIEAREA matched {len(die)} times")
    x0, y0, x1, y1 = (int(item) for item in die[0])
    if x1 <= x0 or y1 <= y0:
        raise CampaignError("DEF die dimensions are not positive")
    return (x1 - x0) / units, (y1 - y0) / units


def validate_finish_metrics(metrics: dict[str, float]) -> None:
    zero_fields = (
        "finish__flow__errors__count",
        "finish__timing__drv__hold_violation_count",
        "finish__timing__drv__max_cap",
        "finish__timing__drv__max_fanout",
        "finish__timing__drv__max_slew",
        "finish__timing__drv__setup_violation_count",
        "finish__timing__hold__tns",
        "finish__timing__setup__tns",
    )
    failures = {name: metrics[name] for name in zero_fields if metrics[name] != 0}
    if metrics["finish__timing__setup__ws"] < 0:
        failures["finish__timing__setup__ws"] = metrics[
            "finish__timing__setup__ws"
        ]
    if metrics["finish__timing__hold__ws"] < 0:
        failures["finish__timing__hold__ws"] = metrics[
            "finish__timing__hold__ws"
        ]
    if metrics["finish__design__instance__count__macros"] != 0:
        failures["finish__design__instance__count__macros"] = metrics[
            "finish__design__instance__count__macros"
        ]
    if failures:
        raise CampaignError(f"post-route acceptance metrics failed: {failures}")


def collect(
    run_root: Path,
    variant: str,
    config_path: Path,
    sdc_path: Path,
    lock_path: Path,
) -> dict[str, Any]:
    variant = validate_variant(variant)
    directories = resolve_run_directories(run_root, variant)
    try:
        lock = load_strict_json(lock_path)
    except ValueError as exc:
        raise CampaignError(f"invalid toolchain lock: {exc}") from exc
    validate_lock(lock)
    toolchain = probe_toolchain(lock)

    results = directories["results"]
    reports = directories["reports"]
    logs = directories["logs"]
    artifact_paths = {
        "final_def": require_file(results / "6_final.def", "final DEF"),
        "final_gds": require_file(results / "6_final.gds", "final GDS"),
        "final_odb": require_file(results / "6_final.odb", "final ODB"),
        "final_sdc": require_file(results / "6_final.sdc", "final SDC"),
        "final_spef": require_file(results / "6_final.spef", "final SPEF"),
        "final_verilog": require_file(results / "6_final.v", "final Verilog"),
        "mapped_verilog": require_file(results / "1_2_yosys.v", "mapped Verilog"),
    }
    evidence_paths = {
        "detailed_route_drc": require_file(
            reports / "5_route_drc.rpt", "detailed-route DRC", allow_empty=True
        ),
        "finish_metrics": require_file(logs / "6_report.json", "finish metrics"),
        "finish_report": require_file(reports / "6_finish.rpt", "finish report"),
        "klayout_merge_log": require_file(logs / "6_1_merge.log", "KLayout merge log"),
        "route_log": require_file(logs / "5_2_route.log", "detailed-route log"),
        "synthesis_check": require_file(reports / "synth_check.txt", "synthesis check"),
        "synthesis_statistics": require_file(
            reports / "synth_stat.txt", "synthesis statistics"
        ),
    }

    metrics, duplicate_counts = parse_flat_orfs_metrics(evidence_paths["finish_metrics"])
    validate_finish_metrics(metrics)
    synthesis = parse_synthesis(reports)
    routing = parse_routing(reports, logs)
    constraints = parse_config_and_constraints(
        config_path, sdc_path, artifact_paths["final_sdc"]
    )
    timing_audit = run_timing_audit(run_root, variant, lock)
    structural = run_structural_integrity_audit(run_root, variant, lock)
    die_width_um, die_height_um = parse_die_dimensions(artifact_paths["final_def"])

    source_paths = (*RTL_SOURCES, config_path, sdc_path, lock_path, SCHEMA_PATH, RUNNER)
    for path in source_paths:
        require_file(path, "campaign source")

    body = {
        "artifacts": {
            name: artifact(path, run_root) for name, path in sorted(artifact_paths.items())
        },
        "claim_boundary": {
            "activity_derived_power": False,
            "complete_layer_execution": False,
            "formal_equivalence": False,
            "foundry_drc": False,
            "gds_generated": True,
            "independent_lvs": False,
            "open_pdk_rtl_to_gds_feasibility": True,
            "package_reliability_yield_or_silicon": False,
            "qualified_sram_macro": False,
            "ta_phy_7_closed": False,
            "ta_rtl_6_closed": False,
        },
        "constraints": {
            **constraints,
            "check_setup_diagnostics": timing_audit["check_setup_diagnostics"],
            "unconstrained_endpoints": timing_audit["unconstrained_endpoints"],
        },
        "design": {
            "design_nickname": DESIGN,
            "die_height_um": die_height_um,
            "die_width_um": die_width_um,
            "macro_count": int(metrics["finish__design__instance__count__macros"]),
            "top": TOP,
        },
        "evidence_sha256": {
            name: sha256_file(path) for name, path in sorted(evidence_paths.items())
        },
        "excluded_metrics": {
            "duplicate_orfs_metric_keys": dict(sorted(duplicate_counts.items())),
            "power_ir_thermal_reason": (
                "ORFS used no execution-derived switching activity; its vectorless "
                "power and dependent IR observations are not qualification evidence"
            ),
        },
        "flow": {
            "corners": list(CORNER_LIBRARIES),
            "floorplan_core_utilization_percent": 25.0,
            "maximum_routing_layer": "Metal5",
            "platform": PLATFORM,
            "target_clock_period_ns": 20.0,
            "variant": variant,
        },
        "metrics": {
            "postroute": {
                "core_area_um2": metrics["finish__design__core__area"],
                "die_area_um2": metrics["finish__design__die__area"],
                "io_count": int(metrics["finish__design__io"]),
                "net_count": int(metrics["finish__design__nets"]),
                "standard_cell_area_um2": metrics[
                    "finish__design__instance__area__stdcell"
                ],
                "standard_cell_count": int(
                    metrics["finish__design__instance__count__stdcell"]
                ),
                "standard_cell_utilization": metrics[
                    "finish__design__instance__utilization__stdcell"
                ],
            },
            "routing": routing,
            "synthesis": synthesis,
            "timing": {
                "aggregate_extracted": {
                    "core_clock_fmax_hz": metrics[
                        "finish__timing__fmax__clock:core_clock"
                    ],
                    "hold_tns_ns": metrics["finish__timing__hold__tns"],
                    "hold_violations": int(
                        metrics["finish__timing__drv__hold_violation_count"]
                    ),
                    "hold_wns_ns": metrics["finish__timing__hold__ws"],
                    "setup_tns_ns": metrics["finish__timing__setup__tns"],
                    "setup_violations": int(
                        metrics["finish__timing__drv__setup_violation_count"]
                    ),
                    "setup_wns_ns": metrics["finish__timing__setup__ws"],
                },
                "independent_audit": timing_audit,
            },
        },
        "open_gates": [
            {
                "gate": "formal_equivalence",
                "reason": (
                    "ORFS Kepler LEC was disabled after its bundled child process "
                    "raised SIGILL on this host; structural checks are not equivalence"
                ),
                "status": "not_run",
            },
            {
                "gate": "activity_power_ir_thermal_performance_per_watt",
                "reason": "no execution-derived switching activity was supplied",
                "status": "not_run",
            },
            {
                "gate": "foundry_drc_lvs",
                "reason": (
                    "OpenROAD internal detailed-route checks and KLayout stream merge "
                    "are not independent foundry signoff"
                ),
                "status": "not_run",
            },
            {
                "gate": "sram_macro_package_reliability_yield_silicon",
                "reason": (
                    "the design uses an external behavioral SRAM boundary and has no "
                    "package, reliability, yield, tapeout, or silicon evidence"
                ),
                "status": "not_run",
            },
        ],
        "qualification": {
            "detailed_route_internal_drc": "pass",
            "extracted_setup_hold": "pass",
            "klayout_stream_merge": "pass",
            "open_pdk_rtl_to_gds_feasibility": "pass",
            "post_synthesis_structural_integrity": "pass",
            "timing_constraint_coverage": "pass",
        },
        "schema": SCHEMA,
        "source_sha256": {
            str(path.resolve().relative_to(ROOT.resolve())): sha256_file(path)
            for path in sorted(source_paths)
        },
        "status": "pass",
        "structural_integrity": structural,
        "toolchain": toolchain,
    }
    return {
        **body,
        "campaign_id": sha256_bytes(canonical_json_bytes(body)),
    }


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    try:
        report = collect(
            arguments.run_root,
            arguments.variant,
            arguments.config,
            arguments.sdc,
            arguments.lock,
        )
        schema = load_strict_json(SCHEMA_PATH)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(report)
    except (CampaignError, ValueError) as exc:
        parser().error(str(exc))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(report))
        handle.flush()
        os.fsync(handle.fileno())
    print(report["campaign_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
