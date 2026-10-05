"""Fail-closed DeepSeek V4 ``sample`` reference semantics.

The pinned ``inference/model.py`` defines two materially different paths::

    if temperature == 0:
        return logits.argmax(dim=-1)
    logits = logits / max(temperature, 1e-5)
    probs = torch.softmax(logits, dim=-1, dtype=torch.float32)
    return probs.div_(torch.empty_like(probs).exponential_(1)).argmax(dim=-1)

For finite binary32 logits the zero-temperature path is fully specified here:
larger values win and an exact tie selects the smaller vocabulary index, which
is PyTorch's documented ``argmax`` first-occurrence rule.

The stochastic path is not bit-replayable from the release alone.  Its
``torch>=2.10.0`` requirement does not pin a Torch build, CUDA backend,
generator algorithm/state representation, ``exponential_`` word-to-value
mapping, softmax exponential, or reduction order.  Consequently this module
fails closed when exact PyTorch/CUDA equivalence is requested.

Callers may explicitly opt into a separate deterministic target adaptation.
That adaptation consumes immutable, caller-supplied positive finite binary32
exponential draws in row-major order.  It rounds temperature division,
max-subtraction, correctly-rounded exponential, a balanced softmax reduction,
probability division, and the exponential-race division to binary32 RNE.  It
preserves the pinned algebra and makes entropy replayable, but it never claims
bit identity with the unpinned PyTorch/CUDA implementation.

This is a functional numeric reference only.  It does not model RNG hardware,
cycles, latency, bandwidth, energy, area, routing, physical implementation,
full generation, speculative acceptance, or accelerator performance.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from fractions import Fraction
import hashlib
from typing import TypeAlias

from .formats import (
    NumericReferenceError,
    binary32_balanced_sum,
    binary32_divide,
    decode_binary32,
    encode_binary32_rne,
)
from .transcendental import (
    TranscendentalReferenceError,
    binary32_exp_general_rne,
)


MODEL_SOURCE_SHA256 = "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
GENERATION_SOURCE_SHA256 = (
    "775fcfee2344e21a7b02c73161c517763e4348b84cf2eb266353e0857b9c8812"
)
SAMPLE_SOURCE_SHA256 = (
    "da6030c7ebf858d615fcdf6b7efb88b5a98f53849b98ffc0815b4eccd467955a"
)
REQUIREMENTS_SOURCE_SHA256 = (
    "857e0b8b58e41cabe16e55bf4ab7ff791677c53b25f0f3e104ef85227cd11eab"
)
OFFICIAL_REPOSITORY = "deepseek-ai/DeepSeek-V4-Flash-0731"
OFFICIAL_REVISION = "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
SAMPLE_SOURCE_ANCHOR = "inference/model.py:939-946:sample"
LOGIT_DTYPE_SOURCE_ANCHOR = "inference/model.py:719-740:ParallelHead"
REQUIREMENTS_SOURCE_ANCHOR = "inference/requirements.txt:1"
RNG_SEED_SOURCE_ANCHOR = "inference/generate.py:79:torch.manual_seed"

DEEPSEEK_V4_VOCABULARY_SIZE = 129_280
DEEPSEEK_V4_MAX_BATCH_SIZE = 4
OFFICIAL_RNG_SEED = 33_377_335
BINARY32_BYTES = 4
BINARY32_ONE = 0x3F800000
BINARY32_MINIMUM_TEMPERATURE = 0x3727C5AC

GREEDY_NUMERIC_PROFILE = "finite_binary32_first_index_argmax_v1"
TARGET_STOCHASTIC_NUMERIC_PROFILE = (
    "cr32_exp_balanced_softmax_explicit_binary32_exponential_race_v1"
)
PYTORCH_STOCHASTIC_EQUIVALENCE = (
    "unresolved_unpinned_torch_cuda_rng_exponential_softmax_backend"
)
TIE_POLICY = "maximum_value_then_smallest_vocabulary_index"
ENTROPY_ORDER = "row_major_batch_then_vocabulary"

SOURCE_EQUIVALENCE_BOUNDARY = (
    "Greedy finite-binary32 argmax is exact for the pinned source expression.",
    "Nonzero-temperature source replay is blocked because the release pins only torch>=2.10.0, not a Torch/CUDA build or generator state contract.",
    "The pinned launcher calls torch.manual_seed(33377335), but the deterministic target profile consumes post-exponential binary32 draws and does not derive them from that seed or claim the backend's RNG mapping.",
    "The target softmax freezes correctly-rounded binary32 exponentials and a balanced reduction; the pinned source does not freeze its CUDA softmax implementation.",
)

NONCLAIMS = (
    "No bit-exact PyTorch/CUDA stochastic replay claim.",
    "No implicit host randomness, wall-clock state, or process-global RNG use.",
    "Caller-supplied exponential draws establish replay identity, not statistical distribution or RNG-quality evidence.",
    "No top-p filtering, generation-loop, DSpark verification, or speculative-acceptance claim.",
    "Functional counters are not cycles, latency, throughput, bandwidth, energy, area, routing, or PPA.",
    "No full-model correctness or accelerator-comparison claim.",
)

Binary32Row: TypeAlias = tuple[int, ...]
Binary32Matrix: TypeAlias = tuple[Binary32Row, ...]


class SamplingReferenceError(ValueError):
    """Raised when sampling inputs or numeric execution poison the transaction."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise SamplingReferenceError(f"{label} must be a sequence")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise SamplingReferenceError(
            f"{label} must be an integer in {minimum}..{maximum}"
        )
    return value


