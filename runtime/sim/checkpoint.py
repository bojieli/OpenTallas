"""Serialise and restore the mutable state of an ABI 3.0 functional device.

A deployment is split, by construction, into bytes that are *derived* and bytes
that are *accumulated*.  Weights arrive as authenticated segments of the locked
checkpoint and are mapped read-only; derived constants -- rotary tables, window
index tables -- are re-materialised from a named generator and re-checked
against the digest the deployment binds.  Neither can differ between two
processes that read the same deployment, so neither belongs in a checkpoint.

What is left is the private byte buffer of every zero-filled object: the KV
state images, the activation scratch, the token ring and the input window.  That
set, plus the host-visible session bookkeeping (position, generation, cursor
rows, the produced tokens), is the entire mutable state of the device.  This
module writes exactly that set and restores exactly that set, so a process that
loads a checkpoint is in the state the writing process was in when it stopped --
not approximately, and not "in the parts we thought mattered".

Three properties make the claim checkable rather than asserted:

*Completeness is proved, not assumed.*  :func:`save_device_state` refuses to
write a checkpoint if any writable object is not one it serialises.  A future
backend that makes a mapped object writable therefore fails loudly here instead
of silently producing a checkpoint that is missing state.

*The payload is compacted losslessly.*  A Qwen deployment's mutable image is
3.3 GB, almost all of it still at its fill byte; only the byte runs that differ
from the fill are stored.  This is a storage decision, not a semantic one, and
it is checked: the manifest binds the SHA-256 of each object's *whole*
contents, and a restore that does not reproduce that digest raises.

*The target is bound.*  A checkpoint records the deployment and capability
digests it was taken under and refuses to load into a different one.  Restarting
into a different program is not a restart.

Where this sits in the ABI.  The wire format already names the host operations
``CHECKPOINT_SESSION = 0x12`` and ``RESTORE_SESSION = 0x13`` (section 6), but it
does not define the payload they move, and the functional device does not serve
either opcode: :meth:`Device.submit` handles only session creation and
destruction, with generation driven through the runtime driver.  This module is
the payload format behind those two opcodes at the runtime boundary.  It is not
a submission through the host queue, and it does not claim to be one: a Qwen
deployment's mutable image is 3.3 GB and its largest host-visible window is
about 1 MB, so a checkpoint could not cross that boundary as a host window at
all in the deployments this repository builds today.
"""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from runtime.abi3.capability import canonical_json
from runtime.sim.device import Device, Session, StateResource

SCHEMA = "opentallas.abi3.device_checkpoint.v1"

#: Granularity of the fill-run scan.  Small enough that a KV window written for
#: a hundred positions does not drag its whole 33 MB plane into the payload,
#: large enough that the manifest stays short.
BLOCK_BYTES = 1 << 16

#: One stored run: byte offset then byte length, little endian.
RUN_HEADER = struct.Struct("<QQ")
FILE_MAGIC = b"ABI3CKPT"


