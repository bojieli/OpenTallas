"""The DeepSeek-V4.1-Flash ROM array backend (plan WP-F, gate DS41-P3).

``compiler.backends.rom.deepseek_v41_array`` lowers the V4.1 neutral graph onto
AM-R1's ``CLUSTER_N`` with the routed expert banks node-sharded by consecutive
ownership, the dense operands replicated, and the Engram tables off ROM.  It is
a re-parameterisation of the V4 array backend, and these checks hold it to the
four things the plan asks of it plus the two properties every ROM product keeps:

* **the node count is derived, and the plan's 51 is refused** -- by whole-expert
  ownership (384 % 51 = 21) and by the declared 8-device NVLink domain
  (51 % 8 = 3), with the admissible counts named and the direction upward;
* **the capability** declares ``CLUSTER_N``, a fabric whose partition is exact,
  the cluster chip's engine lane mix and link endpoints, 384 expert ids, and the
  four AM-E10 numeric contracts, whose names are confronted with the four
  modules that define them;
* **Engram is off ROM**, its bytes derived from the released configuration and
  equal to the inventory's, with the placements that do not fit refused;
* **placement** -- every expert's ROM bytes on its owning node at one
  node-local address, emitted as an A28 ``node_segments`` image, and the routed
  view presenting ``E/N`` local experts against the global bound;
* **the inverse proof** reconstructs the checkpoint from the node-sharded
  images, and **two clean builds are byte-identical** (DS41-P3 exit criterion);
* **descriptor multiset equality** with the HBM deployment of the same IR is
  implemented here and exercised on the pairs that are buildable today; the
  V4.1 cross-backend pair needs WP-G and is reported as pending, with the
  command, rather than asserted.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import math
from pathlib import Path

import pytest

from compiler.backends.rom.common.check import check_rom_schedule
from compiler.backends.rom.common.inverse import check_rom_inverse
from compiler.backends.rom.deepseek_v41_array import (
    DEFAULT_ENGRAM_PLACEMENT,
    DOMAIN_COUNT,
    DOMAIN_SIZE,
    ENGRAM_TABLE_ROLES,
    ENGRAM_TABLE_TENSOR_MARKER,
    EXPERTS_PER_NODE,
    NODE_COUNT,
    PLAN_NODE_COUNT,
    ROUTED_EXPERTS,
    TARGET_ID,
    V41_NUMERIC_CONTRACTS,
    DeepSeekV41ArrayError,
    admissible_node_counts,
    build_deepseek_v41_array_rom_deployment,
    cluster_n_link,
    compare_descriptor_multisets,
    deepseek_v41_array_rom_capability,
    engram_residency,
    engram_shard_feasibility,
    engram_table_bytes,
    engram_tables_are_off_rom,
    expert_parallel_node_count,
    v41_array_geometry,
)
from compiler.backends.rom.common.image import plan_resident_regions
from compiler.frontends.v3.deepseek_v41 import V41_FLASH_PROFILE
from compiler.backends.rom.deepseek_v41_array import (
    BANK_BYTES as BANK_BYTES_DECLARED,
    DENSE_BANKS as DENSE_BANKS_DECLARED,
    EXPERT_BANKS as EXPERT_BANKS_DECLARED,
)
from runtime.abi3.capability import Capability, canonical_json
from runtime.abi3.constants import (
    Major,
    NodeClass,
    ParticipantScope,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.constants import Tensor as TensorOp
from runtime.abi3.descriptors import CollectiveOp, ExtendedDescriptorType
from runtime.abi3.verifier import verify_deployment

ROOT = Path(__file__).resolve().parents[1]

# The synthetic DeepSeek-shaped graph builder lives in the ROM backend suite,
# exactly as the V4 array suite loads it: by path, so that test file does not
# become an importable package.
_spec = importlib.util.spec_from_file_location(
    "rom_backend_suite", ROOT / "tests" / "compiler" / "test_rom_backend.py"
)
_suite = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_suite)
deepseek_shaped_graph = _suite.deepseek_shaped_graph

#: One owned expert per node, which is what the fixture's expert count has to be
#: for the ownership rule to be exercised at the real node count.
EXPERTS = NODE_COUNT
BANK_BYTES = 1 << 20
EXPERT_BANKS = 4
DENSE_BANKS = 8
ALIGNMENT = 1024
SHARDED = ("expert_bank", "expert_bank_scale")

PUBLISHED_CAPABILITY = (
    ROOT / "configs" / "hardware" / "abi3_capability" / f"rom_deepseek_v41_array_{NODE_COUNT}.json"
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("rom-array-v41")


@pytest.fixture(scope="module")
def graph(workspace: Path):
    return deepseek_shaped_graph(workspace, experts=EXPERTS)


def _fixture_capability(**overrides):
    kwargs = dict(
        max_context_positions=16,
        vocabulary_size=32,
        expert_count=EXPERTS,
        experts_per_token=2,
        bank_bytes=BANK_BYTES,
        expert_banks=EXPERT_BANKS,
        dense_banks=DENSE_BANKS,
    )
    kwargs.update(overrides)
    return deepseek_v41_array_rom_capability(**kwargs)


@pytest.fixture(scope="module")
def capability():
    return _fixture_capability()


def _build(graph, capability, **overrides):
    kwargs = dict(
        bank_bytes=BANK_BYTES,
        expert_banks=EXPERT_BANKS,
        dense_banks=DENSE_BANKS,
        alignment_bytes=ALIGNMENT,
    )
    kwargs.update(overrides)
    return build_deepseek_v41_array_rom_deployment(
        graph, capability=capability, **kwargs
    )


@pytest.fixture(scope="module")
def build(graph, capability):
    return _build(graph, capability)


def _descriptors(deployment, kind):
    return [
        d for d in deployment.table.descriptors() if d.descriptor_type == int(kind)
    ]


def _operators(deployment, family, sub):
    return [
        d
        for d in _descriptors(deployment, ExtendedDescriptorType.OPERATOR)
        if d.payload["engine_family"] == int(family)
        and d.payload["engine_sub"] == int(sub)
    ]


# ---------------------------------------------------------------------------
# the node count is derived, and the plan's design point is refused
# ---------------------------------------------------------------------------
def test_the_plan_design_point_is_refused_by_two_independent_rules():
    """51 devices is the plan's design point and is not expressible.

    Both refusals are arithmetic on released or declared numbers, and both are
    enforced elsewhere in the tree: ``image.node_sharded_region_source`` for the
    ownership rule, ``Capability._validate_fabric`` for the fabric partition.
    """
    assert ROUTED_EXPERTS % PLAN_NODE_COUNT == 27  # 384 = 51 x 7 + 27
    assert PLAN_NODE_COUNT % DOMAIN_SIZE == 3
    assert PLAN_NODE_COUNT not in admissible_node_counts(
        ROUTED_EXPERTS, domain_size=DOMAIN_SIZE, limit=4 * PLAN_NODE_COUNT
    )
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        v41_array_geometry(node_count=PLAN_NODE_COUNT)
    assert "do not partition into" in str(refusal.value)


def test_the_derived_node_count_is_the_smallest_admissible_above_the_target():
    admissible = admissible_node_counts(
        ROUTED_EXPERTS, domain_size=DOMAIN_SIZE, limit=4 * PLAN_NODE_COUNT
    )
    assert NODE_COUNT == expert_parallel_node_count(ROUTED_EXPERTS)
    assert NODE_COUNT in admissible
    assert NODE_COUNT >= PLAN_NODE_COUNT
    assert min(n for n in admissible if n >= PLAN_NODE_COUNT) == NODE_COUNT
    # the direction is up, and the admissible count below the target exists --
    # which is exactly why the direction has to be stated rather than implied
    below = [n for n in admissible if n < PLAN_NODE_COUNT]
    assert below and max(below) == 48
    assert ROUTED_EXPERTS % NODE_COUNT == 0
    assert NODE_COUNT % DOMAIN_SIZE == 0
    assert EXPERTS_PER_NODE == ROUTED_EXPERTS // NODE_COUNT


def test_thirty_two_nodes_is_never_admissible_on_cluster_n():
    """``CLUSTER_32`` keeps its exact cardinality; AM-R1 adds a class beside it."""
    assert 32 not in admissible_node_counts(
        ROUTED_EXPERTS, domain_size=DOMAIN_SIZE, limit=64
    )


def test_an_expert_count_that_does_not_divide_is_refused_with_the_arithmetic():
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        v41_array_geometry(node_count=NODE_COUNT, routed_experts=ROUTED_EXPERTS - 1)
    assert "do not divide into" in str(refusal.value)


# ---------------------------------------------------------------------------
# capability
# ---------------------------------------------------------------------------
def test_the_capability_is_a_cluster_n_with_an_exact_fabric_partition():
    published = deepseek_v41_array_rom_capability()
    published.validate()
    assert published.topology_class == int(TopologyClass.CLUSTER_N)
    assert published.limits["max_nodes"] == NODE_COUNT
    assert published.limits["max_expert_ids"] == ROUTED_EXPERTS
    cluster = published.fabric["cluster"]
    assert cluster["domain_size"] * cluster["domains"] == NODE_COUNT
    assert cluster["domains"] == DOMAIN_COUNT
    assert published.fabric["node_class"] == int(NodeClass.DIE)
    # the verifier binds route_group_count to the domain count, so the link
    # record has to carry the same number
    assert published.link["route_groups"] == cluster["domains"]
    assert published.link["peers_per_node"] == NODE_COUNT - 1


def test_the_capability_holds_the_cluster_chip_fixed():
    """Only the packaging varies: the chip's engines and endpoints do not."""
    from compiler.backends.hbm_sram.capability import capability_for

    cluster = capability_for("cluster-32")
    array = deepseek_v41_array_rom_capability()
    assert {k: dict(v) for k, v in array.engines.items()} == {
        k: dict(v) for k, v in cluster.engines.items()
    }
    for field in ("endpoints_per_node", "virtual_channels", "credit_bound",
                  "chunk_bytes", "retry_bound"):
        assert array.link[field] == cluster.link[field]


