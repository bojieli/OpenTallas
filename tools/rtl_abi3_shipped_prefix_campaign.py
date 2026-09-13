#!/usr/bin/env python3
"""Run the focused ABI 3.0 shipped-prefix integration witness.

The complete source-bound Qwen layer-zero query/key/value MATMUL family, the
two descriptor-sized query/key head RMSNorm operations, and both whole-head
RoPE operations are intentionally executed under Verilator.  Interpreted
Icarus needs several hours for these single-lane MATMUL launches, so this
campaign does not imply that Icarus ran the complete integrated transaction.
Instead it fail-closed binds the unchanged ``ot_a3_mac_lane`` and qualified
RoPE sources to their retained dual-simulator qualifications and records that
evidence as compositional, not integrated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import resource
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
VECTOR_JSON = VECTOR_DIR / "abi3_shipped_prefix_vectors.json"
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"
ENGINE_CAMPAIGN = ROOT / "results/rtl/abi3_engine_campaign.json"
ROPE_CAMPAIGN = ROOT / "results/tensor_accelerator/qwen3_rtl_rope_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
# The integrated replay's check count.  It is a function of the harness AND of
# the vector set, so it moves whenever either does, and it is arithmetic here
# rather than a re-typed measurement: 189,826 was the count before the six
# mapped operator families were observed, and the harness now adds nine checks
# per case -- the six per-family launch counts plus the selected token, its tie
# multiplicity and its EOS reason -- over four cases.  A vector set that
# carries mapped placement adds one more check per mapped case (its reserved
# word), so this constant has to be re-measured, not adjusted by hand, when
# the case-record generation changes.
# The checks the harness makes that do NOT scale with the words the run
# produces: the per-case control and admission comparisons and the run-wide
# totals.  It is the only literal here, and it is the residue of the previous
# generation's own literal: that campaign expected 189,862 checks over a run
# whose word-scaled checks were 91,136 (per-case image) + 91,136 (final image)
# + 7,168 (unwritten tail) = 189,440, leaving 422.  Everything else is derived
# from the vector set below, so a run that compares a different number of
# WORDS than the vector set declares is refused by arithmetic rather than by a
# number somebody remembered to update.
STRUCTURAL_INTEGRATED_CHECKS = 189_862 - 189_440
#: The case count the residue above was MEASURED at.  The residue is not
#: case-independent: the comment above says the harness adds nine checks per
#: case -- six per-family launch counts plus the selected token, its tie
#: multiplicity and its EOS reason -- and those 36 are inside the 422.  So a
#: vector set with a fifth case (WP-L adds the V4.1 wafer entrypoint) does NOT
#: get +9 assumed here: the residue is re-measured from a run and this number
#: moves with it.  Guessing the delta would put a fabricated check count in an
#: acceptance comparison, which is worse than refusing.
STRUCTURAL_CHECKS_MEASURED_AT_CASES = 4
#: Where a V4.1 run is recorded, plan section 13 WP-L.  It is a separate file
#: rather than an overwrite because the Qwen/V4 record is the evidence for a
#: different set of targets; --output selects it.
V41_OUTPUT = ROOT / "results/rtl/abi3_shipped_prefix_campaign_v41.json"


def expected_integrated_checks(vectors: dict[str, Any]) -> int:
    """How many checks a correct run of THIS vector set must report.

    Results are placed by object, so three different word counts appear and
    they are not interchangeable:

      * ``result_word_count`` -- the words the engines WRITE.  Each is
        compared twice against the golden write stream, by address and by
        value, as it commits.
      * the per-case ``result_region_span`` -- the words the retained image
        HOLDS.  Smaller than the writes by exactly what a rewritten buffer
        gives up.  Compared once per case and once over the whole image.
      * the result bank's declared size -- everything above the image has to
        read back unwritten.

    Plus one consumed-count check per case and one for the whole run.
    """
    case_count = len(vectors["cases"])
    if case_count != STRUCTURAL_CHECKS_MEASURED_AT_CASES:
        raise SystemExit(
            f"the vector set carries {case_count} cases and "
            f"STRUCTURAL_INTEGRATED_CHECKS was measured at "
            f"{STRUCTURAL_CHECKS_MEASURED_AT_CASES}. The residue is per-case "
            "(nine harness checks per case sit inside it), so it has to be "
            "re-measured from a run of THIS vector set -- run the campaign, read "
            "the checks= the harness printed, subtract the word-scaled terms "
            "this function computes, and set the constant to the difference. "
            "Do not add nine per case by hand: the delta is a property of the "
            "harness, and a fabricated check count in an acceptance comparison "
            "is worse than a refusal."
        )
    writes = int(vectors["result_word_count"])
    span = sum(
        int(case["bank_mapping"]["result_region_span"]) for case in vectors["cases"]
    )
    image = int(vectors["retained_image_word_count"])
    if span != image:
        raise SystemExit(
            f"the cases allocate {span} result words and the vector set "
            f"declares a retained image of {image}"
        )
    result_words = int(vectors["geometry"]["result_words"])
    if image > result_words:
        raise SystemExit("the retained image does not fit the result bank")
    return (
        STRUCTURAL_INTEGRATED_CHECKS
        + 2 * writes                      # every write: address and value
        + len(vectors["cases"])           # each case consumed its own writes
        + 1                               # the run consumed the whole stream
        + image                           # the retained image, per case
        + image                           # the retained image, whole run
        + (result_words - image)          # and nothing above it was written
    )
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/ot_ta_command_decoder.sv",
    "rtl/ot_ta_rope_bf16_sram_engine.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_program_header.sv",
    "rtl/abi3/ot_a3_shared_divider.sv",
    "rtl/abi3/ot_a3_symbol_file.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_resolver_bank.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_issue_record_store.sv",
    "rtl/abi3/ot_a3_dependence_table.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
    "rtl/abi3/ot_a3_device_top.sv",
    "rtl/abi3/ot_a3_mac_lane.sv",
    #: The pipelined TENSOR lane and the qualified MAC it is built from.
    #: ot_a3_engine_array routes BF16 x BF16 unscaled MATMUL descriptors to the
    #: pipelined lane and everything else to ot_a3_mac_lane, so both are compiled.
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
    # The datapaths of the six operator families the issue bridge admits in
    # addition to the original seven.  They are listed here because the bridge
    # instantiates them unconditionally: an instance that has not bound its
    # operand banks refuses those families at issue with the same
    # TRAP_CAPABILITY it always gave, but the modules still have to elaborate.
    "rtl/abi3/ot_a3_fp32_div_rne.sv",
    "rtl/abi3/ot_a3_fp32_transcendental_cr_rne.sv",
    "rtl/abi3/ot_a3_qwen_gqa.sv",
    "rtl/abi3/ot_a3_vector_silu_mul.sv",
    "rtl/abi3/ot_a3_selection_token_append.sv",
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
)
TEST_SOURCES = (
    "rtl/test/a3_engine_completion_adapter.sv",
    "rtl/test/a3_shipped_prefix_top.sv",
    "rtl/test/a3_shipped_prefix_harness.cpp",
)
CONTRACT_SOURCES = (
    "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md",
    "runtime/abi3/constants.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/records.py",
    "runtime/abi3/deployment.py",
    "runtime/sim/memory.py",
    "runtime/sim/generators.py",
    "runtime/sim/engines/dma.py",
    "runtime/sim/formats.py",
    "runtime/reference/tensor_accelerator_rmsnorm.py",
    "runtime/reference/tensor_accelerator_rope.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/rope.py",
    "docs/TENSOR_ACCELERATOR_ABI_3_OPERATOR_CONVENTIONS.md",
)
TOOL_SOURCES = (
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/build_abi3_shipped_prefix_vectors.py",
    "tools/rtl_abi3_shipped_prefix_campaign.py",
)
DEPLOYMENT_IMAGES = (
    "a3_program.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
)
VECTOR_FILES = (
    "p3_case.hex",
    "p3_issue.hex",
    "p3_index.hex",
    "p3_source.hex",
    "p3_expect.hex",
    "p3_writes.hex",
    "p3_meta.hex",
)

CASE_RE = re.compile(
    r"^CASE (?P<index>\d+) OK launches=(?P<launches>\d+) "
    r"words=(?P<words>\d+) responses=(?P<responses>\d+) "
    r"trap=(?P<trap>\d+) fault=(?P<fault>\d+) "
    r"fetched=(?P<fetched>\d+) retired=(?P<retired>\d+) "
    r"issued=(?P<issued>\d+) views=(?P<views>\d+)$",
    re.MULTILINE,
)
CHECKS_RE = re.compile(r"checks=(\d+)")
VERILATOR_VERSION_RE = re.compile(r"Verilator (\d+)\.(\d+)")

# The six operator families rtl/abi3/ot_a3_engine_issue_bridge.sv admits in
# addition to the original seven, in the order the harness prints them.  Which
# of them THIS vehicle reached is a measurement, taken from the run log: the
# harness counts a family only when the bridge launched it and the case it
# launched in compared its result words against golden.  A family with no
# launch is trapped here, whatever another vehicle measured, and the absence of
# the line altogether is six trapped families rather than an unknown.
MAPPED_FAMILIES = (
    "VECTOR.ADD",
    "VECTOR.SILU_MUL",
    "DMA.SCATTER",
    "ATTENTION.GQA",
    "SELECTION.ARGMAX",
    "SELECTION.TOKEN_APPEND",
)
ADMISSION_RE = re.compile(
    r"^ADMISSION vectors=(?P<vectors>\w+) "
    r"cases_with_placement=(?P<cases_with_placement>\d+) "
    r"injecting=(?P<injecting>\d+) "
    r"(?P<counts>.*?) reached=(?P<reached>\d+) trapped=(?P<trapped>\d+)$",
    re.MULTILINE,
)


def parse_admission(log: str) -> dict[str, Any]:
    """The integrated vehicle's own answer for the six mapped families.

    Absence of the marker is not "not evaluable": it is six families this
    vehicle did not reach, which is what the rung must then report.
    """
    match = ADMISSION_RE.search(log)
    if match is None:
        return {
            "measured": False,
            "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
            "why_not_measured": (
                "the integrated run emitted no ADMISSION line, so no family "
                "was observed to launch in this vehicle"
            ),
            "launches": {family: 0 for family in MAPPED_FAMILIES},
            "reached_families": [],
            "trapped_families": list(MAPPED_FAMILIES),
            "reached_family_count": 0,
            "capability_trapped_family_count": len(MAPPED_FAMILIES),
        }
    counts = dict(
        pair.split("=", 1) for pair in match.group("counts").split() if "=" in pair
    )
    launches = {family: int(counts.get(family, 0)) for family in MAPPED_FAMILIES}
    reached = [family for family, count in launches.items() if count != 0]
    trapped = [family for family in MAPPED_FAMILIES if family not in reached]
    record = {
        "measured": True,
        "vehicle": "rtl/test/a3_shipped_prefix_top.sv",
        "vector_generation": match.group("vectors"),
        "cases_with_mapped_placement": int(match.group("cases_with_placement")),
        "result_injection": int(match.group("injecting")) != 0,
        "launches": launches,
        "reached_families": reached,
        "trapped_families": trapped,
        "reached_family_count": len(reached),
        "capability_trapped_family_count": len(trapped),
    }
    if len(reached) != int(match.group("reached")) or len(trapped) != int(
        match.group("trapped")
    ):
        raise SystemExit("the ADMISSION line disagrees with its own counts")
    return record


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_identity() -> dict[str, Any]:
    """The commit the artifact was produced at, and whether the tree was clean.

    Recorded beside the source digests, not instead of them: the digests bind
    the artifact to its inputs, the commit says where those inputs came from.
    """
    def run(args: list[str]) -> str:
        try:
            result = subprocess.run(
                args, cwd=ROOT, capture_output=True, text=True, check=False
            )
        except OSError:
            return ""
        return result.stdout if result.returncode == 0 else ""

    head = run(["git", "rev-parse", "HEAD"]).strip()
    status = run(["git", "status", "--porcelain"]).strip()
    return {"commit": head or None, "worktree_dirty": bool(status)}


def canonical(text: str, build: Path) -> str:
    return (
        text.replace(str(build), "<BUILD>")
        .replace(str(ROOT), "<ROOT>")
        .replace(str(Path.home()), "<HOME>")
    )


def resolve(name: str, pinned: Path | None) -> Path:
    override = os.environ.get(f"OPENTALLAS_{name.upper()}")
    if override:
        return Path(override)
    if pinned is not None and pinned.exists():
        return pinned
    found = shutil.which(name)
    if found is None:
        raise SystemExit(f"required tool is unavailable: {name}")
    return Path(found)


def tool_record(executable: Path, version_args: list[str]) -> dict[str, str]:
    result = subprocess.run(
        [str(executable), *version_args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=60,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return {
        "executable": canonical(str(executable.resolve()), ROOT),
        "executable_sha256": sha256_file(executable.resolve()),
        "version": lines[0] if lines else "no version text",
    }


def require_versions(tools: dict[str, dict[str, str]]) -> None:
    match = VERILATOR_VERSION_RE.search(tools["verilator"]["version"])
    if match is None or (int(match.group(1)), int(match.group(2))) < (5, 50):
        raise SystemExit(f"Verilator {PINNED_VERILATOR_VERSION} or newer is required")


def load_lane_qualification() -> dict[str, Any]:
    """Bind the unchanged MAC lane to its retained dual-simulator evidence."""

    if not ENGINE_CAMPAIGN.is_file():
        raise SystemExit(f"missing compositional lane evidence: {ENGINE_CAMPAIGN}")
    body = json.loads(ENGINE_CAMPAIGN.read_text(encoding="utf-8"))
    source_path = "rtl/abi3/ot_a3_mac_lane.sv"
    source_sha256 = sha256_file(ROOT / source_path)
    blocked_limit = (
        body.get("claim_boundary", {})
        .get("does_not_establish", {})
        .get("blocked_contraction_contract")
    )
    expected_simulators = ["iverilog_vvp", "verilator_cpp_executable"]
    expected_checks = {"iverilog": 40_878, "verilator": 40_878}
    if (
        body.get("schema") != "opentallas.rtl.abi3_engine_campaign.v1"
        or body.get("status") != "pass"
        or body.get("evidence_class") != "public_open_tool_rtl_simulation"
        or body.get("simulators_counted") != expected_simulators
        or body.get("checks_per_simulator") != expected_checks
        or body.get("source_sha256", {}).get(source_path) != source_sha256
        or body.get("correlation", {}).get("mac_count") != 59_868
        or not isinstance(blocked_limit, str)
        or "only bf16_bf16_fp32_sequential_rne_v1 is correlated" not in blocked_limit
    ):
        raise SystemExit("the retained dual-simulator MAC-lane qualification changed")
    return {
        "artifact": str(ENGINE_CAMPAIGN.relative_to(ROOT)),
        "artifact_sha256": sha256_file(ENGINE_CAMPAIGN),
        "schema": body["schema"],
        "status": body["status"],
        "evidence_class": body["evidence_class"],
        "simulators_counted": expected_simulators,
        "checks_per_simulator": expected_checks,
        "qualified_mac_count": 59_868,
        "lane_source": source_path,
        "lane_source_sha256": source_sha256,
        "qualification_contract": "bf16_bf16_fp32_sequential_rne_v1",
        "blocked_contract_limit": blocked_limit,
        "composition_boundary": (
            "the exact shipped blocked-contract operation declares the same "
            "single-lane ascending-K arithmetic association and executes it "
            "completely in the integrated Verilator replay; the retained "
            "Icarus evidence qualifies that unchanged lane arithmetic on its "
            "bounded sequential-contract vectors, not the full shipped "
            "program, exact query/key/value shapes, or blocked descriptors"
        ),
    }


def load_rope_qualification() -> dict[str, Any]:
    """Bind the unchanged fused RoPE core to retained dual-simulator evidence."""

    if not ROPE_CAMPAIGN.is_file():
        raise SystemExit(f"missing compositional RoPE evidence: {ROPE_CAMPAIGN}")
    body = json.loads(ROPE_CAMPAIGN.read_text(encoding="utf-8"))
    source_path = "rtl/ot_ta_rope_bf16_sram_engine.sv"
    source_sha256 = sha256_file(ROOT / source_path)
    program = body.get("program_correlation", {})
    arithmetic = body.get("arithmetic_evidence", {})
    boundary = body.get("claim_boundary", {})
    simulator_cases = body.get("cases", [])
    if (
        body.get("schema") != "opentallas.tensor_accelerator.qwen_rtl_rope_campaign.v1"
        or body.get("status") != "pass"
        or body.get("simulators") != ["iverilog", "verilator"]
        or [case.get("status") for case in simulator_cases] != ["pass", "pass"]
        or body.get("source_sha256", {}).get(source_path) != source_sha256
        or not arithmetic.get("exact_scalar_all_elements")
        or not boundary.get("dual_simulator_complete_operations")
        or not boundary.get("complete_rope_graph_operation")
        or program.get("verified_position_count") != 2
        or len(program.get("position_cases", [])) != 2
        or program["position_cases"][0].get("position") != 0
        or program["position_cases"][1].get("position") != 7999
        or program.get("element_count") != 5_120
        or program.get("multiplication_count") != 10_240
        or program.get("addition_count") != 5_120
    ):
        raise SystemExit("the retained dual-simulator RoPE qualification changed")
    return {
        "artifact": str(ROPE_CAMPAIGN.relative_to(ROOT)),
        "artifact_sha256": sha256_file(ROPE_CAMPAIGN),
        "schema": body["schema"],
        "status": body["status"],
        "simulators_counted": body["simulators"],
        "qualified_positions": [0, 7999],
        "qualified_element_count_per_position": 5_120,
        "qualified_multiplication_count_per_position": 10_240,
        "qualified_addition_count_per_position": 5_120,
        "core_source": source_path,
        "core_source_sha256": source_sha256,
        "qualification_contract": "qwen3_rope_fp32_bf16_v1",
        "composition_boundary": (
            "the ABI 3.0 adapter narrows each declared FP32 coefficient to "
            "BF16 RNE and presents one declared query or key tensor to the "
            "unchanged fused core while the inactive side is internal zero; "
            "the retained Icarus-plus-Verilator campaign qualifies that core "
            "at positions 0 and 7999, while the integrated Verilator replay "
            "checks every position-16 result from the real ABI descriptors"
        ),
    }


def elaboration_geometry(vectors: dict[str, Any]) -> list[str]:
    """The -G flags the vector set itself demands of the top.

    The campaign used to elaborate ``ot_a3_shipped_prefix_top`` at its RTL
    defaults and pass no ``-G`` at all, which made the run correct only while
    the defaults happened to equal the geometry the vector set was built for.
    They are not the same statement, and the harness proves it: it compares
    ``meta[7]`` -- the vector set's declared result memory -- against the size
    the top reports through ``ot_a3_geometry_declare``.  The vector set is the
    source of truth for its own geometry, so the campaign reads it from there
    and elaborates to it.  A ladder rung whose case needs a 151,936-word
    result bank for the LM head's logits, or a source bank sized for a KV
    cache, states that in its vector set and gets it.
    """

    geometry = vectors.get("geometry")
    if not isinstance(geometry, dict):
        raise SystemExit("the shipped-prefix vectors declare no geometry")
    flags = []
    for name in ("INDEX_WORDS", "SOURCE_WORDS", "RESULT_WORDS"):
        value = geometry.get(name.lower())
        if not isinstance(value, int) or value <= 0:
            raise SystemExit(f"the shipped-prefix vectors declare no {name}")
        flags.append(f"-G{name}={value}")
    return flags


def load_vectors() -> dict[str, Any]:
    if not VECTOR_JSON.is_file():
        raise SystemExit(
            f"missing {VECTOR_JSON}; run tools/build_abi3_shipped_prefix_vectors.py"
        )
    vectors = json.loads(VECTOR_JSON.read_text(encoding="utf-8"))
    if vectors.get("schema") != "opentallas.rtl.abi3_shipped_prefix_vectors.v1":
        raise SystemExit("the shipped-prefix vectors have an unknown schema")
    if vectors.get("abi") != {"major": 3, "minor": 0}:
        raise SystemExit("the shipped-prefix vectors are not ABI 3.0")
    if vectors.get("state_compat") != 0:
        raise SystemExit("the production shipped-prefix profile enables STATE")
    for name, expected in vectors.get("image_sha256", {}).items():
        if sha256_file(VECTOR_DIR / name) != expected:
            raise SystemExit(f"shipped-prefix image {name} is stale")
    source = vectors["input_deployment_vectors"]
    source_path = ROOT / source["path"]
    if sha256_file(source_path) != source["sha256"]:
        raise SystemExit("the source shipped-deployment vector manifest changed")
    for name, expected in source["images"].items():
        if sha256_file(DEPLOYMENT_VECTOR_DIR / name) != expected:
            raise SystemExit(f"source deployment image {name} changed")
    return vectors


def stage_matmul_weight(vectors: dict[str, Any], destination: Path) -> dict[str, Any]:
    """Stage the three complete matrices both shipped Qwen targets consume."""

    operations = [
        [
            operation
            for operation in case["supported_prefix"]
            if operation["kind"] == "tensor_matmul"
        ]
        for case in vectors["cases"][:2]
    ]
    if any(len(group) != 3 for group in operations):
        raise SystemExit("each Qwen case must stage three MATMUL matrices")
    identity_fields = (
        "checkpoint",
        "checkpoint_revision",
        "shard",
        "declared_segment_offset",
        "declared_segment_bytes",
        "declared_segment_sha256",
        "selected_matrix_sha256",
    )
    combined_digest = hashlib.sha256()
    staged_matrices = []
    with destination.open("xb") as output_handle:
        for index, operation in enumerate(operations[0]):
            peer = operations[1][index]
            source = operation["weight_source"]
            peer_source = peer["weight_source"]
            if int(operation["pc"]) != int(peer["pc"]) or any(
                source[field] != peer_source[field] for field in identity_fields
            ):
                raise SystemExit(
                    f"Qwen ROM/HBM PC-{operation['pc']} weight identities disagree"
                )
            checkpoint = Path(source["checkpoint"]).expanduser()
            if checkpoint.name != source["checkpoint_revision"]:
                raise SystemExit("Qwen checkpoint revision path disagrees")
            shard = checkpoint / source["shard"]
            source_offset = int(source["declared_segment_offset"])
            byte_count = int(source["declared_segment_bytes"])
            base_words = int(operation["staged_weight_base_words"])
            if int(peer["staged_weight_base_words"]) != base_words:
                raise SystemExit("Qwen MATMUL staged-base identities disagree")
            if output_handle.tell() != base_words * 2:
                raise SystemExit("Qwen MATMUL staged layout is not contiguous")
            segment_digest = hashlib.sha256()
            remaining = byte_count
            with shard.open("rb") as input_handle:
                input_handle.seek(source_offset)
                while remaining:
                    chunk = input_handle.read(min(1 << 20, remaining))
                    if not chunk:
                        raise SystemExit(
                            f"Qwen PC-{operation['pc']} MATMUL segment is truncated"
                        )
                    output_handle.write(chunk)
                    segment_digest.update(chunk)
                    combined_digest.update(chunk)
                    remaining -= len(chunk)
            observed = segment_digest.hexdigest()
            if (
                observed != source["declared_segment_sha256"]
                or observed != source["selected_matrix_sha256"]
            ):
                raise SystemExit(
                    f"Qwen PC-{operation['pc']} MATMUL matrix identity differs"
                )
            staged_matrices.append(
                {
                    "pc": int(operation["pc"]),
                    "base_words": base_words,
                    "bytes": byte_count,
                    "sha256": observed,
                    "source_checkpoint_revision": source["checkpoint_revision"],
                    "source_shard": source["shard"],
                    "source_offset": source_offset,
                }
            )
        output_handle.flush()
        os.fsync(output_handle.fileno())
    byte_count = destination.stat().st_size
    vector_layout = vectors["staged_matmul_weight_layout"]
    compact_layout = {
        "bytes": byte_count,
        "matrices": [
            {
                "base_words": matrix["base_words"],
                "bytes": matrix["bytes"],
                "sha256": matrix["sha256"],
            }
            for matrix in staged_matrices
        ],
    }
    if compact_layout != vector_layout:
        raise SystemExit("staged MATMUL layout differs from vector manifest")
    return {
        "path": "generated/p3_matmul_weight.bin",
        "bytes": byte_count,
        "sha256": combined_digest.hexdigest(),
        "matrices": staged_matrices,
    }


def run_stage(
    name: str, command: list[str], build: Path, timeout: int
) -> dict[str, Any]:
    """Run one stage and measure what it cost, not only what it printed.

    The geometry the top is elaborated with is a cost as well as a
    capability -- a result bank sized for 151,936 logits and a source bank
    sized for a KV cache are simulator heap -- so every stage records its own
    wall time and the peak resident set of the child that ran it.  ``ru_maxrss``
    is a high-water mark over all reaped children, so the value before the
    stage is subtracted out and the stage's own peak is the increase, or the
    whole mark when it is the first.
    """

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=build,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    wall = time.monotonic() - started
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
        "wall_seconds": round(wall, 3),
        "cpu_seconds": round(
            (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime), 3
        ),
        # kilobytes on Linux; reported as bytes so no reader has to guess
        "peak_child_resident_bytes": int(after.ru_maxrss) * 1024,
    }


MEASURE_RE = re.compile(r"^MEASURE .*?\bcycles=(?P<cycles>\d+)\b", re.MULTILINE)


def parse_measure(log: str) -> dict[str, Any]:
    """The run's own simulated-cycle count, read off its MEASURE line.

    A rung of the verification ladder must state a positive
    ``execution.simulated_cycles``, and it has to be the number the simulator
    reported, not one composed here.  A run that emitted no MEASURE line
    measured no cycles, and says so rather than borrowing a plausible figure.
    """

    match = MEASURE_RE.search(log)
    if match is None:
        return {
            "measured": False,
            "simulated_cycles": 0,
            "why_not_measured": (
                "the run emitted no MEASURE line, so this campaign states no "
                "cycle count of its own"
            ),
        }
    return {"measured": True, "simulated_cycles": int(match.group("cycles"))}


def parse_observation(log: str) -> dict[str, Any]:
    cases = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in CASE_RE.finditer(log)
    ]
    checks = CHECKS_RE.findall(log)
    return {
        "cases": cases,
        "checks": int(checks[-1]) if checks else None,
        "admission": parse_admission(log),
        "measure": parse_measure(log),
    }


def simulator_case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
    expected_case_count: int,
) -> dict[str, Any]:
    """One simulator's compile-and-run, judged against THIS vector set.

    ``expected_case_count`` used to be the literal 4.  The vector set is
    append-only and WP-L adds a fifth case for the V4.1 wafer entrypoint, so a
    frozen 4 would have failed a correct five-case run and -- worse -- passed a
    four-case run of a five-case vector set.  It comes from the vector set now.
    """
    compiled = run_stage(f"{name}.compile", compile_command, build, 1800)
    executed: dict[str, Any] | None = None
    if compiled["returncode"] == 0:
        executed = run_stage(f"{name}.run", run_command, build, 3600)
    run_log = executed["log"] if executed else ""
    observation = parse_observation(run_log)
    passed = (
        compiled["returncode"] == 0
        and executed is not None
        and executed["returncode"] == 0
        and marker in run_log
        and len(observation["cases"]) == expected_case_count
        and observation["checks"] is not None
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "compile_wall_seconds": compiled["wall_seconds"],
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": run_log,
        "run_wall_seconds": executed["wall_seconds"] if executed else None,
        "run_cpu_seconds": executed["cpu_seconds"] if executed else None,
        "peak_child_resident_bytes": (
            executed["peak_child_resident_bytes"] if executed else None
        ),
        "required_marker": marker,
        "marker_present": marker in run_log,
        "checks": observation["checks"],
        "observed_cases": observation["cases"],
        "operator_admission": observation["admission"],
        "measure": observation["measure"],
        "simulated_cycles": observation["measure"]["simulated_cycles"],
        "log_sha256": hashlib.sha256(
            (compiled["log"] + run_log).encode("utf-8")
        ).hexdigest(),
    }


def _expected_cases(vectors: dict[str, Any]) -> list[dict[str, int]]:
    out = []
    for index, case in enumerate(vectors["cases"]):
        expected = case["expected"]
        out.append(
            {
                "index": index,
                "launches": int(expected["real_engine_launches"]),
                "words": int(expected["result_words"]),
                "responses": int(expected["issued"]),
                "trap": int(expected["trap_class"]),
                "fault": int(expected["first_fault_instruction"]),
                "fetched": int(expected["fetched"]),
                "retired": int(expected["retired"]),
                "issued": int(expected["issued"]),
                "views": int(expected["views"]),
            }
        )
    return out


def run(build_root: Path | None = None) -> dict[str, Any]:
    vectors = load_vectors()
    lane_qualification = load_lane_qualification()
    rope_qualification = load_rope_qualification()
    marker = vectors["required_marker"]
    executables = {
        "verilator": resolve(
            "verilator",
            TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator",
        ),
        "cxx": resolve("g++", None),
    }
    tools = {
        name: tool_record(path, ["--version"]) for name, path in executables.items()
    }
    require_versions(tools)

    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-prefix-rtl-") as raw:
        build = Path(build_root) if build_root else Path(raw)
        build.mkdir(parents=True, exist_ok=True)
        for name in DEPLOYMENT_IMAGES:
            shutil.copy2(DEPLOYMENT_VECTOR_DIR / name, build / name)
        for name in VECTOR_FILES:
            shutil.copy2(VECTOR_DIR / name, build / name)
        staged_matmul_weight = stage_matmul_weight(
            vectors, build / "p3_matmul_weight.bin"
        )

        rtl = [str(ROOT / path) for path in RTL_SOURCES]
        geometry_flags = elaboration_geometry(vectors)
        verilator_compile = [
            str(executables["verilator"]),
            "--cc",
            "--exe",
            "--build",
            "-Wall",
            "-Wno-fatal",
            "-Wno-DECLFILENAME",
            "--top-module",
            "ot_a3_shipped_prefix_top",
            "--Mdir",
            "obj_p3",
            *geometry_flags,
            *rtl,
            str(ROOT / "rtl/test/a3_engine_completion_adapter.sv"),
            str(ROOT / "rtl/test/a3_shipped_prefix_top.sv"),
            str(ROOT / "rtl/test/a3_shipped_prefix_harness.cpp"),
            "-CFLAGS",
            "-std=c++17",
        ]
        cases = [
            simulator_case(
                "verilator",
                verilator_compile,
                ["./obj_p3/Vot_a3_shipped_prefix_top"],
                build,
                marker,
                len(vectors["cases"]),
            )
        ]

    expected_cases = _expected_cases(vectors)
    integrated_replay_passed = (
        len(cases) == 1
        and cases[0]["status"] == "pass"
        and cases[0]["observed_cases"] == expected_cases
        and cases[0]["checks"] == expected_integrated_checks(vectors)
    )
    source_paths = (*RTL_SOURCES, *TEST_SOURCES, *CONTRACT_SOURCES, *TOOL_SOURCES)
    sources = {
        path: {
            "sha256": sha256_file(ROOT / path),
            "bytes": (ROOT / path).stat().st_size,
        }
        for path in source_paths
    }
    fault_sites = [
        {
            "case": vector_case["name"],
            "pc": int(vector_case["first_unsupported"]["pc"]),
            "descriptor_id": int(vector_case["first_unsupported"]["descriptor_id"]),
            "family": int(vector_case["first_unsupported"]["family"]),
            "sub": int(vector_case["first_unsupported"]["sub"]),
            "opcode": str(vector_case["first_unsupported"]["opcode"]),
            "trap_class": int(vector_case["first_unsupported"]["trap_class"]),
        }
        for vector_case in vectors["cases"]
    ]
    checkpoint_rows = []
    checkpoint_gains = []
    checkpoint_head_gains = []
    checkpoint_matrices = []
    rope_operations = []
    for vector_case in vectors["cases"]:
        embedding = next(
            operation
            for operation in vector_case["supported_prefix"]
            if operation["kind"] == "tensor_embed_lookup"
        )
        checkpoint_rows.append(
            {
                "case": vector_case["name"],
                "deployment_sha256": vector_case["deployment_sha256"],
                "deployment_identity_evidence": vector_case[
                    "deployment_identity_evidence"
                ],
                "operator_pc": int(embedding["pc"]),
                "operator_descriptor_id": int(embedding["descriptor_id"]),
                "numeric_contract_sha256": embedding["contract_sha256"],
                "source": embedding["source"],
            }
        )
        rms_operations = [
            operation
            for operation in vector_case["supported_prefix"]
            if operation["kind"] == "vector_rms_norm"
        ]
        for rms_norm in rms_operations:
            checkpoint_gains.append(
                {
                    "case": vector_case["name"],
                    "deployment_sha256": vector_case["deployment_sha256"],
                    "operator_pc": int(rms_norm["pc"]),
                    "operator_descriptor_id": int(rms_norm["descriptor_id"]),
                    "numeric_contract_sha256": rms_norm["contract_sha256"],
                    "source": rms_norm["weight_source"],
                }
            )
        head_rms_operations = [
            operation
            for operation in vector_case["supported_prefix"]
            if operation["kind"] == "vector_head_rms_norm"
        ]
        for head_rms_norm in head_rms_operations:
            checkpoint_head_gains.append(
                {
                    "case": vector_case["name"],
                    "deployment_sha256": vector_case["deployment_sha256"],
                    "operator_pc": int(head_rms_norm["pc"]),
                    "operator_descriptor_id": int(head_rms_norm["descriptor_id"]),
                    "numeric_contract_sha256": head_rms_norm["contract_sha256"],
                    "row_count": int(head_rms_norm["row_count"]),
                    "row_width": int(head_rms_norm["row_width"]),
                    "expected_payload_sha256": head_rms_norm["expected_payload_sha256"],
                    "mean_square_payload_sha256": head_rms_norm[
                        "mean_square_payload_sha256"
                    ],
                    "inverse_rms_payload_sha256": head_rms_norm[
                        "inverse_rms_payload_sha256"
                    ],
                    "source": head_rms_norm["weight_source"],
                }
            )
        case_ropes = [
            operation
            for operation in vector_case["supported_prefix"]
            if operation["kind"] == "vector_rope"
        ]
        for rope in case_ropes:
            rope_operations.append(
                {
                    "case": vector_case["name"],
                    "deployment_sha256": vector_case["deployment_sha256"],
                    "operator_pc": int(rope["pc"]),
                    "operator_descriptor_id": int(rope["descriptor_id"]),
                    "numeric_contract_sha256": rope["contract_sha256"],
                    "operator_aux_id_0": int(rope["operator_aux_id_0"]),
                    "row_count": int(rope["row_count"]),
                    "row_width": int(rope["row_width"]),
                    "coefficient_fp32_payload_sha256": rope[
                        "coefficient_fp32_payload_sha256"
                    ],
                    "coefficient_bf16_payload_sha256": rope[
                        "coefficient_bf16_payload_sha256"
                    ],
                    "coefficient_narrow_saturated_element_count": int(
                        rope["coefficient_narrow_saturated_element_count"]
                    ),
                    "multiplication_count": int(rope["multiplication_count"]),
                    "addition_count": int(rope["addition_count"]),
                    "expected_payload_sha256": rope["expected_payload_sha256"],
                    "oracle_agreement": rope["oracle_agreement"],
                }
            )
        matmul_operations = [
            operation
            for operation in vector_case["supported_prefix"]
            if operation["kind"] == "tensor_matmul"
        ]
        for matmul in matmul_operations:
            checkpoint_matrices.append(
                {
                    "case": vector_case["name"],
                    "deployment_sha256": vector_case["deployment_sha256"],
                    "operator_pc": int(matmul["pc"]),
                    "operator_descriptor_id": int(matmul["descriptor_id"]),
                    "numeric_contract_sha256": matmul["contract_sha256"],
                    "executed_association": matmul["executed_association"],
                    "association_scope": matmul["association_scope"],
                    "expected_row_sha256": matmul["expected_row_sha256"],
                    "source": matmul["weight_source"],
                }
            )
    return {
        "schema": "opentallas.rtl.abi3_shipped_prefix_campaign.v1",
        "status": "pass" if integrated_replay_passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation_composite",
        "evidence_mode": (
            "full_integrated_verilator_plus_dual_simulator_mac_lane_and_rope_"
            "composition"
        ),
        "abi": {"major": 3, "minor": 0},
        "state_compat": 0,
        "state_activity": {
            "compatibility_controller_elaborated": False,
            "configured_state_descriptor_count": 0,
            "prepare_count": 0,
            "commit_count": 0,
            "discard_count": 0,
            "read_count": 0,
            "generation_advance_count": 0,
            "commit_apply_count": 0,
            "rows_committed": 0,
            "bytes_written": 0,
            "apply_overflow_count": 0,
        },
        "vector_set": {
            "path": str(VECTOR_JSON.relative_to(ROOT)),
            "sha256": sha256_file(VECTOR_JSON),
            "schema": vectors["schema"],
        },
        "staged_matmul_weight": staged_matmul_weight,
        "compositional_mac_lane_qualification": lane_qualification,
        "compositional_rope_qualification": rope_qualification,
        "scope": {
            "establishes": [
                "the real sequencer resolves exact operand views from each of the four shipped decode programs",
                "six dense one-index FP32 DMA.GATHER operations execute through ot_a3_engine_array and reproduce 1,024 authenticated generated RoPE words",
                "four exact BF16 TENSOR.EMBED_LOOKUP operations execute through the existing index mover and reproduce 16,384 checkpoint codes from four bounded 8 KiB selected-row reads",
                "two exact Qwen BF16 VECTOR.RMS_NORM operations consume the prior embedding result and authenticated layer-zero gain, reproducing all 8,192 retained output codes",
                "two DeepSeek stride-zero DMA.TRANSFER operations consume the prior embedding result and reproduce all 32,768 output codes through a four-zero-index mover lowering",
                "six complete Qwen layer-zero query/key/value TENSOR.MATMUL operations consume the prior RMSNorm result and every code of three authenticated matrices through one descriptor-driven ot_a3_mac_lane path, reproducing all 12,288 output codes after 50,331,648 MACs",
                "the blocked MATMUL contract is bound to the explicit ot_a3_mac_lane single-lane ascending-K association, executed for 1x4096 by 4096x4096 and two 1024x4096 shapes per deployment, with per-product and per-add binary32 RNE and one final BF16 RNE",
                "four Qwen VECTOR.HEAD_RMS_NORM operations consume the exact prior query/key projection result banks and authenticated 128-code gains through one descriptor-sized buffered datapath, reproducing 10,240 output codes for two 32x128 and two 8x128 row sets",
                "the head-normalization datapath applies the declared qwen3_rmsnorm_fp32_bf16_v1 contract independently to every descriptor-selected head row and buffers every output before its first destination write",
                "four Qwen VECTOR.ROPE operations consume the exact prior query/key head-normalization result banks and the previously gathered FP32 position-16 coefficient row, narrow all 256 coefficients to BF16 RNE, and reproduce 10,240 output codes that agree element-for-element with the independent scalar oracle",
                "the ABI 3.0 RoPE adapter executes each declared 32x128 or 8x128 operand through the unchanged qualified Qwen RoPE core, provides internal positive zero to its inactive fused side, and neither reads an undeclared external operand nor publishes an undeclared destination write",
                "each selected checkpoint range is bound to its certified deployment, checkpoint revision, shard, declared segment digest, exact byte range, and selected-range SHA-256 without claiming a complete-shard rehash",
                "Qwen next refuses DMA.SCATTER at PC 32; DeepSeek ROM refuses LINK.MULTICAST at PC 13 and DeepSeek HBM refuses VECTOR.MHC at PC 14, each with a precise CAPABILITY trap, no retirement, no event publication, and no later write",
                "the production profile elaborates STATE_COMPAT=0 and every compatibility-state counter and overflow output remains zero",
                "Verilator executes the complete integrated shipped-prefix cases and its independent C++ checker reproduces every retained observation and result word",
                "the unchanged ot_a3_mac_lane source is bound by SHA-256 to its retained Icarus-plus-Verilator engine qualification; that compositional campaign contributes 40,878 checks per simulator over 59,868 MACs",
                "the unchanged ot_ta_rope_bf16_sram_engine source is bound by SHA-256 to its retained Icarus-plus-Verilator operation-complete qualification at positions 0 and 7999",
            ],
            "does_not_establish": [
                "prefill execution",
                "Qwen DMA.SCATTER, ATTENTION.GQA, LINK.MULTICAST, VECTOR.MHC, or any later model operator",
                "a whole transaction, token selection, decoding, EOS, or model correctness",
                "output-token correctness, legitimate decoded text, or correctness-qualified TPOT",
                "complete checkpoint-segment reauthentication during this bounded run",
                "memory-macro timing, SRAM/HBM arbitration, physical timing, area, or power",
                "a complete integrated shipped-prefix execution under Icarus; Icarus coverage is compositional qualification of the unchanged MAC lane and Qwen RoPE core, not execution of these full shipped descriptor/control paths",
                "dual-simulator agreement on this complete integrated transaction",
            ],
        },
        "supported_profile": vectors["supported_profile"],
        "unsupported_policy": vectors["unsupported_policy"],
        "case_count": vectors["case_count"],
        "real_engine_launch_count": vectors["real_engine_launch_count"],
        "dma_gather_launch_count": vectors["dma_gather_launch_count"],
        "embedding_launch_count": vectors["embedding_launch_count"],
        "rms_norm_launch_count": vectors["rms_norm_launch_count"],
        "head_rms_norm_launch_count": vectors["head_rms_norm_launch_count"],
        "rope_launch_count": vectors["rope_launch_count"],
        "dma_transfer_launch_count": vectors["dma_transfer_launch_count"],
        "matmul_launch_count": vectors["matmul_launch_count"],
        "rope_coefficient_gather_result_word_count": vectors[
            "rope_coefficient_gather_result_word_count"
        ],
        "rope_result_word_count": vectors["rope_result_word_count"],
        "embedding_result_word_count": vectors["embedding_result_word_count"],
        "rms_norm_result_word_count": vectors["rms_norm_result_word_count"],
        "head_rms_norm_result_word_count": vectors["head_rms_norm_result_word_count"],
        "dma_transfer_result_word_count": vectors["dma_transfer_result_word_count"],
        "matmul_result_word_count": vectors["matmul_result_word_count"],
        "matmul_mac_count": vectors["matmul_mac_count"],
        "selected_embedding_checkpoint_byte_count": vectors[
            "selected_embedding_checkpoint_byte_count"
        ],
        "selected_rms_checkpoint_byte_count": vectors[
            "selected_rms_checkpoint_byte_count"
        ],
        "selected_head_rms_checkpoint_byte_count": vectors[
            "selected_head_rms_checkpoint_byte_count"
        ],
        "selected_matmul_checkpoint_byte_count": vectors[
            "selected_matmul_checkpoint_byte_count"
        ],
        "selected_checkpoint_byte_count": vectors["selected_checkpoint_byte_count"],
        # Words the engines WRITE, and words the retained image spans.  They
        # differ by exactly the words a rewritten buffer gives up, and both
        # are published because only the first is a count of what ran.
        "result_word_count": vectors["result_word_count"],
        "retained_image_word_count": vectors["retained_image_word_count"],
        "resolved_view_count": vectors["resolved_view_count"],
        "capability_fault_count": vectors["capability_fault_count"],
        "fault_sites": fault_sites,
        "checkpoint_rows": checkpoint_rows,
        "checkpoint_gains": checkpoint_gains,
        "checkpoint_head_gains": checkpoint_head_gains,
        "checkpoint_matrices": checkpoint_matrices,
        "rope_operations": rope_operations,
        "post_fault_write_count": 0,
        "required_marker": marker,
        "integrated_simulator_checks": {case["name"]: case["checks"] for case in cases},
        "integrated_simulators": [case["name"] for case in cases],
        "integrated_replay_passed": integrated_replay_passed,
        # Rung G1a's integrated half, measured rather than inferred from the
        # presence of a port connection in the top's source text.
        "operator_admission": (
            cases[0]["operator_admission"] if cases else parse_admission("")
        ),
        # The integrated run's own simulated-cycle count, summed over the
        # simulators that ran it.  Rung G1a's provenance spine requires a
        # positive one and will not accept a composed figure.
        "simulated_cycles": sum(
            int(case.get("simulated_cycles") or 0) for case in cases
        ),
        "simulated_cycles_by_simulator": {
            case["name"]: int(case.get("simulated_cycles") or 0) for case in cases
        },
        "expected_cases": expected_cases,
        # What the top was elaborated with, and what that geometry cost.  Both
        # halves are here deliberately: a geometry that admits an operator and
        # a geometry that thrashes are the same statement until the second
        # number is present.
        "elaboration": {
            "geometry_flags": geometry_flags,
            "declared_by": "the vector set's own geometry block",
            "index_words": vectors["geometry"]["index_words"],
            "source_words": vectors["geometry"]["source_words"],
            "result_words": vectors["geometry"]["result_words"],
            "operand_bank_bytes": 4
            * (
                int(vectors["geometry"]["index_words"])
                + int(vectors["geometry"]["source_words"])
                + int(vectors["geometry"]["result_words"])
            ),
        },
        "cost": {
            "compile_wall_seconds": [
                case.get("compile_wall_seconds") for case in cases
            ],
            "run_wall_seconds": [case.get("run_wall_seconds") for case in cases],
            "run_cpu_seconds": [case.get("run_cpu_seconds") for case in cases],
            "peak_child_resident_bytes": max(
                [int(case.get("peak_child_resident_bytes") or 0) for case in cases]
                or [0]
            ),
        },
        "tools": tools,
        "git": git_identity(),
        "source": sources,
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--build-dir", type=Path, default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 2
    summary = run(args.build_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    for case in summary["cases"]:
        print(f"{case['name']}: {case['status'].upper()} checks={case['checks']}")
    print(
        f"abi3 shipped-prefix rtl campaign: {summary['status'].upper()} -> "
        f"{args.output}"
    )
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
