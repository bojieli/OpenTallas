from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import subprocess
import sys

from jsonschema import Draft202012Validator, ValidationError
import pytest

from compiler.frontend.checkpoint import load_checkpoint_lock
from compiler.tensor_accelerator.common import (
    canonical_json_bytes,
    load_strict_json,
    write_canonical_json,
)
from compiler.tensor_accelerator.production_capability import (
    load_production_capability,
)
from compiler.tensor_accelerator.production_command import (
    ABI_MAJOR,
    Opcode,
    SELECTION_ABI_MINOR,
    encode,
)
from compiler.tensor_accelerator.production_model import (
    compute_graph_id,
    load_production_model_graph,
)
from compiler.tensor_accelerator.qwen_full_model_context import (
    build_qwen_long_context_profile,
)
from compiler.tensor_accelerator.qwen_full_model_context_checking import (
    QwenFullModelContextCheckError,
    check_qwen_long_context_profile,
)
from compiler.tensor_accelerator.qwen_full_model_semantics import (
    build_qwen_full_model_semantics,
)
from compiler.tensor_accelerator.qwen_full_model_semantics_checking import (
    check_qwen_full_model_semantics,
)
from compiler.tensor_accelerator.qwen_full_model_physical import (
    _capacity_certificate,
    _commands,
    _physical_layout,
    _physical_plan,
    _source_lock,
    _sram_plan,
)
from compiler.tensor_accelerator.qwen_full_model_physical_checking import (
    COMMAND_PATH,
    _derive_hbm,
    _derive_sram,
    _verify_command_program,
)


ROOT = Path(__file__).resolve().parents[2]
BASE_GRAPH = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/"
    "source/model_graph.v2.json"
)
V6 = ROOT / "configs/hardware/tensor_accelerator_development_v6.json"
V7 = ROOT / "configs/hardware/tensor_accelerator_development_v7.json"
CONTEXT = ROOT / "results/tensor_accelerator/qwen3_long_acceptance_context_v1"
LONG_GRAPH = CONTEXT / "model_graph.v2.json"
PROFILE = CONTEXT / "context_profile.json"
CONTEXT_CHECK = CONTEXT / "independent_check.json"
LONG_FINAL = CONTEXT / "final_output_qualification.json"
BASE_FINAL = ROOT / "results/tensor_accelerator/qwen3_final_output_qualification.json"
LONG_SEMANTICS = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_semantics_v1"
)
QKV = ROOT / "results/tensor_accelerator/qwen3_qkv_qualification.json"
ATTENTION = ROOT / "results/tensor_accelerator/qwen3_attention_qualification.json"
LAYER = ROOT / "results/tensor_accelerator/qwen3_layer_qualification.json"
SCHEMAS = ROOT / "schemas/compiler/tensor_accelerator"
CHECKPOINT_LOCK = (
    ROOT
    / "results/tensor_accelerator/qwen3_full_model_physical/"
    "source/checkpoint.lock.json"
)
BASE_PHYSICAL = ROOT / "results/tensor_accelerator/qwen3_full_model_physical"
LONG_PHYSICAL = (
    ROOT / "results/tensor_accelerator/qwen3_long_acceptance_physical_v1"
)


def _reidentify(value: dict[str, object], field: str) -> None:
    value[field] = hashlib.sha256(
        canonical_json_bytes({key: item for key, item in value.items() if key != field})
    ).hexdigest()


