#!/usr/bin/env python3
"""Build the ROM read-service correlation vector set from a real deployment.

Nothing here is hand written.  The tables come from the compiled ROM region
plan that ``compiler/backends/rom`` publishes inside an ABI 3.0 ROM deployment
(``notes.rom_plan``) together with the MEMORY_OBJECT descriptors that name the
placement resource and base address of every ROM object.  The requests come
from the ROM reads the deployed program actually issues.

Two products, two request sources, and the difference is stated rather than
smoothed over:

``qwen3-chip``
    The Qwen ROM deployment is executed on ``runtime.sim.device.Device`` and
    every ROM-class read the engines perform is recorded, with the byte range it
    covers.  This is an executed read stream.

``deepseek-wafer``
    This campaign retains no executed DeepSeek request stream.  Its requests
    are derived from the compiled plan's own read unit -- a region slot is what
    one iteration of a compressed loop reads -- plus every shard boundary the
    plan declares.  That is derived evidence about addressing, not an executed
    program, and the artifact says so.  The separate governed token lane now
    completes; that does not retroactively make this plan-derived set executed.

The reference decode in this file is written against the plan, independently of
the RTL: it is what the RTL is correlated against, and it is the second
implementation of the same rule.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.constants import DTYPE_BITS, DType, StorageClass  # noqa: E402
from runtime.abi3.crc import record_crc  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402

# Frozen geometry, transcribed in rtl/rom/ot_rom_pkg.sv.
ROW_BYTES = 4096
SENSE_BYTES = 64
SUBWORDS_PER_ROW = ROW_BYTES // SENSE_BYTES
DIGEST_POLY = 0x42F0E1EBA9EA3693
MASK64 = (1 << 64) - 1
NO_ID = 0xFFFFFFFF
DESCRIPTOR_PLAN_PROBE_ID = 0xFFFFFFFE

STATUS_OK, STATUS_MASKED, STATUS_FAULT = 0, 1, 2
(
    FAULT_NONE,
    FAULT_UNPLACED_OBJECT,
    FAULT_OUT_OF_RANGE,
    FAULT_SHARD_GAP,
    FAULT_QUARANTINED,
    FAULT_COLUMN_REPAIR,
    FAULT_ZERO_LENGTH,
    FAULT_DESCRIPTOR_PLAN,
) = range(8)


def digest_step(state: int, value: int) -> int:
    """One 64-bit Galois LFSR step; the RTL function of the same name."""
    top = (state >> 63) & 1
    out = ((state << 1) & MASK64) ^ (DIGEST_POLY if top else 0) ^ (value & MASK64)
    return out & MASK64


def granule_pattern(resource: int, row: int, subword: int) -> bytes:
    """The address-derived sense granule the verification array returns.

    Identical in rtl/test/rom_service_top.sv.  It exists so that a read far
    larger than any image this repository could carry is still checked for
    conveyance and ordering; it is not weight data and is never counted as one.
    """
    seed = 0
    seed = digest_step(seed, resource)
    seed = digest_step(seed, row)
    seed = digest_step(seed, subword)
    out = bytearray()
    for index in range(SENSE_BYTES * 8 // 64):
        seed = digest_step(seed, index)
        out += seed.to_bytes(8, "little")
    return bytes(out)


# ---------------------------------------------------------------------------
# The plan, read back out of a real deployment
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Shard:
    region_id: int
    node_id: int
    reticle: int
    tile: int
    bank: int
    resource_index: int
    region_offset: int
    bytes: int
    resource_address: int


@dataclass(frozen=True)
class ObjectEntry:
    object_id: int
    region_id: int
    shard_first: int
    shard_count: int
    region_offset: int
    size_bytes: int
    role: str
    key: str


@dataclass
class Plan:
    objects: dict[int, ObjectEntry]
    descriptors: dict[int, bytes]
    shards: list[Shard]
    regions: list[dict[str, Any]]
    resources: list[tuple[int, int, int, int]]
    repair: list[dict[str, Any]]
    unplaced: list[dict[str, Any]]
    rom_object_ids: list[int]
    row_bytes: int
    resource_bytes: int

    def sorted_objects(self) -> list[ObjectEntry]:
        return [self.objects[key] for key in sorted(self.objects)]


def load_plan(deployment: Deployment) -> Plan:
    """Read the region plan and the ROM MEMORY_OBJECT descriptors back.

    Every value is cross-checked against the other place it appears rather than
    trusted once: a region's base address against its first shard, an object's
    descriptor base address against its offset inside its region, and every
    shard's coordinate against the repair map's bank inventory.  This function
    refuses rather than repairs.
    """
    plan = deployment.notes.get("rom_plan")
    if not plan:
        raise SystemExit("deployment carries no notes.rom_plan; not a ROM build")
    layout = plan["layout"]
    if layout["row_bytes"] != ROW_BYTES:
        raise SystemExit(
            f"plan row_bytes {layout['row_bytes']} is not the {ROW_BYTES} this "
            "vector set and rtl/rom/ot_rom_pkg.sv are written for"
        )

    banks = plan["repair_map"]["banks"]
    resources = [tuple(bank["coordinate"]) for bank in banks]
    resource_index = {coord: index for index, coord in enumerate(resources)}
    if len(resource_index) != len(resources):
        raise SystemExit("the repair map lists a placement resource twice")

    shards: list[Shard] = []
    object_of: dict[int, ObjectEntry] = {}
    region_shard_span: dict[int, tuple[int, int]] = {}
    for region in plan["regions"]:
        first = len(shards)
        cursor = 0
        for raw in region["shards"]:
            node, reticle, tile, bank, region_offset, extent, address = raw
            coord = (node, reticle, tile, bank)
            if coord not in resource_index:
                raise SystemExit(
                    f"region {region['key']!r} names resource {coord} which the "
                    "repair map does not inventory"
                )
            if region_offset != cursor:
                raise SystemExit(
                    f"region {region['key']!r} shard table does not tile the "
                    f"region: shard starts at {region_offset}, expected {cursor}"
                )
            cursor += extent
            shards.append(
                Shard(
                    region_id=region["region_id"],
                    node_id=node,
                    reticle=reticle,
                    tile=tile,
                    bank=bank,
                    resource_index=resource_index[coord],
                    region_offset=region_offset,
                    bytes=extent,
                    resource_address=address,
                )
            )
        total = region["payload_bytes"] + region["pad_bytes"]
        if cursor != total:
            raise SystemExit(
                f"region {region['key']!r} shards cover {cursor} bytes but the "
                f"region is {total}"
            )
        if region["shards"][0][6] != region["base_address"]:
            raise SystemExit(
                f"region {region['key']!r} base address {region['base_address']} "
                f"is not its first shard address {region['shards'][0][6]}"
            )
        region_shard_span[region["region_id"]] = (first, len(shards) - first)

        for object_id, offset, size in (
            (region["object_id"], 0, region["payload_bytes"]),
            (region["pad_object_id"], region["payload_bytes"], region["pad_bytes"]),
        ):
            if object_id == NO_ID or size == 0:
                continue
            object_of[object_id] = ObjectEntry(
                object_id=object_id,
                region_id=region["region_id"],
                shard_first=region_shard_span[region["region_id"]][0],
                shard_count=region_shard_span[region["region_id"]][1],
                region_offset=offset,
                size_bytes=size,
                role=region["role"],
                key=region["key"],
            )

    table = deployment.table
    # Keep the exact admitted wire records, not a second convenient rendering
    # of their decoded fields.  DescriptorTable.encode() returns the bytes
    # whose digest Deployment.read() has already checked against the manifest;
    # walk that variable-length stream once so the object image below can pair
    # each plan entry with the actual 128-byte MEMORY_OBJECT record at its
    # descriptor-table index.
    descriptor_records: list[bytes] = []
    table_blob = table.encode()
    cursor = 0
    while cursor < len(table_blob):
        if cursor + 12 > len(table_blob):
            raise SystemExit("admitted descriptor table ends inside a header")
        total = int.from_bytes(table_blob[cursor + 8 : cursor + 12], "little")
        if total <= 0 or cursor + total > len(table_blob):
            raise SystemExit("admitted descriptor table has an invalid record span")
        descriptor_records.append(table_blob[cursor : cursor + total])
        cursor += total
    if len(descriptor_records) != len(table):
        raise SystemExit(
            "descriptor-table record walk disagrees with the admitted table length"
        )

    rom_ids: list[int] = []
    placed_descriptors: dict[int, bytes] = {}
    unplaced: list[dict[str, Any]] = []
    for object_id in sorted(table.ids_of_type(ExtendedDescriptorType.MEMORY_OBJECT)):
        payload = table.get(object_id, ExtendedDescriptorType.MEMORY_OBJECT).payload
        if payload["storage_class"] != int(StorageClass.ROM):
            continue
        rom_ids.append(object_id)
        entry = object_of.get(object_id)
        if entry is None:
            source = deployment.objects.get(object_id)
            unplaced.append(
                {
                    "object_id": object_id,
                    "size_bytes": payload["size_bytes"],
                    "declared_bank_or_tile": payload["bank_or_tile"],
                    "declared_base_address": payload["base_address"],
                    "source_kind": getattr(source, "kind", None),
                    "generator": getattr(source, "generator", "") or None,
                }
            )
            continue
        record = descriptor_records[object_id]
        if len(record) != 128:
            raise SystemExit(
                f"placed ROM object {object_id} has a {len(record)}-byte "
                "MEMORY_OBJECT record; the RTL configuration contract is 128 bytes"
            )
        placed_descriptors[object_id] = record
        if payload["size_bytes"] != entry.size_bytes:
            raise SystemExit(
                f"object {object_id} descriptor size {payload['size_bytes']} "
                f"disagrees with its region extent {entry.size_bytes}"
            )
        shard0 = shards[entry.shard_first]
        expected_base = shard0.resource_address + entry.region_offset
        if payload["base_address"] != expected_base:
            raise SystemExit(
                f"object {object_id} descriptor base address "
                f"{payload['base_address']} disagrees with the plan's "
                f"{expected_base}"
            )
        declared = payload["bank_or_tile"]
        actual = shard0.tile if shard0.tile else shard0.bank
        if declared != actual and declared != NO_ID & 0xFFFF:
            raise SystemExit(
                f"object {object_id} descriptor names bank_or_tile {declared} "
                f"but the plan places its first shard on {actual}"
            )

    # The byte-window reader addresses the region members, while DeviceMemory
    # authenticates the deployment object's segments.  Prove those are the
    # same ranges before calling a window "authenticated"; otherwise two
    # independently digest-bound manifest fields could name different bytes.
    for region in plan["regions"]:
        object_id = region["object_id"]
        if object_id == NO_ID or region["payload_bytes"] == 0:
            continue
        source = deployment.objects.get(object_id)
        if source is None or source.kind not in {"file", "segments"}:
            raise SystemExit(
                f"region {region['key']!r} payload object {object_id} is not "
                "backed by shared authenticated segments"
            )
        expected = [
            {
                "path": segment.path,
                "offset": segment.offset,
                "bytes": segment.bytes,
                "sha256": segment.sha256,
            }
            for segment in source.segments
        ]
        actual = [
            {
                "path": member["source_path"],
                "offset": member["source_offset"],
                "bytes": member["bytes"],
                "sha256": member.get("source_sha256"),
            }
            for member in region["members"]
        ]
        if actual != expected:
            raise SystemExit(
                f"region {region['key']!r} member ranges do not match object "
                f"{object_id}'s authenticated source map"
            )

    repair = []
    for entry in plan["repair_map"]["entries"]:
        coord = tuple(entry["coordinate"])
        repair.append(
            {
                "resource_index": resource_index[coord],
                "kind": entry["kind"],
                "logical_index": entry["logical_index"],
                "spare_index": entry["spare_index"],
            }
        )

    return Plan(
        objects=object_of,
        descriptors=placed_descriptors,
        shards=shards,
        regions=plan["regions"],
        resources=resources,
        repair=repair,
        unplaced=unplaced,
        rom_object_ids=rom_ids,
        row_bytes=ROW_BYTES,
        resource_bytes=layout["resource_bytes"],
    )


# ---------------------------------------------------------------------------
# The reference decode
# ---------------------------------------------------------------------------
@dataclass
class Beat:
    index: int
    resource_index: int
    resource_address: int
    region_byte: int
    physical_row: int
    subword: int
    bytes: int
    activate: bool

    def record(self) -> int:
        value = self.index & 0xFFFFFFFF
        value |= (1 if self.activate else 0) << 39
        value |= (self.bytes & 0xFFFF) << 40
        value |= (self.subword & 0xFF) << 56
        value |= (self.physical_row & 0xFFFFFFFF) << 64
        value |= (self.resource_index & 0xFFFFFFFF) << 96
        value |= (self.region_byte & MASK64) << 128
        value |= (self.resource_address & MASK64) << 192
        return value


@dataclass
class RequestResult:
    status: int
    fault: int
    beats: int
    bytes: int
    activations: int
    beat_digest: int
    data_digest: int
    first_beat: int
    last_beat: int
    touched: list[tuple[int, int, int]] = field(default_factory=list)


class Reference:
    """The rule the RTL is correlated against, written from the plan alone."""

    def __init__(
        self,
        plan: Plan,
        masked_regions: set[int],
        broken_resources: set[int],
        repair: Sequence[dict[str, Any]],
    ) -> None:
        self.plan = plan
        self.masked = masked_regions
        self.broken = broken_resources
        self.row_repair: dict[tuple[int, int], int] = {}
        self.column_resources: set[int] = set()
        for entry in repair:
            if entry["kind"] == "row":
                self.row_repair[
                    (entry["resource_index"], entry["logical_index"])
                ] = entry["spare_index"]
            elif entry["kind"] == "column":
                self.column_resources.add(entry["resource_index"])
        # The row buffer persists across requests; so does the RTL's.
        self.rowbuf: tuple[int, int] | None = None
        #: Every placement resource a *served* request actually entered.  It is
        #: the coverage figure the wafer claim rests on: an addressing service
        #: that reached 9,299 of 9,300 tiles would look identical in every
        #: aggregate below.
        self.resources_entered: set[int] = set()

    def find_shard(self, entry: ObjectEntry, region_byte: int) -> Shard | None:
        lo = entry.shard_first
        hi = entry.shard_first + entry.shard_count
        best: Shard | None = None
        while lo < hi:
            mid = (lo + hi) // 2
            candidate = self.plan.shards[mid]
            if candidate.region_offset <= region_byte:
                best = candidate
                lo = mid + 1
            else:
                hi = mid
        if best is None:
            return None
        if region_byte >= best.region_offset + best.bytes:
            return None
        return best

    def run(
        self,
        object_id: int,
        offset: int,
        length: int,
        reader,
        *,
        collect: bool = False,
    ) -> RequestResult:
        """Decode one request the way rtl/rom/ot_rom_read_service.sv does.

        ``collect`` records every sense granule the request touches, which the
        caller needs only for the requests whose data window is published.  A
        hundred-megabyte read touches a million and a half granules and they are
        not kept.
        """
        # One explicit campaign-only entry is appended after the genuine plan
        # objects.  It carries a well-formed, valid-CRC MEMORY_OBJECT record
        # whose base is deliberately one declared alignment unit away from the
        # first shard.  The service must detect that independent disagreement
        # before sensing.  It is not treated as an ordinary unplaced object,
        # because doing so would never exercise the descriptor/shard binding.
        if object_id == DESCRIPTOR_PLAN_PROBE_ID:
            return RequestResult(
                STATUS_FAULT, FAULT_DESCRIPTOR_PLAN, 0, 0, 0, 0, 0, 0, 0
            )
        entry = self.plan.objects.get(object_id)
        if entry is None:
            return RequestResult(
                STATUS_FAULT, FAULT_UNPLACED_OBJECT, 0, 0, 0, 0, 0, 0, 0
            )
        if length == 0:
            return RequestResult(STATUS_FAULT, FAULT_ZERO_LENGTH, 0, 0, 0, 0, 0, 0, 0)
        if offset + length > entry.size_bytes:
            return RequestResult(STATUS_FAULT, FAULT_OUT_OF_RANGE, 0, 0, 0, 0, 0, 0, 0)
        if entry.region_id in self.masked:
            # Masked is not a fault: nothing is activated, nothing is sensed and
            # the consumer is told so rather than handed zeros.
            return RequestResult(STATUS_MASKED, FAULT_NONE, 0, 0, 0, 0, 0, 0, 0)

        # Walk the extent once to prove every placement resource it reaches is
        # in service, before anything is sensed.  A refused read must not put a
        # single byte of weight on the operand bus -- a consumer cannot tell a
        # partial weight from a whole one -- and it must not disturb the row
        # buffer either, or the next request's activation count would move.
        # rtl/rom/ot_rom_read_service.sv walks the same two passes.
        probe = entry.region_offset + offset
        end = entry.region_offset + offset + length
        while probe < end:
            shard = self.find_shard(entry, probe)
            if shard is None:
                return RequestResult(STATUS_FAULT, FAULT_SHARD_GAP, 0, 0, 0, 0, 0, 0, 0)
            if shard.resource_index in self.broken:
                return RequestResult(
                    STATUS_FAULT, FAULT_QUARANTINED, 0, 0, 0, 0, 0, 0, 0
                )
            if shard.resource_index in self.column_resources:
                return RequestResult(
                    STATUS_FAULT, FAULT_COLUMN_REPAIR, 0, 0, 0, 0, 0, 0, 0
                )
            probe = shard.region_offset + shard.bytes

        beat_digest = 0
        data_digest = 0
        activations = 0
        touched: list[tuple[int, int, int]] = []
        first_record: int | None = None
        last_record = 0
        cursor = 0
        region_byte = entry.region_offset + offset
        index = 0
        while cursor < length:
            shard = self.find_shard(entry, region_byte)
            # The pass above proved all three of these; if one fires now the
            # two passes disagree, which is a defect in this reference and not
            # a property of the request.
            assert shard is not None
            assert shard.resource_index not in self.broken
            assert shard.resource_index not in self.column_resources
            offset_in_shard = region_byte - shard.region_offset
            address = shard.resource_address + offset_in_shard
            logical_row = address // ROW_BYTES
            physical_row = self.row_repair.get(
                (shard.resource_index, logical_row), logical_row
            )
            subword = (address // SENSE_BYTES) % SUBWORDS_PER_ROW
            byte_in_word = address % SENSE_BYTES
            take = min(
                length - cursor,
                SENSE_BYTES - byte_in_word,
                shard.bytes - offset_in_shard,
            )
            self.resources_entered.add(shard.resource_index)
            activate = self.rowbuf != (shard.resource_index, physical_row)
            record = Beat(
                index=index,
                resource_index=shard.resource_index,
                resource_address=address,
                region_byte=region_byte,
                physical_row=physical_row,
                subword=subword,
                bytes=take,
                activate=activate,
            ).record()
            for shift in (0, 64, 128, 192):
                beat_digest = digest_step(beat_digest, (record >> shift) & MASK64)
            granule = reader(shard, address - byte_in_word)
            payload = granule[byte_in_word : byte_in_word + take]
            aligned = payload + bytes(SENSE_BYTES - len(payload))
            for word in range(SENSE_BYTES // 8):
                data_digest = digest_step(
                    data_digest,
                    int.from_bytes(aligned[word * 8 : word * 8 + 8], "little"),
                )
            if collect:
                touched.append((shard.resource_index, physical_row, subword))
            if activate:
                activations += 1
            self.rowbuf = (shard.resource_index, physical_row)
            if first_record is None:
                first_record = record
            last_record = record
            cursor += take
            region_byte += take
            index += 1
        return RequestResult(
            status=STATUS_OK,
            fault=FAULT_NONE,
            beats=index,
            bytes=length,
            activations=activations,
            beat_digest=beat_digest,
            data_digest=data_digest,
            first_beat=first_record or 0,
            last_beat=last_record,
            touched=touched,
        )


# ---------------------------------------------------------------------------
# Region byte reader: the authenticated checkpoint, addressed the plan's way
# ---------------------------------------------------------------------------
class RegionBytes:
    """Read the bytes a region holds at a region-relative offset.

    A region's payload is an ordered list of authenticated checkpoint ranges and
    its tail is a declared zero pad, exactly as
    ``compiler.backends.rom.common.image`` lays it out.  Nothing is copied: the
    files are opened where the deployment says they are and read at the offset
    the member record names.
    """

    def __init__(self, plan: Plan, root: Path | None) -> None:
        self.root = root
        self.handles: dict[str, Any] = {}
        self.members: dict[int, list[tuple[int, int, str, int]]] = {}
        self.payload: dict[int, int] = {}
        self.available = root is not None
        for region in plan.regions:
            rows = [
                (m["offset_bytes"], m["bytes"], m["source_path"], m["source_offset"])
                for m in region["members"]
            ]
            rows.sort()
            self.members[region["region_id"]] = rows
            self.payload[region["region_id"]] = region["payload_bytes"]
        if self.available:
            for rows in self.members.values():
                for _, _, path, _ in rows:
                    full = Path(path)
                    if not full.is_absolute():
                        full = (root / path)
                    if not full.exists():
                        self.available = False
                        return

    def read(self, region_id: int, offset: int, length: int) -> bytes | None:
        if not self.available:
            return None
        out = bytearray(length)
        rows = self.members[region_id]
        for member_offset, member_bytes, path, source_offset in rows:
            lo = max(offset, member_offset)
            hi = min(offset + length, member_offset + member_bytes)
            if lo >= hi:
                continue
            handle = self.handles.get(path)
            if handle is None:
                full = Path(path)
                if not full.is_absolute():
                    full = self.root / path
                handle = open(full, "rb")
                self.handles[path] = handle
            handle.seek(source_offset + (lo - member_offset))
            chunk = handle.read(hi - lo)
            if len(chunk) != hi - lo:
                return None
            out[lo - offset : hi - offset] = chunk
        # Everything past the payload is the declared zero pad; the bytearray
        # already holds zeros there.
        return bytes(out)


# ---------------------------------------------------------------------------
# Request sources
# ---------------------------------------------------------------------------
@dataclass
class Request:
    object_id: int
    offset: int
    length: int
    origin: str
    note: str = ""
    windowed: bool = False


#: The functional-device sources an executed request stream depends on.  They
#: are digested before and after the run: a concurrent edit between the two
#: makes the stream a mixture of two implementations, and this refuses rather
#: than publishing it.
# Keep this boundary aligned with the modules that can determine an executed
# request stream.  A deployment digest binds the already-lowered program, so
# compiler lowering is deliberately outside this list; admission, decoding,
# memory materialisation, numeric helpers and every registered engine are not.
RUNTIME_SOURCES = (
    "runtime/abi3/builder.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/constants.py",
    "runtime/abi3/crc.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/layout.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/driver.py",
    "runtime/reference/compression_pool.py",
    "runtime/reference/formats.py",
    "runtime/reference/hadamard.py",
    "runtime/reference/hyper_connection.py",
    "runtime/reference/normalization.py",
    "runtime/reference/quantization.py",
    "runtime/reference/sparse_attention.py",
    "runtime/reference/sqrt_softplus.py",
    "runtime/reference/swiglu.py",
    "runtime/reference/transcendental.py",
    "runtime/sim/backend.py",
    "runtime/sim/counters.py",
    "runtime/sim/device.py",
    "runtime/sim/engine.py",
    "runtime/sim/formats.py",
    "runtime/sim/generators.py",
    "runtime/sim/memory.py",
    "runtime/tensor_accelerator/attention.py",
    "runtime/tensor_accelerator/bf16.py",
    "runtime/tensor_accelerator/elementwise.py",
    "runtime/tensor_accelerator/rmsnorm.py",
    "runtime/tensor_accelerator/rope.py",
    "runtime/tensor_accelerator/sparse_attention.py",
)


def runtime_source_paths() -> tuple[Path, ...]:
    """Return the complete, fail-closed functional source boundary."""

    paths = {
        *(REPO / rel for rel in RUNTIME_SOURCES),
        *(REPO / "runtime" / "sim" / "engines").glob("*.py"),
    }
    missing = sorted(str(path.relative_to(REPO)) for path in paths if not path.is_file())
    if missing:
        raise SystemExit(
            "the executed-stream source boundary names missing files: "
            + ", ".join(missing)
        )
    return tuple(sorted(paths))


def runtime_digests() -> dict[str, str]:
    return {
        str(path.relative_to(REPO)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in runtime_source_paths()
    }


def input_identity(path: Path) -> dict[str, str]:
    """Stable identity of an exact non-checkpoint input loaded by the run."""

    resolved = path.resolve()
    try:
        recorded_path = str(resolved.relative_to(REPO))
    except ValueError:
        recorded_path = str(resolved)
    return {
        "path": recorded_path,
        "sha256": hashlib.sha256(resolved.read_bytes()).hexdigest(),
    }


def checkpoint_binding_identity(deployment: Deployment) -> dict[str, Any]:
    """Summarise the authenticated external ranges DeviceMemory verifies.

    The root is intentionally not identity: moving an identical checkpoint may
    not change evidence.  The ordered object/range map, including every
    declared range digest, is identity and is already transitively bound by the
    deployment digest.  Publishing it explicitly makes the loaded-input scope
    auditable without embedding host-specific paths.
    """

    rows: list[dict[str, Any]] = []
    range_count = 0
    for object_id, source in sorted(deployment.objects.items()):
        maps = (
            source.node_segments
            if source.kind == "node_segments"
            else (source.segments,) if source.kind in {"file", "segments"} else ()
        )
        for node_id, segments in enumerate(maps):
            for segment in segments:
                rows.append(
                    {
                        "object_id": object_id,
                        "node_id": node_id if source.kind == "node_segments" else None,
                        **segment.to_dict(),
                    }
                )
                range_count += 1
    encoded = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "authenticated_range_count": range_count,
        "range_map_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def executed_qwen_requests(
    deployment_dir: Path,
    checkpoint_root: Path | None,
    capability_path: Path,
    workload_path: Path,
    prompt_tokens: int,
    max_new_tokens: int,
) -> tuple[list[Request], dict[str, Any]]:
    """Record every ROM read the deployed Qwen ROM program actually performs.

    Two accounting sites exist in the functional device and both are recorded:
    ``runtime.sim.engine.EngineContext._account_read`` for a whole-view read and
    ``runtime.sim.engines.tensor._account_read`` for the partial reads the
    tensor engine performs itself.  The recorded stream is checked against the
    device's own ``rom.bytes_read`` counter afterwards; a mismatch means a third
    site exists and the vector set is refused rather than published short.
    """
    import numpy as np

    from runtime.abi3.capability import Capability
    from runtime.driver import GenerationDriver
    from runtime.sim.device import Device
    from runtime.sim.engines import load_engines
    import runtime.sim.engine as engine_mod
    import runtime.sim.engines.tensor as tensor_mod
    from runtime.abi3.constants import Major, Tensor
    from runtime.sim.engine import _REGISTRY

    load_engines()
    before = runtime_digests()
    input_before = {
        "capability": input_identity(capability_path),
        "workload": input_identity(workload_path),
    }
    events: list[dict[str, Any]] = []
    gather_rows: list[list[int]] = []

    def contiguous(dims: Sequence[int], strides: Sequence[int]) -> bool:
        expected = 1
        for dim, stride in zip(reversed(dims), reversed(strides)):
            if dim == 1:
                continue
            if stride != expected:
                return False
            expected *= dim
        return True

    def element_bytes(view, count: int) -> int:
        bits = DTYPE_BITS[DType(view.dtype)]
        return (int(count) * bits) // 8

    def record(site: str, view, nbytes: int, memory) -> None:
        if memory[view.object_id].storage_class != StorageClass.ROM:
            return
        events.append(
            {
                "site": site,
                "object_id": int(view.object_id),
                "descriptor_id": int(view.descriptor_id),
                "element_offset": int(view.element_offset),
                "dims": [int(d) for d in view.dims],
                "strides": [int(s) for s in view.strides],
                "dtype": int(view.dtype),
                "bytes": int(nbytes),
                "whole_view": int(nbytes) == element_bytes(view, view.element_count),
                "contiguous": contiguous(view.dims, view.strides),
                "gather": list(gather_rows[-1]) if gather_rows else None,
            }
        )

    original_ctx = engine_mod.EngineContext._account_read

    def patched_ctx(self, view, array):
        record("ctx.read", view, int(array.size) * int(array.dtype.itemsize),
               self.memory)
        return original_ctx(self, view, array)

    original_tensor = tensor_mod._account_read

    def patched_tensor(ctx, view, nbytes):
        record("tensor.partial", view, int(nbytes), ctx.memory)
        return original_tensor(ctx, view, nbytes)

    embed_key = (int(Major.TENSOR), int(Tensor.EMBED_LOOKUP))
    original_embed = _REGISTRY[embed_key]

    def patched_embed(ctx, sub, descriptor):
        id_view = ctx.input_view(descriptor, 0)
        rows = np.asarray(ctx.views.read_array(id_view)).reshape(-1)
        gather_rows.append([int(r) for r in rows])
        try:
            return original_embed(ctx, sub, descriptor)
        finally:
            gather_rows.pop()

    engine_mod.EngineContext._account_read = patched_ctx
    tensor_mod._account_read = patched_tensor
    _REGISTRY[embed_key] = patched_embed
    try:
        capability = Capability.from_dict(
            json.loads(capability_path.read_text(encoding="utf-8"))
        )
        deployment = Deployment.read(deployment_dir)
        # Admission is part of the evidence, and the explicit checkpoint root
        # is the missing link between an ignored three-file deployment bundle
        # and the authenticated source ranges it names.
        device = Device(deployment, capability, root=checkpoint_root)
        driver = GenerationDriver(device)
        workload = json.loads(workload_path.read_text(encoding="utf-8"))
        prompt = workload["token_ids"][:prompt_tokens]
        result = driver.generate(prompt, max_new_tokens=max_new_tokens)
    finally:
        engine_mod.EngineContext._account_read = original_ctx
        tensor_mod._account_read = original_tensor
        _REGISTRY[embed_key] = original_embed

    after = runtime_digests()
    if before != after:
        changed = sorted(
            name for name in set(before) | set(after)
            if before.get(name) != after.get(name)
        )
        raise SystemExit(
            "the functional device's sources changed while the request stream "
            f"was being recorded ({', '.join(changed)}); the stream would be a "
            "mixture of two implementations"
        )
    input_after = {
        "capability": input_identity(capability_path),
        "workload": input_identity(workload_path),
    }
    if input_before != input_after:
        raise SystemExit(
            "the capability or workload changed while the request stream was "
            "being recorded; the stream would have mixed input identities"
        )

    recorded = sum(event["bytes"] for event in events)
    counter = int(result.counters.get("rom.bytes_read", 0))
    if recorded != counter:
        raise SystemExit(
            f"recorded {recorded} ROM bytes but the device counted {counter}; "
            "a ROM read is accounted somewhere this instrument does not see, "
            "so the request stream would be published short"
        )

    requests: list[Request] = []
    skipped = 0
    for event in events:
        item = DType(event["dtype"])
        bits = DTYPE_BITS[item]
        if not event["contiguous"]:
            skipped += 1
            continue
        base = (event["element_offset"] * bits) // 8
        if event["gather"] is not None and not event["whole_view"]:
            width = event["dims"][-1]
            row_bytes = (width * bits) // 8
            for row in event["gather"]:
                requests.append(
                    Request(
                        object_id=event["object_id"],
                        offset=base + row * row_bytes,
                        length=row_bytes,
                        origin="executed",
                        note=f"embed row {row}",
                    )
                )
            continue
        if not event["whole_view"]:
            # A partial read of a stacked weight (a routed expert slice) is a
            # contiguous slice at the head of the view; nothing in the Qwen
            # dense program produces one, and if that changes, this count makes
            # it visible rather than letting it be silently mis-addressed.
            skipped += 1
            continue
        requests.append(
            Request(
                object_id=event["object_id"],
                offset=base,
                length=event["bytes"],
                origin="executed",
                note=f"descriptor {event['descriptor_id']}",
            )
        )
    if skipped:
        raise SystemExit(
            f"{skipped} ROM read events cannot be expressed as exact contiguous "
            "ranges; publishing the executed stream would omit device traffic"
        )
    summary = {
        "runtime_source_sha256": after,
        "loaded_inputs": input_after,
        "checkpoint_binding": {
            **checkpoint_binding_identity(deployment),
            "verified_on_device_activation": True,
        },
        "deployment_admitted": bool(device.report and device.report.admitted),
        "generated_token_count": len(result.generated_token_ids),
        "stop_reason": result.stop_reason,
        "prompt_token_count": len(prompt),
        "rom_bytes_read_counter": counter,
        "rom_read_events": len(events),
        "requests_derived": len(requests),
        "events_not_expressible_as_contiguous_ranges": skipped,
        "failure": result.failure,
    }
    return requests, summary


def plan_derived_requests(plan: Plan, limit_per_region: int) -> list[Request]:
    """Requests derived from the compiled plan's own read unit.

    A region slot is what one iteration of a compressed loop reads, so a slot is
    the read the deployment was laid out for.  This walks slots and shard
    boundaries; it is derived evidence about addressing and is never described
    as an executed read stream.
    """
    requests: list[Request] = []
    by_region: dict[int, dict[str, Any]] = {r["region_id"]: r for r in plan.regions}
    for entry in plan.sorted_objects():
        region = by_region[entry.region_id]
        if entry.region_offset != 0:
            continue  # the pad object is covered by the probe set
        slot_bytes = region["slot_bytes"]
        slot_count = region["slot_count"]
        if slot_bytes <= 0:
            continue
        picked = 0
        for slot in range(slot_count):
            if picked >= limit_per_region:
                break
            requests.append(
                Request(
                    object_id=entry.object_id,
                    offset=slot * slot_bytes,
                    length=slot_bytes,
                    origin="plan_slot",
                    note=f"{region['key']} slot {slot}",
                )
            )
            picked += 1
    return requests


def probe_requests(plan: Plan) -> list[Request]:
    """One-granule probes over the whole address space, plus the boundaries.

    A probe costs a handful of cycles, so the entire 16 GB (Qwen) or 156 GB
    (DeepSeek wafer) address space can be covered at its boundaries even though
    replaying the reads that traverse it cannot be.
    """
    requests: list[Request] = []
    for entry in plan.sorted_objects():
        size = entry.size_bytes
        key = entry.key
        requests.append(
            Request(entry.object_id, 0, min(SENSE_BYTES, size), "probe",
                    f"{key} first granule")
        )
        if size > SENSE_BYTES:
            requests.append(
                Request(entry.object_id, size - SENSE_BYTES, SENSE_BYTES, "probe",
                        f"{key} last granule")
            )
            requests.append(
                Request(entry.object_id, size // 2, min(SENSE_BYTES, size // 2),
                        "probe", f"{key} midpoint granule")
            )
        if size > ROW_BYTES + SENSE_BYTES:
            requests.append(
                Request(entry.object_id, ROW_BYTES - 32, 64, "probe",
                        f"{key} row boundary crossing")
            )
        if size > 200:
            requests.append(
                Request(entry.object_id, 1, 130, "probe_unaligned",
                        f"{key} unaligned offset and length")
            )
        # Every shard boundary this object reaches, crossed by one request.
        for index in range(entry.shard_first, entry.shard_first + entry.shard_count - 1):
            shard = plan.shards[index]
            boundary = shard.region_offset + shard.bytes
            offset = boundary - entry.region_offset
            if 32 <= offset <= size - 32:
                requests.append(
                    Request(entry.object_id, offset - 32, 64, "probe_shard_edge",
                            f"{key} crosses into resource "
                            f"{plan.shards[index + 1].resource_index}")
                )
    return requests


def negative_requests(plan: Plan) -> list[Request]:
    """Requests that must fail closed, one per refusal the service declares."""
    requests: list[Request] = []
    for record in plan.unplaced:
        requests.append(
            Request(
                record["object_id"], 0, min(SENSE_BYTES, record["size_bytes"]),
                "negative_unplaced",
                f"ROM object {record['object_id']} is in no region "
                f"(source {record.get('generator') or record.get('source_kind')})",
            )
        )
    placed = plan.sorted_objects()
    if placed:
        first = placed[0]
        requests.append(
            Request(first.object_id, first.size_bytes - 1, 64,
                    "negative_range", "one byte past the end of the object")
        )
        requests.append(
            Request(first.object_id, first.size_bytes, 64,
                    "negative_range", "starts past the end of the object")
        )
        requests.append(
            Request(first.object_id, 0, 0, "negative_zero", "zero length")
        )
        # This is the request that distinguishes the RTL's 65-bit extent
        # check from a wrapped 64-bit sum.  At 64 bits, offset + length is 32
        # and could look in range for almost every object; at 65 bits it is
        # unambiguously beyond the descriptor's size and must be refused
        # before any shard or sense access.
        requests.append(
            Request(
                first.object_id,
                (1 << 64) - 32,
                64,
                "negative_range_wrap",
                "64-bit offset plus length carries into bit 64",
            )
        )
        requests.append(
            Request(
                DESCRIPTOR_PLAN_PROBE_ID,
                0,
                min(SENSE_BYTES, first.size_bytes),
                "negative_descriptor_plan",
                "valid descriptor base disagrees with the first plan shard",
            )
        )
    requests.append(
        Request(0xDEADBEEF, 0, 64, "negative_unknown",
                "an object id no descriptor declares")
    )
    return requests


# ---------------------------------------------------------------------------
# Image emission
# ---------------------------------------------------------------------------
def write_words(path: Path, words: Iterable[int], per_line: int) -> None:
    lines: list[str] = []
    row: list[str] = []
    for word in words:
        row.append(f"{word & 0xFFFFFFFF:08x}")
        if len(row) == per_line:
            lines.append(" ".join(row))
            row = []
    if row:
        lines.append(" ".join(row))
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def split64(value: int) -> tuple[int, int]:
    return value & 0xFFFFFFFF, (value >> 32) & 0xFFFFFFFF


def split256(value: int) -> list[int]:
    return [(value >> (32 * i)) & 0xFFFFFFFF for i in range(8)]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(args: argparse.Namespace) -> dict[str, Any]:
    deployment = Deployment.read(args.deployment)
    plan = load_plan(deployment)
    region_by_id = {r["region_id"]: r for r in plan.regions}

    masked_regions: set[int] = set()
    for key in args.mask_region:
        matches = [r["region_id"] for r in plan.regions if r["key"] == key]
        if not matches:
            raise SystemExit(f"--mask-region {key!r} names no region in this plan")
        masked_regions.update(matches)
    broken = set(args.quarantine_resource)
    for index in broken:
        if index >= len(plan.resources):
            raise SystemExit(
                f"--quarantine-resource {index} is outside the "
                f"{len(plan.resources)} resources this plan inventories"
            )

    reader_source = RegionBytes(plan, args.checkpoint_root or args.deployment)

    # -- assemble the request list ------------------------------------
    requests: list[Request] = []
    executed_summary: dict[str, Any] = {}
    if args.executed:
        executed, executed_summary = executed_qwen_requests(
            args.deployment,
            args.checkpoint_root,
            args.capability,
            args.workload,
            args.prompt_tokens,
            args.max_new_tokens,
        )
        requests.extend(executed)
    if args.plan_slots:
        requests.extend(plan_derived_requests(plan, args.plan_slots))
    requests.extend(probe_requests(plan))
    requests.extend(negative_requests(plan))
    if masked_regions:
        for region_id in sorted(masked_regions):
            region = region_by_id[region_id]
            if region["object_id"] == NO_ID:
                continue
            requests.append(
                Request(region["object_id"], 0, min(SENSE_BYTES, region["payload_bytes"]),
                        "masked", f"{region['key']} is masked off")
            )
            requests.append(
                Request(region["object_id"], 0, region["slot_bytes"],
                        "masked", f"{region['key']} whole slot while masked")
            )
    for index in sorted(broken):
        coord = plan.resources[index]
        owner = next(
            (s for s in plan.shards if s.resource_index == index), None
        )
        if owner is None:
            continue
        entry = next(
            (
                e
                for e in plan.sorted_objects()
                if e.region_id == owner.region_id and e.region_offset == 0
            ),
            None,
        )
        if entry is None:
            continue
        offset = max(0, owner.region_offset - entry.region_offset)
        if offset + SENSE_BYTES <= entry.size_bytes:
            requests.append(
                Request(entry.object_id, offset, SENSE_BYTES, "quarantined",
                        f"resource {index} {coord} is quarantined")
            )
    for entry_repair in plan.repair:
        if entry_repair["kind"] != "row":
            continue
        index = entry_repair["resource_index"]
        row = entry_repair["logical_index"]
        shard = next((s for s in plan.shards if s.resource_index == index), None)
        if shard is None:
            continue
        obj = next(
            (
                e
                for e in plan.sorted_objects()
                if e.region_id == shard.region_id and e.region_offset == 0
            ),
            None,
        )
        if obj is None:
            continue
        address = row * ROW_BYTES
        if address < shard.resource_address:
            continue
        offset = (shard.region_offset + (address - shard.resource_address)
                  - obj.region_offset)
        if 0 <= offset and offset + ROW_BYTES <= obj.size_bytes:
            requests.append(
                Request(obj.object_id, offset, ROW_BYTES, "repaired_row",
                        f"logical row {row} on resource {index} is repaired to "
                        f"spare {entry_repair['spare_index']}")
            )

    # -- decide which requests carry a published real-byte window ------
    reference = Reference(plan, masked_regions, broken, plan.repair)
    scratch_reader_calls = 0

    def pattern_reader(shard: Shard, granule_address: int) -> bytes:
        nonlocal scratch_reader_calls
        scratch_reader_calls += 1
        logical_row = granule_address // ROW_BYTES
        physical_row = reference.row_repair.get(
            (shard.resource_index, logical_row), logical_row
        )
        subword = (granule_address // SENSE_BYTES) % SUBWORDS_PER_ROW
        return granule_pattern(shard.resource_index, physical_row, subword)

    def real_reader(shard: Shard, granule_address: int) -> bytes | None:
        region_offset = shard.region_offset + (granule_address - shard.resource_address)
        return reader_source.read(shard.region_id, region_offset, SENSE_BYTES)

    # -- run the reference --------------------------------------------
    kept: list[tuple[Request, RequestResult]] = []
    window: dict[tuple[int, int, int], bytes] = {}
    beat_budget = args.beat_budget
    spent = 0
    shapes: set[tuple[int, int]] = set()
    dropped = 0
    dropped_beats = 0
    largest_dropped = 0
    # Only the long replayed streams are budgeted.  Probes, refusals, masked
    # and quarantined cases and the repair case are always kept: they are what
    # cover the address space and the refusals, and they cost a handful of beats
    # each.  The budget exists because a decode step reads fifteen gigabytes and
    # no open-tool simulator will replay that beat by beat; which real requests
    # it dropped is published rather than left to be inferred.
    budgeted = {"executed", "plan_slot"}
    for request in requests:
        entry = plan.objects.get(request.object_id)
        estimate = 0
        if entry is not None and request.length:
            estimate = (request.length + SENSE_BYTES - 1) // SENSE_BYTES + 2
        shape = (request.object_id, request.length)
        if request.origin in budgeted and spent + estimate > beat_budget:
            dropped += 1
            dropped_beats += estimate
            largest_dropped = max(largest_dropped, request.length)
            continue
        shapes.add(shape)

        windowed = (
            reader_source.available
            and estimate <= args.window_beat_limit
            and len(window) + estimate <= args.window_granules
        )
        captured: dict[tuple[int, int, int], bytes] = {}

        def reader(shard: Shard, granule_address: int,
                   _windowed: bool = windowed) -> bytes:
            if _windowed:
                real = real_reader(shard, granule_address)
                if real is not None:
                    logical_row = granule_address // ROW_BYTES
                    physical_row = reference.row_repair.get(
                        (shard.resource_index, logical_row), logical_row
                    )
                    subword = (granule_address // SENSE_BYTES) % SUBWORDS_PER_ROW
                    captured[(shard.resource_index, physical_row, subword)] = real
                    return real
            return pattern_reader(shard, granule_address)

        saved_rowbuf = reference.rowbuf
        result = reference.run(
            request.object_id, request.offset, request.length, reader,
            collect=False,
        )
        if windowed and captured and (len(window) + len(captured)) > args.window_granules:
            # The window would overflow: replay this request against the
            # pattern instead, from the same row-buffer state, so the published
            # expectation is the one the RTL will be given.
            reference.rowbuf = saved_rowbuf
            windowed = False
            captured = {}
            result = reference.run(
                request.object_id, request.offset, request.length,
                pattern_reader, collect=False,
            )
        else:
            window.update(captured)
        request.windowed = bool(windowed and captured)
        spent += max(1, result.beats)
        kept.append((request, result))

    if not kept:
        raise SystemExit("no request survived the beat budget")

    # -- images --------------------------------------------------------
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)

    object_words: list[int] = []
    sorted_objects = plan.sorted_objects()
    if not sorted_objects:
        raise SystemExit("ROM plan has no placed object for the binding probe")
    if DESCRIPTOR_PLAN_PROBE_ID in plan.objects:
        raise SystemExit("the reserved descriptor/plan probe ID is a real plan object")
    for entry in sorted_objects:
        lo, hi = split64(entry.region_offset)
        slo, shi = split64(entry.size_bytes)
        object_words += [
            entry.object_id, entry.region_id, entry.shard_first,
            entry.shard_count, lo, hi, slo, shi,
        ]
    # A final high-ID object is loaded into the first otherwise-unused table
    # slot by the verification top.  Its compact plan entry is a genuine copy;
    # only the independently supplied descriptor base below is changed.
    probe_entry = sorted_objects[0]
    probe_region_lo, probe_region_hi = split64(probe_entry.region_offset)
    probe_size_lo, probe_size_hi = split64(probe_entry.size_bytes)
    object_words += [
        DESCRIPTOR_PLAN_PROBE_ID,
        probe_entry.region_id,
        probe_entry.shard_first,
        probe_entry.shard_count,
        probe_region_lo,
        probe_region_hi,
        probe_size_lo,
        probe_size_hi,
    ]
    write_words(out / "rom_object.hex", object_words, 8)

    descriptor_words: list[int] = []
    for entry in sorted_objects:
        record = plan.descriptors[entry.object_id]
        descriptor_words.append(entry.object_id)
        descriptor_words.extend(
            int.from_bytes(record[offset : offset + 4], "little")
            for offset in range(0, len(record), 4)
        )
    probe_descriptor = bytearray(plan.descriptors[probe_entry.object_id])
    alignment_log2 = probe_descriptor[66]
    if alignment_log2 >= 64:
        raise SystemExit("binding-probe source descriptor has invalid alignment")
    probe_base = int.from_bytes(probe_descriptor[72:80], "little")
    changed_base = probe_base + (1 << alignment_log2)
    if changed_base >= (1 << 64):
        raise SystemExit("binding-probe descriptor base would overflow")
    probe_descriptor[72:80] = changed_base.to_bytes(8, "little")
    probe_descriptor[48:52] = bytes(4)
    probe_descriptor[48:52] = record_crc(
        bytes(probe_descriptor), 48
    ).to_bytes(4, "little")
    descriptor_words.append(DESCRIPTOR_PLAN_PROBE_ID)
    descriptor_words.extend(
        int.from_bytes(probe_descriptor[offset : offset + 4], "little")
        for offset in range(0, len(probe_descriptor), 4)
    )
    write_words(out / "rom_descriptor.hex", descriptor_words, 33)

    shard_words: list[int] = []
    for shard in plan.shards:
        rlo, rhi = split64(shard.region_offset)
        blo, bhi = split64(shard.bytes)
        alo, ahi = split64(shard.resource_address)
        shard_words += [
            shard.region_id, shard.node_id, shard.reticle, shard.tile,
            shard.bank, shard.resource_index, rlo, rhi, blo, bhi, alo, ahi,
        ]
    write_words(out / "rom_shard.hex", shard_words, 12)

    repair_words: list[int] = []
    for entry_repair in plan.repair:
        kind = 1 if entry_repair["kind"] == "column" else 0
        repair_words += [
            entry_repair["resource_index"],
            entry_repair["logical_index"],
            entry_repair["spare_index"],
            (1 << 1) | kind,
        ]
    write_words(out / "rom_repair.hex", repair_words, 4)

    mask_words: list[int] = []
    for region_id in sorted(masked_regions):
        mask_words += [0, region_id]
    for index in sorted(broken):
        mask_words += [1, index]
    write_words(out / "rom_mask.hex", mask_words, 2)

    # The request record carries the length in one 32-bit word.  A plan whose
    # read unit exceeded that would be silently truncated into a shorter, legal
    # request, so it is refused here instead.
    oversize = [r for r, _ in kept if r.length >= (1 << 32)]
    if oversize:
        raise SystemExit(
            f"{len(oversize)} request(s) are 4 GiB or larger and the request "
            f"record carries a 32-bit length; the first is object "
            f"{oversize[0].object_id} for {oversize[0].length} bytes"
        )

    request_words: list[int] = []
    expect_words: list[int] = []
    total = collections.Counter()
    refusals_by_origin: collections.Counter = collections.Counter()
    masked_by_origin: collections.Counter = collections.Counter()
    for tag, (request, result) in enumerate(kept):
        lo, hi = split64(request.offset)
        request_words += [
            request.object_id, lo, hi, request.length,
            tag & 0xFFFF, 1 if request.windowed else 0, 0, 0,
        ]
        blo, bhi = split64(result.beats)
        ylo, yhi = split64(result.bytes)
        alo, ahi = split64(result.activations)
        dlo, dhi = split64(result.beat_digest)
        elo, ehi = split64(result.data_digest)
        record = [
            result.status, result.fault, blo, bhi, ylo, yhi, alo, ahi,
            dlo, dhi, elo, ehi,
        ]
        record += split256(result.first_beat)
        record += split256(result.last_beat)
        record += [tag & 0xFFFF, 1 if request.windowed else 0, 0, 0]
        assert len(record) == 32
        expect_words += record
        total["beats"] += result.beats
        total["bytes"] += result.bytes
        total["activations"] += result.activations
        if result.status == STATUS_MASKED:
            total["masked"] += 1
            masked_by_origin[request.origin] += 1
        if result.status == STATUS_FAULT:
            total["faults"] += 1
            refusals_by_origin[request.origin] += 1
    write_words(out / "rom_request.hex", request_words, 8)
    write_words(out / "rom_expect.hex", expect_words, 32)

    window_words: list[int] = []
    for (resource, row, subword) in sorted(window):
        data = window[(resource, row, subword)]
        window_words += [resource, row, subword]
        window_words += [
            int.from_bytes(data[i * 4 : i * 4 + 4], "little")
            for i in range(SENSE_BYTES // 4)
        ]
        window_words += [0]
        assert len(window_words) % 20 == 0
    write_words(out / "rom_window.hex", window_words, 20)

    marker_payload = json.dumps(
        {
            "requests": len(kept),
            "beats": total["beats"],
            "bytes": total["bytes"],
            "activations": total["activations"],
            "masked": total["masked"],
            "faults": total["faults"],
            "objects": len(plan.objects),
            "shards": len(plan.shards),
        },
        sort_keys=True,
    ).encode("utf-8")
    marker_value = int.from_bytes(hashlib.sha256(marker_payload).digest()[:8], "little")
    marker_lo, marker_hi = split64(marker_value)

    meta = [0] * 32
    meta[0] = len(plan.objects)
    meta[1] = len(plan.shards)
    meta[2] = len(plan.repair)
    meta[3] = len(masked_regions) + len(broken)
    meta[4] = len(kept)
    meta[5] = len(window)
    meta[6] = marker_lo
    meta[7] = marker_hi
    meta[8], meta[9] = split64(total["beats"])
    meta[10], meta[11] = split64(total["bytes"])
    meta[12], meta[13] = split64(total["activations"])
    meta[14], meta[15] = split64(total["masked"])
    meta[16], meta[17] = split64(total["faults"])
    # The table depths this set needs.  A set that outgrew a parameter would
    # otherwise alias silently onto a legal wrong entry, which is the failure
    # this whole campaign exists to catch; both checkers compare these against
    # the parameters the top was actually elaborated with.
    required = {
        # One object slot after the real plan is occupied by the explicit
        # descriptor/first-shard mismatch probe.
        "objects": len(plan.objects) + 1,
        "shards": len(plan.shards),
        "regions": max((r["region_id"] for r in plan.regions), default=-1) + 1,
        # The service holds a quarantine LIST, so what constrains it is how many
        # resources are withdrawn, not how many exist.
        "quarantine_entries": len(broken),
        "repair_entries": len(plan.repair),
        "requests": len(kept),
        "window_entries": len(window),
        "masks": len(masked_regions) + len(broken),
    }
    for slot, key in enumerate(
        (
            "objects",
            "shards",
            "regions",
            "quarantine_entries",
            "repair_entries",
            "requests",
            "window_entries",
            "masks",
        )
    ):
        meta[18 + slot] = required[key]
    write_words(out / "rom_meta.hex", meta, 8)

    marker = (
        f"ROM-SERVICE-OK requests={len(kept)} beats={total['beats']} "
        f"bytes={total['bytes']} activations={total['activations']} "
        f"masked={total['masked']} faults={total['faults']} "
        f"marker={marker_hi:08x}{marker_lo:08x}"
    )

    origins = collections.Counter(r.origin for r, _ in kept)
    faults = collections.Counter(
        result.fault for _, result in kept if result.status == STATUS_FAULT
    )
    vectors = {
        "schema": "opentallas.rtl.rom_service_vectors.v2",
        "product": args.product,
        "scenario": args.scenario,
        "deployment": {
            "deployment_id": deployment.deployment_id,
            "target_id": deployment.target_id,
            "model_id": deployment.model_id,
            "deployment_sha256": deployment.deployment_digest.hex(),
            "plan_id": deployment.notes["rom_plan"]["plan_id"],
        },
        "geometry": {
            "row_bytes": ROW_BYTES,
            "sense_bytes": SENSE_BYTES,
            "subwords_per_row": SUBWORDS_PER_ROW,
            "resource_bytes": plan.resource_bytes,
        },
        "plan": {
            "region_count": len(plan.regions),
            "placed_rom_object_count": len(plan.objects),
            "rom_object_count": len(plan.rom_object_ids),
            "unplaced_rom_objects": plan.unplaced,
            "shard_count": len(plan.shards),
            "resource_count": len(plan.resources),
            "repair_entry_count": len(plan.repair),
            "repair_row_entries": sum(
                1 for e in plan.repair if e["kind"] == "row"
            ),
            "repair_column_entries": sum(
                1 for e in plan.repair if e["kind"] == "column"
            ),
            "distributed_region_count": sum(
                1 for r in plan.regions if len(r["shards"]) > 1
            ),
            "max_shards_in_one_region": max(
                (len(r["shards"]) for r in plan.regions), default=0
            ),
            "memory_object_wire_records": {
                "count": len(plan.descriptors),
                "bytes_per_record": 128,
                "source": "exact admitted descriptor-table bytes",
                "paired_by_descriptor_table_index": True,
            },
            "synthetic_descriptor_plan_probe": {
                "object_id": DESCRIPTOR_PLAN_PROBE_ID,
                "descriptor_crc_valid": True,
                "changed_field": "base_address",
                "expected_fault": FAULT_DESCRIPTOR_PLAN,
            },
        },
        "runtime_health": {
            "masked_regions": sorted(masked_regions),
            "masked_region_keys": [
                region_by_id[r]["key"] for r in sorted(masked_regions)
            ],
            "quarantined_resources": sorted(broken),
        },
        "required_capacity": required,
        "requests": {
            "count": len(kept),
            "by_origin": dict(sorted(origins.items())),
            "dropped_for_beat_budget": dropped,
            "dropped_beat_estimate": dropped_beats,
            "largest_dropped_request_bytes": largest_dropped,
            "beat_budget": beat_budget,
            "windowed_count": sum(1 for r, _ in kept if r.windowed),
            "distinct_shapes": len(shapes),
        },
        "totals": {
            "beats": total["beats"],
            "bytes": total["bytes"],
            "activations": total["activations"],
            "masked": total["masked"],
            "faults": total["faults"],
            "fault_classes": {str(k): v for k, v in sorted(faults.items())},
            "refusals_by_origin": dict(sorted(refusals_by_origin.items())),
            "masked_by_origin": dict(sorted(masked_by_origin.items())),
            "placement_resources_entered": len(reference.resources_entered),
            "placement_resources_in_plan": len(plan.resources),
        },
        "window": {
            "granule_count": len(window),
            "real_bytes": len(window) * SENSE_BYTES,
            "source": "authenticated checkpoint segments named by the region plan"
            if reader_source.available
            else "unavailable: no checkpoint under the deployment root",
            "checkpoint_available": reader_source.available,
        },
        "executed_source": executed_summary,
        "required_marker": marker,
        "image_sha256": {
            name: sha256_file(out / name)
            for name in sorted(
                [
                    "rom_object.hex",
                    "rom_descriptor.hex",
                    "rom_shard.hex",
                    "rom_repair.hex",
                    "rom_mask.hex",
                    "rom_request.hex",
                    "rom_expect.hex",
                    "rom_window.hex",
                    "rom_meta.hex",
                ]
            )
        },
        "request_index": [
            {
                "tag": tag,
                "object_id": request.object_id,
                "offset": request.offset,
                "length": request.length,
                "origin": request.origin,
                "note": request.note,
                "windowed": request.windowed,
                "status": result.status,
                "fault": result.fault,
                "beats": result.beats,
                "activations": result.activations,
            }
            for tag, (request, result) in enumerate(kept)
        ],
    }
    (out / "rom_service_vectors.json").write_text(
        json.dumps(vectors, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return vectors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deployment", type=Path, required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--scenario", default="nominal")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, default=None)
    parser.add_argument("--executed", action="store_true",
                        help="record the ROM reads the program actually issues")
    parser.add_argument("--capability", type=Path, default=None)
    parser.add_argument("--workload", type=Path, default=None)
    parser.add_argument("--prompt-tokens", type=int, default=16)
    parser.add_argument("--max-new-tokens", type=int, default=1)
    parser.add_argument("--plan-slots", type=int, default=0,
                        help="slots per region to take from the compiled plan")
    parser.add_argument("--beat-budget", type=int, default=1_500_000)
    parser.add_argument("--window-beat-limit", type=int, default=4096)
    parser.add_argument("--window-granules", type=int, default=12000)
    parser.add_argument("--mask-region", action="append", default=[])
    parser.add_argument("--quarantine-resource", action="append", type=int,
                        default=[])
    args = parser.parse_args(argv)
    if args.executed and (args.capability is None or args.workload is None):
        raise SystemExit("--executed needs --capability and --workload")
    summary = build(args)
    print(f"product            {summary['product']} ({summary['scenario']})")
    print(f"ROM objects        {summary['plan']['placed_rom_object_count']} placed "
          f"of {summary['plan']['rom_object_count']} declared")
    if summary["plan"]["unplaced_rom_objects"]:
        for record in summary["plan"]["unplaced_rom_objects"]:
            print(f"  UNPLACED object {record['object_id']} "
                  f"{record['size_bytes']} B, bank_or_tile "
                  f"{record['declared_bank_or_tile']}, "
                  f"source {record.get('generator') or record.get('source_kind')}")
    print(f"shards             {summary['plan']['shard_count']} over "
          f"{summary['plan']['resource_count']} resources")
    print(f"requests           {summary['requests']['count']} "
          f"({summary['requests']['by_origin']})")
    print(f"beats              {summary['totals']['beats']}")
    print(f"bytes              {summary['totals']['bytes']}")
    print(f"activations        {summary['totals']['activations']}")
    print(f"masked / faults    {summary['totals']['masked']} / "
          f"{summary['totals']['faults']}")
    print(f"real-byte window   {summary['window']['granule_count']} granules "
          f"({summary['window']['real_bytes']} B)")
    print(f"marker             {summary['required_marker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
