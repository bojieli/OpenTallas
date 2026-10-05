#!/usr/bin/env python3
"""Run dual-simulator arithmetic and adjacent Qwen DMA/RMSNorm RTL evidence."""

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
    binary32_bits_to_bf16_rne,
    binary32_multiply,
)
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    binary32_rsqrt_rne,
)


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_rmsnorm_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_dma_rmsnorm_vectors.v1"
VECTOR_ID = "ce2a725cc574f334273dbfdc93e6fab7fc4da48df8d2d4087f22307635212d81"
ARITHMETIC_SEED = 0x5157454E33524D53
ADD_COUNT = 5000
MULTIPLY_COUNT = 5000
BF16_COUNT = 5000
RSQRT_COUNT = 2000
ELEMENTS = 4096

RTL_PATHS = (
    ROOT / "rtl/ot_fp32_rne_pkg.sv",
    ROOT / "rtl/ot_fp32_rsqrt_rne.sv",
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
    ROOT / "rtl/ot_ta_rmsnorm_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_rmsnorm_sequencer.sv",
)
ARITHMETIC_TOP = ROOT / "rtl/test/ot_fp32_rne_differential_top.sv"
ARITHMETIC_TB = ROOT / "rtl/test/tb_fp32_rne_differential.sv"
ARITHMETIC_HARNESS = ROOT / "rtl/test/fp32_rne_differential_harness.cpp"
PROGRAM_TB = ROOT / "rtl/test/tb_qwen_ta_dma_rmsnorm.sv"
PROGRAM_HARNESS = ROOT / "rtl/test/qwen_ta_dma_rmsnorm_harness.cpp"
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_rmsnorm_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_dma_rmsnorm_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_dma_rmsnorm_vectors.py"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over Qwen DMA/RMSNorm RTL"
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


def _arithmetic_files() -> dict[str, str]:
    rng = random.Random(ARITHMETIC_SEED)
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
        0x3EFFFFFF,
        0x3F000000,
        0x3F000001,
        0x3F7FFFFF,
        0x3F800000,
        0x3F800001,
        0x3FFFFFFF,
        0x40000000,
        0x40400000,
        0x4B000000,
        0x7EFFFFFF,
        0x7F000000,
        0x7F7FFFFE,
        0x7F7FFFFF,
        0x80800000,
        0xBF000000,
        0xBF800000,
        0xC0000000,
        0xFF7FFFFF,
        0x7F800000,
        0xFF800000,
        0x7FC00000,
    ]

    def finite_code() -> int:
        while True:
            value = rng.getrandbits(32)
            if (value >> 23) & 0xFF != 0xFF:
                return value

    def pairs(count: int) -> list[tuple[int, int]]:
        values = [(left, right) for left in directed for right in directed]
        while len(values) < count:
            mode = len(values) % 8
            if mode == 0:
                values.append(
                    (finite_code() & 0x7FFFFFFF, finite_code() & 0x7FFFFFFF)
                )
            elif mode == 2:
                values.append((rng.choice(directed), finite_code()))
            else:
                values.append((finite_code(), finite_code()))
        return values[:count]

    add_packed: list[str] = []
    add_fields: list[str] = []
    for left, right in pairs(ADD_COUNT):
        if (
            left & 0x80000000
            or right & 0x80000000
            or (left >> 23) & 0xFF == 0xFF
            or (right >> 23) & 0xFF == 0xFF
        ):
            error, result = 1, 0
        else:
            try:
                result = binary32_add(left, right)
                error = 0
            except NumericReferenceError:
                error, result = 2, 0
        expected = (error << 32) | result
        packed = (left << 66) | (right << 34) | expected
        add_packed.append(f"{packed:025x}\n")
        add_fields.append(f"{left:08x} {right:08x} {expected:09x}\n")

    multiply_packed: list[str] = []
    multiply_fields: list[str] = []
    for left, right in pairs(MULTIPLY_COUNT):
        if (left >> 23) & 0xFF == 0xFF or (right >> 23) & 0xFF == 0xFF:
            error, result = 1, 0
        else:
            try:
                result = binary32_multiply(left, right)
                error = 0
            except NumericReferenceError:
                error, result = 2, 0
        expected = (error << 32) | result
        packed = (left << 66) | (right << 34) | expected
        multiply_packed.append(f"{packed:025x}\n")
        multiply_fields.append(f"{left:08x} {right:08x} {expected:09x}\n")

    codes = list(directed)
    while len(codes) < BF16_COUNT:
        codes.append(rng.getrandbits(32))
    bf16_packed: list[str] = []
    bf16_fields: list[str] = []
    for code in codes[:BF16_COUNT]:
        if (code >> 23) & 0xFF == 0xFF:
            error, saturated, result = 1, 0, 0
        else:
            quantized = binary32_bits_to_bf16_rne(code)
            error, saturated, result = 0, int(quantized.saturated), quantized.code
        expected = (error << 17) | (saturated << 16) | result
        packed = (code << 19) | expected
        bf16_packed.append(f"{packed:013x}\n")
        bf16_fields.append(f"{code:08x} {expected:05x}\n")

    rsqrt_codes = list(directed)
    while len(rsqrt_codes) < RSQRT_COUNT:
        if len(rsqrt_codes) % 7:
            rsqrt_codes.append(finite_code() & 0x7FFFFFFF)
        else:
            rsqrt_codes.append(rng.getrandbits(32))
    rsqrt_packed: list[str] = []
    rsqrt_fields: list[str] = []
    for code in rsqrt_codes[:RSQRT_COUNT]:
        if (
            code & 0x80000000
            or (code >> 23) & 0xFF == 0xFF
            or code & 0x7FFFFFFF == 0
        ):
            error, result = 1, 0
        else:
            error, result = 0, binary32_rsqrt_rne(code)
        expected = (error << 32) | result
        packed = (code << 34) | expected
        rsqrt_packed.append(f"{packed:017x}\n")
        rsqrt_fields.append(f"{code:08x} {expected:09x}\n")

    return {
        "arithmetic_add.hex": "".join(add_packed),
        "arithmetic_add_fields.hex": "".join(add_fields),
        "arithmetic_bf16.hex": "".join(bf16_packed),
        "arithmetic_bf16_fields.hex": "".join(bf16_fields),
        "arithmetic_mul.hex": "".join(multiply_packed),
        "arithmetic_mul_fields.hex": "".join(multiply_fields),
        "arithmetic_rsqrt.hex": "".join(rsqrt_packed),
        "arithmetic_rsqrt_fields.hex": "".join(rsqrt_fields),
    }


