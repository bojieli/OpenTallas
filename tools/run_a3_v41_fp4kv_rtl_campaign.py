#!/usr/bin/env python3
"""Dual-simulator evidence for the V4.1 FP4 main-KV dequantize RTL block.

Runs the SAME source-current vectors through Icarus Verilog and the PINNED
Verilator 5.050, compares every emitted output word against the independent
exact-rational oracle in ``runtime/reference/fp4_kv.py``, requires the two
simulators to agree word for word and summary for summary, and elaborates the
block through the pinned Yosys frontend.

Reported cycles and host wall times are verification cost.  This campaign is
not a frequency, area, token-correctness or TPOT claim.
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


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VECTOR_DIR = ROOT / "testdata/rtl/a3_v41_fp4kv"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_v41_fp4kv_dequant_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_vector_fp4kv_dequant.sv",
    "rtl/test/tb_a3_v41_fp4kv_dequant.sv",
)
SYNTH_SOURCES = (
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_vector_fp4kv_dequant.sv",
)
ORACLE_SOURCES = (
    "runtime/reference/formats.py",
    "runtime/reference/fp4_kv.py",
    "tools/build_a3_v41_fp4kv_vectors.py",
    "tools/run_a3_v41_fp4kv_rtl_campaign.py",
)
VECTOR_FILES = (
    "meta.hex",
    "cases.hex",
    "code.hex",
    "scale.hex",
    "pass.hex",
    "expected.hex",
    "index.json",
)
TOP_MODULE = "tb_a3_v41_fp4kv_dequant"
SYNTH_TOP = "ot_a3_vector_fp4kv_dequant"

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
LANE_RE = re.compile(r"^LANE_SUMMARY (?P<body>.+)$")
PASS_RE = re.compile(
    r"^PASS a3_v41_fp4kv lane_counts=(?P<lane_counts>\d+) cases=(?P<cases>\d+) "
    r"checks=(?P<checks>\d+) word_checks=(?P<word_checks>\d+) "
    r"element_checks=(?P<element_checks>\d+)$"
)
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
IVERILOG_RE = re.compile(r"Icarus Verilog version (?P<major>\d+)\.(?P<minor>\d+)")
VERILATOR_RE = re.compile(r"Verilator (?P<major>\d+)\.(?P<minor>\d+)")
YOSYS_RE = re.compile(r"Yosys (?P<major>\d+)\.(?P<minor>\d+)")
CELL_RE = re.compile(r"^\s+(?P<count>\d+)\s+\$(?P<cell>[a-z_0-9]+)\s*$")


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
    if not iverilog or not vvp:
        raise RuntimeError("iverilog and vvp must be on PATH")
    if not verilator.is_file():
        raise RuntimeError(f"pinned Verilator {PINNED_VERILATOR_VERSION} is missing")
    if not yosys.is_file():
        raise RuntimeError(f"pinned Yosys {PINNED_YOSYS_VERSION} is missing")
    return Path(iverilog), Path(vvp), verilator, yosys


def plusargs(vector_root: Path) -> list[str]:
    return [
        f"+META={vector_root / 'meta.hex'}",
        f"+CASES={vector_root / 'cases.hex'}",
        f"+CODE={vector_root / 'code.hex'}",
        f"+SCALE={vector_root / 'scale.hex'}",
        f"+PASSTHROUGH={vector_root / 'pass.hex'}",
        f"+EXPECTED={vector_root / 'expected.hex'}",
    ]


def parse_log(log: str) -> tuple[list[dict[str, int]], list[dict[str, int]], dict[str, int]]:
    cases: list[dict[str, int]] = []
    lanes: list[dict[str, int]] = []
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
            continue
        match = LANE_RE.match(line)
        if match:
            lanes.append(
                {
                    item.group("key"): int(item.group("value"))
                    for item in KV_RE.finditer(match.group("body"))
                }
            )
            continue
        match = PASS_RE.match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if passed is None:
        raise RuntimeError("simulator did not emit the exact PASS marker")
    # A stable order, so the two simulators are compared on content only.
    cases.sort(key=lambda item: (item["lanes"], item["case"]))
    lanes.sort(key=lambda item: item["lanes"])
    return cases, lanes, passed


def validate_observed(
    cases: list[dict[str, int]],
    lane_rows: list[dict[str, int]],
    passed: dict[str, int],
    manifest: dict[str, Any],
) -> dict[str, Any]:
    """Compare every observed row against the oracle's own manifest."""

    lane_counts = [int(value) for value in manifest["rtl_parameters"]["lane_counts_instantiated"]]
    expected_rows: list[dict[str, int]] = []
    for lanes in lane_counts:
        for index, record in enumerate(manifest["cases"]):
            error = int(record["expected_error"][str(lanes)])
            legal = error == 0
            expected_rows.append(
                {
                    "lanes": lanes,
                    "case": index,
                    "error": error,
                    "out_words": record["expected_output_words"] if legal else 0,
                    "elements": record["count"] if legal else 0,
                    "saturations": record["expected_saturations"] if legal else 0,
                    "beats": int(record["expected_issue_beats"][str(lanes)]),
                    "stalls": 0,
                }
            )
    observed_rows = [
        {key: value for key, value in row.items() if key != "scan"} for row in cases
    ]
    if observed_rows != expected_rows:
        for observed, wanted in zip(observed_rows, expected_rows):
            if observed != wanted:
                raise RuntimeError(
                    f"simulator row differs from the oracle: {observed} != {wanted}"
                )
        raise RuntimeError(
            f"simulator produced {len(observed_rows)} rows, oracle expects "
            f"{len(expected_rows)}"
        )
    for row in lane_rows:
        if row["failures"] != 0:
            raise RuntimeError(f"lane {row['lanes']} reported failures")
        if row["worst_stall"] != 0:
            raise RuntimeError(
                f"lane {row['lanes']} stalled: initiation interval is not one"
            )
    expected_pass = manifest["expected_pass"]
    if passed["cases"] != int(expected_pass["cases"]):
        raise RuntimeError("PASS case count differs from the manifest")
    if passed["lane_counts"] != int(expected_pass["lane_counts"]):
        raise RuntimeError("PASS lane-count differs from the manifest")
    if passed["word_checks"] != int(expected_pass["word_checks"]):
        raise RuntimeError("PASS word-check count differs from the manifest")
    if passed["element_checks"] != int(expected_pass["element_checks"]):
        raise RuntimeError("PASS element-check count differs from the manifest")
    return {
        "rows": observed_rows,
        "lane_rows": lane_rows,
        "pass": passed,
    }


