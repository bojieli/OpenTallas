"""The DeepSeek-V4.1-Flash front end, and the cross-check V4 never had.

Most of this file is the same contract the V4 front end holds: the neutral
registry, the shared lowering table, one frozen numeric contract per source
operator kind, and no identifier carrying a backend term.

The part that is new -- and the reason this package is worth landing before the
checkpoint lock exists -- is
:func:`test_the_census_matches_the_analytical_operator_inventory_per_layer` and
the tests around it.  DeepSeek-V4.1-Flash is described twice in this
repository, by two derivations that share no code:

* the **analytical** layer, ``src/opentallas/operations.py``'s
  ``_deepseek_v41_inventory``, reads the committed candidate profile and
  charges one decode token's tensor contractions layer by layer;
* the **executable** layer, ``compiler/frontends/v3/deepseek_v41.py``, reads the
  pinned release record and plans the neutral kernels layer by layer.

If those two disagree about *which layers* run a compressor, an indexer, a
candidate-pool selection or an Engram module, one of them is wrong about the
model, and every figure or schedule built on it is wrong with it.  Nothing in
the V4 program could catch that, because V4 had no second description to
confront.  These tests confront them term by term and layer by layer, and they
need no payload byte to do it.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping

import pytest

from compiler.frontend.deepseek_v4_releases import V41_FLASH
from compiler.ir.v3.kernel_ir import (
    DTYPES,
    FORBIDDEN_TERMS,
    OPERATION_KINDS,
)
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE
from compiler.ir.v3.numeric import CONTRACT_PATTERN, is_implementation_path
from compiler.frontends.v3.deepseek_v41 import (
    ARCHITECTURAL_MAX_CONTEXT,
    graph_census_v41,
    ATTENTION_MODES,
    CANDIDATE_PROFILE_PATH,
    CONTRACT_BASE_BY_SOURCE_KIND,
    DEFAULT_CONTEXT_TOKENS,
    FP4_INDEX_BLOCK,
    FP4_MAIN_BLOCK,
    LOWERING_PLAN,
    MAIN_LATENT_DTYPE,
    SPECULATIVE_SOURCE_KINDS,
    V41_FLASH_PROFILE,
    DeepSeekV41KernelIRError,
    attention_mode_plan,
    confront_layer_modes,
    confront_source_digests,
    contract_for,
    export_deepseek_v41_kernel_graph,
    layer_source_plan,
    missing_ir_artifacts,
    plan_defects,
    planned_census,
    released_architecture_config,
    resolve_model_profile,
    source_kind_plan,
    unlayered_source_plan,
    validate_architecture_pins,
)
from opentallas.operations import operation_inventory
from opentallas.schema import ModelProfile

ROOT = Path(__file__).resolve().parents[2]

#: The context the cross-check is taken at.  Any context past the candidate
#: pool exercises the Reindex cap; this is the ADR-003 acceptance length.
CROSS_CHECK_CONTEXT = 200_000


@pytest.fixture(scope="module")
def profile():
    return V41_FLASH_PROFILE


@pytest.fixture(scope="module")
def modes(profile):
    return profile.layer_modes()


@pytest.fixture(scope="module")
def census(profile):
    return planned_census(profile)


@pytest.fixture(scope="module")
def analytical() -> ModelProfile:
    return ModelProfile.load(CANDIDATE_PROFILE_PATH)


@pytest.fixture(scope="module")
def inventory(analytical):
    return operation_inventory(analytical, CROSS_CHECK_CONTEXT)


# ---------------------------------------------------------------------------
# The cross-check between the analytical and the executable layer
# ---------------------------------------------------------------------------
#: One analytical tensor-contraction term, and the source operator kind the
#: executable plan realises it with.  Every term the V4.1 inventory charges is
#: here: a term with no executable counterpart is a mechanism the IR cannot
#: express, and a source kind with no analytical counterpart is work the
#: analytical layer is not charging for.  Both are defects, and
#: ``test_every_analytical_term_and_every_operator_kind_is_accounted_for``
#: refuses either.
_TERM_TO_SOURCE_KIND: Mapping[str, str] = {
    "attention_core": "SPARSE_ATTENTION",
    "attention_wkv": "FP8_LINEAR",
    "attention_wo_a_grouped": "GROUPED_OUTPUT_PROJECT",
    "attention_wo_b": "GROUPED_OUTPUT_PROJECT",
    "attention_wq_a": "FP8_LINEAR",
    "attention_wq_b": "FP8_LINEAR",
    "engram_kv_projection": "ENGRAM_KV_PROJECT",
    "indexer_key_projection": "INDEX_KEY_PROJECT",
    "indexer_qk_scan": "INDEX_SCORE",
    "indexer_query_up_projection": "INDEX_QUERY_PROJECT",
    "indexer_weight_projection": "INDEX_WEIGHT_PROJECT",
    "main_compressor_projections": "COMPRESS_PROJECT",
    "mhc_pre_projections": "HC_PRE",
    "routed_expert_swiglu": "MXFP4_SWIGLU",
    "router_projection": "ROUTER_SCORE",
    "shared_expert_swiglu": "FP8_SWIGLU",
}

#: The same correspondence for the inventory's auxiliary counts, which are the
#: non-contraction mechanisms: the pooled compressor, the candidate-block
#: reduction, the Engram row reads and the selections.
_AUXILIARY_TO_SOURCE_KIND: Mapping[str, str] = {
    "attention_score_elements": "SPARSE_ATTENTION",
    "candidate_block_scores": "CANDIDATE_BLOCK_SELECT",
    "compressor_pool_elements": "COMPRESS_POOL",
    "engram_lookup_bytes": "ENGRAM_ROW_LOOKUP",
    "engram_lookup_rows": "ENGRAM_ROW_LOOKUP",
    "index_score_elements": "INDEX_SCORE",
    "topk_candidates": "INDEX_TOPK",
    "topk_selected": "INDEX_TOPK",
}

#: Analytical auxiliary counts that every layer accrues from several mechanisms
#: at once -- normalizations, transcendentals, the Sinkhorn matrix -- so their
#: layer set is "all of them" and confronting it with one source kind would say
#: nothing.  They are checked as covering every layer instead.
_UBIQUITOUS_AUXILIARY = frozenset(
    {
        "nonlinear_elements",
        "normalization_elements",
        "sinkhorn_matrix_elements_per_iteration",
    }
)

#: Source operator kinds the analytical inventory deliberately does not charge
#: for, with the reason.  A kind that is not here and not in the two
#: correspondence tables above is an accounting gap.
_UNCHARGED_SOURCE_KINDS: Mapping[str, str] = {
    # movement and views: no contraction, no transcendental
    "ATTENTION_KV_VIEW": "a concatenation of two KV sources",
    "CANDIDATE_MASK_READ": "a read of the pool the candidate source published",
    "COMPRESSED_KV_VALID_VIEW": "a read of the owner's cache",
    "COMPRESS_KV_WRITE": "a cache append",
    "COMPRESS_STATE_UPDATE": "the partial-group carry of a pooled compressor",
    "ENGRAM_NGRAM_HASH": "integer multiply-modulo, charged as lookup traffic",
    "ENGRAM_TOKEN_COMPRESS": "a table read of compressed token ids",
    "HC_EXPAND": "a broadcast of the embedding into hc_mult copies",
    "HC_FINAL_COLLAPSE": "a weighted reduction with no projection tensor",
    "HC_POST": "a weighted combination, charged inside mhc_pre_projections",
    "INDEX_KEY_WRITE": "a cache append",
    "KV_WINDOW_WRITE": "a ring-buffer write",
    "ROPE_APPLY": "a rotation, charged as normalization/elementwise work",
    "ROPE_INVERSE": "the same rotation conjugated",
    "SHARED_INDEX_REUSE": "a read of the selection an index source published",
    "SPARSE_ATTENTION": "charged as attention_core",
    "WINDOW_INDEX": "an index enumeration",
    # quantization round trips: elementwise, charged in the format of the GEMM
    "FP4_INDEX_QDQ": "an elementwise round trip",
    "FP4_MAIN_QDQ": "an elementwise round trip",
    "FP8_QDQ": "an elementwise round trip",
    # routing selection and normalization, charged as auxiliary counts
    "BIASED_TOPK_ROUTE": "expert selection, charged as nonlinear_elements",
    "EXPERT_DISPATCH": "a permutation",
    "EXPERT_REDUCE": "a scatter-add",
    "ROUTER_WEIGHT_NORMALIZE": "a normalization of six weights",
    "SQRT_SOFTPLUS": "the router transcendental, charged as nonlinear_elements",
    # the fused Engram gate's arithmetic is its normalizations and sigmoid
    "ENGRAM_GATE": "a normalized dot and sigmoid, charged as normalization",
    # normalization, charged as normalization_elements
    "RMS_NORM": "charged as normalization_elements",
    # the unlayered path
    "HEAD_RMS_NORM": "charged as normalization_elements",
    "LM_HEAD": "charged as final_vocabulary_head",
    "SAMPLE": "selection over the logits",
    "TOKEN_EMBED": "a table read",
    "INDEX_TOPK": "charged as topk_candidates and topk_selected",
    "CANDIDATE_BLOCK_SELECT": "charged as candidate_block_scores",
}


def _layers_by_term(inventory) -> dict[str, set[int | None]]:
    layers: dict[str, set[int | None]] = defaultdict(set)
    for component in inventory.components:
        layers[component.name].add(component.layer_index)
    return dict(layers)


def _layers_by_auxiliary(inventory) -> dict[str, set[int]]:
    layers: dict[str, set[int]] = defaultdict(set)
    for index, counts in enumerate(inventory.per_layer_auxiliary_counts):
        for name in counts:
            layers[name].add(index)
    return dict(layers)


def _layers_by_source_kind(profile) -> dict[str, set[int]]:
    layers: dict[str, set[int]] = defaultdict(set)
    for index, sources in enumerate(layer_source_plan(profile)):
        for source in sources:
            layers[source].add(index)
    return dict(layers)


def test_the_census_matches_the_analytical_operator_inventory_per_layer(
    profile, inventory
):
    """Every charged mechanism runs on exactly the layers the IR plans it on.

    This is the cross-check.  Both sides are derived -- the analytical layer
    from ``metadata.operator_config``, the executable layer from the release
    record's ``kv_source_layer_ids``, ``index_source_layer_ids``,
    ``candidate_source_layer_id`` and ``engram_layer_ids`` -- and neither reads
    the other, so an agreement on all twenty-four layer sets is evidence that
    the two descriptions are of the same model.
    """

    by_term = _layers_by_term(inventory)
    by_auxiliary = _layers_by_auxiliary(inventory)
    by_source = _layers_by_source_kind(profile)

    disagreements: list[str] = []
    for term, source_kind in _TERM_TO_SOURCE_KIND.items():
        assert term in by_term, f"the analytical inventory no longer charges {term}"
        analytical_layers = by_term[term]
        planned = by_source.get(source_kind, set())
        if analytical_layers != planned:
            disagreements.append(
                f"{term} is charged on {sorted(analytical_layers)} and "
                f"{source_kind} is planned on {sorted(planned)}"
            )
    for name, source_kind in _AUXILIARY_TO_SOURCE_KIND.items():
        assert name in by_auxiliary, f"the inventory no longer counts {name}"
        analytical_layers = by_auxiliary[name]
        planned = by_source.get(source_kind, set())
        if analytical_layers != planned:
            disagreements.append(
                f"{name} is counted on {sorted(analytical_layers)} and "
                f"{source_kind} is planned on {sorted(planned)}"
            )
    assert disagreements == []


def test_every_analytical_term_and_every_operator_kind_is_accounted_for(
    profile, inventory
):
    """Neither description carries a mechanism the other has never heard of."""

    by_term = _layers_by_term(inventory)
    by_auxiliary = _layers_by_auxiliary(inventory)

    # The vocabulary head is the one unlayered contraction; everything else the
    # inventory charges is a layer term this file maps.
    unlayered_terms = {
        term for term, layers in by_term.items() if layers == {None}
    }
    assert unlayered_terms == {"final_vocabulary_head"}
    assert set(by_term) - unlayered_terms == set(_TERM_TO_SOURCE_KIND)
    assert "LM_HEAD" in unlayered_source_plan(profile)

    counted = set(by_auxiliary)
    assert counted - _UBIQUITOUS_AUXILIARY == set(_AUXILIARY_TO_SOURCE_KIND)
    for name in _UBIQUITOUS_AUXILIARY:
        assert by_auxiliary[name] == set(range(profile.layers)), name

    planned_kinds = set(source_kind_plan(profile))
    accounted = (
        set(_TERM_TO_SOURCE_KIND.values())
        | set(_AUXILIARY_TO_SOURCE_KIND.values())
        | set(_UNCHARGED_SOURCE_KINDS)
        | SPECULATIVE_SOURCE_KINDS
    )
    assert planned_kinds - accounted == set(), (
        "a source operator kind is neither charged by the analytical inventory "
        "nor listed as deliberately uncharged"
    )


def test_the_two_layers_agree_on_the_engram_geometry(profile, analytical):
    """The row count and the layer ids, derived twice.

    ``engram_hash_columns`` is a product in ``engram.py`` -- one row per
    (n-gram order, hash head) pair -- and the analytical layer carries the
    product while this front end derives it.  A silent disagreement here would
    change the Engram table's read traffic and nothing else would notice.
    """

    config = analytical.metadata["operator_config"]
    engram = analytical.metadata["engram"]
    assert profile.engram_hash_columns == int(config["engram_hash_columns"])
    assert profile.engram_hash_columns == int(engram["rows_read_per_token_per_module"])
    assert profile.engram_layers == tuple(int(x) for x in engram["layer_ids"])
    assert profile.engram_head_dim == int(engram["head_dim"])
    assert profile.engram_rows == tuple(int(x) for x in engram["num_embeddings"])
    assert profile.engram_heads == int(engram["n_heads"])
    assert profile.engram_max_ngram == int(engram["max_ngram_size"])
    # One FP8 row plus its E8M0 scales is the published packed row width.
    row_bytes = profile.engram_head_dim * (1 + 1 / profile.weight_scale_block)
    assert row_bytes == float(engram["row_bytes_packed"])


def test_the_two_layers_agree_on_the_candidate_pool(profile, analytical, inventory):
    """The Reindex cap is the pool, and it binds exactly the Reindex layers."""

    config = analytical.metadata["operator_config"]
    assert profile.candidate_blocks == int(config["candidate_topk_blocks"])
    assert profile.candidate_block == int(config["candidate_block_size"])
    assert profile.candidate_source_layer == int(config["candidate_source_layer_id"])
    pool = profile.candidate_pool_entries

    scans = {
        component.layer_index: component.operations
        for component in inventory.components
        if component.name == "indexer_qk_scan"
    }
    per_entry = 2 * profile.index_heads * profile.index_head_dim
    modes = {mode.layer: mode for mode in profile.layer_modes()}
    for layer, operations in scans.items():
        scanned = operations / per_entry
        if modes[layer].mode == "reindex":
            assert scanned == pool, (layer, scanned, pool)
        else:
            # An unbounded Full scan at this context reads more than the pool.
            assert scanned > pool, (layer, scanned, pool)

    # Every Reindex layer reads the mask, and only the candidate source makes it.
    by_source = _layers_by_source_kind(profile)
    reindex = {layer for layer, mode in modes.items() if mode.mode == "reindex"}
    assert by_source["CANDIDATE_MASK_READ"] == reindex
    assert by_source["CANDIDATE_BLOCK_SELECT"] == {profile.candidate_source_layer}


def test_the_two_layers_agree_on_the_quantization_blocks(profile, analytical):
    """Two FP4 formats, two blocks, two scale types -- and not one operator."""

    config = analytical.metadata["operator_config"]
    assert profile.weight_scale_block == int(config["fp8_weight_block"])
    assert FP4_MAIN_BLOCK != FP4_INDEX_BLOCK
    assert MAIN_LATENT_DTYPE in DTYPES
    plan = source_kind_plan(profile)
    assert plan["FP4_MAIN_QDQ"] == plan["FP4_INDEX_QDQ"] == ("QUANTIZE", "DEQUANTIZE")
    # Same neutral kinds, different numeric contract: that is the whole point.
    assert contract_for("FP4_MAIN_QDQ") != contract_for("FP4_INDEX_QDQ")
    assert contract_for("FP4_MAIN_QDQ") == "fp4_e2m1_s16_e4m3_to_fp8_v1"


# ---------------------------------------------------------------------------
# The CSA2 mode sequence
# ---------------------------------------------------------------------------
def test_the_mode_sequence_is_derived_and_agrees_with_the_committed_one(profile):
    derived = confront_layer_modes(profile)
    assert len(derived) == profile.layers
    committed = json.loads(CANDIDATE_PROFILE_PATH.read_text())["metadata"]
    assert [mode.label for mode in derived] == list(committed["attention_sequence"])


def test_the_four_attention_modes_and_their_layer_counts(profile, census, modes):
    assert set(census["layers_by_attention_mode"]) <= set(ATTENTION_MODES)
    counted = Counter(mode.mode for mode in modes)
    # Two window-only layers, then three encoder groups of six at ratio 2 and
    # five decoder groups of four at ratio 1: one index source per group, which
    # is one Full per encoder group, one Full then four Reindex in the decoder.
    window_only = sum(1 for mode in modes if mode.ratio == 0)
    groups = len(profile.index_source_layers)
    assert counted["swa"] == window_only
    assert counted["full"] + counted["reindex"] == groups
    assert counted["reuse"] == profile.layers - window_only - groups
    assert counted["full"] == len(profile.kv_source_layers)
    assert counted["reindex"] == sum(
        1 for mode in modes if mode.index_source and mode.uses_candidates
    )
    assert sum(counted.values()) == profile.layers


def test_the_report_group_structure_follows_from_the_released_id_lists(profile, modes):
    """SRC-DSV41-FLASH-REPORT section 2.2, as an observation not an assumption.

    Every CSA2 layer's index source is the highest index-source layer at or
    below it, so the groups are the gaps between consecutive index sources.
    """

    sources = sorted(profile.index_source_layers)
    csa2 = [mode for mode in modes if mode.ratio > 0]
    assert csa2[0].layer == sources[0]
    groups: list[list[int]] = []
    for mode in csa2:
        if mode.layer in sources:
            groups.append([])
        groups[-1].append(mode.layer)
    assert len(groups) == len(sources)
    encoder = [group for group in groups if modes[group[0]].ratio == 2]
    decoder = [group for group in groups if modes[group[0]].ratio == 1]
    assert [len(group) for group in encoder] == [6, 6, 6]
    assert [len(group) for group in decoder] == [4, 4, 4, 4, 4]
    for group in groups:
        assert modes[group[0]].index_source
        assert not any(modes[layer].index_source for layer in group[1:])


def test_the_shared_cache_has_one_writer_and_every_other_layer_reads_it(
    profile, modes
):
    by_source = _layers_by_source_kind(profile)
    owners = {mode.layer for mode in modes if mode.kv_owner}
    csa2 = {mode.layer for mode in modes if mode.ratio > 0}
    assert owners == set(profile.kv_source_layers)
    assert by_source["COMPRESS_PROJECT"] == owners
    assert by_source["COMPRESS_KV_WRITE"] == owners
    assert by_source["INDEX_KEY_PROJECT"] == owners
    # Every CSA2 layer, owner or not, reads the cache as a state resource.
    assert by_source["COMPRESSED_KV_VALID_VIEW"] == csa2
    assert by_source["ATTENTION_KV_VIEW"] == csa2
    # A window-only layer has no compressed path at all.
    for layer in set(range(profile.layers)) - csa2:
        sources = set(layer_source_plan(profile)[layer])
        assert not sources & {
            "ATTENTION_KV_VIEW",
            "COMPRESSED_KV_VALID_VIEW",
            "INDEX_SCORE",
            "INDEX_TOPK",
            "SHARED_INDEX_REUSE",
        }


def test_a_ratio_one_compressor_pools_nothing(profile, modes):
    """Plan section 5: ``COMPRESS_PROJECT`` as is, without ``COMPRESS_POOL``."""

    plan = layer_source_plan(profile)
    for mode in modes:
        sources = set(plan[mode.layer])
        pooled = {"COMPRESS_POOL", "COMPRESS_STATE_UPDATE"} & sources
        if mode.kv_owner and mode.ratio > 1:
            assert pooled == {"COMPRESS_POOL", "COMPRESS_STATE_UPDATE"}, mode.layer
        else:
            assert pooled == set(), mode.layer


def test_a_full_layer_indexes_the_latent_before_it_rotates_it(profile, modes):
    """The released order, which is not the obvious one.

    ``Attention._compress_kv``: the compressor produces the latent, the indexer
    derives its key from that *unrotated* latent, and only then is the latent
    rotated, FP4-quantized and written to the shared cache -- "the indexer
    needs the latent before RoPE, so it runs before the cache is written".  A
    plan that wrote the cache first would hand the indexer a rotated,
    requantized latent and silently change every index key in the model.
    """

    plan = layer_source_plan(profile)
    for mode in modes:
        if mode.mode != "full":
            continue
        sources = list(plan[mode.layer])
        assert sources.index("COMPRESS_PROJECT") < sources.index("INDEX_KEY_PROJECT")
        assert sources.index("INDEX_KEY_PROJECT") < sources.index("FP4_MAIN_QDQ")
        assert sources.index("INDEX_SCORE") < sources.index("FP4_MAIN_QDQ")
        assert sources.index("FP4_MAIN_QDQ") < sources.index("COMPRESS_KV_WRITE")
        assert sources.index("COMPRESS_KV_WRITE") < sources.index("SPARSE_ATTENTION")
        # The index key is rotated and quantized in its own format, and written
        # to its own cache, before the query is projected against it.
        assert sources.index("INDEX_KEY_WRITE") < sources.index("INDEX_QUERY_PROJECT")
        if mode.is_candidate_source:
            assert (
                sources.index("INDEX_SCORE")
                < sources.index("CANDIDATE_BLOCK_SELECT")
                < sources.index("INDEX_TOPK")
            )


def test_a_reuse_layer_scores_nothing(profile, modes):
    plan = layer_source_plan(profile)
    for mode in modes:
        if mode.mode != "reuse":
            continue
        sources = set(plan[mode.layer])
        assert "INDEX_SCORE" not in sources
        assert "INDEX_TOPK" not in sources
        assert "INDEX_QUERY_PROJECT" not in sources
        assert "SHARED_INDEX_REUSE" in sources


# ---------------------------------------------------------------------------
# The plan is a legal IR plan
# ---------------------------------------------------------------------------
def test_the_plan_has_no_defects(profile):
    assert plan_defects(profile) == []


def test_every_plan_entry_is_emitted_by_some_layer(profile):
    """A catalogue entry is not a lowering.

    ``plan_defects`` refuses a source kind the plan lowers that no layer emits,
    and this states the same thing from the other side, so a plan entry added
    for a mechanism this model does not have cannot sit unnoticed.
    """

    for speculative in (False, True):
        used = set(unlayered_source_plan(profile))
        for layer in layer_source_plan(profile, include_speculative=speculative):
            used |= set(layer)
        planned = set(source_kind_plan(profile, include_speculative=speculative))
        assert planned == used, sorted(planned ^ used)


def test_every_kind_is_registered_and_lowerable(profile):
    for source, neutral in source_kind_plan(profile, include_speculative=True).items():
        assert neutral, source
        for kind in neutral:
            assert kind in OPERATION_KINDS, (source, kind)
            assert kind in KERNEL_TO_ENGINE, (source, kind)


def test_the_am_e10_kinds_are_actually_used(profile, census):
    """WP-C's four kinds, present in the ordinary profile's own census.

    A kind added to the registry and used by nothing is not an addition; the
    three-party change AM-E10 made is only closed once a model lowers to it.
    """

    for kind in ("BLOCK_MAX", "CANDIDATE_MASK", "NGRAM_HASH", "ENGRAM_GATE"):
        assert census["kernels_by_kind"].get(kind, 0) > 0, kind
    assert census["kernels_by_kind"]["BLOCK_MAX"] == 1
    assert census["kernels_by_kind"]["CANDIDATE_MASK"] == 1
    # One operator per n-gram ORDER, per module: ``DMA.NGRAM_HASH`` states the
    # order it computes in its aux row and writes one column per hash head, so a
    # module's ``(max_ngram - 1) * n_heads`` columns are that many operators.
    assert census["kernels_by_kind"]["NGRAM_HASH"] == len(
        profile.engram_layers
    ) * (profile.engram_max_ngram - 1)
    assert census["kernels_by_kind"]["ENGRAM_GATE"] == len(profile.engram_layers)


def test_no_plan_identifier_carries_a_backend_term(profile):
    names = (
        set(source_kind_plan(profile, include_speculative=True))
        | set(ATTENTION_MODES)
        | set(CONTRACT_BASE_BY_SOURCE_KIND.values())
    )
    offenders = [
        (name, term)
        for name in names
        for term in FORBIDDEN_TERMS
        if term in name.lower()
    ]
    assert offenders == []


def test_numeric_contracts_are_canonical_semantic_identifiers(profile):
    for source in source_kind_plan(profile, include_speculative=True):
        contract = contract_for(source)
        assert CONTRACT_PATTERN.match(contract), contract
        assert not is_implementation_path(contract), contract


def test_the_new_capability_contracts_are_the_ones_the_plan_publishes():
    """Plan section 6.4's four V4.1 numeric contracts, spelled once."""

    published = {contract_for(source) for source in CONTRACT_BASE_BY_SOURCE_KIND}
    for name in (
        "fp4_e2m1_s16_e4m3_to_fp8_v1",
        "engram_gate_fp32_v1",
        "ngram_hash_u32_v1",
        "candidate_mask_v1",
    ):
        assert name in published, name