class CheckpointError(Exception):
    """Raised when a checkpoint cannot be written, or cannot be trusted."""


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def save_device_state(
    device: Device,
    session: Session,
    path: Path,
    *,
    host_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write every mutable byte of ``device`` and ``session`` under ``path``.

    ``host_state`` is the driver's own bookkeeping -- the generated tokens, the
    next decode position, the transaction counter.  It is carried verbatim: the
    device cannot reconstruct it, and a restart that guesses it is not a
    restart.
    """
    if getattr(device, "node_count", 1) > 1:
        # Every node of a cluster has its own arena and its own state images,
        # and this walks one of them.  A checkpoint that saved node zero and
        # restored thirty-two would resume a generation from thirty-one empty
        # KV caches and produce tokens from a computation that never happened,
        # which is exactly what "a checkpoint that omits writable state is not a
        # checkpoint" already says below.  So it fails closed until it walks
        # every arena.
        raise CheckpointError(
            f"this device has {device.node_count} nodes and this checkpoint "
            "serialises one arena; a multi-node checkpoint must carry every "
            "node's state"
        )
    path = Path(path)
    (path / "objects").mkdir(parents=True, exist_ok=True)

    serialised: set[int] = set()
    objects: list[dict[str, Any]] = []
    for object_id in sorted(device.memory.objects):
        obj = device.memory.objects[object_id]
        source = device.deployment.objects.get(object_id)
        if source is None:
            raise CheckpointError(f"object {object_id} has no declared source")
        if source.kind != "zero":
            # Mapped and generated objects are re-derived from the deployment
            # and re-authenticated when the device is built.  They are recorded
            # in the manifest so the checkpoint states what it relies on.
            continue
        buffer = obj.anonymous_buffer()
        if buffer is None:  # pragma: no cover -- a zero object owns a buffer
            raise CheckpointError(
                f"object {object_id} declares a zero source but owns no buffer"
            )
        objects.append(_write_object(path, object_id, obj, buffer, int(source.fill)))
        serialised.add(object_id)

    missing = sorted(
        object_id
        for object_id, obj in device.memory.objects.items()
        if obj.writable and object_id not in serialised
    )
    if missing:
        raise CheckpointError(
            f"objects {missing} are writable but are not serialised; a "
            "checkpoint that omits writable state is not a checkpoint"
        )

    body: dict[str, Any] = {
        "schema": SCHEMA,
        "deployment": {
            "deployment_id": device.deployment.deployment_id,
            "generation": device.deployment.generation,
            "target_id": device.deployment.target_id,
            "backend": device.deployment.backend,
            "deployment_digest": device.deployment.deployment_digest.hex(),
            "capability_digest": device.capability.digest,
        },
        "device": {
            "next_session": device._next_session,
            "device_cycle": device._device_cycle,
            "counters": device.counters.snapshot(),
        },
        "session": _session_to_dict(session),
        "objects": objects,
        "derived_objects": [
            {"object_id": object_id, "kind": source.kind}
            for object_id, source in sorted(device.deployment.objects.items())
            if source.kind != "zero"
        ],
        "block_bytes": BLOCK_BYTES,
        "host_state": dict(host_state or {}),
    }
    (path / "checkpoint.json").write_bytes(canonical_json(body))
    return body


def _write_object(
    path: Path,
    object_id: int,
    obj: Any,
    buffer: np.ndarray,
    fill: int,
) -> dict[str, Any]:
    """Store the runs of ``buffer`` that differ from ``fill`` plus its digest."""
    runs = _fill_runs(buffer, fill)
    blob = path / "objects" / f"{object_id:05d}.bin"
    digest = hashlib.sha256()
    stored = 0
    with blob.open("wb") as handle:
        handle.write(FILE_MAGIC)
        handle.write(RUN_HEADER.pack(int(buffer.size), len(runs)))
        for start, stop in runs:
            handle.write(RUN_HEADER.pack(start, stop - start))
            handle.write(buffer[start:stop].tobytes())
            stored += stop - start
    # The digest covers the whole object, not the stored runs: it is what makes
    # the fill-run compaction checkable rather than believed.
    for begin in range(0, int(buffer.size), 1 << 24):
        digest.update(buffer[begin : begin + (1 << 24)].tobytes())
    return {
        "object_id": object_id,
        "size_bytes": int(buffer.size),
        "storage_class": obj.storage_class.name,
        "writable": bool(obj.writable),
        "fill": fill,
        "run_count": len(runs),
        "stored_bytes": stored,
        "sha256": digest.hexdigest(),
        "file": f"objects/{object_id:05d}.bin",
    }


def _fill_runs(buffer: np.ndarray, fill: int) -> list[tuple[int, int]]:
    """Byte ranges that differ from ``fill``, snapped to the block grid."""
    size = int(buffer.size)
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for begin in range(0, size, BLOCK_BYTES):
        end = min(begin + BLOCK_BYTES, size)
        if bool(np.any(buffer[begin:end] != fill)):
            if start is None:
                start = begin
        elif start is not None:
            runs.append((start, begin))
            start = None
    if start is not None:
        runs.append((start, size))
    return runs


def _session_to_dict(session: Session) -> dict[str, Any]:
    return {
        "session_id": session.session_id,
        "generation": session.generation,
        "position": session.position,
        "tokens": list(session.tokens),
        "generated": list(session.generated),
        "finished": bool(session.finished),
        "eos_reason": int(session.eos_reason),
        "states": [
            {
                "descriptor_id": state.descriptor_id,
                "state_class": state.state_class,
                "committed_object_id": state.committed_object_id,
                "prepared_object_id": state.prepared_object_id,
                "row_bytes": state.row_bytes,
                "capacity_rows": state.capacity_rows,
                "cursor_rows": state.cursor_rows,
                "generation": state.generation,
                "open_prepare": bool(state.open_prepare),
            }
            for state in sorted(session.states.values(), key=lambda s: s.descriptor_id)
        ],
    }


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def read_manifest(path: Path) -> dict[str, Any]:
    return json.loads((Path(path) / "checkpoint.json").read_text())


def restore_device_state(
    device: Device, path: Path
) -> tuple[Session, dict[str, Any]]:
    """Put ``device`` into the state the checkpoint under ``path`` records.

    Returns the restored session and the checkpoint manifest.  Every restored
    object's whole-contents SHA-256 is re-checked against the manifest, so a
    silent partial restore is not possible.
    """
    path = Path(path)
    body = read_manifest(path)
    if body.get("schema") != SCHEMA:
        raise CheckpointError(f"checkpoint schema {body.get('schema')!r} is not {SCHEMA}")

    declared = body["deployment"]
    actual_deployment = device.deployment.deployment_digest.hex()
    if declared["deployment_digest"] != actual_deployment:
        raise CheckpointError(
            f"checkpoint was taken on deployment {declared['deployment_digest'][:16]}, "
            f"this device runs {actual_deployment[:16]}; restarting into a "
            "different program is not a restart"
        )
    if declared["capability_digest"] != device.capability.digest:
        raise CheckpointError(
            f"checkpoint capability {declared['capability_digest'][:16]} does not "
            f"match this device's {device.capability.digest[:16]}"
        )
    if int(body.get("block_bytes", 0)) <= 0:
        raise CheckpointError("checkpoint declares no block size")

    for entry in body["objects"]:
        _restore_object(device, path, entry)

    device._next_session = int(body["device"]["next_session"])
    device._device_cycle = int(body["device"]["device_cycle"])
    device.counters.reset()
    for name, value in body["device"]["counters"].items():
        device.counters.add(name, int(value))

    session = _session_from_dict(device, body["session"])
    device.sessions = {session.session_id: session}
    return session, body


def _restore_object(device: Device, path: Path, entry: Mapping[str, Any]) -> None:
    object_id = int(entry["object_id"])
    obj = device.memory.objects.get(object_id)
    if obj is None:
        raise CheckpointError(f"checkpoint names object {object_id}, which does not exist")
    buffer = obj.anonymous_buffer()
    if buffer is None:
        raise CheckpointError(
            f"object {object_id} is mapped in this device but was a private "
            "buffer when the checkpoint was written"
        )
    if int(buffer.size) != int(entry["size_bytes"]):
        raise CheckpointError(
            f"object {object_id} is {buffer.size} bytes here and "
            f"{entry['size_bytes']} bytes in the checkpoint"
        )
    blob = path / entry["file"]
    with blob.open("rb") as handle:
        if handle.read(len(FILE_MAGIC)) != FILE_MAGIC:
            raise CheckpointError(f"{blob} is not a checkpoint object payload")
        size, run_count = RUN_HEADER.unpack(handle.read(RUN_HEADER.size))
        if size != int(entry["size_bytes"]):
            raise CheckpointError(f"{blob} declares {size} bytes, manifest says {entry['size_bytes']}")
        # Start from the declared fill so that a byte the writing process left
        # at its fill value is restored as that value even if this process's
        # buffer has been touched.
        buffer[:] = np.uint8(int(entry["fill"]))
        for _ in range(run_count):
            start, length = RUN_HEADER.unpack(handle.read(RUN_HEADER.size))
            payload = handle.read(length)
            if len(payload) != length:
                raise CheckpointError(f"{blob} is truncated inside a run at {start}")
            buffer[start : start + length] = np.frombuffer(payload, dtype=np.uint8)
        if handle.read(1):
            raise CheckpointError(f"{blob} has trailing bytes after its last run")

    digest = hashlib.sha256()
    for begin in range(0, int(buffer.size), 1 << 24):
        digest.update(buffer[begin : begin + (1 << 24)].tobytes())
    if digest.hexdigest() != entry["sha256"]:
        raise CheckpointError(
            f"object {object_id} restored to digest {digest.hexdigest()[:16]}, the "
            f"checkpoint binds {entry['sha256'][:16]}"
        )


def _session_from_dict(device: Device, body: Mapping[str, Any]) -> Session:
    session = Session(
        session_id=int(body["session_id"]),
        generation=int(body["generation"]),
        position=int(body["position"]),
        tokens=[int(t) for t in body["tokens"]],
        generated=[int(t) for t in body["generated"]],
        finished=bool(body["finished"]),
        eos_reason=int(body["eos_reason"]),
    )
    template = device.create_session()
    device.sessions.pop(template.session_id, None)
    device._next_session -= 1
    declared = {state["descriptor_id"]: state for state in body["states"]}
    if set(declared) != set(template.states):
        raise CheckpointError(
            f"checkpoint binds state resources {sorted(declared)}, this "
            f"deployment declares {sorted(template.states)}"
        )
    for descriptor_id, state in declared.items():
        fresh = template.states[descriptor_id]
        for field in (
            "state_class",
            "committed_object_id",
            "prepared_object_id",
            "row_bytes",
            "capacity_rows",
        ):
            if int(state[field]) != int(getattr(fresh, field)):
                raise CheckpointError(
                    f"state {descriptor_id}: checkpoint {field}={state[field]} "
                    f"but the deployment declares {getattr(fresh, field)}"
                )
        session.states[descriptor_id] = StateResource(
            descriptor_id=descriptor_id,
            state_class=int(state["state_class"]),
            committed_object_id=int(state["committed_object_id"]),
            prepared_object_id=int(state["prepared_object_id"]),
            row_bytes=int(state["row_bytes"]),
            capacity_rows=int(state["capacity_rows"]),
            cursor_rows=int(state["cursor_rows"]),
            generation=int(state["generation"]),
            open_prepare=bool(state["open_prepare"]),
        )
    return session


__all__ = [
    "BLOCK_BYTES",
    "CheckpointError",
    "FILE_MAGIC",
    "RUN_HEADER",
    "SCHEMA",
    "read_manifest",
    "restore_device_state",
    "save_device_state",
]
