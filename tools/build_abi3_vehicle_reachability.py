#!/usr/bin/env python3
"""Derive which operator families the integrated vehicle can reach, and at what cost.

The integrated shipped-prefix vehicle (``rtl/test/a3_shipped_prefix_top.sv``)
runs one transaction per case, entering the deployed program at a per-case
``cfg_entry_pc`` and bounded above by ``cfg_instruction_count``.  Six operator
families the governed Qwen decode issues -- ``VECTOR.ADD``,
``VECTOR.SILU_MUL``, ``DMA.SCATTER``, ``ATTENTION.GQA``, ``SELECTION.ARGMAX``
and ``SELECTION.TOKEN_APPEND`` -- sit past the vehicle's present fail-closed
boundary at PC 32, and the standing plan proposed reaching each of them with
"one case per family entering at that family's own PC with its operands
preloaded".

That shape is not free to choose, and this tool says so from the program
rather than from an opinion.  ABI 3.0 events are transaction-scoped: the
event scoreboard (``rtl/abi3/ot_a3_event_scoreboard.sv``) treats a wait-set
producer that is *neither pending nor signalled* as "never issued" and traps
``A3_TRAP_INTERNAL`` (13) before the instruction dispatches.  An entry PC that
skips a family's producers therefore cannot execute that family at all.  The
reachable entry is the earliest PC from which straight-line execution signals
the family's whole transitive producer closure without stepping on a
``CONTROL.LOOP_NEXT`` whose ``LOOP_SETUP`` it skipped -- and the cost of the
case is every MATMUL that lies between them.

Everything below is derived from the deployment's own program body, its own
descriptor table and its own bound request symbols:

* the PCs that issue each family, from the decoded instruction stream;
* each instruction's wait set and its producers, from the ``EVENT_WAIT_SET``
  descriptors, and each instruction's signalled event from the instruction;
* loop trip counts, from the ``LOOP_CONTROL`` descriptors and the request's
  own symbol bindings, by the same rule the vector builder applies;
* the MAC cost of every ``TENSOR.MATMUL`` on the path, from the resolved
  weight view's own dimensions -- never from a table typed here.

The derivation is then executed as a small abstract machine with exactly the
transitions the RTL has: fetch bound (``pc >= instruction_count`` ->
``A3_TRAP_ILLEGAL``), loop stack (``LOOP_NEXT`` on an empty stack or naming a
loop that is not on top -> ``A3_TRAP_ILLEGAL``), and wait sets
(unsignalled producer -> ``A3_TRAP_INTERNAL``).  ``--probe-plan`` emits the
(entry, instruction_count) pairs for the RTL entry probe, so the prediction
this tool derives is checked against the sequencer's own verdict rather than
believed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Major, Control, Tensor  # noqa: E402
from runtime.abi3.constants import InstructionFlag  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from tools.build_abi3_shipped_prefix_vectors import (  # noqa: E402
    TARGETS,
    _deployment_vectors,
    _loop_trip,
    _resolved_views,
)

SCHEMA = "opentallas.rtl.abi3_vehicle_reachability.v1"
NO_ID = 0xFFFF_FFFF
DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_vehicle_reachability.json"

# The six families rtl/abi3/ot_a3_engine_issue_bridge.sv admits by mapped
# placement, named by (major, sub) so the match is against the program's own
# opcode bytes rather than against a printed string.
MAPPED_FAMILIES: tuple[tuple[str, int, int], ...] = (
    ("VECTOR.ADD", 0x30, 0x03),
    ("VECTOR.SILU_MUL", 0x30, 0x04),
    ("DMA.SCATTER", 0x10, 0x03),
    ("ATTENTION.GQA", 0x40, 0x01),
    ("SELECTION.ARGMAX", 0x70, 0x00),
    ("SELECTION.TOKEN_APPEND", 0x70, 0x01),
)

TRAP_ILLEGAL = 5
TRAP_INTERNAL = 13


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Program:
    """One deployment's decoded body, with every field this tool reads derived."""

    def __init__(self, target: Any, symbols: dict[int, int]) -> None:
        self.target = target
        self.deployment = Deployment.read(ROOT / target.deployment)
        _, body = split_program(self.deployment.program)
        self.instructions = decode_body(body)
        self.symbols = symbols
        self.table = self.deployment.table
        self.entry_pc = int(
            next(
                item
                for item in self.deployment.entrypoints
                if int(item["entrypoint_id"]) == 1
            )["first_instruction"]
        )
        self.waits: dict[int, list[int]] = {}
        self.signals: dict[int, int] = {}
        self.loop_trip: dict[int, int] = {}
        self.loop_start: dict[int, int] = {}
        for pc, instruction in enumerate(self.instructions):
            wait_id = int(instruction.wait_set_id)
            if wait_id != NO_ID:
                payload = self.table.get(
                    wait_id, ExtendedDescriptorType.EVENT_WAIT_SET
                ).payload
                count = int(payload["producer_count"])
                self.waits[pc] = [
                    int(payload[f"producer_{index}"]) for index in range(count)
                ]
            event = int(instruction.signal_event_id)
            if event != NO_ID:
                self.signals[pc] = event
            if int(instruction.major) == int(Major.CONTROL) and int(
                instruction.sub
            ) == int(Control.LOOP_SETUP):
                loop_id = int(instruction.control_id)
                payload = self.table.get(
                    loop_id, ExtendedDescriptorType.LOOP_CONTROL
                ).payload
                self.loop_trip[pc] = _loop_trip(payload, symbols)
                self.loop_start[pc] = int(payload["body_start"])

    def loop_trip_ids_covering(self, pc: int) -> list[int]:
        """The loop ids whose declared body contains ``pc``.

        Taken from each LOOP_CONTROL descriptor's own ``body_start`` and
        ``body_end``, so a view that names a loop induction variable resolves
        in the loop nest the program actually puts it in.
        """
        out: list[int] = []
        for setup_pc, start in self.loop_start.items():
            loop_id = int(self.instructions[setup_pc].control_id)
            payload = self.table.get(
                loop_id, ExtendedDescriptorType.LOOP_CONTROL
            ).payload
            if start <= pc <= int(payload["body_end"]):
                out.append(loop_id)
        return out

    def macs(self, pc: int, loops: dict[int, int]) -> int:
        """The MAC count of the MATMUL at ``pc``, from its own resolved views.

        Not a table: the weight view's resolved dimensions are the reduction
        and the output width, which is the same product the shipped-prefix
        vector builder derives for the three MATMULs it already executes.
        """
        instruction = self.instructions[pc]
        if int(instruction.major) != int(Major.TENSOR) or int(
            instruction.sub
        ) != int(Tensor.MATMUL):
            return 0
        views = _resolved_views(
            self.deployment,
            int(instruction.descriptor_id),
            loops,
            self.symbols,
            major=int(instruction.major),
        )
        by_slot = {int(view["slot"]): view for view in views}
        weight = by_slot.get(1)
        if weight is None or len(weight["dims"]) != 2:
            raise SystemExit(
                f"{self.target.key}: MATMUL at PC {pc} has no rank-2 weight view"
            )
        return int(weight["dims"][0]) * int(weight["dims"][1])


