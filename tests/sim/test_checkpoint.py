"""The device checkpoint must be complete, exact and refuse what it cannot trust.

These tests run against the tiny ABI 3.0 conformance fixture, so they exercise
the checkpoint mechanism itself rather than a model.  The properties they pin
are the ones a restart claim rests on: every mutable byte is carried, the
restore reproduces them exactly, and a checkpoint that does not belong to this
deployment -- or that has been truncated -- is refused rather than half applied.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

import runtime.sim.checkpoint as checkpoint_module
from runtime.abi3.constants import StorageClass, TopologyClass
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.sim.checkpoint import (
    CheckpointError,
    restore_device_state,
    save_device_state,
)
from runtime.sim.device import Device


def _device(
    storage_class: StorageClass = StorageClass.HBM, *, nodes: int = 1
) -> Device:
    topology = TopologyClass.SINGLE_CHIP if nodes == 1 else TopologyClass.CLUSTER_32
    capability = fixture_capability(topology)
    return Device(
        build_fixture(
            storage_class=storage_class,
            capability=capability,
            node_count=nodes,
        ),
        capability,
        verify=True,
    )


def _dirty(device: Device, seed: int) -> dict[int, bytes]:
    """Write recognisable bytes into every writable object."""
    rng = np.random.default_rng(seed)
    written: dict[int, bytes] = {}
    for object_id, obj in sorted(device.memory.objects.items()):
        if not obj.writable:
            continue
        buffer = obj.anonymous_buffer()
        assert buffer is not None
        count = min(int(buffer.size), 512)
        buffer[:count] = rng.integers(1, 256, size=count, dtype=np.uint8)
        written[object_id] = bytes(buffer[:count])
    assert written, "the fixture must have writable objects for this to test anything"
    return written


def test_round_trip_restores_every_mutable_byte(tmp_path):
    device = _device()
    session = device.create_session()
    written = _dirty(device, seed=11)
    session.position = 7
    session.tokens = [3, 4, 5]
    session.generated = [4, 5]
    session.generation = 6
    for state in session.states.values():
        state.cursor_rows = 2
        state.generation = 3
    device._device_cycle = 909
    device.counters.add("instructions.retired", 42)
    device.node_counters[0].add("tensor.output_elements", 17)

    manifest = save_device_state(
        device, session, tmp_path / "ckpt", host_state={"position": 7}
    )
    assert manifest["objects"], "a checkpoint with no objects proves nothing"

    fresh = _device()
    restored, body = restore_device_state(fresh, tmp_path / "ckpt")

    assert body["host_state"] == {"position": 7}
    assert restored.position == 7
    assert restored.tokens == [3, 4, 5]
    assert restored.generated == [4, 5]
    assert restored.generation == 6
    assert fresh._device_cycle == 909
    assert fresh.counters.get("instructions.retired") == 42
    assert fresh.node_counters[0].get("tensor.output_elements") == 17
    assert {d: (s.cursor_rows, s.generation) for d, s in restored.states.items()} == {
        d: (s.cursor_rows, s.generation) for d, s in session.states.items()
    }
    for object_id, prefix in written.items():
        buffer = fresh.memory.objects[object_id].anonymous_buffer()
        assert bytes(buffer[: len(prefix)]) == prefix
        assert bytes(buffer) == bytes(
            device.memory.objects[object_id].anonymous_buffer()
        )


def test_restore_overwrites_state_the_fresh_process_already_has(tmp_path):
    """A restore replaces the target's bytes; it does not merge with them."""
    device = _device()
    session = device.create_session()
    _dirty(device, seed=13)
    save_device_state(device, session, tmp_path / "ckpt")

    other = _device()
    _dirty(other, seed=17)  # different bytes in the same places
    restore_device_state(other, tmp_path / "ckpt")
    for object_id, obj in device.memory.objects.items():
        buffer = obj.anonymous_buffer()
        if buffer is None:
            continue
        assert bytes(buffer) == bytes(
            other.memory.objects[object_id].anonymous_buffer()
        )


def test_a_checkpoint_from_another_deployment_is_refused(tmp_path):
    device = _device(StorageClass.HBM)
    save_device_state(device, device.create_session(), tmp_path / "ckpt")
    with pytest.raises(CheckpointError, match="deployment"):
        restore_device_state(_device(StorageClass.ROM), tmp_path / "ckpt")


