"""DeepSeek-V4.1-Flash immutable-ROM lowering for a reticle-class ROM array.

This is the V4.1 sibling of :mod:`compiler.backends.rom.deepseek_v4_array` and
it exists for one experiment, stated in
``docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md`` section 3.2: hold the
model, the tile and the weight tier fixed and vary only the packaging against
TA-DS41-ROM-WAFER, and hold the node count and the fabric fixed against
TA-DS41-HBM.  Section 1 point 3 says why it is worth building a target the
analytical layer already calls the losing class: at N5 iso-area the array is
1.23x its GPU comparator where the two-wafer design is 3.00x, because both the
array and the GPU pay about 560 us of collectives per token on the same NVLink
and InfiniBand fabric.  The target exists to make that measured.

Everything structural is the V4 array's, reused rather than restated: the
:class:`~compiler.backends.rom.deepseek_v4_array._ArrayPlacer`, its layout
policy, its link plan, its uniform-node-address proof, its geometry reporter
and the cluster chip's engine lane mix are imported from that module.  What
this module decides is the four things V4.1 changes.

**1.  The node count is derived, and 51 is refused.**  The plan's design point
is ``ROM-N5-native-SRAMKV-array-hybrid-x51``: 51 devices, 41,565 mm2, the best
array in the engram-host roofline candidate.  51 is not expressible, and the
refusal is arithmetic rather than a preference:

* Whole-expert ownership needs ``n_routed_experts % node_count == 0``.  A
  node-sharded ROM region is equal owner strides -- ``node_sharded_region_source``
  refuses a region whose members per slot do not divide by the shard count, and
  the symmetric ``MEMORY_OBJECT`` descriptor carries one ``base_address`` for
  every node -- and 384 % 51 = 27.
* The declared fabric needs ``node_count == domains * domain_size``.  AM-R1
  makes ``fabric.cluster`` mandatory on ``CLUSTER_N`` and
  ``Capability._validate_fabric`` requires the partition to be exact; the
  fabric this target sits on is the TA-DS-HBM fabric, whose NVLink domain is
  ``links.nvlink5.domain_size`` = 8 in ``configs/hardware/technology.json``,
  and 51 % 8 = 3.

``expert_parallel_node_count`` therefore derives the node count from the
released expert count and the declared domain size, and it derives it *upward*:
64, the smallest admissible count at or above the design point.  The direction
is deliberate.  48 is admissible and is 5.9% less silicon than the design
point, which would make this side of a packaging comparison cheaper than the
point it is standing in for; 64 is 25.5% more.  The analytical record's own
device sweep for that design is feasible from 50 devices upward and lists no
point at 48, so 48 is also below the capacity floor the roofline priced.  When
one of two directions flatters the ROM side, take the other.

**2.  The Engram tables are off-ROM and their residence is checked, not
assumed.**  202,758,032,400 bytes of n-gram table (derived here from
``engram_num_embeddings``, ``engram_head_dim`` and the released FP8 block, and
equal to ``data/inventory/deepseek-v4.1-flash.json#lookup_table_bytes.engram_table_packed``)
is 202.8 GB the ROM does not hold, beside the 298.6 GB it does.  Plan
section 3.2 builds the ``N`` with Engram off-ROM and WP-F asks for it in
node-local HBM; the two modules together are 202.8 GB against the 180 GB a node
attaches, so *replicated* node-local HBM is refused by arithmetic and the
admissible node-local form is row-sharded across the array, 3.2 GB a node at
64.  :func:`engram_residency` prices all three placements against the declared
per-node HBM and refuses the ones that do not fit, and the chosen one is
declared in the capability as ``memory.hbm.resident_region_bytes`` and recorded
in the notes.  The off-node lookup a row-sharded table implies is NOT
priced by the analytical point this target stands in for -- that point is the
``engram-host`` candidate -- and the notes say so.

**3.  The topology is ``CLUSTER_N`` and the fabric is declared beside it.**
``CLUSTER_32`` means exactly 32 nodes and cannot be widened (four shipped
capability records name it), so the class is AM-R1's ``CLUSTER_N``; its
``fabric.cluster`` names the NVLink domain and the inter-domain class, and
``runtime.abi3.verifier._verify_cluster_fabric_binding`` binds the TOPOLOGY
descriptor's ``route_group_count`` to the declared domain count.  That is why
this module's topology emitter declares ``route_group_count = domains`` where
the V4 array declares 1.

**4.  Nothing here is a claim about area, and under this partition the claim
would be large.**  The V4 array replicates every dense operand on every node
and says so; for V4.1 that costs 9,846,779,328 bytes per node against
4,512,153,600 bytes of owned experts at 64 nodes, so the replicated store is
2.2x the sharded one and a node needs about 14.4 GB of ROM -- two reticles at
the graded array density, not one.  The per-node bytes the build actually needs
and the area they imply at both graded densities are recorded in
``notes["array_placement"]``, together with the ratio to the analytical design
point, so no reader can mistake this build for an iso-area statement.  The fix
is the V4 array plan's own WP-D2, column-sharded dense compute with activation
all-gathers, and it is not in this module.

Descriptor multiset equality with the HBM deployment of the same IR is a DS41-P3
exit criterion.  :func:`descriptor_multiset` and
:func:`compare_descriptor_multisets` implement it here, so the array side owns
one implementation both sides can run.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from compiler.backends.rom.common.image import (
    DefectRecord,
    RomImagePlan,
)
from compiler.backends.rom.common.program import (
    RomLowering,
    RomTargetPolicy,
)
from compiler.backends.rom.deepseek_v4 import (
    NUMERIC_CONTRACTS as _V4_NUMERIC_CONTRACTS,
    ROM_ROW_BYTES,
)
#: The wafer and the array are two TARGETS of one product, exactly as they are
#: for V4, so the product string has one owner: WP-E's wafer backend.  The V4
#: array imports ``PRODUCT`` from ``deepseek_v4`` for the same reason.
from compiler.backends.rom.deepseek_v41 import PRODUCT
from compiler.backends.rom.deepseek_v4_array import (
    CAPABILITY_FEATURES,
    CLUSTER_ENGINES,
    HBM_STACKS_PER_NODE,
    PHYSICAL_HBM_BYTES,
    PROGRAM_FEATURES,
    RETICLE_AREA_MM2,
    ROOFLINE_N5_ROM_DENSITY_BYTES_MM2,
    SHARDED_ROLES,
    SRAM_BYTES,
    TOKEN_BLOCK_ROWS,
    WAFER_BACKEND_USABLE_DENSITY_BYTES_MM2,
    _ArrayPlacer,
    _array_link_plan_factory,
    _prove_uniform_node_addresses,
    _route_table_digest,
    array_geometry,
    deepseek_v4_array_layout_policy,
)
from compiler.backends.hbm_sram.capability import CLUSTER_32_LINK
from compiler.frontends.v3.deepseek_v41 import V41_FLASH_PROFILE, DeepSeekV41Profile
from compiler.ir.v3.kernel_ir import KernelGraph
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    NO_ID,
    NodeClass,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import Deployment
from runtime.abi3.descriptors import ExtendedDescriptorType

BACKEND = "rom.cluster_n"

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
TECHNOLOGY_PATH = REPOSITORY_ROOT / "configs" / "hardware" / "technology.json"

#: The array design point plan section 3.2 names, read off the roofline record
#: it cites: ``results/roofline/candidates/deepseek-v4.1-flash-engram-host/
#: n5_vs_b200/analytical.json``, design
#: ``ROM-N5-native-SRAMKV-array-hybrid-x51``, ``device_count`` 51 at
#: 41,565 mm2.  It is a TARGET, not a placement: see
#: :func:`expert_parallel_node_count`.
PLAN_NODE_COUNT = 51

#: The link class the intra-domain hop rides, and the one past the domain edge.
#: Both are names in ``configs/hardware/technology.json#links``; the design
#: point's own topology record carries ``intra_link: nvlink5`` and
#: ``link: infiniband_ndr``.
INTRA_DOMAIN_LINK = "nvlink5"
INTER_DOMAIN_LINK = "infiniband_ndr"

#: Link class ids inside one deployment, in the order the topology declares
#: them: 0 is the intra-domain hop, 1 the inter-domain hop, 2 the reduction
#: class the ROM traffic semantics reserve for collectives.  The V4 array
#: declares the same three.
LINK_CLASS_INTRA_DOMAIN = 0
LINK_CLASS_INTER_DOMAIN = 1
LINK_CLASS_COUNT = 3


class DeepSeekV41ArrayError(ValueError):
    """Raised when the V4.1 graph will not fit the declared array boundary."""


# ---------------------------------------------------------------------------
# The fabric the node count has to divide into
# ---------------------------------------------------------------------------
def technology_domain_size(
    *, link: str = INTRA_DOMAIN_LINK, path: Path | None = None
) -> int:
    """Devices in one high-bandwidth domain, read from the technology record.

    The number is not this module's to choose: it is
    ``links.<link>.domain_size`` in ``configs/hardware/technology.json``, the
    same field the roofline reads to build the design point this target stands
    in for.  A missing entry is an error, never a default -- a silently
    defaulted domain size would put a fabric in the capability that the
    technology record does not describe.
    """
    source = Path(path) if path is not None else TECHNOLOGY_PATH
    try:
        body = json.loads(source.read_text())
    except OSError as exc:  # pragma: no cover - configuration is in the tree
        raise DeepSeekV41ArrayError(
            f"the technology record {source} could not be read: {exc}"
        ) from exc
    entry = (body.get("links") or {}).get(link)
    if not isinstance(entry, Mapping) or "domain_size" not in entry:
        raise DeepSeekV41ArrayError(
            f"{source}#links.{link} declares no domain_size; the array cannot "
            "declare a fabric the technology record does not describe"
        )
    field = entry["domain_size"]
    value = field.get("value") if isinstance(field, Mapping) else field
    size = int(value)
    if size < 1:
        raise DeepSeekV41ArrayError(
            f"{source}#links.{link}.domain_size is {size}; a domain holds at "
            "least one device"
        )
    return size


DOMAIN_SIZE = technology_domain_size()


def admissible_node_counts(
    routed_experts: int, *, domain_size: int, limit: int
) -> tuple[int, ...]:
    """Node counts a whole-expert ROM array on this fabric can be built at.

    Three conditions, each with a named enforcer elsewhere in the tree:

    * ``routed_experts % n == 0`` -- ``image.node_sharded_region_source`` and
      ``_ArrayPlacer.shard_bytes`` both refuse unequal owner strides.
    * ``n % domain_size == 0`` -- ``Capability._validate_fabric`` requires
      ``domains * domain_size == max_nodes`` exactly.
    * ``n != 32`` -- ``CLUSTER_N`` must not declare 32 nodes; that is
      ``CLUSTER_32``, and one machine with two expressible classes is an
      asymmetry no digest comparison sees through.
    """
    if routed_experts < 1 or domain_size < 1 or limit < 1:
        raise DeepSeekV41ArrayError(
            "admissible node counts need a positive expert count, domain size "
            f"and limit; got {routed_experts}, {domain_size}, {limit}"
        )
    return tuple(
        n
        for n in range(domain_size, limit + 1, domain_size)
        if routed_experts % n == 0 and n != 32
    )


def expert_parallel_node_count(
    routed_experts: int,
    *,
    target: int = PLAN_NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
) -> int:
    """The node count this backend builds, derived from the released geometry.

    ``target`` is the plan's design point.  When it is admissible it is
    returned unchanged.  When it is not -- which is the V4.1 case, 384 experts
    and 51 devices -- the smallest admissible count **at or above** it is
    returned, because the alternative direction makes the array cheaper than
    the point it stands in for and flatters this side of the comparison.
    """
    candidates = admissible_node_counts(
        routed_experts, domain_size=domain_size, limit=max(target, domain_size) * 4
    )
    if not candidates:
        raise DeepSeekV41ArrayError(
            f"no node count in 1..{max(target, domain_size) * 4} owns whole "
            f"experts out of {routed_experts} on a {domain_size}-device domain"
        )
    at_or_above = [n for n in candidates if n >= target]
    return at_or_above[0] if at_or_above else candidates[-1]


#: The released routed-expert geometry, read from the V4.1 profile rather than
#: typed here: ``n_routed_experts`` 384 and ``num_experts_per_tok`` 6 out of
#: ``compiler/models/deepseek-v4.1-flash/config.json``.
ROUTED_EXPERTS = V41_FLASH_PROFILE.routed_experts
EXPERTS_PER_TOKEN = V41_FLASH_PROFILE.top_k
VOCABULARY_SIZE = V41_FLASH_PROFILE.vocabulary
#: ``max_position_embeddings``: the architectural ceiling the released
#: configuration declares, which is what the program is bounded at.  The
#: mandatory workload is 200,000 tokens inside it.
MAX_CONTEXT_POSITIONS = int(
    dict(V41_FLASH_PROFILE.architecture_pins)["max_position_embeddings"]
)

NODE_COUNT = expert_parallel_node_count(ROUTED_EXPERTS)
DOMAIN_COUNT = NODE_COUNT // DOMAIN_SIZE
EXPERTS_PER_NODE = ROUTED_EXPERTS // NODE_COUNT

TARGET_ID = f"deepseek-v4.1-flash-rom-array-{NODE_COUNT}"

#: One ROM bank, and the split between the node-sharded expert store and the
#: replicated dense store.  A placement convention, exactly as the V4 array's
#: is -- the analytical study prices no bank plan -- sized from the released
#: byte counts, which ``build_official_tensor_specs`` sums as:
#:
#: * routed experts 288,777,830,400 B over 40 layers x 384 experts, so
#:   288,777,830,400 / 64 = 4,512,153,600 B (4.20 GiB) of owned experts per
#:   node: 5 banks of payload, 6 declared;
#: * dense 7,199,083,968 B of backbone plus 2,647,695,360 B of embedding and
#:   head = 9,846,779,328 B (9.17 GiB) replicated on every node: 10 banks of
#:   payload, 12 declared.
#:
#: The spare bank on each side is for the row alignment of every shard and the
#: declared zero pad of every region, which the plan walks bank by bank.  The
#: DSpark-3 draft stack (7,932,874,632 B) is NOT provisioned: the first release
#: excludes speculation (plan section 3.5), and a build that includes it is
#: refused by the per-node capacity check rather than silently housed.
BANK_BYTES = 1 << 30
EXPERT_BANKS = 6
DENSE_BANKS = 12
NODE_ROM_BYTES = (EXPERT_BANKS + DENSE_BANKS) * BANK_BYTES

#: The declared and physical per-node HBM boundary, the V4 array's own
#: five-stack die-edge rule, imported rather than restated.
HBM_BYTES = PHYSICAL_HBM_BYTES

#: The four numeric contracts AM-E10 adds for V4.1, beside the V4 set.  Each
#: name is owned by the module that implements it -- ``runtime/reference/fp4_kv.py``
#: (``CONTRACT``), ``runtime/reference/engram.py``
#: (``ENGRAM_GATE_NUMERIC_CONTRACT``, ``NGRAM_HASH_NUMERIC_CONTRACT``) and
#: ``runtime/sim/engines/route.py`` (``CANDIDATE_MASK_CONTRACT``) -- and
#: ``tests/test_deepseek_v41_array_backend.py`` confronts these four strings
#: with those four definitions rather than trusting this tuple.
V41_NUMERIC_CONTRACTS = (
    "candidate_mask_v1",
    "engram_gate_fp32_v1",
    "fp4_e2m1_s16_e4m3_to_fp8_v1",
    "ngram_hash_u32_v1",
)
NUMERIC_CONTRACTS = tuple(sorted(set(_V4_NUMERIC_CONTRACTS) | set(V41_NUMERIC_CONTRACTS)))

#: Where the Engram tables live.  ``host`` is the placement the analytical
#: design point this target stands in for was priced with (the
#: ``deepseek-v4.1-flash-engram-host`` candidate); ``node_local_hbm`` is what
#: plan WP-F asks for and is admissible only row-sharded; ``replicated_hbm``
#: is refused for V4.1 because one module's table exceeds one node's HBM.
ENGRAM_PLACEMENTS = ("node_local_hbm", "host", "replicated_hbm")
DEFAULT_ENGRAM_PLACEMENT = "node_local_hbm"

#: ``semantic_role`` of the two Engram table operands in
#: ``compiler.frontend.deepseek_v41._add_engram``, and the tensor-name marker
#: they carry (``layers.<L>.engram.embed.{weight,scale}``).  The marker is how
#: :func:`engram_tables_are_off_rom` recognises a table that reached the ROM
#: plan, and the test confronts both with ``build_official_tensor_specs``.
ENGRAM_TABLE_ROLES = ("engram.table.scale", "engram.table.weight")
ENGRAM_TABLE_TENSOR_MARKER = ".engram.embed."


# ---------------------------------------------------------------------------
# Engram residence
# ---------------------------------------------------------------------------
def engram_table_bytes(profile: DeepSeekV41Profile = V41_FLASH_PROFILE) -> dict[str, Any]:
    """Bytes of Engram n-gram table, derived from the released configuration.

    One module's table is ``engram_num_embeddings[i]`` rows of
    ``engram_head_dim`` FP8 E4M3 values plus one UE8M0 scale per released FP8
    block along the row.  Summed over ``engram_layer_ids`` this reproduces
    ``data/inventory/deepseek-v4.1-flash.json#lookup_table_bytes.engram_table_packed``
    exactly, which is the cross-check that says the derivation is the
    inventory's and not a second opinion.
    """
    head_dim = profile.engram_head_dim
    block = profile.weight_scale_block
    scale_columns = math.ceil(head_dim / block)
    per_module = []
    for layer, rows in zip(profile.engram_layers, profile.engram_rows):
        weight = rows * head_dim
        scale = rows * scale_columns
        per_module.append(
            {
                "layer": int(layer),
                "rows": int(rows),
                "weight_bytes": int(weight),
                "scale_bytes": int(scale),
                "bytes": int(weight + scale),
            }
        )
    return {
        "head_dim": int(head_dim),
        "scale_block_elements": int(block),
        "scale_columns": int(scale_columns),
        "modules": tuple(per_module),
        "largest_module_bytes": max(m["bytes"] for m in per_module),
        "total_bytes": sum(m["bytes"] for m in per_module),
        "lookup_bytes_per_token": int(
            (profile.engram_max_ngram - 1)
            * profile.engram_heads
            * len(per_module)
            * head_dim
        ),
    }


def engram_residency(
    placement: str = DEFAULT_ENGRAM_PLACEMENT,
    *,
    node_count: int = NODE_COUNT,
    hbm_bytes_per_node: int = HBM_BYTES,
    profile: DeepSeekV41Profile = V41_FLASH_PROFILE,
) -> dict[str, Any]:
    """Price the three Engram placements and refuse the ones that do not fit.

    The refusals are the point.  ``replicated_hbm`` asks every node to hold the
    whole 202.8 GB table and one node attaches 180 GB, so it is refused by
    arithmetic rather than by taste; ``node_local_hbm`` is admissible only as a
    row-sharded region, and the off-node lookup that implies is not priced by
    the analytical point this target stands in for.
    """
    if placement not in ENGRAM_PLACEMENTS:
        raise DeepSeekV41ArrayError(
            f"unknown Engram placement {placement!r}; the plan prices "
            f"{list(ENGRAM_PLACEMENTS)}"
        )
    table = engram_table_bytes(profile)
    total = int(table["total_bytes"])
    largest = int(table["largest_module_bytes"])
    # Rows do not divide evenly by the node count, so the row-sharded share is
    # the ceiling: the last node holds fewer rows and every node reserves the
    # same region, which is what a declared resident region means.
    sharded = -(-total // max(node_count, 1))
    options = {
        "node_local_hbm": {
            "resident_bytes_per_node": sharded,
            "admitted": sharded <= hbm_bytes_per_node,
            "form": "row_sharded_across_the_array",
            "rule": (
                "the table is row-sharded over the nodes; every node reserves "
                "ceil(total / nodes) and holds its own rows, load-once and "
                "read-only"
            ),
            "unpriced_consequence": (
                "a lookup whose n-gram hash lands on another node's rows is a "
                "fabric read.  The analytical design point this target stands "
                "in for is the engram-host candidate, which pays a host round "
                "trip instead, so neither cost is the other's and the cycle "
                "model (gate DS41-C2) is what settles it"
            ),
        },
        "host": {
            "resident_bytes_per_node": 0,
            "admitted": True,
            "form": "host_memory_as_deepseek_serves_it",
            "rule": (
                "the table stays in host memory and the lookup is a PCIe or "
                "RDMA round trip, which is the placement the engram-host "
                "roofline candidate prices"
            ),
        },
        "replicated_hbm": {
            "resident_bytes_per_node": total,
            "admitted": total <= hbm_bytes_per_node,
            "form": "whole_table_on_every_node",
            "rule": (
                "every node holds the whole table, which is the only form in "
                "which a lookup is guaranteed local"
            ),
        },
    }
    chosen = options[placement]
    if not chosen["admitted"]:
        raise DeepSeekV41ArrayError(
            f"Engram placement {placement!r} needs "
            f"{chosen['resident_bytes_per_node']} bytes of resident HBM per "
            f"node and a node declares {hbm_bytes_per_node}; the largest single "
            f"module is {largest} bytes over {node_count} nodes"
        )
    return {
        "placement": placement,
        "table": table,
        "resident_bytes_per_node": int(chosen["resident_bytes_per_node"]),
        "options": options,
    }


def engram_tables_are_off_rom(plan: RomImagePlan) -> None:
    """No Engram table reached the ROM plan.

    202.8 GB of n-gram table replicated on every node is what makes the array
    84 to 91 reticles instead of 51 (plan section 3.2), and the placement this
    target builds is the off-ROM one.  The V4.1 exporter is what keeps the
    table out of the weight regions; this is the backend refusing to ship the
    build if it did not, named by the tensor the checkpoint binds rather than
    by a region key, because region keys are positional and tensor ids are not.
    """
    for region in plan.regions:
        for member in region.members:
            if ENGRAM_TABLE_TENSOR_MARKER in member.tensor_id:
                raise DeepSeekV41ArrayError(
                    f"ROM region {region.key!r} places Engram table tensor "
                    f"{member.tensor_id!r}.  This target holds the Engram "
                    "tables off ROM (plan section 3.2); a ROM-resident table "
                    "is TA-DS41-ROM-WAFER-3, a different target"
                )


# ---------------------------------------------------------------------------
# Geometry and fabric
# ---------------------------------------------------------------------------
def cluster_n_link(
    *,
    node_count: int = NODE_COUNT,
    domain_count: int = DOMAIN_COUNT,
    base: Mapping[str, int] = CLUSTER_32_LINK,
) -> dict[str, int]:
    """The link record for an ``N``-node array on the TA-DS-HBM fabric.

    The endpoint inventory is the cluster chip's, unchanged -- that is a
    property of the chip, and holding it fixed is what makes this a packaging
    comparison.  Three fields are attachment, not chip, and follow the node
    count: ``peers_per_node`` is ``N - 1`` by definition, ``route_groups`` is
    the domain count the capability's fabric declares (the verifier binds the
    two together), and ``bisection_links`` is two of each node's endpoints
    crossing a symmetric cut, the rule that reproduces the published
    ``hbm_sram_cluster_32`` record's 64 links at 32 nodes exactly.  One
    published record cannot distinguish that rule from others that agree at
    32, so the field is a declaration; nothing in the lowering reads it.
    """
    record = {k: int(v) for k, v in base.items()}
    record["peers_per_node"] = int(node_count) - 1
    record["route_groups"] = int(domain_count)
    record["bisection_links"] = 2 * int(node_count)
    return record


def v41_array_geometry(
    *,
    node_count: int = NODE_COUNT,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    domain_size: int = DOMAIN_SIZE,
    routed_experts: int = ROUTED_EXPERTS,
    engram_placement: str = DEFAULT_ENGRAM_PLACEMENT,
    hbm_bytes_per_node: int = HBM_BYTES,
) -> dict[str, Any]:
    """The V4 array's geometry record, plus what V4.1 decides on top of it."""
    if node_count % domain_size:
        raise DeepSeekV41ArrayError(
            f"{node_count} nodes do not partition into {domain_size}-device "
            "domains; the declared fabric must be exact"
        )
    if routed_experts % node_count:
        raise DeepSeekV41ArrayError(
            f"{routed_experts} experts do not divide into {node_count} owners; "
            "admissible counts on this fabric are "
            f"{admissible_node_counts(routed_experts, domain_size=domain_size, limit=node_count * 4)}"
        )
    geometry = array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
    )
    engram = engram_residency(
        engram_placement,
        node_count=node_count,
        hbm_bytes_per_node=hbm_bytes_per_node,
    )
    geometry.update(
        {
            "hbm_bytes_per_node_declared": int(hbm_bytes_per_node),
            "experts_per_node": routed_experts // node_count,
            "routed_experts": int(routed_experts),
            "plan_node_count": PLAN_NODE_COUNT,
            "node_count_derivation": {
                "target": PLAN_NODE_COUNT,
                "chosen": int(node_count),
                "domain_size": int(domain_size),
                "domain_count": node_count // domain_size,
                "admissible_at_or_below_target": admissible_node_counts(
                    routed_experts, domain_size=domain_size, limit=PLAN_NODE_COUNT
                ),
                "refusals_at_the_target": {
                    "whole_expert_ownership": (
                        f"{routed_experts} % {PLAN_NODE_COUNT} = "
                        f"{routed_experts % PLAN_NODE_COUNT}"
                    ),
                    "fabric_partition": (
                        f"{PLAN_NODE_COUNT} % {domain_size} = "
                        f"{PLAN_NODE_COUNT % domain_size}"
                    ),
                },
                "direction": (
                    "upward: the admissible count below the target is cheaper "
                    "silicon than the design point and would flatter the ROM "
                    "side of a packaging comparison"
                ),
            },
            "fabric": {
                "intra_domain_link": INTRA_DOMAIN_LINK,
                "inter_domain_link": INTER_DOMAIN_LINK,
                "domain_size": int(domain_size),
                "domains": node_count // domain_size,
                "source": "configs/hardware/technology.json#links",
            },
            "engram": {
                "placement": engram["placement"],
                "table_bytes": engram["table"]["total_bytes"],
                "resident_bytes_per_node": engram["resident_bytes_per_node"],
                "lookup_bytes_per_token": engram["table"]["lookup_bytes_per_token"],
                "options": engram["options"],
            },
            "partition": "expert_parallel_consecutive_ownership_dense_replicated",
            "evidence": (
                "node count derived from the released expert count and the "
                "declared NVLink domain size, not chosen; bank geometry is a "
                "placement convention sized from the released byte counts; "
                "per-node ROM bytes are what the build needs and the implied "
                "area is stated at two graded densities in the topology notes"
            ),
        }
    )
    return geometry


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def deepseek_v41_array_rom_capability(
    *,
    max_context_positions: int = MAX_CONTEXT_POSITIONS,
    vocabulary_size: int = VOCABULARY_SIZE,
    expert_count: int = ROUTED_EXPERTS,
    experts_per_token: int = EXPERTS_PER_TOKEN,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    engram_placement: str = DEFAULT_ENGRAM_PLACEMENT,
    max_state_resources: int = 16,
) -> Capability:
    """The exact limits of the ``N``-node V4.1 ROM array.

    Topology class is AM-R1's ``CLUSTER_N`` with the fabric declared beside the
    node count; the engine lane mix and the link endpoint inventory are the
    cluster chip's, so compute is the same on both sides of the storage-class
    comparison; the limits and the numeric contracts are the V4.1 ROM
    program's; memory is per node.
    """
    geometry = v41_array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        domain_size=domain_size,
        routed_experts=expert_count,
        engram_placement=engram_placement,
    )
    domains = node_count // domain_size
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.CLUSTER_N),
        features=tuple(int(f) for f in CAPABILITY_FEATURES),
        limits={
            "max_instructions": 8192,
            "max_descriptors": 65536,
            "max_loop_depth": 4,
            "max_loop_trip": 4096,
            "max_retired_work": 1 << 26,
            "max_events": 1024,
            "max_event_id": 1023,
            "max_outstanding_per_queue": 32,
            "max_context_positions": int(max_context_positions),
            # 384 expert ids and top-6, against the V4 array's 256 and 8.  Both
            # come from the released configuration, not from this module.
            "max_expert_ids": int(expert_count),
            "max_topk": max(int(experts_per_token), 8),
            "max_vocabulary": int(vocabulary_size),
            "max_sessions": 16,
            "max_nodes": int(node_count),
            "max_state_resources": int(max_state_resources),
        },
        numeric_contracts=NUMERIC_CONTRACTS,
        engines={name: dict(spec) for name, spec in CLUSTER_ENGINES.items()},
        memory={
            "rom": {
                "bytes": geometry["node_rom_bytes"],
                "banks": expert_banks + dense_banks,
            },
            "sram": {"bytes": SRAM_BYTES, "banks": 32},
            "hbm": {
                "bytes": HBM_BYTES,
                "channels": 8,
                "burst_bytes": 64,
                "physical_stacks": HBM_STACKS_PER_NODE,
                "physical_bytes": PHYSICAL_HBM_BYTES,
                # The load-once, read-only Engram region this node reserves.
                # Zero when the tables are served from host memory.
                "resident_region_bytes": int(
                    geometry["engram"]["resident_bytes_per_node"]
                ),
            },
        },
        link=cluster_n_link(node_count=node_count, domain_count=domains),
        fabric={
            # A reticle-class die, not a wafer logical device: one node is one
            # 815 mm2 chip and has no internal fabric of its own to declare.
            "node_class": int(NodeClass.DIE),
            "cluster": {
                "domain_size": int(domain_size),
                "domains": int(domains),
                "inter_domain_class": LINK_CLASS_INTER_DOMAIN,
            },
        },
        technology_view=f"rom_array_cluster_{node_count}_physical_v1",
    )
    capability.validate()
    capability.capability_id = capability.digest
    return capability


