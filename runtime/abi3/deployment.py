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
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field as dc_field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .capability import canonical_json, digest_of
from .constants import (
    ABI_MAJOR,
    ABI_MINOR,
    DESCRIPTOR_ALIGNMENT,
    NO_ID,
    StorageClass,
    TopologyClass,
)
from .crc import sha256, sha256_hex
from .descriptors import (
    Descriptor,
    ExtendedDescriptorType,
    decode_entrypoint_table,
)
from .layout import RecordError
from .records import ProgramHeader, split_program

DEPLOYMENT_SCHEMA = "opentallas.abi3.deployment.v1"


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
    authenticated file) or ``"segments"`` (an ordered concatenation of byte
    ranges).  ``fill`` applies to ``"zero"`` only.
    """

    kind: str
    size_bytes: int
    segments: tuple[Segment, ...] = ()
    fill: int = 0
    generator: str = ""
    parameters: Mapping[str, Any] = dc_field(default_factory=dict)
    digest: str = ""

    def __post_init__(self) -> None:
        if self.kind not in {"zero", "file", "segments", "generated"}:
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
            return
        if self.kind == "zero":
            if self.segments:
                raise DeploymentError("a zero object cannot declare segments")
            if not 0 <= self.fill <= 255:
                raise DeploymentError("fill byte out of range")
        else:
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

    # -- publication -----------------------------------------------------
    def write(self, root: Path) -> Path:
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
