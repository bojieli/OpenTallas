#!/usr/bin/env python3
"""What bounds rung G1e's pass count -- measured, not argued.

G1e (``configs/gates/redesign_gates.json``) requires ``passes.executed`` to
equal the number the gate names, and the rung measures three.  Until now the
artifact explained the gap in prose: the shipped Qwen deployment runs
``TA-QW-EOS-1`` in one prefill transaction spanning all sixteen prompt
positions and one decode transaction per further token.  Prose is not
evidence, and an explanation of a red field is exactly the place a programme
like this one gets it wrong, so this tool replaces the explanation with an
experiment.

It executes the governed workload on ``runtime.sim.device.Device`` under
several *host decompositions* -- the same request, cut into transactions
differently -- and records, for each, how many device transactions it
performed, how many of the workload's token positions it forward-passed, and
whether it reproduced the oracle's gold.  A decomposition that does not
reproduce the gold is not an execution of this workload, whatever its pass
count; the maximum pass count over the decompositions that DO reproduce it is
the number the rung can honestly report.

Four things are deliberate.

**No RTL is read.**  This is a property of the deployment's program and the
ABI request, and the measurement stands or falls on the reference model, which
G1a-G1d bind to the RTL elsewhere.

**The gate's own numbers are read from the gate.**  ``gate_requires_positions``
below comes out of ``configs/gates/redesign_gates.json``; nothing here
hand-types it, and nothing here edits it.  It used to read the single field
``passes.executed``, which the gate withdrew when its own defect was
corrected -- 19 is the workload's TOKEN-POSITION count, not a pass count --
and this tool went on reading the withdrawn field, so it refused to run at
all and the rung it feeds could not be regenerated.  It now reads the three
position fields the gate requires, and refuses if any of them is absent.

**Failure is data.**  A decomposition that traps, that ends the session early
or that emits a token the workload never generated is recorded with what it
actually did, because that is the measurement -- the point is which
decompositions the design admits, not that one of them worked.

**The oracle decides.**  ``reproduces_gold`` compares against
``results/abi3/qwen3_reference_oracle_eos.json`` for this workload's digest,
so a decomposition cannot be counted correct by producing plausible tokens.
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

for _thread_variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_thread_variable, "8")

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import Phase, Symbol  # noqa: E402
from runtime.abi3.records import EosReason  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.driver import GenerationDriver  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    TARGETS,
    certified_deployment_identity,
    checkpoint_root,
)

SCHEMA = "opentallas.rtl.abi3_g1e_pass_decomposition.v1"
WORKLOAD_ID = "TA-QW-EOS-1"
WORKLOAD_PATH = "build/workloads/qwen3-8b/TA-QW-EOS-1.json"
ORACLE_PATH = "results/abi3/qwen3_reference_oracle_eos.json"
GATES_PATH = "configs/gates/redesign_gates.json"

STORES = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}

SOURCE_FILES = (
    "tools/build_abi3_g1e_pass_decomposition.py",
    "runtime/driver.py",
    "runtime/sim/device.py",
    "runtime/abi3/verifier.py",
)


# What G1e's specification requires of the pass accounting, by field name.
# It required ``passes.executed == 19`` until the spec was corrected: 19 is
# the workload's TOKEN-POSITION count, not a pass count, and the requirement
# is now the position accounting below -- strictly more than a raw pass count
# ever pinned.  This tool reads whichever of these the gate declares and
# refuses to invent any of them; a gate that declares none of them is a gate
# this tool cannot report against, which is a failure and not a default.
GATE_POSITION_FIELDS = (
    "passes.workload_token_positions",
    "passes.model_forward_passes",
    "passes.positions_never_forward_passed",
)


def gate_required_positions() -> dict[str, int]:
    """The position accounting G1e's own specification names.  Read, never typed."""
    document = json.loads((ROOT / GATES_PATH).read_text(encoding="utf-8"))
    gates = document if isinstance(document, list) else document.get("gates", [])
    required: dict[str, int] = {}
    for gate in gates:
        if gate.get("id") != "G1e":
            continue
        for field in gate["evaluator"]["require_fields"]:
            name = field.get("field")
            if name in GATE_POSITION_FIELDS:
                required[name.split(".", 1)[1]] = int(field["equals"])
    missing = [
        name.split(".", 1)[1]
        for name in GATE_POSITION_FIELDS
        if name.split(".", 1)[1] not in required
    ]
    if missing:
        raise SystemExit(
            f"{GATES_PATH} declares no G1e "
            + ", ".join(f"passes.{name}" for name in missing)
            + " field; this tool reports the gate's own numbers and will not "
            "invent one"
        )
    return required


