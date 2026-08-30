"""Device memory and tensor-view resolution for the ABI 3.0 functional device.

Two properties drive this design.

*Zero-copy weight residency.*  A Qwen deployment addresses 16 GB and a DeepSeek
deployment 156 GB of immutable weights.  Materialising either as a private image
per target, per backend, per rebuild is not possible on any realistic machine
and proves nothing: the manifest already binds each segment's SHA-256 to the
locked checkpoint.  Memory objects are therefore backed by ``numpy.memmap`` over
the authenticated files, and a tensor view resolves to a strided NumPy view of
that mapping whenever its extent lies inside one segment.

*Layout by view, not by relayout.*  ABI 2.5 pre-tiled every weight into a
private HBM image, which is why one Qwen forward step cost 924,386 flat
commands.  ABI 3.0 tensor views carry rank-6 dimensions and strides, so a tiled
read is a strided view over the original row-major bytes.  No relayout pass, no
second copy, and the bytes the engine reads are the checkpoint bytes.
"""

from __future__ import annotations

import mmap
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import numpy as np

from runtime.abi3.constants import (
    DTYPE_BITS,
    NO_ID,
    DType,
    Permission,
    StorageClass,
)
from runtime.abi3.crc import sha256_hex
from runtime.abi3.deployment import Deployment, ObjectSource, Segment, resolve_path
from runtime.abi3.descriptors import (
    Descriptor,
    ExtendedDescriptorType,
    MAX_DYNAMIC_TERMS,
    MAX_RANK,
    SelectorKind,
    Symbol,
    iteration_extent,
)


class MemoryError_(Exception):
    """Raised on any device-memory access violation (trap class 3 or 7)."""


NUMPY_DTYPE: dict[int, np.dtype] = {
    DType.U8: np.dtype(np.uint8),
    DType.I8: np.dtype(np.int8),
    DType.U16: np.dtype(np.uint16),
    DType.I16: np.dtype(np.int16),
    DType.U32: np.dtype(np.uint32),
    DType.I32: np.dtype(np.int32),
    DType.U64: np.dtype(np.uint64),
    DType.I64: np.dtype(np.int64),
    DType.BF16: np.dtype(np.uint16),        # architectural bit pattern
    DType.FP16: np.dtype(np.float16),
    DType.FP32: np.dtype(np.float32),
    DType.FP64: np.dtype(np.float64),
    DType.FP8_E4M3FN: np.dtype(np.uint8),   # architectural bit pattern
    DType.FP8_E5M2: np.dtype(np.uint8),
    DType.MXFP4_E2M1: np.dtype(np.uint8),   # two elements per byte
    DType.E8M0_SCALE: np.dtype(np.uint8),
}

SUB_BYTE_DTYPES = frozenset({int(DType.MXFP4_E2M1)})


@dataclass(slots=True)
class _MappedSegment:
    """One resolved segment: a memmap plus its logical byte range."""

    start: int
    stop: int
    array: np.ndarray
    path: str
    file_offset: int


