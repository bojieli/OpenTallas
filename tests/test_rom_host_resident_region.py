"""A load-once region whose declared home is HOST memory, proved end to end.

Why this store exists, and why it is not a convenience.  A resident region is
model content the machine reads every token and never writes, held off the ROM
image so its bytes are counted once.  Amendment A28 lets one symmetric
``MEMORY_OBJECT`` name a *different* local image per node, which is what makes a
node-sharded table possible -- and it is also the rule that makes one
impossible: "every list must cover exactly the descriptor's ``size_bytes``"
(wire format section 12.19), because the descriptor states one node-local size
and one object id for every node.  A table whose row count does not divide by
the node count therefore has **no** node-sharded form: an equal whole-row split
does not exist, and the asymmetric split the arithmetic leaves is not a
capability number, it is a wire field that does not exist.
``tests/test_deepseek_v41_array_backend.py`` measures that on the released
DeepSeek-V4.1-Flash Engram tables.  What is left for such a table is one image
every node reaches over the host interface -- the placement the analytical
design point the V4.1 array stands in for was priced with -- and this module is
that placement held to every rule the HBM one is held to:

* the members tile the region and every tensor is placed exactly once;
* the object is ``READ | IMMUTABLE`` and its content digest binds the ordered
  authenticated checkpoint segments;
* the independent inverse proof reconstructs the bytes from the checkpoint;
* the host image is NOT a node's HBM reserve, and neither total absorbs the
  other; and
* a host region is never node-sharded, because host memory holds one copy.

The checkpoint is a real file on disk, so the proof reconstructs real bytes.
"""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path

import pytest

from compiler.backends.rom.common.image import (
    RESIDENT_STORAGE_CLASS,
    RegionRequest,
    ResidentHbmPolicy,
    RomImageError,
    RomLayoutPolicy,
    emit_rom_objects,
    plan_rom_image,
)
from compiler.backends.rom.common.inverse import InverseProofError, check_rom_inverse
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    Control,
    Feature,
    Major,
    NO_NODE,
    Permission,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import ObjectSource, Segment
from runtime.abi3.descriptors import ExtendedDescriptorType, Phase

ROW_BYTES = 256
SCALE_ROW_BYTES = 8
ROWS = 12
WEIGHT_BYTES = ROWS * ROW_BYTES
SCALE_BYTES = ROWS * SCALE_ROW_BYTES
DENSE_BYTES = 4096


@pytest.fixture(scope="module")
def checkpoint(tmp_path_factory) -> Path:
    """One file, three tensors: a dense ROM weight and a table with its scales."""
    root = tmp_path_factory.mktemp("host-resident")
    body = bytes((i * 37 + 11) % 256 for i in range(DENSE_BYTES + WEIGHT_BYTES + SCALE_BYTES))
    (root / "shard.bin").write_bytes(body)
    return root


def _digest(root: Path, offset: int, count: int) -> str:
    with open(root / "shard.bin", "rb") as handle:
        handle.seek(offset)
        return hashlib.sha256(handle.read(count)).hexdigest()


def _capability(*, host_bytes: int, hbm_resident: int = 0) -> Capability:
    memory = {
        "rom": {"bytes": 1 << 30, "banks": 1},
        "sram": {"bytes": 1 << 20, "banks": 8},
        "hbm": {"bytes": 1 << 30, "resident_region_bytes": hbm_resident},
    }
    if host_bytes:
        memory["host"] = {"resident_region_bytes": host_bytes}
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(f)
            for f in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_instructions": 64,
            "max_descriptors": 64,
            "max_loop_depth": 1,
            "max_loop_trip": 4,
            "max_retired_work": 1 << 20,
            "max_events": 4,
            "max_event_id": 7,
            "max_outstanding_per_queue": 4,
            "max_context_positions": 16,
            "max_expert_ids": 1,
            "max_topk": 1,
            "max_vocabulary": 8,
            "max_sessions": 1,
            "max_nodes": 1,
            "max_state_resources": 1,
        },
        numeric_contracts=(),
        engines={"tensor": {"lanes": 8, "queues": 1}},
        memory=memory,
    )
    capability.validate()
    capability.capability_id = capability.digest
    return capability


