"""WP-G: the V4.1 HBM comparator, and the model-blindness claim it rests on.

Plan section 3.3 says the HBM/SRAM backend is model-blind and is reused as is,
with "none beyond the new IR kinds" required of it.  These tests are the
machine-checkable form of that sentence:

* the two shipped profiles do not move -- the comparator is a *new* record, and
  a V4.1 addition that re-digested ``cluster-32`` would invalidate deployments
  and cycle evidence that quote it;
* ``CLUSTER_N`` is reachable for any admissible node count and refuses the
  counts AM-R1 refuses, with the count a parameter rather than a constant;
* the four AM-E10 kinds plan and lower on the unmodified backend, and each one's
  operator carries the operand and aux row its engine makes **mandatory** -- an
  operator missing a mandatory immediate is admitted by the verifier and traps
  at issue, which is the failure these tests exist to catch at compile time; and
* the one thing that does *not* work is recorded as a failing expectation rather
  than papered over: AM-E10's ``fp4_e2m1_s16_e4m3`` has no ABI 3.0 storage type,
  so no backend can place a view of it.  The test asserts the refusal, and it is
  the test that flips when the storage type lands.
"""

from __future__ import annotations

import dataclasses
import hashlib

import pytest

from compiler.backends.hbm_sram.capability import (
    CLUSTER_DOMAIN_SIZE,
    capability_for,
    cluster_n_capability,
    profile_difference,
)
from compiler.backends.hbm_sram.lower import _DTYPE_FEATURE
from compiler.backends.hbm_sram.plan import DTYPE_MAP, PlanError
from compiler.ir.v3.kernel_ir import check_neutral
from compiler.ir.v3.lowering import KERNEL_TO_ENGINE, OPTIONAL_INPUT_SLOTS
from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import (
    DTYPE_BITS,
    Dma,
    DType,
    Feature,
    Major,
    Route,
    TopologyClass,
    Vector,
)
from runtime.reference.engram import NGRAM_HASH_NUMERIC_CONTRACT

from tools.build_deepseek_v41_hbm_comparator import (
    MAIN_LATENT_DTYPE,
    block_max_view_tiling,
    V41_FLASH_PROFILE,
    am_e10_probe_graph,
    build_document,
    comparator_capability,
    comparator_sizing,
    lower,
    v41_added_contracts,
)

#: The digest the committed evidence quotes for the shipped 32-node record.
CLUSTER_32_DIGEST_PREFIX = "1eb2e92dac1d9fb8"

NODES = CLUSTER_DOMAIN_SIZE
PROBE_ROWS = 1 << 12


@pytest.fixture(scope="module")
def probe():
    """The AM-E10 probe with the latent in a format the ABI can store."""
    return am_e10_probe_graph(engram_rows=PROBE_ROWS, latent_dtype="fp8_e4m3fn")


@pytest.fixture(scope="module")
def lowered(probe):
    return lower(probe, NODES)


def _operators(deployment, family: int, sub: int) -> list[dict]:
    rows = []
    for descriptor in deployment.table.descriptors():
        payload = descriptor.payload
        if "engine_sub" not in payload:
            continue
        if (int(payload["engine_family"]), int(payload["engine_sub"])) == (family, sub):
            rows.append(payload)
    return rows


def _aux(payload, slot: int):
    from runtime.abi3.constants import NO_ID

    value = payload.get(f"aux_id_{slot}")
    return None if value is None or int(value) == int(NO_ID) else int(value)


# ---------------------------------------------------------------------------
# nothing shipped moves
# ---------------------------------------------------------------------------
def test_the_two_shipped_profiles_are_unchanged() -> None:
    assert capability_for("cluster-32").digest.startswith(CLUSTER_32_DIGEST_PREFIX)
    difference = profile_difference()
    assert difference["unexpected"] == []
    assert difference["identical_feature_bits"]
    assert "fabric" not in capability_for("cluster-32").to_dict()
    assert "fabric" not in capability_for("single-chip").to_dict()


# ---------------------------------------------------------------------------
# the profile
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("nodes", [CLUSTER_DOMAIN_SIZE, 2 * CLUSTER_DOMAIN_SIZE, 64])
def test_cluster_n_binds_its_fabric_to_its_route_groups(nodes: int) -> None:
    """AM-R1: the verifier binds the two, so the record may not disagree."""
    capability = cluster_n_capability(node_count=nodes)
    cluster = capability.fabric["cluster"]
    assert capability.topology_class == int(TopologyClass.CLUSTER_N)
    assert capability.limits["max_nodes"] == nodes
    assert capability.link["peers_per_node"] == nodes - 1
    assert capability.link["route_groups"] == cluster["domains"]
    assert cluster["domains"] * cluster["domain_size"] == nodes


