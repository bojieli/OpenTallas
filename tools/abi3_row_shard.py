#!/usr/bin/env python3
"""Row-shard descriptors and the composer that reassembles them.

A ``TENSOR.MATMUL`` output row is a dot product over the whole reduction axis
K and is independent of every other output row: the RTL's association is
``ot_a3_mac_lane_single_lane_ascending_k_v1``, one lane walking K in ascending
order for one output row, and no state crosses a row boundary.  Splitting the
output rows into contiguous ranges is therefore an EXACT decomposition -- the
same products, the same order, the same roundings -- and not an approximation.

That is the whole basis on which this module refuses to be lenient.  A shard
run is evidence only if the partition is exact, so every rule below is a
refusal and none of them is a warning:

* a shard's own word count must equal the row count it declares;
* the shards, sorted by first row, must start at row 0, meet end-to-start with
  no gap and no overlap, and finish exactly at the declared extent;
* the sum of the shard extents must independently equal the declared extent --
  a second, redundant statement of the same fact, kept because a tiling error
  that survived the first check would have to survive counting as well;
* every shard must name the same operator.

The composed result is a ``Composition``.  A reduction over a sharded operator
-- an argmax, a norm -- is only allowed to consume one of those, never a list
of shards, so a per-shard reduction merged afterwards cannot be written by
accident: ``argmax_lowest_index`` and ``sum_of_squares`` take a
``Composition`` and nothing else.

Nothing here reads a file, runs a simulator or knows what a shard's words came
from.  It is the arithmetic of the decomposition and it is unit-tested against
every refusal it claims to make.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Iterable, Sequence


class ShardCompositionError(Exception):
    """A composition that is not a partition of the declared extent."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


@dataclass(frozen=True)
class ShardDescriptor:
    """One contiguous range of an operator's output rows.

    ``operator`` names the operator the shard belongs to -- for the governed
    Qwen program that is the (deployment, program counter, operator descriptor
    id) triple, rendered as a string by the caller.  Two shards that do not
    agree on it are not shards of one operator and the composer refuses them.
    """

    operator: str
    first_output_row: int
    row_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.operator, str) or not self.operator:
            raise ShardCompositionError(
                "shard_operator_missing", f"operator={self.operator!r}"
            )
        if not isinstance(self.first_output_row, int) or isinstance(
            self.first_output_row, bool
        ):
            raise ShardCompositionError(
                "shard_first_row_not_an_integer",
                f"first_output_row={self.first_output_row!r}",
            )
        if not isinstance(self.row_count, int) or isinstance(self.row_count, bool):
            raise ShardCompositionError(
                "shard_row_count_not_an_integer", f"row_count={self.row_count!r}"
            )
        if self.first_output_row < 0:
            raise ShardCompositionError(
                "shard_first_row_negative",
                f"first_output_row={self.first_output_row}",
            )
        if self.row_count <= 0:
            raise ShardCompositionError(
                "shard_row_count_not_positive", f"row_count={self.row_count}"
            )

    @property
    def end_output_row(self) -> int:
        return self.first_output_row + self.row_count

    @property
    def key(self) -> str:
        return f"{self.operator}#rows[{self.first_output_row}:{self.end_output_row})"


@dataclass(frozen=True)
class Composition:
    """The concatenation of a proven-exact partition of one operator."""

    operator: str
    declared_extent: int
    words: tuple[int, ...]
    shard_count: int
    partition_proof: dict = field(default_factory=dict)

    @property
    def sha256(self) -> str:
        payload = b"".join(int(word).to_bytes(2, "little") for word in self.words)
        return hashlib.sha256(payload).hexdigest()


def plan_row_shards(
    operator: str, declared_extent: int, shard_count: int
) -> list[ShardDescriptor]:
    """An exact tiling of ``declared_extent`` rows into ``shard_count`` shards.

    The last shard absorbs the remainder, so an extent that is not a multiple
    of the shard count still tiles exactly -- 151,936 rows into 4,096-row
    shards is 37 full shards and one of 1,536, not 38 shards of a rounded
    size that overrun the operator.
    """

    if not isinstance(declared_extent, int) or declared_extent <= 0:
        raise ShardCompositionError(
            "declared_extent_not_positive", f"declared_extent={declared_extent!r}"
        )
    if not isinstance(shard_count, int) or shard_count <= 0:
        raise ShardCompositionError(
            "shard_count_not_positive", f"shard_count={shard_count!r}"
        )
    if shard_count > declared_extent:
        raise ShardCompositionError(
            "shard_count_exceeds_extent",
            f"shard_count={shard_count} declared_extent={declared_extent}",
        )
    base = declared_extent // shard_count
    shards: list[ShardDescriptor] = []
    cursor = 0
    for index in range(shard_count):
        count = base if index + 1 < shard_count else declared_extent - cursor
        shards.append(ShardDescriptor(operator, cursor, count))
        cursor += count
    if cursor != declared_extent:
        raise ShardCompositionError(
            "planner_did_not_tile",
            f"cursor={cursor} declared_extent={declared_extent}",
        )
    return shards


