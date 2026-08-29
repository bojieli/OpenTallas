#!/usr/bin/env python3
"""Independent ABI 3.0 deployment legality checker.

Reads a deployment directory (``deployment.json``, ``descriptors.bin``,
``program.bin``) and a capability JSON document, and writes a canonical JSON
legality report.  Exit status is ``0`` when the deployment is admissible and
``1`` when it is not, so the tool can gate a release without anyone reading the
report.

This checker is deliberately *not* the encoder's twin:

* it never imports ``runtime.abi3.builder`` or any compiler backend, so it
  cannot inherit a mistake from the thing that produced the artifact;
* it never imports ``runtime.abi3.verifier`` either, so running both against one
  deployment is a genuine second opinion rather than the same proof twice; and
* every bound it reports is re-derived from the decoded descriptor table and
  instruction stream, not read out of the manifest.

It uses the ABI 3.0 *decoders* (record, descriptor, deployment, capability)
because re-implementing a wire format is how two implementations of one contract
silently disagree; the decoders are the contract, the proofs are the check.

Where this checker is deliberately stricter than ``runtime/abi3/verifier.py``,
the extra proof is named in ``checks`` so a disagreement between the two is
visible rather than mysterious.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.capability import Capability, canonical_json  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    DTYPE_BITS,
    NO_ID,
    PROGRAM_HEADER_BYTES,
    Control,
    DType,
    Feature,
    InstructionFlag,
    Major,
    Permission,
    Selection,
    State,
    StorageClass,
    feature_bits,
)
from runtime.abi3.crc import sha256_hex  # noqa: E402
from runtime.abi3.deployment import (  # noqa: E402
    Deployment,
    DeploymentError,
    resolve_path,
)
from runtime.abi3.descriptors import (  # noqa: E402
    MAX_DYNAMIC_TERMS,
    MAX_RANK,
    MAX_WAIT_PRODUCERS,
    Descriptor,
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
    decode_entrypoint_table,
)
from runtime.abi3.records import ProgramHeader, decode_body  # noqa: E402

REPORT_SCHEMA = "opentallas.abi3.legality_report.v1"

#: Descriptor type each instruction family must name in ``descriptor_id``.
FAMILY_DESCRIPTOR: dict[int, int] = {
    int(Major.DMA): int(ExtendedDescriptorType.OPERATOR),
    int(Major.TENSOR): int(ExtendedDescriptorType.OPERATOR),
    int(Major.VECTOR): int(ExtendedDescriptorType.OPERATOR),
    int(Major.ATTENTION): int(ExtendedDescriptorType.OPERATOR),
    int(Major.ROUTE): int(ExtendedDescriptorType.OPERATOR),
    int(Major.REDUCTION): int(ExtendedDescriptorType.OPERATOR),
    int(Major.SELECTION): int(ExtendedDescriptorType.OPERATOR),
    int(Major.LINK): int(ExtendedDescriptorType.COMMUNICATION),
    int(Major.STATE): int(ExtendedDescriptorType.STATE),
    int(Major.OBSERVATION): int(ExtendedDescriptorType.COUNTER_CLASS),
}

WRITE_PERMISSIONS = int(
    Permission.WRITE | Permission.STATE_PREPARE | Permission.STATE_COMMIT
)


class Report:
    """Accumulates named checks, errors and warnings in a stable order."""

    def __init__(self) -> None:
        self.checks: dict[str, bool] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.facts: dict[str, Any] = {}

    def check(self, name: str, ok: bool, message: str) -> bool:
        self.checks[name] = self.checks.get(name, True) and bool(ok)
        if not ok:
            self.errors.append(message)
        return bool(ok)

    def fail(self, name: str, message: str) -> None:
        self.check(name, False, message)

    def note(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def admitted(self) -> bool:
        return not self.errors


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------
def load_capability(path: Path) -> Capability:
    body = json.loads(path.read_text(encoding="utf-8"))
    return Capability.from_dict(body)


def load_deployment(root: Path, report: Report) -> Deployment | None:
    for name in ("deployment.json", "descriptors.bin", "program.bin"):
        if not (root / name).is_file():
            report.fail("bundle_complete", f"deployment is missing {name}")
    if not report.checks.get("bundle_complete", True):
        return None
    report.checks.setdefault("bundle_complete", True)
    try:
        deployment = Deployment.read(root)
    except (DeploymentError, ValueError, KeyError) as exc:
        report.fail("digest_chain", f"deployment does not decode: {exc}")
        return None
    report.checks.setdefault("digest_chain", True)
    return deployment


# ---------------------------------------------------------------------------
# proofs
# ---------------------------------------------------------------------------
def check_versions(header: ProgramHeader, report: Report) -> None:
    report.check(
        "abi_major",
        header.abi_major == 3,
        f"program declares ABI major {header.abi_major}, this checker implements 3",
    )
    report.check(
        "abi_minor",
        header.abi_minor <= 0,
        f"program requires ABI minor {header.abi_minor}",
    )
    report.check(
        "header_flags_reserved",
        header.flags == 0,
        "all version-3.0 program header flag bits are reserved",
    )


def check_manifest_binding(
    deployment: Deployment, header: ProgramHeader, report: Report
) -> None:
    manifest = deployment.manifest()
    report.check(
        "manifest_binds_table",
        manifest["descriptor_table_sha256"] == deployment.table.digest.hex(),
        "manifest descriptor-table digest does not match the table",
    )
    report.check(
        "header_binds_table",
        header.descriptor_table_digest == deployment.table.digest,
        "program header does not bind the descriptor table",
    )
    report.check(
        "header_binds_manifest",
        header.deployment_digest == deployment.deployment_digest,
        "program header does not bind the deployment manifest",
    )
    report.check(
        "manifest_work_bound",
        manifest["max_retired_work"] == header.max_retired_work,
        "manifest and program header disagree about the work bound",
    )
    report.check(
        "manifest_required_features",
        deployment.required_features == header.required_features,
        "manifest and program header declare different required features",
    )
    report.check(
        "manifest_instruction_count",
        manifest["instruction_count"] == header.instruction_count,
        "manifest and program header disagree about the instruction count",
    )


def check_capability(
    deployment: Deployment,
    header: ProgramHeader,
    capability: Capability,
    report: Report,
) -> None:
    required = feature_bits(header.required_features)
    available = {int(bit) for bit in capability.features}
    missing = sorted(required - available)
    report.check(
        "capability_features",
        not missing,
        f"capability does not implement required feature bits {missing}",
    )
    report.check(
        "capability_identity",
        deployment.capability_digest == capability.digest,
        "deployment was compiled against capability "
        f"{deployment.capability_digest[:16]}, this capability is "
        f"{capability.digest[:16]}",
    )
    report.check(
        "topology_class",
        int(deployment.topology_class) == int(capability.topology_class),
        "deployment topology class does not match the capability",
    )
    limits = capability.limits
    report.check(
        "instruction_bound",
        header.instruction_count <= limits["max_instructions"],
        f"program has {header.instruction_count} instructions, capability admits "
        f"{limits['max_instructions']}",
    )
    report.check(
        "descriptor_bound",
        len(deployment.table) <= limits["max_descriptors"],
        f"deployment has {len(deployment.table)} descriptors, capability admits "
        f"{limits['max_descriptors']}",
    )
    report.check(
        "declared_work_bound",
        header.max_retired_work <= limits["max_retired_work"],
        f"declared maximum retired work {header.max_retired_work} exceeds the "
        f"capability bound {limits['max_retired_work']}",
    )


def check_instructions(
    deployment: Deployment, instructions: list[Any], report: Report
) -> dict[str, Any]:
    table = deployment.table
    signalled: dict[int, int] = {}
    for index, instruction in enumerate(instructions):
        where = f"instruction {index} ({instruction.mnemonic})"
        try:
            instruction.validate()
        except ValueError as exc:
            report.fail("instruction_legality", f"{where}: {exc}")
            continue
        family = int(instruction.major)
        expected = FAMILY_DESCRIPTOR.get(family)
        if expected is not None:
            resolve(table, instruction.descriptor_id, expected, where, report)
        if instruction.predicate_id != NO_ID:
            resolve(
                table,
                instruction.predicate_id,
                int(ExtendedDescriptorType.PREDICATE),
                f"{where} predicate",
                report,
            )
        if instruction.wait_set_id != NO_ID:
            resolve(
                table,
                instruction.wait_set_id,
                int(ExtendedDescriptorType.EVENT_WAIT_SET),
                f"{where} wait set",
                report,
            )
        if instruction.signal_event_id != NO_ID:
            if instruction.signal_event_id in signalled:
                report.fail(
                    "events_single_assignment",
                    f"{where}: event {instruction.signal_event_id} is also "
                    f"signalled by instruction {signalled[instruction.signal_event_id]}",
                )
            signalled.setdefault(instruction.signal_event_id, index)
        flags = instruction.flags
        if flags & InstructionFlag.WAIT_ACQUIRE and instruction.wait_set_id == NO_ID:
            report.note(f"{where}: WAIT_ACQUIRE is set but no wait set is named")
        if flags & InstructionFlag.SIGNAL_RELEASE and instruction.signal_event_id == NO_ID:
            report.note(f"{where}: SIGNAL_RELEASE is set but no event is signalled")
        if flags & InstructionFlag.GLOBAL_SCOPE and family != int(Major.LINK):
            report.note(
                f"{where}: GLOBAL_SCOPE claims a cluster/wafer participant set "
                "but the descriptor is not a communication descriptor"
            )
        if flags & InstructionFlag.OPTIONAL_FEATURE:
            report.note(
                f"{where}: OPTIONAL_FEATURE requires an authenticated "
                "alternative path, which this bundle does not declare"
            )
    report.checks.setdefault("instruction_legality", True)
    report.checks.setdefault("events_single_assignment", True)
    return {"signalled": signalled}


def resolve(
    table: Any, descriptor_id: int, expected: int, where: str, report: Report
) -> Descriptor | None:
    if descriptor_id == NO_ID:
        report.fail("descriptor_resolution", f"{where}: descriptor ID is NO_ID")
        return None
    if not 0 <= descriptor_id < len(table):
        report.fail(
            "descriptor_resolution",
            f"{where}: descriptor ID {descriptor_id} is outside the table",
        )
        return None
    descriptor = table[descriptor_id]
    if descriptor.descriptor_type != expected:
        report.fail(
            "descriptor_resolution",
            f"{where}: descriptor {descriptor_id} is "
            f"{ExtendedDescriptorType(descriptor.descriptor_type).name}, expected "
            f"{ExtendedDescriptorType(expected).name}",
        )
        return None
    report.checks.setdefault("descriptor_resolution", True)
    return descriptor


def loop_trip(descriptor: Descriptor, capability: Capability, report: Report) -> int:
    """The largest number of iterations this loop can run, or 0 if unprovable."""
    payload = descriptor.payload
    where = f"loop descriptor {descriptor.descriptor_id}"
    step = payload["step"]
    declared = payload["max_iterations"]
    if step == 0:
        report.fail("loops_bounded", f"{where}: step is zero, so the loop is unbounded")
        return 0
    if declared <= 0:
        report.fail("loops_bounded", f"{where}: declares no maximum iteration count")
        return 0
    if declared > capability.limits["max_loop_trip"]:
        report.fail(
            "loops_bounded",
            f"{where}: declared maximum {declared} exceeds capability "
            f"{capability.limits['max_loop_trip']}",
        )
    selector = payload["bound_selector_kind"]
    if selector == int(SelectorKind.CONSTANT):
        span = payload["upper_bound"] - payload["lower_bound"]
        if span <= 0:
            report.fail("loops_bounded", f"{where}: constant span is not positive")
            return 0
        trip = (span + step - 1) // step
        if trip > declared:
            report.fail(
                "loops_bounded",
                f"{where}: constant trip {trip} exceeds the declared maximum {declared}",
            )
        return min(trip, declared)
    if selector == int(SelectorKind.RUNTIME_SYMBOL):
        try:
            Symbol(payload["bound_symbol_id"])
        except ValueError:
            report.fail(
                "loops_bounded",
                f"{where}: bound symbol {payload['bound_symbol_id']} is not in the "
                "frozen runtime-symbol registry",
            )
            return 0
        return declared
    report.fail("loops_bounded", f"{where}: unknown bound selector kind {selector}")
    return 0


def check_control_flow(
    deployment: Deployment,
    header: ProgramHeader,
    instructions: list[Any],
    capability: Capability,
    report: Report,
) -> dict[str, Any]:
    table = deployment.table
    limits = capability.limits
    stack: list[tuple[int, int]] = []
    multiplier = 1
    work = 0
    depth = 0
    completes: list[int] = []
    trips: dict[int, int] = {}
    for index, instruction in enumerate(instructions):
        if int(instruction.major) == int(Major.CONTROL):
            sub = instruction.sub
            if sub == int(Control.LOOP_SETUP):
                descriptor = resolve(
                    table,
                    instruction.control_id,
                    int(ExtendedDescriptorType.LOOP_CONTROL),
                    f"instruction {index} LOOP_SETUP",
                    report,
                )
                if descriptor is None:
                    continue
                trip = loop_trip(descriptor, capability, report)
                trips[descriptor.descriptor_id] = trip
                if descriptor.payload["body_start"] != index + 1:
                    report.fail(
                        "loop_bodies",
                        f"instruction {index}: loop body_start "
                        f"{descriptor.payload['body_start']} must be {index + 1}",
                    )
                stack.append((instruction.control_id, max(trip, 1)))
                multiplier *= max(trip, 1)
                depth = max(depth, len(stack))
                if len(stack) > limits["max_loop_depth"]:
                    report.fail(
                        "loop_depth",
                        f"instruction {index}: loop nesting {len(stack)} exceeds "
                        f"capability depth {limits['max_loop_depth']}",
                    )
                continue
            if sub == int(Control.LOOP_NEXT):
                if not stack:
                    report.fail(
                        "loops_closed",
                        f"instruction {index}: LOOP_NEXT with no open loop",
                    )
                    continue
                loop_id, trip = stack.pop()
                if instruction.control_id != loop_id:
                    report.fail(
                        "loops_closed",
                        f"instruction {index}: LOOP_NEXT closes loop "
                        f"{instruction.control_id} but {loop_id} is innermost",
                    )
                elif table[loop_id].payload["body_end"] != index:
                    report.fail(
                        "loop_bodies",
                        f"instruction {index}: loop body_end "
                        f"{table[loop_id].payload['body_end']} does not match",
                    )
                work += multiplier
                multiplier //= max(trip, 1)
                continue
            if sub == int(Control.BRANCH):
                target = instruction.control_id
                if not 0 <= target < len(instructions):
                    report.fail(
                        "branch_targets",
                        f"instruction {index}: branch target {target} is outside "
                        "the authenticated body",
                    )
                elif target <= index:
                    report.fail(
                        "branch_targets",
                        f"instruction {index}: branch target {target} is not "
                        "forward; only LOOP_NEXT transfers control backwards",
                    )
                elif stack and target > table[stack[-1][0]].payload["body_end"]:
                    report.note(
                        f"instruction {index}: forward branch leaves an open loop "
                        "body; the loop stack is not unwound by any instruction"
                    )
                continue
            if sub == int(Control.WAIT) and instruction.wait_set_id == NO_ID:
                report.fail(
                    "wait_operands", f"instruction {index}: WAIT without a wait set"
                )
            if sub == int(Control.COMPLETE):
                completes.append(index)
                if stack:
                    report.fail(
                        "completion",
                        f"instruction {index}: COMPLETE inside an open loop body",
                    )
        work += multiplier
    report.checks.setdefault("loops_bounded", True)
    report.checks.setdefault("loop_bodies", True)
    report.checks.setdefault("loop_depth", True)
    report.checks.setdefault("branch_targets", True)
    report.checks.setdefault("wait_operands", True)
    report.check(
        "loops_closed", not stack, f"program ends with {len(stack)} open loop(s)"
    )
    report.check(
        "completion",
        len(completes) == 1,
        f"program declares {len(completes)} COMPLETE instructions, expected 1",
    )
    if completes:
        report.check(
            "completion_terminal",
            completes[-1] == len(instructions) - 1,
            "COMPLETE is not the final instruction",
        )
    report.check(
        "proved_work_bound",
        work <= header.max_retired_work,
        f"re-derived retired work {work} exceeds the declared bound "
        f"{header.max_retired_work}",
    )
    return {"work": work, "depth": depth, "trips": trips}


def check_events(
    deployment: Deployment, signalled: dict[int, int], capability: Capability, report: Report
) -> int:
    table = deployment.table
    waited: set[int] = set()
    for descriptor in table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.EVENT_WAIT_SET):
            continue
        payload = descriptor.payload
        count = payload["producer_count"]
        where = f"wait set {descriptor.descriptor_id}"
        if count == 0:
            report.fail("events_producible", f"{where}: declares no producers")
            continue
        if count > MAX_WAIT_PRODUCERS:
            report.fail("events_producible", f"{where}: {count} producers exceed 12")
            continue
        required = payload["required_count"]
        if not 1 <= required <= count:
            report.fail(
                "events_producible",
                f"{where}: required_count {required} is not between 1 and {count}",
            )
        for slot in range(count):
            event = payload[f"producer_{slot}"]
            waited.add(event)
            if event not in signalled:
                report.fail(
                    "events_producible",
                    f"{where}: waits on event {event}, which no instruction signals",
                )
        for slot in range(count, MAX_WAIT_PRODUCERS):
            if payload[f"producer_{slot}"] != NO_ID:
                report.fail(
                    "events_producible",
                    f"{where}: producer slot {slot} is set beyond the declared count",
                )
    report.checks.setdefault("events_producible", True)
    report.check(
        "event_bound",
        len(signalled) <= capability.limits["max_events"],
        f"program signals {len(signalled)} distinct events, capability admits "
        f"{capability.limits['max_events']}",
    )
    return len(signalled)


def check_wait_ordering(
    deployment: Deployment, instructions: list[Any], signalled: dict[int, int], report: Report
) -> None:
    """A wait whose only producers come later cannot ever be satisfied."""
    table = deployment.table
    for index, instruction in enumerate(instructions):
        if instruction.wait_set_id == NO_ID:
            continue
        if not 0 <= instruction.wait_set_id < len(table):
            continue
        descriptor = table[instruction.wait_set_id]
        if descriptor.descriptor_type != int(ExtendedDescriptorType.EVENT_WAIT_SET):
            continue
        payload = descriptor.payload
        for slot in range(payload["producer_count"]):
            event = payload[f"producer_{slot}"]
            producer = signalled.get(event)
            if producer is not None and producer > index:
                report.note(
                    f"instruction {index}: waits on event {event}, whose only "
                    f"producer is the later instruction {producer}"
                )


def check_state(deployment: Deployment, instructions: list[Any], report: Report) -> int:
    table = deployment.table
    prepared: dict[int, int] = {}
    for index, instruction in enumerate(instructions):
        if int(instruction.major) != int(Major.STATE):
            continue
        descriptor = resolve(
            table,
            instruction.descriptor_id,
            int(ExtendedDescriptorType.STATE),
            f"instruction {index} state",
            report,
        )
        if descriptor is None:
            continue
        sid = descriptor.descriptor_id
        sub = instruction.sub
        if sub == int(State.PREPARE):
            if sid in prepared:
                report.fail(
                    "state_discipline",
                    f"instruction {index}: state {sid} is prepared twice without an "
                    f"intervening commit or discard (first at {prepared[sid]})",
                )
            prepared[sid] = index
            if not descriptor.permissions & Permission.STATE_PREPARE:
                report.fail(
                    "state_permissions",
                    f"instruction {index}: state {sid} lacks STATE_PREPARE permission",
                )
        elif sub in (int(State.COMMIT), int(State.DISCARD)):
            if sid not in prepared:
                report.fail(
                    "state_discipline",
                    f"instruction {index}: state {sid} is resolved without a "
                    "preceding prepare",
                )
            else:
                prepared.pop(sid)
            if sub == int(State.COMMIT) and not (
                descriptor.permissions & Permission.STATE_COMMIT
            ):
                report.fail(
                    "state_permissions",
                    f"instruction {index}: state {sid} lacks STATE_COMMIT permission",
                )
    for sid, index in sorted(prepared.items()):
        report.fail(
            "state_discipline",
            f"state {sid} prepared at instruction {index} has no reachable commit "
            "or discard",
        )
    report.checks.setdefault("state_discipline", True)
    report.checks.setdefault("state_permissions", True)
    return len(table.ids_of_type(int(ExtendedDescriptorType.STATE)))


def check_objects(deployment: Deployment, report: Report) -> None:
    for descriptor in deployment.table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.MEMORY_OBJECT):
            continue
        payload = descriptor.payload
        oid = descriptor.descriptor_id
        try:
            storage = StorageClass(payload["storage_class"])
        except ValueError:
            report.fail(
                "object_storage",
                f"object {oid}: unknown storage class {payload['storage_class']}",
            )
            continue
        writable = bool(descriptor.permissions & WRITE_PERMISSIONS)
        if storage == StorageClass.ROM and writable:
            report.fail(
                "object_permissions",
                f"object {oid}: ROM storage declares a write permission",
            )
        if descriptor.permissions & Permission.IMMUTABLE and writable:
            report.fail(
                "object_permissions",
                f"object {oid}: IMMUTABLE object declares a write path",
            )
        if payload["size_bytes"] == 0:
            report.fail("object_sizes", f"object {oid}: zero-size memory object")
        source = deployment.objects.get(oid)
        if source is None:
            report.fail(
                "object_sources", f"object {oid}: no source declared in the manifest"
            )
            continue
        if source.size_bytes != payload["size_bytes"]:
            report.fail(
                "object_sources",
                f"object {oid}: manifest source is {source.size_bytes} bytes, "
                f"descriptor declares {payload['size_bytes']}",
            )
        for segment in source.segments:
            try:
                path = resolve_path(deployment.root, segment.path)
            except DeploymentError as exc:
                report.fail("object_sources", f"object {oid}: {exc}")
                continue
            if not path.is_file():
                report.fail(
                    "object_sources",
                    f"object {oid}: source file {segment.path} does not exist",
                )
                continue
            if path.stat().st_size < segment.offset + segment.bytes:
                report.fail(
                    "object_sources",
                    f"object {oid}: segment runs past the end of {segment.path}",
                )
    for name in ("object_storage", "object_permissions", "object_sizes", "object_sources"):
        report.checks.setdefault(name, True)


def check_views(
    deployment: Deployment,
    capability: Capability,
    trips: dict[int, int],
    report: Report,
) -> None:
    limits = capability.limits
    positions = limits["max_context_positions"]
    symbol_max = {
        int(Symbol.SPAN_TOKENS): positions,
        int(Symbol.POSITION_START): positions,
        int(Symbol.POSITION_END): positions,
        int(Symbol.CONTEXT_LENGTH): positions,
        int(Symbol.PHASE): 1,
        int(Symbol.GENERATION_INDEX): positions,
        int(Symbol.MAX_NEW_TOKENS): positions,
        int(Symbol.BATCH): 1,
        int(Symbol.NODE_ID): max(limits["max_nodes"] - 1, 0),
        int(Symbol.NODE_COUNT): limits["max_nodes"],
        int(Symbol.ACTIVE_EXPERT_COUNT): limits["max_topk"],
        int(Symbol.SPARSE_INDEX_COUNT): positions,
        int(Symbol.LAYER_COUNT): 1024,
        int(Symbol.VOCABULARY_PARTITIONS): 1024,
    }
    table = deployment.table
    for descriptor in table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.TENSOR_VIEW):
            continue
        payload = descriptor.payload
        vid = descriptor.descriptor_id
        rank = payload["rank"]
        if not 1 <= rank <= MAX_RANK:
            report.fail("view_shape", f"view {vid}: rank {rank} is out of range")
            continue
        try:
            dtype = DType(payload["dtype"])
        except ValueError:
            report.fail("view_shape", f"view {vid}: unknown dtype {payload['dtype']}")
            continue
        for axis in range(rank, MAX_RANK):
            if payload[f"dim{axis}"] or payload[f"stride{axis}"]:
                report.fail(
                    "view_shape", f"view {vid}: axis {axis} beyond the rank is nonzero"
                )
        last = payload["element_offset"]
        for axis in range(rank):
            dim = payload[f"dim{axis}"]
            if dim == 0:
                report.fail("view_shape", f"view {vid}: axis {axis} has zero extent")
                dim = 1
            last += (dim - 1) * payload[f"stride{axis}"]
        terms = payload["dynamic_term_count"]
        if terms > MAX_DYNAMIC_TERMS:
            report.fail(
                "view_shape", f"view {vid}: {terms} dynamic terms exceed the maximum"
            )
            continue
        for slot in range(terms):
            kind = payload[f"term{slot}_kind"]
            index = payload[f"term{slot}_index"]
            stride = payload[f"term{slot}_stride"]
            if kind == int(SelectorKind.LOOP_INDUCTION):
                if index not in trips:
                    report.fail(
                        "view_terms",
                        f"view {vid} term {slot}: loop descriptor {index} is never "
                        "set up by any LOOP_SETUP",
                    )
                    continue
                last += (max(trips[index], 1) - 1) * stride
            elif kind == int(SelectorKind.RUNTIME_SYMBOL):
                if index not in symbol_max:
                    report.fail(
                        "view_terms",
                        f"view {vid} term {slot}: unknown runtime symbol {index}",
                    )
                    continue
                last += max(symbol_max[index] - 1, 0) * stride
            else:
                report.fail(
                    "view_terms",
                    f"view {vid} term {slot}: selector kind {kind} is not usable in "
                    "a tensor view",
                )
        for slot in range(terms, MAX_DYNAMIC_TERMS):
            if (
                payload[f"term{slot}_kind"]
                or payload[f"term{slot}_index"]
                or payload[f"term{slot}_stride"]
            ):
                report.fail(
                    "view_terms",
                    f"view {vid}: dynamic term {slot} is set beyond the declared count",
                )
        obj = resolve(
            table,
            descriptor.primary_object_id,
            int(ExtendedDescriptorType.MEMORY_OBJECT),
            f"view {vid} object",
            report,
        )
        if obj is None:
            continue
        needed = ((last + 1) * DTYPE_BITS[dtype] + 7) // 8
        if needed > obj.payload["size_bytes"]:
            report.fail(
                "view_bounds",
                f"view {vid}: maximum element {last} needs {needed} bytes but object "
                f"{obj.descriptor_id} is {obj.payload['size_bytes']} bytes",
            )
    for name in ("view_shape", "view_terms", "view_bounds"):
        report.checks.setdefault(name, True)


def check_operator_write_paths(deployment: Deployment, report: Report) -> None:
    """No engine may name a read-only destination.

    The wire format gives every descriptor an access mask, and section 5 says
    conflicting permissions fail admission.  A tensor operation whose output view
    is read-only, or whose output object is IMMUTABLE or in ROM, is a write with
    no legal path -- it must be refused at admission rather than trapped per
    launch.
    """
    table = deployment.table
    for descriptor in table.descriptors():
        if descriptor.descriptor_type != int(ExtendedDescriptorType.OPERATOR):
            continue
        oid = descriptor.descriptor_id
        for slot in range(2):
            view_id = descriptor.payload[f"output_view_{slot}"]
            if view_id == NO_ID:
                continue
            view = resolve(
                table,
                view_id,
                int(ExtendedDescriptorType.TENSOR_VIEW),
                f"operator {oid} output {slot}",
                report,
            )
            if view is None:
                continue
            if not view.permissions & Permission.WRITE:
                report.fail(
                    "engine_write_paths",
                    f"operator {oid}: output view {view_id} has no WRITE permission",
                )
            if view.permissions & Permission.IMMUTABLE:
                report.fail(
                    "engine_write_paths",
                    f"operator {oid}: output view {view_id} is IMMUTABLE",
                )
            if not 0 <= view.primary_object_id < len(table):
                continue
            obj = table[view.primary_object_id]
            if obj.descriptor_type != int(ExtendedDescriptorType.MEMORY_OBJECT):
                continue
            if obj.permissions & Permission.IMMUTABLE:
                report.fail(
                    "engine_write_paths",
                    f"operator {oid}: output view {view_id} writes into IMMUTABLE "
                    f"object {view.primary_object_id}",
                )
            if not obj.permissions & Permission.WRITE:
                report.fail(
                    "engine_write_paths",
                    f"operator {oid}: output view {view_id} writes into object "
                    f"{view.primary_object_id}, which has no WRITE permission",
                )
            if obj.payload.get("storage_class") == int(StorageClass.ROM):
                report.fail(
                    "engine_write_paths",
                    f"operator {oid}: output view {view_id} writes into ROM object "
                    f"{view.primary_object_id}",
                )
    report.checks.setdefault("engine_write_paths", True)


def check_entrypoints(
    deployment: Deployment,
    header: ProgramHeader,
    instructions: list[Any],
    report: Report,
) -> list[dict[str, int]]:
    table = deployment.table
    descriptor = resolve(
        table,
        header.entrypoint_table_descriptor,
        int(ExtendedDescriptorType.ENTRYPOINT_TABLE),
        "entrypoint table",
        report,
    )
    if descriptor is None or descriptor.raw_payload is None:
        return []
    try:
        entries = decode_entrypoint_table(descriptor.raw_payload)
    except ValueError as exc:
        report.fail("entrypoints", f"entrypoint table does not decode: {exc}")
        return []
    report.check(
        "entrypoint_count",
        len(entries) == header.entrypoint_count,
        f"entrypoint table holds {len(entries)} entries, the header declares "
        f"{header.entrypoint_count}",
    )
    manifest_entries = [dict(entry) for entry in deployment.entrypoints]
    report.check(
        "entrypoints_authenticated",
        manifest_entries == entries,
        "the manifest's entrypoints do not match the authenticated "
        "ENTRYPOINT_TABLE descriptor",
    )
    seen: set[int] = set()
    for entry in entries:
        eid = entry["entrypoint_id"]
        if eid in seen:
            report.fail("entrypoints", f"entrypoint {eid} is declared twice")
        seen.add(eid)
        first = entry["first_instruction"]
        if not 0 <= first < len(instructions):
            report.fail(
                "entrypoints",
                f"entrypoint {eid}: first instruction {first} is outside the body",
            )
        if entry["phase"] not in (0, 1):
            report.fail("entrypoints", f"entrypoint {eid}: unknown phase {entry['phase']}")
        if entry["generation_policy_id"] != NO_ID:
            resolve(
                table,
                entry["generation_policy_id"],
                int(ExtendedDescriptorType.GENERATION_POLICY),
                f"entrypoint {eid} policy",
                report,
            )
    report.checks.setdefault("entrypoints", True)
    return entries


def check_selection(
    deployment: Deployment,
    entries: list[dict[str, int]],
    instructions: list[Any],
    capability: Capability,
    report: Report,
) -> None:
    """On-device selection is mandatory for any generative entrypoint."""
    generative = [
        entry for entry in entries if entry["generation_policy_id"] != NO_ID
    ]
    if not generative:
        report.checks.setdefault("on_device_selection", True)
        return
    has = {
        int(sub): any(
            int(i.major) == int(Major.SELECTION) and i.sub == int(sub)
            for i in instructions
        )
        for sub in (Selection.ARGMAX, Selection.TOKEN_APPEND)
    }
    report.check(
        "on_device_selection",
        has[int(Selection.ARGMAX)],
        "a generative entrypoint exists but no SELECTION.ARGMAX instruction does "
        "the selection on the device",
    )
    report.check(
        "token_append_present",
        has[int(Selection.TOKEN_APPEND)],
        "a generative entrypoint exists but the program never appends a token",
    )
    report.check(
        "selection_feature_bit",
        int(Feature.ON_DEVICE_SELECTION) in set(capability.features),
        "a generative deployment needs capability feature bit 7",
    )
    for entry in generative:
        policy = deployment.table[entry["generation_policy_id"]]
        vocabulary = policy.payload["vocabulary_size"]
        report.check(
            "vocabulary_bound",
            vocabulary <= capability.limits["max_vocabulary"],
            f"generation policy {policy.descriptor_id}: vocabulary {vocabulary} "
            f"exceeds the capability bound {capability.limits['max_vocabulary']}",
        )
        report.check(
            "generation_bound",
            policy.payload["max_new_tokens"] <= capability.limits["max_context_positions"],
            f"generation policy {policy.descriptor_id}: max_new_tokens exceeds the "
            "capability context bound",
        )
        count = policy.payload["eos_count"]
        if count == 0:
            report.note(
                f"generation policy {policy.descriptor_id} declares no EOS token; "
                "only the length bound can stop generation"
            )
        for slot in range(count, 8):
            if policy.payload[f"eos_token_{slot}"] != NO_ID:
                report.fail(
                    "generation_policy",
                    f"generation policy {policy.descriptor_id}: EOS slot {slot} is "
                    "set beyond the declared count",
                )
    report.checks.setdefault("generation_policy", True)


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------
def histogram(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def check(root: Path, capability: Capability) -> dict[str, Any]:
    report = Report()
    body: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "deployment_root": root.name,
        "capability_digest": capability.digest,
    }
    deployment = load_deployment(root, report)
    if deployment is None:
        body.update(
            {
                "admitted": False,
                "checks": dict(sorted(report.checks.items())),
                "errors": report.errors,
                "warnings": report.warnings,
            }
        )
        return body

    header = ProgramHeader.decode(deployment.program[:PROGRAM_HEADER_BYTES])
    instructions = decode_body(deployment.program[PROGRAM_HEADER_BYTES:])

    check_versions(header, report)
    check_manifest_binding(deployment, header, report)
    check_capability(deployment, header, capability, report)
    events = check_instructions(deployment, instructions, report)
    flow = check_control_flow(deployment, header, instructions, capability, report)
    signalled = events["signalled"]
    event_count = check_events(deployment, signalled, capability, report)
    check_wait_ordering(deployment, instructions, signalled, report)
    state_resources = check_state(deployment, instructions, report)
    check_objects(deployment, report)
    check_views(deployment, capability, flow["trips"], report)
    check_operator_write_paths(deployment, report)
    entries = check_entrypoints(deployment, header, instructions, report)
    check_selection(deployment, entries, instructions, capability, report)

    body.update(
        {
            "admitted": report.admitted,
            "identity": {
                "backend": deployment.backend,
                "deployment_id": deployment.deployment_id,
                "generation": deployment.generation,
                "model_id": deployment.model_id,
                "target_id": deployment.target_id,
                "topology_class": int(deployment.topology_class),
            },
            "digests": {
                "deployment_sha256": deployment.deployment_digest.hex(),
                "descriptor_table_sha256": deployment.table.digest.hex(),
                "program_body_sha256": header.body_digest.hex(),
                "program_sha256": sha256_hex(deployment.program),
                "topology_sha256": header.topology_digest.hex(),
            },
            "program": {
                "declared_retired_work": header.max_retired_work,
                "descriptor_count": len(deployment.table),
                "entrypoint_count": header.entrypoint_count,
                "event_count": event_count,
                "instruction_count": header.instruction_count,
                "loop_depth": flow["depth"],
                "proved_retired_work": flow["work"],
                "required_features": sorted(feature_bits(header.required_features)),
                "state_resources": state_resources,
                "watchdog_class": header.watchdog_class,
            },
            "descriptors": histogram(
                ExtendedDescriptorType(d.descriptor_type).name
                for d in deployment.table.descriptors()
            ),
            "opcodes": histogram(i.mnemonic for i in instructions),
            "entrypoints": [dict(sorted(entry.items())) for entry in entries],
            "checks": dict(sorted(report.checks.items())),
            "errors": report.errors,
            "warnings": report.warnings,
        }
    )
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Independently check one ABI 3.0 deployment directory against one "
            "capability and emit a canonical JSON legality report."
        )
    )
    parser.add_argument(
        "--deployment",
        required=True,
        type=Path,
        help="directory holding deployment.json, descriptors.bin and program.bin",
    )
    parser.add_argument(
        "--capability", required=True, type=Path, help="capability JSON document"
    )
    parser.add_argument(
        "--output", type=Path, help="write the report here instead of stdout"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="suppress the report on stdout"
    )
    args = parser.parse_args(argv)

    try:
        capability = load_capability(args.capability)
    except (OSError, ValueError, KeyError) as exc:
        print(f"capability is unusable: {exc}", file=sys.stderr)
        return 2
    try:
        body = check(args.deployment, capability)
    except Exception as exc:  # a decoder that raises is still a rejection
        body = {
            "schema": REPORT_SCHEMA,
            "deployment_root": args.deployment.name,
            "admitted": False,
            "checks": {},
            "errors": [f"{type(exc).__name__}: {exc}"],
            "warnings": [],
        }
    blob = canonical_json(body)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(blob)
    if not args.quiet:
        sys.stdout.write(blob.decode("ascii"))
    return 0 if body["admitted"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