@pytest.mark.parametrize(
    "nodes, reason",
    [(32, "CLUSTER_32"), (1, "SINGLE_CHIP"), (12, "domains")],
)
def test_cluster_n_refuses_a_count_the_class_cannot_express(
    nodes: int, reason: str
) -> None:
    with pytest.raises(ValueError, match=reason):
        cluster_n_capability(node_count=nodes)


def test_the_node_count_is_a_parameter_not_a_cardinality() -> None:
    with pytest.raises(KeyError, match="node_count"):
        capability_for("cluster-n")
    with pytest.raises(KeyError, match="own node count"):
        capability_for("cluster-32", node_count=64)


def test_the_comparator_declares_the_four_am_e10_contracts_and_no_others() -> None:
    added = v41_added_contracts()
    assert added == (
        "candidate_mask_v1",
        # NOT ``engram_gate_fp32_v1``.  The V4.1 front end pins
        # ``engram_gate_pinned_form`` because the frozen v1 contract differs from
        # this release's own ``Engram.forward`` in four ways that all change the
        # VALUE -- run on one input the two gates are 0.784 and 0.683 -- so naming
        # v1 asked the device to compute a gate this model does not have, and the
        # emitted token disagreed with the reference oracle while V4-Flash's, whose
        # path has no Engram, agreed.  v1 is frozen ABI and is left alone; the
        # comparator declares the contract whose implementation is the release's
        # expression.  This test asserted the old name after the front end moved.
        "engram_gate_pinned_form_v1",
        "fp4_e2m1_s16_e4m3_to_fp8_v1",
        "ngram_hash_u32_v1",
    )
    shipped = set(capability_for("cluster-32").numeric_contracts)
    declared = set(comparator_capability(NODES).numeric_contracts)
    assert declared - shipped == set(added)
    # The gate a declaration has to pass: the name must be implemented, and
    # ``ngram_hash_u32_v1`` is only declarable because its reference now names it.
    assert NGRAM_HASH_NUMERIC_CONTRACT == "ngram_hash_u32_v1"


def test_the_node_count_is_derived_from_the_released_profile() -> None:
    sizing = comparator_sizing()
    assert sizing["context_tokens"] == 200_000
    # 307.5 GB of weights with the Engram tables in host memory, not on device.
    assert sizing["on_device_weight_bytes"] == 307_527_990_600
    assert sizing["host_resident_weight_bytes"] == 202_758_032_400
    assert sizing["required_bytes"] == (
        sizing["on_device_weight_bytes"] + sizing["session_kv_bytes"]
    )
    floor = sizing["capacity_floor_nodes"]
    per_node = sizing["hbm_bytes_per_node"]
    assert (floor - 1) * per_node < sizing["required_bytes"] <= floor * per_node
    assert sizing["smallest_admissible_nodes"] >= floor


# ---------------------------------------------------------------------------
# the probe: no frozen geometry, and it is admitted
# ---------------------------------------------------------------------------
def test_the_probe_is_neutral_and_takes_every_extent_from_the_profile(probe) -> None:
    assert check_neutral(probe) == []
    shapes = {tensor.tensor_id: tensor.shape for tensor in probe.tensors}
    assert shapes["embed"] == (V41_FLASH_PROFILE.vocabulary, V41_FLASH_PROFILE.hidden)
    assert shapes["pool.block_ids"][1] == (
        V41_FLASH_PROFILE.sliding_window + V41_FLASH_PROFILE.candidate_blocks
    )
    assert shapes["reindex.indices"][1] == (
        V41_FLASH_PROFILE.sliding_window + V41_FLASH_PROFILE.index_topk
    )
    orders = probe.source["ngram_orders"]
    assert orders[-1] == V41_FLASH_PROFILE.engram_max_ngram
    assert len(orders) * V41_FLASH_PROFILE.engram_heads == (
        V41_FLASH_PROFILE.engram_hash_columns
    )


def test_the_probe_is_admitted_and_rebuilds_byte_identically(lowered) -> None:
    report, _ = lowered
    assert report["admitted"], report["verifier_errors"]
    assert report["checker_ok"], report["checker_errors"]
    assert report["rebuild_identical"]
    assert report["hbm_fits"]
    assert report["topology_class"] == "CLUSTER_N"
    assert report["node_count"] == NODES


