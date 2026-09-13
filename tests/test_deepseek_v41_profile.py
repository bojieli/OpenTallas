"""DeepSeek-V4.1-Flash: the candidate profile and what it must reproduce.

The profile is built from the official checkpoint's safetensors headers and
config at one pinned revision.  Nothing here executes the model; what these
tests pin is that the accounting reproduces the numbers DeepSeek publishes
(552B backbone, 196B Engram, 16B active per decode token, 8B per prefill
token, 890 bytes of global KV per token) and that the CSA2 sharing semantics
added for it -- a layer that owns no cache, a layer that scans nothing, a
scan bounded by a candidate pool, a window at a different precision -- do
exactly what the pinned ``inference/model.py`` does, and nothing to any
profile that predates them.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from opentallas.analytical import AnalyticalSimulator
from opentallas.config import load_architecture_envelopes
from opentallas.deployment import A100_BF16_EXPANDED, deployment_model
from opentallas.operations import (
    BF16_X_BF16,
    FP4_X_FP4,
    FP8_X_FP8,
    MXFP4_X_FP8,
    operation_inventory,
)
from opentallas.schema import (
    AttentionGroup,
    HardwareProfile,
    ModelProfile,
    SimulationRequest,
    ValidationError,
)
from opentallas.workload import (
    hbm_resident_regions,
    linear_partition,
    hbm_resident_weight_bytes,
    kv_traffic,
    per_layer_hbm_resident_bytes,
    per_layer_hbm_resident_read_bytes,
    per_layer_kv_read_write,
    weight_traffic,
)


ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "configs" / "models" / "candidates"


def model(slug: str) -> ModelProfile:
    return ModelProfile.load(CANDIDATES / f"{slug}.json")


@pytest.fixture(scope="module")
def flash() -> ModelProfile:
    return model("deepseek-v4.1-flash")


@pytest.fixture(scope="module")
def engram_host() -> ModelProfile:
    return model("deepseek-v4.1-flash-engram_host")


@pytest.fixture(scope="module")
def engram_hbm() -> ModelProfile:
    return model("deepseek-v4.1-flash-engram_hbm")


@pytest.fixture(scope="module")
def central_wafer_pair():
    """The central N4-class wafer envelope and its B300 comparator.

    The placement question is a capacity question, so it has to be asked of the
    envelope whose capacities the plan quotes rather than of the legacy midpoint.
    """

    gpus, wafers, _ = load_architecture_envelopes(
        ROOT / "configs" / "hardware" / "leading_node_market.json"
    )
    wafer = next(arch for arch in wafers if arch.name.endswith("central"))
    gpu = max(gpus, key=lambda arch: arch.device_count)
    return gpu, wafer, AnalyticalSimulator(HardwareProfile(gpu=gpu, rom=wafer))


# --- what the checkpoint says --------------------------------------------


def test_profile_is_pinned_to_the_official_release(flash: ModelProfile) -> None:
    assert flash.source_repo == "deepseek-ai/DeepSeek-V4.1-Flash"
    assert flash.source_revision == "dba1be0a40aa45a94ad051997016db3960a90277"
    assert flash.metadata["adapter"] == "deepseek_v41"
    assert flash.num_layers == 40
    assert flash.num_experts == 384
    assert flash.experts_per_token == 6
    assert flash.hidden_size == 5120
    assert flash.max_context_tokens == 1_048_576
    assert flash.checkpoint_bytes == 510_286_023_000


def test_parameter_counts_reproduce_the_published_figures(flash: ModelProfile) -> None:
    counts = flash.metadata["parameter_counts"]
    backbone = (
        counts["decode_dense"]
        + counts["decode_routed"]
        + counts["resident_only"]
        - counts["engram_table"]
    )
    # 552B backbone and 196B Engram, as the model card states; the input
    # embedding and vision encoder are part of the backbone count.
    assert backbone == pytest.approx(552e9, rel=0.01)
    assert counts["engram_table"] == pytest.approx(196e9, rel=0.01)
    # 16B activated per decode token: every dense decode parameter plus 6 of
    # 384 routed experts on every layer.
    active = counts["decode_dense"] + counts["decode_routed"] * 6 / 384
    assert active == pytest.approx(16e9, rel=0.01)
    # DSpark draft blocks are separate and only read under speculation.
    assert counts["draft_dense"] + counts["draft_routed"] == pytest.approx(14.2e9, rel=0.01)


def test_decode_streams_forty_layers_and_the_untied_head(flash: ModelProfile) -> None:
    assert len(flash.layer_dense_weight_bytes) == 40
    assert len(flash.layer_routed_weight_bytes) == 40
    assert len(set(flash.layer_routed_weight_bytes)) == 1  # 384 identical experts
    assert flash.layer_routed_weight_bytes[0] == 384 * 3 * (5_898_240 + 368_640)
    # The BF16 head [129280, 5120] is streamed and unlayered.
    unlayered = flash.dense_weight_bytes - sum(flash.layer_dense_weight_bytes)
    assert unlayered == pytest.approx(129_280 * 5120 * 2 + 5120 * 2, abs=1)
    traffic = weight_traffic(flash, 1)
    assert traffic.routed_bytes == pytest.approx(flash.routed_weight_bytes * 6 / 384)
    assert traffic.total_bytes == pytest.approx(13.035e9, rel=0.001)


def test_engram_tables_are_resident_and_read_by_row(flash: ModelProfile) -> None:
    engram = flash.metadata["engram"]
    assert engram["layer_ids"] == [1, 14]
    assert engram["rows_read_per_token_per_module"] == 24  # 3 n-gram orders x 8 heads
    assert engram["row_bytes_packed"] == 256 + 8  # FP8 row plus one E8M0 per 32
    assert engram["lookup_bytes_per_token"] == 2 * 24 * 264
    assert flash.resident_only_weight_bytes > 202e9


# --- the KV cache -----------------------------------------------------------


def test_global_kv_is_890_bytes_per_token(flash: ModelProfile) -> None:
    """The model card's figure, from FP4 entries and cross-layer sharing."""

    assert flash.metadata["global_kv_bytes_per_token"] == 890.0
    labels = {group.label: group for group in flash.attention_groups}
    assert {label: group.count for label, group in labels.items()} == {
        "swa": 2,
        "csa2-2-full": 3,
        "csa2-2-reuse": 15,
        "csa2-1-full": 1,
        "csa2-1-reindex": 4,
        "csa2-1-reuse": 15,
    }
    for label in ("csa2-2-full", "csa2-1-full"):
        assert labels[label].kv_owner and labels[label].scans_index
        assert labels[label].entry_bytes == 512 / 2 + 512 / 16  # E2M1 + E4M3 per 16
        assert labels[label].index_entry_bytes == 128 / 2 + 128 / 32  # E2M1 + E8M0 per 32
        assert labels[label].window_entry_bytes == 512 + 512 / 32  # E4M3 + E8M0 per 32
    for label in ("csa2-2-reuse", "csa2-1-reuse"):
        assert not labels[label].kv_owner and not labels[label].scans_index
    reindex = labels["csa2-1-reindex"]
    assert not reindex.kv_owner and reindex.scans_index
    assert reindex.index_scan_entries_cap == 2048 * 8


