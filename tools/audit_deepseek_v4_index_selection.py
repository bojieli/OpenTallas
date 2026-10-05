#!/usr/bin/env python3
"""Differential audit of sparse *selection* at the model's real parameters.

Why this exists
---------------
The DeepSeek headline ratios in this repository are quoted at 200,000 and
1,000,000 context tokens, where which KV rows sparse selection picks decides
essentially every byte moved.  Selection only starts *discarding* candidates at
2,052 prompt tokens: the ``compress_ratio=4`` layers hold ``context // 4``
compressed groups and rank ``top_k=512`` of them, so below 2,052 the ranking
runs and keeps everything it ranks.  A backend run at 2,052 tokens costs about
77 hours at the one measured backend rate, and at 200,000 tokens it is out of
reach entirely, so the regime the claims live in cannot be gated end to end
here.

This audit gates the *selection operator itself* in that regime.  It executes
``ROUTE.INDEX_TOPK`` -- through a real ABI 3.0 deployment on the functional
device, not by calling the engine with hand-made Python state -- at the model's
own ``top_k``, ``window`` and compression ratios, at contexts from 2,052 to
1,000,001, and compares the KV rows it selects against the rows the *released*
implementation selects for the same scores.

Two address spaces, one selection
---------------------------------
The accelerator and the released implementation do **not** number KV rows the
same way, and this audit would be meaningless if it compared raw row numbers.
The released ``Attention.forward`` attends over ``cat([kv, kv_compress])`` in
prefill, so a compressed group ``g`` is row ``seqlen + g``; in decode it
attends over the circular cache, so ``g`` is row ``window + g``.  The
accelerator's ``ATTENTION.SPARSE`` operand is the request's own rows, then the
window, then the compressed rows in both phases, so ``g`` is row
``span + window + g``.  Both are internally consistent; they are different
address maps for the same choice.

This audit therefore compares what is address-independent -- **which window
positions and which compressed groups** each side selects -- and checks the map
rather than assuming it: every accelerator compressed row must land at or above
``span + window``, every window row below it, and the two sides must select the
same number of each.  A defect that moved the compressed segment would break
that check, not slip through it.

What the comparator is
----------------------
The released code, transcribed line-for-line from the pinned
``inference/model.py`` (sha256 recorded in the output) into
:func:`released_selection`: ``Indexer.forward``'s mask, ``topk`` and offset for
the ranked ``compress_ratio=4`` layers, ``get_compress_topk_idxs`` for the
unranked ``compress_ratio=128`` layers, ``get_window_topk_idxs`` for the
sliding window, and the ``torch.cat`` in ``Attention.forward`` that makes them
one index array.  It runs on torch, reads no checkpoint, and supplies nothing
to the accelerator.

What this does and does not establish
-------------------------------------
Establishes: for the same index scores, the accelerator's selection operator
names the same KV rows the released implementation names, at the model's real
selection parameters, in the pruning regime.

Does **not** establish: that the accelerator computes the same *scores* (that
is ``INDEX_SCORE``, a different operator), that end-to-end tokens agree at any
context above 256, or anything about timing, bytes or hardware.

Ties are reported, not hidden
-----------------------------
``index_score.topk`` and the accelerator's stable descending rank agree on
which scores are selected but need not agree on *which candidate* when the
score at the selection boundary is a tie, and the released scores are
``relu``-ed, so exact ties at zero are expected at long context.  Every case
therefore reports ``rows_with_boundary_tie``: rows where the k-th and
(k+1)-th ranked scores are equal, and where "the same rows" is not a
well-posed question about the released model.  Rows without a boundary tie are
required to match exactly; rows with one are required to match as a multiset of
selected *scores*, which is what is well defined.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3.builder import DeploymentBuilder  # noqa: E402
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Control,
    DType,
    Feature,
    Major,
    NO_ID,
    Permission,
    Route,
    StorageClass,
    TopologyClass,
)
from runtime.abi3.deployment import ObjectSource  # noqa: E402
from runtime.abi3.descriptors import Phase, Symbol  # noqa: E402
from runtime.abi3.records import CompletionStatus  # noqa: E402
from runtime.reference.indexing import dspark_window_indices  # noqa: E402
from runtime.sim.device import Device  # noqa: E402

import runtime.sim.engines.route  # noqa: E402,F401  (registers the handlers)

SCHEMA = "opentallas.deepseek_v4_index_selection_audit.v1"
MODEL_PROFILE = REPO / "configs" / "models" / "deepseek-v4-flash-0731.json"
DEFAULT_SNAPSHOT = (
    Path.home()
    / ".cache/huggingface/hub"
    / "models--deepseek-ai--DeepSeek-V4-Flash-0731/snapshots"
    / "7872f01b1d1fe23eabc4c98b48bffcef5a386062"
)
#: The pinned released source the comparator is transcribed from.
MODEL_SOURCE_SHA256 = (
    "c0c19e6c9fa439bac7fbb1c5bc1868232dfd5aa2f439a548d0e33dcc2a9edd3f"
)


# ---------------------------------------------------------------------------
# BF16 helpers -- the released index scores are bfloat16.
# ---------------------------------------------------------------------------
def widen(codes: np.ndarray) -> np.ndarray:
    return (np.asarray(codes, dtype=np.uint16).astype(np.uint32) << 16).view(
        np.float32
    )


def narrow(values: np.ndarray) -> np.ndarray:
    """binary32 -> BF16 codes, round-to-nearest-even, the contract's rounding."""
    bits = np.ascontiguousarray(values, dtype=np.float32).view(np.uint32)
    rounded = (bits + 0x7FFF + ((bits >> 16) & 1)) >> 16
    return rounded.astype(np.uint16)


