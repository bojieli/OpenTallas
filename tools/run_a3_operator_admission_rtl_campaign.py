#!/usr/bin/env python3
"""Dual-simulator evidence for the six newly admitted ABI 3.0 operator families.

Three testbenches, both pinned simulators, one artifact:

* ``tb_a3_operator_admission`` drives the unmodified issue bridge with the
  retained shipped records of the governed Qwen decode program's DMA.SCATTER,
  ATTENTION.GQA, VECTOR.ADD, VECTOR.SILU_MUL, SELECTION.ARGMAX and
  SELECTION.TOKEN_APPEND instructions, and compares every result word against
  the independent scalar references;
* ``tb_a3_vector_silu_mul`` and ``tb_a3_selection_token_append`` are the block
  campaigns of the two datapaths this device did not have before.

Simulator cycles and host wall times here are verification cost.  Nothing in
this campaign is a token commit, a layer, or TPOT evidence.
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
ADMISSION_VECTORS = ROOT / "testdata/rtl/a3_operator_admission"
UNIT_VECTORS = ROOT / "testdata/rtl/a3_operator_units"
DEFAULT_OUTPUT = ROOT / "results/rtl/a3_operator_admission_campaign.json"
PINNED_VERILATOR_VERSION = "5.050"
PINNED_YOSYS_VERSION = "0.68"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

BRIDGE_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    "rtl/abi3/ot_a3_selection_argmax.sv",
    "rtl/abi3/ot_a3_dma_index_mover.sv",
    "rtl/abi3/ot_a3_vector_add.sv",
    "rtl/abi3/ot_a3_vector_convert.sv",
    "rtl/abi3/ot_a3_vector_scale.sv",
    "rtl/abi3/ot_a3_vector_hadamard.sv",
    "rtl/abi3/ot_a3_vector_index_score.sv",
    "rtl/abi3/ot_a3_vector_compress_project.sv",
    "rtl/abi3/ot_a3_vector_mhc_post.sv",
    "rtl/abi3/ot_a3_engine_array.sv",
    "rtl/abi3/ot_a3_vector_rms_norm.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
)
SILU_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
)
APPEND_SOURCES = (
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
)
BENCHES = (
    {
        "top": "tb_a3_operator_admission",
        "sources": BRIDGE_SOURCES + ("rtl/test/tb_a3_operator_admission.sv",),
        "timeout": 5400,
    },
    {
        "top": "tb_a3_vector_silu_mul",
        "sources": SILU_SOURCES + ("rtl/test/tb_a3_vector_silu_mul.sv",),
        "timeout": 3600,
    },
    {
        "top": "tb_a3_selection_token_append",
        "sources": APPEND_SOURCES + ("rtl/test/tb_a3_selection_token_append.sv",),
        "timeout": 600,
    },
)
# The whole bridge does not elaborate under the pinned Yosys 0.68: the frontend
# rejects a non-constant procedural for-loop bound in rtl/ot_fp32_rne_pkg.sv
# reached through ot_a3_vector_index_score, which predates this campaign and
# is recorded rather than worked around.  The two datapaths this campaign adds
# are elaborated, exactly as the PC38 GQA campaign elaborates its one module.
SYNTHESIS_TOPS = (
    {"top": "ot_a3_vector_silu_mul", "sources": SILU_SOURCES},
    {"top": "ot_a3_selection_token_append", "sources": APPEND_SOURCES},
)
ORACLE_SOURCES = (
    "runtime/reference/formats.py",
    "runtime/reference/tensor_accelerator_attention.py",
    "runtime/reference/tensor_accelerator_elementwise.py",
    "runtime/sim/engines/selection.py",
    "tools/build_a3_operator_admission_vectors.py",
    "tools/build_a3_operator_unit_vectors.py",
    "tools/run_a3_operator_admission_rtl_campaign.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_expect.hex",
)
ADMISSION_FILES = (
    "cases.hex",
    "views.hex",
    "descriptors.hex",
    "bank.hex",
    "index.hex",
    "preload.hex",
    "expected.hex",
    "index.json",
)
UNIT_FILES = (
    "silu_cases.hex",
    "silu_gate.hex",
    "silu_up.hex",
    "silu_expected.hex",
    "append_cases.hex",
    "index.json",
)

CASE_RE = re.compile(r"^CASE_SUMMARY (?P<body>.+)$")
GEOMETRY_RE = re.compile(r"^GEOMETRY (?P<body>.+)$")
KV_RE = re.compile(r"(?P<key>[a-z_]+)=(?P<value>\d+)")
PASS_RES = {
    "tb_a3_operator_admission": re.compile(
        r"^PASS a3_operator_admission cases=(?P<cases>\d+) "
        r"positive=(?P<positive>\d+) words=(?P<words>\d+) "
        r"checks=(?P<checks>\d+)$"
    ),
    "tb_a3_vector_silu_mul": re.compile(
        r"^PASS a3_vector_silu_mul cases=(?P<cases>\d+) "
        r"elements=(?P<elements>\d+) checks=(?P<checks>\d+)$"
    ),
    "tb_a3_selection_token_append": re.compile(
        r"^PASS a3_selection_token_append cases=(?P<cases>\d+) "
        r"checks=(?P<checks>\d+)$"
    ),
}
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
            command, cwd=ROOT, capture_output=True, text=True, check=False,
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
    iverilog_name = shutil.which("iverilog")
    vvp_name = shutil.which("vvp")
    verilator = TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator"
    yosys = TOOLS_ROOT / f"yosys-{PINNED_YOSYS_VERSION}/bin/yosys"
    if not iverilog_name or not vvp_name or not verilator.is_file() or not yosys.is_file():
        raise RuntimeError("required pinned RTL tools are unavailable")
    return Path(iverilog_name), Path(vvp_name), verilator, yosys


def plusargs(admission: Path, units: Path) -> list[str]:
    return [
        f"+CASES={admission / 'cases.hex'}",
        f"+VIEWS={admission / 'views.hex'}",
        f"+DESCRIPTORS={admission / 'descriptors.hex'}",
        f"+BANK={admission / 'bank.hex'}",
        f"+INDEX={admission / 'index.hex'}",
        f"+PRELOAD={admission / 'preload.hex'}",
        f"+EXPECTED={admission / 'expected.hex'}",
        f"+SILU_CASES={units / 'silu_cases.hex'}",
        f"+SILU_GATE={units / 'silu_gate.hex'}",
        f"+SILU_UP={units / 'silu_up.hex'}",
        f"+SILU_EXPECTED={units / 'silu_expected.hex'}",
        f"+APPEND_CASES={units / 'append_cases.hex'}",
    ]


def parse_log(top: str, log: str) -> dict[str, Any]:
    cases: list[dict[str, int]] = []
    geometry: dict[str, int] = {}
    passed: dict[str, int] | None = None
    for raw in log.splitlines():
        line = raw.strip()
        match = GEOMETRY_RE.match(line)
        if match:
            geometry = {
                item.group("key"): int(item.group("value"))
                for item in KV_RE.finditer(match.group("body"))
            }
        match = CASE_RE.match(line)
        if match:
            cases.append(
                {
                    item.group("key"): int(item.group("value"))
                    for item in KV_RE.finditer(match.group("body"))
                }
            )
        match = PASS_RES[top].match(line)
        if match:
            passed = {key: int(value) for key, value in match.groupdict().items()}
    if passed is None:
        raise RuntimeError(f"{top}: simulator did not emit the exact PASS marker")
    return {"geometry": geometry, "cases": cases, "pass": passed}


def expected_admission_cases(manifest: dict[str, Any]) -> list[dict[str, int]]:
    return [
        {
            "index": index,
            "fault": int(case["expected"]["fault"]),
            "trap": int(case["expected"]["trap_class"]),
            "writes": int(case["expected"]["write_beats"]),
        }
        for index, case in enumerate(manifest["cases"])
    ]


def observed_admission_cases(rows: list[dict[str, int]]) -> list[dict[str, int]]:
    return [
        {
            "index": row["index"],
            "fault": row["fault"],
            "trap": row["trap"],
            "writes": row["writes"],
        }
        for row in rows
    ]


def validate_admission(result: dict[str, Any], manifest: dict[str, Any]) -> None:
    geometry = manifest["geometry"]
    expected_geometry = {
        "cases": int(manifest["expected_pass"]["cases"]),
        "case_words": int(geometry["case_words"]),
        "view_slots": int(geometry["view_slots"]),
        "view_words": int(geometry["view_words"]),
        "map_entries": int(geometry["map_entries"]),
        "descriptor_records": int(geometry["descriptor_records"]),
        "bank_words": int(geometry["bank_words"]),
        "index_words": int(geometry["index_words"]),
        "expected_words": int(geometry["expected_words"]),
        "preload_words": int(geometry["preload_words"]),
    }
    if result["geometry"] != expected_geometry:
        raise RuntimeError(
            "testbench geometry differs from the vector manifest: "
            f"{result['geometry']} != {expected_geometry}"
        )
    if observed_admission_cases(result["cases"]) != expected_admission_cases(manifest):
        raise RuntimeError("admission case outcomes differ from the manifest")
    for row, case in zip(result["cases"], manifest["cases"], strict=True):
        expected = case["expected"]
        if not expected["fault"]:
            if row["result"] != int(expected["result_count"]):
                raise RuntimeError(f"{case['name']}: result count differs")
            if row["work"] != int(expected["work_count"]):
                raise RuntimeError(f"{case['name']}: work count differs")
        if int(expected["launch"]) == 4:
            if row["token"] != int(expected["token"]):
                raise RuntimeError(f"{case['name']}: selected token differs")
            if row["ties"] != int(expected["tie_multiplicity"]):
                raise RuntimeError(f"{case['name']}: tie multiplicity differs")
        if int(expected["launch"]) == 5:
            if row["token"] != int(expected["token"]):
                raise RuntimeError(f"{case['name']}: appended token differs")
            if row["eos"] != int(expected["eos_reason"]):
                raise RuntimeError(f"{case['name']}: EOS reason differs")
    passed = result["pass"]
    if passed["cases"] != int(manifest["expected_pass"]["cases"]):
        raise RuntimeError("admission case count differs")
    if passed["positive"] != int(manifest["expected_pass"]["positive"]):
        raise RuntimeError("admission positive case count differs")
    if passed["words"] != int(manifest["expected_pass"]["compared_words"]):
        raise RuntimeError("admission compared-word count differs")


def validate_silu(result: dict[str, Any], manifest: dict[str, Any]) -> None:
    geometry = manifest["geometry"]
    if result["geometry"] != {
        "cases": int(geometry["silu_case_count"]),
        "elements": int(geometry["silu_element_count"]),
    }:
        raise RuntimeError("SiLU testbench geometry differs from the manifest")
    for row, case in zip(result["cases"], manifest["silu_cases"], strict=True):
        if row["error"] != int(case["expected_error"]):
            raise RuntimeError(f"{case['name']}: error code differs")
        if row["out"] != int(case["expected_out_count"]):
            raise RuntimeError(f"{case['name']}: retired element count differs")
        if row["work"] != int(case["expected_work_count"]):
            raise RuntimeError(f"{case['name']}: multiply count differs")
        if row["saturations"] != int(case["expected_saturations"]):
            raise RuntimeError(f"{case['name']}: output saturations differ")
        if row["activation_saturations"] != int(
            case["expected_activation_saturations"]
        ):
            raise RuntimeError(f"{case['name']}: activation saturations differ")
    if result["pass"] != {
        "cases": int(geometry["silu_case_count"]),
        "elements": int(geometry["silu_element_count"]),
        "checks": result["pass"]["checks"],
    }:
        raise RuntimeError("SiLU PASS summary differs from the manifest")


def validate_append(result: dict[str, Any], manifest: dict[str, Any]) -> None:
    geometry = manifest["geometry"]
    if result["geometry"] != {"cases": int(geometry["append_case_count"])}:
        raise RuntimeError("token-append testbench geometry differs")
    for row, case in zip(result["cases"], manifest["append_cases"], strict=True):
        for observed, expected, label in (
            (row["error"], case["expected_error"], "error code"),
            (row["capability"], int(case["expected_capability"]), "refusal class"),
            (row["token"], case["expected_token"], "token"),
            (row["eos"], case["expected_eos"], "EOS reason"),
            (row["out"], case["expected_out_count"], "ring writes"),
            (row["appended"], case["expected_appended"], "append count"),
            (row["reads"], case["expected_reads"], "token reads"),
        ):
            if int(observed) != int(expected):
                raise RuntimeError(f"{case['name']}: {label} differs")
    if result["pass"]["cases"] != int(geometry["append_case_count"]):
        raise RuntimeError("token-append case count differs")


VALIDATORS = {
    "tb_a3_operator_admission": ("admission", validate_admission),
    "tb_a3_vector_silu_mul": ("units", validate_silu),
    "tb_a3_selection_token_append": ("units", validate_append),
}


def regenerate_and_compare(temporary: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    python = shutil.which("python3") or "python3"
    manifests: dict[str, dict[str, Any]] = {}
    for builder, directory, files, key in (
        (
            "tools/build_a3_operator_admission_vectors.py",
            ADMISSION_VECTORS,
            ADMISSION_FILES,
            "admission",
        ),
        (
            "tools/build_a3_operator_unit_vectors.py",
            UNIT_VECTORS,
            UNIT_FILES,
            "units",
        ),
    ):
        generated = temporary / key
        process, _ = run(
            [python, str(ROOT / builder), "--output", str(generated)], timeout=3600
        )
        if process.returncode:
            raise RuntimeError(
                f"{builder} failed:\n{process.stdout}\n{process.stderr}"
            )
        for filename in files:
            if (generated / filename).read_bytes() != (directory / filename).read_bytes():
                raise RuntimeError(f"checked-in vector {filename} is not source-current")
        manifests[key] = json.loads((generated / "index.json").read_text())
    return manifests["admission"], manifests["units"]


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
    timing: dict[str, float] = {}
    logs: dict[str, str] = {}
    normalized: dict[str, Any] = {}

    with tempfile.TemporaryDirectory(prefix="a3-operator-admission-") as name:
        temporary = Path(name)
        admission_manifest, unit_manifest = regenerate_and_compare(temporary)
        manifests = {"admission": admission_manifest, "units": unit_manifest}
        arguments = plusargs(ADMISSION_VECTORS, UNIT_VECTORS)

        for bench in BENCHES:
            top = bench["top"]
            manifest_key, validator = VALIDATORS[top]
            sources = [str(ROOT / source) for source in bench["sources"]]

            vvp_output = temporary / f"{top}.vvp"
            process, seconds = run(
                [str(iverilog), "-g2012", "-s", top, "-o", str(vvp_output), *sources],
                timeout=1800,
            )
            timing[f"{top}_iverilog_compile"] = seconds
            if process.returncode:
                raise RuntimeError(
                    f"{top}: Icarus compile failed:\n{process.stdout}\n{process.stderr}"
                )
            process, seconds = run(
                [str(vvp), str(vvp_output), *arguments], timeout=bench["timeout"]
            )
            timing[f"{top}_iverilog_simulation"] = seconds
            iverilog_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(f"{top}: Icarus simulation failed:\n{iverilog_log}")
            iverilog_result = parse_log(top, iverilog_log)
            validator(iverilog_result, manifests[manifest_key])

            verilator_dir = temporary / f"verilator_{top}"
            process, seconds = run(
                [
                    str(verilator), "--binary", "--timing", "--top-module", top,
                    "--Mdir", str(verilator_dir), "-o", "sim", "-Wno-fatal",
                    "-Wno-WIDTHEXPAND", "-Wno-WIDTHTRUNC", "-Wno-MISINDENT",
                    *sources,
                ],
                timeout=1800,
            )
            timing[f"{top}_verilator_compile"] = seconds
            verilator_compile_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(
                    f"{top}: Verilator compile failed:\n{verilator_compile_log}"
                )
            process, seconds = run(
                [str(verilator_dir / "sim"), *arguments], timeout=bench["timeout"]
            )
            timing[f"{top}_verilator_simulation"] = seconds
            verilator_log = process.stdout + process.stderr
            if process.returncode:
                raise RuntimeError(
                    f"{top}: Verilator simulation failed:\n{verilator_log}"
                )
            verilator_result = parse_log(top, verilator_log)
            validator(verilator_result, manifests[manifest_key])

            if iverilog_result != verilator_result:
                raise RuntimeError(f"{top}: Icarus and Verilator results differ")
            normalized[top] = iverilog_result
            logs[f"{top}_iverilog"] = hashlib.sha256(
                iverilog_log.encode()
            ).hexdigest()
            logs[f"{top}_verilator_compile"] = hashlib.sha256(
                verilator_compile_log.encode()
            ).hexdigest()
            logs[f"{top}_verilator"] = hashlib.sha256(
                verilator_log.encode()
            ).hexdigest()

        synthesis: list[dict[str, Any]] = []
        for entry in SYNTHESIS_TOPS:
            script = (
                "read_verilog -sv "
                + " ".join(str(ROOT / source) for source in entry["sources"])
                + f"; hierarchy -check -top {entry['top']}; proc; opt; check; stat"
            )
            process, seconds = run([str(yosys), "-Q", "-p", script], timeout=1800)
            timing[f"{entry['top']}_yosys_elaboration"] = seconds
            yosys_log = process.stdout + process.stderr
            if process.returncode or "Found and reported 0 problems." not in yosys_log:
                raise RuntimeError(f"{entry['top']}: Yosys elaboration failed:\n{yosys_log}")
            synthesis.append({"top": entry["top"], "check_problems": 0})
            logs[f"{entry['top']}_yosys"] = hashlib.sha256(
                yosys_log.encode()
            ).hexdigest()

        source_paths = [
            ROOT / path
            for path in (
                *dict.fromkeys(
                    source for bench in BENCHES for source in bench["sources"]
                ),
                *ORACLE_SOURCES,
            )
        ]
        admitted = admission_manifest["admitted_families"]
        result: dict[str, Any] = {
            "schema": "opentallas.rtl.a3_operator_admission_campaign.v1",
            "status": "pass",
            "abi": {"major": 3, "minor": 0},
            "scope": {
                **admission_manifest["claim_boundary"],
                "dual_simulator": True,
                "synthesizable_elaboration": True,
                "simulator_cycles_are_verification_cost_only": True,
            },
            "admission": {
                "previously_capability_trapped_families": [
                    "DMA.SCATTER",
                    "ATTENTION.GQA",
                    "VECTOR.ADD",
                    "VECTOR.SILU_MUL",
                    "SELECTION.ARGMAX",
                    "SELECTION.TOKEN_APPEND",
                ],
                "admitted_families": admitted,
                "admitted_family_count": len(admitted),
                "governed_program_counters": admission_manifest[
                    "governed_program_counters"
                ],
                "capability_trapped_family_count": 0,
                "still_refused": [
                    "VECTOR.SOFTMAX, checked in this campaign: an opcode with "
                    "no datapath is still a CAPABILITY trap",
                    "any of the six, on an instance that has not bound its "
                    "operand banks: cfg_extended_placement_valid low keeps the "
                    "previous TRAP_CAPABILITY exactly, which is what leaves an "
                    "unwired integration's behaviour unchanged",
                ],
            },
            "aggregate": {
                "admission_case_count": admission_manifest["expected_pass"]["cases"],
                "admission_positive_case_count": admission_manifest[
                    "expected_pass"
                ]["positive"],
                "admission_negative_case_count": admission_manifest[
                    "expected_pass"
                ]["negative"],
                "admission_words_compared": admission_manifest["expected_pass"][
                    "compared_words"
                ],
                "admission_write_beats": admission_manifest["expected_pass"][
                    "write_beats"
                ],
                "silu_case_count": unit_manifest["geometry"]["silu_case_count"],
                "silu_elements_compared": unit_manifest["geometry"][
                    "silu_element_count"
                ],
                "append_case_count": unit_manifest["geometry"]["append_case_count"],
                "checks_per_simulator": sum(
                    int(value["pass"]["checks"]) for value in normalized.values()
                ),
            },
            "contexts_covered": sorted(
                {
                    int(case["context_length"])
                    for case in admission_manifest["cases"]
                    if not case["expected"]["fault"]
                    and case["family"] in (0x10, 0x40)
                }
            ),
            "oracles": admission_manifest["oracles"],
            "unit_oracles": unit_manifest["oracles"],
            "operands": admission_manifest["operands"],
            "normalized": normalized,
            "simulators_agree": True,
            "synthesis_frontend": {
                "tops": synthesis,
                "note": (
                    "generic synthesizable elaboration of the two new datapaths "
                    "only; no library mapping, PPA, token-latency or TPOT claim. "
                    "The whole issue bridge does not elaborate under the pinned "
                    "Yosys 0.68 for a reason that predates this campaign: the "
                    "frontend rejects a non-constant procedural for-loop bound "
                    "in rtl/ot_fp32_rne_pkg.sv reached through "
                    "ot_a3_vector_index_score"
                ),
            },
            "verification_wall_seconds": timing,
            "tools": tools,
            "source_sha256": {
                str(path.relative_to(ROOT)): sha256(path) for path in source_paths
            },
            "vector_sha256": {
                f"a3_operator_admission/{name}": sha256(ADMISSION_VECTORS / name)
                for name in ADMISSION_FILES
            }
            | {
                f"a3_operator_units/{name}": sha256(UNIT_VECTORS / name)
                for name in UNIT_FILES
            },
            "log_sha256": logs,
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
    if value.get("admission", {}).get("admitted_family_count") != 6:
        problems.append("six operator families are not admitted")
    if value.get("admission", {}).get("capability_trapped_family_count") != 0:
        problems.append("a governed family is still capability-trapped")
    if value.get("contexts_covered") != [17, 19]:
        problems.append("the governed decode contexts are not covered")
    for source, expected in value.get("source_sha256", {}).items():
        candidate = ROOT / source
        if not candidate.is_file() or sha256(candidate) != expected:
            problems.append(f"source drift: {source}")
    for name, expected in value.get("vector_sha256", {}).items():
        candidate = ROOT / "testdata/rtl" / name
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
        "ABI3 operator-admission RTL campaign "
        f"status={result['status']} "
        f"families={result['admission']['admitted_family_count']} "
        f"words={result['aggregate']['admission_words_compared']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