def test_the_contract_table_covers_the_plan_and_nothing_else(profile):
    planned = set(source_kind_plan(profile, include_speculative=True))
    assert planned == set(CONTRACT_BASE_BY_SOURCE_KIND)


def test_the_rms_norm_contract_is_the_frozen_one(profile):
    """Amendment A8: the engine dispatches on the name.

    This is the V4 front end's own lesson, and a V4.1 module that renamed it
    would have every RMSNorm in the graph refused at execution.
    """

    assert contract_for("RMS_NORM") == "deepseek_rmsnorm_binary32_v1"


def test_the_lowering_of_a_shared_kind_is_byte_for_byte_the_v4_one(profile):
    from compiler.frontends.v3.deepseek_v4 import lowering_plan as v4_plan

    v4 = v4_plan()
    shared = (
        "ATTENTION_KV_VIEW",
        "BIASED_TOPK_ROUTE",
        "COMPRESSED_KV_VALID_VIEW",
        "COMPRESS_KV_WRITE",
        "COMPRESS_POOL",
        "COMPRESS_PROJECT",
        "COMPRESS_STATE_UPDATE",
        "EXPERT_DISPATCH",
        "EXPERT_REDUCE",
        "FP8_LINEAR",
        "FP8_QDQ",
        "FP8_SWIGLU",
        "HC_EXPAND",
        "HC_POST",
        "HC_PRE",
        "HEAD_RMS_NORM",
        "INDEX_SCORE",
        "INDEX_TOPK",
        "KV_WINDOW_WRITE",
        "LM_HEAD",
        "MXFP4_SWIGLU",
        "RMS_NORM",
        "ROPE_APPLY",
        "ROPE_INVERSE",
        "ROUTER_SCORE",
        "ROUTER_WEIGHT_NORMALIZE",
        "SAMPLE",
        "SPARSE_ATTENTION",
        "SQRT_SOFTPLUS",
        "TOKEN_EMBED",
        "WINDOW_INDEX",
    )
    plan = source_kind_plan(profile)
    for source in shared:
        assert source in v4, source
        assert plan[source] == v4[source], source
    # ``GROUPED_OUTPUT_PROJECT`` is the one shared name whose V4.1 lowering is
    # longer, and the difference is a source node V4 has and V4.1 does not: V4's
    # graph carries ``wo_b`` as its own ``FP8_LINEAR``, while V4.1's layer plan
    # ends its attention at this one kind, so the dense second stage belongs to
    # it.  Without those two kernels the branch reaching ``HC_POST`` would be
    # ``o_groups * o_lora_rank`` wide where the residual stream is ``hidden``.
    assert plan["GROUPED_OUTPUT_PROJECT"] == v4["GROUPED_OUTPUT_PROJECT"] + (
        "QUANTIZE",
        "MATMUL",
    )


