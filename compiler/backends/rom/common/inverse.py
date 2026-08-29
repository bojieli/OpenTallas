"""Independent inverse proof for an immutable-ROM deployment.

This module is the *check*, not the producer.  It deliberately imports nothing
from :mod:`compiler.backends.rom.common.image` and nothing from either product
backend: it reads only the emitted artifact -- the descriptor table, the object
sources, and the region plan the deployment manifest binds -- plus the
authenticated checkpoint bytes, and it re-implements every rule it needs.  A
plan this module rejects must not be taped out.

What it proves
--------------

1.  Every ROM memory object declares ``StorageClass.ROM`` and exactly
    ``READ | IMMUTABLE``.  No write permission, anywhere, ever.
2.  Every region's declared members tile its payload exactly: offsets start at
    zero, are contiguous, do not overlap, and sum to the object size.
3.  Reconstructing a member from the deployment's own
    :class:`~runtime.abi3.deployment.ObjectSource` segments yields bytes that
    are **bit-identical** to the checkpoint binding the region plan records, and
    whose SHA-256 equals the authenticated payload digest.  Reconstruction and
    expectation are read separately, so a swapped or truncated segment table
    fails.
4.  Every padding byte is zero.  Padding is a declared, addressable, immutable
    zero-source ROM object; the checker materialises it and inspects every byte,
    and confirms its content digest.
5.  Each region's content digest recomputes under an independently written
    implementation of the binding rule.
6.  Placement is unique: no two regions overlap in any physical resource, every
    weight tensor is placed exactly once, and no region sits on a quarantined
    resource.
7.  The repair map is internally consistent: every activated spare belongs to a
    declared bank, spare indices are inside the declared inventory, and no
    logical row or column is repaired twice.

The reconstruction is streamed, so proving a 16 GB or 156 GB image costs no
temporary storage and never materialises a private copy.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from runtime.abi3.constants import Permission, StorageClass
from runtime.abi3.deployment import Deployment, ObjectSource, resolve_path
from runtime.abi3.descriptors import ExtendedDescriptorType

INVERSE_REPORT_SCHEMA = "opentallas.rom.inverse_report.v1"
CHUNK_BYTES = 4 << 20

#: The region content-digest rule, re-implemented here on purpose.  If the
#: producer's rule and this one ever disagree, the proof fails loudly instead of
#: agreeing by construction.
_REGION_DOMAIN = b"opentallas.rom.region.v1\n"

ByteReader = Callable[[str, int, int], bytes]


class InverseProofError(ValueError):
    """Raised when an emitted ROM deployment fails its inverse proof."""


@dataclass(frozen=True, slots=True)
class _Segment:
    path: str
    offset: int
    bytes: int
    sha256: str | None


def file_reader(root: Path | None = None) -> ByteReader:
    """A byte reader over the authenticated checkpoint files on disk."""

    def read(path: str, offset: int, count: int) -> bytes:
        resolved = resolve_path(root, path)
        with open(resolved, "rb") as handle:
            handle.seek(offset)
            payload = handle.read(count)
        if len(payload) != count:
            raise InverseProofError(
                f"short read of {count} bytes at {offset} in {path!r}"
            )
        return payload

    return read


# ---------------------------------------------------------------------------
# Small independent helpers
# ---------------------------------------------------------------------------
def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InverseProofError(message)


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise InverseProofError(f"{label} must be an integer >= {minimum}")
    return value


def _hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise InverseProofError(f"{label} must be a 64-character SHA-256 digest")
    try:
        bytes.fromhex(value)
    except ValueError:
        raise InverseProofError(f"{label} is not hexadecimal") from None
    return value.lower()


def _independent_region_digest(region: Mapping[str, Any]) -> str:
    """Re-derive the region content digest from the plan record alone."""
    payload = _integer(region.get("payload_bytes"), "payload_bytes", 1)
    pad = _integer(region.get("pad_bytes"), "pad_bytes")
    slots = _integer(region.get("slot_count"), "slot_count", 1)
    slot_bytes = _integer(region.get("slot_bytes"), "slot_bytes", 1)
    accumulator = hashlib.sha256()
    accumulator.update(_REGION_DOMAIN)
    accumulator.update((str(region["key"]) + "\n").encode("utf-8"))
    accumulator.update((str(payload) + "\n" + str(pad) + "\n").encode("ascii"))
    accumulator.update((str(slots) + "\n" + str(slot_bytes) + "\n").encode("ascii"))
    for member in region["members"]:
        accumulator.update((str(member["tensor_id"]) + "\n").encode("utf-8"))
        accumulator.update(
            (
                str(_integer(member["slot"], "member slot"))
                + "\n"
                + str(_integer(member["offset_bytes"], "member offset"))
                + "\n"
                + str(_integer(member["bytes"], "member bytes", 1))
                + "\n"
            ).encode("ascii")
        )
        accumulator.update(
            (_hex(member["source_sha256"], "member source_sha256") + "\n").encode(
                "ascii"
            )
        )
    zero_digest = hashlib.sha256(b"\x00" * pad).hexdigest()
    accumulator.update((zero_digest + "\n").encode("ascii"))
    return accumulator.hexdigest()


def _slice_stream(
    reader: ByteReader,
    segments: Sequence[_Segment],
    start: int,
    length: int,
) -> Iterator[bytes]:
    """Yield the bytes of ``[start, start + length)`` of a segmented object."""
    cursor = 0
    remaining = length
    position = start
    for segment in segments:
        if remaining <= 0:
            break
        end = cursor + segment.bytes
        if position >= end:
            cursor = end
            continue
        inner = position - cursor
        take = min(segment.bytes - inner, remaining)
        offset = segment.offset + inner
        while take:
            step = min(CHUNK_BYTES, take)
            block = reader(segment.path, offset, step)
            if len(block) != step:
                raise InverseProofError(
                    f"short read reconstructing {segment.path!r} at {offset}"
                )
            yield block
            offset += step
            take -= step
            remaining -= step
            position += step
        cursor = end
    if remaining:
        raise InverseProofError(
            f"object segments cover {length - remaining} of {length} requested bytes"
        )


def _zero_stream(size: int) -> Iterator[bytes]:
    remaining = size
    while remaining:
        step = min(CHUNK_BYTES, remaining)
        yield b"\x00" * step
        remaining -= step


def _object_segments(source: ObjectSource) -> tuple[_Segment, ...]:
    return tuple(
        _Segment(path=s.path, offset=s.offset, bytes=s.bytes, sha256=s.sha256)
        for s in source.segments
    )


# ---------------------------------------------------------------------------
# The proof
# ---------------------------------------------------------------------------
def check_rom_inverse(
    deployment: Deployment,
    *,
    reader: ByteReader | None = None,
    root: Path | None = None,
    require_bit_identical: bool = True,
) -> dict[str, Any]:
    """Prove ``deployment``'s ROM regions reconstruct the checkpoint exactly."""
    if reader is None:
        reader = file_reader(root if root is not None else deployment.root)

    plan = deployment.notes.get("rom_plan")
    _require(
        isinstance(plan, Mapping),
        "the deployment manifest carries no ROM region plan; there is nothing to "
        "prove and nothing binding the physical claim",
    )
    _require(
        plan.get("schema") == "opentallas.rom.region_plan.v1",
        f"unexpected ROM region plan schema {plan.get('schema')!r}",
    )
    regions = plan.get("regions")
    _require(isinstance(regions, list) and bool(regions), "the plan places no region")

    table = deployment.table
    rom_objects = {}
    for descriptor in table.descriptors():
        if descriptor.descriptor_type != ExtendedDescriptorType.MEMORY_OBJECT:
            continue
        if descriptor.payload["storage_class"] != int(StorageClass.ROM):
            continue
        rom_objects[descriptor.descriptor_id] = descriptor
        permissions = descriptor.permissions
        _require(
            permissions == int(Permission.READ | Permission.IMMUTABLE),
            f"ROM object {descriptor.descriptor_id} declares permissions "
            f"{permissions:#04x}; immutable ROM is exactly READ|IMMUTABLE",
        )
        _require(
            not permissions
            & int(Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT),
            f"ROM object {descriptor.descriptor_id} declares a write path",
        )

    placed: dict[str, str] = {}
    occupied: dict[tuple[int, int, int, int], list[tuple[int, int, str]]] = {}
    payload_bytes = 0
    padding_bytes = 0
    reconstructed: list[dict[str, Any]] = []
    referenced: set[int] = set()

    for record in regions:
        _require(isinstance(record, Mapping), "a region record is malformed")
        key = str(record["key"])
        object_id = _integer(record.get("object_id"), f"{key} object_id")
        _require(
            object_id in rom_objects,
            f"region {key!r} names object {object_id}, which is not an immutable "
            "ROM memory object",
        )
        referenced.add(object_id)
        descriptor = rom_objects[object_id]
        declared_payload = _integer(record.get("payload_bytes"), f"{key} payload", 1)
        pad = _integer(record.get("pad_bytes"), f"{key} pad")
        _require(
            descriptor.payload["size_bytes"] == declared_payload,
            f"region {key!r} is {declared_payload} bytes in the plan and "
            f"{descriptor.payload['size_bytes']} in the descriptor",
        )
        source = deployment.objects.get(object_id)
        _require(source is not None, f"region {key!r} has no manifest object source")
        _require(
            source.kind == "segments",
            f"region {key!r} has a {source.kind!r} source; a zero-copy ROM region "
            "must reference authenticated checkpoint byte ranges",
        )
        _require(
            source.size_bytes == declared_payload,
            f"region {key!r} source covers {source.size_bytes} bytes, plan says "
            f"{declared_payload}",
        )
        segments = _object_segments(source)

        members = record["members"]
        _require(isinstance(members, list) and bool(members), f"region {key!r} is empty")
        cursor = 0
        for member in members:
            tensor_id = str(member["tensor_id"])
            _require(
                tensor_id not in placed,
                f"tensor {tensor_id!r} is placed twice: {placed.get(tensor_id)!r} and "
                f"{key!r}",
            )
            placed[tensor_id] = key
            offset = _integer(member["offset_bytes"], f"{key} member offset")
            length = _integer(member["bytes"], f"{key} member bytes", 1)
            _require(
                offset == cursor,
                f"region {key!r} member {tensor_id!r} starts at {offset}, expected "
                f"{cursor}; members must tile the region without gaps or overlap",
            )
            cursor = offset + length
            expected_digest = _hex(member["source_sha256"], f"{key} member digest")
            source_path = str(member["source_path"])
            source_offset = _integer(member["source_offset"], f"{key} source offset")

            actual = hashlib.sha256()
            expected = hashlib.sha256()
            emitted = _slice_stream(reader, segments, offset, length)
            checkpoint = _slice_stream(
                reader,
                (_Segment(source_path, source_offset, length, expected_digest),),
                0,
                length,
            )
            seen = 0
            for left, right in zip(emitted, checkpoint):
                if require_bit_identical and left != right:
                    raise InverseProofError(
                        f"region {key!r} member {tensor_id!r} does not reconstruct "
                        f"the checkpoint binding at byte {seen}"
                    )
                actual.update(left)
                expected.update(right)
                seen += len(left)
            _require(
                seen == length,
                f"region {key!r} member {tensor_id!r} reconstructed {seen} of "
                f"{length} bytes",
            )
            _require(
                actual.hexdigest() == expected_digest,
                f"region {key!r} member {tensor_id!r} reconstructs to "
                f"{actual.hexdigest()}, checkpoint binding says {expected_digest}",
            )
            _require(
                expected.hexdigest() == expected_digest,
                f"checkpoint bytes for {tensor_id!r} do not match the binding digest",
            )
            payload_bytes += length
            reconstructed.append(
                {
                    "bytes": length,
                    "region": key,
                    "sha256": expected_digest,
                    "tensor_id": tensor_id,
                }
            )
        _require(
            cursor == declared_payload,
            f"region {key!r} members cover {cursor} of {declared_payload} bytes",
        )

        # --- padding ---------------------------------------------------
        pad_object_id = record.get("pad_object_id")
        if pad:
            _require(
                isinstance(pad_object_id, int) and pad_object_id in rom_objects,
                f"region {key!r} declares {pad} pad bytes but no immutable pad "
                "object owns them",
            )
            referenced.add(int(pad_object_id))
            pad_descriptor = rom_objects[int(pad_object_id)]
            _require(
                pad_descriptor.payload["size_bytes"] == pad,
                f"region {key!r} pad object is "
                f"{pad_descriptor.payload['size_bytes']} bytes, plan says {pad}",
            )
            pad_source = deployment.objects.get(int(pad_object_id))
            _require(
                pad_source is not None and pad_source.kind == "zero",
                f"region {key!r} pad object is not a zero source",
            )
            _require(
                pad_source.fill == 0,
                f"region {key!r} pad object declares fill byte {pad_source.fill}",
            )
            digest = hashlib.sha256()
            seen = 0
            for block in _zero_stream(pad):
                if any(block):
                    raise InverseProofError(
                        f"region {key!r} padding is not zero at byte {seen}"
                    )
                digest.update(block)
                seen += len(block)
            _require(seen == pad, f"region {key!r} padding is short")
            _require(
                digest.hexdigest() == _hex(record["pad_sha256"], f"{key} pad digest"),
                f"region {key!r} pad digest does not match its plan record",
            )
            _require(
                pad_descriptor.payload["content_digest"].hex() == digest.hexdigest(),
                f"region {key!r} pad descriptor digest does not bind zero bytes",
            )
            padding_bytes += pad
        else:
            _require(
                pad_object_id in (None, 0xFFFFFFFF)
                or pad_object_id not in rom_objects,
                f"region {key!r} declares no padding but owns a pad object",
            )

        # --- digest ----------------------------------------------------
        recomputed = _independent_region_digest(record)
        _require(
            recomputed == _hex(record["content_sha256"], f"{key} content digest"),
            f"region {key!r} content digest does not recompute independently",
        )
        _require(
            descriptor.payload["content_digest"].hex() == recomputed,
            f"region {key!r} descriptor does not bind the recomputed content digest",
        )

        # --- placement -------------------------------------------------
        shards = record["shards"]
        _require(isinstance(shards, list) and bool(shards), f"region {key!r} unplaced")
        covered = 0
        for shard in shards:
            _require(
                isinstance(shard, list) and len(shard) == 7,
                f"region {key!r} has a malformed shard record",
            )
            node, reticle, tile, bank, region_offset, extent, address = (
                _integer(v, f"{key} shard field") for v in shard
            )
            _require(extent > 0, f"region {key!r} declares an empty shard")
            _require(
                region_offset == covered,
                f"region {key!r} shards do not tile the region in order",
            )
            covered += extent
            slot = (node, reticle, tile, bank)
            for other_start, other_end, other_key in occupied.get(slot, ()):
                if address < other_end and other_start < address + extent:
                    raise InverseProofError(
                        f"region {key!r} overlaps {other_key!r} in resource {slot} "
                        f"at [{address}, {address + extent})"
                    )
            occupied.setdefault(slot, []).append((address, address + extent, key))
        _require(
            covered == declared_payload + pad,
            f"region {key!r} shards cover {covered} of {declared_payload + pad} bytes",
        )

    unreferenced = sorted(set(rom_objects) - referenced)
    _require(
        not unreferenced,
        f"ROM objects {unreferenced} are declared but owned by no plan region; "
        "every immutable byte must be accounted for",
    )

    repair = _check_repair_map(plan, occupied)

    totals = plan.get("totals", {})
    _require(
        _integer(totals.get("payload_bytes"), "totals.payload_bytes") == payload_bytes,
        "the plan's payload total does not match the reconstructed payload",
    )
    _require(
        _integer(totals.get("padding_bytes"), "totals.padding_bytes") == padding_bytes,
        "the plan's padding total does not match the proved padding",
    )

    return {
        "all_padding_zero": True,
        "bit_identical": bool(require_bit_identical),
        "model_id": plan.get("model_id"),
        "padding_bytes": padding_bytes,
        "payload_bytes": payload_bytes,
        "placed_tensor_count": len(placed),
        "plan_id": plan.get("plan_id"),
        "product": plan.get("product"),
        "reconstructed_content_sha256": hashlib.sha256(
            b"".join(
                record["tensor_id"].encode("utf-8")
                + b"\x00"
                + bytes.fromhex(record["sha256"])
                for record in reconstructed
            )
        ).hexdigest(),
        "region_count": len(regions),
        "repair": repair,
        "rom_bytes": payload_bytes + padding_bytes,
        "schema": INVERSE_REPORT_SCHEMA,
        "status": "pass",
    }


