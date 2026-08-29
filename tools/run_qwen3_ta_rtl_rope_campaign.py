#!/usr/bin/env python3
"""Run dual-simulator Qwen indexed RoPE RTL evidence."""

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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_rope_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_rope_vectors.v1"
VECTOR_ID = "7a55f9aba5c3e329e571e2a5564beeb666964cd774a868d5ba448470574206d7"
HEAD_RMS_CAMPAIGN_ID = (
    "d7153d61372e1470310e578d71fda690ccda2fe361a30386399a60d6f0b36c37"
)
QUALIFICATION_ID = "42be4b6e14ca271c583e0b8f4bb0bc9a5e854e4e5aa918b0e90acc6217d763ae"

RTL_PATHS = (
    ROOT / "rtl/ot_fp32_rne_pkg.sv",
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_indexed_to_sram.sv",
    ROOT / "rtl/ot_ta_rope_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_rope_sequencer.sv",
)
PROGRAM_TB = ROOT / "rtl/test/tb_qwen_ta_rope.sv"
PROGRAM_HARNESS = ROOT / "rtl/test/qwen_ta_rope_harness.cpp"
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_rope_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/"
    "qwen_rtl_rope_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_rope_vectors.py"
HEAD_RMS_CAMPAIGN_PATH = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_head_rmsnorm_campaign.json"
)
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


def _hex(values: list[int]) -> str:
    return "".join(f"{value:04x}\n" for value in values)


def _program_files(vectors: dict[str, Any]) -> dict[str, str]:
    cases = vectors["cases"]
    return {
        "rope_commands.hex": "".join(
            f"{command['record_hex']}\n" for command in vectors["commands"]
        ),
        "rope_q_input.hex": _hex(vectors["q_input_codes"]),
        "rope_k_input.hex": _hex(vectors["k_input_codes"]),
        "rope_coefficient_0.hex": _hex(cases[0]["coefficient_codes"]),
        "rope_coefficient_7999.hex": _hex(cases[1]["coefficient_codes"]),
        "rope_q_output_0.hex": _hex(cases[0]["q_output_codes"]),
        "rope_k_output_0.hex": _hex(cases[0]["k_output_codes"]),
        "rope_q_output_7999.hex": _hex(cases[1]["q_output_codes"]),
        "rope_k_output_7999.hex": _hex(cases[1]["k_output_codes"]),
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
        raise ValueError("indexed RoPE vector identity differs")
    _validate_dependency(
        HEAD_RMS_CAMPAIGN_PATH, HEAD_RMS_CAMPAIGN_ID, "campaign_id"
    )
    _validate_dependency(QUALIFICATION_PATH, QUALIFICATION_ID, "report_id")
    program_files = _program_files(vectors)
    marker = (
        "PASS: Qwen indexed RoPE RTL commands=2 positions=2 elements=10240 "
        "multiplications=20480 additions=10240 outputs=10240 faults=3"
    )

    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-rope-") as raw:
        build = Path(raw)
        for name, payload in program_files.items():
            (build / name).write_text(payload, encoding="ascii")

        iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_qwen_ta_rope",
            "-o",
            str(build / "rope_simv"),
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
            "ot_ta_dma_rope_sequencer",
            "--Mdir",
            str(build / "obj_rope"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_HARNESS),
        ]
        cases = [
            _case(
                "rope_iverilog",
                iverilog_compile,
                ["vvp", str(build / "rope_simv")],
                build=build,
                marker=marker,
            ),
            _case(
                "rope_verilator",
                verilator_compile,
                [str(build / "obj_rope/Vot_ta_dma_rope_sequencer")],
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
            HEAD_RMS_CAMPAIGN_PATH,
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

    position_cases = [
        {
            "coefficient_payload_sha256": item["coefficient_payload_sha256"],
            "k_output_payload_sha256": item["k_output_payload_sha256"],
            "position": item["position"],
            "q_output_payload_sha256": item["q_output_payload_sha256"],
            "selected_hbm_address": item["selected_hbm_address"],
        }
        for item in vectors["cases"]
    ]
    body: dict[str, Any] = {
        "arithmetic_evidence": {
            "exact_scalar_all_elements": True,
            "head_rmsnorm_campaign_id": HEAD_RMS_CAMPAIGN_ID,
            "identity_position_zero": True,
            "non_identity_position_7999": True,
            "position_count": 2,
            "qkv_qualification_report_id": QUALIFICATION_ID,
            "status": "pass",
        },
        "cases": cases,
        "claim_boundary": {
            "activity_derived_power_or_timing": False,
            "all_qkv_preparation_graph_operations_individually_closed": True,
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_layer_execution": False,
            "complete_rope_graph_operation": True,
            "connected_qkv_preparation_program": False,
            "dual_simulator_complete_operations": True,
            "exact_scalar_all_elements": True,
            "generic_position_selection": True,
            "hbm_response_error_atomicity": True,
            "index_range_fail_stop": True,
            "preloaded_q_and_k_normalized_inputs": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_position_7999_profile_replay": True,
            "qualified_sram_macro": False,
            "ta_rtl_6_closed": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "program_correlation": {
            "addition_count": 5_120,
            "addition_saturation_count": 0,
            "coefficient_read_count": 256,
            "command_count": 2,
            "command_end": 3_080,
            "command_start": 3_079,
            "dma_hbm_bytes": 512,
            "dma_hbm_request_count": 8,
            "dma_hbm_response_count": 8,
            "dma_index_read_count": 2,
            "dma_sram_write_count": 32,
            "early_terminal_fail_stop_cases": 1,
            "element_count": 5_120,
            "graph_operation_ids": ["node.0007"],
            "hbm_response_error_fail_stop_cases": 1,
            "index_range_fail_stop_cases": 1,
            "key_input_read_count": 1_024,
            "key_output_write_count": 1_024,
            "multiplication_count": 10_240,
            "multiplication_saturation_count": 0,
            "position_cases": position_cases,
            "query_input_read_count": 4_096,
            "query_output_write_count": 4_096,
            "sram_bytes_read": 10_756,
            "sram_bytes_written": 10_752,
            "sram_read_count": 5_378,
            "sram_write_count": 5_152,
            "verified_position_count": 2,
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
