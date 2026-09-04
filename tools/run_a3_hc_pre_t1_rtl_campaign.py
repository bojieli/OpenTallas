#!/usr/bin/env python3
"""Run the focused dual-simulator DeepSeek HC_PRE T=1 RTL campaign.

The campaign regenerates and byte-compares independent exact vectors, executes
the same authenticated checkpoint transaction through current ROM PC15 and HBM
PC14 descriptors on Icarus and pinned Verilator, and asks pinned Yosys to
elaborate/check the synthesizable top.  Controller cycles and host wall time
are verification metadata only; neither is architectural token latency/TPOT.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_pre_t1"
CHECKPOINT_DIR = ROOT / "testdata/rtl/a3_hc_pre_t1_checkpoint"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_hc_pre_t1_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_hc_projection_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_rne.sv",
    "rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_sinkhorn20_rne.sv",
    "rtl/abi3/ot_a3_vector_mhc_pre_tile_scheduler.sv",
    "rtl/abi3/ot_a3_hc_projection_rms_rne.sv",
    "rtl/abi3/ot_a3_hc_coefficients_rne.sv",
    "rtl/abi3/ot_a3_hc_pre_t1_descriptor_rne.sv",
    "rtl/test/tb_a3_hc_pre_t1.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:-1]
ORACLE_SOURCES = (
    "tools/extract_a3_hc_pre_t1_checkpoint.py",
    "tools/build_a3_hc_pre_t1_vectors.py",
    "tools/build_a3_mhc_pre_tile_vectors.py",
    "tools/run_a3_hc_pre_t1_rtl_campaign.py",
    "runtime/reference/formats.py",
    "runtime/reference/hyper_connection.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_weights.u32le",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le",
)
VECTOR_FILES = (
    "meta.hex",
    "fma_cases.hex",
    "expected.hex",
    "rom_config.hex",
    "hbm_config.hex",
    "index.json",
)
CHECKPOINT_FILES = ("hidden.hex", "projection.hex", "base.hex", "scale.hex", "index.json")

SUMMARY_RE = re.compile(r"^HC_PRE_T1_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_hc_pre_t1 checks=(?P<checks>\d+)$")
KV_RE = re.compile(r"(?P<key>[a-z0-9_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def scrub(value: str, temporary: Path | None = None) -> str:
    if temporary is not None:
        value = value.replace(str(temporary), "<TMP>")
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
        output = (exc.stdout or "") + (exc.stderr or "")
        raise RuntimeError(
            f"command timed out after {timeout}s: {scrub(' '.join(command))}\n{output}"
        ) from exc
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
    if process.returncode:
        raise RuntimeError(f"{label} version probe failed: {output}")
    match = pattern.search(output)
    if match is None:
        raise RuntimeError(f"cannot parse {label} version: {output!r}")
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
    if not iverilog_name or not vvp_name:
        raise RuntimeError("Icarus Verilog and vvp are required")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not verilator.is_file():
        raise RuntimeError(f"pinned Verilator is missing: {verilator}")
    if not yosys.is_file():
        raise RuntimeError(f"pinned Yosys is missing: {yosys}")
    return Path(iverilog_name), Path(vvp_name), verilator, yosys


def plusargs() -> list[str]:
    return [
        f"+META={VECTOR_DIR / 'meta.hex'}",
        f"+FMA={VECTOR_DIR / 'fma_cases.hex'}",
        f"+HIDDEN={CHECKPOINT_DIR / 'hidden.hex'}",
        f"+PROJECTION={CHECKPOINT_DIR / 'projection.hex'}",
        f"+BASE={CHECKPOINT_DIR / 'base.hex'}",
        f"+SCALE={CHECKPOINT_DIR / 'scale.hex'}",
        f"+EXPECTED={VECTOR_DIR / 'expected.hex'}",
        f"+ROM_CONFIG={VECTOR_DIR / 'rom_config.hex'}",
        f"+HBM_CONFIG={VECTOR_DIR / 'hbm_config.hex'}",
    ]


def parse_log(log: str) -> tuple[dict[str, int], int]:
    summary: dict[str, int] | None = None
    checks: int | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = SUMMARY_RE.match(line)
        if match:
            summary = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(match.group("body"))
            }
        passed = PASS_RE.match(line)
        if passed:
            checks = int(passed.group("checks"))
    if summary is None or checks is None:
        raise RuntimeError("simulator omitted the exact HC_PRE T=1 summary/PASS marker")
    return summary, checks


def validate_summary(
    summary: dict[str, int], checks: int, manifest: dict[str, Any]
) -> None:
    counts = manifest["fma"]["counts"]
    expected_fixed = {
        "fma_cases": int(counts["total"]),
        "fma_success": int(counts["success"]),
        "fma_argument_errors": int(counts["argument_errors"]),
        "fma_overflow_errors": int(counts["overflow_errors"]),
        "checkpoint_words": 148,
        "parity_words": 24,
        "output_stalls": 17,
        "active_resets": 1,
        "descriptor_errors": 1,
        "arithmetic_errors": 2,
    }
    for key, expected in expected_fixed.items():
        if summary.get(key) != expected:
            raise RuntimeError(f"simulator summary {key}={summary.get(key)} != {expected}")
    if summary.get("atomic_private_checks", 0) < 600_000:
        raise RuntimeError("simulator did not continuously check atomic private outputs")
    if summary.get("rom_cycles") != summary.get("hbm_cycles"):
        raise RuntimeError("ROM/HBM arithmetic execution cycles differ")
    if summary.get("rom_cycles", 0) <= 200_000:
        raise RuntimeError("HC_PRE transaction ended implausibly early")
    if summary.get("coefficient_error_cycles", 0) <= 200_000:
        raise RuntimeError("late coefficient failure did not traverse full projection")
    if checks <= 0:
        raise RuntimeError("simulator reported no checks")


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_hc_pre_t1_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=180,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")

    checkpoint = json.loads((CHECKPOINT_DIR / "index.json").read_text("ascii"))
    body = dict(checkpoint)
    observed_id = body.pop("manifest_id", None)
    expected_id = hashlib.sha256(
        json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("ascii")
    ).hexdigest()
    if observed_id != expected_id:
        raise RuntimeError("retained checkpoint manifest identity is stale")
    for filename in CHECKPOINT_FILES[:-1]:
        record = checkpoint["files"][filename]
        path = CHECKPOINT_DIR / filename
        if path.stat().st_size != record["bytes"] or sha256(path) != record["sha256"]:
            raise RuntimeError(f"retained checkpoint input {filename} is stale")
    return json.loads((generated / "index.json").read_text("ascii"))


def campaign(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(
            iverilog, ["-V"], IVERILOG_RE, (11, 0), "Icarus Verilog"
        ),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }

    with tempfile.TemporaryDirectory(prefix="a3-hc-pre-t1-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_hc_pre_t1",
                "-o",
                str(iverilog_output),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=180,
        )
        iverilog_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus compile failed:\n{iverilog_compile_log}")
        process, iverilog_run_seconds = run(
            [str(vvp), str(iverilog_output), *plusargs()], timeout=3600
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_summary, iverilog_checks = parse_log(iverilog_log)
        validate_summary(iverilog_summary, iverilog_checks, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_hc_pre_t1",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_hc_pre_t1",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                "-Wno-PROCASSINIT",
                "-Wno-UNUSEDSIGNAL",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=600,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim_a3_hc_pre_t1"), *plusargs()], timeout=600
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_summary, verilator_checks = parse_log(verilator_log)
        validate_summary(verilator_summary, verilator_checks, manifest)
        if (iverilog_summary, iverilog_checks) != (
            verilator_summary,
            verilator_checks,
        ):
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_hc_pre_t1_descriptor_rne; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=1200
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / source for source in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_hc_pre_t1_campaign.v1",
            "status": "pass",
            "scope": {
                "exact_bf16_fp32_fp32_fused_rne": True,
                "balanced_16384_element_rms": True,
                "eight_lane_24_row_projection": True,
                "affine_sigmoid_stable_softmax_sinkhorn20_tail": True,
                "authenticated_checkpoint_position_zero": True,
                "checkpoint_token_id": 18_042,
                "all_74_numeric_boundary_words_exact": True,
                "qualified_t512_first_24_output_words_exact": True,
                "current_rom_pc15_descriptor_381_execution": True,
                "current_hbm_pc14_descriptor_545_execution": True,
                "rom_hbm_output_parity": True,
                "busy_input_refusal_and_input_latching": True,
                "active_reset": True,
                "output_backpressure_stability": True,
                "atomic_fail_closed_output": True,
                "late_arithmetic_error_single_completion": True,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "input_or_output_indexed_lookup_table": False,
                "multi_token_hc_pre": False,
                "transformer_layer": False,
                "full_model_execution": False,
                "model_token_generation": False,
                "token_correctness": False,
                "eos": False,
                "technology_mapping_or_timing": False,
                "architectural_timing": False,
                "tpot": False,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "fma_counts": manifest["fma"]["counts"],
            "checkpoint_binding": manifest["checkpoint"],
            "witness": manifest["witness"],
            "descriptor_binding": manifest["descriptors"],
            "checks_per_simulator": iverilog_checks,
            "normalized_summary": iverilog_summary,
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_hc_pre_t1_descriptor_rne",
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no technology mapping, PPA, frequency, architectural token latency, or TPOT claim",
            },
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_simulation": iverilog_run_seconds,
                "verilator_compile": verilator_compile_seconds,
                "verilator_simulation": verilator_run_seconds,
                "yosys_elaboration": yosys_seconds,
            },
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                str(path.relative_to(ROOT)): sha256(path)
                for path in (
                    *(VECTOR_DIR / filename for filename in VECTOR_FILES),
                    *(CHECKPOINT_DIR / filename for filename in CHECKPOINT_FILES),
                )
            },
            "log_sha256": {
                "iverilog_compile": hashlib.sha256(iverilog_compile_log.encode()).hexdigest(),
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
    problems: list[str] = []
    try:
        result = json.loads(path.read_text("ascii"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    if result.get("status") != "pass":
        problems.append("retained campaign status is not pass")
    if result.get("simulators_agree") is not True:
        problems.append("retained campaign lacks simulator agreement")
    scope = result.get("scope", {})
    for forbidden in (
        "multi_token_hc_pre",
        "transformer_layer",
        "full_model_execution",
        "model_token_generation",
        "token_correctness",
        "eos",
        "technology_mapping_or_timing",
        "architectural_timing",
        "tpot",
    ):
        if scope.get(forbidden) is not False:
            problems.append(f"retained campaign overclaims {forbidden}")
    for relative, expected in result.get("source_sha256", {}).items():
        current = ROOT / relative
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"source hash is stale: {relative}")
    for relative, expected in result.get("vector_sha256", {}).items():
        current = ROOT / relative
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"vector hash is stale: {relative}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = validate_retained(args.output.resolve())
        if problems:
            raise SystemExit("\n".join(problems))
        print(f"PASS retained HC_PRE T=1 campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        "PASS A3 HC_PRE T=1 RTL campaign: "
        f"{result['checks_per_simulator']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
