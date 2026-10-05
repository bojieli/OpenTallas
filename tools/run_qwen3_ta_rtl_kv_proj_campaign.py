#!/usr/bin/env python3
"""Run dual-simulator complete Qwen K/V projection RTL evidence."""

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


SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_kv_proj_campaign.v1"
VECTOR_SCHEMA = "opentallas.tensor_accelerator.qwen_rtl_kv_proj_vectors.v1"
VECTOR_ID = "ee711ae0b31985d0215b9f0c14233c3a2cb0cade3f79809bfc00493d369d5873"
PRIOR_CAMPAIGN_ID = (
    "af8c787f6c6995527ca0b75ab813b06f9ed05f9c18066ccf3e05ea1fa4d69603"
)
PRIOR_VECTOR_ID = "32dbdaa446fc4192f31a0a26394e04094e74c6459858d8a6b0135c11fc9e324b"
SHARD_SHA256 = "656958bc279d27f01126b855c25daeddc42f37f69445e97c2df432cee6dffb37"
WEIGHT_SHA256 = "a7d864dfda7e9659bcf297728eed39ce59aa85b09d40c1f63e638dc45fc8a10c"
WEIGHT_BYTES = 16_777_216

RTL_PATHS = (
    ROOT / "rtl/ot_fp32_rne_pkg.sv",
    ROOT / "rtl/ot_ta_command_decoder.sv",
    ROOT / "rtl/ot_ta_dma_hbm_to_sram.sv",
    ROOT / "rtl/ot_ta_matmul_bf16_sram_engine.sv",
    ROOT / "rtl/ot_ta_dma_matmul_sequencer.sv",
)
PROGRAM_TB = ROOT / "rtl/test/tb_qwen_ta_kv_proj.sv"
PROGRAM_HARNESS = ROOT / "rtl/test/qwen_ta_kv_proj_harness.cpp"
CAMPAIGN_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_kv_proj_campaign_v1.schema.json"
)
VECTOR_SCHEMA_PATH = (
    ROOT
    / "schemas/compiler/tensor_accelerator/qwen_rtl_kv_proj_vectors_v1.schema.json"
)
VECTOR_BUILDER_PATH = ROOT / "tools/build_qwen3_ta_rtl_kv_proj_vectors.py"
PRIOR_CAMPAIGN_PATH = (
    ROOT / "results/tensor_accelerator/qwen3_rtl_q_proj_campaign.json"
)

OBSERVATION_RE = re.compile(
    r"cycles=(?P<cycles>[0-9]+) "
    r"request_stalls=(?P<request_stalls>[0-9]+) "
    r"read_stalls=(?P<read_stalls>[0-9]+) "
    r"write_stalls=(?P<write_stalls>[0-9]+)"
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run Icarus and Verilator over complete Qwen K/V RTL"
    )
    result.add_argument("--vectors", required=True, type=Path)
    result.add_argument("--hbm-shard", required=True, type=Path)
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
        run_code, run_log = _run(run_command, cwd=build, timeout=7200)
    else:
        run_code, run_log = None, ""
    retained_compile = _normalize(compile_log, build=build)
    retained_run = _normalize(run_log, build=build)
    complete_log = retained_compile + retained_run
    observation_match = OBSERVATION_RE.search(retained_run)
    observation = (
        {key: int(value) for key, value in observation_match.groupdict().items()}
        if observation_match is not None
        else None
    )
    passed = (
        compile_code == 0
        and run_code == 0
        and marker in retained_run
        and observation is not None
    )
    return {
        "command": _normalize(
            shlex.join(compile_command) + " && " + shlex.join(run_command),
            build=build,
        ),
        "compile_log": retained_compile,
        "compile_returncode": compile_code,
        "log_sha256": _sha256(complete_log.encode("utf-8")),
        "name": name,
        "observation": observation,
        "run_log": retained_run,
        "run_returncode": run_code,
        "status": "pass" if passed else "fail",
    }


