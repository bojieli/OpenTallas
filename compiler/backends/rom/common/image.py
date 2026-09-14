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
from typing import Any, Callable, Iterable, Mapping, Sequence

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
    #: How a region that overflows one placement resource finds the next one.
    #: The default walks banks on a conventional chip; the wafer product
    #: supplies one that walks tiles and wraps into the next reticle.
    advance_resource: "Callable[[RomCoordinate], RomCoordinate] | None" = None
    #: Optional per-request shard stride: the most bytes one shard of the
    #: request may take before the walker moves to the next resource.  The
    #: array product sets it to exactly one owner's experts, so every shard of
    #: an expert bank is one node's contiguous expert range.
    shard_bytes: "Callable[[RegionRequest], int | None] | None" = None
    #: Optional explicit placement of shard ``k`` of a request.  It receives
    #: the request, the shard index and the walker's live cursor (resource id
    #: -> bytes used) and returns the resource that shard lands on, which must
    #: have room; with it set, ``advance_resource`` is not consulted for that
    #: request.  The array product uses it to put shard ``k`` on node ``k mod
    #: N`` -- consecutive expert ownership -- on that node's first bank with
    #: room.
    place_shard: (
        "Callable[[RegionRequest, int, Mapping[tuple[int, int, int, int], int]],"
        " RomCoordinate] | None"
    ) = None

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
class ResidentHbmPolicy:
    """How a target holds its load-once resident HBM regions.

    A resident region is model content the machine reads every token and never
    writes, whose declared home is HBM rather than the ROM image.  It is not a
    hole in the immutable image: it keeps the region record, the content-digest
    rule, the inverse proof and the immutable READ-only object; what changes is
    the storage class and the placement.

    ``node_shards`` is the whole rule for how the bytes reach the machine.  One
    means every node holds the same image -- the wafer product's wafer-edge
    copy.  ``N`` means the region is row-sharded across ``N`` nodes and each
    node holds its own contiguous rows, which is the only admissible node-local
    form for a table larger than one node's HBM.  A shard must be a whole
    number of the region's addressing rows: a row split across two nodes has no
    owner.
    """

    #: Tensor ids whose regions are resident rather than ROM.  Derived by the
    #: backend from the graph's own structure; this policy only carries it.
    tensors: frozenset[str] = frozenset()
    #: Node images the region is split into (see the class docstring).
    node_shards: int = 1
    #: The node that holds an unsharded resident region, or ``NO_NODE`` when
    #: every node holds the same copy.
    node_id: int = NO_NODE
    #: Bytes of resident region one node declares, from the capability.  Zero
    #: means the target declares no resident region and none may be planned.
    declared_bytes_per_node: int = 0
    #: Region base alignment inside a node's resident window, for a region
    #: with no row structure of its own.  A region that *has* an addressing row
    #: is aligned to that row instead, because the row is the granularity the
    #: machine reads a resident table at and a row-aligned base is what a row
    #: lookup needs.  It is also the only alignment that does not inflate the
    #: reserve: a ROM region pads to the macro row because every byte of the
    #: mask address space must be a declared immutable object, and a node's HBM
    #: window carries no such obligation, so padding a resident region to 4 KiB
    #: would make the machine reserve bytes the model does not have.
    alignment_bytes: int = 4096

    def validate(self) -> None:
        if self.node_shards < 1:
            raise RomImageError("a resident region needs at least one node image")
        if self.alignment_bytes <= 0 or self.alignment_bytes & (
            self.alignment_bytes - 1
        ):
            raise RomImageError(
                "the resident region alignment must be a positive power of two"
            )
        if self.tensors and self.declared_bytes_per_node <= 0:
            raise RomImageError(
                "a resident HBM region was requested and the capability declares "
                "no resident region; the bytes would have no declared home"
            )


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

    A region is ``slot_count`` slots of ``slot_bytes`` each.  A slot is what one
    iteration of a compressed loop reads: usually one layer's copy of one
    operand, but for a routed MoE weight it is a whole expert bank -- every
    expert's matrix for that layer, in ascending logical expert order.  Slots
    must be equal-sized, or the loop stride would not be constant and one
    dynamic term could not reach every slot.
    """

    key: str
    role: str
    dtype: str
    members: tuple[RomMember, ...]
    slot_count: int
    slot_bytes: int
    element_count_per_slot: int
    coordinate_hint: RomCoordinate = RomCoordinate()
    #: The indivisible addressing row of this payload, in bytes, when it has
    #: one: a lookup table's row is read whole, so a shard boundary that fell
    #: inside one would make a single lookup two reads and would leave the
    #: row's owner undefined.  Derived by the caller from the operand's own
    #: trailing extent and element type -- never written down -- and ``0``
    #: when the payload has no row structure the planner must respect.
    row_bytes: int = 0

    @staticmethod
    def striped(
        key: str,
        role: str,
        dtype: str,
        slots: Sequence[Sequence[tuple[str, int, str, int, str]]],
        element_count_per_slot: int,
        coordinate_hint: "RomCoordinate | None" = None,
        row_bytes: int = 0,
    ) -> "RegionRequest":
        """Build a request from per-slot ``(tensor_id, bytes, path, offset, sha)``."""
        members: list[RomMember] = []
        cursor = 0
        slot_bytes = sum(entry[1] for entry in slots[0]) if slots else 0
        for index, entries in enumerate(slots):
            total = sum(entry[1] for entry in entries)
            if total != slot_bytes:
                raise RomImageError(
                    f"ROM region {key!r} slot {index} is {total} bytes but slot 0 "
                    f"is {slot_bytes}; a loop-addressed region needs a constant "
                    "stride"
                )
            for tensor_id, extent, path, offset, digest in entries:
                members.append(
                    RomMember(
                        tensor_id=tensor_id,
                        slot=index,
                        offset_bytes=cursor,
                        bytes=extent,
                        source_path=path,
                        source_offset=offset,
                        source_sha256=digest,
                        dtype=dtype,
                    )
                )
                cursor += extent
        return RegionRequest(
            key=key,
            role=role,
            dtype=dtype,
            members=tuple(members),
            slot_count=len(slots),
            slot_bytes=slot_bytes,
            element_count_per_slot=element_count_per_slot,
            coordinate_hint=coordinate_hint or RomCoordinate(),
            row_bytes=int(row_bytes),
        )


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
    #: ``"rom"`` for a region of the immutable ROM image, ``"hbm"`` for a
    #: load-once resident region: bytes the machine reads from HBM every token
    #: and never writes.  A resident region is the same first-class, checked,
    #: digest-bound record as a ROM one -- the same members, the same content
    #: digest rule, the same inverse proof -- and differs in exactly where the
    #: bytes live, so its ``shards`` name a node and an offset in that node's
    #: resident window instead of a bank and a ROM address.
    residency: str = "rom"
    #: The region's indivisible addressing row, carried through from the
    #: request so the shard rule and the plan record state the same number.
    row_bytes: int = 0
    #: Node images this region is split into: ``1`` when every node holds the
    #: same bytes, ``shards`` when it is row-sharded across the machine.
    node_shards: int = 1

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
        body = {
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
        if self.residency != "rom":
            # Only a resident region states these.  A ROM-only plan's record --
            # and therefore its plan id and the deployment digest that binds it
            # -- is exactly what it was before residency existed.
            body["node_shards"] = self.node_shards
            body["residency"] = self.residency
            body["row_bytes"] = self.row_bytes
        return body


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
    "fp4_e2m1_s16_e4m3": DType.FP4_E2M1_S16_E4M3,
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
    #: Load-once regions whose declared residency is HBM, not the ROM image.
    #: They are *not* in ``regions``: ``rom_bytes`` is the image the mask
    #: carries, and counting a byte in both is the double count this field
    #: exists to make impossible.
    resident_regions: tuple[RomRegion, ...] = ()

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
    def resident_payload_bytes(self) -> int:
        return sum(r.payload_bytes for r in self.resident_regions)

    @property
    def resident_padding_bytes(self) -> int:
        return sum(r.pad_bytes for r in self.resident_regions)

    @property
    def resident_bytes(self) -> int:
        return self.resident_payload_bytes + self.resident_padding_bytes

    @property
    def resident_bytes_per_node(self) -> dict[int, int]:
        """Resident bytes each node holds, keyed by node id.

        A node-sharded region contributes its own shard to its own node; an
        unsharded one contributes to every node that holds a copy, which for
        ``NO_NODE`` is the machine and is reported under that key.
        """
        used: dict[int, int] = {}
        for region in self.resident_regions:
            for shard in region.shards:
                node = shard.coordinate.node_id
                used[node] = max(
                    used.get(node, 0), shard.resource_address + shard.bytes
                )
        return dict(sorted(used.items()))

    @property
    def resident_bytes_worst_node(self) -> int:
        return max(self.resident_bytes_per_node.values(), default=0)

    @property
    def region_count(self) -> int:
        return len(self.regions)

    @property
    def resource_count(self) -> int:
        return len(self.repair_map.banks)

    @property
    def largest_region_bytes(self) -> int:
        return max((r.total_bytes for r in self.regions), default=0)

    @property
    def largest_member_bytes(self) -> int:
        """The largest *indivisible* payload: one tensor's bytes.

        A region may be distributed over many placement resources, so region
        size is not a capacity constraint.  What must fit is the smallest thing
        the plan will not split further, which is one checkpoint tensor.
        """
        return max(
            (m.bytes for r in self.regions for m in r.members), default=0
        )

    @property
    def distributed_member_count(self) -> int:
        """Members larger than one placement resource, i.e. tensor-parallel."""
        limit = self.policy.resource_bytes
        return sum(
            1 for r in self.regions for m in r.members if m.bytes > limit
        )

    def region(self, key: str) -> RomRegion:
        for candidate in (*self.regions, *self.resident_regions):
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
                "distributed_member_count": self.distributed_member_count,
                "largest_member_bytes": self.largest_member_bytes,
                "largest_region_bytes": self.largest_region_bytes,
                "padding_bytes": self.padding_bytes,
                "payload_bytes": self.payload_bytes,
                "placed_tensor_count": sum(len(r.members) for r in self.regions),
                "region_count": self.region_count,
                "resource_count": self.resource_count,
                "rom_bytes": self.rom_bytes,
            },
        }
        if self.resident_regions:
            # Conditional on purpose.  A product with no resident region emits
            # exactly the record it emitted before residency existed, so its
            # plan id -- and the deployment digest that binds it -- cannot move.
            body["resident_regions"] = [r.to_dict() for r in self.resident_regions]
            body["totals"]["resident_bytes"] = self.resident_bytes
            body["totals"]["resident_bytes_per_node"] = {
                str(node): used
                for node, used in self.resident_bytes_per_node.items()
            }
            body["totals"]["resident_padding_bytes"] = self.resident_padding_bytes
            body["totals"]["resident_payload_bytes"] = self.resident_payload_bytes
            body["totals"]["resident_region_count"] = len(self.resident_regions)
        body["plan_id"] = hashlib.sha256(canonical_json(body)).hexdigest()
        return body


def _validate_region_request(
    request: RegionRequest,
    seen_keys: set[str],
    placed: dict[str, str],
) -> int:
    """Check one request's members tile its slots, and return its payload bytes.

    Shared by the ROM image and the resident HBM regions on purpose: a resident
    region is held to the identical tiling, slot-stride and place-once rules,
    because the only thing residency changes is where the bytes live.
    """
    if request.key in seen_keys:
        raise RomImageError(f"duplicate ROM region key {request.key!r}")
    seen_keys.add(request.key)
    if not request.members:
        raise RomImageError(f"ROM region {request.key!r} places no payload")
    if request.dtype not in DTYPE_BY_NAME:
        raise RomImageError(
            f"ROM region {request.key!r} has unrepresentable dtype "
            f"{request.dtype!r}"
        )
    slot_bytes = request.slot_bytes
    if slot_bytes <= 0 or request.slot_count <= 0:
        raise RomImageError(f"ROM region {request.key!r} has an empty slot")
    covered = 0
    for member in request.members:
        if member.bytes <= 0:
            raise RomImageError(
                f"ROM region {request.key!r} member {member.tensor_id!r} is empty"
            )
        if member.offset_bytes != covered:
            raise RomImageError(
                f"ROM region {request.key!r} member {member.tensor_id!r} sits at "
                f"{member.offset_bytes}, expected {covered}; members must tile "
                "the region without gaps or overlap"
            )
        if member.slot != member.offset_bytes // slot_bytes:
            raise RomImageError(
                f"ROM region {request.key!r} member {member.tensor_id!r} declares "
                f"slot {member.slot} but sits in slot "
                f"{member.offset_bytes // slot_bytes}"
            )
        if (member.offset_bytes + member.bytes - 1) // slot_bytes != member.slot:
            raise RomImageError(
                f"ROM region {request.key!r} member {member.tensor_id!r} straddles "
                "a slot boundary"
            )
        if member.tensor_id in placed:
            raise RomImageError(
                f"tensor {member.tensor_id!r} is placed twice: in "
                f"{placed[member.tensor_id]!r} and {request.key!r}"
            )
        placed[member.tensor_id] = request.key
        covered += member.bytes
    if covered != slot_bytes * request.slot_count:
        raise RomImageError(
            f"ROM region {request.key!r} members cover {covered} bytes but "
            f"{request.slot_count} slots of {slot_bytes} need "
            f"{slot_bytes * request.slot_count}"
        )
    return slot_bytes * request.slot_count


def plan_resident_regions(
    *,
    requests: Sequence[RegionRequest],
    policy: ResidentHbmPolicy,
    seen_keys: set[str],
    placed: dict[str, str],
    first_region_id: int,
) -> tuple[RomRegion, ...]:
    """Lay out the load-once resident HBM regions of one deployment.

    The rules a resident region is held to, all of them checkable from the
    emitted record by :func:`~compiler.backends.rom.common.inverse.check_rom_inverse`:

    *   its members tile its slots exactly, as a ROM region's do;
    *   its shards tile the region in order and do not overlap inside a node's
        resident window, as a ROM region's do inside a bank;
    *   a sharded region's node image is a whole number of addressing rows, so
        one lookup is one node's read and the row has an owner; and
    *   every node's image is the same size, because ABI 3.0's MEMORY_OBJECT is
        symmetric -- one object id and one node-local size for every node.
    """
    policy.validate()
    regions: list[RomRegion] = []
    shards_count = int(policy.node_shards)
    cursor: dict[int, int] = {}
    # Packed in descending alignment order, then by key.  A node's resident
    # window is one allocation, and laying a strictly-aligned region after a
    # loosely-aligned one makes its base skip the tail: for the released model
    # that is 64 bytes, which is 64 bytes of HBM the machine would have to
    # reserve beyond the table it holds.  Sorting is deterministic and changes
    # only the order bytes are packed in, never which region owns them.
    ordered = sorted(
        requests,
        key=lambda request: (
            -(int(request.row_bytes) or policy.alignment_bytes),
            request.key,
        ),
    )
    for offset, request in enumerate(ordered):
        payload_bytes = _validate_region_request(request, seen_keys, placed)
        row = int(request.row_bytes)
        alignment = row or policy.alignment_bytes
        if row and payload_bytes % row:
            raise RomImageError(
                f"resident region {request.key!r} of {payload_bytes} bytes is "
                f"not a whole number of its {row}-byte addressing rows"
            )
        total = _align_up(payload_bytes, alignment)
        pad_bytes = total - payload_bytes
        if shards_count > 1:
            if payload_bytes % shards_count:
                raise RomImageError(
                    f"resident region {request.key!r} of {payload_bytes} bytes "
                    f"does not divide into {shards_count} equal node images; ABI "
                    "3.0's MEMORY_OBJECT states one node-local size for every "
                    "node"
                )
            per_node = payload_bytes // shards_count
            row = int(request.row_bytes)
            if row and per_node % row:
                raise RomImageError(
                    f"resident region {request.key!r} shards into {per_node} "
                    f"bytes a node, which is not a whole number of its "
                    f"{row}-byte addressing rows; a row split across two nodes "
                    "has no owner"
                )
            if pad_bytes:
                raise RomImageError(
                    f"resident region {request.key!r} needs {pad_bytes} pad bytes "
                    f"and is sharded {shards_count} ways; a sharded region's pad "
                    "would sit on one node and break the symmetric node image"
                )
            nodes = range(shards_count)
        else:
            per_node = total
            nodes = (int(policy.node_id),)
        shards: list[RomShard] = []
        region_offset = 0
        for node in nodes:
            start = _align_up(cursor.get(node, 0), alignment)
            extent = per_node if shards_count > 1 else total
            shards.append(
                RomShard(
                    coordinate=RomCoordinate(node_id=node),
                    region_offset=region_offset,
                    bytes=extent,
                    resource_address=start,
                )
            )
            cursor[node] = start + extent
            if shards_count > 1:
                region_offset += extent
        if len({shard.resource_address for shard in shards}) != 1:
            # ABI 3.0's MEMORY_OBJECT carries ONE base address for every node,
            # so a sharded region has to sit at the same offset in every node's
            # resident window.  It does by construction -- every node takes the
            # same extent from every region, in the same order -- and this is
            # the assertion that keeps a future placement rule from quietly
            # breaking it.
            raise RomImageError(
                f"resident region {request.key!r} lands at different offsets on "
                "different nodes; the symmetric MEMORY_OBJECT states one base "
                "address for every node"
            )
        regions.append(
            RomRegion(
                region_id=first_region_id + offset,
                key=request.key,
                role=request.role,
                dtype=request.dtype,
                coordinate=shards[0].coordinate,
                base_address=shards[0].resource_address,
                payload_bytes=payload_bytes,
                pad_bytes=pad_bytes,
                alignment=alignment,
                slot_count=request.slot_count,
                slot_bytes=request.slot_bytes,
                slot_elements=request.element_count_per_slot,
                members=request.members,
                shards=tuple(shards),
                content_digest=region_content_digest(
                    key=request.key,
                    payload_bytes=payload_bytes,
                    pad_bytes=pad_bytes,
                    slot_count=request.slot_count,
                    slot_bytes=request.slot_bytes,
                    members=request.members,
                ),
                pad_digest=_sha256(bytes(pad_bytes)),
                residency="hbm",
                row_bytes=int(request.row_bytes),
                node_shards=shards_count,
            )
        )
    worst = max(
        (
            max(
                (s.resource_address + s.bytes for s in region.shards),
                default=0,
            )
            for region in regions
        ),
        default=0,
    )
    if worst > policy.declared_bytes_per_node:
        raise RomImageError(
            f"the load-once resident HBM regions need {worst} bytes on one node "
            f"and the capability declares a resident region of "
            f"{policy.declared_bytes_per_node}"
        )
    return tuple(regions)


def plan_rom_image(
    *,
    model_id: str,
    product: str,
    requests: Sequence[RegionRequest],
    policy: RomLayoutPolicy,
    defects: Sequence[DefectRecord] = (),
    notes: Mapping[str, Any] | None = None,
    resident_requests: Sequence[RegionRequest] = (),
    resident_policy: "ResidentHbmPolicy | None" = None,
) -> RomImagePlan:
    """Lay out ``requests`` into aligned, sharded, digest-bound ROM regions.

    ``resident_requests`` are the load-once regions whose declared home is HBM.
    They are planned by :func:`plan_resident_regions` into a separate list and
    are deliberately *not* part of ``rom_bytes``: the whole point of the split
    is that a byte priced in the capability's resident HBM region is not also a
    byte of the mask image.
    """
    policy.validate()
    seen_keys: set[str] = set()
    placed: dict[str, str] = {}
    regions: list[RomRegion] = []
    # Cursor per placement resource, so shards never overlap.
    cursor: dict[tuple[int, int, int, int], int] = {}
    resources: dict[tuple[int, int, int, int], RomCoordinate] = {}

    for index, request in enumerate(requests):
        payload_bytes = _validate_region_request(request, seen_keys, placed)
        slot_bytes = request.slot_bytes
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
                slot_count=request.slot_count,
                slot_bytes=slot_bytes,
                slot_elements=request.element_count_per_slot,
                members=request.members,
                shards=shards,
                content_digest=region_content_digest(
                    key=request.key,
                    payload_bytes=payload_bytes,
                    pad_bytes=pad_bytes,
                    slot_count=request.slot_count,
                    slot_bytes=slot_bytes,
                    members=request.members,
                ),
                pad_digest=_sha256(bytes(pad_bytes)),
            )
        )

    resident_regions: tuple[RomRegion, ...] = ()
    if resident_requests:
        if resident_policy is None:
            raise RomImageError(
                "resident HBM regions were requested and the target declares no "
                "resident placement policy"
            )
        resident_regions = plan_resident_regions(
            requests=resident_requests,
            policy=resident_policy,
            seen_keys=seen_keys,
            placed=placed,
            first_region_id=len(regions),
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
        resident_regions=resident_regions,
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
    advance = policy.advance_resource or _next_resource
    stride = policy.shard_bytes(request) if policy.shard_bytes is not None else None
    if stride is not None and stride <= 0:
        raise RomImageError(f"ROM region {request.key!r} declares a non-positive shard stride")
    placer = policy.place_shard
    here = hint
    guard = 0
    while remaining:
        guard += 1
        if guard > 1 << 22:
            raise RomImageError(f"ROM region {request.key!r} failed to place")
        if placer is not None:
            here = placer(request, len(shards), cursor)
        rid = here.resource_id
        resources.setdefault(rid, here)
        start = _align_up(cursor.get(rid, policy.base_address), policy.alignment_bytes)
        room = policy.base_address + policy.resource_bytes - start
        if room <= 0:
            if placer is not None:
                raise RomImageError(
                    f"ROM region {request.key!r} shard {len(shards)} was placed on "
                    f"resource {rid}, which has no room"
                )
            here = advance(here)
            continue
        take = min(room, remaining) if stride is None else min(room, remaining, stride)
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
        if remaining and placer is None:
            here = advance(here)
    # The trailing pad belongs to the last shard; the payload never straddles
    # the pad boundary because the pad is always the region tail.
    if payload_bytes > total_bytes:  # pragma: no cover - defensive
        raise RomImageError("payload exceeds the aligned region size")
    return tuple(shards), coordinate


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def _next_resource(coordinate: RomCoordinate) -> RomCoordinate:
    """Default spill order for a conventional chip: the next ROM bank."""
    return RomCoordinate(
        node_id=coordinate.node_id,
        reticle=coordinate.reticle,
        tile=coordinate.tile,
        bank=coordinate.bank + 1,
    )


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


def node_sharded_region_source(region: RomRegion, shards: int) -> ObjectSource:
    """A28 ``node_segments`` source for a region split ``shards`` ways by owner.

    Node ``k`` holds members ``[k*E/N, (k+1)*E/N)`` of *every* slot, in slot
    order: the node-local image is the region with the other nodes' experts
    removed, so a local slot stride is the global one divided by ``shards`` and
    the routed engine's consecutive-ownership rule (local expert ``e`` is global
    ``k*E/N + e``) reads it directly.  Every node's image is the same size.
    """
    if shards <= 1:
        return region_object_source(region)
    per_slot = len(region.members) // max(region.slot_count, 1)
    if per_slot * region.slot_count != len(region.members) or per_slot % shards:
        raise RomImageError(
            f"ROM region {region.key!r} has {len(region.members)} members over "
            f"{region.slot_count} slots and cannot be split {shards} ways by owner"
        )
    if region.payload_bytes % shards:
        raise RomImageError(
            f"ROM region {region.key!r} payload {region.payload_bytes} is not "
            f"divisible into {shards} equal node images"
        )
    owned = per_slot // shards
    ordered = sorted(region.members, key=lambda m: m.offset_bytes)
    node_segments: list[tuple[Segment, ...]] = []
    for node in range(shards):
        segments: list[Segment] = []
        for slot in range(region.slot_count):
            base = slot * per_slot + node * owned
            for member in ordered[base : base + owned]:
                segments.append(
                    Segment(
                        path=member.source_path,
                        offset=member.source_offset,
                        bytes=member.bytes,
                        sha256=member.source_sha256,
                    )
                )
        node_segments.append(tuple(segments))
    local = region.payload_bytes // shards
    for node, segments in enumerate(node_segments):
        if sum(s.bytes for s in segments) != local:
            raise RomImageError(
                f"ROM region {region.key!r} node {node} image covers "
                f"{sum(s.bytes for s in segments)} bytes, expected {local}; the "
                "members of one slot are not equal-sized"
            )
    return ObjectSource("node_segments", local, node_segments=tuple(node_segments))


def row_sharded_region_source(
    region: RomRegion,
    shards: int,
    *,
    shard_digests: "Mapping[tuple[int, int], str] | None" = None,
) -> ObjectSource:
    """A28 ``node_segments`` source for a region split by *rows* across nodes.

    ``node_sharded_region_source`` splits a region by whole *members*, which is
    what a routed expert bank is: one member per expert.  A lookup table is one
    member per slot and is divided inside it, so this splits each slot's byte
    range into ``shards`` equal contiguous pieces, each a whole number of the
    region's addressing rows.  The order is the region's own -- slot-major,
    owner-minor -- which is the order
    :func:`compiler.backends.rom.common.inverse._object_segments` reconstructs
    a node-sharded object in, so the two derivations meet on the same bytes.
    """
    if shards <= 1:
        return region_object_source(region)
    slot_count = max(region.slot_count, 1)
    if len(region.members) != slot_count:
        raise RomImageError(
            f"resident region {region.key!r} has {len(region.members)} members "
            f"over {slot_count} slots; a row-sharded table is one member a slot"
        )
    if region.slot_bytes % shards:
        raise RomImageError(
            f"resident region {region.key!r} slot of {region.slot_bytes} bytes "
            f"does not divide into {shards} equal node images"
        )
    per_node_per_slot = region.slot_bytes // shards
    row = int(region.row_bytes)
    if row and per_node_per_slot % row:
        raise RomImageError(
            f"resident region {region.key!r} would give a node "
            f"{per_node_per_slot} bytes of a {row}-byte row table"
        )
    ordered = sorted(region.members, key=lambda m: m.offset_bytes)
    node_segments: list[tuple[Segment, ...]] = []
    for node in range(shards):
        segments: list[Segment] = []
        for slot, member in enumerate(ordered):
            digest = (shard_digests or {}).get((slot, node))
            if digest is None:
                # A shard of a tensor is a byte range the checkpoint lock does
                # not name: the lock authenticates whole tensors.  An
                # unauthenticated range has no honest content identity, and
                # ``ObjectSource.authenticated_content_digest`` refuses one, so
                # the caller must supply the digest of every shard it asks for.
                raise RomImageError(
                    f"resident region {region.key!r} shard (slot {slot}, node "
                    f"{node}) is a sub-range of tensor {member.tensor_id!r} and "
                    "carries no authenticated digest; the checkpoint lock names "
                    "whole tensors, so a row-sharded table must be authenticated "
                    "range by range from the checkpoint bytes"
                )
            segments.append(
                Segment(
                    path=member.source_path,
                    offset=member.source_offset + node * per_node_per_slot,
                    bytes=per_node_per_slot,
                    sha256=digest,
                )
            )
        node_segments.append(tuple(segments))
    return ObjectSource(
        "node_segments",
        per_node_per_slot * slot_count,
        node_segments=tuple(node_segments),
    )


def emit_rom_objects(
    builder: DeploymentBuilder,
    plan: RomImagePlan,
    *,
    storage_class: StorageClass = StorageClass.ROM,
    permissions: int = ROM_PERMISSIONS,
    node_shards: "Callable[[RomRegion], int | None] | None" = None,
) -> dict[str, int]:
    """Emit one immutable memory object per region, plus its zero pad object.

    ``storage_class`` is a parameter for exactly one reason: it lets a test
    build the identical program against HBM and diff the two deployments, which
    is the mechanical form of the "differ only in storage class, placement and
    topology" requirement.  Production ROM builds always pass ``ROM``.  The
    comparison HBM image deliberately leaves physical placement unresolved:
    ROM bank-local addresses overlap when flattened into one HBM address space,
    so copying those addresses would describe an invalid HBM allocation.  Zero
    plus ``NO_NODE`` is the ABI's explicit legacy/unplaced sentinel and keeps
    this functional comparison from making a fabricated placement claim.
    """
    if permissions & (Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT):
        raise RomImageError(
            "an immutable ROM object must not declare a write permission"
        )
    alignment_log2 = plan.policy.alignment_bytes.bit_length() - 1
    placed_in_rom = storage_class == StorageClass.ROM
    ids: dict[str, int] = {}
    for region in plan.regions:
        shards = node_shards(region) if node_shards is not None else None
        if shards and shards > 1 and placed_in_rom:
            # One node-local object: node ``k`` materialises its own owner
            # range and every node sees the same local size.  The physical
            # per-node shard coordinates live in the region plan.
            source = node_sharded_region_source(region, shards)
            size_bytes = region.payload_bytes // shards
            node_id = NO_NODE
        else:
            source = region_object_source(region)
            size_bytes = region.payload_bytes
            node_id = region.coordinate.node_id
        object_id = builder.memory_object(
            storage_class=storage_class,
            size_bytes=size_bytes,
            source=source,
            permissions=permissions,
            node_id=node_id,
            bank_or_tile=(
                _bank_or_tile(region.coordinate) if placed_in_rom else NO_NODE
            ),
            base_address=region.base_address if placed_in_rom else 0,
            alignment_log2=alignment_log2,
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=source.authenticated_content_digest(),
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
                bank_or_tile=(
                    _bank_or_tile(region.coordinate) if placed_in_rom else NO_NODE
                ),
                base_address=(
                    region.base_address + region.payload_bytes
                    if placed_in_rom
                    else 0
                ),
                alignment_log2=0,
                integrity_mode=IntegrityMode.CRC_AND_ECC,
                content_digest=bytes(32),
                key=f"{region.key}.pad",
            )
            region.pad_object_id = pad_id
            ids[f"{region.key}.pad"] = pad_id
    ids.update(
        emit_resident_hbm_objects(builder, plan, permissions=permissions)
    )
    return ids


def emit_resident_hbm_objects(
    builder: DeploymentBuilder,
    plan: RomImagePlan,
    *,
    permissions: int = ROM_PERMISSIONS,
) -> dict[str, int]:
    """Emit one immutable HBM memory object per resident region, plus its pad.

    The storage class is the only thing that differs from a ROM region's
    object.  The permissions are the same ``READ | IMMUTABLE`` -- load once,
    never written, never committed to -- the content digest binds the same
    ordered authenticated segments, and the region record the inverse proof
    reads is the same record.  A resident region is a declared, checked,
    digest-bound part of the deployment whose residency is HBM; it is not a
    hole in the immutable image.
    """
    if permissions & (
        Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT
    ):
        raise RomImageError(
            "a load-once resident object must not declare a write permission"
        )
    ids: dict[str, int] = {}
    for region in plan.resident_regions:
        shards = max(int(region.node_shards), 1)
        if shards > 1:
            source = row_sharded_region_source(region, shards)
            size_bytes = region.payload_bytes // shards
            node_id = NO_NODE
        else:
            source = region_object_source(region)
            size_bytes = region.payload_bytes
            node_id = region.coordinate.node_id
        object_id = builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=size_bytes,
            source=source,
            permissions=permissions,
            node_id=node_id,
            bank_or_tile=NO_NODE,
            base_address=region.base_address,
            alignment_log2=max(region.alignment.bit_length() - 1, 0),
            integrity_mode=IntegrityMode.CRC_AND_ECC,
            content_digest=source.authenticated_content_digest(),
            key=region.key,
        )
        region.object_id = object_id
        ids[region.key] = object_id
        if region.pad_bytes:
            pad_id = builder.memory_object(
                storage_class=StorageClass.HBM,
                size_bytes=region.pad_bytes,
                source=ObjectSource.zeros(region.pad_bytes),
                permissions=permissions,
                node_id=node_id,
                bank_or_tile=NO_NODE,
                base_address=region.base_address + region.payload_bytes,
                alignment_log2=0,
                integrity_mode=IntegrityMode.CRC_AND_ECC,
                content_digest=bytes(32),
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
    "ResidentHbmPolicy",
    "RomShard",
    "emit_resident_hbm_objects",
    "emit_rom_objects",
    "plan_repair_map",
    "plan_resident_regions",
    "plan_rom_image",
    "region_content_digest",
    "region_object_source",
    "row_sharded_region_source",
]
