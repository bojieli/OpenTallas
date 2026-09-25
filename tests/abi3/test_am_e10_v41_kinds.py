"""AM-E10: the four DeepSeek-V4.1-Flash kinds, as a three-party change.

A kind that is not in :data:`compiler.ir.v3.kernel_ir.OPERATION_KINDS`, in
:data:`compiler.ir.v3.lowering.KERNEL_TO_ENGINE` and in a registered engine is
not an addition -- it is a compile error waiting for the first deployment that
uses it.  This module checks all three parties for ``BLOCK_MAX``,
``CANDIDATE_MASK``, ``NGRAM_HASH`` and ``ENGRAM_GATE``, checks that neither a
kind name nor any attribute key they introduce carries a backend term, and
checks the absent-operand rule of ``ROUTE.INDEX_TOPK``'s new slot 3 in both
directions: present and absent must both be legal, and with the slot absent the
engine must produce the result, and the counters, that it produced before the
slot existed.

Every expectation below is computed in the test -- plain Python integer
arithmetic, plain NumPy, or a binary64 recomputation -- never by calling the
engine a second time.

**What this module does not establish**: see :data:`CLAIM_BOUNDARY`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pytest

import runtime.sim.engines.dma as dma_engine  # noqa: F401  (registers handlers)
import runtime.sim.engines.route as route_engine  # noqa: F401
import runtime.sim.engines.vector as vector_engine  # noqa: F401
from compiler.ir.v3.kernel_ir import DTYPES, FORBIDDEN_TERMS, OPERATION_KINDS
from compiler.ir.v3.lowering import (
    ABSENT_OPERANDS,
    KERNEL_TO_ENGINE,
    OPTIONAL_INPUT_SLOTS,
    check_operand_slots,
)
from runtime.abi3.builder import DeploymentBuilder
from runtime.abi3.constants import (
    NO_ID,
    Dma,
    DType,
    Major,
    Permission,
    ReductionOrder,
    Route,
    StorageClass,
    TopologyClass,
    Vector,
)
from runtime.abi3.deployment import Deployment, ObjectSource, Segment
from runtime.abi3.descriptors import Phase, Symbol
from runtime.abi3.fixture import fixture_capability
from runtime.reference.candidate_pool import (
    CANDIDATE_MASK_ABSENT_ID,
    block_max_rows,
    select_candidate_mask,
)
from runtime.reference.engram import (
    ENGRAM_GATE_EPSILON_BINARY32,
    engram_gate as reference_engram_gate,
    ngram_row_ids,
)
from runtime.sim.counters import CounterSet
from runtime.sim.engine import EngineContext, EngineError, dispatch, implemented
from runtime.sim.engines.route import PAD_INDEX
from runtime.sim.memory import DeviceMemory, ViewResolver

READ = int(Permission.READ)
IMMUTABLE = int(Permission.READ | Permission.IMMUTABLE)
READ_WRITE = int(Permission.READ | Permission.WRITE)

#: The four kinds this amendment adds, with the engine sub-op each lowers to.
AM_E10_KINDS: dict[str, tuple[Major, int]] = {
    "BLOCK_MAX": (Major.ROUTE, int(Route.BLOCK_MAX)),
    "CANDIDATE_MASK": (Major.ROUTE, int(Route.CANDIDATE_MASK)),
    "NGRAM_HASH": (Major.DMA, int(Dma.NGRAM_HASH)),
    "ENGRAM_GATE": (Major.VECTOR, int(Vector.ENGRAM_GATE)),
}

#: The attribute keys these kinds introduce into a neutral kernel, from plan
#: section 5: ``BLOCK_MAX(scores, block)``, ``CANDIDATE_MASK(block_ids, block,
#: width)``, ``NGRAM_HASH(token_ids, order, head)``, and the ``absent_operands``
#: row that makes ``INDEX_TOPK``'s mask optional.
AM_E10_ATTRIBUTE_KEYS: tuple[str, ...] = (
    "block",
    "width",
    "order",
    "head",
    ABSENT_OPERANDS,
)

#: The dtype AM-E10 adds beside the four kinds, and the one it must not be
#: confused with.
AM_E10_DTYPE = "fp4_e2m1_s16_e4m3"
MXFP4_DTYPE = "mxfp4_e2m1"

#: What a passing run of this module does **not** establish.  Every entry is a
#: gap, not a caveat: a reader who treats this file as evidence of agreement
#: with the released DeepSeek-V4.1-Flash model would be wrong in each of these
#: ways.
CLAIM_BOUNDARY: tuple[str, ...] = (
    "Not vendor agreement for the gate or the pool: runtime/reference/"
    "{engram,candidate_pool}.py are independent statements of the plan's "
    "mechanisms, and both record that the pinned inference/engram.py and "
    "inference/model.py are absent from this checkout. Agreement here is "
    "agreement with those references.",
    "Not a released row assignment: DMA.NGRAM_HASH reproduces the pinned "
    "NgramHashState.forward identity, but its multipliers, column primes and "
    "column offsets are operands. A campaign that has not bound the released "
    "tables to those operands has not checked a released row id.",
    "Not a qualified operand map: the plan's ENGRAM_GATE row names five "
    "operands and an ABI 3.0 operator admits four input views, so key and "
    "value -- the two halves of one projection -- share a view. No committed "
    "exporter emits this packing yet, so the map is checked against the "
    "reference and the plan, not against a graph a backend admitted.",
    "Not a numeric qualification: no numeric-contract row is published here "
    "for block_max_ordered_ieee_v1, candidate_mask_v1, ngram_hash_u32_v1 or "
    "engram_gate_fp32_v1. Bit agreement with the reference is shown; the "
    "qualification record is WP-H and DS41-N5 work.",
    "Not RTL correlation: this module executes the functional simulator only. "
    "No Icarus or Verilator run, and therefore no simulators_agree flag, is "
    "part of it.",
    "Not the frozen operand row: KERNEL_TO_ENGINE['INDEX_TOPK'] still declares "
    "three input slots while OPTIONAL_INPUT_SLOTS names slot 3, so a kernel "
    "that states where the mask is remains inadmissible. Three tests below "
    "fail on exactly that, and the fix is in a file this unit does not own.",
)


# ---------------------------------------------------------------------------
# Harness: a minimal deployment plus the engine context that executes it
# ---------------------------------------------------------------------------
class Bench:
    """Build views, dispatch one engine operator, read the result back.

    Deliberately the direct-dispatch shape of ``tests/sim`` rather than a whole
    transaction: what is under test is an engine's operand reading, and a
    microsequencer program between the test and the engine would only add a
    second reason for a failure.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.capability = fixture_capability()
        self.builder = DeploymentBuilder(
            target_id="am-e10",
            model_id="am-e10",
            backend="test",
            capability=self.capability,
        )
        self.builder.topology(topology_class=TopologyClass.SINGLE_CHIP, node_count=1)
        self.files = 0
        self.outputs: dict[int, tuple[int, tuple[int, ...], np.dtype]] = {}
        self.ctx: EngineContext | None = None
        self._schedules: dict[int, int] = {}

    # -- objects and views ----------------------------------------------
    def _constant(self, payload: bytes) -> int:
        self.files += 1
        name = f"object{self.files}.bin"
        (self.root / name).write_bytes(payload)
        segment = Segment(name, 0, len(payload), None)
        source = ObjectSource("segments", len(payload), (segment,))
        return self.builder.memory_object(
            storage_class=StorageClass.HBM,
            size_bytes=len(payload),
            source=source,
            permissions=IMMUTABLE,
            content_digest=bytes(32),
        )

    def input_view(
        self, array: np.ndarray, dtype: DType, *, dims: Sequence[int] | None = None
    ) -> int:
        payload = np.ascontiguousarray(array).tobytes()
        return self.builder.tensor_view(
            object_id=self._constant(payload),
            dtype=dtype,
            dims=list(dims if dims is not None else array.shape),
            permissions=READ,
        )

    def output_view(self, dims: Sequence[int], dtype: DType) -> int:
        numpy_dtype = {
            DType.U8: np.dtype(np.uint8),
            DType.U32: np.dtype(np.uint32),
            DType.BF16: np.dtype(np.uint16),
            DType.FP32: np.dtype(np.float32),
        }[dtype]
        count = int(np.prod(dims))
        object_id = self.builder.memory_object(
            storage_class=StorageClass.SRAM,
            size_bytes=count * numpy_dtype.itemsize,
            source=ObjectSource.zeros(count * numpy_dtype.itemsize),
            permissions=READ_WRITE,
        )
        view = self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            permissions=READ_WRITE,
        )
        self.outputs[view] = (object_id, tuple(int(d) for d in dims), numpy_dtype)
        return view

    # -- descriptors -----------------------------------------------------
    def numeric(self, **kwargs: Any) -> int:
        kwargs.setdefault("contract", "am-e10-test")
        return self.builder.numeric(**kwargs)

    def operator(
        self,
        family: Major,
        sub: int,
        inputs: Sequence[int] = (),
        outputs: Sequence[int] = (),
        *,
        aux: Sequence[int] = (),
        numeric_profile_id: int = NO_ID,
    ) -> int:
        schedule = self._schedules.get(int(family))
        if schedule is None:
            schedule = self.builder.schedule(
                engine_family=family,
                tile_rows=1,
                tile_cols=1,
                tile_depth=1,
                bank_mask=0b1,
                max_outstanding=1,
            )
            self._schedules[int(family)] = schedule
        return self.builder.operator(
            engine_family=family,
            engine_sub=int(sub),
            inputs=list(inputs),
            outputs=list(outputs),
            aux=list(aux),
            numeric_profile_id=numeric_profile_id,
            schedule_id=schedule,
        )

    # -- execution -------------------------------------------------------
    def bind(self, symbols: dict[int, int] | None = None) -> "Bench":
        deployment = Deployment(
            deployment_id=1,
            generation=1,
            target_id="am-e10",
            model_id="am-e10",
            backend="test",
            topology_class=int(TopologyClass.SINGLE_CHIP),
            capability_digest="",
            table=self.builder.table,
            program=b"",
            objects=dict(self.builder.objects),
            entrypoints=(),
            required_features=bytes(32),
            root=self.root,
        )
        memory = DeviceMemory(deployment, root=self.root)
        self.ctx = EngineContext(
            table=deployment.table,
            memory=memory,
            views=ViewResolver(deployment, memory),
            counters=CounterSet(),
            loops={},
            symbols=dict(symbols or {}),
        )
        self.memory = memory
        return self

    def run(
        self,
        family: Major,
        sub: int,
        operator_id: int,
        *,
        symbols: dict[int, int] | None = None,
    ) -> None:
        if self.ctx is None:
            self.bind(symbols)
        dispatch(self.ctx, int(family), int(sub), self.builder.table[operator_id])

    def result(self, view_id: int) -> np.ndarray:
        object_id, dims, numpy_dtype = self.outputs[view_id]
        count = int(np.prod(dims))
        payload = self.memory[object_id].read(0, count * numpy_dtype.itemsize)
        return np.frombuffer(payload, dtype=numpy_dtype).reshape(dims).copy()

    @property
    def counters(self) -> CounterSet:
        assert self.ctx is not None
        return self.ctx.counters


