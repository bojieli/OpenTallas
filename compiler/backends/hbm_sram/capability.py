"""Capability records for the shared HBM/SRAM accelerator chip.

TA-HBM-3.0 section 3.5 forbids a model-specific hardware switch: one RTL source
inventory, one elaboration parameter set, one netlist digest, one capability
record.  What varies between the Qwen deployment and the DeepSeek deployment is
*how many copies of that chip are wired together*, not what the chip is.

So this module builds the two profiles from one shared body and lets them
differ in exactly three places:

1. ``topology_class`` -- ``SINGLE_CHIP`` versus ``CLUSTER_32``;
2. ``limits["max_nodes"]`` -- the node count, 1 versus 32; and
3. ``link`` -- the fabric attachment of an endpoint that is present either way.

Everything else -- feature bits (including ``INTER_CHIP_ENDPOINT``, because the
chip is the same netlist whether or not a peer is attached), engine inventory,
memory sizes, numeric contracts, and every other limit -- is byte-identical.
:func:`profile_difference` is the machine-checkable statement of that claim and
is asserted by the lane's tests.

The quantitative values (SRAM bytes, HBM bytes, lane counts, link widths) are
explicitly deferred by ADR-003 section 19; they are declared here as one
named ``technology_view`` so that a later characterization replaces them in one
place and both profiles move together.
"""

from __future__ import annotations

from typing import Any, Mapping

from compiler.ir.v3.numeric import canonical_contract_id, union_contract_ids
from runtime.abi3.capability import Capability, digest_of
from runtime.abi3.constants import Feature, TopologyClass

TECHNOLOGY_VIEW = "shared-hbm-sram-chip-v3"

#: Numeric contracts the shared chip implements.  A kernel naming a contract
#: outside this tuple is a compile error: ADR-003 section 14 forbids silent
#: emulation, so an unimplemented contract must fail admission, not be
#: approximated.
#:
#: The list is *derived* from the published cross-model union rather than hand
#: written.  One chip serves both models, so its capability must declare the
#: union of both models' contracts, and a hand-maintained union goes stale the
#: moment an exporter adds an operation -- with the failure surfacing as an
#: admission error at the very end of a long build.  Two contracts with
#: different names are different operations: Qwen's RMSNorm and DeepSeek's
#: disagree by one ulp on roughly 27 % of elements, so both are declared.
#:
#: One contract is added on top of the union: TA-ABI3-OPCONV-1 amendment A7's
#: blocked execution contract, which no exporter names because it is what the
#: *backend* declares on an execution operator while the graph names the
#: sequential oracle.
EXECUTION_ONLY_CONTRACTS: tuple[str, ...] = ("bf16_bf16_fp32_blocked_rne_v1",)

#: Used only when no neutral graph has been published yet, so that the module
#: remains importable and testable on a bare checkout.
_FALLBACK_CONTRACTS: tuple[str, ...] = (
    "bf16_add_rne_v1",
    "bf16_bf16_fp32_sequential_rne_v1",
    "bf16_convert_rne_v1",
    "exact_copy_v1",
    "exact_index_gather_v1",
    "exact_index_select_v1",
)


def shared_numeric_contracts() -> tuple[str, ...]:
    """The contract union this chip declares, canonical and sorted."""
    union = set(union_contract_ids()) or set(_FALLBACK_CONTRACTS)
    union |= set(EXECUTION_ONLY_CONTRACTS)
    return tuple(sorted(canonical_contract_id(name) for name in union))


SHARED_NUMERIC_CONTRACTS: tuple[str, ...] = shared_numeric_contracts()

