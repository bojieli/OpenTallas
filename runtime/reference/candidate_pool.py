"""DeepSeek-V4.1-Flash candidate-pool reference semantics (AM-E10).

The Hierarchical Sparse Indexer of DeepSeek-V4.1-Flash does not score the whole
context on a Reindex layer.  One layer -- ``candidate_source_layer_id`` 20 in the
pinned ``config.json`` (SRC-DSV41-FLASH-CONFIG) -- reduces the index scores to
one score per block of eight positions, takes the highest-scoring blocks, and
every later Reindex layer scores *only* the positions those blocks cover:
2,048 blocks of 8, so at most 16,384 positions however long the context is.

This module is the reference for that pool.  It is derived from the pinned
sources, never from OpenTallas RTL:

* SRC-DSV41-FLASH-MODEL (``inference/model.py``, SHA-256
  ``4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65``): the
  ``Indexer`` "masks scores to the candidate pool when
  ``0 <= candidate_source_layer < layer_id``".
* SRC-DSV41-FLASH-REPORT sections 2.2-2.4: "Reindex layers score only the
  2,048-block x 8-position candidate pool".
* SRC-DSV41-FLASH-CONFIG: ``candidate_source_layer_id`` 20 with 2,048 blocks
  of 8; ``index_source_layer_ids`` [2, 8, 14, 20, 24, 28, 32, 36].

``runtime/reference/selection.py`` already fixes the tie rule that decides
*which* blocks win; this module fixes what a won block means for the position
axis, which is the part the machine has to materialise.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Mapping


#: SRC-DSV41-FLASH-MODEL, the pinned ``inference/model.py``.
CANDIDATE_MASK_MODEL_SOURCE_SHA256 = (
    "4e9ae23620edc8028ccc5d5fef552ab7fdc7dcd6f79608754fe9f67644056f65"
)
#: SRC-DSV41-FLASH-CONFIG, the pinned ``config.json``.
CANDIDATE_MASK_CONFIG_SOURCE_SHA256 = (
    "8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879"
)
#: The numeric contract this function is the reference for (plan section 6.4).
CANDIDATE_MASK_CONTRACT = "candidate_mask_v1"
#: V4.1 block size: ``candidate_source_layer_id`` 20 scores 2,048 blocks of 8.
CANDIDATE_MASK_DEFAULT_BLOCK = 8
#: V4.1 pool width in blocks, and therefore the population bound the plan's
#: ``candidate_pool_bound`` checker states: 2,048 x 8 = 16,384 positions.
CANDIDATE_MASK_DEFAULT_BLOCK_IDS = 2048
#: ABI 3.0 ``A3_NO_ID``: a top-k slot that selected nothing.  A block-score
#: vector padded to -inf still returns k indices, so the absent slot has to be
#: representable rather than guessed at.
CANDIDATE_MASK_ABSENT_ID = 0xFFFF_FFFF


class CandidateMaskError(ValueError):
    """Raised when a candidate-mask request violates the pool contract."""


def select_candidate_mask(
    block_ids: Sequence[int],
    *,
    width: int,
    block: int = CANDIDATE_MASK_DEFAULT_BLOCK,
    word_bits: int = 32,
    pin_last_block: bool = True,
    max_population: int | None = None,
    absent_id: int = CANDIDATE_MASK_ABSENT_ID,
) -> dict[str, Any]:
    """Expand chosen candidate-block ids into a per-position admission mask.

    POLARITY.  A set bit ADMITS its position: the consumer keeps the score at
    every position whose mask bit is 1 and replaces every other score with
    -inf.  The pinned indexer "masks scores to the candidate pool", and the
    plan's ``candidate_pool_bound`` checker bounds the mask's POPULATION by
    16,384 -- which is 2,048 chosen blocks x 8 positions, the admitted count.
    A mask whose set bits meant "exclude" would have a population of
    ``width - 16,384`` and would grow with the context instead of being bounded
    by the pool, so the bound fixes the polarity: 1 = keep, 0 = -inf.

    PINNED LAST BLOCK.  The block that contains the newest position is always
    admitted, whether or not the block top-k returned its id.  Its
    block-maximum is taken over a partially filled block whose absent tail is
    -inf padding, so its score is not comparable with a full block's; and the
    Indexer is applied identically in training and inference, where the current
    block is always visible.  Set ``pin_last_block=False`` only to study what
    the rule is worth -- it is not an option the model has.

    -INF PADDING / TAIL.  ``width`` need not be a multiple of ``block``.  The
    last block covers ``[last * block, width)`` only; positions at or above
    ``width`` do not exist, are never admitted, and are zero in the high bits of
    the final packed word.

    Ids are a SET: a repeated id admits its block once, and the order of
    ``block_ids`` does not matter.  ``absent_id`` slots are skipped.  Any other
    id at or above ``ceil(width / block)`` is a fault, not a silent drop: it
    means the block top-k ranked a block this position axis does not have.

    Returns a dict with the packed ``words`` (bit ``j`` of word ``w`` is
    position ``w * word_bits + j``), the ``population``, the admitted
    ``blocks``, and the geometry the answer was computed under.
    """
    if not isinstance(width, int) or isinstance(width, bool) or width <= 0:
        raise CandidateMaskError("width must be a positive integer")
    if not isinstance(block, int) or isinstance(block, bool) or block <= 0:
        raise CandidateMaskError("block must be a positive integer")
    if not isinstance(word_bits, int) or isinstance(word_bits, bool) or word_bits <= 0:
        raise CandidateMaskError("word_bits must be a positive integer")
    if max_population is not None and (
        not isinstance(max_population, int)
        or isinstance(max_population, bool)
        or max_population < 0
    ):
        raise CandidateMaskError("max_population must be a non-negative integer")

    block_count = (width + block - 1) // block
    admitted: set[int] = set()
    for slot, raw in enumerate(block_ids):
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise CandidateMaskError(f"block id slot {slot} is not an integer")
        if raw == absent_id:
            continue
        if raw < 0 or raw >= block_count:
            raise CandidateMaskError(
                f"block id slot {slot} selects block {raw}, outside the "
                f"{block_count} blocks of a {width}-position axis"
            )
        admitted.add(raw)
    pinned = block_count - 1 if pin_last_block else None
    if pinned is not None:
        admitted.add(pinned)

    #: Position-by-position, from the block set, with no bit arithmetic: the
    #: independent statement of the semantics the RTL implements by expanding a
    #: block bitmap.  Position p is admitted when p // block is admitted.
    positions = bytearray(width)
    for chosen in sorted(admitted):
        start = chosen * block
        stop = min(start + block, width)
        for position in range(start, stop):
            positions[position] = 1
    population = sum(positions)
    if max_population is not None and population > max_population:
        raise CandidateMaskError(
            f"candidate pool admits {population} positions, above the declared "
            f"bound of {max_population}"
        )

    word_count = (width + word_bits - 1) // word_bits
    words = []
    for word_index in range(word_count):
        value = 0
        base = word_index * word_bits
        for bit in range(word_bits):
            position = base + bit
            if position < width and positions[position]:
                value |= 1 << bit
        words.append(value)

    return {
        "contract": CANDIDATE_MASK_CONTRACT,
        "polarity": "set_bit_admits_position",
        "width": width,
        "block": block,
        "word_bits": word_bits,
        "block_count": block_count,
        "words": tuple(words),
        "word_count": word_count,
        "population": population,
        "admitted_block_count": len(admitted),
        "blocks": tuple(sorted(admitted)),
        "pinned_block": pinned,
        "tail_bits": width % word_bits,
    }


# ---------------------------------------------------------------------------
# ROUTE.BLOCK_MAX, the blockwise maximum of the candidate pool
# (docs/DEEPSEEK_V41_FLASH_ROM_IMPLEMENTATION_PLAN.md section 5 row 2, and
# section 7's `select_candidate_blocks` semantics: the negative-infinity
# padding of a partial final block).  Numeric contract
# `block_max_ordered_ieee_v1`.
#
# This is the independent reference for rtl/abi3/ot_a3_route_block_max.sv.  It
# is written from the operator's semantics, not from that block: the order is
# stated as an order on EXACT VALUES of the score format, computed with
# `fractions.Fraction` and integer field arithmetic, with no host floating
# point and none of the monotone-key bit manipulation the RTL uses to realise
# it.  Agreement between the two is therefore a check, not a tautology.
# ---------------------------------------------------------------------------

from collections.abc import Sequence  # noqa: E402  (appended section)
from fractions import Fraction  # noqa: E402  (appended section)

BLOCK_MAX_NUMERIC_CONTRACT = "block_max_ordered_ieee_v1"
#: DeepSeek-V4.1-Flash candidate pool: 2,048 blocks of 8 binary32 scores.
#: Defaults, never bounds: every entry point below takes them as arguments.
BLOCK_MAX_V41_BLOCK = 8
BLOCK_MAX_V41_ROW_BLOCKS = 2048
BLOCK_MAX_V41_EXPONENT_BITS = 8
BLOCK_MAX_V41_MANTISSA_BITS = 23


class BlockMaxReferenceError(ValueError):
    """Raised when a BLOCK_MAX input violates the operator's contract."""


