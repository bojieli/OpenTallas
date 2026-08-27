#!/usr/bin/env python3
"""Validate and deterministically render the public-reference specification.

The checker intentionally uses only the Python standard library.  It is a gate
for specification consistency, not a replacement for RTL lint, formal proof,
CDC/RDC, or target-node signoff.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "spec"
EVIDENCE_CLASSES = {
    "measured",
    "published",
    "derived",
    "assumed",
    "simulated",
    "synthetic",
}
PLACEHOLDER_RE = re.compile(r"\b(?:TODO|TBD|FIXME|XXX)\b", re.IGNORECASE)
REF_RE = re.compile(r"\b(?:ARCH|MICRO|ICD|NUM|CRP|RAS|FW|PPA|DV|CC)-\d+(?:\.\d+)?\b")
FAULT_SITE_RE = re.compile(r'check_site\s*\(\s*"(FC-[A-Z0-9-]+)"')
COVER_BIN_DECL_RE = re.compile(r'pass_bin\s*\(\s*"(COV-[A-Z0-9-]+)"')


class SpecError(RuntimeError):
    pass


def _strict_load(path: Path) -> Any:
    """Load JSON while rejecting duplicate object keys."""

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
        raise SpecError(f"invalid JSON in {path.relative_to(ROOT)}: {exc}") from exc
    if duplicates:
        names = ", ".join(sorted(set(duplicates)))
        raise SpecError(f"duplicate JSON keys in {path.relative_to(ROOT)}: {names}")
    return data


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SpecError(message)


def _integer(value: Any, label: str, *, minimum: int | None = None) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool), f"{label} must be an integer")
    if minimum is not None:
        _require(value >= minimum, f"{label} must be >= {minimum}")
    return value


def _spec_refs() -> set[str]:
    refs: set[str] = set()
    for path in sorted(SPEC.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        refs.update(REF_RE.findall(text))
    return refs


def _validate_interfaces(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    interfaces = data.get("interfaces")
    if not isinstance(interfaces, list) or not interfaces:
        errors.append("interfaces.json must contain a non-empty interfaces list")
        return errors
    ids: set[str] = set()
    for item in interfaces:
        iid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(iid, str) or not iid:
            errors.append("every interface needs a non-empty id")
            continue
        if iid in ids:
            errors.append(f"duplicate interface id {iid}")
        ids.add(iid)
        width = item.get("width_bits")
        if not isinstance(width, int) or width <= 0:
            errors.append(f"{iid}: width_bits must be a positive integer")
            continue
        fields = item.get("fields")
        if not isinstance(fields, list) or not fields:
            errors.append(f"{iid}: fields must be a non-empty list")
            continue
        names: set[str] = set()
        bits: list[tuple[int, int, str]] = []
        for field in fields:
            name = field.get("name") if isinstance(field, dict) else None
            if not isinstance(name, str) or not name:
                errors.append(f"{iid}: every field needs a name")
                continue
            if name in names:
                errors.append(f"{iid}: duplicate field {name}")
            names.add(name)
            lsb = field.get("lsb")
            fwidth = field.get("width")
            if not isinstance(lsb, int) or not isinstance(fwidth, int) or lsb < 0 or fwidth <= 0:
                errors.append(f"{iid}.{name}: invalid lsb/width")
                continue
            if lsb + fwidth > width:
                errors.append(f"{iid}.{name}: extends beyond interface width")
            bits.append((lsb, lsb + fwidth, name))
        bits.sort()
        cursor = 0
        for start, end, name in bits:
            if start != cursor:
                kind = "gap" if start > cursor else "overlap"
                errors.append(f"{iid}: {kind} before {name} ({cursor}..{start})")
            cursor = max(cursor, end)
        if cursor != width:
            errors.append(f"{iid}: field coverage ends at {cursor}, expected {width}")
    return errors


def _validate_ids(data: dict[str, Any], key: str, label: str, errors: list[str]) -> list[dict[str, Any]]:
    values = data.get(key)
    if not isinstance(values, list):
        errors.append(f"{label}: {key} must be a list")
        return []
    seen: set[str] = set()
    for item in values:
        iid = item.get("id") if isinstance(item, dict) else None
        if not isinstance(iid, str) or not iid:
            errors.append(f"{label}: every entry needs a non-empty id")
        elif iid in seen:
            errors.append(f"{label}: duplicate id {iid}")
        else:
            seen.add(iid)
    return [item for item in values if isinstance(item, dict)]


def _validate_budgets(data: dict[str, Any], errors: list[str]) -> None:
    area = data.get("area", {})
    allocation = area.get("allocation_percent", {})
    if not isinstance(allocation, dict) or not allocation:
        errors.append("budgets.area.allocation_percent must be non-empty")
    else:
        values = list(allocation.values())
        if any(not isinstance(v, (int, float)) or v < 0 for v in values):
            errors.append("area allocation percentages must be non-negative numbers")
        elif abs(sum(values) - 100.0) > 1e-9:
            errors.append(f"area allocation percentages sum to {sum(values)}, expected 100")
    power = data.get("power", {})
    palloc = power.get("allocation_w", {})
    operating = power.get("operating_w_per_stage")
    if not isinstance(palloc, dict) or not palloc:
        errors.append("budgets.power.allocation_w must be non-empty")
    elif not isinstance(operating, (int, float)) or abs(sum(palloc.values()) - operating) > 1e-9:
        errors.append("power allocation watts must sum exactly to operating_w_per_stage")
    capacity = data.get("capacity", {})
    raw = capacity.get("rom_raw_bytes_per_stage")
    usable = capacity.get("rom_usable_bytes_per_stage")
    if (
        not isinstance(raw, (int, float))
        or not isinstance(usable, (int, float))
        or raw <= 0
        or usable <= 0
        or raw < usable
    ):
        errors.append("ROM raw/usable capacity values are invalid")
    hbm = capacity.get("hbm_physical_bytes_per_stage")
    frac = capacity.get("hbm_usable_fraction")
    if not isinstance(hbm, (int, float)) or not isinstance(frac, (int, float)) or not 0 < frac <= 1:
        errors.append("HBM capacity/fraction values are invalid")


def _validate_fault_campaign(
    data: dict[str, Any], check_ids: set[str], errors: list[str]
) -> None:
    sites = data.get("sites")
    if not isinstance(sites, list) or not sites:
        errors.append("fault_campaign.sites must be a non-empty list")
        return
    if data.get("planned_site_count") != len(sites):
        errors.append("fault_campaign planned_site_count does not match sites")
    simulators = data.get("required_simulators")
    if not isinstance(simulators, list) or len(set(simulators)) < 2:
        errors.append("fault_campaign requires at least two distinct simulators")
    required_fields = {
        "id",
        "bench",
        "fault_class",
        "verification_requirements",
        "expected_observation",
        "containment",
        "recovery",
    }
    planned_ids: list[str] = []
    planned_by_bench: dict[str, set[str]] = {}
    for index, site in enumerate(sites):
        if not isinstance(site, dict):
            errors.append(f"fault_campaign site {index} is not an object")
            continue
        missing = sorted(required_fields - set(site))
        if missing:
            errors.append(f"fault_campaign site {index} missing {', '.join(missing)}")
            continue
        site_id = site["id"]
        if not isinstance(site_id, str) or re.fullmatch(r"FC-[A-Z0-9-]+", site_id) is None:
            errors.append(f"fault_campaign site {index} has invalid id {site_id!r}")
            continue
        planned_ids.append(site_id)
        bench = site["bench"]
        if not isinstance(bench, str) or not (ROOT / bench).is_file():
            errors.append(f"{site_id}: missing bench {bench!r}")
        else:
            planned_by_bench.setdefault(bench, set()).add(site_id)
        requirements = site["verification_requirements"]
        if not isinstance(requirements, list) or not requirements:
            errors.append(f"{site_id}: verification_requirements must be non-empty")
        else:
            for requirement in requirements:
                if requirement not in check_ids:
                    errors.append(f"{site_id}: unknown verification check {requirement}")
        for field in ("fault_class", "expected_observation", "containment", "recovery"):
            if not isinstance(site[field], str) or not site[field].strip():
                errors.append(f"{site_id}: {field} must be non-empty")
    if len(set(planned_ids)) != len(planned_ids):
        duplicates = sorted(
            site_id for site_id in set(planned_ids) if planned_ids.count(site_id) != 1
        )
        errors.append(f"fault_campaign duplicate site IDs: {duplicates}")

    declared_ids: list[str] = []
    for bench, planned in sorted(planned_by_bench.items()):
        declared = FAULT_SITE_RE.findall((ROOT / bench).read_text(encoding="utf-8"))
        declared_ids.extend(declared)
        if set(declared) != planned:
            errors.append(f"fault_campaign/source site mismatch in {bench}")
    if len(set(declared_ids)) != len(declared_ids):
        errors.append("fault_campaign source declares a duplicate site ID")
    if set(declared_ids) != set(planned_ids):
        errors.append("fault_campaign has missing or stale source site IDs")
    gates = data.get("external_gates")
    if not isinstance(gates, list) or not gates:
        errors.append("fault_campaign must enumerate external non-modeled gates")
    elif any(
        not isinstance(gate, dict)
        or gate.get("status") != "external_not_modeled"
        or not gate.get("id")
        or not gate.get("scope")
        for gate in gates
    ):
        errors.append("fault_campaign external gates require id/scope/external_not_modeled")


def _validate_coverage_campaign(
    plan: dict[str, Any],
    waivers: dict[str, Any],
    verification: dict[str, Any],
    check_ids: set[str],
    errors: list[str],
) -> None:
    campaign = verification.get("coverage_campaign")
    if not isinstance(campaign, dict):
        errors.append("verification.coverage_campaign must be an object")
        return
    expected_paths = {
        "plan_path": "spec/coverage_plan.json",
        "runner_path": "tools/rtl_coverage_campaign.py",
        "waiver_path": "spec/coverage_waivers.json",
    }
    for field, expected in expected_paths.items():
        if campaign.get(field) != expected:
            errors.append(f"verification.coverage_campaign.{field} must be {expected}")
        elif not (ROOT / expected).is_file():
            errors.append(f"coverage campaign path is missing: {expected}")
    result_paths = campaign.get("result_paths")
    if not isinstance(result_paths, list) or not result_paths:
        errors.append("verification.coverage_campaign.result_paths must be non-empty")
    elif any(not isinstance(path, str) or not (ROOT / path).is_file() for path in result_paths):
        errors.append("verification.coverage_campaign result artifact is missing")
    simulators = campaign.get("required_simulators")
    minimum = verification.get("tool_independence", {}).get("simulators_minimum")
    if (
        not isinstance(simulators, list)
        or not isinstance(minimum, int)
        or len(set(simulators)) < minimum
    ):
        errors.append("coverage campaign does not meet simulator independence minimum")
    if campaign.get("unexpected_warnings_are_fatal") is not True:
        errors.append("coverage campaign must treat unexpected warnings as fatal")
    if not isinstance(campaign.get("evidence_boundary"), str) or not campaign["evidence_boundary"].strip():
        errors.append("coverage campaign must state its evidence boundary")

    closure = verification.get("closure", {})
    expected_thresholds = {
        "line_percent": float(closure.get("line_coverage_percent", -1)),
        "branch_percent": float(closure.get("branch_coverage_percent", -1)),
        "toggle_percent": float(closure.get("toggle_coverage_percent", -1)),
        "must_bin_percent": float(
            closure.get("functional_coverage_must_bins_percent", -1)
        ),
        "fsm_state_bin_percent": float(closure.get("fsm_state_bins_percent", -1)),
    }
    if plan.get("thresholds") != expected_thresholds:
        errors.append("coverage plan thresholds disagree with verification closure")
    deduplication = plan.get("point_accounting", {}).get("source_deduplication_key")
    if deduplication != campaign.get("source_deduplication_key"):
        errors.append("coverage source-deduplication key disagrees with verification")
    if plan.get("waiver_file") != campaign.get("waiver_path"):
        errors.append("coverage waiver path disagrees with verification")
    warning_policy = plan.get("warning_policy", {})
    if warning_policy.get("unexpected_warning_is_failure") is not True:
        errors.append("coverage plan must fail unexpected warnings")

    cases = plan.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("coverage plan cases must be a non-empty list")
        cases = []
    case_names: list[str] = []
    benches: list[str] = []
    planned_bins: list[str] = []
    required_case_fields = {
        "name",
        "top",
        "bench",
        "seed_hex",
        "pass_marker",
        "verilator_suppressions",
        "requirements",
        "sources",
        "bins",
    }
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"coverage case {index} is not an object")
            continue
        missing = sorted(required_case_fields - set(case))
        if missing:
            errors.append(f"coverage case {index} missing {', '.join(missing)}")
            continue
        name = case["name"]
        bench = case["bench"]
        case_names.append(name)
        benches.append(bench)
        if not isinstance(name, str) or re.fullmatch(r"[a-z0-9_]+", name) is None:
            errors.append(f"coverage case {index} has invalid name")
        if not isinstance(case["seed_hex"], str) or re.fullmatch(
            r"[0-9a-f]{8}", case["seed_hex"]
        ) is None:
            errors.append(f"coverage case {name} has invalid seed_hex")
        requirements = case["requirements"]
        if not isinstance(requirements, list) or not requirements:
            errors.append(f"coverage case {name} has no requirements")
        else:
            for requirement in requirements:
                if requirement not in check_ids:
                    errors.append(f"coverage case {name} has unknown check {requirement}")
        sources = case["sources"]
        if not isinstance(sources, list) or bench not in sources:
            errors.append(f"coverage case {name} source inventory omits its bench")
            sources = []
        for source in sources:
            if not isinstance(source, str) or not (ROOT / source).is_file():
                errors.append(f"coverage case {name} has missing source {source!r}")
        bench_path = ROOT / bench if isinstance(bench, str) else ROOT / "<invalid>"
        if bench_path.is_file():
            text = bench_path.read_text(encoding="utf-8")
            if f"module {case['top']}" not in text:
                errors.append(f"coverage case {name} top is absent from its bench")
            if case["seed_hex"] not in text.lower().replace("_", ""):
                errors.append(f"coverage case {name} seed/ID is absent from its bench")
        bins = case["bins"]
        if not isinstance(bins, list):
            errors.append(f"coverage case {name} bins must be a list")
        else:
            for bin_id in bins:
                if not isinstance(bin_id, str) or re.fullmatch(
                    r"COV-[A-Z0-9-]+", bin_id
                ) is None:
                    errors.append(f"coverage case {name} has invalid bin {bin_id!r}")
                else:
                    planned_bins.append(bin_id)
    for label, values in (("case", case_names), ("bench", benches), ("bin", planned_bins)):
        duplicates = sorted(value for value in set(values) if values.count(value) != 1)
        if duplicates:
            errors.append(f"coverage plan has duplicate {label}s: {duplicates}")
    declared_bins: list[str] = []
    for bench in benches:
        path = ROOT / bench
        if path.is_file():
            declared_bins.extend(COVER_BIN_DECL_RE.findall(path.read_text(encoding="utf-8")))
    if sorted(declared_bins) != sorted(planned_bins):
        errors.append("coverage plan/source mandatory-bin inventory mismatch")
    fsm_bins = plan.get("fsm_state_bins")
    expected_fsm = {item for item in planned_bins if item.startswith("COV-FSM-")}
    if not isinstance(fsm_bins, list) or set(fsm_bins) != expected_fsm:
        errors.append("coverage FSM bins do not exactly match planned COV-FSM bins")

    if waivers.get("campaign") != plan.get("campaign"):
        errors.append("coverage waiver campaign name disagrees with plan")
    entries = waivers.get("waivers")
    if not isinstance(entries, list):
        errors.append("coverage waivers must be a list")
        entries = []
    required_waiver_fields = {
        "id",
        "owner",
        "reason",
        "review_disposition",
        "requirement_impact",
        "revalidate_on",
        "point",
    }
    exact_point_fields = {
        "file",
        "line",
        "column",
        "point_class",
        "point_type",
        "description",
        "source_span",
    }
    waiver_ids: list[str] = []
    for index, waiver in enumerate(entries):
        if not isinstance(waiver, dict) or set(waiver) != required_waiver_fields:
            errors.append(f"coverage waiver {index} does not use the exact schema")
            continue
        waiver_ids.append(waiver["id"])
        point = waiver["point"]
        if not isinstance(point, dict) or set(point) != exact_point_fields:
            errors.append(f"coverage waiver {waiver['id']} does not identify an exact point")
        elif not isinstance(point["file"], str) or not (ROOT / point["file"]).is_file():
            errors.append(f"coverage waiver {waiver['id']} names a missing source")
        for field in required_waiver_fields - {"point"}:
            if not isinstance(waiver[field], str) or not waiver[field].strip():
                errors.append(f"coverage waiver {index} has empty {field}")
    if len(waiver_ids) != len(set(waiver_ids)):
        errors.append("coverage waiver IDs are not unique")


def _validate_models(
    manifest: dict[str, Any], parameters: dict[str, Any], errors: list[str]
) -> None:
    limits = parameters.get("architectural_limits", {})
    identifiers = parameters.get("identifiers", {})
    profiles = parameters.get("model_profiles", {})
    manifest_models = manifest.get("models", [])
    if not isinstance(profiles, dict) or not isinstance(manifest_models, list):
        errors.append("manifest/parameters model records must be lists/maps")
        return
    names = {item.get("name") for item in manifest_models if isinstance(item, dict)}
    if names != set(profiles):
        errors.append(f"manifest and parameters model names differ: {sorted(names ^ set(profiles))}")
    def limit(name: str) -> int:
        return _integer(limits.get(name), f"architectural_limits.{name}", minimum=1)
    try:
        max_context = limit("context_tokens_max")
        max_experts = limit("experts_max")
        max_layers = limit("layers_max")
        max_stages = limit("pipeline_stages_max")
        max_top_k = limit("top_k_max")
        max_sessions = limit("sessions_max")
    except SpecError as exc:
        errors.append(str(exc))
        return
    for name, profile in profiles.items():
        if not isinstance(profile, dict):
            errors.append(f"model profile {name} is not an object")
            continue
        checks = (
            ("experts", max_experts),
            ("layers", max_layers),
            ("stages", max_stages),
            ("top_k", max_top_k),
        )
        for field, upper in checks:
            value = profile.get(field)
            if not isinstance(value, int) or not 1 <= value <= upper:
                errors.append(f"{name}.{field}={value!r} outside 1..{upper}")
        contexts = profile.get("context_tokens")
        if not isinstance(contexts, list) or not contexts or any(
            not isinstance(v, int) or not 1 <= v <= max_context for v in contexts
        ):
            errors.append(f"{name}.context_tokens outside architectural bound")
        if profile.get("top_k", 0) > profile.get("experts", 0):
            errors.append(f"{name}: top_k exceeds experts")
        if name == "Qwen3-8B":
            for key, expected in (
                ("dense", True),
                ("experts", 1),
                ("top_k", 1),
                ("layers", 36),
                ("hidden_size", 4096),
                ("num_key_value_heads", 8),
                ("head_dim", 128),
                ("native_context_tokens", 32768),
            ):
                if profile.get(key) != expected:
                    errors.append(f"Qwen3-8B.{key}={profile.get(key)!r}, expected {expected!r}")
        if profile.get("native_context_tokens", 1) > max_context:
            errors.append(f"{name}: native context exceeds architectural limit")
    field_limits = (
        ("stage_id_bits", max_stages - 1),
        ("layer_id_bits", max_layers - 1),
        ("expert_id_bits", max_experts - 1),
        ("position_bits", max_context - 1),
        ("session_id_bits", max_sessions - 1),
    )
    for key, maximum in field_limits:
        bits = identifiers.get(key)
        if not isinstance(bits, int) or bits <= 0 or (1 << bits) - 1 < maximum:
            errors.append(f"identifier field {key} ({bits!r}) cannot encode {maximum}")
    batch_bits = identifiers.get("batch_per_stage_bits", 16)
    if not isinstance(batch_bits, int) or (1 << batch_bits) < limit("batch_per_stage_max_field"):
        errors.append("batch field cannot encode configured maximum")
    # Check the checked-in generated model profiles as well as the abstract parameter table.
    for item in manifest_models:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        path = ROOT / "configs" / "models" / (
            {"DeepSeek-V4-Flash-0731": "deepseek-v4-flash-0731", "DeepSeek-V4-Pro-0813": "deepseek-v4-pro-0813", "Kimi-K3": "kimi-k3", "Qwen3-8B": "qwen3-8b"}.get(name, "") + ".json"
        )
        if not path.exists():
            errors.append(f"manifest model {name} lacks checked-in profile {path}")
            continue
        model = _strict_load(path)
        profile = profiles.get(name, {})
        for model_key, parameter_key in (
            ("num_layers", "layers"),
            ("num_experts", "experts"),
            ("experts_per_token", "top_k"),
            ("hidden_size", "hidden_size"),
        ):
            if model.get(model_key) != profile.get(parameter_key):
                errors.append(f"{name}: checked-in {model_key} disagrees with parameters")
        if model.get("source_revision") != item.get("revision"):
            errors.append(f"{name}: source revision disagrees with manifest")
        if item.get("stages_midpoint", 0) != profile.get("stages"):
            errors.append(f"{name}: midpoint stage count disagrees with parameters")


def _validate_manifest(
    manifest: dict[str, Any], errors: list[str], *, allow_generated_missing: bool = False
) -> None:
    docs = manifest.get("documents")
    if not isinstance(docs, list) or not docs:
        errors.append("manifest.documents must be non-empty")
    else:
        seen: set[str] = set()
        for item in docs:
            if not isinstance(item, dict):
                errors.append("manifest document entry is not an object")
                continue
            did, path = item.get("id"), item.get("path")
            if did in seen:
                errors.append(f"duplicate manifest document id {did}")
            seen.add(did)
            generated_missing = bool(item.get("generated")) and allow_generated_missing
            if not isinstance(path, str) or (not (ROOT / path).is_file() and not generated_missing):
                errors.append(f"manifest document missing: {path}")
    for path in manifest.get("machine_readable", []):
        if not isinstance(path, str) or not (ROOT / path).is_file():
            errors.append(f"manifest machine-readable file missing: {path}")


def generate_traceability(requirements: list[dict[str, Any]], checks: list[dict[str, Any]]) -> str:
    reqs = sorted(requirements, key=lambda item: item["id"])
    dvs = sorted(checks, key=lambda item: item["id"])
    lines = [
        "# Requirements traceability (generated)",
        "",
        "> Do not edit this file by hand. Generated deterministically by",
        "> `tools/check_spec.py` from `requirements.json` and `verification.json`.",
        "",
        f"- Requirements: {len(reqs)} ({sum(item.get('priority') == 'must' for item in reqs)} must, {sum(item.get('priority') == 'should' for item in reqs)} should)",
        f"- Planned verification checks: {len(dvs)}",
        "",
        "## Requirement allocation",
        "",
        "| ID | Priority | Basis | Architecture refs | Implementation allocations | Verification refs | Statement |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in reqs:
        statement = item["statement"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {item['id']} | {item['priority']} | {item['basis']} | "
            f"{', '.join(sorted(item['architecture_refs']))} | "
            f"{', '.join(sorted(item['allocations']))} | "
            f"{', '.join(sorted(item['verification_refs']))} | {statement} |"
        )
    lines.extend([
        "",
        "## Planned-check index",
        "",
        "| Check ID | Environments | Methods | Name |",
        "|---|---|---|---|",
    ])
    for item in dvs:
        lines.append(
            f"| {item['id']} | {', '.join(sorted(item['environments']))} | "
            f"{', '.join(item['methods'])} | {item['name']} |"
        )
    lines.append("")
    return "\n".join(lines)


def validate(*, write_traceability: bool = False) -> str:
    manifest = _strict_load(SPEC / "manifest.json")
    parameters = _strict_load(SPEC / "parameters.json")
    budgets = _strict_load(SPEC / "budgets.json")
    interfaces = _strict_load(SPEC / "interfaces.json")
    requirements_data = _strict_load(SPEC / "requirements.json")
    verification_data = _strict_load(SPEC / "verification.json")
    fault_campaign = _strict_load(SPEC / "fault_campaign.json")
    coverage_plan = _strict_load(SPEC / "coverage_plan.json")
    coverage_waivers = _strict_load(SPEC / "coverage_waivers.json")
    errors: list[str] = []
    for path, data in (
        ("manifest.json", manifest),
        ("parameters.json", parameters),
        ("budgets.json", budgets),
        ("interfaces.json", interfaces),
        ("requirements.json", requirements_data),
        ("verification.json", verification_data),
        ("fault_campaign.json", fault_campaign),
        ("coverage_plan.json", coverage_plan),
        ("coverage_waivers.json", coverage_waivers),
    ):
        if not isinstance(data, dict) or not isinstance(data.get("schema_version"), int):
            errors.append(f"{path}: missing integer schema_version")
    if manifest.get("evidence_classes") != sorted(manifest.get("evidence_classes", [])):
        errors.append("manifest evidence_classes must be sorted deterministically")
    if set(manifest.get("evidence_classes", [])) != EVIDENCE_CLASSES:
        errors.append("manifest evidence_classes do not match the evidence contract")
    _validate_manifest(manifest, errors, allow_generated_missing=write_traceability)
    errors.extend(_validate_interfaces(interfaces))
    requirements = _validate_ids(requirements_data, "requirements", "requirements", errors)
    checks = _validate_ids(verification_data, "planned_checks", "verification", errors)
    environments = _validate_ids(verification_data, "environments", "verification environments", errors)
    check_ids = {item.get("id") for item in checks}
    env_ids = {item.get("id") for item in environments}
    spec_refs = _spec_refs()
    for item in requirements:
        rid = item.get("id", "<missing>")
        if item.get("priority") not in {"must", "should"}:
            errors.append(f"{rid}: invalid priority")
        if item.get("basis") not in EVIDENCE_CLASSES:
            errors.append(f"{rid}: invalid evidence basis")
        for key in ("allocations", "architecture_refs", "verification_refs"):
            if not isinstance(item.get(key), list) or not item[key]:
                errors.append(f"{rid}: {key} must be non-empty")
        for ref in item.get("verification_refs", []):
            if ref not in check_ids:
                errors.append(f"{rid}: unknown verification reference {ref}")
        for ref in item.get("architecture_refs", []):
            if ref not in spec_refs:
                errors.append(f"{rid}: unknown architecture/spec section {ref}")
        if item.get("priority") == "must" and not item.get("allocations"):
            errors.append(f"{rid}: must requirement lacks implementation allocation")
    for item in checks:
        cid = item.get("id", "<missing>")
        for env in item.get("environments", []):
            if env not in env_ids:
                errors.append(f"{cid}: unknown environment {env}")
    _validate_fault_campaign(fault_campaign, check_ids, errors)
    _validate_coverage_campaign(
        coverage_plan, coverage_waivers, verification_data, check_ids, errors
    )
    _validate_budgets(budgets, errors)
    _validate_models(manifest, parameters, errors)
    normative_paths = [
        ROOT / item["path"]
        for item in manifest.get("documents", [])
        if isinstance(item, dict) and item.get("normative") and isinstance(item.get("path"), str)
    ]
    for path in normative_paths:
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if PLACEHOLDER_RE.search(text):
                errors.append(f"normative placeholder in {path.relative_to(ROOT)}")
    trace = generate_traceability(requirements, checks)
    trace_path = SPEC / "TRACEABILITY.md"
    if write_traceability:
        trace_path.write_text(trace, encoding="utf-8")
    elif trace_path.exists() and trace_path.read_text(encoding="utf-8") != trace:
        errors.append("TRACEABILITY.md is stale; run tools/check_spec.py --write")
    elif not trace_path.exists():
        errors.append("TRACEABILITY.md is missing; run tools/check_spec.py --write")
    if errors:
        raise SpecError("\n".join(f"- {error}" for error in errors))
    return trace


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="write generated TRACEABILITY.md")
    args = parser.parse_args()
    try:
        validate(write_traceability=args.write)
    except SpecError as exc:
        print(f"SPEC CHECK FAILED\n{exc}", file=sys.stderr)
        return 1
    print("SPEC CHECK PASS: schema, interfaces, traceability, budgets, models, and placeholders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
