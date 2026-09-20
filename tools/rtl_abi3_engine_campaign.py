#!/usr/bin/env python3
"""Run and record the two-simulator RTL 3.0 *engine datapath* correlation.

This is the W8.3 counterpart of ``tools/rtl_abi3_campaign.py``, which
correlates the control plane.  That campaign binds every engine to a recording
no-op and says so in its own limitations: no engine arithmetic is modelled on
either side.  This one replays the engine vector set through the datapath RTL
twice -- once under Icarus Verilog and once as a separately compiled Verilator
C++ executable -- and requires both to print the exact marker the vector set
derived from a real execution on ``runtime.sim.device.Device``.

Nothing about the marker is written by hand.  Every case in the vector set is a
real ABI 3.0 program built with ``runtime.abi3.builder.DeploymentBuilder``,
admitted by ``runtime.abi3.verifier`` and executed with the real engines in
``runtime.sim.engines``; the operand and result images are the bytes those
engines read and wrote, read back out of device memory afterwards.

Tool identity is recorded, not assumed: the resolved executable path, its
SHA-256 and its self-reported version go into the artifact, and a Verilator
older than the pinned 5.050 or an Icarus older than 11.0 is refused rather than
silently accepted.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
VECTOR_DIR = ROOT / "testdata/compiler/abi3_engine"
VECTOR_JSON = VECTOR_DIR / "abi3_engine_vectors.json"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_engine_campaign.json"
VECTOR_SCHEMA = "opentallas.rtl.abi3_engine_vectors.v2"

PINNED_VERILATOR_VERSION = "5.050"
PINNED_IVERILOG_VERSION = "11.0"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    # ccf0d83 put ot_a3_mac_lane_pipe inside ot_a3_engine_array but left it
    # out of this list, so the campaign has not compiled since: Icarus
    # reports "Unknown module type: ot_a3_mac_lane_pipe" at
    # rtl/abi3/ot_a3_engine_array.sv:574.  The pipelined lane and its
    # package come with it.
    "rtl/proto/ot_mac_bf16_fp32_pipe.sv",
    "rtl/abi3/ot_a3_mac_lane_pipe.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    #: ot_a3_vector_add instantiates the pipelined binary32 adder, so the
    #: proto module has to be elaborated with it.
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    # The engine array instantiates the PIPELINED scaler
    # (rtl/abi3/ot_a3_engine_array.sv), so its sources are what the array is
    # built from; the combinational engine stays in the list because the
    # equivalence bench drives both.
    "rtl/proto/ot_fp32_mul_rne_pipe.sv",
    "rtl/abi3/ot_a3_vector_scale_pipe.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
)
TESTBENCH_SOURCES = (
    "rtl/test/a3_engine_top.sv",
    "rtl/test/tb_a3_engine.sv",
    "rtl/test/a3_engine_harness.cpp",
)
# The frozen numeric authorities the RTL transcribes.  They are hashed so that
# a change to any of them invalidates this evidence instead of silently
# outdating it.
CONTRACT_SOURCES = (
    "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md",
    "runtime/abi3/constants.py",
    "runtime/abi3/descriptors.py",
    "runtime/reference/formats.py",
    "runtime/sim/formats.py",
    "runtime/sim/backend.py",
    "runtime/sim/engines/tensor.py",
    "runtime/sim/engines/dma.py",
    "runtime/sim/engines/vector.py",
    "runtime/sim/engines/deepseek_vector.py",
    "runtime/sim/engines/selection.py",
    "runtime/reference/compression.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/reference/hadamard.py",
    "runtime/reference/index_score.py",
    "runtime/reference/vector.py",
)
TOOL_SOURCES = (
    "tools/build_abi3_engine_vectors.py",
    "tools/rtl_abi3_engine_campaign.py",
)
VECTOR_FILES = (
    "e3_m0.hex",
    "e3_m1.hex",
    "e3_m2.hex",
    "e3_m3.hex",
    "e3_expect.hex",
    "e3_case.hex",
    "e3_decode.hex",
    "e3_arith.hex",
    "e3_meta.hex",
)

CHECKS_RE = re.compile(r"checks=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")
IVERILOG_VERSION_RE = re.compile(r"Icarus Verilog version (\d+)\.(\d+)")

# Deliberate, single-source arithmetic defects.  A campaign is sensitive only
# if the modified RTL still compiles and both independently written checkers
# reject its output.  Exact source strings make each mutation reproducible and
# prevent an edit around the intended site from silently turning the mutation
# into a no-op.
MUTATIONS: tuple[dict[str, str], ...] = (
    {
        "id": "convert_narrowed_lsb",
        "source": "rtl/abi3/ot_a3_vector_convert.sv",
        "description": "invert the low bit of every converted BF16 result",
        "before": "out_data <= {16'b0, narrowed[15:0]};",
        "after": "out_data <= {16'b0, narrowed[15:1], ~narrowed[0]};",
    },
    {
        # The array now builds the PIPELINED scaler, so a mutation of the
        # combinational engine is no longer in the array's build path and would
        # be silently un-caught.  This mutates the engine the array actually
        # instantiates, and the fault is the same class: the committed word stops
        # depending on the product.
        "id": "scale_result_ignores_product",
        "source": "rtl/abi3/ot_a3_vector_scale_pipe.sv",
        "description": "commit the left operand instead of the SCALE product",
        "before": (
            "ot_fp32_rne_pkg::fp32_to_bf16_rne(product_value);"
        ),
        "after": (
            "ot_fp32_rne_pkg::fp32_to_bf16_rne(scale_bits_r);"
        ),
    },
    {
        "id": "hadamard_remove_normalization",
        "source": "rtl/abi3/ot_a3_vector_hadamard.sv",
        "description": "replace 1/sqrt(128) with 1.0",
        "before": "localparam [31:0] HADAMARD_SCALE = 32'h3db5_04f3;",
        "after": "localparam [31:0] HADAMARD_SCALE = 32'h3f80_0000;",
    },
    {
        "id": "index_score_remove_relu",
        "source": "rtl/abi3/ot_a3_vector_index_score.sv",
        "description": "propagate negative rounded head scores through ReLU",
        #: the narrowing moved off the product-add's cycle, so the ReLU now reads
        #: acc_narrowed -- the same fp32_to_bf16_rne of the same sum, one cycle later
        #: -- and this mutation follows it.  What it tests is unchanged: drop the
        #: negative-score clamp and the campaign must notice.
        "before": (
            "relu_value <= acc_narrowed[15]\n"
            "                            ? 32'b0 : "
            "{acc_narrowed[15:0], 16'b0};"
        ),
        "after": "relu_value <= {acc_narrowed[15:0], 16'b0};",
    },
    {
        "id": "compress_swap_output_planes",
        "source": "rtl/abi3/ot_a3_vector_compress_project.sv",
        "description": "store gate outputs before KV outputs",
        #: the index moved into a register computed a cycle ahead of the store, so
        #: the plane offset lives there now.  What this mutation tests is unchanged:
        #: swap the two output planes and the campaign must notice.
        "before": "(plane ? {16'b0, cfg_cols} : 32'b0) + {16'b0, col};",
        "after": "(plane ? 32'b0 : {16'b0, cfg_cols}) + {16'b0, col};",
    },
    {
        "id": "compress_split_product_add_rounding",
        "source": "rtl/abi3/ot_a3_vector_compress_project.sv",
        "description": (
            "replace the exact-product single-rounded dot step with a "
            "separately rounded binary32 multiply followed by add"
        ),
        "before": (
            "wire [33:0] accumulated =\n"
            "        ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne(\n"
            "            accumulator, h_rd_data[15:0], weight_code\n"
            "        );"
        ),
        "after": (
            "wire [33:0] split_product = ot_fp32_rne_pkg::fp32_mul_rne(\n"
            "        decoded_hidden[31:0], decoded_weight[31:0]\n"
            "    );\n"
            "    wire [33:0] accumulated = ot_fp32_rne_pkg::fp32_add_rne(\n"
            "        accumulator, split_product[31:0]\n"
            "    );"
        ),
    },
    {
        "id": "mhc_transpose_combination",
        "source": "rtl/abi3/ot_a3_vector_mhc_post.sv",
        "description": "address comb[destination][source] instead of source/dest",
        "before": (
            "({30'b0, source} * MULTIPLIER) +\n"
            "                        {30'b0, destination};"
        ),
        "after": (
            "({30'b0, destination} * MULTIPLIER) +\n"
            "                        {30'b0, source};"
        ),
    },
)


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
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=1800)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=3600)
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


def mutation_simulator_case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
) -> dict[str, Any]:
    """Compile one arithmetic mutation and require its checker to reject it.

    A syntax or elaboration failure is not sensitivity to arithmetic, so it is
    explicitly not counted as caught.  Mutation logs are represented by stable
    hashes and the first mismatch instead of being duplicated seven times in the
    retained artifact.
    """
    compiled = run_stage(f"{name}.compile", compile_command, build, timeout=1800)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, timeout=3600)
    compile_log = compiled["log"]
    run_log = executed["log"] if executed else ""
    marker_present = bool(executed and marker in run_log)
    caught = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] != 0
        and not marker_present
    )
    mismatch = next(
        (
            line.strip()
            for line in run_log.splitlines()
            if line.strip().startswith("FAIL:")
            or line.strip().startswith("FAILURES:")
        ),
        None,
    )
    checks = CHECKS_RE.search(run_log) if executed else None
    combined = compile_log + run_log
    return {
        "name": name,
        "status": "caught" if caught else "missed",
        "caught": caught,
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log_sha256": hashlib.sha256(
            compile_log.encode("utf-8")
        ).hexdigest(),
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log_sha256": hashlib.sha256(run_log.encode("utf-8")).hexdigest(),
        "log_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        "required_marker": marker,
        "marker_present": marker_present,
        "first_mismatch": mismatch,
        "checks_before_rejection": int(checks.group(1)) if checks else None,
    }


def load_vectors() -> dict[str, Any]:
    if not VECTOR_JSON.exists():
        raise SystemExit(
            f"vector set is missing: {VECTOR_JSON}; run "
            "tools/build_abi3_engine_vectors.py first"
        )
    vectors = json.loads(VECTOR_JSON.read_text(encoding="utf-8"))
    if vectors.get("schema") != VECTOR_SCHEMA:
        raise SystemExit(
            "the retained engine vectors predate descriptor-correlated "
            "fail-closed admission and exact-product product-add coverage; "
            "they are stale evidence and must not be replayed as a passing "
            "W8.3 campaign. Regenerate only after the frozen INDEX_SCORE "
            "Device implementation agrees with runtime.reference.index_score"
        )
    admission = vectors.get("descriptor_admission", {})
    if admission.get("schema") != "operator_view_numeric_exact_v1":
        raise SystemExit(
            "the engine vector set lacks the required descriptor-admission "
            "binding"
        )
    geometry = vectors.get("geometry", {})
    if geometry.get("case_stride") != 80 or geometry.get("arith_stride") != 12:
        raise SystemExit(
            "the engine vector record geometry lacks W8.3 admission or "
            "product-add fields"
        )
    for name, digest in vectors["image_sha256"].items():
        actual = sha256_file(VECTOR_DIR / name)
        if actual != digest:
            raise SystemExit(
                f"vector image {name} does not match the vector set digest; "
                "regenerate with tools/build_abi3_engine_vectors.py"
            )
    return vectors


def run(build_root: Path | None = None) -> dict[str, Any]:
    vectors = load_vectors()
    marker = vectors["required_marker"]
    mutations: list[dict[str, Any]] = []
    refusal_sources: dict[str, int] = {}
    for vector_case in vectors["cases"]:
        if int(vector_case["expected_fault_code"]) == 0:
            continue
        source = str(vector_case["expectation_source"])
        refusal_sources[source] = refusal_sources.get(source, 0) + 1

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

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-engine-rtl-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        for name in VECTOR_FILES:
            shutil.copy2(VECTOR_DIR / name, build / name)

        rtl = [str(ROOT / path) for path in RTL_SOURCES]
        iverilog_compile = [
            str(executables["iverilog"]),
            "-g2012",
            "-s",
            "tb_a3_engine",
            "-o",
            "e3_sim.vvp",
            *rtl,
            str(ROOT / "rtl/test/a3_engine_top.sv"),
            str(ROOT / "rtl/test/tb_a3_engine.sv"),
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
            "ot_a3_engine_top",
            "--Mdir",
            "obj_e3",
            *rtl,
            str(ROOT / "rtl/test/a3_engine_top.sv"),
            str(ROOT / "rtl/test/a3_engine_harness.cpp"),
            "-CFLAGS",
            "-std=c++17",
        ]
        # Each simulator writes a distinct executable/build tree. Run both in
        # parallel, then resolve them in canonical order for stable evidence.
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [
                pool.submit(
                    simulator_case,
                    "iverilog",
                    iverilog_compile,
                    [str(executables["vvp"]), "e3_sim.vvp"],
                    build,
                    marker,
                ),
                pool.submit(
                    simulator_case,
                    "verilator",
                    verilator_compile,
                    ["./obj_e3/Vot_a3_engine_top"],
                    build,
                    marker,
                ),
            ]
            cases = [future.result() for future in futures]

        for spec in MUTATIONS:
            source = ROOT / spec["source"]
            original = source.read_text(encoding="utf-8")
            occurrences = original.count(spec["before"])
            if occurrences != 1:
                raise SystemExit(
                    f"mutation {spec['id']} expected one exact replacement in "
                    f"{spec['source']}, found {occurrences}"
                )
            mutated = original.replace(spec["before"], spec["after"], 1)
            mutated_path = build / f"mutation_{spec['id']}_{source.name}"
            mutated_path.write_text(mutated, encoding="utf-8")
            mutated_rtl = [
                str(mutated_path) if path == spec["source"] else str(ROOT / path)
                for path in RTL_SOURCES
            ]
            vvp_name = f"e3_mutation_{spec['id']}.vvp"
            obj_name = f"obj_e3_mutation_{spec['id']}"
            mutation_iverilog_compile = [
                str(executables["iverilog"]),
                "-g2012",
                "-s",
                "tb_a3_engine",
                "-o",
                vvp_name,
                *mutated_rtl,
                str(ROOT / "rtl/test/a3_engine_top.sv"),
                str(ROOT / "rtl/test/tb_a3_engine.sv"),
            ]
            mutation_verilator_compile = [
                str(executables["verilator"]),
                "--cc",
                "--exe",
                "--build",
                "-Wall",
                "-Wno-fatal",
                "-Wno-DECLFILENAME",
                "--top-module",
                "ot_a3_engine_top",
                "--Mdir",
                obj_name,
                *mutated_rtl,
                str(ROOT / "rtl/test/a3_engine_top.sv"),
                str(ROOT / "rtl/test/a3_engine_harness.cpp"),
                "-CFLAGS",
                "-std=c++17",
            ]
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(
                        mutation_simulator_case,
                        "iverilog",
                        mutation_iverilog_compile,
                        [str(executables["vvp"]), vvp_name],
                        build,
                        marker,
                    ),
                    pool.submit(
                        mutation_simulator_case,
                        "verilator",
                        mutation_verilator_compile,
                        [f"./{obj_name}/Vot_a3_engine_top"],
                        build,
                        marker,
                    ),
                ]
                simulator_results = [future.result() for future in futures]
            mutations.append(
                {
                    "id": spec["id"],
                    "source": spec["source"],
                    "description": spec["description"],
                    "exact_replacement": {
                        "before": spec["before"],
                        "after": spec["after"],
                    },
                    "source_sha256": hashlib.sha256(
                        original.encode("utf-8")
                    ).hexdigest(),
                    "mutated_source_sha256": hashlib.sha256(
                        mutated.encode("utf-8")
                    ).hexdigest(),
                    "simulators": simulator_results,
                    "caught_by_both": all(
                        result["caught"] for result in simulator_results
                    ),
                }
            )

    sources = {
        path: sha256_file(ROOT / path)
        for path in sorted(
            RTL_SOURCES + TESTBENCH_SOURCES + CONTRACT_SOURCES + TOOL_SOURCES
        )
    }
    sources["testdata/compiler/abi3_engine/abi3_engine_vectors.json"] = sha256_file(
        VECTOR_JSON
    )
    for name in VECTOR_FILES:
        sources[f"testdata/compiler/abi3_engine/{name}"] = sha256_file(
            VECTOR_DIR / name
        )

    all_mutations_caught = all(item["caught_by_both"] for item in mutations)
    passed = all(case["status"] == "pass" for case in cases)
    passed = passed and all_mutations_caught
    check_counts = {case["name"]: case["checks"] for case in cases}
    if passed and len({value for value in check_counts.values()}) != 1:
        # Two checkers that print the same marker but ran a different number of
        # comparisons are not two checks of the same thing.
        passed = False

    return {
        "schema": "opentallas.rtl.abi3_engine_campaign.v1",
        "campaign": "rtl3_abi3_engine_datapath_correlation",
        "status": "pass" if passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "simulators_counted": ["iverilog_vvp", "verilator_cpp_executable"],
        "required_marker": marker,
        "checks_per_simulator": check_counts,
        "mutation_sensitivity": {
            "policy": (
                "a mutation is caught only when its modified RTL compiles, "
                "the checker executes and returns failure, and the baseline "
                "PASS marker is absent"
            ),
            "mutation_count": len(mutations),
            "all_caught_by_both_simulators": all_mutations_caught,
            "mutations": mutations,
        },
        "correlation": {
            "reference": "runtime.sim.device.Device with runtime.sim.engines",
            "engine_policy": vectors["engine_policy"],
            "case_count": vectors["case_count"],
            "positive_case_count": vectors["positive_case_count"],
            "fault_case_count": vectors["fault_case_count"],
            "family_count": vectors["family_count"],
            "families": vectors["families"],
            "result_word_count": vectors["result_word_count"],
            "mac_count": vectors["mac_count"],
            "decode_probe_count": vectors["decode_probe_count"],
            "decode_reference": vectors["decode_reference"],
            "arith_probe_count": vectors["arith_probe_count"],
            "arith_reference": vectors["arith_reference"],
            "numeric_reference": vectors["numeric_reference"],
            "descriptor_admission": vectors["descriptor_admission"],
            "refusal_count_by_expectation_source": refusal_sources,
            "vector_rtl_scope": vectors["vector_rtl_scope"],
            "compared": [
                "every element the functional engine wrote, word for word, in "
                "the view's own logical order",
                "the fault class of every Device refusal, classified from the "
                "message the functional engine's EngineError carried",
                "ERR_SHAPE for every RTL-only bounded-profile or descriptor-"
                "admission refusal whose unmodified ABI 3.0 program the Device "
                "successfully executed",
                "that a refused operation left its whole destination window "
                "holding the unwritten sentinel, so a partial result is a "
                "failure rather than a pass",
                "TENSOR.MATMUL output element count and BF16 output saturation "
                "count, against tensor.output_elements and tensor.saturations",
                "VECTOR.ADD, CONVERT, SCALE and HADAMARD element counts and "
                "the saturation counts published where their contracts do",
                "VECTOR.INDEX_SCORE output and saturation counts separately "
                "from its full site-by-head-by-candidate-by-depth "
                "vector.elements work count",
                "VECTOR.COMPRESS/COMPRESS_PROJECT packed KV-then-gate FP32 "
                "output and VECTOR.MHC/HYPER_CONNECT_POST source/destination "
                "matrix orientation, result and saturation counts, and "
                "vector.elements count",
                "SELECTION.ARGMAX selected token, vocabulary elements read and "
                "tie multiplicity, against selection.vocabulary_elements and "
                "selection.tie_multiplicity",
                "DMA.GATHER and DMA.SCATTER moved-element count, against "
                "dma.gather_elements and dma.scatter_elements",
                "the complete code space of E4M3FN, E2M1 and E8M0 and a "
                "signed, four-significand sweep of every BF16 exponent, "
                "against runtime.sim.formats",
                "binary32 add, multiply and BF16 rounding plus the exact-"
                "product single-rounded BF16 product-add primitive over a "
                "corner cross-product and seeded spreads, against "
                "runtime.reference.formats, whose fractions.Fraction "
                "arithmetic rounds once with no host floating point on the "
                "reference side",
                "operator arity, every input/output dtype, rank, dimension and "
                "scaled flag, every NUMERIC control, the full contract digest "
                "and all auxiliary bindings before a bounded VECTOR dispatch",
                "that an operation the array does not implement is refused "
                "rather than routed to another datapath",
            ],
        },
        "tools": tools,
        "source_sha256": sources,
        "cases": cases,
        "claim_boundary": {
            "establishes": [
                "the eleven integrated engine opcode pairs in rtl/abi3/ "
                "produce bit-identical results to the functional simulator's "
                "engines on every case of this vector set, under two "
                "independently written checkers on two simulators",
                "bounded CONVERT, SCALE, HADAMARD, INDEX_SCORE, "
                "COMPRESS_PROJECT and HYPER_CONNECT_POST RTL agrees in output, "
                "fault class and architectural counters within the exact "
                "vector_rtl_scope published beside this claim",
                "seven independent source mutations -- conversion rounding, "
                "scaling arithmetic, Hadamard normalization, INDEX_SCORE "
                "ReLU, compressor plane order, compressor exact-product "
                "rounding and MHC matrix orientation -- all compile and are "
                "rejected by both simulators",
                "the storage-format decoders are exhaustively correct over "
                "E4M3FN, E2M1 and E8M0 against the exact Fraction reference",
                "the sequential contraction contract is reproduced for "
                "BF16 x BF16, FP8 x FP8 and block-scaled MXFP4 x FP8, "
                "including amendment A15's two-dimensional scale block",
                f"the {refusal_sources.get('device_fault', 0)} Device refusals "
                "agree in class, while every explicit bounded-profile and "
                "descriptor-admission negative refuses with ERR_SHAPE; every "
                "refusal leaves the whole destination untouched",
                "the binary32 add, multiply and BF16 rounding these datapaths "
                "are built from, plus their exact-product single-rounded BF16 "
                "product-add primitive, agree with runtime.reference.formats "
                "over directed corners and seeded spreads that reach signed "
                "zero, both smallest subnormals, the largest finite and the "
                "nonfinite band",
            ],
            "does_not_establish": {
                "blocked_contraction_contract": (
                    "only bf16_bf16_fp32_sequential_rne_v1 is correlated. The "
                    "blocked contract's association is the executing "
                    "implementation's declared one, so bit-exactness against "
                    "it is not a well-posed claim about a different "
                    "implementation and is not made"
                ),
                "fault_position": (
                    "the new CONVERT, SCALE, HADAMARD, INDEX_SCORE, "
                    "COMPRESS_PROJECT and HYPER_CONNECT_POST blocks preflight "
                    "or buffer the whole bounded operation, and late-poison "
                    "cases prove their destinations stay untouched. Legacy "
                    "TENSOR.MATMUL and VECTOR.ADD stop at the first faulting "
                    "output; their fault cases place the first offender in "
                    "the first output, so atomicity after a later legacy "
                    "fault is NOT established"
                ),
                "throughput_or_latency": (
                    "the lane computes one multiply-accumulate every five "
                    "cycles by construction, to keep one binary32 operation "
                    "per pipeline stage. No cycle count in this campaign is a "
                    "performance claim, and none feeds any timing model"
                ),
                "other_engine_families": (
                    "ATTENTION, ROUTE, REDUCTION, LINK and STATE have no "
                    "datapath in this engine array. SILU_MUL, SOFTMAX and "
                    "SQRT_SOFTPLUS are wholly absent because their correctly "
                    "rounded transcendental RTL does not exist; SCALE.SIGMOID, "
                    "CONVERT block-dequantize/two-output-quantize, "
                    "COMPRESS_POOL/STATE_UPDATE, MHC_PRE/HEAD, non-unit-scale "
                    "or non-four-head INDEX_SCORE and trailing-axis SCALE "
                    "broadcasting are not covered. Standalone RMS_NORM, "
                    "HEAD_RMS_NORM and ROPE RTL remains outside this integrated "
                    "campaign. Also absent are "
                    "TENSOR.GROUPED_MATMUL, ROUTED_MATMUL and EMBED_LOOKUP, "
                    "DMA.TRANSFER and FILL, and SELECTION.TOKEN_APPEND. "
                    "SELECTION.SAMPLE has no governed contract on either side"
                ),
                "integration_with_the_control_plane": (
                    "the sequencer of W8.6 and these datapaths are correlated "
                    "separately and are not wired together. Nothing here shows "
                    "that a resolved view drives the operand addresses these "
                    "blocks read; the operand images are the bytes the "
                    "functional device's resolver produced, supplied directly"
                ),
                "memory_macros": (
                    "operand and result memories are behavioural arrays in the "
                    "verification top. No SRAM or ROM macro, no bank conflict, "
                    "no ECC and no arbitration is modelled"
                ),
                "exhaustive_arithmetic": (
                    "the arithmetic probe is a directed corner sweep and a "
                    "seeded spread, not an exhaustive proof. It samples "
                    f"{vectors['arith_probe_count']:,} "
                    "of the 2**64 binary32 operand pairs, chosen where a "
                    "rounding or normalisation defect is most likely to live; "
                    "it does not establish IEEE conformance of the package"
                ),
                "physical_realisability": (
                    "simulation says nothing about area, timing or power. The "
                    "routed characterisation is a separate artifact and states "
                    "its own boundary"
                ),
            },
        },
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
        print(f"{case['name']}: {case['status'].upper()} checks={case['checks']}")
    print(f"abi3 engine rtl campaign: {summary['status'].upper()} -> {args.output}")
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
