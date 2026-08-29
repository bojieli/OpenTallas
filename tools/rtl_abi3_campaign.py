#!/usr/bin/env python3
"""Run and record the two-simulator RTL 3.0 correlation campaign.

The campaign replays the ABI 3.0 vector set through the RTL twice -- once under
Icarus Verilog and once as a separately compiled Verilator C++ executable -- and
records the result as a canonical JSON artifact.  A run counts only if both
simulators print the exact marker derived from the vector set, which names the
number of programs, program headers, engine-issue events and traps that had to
be reproduced.  Nothing about the marker is written by hand: it comes from the
golden execution of every program on runtime.sim.device.Device.

Tool identity is recorded, not assumed: the resolved executable path, its
SHA-256 and its self-reported version go into the artifact, and a Verilator
older than the pinned 5.050 or an Icarus older than 11.0 is refused rather than
silently accepted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/compiler/abi3"
VECTOR_JSON = VECTOR_DIR / "abi3_rtl_vectors.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_program_header.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_microsequencer_top.sv",
    "rtl/test/tb_a3_microsequencer.sv",
    "rtl/test/a3_microsequencer_harness.cpp",
)
# The frozen contracts the RTL transcribes.  They are hashed so that a change to
# the ABI invalidates this evidence instead of silently outdating it.
CONTRACT_SOURCES = (
    "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md",
    "runtime/abi3/constants.py",
    "runtime/abi3/records.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/verifier.py",
    "runtime/sim/device.py",
)
TOOL_SOURCES = (
    "tools/build_abi3_rtl_vectors.py",
    "tools/rtl_abi3_campaign.py",
)
VECTOR_FILES = (
    "a3_program.hex",
    "a3_header.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
    "a3_case.hex",
    "a3_issue.hex",
    "a3_meta.hex",
)

CHECKS_RE = re.compile(r"checks=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical(text: str, build: Path) -> str:
    """Strip machine-specific paths so the artifact is reproducible."""
    return (
        text.replace(str(build), "<BUILD>")
        .replace(str(ROOT), "<ROOT>")
        .replace(str(Path.home()), "<HOME>")
    )


def resolve(name: str, pinned: Path | None) -> Path:
    """Prefer the pinned toolchain, then PATH; never a guess."""
    override = os.environ.get(f"OPENTALLAS_{name.upper()}")
    if override:
        return Path(override)
    if pinned is not None and pinned.exists():
        return pinned
    found = shutil.which(name)
    if found is None:
        raise SystemExit(f"required tool is unavailable: {name}")
    return Path(found)


def tool_record(executable: Path, version_args: list[str]) -> dict[str, Any]:
    """Identify one tool: canonical path, executable digest, self-report."""
    result = subprocess.run(
        [str(executable), *version_args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical(str(executable), ROOT),
        "executable_sha256": sha256_file(executable),
        "version": lines[0] if lines else "no version text",
    }


def require_versions(tools: dict[str, dict[str, Any]]) -> None:
    verilator = tools["verilator"]["version"]
    match = VERILATOR_VERSION_RE.search(verilator)
    if match is None or (int(match.group(1)), int(match.group(2))) < (5, 50):
        raise SystemExit(
            f"Verilator {PINNED_VERILATOR_VERSION} or newer is required, found "
            f"{verilator!r}; set OPENTALLAS_VERILATOR or install the pinned build"
        )
    icarus = tools["iverilog"]["version"]
    match = IVERILOG_VERSION_RE.search(icarus)
    if match is None or (int(match.group(1)), int(match.group(2))) < (11, 0):
        raise SystemExit(
            f"Icarus Verilog {PINNED_IVERILOG_VERSION} or newer is required, "
            f"found {icarus!r}"
        )


def run_stage(
    name: str, command: list[str], build: Path, timeout: int
) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=build,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
    }


def simulator_case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=900)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=1800)
    log = compiled["log"] + (executed["log"] if executed else "")
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and marker in executed["log"]
    )
    checks = CHECKS_RE.search(executed["log"]) if executed else None
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": executed["log"] if executed else "",
        "log_sha256": hashlib.sha256(log.encode("utf-8")).hexdigest(),
        "required_marker": marker,
        "marker_present": bool(executed and marker in executed["log"]),
        "checks": int(checks.group(1)) if checks else None,
    }


def load_vectors() -> dict[str, Any]:
    if not VECTOR_JSON.exists():
        raise SystemExit(
            f"vector set is missing: {VECTOR_JSON}; run "
            "tools/build_abi3_rtl_vectors.py first"
        )
    vectors = json.loads(VECTOR_JSON.read_text(encoding="utf-8"))
    for name, digest in vectors["image_sha256"].items():
        actual = sha256_file(VECTOR_DIR / name)
        if actual != digest:
            raise SystemExit(
                f"vector image {name} does not match the vector set digest; "
                "regenerate with tools/build_abi3_rtl_vectors.py"
            )
    return vectors


def run(build_root: Path | None = None) -> dict[str, Any]:
    vectors = load_vectors()
    marker = vectors["required_marker"]

    executables = {
        "iverilog": resolve("iverilog", None),
        "vvp": resolve("vvp", None),
        "verilator": resolve(
            "verilator",
            TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator",
        ),
        "cxx": resolve("g++", None),
    }
    version_flags = {
        "iverilog": ["-V"],
        "vvp": ["-V"],
        "verilator": ["--version"],
        "cxx": ["--version"],
    }
    tools = {
        name: tool_record(path, version_flags[name])
        for name, path in executables.items()
    }
    require_versions(tools)

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-rtl-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        for name in VECTOR_FILES:
            shutil.copy2(VECTOR_DIR / name, build / name)

        rtl = [str(ROOT / path) for path in RTL_SOURCES]
        iverilog_compile = [
            str(executables["iverilog"]),
            "-g2012",
            "-s",
            "tb_a3_microsequencer",
            "-o",
            "a3_sim.vvp",
            *rtl,
            str(ROOT / "rtl/test/a3_microsequencer_top.sv"),
            str(ROOT / "rtl/test/tb_a3_microsequencer.sv"),
        ]
        verilator_compile = [
            str(executables["verilator"]),
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            "--top-module",
            "ot_a3_microsequencer_top",
            "--Mdir",
            "obj_a3",
            *rtl,
            str(ROOT / "rtl/test/a3_microsequencer_top.sv"),
            str(ROOT / "rtl/test/a3_microsequencer_harness.cpp"),
            "-CFLAGS",
            "-std=c++17",
        ]
        cases = [
            simulator_case(
                "iverilog",
                iverilog_compile,
                [str(executables["vvp"]), "a3_sim.vvp"],
                build,
                marker,
            ),
            simulator_case(
                "verilator",
                verilator_compile,
                ["./obj_a3/Vot_a3_microsequencer_top"],
                build,
                marker,
            ),
        ]

    sources = {
        path: sha256_file(ROOT / path)
        for path in sorted(
            RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES
        )
    }
    sources["testdata/compiler/abi3/abi3_rtl_vectors.json"] = sha256_file(VECTOR_JSON)
    for name in VECTOR_FILES:
        sources[f"testdata/compiler/abi3/{name}"] = sha256_file(VECTOR_DIR / name)

    passed = all(case["status"] == "pass" for case in cases)
    return {
        "schema": "opentallas.rtl.abi3_campaign.v1",
        "campaign": "rtl3_abi3_correlation",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "required_marker": marker,
        "correlation": {
            "reference": "runtime.sim.device.Device",
            "case_count": vectors["case_count"],
            "program_run_count": vectors["program_run_count"],
            "header_admission_count": vectors["header_admission_count"],
            "issue_event_count": vectors["issue_event_count"],
            "trap_count": vectors["trap_count"],
            "positive_case_count": vectors["positive_case_count"],
            "negative_case_count": vectors["negative_case_count"],
            "compared": [
                "program header admission and trap class",
                "instructions fetched, retired and predicated off",
                "instructions issued and loop iterations",
                "branches taken and wait-set evaluations",
                "engine issue sequence: family, subopcode, descriptor ID",
                "state prepare, commit, discard, read and advance counts",
                "state commit applied or discarded, and rows committed",
                "trap class and first faulting instruction",
            ],
        },
        "tools": tools,
        "source_sha256": sources,
        "cases": cases,
        "limitations": [
            "engine datapaths are out of scope: the issue port carries family, "
            "subopcode and descriptor ID only",
            "descriptor record CRC32C and the header's SHA-256 digests are not "
            "checked in RTL; instruction and header CRC32C are",
            "predicate kinds that require an engine or a memory read "
            "(ENGINE_STATUS, ROUTE_VALID, BOOLEAN_OBJECT, EOS_MEMBER) fail "
            "closed with trap class 4 instead of being evaluated",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing campaign artifact",
    )
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(
            f"refusing to overwrite {args.output}; pass --force to replace it",
            file=sys.stderr,
        )
        return 2

    summary = run(args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()}")
    print(f"abi3 rtl campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
