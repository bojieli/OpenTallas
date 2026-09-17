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

# One campaign per Qwen lowering.  The bridge, the datapaths and the unit
# benches are identical; the descriptor records the bridge is driven with are
# not, so each storage class gets its own vector set, its own simulation and
# its own artifact.  ``rom`` keeps the original paths so every artifact that
# already binds them stays valid.
DEFAULT_STORAGE_CLASS = "rom"


def admission_vectors_for(storage_class: str) -> Path:
    if storage_class == DEFAULT_STORAGE_CLASS:
        return ADMISSION_VECTORS
    return ROOT / f"testdata/rtl/a3_operator_admission_{storage_class}"


def output_for(storage_class: str) -> Path:
    if storage_class == DEFAULT_STORAGE_CLASS:
        return DEFAULT_OUTPUT
    return ROOT / f"results/rtl/a3_operator_admission_{storage_class}_campaign.json"
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
    "rtl/proto/ot_mac_bf16_fp32_pipe.sv",
    "rtl/abi3/ot_a3_mac_lane_pipe.sv",
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
    "rtl/abi3/ot_a3_rope_lane_pipe.sv",
    "rtl/abi3/ot_a3_vector_rope.sv",
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
    "rtl/proto/ot_fp32_add_rne_pipe.sv",
    "rtl/abi3/ot_a3_route_weight_normalize.sv",
    "rtl/abi3/ot_a3_route_window_index.sv",
    "rtl/abi3/ot_a3_route_biased_topk.sv",
    "rtl/proto/ot_fp32_mul_rne_pipe.sv",
    "rtl/abi3/ot_a3_reduction_expert_sum.sv",
    "rtl/abi3/ot_a3_place_table.sv",
    #: ATTENTION.SPARSE and the eight parts it composes. The bridge
    #: instantiates the engine, so every list that elaborates the bridge
    #: needs them -- a missing entry is not a missing test, it is a
    #: MODMISSING at elaboration and a campaign that cannot run at all.
    "rtl/abi3/ot_a3_fp32_exp_pos_cr_rne.sv",
    "rtl/abi3/ot_a3_reduction_balanced_sum.sv",
    "rtl/abi3/ot_a3_attention_kv_index.sv",
    "rtl/abi3/ot_a3_attention_softmax_block.sv",
    "rtl/abi3/ot_a3_attention_denominator.sv",
    "rtl/abi3/ot_a3_attention_epilogue.sv",
    "rtl/abi3/ot_a3_attention_qk_walk.sv",
    "rtl/abi3/ot_a3_attention_av_walk.sv",
    "rtl/abi3/ot_a3_attention_sparse.sv",
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
        # HOST WALL-CLOCK BUDGET, not a check and not a tolerance.  Every
        # comparison this campaign makes is unchanged: both pinned simulators
        # still run every case and their normalized results must still be
        # equal.  What changed is the WORK.  958071e added the layer-zero key
        # and value projections -- two real TENSOR.MATMULs of 20,972,560
        # simulated cycles each, against the checkpoint's own k_proj and
        # v_proj -- to a bench whose whole previous case list cost Icarus
        # 845.5 s, the figure the retained pre-958071e artifact records in
        # its own verification_wall_seconds.  5,400 s was chosen for that
        # bench and is too small for this one, and that is measured rather
        # than assumed: on 2026-09-08 ONE of the two projection cases ran
        # past 2,784 s under Icarus without finishing, while the same widened
        # bench completes under Verilator in 311 s -- and the 43.2x
        # Icarus/Verilator ratio the retained artifact records for this same
        # bench pair (845.5 / 19.6) projects 13,435 s for the Icarus leg.
        # 28,800 s is that projection with 2.1x headroom for a loaded box.
        # Section 11.7 records what NOT raising it cost: the campaign could
        # not be re-taken at all, so the placement depth it measures stayed
        # an unreproducible number and the two rungs that read it fell back
        # to the integrated vehicle's own span of 13 objects.
        "timeout": 28800,
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
    "runtime/reference/tensor_accelerator_rmsnorm.py",
    "runtime/reference/tensor_accelerator_rope.py",
    "runtime/sim/engines/selection.py",
    "tools/build_a3_operator_admission_vectors.py",
    "tools/build_a3_operator_unit_vectors.py",
    "tools/run_a3_operator_admission_rtl_campaign.py",
    "testdata/compiler/abi3_deployment/abi3_deployment_rtl_vectors.json",
    "testdata/compiler/abi3_deployment/a3_descriptor.hex",
    "testdata/compiler/abi3_deployment/a3_program.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_expect.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_writes.hex",
    "testdata/compiler/abi3_shipped_prefix/p3_source.hex",
)
ADMISSION_FILES = (
    "cases.hex",
    "views.hex",
    "descriptors.hex",
    "bank.hex",
    "index.hex",
    "source.hex",
    "preload.hex",
    "expected.hex",
    # The projection-matrix image.  It is regenerated and byte-compared here
    # exactly like the committed images; it is simply not committed, because
    # it is 8,388,608 checkpoint codes and is re-derived deterministically
    # from the pinned checkpoint the deployment names.
    "weights.hex",
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
        f"+SOURCE={admission / 'source.hex'}",
        f"+PRELOAD={admission / 'preload.hex'}",
        f"+WEIGHTS={admission / 'weights.hex'}",
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
        "map_base": int(geometry["map_base"]),
        "descriptor_records": int(geometry["descriptor_records"]),
        "bank_words": int(geometry["bank_words"]),
        "index_words": int(geometry["index_words"]),
        "source_words": int(geometry["source_words"]),
        "expected_words": int(geometry["expected_words"]),
        "preload_words": int(geometry["preload_words"]),
        "weight_words": int(geometry["weight_words"]),
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


# The six families the bridge answered with TRAP_CAPABILITY before this
# campaign existed, as the (family, subopcode) pairs the vector manifest
# reports.  The campaign now also issues four object-keyed families the bridge
# already admitted -- they are here to bind and resolve objects the six never
# name -- so "admitted" is a larger set than "no longer trapped", and the two
# are kept apart rather than merged into one growing count.
PREVIOUSLY_CAPABILITY_TRAPPED = (
    {"family": 0x10, "sub": 0x03},  # DMA.SCATTER
    {"family": 0x30, "sub": 0x03},  # VECTOR.ADD
    {"family": 0x30, "sub": 0x04},  # VECTOR.SILU_MUL
    {"family": 0x40, "sub": 0x01},  # ATTENTION.GQA
    {"family": 0x70, "sub": 0x00},  # SELECTION.ARGMAX
    {"family": 0x70, "sub": 0x01},  # SELECTION.TOKEN_APPEND
)

BRIDGE = ROOT / "rtl/abi3/ot_a3_engine_issue_bridge.sv"
ADMISSION_TOP = ROOT / "rtl/test/tb_a3_operator_admission.sv"


def placement_measurement(
    result: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    """How deep a placement table this run actually bound AND resolved.

    The bridge places every operand and every result of every family through
    one object table, so the capacity question a transformer layer asks is not
    per role: it is how many distinct objects ONE binding of that table can
    name at once.  This counts it from the run, and only from the run.

    A group is a set of cases carrying byte-identical table contents, so every
    object in it was resident at every one of that group's resolutions.  An
    object is counted only when it is (a) bound in that group's table and (b)
    named by an operand or result view of a case in the group that the
    simulator reported as issued with no fault, with the write-beat count the
    vector set declared, and whose whole result region was then compared word
    by word against the expectation at its own address.  An entry no operand
    named is bound and NOT counted: a table can be filled with anything, and
    filling it is not evidence that the design resolved it.
    """

    rows = {int(row["index"]): row for row in result["cases"]}
    groups: dict[tuple[tuple[int, int], ...], list[tuple[int, dict[str, Any]]]] = {}
    for index, case in enumerate(manifest["cases"]):
        key = tuple(
            sorted((int(key), int(value)) for key, value in case["object_map"].items())
        )
        groups.setdefault(key, []).append((index, case))

    best: dict[str, Any] | None = None
    for key, members in groups.items():
        bound = {object_id for object_id, _ in key}
        resolved: set[int] = set()
        credited: list[str] = []
        for index, case in members:
            row = rows.get(index)
            expected = case["expected"]
            if (
                row is None
                or row["fault"]
                or row["trap"]
                or not case["placement_valid"]
                or int(expected["compare_count"]) <= 0
                or row["writes"] != int(expected["write_beats"])
                or row["result"] != int(expected["result_count"])
            ):
                continue
            resolved |= {int(value) for value in case["objects_named"]}
            credited.append(case["name"])
        counted = sorted(resolved & bound)
        record = {
            "cases_credited": credited,
            "measured_simultaneous_objects": len(counted),
            "objects_bound": sorted(bound),
            "objects_resolved_and_compared": counted,
            "table_entries_bound": len(bound),
        }
        if (
            best is None
            or record["measured_simultaneous_objects"]
            > best["measured_simultaneous_objects"]
        ):
            best = record
    if best is None:
        raise RuntimeError("the admission run carried no case to measure")
    return {
        "bridge": str(BRIDGE.relative_to(ROOT)),
        "bridge_sha256": sha256(BRIDGE),
        "definition": (
            "the largest number of distinct ABI objects one byte-identical "
            "binding of the bridge's object table held while the design "
            "resolved every one of them, on cases that issued without fault, "
            "wrote the declared number of beats and had their whole result "
            "region compared word by word at its own address"
        ),
        "simulators": ["iverilog", "verilator"],
        "vector_format_entries": int(manifest["geometry"]["map_entries"]),
        "vector_format_entries_note": (
            "how many entries the CASE RECORD can carry, echoed by the run's "
            "own GEOMETRY line and checked against the vector manifest. It is "
            "a bound on the measurement below, never a substitute for it"
        ),
        "vehicle": str(ADMISSION_TOP.relative_to(ROOT)),
        "vehicle_sha256": sha256(ADMISSION_TOP),
        **best,
    }


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


def regenerate_and_compare(
    temporary: Path, storage_class: str = DEFAULT_STORAGE_CLASS
) -> tuple[dict[str, Any], dict[str, Any]]:
    python = shutil.which("python3") or "python3"
    manifests: dict[str, dict[str, Any]] = {}
    for builder, directory, files, key, extra in (
        (
            "tools/build_a3_operator_admission_vectors.py",
            admission_vectors_for(storage_class),
            ADMISSION_FILES,
            "admission",
            ["--storage-class", storage_class],
        ),
        (
            "tools/build_a3_operator_unit_vectors.py",
            UNIT_VECTORS,
            UNIT_FILES,
            "units",
            [],
        ),
    ):
        generated = temporary / key
        process, _ = run(
            [python, str(ROOT / builder), "--output", str(generated), *extra],
            timeout=3600,
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


def campaign(
    output: Path, storage_class: str = DEFAULT_STORAGE_CLASS
) -> dict[str, Any]:
    admission_vectors = admission_vectors_for(storage_class)
    admission_prefix = admission_vectors.name
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
        admission_manifest, unit_manifest = regenerate_and_compare(
            temporary, storage_class
        )
        manifests = {"admission": admission_manifest, "units": unit_manifest}
        arguments = plusargs(admission_vectors, UNIT_VECTORS)
        # Geometry belongs to the vector set, not the testbench: the ROM
        # admission set carries 218 descriptor records and the HBM set 224.
        # The manifest's own numbers are passed in and the GEOMETRY line the
        # run prints back is checked against the same manifest, so a
        # disagreement is a refusal rather than a silently resized array.
        geometry = admission_manifest["geometry"]
        admission_overrides = {
            "CASE_COUNT": int(admission_manifest["expected_pass"]["cases"]),
            "DESC_RECORDS": int(geometry["descriptor_records"]),
            "BANK_WORDS": int(geometry["bank_words"]),
            "SOURCE_WORDS": int(geometry["source_words"]),
            "EXPECTED_WORDS": int(geometry["expected_words"]),
            "PRELOAD_WORDS": int(geometry["preload_words"]),
            "WEIGHT_WORDS": int(geometry["weight_words"]),
        }

        for bench in BENCHES:
            top = bench["top"]
            manifest_key, validator = VALIDATORS[top]
            sources = [str(ROOT / source) for source in bench["sources"]]
            overrides = (
                admission_overrides if top == "tb_a3_operator_admission" else {}
            )
            iverilog_parameters = [
                f"-P{top}.{name}={value}" for name, value in overrides.items()
            ]
            verilator_parameters = [
                f"-G{name}={value}" for name, value in overrides.items()
            ]

            vvp_output = temporary / f"{top}.vvp"
            process, seconds = run(
                [
                    str(iverilog), "-g2012", "-s", top, "-o", str(vvp_output),
                    *iverilog_parameters, *sources,
                ],
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
                    *verilator_parameters, *sources,
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
        previously_trapped = [dict(entry) for entry in PREVIOUSLY_CAPABILITY_TRAPPED]
        missing = [entry for entry in previously_trapped if entry not in admitted]
        if missing:
            raise RuntimeError(
                "the campaign issues no positive case for the previously "
                f"capability-trapped families {missing}"
            )
        object_keyed = [entry for entry in admitted if entry not in previously_trapped]
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
                "previously_capability_trapped_families_admitted": previously_trapped,
                "previously_capability_trapped_family_count": len(previously_trapped),
                "object_keyed_families_also_issued": object_keyed,
                "object_keyed_families_note": (
                    "families outside the six, issued here because they "
                    "resolve their operands through the SAME object table the "
                    "six mapped families use and name objects the six never "
                    "do; the placement block below is what they are for.  "
                    "TENSOR.MATMUL and the two head-span forms were already "
                    "admitted; the BF16 dense-row DMA.GATHER was not, and its "
                    "admission is the one predicate this campaign widened"
                ),
                "governed_program_counters": admission_manifest[
                    "governed_program_counters"
                ],
                "capability_trapped_family_count": 0,
                "still_refused": [
                    "VECTOR.SOFTMAX, checked in this campaign: an opcode with "
                    "no datapath is still a CAPABILITY trap",
                    "PC 68's DMA.GATHER is NO LONGER refused: it was, on a "
                    "dense-row source dtype pinned to FP32 by the one "
                    "gather the predicate had been written against, and it "
                    "is issued as a passing case in this campaign now",
                    "the three MLP projections of the governed layer, PCs 50, "
                    "53 and 59, are NO LONGER REFUSED and are no longer checked "
                    "here.  They were, on an admitted TENSOR.MATMUL weight view "
                    "of [n <= 4096, 4096] against their [12288, 4096], "
                    "[12288, 4096] and [4096, 12288]; f6afec5 raised that bound "
                    "to desc_view_dim0 <= 65535 so the reduced decode\'s head "
                    "could run unpartitioned, which put all three inside it.  "
                    "The three refusal cases were retired rather than repaired: "
                    "they cannot become passing cases without staging a "
                    "12,288 x 4,096 projection this vehicle does not carry -- "
                    "50.3 x 10^6 MACs against the admitted pair\'s 4.2 -- and "
                    "they cannot be re-aimed past 65,535 because a case\'s "
                    "weight dims come from the deployment\'s own descriptor "
                    "records and no shipped operator declares one above it.  "
                    "The consequence is that NOTHING IN THIS CAMPAIGN NOW "
                    "EXERCISES THE MATMUL WEIGHT-ROW BOUND, which the vector "
                    "manifest records as uncovered_after_bound_change",
                    "any of the six, on an instance that has not bound its "
                    "operand banks: cfg_extended_placement_valid low keeps the "
                    "previous TRAP_CAPABILITY exactly, which is what leaves an "
                    "unwired integration's behaviour unchanged",
                ],
            },
            "placement": placement_measurement(
                normalized["tb_a3_operator_admission"], admission_manifest
            ),
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
            "storage_class": storage_class,
            "target": admission_manifest["target"],
            "deployment_sha256": admission_manifest["deployment_sha256"],
            "vector_sha256": {
                f"{admission_prefix}/{name}": sha256(admission_vectors / name)
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
    admission = value.get("admission", {})
    if admission.get("previously_capability_trapped_family_count") != 6:
        problems.append("six operator families are not admitted")
    if [
        entry
        for entry in (dict(item) for item in PREVIOUSLY_CAPABILITY_TRAPPED)
        if entry not in (admission.get("admitted_families") or [])
    ]:
        problems.append("a previously capability-trapped family has no case")
    if value.get("admission", {}).get("capability_trapped_family_count") != 0:
        problems.append("a governed family is still capability-trapped")
    placement = value.get("placement") or {}
    if not isinstance(placement.get("measured_simultaneous_objects"), int) or (
        placement["measured_simultaneous_objects"] <= 0
    ):
        problems.append("the retained campaign measures no placement depth")
    elif placement["measured_simultaneous_objects"] > placement.get(
        "table_entries_bound", 0
    ):
        problems.append(
            "the measured placement depth exceeds the table the run bound"
        )
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
    result.add_argument("--output", type=Path, default=None)
    result.add_argument(
        "--storage-class",
        choices=["rom", "hbm"],
        default=DEFAULT_STORAGE_CLASS,
        help=(
            "which Qwen lowering to drive the bridge with.  Evidence measured "
            "on one lowering is not evidence about the other: their governed "
            "descriptor ids are disjoint and their DMA.SCATTER numeric "
            "profiles disagree under one contract digest."
        ),
    )
    return result


def main() -> int:
    args = parser().parse_args()
    output = args.output or output_for(args.storage_class)
    result = campaign(output, args.storage_class)
    print(
        "ABI3 operator-admission RTL campaign "
        f"storage_class={args.storage_class} "
        f"target={result['target']} "
        f"status={result['status']} "
        f"families={result['admission']['admitted_family_count']} "
        f"words={result['aggregate']['admission_words_compared']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