def test_the_lowering_plan_carries_both_namespaces(profile):
    plan = LOWERING_PLAN
    for mode in ("attention_full", "attention_reindex", "attention_reuse"):
        assert mode in plan, mode
    assert plan["attention_reuse"] == (
        "STATE_READ",
        "CONCAT",
        "STATE_READ",
        "CONCAT",
    )
    # A mode entry is the expansion of its source kinds, never a restatement.
    assert dict(attention_mode_plan(profile)) == {
        key: value for key, value in plan.items() if key in ATTENTION_MODES
    }
    kinds = source_kind_plan(profile)
    assert {key for key in plan if key.isupper()} == set(kinds)
    for mode, neutral in attention_mode_plan(profile).items():
        assert all(kind in OPERATION_KINDS for kind in neutral), mode


def test_a_full_scan_plans_more_than_a_reindex_and_a_reindex_more_than_a_reuse(
    profile, census
):
    """A layer's cost is a function of its role and nothing else.

    Three released facts decide what a layer plans -- its mode, its compression
    ratio (a ratio-1 compressor pools nothing) and whether it publishes the
    candidate pool -- plus whether it hosts an Engram module, which costs the
    same wherever it sits.  So every layer with the same role plans the same
    number of kernels, and the roles are ordered by how much of the compressed
    path they run.
    """

    counts = [sum(item.values()) for item in census["per_layer_kernels_by_kind"]]
    engram = set(profile.engram_layers)

    def role(mode) -> tuple[str, int, bool]:
        return (mode.mode, mode.ratio, mode.is_candidate_source)

    by_role: dict[tuple[str, int, bool], set[int]] = defaultdict(set)
    engram_delta: set[int] = set()
    for mode in profile.layer_modes():
        if mode.layer not in engram:
            by_role[role(mode)].add(counts[mode.layer])
    for mode in profile.layer_modes():
        if mode.layer not in engram:
            continue
        siblings = by_role[role(mode)]
        assert len(siblings) == 1, role(mode)
        engram_delta.add(counts[mode.layer] - next(iter(siblings)))
    for key, seen in by_role.items():
        assert len(seen) == 1, (key, sorted(seen))
    by_mode = defaultdict(set)
    for key, seen in by_role.items():
        by_mode[key[0]] |= seen
    assert min(by_mode["full"]) > max(by_mode["reindex"])
    assert max(by_mode["reindex"]) > max(by_mode["reuse"])
    assert max(by_mode["reuse"]) > max(by_mode["swa"])
    # One Engram module is one cost, whatever mode hosts it.
    plan = source_kind_plan(profile)
    expected = sum(
        len(plan[source])
        for source in (
            "ENGRAM_NGRAM_HASH",
            "ENGRAM_ROW_LOOKUP",
            "ENGRAM_KV_PROJECT",
            "ENGRAM_GATE",
        )
    )
    assert engram_delta == {expected}