def _program_files(vectors: dict[str, Any]) -> dict[str, str]:
    return {
        "kv_proj_accumulators.hex": "".join(
            f"{value:08x}\n"
            for tile in vectors["expected_accumulator_tiles"]
            for value in tile
        ),
        "kv_proj_commands.hex": "".join(
            f"{command['record_hex']}\n" for command in vectors["commands"]
        ),
        "kv_proj_input.hex": "".join(
            f"{value:04x}\n" for value in vectors["input_codes"]
        ),
        "kv_proj_output.hex": "".join(
            f"{value:04x}\n" for value in vectors["expected_output_codes"]
        ),
    }


def _stage_weight_slice(shard: Path, destination: Path, vectors: dict[str, Any]) -> str:
    shard_record = vectors["hbm_shard"]
    if (
        shard.name != Path(shard_record["path"]).name
        or shard.stat().st_size != shard_record["size_bytes"]
        or _sha256_file(shard) != SHARD_SHA256
    ):
        raise ValueError("immutable Qwen HBM shard differs")
    digest = hashlib.sha256()
    remaining = shard_record["slice_size_bytes"]
    with shard.open("rb") as source, destination.open("xb") as output:
        source.seek(shard_record["slice_offset_bytes"])
        while remaining:
            chunk = source.read(min(1024 * 1024, remaining))
            if not chunk:
                raise ValueError("Qwen K/V projection weight slice is truncated")
            output.write(chunk)
            digest.update(chunk)
            remaining -= len(chunk)
        output.flush()
        os.fsync(output.fileno())
    observed = digest.hexdigest()
    if destination.stat().st_size != WEIGHT_BYTES or observed != WEIGHT_SHA256:
        raise ValueError("Qwen K/V projection weight slice identity differs")
    return observed