def simulate(program: Program, entry: int, instruction_count: int) -> dict[str, Any]:
    """Execute the abstract machine the microsequencer is, from ``entry``.

    Transitions are exactly the RTL's, and each one is a refusal the RTL can
    actually produce: the fetch bound, the loop stack, and the wait set.
    """
    pc = entry
    signalled: set[int] = set()
    stack: list[tuple[int, int, int]] = []  # (loop pc, remaining trips, body start)
    macs = 0
    issued: list[dict[str, Any]] = []
    fetched = 0
    guard = 0
    guard_limit = 1_000_000
    while True:
        guard += 1
        if guard > guard_limit:
            raise SystemExit(f"{program.target.key}: abstract run did not terminate")
        if pc >= instruction_count or pc >= len(program.instructions):
            return {
                "outcome": "trap",
                "trap_class": TRAP_ILLEGAL,
                "trap_pc": pc,
                "reason": "fetch left the authorised instruction bound",
                "macs": macs,
                "issued": issued,
                "fetched": fetched,
            }
        fetched += 1
        instruction = program.instructions[pc]
        major = int(instruction.major)
        sub = int(instruction.sub)
        # Predication is a runtime read of device memory, not a property of
        # the program text.  This machine does not model it, and says so
        # rather than guessing a branch: a path through a PREDICATED
        # instruction is underivable here, and the site it guards is reported
        # as underived rather than as reachable or unreachable.
        if int(instruction.flags) & int(InstructionFlag.PREDICATED):
            return {
                "outcome": "underivable",
                "trap_class": None,
                "trap_pc": pc,
                "reason": (
                    f"PC {pc} is PREDICATED; its predicate is a device-memory "
                    "read this derivation does not model"
                ),
                "macs": macs,
                "issued": issued,
                "fetched": fetched,
            }
        # The wait set is evaluated for EVERY instruction, CONTROL included:
        # the microsequencer runs S_WAIT_REQ between decode and dispatch and
        # does not special-case the family.  CONTROL.FENCE at the head of the
        # Qwen selection tail carries a wait set, and skipping it here would
        # have reported SELECTION.TOKEN_APPEND reachable when it is not.
        producers = program.waits.get(pc, [])
        missing = [event for event in producers if event not in signalled]
        if missing:
            return {
                "outcome": "trap",
                "trap_class": TRAP_INTERNAL,
                "trap_pc": pc,
                "reason": (
                    "wait set names producer event(s) "
                    f"{missing} that this transaction never issued"
                ),
                "macs": macs,
                "issued": issued,
                "fetched": fetched,
            }
        if major == int(Major.CONTROL):
            if sub == int(Control.LOOP_SETUP):
                stack.append(
                    (pc, program.loop_trip[pc] - 1, program.loop_start[pc])
                )
                if pc in program.signals:
                    signalled.add(program.signals[pc])
                pc += 1
                continue
            if sub == int(Control.LOOP_NEXT):
                loop_id = int(instruction.control_id)
                if not stack or int(
                    program.instructions[stack[-1][0]].control_id
                ) != loop_id:
                    return {
                        "outcome": "trap",
                        "trap_class": TRAP_ILLEGAL,
                        "trap_pc": pc,
                        "reason": (
                            "CONTROL.LOOP_NEXT for a loop this transaction never "
                            "set up: the loop stack is empty or names another loop"
                        ),
                        "macs": macs,
                        "issued": issued,
                        "fetched": fetched,
                    }
                setup_pc, remaining, body_start = stack[-1]
                if pc in program.signals:
                    signalled.add(program.signals[pc])
                if remaining > 0:
                    stack[-1] = (setup_pc, remaining - 1, body_start)
                    pc = body_start
                else:
                    stack.pop()
                    pc += 1
                continue
            # every other CONTROL form retires in place for this machine
            if pc in program.signals:
                signalled.add(program.signals[pc])
            if sub == int(Control.COMPLETE):
                return {
                    "outcome": "complete",
                    "trap_class": 0,
                    "trap_pc": pc,
                    "reason": "CONTROL.COMPLETE",
                    "macs": macs,
                    "issued": issued,
                    "fetched": fetched,
                }
            pc += 1
            continue
        loops = {
            int(program.instructions[setup_pc].control_id): 0 for setup_pc, _, _ in stack
        }
        macs += program.macs(pc, loops)
        issued.append({"pc": pc, "major": major, "sub": sub})
        if pc in program.signals:
            signalled.add(program.signals[pc])
        pc += 1