def _block_max_check_format(exponent_bits: int, mantissa_bits: int) -> int:
    if isinstance(exponent_bits, bool) or not isinstance(exponent_bits, int):
        raise BlockMaxReferenceError("exponent_bits must be an integer")
    if isinstance(mantissa_bits, bool) or not isinstance(mantissa_bits, int):
        raise BlockMaxReferenceError("mantissa_bits must be an integer")
    if exponent_bits < 2 or mantissa_bits < 1:
        raise BlockMaxReferenceError(
            f"exponent_bits {exponent_bits} and mantissa_bits {mantissa_bits} are not an "
            "IEEE-754 interchange shape"
        )
    return 1 + exponent_bits + mantissa_bits


def block_max_padding_code(
    exponent_bits: int = BLOCK_MAX_V41_EXPONENT_BITS,
    mantissa_bits: int = BLOCK_MAX_V41_MANTISSA_BITS,
) -> int:
    """The code the reference pads a partial final block with: negative infinity.

    Negative infinity is the identity of the maximum over the admitted codes,
    which is why the padding is invisible in the result and why a zero pad
    would not be: the scores this operator reduces are masked attention
    scores, so a whole block can be negative.
    """

    _block_max_check_format(exponent_bits, mantissa_bits)
    return ((1 << (exponent_bits + 1)) - 1) << mantissa_bits