def _finite_binary32(value: object, label: str) -> tuple[int, Fraction]:
    if type(value) is not int or not 0 <= value < 1 << 32:
        raise SamplingReferenceError(
            f"{label} must be an exact 32-bit binary32 encoding"
        )
    try:
        decoded = decode_binary32(value)
    except NumericReferenceError as exc:  # pragma: no cover - range checked above
        raise SamplingReferenceError(
            f"{label} must be an exact 32-bit binary32 encoding"
        ) from exc
    if not decoded.finite or decoded.value is None:
        raise SamplingReferenceError(f"{label} must be finite binary32")
    return value, decoded.value


def _positive_binary32(value: object, label: str) -> int:
    code, decoded = _finite_binary32(value, label)
    if decoded <= 0:
        raise SamplingReferenceError(f"{label} must be positive finite binary32")
    return code


def _codes_sha256(
    codes: Sequence[int],
    *,
    rows: int,
    columns: int,
    domain: bytes,
) -> str:
    digest = hashlib.sha256()
    digest.update(domain)
    digest.update(rows.to_bytes(8, "little"))
    digest.update(columns.to_bytes(8, "little"))
    for code in codes:
        digest.update(code.to_bytes(4, "little"))
    return digest.hexdigest()


def _sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise SamplingReferenceError(f"{label} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True)
class ExplicitExponentialEntropy:
    """Immutable row-major stream of post-``exponential_(1)`` binary32 draws.

    This is deliberately not a seed-based generator.  The official release
    does not define how a seed and CUDA generator state map to its exponential
    tensor.  Supplying those post-transform draws makes the target adaptation
    deterministic without pretending to reproduce the missing backend contract.
    """

    binary32_codes: tuple[int, ...]
    offset: int = 0

    def __post_init__(self) -> None:
        if type(self.binary32_codes) is not tuple:
            raise SamplingReferenceError(
                "entropy binary32_codes must be an immutable tuple"
            )
        for index, code in enumerate(self.binary32_codes):
            _positive_binary32(code, f"entropy binary32_codes[{index}]")
        _integer(
            self.offset,
            "entropy offset",
            minimum=0,
            maximum=len(self.binary32_codes),
        )

    @classmethod
    def from_codes(cls, binary32_codes: Sequence[int]) -> ExplicitExponentialEntropy:
        """Copy one explicit sequence into an immutable validated stream."""

        raw = _sequence(binary32_codes, "entropy binary32_codes")
        return cls(tuple(raw))

    @property
    def remaining(self) -> int:
        return len(self.binary32_codes) - self.offset

    @property
    def stream_sha256(self) -> str:
        return _codes_sha256(
            self.binary32_codes,
            rows=1,
            columns=len(self.binary32_codes),
            domain=b"opentallas.explicit_exponential_entropy.v1\x00",
        )

    def take(self, count: int) -> tuple[tuple[int, ...], ExplicitExponentialEntropy]:
        """Functionally consume exactly ``count`` draws or fail unchanged."""

        count = _integer(
            count,
            "entropy draw count",
            minimum=0,
            maximum=(1 << 63) - 1,
        )
        stop = self.offset + count
        if stop > len(self.binary32_codes):
            raise SamplingReferenceError(
                f"explicit exponential entropy exhausted: need {count}, "
                f"have {self.remaining}"
            )
        return self.binary32_codes[self.offset : stop], replace(self, offset=stop)


@dataclass(frozen=True)
class SamplingFunctionalCounters:
    """Source-visible work only; these fields are never timing or PPA."""

    rows: int
    vocabulary_values: int
    logit_read_bytes: int
    temperature_zero_comparisons: int
    temperature_floor_comparisons: int
    temperature_divides: int
    softmax_max_comparisons: int
    softmax_subtracts: int
    softmax_exp_evaluations: int
    softmax_reduction_adds: int
    softmax_padding_values: int
    probability_divides: int
    exponential_draws_consumed: int
    entropy_read_bytes: int
    exponential_race_divides: int
    argmax_comparisons: int
    token_writes: int

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise SamplingReferenceError(
                    f"sampling counter {name} must be an exact nonnegative integer"
                )
        if not 1 <= self.rows <= DEEPSEEK_V4_MAX_BATCH_SIZE:
            raise SamplingReferenceError(
                f"sampling counter rows must be in 1..{DEEPSEEK_V4_MAX_BATCH_SIZE}"
            )
        if self.vocabulary_values < self.rows or self.vocabulary_values % self.rows:
            raise SamplingReferenceError(
                "sampling counter vocabulary_values must describe equal nonempty rows"
            )
        vocabulary_size = self.vocabulary_values // self.rows
        if vocabulary_size > DEEPSEEK_V4_VOCABULARY_SIZE:
            raise SamplingReferenceError(
                "sampling counter vocabulary width exceeds the official profile"
            )
        reduction_adds, padding_values = _balanced_reduction_work(vocabulary_size)
        common = {
            "rows": self.rows,
            "vocabulary_values": self.vocabulary_values,
            "logit_read_bytes": self.vocabulary_values * BINARY32_BYTES,
            "temperature_zero_comparisons": 1,
            "argmax_comparisons": self.vocabulary_values - self.rows,
            "token_writes": self.rows,
        }
        if self.exponential_draws_consumed == 0:
            expected = {
                **common,
                "temperature_floor_comparisons": 0,
                "temperature_divides": 0,
                "softmax_max_comparisons": 0,
                "softmax_subtracts": 0,
                "softmax_exp_evaluations": 0,
                "softmax_reduction_adds": 0,
                "softmax_padding_values": 0,
                "probability_divides": 0,
                "exponential_draws_consumed": 0,
                "entropy_read_bytes": 0,
                "exponential_race_divides": 0,
            }
        else:
            expected = {
                **common,
                "temperature_floor_comparisons": 1,
                "temperature_divides": self.vocabulary_values,
                "softmax_max_comparisons": self.vocabulary_values - self.rows,
                "softmax_subtracts": self.vocabulary_values,
                "softmax_exp_evaluations": self.vocabulary_values,
                "softmax_reduction_adds": self.rows * reduction_adds,
                "softmax_padding_values": self.rows * padding_values,
                "probability_divides": self.vocabulary_values,
                "exponential_draws_consumed": self.vocabulary_values,
                "entropy_read_bytes": self.vocabulary_values * BINARY32_BYTES,
                "exponential_race_divides": self.vocabulary_values,
            }
        observed = {name: getattr(self, name) for name in self.__dataclass_fields__}
        if observed != expected:
            raise SamplingReferenceError(
                "sampling functional counters do not reconcile to one exact profile"
            )


@dataclass(frozen=True)
class SamplingResult:
    """Immutable tokens, provenance, entropy continuation, and functional work."""

    token_ids: tuple[int, ...]
    batch_size: int
    vocabulary_size: int
    mode: str
    status: str
    source_equivalence: str
    numeric_profile: str
    tie_policy: str
    temperature_binary32: int
    effective_temperature_binary32: int | None
    logits_sha256: str
    probabilities_sha256: str | None
    race_scores_sha256: str | None
    entropy_stream_sha256: str | None
    entropy_offset_before: int | None
    entropy_offset_after: int | None
    next_entropy: ExplicitExponentialEntropy | None
    counters: SamplingFunctionalCounters
    source_equivalence_boundary: tuple[str, ...]
    nonclaims: tuple[str, ...]

    def __post_init__(self) -> None:
        if type(self.token_ids) is not tuple:
            raise SamplingReferenceError(
                "sampling token_ids must be an immutable tuple"
            )
        batch_size = _integer(
            self.batch_size,
            "sampling result batch_size",
            minimum=1,
            maximum=DEEPSEEK_V4_MAX_BATCH_SIZE,
        )
        vocabulary_size = _integer(
            self.vocabulary_size,
            "sampling result vocabulary_size",
            minimum=1,
            maximum=DEEPSEEK_V4_VOCABULARY_SIZE,
        )
        if len(self.token_ids) != batch_size:
            raise SamplingReferenceError(
                "sampling token_ids length must equal result batch_size"
            )
        for index, token in enumerate(self.token_ids):
            _integer(
                token,
                f"sampling token_ids[{index}]",
                minimum=0,
                maximum=vocabulary_size - 1,
            )
        if type(self.counters) is not SamplingFunctionalCounters:
            raise SamplingReferenceError(
                "sampling result counters must be exact SamplingFunctionalCounters"
            )
        if (
            self.counters.rows != batch_size
            or self.counters.vocabulary_values != batch_size * vocabulary_size
        ):
            raise SamplingReferenceError(
                "sampling result dimensions differ from its functional counters"
            )
        if self.tie_policy != TIE_POLICY:
            raise SamplingReferenceError("sampling result tie policy differs")
        if self.source_equivalence_boundary != SOURCE_EQUIVALENCE_BOUNDARY:
            raise SamplingReferenceError(
                "sampling result source-equivalence boundary differs"
            )
        if self.nonclaims != NONCLAIMS:
            raise SamplingReferenceError("sampling result nonclaims differ")
        _sha256(self.logits_sha256, "sampling result logits_sha256")
        temperature_code, temperature_value = _finite_binary32(
            self.temperature_binary32,
            "sampling result temperature_binary32",
        )

        if self.mode == "greedy_argmax":
            if (
                temperature_value != 0
                or self.status != "pinned_source_greedy_exact"
                or self.source_equivalence
                != "bit_exact_for_validated_finite_binary32_inputs"
                or self.numeric_profile != GREEDY_NUMERIC_PROFILE
                or self.effective_temperature_binary32 is not None
                or self.probabilities_sha256 is not None
                or self.race_scores_sha256 is not None
                or self.counters.exponential_draws_consumed != 0
            ):
                raise SamplingReferenceError(
                    "greedy sampling result metadata or numeric profile differs"
                )
        elif self.mode == "explicit_exponential_race_target_adaptation":
            minimum = decode_binary32(BINARY32_MINIMUM_TEMPERATURE).value
            if minimum is None:  # pragma: no cover - frozen constant
                raise RuntimeError("minimum temperature constant became nonfinite")
            expected_effective = (
                BINARY32_MINIMUM_TEMPERATURE
                if temperature_value < minimum
                else temperature_code
            )
            if (
                temperature_value == 0
                or self.status != "deterministic_target_adaptation_executed"
                or self.source_equivalence != PYTORCH_STOCHASTIC_EQUIVALENCE
                or self.numeric_profile != TARGET_STOCHASTIC_NUMERIC_PROFILE
                or self.effective_temperature_binary32 != expected_effective
                or self.counters.exponential_draws_consumed
                != batch_size * vocabulary_size
            ):
                raise SamplingReferenceError(
                    "stochastic target result metadata or numeric profile differs"
                )
            _sha256(
                self.probabilities_sha256,
                "sampling result probabilities_sha256",
            )
            _sha256(
                self.race_scores_sha256,
                "sampling result race_scores_sha256",
            )
        else:
            raise SamplingReferenceError("sampling result mode is unsupported")

        if self.next_entropy is None:
            if any(
                value is not None
                for value in (
                    self.entropy_stream_sha256,
                    self.entropy_offset_before,
                    self.entropy_offset_after,
                )
            ):
                raise SamplingReferenceError(
                    "sampling result entropy metadata exists without a continuation"
                )
            if self.mode != "greedy_argmax":
                raise SamplingReferenceError(
                    "stochastic target result lacks its entropy continuation"
                )
            return
        if type(self.next_entropy) is not ExplicitExponentialEntropy:
            raise SamplingReferenceError(
                "sampling result entropy continuation has the wrong type"
            )
        entropy_digest = _sha256(
            self.entropy_stream_sha256,
            "sampling result entropy_stream_sha256",
        )
        before = _integer(
            self.entropy_offset_before,
            "sampling result entropy_offset_before",
            minimum=0,
            maximum=len(self.next_entropy.binary32_codes),
        )
        after = _integer(
            self.entropy_offset_after,
            "sampling result entropy_offset_after",
            minimum=0,
            maximum=len(self.next_entropy.binary32_codes),
        )
        expected_consumption = self.counters.exponential_draws_consumed
        if (
            entropy_digest != self.next_entropy.stream_sha256
            or self.next_entropy.offset != after
            or after != before + expected_consumption
        ):
            raise SamplingReferenceError(
                "sampling result entropy continuation does not reconcile atomically"
            )


def _finite_logits(
    value: object,
    *,
    vocabulary_size: int,
) -> Binary32Matrix:
    raw_rows = _sequence(value, "logits_binary32_codes")
    if not 1 <= len(raw_rows) <= DEEPSEEK_V4_MAX_BATCH_SIZE:
        raise SamplingReferenceError(
            "logits_binary32_codes batch size must be in "
            f"1..{DEEPSEEK_V4_MAX_BATCH_SIZE}"
        )
    rows: list[Binary32Row] = []
    for row_index, raw_row in enumerate(raw_rows):
        row = _sequence(raw_row, f"logits_binary32_codes[{row_index}]")
        if len(row) != vocabulary_size:
            raise SamplingReferenceError(
                f"logits_binary32_codes[{row_index}] has width {len(row)}, "
                f"expected {vocabulary_size}"
            )
        rows.append(
            tuple(
                _finite_binary32(
                    code,
                    f"logits_binary32_codes[{row_index}][{column}]",
                )[0]
                for column, code in enumerate(row)
            )
        )
    return tuple(rows)


def _first_argmax(row: Binary32Row) -> int:
    best_index = 0
    best = decode_binary32(row[0]).value
    if best is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("finite argmax input became nonfinite")
    for index in range(1, len(row)):
        candidate = decode_binary32(row[index]).value
        if candidate is None:  # pragma: no cover - public validation invariant
            raise RuntimeError("finite argmax input became nonfinite")
        if candidate > best:
            best = candidate
            best_index = index
    return best_index


def _balanced_reduction_work(value_count: int) -> tuple[int, int]:
    """Return exact additions and zero pads used by ``binary32_balanced_sum``."""

    additions = 0
    padding_values = 0
    level_width = value_count
    while level_width > 1:
        if level_width & 1:
            level_width += 1
            padding_values += 1
        level_width //= 2
        additions += level_width
    return additions, padding_values


def _subtract_binary32(left_code: int, right_value: Fraction) -> int:
    left = decode_binary32(left_code).value
    if left is None:  # pragma: no cover - public validation invariant
        raise RuntimeError("finite subtraction input became nonfinite")
    return encode_binary32_rne(left - right_value)


def _target_stochastic_row(
    row: Binary32Row,
    draws: tuple[int, ...],
    *,
    effective_temperature: int,
    row_index: int,
) -> tuple[int, tuple[int, ...], tuple[int, ...]]:
    try:
        scaled = tuple(binary32_divide(code, effective_temperature) for code in row)
    except NumericReferenceError as exc:
        raise SamplingReferenceError(
            f"temperature division poisoned stochastic row {row_index}: {exc}"
        ) from exc

    scaled_values = tuple(decode_binary32(code).value for code in scaled)
    if any(value is None for value in scaled_values):  # pragma: no cover
        raise RuntimeError("finite scaled logits became nonfinite")
    row_max = max(value for value in scaled_values if value is not None)
    try:
        shifted = tuple(_subtract_binary32(code, row_max) for code in scaled)
        exponentials = tuple(binary32_exp_general_rne(code) for code in shifted)
        denominator = binary32_balanced_sum(exponentials)
        probabilities = tuple(
            binary32_divide(code, denominator) for code in exponentials
        )
        race_scores = tuple(
            binary32_divide(probability, draw)
            for probability, draw in zip(probabilities, draws, strict=True)
        )
    except (NumericReferenceError, TranscendentalReferenceError) as exc:
        raise SamplingReferenceError(
            f"deterministic target softmax/race poisoned row {row_index}: {exc}"
        ) from exc
    return _first_argmax(race_scores), probabilities, race_scores


def deepseek_v4_sample_binary32(
    logits_binary32_codes: Sequence[Sequence[int]],
    temperature_binary32: int,
    *,
    entropy: ExplicitExponentialEntropy | None = None,
    vocabulary_size: int = DEEPSEEK_V4_VOCABULARY_SIZE,
    require_pytorch_cuda_equivalence: bool = True,
) -> SamplingResult:
    """Execute pinned greedy semantics or an explicit stochastic adaptation.

    ``require_pytorch_cuda_equivalence`` defaults to ``True``.  Therefore a
    nonzero-temperature call fails unless the caller deliberately opts into the
    separately named target profile by passing ``False`` and an immutable
    :class:`ExplicitExponentialEntropy` stream.  No code path reads implicit
    host entropy or mutates caller state.

    ``vocabulary_size`` defaults to the official 129,280-token graph profile.
    A smaller explicit value supports independent scalar/reference tests while
    retaining the exact same rank-2 and row-width checks.
    """

    vocabulary_size = _integer(
        vocabulary_size,
        "vocabulary_size",
        minimum=1,
        maximum=DEEPSEEK_V4_VOCABULARY_SIZE,
    )
    if type(require_pytorch_cuda_equivalence) is not bool:
        raise SamplingReferenceError(
            "require_pytorch_cuda_equivalence must be an exact bool"
        )
    temperature_code, temperature_value = _finite_binary32(
        temperature_binary32,
        "temperature_binary32",
    )
    logits = _finite_logits(
        logits_binary32_codes,
        vocabulary_size=vocabulary_size,
    )
    row_count = len(logits)
    value_count = row_count * vocabulary_size
    logits_digest = _codes_sha256(
        tuple(code for row in logits for code in row),
        rows=row_count,
        columns=vocabulary_size,
        domain=b"opentallas.deepseek_v4_sample_logits.v1\x00",
    )
    if entropy is not None and type(entropy) is not ExplicitExponentialEntropy:
        raise SamplingReferenceError(
            "entropy must be an exact ExplicitExponentialEntropy stream or None"
        )
    entropy_digest = entropy.stream_sha256 if entropy is not None else None
    entropy_before = entropy.offset if entropy is not None else None

    if temperature_value == 0:
        tokens = tuple(_first_argmax(row) for row in logits)
        counters = SamplingFunctionalCounters(
            rows=row_count,
            vocabulary_values=value_count,
            logit_read_bytes=value_count * BINARY32_BYTES,
            temperature_zero_comparisons=1,
            temperature_floor_comparisons=0,
            temperature_divides=0,
            softmax_max_comparisons=0,
            softmax_subtracts=0,
            softmax_exp_evaluations=0,
            softmax_reduction_adds=0,
            softmax_padding_values=0,
            probability_divides=0,
            exponential_draws_consumed=0,
            entropy_read_bytes=0,
            exponential_race_divides=0,
            argmax_comparisons=row_count * (vocabulary_size - 1),
            token_writes=row_count,
        )
        return SamplingResult(
            token_ids=tokens,
            batch_size=row_count,
            vocabulary_size=vocabulary_size,
            mode="greedy_argmax",
            status="pinned_source_greedy_exact",
            source_equivalence="bit_exact_for_validated_finite_binary32_inputs",
            numeric_profile=GREEDY_NUMERIC_PROFILE,
            tie_policy=TIE_POLICY,
            temperature_binary32=temperature_code,
            effective_temperature_binary32=None,
            logits_sha256=logits_digest,
            probabilities_sha256=None,
            race_scores_sha256=None,
            entropy_stream_sha256=entropy_digest,
            entropy_offset_before=entropy_before,
            entropy_offset_after=entropy_before,
            next_entropy=entropy,
            counters=counters,
            source_equivalence_boundary=SOURCE_EQUIVALENCE_BOUNDARY,
            nonclaims=NONCLAIMS,
        )

    if require_pytorch_cuda_equivalence:
        raise SamplingReferenceError(
            "exact nonzero-temperature PyTorch/CUDA replay is unresolved: the "
            "pinned release does not freeze its RNG, exponential transform, or "
            "softmax backend; explicitly select the deterministic target "
            "adaptation to continue"
        )
    if type(entropy) is not ExplicitExponentialEntropy:
        raise SamplingReferenceError(
            "nonzero-temperature target sampling requires one exact "
            "ExplicitExponentialEntropy stream"
        )

    minimum_temperature_value = decode_binary32(BINARY32_MINIMUM_TEMPERATURE).value
    if minimum_temperature_value is None:  # pragma: no cover - frozen constant
        raise RuntimeError("minimum temperature constant became nonfinite")
    effective_temperature = (
        BINARY32_MINIMUM_TEMPERATURE
        if temperature_value < minimum_temperature_value
        else temperature_code
    )
    draws, next_entropy = entropy.take(value_count)
    probabilities: list[int] = []
    race_scores: list[int] = []
    tokens: list[int] = []
    for row_index, row in enumerate(logits):
        start = row_index * vocabulary_size
        stop = start + vocabulary_size
        token, row_probabilities, row_race_scores = _target_stochastic_row(
            row,
            draws[start:stop],
            effective_temperature=effective_temperature,
            row_index=row_index,
        )
        tokens.append(token)
        probabilities.extend(row_probabilities)
        race_scores.extend(row_race_scores)

    softmax_reduction_adds_per_row, softmax_padding_values_per_row = (
        _balanced_reduction_work(vocabulary_size)
    )
    counters = SamplingFunctionalCounters(
        rows=row_count,
        vocabulary_values=value_count,
        logit_read_bytes=value_count * BINARY32_BYTES,
        temperature_zero_comparisons=1,
        temperature_floor_comparisons=1,
        temperature_divides=value_count,
        softmax_max_comparisons=row_count * (vocabulary_size - 1),
        softmax_subtracts=value_count,
        softmax_exp_evaluations=value_count,
        softmax_reduction_adds=row_count * softmax_reduction_adds_per_row,
        softmax_padding_values=row_count * softmax_padding_values_per_row,
        probability_divides=value_count,
        exponential_draws_consumed=value_count,
        entropy_read_bytes=value_count * BINARY32_BYTES,
        exponential_race_divides=value_count,
        argmax_comparisons=row_count * (vocabulary_size - 1),
        token_writes=row_count,
    )
    return SamplingResult(
        token_ids=tuple(tokens),
        batch_size=row_count,
        vocabulary_size=vocabulary_size,
        mode="explicit_exponential_race_target_adaptation",
        status="deterministic_target_adaptation_executed",
        source_equivalence=PYTORCH_STOCHASTIC_EQUIVALENCE,
        numeric_profile=TARGET_STOCHASTIC_NUMERIC_PROFILE,
        tie_policy=TIE_POLICY,
        temperature_binary32=temperature_code,
        effective_temperature_binary32=effective_temperature,
        logits_sha256=logits_digest,
        probabilities_sha256=_codes_sha256(
            probabilities,
            rows=row_count,
            columns=vocabulary_size,
            domain=b"opentallas.deepseek_v4_sample_probabilities.v1\x00",
        ),
        race_scores_sha256=_codes_sha256(
            race_scores,
            rows=row_count,
            columns=vocabulary_size,
            domain=b"opentallas.deepseek_v4_sample_race_scores.v1\x00",
        ),
        entropy_stream_sha256=entropy.stream_sha256,
        entropy_offset_before=entropy.offset,
        entropy_offset_after=next_entropy.offset,
        next_entropy=next_entropy,
        counters=counters,
        source_equivalence_boundary=SOURCE_EQUIVALENCE_BOUNDARY,
        nonclaims=NONCLAIMS,
    )


__all__ = [
    "BINARY32_BYTES",
    "BINARY32_MINIMUM_TEMPERATURE",
    "BINARY32_ONE",
    "DEEPSEEK_V4_MAX_BATCH_SIZE",
    "DEEPSEEK_V4_VOCABULARY_SIZE",
    "ENTROPY_ORDER",
    "GENERATION_SOURCE_SHA256",
    "GREEDY_NUMERIC_PROFILE",
    "LOGIT_DTYPE_SOURCE_ANCHOR",
    "MODEL_SOURCE_SHA256",
    "NONCLAIMS",
    "OFFICIAL_REPOSITORY",
    "OFFICIAL_REVISION",
    "OFFICIAL_RNG_SEED",
    "PYTORCH_STOCHASTIC_EQUIVALENCE",
    "REQUIREMENTS_SOURCE_SHA256",
    "REQUIREMENTS_SOURCE_ANCHOR",
    "RNG_SEED_SOURCE_ANCHOR",
    "SAMPLE_SOURCE_SHA256",
    "SAMPLE_SOURCE_ANCHOR",
    "SOURCE_EQUIVALENCE_BOUNDARY",
    "TARGET_STOCHASTIC_NUMERIC_PROFILE",
    "TIE_POLICY",
    "ExplicitExponentialEntropy",
    "SamplingFunctionalCounters",
    "SamplingReferenceError",
    "SamplingResult",
    "deepseek_v4_sample_binary32",
]
