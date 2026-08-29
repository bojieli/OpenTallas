"""Device-memory properties the two large deployments depend on.

A deployment's *declared* sizes are the architectural maxima -- span_tokens up
to 8192, a context up to 8192 -- while a request uses whatever it actually
asks for.  These tests pin the consequence: an object the deployment declares
costs address space, not resident memory, until a request writes to it.
"""

from __future__ import annotations

import sys

import pytest

from runtime.abi3.constants import NO_ID, Permission, StorageClass
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Descriptor, ExtendedDescriptorType
from runtime.sim.memory import MemoryObject

GIB = 1 << 30


def _object(size_bytes: int, source: ObjectSource) -> MemoryObject:
    descriptor = Descriptor(
        descriptor_id=1,
        descriptor_type=int(ExtendedDescriptorType.MEMORY_OBJECT),
        payload={
            "size_bytes": size_bytes,
            "storage_class": int(StorageClass.HBM),
            "node_id": 0,
            "alignment_log2": 12,
            "flags": 0,
            "source_kind": 0,
            "segment_count": 0,
            "digest": b"\x00" * 32,
        },
        permissions=int(Permission.READ | Permission.WRITE),
        primary_object_id=NO_ID,
    )
    return MemoryObject(1, descriptor, source, None)


def _resident_bytes() -> int:
    with open("/proc/self/statm", "r", encoding="ascii") as handle:
        return int(handle.read().split()[1]) * 4096


@pytest.mark.skipif(
    not sys.platform.startswith("linux"), reason="reads /proc/self/statm"
)
def test_a_declared_zero_object_costs_address_space_not_resident_memory():
    """An arena sized by the maximum span must not be paid for up front.

    The DeepSeek cluster deployment declares 160 GiB of activation arena,
    sized by ``span_tokens`` at its architectural maximum of 8192.  A
    104-token prefill touches a fraction of a percent of it.  Filling the
    object at construction commits every page and the run is OOM-killed on a
    188 GiB machine before it executes an instruction; a calloc-backed
    allocation hands back lazily faulted zero pages instead, and the bytes
    read are identical either way.
    """
    before = _resident_bytes()
    obj = _object(8 * GIB, ObjectSource.zeros(8 * GIB))
    grew = _resident_bytes() - before
    assert grew < GIB // 4, f"declaring 8 GiB made {grew} bytes resident"
    assert obj.read(0, 4096) == b"\x00" * 4096
    obj.write(7 * GIB, b"\x01\x02\x03\x04")
    assert obj.read(7 * GIB, 4) == b"\x01\x02\x03\x04"
    assert obj.read(0, 8) == b"\x00" * 8


def test_a_nonzero_fill_is_still_written():
    """Only a zero fill is free; a declared pattern is still materialised."""
    obj = _object(4096, ObjectSource("zero", 4096, fill=0xA5))
    assert obj.read(0, 8) == bytes([0xA5] * 8)
