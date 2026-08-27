#!/usr/bin/env python3
"""Run reproducible public-tool RTL verification campaigns.

This runner records bounded proof depth and solver identity explicitly.  A pass
is evidence for the stated harness, assumptions, parameters, and bound only; it
is not target-node or product signoff.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "rtl" / "build" / "campaign"
RESULTS = ROOT / "results" / "rtl"


@dataclass(frozen=True)
class FormalCase:
    name: str
    sources: tuple[str, ...]
    sat_depth: int
    cvc4_depth: int
    cover_depth: int
    induction_depth: int | None = None
    timeout_seconds: int = 150
    cvc4_bmc_noincr: bool = False


FORMAL_CASES = (
    FormalCase(
        "f_skid_buffer",
        ("rtl/lib/ot_skid_buffer.sv", "rtl/formal/f_skid_buffer.sv"),
        24,
        12,
        8,
    ),
    FormalCase(
        "f_async_fifo",
        (
            "rtl/lib/ot_reset_sync.sv",
            "rtl/lib/ot_async_fifo.sv",
            "rtl/formal/f_async_fifo.sv",
        ),
        24,
        12,
        14,
    ),
    FormalCase(
        "f_cdc_mailbox",
        ("rtl/lib/ot_cdc_mailbox.sv", "rtl/formal/f_cdc_mailbox.sv"),
        32,
        16,
        28,
    ),
    FormalCase(
        "f_sync_level",
        ("rtl/lib/ot_sync_level.sv", "rtl/formal/f_sync_level.sv"),
        24,
        12,
        12,
    ),
    FormalCase(
        "f_credit_manager",
        ("rtl/ot_credit_manager.sv", "rtl/formal/f_credit_manager.sv"),
        24,
        7,
        10,
        induction_depth=8,
    ),
    FormalCase(
        "f_power_controller",
        ("rtl/ot_power_reset_controller.sv", "rtl/formal/f_power_controller.sv"),
        24,
        12,
        10,
        induction_depth=8,
    ),
    FormalCase(
        "f_route_mask",
        ("rtl/ot_route_mask.sv", "rtl/formal/f_route_mask.sv"),
        24,
        7,
        8,
    ),
    FormalCase(
        "f_schedule_controller",
        ("rtl/ot_schedule_controller.sv", "rtl/formal/f_schedule_controller.sv"),
        24,
        8,
        10,
    ),
    FormalCase(
        "f_stage_controller",
        ("rtl/ot_stage_controller.sv", "rtl/formal/f_stage_controller.sv"),
        24,
        12,
        18,
        timeout_seconds=360,
        cvc4_bmc_noincr=True,
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_version(command: list[str]) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {"available": False, "command": shlex.join(command)}
    run = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=15,
    )
    lines = [line.strip() for line in run.stdout.splitlines() if line.strip()]
    return {
        "available": True,
        "command": shlex.join(command),
        "executable": executable,
        "executable_sha256": sha256_file(Path(executable)),
        "version": lines[0] if lines else "no version text",
    }


def run_phase(
    case: FormalCase,
    phase: str,
    command: list[str],
    *,
    timeout: int,
    required_text: str | None = None,
) -> dict[str, Any]:
    log_path = BUILD / f"{case.name}.{phase}.log"
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
        log_path.write_text(output, encoding="utf-8")
        passed = run.returncode == 0 and (required_text is None or required_text in output)
        status = "pass" if passed else "fail"
        return {
            "phase": phase,
            "status": status,
            "returncode": run.returncode,
            "timeout_seconds": timeout,
            "command": shlex.join(command),
            "log": str(log_path.relative_to(ROOT)),
        }
    except subprocess.TimeoutExpired as exc:
        def timeout_text(value: str | bytes | None) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        output = timeout_text(exc.stdout) + timeout_text(exc.stderr)
        log_path.write_text(output, encoding="utf-8")
        return {
            "phase": phase,
            "status": "timeout",
            "returncode": None,
            "timeout_seconds": timeout,
            "command": shlex.join(command),
            "log": str(log_path.relative_to(ROOT)),
        }


def yosys_prefix(case: FormalCase) -> str:
    sources = " ".join(case.sources)
    return (
        f"read_verilog -formal -D SYNTHESIS -sv {sources}; "
        f"prep -top {case.name} -flatten; async2sync; "
    )


def run_formal_case(case: FormalCase) -> dict[str, Any]:
    print(f"formal: {case.name}", flush=True)
    phases: list[dict[str, Any]] = []
    sat_script = (
        yosys_prefix(case)
        + "chformal -cover -remove; memory_map; opt_clean; "
        + f"sat -seq {case.sat_depth} -prove-asserts -set-assumes "
        + "-set-init-zero -verify"
    )
    phases.append(
        run_phase(
            case,
            "yosys_sat_bmc",
            ["yosys", "-q", "-p", sat_script],
            timeout=case.timeout_seconds,
        )
    )

    smt_path = BUILD / f"{case.name}.smt2"
    smt_script = (
        yosys_prefix(case)
        + "memory_map; opt_clean; "
        + f"write_smt2 -stbv -wires {smt_path.relative_to(ROOT)}"
    )
    phases.append(
        run_phase(
            case,
            "smt_elaboration",
            ["yosys", "-q", "-p", smt_script],
            timeout=case.timeout_seconds,
        )
    )
    if phases[-1]["status"] == "pass" and smt_path.exists():
        smt_hash = sha256_file(smt_path)
        cvc4_bmc_command = [
            "yosys-smtbmc",
            "-s",
            "cvc4",
        ]
        if case.cvc4_bmc_noincr:
            cvc4_bmc_command.append("--noincr")
        cvc4_bmc_command.extend(
            [
                "-t",
                str(case.cvc4_depth),
                str(smt_path.relative_to(ROOT)),
            ]
        )
        phases.append(
            run_phase(
                case,
                "cvc4_bmc",
                cvc4_bmc_command,
                timeout=case.timeout_seconds,
                required_text="Status: PASSED",
            )
        )
        phases.append(
            run_phase(
                case,
                "cvc4_cover",
                [
                    "yosys-smtbmc",
                    "-s",
                    "cvc4",
                    "-c",
                    "-t",
                    str(case.cover_depth),
                    str(smt_path.relative_to(ROOT)),
                ],
                timeout=case.timeout_seconds,
                required_text="Status: PASSED",
            )
        )
        if case.induction_depth is not None:
            phases.append(
                run_phase(
                    case,
                    "cvc4_induction",
                    [
                        "yosys-smtbmc",
                        "-s",
                        "cvc4",
                        "-i",
                        "-t",
                        str(case.induction_depth),
                        str(smt_path.relative_to(ROOT)),
                    ],
                    timeout=case.timeout_seconds,
                    required_text="Temporal induction successful.",
                )
            )
    else:
        smt_hash = None

    passed = all(item["status"] == "pass" for item in phases)
    return {
        "name": case.name,
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_proxy",
        "bounds": {
            "yosys_sat_bmc": case.sat_depth,
            "cvc4_bmc": case.cvc4_depth,
            "cvc4_cover": case.cover_depth,
            "cvc4_induction": case.induction_depth,
        },
        "cvc4_bmc_mode": "non_incremental" if case.cvc4_bmc_noincr else "incremental",
        "sources": list(case.sources),
        "smt2_sha256": smt_hash,
        "phases": phases,
    }


def render_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Public-tool RTL formal campaign",
        "",
        f"**Overall status:** {summary['status'].upper()}",
        "",
        "This is reproducible methodology evidence for the checked public RTL. It is not "
        "product signoff, macro qualification, or proof beyond each recorded bound. CVC4 "
        "induction is claimed only where the table explicitly lists a depth.",
        "",
        "| Harness | Yosys SAT BMC | CVC4 BMC | CVC4 mode | Covers | Induction | Result |",
        "|---|---:|---:|---|---:|---:|---|",
    ]
    for case in summary["cases"]:
        bounds = case["bounds"]
        induction = bounds["cvc4_induction"]
        lines.append(
            f"| `{case['name']}` | {bounds['yosys_sat_bmc']} | {bounds['cvc4_bmc']} | "
            f"{case['cvc4_bmc_mode']} | {bounds['cvc4_cover']} | "
            f"{induction if induction is not None else 'bounded only'} | "
            f"{case['status'].upper()} |"
        )
    lines.extend(
        [
            "",
            "## Solver qualification notes",
            "",
            "- The independent configurations are Yosys internal SAT and Yosys SMT2 with CVC4 1.8.",
            "- The stage-controller CVC4 BMC uses non-incremental solver processes at the same "
            "depth and with the same formula because CVC4 1.8's incremental mode has a severe "
            "local performance cliff on that model; this changes solver scheduling, not proof scope.",
            "- Z3 4.8.12 was locally non-terminating at useful bounds for these generated models; "
            "Ubuntu Boolector 1.5.118 is too old for the interaction. Neither is counted as pass evidence.",
            "- Some CVC4 bounds are intentionally lower than SAT because solver cost "
            "rises sharply; the exact depths are part of the claim, not hidden campaign metadata.",
            "",
            "## Source manifest",
            "",
        ]
    )
    for path, digest in summary["source_sha256"].items():
        lines.append(f"- `{path}`: `{digest}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--formal",
        action="store_true",
        help="run the formal campaign (currently the default and implemented phase)",
    )
    parser.parse_args()

    BUILD.mkdir(parents=True, exist_ok=True)
    RESULTS.mkdir(parents=True, exist_ok=True)

    missing = [tool for tool in ("yosys", "yosys-smtbmc", "cvc4") if shutil.which(tool) is None]
    if missing:
        print(f"missing required formal tools: {', '.join(missing)}", file=sys.stderr)
        return 2

    source_paths = sorted(
        {source for case in FORMAL_CASES for source in case.sources}
        | {
            "tools/rtl_campaign.py",
            "spec/VERIFICATION_PLAN.md",
            "spec/verification.json",
        }
    )
    source_hashes = {path: sha256_file(ROOT / path) for path in source_paths}
    tools = {
        "yosys": tool_version(["yosys", "-V"]),
        "yosys_smtbmc": tool_version(["yosys-smtbmc", "--version"]),
        "cvc4": tool_version(["cvc4", "--version"]),
        "z3": tool_version(["z3", "--version"]),
        "boolector": tool_version(["boolector", "--version"]),
    }
    cases = [run_formal_case(case) for case in FORMAL_CASES]
    passed = all(case["status"] == "pass" for case in cases)
    summary = {
        "schema_version": 1,
        "campaign": "formal",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_proxy",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "source_sha256": source_hashes,
        "tools": tools,
        "solver_configurations_counted": ["yosys_internal_sat", "cvc4_via_yosys_smt2_stbv"],
        "solver_compatibility_findings": {
            "z3_4_8_12": "not counted; local generated-SMT performance did not reach useful bounds",
            "boolector_1_5_118": "not counted; installed version is incompatible with generated interaction",
        },
        "cases": cases,
        "limitations": [
            "bounded results claim only the recorded depth and harness assumptions",
            "induction is counted only for credit and power harnesses",
            "formal clocks are abstract global clocks; independent clock ratios and reset phase are exercised in simulation and CDC structure is checked separately",
            "no result qualifies target ROM, HBM, PHY, package, standard-cell, or PDK behavior",
        ],
    }
    json_path = RESULTS / "formal_campaign.json"
    report_path = RESULTS / "FORMAL_REPORT.md"
    json_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(summary), encoding="utf-8")
    print(f"formal campaign: {summary['status'].upper()}")
    print(f"evidence: {json_path.relative_to(ROOT)}, {report_path.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
