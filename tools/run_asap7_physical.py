#!/usr/bin/env python3
"""Run a source-hashed, macro-free ASAP7 RTL-to-GDS campaign.

ASAP7 is a predictive academic PDK.  This runner therefore emits predictive
digital evidence only and carries that limitation into every generated report.
It deliberately rejects the FakeRAM macros bundled with the OpenROAD platform.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LOCK = ROOT / "configs" / "pdk" / "asap7_physical_lock.json"
BUILD_ROOT = ROOT / "build" / "asap7_physical"
RESULT_ROOT = ROOT / "results" / "asap7_physical"
RUNNER = Path(__file__).resolve()


class CampaignError(RuntimeError):
    """A governed ASAP7 input or acceptance gate failed."""


def strict_json(path: Path) -> Any:
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError(f"cannot read strict JSON {path}: {exc}") from exc
    if duplicates:
        raise CampaignError(f"duplicate JSON keys in {path}: {sorted(set(duplicates))}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path, *, relative_to: Path = ROOT) -> dict[str, Any]:
    try:
        name = str(path.resolve().relative_to(relative_to.resolve()))
    except ValueError:
        name = str(path)
    return {
        "path": name,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def run_command(
    command: list[str],
    *,
    cwd: Path,
    log: Path | None = None,
    timeout_seconds: int | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_seconds,
    )
    if log is not None:
        log.parent.mkdir(parents=True, exist_ok=True)
        log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join(completed.stdout.splitlines()[-80:])
        raise CampaignError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n{tail}"
        )
    return completed


def finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampaignError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise CampaignError(f"{label} must be finite")
    return result


def validate_lock(lock: dict[str, Any]) -> None:
    if lock.get("schema_version") != 1:
        raise CampaignError("ASAP7 lock schema_version must be 1")
    cases = lock.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CampaignError("ASAP7 lock cases must be a non-empty list")
    names: list[str] = []
    forbidden = tuple(
        str(item).lower()
        for item in lock.get("acceptance", {}).get(
            "forbidden_memory_name_patterns", []
        )
    )
    if not forbidden:
        raise CampaignError("ASAP7 lock must forbid placeholder memory names")
    for case in cases:
        if not isinstance(case, dict):
            raise CampaignError("ASAP7 case must be an object")
        required = {
            "name",
            "description",
            "top",
            "sources",
            "parameters",
            "clock_port",
            "async_reset_ports",
            "clock_period_ns",
            "corner",
            "voltage_v",
            "temperature_c",
            "primary_vt",
            "core_utilization_percent",
            "place_density",
            "equivalence_method",
        }
        missing = required - set(case)
        if missing:
            raise CampaignError(f"ASAP7 case missing fields: {sorted(missing)}")
        name = case["name"]
        if not isinstance(name, str) or re.fullmatch(r"[a-z0-9_]+", name) is None:
            raise CampaignError(f"invalid ASAP7 case name {name!r}")
        names.append(name)
        top = case["top"]
        if not isinstance(top, str) or not top:
            raise CampaignError(f"{name}: invalid top")
        sources = case["sources"]
        if not isinstance(sources, dict) or not sources:
            raise CampaignError(f"{name}: sources must map paths to SHA-256")
        for source, expected in sources.items():
            lowered = source.lower()
            if any(pattern in lowered for pattern in forbidden):
                raise CampaignError(f"{name}: forbidden memory source {source}")
            path = ROOT / source
            if not path.is_file():
                raise CampaignError(f"{name}: missing source {source}")
            if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
                raise CampaignError(f"{name}: invalid source hash for {source}")
        parameters = case["parameters"]
        if not isinstance(parameters, dict) or not parameters:
            raise CampaignError(f"{name}: parameters must be non-empty")
        for key, value in parameters.items():
            if not isinstance(key, str) or not isinstance(value, int) or value < 0:
                raise CampaignError(f"{name}: invalid parameter {key}={value!r}")
        period = finite_number(case["clock_period_ns"], f"{name}.clock_period_ns")
        if period <= 0:
            raise CampaignError(f"{name}: clock period must be positive")
        density = finite_number(case["place_density"], f"{name}.place_density")
        if not 0 < density < 1:
            raise CampaignError(f"{name}: place density must be between zero and one")
        utilization = finite_number(
            case["core_utilization_percent"], f"{name}.core_utilization_percent"
        )
        if not 0 < utilization < 100:
            raise CampaignError(f"{name}: core utilization must be between 0 and 100")
        if case["corner"] not in {"BC", "TC", "WC"}:
            raise CampaignError(f"{name}: unsupported ASAP7 corner")
        if case["primary_vt"] not in {"RVT", "LVT", "SLVT"}:
            raise CampaignError(f"{name}: unsupported ASAP7 Vt")
        if case["equivalence_method"] not in {
            "feedforward_output_register_next_state_cec",
            "state_relation_transition_cec",
        }:
            raise CampaignError(f"{name}: unsupported equivalence method")
        if case["equivalence_method"] == "state_relation_transition_cec":
            aliases = case.get("state_aliases")
            if not isinstance(aliases, dict):
                raise CampaignError(f"{name}: state_aliases must be an object")
            for alias, representative in aliases.items():
                if not all(
                    isinstance(item, str) and item
                    for item in (alias, representative)
                ):
                    raise CampaignError(f"{name}: invalid state alias relation")
                if alias == representative or representative in aliases:
                    raise CampaignError(
                        f"{name}: state aliases must map directly to canonical bits"
                    )
        if "archived_evidence" in case:
            validate_archived_evidence(case)
    if len(names) != len(set(names)):
        raise CampaignError("ASAP7 case names must be unique")
    acceptance = lock.get("acceptance")
    if not isinstance(acceptance, dict):
        raise CampaignError("ASAP7 acceptance must be an object")
    if acceptance.get("required_cases") != names:
        raise CampaignError("acceptance.required_cases must enumerate cases in order")
    toolchain = lock.get("toolchain", {})
    container = toolchain.get("container", {})
    if not all(
        isinstance(container.get(field), str) and container[field]
        for field in ("repository", "amd64_digest", "image_id")
    ):
        raise CampaignError("ASAP7 container lock is incomplete")
    files = toolchain.get("asap7", {}).get("files")
    if not isinstance(files, dict) or not files:
        raise CampaignError("ASAP7 platform file lock is empty")
    for name, expected in files.items():
        if (
            not isinstance(name, str)
            or not isinstance(expected, str)
            or re.fullmatch(r"[0-9a-f]{64}", expected) is None
        ):
            raise CampaignError(f"invalid ASAP7 platform lock entry {name!r}")
    time_unit_ps = toolchain.get("asap7", {}).get("sdc_time_unit_ps")
    if time_unit_ps != 1:
        raise CampaignError("ASAP7 SDC/liberty time unit must be explicitly locked to 1 ps")
    for tool in ("openroad", "yosys", "abc"):
        identity = toolchain.get(tool, {})
        if not all(
            isinstance(identity.get(field), str) and identity[field]
            for field in ("version", "executable", "sha256")
        ):
            raise CampaignError(f"ASAP7 {tool} lock is incomplete")
        if re.fullmatch(r"[0-9a-f]{64}", identity["sha256"]) is None:
            raise CampaignError(f"ASAP7 {tool} hash is invalid")


def validate_archived_evidence(case: dict[str, Any]) -> None:
    """A lock case may declare that its archived record predates its sources.

    The lock always names the sources the campaign must route NOW.  When those
    sources have moved past the archived record and re-qualification has not
    closed, the case carries ``archived_evidence`` instead of a pretend-current
    hash: the record's own source hashes, and why it has not been re-taken.
    """
    name = case["name"]
    archived = case["archived_evidence"]
    if not isinstance(archived, dict):
        raise CampaignError(f"{name}: archived_evidence must be an object")
    if archived.get("status") != "stale":
        raise CampaignError(f"{name}: archived_evidence.status must be 'stale'")
    record_sources = archived.get("record_sources")
    if not isinstance(record_sources, dict) or set(record_sources) != set(case["sources"]):
        raise CampaignError(
            f"{name}: archived_evidence.record_sources must hash the case's sources"
        )
    for source, digest in record_sources.items():
        if not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise CampaignError(f"{name}: invalid archived hash for {source}")
    if record_sources == case["sources"]:
        raise CampaignError(
            f"{name}: archived_evidence declares a record stale that matches the lock"
        )
    for field in ("reason", "requalification"):
        if not isinstance(archived.get(field), str) or not archived[field]:
            raise CampaignError(f"{name}: archived_evidence.{field} is required")


def record_sources(record: dict[str, Any]) -> dict[str, str]:
    return {
        item["path"]: item["sha256"] for item in record.get("source_inventory", [])
    }


def record_is_current(case: dict[str, Any], record: dict[str, Any]) -> bool:
    """A record counts only if it was produced from the sources the lock names."""
    return record_sources(record) == case["sources"]


def case_by_name(lock: dict[str, Any], name: str) -> dict[str, Any]:
    for case in lock["cases"]:
        if case["name"] == name:
            return case
    raise CampaignError(f"unknown ASAP7 case {name!r}")


def verify_source_hashes(case: dict[str, Any]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for source, expected in sorted(case["sources"].items()):
        path = ROOT / source
        actual = sha256_file(path)
        if actual != expected:
            raise CampaignError(
                f"{case['name']}: {source} hash {actual}, expected {expected}"
            )
        inventory.append(artifact(path))
    return inventory


def docker_reference(lock: dict[str, Any]) -> str:
    container = lock["toolchain"]["container"]
    return f"{container['repository']}@{container['amd64_digest']}"


def verify_toolchain(lock: dict[str, Any]) -> dict[str, Any]:
    reference = docker_reference(lock)
    container = lock["toolchain"]["container"]
    inspected = run_command(
        ["docker", "image", "inspect", reference, "--format", "{{.Id}}"],
        cwd=ROOT,
    ).stdout.strip()
    # The classic Docker image store reports .Id as the image CONFIG digest
    # (image_id); the containerd image store reports it as the MANIFEST digest,
    # which for an image pulled by digest is the locked amd64_digest itself.  A
    # manifest digest is content-addressed and names its config, so either one
    # identifies the locked image; anything else is refused.  The executable and
    # ASAP7 collateral hashes below are checked in both cases.
    if inspected == container["image_id"]:
        image_identity = "config_digest"
    elif inspected == container["amd64_digest"]:
        image_identity = "manifest_digest"
    else:
        raise CampaignError(
            f"ASAP7 container image ID {inspected}, expected {container['image_id']} "
            f"(config digest) or {container['amd64_digest']} (manifest digest)"
        )
    asap7 = lock["toolchain"]["asap7"]
    platform_root = asap7["platform_root"]
    locked_paths = sorted(asap7["files"])
    quoted_paths = " ".join(
        f"'{platform_root}/{path}'" for path in locked_paths
    )
    probe = run_command(
        [
            "docker",
            "run",
            "--rm",
            reference,
            "bash",
            "-lc",
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            "openroad -version; yosys -V; "
            f"'{lock['toolchain']['abc']['executable']}' -q 'version'; "
            "sha256sum $(command -v openroad) $(command -v yosys) "
            f"'{lock['toolchain']['abc']['executable']}' "
            + quoted_paths,
        ],
        cwd=ROOT,
    ).stdout
    lines = [line.strip() for line in probe.splitlines() if line.strip()]
    openroad = lock["toolchain"]["openroad"]
    yosys = lock["toolchain"]["yosys"]
    abc = lock["toolchain"]["abc"]
    if not lines or openroad["version"] not in lines[0]:
        raise CampaignError(f"OpenROAD identity mismatch: {lines[:2]}")
    if len(lines) < 2 or lines[1] != yosys["version"]:
        raise CampaignError(f"Yosys identity mismatch: {lines[:3]}")
    if len(lines) < 3 or lines[2] != abc["version"]:
        raise CampaignError(f"ABC identity mismatch: {lines[:4]}")
    hashes: dict[str, str] = {}
    for line in lines[3:]:
        fields = line.split(maxsplit=1)
        if len(fields) == 2 and re.fullmatch(r"[0-9a-f]{64}", fields[0]):
            hashes[fields[1]] = fields[0]
    expected_hashes = {
        openroad["executable"]: openroad["sha256"],
        yosys["executable"]: yosys["sha256"],
        abc["executable"]: abc["sha256"],
        **{
            f"{platform_root}/{name}": value
            for name, value in asap7["files"].items()
        },
    }
    mismatches = {
        name: {"actual": hashes.get(name), "expected": expected}
        for name, expected in expected_hashes.items()
        if hashes.get(name) != expected
    }
    if mismatches:
        raise CampaignError(f"ASAP7 tool/collateral hash mismatches: {mismatches}")
    return {
        "status": "pass",
        "container_reference": reference,
        "container_image_id": inspected,
        "container_image_identity": image_identity,
        "openroad_version": lines[0],
        "yosys_version": lines[1],
        "abc_version": lines[2],
        "verified_sha256": dict(sorted(hashes.items())),
    }


def git_worktree_status() -> list[str]:
    """Return the campaign-entry worktree status used for provenance."""
    return run_command(
        ["git", "status", "--short", "--untracked-files=all"], cwd=ROOT
    ).stdout.splitlines()


def git_state(
    case: dict[str, Any], *, campaign_status: list[str] | None = None
) -> dict[str, Any]:
    head = run_command(["git", "rev-parse", "HEAD"], cwd=ROOT).stdout.strip()
    status = (
        git_worktree_status()
        if campaign_status is None
        else list(campaign_status)
    )
    source_paths = sorted(case["sources"])
    source_diff = run_command(
        ["git", "diff", "--", *source_paths], cwd=ROOT
    ).stdout
    return {
        "head": head,
        "worktree_clean": not status,
        "dirty_paths": status,
        "selected_sources_match_index": not source_diff,
        "selected_sources": source_paths,
    }


def parameter_text(case: dict[str, Any]) -> str:
    return " ".join(
        f"{key} {value}" for key, value in sorted(case["parameters"].items())
    )


def config_text(case: dict[str, Any], lock: dict[str, Any]) -> str:
    constraints = lock["constraints"]
    sources = " ".join(f"/src/{path}" for path in sorted(case["sources"]))
    return "\n".join(
        [
            f"export DESIGN_NICKNAME = opentallas_{case['name']}",
            f"export DESIGN_NAME = {case['top']}",
            "export PLATFORM = asap7",
            f"export VERILOG_FILES = {sources}",
            "export VERILOG_DEFINES = -DSYNTHESIS",
            f"export VERILOG_TOP_PARAMS = {parameter_text(case)}",
            "export SDC_FILE = /work/constraint.sdc",
            f"export CORNER = {case['corner']}",
            f"export ASAP7_USE_VT = {case['primary_vt']}",
            f"export CORE_UTILIZATION = {case['core_utilization_percent']:g}",
            "export CORE_ASPECT_RATIO = 1",
            "export CORE_MARGIN = 2",
            f"export PLACE_DENSITY = {case['place_density']:g}",
            "export PLACE_DENSITY_LB_ADDON = 0.05",
            "export SYNTH_REPEATABLE_BUILD = 1",
            "export SYNTH_HIERARCHICAL = 0",
            "export LEC_CHECK = 0",
            f"export TNS_END_PERCENT = {constraints['tns_end_percent']:g}",
            f"export HOLD_SLACK_MARGIN = {constraints['hold_slack_margin_ns']:g}",
            f"export SETUP_SLACK_MARGIN = {constraints['setup_slack_margin_ns']:g}",
            "export SKIP_REPORT_METRICS = 0",
            "export REPORT_CLOCK_SKEW = 1",
            "",
        ]
    )


def sdc_text(case: dict[str, Any], lock: dict[str, Any]) -> str:
    constraints = lock["constraints"]
    period_ns = finite_number(case["clock_period_ns"], "clock_period_ns")
    time_unit_ps = finite_number(
        lock["toolchain"]["asap7"]["sdc_time_unit_ps"], "sdc_time_unit_ps"
    )
    period = period_ns * 1000.0 / time_unit_ps
    lines = [
        f"set clk_period {period:g}",
        f"create_clock -name core_clk -period $clk_period [get_ports {case['clock_port']}]",
        "set non_clock_inputs [all_inputs -no_clocks]",
        f"set_input_delay [expr $clk_period * {constraints['input_delay_fraction']:g}] -clock core_clk $non_clock_inputs",
        f"set_output_delay [expr $clk_period * {constraints['output_delay_fraction']:g}] -clock core_clk [all_outputs]",
        f"set_load {constraints['output_load_ff']:g} [all_outputs]",
        f"set_max_fanout {constraints['max_fanout']} [current_design]",
    ]
    for reset in case["async_reset_ports"]:
        lines.append(f"set_false_path -from [get_ports {reset}]")
    lines.append("")
    return "\n".join(lines)


def sanitize_mapped_netlist(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    normalized, count = re.subn(
        r"\b(input|output|wire)\s+signed\b", r"\1", text
    )
    path.write_text(normalized, encoding="utf-8")
    return count


def docker_prefix(lock: dict[str, Any], case_dir: Path) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ROOT}:/src:ro",
        "-v",
        f"{case_dir}:/work",
        "-w",
        "/OpenROAD-flow-scripts/flow",
        docker_reference(lock),
        "bash",
        "-lc",
    ]


def docker_shell_command(
    lock: dict[str, Any], case_dir: Path, shell_command: str
) -> list[str]:
    return docker_prefix(lock, case_dir) + [
        "trap 'chmod -R a+rwX /work >/dev/null 2>&1 || true' EXIT; "
        + shell_command
    ]


def make_case_writable(lock: dict[str, Any], case_dir: Path) -> None:
    """Repair files created by older root-running containers in one case only."""
    if not case_dir.is_dir():
        return
    run_command(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{case_dir}:/work",
            docker_reference(lock),
            "chmod",
            "-R",
            "a+rwX",
            "/work",
        ],
        cwd=ROOT,
        timeout_seconds=300,
    )


def make_prefix() -> str:
    return (
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        "make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base "
    )


def liberty_paths(lock: dict[str, Any]) -> list[str]:
    root = lock["toolchain"]["asap7"]["platform_root"]
    return [
        f"{root}/{name}"
        for name in sorted(lock["toolchain"]["asap7"]["files"])
        if "/lib/NLDM/" in f"/{name}" or name.startswith("lib/NLDM/")
    ]


FF_TO_NEXTSTATE = """\
module \\$dff (CLK, D, Q);
    parameter WIDTH = 1;
    parameter CLK_POLARITY = 1'b1;
    input CLK;
    input [WIDTH-1:0] D;
    output [WIDTH-1:0] Q;
    assign Q = D;