class MemoryObject:
    """One ABI 3.0 memory object backed by mappings or an anonymous buffer."""

    __slots__ = (
        "object_id",
        "size_bytes",
        "storage_class",
        "permissions",
        "node_id",
        "_segments",
        "_anonymous",
        "_descriptor",
    )

    def __init__(
        self,
        object_id: int,
        descriptor: Descriptor,
        source: ObjectSource,
        root: Path | None,
        *,
        writable_override: bool = False,
        mappings: dict[Path, np.ndarray] | None = None,
    ) -> None:
        payload = descriptor.payload
        self.object_id = object_id
        self.size_bytes = payload["size_bytes"]
        self.storage_class = StorageClass(payload["storage_class"])
        self.permissions = descriptor.permissions
        self.node_id = payload["node_id"]
        self._descriptor = descriptor
        self._segments: list[_MappedSegment] = []
        self._anonymous: np.ndarray | None = None
        if source.kind == "zero":
            if source.fill:
                self._anonymous = np.full(self.size_bytes, source.fill, dtype=np.uint8)
            else:
                # ``np.zeros`` is calloc-backed, so the kernel hands back
                # lazily faulted zero pages and only the bytes a request
                # actually touches are ever committed.  ``np.full`` writes
                # every byte, which commits the whole object up front: the
                # DeepSeek cluster deployment declares a 160 GiB activation
                # arena sized by the *maximum* span, so a 104-token prefill
                # was paying 160 GiB of resident anonymous memory to use a
                # fraction of a percent of it, and was OOM-killed for it on a
                # 188 GiB machine.  The contents are identical either way.
                self._anonymous = np.zeros(self.size_bytes, dtype=np.uint8)
        elif source.kind == "generated":
            from runtime.sim.generators import generate_bytes
            from runtime.abi3.crc import sha256_hex

            payload = generate_bytes(source.generator, source.parameters)
            if len(payload) != self.size_bytes:
                raise MemoryError_(
                    f"object {object_id}: generator {source.generator!r} produced "
                    f"{len(payload)} bytes, the descriptor declares "
                    f"{self.size_bytes}"
                )
            actual = sha256_hex(payload)
            if actual != source.digest:
                raise MemoryError_(
                    f"object {object_id}: generator {source.generator!r} produced "
                    f"digest {actual[:16]}, the deployment binds "
                    f"{source.digest[:16]}; a drifting generator would silently "
                    "change model outputs"
                )
            self._anonymous = np.frombuffer(payload, dtype=np.uint8).copy()
        else:
            cursor = 0
            for segment in source.segments:
                path = resolve_path(root, segment.path)
                array = _map_range(path, segment.offset, segment.bytes, mappings)
                self._segments.append(
                    _MappedSegment(
                        start=cursor,
                        stop=cursor + segment.bytes,
                        array=array,
                        path=str(path),
                        file_offset=segment.offset,
                    )
                )
                cursor += segment.bytes
            if cursor != self.size_bytes:
                raise MemoryError_(
                    f"object {object_id}: segments cover {cursor} of "
                    f"{self.size_bytes} bytes"
                )
        if writable_override:
            self.permissions |= int(Permission.WRITE)

    # -- properties ------------------------------------------------------
    @property
    def writable(self) -> bool:
        return bool(
            self.permissions
            & (Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT)
        )

    @property
    def readable(self) -> bool:
        return bool(self.permissions & Permission.READ)

    def _check_range(self, offset: int, nbytes: int) -> None:
        if offset < 0 or nbytes < 0 or offset + nbytes > self.size_bytes:
            raise MemoryError_(
                f"object {self.object_id}: access [{offset}, {offset + nbytes}) "
                f"exceeds {self.size_bytes} bytes"
            )

    # -- byte access -----------------------------------------------------
    def read(self, offset: int, nbytes: int) -> bytes:
        self._check_range(offset, nbytes)
        if not self.readable:
            raise MemoryError_(f"object {self.object_id} is not readable")
        return bytes(self._byte_view(offset, nbytes))

    def write(self, offset: int, payload: bytes) -> None:
        self._check_range(offset, len(payload))
        if not self.writable:
            raise MemoryError_(
                f"object {self.object_id} ({self.storage_class.name}) is not writable"
            )
        self._byte_view(offset, len(payload))[:] = np.frombuffer(
            payload, dtype=np.uint8
        )

    def _byte_view(self, offset: int, nbytes: int) -> np.ndarray:
        """Return a uint8 view, contiguous when the range is in one segment."""
        if self._anonymous is not None:
            return self._anonymous[offset : offset + nbytes]
        if nbytes == 0:
            return np.empty(0, dtype=np.uint8)
        segment = self._find(offset)
        if offset + nbytes <= segment.stop:
            local = offset - segment.start
            return segment.array[local : local + nbytes]
        # Spanning read: assemble.  Backends place tensors so that a single
        # view never spans a shard boundary, so this is a correctness fallback
        # rather than a hot path.
        out = np.empty(nbytes, dtype=np.uint8)
        written = 0
        cursor = offset
        while written < nbytes:
            segment = self._find(cursor)
            local = cursor - segment.start
            take = min(segment.stop - cursor, nbytes - written)
            out[written : written + take] = segment.array[local : local + take]
            written += take
            cursor += take
        return out

    def _find(self, offset: int) -> _MappedSegment:
        low, high = 0, len(self._segments) - 1
        while low <= high:
            mid = (low + high) // 2
            segment = self._segments[mid]
            if offset < segment.start:
                high = mid - 1
            elif offset >= segment.stop:
                low = mid + 1
            else:
                return segment
        raise MemoryError_(f"object {self.object_id}: offset {offset} unmapped")

    def anonymous_buffer(self) -> np.ndarray | None:
        """The private byte buffer of this object, or ``None`` if it is mapped.

        A zero-filled or generated object owns a private ``uint8`` array: it is
        process memory and nothing outside the process holds its contents.  A
        file-backed object is a read-only ``numpy.memmap`` over authenticated
        checkpoint bytes, which the deployment manifest already binds.  The
        distinction is exactly the one a checkpoint has to make -- what must be
        serialised versus what is re-derived from the deployment -- so it is
        stated here rather than by reaching for a private attribute.
        """
        return self._anonymous

    def contiguous_base(self, offset: int, nbytes: int) -> np.ndarray | None:
        """Return a zero-copy uint8 view, or ``None`` if the range spans files."""
        self._check_range(offset, nbytes)
        if self._anonymous is not None:
            return self._anonymous[offset : offset + nbytes]
        if not self._segments:
            return None
        segment = self._find(offset)
        if offset + nbytes <= segment.stop:
            local = offset - segment.start
            return segment.array[local : local + nbytes]
        return None


