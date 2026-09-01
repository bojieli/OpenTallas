#!/usr/bin/env python3
"""Checkpoint/restart exactness for an ABI 3.0 deployment (W6.6).

The claim this tool exists to prove is narrow and it is the only one worth
making:

    stop a generation after N decode steps, serialise the device state, load it
    in a **fresh process**, finish the decode, and the full token sequence is
    identical to an uninterrupted run of the same workload on the same backend.

Three properties of the method matter.

*Separate processes.*  Each of the three runs -- uninterrupted, interrupted,
resumed -- is its own operating-system process, launched by this script.  An
in-process "restart" can pass by accident: the KV images, the memory-mapped
weights and the session objects were never torn down, so a restart that
restored nothing would still continue correctly.  Only a new process proves the
checkpoint carries the state.

*The device sees the same request either way.*  The interrupted run stops after
``--stop-after`` tokens without lowering the declared bound: ``MAX_NEW_TOKENS``
stays the workload's limit in every transaction, so the transactions the
interrupted run issues are the transactions the uninterrupted run issued.  A
stop that changed the request would compare two different computations.

*No equality claim is made about an empty or short sequence.*  Every comparison
here is guarded by an explicit length and non-emptiness check, and the guards
are reported.  Two empty token lists are not a match, and this tool refuses to
call them one.

Usage::

    CK=$(ls -d ~/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/*/ | head -1)
    PYTHONPATH=. OPENTALLAS_ABI3_BACKEND=torch_cpu python3 \\
      tools/run_abi3_restart_exactness.py \\
      --kernel-ir build/ir-v3/qwen3-8b/kernel_ir.v3.json --backend hbm_sram \\
      --capability configs/hardware/abi3_capability/hbm_sram_single_chip.json \\
      --workload build/workloads/qwen3-8b/TA-QW-CHAT-1.json --deployment-root "$CK" \\
      --max-new-tokens 6 --stop-after 3 \\
      --output results/abi3/restart_exactness.json --force

The deployment is lowered independently in each phase from the neutral IR and
is never written into ``--deployment-root``: the root supplies the
authenticated weight files only, so a campaign running concurrently against the
same checkpoint is untouched.  Each phase asserts it lowered the same
deployment digest, so the three runs are provably the same program.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

# The blocked GEMM association is part of the execution identity.  Match the
# governed DeepSeek token path unless the caller has deliberately fixed another
# value before launching the campaign; every phase records the resulting flags.
for _thread_variable in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
):
    os.environ.setdefault(_thread_variable, "8")

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.capability import Capability, canonical_json, digest_of  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver, validate_token_ids  # noqa: E402
from runtime.evidence import (  # noqa: E402
    EvidenceClass,
    ExecutionRecord,
    TargetIdentity,
    WorkloadIdentity,
    check_token_legitimacy,
)
from runtime.sim.checkpoint import (  # noqa: E402
    FILE_MAGIC,
    LEGACY_DIGEST_MODE,
    RUN_HEADER,
    SPARSE_DIGEST_MODE,
    read_manifest,
    restore_device_state,
    save_device_state,
    sparse_object_digest,
)
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

SCHEMA = "opentallas.abi3.restart_exactness.v2"

#: Backend name -> "module:function" producing a Deployment.  Same table as the
#: campaign: a target is a set of descriptors, not a code path.
BACKENDS = {
    "hbm_sram": "compiler.backends.hbm_sram.lower:lower_to_abi3",
    "rom_qwen3": "compiler.backends.rom.qwen3:lower_to_abi3",
    "rom_deepseek_v4": "compiler.backends.rom.deepseek_v4:lower_to_abi3",
}

PHASES = ("baseline", "interrupt", "resume")


class ExactnessError(Exception):
    """Raised when the experiment cannot be run, or cannot be believed."""


# ---------------------------------------------------------------------------
# Shared setup, performed identically by every phase
# ---------------------------------------------------------------------------
def _resolve(spec: str):
    module_name, _, attribute = spec.partition(":")
    return getattr(importlib.import_module(module_name), attribute)


def _build_device(args: argparse.Namespace) -> tuple[Device, Any, Any, dict[str, Any]]:
    """Lower the IR, admit it and bring up a device on the authenticated root."""
    from compiler.ir.v3.kernel_ir import KernelGraph

    coverage = load_engines()
    capability = Capability.from_dict(json.loads(args.capability.read_text()))
    graph = KernelGraph.read(args.kernel_ir)
    lower = _resolve(BACKENDS[args.backend])
    kwargs: dict[str, Any] = {}
    if args.topology:
        kwargs["topology"] = args.topology
    deployment = lower(graph, capability, **kwargs)
    deployment.root = args.deployment_root
    report = verify_deployment(deployment, capability)
    if not report.admitted:
        raise ExactnessError(
            "the deployment was not admitted: "
            + (report.errors[0] if report.errors else "no reason given")
        )
    device = Device(deployment, capability, root=args.deployment_root, verify=False)
    body = graph.to_dict()
    return device, capability, graph, {
        "verification": report.to_dict(),
        "engine_coverage": {
            "implemented_count": coverage["implemented_count"],
            "missing_count": coverage["missing_count"],
        },
        "graph_id": graph.graph_id,
        "numeric_profile": body.get("numeric_profile", ""),
        "model_id": body.get("model_id", ""),
    }


def _source_identity() -> dict[str, Any]:
    """A digest over the Python that will execute, so drift is not silent.

    Three processes minutes apart are three chances for the runtime to change
    underneath the experiment -- this repository is worked on concurrently, and
    a device or memory module edited between the interrupted run and the
    resumed one would make the comparison meaningless without changing the
    backend identity.  Each phase records this digest and the comparison
    refuses to conclude anything if the three disagree.
    """
    files = sorted(
        {
            path
            for root in ("runtime", "compiler")
            for path in (REPO / root).rglob("*.py")
            if "__pycache__" not in path.parts
        }
        | {Path(__file__).resolve()}
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(str(path.relative_to(REPO)).encode())
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {
        "python_source_digest": digest.hexdigest(),
        "python_file_count": len(files),
    }


def _implementation_identity() -> dict[str, Any]:
    from runtime.sim.backend import get_backend

    return dict(get_backend().implementation_identity())


def _phase_envelope(
    phase: str, device: Device, extra: dict[str, Any]
) -> dict[str, Any]:
    return {
        "phase": phase,
        "pid": os.getpid(),
        "backend_environment": os.environ.get("OPENTALLAS_ABI3_BACKEND", ""),
        "deployment_digest": device.deployment.deployment_digest.hex(),
        "capability_digest": device.capability.digest,
        "target_id": device.deployment.target_id,
        "deployment_backend": device.deployment.backend,
        "topology_class": int(device.deployment.topology_class),
        "node_count": device.node_count,
        "technology_view": device.capability.technology_view,
        "implementation_identity": _implementation_identity(),
        "source_identity": _source_identity(),
        "node_counters": [counter.to_dict() for counter in device.node_counters],
        **extra,
    }


def _driver_identity(driver: GenerationDriver) -> dict[str, Any]:
    return {
        "generation_policy_digest": digest_of(driver.policy),
        "generation_policy": dict(driver.policy),
        "vocabulary_size": driver.vocabulary_size,
        "eos_token_ids": list(driver.eos_token_ids),
    }


def _tokenizer_digest(path: Path, workload: Mapping[str, Any]) -> str:
    """The tokenizer SHA-256 this workload was rendered with.

    It is a shared-identity field, so a record that leaves it empty cannot be
    compared with one that fills it.  Per-workload files carry it only
    sometimes; the workload index beside them always does, and it is accepted
    only when the index names *this* workload with the digest about to run.
    """
    direct = str(workload.get("metadata", {}).get("tokenizer_sha256", ""))
    if direct:
        return direct
    index = path.parent / "index.json"
    if not index.exists():
        return ""
    body = json.loads(index.read_text())
    entry = body.get("workloads", {}).get(workload["workload_id"])
    if entry and entry.get("digest") == workload["digest"]:
        return str(body.get("tokenizer_sha256", ""))
    return ""


def _write(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(body))


def _progress(label: str):
    def report(done: int, limit: int) -> None:
        print(f"  {label}: {done}/{limit} tokens", flush=True)

    return report


# ---------------------------------------------------------------------------
# Phase 1: the uninterrupted comparator
# ---------------------------------------------------------------------------
def run_baseline(args: argparse.Namespace) -> int:
    device, _capability, _graph, extra = _build_device(args)
    workload = json.loads(args.workload.read_text())
    driver = GenerationDriver(device)
    prompt = [int(t) for t in workload["token_ids"]]
    limit = args.max_new_tokens or workload["max_new_tokens"]
    print(
        f"baseline: {len(prompt)} prompt tokens, max_new={limit}, "
        f"pid={os.getpid()}",
        flush=True,
    )
    started = time.perf_counter()
    result = driver.generate(prompt, max_new_tokens=limit, progress=_progress("baseline"))
    print(
        f"baseline produced {len(result.generated_token_ids)} tokens in "
        f"{time.perf_counter() - started:.1f}s, stop={result.stop_reason}",
        flush=True,
    )
    _write(
        args.phase_output,
        _phase_envelope(
            "baseline",
            device,
            {
                "declared_max_new_tokens": limit,
                "result": result.to_dict(),
                **_driver_identity(driver),
                **extra,
            },
        ),
    )
    return 0 if result.failure is None else 4


# ---------------------------------------------------------------------------
# Phase 2: run part of the generation, then serialise the device
# ---------------------------------------------------------------------------
def run_interrupt(args: argparse.Namespace) -> int:
    device, _capability, _graph, extra = _build_device(args)
    workload = json.loads(args.workload.read_text())
    driver = GenerationDriver(device)
    prompt = [int(t) for t in workload["token_ids"]]
    limit = args.max_new_tokens or workload["max_new_tokens"]
    print(
        f"interrupt: {len(prompt)} prompt tokens, declared max_new={limit}, "
        f"stopping after {args.stop_after} tokens, pid={os.getpid()}",
        flush=True,
    )
    session = device.create_session()
    result = driver.generate(
        prompt,
        max_new_tokens=limit,
        session=session,
        stop_after_tokens=args.stop_after,
        progress=_progress("interrupt"),
    )
    if result.failure is not None:
        _write(
            args.phase_output,
            _phase_envelope(
                "interrupt",
                device,
                {"result": result.to_dict(), **_driver_identity(driver), **extra},
            ),
        )
        print(f"  FAILURE {result.failure}", file=sys.stderr)
        return 4

    position = len(prompt) + result.decode_steps
    if position != session.position:
        raise ExactnessError(
            f"driver position {position} disagrees with the session's "
            f"{session.position}; the checkpoint would restart at the wrong place"
        )
    open_prepares = sorted(
        state.descriptor_id
        for state in session.states.values()
        if state.open_prepare
    )
    if open_prepares:
        raise ExactnessError(
            f"state resources {open_prepares} are still prepared; a checkpoint "
            "taken inside a transaction is not a transaction boundary"
        )

    started = time.perf_counter()
    manifest = save_device_state(
        device,
        session,
        args.checkpoint,
        host_state={
            "prompt_token_ids": prompt,
            "generated_token_ids": list(result.generated_token_ids),
            "position": position,
            "transaction_counter": driver.transaction_count,
            "declared_max_new_tokens": limit,
            "decode_steps": result.decode_steps,
            "workload_id": workload["workload_id"],
            "workload_digest": workload["digest"],
        },
    )
    seconds = time.perf_counter() - started
    stored = sum(int(o["stored_bytes"]) for o in manifest["objects"])
    total = sum(int(o["size_bytes"]) for o in manifest["objects"])
    physical = int(manifest.get("encoding", {}).get("physical_payload_bytes", stored))
    print(
        f"interrupt produced {len(result.generated_token_ids)} tokens, "
        f"stop={result.stop_reason}; checkpointed {len(manifest['objects'])} "
        f"mutable objects ({stored / 1e6:.1f} MB logical, "
        f"{physical / 1e6:.1f} MB physical payload of {total / 1e6:.1f} MB) "
        f"in {seconds:.1f}s",
        flush=True,
    )
    _write(
        args.phase_output,
        _phase_envelope(
            "interrupt",
            device,
            {
                "declared_max_new_tokens": limit,
                "stop_after_tokens": args.stop_after,
                "result": result.to_dict(),
                "checkpoint": {
                    "path": str(args.checkpoint),
                    "seconds": round(seconds, 3),
                    "node_count": int(manifest["device"].get("node_count", 1)),
                    "object_count": len(manifest["objects"]),
                    "mutable_bytes": total,
                    "stored_bytes": stored,
                    "physical_payload_bytes": physical,
                    "encoding": manifest.get("encoding", {}),
                    "session": manifest["session"],
                    "objects": manifest["objects"],
                },
                **_driver_identity(driver),
                **extra,
            },
        ),
    )
    return 0


# ---------------------------------------------------------------------------
# Phase 3: a fresh process loads the checkpoint and finishes the decode
# ---------------------------------------------------------------------------
def run_resume(args: argparse.Namespace) -> int:
    device, _capability, _graph, extra = _build_device(args)
    workload = json.loads(args.workload.read_text())
    started = time.perf_counter()
    session, manifest = restore_device_state(device, args.checkpoint)
    restore_seconds = time.perf_counter() - started
    host = manifest["host_state"]
    if host["workload_digest"] != workload["digest"]:
        raise ExactnessError(
            "the checkpoint was taken on a different workload than the one "
            "this process was asked to finish"
        )
    prompt = [int(t) for t in host["prompt_token_ids"]]
    already = [int(t) for t in host["generated_token_ids"]]
    limit = args.max_new_tokens or workload["max_new_tokens"]
    if int(host["declared_max_new_tokens"]) != limit:
        raise ExactnessError(
            f"the checkpoint declared max_new_tokens={host['declared_max_new_tokens']} "
            f"and this process was given {limit}; the resumed transactions would "
            "not be the transactions the uninterrupted run issued"
        )
    print(
        f"resume: restored {len(manifest['objects'])} objects in "
        f"{restore_seconds:.1f}s; continuing from {len(already)} tokens at "
        f"position {host['position']}, pid={os.getpid()}",
        flush=True,
    )
    driver = GenerationDriver(device)
    result = driver.resume(
        prompt,
        already,
        session=session,
        position=int(host["position"]),
        max_new_tokens=limit,
        transaction_offset=int(host["transaction_counter"]),
        progress=_progress("resume"),
    )
    print(
        f"resume produced {len(result.generated_token_ids)} tokens total "
        f"({result.decode_steps} decode steps in this process), "
        f"stop={result.stop_reason}",
        flush=True,
    )
    _write(
        args.phase_output,
        _phase_envelope(
            "resume",
            device,
            {
                "declared_max_new_tokens": limit,
                "restore_seconds": round(restore_seconds, 3),
                "restored_from": str(args.checkpoint),
                "restored_token_count": len(already),
                "restored_position": int(host["position"]),
                "restored_session": manifest["session"],
                "result": result.to_dict(),
                **_driver_identity(driver),
                **extra,
            },
        ),
    )
    return 0 if result.failure is None else 4


# ---------------------------------------------------------------------------
# Orchestration and the comparison itself
# ---------------------------------------------------------------------------
def _launch(
    phase: str,
    args: argparse.Namespace,
    output: Path,
    *,
    checkpoint: Path | None = None,
    label: str | None = None,
    allow_failure: bool = False,
) -> dict[str, Any]:
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--phase", phase,
        "--kernel-ir", str(args.kernel_ir),
        "--backend", args.backend,
        "--capability", str(args.capability),
        "--workload", str(args.workload),
        "--deployment-root", str(args.deployment_root),
        "--checkpoint", str(checkpoint or args.checkpoint),
        "--phase-output", str(output),
        "--stop-after", str(args.stop_after),
        "--output", str(args.output),
    ]
    if args.max_new_tokens is not None:
        command += ["--max-new-tokens", str(args.max_new_tokens)]
    if args.topology:
        command += ["--topology", args.topology]
    print(f"\n=== phase {label or phase}: {' '.join(command)}", flush=True)
    environment = dict(os.environ)
    environment.setdefault("PYTHONPATH", str(REPO))
    completed = subprocess.run(command, env=environment, cwd=str(REPO))
    if completed.returncode != 0 and not (allow_failure and output.exists()):
        raise ExactnessError(
            f"phase {label or phase} exited {completed.returncode}; see its "
            "output above"
        )
    if not output.exists():
        raise ExactnessError(f"phase {phase} wrote no result to {output}")
    body = json.loads(output.read_text())
    body["exit_status"] = completed.returncode
    return body


def _blind_checkpoint(
    source: Path, target: Path, classes: set[str]
) -> list[dict[str, int]]:
    """Copy a checkpoint with the named storage classes reset to their fill.

    This is the experiment's negative control.  A restart test that cannot fail
    proves nothing, so before believing a match we take the same checkpoint,
    erase exactly the images that carry the KV history, and require that the
    same resumed decode then produces a *different* sequence.  The manifest
    digests are recomputed so the blinded checkpoint is internally consistent:
    it is refused by nothing, which is the point -- what changes the answer is
    the missing state, not a detected corruption.
    """
    if target.exists():
        shutil.rmtree(target)

    # A DeepSeek cluster carries one mutable arena per node.  Copying its exact
    # checkpoint once for each control can triple the campaign's disk use even
    # though each control changes only one storage-class subset.  Link payloads
    # on the same filesystem (falling back to a normal copy), then atomically
    # replace only the blinded files; the source checkpoint's links and bytes
    # remain untouched and each target manifest is independently verified.
    def link_or_copy(src: str, dst: str) -> str:
        try:
            os.link(src, dst)
            return dst
        except OSError:
            return shutil.copy2(src, dst)

    shutil.copytree(source, target, copy_function=link_or_copy)
    body = json.loads((target / "checkpoint.json").read_text())
    blinded: list[dict[str, int]] = []
    fill_digests: dict[tuple[int, int, str], str] = {}
    for entry in body["objects"]:
        if entry["storage_class"] not in classes:
            continue
        blob = target / entry["file"]
        replacement = blob.with_name(f".{blob.name}.blinded")
        with replacement.open("wb") as handle:
            handle.write(FILE_MAGIC)
            handle.write(RUN_HEADER.pack(int(entry["size_bytes"]), 0))
        os.replace(replacement, blob)
        digest_mode = entry.get("digest_mode", LEGACY_DIGEST_MODE)
        digest_key = (
            int(entry["fill"]),
            int(entry["size_bytes"]),
            str(digest_mode),
        )
        digest_hex = fill_digests.get(digest_key)
        if digest_hex is None:
            if digest_mode == SPARSE_DIGEST_MODE:
                digest_hex = sparse_object_digest(digest_key[1], digest_key[0])
            elif digest_mode == LEGACY_DIGEST_MODE:
                digest = hashlib.sha256()
                block = bytes([digest_key[0]]) * (1 << 22)
                remaining = digest_key[1]
                while remaining > 0:
                    take = min(remaining, len(block))
                    digest.update(block[:take])
                    remaining -= take
                digest_hex = digest.hexdigest()
            else:
                raise ExactnessError(
                    f"object {entry['object_id']} uses unknown checkpoint digest "
                    f"mode {digest_mode!r}"
                )
            fill_digests[digest_key] = digest_hex
        entry["run_count"] = 0
        entry["stored_bytes"] = 0
        entry["sha256"] = digest_hex
        entry.pop("payload_hardlink_of", None)
        blinded.append(
            {
                "node_id": int(entry.get("node_id", 0)),
                "object_id": int(entry["object_id"]),
            }
        )
    if "encoding" in body:
        inodes: set[tuple[int, int]] = set()
        physical_payload_bytes = 0
        for entry in body["objects"]:
            stat = (target / entry["file"]).stat()
            inode = (int(stat.st_dev), int(stat.st_ino))
            if inode not in inodes:
                inodes.add(inode)
                physical_payload_bytes += int(stat.st_size)
        body["encoding"].update(
            {
                "logical_stored_bytes": sum(
                    int(entry["stored_bytes"]) for entry in body["objects"]
                ),
                "physical_payload_bytes": physical_payload_bytes,
                "unique_payload_files": len(inodes),
                "deduplicated_payload_files": len(body["objects"]) - len(inodes),
            }
        )
    manifest = target / "checkpoint.json"
    replacement_manifest = target / ".checkpoint.json.blinded"
    replacement_manifest.write_bytes(canonical_json(body))
    os.replace(replacement_manifest, manifest)
    return blinded


def _compare(
    baseline: Sequence[int], restarted: Sequence[int]
) -> tuple[bool, int | None]:
    """Element-wise comparison that never calls two empty lists a match."""
    if not baseline or not restarted:
        return False, 0
    if len(baseline) != len(restarted):
        limit = min(len(baseline), len(restarted))
        for index in range(limit):
            if baseline[index] != restarted[index]:
                return False, index
        return False, limit
    for index, (left, right) in enumerate(zip(baseline, restarted)):
        if left != right:
            return False, index
    return True, None


def _node_counter_differences(
    baseline: Sequence[Mapping[str, Any]],
    restarted: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Exact per-node counter-state differences, including sticky overflow."""

    if len(baseline) != len(restarted):
        return {
            "node_count": {
                "baseline": len(baseline),
                "restarted": len(restarted),
            }
        }
    differences: dict[str, Any] = {}
    for node_id, (left, right) in enumerate(zip(baseline, restarted)):
        if left == right:
            continue
        left_values = left.get("counters", left)
        right_values = right.get("counters", right)
        counter_differences = {
            name: {
                "baseline": left_values.get(name),
                "restarted": right_values.get(name),
            }
            for name in sorted(set(left_values) | set(right_values))
            if left_values.get(name) != right_values.get(name)
        }
        left_overflow = sorted(left.get("sticky_overflow", []))
        right_overflow = sorted(right.get("sticky_overflow", []))
        differences[str(node_id)] = {
            "counter_differences": counter_differences,
            "sticky_overflow": (
                None
                if left_overflow == right_overflow
                else {"baseline": left_overflow, "restarted": right_overflow}
            ),
        }
    return differences


