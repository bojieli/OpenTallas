#!/usr/bin/env python3
"""Run the focused dual-simulator HC softmax/Sinkhorn composition campaign.

The exact vector set is regenerated and byte-compared before the same shards
run on Icarus 11.0 and pinned Verilator 5.050.  Sharding only reduces host
verification time; each matrix is still one uninterrupted RTL transaction.
Pinned Yosys 0.68 checks synthesizable elaboration of the composed top.

All controller cycles and host wall times are verification metadata.  They are
not a target schedule, model-token latency, technology result, or TPOT.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_softmax_sinkhorn20"
INPUT_VECTOR_DIR = ROOT / "testdata/rtl/a3_hc_stable_softmax"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_hc_softmax_sinkhorn20_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
DEFAULT_SHARDS = 16
TIMEOUT_CYCLES = 32_768
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_rne.sv",
    # The composed block instantiates the PIPELINED twin, so both are here: the
    # twin because it is what runs, and the original because the twin's claim is
    # bit-exactness against it and its source belongs in the digest set.
    "rtl/abi3/ot_a3_hc_sinkhorn20_rne.sv",
    "rtl/abi3/ot_a3_fp32_div_rne_pipe.sv",
    "rtl/abi3/ot_a3_hc_sinkhorn20_rne_pipe.sv",
    "rtl/abi3/ot_a3_hc_stable_softmax_sinkhorn20_rne.sv",
    "rtl/test/tb_a3_hc_softmax_sinkhorn20.sv",
)
SYNTH_SOURCES = RTL_SOURCES[:-1]
ORACLE_SOURCES = (
    "tools/build_a3_hc_softmax_sinkhorn20_vectors.py",
    "tools/run_a3_hc_softmax_sinkhorn20_rtl_campaign.py",
    "tools/build_a3_hc_stable_softmax_vectors.py",
    "tools/build_a3_hc_numeric_vectors.py",
    "runtime/reference/hyper_connection.py",
    "testdata/rtl/a3_hc_stable_softmax/checkpoint_logits.json",
    "testdata/rtl/a3_hc_stable_softmax/checkpoint_logits.u32le",
    "testdata/rtl/a3_hc_stable_softmax/index.json",
    "testdata/rtl/a3_hc_stable_softmax/matrix_input.hex",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "results/abi3/rom_schedule_checks.json",
    "results/abi3/hbm_deepseek_deployment_certificate.json",
    "results/abi3/deepseek_hbm_hc_pre_t512_functional_qualification.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/qualification_vector.json",
    "testdata/runtime/deepseek_hbm_hc_pre_t512/expected_pc14_combination.u32le",
)
GENERATED_VECTOR_FILES = ("meta.hex", "matrix_expected.hex", "index.json")
VECTOR_FILES = GENERATED_VECTOR_FILES

SUMMARY_RE = re.compile(r"^COMPOSE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(r"^PASS a3_hc_softmax_sinkhorn20 checks=(?P<checks>\d+)$")
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


def plusargs(start: int, count: int) -> list[str]:
    return [
        f"+META={VECTOR_DIR / 'meta.hex'}",
        f"+INPUT={INPUT_VECTOR_DIR / 'matrix_input.hex'}",
        f"+EXPECTED={VECTOR_DIR / 'matrix_expected.hex'}",
        f"+START_CASE={start}",
        f"+CASE_COUNT={count}",
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


def load_errors() -> list[int]:
    words = [
        int(line, 16)
        for line in (VECTOR_DIR / "matrix_expected.hex").read_text().splitlines()
        if line
    ]
    if len(words) % 17:
        raise RuntimeError("composed expected-vector image is not 17-word aligned")
    return [words[index + 16] for index in range(0, len(words), 17)]


def shard_ranges(case_count: int, shard_count: int) -> list[tuple[int, int]]:
    shard_count = max(1, min(shard_count, case_count))
    quotient, remainder = divmod(case_count, shard_count)
    result: list[tuple[int, int]] = []
    start = 0
    for shard in range(shard_count):
        count = quotient + int(shard < remainder)
        result.append((start, count))
        start += count
    if start != case_count:
        raise RuntimeError("shard partition did not cover every case")
    return result


def stalls_for_range(start: int, count: int) -> int:
    return sum(
        3 if index % 19 == 0 else 1 if index % 7 == 0 else 0
        for index in range(start, start + count)
    )


def validate_shard(
    summary: dict[str, int],
    checks: int,
    start: int,
    count: int,
    manifest: dict[str, Any],
    errors: list[int],
) -> None:
    checkpoint_total = int(manifest["counts"]["checkpoint_cases"])
    selected_errors = errors[start : start + count]
    checkpoint_cases = max(0, min(start + count, checkpoint_total) - start)
    wanted = {
        "start": start,
        "cases": count,
        "checkpoint": checkpoint_cases,
        "directed": count - checkpoint_cases,
        "success": sum(error == 0 for error in selected_errors),
        "errors": sum(error != 0 for error in selected_errors),
        "argument_errors": selected_errors.count(1),
        "overflow_errors": selected_errors.count(2),
        "checkpoint_words": checkpoint_cases * 16,
        "t1_words": 16 if start == 0 else 0,
        "sinkhorn_entries": sum(error == 0 for error in selected_errors),
        "stalls": stalls_for_range(start, count),
        "reset_cycles": 31 if start == 0 else 0,
        "active_resets": 1 if start == 0 else 0,
    }
    expected_fields = {*wanted, "max_cycles", "busy_atomic_checks"}
    if set(summary) != expected_fields:
        raise RuntimeError(f"simulator summary fields drifted: {sorted(summary)}")
    for key, expected in wanted.items():
        if summary[key] != expected:
            raise RuntimeError(
                f"shard {start}+{count} {key}={summary[key]} != {expected}"
            )
    if not 0 < summary["max_cycles"] < TIMEOUT_CYCLES:
        raise RuntimeError(f"shard {start}+{count} violated the controller bound")
    if summary["busy_atomic_checks"] < summary["cases"]:
        raise RuntimeError(f"shard {start}+{count} lacks active atomicity checks")
    expected_checks = (
        4
        + (4 if start == 0 else 0)
        + summary["busy_atomic_checks"]
        + 23 * count
        + summary["errors"]
        + 4 * summary["stalls"]
    )
    if checks != expected_checks:
        raise RuntimeError(
            f"shard {start}+{count} checks={checks} != {expected_checks}"
        )


def execute_shards(
    executable: list[str],
    ranges: list[tuple[int, int]],
    manifest: dict[str, Any],
    errors: list[int],
    *,
    timeout: int,
) -> tuple[list[dict[str, Any]], float]:
    started = time.monotonic()

    def one(entry: tuple[int, int]) -> dict[str, Any]:
        start, count = entry
        process, seconds = run(
            [*executable, *plusargs(start, count)], timeout=timeout
        )
        log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(
                f"simulation shard {start}+{count} failed:\n{log}"
            )
        summary, checks = parse_log(log)
        validate_shard(summary, checks, start, count, manifest, errors)
        return {
            "start": start,
            "count": count,
            "checks": checks,
            "summary": summary,
            "wall_seconds": seconds,
            "log_sha256": hashlib.sha256(log.encode()).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=len(ranges)) as executor:
        records = list(executor.map(one, ranges))
    return records, time.monotonic() - started


def aggregate(records: list[dict[str, Any]]) -> tuple[dict[str, int], int]:
    additive = (
        "cases",
        "checkpoint",
        "directed",
        "success",
        "errors",
        "argument_errors",
        "overflow_errors",
        "checkpoint_words",
        "t1_words",
        "sinkhorn_entries",
        "stalls",
        "reset_cycles",
        "active_resets",
        "busy_atomic_checks",
    )
    summary = {
        key: sum(record["summary"][key] for record in records) for key in additive
    }
    summary["max_cycles"] = max(
        record["summary"]["max_cycles"] for record in records
    )
    return summary, sum(int(record["checks"]) for record in records)


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_hc_softmax_sinkhorn20_vectors.py"),
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


def campaign(
    output: Path = DEFAULT_OUTPUT, *, shard_count: int = DEFAULT_SHARDS
) -> dict[str, Any]:
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

    with tempfile.TemporaryDirectory(prefix="a3-hc-softmax-sinkhorn20-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)
        errors = load_errors()
        if len(errors) != int(manifest["counts"]["cases"]):
            raise RuntimeError("manifest and expected image case counts differ")
        ranges = shard_ranges(len(errors), shard_count)

        iverilog_output = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                "tb_a3_hc_softmax_sinkhorn20",
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
        iverilog_records, iverilog_wall = execute_shards(
            [str(vvp), str(iverilog_output)],
            ranges,
            manifest,
            errors,
            timeout=900,
        )
        iverilog_summary, iverilog_checks = aggregate(iverilog_records)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                "tb_a3_hc_softmax_sinkhorn20",
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim_a3_hc_softmax_sinkhorn20",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                "-Wno-PROCASSINIT",
                "-Wno-UNUSEDSIGNAL",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=300,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(
                f"Verilator compile failed:\n{verilator_compile_log}"
            )
        verilator_executable = verilator_dir / "sim_a3_hc_softmax_sinkhorn20"
        verilator_records, verilator_wall = execute_shards(
            [str(verilator_executable)],
            ranges,
            manifest,
            errors,
            timeout=300,
        )
        verilator_summary, verilator_checks = aggregate(verilator_records)
        if (iverilog_summary, iverilog_checks) != (
            verilator_summary,
            verilator_checks,
        ):
            raise RuntimeError("Icarus and Verilator normalized results differ")

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_hc_stable_softmax_sinkhorn20_rne; "
            "proc; opt; check; stat"
        )
        process, yosys_seconds = run(
            [str(yosys), "-Q", "-p", yosys_script], timeout=240
        )
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration/check failed:\n{yosys_log}")

        source_paths = [ROOT / source for source in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_hc_softmax_sinkhorn20_campaign.v1",
            "status": "pass",
            "scope": {
                "atomic_stable_softmax_sinkhorn20_composition": True,
                "frozen_hc_numeric_and_operation_order": True,
                "checkpoint_first_t512_matrices": 512,
                "checkpoint_final_t320_matrices": 320,
                "t1_shape_witness": True,
                "authenticated_t512_final_output_bitwise_match": True,
                "current_rom_and_hbm_descriptor_identity_bound": True,
                "independent_exact_rational_oracle": True,
                "host_floating_point_oracle": False,
                "busy_input_refusal_and_input_latching": True,
                "active_reset_in_sinkhorn": True,
                "output_backpressure_stability": True,
                "atomic_fail_closed_output": True,
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "input_or_output_indexed_lookup_table": False,
                "full_200k_checkpoint_domain": False,
                "full_hc_pre": False,
                "descriptor_execution": False,
                "pc14_or_pc15_integration": False,
                "model_token_generation": False,
                "token_correctness": False,
                "eos": False,
                "technology_mapping_or_timing": False,
                "architectural_timing": False,
                "tpot": False,
            },
            "counts": manifest["counts"],
            "checkpoint_binding": manifest["checkpoint_binding"],
            "descriptor_binding": manifest["descriptor_binding"],
            "shard_count": len(ranges),
            "checks_per_simulator": iverilog_checks,
            "normalized_summary": iverilog_summary,
            "simulators_agree": True,
            "synthesis_frontend": {
                "top": "ot_a3_hc_stable_softmax_sinkhorn20_rne",
                "check_problems": 0,
                "note": "generic RTLIL elaboration only; no technology mapping, PPA, target frequency, architectural latency, token, or TPOT claim",
            },
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_parallel_shards": iverilog_wall,
                "iverilog_summed_shard_seconds": sum(
                    record["wall_seconds"] for record in iverilog_records
                ),
                "verilator_compile": verilator_compile_seconds,
                "verilator_parallel_shards": verilator_wall,
                "verilator_summed_shard_seconds": sum(
                    record["wall_seconds"] for record in verilator_records
                ),
                "yosys_elaboration": yosys_seconds,
            },
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                filename: sha256(VECTOR_DIR / filename) for filename in VECTOR_FILES
            },
            "simulator_shards": {
                "iverilog": iverilog_records,
                "verilator": verilator_records,
            },
            "log_sha256": {
                "verilator_compile": hashlib.sha256(
                    verilator_compile_log.encode()
                ).hexdigest(),
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
        "descriptor_execution",
        "pc14_or_pc15_integration",
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
    for filename, expected in result.get("vector_sha256", {}).items():
        current = VECTOR_DIR / filename
        if not current.is_file() or sha256(current) != expected:
            problems.append(f"vector hash is stale: {filename}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        problems = validate_retained(args.output.resolve())
        if problems:
            raise SystemExit("\n".join(problems))
        print(f"PASS retained HC composition campaign: {args.output.resolve()}")
        return
    result = campaign(args.output.resolve(), shard_count=args.shards)
    print(
        "PASS HC stable-softmax/Sinkhorn RTL campaign: "
        f"{result['counts']['cases']} matrices, "
        f"{result['checks_per_simulator']} checks, two simulators agree"
    )


if __name__ == "__main__":
    main()
