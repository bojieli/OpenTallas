"""Transactional target-only generation control for DeepSeek V4 Flash.

This is an executable specification of the loop in the pinned
``inference/generate.py``. It does not execute model operators. Instead, it
issues exact prefill/decode invocations to an executor, requires an explicit
mutable-state commit and logits identity for every invocation, applies the
official prompt-token override and EOS rules, and emits a deterministic trace.

DSpark is deliberately rejected here: the pinned local generator never calls
``forward_spec``, and the release does not define target verification or
acceptance. A later speculative controller must bind an independently specified
serving implementation before that behavior can become executable evidence.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import hashlib
import json
import math
import re
from typing import Any

from compiler.frontend.deepseek_v4_tokenizer import (
    BOS_TOKEN_ID,
    EOS_TOKEN_ID,
    MODEL_MAX_LENGTH,
    VOCAB_SIZE,
)
from compiler.ir.model import canonical_json_bytes


GENERATION_SOURCE_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
OFFICIAL_RNG_SEED = 33_377_335

GENERATION_SCHEMA = "opentallas.deepseek_v4_generation_trace.v1"
INVOCATION_SCHEMA = "opentallas.deepseek_v4_model_invocation.v1"
REPLAY_SCHEMA = "opentallas.deepseek_v4_generation_replay.v1"
REQUIRED_STATE_SCOPES = (
    "main_attention_kv_all_layers",
    "main_compressor_state_all_compressed_layers",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class DeepSeekV4GenerationError(RuntimeError):
    """Raised when generation control or executor evidence is invalid."""


def _integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not minimum <= value <= maximum
    ):
        raise DeepSeekV4GenerationError(
            f"{label} must be an integer in {minimum}..{maximum}"
        )
    return value


def _sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise DeepSeekV4GenerationError(
            f"{label} must be one lowercase SHA-256 digest"
        )
    return value


def _token_ids_bytes(ids: Sequence[int]) -> bytes:
    return b"".join(token_id.to_bytes(4, "little", signed=False) for token_id in ids)


def token_ids_sha256(ids: Sequence[int]) -> str:
    """Hash a token stream as unambiguous little-endian uint32 values."""

    return hashlib.sha256(_token_ids_bytes(ids)).hexdigest()


@dataclass(frozen=True)
class GenerationConfig:
    """Explicit limits and sampling policy for one official-loop request."""

    max_batch_size: int
    max_context_tokens: int
    max_new_tokens: int
    temperature: float = 0.0
    top_p: float = 1.0
    rng_seed: int = OFFICIAL_RNG_SEED
    decode_mode: str = "target_only"
    vocab_size: int = VOCAB_SIZE
    bos_token_id: int = BOS_TOKEN_ID
    eos_token_id: int = EOS_TOKEN_ID

    def __post_init__(self) -> None:
        _integer(
            self.max_batch_size,
            "max_batch_size",
            minimum=1,
            maximum=1_000_000,
        )
        _integer(
            self.max_context_tokens,
            "max_context_tokens",
            minimum=2,
            maximum=MODEL_MAX_LENGTH,
        )
        _integer(
            self.max_new_tokens,
            "max_new_tokens",
            minimum=1,
            maximum=self.max_context_tokens,
        )
        if (
            isinstance(self.temperature, bool)
            or not isinstance(self.temperature, (int, float))
            or not math.isfinite(self.temperature)
            or self.temperature < 0
        ):
            raise DeepSeekV4GenerationError(
                "temperature must be one finite number >= 0"
            )
        if (
            isinstance(self.top_p, bool)
            or not isinstance(self.top_p, (int, float))
            or not math.isfinite(self.top_p)
            or self.top_p != 1.0
        ):
            raise DeepSeekV4GenerationError(
                "top_p must equal 1.0: pinned local generate.py has no top-p filter"
            )
        if self.rng_seed != OFFICIAL_RNG_SEED:
            raise DeepSeekV4GenerationError(
                f"rng_seed must equal pinned torch.manual_seed({OFFICIAL_RNG_SEED})"
            )
        if self.decode_mode != "target_only":
            if self.decode_mode == "dspark":
                raise DeepSeekV4GenerationError(
                    "DSpark generation is blocked: pinned generate.py never calls "
                    "forward_spec and no pinned target-verification/acceptance "
                    "algorithm exists"
                )
            raise DeepSeekV4GenerationError(
                f"unsupported decode_mode {self.decode_mode!r}"
            )
        if self.vocab_size != VOCAB_SIZE:
            raise DeepSeekV4GenerationError(
                f"vocab_size must equal official value {VOCAB_SIZE}"
            )
        if self.bos_token_id != BOS_TOKEN_ID:
            raise DeepSeekV4GenerationError(
                f"bos_token_id must equal official value {BOS_TOKEN_ID}"
            )
        if self.eos_token_id != EOS_TOKEN_ID:
            raise DeepSeekV4GenerationError(
                f"eos_token_id must equal official value {EOS_TOKEN_ID}"
            )

    @property
    def sampling_algorithm(self) -> str:
        return (
            "greedy_argmax"
            if self.temperature == 0
            else "pytorch_cuda_exponential_race"
        )

    @property
    def sampling_replay_status(self) -> str:
        return (
            "deterministic_no_rng"
            if self.temperature == 0
            else "blocked_pending_pinned_torch_cuda_rng_stack"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "bos_token_id": self.bos_token_id,
            "decode_mode": self.decode_mode,
            "eos_token_id": self.eos_token_id,
            "max_batch_size": self.max_batch_size,
            "max_context_tokens": self.max_context_tokens,
            "max_new_tokens": self.max_new_tokens,
            "rng_seed": self.rng_seed,
            "temperature": float(self.temperature),
            "top_p": float(self.top_p),
            "vocab_size": self.vocab_size,
        }


@dataclass(frozen=True)
class ModelInvocation:
    """One exact model call requested by the generation controller."""

    invocation_id: str
    request_id: str
    invocation_index: int
    phase: str
    start_pos: int
    stop_pos_exclusive: int
    candidate_position: int
    input_ids: tuple[tuple[int, ...], ...]
    prompt_override_mask: tuple[bool, ...]
    finished_before_mask: tuple[bool, ...]
    required_state_scopes: tuple[str, ...]
    sample_value_count: int

    @property
    def input_length(self) -> int:
        return self.stop_pos_exclusive - self.start_pos

    def to_dict(self, *, include_input_ids: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "candidate_position": self.candidate_position,
            "finished_before_mask": list(self.finished_before_mask),
            "input_ids_sha256": [
                token_ids_sha256(row) for row in self.input_ids
            ],
            "input_length": self.input_length,
            "invocation_id": self.invocation_id,
            "invocation_index": self.invocation_index,
            "phase": self.phase,
            "prompt_override_mask": list(self.prompt_override_mask),
            "request_id": self.request_id,
            "required_state_scopes": list(self.required_state_scopes),
            "sample_value_count": self.sample_value_count,
            "schema": INVOCATION_SCHEMA,
            "start_pos": self.start_pos,
            "stop_pos_exclusive": self.stop_pos_exclusive,
        }
        if include_input_ids:
            result["input_ids"] = [list(row) for row in self.input_ids]
        return result


def _normalize_prompts(
    prompt_tokens: Any, config: GenerationConfig
) -> tuple[tuple[int, ...], ...]:
    if isinstance(prompt_tokens, (str, bytes)) or not isinstance(
        prompt_tokens, Sequence
    ):
        raise DeepSeekV4GenerationError(
            "prompt_tokens must be a sequence of token-ID sequences"
        )
    if not prompt_tokens:
        raise DeepSeekV4GenerationError("prompt_tokens must contain at least one row")
    if len(prompt_tokens) > config.max_batch_size:
        raise DeepSeekV4GenerationError(
            f"batch has {len(prompt_tokens)} rows, exceeding "
            f"max_batch_size={config.max_batch_size}"
        )
    rows: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(prompt_tokens):
        if isinstance(raw_row, (str, bytes)) or not isinstance(raw_row, Sequence):
            raise DeepSeekV4GenerationError(
                f"prompt_tokens[{row_index}] must be a token-ID sequence"
            )
        row: list[int] = []
        for column, token_id in enumerate(raw_row):
            row.append(
                _integer(
                    token_id,
                    f"prompt_tokens[{row_index}][{column}]",
                    minimum=0,
                    maximum=config.vocab_size - 1,
                )
            )
        if not row:
            raise DeepSeekV4GenerationError(
                f"prompt_tokens[{row_index}] must not be empty"
            )
        if row[0] != config.bos_token_id:
            raise DeepSeekV4GenerationError(
                f"prompt_tokens[{row_index}] must begin with official BOS ID "
                f"{config.bos_token_id}"
            )
        if len(row) >= config.max_context_tokens:
            raise DeepSeekV4GenerationError(
                f"prompt_tokens[{row_index}] has {len(row)} tokens and leaves no "
                f"generation position in max_context_tokens={config.max_context_tokens}"
            )
        rows.append(tuple(row))
    return tuple(rows)


class DeepSeekV4GenerationController:
    """Stateful, fail-closed implementation of the pinned target-only loop."""

    def __init__(
        self, prompt_tokens: Sequence[Sequence[int]], config: GenerationConfig
    ):
        if not isinstance(config, GenerationConfig):
            raise DeepSeekV4GenerationError("config must be a GenerationConfig")
        self._config = config
        self._prompts = _normalize_prompts(prompt_tokens, config)
        self._batch_size = len(self._prompts)
        self._prompt_lengths = tuple(len(row) for row in self._prompts)
        self._minimum_prompt_length = min(self._prompt_lengths)
        self._maximum_prompt_length = max(self._prompt_lengths)
        self._total_length = min(
            config.max_context_tokens,
            config.max_new_tokens + self._maximum_prompt_length,
        )
        self._tokens: list[list[int | None]] = [
            list(row) + [None] * (self._total_length - len(row))
            for row in self._prompts
        ]
        self._previous_position = 0
        self._candidate_position = self._minimum_prompt_length
        self._finished = [False] * self._batch_size
        self._model_eos_positions: list[int | None] = [None] * self._batch_size
        self._trace: list[dict[str, Any]] = []
        self._pending: ModelInvocation | None = None
        self._last_rng_state_after: str | None = None
        self._termination: str | None = None
        self._request_id = self._build_request_id()

    @property
    def request_id(self) -> str:
        return self._request_id

    @property
    def complete(self) -> bool:
        return self._termination is not None

    @property
    def pending_invocation(self) -> ModelInvocation | None:
        return self._pending

    def _build_request_id(self) -> str:
        identity = {
            "config": self._config.to_dict(),
            "prompt_rows": [
                {
                    "length": len(row),
                    "token_ids_sha256": token_ids_sha256(row),
                }
                for row in self._prompts
            ],
            "source": {
                "generate_sha256": GENERATION_SOURCE_SHA256,
                "model_sha256": MODEL_SOURCE_SHA256,
                "repository": OFFICIAL_REPOSITORY,
                "revision": OFFICIAL_REVISION,
            },
        }
        return hashlib.sha256(canonical_json_bytes(identity)).hexdigest()

    def next_invocation(self) -> ModelInvocation | None:
        """Return the next call, or the same outstanding call until it commits."""

        if self._pending is not None:
            return self._pending
        if self.complete:
            return None
        if self._candidate_position >= self._total_length:
            self._termination = "length_limit"
            return None

        input_rows: list[tuple[int, ...]] = []
        for row_index, tokens in enumerate(self._tokens):
            raw_segment = tokens[
                self._previous_position : self._candidate_position
            ]
            if not raw_segment or any(token is None for token in raw_segment):
                raise DeepSeekV4GenerationError(
                    f"internal token state for row {row_index} is not contiguous "
                    f"over [{self._previous_position}, {self._candidate_position})"
                )
            input_rows.append(tuple(int(token) for token in raw_segment))
        override = tuple(
            self._candidate_position < prompt_length
            for prompt_length in self._prompt_lengths
        )
        descriptor = {
            "candidate_position": self._candidate_position,
            "finished_before_mask": self._finished,
            "input_ids_sha256": [
                token_ids_sha256(row) for row in input_rows
            ],
            "invocation_index": len(self._trace),
            "phase": "prefill" if self._previous_position == 0 else "decode",
            "prompt_override_mask": override,
            "request_id": self._request_id,
            "required_state_scopes": REQUIRED_STATE_SCOPES,
            "sample_value_count": (
                0
                if self._config.temperature == 0
                else self._batch_size * self._config.vocab_size
            ),
            "start_pos": self._previous_position,
            "stop_pos_exclusive": self._candidate_position,
        }
        invocation_id = hashlib.sha256(canonical_json_bytes(descriptor)).hexdigest()
        self._pending = ModelInvocation(
            invocation_id=invocation_id,
            request_id=self._request_id,
            invocation_index=len(self._trace),
            phase=descriptor["phase"],
            start_pos=self._previous_position,
            stop_pos_exclusive=self._candidate_position,
            candidate_position=self._candidate_position,
            input_ids=tuple(input_rows),
            prompt_override_mask=override,
            finished_before_mask=tuple(self._finished),
            required_state_scopes=REQUIRED_STATE_SCOPES,
            sample_value_count=descriptor["sample_value_count"],
        )
        return self._pending

    def accept_model_result(
        self,
        *,
        invocation_id: str,
        candidate_token_ids: Sequence[int],
        processed_start_pos: int,
        processed_stop_pos_exclusive: int,
        logits_sha256: str,
        state_commit_sha256: str,
        argmax_token_ids: Sequence[int] | None = None,
        rng_state_before_sha256: str | None = None,
        rng_state_after_sha256: str | None = None,
    ) -> None:
        """Atomically accept one executor result after validating its state commit."""

        invocation = self._pending
        if invocation is None:
            raise DeepSeekV4GenerationError(
                "no model invocation is pending; call next_invocation first"
            )
        if invocation_id != invocation.invocation_id:
            raise DeepSeekV4GenerationError(
                f"result invocation_id {invocation_id!r} does not match "
                f"pending {invocation.invocation_id!r}"
            )
        observed_start = _integer(
            processed_start_pos,
            "processed_start_pos",
            minimum=0,
            maximum=self._config.max_context_tokens,
        )
        observed_stop = _integer(
            processed_stop_pos_exclusive,
            "processed_stop_pos_exclusive",
            minimum=1,
            maximum=self._config.max_context_tokens,
        )
        if (
            observed_start != invocation.start_pos
            or observed_stop != invocation.stop_pos_exclusive
        ):
            raise DeepSeekV4GenerationError(
                "executor state-commit span differs from requested "
                f"[{invocation.start_pos}, {invocation.stop_pos_exclusive})"
            )
        logits_digest = _sha256(logits_sha256, "logits_sha256")
        state_digest = _sha256(state_commit_sha256, "state_commit_sha256")
        candidates = self._validate_result_ids(
            candidate_token_ids, "candidate_token_ids"
        )

        argmax: tuple[int, ...] | None = None
        before_digest: str | None = None
        after_digest: str | None = None
        if self._config.temperature == 0:
            if argmax_token_ids is None:
                raise DeepSeekV4GenerationError(
                    "greedy execution requires independently reported argmax_token_ids"
                )
            argmax = self._validate_result_ids(
                argmax_token_ids, "argmax_token_ids"
            )
            if argmax != candidates:
                raise DeepSeekV4GenerationError(
                    "greedy candidate_token_ids differ from argmax_token_ids"
                )
            if rng_state_before_sha256 is not None or rng_state_after_sha256 is not None:
                raise DeepSeekV4GenerationError(
                    "greedy execution must not report RNG state transitions"
                )
        else:
            if argmax_token_ids is not None:
                raise DeepSeekV4GenerationError(
                    "stochastic execution must not claim greedy argmax selection"
                )
            before_digest = _sha256(
                rng_state_before_sha256, "rng_state_before_sha256"
            )
            after_digest = _sha256(
                rng_state_after_sha256, "rng_state_after_sha256"
            )
            if (
                self._last_rng_state_after is not None
                and before_digest != self._last_rng_state_after
            ):
                raise DeepSeekV4GenerationError(
                    "stochastic RNG state is discontinuous between invocations"
                )

        # All validation above is side-effect free. From this point the result is
        # committed atomically into controller-visible token and trace state.
        selected: list[int] = []
        new_eos: list[bool] = []
        finished_before = tuple(self._finished)
        for row_index, candidate in enumerate(candidates):
            override = invocation.prompt_override_mask[row_index]
            token = (
                self._prompts[row_index][invocation.candidate_position]
                if override
                else candidate
            )
            self._tokens[row_index][invocation.candidate_position] = token
            selected.append(token)
            is_new_eos = (
                not override
                and not self._finished[row_index]
                and token == self._config.eos_token_id
            )
            new_eos.append(is_new_eos)
            if is_new_eos:
                self._finished[row_index] = True
                self._model_eos_positions[row_index] = invocation.candidate_position

        record: dict[str, Any] = invocation.to_dict(include_input_ids=False)
        record.update(
            {
                "argmax_token_ids": list(argmax) if argmax is not None else None,
                "candidate_token_ids": list(candidates),
                "finished_after_mask": list(self._finished),
                "logits_sha256": logits_digest,
                "new_eos_mask": new_eos,
                "rng_state_after_sha256": after_digest,
                "rng_state_before_sha256": before_digest,
                "selected_token_ids": selected,
                "state_commit_sha256": state_digest,
                "state_commit_status": "committed",
            }
        )
        self._trace.append(record)
        self._last_rng_state_after = after_digest
        self._previous_position = invocation.candidate_position
        self._candidate_position = invocation.candidate_position + 1
        self._pending = None

        if all(self._finished):
            self._termination = "all_rows_generated_eos"
        elif self._candidate_position >= self._total_length:
            self._termination = "length_limit"
        if finished_before != invocation.finished_before_mask:
            raise AssertionError("controller finished-state changed before commit")

    def _validate_result_ids(
        self, value: Any, label: str
    ) -> tuple[int, ...]:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise DeepSeekV4GenerationError(
                f"{label} must be one token-ID sequence"
            )
        if len(value) != self._batch_size:
            raise DeepSeekV4GenerationError(
                f"{label} has {len(value)} rows, expected {self._batch_size}"
            )
        return tuple(
            _integer(
                token_id,
                f"{label}[{index}]",
                minimum=0,
                maximum=self._config.vocab_size - 1,
            )
            for index, token_id in enumerate(value)
        )

    def result(self) -> dict[str, Any]:
        """Return a canonical trace after all rows or the official length bound stop."""

        if self._pending is not None:
            raise DeepSeekV4GenerationError(
                "cannot finalize while a model invocation is uncommitted"
            )
        if not self.complete:
            raise DeepSeekV4GenerationError(
                "generation is incomplete; execute the next model invocation"
            )
        sessions = [
            self._session_result(row_index)
            for row_index in range(self._batch_size)
        ]
        result: dict[str, Any] = {
            "control_scope": {
                "covered": [
                    "official target-only batch loop",
                    "prefill/decode invocation spans",
                    "prompt-token override",
                    "EOS and output-bound termination",
                    "executor mutable-state commit chaining",
                    "sampling and RNG-state provenance",
                ],
                "execution_status": (
                    "control_trace_only_pending_model_operator_execution"
                ),
                "unresolved": [
                    "logits and operator numerical correctness",
                    "DSpark target verification and speculative acceptance",
                    "stochastic replay until the exact Torch/CUDA RNG stack is pinned",
                ],
            },
            "request": {
                "batch_size": self._batch_size,
                "config": self._config.to_dict(),
                "maximum_prompt_length": self._maximum_prompt_length,
                "minimum_prompt_length": self._minimum_prompt_length,
                "prompt_rows": [
                    {
                        "length": len(row),
                        "token_ids_sha256": token_ids_sha256(row),
                    }
                    for row in self._prompts
                ],
                "request_id": self._request_id,
                "total_loop_length": self._total_length,
            },
            "sampling": {
                "algorithm": self._config.sampling_algorithm,
                "exact_replay_status": self._config.sampling_replay_status,
                "official_expression": (
                    "argmax(logits)"
                    if self._config.temperature == 0
                    else "argmax(softmax(logits/max(temperature,1e-5))/"
                    "Exponential(1))"
                ),
                "rng_seed": (
                    None
                    if self._config.temperature == 0
                    else self._config.rng_seed
                ),
            },
            "schema": GENERATION_SCHEMA,
            "sessions": sessions,
            "source": {
                "generate_sha256": GENERATION_SOURCE_SHA256,
                "model_sha256": MODEL_SOURCE_SHA256,
                "repository": OFFICIAL_REPOSITORY,
                "revision": OFFICIAL_REVISION,
            },
            "termination": self._termination,
            "trace": copy_trace(self._trace),
        }
        result["trace_id"] = hashlib.sha256(canonical_json_bytes(result)).hexdigest()
        return result

    def _session_result(self, row_index: int) -> dict[str, Any]:
        prompt_length = self._prompt_lengths[row_index]
        visible_stop = min(
            self._total_length,
            prompt_length + self._config.max_new_tokens,
        )
        raw_visible = self._tokens[row_index][prompt_length:visible_stop]
        first_unfilled = next(
            (
                index
                for index, token in enumerate(raw_visible)
                if token is None
            ),
            len(raw_visible),
        )
        visible = [int(token) for token in raw_visible[:first_unfilled]]
        if first_unfilled < len(raw_visible) and self._config.eos_token_id not in visible:
            raise DeepSeekV4GenerationError(
                f"session {row_index} has an unfilled visible completion position "
                "before a generated EOS"
            )
        if self._config.eos_token_id in visible:
            eos_index = visible.index(self._config.eos_token_id)
            completion = visible[:eos_index] + [self._config.eos_token_id]
            eos_origin = "model_generated"
            stop_reason = "eos"
        else:
            completion = visible + [self._config.eos_token_id]
            eos_origin = "host_appended_like_official_generate_py"
            stop_reason = (
                "max_context_tokens"
                if visible_stop < prompt_length + self._config.max_new_tokens
                else "max_new_tokens"
            )
        model_eos_position = self._model_eos_positions[row_index]
        committed_exclusive = self._previous_position
        model_eos_committed = (
            model_eos_position is not None
            and model_eos_position < committed_exclusive
        )
        post_eos_committed = (
            0
            if model_eos_position is None
            else max(0, committed_exclusive - model_eos_position - 1)
        )
        return {
            "completion_token_count": len(completion),
            "completion_token_ids": completion,
            "completion_token_ids_sha256": token_ids_sha256(completion),
            "eos_origin": eos_origin,
            "model_eos_committed_to_state": model_eos_committed,
            "model_eos_position": model_eos_position,
            "post_eos_positions_committed": post_eos_committed,
            "prompt_length": prompt_length,
            "row": row_index,
            "state_committed_through_exclusive": committed_exclusive,
            "stop_reason": stop_reason,
        }


def copy_trace(trace: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy a JSON-shaped trace without exposing controller-owned containers."""

    # Canonical JSON round-trip also rejects any accidental non-finite or
    # non-serializable state before the trace can become evidence.
    return json.loads(canonical_json_bytes(list(trace)))