# ---------------------------------------------------------------------------
# The released configuration, confronted
# ---------------------------------------------------------------------------
@pytest.mark.skipif(
    not V41_FLASH.config_path.is_file(),
    reason="the committed DeepSeek-V4.1-Flash config is not present",
)
def test_every_architecture_pin_is_confronted_with_the_released_config(profile):
    config = released_architecture_config(profile)
    validate_architecture_pins(profile, config)
    assert len(profile.architecture_pins) >= 30
    keys = [key for key, _ in profile.architecture_pins]
    assert len(keys) == len(set(keys))
    for key in (
        "kv_source_layer_ids",
        "index_source_layer_ids",
        "candidate_source_layer_id",
        "engram_layer_ids",
    ):
        assert key in keys, key


@pytest.mark.skipif(
    not V41_FLASH.config_path.is_file(),
    reason="the committed DeepSeek-V4.1-Flash config is not present",
)
def test_a_pin_that_disagrees_with_the_release_is_refused(profile):
    config = dict(released_architecture_config(profile))
    config["candidate_source_layer_id"] = profile.candidate_source_layer + 4
    with pytest.raises(DeepSeekV41KernelIRError, match="candidate_source_layer_id"):
        validate_architecture_pins(profile, config)


@pytest.mark.skipif(
    not (V41_FLASH.snapshot / "inference" / "model.py").is_file(),
    reason="the pinned DeepSeek-V4.1-Flash inference source is not present",
)
def test_the_pinned_inference_source_is_the_one_the_plan_describes(profile):
    digests = confront_source_digests(profile)
    assert set(digests) == {"inference/model.py", "inference/engram.py"}