def _block_max_order(code: int, exponent_bits: int, mantissa_bits: int) -> tuple[int, "Fraction", int]:
    """The total order on the admitted codes of one sign-magnitude IEEE format.

    The key is (tier, exact value, zero rank): negative infinity below every
    finite value, positive infinity above every finite value, finite values by
    their exact rational value, and the negative zero immediately below the
    positive zero.  Every component is exact, so the comparison is exact; a
    NaN has no place in the order and is refused by the caller.
    """

    width = 1 + exponent_bits + mantissa_bits
    if isinstance(code, bool) or not isinstance(code, int):
        raise BlockMaxReferenceError("a score must be an unsigned integer code")
    if code < 0 or code >> width:
        raise BlockMaxReferenceError(
            f"score code {code} does not fit the {width}-bit score format"
        )
    negative = bool(code >> (exponent_bits + mantissa_bits))
    exponent = (code >> mantissa_bits) & ((1 << exponent_bits) - 1)
    mantissa = code & ((1 << mantissa_bits) - 1)
    if exponent == (1 << exponent_bits) - 1:
        if mantissa:
            raise BlockMaxReferenceError(
                "BLOCK_MAX refuses a NaN score: the order is not total on NaNs and the "
                "candidates for a convention (IEEE maxNum, numpy.maximum, Python max) "
                "disagree, so there is no semantics to reproduce"
            )
        return (-1 if negative else 1, Fraction(0), 1)
    bias = (1 << (exponent_bits - 1)) - 1
    if exponent == 0:
        magnitude = Fraction(mantissa, 1 << (mantissa_bits - 1 + bias))
    else:
        magnitude = Fraction((1 << mantissa_bits) | mantissa) * Fraction(2) ** (
            exponent - bias - mantissa_bits
        )
    value = -magnitude if negative else magnitude
    zero_rank = 0 if (magnitude == 0 and negative) else 1
    return (0, value, zero_rank)


