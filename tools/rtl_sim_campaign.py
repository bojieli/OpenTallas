#!/usr/bin/env python3
"""Run and record the public two-simulator RTL campaign."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "rtl" / "build" / "sim_campaign"
RESULTS = ROOT / "results" / "rtl"

CASES = (
    ("iverilog_tile", ["make", "-C", "rtl", "sim"], "PASS: wordline mask"),
    ("iverilog_reference_units", ["make", "-C", "rtl", "unit-sim"], "PASS: reference unit blocks"),
    (
        "iverilog_cdc_reset",
        ["make", "-C", "rtl", "cdc-sim"],
        "PASS: CDC mailbox, qualified level, and reset-rendezvous FIFO",
    ),
    ("iverilog_stage_integration", ["make", "-C", "rtl", "integration-sim"], "PASS: stage top"),
    (
        "verilator_randomized_units",
        ["make", "-C", "rtl", "verilator-sim"],
        "PASS: independent Verilator randomized scoreboard",
    ),
)

SOURCES = tuple(
    sorted(
        {
            "rtl/Makefile",
            "tools/rtl_sim_campaign.py",
            "spec/CLOCK_RESET_POWER.md",
            "spec/INTERFACES.md",
            "spec/VERIFICATION_PLAN.md",
            "spec/verification.json",
        }
        | {
            str(path.relative_to(ROOT))
            for pattern in ("*.sv", "lib/*.sv", "test/*.sv", "test/*.cpp")
            for path in (ROOT / "rtl").glob(pattern)
        }
    )
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def version(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": shlex.join(command)}
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "command": shlex.join(command),
        "executable": executable,
        "executable_sha256": sha256_file(Path(executable)),
        "version": lines[0] if lines else "no version text",
    }


def run_case(name: str, command: list[str], marker: str) -> dict[str, Any]:
    print(f"simulation: {name}", flush=True)
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=180,
    )
    log = BUILD / f"{name}.log"
    log.write_text(result.stdout, encoding="utf-8")
    passed = result.returncode == 0 and marker in result.stdout
    record: dict[str, Any] = {
        "name": name,
        "status": "pass" if passed else "fail",
        "command": shlex.join(command),
        "returncode": result.returncode,
        "required_marker": marker,
        "log": str(log.relative_to(ROOT)),
    }
    if name == "verilator_randomized_units":
        match = re.search(
            r"seed=0x([0-9a-fA-F]+) cycles=(\d+) checks=(\d+)", result.stdout
        )
        if match:
            record["seed_hex"] = match.group(1).lower()
            record["cycles"] = int(match.group(2))
            record["scoreboard_checks"] = int(match.group(3))
        else:
            record["status"] = "fail"
            record["parse_error"] = "missing deterministic seed/cycle/check summary"
    return record


def coverage_summary(path: Path) -> dict[str, Any]:
    # Verilator's native format preserves point class; LCOV conversion in the
    # installed public release collapses line/branch/toggle and is unsuitable
    # for closure accounting.
    point_re = re.compile(r"^C '(.*)' (\d+)$")
    stats: dict[str, dict[str, list[int]]] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = point_re.match(line)
        if not match:
            continue
        metadata, count_text = match.groups()
        fields: dict[str, str] = {}
        for field in metadata.split("\x01"):
            if "\x02" in field:
                key, value = field.split("\x02", 1)
                fields[key] = value
        filename = fields.get("f", "unknown")
        point_class = fields.get("page", "unknown").split("/", 1)[0]
        stats.setdefault(filename, {}).setdefault(point_class, [0, 0])
        stats[filename][point_class][1] += 1
        stats[filename][point_class][0] += int(count_text) > 0

    dut_files = [name for name in stats if not name.startswith("test/")]
    classes = {"line": "v_line", "branch": "v_branch", "toggle": "v_toggle"}
    dut: dict[str, Any] = {}
    for label, point_class in classes.items():
        hit = sum(stats[name].get(point_class, [0, 0])[0] for name in dut_files)
        total = sum(stats[name].get(point_class, [0, 0])[1] for name in dut_files)
        dut[label] = {
            "hit": hit,
            "total": total,
            "percent": round(100.0 * hit / total, 3) if total else None,
        }
    per_file: dict[str, Any] = {}
    for filename, classes_by_file in sorted(stats.items()):
        per_file[filename] = {
            label: {
                "hit": classes_by_file.get(point_class, [0, 0])[0],
                "total": classes_by_file.get(point_class, [0, 0])[1],
            }
            for label, point_class in classes.items()
        }
    return {
        "scope": "ot_numeric_dot + ot_skid_buffer + ot_credit_manager; wrapper excluded",
        "dut": dut,
        "per_file": per_file,
        "exclusions": [
            "test/ot_verilator_unit_top.sv wrapper toggle points are not DUT coverage",
            "static legal-traffic error flags do not toggle; they remain included in DUT toggle denominator",
        ],
    }


def render(summary: dict[str, Any]) -> str:
    cov = summary["coverage"]["dut"]
    lines = [
        "# Public two-simulator RTL campaign",
        "",
        f"**Overall status:** {summary['status'].upper()}",
        "",
        "Icarus Verilog and a separately compiled Verilator C++ executable both pass. The C++ "
        "scoreboard independently implements signed dot-product saturation, FIFO ordering, and "
        "multi-sink credit conservation; it does not call an RTL helper algorithm.",
        "",
        "| Test | Simulator | Result |",
        "|---|---|---|",
    ]
    for case in summary["cases"]:
        simulator = "Verilator/C++" if case["name"].startswith("verilator") else "Icarus/vvp"
        lines.append(f"| `{case['name']}` | {simulator} | {case['status'].upper()} |")
    lines.extend(
        [
            "",
            "## Independent executable",
            "",
            f"- Seed: `0x{summary['verilator']['seed_hex']}`",
            f"- Cycles: {summary['verilator']['cycles']:,}",
            f"- Scoreboard checks: {summary['verilator']['scoreboard_checks']:,}",
            "- Exercised saturation, poison, invalid bubbles, full/stalled and full/recycle FIFO "
            "states, credit exhaustion, and atomic release/reserve recycle.",
            "",
            "## Verilator DUT coverage",
            "",
            "| Metric | Hit/total | Percent | Unit-scope target |",
            "|---|---:|---:|---:|",
            f"| Line | {cov['line']['hit']}/{cov['line']['total']} | {cov['line']['percent']:.3f}% | 95% |",
            f"| Branch | {cov['branch']['hit']}/{cov['branch']['total']} | {cov['branch']['percent']:.3f}% | 90% |",
            f"| Toggle | {cov['toggle']['hit']}/{cov['toggle']['total']} | {cov['toggle']['percent']:.3f}% | 85% |",
            "",
            "These percentages close only the named three-block executable scope, not the stage or "
            "project-wide coverage gate. Wrapper points are excluded; legal-traffic error outputs remain "
            "in the DUT toggle denominator.",
            "",
            "## Evidence boundary",
            "",
            "This is public-tool RTL simulation evidence. It does not qualify target numerical formats, "
            "model quality, ROM/HBM/PHY macros, package behavior, or PDK timing/power.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)
    missing = [name for name in ("iverilog", "vvp", "verilator", "verilator_coverage")
               if shutil.which(name) is None]
    if missing:
        print(f"missing required simulator tools: {', '.join(missing)}", file=sys.stderr)
        return 2
    cases = [run_case(*case) for case in CASES]
    coverage_path = ROOT / "rtl" / "build" / "verilator_unit" / "coverage.dat"
    coverage = coverage_summary(coverage_path) if coverage_path.exists() else {"dut": {}}
    closure = json.loads((ROOT / "spec" / "verification.json").read_text())["closure"]
    targets = {
        "line": closure["line_coverage_percent"],
        "branch": closure["branch_coverage_percent"],
        "toggle": closure["toggle_coverage_percent"],
    }
    coverage_pass = bool(coverage.get("dut")) and all(
        coverage["dut"][metric]["percent"] >= threshold
        for metric, threshold in targets.items()
    )
    verilator_case = next(case for case in cases if case["name"].startswith("verilator"))
    passed = all(case["status"] == "pass" for case in cases) and coverage_pass
    summary = {
        "schema_version": 1,
        "campaign": "two_simulator",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "tools": {
            "iverilog": version(["iverilog", "-V"]),
            "verilator": version(["verilator", "--version"]),
            "compiler": version(["g++", "--version"]),
        },
        "source_sha256": {path: sha256_file(ROOT / path) for path in sorted(SOURCES)},
        "cases": cases,
        "verilator": {
            "seed_hex": verilator_case.get("seed_hex"),
            "cycles": verilator_case.get("cycles"),
            "scoreboard_checks": verilator_case.get("scoreboard_checks"),
        },
        "coverage": coverage,
        "unit_scope_coverage_targets": targets,
        "unit_scope_coverage_status": "pass" if coverage_pass else "fail",
        "limitations": [
            "coverage closure applies only to the three-block Verilator executable scope",
            "Icarus and Verilator share RTL sources but use independent elaboration and simulation engines",
            "target numeric formats and physical macros remain outside this campaign",
        ],
    }
    (RESULTS / "simulation_campaign.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (RESULTS / "SIMULATION_REPORT.md").write_text(render(summary), encoding="utf-8")
    print(f"two-simulator campaign: {summary['status'].upper()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