def family_report(program: Program) -> list[dict[str, Any]]:
    """Per family: where it is issued, the cheapest entry that reaches it, why."""

    candidate_entries = sorted(
        {0, program.entry_pc}
        | {
            pc
            for pc, instruction in enumerate(program.instructions)
            if int(instruction.major) == int(Major.CONTROL)
            and int(instruction.sub) == int(Control.LOOP_SETUP)
        }
        | {
            pc
            for pc, instruction in enumerate(program.instructions)
            if int(instruction.major) != int(Major.CONTROL)
        }
    )
    out: list[dict[str, Any]] = []
    for name, major, sub in MAPPED_FAMILIES:
        sites = [
            pc
            for pc, instruction in enumerate(program.instructions)
            if int(instruction.major) == major and int(instruction.sub) == sub
        ]
        entry_records: list[dict[str, Any]] = []
        for site in sites:
            best: dict[str, Any] | None = None
            blocked: dict[str, Any] | None = None
            underivable: str | None = None
            for entry in candidate_entries:
                if entry > site:
                    continue
                run = simulate(program, entry, site + 1)
                if run["outcome"] == "underivable":
                    if underivable is None:
                        underivable = run["reason"]
                    continue
                reached = any(record["pc"] == site for record in run["issued"])
                if reached:
                    record = {
                        "entry_pc": entry,
                        "instruction_count": site + 1,
                        "macs": run["macs"],
                        "issued_operations": len(run["issued"]),
                        "terminal_trap_class": TRAP_ILLEGAL,
                        "terminal_pc": site + 1,
                    }
                    if best is None or record["macs"] < best["macs"]:
                        best = record
                if not reached and (blocked is None or entry > blocked["entry_pc"]):
                    blocked = {
                        "entry_pc": entry,
                        "trap_class": run["trap_class"],
                        "trap_pc": run["trap_pc"],
                        "reason": run["reason"],
                        "macs": run["macs"],
                    }
            # The shape the standing plan proposed, evaluated exactly as
            # proposed: enter the transaction at the family's own PC.
            own = simulate(program, site, site + 1)
            own_reached = any(record["pc"] == site for record in own["issued"])
            own_derivable = own["outcome"] != "underivable"
            entry_records.append(
                {
                    "pc": site,
                    "descriptor_id": int(program.instructions[site].descriptor_id),
                    "derivable": own_derivable and underivable is None,
                    "underivable_reason": (
                        own["reason"] if not own_derivable else underivable
                    ),
                    "reachable": best is not None,
                    "cheapest_entry": best,
                    "nearest_refusal": blocked,
                    "own_pc_entry": {
                        "entry_pc": site,
                        "instruction_count": site + 1,
                        "derivable": own_derivable,
                        "dispatches_the_site": own_reached,
                        "trap_class": own["trap_class"],
                        "trap_pc": own["trap_pc"],
                        "reason": own["reason"],
                        "macs": own["macs"],
                    },
                }
            )
        reachable_sites = [record for record in entry_records if record["reachable"]]
        out.append(
            {
                "family": name,
                "opcode": {"major": major, "sub": sub},
                "issue_sites": entry_records,
                "reachable": bool(reachable_sites),
                "min_macs": (
                    min(record["cheapest_entry"]["macs"] for record in reachable_sites)
                    if reachable_sites
                    else None
                ),
            }
        )
    return out