#: Feature bits the shared chip implements.  ``INTER_CHIP_ENDPOINT`` is present
#: in *both* profiles: the endpoint is synthesized into every chip whether or
#: not a peer is attached (TA-HBM-3.0 section 1).
SHARED_FEATURES: tuple[Feature, ...] = (
    Feature.HOST_QUEUE_ABI,
    Feature.DEPLOYMENT_DESCRIPTOR_ABI,
    Feature.DETERMINISTIC_MICROSEQUENCER,
    Feature.BF16_TENSOR,
    Feature.FP8_E4M3FN_TENSOR,
    Feature.MXFP4_E2M1_E8M0,
    Feature.TRANSACTIONAL_STATE,
    Feature.ON_DEVICE_SELECTION,
    Feature.INTER_CHIP_ENDPOINT,
    Feature.INTEGRITY_RETRY,
)

#: Per-node memory.  96 GiB of HBM holds the 16 GB Qwen image with room for
#: activations and KV, and one thirty-second of the 156 GB DeepSeek image with
#: the same margin.
HBM_BYTES_PER_NODE = 96 * (1 << 30)
SRAM_BYTES_PER_NODE = 128 * (1 << 20)
SRAM_BANKS = 32
SRAM_BANK_BYTES = SRAM_BYTES_PER_NODE // SRAM_BANKS
SRAM_PORTS_PER_BANK = 2

SHARED_LIMITS: Mapping[str, int] = {
    "max_instructions": 1 << 16,
    "max_descriptors": 1 << 16,
    # ADR-003 section 5.1: four nested loops is the minimum compliant depth and
    # is what this chip implements -- layer, row, output tile, depth tile.
    "max_loop_depth": 4,
    "max_loop_trip": 1 << 24,
    "max_retired_work": 1 << 46,
    "max_events": 4096,
    "max_outstanding_per_queue": 64,
    # 262,144 covers the 8,000-token Qwen acceptance context and the
    # 200,000-token DeepSeek acceptance context on one shared limit.
    "max_context_positions": 1 << 18,
    "max_expert_ids": 4096,
    "max_topk": 16,
    "max_vocabulary": 1 << 18,
    "max_sessions": 8,
    "max_nodes": 1,  # replaced per profile
}

SHARED_ENGINES: Mapping[str, Mapping[str, int]] = {
    "attention": {"lanes": 64, "queues": 2},
    "dma": {"lanes": 8, "queues": 4},
    "link": {"lanes": 8, "queues": 4},
    "reduction": {"lanes": 128, "queues": 2},
    "route": {"lanes": 32, "queues": 1},
    "selection": {"lanes": 8, "queues": 1},
    "state": {"lanes": 8, "queues": 1},
    "tensor": {"lanes": 256, "queues": 4},
    "vector": {"lanes": 128, "queues": 2},
}

SHARED_MEMORY: Mapping[str, Mapping[str, int]] = {
    "hbm": {"bytes": HBM_BYTES_PER_NODE, "channels": 8, "burst_bytes": 64},
    "sram": {
        "bytes": SRAM_BYTES_PER_NODE,
        "banks": SRAM_BANKS,
        "bank_bytes": SRAM_BANK_BYTES,
        "ports": SRAM_PORTS_PER_BANK,
    },
}

#: The link record.  The endpoint inventory is identical in both profiles; only
#: the attachment (how many peers, how many route groups, how much bisection)
#: changes, because that is a property of the system, not of the chip.
_LINK_COMMON: Mapping[str, int] = {
    "endpoints_per_node": 8,
    "virtual_channels": 4,
    "credit_bound": 32,
    "chunk_bytes": 1 << 16,
    "retry_bound": 3,
}

SINGLE_CHIP_LINK: Mapping[str, int] = {
    **_LINK_COMMON,
    "peers_per_node": 0,
    "route_groups": 0,
    "bisection_links": 0,
}

CLUSTER_32_LINK: Mapping[str, int] = {
    **_LINK_COMMON,
    "peers_per_node": 31,
    "route_groups": 4,
    "bisection_links": 64,
}

#: The fields that are permitted to differ between the two profiles.
PROFILE_VARIANT_FIELDS = ("topology_class", "limits.max_nodes", "link")