PROFILES = {
    f"rom-deepseek-v41-array-{NODE_COUNT}": deepseek_v41_array_rom_capability,
}


# ---------------------------------------------------------------------------
# Topology
# ---------------------------------------------------------------------------
def _v41_array_topology_factory(
    *,
    node_count: int,
    domain_count: int,
    epoch: int,
    link: Mapping[str, int],
    hbm_bytes_per_node: int,
):
    """Emit the ``CLUSTER_N`` TOPOLOGY descriptor for the array.

    Two fields differ from the V4 array's emitter and both are AM-R1's doing:
    the class is ``CLUSTER_N``, and ``route_group_count`` is the capability's
    declared domain count rather than 1, because
    ``verifier._verify_cluster_fabric_binding`` binds the two and the LINK
    engine partitions its participant set by the same number.  A collective
    that names no group still addresses every node, which is what the expert
    all-reduce needs.
    """

    def emit(builder, plan: RomImagePlan) -> int:
        repair = plan.repair_map
        nodes = sorted(
            {shard.coordinate.node_id for r in plan.regions for shard in r.shards}
        )
        if nodes and (nodes[0] < 0 or nodes[-1] >= node_count):
            raise DeepSeekV41ArrayError(
                f"the region plan places shards on nodes {nodes[0]}..{nodes[-1]} "
                f"but the array declares {node_count}"
            )
        endpoints = int(link.get("endpoints_per_node", 8))
        return builder.topology(
            topology_class=TopologyClass.CLUSTER_N,
            node_count=node_count,
            reticle_count=0,
            tiles_per_reticle=0,
            local_node_id=0,
            local_reticle_id=0,
            local_tile_id=0,
            link_class_count=LINK_CLASS_COUNT,
            active_resource_count=len(repair.active_resources),
            quarantined_resource_count=len(repair.quarantine),
            hbm_bytes_per_node=hbm_bytes_per_node,
            sram_bytes_per_node=SRAM_BYTES,
            link_count=node_count * endpoints,
            route_group_count=domain_count,
            epoch=epoch,
            bisection_link_count=int(link.get("bisection_links", 0)),
            active_resource_digest=repair.active_resource_digest,
            quarantine_digest=repair.quarantine_digest,
            route_table_digest=_route_table_digest(plan),
            health_digest=repair.health_digest,
            key="topology",
        )

    return emit