def test_the_published_capability_file_is_the_profile():
    if not PUBLISHED_CAPABILITY.exists():
        pytest.fail(
            f"{PUBLISHED_CAPABILITY.name} is not published; run "
            "`python3 tools/publish_abi3_capabilities.py`"
        )
    body = json.loads(PUBLISHED_CAPABILITY.read_text())
    assert Capability.from_dict(body).digest == deepseek_v41_array_rom_capability().digest
    assert PUBLISHED_CAPABILITY.read_bytes() == canonical_json(body)
    # the published stem names the derived node count, so a change in the
    # released expert count or the declared domain size fails here
    assert PUBLISHED_CAPABILITY.stem.endswith(str(NODE_COUNT))
    assert TARGET_ID.endswith(str(NODE_COUNT))


def test_the_four_new_numeric_contracts_are_the_names_their_owners_declare():
    """One definition each, confronted -- not four strings typed twice."""
    from runtime.reference.engram import (
        ENGRAM_GATE_NUMERIC_CONTRACT,
        NGRAM_HASH_NUMERIC_CONTRACT,
    )
    from runtime.reference.fp4_kv import CONTRACT as FP4_KV_CONTRACT
    from runtime.sim.engines.route import CANDIDATE_MASK_CONTRACT

    assert set(V41_NUMERIC_CONTRACTS) == {
        CANDIDATE_MASK_CONTRACT,
        ENGRAM_GATE_NUMERIC_CONTRACT,
        FP4_KV_CONTRACT,
        NGRAM_HASH_NUMERIC_CONTRACT,
    }
    declared = deepseek_v41_array_rom_capability().numeric_contracts
    assert set(V41_NUMERIC_CONTRACTS) <= set(declared)


