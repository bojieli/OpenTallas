#!/usr/bin/env python3
"""Run dual-simulator signed arithmetic and Qwen DMA/MATMUL RTL evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import random
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from compiler.tensor_accelerator.common import (  # noqa: E402
    canonical_json_bytes,
    load_strict_json,
)
from runtime.reference.formats import (  # noqa: E402
    NumericReferenceError,
    binary32_add,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_matmul_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_matmul_vectors.v1"
VECTOR_ID = "ad2d94e71e7a24d98e92cff7a097d616e3c84e3540d033650119d81dbaaa1dc5"
SIGNED_ADD_SEED = 0x5157454E334D4154
SIGNED_ADD_COUNT = 20_000
SIGNED_ADD_FINITE_SUCCESS_COUNT = 19_367
SIGNED_ADD_NONFINITE_REJECTION_COUNT = 597
SIGNED_ADD_OVERFLOW_REJECTION_COUNT = 36
INPUTS = 256
OUTPUTS = 64
WEIGHTS = INPUTS * OUTPUTS

RTL_PATHS = (
    ROOT / "rtl/ot_fp32_rne_pkg.sv",
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
    ROOT / "rtl/ot_ta_matmul_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_matmul_sequencer.sv",
)
ARITHMETIC_TOP = ROOT / "rtl/test/ot_fp32_signed_add_differential_top.sv"
ARITHMETIC_TB = ROOT / "rtl/test/tb_fp32_signed_add_differential.sv"
ARITHMETIC_HARNESS = ROOT / "rtl/test/fp32_signed_add_differential_harness.cpp"
PROGRAM_TB = ROOT / "rtl/test/tb_qwen_ta_dma_matmul.sv"
PROGRAM_HARNESS = ROOT / "rtl/test/qwen_ta_dma_matmul_harness.cpp"
CAMPAIGN_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_matmul_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_matmul_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_dma_matmul_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over Qwen DMA/MATMUL RTL"
    )
    result.add_argument("--vectors", required=True, type=Path)
    result.add_argument("--output", required=True, type=Path)
    return result


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _body_id(value: dict[str, Any], field: str) -> str:
    body = {key: item for key, item in value.items() if key != field}
    return _sha256(canonical_json_bytes(body))


def _version(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        raise RuntimeError(f"required tool is unavailable: {command[0]}")
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if result.returncode != 0 or not lines:
        raise RuntimeError(f"cannot query tool version: {shlex.join(command)}")
    return lines[0]


def _run(command: list[str], *, cwd: Path, timeout: int) -> tuple[int, str]:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("MAKE")
    }
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return result.returncode, result.stdout


def _normalize(value: str, *, build: Path) -> str:
    return value.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")


def _case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    *,
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compile_code, compile_log = _run(compile_command, cwd=ROOT, timeout=300)
    if compile_code == 0:
        run_code, run_log = _run(run_command, cwd=build, timeout=300)
    else:
        run_code, run_log = None, ""
    retained_compile = _normalize(compile_log, build=build)
    retained_run = _normalize(run_log, build=build)
    complete_log = retained_compile + retained_run
    passed = compile_code == 0 and run_code == 0 and marker in retained_run
    return {
        "command": _normalize(
            shlex.join(compile_command) + " && " + shlex.join(run_command),
            build=build,
        ),
        "compile_log": retained_compile,
        "compile_returncode": compile_code,
        "log_sha256": _sha256(complete_log.encode("utf-8")),
        "name": name,
        "run_log": retained_run,
        "run_returncode": run_code,
        "status": "pass" if passed else "fail",
    }


def _signed_add_files() -> dict[str, str]:
    rng = random.Random(SIGNED_ADD_SEED)
    directed = [
        0x00000000,
        0x80000000,
        0x00000001,
        0x00000002,
        0x00000003,
        0x003FFFFF,
        0x00400000,
        0x007FFFFE,
        0x007FFFFF,
        0x00800000,
        0x00800001,
        0x00FFFFFF,
        0x01000000,
        0x33800000,
        0x34000000,
        0x3E800000,
        0x3EFFFFFF,
        0x3F000000,
        0x3F000001,
        0x3F7FFFFF,
        0x3F800000,
        0x3F800001,
        0x3FFFFFFF,
        0x40000000,
        0x40400000,
        0x4AFFFFFF,
        0x4B000000,
        0x7E800000,
        0x7EFFFFFF,
        0x7F000000,
        0x7F7FFFFE,
        0x7F7FFFFF,
        0x80000001,
        0x807FFFFF,
        0x80800000,
        0xBF000000,
        0xBF000001,
        0xBF7FFFFF,
        0xBF800000,
        0xBF800001,
        0xBFFFFFFF,
        0xC0000000,
        0xFF000000,
        0xFF7FFFFE,
        0xFF7FFFFF,
        0x7F800000,
        0xFF800000,
        0x7FC00000,
        0xFFC12345,
    ]
    pairs = [(left, right) for left in directed for right in directed]
    for _ in range(3000):
        code = rng.getrandbits(32)
        while (code >> 23) & 0xFF == 0xFF:
            code = rng.getrandbits(32)
        pairs.append((code, code ^ 0x80000000))
        magnitude = code & 0x7FFFFFFF
        if magnitude and magnitude < 0x7F7FFFFF:
            adjacent = (code ^ 0x80000000) + (-1 if code >> 31 else 1)
            pairs.append((code, adjacent))
    while len(pairs) < SIGNED_ADD_COUNT:
        mode = len(pairs) % 7
        if mode == 0:
            left = rng.choice(directed)
            right = rng.getrandbits(32)
        elif mode == 1:
            exponent = rng.randrange(255)
            left = (rng.getrandbits(1) << 31) | (exponent << 23) | rng.getrandbits(23)
            delta = rng.randrange(-3, 4)
            other_exponent = max(0, min(254, exponent + delta))
            right = (
                (((left >> 31) ^ 1) << 31)
                | (other_exponent << 23)
                | rng.getrandbits(23)
            )
        else:
            left = rng.getrandbits(32)
            right = rng.getrandbits(32)
        pairs.append((left, right))

    packed: list[str] = []
    fields: list[str] = []
    error_counts = [0, 0, 0]
    for left, right in pairs[:SIGNED_ADD_COUNT]:
        if (left >> 23) & 0xFF == 0xFF or (right >> 23) & 0xFF == 0xFF:
            error, result = 1, 0
        else:
            try:
                error, result = 0, binary32_add(left, right)
            except NumericReferenceError:
                error, result = 2, 0
        error_counts[error] += 1
        expected = (error << 32) | result
        packed.append(f"{(left << 66) | (right << 34) | expected:025x}\n")
        fields.append(f"{left:08x} {right:08x} {expected:09x}\n")
    if error_counts != [
        SIGNED_ADD_FINITE_SUCCESS_COUNT,
        SIGNED_ADD_NONFINITE_REJECTION_COUNT,
        SIGNED_ADD_OVERFLOW_REJECTION_COUNT,
    ]:
        raise RuntimeError("signed-add differential vector partition differs")
    return {
        "signed_add.hex": "".join(packed),
        "signed_add_fields.hex": "".join(fields),
    }


def _program_files(vectors: dict[str, Any]) -> dict[str, str]:
    return {
        "matmul_expected.hex": "".join(
            f"{value:08x}\n" for value in vectors["expected_accumulator_codes"]
        ),
        "matmul_input.hex": "".join(
            f"{value:04x}\n" for value in vectors["input_codes"]
        ),
        "matmul_payload.hex": "".join(
            f"{value:02x}\n"
            for value in bytes.fromhex(vectors["weight_tile_payload_hex"])
        ),
    }


def run(vectors_path: Path) -> dict[str, Any]:
    vectors_path = Path(vectors_path).resolve()
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if (
        vectors.get("schema") != VECTOR_SCHEMA
        or vectors.get("vector_set_id") != VECTOR_ID
        or vectors.get("vector_set_id") != _body_id(vectors, "vector_set_id")
    ):
        raise ValueError("DMA/MATMUL vector identity differs")

    arithmetic_files = _signed_add_files()
    program_files = _program_files(vectors)
    marker_arithmetic = (
        "PASS: FP32 signed-add RTL differential cases=20000 seed=5157454e334d4154"
    )
    marker_program = (
        "PASS: Qwen DMA+MATMUL RTL slice commands=2 inputs=256 "
        "weights=16384 outputs=64 faults=7 "
        f"vector_set={VECTOR_ID}"
    )

    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-dma-matmul-") as raw:
        build = Path(raw)
        for name, payload in {**arithmetic_files, **program_files}.items():
            (build / name).write_text(payload, encoding="ascii")

        arithmetic_iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_fp32_signed_add_differential",
            "-o",
            str(build / "signed_add_simv"),
            str(RTL_PATHS[0]),
            str(ARITHMETIC_TB),
        ]
        arithmetic_verilator_compile = [
            "verilator",
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "--top-module",
            "ot_fp32_signed_add_differential_top",
            "--Mdir",
            str(build / "obj_signed_add"),
            str(RTL_PATHS[0]),
            str(ARITHMETIC_TOP),
            str(ARITHMETIC_HARNESS),
        ]
        program_iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_qwen_ta_dma_matmul",
            "-o",
            str(build / "program_simv"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_TB),
        ]
        program_verilator_compile = [
            "verilator",
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "--top-module",
            "ot_ta_dma_matmul_sequencer",
            "--Mdir",
            str(build / "obj_program"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_HARNESS),
        ]
        cases = [
            _case(
                "signed_add_iverilog",
                arithmetic_iverilog_compile,
                ["vvp", str(build / "signed_add_simv")],
                build=build,
                marker=marker_arithmetic,
            ),
            _case(
                "signed_add_verilator",
                arithmetic_verilator_compile,
                [str(build / "obj_signed_add/Vot_fp32_signed_add_differential_top")],
                build=build,
                marker=marker_arithmetic,
            ),
            _case(
                "program_iverilog",
                program_iverilog_compile,
                ["vvp", str(build / "program_simv")],
                build=build,
                marker=marker_program,
            ),
            _case(
                "program_verilator",
                program_verilator_compile,
                [str(build / "obj_program/Vot_ta_dma_matmul_sequencer")],
                build=build,
                marker=marker_program,
            ),
        ]

    static_paths = {
        str(path.relative_to(ROOT)): path
        for path in (
            *RTL_PATHS,
            ARITHMETIC_TOP,
            ARITHMETIC_TB,
            ARITHMETIC_HARNESS,
            PROGRAM_TB,
            PROGRAM_HARNESS,
            CAMPAIGN_SCHEMA_PATH,
            VECTOR_SCHEMA_PATH,
            VECTOR_BUILDER_PATH,
            Path(__file__).resolve(),
            vectors_path,
        )
    }
    source_sha256 = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    for name, payload in sorted({**arithmetic_files, **program_files}.items()):
        source_sha256[f"generated/{name}"] = _sha256(payload.encode("ascii"))

    composition = vectors["composition"]
    body: dict[str, Any] = {
        "arithmetic_correlation": {
            "finite_success_cases": SIGNED_ADD_FINITE_SUCCESS_COUNT,
            "nonfinite_rejection_cases": SIGNED_ADD_NONFINITE_REJECTION_COUNT,
            "oracle": "independent_exact_scalar_fraction",
            "overflow_rejection_cases": SIGNED_ADD_OVERFLOW_REJECTION_COUNT,
            "seed_hex": f"{SIGNED_ADD_SEED:016x}",
            "signed_add_cases": SIGNED_ADD_COUNT,
        },
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": {
            "activity_derived_power_or_timing": False,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "bf16_final_output_written": False,
            "complete_layer_execution": False,
            "complete_matmul_command": True,
            "complete_q_projection_graph_operation": False,
            "graph_valid_qwen_command_slice": True,
            "preloaded_attention_norm_slice": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "raw_fp32_accumulator_tile_written": True,
            "signed_fp32_add_differential": True,
            "ta_rtl_6_closed": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "program_correlation": {
            "accumulator_payload_sha256": composition["accumulator_payload_sha256"],
            "accumulator_write_count": OUTPUTS,
            "auxiliary_write_count": 0,
            "command_indices": composition["submitted_command_indices"],
            "crc_fail_stop_cases": 1,
            "dma_hbm_bytes": 32768,
            "dma_hbm_request_count": 512,
            "dma_sram_write_count": 2048,
            "graph_operation_id": composition["graph_operation_id"],
            "hbm_response_fail_stop_cases": 1,
            "input_payload_sha256": composition["input_payload_sha256"],
            "matmul_add_count": WEIGHTS,
            "matmul_input_read_count": INPUTS,
            "matmul_multiply_count": WEIGHTS,
            "matmul_weight_read_count": WEIGHTS,
            "numeric_fail_stop_cases": 4,
            "program_order_fail_stop_cases": 1,
            "weight_tile_payload_sha256": composition["weight_tile_payload_sha256"],
            "write_suppression_numeric_fault_cases": 4,
        },
        "schema": SCHEMA,
        "simulators": ["iverilog", "verilator"],
        "source_sha256": source_sha256,
        "status": "pass" if all(case["status"] == "pass" for case in cases) else "fail",
        "tools": {
            "iverilog": _version(["iverilog", "-V"]),
            "verilator": _version(["verilator", "--version"]),
        },
        "vector_set_id": vectors["vector_set_id"],
    }
    campaign = {**body, "campaign_id": _body_id(body, "campaign_id")}
    schema = load_strict_json(CAMPAIGN_SCHEMA_PATH)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(campaign)
    return campaign


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    if arguments.output.exists():
        parser().error(f"--output already exists: {arguments.output}")
    campaign = run(arguments.vectors)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(campaign))
        handle.flush()
        os.fsync(handle.fileno())
    print(campaign["campaign_id"])
    return 0 if campaign["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
