"""Source-equivalence proof for the ABI-3 compressor history ring.

The released ratio-four compressor presents its decode history as two
four-row groups and copies the current group into the previous group after a
pool.  That copy is not an observable model operation: an eight-row circular
history containing the last eight absolute positions reconstructs the exact
same pool operands.  Ratio 128 is the corresponding 128-row circular history.

These tests compare that physical representation with the pinned immutable
reference transition, including FP32 score-plus-APE encodings.  They exercise
fresh prefills below, at, and across a group boundary and then cross two decode
boundaries.  Only source-live raw rows are compared between boundaries; dead
slots may retain an older row, exactly as the released decode buffers do.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pytest

from runtime.reference.compression_state import (
    F32_NEGATIVE_INFINITY,
    CompressionPoolInputs,
    CompressionState,
    compress_state_update_f32,
    zero_compression_state_f32,
)
from runtime.reference.formats import binary32_add, encode_binary32_rne


F32Vector = tuple[int, ...]
F32Tensor = tuple[tuple[F32Vector, ...], ...]


def _f32(value: int) -> int:
    return encode_binary32_rne(value)


def _tensor(
    *, batches: int, start: int, length: int, width: int, base: int
) -> F32Tensor:
    return tuple(
        tuple(
            tuple(
                _f32(base + batch * 100_000 + position * width + column)
                for column in range(width)
            )
            for position in range(start, start + length)
        )
        for batch in range(batches)
    )


def _ape(ratio: int, width: int) -> tuple[F32Vector, ...]:
    return tuple(
        tuple(_f32(1 + phase * width + column) for column in range(width))
        for phase in range(ratio)
    )


def _sessions(count: int) -> tuple[str, ...]:
    return tuple(
        hashlib.sha256(f"abi3-ring-session-{lane}".encode()).hexdigest()
        for lane in range(count)
    )


@dataclass
class _RingHistory:
    """Ordinary writable-HBM form: absolute position modulo slot count."""

    ratio: int
    head_dim: int
    kv: list[list[F32Vector]]
    scores: list[list[F32Vector]]

    @classmethod
    def zero(cls, *, ratio: int, head_dim: int, batches: int) -> _RingHistory:
        coefficient = 2 if ratio == 4 else 1
        width = coefficient * head_dim
        slots = coefficient * ratio
        return cls(
            ratio=ratio,
            head_dim=head_dim,
            kv=[[(0,) * width for _ in range(slots)] for _ in range(batches)],
            scores=[
                [(F32_NEGATIVE_INFINITY,) * width for _ in range(slots)]
                for _ in range(batches)
            ],
        )

    @property
    def slots(self) -> int:
        return 2 * self.ratio if self.ratio == 4 else self.ratio

    def append(
        self,
        kv: F32Tensor,
        scores: F32Tensor,
        ape: tuple[F32Vector, ...],
        *,
        start_pos: int,
    ) -> None:
        for batch, (kv_rows, score_rows) in enumerate(zip(kv, scores, strict=True)):
            for offset, (kv_row, score_row) in enumerate(
                zip(kv_rows, score_rows, strict=True)
            ):
                absolute = start_pos + offset
                phase = absolute % self.ratio
                slot = absolute % self.slots
                self.kv[batch][slot] = kv_row
                self.scores[batch][slot] = tuple(
                    binary32_add(code, bias)
                    for code, bias in zip(score_row, ape[phase], strict=True)
                )

    def boundary_operands(self, *, end_pos: int) -> CompressionPoolInputs:
        """Reconstruct the source order at an exact completed-group boundary."""

        assert end_pos > 0 and end_pos % self.ratio == 0
        ratio = self.ratio
        if ratio == 4:
            # ring_indices_v1(modulus=8)[POSITION_END : POSITION_END + 8]
            # names the preceding group followed by the just-completed group.
            order = tuple((end_pos + offset) % self.slots for offset in range(8))
            kv_batches = []
            score_batches = []
            for batch in range(len(self.kv)):
                ordered_kv = tuple(self.kv[batch][slot] for slot in order)
                ordered_scores = tuple(self.scores[batch][slot] for slot in order)
                kv_group = tuple(
                    row[: self.head_dim] for row in ordered_kv[:ratio]
                ) + tuple(row[self.head_dim :] for row in ordered_kv[ratio:])
                score_group = tuple(
                    row[: self.head_dim] for row in ordered_scores[:ratio]
                ) + tuple(
                    row[self.head_dim :] for row in ordered_scores[ratio:]
                )
                kv_batches.append((kv_group,))
                score_batches.append((score_group,))
            return CompressionPoolInputs(tuple(kv_batches), tuple(score_batches))

        # At a ratio-128 boundary, absolute-position modulo 128 is already
        # phase order 0..127, the source reduction order.
        return CompressionPoolInputs(
            tuple((tuple(rows),) for rows in self.kv),
            tuple((tuple(rows),) for rows in self.scores),
        )


def _assert_live_rows_match(
    source: CompressionState, ring: _RingHistory, *, next_pos: int
) -> None:
    """Compare rows that can reach a future pool before being overwritten."""

    ratio = ring.ratio
    complete_groups, remainder = divmod(next_pos, ratio)
    for batch in range(len(ring.kv)):
        if ratio == 4 and complete_groups:
            previous_start = (complete_groups - 1) * ratio
            for phase in range(ratio):
                absolute = previous_start + phase
                slot = absolute % ring.slots
                assert source.kv_f32_codes[batch][phase] == ring.kv[batch][slot]
                assert (
                    source.score_f32_codes[batch][phase]
                    == ring.scores[batch][slot]
                )

        destination = ratio if ratio == 4 else 0
        current_start = complete_groups * ratio
        for phase in range(remainder):
            absolute = current_start + phase
            slot = absolute % ring.slots
            assert (
                source.kv_f32_codes[batch][destination + phase]
                == ring.kv[batch][slot]
            )
            assert (
                source.score_f32_codes[batch][destination + phase]
                == ring.scores[batch][slot]
            )


@pytest.mark.parametrize(
    ("ratio", "prefill_lengths"),
    [
        (4, (1, 3, 4, 5, 7, 8, 9)),
        (128, (1, 127, 128, 129, 255, 256)),
    ],
)
def test_circular_hbm_history_matches_source_roll_across_decode_boundaries(
    ratio: int, prefill_lengths: tuple[int, ...]
) -> None:
    batches = 2
    head_dim = 2
    coefficient = 2 if ratio == 4 else 1
    width = coefficient * head_dim
    ape = _ape(ratio, width)
    sessions = _sessions(batches)

    for prefill_length in prefill_lengths:
        source = zero_compression_state_f32(
            ratio=ratio, batch_capacity=batches, head_dim=head_dim
        )
        ring = _RingHistory.zero(
            ratio=ratio, head_dim=head_dim, batches=batches
        )
        prefill_kv = _tensor(
            batches=batches,
            start=0,
            length=prefill_length,
            width=width,
            base=1_000,
        )
        prefill_scores = _tensor(
            batches=batches,
            start=0,
            length=prefill_length,
            width=width,
            base=10_000,
        )
        prefill = compress_state_update_f32(
            source,
            prefill_kv,
            prefill_scores,
            ape,
            session_ids=sessions,
            start_pos=0,
        )
        source = prefill.state
        ring.append(prefill_kv, prefill_scores, ape, start_pos=0)
        assert prefill.should_compress == (prefill_length >= ratio)
        assert prefill.counters.complete_group_count == prefill_length // ratio
        _assert_live_rows_match(source, ring, next_pos=prefill_length)

        emitted_cache_rows = list(range(prefill_length // ratio))
        boundary_count = 0
        for position in range(prefill_length, prefill_length + 2 * ratio):
            kv = _tensor(
                batches=batches,
                start=position,
                length=1,
                width=width,
                base=1_000,
            )
            scores = _tensor(
                batches=batches,
                start=position,
                length=1,
                width=width,
                base=10_000,
            )
            result = compress_state_update_f32(
                source,
                kv,
                scores,
                ape,
                session_ids=sessions,
                start_pos=position,
            )
            source = result.state
            ring.append(kv, scores, ape, start_pos=position)
            boundary = (position + 1) % ratio == 0
            assert result.should_compress == boundary
            assert result.decode_phase == position % ratio
            if boundary:
                assert result.pool_inputs == ring.boundary_operands(
                    end_pos=position + 1
                )
                emitted_cache_rows.append(position // ratio)
                boundary_count += 1
            else:
                assert result.pool_inputs is None
            _assert_live_rows_match(source, ring, next_pos=position + 1)

        assert boundary_count == 2
        assert emitted_cache_rows == list(range(emitted_cache_rows[-1] + 1))