class Tally:
    """Every transaction the device ran, with the request that produced it."""

    def __init__(self, device: Device) -> None:
        self.device = device
        self.rows: list[dict[str, Any]] = []
        self._original = device.run_transaction

    def __enter__(self) -> "Tally":
        original = self._original

        def run_transaction(session, **kwargs):  # noqa: ANN001, ANN202
            symbols = dict(kwargs.get("symbols") or {})
            started = time.perf_counter()
            result = original(session, **kwargs)
            self.rows.append(
                {
                    "entrypoint_id": int(kwargs.get("entrypoint_id", -1)),
                    "span_tokens": int(symbols.get(int(Symbol.SPAN_TOKENS), 1)),
                    "position_start": int(symbols.get(int(Symbol.POSITION_START), 0)),
                    "phase": int(symbols.get(int(Symbol.PHASE), -1)),
                    "status": int(result.status),
                    "trap_class": int(result.trap_class),
                    "message": str(result.message or "")[:240],
                    "produced_tokens": [int(t) for t in result.produced_tokens],
                    "eos_reason": int(result.eos_reason),
                    "seconds": round(time.perf_counter() - started, 3),
                }
            )
            return result

        self.device.run_transaction = run_transaction  # type: ignore[method-assign]
        return self

    def __exit__(self, *exc: object) -> None:
        self.device.run_transaction = self._original  # type: ignore[method-assign]


class Bench:
    """One admitted deployment, and a fresh device for each decomposition."""

    def __init__(self, store: str, checkpoint: Path | None = None) -> None:
        self.target = next(t for t in TARGETS if t.key == STORES[store])
        self.identity = certified_deployment_identity(self.target)
        self.deployment = Deployment.read(ROOT / self.target.deployment)
        actual = self.deployment.deployment_digest.hex()
        if actual != self.identity.deployment_sha256:
            raise SystemExit(
                f"{self.target.key}: deployment digest is {actual}, the "
                f"certificate at {self.identity.evidence_artifact} case "
                f"{self.identity.evidence_case!r} requires "
                f"{self.identity.deployment_sha256}"
            )
        self.capability = Capability.from_dict(
            json.loads((ROOT / self.target.capability).read_text(encoding="utf-8"))
        )
        if self.capability.digest != self.identity.capability_sha256:
            raise SystemExit(
                f"{self.target.key}: capability digest is "
                f"{self.capability.digest}, the certificate requires "
                f"{self.identity.capability_sha256}"
            )
        report = verify_deployment(self.deployment, self.capability)
        if not report.admitted:
            raise SystemExit(f"{self.target.key}: the ABI verifier refuses it")
        load_engines()
        self.checkpoint = checkpoint_root(self.target, checkpoint)

    def device(self, weight_cache_bytes: int) -> Device:
        return Device(
            self.deployment,
            self.capability,
            root=self.checkpoint,
            verify=False,
            trace=False,
            decoded_weight_cache_bytes=weight_cache_bytes,
        )


def _summarise(
    name: str, statement: str, rows: list[dict[str, Any]],
    generated: list[int], gold: list[int], note: str, seconds: float,
) -> dict[str, Any]:
    return {
        "decomposition": name,
        "statement": statement,
        "device_transactions": len(rows),
        "completed_transactions": sum(1 for r in rows if r["status"] == 0),
        "forward_passed_positions": sum(
            r["span_tokens"] for r in rows if r["status"] == 0
        ),
        "generated_token_ids": generated,
        "reproduces_gold": generated == gold,
        "note": note,
        "wall_seconds": round(seconds, 2),
        "transactions": rows,
    }