def test_a_snapshot_without_the_inference_source_confronts_nothing(profile, tmp_path):
    assert confront_source_digests(profile, tmp_path) == {}


def test_a_changed_inference_source_is_refused(profile, tmp_path):
    (tmp_path / "inference").mkdir()
    (tmp_path / "inference" / "model.py").write_text("# not the pinned source\n")
    with pytest.raises(DeepSeekV41KernelIRError, match="lowering plan"):
        confront_source_digests(profile, tmp_path)


# ---------------------------------------------------------------------------
# Determinism, refusals and the speculative profile
# ---------------------------------------------------------------------------
def test_the_planned_census_is_deterministic(profile):
    assert planned_census(profile) == planned_census(profile)
    assert json.dumps(planned_census(profile), sort_keys=True) == json.dumps(
        planned_census(profile), sort_keys=True
    )


def test_the_census_totals_are_the_sum_of_its_parts(profile, census):
    total = Counter()
    for item in census["per_layer_kernels_by_kind"]:
        total.update(item)
    total.update(census["unlayered_kernels_by_kind"])
    assert dict(sorted(total.items())) == census["kernels_by_kind"]
    assert sum(total.values()) == census["kernel_count"]
    assert census["layer_count"] == profile.layers
    assert census["model_id"] == "deepseek-v4.1-flash"


