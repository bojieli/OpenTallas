#!/usr/bin/env python3
"""Golden control-path vectors for rung G1e, from the reference model alone.

Rung G1e (``configs/gates/redesign_gates.json``) asks for the governed
workload's whole CONTROL path in RTL with the engine results injected at the
engine result boundary, and the RTL issue trace compared to the golden model's
element for element.  Two properties decide whether that is evidence or
theatre, and both are enforced here rather than asserted:

**The golden is produced independently.**  Everything in the emitted trace
comes from ``runtime.sim.device.Device`` executing the governed workload
``TA-QW-EOS-1`` through ``runtime.driver.GenerationDriver`` -- the same
reference model the deployment co-simulation uses -- and from
``runtime.sim.memory.ViewResolver`` resolving each operand view against the
loop bindings the device itself recorded at that instruction.  No RTL is
compiled, run or read by this tool.  A golden derived from the RTL run would
make the later comparison a tautology; this one cannot be, because the RTL
does not exist as far as this file is concerned.

**Nothing in the control path may come from the model.**  The injected stream
carries, per issue, only the engine's completion (fault and trap class) and
the result WORDS the RTL control path can observe.  Which words those are is
derived, not chosen: the sequencer reads device memory in exactly one place --
a PREDICATE whose truth is a word in an object (``BOOLEAN_OBJECT`` /
``EOS_MEMBER``, ``runtime/sim/device.py:_object_predicate``,
``rtl/abi3/ot_a3_microsequencer.sv`` S_PRED_OBJECT) -- so the stream carries
the words those predicates name and nothing else.  For a deployment whose
program declares no such predicate the derived set is empty, and the artifact
says so with the count that proves it rather than leaving the reader to
assume the injection was small because it was convenient.

Emitted, per storage class, into ``--output``:

* ``a3_program.hex`` / ``a3_descriptor.hex`` / ``a3_symbol.hex`` -- the images
  the design's own host load path is fed with, in the format
  ``tools/build_abi3_deployment_rtl_vectors.py`` already publishes.
* ``g1e_case.hex`` -- one record per pass: the configuration the transaction
  runs under and the golden counters it must reproduce.
* ``g1e_meta.hex`` -- the geometry the checker refuses to guess.
* ``g1e_golden_trace.txt`` -- the compared trace: per issue the opcode,
  descriptor id and program counter, then every resolved view with its slot,
  descriptor id, extent, extent axis, element offset and rank.
* ``g1e_golden_trace_queue.txt`` -- the same trace with the SCHEDULE record's
  queue added.  The queue is a pure function of the operator's schedule
  descriptor (``Device._issue_queue``), so it can be compared; it is emitted
  as a separate file so the gate-compared field set stays exactly the one the
  shipped harness declares, and the queue comparison is reported beside it.
* ``g1e_inject.txt`` -- the injected engine results, in issue order.
* ``g1e_vectors.json`` -- the manifest: source digests, the workload and
  oracle identity, per-pass records, and the measurements this file makes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The blocked-GEMM association is part of the numeric implementation
# identity, so the thread default is established before any runtime module
# imports NumPy, exactly as tools/run_accelerator_tokens.py does.
for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_variable, "8")

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import Major, NO_ID  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    PredicateKind,
    Symbol,
)
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    DESC_WORDS,
    DESCRIPTOR_PREFIX_BYTES,
    OPERAND_FIELDS,
    PROGRAM_WORDS,
    SYMBOL_STRIDE,
    SYMBOL_WORDS,
    TARGETS,
    certified_deployment_identity,
    checkpoint_root,
    hex_lines,
    resolved_views,
)

SCHEMA = "opentallas.rtl.abi3_g1e_control_vectors.v1"
WORKLOAD_ID = "TA-QW-EOS-1"
WORKLOAD_PATH = "build/workloads/qwen3-8b/TA-QW-EOS-1.json"
ORACLE_PATH = "results/abi3/qwen3_reference_oracle_eos.json"

CASE_STRIDE = 32
META_WORDS = 16

# The storage classes G1e requires, and the shipped target each is.
STORES = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}

# The trace's compared field sets.  The first is what the shipped verification
# harness already declares for an RTL issue; the second adds the schedule the
# SCHEDULE record selected.  ``serial`` and ``irs_slot`` are RTL-internal
# allocations the reference model does not compute and are deliberately absent
# from both: a golden that carried a field it had invented would be comparing
# the RTL against this file rather than against the model.
GOLDEN_ISSUE_FIELDS = ("family", "sub", "descriptor_id", "pc")
GOLDEN_ISSUE_FIELDS_QUEUE = ("family", "sub", "descriptor_id", "pc", "queue")
GOLDEN_VIEW_FIELDS = (
    "slot",
    "descriptor_id",
    "extent",
    "extent_axis",
    "element_offset",
    "rank",
)

SOURCE_FILES = (
    "runtime/sim/device.py",
    "runtime/sim/memory.py",
    "runtime/driver.py",
    "runtime/abi3/deployment.py",
    "runtime/abi3/descriptors.py",
    "runtime/abi3/records.py",
    "runtime/abi3/verifier.py",
    "runtime/abi3/request.py",
    "tools/build_abi3_deployment_rtl_vectors.py",
    "tools/build_abi3_g1e_control_vectors.py",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def predicate_observable_objects(deployment: Deployment) -> list[dict[str, int]]:
    """Every (object, element) word the sequencer can read as a predicate.

    This is the derivation that decides what the injected stream must carry.
    ``runtime/sim/device.py:_object_predicate`` and
    ``rtl/abi3/ot_a3_microsequencer.sv`` state S_PRED_OBJECT are the only
    places either machine reads a device-memory word to decide control flow;
    every other predicate kind is answered from the loop stack, the symbol
    file or the phase.  A word no PREDICATE names can therefore change no
    control decision, and the stream does not have to carry it.
    """
    out: list[dict[str, int]] = []
    for descriptor_id in deployment.table.ids_of_type(
        ExtendedDescriptorType.PREDICATE
    ):
        payload = deployment.table[descriptor_id].payload
        kind = PredicateKind(int(payload["predicate_kind"]))
        if kind not in (PredicateKind.BOOLEAN_OBJECT, PredicateKind.EOS_MEMBER):
            continue
        out.append(
            {
                "predicate_descriptor_id": int(descriptor_id),
                "kind": kind.name,
                "object_id": int(payload["object_id"]),
                "element_index": int(payload["element_index"]),
            }
        )
    return out


def predicated_instruction_count(device: Device) -> int:
    return sum(
        1
        for instruction in device.instructions
        if int(getattr(instruction, "predicate_id", NO_ID)) != NO_ID
    )


class PassRecorder:
    """Observe every transaction the driver runs, and nothing else.

    The recorder is installed around ``Device.run_transaction`` so that the
    passes it sees are the passes the *driver* chose to run -- the workload's
    own prefill and decode sequence -- rather than a sequence this file
    invented.  The issue stream is the device's own trace and the views are
    the device's own resolver's.
    """

    def __init__(self, device: Device) -> None:
        self.device = device
        self.passes: list[dict[str, Any]] = []
        self._original = device.run_transaction

    def __enter__(self) -> "PassRecorder":
        device = self.device
        original = self._original

        def run_transaction(session, **kwargs):  # noqa: ANN001, ANN202
            mark = len(device.trace)
            started = time.perf_counter()
            result = original(session, **kwargs)
            seconds = time.perf_counter() - started
            symbols = dict(kwargs.get("symbols") or {})
            symbols.setdefault(int(Symbol.PHASE), 0)
            symbols.setdefault(int(Symbol.GENERATION_INDEX), 0)
            symbols[int(Symbol.NODE_COUNT)] = int(device.node_count)
            symbols[int(Symbol.NODE_ID)] = 0
            counters = dict(result.counters or {})
            issues: list[dict[str, Any]] = []
            for entry in device.trace[mark:]:
                instruction = device.instructions[entry["pc"]]
                family = Major(instruction.major)
                issues.append(
                    {
                        "pc": int(entry["pc"]),
                        "family": int(instruction.major),
                        "sub": int(instruction.sub),
                        "descriptor_id": int(instruction.descriptor_id),
                        "queue": int(
                            device._issue_queue(  # noqa: SLF001
                                instruction, family
                            )
                        ),
                        "views": resolved_views(device, entry, symbols),
                        "output_words": _output_words(device, entry, symbols),
                    }
                )
            self.passes.append(
                {
                    "entrypoint_id": int(kwargs.get("entrypoint_id", -1)),
                    "symbols": {int(k): int(v) for k, v in sorted(symbols.items())},
                    "status": int(result.status),
                    "complete": bool(result.status == 0),
                    "trap_class": int(result.trap_class),
                    "message": str(result.message or ""),
                    "first_fault": int(result.first_fault_instruction),
                    "fetched": int(result.fetched),
                    "retired": int(result.retired),
                    "predicated_off": int(result.predicated_off),
                    "issued": int(counters.get("instructions.issued", 0)),
                    "loop_iterations": int(counters.get("control.loop_iterations", 0)),
                    "wait_events": int(counters.get("queue.wait_events", 0)),
                    "seconds": round(seconds, 3),
                    "issues": issues,
                }
            )
            return result

        device.run_transaction = run_transaction  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: object) -> None:
        self.device.run_transaction = self._original  # type: ignore[method-assign]


def _output_words(device: Device, entry: dict[str, Any], symbols: dict[int, int]) -> int:
    """How many words this issue's output views cover, per the model.

    Reported, not injected: it is the size of the result stream a run that
    supplied every output word would have to carry, and it is the number that
    says why such a stream is not the affordable form of this rung.
    """
    instruction = device.instructions[entry["pc"]]
    try:
        operator = device.deployment.table.get(
            int(instruction.descriptor_id), ExtendedDescriptorType.OPERATOR
        )
    except Exception:  # not an operator instruction
        return 0
    total = 0
    for field in OPERAND_FIELDS:
        if not field.startswith("output_view"):
            continue
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        resolved = device.views.resolve(view_id, entry["loops"], symbols)
        words = 1
        for dim in resolved.dims:
            words *= int(dim)
        total += words
    return total


def run_golden(
    store: str, checkpoint: Path | None, weight_cache_bytes: int
) -> dict[str, Any]:
    """Execute the governed workload on the reference model and record it."""
    target = next(t for t in TARGETS if t.key == STORES[store])
    identity = certified_deployment_identity(target)
    deployment = Deployment.read(ROOT / target.deployment)
    actual = deployment.deployment_digest.hex()
    if actual != identity.deployment_sha256:
        raise SystemExit(
            f"{target.key}: deployment digest is {actual}, the certificate at "
            f"{identity.evidence_artifact} case {identity.evidence_case!r} "
            f"requires {identity.deployment_sha256}"
        )
    capability = Capability.from_dict(
        json.loads((ROOT / target.capability).read_text(encoding="utf-8"))
    )
    if capability.digest != identity.capability_sha256:
        raise SystemExit(
            f"{target.key}: capability digest is {capability.digest}, the "
            f"certificate requires {identity.capability_sha256}"
        )
    report = verify_deployment(deployment, capability)
    if not report.admitted:
        raise SystemExit(f"{target.key}: the ABI verifier refuses it: {report.errors}")

    workload = json.loads((ROOT / WORKLOAD_PATH).read_text(encoding="utf-8"))
    oracle = json.loads((ROOT / ORACLE_PATH).read_text(encoding="utf-8"))
    oracle_case = oracle["results"][WORKLOAD_ID]
    if oracle_case["workload_digest"] != workload["digest"]:
        raise SystemExit(
            "the oracle's workload digest does not match the workload on disk; "
            "comparing a run against gold produced for a different prompt is "
            "refused, not recorded as a mismatch"
        )

    load_engines()
    device = Device(
        deployment,
        capability,
        root=checkpoint_root(target, checkpoint),
        verify=False,
        trace=True,
        decoded_weight_cache_bytes=weight_cache_bytes,
    )
    driver = GenerationDriver(device)
    prompt = [int(token) for token in workload["token_ids"]]
    started = time.perf_counter()
    with PassRecorder(device) as recorder:
        result = driver.generate(prompt, max_new_tokens=int(workload["max_new_tokens"]))
    wall = time.perf_counter() - started
    generated = [int(token) for token in result.generated_token_ids]
    if generated != [int(t) for t in oracle_case["generated_token_ids"]]:
        raise SystemExit(
            f"{target.key}: the reference model produced {generated}, the "
            f"oracle's gold is {oracle_case['generated_token_ids']}; a golden "
            "trace from a run that does not reproduce the gold is not this "
            "workload's control path"
        )
    if result.stop_reason != "eos":
        raise SystemExit(
            f"{target.key}: stop reason is {result.stop_reason!r}, the governed "
            "workload's gold ends in the official EOS"
        )

    # The post-EOS transaction, attempted on the very session that reached
    # EOS.  It is recorded with the class that refused it and the layer that
    # did, because which layer refuses is exactly what G1e's eos.post_eos_
    # refused field is about.
    session = next(iter(device.sessions.values()))
    post = device.run_transaction(session, entrypoint_id=1, symbols={})
    post_eos = {
        "attempted": True,
        "status": int(post.status),
        "refused": bool(post.status != 0),
        "trap_class": int(post.trap_class),
        "message": str(post.message or ""),
        "refused_by": "runtime.sim.device.Device.run_transaction (Session.finished)",
        "refused_in_rtl": False,
        "why": (
            "the refusal is a host session-state refusal, taken before any "
            "instruction is fetched; it is not an act of the RTL control "
            "plane and this vehicle cannot measure it as one"
        ),
    }

    return {
        "store": store,
        "target": target,
        "identity": identity,
        "deployment": deployment,
        "capability": capability,
        "report": report,
        "workload": workload,
        "oracle": oracle,
        "oracle_case": oracle_case,
        "device": device,
        "driver": driver,
        "result": result,
        "generated": generated,
        "passes": recorder.passes,
        "post_eos": post_eos,
        "wall_seconds": round(wall, 2),
    }


def emit(golden: dict[str, Any], out: Path) -> dict[str, Any]:
    device: Device = golden["device"]
    deployment: Deployment = golden["deployment"]
    passes: list[dict[str, Any]] = golden["passes"]
    out.mkdir(parents=True, exist_ok=True)

    image = deployment.program
    header_blob = image[:256]
    body = image[256:]
    instruction_count = int.from_bytes(header_blob[16:20], "little")
    entrypoint_count = int.from_bytes(header_blob[20:24], "little")
    work_bound = int(device.header.max_retired_work)

    program_words = [
        int.from_bytes(body[offset : offset + 32], "little")
        for offset in range(0, len(body), 32)
    ]
    table = deployment.table
    desc_words = []
    for index in range(len(table)):
        record = table._records[index]  # noqa: SLF001
        prefix = record[:DESCRIPTOR_PREFIX_BYTES]
        desc_words.append(
            int.from_bytes(prefix + bytes(DESCRIPTOR_PREFIX_BYTES - len(prefix)), "little")
        )
    state_count = len(table.ids_of_type(ExtendedDescriptorType.STATE))

    observable = predicate_observable_objects(deployment)
    observable_index = {
        (entry["object_id"], entry["element_index"]) for entry in observable
    }

    symbol_words: list[int] = []
    case_words: list[int] = []
    trace_lines = [
        "FIELDS ISSUE " + " ".join(GOLDEN_ISSUE_FIELDS),
        "FIELDS VIEW " + " ".join(GOLDEN_VIEW_FIELDS),
    ]
    queue_lines = [
        "FIELDS ISSUE " + " ".join(GOLDEN_ISSUE_FIELDS_QUEUE),
        "FIELDS VIEW " + " ".join(GOLDEN_VIEW_FIELDS),
    ]
    result_lines = [
        "# RESULT <family> <sub> <descriptor_id> <pc> <fault> <trap_class> "
        "<word count>, then that many WORD <address> <data> lines",
    ]
    total_issues = 0
    total_views = 0
    total_result_words = 0
    total_output_words = 0
    pass_records: list[dict[str, Any]] = []

    for index, record in enumerate(passes):
        symbol_base = len(symbol_words)
        mask = 0
        for slot in range(SYMBOL_STRIDE):
            value = record["symbols"].get(slot)
            symbol_words.append(0 if value is None else int(value) & 0xFFFFFFFF)
            if value is not None:
                mask |= 1 << slot
        entry = next(
            e
            for e in deployment.entrypoints
            if e["entrypoint_id"] == record["entrypoint_id"]
        )
        issue_base = total_issues
        view_base = total_views
        pass_views = 0
        pass_output_words = 0
        for issue in record["issues"]:
            fields = [
                issue["family"],
                issue["sub"],
                issue["descriptor_id"],
                issue["pc"],
            ]
            trace_lines.append("ISSUE " + " ".join(str(v) for v in fields))
            queue_lines.append(
                "ISSUE " + " ".join(str(v) for v in fields + [issue["queue"]])
            )
            for view in sorted(issue["views"], key=lambda v: int(v["slot"])):
                line = "VIEW " + " ".join(
                    str(int(view[name])) for name in GOLDEN_VIEW_FIELDS
                )
                trace_lines.append(line)
                queue_lines.append(line)
                pass_views += 1
            # The injected engine result: the completion, plus exactly the
            # words a PREDICATE could read back.  Everything else the engine
            # would have written is unreadable by the control plane and is
            # counted, not supplied.
            words: list[tuple[int, int]] = []
            if observable_index:
                words = _observable_words(device, issue, observable_index)
            result_lines.append(
                f"RESULT {issue['family']} {issue['sub']} "
                f"{issue['descriptor_id']} {issue['pc']} 0 0 {len(words)}"
            )
            for address, data in words:
                result_lines.append(f"WORD {address} {data}")
            total_result_words += len(words)
            pass_output_words += int(issue["output_words"])
            total_issues += 1
        total_views += pass_views
        total_output_words += pass_output_words

        words_record = [
            0,  # program base: one deployment per vector set
            instruction_count,
            0,  # descriptor base
            len(table),
            symbol_base,
            mask,
            int(entry["first_instruction"]),
            work_bound & 0xFFFFFFFF,
            (work_bound >> 32) & 0xFFFFFFFF,
            state_count,
            int(record["trap_class"]),
            1 if record["complete"] else 0,
            int(record["fetched"]),
            int(record["retired"]),
            int(record["predicated_off"]),
            int(record["issued"]),
            int(record["loop_iterations"]),
            int(record["wait_events"]),
            len(record["issues"]),
            pass_views,
            issue_base,
            len(record["issues"]),
            view_base,
            pass_views,
            int(record["entrypoint_id"]),
            index,
            int(record["symbols"].get(int(Symbol.GENERATION_INDEX), 0)),
            int(record["symbols"].get(int(Symbol.CONTEXT_LENGTH), 0)),
            entrypoint_count,
            0,
            0,
            0,
        ]
        if len(words_record) != CASE_STRIDE:
            raise SystemExit(
                f"case record is {len(words_record)} words, the stride is "
                f"{CASE_STRIDE}"
            )
        case_words.extend(words_record)
        pass_records.append(
            {
                "pass_index": index,
                "entrypoint_id": record["entrypoint_id"],
                "symbols": record["symbols"],
                "complete": record["complete"],
                "trap_class": record["trap_class"],
                "fetched": record["fetched"],
                "retired": record["retired"],
                "predicated_off": record["predicated_off"],
                "issued": record["issued"],
                "loop_iterations": record["loop_iterations"],
                "wait_events": record["wait_events"],
                "issue_count": len(record["issues"]),
                "view_count": pass_views,
                "golden_output_words": pass_output_words,
                "golden_seconds": record["seconds"],
            }
        )

    meta = [
        len(passes),
        total_issues,
        total_views,
        total_issues,  # one injected result per issue
        CASE_STRIDE,
        total_result_words,
        len(program_words),
        len(desc_words),
        len(symbol_words),
        0 if golden["store"] == "rom" else 1,
        instruction_count,
        len(table),
        state_count,
        work_bound & 0xFFFFFFFF,
        (work_bound >> 32) & 0xFFFFFFFF,
        len(observable),
    ]
    if len(meta) != META_WORDS:
        raise SystemExit(f"meta is {len(meta)} words, the checker reads {META_WORDS}")

    files = {
        "a3_program.hex": hex_lines(program_words, 256, PROGRAM_WORDS),
        "a3_descriptor.hex": hex_lines(
            desc_words, DESCRIPTOR_PREFIX_BYTES * 8, DESC_WORDS
        ),
        "a3_symbol.hex": hex_lines(symbol_words, 32, SYMBOL_WORDS),
        "g1e_case.hex": hex_lines(case_words, 32),
        "g1e_meta.hex": hex_lines(meta, 32),
        "g1e_golden_trace.txt": "\n".join(trace_lines) + "\n",
        "g1e_golden_trace_queue.txt": "\n".join(queue_lines) + "\n",
        "g1e_inject.txt": "\n".join(result_lines) + "\n",
    }
    for name, payload in files.items():
        (out / name).write_text(payload, encoding="ascii")

    compared_elements = total_issues * len(GOLDEN_ISSUE_FIELDS) + total_views * len(
        GOLDEN_VIEW_FIELDS
    )
    target = golden["target"]
    identity = golden["identity"]
    manifest = {
        "schema": SCHEMA,
        "storage_class": golden["store"],
        "workload_id": WORKLOAD_ID,
        "produced_by": "tools/build_abi3_g1e_control_vectors.py",
        "golden_model": {
            "module": "runtime.sim.device.Device",
            "driver": "runtime.driver.GenerationDriver",
            "view_resolution": "runtime.sim.memory.ViewResolver (the device's own)",
            "independent_of_rtl": True,
            "how": (
                "this tool compiles, runs and reads no RTL; the issue stream is "
                "Device.trace and every view is resolved by the device's own "
                "resolver against the loop bindings the device recorded at that "
                "instruction"
            ),
            "wall_seconds": golden["wall_seconds"],
        },
        "deployment": {
            "target_key": target.key,
            "directory": target.deployment,
            "deployment_sha256": identity.deployment_sha256,
            "capability": target.capability,
            "capability_sha256": identity.capability_sha256,
            "model_id": identity.model_id,
            "descriptor_count": len(table),
            "instruction_count": instruction_count,
            "entrypoint_count": entrypoint_count,
            "state_descriptor_count": state_count,
            "declared_max_retired_work": work_bound,
            "admitted": bool(golden["report"].admitted),
            "certificate": identity.record(),
        },
        "workload": {
            "path": WORKLOAD_PATH,
            "sha256": sha256_file(ROOT / WORKLOAD_PATH),
            "digest": golden["workload"]["digest"],
            "prompt_token_count": int(golden["workload"]["prompt_token_count"]),
            "max_new_tokens": int(golden["workload"]["max_new_tokens"]),
        },
        "oracle": {
            "path": ORACLE_PATH,
            "artifact_sha256": sha256_file(ROOT / ORACLE_PATH),
            "generated_token_ids": [
                int(t) for t in golden["oracle_case"]["generated_token_ids"]
            ],
            "stop_reason": golden["oracle_case"]["stop_reason"],
            "agreement": True,
        },
        "model_run": {
            "generated_token_ids": golden["generated"],
            "stop_reason": golden["result"].stop_reason,
            "transactions": int(golden["result"].transactions),
            "prefill_tokens": int(golden["result"].prefill_tokens),
        },
        "passes": pass_records,
        "counts": {
            "passes": len(passes),
            "issues": total_issues,
            "views": total_views,
            "compared_trace_elements": compared_elements,
            "injected_results": total_issues,
            "injected_result_words": total_result_words,
        },
        "injection_derivation": {
            "boundary": "engine_result",
            "supplies": [
                "the engine completion (fault and trap class) for each issue",
                "the result words a PREDICATE can read back, and no others",
            ],
            "predicate_readable_words": observable,
            "predicated_instructions_in_program": predicated_instruction_count(device),
            "result_words_supplied": total_result_words,
            "golden_output_words_if_every_word_were_supplied": total_output_words,
            "why": (
                "the sequencer reads device memory in exactly one place -- a "
                "PREDICATE whose truth is a word in an object -- so a word no "
                "PREDICATE names cannot change a control decision. This "
                "program declares "
                f"{len(observable)} such predicate word(s) and "
                f"{predicated_instruction_count(device)} predicated "
                "instruction(s); supplying the other "
                f"{total_output_words:,} output words would change nothing the "
                "control path can observe, and is counted here rather than "
                "carried"
            ),
        },
        "post_eos": golden["post_eos"],
        "source_sha256": {
            path: sha256_file(ROOT / path) for path in SOURCE_FILES
        },
        "emitted": {
            name: {
                "sha256": sha256_file(out / name),
                "bytes": (out / name).stat().st_size,
            }
            for name in files
        },
    }
    (out / "g1e_vectors.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _observable_words(
    device: Device, issue: dict[str, Any], observable: set[tuple[int, int]]
) -> list[tuple[int, int]]:
    """Result words this issue produced that a PREDICATE can read back.

    Only reached when the deployment declares an object predicate at all.  The
    address is the word offset inside the named object; the checker maps it to
    the vehicle's predicate window, which is the only place the RTL reads a
    result word for a control decision.
    """
    words: list[tuple[int, int]] = []
    for view in issue["views"]:
        object_id = int(view.get("object_id", NO_ID))
        if object_id == NO_ID:
            continue
        for named_object, element in sorted(observable):
            if named_object != object_id:
                continue
            memory = device.memory[named_object]
            value = int.from_bytes(memory.read(element * 4, 4), "little")
            words.append((element, value))
    return words


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", choices=sorted(STORES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument(
        "--weight-cache-bytes",
        type=int,
        default=2 << 30,
        help="decoded weight cache budget for the reference model",
    )
    args = parser.parse_args()

    golden = run_golden(args.store, args.checkpoint, args.weight_cache_bytes)
    manifest = emit(golden, args.output)
    counts = manifest["counts"]
    print(
        "PASS: ABI3 G1e golden control vectors "
        f"store={manifest['storage_class']} passes={counts['passes']} "
        f"issues={counts['issues']} views={counts['views']} "
        f"elements={counts['compared_trace_elements']} "
        f"injected={counts['injected_results']} "
        f"words={counts['injected_result_words']} "
        f"tokens={manifest['model_run']['generated_token_ids']} "
        f"stop={manifest['model_run']['stop_reason']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