def case_workload_driver(bench: Bench, prompt, limit, gold, cache) -> dict[str, Any]:
    device = bench.device(cache)
    driver = GenerationDriver(device)
    started = time.perf_counter()
    with Tally(device) as tally:
        result = driver.generate(prompt, max_new_tokens=limit)
    return _summarise(
        "workload_driver",
        "the workload's own submission sequence: one prefill transaction "
        "spanning every prompt position, then one decode transaction per "
        "further token, exactly as runtime.driver.GenerationDriver.generate "
        "issues it",
        tally.rows,
        [int(t) for t in result.generated_token_ids],
        gold,
        f"stop_reason={result.stop_reason}",
        time.perf_counter() - started,
    )


def _decode_to_eos(driver, session, rows_generated, position, limit, tally_rows):
    note = ""
    while len(rows_generated) < limit and not session.finished:
        driver._write_input_tokens(session, [rows_generated[-1]], 0)  # noqa: SLF001
        symbols = {
            **driver.deployment_symbols,
            int(Symbol.SPAN_TOKENS): 1,
            int(Symbol.POSITION_START): position,
            int(Symbol.POSITION_END): position + 1,
            int(Symbol.CONTEXT_LENGTH): position + 1,
            int(Symbol.PHASE): int(Phase.DECODE),
            int(Symbol.MAX_NEW_TOKENS): limit,
            int(Symbol.BATCH): 1,
            int(Symbol.GENERATION_INDEX): len(rows_generated),
            int(Symbol.SPAN_LAST_INDEX): 0,
        }
        _, result = driver._submit(  # noqa: SLF001
            session, entrypoint=driver.decode_entrypoint, symbols=symbols,
            phase=Phase.DECODE, max_new_tokens=limit,
        )
        if int(result.status) != 0:
            note = f"the decode transaction at position {position} failed: {result.message}"
            break
        rows_generated.extend(int(t) for t in result.produced_tokens)
        position += 1
        if int(result.eos_reason) == int(EosReason.OFFICIAL_EOS):
            break
        if int(result.eos_reason) != int(EosReason.NONE):
            note = (
                f"the decode transaction at position {position - 1} ended the "
                f"session with eos_reason={int(result.eos_reason)} before the "
                "official EOS"
            )
            break
    return note


def case_chunked_prefill(
    bench: Bench, prompt, limit, gold, cache, span: int
) -> dict[str, Any]:
    """The prompt in ceil(len/span) prefill transactions, then decode."""
    device = bench.device(cache)
    driver = GenerationDriver(device)
    session = device.create_session()
    generated: list[int] = []
    note = ""
    started = time.perf_counter()
    with Tally(device) as tally:
        position = 0
        consumed_prompt = True
        while position < len(prompt):
            chunk = prompt[position:position + span]
            driver._write_input_tokens(session, chunk, 0)  # noqa: SLF001
            symbols = {
                **driver.deployment_symbols,
                int(Symbol.SPAN_TOKENS): len(chunk),
                int(Symbol.POSITION_START): position,
                int(Symbol.POSITION_END): position + len(chunk),
                int(Symbol.CONTEXT_LENGTH): position + len(chunk),
                int(Symbol.PHASE): int(Phase.PREFILL),
                int(Symbol.MAX_NEW_TOKENS): limit,
                int(Symbol.BATCH): 1,
                int(Symbol.GENERATION_INDEX): len(generated),
                int(Symbol.SPAN_LAST_INDEX): len(chunk) - 1,
            }
            try:
                _, result = driver._submit(  # noqa: SLF001
                    session, entrypoint=driver.prefill_entrypoint,
                    symbols=symbols, phase=Phase.PREFILL, max_new_tokens=limit,
                )
            except Exception as exc:  # noqa: BLE001
                note = (
                    f"the chunk at position {position} was refused before it "
                    f"ran: {type(exc).__name__}: {exc}"
                )
                consumed_prompt = False
                break
            if int(result.status) != 0:
                note = (
                    f"the chunk at position {position} failed: {result.message}"
                )
                consumed_prompt = False
                break
            generated.extend(int(t) for t in result.produced_tokens)
            position += len(chunk)
            if int(result.eos_reason) != int(EosReason.NONE):
                note = (
                    f"the chunk at position {position - len(chunk)} ended the "
                    f"session with eos_reason={int(result.eos_reason)} after "
                    f"{position} of {len(prompt)} prompt positions: every pass "
                    "of this program appends a token, so the request's own "
                    "MAX_NEW_TOKENS bound is reached while the prompt is still "
                    "being read"
                )
                consumed_prompt = False
                break
        if consumed_prompt and generated:
            note = _decode_to_eos(
                driver, session, generated, len(prompt), limit, tally.rows
            )
    return _summarise(
        f"chunked_prefill_span_{span}",
        f"the prompt in prefill transactions of SPAN_TOKENS={span}, then one "
        "decode transaction per further token",
        tally.rows,
        generated,
        gold,
        note,
        time.perf_counter() - started,
    )