def _exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DeepSeekV4GenerationError(f"{label} must be an object")
    missing = sorted(expected - value.keys())
    unknown = sorted(value.keys() - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing {missing!r}")
        if unknown:
            details.append(f"unknown {unknown!r}")
        raise DeepSeekV4GenerationError(f"{label} has " + "; ".join(details))
    return value


def replay_generation_control(value: Any) -> dict[str, Any]:
    """Replay executor evidence through the transactional controller.

    This command path is a control fixture and evidence verifier. It does not
    calculate logits or mutable model state; those values and their hashes must
    come from an executor and remain explicitly marked pending in the result.
    """

    document = _exact_keys(
        value,
        {"config", "model_results", "prompt_token_ids", "schema"},
        "generation replay",
    )
    if document["schema"] != REPLAY_SCHEMA:
        raise DeepSeekV4GenerationError(
            f"unsupported generation replay schema {document['schema']!r}"
        )
    config_value = _exact_keys(
        document["config"],
        {
            "bos_token_id",
            "decode_mode",
            "eos_token_id",
            "max_batch_size",
            "max_context_tokens",
            "max_new_tokens",
            "rng_seed",
            "temperature",
            "top_p",
            "vocab_size",
        },
        "generation replay config",
    )
    try:
        config = GenerationConfig(**config_value)
    except TypeError as exc:  # pragma: no cover - exact keys makes this defensive
        raise DeepSeekV4GenerationError(f"invalid generation config: {exc}") from exc
    raw_results = document["model_results"]
    if not isinstance(raw_results, list):
        raise DeepSeekV4GenerationError("model_results must be a list")
    controller = DeepSeekV4GenerationController(
        document["prompt_token_ids"], config
    )
    result_keys = {
        "argmax_token_ids",
        "candidate_token_ids",
        "invocation_id",
        "logits_sha256",
        "processed_start_pos",
        "processed_stop_pos_exclusive",
        "rng_state_after_sha256",
        "rng_state_before_sha256",
        "state_commit_sha256",
    }
    for index, raw_result in enumerate(raw_results):
        invocation = controller.next_invocation()
        if invocation is None:
            raise DeepSeekV4GenerationError(
                f"model_results[{index}] is extra after generation terminated"
            )
        result = _exact_keys(
            raw_result, result_keys, f"model_results[{index}]"
        )
        controller.accept_model_result(**result)
    if not controller.complete:
        pending = controller.next_invocation()
        assert pending is not None
        raise DeepSeekV4GenerationError(
            "model_results ended before generation completed; "
            f"missing invocation {pending.invocation_id}"
        )
    return controller.result()


__all__ = [
    "DeepSeekV4GenerationController",
    "DeepSeekV4GenerationError",
    "GENERATION_SCHEMA",
    "GENERATION_SOURCE_SHA256",
    "GenerationConfig",
    "INVOCATION_SCHEMA",
    "MODEL_SOURCE_SHA256",
    "ModelInvocation",
    "OFFICIAL_RNG_SEED",
    "REPLAY_SCHEMA",
    "REQUIRED_STATE_SCOPES",
    "replay_generation_control",
    "token_ids_sha256",
]