def test_kv_storage_is_shared_not_per_layer(flash: ModelProfile) -> None:
    context = 200_000
    traffic = kv_traffic(flash, context)
    swa_per_layer = 128 * 528.0
    global_bytes = 890.0 * context
    assert traffic.storage_bytes_per_user == pytest.approx(
        40 * swa_per_layer + global_bytes, rel=1e-6
    )
    by_label = {item["label"]: item for item in traffic.breakdown}
    assert by_label["csa2-2-reuse"]["compressed_entries_stored_per_layer"] == 0
    assert by_label["csa2-1-reuse"]["index_entries_scanned_per_layer"] == 0
    assert by_label["csa2-1-reindex"]["index_entries_scanned_per_layer"] == 16_384
    assert by_label["csa2-1-full"]["index_entries_scanned_per_layer"] == context
    assert by_label["csa2-2-full"]["index_entries_scanned_per_layer"] == context / 2


def test_kv_read_grows_only_through_the_four_full_scans(flash: ModelProfile) -> None:
    low = kv_traffic(flash, 200_000)
    high = kv_traffic(flash, 1_000_000)
    scan_entries_per_token = 3 / 2 + 1  # three ratio-2 owners plus one ratio-1
    expected_growth = (1_000_000 - 200_000) * scan_entries_per_token * 68.0
    assert high.read_bytes - low.read_bytes == pytest.approx(expected_growth)
    # The write stream is context-independent: 40 window entries plus the
    # amortised owned entries.
    assert high.write_bytes == low.write_bytes


# --- the operator inventory -------------------------------------------------