def orchestrate(args: argparse.Namespace) -> int:
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1
    workload = json.loads(args.workload.read_text())
    limit = args.max_new_tokens or workload["max_new_tokens"]
    if args.stop_after < 1 or args.stop_after >= limit:
        print(
            f"--stop-after must be between 1 and {limit - 1} so that both the "
            "interrupted part and the resumed part do real work",
            file=sys.stderr,
        )
        return 1

    work = args.work_dir or Path(tempfile.mkdtemp(prefix="abi3-restart-"))
    work.mkdir(parents=True, exist_ok=True)
    args.checkpoint = work / "checkpoint"
    print(f"work directory: {work}", flush=True)

    started = time.perf_counter()
    phases = {
        phase: _launch(phase, args, work / f"{phase}.json") for phase in PHASES
    }

    # The negative control runs the *same* resumed decode from a checkpoint
    # whose KV state images have been reset to their fill value.  If that run
    # still reproduces the baseline, the experiment is not sensitive to the
    # state it claims to carry and no match it reports means anything.
    negative: dict[str, Any] | None = None
    if args.negative_control:
        blinded = work / "checkpoint-blinded"
        erased = _blind_checkpoint(args.checkpoint, blinded, {"STATE"})
        print(f"\nnegative control: erased state objects {erased}", flush=True)
        negative = _launch(
            "resume",
            args,
            work / "negative.json",
            checkpoint=blinded,
            label="resume (negative control: KV state erased)",
            allow_failure=True,
        )
        negative["erased_objects"] = erased

    # The complementary control asks a design question rather than a validity
    # one: is the *architectural* state -- the STATE-class resources and the
    # cursor -- on its own enough to continue?  Everything else in the
    # checkpoint is activation scratch, which a deployment would not persist.
    # This leg erases exactly that scratch and keeps the state images.  It is
    # reported, not gated: a divergence here does not invalidate the restart
    # claim above, it says that scratch outlives a transaction.
    state_only: dict[str, Any] | None = None
    if args.state_only_control:
        kept = work / "checkpoint-state-only"
        classes = {
            entry["storage_class"]
            for entry in read_manifest(args.checkpoint)["objects"]
        } - {"STATE"}
        erased_scratch = _blind_checkpoint(args.checkpoint, kept, classes)
        print(
            f"\nstate-only control: erased {sorted(classes)} objects "
            f"{erased_scratch}, kept the STATE images",
            flush=True,
        )
        state_only = _launch(
            "resume",
            args,
            work / "state_only.json",
            checkpoint=kept,
            label="resume (state-only control: scratch erased)",
            allow_failure=True,
        )
        state_only["erased_objects"] = erased_scratch
        state_only["erased_storage_classes"] = sorted(classes)
    wall = time.perf_counter() - started

    baseline = phases["baseline"]
    interrupt = phases["interrupt"]
    resume = phases["resume"]

    baseline_tokens = [int(t) for t in baseline["result"]["generated_token_ids"]]
    interrupt_tokens = [int(t) for t in interrupt["result"]["generated_token_ids"]]
    restarted_tokens = [int(t) for t in resume["result"]["generated_token_ids"]]
    tail = restarted_tokens[len(interrupt_tokens):]

    # -- guards.  Every one of these must hold before an equality claim is
    # -- allowed to mean anything.  A vacuous pass is the failure mode this
    # -- section exists to make impossible.
    pids = [phases[phase]["pid"] for phase in PHASES]
    identities = [phases[phase]["implementation_identity"] for phase in PHASES]
    digests = [phases[phase]["deployment_digest"] for phase in PHASES]
    node_counts = [int(phases[phase]["node_count"]) for phase in PHASES]
    sources = [
        phases[phase]["source_identity"]["python_source_digest"] for phase in PHASES
    ]
    expected_length = (
        len(baseline_tokens)
        if baseline["result"]["stop_reason"] == "eos"
        else limit
    )
    guards = {
        "three_distinct_processes": len(set(pids)) == 3,
        "same_deployment_digest": len(set(digests)) == 1,
        "same_node_count": len(set(node_counts)) == 1,
        "same_implementation_identity": all(
            digest_of(identity) == digest_of(identities[0]) for identity in identities
        ),
        "same_runtime_source_tree": len(set(sources)) == 1,
        "baseline_non_empty": len(baseline_tokens) > 0,
        "baseline_reached_expected_length": len(baseline_tokens) == expected_length,
        "interrupt_produced_expected_prefix_length": (
            len(interrupt_tokens) == args.stop_after
        ),
        "interrupt_prefix_matches_baseline": (
            len(interrupt_tokens) > 0
            and interrupt_tokens == baseline_tokens[: len(interrupt_tokens)]
        ),
        "baseline_longer_than_the_interrupted_prefix": (
            len(baseline_tokens) > len(interrupt_tokens)
        ),
        "resume_did_real_work": (
            int(resume["result"]["decode_steps"]) >= 1 and len(tail) >= 1
        ),
        "resume_did_not_prefill": int(resume["result"]["prefill_tokens"]) == 0,
        "restarted_non_empty": len(restarted_tokens) > 0,
        "restarted_length_matches_baseline": (
            len(restarted_tokens) == len(baseline_tokens)
        ),
        "restarted_reached_expected_length": (
            len(restarted_tokens) == expected_length
        ),
        "no_phase_failed": all(
            phases[phase]["result"]["failure"] is None for phase in PHASES
        ),
    }
    failed_guards = sorted(name for name, ok in guards.items() if not ok)

    matched, divergence = _compare(baseline_tokens, restarted_tokens)
    # The equality claim is only made when every guard holds: a match between
    # two sequences that failed a guard is not evidence of anything.
    token_identical = matched and not failed_guards

    # -- a second, independent view of the same claim: the transactions the
    # -- resumed process issued should have retired the same work as the
    # -- baseline's corresponding transactions.
    baseline_steps = baseline["result"]["per_step"]
    restarted_steps = list(interrupt["result"]["per_step"]) + list(
        resume["result"]["per_step"]
    )
    work_identical = len(baseline_steps) == len(restarted_steps) and all(
        left["retired_work"] == right["retired_work"]
        and left["produced_tokens"] == right["produced_tokens"]
        for left, right in zip(baseline_steps, restarted_steps)
    )

    # -- a third view: the device's architectural counters.  The checkpoint
    # -- carries them, so a restarted run that did the same work ends on the
    # -- same counter values as the uninterrupted one.
    baseline_counters = dict(baseline["result"]["counters"])
    restarted_counters = dict(resume["result"]["counters"])
    counter_differences = {
        name: {
            "baseline": baseline_counters.get(name),
            "restarted": restarted_counters.get(name),
        }
        for name in sorted(set(baseline_counters) | set(restarted_counters))
        if baseline_counters.get(name) != restarted_counters.get(name)
    }
    counters_identical = not counter_differences
    node_counter_differences = _node_counter_differences(
        baseline["node_counters"], resume["node_counters"]
    )
    node_counters_identical = not node_counter_differences

    legitimacy = check_token_legitimacy(
        restarted_tokens,
        vocabulary_size=int(baseline["vocabulary_size"]),
        eos_token_ids=[int(t) for t in baseline["eos_token_ids"]],
        stop_reason=resume["result"]["stop_reason"],
    )
    legitimacy += validate_token_ids(
        restarted_tokens, int(baseline["vocabulary_size"])
    )
    checkpoint = interrupt["checkpoint"]

    negative_tokens = (
        [int(t) for t in negative["result"]["generated_token_ids"]]
        if negative is not None
        else []
    )
    negative_matched, negative_divergence = (
        _compare(baseline_tokens, negative_tokens)
        if negative is not None
        else (False, None)
    )
    negative_control = (
        None
        if negative is None
        else {
            "erased_objects": negative["erased_objects"],
            "erased_storage_classes": ["STATE"],
            "pid": negative["pid"],
            "token_ids": negative_tokens,
            "diverged_from_baseline": not negative_matched,
            "first_divergence_index": negative_divergence,
            "stop_reason": negative["result"]["stop_reason"],
            "failure": negative["result"]["failure"],
            "exit_status": negative["exit_status"],
        }
    )

    state_only_tokens = (
        [int(t) for t in state_only["result"]["generated_token_ids"]]
        if state_only is not None
        else []
    )
    state_only_matched, state_only_divergence = (
        _compare(baseline_tokens, state_only_tokens)
        if state_only is not None
        else (False, None)
    )
    state_only_control = (
        None
        if state_only is None
        else {
            "question": (
                "are the STATE-class resources and the cursor on their own "
                "enough to continue, or does the restart depend on activation "
                "scratch that a deployment would not persist?"
            ),
            "erased_objects": state_only["erased_objects"],
            "erased_storage_classes": state_only["erased_storage_classes"],
            "pid": state_only["pid"],
            "token_ids": state_only_tokens,
            "matches_baseline": state_only_matched and bool(state_only_tokens),
            "first_divergence_index": state_only_divergence,
            "stop_reason": state_only["result"]["stop_reason"],
            "failure": state_only["result"]["failure"],
            "exit_status": state_only["exit_status"],
            "reported_only": True,
        }
    )

    reasons: list[str] = []
    if negative is not None and negative_matched:
        reasons.append(
            "the negative control reproduced the baseline with the KV state "
            "erased; this experiment does not measure what it claims to"
        )
    if failed_guards:
        reasons.append(f"guards failed: {failed_guards}")
    if not matched:
        reasons.append(
            "the restarted sequence differs from the uninterrupted one"
            + (f" at index {divergence}" if divergence is not None else "")
        )
    if not work_identical:
        reasons.append("the restarted transactions retired different work")
    if not counters_identical:
        reasons.append(
            f"{len(counter_differences)} architectural counters differ: "
            + ", ".join(sorted(counter_differences)[:6])
        )
    if not node_counters_identical:
        reasons.append(
            f"per-node architectural counter state differs on "
            f"{len(node_counter_differences)} node entries"
        )
    if legitimacy:
        reasons.append(f"token legitimacy: {legitimacy}")

    record = ExecutionRecord(
        evidence_class=EvidenceClass.FUNCTIONAL,
        workload=WorkloadIdentity(
            model_id=baseline["model_id"],
            workload_id=workload["workload_id"],
            workload_digest=workload["digest"],
            prompt_token_count=len(workload["token_ids"]),
            max_new_tokens=limit,
            generation_policy_digest=baseline["generation_policy_digest"],
            numeric_profile=baseline["numeric_profile"],
            graph_id=baseline["graph_id"],
            tokenizer_sha256=_tokenizer_digest(args.workload, workload),
            generation_policy=baseline["generation_policy"],
        ),
        target=TargetIdentity(
            target_id=baseline["target_id"],
            backend=baseline["deployment_backend"],
            topology_class=int(baseline["topology_class"]),
            node_count=int(baseline["node_count"]),
            capability_digest=baseline["capability_digest"],
            deployment_digest=baseline["deployment_digest"],
            technology_view=baseline["technology_view"],
        ),
        generated_token_ids=tuple(restarted_tokens),
        stop_reason=resume["result"]["stop_reason"],
        counters=restarted_counters,
        implementation_identity=baseline["implementation_identity"],
        notes={
            "claim": (
                "a generation stopped after N decode steps, serialised, and "
                "finished in a fresh process produces the same token sequence "
                "as an uninterrupted run of the same workload on the same "
                "backend"
            ),
            "token_identical": token_identical,
            "first_divergence_index": divergence,
            "first_divergence": (
                None
                if divergence is None
                else {
                    "index": divergence,
                    "baseline_token": (
                        baseline_tokens[divergence]
                        if divergence < len(baseline_tokens)
                        else None
                    ),
                    "restarted_token": (
                        restarted_tokens[divergence]
                        if divergence < len(restarted_tokens)
                        else None
                    ),
                }
            ),
            "retired_work_identical": work_identical,
            "negative_control": negative_control,
            "state_only_control": state_only_control,
            "counters_identical": counters_identical,
            "counter_differences": counter_differences,
            "node_counters_identical": node_counters_identical,
            "node_counter_differences": node_counter_differences,
            "node_counters": resume["node_counters"],
            "token_legitimacy_problems": legitimacy,
            "guards": guards,
            "failed_guards": failed_guards,
            "stop_after_tokens": args.stop_after,
            "expected_token_count": expected_length,
            "baseline_token_ids": baseline_tokens,
            "interrupted_prefix_token_ids": interrupt_tokens,
            "restarted_token_ids": restarted_tokens,
            "resumed_tail_token_ids": tail,
            "process_ids": {phase: phases[phase]["pid"] for phase in PHASES},
            "source_identity": {
                phase: phases[phase]["source_identity"] for phase in PHASES
            },
            "phase_stop_reasons": {
                phase: phases[phase]["result"]["stop_reason"] for phase in PHASES
            },
            "phase_wall_seconds": {
                phase: phases[phase]["result"]["wall_seconds"] for phase in PHASES
            },
            "checkpoint": {
                "schema": read_manifest(args.checkpoint)["schema"],
                "node_count": checkpoint["node_count"],
                "object_count": checkpoint["object_count"],
                "mutable_bytes": checkpoint["mutable_bytes"],
                "stored_bytes": checkpoint["stored_bytes"],
                "write_seconds": checkpoint["seconds"],
                "restore_seconds": resume["restore_seconds"],
                "session": checkpoint["session"],
                "objects": checkpoint["objects"],
            },
            "verification": baseline["verification"],
            "engine_coverage": baseline["engine_coverage"],
            "work_directory": str(work),
            "wall_seconds": round(wall, 1),
        },
        failure="; ".join(reasons) or None,
    )

    status = "pass" if not reasons else "failed"
    _write(
        args.output,
        {"schema": SCHEMA, "status": status, "record": record.to_dict()},
    )

    print("\n--- restart exactness ---")
    print(f"baseline   ({len(baseline_tokens)} tokens): {baseline_tokens}")
    print(f"interrupted({len(interrupt_tokens)} tokens): {interrupt_tokens}")
    print(f"restarted  ({len(restarted_tokens)} tokens): {restarted_tokens}")
    print(f"resumed tail ({len(tail)} tokens): {tail}")
    for name in sorted(guards):
        print(f"  guard {name:44s} {'ok' if guards[name] else 'FAILED'}")
    print(f"token identical: {token_identical}")
    print(f"retired work identical: {work_identical}")
    print(f"counters identical: {counters_identical}")
    print(f"per-node counters identical: {node_counters_identical}")
    if negative_control is not None:
        print(
            f"negative control ({len(negative_tokens)} tokens): {negative_tokens} "
            f"-> diverged={negative_control['diverged_from_baseline']} "
            f"at index {negative_control['first_divergence_index']}"
        )
    if state_only_control is not None:
        print(
            f"state-only control ({len(state_only_tokens)} tokens): "
            f"{state_only_tokens} -> matches baseline="
            f"{state_only_control['matches_baseline']} "
            f"(reported, not gated)"
        )
    for name, values in counter_differences.items():
        print(f"  counter {name}: baseline={values['baseline']} restarted={values['restarted']}")
    for problem in legitimacy:
        print(f"  TOKEN LEGITIMACY {problem}")
    if divergence is not None:
        print(f"first divergence at index {divergence}")
    print(f"wrote {args.output} ({status})")
    return 0 if status == "pass" else 5


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kernel-ir", type=Path, required=True)
    parser.add_argument("--backend", choices=sorted(BACKENDS), required=True)
    parser.add_argument("--capability", type=Path, required=True)
    parser.add_argument("--workload", type=Path, required=True)
    parser.add_argument("--deployment-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-new-tokens", type=int, default=None)
    parser.add_argument(
        "--stop-after",
        type=int,
        default=3,
        help="tokens to produce before the interrupted process serialises",
    )
    parser.add_argument("--topology", default=None)
    parser.add_argument("--work-dir", type=Path, default=None)
    parser.add_argument(
        "--no-state-only-control",
        dest="state_only_control",
        action="store_false",
        help=(
            "skip the control that erases activation scratch and keeps only "
            "the STATE images"
        ),
    )
    parser.add_argument(
        "--no-negative-control",
        dest="negative_control",
        action="store_false",
        help="skip the blinded-checkpoint control that proves the test can fail",
    )
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--phase", choices=PHASES, default=None)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--phase-output", type=Path, default=None)
    args = parser.parse_args()

    if args.phase is None:
        return orchestrate(args)
    if args.checkpoint is None or args.phase_output is None:
        print("--phase requires --checkpoint and --phase-output", file=sys.stderr)
        return 1
    runner = {
        "baseline": run_baseline,
        "interrupt": run_interrupt,
        "resume": run_resume,
    }[args.phase]
    return runner(args)


if __name__ == "__main__":
    raise SystemExit(main())
