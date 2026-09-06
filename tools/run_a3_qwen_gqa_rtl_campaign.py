#!/usr/bin/env python3
"""Run exact dual-simulator Qwen ABI 3.0 PC38 GQA evidence.

The reported simulator cycles and host wall times are verification cost only.
PC38 is neither a token commit nor TPOT evidence.
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
import tempfile
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/rtl/a3_qwen_gqa"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_qwen_gqa_campaign.json"
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
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_qwen_kv_scatter_adapter.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_qwen_gqa_adapter.sv",
    "rtl/test/tb_a3_qwen_gqa.sv",
)
SYNTH_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
)
ORACLE_SOURCES = (
    "runtime/reference/formats.py",
    "runtime/reference/tensor_accelerator_attention.py",
    "tools/build_a3_qwen_gqa_vectors.py",
    "tools/run_a3_qwen_gqa_rtl_campaign.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json",
    "testdata/compiler/abi3_shipped_prefix/p3_expect.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_writes.hex",
    "results/rtl/abi3_shipped_prefix_campaign.json",
)
VECTOR_FILES = (
    "cases.hex",
    "instruction.hex",
    "operator.hex",
    "view0.hex",
    "view1.hex",
    "view2.hex",
    "view3.hex",
    "output.hex",
    "numeric.hex",
    "source.hex",
    "expected.hex",
    "index.json",
)

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_qwen_gqa cases=(?P<cases>\d+) "
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


def run(command: list[str], *, timeout: int) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
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


def plusargs(vector_root: Path) -> list[str]:
    return [
        f"+CASES={vector_root / 'cases.hex'}",
        f"+INSTRUCTION={vector_root / 'instruction.hex'}",
        f"+OPERATOR={vector_root / 'operator.hex'}",
        f"+VIEW0={vector_root / 'view0.hex'}",
        f"+VIEW1={vector_root / 'view1.hex'}",
        f"+VIEW2={vector_root / 'view2.hex'}",
        f"+VIEW3={vector_root / 'view3.hex'}",
        f"+OUTPUT={vector_root / 'output.hex'}",
        f"+NUMERIC={vector_root / 'numeric.hex'}",
        f"+SOURCE={vector_root / 'source.hex'}",
        f"+EXPECTED={vector_root / 'expected.hex'}",
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
        "writes": "writes",
        "score": "score_multiplies",
        "exp": "exponentials",
        "value": "value_multiplies",
        "executed": "gqa_executed",
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
    # The PASS marker is compared against the vector manifest's own derived
    # expectation, not against a constant pinned here.  A pinned constant has
    # to be edited whenever a case is added, and an edited constant is not
    # evidence; the manifest derives it from the same rule the testbench
    # counts by, so a case that silently stops being checked still fails.
    expected_pass = {
        key: int(value) for key, value in manifest["expected_pass"].items()
    }
    if passed != expected_pass:
        raise RuntimeError(
            f"simulator PASS summary differs: {passed} != {expected_pass}"
        )


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_qwen_gqa_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=120,
    )
    if process.returncode:
        raise RuntimeError(f"vector generation failed:\n{process.stdout}\n{process.stderr}")
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


def aggregate(
    manifest: dict[str, Any], observed: list[dict[str, int]]
) -> dict[str, int]:
    """Sum the observed per-case counters the manifest already predicted.

    Every entry is a sum over the *observed* rows, which validate_observed has
    already proved equal to the manifest's per-case expectation.  Nothing here
    is a constant that a new case could silently leave stale.
    """

    output_words = int(manifest["request"]["output_shape"][1]) * int(
        manifest["request"]["output_shape"][2]
    )
    positive = [item for item in observed if item["writes"] != 0]
    return {
        "case_count": len(observed),
        "positive_case_count": len(positive),
        "negative_case_count": len(observed) - len(positive),
        "contexts_covered": list(manifest["request"]["contexts"]),
        "computed_output_words_compared": sum(
            output_words for _ in positive
        ),
        "atomic_sentinel_words_checked": output_words * (
            len(observed) - len(positive)
        ),
        "memory_reads": sum(item["reads"] for item in observed),
        "score_multiplications": sum(item["score"] for item in observed),
        "exponential_evaluations": sum(item["exp"] for item in observed),
        "value_multiplications": sum(item["value"] for item in observed),
        "rtl_write_beats": sum(item["writes"] for item in observed),
        "checks_per_simulator": int(manifest["expected_pass"]["checks"]),
    }


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_RE, None, "Icarus"),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }
    with tempfile.TemporaryDirectory(prefix="a3-qwen-gqa-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)
        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [str(iverilog), "-g2012", "-s", "tb_a3_qwen_gqa", "-o", str(iverilog_output), *[str(ROOT / source) for source in RTL_SOURCES]],
            timeout=120,
        )
        if process.returncode:
            raise RuntimeError(f"Icarus compile failed:\n{process.stdout}\n{process.stderr}")
        process, iverilog_run_seconds = run(
            [str(vvp), str(iverilog_output), *plusargs(VECTOR_DIR)], timeout=600
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_cases, iverilog_pass = parse_log(iverilog_log)
        validate_observed(iverilog_cases, iverilog_pass, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [str(verilator), "--binary", "--timing", "--top-module", "tb_a3_qwen_gqa", "--Mdir", str(verilator_dir), "-o", "sim", "-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC", *[str(ROOT / source) for source in RTL_SOURCES]],
            timeout=300,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim"), *plusargs(VECTOR_DIR)], timeout=300
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
            + "; hierarchy -check -top ot_a3_qwen_gqa; proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=180
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration failed:\n{yosys_log}")

        source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_qwen_gqa_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "scope": {
                **manifest["claim_boundary"],
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "shared_certifying_exponential": True,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "boundary": {
                "contexts_covered": list(manifest["request"]["contexts"]),
                "previous_first_unsupported_pc": 38,
                "new_first_unsupported_pc": 41,
                "new_first_unsupported_opcode": "TENSOR.MATMUL",
                "rom_operator_descriptor_id": 134,
                "hbm_operator_descriptor_id": 137,
            },
            "aggregate": aggregate(manifest, iverilog_cases),
            "activation_binding": manifest["authentic_current_activations"],
            "history_binding": manifest["history"],
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
                "top": "ot_a3_qwen_gqa",
                "check_problems": 0,
                "note": (
                    "generic synthesizable elaboration only; no library mapping, "
                    "PPA, token latency, output-token correctness, or TPOT claim"
                ),
            },
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                filename: sha256(VECTOR_DIR / filename) for filename in VECTOR_FILES
            },
            "log_sha256": {
                "iverilog": hashlib.sha256(iverilog_log.encode()).hexdigest(),
                "verilator_compile": hashlib.sha256(verilator_compile_log.encode()).hexdigest(),
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
    if value.get("boundary", {}).get("new_first_unsupported_pc") != 41:
        problems.append("next unsupported PC differs")
    if value.get("aggregate", {}).get("computed_output_words_compared") != 16384:
        problems.append("computed-word count differs")
    if value.get("aggregate", {}).get("contexts_covered") != [17, 18, 19]:
        problems.append("governed decode contexts are not all covered")
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
        "Qwen PC38 GQA RTL campaign "
        f"status={result['status']} words={result['aggregate']['computed_output_words_compared']} "
        "next_pc=41"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
