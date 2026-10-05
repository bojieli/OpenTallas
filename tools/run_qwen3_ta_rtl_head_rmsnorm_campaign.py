#!/usr/bin/env python3
"""Run dual-simulator Qwen Q/K per-head RMSNorm RTL evidence."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_head_rmsnorm_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_head_rmsnorm_vectors.v1"
VECTOR_ID = "9d6ff4c9ad10e03592d02ec3edebaf6bc341285fac8c69bc09b7daa7891ee791"
Q_CAMPAIGN_ID = "af8c787f6c6995527ca0b75ab813b06f9ed05f9c18066ccf3e05ea1fa4d69603"
KV_CAMPAIGN_ID = "584e0f388d6295a3abc5d6d6f96e5f32500b493bf81d6a7b09d51b112a735894"
QUALIFICATION_ID = "42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae"

RTL_PATHS = (
    ROOT / "rtl/ot_fp32_rne_pkg.sv",
    ROOT / "rtl/ot_fp32_rsqrt_rne.sv",
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
    ROOT / "rtl/ot_ta_head_rmsnorm_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_head_rmsnorm_sequencer.sv",
)
PROGRAM_TB = ROOT / "rtl/test/tb_qwen_ta_head_rmsnorm.sv"
PROGRAM_HARNESS = ROOT / "rtl/test/qwen_ta_head_rmsnorm_harness.cpp"
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_head_rmsnorm_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_head_rmsnorm_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_head_rmsnorm_vectors.py"
Q_CAMPAIGN_PATH = ROOT / "results/tensor_accelerator/qwen3_rtl_q_proj_campaign.json"
KV_CAMPAIGN_PATH = ROOT / "results/tensor_accelerator/qwen3_rtl_kv_proj_campaign.json"
QUALIFICATION_PATH = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"

OBSERVATION_RE = re.compile(
    r"cycles=(?P<cycles>[0-9]+) "
    r"request_stalls=(?P<request_stalls>[0-9]+) "
    r"read_stalls=(?P<read_stalls>[0-9]+) "
    r"write_stalls=(?P<write_stalls>[0-9]+)"
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
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
        [executable, *command[1:]],
        check=False,
        capture_output=True,
        text=True,
    )
    text = (result.stdout + result.stderr).strip()
    if result.returncode != 0 or not text:
        raise RuntimeError(f"cannot identify tool: {command[0]}")
    return text.splitlines()[0]


def _normalize(value: str, build: Path) -> str:
    return value.replace(str(build), "<BUILD>").replace(str(ROOT), "<ROOT>")


def _case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    *,
    build: Path,
    marker: str,
) -> dict[str, Any]:
    compiled = subprocess.run(
        compile_command,
        cwd=build,
        check=False,
        capture_output=True,
        text=True,
    )
    compile_log = _normalize(compiled.stdout + compiled.stderr, build)
    run_code: int | None = None
    run_log = ""
    if compiled.returncode == 0:
        executed = subprocess.run(
            run_command,
            cwd=build,
            check=False,
            capture_output=True,
            text=True,
        )
        run_code = executed.returncode
        run_log = _normalize(executed.stdout + executed.stderr, build)
    observation = None
    match = OBSERVATION_RE.search(run_log)
    if match:
        observation = {key: int(value) for key, value in match.groupdict().items()}
    passed = compiled.returncode == 0 and run_code == 0 and marker in run_log
    full_command = f"{shlex.join(compile_command)} && {shlex.join(run_command)}"
    retained_log = compile_log + run_log
    return {
        "command": _normalize(full_command, build),
        "compile_log": compile_log,
        "compile_returncode": compiled.returncode,
        "log_sha256": _sha256(retained_log.encode("utf-8")),
        "name": name,
        "observation": observation,
        "run_log": run_log,
        "run_returncode": run_code,
        "status": "pass" if passed else "fail",
    }


def _hex(values: list[int], width: int) -> str:
    return "".join(f"{value:0{width}x}\n" for value in values)


def _program_files(vectors: dict[str, Any]) -> dict[str, str]:
    return {
        "head_rmsnorm_commands.hex": "".join(
            f"{command['record_hex']}\n" for command in vectors["commands"]
        ),
        "head_rmsnorm_q_input.hex": _hex(vectors["q_input_codes"], 4),
        "head_rmsnorm_k_input.hex": _hex(vectors["k_input_codes"], 4),
        "head_rmsnorm_q_weight.hex": _hex(vectors["q_weight_codes"], 4),
        "head_rmsnorm_k_weight.hex": _hex(vectors["k_weight_codes"], 4),
        "head_rmsnorm_q_output.hex": _hex(vectors["q_output_codes"], 4),
        "head_rmsnorm_k_output.hex": _hex(vectors["k_output_codes"], 4),
        "head_rmsnorm_k_mean.hex": _hex(vectors["k_mean_square_codes"], 8),
        "head_rmsnorm_k_inverse.hex": _hex(vectors["k_inverse_rms_codes"], 8),
    }


def _validate_dependency(path: Path, expected_id: str, id_field: str) -> None:
    value = load_strict_json(path)
    if (
        value.get(id_field) != expected_id
        or value.get("status") != "pass"
        or value.get(id_field) != _body_id(value, id_field)
    ):
        raise ValueError(f"retained dependency differs: {path.name}")


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
        raise ValueError("Q/K head RMSNorm vector identity differs")
    _validate_dependency(Q_CAMPAIGN_PATH, Q_CAMPAIGN_ID, "campaign_id")
    _validate_dependency(KV_CAMPAIGN_PATH, KV_CAMPAIGN_ID, "campaign_id")
    _validate_dependency(QUALIFICATION_PATH, QUALIFICATION_ID, "report_id")
    program_files = _program_files(vectors)
    marker = (
        "PASS: Qwen Q/K head RMSNorm RTL commands=4 rows=40 elements=5120 "
        "reductions=5080 rsqrt=40 outputs=5120 faults=1"
    )

    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-head-rms-") as raw:
        build = Path(raw)
        for name, payload in program_files.items():
            (build / name).write_text(payload, encoding="ascii")

        iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_qwen_ta_head_rmsnorm",
            "-o",
            str(build / "head_rmsnorm_simv"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_TB),
        ]
        verilator_compile = [
            "verilator",
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "--top-module",
            "ot_ta_dma_head_rmsnorm_sequencer",
            "--Mdir",
            str(build / "obj_head_rmsnorm"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_HARNESS),
        ]
        cases = [
            _case(
                "head_rmsnorm_iverilog",
                iverilog_compile,
                ["vvp", str(build / "head_rmsnorm_simv")],
                build=build,
                marker=marker,
            ),
            _case(
                "head_rmsnorm_verilator",
                verilator_compile,
                [
                    str(
                        build
                        / "obj_head_rmsnorm/"
                        "Vot_ta_dma_head_rmsnorm_sequencer"
                    )
                ],
                build=build,
                marker=marker,
            ),
        ]

    static_paths = {
        str(path.relative_to(ROOT)): path
        for path in (
            *RTL_PATHS,
            PROGRAM_TB,
            PROGRAM_HARNESS,
            CAMPAIGN_SCHEMA_PATH,
            VECTOR_SCHEMA_PATH,
            VECTOR_BUILDER_PATH,
            Path(__file__).resolve(),
            Q_CAMPAIGN_PATH,
            KV_CAMPAIGN_PATH,
            QUALIFICATION_PATH,
        )
    }
    vector_label = (
        str(vectors_path.relative_to(ROOT))
        if vectors_path.is_relative_to(ROOT)
        else f"external/{vectors_path.name}"
    )
    static_paths[vector_label] = vectors_path
    source_sha256 = {
        name: _sha256_file(path) for name, path in sorted(static_paths.items())
    }
    for name, payload in sorted(program_files.items()):
        source_sha256[f"generated/{name}"] = _sha256(payload.encode("ascii"))

    operations = vectors["composition"]["operations"]
    body: dict[str, Any] = {
        "arithmetic_evidence": {
            "exact_scalar_all_rows": True,
            "kv_projection_campaign_id": KV_CAMPAIGN_ID,
            "q_projection_campaign_id": Q_CAMPAIGN_ID,
            "qkv_qualification_report_id": QUALIFICATION_ID,
            "status": "pass",
        },
        "cases": cases,
        "claim_boundary": {
            "activity_derived_power_or_timing": False,
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_k_head_rmsnorm_graph_operation": True,
            "complete_layer_execution": False,
            "complete_q_head_rmsnorm_graph_operation": True,
            "complete_qkv_preparation": False,
            "dual_simulator_complete_operations": True,
            "exact_scalar_all_rows": True,
            "preloaded_q_and_k_projection_outputs": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "program_correlation": {
            "command_count": 4,
            "command_end": 3_078,
            "command_start": 3_075,
            "dma_hbm_bytes": 512,
            "dma_hbm_request_count": 8,
            "dma_sram_write_count": 32,
            "early_terminal_fail_stop_cases": 1,
            "element_count": 5_120,
            "graph_operation_ids": ["node.0005", "node.0006"],
            "input_read_count": 5_120,
            "normalized_saturation_count": 0,
            "operations": [
                {
                    "inverse_rms_payload_sha256": item[
                        "inverse_rms_payload_sha256"
                    ],
                    "mean_square_payload_sha256": item[
                        "mean_square_payload_sha256"
                    ],
                    "operation_id": item["operation_id"],
                    "output_payload_sha256": item["output_payload_sha256"],
                    "projection": item["projection"],
                    "row_count": item["row_count"],
                }
                for item in operations
            ],
            "output_saturation_count": 0,
            "output_write_count": 5_120,
            "reciprocal_square_root_count": 40,
            "reduction_add_count": 5_080,
            "row_count": 40,
            "weight_read_count": 5_120,
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
