"""ROM region planning shared by the Qwen and DeepSeek ROM products.

What this module owns
---------------------

1.  **Region layout.**  An immutable ROM address space is partitioned into
    *regions*.  A region owns one or more *slots* of identical byte length --
    typically the same operand of every layer in one layer run -- laid out
    contiguously so that a single ABI 3.0 tensor view plus one
    :class:`~runtime.abi3.builder.DynamicTerm` reaches any slot.  That is what
    makes loop compression possible on ROM: the layer index becomes a ROM row
    address offset, not a separate descriptor.

2.  **Alignment and zero-padded gaps.**  Each region base is aligned to the ROM
    macro row.  The tail of a region up to the next aligned base is a *pad*: a
    declared, addressable, immutable, zero-filled ROM object.  Padding is never
    an undeclared hole -- every byte of the ROM address space is owned by a
    declared immutable object, so BIST can read it and the inverse checker can
    prove it is zero.

3.  **Per-region content digest.**  The bytes themselves stay in the
    authenticated checkpoint (zero copy: no 16 GB or 156 GB image is ever
    written).  The region digest therefore binds the *ordered list of
    authenticated payload digests* plus the zero-pad extent, under the rule in
    :func:`region_content_digest`.  :mod:`compiler.backends.rom.common.inverse`
    re-implements that rule independently and, given a byte reader over the
    checkpoint, additionally proves the reconstructed bytes are bit-identical to
    the checkpoint binding.

4.  **The repair map.**  Spare row/column activation plus a quarantine list, as
    a first-class compiler artifact.  Before this module the repair map existed
    only as an RTL translation table (``rtl/ot_rom_wrapper.sv``: ``repair_valid``
    / ``repair_map``) and a host/CSR window (``spec/INTERFACES.md``:
    ``REPAIR_MAP_WINDOW``); nothing on the compiler side produced one.  The
    producer here is deterministic: defects arrive sorted, spares are allocated
    lowest-first inside the owning bank, and a bank that exhausts its spares
    quarantines its owning resource rather than silently returning bad data.

Nothing in this module writes weight bytes.  A region's
:class:`~runtime.abi3.deployment.ObjectSource` is an ordered list of
:class:`~runtime.abi3.deployment.Segment` ranges into the locked checkpoint,
exactly as the HBM backend does.  The physical claim "these bytes are in mask
ROM" is carried by the storage class, the permissions and this plan.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field as dc_field
from typing import Any, Iterable, Mapping, Sequence

from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import canonical_json
from runtime.abi3.constants import (
    DTYPE_BITS,
    DType,
    IntegrityMode,
    NO_ID,
    NO_NODE,
    Permission,
    StorageClass,
)
from runtime.abi3.deployment import ObjectSource, Segment

ROM_PLAN_SCHEMA = "opentallas.rom.region_plan.v1"
REGION_DIGEST_DOMAIN = b"opentallas.rom.region.v1\n"
REPAIR_MAP_SCHEMA = "opentallas.rom.repair_map.v1"

#: Permissions every ROM object carries, and the only ones it may carry.  The
#: independent verifier rejects a ROM object that declares WRITE, STATE_PREPARE
#: or STATE_COMMIT; this constant is why that check passes rather than being
#: worked around.
ROM_PERMISSIONS = int(Permission.READ | Permission.IMMUTABLE)


class RomImageError(ValueError):
    """Raised when a ROM region plan cannot be produced safely."""


def _align_up(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment


def _sha256(payload: bytes) -> bytes:
    return hashlib.sha256(payload).digest()


# ---------------------------------------------------------------------------
# Policy and coordinates
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RomLayoutPolicy:
    """Geometry of the immutable ROM array this product compiles for."""

    #: Region base alignment.  This is the ROM macro row/page granularity: a
    #: region base is a row address, so the layer stride inside a region is a
    #: whole number of rows.
    alignment_bytes: int = 4096
    #: Bytes per physical ROM row inside a bank.  Rows are the repair unit.
    row_bytes: int = 4096
    #: ROM bytes one placement resource (a chip bank, or a wafer tile) owns.
    resource_bytes: int = 1 << 30
    #: Spare rows provisioned per bank, as a fraction of its data rows.
    spare_row_fraction: float = 0.01
    #: Floor on spare rows per bank, so a small bank still has redundancy.
    minimum_spare_rows: int = 4
    #: Spare bit-columns per bank.
    spare_columns_per_bank: int = 8
    #: First ROM byte address of every placement resource.
    base_address: int = 0

    def validate(self) -> None:
        for name in ("alignment_bytes", "row_bytes", "resource_bytes"):
            value = getattr(self, name)
            if value <= 0 or value & (value - 1):
                raise RomImageError(f"{name} must be a positive power of two")
        if self.row_bytes > self.alignment_bytes:
            raise RomImageError("the region alignment must cover a whole ROM row")
        if self.alignment_bytes % self.row_bytes:
            raise RomImageError("the region alignment must be a multiple of the row")
        if not 0.0 <= self.spare_row_fraction < 1.0:
            raise RomImageError("spare_row_fraction must be in [0, 1)")
        if self.minimum_spare_rows < 0 or self.spare_columns_per_bank < 0:
            raise RomImageError("spare inventories must be non-negative")


@dataclass(frozen=True, slots=True)
class RomCoordinate:
    """Where a byte range physically sits.

    ``node_id`` is the ABI node.  A wafer-scale logical accelerator is ONE node,
    so the wafer product leaves it at 0 and uses ``reticle``/``tile``.  A
    conventional single chip leaves ``reticle``/``tile`` at 0 and uses ``bank``.
    """

    node_id: int = 0
    reticle: int = 0
    tile: int = 0
    bank: int = 0

    @property
    def resource_id(self) -> tuple[int, int, int, int]:
        return (self.node_id, self.reticle, self.tile, self.bank)

    def to_list(self) -> list[int]:
        return [self.node_id, self.reticle, self.tile, self.bank]


@dataclass(frozen=True, slots=True)
class RomShard:
    """One contiguous piece of a region resident in one physical resource."""

    coordinate: RomCoordinate
    region_offset: int
    bytes: int
    resource_address: int

    def to_list(self) -> list[int]:
        return [
            *self.coordinate.to_list(),
            self.region_offset,
            self.bytes,
            self.resource_address,
        ]


@dataclass(frozen=True, slots=True)
class RomMember:
    """One checkpoint-bound payload placed inside a region."""

    tensor_id: str
    slot: int
    offset_bytes: int
    bytes: int
    source_path: str
    source_offset: int
    source_sha256: str
    dtype: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "bytes": self.bytes,
            "dtype": self.dtype,
            "offset_bytes": self.offset_bytes,
            "slot": self.slot,
            "source_offset": self.source_offset,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "tensor_id": self.tensor_id,
        }


@dataclass(frozen=True, slots=True)
class RegionRequest:
    """What a backend asks the planner to place.

    ``slots`` are the *same* logical operand for successive iterations of one
    compressed loop.  Every slot must have identical byte length, or the loop
    stride would not be constant and the region could not be addressed by a
    single dynamic term.
    """

    key: str
    role: str
    dtype: str
    slots: tuple[RomMember, ...]
    element_count_per_slot: int
    coordinate_hint: RomCoordinate = RomCoordinate()


@dataclass(slots=True)
class RomRegion:
    """One immutable region of the ROM address space."""

    region_id: int
    key: str
    role: str
    dtype: str
    coordinate: RomCoordinate
    base_address: int
    payload_bytes: int
    pad_bytes: int
    alignment: int
    slot_count: int
    slot_bytes: int
    slot_elements: int
    members: tuple[RomMember, ...]
    shards: tuple[RomShard, ...]
    content_digest: bytes
    pad_digest: bytes
    object_id: int = NO_ID
    pad_object_id: int = NO_ID

    @property
    def total_bytes(self) -> int:
        return self.payload_bytes + self.pad_bytes

    @property
    def slot_element_stride(self) -> int:
        """Element offset between successive slots, for a dynamic view term."""
        bits = DTYPE_BITS[DTYPE_BY_NAME[self.dtype]]
        if self.slot_bytes * 8 % bits:
            raise RomImageError(
                f"region {self.key!r}: slot of {self.slot_bytes} bytes is not a "
                f"whole number of {bits}-bit elements"
            )
        return self.slot_bytes * 8 // bits

    def to_dict(self) -> dict[str, Any]:
        return {
            "alignment": self.alignment,
            "base_address": self.base_address,
            "content_sha256": self.content_digest.hex(),
            "coordinate": self.coordinate.to_list(),
            "dtype": self.dtype,
            "key": self.key,
            "members": [m.to_dict() for m in self.members],
            "object_id": self.object_id,
            "pad_bytes": self.pad_bytes,
            "pad_object_id": self.pad_object_id,
            "pad_sha256": self.pad_digest.hex(),
            "payload_bytes": self.payload_bytes,
            "region_id": self.region_id,
            "role": self.role,
            "shards": [s.to_list() for s in self.shards],
            "slot_bytes": self.slot_bytes,
            "slot_count": self.slot_count,
            "slot_elements": self.slot_elements,
        }


# ---------------------------------------------------------------------------
# Repair map
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class DefectRecord:
    """One permanent defect reported by ROM BIST / DFT for a built device.

    ``kind`` is ``"row"``, ``"column"`` or ``"resource"``.  A ``"resource"``
    defect is unrepairable by redundancy and quarantines the owning tile/bank
    outright.
    """

    coordinate: RomCoordinate
    kind: str
    index: int
    source: str = "bist"

    def sort_key(self) -> tuple[Any, ...]:
        return (*self.coordinate.resource_id, self.kind, self.index, self.source)


@dataclass(frozen=True, slots=True)
class RepairEntry:
    """One activated spare, i.e. one logical->physical translation."""

    coordinate: RomCoordinate
    kind: str
    logical_index: int
    spare_index: int
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate.to_list(),
            "kind": self.kind,
            "logical_index": self.logical_index,
            "source": self.source,
            "spare_index": self.spare_index,
        }


@dataclass(frozen=True, slots=True)
class QuarantineEntry:
    """One resource withdrawn from service."""

    coordinate: RomCoordinate
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"coordinate": self.coordinate.to_list(), "reason": self.reason}


@dataclass(frozen=True, slots=True)
class BankGeometry:
    """Row/column inventory of one placement resource."""

    coordinate: RomCoordinate
    row_bytes: int
    data_rows: int
    spare_rows: int
    spare_columns: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate": self.coordinate.to_list(),
            "data_rows": self.data_rows,
            "row_bytes": self.row_bytes,
            "spare_columns": self.spare_columns,
            "spare_rows": self.spare_rows,
        }


@dataclass(slots=True)
class RepairMap:
    """Spare activation plus quarantine for one compiled ROM image."""

    banks: tuple[BankGeometry, ...]
    entries: tuple[RepairEntry, ...]
    quarantine: tuple[QuarantineEntry, ...]

    @property
    def active_resources(self) -> tuple[tuple[int, int, int, int], ...]:
        quarantined = {q.coordinate.resource_id for q in self.quarantine}
        return tuple(
            bank.coordinate.resource_id
            for bank in self.banks
            if bank.coordinate.resource_id not in quarantined
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "banks": [b.to_dict() for b in self.banks],
            "entries": [e.to_dict() for e in self.entries],
            "quarantine": [q.to_dict() for q in self.quarantine],
            "schema": REPAIR_MAP_SCHEMA,
            "spare_columns_total": sum(b.spare_columns for b in self.banks),
            "spare_columns_used": sum(1 for e in self.entries if e.kind == "column"),
            "spare_rows_total": sum(b.spare_rows for b in self.banks),
            "spare_rows_used": sum(1 for e in self.entries if e.kind == "row"),
        }

    @property
    def active_resource_digest(self) -> bytes:
        return _sha256(
            canonical_json(
                {
                    "active": [list(r) for r in self.active_resources],
                    "schema": REPAIR_MAP_SCHEMA,
                }
            )
        )

    @property
    def quarantine_digest(self) -> bytes:
        return _sha256(
            canonical_json(
                {
                    "quarantine": [q.to_dict() for q in self.quarantine],
                    "schema": REPAIR_MAP_SCHEMA,
                }
            )
        )

    @property
    def health_digest(self) -> bytes:
        return _sha256(canonical_json(self.to_dict()))


def plan_repair_map(
    regions: Sequence[RomRegion],
    policy: RomLayoutPolicy,
    defects: Sequence[DefectRecord] = (),
) -> RepairMap:
    """Derive the bank inventory and activate spares for ``defects``.

    Deterministic by construction: banks in resource order, defects sorted by
    :meth:`DefectRecord.sort_key`, spares allocated lowest-index first inside
    the owning bank.  A bank that runs out of spares quarantines its resource;
    it never silently keeps serving the defective line.
    """
    policy.validate()
    used: dict[tuple[int, int, int, int], int] = {}
    coordinates: dict[tuple[int, int, int, int], RomCoordinate] = {}
    for region in regions:
        for shard in region.shards:
            rid = shard.coordinate.resource_id
            coordinates.setdefault(rid, shard.coordinate)
            end = shard.resource_address + shard.bytes
            used[rid] = max(used.get(rid, 0), end)
    banks: list[BankGeometry] = []
    for rid in sorted(used):
        data_rows = _align_up(used[rid], policy.row_bytes) // policy.row_bytes
        spare_rows = max(
            policy.minimum_spare_rows,
            int(data_rows * policy.spare_row_fraction + 0.999999),
        )
        banks.append(
            BankGeometry(
                coordinate=coordinates[rid],
                row_bytes=policy.row_bytes,
                data_rows=data_rows,
                spare_rows=spare_rows,
                spare_columns=policy.spare_columns_per_bank,
            )
        )
    inventory = {bank.coordinate.resource_id: bank for bank in banks}
    next_spare_row: dict[tuple[int, int, int, int], int] = {}
    next_spare_column: dict[tuple[int, int, int, int], int] = {}
    entries: list[RepairEntry] = []
    quarantine: list[QuarantineEntry] = []
    quarantined: set[tuple[int, int, int, int]] = set()

    for defect in sorted(defects, key=DefectRecord.sort_key):
        rid = defect.coordinate.resource_id
        bank = inventory.get(rid)
        if bank is None:
            raise RomImageError(
                f"defect names resource {rid} which holds no ROM region"
            )
        if rid in quarantined:
            continue
        if defect.kind == "resource":
            quarantined.add(rid)
            quarantine.append(
                QuarantineEntry(defect.coordinate, f"unrepairable:{defect.source}")
            )
            continue
        if defect.kind == "row":
            if defect.index >= bank.data_rows:
                raise RomImageError(
                    f"row defect {defect.index} is outside bank {rid} depth "
                    f"{bank.data_rows}"
                )
            cursor = next_spare_row.get(rid, 0)
            if cursor >= bank.spare_rows:
                quarantined.add(rid)
                quarantine.append(
                    QuarantineEntry(defect.coordinate, "spare_rows_exhausted")
                )
                continue
            next_spare_row[rid] = cursor + 1
            entries.append(
                RepairEntry(
                    coordinate=defect.coordinate,
                    kind="row",
                    logical_index=defect.index,
                    spare_index=bank.data_rows + cursor,
                    source=defect.source,
                )
            )
            continue
        if defect.kind == "column":
            cursor = next_spare_column.get(rid, 0)
            if cursor >= bank.spare_columns:
                quarantined.add(rid)
                quarantine.append(
                    QuarantineEntry(defect.coordinate, "spare_columns_exhausted")
                )
                continue
            next_spare_column[rid] = cursor + 1
            entries.append(
                RepairEntry(
                    coordinate=defect.coordinate,
                    kind="column",
                    logical_index=defect.index,
                    spare_index=cursor,
                    source=defect.source,
                )
            )
            continue
        raise RomImageError(f"unknown defect kind {defect.kind!r}")

    return RepairMap(
        banks=tuple(banks),
        entries=tuple(entries),
        quarantine=tuple(
            sorted(quarantine, key=lambda q: (*q.coordinate.resource_id, q.reason))
        ),
    )


# ---------------------------------------------------------------------------
# Digest rules
# ---------------------------------------------------------------------------
DTYPE_BY_NAME: Mapping[str, DType] = {
    "bf16": DType.BF16,
    "fp16": DType.FP16,
    "fp32": DType.FP32,
    "fp8_e4m3fn": DType.FP8_E4M3FN,
    "fp8_e5m2": DType.FP8_E5M2,
    "mxfp4_e2m1": DType.MXFP4_E2M1,
    "e8m0": DType.E8M0_SCALE,
    "i8": DType.I8,
    "u8": DType.U8,
    "i32": DType.I32,
    "u32": DType.U32,
    "i64": DType.I64,
    "u64": DType.U64,
    "bool": DType.U8,
}


def region_content_digest(
    *,
    key: str,
    payload_bytes: int,
    pad_bytes: int,
    slot_count: int,
    slot_bytes: int,
    members: Iterable[RomMember],
) -> bytes:
    """The frozen binding rule for a ROM region's content.

    ROM regions are zero copy, so this digest cannot be the SHA-256 of a
    materialised image.  It binds, in placement order, every member's
    authenticated checkpoint payload digest together with its offset and
    length, plus the zero-pad extent.  Given the checkpoint, the region's bytes
    are fully determined by this record, and
    :func:`compiler.backends.rom.common.inverse.check_rom_inverse`
    re-derives it with an independent implementation.
    """
    digest = hashlib.sha256()
    digest.update(REGION_DIGEST_DOMAIN)
    digest.update(f"{key}\n".encode("utf-8"))
    digest.update(f"{payload_bytes}\n{pad_bytes}\n".encode("ascii"))
    digest.update(f"{slot_count}\n{slot_bytes}\n".encode("ascii"))
    for member in members:
        digest.update(f"{member.tensor_id}\n".encode("utf-8"))
        digest.update(
            f"{member.slot}\n{member.offset_bytes}\n{member.bytes}\n".encode("ascii")
        )
        digest.update(f"{member.source_sha256}\n".encode("ascii"))
    digest.update(hashlib.sha256(bytes(pad_bytes)).hexdigest().encode("ascii"))
    digest.update(b"\n")
    return digest.digest()


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class RomImagePlan:
    """A complete immutable-ROM region plan for one product."""

    model_id: str
    product: str
    policy: RomLayoutPolicy
    regions: tuple[RomRegion, ...]
    repair_map: RepairMap
    notes: dict[str, Any] = dc_field(default_factory=dict)

    @property
    def payload_bytes(self) -> int:
        return sum(r.payload_bytes for r in self.regions)

    @property
    def padding_bytes(self) -> int:
        return sum(r.pad_bytes for r in self.regions)

    @property
    def rom_bytes(self) -> int:
        return self.payload_bytes + self.padding_bytes

    @property
    def region_count(self) -> int:
        return len(self.regions)

    @property
    def resource_count(self) -> int:
        return len(self.repair_map.banks)

    @property
    def largest_region_bytes(self) -> int:
        return max((r.total_bytes for r in self.regions), default=0)

    def region(self, key: str) -> RomRegion:
        for candidate in self.regions:
            if candidate.key == key:
                return candidate
        raise RomImageError(f"no ROM region named {key!r}")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "layout": {
                "address_unit": "byte",
                "alignment_bytes": self.policy.alignment_bytes,
                "base_address": self.policy.base_address,
                "resource_bytes": self.policy.resource_bytes,
                "row_bytes": self.policy.row_bytes,
            },
            "model_id": self.model_id,
            "notes": dict(sorted(self.notes.items())),
            "product": self.product,
            "regions": [r.to_dict() for r in self.regions],
            "repair_map": self.repair_map.to_dict(),
            "schema": ROM_PLAN_SCHEMA,
            "totals": {
                "largest_region_bytes": self.largest_region_bytes,
                "padding_bytes": self.padding_bytes,
                "payload_bytes": self.payload_bytes,
                "placed_tensor_count": sum(len(r.members) for r in self.regions),
                "region_count": self.region_count,
                "resource_count": self.resource_count,
                "rom_bytes": self.rom_bytes,
            },
        }
        body["plan_id"] = hashlib.sha256(canonical_json(body)).hexdigest()
        return body


def plan_rom_image(
    *,
    model_id: str,
    product: str,
    requests: Sequence[RegionRequest],
    policy: RomLayoutPolicy,
    defects: Sequence[DefectRecord] = (),
    notes: Mapping[str, Any] | None = None,
) -> RomImagePlan:
    """Lay out ``requests`` into aligned, sharded, digest-bound ROM regions."""
    policy.validate()
    seen_keys: set[str] = set()
    placed: dict[str, str] = {}
    regions: list[RomRegion] = []
    # Cursor per placement resource, so shards never overlap.
    cursor: dict[tuple[int, int, int, int], int] = {}
    resources: dict[tuple[int, int, int, int], RomCoordinate] = {}

    for index, request in enumerate(requests):
        if request.key in seen_keys:
            raise RomImageError(f"duplicate ROM region key {request.key!r}")
        seen_keys.add(request.key)
        if not request.slots:
            raise RomImageError(f"ROM region {request.key!r} places no payload")
        if request.dtype not in DTYPE_BY_NAME:
            raise RomImageError(
                f"ROM region {request.key!r} has unrepresentable dtype "
                f"{request.dtype!r}"
            )
        slot_bytes = request.slots[0].bytes
        if slot_bytes <= 0:
            raise RomImageError(f"ROM region {request.key!r} has an empty slot")
        for slot_index, member in enumerate(request.slots):
            if member.bytes != slot_bytes:
                raise RomImageError(
                    f"ROM region {request.key!r} slot {slot_index} is "
                    f"{member.bytes} bytes but slot 0 is {slot_bytes}; a "
                    "loop-addressed region needs a constant stride"
                )
            if member.slot != slot_index:
                raise RomImageError(
                    f"ROM region {request.key!r} slot {slot_index} declares slot "
                    f"{member.slot}"
                )
            if member.tensor_id in placed:
                raise RomImageError(
                    f"tensor {member.tensor_id!r} is placed twice: in "
                    f"{placed[member.tensor_id]!r} and {request.key!r}"
                )
            placed[member.tensor_id] = request.key
            expected = slot_index * slot_bytes
            if member.offset_bytes != expected:
                raise RomImageError(
                    f"ROM region {request.key!r} slot {slot_index} sits at "
                    f"{member.offset_bytes}, expected {expected}"
                )

        payload_bytes = slot_bytes * len(request.slots)
        total = _align_up(payload_bytes, policy.alignment_bytes)
        pad_bytes = total - payload_bytes

        shards, coordinate = _shard(
            request=request,
            total_bytes=total,
            payload_bytes=payload_bytes,
            policy=policy,
            cursor=cursor,
            resources=resources,
        )
        base_address = shards[0].resource_address
        regions.append(
            RomRegion(
                region_id=index,
                key=request.key,
                role=request.role,
                dtype=request.dtype,
                coordinate=coordinate,
                base_address=base_address,
                payload_bytes=payload_bytes,
                pad_bytes=pad_bytes,
                alignment=policy.alignment_bytes,
                slot_count=len(request.slots),
                slot_bytes=slot_bytes,
                slot_elements=request.element_count_per_slot,
                members=tuple(request.slots),
                shards=shards,
                content_digest=region_content_digest(
                    key=request.key,
                    payload_bytes=payload_bytes,
                    pad_bytes=pad_bytes,
                    slot_count=len(request.slots),
                    slot_bytes=slot_bytes,
                    members=request.slots,
                ),
                pad_digest=_sha256(bytes(pad_bytes)),
            )
        )

    repair_map = plan_repair_map(regions, policy, defects)
    quarantined = {q.coordinate.resource_id for q in repair_map.quarantine}
    for region in regions:
        for shard in region.shards:
            if shard.coordinate.resource_id in quarantined:
                raise RomImageError(
                    f"ROM region {region.key!r} is placed on quarantined resource "
                    f"{shard.coordinate.resource_id}; recompile against the "
                    "degraded topology"
                )
    return RomImagePlan(
        model_id=model_id,
        product=product,
        policy=policy,
        regions=tuple(regions),
        repair_map=repair_map,
        notes=dict(notes or {}),
    )


def _shard(
    *,
    request: RegionRequest,
    total_bytes: int,
    payload_bytes: int,
    policy: RomLayoutPolicy,
    cursor: dict[tuple[int, int, int, int], int],
    resources: dict[tuple[int, int, int, int], RomCoordinate],
) -> tuple[tuple[RomShard, ...], RomCoordinate]:
    """Place ``total_bytes`` starting at the hinted resource, spilling forward.

    A region larger than one placement resource is distributed: successive
    resources (the next tile, then the next reticle) take the remainder.  The
    shard table is the per-tile coordinate record the wafer topology binds by
    digest.
    """
    hint = request.coordinate_hint
    coordinate = hint
    shards: list[RomShard] = []
    remaining = total_bytes
    offset = 0
    tile = hint.tile
    reticle = hint.reticle
    bank = hint.bank
    guard = 0
    while remaining:
        guard += 1
        if guard > 1 << 22:
            raise RomImageError(f"ROM region {request.key!r} failed to place")
        here = RomCoordinate(
            node_id=hint.node_id, reticle=reticle, tile=tile, bank=bank
        )
        rid = here.resource_id
        resources.setdefault(rid, here)
        start = cursor.get(rid, policy.base_address)
        start = _align_up(start, policy.alignment_bytes)
        room = policy.base_address + policy.resource_bytes - start
        if room <= 0:
            tile += 1
            bank += 1
            continue
        take = min(room, remaining)
        if not shards:
            coordinate = here
        shards.append(
            RomShard(
                coordinate=here,
                region_offset=offset,
                bytes=take,
                resource_address=start,
            )
        )
        cursor[rid] = start + take
        offset += take
        remaining -= take
        if remaining:
            tile += 1
            bank += 1
    # The trailing pad belongs to the last shard; the payload never straddles
    # the pad boundary because the pad is always the region tail.
    if payload_bytes > total_bytes:  # pragma: no cover - defensive
        raise RomImageError("payload exceeds the aligned region size")
    return tuple(shards), coordinate


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def region_object_source(region: RomRegion) -> ObjectSource:
    """The zero-copy source for a region: byte ranges of the checkpoint.

    No ROM image file is produced.  Each member contributes exactly one
    authenticated segment; the manifest binds the segment's SHA-256, so the
    bytes the device reads are the bytes the checkpoint lock authenticated.
    """
    segments = tuple(
        Segment(
            path=member.source_path,
            offset=member.source_offset,
            bytes=member.bytes,
            sha256=member.source_sha256,
        )
        for member in region.members
    )
    return ObjectSource("segments", region.payload_bytes, segments)


def emit_rom_objects(
    builder: DeploymentBuilder,
    plan: RomImagePlan,
    *,
    storage_class: StorageClass = StorageClass.ROM,
    permissions: int = ROM_PERMISSIONS,
) -> dict[str, int]:
    """Emit one immutable memory object per region, plus its zero pad object.

    ``storage_class`` is a parameter for exactly one reason: it lets a test
    build the identical program against HBM and diff the two deployments, which
    is the mechanical form of the "differ only in storage class, placement and
    topology" requirement.  Production ROM builds always pass ``ROM``.
    """
    if permissions & (Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT):
        raise RomImageError(
            "an immutable ROM object must not declare a write permission"
        )
    alignment_log2 = plan.policy.alignment_bytes.bit_length() - 1
    ids: dict[str, int] = {}
    for region in plan.regions:
        object_id = builder.memory_object(
            storage_class=storage_class,
            size_bytes=region.payload_bytes,
            source=region_object_source(region),
            permissions=permissions,
            node_id=region.coordinate.node_id,
            bank_or_tile=_bank_or_tile(region.coordinate),
            base_address=region.base_address,
            alignment_log2=alignment_log2,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=region.content_digest,
            key=region.key,
        )
        region.object_id = object_id
        ids[region.key] = object_id
        if region.pad_bytes:
            pad_id = builder.memory_object(
                storage_class=storage_class,
                size_bytes=region.pad_bytes,
                source=ObjectSource.zeros(region.pad_bytes),
                permissions=permissions,
                node_id=region.coordinate.node_id,
                bank_or_tile=_bank_or_tile(region.coordinate),
                base_address=region.base_address + region.payload_bytes,
                alignment_log2=0,
                integrity_mode=IntegrityMode.CRC_AND_ECC,
                content_digest=region.pad_digest,
                key=f"{region.key}.pad",
            )
            region.pad_object_id = pad_id
            ids[f"{region.key}.pad"] = pad_id
    return ids


def _bank_or_tile(coordinate: RomCoordinate) -> int:
    """Pack the placement resource into the descriptor's 16-bit field.

    ABI 3.0's memory object carries one ``bank_or_tile`` value.  The full
    (node, reticle, tile, bank) coordinate and the per-shard table live in the
    region plan, which the deployment manifest binds by digest.
    """
    value = coordinate.tile if coordinate.tile else coordinate.bank
    if not 0 <= value < NO_NODE:
        raise RomImageError(
            f"placement resource {coordinate.resource_id} does not fit the "
            "16-bit bank_or_tile field"
        )
    return value


__all__ = [
    "BankGeometry",
    "DTYPE_BY_NAME",
    "DefectRecord",
    "QuarantineEntry",
    "RegionRequest",
    "RepairEntry",
    "RepairMap",
    "ROM_PERMISSIONS",
    "ROM_PLAN_SCHEMA",
    "RomCoordinate",
    "RomImageError",
    "RomImagePlan",
    "RomLayoutPolicy",
    "RomMember",
    "RomRegion",
    "RomShard",
    "emit_rom_objects",
    "plan_repair_map",
    "plan_rom_image",
    "region_content_digest",
    "region_object_source",
]
