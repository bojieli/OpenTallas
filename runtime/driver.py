"""Host driver: prompt in, real tokenizer token IDs out, through the ABI 3.0 queue.

The host's permitted role is narrow and this module keeps to it.  It may
tokenize, write the prompt into an authenticated input window, submit a bounded
request, and decode returned token IDs.  It may not sequence device operations,
choose a token, or supply an intermediate activation: token selection happens in
the device's SELECTION engine, driven by the compiled program, and the driver
only reads the result out of the token ring.

Every request and completion crosses the boundary as a real encoded 128-byte
ABI 3.0 record.  The complete runtime-symbol map crosses in the separately
encoded record named by ``request_descriptor_id``; no Python symbol sidecar is
accepted by the device queue.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np

from runtime.abi3.constants import (
    Attention,
    CompletionStatus,
    HostOpcode,
    Major,
    NO_ID,
    Reduction,
    Route,
    SubmissionFlag,
    TrapClass,
)
from runtime.abi3.descriptors import ExtendedDescriptorType, Phase, SelectorKind, Symbol
from runtime.abi3.records import Completion, EosReason, Submission
from runtime.abi3.request import RequestSymbolDescriptor
from runtime.sim.batch import BatchLaneSubmission, BatchScheduler
from runtime.sim.device import Device, Session, TransactionResult


class DriverError(Exception):
    """Raised when the host boundary itself is misused or a request fails."""


#: The six section 12.2 symbols a *request* does not carry.  The other nine are
#: properties of the submission -- how many tokens, at what position, in which
#: phase -- and the driver states those from the request itself.
_DEPLOYMENT_SYMBOLS = (
    Symbol.NODE_ID,
    Symbol.NODE_COUNT,
    Symbol.ACTIVE_EXPERT_COUNT,
    Symbol.SPARSE_INDEX_COUNT,
    Symbol.LAYER_COUNT,
    Symbol.VOCABULARY_PARTITIONS,
)


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
    request_start_tick: int | None = None
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
            "request_start_tick": self.request_start_tick,
            "per_step": self.per_step,
            "wall_seconds": round(self.wall_seconds, 6),
            "failure": self.failure,
        }


@dataclass(frozen=True, slots=True)
class BatchGenerationRequest:
    """One independent sequence admitted to a physical dynamic batch."""

    sequence_id: str
    prompt_token_ids: tuple[int, ...]
    max_new_tokens: int


@dataclass
class BatchSequenceResult:
    """One lane's complete result, retaining its scalar ABI trajectory."""

    lane_index: int
    sequence_id: str
    generation: GenerationResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "lane_index": self.lane_index,
            "sequence_id": self.sequence_id,
            **self.generation.to_dict(),
        }