def block_max_rows(
    rows: "Sequence[Sequence[int]]",
    block: int = BLOCK_MAX_V41_BLOCK,
    *,
    exponent_bits: int = BLOCK_MAX_V41_EXPONENT_BITS,
    mantissa_bits: int = BLOCK_MAX_V41_MANTISSA_BITS,
) -> "tuple[tuple[int, ...], ...]":
    """Reduce each score row to one score per contiguous block of `block`.

    `rows[r]` is a row of score codes in the sign-magnitude IEEE interchange
    format described by `exponent_bits` and `mantissa_bits` (binary32 by
    default; BF16 is (8, 7) and FP16 is (5, 10)).  The result holds, for each
    row, `ceil(len(row) / block)` codes: block `b` is the maximum over
    positions `[b * block, (b + 1) * block)` of the row padded to a multiple of
    `block` with `block_max_padding_code`, so a row whose length is not a
    multiple of `block` keeps its tail as a partial final block reduced over
    its real positions only.  An empty row yields no blocks.

    The returned value is the winning CODE, bit for bit, under the total order
    of `_block_max_order`: `max(-0.0, +0.0)` is `+0.0`, `max(-0.0, -0.0)` is
    `-0.0`, and no value is rounded, added or renormalised anywhere -- this
    operator selects, it does not compute.

    Raises `BlockMaxReferenceError` for a non-positive block, a code that does
    not fit the format, or a NaN score.  This function models the numeric
    semantics only; the structural refusals of the engine block (a zero
    extent, an interior partial block, a row longer than the admitted block
    count) are properties of a descriptor, not of this reduction.
    """

    if isinstance(block, bool) or not isinstance(block, int):
        raise BlockMaxReferenceError("block must be an integer")
    if block < 1:
        raise BlockMaxReferenceError(f"block {block} must be at least 1")
    _block_max_check_format(exponent_bits, mantissa_bits)
    padding = block_max_padding_code(exponent_bits, mantissa_bits)

    reduced: list[tuple[int, ...]] = []
    for row in rows:
        codes = list(row)
        remainder = len(codes) % block
        if remainder:
            codes.extend([padding] * (block - remainder))
        keys = [_block_max_order(code, exponent_bits, mantissa_bits) for code in codes]
        row_blocks: list[int] = []
        for base in range(0, len(codes), block):
            best = base
            for offset in range(base + 1, base + block):
                if keys[offset] > keys[best]:
                    best = offset
            row_blocks.append(codes[best])
        reduced.append(tuple(row_blocks))
    return tuple(reduced)