@pytest.fixture()
def bench(tmp_path: Path) -> Bench:
    return Bench(tmp_path)


def fp32_profile(bench: Bench, *, epsilon: float = 0.0) -> int:
    epsilon_bits = (
        int(np.asarray([np.float32(epsilon)], dtype=np.float32).view(np.uint32)[0])
        if epsilon
        else 0
    )
    return bench.numeric(
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
        second_input_dtype=DType.FP32,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        epsilon_bits=epsilon_bits,
    )


# ---------------------------------------------------------------------------
# Three-party presence
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("kind", sorted(AM_E10_KINDS))
def test_each_new_kind_is_a_three_party_change(kind: str) -> None:
    """IR kind, lowering row and dispatching engine, for one kind at a time."""
    family, sub = AM_E10_KINDS[kind]
    assert kind in OPERATION_KINDS, f"{kind} is not a neutral IR kind"
    assert kind in KERNEL_TO_ENGINE, f"{kind} has no frozen lowering row"
    engine = KERNEL_TO_ENGINE[kind]
    assert (int(engine.family), int(engine.sub)) == (int(family), int(sub)), (
        f"{kind} lowers to {(int(engine.family), int(engine.sub))}, not to the "
        f"ABI sub-op {(int(family), int(sub))} the amendment numbers"
    )
    assert (int(family), int(sub)) in implemented(), (
        f"no engine dispatches {family.name}.{sub:#04x}, so a deployment using "
        f"{kind} would trap on a capability fault"
    )


def test_the_new_kinds_do_not_displace_an_existing_sub_op() -> None:
    """Each new sub-op number is used by exactly one kind."""
    used: dict[tuple[int, int], list[str]] = {}
    for kind, engine in KERNEL_TO_ENGINE.items():
        used.setdefault((int(engine.family), int(engine.sub)), []).append(kind)
    for kind, (family, sub) in AM_E10_KINDS.items():
        assert used[(int(family), int(sub))] == [kind], (
            f"sub-op {family.name}.{sub:#04x} is shared by "
            f"{sorted(used[(int(family), int(sub))])}"
        )