def test_operator_inventory_charges_every_layer_on_decode(flash: ModelProfile) -> None:
    inventory = operation_inventory(flash, 200_000)
    named = inventory.named_operations()
    assert inventory.method == "deepseek_v41_official_operator_inventory_v1"
    assert len(inventory.per_layer_operations_by_format) == 40
    assert named["routed_expert_swiglu"] == pytest.approx(40 * 6 * 5120 * 2304 * 6)
    assert named["shared_expert_swiglu"] == pytest.approx(40 * 6 * 5120 * 2304)
    assert named["final_vocabulary_head"] == 2 * 5120 * 129_280
    assert named["engram_kv_projection"] == pytest.approx(2 * 2 * 6144 * 25_600)
    assert inventory.operations_for(MXFP4_X_FP8) > inventory.operations_for(FP8_X_FP8) > 0
    assert inventory.operations_for(FP4_X_FP4) > 0
    assert inventory.operations_for(BF16_X_BF16) > 0


def test_index_scan_is_bounded_on_reindex_layers(flash: ModelProfile) -> None:
    context = 200_000
    inventory = operation_inventory(flash, context)
    scan = [
        component
        for component in inventory.components
        if component.name == "indexer_qk_scan"
    ]
    assert [component.layer_index for component in scan] == [2, 8, 14, 20, 24, 28, 32, 36]
    per_entry = 2 * 32 * 128
    by_layer = {component.layer_index: component.operations for component in scan}
    for layer in (2, 8, 14):
        assert by_layer[layer] == pytest.approx(per_entry * ((context + 1) // 2))
    assert by_layer[20] == pytest.approx(per_entry * (context + 1))
    for layer in (24, 28, 32, 36):
        assert by_layer[layer] == pytest.approx(per_entry * 16_384)


def test_decode_work_is_nearly_flat_in_context(flash: ModelProfile) -> None:
    """Report Figure 2: 4K to 1M raises precision-weighted decode FLOPs ~1/4."""

    weights = {
        BF16_X_BF16: 1.0,
        "fp32_x_fp32": 1.0,
        FP8_X_FP8: 0.5,
        MXFP4_X_FP8: 0.5,
        FP4_X_FP4: 0.25,
    }

    def weighted(context: int) -> float:
        inventory = operation_inventory(flash, context)
        return sum(
            weights[fmt] * ops for fmt, ops in inventory.operations_by_format.items()
        )

    growth = weighted(1_000_000) / weighted(4_096)
    assert 1.2 < growth < 1.35
    v4 = ModelProfile.load(ROOT / "configs" / "models" / "deepseek-v4-flash-0731.json")
    assert (
        operation_inventory(v4, 1_000_000).total_tensor_operations
        > 2 * operation_inventory(flash, 1_000_000).total_tensor_operations
    )


# --- the Engram placement variant -------------------------------------------


def test_engram_host_variant_moves_only_the_tables(
    flash: ModelProfile, engram_host: ModelProfile
) -> None:
    tables = 202_758_032_400
    assert engram_host.name == "DeepSeek-V4.1-Flash-engram-host"
    assert flash.checkpoint_bytes - engram_host.checkpoint_bytes == tables
    assert flash.resident_only_weight_bytes - engram_host.resident_only_weight_bytes == tables
    assert engram_host.metadata["host_resident_weight_bytes"] == tables
    assert engram_host.dense_weight_bytes == flash.dense_weight_bytes
    assert engram_host.routed_weight_bytes == flash.routed_weight_bytes
    assert engram_host.attention_groups == flash.attention_groups
    assert kv_traffic(engram_host, 200_000) == kv_traffic(flash, 200_000)
    assert (
        operation_inventory(engram_host, 200_000).operations_by_format
        == operation_inventory(flash, 200_000).operations_by_format
    )
    assert engram_host.metadata["checkpoint_inventory"] == flash.metadata["checkpoint_inventory"]


def test_a100_expansion_covers_the_engram_tables(
    flash: ModelProfile, engram_host: ModelProfile
) -> None:
    expanded = deployment_model(flash, A100_BF16_EXPANDED)
    expanded_host = deployment_model(engram_host, A100_BF16_EXPANDED)
    assert expanded.checkpoint_bytes > 1.4e12
    # FP8 rows expand two-fold; the E8M0 scales are absorbed.  The two tables
    # have 384,006,168 and 384,016,682 rows of 256 FP8 values.
    assert expanded.checkpoint_bytes - expanded_host.checkpoint_bytes == 2 * (
        (384_006_168 + 384_016_682) * 256
    )
    window = next(group for group in expanded.attention_groups if group.kind == "window")
    assert window.entry_bytes == 2 * 512
    shared = next(group for group in expanded.attention_groups if group.label == "csa2-1-reuse")
    assert shared.entry_bytes == 2 * 512 and shared.window_entry_bytes == 0.0
    assert not shared.kv_owner


# --- the third Engram placement: resident in the KV store --------------------


def test_engram_hbm_is_the_host_variant_with_the_tables_charged_somewhere(
    flash: ModelProfile, engram_host: ModelProfile, engram_hbm: ModelProfile
) -> None:
    """The third placement is the second one's sibling, differing only in the bill.

    Both take the tables off the weight store, so both present the same
    checkpoint to a mask ROM.  Host memory then charges nothing to either side of
    a comparison; wafer-edge HBM charges its capacity to the stage that owns the
    region and its rows to that stage's read bandwidth.
    """

    tables = flash.metadata["parameter_counts"]["engram_table"] // 256 * 264
    assert engram_hbm.name == "DeepSeek-V4.1-Flash-engram-hbm"
    assert engram_hbm.checkpoint_bytes == engram_host.checkpoint_bytes
    assert engram_hbm.resident_only_weight_bytes == engram_host.resident_only_weight_bytes
    assert flash.checkpoint_bytes - engram_hbm.checkpoint_bytes == tables
    assert engram_hbm.dense_weight_bytes == flash.dense_weight_bytes
    assert engram_hbm.routed_weight_bytes == flash.routed_weight_bytes
    assert engram_hbm.attention_groups == flash.attention_groups
    assert engram_hbm.metadata["checkpoint_inventory"] == flash.metadata["checkpoint_inventory"]
    # Where the bill lands is the whole difference between the three.
    assert engram_hbm.metadata["host_resident_weight_bytes"] == 0
    assert hbm_resident_weight_bytes(engram_hbm) == tables
    assert hbm_resident_weight_bytes(engram_host) == 0.0
    assert hbm_resident_weight_bytes(flash) == 0.0
    assert hbm_resident_regions(flash) == ()


def test_engram_hbm_regions_are_derived_from_the_engram_configuration(
    engram_hbm: ModelProfile,
) -> None:
    """Nothing about the region is written down: rows x row bytes, per module."""

    engram = engram_hbm.metadata["engram"]
    regions = hbm_resident_regions(engram_hbm)
    assert [int(region["layer_id"]) for region in regions] == engram["layer_ids"]
    for region, rows in zip(regions, engram["num_embeddings"]):
        assert region["bytes"] == rows * engram["row_bytes_packed"]
        assert region["read_bytes_per_token"] == (
            engram["rows_read_per_token_per_module"] * engram["row_bytes_packed"]
        )
    per_layer = per_layer_hbm_resident_bytes(engram_hbm)
    assert len(per_layer) == engram_hbm.num_layers
    assert [index for index, value in enumerate(per_layer) if value] == engram["layer_ids"]
    assert sum(per_layer) == hbm_resident_weight_bytes(engram_hbm)


def test_engram_hbm_lookup_rows_are_kv_read_bytes_on_the_owning_layers(
    engram_host: ModelProfile, engram_hbm: ModelProfile
) -> None:
    """The identity the placement exists to price: the rows come out of the KV store.

    Reads grow by exactly the lookup, writes and per-user storage do not move at
    all -- the tables are written once at load and are not per-user state -- and
    the growth is attributed to the two layers that own the modules, which is
    what puts it on one pipeline stage rather than smeared over both.
    """

    lookup = engram_hbm.metadata["engram"]["lookup_bytes_per_token"]
    for context in (8_192, 200_000, 1_000_000):
        host = kv_traffic(engram_host, context)
        hbm = kv_traffic(engram_hbm, context)
        assert hbm.read_bytes - host.read_bytes == pytest.approx(lookup)
        assert hbm.write_bytes == host.write_bytes
        assert hbm.storage_bytes_per_user == host.storage_bytes_per_user

        host_layers = per_layer_kv_read_write(engram_host, context)
        hbm_layers = per_layer_kv_read_write(engram_hbm, context)
        resident_read = per_layer_hbm_resident_read_bytes(engram_hbm)
        assert sum(resident_read) == pytest.approx(lookup)
        for index, ((host_read, host_write), (hbm_read, hbm_write)) in enumerate(
            zip(host_layers, hbm_layers)
        ):
            assert hbm_read - host_read == pytest.approx(resident_read[index])
            assert hbm_write == host_write


def test_engram_hbm_keeps_the_two_wafer_partition_and_pays_on_the_owning_stage(
    flash: ModelProfile,
    engram_host: ModelProfile,
    engram_hbm: ModelProfile,
    central_wafer_pair,
) -> None:
    """Two wafers, not three, and the capacity comes off exactly one of them.

    The released placement holds the tables in the weight store, which is what
    makes it a three-wafer machine on the central envelope.  Both variants that
    move the tables out fit in two.  Only the HBM placement then loses KV
    capacity, and it loses it on the stage whose layer range contains layers 1
    and 14 -- the encoder wafer -- which is a consequence of the same minimax
    partition that places the weights, not a choice made here.
    """

    _, wafer, sim = central_wafer_pair
    request = SimulationRequest(context_tokens=200_000, batch_size=1)
    resident = sim.simulate(flash, wafer, request)
    host = sim.simulate(engram_host, wafer, request)
    hbm = sim.simulate(engram_hbm, wafer, request)

    assert resident.stages == 3
    assert host.stages == 2 and hbm.stages == 2
    assert hbm.metrics["C9_layer_storage_bytes_by_stage"] == (
        host.metrics["C9_layer_storage_bytes_by_stage"]
    )

    by_stage = ast.literal_eval(hbm.metrics["C7_C8_kv_store_resident_bytes_by_stage"])
    assert len(by_stage) == hbm.stages
    assert sum(by_stage) == hbm_resident_weight_bytes(engram_hbm)
    # The stage that pays is the one the weight partition put layers 1 and 14 on,
    # recomputed here by the same minimax rule rather than asserted as stage 0.
    partitions = linear_partition(
        tuple(
            dense + routed
            for dense, routed in zip(
                engram_hbm.layer_dense_weight_bytes, engram_hbm.layer_routed_weight_bytes
            )
        ),
        hbm.stages,
    )
    engram_layers = engram_hbm.metadata["engram"]["layer_ids"]
    owning = {
        stage
        for stage, (start, end) in enumerate(partitions)
        if any(start <= layer < end for layer in engram_layers)
    }
    assert {stage for stage, value in enumerate(by_stage) if value} == owning
    # The tables are 202.8 GB of a 1,296 GB usable store, so the stage that holds
    # them serves proportionally fewer sessions and the other one is untouched.
    assert hbm.metrics["C7_C8_max_batch_per_stage"] < host.metrics["C7_C8_max_batch_per_stage"]
    assert "C7_C8_kv_store_resident_weight_bytes" not in host.metrics
    assert "C7_C8_kv_store_resident_weight_bytes" not in resident.metrics


def test_engram_hbm_becomes_infeasible_when_the_store_cannot_hold_the_tables(
    engram_hbm: ModelProfile, central_wafer_pair
) -> None:
    """A KV store smaller than the resident region is refused, by name."""

    _, wafer, sim = central_wafer_pair
    tables = hbm_resident_weight_bytes(engram_hbm)
    starved = replace(wafer, kv_capacity_bytes_per_device=tables / 2)
    point = sim.simulate(
        engram_hbm, starved, SimulationRequest(context_tokens=200_000, batch_size=1)
    )
    assert not point.feasible
    assert any("KV-store-resident weights" in reason for reason in point.infeasible_reasons)


def test_engram_hbm_expansion_charges_expanded_tables(
    flash: ModelProfile, engram_hbm: ModelProfile
) -> None:
    """Under the A100 policy the resident region is BF16, like everything else."""

    expanded = deployment_model(engram_hbm, A100_BF16_EXPANDED)
    rows = sum(engram_hbm.metadata["engram"]["num_embeddings"])
    head_dim = engram_hbm.metadata["engram"]["head_dim"]
    assert hbm_resident_weight_bytes(expanded) == rows * 2 * head_dim
    assert [int(region["layer_id"]) for region in hbm_resident_regions(expanded)] == (
        engram_hbm.metadata["engram"]["layer_ids"]
    )
    assert deployment_model(flash, A100_BF16_EXPANDED).checkpoint_bytes - (
        expanded.checkpoint_bytes
    ) == rows * 2 * head_dim


def test_expanded_deployment_without_an_expanded_region_is_refused(
    engram_hbm: ModelProfile,
) -> None:
    """A profile that declares a resident region must declare its expansion."""

    metadata = dict(engram_hbm.metadata)
    storage = {
        key: value
        for key, value in metadata["deployment_storage"]["a100_bf16_expanded"].items()
        if key not in ("hbm_resident_bytes", "hbm_resident_regions")
    }
    metadata["deployment_storage"] = {"a100_bf16_expanded": storage}
    broken = replace(engram_hbm, metadata=metadata)
    with pytest.raises(ValidationError, match="hbm_resident_bytes"):
        deployment_model(broken, A100_BF16_EXPANDED)


def test_resident_regions_must_name_a_layer_the_model_has(
    engram_hbm: ModelProfile,
) -> None:
    metadata = dict(engram_hbm.metadata)
    metadata["hbm_resident_regions"] = [
        {
            "layer_id": engram_hbm.num_layers,
            "bytes": 1.0,
            "read_bytes_per_token": 1.0,
        }
    ]
    metadata["hbm_resident_weight_bytes"] = 1.0
    broken = replace(engram_hbm, metadata=metadata)
    with pytest.raises(ValueError, match="outside the 40 layers"):
        hbm_resident_regions(broken)


def test_declared_total_must_match_the_regions(engram_hbm: ModelProfile) -> None:
    metadata = dict(engram_hbm.metadata)
    metadata["hbm_resident_weight_bytes"] = (
        float(metadata["hbm_resident_weight_bytes"]) + 1024.0
    )
    broken = replace(engram_hbm, metadata=metadata)
    with pytest.raises(ValueError, match="hbm_resident_regions sum to"):
        hbm_resident_weight_bytes(broken)


# --- the schema additions ---------------------------------------------------


def test_sharing_fields_default_to_the_pre_v41_behaviour() -> None:
    group = AttentionGroup(
        kind="compressed_sparse",
        count=1,
        entry_bytes=1024,
        window_tokens=128,
        compression_ratio=4,
        top_k=512,
        index_entry_bytes=256,
    )
    assert group.kv_owner and group.scans_index
    assert group.index_scan_entries_cap == 0
    assert group.effective_window_entry_bytes == 1024
    for slug in ("deepseek-v4-flash-0731", "deepseek-v4-pro-0813", "kimi-k3", "qwen3-8b"):
        profile = ModelProfile.load(ROOT / "configs" / "models" / f"{slug}.json")
        serialised = profile.to_dict()["attention_groups"]
        assert all(
            key not in item
            for item in serialised
            for key in ("kv_owner", "scans_index", "index_scan_entries_cap", "window_entry_bytes")
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"kind": "window", "kv_owner": False},
        {"kind": "dense_mla", "scans_index": False},
        {"kind": "compressed_dense", "compression_ratio": 4, "index_scan_entries_cap": 16},
        {"kind": "compressed_dense", "compression_ratio": 1},
        {"kind": "window", "window_entry_bytes": -1.0},
        {"kind": "dense_kv", "window_tokens": 0, "window_entry_bytes": 100.0},
    ],
)
def test_sharing_fields_are_refused_where_they_mean_nothing(overrides: dict) -> None:
    base = dict(kind="window", count=1, entry_bytes=1024.0, window_tokens=128)
    base.update(overrides)
    with pytest.raises(ValidationError):
        AttentionGroup(**base)


def test_ratio_one_is_a_legal_sparse_cache() -> None:
    group = AttentionGroup(
        kind="compressed_sparse",
        count=1,
        entry_bytes=288,
        window_tokens=128,
        window_entry_bytes=528,
        compression_ratio=1,
        top_k=512,
        index_entry_bytes=68,
    )
    traffic = kv_traffic(
        ModelProfile(
            name="ratio-one",
            source_repo="test",
            source_revision="0" * 40,
            total_parameters=1e9,
            active_parameters=1e9,
            checkpoint_bytes=1e9,
            dense_weight_bytes=1e9,
            routed_weight_bytes=0,
            dense_compute_format="bf16_x_bf16",
            routed_compute_format=None,
            num_layers=1,
            num_experts=1,
            experts_per_token=1,
            hidden_size=16,
            max_context_tokens=10_000,
            attention_groups=(group,),
        ),
        1_000,
    )
    assert traffic.storage_bytes_per_user == 128 * 528 + 1_000 * (288 + 68)
    assert traffic.read_bytes == 128 * 528 + 512 * 288 + 1_000 * 68