endmodule

module \\$_DFF_P_ (C, D, Q);
    input C, D;
    output Q;
    assign Q = D;
endmodule

module \\$_DFF_N_ (C, D, Q);
    input C, D;
    output Q;
    assign Q = D;
endmodule
"""


SEQUENTIAL_CELL_SELECTION = " ".join(
    (
        "t:$dff",
        "t:$adff",
        "t:$adffe",
        "t:$sdff",
        "t:$sdffe",
        "t:$sdffce",
        "t:$dffe",
        "t:$dffsr",
        "t:$dffsre",
        "t:$dlatch",
        "t:$adlatch",
        "t:$dlatchsr",
        "t:$_DFF_*",
        "t:$_DFFE_*",
        "t:$_DFFSR_*",
        "t:$_DFFSRE_*",
        "t:$_SDFF_*",
        "t:$_SDFFE_*",
        "t:$_SDFFCE_*",
        "t:$_DLATCH_*",
        "t:$_DLATCHSR_*",
    )
)


SUPPORTED_NEXTSTATE_FF_SELECTION = " ".join(
    ("t:$dff", "t:$_DFF_P_", "t:$_DFF_N_")
)


COARSE_DFF_TYPE = "$dff"


FINE_TO_COARSE = r"""\
module \$_DFF_P_ (C, D, Q);
    input C, D;
    output Q;
    \$dff #(.WIDTH(1), .CLK_POLARITY(1'b1)) _TECHMAP_REPLACE_ (
        .CLK(C), .D(D), .Q(Q)
    );