# ---------------------------------------------------------------------------
# The released comparator, transcribed from the pinned inference/model.py.
# ---------------------------------------------------------------------------
def released_selection(
    scores: np.ndarray | None,
    *,
    ratio: int,
    top_k: int,
    window: int,
    span: int,
    start_pos: int,
    context: int,
) -> list[list[int]]:
    """The released selection for one attention layer.

    Returns one ``(window_positions, compressed_groups)`` pair per query, with
    the released ``offset`` already removed from the compressed side, so the
    result is the *choice* and not the released row numbering.

    Transcribed from ``inference/model.py``:

    * ``get_window_topk_idxs`` (lines 261-271) for the window block;
    * ``Indexer.forward`` (lines 430-438) when the layer ranks -- the prefill
      ``-inf`` mask, ``topk(min(index_topk, end_pos // ratio))``, the
      re-mask to ``-1`` and the ``+ offset``; and
    * ``get_compress_topk_idxs`` (lines 275-282) when it does not; and
    * the ``torch.cat`` in ``Attention.forward`` (line 520).

    ``offset`` is the released one: ``kv.size(1)`` at ``start_pos == 0`` and
    ``win`` afterwards (line 515).  ``-1`` entries are dropped rather than
    returned, because ``kernel.sparse_attn`` treats every ``-1`` slot as an
    absent lane and the accelerator's operator compacts them away.
    """

    import torch

    end_pos = start_pos + span
    offset = span if start_pos == 0 else window

    # -- window block: get_window_topk_idxs -----------------------------
    if start_pos >= window - 1:
        slot = start_pos % window
        win_rows = [
            list(range(slot + 1, window)) + list(range(slot + 1))
        ] * span
    elif start_pos > 0:
        win_rows = [
            list(range(start_pos + 1)) + [-1] * (window - start_pos - 1)
        ] * span
    else:
        width = min(span, window)
        win_rows = []
        for query in range(span):
            base = max(0, query - window + 1)
            win_rows.append(
                [c if c <= query else -1 for c in range(base, base + width)]
            )

    # -- compressed block ------------------------------------------------
    if scores is None:
        # get_compress_topk_idxs
        if start_pos > 0:
            complete = (start_pos + 1) // ratio
            comp_rows = [[offset + g for g in range(complete)]] * span
        else:
            width = span // ratio
            comp_rows = [
                [
                    offset + g if g < (query + 1) // ratio else -1
                    for g in range(width)
                ]
                for query in range(span)
            ]
    else:
        # Indexer.forward
        index_score = torch.from_numpy(np.asarray(scores, dtype=np.float32))
        if start_pos == 0:
            mask = torch.arange(span // ratio).repeat(span, 1) >= (
                torch.arange(1, span + 1).unsqueeze(1) // ratio
            )
            index_score = index_score + torch.where(
                mask, float("-inf"), 0.0
            ).float()
        topk_idxs = index_score.topk(
            min(top_k, end_pos // ratio), dim=-1
        )[1]
        if start_pos == 0:
            remask = topk_idxs >= (torch.arange(1, span + 1).unsqueeze(1) // ratio)
            topk_idxs = torch.where(remask, torch.full_like(topk_idxs, -1), topk_idxs + offset)
        else:
            topk_idxs = topk_idxs + offset
        comp_rows = topk_idxs.tolist()

    return [
        (
            sorted({int(v) for v in win_rows[q] if int(v) >= 0}),
            sorted({int(v) - offset for v in comp_rows[q] if int(v) >= 0}),
        )
        for q in range(span)
    ]


# ---------------------------------------------------------------------------
# A minimal single-operator deployment, executed on the functional device.
# ---------------------------------------------------------------------------
def _capability(sram_bytes: int) -> Capability:
    cap = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=tuple(
            int(f)
            for f in (
                Feature.HOST_QUEUE_ABI,
                Feature.DEPLOYMENT_DESCRIPTOR_ABI,
                Feature.DETERMINISTIC_MICROSEQUENCER,
                Feature.BF16_TENSOR,
                Feature.TRANSACTIONAL_STATE,
                Feature.ON_DEVICE_SELECTION,
            )
        ),
        limits={
            "max_descriptors": 4096,
            "max_instructions": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 16,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 1 << 21,
            "max_expert_ids": 1024,
            "max_topk": 1024,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=("bf16_bf16_fp32_sequential_rne_v1",),
        engines={"route": {"queues": 1}},
        memory={"sram": {"bytes": sram_bytes}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class _Build:
    def __init__(self, sram_bytes: int) -> None:
        self.capability = _capability(sram_bytes)
        self.builder = DeploymentBuilder(
            target_id="index-selection-audit",
            model_id="deepseek-v4-flash-0731",
            backend="audit",
            capability=self.capability,
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=sram_bytes,
            sram_bytes_per_node=sram_bytes,
        )
        self._initial: dict[int, bytes] = {}
        self._schedule: int | None = None

    def _object(self, nbytes: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def input_view(self, values: np.ndarray, dtype: DType) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self._object(len(data))
        self._initial[oid] = data
        return self.builder.tensor_view(
            object_id=oid,
            dtype=dtype,
            dims=list(values.shape),
            permissions=int(Permission.READ),
        )

    def output_view(self, dims, dtype: DType, itemsize: int) -> int:
        count = int(np.prod(dims))
        oid = self._object(count * itemsize)
        return self.builder.tensor_view(
            object_id=oid,
            dtype=dtype,
            dims=list(dims),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def emit(self, family, sub, inputs, outputs, aux) -> int:
        if self._schedule is None:
            self._schedule = self.builder.schedule(
                engine_family=family,
                tile_rows=1,
                tile_cols=1,
                tile_depth=1,
                bank_mask=0b1,
                max_outstanding=1,
            )
        op = self.builder.operator(
            engine_family=family,
            engine_sub=sub,
            inputs=list(inputs),
            outputs=list(outputs),
            aux=list(aux),
            numeric_profile_id=NO_ID,
            schedule_id=self._schedule,
        )
        self.builder.emit(family, sub, descriptor_id=op)
        return op

    def finish(self, phase: Phase = Phase.PREFILL) -> Device:
        self.builder.emit(Major.CONTROL, Control.COMPLETE)
        self.builder.entrypoint(
            entrypoint_id=0,
            first_instruction=0,
            phase=phase,
            generation_policy_id=NO_ID,
        )
        device = Device(self.builder.finish(), self.capability)
        for oid, data in self._initial.items():
            device.memory[oid].write(0, data)
        return device


def accelerator_selection(
    score_codes: np.ndarray | None,
    window_rows: np.ndarray,
    *,
    ratio: int,
    top_k: int,
    span: int,
    start_pos: int,
    context: int,
    candidates: int,
) -> tuple[list[list[int]], dict[str, int]]:
    """Run ``ROUTE.INDEX_TOPK`` on the functional device and read it back."""

    window = int(window_rows.shape[1])
    slots = window + top_k
    footprint = (
        (0 if score_codes is None else score_codes.nbytes)
        + window_rows.nbytes
        + span * slots * 4
        + (1 << 20)
    )
    build = _Build(max(1 << 22, int(footprint * 2)))
    inputs: list[int] = []
    if score_codes is None:
        inputs.append(NO_ID)
    else:
        inputs.append(build.input_view(score_codes, DType.BF16))
    inputs.append(build.input_view(window_rows.astype(np.uint32), DType.U32))
    inputs.append(build.input_view(np.array([ratio], dtype=np.uint32), DType.U32))
    out = build.output_view((span, slots), DType.U32, 4)
    build.emit(
        Major.ROUTE,
        Route.INDEX_TOPK,
        inputs,
        [out],
        aux=[
            top_k,
            0,
            int(Symbol.CONTEXT_LENGTH),
            int(Symbol.POSITION_START),
        ],
    )
    device = build.finish()
    symbols = {
        int(Symbol.CONTEXT_LENGTH): context,
        int(Symbol.POSITION_START): start_pos,
    }
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    if result.status != CompletionStatus.SUCCESS:
        raise SystemExit(
            f"ROUTE.INDEX_TOPK did not complete: {result.status.name} "
            f"{getattr(result, 'message', '')}"
        )
    view = device.views.resolve(out, {}, symbols)
    got = np.array(device.views.read_array(view)).reshape(span, slots)
    rows = [sorted(int(v) for v in row if int(v) != NO_ID) for row in got]
    return rows, dict(result.counters)


#: Where the accelerator's compressed segment starts, per
#: ``runtime/sim/engines/route.py::index_topk`` (``rebase = span + window``).
def accelerator_rebase(span: int, window: int) -> int:
    return span + window


def split_accelerator_rows(
    rows: list[list[int]], span: int, window: int
) -> list[tuple[list[int], list[int]]]:
    """Accelerator rows -> ``(window_positions, compressed_groups)``.

    The split point is the operator's own ``rebase``.  If the operator ever
    emitted a compressed row below it, or a window row above it, this would
    produce a nonsensical group index rather than quietly comparing equal --
    which is why the counts are checked against the released side afterwards.
    """

    base = accelerator_rebase(span, window)
    return [
        (
            sorted(v for v in row if v < base),
            sorted(v - base for v in row if v >= base),
        )
        for row in rows
    ]


def _boundary_tie_rows(scores: np.ndarray, limits: list[int], take: int) -> list[int]:
    """Rows whose k-th and (k+1)-th ranked scores are equal.

    On such a row the released ``torch.topk`` and the accelerator's stable
    descending rank may legitimately name different candidates, because the
    released model does not say which of two equal scores wins.  The selected
    *scores* are still determined, and that is what such a row is checked on.
    """

    rows = []
    for index, limit in enumerate(limits):
        if limit <= take:
            continue
        ordered = np.sort(scores[index, :limit])[::-1]
        if ordered[take - 1] == ordered[take]:
            rows.append(index)
    return rows


def _window_block(window: int, span: int, start_pos: int) -> np.ndarray:
    """``get_window_topk_idxs`` as a U32 block, ``-1`` padded to ``NO_ID``."""
    if start_pos >= window - 1:
        slot = start_pos % window
        rows = [list(range(slot + 1, window)) + list(range(slot + 1))] * span
    elif start_pos > 0:
        rows = [list(range(start_pos + 1)) + [-1] * (window - start_pos - 1)] * span
    else:
        width = min(span, window)
        rows = []
        for query in range(span):
            base = max(0, query - window + 1)
            row = [c if c <= query else -1 for c in range(base, base + width)]
            row = row + [-1] * (window - width)
            rows.append(row)
    block = np.array(rows, dtype=np.int64)
    return np.where(block < 0, np.uint32(NO_ID), block.astype(np.uint32)).astype(
        np.uint32
    )


#: Every positive finite BF16 value there is.  The released index score is
#: BF16, so this is the whole value space a candidate's score can occupy.
def _positive_finite_bf16_codes() -> np.ndarray:
    codes = np.arange(0, 1 << 16, dtype=np.uint16)
    values = widen(codes)
    return codes[(values > 0) & np.isfinite(values)]


BF16_POSITIVE_FINITE_VALUES = int(_positive_finite_bf16_codes().size)


def _scores(kind: str, span: int, candidates: int, seed: int) -> np.ndarray:
    """Synthetic BF16 index scores.

    ``distinct`` draws each row from *distinct BF16 codes*, so the ranking is
    uniquely determined and a disagreement is a defect rather than a tie -- but
    only while it can be: BF16 holds
    :data:`BF16_POSITIVE_FINITE_VALUES` positive finite values, so once a row
    has more candidates than that, distinct scores are impossible for *any*
    corpus and for the released model itself.  :func:`distinct_scores_possible`
    records which side of that line a case is on.

    ``relu`` is the released shape -- ``index_score.relu_()`` before the
    head-weighted sum -- so roughly half the candidates are exactly ``+0``.
    Both are synthetic: they say what the operator does with a score block, not
    what score block the model produces.
    """

    rng = np.random.default_rng(seed)
    if kind == "distinct":
        pool = _positive_finite_bf16_codes()
        out = np.empty((span, candidates), dtype=np.uint16)
        for row in range(span):
            if candidates <= pool.size:
                out[row] = rng.choice(pool, size=candidates, replace=False)
            else:
                out[row] = rng.choice(pool, size=candidates, replace=True)
        return out
    if kind == "relu":
        raw = rng.normal(0.0, 1.0, size=(span, candidates)).astype(np.float32)
        return narrow(np.maximum(raw, 0.0))
    raise SystemExit(f"unknown score corpus {kind!r}")


def distinct_scores_possible(candidates: int) -> bool:
    """Can this many candidates carry pairwise different BF16 scores at all?

    Not a property of the corpus: a property of the format the released model
    scores in.  At ``compress_ratio=4`` the candidate count is ``context // 4``,
    so above a context of ``4 * BF16_POSITIVE_FINITE_VALUES`` the pigeonhole
    forces repeats, and *which* of two equally-scored groups the top-k keeps is
    not determined by the released model.  The *count* it keeps still is, which
    is what a byte-traffic claim rests on.
    """

    return candidates <= BF16_POSITIVE_FINITE_VALUES


def released_window_positions(
    window: int, span: int, start_pos: int
) -> list[list[int]]:
    """The absolute context positions the released window index names.

    ``get_window_topk_idxs`` has three branches and two address spaces -- it
    returns absolute positions during prefill and *circular cache slots* once
    decoding has begun -- but all three name the same set of context positions:
    the at most ``window`` positions ending at the query.  The decode branch
    lists the slots oldest-to-newest, and the slot holding the oldest live
    position is the one written ``window - 1`` steps ago, so the set it names
    is ``[max(0, p - window + 1) .. p]``, which is the prefill branch's set as
    well.  That common set is what is compared, because the accelerator's
    ``ROUTE.WINDOW_INDEX`` emits it in the accelerator's own address space.
    """

    return [
        list(range(max(0, p - window + 1), p + 1))
        for p in (
            range(span) if start_pos == 0 else [start_pos] * span
        )
    ]


def accelerator_window(
    positions: np.ndarray, *, window: int, context: int
) -> list[list[int]]:
    """Run ``ROUTE.WINDOW_INDEX`` on the functional device and read it back."""

    span = int(positions.size)
    footprint = span * window * 4 + span * 4 + (1 << 20)
    build = _Build(max(1 << 22, int(footprint * 2)))
    src = build.input_view(positions.astype(np.uint32), DType.U32)
    out = build.output_view((span, window), DType.U32, 4)
    build.emit(
        Major.ROUTE,
        Route.WINDOW_INDEX,
        [src],
        [out],
        aux=[window, 0, int(Symbol.CONTEXT_LENGTH), NO_ID],
    )
    device = build.finish()
    symbols = {int(Symbol.CONTEXT_LENGTH): context}
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    if result.status != CompletionStatus.SUCCESS:
        raise SystemExit(
            f"ROUTE.WINDOW_INDEX did not complete: {result.status.name}"
        )
    view = device.views.resolve(out, {}, symbols)
    got = np.array(device.views.read_array(view)).reshape(span, window)
    return [sorted(int(v) for v in row if int(v) != NO_ID) for row in got]


def accelerator_dspark_window(
    positions: np.ndarray, *, window: int, block: int, context: int
) -> list[list[int]]:
    """Run ``ROUTE.DSPARK_WINDOW_INDEX`` on the device and read it back.

    Amendment A30's operator, and unlike ``ROUTE.WINDOW_INDEX`` it exists in
    decode only, so the entrypoint declares that phase.  The rows are returned
    in the order the operator wrote them, not sorted: this family's order is
    slot-ascending rather than chronological, and sorting would be exactly the
    step that hides a restored rotation.
    """

    span = int(positions.size)
    slots = window + block
    footprint = span * slots * 4 + span * 4 + (1 << 20)
    build = _Build(max(1 << 22, int(footprint * 2)))
    src = build.input_view(positions.astype(np.uint32), DType.U32)
    out = build.output_view((span, slots), DType.U32, 4)
    build.emit(
        Major.ROUTE,
        Route.DSPARK_WINDOW_INDEX,
        [src],
        [out],
        aux=[window, block, int(Symbol.CONTEXT_LENGTH), NO_ID],
    )
    device = build.finish(Phase.DECODE)
    symbols = {int(Symbol.CONTEXT_LENGTH): context}
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    if result.status != CompletionStatus.SUCCESS:
        raise SystemExit(
            f"ROUTE.DSPARK_WINDOW_INDEX did not complete: {result.status.name}"
        )
    view = device.views.resolve(out, {}, symbols)
    got = np.array(device.views.read_array(view)).reshape(span, slots)
    return [[int(v) for v in row if int(v) != NO_ID] for row in got]


def run_dspark_window_case(
    *, label: str, window: int, block: int, start_pos: int, context: int
) -> dict[str, Any]:
    positions = start_pos + np.arange(block, dtype=np.uint32)
    got = accelerator_dspark_window(
        positions, window=window, block=block, context=context
    )
    expected = [
        list(row)
        for row in dspark_window_indices(window, 1, block, start_pos)[0]
    ]
    mismatches = [q for q in range(block) if got[q] != expected[q]]
    return {
        "label": label,
        "operator": "ROUTE.DSPARK_WINDOW_INDEX",
        "context": context,
        "window": window,
        "draft_block": block,
        "start_position": start_pos,
        "phase": "decode",
        "history_slots": min(window, start_pos + 1),
        "rows_identical": len({tuple(row) for row in got}) == 1,
        "row_mismatches": mismatches[:8],
        "row_mismatch_count": len(mismatches),
        "agrees": not mismatches,
    }


def run_window_case(
    *, label: str, window: int, span: int, start_pos: int, context: int
) -> dict[str, Any]:
    positions = (
        np.arange(span, dtype=np.uint32)
        if start_pos == 0
        else np.full(span, start_pos, dtype=np.uint32)
    )
    got = accelerator_window(positions, window=window, context=context)
    expected = released_window_positions(window, span, start_pos)
    mismatches = [q for q in range(span) if got[q] != expected[q]]
    clipped = sum(1 for row in expected if len(row) == window)
    return {
        "label": label,
        "operator": "ROUTE.WINDOW_INDEX",
        "context": context,
        "window": window,
        "span": span,
        "start_position": start_pos,
        "phase": "prefill" if start_pos == 0 else "decode",
        "queries_at_full_window": clipped,
        "queries_whose_window_excludes_position_zero": sum(
            1 for row in expected if row and row[0] > 0
        ),
        "row_mismatches": mismatches[:8],
        "row_mismatch_count": len(mismatches),
        "agrees": not mismatches,
    }


def _profile(path: Path) -> tuple[dict, list[dict]]:
    body = json.loads(path.read_text())
    return body["metadata"]["operator_config"], body["attention_groups"]


def run_case(
    *,
    label: str,
    ratio: int,
    top_k: int,
    window: int,
    span: int,
    start_pos: int,
    context: int,
    corpus: str,
    seed: int,
) -> dict[str, Any]:
    candidates = context // ratio
    ranked = top_k > 0
    codes = _scores(corpus, span, candidates, seed) if ranked else None
    values = widen(codes) if codes is not None else None
    window_rows = _window_block(window, span, start_pos)

    got, counters = accelerator_selection(
        codes,
        window_rows,
        ratio=ratio,
        top_k=top_k if ranked else candidates,
        span=span,
        start_pos=start_pos,
        context=context,
        candidates=candidates,
    )

    if ranked:
        released_scores = values.copy()
    else:
        released_scores = None
    expected = released_selection(
        released_scores,
        ratio=ratio,
        top_k=top_k,
        window=window,
        span=span,
        start_pos=start_pos,
        context=context,
    )

    limits = [
        min((start_pos + row + 1) // ratio, candidates) for row in range(span)
    ]
    take = min(top_k, candidates) if ranked else candidates
    tie_rows = (
        _boundary_tie_rows(values, limits, take) if ranked and take else []
    )
    tie_set = set(tie_rows)

    split = split_accelerator_rows(got, span, window)

    window_mismatches: list[int] = []
    group_mismatches: list[int] = []
    count_mismatches: list[int] = []
    tied_score_mismatches: list[int] = []
    for row in range(span):
        accel_window, accel_groups = split[row]
        want_window, want_groups = expected[row]
        if accel_window != want_window:
            window_mismatches.append(row)
        if len(accel_groups) != len(want_groups):
            # The address map itself is wrong, or one side selected a
            # different number of groups.  Either way this is not a tie.
            count_mismatches.append(row)
            continue
        if accel_groups == want_groups:
            continue
        if row in tie_set:
            got_scores = sorted(float(values[row, g]) for g in accel_groups)
            want_scores = sorted(float(values[row, g]) for g in want_groups)
            if got_scores != want_scores:
                tied_score_mismatches.append(row)
        else:
            group_mismatches.append(row)

    agrees = not (
        window_mismatches
        or group_mismatches
        or count_mismatches
        or tied_score_mismatches
    )

    return {
        "label": label,
        "context": context,
        "compression_ratio": ratio,
        "top_k": top_k,
        "ranks_candidates": ranked,
        "window": window,
        "span": span,
        "start_position": start_pos,
        "phase": "prefill" if start_pos == 0 else "decode",
        "score_corpus": corpus if ranked else "not_applicable",
        "candidate_compressed_groups": candidates,
        "distinct_bf16_scores_possible": distinct_scores_possible(candidates),
        "bf16_positive_finite_values": BF16_POSITIVE_FINITE_VALUES,
        "selected_per_query": take,
        "selection_prunes": bool(ranked and candidates > take),
        "accelerator_compressed_segment_starts_at": accelerator_rebase(span, window),
        "released_compressed_segment_starts_at": span if start_pos == 0 else window,
        "rows_with_boundary_tie": len(tie_rows),
        "rows_compared_exactly": span - len(tie_rows),
        "window_position_mismatches": window_mismatches[:8],
        "window_position_mismatch_count": len(window_mismatches),
        "selected_group_count_mismatches": count_mismatches[:8],
        "selected_group_count_mismatch_count": len(count_mismatches),
        "compressed_group_mismatches": group_mismatches[:8],
        "compressed_group_mismatch_count": len(group_mismatches),
        "tied_row_score_mismatches": tied_score_mismatches[:8],
        "tied_row_score_mismatch_count": len(tied_score_mismatches),
        "agrees": agrees,
        "route_topk_candidates_counter": int(
            counters.get("route.topk_candidates", 0)
        ),
    }


def default_cases(config: dict, groups: list[dict]) -> list[dict[str, Any]]:
    """Cases derived from the pinned profile, not chosen by hand.

    The contexts are the ones the program makes claims at (200,000 and
    1,000,000, each plus one so the final query has completed its group), the
    first context at which selection prunes, and the committed ladder rungs
    between.  Prefill spans are the whole prompt where the score block fits in
    memory, which is what the released model does; longer contexts are audited
    at their decode step, which is what the released model does after prefill
    and is where per-token KV traffic is decided.
    """

    window = int(config["window_tokens"])
    ranked = {
        int(g["compression_ratio"]): int(g["top_k"])
        for g in groups
        if int(g["compression_ratio"]) > 1
    }
    cases: list[dict[str, Any]] = []
    fine = min(r for r, k in ranked.items() if k)
    top_k = ranked[fine]
    first_prune = fine * (top_k + 1)

    for corpus in ("distinct", "relu"):
        # Whole-prompt prefill, the released prefill, where the score block fits.
        for context in (first_prune, 8000):
            cases.append(
                dict(
                    label=f"prefill_ratio{fine}_{context}_{corpus}",
                    ratio=fine,
                    top_k=top_k,
                    window=window,
                    span=context,
                    start_pos=0,
                    context=context,
                    corpus=corpus,
                )
            )
        # Decode, at every context the program quotes.
        for context in (first_prune, 8000, 32000, 200001, 1000001):
            cases.append(
                dict(
                    label=f"decode_ratio{fine}_{context}_{corpus}",
                    ratio=fine,
                    top_k=top_k,
                    window=window,
                    span=1,
                    start_pos=context - 1,
                    context=context,
                    corpus=corpus,
                )
            )
    # The unranked group: no scores, every completed group taken.
    coarse = max(ranked)
    for context in (first_prune, 8000, 200001):
        cases.append(
            dict(
                label=f"decode_ratio{coarse}_{context}_dense",
                ratio=coarse,
                top_k=0,
                window=window,
                span=1,
                start_pos=context - 1,
                context=context,
                corpus="not_applicable",
            )
        )
    cases.append(
        dict(
            label=f"prefill_ratio{coarse}_{first_prune}_dense",
            ratio=coarse,
            top_k=0,
            window=window,
            span=first_prune,
            start_pos=0,
            context=first_prune,
            corpus="not_applicable",
        )
    )
    return cases


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-profile", type=Path, default=MODEL_PROFILE)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO / "results" / "abi3" / "deepseek_v4_index_selection_audit.json",
    )
    parser.add_argument("--seed", type=int, default=20260831)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    source = args.snapshot / "inference" / "model.py"
    observed = hashlib.sha256(source.read_bytes()).hexdigest()
    if observed != MODEL_SOURCE_SHA256:
        raise SystemExit(
            f"{source} has sha256 {observed}, expected {MODEL_SOURCE_SHA256}; "
            "the comparator is a transcription of a different file"
        )

    config, groups = _profile(args.model_profile)
    window = int(config["window_tokens"])
    window_results = []
    for case in (
        dict(label="window_prefill_2052", span=2052, start_pos=0, context=2052),
        dict(label="window_prefill_8000", span=8000, start_pos=0, context=8000),
        dict(label="window_decode_2052", span=1, start_pos=2051, context=2052),
        dict(label="window_decode_32000", span=1, start_pos=31999, context=32000),
        dict(
            label="window_decode_200001", span=1, start_pos=200000, context=200001
        ),
        dict(
            label="window_decode_1000001",
            span=1,
            start_pos=1000000,
            context=1000001,
        ),
    ):
        print(f"  {case['label']} ...", flush=True)
        window_results.append(run_window_case(window=window, **case))
        print(f"    agrees={window_results[-1]['agrees']}")

    # Amendment A30.  The draft window is a separate operator, so it is audited
    # separately: a padded row (fewer than ``window`` committed tokens, the only
    # case that exercises tail padding) and two saturated ones.
    dspark_results = []
    for case in (
        dict(label="dspark_decode_short_60", block=5, start_pos=60, context=61),
        dict(
            label="dspark_decode_saturated_200",
            block=5,
            start_pos=200,
            context=201,
        ),
        dict(
            label="dspark_decode_saturated_32000",
            block=5,
            start_pos=31999,
            context=32000,
        ),
    ):
        print(f"  {case['label']} ...", flush=True)
        dspark_results.append(run_dspark_window_case(window=window, **case))
        print(f"    agrees={dspark_results[-1]['agrees']}")

    results = []
    for index, case in enumerate(default_cases(config, groups)):
        print(f"  {case['label']} ...", flush=True)
        results.append(run_case(seed=args.seed + index, **case))
        last = results[-1]
        print(
            f"    agrees={last['agrees']} "
            f"prunes={last['selection_prunes']} "
            f"boundary_ties={last['rows_with_boundary_tie']}/{last['span']}"
        )

    all_results = results + window_results + dspark_results
    disagreements = [r for r in all_results if not r["agrees"]]
    document = {
        "schema": SCHEMA,
        "evidence_class": "external_reference_comparator",
        "model_id": "deepseek-v4-flash-0731",
        "comparator": {
            "kind": "released_implementation_transcription",
            "source": "inference/model.py",
            "source_sha256": MODEL_SOURCE_SHA256,
            "functions": [
                "Attention.forward window/compressed concatenation",
                "Indexer.forward",
                "get_window_topk_idxs",
                "get_compress_topk_idxs",
                "get_dspark_topk_idxs",
            ],
            "supplies_no_activation_to_the_accelerator": True,
        },
        "under_test": {
            "operator": [
                "ROUTE.INDEX_TOPK",
                "ROUTE.WINDOW_INDEX",
                "ROUTE.DSPARK_WINDOW_INDEX",
            ],
            "executed_by": "runtime/sim/engines/route.py on runtime/sim/device.py",
            "through": "a real ABI 3.0 deployment admitted by the verifier",
        },
        "seed": args.seed,
        "cases": results,
        "window_index_cases": window_results,
        "dspark_window_index_cases": dspark_results,
        "case_count": len(all_results),
        "disagreeing_cases": [r["label"] for r in disagreements],
        "all_agree": not disagreements,
        "score_value_space": {
            "bf16_positive_finite_values": BF16_POSITIVE_FINITE_VALUES,
            "context_above_which_ratio_4_candidates_cannot_all_differ": (
                4 * BF16_POSITIVE_FINITE_VALUES
            ),
            "consequence": (
                "The released index score is BF16. Above a context of "
                f"{4 * BF16_POSITIVE_FINITE_VALUES:,} the compress_ratio=4 "
                "layers hold more candidates than BF16 has positive finite "
                "values, so some candidates necessarily tie and the released "
                "model does not say which of two tied groups the top-512 "
                "keeps. Both the 200,000- and 1,000,000-token contexts this "
                "program quotes are above that line. What stays determined is "
                "how many rows are read -- 512 per query per csa layer -- "
                "which is what the byte-traffic model uses; what is not "
                "determined is which rows, and therefore neither is the token "
                "at those contexts, on any implementation."
            ),
        },
        "not_a_claim": [
            "index_score_arithmetic",
            "end_to_end_token_agreement_above_256_prompt_tokens",
            "timing_or_performance",
            "accelerator_execution_of_the_whole_model",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=1, sort_keys=True) + "\n")
    print(
        f"wrote {args.output}: {len(all_results)} cases, "
        f"all_agree={not disagreements}"
    )
    return 0 if not disagreements else 2


if __name__ == "__main__":
    raise SystemExit(main())
