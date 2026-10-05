#!/usr/bin/env python3
"""Run the independent ROM schedule checker over shipped deployments.

The default campaign checks the conventional Qwen ROM chip and the DeepSeek
wafer ROM deployment.  They are independent read-only jobs and run in separate
processes by default, so loading and reconstructing the two large artifact
families does not serialize the campaign.

Custom cases use four arguments::

    --case NAME KERNEL_IR DEPLOYMENT_DIR CAPABILITY_JSON
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from compiler.backends.rom.common.check import (  # noqa: E402
    SCHEDULE_CHECK_SCHEMA,
    check_rom_schedule,
)
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402

CAMPAIGN_SCHEMA = "opentallas.rom.schedule_campaign.v1"


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    ir: str
    deployment: str
    capability: str


DEFAULT_CASES = (
    Case(
        "qwen3-rom-single-chip",
        "build/ir-v3/qwen3-8b/kernel_ir.v3.json",
        "build/abi3/qwen3-8b-rom",
        "configs/hardware/abi3_capability/rom_qwen3.json",
    ),
    Case(
        "deepseek-v4-flash-rom-wafer",
        "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json",
        "build/abi3/deepseek-v4-flash-rom",
        "configs/hardware/abi3_capability/rom_deepseek_v4.json",
    ),
    Case(
        "deepseek-v4-flash-rom-array-32",
        "build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json",
        "build/abi3/deepseek-v4-flash-rom-array-32",
        "configs/hardware/abi3_capability/rom_deepseek_v4_array_32.json",
    ),
    # DeepSeek-V4.1-Flash on two wafer-scale logical devices (plan WP-E).  Its
    # certificate is the one that carries ``shared_state_locality``,
    # ``resident_hbm_region``, ``candidate_pool_bound`` and ``expert_capacity``.
    Case(
        "deepseek-v41-flash-rom-wafer-2",
        "build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json",
        "build/abi3/deepseek-v41-flash-rom-wafer-2",
        "configs/hardware/abi3_capability/rom_deepseek_v41_wafer.json",
    ),
)


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPOSITORY_ROOT / candidate


def _digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def _relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPOSITORY_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def run_case(case: Case) -> dict[str, Any]:
    """Load one immutable artifact set and reconstruct its schedule."""

    ir_path = _resolve(case.ir)
    deployment_root = _resolve(case.deployment)
    capability_path = _resolve(case.capability)
    graph = KernelGraph.read(ir_path)
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
    deployment = Deployment.read(deployment_root)
    report = check_rom_schedule(graph, deployment, capability)
    report["case"] = case.name
    report["inputs"] = {
        "kernel_ir": {
            "path": _relative(ir_path),
            "sha256": _digest(ir_path),
        },
        "capability": {
            "path": _relative(capability_path),
            "sha256": _digest(capability_path),
        },
        "deployment": {
            "path": _relative(deployment_root),
            "manifest_sha256": _digest(deployment_root / "deployment.json"),
            "descriptors_sha256": _digest(deployment_root / "descriptors.bin"),
            "program_sha256": _digest(deployment_root / "program.bin"),
        },
    }
    return report


def _parse_cases(values: Sequence[Sequence[str]] | None) -> tuple[Case, ...]:
    if not values:
        return DEFAULT_CASES
    return tuple(Case(*value) for value in values)


def missing_inputs(case: Case) -> list[str]:
    """Artifacts this case needs and this tree does not have.

    A default case whose deployment has not been built yet is reported as
    skipped rather than run: it is named here because the product exists, and a
    campaign that silently omitted it or crashed on it would be two different
    kinds of wrong.  A case given explicitly on the command line is always run,
    so an absent artifact there is still an error.
    """
    absent: list[str] = []
    for path in (_resolve(case.ir), _resolve(case.capability)):
        if not path.is_file():
            absent.append(_relative(path))
    root = _resolve(case.deployment)
    for name in ("deployment.json", "descriptors.bin", "program.bin"):
        if not (root / name).is_file():
            absent.append(_relative(root / name))
    return absent


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        action="append",
        nargs=4,
        metavar=("NAME", "KERNEL_IR", "DEPLOYMENT_DIR", "CAPABILITY_JSON"),
        help="case to check; repeat for multiple independent deployments",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        help="parallel worker processes (default: 2)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPOSITORY_ROOT / "results/abi3/rom_schedule_checks.json",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--json", action="store_true", help="also print the complete campaign"
    )
    args = parser.parse_args(argv)

    cases = _parse_cases(args.case)
    if not cases:
        parser.error("at least one case is required")
    skipped: list[dict[str, Any]] = []
    if not args.case:
        runnable: list[Case] = []
        for case in cases:
            absent = missing_inputs(case)
            if absent:
                skipped.append({"case": case.name, "absent_inputs": absent})
            else:
                runnable.append(case)
        cases = tuple(runnable)
    if not cases:
        parser.error(
            "every default case is missing its artifacts: "
            + ", ".join(entry["case"] for entry in skipped)
        )
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    output = args.output if args.output.is_absolute() else Path.cwd() / args.output
    if output.exists() and not args.force:
        print(f"refusing to overwrite {output}; pass --force", file=sys.stderr)
        return 1

    workers = min(args.jobs, len(cases), os.cpu_count() or 1)
    if workers == 1:
        reports = [run_case(case) for case in cases]
    else:
        with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
            reports = list(pool.map(run_case, cases))
    reports.sort(key=lambda report: report["case"])

    checker_path = REPOSITORY_ROOT / "compiler/backends/rom/common/check.py"
    tool_path = Path(__file__).resolve()
    campaign = {
        "schema": CAMPAIGN_SCHEMA,
        "status": "pass" if all(report["ok"] for report in reports) else "fail",
        "checker_schema": SCHEDULE_CHECK_SCHEMA,
        "parallel_jobs": workers,
        "case_count": len(reports),
        "skipped": sorted(skipped, key=lambda entry: entry["case"]),
        "skipped_count": len(skipped),
        "source": {
            "checker": {
                "path": _relative(checker_path),
                "sha256": _digest(checker_path),
            },
            "campaign_tool": {
                "path": _relative(tool_path),
                "sha256": _digest(tool_path),
            },
        },
        "cases": reports,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json(campaign))

    if args.json:
        print(json.dumps(campaign, indent=2, sort_keys=True))
    else:
        print(
            f"ROM schedule campaign: {campaign['status']} "
            f"({len(reports)} cases, {workers} parallel job(s))"
        )
        for report in reports:
            print(
                f"  {report['case']:<34} {report['status']:<4} "
                f"{len(report['checks'])} checks, "
                f"{report['actual']['instructions']} instructions, "
                f"{report['actual']['schedules']} schedules"
            )
            for error in report["errors"]:
                print(f"    ERROR: {error}")
        for entry in campaign["skipped"]:
            print(f"  {entry['case']:<34} skipped (absent: {entry['absent_inputs'][0]})")
        print(f"wrote {_relative(output)}")
    return 0 if campaign["status"] == "pass" else 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