endmodule

module \$_DFF_N_ (C, D, Q);
    input C, D;
    output Q;
    \$dff #(.WIDTH(1), .CLK_POLARITY(1'b0)) _TECHMAP_REPLACE_ (
        .CLK(C), .D(D), .Q(Q)
    );
endmodule
"""


def sequential_equivalence_script(
    case: dict[str, Any], lock: dict[str, Any], netlist: str
) -> str:
    sources = " ".join(f"/src/{path}" for path in sorted(case["sources"]))
    top = case["top"]
    chparams = " ".join(
        f"-chparam {key} {value}"
        for key, value in sorted(case["parameters"].items())
    )
    lines = [
        f"read_verilog -sv -DSYNTHESIS {sources}",
        f"hierarchy -check -top {top} {chparams}",
        "proc",
        "memory",
        "flatten",
        "async2sync",
        "opt",
        f"rename {top} gold",
    ]
    lines.extend(
        f"read_liberty -ignore_miss_func -ignore_miss_data_latch {path}"
        for path in liberty_paths(lock)
    )
    lines.extend(
        [
            f"read_verilog {netlist}",
            "proc",
            f"flatten {top}",
            f"async2sync {top}",
            f"opt {top}",
            f"rename {top} gate",
            "equiv_make gold gate equiv",
            "hierarchy -top equiv",
            # Partition each observable bit and stop cones at shared nodes.  The
            # default grouped solve creates one monolithic SAT instance for a
            # wide arithmetic output and does not scale to the 64-multiplier
            # case, while these options preserve the same bit-exact proof goal.
            "equiv_simple -short -nogroup -seq 2",
            "equiv_induct -seq 2",
            "equiv_status -assert",
            "",
        ]
    )
    return "\n".join(lines)


def run_sequential_equivalence(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    *,
    label: str,
    netlist: Path,
) -> dict[str, Any]:
    script = case_dir / f"equivalence_{label}.ys"
    log = case_dir / f"equivalence_{label}.log"
    relative = "/work/" + str(netlist.relative_to(case_dir))
    script.write_text(
        sequential_equivalence_script(case, lock, relative), encoding="utf-8"
    )
    command = docker_shell_command(lock, case_dir,
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        f"yosys -l /work/{log.name} -s /work/{script.name}"
    )
    run_command(command, cwd=ROOT, log=None, timeout_seconds=1800)
    if not log.is_file():
        raise CampaignError(f"{case['name']}: {label} equivalence log missing")
    text = log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"Of those cells\s+([0-9]+) are proven and ([0-9]+) are unproven", text
    )
    if "Equivalence successfully proven!" not in text or not matches:
        raise CampaignError(f"{case['name']}: {label} equivalence did not close")
    proven, unproven = map(int, matches[-1])
    limit_key = (
        "mapped_equivalence_unproven_max"
        if label == "mapped"
        else "postroute_equivalence_unproven_max"
    )
    limit = int(lock["acceptance"][limit_key])
    if unproven > limit:
        raise CampaignError(
            f"{case['name']}: {label} equivalence has {unproven} unproven, limit {limit}"
        )
    return {
        "status": "pass",
        "method": "Yosys sequential equivalence after RTL and mapped-cell normalization",
        "proven_points": proven,
        "unproven_points": unproven,
        "artifact": artifact(log),
        "script": artifact(script),
    }


def nextstate_script(
    case: dict[str, Any],
    lock: dict[str, Any],
    *,
    netlist: str | None,
    state_json: str,
    aiger_binary: str,
    aiger_ascii: str,
) -> str:
    top = case["top"]
    if netlist is None:
        sources = " ".join(f"/src/{path}" for path in sorted(case["sources"]))
        chparams = " ".join(
            f"-chparam {key} {value}"
            for key, value in sorted(case["parameters"].items())
        )
        lines = [
            f"read_verilog -sv -DSYNTHESIS {sources}",
            f"hierarchy -check -top {top} {chparams}",
        ]
    else:
        lines = [
            *(
                f"read_liberty -ignore_miss_func -ignore_miss_data_latch {path}"
                for path in liberty_paths(lock)
            ),
            f"read_verilog {netlist}",
            f"hierarchy -check -top {top}",
        ]
    lines.extend(
        [
            "proc",
            "memory",
            "flatten",
            "async2sync",
            "dffunmap",
            "check -assert -nolatches",
            f"select -assert-any {SUPPORTED_NEXTSTATE_FF_SELECTION}",
            f"tee -q -o {state_json} stat -width -json",
            "techmap -map /work/ff_to_nextstate.v",
            "opt",
            f"select -assert-none {SEQUENTIAL_CELL_SELECTION}",
            "check -assert -nolatches",
            "scc -expect 0",
            "techmap",
            "opt",
            "abc -g AND",
            "clean",
            "aigmap",
            "clean",
            "check -assert -nolatches",
            "scc -expect 0",
            f"hierarchy -check -top {top}",
            f"write_aiger -symbols {aiger_binary}",
            f"write_aiger -ascii -symbols {aiger_ascii}",
            "",
        ]
    )
    return "\n".join(lines)


def state_register_bits(path: Path, top: str) -> int:
    data = strict_json(path)
    modules = data.get("modules", {}) if isinstance(data, dict) else {}
    module = modules.get(f"\\{top}")
    if not isinstance(module, dict):
        raise CampaignError(f"state audit omits top module {top}")
    counts = module.get("num_cells_by_type", {})
    if not isinstance(counts, dict):
        raise CampaignError(f"state audit for {top} omits cell counts")
    bits = 0
    unsupported: list[str] = []
    for cell_type, count in counts.items():
        if not isinstance(cell_type, str) or not isinstance(count, int):
            raise CampaignError(f"invalid state-audit count {cell_type!r}={count!r}")
        match = re.fullmatch(r"\$dff_([0-9]+)", cell_type)
        if match:
            bits += int(match.group(1)) * count
        elif re.fullmatch(r"\$_DFF_[PN]_(?:_1)?", cell_type):
            bits += count
        elif "dff" in cell_type.lower() or "latch" in cell_type.lower():
            unsupported.append(cell_type)
    if unsupported:
        raise CampaignError(f"state audit contains unsupported cells {unsupported}")
    if bits <= 0:
        raise CampaignError(f"state audit for {top} found no register bits")
    return bits


def aiger_interface(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="ascii").splitlines()
    if not lines:
        raise CampaignError(f"empty AIGER artifact {path}")
    header = lines[0].split()
    if len(header) < 6 or header[0] != "aag":
        raise CampaignError(f"unexpected ASCII AIGER header in {path}")
    try:
        inputs, latches, outputs = map(int, header[2:5])
    except ValueError as exc:
        raise CampaignError(f"invalid ASCII AIGER counts in {path}") from exc
    symbols: dict[str, dict[int, str]] = {"i": {}, "o": {}}
    for line in lines:
        match = re.fullmatch(r"([io])([0-9]+) (.+)", line)
        if match:
            symbols[match.group(1)][int(match.group(2))] = match.group(3)
    input_names = [symbols["i"].get(index) for index in range(inputs)]
    output_names = [symbols["o"].get(index) for index in range(outputs)]
    if any(name is None for name in input_names + output_names):
        raise CampaignError(f"incomplete AIGER symbol table in {path}")
    return {
        "inputs": inputs,
        "latches": latches,
        "outputs": outputs,
        "input_names": input_names,
        "output_names": output_names,
    }


def validate_aiger_pair(
    case_name: str,
    label: str,
    interfaces: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if set(interfaces) != {"gold", "gate"}:
        raise CampaignError(f"{case_name}: {label} AIGER pair is incomplete")
    gold = interfaces["gold"]
    gate = interfaces["gate"]
    for side, interface in interfaces.items():
        for kind in ("input_names", "output_names"):
            names = interface.get(kind)
            if not isinstance(names, list) or len(names) != len(set(names)):
                raise CampaignError(
                    f"{case_name}: {label} {side} AIGER has non-unique {kind}"
                )
    count_keys = ("inputs", "latches", "outputs")
    if any(gold.get(key) != gate.get(key) for key in count_keys):
        raise CampaignError(
            f"{case_name}: {label} AIGER interface counts differ: {interfaces}"
        )
    if (
        sorted(gold["input_names"]) != sorted(gate["input_names"])
        or sorted(gold["output_names"]) != sorted(gate["output_names"])
    ):
        raise CampaignError(
            f"{case_name}: {label} AIGER interface names differ: {interfaces}"
        )
    if gold.get("latches") != 0:
        raise CampaignError(f"{case_name}: {label} AIGER still contains latches")
    return {
        "inputs": gold["inputs"],
        "latches": gold["latches"],
        "outputs": gold["outputs"],
        "input_names": sorted(gold["input_names"]),
        "output_names": sorted(gold["output_names"]),
        "matching": "ABC CEC by unique AIGER symbol name; canonical order shown",
        "generated_order_identical": (
            gold["input_names"] == gate["input_names"]
            and gold["output_names"] == gate["output_names"]
        ),
    }


def run_nextstate_equivalence(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    *,
    label: str,
    netlist: Path,
) -> dict[str, Any]:
    ff_map = case_dir / "ff_to_nextstate.v"
    ff_map.write_text(FF_TO_NEXTSTATE, encoding="utf-8")
    relative_netlist = "/work/" + str(netlist.relative_to(case_dir))
    generated: dict[str, Path] = {"ff_to_nextstate.v": ff_map}
    interfaces: dict[str, dict[str, Any]] = {}
    state_bits: dict[str, int] = {}
    for side, candidate in (("gold", None), ("gate", relative_netlist)):
        prefix = f"equivalence_{label}_{side}"
        script = case_dir / f"{prefix}.ys"
        log = case_dir / f"{prefix}.log"
        state = case_dir / f"{prefix}_state.json"
        aiger = case_dir / f"{prefix}.aig"
        aiger_ascii = case_dir / f"{prefix}.aag"
        script.write_text(
            nextstate_script(
                case,
                lock,
                netlist=candidate,
                state_json=f"/work/{state.name}",
                aiger_binary=f"/work/{aiger.name}",
                aiger_ascii=f"/work/{aiger_ascii.name}",
            ),
            encoding="utf-8",
        )
        command = docker_shell_command(lock, case_dir,
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            f"yosys -l /work/{log.name} -s /work/{script.name}"
        )
        run_command(command, cwd=ROOT, timeout_seconds=1800)
        for required in (log, state, aiger, aiger_ascii):
            if not required.is_file():
                raise CampaignError(
                    f"{case['name']}: {label} {side} proof artifact missing: "
                    f"{required.name}"
                )
        state_bits[side] = state_register_bits(state, case["top"])
        interfaces[side] = aiger_interface(aiger_ascii)
        generated.update(
            {
                script.name: script,
                log.name: log,
                state.name: state,
                aiger.name: aiger,
                aiger_ascii.name: aiger_ascii,
            }
        )
    interface = validate_aiger_pair(case["name"], label, interfaces)
    if state_bits["gold"] != interface["outputs"]:
        raise CampaignError(
            f"{case['name']}: {label} RTL has {state_bits['gold']} state bits but "
            f"{interface['outputs']} output bits"
        )
    if state_bits["gate"] > interface["outputs"]:
        raise CampaignError(
            f"{case['name']}: {label} gate has more register bits than outputs: "
            f"{state_bits['gate']} > {interface['outputs']}"
        )
    cec_log = case_dir / f"equivalence_{label}_abc_cec.log"
    abc = lock["toolchain"]["abc"]["executable"]
    cec_command = docker_shell_command(lock, case_dir,
        f"'{abc}' -c 'cec /work/equivalence_{label}_gold.aig "
        f"/work/equivalence_{label}_gate.aig'"
    )
    run_command(cec_command, cwd=ROOT, log=cec_log, timeout_seconds=1800)
    cec_text = cec_log.read_text(encoding="utf-8", errors="replace")
    if "Networks are equivalent." not in cec_text:
        raise CampaignError(f"{case['name']}: {label} ABC CEC did not close")
    generated[cec_log.name] = cec_log
    return {
        "status": "pass",
        "method": (
            "Full sequential equivalence for a one-state-layer, feed-forward "
            "output-register design via audited combinational next-state ABC CEC"
        ),
        "proof_preconditions": {
            "rtl_state_bits_equal_architectural_output_bits": True,
            "mapped_constant_state_elimination_allowed": True,
            "state_feedback_after_ff_collapse_scc_count": 0,
            "gold_state_bits": state_bits["gold"],
            "gate_state_bits": state_bits["gate"],
            "aiger_latches": interface["latches"],
        },
        "aiger_interface": interface,
        "proven_points": interface["outputs"],
        "unproven_points": 0,
        "artifacts": {
            name: artifact(path) for name, path in sorted(generated.items())
        },
    }


def transition_normalize_script(
    case: dict[str, Any],
    lock: dict[str, Any],
    *,
    netlist: str | None,
    pre_state_json: str | None,
    normalized_json: str,
    normalized_il: str,
) -> str:
    """Create a coarse-FF design while preserving deterministic cell names."""
    top = case["top"]
    if netlist is None:
        sources = " ".join(f"/src/{path}" for path in sorted(case["sources"]))
        chparams = " ".join(
            f"-chparam {key} {value}"
            for key, value in sorted(case["parameters"].items())
        )
        lines = [
            f"read_verilog -sv -DSYNTHESIS {sources}",
            f"hierarchy -check -top {top} {chparams}",
            "proc",
            "memory",
            "flatten",
            "opt_clean",
        ]
        if pre_state_json is None:
            raise CampaignError(f"{case['name']}: RTL state-map path is required")
        lines.append(f"write_json {pre_state_json}")
    else:
        lines = [
            *(
                f"read_liberty -ignore_miss_func -ignore_miss_data_latch {path}"
                for path in liberty_paths(lock)
            ),
            f"read_verilog {netlist}",
            f"hierarchy -check -top {top}",
            "proc",
            "memory",
            "flatten",
            "opt_clean",
        ]
    lines.extend(
        [
            "async2sync",
            "dffunmap",
        ]
    )
    if netlist is not None:
        lines.append("techmap -map /work/fine_to_coarse.v -max_iter 1")
    lines.extend(
        [
            "splitnets -ports",
            "opt_clean",
            f"select -assert-any t:{COARSE_DFF_TYPE}",
            f"select -assert-none {SEQUENTIAL_CELL_SELECTION.replace('t:$dff ', '')}",
            "check -assert -nolatches",
            f"write_rtlil {normalized_il}",
            f"write_json {normalized_json}",
            "",
        ]
    )
    return "\n".join(lines)


def json_top(data: Any, top: str, label: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise CampaignError(f"{label}: JSON root is not an object")
    modules = data.get("modules")
    if not isinstance(modules, dict):
        raise CampaignError(f"{label}: JSON omits modules")
    module = modules.get(top) or modules.get(f"\\{top}")
    if not isinstance(module, dict):
        raise CampaignError(f"{label}: JSON omits top module {top}")
    return module


def visible_bit_aliases(module: dict[str, Any]) -> dict[int, list[tuple[str, int, int]]]:
    aliases: dict[int, list[tuple[str, int, int]]] = {}
    for name, net in module.get("netnames", {}).items():
        if not isinstance(name, str) or not isinstance(net, dict):
            continue
        if net.get("hide_name"):
            continue
        bits = net.get("bits")
        if not isinstance(bits, list):
            continue
        for index, bit in enumerate(bits):
            if isinstance(bit, int):
                aliases.setdefault(bit, []).append((name, index, len(bits)))
    return aliases


def bit_state_name(name: str, index: int, width: int) -> str:
    return name if width == 1 else f"{name}[{index}]"


def rtl_state_cells(pre_state: Any, top: str) -> dict[str, list[str]]:
    """Map stable RTL FF cell names to their architectural bit names."""
    module = json_top(pre_state, top, "RTL pre-normalization state map")
    aliases = visible_bit_aliases(module)
    result: dict[str, list[str]] = {}
    state_names: list[str] = []
    for cell_name, cell in module.get("cells", {}).items():
        if not isinstance(cell, dict) or "dff" not in str(cell.get("type", "")).lower():
            continue
        connections = cell.get("connections", {})
        q_bits = connections.get("Q")
        if not isinstance(q_bits, list) or not q_bits:
            raise CampaignError(f"RTL state cell {cell_name} has no Q bits")
        names: list[str] = []
        for bit in q_bits:
            if not isinstance(bit, int):
                raise CampaignError(f"RTL state cell {cell_name} has a constant Q bit")
            candidates = aliases.get(bit, [])
            if len(candidates) != 1:
                raise CampaignError(
                    f"RTL state cell {cell_name} Q bit has {len(candidates)} "
                    "visible logical aliases"
                )
            names.append(bit_state_name(*candidates[0]))
        result[cell_name] = names
        state_names.extend(names)
    if not result:
        raise CampaignError(f"RTL state map for {top} is empty")
    if len(state_names) != len(set(state_names)):
        raise CampaignError(f"RTL state map for {top} contains duplicate bit names")
    return result


def normalized_state_records(
    normalized: Any,
    top: str,
    *,
    rtl_cells: dict[str, list[str]] | None,
) -> dict[str, dict[str, Any]]:
    """Return logical state -> normalized coarse-FF Q/D connection record."""
    module = json_top(normalized, top, "normalized transition design")
    result: dict[str, dict[str, Any]] = {}
    for cell_name, cell in module.get("cells", {}).items():
        if not isinstance(cell, dict) or cell.get("type") != COARSE_DFF_TYPE:
            continue
        connections = cell.get("connections", {})
        q_bits = connections.get("Q")
        d_bits = connections.get("D")
        if (
            not isinstance(q_bits, list)
            or not isinstance(d_bits, list)
            or not q_bits
            or len(q_bits) != len(d_bits)
            or not all(isinstance(bit, int) for bit in q_bits + d_bits)
        ):
            raise CampaignError(f"invalid coarse FF connections for {cell_name}")
        if rtl_cells is not None:
            names = rtl_cells.get(cell_name)
            if names is None or len(names) != len(q_bits):
                raise CampaignError(
                    f"normalized RTL FF {cell_name} does not match its state map"
                )
        else:
            match = re.fullmatch(
                r"\$flatten\\(.+?)\$_(?:DFF|DFFE|DFFSR|DFFSRE|SDFF|SDFFE|SDFFCE).*",
                cell_name,
            )
            if match is None or len(q_bits) != 1:
                raise CampaignError(
                    f"cannot recover logical state name from mapped FF {cell_name}"
                )
            names = [match.group(1)]
            scope_name = cell_name.split(".$auto", maxsplit=1)[0]
            if not scope_name.startswith("$flatten\\"):
                raise CampaignError(f"mapped FF lacks flattened scope: {cell_name}")
            scope_name = scope_name.removeprefix("$flatten\\")
            scope = module.get("cells", {}).get(scope_name)
            physical_module = (
                scope.get("attributes", {}).get("module")
                if isinstance(scope, dict)
                else None
            )
            if not isinstance(physical_module, str) or "QN" not in physical_module.upper():
                raise CampaignError(
                    f"mapped FF {cell_name} has unaudited output polarity "
                    f"from physical module {physical_module!r}"
                )
        for index, name in enumerate(names):
            if name in result:
                raise CampaignError(f"duplicate normalized state bit {name}")
            result[name] = {
                "cell": cell_name,
                "cell_bit": index,
                "q": q_bits[index],
                "d": d_bits[index],
                "logical_state_inverted": rtl_cells is None,
                "physical_module": physical_module if rtl_cells is None else None,
            }
    if not result:
        raise CampaignError(f"normalized transition design for {top} has no state")
    return result


def state_relation_audit(
    case: dict[str, Any],
    gold: dict[str, dict[str, Any]],
    gate: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    aliases = dict(case.get("state_aliases", {}))
    gold_names = set(gold)
    gate_names = set(gate)
    unknown_aliases = (set(aliases) | set(aliases.values())) - gold_names
    if unknown_aliases:
        raise CampaignError(
            f"{case['name']}: state relation names absent from RTL: "
            f"{sorted(unknown_aliases)}"
        )
    canonical_gold = {aliases.get(name, name) for name in gold_names}
    if gate_names != canonical_gold:
        raise CampaignError(
            f"{case['name']}: mapped state differs from the declared relation; "
            f"RTL-only={sorted(canonical_gold - gate_names)}, "
            f"gate-only={sorted(gate_names - canonical_gold)}"
        )
    optimized = gold_names - gate_names
    if optimized != set(aliases):
        raise CampaignError(
            f"{case['name']}: optimized state must be declared exactly; "
            f"observed={sorted(optimized)}, declared={sorted(aliases)}"
        )
    return {
        "status": "pass",
        "rtl_state_bits": len(gold_names),
        "mapped_state_bits": len(gate_names),
        "relation_variables": len(canonical_gold),
        "optimized_alias_bits": len(aliases),
        "aliases": dict(sorted(aliases.items())),
        "reset_establishment_checked_by_transition_cec": True,
        "relation_preservation_checked_by_all_next_state_outputs": True,
    }


def replace_json_bits(value: Any, substitutions: dict[int, int]) -> Any:
    if isinstance(value, int) and not isinstance(value, bool):
        return substitutions.get(value, value)
    if isinstance(value, list):
        return [replace_json_bits(item, substitutions) for item in value]
    if isinstance(value, dict):
        return {
            key: replace_json_bits(item, substitutions)
            for key, item in value.items()
        }
    return value


def maximum_json_bit(value: Any) -> int:
    maximum = 1
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, list):
        for item in value:
            maximum = max(maximum, maximum_json_bit(item))
    elif isinstance(value, dict):
        for item in value.values():
            maximum = max(maximum, maximum_json_bit(item))
    return maximum


def functional_port_contract(
    gold_module: dict[str, Any], gate_module: dict[str, Any]
) -> list[tuple[str, str, int]]:
    contracts: list[dict[str, tuple[str, int]]] = []
    for module in (gold_module, gate_module):
        contract: dict[str, tuple[str, int]] = {}
        for name, port in module.get("ports", {}).items():
            if not isinstance(port, dict):
                raise CampaignError(f"invalid transition port {name}")
            direction = port.get("direction")
            bits = port.get("bits")
            if direction not in {"input", "output"} or not isinstance(bits, list):
                raise CampaignError(f"invalid transition port {name}")
            contract[name] = (direction, len(bits))
        contracts.append(contract)
    if contracts[0] != contracts[1]:
        raise CampaignError("RTL and mapped functional transition ports differ")
    return [
        (name, *contracts[0][name])
        for name in sorted(
            contracts[0], key=lambda item: (contracts[0][item][0] != "input", item)
        )
    ]


def transition_combinational_json(
    normalized: Any,
    top: str,
    records: dict[str, dict[str, Any]],
    *,
    full_state_names: list[str],
    aliases: dict[str, str],
    functional_contract: list[tuple[str, str, int]],
) -> dict[str, Any]:
    """Replace FFs by related current-state PIs and next-state POs."""
    if not isinstance(normalized, dict):
        raise CampaignError("normalized transition JSON is not an object")
    transformed = json.loads(json.dumps(normalized))
    module = json_top(transformed, top, "transition combinationalization")
    canonical_names = sorted({aliases.get(name, name) for name in full_state_names})
    if set(records) != set(canonical_names) and set(records) != set(full_state_names):
        raise CampaignError("transition state record set does not satisfy relation")

    substitutions: dict[int, int] = {}
    for name in full_state_names:
        canonical = aliases.get(name, name)
        if name in records:
            source_q = records[name]["q"]
        else:
            source_q = records[canonical]["q"]
        target_q = records[canonical]["q"]
        substitutions[source_q] = target_q
    transformed = replace_json_bits(transformed, substitutions)
    module = json_top(transformed, top, "transition combinationalization")

    cells = module.get("cells")
    if not isinstance(cells, dict):
        raise CampaignError("transition JSON omits cells")
    module["cells"] = OrderedDict(
        (name, cell)
        for name, cell in cells.items()
        if not isinstance(cell, dict) or cell.get("type") != COARSE_DFF_TYPE
    )
    cells = module["cells"]
    next_bit = maximum_json_bit(transformed) + 1

    def allocate_bit() -> int:
        nonlocal next_bit
        bit = next_bit
        next_bit += 1
        return bit

    def add_inverter(name: str, source: int, target: int) -> None:
        cells[name] = {
            "hide_name": 0,
            "type": "$_NOT_",
            "parameters": {},
            "attributes": {"transition_polarity_bridge": "1"},
            "port_directions": {"A": "input", "Y": "output"},
            "connections": {"A": [source], "Y": [target]},
        }

    old_ports = module.get("ports")
    if not isinstance(old_ports, dict):
        raise CampaignError("transition JSON omits ports")
    ports: OrderedDict[str, dict[str, Any]] = OrderedDict()
    for name, direction, width in functional_contract:
        port = old_ports.get(name)
        if (
            not isinstance(port, dict)
            or port.get("direction") != direction
            or len(port.get("bits", [])) != width
        ):
            raise CampaignError(f"transition functional port mismatch for {name}")
        if direction == "input":
            ports[name] = port
    for name in canonical_names:
        raw_bit = substitutions.get(records[name]["q"], records[name]["q"])
        if records[name]["logical_state_inverted"]:
            bit = allocate_bit()
            add_inverter(f"$state_polarity${name}", bit, raw_bit)
        else:
            bit = raw_bit
        ports[f"state__{name}"] = {"direction": "input", "bits": [bit]}
    for name, direction, _width in functional_contract:
        if direction == "output":
            ports[name] = old_ports[name]
    for name in full_state_names:
        canonical = aliases.get(name, name)
        record = records.get(name, records[canonical])
        raw_bit = substitutions.get(record["d"], record["d"])
        if record["logical_state_inverted"]:
            bit = allocate_bit()
            add_inverter(f"$next_polarity${name}", raw_bit, bit)
        else:
            bit = raw_bit
        ports[f"next__{name}"] = {"direction": "output", "bits": [bit]}
    module["ports"] = ports

    netnames = module.get("netnames")
    if not isinstance(netnames, dict):
        raise CampaignError("transition JSON omits netnames")
    for port_name, port in ports.items():
        if port_name.startswith(("state__", "next__")):
            netnames[port_name] = {
                "hide_name": 0,
                "bits": port["bits"],
                "attributes": {},
            }
    return transformed


def transition_aiger_script(
    top: str, transition_json: str, aiger_binary: str, aiger_ascii: str
) -> str:
    return "\n".join(
        [
            f"read_json {transition_json}",
            f"hierarchy -check -top {top}",
            f"select -assert-none {SEQUENTIAL_CELL_SELECTION}",
            "check -assert -nolatches",
            "scc -expect 0",
            "techmap",
            "opt",
            "abc -g AND",
            "clean",
            "aigmap",
            "clean",
            f"select -assert-none {SEQUENTIAL_CELL_SELECTION}",
            "check -assert -nolatches",
            "scc -expect 0",
            f"hierarchy -check -top {top}",
            f"write_aiger -symbols {aiger_binary}",
            f"write_aiger -ascii -symbols {aiger_ascii}",
            "",
        ]
    )


def run_transition_equivalence(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    *,
    label: str,
    netlist: Path,
) -> dict[str, Any]:
    fine_map = case_dir / "fine_to_coarse.v"
    fine_map.write_text(FINE_TO_COARSE, encoding="utf-8")
    generated: dict[str, Path] = {fine_map.name: fine_map}
    normalized_data: dict[str, Any] = {}
    rtl_cells: dict[str, list[str]] | None = None
    records: dict[str, dict[str, dict[str, Any]]] = {}
    relative_netlist = "/work/" + str(netlist.relative_to(case_dir))
    for side, candidate in (("gold", None), ("gate", relative_netlist)):
        prefix = f"equivalence_{label}_{side}_transition"
        script = case_dir / f"{prefix}_normalize.ys"
        log = case_dir / f"{prefix}_normalize.log"
        pre_state = case_dir / f"{prefix}_pre_state.json"
        normalized_json = case_dir / f"{prefix}_normalized.json"
        normalized_il = case_dir / f"{prefix}_normalized.il"
        script.write_text(
            transition_normalize_script(
                case,
                lock,
                netlist=candidate,
                pre_state_json=(f"/work/{pre_state.name}" if candidate is None else None),
                normalized_json=f"/work/{normalized_json.name}",
                normalized_il=f"/work/{normalized_il.name}",
            ),
            encoding="utf-8",
        )
        command = docker_shell_command(lock, case_dir,
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            f"yosys -l /work/{log.name} -s /work/{script.name}"
        )
        run_command(command, cwd=ROOT, timeout_seconds=1800)
        required = [script, log, normalized_json, normalized_il]
        if candidate is None:
            required.append(pre_state)
        for path in required:
            if not path.is_file():
                raise CampaignError(
                    f"{case['name']}: {label} transition artifact missing: {path.name}"
                )
            generated[path.name] = path
        normalized_data[side] = strict_json(normalized_json)
        if candidate is None:
            rtl_cells = rtl_state_cells(strict_json(pre_state), case["top"])
        records[side] = normalized_state_records(
            normalized_data[side],
            case["top"],
            rtl_cells=rtl_cells if candidate is None else None,
        )
    if rtl_cells is None:
        raise CampaignError(f"{case['name']}: RTL transition state map was not created")

    audit = state_relation_audit(case, records["gold"], records["gate"])
    audit_path = case_dir / f"equivalence_{label}_state_relation.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated[audit_path.name] = audit_path
    gold_module = json_top(normalized_data["gold"], case["top"], "gold transition")
    gate_module = json_top(normalized_data["gate"], case["top"], "gate transition")
    functional_contract = functional_port_contract(gold_module, gate_module)
    full_state_names = sorted(records["gold"])
    aliases = dict(case.get("state_aliases", {}))
    interfaces: dict[str, dict[str, Any]] = {}
    for side in ("gold", "gate"):
        transition_json = case_dir / f"equivalence_{label}_{side}_transition.json"
        transition_json.write_text(
            json.dumps(
                transition_combinational_json(
                    normalized_data[side],
                    case["top"],
                    records[side],
                    full_state_names=full_state_names,
                    aliases=aliases,
                    functional_contract=functional_contract,
                ),
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
        )
        prefix = f"equivalence_{label}_{side}_transition"
        aiger_script = case_dir / f"{prefix}_aiger.ys"
        aiger_log = case_dir / f"{prefix}_aiger.log"
        aiger = case_dir / f"{prefix}.aig"
        aiger_ascii = case_dir / f"{prefix}.aag"
        aiger_script.write_text(
            transition_aiger_script(
                case["top"],
                f"/work/{transition_json.name}",
                f"/work/{aiger.name}",
                f"/work/{aiger_ascii.name}",
            ),
            encoding="utf-8",
        )
        command = docker_shell_command(lock, case_dir,
            "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
            f"yosys -l /work/{aiger_log.name} -s /work/{aiger_script.name}"
        )
        run_command(command, cwd=ROOT, timeout_seconds=1800)
        for path in (transition_json, aiger_script, aiger_log, aiger, aiger_ascii):
            if not path.is_file():
                raise CampaignError(
                    f"{case['name']}: {label} transition proof omits {path.name}"
                )
            generated[path.name] = path
        interfaces[side] = aiger_interface(aiger_ascii)
    interface = validate_aiger_pair(
        case["name"], f"{label} transition", interfaces
    )
    cec_log = case_dir / f"equivalence_{label}_transition_abc_cec.log"
    abc = lock["toolchain"]["abc"]["executable"]
    cec_command = docker_shell_command(lock, case_dir,
        f"'{abc}' -c 'cec /work/equivalence_{label}_gold_transition.aig "
        f"/work/equivalence_{label}_gate_transition.aig'"
    )
    run_command(cec_command, cwd=ROOT, log=cec_log, timeout_seconds=1800)
    cec_text = cec_log.read_text(encoding="utf-8", errors="replace")
    if "Networks are equivalent." not in cec_text:
        raise CampaignError(f"{case['name']}: {label} transition ABC CEC did not close")
    generated[cec_log.name] = cec_log
    return {
        "status": "pass",
        "method": (
            "Exact combinational transition-relation ABC CEC under an audited "
            "state-encoding relation, including reset and relation preservation"
        ),
        "state_relation": audit,
        "aiger_interface": interface,
        "proven_points": interface["outputs"],
        "unproven_points": 0,
        "artifacts": {
            name: artifact(path) for name, path in sorted(generated.items())
        },
    }


def run_equivalence(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    *,
    label: str,
    netlist: Path,
) -> dict[str, Any]:
    if case["equivalence_method"] == "feedforward_output_register_next_state_cec":
        return run_nextstate_equivalence(
            case, lock, case_dir, label=label, netlist=netlist
        )
    return run_transition_equivalence(
        case, lock, case_dir, label=label, netlist=netlist
    )


METRIC_KEYS = {
    "setup_wns_ns": "finish__timing__setup__ws",
    "setup_tns_ns": "finish__timing__setup__tns",
    "setup_violations": "finish__timing__drv__setup_violation_count",
    "hold_wns_ns": "finish__timing__hold__ws",
    "hold_tns_ns": "finish__timing__hold__tns",
    "hold_violations": "finish__timing__drv__hold_violation_count",
    "drc_errors": "detailedroute__route__drc_errors",
    "antenna_violating_nets": "detailedroute__antenna__violating__nets",
    "antenna_violating_pins": "detailedroute__antenna__violating__pins",
    "core_area_um2": "finish__design__core__area",
    "die_area_um2": "finish__design__die__area",
    "standard_cell_area_um2": "finish__design__instance__area__stdcell",
    "utilization_fraction": "finish__design__instance__utilization",
    "wirelength_um": "detailedroute__route__wirelength",
    "vias": "detailedroute__route__vias",
    "fmax_hz": "finish__timing__fmax",
    "clock_count": "constraints__clocks__count",
}


def metadata_number(metadata: dict[str, Any], key: str) -> float:
    if key not in metadata:
        raise CampaignError(f"ORFS metadata omits {key}")
    return finite_number(metadata[key], f"metadata.{key}")


def extract_metrics(
    metadata: dict[str, Any], lock: dict[str, Any], case: dict[str, Any]
) -> dict[str, Any]:
    metrics = {
        name: metadata_number(metadata, key) for name, key in METRIC_KEYS.items()
    }
    timing_ps = {
        name: metrics[name]
        for name in ("setup_wns_ns", "setup_tns_ns", "hold_wns_ns", "hold_tns_ns")
    }
    for name, raw_ps in timing_ps.items():
        metrics[name] = raw_ps / 1000.0
    metrics["raw_timing_ps"] = timing_ps
    expected_period_ps = float(case["clock_period_ns"]) * 1000.0
    details = metadata.get("constraints__clocks__details")
    if not isinstance(details, list) or len(details) != 1:
        raise CampaignError("ORFS metadata omits the single clock-period detail")
    match = re.fullmatch(r"core_clk:\s*([-+0-9.eE]+)", str(details[0]))
    if match is None or not math.isclose(
        float(match.group(1)), expected_period_ps, rel_tol=0.0, abs_tol=1e-6
    ):
        raise CampaignError(
            f"ORFS clock is {details!r}; expected core_clk: {expected_period_ps:g} ps"
        )
    metrics["clock_period_ns"] = float(case["clock_period_ns"])
    metrics["sdc_clock_period_ps"] = expected_period_ps
    flow_errors = {
        key: int(metadata_number(metadata, key))
        for key in sorted(metadata)
        if key.endswith("__flow__errors__count")
    }
    if not flow_errors:
        raise CampaignError("ORFS metadata contains no flow-error counts")
    metrics["flow_error_counts"] = flow_errors
    return metrics


def metric_gate_failures(
    metrics: dict[str, Any], lock: dict[str, Any]
) -> list[str]:
    acceptance = lock["acceptance"]
    failures: list[str] = []
    for name in ("setup_wns_ns", "setup_tns_ns", "hold_wns_ns", "hold_tns_ns"):
        limit = float(acceptance[f"{name}_min"])
        if metrics[name] < limit:
            failures.append(f"{name}={metrics[name]} < {limit}")
    for name in (
        "setup_violations",
        "hold_violations",
        "drc_errors",
        "antenna_violating_nets",
        "antenna_violating_pins",
    ):
        limit = float(acceptance[f"{name}_max"])
        if metrics[name] > limit:
            failures.append(f"{name}={metrics[name]} > {limit}")
    for key, count in metrics["flow_error_counts"].items():
        if count > int(acceptance["flow_errors_max"]):
            failures.append(f"{key}={count} > {acceptance['flow_errors_max']}")
    if int(metrics["clock_count"]) != 1:
        failures.append(f"clock_count={metrics['clock_count']} != 1")
    return failures


def unconstrained_check_tcl(lock: dict[str, Any], odb: str, sdc: str) -> str:
    lines = [
        "source /OpenROAD-flow-scripts/flow/platforms/asap7/liberty_suppressions.tcl",
    ]
    lines.extend(f"read_liberty {path}" for path in liberty_paths(lock))
    lines.extend(
        [
            f"read_db {odb}",
            f"read_sdc {sdc}",
            "check_setup -unconstrained_endpoints > /work/unconstrained_endpoints.rpt",
            "",
        ]
    )
    return "\n".join(lines)


def run_unconstrained_audit(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    result_dir: Path,
) -> dict[str, Any]:
    script = case_dir / "unconstrained_check.tcl"
    log = case_dir / "unconstrained_check.log"
    report = case_dir / "unconstrained_endpoints.rpt"
    odb = "/work/" + str((result_dir / "6_final.odb").relative_to(case_dir))
    sdc = "/work/" + str((result_dir / "6_final.sdc").relative_to(case_dir))
    script.write_text(unconstrained_check_tcl(lock, odb, sdc), encoding="utf-8")
    command = docker_shell_command(
        lock,
        case_dir,
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        f"openroad -no_init -exit /work/{script.name}",
    )
    run_command(command, cwd=ROOT, log=log, timeout_seconds=1800)
    if not report.is_file():
        raise CampaignError(f"{case['name']}: unconstrained endpoint report missing")
    lines = [line for line in report.read_text(encoding="utf-8").splitlines() if line.strip()]
    limit = int(lock["acceptance"]["unconstrained_endpoints_max"])
    if len(lines) > limit:
        raise CampaignError(
            f"{case['name']}: unconstrained endpoint audit returned {len(lines)} "
            f"report lines, limit {limit}: {lines[:20]}"
        )
    return {
        "status": "pass",
        "unconstrained_endpoint_report_lines": len(lines),
        "acceptance_max": limit,
        "artifact": artifact(report),
        "script": artifact(script),
        "log": artifact(log),
    }


def memory_placeholder_audit(
    case: dict[str, Any], lock: dict[str, Any], paths: list[Path]
) -> dict[str, Any]:
    patterns = [
        re.compile(re.escape(item), re.IGNORECASE)
        for item in lock["acceptance"]["forbidden_memory_name_patterns"]
    ]
    hits: list[dict[str, Any]] = []
    for path in paths:
        if not path.is_file() or path.stat().st_size > 100 * 1024 * 1024:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            count = len(pattern.findall(text))
            if count:
                hits.append(
                    {"path": str(path.relative_to(ROOT)), "pattern": pattern.pattern, "count": count}
                )
    if hits:
        raise CampaignError(f"{case['name']}: forbidden placeholder memory references {hits}")
    return {
        "status": "pass",
        "forbidden_patterns": lock["acceptance"]["forbidden_memory_name_patterns"],
        "files_scanned": [str(path.relative_to(ROOT)) for path in paths],
        "matches": [],
    }


def copy_result_artifacts(
    case: dict[str, Any],
    case_dir: Path,
    result_dir: Path,
    report_dir: Path,
) -> dict[str, Any]:
    destination = RESULT_ROOT / case["name"] / "artifacts"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    selected = {
        name: result_dir / name
        for name in (
            "1_2_yosys.v",
            "6_final.def",
            "6_final.gds",
            "6_final.odb",
            "6_final.sdc",
            "6_final.spef",
            "6_final.v",
        )
    }
    selected.update(
        {
            "metadata.json": report_dir / "metadata.json",
            "6_finish.rpt": report_dir / "6_finish.rpt",
            "5_route_drc.rpt": report_dir / "5_route_drc.rpt",
            "config.mk": case_dir / "config.mk",
            "constraint.sdc": case_dir / "constraint.sdc",
            "1_2_yosys.raw.v": case_dir / "1_2_yosys.raw.v",
            "openroad_synthesis.log": case_dir / "openroad_synthesis.log",
            "openroad_flow.log": case_dir / "openroad_flow.log",
            "unconstrained_check.tcl": case_dir / "unconstrained_check.tcl",
            "unconstrained_check.log": case_dir / "unconstrained_check.log",
            "unconstrained_endpoints.rpt": case_dir / "unconstrained_endpoints.rpt",
        }
    )
    for proof_path in sorted(case_dir.glob("equivalence_*")):
        if proof_path.is_file():
            selected[proof_path.name] = proof_path
    ff_map = case_dir / "ff_to_nextstate.v"
    if ff_map.is_file():
        selected[ff_map.name] = ff_map
    missing = [name for name, path in selected.items() if not path.is_file()]
    if missing:
        raise CampaignError(f"{case['name']}: cannot archive missing artifacts {missing}")
    output: dict[str, Any] = {}
    for name, source in selected.items():
        target = destination / name
        shutil.copy2(source, target)
        output[name] = artifact(target)
    return output


def diagnostic_period_label(case: dict[str, Any]) -> str:
    text = f"{float(case['clock_period_ns']):g}".replace(".", "p")
    return f"{text}ns"


def write_failed_physical_evidence(
    case: dict[str, Any],
    lock: dict[str, Any],
    case_dir: Path,
    result_dir: Path,
    report_dir: Path,
    *,
    state: dict[str, Any],
    source_inventory: list[dict[str, Any]],
    metrics: dict[str, Any],
    failures: list[str],
    unconstrained_audit: dict[str, Any],
) -> Path:
    destination = (
        RESULT_ROOT
        / "diagnostics"
        / case["name"]
        / diagnostic_period_label(case)
    )
    if destination.exists():
        shutil.rmtree(destination)
    evidence_dir = destination / "artifacts"
    evidence_dir.mkdir(parents=True)
    selected = {
        "metadata.json": report_dir / "metadata.json",
        "6_finish.rpt": report_dir / "6_finish.rpt",
        "5_route_drc.rpt": report_dir / "5_route_drc.rpt",
        "config.mk": case_dir / "config.mk",
        "constraint.sdc": case_dir / "constraint.sdc",
        "1_2_yosys.raw.v": case_dir / "1_2_yosys.raw.v",
        "openroad_synthesis.log": case_dir / "openroad_synthesis.log",
        "openroad_flow.log": case_dir / "openroad_flow.log",
        "unconstrained_check.tcl": case_dir / "unconstrained_check.tcl",
        "unconstrained_check.log": case_dir / "unconstrained_check.log",
        "unconstrained_endpoints.rpt": case_dir / "unconstrained_endpoints.rpt",
    }
    for proof in sorted(case_dir.glob("equivalence_mapped*")):
        if proof.is_file():
            selected[proof.name] = proof
    missing = [name for name, path in selected.items() if not path.is_file()]
    if missing:
        raise CampaignError(
            f"{case['name']}: failed-run evidence omits required files {missing}"
        )
    copied: dict[str, Any] = {}
    for name, source in selected.items():
        target = evidence_dir / name
        shutil.copy2(source, target)
        copied[name] = artifact(target)
    final_manifests = {
        path.name: artifact(path)
        for path in sorted(result_dir.glob("6_final.*"))
        if path.is_file()
    }
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    record = {
        "schema_version": 1,
        "campaign_id": lock["campaign_id"],
        "status": "fail",
        "generated_at": generated,
        "case": case,
        "canonical": state["worktree_clean"],
        "git": state,
        "source_inventory": source_inventory,
        "metrics": metrics,
        "acceptance_failures": failures,
        "unconstrained_endpoint_audit": unconstrained_audit,
        "copied_artifacts": copied,
        "final_artifact_manifests": final_manifests,
        "claim_boundary": lock["claim_boundary"],
        "runner": artifact(RUNNER),
        "lock": artifact(DEFAULT_LOCK),
    }
    output = destination / "failure.json"
    output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output


def run_case(
    case: dict[str, Any],
    lock: dict[str, Any],
    *,
    allow_dirty: bool,
    campaign_status: list[str] | None = None,
) -> dict[str, Any]:
    source_inventory = verify_source_hashes(case)
    state = git_state(case, campaign_status=campaign_status)
    if not state["selected_sources_match_index"]:
        raise CampaignError(f"{case['name']}: selected RTL sources have unstaged changes")
    if not state["worktree_clean"] and not allow_dirty:
        raise CampaignError(
            "worktree is dirty; rerun after concurrent work commits, or use --allow-dirty "
            "for an explicitly noncanonical source-hashed run"
        )
    case_dir = BUILD_ROOT / case["name"]
    if case_dir.exists():
        make_case_writable(lock, case_dir)
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    (case_dir / "config.mk").write_text(config_text(case, lock), encoding="utf-8")
    (case_dir / "constraint.sdc").write_text(sdc_text(case, lock), encoding="utf-8")
    nickname = f"opentallas_{case['name']}"
    result_dir = case_dir / "results" / "asap7" / nickname / "base"
    report_dir = case_dir / "reports" / "asap7" / nickname / "base"
    mapped = result_dir / "1_2_yosys.v"
    mapped_container = f"/work/results/asap7/{nickname}/base/1_2_yosys.v"
    synthesis_log = case_dir / "openroad_synthesis.log"
    synth_command = docker_shell_command(lock, case_dir,
        make_prefix()
        + mapped_container
        + " && chmod a+w "
        + mapped_container
    )
    run_command(synth_command, cwd=ROOT, log=synthesis_log, timeout_seconds=3600)
    if not mapped.is_file():
        raise CampaignError(f"{case['name']}: ORFS did not produce mapped netlist")
    raw_mapped = case_dir / "1_2_yosys.raw.v"
    shutil.copy2(mapped, raw_mapped)
    signed_removed = sanitize_mapped_netlist(mapped)
    mapped_equivalence = run_equivalence(
        case, lock, case_dir, label="mapped", netlist=mapped
    )
    flow_log = case_dir / "openroad_flow.log"
    flow_command = docker_shell_command(lock, case_dir,
        make_prefix() + "finish metadata-generate"
    )
    run_command(flow_command, cwd=ROOT, log=flow_log, timeout_seconds=7200)
    required = [result_dir / name for name in lock["acceptance"]["required_final_artifacts"]]
    metadata_path = report_dir / "metadata.json"
    required.extend(
        [
            metadata_path,
            report_dir / "6_finish.rpt",
            report_dir / "5_route_drc.rpt",
        ]
    )
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise CampaignError(f"{case['name']}: ORFS omitted required artifacts {missing}")
    metadata = strict_json(metadata_path)
    if not isinstance(metadata, dict):
        raise CampaignError(f"{case['name']}: metadata root must be an object")
    metrics = extract_metrics(metadata, lock, case)
    unconstrained_audit = run_unconstrained_audit(
        case, lock, case_dir, result_dir
    )
    metric_failures = metric_gate_failures(metrics, lock)
    if metric_failures:
        failed = write_failed_physical_evidence(
            case,
            lock,
            case_dir,
            result_dir,
            report_dir,
            state=state,
            source_inventory=source_inventory,
            metrics=metrics,
            failures=metric_failures,
            unconstrained_audit=unconstrained_audit,
        )
        raise CampaignError(
            f"ASAP7 physical gates failed: {metric_failures}; "
            f"evidence archived at {failed}"
        )
    postroute_equivalence = run_equivalence(
        case, lock, case_dir, label="postroute", netlist=result_dir / "6_final.v"
    )
    placeholder_audit = memory_placeholder_audit(
        case,
        lock,
        [
            ROOT / source for source in case["sources"]
        ]
        + [mapped, result_dir / "6_final.v", case_dir / "config.mk"],
    )
    archived = copy_result_artifacts(case, case_dir, result_dir, report_dir)
    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
    result = {
        "schema_version": 1,
        "campaign_id": lock["campaign_id"],
        "case": case,
        "status": "pass",
        "generated_at": generated,
        "canonical": state["worktree_clean"],
        "canonical_disposition": (
            "clean source baseline"
            if state["worktree_clean"]
            else "noncanonical dirty-worktree run; selected source hashes are locked and unchanged"
        ),
        "git": state,
        "source_inventory": source_inventory,
        "toolchain": verify_toolchain(lock),
        "metrics": metrics,
        "mapped_equivalence": mapped_equivalence,
        "postroute_equivalence": postroute_equivalence,
        "unconstrained_endpoint_audit": unconstrained_audit,
        "memory_placeholder_audit": placeholder_audit,
        "netlist_normalization": {
            "signed_declaration_tokens_removed": signed_removed,
            "reason": "The embedded OpenSTA reader rejects signed top declarations after bit-level mapping; mandatory mapped and final sequential equivalence gate this syntax-only normalization.",
            "raw_mapped_netlist": archived["1_2_yosys.raw.v"],
        },
        "artifacts": archived,
        "claim_boundary": lock["claim_boundary"],
        "runner": artifact(RUNNER),
        "lock": artifact(DEFAULT_LOCK),
    }
    case_result = RESULT_ROOT / case["name"] / "physical.json"
    case_result.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def load_completed(lock: dict[str, Any]) -> dict[str, dict[str, Any]]:
    completed: dict[str, dict[str, Any]] = {}
    for case in lock["cases"]:
        path = RESULT_ROOT / case["name"] / "physical.json"
        if not path.is_file():
            continue
        data = strict_json(path)
        if (
            isinstance(data, dict)
            and data.get("campaign_id") == lock["campaign_id"]
            and data.get("case", {}).get("name") == case["name"]
        ):
            completed[case["name"]] = data
    return completed


def render_report(lock: dict[str, Any], completed: dict[str, dict[str, Any]]) -> str:
    required = lock["acceptance"]["required_cases"]
    cases = {case["name"]: case for case in lock["cases"]}
    stale = [
        name for name in required
        if name in completed and not record_is_current(cases[name], completed[name])
    ]
    passed = [
        name for name in required
        if completed.get(name, {}).get("status") == "pass" and name not in stale
    ]
    canonical = [name for name in passed if completed[name].get("canonical")]
    overall = "PASS" if passed == required and canonical == required else "PARTIAL"
    lines = [
        "# ASAP7 predictive physical implementation",
        "",
        f"**Campaign:** `{lock['campaign_id']}`  ",
        f"**Overall status:** **{overall}**  ",
        f"**Completed cases:** {len(passed)}/{len(required)}  ",
        f"**Clean-baseline cases:** {len(canonical)}/{len(required)}  ",
        f"**Stale archived cases:** {len(stale)}/{len(required)}",
        "",
        "This is a source-hashed RTL-to-GDS experiment in the public predictive ASAP7",
        "research platform. It is not foundry signoff and contains no ROM or SRAM macro.",
        "The bundled ASAP7 FakeRAM files are explicitly forbidden from these cases.",
        "",
        "## Results",
        "",
        "| Case | Status | Canonical | Target | Fmax | Std-cell area | Routed wire | Vias | Setup WNS | Hold WNS | DRC |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in lock["cases"]:
        name = case["name"]
        data = completed.get(name)
        if data is None:
            lines.append(
                f"| `{name}` | NOT RUN | — | {1e3/case['clock_period_ns']:.1f} MHz | — | — | — | — | — | — | — |"
            )
            continue
        metrics = data["metrics"]
        status = "STALE" if name in stale else data["status"].upper()
        lines.append(
            f"| `{name}` | {status} | {'yes' if data['canonical'] else 'no'} | "
            f"{1e3/case['clock_period_ns']:.1f} MHz | {metrics['fmax_hz']/1e6:.1f} MHz | "
            f"{metrics['standard_cell_area_um2']:.2f} µm² | {metrics['wirelength_um']:.1f} µm | "
            f"{metrics['vias']:.0f} | {metrics['setup_wns_ns']:.4f} ns | "
            f"{metrics['hold_wns_ns']:.4f} ns | {metrics['drc_errors']:.0f} |"
        )
    lines.extend(
        [
            "",
            "A case is passing only after mapped-netlist and final-netlist sequential",
            "equivalence, zero reported setup/hold violations, zero detailed-route DRC",
            "errors, zero antenna violations, and zero flow errors. A dirty-worktree run",
            "is retained as useful source-hashed evidence but does not close the clean-baseline gate.",
            "A STALE case's archived record was produced from source that no longer matches",
            "the lock; its figures describe that older RTL and are not counted.",
            "",
            "## Evidence boundary",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in lock["claim_boundary"])
    if stale:
        lines.extend(["", "## Stale archived evidence", ""])
        for name in stale:
            archived = cases[name].get("archived_evidence", {})
            lines.append(
                f"- `{name}`: {archived.get('reason', 'record sources do not match the lock')} "
                f"Re-qualification: {archived.get('requalification', 'not attempted')}"
            )
    lines.extend(
        [
            "",
            "The next physical stages are exact target-format arithmetic, the stage-control",
            "shell, hierarchical router/NoC cuts, and a separately characterized research ROM",
            "macro. These three initial blocks do not close those gates.",
            "",
        ]
    )
    return "\n".join(lines)


def write_aggregate(lock: dict[str, Any]) -> None:
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    completed = load_completed(lock)
    cases = {case["name"]: case for case in lock["cases"]}
    stale = sorted(
        name for name, record in completed.items()
        if not record_is_current(cases[name], record)
    )
    undeclared = [name for name in stale if "archived_evidence" not in cases[name]]
    if undeclared:
        raise CampaignError(
            f"archived records do not match the lock sources and are not declared "
            f"stale: {undeclared}"
        )
    summary = {
        "schema_version": 1,
        "campaign_id": lock["campaign_id"],
        "required_cases": lock["acceptance"]["required_cases"],
        "completed_cases": sorted(completed),
        "stale_cases": stale,
        "all_pass": all(
            completed.get(name, {}).get("status") == "pass" and name not in stale
            for name in lock["acceptance"]["required_cases"]
        ),
        "all_canonical": all(
            completed.get(name, {}).get("canonical") is True and name not in stale
            for name in lock["acceptance"]["required_cases"]
        ),
        "cases": completed,
        "claim_boundary": lock["claim_boundary"],
    }
    (RESULT_ROOT / "physical.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (RESULT_ROOT / "REPORT.md").write_text(
        render_report(lock, completed), encoding="utf-8"
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument(
        "--aggregate-only",
        action="store_true",
        help="re-render physical.json and REPORT.md from the archived case records",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="validate source, lock, container, and ASAP7 collateral without running P&R",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    lock = strict_json(args.lock)
    if not isinstance(lock, dict):
        raise CampaignError("ASAP7 lock root must be an object")
    validate_lock(lock)
    if args.aggregate_only:
        write_aggregate(lock)
        return 0
    selected = args.cases or lock["acceptance"]["required_cases"]
    if len(selected) != len(set(selected)):
        raise CampaignError("duplicate --case selection")
    for name in selected:
        case = case_by_name(lock, name)
        verify_source_hashes(case)
    identity = verify_toolchain(lock)
    print(
        f"ASAP7 toolchain verified: {identity['openroad_version']} / "
        f"{identity['yosys_version']}",
        flush=True,
    )
    if args.check_only:
        return 0
    campaign_status = git_worktree_status()
    for name in selected:
        print(f"[{name}] starting governed ASAP7 flow", flush=True)
        run_case(
            case_by_name(lock, name),
            lock,
            allow_dirty=args.allow_dirty,
            campaign_status=campaign_status,
        )
        write_aggregate(lock)
        print(f"[{name}] PASS", flush=True)
    write_aggregate(lock)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CampaignError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