def test_the_new_dtype_is_registered_and_is_not_mxfp4() -> None:
    """E4M3 scales per 16 are a different storage type from E8M0 per 32."""
    assert AM_E10_DTYPE in DTYPES
    assert MXFP4_DTYPE in DTYPES
    assert AM_E10_DTYPE != MXFP4_DTYPE


# ---------------------------------------------------------------------------
# Neutrality
# ---------------------------------------------------------------------------
def _offending_terms(text: str) -> list[str]:
    lowered = text.lower()
    return [term for term in FORBIDDEN_TERMS if term in lowered]


@pytest.mark.parametrize("kind", sorted(AM_E10_KINDS))
def test_a_new_kind_name_carries_no_backend_term(kind: str) -> None:
    assert _offending_terms(kind) == []


@pytest.mark.parametrize("key", AM_E10_ATTRIBUTE_KEYS)
def test_a_new_attribute_key_carries_no_backend_term(key: str) -> None:
    assert _offending_terms(key) == []


def test_the_new_dtype_name_carries_no_backend_term() -> None:
    assert _offending_terms(AM_E10_DTYPE) == []


def test_the_claim_boundary_is_stated() -> None:
    """The boundary is part of the evidence, not a comment beside it."""
    assert CLAIM_BOUNDARY
    assert all(isinstance(entry, str) and entry.strip() for entry in CLAIM_BOUNDARY)


# ---------------------------------------------------------------------------
# The absent-operand rule for INDEX_TOPK's new slot 3
# ---------------------------------------------------------------------------
def test_index_topk_slot_three_is_optional_in_the_frozen_operand_row() -> None:
    """The optional row names the mask slot."""
    assert OPTIONAL_INPUT_SLOTS["INDEX_TOPK"] == frozenset({0, 1, 2, 3})


def test_index_topk_with_every_operand_present_is_admitted() -> None:
    """Four operands and no absence declared is the fully bound form."""
    assert (
        check_operand_slots("INDEX_TOPK", ["scores", "window", "ratio", "mask"], {})
        == []
    )


def test_index_topk_accounts_for_the_mask_slot_in_its_operand_row() -> None:
    """The frozen row must have four input slots for the mask to be one of them.

    ``OPTIONAL_INPUT_SLOTS`` may name slot 3, but ``check_operand_slots`` bounds
    the accounted operands by ``KERNEL_TO_ENGINE[kind].inputs``, so a row that
    still declares three input slots refuses every kernel that *states* where
    the mask is -- present or absent.  The fix is one number in the frozen
    lowering row, ``EngineOp(Major.ROUTE, Route.INDEX_TOPK, 3, 1)`` to ``4``;
    this test fails until it is made.
    """
    assert KERNEL_TO_ENGINE["INDEX_TOPK"].inputs == 4, (
        "INDEX_TOPK's frozen operand row admits "
        f"{KERNEL_TO_ENGINE['INDEX_TOPK'].inputs} input slots, so AM-E10's "
        "mask slot cannot be accounted for"
    )


def test_index_topk_admits_the_mask_slot_declared_absent() -> None:
    """Absent must be legal, and it must be legal *stated*.

    A kernel that names its three present operands and declares slot 3 absent
    is the form a V4.1 layer without a candidate pool takes.  It is refused
    today for the arity reason the previous test states.
    """
    assert (
        check_operand_slots(
            "INDEX_TOPK", ["scores", "window", "ratio"], {ABSENT_OPERANDS: [3]}
        )
        == []
    )


def test_index_topk_admits_the_dense_masked_form() -> None:
    """Scores absent and the mask present: the dense candidate-pool form."""
    assert (
        check_operand_slots(
            "INDEX_TOPK", ["window", "ratio", "mask"], {ABSENT_OPERANDS: [0]}
        )
        == []
    )


def test_a_kind_without_an_optional_row_still_refuses_an_absent_operand() -> None:
    """The new slot is optional for ``INDEX_TOPK`` only."""
    problems = check_operand_slots("BLOCK_MAX", [], {ABSENT_OPERANDS: [0]})
    assert problems and "does not make them optional" in problems[0]


# ---------------------------------------------------------------------------
# ROUTE.BLOCK_MAX
# ---------------------------------------------------------------------------
def test_block_max_reduces_each_block_including_a_short_tail(bench: Bench) -> None:
    """Against ``runtime.reference.candidate_pool.block_max_rows``, code for code."""
    span, width, block = 3, 11, 4
    rng = np.random.default_rng(20260913)
    scores = rng.standard_normal((span, width)).astype(np.float32)
    blocks = -(-width // block)

    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((span, blocks), DType.FP32)
    operator = bench.operator(
        Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[block]
    )
    bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)

    codes = scores.view(np.uint32)
    expected = np.asarray(
        block_max_rows([row.tolist() for row in codes], block), dtype=np.uint32
    )
    assert np.array_equal(bench.result(out).view(np.uint32), expected)
    assert bench.counters["route.topk_candidates"] == span * width


def test_block_max_admits_a_masked_score_and_orders_signed_zero(bench: Bench) -> None:
    """Minus infinity is an input, and ``max(-0.0, +0.0)`` is ``+0.0``.

    A masked candidate score *is* minus infinity, so refusing it would refuse
    the reference's own padding value; and the two zeros are distinct codes, so
    which one a block selects is a bit-level statement the reference makes and
    this engine has to make the same way.
    """
    block = 4
    scores = np.array(
        [
            [-np.inf, -np.inf, -np.inf, -2.0],
            [-0.0, 0.0, -0.0, -0.0],
            [1.5, -np.inf, 0.25, -np.inf],
        ],
        dtype=np.float32,
    )
    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((3, 1), DType.FP32)
    operator = bench.operator(
        Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[block]
    )
    bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    result = bench.result(out).view(np.uint32)
    expected = np.asarray(
        block_max_rows([row.tolist() for row in scores.view(np.uint32)], block),
        dtype=np.uint32,
    )
    assert np.array_equal(result, expected)
    # Positive zero, not the negative zero that shares its value.
    assert int(result[1, 0]) == 0x00000000


def test_block_max_selects_a_bf16_code_without_converting_it(bench: Bench) -> None:
    """The block maximum is a selection: BF16 in, the same BF16 code out."""
    block = 4
    codes = np.array([[0x3F80, 0xBF80, 0x4000, 0x0000, 0x3F00, 0xFF80]], dtype=np.uint16)
    source = bench.input_view(codes, DType.BF16)
    out = bench.output_view((1, 2), DType.BF16)
    operator = bench.operator(
        Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[block]
    )
    bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    expected = np.asarray(
        block_max_rows(
            [codes[0].tolist()], block, exponent_bits=8, mantissa_bits=7
        ),
        dtype=np.uint16,
    )
    assert np.array_equal(bench.result(out), expected)


