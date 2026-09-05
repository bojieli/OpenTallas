#!/usr/bin/env python3
"""Run and record the device top's host load path on the vehicle geometry.

``rtl/abi3/ot_a3_device_top.sv`` presents its program and descriptor stores as
abstract macro boundaries and writes them only through its ``host_*`` port,
the management processor's load path of docs/CHIP_ARCHITECTURE_DESIGN.md
section 3.4.  The control-plane campaigns preload those stores from the
vector images, because their two checkers own reset and start timing and a
serial load of the four-deployment image would be ~10k cycles inside timing
they hash.  This bench is therefore the evidence that the path exists and
works: ``rtl/test/tb_a3_device_top_host_load.sv`` starts with empty stores
(the Qwen3-8B ROM case must trap), writes the deployment's program body and
descriptor records lane by lane through ``host_*`` at the vehicle defaults
(PROGRAM_WORDS = 128, DESC_WORDS = 256), streams the header through the
admission port, runs both entrypoints and requires every compared counter to
equal the golden record, then requires a write offered while busy or past a
store's end to be refused and to leave the store intact.

One checker, two simulators: Icarus, and Verilator built with ``--timing``
from the same bench.  A run counts only if both print the same PASS marker
and the same per-case lines.  Tool identity, source digests and the git
commit are recorded, not assumed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import rtl_abi3_deployment_campaign as base  # noqa: E402

SCHEMA = "opentallas.rtl.abi3_device_top_host_load.v1"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_device_top_host_load.json"
BENCH = "rtl/test/tb_a3_device_top_host_load.sv"
TOP = "tb_a3_device_top_host_load"
VECTOR_FILES = (
    "a3_program.hex",
    "a3_header.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
    "a3_deployment_case.hex",
)
TOOL_SOURCES = (
    "tools/rtl_abi3_device_top_host_load.py",
    "tools/rtl_abi3_deployment_campaign.py",
)
VEHICLE_GEOMETRY = {"PROGRAM_WORDS": 128, "DESC_WORDS": 256}

PASS_RE = re.compile(
    r"^PASS: ABI3 device top host load vehicle_program_words=(?P<program>\d+) "
    r"vehicle_desc_words=(?P<desc>\d+) host_writes=(?P<writes>\d+) "
    r"cases=(?P<cases>\d+) checks=(?P<checks>\d+)$",
    re.MULTILINE,
)
CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) loaded=(?P<loaded>[01]) complete=(?P<complete>[01]) "
    r"trap=(?P<trap>\d+) fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) "
    r"issued=(?P<issued>\d+) views=(?P<views>\d+)$",
    re.MULTILINE,
)


def observe(log: str) -> dict[str, Any]:
    marker = PASS_RE.search(log)
    return {
        "marker": marker.group(0) if marker else None,
        "checks": int(marker.group("checks")) if marker else None,
        "host_writes": int(marker.group("writes")) if marker else None,
        "cases": [
            {key: int(value) for key, value in match.groupdict().items()}
            for match in CASE_RE.finditer(log)
        ],
        "failures": [
            line for line in log.splitlines() if line.startswith("FAIL")
        ],
    }


def simulate(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
) -> dict[str, Any]:
    compiled = base.run_stage(f"{name}.compile", compile_command, build, timeout=1800)
    executed = None
    if compiled["returncode"] == 0:
        executed = base.run_stage(f"{name}.run", run_command, build, timeout=3600)
    log = compiled["log"] + (executed["log"] if executed else "")
    observation = observe(executed["log"] if executed else "")
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and observation["marker"] is not None
        and not observation["failures"]
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": base.canonical(" ".join(compile_command), build),
        "compile_returncode": compiled["returncode"],
        "run_command": base.canonical(" ".join(run_command), build),
        "run_returncode": executed["returncode"] if executed else None,
        "log_sha256": base.hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "run_log": base.canonical(
            "\n".join(
                line
                for line in (executed["log"] if executed else "").splitlines()
                if "Not enough words" not in line
            ),
            build,
        ),
        **observation,
    }


def run(build_root: Path | None = None) -> dict[str, Any]:
    executables = {
        "iverilog": base.resolve("iverilog", None),
        "vvp": base.resolve("vvp", None),
        "verilator": base.resolve(
            "verilator",
            base.TOOLS_ROOT
            / f"verilator-{base.PINNED_VERILATOR_VERSION}/bin/verilator",
        ),
        "cxx": base.resolve("g++", None),
    }
    version_args = {
        "iverilog": ["-V"],
        "vvp": ["-V"],
        "verilator": ["--version"],
        "cxx": ["--version"],
    }
    tools = {
        name: base.tool_record(path, version_args[name])
        for name, path in executables.items()
    }
    base.require_versions(tools)

    rtl = [str(ROOT / path) for path in base.RTL_SOURCES]
    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-hostload-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        for name in VECTOR_FILES:
            shutil.copy2(base.VECTOR_DIR / name, build / name)
        iverilog = simulate(
            "iverilog",
            [
                str(executables["iverilog"]),
                "-g2012",
                "-s",
                TOP,
                "-o",
                "hostload.vvp",
                *rtl,
                str(ROOT / BENCH),
            ],
            [str(executables["vvp"]), "hostload.vvp"],
            build,
        )
        verilator = simulate(
            "verilator",
            [
                str(executables["verilator"]),
                "--binary",
                "--timing",
                "-Wall",
                "-Wno-fatal",
                "-Wno-DECLFILENAME",
                "--top-module",
                TOP,
                "--Mdir",
                "obj_hostload",
                *rtl,
                str(ROOT / BENCH),
            ],
            [f"./obj_hostload/V{TOP}"],
            build,
        )
    cases = [iverilog, verilator]

    sources = {
        path: base.sha256_file(ROOT / path)
        for path in sorted((*base.RTL_SOURCES, BENCH, *TOOL_SOURCES))
    }
    for name in VECTOR_FILES:
        sources[f"testdata/compiler/abi3_deployment/{name}"] = base.sha256_file(
            base.VECTOR_DIR / name
        )

    agree = (
        iverilog["marker"] is not None
        and iverilog["marker"] == verilator["marker"]
        and iverilog["cases"] == verilator["cases"]
    )
    status = (
        "pass"
        if agree and all(case["status"] == "pass" for case in cases)
        else "fail"
    )
    return {
        "schema": SCHEMA,
        "campaign": "rtl3_device_top_host_load",
        "status": status,
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "design_top": "rtl/abi3/ot_a3_device_top.sv",
        "vehicle_geometry": VEHICLE_GEOMETRY,
        "deployment_loaded": "qwen3-8b-rom-single-chip (both entrypoints)",
        "what_ran": [
            "empty stores: the first Qwen3-8B ROM case traps and retires nothing",
            "program body and descriptor records written one 32-bit lane per "
            "cycle through host_* at the vehicle store geometry, relocated to "
            "row 0; no write refused; every row read back from the store model",
            "program header streamed through the admission beat port; legality, "
            "trap class, instruction count, entrypoint count and declared "
            "maximum retired work against the golden record",
            "both entrypoints run against the loaded stores: trap class, "
            "completion, fetched, retired, predicated off, issued, loop "
            "iterations, branches, wait-set evaluations, issue pulses, view "
            "pulses, views-resolved counter and event_signal_error against "
            "the golden record",
            "a write offered while busy, past the last row of each store, and "
            "past the last lane: refused, reported, store intact; the refusal "
            "flag clears on reset",
        ],
        "marker": iverilog["marker"] if agree else None,
        "simulators_agree": agree,
        "cases": cases,
        "claim_boundary": {
            "establishes": (
                "the design's host load path writes the control stores the "
                "sequencer then executes from, at the vehicle geometry, under "
                "two simulators"
            ),
            "does_not_establish": {
                "campaign_observation": (
                    "the L1-CP campaigns preload the stores by $readmemh in the "
                    "wrapper; their observation streams are compared by "
                    "tools/rtl_abi3_deployment_campaign.py, not here"
                ),
                "symbol_file_load": (
                    "the runtime symbol file is a combinational boundary of the "
                    "device top and is not behind host_*"
                ),
                "checker_independence": (
                    "one checker under two simulators, not two independently "
                    "written checkers"
                ),
            },
        },
        "source_sha256": sources,
        "tools": tools,
        "git": base.git_identity(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2
    summary = run(args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()} {case['marker']}")
    print(f"abi3 device top host load: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
