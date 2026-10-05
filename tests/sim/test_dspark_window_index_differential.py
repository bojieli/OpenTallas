"""Amendment A30: ``ROUTE.DSPARK_WINDOW_INDEX`` against the released helper.

The proof this module exists to carry is differential and element-for-element.
``get_dspark_topk_idxs`` is transcribed once into NumPy, directly from
``inference/model.py`` of the pinned DeepSeek-V4-Pro-0813 snapshot, and every
index the engine writes is compared against it -- not against a summary of it,
not against a set, and not against the in-tree reference, which is a second
transcription and could be wrong in the same way.

That comparison has to be element-for-element and it has to be ordered, because
this family is the one place in the ABI where a wrong answer is numerically
invisible.  ``ATTENTION.SPARSE`` reads an index row as a *set* and treats
``0xffffffff`` as an absent lane at any position, so a row carrying the right
keys in a different order produces bit-identical attention, and a row carrying
the wrong keys produces a full, finite, fluent softmax that no operand, bound or
numeric check can refuse.  A test that compared sorted sets, or compared
attention outputs, would pass for an implementation that restored the
chronological rotation ``ROUTE.WINDOW_INDEX`` uses; a test that compared only
long contexts would pass for one that padded in the middle.  Both are checked
here explicitly.

The other half of the proof is that a substitution cannot pass: the two
operators are run over the same positions and required to disagree, each family
is required to be refused on the other's kind at neutral admission, and both
backends are required to refuse a draft window that does not state its block
size rather than deriving one from an output whose extent is the window plus
the block.
"""

from __future__ import annotations

import dataclasses

import numpy as np
import pytest

from compiler.backends.hbm_sram.plan import PlanError, _aux_ids
from compiler.backends.rom.common.program import (
    IMPLEMENTED_DRAFT_INDEX_FAMILIES,
    IMPLEMENTED_INDEX_FAMILIES,
    RomLowering,
    RomLoweringError,
)
from compiler.backends.rom.deepseek_v4 import (
    deepseek_v4_rom_capability,
    deepseek_v4_rom_policy,
)
from compiler.ir.v3.kernel_ir import (
    Entrypoint,
    Kernel,
    KernelGraph,
    Tensor,
    check_neutral,
)
from compiler.ir.v3.lowering import (
    INDEX_FAMILIES,
    KERNEL_TO_ENGINE,
    check_index_family,
    engine_for,
)
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.capability import Capability
from runtime.abi3.constants import (
    CompletionStatus,
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
from runtime.abi3.deployment import ObjectSource
from runtime.abi3.descriptors import Phase, Symbol
from runtime.reference.indexing import dspark_window_indices, window_indices
from runtime.sim.device import Device

# Importing the engine module registers its (family, subopcode) handlers.
import runtime.sim.engines.route  # noqa: F401


# ---------------------------------------------------------------------------
# The released helper, transcribed
# ---------------------------------------------------------------------------
def released_dspark_topk_idxs(
    window_size: int, bsz: int, block_size: int, start_pos: int
) -> np.ndarray:
    """``get_dspark_topk_idxs``, line for line, in NumPy.

    From ``inference/model.py`` of the pinned Pro-0813 snapshot::

        @lru_cache(1)
        def get_dspark_topk_idxs(window_size, bsz, block_size, start_pos):
            assert start_pos > 0
            matrix = torch.cat([torch.arange(min(window_size, start_pos + 1)),
                                window_size + torch.arange(block_size)])
            return matrix.int().view(1, 1, -1).expand(
                bsz, block_size, -1).contiguous()

    ``expand`` is the whole semantics of the second axis: one row is computed
    and every draft query gets that row, so attention inside the draft block is
    bidirectional.  It is written out here as an explicit broadcast rather than
    a loop, so that a reader can see there is no per-row term to get wrong.
    """
    assert start_pos > 0
    matrix = np.concatenate(
        [
            np.arange(min(window_size, start_pos + 1), dtype=np.int64),
            window_size + np.arange(block_size, dtype=np.int64),
        ]
    )
    return np.broadcast_to(
        matrix.astype(np.int32).reshape(1, 1, -1),
        (bsz, block_size, matrix.size),
    ).copy()


#: ``(window_size, block_size, start_pos)``.
#:
#: Chosen to straddle every boundary the row has.  ``start_pos + 1`` below the
#: window is the padded case and the *only* one that exercises tail padding;
#: ``start_pos + 1`` equal to the window is the exact saturation point;
#: ``start_pos`` far past it is the case a modulo-reducing implementation would
#: get wrong.  ``(128, 5, ...)`` is the released profile; the small windows are
#: there because an off-by-one hides easily behind 128, and ``block_size`` of
#: one and four make sure nothing depends on the released block being five.
CASES = [
    (128, 5, 1),
    (128, 5, 60),
    (128, 5, 126),
    (128, 5, 127),
    (128, 5, 128),
    (128, 5, 200),
    (128, 5, 4000),
    (8, 3, 1),
    (8, 3, 3),
    (8, 3, 6),
    (8, 3, 7),
    (8, 3, 8),
    (8, 3, 40),
    (16, 1, 15),
    (4, 4, 2),
    (64, 8, 1000),
]


# ---------------------------------------------------------------------------
# harness
# ---------------------------------------------------------------------------
def capability(*, max_context_positions: int = 4096) -> Capability:
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
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 16,
            "max_retired_work": 1 << 24,
            "max_events": 256,
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": max_context_positions,
            "max_expert_ids": 1024,
            "max_topk": 64,
            "max_vocabulary": 1 << 17,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=("bf16_bf16_fp32_sequential_rne_v1",),
        engines={"route": {"queues": 1}},
        memory={"sram": {"bytes": 1 << 26}},
        technology_view="engine-conformance",
    )
    cap.validate()
    return cap