def test_the_link_record_reproduces_the_published_cluster_32_bisection_rule():
    """The rule is stated by reproducing the one record that fixes it."""
    from compiler.backends.hbm_sram.capability import CLUSTER_32_LINK

    at_32 = cluster_n_link(node_count=32, domain_count=4)
    assert at_32["bisection_links"] == CLUSTER_32_LINK["bisection_links"]
    assert at_32["peers_per_node"] == CLUSTER_32_LINK["peers_per_node"]
    assert at_32["route_groups"] == CLUSTER_32_LINK["route_groups"]


# ---------------------------------------------------------------------------
# Engram
# ---------------------------------------------------------------------------
def test_the_engram_table_bytes_are_derived_and_equal_the_inventory():
    inventory = json.loads(
        (ROOT / "data" / "inventory" / "deepseek-v4.1-flash.json").read_text()
    )
    packed = int(inventory["lookup_table_bytes"]["engram_table_packed"])
    table = engram_table_bytes()
    assert table["total_bytes"] == packed
    assert len(table["modules"]) == 2
    assert table["scale_columns"] == math.ceil(
        table["head_dim"] / table["scale_block_elements"]
    )


def test_neither_on_device_engram_placement_is_expressible_and_both_refuse():
    """The two device placements are refused, each by its own arithmetic.

    ``replicated_hbm`` asks every node for the whole table and a node attaches
    less than that.  ``node_local_hbm`` -- plan WP-F's request -- asks for a
    row-sharded region, and the released row counts have no symmetric whole-row
    split over the derived node count, which ABI 3.0 gives no way to express
    asymmetrically (amendment A28).  Both numbers are read off the released
    profile.
    """
    table = engram_table_bytes()
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        engram_residency("replicated_hbm")
    assert "resident HBM per node" in str(refusal.value)
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        engram_residency("node_local_hbm")
    message = str(refusal.value)
    assert "not expressible on" in message
    assert "A28" in message
    priced = engram_residency(DEFAULT_ENGRAM_PLACEMENT)
    assert priced["placement"] == "host"
    assert priced["options"]["replicated_hbm"]["admitted"] is False
    assert priced["options"]["node_local_hbm"]["admitted"] is False
    # the host image is the whole table, once, and no node reserves HBM for it
    assert priced["resident_bytes_per_node"] == 0
    assert priced["host_region_bytes"] == int(table["total_bytes"])