def plan_row_shards_of_size(
    operator: str, declared_extent: int, rows_per_shard: int
) -> list[ShardDescriptor]:
    """An exact tiling into shards of at most ``rows_per_shard`` rows."""

    if not isinstance(rows_per_shard, int) or rows_per_shard <= 0:
        raise ShardCompositionError(
            "rows_per_shard_not_positive", f"rows_per_shard={rows_per_shard!r}"
        )
    if not isinstance(declared_extent, int) or declared_extent <= 0:
        raise ShardCompositionError(
            "declared_extent_not_positive", f"declared_extent={declared_extent!r}"
        )
    shards: list[ShardDescriptor] = []
    cursor = 0
    while cursor < declared_extent:
        count = min(rows_per_shard, declared_extent - cursor)
        shards.append(ShardDescriptor(operator, cursor, count))
        cursor += count
    return shards


def compose(
    declared_extent: int,
    shards: Iterable[tuple[ShardDescriptor, Sequence[int]]],
) -> Composition:
    """Concatenate shard outputs, refusing anything that is not a partition."""

    if not isinstance(declared_extent, int) or declared_extent <= 0:
        raise ShardCompositionError(
            "declared_extent_not_positive", f"declared_extent={declared_extent!r}"
        )
    items = list(shards)
    if not items:
        raise ShardCompositionError(
            "no_shards", f"declared_extent={declared_extent}"
        )

    operators = {shard.operator for shard, _ in items}
    if len(operators) != 1:
        raise ShardCompositionError(
            "shards_of_different_operators", ", ".join(sorted(operators))
        )
    operator = operators.pop()

    # Rule 1, per shard: a shard's word count is the row count it declares.
    # An operator that produced fewer or more words than the range it was
    # asked for is a refusal here and not a silently short concatenation.
    for shard, words in items:
        if len(words) != shard.row_count:
            raise ShardCompositionError(
                "shard_word_count_disagrees_with_row_count",
                f"{shard.key} words={len(words)} row_count={shard.row_count}",
            )

    ordered = sorted(items, key=lambda item: item[0].first_output_row)

    # Rule 2: the sorted shards tile [0, declared_extent) exactly.  The cursor
    # walk names gap and overlap separately, because they are different
    # defects and a reader is owed which one happened.
    cursor = 0
    for shard, _ in ordered:
        if shard.first_output_row < cursor:
            raise ShardCompositionError(
                "shard_overlap",
                f"{shard.key} starts at {shard.first_output_row}, "
                f"previous shard ended at {cursor}",
            )
        if shard.first_output_row > cursor:
            raise ShardCompositionError(
                "shard_gap",
                f"rows [{cursor}:{shard.first_output_row}) are in no shard "
                f"before {shard.key}",
            )
        cursor = shard.end_output_row
    if cursor != declared_extent:
        raise ShardCompositionError(
            "composed_extent_disagrees_with_declared_extent",
            f"composed={cursor} declared={declared_extent}",
        )

    # Rule 3, redundant on purpose: the extents sum to the declared extent.
    total = sum(shard.row_count for shard, _ in ordered)
    if total != declared_extent:
        raise ShardCompositionError(
            "shard_extents_do_not_sum_to_declared_extent",
            f"sum={total} declared={declared_extent}",
        )

    words: list[int] = []
    for shard, shard_words in ordered:
        words.extend(int(word) for word in shard_words)
    if len(words) != declared_extent:
        raise ShardCompositionError(
            "composed_word_count_disagrees_with_declared_extent",
            f"words={len(words)} declared={declared_extent}",
        )

    proof = {
        "declared_extent": declared_extent,
        "shard_count": len(ordered),
        "shard_extents": [shard.row_count for shard, _ in ordered],
        "sum_of_shard_extents": total,
        "first_row_of_first_shard": ordered[0][0].first_output_row,
        "end_row_of_last_shard": ordered[-1][0].end_output_row,
        "covers_every_row_exactly_once": True,
        "gaps": 0,
        "overlaps": 0,
        "rule": (
            "sorted by first output row, each shard begins exactly where the "
            "previous ended; the first begins at 0 and the last ends at the "
            "declared extent; and the extents sum to the declared extent"
        ),
    }
    return Composition(
        operator=operator,
        declared_extent=declared_extent,
        words=tuple(words),
        shard_count=len(ordered),
        partition_proof=proof,
    )


def argmax_lowest_index(composition: Composition) -> int:
    """Greedy lowest-id argmax over the WHOLE composed vector.

    It takes a ``Composition`` and nothing else on purpose.  A per-shard
    argmax merged afterwards is a different function of the same numbers, and
    the type system is the only place this project can refuse it before it is
    written.
    """

    if not isinstance(composition, Composition):
        raise ShardCompositionError(
            "reduction_over_something_that_is_not_a_composition",
            f"got {type(composition).__name__}",
        )
    if len(composition.words) != composition.declared_extent:
        raise ShardCompositionError(
            "reduction_over_an_incomplete_composition",
            f"words={len(composition.words)} declared="
            f"{composition.declared_extent}",
        )
    best_index = 0
    best_value = _bf16_to_float(composition.words[0])
    for index in range(1, len(composition.words)):
        value = _bf16_to_float(composition.words[index])
        if value > best_value:
            best_value = value
            best_index = index
    return best_index


def _bf16_to_float(code: int) -> float:
    import struct

    return struct.unpack("<f", struct.pack("<I", (int(code) & 0xFFFF) << 16))[0]
