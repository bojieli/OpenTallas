#!/usr/bin/env python3
"""Run exact dual-simulator Qwen ABI 3.0 PC41 RTL evidence.

PC41 is an intermediate attention tensor, not a token commit.  Simulator
cycles and host wall times in this campaign are verification costs only; they
must not be reported as token correctness, EOS, architectural ticks, or TPOT.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_a3_qwen_output_projection_vectors as vectors  # noqa: E402


VECTOR_DIR = ROOT / "testdata/rtl/a3_qwen_output_projection"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_qwen_output_projection_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_descriptor_record_validator.sv",
    "rtl/abi3/ot_a3_qwen_output_projection.sv",
    "rtl/abi3/ot_a3_qwen_output_projection_adapter.sv",
    "rtl/test/tb_a3_qwen_output_projection.sv",
)
SYNTH_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_qwen_output_projection.sv",
)
ORACLE_SOURCES = (
    "runtime/tensor_accelerator/bf16.py",
    "runtime/reference/formats.py",
    "runtime/reference/tensor_accelerator_bf16.py",
    "tools/build_a3_qwen_output_projection_vectors.py",
    "tools/run_a3_qwen_output_projection_rtl_campaign.py",
    "testdata/rtl/a3_qwen_gqa/index.json",
    "testdata/rtl/a3_qwen_gqa/expected.hex",
    "results/rtl/a3_qwen_gqa_campaign.json",
    "results/tensor_accelerator/qwen3_full_model_physical/source/checkpoint.lock.json",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
)
VECTOR_FILES = vectors.VECTOR_FILES

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_qwen_output_projection cases=(?P<cases>\d+) "
    r"positive=(?P<positive>\d+) words=(?P<words>\d+) "
    r"checks=(?P<checks>\d+)$"
)
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(value: str, temporary_root: Path | None = None) -> str:
    if temporary_root is not None:
        value = value.replace(str(temporary_root), "<TMP>")
    return value.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(
    command: list[str], *, timeout: int, cwd: Path = ROOT
) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"command timed out after {timeout}s") from exc
    return process, time.monotonic() - started


def tool_identity(
    executable: Path,
    arguments: list[str],
    pattern: re.Pattern[str],
    expected: tuple[int, int] | None,
    label: str,
) -> dict[str, str]:
    process, _ = run([str(executable), *arguments], timeout=30)
    output = (process.stdout + process.stderr).strip()
    match = pattern.search(output)
    if process.returncode or match is None:
        raise RuntimeError(f"cannot identify {label}: {output}")
    observed = (int(match.group("major")), int(match.group("minor")))
    if expected is not None and observed != expected:
        raise RuntimeError(f"{label} version {observed} is not pinned {expected}")
    resolved = executable.resolve()
    return {
        "path": scrub(str(resolved)),
        "sha256": sha256(resolved),
        "version": output.splitlines()[0],
    }


def resolve_tools() -> tuple[Path, Path, Path, Path]:
    iverilog_name = shutil.which("iverilog")
    vvp_name = shutil.which("vvp")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not iverilog_name or not vvp_name or not verilator.is_file() or not yosys.is_file():
        raise RuntimeError("required pinned RTL tools are unavailable")
    return Path(iverilog_name), Path(vvp_name), verilator, yosys


def plusargs(weight: Path) -> list[str]:
    return [
        f"+CASES={VECTOR_DIR / 'cases.hex'}",
        f"+INSTRUCTION={VECTOR_DIR / 'instruction.hex'}",
        f"+OPERATOR={VECTOR_DIR / 'operator.hex'}",
        f"+VIEW0={VECTOR_DIR / 'view0.hex'}",
        f"+VIEW1={VECTOR_DIR / 'view1.hex'}",
        f"+OUTPUT={VECTOR_DIR / 'output.hex'}",
        f"+NUMERIC={VECTOR_DIR / 'numeric.hex'}",
        f"+INPUT={VECTOR_DIR / 'input.hex'}",
        f"+EXPECTED={VECTOR_DIR / 'expected.hex'}",
        f"+WEIGHT={weight}",
    ]


def parse_log(log: str) -> tuple[list[dict[str, int]], dict[str, int]]:
    cases: list[dict[str, int]] = []
    passed: dict[str, int] | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = CASE_RE.match(line)
        if match:
            cases.append(
                {
                    item.group("key"): int(item.group("value"))
                    for item in KV_RE.finditer(match.group("body"))
                }
            )
        match = PASS_RE.match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if passed is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    return cases, passed


def expected_observation(manifest: dict[str, Any]) -> list[dict[str, int]]:
    keys = {
        "failed": "failed",
        "trap": "trap_class",
        "refusal": "refusal_reason",
        "records": "records_checked",
        "reads": "memory_reads",
        "input": "input_reads",
        "weights": "weight_reads",
        "macs": "macs",
        "writes": "writes",
        "executed": "projection_executed",
    }
    return [
        {
            "index": index,
            **{
                output: int(case["expected"][source])
                for output, source in keys.items()
            },
        }
        for index, case in enumerate(manifest["cases"])
    ]


def validate_observed(
    observed: list[dict[str, int]], passed: dict[str, int], manifest: dict[str, Any]
) -> None:
    normalized = [
        {key: value for key, value in item.items() if key != "verification_cycles"}
        for item in observed
    ]
    if normalized != expected_observation(manifest):
        raise RuntimeError("simulator summaries differ from the vector manifest")
    if passed != {"cases": 6, "positive": 2, "words": 8192, "checks": 24702}:
        raise RuntimeError(f"simulator PASS summary differs: {passed}")


def regenerate_and_stage(temporary: Path) -> tuple[dict[str, Any], Path, dict[str, Any]]:
    generated = temporary / "vectors"
    manifest = vectors.build(generated)
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")

    weight_codes, weight_source = vectors.read_weight()
    staged = temporary / "o_proj.weight.bin"
    staged.write_bytes(np.ascontiguousarray(weight_codes, dtype="<u2").tobytes())
    if staged.stat().st_size != 2 * vectors.WEIGHT_READS:
        raise RuntimeError("staged checkpoint weight has the wrong size")
    if sha256(staged) != vectors.EXPECTED_WEIGHT_SHA256:
        raise RuntimeError("staged checkpoint weight has the wrong digest")
    return manifest, staged, weight_source


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_RE, None, "Icarus"),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }
    with tempfile.TemporaryDirectory(prefix="a3-qwen-output-projection-") as name:
        temporary = Path(name)
        manifest, staged_weight, weight_source = regenerate_and_stage(temporary)

        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog), "-g2012", "-s", "tb_a3_qwen_output_projection",
                "-o", str(iverilog_output),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=120,
        )
        if process.returncode:
            raise RuntimeError(f"Icarus compile failed:\n{process.stdout}\n{process.stderr}")
        process, iverilog_run_seconds = run(
            [str(vvp), str(iverilog_output), *plusargs(staged_weight)], timeout=9000
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_cases, iverilog_pass = parse_log(iverilog_log)
        validate_observed(iverilog_cases, iverilog_pass, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator), "--binary", "--timing",
                "--top-module", "tb_a3_qwen_output_projection",
                "--Mdir", str(verilator_dir), "-o", "sim", "-Wno-fatal",
                "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC", "-Wno-LITENDIAN",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=600,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim"), *plusargs(staged_weight)], timeout=1200
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_cases, verilator_pass = parse_log(verilator_log)
        validate_observed(verilator_cases, verilator_pass, manifest)
        if iverilog_cases != verilator_cases or iverilog_pass != verilator_pass:
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_qwen_output_projection; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=300
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration failed:\n{yosys_log}")

        source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_qwen_output_projection_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "scope": {
                **manifest["claim_boundary"],
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "simulator_cycles_are_verification_cost_only": True,
                "release_gate_1_exact_tokens_through_eos_closed": False,
                "release_gate_2_tpot_from_same_token_execution_closed": False,
            },
            "boundary": {
                "previous_first_unsupported_pc": 41,
                "completed_pc": 41,
                "completed_opcode": "TENSOR.MATMUL",
                "new_first_unsupported_pc": 44,
                "new_first_unsupported_opcode": "VECTOR.ADD",
                "rom_operator_descriptor_id": 134,
                "hbm_operator_descriptor_id": 137,
            },
            "aggregate": {
                "case_count": 6,
                "positive_case_count": 2,
                "negative_case_count": 4,
                "computed_output_words_compared": 8192,
                "atomic_sentinel_words_checked": 16384,
                "memory_reads": 50343936,
                "input_reads": 12288,
                "checkpoint_weight_reads": 50331648,
                "multiply_adds": 50331648,
                "rtl_write_beats": 8192,
                "checks_per_simulator": 24702,
            },
            "input_binding": manifest["input"],
            "checkpoint_weight": {
                **weight_source,
                "staged_bytes": staged_weight.stat().st_size,
                "staged_sha256": sha256(staged_weight),
                "staged_copy_retained": False,
            },
            "oracle": manifest["oracle"],
            "normalized_cases": iverilog_cases,
            "simulators_agree": True,
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_simulation": iverilog_run_seconds,
                "verilator_compile": verilator_compile_seconds,
                "verilator_simulation": verilator_run_seconds,
                "yosys_elaboration": yosys_seconds,
            },
            "synthesis_frontend": {
                "top": "ot_a3_qwen_output_projection",
                "check_problems": 0,
                "note": (
                    "generic synthesizable elaboration only; no library mapping, "
                    "PPA, token latency, output-token correctness, or TPOT claim"
                ),
            },
            "release_gate_order": [
                "exact legitimate model output tokens through EOS",
                (
                    "TPOT from architectural token-commit ticks in that same "
                    "passing execution using characterized SKY130/ASAP7 timing"
                ),
            ],
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                filename: sha256(VECTOR_DIR / filename) for filename in VECTOR_FILES
            },
            "log_sha256": {
                "iverilog": hashlib.sha256(iverilog_log.encode()).hexdigest(),
                "verilator_compile": hashlib.sha256(
                    verilator_compile_log.encode()
                ).hexdigest(),
                "verilator": hashlib.sha256(verilator_log.encode()).hexdigest(),
                "yosys": hashlib.sha256(yosys_log.encode()).hexdigest(),
            },
        }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def validate_retained(path: Path = DEFAULT_OUTPUT) -> list[str]:
    if not path.is_file():
        return [f"missing retained campaign: {path}"]
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    problems: list[str] = []
    if value.get("status") != "pass":
        problems.append("campaign status differs")
    if value.get("boundary", {}).get("new_first_unsupported_pc") != 44:
        problems.append("next unsupported PC differs")
    if value.get("aggregate", {}).get("computed_output_words_compared") != 8192:
        problems.append("computed-word count differs")
    for source, expected in value.get("source_sha256", {}).items():
        candidate = ROOT / source
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"source drift: {source}")
    for filename, expected in value.get("vector_sha256", {}).items():
        candidate = VECTOR_DIR / filename
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"vector drift: {filename}")
    return problems


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def main() -> int:
    args = parser().parse_args()
    result = campaign(args.output)
    print(
        "Qwen PC41 output-projection RTL campaign "
        f"status={result['status']} "
        f"words={result['aggregate']['computed_output_words_compared']} "
        "next_pc=44"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