def test_an_unknown_model_is_refused():
    with pytest.raises(DeepSeekV41KernelIRError, match="unknown DeepSeek-V4.1 model"):
        resolve_model_profile("deepseek-v4-flash-0731")


def test_a_context_beyond_the_architectural_capacity_is_rejected():
    with pytest.raises(DeepSeekV41KernelIRError, match="architectural"):
        export_deepseek_v41_kernel_graph(
            context_tokens=ARCHITECTURAL_MAX_CONTEXT + 128
        )


def test_a_context_that_is_not_whole_windows_is_rejected(profile):
    with pytest.raises(DeepSeekV41KernelIRError, match="sliding windows"):
        export_deepseek_v41_kernel_graph(
            context_tokens=DEFAULT_CONTEXT_TOKENS + 1
        )


def test_the_export_names_every_artifact_it_does_not_have(profile, tmp_path):
    """The refusal is the deliverable while the lock does not exist.

    Gate DS41-I2 is not closed by this package, and the way that is stated is a
    build that stops naming each artifact and the tool that produces it -- the
    V4 front end's own behaviour for the Pro release.
    """

    missing = missing_ir_artifacts(profile, tmp_path, tmp_path / "absent.lock.json")
    joined = "\n".join(missing)
    # The snapshot is named with the revision to fetch, and the lock with the
    # tool that produces it and the number of bytes it has to read.
    assert str(tmp_path) in joined
    assert profile.revision in joined
    assert "tools/build_checkpoint_lock.py" in joined
    assert f"{profile.release.payload_bytes:,}" in joined
    with pytest.raises(DeepSeekV41KernelIRError) as caught:
        export_deepseek_v41_kernel_graph(
            snapshot=tmp_path, checkpoint_lock_path=tmp_path / "absent.lock.json"
        )
    assert "artifact" in str(caught.value)
    # The lock is the outstanding one on this host whatever else has landed.
    outstanding = missing_ir_artifacts(
        profile, profile.release.snapshot, profile.release.checkpoint_lock
    )
    if not profile.release.checkpoint_lock.is_file():
        assert any("checkpoint lock" in item for item in outstanding)