def _requests(root: Path):
    dense = RegionRequest.striped(
        "rom.r0.p000.s0",
        "layer_weight",
        "fp8_e4m3fn",
        [[("dense.weight", DENSE_BYTES, "shard.bin", 0, _digest(root, 0, DENSE_BYTES))]],
        DENSE_BYTES,
    )
    table = RegionRequest.striped(
        "host.r0.p001.s1",
        "layer_weight",
        "fp8_e4m3fn",
        [
            [
                (
                    "layers.1.engram.embed.weight",
                    WEIGHT_BYTES,
                    "shard.bin",
                    DENSE_BYTES,
                    _digest(root, DENSE_BYTES, WEIGHT_BYTES),
                )
            ]
        ],
        WEIGHT_BYTES,
        row_bytes=ROW_BYTES,
    )
    scale = RegionRequest.striped(
        "host.r0.p001.s1.scale",
        "layer_weight_scale",
        "e8m0",
        [
            [
                (
                    "layers.1.engram.embed.scale",
                    SCALE_BYTES,
                    "shard.bin",
                    DENSE_BYTES + WEIGHT_BYTES,
                    _digest(root, DENSE_BYTES + WEIGHT_BYTES, SCALE_BYTES),
                )
            ]
        ],
        SCALE_BYTES,
        row_bytes=SCALE_ROW_BYTES,
    )
    return dense, (table, scale)


def _plan(root: Path, *, residency: str = "host", node_shards: int = 1, declared: int | None = None):
    dense, resident = _requests(root)
    policy = RomLayoutPolicy(alignment_bytes=4096, row_bytes=4096, resource_bytes=1 << 20)
    return plan_rom_image(
        model_id="host-resident-fixture",
        product="fixture",
        requests=(dense,),
        policy=policy,
        resident_requests=resident,
        resident_policy=ResidentHbmPolicy(
            tensors=frozenset(
                {"layers.1.engram.embed.weight", "layers.1.engram.embed.scale"}
            ),
            node_shards=node_shards,
            node_id=NO_NODE,
            declared_bytes_per_node=(
                WEIGHT_BYTES + SCALE_BYTES if declared is None else declared
            ),
            alignment_bytes=ROW_BYTES,
            residency=residency,
        ),
    )


@pytest.fixture(scope="module")
def deployment(checkpoint: Path):
    plan = _plan(checkpoint)
    capability = _capability(host_bytes=WEIGHT_BYTES + SCALE_BYTES)
    builder = DeploymentBuilder(
        target_id="host-resident-fixture",
        model_id="host-resident-fixture",
        backend="fixture",
        capability=capability,
    )
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    emit_rom_objects(builder, plan)
    builder.notes["rom_plan"] = plan.to_dict()
    # One instruction, because a program header states a nonzero count.  This
    # fixture is about the placement record and its proof, not about a program.
    builder.emit(Major.CONTROL, Control.FENCE)
    builder.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.DECODE)
    return builder.finish(), plan


def _objects(deployment):
    return {
        d.descriptor_id: d
        for d in deployment.table.descriptors()
        if d.descriptor_type == int(ExtendedDescriptorType.MEMORY_OBJECT)
    }


# ---------------------------------------------------------------------------
# the placement
# ---------------------------------------------------------------------------
def test_a_host_resident_region_is_a_host_object_and_not_a_rom_byte(deployment):
    built, plan = deployment
    assert [r.residency for r in plan.resident_regions] == ["host", "host"]
    assert plan.rom_bytes == DENSE_BYTES
    assert plan.resident_payload_bytes == WEIGHT_BYTES + SCALE_BYTES
    assert plan.resident_padding_bytes == 0
    assert plan.host_bytes == WEIGHT_BYTES + SCALE_BYTES
    # the bytes are in no node's HBM reserve: the host holds them
    assert plan.resident_bytes_per_node == {}
    objects = _objects(built)
    for region in plan.resident_regions:
        payload = objects[region.object_id].payload
        assert payload["storage_class"] == int(StorageClass.HOST)
        assert objects[region.object_id].permissions == int(
            Permission.READ | Permission.IMMUTABLE
        )
        assert payload["size_bytes"] == region.payload_bytes
    # and the ROM region is still ROM
    rom = plan.regions[0]
    assert objects[rom.object_id].payload["storage_class"] == int(StorageClass.ROM)
    assert RESIDENT_STORAGE_CLASS["host"] == StorageClass.HOST


def test_the_plan_record_says_host_and_keeps_the_totals_apart(deployment):
    _built, plan = deployment
    body = plan.to_dict()
    assert {r["residency"] for r in body["resident_regions"]} == {"host"}
    assert body["totals"]["host_bytes"] == WEIGHT_BYTES + SCALE_BYTES
    assert body["totals"]["host_region_count"] == 2
    assert body["totals"]["resident_bytes_per_node"] == {}
    assert body["totals"]["rom_bytes"] == DENSE_BYTES


def test_the_inverse_proof_reconstructs_the_host_image_from_the_checkpoint(
    deployment, checkpoint
):
    built, plan = deployment
    proof = check_rom_inverse(built, root=checkpoint)
    assert proof["status"] == "pass"
    assert proof["bit_identical"] is True
    assert proof["host_bytes"] == WEIGHT_BYTES + SCALE_BYTES
    assert proof["host_region_count"] == 2
    assert proof["resident_payload_bytes"] == WEIGHT_BYTES + SCALE_BYTES
    assert proof["resident_bytes_per_node"] == {}
    assert proof["rom_bytes"] == DENSE_BYTES
    assert proof["placed_tensor_count"] == 3