def test_block_max_refuses_an_output_that_does_not_tile(bench: Bench) -> None:
    scores = np.zeros((2, 11), dtype=np.float32)
    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((2, 2), DType.FP32)
    operator = bench.operator(Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[4])
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    assert "3 block(s)" in str(raised.value)


def test_block_max_requires_the_block_width(bench: Bench) -> None:
    """A tiling nobody declared is not inferred from two extents."""
    scores = np.zeros((2, 8), dtype=np.float32)
    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((2, 2), DType.FP32)
    operator = bench.operator(Major.ROUTE, Route.BLOCK_MAX, [source], [out])
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    assert "no block width" in str(raised.value)


def test_block_max_refuses_a_nan_score(bench: Bench) -> None:
    """The order is not total on NaNs and the conventions disagree."""
    scores = np.zeros((1, 8), dtype=np.float32)
    scores[0, 3] = np.nan
    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((1, 2), DType.FP32)
    operator = bench.operator(Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[4])
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    assert raised.value.trap_class == 6


def test_block_max_refuses_to_convert_its_score(bench: Bench) -> None:
    scores = np.zeros((1, 8), dtype=np.float32)
    source = bench.input_view(scores, DType.FP32)
    out = bench.output_view((1, 2), DType.BF16)
    operator = bench.operator(Major.ROUTE, Route.BLOCK_MAX, [source], [out], aux=[4])
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.BLOCK_MAX, operator)
    assert "VECTOR.CONVERT" in str(raised.value)


# ---------------------------------------------------------------------------
# ROUTE.CANDIDATE_MASK
# ---------------------------------------------------------------------------
def reference_plane(
    block_ids: Sequence[int], *, width: int, block: int
) -> np.ndarray:
    """Unpack the reference's packed admission words into one flag per position."""
    record = select_candidate_mask(
        [int(value) for value in block_ids], width=width, block=block
    )
    words = record["words"]
    plane = np.zeros(width, dtype=np.uint8)
    for position in range(width):
        word = words[position // 32]
        plane[position] = (word >> (position % 32)) & 1
    assert int(plane.sum()) == int(record["population"])
    return plane


def test_candidate_mask_admits_exactly_the_named_blocks(bench: Bench) -> None:
    """Against the reference plane: padding, repeats, and the pinned last block."""
    width, block = 11, 4
    ids = np.array(
        [
            [0, 1, PAD_INDEX],
            [1, 1, 1],
            [PAD_INDEX, PAD_INDEX, PAD_INDEX],
        ],
        dtype=np.uint32,
    )
    span = ids.shape[0]
    source = bench.input_view(ids, DType.U32)
    out = bench.output_view((span, width), DType.U8)
    operator = bench.operator(
        Major.ROUTE, Route.CANDIDATE_MASK, [source], [out], aux=[block]
    )
    bench.run(Major.ROUTE, Route.CANDIDATE_MASK, operator)
    result = bench.result(out)

    expected = np.stack(
        [reference_plane(ids[row], width=width, block=block) for row in range(span)]
    )
    assert np.array_equal(result, expected)
    # The last block -- positions 8..10 -- is admitted in every row, including
    # the row whose every selection slot was padding.
    assert result[:, 8:].all()
    assert result[2, :8].tolist() == [0] * 8
    assert bench.counters["route.topk_candidates"] == int(expected.sum())


def test_candidate_mask_uses_the_absent_id_the_reference_names(bench: Bench) -> None:
    assert PAD_INDEX == CANDIDATE_MASK_ABSENT_ID


def test_candidate_mask_rejects_a_block_outside_the_axis(bench: Bench) -> None:
    width, block = 11, 4  # three blocks: 0, 1, 2
    ids = np.array([[0, 3]], dtype=np.uint32)
    source = bench.input_view(ids, DType.U32)
    out = bench.output_view((1, width), DType.U8)
    operator = bench.operator(
        Major.ROUTE, Route.CANDIDATE_MASK, [source], [out], aux=[block]
    )
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.CANDIDATE_MASK, operator)
    assert raised.value.trap_class == 3
    assert "outside the 3 block(s)" in str(raised.value)
    assert bench.counters["route.rejected_ids"] == 1


def test_candidate_mask_enforces_a_declared_population_bound(bench: Bench) -> None:
    """The plan's ``candidate_pool_bound``, checked where the plane is written."""
    width, block, bound = 16, 4, 8
    ids = np.array([[0, 1, 2]], dtype=np.uint32)  # plus the pinned block 3: 16 > 8
    source = bench.input_view(ids, DType.U32)
    out = bench.output_view((1, width), DType.U8)
    operator = bench.operator(
        Major.ROUTE, Route.CANDIDATE_MASK, [source], [out], aux=[block, bound]
    )
    with pytest.raises(EngineError) as raised:
        bench.run(Major.ROUTE, Route.CANDIDATE_MASK, operator)
    assert "above the declared bound of 8" in str(raised.value)


# ---------------------------------------------------------------------------
# DMA.NGRAM_HASH
# ---------------------------------------------------------------------------
#: A small Engram column layout: two orders (2-grams and 3-grams) of three hash
#: heads, ngram-major and head-minor, with the offsets the prefix sums of the
#: primes.  Every number here is an operand of the engine, never a constant in
#: it: this is one table, not the table.
NGRAM_PRIMES = ((1009, 1013, 1019), (1021, 1031, 1033))
NGRAM_MULTIPLIERS = (0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D)
NGRAM_VOCAB = 2048
NGRAM_PAD_ID = 0


def ngram_offsets(primes: Sequence[Sequence[int]]) -> tuple[int, ...]:
    """``cumsum([0, *sizes[:-1]])`` over the flattened columns, as released."""
    flat = [int(value) for row in primes for value in row]
    offsets: list[int] = []
    running = 0
    for size in flat:
        offsets.append(running)
        running += size
    return tuple(offsets)


def ngram_column_table(primes: Sequence[Sequence[int]]) -> np.ndarray:
    """The ``[2, orders, heads]`` operand: primes then base rows."""
    prime_plane = np.asarray(primes, dtype=np.uint32)
    offset_plane = np.asarray(ngram_offsets(primes), dtype=np.uint32).reshape(
        prime_plane.shape
    )
    return np.stack((prime_plane, offset_plane))