# ---------------------------------------------------------------------------
# Product entry points
# ---------------------------------------------------------------------------
def deepseek_v41_array_rom_policy(
    *,
    defects: Sequence[DefectRecord] = (),
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    alignment_bytes: int = ROM_ROW_BYTES,
    sram_budget_bytes: int = SRAM_BYTES,
    epoch: int = 1,
    chunk_bytes: int = 1 << 16,
    token_block_rows: int = TOKEN_BLOCK_ROWS,
    routed_experts: int = ROUTED_EXPERTS,
    engram_placement: str = DEFAULT_ENGRAM_PLACEMENT,
    hbm_bytes_per_node: int = HBM_BYTES,
    new_token_budget_cap: int | None = None,
    target_id: str = TARGET_ID,
    notes: Mapping[str, Any] | None = None,
) -> tuple[RomTargetPolicy, _ArrayPlacer]:
    """The V4 array's policy, on ``CLUSTER_N`` at the derived node count.

    The placer, the layout policy and the link plan are the V4 array's own
    objects, imported: consecutive expert ownership, dense on node 0's dense
    banks, and the six-service critical path whose expert reduction is
    data-bearing.  Reusing them is what makes this a re-parameterisation
    rather than a second derivation.
    """
    geometry = v41_array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        domain_size=domain_size,
        routed_experts=routed_experts,
        engram_placement=engram_placement,
        hbm_bytes_per_node=hbm_bytes_per_node,
    )
    placer = _ArrayPlacer(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        alignment=alignment_bytes,
        sharded_roles=SHARDED_ROLES,
    )
    policy = RomTargetPolicy(
        product=PRODUCT,
        target_id=target_id,
        backend=BACKEND,
        topology_class=TopologyClass.CLUSTER_N,
        layout=deepseek_v4_array_layout_policy(
            placer, bank_bytes=bank_bytes, alignment_bytes=alignment_bytes
        ),
        sram_budget_bytes=sram_budget_bytes,
        token_block_rows=token_block_rows,
        tile_rows=128,
        tile_cols=128,
        tile_depth=256,
        defects=tuple(defects),
        features=PROGRAM_FEATURES,
        place_region=placer.place_region,
        emit_topology=_v41_array_topology_factory(
            node_count=node_count,
            domain_count=node_count // domain_size,
            epoch=epoch,
            link=cluster_n_link(
                node_count=node_count, domain_count=node_count // domain_size
            ),
            hbm_bytes_per_node=hbm_bytes_per_node,
        ),
        link_plan=_array_link_plan_factory(chunk_bytes=chunk_bytes),
        bank_shards=node_count,
        node_sharded_roles=SHARDED_ROLES,
        new_token_budget_cap=new_token_budget_cap,
        notes={
            "host_submission": f"one submission targets the whole {node_count}-node array",
            "partition": geometry["partition"],
            "physical_boundary": "cluster_n_reticle_class_rom_chips",
            "array_geometry": geometry,
            **dict(notes or {}),
        },
    )
    return policy, placer


