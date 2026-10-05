#!/usr/bin/env python3
"""Run the focused dual-simulator ABI 3.0 HC numeric RTL campaign.

The campaign regenerates and byte-compares the independent exact vectors,
executes the same synthesizable divider/Sinkhorn RTL with Icarus and pinned
Verilator 5.050, requires identical normalized summaries, and performs a
modern-Yosys synthesizable-elaboration check.  Simulator wall time and the
time-multiplexed controller cycle counts are verification metadata, not an
architectural latency or TPOT result.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_numeric"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_hc_numeric_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv",
    "rtl/test/tb_a3_hc_numeric.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:3]
ORACLE_SOURCES = (
    "tools/build_a3_hc_numeric_vectors.py",
    "tools/run_a3_hc_numeric_rtl_campaign.py",
    "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le",
)
VECTOR_FILES = (
    "meta.hex",
    "division.hex",
    "sinkhorn_input.hex",
    "sinkhorn_expected.hex",
    "index.json",
)

SUMMARY_RE = re.compile(r"^(?P<name>DIV|SINK|RESET)_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_hc_numeric checks=(?P<checks>\d+)$")
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
        raise RuntimeError(
            f"command timed out after {timeout}s: {scrub(' '.join(command))}"
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
    text = (process.stdout + process.stderr).strip()
    if process.returncode:
        raise RuntimeError(f"{label} version probe failed: {text}")
    match = pattern.search(text)
    if match is None:
        raise RuntimeError(f"cannot parse {label} version: {text!r}")
    observed = (int(match.group("major")), int(match.group("minor")))
    if expected is not None and observed != expected:
        raise RuntimeError(f"{label} version {observed} is not pinned {expected}")
    return {
        "path": scrub(str(executable.resolve())),
        "sha256": sha256(executable.resolve()),
        "version": text.splitlines()[0],
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


def plusargs(vector_root: Path) -> list[str]:
    return [
        f"+META={vector_root / 'meta.hex'}",
        f"+DIVISION={vector_root / 'division.hex'}",
        f"+SINK_INPUT={vector_root / 'sinkhorn_input.hex'}",
        f"+SINK_EXPECTED={vector_root / 'sinkhorn_expected.hex'}",
    ]


def parse_log(log: str) -> tuple[dict[str, dict[str, int]], int]:
    summaries: dict[str, dict[str, int]] = {}
    checks: int | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = SUMMARY_RE.match(line)
        if match:
            summaries[match.group("name").lower()] = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(match.group("body"))
            }
        passed = PASS_RE.match(line)
        if passed:
            checks = int(passed.group("checks"))
    if set(summaries) != {"div", "sink", "reset"}:
        raise RuntimeError(f"simulator summaries incomplete: {sorted(summaries)}")
    if checks is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    return summaries, checks


def load_words(path: Path) -> list[int]:
    return [int(line, 16) for line in path.read_text().splitlines() if line]


def expected_summary(manifest: dict[str, Any]) -> tuple[dict[str, dict[str, int]], int]:
    counts = manifest["counts"]
    division = load_words(VECTOR_DIR / "division.hex")
    div_cases = counts["division_cases"]
    qualifying_divisions = sum(
        1
        for index in range(div_cases)
        if division[index * 4 + 3] != 1 and division[index * 4] & 0x7FFFFFFF
    )
    div_backpressure_base = qualifying_divisions * 2
    div_stalls_base = sum(
        (3 if index % 17 == 0 else 1) * 4 for index in range(div_cases)
    )
    div_backpressure = div_backpressure_base + 2  # reset rerun of case two
    div_stalls = div_stalls_base + 4

    sink_cases = counts["sinkhorn_cases"]
    sink_successes = int(counts["sinkhorn_errors"].get("0", 0))
    sink_errors = sink_cases - sink_successes
    sink_stalls_base = sum(
        (3 if index % 11 == 0 else 1) * 18 for index in range(sink_cases)
    )
    sink_stalls = sink_stalls_base + 54
    expected = {
        "div": {
            "cases": div_cases,
            "backpressure": div_backpressure,
            "stalls": div_stalls,
            "max_cycles": 33,
        },
        "sink": {
            "cases": sink_cases,
            "successes": sink_successes + 1,
            "errors": sink_errors,
            "checkpoint_words": 5 * 16,
            "backpressure": (sink_successes + 1) * 2,
            "stalls": sink_stalls,
            "max_cycles": 21374,
        },
        "reset": {"checks": 4},
    }
    # Two initial-ready checks; per-request formulas include the explicit
    # bounded/error/result/consume checks, backpressure checks and stall checks.
    checks = 2
    checks += div_cases * 4 + div_backpressure_base + div_stalls_base
    checks += 4 + 2 + 4  # duplicate divider case after reset
    checks += 2  # divider reset assertions
    checks += sink_cases * 19 + sink_successes * 2 + sink_stalls_base
    checks += 19 + 2 + 54  # duplicate checkpoint Sinkhorn case after reset
    checks += 2  # Sinkhorn reset assertions
    return expected, checks


def regenerate_and_compare(temporary_root: Path) -> dict[str, Any]:
    generated = temporary_root / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_hc_numeric_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=60,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


def validate_observed(
    summaries: dict[str, dict[str, int]],
    checks: int,
    manifest: dict[str, Any],
) -> None:
    expected, expected_checks = expected_summary(manifest)
    if summaries != expected:
        raise RuntimeError(f"simulator summary {summaries} != expected {expected}")
    if checks != expected_checks:
        raise RuntimeError(f"simulator checks {checks} != expected {expected_checks}")


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(
            iverilog, ["-V"], IVERILOG_RE, None, "Icarus Verilog"
        ),
        "vvp": {
            "path": scrub(str(vvp.resolve())),
            "sha256": sha256(vvp.resolve()),
        },
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(
            yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"
        ),
    }

    with tempfile.TemporaryDirectory(prefix="a3-hc-numeric-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb_a3_hc_numeric.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_hc_numeric",
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
            [str(vvp), str(iverilog_output), *plusargs(VECTOR_DIR)], timeout=600
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
                "tb_a3_hc_numeric",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_hc_numeric",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=180,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim_a3_hc_numeric"), *plusargs(VECTOR_DIR)],
            timeout=120,
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_summary, verilator_checks = parse_log(verilator_log)
        validate_observed(verilator_summary, verilator_checks, manifest)
        if iverilog_summary != verilator_summary or iverilog_checks != verilator_checks:
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_hc_sinkhorn20_rne; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=120
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / item for item in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_hc_numeric_campaign.v1",
            "status": "pass",
            "scope": {
                "divider": "all finite signed binary32 operands with RNE and gradual underflow",
                "sinkhorn": "atomic post-stable-softmax 4x4 tail: 20 column and 19 row normalizations",
                "checkpoint_derived_positions": 4,
                "checkpoint_derived_sinkhorn_divisions": manifest["counts"]["checkpoint_sinkhorn_divisions"],
                "independent_fraction_oracle": True,
                "host_floating_point_oracle": False,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "technology_mapping_or_timing": False,
                "full_hc_pre": False,
                "stable_softmax_front_end": False,
                "correctly_rounded_exponential": False,
                "correctly_rounded_sigmoid": False,
                "pc14_integration": False,
                "model_token_generation": False,
                "eos": False,
                "architectural_timing": False,
                "tpot": False,
            },
            "counts": manifest["counts"],
            "checkpoint_binding": manifest["checkpoint_binding"],
            "checks": iverilog_checks,
            "normalized_summary": iverilog_summary,
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_hc_sinkhorn20_rne",
                "processes_after_elaboration": 0,
                "memories_after_elaboration": 0,
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no library mapping, PPA, frequency, latency, or TPOT claim",
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
        result = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot read retained campaign: {exc}"]
    if result.get("status") != "pass":
        problems.append("retained campaign status is not pass")
    if result.get("simulators_agree") is not True:
        problems.append("retained campaign lacks simulator agreement")
    scope = result.get("scope", {})
    for forbidden in ("full_hc_pre", "model_token_generation", "eos", "tpot"):
        if scope.get(forbidden) is not False:
            problems.append(f"retained campaign overclaims {forbidden}")
    for name, expected in result.get("source_sha256", {}).items():
        path_now = ROOT / name
        if not path_now.is_file() or sha256(path_now) != expected:
            problems.append(f"source hash is stale: {name}")
    for name, expected in result.get("vector_sha256", {}).items():
        path_now = VECTOR_DIR / name
        if not path_now.is_file() or sha256(path_now) != expected:
            problems.append(f"vector hash is stale: {name}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = validate_retained(args.output.resolve())
        if problems:
            raise SystemExit("\n".join(problems))
        print(f"PASS retained HC numeric campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        "PASS HC numeric RTL campaign: "
        f"{result['counts']['division_cases']} divisions, "
        f"{result['counts']['sinkhorn_cases']} matrices, "
        f"{result['checks']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