def _program_files(vectors: dict[str, Any]) -> dict[str, str]:
    return {
        "expected.hex": "".join(
            f"{value:04x}\n" for value in vectors["expected_codes"]
        ),
        "input.hex": "".join(
            f"{value:04x}\n" for value in vectors["input_codes"]
        ),
        "payload.hex": "".join(
            f"{value:02x}\n" for value in bytes.fromhex(vectors["dma_payload_hex"])
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
        raise ValueError("DMA/RMSNorm vector identity differs")

    arithmetic_files = _arithmetic_files()
    program_files = _program_files(vectors)
    marker_arithmetic = (
        "PASS: FP32 RTL differential add=5000 multiply=5000 bf16=5000 "
        "rsqrt=2000 seed=5157454e33524d53"
    )
    marker_program = (
        "PASS: Qwen DMA+RMSNorm RTL sequence commands=2 elements=4096 "
        f"faults=7 vector_set={VECTOR_ID}"
    )

    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-dma-rmsnorm-") as raw:
        build = Path(raw)
        for name, payload in {**arithmetic_files, **program_files}.items():
            (build / name).write_text(payload, encoding="ascii")

        arithmetic_iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_fp32_rne_differential",
            "-o",
            str(build / "fp32_simv"),
            str(RTL_PATHS[0]),
            str(RTL_PATHS[1]),
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
            "ot_fp32_rne_differential_top",
            "--Mdir",
            str(build / "obj_fp32"),
            str(RTL_PATHS[0]),
            str(RTL_PATHS[1]),
            str(ARITHMETIC_TOP),
            str(ARITHMETIC_HARNESS),
        ]
        program_iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_qwen_ta_dma_rmsnorm",
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
            "ot_ta_dma_rmsnorm_sequencer",
            "--Mdir",
            str(build / "obj_program"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_HARNESS),
        ]
        cases = [
            _case(
                "arithmetic_iverilog",
                arithmetic_iverilog_compile,
                ["vvp", str(build / "fp32_simv")],
                build=build,
                marker=marker_arithmetic,
            ),
            _case(
                "arithmetic_verilator",
                arithmetic_verilator_compile,
                [str(build / "obj_fp32/Vot_fp32_rne_differential_top")],
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
                [str(build / "obj_program/Vot_ta_dma_rmsnorm_sequencer")],
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
            "add_cases": ADD_COUNT,
            "bf16_conversion_cases": BF16_COUNT,
            "multiply_cases": MULTIPLY_COUNT,
            "oracle": "independent_exact_scalar_fraction",
            "reciprocal_square_root_cases": RSQRT_COUNT,
            "seed_hex": f"{ARITHMETIC_SEED:016x}",
        },
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": {
            "activity_derived_power_or_timing": False,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "complete_rmsnorm_graph_operation": True,
            "fp32_arithmetic_differential": True,
            "graph_valid_qwen_operation_sequence": True,
            "preloaded_hidden_input": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "program_correlation": {
            "command_indices": composition["submitted_command_indices"],
            "crc_fail_stop_cases": 1,
            "dma_hbm_bytes": 8192,
            "dma_hbm_request_count": 128,
            "dma_sram_write_count": 512,
            "expected_normalized_payload_sha256": composition[
                "expected_normalized_payload_sha256"
            ],
            "expected_output_payload_sha256": composition[
                "expected_output_payload_sha256"
            ],
            "graph_operation_id": composition["graph_operation_id"],
            "hbm_response_fail_stop_cases": 1,
            "input_payload_sha256": composition["input_payload_sha256"],
            "inverse_rms_binary32_code": composition[
                "inverse_rms_binary32_code"
            ],
            "mean_square_binary32_code": composition[
                "mean_square_binary32_code"
            ],
            "nonmonotonic_fail_stop_cases": 1,
            "numeric_fail_stop_cases": 4,
            "rmsnorm_element_count": ELEMENTS,
            "rmsnorm_sram_read_count": 8192,
            "rmsnorm_sram_write_count": 4096,
            "weight_payload_sha256": composition["weight_payload_sha256"],
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