def build_deepseek_v41_array_rom_deployment(
    graph: KernelGraph,
    *,
    capability: Capability | None = None,
    defects: Sequence[DefectRecord] = (),
    weight_storage_class: StorageClass = StorageClass.ROM,
    node_count: int = NODE_COUNT,
    domain_size: int = DOMAIN_SIZE,
    bank_bytes: int = BANK_BYTES,
    expert_banks: int = EXPERT_BANKS,
    dense_banks: int = DENSE_BANKS,
    alignment_bytes: int = ROM_ROW_BYTES,
    epoch: int = 1,
    token_block_rows: int = TOKEN_BLOCK_ROWS,
    deployment_id: int = 1,
    generation: int = 1,
    engram_placement: str = DEFAULT_ENGRAM_PLACEMENT,
    notes: Mapping[str, Any] | None = None,
    target_id: str = TARGET_ID,
) -> tuple[Deployment, RomImagePlan]:
    """Lower ``graph`` onto the ``N``-node DeepSeek-V4.1 ROM array."""
    capability = capability or deepseek_v41_array_rom_capability(
        node_count=node_count,
        domain_size=domain_size,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        engram_placement=engram_placement,
    )
    if capability.topology_class != int(TopologyClass.CLUSTER_N):
        raise DeepSeekV41ArrayError(
            "the V4.1 ROM array is a CLUSTER_N target; a wafer, a single chip "
            "or a CLUSTER_32 capability cannot host it"
        )
    if int(capability.limits["max_nodes"]) != node_count:
        raise DeepSeekV41ArrayError(
            f"capability admits {capability.limits['max_nodes']} nodes, build "
            f"asked for {node_count}"
        )
    hbm_bytes_per_node = int(capability.memory["hbm"]["bytes"])
    resident = int(capability.memory["hbm"].get("resident_region_bytes", 0))
    policy, _placer = deepseek_v41_array_rom_policy(
        defects=defects,
        node_count=node_count,
        domain_size=domain_size,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        alignment_bytes=alignment_bytes,
        epoch=epoch,
        token_block_rows=token_block_rows,
        routed_experts=int(capability.limits["max_expert_ids"]),
        engram_placement=engram_placement,
        hbm_bytes_per_node=hbm_bytes_per_node,
        notes=notes,
        target_id=target_id,
    )
    lowering = RomLowering(
        graph,
        capability,
        policy,
        weight_storage_class=weight_storage_class,
        deployment_id=deployment_id,
        generation=generation,
    )
    plan = lowering.plan_regions()
    _prove_uniform_node_addresses(plan, node_count)
    engram_tables_are_off_rom(plan)

    per_node_sharded = sum(
        s.bytes
        for r in plan.regions
        if r.role in SHARDED_ROLES
        for s in r.shards
        if s.coordinate.node_id == 0
    )
    dense_bytes = sum(
        r.payload_bytes + r.pad_bytes
        for r in plan.regions
        if r.role not in SHARDED_ROLES
    )
    sharded_total = sum(
        r.payload_bytes + r.pad_bytes for r in plan.regions if r.role in SHARDED_ROLES
    )
    per_node = per_node_sharded + dense_bytes
    declared = int(capability.memory["rom"]["bytes"])
    if per_node > declared:
        raise DeepSeekV41ArrayError(
            f"one node needs {per_node} ROM bytes ({per_node_sharded} sharded + "
            f"{dense_bytes} replicated dense) but the capability declares {declared}"
        )
    geometry = v41_array_geometry(
        node_count=node_count,
        bank_bytes=bank_bytes,
        expert_banks=expert_banks,
        dense_banks=dense_banks,
        domain_size=domain_size,
        routed_experts=int(capability.limits["max_expert_ids"]),
        engram_placement=engram_placement,
        hbm_bytes_per_node=hbm_bytes_per_node,
    )
    design_point_area = PLAN_NODE_COUNT * RETICLE_AREA_MM2
    node_area = {
        "at_wafer_backend_usable_density": per_node
        / WAFER_BACKEND_USABLE_DENSITY_BYTES_MM2,
        "at_roofline_n5_array_density": per_node / ROOFLINE_N5_ROM_DENSITY_BYTES_MM2,
        "reticle_area_mm2": RETICLE_AREA_MM2,
    }
    lowering.builder.notes["array_placement"] = {
        "node_count": node_count,
        "experts_per_node": int(capability.limits["max_expert_ids"]) // node_count,
        "sharded_region_count": sum(
            1 for r in plan.regions if r.role in SHARDED_ROLES
        ),
        "sharded_rom_bytes_total": sharded_total,
        "sharded_rom_bytes_per_node": per_node_sharded,
        "replicated_dense_rom_bytes_per_node": dense_bytes,
        "rom_bytes_per_node": per_node,
        "rom_bytes_array_physical": per_node * node_count,
        "rom_bytes_plan_unique": plan.rom_bytes,
        "dense_replication_factor": node_count,
        "expert_banks_used_per_node": len(
            {
                s.coordinate.bank
                for r in plan.regions
                if r.role in SHARDED_ROLES
                for s in r.shards
                if s.coordinate.node_id == 0
            }
        ),
        "dense_banks_used": len(
            {
                s.coordinate.bank
                for r in plan.regions
                if r.role not in SHARDED_ROLES
                for s in r.shards
            }
        ),
        "implied_rom_area_mm2_per_node": {
            **node_area,
            "reticles_per_node_at_roofline_n5_array_density": (
                node_area["at_roofline_n5_array_density"] / RETICLE_AREA_MM2
            ),
            "note": (
                "the replicated dense store is the price of expert-parallel "
                "ownership without column-sharded dense compute (V4 array plan "
                "WP-D2); the iso-area rule derives the comparator from these "
                f"bytes, not from {node_count} x {RETICLE_AREA_MM2} mm2"
            ),
        },
        "iso_area_caveat": {
            "analytical_design_point": (
                "DeepSeek-V4.1-Flash-engram-host/"
                "ROM-N5-native-SRAMKV-array-hybrid-x51"
            ),
            "analytical_device_count": PLAN_NODE_COUNT,
            "analytical_silicon_area_mm2": design_point_area,
            "built_device_count": node_count,
            "built_silicon_area_mm2_at_roofline_n5_array_density": (
                node_area["at_roofline_n5_array_density"] * node_count
            ),
            "area_ratio_to_design_point": (
                node_area["at_roofline_n5_array_density"] * node_count
            )
            / design_point_area,
            "statement": (
                "a deployment built against this record is NOT iso-area with "
                "the analytical design point and must not be reported as if it "
                "were: the node count is derived upward from 51 and the dense "
                "store is replicated"
            ),
        },
        "engram": geometry["engram"],
    }
    lowering.builder.notes["array_geometry"] = geometry
    deployment = lowering.build()
    footprint = deployment.notes.get("memory_footprint", {})
    session = int(footprint.get("session_bytes_in_hbm", 0))
    physical = int(capability.memory["hbm"].get("physical_bytes", hbm_bytes_per_node))
    if session + resident > physical:
        raise DeepSeekV41ArrayError(
            f"one node's session state needs {session} bytes of HBM and the "
            f"Engram resident region {resident}; together they exceed the "
            f"{physical} bytes a node physically attaches"
        )
    return deployment, plan