class Build:
    """A minimal single-transaction deployment, as the ROUTE engine tests use."""

    def __init__(self, *, max_context_positions: int = 4096) -> None:
        self.capability = capability(max_context_positions=max_context_positions)
        self.builder = DeploymentBuilder(
            target_id="a30-test",
            model_id="a30-test",
            backend="test",
            capability=self.capability,
        )
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=1 << 26,
            sram_bytes_per_node=1 << 26,
        )
        self._initial: dict[int, bytes] = {}
        self._schedule: int | None = None

    def _scratch(self, nbytes: int) -> int:
        return self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=nbytes,
            source=ObjectSource.zeros(nbytes),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def input_view(self, values: np.ndarray) -> int:
        data = np.ascontiguousarray(values).tobytes()
        oid = self._scratch(len(data))
        self._initial[oid] = data
        return self.builder.tensor_view(
            object_id=oid,
            dtype=DType.U32,
            dims=list(values.shape),
            permissions=int(Permission.READ),
        )

    def output_view(self, dims) -> int:
        count = int(np.prod(dims))
        return self.builder.tensor_view(
            object_id=self._scratch(count * 4),
            dtype=DType.U32,
            dims=list(dims),
            permissions=int(Permission.READ | Permission.WRITE),
        )

    def emit(self, sub, inputs, outputs, aux) -> None:
        if self._schedule is None:
            self._schedule = self.builder.schedule(
                engine_family=Major.ROUTE,
                tile_rows=1,
                tile_cols=1,
                tile_depth=1,
                bank_mask=0b1,
                max_outstanding=1,
            )
        op = self.builder.operator(
            engine_family=Major.ROUTE,
            engine_sub=sub,
            inputs=list(inputs),
            outputs=list(outputs),
            aux=list(aux),
            numeric_profile_id=NO_ID,
            schedule_id=self._schedule,
        )
        self.builder.emit(Major.ROUTE, sub, descriptor_id=op)

    def finish(self, phase: Phase) -> Device:
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