KV_ROW_WORDS = 1024


def workload_context_rows() -> dict[str, Any]:
    """The KV plane rows the governed workload actually reaches.

    Derived, never chosen: the request's own prompt length plus the number of
    tokens the reference oracle generates for TA-QW-EOS-1.  The deployment's
    GENERATION_POLICY declares ``max_new_tokens`` 8,256, which is the shipped
    machine's capacity and not this workload's reach; sizing the vehicle's
    compact bank to it would be a 67 MB bank for 19 rows of traffic.
    """

    oracle_path = ROOT / "results/abi3/qwen3_reference_oracle_eos.json"
    if not oracle_path.is_file():
        raise SystemExit(f"missing the workload oracle: {oracle_path}")
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    result = oracle["results"]["TA-QW-EOS-1"]
    prompt = int(result["prompt_token_count"])
    generated = len(result["generated_token_ids"])
    if generated != int(result["generated_token_count"]):
        raise SystemExit("the oracle's token count disagrees with its own list")
    return {
        "prompt_token_count": prompt,
        "generated_token_count": generated,
        "kv_plane_rows": prompt + generated,
        "source": "results/abi3/qwen3_reference_oracle_eos.json",
    }


def bank_demand(
    program: Program, families: list[dict[str, Any]], kv_plane_rows: int
) -> dict[str, Any]:
    """What the mapped families demand of the vehicle's operand banks.

    Every object a mapped family's views name is sized from the resolved view
    itself.  The one object that is not taken at its declared size is the KV
    cache: the bridge requires it as one compact bank of
    ``2 * kv_plane_rows * 1024`` words with the V plane a fixed
    ``kv_plane_rows * 1024`` above the K plane, and the declared object is
    8,256 rows of shipped capacity rather than this workload's reach.  A view
    whose object cannot be resolved is reported as unresolved, not skipped.
    """

    objects: dict[int, dict[str, Any]] = {}
    unresolved: list[dict[str, Any]] = []
    for family in families:
        for site in family["issue_sites"]:
            if not site["derivable"]:
                continue
            pc = site["pc"]
            instruction = program.instructions[pc]
            loops = {
                loop_id: 0
                for loop_id in program.loop_trip_ids_covering(pc)
            }
            try:
                views = _resolved_views(
                    program.deployment,
                    int(instruction.descriptor_id),
                    loops,
                    program.symbols,
                    major=int(instruction.major),
                )
            except Exception as error:  # resolution is the measurement here
                unresolved.append(
                    {"pc": pc, "family": family["family"], "why": str(error)}
                )
                continue
            for view in views:
                words = 1
                for dim in view["dims"]:
                    words *= int(dim)
                is_kv = (
                    len(view["dims"]) == 3
                    and int(view["strides"][0]) == 2 * KV_ROW_WORDS
                    and int(view["element_offset"]) in (0, KV_ROW_WORDS)
                )
                # Only the scatter's and the attention's own INDEX operand
                # lives in the index bank: the bridge reads it with
                # m0_reads_result low, so base + resolved offset must be below
                # INDEX_WORDS.  A U32 scalar that is some other family's
                # operand or any family's OUTPUT is a plane of the result
                # bank -- the selected token id is written by the device, not
                # supplied to it, and putting it in the index bank would size
                # the wrong memory.
                entry = objects.setdefault(
                    int(view["object_id"]),
                    {
                        "object_id": int(view["object_id"]),
                        "declared_words": words,
                        "is_index_view": (
                            view["dtype"] == 4
                            and view["dims"] == [1]
                            and int(view["slot"]) < 4
                            and family["family"]
                            in ("DMA.SCATTER", "ATTENTION.GQA")
                        ),
                        "is_kv_cache": is_kv,
                        "named_by": [],
                    },
                )
                entry["declared_words"] = max(entry["declared_words"], words)
                entry["is_kv_cache"] = entry["is_kv_cache"] or is_kv
                entry["is_index_view"] = entry["is_index_view"] and (
                    view["dtype"] == 4
                    and view["dims"] == [1]
                    and int(view["slot"]) < 4
                    and family["family"] in ("DMA.SCATTER", "ATTENTION.GQA")
                )
                entry["named_by"].append({"family": family["family"], "pc": pc})
    for entry in objects.values():
        entry["vehicle_words"] = (
            2 * kv_plane_rows * KV_ROW_WORDS
            if entry["is_kv_cache"]
            else entry["declared_words"]
        )
        entry["bank"] = (
            "index"
            if entry["is_index_view"]
            else ("result_kv_bank" if entry["is_kv_cache"] else "result")
        )
    result_words = sum(
        entry["vehicle_words"]
        for entry in objects.values()
        if entry["bank"] != "index"
    )
    index_words = sum(
        entry["vehicle_words"]
        for entry in objects.values()
        if entry["bank"] == "index"
    )
    return {
        "kv_plane_rows": kv_plane_rows,
        "objects": sorted(objects.values(), key=lambda item: item["object_id"]),
        "result_bank_words_for_mapped_objects": result_words,
        "index_bank_words_for_mapped_objects": index_words,
        "unresolved_views": unresolved,
    }


