"""The DeepSeek-V4.1-Flash tensor contract, against everything that can check it.

Gate DS41-S1's exit criterion is that the derived contract reproduces the
released storage exactly -- 96,085 tensors and 510,286,023,000 bytes -- which is
a cross-check against ``data/inventory/deepseek-v4.1-flash.json`` and needs no
weight bytes, because the inventory is header-derived.  That check runs here
unconditionally.

Two stronger witnesses run when the host has them, and are skipped rather than
weakened when it does not: the 48 pinned shard headers cached under
``.cache/hf/headers/`` (name, dtype and shape for every tensor) and the released
``model.safetensors.index.json`` in the pinned snapshot (the exact name set and
``metadata.total_size``).  Both are host caches outside the repository, so a
clean checkout runs the inventory cross-check and skips these.
"""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
import re

import pytest

from compiler.frontend.checkpoint import (
    DTYPE_BITS,
    load_checkpoint_source,
    validate_checkpoint_lock,
)
from compiler.frontend.deepseek_v4 import build_official_tensor_specs as v4_specs
from compiler.ir.model import canonical_json_bytes
from compiler.frontend.deepseek_v4_releases import FLASH, PRO, V41_FLASH
from compiler.frontend.deepseek_v41 import (
    PAYLOAD_BYTES,
    TENSOR_COUNT,
    TENSOR_STRUCTURE_SHA256,
    DeepSeekV41AdapterError,
    TensorSpec,
    build_official_tensor_specs,
    load_official_config,
    tensor_structure_sha256,
)


ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "data/inventory/deepseek-v4.1-flash.json"
HEADER_CACHE = (
    ROOT / ".cache/hf/headers" / V41_FLASH.repository.replace("/", "--")
    / V41_FLASH.revision
)


@pytest.fixture(scope="module")
def official_config() -> dict:
    return load_official_config()


@pytest.fixture(scope="module")
def specs(official_config: dict) -> tuple[TensorSpec, ...]:
    return build_official_tensor_specs(official_config)


@pytest.fixture(scope="module")
def by_name(specs: tuple[TensorSpec, ...]) -> dict[str, TensorSpec]:
    return {spec.name: spec for spec in specs}


@pytest.fixture(scope="module")
def inventory() -> dict:
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def header_tensors() -> dict[str, tuple[str, tuple[int, ...]]]:
    """Name, dtype and shape for every tensor in the 48 pinned shard headers."""

    if not HEADER_CACHE.is_dir():
        pytest.skip(f"no pinned shard headers cached at {HEADER_CACHE}")
    shards = sorted(HEADER_CACHE.glob("*.safetensors.json"))
    if len(shards) != V41_FLASH.shard_count:
        pytest.skip(
            f"{len(shards)} cached headers, not the pinned {V41_FLASH.shard_count}"
        )
    tensors: dict[str, tuple[str, tuple[int, ...]]] = {}
    for shard in shards:
        for name, record in json.loads(shard.read_text(encoding="utf-8")).items():
            if name == "__metadata__":
                continue
            assert name not in tensors, f"{name} appears in two shards"
            tensors[name] = (record["dtype"], tuple(record["shape"]))
    return tensors


