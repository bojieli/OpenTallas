"""Kimi-K3 (KDA linear attention) and MiMo-V2.6 candidate profiles.

Covers the attention-core operation terms added to ``AttentionGroup`` and the
fallback operation inventory, the recurrent-state traffic of a KDA layer, and
the header-derived MiMo-V2.6 profiles.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from opentallas.operations import operation_inventory
from opentallas.profiling import _parameter_count
from opentallas.schema import AttentionGroup, ModelProfile, ValidationError
from opentallas.workload import kv_traffic


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "configs" / "models" / "candidates"
OP_FIELDS = ("operations_per_token", "operations_per_entry", "operations_format")


def kimi() -> ModelProfile:
    return ModelProfile.load(CANDIDATES / "kimi-k3-attention_ops.json")


def legacy_kimi() -> ModelProfile:
    return ModelProfile.load(ROOT / "configs" / "models" / "kimi-k3.json")


def mimo(size: str) -> ModelProfile:
    return ModelProfile.load(CANDIDATES / f"mimo-v2.6-{size}.json")


# --- schema ---------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json",
        ROOT / "configs" / "models" / "deepseek-v4-pro-0813.json",
        ROOT / "configs" / "models" / "kimi-k3.json",
        ROOT / "configs" / "models" / "qwen3-8b.json",
        CANDIDATES / "deepseek-v4.1-flash.json",
    ],
)
def test_profiles_that_predate_the_operation_fields_serialise_without_them(path: Path) -> None:
    profile = ModelProfile.load(path)
    for group in profile.to_dict()["attention_groups"]:
        assert not set(OP_FIELDS) & set(group)


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "window", "operations_per_token": 1.0},
        {"kind": "dense_kv", "window_tokens": 0, "operations_per_token": 1.0},
        {
            "kind": "compressed_dense",
            "compression_ratio": 4,
            "window_tokens": 0,
            "operations_per_entry": 1.0,
        },
        {"kind": "window", "operations_per_entry": -1.0},
    ],
)
def test_operation_fields_are_refused_where_they_mean_nothing(overrides: dict) -> None:
    base = dict(kind="window", count=1, entry_bytes=1024.0, window_tokens=128)
    base.update(overrides)
    with pytest.raises(ValidationError):
        AttentionGroup(**base)


def test_recurrent_group_accepts_a_per_token_operation_count() -> None:
    group = AttentionGroup(
        kind="recurrent", count=2, recurrent_state_bytes=64.0, operations_per_token=10.0
    )
    assert group.operations_per_token == 10.0
    with pytest.raises(ValidationError):
        AttentionGroup(
            kind="recurrent", count=2, recurrent_state_bytes=64.0, operations_per_entry=1.0
        )


# --- operation inventory ---------------------------------------------------


def test_legacy_kimi_inventory_is_the_active_parameter_identity() -> None:
    model = legacy_kimi()
    inventory = operation_inventory(model, 200_000)
    assert inventory.total_tensor_operations == pytest.approx(2.0 * model.active_parameters)
    assert not any(c.name.startswith("attention_") for c in inventory.components)


def test_kda_state_update_is_context_independent_and_fp32() -> None:
    model = kimi()
    heads, dim, kernel, layers = 96, 128, 4, 69
    expected = layers * (heads * 7 * dim * dim + 3 * heads * dim * 2 * kernel)
    for context in (8_192, 200_000, 1_000_000):
        inventory = operation_inventory(model, context)
        assert inventory.operations_for("fp32_x_fp32") == pytest.approx(expected)
    names = operation_inventory(model, 8_192).named_operations()
    assert names["attention_state_update:kda"] == pytest.approx(expected)


def test_mla_core_grows_linearly_with_context() -> None:
    model = kimi()
    per_entry = 2 * 96 * (512 + 64) + 2 * 96 * 512
    low = operation_inventory(model, 8_192).named_operations()["attention_core:gated-mla"]
    high = operation_inventory(model, 200_000).named_operations()["attention_core:gated-mla"]
    assert low == pytest.approx(24 * per_entry * 8_192)
    assert high == pytest.approx(24 * per_entry * 200_000)
    # Weight arithmetic is exactly the legacy identity on top of which the
    # attention terms sit.
    weights = sum(
        c.operations
        for c in operation_inventory(model, 8_192).components
        if c.name.startswith("active_parameter")
    )
    assert weights == pytest.approx(2.0 * model.active_parameters)


def test_window_core_stops_growing_at_the_window() -> None:
    model = mimo("flash")
    swa = [g for g in model.attention_groups if g.kind == "window"][0]
    at_window = operation_inventory(model, 128).named_operations()["attention_core:swa"]
    beyond = operation_inventory(model, 200_000).named_operations()["attention_core:swa"]
    assert at_window == beyond == pytest.approx(swa.count * swa.operations_per_entry * 128)


# --- KDA state traffic -----------------------------------------------------


def test_kda_state_is_read_and_written_whole_every_token() -> None:
    model = kimi()
    state = 69 * (96 * 128 * 128 * 4 + 3 * 96 * 128 * 3 * 2)
    for context in (8_192, 1_000_000):
        traffic = kv_traffic(model, context)
        kda = next(item for item in traffic.breakdown if item["kind"] == "recurrent")
        assert kda["read_bytes"] == kda["write_bytes"] == kda["storage_bytes_per_user"] == state
        assert traffic.storage_bytes_per_user == pytest.approx(state + 24 * 576 * context)
    meta = model.metadata["kda_state"]
    assert meta["bytes_per_user"] == state
    # Past ~32.5K tokens the MLA cache, not the recurrent state, dominates.
    assert meta["context_at_which_mla_cache_equals_kda_state"] == pytest.approx(state / (24 * 576))


def test_kimi_candidate_differs_from_legacy_only_by_the_operation_terms() -> None:
    old = legacy_kimi().to_dict()
    new = kimi().to_dict()
    for key in old:
        if key in {"attention_groups", "metadata"}:
            continue
        assert old[key] == new[key], key
    for before, after in zip(old["attention_groups"], new["attention_groups"]):
        stripped = {k: v for k, v in after.items() if k not in OP_FIELDS}
        assert stripped == before


# --- MiMo-V2.6 -------------------------------------------------------------


@pytest.mark.parametrize(
    ("size", "layers", "global_layers", "global_entry", "swa_entry", "experts", "total", "active"),
    [
        ("pro", 70, 10, 8 * 320 * 2, 8 * 320 * 2, 384, 1.02e12, 42e9),
        ("flash", 48, 9, 4 * 320 * 2, 8 * 320 * 2, 256, 309e9, 15e9),
    ],
)
def test_mimo_profiles_match_the_published_architecture(
    size, layers, global_layers, global_entry, swa_entry, experts, total, active
) -> None:
    model = mimo(size)
    assert model.num_layers == layers
    assert model.num_experts == experts and model.experts_per_token == 8
    groups = {g.kind: g for g in model.attention_groups}
    assert groups["dense_kv"].count == global_layers
    assert groups["dense_kv"].entry_bytes == global_entry
    assert groups["window"].count == layers - global_layers
    assert groups["window"].entry_bytes == swa_entry
    assert groups["window"].window_tokens == 128
    assert not any(g.kind == "recurrent" for g in model.attention_groups)
    counts = model.metadata["parameter_counts"]
    assert sum(counts.values()) == pytest.approx(total, rel=0.02)
    # Header-derived decode-active parameters exclude only the input embedding.
    assert model.metadata["decode_active_parameters_from_headers"] == pytest.approx(
        active, rel=0.05
    )
    sequence = model.metadata["attention_sequence"]
    assert sequence[0] == "global-gqa" and sequence.count("global-gqa") == global_layers


def test_mimo_kv_is_linear_in_context_beyond_the_window() -> None:
    model = mimo("pro")
    low = kv_traffic(model, 8_192).read_bytes
    high = kv_traffic(model, 200_000).read_bytes
    swa = 60 * 128 * 5120
    assert low == pytest.approx(swa + 10 * 5120 * 8_192)
    assert high == pytest.approx(swa + 10 * 5120 * 200_000)


# --- header parameter counting ----------------------------------------------


def test_packed_u8_experts_count_two_parameters_per_byte() -> None:
    name = "model.layers.1.mlp.experts.0.gate_proj.weight"
    assert _parameter_count(name, "U8", [2048, 2048]) == 2 * 2048 * 2048
    assert _parameter_count(name + "_scale", "U8", [2048, 128]) == 0
    kimi_name = "language_model.model.layers.1.block_sparse_moe.experts.0.w1.weight_packed"
    assert _parameter_count(kimi_name, "U8", [10, 10]) == 200
    assert _parameter_count("model.layers.0.self_attn.qkv_proj.weight_scale_inv", "F32", [4, 4]) == 0
    # A dense BF16 tensor is unchanged.
    assert _parameter_count("model.layers.0.self_attn.o_proj.weight", "BF16", [4, 8]) == 32


# --- study wiring -----------------------------------------------------------


def test_every_candidate_model_has_a_serial_depth_entry() -> None:
    sys.path.insert(0, str(ROOT / "tools"))
    import run_roofline_studies as studies

    table = json.loads((ROOT / "configs" / "hardware" / "technology.json").read_text())[
        "latency"
    ]["array_pass_boundaries_per_layer_by_model"]
    slugs = {entry[0] for entry in studies.CANDIDATE_MODELS}
    assert {"kimi-k3", "kimi-k3-8k", "kimi-k3-1m", "mimo-v26-pro", "mimo-v26-flash"} <= slugs
    for _slug, name, path, context in studies.CANDIDATE_MODELS:
        assert name in table
        profile = ModelProfile.load(path)
        assert profile.name == name
        assert context <= profile.max_context_tokens
    with pytest.raises(SystemExit):
        studies._candidate_files(Path("unused"), None, {}, ("no-such-candidate",))