def lower_to_abi3(
    graph: KernelGraph,
    capability: Capability,
    *,
    topology: int | None = None,
    deployment_id: int = 1,
    generation: int = 1,
    **kwargs: Any,
) -> Deployment:
    """The shared backend entry point: one neutral graph in, one deployment out."""
    if topology is not None and int(topology) != int(TopologyClass.CLUSTER_N):
        raise DeepSeekV41ArrayError(
            f"the V4.1 ROM array is a CLUSTER_N target; topology class "
            f"{int(topology)} was requested"
        )
    deployment, _plan = build_deepseek_v41_array_rom_deployment(
        graph,
        capability=capability,
        deployment_id=deployment_id,
        generation=generation,
        **kwargs,
    )
    return deployment


# ---------------------------------------------------------------------------
# Descriptor multiset equality: the DS41-P3 exit criterion
# ---------------------------------------------------------------------------
#: Payload fields that name another descriptor in the same table.  A descriptor
#: id is a table index, so two lowerings of one graph cannot be expected to
#: agree on the number; they can be required to agree on what it *points at*,
#: which is what :func:`descriptor_signature` substitutes.  Names are taken
#: from ``runtime.abi3.descriptors.PAYLOAD_LAYOUTS``; a field not listed here
#: stays an opaque integer, which can only make the comparison stricter.
REFERENCE_FIELDS = frozenset(
    {
        "committed_object_id",
        "edge_mask_id",
        "input_view_0",
        "input_view_1",
        "input_view_2",
        "input_view_3",
        "local_object_id",
        "numeric_profile_id",
        "object_id",
        "output_view_0",
        "output_view_1",
        "predicate_id",
        "prepared_object_id",
        "reduction_numeric_id",
        "remote_object_id",
        "scale_object_id",
        "schedule_id",
        "token_ring_object_id",
        "view_descriptor_id",
    }
)