# ---------------------------------------------------------------------------
# every rule that must still be able to fail
# ---------------------------------------------------------------------------
def test_a_host_region_may_not_be_node_sharded(checkpoint):
    """Host memory holds one copy; A28's node map hands each node its own."""
    with pytest.raises(RomImageError) as refusal:
        _plan(checkpoint, node_shards=4)
    assert "one host image every node reaches" in str(refusal.value)


def test_a_store_the_abi_has_no_class_for_is_refused(checkpoint):
    with pytest.raises(RomImageError) as refusal:
        _plan(checkpoint, residency="sram")
    assert "residency is one of ['hbm', 'host']" in str(refusal.value)


def test_a_host_image_over_the_declared_region_is_refused(checkpoint):
    with pytest.raises(RomImageError) as refusal:
        _plan(checkpoint, declared=WEIGHT_BYTES)
    message = str(refusal.value)
    assert "HOST regions need" in message and "host image" in message


def test_the_proof_refuses_a_host_region_backed_by_an_hbm_object(deployment, checkpoint):
    """The store the record names must be the store the wire names."""
    built, _plan_ = deployment
    candidate = copy.deepcopy(built)
    for descriptor in candidate.table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.MEMORY_OBJECT):
            continue
        if descriptor.payload["storage_class"] == int(StorageClass.HOST):
            descriptor.payload["storage_class"] = int(StorageClass.HBM)
            break
    with pytest.raises(InverseProofError) as refusal:
        check_rom_inverse(candidate, root=checkpoint)
    assert "resident HOST memory object" in str(refusal.value)


def test_the_proof_refuses_a_host_total_that_does_not_match_the_shards(
    deployment, checkpoint
):
    built, _plan_ = deployment
    candidate = copy.deepcopy(built)
    candidate.notes["rom_plan"]["totals"]["host_bytes"] += 64
    with pytest.raises(InverseProofError) as refusal:
        check_rom_inverse(candidate, root=checkpoint)
    assert "host image total does not match" in str(refusal.value)


def test_the_proof_refuses_a_host_region_left_in_rom(deployment, checkpoint):
    """The double count, as a refusal: a ROM object cannot back a host region."""
    built, _plan_ = deployment
    candidate = copy.deepcopy(built)
    body = candidate.notes["rom_plan"]
    body["resident_regions"][0]["object_id"] = body["regions"][0]["object_id"]
    with pytest.raises(InverseProofError) as refusal:
        check_rom_inverse(candidate, root=checkpoint)
    assert "resident HOST memory object" in str(refusal.value)


def test_the_abi_refuses_an_asymmetric_node_map_whichever_size_is_declared():
    """Why a bulk-plus-tail shard is not a capability re-derivation.

    Amendment A28: one segment list per admitted topology node, and every list
    covers exactly the descriptor's ``size_bytes``.  A tail node that holds more
    rows than the rest is refused whether the declared size is the tail's or the
    bulk's, because the wire descriptor has one node-local size.
    """
    nodes, rows = 8, 8 * 3 + 2
    bulk = (rows // nodes) * ROW_BYTES
    tail = (rows // nodes + rows % nodes) * ROW_BYTES
    assert bulk != tail
    maps = [(Segment("shard.bin", i * bulk, bulk, "ab" * 32),) for i in range(nodes - 1)]
    maps.append((Segment("shard.bin", (nodes - 1) * bulk, tail, "ab" * 32),))
    assert sum(s.bytes for m in maps for s in m) == rows * ROW_BYTES
    for size in (tail, bulk):
        with pytest.raises(Exception) as refusal:
            ObjectSource("node_segments", size, node_segments=tuple(maps))
        assert "segments cover" in str(refusal.value)


def test_an_hbm_resident_region_is_unchanged_by_the_new_store(checkpoint):
    """The HBM residency keeps its record, its reserve and its storage class."""
    plan = _plan(checkpoint, residency="hbm")
    assert [r.residency for r in plan.resident_regions] == ["hbm", "hbm"]
    assert plan.host_bytes == 0
    assert plan.resident_bytes_per_node == {NO_NODE: WEIGHT_BYTES + SCALE_BYTES}
    body = plan.to_dict()
    assert "host_bytes" not in body["totals"]
    assert "host_region_count" not in body["totals"]
    assert body["totals"]["resident_bytes_per_node"] == {
        str(NO_NODE): WEIGHT_BYTES + SCALE_BYTES
    }