def test_the_ceiling_the_capability_used_to_declare_was_not_a_row_granular_share():
    """Why ``ceil(total / nodes)`` was itself the defect, not a rounding taste.

    A node image of a row-sharded table is a whole number of every addressing
    row it holds.  The ceiling is not: for the released tables it is odd, so it
    is not a whole number even of the 8-byte scale row, and therefore no split
    of any shape could have produced it.  A capability number no placement can
    reach is a number nothing checks.
    """
    table = engram_table_bytes()
    ceiling = -(-int(table["total_bytes"]) // NODE_COUNT)
    scale_row = int(table["scale_columns"])
    assert ceiling % scale_row != 0
    assert ceiling % int(table["head_dim"]) != 0
    # and it is not what the capability declares any more
    assert (
        deepseek_v41_array_rom_capability().memory["hbm"]["resident_region_bytes"]
        != ceiling
    )


def test_no_admissible_node_count_divides_the_engram_row_counts():
    """Why "a node count that divides the row counts" is not an option either.

    Every admissible count is a multiple of the declared NVLink domain size and
    divides the released expert count.  One released row count is 2 mod 4, so no
    multiple of 4 -- let alone of 8 -- divides it, at any device count.
    """
    rows = [int(module["rows"]) for module in engram_table_bytes()["modules"]]
    admissible = admissible_node_counts(
        ROUTED_EXPERTS, domain_size=DOMAIN_SIZE, limit=ROUTED_EXPERTS
    )
    assert NODE_COUNT in admissible
    assert not [n for n in admissible if all(count % n == 0 for count in rows)]
    assert any(count % 4 == 2 for count in rows)


def test_the_shard_feasibility_predicate_still_admits_a_table_that_divides():
    """The refusal is a predicate, not a pin: a divisible table is admitted.

    The stand-in carries the released rows with their remainder removed, so the
    only thing that differs from the refused case is the arithmetic the rule is
    about.  Without this the refusal could be a constant that happens to say no.
    """

    class _Divisible:
        """The released Engram geometry with row counts the node count divides."""

        engram_layers = V41_FLASH_PROFILE.engram_layers
        engram_rows = tuple(
            rows - rows % NODE_COUNT for rows in V41_FLASH_PROFILE.engram_rows
        )
        engram_head_dim = V41_FLASH_PROFILE.engram_head_dim
        weight_scale_block = V41_FLASH_PROFILE.weight_scale_block
        engram_max_ngram = V41_FLASH_PROFILE.engram_max_ngram
        engram_heads = V41_FLASH_PROFILE.engram_heads

    released = engram_shard_feasibility()
    assert released["divides"] is False
    assert [m["remainder_rows"] for m in released["modules"]] == [24, 42]
    stand_in = engram_shard_feasibility(profile=_Divisible())
    assert stand_in["divides"] is True
    admitted = engram_residency("node_local_hbm", profile=_Divisible())
    # the admitted reserve is the node image -- rows a node x row bytes -- and
    # not a ceiling over the whole table
    table = engram_table_bytes(_Divisible())
    per_row = int(table["head_dim"]) + int(table["scale_columns"])
    assert admitted["resident_bytes_per_node"] == sum(
        module["rows_a_node"] * per_row for module in stand_in["modules"]
    )


def test_the_capability_prices_the_store_the_placement_uses():
    array = deepseek_v41_array_rom_capability()
    residency = engram_residency(DEFAULT_ENGRAM_PLACEMENT)
    # nothing in node-attached HBM: the double count is gone in both directions
    assert array.memory["hbm"]["resident_region_bytes"] == 0
    assert array.memory["host"]["resident_region_bytes"] == (
        residency["host_region_bytes"]
    )
    assert array.memory["host"]["resident_region_bytes"] == int(
        residency["table"]["total_bytes"]
    )
    # host memory is not this device's, so the record declares no host capacity
    assert set(array.memory["host"]) == {"resident_region_bytes"}
    # and a capability that priced both stores is refused by the builder
    both = Capability.from_dict(json.loads(canonical_json(array.to_dict()).decode()))
    both.memory["hbm"]["resident_region_bytes"] = 1 << 20
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        # The graph is never reached: the capability contradiction is refused
        # before anything is read out of it.
        build_deepseek_v41_array_rom_deployment(None, capability=both)
    assert "counts those bytes twice" in str(refusal.value)


def test_the_engram_table_marker_is_the_adapters_own_tensor_name():
    """The marker is confronted with the released tensor specs, not assumed."""
    from compiler.frontend.deepseek_v41 import (
        build_official_tensor_specs,
        load_official_config,
    )

    specs = build_official_tensor_specs(load_official_config())
    tables = [s for s in specs if s.semantic_role in ENGRAM_TABLE_ROLES]
    modules = len(engram_table_bytes()["modules"])
    assert len(tables) == modules * len(ENGRAM_TABLE_ROLES)
    assert all(ENGRAM_TABLE_TENSOR_MARKER in s.name for s in tables)
    assert set(ENGRAM_TABLE_ROLES) == {s.semantic_role for s in tables}


def test_a_row_sharded_resident_table_must_divide_into_whole_rows():
    """The released tables do not row-shard over 64 nodes, and the refusal says so.

    Every number here is read from the released profile through
    ``engram_table_bytes``: the module row counts, the FP8 row width and the
    node count the fabric rule derives.  A node's share of a row-sharded region
    has to be a whole number of table rows -- a row split across two nodes has
    no owner and one lookup becomes two reads -- and 384,006,168 rows over 64
    nodes leaves 24.
    """
    from compiler.backends.rom.common.image import (
        RegionRequest,
        ResidentHbmPolicy,
        RomImageError,
    )

    table = engram_table_bytes()
    head_dim = int(table["head_dim"])
    rows = [int(module["rows"]) for module in table["modules"]]
    assert rows and any(count % NODE_COUNT for count in rows), (
        "this test is about the case where the rows do not divide; if the "
        "released row counts ever do, it is the arithmetic that changed"
    )
    payload = rows[0] * head_dim
    request = RegionRequest.striped(
        "hbm.engram.weight",
        "layer_weight",
        "fp8_e4m3fn",
        [[("layers.1.engram.embed.weight", payload, "shard.safetensors", 0, "0" * 64)]],
        rows[0] * head_dim,
        row_bytes=head_dim,
    )
    policy = ResidentHbmPolicy(
        tensors=frozenset({"layers.1.engram.embed.weight"}),
        node_shards=NODE_COUNT,
        declared_bytes_per_node=int(table["total_bytes"]),
        alignment_bytes=head_dim,
    )
    with pytest.raises(RomImageError) as refusal:
        plan_resident_regions(
            requests=(request,),
            policy=policy,
            seen_keys=set(),
            placed={},
            first_region_id=0,
        )
    message = str(refusal.value)
    assert f"{head_dim}-byte addressing rows" in message
    assert "has no owner" in message
    # and the arithmetic the refusal is about, stated independently
    assert payload % NODE_COUNT == 0, "the bytes divide"
    assert (payload // NODE_COUNT) % head_dim != 0, "the rows do not"


def test_a_row_count_that_divides_the_node_count_shards_into_whole_rows():
    """The positive side of the same rule, so it is a rule and not a refusal.

    The shard geometry is admitted when the rows divide; what the released model
    then still needs, and what this deliberately does not fake, is an
    authenticated digest per shard -- the checkpoint lock names whole tensors,
    so a sub-tensor range has no content identity until the bytes are read.
    """
    from compiler.backends.rom.common.image import (
        RegionRequest,
        ResidentHbmPolicy,
        plan_resident_regions,
        row_sharded_region_source,
        RomImageError,
    )

    head_dim = 256
    rows = NODE_COUNT * 3
    payload = rows * head_dim
    request = RegionRequest.striped(
        "hbm.engram.weight",
        "layer_weight",
        "fp8_e4m3fn",
        [[("table.weight", payload, "shard.safetensors", 0, "ab" * 32)]],
        payload,
        row_bytes=head_dim,
    )
    regions = plan_resident_regions(
        requests=(request,),
        policy=ResidentHbmPolicy(
            tensors=frozenset({"table.weight"}),
            node_shards=NODE_COUNT,
            declared_bytes_per_node=payload,
            alignment_bytes=head_dim,
        ),
        seen_keys=set(),
        placed={},
        first_region_id=0,
    )
    assert len(regions) == 1
    region = regions[0]
    assert region.residency == "hbm"
    assert region.node_shards == NODE_COUNT
    assert len(region.shards) == NODE_COUNT
    assert {shard.bytes for shard in region.shards} == {payload // NODE_COUNT}
    assert (payload // NODE_COUNT) % head_dim == 0
    assert sum(shard.bytes for shard in region.shards) == payload
    # the object source refuses to name an unauthenticated sub-range
    with pytest.raises(RomImageError) as refusal:
        row_sharded_region_source(region, NODE_COUNT)
    assert "carries no authenticated digest" in str(refusal.value)


def test_an_engram_table_that_reached_the_rom_plan_is_refused(build):
    """The off-ROM placement is checked on the plan, not trusted to the IR."""
    _deployment, plan = build
    victim = plan.regions[0]
    member = victim.members[0]
    forged = dataclasses.replace(
        member, tensor_id=f"layers.1{ENGRAM_TABLE_TENSOR_MARKER}weight"
    )
    poisoned = dataclasses.replace(
        plan, regions=tuple(
            dataclasses.replace(r, members=(forged,) + r.members[1:])
            if r is victim
            else r
            for r in plan.regions
        )
    )
    with pytest.raises(DeepSeekV41ArrayError) as refusal:
        engram_tables_are_off_rom(poisoned)
    assert "Engram table tensor" in str(refusal.value)


# ---------------------------------------------------------------------------
# the bank plan against the released checkpoint
# ---------------------------------------------------------------------------
def _released_rom_bytes():
    """Bytes this target holds in ROM, summed from the released tensor specs.

    Decode only, which is what the first release serves: the vision tower and
    the DSpark-3 draft stack are excluded (plan section 3.5), and so are the
    Engram tables, which this target holds off ROM.
    """
    from compiler.frontend.deepseek_v41 import (
        build_official_tensor_specs,
        load_official_config,
    )

    routed = dense = engram = excluded = 0
    for spec in build_official_tensor_specs(load_official_config()):
        size = spec.size_bytes
        if spec.scope not in ("main", "global"):
            excluded += size
        elif spec.semantic_role in ENGRAM_TABLE_ROLES:
            engram += size
        elif spec.expert is not None:
            routed += size
        else:
            dense += size
    return {
        "routed": routed,
        "dense": dense,
        "engram": engram,
        "excluded": excluded,
    }


def test_the_bank_plan_holds_the_released_checkpoint_at_the_derived_node_count():
    """The declared bank geometry is checked against the checkpoint, not asserted.

    The comment in the backend states this arithmetic; this is the confrontation.
    A released expert count, dense size or node count that broke it would fail
    here rather than at the first full-scale build.
    """
    bytes_ = _released_rom_bytes()
    assert bytes_["routed"] % ROUTED_EXPERTS == 0
    per_node_experts = bytes_["routed"] // NODE_COUNT
    per_node = per_node_experts + bytes_["dense"]
    assert per_node_experts <= EXPERT_BANKS_DECLARED * BANK_BYTES_DECLARED, per_node_experts
    assert bytes_["dense"] <= DENSE_BANKS_DECLARED * BANK_BYTES_DECLARED, bytes_["dense"]
    published = deepseek_v41_array_rom_capability()
    assert per_node <= published.memory["rom"]["bytes"]
    # the Engram tables are the reason this target exists in the off-ROM form:
    # they are larger than everything else this node holds, by a lot
    assert bytes_["engram"] > 20 * per_node_experts


def test_the_replicated_dense_store_costs_more_than_one_reticle():
    """The area caveat is a fact of the partition, so it is measured here.

    Under expert-parallel ownership with the dense operands replicated, a node
    holds more ROM than an 815 mm2 reticle provides at the graded array density.
    That is the V4 array plan's WP-D2 debt, carried into V4.1 and stated rather
    than discovered at gate DS41-PHY10.
    """
    from compiler.backends.rom.deepseek_v41_array import (
        ROOFLINE_N5_ROM_DENSITY_BYTES_MM2,
        RETICLE_AREA_MM2,
    )

    bytes_ = _released_rom_bytes()
    per_node = bytes_["routed"] // NODE_COUNT + bytes_["dense"]
    reticle_capacity = RETICLE_AREA_MM2 * ROOFLINE_N5_ROM_DENSITY_BYTES_MM2
    assert per_node > reticle_capacity
    assert bytes_["dense"] > bytes_["routed"] // NODE_COUNT


# ---------------------------------------------------------------------------
# admission, topology and placement
# ---------------------------------------------------------------------------
def test_the_array_is_admitted_as_a_cluster_n(build, capability):
    deployment, _plan = build
    report = verify_deployment(deployment, capability)
    assert report.admitted, report.errors
    assert int(deployment.topology_class) == int(TopologyClass.CLUSTER_N)
    topology = _descriptors(deployment, ExtendedDescriptorType.TOPOLOGY)
    assert len(topology) == 1
    payload = topology[0].payload
    assert payload["node_count"] == NODE_COUNT
    assert payload["route_group_count"] == DOMAIN_COUNT
    assert payload["reticle_count"] == 0 and payload["tiles_per_reticle"] == 0
    assert deployment.notes["array_placement"]["node_count"] == NODE_COUNT
    assert deployment.notes["array_placement"]["dense_replication_factor"] == NODE_COUNT
    assert deployment.target_id == TARGET_ID


def test_the_notes_state_the_area_caveat_with_the_arithmetic(build):
    deployment, _plan = build
    caveat = deployment.notes["array_placement"]["iso_area_caveat"]
    assert caveat["analytical_device_count"] == PLAN_NODE_COUNT
    assert caveat["built_device_count"] == NODE_COUNT
    assert "NOT iso-area" in caveat["statement"]
    placement = deployment.notes["array_placement"]
    assert placement["replicated_dense_rom_bytes_per_node"] > 0
    assert placement["rom_bytes_array_physical"] > placement["rom_bytes_plan_unique"]


def test_every_expert_lives_on_its_owning_node_at_one_local_address(build):
    _deployment, plan = build
    sharded = [r for r in plan.regions if r.role in SHARDED]
    assert len(sharded) >= 2, [r.role for r in plan.regions]
    for region in sharded:
        per_slot = len(region.members) // region.slot_count
        assert per_slot == EXPERTS
        assert len(region.shards) == region.slot_count * NODE_COUNT
        assert region.pad_bytes == 0
        for index, shard in enumerate(region.shards):
            assert shard.coordinate.node_id == index % NODE_COUNT
            assert shard.coordinate.reticle == 0 and shard.coordinate.tile == 0
        for local in range(region.slot_count):
            places = {
                (s.coordinate.bank, s.resource_address)
                for s in region.shards[local * NODE_COUNT : (local + 1) * NODE_COUNT]
            }
            assert len(places) == 1, (region.key, local, places)


def test_sharded_regions_are_node_local_images(build):
    deployment, plan = build
    for region in plan.regions:
        source = deployment.objects[region.object_id]
        descriptor = deployment.table[region.object_id]
        assert descriptor.payload["storage_class"] == int(StorageClass.ROM)
        if region.role in SHARDED:
            assert source.kind == "node_segments"
            assert len(source.node_segments) == NODE_COUNT
            assert source.size_bytes * NODE_COUNT == region.payload_bytes
        else:
            assert source.kind == "segments"
            assert {s.coordinate.node_id for s in region.shards} == {0}


def test_the_routed_view_presents_local_experts_against_the_global_bound(build):
    deployment, _plan = build
    routed = _operators(deployment, Major.TENSOR, TensorOp.ROUTED_MATMUL)
    assert routed
    for operator in routed:
        assert operator.payload["aux_id_0"] == EXPERTS
        view = deployment.table[operator.payload["input_view_1"]].payload
        assert view["dim0"] == EXPERTS // NODE_COUNT


def test_the_expert_reduction_is_data_bearing_over_every_node(build):
    deployment, _plan = build
    reductions = [
        d
        for d in _descriptors(deployment, ExtendedDescriptorType.COMMUNICATION)
        if d.payload["collective_op"] == int(CollectiveOp.SUM)
        and d.payload["participant_scope"] == int(ParticipantScope.NODE)
    ]
    assert reductions, "no node-scoped expert all-reduce was emitted"
    for comm in reductions:
        assert comm.payload["participant_count"] == NODE_COUNT
        assert comm.payload["byte_extent"] > 0


# ---------------------------------------------------------------------------
# the two properties every ROM product keeps
# ---------------------------------------------------------------------------
def test_inverse_proof_reconstructs_the_node_sharded_images(build, workspace):
    deployment, plan = build
    report = check_rom_inverse(deployment, reader=_suite._reader(workspace))
    assert report["status"] == "pass"
    assert report["rom_bytes"] == plan.rom_bytes


def test_the_independent_schedule_checker_admits_the_cluster_n_array(
    graph, build, capability
):
    """The checker imports neither the producer nor this backend."""
    deployment, _plan = build
    report = check_rom_schedule(graph, deployment, capability)
    assert report["status"] == "pass", report["errors"][:5]
    assert report["checks"]["rom_shard_topology"] is True
    assert report["passed_check_count"] == report["check_count"]


def test_two_clean_builds_are_byte_identical(graph, capability, build):
    """DS41-P3 exit criterion: build twice, compare digests."""
    first, _ = build
    second, _ = _build(graph, capability)
    assert first.program == second.program
    assert first.table.encode() == second.table.encode()
    assert canonical_json(first.manifest()) == canonical_json(second.manifest())
    assert first.deployment_digest == second.deployment_digest


# ---------------------------------------------------------------------------
# descriptor multiset equality: the DS41-P3 exit criterion that is ours
# ---------------------------------------------------------------------------
def test_the_multiset_is_stable_across_two_clean_builds(graph, capability, build):
    first, _ = build
    second, _ = _build(graph, capability)
    report = compare_descriptor_multisets(first, second, left_label="a", right_label="b")
    assert report["equal"], report["only_in_left_by_type"]
    assert report["descriptor_count"]["a"] == len(first.table)


def test_the_multiset_isolates_the_node_sharded_image_and_nothing_else(
    graph, capability, build
):
    """The projection's control, and a measured fact about the two images.

    The same backend and the same graph, weights moved from ROM to HBM.  Every
    descriptor whose difference would be pure placement -- storage class, node,
    bank, address -- compares equal, which is what the projection is for.  What
    does NOT compare equal is the node-sharded expert image, and that is not a
    placement freedom: ``emit_rom_objects`` emits an A28 ``node_segments``
    object of ``payload_bytes / N`` only when the storage class is ROM, so the
    HBM twin of a node-sharded region is one whole-region object.  Two
    MEMORY_OBJECTs (the expert bank and its block-scale bank), the one view that
    names the sharded scale object, and the one routed contraction that reads
    them are the whole difference, and the size ratio is exactly the node count.

    This is why descriptor multiset equality against the HBM COMPARATOR is a
    real criterion rather than a tautology: the comparator has to node-shard its
    expert banks the same way, which the 32-node HBM cluster does.
    """
    rom, _ = build
    hbm, _ = _build(graph, capability, weight_storage_class=StorageClass.HBM)
    assert rom.table.encode() != hbm.table.encode()
    report = compare_descriptor_multisets(
        rom, hbm, left_label="rom", right_label="hbm_storage_class"
    )
    assert not report["equal"]
    assert report["only_in_left_by_type"] == {
        "MEMORY_OBJECT": 2,
        "OPERATOR": 1,
        "TENSOR_VIEW": 1,
    }
    assert report["only_in_right_by_type"] == report["only_in_left_by_type"]
    # 4 of the 403 descriptors, and the two objects differ by exactly N
    equal_share = report["descriptor_count"]["rom"] - report["only_in_left_total"]
    assert equal_share == len(rom.table) - 4
    plan = build[1]
    for region in plan.regions:
        if region.role not in SHARDED:
            continue
        rom_size = rom.table[region.object_id].payload["size_bytes"]
        hbm_size = hbm.table[region.object_id].payload["size_bytes"]
        assert hbm_size == region.payload_bytes
        assert rom_size * NODE_COUNT == hbm_size


def test_the_multiset_detects_a_lowering_difference(workspace, capability, build):
    """The falsifier: one more MoE layer must not compare equal."""
    rom, _ = build
    longer = deepseek_shaped_graph(
        workspace, experts=EXPERTS, sequence=("dense", "dense", "moe", "moe", "moe", "moe")
    )
    other, _ = _build(longer, capability)
    report = compare_descriptor_multisets(rom, other)
    assert not report["equal"]
    assert report["only_in_right_total"] > 0
    assert set(report["only_in_right_by_type"]) <= set(report["by_type"]["right"])


def test_the_arrays_admissible_counts_are_a_subset_of_the_comparators():
    """The two sides of the controlled comparison must be able to meet.

    Plan section 3.2 holds the node count fixed against TA-DS41-HBM.  The
    comparator is model-blind, so its admissible counts are every whole number
    of fabric domains; the array's are those that also own whole experts.  The
    array's set must therefore be contained in the comparator's, or no node
    count exists at which the pair can be built, and the array's is the
    constrained one -- which is why the comparator is the side that follows
    (``tools/build_deepseek_v41_hbm_comparator.py --nodes``).
    """
    comparator = pytest.importorskip(
        "tools.build_deepseek_v41_hbm_comparator",
        reason="WP-G's comparator tool is not in the tree yet",
    )
    theirs = set(comparator.admissible_node_counts(maximum=256))
    mine = set(admissible_node_counts(ROUTED_EXPERTS, domain_size=DOMAIN_SIZE, limit=256))
    assert mine, "no admissible array node count"
    assert mine <= theirs, sorted(mine - theirs)
    assert NODE_COUNT in theirs


#: The V4.1 cross-backend pair.  The HBM comparator is WP-G's
#: ``tools/build_hbm_sram_deployment.py --profile cluster-N --model
#: deepseek-v4.1-flash``, and the V4.1 kernel IR is
#: ``tools/build_deepseek_v4_kernel_ir_v3.py --model deepseek-v4.1-flash``;
#: neither artifact exists yet.  When both do, this is the command:
#:
#:   PYTHONPATH=. python3 -c "
#:   from compiler.ir.v3.kernel_ir import KernelGraph
#:   from compiler.backends.rom.deepseek_v41_array import (
#:       build_deepseek_v41_array_rom_deployment, compare_descriptor_multisets)
#:   from runtime.abi3.deployment import Deployment
#:   g = KernelGraph.read('build/ir-v3/deepseek-v4.1-flash/kernel_ir.v3.json')
#:   rom, _ = build_deepseek_v41_array_rom_deployment(g)
#:   hbm = Deployment.read('build/abi3/deepseek-v41-flash-hbm-cluster')
#:   print(compare_descriptor_multisets(rom, hbm))"
V41_IR = ROOT / "build" / "ir-v3" / "deepseek-v4.1-flash" / "kernel_ir.v3.json"
V41_HBM_BUNDLE = ROOT / "build" / "abi3" / "deepseek-v41-flash-hbm-cluster"


def test_descriptor_multiset_equality_with_the_v41_hbm_deployment():
    """The plan's exit criterion, on the real pair, when the pair exists."""
    if not V41_IR.exists():
        pytest.skip(
            f"{V41_IR.relative_to(ROOT)} is not built: run `make abi3-ir` once the "
            "V4.1 checkpoint lock and source contract admit a byte-pinned graph"
        )
    if not V41_HBM_BUNDLE.exists():
        pytest.skip(
            f"{V41_HBM_BUNDLE.relative_to(ROOT)} is not built (WP-G): run "
            "`PYTHONPATH=. python3 tools/build_hbm_sram_deployment.py --ir "
            f"{V41_IR.relative_to(ROOT)} --profile cluster-N --out "
            f"{V41_HBM_BUNDLE.relative_to(ROOT)}`"
        )
    from compiler.ir.v3.kernel_ir import KernelGraph
    from runtime.abi3.deployment import Deployment

    graph = KernelGraph.read(V41_IR)
    rom, _plan = build_deepseek_v41_array_rom_deployment(graph)
    hbm = Deployment.read(V41_HBM_BUNDLE)
    report = compare_descriptor_multisets(
        rom, hbm, left_label="rom_array", right_label="hbm_cluster"
    )
    assert report["equal"], (
        report["only_in_left_by_type"],
        report["only_in_right_by_type"],
    )