#: Fields that describe *where* a thing lives rather than what it is, per
#: descriptor type, with the reason each is excluded.  These are exactly the
#: degrees of freedom the ROM-versus-HBM comparison protocol grants ("differ
#: only in storage class, placement and topology"); everything else -- sizes,
#: dtypes, strides, extents, content digests, engine and sub-op numbers,
#: participant counts, tile shapes -- is compared.
PLACEMENT_FIELDS: Mapping[ExtendedDescriptorType, frozenset[str]] = {
    ExtendedDescriptorType.MEMORY_OBJECT: frozenset(
        {
            "storage_class",  # ROM against HBM is the comparison, not a difference
            "node_id",  # which node materialises the image
            "bank_or_tile",  # physical resource inside the node
            "base_address",  # address inside that resource
        }
    ),
    ExtendedDescriptorType.STATE: frozenset({"node_id"}),
}

#: Descriptor types whose content is the packaging itself.  A topology
#: descriptor cannot be equal across two packagings and is not evidence about
#: the program; the signature keeps the type so a missing topology still shows
#: up, and drops the payload.  Nothing else is dropped.
OPAQUE_TYPES = frozenset({ExtendedDescriptorType.TOPOLOGY})

_MAX_REFERENCE_DEPTH = 8


def _payload_items(
    descriptor: Any, *, ignore: Iterable[str]
) -> list[tuple[str, Any]]:
    skip = set(ignore)
    items = []
    for name, value in sorted(descriptor.payload.items()):
        if name in skip or name.startswith("reserved"):
            continue
        items.append((name, value))
    return items