# ---------------------------------------------------------------------------
# `select_candidate_blocks`, level one of the two-level top-k, END TO END
# (plan section 7: "`select_candidate_blocks` semantics including the
# pinned-last-block rule and the -inf padding").
#
# `select_candidate_mask` above starts from block ids a top-k already chose.
# That is the operand the RTL takes, but it is NOT the whole of the pinned
# function: the pinned `select_candidate_blocks` starts from index SCORES, and
# three of its decisions live between the scores and the ids --
#
#   1. the -inf pad of the partial final block, which makes an unreachable
#      block score -inf rather than wrapping into a neighbour;
#   2. the pin, which is `(compress_lens - 1) // block_size` -- the block
#      holding THIS QUERY's newest reachable position, NOT the last block of
#      the position axis.  During decode the two coincide because the axis is
#      exactly as long as the query can reach.  During prefill they do not:
#      `compress_lens` is per-query and every query pins a different block;
#   3. the `top.values > -inf` drop, which is what stops a query with fewer
#      reachable blocks than `topk_blocks` from admitting padding.
#
# `select_candidate_mask`'s `pin_last_block` pins `block_count - 1`, so it is
# the decode case of (2) and cannot express the prefill case.  This function
# states all three, takes `compress_lens` per query, and is the reference the
# oracle compares the vendor's own `select_candidate_blocks` against.
#
# NO FROZEN GEOMETRY.  `block_size`, `topk_blocks` and the position width are
# arguments.  The pin is DERIVED from `compress_lens` for every query, so a
# context that is not a multiple of the block size, and a query whose reach is
# shorter than the axis, are ordinary inputs rather than special cases.
# ---------------------------------------------------------------------------


#: Sentinel for "this position scores -inf": the pad of a partial final block
#: and every position the query cannot reach.  A sentinel rather than a float
#: because the ordering below is on exact values, and -inf has no exact value.
NEGATIVE_INFINITY = "-inf"


def _score_key(value: object) -> tuple[int, Fraction]:
    """Order scores with -inf strictly below every finite value."""
    if value is NEGATIVE_INFINITY or value == NEGATIVE_INFINITY:
        return (0, Fraction(0))
    if isinstance(value, bool) or not isinstance(value, (int, Fraction)):
        raise CandidateMaskError(
            "a score must be an int, a Fraction, or NEGATIVE_INFINITY; "
            f"got {type(value).__name__}"
        )
    return (1, Fraction(value))