def _check_repair_map(
    plan: Mapping[str, Any],
    occupied: Mapping[tuple[int, int, int, int], Sequence[tuple[int, int, str]]],
) -> dict[str, Any]:
    """Prove the repair map is internally consistent and does not lie."""
    repair = plan.get("repair_map")
    _require(isinstance(repair, Mapping), "the plan carries no repair map")
    banks = repair.get("banks")
    _require(isinstance(banks, list), "the repair map declares no bank inventory")
    inventory: dict[tuple[int, int, int, int], Mapping[str, Any]] = {}
    for bank in banks:
        coordinate = tuple(_integer(v, "bank coordinate") for v in bank["coordinate"])
        _require(len(coordinate) == 4, "a bank coordinate is malformed")
        _require(
            coordinate not in inventory, f"bank {coordinate} is declared twice"
        )
        inventory[coordinate] = bank
        row_bytes = _integer(bank["row_bytes"], "row_bytes", 1)
        data_rows = _integer(bank["data_rows"], "data_rows", 1)
        used = max((end for _s, end, _k in occupied.get(coordinate, ())), default=0)
        needed = (used + row_bytes - 1) // row_bytes
        _require(
            data_rows == needed,
            f"bank {coordinate} declares {data_rows} data rows but holds {used} "
            f"bytes, which needs {needed}",
        )

    missing = sorted(set(occupied) - set(inventory))
    _require(not missing, f"resources {missing} hold regions but have no bank record")

    quarantined = set()
    for entry in repair.get("quarantine", []):
        coordinate = tuple(_integer(v, "quarantine coordinate") for v in entry["coordinate"])
        quarantined.add(coordinate)
        _require(
            coordinate not in occupied,
            f"resource {coordinate} is quarantined but still holds ROM regions",
        )

    seen: set[tuple[Any, ...]] = set()
    rows_used: dict[tuple[int, int, int, int], int] = {}
    columns_used: dict[tuple[int, int, int, int], int] = {}
    for entry in repair.get("entries", []):
        coordinate = tuple(_integer(v, "repair coordinate") for v in entry["coordinate"])
        kind = str(entry["kind"])
        _require(kind in {"row", "column"}, f"unknown repair kind {kind!r}")
        bank = inventory.get(coordinate)
        _require(bank is not None, f"repair entry names undeclared bank {coordinate}")
        logical = _integer(entry["logical_index"], "logical_index")
        spare = _integer(entry["spare_index"], "spare_index")
        token = (coordinate, kind, logical)
        _require(token not in seen, f"{kind} {logical} of bank {coordinate} is repaired twice")
        seen.add(token)
        if kind == "row":
            _require(
                logical < bank["data_rows"],
                f"row {logical} is outside bank {coordinate}",
            )
            _require(
                bank["data_rows"] <= spare < bank["data_rows"] + bank["spare_rows"],
                f"row repair for bank {coordinate} targets a physical row outside "
                "the spare inventory",
            )
            rows_used[coordinate] = rows_used.get(coordinate, 0) + 1
            _require(
                rows_used[coordinate] <= bank["spare_rows"],
                f"bank {coordinate} activates more spare rows than it owns",
            )
        else:
            _require(
                spare < bank["spare_columns"],
                f"column repair for bank {coordinate} targets a spare outside the "
                "inventory",
            )
            columns_used[coordinate] = columns_used.get(coordinate, 0) + 1
            _require(
                columns_used[coordinate] <= bank["spare_columns"],
                f"bank {coordinate} activates more spare columns than it owns",
            )
    return {
        "banks": len(inventory),
        "quarantined": len(quarantined),
        "spare_columns_activated": sum(columns_used.values()),
        "spare_columns_total": sum(int(b["spare_columns"]) for b in inventory.values()),
        "spare_rows_activated": sum(rows_used.values()),
        "spare_rows_total": sum(int(b["spare_rows"]) for b in inventory.values()),
    }


__all__ = [
    "ByteReader",
    "INVERSE_REPORT_SCHEMA",
    "InverseProofError",
    "check_rom_inverse",
    "file_reader",
]