def _ngram_operator(
    bench: Bench,
    ids: np.ndarray,
    *,
    order: int,
    heads: int,
    primes: Sequence[Sequence[int]] = NGRAM_PRIMES,
    dead: np.ndarray | None = None,
) -> tuple[int, int]:
    inputs = [
        bench.input_view(ids, DType.U32),
        bench.input_view(np.asarray(NGRAM_MULTIPLIERS, dtype=np.uint32), DType.U32),
        bench.input_view(ngram_column_table(primes), DType.U32),
    ]
    if dead is not None:
        inputs.append(bench.input_view(dead, DType.U8))
    out = bench.output_view((int(ids.size), heads), DType.U32)
    operator = bench.operator(
        Major.DMA,
        Dma.NGRAM_HASH,
        inputs,
        [out],
        aux=[order, NGRAM_PAD_ID, NGRAM_VOCAB],
    )
    return operator, out


def reference_rows(
    ids: np.ndarray,
    *,
    order: int,
    heads: int,
    primes: Sequence[Sequence[int]] = NGRAM_PRIMES,
    dead: Sequence[int] = (),
) -> np.ndarray:
    return np.asarray(
        [
            [
                int(
                    ngram_row_ids(
                        [int(value) for value in ids],
                        order=order,
                        head=head,
                        multipliers=list(NGRAM_MULTIPLIERS),
                        primes=[list(row) for row in primes],
                        offsets=list(ngram_offsets(primes)),
                        pad_id=NGRAM_PAD_ID,
                        compressed_vocab_size=NGRAM_VOCAB,
                        dead_positions=tuple(dead),
                        n_heads=heads,
                    )[position]["row_id"]
                )
                for head in range(heads)
            ]
            for position in range(int(ids.size))
        ],
        dtype=np.uint32,
    )


@pytest.mark.parametrize("order", [2, 3])
def test_ngram_hash_matches_the_pinned_reference_identity(
    bench: Bench, order: int
) -> None:
    """Against ``runtime.reference.engram.ngram_row_ids``, row id for row id."""
    heads = len(NGRAM_PRIMES[0])
    rng = np.random.default_rng(41)
    ids = rng.integers(0, NGRAM_VOCAB, size=6, dtype=np.uint32)
    operator, out = _ngram_operator(bench, ids, order=order, heads=heads)
    bench.run(Major.DMA, Dma.NGRAM_HASH, operator)
    result = bench.result(out)
    assert np.array_equal(result, reference_rows(ids, order=order, heads=heads))
    # Each column's rows live inside its own prime-sized bucket.
    offsets = ngram_offsets(NGRAM_PRIMES)
    for head in range(heads):
        column = (order - 2) * heads + head
        base = offsets[column]
        size = NGRAM_PRIMES[order - 2][head]
        assert bool(np.all((result[:, head] >= base) & (result[:, head] < base + size)))
    assert bench.counters["dma.transfers"] == 1


def test_ngram_hash_blocks_a_lookback_stickily(bench: Bench) -> None:
    """A dead position blocks that lookback and every deeper one."""
    heads = len(NGRAM_PRIMES[0])
    ids = np.array([5, 9, 17, 23, 31], dtype=np.uint32)
    dead = np.array([0, 0, 1, 0, 0], dtype=np.uint8)
    operator, out = _ngram_operator(bench, ids, order=3, heads=heads, dead=dead)
    bench.run(Major.DMA, Dma.NGRAM_HASH, operator)
    assert np.array_equal(
        bench.result(out), reference_rows(ids, order=3, heads=heads, dead=(2,))
    )


def test_ngram_hash_refuses_an_id_outside_the_compressed_vocabulary(
    bench: Bench,
) -> None:
    heads = len(NGRAM_PRIMES[0])
    ids = np.array([1, NGRAM_VOCAB, 3, 4], dtype=np.uint32)
    operator, _ = _ngram_operator(bench, ids, order=2, heads=heads)
    with pytest.raises(EngineError) as raised:
        bench.run(Major.DMA, Dma.NGRAM_HASH, operator)
    assert "compressed vocabulary" in str(raised.value)
    assert raised.value.trap_class == 3


def test_ngram_hash_refuses_a_column_table_that_does_not_span_the_orders(
    bench: Bench,
) -> None:
    """Three multipliers from order two are two orders, not one."""
    ids = np.array([1, 2, 3], dtype=np.uint32)
    operator, _ = _ngram_operator(
        bench, ids, order=2, heads=3, primes=(NGRAM_PRIMES[0],)
    )
    with pytest.raises(EngineError) as raised:
        bench.run(Major.DMA, Dma.NGRAM_HASH, operator)
    assert "does not span the declared orders" in str(raised.value)


def test_ngram_hash_requires_the_compressed_vocabulary_size(bench: Bench) -> None:
    ids = np.array([1, 2, 3], dtype=np.uint32)
    inputs = [
        bench.input_view(ids, DType.U32),
        bench.input_view(np.asarray(NGRAM_MULTIPLIERS, dtype=np.uint32), DType.U32),
        bench.input_view(ngram_column_table(NGRAM_PRIMES), DType.U32),
    ]
    out = bench.output_view((3, 3), DType.U32)
    operator = bench.operator(
        Major.DMA, Dma.NGRAM_HASH, inputs, [out], aux=[2, NGRAM_PAD_ID]
    )
    with pytest.raises(EngineError) as raised:
        bench.run(Major.DMA, Dma.NGRAM_HASH, operator)
    assert "aux_id_2" in str(raised.value)


# ---------------------------------------------------------------------------
# VECTOR.ENGRAM_GATE
# ---------------------------------------------------------------------------
#: The clamp floor the reference pins, passed through the numeric profile so
#: that the engine reads it from a descriptor rather than holding it.
EPSILON_BITS = ENGRAM_GATE_EPSILON_BINARY32


def engram_profile(bench: Bench) -> int:
    return bench.numeric(
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
        second_input_dtype=DType.FP32,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        epsilon_bits=EPSILON_BITS,
    )


def _engram_gate_operator(
    bench: Bench,
    state: np.ndarray,
    pair: np.ndarray,
    query: np.ndarray,
    gate_key: np.ndarray,
    *,
    profile: int | None = None,
) -> tuple[int, int]:
    inputs = [
        bench.input_view(state, DType.FP32),
        bench.input_view(pair, DType.FP32),
        bench.input_view(query, DType.FP32),
        bench.input_view(gate_key, DType.FP32),
    ]
    out = bench.output_view(state.shape, DType.FP32)
    operator = bench.operator(
        Major.VECTOR,
        Vector.ENGRAM_GATE,
        inputs,
        [out],
        numeric_profile_id=engram_profile(bench) if profile is None else profile,
    )
    return operator, out