def descriptor_signature(
    table: Any,
    descriptor_id: int,
    *,
    depth: int = 0,
    seen: tuple[int, ...] = (),
) -> tuple:
    """A placement-independent, reference-resolved signature of one descriptor.

    Descriptor ids are substituted by the signature of what they point at, so
    the result is a structural fingerprint of the computation the descriptor
    describes.  A reference cycle, or a chain deeper than
    ``_MAX_REFERENCE_DEPTH``, is recorded as such rather than silently cut:
    a comparison that quietly dropped part of the structure could pass on two
    deployments that differ inside it.
    """
    descriptor = table[descriptor_id]
    kind = ExtendedDescriptorType(descriptor.descriptor_type)
    if kind in OPAQUE_TYPES:
        return (kind.name, "opaque")
    ignore = PLACEMENT_FIELDS.get(kind, frozenset())
    fields: list[tuple[str, Any]] = []
    for name, value in _payload_items(descriptor, ignore=ignore):
        if name in REFERENCE_FIELDS and isinstance(value, int):
            if value == int(NO_ID):
                # An absent optional reference.  The sentinel is the same
                # number in both lowerings, so it compares as itself.
                fields.append((name, "no_id"))
                continue
            if descriptor_id in seen or depth >= _MAX_REFERENCE_DEPTH:
                fields.append((name, ("unresolved", value)))
                continue
            try:
                referent = table[value]
            except Exception:  # noqa: BLE001 - any table refusal is "absent"
                fields.append((name, ("absent", value)))
                continue
            if referent is None:
                fields.append((name, ("absent", value)))
                continue
            fields.append(
                (
                    name,
                    descriptor_signature(
                        table,
                        value,
                        depth=depth + 1,
                        seen=seen + (descriptor_id,),
                    ),
                )
            )
            continue
        if isinstance(value, (bytes, bytearray)):
            fields.append((name, bytes(value).hex()))
            continue
        fields.append((name, value))
    return (kind.name, int(descriptor.permissions), tuple(fields))


