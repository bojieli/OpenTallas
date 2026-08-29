"""The device checkpoint must be complete, exact and refuse what it cannot trust.

These tests run against the tiny ABI 3.0 conformance fixture, so they exercise
the checkpoint mechanism itself rather than a model.  The properties they pin
are the ones a restart claim rests on: every mutable byte is carried, the
restore reproduces them exactly, and a checkpoint that does not belong to this
deployment -- or that has been truncated -- is refused rather than half applied.
"""

from __future__ import annotations

import numpy as np
import pytest

from runtime.abi3.constants import StorageClass
from runtime.abi3.fixture import build_fixture, fixture_capability
from runtime.sim.checkpoint import (
    CheckpointError,
    restore_device_state,
    save_device_state,
)
from runtime.sim.device import Device


def _device(storage_class: StorageClass = StorageClass.HBM) -> Device:
    capability = fixture_capability()
    return Device(
        build_fixture(storage_class=storage_class, capability=capability),
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
    victim = next(
        entry for entry in manifest["objects"] if entry["stored_bytes"] > 0
    )
    blob = tmp_path / "ckpt" / victim["file"]
    blob.write_bytes(blob.read_bytes()[:-16])
    with pytest.raises(CheckpointError):
        restore_device_state(_device(), tmp_path / "ckpt")


def test_a_payload_that_does_not_match_its_digest_is_refused(tmp_path):
    device = _device()
    _dirty(device, seed=23)
    manifest = save_device_state(device, device.create_session(), tmp_path / "ckpt")
    victim = next(
        entry for entry in manifest["objects"] if entry["stored_bytes"] > 0
    )
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
        object_id
        for object_id, obj in device.memory.objects.items()
        if obj.writable
    }
    assert writable, "a device with no writable object cannot test this"
    assert writable <= serialised