def run_draft_window(
    *,
    window: int,
    block: int,
    start_pos: int,
    phase: Phase = Phase.DECODE,
    context: int | None = None,
    aux0=None,
    aux1=None,
    positions: np.ndarray | None = None,
):
    """Execute one ``ROUTE.DSPARK_WINDOW_INDEX`` and return (result, rows)."""

    context = start_pos + 1 if context is None else context
    build = Build(max_context_positions=max(4096, start_pos + block + 2))
    if positions is None:
        positions = start_pos + np.arange(block, dtype=np.uint32)
    src = build.input_view(positions.astype(np.uint32))
    out = build.output_view((block, window + block))
    build.emit(
        int(Route.DSPARK_WINDOW_INDEX),
        [src],
        [out],
        aux=[
            window if aux0 is None else aux0,
            block if aux1 is None else aux1,
            int(Symbol.CONTEXT_LENGTH),
        ],
    )
    device = build.finish(phase)
    symbols = {int(Symbol.CONTEXT_LENGTH): context}
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    if result.status != CompletionStatus.SUCCESS:
        return result, None
    view = device.views.resolve(out, {}, symbols)
    rows = np.array(device.views.read_array(view)).reshape(block, window + block)
    return result, rows


def run_window(*, window: int, positions: np.ndarray, context: int, phase: Phase):
    """Execute one ``ROUTE.WINDOW_INDEX``, for the side-by-side comparison."""

    span = int(positions.size)
    build = Build(max_context_positions=max(4096, context + 2))
    src = build.input_view(positions.astype(np.uint32))
    out = build.output_view((span, window))
    build.emit(
        int(Route.WINDOW_INDEX),
        [src],
        [out],
        aux=[window, 0, int(Symbol.CONTEXT_LENGTH)],
    )
    device = build.finish(phase)
    symbols = {int(Symbol.CONTEXT_LENGTH): context}
    result = device.run_transaction(
        device.create_session(), entrypoint_id=0, symbols=symbols
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    view = device.views.resolve(out, {}, symbols)
    return np.array(device.views.read_array(view)).reshape(span, window)


def padded(released_rows: np.ndarray, window: int, block: int) -> np.ndarray:
    """The released row placed in a ``[block, window + block]`` output.

    Padding is a *tail*: the two segments stay contiguous at columns
    ``0 .. h + block``, and ``0xffffffff`` runs from there to the end.  It is
    not interior padding that would hold the draft segment at fixed columns
    ``window .. window + block``, which amendment A6's tail-padding rule and
    A19's suffix check both forbid, and which would be wrong only for a context
    shorter than the window.
    """
    expected = np.full((block, window + block), NO_ID, dtype=np.uint32)
    expected[:, : released_rows.shape[1]] = released_rows.astype(np.uint32)
    return expected


# ---------------------------------------------------------------------------
# The differential proof
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("window,block,start_pos", CASES)
def test_decode_output_equals_the_released_helper_element_for_element(
    window, block, start_pos
):
    released = released_dspark_topk_idxs(window, 1, block, start_pos)
    assert released.shape == (1, block, min(window, start_pos + 1) + block)

    result, rows = run_draft_window(
        window=window, block=block, start_pos=start_pos
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    expected = padded(released[0], window, block)
    assert np.array_equal(rows, expected), (
        f"window={window} block={block} start_pos={start_pos}\n"
        f"engine   {rows[0][:12]}\nreleased {expected[0][:12]}"
    )
    # Every produced index is counted, and only the produced ones.
    produced = block * released.shape[2]
    assert result.counters["route.topk_candidates"] == produced


@pytest.mark.parametrize("window,block,start_pos", CASES)
def test_prefill_is_refused_rather_than_given_a_row_nothing_defines(
    window, block, start_pos
):
    """The second phase, told honestly.

    ``DSparkAttention.forward`` fills its cache and returns when
    ``start_pos == 0``, so ``get_dspark_topk_idxs`` is never reached in prefill
    and asserts ``start_pos > 0``.  There is therefore no released prefill row
    to be differential against, and the operator traps instead of reusing the
    decode rule -- which would be the same invisible substitution the family
    gate exists to stop, committed by the implementation rather than by the
    graph.  ``ROUTE.WINDOW_INDEX`` has two phase behaviours; this operator has
    one, deliberately.
    """
    result, _ = run_draft_window(
        window=window, block=block, start_pos=start_pos, phase=Phase.PREFILL
    )
    assert result.status == CompletionStatus.FAILED
    assert "decode operator" in result.message
    assert "start_pos > 0" in result.message


@pytest.mark.parametrize("bsz", [1, 2, 5])
def test_the_row_is_identical_across_every_draft_query_and_every_request(bsz):
    """``expand``, not a per-row computation.

    A causal variant of this operator would be the released one with its point
    removed: the drafts would stop seeing each other, become independent, and
    acceptance would collapse toward the single-token case while the tokens
    stayed grammatical.  So the broadcast is asserted directly, against the
    released expansion over both axes it expands on.
    """
    window, block, start_pos = 128, 5, 200
    released = released_dspark_topk_idxs(window, bsz, block, start_pos)
    _, rows = run_draft_window(window=window, block=block, start_pos=start_pos)
    for request in range(bsz):
        assert np.array_equal(
            rows, padded(released[request], window, block)
        )
    assert len({tuple(int(v) for v in row) for row in rows}) == 1


def test_the_saturated_history_is_slot_ascending_and_not_chronological():
    """The easiest thing to 'fix' wrongly, asserted so it cannot be.

    Every other decode window row in this ABI is in chronological ring order,
    and two sentences of the frozen documents say so as if it were general.
    ``get_dspark_topk_idxs`` does not rotate -- unlike ``get_window_topk_idxs``
    -- so a saturated history here is ``0 .. window - 1``.  The rotation names
    the *same set* of keys, so restoring it would leave ``sparse_attn``
    numerically identical and no output comparison could see it.  The order is
    therefore asserted against the released row itself.
    """
    window, block, start_pos = 128, 5, 200
    _, rows = run_draft_window(window=window, block=block, start_pos=start_pos)
    history = rows[0][:window]
    assert np.array_equal(history, np.arange(window, dtype=np.uint32))

    chronological = np.array(
        [(start_pos - window + 1 + i) % window for i in range(window)],
        dtype=np.uint32,
    )
    assert not np.array_equal(history, chronological)
    # ... and the two are indistinguishable to the consumer, which is why the
    # ordered comparison above is the only thing that separates them.
    assert set(history.tolist()) == set(chronological.tolist())


@pytest.mark.parametrize("window,block,start_pos", CASES)
def test_padding_is_a_suffix_and_only_a_short_context_has_any(
    window, block, start_pos
):
    _, rows = run_draft_window(window=window, block=block, start_pos=start_pos)
    entries = min(window, start_pos + 1) + block
    for row in rows:
        pad = np.asarray(row) == NO_ID
        assert not pad[:entries].any()
        assert pad[entries:].all()
    if start_pos + 1 >= window:
        assert entries == window + block  # saturated: no padding at all


@pytest.mark.parametrize("window,block,start_pos", CASES)
def test_the_engine_agrees_with_the_in_tree_reference_as_well(
    window, block, start_pos
):
    """The second transcription, checked against the first.

    ``runtime.reference.indexing.dspark_window_indices`` is independent of the
    engine and of the NumPy transcription above.  Agreeing with both is what
    makes a shared mistake unlikely rather than merely undetected.
    """
    _, rows = run_draft_window(window=window, block=block, start_pos=start_pos)
    reference = np.asarray(
        dspark_window_indices(window, 1, block, start_pos)[0], dtype=np.int64
    )
    assert np.array_equal(
        rows, padded(reference, window, block)
    )


# ---------------------------------------------------------------------------
# A substitution cannot pass
# ---------------------------------------------------------------------------
def test_the_two_operators_do_not_produce_the_same_indices():
    """Four independent differences, at the same operand row.

    Both operators take one U32 position vector and write U32 KV rows of the
    same fused operand, so nothing about the operand, the bounds or the
    arithmetic separates them.  What separates them is the rows themselves.
    """
    window, block, start_pos = 128, 5, 200
    positions = start_pos + np.arange(block, dtype=np.uint32)
    context = start_pos + 1

    _, draft = run_draft_window(
        window=window, block=block, start_pos=start_pos
    )
    sliding = run_window(
        window=window,
        positions=np.full(block, start_pos, dtype=np.uint32),
        context=context,
        phase=Phase.DECODE,
    )
    per_query = run_window(
        window=window, positions=positions, context=context + block,
        phase=Phase.DECODE,
    )

    # 1. fixed versus sliding, and 2. broadcast versus per-row.
    assert len({tuple(int(v) for v in row) for row in draft}) == 1
    assert len({tuple(int(v) for v in row) for row in per_query}) == block
    # 3. two disjoint segments: the draft rows live at and above the window
    #    capacity, in an address range the window operator cannot name at all.
    assert set(range(window, window + block)) <= set(draft[0].tolist())
    assert max(int(v) for v in sliding.reshape(-1)) < window
    # 4. slot-enumerated versus modulo-reduced.
    assert not np.array_equal(draft[0][:window], sliding[0])
    assert np.array_equal(
        sliding[0],
        np.asarray(window_indices(window, 1, 1, start_pos)[0][0], dtype=np.uint32),
    )


def test_each_family_is_refused_on_the_other_kind_at_neutral_admission():
    """The pair that carries A30, stated in the rule's own terms.

    ``INDEX_FAMILIES['WINDOW_INDEX']`` is unchanged by this amendment, which is
    the single most valuable property of choosing a new operator over a second
    family: the frozen entry and the assertions that pin it survive verbatim.
    """
    assert INDEX_FAMILIES["WINDOW_INDEX"] == frozenset({"causal_circular_window"})
    assert INDEX_FAMILIES["DSPARK_WINDOW_INDEX"] == frozenset(
        {"causal_window_then_current_draft"}
    )

    refused = check_index_family(
        "WINDOW_INDEX", {"index_family": "causal_window_then_current_draft"}
    )
    assert refused and "causal_circular_window" in refused[0]
    mirrored = check_index_family(
        "DSPARK_WINDOW_INDEX", {"index_family": "causal_circular_window"}
    )
    assert mirrored and "causal_window_then_current_draft" in mirrored[0]

    assert (
        check_index_family(
            "DSPARK_WINDOW_INDEX",
            {"index_family": "causal_window_then_current_draft"},
        )
        == []
    )
    assert (
        check_index_family(
            "WINDOW_INDEX", {"index_family": "causal_circular_window"}
        )
        == []
    )


def test_the_substitution_changes_the_subopcode():
    """Which is what makes it visible to the engine and to both backends."""
    window = KERNEL_TO_ENGINE["WINDOW_INDEX"]
    draft = KERNEL_TO_ENGINE["DSPARK_WINDOW_INDEX"]
    assert window.family is draft.family is Major.ROUTE
    assert int(window.sub) == int(Route.WINDOW_INDEX) == 0x06
    assert int(draft.sub) == int(Route.DSPARK_WINDOW_INDEX) == 0x07
    # Same operand row, different operator: the row is not what tells them
    # apart, and an implementation that guessed from the operands would have
    # nothing to go on.
    assert (window.inputs, window.outputs) == (draft.inputs, draft.outputs)


# ---------------------------------------------------------------------------
# Engine refusals
# ---------------------------------------------------------------------------
def test_the_engine_requires_both_immediates():
    """Neither may be derived, because the output extent is their sum.

    ``ROUTE.WINDOW_INDEX`` may take its window from the output's own column
    count.  Inherited here by copy that fallback is actively wrong: a 128-slot
    ring written into a ``[5, 133]`` output would derive a window of 133, and
    every history index from 128 up would address a draft row -- a legal KV row,
    and the wrong one.
    """
    for aux0, aux1 in ((NO_ID, 5), (128, NO_ID), (NO_ID, NO_ID)):
        result, _ = run_draft_window(
            window=128, block=5, start_pos=200, aux0=aux0, aux1=aux1
        )
        assert result.status == CompletionStatus.FAILED
        assert "aux_id_0" in result.message and "aux_id_1" in result.message


def test_the_engine_checks_the_two_shape_identities():
    result, _ = run_draft_window(window=128, block=5, start_pos=200, aux0=64)
    assert result.status == CompletionStatus.FAILED
    assert "draft block" in result.message


def test_the_engine_requires_the_consecutive_position_run():
    """Row 0 is the request cursor, so the vector's shape is load-bearing.

    Both backends build this vector as ``POSITION_START + row`` over the
    operator's own output rows.  If either ever built it differently for a
    block-shaped output, row 0 would stop being ``POSITION_START`` and the
    history prefix would silently change length -- still all legal KV rows.
    """
    result, _ = run_draft_window(
        window=128,
        block=5,
        start_pos=200,
        positions=np.array([200, 200, 200, 200, 200], dtype=np.uint32),
    )
    assert result.status == CompletionStatus.FAILED
    assert "consecutive run" in result.message


def test_the_engine_refuses_the_prefill_cursor():
    result, _ = run_draft_window(
        window=128,
        block=5,
        start_pos=200,
        positions=np.arange(5, dtype=np.uint32),
        context=8,
    )
    assert result.status == CompletionStatus.FAILED
    assert "start_pos > 0" in result.message


def test_the_engine_bounds_the_cursor_by_the_context_but_not_the_drafts():
    """The drafts are positions the request has not committed yet.

    Bounding them by ``CONTEXT_LENGTH`` would refuse exactly the speculation
    this operator indexes, so only the cursor is checked.
    """
    result, rows = run_draft_window(
        window=128, block=5, start_pos=200, context=201
    )
    assert result.status == CompletionStatus.SUCCESS, result.message
    assert rows is not None
    result, _ = run_draft_window(window=128, block=5, start_pos=200, context=200)
    assert result.status == CompletionStatus.FAILED
    assert "visible positions" in result.message


# ---------------------------------------------------------------------------
# Backend admission
# ---------------------------------------------------------------------------
def _draft_kernel(**overrides) -> Kernel:
    attributes = {
        "index_family": "causal_window_then_current_draft",
        "window_size": 128,
        "draft_block_size": 5,
        "padding_index": -1,
    }
    attributes.update(overrides.pop("attributes", {}))
    fields = dict(
        index=0,
        kernel_id="dspark.layer00.window_indices",
        kind="DSPARK_WINDOW_INDEX",
        inputs=("pos0",),
        outputs=("idx0",),
        numeric_contract="indexing_dspark_window_indices_v1",
        iteration_domain={"tokens": 5, "width": 133},
        phases=("decode",),
        layer=0,
        attributes=attributes,
    )
    fields.update(overrides)
    return Kernel(**fields)


@pytest.fixture(scope="module")
def draft_graph() -> tuple[KernelGraph, dict[str, Tensor]]:
    """A two-layer graph shaped like the speculative profile's draft windows."""
    tensors: list[Tensor] = []
    kernels: list[Kernel] = []
    for layer in range(2):
        tensors += [
            Tensor(f"pos{layer}", "u32", (5,), "activation"),
            Tensor(f"idx{layer}", "u32", (5, 133), "activation"),
        ]
        kernels.append(
            _draft_kernel(
                index=layer,
                kernel_id=f"dspark.layer{layer:02d}.window_indices",
                inputs=(f"pos{layer}",),
                outputs=(f"idx{layer}",),
                layer=layer,
            )
        )
    graph = KernelGraph(
        model_id="a30-draft-window",
        source={"family": "test"},
        symbols=(),
        tensors=tuple(tensors),
        states=(),
        kernels=tuple(kernels),
        entrypoints=tuple(
            Entrypoint(phase=p, inputs=("pos0",), outputs=("idx1",), states=())
            for p in ("prefill", "decode")
        ),
    )
    assert check_neutral(graph) == []
    return graph, {t.tensor_id: t for t in tensors}


def test_hbm_states_the_window_and_the_block_and_refuses_a_missing_one(
    draft_graph,
):
    graph, tensors = draft_graph
    kernel = graph.kernels[0]
    aux = _aux_ids(
        kernel, engine_for(kernel.kind), tensors, graph, span_max=5, groups=1
    )
    assert aux == (128, 5, int(Symbol.CONTEXT_LENGTH))

    for name in ("window_size", "draft_block_size"):
        # Missing, and zero: a declared zero is not a smaller capacity, it is
        # an undeclared one wearing an integer, and deriving either from the
        # output is the mistake this branch exists to refuse.
        for attributes in (
            {k: v for k, v in kernel.attributes.items() if k != name},
            {**kernel.attributes, name: 0},
        ):
            broken = dataclasses.replace(kernel, attributes=attributes)
            with pytest.raises(PlanError, match="DSPARK_WINDOW_INDEX"):
                _aux_ids(
                    broken,
                    engine_for(broken.kind),
                    tensors,
                    graph,
                    span_max=5,
                    groups=1,
                )


@pytest.fixture(scope="module")
def rom_lowering(draft_graph) -> RomLowering:
    graph, _ = draft_graph
    return RomLowering(
        graph,
        deepseek_v4_rom_capability(
            max_context_positions=1024,
            vocabulary_size=32,
            expert_count=8,
            experts_per_token=2,
            tile_rom_bytes=1 << 16,
            tiles_per_reticle=8,
        ),
        deepseek_v4_rom_policy(tile_rom_bytes=1 << 16, tiles_per_reticle=8),
    )


def test_rom_states_the_window_and_the_block_and_refuses_a_missing_one(
    rom_lowering, draft_graph
):
    graph, _ = draft_graph
    kernel = graph.kernels[0]
    assert rom_lowering._aux(
        kernel, Major.ROUTE, int(Route.DSPARK_WINDOW_INDEX)
    ) == [128, 5, int(Symbol.CONTEXT_LENGTH)]

    for name in ("window_size", "draft_block_size"):
        for attributes in (
            {k: v for k, v in kernel.attributes.items() if k != name},
            {**kernel.attributes, name: 0},
        ):
            broken = dataclasses.replace(kernel, attributes=attributes)
            with pytest.raises(RomLoweringError, match="DSPARK_WINDOW_INDEX"):
                rom_lowering._aux(
                    broken, Major.ROUTE, int(Route.DSPARK_WINDOW_INDEX)
                )


def test_rom_refuses_each_family_on_the_other_subopcode(rom_lowering, draft_graph):
    graph, _ = draft_graph
    kernel = graph.kernels[0]
    assert IMPLEMENTED_INDEX_FAMILIES == frozenset({"causal_circular_window"})
    assert IMPLEMENTED_DRAFT_INDEX_FAMILIES == frozenset(
        {"causal_window_then_current_draft"}
    )

    wrong = dataclasses.replace(
        kernel,
        attributes={**kernel.attributes, "index_family": "causal_circular_window"},
    )
    with pytest.raises(RomLoweringError) as refusal:
        rom_lowering._aux(wrong, Major.ROUTE, int(Route.DSPARK_WINDOW_INDEX))
    message = str(refusal.value)
    assert "causal_circular_window" in message
    assert "ROUTE.DSPARK_WINDOW_INDEX" in message
    assert "broadcast" in message

    onto_window = dataclasses.replace(
        kernel,
        kind="WINDOW_INDEX",
        attributes={
            "index_family": "causal_window_then_current_draft",
            "window_size": 128,
        },
    )
    with pytest.raises(RomLoweringError) as refusal:
        rom_lowering._aux(onto_window, Major.ROUTE, int(Route.WINDOW_INDEX))
    message = str(refusal.value)
    assert "causal_window_then_current_draft" in message
    assert "ROUTE.WINDOW_INDEX" in message
    assert "causal_circular_window" in message