def test_a_truncated_payload_is_refused(tmp_path):
    device = _device()
    _dirty(device, seed=19)
    manifest = save_device_state(device, device.create_session(), tmp_path / "ckpt")
    victim = next(entry for entry in manifest["objects"] if entry["stored_bytes"] > 0)
    blob = tmp_path / "ckpt" / victim["file"]
    blob.write_bytes(blob.read_bytes()[:-16])
    with pytest.raises(CheckpointError):
        restore_device_state(_device(), tmp_path / "ckpt")


def test_a_payload_that_does_not_match_its_digest_is_refused(tmp_path):
    device = _device()
    _dirty(device, seed=23)
    manifest = save_device_state(device, device.create_session(), tmp_path / "ckpt")
    victim = next(entry for entry in manifest["objects"] if entry["stored_bytes"] > 0)
    blob = tmp_path / "ckpt" / victim["file"]
    data = bytearray(blob.read_bytes())
    data[-1] ^= 0xFF
    blob.write_bytes(bytes(data))
    with pytest.raises(CheckpointError, match="digest"):
        restore_device_state(_device(), tmp_path / "ckpt")


def test_every_writable_object_is_serialised(tmp_path):
    """The completeness check is what makes the checkpoint's claim honest."""
    device = _device()
    manifest = save_device_state(device, device.create_session(), tmp_path / "ckpt")
    serialised = {int(entry["object_id"]) for entry in manifest["objects"]}
    writable = {
        object_id for object_id, obj in device.memory.objects.items() if obj.writable
    }
    assert writable, "a device with no writable object cannot test this"
    assert writable <= serialised


def test_cluster_round_trip_restores_every_node_arena_and_counter_set(tmp_path):
    """A cluster checkpoint is the cross product of nodes and mutable objects."""

    nodes = 32
    device = _device(nodes=nodes)
    session = device.create_session()
    expected: dict[tuple[int, int], bytes] = {}
    for node_id, memory in enumerate(device.node_memories):
        for object_id, obj in sorted(memory.objects.items()):
            if not obj.writable:
                continue
            buffer = obj.anonymous_buffer()
            assert buffer is not None
            count = min(int(buffer.size), 128)
            value = np.uint8((1 + node_id * 17 + object_id % 13) % 256)
            buffer[:count] = value
            expected[(node_id, object_id)] = bytes(buffer)
        device.node_counters[node_id].add("dma.transfers", node_id + 1)
    device.counters.add("dma.transfers", sum(range(1, nodes + 1)))
    # Pin sticky overflow too: it is architectural state, not a presentation
    # detail of the counter report.
    device.node_counters[1].add("tensor.additions", (1 << 64) - 1)
    device.node_counters[1].add("tensor.additions", 1)

    manifest = save_device_state(device, session, tmp_path / "cluster")
    found = {
        (int(entry["node_id"]), int(entry["object_id"]))
        for entry in manifest["objects"]
    }
    assert found == set(expected)
    assert len({entry["file"] for entry in manifest["objects"]}) == len(found)

    fresh = _device(nodes=nodes)
    restore_device_state(fresh, tmp_path / "cluster")

    assert fresh.counters.to_dict() == device.counters.to_dict()
    assert [counter.to_dict() for counter in fresh.node_counters] == [
        counter.to_dict() for counter in device.node_counters
    ]
    for (node_id, object_id), payload in expected.items():
        actual = fresh.node_memories[node_id][object_id].anonymous_buffer()
        assert actual is not None
        assert bytes(actual) == payload


def test_restore_refuses_a_manifest_missing_one_node_object(tmp_path):
    nodes = 32
    device = _device(nodes=nodes)
    save_device_state(device, device.create_session(), tmp_path / "cluster")
    manifest_path = tmp_path / "cluster" / "checkpoint.json"
    body = json.loads(manifest_path.read_text())
    removed = body["objects"].pop()
    manifest_path.write_text(json.dumps(body))

    with pytest.raises(CheckpointError, match="coverage differs.*missing"):
        restore_device_state(_device(nodes=nodes), tmp_path / "cluster")
    assert removed["node_id"] == nodes - 1


