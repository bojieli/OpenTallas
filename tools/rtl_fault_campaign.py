#!/usr/bin/env python3
"""Run the source-checked dual-simulator public RTL fault campaign.

The pass claim is deliberately limited to the site IDs enumerated in
``spec/fault_campaign.json``.  It is not ATPG, macro, PDK, PHY, physical-fault,
manufacturing, or product-signoff evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "rtl" / "build" / "fault_campaign"
RESULTS = ROOT / "results" / "rtl"
PLAN_PATH = ROOT / "spec" / "fault_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
DEFAULT_VERILATOR = (
    Path.home()
    / ".local"
    / "opentallas-tools"
    / f"verilator-{PINNED_VERILATOR_VERSION}"
    / "bin"
    / "verilator"
)
SITE_DECL_RE = re.compile(r'check_site\s*\(\s*"(FC-[A-Z0-9-]+)"')
SITE_OUTPUT_RE = re.compile(r"^FAULT_SITE\s+(FC-[A-Z0-9-]+)\s+(PASS|FAIL)\s*$")


@dataclass(frozen=True)
class FaultCase:
    name: str
    bench: str
    top: str
    sources: tuple[str, ...]


CASES = (
    FaultCase(
        "fault_data",
        "rtl/test/tb_fault_data.sv",
        "tb_fault_data",
        (
            "rtl/ot_route_mask.sv",
            "rtl/ot_rom_wrapper.sv",
            "rtl/ot_hbm_frontend.sv",
            "rtl/test/tb_fault_data.sv",
        ),
    ),
    FaultCase(
        "fault_link",
        "rtl/test/tb_fault_link.sv",
        "tb_fault_link",
        (
            "rtl/ot_stage_link_rx.sv",
            "rtl/ot_stage_link_tx.sv",
            "rtl/test/tb_fault_link.sv",
        ),
    ),
    FaultCase(
        "fault_ras_dft",
        "rtl/test/tb_fault_ras_dft.sv",
        "tb_fault_ras_dft",
        (
            "rtl/ot_ras_controller.sv",
            "rtl/ot_bist_controller.sv",
            "rtl/ot_dft_controller.sv",
            "rtl/test/tb_fault_ras_dft.sv",
        ),
    ),
    FaultCase(
        "fault_control",
        "rtl/test/tb_fault_control.sv",
        "tb_fault_control",
        (
            "rtl/ot_power_reset_controller.sv",
            "rtl/ot_schedule_controller.sv",
            "rtl/ot_session_table.sv",
            "rtl/ot_stage_controller.sv",
            "rtl/test/tb_fault_control.sv",
        ),
    ),
)


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
    replacements = (
        (str(ROOT), "<ROOT>"),
        (str(Path.home()), "<HOME>"),
    )
    for original, replacement in replacements:
        if value == original:
            return replacement
        if value.startswith(original + os.sep):
            return replacement + value[len(original) :]
    return value


def command_text(command: list[str], aliases: dict[str, str]) -> str:
    normalized: list[str] = []
    for index, argument in enumerate(command):
        if index == 0 and argument in aliases:
            normalized.append(aliases[argument])
        else:
            normalized.append(canonical_path(argument))
    return shlex.join(normalized)


def resolve_executable(name: str) -> Path:
    found = shutil.which(name)
    if found is None:
        raise RuntimeError(f"missing required executable: {name}")
    return Path(found).resolve()


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
    version = subprocess.run(
        [str(candidate), "--version"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    ).stdout.strip()
    if f"Verilator {PINNED_VERILATOR_VERSION}" not in version:
        raise RuntimeError(
            f"fault campaign requires Verilator {PINNED_VERILATOR_VERSION}, got: {version}"
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
        if line.startswith("%Warning-") or " warning:" in lowered or lowered.startswith("warning:"):
            findings.append(line)
    return findings


def run_command(
    command: list[str],
    log_path: Path,
    *,
    timeout: int,
    aliases: dict[str, str],
) -> dict[str, Any]:
    try:
        run = subprocess.run(
            command,
            cwd=ROOT,
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
        "command": command_text(command, aliases),
        "log": str(log_path.relative_to(ROOT)),
        "returncode": returncode,
        "timeout_seconds": timeout,
        "timed_out": timed_out,
        "output": output,
        "warnings": warning_lines(output),
    }


def load_and_validate_plan() -> tuple[dict[str, Any], dict[str, set[str]]]:
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    sites = plan.get("sites")
    if not isinstance(sites, list) or not sites:
        raise RuntimeError("fault plan has no sites")
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
    planned_by_bench: dict[str, set[str]] = defaultdict(set)
    valid_benches = {case.bench for case in CASES}
    verification = json.loads(
        (ROOT / "spec" / "verification.json").read_text(encoding="utf-8")
    )
    valid_checks = {entry["id"] for entry in verification["planned_checks"]}
    for index, site in enumerate(sites):
        missing = sorted(required_fields - set(site))
        if missing:
            raise RuntimeError(f"fault site {index} missing fields: {', '.join(missing)}")
        site_id = site["id"]
        if re.fullmatch(r"FC-[A-Z0-9-]+", site_id) is None:
            raise RuntimeError(f"invalid fault site ID: {site_id!r}")
        if site["bench"] not in valid_benches:
            raise RuntimeError(f"{site_id}: unknown bench {site['bench']!r}")
        if not site["verification_requirements"]:
            raise RuntimeError(f"{site_id}: no verification requirement")
        unknown_checks = sorted(set(site["verification_requirements"]) - valid_checks)
        if unknown_checks:
            raise RuntimeError(f"{site_id}: unknown checks {unknown_checks}")
        for field in ("fault_class", "expected_observation", "containment", "recovery"):
            if not isinstance(site[field], str) or not site[field].strip():
                raise RuntimeError(f"{site_id}: empty {field}")
        planned_ids.append(site_id)
        planned_by_bench[site["bench"]].add(site_id)
    duplicate_plan = sorted(site for site, count in Counter(planned_ids).items() if count != 1)
    if duplicate_plan:
        raise RuntimeError(f"duplicate planned fault IDs: {duplicate_plan}")
    if plan.get("planned_site_count") != len(sites):
        raise RuntimeError("planned_site_count does not match sites array")

    declared_ids: list[str] = []
    declared_by_bench: dict[str, set[str]] = defaultdict(set)
    for case in CASES:
        text = (ROOT / case.bench).read_text(encoding="utf-8")
        bench_ids = SITE_DECL_RE.findall(text)
        declared_ids.extend(bench_ids)
        declared_by_bench[case.bench].update(bench_ids)
    duplicate_source = sorted(site for site, count in Counter(declared_ids).items() if count != 1)
    if duplicate_source:
        raise RuntimeError(f"duplicate declared fault IDs: {duplicate_source}")
    missing_source = sorted(set(planned_ids) - set(declared_ids))
    stale_source = sorted(set(declared_ids) - set(planned_ids))
    if missing_source or stale_source:
        raise RuntimeError(
            f"fault plan/source mismatch; missing declarations={missing_source}, "
            f"unplanned declarations={stale_source}"
        )
    for bench in valid_benches:
        if planned_by_bench[bench] != declared_by_bench[bench]:
            raise RuntimeError(f"fault IDs assigned to wrong bench: {bench}")
    if len(plan.get("external_gates", [])) < 1:
        raise RuntimeError("fault plan must name external/non-modeled gates")
    return plan, planned_by_bench


def validate_site_output(output: str, expected: set[str]) -> dict[str, Any]:
    observations: list[tuple[str, str]] = []
    for line in output.splitlines():
        match = SITE_OUTPUT_RE.fullmatch(line.strip())
        if match:
            observations.append((match.group(1), match.group(2)))
    counts = Counter(site for site, _ in observations)
    duplicates = sorted(site for site, count in counts.items() if count != 1)
    observed = set(counts)
    missing = sorted(expected - observed)
    unexpected = sorted(observed - expected)
    failures = sorted(site for site, status in observations if status != "PASS")
    semantic_lines = [f"FAULT_SITE {site} {status}" for site, status in observations]
    semantic_text = "\n".join(semantic_lines) + ("\n" if semantic_lines else "")
    passed = not duplicates and not missing and not unexpected and not failures
    return {
        "status": "pass" if passed else "fail",
        "expected_site_count": len(expected),
        "observed_site_count": len(observations),
        "duplicate_sites": duplicates,
        "missing_sites": missing,
        "unexpected_sites": unexpected,
        "failed_sites": failures,
        "semantic_output_sha256": sha256_text(semantic_text),
        "observed_pass_sites": sorted(
            site for site, status in observations if status == "PASS"
        ),
    }


def run_iverilog_case(
    case: FaultCase,
    expected: set[str],
    iverilog: Path,
    vvp: Path,
    aliases: dict[str, str],
) -> dict[str, Any]:
    case_dir = BUILD / "iverilog" / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    executable = case_dir / case.top
    compile_command = [
        str(iverilog),
        "-g2012",
        "-Wall",
        "-Wno-sensitivity-entire-array",
        "-s",
        case.top,
        "-o",
        str(executable.relative_to(ROOT)),
        *case.sources,
    ]
    compile_result = run_command(
        compile_command,
        case_dir / "compile.log",
        timeout=120,
        aliases=aliases,
    )
    compile_pass = (
        compile_result["returncode"] == 0
        and not compile_result["timed_out"]
        and not compile_result["warnings"]
    )
    simulation_result: dict[str, Any] | None = None
    site_result: dict[str, Any] | None = None
    if compile_pass:
        simulation_result = run_command(
            [str(vvp), str(executable.relative_to(ROOT))],
            case_dir / "simulation.log",
            timeout=60,
            aliases=aliases,
        )
        site_result = validate_site_output(simulation_result["output"], expected)
    passed = bool(
        compile_pass
        and simulation_result
        and simulation_result["returncode"] == 0
        and not simulation_result["timed_out"]
        and not simulation_result["warnings"]
        and site_result
        and site_result["status"] == "pass"
    )
    for result in (compile_result, simulation_result):
        if result is not None:
            result.pop("output", None)
    return {
        "simulator": "iverilog_vvp",
        "bench": case.bench,
        "top": case.top,
        "status": "pass" if passed else "fail",
        "compile": compile_result,
        "simulation": simulation_result,
        "sites": site_result,
    }


def run_verilator_case(
    case: FaultCase,
    expected: set[str],
    verilator: Path,
    aliases: dict[str, str],
) -> dict[str, Any]:
    case_dir = BUILD / "verilator" / case.name
    case_dir.mkdir(parents=True, exist_ok=True)
    compile_command = [
        str(verilator),
        "--binary",
        "--timing",
        "-Wall",
        "-Wno-PROCASSINIT",
        "-Wno-UNUSEDSIGNAL",
        "-Wno-PINCONNECTEMPTY",
        "--top-module",
        case.top,
        "--Mdir",
        str(case_dir.relative_to(ROOT)),
        *case.sources,
    ]
    compile_result = run_command(
        compile_command,
        case_dir / "compile.log",
        timeout=300,
        aliases=aliases,
    )
    compile_pass = (
        compile_result["returncode"] == 0
        and not compile_result["timed_out"]
        and not compile_result["warnings"]
    )
    simulation_result: dict[str, Any] | None = None
    site_result: dict[str, Any] | None = None
    executable = case_dir / f"V{case.top}"
    if compile_pass and executable.exists():
        simulation_result = run_command(
            [str(executable.relative_to(ROOT))],
            case_dir / "simulation.log",
            timeout=60,
            aliases=aliases,
        )
        site_result = validate_site_output(simulation_result["output"], expected)
    passed = bool(
        compile_pass
        and simulation_result
        and simulation_result["returncode"] == 0
        and not simulation_result["timed_out"]
        and not simulation_result["warnings"]
        and site_result
        and site_result["status"] == "pass"
    )
    for result in (compile_result, simulation_result):
        if result is not None:
            result.pop("output", None)
    return {
        "simulator": "verilator_5_050_timed_binary",
        "bench": case.bench,
        "top": case.top,
        "status": "pass" if passed else "fail",
        "compile": compile_result,
        "simulation": simulation_result,
        "sites": site_result,
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Public RTL fault-containment campaign",
        "",
        f"**Overall status:** {summary['status'].upper()}",
        "",
        f"The campaign observed **{summary['site_count']} / {summary['site_count']}** "
        "planned public RTL sites exactly once in each of two independent simulators "
        f"({summary['simulator_site_observations']} checked simulator-site observations). "
        "This is 100% only for the enumerated site set; it is not a physical-fault, "
        "macro, ATPG, manufacturing, or product-signoff coverage claim.",
        "",
        "## Bench closure",
        "",
        "| Bench | Planned sites | Icarus/vvp | Verilator 5.050 |",
        "|---|---:|---|---|",
    ]
    case_by_key = {(case["bench"], case["simulator"]): case for case in summary["cases"]}
    for bench, count in summary["bench_site_counts"].items():
        iv = case_by_key[(bench, "iverilog_vvp")]["status"].upper()
        vl = case_by_key[(bench, "verilator_5_050_timed_binary")]["status"].upper()
        lines.append(f"| `{bench}` | {count} | {iv} | {vl} |")
    lines.extend(
        [
            "",
            "## Tool identity and warning policy",
            "",
            "| Tool | Version | Executable SHA-256 |",
            "|---|---|---|",
        ]
    )
    for name, record in summary["tools"].items():
        lines.append(
            f"| {name} | `{record['version']}` | `{record['executable_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "Unexpected compile or simulation warnings are fatal. Icarus suppresses only "
            "`sensitivity-entire-array`, an informational diagnostic that the IEEE `always @*` "
            "semantics intentionally include every dynamically selected array word. Verilator "
            "suppresses only bench-local `PROCASSINIT`, `UNUSEDSIGNAL`, and `PINCONNECTEMPTY`; "
            "width warnings and fatal-warning behavior remain enabled.",
            "",
            "## Site matrix",
            "",
            "| Site | Class | Requirements | Expected observation | Containment | Recovery | Icarus | Verilator |",
            "|---|---|---|---|---|---|---|---|",
        ]
    )
    for site in summary["sites"]:
        requirements = ", ".join(site["verification_requirements"])
        lines.append(
            f"| `{site['id']}` | {site['fault_class']} | {requirements} | "
            f"{site['expected_observation']} | {site['containment']} | {site['recovery']} | "
            f"{site['observed']['iverilog_vvp'].upper()} | "
            f"{site['observed']['verilator_5_050_timed_binary'].upper()} |"
        )
    lines.extend(
        [
            "",
            "## Explicit external gates",
            "",
            "| Gate | Status | Scope not established here |",
            "|---|---|---|",
        ]
    )
    for gate in summary["external_gates"]:
        lines.append(f"| `{gate['id']}` | {gate['status']} | {gate['scope']} |")
    lines.extend(
        [
            "",
            "## Commands and logs",
            "",
            "| Simulator | Bench | Compile log | Simulation log | Result |",
            "|---|---|---|---|---|",
        ]
    )
    for case in summary["cases"]:
        sim_log = case["simulation"]["log"] if case["simulation"] else "not run"
        lines.append(
            f"| {case['simulator']} | `{case['bench']}` | "
            f"`{case['compile']['log']}` | `{sim_log}` | {case['status'].upper()} |"
        )
    lines.extend(
        [
            "",
            "Raw build/run logs live under `rtl/build/fault_campaign/`; canonical evidence "
            "records commands, outcomes, semantic site-output hashes, source hashes, and tool "
            "executable hashes without promoting variable build timing to an identity field.",
            "",
            "## Claim boundary",
            "",
            *[f"- {item}" for item in summary["limitations"]],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    try:
        plan, expected_by_bench = load_and_validate_plan()
        iverilog = resolve_executable("iverilog")
        vvp = resolve_executable("vvp")
        compiler = resolve_executable("g++")
        verilator = resolve_verilator()
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"fault campaign setup failed: {exc}", file=sys.stderr)
        return 2

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    aliases = {
        str(iverilog): "<IVERILOG>",
        str(vvp): "<VVP>",
        str(verilator): "<VERILATOR_5_050>",
        str(compiler): "<CXX>",
    }
    cases: list[dict[str, Any]] = []
    for case in CASES:
        expected = expected_by_bench[case.bench]
        print(f"fault: Icarus {case.name}", flush=True)
        cases.append(run_iverilog_case(case, expected, iverilog, vvp, aliases))
        print(f"fault: Verilator {case.name}", flush=True)
        cases.append(run_verilator_case(case, expected, verilator, aliases))

    site_observed: dict[str, dict[str, str]] = {
        site["id"]: {
            "iverilog_vvp": "fail",
            "verilator_5_050_timed_binary": "fail",
        }
        for site in plan["sites"]
    }
    for case in cases:
        site_data = case.get("sites") or {}
        for site_id in site_data.get("observed_pass_sites", []):
            site_observed[site_id][case["simulator"]] = "pass"
    sites = []
    for planned in plan["sites"]:
        site = dict(planned)
        site["observed"] = site_observed[planned["id"]]
        site["status"] = (
            "pass" if all(value == "pass" for value in site["observed"].values()) else "fail"
        )
        sites.append(site)

    source_paths = sorted(
        {source for case in CASES for source in case.sources}
        | {
            "spec/fault_campaign.json",
            "spec/verification.json",
            "spec/VERIFICATION_PLAN.md",
            "spec/RAS_REPAIR_DFT.md",
            "tools/bootstrap_verilator_5_050.sh",
            "tools/rtl_fault_campaign.py",
        }
    )
    passed = all(case["status"] == "pass" for case in cases) and all(
        site["status"] == "pass" for site in sites
    )
    summary = {
        "schema_version": 1,
        "campaign": plan["campaign_id"],
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_directed_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "claim_scope": plan["claim_scope"],
        "site_count": len(sites),
        "simulators_counted": plan["required_simulators"],
        "simulator_site_observations": len(sites) * len(plan["required_simulators"]),
        "bench_site_counts": {
            case.bench: len(expected_by_bench[case.bench]) for case in CASES
        },
        "tools": {
            "iverilog": tool_record(iverilog, ["-V"]),
            "vvp": tool_record(vvp, ["-V"]),
            "verilator": tool_record(verilator, ["--version"]),
            "compiler": tool_record(compiler, ["--version"]),
        },
        "verilator_source": {
            "repository": plan["toolchain"]["verilator_source_repository"],
            "commit": plan["toolchain"]["verilator_source_commit"],
            "bootstrap": plan["toolchain"]["bootstrap"],
        },
        "warning_policy": plan["warning_policy"],
        "source_sha256": {path: sha256_file(ROOT / path) for path in source_paths},
        "cases": cases,
        "sites": sites,
        "external_gates": plan["external_gates"],
        "limitations": [
            "100% means activation and specified observation/containment for these enumerated public RTL sites only.",
            "The directed benches use reduced parameters and behavioral macro boundaries; they do not establish architectural-maxima timing or physical behavior.",
            "No target ATPG, foundry ROM/SRAM ECC or BIST qualification, HBM/PHY behavior, physical fault coverage, manufacturing/yield, numerical quality, PDK closure, or product signoff is claimed.",
            "Statistical random fault injection, stage/reticle/pipeline degradation, reset-phase campaigns, and code/functional coverage closure remain separate verification gates.",
        ],
    }
    json_path = RESULTS / "fault_campaign.json"
    report_path = RESULTS / "FAULT_REPORT.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(summary), encoding="utf-8")
    print(f"fault campaign: {summary['status'].upper()} ({len(sites)} sites x 2 simulators)")
    print(f"evidence: {json_path.relative_to(ROOT)}, {report_path.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
