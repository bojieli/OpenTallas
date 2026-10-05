"""Conformance suite for amendment AM-R1 -- the topology amendment.

AM-R1 exists because three machines the design commits to could not be
*named*.  ``TopologyClass`` had exactly ``SINGLE_CHIP``, ``CLUSTER_32`` and
``WAFER_LOGICAL_DEVICE``, and ``Capability.validate`` bound ``CLUSTER_32`` to
exactly 32 nodes, so a five-die Qwen pipeline, a four-die Qwen tensor group and
DeepSeek-V4-Pro's four wafer-class nodes had no topology class at all.  The
consequence was not a missing feature but a wrong comparison: every shipped
Qwen artifact is a ``SINGLE_CHIP`` stand-in for a multi-die machine.

This suite proves the amendment in the two directions that matter.

*it refuses what the amendment forbids*
    every negative case below is a topology the amendment names as illegal, and
    each is paired with the neighbouring legal one so a validator that refuses
    everything fails too.

*it does not move a byte of anything already shipped*
    the amendment's whole claim to landing before the re-lowering is that a
    capability which declares no fabric keeps its canonical bytes.  The digests
    are not typed in here: they are read back out of the committed evidence
    artifacts that quote them, so if the amendment moved one, no artifact would
    name it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runtime.abi3.capability import (
    FABRIC_CLUSTER_FIELDS,
    Capability,
)
from runtime.abi3.constants import (
    Feature,
    NodeClass,
    ParticipantScope,
    TopologyClass,
)
from runtime.abi3.crc import sha256
from runtime.abi3.descriptors import (
    TOPOLOGY_PAYLOAD,
    ExtendedDescriptorType,
)
from runtime.abi3.fixture import fixture_capability
from runtime.abi3.verifier import Verifier

from . import ROOT, patched_payload, probe_deployment, restamp

#: Committed artifacts that quote a capability record by path *and* digest.
#: These are the anchor for the digest-stability proof: they were written
#: before AM-R1 by tools that hash the record they read.
DIGEST_ANCHORS = (
    "results/abi3/rom_schedule_checks.json",
    "results/abi3/hbm_qwen_deployment_certificate.json",
    "results/abi3/hbm_deepseek_deployment_certificate.json",
    "results/abi3/asap7_comparison_readiness.json",
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def cluster_n_capability(
    *,
    nodes: int = 5,
    domains: int = 1,
    domain_size: int | None = None,
    inter_domain_class: int = 0,
    node_class: int = int(NodeClass.DIE),
    features: tuple[int, ...] | None = None,
    fabric: dict[str, Any] | None = None,
    topology_class: TopologyClass = TopologyClass.CLUSTER_N,
) -> Capability:
    """A ``CLUSTER_N`` capability, adjustable in exactly one way per test."""
    base = fixture_capability()
    if domain_size is None:
        domain_size = nodes // domains if domains else nodes
    if fabric is None:
        fabric = {
            "node_class": node_class,
            "cluster": {
                "domain_size": domain_size,
                "domains": domains,
                "inter_domain_class": inter_domain_class,
            },
        }
    bits = (
        features
        if features is not None
        else tuple(base.features) + (int(Feature.INTER_CHIP_ENDPOINT),)
    )
    return Capability(
        capability_id="",
        topology_class=int(topology_class),
        features=tuple(sorted(set(bits))),
        limits={**base.limits, "max_nodes": nodes},
        numeric_contracts=base.numeric_contracts,
        engines=base.engines,
        memory=base.memory,
        link=dict(base.link),
        fabric=fabric,
        technology_view="am-r1-test",
    )


def _anchored_digests() -> dict[str, set[str]]:
    """(record path -> digests some committed artifact recorded for it)."""
    found: dict[str, set[str]] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            path, sha = node.get("path"), node.get("sha256")
            if (
                isinstance(path, str)
                and isinstance(sha, str)
                and path.startswith("configs/hardware/abi3_capability/")
            ):
                found.setdefault(path, set()).add(sha)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for relative in DIGEST_ANCHORS:
        artifact = ROOT / relative
        if artifact.exists():
            walk(json.loads(artifact.read_text()))
    return found


# ---------------------------------------------------------------------------
# 1. the registry
# ---------------------------------------------------------------------------
def test_the_three_frozen_topology_classes_keep_their_values() -> None:
    """AM-R1 assigns a new value; it reassigns none."""
    assert int(TopologyClass.SINGLE_CHIP) == 0
    assert int(TopologyClass.CLUSTER_32) == 1
    assert int(TopologyClass.WAFER_LOGICAL_DEVICE) == 2
    assert int(TopologyClass.CLUSTER_N) == 3
    assert int(ParticipantScope.WAFER) == 3
    assert int(NodeClass.DIE) == 0
    assert int(NodeClass.WAFER) == 1


# ---------------------------------------------------------------------------
# 2. nothing already shipped moves
# ---------------------------------------------------------------------------
def test_shipped_capability_records_keep_the_digests_the_evidence_quotes() -> None:
    """A record that declares no fabric publishes no ``fabric`` key.

    The expected digests come from committed artifacts that quote the record
    they hashed, so this fails if AM-R1 moved a single canonical byte.
    """
    anchored = _anchored_digests()
    assert anchored, "no committed artifact quotes a capability record by digest"
    checked = 0
    for path, digests in sorted(anchored.items()):
        record = ROOT / path
        if not record.exists():
            continue
        capability = Capability.from_dict(json.loads(record.read_text()))
        assert "fabric" not in capability.to_dict(), path
        assert capability.digest in digests, (
            f"{path}: live digest {capability.digest} is quoted by no committed "
            f"artifact; recorded {sorted(digests)}"
        )
        checked += 1
    assert checked >= 4


def test_every_committed_capability_record_still_validates() -> None:
    records = sorted(
        (ROOT / "configs" / "hardware" / "abi3_capability").rglob("*.json")
    )
    assert len(records) >= 7
    for record in records:
        Capability.from_dict(json.loads(record.read_text()))


def test_cluster_32_still_means_exactly_thirty_two() -> None:
    """AM-R1 widens no existing class."""
    admitted = fixture_capability(TopologyClass.CLUSTER_32)
    admitted.validate()
    for nodes in (31, 33, 64):
        narrowed = fixture_capability(TopologyClass.CLUSTER_32)
        narrowed.limits = {**narrowed.limits, "max_nodes": nodes}
        with pytest.raises(ValueError, match="exactly 32 nodes"):
            narrowed.validate()


# ---------------------------------------------------------------------------
# 3. what CLUSTER_N admits
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "nodes,domains",
    [(4, 1), (5, 1), (8, 1), (8, 2), (16, 4)],
)
def test_cluster_n_admits_the_design_points_no_class_could_express(
    nodes: int, domains: int
) -> None:
    """Qwen x4 / x5 / x8 and a two-level 16-node machine."""
    capability = cluster_n_capability(
        nodes=nodes,
        domains=domains,
        inter_domain_class=0 if domains == 1 else 1,
    )
    capability.validate()
    assert capability.to_dict()["fabric"]["cluster"]["domains"] == domains


def test_cluster_n_admits_wafer_class_nodes_with_both_endpoint_bits() -> None:
    """DeepSeek-V4-Pro: four wafer logical devices on one fabric."""
    base = fixture_capability()
    capability = cluster_n_capability(
        nodes=4,
        domains=1,
        node_class=int(NodeClass.WAFER),
        features=tuple(base.features)
        + (int(Feature.INTER_CHIP_ENDPOINT), int(Feature.WAFER_ENDPOINT)),
    )
    capability.validate()


def test_the_array_gains_a_two_level_fabric_without_moving_its_class() -> None:
    """The 32-node DeepSeek array is 4 stages x 8 shards and stays CLUSTER_32."""
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    capability.fabric = {
        "node_class": int(NodeClass.DIE),
        "cluster": {"domain_size": 8, "domains": 4, "inter_domain_class": 1},
    }
    capability.validate()
    assert int(capability.topology_class) == int(TopologyClass.CLUSTER_32)


# ---------------------------------------------------------------------------
# 4. what CLUSTER_N refuses
# ---------------------------------------------------------------------------
def test_a_one_node_cluster_n_is_refused() -> None:
    with pytest.raises(ValueError, match="at least 2 nodes"):
        cluster_n_capability(nodes=1, domains=1).validate()


def test_a_thirty_two_node_cluster_n_is_refused() -> None:
    """Two expressible classes for one machine is the asymmetry C2 catches."""
    with pytest.raises(ValueError, match="must not declare exactly 32 nodes"):
        cluster_n_capability(nodes=32, domains=4, domain_size=8).validate()


def test_cluster_n_without_a_fabric_is_refused() -> None:
    with pytest.raises(ValueError, match="must declare fabric.cluster"):
        cluster_n_capability(nodes=5, fabric={}).validate()


def test_cluster_n_without_the_inter_chip_endpoint_bit_is_refused() -> None:
    base = fixture_capability()
    with pytest.raises(ValueError, match="must advertise bit 8"):
        cluster_n_capability(nodes=5, features=tuple(base.features)).validate()


@pytest.mark.parametrize("missing", FABRIC_CLUSTER_FIELDS)
def test_an_incomplete_fabric_is_refused(missing: str) -> None:
    capability = cluster_n_capability(nodes=8, domains=2)
    del capability.fabric["cluster"][missing]
    with pytest.raises(ValueError, match="missing"):
        capability.validate()


def test_a_fabric_that_does_not_partition_the_nodes_is_refused() -> None:
    """5 nodes are not 2 domains of 2, and a fabric that says so is refused."""
    with pytest.raises(ValueError, match=r"2 x 2 = 4 nodes"):
        cluster_n_capability(
            nodes=5, domains=2, domain_size=2, inter_domain_class=1
        ).validate()


def test_a_single_domain_fabric_may_not_price_an_inter_domain_hop() -> None:
    with pytest.raises(ValueError, match="no inter-domain hop"):
        cluster_n_capability(nodes=5, domains=1, inter_domain_class=2).validate()


def test_wafer_class_nodes_need_both_feature_bits_together() -> None:
    base = fixture_capability()
    with pytest.raises(ValueError, match="bits 8 and 9 together"):
        cluster_n_capability(
            nodes=4,
            domains=1,
            node_class=int(NodeClass.WAFER),
            features=tuple(base.features) + (int(Feature.INTER_CHIP_ENDPOINT),),
        ).validate()


def test_a_fabric_on_a_one_device_capability_is_refused() -> None:
    """A single chip has no fabric between devices to declare."""
    capability = fixture_capability(TopologyClass.SINGLE_CHIP)
    capability.fabric = {
        "cluster": {"domain_size": 1, "domains": 1, "inter_domain_class": 0}
    }
    with pytest.raises(ValueError, match="a fabric needs something to join"):
        capability.validate()


def test_an_unknown_fabric_key_is_refused() -> None:
    capability = cluster_n_capability(nodes=5)
    capability.fabric["mesh"] = {"radix": 4}
    with pytest.raises(ValueError, match="unknown keys"):
        capability.validate()


def test_the_fabric_survives_a_round_trip_through_canonical_json() -> None:
    capability = cluster_n_capability(nodes=8, domains=2, inter_domain_class=3)
    restored = Capability.from_dict(capability.to_dict())
    assert restored.digest == capability.digest
    assert restored.fabric == capability.to_dict()["fabric"]


# ---------------------------------------------------------------------------
# 5. the verifier binds the descriptor to the fabric
# ---------------------------------------------------------------------------
def _fabric_bound_deployment(route_groups: int, node_count: int = 32):
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    capability.fabric = {
        "node_class": int(NodeClass.DIE),
        "cluster": {"domain_size": 8, "domains": 4, "inter_domain_class": 1},
    }
    capability.validate()
    deployment = probe_deployment(capability)
    topology_id = deployment.table.ids_of_type(ExtendedDescriptorType.TOPOLOGY)[0]
    table = patched_payload(
        deployment.table, topology_id, TOPOLOGY_PAYLOAD, "node_count", node_count
    )
    table = patched_payload(
        table, topology_id, TOPOLOGY_PAYLOAD, "route_group_count", route_groups
    )
    deployment.table = table
    return capability, restamp(
        deployment, topology_digest=sha256(table[topology_id].encode())
    )


def test_a_descriptor_whose_route_groups_contradict_the_fabric_is_refused() -> None:
    """The capability says four domains; the descriptor says two."""
    capability, deployment = _fabric_bound_deployment(route_groups=2)
    verifier = Verifier(deployment, capability)
    verifier.verify()
    # illegal in exactly one way: the node count still matches the capability
    # and the fabric still partitions it, so only the group count is wrong.
    assert verifier.checks.get("topology_node_count_identity") is True
    assert verifier.checks.get("topology_fabric_domain_size") is True
    assert verifier.checks.get("topology_fabric_route_groups") is False
    assert any(
        "route groups" in problem and "4 domain" in problem
        for problem in verifier.errors
    ), verifier.errors


def test_the_matching_descriptor_passes_the_same_check() -> None:
    capability, deployment = _fabric_bound_deployment(route_groups=4)
    verifier = Verifier(deployment, capability)
    verifier.verify()
    assert verifier.checks.get("topology_fabric_route_groups") is True
    assert verifier.checks.get("topology_fabric_domain_size") is True


# ---------------------------------------------------------------------------
# 6. an assigned scope with no derivation is refused, not defaulted
# ---------------------------------------------------------------------------
def test_a_wafer_scoped_collective_is_refused_until_the_wire_fields_land() -> None:
    """``WAFER`` is assigned so the registry is republished once.

    Its member derivation reads the AM-R1 ``node_class`` field, which no
    admitted TOPOLOGY descriptor carries, so it must be refused rather than
    fall through to the derivation that happens to sit last in the function.
    """
    from runtime.sim.engines.link import EngineError, _member_count

    topology = {"node_count": 8, "reticle_count": 4, "tiles_per_reticle": 16}
    for scope, expected in (
        (ParticipantScope.NODE, 8),
        (ParticipantScope.RETICLE, 4),
        (ParticipantScope.TILE, 64),
    ):
        assert _member_count(topology, int(scope))[0] == expected
    with pytest.raises(EngineError, match="node_class"):
        _member_count(topology, int(ParticipantScope.WAFER))
