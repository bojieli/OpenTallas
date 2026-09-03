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
        obj = self.device.host_object(self.input_object_id)
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
        self.device.host_write(self.input_object_id, byte_offset, payload)

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
            )
        generated.extend(result.produced_tokens)
        if result.eos_reason == EosReason.OFFICIAL_EOS:
            return self._finish(
                prompt, generated, "eos", result.selected_token, transactions,
                len(prompt), 0, per_step, started, None,
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
                "restored session already returned EOS; there is nothing to resume"
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
            self._write_input_tokens([generated[-1]], 0)
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
