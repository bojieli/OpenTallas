"""Focused guards for the governed checkpoint/restart campaign."""

from __future__ import annotations

from runtime.abi3.constants import StorageClass, TopologyClass
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.sim.checkpoint import (
    read_manifest,
    restore_device_state,
    save_device_state,
)
from runtime.sim.device import Device
from tools.run_abi3_restart_exactness import (
    _blind_checkpoint,
    _node_counter_differences,
)


def _cluster(nodes: int = 2) -> Device:
    capability = fixture_capability(TopologyClass.CLUSTER_32)
    deployment = build_fixture(
        storage_class=StorageClass.HBM,
        capability=capability,
        node_count=nodes,
    )
    return Device(deployment, capability, verify=True)


def test_node_counter_differences_include_values_and_sticky_overflow() -> None:
    baseline = [
        {
            "counters": {"dma.transfers": 2},
            "sticky_overflow": [],
            "registry_size": 121,
        },
        {
            "counters": {"tensor.additions": (1 << 64) - 1},
            "sticky_overflow": ["tensor.additions"],
            "registry_size": 121,
        },
    ]
    assert _node_counter_differences(baseline, baseline) == {}

    restarted = [dict(baseline[0]), dict(baseline[1])]
    restarted[0] = {
        **restarted[0],
        "counters": {"dma.transfers": 3},
    }
    restarted[1] = {
        **restarted[1],
        "sticky_overflow": [],
    }
    differences = _node_counter_differences(baseline, restarted)

    assert differences["0"]["counter_differences"]["dma.transfers"] == {
        "baseline": 2,
        "restarted": 3,
    }
    assert differences["1"]["sticky_overflow"] == {
        "baseline": ["tensor.additions"],
        "restarted": [],
    }


def test_blinded_cluster_checkpoint_erases_state_on_every_node(tmp_path) -> None:
    device = _cluster()
    for node_id, memory in enumerate(device.node_memories):
        for obj in memory.objects.values():
            if obj.storage_class is not StorageClass.STATE:
                continue
            buffer = obj.anonymous_buffer()
            assert buffer is not None
            buffer[:32] = node_id + 3

    source = tmp_path / "source"
    target = tmp_path / "blinded"
    save_device_state(device, device.create_session(), source)
    source_manifest = (source / "checkpoint.json").read_bytes()
    erased = _blind_checkpoint(source, target, {"STATE"})

    assert (source / "checkpoint.json").read_bytes() == source_manifest
    source_body = read_manifest(source)
    target_body = read_manifest(target)
    unchanged = next(
        entry for entry in target_body["objects"] if entry["storage_class"] != "STATE"
    )
    blinded = next(
        entry for entry in target_body["objects"] if entry["storage_class"] == "STATE"
    )
    assert (source / unchanged["file"]).stat().st_ino == (
        target / unchanged["file"]
    ).stat().st_ino
    source_blinded = next(
        entry
        for entry in source_body["objects"]
        if entry["node_id"] == blinded["node_id"]
        and entry["object_id"] == blinded["object_id"]
    )
    assert (source / source_blinded["file"]).stat().st_ino != (
        target / blinded["file"]
    ).stat().st_ino

    expected = {
        (node_id, object_id)
        for node_id, memory in enumerate(device.node_memories)
        for object_id, obj in memory.objects.items()
        if obj.storage_class is StorageClass.STATE
    }
    assert {(entry["node_id"], entry["object_id"]) for entry in erased} == expected

    restored = _cluster()
    restore_device_state(restored, target)
    for node_id, object_id in expected:
        buffer = restored.node_memories[node_id][object_id].anonymous_buffer()
        assert buffer is not None
        assert not buffer.any()