# ---------------------------------------------------------------------------
# the mandatory rows of the four new sub-ops
# ---------------------------------------------------------------------------
def test_block_max_and_candidate_mask_state_their_block_width(lowered) -> None:
    _, deployment = lowered
    block = V41_FLASH_PROFILE.candidate_block
    for sub in (Route.BLOCK_MAX, Route.CANDIDATE_MASK):
        operators = _operators(deployment, int(Major.ROUTE), int(sub))
        assert operators, f"no ROUTE.{Route(sub).name} operator was emitted"
        for payload in operators:
            assert _aux(payload, 0) == block


def test_candidate_mask_states_the_pool_population_bound(lowered) -> None:
    _, deployment = lowered
    operators = _operators(deployment, int(Major.ROUTE), int(Route.CANDIDATE_MASK))
    assert [_aux(p, 1) for p in operators] == [
        V41_FLASH_PROFILE.candidate_pool_entries
    ] * len(operators)


def test_ngram_hash_carries_its_three_mandatory_immediates(lowered) -> None:
    from runtime.abi3.constants import NO_ID

    _, deployment = lowered
    operators = _operators(deployment, int(Major.DMA), int(Dma.NGRAM_HASH))
    assert len(operators) == len(
        range(2, V41_FLASH_PROFILE.engram_max_ngram + 1)
    )
    orders = sorted(_aux(p, 0) for p in operators)
    assert orders == list(range(2, V41_FLASH_PROFILE.engram_max_ngram + 1))
    for payload in operators:
        assert _aux(payload, 2) == V41_FLASH_PROFILE.engram_compressed_vocabulary
        assert _aux(payload, 1) is not None
        # in0..in2 bound, in3 -- the dead-position flags -- stated absent.
        for slot in (0, 1, 2):
            assert int(payload[f"input_view_{slot}"]) != int(NO_ID)
        assert int(payload["input_view_3"]) == int(NO_ID)
        assert _aux(payload, 3) == 2


def test_the_gate_packs_five_operands_into_the_abi_s_four_views(lowered) -> None:
    _, deployment = lowered
    operators = _operators(deployment, int(Major.VECTOR), int(Vector.ENGRAM_GATE))
    assert len(operators) == 1
    assert KERNEL_TO_ENGINE["ENGRAM_GATE"].inputs == 4
    assert max(op.inputs for op in KERNEL_TO_ENGINE.values()) == 4


def test_the_mask_reaches_index_topk_s_fourth_slot(lowered) -> None:
    from runtime.abi3.constants import NO_ID

    _, deployment = lowered
    assert OPTIONAL_INPUT_SLOTS["INDEX_TOPK"] == frozenset({0, 1, 2, 3})
    assert KERNEL_TO_ENGINE["INDEX_TOPK"].inputs == 4
    operators = _operators(deployment, int(Major.ROUTE), int(Route.INDEX_TOPK))
    masked = [p for p in operators if int(p["input_view_3"]) != int(NO_ID)]
    assert len(masked) == 1, "the reindex top-k must carry the candidate mask"
    assert _aux(masked[0], 0) == V41_FLASH_PROFILE.index_topk


# ---------------------------------------------------------------------------
# the refusals: an undeclared immediate must fail the build, not the device
# ---------------------------------------------------------------------------
def _without_attribute(graph, kind: str, key: str):
    kernels = []
    for kernel in graph.kernels:
        if kernel.kind == kind and key in kernel.attributes:
            attributes = {k: v for k, v in kernel.attributes.items() if k != key}
            kernel = dataclasses.replace(kernel, attributes=attributes)
        kernels.append(kernel)
    return dataclasses.replace(graph, kernels=tuple(kernels))


@pytest.mark.parametrize(
    "kind, key, message",
    [
        ("BLOCK_MAX", "block", "states its block width in aux0"),
        ("CANDIDATE_MASK", "block", "states its block width in aux0"),
        ("NGRAM_HASH", "order", "declares no order"),
        ("NGRAM_HASH", "compressed_vocabulary", "compressed_vocabulary"),
    ],
)
def test_an_undeclared_mandatory_immediate_is_refused_at_compile_time(
    probe, kind: str, key: str, message: str
) -> None:
    graph = _without_attribute(probe, kind, key)
    with pytest.raises(PlanError, match=message):
        lower(graph, NODES)


