"""Exact table-lookup references for DeepSeek V4 embedding and hash routing.

Both operators are pure gathers in the pinned source. The global embedding
reference is mathematically equivalent to the vocabulary-parallel zero-mask and
all-reduce implementation because exactly one shard owns every valid token row.
BF16 values are carried as their raw 16-bit encodings, so the lookup introduces
no host floating-point conversion. Hash routing likewise returns the exact
checkpoint table entries without consulting or reordering router scores.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TypeAlias

from .formats import decode_e4m3fn, decode_e8m0, encode_bf16_rne


MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)
BF16_MAX_ENCODING = (1 << 16) - 1

TokenMatrix: TypeAlias = tuple[tuple[int, ...], ...]
BF16Row: TypeAlias = tuple[int, ...]
BF16EmbeddingTensor: TypeAlias = tuple[tuple[BF16Row, ...], ...]
RouteTable: TypeAlias = tuple[tuple[int, ...], ...]


class LookupReferenceError(ValueError):
    """Raised when a table or lookup request is structurally invalid."""


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise LookupReferenceError(f"{label} must be a sequence")
    return value


def _integer(value: object, label: str, *, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise LookupReferenceError(f"{label} must be a nonnegative integer")
    if maximum is not None and value > maximum:
        raise LookupReferenceError(f"{label}={value} exceeds {maximum}")
    return value


def _token_matrix(value: object, *, vocabulary_size: int) -> TokenMatrix:
    batches = _sequence(value, "token_ids")
    if not batches:
        raise LookupReferenceError("token_ids must contain at least one batch")
    result: list[tuple[int, ...]] = []
    sequence_length: int | None = None
    for batch_index, raw_row in enumerate(batches):
        row = _sequence(raw_row, f"token_ids[{batch_index}]")
        if sequence_length is None:
            sequence_length = len(row)
            if sequence_length == 0:
                raise LookupReferenceError(
                    "token_ids must contain at least one token per batch"
                )
        elif len(row) != sequence_length:
            raise LookupReferenceError("token_ids must be a rectangular rank-2 tensor")
        result.append(
            tuple(
                _integer(
                    token_id,
                    f"token_ids[{batch_index}][{position}]",
                    maximum=vocabulary_size - 1,
                )
                for position, token_id in enumerate(row)
            )
        )
    return tuple(result)


def _bf16_table(value: object) -> tuple[BF16Row, ...]:
    rows = _sequence(value, "embedding_weight")
    if not rows:
        raise LookupReferenceError("embedding_weight must contain at least one row")
    result: list[BF16Row] = []
    width: int | None = None
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"embedding_weight[{row_index}]")
        if width is None:
            width = len(row)
            if width == 0:
                raise LookupReferenceError(
                    "embedding_weight rows must contain at least one BF16 value"
                )
        elif len(row) != width:
            raise LookupReferenceError(
                "embedding_weight must be a rectangular rank-2 tensor"
            )
        result.append(
            tuple(
                _integer(
                    code,
                    f"embedding_weight[{row_index}][{column}]",
                    maximum=BF16_MAX_ENCODING,
                )
                for column, code in enumerate(row)
            )
        )
    return tuple(result)


def bf16_token_embedding(
    token_ids: Sequence[Sequence[int]],
    embedding_weight: Sequence[Sequence[int]],
) -> BF16EmbeddingTensor:
    """Gather global BF16 embedding rows for a rectangular token-ID tensor.

    Elements of ``embedding_weight`` and the result are exact BF16 bit patterns,
    not Python floating-point approximations.
    """

    weight = _bf16_table(embedding_weight)
    tokens = _token_matrix(token_ids, vocabulary_size=len(weight))
    return tuple(tuple(weight[token_id] for token_id in batch) for batch in tokens)


def _route_table(value: object, *, expert_count: int) -> RouteTable:
    rows = _sequence(value, "route_table")
    if not rows:
        raise LookupReferenceError("route_table must contain at least one row")
    result: list[tuple[int, ...]] = []
    top_k: int | None = None
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"route_table[{row_index}]")
        if top_k is None:
            top_k = len(row)
            if top_k == 0:
                raise LookupReferenceError(
                    "route_table rows must contain at least one expert"
                )
        elif len(row) != top_k:
            raise LookupReferenceError("route_table must be a rectangular rank-2 tensor")
        result.append(
            tuple(
                _integer(
                    expert_id,
                    f"route_table[{row_index}][{slot}]",
                    maximum=expert_count - 1,
                )
                for slot, expert_id in enumerate(row)
            )
        )
    return tuple(result)


def hash_route_indices(
    token_ids: Sequence[int],
    route_table: Sequence[Sequence[int]],
    *,
    expert_count: int,
) -> tuple[tuple[int, ...], ...]:
    """Gather checkpoint-pinned expert IDs for flattened input token IDs.

    Duplicate expert IDs are preserved: the pinned source performs a plain table
    lookup and does not declare uniqueness enforcement at this boundary.
    """

    expert_count = _integer(expert_count, "expert_count")
    if expert_count == 0:
        raise LookupReferenceError("expert_count must be greater than zero")
    table = _route_table(route_table, expert_count=expert_count)
    raw_tokens = _sequence(token_ids, "token_ids")
    if not raw_tokens:
        raise LookupReferenceError("token_ids must contain at least one token")
    tokens = tuple(
        _integer(token_id, f"token_ids[{index}]", maximum=len(table) - 1)
        for index, token_id in enumerate(raw_tokens)
    )
    return tuple(table[token_id] for token_id in tokens)





# ---------------------------------------------------------------------------
# DeepSeek-V4.1-Flash Engram table lookups
# ---------------------------------------------------------------------------
#
# Four kernels of the V4.1 Engram path are table reads, and each names its own
# numeric contract because each reads a differently typed table:
#
#   ``lookup_compressed_token_ids_v1``              u32 map, one value per token
#   ``lookup_engram_row_fp8_e4m3_row_read_v1``      fp8_e4m3fn rows, 256 wide
#   ``lookup_engram_row_fp8_e4m3_row_scale_read_v1`` e8m0 row scales, one per row
#   ``lookup_engram_row_fp8_e4m3_reconstruct_v1``   e8m0-scaled blocks -> bf16
#
# The scale read is the gather the reconstruction below has always ASSUMED its
# caller performed -- its docstring states that the caller "has already gathered
# ``scale[row_identifiers[p][c]]`` for every hash column ``c``".  The export now
# emits that gather as its own kernel, which is why it now names its own
# contract: handing the whole ``[table_rows, 1]`` scale tensor to the
# reconstruction instead left the correspondence unstated in the graph, and the
# device refused the pair (189,998 scale rows against 3,072 gathered rows).
#
# Every one of them is written from the kernel's own declared attributes and
# from the released tensor declarations -- ``engram.compressed_token_map`` is
# ``u32[129280]`` with ``table_value_maximum`` 99091, and
# ``layers.<n>.engram.embed.weight`` is ``fp8_e4m3fn[rows, 256]`` carrying
# ``scale_tensor_id`` ``...embed.scale`` of dtype ``e8m0`` with
# ``scale_block_elements`` 32.  NOTHING about the V4.1 geometry is frozen below:
# the table width, the row count, the number of hash columns, the block size and
# the value bound are all operands or keyword arguments, and every bound that a
# caller states is *checked* rather than assumed.
#
# NOT ESTABLISHED by any of the three: how the compressed token map itself is
# built (the vendor normalises with its own tokenizer; the map is an operand
# here, exactly as it is an operand of the kernel), which row identifiers the
# n-gram hash produces (that is ``runtime.reference.engram.ngram_row_ids``), and
# what the gate downstream of the reconstruction does.


def compressed_token_ids(
    token_ids: Sequence[int],
    compressed_token_map: Sequence[int],
    *,
    value_maximum: int | None = None,
) -> tuple[int, ...]:
    """Engram compressed token ids -- contract ``lookup_compressed_token_ids_v1``.

    ``out[p] = compressed_token_map[token_ids[p]]``, one committed value per
    position, in position order.  The kernel declares ``committed_row:
    absolute_position``, which is this ordering: the value for position ``p`` is
    the ``p``-th element of the result and of the state it commits to.

    ``value_maximum`` is the kernel's ``table_value_maximum`` attribute.  When
    given, every table value the lookup *returns* is checked against it, so a
    map that would address an n-gram column outside the compressed vocabulary is
    refused here rather than producing a row identifier nothing owns.  It is a
    checked bound, never a clamp: an out-of-range value raises.
    """

    table = _sequence(compressed_token_map, "compressed_token_map")
    if not table:
        raise LookupReferenceError(
            "compressed_token_map must contain at least one row"
        )
    bound = (
        None
        if value_maximum is None
        else _integer(value_maximum, "value_maximum")
    )
    values = tuple(
        _integer(entry, f"compressed_token_map[{index}]")
        for index, entry in enumerate(table)
    )
    raw = _sequence(token_ids, "token_ids")
    if not raw:
        raise LookupReferenceError("token_ids must contain at least one token")
    out: list[int] = []
    for position, token_id in enumerate(raw):
        index = _integer(
            token_id, f"token_ids[{position}]", maximum=len(values) - 1
        )
        value = values[index]
        if bound is not None and value > bound:
            raise LookupReferenceError(
                f"compressed_token_map[{index}] is {value}, above the declared "
                f"table_value_maximum {bound}"
            )
        out.append(value)
    return tuple(out)


def _fp8_row_table(
    value: object, *, row_width: int | None
) -> tuple[tuple[int, ...], ...]:
    rows = _sequence(value, "row_table")
    if not rows:
        raise LookupReferenceError("row_table must contain at least one row")
    width = row_width
    table: list[tuple[int, ...]] = []
    for row_index, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"row_table[{row_index}]")
        if width is None:
            width = len(row)
        if len(row) != width:
            raise LookupReferenceError(
                f"row_table[{row_index}] is {len(row)} wide, expected {width}"
            )
        table.append(
            tuple(
                _integer(code, f"row_table[{row_index}][{column}]", maximum=0xFF)
                for column, code in enumerate(row)
            )
        )
    if not width:
        raise LookupReferenceError("row_table rows must not be empty")
    return tuple(table)


def engram_row_fp8_e4m3_row_read(
    row_identifiers: Sequence[Sequence[int]],
    row_table: Sequence[Sequence[int]],
    *,
    row_width: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    """Engram row read -- contract ``lookup_engram_row_fp8_e4m3_row_read_v1``.

    ``row_identifiers[p]`` holds one identifier per hash column of position
    ``p`` -- 24 for V4.1-Flash, three n-gram orders times eight hash heads --
    and the result for that position is the concatenation of the addressed
    table rows in ``ascending_column_then_row_element`` order, which is the
    layout the downstream ``DEQUANTIZE`` kernel declares:

        out[p] = row_table[id[p][0]] ++ row_table[id[p][1]] ++ ...

    The payload is fp8_e4m3fn and this operation is BYTE PRESERVING: the codes
    are returned exactly as the table holds them, with no decode, so the only
    arithmetic here is address arithmetic.  Every identifier is bounds-checked
    against the table's own row count, which is how a hash column whose prime
    bucket ends beyond the released table is refused rather than wrapped.
    """

    table = _fp8_row_table(row_table, row_width=row_width)
    width = len(table[0])
    positions = _sequence(row_identifiers, "row_identifiers")
    if not positions:
        raise LookupReferenceError("row_identifiers must contain a position")
    columns: int | None = None
    out: list[tuple[int, ...]] = []
    for position, raw_row in enumerate(positions):
        ids = _sequence(raw_row, f"row_identifiers[{position}]")
        if columns is None:
            columns = len(ids)
            if columns == 0:
                raise LookupReferenceError(
                    "row_identifiers rows must name at least one hash column"
                )
        elif len(ids) != columns:
            raise LookupReferenceError(
                "row_identifiers must be a rectangular rank-2 tensor"
            )
        codes: list[int] = []
        for column, identifier in enumerate(ids):
            row_id = _integer(
                identifier,
                f"row_identifiers[{position}][{column}]",
                maximum=len(table) - 1,
            )
            codes.extend(table[row_id])
        if len(codes) != columns * width:
            raise LookupReferenceError("row read produced a ragged row")
        out.append(tuple(codes))
    return tuple(out)


def engram_row_fp8_e4m3_row_scale_read(
    row_identifiers: Sequence[Sequence[int]],
    scale_table: Sequence[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    """Engram row-scale read -- ``lookup_engram_row_fp8_e4m3_row_scale_read_v1``.

    The companion of :func:`engram_row_fp8_e4m3_row_read`: the SAME identifiers
    address the table's scale plane, in the same
    ``ascending_column_then_row_element`` order, so that scale ``c`` of the
    returned row is the scale of hash column ``c`` of the payload row.  This is
    the release's own second gather -- ``ParallelEngramEmbedding.forward`` runs
    ``scales = F.embedding(local_indices, self.scale)`` beside its payload
    embedding -- and it is what makes the correspondence the reconstruction
    checks true by construction rather than by assertion.

    The scale plane is declared ``e8m0[table_rows, blocks_per_row]``, and the
    V4.1 tables hold exactly one block per row because ``scale_block_elements``
    is the row's full width.  That is NOT frozen here: the per-row block count
    is taken from the table and every row is checked to carry the same count.

    The operation is BYTE PRESERVING, as the payload read is: an e8m0 code is
    returned exactly as the table holds it, undecoded, so no value can round and
    a NaN code (0xFF) is neither produced nor consumed here -- the
    reconstruction is where it is refused, because that is where it would reach
    arithmetic.  The only arithmetic is address arithmetic, and every identifier
    is bounds-checked against the scale plane's own row count.
    """

    rows = _sequence(scale_table, "scale_table")
    if not rows:
        raise LookupReferenceError("scale_table must hold a row")
    table: list[tuple[int, ...]] = []
    blocks: int | None = None
    for index, raw in enumerate(rows):
        row = _sequence(raw, f"scale_table[{index}]")
        if blocks is None:
            blocks = len(row)
            if blocks == 0:
                raise LookupReferenceError(
                    "scale_table rows must hold at least one block scale"
                )
        elif len(row) != blocks:
            raise LookupReferenceError(
                f"scale_table[{index}] holds {len(row)} block scales and "
                f"scale_table[0] holds {blocks}; the plane is rectangular"
            )
        table.append(
            tuple(
                _integer(value, f"scale_table[{index}][{slot}]", maximum=0xFF)
                for slot, value in enumerate(row)
            )
        )
    positions = _sequence(row_identifiers, "row_identifiers")
    if not positions:
        raise LookupReferenceError("row_identifiers must contain a position")
    columns: int | None = None
    out: list[tuple[int, ...]] = []
    for position, raw_row in enumerate(positions):
        ids = _sequence(raw_row, f"row_identifiers[{position}]")
        if columns is None:
            columns = len(ids)
            if columns == 0:
                raise LookupReferenceError(
                    "row_identifiers rows must name at least one hash column"
                )
        elif len(ids) != columns:
            raise LookupReferenceError(
                "row_identifiers must be a rectangular rank-2 tensor"
            )
        scales: list[int] = []
        for column, identifier in enumerate(ids):
            row_id = _integer(
                identifier,
                f"row_identifiers[{position}][{column}]",
                maximum=len(table) - 1,
            )
            scales.extend(table[row_id])
        out.append(tuple(scales))
    return tuple(out)


def engram_row_fp8_e4m3_reconstruct(
    payload_codes: Sequence[Sequence[int]],
    scale_codes: Sequence[Sequence[int]],
    *,
    block_size: int,
) -> tuple[tuple[int, ...], ...]:
    """Engram row reconstruction -- ``lookup_engram_row_fp8_e4m3_reconstruct_v1``.

    For every position, the read row is partitioned into consecutive blocks of
    ``block_size`` elements -- 32 for V4.1-Flash, which is the released
    ``scale_block_elements`` of ``layers.<n>.engram.embed.weight`` -- and block
    ``b`` is multiplied by ``scale_codes[p][b]``.  The scale tensor is declared
    ``e8m0``, so each scale is an exact power of two and the product is exact;
    the single rounding of the whole operation is the final bf16
    round-to-nearest-even that ``output_dtype: bf16`` names.

    ``scale_rows: addressed_by_the_same_row_identifiers`` is why the scales are
    an operand of the same shape as the payload's block count rather than a
    second gather: the caller has already gathered
    ``scale[row_identifiers[p][c]]`` for every hash column ``c``, in the same
    ``ascending_column_then_row_element`` order, so block ``b`` of the flattened
    row and scale ``b`` of the flattened scale row correspond by construction.
    That correspondence is CHECKED here: a scale row whose length is not the
    payload row's block count is refused.

    An e8m0 NaN scale (code 0xFF) is refused rather than propagated: the
    released tables are finite, and a silently propagated NaN would turn a
    corrupt table row into a plausible gate input.
    """

    block = _integer(block_size, "block_size")
    if block == 0:
        raise LookupReferenceError("block_size must be positive")
    rows = _sequence(payload_codes, "payload_codes")
    scales = _sequence(scale_codes, "scale_codes")
    if not rows:
        raise LookupReferenceError("payload_codes must contain a position")
    if len(scales) != len(rows):
        raise LookupReferenceError(
            f"scale_codes holds {len(scales)} positions and payload_codes "
            f"{len(rows)}"
        )
    out: list[tuple[int, ...]] = []
    for position, raw_row in enumerate(rows):
        row = _sequence(raw_row, f"payload_codes[{position}]")
        if len(row) % block:
            raise LookupReferenceError(
                f"payload_codes[{position}] is {len(row)} wide, which is not a "
                f"whole number of {block}-element blocks"
            )
        block_count = len(row) // block
        scale_row = _sequence(scales[position], f"scale_codes[{position}]")
        if len(scale_row) != block_count:
            raise LookupReferenceError(
                f"scale_codes[{position}] holds {len(scale_row)} scales for "
                f"{block_count} blocks"
            )
        values: list[int] = []
        for block_index in range(block_count):
            scale_code = _integer(
                scale_row[block_index],
                f"scale_codes[{position}][{block_index}]",
                maximum=0xFF,
            )
            scale = decode_e8m0(scale_code)
            if scale.value is None:
                raise LookupReferenceError(
                    f"scale_codes[{position}][{block_index}] is a non-finite "
                    "e8m0 scale; the released Engram scale tables are finite"
                )
            for offset in range(block):
                index = block_index * block + offset
                code = _integer(
                    row[index], f"payload_codes[{position}][{index}]", maximum=0xFF
                )
                element = decode_e4m3fn(code)
                if element.value is None:
                    raise LookupReferenceError(
                        f"payload_codes[{position}][{index}] is a non-finite "
                        "fp8_e4m3fn element"
                    )
                values.append(encode_bf16_rne(element.value * scale.value).code)
        out.append(tuple(values))
    return tuple(out)


__all__ = [
    "BF16_MAX_ENCODING",
    "MODEL_SOURCE_SHA256",
    "BF16EmbeddingTensor",
    "BF16Row",
    "LookupReferenceError",
    "RouteTable",
    "TokenMatrix",
    "bf16_token_embedding",
    "compressed_token_ids",
    "engram_row_fp8_e4m3_reconstruct",
    "engram_row_fp8_e4m3_row_read",
    "engram_row_fp8_e4m3_row_scale_read",
    "hash_route_indices",
]
