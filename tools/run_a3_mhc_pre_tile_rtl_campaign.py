#!/usr/bin/env python3
"""Run the focused dual-simulator ABI 3.0 HC_PRE tile campaign.

The campaign rebuilds and byte-compares descriptor-derived vectors, runs the
same standalone scheduler and independent scoreboard in Icarus and pinned
Verilator 5.050, and checks synthesizable elaboration with pinned Yosys 0.68.
Its cycles and wall times are verification costs, never architectural latency
or TPOT.  The scheduler performs no HC_PRE arithmetic or model decoding.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_mhc_pre_tiles"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_mhc_pre_tile_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_vector_mhc_pre_tile_scheduler.sv",
    "rtl/test/tb_a3_mhc_pre_tile_scheduler.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:1]
ORACLE_SOURCES = (
    "tools/build_a3_mhc_pre_tile_vectors.py",
    "tools/run_a3_mhc_pre_tile_rtl_campaign.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_weights.u32le",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le",
)
VECTOR_FILES = ("cases.hex", "index.json")

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
RESET_RE = re.compile(r"^RESET_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_mhc_pre_tile checks=(?P<checks>\d+)$")
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


def plusargs(vector_root: Path) -> list[str]:
    return [f"+CASES={vector_root / 'cases.hex'}"]


def parse_log(log: str) -> tuple[list[dict[str, int]], dict[str, int], int]:
    cases: list[dict[str, int]] = []
    reset: dict[str, int] | None = None
    checks: int | None = None
    for raw in log.splitlines():
        line = raw.strip()
        case_match = CASE_RE.match(line)
        if case_match:
            cases.append(
                {
                    item.group("key"): int(item.group("value"))
                    for item in KV_RE.finditer(case_match.group("body"))
                }
            )
        reset_match = RESET_RE.match(line)
        if reset_match:
            reset = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(reset_match.group("body"))
            }
        passed = PASS_RE.match(line)
        if passed:
            checks = int(passed.group("checks"))
    if reset is None:
        raise RuntimeError("simulator omitted the active-reset summary")
    if checks is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    return cases, reset, checks


def stalls_for_tiles(tile_count: int) -> int:
    accepted = 0
    guard = 0
    stalls = 0
    while accepted < tile_count:
        if guard % 7 != 2 and guard % 13 != 5:
            accepted += 1
        else:
            stalls += 1
        guard += 1
    return stalls


def expected_observation(
    manifest: dict[str, Any],
) -> tuple[list[dict[str, int]], dict[str, int], int]:
    cases: list[dict[str, int]] = []
    total_tiles = 0
    total_stalls = 0
    for index, case in enumerate(manifest["cases"]):
        expected = case["expected"]
        tiles = int(expected["total_tiles"])
        stalls = stalls_for_tiles(tiles) if expected["admitted"] else 0
        cases.append(
            {
                "index": index,
                "admitted": int(expected["admitted"]),
                "error": int(expected["error_code"]),
                "tiles": tiles,
                "projection": int(expected["projection_tiles"]),
                "commit": int(expected["commit_tiles"]),
                "fmas": int(expected["logical_fmas"]),
                "outputs": int(expected["logical_output_words"]),
                "stalls": stalls,
                "cycles": tiles + stalls,
            }
        )
        total_tiles += tiles
        total_stalls += stalls

    reset = {"accepted": 37, "stalls": 9}
    accepted_tile_checks = total_tiles * 11
    valid_cycle_checks = total_tiles + total_stalls
    stall_stability_checks = total_stalls * 16
    terminal_checks = len(cases) * 15
    reset_checks = 37 * 11 + reset["stalls"] * 16 + 4 + 8
    checks = (
        accepted_tile_checks
        + valid_cycle_checks
        + stall_stability_checks
        + terminal_checks
        + reset_checks
    )
    return cases, reset, checks


def validate_observed(
    cases: list[dict[str, int]],
    reset: dict[str, int],
    checks: int,
    manifest: dict[str, Any],
) -> None:
    expected_cases, expected_reset, expected_checks = expected_observation(manifest)
    if cases != expected_cases:
        raise RuntimeError("simulator case summaries differ from the vector manifest")
    if reset != expected_reset:
        raise RuntimeError(f"active-reset summary {reset} != {expected_reset}")
    if checks != expected_checks:
        raise RuntimeError(f"simulator checks {checks} != {expected_checks}")


def regenerate_and_compare(temporary_root: Path) -> dict[str, Any]:
    generated = temporary_root / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_mhc_pre_tile_vectors.py"),
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
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }

    with tempfile.TemporaryDirectory(prefix="a3-mhc-pre-tile-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        iverilog_output = temporary / "tb_a3_mhc_pre_tile.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_mhc_pre_tile_scheduler",
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
            [str(vvp), str(iverilog_output), *plusargs(VECTOR_DIR)], timeout=180
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_cases, iverilog_reset, iverilog_checks = parse_log(iverilog_log)
        validate_observed(iverilog_cases, iverilog_reset, iverilog_checks, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_mhc_pre_tile_scheduler",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_mhc_pre_tile",
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
            [str(verilator_dir / "sim_a3_mhc_pre_tile"), *plusargs(VECTOR_DIR)],
            timeout=120,
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_cases, verilator_reset, verilator_checks = parse_log(verilator_log)
        validate_observed(verilator_cases, verilator_reset, verilator_checks, manifest)
        if (
            iverilog_cases != verilator_cases
            or iverilog_reset != verilator_reset
            or iverilog_checks != verilator_checks
        ):
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_vector_mhc_pre_tile_scheduler; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=180
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / item for item in (*RTL_SOURCES, *ORACLE_SOURCES)]
        positive = [case for case in iverilog_cases if case["admitted"]]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_mhc_pre_tile_campaign.v1",
            "status": "pass",
            "scope": {
                "exact_rom_pc15_descriptor_381_admission": True,
                "exact_hbm_pc14_descriptor_545_admission": True,
                "authenticated_prior_hbm_descriptor_546_semantic_equivalence": True,
                "exact_projection_coordinate_coverage": True,
                "exact_output_coordinate_coverage": True,
                "lossless_ready_valid_backpressure": True,
                "active_reset": True,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "functional_t512_golden_digest_bound": True,
                "full_hc_pre_rtl_arithmetic": False,
                "model_token_generation": False,
                "end_to_end_token_correctness": False,
                "eos": False,
                "architectural_timing": False,
                "tpot": False,
                "technology_mapping_or_timing": False,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "checks": iverilog_checks,
            "normalized_cases": iverilog_cases,
            "active_reset": iverilog_reset,
            "aggregate": {
                "positive_cases": len(positive),
                "negative_cases": len(iverilog_cases) - len(positive),
                "accepted_tiles": sum(case["tiles"] for case in positive),
                "projection_tiles": sum(case["projection"] for case in positive),
                "commit_tiles": sum(case["commit"] for case in positive),
                "deliberate_stall_cycles": sum(case["stalls"] for case in positive),
            },
            "functional_output_binding": manifest["functional_output_binding"],
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_vector_mhc_pre_tile_scheduler",
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no library mapping, PPA, frequency, latency, token-correctness, or TPOT claim",
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
    for forbidden in (
        "full_hc_pre_rtl_arithmetic",
        "model_token_generation",
        "end_to_end_token_correctness",
        "eos",
        "architectural_timing",
        "tpot",
        "technology_mapping_or_timing",
    ):
        if scope.get(forbidden) is not False:
            problems.append(f"retained campaign overclaims {forbidden}")
    for name, expected in result.get("source_sha256", {}).items():
        current = ROOT / name
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"source hash is stale: {name}")
    for name, expected in result.get("vector_sha256", {}).items():
        current = VECTOR_DIR / name
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"vector hash is stale: {name}")
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
        print(f"PASS retained HC_PRE tile campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve())
    print(
        "PASS HC_PRE tile RTL campaign: "
        f"{result['aggregate']['accepted_tiles']} tiles, "
        f"{result['checks']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
