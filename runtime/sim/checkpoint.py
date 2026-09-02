"""Serialise and restore the mutable state of an ABI 3.0 functional device.

A deployment is split, by construction, into bytes that are *derived* and bytes
that are *accumulated*.  Weights arrive as authenticated segments of the locked
checkpoint and are mapped read-only; derived constants -- rotary tables, window
index tables -- are re-materialised from a named generator and re-checked
against the digest the deployment binds.  Neither can differ between two
processes that read the same deployment, so neither belongs in a checkpoint.

What is left is the private byte buffer of every writable object: the KV state
images, the activation scratch, the token ring and the input window.  A cluster
owns one private copy per logical node, so the checkpoint names both node and
object and carries every arena.  That set, the aggregate and per-node counters,
plus the host-visible session bookkeeping (position, generation, cursor rows,
the produced tokens), is the entire mutable state of the device.  This module
writes exactly that set and restores exactly that set, so a process that loads a
checkpoint is in the state the writing process was in when it stopped -- not
approximately, and not "in the parts we thought mattered".

Three properties make the claim checkable rather than asserted:

*Completeness is proved, not assumed.*  :func:`save_device_state` refuses to
write a checkpoint if any writable object on any node is not one it serialises,
and :func:`restore_device_state` independently reconstructs that expected set
from the deployment before touching an object.  A future backend that makes a
mapped object writable, or a manifest with one node/object entry removed,
therefore fails loudly instead of silently producing a partial restart.

*The payload is compacted losslessly.*  A Qwen deployment's mutable image is
3.3 GB, almost all of it still at its fill byte; DeepSeek's 32 node deployment
has several logical terabytes of calloc-backed arena while a short request
touches only a small fraction.  Small objects are scanned completely.  Large
objects use byte intervals recorded at every architectural write boundary, and
the interval is conservative for strided views, so it can retain extra fill but
cannot omit a device write.  The manifest binds a canonical sparse digest over
the size, fill, run coordinates and run payloads.  Those fields uniquely
reconstruct every logical byte without hashing terabytes of untouched fill.

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
import os
import struct
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from runtime.abi3.capability import canonical_json
from runtime.sim.device import Device, Session, StateResource
from runtime.sim.counters import CounterSet

SCHEMA = "opentallas.abi3.device_checkpoint.v2"
LEGACY_SCHEMA = "opentallas.abi3.device_checkpoint.v1"

#: Granularity of the fill-run scan.  Small enough that a KV window written for
#: a hundred positions does not drag its whole 33 MB plane into the payload,
#: large enough that the manifest stays short.
BLOCK_BYTES = 1 << 16

# Below this size, a complete scan also detects callers that deliberately
# mutate ``anonymous_buffer()`` outside the architectural memory API (useful in
# focused tests).  Larger objects rely on MemoryObject's complete write ledger;
# linearly touching a 34 GiB zero arena merely to rediscover that it is a hole
# defeats the sparse allocation that makes the simulator runnable.
FULL_SCAN_MAX_BYTES = 1 << 26

IO_CHUNK_BYTES = 1 << 24
SPARSE_DIGEST_MODE = "sha256_sparse_runs_v1"
LEGACY_DIGEST_MODE = "sha256_full_contents_v1"
SPARSE_DIGEST_PREFIX = b"OpenTallas ABI3 sparse checkpoint object v1\0"

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
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)

    serialised: set[tuple[int, int]] = set()
    objects: list[dict[str, Any]] = []
    payloads: dict[tuple[Any, ...], Path] = {}
    for node_id, memory in enumerate(device.node_memories):
        for object_id in sorted(memory.objects):
            obj = memory.objects[object_id]
            if not obj.writable:
                continue
            source = device.deployment.objects.get(object_id)
            if source is None:
                raise CheckpointError(
                    f"node {node_id} object {object_id} has no declared source"
                )
            if source.kind != "zero":
                raise CheckpointError(
                    f"node {node_id} object {object_id} is writable but its "
                    f"source kind is {source.kind!r}; a checkpoint cannot "
                    "reconstruct a private mapped or generated object"
                )
            buffer = obj.anonymous_buffer()
            if buffer is None:  # pragma: no cover -- a zero object owns a buffer
                raise CheckpointError(
                    f"node {node_id} object {object_id} declares a zero source "
                    "but owns no buffer"
                )
            relative = (
                Path("objects") / f"{object_id:05d}.bin"
                if device.node_count == 1
                else Path("nodes")
                / f"{node_id:05d}"
                / "objects"
                / f"{object_id:05d}.bin"
            )
            entry = _write_object(
                path,
                relative,
                node_id,
                object_id,
                obj,
                buffer,
                int(source.fill),
            )
            _deduplicate_payload(path, entry, payloads)
            objects.append(entry)
            serialised.add((node_id, object_id))

    missing = sorted(
        (node_id, object_id)
        for node_id, memory in enumerate(device.node_memories)
        for object_id, obj in memory.objects.items()
        if obj.writable and (node_id, object_id) not in serialised
    )
    if missing:
        raise CheckpointError(
            f"node/object pairs {missing} are writable but are not serialised; a "
            "checkpoint that omits writable state is not a checkpoint"
        )

    physical_payload_bytes = 0
    payload_inodes: set[tuple[int, int]] = set()
    for entry in objects:
        stat = (path / entry["file"]).stat()
        inode = (int(stat.st_dev), int(stat.st_ino))
        if inode not in payload_inodes:
            payload_inodes.add(inode)
            physical_payload_bytes += int(stat.st_size)

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
            "node_count": device.node_count,
            "next_session": device._next_session,
            "device_cycle": device._device_cycle,
            "counters": device.counters.to_dict(),
            "node_counters": [counter.to_dict() for counter in device.node_counters],
        },
        "session": _session_to_dict(session),
        "objects": objects,
        "reconstructed_objects": [
            {"object_id": object_id, "source_kind": source.kind}
            for object_id, source in sorted(device.deployment.objects.items())
            if not device.memory.objects[object_id].writable
        ],
        "block_bytes": BLOCK_BYTES,
        "encoding": {
            "digest_mode": SPARSE_DIGEST_MODE,
            "full_scan_max_bytes": FULL_SCAN_MAX_BYTES,
            "logical_stored_bytes": sum(
                int(entry["stored_bytes"]) for entry in objects
            ),
            "physical_payload_bytes": physical_payload_bytes,
            "unique_payload_files": len(payload_inodes),
            "deduplicated_payload_files": len(objects) - len(payload_inodes),
        },
        "host_state": dict(host_state or {}),
    }
    (path / "checkpoint.json").write_bytes(canonical_json(body))
    return body


def _write_object(
    path: Path,
    relative: Path,
    node_id: int,
    object_id: int,
    obj: Any,
    buffer: np.ndarray,
    fill: int,
) -> dict[str, Any]:
    """Store a lossless sparse image and its canonical representation digest."""

    capture_mode = (
        "full_scan" if int(buffer.size) <= FULL_SCAN_MAX_BYTES else "tracked_writes"
    )
    runs = (
        _fill_runs(buffer, fill)
        if capture_mode == "full_scan"
        else _fill_runs(buffer, fill, obj.dirty_ranges())
    )
    blob = path / relative
    blob.parent.mkdir(parents=True, exist_ok=True)
    digest = _sparse_digest(int(buffer.size), fill, len(runs))
    stored = 0
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=blob.parent,
            prefix=f".{blob.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(FILE_MAGIC)
            handle.write(RUN_HEADER.pack(int(buffer.size), len(runs)))
            for start, stop in runs:
                header = RUN_HEADER.pack(start, stop - start)
                handle.write(header)
                digest.update(header)
                for begin in range(start, stop, IO_CHUNK_BYTES):
                    end = min(begin + IO_CHUNK_BYTES, stop)
                    payload = buffer[begin:end].tobytes()
                    handle.write(payload)
                    digest.update(payload)
                stored += stop - start
        # A previous checkpoint may have hard-linked this path to another
        # payload.  Replacing the directory entry, rather than truncating that
        # shared inode in place, keeps every sibling image intact until this
        # run's own authenticated deduplication decides they are identical.
        os.replace(temporary, blob)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {
        "node_id": node_id,
        "object_id": object_id,
        "size_bytes": int(buffer.size),
        "storage_class": obj.storage_class.name,
        "writable": bool(obj.writable),
        "fill": fill,
        "run_count": len(runs),
        "stored_bytes": stored,
        "capture_mode": capture_mode,
        "digest_mode": SPARSE_DIGEST_MODE,
        "sha256": digest.hexdigest(),
        "file": relative.as_posix(),
    }


def _deduplicate_payload(
    path: Path,
    entry: dict[str, Any],
    payloads: dict[tuple[Any, ...], Path],
) -> None:
    """Hard-link byte-identical node payloads after authenticating their image."""

    key = (
        entry["digest_mode"],
        entry["sha256"],
        int(entry["size_bytes"]),
        int(entry["fill"]),
        int(entry["run_count"]),
        int(entry["stored_bytes"]),
    )
    relative = Path(entry["file"])
    existing = payloads.get(key)
    if existing is None:
        payloads[key] = relative
        return
    blob = path / relative
    blob.unlink()
    try:
        os.link(path / existing, blob)
    except OSError:
        # Cross-device or link-policy failures do not weaken correctness; they
        # only forgo a disk optimisation.  Recreate the file from its already
        # authenticated peer without holding the payload in memory.
        import shutil

        shutil.copyfile(path / existing, blob)
        return
    entry["payload_hardlink_of"] = existing.as_posix()


def _fill_runs(
    buffer: np.ndarray,
    fill: int,
    candidates: Sequence[tuple[int, int]] | None = None,
) -> list[tuple[int, int]]:
    """Non-fill blocks in the whole object or only tracked candidate ranges."""

    size = int(buffer.size)
    runs: list[tuple[int, int]] = []
    regions = [(0, size)] if candidates is None else _snap_ranges(candidates, size)
    for region_start, region_stop in regions:
        start: int | None = None
        for begin in range(region_start, region_stop, BLOCK_BYTES):
            end = min(begin + BLOCK_BYTES, region_stop)
            if bool(np.any(buffer[begin:end] != fill)):
                if start is None:
                    start = begin
            elif start is not None:
                runs.append((start, begin))
                start = None
        if start is not None:
            runs.append((start, region_stop))
    return runs


def _snap_ranges(ranges: Sequence[tuple[int, int]], size: int) -> list[tuple[int, int]]:
    """Snap tracked writes to the payload block grid and coalesce neighbours."""

    snapped: list[tuple[int, int]] = []
    for raw_start, raw_stop in ranges:
        start = max((int(raw_start) // BLOCK_BYTES) * BLOCK_BYTES, 0)
        stop = min(
            ((int(raw_stop) + BLOCK_BYTES - 1) // BLOCK_BYTES) * BLOCK_BYTES,
            int(size),
        )
        if stop <= start:
            continue
        if snapped and start <= snapped[-1][1]:
            snapped[-1] = (snapped[-1][0], max(snapped[-1][1], stop))
        else:
            snapped.append((start, stop))
    return snapped


def _sparse_digest(size: int, fill: int, run_count: int) -> Any:
    digest = hashlib.sha256()
    digest.update(SPARSE_DIGEST_PREFIX)
    digest.update(RUN_HEADER.pack(int(size), int(run_count)))
    digest.update(bytes([int(fill)]))
    return digest


def sparse_object_digest(
    size: int, fill: int, runs: Sequence[tuple[int, bytes]] = ()
) -> str:
    """Digest one canonical sparse object; exposed for checkpoint controls."""

    digest = _sparse_digest(size, fill, len(runs))
    for start, payload in runs:
        header = RUN_HEADER.pack(int(start), len(payload))
        digest.update(header)
        digest.update(payload)
    return digest.hexdigest()


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
                "commit_policy": state.commit_policy,
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


def restore_device_state(device: Device, path: Path) -> tuple[Session, dict[str, Any]]:
    """Put ``device`` into the state the checkpoint under ``path`` records.

    Returns the restored session and the checkpoint manifest.  Every restored
    object's canonical sparse SHA-256 is re-checked against the manifest, so a
    silent partial restore is not possible without linearly reading untouched
    fill regions.
    """
    path = Path(path)
    body = read_manifest(path)
    schema = body.get("schema")
    if schema not in {SCHEMA, LEGACY_SCHEMA}:
        raise CheckpointError(
            f"checkpoint schema {schema!r} is neither {SCHEMA} nor {LEGACY_SCHEMA}"
        )

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

    declared_nodes = int(body.get("device", {}).get("node_count", 1))
    if declared_nodes != device.node_count:
        raise CheckpointError(
            f"checkpoint carries {declared_nodes} node arenas, this device "
            f"declares {device.node_count}"
        )
    _validate_object_manifest(device, path, body["objects"])
    for entry in body["objects"]:
        _restore_object(device, path, entry)

    device._next_session = int(body["device"]["next_session"])
    device._device_cycle = int(body["device"]["device_cycle"])
    _restore_counter_set(device.counters, body["device"]["counters"])
    node_counter_states = body["device"].get("node_counters")
    if node_counter_states is None:
        # Additive compatibility with the original single-node manifest.  It
        # did not retain the per-node split, so there is nothing truthful to
        # reconstruct there.  A multi-node manifest is never accepted without
        # all node counter sets.
        if device.node_count != 1:
            raise CheckpointError(
                "a multi-node checkpoint carries no per-node counter state"
            )
        device.node_counters[0].reset()
    else:
        if len(node_counter_states) != device.node_count:
            raise CheckpointError(
                f"checkpoint carries {len(node_counter_states)} per-node counter "
                f"sets for {device.node_count} nodes"
            )
        for counter, state in zip(device.node_counters, node_counter_states):
            _restore_counter_set(counter, state)

    session = _session_from_dict(device, body["session"])
    device.sessions = {session.session_id: session}
    return session, body


def _validate_object_manifest(
    device: Device, path: Path, entries: list[Mapping[str, Any]]
) -> None:
    """Prove the manifest names every mutable node/object exactly once.

    Save-side completeness is not enough: removing a complete entry from a JSON
    manifest used to make restore silently leave that object at its fresh fill
    value.  Reconstructing the expected set from the admitted deployment makes
    omission, duplication, a wrong node, and a storage/fill substitution all
    fail before any destination buffer is touched.
    """

    expected = {
        (node_id, object_id)
        for node_id, memory in enumerate(device.node_memories)
        for object_id, obj in memory.objects.items()
        if obj.writable
    }
    found: set[tuple[int, int]] = set()
    for index, entry in enumerate(entries):
        node_id = int(entry.get("node_id", 0))
        object_id = int(entry["object_id"])
        key = (node_id, object_id)
        if key in found:
            raise CheckpointError(
                f"checkpoint repeats node/object pair {key} at entry {index}"
            )
        found.add(key)
        if not 0 <= node_id < device.node_count:
            raise CheckpointError(
                f"checkpoint object {object_id} names node {node_id}, but the "
                f"device has nodes 0..{device.node_count - 1}"
            )
        obj = device.node_memories[node_id].objects.get(object_id)
        if obj is None:
            raise CheckpointError(
                f"checkpoint names node {node_id} object {object_id}, which "
                "does not exist"
            )
        source = device.deployment.objects.get(object_id)
        if not obj.writable or source is None or source.kind != "zero":
            raise CheckpointError(
                f"checkpoint names node {node_id} object {object_id}, which is "
                "not a writable zero-source object"
            )
        if entry.get("storage_class") != obj.storage_class.name:
            raise CheckpointError(
                f"node {node_id} object {object_id}: checkpoint storage class "
                f"{entry.get('storage_class')!r} does not match "
                f"{obj.storage_class.name!r}"
            )
        if int(entry.get("fill", -1)) != int(source.fill):
            raise CheckpointError(
                f"node {node_id} object {object_id}: checkpoint fill "
                f"{entry.get('fill')!r} does not match {source.fill}"
            )
        digest_mode = entry.get("digest_mode", LEGACY_DIGEST_MODE)
        if digest_mode not in {SPARSE_DIGEST_MODE, LEGACY_DIGEST_MODE}:
            raise CheckpointError(
                f"node {node_id} object {object_id}: unknown checkpoint digest "
                f"mode {digest_mode!r}"
            )
        if capture_mode := entry.get("capture_mode"):
            if capture_mode not in {"full_scan", "tracked_writes"}:
                raise CheckpointError(
                    f"node {node_id} object {object_id}: unknown capture mode "
                    f"{capture_mode!r}"
                )
        relative = Path(str(entry.get("file", "")))
        if (
            not relative.parts
            or relative.is_absolute()
            or ".." in relative.parts
            or relative.as_posix() != str(entry.get("file", ""))
        ):
            raise CheckpointError(
                f"node {node_id} object {object_id} has unsafe payload path "
                f"{entry.get('file')!r}"
            )
        if not (path / relative).is_file():
            raise CheckpointError(
                f"node {node_id} object {object_id} payload is missing: {relative}"
            )

    missing = sorted(expected - found)
    unexpected = sorted(found - expected)
    if missing or unexpected:
        raise CheckpointError(
            "checkpoint mutable-object coverage differs from the deployment: "
            f"missing={missing}, unexpected={unexpected}"
        )


def _restore_counter_set(counter: CounterSet, state: Mapping[str, Any]) -> None:
    """Restore values and sticky-overflow state, accepting the original shape."""

    if "counters" in state:
        values = state["counters"]
        overflow = state.get("sticky_overflow", [])
    else:
        # The first checkpoint format stored only the value mapping.  It is
        # still readable for the retained single-node artifact, but new writes
        # retain the sticky architectural state as well.
        values = state
        overflow = []
    counter.reset()
    for name, value in values.items():
        counter.add(str(name), int(value))
    unknown = sorted(set(str(name) for name in overflow) - set(values))
    if unknown:
        raise CheckpointError(
            f"sticky-overflow counters have no stored value: {unknown}"
        )
    counter._overflow.update(str(name) for name in overflow)


def _restore_object(device: Device, path: Path, entry: Mapping[str, Any]) -> None:
    node_id = int(entry.get("node_id", 0))
    object_id = int(entry["object_id"])
    obj = device.node_memories[node_id].objects.get(object_id)
    if obj is None:
        raise CheckpointError(
            f"checkpoint names node {node_id} object {object_id}, which does not exist"
        )
    buffer = obj.anonymous_buffer()
    if buffer is None:
        raise CheckpointError(
            f"node {node_id} object {object_id} is mapped in this device but was a private "
            "buffer when the checkpoint was written"
        )
    if int(buffer.size) != int(entry["size_bytes"]):
        raise CheckpointError(
            f"node {node_id} object {object_id} is {buffer.size} bytes here and "
            f"{entry['size_bytes']} bytes in the checkpoint"
        )
    blob = path / entry["file"]
    digest_mode = str(entry.get("digest_mode", LEGACY_DIGEST_MODE))
    with blob.open("rb") as handle:
        if handle.read(len(FILE_MAGIC)) != FILE_MAGIC:
            raise CheckpointError(f"{blob} is not a checkpoint object payload")
        header = handle.read(RUN_HEADER.size)
        if len(header) != RUN_HEADER.size:
            raise CheckpointError(f"{blob} is truncated before its object header")
        size, run_count = RUN_HEADER.unpack(header)
        if size != int(entry["size_bytes"]):
            raise CheckpointError(
                f"{blob} declares {size} bytes, manifest says {entry['size_bytes']}"
            )
        if run_count != int(entry.get("run_count", run_count)):
            raise CheckpointError(
                f"{blob} carries {run_count} runs, manifest says "
                f"{entry.get('run_count')}"
            )
        # Start from the declared fill so that a byte the writing process left
        # at its fill value is restored as that value even if this process's
        # buffer has been touched.  A large fresh arena is already all fill;
        # resetting only its own tracked writes preserves the sparse virtual
        # allocation instead of committing several logical terabytes merely to
        # write zero over zero.
        fill = int(entry["fill"])
        if int(buffer.size) <= FULL_SCAN_MAX_BYTES or digest_mode == LEGACY_DIGEST_MODE:
            buffer[:] = np.uint8(fill)
        else:
            for start, stop in obj.dirty_ranges():
                buffer[start:stop] = np.uint8(fill)
        obj.clear_dirty_ranges()

        sparse_digest = (
            _sparse_digest(int(size), fill, int(run_count))
            if digest_mode == SPARSE_DIGEST_MODE
            else None
        )
        last_stop = 0
        restored_bytes = 0
        for _ in range(run_count):
            run_header = handle.read(RUN_HEADER.size)
            if len(run_header) != RUN_HEADER.size:
                raise CheckpointError(f"{blob} is truncated before a run header")
            start, length = RUN_HEADER.unpack(run_header)
            stop = start + length
            if length <= 0 or start < last_stop or stop > size:
                raise CheckpointError(
                    f"{blob} has invalid or overlapping run [{start}, {stop}) "
                    f"after byte {last_stop} of a {size}-byte object"
                )
            if sparse_digest is not None:
                sparse_digest.update(run_header)
            cursor = start
            while cursor < stop:
                take = min(IO_CHUNK_BYTES, stop - cursor)
                payload = handle.read(take)
                if len(payload) != take:
                    raise CheckpointError(
                        f"{blob} is truncated inside a run at {cursor}"
                    )
                if sparse_digest is not None:
                    sparse_digest.update(payload)
                obj.write(cursor, payload)
                cursor += take
            restored_bytes += length
            last_stop = stop
        if handle.read(1):
            raise CheckpointError(f"{blob} has trailing bytes after its last run")
    if restored_bytes != int(entry.get("stored_bytes", restored_bytes)):
        raise CheckpointError(
            f"{blob} restores {restored_bytes} payload bytes, manifest says "
            f"{entry.get('stored_bytes')}"
        )

    if sparse_digest is not None:
        actual_digest = sparse_digest.hexdigest()
    else:
        legacy_digest = hashlib.sha256()
        for begin in range(0, int(buffer.size), IO_CHUNK_BYTES):
            legacy_digest.update(buffer[begin : begin + IO_CHUNK_BYTES].tobytes())
        actual_digest = legacy_digest.hexdigest()
    if actual_digest != entry["sha256"]:
        raise CheckpointError(
            f"node {node_id} object {object_id} restored to digest "
            f"{actual_digest[:16]}, the "
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
            # Amendment A21: the commit policy is a deployment declaration, so
            # a checkpoint may carry it but may not disagree with it.
            "commit_policy",
        ):
            if field not in state:
                continue
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
            commit_policy=int(state.get("commit_policy", fresh.commit_policy)),
            cursor_rows=int(state["cursor_rows"]),
            generation=int(state["generation"]),
            open_prepare=bool(state["open_prepare"]),
        )
    return session


__all__ = [
    "BLOCK_BYTES",
    "CheckpointError",
    "FILE_MAGIC",
    "LEGACY_DIGEST_MODE",
    "LEGACY_SCHEMA",
    "RUN_HEADER",
    "SCHEMA",
    "SPARSE_DIGEST_MODE",
    "read_manifest",
    "restore_device_state",
    "save_device_state",
    "sparse_object_digest",
]