def reference_gate_rows(
    state: np.ndarray,
    pair: np.ndarray,
    query: np.ndarray,
    gate_key: np.ndarray,
) -> np.ndarray:
    """The reference contract, row by row, on the same codes."""
    rows, width = state.shape
    codes = np.empty((rows, width), dtype=np.uint32)
    for row in range(rows):
        pair_row = pair[0] if pair.shape[0] == 1 else pair[row]
        outcome = reference_engram_gate(
            [int(code) for code in state[row].view(np.uint32)],
            [int(code) for code in pair_row[0].view(np.uint32)],
            [int(code) for code in pair_row[1].view(np.uint32)],
            [int(code) for code in query[row].view(np.uint32)],
            [int(code) for code in gate_key[row].view(np.uint32)],
            epsilon_code=EPSILON_BITS,
            max_width=width,
        )
        assert outcome.refusal_stage == 0, outcome.refusal_stage
        codes[row] = np.asarray(outcome.output_codes, dtype=np.uint32)
    return codes.view(np.float32)


def test_engram_gate_matches_the_reference_contract(bench: Bench) -> None:
    rows, width = 3, 16
    rng = np.random.default_rng(7)
    state = rng.standard_normal((rows, width)).astype(np.float32)
    pair = rng.standard_normal((1, 2, width)).astype(np.float32)
    query = rng.standard_normal((rows, width)).astype(np.float32)
    gate_key = rng.standard_normal((rows, width)).astype(np.float32)

    operator, out = _engram_gate_operator(bench, state, pair, query, gate_key)
    bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    expected = reference_gate_rows(state, pair, query, gate_key)
    assert np.array_equal(bench.result(out).view(np.uint32), expected.view(np.uint32))
    assert bench.counters["vector.norm_rows"] == 2 * rows
    assert bench.counters["vector.activation_elements"] == rows


def test_engram_gate_takes_a_pair_per_row_when_it_is_given_one(bench: Bench) -> None:
    rows, width = 2, 8
    rng = np.random.default_rng(19)
    state = rng.standard_normal((rows, width)).astype(np.float32)
    pair = rng.standard_normal((rows, 2, width)).astype(np.float32)
    query = rng.standard_normal((rows, width)).astype(np.float32)
    gate_key = rng.standard_normal((rows, width)).astype(np.float32)
    operator, out = _engram_gate_operator(bench, state, pair, query, gate_key)
    bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    assert np.array_equal(
        bench.result(out).view(np.uint32),
        reference_gate_rows(state, pair, query, gate_key).view(np.uint32),
    )


def test_engram_gate_with_a_zero_value_is_the_identity(bench: Bench) -> None:
    """The residual add is an add: nothing retrieved changes nothing."""
    rows, width = 2, 8
    rng = np.random.default_rng(11)
    state = rng.standard_normal((rows, width)).astype(np.float32)
    pair = np.zeros((1, 2, width), dtype=np.float32)
    pair[0, 0] = rng.standard_normal(width).astype(np.float32)  # key, value stays zero
    query = rng.standard_normal((rows, width)).astype(np.float32)
    gate_key = rng.standard_normal((rows, width)).astype(np.float32)
    operator, out = _engram_gate_operator(bench, state, pair, query, gate_key)
    bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    assert np.array_equal(bench.result(out), state)


def test_engram_gate_opens_halfway_on_an_orthogonal_pair(bench: Bench) -> None:
    """A zero dot is an exactly one-half gate, bit for bit.

    ``sigmoid(signed_sqrt(0)) == 0.5`` exactly, so an orthogonal ``q`` and ``k``
    pin the whole chain -- dot, clamp, division, signed square root, sigmoid,
    add -- at one point with no tolerance.
    """
    width = 4
    state = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    key = np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
    value = np.array([0.5, 0.25, 0.125, 2.0], dtype=np.float32)
    pair = np.stack((key, value))[None, ...]
    query = np.array([[1.0, 1.0, 0.0, 0.0]], dtype=np.float32)
    gate_key = np.array([[1.0, -1.0, 0.0, 0.0]], dtype=np.float32)
    operator, out = _engram_gate_operator(bench, state, pair, query, gate_key)
    bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    expected = np.add(
        state,
        np.multiply(
            np.float32(0.5), np.multiply(key, value, dtype=np.float32), dtype=np.float32
        ),
        dtype=np.float32,
    )
    assert np.array_equal(bench.result(out), expected)


def test_engram_gate_clamps_a_vanishing_denominator(bench: Bench) -> None:
    """A zero ``q`` takes the ``1e-6`` floor instead of dividing by zero."""
    width = 4
    state = np.ones((1, width), dtype=np.float32)
    pair = np.ones((1, 2, width), dtype=np.float32)
    query = np.zeros((1, width), dtype=np.float32)
    gate_key = np.ones((1, width), dtype=np.float32)
    operator, out = _engram_gate_operator(bench, state, pair, query, gate_key)
    bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    expected = reference_gate_rows(state, pair, query, gate_key)
    assert np.array_equal(bench.result(out).view(np.uint32), expected.view(np.uint32))
    # 0 / 1e-6 is +0, whose gate is exactly one half.
    assert np.array_equal(
        bench.result(out), np.add(state, np.float32(0.5), dtype=np.float32)
    )


def test_engram_gate_refuses_a_nonfinite_operand(bench: Bench) -> None:
    """The refusal names the contract site, not just the transaction."""
    width = 4
    state = np.ones((1, width), dtype=np.float32)
    pair = np.ones((1, 2, width), dtype=np.float32)
    query = np.ones((1, width), dtype=np.float32)
    gate_key = np.array([[np.inf, 1.0, 1.0, 1.0]], dtype=np.float32)
    operator, _ = _engram_gate_operator(bench, state, pair, query, gate_key)
    with pytest.raises(EngineError) as raised:
        bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    assert "site 2" in str(raised.value)
    assert raised.value.trap_class == 6


def test_engram_gate_requires_an_epsilon(bench: Bench) -> None:
    """The clamp floor is the profile's, not one the engine supplies."""
    width = 8
    state = np.ones((1, width), dtype=np.float32)
    pair = np.ones((1, 2, width), dtype=np.float32)
    bare = bench.numeric(
        input_dtype=DType.FP32,
        output_dtype=DType.FP32,
        second_input_dtype=DType.FP32,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
    )
    operator, _ = _engram_gate_operator(
        bench, state, pair, state, state, profile=bare
    )
    with pytest.raises(EngineError) as raised:
        bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    assert "epsilon" in str(raised.value)