def _map_range(
    path: Path,
    offset: int,
    nbytes: int,
    mappings: dict[Path, np.ndarray] | None = None,
) -> np.ndarray:
    """Return a zero-copy uint8 view of ``nbytes`` at ``offset`` of ``path``.

    One mapping per *file*, not per segment.  This matters at scale and the
    limit is the kernel's, not this program's: Linux caps a process at
    ``vm.max_map_count`` mappings, 65,530 by default.  The DeepSeek deployment
    addresses its 156 GB checkpoint as 67,612 segments across 48 shards, so
    mapping each segment separately exceeds the cap and fails with a bare
    ``OSError: [Errno 12] Cannot allocate memory`` that looks like the machine
    is out of RAM when it has 130 GB free.

    Mapping whole files and slicing costs nothing extra -- the pages are only
    faulted in on access either way -- and takes the DeepSeek deployment from
    67,612 mappings to 48.  ``mappings`` is the per-deployment cache; passing
    ``None`` maps this one file on its own, which is what a caller wanting a
    single range should do.
    """
    if not path.exists():
        raise MemoryError_(f"object source file is missing: {path}")
    size = path.stat().st_size
    if offset + nbytes > size:
        raise MemoryError_(
            f"segment [{offset}, {offset + nbytes}) exceeds {path} ({size} bytes)"
        )
    if nbytes == 0:
        return np.empty(0, dtype=np.uint8)
    if mappings is None:
        page = mmap.ALLOCATIONGRANULARITY
        aligned = (offset // page) * page
        slack = offset - aligned
        mapping = np.memmap(
            path, dtype=np.uint8, mode="r", offset=aligned, shape=(slack + nbytes,)
        )
        return mapping[slack : slack + nbytes]
    whole = mappings.get(path)
    if whole is None:
        whole = np.memmap(path, dtype=np.uint8, mode="r", shape=(size,))
        mappings[path] = whole
    return whole[offset : offset + nbytes]


class DeviceMemory:
    """All memory objects of one activated deployment, on one node.

    A cluster deployment has one of these per logical node.  ``share_from``
    builds a sibling arena against an existing one: an object with no write
    permission is *shared* by reference, because it is immutable and every node
    addresses its own shard of it through the view's ``NODE_ID`` term, so a
    private copy would be thirty-two identical mappings of the same checkpoint
    bytes.  Everything writable -- the activation arena, the state images, the
    host windows -- is built fresh, which is what makes a node's activations
    node-local and a collective the only way one node can see another's.
    """

    def __init__(
        self,
        deployment: Deployment,
        *,
        root: Path | None = None,
        share_from: "DeviceMemory | None" = None,
    ) -> None:
        self.deployment = deployment
        self.root = root if root is not None else deployment.root
        self.objects: dict[int, MemoryObject] = {}
        # One whole-file mapping shared by every object that reads from it.
        # Held on the instance so the mappings outlive the loop below and die
        # with this deployment rather than with the process.  A sibling node
        # shares the cache: the checkpoint is mapped once for the cluster.
        self._mappings: dict[Path, np.ndarray] = (
            share_from._mappings if share_from is not None else {}
        )
        for descriptor in deployment.table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
                continue
            oid = descriptor.descriptor_id
            source = deployment.objects.get(oid)
            if source is None:
                raise MemoryError_(f"object {oid} has no declared source")
            if share_from is not None:
                existing = share_from.objects[oid]
                if not existing.writable:
                    self.objects[oid] = existing
                    continue
                if existing._segments:
                    raise MemoryError_(
                        f"object {oid} is writable and file-backed; a per-node "
                        "private copy of a mapped object is not expressible "
                        "without relaying out the checkpoint"
                    )
            self.objects[oid] = MemoryObject(
                oid, descriptor, source, self.root, mappings=self._mappings
            )

    def __getitem__(self, object_id: int) -> MemoryObject:
        try:
            return self.objects[object_id]
        except KeyError:
            raise MemoryError_(f"unknown memory object {object_id}") from None

    def total_bytes(self) -> int:
        return sum(obj.size_bytes for obj in self.objects.values())

    def bytes_by_class(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for obj in self.objects.values():
            out[obj.storage_class.name] = out.get(obj.storage_class.name, 0) + obj.size_bytes
        return out


# ---------------------------------------------------------------------------
# View resolution
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class ResolvedView:
    """A tensor view bound to concrete loop and symbol values."""

    descriptor_id: int
    object_id: int
    dtype: int
    dims: tuple[int, ...]
    strides: tuple[int, ...]
    element_offset: int
    writable: bool
    scale_object_id: int = NO_ID
    scale_block_elements: int = 0
    #: Amendment A15: the scale block along the *leading* axis.  Zero on the
    #: wire means one, which is the one-dimensional case amendment A8 froze, so
    #: this is resolved to one rather than carried as zero.
    scale_block_rows: int = 1
    #: Amendment A18: the axis whose extent the request determines, and the
    #: affine function of the bound symbol that gives it.  Axis 0 with a
    #: numerator and unit of one and no bias is amendment A13.
    extent_axis: int = 0
    extent_unit: int = 1
    extent_numerator: int = 1
    extent_bias: int = 0

    @property
    def element_count(self) -> int:
        count = 1
        for dim in self.dims:
            count *= dim
        return count

    @property
    def numpy_dtype(self) -> np.dtype:
        return NUMPY_DTYPE[self.dtype]

    @property
    def is_sub_byte(self) -> bool:
        return self.dtype in SUB_BYTE_DTYPES


class ViewResolver:
    """Resolves tensor-view descriptors against loop and symbol bindings."""

    def __init__(self, deployment: Deployment, memory: DeviceMemory) -> None:
        self.deployment = deployment
        self.memory = memory
        self._cache: dict[int, Descriptor] = {}
        self._device_cache: dict[tuple[Any, ...], tuple[int, Any]] = {}
        self._device_cache_backend: str = ""
        self._device_cache_used: int = 0

    def descriptor(self, view_id: int) -> Descriptor:
        cached = self._cache.get(view_id)
        if cached is None:
            cached = self.deployment.table.get(
                view_id, ExtendedDescriptorType.TENSOR_VIEW
            )
            self._cache[view_id] = cached
        return cached

    def resolve(
        self,
        view_id: int,
        loops: Mapping[int, int],
        symbols: Mapping[int, int],
    ) -> ResolvedView:
        descriptor = self.descriptor(view_id)
        payload = descriptor.payload
        rank = payload["rank"]
        offset = payload["element_offset"]
        # Amendment A18: the view says which axis the request determines and
        # what affine function of the bound symbol gives it.  All four fields
        # read zero on every view written before the amendment, and that is
        # axis 0, ``value`` itself, no bias -- amendment A13 exactly.
        axis = int(payload["extent_axis"])
        unit = max(int(payload["extent_unit"]), 1)
        numerator = max(int(payload["extent_numerator"]), 1)
        bias = int(payload["extent_bias"])
        if rank and not 0 <= axis < rank:
            raise MemoryError_(
                f"view {view_id}: amendment A18 extent axis {axis} is outside "
                f"the rank-{rank} view that declares it"
            )
        leading_loop: int | None = None
        for slot in range(payload["dynamic_term_count"]):
            kind = payload[f"term{slot}_kind"]
            index = payload[f"term{slot}_index"]
            stride = payload[f"term{slot}_stride"]
            if kind == SelectorKind.LOOP_INDUCTION:
                try:
                    value = loops[index]
                except KeyError:
                    raise MemoryError_(
                        f"view {view_id}: loop {index} is not active"
                    ) from None
            elif kind == SelectorKind.RUNTIME_SYMBOL:
                try:
                    value = symbols[index]
                except KeyError:
                    raise MemoryError_(
                        f"view {view_id}: symbol {Symbol(index).name} is unbound"
                    ) from None
            else:
                raise MemoryError_(f"view {view_id}: bad selector kind {kind}")
            offset += value * stride
            if kind == SelectorKind.LOOP_INDUCTION and self._walks_extent_axis(
                payload, stride, index, axis, numerator, unit
            ):
                leading_loop = self._remaining_extent(
                    index, value, symbols, numerator, unit, bias, leading_loop
                )
        dims = [payload[f"dim{a}"] for a in range(rank)]
        if leading_loop is not None and dims:
            # A symbol-bounded loop's final iteration is partial: a block of 512
            # tokens over a span of 93 has one iteration holding 93 rows, not
            # 512.  The loop descriptor already states this -- ``bound_symbol``
            # and ``bound_divisor`` are exactly the extent and the block -- so
            # the resolved view presents the rows the request has rather than
            # the rows the block could hold.  Without it a backend must emit one
            # token per dispatch to stay correct, which is the retired-work
            # failure ABI 3.0 exists to remove.
            #
            # A18 moves the same statement onto the axis the view names and
            # into that axis's own units.  Three released operands need it and
            # none of them is a special case of the other two: the compressor's
            # pool counts *groups* of four tokens behind a batch, so neither the
            # axis nor the unit A13 assumed is the one it has; the index key
            # counts committed groups of 128; and the attention KV join is the
            # request's rows *plus a 128-row sliding window*, which no clamp can
            # state because a clamp only ever shortens.
            remaining = leading_loop
            if 0 < remaining < dims[axis]:
                dims[axis] = remaining
        return ResolvedView(
            descriptor_id=view_id,
            object_id=descriptor.primary_object_id,
            dtype=payload["dtype"],
            dims=tuple(dims),
            strides=tuple(payload[f"stride{a}"] for a in range(rank)),
            element_offset=offset,
            writable=bool(descriptor.permissions & Permission.WRITE),
            scale_object_id=payload["scale_object_id"],
            scale_block_elements=payload["scale_block_elements"],
            scale_block_rows=max(int(payload["scale_block_rows"]), 1),
            extent_axis=axis,
            extent_unit=unit,
            extent_numerator=numerator,
            extent_bias=bias,
        )

    def _walks_extent_axis(
        self,
        payload: Mapping[str, Any],
        term_stride: int,
        loop_id: int,
        axis: int,
        numerator: int,
        unit: int,
    ) -> bool:
        """Does this term step the view along the axis the request determines?

        A13 clamps the leading extent because a block loop's final iteration
        holds fewer rows than the block.  That is only meaningful when the loop
        is walking the axis being clamped, and the arithmetic says when it is:
        one iteration advances by one whole block of that axis, so the term's
        stride is ``stride[axis] * (numerator * bound_divisor / unit)``.

        A view can perfectly well be indexed by a loop along some *other* axis.
        The mHC branch reduction is one: its leading axis is the four
        hyper-connection streams while the loop steps over tokens, so its term
        stride is one token's row and not four streams' worth of the leading
        one.  Clamping such a view would present four streams as one, which is
        not a partial final iteration of anything.

        Deriving the answer rather than assuming it is the point.  The rule
        originally applied to any loop-induction term in slot zero, which is the
        assumption that the loop indexes the leading axis -- true of every view
        either model had emitted, and false in general.  A18 keeps the
        derivation and lets the view say *which* axis the derivation is about,
        and in what unit; ``axis = 0, unit = 1`` is A13's own test, unchanged.
        """
        divisor = 0
        try:
            loop = self.deployment.table.get(
                loop_id, ExtendedDescriptorType.LOOP_CONTROL
            )
        except Exception:  # not a loop descriptor: _remaining_extent says so
            return True
        if loop.payload["bound_selector_kind"] != SelectorKind.RUNTIME_SYMBOL:
            return False
        divisor = max(int(loop.payload["bound_divisor"]), 1)
        step = iteration_extent(divisor, numerator, unit)
        if step is None:
            # One iteration is not a whole number of this axis's elements, so
            # the term does not walk it in blocks and bounds nothing.
            return False
        return int(term_stride) == int(payload[f"stride{axis}"]) * step

    def _remaining_extent(
        self,
        loop_id: int,
        iteration: int,
        symbols: Mapping[int, int],
        numerator: int,
        unit: int,
        bias: int,
        current: int | None,
    ) -> int | None:
        """Elements left on the clamped axis this iteration, if fewer.

        The loop counts the bound symbol's units -- tokens -- and the axis
        counts its own elements, which are an affine function of them:
        ``numerator * tokens / unit + bias``.  The division floors, because a
        partial group is not an element of a group axis -- four tokens of a
        128-token group are no compressed group at all, which is exactly what
        the compressor's own should-compress predicate says.  The bias is added
        after, because it is rows the operand carries whatever the request is:
        a KV join's 128-row sliding window is there for a span of one.

        With ``numerator = 1, unit = 1, bias = 0`` the function is the identity
        and this is A13's ``_remaining_rows``.
        """
        try:
            loop = self.deployment.table.get(
                loop_id, ExtendedDescriptorType.LOOP_CONTROL
            )
        except Exception:  # not a loop descriptor: nothing to bound
            return current
        payload = loop.payload
        if payload["bound_selector_kind"] != SelectorKind.RUNTIME_SYMBOL:
            return current
        bound = symbols.get(payload["bound_symbol_id"])
        if bound is None:
            return current
        divisor = max(int(payload["bound_divisor"]), 1)
        block = iteration_extent(divisor, numerator, unit)
        if block is None:
            return current
        tokens = int(bound) - int(iteration) * divisor
        if tokens <= 0:
            # An iteration at or past the extent bounds nothing.  Asking for the
            # affine image of a negative count would answer a question the loop
            # never poses.
            return current
        extent = (int(numerator) * tokens) // unit + int(bias)
        if extent <= 0 or extent >= block + int(bias):
            return current
        return extent if current is None else min(current, extent)

    # -- array access ----------------------------------------------------
    def read_array(self, view: ResolvedView) -> np.ndarray:
        """Return the view's elements as a NumPy array of its storage dtype.

        Zero-copy when the extent lies in one mapped segment and the strides
        describe a legal NumPy layout; otherwise a gathered copy.
        """
        obj = self.memory[view.object_id]
        if view.is_sub_byte:
            return self._read_sub_byte(view, obj)
        dtype = view.numpy_dtype
        itemsize = dtype.itemsize
        span = _element_span(view.dims, view.strides)
        base = obj.contiguous_base(
            view.element_offset * itemsize, (span + 1) * itemsize
        )
        if base is not None:
            flat = base.view(dtype)
            return np.lib.stride_tricks.as_strided(
                flat,
                shape=view.dims,
                strides=tuple(s * itemsize for s in view.strides),
                writeable=False,
            )
        payload = obj.read(view.element_offset * itemsize, (span + 1) * itemsize)
        flat = np.frombuffer(payload, dtype=dtype)
        return np.lib.stride_tricks.as_strided(
            flat,
            shape=view.dims,
            strides=tuple(s * itemsize for s in view.strides),
            writeable=False,
        )

    def device_array(self, view: ResolvedView, backend: Any) -> Any:
        """The view's elements placed on ``backend``'s device, without detour.

        The host read stays exactly what :meth:`read_array` produces -- a
        strided view over the ``numpy.memmap`` when the extent lies in one
        mapped segment -- so the zero-copy weight residency is untouched.  What
        this adds is the *placement*: the mapped bytes are handed to the
        backend in their storage format, so a BF16 weight crosses the bus as
        16-bit codes and is widened on the far side, rather than being widened
        to binary32 on the host and crossing at twice the width.

        Immutable objects may additionally be held resident, bounded by
        ``backend.device_cache_bytes()``.  The budget is zero unless an
        operator opts in, because the device is shared and a Qwen deployment
        addresses more weight than it has free.
        """
        array = self.read_array(view)
        if getattr(backend, "device", "host") == "host":
            # A host backend computes on the mapping itself.  Placing would be
            # a copy with no destination, so there is nothing to place.
            return array
        if backend.name != self._device_cache_backend:
            self.clear_device_cache()
            self._device_cache_backend = backend.name
        budget = int(backend.device_cache_bytes())
        obj = self.memory[view.object_id]
        cacheable = budget > 0 and not obj.writable
        key: tuple[Any, ...] | None = None
        if cacheable:
            key = (
                view.object_id,
                int(view.dtype),
                tuple(view.dims),
                tuple(view.strides),
                int(view.element_offset),
            )
            hit = self._device_cache.get(key)
            if hit is not None:
                return hit[1]
        placed = backend.place(array)
        if cacheable and key is not None:
            nbytes = int(array.size) * int(array.dtype.itemsize)
            if nbytes <= budget - self._device_cache_used:
                self._device_cache[key] = (nbytes, placed)
                self._device_cache_used += nbytes
        return placed

    def clear_device_cache(self) -> None:
        """Release every device-resident view this resolver is holding."""
        self._device_cache.clear()
        self._device_cache_used = 0
        self._device_cache_backend = ""

    def _read_sub_byte(self, view: ResolvedView, obj: MemoryObject) -> np.ndarray:
        """Read a 4-bit view as one uint8 nibble per element, low nibble first."""
        span = _element_span(view.dims, view.strides) + 1
        start = view.element_offset
        if start % 2 or span % 2:
            raise MemoryError_(
                f"view {view.descriptor_id}: sub-byte views must start and span "
                "an even number of elements"
            )
            
        payload = obj.read(start // 2, span // 2)
        packed = np.frombuffer(payload, dtype=np.uint8)
        nibbles = np.empty(span, dtype=np.uint8)
        nibbles[0::2] = packed & 0x0F
        nibbles[1::2] = packed >> 4
        return np.lib.stride_tricks.as_strided(
            nibbles, shape=view.dims, strides=tuple(s for s in view.strides),
            writeable=False,
        )

    def _write_sub_byte(
        self, view: ResolvedView, values: np.ndarray, obj: MemoryObject
    ) -> None:
        """Write a 4-bit view, packing two elements per byte, low nibble first.

        Sub-byte views were read-only because nothing produced one: MXFP4 was a
        checkpoint format and the engines only consumed it.  The DeepSeek
        indexer produces one -- ``quantization_fp4_qdq_bf16_quantize_v1`` writes
        E2M1 codes and their E8M0 scales -- so the destination has to exist.

        Two elements share a byte, so a *strided* destination is not writable at
        all: a stride that skips elements would have this write read and rewrite
        nibbles belonging to another view, which is an aliasing write however it
        is spelled.  The view must therefore be dense and row-major, and must
        start and span an even number of elements, which is exactly what
        :meth:`_read_sub_byte` already requires of a read.
        """
        dims = tuple(int(d) for d in view.dims)
        strides = tuple(int(s) for s in view.strides)
        expected: list[int] = [1] * len(dims)
        running = 1
        for axis in range(len(dims) - 1, -1, -1):
            expected[axis] = running
            running *= max(dims[axis], 1)
        if strides != tuple(expected):
            raise MemoryError_(
                f"view {view.descriptor_id}: a 4-bit destination must be dense "
                f"and row-major; strides {strides} are not {tuple(expected)}, "
                "and two elements of a strided 4-bit view share a byte with "
                "elements the view does not name"
            )
        if values.shape != dims:
            raise MemoryError_(
                f"view {view.descriptor_id}: writing shape {values.shape} into "
                f"{dims}"
            )
        span = running
        if view.element_offset % 2 or span % 2:
            raise MemoryError_(
                f"view {view.descriptor_id}: sub-byte views must start and span "
                "an even number of elements"
            )
        flat = np.ascontiguousarray(values).reshape(-1)
        if flat.dtype != np.uint8:
            raise MemoryError_(
                f"view {view.descriptor_id}: writing {flat.dtype} into a 4-bit "
                "view; one unsigned nibble per element is the storage form"
            )
        if flat.size and int(flat.max()) > 0x0F:
            raise MemoryError_(
                f"view {view.descriptor_id}: a 4-bit element outside 0..15"
            )
        packed = (flat[0::2] | (flat[1::2] << np.uint8(4))).astype(np.uint8)
        obj.write(view.element_offset // 2, packed.tobytes())

    def write_array(self, view: ResolvedView, values: np.ndarray) -> None:
        """Write ``values`` into ``view``, checking permission, shape and dtype."""
        obj = self.memory[view.object_id]
        if not obj.writable:
            raise MemoryError_(
                f"view {view.descriptor_id} targets object {view.object_id} "
                f"({obj.storage_class.name}), which has no write permission"
            )
        if view.is_sub_byte:
            self._write_sub_byte(view, values, obj)
            return
        dtype = view.numpy_dtype
        if values.shape != view.dims:
            raise MemoryError_(
                f"view {view.descriptor_id}: writing shape {values.shape} into "
                f"{view.dims}"
            )
        if values.dtype != dtype:
            raise MemoryError_(
                f"view {view.descriptor_id}: writing {values.dtype} into a "
                f"{dtype} view; conversion must be an explicit engine operation"
            )
        itemsize = dtype.itemsize
        span = _element_span(view.dims, view.strides)
        base = obj.contiguous_base(
            view.element_offset * itemsize, (span + 1) * itemsize
        )
        if base is None:
            raise MemoryError_(
                f"view {view.descriptor_id}: destination is not a single mapping"
            )
        target = np.lib.stride_tricks.as_strided(
            base.view(dtype),
            shape=view.dims,
            strides=tuple(s * itemsize for s in view.strides),
            writeable=True,
        )
        target[...] = values


def _element_span(dims: Sequence[int], strides: Sequence[int]) -> int:
    """Largest element index reachable from offset zero for this view."""
    span = 0
    for dim, stride in zip(dims, strides):
        span += (dim - 1) * stride
    return span
