"""Host driver: prompt in, real tokenizer token IDs out, through the ABI 3.0 queue.

The host's permitted role is narrow and this module keeps to it.  It may
tokenize, write the prompt into an authenticated input window, submit a bounded
request, and decode returned token IDs.  It may not sequence device operations,
choose a token, or supply an intermediate activation: token selection happens in
the device's SELECTION engine, driven by the compiled program, and the driver
only reads the result out of the token ring.

Every request and completion crosses the boundary as a real encoded 128-byte
ABI 3.0 record, not as a Python object, so the queue format is exercised on
every generated token rather than only in a unit test.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from runtime.abi3.constants import (
    CompletionStatus,
    HostOpcode,
    NO_ID,
    SubmissionFlag,
    TrapClass,
)
from runtime.abi3.descriptors import ExtendedDescriptorType, Phase, Symbol
from runtime.abi3.records import Completion, EosReason, Submission
from runtime.sim.device import Device, Session, TransactionResult


class DriverError(Exception):
    """Raised when the host boundary itself is misused or a request fails."""


@dataclass
class GenerationResult:
    """Everything a report needs about one generation, and nothing derived."""

    prompt_token_ids: tuple[int, ...]
    generated_token_ids: tuple[int, ...]
    stop_reason: str
    eos_token_id: int | None
    transactions: int
    prefill_tokens: int
    decode_steps: int
    counters: dict[str, int]
    per_step: list[dict[str, Any]] = dc_field(default_factory=list)
    wall_seconds: float = 0.0
    failure: str | None = None

    @property
    def all_token_ids(self) -> tuple[int, ...]:
        return self.prompt_token_ids + self.generated_token_ids

    def to_dict(self) -> dict[str, Any]:
        return {
            "prompt_token_ids": list(self.prompt_token_ids),
            "prompt_token_count": len(self.prompt_token_ids),
            "generated_token_ids": list(self.generated_token_ids),
            "generated_token_count": len(self.generated_token_ids),
            "stop_reason": self.stop_reason,
            "eos_token_id": self.eos_token_id,
            "transactions": self.transactions,
            "prefill_tokens": self.prefill_tokens,
            "decode_steps": self.decode_steps,
            "counters": dict(sorted(self.counters.items())),
            "per_step": self.per_step,
            "wall_seconds": round(self.wall_seconds, 6),
            "failure": self.failure,
        }


class GenerationDriver:
    """Drives prefill and decode over one device and one session."""

    def __init__(
        self,
        device: Device,
        *,
        input_object_id: int | None = None,
        token_ring_object_id: int | None = None,
        prefill_entrypoint: int = 0,
        decode_entrypoint: int = 1,
    ) -> None:
        self.device = device
        self.prefill_entrypoint = prefill_entrypoint
        self.decode_entrypoint = decode_entrypoint
        self.policy = self._resolve_policy()
        self.token_ring_object_id = (
            token_ring_object_id
            if token_ring_object_id is not None
            else self.policy["token_ring_object_id"]
        )
        self.input_object_id = (
            input_object_id
            if input_object_id is not None
            else self.token_ring_object_id
        )
        self._transaction = 0

    # -- policy ----------------------------------------------------------
    def _resolve_policy(self) -> Mapping[str, Any]:
        for entry in self.device.deployment.entrypoints:
            gid = entry.get("generation_policy_id", NO_ID)
            if gid != NO_ID:
                return self.device.deployment.table.get(
                    gid, ExtendedDescriptorType.GENERATION_POLICY
                ).payload
        raise DriverError(
            "deployment declares no generation policy; it cannot generate tokens"
        )

    @property
    def eos_token_ids(self) -> tuple[int, ...]:
        count = self.policy["eos_count"]
        return tuple(self.policy[f"eos_token_{i}"] for i in range(count))

    @property
    def vocabulary_size(self) -> int:
        return self.policy["vocabulary_size"]

    # -- host queue ------------------------------------------------------
    def _next_transaction(self) -> int:
        self._transaction += 1
        return self._transaction

    def _idempotency_key(self, session: Session, transaction: int) -> bytes:
        material = f"{session.session_id}:{session.generation}:{transaction}".encode()
        return hashlib.sha256(material).digest()[:16]

    def _submit(
        self,
        session: Session,
        *,
        entrypoint: int,
        symbols: Mapping[int, int],
        phase: Phase,
        max_new_tokens: int,
    ) -> tuple[Completion, TransactionResult]:
        """Encode a real submission, run the transaction, encode a completion."""
        transaction = self._next_transaction()
        request = Submission(
            host_opcode=int(HostOpcode.GENERATE),
            deployment_id=self.device.deployment.deployment_id,
            deployment_generation=self.device.deployment.generation,
            session_id=session.session_id,
            session_generation=session.generation,
            transaction_id=transaction,
            idempotency_key=self._idempotency_key(session, transaction),
            input_window_id=self.input_object_id,
            output_window_id=self.token_ring_object_id,
            entrypoint_id=entrypoint,
            generation_policy_id=NO_ID,
            watchdog_class=1,
            flags=int(
                SubmissionFlag.PREFILL_PHASE
                if phase is Phase.PREFILL
                else SubmissionFlag.DECODE_PHASE
            ),
        ).encode()
        decoded = Submission.decode(request)  # the device sees only the bytes
        result = self.device.run_transaction(
            session,
            entrypoint_id=decoded.entrypoint_id,
            symbols=symbols,
            generation_policy_id=self._policy_id(),
        )
        completion = Completion(
            status=result.status,
            transaction_id=decoded.transaction_id,
            deployment_id=decoded.deployment_id,
            deployment_generation=decoded.deployment_generation,
            session_id=decoded.session_id,
            session_generation=session.generation,
            trap_class=result.trap_class,
            committed_token_position=session.position,
            produced_token_count=len(result.produced_tokens),
            committed_state_generation=session.generation,
            first_fault_instruction=result.first_fault_instruction,
            idempotency_key=decoded.idempotency_key,
            final_token_id=result.selected_token,
            eos_reason=result.eos_reason,
            retired_work=result.retired,
            completion_timestamp=self.device._device_cycle,
        ).encode()
        return Completion.decode(completion), result

    def _policy_id(self) -> int:
        for entry in self.device.deployment.entrypoints:
            gid = entry.get("generation_policy_id", NO_ID)
            if gid != NO_ID:
                return gid
        return NO_ID

    # -- input staging ----------------------------------------------------
    def _write_input_tokens(self, token_ids: Sequence[int], offset: int) -> None:
        """Write prompt token IDs into the authenticated input window."""
        obj = self.device.memory[self.input_object_id]
        payload = np.asarray(token_ids, dtype=np.uint32).tobytes()
        byte_offset = offset * 4
        if byte_offset + len(payload) > obj.size_bytes:
            raise DriverError(
                f"input window holds {obj.size_bytes // 4} tokens; writing "
                f"{len(token_ids)} at {offset} does not fit"
            )
        for token in token_ids:
            if not 0 <= token < self.vocabulary_size:
                raise DriverError(
                    f"token {token} is outside the declared vocabulary "
                    f"{self.vocabulary_size}"
                )
        obj.write(byte_offset, payload)

    # -- generation -------------------------------------------------------
    def generate(
        self,
        prompt_token_ids: Sequence[int],
        *,
        max_new_tokens: int | None = None,
        session: Session | None = None,
        progress: Callable[[int, int], None] | None = None,
    ) -> GenerationResult:
        """Prefill the prompt then decode to the first official EOS or the bound.

        The EOS token is included in the returned sequence and no transaction
        runs after it (ADR-003 section 8.7).
        """
        started = time.perf_counter()
        if not prompt_token_ids:
            raise DriverError("prompt is empty")
        limit = (
            self.policy["max_new_tokens"]
            if max_new_tokens is None
            else min(max_new_tokens, self.policy["max_new_tokens"])
        )
        session = session or self.device.create_session()
        prompt = tuple(int(t) for t in prompt_token_ids)
        self._write_input_tokens(prompt, 0)

        per_step: list[dict[str, Any]] = []
        generated: list[int] = []
        transactions = 0
        stop_reason = "max_new_tokens"
        failure: str | None = None
        eos_token: int | None = None

        symbols = {
            int(Symbol.SPAN_TOKENS): len(prompt),
            int(Symbol.POSITION_START): 0,
            int(Symbol.POSITION_END): len(prompt),
            int(Symbol.CONTEXT_LENGTH): len(prompt),
            int(Symbol.PHASE): int(Phase.PREFILL),
            int(Symbol.MAX_NEW_TOKENS): limit,
            int(Symbol.BATCH): 1,
            int(Symbol.GENERATION_INDEX): 0,
            int(Symbol.SPAN_LAST_INDEX): len(prompt) - 1,
        }
        completion, result = self._submit(
            session,
            entrypoint=self.prefill_entrypoint,
            symbols=symbols,
            phase=Phase.PREFILL,
            max_new_tokens=limit,
        )
        transactions += 1
        per_step.append(_step_record(0, "prefill", completion, result))
        if completion.status != CompletionStatus.SUCCESS:
            failure = f"prefill failed: {result.message}"
            return self._finish(
                prompt, generated, "failed", None, transactions, len(prompt), 0,
                per_step, started, failure,
            )
        generated.extend(result.produced_tokens)
        if result.eos_reason == EosReason.OFFICIAL_EOS:
            eos_token = result.selected_token
            return self._finish(
                prompt, generated, "eos", eos_token, transactions, len(prompt), 0,
                per_step, started, None,
            )

        position = len(prompt)
        decode_steps = 0
        while len(generated) < limit:
            if not generated:
                failure = "prefill produced no token to decode from"
                stop_reason = "failed"
                break
            # The input window holds *this transaction's* input span, not the
            # whole history: the device reads it from element zero and the
            # history lives in committed KV state. Writing a decode token at
            # its absolute position instead left the device re-reading the
            # first prompt token every step, which showed up as the generation
            # repeating itself after the first decode.
            self._write_input_tokens([generated[-1]], 0)
            symbols = {
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
            completion, result = self._submit(
                session,
                entrypoint=self.decode_entrypoint,
                symbols=symbols,
                phase=Phase.DECODE,
                max_new_tokens=limit,
            )
            transactions += 1
            decode_steps += 1
            per_step.append(_step_record(decode_steps, "decode", completion, result))
            if completion.status != CompletionStatus.SUCCESS:
                failure = f"decode step {decode_steps} failed: {result.message}"
                stop_reason = "failed"
                break
            generated.extend(result.produced_tokens)
            position += 1
            if progress is not None:
                progress(len(generated), limit)
            if result.eos_reason == EosReason.OFFICIAL_EOS:
                eos_token = result.selected_token
                stop_reason = "eos"
                break
        else:
            stop_reason = "max_new_tokens"

        return self._finish(
            prompt, generated, stop_reason, eos_token, transactions, len(prompt),
            decode_steps, per_step, started, failure,
        )

    def _finish(
        self,
        prompt: tuple[int, ...],
        generated: Sequence[int],
        stop_reason: str,
        eos_token: int | None,
        transactions: int,
        prefill_tokens: int,
        decode_steps: int,
        per_step: list[dict[str, Any]],
        started: float,
        failure: str | None,
    ) -> GenerationResult:
        return GenerationResult(
            prompt_token_ids=prompt,
            generated_token_ids=tuple(int(t) for t in generated),
            stop_reason=stop_reason,
            eos_token_id=eos_token,
            transactions=transactions,
            prefill_tokens=prefill_tokens,
            decode_steps=decode_steps,
            counters=self.device.counters.snapshot(),
            per_step=per_step,
            wall_seconds=time.perf_counter() - started,
            failure=failure,
        )


def _step_record(
    index: int, phase: str, completion: Completion, result: TransactionResult
) -> dict[str, Any]:
    return {
        "step": index,
        "phase": phase,
        "status": CompletionStatus(completion.status).name,
        "trap": TrapClass(completion.trap_class).name,
        "transaction_id": completion.transaction_id,
        "retired_work": completion.retired_work,
        "produced_tokens": list(result.produced_tokens),
        "final_token_id": (
            None if completion.final_token_id == NO_ID else completion.final_token_id
        ),
        "eos_reason": completion.eos_reason,
        "instructions_retired": result.retired,
        "instructions_predicated_off": result.predicated_off,
        "wall_seconds": round(result.wall_seconds, 6),
    }


def validate_token_ids(
    token_ids: Iterable[int], vocabulary_size: int
) -> list[str]:
    """Return the reasons any produced ID is not a legal tokenizer token."""
    problems = []
    for index, token in enumerate(token_ids):
        if not isinstance(token, int) or isinstance(token, bool):
            problems.append(f"token {index} is not an integer: {token!r}")
        elif not 0 <= token < vocabulary_size:
            problems.append(
                f"token {index} = {token} is outside vocabulary {vocabulary_size}"
            )
    return problems