@dataclass
class BatchGenerationResult:
    """Independent sequence results from one shared scheduler execution."""

    batch_execution_id: str | None
    physical_batch_size: int
    sequences: tuple[BatchSequenceResult, ...]
    waves: tuple[dict[str, Any], ...]
    scheduler_evidence: dict[str, Any]
    wall_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_execution_id": self.batch_execution_id,
            "physical_batch_size": self.physical_batch_size,
            "sequences": [sequence.to_dict() for sequence in self.sequences],
            "waves": list(self.waves),
            "scheduler_evidence": self.scheduler_evidence,
            "wall_seconds": round(self.wall_seconds, 6),
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
        self.deployment_symbols = self._resolve_deployment_symbols()

    # -- deployment scalars ----------------------------------------------
    def _resolve_deployment_symbols(self) -> dict[int, int]:
        """The six section 12.2 symbols a request does not carry.

        Nine of the fifteen frozen symbols are properties of the *submission* --
        how many tokens, at what position, in which phase -- and this driver
        has always stated those.  The other six are properties of the
        *deployment*, and until now four of them were simply never bound, so a
        loop bound or a view term naming one resolved to ``symbol ... is
        unbound`` at the moment it was read.  A frozen registry entry no
        implementation binds is not a registry entry; it is a trap waiting for
        the first program that uses it.

        Each is read off the descriptors that *define* it, so the value is the
        deployment's own statement rather than a host's guess:

        ``NODE_ID`` / ``NODE_COUNT``
            the admitted topology's.  The device rebinds both -- ``NODE_ID`` at
            every engine issue -- so these are stated only so that no symbol is
            missing before it does.
        ``ACTIVE_EXPERT_COUNT``
            routing slots per token, the expert-ID extent every
            ``TENSOR.ROUTED_MATMUL`` declares.
        ``SPARSE_INDEX_COUNT``
            selected KV rows per query row, the index extent every
            ``ATTENTION.SPARSE`` declares.
        ``VOCABULARY_PARTITIONS``
            declared partitions, the partial-result extent every
            ``REDUCTION.PARTITION_SUM`` declares.
        ``LAYER_COUNT``
            the layer count the deployment's own lowering notes record.  No
            descriptor states it, so nothing is derived from one.

        A symbol is *stated* only when every operator that defines it declares
        the same number.  Operators that disagree state nothing: DeepSeek's
        sparse attention declares 128, 640 and 2,176 selected rows in different
        layers, and one runtime symbol cannot be all three, so the deployment
        simply does not define ``SPARSE_INDEX_COUNT`` -- which is the truth, and
        is why an average or a maximum would be a fabrication.

        A symbol the program actually *names* -- in a loop bound, a predicate
        operand or a view term -- that the deployment does not state is a
        **refusal**, because binding a made-up value there is exactly the silent
        wrong answer this boundary exists to prevent.  An unstated symbol that
        nothing names is bound to the value meaning the thing does not exist:
        zero routed experts, zero sparse indices, one vocabulary partition, no
        declared layer count.  Binding it costs nothing and removes a whole
        class of "symbol is unbound" faults from programs that never asked.
        """
        deployment = self.device.deployment
        stated: dict[int, int] = {
            int(Symbol.NODE_ID): 0,
            int(Symbol.NODE_COUNT): int(self.device.node_count),
        }
        witness: dict[int, tuple[str, tuple[int, ...]]] = {}
        for symbol, where, values in (
            (
                Symbol.ACTIVE_EXPERT_COUNT,
                "ROUTE.TOPK/BIASED_TOPK selected-expert extents",
                self._operand_extents(
                    Major.ROUTE,
                    (int(Route.TOPK), int(Route.BIASED_TOPK)),
                    "output_view_0",
                    -1,
                ),
            ),
            (
                Symbol.SPARSE_INDEX_COUNT,
                "ATTENTION.SPARSE index extents",
                self._operand_extents(
                    Major.ATTENTION, (int(Attention.SPARSE),), "input_view_2", -1
                ),
            ),
            (
                Symbol.VOCABULARY_PARTITIONS,
                "REDUCTION.PARTITION_SUM partial extents",
                self._operand_extents(
                    Major.REDUCTION,
                    (int(Reduction.PARTITION_SUM),),
                    "input_view_0",
                    0,
                ),
            ),
            (
                Symbol.LAYER_COUNT,
                "the deployment's lowering notes",
                _declared_layer_count(deployment.notes),
            ),
        ):
            witness[int(symbol)] = (where, values)
            if len(values) == 1:
                stated[int(symbol)] = int(values[0])
        named = self._named_symbols()
        defaults = {
            int(Symbol.ACTIVE_EXPERT_COUNT): 0,
            int(Symbol.SPARSE_INDEX_COUNT): 0,
            int(Symbol.VOCABULARY_PARTITIONS): 1,
            int(Symbol.LAYER_COUNT): 0,
        }
        for symbol in _DEPLOYMENT_SYMBOLS:
            if int(symbol) in stated:
                continue
            if int(symbol) in named:
                where, values = witness[int(symbol)]
                detail = (
                    f"{where} are {list(values)}, which is not one number"
                    if values
                    else f"nothing in the deployment states it ({where})"
                )
                raise DriverError(
                    f"the program names runtime symbol {symbol.name} but "
                    f"{detail}; the host will not invent one"
                )
            stated[int(symbol)] = defaults[int(symbol)]
        return stated

    def _operand_extents(
        self, family: Major, subs: Sequence[int], slot: str, axis: int
    ) -> tuple[int, ...]:
        """The distinct extents every operator of this kind declares there."""
        table = self.device.deployment.table
        wanted = {int(sub) for sub in subs}
        found: set[int] = set()
        for descriptor in table.descriptors():
            if descriptor.descriptor_type != ExtendedDescriptorType.OPERATOR:
                continue
            payload = descriptor.payload
            if int(payload["engine_family"]) != int(family):
                continue
            if int(payload["engine_sub"]) not in wanted:
                continue
            vid = int(payload[slot])
            if vid == NO_ID:
                continue
            try:
                view = table.get(vid, ExtendedDescriptorType.TENSOR_VIEW)
            except Exception:
                continue
            rank = int(view.payload["rank"])
            index = axis if axis >= 0 else rank + axis
            if not 0 <= index < rank:
                continue
            found.add(int(view.payload[f"dim{index}"]))
        return tuple(sorted(found))

    def _named_symbols(self) -> frozenset[int]:
        """Every runtime symbol this program actually reads."""
        table = self.device.deployment.table
        named: set[int] = set()
        for descriptor in table.descriptors():
            payload = descriptor.payload
            kind = descriptor.descriptor_type
            if kind == ExtendedDescriptorType.LOOP_CONTROL:
                if payload["bound_selector_kind"] == SelectorKind.RUNTIME_SYMBOL:
                    named.add(int(payload["bound_symbol_id"]))
            elif kind == ExtendedDescriptorType.PREDICATE:
                if payload["selector_kind"] == SelectorKind.RUNTIME_SYMBOL:
                    named.add(int(payload["selector_index"]))
            elif kind == ExtendedDescriptorType.TENSOR_VIEW:
                for slot in range(int(payload["dynamic_term_count"])):
                    if payload[f"term{slot}_kind"] == SelectorKind.RUNTIME_SYMBOL:
                        named.add(int(payload[f"term{slot}_index"]))
        return frozenset(named)

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
    @property
    def transaction_count(self) -> int:
        """Transactions this driver has submitted.

        A restart carries it forward so the resumed process does not reuse the
        transaction identifiers and idempotency keys the interrupted one spent.
        """
        return self._transaction

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
        """Register symbols, then execute only the encoded ABI submission."""
        transaction = self._next_transaction()
        request = self._prepare_submission(
            session,
            transaction=transaction,
            entrypoint=entrypoint,
            symbols=symbols,
            phase=phase,
        )
        completion, result = self.device.execute_submission(request)
        return Completion.decode(completion), result

    def _prepare_submission(
        self,
        session: Session,
        *,
        transaction: int,
        entrypoint: int,
        symbols: Mapping[int, int],
        phase: Phase,
    ) -> bytes:
        """Register one symbol descriptor and return its encoded submission.

        Scalar and batched generation share this exact construction. The
        caller owns execution: the scalar path submits it immediately, while a
        batch scheduler first admits every active lane as one atomic wave.
        """

        descriptor_id = self.device.next_request_descriptor_id
        descriptor = RequestSymbolDescriptor.from_symbols(
            request_descriptor_id=descriptor_id,
            deployment_id=self.device.deployment.deployment_id,
            deployment_generation=self.device.deployment.generation,
            session_id=session.session_id,
            session_generation=session.generation,
            transaction_id=transaction,
            symbols=symbols,
        )
        self.device.register_request_descriptor(descriptor.encode())
        try:
            request = Submission(
                host_opcode=int(HostOpcode.GENERATE),
                deployment_id=self.device.deployment.deployment_id,
                deployment_generation=self.device.deployment.generation,
                session_id=session.session_id,
                session_generation=session.generation,
                request_descriptor_id=descriptor_id,
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
        except Exception:
            self.device.discard_request_descriptors((descriptor_id,))
            raise
        return request

    def _policy_id(self) -> int:
        for entry in self.device.deployment.entrypoints:
            gid = entry.get("generation_policy_id", NO_ID)
            if gid != NO_ID:
                return gid
        return NO_ID

    # -- input staging ----------------------------------------------------
    def _write_input_tokens(
        self, session: Session, token_ids: Sequence[int], offset: int
    ) -> None:
        """Write prompt token IDs into the authenticated input window."""
        obj = self.device.host_object(self.input_object_id, session=session)
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
        # Every node of the cluster reads the request out of its own input
        # window, so the window is staged on every node.  On a single chip this
        # is the one write it always was.
        self.device.host_write(
            self.input_object_id, byte_offset, payload, session=session
        )

    # -- generation -------------------------------------------------------
    def generate(
        self,
        prompt_token_ids: Sequence[int],
        *,
        max_new_tokens: int | None = None,
        session: Session | None = None,
        progress: Callable[[int, int], None] | None = None,
        stop_after_tokens: int | None = None,
    ) -> GenerationResult:
        """Prefill the prompt then decode to the first official EOS or the bound.

        The EOS token is included in the returned sequence and no transaction
        runs after it (ADR-003 section 8.7).

        ``stop_after_tokens`` stops this *process* after that many tokens
        without changing the request the device sees: the declared bound in
        ``MAX_NEW_TOKENS`` stays ``max_new_tokens``, so a run that stops early
        and a run that does not submit identical transactions up to the stop.
        It exists so that a checkpoint can be taken between two transactions of
        a generation that is still, from the device's side, the same request.
        """
        started = time.perf_counter()
        if not prompt_token_ids:
            raise DriverError("prompt is empty")
        # Capture the target counter immediately before this fresh request is
        # staged.  Host staging consumes no target cycles in the functional
        # device, so this is the causal request-start boundary paired with the
        # completion timestamps returned by the ABI queue below.  A resumed
        # segment deliberately does not invent the original request start.
        request_start_tick = int(self.device._device_cycle)
        limit = (
            self.policy["max_new_tokens"]
            if max_new_tokens is None
            else min(max_new_tokens, self.policy["max_new_tokens"])
        )
        session = session or self.device.create_session()
        prompt = tuple(int(t) for t in prompt_token_ids)
        self._write_input_tokens(session, prompt, 0)

        per_step: list[dict[str, Any]] = []
        generated: list[int] = []
        transactions = 0

        symbols = {
            **self.deployment_symbols,
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
            return self._finish(
                prompt, generated, "failed", None, transactions, len(prompt), 0,
                per_step, started, f"prefill failed: {result.message}",
                request_start_tick=request_start_tick,
            )
        generated.extend(result.produced_tokens)
        if result.eos_reason == EosReason.OFFICIAL_EOS:
            return self._finish(
                prompt, generated, "eos", result.selected_token, transactions,
                len(prompt), 0, per_step, started, None,
                request_start_tick=request_start_tick,
            )

        return self._decode(
            session,
            prompt=prompt,
            generated=generated,
            position=len(prompt),
            limit=limit,
            stop_after_tokens=stop_after_tokens,
            per_step=per_step,
            transactions=transactions,
            prefill_tokens=len(prompt),
            started=started,
            progress=progress,
            request_start_tick=request_start_tick,
        )

    def resume(
        self,
        prompt_token_ids: Sequence[int],
        generated_token_ids: Sequence[int],
        *,
        session: Session,
        position: int,
        max_new_tokens: int | None = None,
        transaction_offset: int = 0,
        progress: Callable[[int, int], None] | None = None,
        stop_after_tokens: int | None = None,
    ) -> GenerationResult:
        """Continue decode for a session restored from a device checkpoint.

        No prefill runs: the prompt's KV is already in the restored state
        images, and re-prefilling would be a different computation from the one
        the interrupted run performed.  ``position`` is the absolute position
        the next decode token occupies and ``generated_token_ids`` is what the
        interrupted process had produced, so the first resumed transaction is
        byte-for-byte the transaction the uninterrupted run would have issued.
        """
        started = time.perf_counter()
        if session.finished:
            raise DriverError(
                "restored session already reached EOS or the generation cap; "
                "there is nothing to resume"
            )
        generated = [int(t) for t in generated_token_ids]
        if not generated:
            raise DriverError(
                "resume needs the tokens the interrupted run produced; decode "
                "continues from the last one"
            )
        if position < len(prompt_token_ids):
            raise DriverError(
                f"resume position {position} is inside the prompt "
                f"({len(prompt_token_ids)} tokens)"
            )
        limit = (
            self.policy["max_new_tokens"]
            if max_new_tokens is None
            else min(max_new_tokens, self.policy["max_new_tokens"])
        )
        self._transaction = int(transaction_offset)
        self.device.sessions[session.session_id] = session
        return self._decode(
            session,
            prompt=tuple(int(t) for t in prompt_token_ids),
            generated=generated,
            position=int(position),
            limit=limit,
            stop_after_tokens=stop_after_tokens,
            per_step=[],
            transactions=0,
            prefill_tokens=0,
            started=started,
            progress=progress,
            request_start_tick=None,
        )

    def _decode(
        self,
        session: Session,
        *,
        prompt: tuple[int, ...],
        generated: list[int],
        position: int,
        limit: int,
        stop_after_tokens: int | None,
        per_step: list[dict[str, Any]],
        transactions: int,
        prefill_tokens: int,
        started: float,
        progress: Callable[[int, int], None] | None,
        request_start_tick: int | None,
    ) -> GenerationResult:
        """The decode loop, shared by a fresh generation and a resumed one."""
        decode_steps = 0
        failure: str | None = None
        eos_token: int | None = None
        stop_reason = "max_new_tokens"
        if stop_after_tokens is not None and len(generated) >= stop_after_tokens:
            return self._finish(
                prompt, generated, "stopped", None, transactions, prefill_tokens,
                decode_steps, per_step, started, None,
                request_start_tick=request_start_tick,
            )
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
            self._write_input_tokens(session, [generated[-1]], 0)
            symbols = {
                **self.deployment_symbols,
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
            if stop_after_tokens is not None and len(generated) >= stop_after_tokens:
                stop_reason = "stopped"
                break
        else:
            stop_reason = "max_new_tokens"

        return self._finish(
            prompt, generated, stop_reason, eos_token, transactions, prefill_tokens,
            decode_steps, per_step, started, failure,
            request_start_tick=request_start_tick,
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
        *,
        request_start_tick: int | None,
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
            request_start_tick=request_start_tick,
            per_step=per_step,
            wall_seconds=time.perf_counter() - started,
            failure=failure,
        )


class BatchGenerationDriver(GenerationDriver):
    """Drive independent prompts through one physical ABI 3.0 batch.

    The scheduler, not this driver, owns the active mask and session
    retirement. Every active lane contributes one ordinary scalar ABI record
    to each wave; prompts, positions, generation caps, mutable memories, token
    streams, and transaction trajectories remain independent. The host never
    retires a lane merely because its Python loop reached a length: the final
    transaction must return an on-device EOS or MAX_NEW_TOKENS reason.
    """

    def __init__(
        self,
        scheduler: BatchScheduler,
        *,
        input_object_id: int | None = None,
        token_ring_object_id: int | None = None,
        prefill_entrypoint: int = 0,
        decode_entrypoint: int = 1,
    ) -> None:
        super().__init__(
            scheduler.device,
            input_object_id=input_object_id,
            token_ring_object_id=token_ring_object_id,
            prefill_entrypoint=prefill_entrypoint,
            decode_entrypoint=decode_entrypoint,
        )
        self.scheduler = scheduler
        self._lane_transactions = [0] * scheduler.batch_size

    def _next_lane_transaction(self, lane: int) -> int:
        self._lane_transactions[lane] += 1
        return self._lane_transactions[lane]

    def _stage_lane_tokens(
        self, lane: int, token_ids: Sequence[int], offset: int = 0
    ) -> None:
        payload = np.asarray(token_ids, dtype=np.uint32).tobytes()
        byte_offset = int(offset) * 4
        obj = self.device.host_object(
            self.input_object_id, session=self.scheduler.sessions[lane]
        )
        if byte_offset + len(payload) > obj.size_bytes:
            raise DriverError(
                f"lane {lane} input window holds {obj.size_bytes // 4} tokens; "
                f"writing {len(token_ids)} at {offset} does not fit"
            )
        for token in token_ids:
            if not 0 <= int(token) < self.vocabulary_size:
                raise DriverError(
                    f"lane {lane} token {token} is outside the declared "
                    f"vocabulary {self.vocabulary_size}"
                )
        self.scheduler.stage_host_bytes(
            lane, self.input_object_id, byte_offset, payload
        )

    def _lane_submission(
        self,
        lane: int,
        *,
        phase: Phase,
        span_tokens: int,
        position_start: int,
        generation_index: int,
        max_new_tokens: int,
    ) -> BatchLaneSubmission:
        session = self.scheduler.sessions[lane]
        transaction = self._next_lane_transaction(lane)
        symbols = {
            **self.deployment_symbols,
            int(Symbol.SPAN_TOKENS): int(span_tokens),
            int(Symbol.POSITION_START): int(position_start),
            int(Symbol.POSITION_END): int(position_start + span_tokens),
            int(Symbol.CONTEXT_LENGTH): int(position_start + span_tokens),
            int(Symbol.PHASE): int(phase),
            int(Symbol.MAX_NEW_TOKENS): int(max_new_tokens),
            int(Symbol.BATCH): self.scheduler.batch_size,
            int(Symbol.GENERATION_INDEX): int(generation_index),
            int(Symbol.SPAN_LAST_INDEX): int(span_tokens - 1),
        }
        record = self._prepare_submission(
            session,
            transaction=transaction,
            entrypoint=(
                self.prefill_entrypoint
                if phase is Phase.PREFILL
                else self.decode_entrypoint
            ),
            symbols=symbols,
            phase=phase,
        )
        return BatchLaneSubmission(lane_index=lane, record=record)

    def generate_batch(
        self,
        requests: Sequence[BatchGenerationRequest],
        *,
        progress: Callable[[int, int, int], None] | None = None,
    ) -> BatchGenerationResult:
        """Execute one heterogeneous batch through device terminal reasons."""

        started = time.perf_counter()
        rows = tuple(requests)
        if len(rows) != self.scheduler.batch_size:
            raise DriverError(
                f"request count {len(rows)} does not match physical batch "
                f"{self.scheduler.batch_size}"
            )
        if len({row.sequence_id for row in rows}) != len(rows):
            raise DriverError("batch sequence_id values must be unique")
        policy_limit = int(self.policy["max_new_tokens"])
        for lane, row in enumerate(rows):
            if not row.sequence_id:
                raise DriverError(f"lane {lane} has an empty sequence_id")
            if not row.prompt_token_ids:
                raise DriverError(f"lane {lane} prompt is empty")
            if not 1 <= int(row.max_new_tokens) <= policy_limit:
                raise DriverError(
                    f"lane {lane} max_new_tokens={row.max_new_tokens} is outside "
                    f"the generation-policy bound 1..{policy_limit}"
                )

        prompts = [tuple(int(token) for token in row.prompt_token_ids) for row in rows]
        generated: list[list[int]] = [[] for _ in rows]
        per_step: list[list[dict[str, Any]]] = [[] for _ in rows]
        counters: list[dict[str, int]] = [{} for _ in rows]
        lane_wall_seconds = [0.0] * len(rows)
        failures: list[str | None] = [None] * len(rows)
        common_request_start = int(self.device._device_cycle)

        for lane, prompt in enumerate(prompts):
            self._stage_lane_tokens(lane, prompt)
        prefill = self.scheduler.submit_wave(
            [
                self._lane_submission(
                    lane,
                    phase=Phase.PREFILL,
                    span_tokens=len(prompt),
                    position_start=0,
                    generation_index=0,
                    max_new_tokens=rows[lane].max_new_tokens,
                )
                for lane, prompt in enumerate(prompts)
            ]
        )
        self._record_batch_wave(
            prefill,
            generated=generated,
            per_step=per_step,
            counters=counters,
            lane_wall_seconds=lane_wall_seconds,
            failures=failures,
            progress=progress,
            limits=[row.max_new_tokens for row in rows],
        )

        while any(self.scheduler.active):
            active = [
                lane for lane, is_active in enumerate(self.scheduler.active) if is_active
            ]
            submissions: list[BatchLaneSubmission] = []
            for lane in active:
                if not generated[lane]:
                    raise DriverError(
                        f"lane {lane} prefill produced no token to decode from"
                    )
                if len(generated[lane]) >= rows[lane].max_new_tokens:
                    raise DriverError(
                        f"lane {lane} reached request cap "
                        f"{rows[lane].max_new_tokens} without a device terminal reason"
                    )
                self._stage_lane_tokens(lane, [generated[lane][-1]])
                position = len(prompts[lane]) + len(generated[lane]) - 1
                submissions.append(
                    self._lane_submission(
                        lane,
                        phase=Phase.DECODE,
                        span_tokens=1,
                        position_start=position,
                        generation_index=len(generated[lane]),
                        max_new_tokens=rows[lane].max_new_tokens,
                    )
                )
            wave = self.scheduler.submit_wave(submissions)
            self._record_batch_wave(
                wave,
                generated=generated,
                per_step=per_step,
                counters=counters,
                lane_wall_seconds=lane_wall_seconds,
                failures=failures,
                progress=progress,
                limits=[row.max_new_tokens for row in rows],
            )

        scheduler_evidence = self.scheduler.evidence()
        request_starts = [common_request_start] * len(rows)
        for lane, sequence in enumerate(scheduler_evidence.get("sequences", ())):
            starts = sequence.get("request_start_ticks", ())
            if starts:
                request_starts[lane] = int(starts[0])

        sequences: list[BatchSequenceResult] = []
        for lane, row in enumerate(rows):
            reason = int(self.scheduler.history[lane].eos_reason)
            if reason == int(EosReason.OFFICIAL_EOS):
                stop_reason = "eos"
                eos_token = generated[lane][-1] if generated[lane] else None
            elif reason == int(EosReason.MAX_NEW_TOKENS):
                stop_reason = "max_new_tokens"
                eos_token = None
            else:
                stop_reason = "failed"
                eos_token = None
                failures[lane] = failures[lane] or (
                    "lane retired without OFFICIAL_EOS or MAX_NEW_TOKENS"
                )
            sequences.append(
                BatchSequenceResult(
                    lane_index=lane,
                    sequence_id=row.sequence_id,
                    generation=GenerationResult(
                        prompt_token_ids=prompts[lane],
                        generated_token_ids=tuple(generated[lane]),
                        stop_reason=stop_reason,
                        eos_token_id=eos_token,
                        transactions=len(per_step[lane]),
                        prefill_tokens=len(prompts[lane]),
                        decode_steps=max(0, len(per_step[lane]) - 1),
                        counters=dict(sorted(counters[lane].items())),
                        request_start_tick=request_starts[lane],
                        per_step=per_step[lane],
                        wall_seconds=lane_wall_seconds[lane],
                        failure=failures[lane],
                    ),
                )
            )
        return BatchGenerationResult(
            batch_execution_id=self.scheduler.batch_execution_id,
            physical_batch_size=self.scheduler.batch_size,
            sequences=tuple(sequences),
            waves=tuple(wave.to_dict() for wave in self.scheduler.waves),
            scheduler_evidence=scheduler_evidence,
            wall_seconds=time.perf_counter() - started,
        )

    @staticmethod
    def _record_batch_wave(
        wave: Any,
        *,
        generated: list[list[int]],
        per_step: list[list[dict[str, Any]]],
        counters: list[dict[str, int]],
        lane_wall_seconds: list[float],
        failures: list[str | None],
        progress: Callable[[int, int, int], None] | None,
        limits: Sequence[int],
    ) -> None:
        for completion in wave.lanes:
            lane = int(completion.lane_index)
            result = completion.result
            step = len(per_step[lane])
            phase = "prefill" if step == 0 else "decode"
            per_step[lane].append(
                _step_record(step, phase, completion.completion, result)
            )
            generated[lane].extend(int(token) for token in result.produced_tokens)
            lane_wall_seconds[lane] += float(result.wall_seconds)
            for name, value in result.counters.items():
                counters[lane][name] = counters[lane].get(name, 0) + int(value)
            if int(completion.completion.status) != int(CompletionStatus.SUCCESS):
                failures[lane] = (
                    f"{phase} transaction {completion.completion.transaction_id} "
                    f"failed: {result.message}"
                )
            if progress is not None and result.produced_tokens:
                progress(lane, len(generated[lane]), int(limits[lane]))


def _declared_layer_count(notes: Mapping[str, Any]) -> tuple[int, ...]:
    """The layer count a deployment's lowering notes record, if any.

    No descriptor states it.  A ROM lowering compresses an identical stack into
    one loop body, so counting state images or loop descriptors counts bodies,
    not layers -- the DeepSeek wafer deployment carries nine state images for
    forty-three layers, and a driver that read nine there would bind a wrong
    number rather than none.  The lowering's own ``layer_runs`` record says how
    many source layers each compressed run covers, which is the fact itself; a
    deployment that records neither that nor a plain ``layer_count`` states no
    layer count, and this returns nothing rather than a guess.
    """
    for key in ("layer_count", "layers"):
        value = notes.get(key)
        if isinstance(value, int) and value > 0:
            return (value,)
    for value in notes.values():
        if not isinstance(value, Mapping):
            continue
        count = value.get("layer_count")
        if isinstance(count, int) and count > 0:
            return (count,)
        runs = value.get("layer_runs")
        if isinstance(runs, Sequence) and not isinstance(runs, (str, bytes)):
            covered = sum(
                int(run.get("layers_covered", 0))
                for run in runs
                if isinstance(run, Mapping)
            )
            if covered > 0:
                return (covered,)
    return ()


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
        # This is the timestamp carried by the decoded 128-byte ABI 3.0
        # completion record, not host wall time.  Retaining it is what lets a
        # later TPOT gate prove that its raw token-commit ticks came from the
        # same transactions that produced the accepted token IDs.
        "completion_timestamp": completion.completion_timestamp,
        "instructions_retired": result.retired,
        "instructions_predicated_off": result.predicated_off,
        "wall_seconds": round(result.wall_seconds, 6),
        "host_performance": result.host_performance,
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