def test_engram_gate_refuses_a_key_value_view_that_is_not_a_pair(bench: Bench) -> None:
    width = 8
    state = np.ones((2, width), dtype=np.float32)
    pair = np.ones((1, 3, width), dtype=np.float32)
    operator, _ = _engram_gate_operator(bench, state, pair, state, state)
    with pytest.raises(EngineError) as raised:
        bench.run(Major.VECTOR, Vector.ENGRAM_GATE, operator)
    assert "two planes" in str(raised.value) or "[2," in str(raised.value)


# ---------------------------------------------------------------------------
# ROUTE.INDEX_TOPK: present and absent must both be legal
# ---------------------------------------------------------------------------
SPAN, WIDTH, TOPK = 4, 8, 3


def independent_index_topk(
    scores: np.ndarray, topk: int, admission: np.ndarray | None
) -> np.ndarray:
    """The selection this operator owes, computed here.

    Causal prefill, no window join, no compression: the query at row ``r`` sits
    at absolute position ``base + r`` with ``base = candidates - span``, sees
    ``position + 1`` candidates, ranks the admitted ones by descending score
    with ties to the lower column, and emits them sorted ascending, tail-padded.
    """
    span, width = scores.shape
    base = width - span
    out = np.full((span, topk), np.uint32(PAD_INDEX), dtype=np.uint32)
    for row in range(span):
        limit = min(base + row + 1, width)
        columns = list(range(limit))
        if admission is not None:
            columns = [column for column in columns if admission[row, column]]
        ranked = sorted(columns, key=lambda column: (-float(scores[row, column]), column))
        chosen = sorted(ranked[: min(topk, len(columns))])
        out[row, : len(chosen)] = np.asarray(chosen, dtype=np.uint32)
    return out


def _index_topk_case(
    bench: Bench, scores: np.ndarray, admission: np.ndarray | None
) -> tuple[int, int]:
    inputs: list[int] = [bench.input_view(scores, DType.FP32)]
    if admission is not None:
        inputs += [NO_ID, NO_ID, bench.input_view(admission, DType.U8)]
    out = bench.output_view((SPAN, TOPK), DType.U32)
    operator = bench.operator(
        Major.ROUTE, Route.INDEX_TOPK, inputs, [out], aux=[TOPK]
    )
    return operator, out


def test_index_topk_without_a_mask_selects_what_it_always_did(bench: Bench) -> None:
    rng = np.random.default_rng(5)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    operator, out = _index_topk_case(bench, scores, None)
    bench.run(
        Major.ROUTE,
        Route.INDEX_TOPK,
        operator,
        symbols={int(Symbol.PHASE): int(Phase.PREFILL)},
    )
    assert np.array_equal(
        bench.result(out), independent_index_topk(scores, TOPK, None)
    )


def test_an_all_admitting_mask_changes_neither_result_nor_count(
    tmp_path: Path,
) -> None:
    """Present and absent are both legal, and here they must agree exactly."""
    rng = np.random.default_rng(17)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    symbols = {int(Symbol.PHASE): int(Phase.PREFILL)}

    without = Bench(tmp_path / "without")
    (tmp_path / "without").mkdir()
    operator, out = _index_topk_case(without, scores, None)
    without.run(Major.ROUTE, Route.INDEX_TOPK, operator, symbols=symbols)
    bare = without.result(out)
    bare_candidates = without.counters["route.topk_candidates"]

    with_mask = Bench(tmp_path / "with")
    (tmp_path / "with").mkdir()
    admission = np.ones((SPAN, WIDTH), dtype=np.uint8)
    operator, out = _index_topk_case(with_mask, scores, admission)
    with_mask.run(Major.ROUTE, Route.INDEX_TOPK, operator, symbols=symbols)

    assert np.array_equal(with_mask.result(out), bare)
    assert with_mask.counters["route.topk_candidates"] == bare_candidates
    assert np.array_equal(bare, independent_index_topk(scores, TOPK, None))


def test_the_mask_removes_exactly_the_excluded_candidates(bench: Bench) -> None:
    rng = np.random.default_rng(23)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    # Two candidate blocks of four, the second admitted for every query.
    admission = np.zeros((SPAN, WIDTH), dtype=np.uint8)
    admission[:, 4:] = 1
    operator, out = _index_topk_case(bench, scores, admission)
    bench.run(
        Major.ROUTE,
        Route.INDEX_TOPK,
        operator,
        symbols={int(Symbol.PHASE): int(Phase.PREFILL)},
    )
    result = bench.result(out)
    assert np.array_equal(
        result, independent_index_topk(scores, TOPK, admission)
    )
    # No excluded column reaches the output, whatever its score was.
    selected = result[result != np.uint32(PAD_INDEX)]
    assert selected.size and bool(np.all(selected >= 4))


def test_a_mask_that_admits_fewer_than_k_pads_rather_than_inventing_a_row(
    bench: Bench,
) -> None:
    """Exclusion, not a minus-infinity score: an inadmissible row is not emitted."""
    rng = np.random.default_rng(29)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    admission = np.zeros((SPAN, WIDTH), dtype=np.uint8)
    admission[:, 4] = 1  # exactly one admitted candidate per query
    operator, out = _index_topk_case(bench, scores, admission)
    bench.run(
        Major.ROUTE,
        Route.INDEX_TOPK,
        operator,
        symbols={int(Symbol.PHASE): int(Phase.PREFILL)},
    )
    result = bench.result(out)
    assert np.array_equal(result[:, 0], np.full(SPAN, 4, dtype=np.uint32))
    assert np.all(result[:, 1:] == np.uint32(PAD_INDEX))


def test_the_mask_must_cover_the_candidate_axis(bench: Bench) -> None:
    rng = np.random.default_rng(31)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    admission = np.ones((SPAN, WIDTH - 1), dtype=np.uint8)
    operator, out = _index_topk_case(bench, scores, admission)
    with pytest.raises(EngineError) as raised:
        bench.run(
            Major.ROUTE,
            Route.INDEX_TOPK,
            operator,
            symbols={int(Symbol.PHASE): int(Phase.PREFILL)},
        )
    assert "candidate mask" in str(raised.value)


def test_the_mask_admits_no_third_state(bench: Bench) -> None:
    rng = np.random.default_rng(37)
    scores = rng.standard_normal((SPAN, WIDTH)).astype(np.float32)
    admission = np.full((SPAN, WIDTH), 2, dtype=np.uint8)
    operator, out = _index_topk_case(bench, scores, admission)
    with pytest.raises(EngineError) as raised:
        bench.run(
            Major.ROUTE,
            Route.INDEX_TOPK,
            operator,
            symbols={int(Symbol.PHASE): int(Phase.PREFILL)},
        )
    assert "third" in str(raised.value)