def test_restore_refuses_a_duplicate_node_object_entry(tmp_path):
    nodes = 32
    device = _device(nodes=nodes)
    save_device_state(device, device.create_session(), tmp_path / "cluster")
    manifest_path = tmp_path / "cluster" / "checkpoint.json"
    body = json.loads(manifest_path.read_text())
    body["objects"].append(dict(body["objects"][0]))
    manifest_path.write_text(json.dumps(body))

    with pytest.raises(CheckpointError, match="repeats node/object pair"):
        restore_device_state(_device(nodes=nodes), tmp_path / "cluster")


def test_tracked_capture_restores_sparse_ranges_without_scanning_holes(
    tmp_path, monkeypatch
):
    """The large-object path is exact using only architectural write ranges."""

    monkeypatch.setattr(checkpoint_module, "FULL_SCAN_MAX_BYTES", 0)
    device = _device()
    expected: dict[int, bytes] = {}
    for object_id, obj in device.memory.objects.items():
        if not obj.writable:
            continue
        payload = bytes([object_id % 251 + 1]) * 7
        offset = max(int(obj.size_bytes) - len(payload), 0)
        obj.write(offset, payload[: int(obj.size_bytes) - offset])
        buffer = obj.anonymous_buffer()
        assert buffer is not None
        expected[object_id] = bytes(buffer)

    manifest = save_device_state(device, device.create_session(), tmp_path / "sparse")
    assert {entry["capture_mode"] for entry in manifest["objects"]} == {
        "tracked_writes"
    }
    assert all(
        int(entry["stored_bytes"]) <= checkpoint_module.BLOCK_BYTES
        for entry in manifest["objects"]
    )

    fresh = _device()
    # A restore into an already-touched large arena must clear the target's own
    # tracked ranges before applying the source runs.
    for obj in fresh.memory.objects.values():
        if obj.writable:
            obj.write(0, b"\xff")
    restore_device_state(fresh, tmp_path / "sparse")
    for object_id, payload in expected.items():
        actual = fresh.memory.objects[object_id].anonymous_buffer()
        assert actual is not None
        assert bytes(actual) == payload


def test_cluster_checkpoint_hardlinks_identical_node_payloads(tmp_path):
    """Node-identical sparse images consume one physical payload, not N copies."""

    nodes = 32
    device = _device(nodes=nodes)
    manifest = save_device_state(device, device.create_session(), tmp_path / "cluster")
    object_id = int(manifest["objects"][0]["object_id"])
    entries = [
        entry for entry in manifest["objects"] if int(entry["object_id"]) == object_id
    ]
    assert len(entries) == nodes
    inodes = {(tmp_path / "cluster" / entry["file"]).stat().st_ino for entry in entries}
    assert len(inodes) == 1
    assert manifest["encoding"]["deduplicated_payload_files"] > 0


def test_resaving_checkpoint_does_not_mutate_old_hardlinked_payloads(tmp_path):
    """Overwriting one old link must not rewrite a different object in place."""

    device = _device()
    checkpoint = tmp_path / "checkpoint"
    first = save_device_state(device, device.create_session(), checkpoint)
    entries_by_inode: dict[int, list[dict]] = {}
    for entry in first["objects"]:
        inode = (checkpoint / entry["file"]).stat().st_ino
        entries_by_inode.setdefault(inode, []).append(entry)
    linked = next(entries for entries in entries_by_inode.values() if len(entries) > 1)
    left, right = linked[:2]

    changed = device.memory.objects[int(right["object_id"])]
    changed.write(0, b"\xa5")
    expected = {
        int(entry["object_id"]): bytes(
            device.memory.objects[int(entry["object_id"])].anonymous_buffer()
        )
        for entry in (left, right)
    }
    second = save_device_state(device, device.create_session(), checkpoint)
    second_entries = {int(entry["object_id"]): entry for entry in second["objects"]}

    left_path = checkpoint / second_entries[int(left["object_id"])]["file"]
    right_path = checkpoint / second_entries[int(right["object_id"])]["file"]
    assert left_path.stat().st_ino != right_path.stat().st_ino

    fresh = _device()
    restore_device_state(fresh, checkpoint)
    for object_id, payload in expected.items():
        restored = fresh.memory.objects[object_id].anonymous_buffer()
        assert restored is not None
        assert bytes(restored) == payload
