"""Focused mutations for the DeepSeek exact-200K accelerator gate."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "check_deepseek_v4_200k_accelerator_acceptance",
    REPO / "tools/check_deepseek_v4_200k_accelerator_acceptance.py",
)
tool = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(tool)

_helper_spec = importlib.util.spec_from_file_location(
    "deepseek_200k_abi3_test_helpers", REPO / "tests/abi3/__init__.py"
)
abi3_helpers = importlib.util.module_from_spec(_helper_spec)
assert _helper_spec.loader is not None
_helper_spec.loader.exec_module(abi3_helpers)


def _identity(path: Path) -> dict[str, object]:
    return {
        "path": tool._relative(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def _association_entry(calls: int) -> dict[str, object]:
    return {
        "numeric_contract": tool.BLOCKED_CONTRACT,
        "activation_shape": [512, 4096],
        "weight_shape": [4096, 4096],
        "output_shape": [512, 4096],
        "call_count": calls,
    }


def _association(identity: dict[str, object], calls: int) -> dict[str, object]:
    body: dict[str, object] = {
        "schema": tool.ASSOCIATION_SCHEMA,
        "association_policy": tool.ASSOCIATION_POLICY,
        "implementation_identity": copy.deepcopy(identity),
        "entries": [_association_entry(calls)],
        "distinct_association_count": 1,
        "blocked_call_count": calls,
    }
    body["manifest_sha256"] = tool._association_digest(body)
    return body


def _host_performance(identity: dict[str, object], calls: int) -> dict[str, object]:
    ordered: dict[str, object] = {
        "association_policy": "executed_order_adjacent_run_length",
        "runs": [_association_entry(calls)],
        "run_count": 1,
        "blocked_call_count": calls,
    }
    ordered["manifest_sha256"] = tool._canonical_digest(ordered)
    return {
        "schema": "opentallas.abi3.host_performance.device_epoch.v1",
        "scope": "one_activated_device_including_all_logical_nodes",
        "architectural_counter_registry_unchanged": True,
        "implementation_identity": copy.deepcopy(identity),
        "ordered_executed_associations": ordered,
        "association_reconciliation": {
            "ordered_blocked_call_count": calls,
            "aggregated_blocked_call_count": calls,
            "counts_equal": True,
        },
    }


def _build_deployment(backend: str, root: Path):
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import (
        Control,
        DType,
        Dma,
        Feature,
        Major,
        Permission,
        Selection,
        StorageClass,
        TopologyClass,
    )
    from runtime.abi3.deployment import ObjectSource
    from runtime.abi3.descriptors import ExtendedDescriptorType, Phase, SelectionMode
    from runtime.abi3.verifier import verify_deployment

    capability = Capability.from_dict(
        json.loads(tool.CAPABILITIES[backend].read_text())
    )
    hbm = backend == "hbm_sram"
    builder = DeploymentBuilder(
        target_id=tool.TARGET_IDS[backend],
        model_id=tool.MODEL_ID,
        backend=tool.TARGET_BACKENDS[backend],
        capability=capability,
    )
    builder.require(Feature.BF16_TENSOR)
    if hbm:
        builder.topology(
            topology_class=TopologyClass.CLUSTER_32,
            node_count=32,
            active_resource_count=32,
        )
    else:
        builder.topology(
            topology_class=TopologyClass.WAFER_LOGICAL_DEVICE,
            node_count=1,
            reticle_count=1,
            tiles_per_reticle=capability.link["tiles_per_reticle"],
            active_resource_count=capability.link["tiles_per_reticle"],
        )
    live = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=128,
        source=ObjectSource.zeros(128),
        permissions=int(Permission.READ | Permission.WRITE),
    )
    exchange = builder.memory_object(
        storage_class=StorageClass.HBM,
        size_bytes=128,
        source=ObjectSource.zeros(128),
        permissions=int(
            Permission.READ
            | Permission.WRITE
            | (Permission.REMOTE if hbm else Permission.NONE)
        ),
        base_address=128,
    )
    tokens = builder.memory_object(
        storage_class=StorageClass.HOST,
        size_bytes=1024,
        source=ObjectSource.zeros(1024),
        permissions=int(Permission.READ | Permission.WRITE | Permission.HOST_VISIBLE),
    )
    live_view = builder.tensor_view(
        object_id=live,
        dtype=DType.BF16,
        dims=[8, 8],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    exchange_view = builder.tensor_view(
        object_id=exchange,
        dtype=DType.BF16,
        dims=[8, 8],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    token_view = builder.tensor_view(
        object_id=tokens,
        dtype=DType.U32,
        dims=[256],
        permissions=int(Permission.READ | Permission.WRITE),
    )
    numeric = builder.numeric(
        contract=tool.BLOCKED_CONTRACT,
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
    )
    dma_schedule = builder.schedule(
        engine_family=Major.DMA,
        queue_index=3 if hbm else 0,
        issue_window=1,
        max_outstanding=1,
        tile_rows=8,
        tile_cols=8,
        tile_depth=1,
        bank_mask=1,
    )
    selection_schedule = builder.schedule(
        engine_family=Major.SELECTION,
        tile_rows=1,
        tile_cols=8,
        tile_depth=1,
        bank_mask=1,
    )
    transfer = builder.operator(
        engine_family=Major.DMA,
        engine_sub=Dma.TRANSFER,
        inputs=[exchange_view],
        outputs=[live_view],
        numeric_profile_id=numeric,
        schedule_id=dma_schedule,
    )
    argmax = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.ARGMAX,
        inputs=[live_view],
        outputs=[token_view],
        numeric_profile_id=numeric,
        schedule_id=selection_schedule,
    )
    append = builder.operator(
        engine_family=Major.SELECTION,
        engine_sub=Selection.TOKEN_APPEND,
        inputs=[token_view],
        outputs=[token_view],
        numeric_profile_id=numeric,
        schedule_id=selection_schedule,
    )
    policy = builder.generation_policy(
        eos_token_ids=[tool.EOS_TOKEN_ID],
        max_new_tokens=tool.MAX_NEW_TOKENS,
        vocabulary_size=tool.VOCABULARY_SIZE,
        token_ring_object_id=tokens,
        selection_mode=SelectionMode.GREEDY_ARGMAX_LOWEST_ID,
    )
    builder.emit(Major.DMA, Dma.TRANSFER, descriptor_id=transfer)
    builder.emit(Major.SELECTION, Selection.ARGMAX, descriptor_id=argmax)
    builder.emit(Major.SELECTION, Selection.TOKEN_APPEND, descriptor_id=append)
    builder.emit(Major.CONTROL, Control.COMPLETE)
    builder.entrypoint(
        entrypoint_id=0,
        first_instruction=0,
        phase=Phase.PREFILL,
        generation_policy_id=policy,
    )
    builder.entrypoint(
        entrypoint_id=1,
        first_instruction=0,
        phase=Phase.DECODE,
        generation_policy_id=policy,
    )
    builder.source_identity = {"graph_id": tool.GRAPH_ID}
    builder.notes["test_live_object_id"] = live
    deployment = builder.finish()
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    deployment.write(root)
    policy_descriptor = deployment.table[
        deployment.table.ids_of_type(ExtendedDescriptorType.GENERATION_POLICY)[0]
    ]
    return deployment, report, dict(policy_descriptor.payload)


def _logical_node(generated_count: int) -> dict[str, int]:
    node = {name: 11 for name in tool.PAIR_LOGICAL_COUNTERS}
    node.update(
        {
            "attention.kv_bytes_read": 4096,
            "dma.scatter_elements": tool.PROMPT_TOKENS + generated_count,
            "selection.tie_multiplicity": generated_count,
            "selection.tokens_appended": generated_count,
            "selection.tokens_selected": generated_count,
            "selection.vocabulary_elements": (generated_count * tool.VOCABULARY_SIZE),
        }
    )
    return node


def _record(
    backend: str,
    deployment_root: Path,
    oracle_path: Path,
    checkpoint: Path,
) -> dict[str, object]:
    from runtime.abi3.capability import Capability

    workload = json.loads(tool.WORKLOAD.read_text())
    oracle = json.loads(oracle_path.read_text())
    generated = list(oracle["results"][tool.WORKLOAD_ID]["generated_token_ids"])
    deployment, report, policy = _build_deployment(backend, deployment_root)
    capability_path = tool.CAPABILITIES[backend]
    capability = Capability.from_dict(json.loads(capability_path.read_text()))
    prompt = list(workload["token_ids"])
    prompt_digest = tool.digest_of(prompt)
    node_count = tool.NODE_COUNT[backend]
    node = _logical_node(len(generated))
    nodes = [copy.deepcopy(node) for _ in range(node_count)]
    counters = {name: sum(item[name] for item in nodes) for name in node}
    counters.update(
        {
            "instructions.issued": len(generated) * 3,
            "instructions.retired": len(generated) * 7,
            "hbm.bytes_written": len(generated) * 64 * node_count,
            "selection.invalid_tokens": 0,
        }
    )
    steps = [
        {
            "step": index,
            "transaction_id": index + 1,
            "phase": "prefill" if index == 0 else "decode",
            "status": "SUCCESS",
            "trap": "NONE",
            "produced_tokens": [token],
            "final_token_id": token,
            "eos_reason": 2 if index == len(generated) - 1 else 0,
            "instructions_retired": 7,
            "retired_work": 7,
            "instructions_predicated_off": 0,
            "wall_seconds": 1.0,
        }
        for index, token in enumerate(generated)
    ]
    implementation = {
        "backend": "numpy",
        "library": "numpy",
        "library_version": "2.2.6",
        "device": "host",
        "device_name": "test-host",
        "blocked_association": "shape and thread pinned",
        "flags": {
            "OMP_NUM_THREADS": "8",
            "OPENBLAS_NUM_THREADS": "8",
            "MKL_NUM_THREADS": "8",
            "allow_tf32": False,
            "float32_matmul_precision": "highest",
        },
    }
    calls = 64 if backend == "hbm_sram" else 2
    deployment_digest = deployment.deployment_digest.hex()
    return {
        "schema": tool.RECORD_SCHEMA,
        "status": "pass",
        "evidence_class": "functional_artifact_only",
        "tool": "tools/run_accelerator_tokens.py",
        "backend": backend,
        "target": {
            "target_id": tool.TARGET_IDS[backend],
            "backend": tool.TARGET_BACKENDS[backend],
            "topology_class": tool.TOPOLOGY_CLASS[backend],
            "node_count": node_count,
            "capability": tool._relative(capability_path),
            "capability_digest": capability.digest,
            "deployment_digest": deployment_digest,
            "technology_view": capability.technology_view,
        },
        "workload": {
            "workload_id": tool.WORKLOAD_ID,
            "workload_digest": tool.WORKLOAD_DIGEST,
            "prompt_token_ids": prompt,
            "prompt_token_count": len(prompt),
            "max_new_tokens": tool.MAX_NEW_TOKENS,
            "rendered_text_sha256": tool.RENDERED_TEXT_SHA256,
            "prompt_token_ids_sha256": prompt_digest,
            "tokenizer_sha256": tool.TOKENIZER_SHA256,
        },
        "model": {
            "model_id": tool.MODEL_ID,
            "graph_id": tool.GRAPH_ID,
            "numeric_profile": tool.NUMERIC_PROFILE,
            "checkpoint_root": tool._relative(checkpoint),
        },
        "generation_policy": policy,
        "generation_policy_digest": tool.digest_of(policy),
        "verification": report.to_dict(),
        "implementation_identity": implementation,
        "executed_association": _association(implementation, calls),
        "host_performance": _host_performance(implementation, calls),
        "inputs": {
            "kernel_ir": _identity(tool.KERNEL_IR),
            "capability": _identity(capability_path),
            "workload": {
                **_identity(tool.WORKLOAD),
                "declared_workload_digest": tool.WORKLOAD_DIGEST,
                "prompt_token_ids_sha256": prompt_digest,
                "tokenizer_sha256": tool.TOKENIZER_SHA256,
            },
            "reference": _identity(oracle_path),
            "checkpoint_root": {
                "path": tool._relative(checkpoint),
                "kind": "directory",
                "content_binding": (
                    "authenticated deployment object segment SHA-256 values"
                ),
                "deployment_digest_binding": deployment_digest,
            },
            "published_deployment": {
                "path": tool._relative(deployment_root),
                "manifest": _identity(deployment_root / "deployment.json"),
                "descriptors": _identity(deployment_root / "descriptors.bin"),
                "program": _identity(deployment_root / "program.bin"),
            },
        },
        "source_sha256": {
            relative: hashlib.sha256((REPO / relative).read_bytes()).hexdigest()
            for relative in sorted(tool._expected_sources(backend))
        },
        "generated_token_ids": generated,
        "generated_token_count": len(generated),
        "stop_reason": "max_new_tokens",
        "failure": None,
        "token_legitimacy_problems": [],
        "oracle": {
            "artifact": tool._relative(oracle_path),
            "artifact_sha256": hashlib.sha256(oracle_path.read_bytes()).hexdigest(),
            "evidence_class": "external_reference_comparator",
            "expert_numeric_path": "fp8",
            "generated_token_ids": generated,
            "agreement": True,
            "first_divergence_index": None,
            "compared_tokens": len(generated),
            "oracle_token_count": len(generated),
        },
        "terminal_acceptance": {
            "contract": "exact_eos_or_cap",
            "accepted": True,
            "terminal_kind": "cap",
            "checks": {"complete_terminal_sequence": True},
            "failed_checks": [],
        },
        "counters": counters,
        "counter_scope": {
            "aggregate": "cluster_total",
            "per_node": "engine_work_by_node_id",
            "node_count": node_count,
            "node_counters_index": "NODE_ID",
        },
        "node_counters": nodes,
        "per_step": steps,
        "wall_seconds": float(len(generated)),
    }


@pytest.fixture
def accepted_oracle(tmp_path: Path, monkeypatch):
    tokenizer_source = (
        Path.home()
        / ".cache/huggingface/hub"
        / "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots"
        / "7872f01b1d1fe23eabc4c98b48bffcef5a386062/tokenizer.json"
    )
    if not tokenizer_source.is_file():
        pytest.skip("pinned DeepSeek tokenizer is unavailable")
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "tokenizer.json").write_bytes(tokenizer_source.read_bytes())

    oracle = json.loads(tool.ORACLE.read_text())
    generated = [14] * tool.MAX_NEW_TOKENS
    raw = "," * tool.MAX_NEW_TOKENS
    result = oracle["results"][tool.WORKLOAD_ID]
    result.update(
        {
            "generated_token_ids": generated,
            "generated_token_count": len(generated),
            "stop_reason": "max_new_tokens",
            "max_new_tokens": tool.MAX_NEW_TOKENS,
            "expert_numeric_path": "fp8",
            "raw_decoded_text": raw,
            "visible_decoded_text": raw,
        }
    )
    oracle.update(
        {
            "run_status": "complete",
            "snapshot": str(checkpoint),
            "production_checkpoint_preflight": {
                "completed_before_workload_execution": True,
                "expected_file_count": 74,
                "full_byte_hash_verified": True,
                "full_byte_hash_verified_file_count": 74,
            },
            "production_launch": {
                "explicitly_requested": True,
                "contract": {
                    "workload_id": tool.WORKLOAD_ID,
                    "prompt_token_count": tool.PROMPT_TOKENS,
                    "max_new_tokens": tool.MAX_NEW_TOKENS,
                    "selection": "greedy_lowest_token_id_argmax",
                },
            },
        }
    )
    oracle_path = tmp_path / "oracle.json"
    oracle_path.write_text(json.dumps(oracle))
    monkeypatch.setattr(tool, "ORACLE", oracle_path)

    gate = {
        "schema": tool.GATE_B_SCHEMA,
        "accepted": True,
        "status": "accepted",
        "oracle_path": tool._relative(oracle_path),
        "workload": {
            "workload_path": tool._relative(tool.WORKLOAD),
            "workload_source_sha256": tool.WORKLOAD_SOURCE_SHA256,
            "workload_digest": tool.WORKLOAD_DIGEST,
            "workload_index_path": tool._relative(tool.WORKLOAD_INDEX),
            "workload_index_source_sha256": tool.WORKLOAD_INDEX_SHA256,
            "prompt_token_count": tool.PROMPT_TOKENS,
            "prompt_ids_legal": True,
            "rendered_text_sha256": tool.RENDERED_TEXT_SHA256,
        },
        "oracle": {
            "workload_id": tool.WORKLOAD_ID,
            "prompt_token_count": tool.PROMPT_TOKENS,
            "generated_token_count": len(generated),
            "generated_ids_legal": True,
            "terminal_rule": "exact_256_without_eos",
            "first_eos_position": None,
            "vendor_selection_agreement_count": len(generated),
            "decoded_text_exact": True,
            "prompt_reencoded_exact": True,
            "raw_decoded_text": raw,
            "visible_decoded_text": raw,
        },
        "checkpoint": {
            "snapshot": str(checkpoint),
            "source_sha256": tool.CHECKPOINT_SOURCE_SHA256,
            "expected_file_count": tool.CHECKPOINT_FILE_COUNT,
            "expected_total_file_bytes": tool.CHECKPOINT_TOTAL_BYTES,
            "full_byte_hash_requested": True,
            "full_byte_hash_verified": True,
            "full_byte_hash_verified_file_count": tool.CHECKPOINT_FILE_COUNT,
        },
        "dependency_separation": {"separated": True, "problems": []},
        "problems": [],
    }
    gate_path = tmp_path / "gate-b.json"
    gate_path.write_text(json.dumps(gate))
    return oracle_path, gate_path, checkpoint


@pytest.fixture
def passing_pair(tmp_path: Path, accepted_oracle):
    oracle_path, gate_path, checkpoint = accepted_oracle
    rom = _record(
        "rom_deepseek_v4", tmp_path / "rom-deployment", oracle_path, checkpoint
    )
    hbm = _record("hbm_sram", tmp_path / "hbm-deployment", oracle_path, checkpoint)
    return rom, hbm, gate_path


def _write_pair(
    tmp_path: Path, rom: dict[str, object], hbm: dict[str, object]
) -> tuple[Path, Path]:
    rom_path = tmp_path / "rom-record.json"
    hbm_path = tmp_path / "hbm-record.json"
    rom_path.write_text(json.dumps(rom))
    hbm_path.write_text(json.dumps(hbm))
    return rom_path, hbm_path


def _validate(tmp_path: Path, pair) -> dict[str, object]:
    rom, hbm, gate_path = pair
    rom_path, hbm_path = _write_pair(tmp_path, rom, hbm)
    return tool.validate(rom_path, hbm_path, gate_path)


def test_cli_help_states_the_fixed_pair_and_exact_contract() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(REPO / "tools/check_deepseek_v4_200k_accelerator_acceptance.py"),
            "--help",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    rendered = " ".join(completed.stdout.split())
    assert completed.returncode == 0
    assert "--rom-record" in rendered and "--hbm-record" in rendered
    assert "exactly 32 identical HBM/SRAM nodes" in rendered
    assert "ABI ``STATE`` descriptors" in rendered


def test_exact_200k_rom_hbm_pair_passes(tmp_path: Path, passing_pair) -> None:
    result = _validate(tmp_path, passing_pair)
    assert result["status"] == "accepted"
    assert result["accepted"] is True
    assert all(result["pair_checks"].values())
    assert result["abi_profile"] == {
        "version": "3.0",
        "execution_state": "ordinary_live_hbm_sram_buffers",
        "abi_state_descriptors": 0,
        "abi_state_instructions": 0,
        "durable_journal_checkpoint_or_model_retry": False,
        "run_failure_model": "uninterrupted_fail_stop",
    }
    assert result["token_evidence"]["input"]["token_count"] == 200_000
    assert result["token_evidence"]["output"]["token_count"] == 256
    assert result["token_evidence"]["output"]["visible_decoded_text"] == "," * 256


def test_rejected_gate_b_blocks_accelerator_acceptance(
    tmp_path: Path, passing_pair
) -> None:
    rom, hbm, gate_path = passing_pair
    gate = json.loads(gate_path.read_text())
    gate["accepted"] = False
    gate["status"] = "rejected"
    gate["problems"] = ["not complete"]
    gate_path.write_text(json.dumps(gate))
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert (
        "strict DeepSeek exact-200K oracle Gate B is not accepted" in result["problems"]
    )


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda rom, hbm: hbm["target"].__setitem__("node_count", 31),
            "target is not the source-current governed topology",
        ),
        (
            lambda rom, hbm: rom["target"].__setitem__("topology_class", 0),
            "target is not the source-current governed topology",
        ),
        (
            lambda rom, hbm: hbm["workload"]["prompt_token_ids"].pop(),
            "workload prompt tokens are not the frozen 200K prompt",
        ),
        (
            lambda rom, hbm: hbm["workload"].__setitem__("prompt_token_count", 199_999),
            "workload.prompt_token_count is not the frozen value",
        ),
        (
            lambda rom, hbm: hbm["node_counters"].pop(),
            "node_counters is not exactly 32 measured nodes",
        ),
        (
            lambda rom, hbm: rom["verification"].__setitem__("state_resources", 1),
            "nonzero ABI STATE resources",
        ),
        (
            lambda rom, hbm: hbm["counters"].__setitem__("state.prepares", 1),
            "ABI 3.0 live-buffer design",
        ),
        (
            lambda rom, hbm: rom["source_sha256"].__setitem__(
                "runtime/sim/device.py", "0" * 64
            ),
            "source is not current",
        ),
        (
            lambda rom, hbm: rom["target"].__setitem__("deployment_digest", "0" * 64),
            "serialized deployment digest differs from the record",
        ),
        (
            lambda rom, hbm: hbm["executed_association"].__setitem__(
                "manifest_sha256", "0" * 64
            ),
            "association manifest digest is invalid",
        ),
        (
            lambda rom, hbm: hbm["counters"].__setitem__(
                "selection.tokens_selected", 255 * 32
            ),
            "counter selection.tokens_selected",
        ),
    ],
)
def test_record_mutations_fail_closed(
    tmp_path: Path, passing_pair, mutate, expected: str
) -> None:
    rom, hbm, gate_path = passing_pair
    mutate(rom, hbm)
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any(expected in problem for problem in result["problems"])


def test_short_non_eos_output_is_rejected(tmp_path: Path, passing_pair) -> None:
    rom, hbm, gate_path = passing_pair
    for record in (rom, hbm):
        record["generated_token_ids"].pop()
        record["generated_token_count"] -= 1
        record["per_step"].pop()
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any("not exactly the 256-token cap" in item for item in result["problems"])


def test_post_eos_token_is_rejected(tmp_path: Path, passing_pair) -> None:
    rom, hbm, gate_path = passing_pair
    for record in (rom, hbm):
        record["generated_token_ids"][-2] = tool.EOS_TOKEN_ID
        record["per_step"][-2]["produced_tokens"] = [tool.EOS_TOKEN_ID]
        record["per_step"][-2]["final_token_id"] = tool.EOS_TOKEN_ID
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any(
        "continues after the first official EOS" in item for item in result["problems"]
    )


def test_first_official_eos_is_an_included_terminal_token() -> None:
    terminal, problems = tool._terminal_kind([14, 412, tool.EOS_TOKEN_ID], "eos")
    assert terminal == "eos"
    assert problems == []


def test_pair_token_mismatch_is_rejected(tmp_path: Path, passing_pair) -> None:
    rom, hbm, gate_path = passing_pair
    hbm["generated_token_ids"][4] = 15
    hbm["per_step"][4]["produced_tokens"] = [15]
    hbm["per_step"][4]["final_token_id"] = 15
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any("accepted Gate-B oracle" in item for item in result["problems"])
    assert result["pair_checks"]["full_token_sequences_identical"] is False


def test_oracle_decoded_text_mismatch_is_rejected(tmp_path: Path, passing_pair) -> None:
    rom, hbm, gate_path = passing_pair
    oracle_path = tool.ORACLE
    oracle = json.loads(oracle_path.read_text())
    oracle["results"][tool.WORKLOAD_ID]["raw_decoded_text"] += " altered"
    oracle_path.write_text(json.dumps(oracle))
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any(
        "decoded raw output does not equal the Gate-B oracle text" in item
        for item in result["problems"]
    )


def test_association_must_normalise_by_exactly_32(tmp_path: Path, passing_pair) -> None:
    rom, hbm, gate_path = passing_pair
    identity = hbm["implementation_identity"]
    hbm["executed_association"] = _association(identity, 63)
    hbm["host_performance"] = _host_performance(identity, 63)
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert (
        result["pair_checks"]["association_equal_after_32_node_normalisation"] is False
    )


def test_implementation_identity_mismatch_is_rejected(
    tmp_path: Path, passing_pair
) -> None:
    rom, hbm, gate_path = passing_pair
    changed = copy.deepcopy(hbm["implementation_identity"])
    changed["device_name"] = "another-host"
    hbm["implementation_identity"] = changed
    hbm["executed_association"] = _association(changed, 64)
    hbm["host_performance"] = _host_performance(changed, 64)
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert result["pair_checks"]["implementation_identities_identical"] is False


def test_logical_node_counter_mismatch_is_rejected(
    tmp_path: Path, passing_pair
) -> None:
    rom, hbm, gate_path = passing_pair
    hbm["node_counters"][17]["vector.elements"] += 1
    hbm["counters"]["vector.elements"] += 1
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert result["pair_checks"]["logical_node_counters_identical"] is False


def _replace_descriptor(deployment, descriptor_id: int, mutate) -> None:
    descriptor = copy.deepcopy(deployment.table[descriptor_id])
    mutate(descriptor)
    deployment.table._records[descriptor_id] = descriptor.encode()  # noqa: SLF001
    deployment.table._descriptors[descriptor_id] = descriptor  # noqa: SLF001


def _republish_mutated_deployment(record: dict, root: Path, deployment) -> None:
    from runtime.abi3.capability import Capability
    from runtime.abi3.verifier import verify_deployment

    backend = record["backend"]
    capability = Capability.from_dict(
        json.loads(tool.CAPABILITIES[backend].read_text())
    )
    abi3_helpers.restamp(deployment)
    deployment.write(root)
    digest = deployment.deployment_digest.hex()
    record["target"]["deployment_digest"] = digest
    record["inputs"]["checkpoint_root"]["deployment_digest_binding"] = digest
    record["inputs"]["published_deployment"] = {
        "path": tool._relative(root),
        "manifest": _identity(root / "deployment.json"),
        "descriptors": _identity(root / "descriptors.bin"),
        "program": _identity(root / "program.bin"),
    }
    record["verification"] = verify_deployment(deployment, capability).to_dict()


@pytest.mark.parametrize(
    ("surface", "expected"),
    [
        ("storage", "STATE storage object"),
        ("permission", "prepare/commit permissions"),
    ],
)
def test_serialized_state_memory_surfaces_are_rejected(
    tmp_path: Path, passing_pair, surface: str, expected: str
) -> None:
    from runtime.abi3.constants import Permission, StorageClass
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import ExtendedDescriptorType

    rom, hbm, gate_path = passing_pair
    root = tool._resolved_path(rom["inputs"]["published_deployment"]["path"])
    deployment = Deployment.read(root)
    live = next(
        descriptor.descriptor_id
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and int(descriptor.payload["storage_class"]) == int(StorageClass.HBM)
        and int(descriptor.permissions) & int(Permission.WRITE)
    )
    if surface == "storage":
        _replace_descriptor(
            deployment,
            live,
            lambda descriptor: descriptor.payload.__setitem__(
                "storage_class", int(StorageClass.STATE)
            ),
        )
    else:
        _replace_descriptor(
            deployment,
            live,
            lambda descriptor: setattr(
                descriptor,
                "permissions",
                int(descriptor.permissions) | int(Permission.STATE_PREPARE),
            ),
        )
    _republish_mutated_deployment(rom, root, deployment)
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any(expected in item for item in result["problems"])


def test_serialized_state_descriptor_and_instruction_are_rejected(
    tmp_path: Path, passing_pair
) -> None:
    from runtime.abi3.constants import (
        CommitPolicy,
        DType,
        Major,
        Permission,
        State,
        StateClass,
        StorageClass,
    )
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType
    from runtime.abi3.records import (
        Instruction,
        decode_body,
        encode_body,
        split_program,
    )

    rom, hbm, gate_path = passing_pair
    root = tool._resolved_path(rom["inputs"]["published_deployment"]["path"])
    deployment = Deployment.read(root)
    live = next(
        descriptor.descriptor_id
        for descriptor in deployment.table.descriptors()
        if descriptor.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and int(descriptor.payload["storage_class"]) == int(StorageClass.HBM)
        and int(descriptor.permissions) & int(Permission.WRITE)
    )
    state_id = deployment.table.add(
        Descriptor(
            descriptor_id=tool.NO_ID,
            descriptor_type=ExtendedDescriptorType.STATE,
            payload={
                "state_class": int(StateClass.KV_CACHE),
                "commit_policy": int(CommitPolicy.UNSTAGED),
                "element_dtype": int(DType.BF16),
                "session_binding_id": 0,
                "committed_object_id": live,
                "prepared_object_id": live,
                "row_bytes": 2,
                "capacity_rows": 1,
                "initial_cursor_rows": 0,
                "generation_bits": 64,
                "counter_class_id": tool.NO_ID,
                "view_descriptor_id": tool.NO_ID,
                "node_id": 0,
                "initial_digest": bytes(32),
            },
            primary_object_id=live,
            secondary_object_id=live,
            permissions=int(Permission.READ | Permission.STATE_PREPARE),
        )
    )
    _header, body = split_program(deployment.program)
    instructions = decode_body(body)
    instructions.insert(
        -1,
        Instruction(
            major=int(Major.STATE),
            sub=int(State.READ),
            descriptor_id=state_id,
        ),
    )
    abi3_helpers.restamp(deployment, body=encode_body(instructions))
    _republish_mutated_deployment(rom, root, deployment)
    result = _validate(tmp_path, (rom, hbm, gate_path))
    assert result["status"] == "rejected"
    assert any("ABI STATE descriptor" in item for item in result["problems"])
    assert any("ABI STATE instruction" in item for item in result["problems"])


def test_current_short_p32_records_remain_ineligible() -> None:
    result = tool.validate(
        REPO / "results/abi3/accelerator_tokens/deepseek_v4_flash_rom_p32.json",
        REPO / "results/abi3/accelerator_tokens/deepseek_v4_flash_hbm_p32.json",
        tool.DEFAULT_GATE_B,
    )
    assert result["status"] == "rejected"
    assert any("Gate B is not accepted" in item for item in result["problems"])
    assert not any("ABI STATE descriptor" in item for item in result["problems"])
    assert not any("ABI STATE instruction" in item for item in result["problems"])
    assert any("200K prompt" in item for item in result["problems"])
    assert any("256-token cap" in item for item in result["problems"])