# ---------------------------------------------------------------------------
# The whole candidate pool against the released ``select_candidate_blocks``
# ---------------------------------------------------------------------------
def released_candidate_blocks(
    logits: np.ndarray, compress_len: int, topk_blocks: int, block: int
) -> np.ndarray:
    """``inference/model.py::select_candidate_blocks`` for one query, in NumPy.

    ``logits`` is the query's score row over the positions it was scored
    against, with the unreachable ones (``>= compress_len``) already at -inf,
    as ``Indexer.forward`` leaves them.  The block holding the newest reachable
    position is pinned at +inf, the top ``topk_blocks`` blocks are kept unless
    their score is -inf, and the keep flags are expanded back to positions.
    """
    width = logits.shape[-1]
    padded = np.concatenate(
        (logits, np.full(-width % block, -np.inf, dtype=np.float64))
    )
    scores = padded.reshape(-1, block).max(axis=-1)
    last = (compress_len - 1) // block
    scores[last] = np.inf
    order = sorted(range(scores.size), key=lambda b: (-scores[b], b))
    top = order[: min(topk_blocks, scores.size)]
    keep = np.zeros(scores.size, dtype=bool)
    for chosen in top:
        keep[chosen] = scores[chosen] > -np.inf
    return np.repeat(keep, block)[:width]


def _candidate_pool(
    bench: Bench,
    scores: np.ndarray,
    *,
    block: int,
    topk_blocks: int,
    symbols: dict[int, int],
    ranks_blocks: bool = True,
) -> np.ndarray:
    """BLOCK_MAX -> block-ranking INDEX_TOPK -> CANDIDATE_MASK, as V4.1 lowers it.

    The score plane is presented at its CAPACITY (``scores.shape[1]``), wider
    than the context, which is how both V4.1 lanes present it; the columns past
    the context hold whatever the plane last held.
    """
    span, capacity = scores.shape
    blocks = -(-capacity // block)
    score_view = bench.input_view(scores.astype(np.float32), DType.FP32)
    block_scores = bench.output_view((span, blocks), DType.FP32)
    ratio = bench.input_view(np.array([block], dtype=np.uint32), DType.U32)
    ids = bench.output_view((span, topk_blocks), DType.U32)
    admission = bench.output_view((span, capacity), DType.U8)
    maximum = bench.operator(
        Major.ROUTE, Route.BLOCK_MAX, [score_view], [block_scores], aux=[block]
    )
    select = bench.operator(
        Major.ROUTE,
        Route.INDEX_TOPK,
        [block_scores, NO_ID, ratio],
        [ids],
        aux=[
            topk_blocks,
            route_engine.RANKS_BLOCKS if ranks_blocks else 0,
            int(Symbol.CONTEXT_LENGTH),
            int(Symbol.POSITION_START),
        ],
    )
    mask = bench.operator(
        Major.ROUTE, Route.CANDIDATE_MASK, [ids], [admission], aux=[block]
    )
    bench.run(Major.ROUTE, Route.BLOCK_MAX, maximum, symbols=symbols)
    bench.run(Major.ROUTE, Route.INDEX_TOPK, select)
    bench.run(Major.ROUTE, Route.CANDIDATE_MASK, mask)
    return bench.result(admission)


@pytest.mark.parametrize("topk_blocks", [2, 8])
def test_prefill_pool_admits_what_the_release_admits(
    bench: Bench, topk_blocks: int
) -> None:
    """Every prefill row keeps the block holding its own newest position.

    Before the pin moved into the block ranking, a row counted only its
    COMPLETE blocks (the compression-group rule, ``(p + 1) // block``), so the
    partial block holding the query itself was admitted by nobody: the mask's
    own pin is the last block of the PLANE, which at capacity is past the
    context.  At the V4.1 geometry (block 8, P10) that left rows 0-6 with an
    empty pool and rows 8-9 without positions 8 and 9.
    """
    span, context, capacity, block = 10, 10, 16, 4
    rng = np.random.default_rng(41)
    scores = rng.standard_normal((span, capacity))
    result = _candidate_pool(
        bench,
        scores,
        block=block,
        topk_blocks=topk_blocks,
        symbols={
            int(Symbol.PHASE): int(Phase.PREFILL),
            int(Symbol.CONTEXT_LENGTH): context,
            int(Symbol.POSITION_START): 0,
        },
    )
    for row in range(span):
        position = row
        logits = scores[row, :context].copy()
        logits[position + 1 :] = -np.inf
        expected = released_candidate_blocks(logits, position + 1, topk_blocks, block)
        # Only what the query can reach is a selection; the final INDEX_TOPK's
        # causal horizon removes the rest whatever the plane says.
        assert result[row, : position + 1].tolist() == expected[
            : position + 1
        ].astype(np.uint8).tolist(), row


def test_decode_pool_admits_what_the_release_admits(bench: Bench) -> None:
    """One query at POSITION_START 13 of a 14-position context, plane at 16."""
    context, capacity, block, topk_blocks = 14, 16, 4, 2
    rng = np.random.default_rng(43)
    scores = rng.standard_normal((1, capacity))
    result = _candidate_pool(
        bench,
        scores,
        block=block,
        topk_blocks=topk_blocks,
        symbols={
            int(Symbol.PHASE): int(Phase.DECODE),
            int(Symbol.CONTEXT_LENGTH): context,
            int(Symbol.POSITION_START): context - 1,
        },
    )
    expected = released_candidate_blocks(
        scores[0, :context].copy(), context, topk_blocks, block
    )
    assert result[0, :context].tolist() == expected.astype(np.uint8).tolist()


def test_an_unrebased_block_ranking_is_what_the_pool_needs(bench: Bench) -> None:
    """Without RANKS_BLOCKS the block IDs are rebased by the context.

    That is the HBM lane's pool before it set the bit: block 0 at a 10-position
    prefill came back as block 10, so the plane admitted positions 40-43 of a
    16-wide axis here (80-87 of 512 in the shipped cell) and nothing the query
    could reach.  This pins the failure mode the lowering tests guard.
    """
    span, context, capacity, block = 10, 10, 64, 4
    scores = np.random.default_rng(47).standard_normal((span, capacity))
    result = _candidate_pool(
        bench,
        scores,
        block=block,
        topk_blocks=16,
        ranks_blocks=False,
        symbols={
            int(Symbol.PHASE): int(Phase.PREFILL),
            int(Symbol.CONTEXT_LENGTH): context,
            int(Symbol.POSITION_START): 0,
        },
    )
    assert not result[:, :context].any()
