#!/usr/bin/env python3
"""Dual-simulator bit-exactness campaign for DMA.NGRAM_HASH (sub-opcode 0x04).

Runs rtl/test/tb_a3_v41_ngram_hash.sv under Icarus Verilog AND the pinned
Verilator 5.050 over the same vector set, requires both to produce the same
normalized result, and elaborates the device through the pinned Yosys.

Every expected value in the vectors comes from
`runtime/reference/engram.py::ngram_row_ids`, which is written from the pinned
`inference/engram.py` semantics and never reads the RTL.  The vector set is
regenerated here and compared byte for byte with the checked-in copy, so a
campaign cannot pass against stale expectations.

Simulator cycles and host wall times are verification cost.  Nothing here is a
token latency, a frequency or a TPOT.
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
VECTOR_DIR = ROOT / "testdata/rtl/a3_v41_ngram_hash"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_ngram_hash_campaign.json"
VENDOR_ORACLE = ROOT / "results/rtl/a3_v41_ngram_hash_vendor_oracle.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_dma_ngram_hash.sv",
    "rtl/test/tb_a3_v41_ngram_hash.sv",
)
SYNTH_SOURCES = ("rtl/abi3/ot_a3_dma_ngram_hash.sv",)
ORACLE_SOURCES = (
    "runtime/reference/engram.py",
    "tools/build_a3_v41_ngram_hash_vectors.py",
    "tools/run_a3_v41_ngram_hash_rtl_campaign.py",
)
VECTOR_FILES = ("config.hex", "cases.hex", "index.json")

#: The bench's phase plan, which fixes how many results a passing run must
#: check: one isolated latency beat per configuration, then every case at full
#: rate, then every case again through a stalling consumer, plus the
#: write-guard prefix of the first configuration twice.
PHASE_LATENCY_BEATS_PER_CONFIG = 1
PHASE_FULL_RATE_PASSES = 1
PHASE_STALLED_PASSES = 1
PHASE_GUARD_PASSES = 2

SUMMARY_RE = re.compile(r"^NGRAM_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_v41_ngram_hash configs=(?P<configs>\d+) cases=(?P<cases>\d+) "
    r"outputs=(?P<outputs>\d+) refusals=(?P<refusals>\d+) checks=(?P<checks>\d+) "
    r"ii_violations=(?P<ii_violations>\d+)$"
)
KV_RE = re.compile(r"(?P<key>[a-z_0-9]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")
CELL_RE = re.compile(r"^\s+(?P<count>\d+)\s+(?P<cell>\$[a-z_0-9]+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scrub(value: str) -> str:
    return value.replace(str(ROOT), "<ROOT>").replace(str(Path.home()), "<HOME>")


def run(command: list[str], *, timeout: int) -> tuple[subprocess.CompletedProcess[str], float]:
    started = time.monotonic()
    try:
        process = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, check=False, timeout=timeout
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
    process, _ = run([str(executable), *arguments], timeout=60)
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
    iverilog = shutil.which("iverilog")
    vvp = shutil.which("vvp")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not iverilog or not vvp or not verilator.is_file() or not yosys.is_file():
        raise RuntimeError("required pinned RTL tools are unavailable")
    return Path(iverilog), Path(vvp), verilator, yosys


def plusargs() -> list[str]:
    return [
        f"+CONFIG={VECTOR_DIR / 'config.hex'}",
        f"+CASES={VECTOR_DIR / 'cases.hex'}",
    ]


def parse_log(log: str) -> tuple[dict[str, int], dict[str, int]]:
    summary: dict[str, int] | None = None
    passed: dict[str, int] | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = SUMMARY_RE.match(line)
        if match:
            summary = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(match.group("body"))
            }
        match = PASS_RE.match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if summary is None or passed is None:
        raise RuntimeError("simulator did not emit the exact PASS and summary markers")
    return summary, passed


def expected_census(manifest: dict[str, Any]) -> dict[str, int]:
    """Predict the bench's output and refusal census from the vector manifest.

    Nothing here is a constant that a grown vector set would leave stale: every
    term comes from the manifest, and the multipliers are the bench's published
    phase plan.
    """

    configs = manifest["configurations"]
    cases = int(manifest["expected_pass"]["cases"])
    guard_prefix = int(manifest["expected_pass"]["bench_write_guard_prefix"])
    outputs = (
        PHASE_LATENCY_BEATS_PER_CONFIG * len(configs)
        + (PHASE_FULL_RATE_PASSES + PHASE_STALLED_PASSES) * cases
        + PHASE_GUARD_PASSES * guard_prefix
    )
    codes: dict[int, int] = {}
    for key, count in manifest["expected_pass"]["refusals"].items():
        code = int(key.rsplit("_", 1)[1])
        codes[code] = codes.get(code, 0) + (
            PHASE_FULL_RATE_PASSES + PHASE_STALLED_PASSES
        ) * int(count)
    for config in configs:
        code = int(config["first_case_refuse"])
        codes[code] = codes.get(code, 0) + PHASE_LATENCY_BEATS_PER_CONFIG
    for code in configs[0]["guard_prefix_refuse"]:
        codes[int(code)] = codes.get(int(code), 0) + PHASE_GUARD_PASSES
    return {
        "outputs": outputs,
        "refusals": sum(count for code, count in codes.items() if code != 0),
        **{f"code{code}": count for code, count in codes.items() if code != 0},
    }


def validate(summary: dict[str, int], passed: dict[str, int], manifest: dict[str, Any]) -> None:
    census = expected_census(manifest)
    if passed["configs"] != int(manifest["expected_pass"]["configs"]):
        raise RuntimeError("configuration count differs from the vector manifest")
    if passed["cases"] != int(manifest["expected_pass"]["cases"]):
        raise RuntimeError("case count differs from the vector manifest")
    if passed["outputs"] != census["outputs"]:
        raise RuntimeError(
            f"checked outputs {passed['outputs']} differ from the phase plan's "
            f"{census['outputs']}: a phase was skipped or a case was not checked"
        )
    if passed["refusals"] != census["refusals"]:
        raise RuntimeError("refusal total differs from the vector manifest")
    if summary["expected_refusals"] != passed["refusals"]:
        raise RuntimeError("observed refusals differ from the vectors' expectation")
    for key, count in census.items():
        if key.startswith("code") and summary.get(key) != count:
            raise RuntimeError(f"refusal census {key} differs: {summary.get(key)} != {count}")
    if passed["ii_violations"] != 0:
        raise RuntimeError("the bench reported an initiation-interval violation")
    if summary["latency"] <= 0:
        raise RuntimeError("the bench did not measure a latency")
    if summary["stalls"] <= 0:
        raise RuntimeError("the stalled-consumer phase did not stall")
    if summary["cfg_errors"] != sum(
        int(config["expect_cfg_error"]) for config in manifest["configurations"]
    ):
        raise RuntimeError("configuration error reports differ from the manifest")


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_v41_ngram_hash_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=600,
    )
    if process.returncode:
        raise RuntimeError(f"vector generation failed:\n{process.stdout}\n{process.stderr}")
    for name in VECTOR_FILES:
        if (generated / name).read_bytes() != (VECTOR_DIR / name).read_bytes():
            raise RuntimeError(f"checked-in vector {name} is not source-current")
    return json.loads((generated / "index.json").read_text())


def parse_cells(log: str) -> dict[str, int]:
    cells: dict[str, int] = {}
    for line in log.splitlines():
        match = CELL_RE.match(line)
        if match:
            cell = match.group("cell")
            cells[cell] = cells.get(cell, 0) + int(match.group("count"))
    return cells


def vendor_oracle_binding() -> dict[str, Any]:
    if not VENDOR_ORACLE.is_file():
        return {
            "present": False,
            "note": (
                "the vendor cross-check record is absent; run "
                "tools/check_a3_v41_ngram_hash_vendor_oracle.py with the pinned "
                "inference/engram.py to produce it"
            ),
        }
    record = json.loads(VENDOR_ORACLE.read_text())
    return {
        "present": True,
        "path": "results/rtl/a3_v41_ngram_hash_vendor_oracle.json",
        "sha256": sha256(VENDOR_ORACLE),
        "status": record.get("status"),
        "records_compared": record.get("records_compared"),
        "mismatches": record.get("mismatches"),
        "vendor_source_sha256": record.get("vendor_source", {}).get("sha256"),
    }


def campaign(output: Path) -> dict[str, Any]:
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_RE, None, "Icarus"),
        "vvp": {"path": scrub(str(vvp.resolve())), "sha256": sha256(vvp.resolve())},
        "verilator": tool_identity(verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }
    with tempfile.TemporaryDirectory(prefix="a3-v41-ngram-hash-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        vvp_image = temporary / "tb.vvp"
        process, iverilog_compile_seconds = run(
            [
                str(iverilog), "-g2012", "-s", "tb_a3_v41_ngram_hash", "-o", str(vvp_image),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=300,
        )
        if process.returncode:
            raise RuntimeError(f"Icarus compile failed:\n{process.stdout}\n{process.stderr}")
        process, iverilog_run_seconds = run(
            [str(vvp), str(vvp_image), *plusargs()], timeout=1800
        )
        iverilog_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{iverilog_log}")
        iverilog_summary, iverilog_pass = parse_log(iverilog_log)
        validate(iverilog_summary, iverilog_pass, manifest)

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator), "--binary", "--timing", "--top-module",
                "tb_a3_v41_ngram_hash", "--Mdir", str(verilator_dir), "-o", "sim",
                "-Wno-fatal", "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=900,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim"), *plusargs()], timeout=900
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_summary, verilator_pass = parse_log(verilator_log)
        validate(verilator_summary, verilator_pass, manifest)

        simulators_agree = (
            iverilog_summary == verilator_summary and iverilog_pass == verilator_pass
        )
        if not simulators_agree:
            raise RuntimeError(
                f"Icarus and Verilator differ:\n{iverilog_summary}\n{verilator_summary}"
            )

        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + "; hierarchy -check -top ot_a3_dma_ngram_hash; proc; opt; check; stat"
        )
        process, yosys_seconds = run([str(yosys), "-Q", "-p", yosys_script], timeout=600)
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration failed:\n{yosys_log}")
        cells = parse_cells(yosys_log)

        source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_v41_ngram_hash_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "unit": {
                "rtl": "rtl/abi3/ot_a3_dma_ngram_hash.sv",
                "engine_family": "DMA",
                "engine_sub_opcode": 4,
                "ir_kind": "NGRAM_HASH",
                "numeric_contract": "ngram_hash_u32_v1",
                "work_package": "WP-K (DS41-R6)",
            },
            "reference": {
                "module": "runtime/reference/engram.py",
                "function": "ngram_row_ids",
                "sha256": sha256(ROOT / "runtime/reference/engram.py"),
                "derived_from": (
                    "the pinned inference/engram.py of SRC-DSV41-FLASH-MODEL, "
                    "revision dba1be0a40aa45a94ad051997016db3960a90277, source "
                    "SHA-256 11f35ecbead8150c35aa002b3d180ef290b05a25afe883a11884"
                    "f94d476d3897; never from this RTL"
                ),
                "vendor_cross_check": vendor_oracle_binding(),
            },
            "identity_implemented": {
                "fold": "XOR over (compressed id * per-lookback multiplier)",
                "reduction": "modulo the per-(order, head) column prime",
                "row": "column offset + residue",
                "released_layout_proof": (
                    "the 24 derived column primes of each Engram layer sum to that "
                    "layer's released engram_num_embeddings (384,006,168 and "
                    "384,016,682), which is checked when the vectors are built"
                ),
            },
            "pipeline": {
                "measured_latency_cycles": iverilog_summary["latency"],
                "latency_equals_device_info_port": True,
                "initiation_interval": 1,
                "initiation_interval_evidence": (
                    "in an unstalled burst the bench requires in_ready never to "
                    "drop and the first and last of N results to be exactly N-1 "
                    "cycles apart; ii_violations is zero in both simulators"
                ),
                "registered_boundary": "in_valid/in_ready and out_valid/out_ready",
                "reciprocal_derivation_cycles_max": iverilog_summary["recip_max"],
                "reciprocal_derivation_cycles_total": iverilog_summary["recip_total"],
                "per_stage_arithmetic": (
                    "one MUL_DIGIT_W-bit digit folded into a carry-save "
                    "accumulator plus one MUL_DIGIT_W-wide carry-propagate; no "
                    "stage walks a vector, holds more than one carry chain, or "
                    "contains a combinational divide"
                ),
            },
            "geometry": {
                "all_model_numbers_are_parameters_or_operands": True,
                "device_parameters": manifest["device_parameters"],
                "run_time_operands": [
                    "table row count",
                    "pad id",
                    "compressed-vocabulary extent",
                    "per-lookback multipliers",
                    "per-column modulus",
                    "per-column row offset",
                ],
                "configurations_exercised": [
                    {
                        "name": config["name"],
                        "table_rows": config["table_rows"],
                        "modulus_bits": sorted(
                            {int(prime).bit_length() for row in config["primes"] for prime in row}
                        ),
                        "cases": config["case_count"],
                        "expect_cfg_error": config["expect_cfg_error"],
                    }
                    for config in manifest["configurations"]
                ],
            },
            "checks_per_simulator": iverilog_pass["checks"],
            "compared": [
                "the row id of every case",
                "the residue before the column offset",
                "the 63-bit folded dividend",
                "the refusal code, and a forced-zero row id on every refusal",
                "the returned tag, order and head of every case",
                "the configuration error flag and code of every configuration",
            ],
            "normalized_summary": iverilog_summary,
            "normalized_pass": iverilog_pass,
            "simulators_agree": simulators_agree,
            "coverage": manifest["coverage"],
            "verification_wall_seconds": {
                "iverilog_compile": iverilog_compile_seconds,
                "iverilog_simulation": iverilog_run_seconds,
                "verilator_compile": verilator_compile_seconds,
                "verilator_simulation": verilator_run_seconds,
                "yosys_elaboration": yosys_seconds,
            },
            "synthesis_frontend": {
                "top": "ot_a3_dma_ngram_hash",
                "check_problems": 0,
                "cells": cells,
                "note": (
                    "generic synthesizable elaboration only; no library mapping, "
                    "no placement, no route, no frequency, no PPA claim"
                ),
            },
            "claim_boundary": {
                "compares_against_an_independent_python_reference": True,
                "configuration_path_is_sequential_not_initiation_interval_one": True,
                "dual_simulator_bit_exact": True,
                "establishes_asap7_or_sky130_frequency": False,
                "establishes_token_latency_or_tpot": False,
                "executes_engram_row_read_or_gate": False,
                "executes_the_shipped_deployment_sequencer": False,
                "is_placed_or_routed": False,
                "measures_area_or_power": False,
                "reproduces_the_compressed_token_map": False,
                "runs_inside_the_dma_engine_or_the_engine_array": False,
                "simulator_cycles_are_verification_cost_only": True,
                "uses_the_released_column_primes_offsets_and_multipliers": True,
                "uses_the_released_compressed_pad_id": False,
                "vendor_forward_executed_inside_this_campaign": False,
                "validates_the_barrett_bound_in_hardware": True,
            },
            "limitations": [
                "the per-column Barrett reciprocal is derived by a shared "
                "sequential divider at configuration time, which is NOT an "
                "initiation-interval-one path; only the streaming datapath is",
                "the block is verified standalone: no instruction decode, no "
                "descriptor validation and no engine-array integration is exercised",
                "the compressed token map of the pinned build_compressed_token_map "
                "is upstream data and is not reproduced, so a compressed id is an "
                "operand here, not a checked derivation",
                "the pad id is an operand; the released compressed pad id needs the "
                "vendor tokenizer and is not established",
                "the per-column reciprocal derivation cost is reported in cycles "
                "only; it is not a frequency or a wall-clock claim",
            ],
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {name: sha256(VECTOR_DIR / name) for name in VECTOR_FILES},
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
    if value.get("simulators_agree") is not True:
        problems.append("the two simulators did not agree")
    if value.get("pipeline", {}).get("initiation_interval") != 1:
        problems.append("initiation interval differs")
    if value.get("normalized_pass", {}).get("ii_violations") != 0:
        problems.append("an initiation-interval violation was recorded")
    if not value.get("geometry", {}).get("all_model_numbers_are_parameters_or_operands"):
        problems.append("the geometry record does not assert parameterization")
    for source, expected in value.get("source_sha256", {}).items():
        candidate = ROOT / source
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"source drift: {source}")
    for name, expected in value.get("vector_sha256", {}).items():
        candidate = VECTOR_DIR / name
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"vector drift: {name}")
    return problems


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return result


def main() -> int:
    args = parser().parse_args()
    result = campaign(args.output)
    print(
        "a3_v41_ngram_hash RTL campaign "
        f"status={result['status']} "
        f"cases={result['normalized_pass']['cases']} "
        f"outputs={result['normalized_pass']['outputs']} "
        f"checks={result['checks_per_simulator']} "
        f"latency={result['pipeline']['measured_latency_cycles']} ii=1 "
        f"agree={result['simulators_agree']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