def run(vectors_path: Path, hbm_shard_path: Path) -> dict[str, Any]:
    vectors_path = Path(vectors_path).resolve()
    hbm_shard_path = Path(hbm_shard_path).resolve()
    vectors = load_strict_json(vectors_path)
    vector_schema = load_strict_json(VECTOR_SCHEMA_PATH)
    Draft202012Validator.check_schema(vector_schema)
    Draft202012Validator(vector_schema).validate(vectors)
    if (
        vectors.get("schema") != VECTOR_SCHEMA
        or vectors.get("vector_set_id") != VECTOR_ID
        or vectors.get("vector_set_id") != _body_id(vectors, "vector_set_id")
    ):
        raise ValueError("complete K/V projection vector identity differs")
    prior = load_strict_json(PRIOR_CAMPAIGN_PATH)
    if (
        prior.get("campaign_id") != PRIOR_CAMPAIGN_ID
        or prior.get("status") != "pass"
        or prior.get("vector_set_id") != PRIOR_VECTOR_ID
        or prior.get("campaign_id") != _body_id(prior, "campaign_id")
    ):
        raise ValueError("complete Q projection RTL campaign differs")

    program_files = _program_files(vectors)
    marker = (
        "PASS: complete Qwen K/V projections RTL commands=1024 blocks=32 "
        "tiles=512 inputs=131072 weights=8388608 accumulators=32768 "
        "bf16=2048 faults=1"
    )

    with tempfile.TemporaryDirectory(prefix="opentallas-qwen-kv-proj-") as raw:
        build = Path(raw)
        for name, payload in program_files.items():
            (build / name).write_text(payload, encoding="ascii")
        weight_hash = _stage_weight_slice(
            hbm_shard_path, build / "kv_proj_weights.bin", vectors
        )

        iverilog_compile = [
            "iverilog",
            "-g2012",
            "-s",
            "tb_qwen_ta_kv_proj",
            "-o",
            str(build / "kv_proj_simv"),
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
            "ot_ta_dma_matmul_sequencer",
            "-GFIRST_COMMAND_INDEX=2051",
            "-GLAST_COMMAND_INDEX=3074",
            "-GKERNEL0_INDEX=3",
            "-GKERNEL0_LAST_COMMAND_INDEX=2562",
            "-GKERNEL1_INDEX=4",
            "-GKERNEL1_LAST_COMMAND_INDEX=3074",
            "-GKERNEL2_INDEX=4",
            "-GKERNEL2_LAST_COMMAND_INDEX=3074",
            "--Mdir",
            str(build / "obj_kv_proj"),
            *(str(path) for path in RTL_PATHS),
            str(PROGRAM_HARNESS),
        ]
        cases = [
            _case(
                "kv_proj_iverilog",
                iverilog_compile,
                ["vvp", str(build / "kv_proj_simv")],
                build=build,
                marker=marker,
            ),
            _case(
                "kv_proj_verilator",
                verilator_compile,
                [str(build / "obj_kv_proj/Vot_ta_dma_matmul_sequencer")],
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
            PRIOR_CAMPAIGN_PATH,
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
    source_sha256["generated/kv_proj_weights.bin"] = weight_hash

    composition = vectors["composition"]
    body: dict[str, Any] = {
        "arithmetic_evidence": {
            "q_projection_campaign_id": PRIOR_CAMPAIGN_ID,
            "q_projection_vector_set_id": PRIOR_VECTOR_ID,
            "signed_fp32_add_differential_cases": 20_000,
            "status": "pass",
        },
        "build_id": vectors["build_id"],
        "cases": cases,
        "claim_boundary": {
            "activity_derived_power_or_timing": False,
            "architectural_simulator_output_correlated": True,
            "authentic_command_records": True,
            "behavioral_hbm_and_sram": True,
            "complete_k_projection_graph_operation": True,
            "complete_layer_execution": False,
            "complete_qkv_preparation": False,
            "complete_v_projection_graph_operation": True,
            "dual_simulator_complete_operations": True,
            "independent_reference_all_operations_exact": True,
            "preloaded_attention_norm_row": True,
            "program_order_and_fail_stop": True,
            "qualified_hbm_phy": False,
            "qualified_sram_macro": False,
            "raw_weight_payload_retained": False,
            "ta_rtl_6_closed": False,
        },
        "command_program_sha256": vectors["command_program_sha256"],
        "program_correlation": {
            "accumulator_payload_sha256": composition[
                "accumulator_payload_sha256"
            ],
            "accumulator_read_count": 61_440,
            "accumulator_write_count": 32_768,
            "all_accumulator_tiles_sha256": composition[
                "all_accumulator_tiles_sha256"
            ],
            "auxiliary_payload_sha256": composition[
                "combined_output_payload_sha256"
            ],
            "auxiliary_saturation_count": composition[
                "auxiliary_saturation_count"
            ],
            "auxiliary_write_count": 2_048,
            "command_count": 1_024,
            "command_end": 3_074,
            "command_start": 2_051,
            "dma_hbm_bytes": WEIGHT_BYTES,
            "dma_hbm_request_count": 262_144,
            "dma_sram_write_count": 1_048_576,
            "early_terminal_fail_stop_cases": 1,
            "graph_operation_ids": composition["graph_operation_ids"],
            "input_payload_sha256": composition["input_payload_sha256"],
            "matmul_add_count": 8_388_608,
            "matmul_input_read_count": 131_072,
            "matmul_multiply_count": 8_388_608,
            "matmul_weight_read_count": 8_388_608,
            "output_block_count": 32,
            "projection_outputs": [
                {
                    "operation_id": item["operation_id"],
                    "output_payload_sha256": item["output_payload_sha256"],
                    "projection": item["projection"],
                }
                for item in composition["projections"]
            ],
            "weight_payload_sha256": composition[
                "combined_weight_payload_sha256"
            ],
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
    campaign = run(arguments.vectors, arguments.hbm_shard)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_json_bytes(campaign))
        handle.flush()
        os.fsync(handle.fileno())
    print(campaign["campaign_id"])
    return 0 if campaign["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
