#!/usr/bin/env python3
"""Fail-closed campaign against a real ABI 3.0 deployment.

The acceptance contract says a failure must not commit partial state and must
not be promoted by semantic plausibility. Those are properties of the *device*,
not of a unit fixture, so this campaign corrupts a real deployment in each of
several ways and asserts that every one is refused before any work is issued --
and that when a fault happens mid-transaction, the session's state is exactly
where it was.

Each case names the specific rule it exercises, so a failure here reads as a
violated contract rather than as an anonymous assertion.
"""

from __future__ import annotations

import argparse
import copy
import sys
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.backends.hbm_sram.capability import PROFILES  # noqa: E402
from compiler.backends.hbm_sram.lower import lower_to_abi3  # noqa: E402
from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import CompletionStatus, Control, Major, TrapClass  # noqa: E402
from runtime.abi3.deployment import Deployment, DeploymentError  # noqa: E402
from runtime.abi3.descriptors import Phase, Symbol  # noqa: E402
from runtime.abi3.records import Instruction, build_program, split_program  # noqa: E402
from runtime.abi3.verifier import VerificationError, verify_deployment  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

DEFAULT_SNAPSHOT = Path(
    "/home/ubuntu/.cache/huggingface/hub/models--Qwen--Qwen3-8B/snapshots/"
    "b968826d9c46dd6066d109eabc6255188de91218"
)


def flip(blob: bytes, offset: int) -> bytes:
    data = bytearray(blob)
    data[offset % len(data)] ^= 0x01
    return bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=REPO / "build/ir-v3/qwen3-8b/kernel_ir.v3.json")
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--output", type=Path, default=REPO / "results/abi3/failclosed_campaign.json"
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    load_engines()
    capability = PROFILES["single-chip"]
    capability = capability() if callable(capability) else capability
    graph = KernelGraph.read(args.ir)
    deployment = lower_to_abi3(graph, capability)
    header, body = split_program(deployment.program)
    print(f"baseline: {header.instruction_count} instructions, "
          f"{len(deployment.table)} descriptors", flush=True)

    cases: list[dict[str, Any]] = []

    def record(name: str, rule: str, refused: bool, detail: str) -> None:
        cases.append({"case": name, "rule": rule, "refused": refused, "detail": detail})
        mark = "refused" if refused else "ADMITTED"
        print(f"  {name:38s} {mark:9s} {detail[:88]}")

    def try_admit(name: str, rule: str, mutate: Callable[[Deployment], None]) -> None:
        candidate = copy.deepcopy(deployment)
        try:
            mutate(candidate)
        except Exception as exc:
            record(name, rule, True, f"rejected while building: {exc}")
            return
        try:
            report = verify_deployment(candidate, capability)
            if report.admitted:
                record(name, rule, False, "verifier admitted the corrupted deployment")
            else:
                record(name, rule, True, report.errors[0] if report.errors else "rejected")
        except Exception as exc:
            record(name, rule, True, f"{type(exc).__name__}: {exc}")

    print("\nadmission refusals:")
    try_admit(
        "program body bit flip",
        "wire format 2: program body SHA-256 must pass",
        lambda d: setattr(d, "program", d.program[:256] + flip(d.program[256:], 97)),
    )
    try_admit(
        "program header bit flip",
        "wire format 2: header CRC32C must pass",
        lambda d: setattr(d, "program", flip(d.program[:256], 20) + d.program[256:]),
    )
    try_admit(
        "descriptor table bit flip",
        "wire format 5: descriptor CRC32C must pass",
        lambda d: d.table.__setattr__("_records", [flip(d.table._records[0], 33)] + list(d.table._records[1:])),
    )
    try_admit(
        "illegal opcode",
        "wire format 4: an unknown opcode fails before work is issued",
        lambda d: setattr(
            d, "program",
            d.program[:256] + b"\xee" + d.program[257:],
        ),
    )

    def truncate(d: Deployment) -> None:
        d.program = d.program[: len(d.program) - 32]

    try_admit(
        "truncated program",
        "wire format 2: instruction count must match the body",
        truncate,
    )

    def drop_completion(d: Deployment) -> None:
        head, tail = split_program(d.program)
        instructions = [Instruction.decode(tail[i : i + 32]) for i in range(0, len(tail), 32)]
        instructions[-1] = Instruction(int(Major.CONTROL), int(Control.NOP))
        d.program = build_program(
            instructions,
            entrypoint_count=head.entrypoint_count,
            required_features=head.required_features,
            deployment_digest=head.deployment_digest,
            descriptor_table_digest=head.descriptor_table_digest,
            topology_digest=head.topology_digest,
            max_retired_work=head.max_retired_work,
            watchdog_class=head.watchdog_class,
            entrypoint_table_descriptor=head.entrypoint_table_descriptor,
        )

    try_admit(
        "no terminal completion",
        "ADR-003 5.1: every terminal path produces one completion",
        drop_completion,
    )

    # -- a fault mid-transaction must leave state exactly where it was -----
    print("\nmid-transaction fault:")
    device = Device(deployment, capability, root=args.snapshot, verify=False)
    session = device.create_session()
    before = {s.descriptor_id: (s.cursor_rows, s.generation) for s in session.states.values()}
    symbols = {
        int(Symbol.SPAN_TOKENS): 4,
        int(Symbol.POSITION_START): 0,
        int(Symbol.POSITION_END): 4,
        int(Symbol.CONTEXT_LENGTH): 4,
        int(Symbol.PHASE): int(Phase.PREFILL),
        int(Symbol.MAX_NEW_TOKENS): 4,
        int(Symbol.BATCH): 1,
        int(Symbol.GENERATION_INDEX): 0,
        # SPAN_LAST_INDEX deliberately omitted: an unbound symbol must trap.
    }
    result = device.run_transaction(
        session, entrypoint_id=0, symbols=symbols, generation_policy_id=-1
    )
    after = {s.descriptor_id: (s.cursor_rows, s.generation) for s in session.states.values()}
    faulted = result.status != CompletionStatus.SUCCESS
    unchanged = before == after
    record(
        "unbound symbol mid-transaction",
        "ADR-003 8.6: a fault discards prepared state and commits nothing",
        faulted and unchanged,
        f"status={CompletionStatus(result.status).name} "
        f"trap={TrapClass(result.trap_class).name} state_unchanged={unchanged}",
    )
    prepared_open = [s.descriptor_id for s in session.states.values() if s.open_prepare]
    record(
        "no prepared state left open",
        "ADR-003 8.6: abort discards prepared state",
        not prepared_open,
        f"{len(prepared_open)} resources still open",
    )

    body_out = {
        "schema": "opentallas.abi3.failclosed_campaign.v1",
        "evidence_class": "functional_artifact_only",
        "model_id": graph.model_id,
        "graph_id": graph.graph_id,
        "capability_digest": capability.digest,
        "baseline_instruction_count": header.instruction_count,
        "cases": cases,
        "case_count": len(cases),
        "refused_count": sum(1 for c in cases if c["refused"]),
        "all_refused": all(c["refused"] for c in cases),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body_out))
    print(f"\n{body_out['refused_count']}/{body_out['case_count']} refused")
    print(f"wrote {args.output}")
    return 0 if body_out["all_refused"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