def test_the_ratio_grammar_resolves_a_block_the_table_does_not_enumerate() -> None:
    """A18's extent table must not be an enumeration of one model's ratios.

    V4.1's candidate block is eight and V4's ratios are four and 128, so the
    table had no entry for ``context_groups_ratio8`` -- and an absent entry is
    read as "no context-sized axis", which resolves the axis to the span.
    """
    from compiler.backends.hbm_sram.plan import request_extent_for

    assert request_extent_for("context_groups_ratio8").unit == (
        V41_FLASH_PROFILE.candidate_block
    )
    assert request_extent_for("context_groups_ratio4").unit == 4
    assert request_extent_for("span_groups_ratio128").unit == 128
    # Still not an invitation to guess: a name outside the grammar resolves to
    # nothing rather than to a plausible function.
    assert request_extent_for("pool_blocks") is None
    assert request_extent_for("context_groups_ratio0") is None


def test_the_block_max_view_pair_does_not_tile_yet(lowered) -> None:
    """The one place the probe is admitted and would still trap.

    Recorded as an expectation, with the numbers, because the fix -- naming
    ``ROUTE.BLOCK_MAX`` in ``CONTEXT_LOOP_OPS`` -- changes the dispatch
    granularity of an operator nothing has qualified, and that belongs with the
    graph and the execution that can qualify it.  This test is what flips when
    it lands.
    """
    _, deployment = lowered
    rows = block_max_view_tiling(deployment)
    assert rows, "no ROUTE.BLOCK_MAX operator was emitted"
    for row in rows:
        assert row["block"] == V41_FLASH_PROFILE.candidate_block
        assert row["required_score_columns"] == -(
            -row["candidate_columns"] // row["block"]
        )
        assert not row["tiles"], (
            "the view pair now tiles, so ROUTE.BLOCK_MAX's context axis is "
            "resolved: drop this expectation and the known_gaps entry with it"
        )


def test_the_plan_document_states_its_known_gaps() -> None:
    document, _ = build_document(
        ir=None, context_tokens=200_000, node_count=NODES, engram_rows=PROBE_ROWS
    )
    gaps = {gap["id"] for gap in document["known_gaps"]}
    assert gaps == {
        "am-e10-dtype-storage-type-forward-rule-unqualified",
        "block-max-context-axis-not-resolved-by-a-loop",
        "deployment-check-case-does-not-cover-the-new-kinds",
    }


def test_the_new_dtype_now_has_its_own_abi_storage_type() -> None:
    """AM-E10's dtype places, under its OWN storage code and feature bit.

    This test is the flipped form of the refusal it replaces.  The refusal was
    recorded rather than worked around because the cheap alternative -- mapping
    ``fp4_e2m1_s16_e4m3`` onto ``MXFP4_E2M1``, whose scale is E8M0 per 32 --
    would hand an E4M3-per-16 table to an engine expecting the other format,
    which is exactly what the separate neutral name exists to prevent.  So the
    assertions here are about the SEPARATION, not merely about admission: a
    distinct storage code, four bits wide, and a feature bit of its own that
    neither of the two formats it is adjacent to implies.
    """
    graph = am_e10_probe_graph(engram_rows=PROBE_ROWS, latent_dtype=MAIN_LATENT_DTYPE)
    lower(graph, NODES)  # no refusal: the view places

    assert DTYPE_MAP[MAIN_LATENT_DTYPE] is DType.FP4_E2M1_S16_E4M3
    assert DTYPE_MAP[MAIN_LATENT_DTYPE] is not DType.MXFP4_E2M1
    assert DTYPE_BITS[DType.FP4_E2M1_S16_E4M3] == 4
    assert (
        _DTYPE_FEATURE[int(DType.FP4_E2M1_S16_E4M3)]
        is Feature.FP4_E2M1_S16_E4M3_TENSOR
    )
    assert (
        _DTYPE_FEATURE[int(DType.MXFP4_E2M1)]
        is not Feature.FP4_E2M1_S16_E4M3_TENSOR
    )


# ---------------------------------------------------------------------------
# the plan document
# ---------------------------------------------------------------------------
def test_the_plan_document_rebuilds_byte_identically() -> None:
    first, _ = build_document(
        ir=None, context_tokens=200_000, node_count=NODES, engram_rows=PROBE_ROWS
    )
    second, _ = build_document(
        ir=None, context_tokens=200_000, node_count=NODES, engram_rows=PROBE_ROWS
    )
    assert canonical_json(first) == canonical_json(second)
    assert hashlib.sha256(canonical_json(first)).hexdigest() == (
        hashlib.sha256(canonical_json(second)).hexdigest()
    )
    assert first["deployment"]["status"] == "not_built"
    assert first["new_dtype"]["placed"] is True
    assert first["new_dtype"]["error"] is None
    assert first["lowering"]["admitted"]
