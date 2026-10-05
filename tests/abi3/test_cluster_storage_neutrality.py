"""A ``CLUSTER_32`` node's weight storage class is not a topology property.

ADR-003 section 3.3 (amendment of 2026-09-03) admits an N-node
conventional-chip cluster whose nodes hold their weight shard in mask ROM as
the physical profile of TA-DS-ROM-ARRAY.  The controlled comparison that
target exists for -- ROM-array-32 against HBM-cluster-32 -- is only controlled
if nothing between the capability validator and the cycle fabric branches on
the combination ``CLUSTER_32`` plus ``StorageClass.ROM``.  This suite proves
the neutrality mechanically, on the conformance fixture, rather than asserting
it:

* the capability validator admits a 32-node cluster with ROM-resident weights
  and declares exactly 32 nodes (the ``>= 32`` loophole is closed);
* the verifier admits the ROM build of the cluster fixture exactly as it
  admits the HBM build, and the authenticated program body is identical;
* the functional device instantiates 32 node-private memories for the ROM
  build, resolves the ROM weight window on every node, runs a transaction to
  ``SUCCESS`` on both builds, and the two builds differ only in memory-traffic
  counters (the W11.1 storage-class thesis, at cluster scale);
* the cycle fabric built for the ROM cluster is the same ``ClusterFabric`` the
  HBM cluster gets, and the cluster cost table already prices ROM reads.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
    Feature,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.descriptors import ExtendedDescriptorType
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.abi3.records import split_program
from runtime.abi3.verifier import verify_deployment
from runtime.cycle.fabric import ClusterFabric, build_fabric
from runtime.cycle.machine import MachineModel, load_cost_table
from runtime.sim.device import Device
from runtime.sim.engines import load_engines

ROOT = Path(__file__).resolve().parents[2]
load_engines()
CLUSTER_COST_TABLE = ROOT / "configs" / "hardware" / "abi3_cost_cluster32_v2.json"
NODES = 32


def _cluster_capability() -> Capability:
    return fixture_capability(TopologyClass.CLUSTER_32)


def _build(storage_class: StorageClass):
    return build_fixture(
        storage_class=storage_class,
        capability=_cluster_capability(),
        node_count=NODES,
    )


# ---------------------------------------------------------------------------
# capability
# ---------------------------------------------------------------------------
def test_a_cluster_capability_declares_exactly_32_nodes() -> None:
    capability = _cluster_capability()
    assert capability.limits["max_nodes"] == NODES
    capability.validate()
    for wrong in (31, 33, 48, 64):
        loose = _cluster_capability()
        loose.limits["max_nodes"] = wrong
        with pytest.raises(ValueError, match="exactly 32"):
            loose.validate()


def test_the_cluster_capability_admits_rom_resident_weights() -> None:
    """Nothing in the validator names a storage class; the ROM build is admitted."""
    capability = _cluster_capability()
    assert Feature.INTER_CHIP_ENDPOINT in capability.features
    rom = _build(StorageClass.ROM)
    report = verify_deployment(rom, capability)
    assert report.admitted, report.errors
    weights = [
        d
        for d in rom.table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and d.payload["storage_class"] == int(StorageClass.ROM)
    ]
    assert weights, "the ROM cluster build places no ROM object"


# ---------------------------------------------------------------------------
# verifier and program identity
# ---------------------------------------------------------------------------
def test_rom_and_hbm_cluster_builds_share_one_program_body() -> None:
    hbm = _build(StorageClass.HBM)
    rom = _build(StorageClass.ROM)
    hbm_header, hbm_body = split_program(hbm.program)
    rom_header, rom_body = split_program(rom.program)
    assert hbm_body == rom_body
    assert hbm_header.instruction_count == rom_header.instruction_count
    assert int(hbm.topology_class) == int(rom.topology_class) == int(
        TopologyClass.CLUSTER_32
    )
    for deployment in (hbm, rom):
        topology = next(
            d.payload
            for d in deployment.table.descriptors()
            if d.descriptor_type == int(ExtendedDescriptorType.TOPOLOGY)
        )
        assert topology["node_count"] == NODES


# ---------------------------------------------------------------------------
# functional device
# ---------------------------------------------------------------------------
def _run(storage_class: StorageClass):
    capability = _cluster_capability()
    deployment = _build(storage_class)
    device = Device(deployment, capability, verify=True)
    assert device.node_count == NODES
    assert len(device.node_memories) == NODES
    weight_ids = [
        d.descriptor_id
        for d in deployment.table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
        and d.payload["storage_class"] == int(storage_class)
    ]
    for memory in device.node_memories:
        for oid in weight_ids:
            assert memory[oid] is not None
    policy = next(
        d.descriptor_id
        for d in deployment.table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.GENERATION_POLICY)
    )
    session = device.create_session()
    result = device.run_transaction(
        session, entrypoint_id=0, symbols={}, generation_policy_id=policy
    )
    return device, result


def test_the_rom_cluster_runs_a_transaction_to_complete() -> None:
    device, result = _run(StorageClass.ROM)
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert len(result.node_counters) == NODES


def test_the_two_cluster_builds_differ_only_in_memory_traffic() -> None:
    """The W11.1 storage-class thesis at cluster scale, on executed counters."""
    _, hbm = _run(StorageClass.HBM)
    _, rom = _run(StorageClass.ROM)
    assert hbm.status == rom.status == CompletionStatus.SUCCESS
    # Counters are sparse: a family that never fired is absent, so the two
    # builds are compared over the union with zero for an absent name.
    hbm_counters = dict(hbm.counters)
    rom_counters = dict(rom.counters)
    names = sorted(set(hbm_counters) | set(rom_counters))
    differing = [
        name
        for name in names
        if hbm_counters.get(name, 0) != rom_counters.get(name, 0)
    ]
    assert differing, "the two storage classes produced identical traffic counters"
    for name in differing:
        assert name.startswith(("rom.", "hbm.", "sram.")), (
            f"counter {name} differs between the ROM and HBM cluster builds "
            "and is not a memory-traffic counter"
        )
    assert rom_counters.get("rom.bytes_read", 0) > 0
    assert hbm_counters.get("rom.bytes_read", 0) == 0


# ---------------------------------------------------------------------------
# cycle fabric
# ---------------------------------------------------------------------------
def test_the_rom_cluster_gets_the_cluster_fabric_and_a_priced_rom() -> None:
    capability = _cluster_capability()
    table = load_cost_table(CLUSTER_COST_TABLE)
    machine = MachineModel(capability, table)
    fabric = build_fabric(machine, TopologyClass.CLUSTER_32)
    assert isinstance(fabric, ClusterFabric)
    assert fabric.endpoints() == NODES
    # The cluster table prices ROM reads already: a ROM-resident cluster node
    # needs no second table for its weight traffic.
    assert table.resolve("rom.bytes_per_cycle_per_array").value > 0
    assert table.resolve("rom.read_latency_cycles").value > 0
