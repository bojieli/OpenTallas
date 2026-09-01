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


# ---------------------------------------------------------------------------
# Amendment A18: the three extents A13 could not state, at the released sizes
# ---------------------------------------------------------------------------
def _resolve_view(builder, view_id, loops, symbols):
    from runtime.abi3.deployment import Deployment
    from runtime.abi3.constants import TopologyClass
    from runtime.sim.memory import ViewResolver

    deployment = Deployment(
        deployment_id=1,
        generation=1,
        target_id="a18",
        model_id="a18",
        backend="test",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        capability_digest="",
        table=builder.table,
        program=b"",
        objects=dict(builder.objects),
        entrypoints=(),
        required_features=bytes(32),
    )
    return ViewResolver(deployment, None).resolve(view_id, loops, symbols)


def _a18_case(*, dims, strides, axis, unit, numerator, bias, divisor, symbol,
              term_stride):
    """One view under one symbol-bounded block loop, resolved at a binding."""
    from runtime.abi3.builder import DeploymentBuilder, DynamicTerm
    from runtime.abi3.capability import Capability
    from runtime.abi3.constants import DType, Permission, StorageClass, TopologyClass
    from runtime.abi3.deployment import ObjectSource
    from runtime.abi3.descriptors import Symbol
    from runtime.abi3.fixture import fixture_capability

    capability: Capability = fixture_capability()
    builder = DeploymentBuilder(
        target_id="a18", model_id="a18", backend="test", capability=capability
    )
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    obj = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=64,
        source=ObjectSource.zeros(64),
        permissions=int(Permission.READ | Permission.WRITE),
    )
    loop = builder.loop_control(
        lower_bound=0, upper_bound=0, step=1,
        bound_symbol=Symbol.SPAN_TOKENS, bound_divisor=divisor, max_iterations=4,
    )
    view = builder.tensor_view(
        object_id=obj,
        dtype=DType.BF16,
        dims=list(dims),
        strides=list(strides),
        dynamic=[DynamicTerm.loop(loop, term_stride)],
        extent_axis=axis,
        extent_unit=unit,
        extent_numerator=numerator,
        extent_bias=bias,
    )
    resolved = _resolve_view(
        builder, view, {loop: 0}, {int(Symbol.SPAN_TOKENS): symbol}
    )
    return resolved.dims[axis]


def test_a26_edge_mask_clamps_a_rolling_buffer_without_advancing_it():
    """One block-sized object is reused at offset zero on every loop turn."""
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.constants import DType, Permission, TopologyClass
    from runtime.abi3.deployment import ObjectSource
    from runtime.abi3.descriptors import Symbol

    from runtime.abi3.fixture import fixture_capability

    builder = DeploymentBuilder(
        target_id="a26",
        model_id="a26",
        backend="test",
        capability=fixture_capability(),
    )
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    obj = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=4 * 8 * 2,
        source=ObjectSource.zeros(4 * 8 * 2),
        permissions=int(Permission.READ | Permission.WRITE),
    )
    loop = builder.loop_control(
        lower_bound=0,
        upper_bound=3,
        step=1,
        bound_symbol=Symbol.SPAN_TOKENS,
        bound_divisor=4,
        max_iterations=3,
    )
    view = builder.tensor_view(
        object_id=obj,
        dtype=DType.BF16,
        dims=[4, 8],
        strides=[8, 1],
        edge_mask_id=loop,
        permissions=int(Permission.READ | Permission.WRITE),
    )

    resolved = _resolve_view(
        builder,
        view,
        {loop: 2},
        {int(Symbol.SPAN_TOKENS): 10},
    )
    assert resolved.dims == (2, 8)
    assert resolved.element_offset == 0


def test_a26_edge_mask_requires_its_loop_to_be_active():
    from runtime.abi3.builder import DeploymentBuilder
    from runtime.abi3.constants import DType, TopologyClass
    from runtime.abi3.descriptors import Symbol
    from runtime.abi3.fixture import fixture_capability
    from runtime.sim.memory import MemoryError_

    builder = DeploymentBuilder(
        target_id="a26",
        model_id="a26",
        backend="test",
        capability=fixture_capability(),
    )
    builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
    obj = builder.memory_object(
        storage_class=StorageClass.SRAM,
        size_bytes=64,
        source=ObjectSource.zeros(64),
        permissions=int(Permission.READ),
    )
    loop = builder.loop_control(
        lower_bound=0,
        upper_bound=2,
        step=1,
        bound_symbol=Symbol.SPAN_TOKENS,
        bound_divisor=4,
        max_iterations=2,
    )
    view = builder.tensor_view(
        object_id=obj,
        dtype=DType.BF16,
        dims=[4, 8],
        edge_mask_id=loop,
    )
    with pytest.raises(MemoryError_, match="edge-mask loop .* is not active"):
        _resolve_view(
            builder,
            view,
            {},
            {int(Symbol.SPAN_TOKENS): 7},
        )


def test_a18_states_the_attention_kv_join_at_its_released_size():
    """OI-26: the join's extent is ``span + 128``, and a clamp only shortens.

    ``main.layer00.attention_kv_view`` joins 104 current KV rows to a 128-row
    sliding window on axis 0.  The right answer is 232, the token block is 512,
    and A13 could produce neither: its clamp is a shortening of the block, and
    ``span + 128`` is not a shortening of anything.  Under A18 the view declares
    a bias of 128, its declared extent becomes ``block + bias``, and the number
    falls out.
    """
    window, block, span, width = 128, 512, 104, 512
    assert _a18_case(
        dims=(block + window, width),
        strides=(width, 1),
        axis=0, unit=0, numerator=0, bias=window,
        divisor=block, symbol=span,
        term_stride=width * block,
    ) == span + window == 232


def test_a18_states_a_compressed_layer_join_with_one_affine_function():
    """``context + 128 + context/4`` is ``floor(5 * context / 4) + 128``.

    Exactly, because ``5c/4 = c + c/4`` and ``c`` is an integer.  The numerator
    is what lets one symbol state both a count of rows and a count of groups
    derived from those same rows, which is what a compressed layer's KV view is.
    """
    window, block, span, width, ratio = 128, 512, 104, 512, 4
    expected = span + window + span // ratio
    assert _a18_case(
        dims=((ratio + 1) * block // ratio + window, width),
        strides=(width, 1),
        axis=0, unit=ratio, numerator=ratio + 1, bias=window,
        divisor=block, symbol=span,
        term_stride=width * ((ratio + 1) * block // ratio),
    ) == expected == 258


def test_a18_states_the_compressor_pool_group_axis_behind_the_batch():
    """``COMPRESS_STATE_UPDATE``'s pool: groups of four tokens, at axis 1."""
    block, span, ratio, candidates, head_dim = 512, 104, 4, 8, 128
    strides = (
        (block // ratio) * candidates * head_dim,
        candidates * head_dim,
        head_dim,
        1,
    )
    assert _a18_case(
        dims=(1, block // ratio, candidates, head_dim),
        strides=strides,
        axis=1, unit=ratio, numerator=0, bias=0,
        divisor=block, symbol=span,
        term_stride=strides[1] * (block // ratio),
    ) == span // ratio == 26