def select_candidate_blocks(
    logits: Sequence[object],
    compress_lens: int,
    topk_blocks: int,
    block_size: int,
) -> dict[str, Any]:
    """Reference for the pinned ``select_candidate_blocks``, for ONE query row.

    ``logits`` is this query's score per compressed position, lowest position
    first, with every position the query cannot reach already at
    :data:`NEGATIVE_INFINITY` -- which is what makes a block score of -inf mean
    "not reachable yet", exactly as the pinned docstring says.  ``compress_lens``
    is this query's reachable extent in positions.  Returns the per-position
    boolean mask the pinned function returns, plus the blocks and the pin, so an
    audit can see which of the three decisions produced a given position.

    THE THREE DECISIONS, in the pinned order.

    * ``scores[b] = max(logits[b * block_size : (b + 1) * block_size])`` with
      the final block padded to ``block_size`` by -inf.  Padding cannot raise a
      block's score, so a block whose reachable part is empty scores -inf.
    * ``pin = (compress_lens - 1) // block_size`` is forced to ``+inf``, so it
      is admitted whatever it scored.  It is derived per query; with
      ``compress_lens == len(logits)`` it is the axis's last block and this
      agrees with ``select_candidate_mask(pin_last_block=True)``.
    * ``min(topk_blocks, num_blocks)`` blocks are taken by score and any pick
      whose score is -inf is DROPPED.  The pin scores ``+inf``, so the pin is
      never the dropped one.

    TIES.  The pinned implementation calls ``torch.topk``, whose tie order is
    not specified.  This reference therefore reports ``tie_at_threshold``: True
    when a finite score appears both inside and outside the chosen set, i.e.
    when the admitted set is not determined by the scores alone.  It does NOT
    invent a tie rule; ``runtime/reference/selection.py`` owns that question,
    and a comparison against the vendor on a tied row is not evidence either
    way.  The mask is still returned, resolving ties by lowest block id.
    """
    if not isinstance(compress_lens, int) or isinstance(compress_lens, bool):
        raise CandidateMaskError("compress_lens must be an integer")
    if not isinstance(topk_blocks, int) or isinstance(topk_blocks, bool) or topk_blocks <= 0:
        raise CandidateMaskError("topk_blocks must be a positive integer")
    if (
        not isinstance(block_size, int)
        or isinstance(block_size, bool)
        or block_size <= 0
    ):
        raise CandidateMaskError("block_size must be a positive integer")
    width = len(logits)
    if width == 0:
        raise CandidateMaskError("logits must carry at least one position")
    if compress_lens <= 0 or compress_lens > width:
        raise CandidateMaskError(
            f"compress_lens {compress_lens} is outside the 1..{width} this "
            "position axis can express"
        )

    keys = [_score_key(value) for value in logits]
    num_blocks = (width + block_size - 1) // block_size

    #: 1. block maxima over the -inf-padded axis.  The pad is not materialised:
    #: a short final block simply has fewer positions to maximise over, which
    #: is what padding with a value below every other value means.
    block_scores: list[tuple[int, Fraction]] = []
    for block_index in range(num_blocks):
        start = block_index * block_size
        stop = min(start + block_size, width)
        best = (0, Fraction(0))
        for position in range(start, stop):
            if keys[position] > best:
                best = keys[position]
        block_scores.append(best)

    #: 2. the pin, derived from this query's reach.
    pin = (compress_lens - 1) // block_size
    if pin >= num_blocks:
        raise CandidateMaskError(
            f"compress_lens {compress_lens} pins block {pin}, outside the "
            f"{num_blocks} blocks of a {width}-position axis"
        )

    #: 3. top-k by score with the pin forced above everything, then the -inf
    #: drop.  Sorting by (score, -id) and slicing is the same selection as a
    #: top-k, with ties resolved to the lowest id as the docstring states.
    order = sorted(
        range(num_blocks),
        key=lambda index: (
            (2, Fraction(0)) if index == pin else block_scores[index],
            -index,
        ),
        reverse=True,
    )
    taken = order[: min(topk_blocks, num_blocks)]
    admitted = sorted(
        index for index in taken if index == pin or block_scores[index][0] != 0
    )
    dropped = sorted(
        index for index in taken if index != pin and block_scores[index][0] == 0
    )

    #: Was the admitted set decided by the scores alone?  It was not if a
    #: finite score appears both inside and outside it.
    inside = {block_scores[index] for index in taken if index != pin}
    outside = {
        block_scores[index]
        for index in range(num_blocks)
        if index not in taken and block_scores[index][0] != 0
    }
    tie_at_threshold = bool(inside & outside)

    positions = bytearray(width)
    for block_index in admitted:
        start = block_index * block_size
        for position in range(start, min(start + block_size, width)):
            positions[position] = 1

    return {
        "contract": CANDIDATE_MASK_CONTRACT,
        "width": width,
        "block_size": block_size,
        "block_count": num_blocks,
        "compress_lens": compress_lens,
        "topk_blocks": topk_blocks,
        "picks": min(topk_blocks, num_blocks),
        "pinned_block": pin,
        "blocks": tuple(admitted),
        "dropped_negative_infinity_blocks": tuple(dropped),
        "mask": tuple(bool(bit) for bit in positions),
        "population": sum(positions),
        "tie_at_threshold": tie_at_threshold,
    }


