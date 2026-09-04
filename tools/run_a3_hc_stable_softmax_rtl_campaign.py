#!/usr/bin/env python3
"""Run the focused dual-simulator HC stable-softmax RTL campaign.

This campaign regenerates and byte-compares an independent exact vector set,
checks all results and protocol properties on Icarus 11.0 and pinned Verilator
5.050, and performs a modern-Yosys synthesizable-elaboration check.  Simulator
wall time and the deliberately time-multiplexed controller cycles are retained
only as verification metadata; neither is architectural latency or TPOT.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_stable_softmax"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_hc_stable_softmax_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_rne.sv",
    "rtl/test/tb_a3_hc_stable_softmax.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:-1]
ORACLE_SOURCES = (
    "tools/extract_a3_hc_stable_softmax_checkpoint.py",
    "tools/build_a3_hc_stable_softmax_vectors.py",
    "tools/run_a3_hc_stable_softmax_rtl_campaign.py",
    "tools/build_a3_hc_numeric_vectors.py",
    "runtime/reference/hyper_connection.py",
)
GENERATED_VECTOR_FILES = (
    "meta.hex",
    "matrix_input.hex",
    "matrix_expected.hex",
    "index.json",
)
CHECKPOINT_VECTOR_FILES = ("checkpoint_logits.u32le", "checkpoint_logits.json")
VECTOR_FILES = (*CHECKPOINT_VECTOR_FILES, *GENERATED_VECTOR_FILES)

SUMMARY_RE = re.compile(r"^SOFTMAX_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_hc_stable_softmax checks=(?P<checks>\d+)$")
KV_RE = re.compile(r"(?P<key>[a-z0-9_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")
TIMEOUT_CYCLES = 4096


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
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
        raise RuntimeError(
            f"command timed out after {timeout}s: {scrub(' '.join(command))}"
        ) from exc
    return process, time.monotonic() - started


def tool_identity(
    executable: Path,
    arguments: list[str],
    pattern: re.Pattern[str],
    expected: tuple[int, int],
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
    if observed != expected:
        raise RuntimeError(f"{label} version {observed} is not pinned {expected}")
    return {
        "path": scrub(str(executable.resolve())),
        "sha256": sha256(executable.resolve()),
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


def plusargs(vector_root: Path = VECTOR_DIR) -> list[str]:
    return [
        f"+META={vector_root / 'meta.hex'}",
        f"+INPUT={vector_root / 'matrix_input.hex'}",
        f"+EXPECTED={vector_root / 'matrix_expected.hex'}",
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
        raise RuntimeError("simulator log lacks the exact summary/PASS markers")
    return summary, checks


def expected_fixed_summary(manifest: dict[str, Any]) -> dict[str, int]:
    counts = manifest["counts"]
    cases = int(counts["cases"])
    errors = {int(key): int(value) for key, value in counts["errors"].items()}
    stalls = sum(3 if index % 19 == 0 else 1 if index % 7 == 0 else 0 for index in range(cases))
    argument_errors = errors.get(1, 0)
    return {
        "cases": cases,
        "checkpoint": int(counts["checkpoint_cases"]),
        "directed": int(counts["directed_cases"]),
        "success": int(counts["successful_cases"]),
        "errors": int(counts["refused_cases"]),
        "argument_errors": argument_errors,
        "overflow_errors": errors.get(2, 0),
        "checkpoint_words": int(counts["checkpoint_cases"]) * 16,
        "t1_words": 16,
        "busy_refusals": 2 * (cases - argument_errors),
        "stalls": stalls,
        "reset_cycles": 31,
    }


def expected_checks(summary: dict[str, int]) -> int:
    # Four initial checks; 31 active-reset busy checks plus four reset checks;
    # four final count checks.  Atomic-busy checks include both the active-reset
    # and regular-case private-output checks.  Each case has 19 fixed checks,
    # each failure one extra all-zero check, and each stalled cycle four checks.
    return (
        4
        + 31
        + 4
        + 4
        + summary["atomic_busy_checks"]
        + summary["busy_refusals"]
        + 19 * summary["cases"]
        + summary["errors"]
        + 4 * summary["stalls"]
    )


def validate_observed(
    summary: dict[str, int], checks: int, manifest: dict[str, Any]
) -> None:
    fixed = expected_fixed_summary(manifest)
    for key, wanted in fixed.items():
        if summary.get(key) != wanted:
            raise RuntimeError(
                f"simulator summary {key}={summary.get(key)} != expected {wanted}"
            )
    if set(summary) != {
        *fixed,
        "max_cycles",
        "atomic_busy_checks",
    }:
        raise RuntimeError(f"simulator summary fields drifted: {sorted(summary)}")
    if not 0 < summary["max_cycles"] < TIMEOUT_CYCLES:
        raise RuntimeError("stable-softmax controller violated the testbench bound")
    if summary["atomic_busy_checks"] <= 2 * summary["busy_refusals"]:
        raise RuntimeError("atomic private-output checks did not span active execution")
    if summary["atomic_busy_checks"] & 1:
        raise RuntimeError("atomic private-output check count must be even")
    wanted_checks = expected_checks(summary)
    if checks != wanted_checks:
        raise RuntimeError(f"simulator checks {checks} != expected {wanted_checks}")


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_hc_stable_softmax_vectors.py"),
            "--checkpoint",
            str(VECTOR_DIR),
            "--output",
            str(generated),
        ],
        timeout=180,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in GENERATED_VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text(encoding="ascii"))


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

    with tempfile.TemporaryDirectory(prefix="a3-hc-stable-softmax-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_hc_stable_softmax",
                "-o",
                str(iverilog_output),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=120,
        )
        if process.returncode:
            raise RuntimeError(
                f"Icarus compile failed:\n{process.stdout}\n{process.stderr}"
            )
        process, iverilog_run_seconds = run(
            [str(vvp), str(iverilog_output), *plusargs()], timeout=600
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_summary, iverilog_checks = parse_log(iverilog_log)
        validate_observed(iverilog_summary, iverilog_checks, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_hc_stable_softmax",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_hc_stable_softmax",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                "-Wno-PROCASSINIT",
                "-Wno-UNUSEDSIGNAL",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=240,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(
                f"Verilator compile failed:\n{verilator_compile_log}"
            )
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim_a3_hc_stable_softmax"), *plusargs()],
            timeout=180,
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_summary, verilator_checks = parse_log(verilator_log)
        validate_observed(verilator_summary, verilator_checks, manifest)
        if (iverilog_summary, iverilog_checks) != (
            verilator_summary,
            verilator_checks,
        ):
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_hc_stable_softmax_rne; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=180
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_hc_stable_softmax_campaign.v1",
            "status": "pass",
            "scope": {
                "source_major_4x4_stable_softmax": True,
                "exact_frozen_operation_order": True,
                "correctly_rounded_nonpositive_exponential": True,
                "independent_exact_rational_oracle": True,
                "host_floating_point_oracle": False,
                "checkpoint_first_t512_matrices": 512,
                "checkpoint_final_t320_matrices": 320,
                "t1_shape_witness": True,
                "atomic_fail_closed_output": True,
                "input_latching_busy_refusal_and_output_backpressure": True,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "input_or_output_indexed_lookup_table": False,
                "full_200k_checkpoint_domain": False,
                "full_hc_pre": False,
                "sinkhorn_composition": False,
                "pc14_integration": False,
                "model_token_generation": False,
                "eos": False,
                "technology_mapping_or_timing": False,
                "architectural_timing": False,
                "tpot": False,
            },
            "counts": manifest["counts"],
            "coverage": manifest["coverage"],
            "checkpoint_binding": manifest["checkpoint_binding"],
            "checks_per_simulator": iverilog_checks,
            "normalized_summary": iverilog_summary,
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_hc_stable_softmax_rne",
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no library mapping, PPA, frequency, architectural latency, or TPOT claim",
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
    problems: list[str] = []
    try:
        result = json.loads(path.read_text(encoding="ascii"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    if result.get("status") != "pass":
        problems.append("retained campaign status is not pass")
    if result.get("simulators_agree") is not True:
        problems.append("retained campaign lacks simulator agreement")
    scope = result.get("scope", {})
    for forbidden in (
        "full_200k_checkpoint_domain",
        "full_hc_pre",
        "sinkhorn_composition",
        "pc14_integration",
        "model_token_generation",
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
    for filename, expected in result.get("vector_sha256", {}).items():
        current = VECTOR_DIR / filename
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"vector hash is stale: {filename}")
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
        print(f"PASS retained HC stable-softmax campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        "PASS HC stable-softmax RTL campaign: "
        f"{result['counts']['cases']} matrices, "
        f"{result['checks_per_simulator']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