def regenerate_and_compare(temporary: Path) -> dict[str, Any]:
    generated = temporary / "vectors"
    process, _ = run(
        [
            shutil.which("python3") or "python3",
            str(ROOT / "tools/build_a3_v41_fp4kv_vectors.py"),
            "--output",
            str(generated),
        ],
        timeout=900,
    )
    if process.returncode:
        raise RuntimeError(
            f"vector generation failed:\n{process.stdout}\n{process.stderr}"
        )
    for filename in VECTOR_FILES:
        if (generated / filename).read_bytes() != (VECTOR_DIR / filename).read_bytes():
            raise RuntimeError(f"checked-in vector {filename} is not source-current")
    return json.loads((generated / "index.json").read_text())


def synthesis_census(log: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in log.splitlines():
        match = CELL_RE.match(line)
        if match:
            counts[match.group("cell")] = counts.get(match.group("cell"), 0) + int(
                match.group("count")
            )
    return counts


def third_party_cross_check() -> dict[str, Any]:
    """Confirm the oracle's rounding rule against PyTorch's own FP8 cast.

    This is a THIRD independent implementation of the same rounding rule: the
    reference rounds exact rationals, the RTL rounds a fixed-point alignment,
    and ``torch.float8_e4m3fn`` rounds an IEEE double in C++.  Products above
    the finite range are excluded, because the OpenTallas contract clamps them
    -- as the vendor path does -- while PyTorch's cast poisons them to NaN;
    that difference is recorded rather than hidden.
    """

    from runtime.reference.fp4_kv import (
        dequantize_element_to_fp8,
        element_value,
        finite_scale_codes,
        scale_value,
    )

    try:
        import torch
    except Exception as exc:  # pragma: no cover - optional dependency
        return {"available": False, "reason": type(exc).__name__}

    values: list[float] = []
    expected: list[int] = []
    saturating = 0
    for code in range(16):
        for scale in finite_scale_codes():
            product = element_value(code) * scale_value(scale)
            result, saturated = dequantize_element_to_fp8(code, scale)
            if abs(product) > 448:
                if not saturated or (result & 0x7F) != 0x7E:
                    raise RuntimeError(
                        f"out-of-range pair 0x{code:x}/0x{scale:02x} did not clamp"
                    )
                saturating += 1
                continue
            if saturated:
                raise RuntimeError(
                    f"in-range pair 0x{code:x}/0x{scale:02x} reported saturation"
                )
            values.append(float(product))
            expected.append(result)
    observed = (
        torch.tensor(values, dtype=torch.float64)
        .to(torch.float8_e4m3fn)
        .view(torch.uint8)
        .tolist()
    )
    mismatches = 0
    for wanted, got in zip(expected, observed):
        # PyTorch keeps a negative zero; the architectural contract
        # canonicalises zero to +0, which is the only permitted difference.
        if wanted != got and not (wanted == 0 and got in (0x00, 0x80)):
            mismatches += 1
    if mismatches:
        raise RuntimeError(
            f"{mismatches} of {len(values)} in-range pairs differ from PyTorch"
        )
    return {
        "available": True,
        "implementation": f"torch {torch.__version__} float8_e4m3fn cast",
        "in_range_pairs_compared": len(values),
        "in_range_pairs_matched": len(values),
        "saturating_pairs_excluded": saturating,
        "excluded_because": (
            "the contract clamps to the finite endpoint; the PyTorch cast "
            "produces NaN instead"
        ),
    }


def campaign(output: Path) -> dict[str, Any]:
    from runtime.reference.fp4_kv import (
        CONTRACT,
        prove_binary32_intermediate_is_exact,
    )

    exact_pairs = prove_binary32_intermediate_is_exact()
    cross_check = third_party_cross_check()
    iverilog, vvp, verilator, yosys = resolve_tools()
    tools = {
        "iverilog": tool_identity(iverilog, ["-V"], IVERILOG_RE, None, "Icarus"),
        "vvp": {
            "path": scrub(str(vvp.resolve())),
            "sha256": sha256(vvp.resolve()),
        },
        "verilator": tool_identity(
            verilator, ["--version"], VERILATOR_RE, (5, 50), "Verilator"
        ),
        "yosys": tool_identity(yosys, ["-V"], YOSYS_RE, (0, 68), "Yosys"),
    }

    with tempfile.TemporaryDirectory(prefix="a3-v41-fp4kv-") as name:
        temporary = Path(name)
        manifest = regenerate_and_compare(temporary)

        icarus_binary = temporary / "tb.vvp"
        process, icarus_compile_seconds = run(
            [
                str(iverilog),
                "-g2012",
                "-s",
                TOP_MODULE,
                "-o",
                str(icarus_binary),
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=300,
        )
        if process.returncode:
            raise RuntimeError(
                f"Icarus compile failed:\n{process.stdout}\n{process.stderr}"
            )
        process, icarus_run_seconds = run(
            [str(vvp), str(icarus_binary), *plusargs(VECTOR_DIR)], timeout=1800
        )
        icarus_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Icarus simulation failed:\n{icarus_log}")
        icarus_cases, icarus_lanes, icarus_pass = parse_log(icarus_log)
        icarus_result = validate_observed(
            icarus_cases, icarus_lanes, icarus_pass, manifest
        )

        verilator_dir = temporary / "verilator"
        process, verilator_compile_seconds = run(
            [
                str(verilator),
                "--binary",
                "--timing",
                "--top-module",
                TOP_MODULE,
                "--Mdir",
                str(verilator_dir),
                "-o",
                "sim",
                "-Wno-fatal",
                "-Wno-WIDTHEXPAND",
                "-Wno-WIDTHTRUNC",
                *[str(ROOT / source) for source in RTL_SOURCES],
            ],
            timeout=900,
        )
        verilator_compile_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator compile failed:\n{verilator_compile_log}")
        process, verilator_run_seconds = run(
            [str(verilator_dir / "sim"), *plusargs(VECTOR_DIR)], timeout=1800
        )
        verilator_log = process.stdout + process.stderr
        if process.returncode:
            raise RuntimeError(f"Verilator simulation failed:\n{verilator_log}")
        verilator_cases, verilator_lanes, verilator_pass = parse_log(verilator_log)
        verilator_result = validate_observed(
            verilator_cases, verilator_lanes, verilator_pass, manifest
        )

        agree = (
            icarus_result["rows"] == verilator_result["rows"]
            and icarus_result["lane_rows"] == verilator_result["lane_rows"]
            and icarus_result["pass"] == verilator_result["pass"]
        )
        if not agree:
            raise RuntimeError("Icarus and Verilator normalized results differ")

        # The divider/modulo assertions are made by Yosys itself, so a
        # regression fails the run rather than a parser.
        yosys_script = (
            "read_verilog -sv "
            + " ".join(str(ROOT / source) for source in SYNTH_SOURCES)
            + f"; hierarchy -check -top {SYNTH_TOP}; proc; opt; check; stat"
            + "; select -assert-count 0 t:$div"
            + "; select -assert-count 0 t:$mod"
            + "; select -assert-count 0 t:$divfloor"
            + "; select -assert-count 0 t:$modfloor"
            + "; select -list t:$mul"
        )
        process, yosys_seconds = run([str(yosys), "-Q", "-p", yosys_script], timeout=600)
        yosys_log = process.stdout + process.stderr
        if process.returncode or "Found and reported 0 problems." not in yosys_log:
            raise RuntimeError(f"Yosys elaboration failed:\n{yosys_log}")
        census = synthesis_census(yosys_log)
        # One multiplier CELL in the whole design: the lane's 4x4 significand
        # product.  Every other product in the block is by a constant and
        # every extent predicate is by comparison or accumulation, which is why
        # no $div/$mod exists for Yosys to find above.
        multipliers = [
            line.strip()
            for line in yosys_log.splitlines()
            if "/$mul$" in line
        ]
        if len(multipliers) != 1 or "dequant_lane" not in multipliers[0]:
            raise RuntimeError(
                "expected exactly one multiplier, the lane significand product; "
                f"found {multipliers}"
            )

        lane_summary = {
            str(row["lanes"]): {
                "legal_cases": row["legal"],
                "refused_cases": row["refused"],
                "checks": row["checks"],
                "output_words_compared": row["words"],
                "elements_compared": row["elements"],
                "untouched_sentinel_words_checked": row["sentinels"],
                "worst_case_stall_cycles": row["worst_stall"],
                "worst_case_operator_cycles": row["worst_cycles"],
            }
            for row in icarus_lanes
        }
        checks_per_simulator = int(icarus_pass["checks"])

        source_paths = [ROOT / path for path in (*RTL_SOURCES, *ORACLE_SOURCES)]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_v41_fp4kv_dequant_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "unit": {
                "rtl": "rtl/abi3/ot_a3_vector_fp4kv_dequant.sv",
                "engine": "VECTOR.CONVERT with a scale-group operand",
                "ir_kind": "DEQUANTIZE",
                "dtype": "fp4_e2m1_s16_e4m3",
                "contract": CONTRACT,
                "reference": "runtime/reference/fp4_kv.py",
                "primary_source": "SRC-DSV41-FLASH-MODEL",
                "work_package": "WP-K (DS41-R6)",
            },
            "pipeline": {
                "registered_stages": 7,
                "initiation_interval": 1,
                "stage_names": [
                    "issue beat registers",
                    "E2M1/E4M3FN decode",
                    "4x4 significand multiply",
                    "exact 22-bit alignment shift",
                    "leading-one normalize",
                    "truncate, round bit, sticky OR",
                    "RNE round, carry, saturate, encode",
                ],
                "initiation_interval_is_measured_not_asserted": True,
                "measured_worst_case_stall_cycles": max(
                    row["worst_stall"] for row in icarus_lanes
                ),
                "retired_elements_per_cycle_equals_lanes": True,
            },
            "geometry": {
                "scale_group_is_an_operand_field": True,
                "scale_group_default_parameter": manifest["rtl_parameters"][
                    "SCALE_GROUP_DEFAULT"
                ],
                "max_elements_parameter": manifest["rtl_parameters"]["MAX_ELEMENTS"],
                "lane_counts_elaborated": manifest["rtl_parameters"][
                    "lane_counts_instantiated"
                ],
                "scale_groups_admitted": manifest["coverage"][
                    "distinct_scale_groups_admitted"
                ],
                "extents_admitted": manifest["coverage"]["extents_admitted"],
                "identical_output_words_at_every_lane_count": True,
                "no_model_dimension_is_a_localparam": True,
            },
            "coverage": {
                **manifest["coverage"],
                "exhaustive_element_scale_pairs": exact_pairs,
                "exhaustive_pair_space_is_complete": exact_pairs == 16 * 254,
            },
            "oracle": {
                "module": "runtime/reference/fp4_kv.py",
                "arithmetic": "exact rationals, no host floating point",
                "binary32_intermediate_pairs_proved_exact": exact_pairs,
                "single_rounding_contract": (
                    "the E2M1 x E4M3FN product is exact, so the contract is one "
                    "saturating round-to-nearest-even into E4M3FN"
                ),
                "third_party_cross_check": cross_check,
            },
            "verilator_harness": {
                "style": "--binary --timing, Verilator's own generated main",
                "plusarg_context_owner": (
                    "the generated main creates a VerilatedContext, calls "
                    "contextp->commandArgs(argc, argv) BEFORE constructing the "
                    "model, and hands that same context to the model, so "
                    "$value$plusargs in the testbench reads the real argv; no "
                    "hand-written C++ harness with a second context is used"
                ),
                "verified_in_generated_main": True,
            },
            "per_lane_count": lane_summary,
            "checks_per_simulator": checks_per_simulator,
            "simulators_agree": True,
            "normalized_cases": icarus_result["rows"],
            "synthesis_frontend": {
                "top": SYNTH_TOP,
                "check_problems": 0,
                "yosys_stat_cell_counts": census,
                "yosys_stat_note": (
                    "stat sums its per-module listings, so a cell inside the "
                    "lane appears once per elaborated listing; the authoritative "
                    "multiplier count is multiplier_cells below"
                ),
                "multiplier_cells": len(multipliers),
                "multiplier_cell": scrub(multipliers[0]),
                "dividers_or_modulo": 0,
                "divider_absence_asserted_by": "yosys select -assert-count 0",
                "note": (
                    "generic synthesizable elaboration only; no library mapping, "
                    "no PPA, no frequency, no token correctness, no TPOT claim"
                ),
            },
            "claim_boundary": {
                **manifest["claim_boundary"],
                "dual_simulator_word_for_word": True,
                "establishes_e2m1_x_e4m3_to_e4m3_bit_exactness_over_the_whole_pair_space": True,
                "establishes_fail_closed_refusal_with_untouched_destination": True,
                "establishes_initiation_interval_one_by_measurement": True,
                "establishes_identical_results_at_lanes_1_4_and_8": True,
                "establishes_asap7_or_sky130_frequency": False,
                "establishes_area_or_power": False,
                "is_placed_or_routed": False,
                "integrates_the_shipped_engine_array": False,
                "executes_an_abi3_descriptor_or_program": False,
                "establishes_a_model_token_or_tpot": False,
                "establishes_the_vendor_forward_quantizer_scale_selection": False,
                "reads_the_pinned_vendor_inference_model_py": False,
                "covers_a_partial_final_scale_group": False,
                "covers_scale_groups_that_are_not_multiples_of_lanes": False,
                "covers_extents_beyond_the_max_elements_parameter": False,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "not_established": [
                "no frequency, area or power number: the campaign elaborates the "
                "block through the Yosys frontend and stops there",
                "the vendor's forward FP4 quantizer scale-selection rule is not "
                "pinned here; the pinned inference/model.py is not in this "
                "checkout and only the dequantize direction is claimed",
                "the block is not wired into ot_a3_engine_array, so no ABI 3.0 "
                "descriptor, program or token path is exercised",
                "a quantized region that is not a whole number of scale groups is "
                "REFUSED, not padded; nothing is claimed about partial groups",
                "the FP8 destination format is the OpenTallas contract's choice; "
                "the vendor reconstructs the same exact products in BF16",
            ],
            "verification_wall_seconds": {
                "icarus_compile": icarus_compile_seconds,
                "icarus_simulation": icarus_run_seconds,
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
                "icarus": hashlib.sha256(icarus_log.encode()).hexdigest(),
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
    """Problems with the retained record, for the test suite to report."""

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
        problems.append("simulators do not agree")
    pipeline = value.get("pipeline", {})
    if pipeline.get("initiation_interval") != 1:
        problems.append("initiation interval differs")
    if pipeline.get("measured_worst_case_stall_cycles") != 0:
        problems.append("a stall cycle was measured")
    coverage = value.get("coverage", {})
    if coverage.get("exhaustive_element_scale_pairs") != 16 * 254:
        problems.append("the element/scale pair space is not exhaustively covered")
    if value.get("synthesis_frontend", {}).get("dividers_or_modulo") != 0:
        problems.append("the datapath instantiates a divider")
    if value.get("synthesis_frontend", {}).get("check_problems") != 0:
        problems.append("the synthesis frontend reported problems")
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
        "a3_v41_fp4kv dequantize RTL campaign "
        f"status={result['status']} "
        f"checks_per_simulator={result['checks_per_simulator']} "
        f"exhaustive_pairs={result['coverage']['exhaustive_element_scale_pairs']} "
        f"simulators_agree={result['simulators_agree']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
