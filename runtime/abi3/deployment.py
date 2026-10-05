"""ABI 3.0 deployment bundle: descriptor table, object sources, manifest.

A deployment is the complete authenticated input to the device.  It contains

``deployment.json``
    the canonical manifest, binding every digest;
``descriptors.bin``
    the ordered descriptor table -- descriptor ID *is* the table index;
``program.bin``
    the 256-byte program header followed by the instruction body.

Memory-object payloads are **not copied into the bundle**.  Each object declares
a *source*: zero-fill, a whole file, or an ordered list of byte segments in
already-authenticated files.  The segment form is what makes this program
tractable at all: a 16 GB Qwen weight image and a 156 GB DeepSeek weight image
are expressed as views over the locked checkpoint shards, with the accelerator's
tensor views supplying tiling through strides rather than through a relayout
pass.  Copying either image once per backend, per target, per rebuild would cost
more storage than the machine has and would prove nothing extra: the manifest
binds each segment's SHA-256, so the bytes the device reads are exactly the
bytes the checkpoint lock authenticated.

A symmetric cluster object may instead carry one equal-sized ordered segment
list per node.  This remains a manifest-side source declaration -- no wire
descriptor changes -- and lets every node's local byte zero name its own
authenticated expert shard without copying or slicing a digest-bound range.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .capability import canonical_json
from .constants import (
    ABI_MAJOR,
    ABI_MINOR,
    DESCRIPTOR_ALIGNMENT,
    NO_ID,
)
from .crc import sha256, sha256_hex
from .descriptors import (
    Descriptor,
    ExtendedDescriptorType,
)
from .records import split_program

DEPLOYMENT_SCHEMA = "opentallas.abi3.deployment.v1"

#: Domain of the canonical digest carried by a MEMORY_OBJECT whose manifest
#: source is node-indexed.  ``node_segments`` is a deployment-v1 manifest
#: extension, not a wire-format extension: the descriptor's existing
#: ``content_digest`` field carries this root and therefore needs no schema or
#: descriptor-layout amendment.
NODE_SEGMENTS_CONTENT_SCHEMA = "opentallas.abi3.node-segments-content.v1"


class DeploymentError(ValueError):
    """Raised when a deployment fails to build or fails admission."""


# ---------------------------------------------------------------------------
# Object sources
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class Segment:
    """One authenticated byte range of an existing file."""

    path: str
    offset: int
    bytes: int
    sha256: str | None = None

    def __post_init__(self) -> None:
        """Refuse ranges that Python slicing would otherwise reinterpret.

        A negative offset is meaningful to ``numpy`` as an index from the end
        of a mapping, while a negative byte count can cancel a positive range
        in an object's aggregate coverage check.  Neither is an ABI byte
        range.  Validate each segment before ``ObjectSource`` totals it so a
        digest-consistent manifest cannot turn arithmetic cancellation into an
        admitted out-of-bounds source map.
        """

        if self.offset < 0:
            raise DeploymentError(
                f"segment offset must be non-negative, got {self.offset}"
            )
        if self.bytes < 0:
            raise DeploymentError(
                f"segment byte count must be non-negative, got {self.bytes}"
            )

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "path": self.path,
            "offset": self.offset,
            "bytes": self.bytes,
        }
        if self.sha256 is not None:
            body["sha256"] = self.sha256
        return body


@dataclass(frozen=True)
class ObjectSource:
    """How a memory object's bytes are materialised.

    ``kind`` is ``"zero"`` (mutable state and scratch), ``"file"`` (a whole
    authenticated file), ``"segments"`` (one ordered concatenation of byte
    ranges shared by every node), or ``"node_segments"`` (one ordered,
    equally-sized concatenation per logical node).  The last form extends the
    manifest only; the symmetric MEMORY_OBJECT wire descriptor remains one
    node-local size and one object ID.  ``fill`` applies to ``"zero"`` only.
    """

    kind: str
    size_bytes: int
    segments: tuple[Segment, ...] = ()
    fill: int = 0
    generator: str = ""
    parameters: Mapping[str, Any] = dc_field(default_factory=dict)
    digest: str = ""
    node_segments: tuple[tuple[Segment, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.kind not in {
            "zero",
            "file",
            "segments",
            "node_segments",
            "generated",
        }:
            raise DeploymentError(f"unknown object source kind {self.kind!r}")
        if self.size_bytes < 0:
            raise DeploymentError("object size must be non-negative")
        if self.kind == "generated":
            # A derived constant -- a rotary coefficient table, a causal window
            # index table -- exists in no checkpoint, so it cannot be a segment
            # over authenticated bytes. It is instead named by a deterministic
            # generator and bound by the digest of its *result*, which the
            # device checks after materialising it. That keeps the "artifacts
            # only" property: the table is derived from declared parameters,
            # not injected, and a generator that drifts is caught.
            if not self.generator:
                raise DeploymentError("a generated object names no generator")
            if len(self.digest) != 64:
                raise DeploymentError(
                    "a generated object must bind the SHA-256 of its result"
                )
            if self.segments:
                raise DeploymentError("a generated object cannot declare segments")
            if self.node_segments:
                raise DeploymentError(
                    "a generated object cannot declare node segments"
                )
            return
        if self.kind == "zero":
            if self.segments or self.node_segments:
                raise DeploymentError("a zero object cannot declare segments")
            if not 0 <= self.fill <= 255:
                raise DeploymentError("fill byte out of range")
        elif self.kind == "node_segments":
            if self.segments:
                raise DeploymentError(
                    "a node-segments object cannot declare shared segments"
                )
            if not self.node_segments:
                raise DeploymentError(
                    "a node-segments object declares no node source maps"
                )
            for node_id, segments in enumerate(self.node_segments):
                if not segments:
                    raise DeploymentError(
                        f"node-segments object declares no segments for node "
                        f"{node_id}"
                    )
                total = sum(segment.bytes for segment in segments)
                if total != self.size_bytes:
                    raise DeploymentError(
                        f"node {node_id} segments cover {total} bytes, size is "
                        f"{self.size_bytes}"
                    )
        else:
            if self.node_segments:
                raise DeploymentError(
                    f"a {self.kind} object cannot declare node segments"
                )
            if not self.segments:
                raise DeploymentError(f"{self.kind} object declares no segments")
            total = sum(seg.bytes for seg in self.segments)
            if total != self.size_bytes:
                raise DeploymentError(
                    f"object segments cover {total} bytes, size is {self.size_bytes}"
                )
            if self.kind == "file" and len(self.segments) != 1:
                raise DeploymentError("a file object must declare exactly one segment")

    def to_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {"kind": self.kind, "size_bytes": self.size_bytes}
        if self.kind == "zero":
            body["fill"] = self.fill
        elif self.kind == "generated":
            body["generator"] = self.generator
            body["parameters"] = {k: v for k, v in sorted(self.parameters.items())}
            body["digest"] = self.digest
        elif self.kind == "node_segments":
            body["node_segments"] = [
                {
                    "node_id": node_id,
                    "segments": [segment.to_dict() for segment in segments],
                }
                for node_id, segments in enumerate(self.node_segments)
            ]
        else:
            body["segments"] = [seg.to_dict() for seg in self.segments]
        return body

    @classmethod
    def from_dict(cls, body: Mapping[str, Any]) -> "ObjectSource":
        kind = body["kind"]
        if kind == "zero":
            return cls("zero", int(body["size_bytes"]), (), int(body.get("fill", 0)))
        if kind == "generated":
            return cls(
                "generated",
                int(body["size_bytes"]),
                generator=str(body["generator"]),
                parameters=dict(body.get("parameters", {})),
                digest=str(body["digest"]),
            )
        if kind == "node_segments":
            entries = sorted(
                body["node_segments"], key=lambda entry: int(entry["node_id"])
            )
            ids = [int(entry["node_id"]) for entry in entries]
            if ids != list(range(len(entries))):
                raise DeploymentError(
                    "node-segments source IDs must be consecutive from zero"
                )
            node_segments = tuple(
                tuple(
                    Segment(
                        path=str(segment["path"]),
                        offset=int(segment["offset"]),
                        bytes=int(segment["bytes"]),
                        sha256=segment.get("sha256"),
                    )
                    for segment in entry["segments"]
                )
                for entry in entries
            )
            return cls(
                "node_segments",
                int(body["size_bytes"]),
                node_segments=node_segments,
            )
        segments = tuple(
            Segment(
                path=str(s["path"]),
                offset=int(s["offset"]),
                bytes=int(s["bytes"]),
                sha256=s.get("sha256"),
            )
            for s in body["segments"]
        )
        return cls(kind, int(body["size_bytes"]), segments)

    def segments_for_node(self, node_id: int) -> tuple[Segment, ...]:
        """The ordered source map visible to ``node_id``.

        Existing manifests keep the shared ``segments`` form and therefore
        return the same tuple for every node.  A node-indexed source refuses an
        undeclared node rather than silently falling back to another shard.
        """

        if self.kind != "node_segments":
            return self.segments
        if not 0 <= int(node_id) < len(self.node_segments):
            raise DeploymentError(
                f"node-segments source has {len(self.node_segments)} maps; "
                f"node {node_id} is not declared"
            )
        return self.node_segments[int(node_id)]

    def authenticated_content_digest(self) -> bytes:
        """Return the reproducible digest for an authenticated source.

        A shared segment source retains the ABI's established content identity:
        SHA-256 of the ordered concatenation of its 32-byte range digests.  A
        node-indexed source first derives that same identity for each node-local
        image, then hashes a canonical, domain-separated record containing the
        local object size and the ordered ``(node_id, image_digest)`` map.  The
        result commits both node ownership and each node's segment order while
        leaving paths and offsets to the deployment manifest digest, where
        provenance belongs.

        Zero sources use the all-zero descriptor sentinel.  Generated sources
        already declare the SHA-256 of their deterministic result.  Calling
        this method for a file or segment source requires every byte range to
        carry its own SHA-256; an unauthenticated range has no honest content
        identity to derive.
        """

        if self.kind == "zero":
            return bytes(32)
        if self.kind == "generated":
            return _digest_bytes(self.digest, "generated result")
        if self.kind != "node_segments":
            return _ordered_segment_content_digest(self.segments, self.kind)

        nodes = [
            {
                "node_id": node_id,
                "content_sha256": _ordered_segment_content_digest(
                    segments, f"node {node_id}"
                ).hex(),
            }
            for node_id, segments in enumerate(self.node_segments)
        ]
        root = {
            "schema": NODE_SEGMENTS_CONTENT_SCHEMA,
            "size_bytes": self.size_bytes,
            "node_count": len(nodes),
            "nodes": nodes,
        }
        return sha256(canonical_json(root))

    @staticmethod
    def zeros(size_bytes: int) -> "ObjectSource":
        return ObjectSource("zero", size_bytes)

    @staticmethod
    def generated(
        generator: str, parameters: Mapping[str, Any], size_bytes: int, digest: str
    ) -> "ObjectSource":
        return ObjectSource(
            "generated",
            size_bytes,
            generator=generator,
            parameters=dict(parameters),
            digest=digest,
        )


def _digest_bytes(value: str, label: str) -> bytes:
    """Decode one required SHA-256 value with a source-specific error."""

    if not isinstance(value, str) or len(value) != 64:
        raise DeploymentError(f"{label} must carry a 64-hex SHA-256 digest")
    try:
        digest = bytes.fromhex(value)
    except (TypeError, ValueError):
        digest = b""
    if len(digest) != 32:
        raise DeploymentError(f"{label} must carry a 64-hex SHA-256 digest")
    return digest


def _ordered_segment_content_digest(
    segments: Sequence[Segment], label: str
) -> bytes:
    """The established content identity of one ordered segmented image."""

    digest = _complete_ordered_segment_content_digest(segments, label)
    if digest is not None:
        return digest
    missing = next(
        index for index, segment in enumerate(segments) if segment.sha256 is None
    )
    raise DeploymentError(
        f"{label} segment {missing} has no authenticated content digest"
    )


def _complete_ordered_segment_content_digest(
    segments: Sequence[Segment], label: str
) -> bytes | None:
    """Return the ordered digest, or ``None`` for an incomplete legacy map.

    Every digest that *is* present is decoded even when another range omitted
    its digest.  Thus the shared-source compatibility path can distinguish a
    genuinely old, unauthenticated range map from a malformed authentication
    claim and never lets the latter hide behind the all-zero sentinel.
    """

    digests: list[bytes] = []
    missing = False
    for index, segment in enumerate(segments):
        if segment.sha256 is None:
            missing = True
            continue
        digests.append(_digest_bytes(segment.sha256, f"{label} segment {index}"))
    if missing:
        return None
    return sha256(b"".join(digests))


# ---------------------------------------------------------------------------
# Amendment A21: which state resources a deployment can stage
# ---------------------------------------------------------------------------
def staged_objects(table: "DescriptorTable") -> frozenset[int]:
    """Every memory object some descriptor in ``table`` names as a destination.

    Wire format section 12.11 (amendment A21).  A ``STATE.COMMIT`` publishes
    rows the transaction staged into the resource's *prepared* image, and the
    only ways a program can put a byte there are an operator output view and a
    remote-write communication endpoint.  A prepared image that appears in
    neither is one no transaction of this deployment can stage, and its commit
    therefore has no rows to publish.

    This is a property of the finished descriptor table, not a backend's
    choice, so it is derived once here and used by both the builder that
    declares ``commit_policy`` and the verifier that re-derives and checks it.
    Two backends cannot disagree about a fact neither of them states.
    """
    staged: set[int] = set()
    for descriptor in table.descriptors():
        kind = descriptor.descriptor_type
        if kind == int(ExtendedDescriptorType.OPERATOR):
            for slot in ("output_view_0", "output_view_1"):
                view_id = int(descriptor.payload[slot])
                if view_id == NO_ID or not 0 <= view_id < len(table):
                    continue
                view = table[view_id]
                if view.descriptor_type == int(ExtendedDescriptorType.TENSOR_VIEW):
                    staged.add(int(view.primary_object_id))
        elif kind == int(ExtendedDescriptorType.COMMUNICATION):
            # A collective or a remote DMA writes its local endpoint, and a
            # send writes the peer's; both are destinations.
            staged.add(int(descriptor.payload["local_object_id"]))
            staged.add(int(descriptor.payload["remote_object_id"]))
    staged.discard(NO_ID)
    return frozenset(staged)


# ---------------------------------------------------------------------------
# Amendment A25: which state resources have a ring for a row axis
# ---------------------------------------------------------------------------
#: The derived-constant generator whose result is a ring of destination rows.
#: ``runtime.sim.generators.ring_indices_v1`` is ``position mod modulus``, and a
#: movement that addresses its destination with it is writing a ring.
RING_INDEX_GENERATOR = "ring_indices_v1"


def ring_staged_objects(
    table: "DescriptorTable", objects: Mapping[int, ObjectSource]
) -> dict[int, frozenset[int]]:
    """Every memory object a scatter addresses through a ring, and its moduli.

    Wire format section 12.16 (amendment A25).  ``DMA.SCATTER`` is the one
    movement whose index operand names its *destination* rows -- a gather's
    index names its source -- so a scatter whose index is a ring table writes a
    ring, and the ring's size is the table's declared ``modulus``.  Both are
    facts about the finished deployment: the index is a descriptor's operand
    and the modulus is a parameter of a generated object whose result digest
    the manifest binds, so a generator that drifts is caught before the
    derivation is.

    The value is a *set* because an object addressed through two different
    moduli has two candidate row axes and is not a resource this amendment can
    describe.  Returning both lets the caller refuse it by name rather than
    pick one or, worse, fall quietly back to the span.
    """
    from .constants import Dma, Major

    seen: dict[int, set[int]] = {}
    for descriptor in table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.OPERATOR):
            continue
        payload = descriptor.payload
        if int(payload["engine_family"]) != int(Major.DMA):
            continue
        if int(payload["engine_sub"]) != int(Dma.SCATTER):
            continue
        index_object = _view_object(table, int(payload["input_view_0"]))
        if index_object is None:
            continue
        source = objects.get(index_object)
        if source is None or source.kind != "generated":
            continue
        if source.generator != RING_INDEX_GENERATOR:
            continue
        modulus = int(source.parameters.get("modulus", 0))
        if modulus <= 0:
            continue
        for slot in ("output_view_0", "output_view_1"):
            destination = _view_object(table, int(payload[slot]))
            if destination is None:
                continue
            seen.setdefault(destination, set()).add(modulus)
    return {oid: frozenset(m) for oid, m in seen.items()}


def _view_object(table: "DescriptorTable", view_id: int) -> int | None:
    """The memory object ``view_id`` addresses, or ``None`` if it names none."""
    if view_id == NO_ID or not 0 <= view_id < len(table):
        return None
    view = table[view_id]
    if view.descriptor_type != int(ExtendedDescriptorType.TENSOR_VIEW):
        return None
    oid = int(view.primary_object_id)
    return None if oid == NO_ID else oid


def derive_commit_policies(
    table: "DescriptorTable", objects: Mapping[int, ObjectSource]
) -> tuple[dict[int, int], list[str]]:
    """The ``commit_policy`` every STATE descriptor must declare, and why.

    Wire format sections 12.11 and 12.16.  One rule, three answers, derived
    from the finished deployment rather than chosen by a backend:

    * the prepared image is no descriptor's destination -> ``UNSTAGED``;
    * it is a destination, and a scatter addresses it through a ring whose
      modulus divides ``capacity_rows`` -> ``SATURATING``;
    * otherwise -> ``REQUEST_SPAN``.

    Returns the mapping and a list of problems.  A problem is a deployment this
    amendment cannot describe -- a ring that does not divide the capacity it
    wraps -- and is refused by the builder and reported by the verifier rather
    than resolved by guessing which of the two numbers is the real row axis.
    """
    from .constants import CommitPolicy

    staged = staged_objects(table)
    rings = ring_staged_objects(table, objects)
    policies: dict[int, int] = {}
    problems: list[str] = []
    for state_id in table.ids_of_type(int(ExtendedDescriptorType.STATE)):
        payload = table[state_id].payload
        prepared = int(payload["prepared_object_id"])
        capacity = int(payload["capacity_rows"])
        if prepared not in staged:
            policies[state_id] = int(CommitPolicy.UNSTAGED)
            continue
        moduli = rings.get(prepared)
        if not moduli:
            policies[state_id] = int(CommitPolicy.REQUEST_SPAN)
            continue
        if len(moduli) > 1:
            problems.append(
                f"state {state_id}: prepared image {prepared} is staged through "
                f"rings of {', '.join(str(m) for m in sorted(moduli))} rows; a "
                "resource with two candidate row axes is not one amendment A25 "
                "can describe, and it is refused rather than assigned one"
            )
            policies[state_id] = int(CommitPolicy.REQUEST_SPAN)
            continue
        modulus = next(iter(moduli))
        if capacity <= 0 or modulus > capacity or capacity % modulus:
            problems.append(
                f"state {state_id}: prepared image {prepared} is staged through "
                f"a ring of {modulus} rows, which is not a whole divisor of its "
                f"declared capacity_rows {capacity}; the resource's row axis is "
                "then neither the ring nor the capacity and amendment A25 "
                "refuses to choose one"
            )
            policies[state_id] = int(CommitPolicy.REQUEST_SPAN)
            continue
        cursor = int(payload["initial_cursor_rows"])
        if not 0 <= cursor < capacity:
            problems.append(
                f"state {state_id}: initial_cursor_rows {cursor} is not a slot "
                f"of its own ring of {capacity} rows; a saturating cursor is a "
                "slot index and has nowhere else to point"
            )
        policies[state_id] = int(CommitPolicy.SATURATING)
    return policies, problems


# ---------------------------------------------------------------------------
# Descriptor table
# ---------------------------------------------------------------------------
class DescriptorTable:
    """Ordered descriptor table.  The descriptor ID is the table index."""

    __slots__ = ("_records", "_descriptors")

    def __init__(self) -> None:
        self._records: list[bytes] = []
        self._descriptors: list[Descriptor] = []

    def __len__(self) -> int:
        return len(self._records)

    def add(self, descriptor: Descriptor) -> int:
        """Append ``descriptor`` and return its assigned ID."""
        index = len(self._records)
        descriptor.descriptor_id = index
        self._records.append(descriptor.encode())
        self._descriptors.append(descriptor)
        return index

    def rewrite(self, descriptor_id: int) -> None:
        """Re-encode one descriptor whose payload was amended after insertion.

        The table caches each record's bytes at :meth:`add`, so a field a later
        pass fills in -- amendment A21's ``commit_policy``, which is a fact
        about the finished descriptor table and cannot be known while that
        table is still being built -- would otherwise be present in the
        in-memory payload and absent from the encoded record the digest binds.
        """
        self._records[descriptor_id] = self._descriptors[descriptor_id].encode()

    def __getitem__(self, descriptor_id: int) -> Descriptor:
        if not 0 <= descriptor_id < len(self._descriptors):
            raise DeploymentError(f"descriptor ID {descriptor_id} is out of range")
        return self._descriptors[descriptor_id]

    def get(self, descriptor_id: int, expected_type: int | None = None) -> Descriptor:
        descriptor = self[descriptor_id]
        if expected_type is not None and descriptor.descriptor_type != expected_type:
            raise DeploymentError(
                f"descriptor {descriptor_id} is "
                f"{ExtendedDescriptorType(descriptor.descriptor_type).name}, "
                f"expected {ExtendedDescriptorType(expected_type).name}"
            )
        return descriptor

    def encode(self) -> bytes:
        return b"".join(self._records)

    @property
    def digest(self) -> bytes:
        return sha256(self.encode())

    def descriptors(self) -> tuple[Descriptor, ...]:
        return tuple(self._descriptors)

    def ids_of_type(self, descriptor_type: int) -> tuple[int, ...]:
        return tuple(
            i
            for i, d in enumerate(self._descriptors)
            if d.descriptor_type == descriptor_type
        )

    @classmethod
    def decode(cls, blob: bytes) -> "DescriptorTable":
        """Decode an ordered table, failing closed on every structural error."""
        table = cls()
        offset = 0
        index = 0
        while offset < len(blob):
            if offset + DESCRIPTOR_ALIGNMENT > len(blob):
                raise DeploymentError("truncated descriptor table")
            total = int.from_bytes(blob[offset + 8 : offset + 12], "little")
            if total < DESCRIPTOR_ALIGNMENT or total % DESCRIPTOR_ALIGNMENT:
                raise DeploymentError(
                    f"descriptor {index} declares invalid size {total}"
                )
            if offset + total > len(blob):
                raise DeploymentError(f"descriptor {index} runs past the table")
            record = blob[offset : offset + total]
            descriptor = Descriptor.decode(record, index)
            table._records.append(record)
            table._descriptors.append(descriptor)
            offset += total
            index += 1
        if not table._records:
            raise DeploymentError("descriptor table is empty")
        return table


# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class Deployment:
    """A complete, digest-bound ABI 3.0 deployment."""

    deployment_id: int
    generation: int
    target_id: str
    model_id: str
    backend: str
    topology_class: int
    capability_digest: str
    table: DescriptorTable
    program: bytes
    objects: dict[int, ObjectSource]
    entrypoints: tuple[dict[str, int], ...]
    required_features: bytes
    source_identity: dict[str, Any] = dc_field(default_factory=dict)
    notes: dict[str, Any] = dc_field(default_factory=dict)
    root: Path | None = None

    # -- digests ---------------------------------------------------------
    def object_table(self) -> list[dict[str, Any]]:
        return [
            {"object_id": oid, "source": self.objects[oid].to_dict()}
            for oid in sorted(self.objects)
        ]

    def manifest(self) -> dict[str, Any]:
        header, _ = split_program(self.program)
        body = {
            "schema": DEPLOYMENT_SCHEMA,
            "abi": {"major": ABI_MAJOR, "minor": ABI_MINOR},
            "deployment_id": self.deployment_id,
            "generation": self.generation,
            "target_id": self.target_id,
            "model_id": self.model_id,
            "backend": self.backend,
            "topology_class": int(self.topology_class),
            "capability_digest": self.capability_digest,
            "descriptor_count": len(self.table),
            "descriptor_table_sha256": self.table.digest.hex(),
            "program_sha256": sha256_hex(self.program),
            "program_body_sha256": header.body_digest.hex(),
            "instruction_count": header.instruction_count,
            "max_retired_work": header.max_retired_work,
            "topology_digest": header.topology_digest.hex(),
            "required_features": self.required_features.hex(),
            "entrypoints": [dict(sorted(e.items())) for e in self.entrypoints],
            "objects": self.object_table(),
            "source_identity": self.source_identity,
            "notes": self.notes,
        }
        return body

    def digest_body(self) -> dict[str, Any]:
        """The subset of the manifest the deployment digest covers.

        ``program_sha256`` is excluded because the program *header* carries the
        deployment digest: including the whole program would make the digest
        depend on itself.  ``program_body_sha256`` is retained and is what
        actually binds the instructions, and the header separately binds the
        descriptor table and topology digests, so nothing is left unbound.
        """
        body = self.manifest()
        body.pop("program_sha256", None)
        body.pop("deployment_sha256", None)
        return body

    @property
    def deployment_digest(self) -> bytes:
        """SHA-256 of the canonical digest body (see :meth:`digest_body`)."""
        return sha256(canonical_json(self.digest_body()))

    def object_content_digest_errors(self) -> tuple[str, ...]:
        """Return every manifest-source/MEMORY_OBJECT identity disagreement.

        ``file`` and shared ``segments`` sources existed before range hashes
        were mandatory.  An incomplete legacy map therefore remains admissible
        only while its descriptor carries the historical all-zero sentinel.
        Once every range supplies a valid hash, the descriptor must carry the
        ordered composite digest.  All other source kinds have unambiguous
        digest semantics and are always checked exactly.

        This non-raising form is shared with the in-memory verifier so malformed
        supplied hashes become an ordinary failed admission report.  Bundle
        read/write use :meth:`validate_object_content_digests` below to retain
        their fail-fast boundary.
        """

        errors: list[str] = []
        for object_id, source in sorted(self.objects.items()):
            label = source.kind.replace("_", "-")
            try:
                descriptor = self.table[object_id]
            except DeploymentError:
                errors.append(f"{label} source names missing object {object_id}")
                continue
            if descriptor.descriptor_type != int(
                ExtendedDescriptorType.MEMORY_OBJECT
            ):
                errors.append(
                    f"{label} source {object_id} does not name a "
                    "MEMORY_OBJECT descriptor"
                )
                continue

            recorded = descriptor.payload["content_digest"]
            try:
                if source.kind in {"file", "segments"}:
                    expected = _complete_ordered_segment_content_digest(
                        source.segments, source.kind
                    )
                    if expected is None:
                        if recorded != bytes(32):
                            errors.append(
                                f"object {object_id}: legacy {label} source with "
                                "an unauthenticated range requires the all-zero "
                                "MEMORY_OBJECT content digest sentinel"
                            )
                        continue
                else:
                    expected = source.authenticated_content_digest()
            except DeploymentError as exc:
                errors.append(
                    f"object {object_id}: invalid {label} content identity: {exc}"
                )
                continue

            if recorded != expected:
                errors.append(
                    f"object {object_id} {label} content digest does not match "
                    "its MEMORY_OBJECT descriptor"
                )
        return tuple(errors)

    def validate_object_content_digests(self) -> None:
        """Fail when any object source is not bound by its wire descriptor."""

        errors = self.object_content_digest_errors()
        if errors:
            raise DeploymentError(errors[0])

    # -- publication -----------------------------------------------------
    def write(self, root: Path) -> Path:
        self.validate_object_content_digests()
        root = Path(root)
        root.mkdir(parents=True, exist_ok=True)
        (root / "descriptors.bin").write_bytes(self.table.encode())
        (root / "program.bin").write_bytes(self.program)
        manifest = self.manifest()
        manifest["deployment_sha256"] = self.deployment_digest.hex()
        (root / "deployment.json").write_bytes(canonical_json(manifest))
        self.root = root
        return root

    @classmethod
    def read(cls, root: Path) -> "Deployment":
        root = Path(root)
        manifest = json.loads((root / "deployment.json").read_text())
        if manifest.get("schema") != DEPLOYMENT_SCHEMA:
            raise DeploymentError("unexpected deployment schema")
        table = DescriptorTable.decode((root / "descriptors.bin").read_bytes())
        program = (root / "program.bin").read_bytes()
        if table.digest.hex() != manifest["descriptor_table_sha256"]:
            raise DeploymentError("descriptor table digest does not match manifest")
        if sha256_hex(program) != manifest["program_sha256"]:
            raise DeploymentError("program digest does not match manifest")
        objects = {
            int(entry["object_id"]): ObjectSource.from_dict(entry["source"])
            for entry in manifest["objects"]
        }
        deployment = cls(
            deployment_id=manifest["deployment_id"],
            generation=manifest["generation"],
            target_id=manifest["target_id"],
            model_id=manifest["model_id"],
            backend=manifest["backend"],
            topology_class=manifest["topology_class"],
            capability_digest=manifest["capability_digest"],
            table=table,
            program=program,
            objects=objects,
            entrypoints=tuple(manifest["entrypoints"]),
            required_features=bytes.fromhex(manifest["required_features"]),
            source_identity=manifest.get("source_identity", {}),
            notes=manifest.get("notes", {}),
            root=root,
        )
        deployment.validate_object_content_digests()
        recorded = manifest.get("deployment_sha256")
        if recorded is not None and deployment.deployment_digest.hex() != recorded:
            raise DeploymentError("deployment manifest digest mismatch")
        header, _ = split_program(program)
        if header.deployment_digest != deployment.deployment_digest:
            raise DeploymentError(
                "program header does not bind this deployment manifest"
            )
        if header.descriptor_table_digest != table.digest:
            raise DeploymentError(
                "program header does not bind this descriptor table"
            )
        return deployment


def resolve_path(root: Path | None, path: str) -> Path:
    """Resolve an object-source path relative to the deployment root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    if root is None:
        raise DeploymentError(f"relative object path {path!r} needs a deployment root")
    return (root / candidate).resolve()
