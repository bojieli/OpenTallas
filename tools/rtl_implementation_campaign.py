#!/usr/bin/env python3
"""Run the governed public synthesis, STA, equivalence, and P&R proxy campaign.

This runner deliberately treats every number as an open-library methodology
proxy.  It does not infer target-node PPA from Nangate45 and it keeps ROM,
SRAM, HBM, PHY, package, and analog resources outside the synthesized shells.
Only the Python standard library is required; the pinned external tools and
their hashes are described by ``spec/implementation_proxy.json``.
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
import shutil
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
RUNNER = Path(__file__).resolve()
DEFAULT_SPEC = ROOT / "spec" / "implementation_proxy.json"
CDC_SPEC = ROOT / "spec" / "clock_reset_crossings.json"
BUILD_ROOT = ROOT / "rtl" / "build" / "implementation_campaign"

DEFAULT_YOSYS = Path(
    os.environ.get(
        "OPENTALLAS_YOSYS",
        str(Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys"),
    )
)
DEFAULT_ABC = Path(
    os.environ.get(
        "OPENTALLAS_ABC",
        str(Path.home() / ".local/opentallas-tools/yosys-0.68/bin/yosys-abc"),
    )
)
DEFAULT_OPENSTA = Path(
    os.environ.get(
        "OPENTALLAS_OPENSTA",
        str(Path.home() / ".local/opentallas-tools/opensta-be771a0/bin/sta"),
    )
)
DEFAULT_PDK = Path(
    os.environ.get(
        "OPENTALLAS_NANGATE45",
        str(Path.home() / ".local/opentallas-pdk/nangate45-be0dca0"),
    )
)
LIBERTY_NAME = "NangateOpenCellLibrary_typical.lib"
MACRO_LEF_NAME = "NangateOpenCellLibrary.macro.mod.lef"
TECH_LEF_NAME = "NangateOpenCellLibrary.tech.lef"
OPENROAD_REPOSITORY = "openroad/orfs"

MEMORY_WARNING_RE = re.compile(
    r"^Warning: Replacing memory \\(?P<memory>[^ ]+) with list of registers\. "
    r"See (?P<source>rtl/(?:lib/)?[^:]+):(?P<line>[0-9]+)$"
)
AIGER_UNDRIVEN_BIT_RE = re.compile(
    r"^Warning: Treating undriven bit (?P<top>[A-Za-z0-9_$]+)\.\\"
    r"(?P<port>[A-Za-z0-9_$]+)(?: \[(?P<bit>[0-9]+)\])? like \$anyseq\.$"
)
AIGER_UNDRIVEN_TOTAL_RE = re.compile(
    r"^Warning: Treating a total of (?P<count>[0-9]+) undriven bits in "
    r"(?P<top>[A-Za-z0-9_$]+) like \$anyseq\.$"
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
BOUNDED_ABC_SCRIPT = "strash; &get -n; &nf; &put"


class CampaignError(RuntimeError):
    """A governed campaign gate failed."""


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
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise CampaignError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise CampaignError(f"duplicate JSON keys in {path}: {sorted(set(duplicates))}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path) -> dict[str, Any]:
    try:
        relative = str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        relative = path.name
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def shell_version(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode != 0:
        raise CampaignError(
            f"tool identity command failed ({completed.returncode}): {' '.join(command)}\n"
            f"{completed.stdout}"
        )
    return completed.stdout.strip()


def require_hash(path: Path, expected: str, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise CampaignError(f"missing {label}: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise CampaignError(f"{label} hash {actual}, expected {expected}")
    return {"file": path.name, "sha256": actual, "size_bytes": path.stat().st_size}


def validate_spec(spec: dict[str, Any]) -> None:
    if spec.get("schema_version") != 1:
        raise CampaignError("implementation proxy schema_version must be 1")
    cases = spec.get("cases")
    if not isinstance(cases, list) or not cases:
        raise CampaignError("implementation proxy cases must be non-empty")
    names: list[str] = []
    for case in cases:
        if not isinstance(case, dict):
            raise CampaignError("implementation proxy case is not an object")
        missing = {
            "name",
            "kind",
            "top",
            "sources",
            "parameters",
            "equivalence",
            "physical_proxy",
        } - set(case)
        if missing:
            raise CampaignError(f"case is missing fields: {sorted(missing)}")
        name = case["name"]
        if not isinstance(name, str) or re.fullmatch(r"[a-z0-9_]+", name) is None:
            raise CampaignError(f"invalid case name {name!r}")
        names.append(name)
        if case["kind"] not in {"numeric", "stage_control"}:
            raise CampaignError(f"{name}: unsupported kind {case['kind']!r}")
        if case["equivalence"] not in {"required", "scaling_only"}:
            raise CampaignError(f"{name}: invalid equivalence policy")
        if not isinstance(case["parameters"], dict) or not case["parameters"]:
            raise CampaignError(f"{name}: parameters must be non-empty")
        for key, value in case["parameters"].items():
            if not isinstance(key, str) or not isinstance(value, int) or value < 1:
                raise CampaignError(f"{name}: invalid parameter {key}={value!r}")
        if not isinstance(case["sources"], list) or not case["sources"]:
            raise CampaignError(f"{name}: sources must be non-empty")
        for source in case["sources"]:
            if not isinstance(source, str) or not (ROOT / source).is_file():
                raise CampaignError(f"{name}: missing source {source!r}")
        physical = case["physical_proxy"]
        if physical is not None:
            if not isinstance(physical, dict) or physical.get("required") is not True:
                raise CampaignError(f"{name}: physical proxy must be required or null")
            unloaded = physical.get("allowed_unloaded_top_input_bits")
            if not isinstance(unloaded, list):
                raise CampaignError(
                    f"{name}: allowed_unloaded_top_input_bits must be a list"
                )
            seen_unloaded: set[tuple[str, int]] = set()
            for allowance in unloaded:
                if not isinstance(allowance, dict):
                    raise CampaignError(f"{name}: invalid unloaded-input allowance")
                port = allowance.get("port")
                first = allowance.get("first_bit")
                last = allowance.get("last_bit")
                reason = allowance.get("reason")
                if (
                    not isinstance(port, str)
                    or not isinstance(first, int)
                    or not isinstance(last, int)
                    or first < 0
                    or last < first
                    or not isinstance(reason, str)
                    or not reason
                ):
                    raise CampaignError(f"{name}: invalid unloaded-input allowance")
                for bit in range(first, last + 1):
                    key = (port, bit)
                    if key in seen_unloaded:
                        raise CampaignError(
                            f"{name}: duplicate unloaded-input allowance {key}"
                        )
                    seen_unloaded.add(key)
            for field in ("die_area_um", "core_area_um"):
                area = physical.get(field)
                if (
                    not isinstance(area, list)
                    or len(area) != 4
                    or any(not isinstance(value, (int, float)) for value in area)
                    or area[0] >= area[2]
                    or area[1] >= area[3]
                ):
                    raise CampaignError(f"{name}: invalid {field}")
            density = physical.get("place_density")
            if not isinstance(density, (int, float)) or not 0.0 < density < 1.0:
                raise CampaignError(f"{name}: invalid place_density")
    duplicates = sorted(name for name in set(names) if names.count(name) != 1)
    if duplicates:
        raise CampaignError(f"duplicate implementation case names: {duplicates}")
    acceptance = spec.get("acceptance", {})
    name_set = set(names)
    for field in (
        "required_cases",
        "equivalence_required_cases",
        "mapped_equivalence_required_cases",
        "postroute_equivalence_required_cases",
        "prelayout_setup_required_cases",
        "physical_proxy_required_cases",
    ):
        selected = acceptance.get(field)
        if not isinstance(selected, list) or len(selected) != len(set(selected)):
            raise CampaignError(f"acceptance.{field} must be a unique list")
        unknown = set(selected) - name_set
        if unknown:
            raise CampaignError(f"acceptance.{field} has unknown cases: {sorted(unknown)}")
    required = set(acceptance["required_cases"])
    if required != name_set:
        raise CampaignError("acceptance.required_cases must exactly enumerate cases")
    equivalence = {case["name"] for case in cases if case["equivalence"] == "required"}
    if set(acceptance["equivalence_required_cases"]) != equivalence:
        raise CampaignError("equivalence-required cases disagree with case policies")
    physical = {case["name"] for case in cases if case["physical_proxy"] is not None}
    if set(acceptance["physical_proxy_required_cases"]) != physical:
        raise CampaignError("physical-required cases disagree with case policies")
    if set(acceptance["postroute_equivalence_required_cases"]) != physical:
        raise CampaignError(
            "postroute-equivalence-required cases must exactly match physical cases"
        )
    numeric_acceptance = (
        "physical_antenna_violating_nets_max",
        "physical_antenna_violating_pins_max",
        "physical_design_violations_max",
        "physical_drc_errors_max",
        "physical_flow_errors_max",
        "physical_hold_tns_ns_min",
        "physical_hold_violations_max",
        "physical_hold_wns_ns_min",
        "physical_max_capacitance_violations_max",
        "physical_max_fanout_violations_max",
        "physical_max_slew_violations_max",
        "physical_placement_violations_max",
        "physical_setup_tns_ns_min",
        "physical_setup_violations_max",
        "physical_setup_wns_ns_min",
    )
    for field in numeric_acceptance:
        if not isinstance(acceptance.get(field), (int, float)):
            raise CampaignError(f"acceptance.{field} must be numeric")
    constraints = spec.get("constraints", {})
    max_fanout = constraints.get("max_fanout")
    if not isinstance(max_fanout, int) or max_fanout < 1:
        raise CampaignError("constraints.max_fanout must be a positive integer")
    flow_policy = spec.get("physical_flow_policy")
    if not isinstance(flow_policy, dict):
        raise CampaignError("physical_flow_policy must be an object")
    lec = flow_policy.get("orfs_kepler_lec", {})
    if lec.get("enabled") is not False or not all(
        isinstance(lec.get(field), str) and lec[field]
        for field in ("failure_observed", "replacement_gate", "trust_boundary")
    ):
        raise CampaignError("physical_flow_policy.orfs_kepler_lec is incomplete")
    for field in (
        "capacitance_margin",
        "hold_slack_margin_ns",
        "place_density_lower_bound_addon",
        "tns_end_percent",
    ):
        if not isinstance(flow_policy.get(field), (int, float)):
            raise CampaignError(f"physical_flow_policy.{field} must be numeric")
    for field in ("power", "ir_drop"):
        policy = flow_policy.get(field, {})
        if (
            policy.get("gate") is not False
            or not isinstance(policy.get("status"), str)
            or not isinstance(policy.get("use"), str)
        ):
            raise CampaignError(f"physical_flow_policy.{field} is incomplete")
    postroute_policy = flow_policy.get("postroute_equivalence", {})
    if (
        not isinstance(postroute_policy, dict)
        or not isinstance(postroute_policy.get("abc_timeout_seconds"), int)
        or postroute_policy["abc_timeout_seconds"] < 1
        or not isinstance(postroute_policy.get("private_state_symbol_remaps_max"), int)
        or postroute_policy["private_state_symbol_remaps_max"] < 0
        or postroute_policy.get("arbitrary_common_initial_state_required") is not True
        or not isinstance(postroute_policy.get("state_alignment_policy"), str)
        or not postroute_policy["state_alignment_policy"]
    ):
        raise CampaignError(
            "physical_flow_policy.postroute_equivalence is incomplete"
        )
    generic_policy = spec.get("generic_equivalence_policy", {})
    if (
        not isinstance(generic_policy, dict)
        or not isinstance(generic_policy.get("abc_timeout_seconds"), int)
        or generic_policy["abc_timeout_seconds"] < 1
        or not isinstance(generic_policy.get("outer_process_timeout_seconds"), int)
        or generic_policy["outer_process_timeout_seconds"]
        <= generic_policy["abc_timeout_seconds"]
        or not isinstance(generic_policy.get("initial_output_partition_bits"), int)
        or generic_policy["initial_output_partition_bits"] < 1
        or not isinstance(generic_policy.get("minimum_output_partition_bits"), int)
        or generic_policy["minimum_output_partition_bits"] < 1
        or generic_policy["minimum_output_partition_bits"]
        > generic_policy["initial_output_partition_bits"]
        or generic_policy.get("arbitrary_common_initial_state_required") is not True
        or generic_policy.get("require_exact_output_coverage") is not True
        or not all(
            isinstance(generic_policy.get(field), str) and generic_policy[field]
            for field in (
                "interface_alignment_policy",
                "stage_control_method",
                "undefined_state_policy",
            )
        )
    ):
        raise CampaignError("generic_equivalence_policy is incomplete")
    large_policy = spec.get("large_case_mapping_policy")
    if not isinstance(large_policy, dict):
        raise CampaignError("large_case_mapping_policy must be an object")
    large_cases = large_policy.get("case_names")
    if (
        not isinstance(large_cases, list)
        or not large_cases
        or len(large_cases) != len(set(large_cases))
        or any(not isinstance(name, str) for name in large_cases)
    ):
        raise CampaignError(
            "large_case_mapping_policy.case_names must be a non-empty unique list"
        )
    if large_cases != ["numeric_e16_l16"]:
        raise CampaignError(
            "large_case_mapping_policy must be limited exactly to numeric_e16_l16"
        )
    for name in large_cases:
        case = next((item for item in cases if item["name"] == name), None)
        if (
            case is None
            or case["equivalence"] != "scaling_only"
            or case["physical_proxy"] is not None
        ):
            raise CampaignError(
                f"large-case bounded mapping is allowed only for a scaling-only, "
                f"non-physical case: {name}"
            )
    if large_policy.get("abc_script") != BOUNDED_ABC_SCRIPT:
        raise CampaignError(
            "large_case_mapping_policy.abc_script is not the reviewed bounded recipe"
        )
    if (
        not isinstance(large_policy.get("outer_process_timeout_seconds"), int)
        or large_policy["outer_process_timeout_seconds"] < 1
    ):
        raise CampaignError(
            "large_case_mapping_policy.outer_process_timeout_seconds must be positive"
        )
    for field in (
        "profile_id",
        "qor_comparability",
        "rationale",
        "scope",
    ):
        if not isinstance(large_policy.get(field), str) or not large_policy[field]:
            raise CampaignError(f"large_case_mapping_policy.{field} is missing")
    required_closure = large_policy.get("required_closure")
    expected_closure = {
        "all_mapped_cells_from_pinned_liberty": True,
        "blackboxes_max": acceptance["blackboxes_max"],
        "complete_mapped_netlist": True,
        "complete_sta_constraint_coverage": True,
        "latches_max": acceptance["latches_max"],
        "mapped_internal_cells_max": acceptance["mapped_internal_cells_max"],
        "structural_problems_max": acceptance["structural_problems_max"],
    }
    if required_closure != expected_closure:
        raise CampaignError(
            "large_case_mapping_policy.required_closure must preserve all mapped "
            "structural and STA-coverage gates"
        )
    yosys_tools = spec.get("toolchain", {}).get("yosys", {})
    if not isinstance(yosys_tools.get("abc_version_family"), str) or not yosys_tools[
        "abc_version_family"
    ]:
        raise CampaignError("toolchain.yosys.abc_version_family is missing")
    openroad_warnings = spec.get("warning_policy", {}).get("openroad", {})
    allowed_codes = openroad_warnings.get("allowed_codes")
    forbidden_codes = openroad_warnings.get("forbidden_codes")
    if not isinstance(allowed_codes, dict) or not isinstance(forbidden_codes, list):
        raise CampaignError("warning_policy.openroad is incomplete")
    if set(allowed_codes) & set(forbidden_codes):
        raise CampaignError("OpenROAD warning codes cannot be allowed and forbidden")
    for code, disposition in allowed_codes.items():
        if re.fullmatch(r"[A-Z]{3}-[0-9]{4}", code) is None:
            raise CampaignError(f"invalid OpenROAD warning code {code!r}")
        if (
            not isinstance(disposition, dict)
            or set(disposition.get("case_kinds", [])) - {"numeric", "stage_control"}
            or not disposition.get("case_kinds")
            or not isinstance(disposition.get("disposition"), str)
        ):
            raise CampaignError(f"invalid OpenROAD warning disposition for {code}")
    for code in forbidden_codes:
        if not isinstance(code, str) or re.fullmatch(r"[A-Z]{3}-[0-9]{4}", code) is None:
            raise CampaignError(f"invalid forbidden OpenROAD warning code {code!r}")
    for digest in find_values_by_suffix(spec.get("toolchain", {}), "sha256"):
        if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
            raise CampaignError(f"invalid pinned SHA-256 {digest!r}")


def find_values_by_suffix(value: Any, suffix: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key.endswith(suffix):
                found.append(child)
            found.extend(find_values_by_suffix(child, suffix))
    elif isinstance(value, list):
        for child in value:
            found.extend(find_values_by_suffix(child, suffix))
    return found


def resolve_toolchain(spec: dict[str, Any], *, require_physical: bool) -> dict[str, Any]:
    tools = spec["toolchain"]
    yosys = require_hash(
        DEFAULT_YOSYS, tools["yosys"]["executable_sha256"], "Yosys executable"
    )
    abc = require_hash(DEFAULT_ABC, tools["yosys"]["abc_sha256"], "ABC executable")
    opensta = require_hash(
        DEFAULT_OPENSTA, tools["opensta"]["executable_sha256"], "OpenSTA executable"
    )
    liberty = require_hash(
        DEFAULT_PDK / LIBERTY_NAME,
        tools["nangate45"]["liberty_sha256"],
        "Nangate45 Liberty",
    )
    macro_lef = require_hash(
        DEFAULT_PDK / MACRO_LEF_NAME,
        tools["nangate45"]["lef_macro_sha256"],
        "Nangate45 macro LEF",
    )
    technology_lef = require_hash(
        DEFAULT_PDK / TECH_LEF_NAME,
        tools["nangate45"]["lef_technology_sha256"],
        "Nangate45 technology LEF",
    )
    license_file = require_hash(
        DEFAULT_PDK / "LICENSE",
        tools["nangate45"]["license_sha256"],
        "Nangate45 license",
    )
    identities: dict[str, Any] = {
        "yosys": {**yosys, "version_output": shell_version([str(DEFAULT_YOSYS), "-V"])},
        "abc": {
            **abc,
            "version_output": shell_version([str(DEFAULT_ABC), "-c", "version"]),
        },
        "opensta": {
            **opensta,
            "version_output": shell_version([str(DEFAULT_OPENSTA), "-version"]),
        },
        "nangate45": {
            "corner": tools["nangate45"]["corner"],
            "liberty": liberty,
            "macro_lef": macro_lef,
            "technology_lef": technology_lef,
            "license": license_file,
            "use": tools["nangate45"]["use"],
        },
    }
    if tools["yosys"]["abc_version_family"] not in identities["abc"]["version_output"]:
        raise CampaignError(
            "ABC version output does not contain the governed version family: "
            f"{identities['abc']['version_output']}"
        )
    if require_physical:
        container = tools["openroad_orfs_container"]
        reference = f"{OPENROAD_REPOSITORY}@{container['amd64_digest']}"
        image_id = shell_version(
            ["docker", "image", "inspect", reference, "--format", "{{.Id}}"]
        )
        if image_id != container["image_id"]:
            raise CampaignError(
                f"OpenROAD image ID {image_id!r}, expected {container['image_id']!r}"
            )
        inside = shell_version(
            [
                "docker",
                "run",
                "--rm",
                reference,
                "bash",
                "-lc",
                "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
                "openroad -version; yosys -V; "
                "sha256sum \"$(command -v openroad)\" \"$(command -v yosys)\"",
            ]
        )
        for expected in (
            container["openroad_version"],
            container["openroad_executable_sha256"],
            container["yosys_executable_sha256"],
        ):
            if expected not in inside:
                raise CampaignError(
                    f"OpenROAD container identity output omits {expected}:\n{inside}"
                )
        identities["openroad_orfs_container"] = {
            "repository": OPENROAD_REPOSITORY,
            "amd64_digest": container["amd64_digest"],
            "image_id": image_id,
            "identity_output": inside.splitlines(),
            "orfs_revision_binding": container["orfs_revision_binding"],
        }
    return identities


def git_state() -> dict[str, Any]:
    commit = shell_version(["git", "rev-parse", "HEAD"])
    status = shell_version(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"]
    )
    dirty = [line for line in status.splitlines() if line and "rtl/build/" not in line]
    return {"commit": commit, "dirty_paths": dirty}


def source_inventory(spec_path: Path, cases: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    paths = {spec_path.resolve(), CDC_SPEC.resolve(), RUNNER}
    for case in cases:
        paths.update((ROOT / source).resolve() for source in case["sources"])
    inventory: list[dict[str, Any]] = []
    for path in sorted(paths):
        inventory.append(artifact(path))
    return inventory


def fingerprint(
    spec: dict[str, Any], inventory: list[dict[str, Any]], tools: dict[str, Any]
) -> str:
    identity = {
        "spec": spec,
        "sources": inventory,
        "tool_hashes": sorted(find_values_by_suffix(tools, "sha256")),
    }
    payload = json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


def parameter_args(case: dict[str, Any]) -> str:
    return " ".join(
        f"-chparam {key} {value}" for key, value in sorted(case["parameters"].items())
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_logged(
    command: list[str],
    log: Path,
    *,
    cwd: Path = ROOT,
    timeout_s: int | None = None,
) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    try:
        with log.open("w", encoding="utf-8") as handle:
            completed = subprocess.run(
                command,
                cwd=cwd,
                check=False,
                text=True,
                stdout=handle,
                stderr=subprocess.STDOUT,
                timeout=timeout_s,
            )
    except subprocess.TimeoutExpired as exc:
        raise CampaignError(
            f"command exceeded {timeout_s} seconds: {' '.join(command)}; log: {log}"
        ) from exc
    if completed.returncode != 0:
        tail = "\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-80:])
        raise CampaignError(
            f"command failed ({completed.returncode}): {' '.join(command)}\n"
            f"log: {log}\n{tail}"
        )


def mapping_profile(case: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    policy = spec["large_case_mapping_policy"]
    if case["name"] in policy["case_names"]:
        abc_script = policy["abc_script"]
        return {
            "profile_id": policy["profile_id"],
            "abc_script": abc_script,
            "yosys_command_template": (
                'abc -liberty <pinned-liberty> -script "+' + abc_script + '"'
            ),
            "outer_process_timeout_seconds": policy[
                "outer_process_timeout_seconds"
            ],
            "qor_comparable_to_default_profile": False,
            "qor_comparability": policy["qor_comparability"],
            "rationale": policy["rationale"],
        }
    return {
        "profile_id": "default_delay_oriented",
        "abc_script": None,
        "yosys_command_template": "abc -liberty <pinned-liberty> -D 10000",
        "outer_process_timeout_seconds": None,
        "qor_comparable_to_default_profile": True,
        "qor_comparability": (
            "Mapped by the common default delay-oriented ABC command used for all "
            "non-excepted cases."
        ),
        "rationale": "Default governed quality-oriented mapping profile.",
    }


def yosys_script(
    case: dict[str, Any], case_dir: Path, mapping: dict[str, Any]
) -> str:
    sources = " ".join(case["sources"])
    liberty = DEFAULT_PDK / LIBERTY_NAME
    generic_stats = case_dir / "generic_stats.json"
    mapped_stats = case_dir / "mapped_stats.json"
    netlist = case_dir / "netlist.v"
    netlist_json = case_dir / "netlist.json"
    abc_command = mapping["yosys_command_template"].replace(
        "<pinned-liberty>", str(liberty)
    )
    return "\n".join(
        [
            f"read_liberty -lib {liberty}",
            f"read_verilog -sv -DSYNTHESIS {sources}",
            f"hierarchy -check -top {case['top']} {parameter_args(case)}",
            "proc",
            "memory_collect",
            "opt",
            f"tee -o {generic_stats} stat -json",
            f"synth -top {case['top']} -flatten -noabc",
            f"dfflibmap -liberty {liberty}",
            abc_command,
            "clean -purge",
            "check -assert",
            f"tee -o {mapped_stats} stat -json -liberty {liberty}",
            f"write_verilog -noattr -noexpr -nodec {netlist}",
            f"write_json {netlist_json}",
            "",
        ]
    )


def warning_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("Warning:") or line.startswith("ABC: Warning:")
    ]


def validate_warnings(
    warnings: list[str], case: dict[str, Any], policy: dict[str, Any], *, allow_abc: bool
) -> dict[str, Any]:
    allowed_abc = set(policy["allowed_abc_exact"] if allow_abc else [])
    memory_policy = policy["allowed_memory_to_register"]
    unexpected: list[str] = []
    conversions: list[dict[str, Any]] = []
    for warning in warnings:
        if warning in allowed_abc:
            continue
        match = MEMORY_WARNING_RE.fullmatch(warning)
        if match:
            source = match.group("source")
            memory = match.group("memory")
            if source in case["sources"] and memory in memory_policy.get(source, []):
                conversions.append(
                    {"source": source, "line": int(match.group("line")), "memory": memory}
                )
                continue
        unexpected.append(warning)
    if unexpected:
        raise CampaignError(f"{case['name']}: unexpected warnings: {unexpected}")
    return {
        "count": len(warnings),
        "counts": dict(sorted(Counter(warnings).items())),
        "memory_to_register": conversions,
        "unexpected": [],
    }


def top_stats(path: Path, top: str) -> dict[str, Any]:
    data = strict_json(path)
    modules = data.get("modules", {})
    for key in (f"\\{top}", top):
        if key in modules:
            return modules[key]
    raise CampaignError(f"{path}: no statistics for top {top}")


def liberty_cell_names(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"(?m)^\s*cell\s*\(\s*([^\s)]+)\s*\)", text))


def synthesize_case(case: dict[str, Any], case_dir: Path, spec: dict[str, Any]) -> dict[str, Any]:
    synth_dir = case_dir / "synthesis"
    synth_dir.mkdir(parents=True, exist_ok=True)
    mapping = mapping_profile(case, spec)
    script_path = synth_dir / "synth.ys"
    write_text(script_path, yosys_script(case, synth_dir, mapping))
    log = synth_dir / "synth.log"
    print(
        f"[{case['name']}] mapped synthesis ({mapping['profile_id']})", flush=True
    )
    run_logged(
        [str(DEFAULT_YOSYS), "-s", str(script_path)],
        log,
        timeout_s=mapping["outer_process_timeout_seconds"],
    )
    warnings = validate_warnings(
        warning_lines(log), case, spec["warning_policy"], allow_abc=True
    )
    generic_path = synth_dir / "generic_stats.json"
    mapped_path = synth_dir / "mapped_stats.json"
    netlist_path = synth_dir / "netlist.v"
    netlist_json_path = synth_dir / "netlist.json"
    for required in (generic_path, mapped_path, netlist_path, netlist_json_path):
        if not required.is_file():
            raise CampaignError(f"{case['name']}: synthesis omitted {required.name}")
    generic = top_stats(generic_path, case["top"])
    mapped = top_stats(mapped_path, case["top"])
    cell_types = mapped.get("num_cells_by_type", {})
    known = liberty_cell_names(DEFAULT_PDK / LIBERTY_NAME)
    unknown_types = sorted(cell_type for cell_type in cell_types if cell_type not in known)
    internal_count = sum(
        count for cell_type, count in cell_types.items() if cell_type.startswith("$")
    )
    latch_count = sum(
        count
        for cell_type, count in cell_types.items()
        if "LATCH" in cell_type.upper() or cell_type.upper().startswith(("DLH", "DLL"))
    )
    blackbox_count = sum(cell_types[cell_type] for cell_type in unknown_types)
    acceptance = spec["acceptance"]
    if internal_count > acceptance["mapped_internal_cells_max"]:
        raise CampaignError(f"{case['name']}: {internal_count} mapped internal cells")
    if latch_count > acceptance["latches_max"]:
        raise CampaignError(f"{case['name']}: {latch_count} mapped latches")
    if blackbox_count > acceptance["blackboxes_max"]:
        raise CampaignError(
            f"{case['name']}: {blackbox_count} blackbox/unknown cells {unknown_types}"
        )
    return {
        "status": "pass",
        "mapping_profile": mapping,
        "generic": generic,
        "mapped": mapped,
        "all_mapped_cells_from_pinned_liberty": not unknown_types,
        "mapped_internal_cells": internal_count,
        "latches": latch_count,
        "blackboxes": blackbox_count,
        "unknown_cell_types": unknown_types,
        "warnings": warnings,
        "structural_problems": 0,
        "artifacts": {
            "script": artifact(script_path),
            "log": artifact(log),
            "generic_stats": artifact(generic_path),
            "mapped_stats": artifact(mapped_path),
            "netlist": artifact(netlist_path),
            "netlist_json": artifact(netlist_json_path),
        },
        "paths": {
            "netlist": netlist_path,
            "netlist_json": netlist_json_path,
        },
    }


def equivalence_script(case: dict[str, Any]) -> str:
    sources = " ".join(case["sources"])
    multiclock = " -multiclock" if case["kind"] == "stage_control" else ""
    return "\n".join(
        [
            f"read_verilog -sv -DSYNTHESIS {sources}",
            f"hierarchy -check -top {case['top']} {parameter_args(case)}",
            "proc",
            "memory",
            "flatten",
            # ``equiv_opt`` internally duplicates and synthesizes this design, but
            # Yosys ``equiv_induct`` has no SAT model for asynchronous-reset FF
            # cells.  Normalize the common RTL before both sides are created so
            # reset semantics remain aligned and the proof operates on supported
            # synchronous cells.
            "async2sync",
            "opt",
            f"equiv_opt -assert{multiclock} synth -top {case['top']} -flatten -noabc",
            "",
        ]
    )


def generic_aiger_script(
    case: dict[str, Any],
    aiger: Path,
    verbose_map: Path,
    *,
    synthesize: bool,
) -> str:
    sources = " ".join(case["sources"])
    commands = [
        f"read_verilog -sv -DSYNTHESIS {sources}",
        f"hierarchy -check -top {case['top']} {parameter_args(case)}",
        "proc",
        "memory",
        "flatten",
        "opt",
        "async2sync",
        "clk2fflogic",
        "formalff -ff2anyinit -setundef",
    ]
    if synthesize:
        commands.append(f"synth -top {case['top']} -flatten -noabc")
    commands.extend(
        [
            "formalff -anyinit2ff -fine",
            "techmap",
            "dfflegalize -cell $_DFF_P_ x",
            "opt -nodffe -nosdff",
            "setundef -undriven -zero",
            "setundef -zero",
            "aigmap",
            "clean -purge",
            "check -assert",
            f"write_aiger -symbols -zinit -vmap {verbose_map} {aiger}",
            "",
        ]
    )
    return "\n".join(commands)


def parse_aiger_verbose_map(path: Path) -> dict[str, Any]:
    indexed_kinds = {"input", "init", "latch", "invlatch", "output"}
    records: dict[str, dict[int, set[tuple[int, str]]]] = {
        kind: defaultdict(set) for kind in indexed_kinds
    }
    exact_records: set[tuple[str, int, int, str]] = set()
    ninitff: int | None = None
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        fields = raw.split(maxsplit=3)
        if fields and fields[0] == "ninitff":
            if len(fields) != 2 or ninitff is not None:
                raise CampaignError(
                    f"malformed AIGER ninitff record {path}:{line_number}: {raw!r}"
                )
            try:
                ninitff = int(fields[1])
            except ValueError as exc:
                raise CampaignError(
                    f"non-numeric AIGER ninitff record {path}:{line_number}"
                ) from exc
            if ninitff < 0:
                raise CampaignError(f"negative AIGER ninitff record in {path}")
            continue
        if fields and fields[0] == "wire":
            if len(fields) != 4:
                raise CampaignError(
                    f"malformed AIGER wire record {path}:{line_number}: {raw!r}"
                )
            continue
        if len(fields) != 4 or fields[0] not in indexed_kinds:
            raise CampaignError(
                f"malformed AIGER verbose-map record {path}:{line_number}: {raw!r}"
            )
        kind, index_text, bit_text, name = fields
        try:
            index = int(index_text)
            bit = int(bit_text)
        except ValueError as exc:
            raise CampaignError(
                f"non-numeric AIGER map record {path}:{line_number}: {raw!r}"
            ) from exc
        if index < 0 or bit < 0 or not name:
            raise CampaignError(
                f"invalid AIGER map record {path}:{line_number}: {raw!r}"
            )
        record = (kind, index, bit, name)
        if record in exact_records:
            raise CampaignError(f"duplicate AIGER verbose-map record in {path}: {raw}")
        exact_records.add(record)
        records[kind][index].add((bit, name))
    if ninitff is None:
        raise CampaignError(f"AIGER verbose map omits ninitff: {path}")
    return {"records": records, "ninitff": ninitff}


def align_generic_aiger_interfaces(
    gold_aiger: Path,
    gate_aiger: Path,
    gold_map_path: Path,
    gate_map_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    gold_header = aiger_header(gold_aiger)
    gate_header = aiger_header(gate_aiger)
    for field in ("inputs", "latches", "outputs"):
        if gold_header[field] != gate_header[field]:
            raise CampaignError(
                f"generic AIGER {field} differ: {gold_header[field]} versus "
                f"{gate_header[field]}"
            )
    gold_map = parse_aiger_verbose_map(gold_map_path)
    gate_map = parse_aiger_verbose_map(gate_map_path)
    if gold_map["ninitff"] != gate_map["ninitff"]:
        raise CampaignError("generic AIGER ninitff counts differ")
    for kind in ("input", "init", "latch", "invlatch", "output"):
        if gold_map["records"][kind] != gate_map["records"][kind]:
            gold_indices = set(gold_map["records"][kind])
            gate_indices = set(gate_map["records"][kind])
            differing = sorted(
                index
                for index in gold_indices | gate_indices
                if gold_map["records"][kind].get(index)
                != gate_map["records"][kind].get(index)
            )
            raise CampaignError(
                f"generic AIGER {kind} maps differ at indices {differing[:8]}"
            )
    records = gold_map["records"]
    external_inputs = len(records["input"])
    if set(records["input"]) != set(range(external_inputs)):
        raise CampaignError("generic AIGER primary-input indices are not contiguous")
    arbitrary_inputs = gold_header["inputs"] - external_inputs
    if arbitrary_inputs < 0 or set(records["init"]) != set(
        range(external_inputs, gold_header["inputs"])
    ):
        raise CampaignError("generic AIGER arbitrary-init input accounting failed")
    state_bits = int(gold_map["ninitff"])
    latch_indices = set(records["latch"])
    inverted_latch_indices = set(records["invlatch"])
    if latch_indices & inverted_latch_indices or (
        latch_indices | inverted_latch_indices
    ) != set(range(state_bits)):
        raise CampaignError("generic AIGER state-index accounting failed")
    if gold_header["latches"] != state_bits + 1:
        raise CampaignError(
            "generic AIGER must contain proof state plus one zinit control latch"
        )
    output_indices = set(records["output"])
    if output_indices - set(range(gold_header["outputs"])):
        raise CampaignError("generic AIGER output map has out-of-range indices")
    alignment = {
        "status": "pass",
        "gold_header": gold_header,
        "gate_header": gate_header,
        "external_input_bits": external_inputs,
        "arbitrary_initial_state_input_bits": arbitrary_inputs,
        "state_bits": state_bits,
        "ordinary_state_indices": len(latch_indices),
        "inverted_state_indices": len(inverted_latch_indices),
        "state_alias_records": sum(
            len(aliases)
            for kind in ("latch", "invlatch")
            for aliases in records[kind].values()
        ),
        "output_bits": gold_header["outputs"],
        "named_nonconstant_output_bits": len(output_indices),
        "constant_output_bits": gold_header["outputs"] - len(output_indices),
        "policy": (
            "Exact primary-input, arbitrary-init-input, state-index/alias, and "
            "primary-output maps match before proof."
        ),
    }
    return alignment, gold_map, gate_map


def validate_generic_aiger_warnings(
    warnings: list[str],
    case: dict[str, Any],
    policy: dict[str, Any],
    verbose_map: dict[str, Any],
) -> dict[str, Any]:
    remaining: list[str] = []
    undriven: list[tuple[str, int]] = []
    total_records: list[int] = []
    input_bits = {
        (name, bit)
        for aliases in verbose_map["records"]["input"].values()
        for bit, name in aliases
    }
    for warning in warnings:
        bit_match = AIGER_UNDRIVEN_BIT_RE.fullmatch(warning)
        if bit_match is not None:
            if bit_match.group("top") != case["top"]:
                raise CampaignError(f"{case['name']}: AIGER warning names wrong top")
            item = (
                bit_match.group("port"),
                int(bit_match.group("bit") or 0),
            )
            if item not in input_bits or item in undriven:
                raise CampaignError(
                    f"{case['name']}: invalid AIGER undriven-input warning {item}"
                )
            undriven.append(item)
            continue
        total_match = AIGER_UNDRIVEN_TOTAL_RE.fullmatch(warning)
        if total_match is not None:
            if total_match.group("top") != case["top"]:
                raise CampaignError(f"{case['name']}: AIGER total names wrong top")
            total_records.append(int(total_match.group("count")))
            continue
        remaining.append(warning)
    if undriven:
        if total_records != [len(undriven)]:
            raise CampaignError(
                f"{case['name']}: AIGER undriven-input total is inconsistent"
            )
    elif total_records:
        raise CampaignError(f"{case['name']}: stale AIGER undriven-input total")
    summary = validate_warnings(remaining, case, policy, allow_abc=False)
    summary["count"] = len(warnings)
    summary["counts"] = dict(sorted(Counter(warnings).items()))
    summary["aiger_unused_primary_input_bits"] = [
        {"port": port, "bit": bit} for port, bit in sorted(undriven)
    ]
    summary["aiger_disposition"] = (
        "The verbose map proves each listed undriven bit is a retained primary "
        "input with the same index on both proof sides; AIGER models it as a "
        "shared arbitrary input."
    )
    return summary


def read_binary_aiger_sections(
    path: Path,
) -> tuple[dict[str, int], list[bytes], list[bytes], bytes]:
    data = path.read_bytes()
    try:
        header_end = data.index(b"\n") + 1
    except ValueError as exc:
        raise CampaignError(f"binary AIGER omits header newline: {path}") from exc
    header = aiger_header(path)
    if header["maximum_variable"] != (
        header["inputs"] + header["latches"] + header["and_nodes"]
    ):
        raise CampaignError(f"binary AIGER variable accounting failed: {path}")
    offset = header_end

    def ascii_lines(count: int, label: str, pattern: bytes) -> list[bytes]:
        nonlocal offset
        lines: list[bytes] = []
        for _ in range(count):
            try:
                end = data.index(b"\n", offset) + 1
            except ValueError as exc:
                raise CampaignError(
                    f"binary AIGER truncates {label} records: {path}"
                ) from exc
            line = data[offset:end]
            if re.fullmatch(pattern, line) is None:
                raise CampaignError(
                    f"binary AIGER has malformed {label} record in {path}"
                )
            lines.append(line)
            offset = end
        return lines

    latch_lines = ascii_lines(
        header["latches"], "latch", rb"[0-9]+(?: [0-9]+)?\n"
    )
    output_lines = ascii_lines(header["outputs"], "output", rb"[0-9]+\n")
    and_start = offset
    for _ in range(2 * header["and_nodes"]):
        while True:
            if offset >= len(data):
                raise CampaignError(f"binary AIGER truncates AND data: {path}")
            byte = data[offset]
            offset += 1
            if byte & 0x80 == 0:
                break
    return header, latch_lines, output_lines, data[and_start:offset]


def write_binary_aiger_output_subset(
    source: Path, destination: Path, first_output: int, last_output: int
) -> dict[str, int]:
    header, latch_lines, output_lines, and_data = read_binary_aiger_sections(source)
    if not 0 <= first_output < last_output <= header["outputs"]:
        raise CampaignError(
            f"invalid AIGER output range [{first_output}, {last_output})"
        )
    chosen_outputs = output_lines[first_output:last_output]
    new_header = (
        f"aig {header['maximum_variable']} {header['inputs']} "
        f"{header['latches']} {len(chosen_outputs)} {header['and_nodes']}\n"
    ).encode("ascii")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(
        new_header + b"".join(latch_lines) + b"".join(chosen_outputs) + and_data
    )
    parsed = aiger_header(destination)
    expected = dict(header)
    expected["outputs"] = len(chosen_outputs)
    if parsed != expected:
        raise CampaignError(f"AIGER output-subset header failed for {destination}")
    return parsed


def partitioned_abc_dsec(
    case: dict[str, Any],
    proof_dir: Path,
    gold_aiger: Path,
    gate_aiger: Path,
    output_bits: int,
    policy: dict[str, Any],
) -> dict[str, Any]:
    partition_root = proof_dir / "partitions"
    initial_width = int(policy["initial_output_partition_bits"])
    minimum_width = int(policy["minimum_output_partition_bits"])
    pending = [
        (first, min(first + initial_width, output_bits), 0)
        for first in range(0, output_bits, initial_width)
    ]
    attempts: list[dict[str, Any]] = []
    passed: list[dict[str, Any]] = []
    while pending:
        first, last, depth = pending.pop(0)
        tag = f"outputs_{first:04d}_{last:04d}"
        attempt_dir = partition_root / tag
        gold_subset = attempt_dir / "gold.aig"
        gate_subset = attempt_dir / "gate.aig"
        log = attempt_dir / "abc_dsec.log"
        gold_counts = write_binary_aiger_output_subset(
            gold_aiger, gold_subset, first, last
        )
        gate_counts = write_binary_aiger_output_subset(
            gate_aiger, gate_subset, first, last
        )
        if any(
            gold_counts[field] != gate_counts[field]
            for field in ("inputs", "latches", "outputs")
        ):
            raise CampaignError(
                f"{case['name']}: partition {first}:{last} AIGER interfaces differ"
            )
        timeout_s = int(policy["abc_timeout_seconds"])
        abc_command = (
            f"dsec -T {timeout_s} -v {gold_subset.resolve()} "
            f"{gate_subset.resolve()}"
        )
        print(
            f"[{case['name']}] generic dsec outputs {first}:{last}", flush=True
        )
        run_logged(
            [str(DEFAULT_ABC), "-c", abc_command],
            log,
            cwd=attempt_dir,
            timeout_s=int(policy["outer_process_timeout_seconds"]),
        )
        text = log.read_text(encoding="utf-8", errors="replace")
        final_results = re.findall(
            r"^Networks are (equivalent|NOT EQUIVALENT|UNDECIDED)\."
            r"\s+Time =\s*([0-9.]+) sec$",
            text,
            flags=re.MULTILINE,
        )
        if len(final_results) != 1 or "Warning:" in text:
            raise CampaignError(
                f"{case['name']}: partition {first}:{last} has malformed dsec result"
            )
        result_text, elapsed_text = final_results[0]
        miter = re.search(
            r"Original miter:\s+Latches =\s*([0-9]+)\. "
            r"Nodes =\s*([0-9]+)\.",
            text,
        )
        if miter is None:
            raise CampaignError(
                f"{case['name']}: partition {first}:{last} omits miter metrics"
            )
        status = {
            "equivalent": "pass",
            "UNDECIDED": "undecided",
            "NOT EQUIVALENT": "fail",
        }[result_text]
        reduced_miter = attempt_dir / "sm01.aig"
        attempt = {
            "first_output_bit": first,
            "last_output_bit_exclusive": last,
            "output_bits": last - first,
            "split_depth": depth,
            "status": status,
            "elapsed_seconds": float(elapsed_text),
            "original_miter_latches": int(miter.group(1)),
            "original_miter_nodes": int(miter.group(2)),
            "artifacts": {
                "gold_aiger": artifact(gold_subset),
                "gate_aiger": artifact(gate_subset),
                "abc_dsec_log": artifact(log),
            },
        }
        if reduced_miter.is_file():
            attempt["artifacts"]["undecided_reduced_miter"] = artifact(reduced_miter)
        attempts.append(attempt)
        if status == "pass":
            passed.append(attempt)
            continue
        if status == "fail":
            raise CampaignError(
                f"{case['name']}: ABC found outputs {first}:{last} non-equivalent"
            )
        width = last - first
        if width <= minimum_width:
            raise CampaignError(
                f"{case['name']}: output partition {first}:{last} remains undecided"
            )
        midpoint = first + width // 2
        if midpoint <= first or midpoint >= last:
            raise CampaignError(f"{case['name']}: cannot bisect {first}:{last}")
        pending[0:0] = [(first, midpoint, depth + 1), (midpoint, last, depth + 1)]
    passed.sort(key=lambda item: item["first_output_bit"])
    cursor = 0
    for item in passed:
        if item["first_output_bit"] != cursor:
            raise CampaignError(f"{case['name']}: generic output coverage has a gap")
        cursor = item["last_output_bit_exclusive"]
    if cursor != output_bits:
        raise CampaignError(f"{case['name']}: generic output coverage is incomplete")
    return {
        "status": "pass",
        "covered_output_bits": cursor,
        "required_output_bits": output_bits,
        "passing_partitions": len(passed),
        "total_attempts": len(attempts),
        "recursive_splits": len(attempts) - len(passed),
        "maximum_split_depth": max(item["split_depth"] for item in attempts),
        "maximum_attempt_seconds": max(item["elapsed_seconds"] for item in attempts),
        "passing_elapsed_seconds_sum": sum(
            item["elapsed_seconds"] for item in passed
        ),
        "attempts": attempts,
    }


def stage_generic_equivalence(
    case: dict[str, Any], case_dir: Path, spec: dict[str, Any]
) -> dict[str, Any]:
    proof_dir = case_dir / "equivalence_generic"
    proof_dir.mkdir(parents=True, exist_ok=True)
    gold_script = proof_dir / "gold_aiger.ys"
    gate_script = proof_dir / "gate_aiger.ys"
    gold_aiger = proof_dir / "gold.aig"
    gate_aiger = proof_dir / "gate.aig"
    gold_map = proof_dir / "gold.vmap"
    gate_map = proof_dir / "gate.vmap"
    gold_log = proof_dir / "gold_aiger.log"
    gate_log = proof_dir / "gate_aiger.log"
    alignment_path = proof_dir / "interface_state_alignment.json"
    write_text(
        gold_script,
        generic_aiger_script(
            case, gold_aiger, gold_map, synthesize=False
        ),
    )
    write_text(
        gate_script,
        generic_aiger_script(
            case, gate_aiger, gate_map, synthesize=True
        ),
    )
    print(f"[{case['name']}] full-stage generic AIG normalization", flush=True)
    run_logged([str(DEFAULT_YOSYS), "-s", str(gold_script)], gold_log)
    run_logged([str(DEFAULT_YOSYS), "-s", str(gate_script)], gate_log)
    alignment, gold_verbose_map, gate_verbose_map = align_generic_aiger_interfaces(
        gold_aiger, gate_aiger, gold_map, gate_map
    )
    write_text(alignment_path, json.dumps(alignment, indent=2, sort_keys=True) + "\n")
    warnings = {
        "gold": validate_generic_aiger_warnings(
            warning_lines(gold_log),
            case,
            spec["warning_policy"],
            gold_verbose_map,
        ),
        "gate": validate_generic_aiger_warnings(
            warning_lines(gate_log),
            case,
            spec["warning_policy"],
            gate_verbose_map,
        ),
    }
    policy = spec["generic_equivalence_policy"]
    partitions = partitioned_abc_dsec(
        case,
        proof_dir,
        gold_aiger,
        gate_aiger,
        alignment["output_bits"],
        policy,
    )
    return {
        "status": "pass",
        "method": policy["stage_control_method"],
        "arbitrary_common_initial_state": True,
        "undefined_state_policy": policy["undefined_state_policy"],
        "interface_alignment": alignment,
        "proven_points": alignment["output_bits"],
        "unproven_points": 0,
        "partition_proof": partitions,
        "warnings": warnings,
        "artifacts": {
            "gold_script": artifact(gold_script),
            "gate_script": artifact(gate_script),
            "gold_log": artifact(gold_log),
            "gate_log": artifact(gate_log),
            "gold_aiger": artifact(gold_aiger),
            "gate_aiger": artifact(gate_aiger),
            "gold_verbose_map": artifact(gold_map),
            "gate_verbose_map": artifact(gate_map),
            "interface_state_alignment": artifact(alignment_path),
        },
    }


def generic_equivalence(
    case: dict[str, Any], case_dir: Path, spec: dict[str, Any]
) -> dict[str, Any]:
    if case["kind"] == "stage_control":
        return stage_generic_equivalence(case, case_dir, spec)
    proof_dir = case_dir / "equivalence_generic"
    proof_dir.mkdir(parents=True, exist_ok=True)
    script = proof_dir / "equivalence.ys"
    write_text(script, equivalence_script(case))
    log = proof_dir / "equivalence.log"
    print(f"[{case['name']}] RTL-to-generic equivalence", flush=True)
    run_logged([str(DEFAULT_YOSYS), "-s", str(script)], log)
    warning_summary = validate_warnings(
        warning_lines(log), case, spec["warning_policy"], allow_abc=False
    )
    text = log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"Of those cells\s+([0-9]+) are proven and ([0-9]+) are unproven", text
    )
    if "Equivalence successfully proven!" not in text or not matches:
        raise CampaignError(f"{case['name']}: generic equivalence lacks proof closure")
    proven, unproven = map(int, matches[-1])
    if unproven != 0:
        raise CampaignError(f"{case['name']}: {unproven} generic equivalence points open")
    return {
        "status": "pass",
        "method": "Yosys equiv_opt with induction after proc/memory/flatten/async2sync/opt",
        "proven_points": proven,
        "unproven_points": unproven,
        "warnings": warning_summary,
        "artifacts": {"script": artifact(script), "log": artifact(log)},
    }


def mapped_equivalence_script(case: dict[str, Any], netlist: Path) -> str:
    sources = " ".join(case["sources"])
    liberty = DEFAULT_PDK / LIBERTY_NAME
    top = case["top"]
    return "\n".join(
        [
            f"read_verilog -sv -DSYNTHESIS {sources}",
            f"hierarchy -check -top {top} {parameter_args(case)}",
            "proc",
            "memory",
            "flatten",
            "async2sync",
            "opt",
            f"rename {top} gold",
            f"read_liberty -ignore_miss_func -ignore_miss_data_latch {liberty}",
            f"read_verilog {netlist}",
            "proc",
            f"flatten {top}",
            f"async2sync {top}",
            f"opt {top}",
            f"rename {top} gate",
            "equiv_make gold gate equiv",
            "hierarchy -top equiv",
            "equiv_simple",
            "equiv_induct",
            "equiv_status -assert",
            "",
        ]
    )


def mapped_equivalence(
    case: dict[str, Any], case_dir: Path, netlist: Path, spec: dict[str, Any]
) -> dict[str, Any]:
    proof_dir = case_dir / "equivalence_mapped"
    proof_dir.mkdir(parents=True, exist_ok=True)
    script = proof_dir / "equivalence.ys"
    write_text(script, mapped_equivalence_script(case, netlist))
    log = proof_dir / "equivalence.log"
    print(f"[{case['name']}] RTL-to-mapped-netlist equivalence", flush=True)
    run_logged([str(DEFAULT_YOSYS), "-s", str(script)], log)
    warning_summary = validate_warnings(
        warning_lines(log), case, spec["warning_policy"], allow_abc=False
    )
    text = log.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"Of those cells\s+([0-9]+) are proven and ([0-9]+) are unproven", text
    )
    if "Equivalence successfully proven!" not in text or not matches:
        raise CampaignError(f"{case['name']}: mapped equivalence lacks proof closure")
    proven, unproven = map(int, matches[-1])
    if unproven != 0:
        raise CampaignError(f"{case['name']}: {unproven} mapped equivalence points open")
    return {
        "status": "pass",
        "method": "RTL versus actual ABC-mapped netlist with Liberty functions and async2sync",
        "proven_points": proven,
        "unproven_points": unproven,
        "warnings": warning_summary,
        "artifacts": {"script": artifact(script), "log": artifact(log)},
    }


def netlist_ports(netlist_json: Path, top: str) -> dict[str, dict[str, Any]]:
    data = strict_json(netlist_json)
    modules = data.get("modules", {})
    module = modules.get(top) or modules.get(f"\\{top}")
    if not isinstance(module, dict) or not isinstance(module.get("ports"), dict):
        raise CampaignError(f"{netlist_json}: missing top-level ports for {top}")
    return module["ports"]


def port_pattern(name: str, ports: dict[str, dict[str, Any]]) -> str:
    if name not in ports:
        raise CampaignError(f"constraint manifest names absent port {name}")
    width = len(ports[name].get("bits", []))
    return name if width == 1 else f"{name}*"


def brace_patterns(names: Iterable[str], ports: dict[str, dict[str, Any]]) -> str:
    return "{" + " ".join(port_pattern(name, ports) for name in names) + "}"


def constraint_groups(
    case: dict[str, Any], ports: dict[str, dict[str, Any]]
) -> tuple[dict[str, dict[str, list[str]]], list[str], list[str]]:
    if case["kind"] == "numeric":
        expected = {
            "clk",
            "rst_n",
            "in_valid",
            "in_poison",
            "expert_enable",
            "activations",
            "weights",
            "out_valid",
            "out_poison",
            "result",
            "status",
        }
        if set(ports) != expected:
            raise CampaignError(
                f"{case['name']}: numeric constraint inventory mismatch "
                f"missing={sorted(set(ports) - expected)} stale={sorted(expected - set(ports))}"
            )
        groups = {
            "clk": {
                "inputs": [
                    "rst_n",
                    "in_valid",
                    "in_poison",
                    "expert_enable",
                    "activations",
                    "weights",
                ],
                "outputs": ["out_valid", "out_poison", "result", "status"],
            }
        }
        return groups, ["clk"], ["rst_n"]

    crossing = strict_json(CDC_SPEC)
    groups = {
        "aon_clk": {"inputs": [], "outputs": []},
        "core_clk": {"inputs": [], "outputs": []},
    }
    clocks: list[str] = []
    resets: list[str] = []
    accounted: set[str] = set()
    domain_clock = {"aon_cfg": "aon_clk", "core": "core_clk"}
    for group in crossing["stage_top_port_groups"]:
        classification = group["classification"]
        signals = group["signals"]
        if classification == "clock":
            clocks.extend(signals)
            accounted.update(signals)
        elif classification == "reset":
            resets.extend(signals)
            accounted.update(signals)
        elif classification == "functional":
            clock = domain_clock[group["domain"]]
            direction = "inputs" if group["direction"] == "input" else "outputs"
            groups[clock][direction].extend(signals)
            accounted.update(signals)
    groups["aon_clk"]["inputs"].append("aon_rst_n")
    groups["core_clk"]["inputs"].append("core_rst_n")
    if accounted != set(ports):
        raise CampaignError(
            f"{case['name']}: stage constraint inventory mismatch "
            f"unaccounted={sorted(set(ports) - accounted)} stale={sorted(accounted - set(ports))}"
        )
    return groups, clocks, resets


def sdc_text(
    case: dict[str, Any],
    ports: dict[str, dict[str, Any]],
    constraint: dict[str, Any],
    *,
    include_reset_exceptions: bool,
) -> str:
    groups, clocks, resets = constraint_groups(case, ports)
    periods = (
        {"clk": float(constraint["core_period_ns"])}
        if case["kind"] == "numeric"
        else {
            "aon_clk": float(constraint["aon_period_ns"]),
            "core_clk": float(constraint["core_period_ns"]),
        }
    )
    lines = [f"current_design {case['top']}"]
    lines.append(f"set_max_fanout {float(spec_number('max_fanout')):.6f} [current_design]")
    for clock in clocks:
        lines.append(
            f"create_clock -name {clock} -period {periods[clock]:.6f} [get_ports {clock}]"
        )
        lines.append(
            "set_clock_uncertainty -setup "
            f"{periods[clock] * float(constraint['setup_uncertainty_fraction']):.6f} "
            f"[get_clocks {clock}]"
        )
    if len(clocks) > 1:
        lines.append(
            "set_clock_groups -asynchronous "
            + " ".join(f"-group [get_clocks {clock}]" for clock in clocks)
        )
    for clock, directions in groups.items():
        period = periods[clock]
        inputs = brace_patterns(directions["inputs"], ports)
        outputs = brace_patterns(directions["outputs"], ports)
        lines.extend(
            [
                f"set_input_delay -max {period * float(constraint['input_delay_fraction']):.6f} -clock {clock} [get_ports {inputs}]",
                f"set_input_delay -min {period * float(constraint['input_delay_min_fraction']):.6f} -clock {clock} [get_ports {inputs}]",
                f"set_input_transition {float(spec_number('input_transition_ns')):.6f} [get_ports {inputs}]",
                f"set_output_delay -max {period * float(constraint['output_delay_fraction']):.6f} -clock {clock} [get_ports {outputs}]",
                f"set_output_delay -min {period * float(constraint['output_delay_min_fraction']):.6f} -clock {clock} [get_ports {outputs}]",
                f"set_load {float(spec_number('output_load_pf')):.6f} [get_ports {outputs}]",
            ]
        )
    if include_reset_exceptions:
        for reset in resets:
            lines.append(f"set_false_path -from [get_ports {reset}]")
    lines.append("")
    return "\n".join(lines)


_ACTIVE_CONSTRAINT_SPEC: dict[str, Any] | None = None


def spec_number(field: str) -> float:
    if _ACTIVE_CONSTRAINT_SPEC is None:
        raise CampaignError("internal error: constraint spec is not active")
    value = _ACTIVE_CONSTRAINT_SPEC.get(field)
    if not isinstance(value, (int, float)):
        raise CampaignError(f"constraints.{field} must be numeric")
    return float(value)


def sanitize_netlist(source: Path, destination: Path) -> int:
    text = source.read_text(encoding="utf-8")
    sanitized, count = re.subn(r"\b(input|output|wire) signed\b", r"\1", text)
    write_text(destination, sanitized)
    return count


def sta_tcl(top: str, netlist: Path, sdc: Path, report_dir: Path, *, power: bool) -> str:
    liberty = DEFAULT_PDK / LIBERTY_NAME
    lines = [
        f"read_liberty {liberty}",
        f"read_verilog {netlist}",
        f"link_design {top}",
        f"read_sdc {sdc}",
        f"check_setup -verbose > {report_dir / 'check_setup.rpt'}",
        f"report_checks -path_delay max -group_path_count 20 -endpoint_path_count 1 -sort_by_slack -format full_clock_expanded -fields {{capacitance slew fanout input_pin net}} -digits 4 > {report_dir / 'max_paths.rpt'}",
        f"report_checks -path_delay min -group_path_count 20 -endpoint_path_count 1 -sort_by_slack -format full_clock_expanded -fields {{capacitance slew fanout input_pin net}} -digits 4 > {report_dir / 'min_paths.rpt'}",
        f"report_check_types -max_slew -max_fanout -max_capacitance -violators -verbose -digits 4 > {report_dir / 'electrical.rpt'}",
        f"report_check_types -recovery -removal -violators -verbose -digits 4 > {report_dir / 'recovery_removal.rpt'}",
        "report_worst_slack -max -digits 6",
        "report_tns -max -digits 6",
        "report_worst_slack -min -digits 6",
        "report_tns -min -digits 6",
    ]
    if power:
        lines.extend(
            [
                "set_power_activity -global -activity 0.1 -duty 0.5",
                f"report_power -digits 8 > {report_dir / 'vectorless_power.rpt'}",
            ]
        )
    lines.append("exit")
    lines.append("")
    return "\n".join(lines)


def parse_sta_log(log: Path) -> dict[str, float]:
    text = log.read_text(encoding="utf-8", errors="replace")
    if re.search(r"(?m)^Error:", text) or "invalid command name" in text:
        raise CampaignError(f"OpenSTA error in {log}:\n{text}")
    values: dict[str, float] = {}
    patterns = {
        "setup_wns_ns": r"worst slack max\s+([-+0-9.eE]+)",
        "setup_tns_ns": r"tns max\s+([-+0-9.eE]+)",
        "minimum_wns_ns": r"worst slack min\s+([-+0-9.eE]+)",
        "minimum_tns_ns": r"tns min\s+([-+0-9.eE]+)",
    }
    for key, pattern in patterns.items():
        matches = re.findall(pattern, text)
        if not matches:
            raise CampaignError(f"OpenSTA log {log} omits {key}")
        values[key] = float(matches[-1])
    return values


def check_setup_counts(report: Path) -> dict[str, int]:
    text = report.read_text(encoding="utf-8", errors="replace")
    categories = {
        "missing_input_delay": r"There are ([0-9]+) input ports missing set_input_delay",
        "missing_output_delay": r"There are ([0-9]+) output ports missing set_output_delay",
        "multiple_clock": r"There are ([0-9]+) (?:pins|registers).*multiple clock",
        "no_clock": r"There are ([0-9]+) (?:pins|registers).*no clock",
        "unconstrained_endpoints": r"There are ([0-9]+) unconstrained endpoints",
        "loops": r"There are ([0-9]+) combinational loops",
    }
    return {
        key: sum(int(value) for value in re.findall(pattern, text, flags=re.IGNORECASE))
        for key, pattern in categories.items()
    }


def parse_power(report: Path) -> dict[str, float | str]:
    if not report.is_file():
        return {}
    text = report.read_text(encoding="utf-8", errors="replace")
    match = re.search(
        r"(?m)^Total\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)\s+([0-9.eE+-]+)",
        text,
    )
    if not match:
        return {"status": "not_reported"}
    internal, switching, leakage, total = map(float, match.groups())
    return {
        "status": "illustrative_vectorless_only",
        "internal_w": internal,
        "switching_w": switching,
        "leakage_w": leakage,
        "total_w": total,
        "limitations": "Ideal clock network reports zero clock power; no activity trace, extracted parasitics, macros, or product voltage/frequency model.",
    }


def run_sta_scenario(
    case: dict[str, Any],
    sta_dir: Path,
    netlist: Path,
    ports: dict[str, dict[str, Any]],
    constraint: dict[str, Any],
    scenario: str,
    *,
    include_reset_exceptions: bool,
    power: bool,
) -> dict[str, Any]:
    scenario_dir = sta_dir / scenario
    scenario_dir.mkdir(parents=True, exist_ok=True)
    sdc = scenario_dir / "constraints.sdc"
    write_text(
        sdc,
        sdc_text(
            case,
            ports,
            constraint,
            include_reset_exceptions=include_reset_exceptions,
        ),
    )
    tcl = scenario_dir / "sta.tcl"
    write_text(tcl, sta_tcl(case["top"], netlist, sdc, scenario_dir, power=power))
    log = scenario_dir / "sta.log"
    run_logged([str(DEFAULT_OPENSTA), "-no_splash", "-exit", str(tcl)], log)
    metrics = parse_sta_log(log)
    setup = check_setup_counts(scenario_dir / "check_setup.rpt")
    artifacts = {
        "constraints": artifact(sdc),
        "script": artifact(tcl),
        "log": artifact(log),
        "check_setup": artifact(scenario_dir / "check_setup.rpt"),
        "max_paths": artifact(scenario_dir / "max_paths.rpt"),
        "min_paths": artifact(scenario_dir / "min_paths.rpt"),
        "electrical": artifact(scenario_dir / "electrical.rpt"),
        "recovery_removal": artifact(scenario_dir / "recovery_removal.rpt"),
    }
    if power:
        artifacts["vectorless_power"] = artifact(scenario_dir / "vectorless_power.rpt")
    return {
        "status": "pass",
        **metrics,
        "constraint_coverage": setup,
        "reset_exceptions": (
            list(_ACTIVE_CONSTRAINT_SPEC["external_reset_exceptions"])
            if include_reset_exceptions and case["kind"] == "stage_control"
            else (["rst_n"] if include_reset_exceptions else [])
        ),
        "vectorless_power": parse_power(scenario_dir / "vectorless_power.rpt"),
        "artifacts": artifacts,
    }


def sta_case(
    case: dict[str, Any], case_dir: Path, synthesis: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    global _ACTIVE_CONSTRAINT_SPEC
    _ACTIVE_CONSTRAINT_SPEC = spec["constraints"]
    sta_dir = case_dir / "sta"
    sta_dir.mkdir(parents=True, exist_ok=True)
    source_netlist = synthesis["paths"]["netlist"]
    netlist = sta_dir / "netlist_sta.v"
    signed_tokens_removed = sanitize_netlist(source_netlist, netlist)
    ports = netlist_ports(synthesis["paths"]["netlist_json"], case["top"])
    print(f"[{case['name']}] proxy and architectural STA", flush=True)
    proxy = run_sta_scenario(
        case,
        sta_dir,
        netlist,
        ports,
        spec["constraints"]["proxy_setup"],
        "proxy_100mhz",
        include_reset_exceptions=True,
        power=True,
    )
    diagnostic = run_sta_scenario(
        case,
        sta_dir,
        netlist,
        ports,
        spec["constraints"]["architectural_diagnostic"],
        "architectural_diagnostic",
        include_reset_exceptions=True,
        power=False,
    )
    reset_audit = run_sta_scenario(
        case,
        sta_dir,
        netlist,
        ports,
        spec["constraints"]["proxy_setup"],
        "reset_minimum_delay_audit",
        include_reset_exceptions=False,
        power=False,
    )
    acceptance = spec["acceptance"]
    setup_required = case["name"] in acceptance["prelayout_setup_required_cases"]
    setup_pass = (
        proxy["setup_wns_ns"] >= acceptance["proxy_setup_wns_ns_min"]
        and proxy["setup_tns_ns"] <= acceptance["proxy_setup_tns_ns_max"]
    )
    if setup_required and not setup_pass:
        raise CampaignError(
            f"{case['name']}: required pre-layout proxy setup fails: "
            f"WNS {proxy['setup_wns_ns']} ns, TNS {proxy['setup_tns_ns']} ns"
        )
    coverage = proxy["constraint_coverage"]
    if coverage["unconstrained_endpoints"] > acceptance["unconstrained_endpoints_max"]:
        raise CampaignError(f"{case['name']}: unconstrained endpoints {coverage}")
    if any(coverage.values()):
        raise CampaignError(f"{case['name']}: incomplete/invalid STA constraints {coverage}")
    return {
        "status": "pass" if (setup_pass or not setup_required) else "fail",
        "prelayout_setup_gate": {
            "required": setup_required,
            "pass": setup_pass,
            "disposition": (
                "required_pass"
                if setup_required and setup_pass
                else "diagnostic_pass"
                if setup_pass
                else "diagnostic_fail_requires_physical_buffering_or_architecture_change"
            ),
        },
        "netlist_sanitization": {
            "signed_declarations_removed": signed_tokens_removed,
            "reason": "OpenSTA Verilog parser compatibility; signedness is semantically inert after bit-level technology mapping.",
            "artifact": artifact(netlist),
        },
        "proxy_100mhz": proxy,
        "architectural_diagnostic": diagnostic,
        "reset_minimum_delay_audit": reset_audit,
        "minimum_delay_disposition": spec["constraints"]["minimum_delay_policy"],
        "reset_release_obligation": spec["constraints"]["reset_release_obligation"],
        "prelayout_timing_policy": spec["prelayout_timing_policy"],
    }


def physical_config(case: dict[str, Any], spec: dict[str, Any]) -> str:
    physical = case["physical_proxy"]
    policy = spec["physical_flow_policy"]
    sources = " ".join(f"/src/{source}" for source in case["sources"])
    params = " ".join(
        f"{key} {value}" for key, value in sorted(case["parameters"].items())
    )
    die = " ".join(f"{float(value):g}" for value in physical["die_area_um"])
    core = " ".join(f"{float(value):g}" for value in physical["core_area_um"])
    return "\n".join(
        [
            f"export DESIGN_NICKNAME = opentallas_{case['name']}",
            f"export DESIGN_NAME = {case['top']}",
            "export PLATFORM = nangate45",
            f"export VERILOG_FILES = {sources}",
            "export VERILOG_DEFINES = -DSYNTHESIS",
            f"export VERILOG_TOP_PARAMS = {params}",
            "export SDC_FILE = /work/constraint.sdc",
            f"export DIE_AREA = {die}",
            f"export CORE_AREA = {core}",
            f"export PLACE_DENSITY = {float(physical['place_density']):g}",
            "export SYNTH_REPEATABLE_BUILD = 1",
            f"export LEC_CHECK = {1 if policy['orfs_kepler_lec']['enabled'] else 0}",
            f"export CAP_MARGIN = {float(policy['capacitance_margin']):g}",
            f"export HOLD_SLACK_MARGIN = {float(policy['hold_slack_margin_ns']):g}",
            f"export TNS_END_PERCENT = {float(policy['tns_end_percent']):g}",
            "export PLACE_DENSITY_LB_ADDON = "
            f"{float(policy['place_density_lower_bound_addon']):g}",
            "",
        ]
    )


def metadata_number(metadata: dict[str, Any], key: str) -> float:
    value = metadata.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CampaignError(f"physical metadata omits numeric {key}")
    result = float(value)
    if not math.isfinite(result):
        raise CampaignError(f"physical metadata has non-finite {key}={value!r}")
    return result


def physical_gate_metrics(
    case: dict[str, Any], metadata: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    keys = {
        "setup_wns_ns": "finish__timing__setup__ws",
        "setup_tns_ns": "finish__timing__setup__tns",
        "setup_violations": "finish__timing__drv__setup_violation_count",
        "hold_wns_ns": "finish__timing__hold__ws",
        "hold_tns_ns": "finish__timing__hold__tns",
        "hold_violations": "finish__timing__drv__hold_violation_count",
        "max_slew_violations": "finish__timing__drv__max_slew",
        "max_fanout_violations": "finish__timing__drv__max_fanout",
        "max_capacitance_violations": "finish__timing__drv__max_cap",
        "drc_errors": "detailedroute__route__drc_errors",
        "antenna_violating_nets": "detailedroute__antenna__violating__nets",
        "antenna_violating_pins": "detailedroute__antenna__violating__pins",
        "design_violations": "design__violations",
        "placement_violations": "detailedplace__design__violations",
        "reported_max_fanout_limit": "finish__timing__drv__max_fanout_limit",
        "core_area_um2": "finish__design__core__area",
        "die_area_um2": "finish__design__die__area",
        "instance_area_um2": "finish__design__instance__area",
        "standard_cell_area_um2": "finish__design__instance__area__stdcell",
        "utilization_fraction": "finish__design__instance__utilization",
        "wirelength_um": "detailedroute__route__wirelength",
        "vias": "detailedroute__route__vias",
        "fmax_hz": "finish__timing__fmax",
    }
    metrics = {name: metadata_number(metadata, key) for name, key in keys.items()}
    clock_count = metadata_number(metadata, "constraints__clocks__count")
    expected_clocks = 1 if case["kind"] == "numeric" else 2
    flow_error_counts = {
        key: int(metadata_number(metadata, key))
        for key in sorted(metadata)
        if key.endswith("__flow__errors__count")
    }
    if not flow_error_counts:
        raise CampaignError(f"{case['name']}: no physical flow-error metrics")
    metrics["flow_error_counts"] = flow_error_counts
    metrics["clock_count"] = int(clock_count)
    metrics["clock_details"] = metadata.get("constraints__clocks__details")
    acceptance = spec["acceptance"]
    failures: list[str] = []
    minimums = {
        "setup_wns_ns": acceptance["physical_setup_wns_ns_min"],
        "setup_tns_ns": acceptance["physical_setup_tns_ns_min"],
        "hold_wns_ns": acceptance["physical_hold_wns_ns_min"],
        "hold_tns_ns": acceptance["physical_hold_tns_ns_min"],
    }
    maximums = {
        "setup_violations": acceptance["physical_setup_violations_max"],
        "hold_violations": acceptance["physical_hold_violations_max"],
        "max_slew_violations": acceptance[
            "physical_max_slew_violations_max"
        ],
        "max_fanout_violations": acceptance[
            "physical_max_fanout_violations_max"
        ],
        "max_capacitance_violations": acceptance[
            "physical_max_capacitance_violations_max"
        ],
        "drc_errors": acceptance["physical_drc_errors_max"],
        "antenna_violating_nets": acceptance[
            "physical_antenna_violating_nets_max"
        ],
        "antenna_violating_pins": acceptance[
            "physical_antenna_violating_pins_max"
        ],
        "design_violations": acceptance["physical_design_violations_max"],
        "placement_violations": acceptance["physical_placement_violations_max"],
    }
    for field, threshold in minimums.items():
        if metrics[field] < threshold:
            failures.append(f"{field}={metrics[field]} < {threshold}")
    for field, threshold in maximums.items():
        if metrics[field] > threshold:
            failures.append(f"{field}={metrics[field]} > {threshold}")
    for key, count in flow_error_counts.items():
        if count > acceptance["physical_flow_errors_max"]:
            failures.append(
                f"{key}={count} > {acceptance['physical_flow_errors_max']}"
            )
    if int(clock_count) != expected_clocks:
        failures.append(f"clock_count={clock_count:g}, expected {expected_clocks}")
    if metrics["reported_max_fanout_limit"] != float(
        spec["constraints"]["max_fanout"]
    ):
        failures.append(
            "reported max-fanout limit "
            f"{metrics['reported_max_fanout_limit']} != "
            f"{spec['constraints']['max_fanout']}"
        )
    if failures:
        raise CampaignError(f"{case['name']}: physical gates failed: {failures}")
    return metrics


OPENROAD_MESSAGE_RE = re.compile(
    r"\[(?P<severity>WARNING|ERROR) (?P<code>[A-Z]{3}-[0-9]{4})\]"
)


def physical_warning_audit(
    case: dict[str, Any], flow_log: Path, metadata: dict[str, Any], spec: dict[str, Any]
) -> dict[str, Any]:
    text = flow_log.read_text(encoding="utf-8", errors="replace")
    warning_counts: Counter[str] = Counter()
    error_counts: Counter[str] = Counter()
    for match in OPENROAD_MESSAGE_RE.finditer(text):
        target = warning_counts if match.group("severity") == "WARNING" else error_counts
        target[match.group("code")] += 1
    if error_counts:
        raise CampaignError(f"{case['name']}: OpenROAD coded errors {dict(error_counts)}")
    metadata_counts: Counter[str] = Counter()
    for key, value in metadata.items():
        match = re.search(r"__flow__warnings__count__([A-Z]{3}-[0-9]{4})$", key)
        if match and isinstance(value, (int, float)) and value > 0:
            metadata_counts[match.group(1)] += int(value)
    observed = set(warning_counts) | set(metadata_counts)
    policy = spec["warning_policy"]["openroad"]
    forbidden = observed & set(policy["forbidden_codes"])
    if forbidden:
        raise CampaignError(
            f"{case['name']}: forbidden OpenROAD warnings {sorted(forbidden)}: "
            f"{policy['forbidden_code_disposition']}"
        )
    unexpected = observed - set(policy["allowed_codes"])
    if unexpected and policy["unexpected_codes_are_fatal"]:
        raise CampaignError(
            f"{case['name']}: unexpected OpenROAD warning codes {sorted(unexpected)}"
        )
    inapplicable = sorted(
        code
        for code in observed & set(policy["allowed_codes"])
        if case["kind"] not in policy["allowed_codes"][code]["case_kinds"]
    )
    if inapplicable:
        raise CampaignError(
            f"{case['name']}: warning codes not allowed for {case['kind']}: {inapplicable}"
        )
    return {
        "status": "pass",
        "observed_codes": sorted(observed),
        "flow_log_occurrences_by_code": dict(sorted(warning_counts.items())),
        "metadata_stage_occurrences_by_code": dict(sorted(metadata_counts.items())),
        "dispositions": {
            code: policy["allowed_codes"][code]["disposition"]
            for code in sorted(observed)
        },
        "unexpected_codes": [],
        "forbidden_codes": [],
    }


def endpoint_label(kind: str, owner: str, port: str, index: int) -> str:
    suffix = f"[{index}]" if index else ""
    return f"{kind}:{owner}.{port}{suffix}"


def final_netlist_connectivity_audit(
    case: dict[str, Any], physical_dir: Path, final_netlist: Path, spec: dict[str, Any]
) -> dict[str, Any]:
    audit_dir = physical_dir / "independent_audit"
    audit_dir.mkdir(parents=True, exist_ok=True)
    script = audit_dir / "final_netlist_json.ys"
    netlist_json = audit_dir / "final_netlist.json"
    liberty = DEFAULT_PDK / LIBERTY_NAME
    write_text(
        script,
        "\n".join(
            [
                f"read_liberty -lib {liberty}",
                f"read_verilog {final_netlist}",
                f"hierarchy -check -top {case['top']}",
                "check -assert",
                f"write_json {netlist_json}",
                "",
            ]
        ),
    )
    log = audit_dir / "final_netlist_json.log"
    run_logged([str(DEFAULT_YOSYS), "-s", str(script)], log)
    warnings = warning_lines(log)
    if warnings:
        raise CampaignError(
            f"{case['name']}: final-netlist structural import warnings {warnings}"
        )
    data = strict_json(netlist_json)
    module = data.get("modules", {}).get(case["top"]) or data.get("modules", {}).get(
        f"\\{case['top']}"
    )
    if not isinstance(module, dict):
        raise CampaignError(f"{case['name']}: final-netlist JSON omits top module")
    drivers: dict[int, list[str]] = defaultdict(list)
    loads: dict[int, list[str]] = defaultdict(list)
    aliases: dict[int, list[str]] = defaultdict(list)
    for name, net in module.get("netnames", {}).items():
        for bit in net.get("bits", []):
            if isinstance(bit, int):
                aliases[bit].append(name)
    top_ports = module.get("ports", {})
    for name, port in top_ports.items():
        direction = port.get("direction")
        if direction not in {"input", "output", "inout"}:
            raise CampaignError(f"{case['name']}: unknown top-port direction {name}")
        for index, bit in enumerate(port.get("bits", [])):
            if not isinstance(bit, int):
                continue
            if direction in {"input", "inout"}:
                drivers[bit].append(endpoint_label("top_input", case["top"], name, index))
            if direction in {"output", "inout"}:
                loads[bit].append(endpoint_label("top_output", case["top"], name, index))
    for cell_name, cell in module.get("cells", {}).items():
        directions = cell.get("port_directions", {})
        for port_name, bits in cell.get("connections", {}).items():
            direction = directions.get(port_name)
            if direction not in {"input", "output", "inout"}:
                raise CampaignError(
                    f"{case['name']}: no direction for {cell_name}.{port_name}"
                )
            for index, bit in enumerate(bits):
                if not isinstance(bit, int):
                    continue
                if direction in {"output", "inout"}:
                    drivers[bit].append(
                        endpoint_label("cell_output", cell_name, port_name, index)
                    )
                if direction in {"input", "inout"}:
                    loads[bit].append(
                        endpoint_label("cell_input", cell_name, port_name, index)
                    )
    used_bits = sorted(set(drivers) | set(loads))
    undriven = [bit for bit in used_bits if not drivers[bit] and loads[bit]]
    multiply_driven = [bit for bit in used_bits if len(drivers[bit]) > 1]
    dangling = [bit for bit in used_bits if drivers[bit] and not loads[bit]]
    cell_dangling = [
        bit
        for bit in dangling
        if len(drivers[bit]) == 1 and drivers[bit][0].startswith("cell_output:")
    ]
    top_input_dangling = [
        bit
        for bit in dangling
        if len(drivers[bit]) == 1 and drivers[bit][0].startswith("top_input:")
    ]
    expected_unloaded_labels: set[str] = set()
    for allowance in case["physical_proxy"]["allowed_unloaded_top_input_bits"]:
        port_name = allowance["port"]
        port = top_ports.get(port_name)
        if not isinstance(port, dict) or port.get("direction") != "input":
            raise CampaignError(
                f"{case['name']}: unloaded-input allowance names non-input {port_name}"
            )
        width = len(port.get("bits", []))
        if allowance["last_bit"] >= width:
            raise CampaignError(
                f"{case['name']}: unloaded-input allowance exceeds {port_name}[{width - 1}:0]"
            )
        for index in range(allowance["first_bit"], allowance["last_bit"] + 1):
            expected_unloaded_labels.add(
                endpoint_label("top_input", case["top"], port_name, index)
            )
    observed_unloaded_labels = {drivers[bit][0] for bit in top_input_dangling}
    unexpected_unloaded_labels = sorted(
        observed_unloaded_labels - expected_unloaded_labels
    )
    stale_unloaded_allowances = sorted(
        expected_unloaded_labels - observed_unloaded_labels
    )
    invalid_dangling = [
        bit
        for bit in dangling
        if bit not in cell_dangling and bit not in top_input_dangling
    ]
    max_loads = max((len(loads[bit]) for bit in used_bits), default=0)
    max_bits = [bit for bit in used_bits if len(loads[bit]) == max_loads]

    def examples(bits: list[int], limit: int = 20) -> list[dict[str, Any]]:
        return [
            {
                "bit": bit,
                "aliases": sorted(aliases.get(bit, []))[:4],
                "drivers": drivers[bit],
                "loads": loads[bit][:8],
                "load_count": len(loads[bit]),
            }
            for bit in bits[:limit]
        ]

    failures: list[str] = []
    if undriven:
        failures.append(f"{len(undriven)} loaded bits have no driver")
    if multiply_driven:
        failures.append(f"{len(multiply_driven)} bits have multiple drivers")
    if invalid_dangling:
        failures.append(f"{len(invalid_dangling)} invalid dangling drivers")
    if unexpected_unloaded_labels:
        failures.append(
            f"unexpected unloaded top inputs {unexpected_unloaded_labels}"
        )
    if stale_unloaded_allowances:
        failures.append(f"stale unloaded-input allowances {stale_unloaded_allowances}")
    if max_loads > int(spec["constraints"]["max_fanout"]):
        failures.append(
            f"structural max fanout {max_loads} exceeds "
            f"{spec['constraints']['max_fanout']}"
        )
    if failures:
        raise CampaignError(
            f"{case['name']}: final-netlist connectivity audit failed: {failures}; "
            f"undriven={examples(undriven)} multi={examples(multiply_driven)} "
            f"dangling={examples(invalid_dangling)} max={examples(max_bits)}"
        )
    return {
        "status": "pass",
        "used_net_bits": len(used_bits),
        "cell_count": len(module.get("cells", {})),
        "undriven_loaded_bits": 0,
        "multiply_driven_bits": 0,
        "allowed_single_unused_cell_outputs": len(cell_dangling),
        "allowed_dangling_examples": examples(cell_dangling),
        "allowed_unloaded_top_input_bits": sorted(observed_unloaded_labels),
        "max_structural_fanout": max_loads,
        "max_structural_fanout_limit": int(spec["constraints"]["max_fanout"]),
        "max_fanout_examples": examples(max_bits),
        "one_pin_rule": "Every permitted driver-only bit has exactly one cell-output endpoint, zero loads, and no top-level endpoint.",
        "artifacts": {
            "script": artifact(script),
            "log": artifact(log),
            "netlist_json": artifact(netlist_json),
        },
    }


def postroute_aiger_script(
    case: dict[str, Any], netlist: Path, aiger: Path, map_path: Path
) -> str:
    top = case["top"]
    liberty = DEFAULT_PDK / LIBERTY_NAME
    return "\n".join(
        [
            f"read_liberty -ignore_miss_func -ignore_miss_data_latch {liberty}",
            f"read_verilog {netlist}",
            f"hierarchy -top {top}",
            f"proc {top}",
            f"flatten -wb {top}",
            f"async2sync {top}",
            f"techmap {top}",
            f"dfflegalize -cell $_DFF_P_ x {top}",
            f"opt -nodffe -nosdff {top}",
            f"aigmap {top}",
            f"clean -purge {top}",
            f"check -assert {top}",
            f"write_aiger -symbols -zinit -map {map_path} {aiger}",
            "",
        ]
    )


def aiger_header(path: Path) -> dict[str, int]:
    try:
        with path.open("rb") as handle:
            fields = handle.readline().decode("ascii").strip().split()
    except (OSError, UnicodeDecodeError) as exc:
        raise CampaignError(f"cannot read AIGER header {path}: {exc}") from exc
    if len(fields) != 6 or fields[0] != "aig":
        raise CampaignError(f"unexpected binary AIGER header in {path}: {fields}")
    try:
        maximum_variable, inputs, latches, outputs, and_nodes = map(int, fields[1:])
    except ValueError as exc:
        raise CampaignError(f"non-numeric AIGER header in {path}: {fields}") from exc
    if any(value < 0 for value in (maximum_variable, inputs, latches, outputs, and_nodes)):
        raise CampaignError(f"negative AIGER count in {path}: {fields}")
    return {
        "maximum_variable": maximum_variable,
        "inputs": inputs,
        "latches": latches,
        "outputs": outputs,
        "and_nodes": and_nodes,
    }


def parse_aiger_map(path: Path) -> dict[str, list[dict[str, Any]]]:
    records: dict[str, list[dict[str, Any]]] = {
        "input": [],
        "init": [],
        "latch": [],
        "output": [],
        "ninitff": [],
    }
    seen: dict[str, set[int]] = {
        kind: set() for kind in records if kind != "ninitff"
    }
    for line_number, raw in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(), start=1
    ):
        if raw.startswith("ninitff "):
            fields = raw.split()
            if len(fields) != 2 or records["ninitff"]:
                raise CampaignError(
                    f"malformed AIGER ninitff record {path}:{line_number}: {raw!r}"
                )
            try:
                count = int(fields[1])
            except ValueError as exc:
                raise CampaignError(
                    f"non-numeric AIGER ninitff count {path}:{line_number}: {raw!r}"
                ) from exc
            if count < 0:
                raise CampaignError(
                    f"negative AIGER ninitff count {path}:{line_number}: {raw!r}"
                )
            records["ninitff"].append({"count": count})
            continue
        fields = raw.split(maxsplit=3)
        if len(fields) != 4 or fields[0] not in records:
            raise CampaignError(f"malformed AIGER map {path}:{line_number}: {raw!r}")
        kind, index_text, bit_text, name = fields
        try:
            index = int(index_text)
            bit = int(bit_text)
        except ValueError as exc:
            raise CampaignError(
                f"non-numeric AIGER map index {path}:{line_number}: {raw!r}"
            ) from exc
        if index < 0 or bit < 0 or not name:
            raise CampaignError(f"invalid AIGER map record {path}:{line_number}: {raw!r}")
        if index in seen[kind]:
            raise CampaignError(f"duplicate AIGER {kind} index {index} in {path}")
        seen[kind].add(index)
        records[kind].append({"index": index, "bit": bit, "name": name})
    for kind in seen:
        records[kind].sort(key=lambda record: record["index"])
    return records


def align_aiger_state_symbols(
    gold_aiger: Path,
    gate_aiger: Path,
    gold_map_path: Path,
    gate_map_path: Path,
    aligned_gate_aiger: Path,
    alignment_path: Path,
    spec: dict[str, Any],
) -> dict[str, Any]:
    gold_header = aiger_header(gold_aiger)
    gate_header = aiger_header(gate_aiger)
    for field in ("inputs", "latches", "outputs"):
        if gold_header[field] != gate_header[field]:
            raise CampaignError(
                f"postroute AIGER {field} differ: {gold_header[field]} versus "
                f"{gate_header[field]}"
            )
    gold_map = parse_aiger_map(gold_map_path)
    gate_map = parse_aiger_map(gate_map_path)
    for kind in ("input", "output"):
        gold_ports = {
            (record["name"], record["bit"]) for record in gold_map[kind]
        }
        gate_ports = {
            (record["name"], record["bit"]) for record in gate_map[kind]
        }
        if len(gold_ports) != len(gold_map[kind]) or len(gate_ports) != len(
            gate_map[kind]
        ):
            raise CampaignError(f"duplicate postroute AIGER {kind} port mapping")
        if gold_ports != gate_ports:
            raise CampaignError(
                f"postroute AIGER {kind} interfaces differ: "
                f"gold-only={sorted(gold_ports - gate_ports)[:8]} "
                f"gate-only={sorted(gate_ports - gold_ports)[:8]}"
            )
    external_inputs = len(gold_map["input"])
    if len(gate_map["input"]) != external_inputs:
        raise CampaignError("postroute AIGER external input counts differ")
    if len(gold_map["ninitff"]) != 1 or len(gate_map["ninitff"]) != 1:
        raise CampaignError("postroute AIGER ninitff record is missing")
    state_bits = int(gold_map["ninitff"][0]["count"])
    if gate_map["ninitff"][0]["count"] != state_bits:
        raise CampaignError("postroute AIGER state-bit counts differ")
    for side, header, mapping in (
        ("gold", gold_header, gold_map),
        ("gate", gate_header, gate_map),
    ):
        if len(mapping["init"]) != len(mapping["latch"]):
            raise CampaignError(f"{side} postroute AIGER state map is incomplete")
        if mapping["ninitff"] != [{"count": state_bits}]:
            raise CampaignError(f"{side} postroute AIGER ninitff accounting failed")
        if header["inputs"] != external_inputs + state_bits:
            raise CampaignError(f"{side} postroute AIGER zinit input accounting failed")
        if header["latches"] != state_bits + 1:
            raise CampaignError(
                f"{side} postroute AIGER must contain state bits plus one zinit latch"
            )
    gold_latches = {record["index"]: record for record in gold_map["latch"]}
    gate_latches = {record["index"]: record for record in gate_map["latch"]}
    gold_inits = {record["index"]: record for record in gold_map["init"]}
    gate_inits = {record["index"]: record for record in gate_map["init"]}
    if set(gold_latches) != set(gate_latches):
        raise CampaignError("postroute AIGER named latch-index sets differ")
    expected_init_indices = {
        external_inputs + latch_index for latch_index in gold_latches
    }
    if set(gold_inits) != expected_init_indices or set(gate_inits) != expected_init_indices:
        raise CampaignError("postroute AIGER named arbitrary-init indices differ")
    private_state = re.compile(r"^_[0-9]+_\.[A-Za-z0-9_]+$")
    mismatches: list[dict[str, Any]] = []
    for latch_index in sorted(gold_latches):
        init_index = external_inputs + latch_index
        gold_latch = gold_latches[latch_index]
        gate_latch = gate_latches[latch_index]
        gold_init = gold_inits[init_index]
        gate_init = gate_inits[init_index]
        if (
            gold_latch["bit"] != 0
            or gate_latch["bit"] != 0
            or gold_init["bit"] != 0
            or gate_init["bit"] != 0
            or gold_init["name"] != gold_latch["name"]
            or gate_init["name"] != gate_latch["name"]
        ):
            raise CampaignError(
                f"postroute AIGER state-map inconsistency at latch {latch_index}"
            )
        if gold_latch["name"] == gate_latch["name"]:
            continue
        if (
            private_state.fullmatch(gold_latch["name"]) is None
            or private_state.fullmatch(gate_latch["name"]) is None
        ):
            raise CampaignError(
                "postroute AIGER public state names differ at latch "
                f"{latch_index}: {gold_latch['name']!r} versus {gate_latch['name']!r}"
            )
        mismatches.append(
            {
                "latch_index": latch_index,
                "arbitrary_init_input_index": init_index,
                "gold_private_name": gold_latch["name"],
                "gate_private_name": gate_latch["name"],
            }
        )
    policy = spec["physical_flow_policy"]["postroute_equivalence"]
    if len(mismatches) > policy["private_state_symbol_remaps_max"]:
        raise CampaignError(
            f"postroute private-state remaps {len(mismatches)} exceed "
            f"{policy['private_state_symbol_remaps_max']}"
        )
    targets = [item["gold_private_name"] for item in mismatches]
    if len(targets) != len(set(targets)):
        raise CampaignError("postroute state-symbol remap targets are not unique")
    aligned = gate_aiger.read_bytes()
    for mismatch in mismatches:
        for symbol_type, symbol_index, prefix in (
            ("latch", mismatch["latch_index"], ""),
            ("init", mismatch["arbitrary_init_input_index"], "init:"),
        ):
            old_line = (
                f"\n{'l' if symbol_type == 'latch' else 'i'}{symbol_index} "
                f"{prefix}{mismatch['gate_private_name']}\n"
            ).encode()
            new_line = (
                f"\n{'l' if symbol_type == 'latch' else 'i'}{symbol_index} "
                f"{prefix}{mismatch['gold_private_name']}\n"
            ).encode()
            if aligned.count(old_line) != 1:
                raise CampaignError(
                    f"postroute AIGER omits unique {symbol_type} symbol line at "
                    f"index {symbol_index}"
                )
            aligned = aligned.replace(old_line, new_line, 1)
    aligned_gate_aiger.write_bytes(aligned)
    alignment = {
        "status": "pass",
        "policy": (
            "Primary inputs and outputs match by public name and bit. State bits "
            "match by deterministic AIGER latch index; only autogenerated private "
            "symbols may be aligned, and arbitrary initial-state inputs use the "
            "same mapping."
        ),
        "gold_header": gold_header,
        "gate_header": gate_header,
        "external_input_bits": external_inputs,
        "state_bits": state_bits,
        "named_state_bits": len(gold_latches),
        "output_bits": gold_header["outputs"],
        "named_output_bits": len(gold_map["output"]),
        "private_state_symbol_remaps": mismatches,
        "private_state_symbol_remaps_count": len(mismatches),
        "private_state_symbol_remaps_max": policy["private_state_symbol_remaps_max"],
    }
    write_text(alignment_path, json.dumps(alignment, indent=2, sort_keys=True) + "\n")
    return alignment


def postroute_equivalence(
    case: dict[str, Any], physical_dir: Path, synthesized_netlist: Path, final_netlist: Path,
    spec: dict[str, Any]
) -> dict[str, Any]:
    proof_dir = physical_dir / "equivalence_postroute"
    proof_dir.mkdir(parents=True, exist_ok=True)
    gold_script = proof_dir / "gold_aiger.ys"
    gate_script = proof_dir / "gate_aiger.ys"
    gold_aiger = proof_dir / "gold.aig"
    gate_aiger = proof_dir / "gate.aig"
    aligned_gate_aiger = proof_dir / "gate_state_aligned.aig"
    gold_map = proof_dir / "gold.map"
    gate_map = proof_dir / "gate.map"
    alignment_path = proof_dir / "state_alignment.json"
    gold_log = proof_dir / "gold_aiger.log"
    gate_log = proof_dir / "gate_aiger.log"
    dsec_log = proof_dir / "abc_dsec.log"
    write_text(
        gold_script,
        postroute_aiger_script(case, synthesized_netlist, gold_aiger, gold_map),
    )
    write_text(
        gate_script,
        postroute_aiger_script(case, final_netlist, gate_aiger, gate_map),
    )
    print(f"[{case['name']}] ORFS synthesized-to-final equivalence", flush=True)
    run_logged([str(DEFAULT_YOSYS), "-s", str(gold_script)], gold_log)
    run_logged([str(DEFAULT_YOSYS), "-s", str(gate_script)], gate_log)
    warning_summaries = {
        "gold": validate_warnings(
            warning_lines(gold_log), case, spec["warning_policy"], allow_abc=False
        ),
        "gate": validate_warnings(
            warning_lines(gate_log), case, spec["warning_policy"], allow_abc=False
        ),
    }
    alignment = align_aiger_state_symbols(
        gold_aiger,
        gate_aiger,
        gold_map,
        gate_map,
        aligned_gate_aiger,
        alignment_path,
        spec,
    )
    timeout_s = int(
        spec["physical_flow_policy"]["postroute_equivalence"]["abc_timeout_seconds"]
    )
    abc_command = (
        f"dsec -T {timeout_s} -v {gold_aiger} {aligned_gate_aiger}"
    )
    run_logged(
        [str(DEFAULT_ABC), "-c", abc_command],
        dsec_log,
        timeout_s=timeout_s + 60,
    )
    dsec_text = dsec_log.read_text(encoding="utf-8", errors="replace")
    forbidden = (
        "Warning:",
        "Miter computation has failed",
        "Networks are NOT EQUIVALENT",
        "Verification failed",
        "UNDECIDED",
    )
    if dsec_text.count("Networks are equivalent.") != 1 or any(
        marker in dsec_text for marker in forbidden
    ):
        raise CampaignError(
            f"{case['name']}: ABC dsec postroute equivalence lacks clean closure"
        )
    miter = re.search(
        r"Original miter:\s+Latches =\s*([0-9]+)\. Nodes =\s*([0-9]+)\.",
        dsec_text,
    )
    elapsed = re.search(r"Networks are equivalent\.\s+Time =\s*([0-9.]+) sec", dsec_text)
    if miter is None or elapsed is None:
        raise CampaignError(f"{case['name']}: ABC dsec closure metrics are missing")
    return {
        "status": "pass",
        "method": "Pinned Yosys Liberty/AIG normalization followed by pinned ABC dsec inductive sequential equivalence from the exact ORFS synthesized netlist to 6_final.v",
        "arbitrary_common_initial_state": True,
        "external_input_bits": alignment["external_input_bits"],
        "state_bits": alignment["state_bits"],
        "output_bits": alignment["output_bits"],
        "proven_points": alignment["state_bits"] + alignment["output_bits"],
        "unproven_points": 0,
        "aiger_counts": {
            "gold": alignment["gold_header"],
            "gate": alignment["gate_header"],
        },
        "state_alignment": alignment,
        "abc_dsec": {
            "status": "pass",
            "original_miter_latches": int(miter.group(1)),
            "original_miter_nodes": int(miter.group(2)),
            "elapsed_seconds": float(elapsed.group(1)),
            "timeout_seconds": timeout_s,
        },
        "warnings": warning_summaries,
        "orfs_kepler_lec_disposition": spec["physical_flow_policy"]["orfs_kepler_lec"],
        "artifacts": {
            "gold_script": artifact(gold_script),
            "gate_script": artifact(gate_script),
            "gold_log": artifact(gold_log),
            "gate_log": artifact(gate_log),
            "gold_aiger": artifact(gold_aiger),
            "gate_aiger": artifact(gate_aiger),
            "aligned_gate_aiger": artifact(aligned_gate_aiger),
            "gold_map": artifact(gold_map),
            "gate_map": artifact(gate_map),
            "state_alignment": artifact(alignment_path),
            "abc_dsec_log": artifact(dsec_log),
        },
    }


def physical_diagnostic_metrics(
    metadata: dict[str, Any], spec: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    power_keys = {
        "internal_w": "finish__power__internal__total",
        "switching_w": "finish__power__switching__total",
        "leakage_w": "finish__power__leakage__total",
        "total_w": "finish__power__total",
    }
    power = {
        "status": spec["physical_flow_policy"]["power"]["status"],
        "gate": False,
        **{name: metadata_number(metadata, key) for name, key in power_keys.items()},
        "limitations": spec["physical_flow_policy"]["power"]["use"],
    }
    ir_keys = {
        "vdd_average_drop_v": "finish__design_powergrid__drop__average__net__VDD__corner__default",
        "vdd_worst_drop_v": "finish__design_powergrid__drop__worst__net__VDD__corner__default",
        "vss_average_drop_v": "finish__design_powergrid__drop__average__net__VSS__corner__default",
        "vss_worst_drop_v": "finish__design_powergrid__drop__worst__net__VSS__corner__default",
    }
    ir_drop = {
        "status": spec["physical_flow_policy"]["ir_drop"]["status"],
        "gate": False,
        **{name: metadata_number(metadata, key) for name, key in ir_keys.items()},
        "limitations": spec["physical_flow_policy"]["ir_drop"]["use"],
    }
    return power, ir_drop


def physical_case(
    case: dict[str, Any],
    case_dir: Path,
    synthesis: dict[str, Any],
    spec: dict[str, Any],
    *,
    run_equivalence: bool,
) -> dict[str, Any]:
    global _ACTIVE_CONSTRAINT_SPEC
    _ACTIVE_CONSTRAINT_SPEC = spec["constraints"]
    physical_dir = case_dir / "physical"
    physical_dir.mkdir(parents=True, exist_ok=True)
    config = physical_dir / "config.mk"
    write_text(config, physical_config(case, spec))
    ports = netlist_ports(synthesis["paths"]["netlist_json"], case["top"])
    constraint = physical_dir / "constraint.sdc"
    write_text(
        constraint,
        sdc_text(
            case,
            ports,
            spec["constraints"]["proxy_setup"],
            include_reset_exceptions=True,
        ),
    )
    container = spec["toolchain"]["openroad_orfs_container"]
    reference = f"{OPENROAD_REPOSITORY}@{container['amd64_digest']}"
    nickname = f"opentallas_{case['name']}"
    result_dir = physical_dir / "results" / "nangate45" / nickname / "base"
    synthesized_netlist = result_dir / "1_2_yosys.v"
    raw_synthesized_netlist = physical_dir / "orfs_synth_netlist_raw.v"
    container_synthesized_netlist = (
        f"/work/results/nangate45/{nickname}/base/1_2_yosys.v"
    )
    common_make = (
        "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
        "make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base "
    )
    docker_prefix = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{ROOT}:/src:ro",
        "-v",
        f"{physical_dir}:/work",
        "-w",
        "/OpenROAD-flow-scripts/flow",
        reference,
        "bash",
        "-lc",
    ]

    # The OpenSTA Verilog reader embedded in the pinned OpenROAD image rejects
    # signed top-level declarations in an otherwise valid technology-mapped
    # structural netlist.  Generate that netlist first, retain the exact raw
    # artifact, then remove declaration-only signedness before OpenROAD reads
    # it.  The mapped gates are already bit-level, and the independent
    # synthesized-to-postroute sequential-equivalence gate remains mandatory.
    synthesis_log = physical_dir / "openroad_synthesis.log"
    run_logged(
        docker_prefix
        + [
            common_make
            + container_synthesized_netlist
            + " && chmod a+w "
            + container_synthesized_netlist
        ],
        synthesis_log,
    )
    if not synthesized_netlist.is_file():
        raise CampaignError(
            f"{case['name']}: ORFS synthesis omitted {synthesized_netlist}"
        )
    shutil.copy2(synthesized_netlist, raw_synthesized_netlist)
    signed_tokens_removed = sanitize_netlist(
        synthesized_netlist, synthesized_netlist
    )
    if re.search(
        r"\b(input|output|wire) signed\b",
        synthesized_netlist.read_text(encoding="utf-8"),
    ):
        raise CampaignError(
            f"{case['name']}: physical netlist signed-declaration normalization failed"
        )

    log = physical_dir / "openroad_flow.log"
    print(f"[{case['name']}] OpenROAD place/CTS/route/final proxy", flush=True)
    command = docker_prefix + [common_make + "finish metadata-generate"]
    run_logged(command, log)
    report_dir = physical_dir / "reports" / "nangate45" / nickname / "base"
    metadata_path = report_dir / "metadata.json"
    required = {
        "metadata": metadata_path,
        "orfs_synth_netlist": result_dir / "1_2_yosys.v",
        "final_odb": result_dir / "6_final.odb",
        "final_netlist": result_dir / "6_final.v",
        "final_sdc": result_dir / "6_final.sdc",
        "final_def": result_dir / "6_final.def",
        "final_gds": result_dir / "6_final.gds",
        "final_spef": result_dir / "6_final.spef",
        "finish_report": report_dir / "6_finish.rpt",
        "route_drc_report": report_dir / "5_route_drc.rpt",
    }
    missing = [name for name, path in required.items() if not path.is_file()]
    if missing:
        raise CampaignError(f"{case['name']}: physical flow omitted {missing}")
    metadata = strict_json(metadata_path)
    if not isinstance(metadata, dict):
        raise CampaignError(f"{case['name']}: physical metadata root is not an object")
    gates = physical_gate_metrics(case, metadata, spec)
    warnings = physical_warning_audit(case, log, metadata, spec)
    connectivity = final_netlist_connectivity_audit(
        case, physical_dir, required["final_netlist"], spec
    )
    if run_equivalence:
        postroute = postroute_equivalence(
            case,
            physical_dir,
            required["orfs_synth_netlist"],
            required["final_netlist"],
            spec,
        )
    else:
        postroute = {
            "status": "skipped_by_cli",
            "method": "Canonical runs require this independent physical-netlist gate.",
        }
    power, ir_drop = physical_diagnostic_metrics(metadata, spec)
    return {
        "status": "pass",
        "scope": "OpenROAD/ORFS Nangate45 synthesized place, CTS, detailed route, fill, and final report proxy",
        "gates": gates,
        "warning_audit": warnings,
        "final_netlist_connectivity": connectivity,
        "postroute_equivalence": postroute,
        "orfs_kepler_lec": {
            "status": "disabled_replaced_by_independent_gate",
            **spec["physical_flow_policy"]["orfs_kepler_lec"],
        },
        "netlist_sanitization": {
            "signed_declarations_removed": signed_tokens_removed,
            "reason": "OpenROAD/OpenSTA Verilog parser compatibility after bit-level technology mapping; independently checked by mandatory postroute sequential equivalence.",
            "raw_artifact": artifact(raw_synthesized_netlist),
            "sanitized_artifact": artifact(required["orfs_synth_netlist"]),
        },
        "power_diagnostic": power,
        "power_integrity_diagnostic": ir_drop,
        "artifacts": {
            "config": artifact(config),
            "constraint": artifact(constraint),
            "synthesis_flow_log": artifact(synthesis_log),
            "flow_log": artifact(log),
            **{name: artifact(path) for name, path in required.items()},
        },
        "limitations": spec["evidence_boundary"],
    }


def strip_paths(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_paths(child)
            for key, child in value.items()
            if key != "paths"
        }
    if isinstance(value, list):
        return [strip_paths(child) for child in value]
    if isinstance(value, Path):
        return str(value.relative_to(ROOT))
    return value


def render_report(result: dict[str, Any]) -> str:
    lines = [
        "# Public implementation-proxy campaign",
        "",
        f"**Status:** {result['status'].upper()}",
        "",
        f"Baseline commit: `{result['baseline']['commit']}`  ",
        f"Run fingerprint: `{result['run_fingerprint']}`  ",
        f"Evidence class: `{result['evidence_class']}`",
        "",
        "This is a Nangate45 45 nm typical-corner methodology and scaling proxy. "
        "It is not target-node or product signoff, does not establish 1 GHz, and "
        "excludes ROM/SRAM/HBM/PHY/package/analog macro PPA.",
        "",
        "## Case summary",
        "",
        "| Case | Mapping profile | Cells | Area proxy (um^2) | Sequential area | 100 MHz prelayout WNS (ns) | Architectural diagnostic WNS (ns) | Final setup WNS (ns) | Final hold WNS (ns) | Final DRC | Generic equiv | Mapped equiv | Postroute equiv | Physical |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|",
    ]
    for case in result["cases"]:
        mapped = case["synthesis"]["mapped"]
        sta = case["sta"]
        generic = case["equivalence_generic"]["status"]
        mapped_equiv = case["equivalence_mapped"]["status"]
        physical_result = case["physical_proxy"]
        physical = physical_result["status"]
        physical_gates = physical_result.get("gates", {})
        postroute = physical_result.get("postroute_equivalence", {}).get(
            "status", "not_required"
        )
        final_setup = physical_gates.get("setup_wns_ns")
        final_hold = physical_gates.get("hold_wns_ns")
        final_drc = physical_gates.get("drc_errors")
        final_setup_text = "n/a" if final_setup is None else f"{final_setup:.3f}"
        final_hold_text = "n/a" if final_hold is None else f"{final_hold:.3f}"
        final_drc_text = "n/a" if final_drc is None else f"{int(final_drc)}"
        mapping_profile_id = case["synthesis"]["mapping_profile"]["profile_id"]
        lines.append(
            f"| {case['name']} | {mapping_profile_id} | {mapped['num_cells']:,} | {mapped.get('area', 0):,.3f} | "
            f"{mapped.get('sequential_area', 0):,.3f} | "
            f"{sta['proxy_100mhz']['setup_wns_ns']:.3f} | "
            f"{sta['architectural_diagnostic']['setup_wns_ns']:.3f} | "
            f"{final_setup_text} | {final_hold_text} | {final_drc_text} | "
            f"{generic} | {mapped_equiv} | {postroute} | {physical} |"
        )
    lines.extend(
        [
            "",
            "## Gate disposition",
            "",
            f"- Required cases passing: {result['summary']['required_cases_passing']}/{result['summary']['required_cases']}.",
            f"- Generic equivalence closures: {result['summary']['generic_equivalence_passing']}/{result['summary']['generic_equivalence_required']}.",
            f"- Actual mapped-netlist equivalence closures: {result['summary']['mapped_equivalence_passing']}/{result['summary']['mapped_equivalence_required']}.",
            f"- ORFS synthesized-to-final equivalence closures: {result['summary']['postroute_equivalence_passing']}/{result['summary']['postroute_equivalence_required']}.",
            f"- Physical proxy completions: {result['summary']['physical_proxy_passing']}/{result['summary']['physical_proxy_required']}.",
            "- All mapped cases contain zero internal/unmapped cells, latches, blackboxes, and structural errors; exact enumerated warnings are recorded in JSON.",
            "- `numeric_e16_l16` alone uses the governed bounded structural Liberty mapping profile and a 300-second outer timeout. Its area, cell count, and timing are scaling diagnostics and are not directly QoR-comparable to the default delay-oriented cases.",
            "- Required physical cases close final setup, hold, electrical, max-fanout, flow-error, connectivity, equivalence, and detailed-route DRC proxy gates.",
            "- The 100 MHz prelayout setup check gates only the small arithmetic representative; stage-control timing closes on the buffered postroute proxy. Architectural-frequency timing is diagnostic only.",
            "- Unrouted minimum-delay and reset recovery/removal results remain diagnostic until clock-tree/routing and target integration; no broad reset waiver is claimed.",
            "- Vectorless OpenSTA power is illustrative library scaling only and reports an ideal clock network; it is not a product power estimate.",
            "- OpenROAD vectorless power and default-grid IR drop are recorded as non-gating diagnostics and are not product power-integrity evidence.",
            "",
            "## Evidence boundary and open obligations",
            "",
            result["evidence_boundary"],
            "",
        ]
    )
    for item in result["open_macro_line_items"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "The machine-readable result retains exact inputs, tool and library hashes, "
            "parameters, warning inventory, constraints, timing checks, proof-point "
            "counts, physical metrics, and hashes for all local raw artifacts.",
            "",
        ]
    )
    return "\n".join(lines)


def run_campaign(args: argparse.Namespace) -> dict[str, Any]:
    spec_path = args.spec.resolve()
    spec = strict_json(spec_path)
    if not isinstance(spec, dict):
        raise CampaignError("implementation proxy root must be an object")
    validate_spec(spec)
    all_cases = {case["name"]: case for case in spec["cases"]}
    selected_names = args.case or list(spec["acceptance"]["required_cases"])
    unknown = set(selected_names) - set(all_cases)
    if unknown:
        raise CampaignError(f"unknown selected cases: {sorted(unknown)}")
    selected = [all_cases[name] for name in selected_names]
    physical_names = set(spec["acceptance"]["physical_proxy_required_cases"])
    postroute_required = set(
        spec["acceptance"]["postroute_equivalence_required_cases"]
    )
    run_physical = not args.skip_physical and bool(physical_names & set(selected_names))
    tools = resolve_toolchain(spec, require_physical=run_physical or args.validate_only)
    inventory = source_inventory(spec_path, selected)
    state = git_state()
    if state["dirty_paths"] and not (args.allow_dirty or args.validate_only):
        raise CampaignError(
            "campaign requires a clean source tree; dirty paths: " + ", ".join(state["dirty_paths"])
        )
    run_fingerprint = fingerprint(spec, inventory, tools)
    if args.validate_only:
        return {
            "status": "validated",
            "run_fingerprint": run_fingerprint,
            "selected_cases": selected_names,
        }
    run_dir = BUILD_ROOT / run_fingerprint
    if run_dir.exists():
        if not args.force:
            raise CampaignError(
                f"run directory already exists: {run_dir}; use --force only for an intentional replacement"
            )
        resolved = run_dir.resolve()
        if resolved.parent != BUILD_ROOT.resolve() or run_dir.is_symlink():
            raise CampaignError(f"refusing to replace unsafe run directory {run_dir}")
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    cases_result: list[dict[str, Any]] = []
    generic_required = set(spec["acceptance"]["equivalence_required_cases"])
    mapped_required = set(spec["acceptance"]["mapped_equivalence_required_cases"])
    for case in selected:
        case_dir = run_dir / case["name"]
        case_dir.mkdir()
        synthesis = synthesize_case(case, case_dir, spec)
        sta = sta_case(case, case_dir, synthesis, spec)
        if case["name"] in generic_required and not args.skip_equivalence:
            generic = generic_equivalence(case, case_dir, spec)
        else:
            generic = {
                "status": "not_required_scaling_point" if case["name"] not in generic_required else "skipped_by_cli",
                "method": "representative configurations carry formal equivalence; this point is synthesis scaling only",
            }
        if case["name"] in mapped_required and not args.skip_equivalence:
            mapped = mapped_equivalence(
                case, case_dir, synthesis["paths"]["netlist"], spec
            )
        else:
            mapped = {
                "status": "not_required_trusted_mapping_boundary" if case["name"] not in mapped_required else "skipped_by_cli",
                "method": "ABC/library mapping is a declared tool-trust boundary unless this case is explicitly required",
            }
        if case["name"] in physical_names and not args.skip_physical:
            physical = physical_case(
                case,
                case_dir,
                synthesis,
                spec,
                run_equivalence=not args.skip_equivalence,
            )
        else:
            physical = {
                "status": "not_required_scaling_point" if case["name"] not in physical_names else "skipped_by_cli"
            }
        cases_result.append(
            {
                "name": case["name"],
                "kind": case["kind"],
                "top": case["top"],
                "parameters": case["parameters"],
                "sources": [
                    {"path": source, "sha256": sha256_file(ROOT / source)}
                    for source in case["sources"]
                ],
                "synthesis": synthesis,
                "sta": sta,
                "equivalence_generic": generic,
                "equivalence_mapped": mapped,
                "physical_proxy": physical,
            }
        )
    selected_set = set(selected_names)
    required_selected = selected_set & set(spec["acceptance"]["required_cases"])
    generic_selected = selected_set & generic_required
    mapped_selected = selected_set & mapped_required
    physical_selected = selected_set & physical_names
    postroute_selected = selected_set & postroute_required
    summary = {
        "required_cases": len(required_selected),
        "required_cases_passing": len(cases_result),
        "generic_equivalence_required": len(generic_selected),
        "generic_equivalence_passing": sum(
            case["equivalence_generic"]["status"] == "pass" for case in cases_result
        ),
        "mapped_equivalence_required": len(mapped_selected),
        "mapped_equivalence_passing": sum(
            case["equivalence_mapped"]["status"] == "pass" for case in cases_result
        ),
        "physical_proxy_required": len(physical_selected),
        "physical_proxy_passing": sum(
            case["physical_proxy"]["status"].startswith("pass") for case in cases_result
        ),
        "postroute_equivalence_required": len(postroute_selected),
        "postroute_equivalence_passing": sum(
            case["physical_proxy"].get("postroute_equivalence", {}).get("status")
            == "pass"
            for case in cases_result
        ),
    }
    complete_selection = selected_set == set(spec["acceptance"]["required_cases"])
    technical_gates_pass = (
        summary["required_cases_passing"] == summary["required_cases"]
        and summary["generic_equivalence_passing"] == summary["generic_equivalence_required"]
        and summary["mapped_equivalence_passing"] == summary["mapped_equivalence_required"]
        and summary["physical_proxy_passing"] == summary["physical_proxy_required"]
        and summary["postroute_equivalence_passing"]
        == summary["postroute_equivalence_required"]
        and not args.skip_equivalence
        and not args.skip_physical
        and complete_selection
    )
    canonical_pass = technical_gates_pass and not state["dirty_paths"]
    result = {
        "schema_version": 1,
        "campaign_id": spec["campaign_id"],
        "status": "pass" if canonical_pass else "partial_noncanonical",
        "canonical_eligibility": {
            "clean_source_tree": not state["dirty_paths"],
            "complete_case_selection": complete_selection,
            "equivalence_enabled": not args.skip_equivalence,
            "physical_flow_enabled": not args.skip_physical,
            "technical_gates_pass": technical_gates_pass,
        },
        "evidence_class": "synthetic_open_pdk_proxy",
        "baseline": state,
        "run_fingerprint": run_fingerprint,
        "source_inventory": inventory,
        "toolchain": tools,
        "constraints": spec["constraints"],
        "physical_flow_policy": spec["physical_flow_policy"],
        "prelayout_timing_policy": spec["prelayout_timing_policy"],
        "warning_policy": spec["warning_policy"],
        "evidence_boundary": spec["evidence_boundary"],
        "open_macro_line_items": spec["open_macro_line_items"],
        "summary": summary,
        "cases": cases_result,
    }
    result = strip_paths(result)
    if complete_selection and not technical_gates_pass:
        raise CampaignError(f"canonical campaign did not close: {summary}")
    output_json = ROOT / spec["reports"]["json"]
    output_markdown = ROOT / spec["reports"]["markdown"]
    write_text(output_json, json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_text(output_markdown, render_report(result))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--case", action="append", help="run one named case; repeatable")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--skip-equivalence", action="store_true")
    parser.add_argument("--skip-physical", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = run_campaign(args)
    except CampaignError as exc:
        print(f"IMPLEMENTATION CAMPAIGN FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"IMPLEMENTATION CAMPAIGN {result['status'].upper()}: "
        f"fingerprint {result['run_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