def case_plan(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The transactions that would cover the mapped families, and their cost.

    Straight-line execution from one entry PC passes through every site below
    its bound, so sites sharing an entry share a transaction: the plan is one
    transaction per distinct entry PC, and inside it a cost curve -- what each
    additional bound costs and which family it buys.  Printing the curve
    rather than a single total is deliberate: for the Qwen decode the curve is
    flat for three families and then steps by two orders of magnitude for the
    last, and a single number would hide exactly the fact that decides the
    plan.
    """

    by_entry: dict[int, list[dict[str, Any]]] = {}
    for family in families:
        for site in family["issue_sites"]:
            if not (site["reachable"] and site["derivable"]):
                continue
            best = site["cheapest_entry"]
            by_entry.setdefault(best["entry_pc"], []).append(
                {
                    "family": family["family"],
                    "site_pc": site["pc"],
                    "instruction_count": best["instruction_count"],
                    "macs": best["macs"],
                }
            )
    plan = []
    for entry_pc in sorted(by_entry):
        steps = sorted(by_entry[entry_pc], key=lambda item: item["macs"])
        curve = []
        previous = 0
        for step in steps:
            curve.append(
                {
                    "family": step["family"],
                    "site_pc": step["site_pc"],
                    "instruction_count": step["instruction_count"],
                    "cumulative_macs": step["macs"],
                    "marginal_macs": step["macs"] - previous,
                }
            )
            previous = step["macs"]
        plan.append(
            {
                "entry_pc": entry_pc,
                "covers": [step["family"] for step in steps],
                "cost_curve": curve,
                "full_coverage_instruction_count": steps[-1]["instruction_count"],
                "full_coverage_macs": steps[-1]["macs"],
            }
        )
    return plan


def positive_control(program: Program) -> dict[str, Any] | None:
    """A mid-program entry that DOES dispatch, so the refusal is attributable.

    Without one, "entering at the family's own PC refuses" could be read as
    "this vehicle refuses any entry but the entrypoint".  The control is
    derived, not chosen: the LAST engine instruction that carries no wait set
    at all, entered at the LOOP_SETUP that opens its body -- deepest into the
    program, and strictly past the deployed entrypoint, so it is a mid-program
    entry and not the entrypoint wearing another name.  If the program has no
    such instruction this returns None and the campaign says the control is
    absent rather than inventing one.
    """
    for pc in range(len(program.instructions) - 1, -1, -1):
        instruction = program.instructions[pc]
        if int(instruction.major) == int(Major.CONTROL):
            continue
        if program.waits.get(pc):
            continue
        entry = pc
        if pc > 0:
            previous = program.instructions[pc - 1]
            if int(previous.major) == int(Major.CONTROL) and int(
                previous.sub
            ) == int(Control.LOOP_SETUP):
                entry = pc - 1
        if entry <= program.entry_pc:
            continue
        run = simulate(program, entry, pc + 1)
        if run["outcome"] == "underivable":
            continue
        if any(record["pc"] == pc for record in run["issued"]):
            return {
                "site_pc": pc,
                "entry_pc": entry,
                "instruction_count": pc + 1,
                "predicted_dispatches_the_site": True,
                "predicted_trap_class": TRAP_ILLEGAL,
                "predicted_trap_pc": pc + 1,
                "predicted_macs": run["macs"],
            }
    return None


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--probe-plan",
        type=Path,
        default=None,
        help="write the (entry_pc, instruction_count) probe plan the RTL "
        "entry probe replays, so the derivation is checked, not believed",
    )
    args = parser.parse_args(argv)

    deployment_vectors, _ = _deployment_vectors()
    cases = {case["name"]: case for case in deployment_vectors["cases"]}

    targets: list[dict[str, Any]] = []
    probe_plan: list[dict[str, Any]] = []
    for target in TARGETS:
        case = cases.get(f"{target.key}/decode")
        if case is None:
            raise SystemExit(f"no shipped decode case for {target.key}")
        symbols = {int(key): int(value) for key, value in case["symbols"].items()}
        program = Program(target, symbols)
        families = family_report(program)
        control = positive_control(program)
        rows = workload_context_rows()
        demand = bank_demand(program, families, rows["kv_plane_rows"])
        # The transaction the whole program is: what it costs to run the
        # decode step straight through, which is what SELECTION.TOKEN_APPEND
        # needs and which is the run G1 declares out of scope.
        whole = simulate(program, program.entry_pc, len(program.instructions))
        # The bundle this derivation actually read, against the one the
        # shipped deployment vector set certifies.  The checkout is shared,
        # and a bundle that has moved under the vector set is a derivation
        # about a program no vector set binds -- which is a fact about this
        # record, not a detail to leave to a reader to notice.
        certified = str(case.get("deployment_sha256", ""))
        observed = program.deployment.deployment_digest.hex()
        targets.append(
            {
                "target": target.key,
                "deployment": str(target.deployment),
                "deployment_sha256": observed,
                "deployment_sha256_certified_by_vector_set": certified,
                "deployment_matches_vector_set": observed == certified,
                "entry_pc": program.entry_pc,
                "instruction_count": len(program.instructions),
                "whole_program": {
                    "outcome": whole["outcome"],
                    "macs": whole["macs"],
                    "issued_operations": len(whole["issued"]),
                },
                "families": families,
                "positive_control": control,
                "workload_context": rows,
                "bank_demand": demand,
                "case_plan": case_plan(families),
            }
        )
        if control is not None:
            probe_plan.append(
                {"kind": "positive_control", "target": target.key,
                 "family": None, **control}
            )
        for family in families:
            for site in family["issue_sites"]:
                # The shape the standing plan proposed -- enter at the
                # family's own PC -- is probed for every site, and it costs
                # nothing to run because it refuses before any engine work.
                own = site["own_pc_entry"]
                if not own["derivable"]:
                    continue
                probe_plan.append(
                    {
                        "kind": "own_pc_entry",
                        "target": target.key,
                        "family": family["family"],
                        "site_pc": site["pc"],
                        "entry_pc": own["entry_pc"],
                        "instruction_count": own["instruction_count"],
                        "predicted_dispatches_the_site": own["dispatches_the_site"],
                        "predicted_trap_class": own["trap_class"],
                        "predicted_trap_pc": own["trap_pc"],
                        "predicted_macs": own["macs"],
                    }
                )
                if site["reachable"] and site["derivable"]:
                    probe_plan.append(
                        {
                            "kind": "reaching_entry",
                            "target": target.key,
                            "family": family["family"],
                            "site_pc": site["pc"],
                            "entry_pc": site["cheapest_entry"]["entry_pc"],
                            "instruction_count": site["cheapest_entry"][
                                "instruction_count"
                            ],
                            "predicted_dispatches_the_site": True,
                            "predicted_trap_class": TRAP_ILLEGAL,
                            "predicted_trap_pc": site["cheapest_entry"]["terminal_pc"],
                            "predicted_macs": site["cheapest_entry"]["macs"],
                        }
                    )

    record = {
        "schema": SCHEMA,
        "claim": (
            "which operator families the integrated shipped-prefix vehicle can "
            "reach from a single-transaction entry PC, derived from each "
            "deployment's own program, descriptors and bound symbols"
        ),
        "does_not_establish": [
            "that a reachable family produces the right words: reachability is "
            "a control-plane property and bit-exactness is gate G1a's",
            "any wall-clock cost: MAC counts are derived from the resolved "
            "weight views, and the seconds they imply depend on the measured "
            "integrated rate recorded elsewhere",
        ],
        "event_scope_rule": (
            "ABI 3.0 events are transaction-scoped and single-assignment in "
            "the program text; rtl/abi3/ot_a3_event_scoreboard.sv traps "
            "A3_TRAP_INTERNAL (13) on a wait-set producer that is neither "
            "pending nor signalled, so an entry PC that skips a family's "
            "producers cannot execute that family"
        ),
        "source_sha256": {
            path: sha256_file(ROOT / path)
            for path in (
                "rtl/abi3/ot_a3_event_scoreboard.sv",
                "rtl/abi3/ot_a3_loop_stack.sv",
                "rtl/abi3/ot_a3_microsequencer.sv",
                "rtl/test/a3_shipped_prefix_top.sv",
                "tools/build_abi3_shipped_prefix_vectors.py",
                "tools/build_abi3_vehicle_reachability.py",
            )
        },
        "targets": targets,
        "all_deployments_match_vector_set": all(
            entry["deployment_matches_vector_set"] for entry in targets
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    if args.probe_plan is not None:
        args.probe_plan.parent.mkdir(parents=True, exist_ok=True)
        args.probe_plan.write_text(
            json.dumps({"schema": SCHEMA + ".probe_plan", "probes": probe_plan},
                       indent=2, sort_keys=True)
            + "\n"
        )
    for entry in targets:
        print(f"{entry['target']}: whole program {entry['whole_program']['macs']} MACs")
        for family in entry["families"]:
            for site in family["issue_sites"]:
                if site["reachable"]:
                    best = site["cheapest_entry"]
                    print(
                        f"  {family['family']} PC {site['pc']}: reachable from "
                        f"entry {best['entry_pc']} bound {best['instruction_count']}"
                        f", {best['macs']} MACs"
                    )
                elif not site["derivable"]:
                    print(
                        f"  {family['family']} PC {site['pc']}: UNDERIVED -- "
                        f"{site['underivable_reason']}"
                    )
                elif site["nearest_refusal"] is None:
                    print(
                        f"  {family['family']} PC {site['pc']}: UNREACHABLE "
                        "from every admissible entry, and no refusal was "
                        "isolated"
                    )
                else:
                    refusal = site["nearest_refusal"]
                    print(
                        f"  {family['family']} PC {site['pc']}: UNREACHABLE; "
                        f"nearest entry {refusal['entry_pc']} traps "
                        f"{refusal['trap_class']} at PC {refusal['trap_pc']} -- "
                        f"{refusal['reason']}"
                    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