# ---------------------------------------------------------------------------
# CANDIDATE_MASK_READ, the later layers' view of the published admission plane.
# Numeric contract `candidate_mask_view_v1`.
#
# `select_candidate_mask` above is the layer that BUILDS the plane -- V4.1's
# `candidate_source_layer_id` 20.  Every Reindex layer after it does not rebuild
# it: the pinned `Indexer` "masks scores to the candidate pool when
# 0 <= candidate_source_layer < layer_id", one plane shared by layers 24, 28, 32
# and 36.  That read is its own kernel (`STATE_READ`) and its own contract,
# because what it has to get right is not arithmetic on values but IDENTITY over
# a lifetime: the plane a later layer masks with must be bit-for-bit the plane
# layer 20 published, and it must still be the current one.
#
# So this reference is an identity with preconditions, and the preconditions are
# the whole content: a view that silently returned a plane from the wrong
# publisher, or one whose population exceeded the pool the deployment sized its
# score buffers for, is exactly the failure a "it is just a copy" implementation
# cannot detect.  Each is refused here.
#
# NOT ESTABLISHED: which blocks the plane admits (that is
# `select_candidate_blocks` and `select_candidate_mask` above), and what the
# consumer does with an admitted position.
# ---------------------------------------------------------------------------


def candidate_mask_view(
    published: Mapping[str, Any],
    *,
    published_by_layer: int,
    reading_layer: int,
    population_bound: int,
    width: int | None = None,
) -> dict[str, Any]:
    """Read a published candidate admission plane -- ``candidate_mask_view_v1``.

    ``published`` is a record returned by :func:`select_candidate_mask`.  The
    result carries the SAME packed ``words`` object, so a caller that mutates
    the view mutates the publication and a caller that compares them compares
    identity, not a re-derivation.

    Refused, rather than answered:

    * a read by a layer at or before the publisher -- the pinned condition is
      ``candidate_source_layer < layer_id``, strictly, and a layer that read its
      own or an earlier layer's plane would be reading a plane that does not yet
      exist at that point of the block sequence;
    * a plane whose publisher is not the one the reading kernel declares --
      ``published_by_layer`` is an attribute of the read, and a plane from a
      different source layer is a different pool;
    * a population above the reading kernel's declared ``population_bound``.
      The bound is what sizes the masked score axis downstream, so a plane that
      exceeds it would overflow a buffer the deployment proved was large enough;
    * a width disagreement, when the caller states the position axis it expects.

    The polarity is carried through unchanged and re-stated: a set bit admits.
    """
    if not isinstance(published, Mapping):
        raise CandidateMaskError("published must be a candidate-mask record")
    for key in ("width", "block", "word_bits", "words", "population", "polarity"):
        if key not in published:
            raise CandidateMaskError(
                f"published candidate mask has no {key!r}; it is not a record "
                "select_candidate_mask produced"
            )
    for name, value in (
        ("published_by_layer", published_by_layer),
        ("reading_layer", reading_layer),
        ("population_bound", population_bound),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise CandidateMaskError(f"{name} must be a non-negative integer")
    if reading_layer <= published_by_layer:
        raise CandidateMaskError(
            f"layer {reading_layer} reads the candidate pool published by layer "
            f"{published_by_layer}; the pinned condition is "
            "candidate_source_layer < layer_id, strictly"
        )
    if published["polarity"] != "set_bit_admits_position":
        raise CandidateMaskError(
            f"published plane states polarity {published['polarity']!r}, not "
            "set_bit_admits_position"
        )
    published_width = published["width"]
    if width is not None:
        if isinstance(width, bool) or not isinstance(width, int) or width <= 0:
            raise CandidateMaskError("width must be a positive integer")
        if published_width != width:
            raise CandidateMaskError(
                f"published plane is {published_width} positions wide and the "
                f"reading layer expects {width}"
            )
    population = published["population"]
    if population > population_bound:
        raise CandidateMaskError(
            f"published candidate pool admits {population} positions, above the "
            f"{population_bound} the reading kernel declares"
        )
    return {
        "contract": "candidate_mask_view_v1",
        "polarity": "set_bit_admits_position",
        "published_by_layer": published_by_layer,
        "reading_layer": reading_layer,
        "population": population,
        "population_bound": population_bound,
        "width": published_width,
        "block": published["block"],
        "word_bits": published["word_bits"],
        "words": published["words"],
        "identical_to_publication": True,
    }