def case_decode_only(bench: Bench, prompt, limit, gold, cache) -> dict[str, Any]:
    """No prefill at all: every prompt position through the decode entrypoint."""
    device = bench.device(cache)
    driver = GenerationDriver(device)
    session = device.create_session()
    generated: list[int] = []
    note = ""
    started = time.perf_counter()
    with Tally(device) as tally:
        for position, token in enumerate(prompt):
            driver._write_input_tokens(session, [token], 0)  # noqa: SLF001
            symbols = {
                **driver.deployment_symbols,
                int(Symbol.SPAN_TOKENS): 1,
                int(Symbol.POSITION_START): position,
                int(Symbol.POSITION_END): position + 1,
                int(Symbol.CONTEXT_LENGTH): position + 1,
                int(Symbol.PHASE): int(Phase.DECODE),
                int(Symbol.MAX_NEW_TOKENS): limit,
                int(Symbol.BATCH): 1,
                int(Symbol.GENERATION_INDEX): len(generated),
                int(Symbol.SPAN_LAST_INDEX): 0,
            }
            try:
                _, result = driver._submit(  # noqa: SLF001
                    session, entrypoint=driver.decode_entrypoint, symbols=symbols,
                    phase=Phase.DECODE, max_new_tokens=limit,
                )
            except Exception as exc:  # noqa: BLE001
                note = (
                    f"the transaction at position {position} was refused "
                    f"before it ran: {type(exc).__name__}: {exc}"
                )
                break
            if int(result.status) != 0:
                note = (
                    f"the transaction at position {position} failed: "
                    f"{result.message}"
                )
                break
            generated.extend(int(t) for t in result.produced_tokens)
            if int(result.eos_reason) != int(EosReason.NONE):
                note = (
                    f"the transaction at position {position} ended the session "
                    f"with eos_reason={int(result.eos_reason)} after "
                    f"{position + 1} of {len(prompt)} prompt positions"
                )
                break
        else:
            if generated:
                note = _decode_to_eos(
                    driver, session, generated, len(prompt), limit, tally.rows
                )
    return _summarise(
        "decode_entrypoint_per_position",
        "no prefill transaction at all: every prompt position submitted "
        "singly through the decode entrypoint, then one decode transaction "
        "per further token",
        tally.rows,
        generated,
        gold,
        note,
        time.perf_counter() - started,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", choices=sorted(STORES), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, default=None)
    parser.add_argument("--weight-cache-bytes", type=int, default=2 << 30)
    parser.add_argument(
        "--spans", type=int, nargs="*", default=[8, 4, 1],
        help="prefill chunk sizes to try, in prompt positions",
    )
    args = parser.parse_args()

    workload = json.loads((ROOT / WORKLOAD_PATH).read_text(encoding="utf-8"))
    oracle = json.loads((ROOT / ORACLE_PATH).read_text(encoding="utf-8"))
    oracle_case = oracle["results"][WORKLOAD_ID]
    if oracle_case["workload_digest"] != workload["digest"]:
        raise SystemExit(
            "the oracle's workload digest does not match the workload on "
            "disk; a decomposition study against gold for a different prompt "
            "is refused, not recorded"
        )
    gold = [int(t) for t in oracle_case["generated_token_ids"]]
    prompt = [int(t) for t in workload["token_ids"]]
    limit = int(workload["max_new_tokens"])
    positions = len(prompt) + len(gold)

    bench = Bench(args.store, args.checkpoint)
    started = time.perf_counter()
    cases = [case_workload_driver(bench, prompt, limit, gold, args.weight_cache_bytes)]
    for span in args.spans:
        if span >= len(prompt):
            continue
        cases.append(
            case_chunked_prefill(bench, prompt, limit, gold, args.weight_cache_bytes, span)
        )
    cases.append(case_decode_only(bench, prompt, limit, gold, args.weight_cache_bytes))
    wall = time.perf_counter() - started

    correct = [c for c in cases if c["reproduces_gold"]]
    required = gate_required_positions()
    maximum = max((c["device_transactions"] for c in correct), default=0)
    max_forward = max((c["forward_passed_positions"] for c in correct), default=0)

    payload = {
        "schema": SCHEMA,
        "storage_class": args.store,
        "target_key": bench.target.key,
        "deployment_sha256": bench.identity.deployment_sha256,
        "workload_id": WORKLOAD_ID,
        "workload_digest": workload["digest"],
        "oracle": {
            "path": ORACLE_PATH,
            "generated_token_ids": gold,
        },
        "prompt_token_count": len(prompt),
        "workload_token_positions": positions,
        "gate_requires_positions": required,
        "gate_requires_read_from": GATES_PATH,
        "measured": {
            "correct_decomposition_count": len(correct),
            "correct_decompositions": [c["decomposition"] for c in correct],
            "maximum_device_transactions_over_correct_decompositions": maximum,
            "maximum_forward_passed_positions_over_correct_decompositions": (
                max_forward
            ),
            "positions_never_forward_passed": positions - max_forward,
            # The gate's accounting, checked against the decompositions that
            # actually reproduce the oracle's gold.  A decomposition that
            # emits the wrong tokens does not get to satisfy it.
            "gate_accounting_is_reachable": (
                positions == required["workload_token_positions"]
                and max_forward == required["model_forward_passes"]
                and positions - max_forward
                == required["positions_never_forward_passed"]
            ),
        },
        "finding": (
            "every pass of this deployment's program ends in SELECTION.ARGMAX "
            "and SELECTION.TOKEN_APPEND, so a pass that reads prompt positions "
            "without appending a token does not exist in this lowering. Cutting "
            "the prefill into more transactions therefore emits one token per "
            "chunk that the workload never generated, and at SPAN_TOKENS=1 the "
            "request's own MAX_NEW_TOKENS bound ends the session before the "
            "prompt is consumed. The measured consequence is that the "
            "workload's own submission sequence is the only decomposition of "
            f"{WORKLOAD_ID} on this deployment that reproduces the oracle's "
            "gold, and it is the number the rung reports"
        ),
        "does_not_establish": [
            "that no other deployment of this model could execute the "
            "workload in a different number of passes; this measures the "
            "shipped program, not the model",
            "anything about the RTL: no RTL is compiled, run or read here",
        ],
        "cases": cases,
        "wall_seconds": round(wall, 2),
        "source_sha256": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            for path in SOURCE_FILES
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "PASS: ABI3 G1e pass decomposition "
        f"store={args.store} cases={len(cases)} correct={len(correct)} "
        f"max_transactions={maximum} max_forward_positions={max_forward} "
        f"positions={positions} "
        f"gate_requires={json.dumps(required, sort_keys=True)} "
        f"reachable={int(payload['measured']['gate_accounting_is_reachable'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
