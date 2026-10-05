#!/usr/bin/env python3
"""Run the canonical public-reference RTL functional/code coverage campaign.

The campaign deliberately uses Icarus and a pinned Verilator as independent
simulation engines.  Code coverage comes from Verilator's native point format;
hierarchy copies are source-deduplicated before thresholds are evaluated.
Open-tool results are logical RTL evidence only, never product signoff.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "rtl" / "build" / "coverage_campaign"
RESULTS = ROOT / "results" / "rtl"
PLAN_PATH = ROOT / "spec" / "coverage_plan.json"
PINNED_VERILATOR_VERSION = "5.050"
DEFAULT_VERILATOR = (
    Path.home()
    / ".local"
    / "opentallas-tools"
    / f"verilator-{PINNED_VERILATOR_VERSION}"
    / "bin"
    / "verilator"
)
BIN_DECL_RE = re.compile(r'pass_bin\s*\(\s*"(COV-[A-Z0-9-]+)"')
BIN_OUTPUT_RE = re.compile(r"^COVER_BIN\s+(COV-[A-Z0-9-]+)\s+(PASS|FAIL)\s*$")
COVERAGE_POINT_RE = re.compile(r"^C '(.*)' ([0-9]+)$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_path(path: str | Path) -> str:
    value = str(path)
    replacements = ((str(ROOT), "<ROOT>"), (str(Path.home()), "<HOME>"))
    for original, replacement in replacements:
        if value == original:
            return replacement
        if value.startswith(original + os.sep):
            return replacement + value[len(original) :]
    return value


def command_text(command: list[str]) -> str:
    return shlex.join([canonical_path(item) for item in command])


def resolve_executable(name: str) -> Path:
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"missing required executable: {name}")
    candidate = Path(found).resolve()
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise RuntimeError(f"required executable is not runnable: {candidate}")
    return candidate


def resolve_verilator() -> Path:
    configured = os.environ.get("OPENTALLAS_VERILATOR")
    if configured:
        candidate = Path(configured).expanduser().resolve()
    elif DEFAULT_VERILATOR.exists():
        candidate = DEFAULT_VERILATOR.resolve()
    else:
        found = shutil.which("verilator")
        candidate = Path(found).resolve() if found else DEFAULT_VERILATOR
    if not candidate.is_file() or not os.access(candidate, os.X_OK):
        raise RuntimeError(
            "pinned Verilator 5.050 is unavailable; run "
            "tools/bootstrap_verilator_5_050.sh or set OPENTALLAS_VERILATOR"
        )
    version_text = subprocess.run(
        [str(candidate), "--version"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    ).stdout.strip()
    if f"Verilator {PINNED_VERILATOR_VERSION}" not in version_text:
        raise RuntimeError(
            f"coverage campaign requires Verilator {PINNED_VERILATOR_VERSION}, "
            f"got: {version_text}"
        )
    return candidate


def tool_record(executable: Path, version_args: list[str]) -> dict[str, Any]:
    run = subprocess.run(
        [str(executable), *version_args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    )
    lines = [line.strip() for line in run.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical_path(executable),
        "executable_sha256": sha256_file(executable),
        "version": lines[0] if lines else "no version text",
    }


def warning_lines(output: str) -> list[str]:
    findings: list[str] = []
    for line in output.splitlines():
        lowered = line.lower()
        if (
            line.startswith("%Warning-")
            or lowered.startswith("warning:")
            or " warning:" in lowered
        ):
            findings.append(line)
    return findings


def run_command(
    command: list[str],
    log_path: Path,
    *,
    timeout: int,
    cwd: Path = ROOT,
) -> dict[str, Any]:
    try:
        run = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        output = run.stdout
        returncode: int | None = run.returncode
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        def decode(value: str | bytes | None) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        output = decode(exc.stdout) + decode(exc.stderr)
        returncode = None
        timed_out = True
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(output, encoding="utf-8")
    return {
        "command": command_text(command),
        "cwd": canonical_path(cwd),
        "log": str(log_path.relative_to(ROOT)),
        "returncode": returncode,
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "output": output,
        "warnings": warning_lines(output),
    }


def compact_phase(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "output"}


def validate_plan() -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    errors: list[str] = []
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    if plan.get("schema_version") != 1:
        errors.append("coverage plan schema_version must be 1")
    cases = plan.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("coverage plan has no cases")
        cases = []

    verification = json.loads(
        (ROOT / "spec" / "verification.json").read_text(encoding="utf-8")
    )
    closure = verification["closure"]
    expected_thresholds = {
        "line_percent": float(closure["line_coverage_percent"]),
        "branch_percent": float(closure["branch_coverage_percent"]),
        "toggle_percent": float(closure["toggle_coverage_percent"]),
        "must_bin_percent": float(closure["functional_coverage_must_bins_percent"]),
        "fsm_state_bin_percent": float(closure["fsm_state_bins_percent"]),
    }
    if plan.get("thresholds") != expected_thresholds:
        errors.append(
            f"coverage thresholds disagree with verification closure: "
            f"expected {expected_thresholds}"
        )

    valid_requirements = {item["id"] for item in verification["planned_checks"]}
    allowed_suppressions = set(
        plan.get("warning_policy", {})
        .get("verilator_suppressions", {})
    )
    planned_bins: list[str] = []
    case_names: list[str] = []
    benches: list[str] = []
    for case_index, case in enumerate(cases):
        required = {
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
        missing = sorted(required - set(case))
        if missing:
            errors.append(
                f"coverage case {case_index} missing fields: {', '.join(missing)}"
            )
            continue
        case_names.append(case["name"])
        benches.append(case["bench"])
        if re.fullmatch(r"[a-z0-9_]+", case["name"]) is None:
            errors.append(f"invalid coverage case name: {case['name']!r}")
        if re.fullmatch(r"[0-9a-f]{8}", case["seed_hex"]) is None:
            errors.append(f"{case['name']}: seed_hex must be eight lowercase hex digits")
        unknown_suppressions = sorted(
            set(case["verilator_suppressions"]) - allowed_suppressions
        )
        if unknown_suppressions:
            errors.append(
                f"{case['name']}: undeclared Verilator suppressions "
                f"{unknown_suppressions}"
            )
        unknown_requirements = sorted(set(case["requirements"]) - valid_requirements)
        if unknown_requirements:
            errors.append(
                f"{case['name']}: unknown verification checks {unknown_requirements}"
            )
        if not case["requirements"]:
            errors.append(f"{case['name']}: no verification requirements")
        if case["bench"] not in case["sources"]:
            errors.append(f"{case['name']}: bench is absent from source list")
        for source in case["sources"]:
            source_path = ROOT / source
            if not source_path.is_file():
                errors.append(f"{case['name']}: missing source {source}")
        bench_path = ROOT / case["bench"]
        if bench_path.is_file():
            bench_text = bench_path.read_text(encoding="utf-8")
            if f"module {case['top']}" not in bench_text:
                errors.append(
                    f"{case['name']}: top {case['top']} not declared in bench"
                )
            if case["seed_hex"] not in bench_text.lower().replace("_", ""):
                errors.append(f"{case['name']}: seed is not present in bench source")
        for bin_id in case["bins"]:
            if re.fullmatch(r"COV-[A-Z0-9-]+", bin_id) is None:
                errors.append(f"{case['name']}: invalid bin ID {bin_id!r}")
            planned_bins.append(bin_id)

    for label, values in (("case name", case_names), ("bench", benches), ("bin", planned_bins)):
        duplicates = sorted(value for value, count in Counter(values).items() if count != 1)
        if duplicates:
            errors.append(f"duplicate coverage {label}s: {duplicates}")

    declared_bins: list[str] = []
    for bench in benches:
        path = ROOT / bench
        if path.is_file():
            declared_bins.extend(BIN_DECL_RE.findall(path.read_text(encoding="utf-8")))
    duplicate_declarations = sorted(
        item for item, count in Counter(declared_bins).items() if count != 1
    )
    if duplicate_declarations:
        errors.append(f"duplicate source bin declarations: {duplicate_declarations}")
    missing_declarations = sorted(set(planned_bins) - set(declared_bins))
    stale_declarations = sorted(set(declared_bins) - set(planned_bins))
    if missing_declarations:
        errors.append(f"planned bins absent from source: {missing_declarations}")
    if stale_declarations:
        errors.append(f"source bins absent from plan: {stale_declarations}")

    fsm_bins = plan.get("fsm_state_bins")
    if not isinstance(fsm_bins, list) or not fsm_bins:
        errors.append("coverage plan has no FSM state bins")
        fsm_bins = []
    if len(fsm_bins) != len(set(fsm_bins)):
        errors.append("coverage plan has duplicate FSM state bins")
    if set(fsm_bins) != {item for item in planned_bins if item.startswith("COV-FSM-")}:
        errors.append("fsm_state_bins must exactly match planned COV-FSM-* bins")

    waiver_name = plan.get("waiver_file")
    if not isinstance(waiver_name, str):
        errors.append("coverage plan has no waiver_file")
        waivers: dict[str, Any] = {"waivers": []}
    else:
        waiver_path = ROOT / waiver_name
        if not waiver_path.is_file():
            errors.append(f"coverage waiver file does not exist: {waiver_name}")
            waivers = {"waivers": []}
        else:
            waivers = json.loads(waiver_path.read_text(encoding="utf-8"))
    if waivers.get("schema_version") != 1:
        errors.append("coverage waiver schema_version must be 1")
    waiver_entries = waivers.get("waivers")
    if not isinstance(waiver_entries, list):
        errors.append("coverage waivers must be a list")
        waivers["waivers"] = []
    return plan, waivers, errors


def diagnostics_allowed(
    warnings: Iterable[str], allowed_patterns: list[re.Pattern[str]]
) -> tuple[list[str], list[str]]:
    allowed: list[str] = []
    unexpected: list[str] = []
    for warning in warnings:
        if any(pattern.fullmatch(warning) for pattern in allowed_patterns):
            allowed.append(warning)
        else:
            unexpected.append(warning)
    return allowed, unexpected


def parse_bin_output(output: str) -> tuple[list[str], list[str]]:
    passed: list[str] = []
    failed: list[str] = []
    for line in output.splitlines():
        match = BIN_OUTPUT_RE.fullmatch(line.strip())
        if match:
            (passed if match.group(2) == "PASS" else failed).append(match.group(1))
    return passed, failed


def semantic_output(output: str) -> str:
    lines = []
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("COVER_BIN ") or stripped.startswith("PASS:"):
            lines.append(stripped)
    return "\n".join(lines) + "\n"


def simulation_failure_text(output: str) -> list[str]:
    bad: list[str] = []
    for line in output.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("FAIL")
            or stripped.startswith("FATAL")
            or stripped.startswith("%Error")
            or "Assertion failed" in stripped
        ):
            bad.append(line)
    return bad


def validate_observations(
    output: str, expected_bins: list[str], marker: str
) -> tuple[bool, dict[str, Any]]:
    passed, failed = parse_bin_output(output)
    counts = Counter(passed)
    duplicate = sorted(item for item, count in counts.items() if count != 1)
    missing = sorted(set(expected_bins) - set(passed))
    unexpected = sorted(set(passed) - set(expected_bins))
    fatal_text = simulation_failure_text(output)
    ok = not (failed or duplicate or missing or unexpected or fatal_text) and marker in output
    return ok, {
        "planned_count": len(expected_bins),
        "passed_count": len(passed),
        "passed_ids": passed,
        "failed_ids": failed,
        "duplicate_ids": duplicate,
        "missing_ids": missing,
        "unexpected_ids": unexpected,
        "required_marker": marker,
        "required_marker_seen": marker in output,
        "fatal_text": fatal_text,
    }


def run_case(
    case: dict[str, Any],
    *,
    iverilog: Path,
    vvp: Path,
    verilator: Path,
    allowed_iverilog_warnings: list[re.Pattern[str]],
) -> tuple[dict[str, Any], Path | None]:
    print(f"coverage: {case['name']}", flush=True)
    case_build = BUILD / case["name"]
    iverilog_build = case_build / "iverilog"
    verilator_build = case_build / "verilator"
    iverilog_build.mkdir(parents=True, exist_ok=True)
    verilator_build.mkdir(parents=True, exist_ok=True)
    sources = [str(ROOT / item) for item in case["sources"]]

    vvp_image = iverilog_build / f"{case['top']}.vvp"
    iverilog_compile = run_command(
        [
            str(iverilog),
            "-g2012",
            "-Wall",
            "-s",
            case["top"],
            "-o",
            str(vvp_image),
            *sources,
        ],
        iverilog_build / "compile.log",
        timeout=180,
    )
    allowed, unexpected = diagnostics_allowed(
        iverilog_compile["warnings"], allowed_iverilog_warnings
    )
    iverilog_compile["allowed_warnings"] = allowed
    iverilog_compile["unexpected_warnings"] = unexpected
    compile_ok = (
        iverilog_compile["returncode"] == 0
        and not iverilog_compile["timed_out"]
        and not unexpected
        and vvp_image.is_file()
    )
    if compile_ok:
        iverilog_run = run_command(
            [str(vvp), "-n", str(vvp_image)],
            iverilog_build / "run.log",
            timeout=240,
        )
        sim_warnings_allowed, sim_warnings_unexpected = diagnostics_allowed(
            iverilog_run["warnings"], allowed_iverilog_warnings
        )
        iverilog_run["allowed_warnings"] = sim_warnings_allowed
        iverilog_run["unexpected_warnings"] = sim_warnings_unexpected
        observations_ok, iverilog_observations = validate_observations(
            iverilog_run["output"], case["bins"], case["pass_marker"]
        )
        iverilog_semantic = semantic_output(iverilog_run["output"])
        iverilog_ok = (
            iverilog_run["returncode"] == 0
            and not iverilog_run["timed_out"]
            and not sim_warnings_unexpected
            and observations_ok
        )
    else:
        iverilog_run = {
            "command": None,
            "cwd": canonical_path(ROOT),
            "log": None,
            "returncode": None,
            "timeout_seconds": 240,
            "timed_out": False,
            "warnings": [],
            "allowed_warnings": [],
            "unexpected_warnings": [],
        }
        iverilog_observations = {
            "planned_count": len(case["bins"]),
            "passed_count": 0,
            "passed_ids": [],
            "failed_ids": [],
            "duplicate_ids": [],
            "missing_ids": list(case["bins"]),
            "unexpected_ids": [],
            "required_marker": case["pass_marker"],
            "required_marker_seen": False,
            "fatal_text": [],
        }
        iverilog_semantic = ""
        iverilog_ok = False

    verilator_command = [
        str(verilator),
        "--binary",
        "--timing",
        "--coverage",
        "-Wall",
    ]
    verilator_command.extend(
        f"-Wno-{item}" for item in case["verilator_suppressions"]
    )
    verilator_command.extend(
        [
            "--top-module",
            case["top"],
            "--Mdir",
            str(verilator_build),
            *sources,
        ]
    )
    verilator_compile = run_command(
        verilator_command,
        verilator_build / "compile.log",
        timeout=900,
    )
    verilator_compile["unexpected_warnings"] = verilator_compile["warnings"]
    verilator_executable = verilator_build / f"V{case['top']}"
    verilator_compile_ok = (
        verilator_compile["returncode"] == 0
        and not verilator_compile["timed_out"]
        and not verilator_compile["warnings"]
        and verilator_executable.is_file()
    )
    coverage_path: Path | None = None
    if verilator_compile_ok:
        verilator_run = run_command(
            [str(verilator_executable)],
            verilator_build / "run.log",
            timeout=240,
            cwd=verilator_build,
        )
        verilator_run["unexpected_warnings"] = verilator_run["warnings"]
        observations_ok, verilator_observations = validate_observations(
            verilator_run["output"], case["bins"], case["pass_marker"]
        )
        verilator_semantic = semantic_output(verilator_run["output"])
        candidate_coverage = verilator_build / "coverage.dat"
        coverage_path = candidate_coverage if candidate_coverage.is_file() else None
        verilator_ok = (
            verilator_run["returncode"] == 0
            and not verilator_run["timed_out"]
            and not verilator_run["warnings"]
            and observations_ok
            and coverage_path is not None
        )
    else:
        verilator_run = {
            "command": None,
            "cwd": canonical_path(verilator_build),
            "log": None,
            "returncode": None,
            "timeout_seconds": 240,
            "timed_out": False,
            "warnings": [],
            "unexpected_warnings": [],
        }
        verilator_observations = {
            "planned_count": len(case["bins"]),
            "passed_count": 0,
            "passed_ids": [],
            "failed_ids": [],
            "duplicate_ids": [],
            "missing_ids": list(case["bins"]),
            "unexpected_ids": [],
            "required_marker": case["pass_marker"],
            "required_marker_seen": False,
            "fatal_text": [],
        }
        verilator_semantic = ""
        verilator_ok = False

    semantic_match = bool(iverilog_semantic) and iverilog_semantic == verilator_semantic
    source_hashes = {
        source: sha256_file(ROOT / source) for source in sorted(case["sources"])
    }
    passed = iverilog_ok and verilator_ok and semantic_match
    record = {
        "name": case["name"],
        "top": case["top"],
        "bench": case["bench"],
        "seed_hex": case["seed_hex"],
        "status": "pass" if passed else "fail",
        "requirements": case["requirements"],
        "source_sha256": source_hashes,
        "planned_bins": case["bins"],
        "iverilog": {
            "status": "pass" if iverilog_ok else "fail",
            "compile": compact_phase(iverilog_compile),
            "run": compact_phase(iverilog_run),
            "observations": iverilog_observations,
            "semantic_output_sha256": sha256_text(iverilog_semantic),
            "image": str(vvp_image.relative_to(ROOT)) if vvp_image.is_file() else None,
            "image_sha256": sha256_file(vvp_image) if vvp_image.is_file() else None,
        },
        "verilator": {
            "status": "pass" if verilator_ok else "fail",
            "warning_suppressions": case["verilator_suppressions"],
            "compile": compact_phase(verilator_compile),
            "run": compact_phase(verilator_run),
            "observations": verilator_observations,
            "semantic_output_sha256": sha256_text(verilator_semantic),
            "executable": (
                str(verilator_executable.relative_to(ROOT))
                if verilator_executable.is_file()
                else None
            ),
            "executable_sha256": (
                sha256_file(verilator_executable)
                if verilator_executable.is_file()
                else None
            ),
            "coverage_data": (
                str(coverage_path.relative_to(ROOT)) if coverage_path else None
            ),
            "coverage_data_sha256": sha256_file(coverage_path) if coverage_path else None,
        },
        "semantic_outputs_match": semantic_match,
    }
    return record, coverage_path


CoverageKey = tuple[str, int, int, str, str, str, str]


def normalize_source_file(value: str) -> str:
    path = value.replace("\\", "/")
    root_text = str(ROOT).replace("\\", "/") + "/"
    if path.startswith(root_text):
        path = path[len(root_text) :]
    while path.startswith("./"):
        path = path[2:]
    return path


def parse_coverage_file(
    path: Path, dut_sources: set[str]
) -> dict[CoverageKey, int]:
    points: dict[CoverageKey, int] = defaultdict(int)
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = COVERAGE_POINT_RE.fullmatch(line)
        if not match:
            continue
        metadata, count_text = match.groups()
        fields: dict[str, str] = {}
        for field in metadata.split("\x01"):
            if "\x02" in field:
                key, value = field.split("\x02", 1)
                fields[key] = value
        filename = normalize_source_file(fields.get("f", "unknown"))
        if filename not in dut_sources:
            continue
        point_class = fields.get("page", "unknown").split("/", 1)[0]
        key = (
            filename,
            int(fields.get("l", "0")),
            int(fields.get("n", "0")),
            point_class,
            fields.get("t", ""),
            fields.get("o", ""),
            fields.get("S", ""),
        )
        points[key] += int(count_text)
    return points


def point_dict(key: CoverageKey, count: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "file": key[0],
        "line": key[1],
        "column": key[2],
        "point_class": key[3],
        "point_type": key[4],
        "description": key[5],
        "source_span": key[6],
    }
    if count is not None:
        result["count"] = count
    return result


def validate_waivers(
    waiver_doc: dict[str, Any], points: dict[CoverageKey, int]
) -> tuple[set[CoverageKey], list[dict[str, Any]], list[str]]:
    excluded: set[CoverageKey] = set()
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    required = {
        "id",
        "owner",
        "reason",
        "review_disposition",
        "requirement_impact",
        "revalidate_on",
        "point",
    }
    point_fields = {
        "file",
        "line",
        "column",
        "point_class",
        "point_type",
        "description",
        "source_span",
    }
    ids: list[str] = []
    for index, waiver in enumerate(waiver_doc.get("waivers", [])):
        missing = sorted(required - set(waiver))
        if missing:
            errors.append(f"coverage waiver {index} missing fields: {', '.join(missing)}")
            continue
        ids.append(waiver["id"])
        point = waiver["point"]
        if not isinstance(point, dict) or set(point) != point_fields:
            errors.append(
                f"coverage waiver {waiver['id']} must identify every exact point field"
            )
            continue
        key: CoverageKey = (
            point["file"],
            point["line"],
            point["column"],
            point["point_class"],
            point["point_type"],
            point["description"],
            point["source_span"],
        )
        if key not in points:
            errors.append(f"coverage waiver {waiver['id']} is stale or moved")
            continue
        if key in excluded:
            errors.append(f"coverage point waived more than once: {waiver['id']}")
            continue
        for field in (
            "owner",
            "reason",
            "review_disposition",
            "requirement_impact",
            "revalidate_on",
        ):
            if not isinstance(waiver[field], str) or not waiver[field].strip():
                errors.append(f"coverage waiver {waiver['id']} has empty {field}")
        excluded.add(key)
        records.append({**waiver, "native_count": points[key]})
    duplicate_ids = sorted(item for item, count in Counter(ids).items() if count != 1)
    if duplicate_ids:
        errors.append(f"duplicate coverage waiver IDs: {duplicate_ids}")
    return excluded, records, errors


def metric_summary(
    points: dict[CoverageKey, int],
    classes: dict[str, str],
    excluded: set[CoverageKey],
) -> tuple[dict[str, Any], dict[str, Any]]:
    totals: dict[str, Any] = {}
    per_file: dict[str, Any] = {}
    files = sorted({key[0] for key in points})
    for label, point_class in classes.items():
        selected = [
            (key, count)
            for key, count in points.items()
            if key[3] == point_class and key not in excluded
        ]
        hit = sum(count > 0 for _, count in selected)
        total = len(selected)
        totals[label] = {
            "hit": hit,
            "total": total,
            "percent": round(100.0 * hit / total, 3) if total else None,
        }
    for filename in files:
        per_file[filename] = {}
        for label, point_class in classes.items():
            selected = [
                (key, count)
                for key, count in points.items()
                if key[0] == filename and key[3] == point_class and key not in excluded
            ]
            hit = sum(count > 0 for _, count in selected)
            total = len(selected)
            per_file[filename][label] = {
                "hit": hit,
                "total": total,
                "percent": round(100.0 * hit / total, 3) if total else None,
            }
    return totals, per_file


def render_report(summary: dict[str, Any]) -> str:
    raw = summary["coverage"]["raw"]
    reviewed = summary["coverage"]["post_reviewed_exclusions"]
    thresholds = summary["thresholds"]
    lines = [
        "# Public-reference RTL coverage campaign",
        "",
        f"**Overall status:** {summary['status'].upper()}",
        "",
        f"{len(summary['cases'])} deterministic self-checking benches pass under Icarus and "
        "pinned Verilator 5.050. Native Verilator points are merged by source location and description, so "
        "repeated hierarchy instances and repeated case elaborations do not inflate the result.",
        "",
        "## Closure",
        "",
        "| Metric | Raw hit/total | Raw | Post-exclusion hit/total | Post-exclusion | Target | Result |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    threshold_key = {"line": "line_percent", "branch": "branch_percent", "toggle": "toggle_percent"}
    for metric in ("line", "branch", "toggle"):
        target = thresholds[threshold_key[metric]]
        passed = reviewed[metric]["percent"] is not None and reviewed[metric]["percent"] >= target
        lines.append(
            f"| {metric.title()} | {raw[metric]['hit']}/{raw[metric]['total']} | "
            f"{raw[metric]['percent']:.3f}% | {reviewed[metric]['hit']}/{reviewed[metric]['total']} | "
            f"{reviewed[metric]['percent']:.3f}% | {target:.1f}% | "
            f"{'PASS' if passed else 'FAIL'} |"
        )
    bins = summary["functional_coverage"]
    fsm = summary["fsm_state_coverage"]
    lines.extend(
        [
            f"| Must bins | {bins['hit']}/{bins['total']} | {bins['percent']:.3f}% | "
            f"{bins['hit']}/{bins['total']} | {bins['percent']:.3f}% | "
            f"{thresholds['must_bin_percent']:.1f}% | {bins['status'].upper()} |",
            f"| FSM state bins | {fsm['hit']}/{fsm['total']} | {fsm['percent']:.3f}% | "
            f"{fsm['hit']}/{fsm['total']} | {fsm['percent']:.3f}% | "
            f"{thresholds['fsm_state_bin_percent']:.1f}% | {fsm['status'].upper()} |",
            "",
            "## Simulator cases",
            "",
            "| Case | Seed | Bins | Icarus | Verilator | Semantic match |",
            "|---|---:|---:|---|---|---|",
        ]
    )
    for case in summary["cases"]:
        lines.append(
            f"| `{case['name']}` | `0x{case['seed_hex']}` | {len(case['planned_bins'])} | "
            f"{case['iverilog']['status'].upper()} | {case['verilator']['status'].upper()} | "
            f"{'PASS' if case['semantic_outputs_match'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Per-file post-exclusion coverage",
            "",
            "| RTL source | Line | Branch | Toggle |",
            "|---|---:|---:|---:|",
        ]
    )
    for filename, metrics in summary["coverage"]["per_file_post_exclusions"].items():
        def value(metric: str) -> str:
            item = metrics[metric]
            if item["percent"] is None:
                return "n/a"
            return f"{item['hit']}/{item['total']} ({item['percent']:.3f}%)"

        lines.append(
            f"| `{filename}` | {value('line')} | {value('branch')} | {value('toggle')} |"
        )
    lines.extend(["", "## Reviewed exclusions", ""])
    exclusions = summary["coverage"]["reviewed_exclusions"]
    if exclusions:
        lines.extend(
            [
                "| ID | Exact point | Owner | Reason | Revalidate |",
                "|---|---|---|---|---|",
            ]
        )
        for waiver in exclusions:
            point = waiver["point"]
            location = f"{point['file']}:{point['line']}:{point['column']} {point['point_class']}"
            lines.append(
                f"| `{waiver['id']}` | `{location}` | {waiver['owner']} | "
                f"{waiver['reason']} | {waiver['revalidate_on']} |"
            )
    else:
        lines.append("No coverage points are excluded.")
    lines.extend(
        [
            "",
            "## Accounting and evidence boundary",
            "",
            f"- Raw source points: {summary['coverage']['raw_point_count']:,}.",
            f"- Reviewed exact exclusions: {len(exclusions)}.",
            f"- Source-deduplicated uncovered-point audit SHA-256: "
            f"`{summary['coverage']['uncovered_points_sha256']}`.",
            "- Icarus array-sensitivity messages matching the plan's exact allow pattern are "
            "recorded as informational; every other warning is fatal to the campaign.",
            "- Verilator width and lint warnings remain fatal. The only suppressions are the "
            "named timed-bench diagnostics and the separately gated full-stage SYNCASYNCNET case.",
            "- This is public-tool logical RTL evidence. It does not establish target-node timing, "
            "power, physical fault coverage, ATPG, ROM/HBM/PHY macro behavior, package behavior, "
            "manufacturability, model numerical quality, or product-silicon signoff.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        plan, waiver_doc, validation_errors = validate_plan()
        if validation_errors:
            raise RuntimeError("; ".join(validation_errors))
        iverilog = resolve_executable("iverilog")
        vvp = resolve_executable("vvp")
        verilator = resolve_verilator()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"coverage campaign setup failed: {exc}", file=sys.stderr)
        return 2

    # BUILD is owned exclusively by this runner.  Refuse any accidental path
    # broadening before replacing stale generated evidence.
    expected_build = ROOT / "rtl" / "build" / "coverage_campaign"
    if BUILD != expected_build or ROOT not in BUILD.parents:
        print("coverage build path safety check failed", file=sys.stderr)
        return 2
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    allowed_patterns = [
        re.compile(item)
        for item in plan["warning_policy"]["iverilog_allowed_patterns"]
    ]
    cases: list[dict[str, Any]] = []
    coverage_paths: list[tuple[dict[str, Any], Path]] = []
    for case in plan["cases"]:
        record, coverage_path = run_case(
            case,
            iverilog=iverilog,
            vvp=vvp,
            verilator=verilator,
            allowed_iverilog_warnings=allowed_patterns,
        )
        cases.append(record)
        if coverage_path is not None:
            coverage_paths.append((case, coverage_path))

    dut_sources = {
        source
        for case in plan["cases"]
        for source in case["sources"]
        if source.startswith("rtl/") and not source.startswith("rtl/test/")
    }
    merged_points: dict[CoverageKey, int] = defaultdict(int)
    point_cases: dict[CoverageKey, set[str]] = defaultdict(set)
    for case, path in coverage_paths:
        for key, count in parse_coverage_file(path, dut_sources).items():
            merged_points[key] += count
            point_cases[key].add(case["name"])

    excluded, exclusion_records, waiver_errors = validate_waivers(
        waiver_doc, merged_points
    )
    classes = plan["point_accounting"]["classes"]
    raw_metrics, raw_per_file = metric_summary(merged_points, classes, set())
    reviewed_metrics, reviewed_per_file = metric_summary(
        merged_points, classes, excluded
    )
    uncovered = [
        {
            **point_dict(key, count),
            "cases": sorted(point_cases[key]),
            "excluded": key in excluded,
        }
        for key, count in sorted(merged_points.items())
        if count == 0
    ]
    uncovered_text = json.dumps(uncovered, indent=2, sort_keys=True) + "\n"
    uncovered_path = BUILD / "uncovered_points.json"
    uncovered_path.write_text(uncovered_text, encoding="utf-8")

    thresholds = plan["thresholds"]
    metric_thresholds = {
        "line": thresholds["line_percent"],
        "branch": thresholds["branch_percent"],
        "toggle": thresholds["toggle_percent"],
    }
    code_coverage_pass = bool(merged_points) and all(
        reviewed_metrics[label]["percent"] is not None
        and reviewed_metrics[label]["percent"] >= target
        for label, target in metric_thresholds.items()
    )

    planned_bins = [bin_id for case in plan["cases"] for bin_id in case["bins"]]
    case_pass = all(case["status"] == "pass" for case in cases)
    observed_by_both = {
        bin_id
        for case in cases
        if case["iverilog"]["status"] == "pass" and case["verilator"]["status"] == "pass"
        for bin_id in case["planned_bins"]
    }
    bin_hit = len(set(planned_bins) & observed_by_both)
    bin_total = len(planned_bins)
    bin_percent = 100.0 * bin_hit / bin_total if bin_total else 0.0
    bin_pass = bin_percent >= thresholds["must_bin_percent"]
    fsm_bins = set(plan["fsm_state_bins"])
    fsm_hit = len(fsm_bins & observed_by_both)
    fsm_total = len(fsm_bins)
    fsm_percent = 100.0 * fsm_hit / fsm_total if fsm_total else 0.0
    fsm_pass = fsm_percent >= thresholds["fsm_state_bin_percent"]
    waiver_pass = not waiver_errors
    passed = case_pass and code_coverage_pass and bin_pass and fsm_pass and waiver_pass

    source_paths = sorted(
        dut_sources
        | {case["bench"] for case in plan["cases"]}
        | {
            "spec/coverage_plan.json",
            plan["waiver_file"],
            "spec/verification.json",
            "tools/rtl_coverage_campaign.py",
        }
    )
    summary = {
        "schema_version": 1,
        "campaign": plan["campaign"],
        "status": "pass" if passed else "fail",
        "evidence_class": plan["evidence_class"],
        "evidence_boundary": plan["evidence_boundary"],
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "tools": {
            "iverilog": tool_record(iverilog, ["-V"]),
            "vvp": tool_record(vvp, ["-V"]),
            "verilator": tool_record(verilator, ["--version"]),
        },
        "thresholds": thresholds,
        "source_sha256": {
            source: sha256_file(ROOT / source) for source in source_paths
        },
        "cases": cases,
        "functional_coverage": {
            "status": "pass" if bin_pass else "fail",
            "hit": bin_hit,
            "total": bin_total,
            "percent": round(bin_percent, 3),
            "criterion": "each planned bin appears exactly once under both simulators",
            "missing_ids": sorted(set(planned_bins) - observed_by_both),
        },
        "fsm_state_coverage": {
            "status": "pass" if fsm_pass else "fail",
            "hit": fsm_hit,
            "total": fsm_total,
            "percent": round(fsm_percent, 3),
            "missing_ids": sorted(fsm_bins - observed_by_both),
        },
        "coverage": {
            "native_format": plan["point_accounting"]["native_format"],
            "deduplication_key": plan["point_accounting"]["source_deduplication_key"],
            "raw_point_count": len(merged_points),
            "raw": raw_metrics,
            "post_reviewed_exclusions": reviewed_metrics,
            "per_file_raw": raw_per_file,
            "per_file_post_exclusions": reviewed_per_file,
            "reviewed_exclusions": exclusion_records,
            "waiver_validation_errors": waiver_errors,
            "uncovered_point_count": len(uncovered),
            "uncovered_points_audit": str(uncovered_path.relative_to(ROOT)),
            "uncovered_points_sha256": sha256_text(uncovered_text),
        },
        "gates": {
            "all_simulator_cases_pass": case_pass,
            "code_coverage_thresholds_pass": code_coverage_pass,
            "must_bins_pass": bin_pass,
            "fsm_state_bins_pass": fsm_pass,
            "coverage_waivers_valid": waiver_pass,
        },
        "limitations": [
            "coverage is source-deduplicated across reduced public-reference configurations",
            "reviewed exclusions, if any, are exact source points and are never file-wide",
            "public/open tools do not establish target-node or product signoff",
        ],
    }
    result_path = RESULTS / "coverage_campaign.json"
    report_path = RESULTS / "COVERAGE_REPORT.md"
    result_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    report_path.write_text(render_report(summary), encoding="utf-8")
    print(
        "coverage campaign: "
        f"{summary['status'].upper()} "
        f"line={reviewed_metrics['line']['percent']}% "
        f"branch={reviewed_metrics['branch']['percent']}% "
        f"toggle={reviewed_metrics['toggle']['percent']}% "
        f"bins={bin_hit}/{bin_total} fsm={fsm_hit}/{fsm_total}",
        flush=True,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
