#!/usr/bin/env python3
"""Run the focused ABI 3.0 shipped-prefix integration witness.

The complete source-bound Qwen layer-zero query/key/value MATMUL family is
intentionally executed under Verilator.  Interpreted Icarus needs several
hours for these single-lane launches, so this campaign does not imply that
Icarus ran the complete integrated transaction.  Instead it fail-closed binds
the unchanged ``ot_a3_mac_lane`` source to the retained dual-simulator engine
qualification and records that evidence as compositional, not integrated.
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
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VECTOR_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
VECTOR_JSON = VECTOR_DIR / "abi3_shipped_prefix_vectors.json"
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_shipped_prefix_campaign.json"
ENGINE_CAMPAIGN = ROOT / "results/rtl/abi3_engine_campaign.json"

PINNED_VERILATOR_VERSION = "5.050"
TOOLS_ROOT = Path(
    os.environ.get("OPENTALLAS_TOOL_ROOT", Path.home() / ".local/opentallas-tools")
)

RTL_SOURCES = (
    "rtl/ot_fp32_rne_pkg.sv",
    "rtl/ot_fp32_rsqrt_rne.sv",
    "rtl/abi3/ot_a3_format_pkg.sv",
    "rtl/abi3/ot_a3_engine_pkg.sv",
    "rtl/abi3/ot_a3_pkg.sv",
    "rtl/abi3/ot_a3_instruction_decoder.sv",
    "rtl/abi3/ot_a3_loop_stack.sv",
    "rtl/abi3/ot_a3_view_resolver.sv",
    "rtl/abi3/ot_a3_event_scoreboard.sv",
    "rtl/abi3/ot_a3_state_controller.sv",
    "rtl/abi3/ot_a3_microsequencer.sv",
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
    "rtl/abi3/ot_a3_engine_issue_bridge.sv",
)
TEST_SOURCES = (
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
    "runtime/reference/tensor_accelerator_rmsnorm.py",
    "runtime/tensor_accelerator/bf16.py",
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        raise SystemExit(
            f"Verilator {PINNED_VERILATOR_VERSION} or newer is required"
        )


def load_lane_qualification() -> dict[str, Any]:
    """Bind the unchanged MAC lane to its retained dual-simulator evidence."""

    if not ENGINE_CAMPAIGN.is_file():
        raise SystemExit(f"missing compositional lane evidence: {ENGINE_CAMPAIGN}")
    body = json.loads(ENGINE_CAMPAIGN.read_text(encoding="utf-8"))
    source_path = "rtl/abi3/ot_a3_mac_lane.sv"
    source_sha256 = sha256_file(ROOT / source_path)
    blocked_limit = body.get("claim_boundary", {}).get(
        "does_not_establish", {}
    ).get("blocked_contraction_contract")
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
        or "only bf16_bf16_fp32_sequential_rne_v1 is correlated"
        not in blocked_limit
    ):
        raise SystemExit(
            "the retained dual-simulator MAC-lane qualification changed"
        )
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


def stage_matmul_weight(
    vectors: dict[str, Any], destination: Path
) -> dict[str, Any]:
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
            if (
                int(operation["pc"]) != int(peer["pc"])
                or any(
                    source[field] != peer_source[field]
                    for field in identity_fields
                )
            ):
                raise SystemExit(
                    f"Qwen ROM/HBM PC-{operation['pc']} weight identities "
                    "disagree"
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
                            f"Qwen PC-{operation['pc']} MATMUL segment is "
                            "truncated"
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
                    "source_checkpoint_revision": source[
                        "checkpoint_revision"
                    ],
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
    result = subprocess.run(
        command,
        cwd=build,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=timeout,
    )
    return {
        "name": name,
        "command": canonical(shlex.join(command), build),
        "returncode": result.returncode,
        "log": canonical(result.stdout, build),
    }


def parse_observation(log: str) -> dict[str, Any]:
    cases = [
        {key: int(value) for key, value in match.groupdict().items()}
        for match in CASE_RE.finditer(log)
    ]
    checks = CHECKS_RE.findall(log)
    return {"cases": cases, "checks": int(checks[-1]) if checks else None}


def simulator_case(
    name: str,
    compile_command: list[str],
    run_command: list[str],
    build: Path,
    marker: str,
) -> dict[str, Any]:
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
        and len(observation["cases"]) == 4
        and observation["checks"] is not None
    )
    return {
        "name": name,
        "status": "pass" if passed else "fail",
        "compile_command": compiled["command"],
        "compile_returncode": compiled["returncode"],
        "compile_log": compiled["log"],
        "run_command": executed["command"] if executed else None,
        "run_returncode": executed["returncode"] if executed else None,
        "run_log": run_log,
        "required_marker": marker,
        "marker_present": marker in run_log,
        "checks": observation["checks"],
        "observed_cases": observation["cases"],
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
    marker = vectors["required_marker"]
    executables = {
        "verilator": resolve(
            "verilator",
            TOOLS_ROOT / f"verilator-{PINNED_VERILATOR_VERSION}/bin/verilator",
        ),
        "cxx": resolve("g++", None),
    }
    tools = {
        name: tool_record(path, ["--version"])
        for name, path in executables.items()
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
            *rtl,
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
            )
        ]

    expected_cases = _expected_cases(vectors)
    integrated_replay_passed = (
        len(cases) == 1
        and cases[0]["status"] == "pass"
        and cases[0]["observed_cases"] == expected_cases
        and cases[0]["checks"] == 144_708
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
            "descriptor_id": int(
                vector_case["first_unsupported"]["descriptor_id"]
            ),
            "family": int(vector_case["first_unsupported"]["family"]),
            "sub": int(vector_case["first_unsupported"]["sub"]),
            "opcode": str(vector_case["first_unsupported"]["opcode"]),
            "trap_class": int(
                vector_case["first_unsupported"]["trap_class"]
            ),
        }
        for vector_case in vectors["cases"]
    ]
    checkpoint_rows = []
    checkpoint_gains = []
    checkpoint_matrices = []
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
                    "deployment_sha256": vector_case[
                        "deployment_sha256"
                    ],
                    "operator_pc": int(rms_norm["pc"]),
                    "operator_descriptor_id": int(
                        rms_norm["descriptor_id"]
                    ),
                    "numeric_contract_sha256": rms_norm[
                        "contract_sha256"
                    ],
                    "source": rms_norm["weight_source"],
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
                    "deployment_sha256": vector_case[
                        "deployment_sha256"
                    ],
                    "operator_pc": int(matmul["pc"]),
                    "operator_descriptor_id": int(
                        matmul["descriptor_id"]
                    ),
                    "numeric_contract_sha256": matmul[
                        "contract_sha256"
                    ],
                    "executed_association": matmul[
                        "executed_association"
                    ],
                    "association_scope": matmul["association_scope"],
                    "expected_row_sha256": matmul[
                        "expected_row_sha256"
                    ],
                    "source": matmul["weight_source"],
                }
            )
    return {
        "schema": "opentallas.rtl.abi3_shipped_prefix_campaign.v1",
        "status": "pass" if integrated_replay_passed else "fail",
        "evidence_class": "public_open_tool_rtl_simulation_composite",
        "evidence_mode": (
            "full_integrated_verilator_plus_dual_simulator_mac_lane_composition"
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
        "scope": {
            "establishes": [
                "the real sequencer resolves exact operand views from each of the four shipped decode programs",
                "six dense one-index FP32 DMA.GATHER operations execute through ot_a3_engine_array and reproduce 1,024 authenticated generated RoPE words",
                "four exact BF16 TENSOR.EMBED_LOOKUP operations execute through the existing index mover and reproduce 16,384 checkpoint codes from four bounded 8 KiB selected-row reads",
                "two exact Qwen BF16 VECTOR.RMS_NORM operations consume the prior embedding result and authenticated layer-zero gain, reproducing all 8,192 retained output codes",
                "two DeepSeek stride-zero DMA.TRANSFER operations consume the prior embedding result and reproduce all 32,768 output codes through a four-zero-index mover lowering",
                "six complete Qwen layer-zero query/key/value TENSOR.MATMUL operations consume the prior RMSNorm result and every code of three authenticated matrices through one descriptor-driven ot_a3_mac_lane path, reproducing all 12,288 output codes after 50,331,648 MACs",
                "the blocked MATMUL contract is bound to the explicit ot_a3_mac_lane single-lane ascending-K association, executed for 1x4096 by 4096x4096 and two 1024x4096 shapes per deployment, with per-product and per-add binary32 RNE and one final BF16 RNE",
                "each selected checkpoint range is bound to its certified deployment, checkpoint revision, shard, declared segment digest, exact byte range, and selected-range SHA-256 without claiming a complete-shard rehash",
                "Qwen next refuses VECTOR.HEAD_RMS_NORM at PC 20; DeepSeek ROM refuses LINK.MULTICAST at PC 13 and DeepSeek HBM refuses VECTOR.MHC at PC 14, each with a precise CAPABILITY trap, no retirement, no event publication, and no later write",
                "the production profile elaborates STATE_COMPAT=0 and every compatibility-state counter and overflow output remains zero",
                "Verilator executes the complete integrated shipped-prefix cases and its independent C++ checker reproduces every retained observation and result word",
                "the unchanged ot_a3_mac_lane source is bound by SHA-256 to its retained Icarus-plus-Verilator engine qualification; that compositional campaign contributes 40,878 checks per simulator over 59,868 MACs",
            ],
            "does_not_establish": [
                "prefill execution",
                "Qwen VECTOR.HEAD_RMS_NORM, LINK.MULTICAST, VECTOR.MHC, or any later model operator",
                "a whole transaction, token selection, decoding, EOS, or model correctness",
                "complete checkpoint-segment reauthentication during this bounded run",
                "memory-macro timing, SRAM/HBM arbitration, physical timing, area, or power",
                "a complete integrated shipped-prefix execution under Icarus; Icarus coverage is compositional qualification of the unchanged MAC lane, not execution of these full query/key/value blocked-contract operations or their control paths",
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
        "dma_transfer_launch_count": vectors["dma_transfer_launch_count"],
        "matmul_launch_count": vectors["matmul_launch_count"],
        "rope_result_word_count": vectors["rope_result_word_count"],
        "embedding_result_word_count": vectors[
            "embedding_result_word_count"
        ],
        "rms_norm_result_word_count": vectors[
            "rms_norm_result_word_count"
        ],
        "dma_transfer_result_word_count": vectors[
            "dma_transfer_result_word_count"
        ],
        "matmul_result_word_count": vectors["matmul_result_word_count"],
        "matmul_mac_count": vectors["matmul_mac_count"],
        "selected_embedding_checkpoint_byte_count": vectors[
            "selected_embedding_checkpoint_byte_count"
        ],
        "selected_rms_checkpoint_byte_count": vectors[
            "selected_rms_checkpoint_byte_count"
        ],
        "selected_matmul_checkpoint_byte_count": vectors[
            "selected_matmul_checkpoint_byte_count"
        ],
        "selected_checkpoint_byte_count": vectors[
            "selected_checkpoint_byte_count"
        ],
        "result_word_count": vectors["result_word_count"],
        "resolved_view_count": vectors["resolved_view_count"],
        "capability_fault_count": vectors["capability_fault_count"],
        "fault_sites": fault_sites,
        "checkpoint_rows": checkpoint_rows,
        "checkpoint_gains": checkpoint_gains,
        "checkpoint_matrices": checkpoint_matrices,
        "post_fault_write_count": 0,
        "required_marker": marker,
        "integrated_simulator_checks": {
            case["name"]: case["checks"] for case in cases
        },
        "integrated_simulators": [case["name"] for case in cases],
        "integrated_replay_passed": integrated_replay_passed,
        "expected_cases": expected_cases,
        "tools": tools,
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