@pytest.fixture(scope="module")
def released_index() -> dict:
    path = V41_FLASH.checkpoint_index
    if not path.is_file():
        pytest.skip(f"no released checkpoint index at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _pattern(name: str) -> str:
    value = re.sub(r"(?<=layers\.)\d+", "{layer}", name)
    value = re.sub(r"(?<=experts\.)\d+", "{expert}", value)
    value = re.sub(r"(?<=blocks\.)\d+", "{block}", value)
    return re.sub(r"(?<=mtp\.)\d+", "{mtp}", value)


# -- the exit criterion ---------------------------------------------------


def test_contract_reproduces_the_released_storage(
    specs: tuple[TensorSpec, ...], inventory: dict
) -> None:
    """DS41-S1: 96,085 tensors and 510,286,023,000 bytes, without the weights."""

    assert len(specs) == TENSOR_COUNT == inventory["tensor_count"] == 96_085
    payload = sum(spec.size_bytes for spec in specs)
    assert payload == PAYLOAD_BYTES == 510_286_023_000
    assert payload == inventory["checkpoint_bytes"] == inventory["header_storage_bytes"]
    assert tensor_structure_sha256(specs) == TENSOR_STRUCTURE_SHA256


def test_per_dtype_counts_and_bytes_match_the_governed_inventory(
    specs: tuple[TensorSpec, ...], inventory: dict
) -> None:
    """Not just the totals: the split across all five storage dtypes.

    Two errors that cancel in the total -- an FP8 weight generated as BF16 while
    a BF16 one is generated as FP8 -- move this split, so it is the check that
    makes the total meaningful.
    """

    counts = Counter(spec.storage_dtype for spec in specs)
    sizes: Counter[str] = Counter()
    for spec in specs:
        sizes[spec.storage_dtype] += spec.size_bytes
    assert dict(sorted(counts.items())) == inventory["dtype_tensor_counts"]
    assert dict(sorted(sizes.items())) == inventory["dtype_bytes"]
    assert set(counts) == {"BF16", "F32", "F8_E4M3", "F8_E8M0", "I8"}


def test_every_spec_size_follows_from_its_dtype_and_shape(
    specs: tuple[TensorSpec, ...],
) -> None:
    for spec in specs:
        assert spec.storage_dtype in DTYPE_BITS
        assert all(extent > 0 for extent in spec.shape)
        assert spec.size_bytes == (
            math.prod(spec.shape) * DTYPE_BITS[spec.storage_dtype] // 8
        )


# -- against the pinned shard headers ------------------------------------


def test_contract_equals_the_pinned_shard_headers_tensor_for_tensor(
    by_name: dict[str, TensorSpec],
    header_tensors: dict[str, tuple[str, tuple[int, ...]]],
) -> None:
    """The evidence the record's ``tensor_structure_evidence`` claims.

    Name for name, dtype for dtype, extent for extent, against headers read off
    the released shards rather than anything this front end wrote.
    """

    assert V41_FLASH.tensor_structure_evidence == "shard_header_inventory"
    assert sorted(by_name) == sorted(header_tensors)
    mismatched = [
        (
            name,
            (by_name[name].storage_dtype, by_name[name].shape),
            header_tensors[name],
        )
        for name in sorted(by_name)
        if (by_name[name].storage_dtype, by_name[name].shape) != header_tensors[name]
    ]
    assert mismatched == []
    assert len(header_tensors) == TENSOR_COUNT
    assert (
        sum(
            math.prod(shape) * DTYPE_BITS[dtype] // 8
            for dtype, shape in header_tensors.values()
        )
        == PAYLOAD_BYTES
    )


def test_contract_equals_the_released_index_name_set_and_total_size(
    by_name: dict[str, TensorSpec], released_index: dict
) -> None:
    assert sorted(by_name) == sorted(released_index["weight_map"])
    assert released_index["metadata"]["total_size"] == PAYLOAD_BYTES
    assert (
        len(set(released_index["weight_map"].values())) == V41_FLASH.shard_count == 48
    )


# -- the structure the CED implies ---------------------------------------


def test_only_kv_source_layers_own_a_compressor_and_an_index_key(
    by_name: dict[str, TensorSpec],
) -> None:
    """The CED's defining property, read back off the generated names."""

    kv_sources = V41_FLASH.scalar("kv_source_layer_ids")
    for role in ("compressor.norm.weight", "compressor.wkv.weight"):
        owners = sorted(
            int(match.group(1))
            for name in by_name
            if (match := re.fullmatch(rf"layers\.(\d+)\.attn\.{re.escape(role)}", name))
        )
        assert owners == kv_sources, role
    for role in ("indexer.k_norm.weight", "indexer.wk.weight"):
        owners = sorted(
            int(match.group(1))
            for name in by_name
            if (match := re.fullmatch(rf"layers\.(\d+)\.attn\.{re.escape(role)}", name))
        )
        assert owners == kv_sources, role
    # Every other layer has no compressor at all: it reads the published latent.
    assert not [
        name
        for name in by_name
        if ".compressor." in name
        and int(name.split(".")[1]) not in kv_sources
        and name.startswith("layers.")
    ]
    assert not [name for name in by_name if name.startswith("mtp.") and "compressor" in name]


def test_only_ratio_above_one_compressors_own_a_pooling_gate(
    by_name: dict[str, TensorSpec],
) -> None:
    """Layer 20 is a KV source at ratio 1, so it has ``wkv`` and no ``wgate``.

    This is the case a frozen "KV source implies a gate" rule would get wrong,
    and it is exactly one layer of forty, so it is named.
    """

    ratios = V41_FLASH.main_compress_ratios
    gated = sorted(
        int(match.group(1))
        for name in by_name
        if (
            match := re.fullmatch(
                r"layers\.(\d+)\.attn\.compressor\.wgate\.weight", name
            )
        )
    )
    kv_sources = V41_FLASH.scalar("kv_source_layer_ids")
    assert gated == [layer for layer in kv_sources if ratios[layer] > 1]
    assert gated == [2, 8, 14]
    assert 20 in kv_sources and ratios[20] == 1
    assert "layers.20.attn.compressor.wkv.weight" in by_name
    assert "layers.20.attn.compressor.wgate.weight" not in by_name
    # V4's per-ratio position table is gone from V4.1 entirely.
    assert not [name for name in by_name if name.endswith(".compressor.ape")]


def test_index_source_layers_own_the_query_side_only(
    by_name: dict[str, TensorSpec],
) -> None:
    index_sources = V41_FLASH.scalar("index_source_layer_ids")
    for role in ("indexer.weights_proj.weight", "indexer.wq_b.weight"):
        owners = sorted(
            int(match.group(1))
            for name in by_name
            if (match := re.fullmatch(rf"layers\.(\d+)\.attn\.{re.escape(role)}", name))
        )
        assert owners == index_sources, role
    query_only = sorted(set(index_sources) - set(V41_FLASH.scalar("kv_source_layer_ids")))
    assert query_only == [24, 28, 32, 36]
    for layer in query_only:
        assert f"layers.{layer}.attn.indexer.wq_b.weight" in by_name
        assert f"layers.{layer}.attn.indexer.wk.weight" not in by_name
        assert f"layers.{layer}.attn.indexer.k_norm.weight" not in by_name


def test_engram_tables_are_per_layer_and_sized_from_their_own_row_count(
    by_name: dict[str, TensorSpec], official_config: dict
) -> None:
    """The two tables differ by 10,514 rows, so one row count cannot serve both."""

    text = official_config["text_config"]
    layers = text["engram_layer_ids"]
    rows = text["engram_num_embeddings"]
    head_dim = text["engram_head_dim"]
    block = V41_FLASH.quantization_config["weight_block_size"][1]
    assert rows[0] != rows[1]

    owners = sorted(
        int(match.group(1))
        for name in by_name
        if (match := re.fullmatch(r"layers\.(\d+)\.engram\.embed\.weight", name))
    )
    assert owners == layers
    for layer, row_count in zip(layers, rows):
        weight = by_name[f"layers.{layer}.engram.embed.weight"]
        scale = by_name[f"layers.{layer}.engram.embed.scale"]
        assert weight.storage_dtype == "F8_E4M3"
        assert weight.shape == (row_count, head_dim)
        assert scale.storage_dtype == "F8_E8M0"
        assert scale.shape == (row_count, head_dim // block)
        assert scale.scale_for == weight.name
        # The lookup projection: (max_ngram - 1) * n_heads rows in, one key per
        # hyper-connection copy plus one shared value out.
        columns = (text["engram_max_ngram_size"] - 1) * text["engram_n_heads"]
        projection = by_name[f"layers.{layer}.engram.wkv.weight"]
        assert projection.shape == (
            text["hidden_size"] * (text["hc_mult"] + 1),
            columns * head_dim,
        )
        for branch in ("q", "k"):
            gate = by_name[f"layers.{layer}.engram.{branch}_weight"]
            assert gate.shape == (text["hc_mult"], text["hidden_size"])
    assert not [name for name in by_name if name.startswith("mtp.") and "engram" in name]


def test_engram_table_bytes_match_the_governed_inventory(
    by_name: dict[str, TensorSpec], inventory: dict
) -> None:
    packed = sum(
        spec.size_bytes for name, spec in by_name.items() if ".engram.embed." in name
    )
    assert packed == inventory["lookup_table_bytes"]["engram_table_packed"]


# -- vision, MoE and DSpark ----------------------------------------------


def test_vision_tower_is_sized_from_the_vision_section(
    by_name: dict[str, TensorSpec], official_config: dict
) -> None:
    vision = official_config["vision_config"]
    text = official_config["text_config"]
    vision_dim = vision["hidden_size"]
    blocks = sorted(
        int(match.group(1))
        for name in by_name
        if (match := re.fullmatch(r"vision\.blocks\.(\d+)\.norm1\.weight", name))
    )
    assert blocks == list(range(vision["num_hidden_layers"]))
    assert by_name["vision.patch_embed.proj.weight"].shape == (
        vision_dim,
        3 * vision["patch_size"] ** 2,
    )
    assert by_name["aligner.w1.weight"].shape == (
        text["hidden_size"],
        vision_dim * vision["downsample_ratio"] ** 2,
    )
    assert by_name["vision.blocks.0.mlp.w1.weight"].shape == (
        2 * vision["intermediate_size"],
        vision_dim,
    )
    assert by_name["vision.blocks.0.attn.wqkv.weight"].shape == (
        3 * vision_dim,
        vision_dim,
    )
    for delimiter in ("image_start", "image_end", "image_newline"):
        assert by_name[delimiter].shape == (text["hidden_size"],)
    assert all(spec.storage_dtype == "BF16" for name, spec in by_name.items() if
               name.startswith(("vision.", "aligner.")))


def test_every_block_carries_a_vision_language_router_bias(
    by_name: dict[str, TensorSpec], official_config: dict
) -> None:
    """``bias_vl`` exists because the release has a tower, and V4 has none."""

    text = official_config["text_config"]
    for prefix, experts in (
        ("layers", text["n_routed_experts"]),
        ("mtp", text["dspark_n_routed_experts"]),
    ):
        owners = [name for name in by_name if re.fullmatch(rf"{prefix}\.\d+\.ffn\.gate\.bias_vl", name)]
        assert len(owners) == (
            text["num_hidden_layers"] if prefix == "layers" else V41_FLASH.dspark_stage_count
        )
        for name in owners:
            assert by_name[name].shape == (experts,)
    # No V4.1 layer is hash-routed, so no token-to-expert table exists.
    assert not [name for name in by_name if name.endswith(".gate.tid2eid")]
    flash_config = {
        **dict(FLASH.config_scalars),
        "quantization_config": dict(FLASH.quantization_config),
        "rope_scaling": dict(FLASH.rope_scaling),
        "compress_ratios": FLASH.compress_ratios,
    }
    assert [
        spec.name for spec in v4_specs(flash_config, FLASH) if spec.name.endswith("tid2eid")
    ]


def test_dspark_stage_topology_matches_the_released_stage_roles(
    by_name: dict[str, TensorSpec], official_config: dict
) -> None:
    """Stage 0 owns the fold-in projection; the last stage owns the heads."""

    text = official_config["text_config"]
    stages = V41_FLASH.dspark_stage_count
    assert stages == text["num_nextn_predict_layers"] == 3
    final = stages - 1
    assert by_name["mtp.0.main_proj.weight"].shape == (
        text["hidden_size"],
        text["hidden_size"] * len(text["dspark_target_layer_ids"]),
    )
    assert "mtp.0.main_norm.weight" in by_name
    for stage in range(1, stages):
        assert f"mtp.{stage}.main_proj.weight" not in by_name
    for projection in ("embed", "head"):
        assert by_name[f"mtp.{final}.markov_head.{projection}.weight"].shape == (
            text["vocab_size"],
            text["dspark_markov_rank"],
        )
    assert by_name[f"mtp.{final}.confidence_head.proj.weight"].shape == (
        1,
        text["hidden_size"] + text["dspark_markov_rank"],
    )
    assert by_name[f"mtp.{final}.confidence_head.proj.weight"].storage_dtype == "BF16"
    for stage in range(stages - 1):
        assert f"mtp.{stage}.markov_head.embed.weight" not in by_name
        assert f"mtp.{stage}.confidence_head.proj.weight" not in by_name
    # V4.1 drops the hyper-connection head V4 carries globally and per stage.
    assert not [name for name in by_name if "hc_head" in name]


def test_fp8_scale_geometry_is_the_released_block_not_v4s(
    by_name: dict[str, TensorSpec], official_config: dict
) -> None:
    """One generator, two block sizes, both read out of the released config."""

    rows, columns = official_config["quantization_config"]["weight_block_size"]
    assert (rows, columns) == (32, 32)

    linears = 0
    tables = 0
    for spec in by_name.values():
        if spec.scale_for is None or spec.storage_dtype != "F8_E8M0":
            continue
        weight = by_name[spec.scale_for]
        if weight.storage_dtype != "F8_E4M3":
            continue  # MXFP4 scales are the format's own 32-element block
        if weight.semantic_role == "engram.table.weight":
            # A lookup table is blocked along its channels only: a row is fetched
            # and dequantized on its own, so rows can never share a scale.
            assert spec.shape == (
                weight.shape[0],
                math.ceil(weight.shape[1] / columns),
            ), spec.name
            tables += 1
            continue
        assert spec.shape == (
            math.ceil(weight.shape[0] / rows),
            math.ceil(weight.shape[1] / columns),
        ), spec.name
        linears += 1
    assert tables == len(V41_FLASH.scalar("engram_layer_ids")) == 2
    assert linears == 355
    assert by_name["layers.0.attn.wq_b.scale"].shape == (1024, 40)
    assert by_name["layers.0.attn.wq_b.weight"].shape == (32768, 1280)
    # The same generator on a V4 record produces the 128-blocked geometry.
    flash_config = {
        **dict(FLASH.config_scalars),
        "quantization_config": dict(FLASH.quantization_config),
        "rope_scaling": dict(FLASH.rope_scaling),
        "compress_ratios": FLASH.compress_ratios,
    }
    v4_by_name = {spec.name: spec for spec in v4_specs(flash_config, FLASH)}
    v4_weight = v4_by_name["layers.0.attn.wq_b.weight"]
    v4_scale = v4_by_name["layers.0.attn.wq_b.scale"]
    assert v4_scale.shape == (
        math.ceil(v4_weight.shape[0] / 128),
        math.ceil(v4_weight.shape[1] / 128),
    )


def test_every_scale_has_an_exact_owner(by_name: dict[str, TensorSpec]) -> None:
    for name, spec in by_name.items():
        if spec.storage_dtype != "F8_E8M0":
            continue
        assert spec.scale_for is not None, name
        assert spec.scale_for in by_name, name
        owner = by_name[spec.scale_for]
        assert owner.storage_dtype in {"F8_E4M3", "I8"}
        assert spec.layer == owner.layer and spec.expert == owner.expert
    for name, spec in by_name.items():
        if spec.storage_dtype == "I8":
            assert spec.logical_dtype == "MXFP4_E2M1_X2", name
            assert f"{name.removesuffix('.weight')}.scale" in by_name


def test_pattern_census_covers_the_whole_checkpoint(
    specs: tuple[TensorSpec, ...], header_tensors: dict[str, tuple[str, tuple[int, ...]]]
) -> None:
    """Every generated name shape is a released name shape, and vice versa."""

    generated = Counter(_pattern(spec.name) for spec in specs)
    released = Counter(_pattern(name) for name in header_tensors)
    assert generated == released
    assert sum(generated.values()) == TENSOR_COUNT


def test_scopes_partition_the_contract_for_the_placers_downstream(
    specs: tuple[TensorSpec, ...], official_config: dict
) -> None:
    """Every tensor lands in exactly one placement scope, and none is stray.

    The ROM and HBM backends place by ``scope``, so an unscoped or
    wrongly-scoped tensor becomes a placement bug much later.  V4.1 adds a
    fourth scope V4 never had -- ``vision`` -- and the language model must not
    leak into it.
    """

    text = official_config["text_config"]
    counts = Counter(spec.scope for spec in specs)
    assert set(counts) == {"global", "main", "dspark", "vision"}
    assert sum(counts.values()) == TENSOR_COUNT

    assert counts["global"] == 6
    assert sorted(spec.name for spec in specs if spec.scope == "global") == [
        "embed.weight",
        "head.weight",
        "image_end",
        "image_newline",
        "image_start",
        "norm.weight",
    ]
    for scope, prefix in (("main", "layers."), ("dspark", "mtp."), ("vision", None)):
        scoped = [spec for spec in specs if spec.scope == scope]
        if prefix is not None:
            assert all(spec.name.startswith(prefix) for spec in scoped), scope
            assert all(spec.layer is not None for spec in scoped), scope
        else:
            assert all(
                spec.name.startswith(("vision.", "aligner.")) for spec in scoped
            )
    main_layers = {spec.layer for spec in specs if spec.scope == "main"}
    assert main_layers == set(range(text["num_hidden_layers"]))
    assert {spec.layer for spec in specs if spec.scope == "dspark"} == set(
        range(V41_FLASH.dspark_stage_count)
    )
    vision_blocks = {
        spec.layer
        for spec in specs
        if spec.scope == "vision" and spec.layer is not None
    }
    assert vision_blocks == set(range(official_config["vision_config"]["num_hidden_layers"]))
    # Only routed experts carry an expert index, and each layer has the full set.
    experts = Counter(
        spec.layer for spec in specs if spec.scope == "main" and spec.expert is not None
    )
    assert set(experts.values()) == {text["n_routed_experts"] * 3 * 2}


# -- the generator refuses what it cannot derive --------------------------


def test_a_count_that_lands_elsewhere_is_refused(official_config: dict) -> None:
    import copy

    drifted = copy.deepcopy(official_config)
    drifted["text_config"]["n_routed_experts"] = 383
    # The config gate catches it first, which is the point: the record is the gate.
    with pytest.raises(DeepSeekV41AdapterError, match="n_routed_experts"):
        build_official_tensor_specs(drifted)


def test_a_release_whose_engram_lists_disagree_is_refused(
    official_config: dict,
) -> None:
    import dataclasses

    record = dataclasses.replace(
        V41_FLASH,
        config_scalars={
            **dict(V41_FLASH.config_scalars),
            "engram_num_embeddings": [384_006_168],
        },
    )
    drifted = {
        **official_config,
        "text_config": {
            **official_config["text_config"],
            "engram_num_embeddings": [384_006_168],
        },
    }
    with pytest.raises(DeepSeekV41AdapterError, match="row counts"):
        build_official_tensor_specs(drifted, record)


def test_a_kv_source_outside_the_index_sources_is_refused(
    official_config: dict,
) -> None:
    """The invariant that lets the split indexer be derived rather than listed."""

    import dataclasses

    scalars = {
        **dict(V41_FLASH.config_scalars),
        "kv_source_layer_ids": [2, 8, 14, 20, 30],
    }
    record = dataclasses.replace(V41_FLASH, config_scalars=scalars)
    drifted = {
        **official_config,
        "text_config": {
            **official_config["text_config"],
            "kv_source_layer_ids": [2, 8, 14, 20, 30],
        },
    }
    with pytest.raises(DeepSeekV41AdapterError, match="must also be an index source"):
        build_official_tensor_specs(drifted, record)


def test_the_v4_releases_still_derive_their_pinned_structures() -> None:
    """Rule 4: the shared generator moved, so V4's two contracts are re-derived.

    ``_TensorBuilder`` now takes the released FP8 block instead of assuming 128.
    Both V4 records publish ``[128, 128]``, so both structure digests must be
    the bytes that were committed before that change.
    """

    for release, count, payload in (
        (FLASH, 72_317, 166_878_536_440),
        (PRO, 149_782, 892_727_580_904),
    ):
        config = {
            **dict(release.config_scalars),
            "quantization_config": dict(release.quantization_config),
            "rope_scaling": dict(release.rope_scaling),
            "compress_ratios": release.compress_ratios,
        }
        specs = v4_specs(config, release)
        assert len(specs) == count == release.tensor_count
        assert sum(spec.size_bytes for spec in specs) == payload == release.payload_bytes
        assert tensor_structure_sha256(specs) == release.tensor_structure_sha256
    assert (
        FLASH.tensor_structure_sha256
        == "18285fe60ca3655be488bbabb88b59489b8ee03cff7fc4f4729424051ca83e0e"
    )
    assert (
        PRO.tensor_structure_sha256
        == "b776f80c8422880de39e49a0679d4d5b81d218bdd4074b66c691760b65cc0eeb"
    )


def test_the_pinned_lock_agrees_with_the_header_free_derivation() -> None:
    """The byte-level lock and the config-only derivation must describe one model.

    The lock is built by reading and hashing all 510,286,023,000 payload bytes,
    so it knows the checkpoint from its contents; ``build_official_tensor_specs``
    knows it only from ``config.json``.  Nothing forces the two to agree, which
    is what makes the agreement worth asserting: a derivation that invented a
    tensor, dropped one, or mis-shaped one would show up here even though both
    sides already reproduce the same totals.

    The lock is host state rather than a repository artifact -- it names a
    snapshot directory on one machine -- so this skips where the host has no lock
    and the record's pinned digests stand on their own.
    """

    assert V41_FLASH.lock_identity_established is True
    assert FLASH.lock_identity_established and PRO.lock_identity_established
    assert len(V41_FLASH.checkpoint_lock_id) == 64
    assert len(V41_FLASH.tensor_content_sha256) == 64
    # Each release's lock identity is its own.
    assert len(
        {
            release.checkpoint_lock_id
            for release in (FLASH, PRO, V41_FLASH)
        }
    ) == 3

    path = V41_FLASH.checkpoint_lock
    if not path.is_file():
        pytest.skip(f"no checkpoint lock on this host at {path}")
    lock = validate_checkpoint_lock(json.loads(path.read_text(encoding="utf-8")))
    assert lock["lock_id"] == V41_FLASH.checkpoint_lock_id
    assert lock["checkpoint"]["tensor_content_sha256"] == (
        V41_FLASH.tensor_content_sha256
    )
    assert lock["checkpoint"]["tensor_count"] == TENSOR_COUNT
    assert lock["checkpoint"]["payload_bytes"] == PAYLOAD_BYTES
    assert lock["checkpoint"]["shard_count"] == V41_FLASH.shard_count
    # The lock embeds the committed source contract, so the two cannot drift.
    assert canonical_json_bytes(lock["source"]) == canonical_json_bytes(
        load_checkpoint_source(V41_FLASH.checkpoint_source_path)
    )

    specs = build_official_tensor_specs(load_official_config())
    derived = {spec.name: (spec.storage_dtype, spec.shape) for spec in specs}
    locked = {
        tensor["name"]: (tensor["dtype"], tuple(tensor["shape"]))
        for shard in lock["shards"]
        for tensor in shard["tensors"]
    }
    assert len(locked) == TENSOR_COUNT
    assert sorted(locked) == sorted(derived)
    assert [name for name in sorted(derived) if derived[name] != locked[name]] == []
    assert sum(
        tensor["size_bytes"] for shard in lock["shards"] for tensor in shard["tensors"]
    ) == PAYLOAD_BYTES