def _fake_hbm_image(total_size: int) -> dict[str, object]:
    shard_bytes = 1 << 30
    records: list[dict[str, object]] = []
    offset = 0
    for index in range((total_size + shard_bytes - 1) // shard_bytes):
        size = min(shard_bytes, total_size - offset)
        digest = f"{index:064x}"
        records.append(
            {
                "index": index,
                "logical_offset": offset,
                "path": f"memory/hbm/hbm.{index:05d}.{digest}.bin",
                "sha256": digest,
                "size_bytes": size,
            }
        )
        offset += size
    return {
        "logical_sha256": "f" * 64,
        "shard_bytes": shard_bytes,
        "shards": records,
        "size_bytes": total_size,
    }


@pytest.fixture(scope="module")
def long_physical_fixture() -> dict[str, object]:
    model = load_production_model_graph(LONG_GRAPH)
    capability = load_production_capability(V7)
    checkpoint_lock = load_checkpoint_lock(CHECKPOINT_LOCK)
    forward_hbm = _physical_layout(model, capability, checkpoint_lock)
    assert forward_hbm == _derive_hbm(model, capability, checkpoint_lock)
    forward_sram = _sram_plan(model, capability)
    assert forward_sram == _derive_sram(model, capability)
    commands, ranges, counts = _commands(
        model=model,
        hbm=forward_hbm,
        sram=forward_sram,
    )
    command_payload = encode(commands, abi_minor=SELECTION_ABI_MINOR)
    command_program = {
        "abi": {"major": ABI_MAJOR, "minor": SELECTION_ABI_MINOR},
        "command_count": len(commands),
        "kernel_command_ranges": ranges,
        "opcode_counts": counts,
        "path": COMMAND_PATH,
        "sha256": hashlib.sha256(command_payload).hexdigest(),
        "size_bytes": len(command_payload),
    }
    _verify_command_program(
        model=model,
        hbm=forward_hbm,
        sram=forward_sram,
        payload=command_payload,
        candidate_program=command_program,
    )

    source_paths = {
        "capability": V7,
        "checkpoint_lock": CHECKPOINT_LOCK,
        "model_graph": LONG_GRAPH,
        "semantic_check": LONG_SEMANTICS / "independent_check.json",
        "semantic_coverage": LONG_SEMANTICS / "coverage.json",
        "semantic_kernel_ir": LONG_SEMANTICS / "tensor_kernel_ir.json",
    }
    coverage = load_strict_json(source_paths["semantic_coverage"])
    kernel_ir = load_strict_json(source_paths["semantic_kernel_ir"])
    semantic_check = load_strict_json(source_paths["semantic_check"])
    source_lock = _source_lock(
        model=model,
        capability=capability,
        checkpoint_lock=checkpoint_lock,
        coverage=coverage,
        kernel_ir=kernel_ir,
        semantic_check=semantic_check,
        source_paths=source_paths,
    )
    for weight in forward_hbm["weights"]:
        weight["deployed_payload_sha256"] = "0" * 64
    forward_hbm["metadata_table"]["payload_sha256"] = "1" * 64
    forward_hbm["descriptor_table"]["payload_sha256"] = "2" * 64
    forward_hbm["image"] = _fake_hbm_image(forward_hbm["total_size_bytes"])
    capacity = _capacity_certificate(
        capability=capability,
        hbm=forward_hbm,
        sram=forward_sram,
        command_count=len(commands),
    )
    physical_plan = _physical_plan(
        model=model,
        capability=capability,
        source_lock=source_lock,
        semantic_kernel_ir=kernel_ir,
        hbm=forward_hbm,
        sram=forward_sram,
        command_payload=command_payload,
        command_ranges=ranges,
        opcode_counts=counts,
        capacity=capacity,
    )
    return {
        "capacity": capacity,
        "commands": commands,
        "command_program": command_program,
        "hbm": forward_hbm,
        "physical_plan": physical_plan,
    }


def test_long_context_profile_is_exact_retained_and_independently_checked() -> None:
    graph, profile = build_qwen_long_context_profile(BASE_GRAPH)
    assert graph.to_dict() == load_strict_json(LONG_GRAPH)
    assert profile == load_strict_json(PROFILE)
    assert graph.graph_id == (
        "738f3cd8cb5db1ce400c0a44c12385cef6c42ddb2854e22d473251e97a1a51e3"
    )
    assert profile["profile_id"] == (
        "346697fcd9c02c09c9bd1ce36b8e854aa7bbfbb07a5db9b27f65bbbd28f39972"
    )
    checked = check_qwen_long_context_profile(
        base_graph_path=BASE_GRAPH,
        expanded_graph_path=LONG_GRAPH,
        profile_path=PROFILE,
    )
    assert checked == load_strict_json(CONTEXT_CHECK)
    assert checked["check_id"] == (
        "a475063363bd2b18447014c8466f6d858e7adc28c1a17b34b892d06f1e18a673"
    )


def test_long_context_changes_only_admitted_capacity_fields() -> None:
    base = load_strict_json(BASE_GRAPH)
    long = load_strict_json(LONG_GRAPH)
    assert base["operations"] == long["operations"]
    assert base["tensors"] == long["tensors"]
    assert base["state_resources"] == long["state_resources"]
    assert base["source"] == long["source"]
    assert base["model_id"] == long["model_id"]
    assert base["numeric_profile"] == long["numeric_profile"]
    assert [item["id"] for item in base["symbols"]] == [
        item["id"] for item in long["symbols"]
    ]
    symbols = {item["id"]: item for item in long["symbols"]}
    assert symbols["context_capacity"] == {
        "binding": {"kind": "compile_time"},
        "default": 8192,
        "id": "context_capacity",
        "maximum": 8192,
        "minimum": 8192,
        "multiple_of": 8192,
    }
    assert symbols["position_end"]["maximum"] == 8192
    assert symbols["position_start"]["maximum"] == 8191
    assert symbols["span_tokens"]["maximum"] == 8192
    assert [entry["predicate"]["terms"][1]["value"] for entry in long["entrypoints"]] == [
        8192,
        8192,
    ]
    base_symbols = {item["id"]: item for item in base["symbols"]}
    assert base_symbols["context_capacity"]["maximum"] == 8000


def test_v7_extends_only_vector_context_bounds_and_authenticates() -> None:
    v6 = load_strict_json(V6)
    v7 = load_strict_json(V7)
    expected = copy.deepcopy(v6)
    expected["vector_engine"]["max_attention_context_tokens"] = 8192
    expected["vector_engine"]["max_rope_positions"] = 8192
    expected["capability_id"] = v7["capability_id"]
    assert v7 == expected
    capability = load_production_capability(V7)
    assert capability.capability_id == (
        "a9b231b5f146f845257325e68031f02440f0a3712db42d4e4e2b54c69031f6cd"
    )
    assert capability.command_abi_major == 2
    assert capability.command_abi_minor == 5
    assert capability.vector_engine is not None
    assert capability.vector_engine.max_attention_context_tokens == 8192
    assert capability.vector_engine.max_rope_positions == 8192


def test_long_semantics_are_retained_and_independently_reconstructed() -> None:
    coverage, kernel_ir = build_qwen_full_model_semantics(
        model_graph_path=LONG_GRAPH,
        capability_path=V7,
        qkv_qualification_path=QKV,
        attention_qualification_path=ATTENTION,
        layer_qualification_path=LAYER,
        final_output_qualification_path=LONG_FINAL,
    )
    retained_coverage = load_strict_json(LONG_SEMANTICS / "coverage.json")
    retained_kernel = load_strict_json(LONG_SEMANTICS / "tensor_kernel_ir.json")
    assert coverage == retained_coverage
    assert kernel_ir == retained_kernel
    assert coverage["report_id"] == (
        "2d8a5c6d0c7f60c28ad8f1c59c4487417133e7f1ff14578e16652ddd303f2a21"
    )
    assert kernel_ir["kernel_ir_id"] == (
        "35bae3f71666c72ec886875abf336fefc68dd1635288d3b49720c4297d4cc1e1"
    )
    assert kernel_ir["kernels"][0]["shape"]["rows"]["maximum"] == 8192
    assert kernel_ir["kernels"][7]["attributes"]["max_positions"] == 8192
    assert kernel_ir["kernels"][8]["shape"]["max_context_tokens"] == 8192
    assert kernel_ir["kernels"][9]["shape"]["max_context_tokens"] == 8192
    assert kernel_ir["kernels"][614]["shape"]["maximum_rows"] == 8192
    check = check_qwen_full_model_semantics(
        model_graph_path=LONG_GRAPH,
        capability_path=V7,
        coverage_path=LONG_SEMANTICS / "coverage.json",
        kernel_ir_path=LONG_SEMANTICS / "tensor_kernel_ir.json",
        qkv_qualification_path=QKV,
        attention_qualification_path=ATTENTION,
        layer_qualification_path=LAYER,
        final_output_qualification_path=LONG_FINAL,
    )
    assert check == load_strict_json(LONG_SEMANTICS / "independent_check.json")
    assert check["check_id"] == (
        "48a2b845dd61dac94d5741184f1d3f1a1c827a3030f8a183d4966b281254d0bb"
    )


def test_long_physical_layout_and_commands_are_independently_derived(
    long_physical_fixture: dict[str, object],
) -> None:
    hbm = long_physical_fixture["hbm"]
    capacity = long_physical_fixture["capacity"]
    commands = long_physical_fixture["commands"]
    command_program = long_physical_fixture["command_program"]
    assert hbm["coefficient_table"] == {
        "address": 16_384_425_984,
        "layout": "position_major_cos_then_sin_bf16",
        "offset_bytes": 16_384_425_984,
        "payload_sha256": (
            "aeaab0b9af138b2f7464ed38c925ca4ab2faa6de294a49d3e579003e70f7051b"
        ),
        "positions": 8192,
        "row_bytes": 512,
        "size_bytes": 4_194_304,
    }
    assert hbm["mutable_kv_bytes"] == 1_207_959_552
    assert hbm["alignment_padding_bytes"] == 5_675_008
    assert hbm["total_size_bytes"] == 17_599_304_192
    assert len(hbm["states"]) == 36
    assert {
        (state["max_context_tokens"], state["size_bytes_per_plane"])
        for state in hbm["states"]
    } == {(8192, 16_777_216)}
    assert capacity["capacity_certificate_id"] == (
        "3b2411a77adb66bc4e7b32fdccb8dad0ab69609a225b94d4046abcc96e94a3fd"
    )
    assert capacity["context_capacity_tokens"] == 8192
    assert 8031 <= capacity["context_capacity_tokens"]
    assert 8193 > capacity["context_capacity_tokens"]

    assert command_program["command_count"] == 924_386
    assert command_program["size_bytes"] == 59_160_736
    assert command_program["sha256"] == (
        "dfc7ee4d89a091aea616f602174f8bd41cae319ceec92d31fda4cb43636dce6d"
    )
    indexed_context_commands = [
        command
        for command in commands
        if command.opcode is Opcode.DMA_HBM_INDEXED_TO_SRAM
        and command.size2 == 8192
    ]
    assert len(indexed_context_commands) == 36
    assert commands[-2].opcode is Opcode.STATE_COMMIT
    assert commands[-2].size0 == 8192
    assert commands[-2].size1 == 36


def test_long_physical_profile_preserves_the_retained_v6_boundary(
    long_physical_fixture: dict[str, object],
) -> None:
    retained = load_strict_json(BASE_PHYSICAL / "physical/physical_plan.json")
    retained_capacity = load_strict_json(
        BASE_PHYSICAL / "physical/capacity_certificate.json"
    )
    assert retained["command_program"]["command_count"] == 924_386
    assert retained["command_program"]["sha256"] == (
        "f0ce6b50b01f462f837a28504e6ff9a024a24d24abf339f924875d0c2059bcec"
    )
    assert retained["hbm"]["coefficient_table"]["positions"] == 8000
    assert retained["hbm"]["mutable_kv_bytes"] == 1_179_648_000
    assert retained["hbm"]["total_size_bytes"] == 17_573_089_792
    assert retained_capacity["capacity_certificate_id"] == (
        "e0e63f0aeab52582591111d360ae2c92a9cdc968c020c8594d7f71805fe81263"
    )
    assert (
        long_physical_fixture["command_program"]["sha256"]
        != retained["command_program"]["sha256"]
    )


def test_authentic_long_physical_deployment_is_retained_and_checked() -> None:
    manifest = load_strict_json(LONG_PHYSICAL / "deployment_manifest.json")
    plan = load_strict_json(LONG_PHYSICAL / "physical/physical_plan.json")
    capacity = load_strict_json(
        LONG_PHYSICAL / "physical/capacity_certificate.json"
    )
    check = load_strict_json(LONG_PHYSICAL / "checks/independent_check.json")
    assert manifest["build_id"] == (
        "6445ef52a940af167f3bde52e0a326258bb8c8da013d4bb25a3b16e18f171bad"
    )
    assert manifest["physical_plan_id"] == plan["physical_plan_id"] == (
        "2bb30b4bc970b3c0af716eb78b86d3158ed06108218735b515d8e2133dc407a2"
    )
    assert manifest["capacity_certificate_id"] == capacity[
        "capacity_certificate_id"
    ] == "3b2411a77adb66bc4e7b32fdccb8dad0ab69609a225b94d4046abcc96e94a3fd"
    assert manifest["independent_check_id"] == check["check_id"] == (
        "af1545ca635b7400de621a297f8ef8118d07cdab51ab3ca9fb739d4b23fa9c45"
    )
    assert manifest["graph_id"] == load_strict_json(LONG_GRAPH)["graph_id"]
    assert manifest["capability_id"] == load_strict_json(V7)["capability_id"]
    assert manifest["kernel_ir_id"] == load_strict_json(
        LONG_SEMANTICS / "tensor_kernel_ir.json"
    )["kernel_ir_id"]
    assert len(manifest["artifacts"]) == 31
    assert check["status"] == "pass"
    assert check["command_count"] == 924_386
    assert check["hbm_logical_sha256"] == (
        "55fbb4f91ff9a081dede418edec25d7373553a591ce3c031a27d219048b90b97"
    )
    assert check["checks"] and all(check["checks"].values())
    assert len(plan["hbm"]["image"]["shards"]) == 17
    assert plan["hbm"]["image"]["shards"][-1]["size_bytes"] == 419_435_008


def test_long_physical_artifacts_validate_as_one_strict_profile(
    long_physical_fixture: dict[str, object],
) -> None:
    cases = (
        (
            "qwen_full_model_capacity_v1.schema.json",
            long_physical_fixture["capacity"],
        ),
        (
            "qwen_full_model_physical_plan_v1.schema.json",
            long_physical_fixture["physical_plan"],
        ),
    )
    for schema_name, artifact in cases:
        schema = load_strict_json(SCHEMAS / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(artifact)

    mixed_capacity = copy.deepcopy(long_physical_fixture["capacity"])
    mixed_capacity["context_capacity_tokens"] = 8000
    capacity_schema = load_strict_json(
        SCHEMAS / "qwen_full_model_capacity_v1.schema.json"
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(capacity_schema).validate(mixed_capacity)

    mixed_plan = copy.deepcopy(long_physical_fixture["physical_plan"])
    mixed_plan["hbm"]["states"][0]["max_context_tokens"] = 8000
    plan_schema = load_strict_json(
        SCHEMAS / "qwen_full_model_physical_plan_v1.schema.json"
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(plan_schema).validate(mixed_plan)


def test_long_final_output_is_authentically_rebound_without_numeric_drift() -> None:
    base = load_strict_json(BASE_FINAL)
    long = load_strict_json(LONG_FINAL)
    assert long["graph_id"] == load_strict_json(LONG_GRAPH)["graph_id"]
    assert long["report_id"] == (
        "1491eac1e6c4e19381db86920d10cc16ed067719159113ab295a4077ffbe6e81"
    )
    for field in ("outputs", "rmsnorm", "selected_reference", "sources"):
        assert long[field] == base[field]
    stripped_base = {key: value for key, value in base.items() if key not in {"graph_id", "report_id"}}
    stripped_long = {key: value for key, value in long.items() if key not in {"graph_id", "report_id"}}
    assert stripped_long == stripped_base


def test_long_context_artifacts_validate_strict_schemas() -> None:
    cases = (
        ("qwen_full_model_context_profile_v1.schema.json", PROFILE),
        (
            "qwen_full_model_context_profile_check_v1.schema.json",
            CONTEXT_CHECK,
        ),
    )
    for schema_name, artifact in cases:
        schema = load_strict_json(SCHEMAS / schema_name)
        Draft202012Validator.check_schema(schema)
        Draft202012Validator(schema).validate(load_strict_json(artifact))


def test_long_context_checker_rejects_semantic_drift_and_overclaim(
    tmp_path: Path,
) -> None:
    graph = load_strict_json(LONG_GRAPH)
    graph["operations"][2]["numeric_contract"] = "reassociated"
    graph["graph_id"] = compute_graph_id(graph)
    forged_graph = tmp_path / "forged-graph.json"
    write_canonical_json(forged_graph, graph)
    with pytest.raises(
        QwenFullModelContextCheckError,
        match="independent context reconstruction",
    ):
        check_qwen_long_context_profile(
            base_graph_path=BASE_GRAPH,
            expanded_graph_path=forged_graph,
            profile_path=PROFILE,
        )

    profile = load_strict_json(PROFILE)
    profile["claim_boundary"]["qwen_8192_boundary_executed"] = True
    _reidentify(profile, "profile_id")
    forged_profile = tmp_path / "forged-profile.json"
    write_canonical_json(forged_profile, profile)
    with pytest.raises(QwenFullModelContextCheckError, match="claim differs"):
        check_qwen_long_context_profile(
            base_graph_path=BASE_GRAPH,
            expanded_graph_path=LONG_GRAPH,
            profile_path=forged_profile,
        )
    schema = load_strict_json(
        SCHEMAS / "qwen_full_model_context_profile_v1.schema.json"
    )
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(profile)


def test_long_context_bundle_is_reproducible_and_nonoverwriting(
    tmp_path: Path,
) -> None:
    output = tmp_path / "long-context"
    command = [
        sys.executable,
        str(ROOT / "tools/build_qwen3_tensor_accelerator_long_context.py"),
        "--output",
        str(output),
    ]
    first = subprocess.run(
        command,
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert "738f3cd8" in first.stdout
    for filename in ("model_graph.v2.json", "context_profile.json", "independent_check.json"):
        assert (output / filename).read_bytes() == (CONTEXT / filename).read_bytes()
    second = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert second.returncode != 0
    assert "will not be overwritten" in second.stderr


def test_context_checker_does_not_import_context_generator() -> None:
    source = (
        ROOT
        / "compiler/tensor_accelerator/"
        "qwen_full_model_context_checking.py"
    ).read_text(encoding="utf-8")
    assert "qwen_full_model_context import" not in source