# ---------------------------------------------------------------------------
# The emitted document
# ---------------------------------------------------------------------------
#: The checkpoint artifacts a byte-pinned graph needs.  Absent, the tests below
#: skip rather than fail: a fresh checkout holds no 510 GB checkpoint, and the
#: refusal that stands in its place is checked above.
_ARTIFACTS_PRESENT = not missing_ir_artifacts(
    V41_FLASH_PROFILE,
    V41_FLASH_PROFILE.release.snapshot,
    V41_FLASH_PROFILE.release.checkpoint_lock,
)

emitted_only = pytest.mark.skipif(
    not _ARTIFACTS_PRESENT,
    reason="the DeepSeek-V4.1-Flash checkpoint artifacts are not on this host",
)


@pytest.fixture(scope="module")
def emitted(profile):
    if not _ARTIFACTS_PRESENT:
        pytest.skip("the DeepSeek-V4.1-Flash checkpoint artifacts are not present")
    return export_deepseek_v41_kernel_graph(model=profile)


@pytest.fixture(scope="module")
def emitted_census(emitted, profile):
    return graph_census_v41(emitted, profile)


def _emitted_layers_by_source_kind(graph) -> dict[str, set[int]]:
    layers: dict[str, set[int]] = defaultdict(set)
    for kernel in graph.kernels:
        source_kind = str(kernel.attributes.get("source_operation_kind", ""))
        if kernel.layer is not None:
            layers[source_kind].add(kernel.layer)
    return dict(layers)


@emitted_only
def test_the_emitted_census_matches_the_analytical_operator_inventory_per_layer(
    emitted, inventory
):
    """WP-D's cross-check, taken on the **document** rather than on the plan.

    :func:`test_the_census_matches_the_analytical_operator_inventory_per_layer`
    confronts the analytical inventory with the executable *plan*; this confronts
    it with the graph a backend will actually consume, which is the one a
    deployment is built from.  The two are the same claim only while the emitter
    realises the plan, and that is exactly what could drift silently: a handler
    that emitted an indexer on a Reuse layer, or none on a Full one, would leave
    every layer count in the analytical model describing a different model from
    the one the device runs.
    """

    by_term = _layers_by_term(inventory)
    by_auxiliary = _layers_by_auxiliary(inventory)
    by_source = _emitted_layers_by_source_kind(emitted)

    disagreements: list[str] = []
    for term, source_kind in _TERM_TO_SOURCE_KIND.items():
        analytical_layers = by_term[term]
        observed = by_source.get(source_kind, set())
        if analytical_layers != observed:
            disagreements.append(
                f"{term} is charged on {sorted(analytical_layers)} and "
                f"{source_kind} is emitted on {sorted(observed)}"
            )
    for name, source_kind in _AUXILIARY_TO_SOURCE_KIND.items():
        analytical_layers = by_auxiliary[name]
        observed = by_source.get(source_kind, set())
        if analytical_layers != observed:
            disagreements.append(
                f"{name} is counted on {sorted(analytical_layers)} and "
                f"{source_kind} is emitted on {sorted(observed)}"
            )
    assert disagreements == []
    # And every layer the ubiquitous auxiliaries charge is a layer the document
    # has, which is the other half of "per layer": the two descriptions agree on
    # the layer *count* as well as on which mechanism sits where.
    assert {kernel.layer for kernel in emitted.kernels if kernel.layer is not None} == {
        index for index in range(V41_FLASH_PROFILE.layers)
    }


@emitted_only
def test_the_exit_criterion_counts_are_zero(emitted_census):
    """Gate DS41-I2: no unknown, unpriced, unreferenced or unbound anything."""

    assert emitted_census["unknown"] == 0, emitted_census["unknown_kernels"]
    assert emitted_census["unpriced"] == 0, emitted_census["unpriced_kernels"]
    assert emitted_census["unreferenced"] == 0, emitted_census[
        "unreferenced_tensors"
    ]
    assert emitted_census["unbound"] == 0, emitted_census["unbound_tensors"]


@emitted_only
def test_the_document_realises_the_plan_kind_for_kind_and_layer_for_layer(
    emitted_census, census
):
    """The plan and the document are one description, not two."""

    assert emitted_census["kernel_count"] == census["kernel_count"]
    assert emitted_census["kernels_by_kind"] == census["kernels_by_kind"]
    assert emitted_census["per_layer_kernels_by_kind"] == census[
        "per_layer_kernels_by_kind"
    ]
    assert emitted_census["per_layer_source_kinds"] == census[
        "per_layer_source_kinds"
    ]
    assert emitted_census["unlayered_kernels_by_kind"] == census[
        "unlayered_kernels_by_kind"
    ]
    assert emitted_census["source_kinds"] == census["source_kinds"]
    assert emitted_census["attention_modes_by_layer"] == census[
        "attention_modes_by_layer"
    ]


