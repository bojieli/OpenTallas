"""The DeepSeek-V4 front end is one code path over two pinned releases.

These tests hold the two ends of that claim apart.  One end is that naming
DeepSeek-V4-Pro-0813 really does produce the Pro contract -- 61 layers, 384
experts, 149,782 tensors, 3,011 nodes -- from the same functions.  The other is
that nothing about DeepSeek-V4-Flash-0731 moved while that was arranged: the
Flash profile still carries the exact widths the module constants had, and the
Flash graph contract still hashes to the value it has always hashed to, which
``tests/compiler/test_deepseek_v4_graph.py`` pins independently.

Nothing here reads a checkpoint.  Both releases' configuration, tensor and node
contracts are derivable from committed files, which is why the Pro half can be
reviewed while its 892,727,580,904 payload bytes are still downloading.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from compiler.frontend.deepseek_v4 import (
    build_official_tensor_specs,
    load_official_config,
    tensor_structure_sha256,
)
from compiler.frontend.deepseek_v4_graph import build_official_graph_contract
from compiler.frontend.deepseek_v4_releases import (
    FLASH,
    PRO,
    RELEASES,
    DeepSeekV4ReleaseError,
    resolve_release,
)
from compiler.frontends.v3.deepseek_v4 import (
    FLASH_PROFILE,
    MODEL_PROFILES,
    PRO_PROFILE,
    DeepSeekV4KernelIRError,
    export_deepseek_v4_kernel_graph,
    lowering_plan,
    resolve_model_profile,
)

ROOT = Path(__file__).resolve().parents[2]

#: The keys that differ between the two releases.  Everything else in the
#: pinned configuration -- head_dim, the indexer widths, the sliding window,
#: the vocabulary, the quantization block, the YaRN interpolation -- is equal,
#: and that is why one front end covers both.
MOVED_CONFIG_KEYS = frozenset(
    {
        "compress_ratios",
        "dspark_markov_rank",
        "dspark_target_layer_ids",
        "hidden_size",
        "index_topk",
        "moe_intermediate_size",
        "n_routed_experts",
        "num_attention_heads",
        "num_hidden_layers",
        "o_groups",
        "q_lora_rank",
        "routed_scaling_factor",
    }
)


@pytest.fixture(scope="module")
def pro_config() -> dict:
    return load_official_config(release=PRO)


@pytest.fixture(scope="module")
def pro_contract() -> dict:
    return build_official_graph_contract(PRO)


@pytest.mark.parametrize("release", sorted(RELEASES.values(), key=lambda r: r.model_id))
def test_the_record_is_the_committed_config_byte_for_byte(release) -> None:
    """Every registered record equals the config bytes committed beside it.

    Each pinned structure is resolved through the record's own
    ``config_layout`` rather than assumed to sit at the root: the two V4
    releases publish one flat object and V4.1 nests its language model under
    ``text_config``, and a test that assumed either shape would have to be
    edited for the next release rather than reading where it says it is.
    """

    payload = release.config_path.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == release.config_sha256
    assert len(payload) == release.config_bytes
    config = json.loads(payload)

    architecture = release.config_section(config, "architecture")
    for key, expected in release.config_scalars.items():
        assert key in architecture, key
        assert architecture[key] == expected, key
        assert type(architecture[key]) is type(expected), key
    assert (
        release.config_section(config, "quantization_config")["quantization_config"]
        == release.quantization_config
    )
    assert (
        release.config_section(config, "rope_scaling")["rope_scaling"]
        == release.rope_scaling
    )
    assert (
        release.config_section(config, "compress_ratios")["compress_ratios"]
        == release.compress_ratios
    )
    assert len(release.main_compress_ratios) == architecture["num_hidden_layers"]

    # Whatever else the record pins outside the architecture section -- a
    # multi-modal release's root identity and its vision tower -- is checked the
    # same way, and a record that pins nothing else checks nothing else.
    for path, pinned in release.config_sections.items():
        section = config
        for key in filter(None, path.split(".")):
            assert key in section, f"{path}: {key}"
            section = section[key]
        for key, expected in pinned.items():
            assert section[key] == expected, f"{path}.{key}"


def test_the_two_releases_differ_in_exactly_twelve_config_keys() -> None:
    assert set(FLASH.config_scalars) == set(PRO.config_scalars)
    moved = {
        key
        for key in FLASH.config_scalars
        if FLASH.config_scalars[key] != PRO.config_scalars[key]
    }
    assert moved | {"compress_ratios"} == MOVED_CONFIG_KEYS
    assert FLASH.compress_ratios != PRO.compress_ratios


def test_every_moved_key_is_confronted_with_the_released_config() -> None:
    """The pinned-assertion block must cover each key that moves.

    A width the export sizes by and does not check is a width that can drift
    against the config it claims to come from.  ``routed_scaling_factor`` is
    the one with no downstream witness at all: a route scale of 1.5 applied to
    a model whose released value is 2.5 produces finite numbers and no trap.
    """

    for profile in MODEL_PROFILES.values():
        pinned = {key for key, _ in profile.architecture_pins}
        assert MOVED_CONFIG_KEYS <= pinned
        for key, _ in profile.architecture_pins:
            assert key == "compress_ratios" or key in profile.release.config_scalars


def test_the_flash_profile_still_carries_the_released_flash_widths() -> None:
    """Written as literals: this is the half that must not have moved."""

    assert FLASH_PROFILE.model_id == "deepseek-v4-flash-0731"
    assert FLASH_PROFILE.numeric_profile == "deepseek_v4_flash_target_precision_v1"
    assert FLASH_PROFILE.generation_policy_id == "deepseek_v4_flash_greedy_argmax_v1"
    assert (FLASH_PROFILE.hidden, FLASH_PROFILE.heads) == (4096, 64)
    assert (FLASH_PROFILE.q_rank, FLASH_PROFILE.o_groups) == (1024, 8)
    assert (FLASH_PROFILE.index_topk, FLASH_PROFILE.routed_experts) == (512, 256)
    assert FLASH_PROFILE.moe_intermediate == 2048
    assert FLASH_PROFILE.route_scale == 1.5
    assert FLASH_PROFILE.markov_rank == 256
    assert FLASH_PROFILE.layers == 43
    assert FLASH_PROFILE.target_layers == (40, 41, 42)
    assert FLASH_PROFILE.head_dim == 512 and FLASH_PROFILE.rope_dim == 64
    assert FLASH_PROFILE.hc_mix == 24 and FLASH_PROFILE.hc_coefficients == 20
    assert FLASH.tensor_count == 72_317
    assert FLASH.payload_bytes == 166_878_536_440


def test_the_pro_profile_carries_the_released_pro_widths() -> None:
    assert PRO_PROFILE.model_id == "deepseek-v4-pro-0813"
    assert PRO_PROFILE.numeric_profile == "deepseek_v4_pro_target_precision_v1"
    assert PRO_PROFILE.generation_policy_id == "deepseek_v4_pro_greedy_argmax_v1"
    assert (PRO_PROFILE.hidden, PRO_PROFILE.heads) == (7168, 128)
    assert (PRO_PROFILE.q_rank, PRO_PROFILE.o_groups) == (1536, 16)
    assert (PRO_PROFILE.index_topk, PRO_PROFILE.routed_experts) == (1024, 384)
    assert PRO_PROFILE.moe_intermediate == 3072
    assert PRO_PROFILE.route_scale == 2.5
    assert PRO_PROFILE.markov_rank == 512
    assert PRO_PROFILE.layers == 61
    assert PRO_PROFILE.target_layers == (58, 59, 60)
    # The widths that do not move are what makes one front end enough.
    assert PRO_PROFILE.head_dim == FLASH_PROFILE.head_dim
    assert PRO_PROFILE.rope_dim == FLASH_PROFILE.rope_dim
    assert PRO_PROFILE.index_head_dim == FLASH_PROFILE.index_head_dim
    assert PRO_PROFILE.index_heads == FLASH_PROFILE.index_heads
    assert PRO_PROFILE.sliding_window == FLASH_PROFILE.sliding_window
    assert PRO_PROFILE.vocabulary == FLASH_PROFILE.vocabulary
    assert PRO_PROFILE.top_k == FLASH_PROFILE.top_k
    # The grouped output projection keeps its inner width: 64*512/8 = 128*512/16.
    assert (
        PRO_PROFILE.heads * PRO_PROFILE.head_dim // PRO_PROFILE.o_groups
        == FLASH_PROFILE.heads * FLASH_PROFILE.head_dim // FLASH_PROFILE.o_groups
        == 4096
    )


def test_pro_has_no_window_only_layer() -> None:
    """The largest non-numeric difference between the two releases.

    Flash's ratio table begins (0, 0); Pro's begins (128, 128).  Every
    ``if ratio:`` branch in the front end is therefore taken on all 61 Pro
    layers, and layers 0 and 1 gain a ratio-128 compressor.
    """

    flash = FLASH.main_compress_ratios
    pro = PRO.main_compress_ratios
    assert flash[:2] == (0, 0) and pro[:2] == (128, 128)
    assert (flash.count(0), flash.count(4), flash.count(128)) == (2, 21, 20)
    assert (pro.count(0), pro.count(4), pro.count(128)) == (0, 30, 31)
    # Both releases' DSpark stages stay window-only.
    assert FLASH.dspark_compress_ratios == PRO.dspark_compress_ratios == (0, 0, 0)


def test_the_output_join_tree_follows_the_group_count() -> None:
    """Amendment A17 joins four views at a time."""

    assert FLASH_PROFILE.output_join_levels == 3
    assert PRO_PROFILE.output_join_levels == 5
    flash_plan = lowering_plan(FLASH_PROFILE)["GROUPED_OUTPUT_PROJECT"]
    pro_plan = lowering_plan(PRO_PROFILE)["GROUPED_OUTPUT_PROJECT"]
    assert flash_plan.count("MATMUL") == 8 and flash_plan.count("CONCAT") == 3
    assert pro_plan.count("MATMUL") == 16 and pro_plan.count("CONCAT") == 5
    assert set(lowering_plan(PRO_PROFILE)) == set(lowering_plan(FLASH_PROFILE))


def test_an_unknown_model_is_refused_by_name() -> None:
    with pytest.raises(DeepSeekV4KernelIRError, match="deepseek-v4-pro-0813"):
        resolve_model_profile("deepseek-v4-ultra-0901")
    with pytest.raises(DeepSeekV4ReleaseError):
        resolve_release("deepseek-v4-ultra-0901")
    assert resolve_model_profile(PRO) is PRO_PROFILE
    assert resolve_model_profile(PRO_PROFILE) is PRO_PROFILE


def test_the_pro_tensor_contract_matches_the_governed_inventory(pro_config) -> None:
    specs = build_official_tensor_specs(pro_config, PRO)
    inventory = json.loads(
        (ROOT / "data/inventory/deepseek-v4-pro-0813.json").read_text()
    )
    assert len(specs) == inventory["tensor_count"] == 149_782
    assert sum(s.size_bytes for s in specs) == inventory["checkpoint_bytes"]
    assert inventory["checkpoint_bytes"] == PRO.payload_bytes
    assert tensor_structure_sha256(specs) == PRO.tensor_structure_sha256
    # Layers 0 and 1 own a compressor on Pro and none on Flash.
    compressor = {
        s.name for s in specs if s.semantic_role.startswith("attention.compressor")
    }
    assert any(name.startswith("layers.0.") for name in compressor)
    assert any(name.startswith("layers.1.") for name in compressor)


def test_the_pro_node_graph_builds_from_committed_files_alone(pro_contract) -> None:
    assert pro_contract["model_id"] == "deepseek-v4-pro-0813"
    assert pro_contract["coverage"]["node_count"] == 3_011
    assert pro_contract["tensor_assignment"]["assigned_tensor_count"] == 149_782
    assert len(pro_contract["operator_counts"]) == 46
    assert pro_contract["source"]["revision"] == PRO.revision
    assert pro_contract["source"]["tokenizer_sha256"] == FLASH.tokenizer_sha256
    issue = next(
        item
        for item in pro_contract["open_semantic_issues"]
        if item["id"] == "DSV4-SEM-005"
    )
    assert "3,011 nodes" in issue["required_resolution"]
    # No MP=4 canonical application exists for this release, so the covered
    # scope must not claim one and the unresolved list must say so.
    assert not any(
        "canonical application" in item
        for item in pro_contract["system_scope"]["covered"]
    )
    assert any(
        "canonical application" in item
        for item in pro_contract["system_scope"]["unresolved"]
    )


def test_pro_nodes_carry_the_pro_widths(pro_contract) -> None:
    nodes = {node["id"]: node for node in pro_contract["nodes"]}
    assert nodes["main.layer00.query_a"]["attributes"] == {
        "in_features": 7168,
        "out_features": 1536,
    }
    assert nodes["main.layer00.attn_norm"]["attributes"]["width"] == 7168
    assert nodes["main.layer00.query_norm"]["attributes"]["width"] == 1536
    assert nodes["main.layer00.output_a"]["attributes"] == {
        "groups": 16,
        "rank": 1024,
    }
    assert nodes["main.layer00.output_b"]["attributes"] == {
        "in_features": 16384,
        "out_features": 7168,
    }
    assert nodes["main.layer00.route_select"]["attributes"]["experts"] == 384
    assert nodes["main.layer00.route_weights"]["attributes"]["route_scale"] == 2.5
    assert nodes["main.layer00.routed_experts"]["attributes"]["intermediate_size"] == 3072
    assert nodes["dspark.main_project"]["attributes"]["source_layers"] == [58, 59, 60]
    assert nodes["dspark.markov_loop"]["attributes"]["markov_rank"] == 512
    assert nodes["dspark.confidence"]["attributes"]["input_width"] == 7680
    # Layer 0 is compressed on Pro, so it carries the compressor sub-block that
    # Flash's window-only layer 0 does not have.
    assert "main.layer00.compress_project" in nodes


def test_a_pro_kernel_ir_build_stops_and_names_the_artifacts_it_lacks() -> None:
    """It must stop for a missing artifact, not fail somewhere inside a build."""

    if PRO.checkpoint_lock.is_file() and PRO.lock_identity_established:
        pytest.skip("the DeepSeek-V4-Pro-0813 checkpoint lock is present")
    with pytest.raises(DeepSeekV4KernelIRError) as caught:
        export_deepseek_v4_kernel_graph(model="deepseek-v4-pro-0813")
    message = str(caught.value)
    assert "deepseek-v4-pro-0813" in message
    assert str(PRO.checkpoint_lock) in message
    assert "tools/build_checkpoint_lock.py" in message
    assert not PRO.lock_identity_established