def _shared_capability(
    *,
    topology_class: TopologyClass,
    node_count: int,
    link: Mapping[str, int],
    numeric_contracts: tuple[str, ...] = SHARED_NUMERIC_CONTRACTS,
) -> Capability:
    limits = dict(SHARED_LIMITS)
    limits["max_nodes"] = node_count
    capability = Capability(
        capability_id="",
        topology_class=int(topology_class),
        features=tuple(int(f) for f in SHARED_FEATURES),
        limits=limits,
        numeric_contracts=tuple(numeric_contracts),
        engines={name: dict(spec) for name, spec in SHARED_ENGINES.items()},
        memory={name: dict(spec) for name, spec in SHARED_MEMORY.items()},
        link=dict(link),
        technology_view=TECHNOLOGY_VIEW,
    )
    capability.validate()
    capability.capability_id = capability.digest
    return capability


def single_chip_capability() -> Capability:
    """The Qwen deployment profile: one chip, endpoint present, no peers."""
    return _shared_capability(
        topology_class=TopologyClass.SINGLE_CHIP,
        node_count=1,
        link=SINGLE_CHIP_LINK,
    )


def cluster32_capability() -> Capability:
    """The DeepSeek deployment profile: 32 copies of the same chip."""
    return _shared_capability(
        topology_class=TopologyClass.CLUSTER_32,
        node_count=32,
        link=CLUSTER_32_LINK,
    )


#: Factories, one per named profile.  Kept private so that ``PROFILES`` can be
#: a mapping of *capabilities* rather than of callables: a consumer that writes
#: ``PROFILES["single-chip"]`` should get the record, not something it has to
#: know to call.
_FACTORIES: dict[str, Any] = {
    "single-chip": single_chip_capability,
    "cluster-32": cluster32_capability,
}

#: The shared chip's deployment profiles, by name.  These records are shared;
#: call :func:`capability_for` for one a caller may modify.
PROFILES: dict[str, Capability] = {
    name: factory() for name, factory in _FACTORIES.items()
}


def capability_for(profile: str) -> Capability:
    """Return a fresh capability record for a named profile."""
    try:
        factory = _FACTORIES[profile]
    except KeyError:
        raise KeyError(
            f"unknown capability profile {profile!r}; known profiles are "
            f"{sorted(_FACTORIES)}"
        ) from None
    return factory()


def _flatten(body: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in body.items():
        path = f"{prefix}{key}"
        if isinstance(value, Mapping):
            out.update(_flatten(value, f"{path}."))
        else:
            out[path] = value
    return out


def profile_difference() -> dict[str, Any]:
    """Report every field in which the two shared-chip profiles differ.

    The lane's release claim (TA-HBM-3.0 ``HBM-REL8``) is that one conventional
    chip admits Qwen as one node and DeepSeek as 32 identical nodes.  This
    function is the machine-checkable form of that claim: the returned
    ``differing`` set must be exactly the topology class, the node count and the
    link attachment.
    """
    one = _flatten(single_chip_capability().to_dict())
    many = _flatten(cluster32_capability().to_dict())
    keys = sorted(set(one) | set(many))
    differing = {
        key: {"single_chip": one.get(key), "cluster_32": many.get(key)}
        for key in keys
        if one.get(key) != many.get(key)
    }
    allowed = {"topology_class", "limits.max_nodes"}
    unexpected = sorted(
        key
        for key in differing
        if key not in allowed and not key.startswith("link.")
    )
    return {
        "differing": differing,
        "unexpected": unexpected,
        "identical_feature_bits": one["features"] == many["features"],
        "identical_engines": all(
            one[k] == many[k] for k in one if k.startswith("engines.")
        ),
        "identical_memory": all(
            one[k] == many[k] for k in one if k.startswith("memory.")
        ),
        "single_chip_digest": single_chip_capability().digest,
        "cluster_32_digest": cluster32_capability().digest,
    }