@emitted_only
def test_the_document_is_neutral(emitted):
    """FORBIDDEN_TERMS clean, registered kinds, one ABI lowering each."""

    from compiler.ir.v3.kernel_ir import check_neutral

    assert check_neutral(emitted) == []
    for kernel in emitted.kernels:
        assert kernel.kind in OPERATION_KINDS, kernel.kernel_id
        assert kernel.kind in KERNEL_TO_ENGINE, kernel.kernel_id
        spec = KERNEL_TO_ENGINE[kernel.kind]
        assert len(kernel.inputs) <= spec.inputs, kernel.kernel_id
        assert len(kernel.outputs) <= spec.outputs, kernel.kernel_id
    names = [kernel.kernel_id for kernel in emitted.kernels]
    names += [tensor.tensor_id for tensor in emitted.tensors]
    names += [state.state_id for state in emitted.states]
    names += [
        key for kernel in emitted.kernels for key in kernel.attributes
    ]
    offenders = [
        (name, term)
        for name in names
        for term in FORBIDDEN_TERMS
        if term in name.lower()
    ]
    assert offenders == [], offenders[:10]


@emitted_only
def test_every_weight_is_bound_and_every_derived_constant_names_a_generator(
    emitted,
):
    """A weight is checkpoint bytes; a constant is bytes or a named generator."""

    from runtime.sim.generators import registered

    bound = 0
    for tensor in emitted.tensors:
        if tensor.role == "weight":
            assert tensor.binding is not None, tensor.tensor_id
            bound += 1
        if tensor.role == "constant":
            assert tensor.binding is not None or tensor.generator, tensor.tensor_id
            if tensor.generator:
                assert tensor.generator in registered(), tensor.generator
    assert bound == sum(
        1 for tensor in emitted.tensors if tensor.binding is not None
    )
    # Every bound range is inside the pinned payload and names a real shard.
    for tensor in emitted.tensors:
        if tensor.binding is None:
            continue
        binding = tensor.binding
        assert binding.bytes > 0
        assert (V41_FLASH.snapshot / binding.path).is_file(), binding.path
        assert len(binding.sha256) == 64


@emitted_only
def test_the_shared_cache_has_one_writer_and_every_reader_names_it(emitted, modes):
    """CSA2 in the document: four writers, and every other layer a reader.

    Plan section 6.1 makes this a placement rule -- every reader of a shared
    cache is placed on the stage that owns it -- and a rule about readers needs
    the readers to be *visible*.  So a reuse layer's compressed view names the
    owner's resource, and the document says which layer published it.
    """

    writers: dict[str, set[int]] = defaultdict(set)
    readers: dict[str, set[int]] = defaultdict(set)
    for kernel in emitted.kernels:
        for state in kernel.state_writes:
            writers[state].add(kernel.layer)
        for state in kernel.state_reads:
            readers[state].add(kernel.layer)
    owners = set(V41_FLASH_PROFILE.kv_source_layers)
    compressed = {
        state: layers
        for state, layers in writers.items()
        if state.startswith("compressed_key_value.")
    }
    assert len(compressed) == len(owners)
    for state, layers in compressed.items():
        assert len(layers) == 1, (state, layers)
        owner = next(iter(layers))
        assert owner in owners
        # Every layer from the owner to the next one reads exactly this cache.
        expected = {
            mode.layer
            for mode in modes
            if mode.ratio
            and max(
                source for source in V41_FLASH_PROFILE.kv_source_layers
                if source <= mode.layer
            )
            == owner
        }
        assert readers[state] == expected, (state, sorted(readers[state]))
    selections = {
        state: layers
        for state, layers in writers.items()
        if state.startswith("index_selection.")
    }
    assert set().union(*selections.values()) == set(
        V41_FLASH_PROFILE.index_source_layers
    )
    pool = [state for state in writers if state.startswith("candidate_pool_mask.")]
    assert pool == [
        f"candidate_pool_mask.main.layer.{V41_FLASH_PROFILE.candidate_source_layer}"
    ]
    assert readers[pool[0]] == {
        mode.layer for mode in modes if mode.mode == "reindex"
    }


@emitted_only
def test_the_document_is_reproducible(emitted, profile, tmp_path):
    """Two exports of one release are the same document and the same identity."""

    again = export_deepseek_v41_kernel_graph(model=profile)
    assert again.graph_id == emitted.graph_id
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert emitted.write(first) == again.write(second)
    assert first.read_bytes() == second.read_bytes()


def test_the_speculative_profile_is_planned_and_refused(profile):
    """DSpark is behind the flag, and the flag says what it does not emit yet."""

    with pytest.raises(DeepSeekV41KernelIRError) as caught:
        export_deepseek_v41_kernel_graph(model=profile, include_speculative=True)
    message = str(caught.value)
    for kind in SPECULATIVE_SOURCE_KINDS:
        assert kind in message, kind


def test_the_speculative_profile_adds_dspark_and_keeps_the_backbone_intact(profile):
    ordinary = planned_census(profile)
    speculative = planned_census(profile, include_speculative=True)
    assert speculative["layer_count"] == profile.layers + profile.draft_stages
    assert speculative["kernel_count"] > ordinary["kernel_count"]
    added = set(speculative["source_kinds"]) - set(ordinary["source_kinds"])
    assert added == set(SPECULATIVE_SOURCE_KINDS)
    # The backbone layers are untouched except where the draft head reads them.
    for layer in range(profile.layers):
        before = ordinary["per_layer_source_kinds"][layer]
        after = dict(speculative["per_layer_source_kinds"][layer])
        if layer in profile.target_layers:
            assert after.pop("TARGET_HIDDEN_CAPTURE") == 1
        assert after == before, layer
    assert speculative["attention_modes_by_layer"] == ordinary[
        "attention_modes_by_layer"
    ]


def test_the_draft_stages_route_their_own_expert_counts(profile):
    backbone = profile.moe_config(0)
    draft = profile.moe_config(profile.layers)
    assert backbone == (profile.routed_experts, profile.top_k)
    assert draft != backbone
    assert draft[0] < backbone[0] and draft[1] < backbone[1]
