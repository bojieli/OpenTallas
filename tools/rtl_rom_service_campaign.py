#!/usr/bin/env python3
"""Run and record the two-simulator ROM read-service correlation campaign.

The campaign replays each generated ROM request set through the RTL twice --
once under Icarus Verilog and once as a separately compiled Verilator C++
executable -- and records the result as a canonical JSON artifact.  A vector set
counts only if both simulators print the exact marker derived from that set,
which names the number of requests, sense beats, bytes, row activations, masked
requests and refused requests that had to be reproduced.  Nothing about the
marker is written by hand: it comes from the reference decode in
tools/build_rom_service_vectors.py, which is written from the compiled ROM
region plan independently of the RTL.

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
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_ROOT = ROOT / "testdata/compiler/rom_service"
DEFAULT_OUTPUT = ROOT / "results/rtl/rom_service_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/rom/ot_rom_pkg.sv",
    "rtl/rom/ot_rom_read_service.sv",
)
ARRAY_SOURCE = "rtl/rom/ot_rom_bank_array.sv"
TESTBENCH_SOURCES = (
    "rtl/test/rom_service_top.sv",
    "rtl/test/tb_rom_service.sv",
    "rtl/test/rom_service_harness.cpp",
)
# The frozen contracts the RTL and the reference both transcribe.  They are
# hashed so that a change to the ROM plan or the wire format invalidates this
# evidence instead of silently outdating it.
CONTRACT_SOURCES = (
    "compiler/backends/rom/common/image.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/constants.py",
)
TOOL_SOURCES = (
    "tools/build_rom_service_vectors.py",
    "tools/rtl_rom_service_campaign.py",
)
IMAGE_FILES = (
    "rom_object.hex",
    "rom_shard.hex",
    "rom_repair.hex",
    "rom_mask.hex",
    "rom_request.hex",
    "rom_expect.hex",
    "rom_window.hex",
    "rom_meta.hex",
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
    return (
        text.replace(str(build), "<BUILD>")
        .replace(str(ROOT), "<ROOT>")
        .replace(str(Path.home()), "<HOME>")
    )


def resolve(name: str, pinned: Path | None) -> Path:
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
    name: str, command: list[str], cwd: Path, timeout: int
) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": canonical(shlex.join(command), cwd),
        "returncode": result.returncode,
        "log": canonical(result.stdout, cwd),
    }


def load_vector_set(directory: Path) -> dict[str, Any]:
    manifest = directory / "rom_service_vectors.json"
    if not manifest.exists():
        raise SystemExit(
            f"vector set is missing: {manifest}; run "
            "tools/build_rom_service_vectors.py first"
        )
    vectors = json.loads(manifest.read_text(encoding="utf-8"))
    for name, digest in vectors["image_sha256"].items():
        actual = sha256_file(directory / name)
        if actual != digest:
            raise SystemExit(
                f"image {directory / name} does not match the vector-set digest; "
                "regenerate with tools/build_rom_service_vectors.py"
            )
    # An executed request stream is only evidence about the device that
    # produced it.  If the functional device has moved since, the stream is
    # about an implementation that no longer exists, and saying so beats
    # publishing it under the current one's name.
    recorded = vectors.get("executed_source", {}).get("runtime_source_sha256")
    drift: list[str] = []
    if recorded:
        for rel, digest in sorted(recorded.items()):
            path = ROOT / rel
            if not path.exists() or sha256_file(path) != digest:
                drift.append(rel)
    vectors["_runtime_source_drift"] = drift
    return vectors


def run(build_root: Path | None, sets: list[str], timeout: int) -> dict[str, Any]:
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

    vector_sets = {name: load_vector_set(VECTOR_ROOT / name) for name in sets}

    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="opentallas-rom-rtl-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        rtl = [str(ROOT / path) for path in RTL_SOURCES]

        compile_stages = [
            run_stage(
                "iverilog.compile",
                [
                    str(executables["iverilog"]),
                    "-g2012",
                    "-s",
                    "tb_rom_service",
                    "-o",
                    str(build / "rom_service.vvp"),
                    *rtl,
                    str(ROOT / "rtl/test/rom_service_top.sv"),
                    str(ROOT / "rtl/test/tb_rom_service.sv"),
                ],
                build,
                timeout=1800,
            ),
            run_stage(
                "verilator.compile",
                [
                    str(executables["verilator"]),
                    "--cc",
                    "--exe",
                    "--build",
                    "-Wall",
                    "-Wno-DECLFILENAME",
                    "--top-module",
                    "rom_service_top",
                    "--Mdir",
                    "obj_rom",
                    *rtl,
                    str(ROOT / "rtl/test/rom_service_top.sv"),
                    str(ROOT / "rtl/test/rom_service_harness.cpp"),
                    "-CFLAGS",
                    "-std=c++17",
                ],
                build,
                timeout=1800,
            ),
            # The array that stands behind the sense interface is elaborated on
            # its own, and the campaign then requires the one warning it must
            # produce.  "There is no write path" is otherwise a comment; here a
            # tool says the storage array has no driver.
            run_stage(
                "verilator.array_lint",
                [
                    str(executables["verilator"]),
                    "--lint-only",
                    "-Wall",
                    "-Wno-fatal",
                    "-Wno-DECLFILENAME",
                    "-Wno-UNUSEDPARAM",
                    "--top-module",
                    "ot_rom_bank_array",
                    str(ROOT / "rtl/rom/ot_rom_pkg.sv"),
                    str(ROOT / ARRAY_SOURCE),
                ],
                build,
                timeout=600,
            ),
        ]
        lint = compile_stages[-1]
        lint["required_evidence"] = "Signal is not driven: 'rom_cell'"
        lint["evidence_present"] = lint["required_evidence"] in lint["log"]
        lint["other_warnings"] = [
            line
            for line in lint["log"].splitlines()
            if line.startswith("%Warning") and "rom_cell" not in line
        ]
        compiled = (
            all(stage["returncode"] == 0 for stage in compile_stages)
            and lint["evidence_present"]
            and not lint["other_warnings"]
        )

        if compiled:
            for name, vectors in vector_sets.items():
                run_dir = build / name
                run_dir.mkdir(parents=True, exist_ok=True)
                for image in IMAGE_FILES:
                    shutil.copy2(VECTOR_ROOT / name / image, run_dir / image)
                marker = vectors["required_marker"]
                for simulator, command in (
                    ("iverilog", [str(executables["vvp"]),
                                  str(build / "rom_service.vvp")]),
                    ("verilator", [str(build / "obj_rom/Vrom_service_top")]),
                ):
                    executed = run_stage(
                        f"{name}.{simulator}.run", command, run_dir, timeout=timeout
                    )
                    checks = CHECKS_RE.search(executed["log"])
                    passed = (
                        executed["returncode"] == 0
                        and marker in executed["log"]
                        and checks is not None
                    )
                    cases.append(
                        {
                            "name": f"{name}.{simulator}",
                            "vector_set": name,
                            "simulator": simulator,
                            "status": "pass" if passed else "fail",
                            "run_command": executed["command"],
                            "run_returncode": executed["returncode"],
                            "run_log": executed["log"],
                            "log_sha256": hashlib.sha256(
                                executed["log"].encode("utf-8")
                            ).hexdigest(),
                            "required_marker": marker,
                            "marker_present": marker in executed["log"],
                            "checks": int(checks.group(1)) if checks else None,
                        }
                    )

    sources = {
        path: sha256_file(ROOT / path)
        for path in sorted(
            RTL_SOURCES
            + (ARRAY_SOURCE,)
            + TESTBENCH_SOURCES
            + CONTRACT_SOURCES
            + TOOL_SOURCES
        )
    }
    for name in sets:
        directory = VECTOR_ROOT / name
        sources[f"testdata/compiler/rom_service/{name}/rom_service_vectors.json"] = (
            sha256_file(directory / "rom_service_vectors.json")
        )
        for image in IMAGE_FILES:
            sources[f"testdata/compiler/rom_service/{name}/{image}"] = sha256_file(
                directory / image
            )

    drift = {
        name: vectors["_runtime_source_drift"]
        for name, vectors in vector_sets.items()
        if vectors.get("_runtime_source_drift")
    }
    passed = (
        compiled
        and bool(cases)
        and all(case["status"] == "pass" for case in cases)
        and not drift
    )

    correlation = {
        "reference": "tools.build_rom_service_vectors.Reference, written from "
        "the compiled ROM region plan independently of the RTL",
        "compared": [
            "completion status: served, masked, or refused",
            "refusal class: unplaced ROM object, out of range, shard gap, "
            "quarantined resource, activated column repair, zero length",
            "sense-beat count and served-byte count per request",
            "row-activation count per request, against a row buffer that "
            "persists across requests",
            "the first and last beat record of every request: placement "
            "resource, resource address, region byte offset, physical row after "
            "repair translation, sense granule, byte count and activation bit",
            "a 64-bit order-sensitive digest over every beat record of the "
            "request, which is how a hundred-megabyte read is compared without "
            "publishing its beat stream",
            "a 64-bit digest over the operand-bus payload after the column mux, "
            "which for the windowed requests is authenticated checkpoint bytes",
            "the service's own request/beat/byte/activation/masked/refused "
            "counters against the sum of the per-request results",
            "the array's independently kept activation and sense counts",
            "the bytes and beats that actually crossed the operand bus, counted "
            "by an observer in the testbench top rather than by the service",
        ],
        "vector_sets": {
            name: {
                "product": vectors["product"],
                "scenario": vectors["scenario"],
                "deployment": vectors["deployment"],
                "plan": vectors["plan"],
                "requests": vectors["requests"],
                "totals": vectors["totals"],
                "window": vectors["window"],
                "runtime_health": vectors["runtime_health"],
                "executed_source": vectors["executed_source"],
                "runtime_source_drift": vectors["_runtime_source_drift"],
                "required_marker": vectors["required_marker"],
            }
            for name, vectors in vector_sets.items()
        },
    }

    return {
        "schema": "opentallas.rtl.rom_service_campaign.v1",
        "campaign": "rom_service_read_path_correlation",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "compile_stages": compile_stages,
        "correlation": correlation,
        "executed_stream_source_drift": drift,
        "tools": tools,
        "source_sha256": sources,
        "cases": cases,
        "claim_boundary": {
            "rom_macro_instantiated": False,
            "rom_cell_area_established": False,
            "rom_read_energy_established": False,
            "sense_margin_or_amplifier_established": False,
            "wordline_or_bitline_timing_established": False,
            "rom_yield_or_defect_rate_established": False,
            "row_activation_counted_not_priced": True,
            "sense_granule_width_is_a_declared_parameter": True,
            "column_redundancy_implemented": False,
            "column_redundancy_refused_rather_than_ignored": True,
            "row_redundancy_implemented_and_exercised": True,
            "region_mask_performs_no_array_access": True,
            "quarantined_resource_fails_closed": True,
            "unplaced_rom_object_fails_closed": True,
            "addressing_correlated_over_the_whole_address_space": True,
            "whole_decode_step_replayed_beat_by_beat": False,
            "operand_data_checked_against_checkpoint_bytes_on_a_window_only": True,
            "view_to_byte_range_walk_in_scope": False,
            "descriptor_or_program_admission_in_scope": False,
            "executed_request_stream_for_the_wafer_product": False,
            "dual_simulator_agreement": True,
            "physical_implementation_claimed": False,
        },
        "limitations": [
            "there is no ROM array in the RTL under test. The array sits behind "
            "the sense request/response interface and is supplied by the "
            "testbench top, so this campaign establishes addressing, ordering, "
            "masking, repair translation and operand alignment, and establishes "
            "nothing about cell area, read energy, sense margin, wordline or "
            "bitline delay, retention or defect rate",
            "the sense granule is a declared parameter of this block "
            "(ROM_SENSE_BYTES = 64), not a macro property read out of any "
            "collateral in this repository. Row activations and sense accesses "
            "are therefore counted, and are never converted into an energy here",
            "a decode step of the Qwen ROM deployment reads about fifteen "
            "gigabytes and no open-tool simulator will replay that beat by "
            "beat. Each vector set replays real requests up to a published beat "
            "budget and covers the rest of the address space with "
            "single-granule probes at every object, region, row and placement "
            "resource boundary. The requests dropped for budget, and the "
            "largest one dropped, are published in the vector set",
            "operand data is checked against authenticated checkpoint bytes "
            "only for the granules in the published window. Outside it the "
            "array returns a deterministic function of its own address, so what "
            "is checked there is conveyance and ordering, not weight content",
            "the DeepSeek wafer set has no executed request stream: that lane "
            "has produced no tokens (checklist W6.4). Its requests come from "
            "the compiled plan's own read unit and from every shard boundary "
            "the plan declares, which is derived evidence about addressing",
            "column redundancy is refused, not implemented. A read reaching a "
            "resource with an activated column repair fails closed with a "
            "distinct class rather than returning the unrepaired column",
            "the walk from a resolved tensor view to contiguous byte ranges is "
            "not in this block. Requests arrive as contiguous byte ranges and "
            "the campaign derives those ranges from the views the functional "
            "device resolved",
            "no descriptor CRC, program header or admission check is performed "
            "here; the tables arrive over the configuration channel already "
            "admitted",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=5400)
    parser.add_argument(
        "--set",
        action="append",
        dest="sets",
        default=None,
        help="vector-set directory name under testdata/compiler/rom_service",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    sets = args.sets or sorted(
        path.name for path in VECTOR_ROOT.iterdir() if path.is_dir()
    )
    if not sets:
        raise SystemExit(f"no vector sets under {VECTOR_ROOT}")

    if args.output.exists() and not args.force:
        print(
            f"refusing to overwrite {args.output}; pass --force to replace it",
            file=sys.stderr,
        )
        return 2

    summary = run(args.build_dir, sets, args.timeout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for stage in summary["compile_stages"]:
        print(f"{stage['name']}: rc={stage['returncode']}")
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()} checks={case['checks']}")
    print(f"rom service campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