def descriptor_multiset(deployment: Deployment) -> Counter:
    """The multiset of placement-independent descriptor signatures."""
    table = deployment.table
    return Counter(
        descriptor_signature(table, descriptor.descriptor_id)
        for descriptor in table.descriptors()
    )


def compare_descriptor_multisets(
    left: Deployment,
    right: Deployment,
    *,
    left_label: str = "left",
    right_label: str = "right",
) -> dict[str, Any]:
    """Compare two deployments' descriptor multisets and say where they differ.

    The plan's exit criterion is equality.  This returns the whole difference
    rather than a boolean, because an unequal result is the useful one: it says
    which descriptor types disagree and by how many, which is what tells the
    two backends whether the disagreement is a placement freedom they are
    allowed or a lowering difference they are not.
    """
    a = descriptor_multiset(left)
    b = descriptor_multiset(right)
    only_left = a - b
    only_right = b - a
    def by_type(counter: Counter) -> dict[str, int]:
        totals: Counter = Counter()
        for signature, count in counter.items():
            totals[signature[0]] += count
        return dict(sorted(totals.items()))

    return {
        "equal": not only_left and not only_right,
        "labels": {"left": left_label, "right": right_label},
        "descriptor_count": {
            left_label: sum(a.values()),
            right_label: sum(b.values()),
        },
        "by_type": {left_label: by_type(a), right_label: by_type(b)},
        "only_in_left_by_type": by_type(only_left),
        "only_in_right_by_type": by_type(only_right),
        "only_in_left_total": sum(only_left.values()),
        "only_in_right_total": sum(only_right.values()),
        "examples": {
            "only_in_left": [s for s, _ in only_left.most_common(3)],
            "only_in_right": [s for s, _ in only_right.most_common(3)],
        },
    }


__all__ = [
    "BACKEND",
    "BANK_BYTES",
    "DEFAULT_ENGRAM_PLACEMENT",
    "DENSE_BANKS",
    "DOMAIN_COUNT",
    "DOMAIN_SIZE",
    "ENGRAM_PLACEMENTS",
    "EXPERTS_PER_NODE",
    "EXPERT_BANKS",
    "MAX_CONTEXT_POSITIONS",
    "NODE_COUNT",
    "NUMERIC_CONTRACTS",
    "PLAN_NODE_COUNT",
    "PRODUCT",
    "PROFILES",
    "ROUTED_EXPERTS",
    "TARGET_ID",
    "V41_NUMERIC_CONTRACTS",
    "DeepSeekV41ArrayError",
    "admissible_node_counts",
    "build_deepseek_v41_array_rom_deployment",
    "cluster_n_link",
    "compare_descriptor_multisets",
    "deepseek_v41_array_rom_capability",
    "deepseek_v41_array_rom_policy",
    "descriptor_multiset",
    "descriptor_signature",
    "engram_residency",
    "engram_table_bytes",
    "engram_tables_are_off_rom",
    "expert_parallel_node_count",
    "lower_to_abi3",
    "technology_domain_size",
    "v41_array_geometry",
]
