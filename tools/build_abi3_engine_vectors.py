#!/usr/bin/env python3
"""Build ABI 3.0 *engine datapath* correlation vectors from real deployments.

W8.6 correlated the control plane.  It did so with every engine bound to a
recording no-op, on purpose: the microsequencer's job is the issue order, and a
data-dependent engine fault would have trapped the reference on a program the
control-plane RTL can only run to completion.  The consequence, stated in that
campaign's own limitations, is that *no engine arithmetic was modelled on
either side*.  This generator is the other half.

Every vector here is a real ABI 3.0 program: built with
``runtime.abi3.builder.DeploymentBuilder``, admitted by
``runtime.abi3.verifier``, and executed by ``runtime.sim.device.Device`` with
its **real** engine implementations -- ``runtime.sim.engines.tensor``,
``.dma``, ``.vector`` and ``.selection``.  Nothing is stubbed.  What the
generator emits is therefore not a description of what an engine should do; it
is the bytes the functional simulator's engine actually left in device memory,
read back out of it after the transaction:

* the operand elements each resolved operand view held at the issue, in the
  view's own logical order, one element per 32-bit word whatever the storage
  format is;
* the elements the engine wrote into the output view;
* the counters the engine published, and for a refusal the trap class and the
  message the ``EngineError`` carried.

Four families are covered, chosen because each is a place where being wrong
changes a published result rather than a cycle count:

``TENSOR.MATMUL``
    Every contraction in both models.  Covered on the frozen sequential
    contract ``bf16_bf16_fp32_sequential_rne_v1`` -- exact products, strictly
    ascending-K binary32 accumulation, one RNE output rounding -- for
    BF16 x BF16, for FP8 E4M3FN x FP8 E4M3FN, and for the block-scaled
    MXFP4 E2M1 x FP8 E4M3FN pair the DeepSeek MoE actually ships.  The
    *blocked* contract is deliberately absent: its association is the executing
    implementation's declared one, so "bit-exact against it" is not a
    well-posed claim about a different implementation.

``DMA.GATHER`` and ``DMA.SCATTER``
    Every weight and every KV byte that moves.  The properties correlated are
    the two that fail quietly: an index outside the extent it addresses is a
    fault rather than a clamp, and it is detected before anything moves; and
    scatter applies slots in ascending order so a repeated index resolves to
    the last write while unnamed rows keep their prior contents.

``VECTOR.ADD``
    The residual, at every layer boundary, under ``bf16_add_rne_v1``.

``SELECTION.ARGMAX``
    The token itself, under ``greedy_lowest_token_id_argmax``: the lowest token
    ID among the maxima, with the tie multiplicity published beside it.

Two probes sit beside the cases, because the operand distribution real programs
produce is the one under which a numeric defect is *least* likely to show.

* A storage-format decode probe, exhaustive over all 256 E4M3FN codes, all 16
  E2M1 nibbles and all 256 E8M0 codes, against ``runtime.sim.formats`` -- whose
  tables are enumerated from the exact ``fractions.Fraction`` decoders in
  ``runtime/reference/formats.py``.
* A binary32 arithmetic probe over a corner cross-product and a seeded spread,
  against ``runtime.reference.formats.binary32_add``, ``binary32_multiply`` and
  ``binary32_bits_to_bf16_rne``, which round once from exact rationals so no
  host floating-point mode participates on the reference side.

One property needs a case built for it rather than a probe: the *reduction
order*.  Reordering a binary32 reduction perturbs the accumulator by about one
part in 2**24 and the output rounds to BF16, which resolves one part in 2**8,
so on ordinary operands ascending-K and descending-K give the same BF16 code at
every output -- 147 of 585 accumulators in ``matmul_bf16_tile_edge`` differ in
binary32 and none of them differ after rounding.  A deliberately reversed lane
passed the whole set until ``matmul_bf16_reduction_order`` and
``matmul_fp8_reduction_order`` were added, one on each reference code path.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field as dc_field
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any, Sequence

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.builder import DeploymentBuilder  # noqa: E402
from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import (  # noqa: E402
    Control,
    CounterGroup,
    DType,
    Dma,
    Feature,
    Major,
    NO_ID,
    Permission,
    ReductionOrder,
    Selection,
    StorageClass,
    Tensor,
    TopologyClass,
    Vector,
    counter_id,
)
from runtime.abi3.deployment import Deployment, ObjectSource, Segment  # noqa: E402
from runtime.abi3.descriptors import LayoutClass, Phase  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.reference import formats as exact_formats  # noqa: E402
from runtime.sim import formats as sim_formats  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

OUTPUT_DIR = ROOT / "testdata/compiler/abi3_engine"

READ = int(Permission.READ)
IMMUTABLE = int(Permission.READ | Permission.IMMUTABLE)
READ_WRITE = int(Permission.READ | Permission.WRITE)

# ---------------------------------------------------------------------------
# RTL image geometry.  Images are padded to these sizes so both simulators read
# a fully initialised memory; the generator refuses to overflow one.
# ---------------------------------------------------------------------------
M0_WORDS = 40960
M1_WORDS = 40960
M2_WORDS = 4096
M3_WORDS = 4096
RESULT_WORDS = 40960
CASE_WORDS = 4096
DECODE_WORDS = 16384
ARITH_WORDS = 65536
ARITH_STRIDE = 8
META_WORDS = 8
CASE_STRIDE = 32

# Fault codes, transcribed from rtl/abi3/ot_a3_engine_pkg.sv.
ERR_NONE = 0
ERR_OPERAND_NONFINITE = 1
ERR_PRODUCT_RANGE = 2
ERR_ACCUMULATE_RANGE = 3
ERR_INDEX_RANGE = 4
ERR_SELECT_NONFINITE = 5
ERR_SCALE_RANGE = 6
ERR_SHAPE = 7

#: How a golden refusal is classified.  The key is a substring of the message
#: the functional engine's ``EngineError`` carried, so the RTL fault code is a
#: transcription of an observed failure rather than a guess about one.  Every
#: negative case publishes the message it matched, and a message that matches
#: none of these is a hard error here rather than a default.
FAULT_SIGNATURES: tuple[tuple[str, int], ...] = (
    ("names row", ERR_INDEX_RANGE),
    ("outside the", ERR_INDEX_RANGE),
    ("contains a NaN or", ERR_SELECT_NONFINITE),
    ("NaN or infinite", ERR_SELECT_NONFINITE),
    ("reserved or NaN", ERR_OPERAND_NONFINITE),
    ("BF16 NaN or infinity", ERR_OPERAND_NONFINITE),
    ("multiplication overflowed", ERR_PRODUCT_RANGE),
    ("accumulation overflowed", ERR_ACCUMULATE_RANGE),
    ("block scale application left", ERR_SCALE_RANGE),
    ("left the binary32 range", ERR_ACCUMULATE_RANGE),
)


def classify_fault(message: str) -> int:
    for needle, code in FAULT_SIGNATURES:
        if needle in message:
            return code
    raise SystemExit(
        "the golden model refused with a message this generator cannot "
        f"classify, so the RTL fault code would be a guess: {message!r}"
    )


# ---------------------------------------------------------------------------
# Capability
# ---------------------------------------------------------------------------
def engine_capability() -> Capability:
    capability = Capability(
        capability_id="",
        topology_class=int(TopologyClass.SINGLE_CHIP),
        features=(
            int(Feature.HOST_QUEUE_ABI),
            int(Feature.DEPLOYMENT_DESCRIPTOR_ABI),
            int(Feature.DETERMINISTIC_MICROSEQUENCER),
            int(Feature.BF16_TENSOR),
            int(Feature.TRANSACTIONAL_STATE),
            int(Feature.ON_DEVICE_SELECTION),
        ),
        limits={
            "max_instructions": 4096,
            "max_descriptors": 4096,
            "max_loop_depth": 4,
            "max_loop_trip": 1 << 20,
            "max_retired_work": 1 << 32,
            "max_events": 256,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 256,
            "max_expert_ids": 1024,
            "max_topk": 16,
            "max_vocabulary": 4096,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=(
            "bf16_bf16_fp32_sequential_rne_v1",
            "bf16_add_rne_v1",
            "exact_index_select_v1",
        ),
        engines={
            "tensor": {"lanes": 8, "queues": 1},
            "vector": {"lanes": 8, "queues": 1},
            "dma": {"queues": 1},
            "selection": {"queues": 1},
            "state": {"queues": 1},
        },
        memory={
            "sram": {"bytes": 1 << 20, "banks": 2},
            "hbm": {"bytes": 1 << 22},
            "rom": {"bytes": 1 << 22},
        },
        technology_view="rtl3-engine",
    )
    capability.validate()
    return capability


# ---------------------------------------------------------------------------
# One case
# ---------------------------------------------------------------------------
@dataclass
class Case:
    """One engine-datapath vector: a real program plus its golden result."""

    name: str
    note: str
    family: int
    sub: int
    deployment: Deployment
    root: Path
    # Views the RTL reads and the view it must reproduce.
    operand0_view: int
    operand1_view: int = NO_ID
    output_view: int = NO_ID
    prior_view: int = NO_ID
    scale0_object: int = NO_ID
    scale1_object: int = NO_ID
    scale0_count: int = 0
    scale1_count: int = 0
    rows: int = 0
    cols: int = 0
    depth: int = 0
    count: int = 0
    slots: int = 0
    trailing: int = 0
    extent: int = 0
    block_a: int = 0
    block_b: int = 0
    block_rows_a: int = 1
    block_rows_b: int = 1
    expect_admitted: bool = True
    expect_fault: bool = False
    #: Scatter only: what the destination held *before* the transaction.  The
    #: post-run contents are read back out of device memory, but the prior ones
    #: cannot be, so they are kept from construction.
    prior_payload: np.ndarray | None = None
    symbols: dict[int, int] = dc_field(default_factory=dict)
    counter_names: tuple[str, ...] = ()


class Workspace:
    """A deployment builder that carries real, file-backed operand data."""

    def __init__(self, name: str, capability: Capability, root: Path) -> None:
        self.name = name
        self.capability = capability
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.files = 0
        self.builder = DeploymentBuilder(
            target_id=name,
            model_id="abi3-rtl3-engine",
            backend="rtl3-engine",
            capability=capability,
        )
        self.builder.require(Feature.BF16_TENSOR)
        self.builder.topology(
            topology_class=TopologyClass.SINGLE_CHIP,
            node_count=1,
            hbm_bytes_per_node=capability.memory["hbm"]["bytes"],
            sram_bytes_per_node=capability.memory["sram"]["bytes"],
            key="topology",
        )
        self.schedules: dict[int, int] = {}

    # -- objects ---------------------------------------------------------
    def data_object(
        self,
        payload: bytes,
        *,
        storage_class: StorageClass = StorageClass.HBM,
        permissions: int = IMMUTABLE,
    ) -> int:
        self.files += 1
        name = f"{self.name}-object{self.files}.bin"
        (self.root / name).write_bytes(payload)
        return self.builder.memory_object(
            storage_class=storage_class,
            size_bytes=len(payload),
            source=ObjectSource(
                "segments", len(payload), (Segment(name, 0, len(payload)),)
            ),
            permissions=permissions,
            key=f"obj.data{self.files}",
        )

    def scratch(
        self,
        size_bytes: int,
        *,
        storage_class: StorageClass = StorageClass.SRAM,
    ) -> int:
        self.files += 1
        return self.builder.memory_object(
            storage_class=storage_class,
            size_bytes=size_bytes,
            source=ObjectSource.zeros(size_bytes),
            permissions=READ_WRITE,
            key=f"obj.scratch{self.files}",
        )

    # -- views -----------------------------------------------------------
    def const_view(
        self,
        payload: bytes,
        dtype: DType,
        dims: Sequence[int],
        *,
        storage_class: StorageClass = StorageClass.HBM,
        scale_object_id: int = NO_ID,
        scale_block_elements: int = 0,
        scale_block_rows: int = 0,
        key: str | None = None,
    ) -> int:
        object_id = self.data_object(payload, storage_class=storage_class)
        return self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            permissions=READ,
            layout_class=(
                LayoutClass.BLOCK_SCALED
                if scale_object_id != NO_ID
                else LayoutClass.DENSE
            ),
            scale_object_id=scale_object_id,
            scale_block_elements=scale_block_elements,
            scale_block_rows=scale_block_rows,
            key=key,
        )

    def scratch_view(
        self,
        dtype: DType,
        dims: Sequence[int],
        *,
        storage_class: StorageClass = StorageClass.SRAM,
        key: str | None = None,
    ) -> int:
        count = 1
        for dim in dims:
            count *= int(dim)
        if dtype == DType.MXFP4_E2M1:
            size = count // 2
        else:
            size = count * ELEMENT_BYTES[int(dtype)]
        object_id = self.scratch(size, storage_class=storage_class)
        return self.builder.tensor_view(
            object_id=object_id,
            dtype=dtype,
            dims=list(dims),
            permissions=READ_WRITE,
            key=key,
        )

    # -- descriptors -----------------------------------------------------
    def schedule_for(self, family: Major) -> int:
        existing = self.schedules.get(int(family))
        if existing is not None:
            return existing
        sid = self.builder.schedule(
            engine_family=family,
            tile_rows=1,
            tile_cols=1,
            tile_depth=1,
            bank_mask=0b1,
            max_outstanding=1,
            key=f"sched.{family.name.lower()}",
        )
        self.schedules[int(family)] = sid
        return sid

    def counters(self, group: CounterGroup, key: str) -> int:
        return self.builder.counter_class(
            int(group), [counter_id(group, 1)], key=key
        )

    def operator(self, **kwargs: Any) -> int:
        family = kwargs["engine_family"]
        kwargs.setdefault("schedule_id", self.schedule_for(family))
        return self.builder.operator(**kwargs)

    def finish(self, **kwargs: Any) -> Deployment:
        deployment = self.builder.finish(**kwargs)
        # Object sources name files relative to the deployment root, and this
        # workspace wrote them there.
        deployment.root = self.root
        return deployment


#: Storage bytes per element, for the formats a scratch view can hold.
ELEMENT_BYTES = {
    int(DType.BF16): 2,
    int(DType.FP32): 4,
    int(DType.U32): 4,
    int(DType.U8): 1,
    int(DType.FP8_E4M3FN): 1,
    int(DType.E8M0_SCALE): 1,
}


# ---------------------------------------------------------------------------
# Case-record flags (transcribed by both checkers)
# ---------------------------------------------------------------------------
FLAG_COMPARE_WORK = 0x1
FLAG_COMPARE_TOKEN = 0x2
FLAG_EXPECT_UNTOUCHED = 0x4
FLAG_COMPARE_SATURATION = 0x8

#: The value ot_a3_engine_top writes into every result word before a case runs.
#: A fault case asserts that its whole destination window still holds it, which
#: is how "no partial write" is checked rather than assumed.
UNWRITTEN = 0xDEADBEEF


# ---------------------------------------------------------------------------
# Deterministic operand data
# ---------------------------------------------------------------------------
def bf16_codes(values: np.ndarray) -> np.ndarray:
    codes, _ = sim_formats.narrow_bf16_rne(
        np.ascontiguousarray(values, dtype=np.float32)
    )
    return np.ascontiguousarray(codes, dtype=np.uint16)


def random_bf16(rng: np.random.Generator, shape: Sequence[int], scale: float = 1.0):
    return bf16_codes(
        rng.standard_normal(tuple(shape)).astype(np.float32) * np.float32(scale)
    )


def pack_nibbles(nibbles: np.ndarray) -> bytes:
    """Pack MXFP4 nibbles low-nibble-first, the order the resolver reads."""
    flat = np.ascontiguousarray(nibbles, dtype=np.uint8).reshape(-1)
    if flat.size % 2:
        raise SystemExit("an MXFP4 view must hold an even number of elements")
    return bytes((flat[0::2] & 0x0F) | (flat[1::2] << 4))


# ---------------------------------------------------------------------------
# Programs
# ---------------------------------------------------------------------------
def build_program(
    workspace: Workspace,
    family: Major,
    sub: int,
    operator_id: int,
    *,
    prologue: Sequence[tuple[Major, int, int]] = (),
) -> Deployment:
    b = workspace.builder
    for index, (pre_family, pre_sub, pre_operator) in enumerate(prologue):
        b.emit(
            pre_family, pre_sub, descriptor_id=pre_operator,
            source_operation_id=index,
        )
    b.emit(family, sub, descriptor_id=operator_id, source_operation_id=len(prologue))
    b.emit(Major.CONTROL, Control.COMPLETE)
    b.entrypoint(entrypoint_id=0, first_instruction=0, phase=Phase.PREFILL)
    return workspace.finish()


def matmul_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    activation_codes: np.ndarray,
    weight_codes: np.ndarray,
    activation_dtype: DType,
    weight_dtype: DType,
    activation_scales: np.ndarray | None = None,
    weight_scales: np.ndarray | None = None,
    block_a: int = 0,
    block_b: int = 0,
    block_rows_a: int = 0,
    block_rows_b: int = 0,
    expect_fault: bool = False,
) -> Case:
    """One TENSOR.MATMUL over real operand bytes under the sequential contract."""
    w = Workspace(name, capability, root)
    rows, depth = activation_codes.shape
    cols = weight_codes.shape[0]

    def payload(codes: np.ndarray, dtype: DType) -> bytes:
        if dtype == DType.MXFP4_E2M1:
            return pack_nibbles(codes)
        if dtype == DType.BF16:
            return np.ascontiguousarray(codes, dtype=np.uint16).tobytes()
        return np.ascontiguousarray(codes, dtype=np.uint8).tobytes()

    scale_a_object = NO_ID
    scale_b_object = NO_ID
    if activation_scales is not None:
        scale_a_object = w.data_object(
            np.ascontiguousarray(activation_scales, dtype=np.uint8).tobytes()
        )
    if weight_scales is not None:
        scale_b_object = w.data_object(
            np.ascontiguousarray(weight_scales, dtype=np.uint8).tobytes()
        )

    view_a = w.const_view(
        payload(activation_codes, activation_dtype),
        activation_dtype,
        [rows, depth],
        scale_object_id=scale_a_object,
        scale_block_elements=block_a,
        scale_block_rows=block_rows_a,
        key="view.activation",
    )
    view_b = w.const_view(
        payload(weight_codes, weight_dtype),
        weight_dtype,
        [cols, depth],
        scale_object_id=scale_b_object,
        scale_block_elements=block_b,
        scale_block_rows=block_rows_b,
        key="view.weight",
    )
    view_out = w.scratch_view(DType.BF16, [rows, cols], key="view.out")
    numeric = w.builder.numeric(
        contract="bf16_bf16_fp32_sequential_rne_v1",
        input_dtype=activation_dtype,
        second_input_dtype=weight_dtype,
        output_dtype=DType.BF16,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        key="num.matmul",
    )
    operator = w.operator(
        engine_family=Major.TENSOR,
        engine_sub=int(Tensor.MATMUL),
        inputs=[view_a, view_b],
        outputs=[view_out],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.TENSOR, "ctr.tensor"),
        source_kernel_id=0,
        key="op.matmul",
    )
    deployment = build_program(w, Major.TENSOR, int(Tensor.MATMUL), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.TENSOR),
        sub=int(Tensor.MATMUL),
        deployment=deployment,
        root=root,
        operand0_view=view_a,
        operand1_view=view_b,
        output_view=view_out,
        scale0_object=scale_a_object,
        scale1_object=scale_b_object,
        scale0_count=0 if activation_scales is None else int(activation_scales.size),
        scale1_count=0 if weight_scales is None else int(weight_scales.size),
        rows=rows,
        cols=cols,
        depth=depth,
        block_a=block_a,
        block_b=block_b,
        block_rows_a=max(int(block_rows_a), 1),
        block_rows_b=max(int(block_rows_b), 1),
        expect_fault=expect_fault,
        counter_names=("tensor.output_elements", "tensor.saturations"),
    )


def vector_add_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    left_codes: np.ndarray,
    right_codes: np.ndarray,
    expect_fault: bool = False,
) -> Case:
    w = Workspace(name, capability, root)
    dims = list(left_codes.shape)
    count = int(left_codes.size)
    view_l = w.const_view(
        np.ascontiguousarray(left_codes, dtype=np.uint16).tobytes(),
        DType.BF16, dims, key="view.left",
    )
    view_r = w.const_view(
        np.ascontiguousarray(right_codes, dtype=np.uint16).tobytes(),
        DType.BF16, dims, key="view.right",
    )
    view_out = w.scratch_view(DType.BF16, dims, key="view.out")
    numeric = w.builder.numeric(
        contract="bf16_add_rne_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        key="num.add",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.ADD),
        inputs=[view_l, view_r],
        outputs=[view_out],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.add",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.ADD), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.ADD),
        deployment=deployment,
        root=root,
        operand0_view=view_l,
        operand1_view=view_r,
        output_view=view_out,
        count=count,
        expect_fault=expect_fault,
        counter_names=("vector.elements", "vector.saturations"),
    )


def selection_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    logit_payload: bytes,
    logit_dtype: DType,
    count: int,
    expect_fault: bool = False,
) -> Case:
    w = Workspace(name, capability, root)
    view_logits = w.const_view(
        logit_payload, logit_dtype, [count], key="view.logits"
    )
    view_token = w.scratch_view(DType.U32, [1], key="view.token")
    numeric = w.builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=logit_dtype,
        output_dtype=DType.U32,
        key="num.select",
    )
    operator = w.operator(
        engine_family=Major.SELECTION,
        engine_sub=int(Selection.ARGMAX),
        inputs=[view_logits],
        outputs=[view_token],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.SELECTION_EOS, "ctr.selection"),
        source_kernel_id=0,
        key="op.argmax",
    )
    deployment = build_program(w, Major.SELECTION, int(Selection.ARGMAX), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.SELECTION),
        sub=int(Selection.ARGMAX),
        deployment=deployment,
        root=root,
        operand0_view=view_logits,
        output_view=view_token,
        count=count,
        expect_fault=expect_fault,
        counter_names=("selection.vocabulary_elements", "selection.tie_multiplicity"),
    )


def dma_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    scatter: bool,
    indices: np.ndarray,
    rows: int,
    trailing: int,
    payload_codes: np.ndarray,
    prior_codes: np.ndarray | None = None,
    expect_fault: bool = False,
) -> Case:
    """One DMA.GATHER or DMA.SCATTER over real index and payload bytes."""
    w = Workspace(name, capability, root)
    slots = int(indices.size)
    view_index = w.const_view(
        np.ascontiguousarray(indices, dtype=np.uint32).tobytes(),
        DType.U32, [slots], key="view.index",
    )
    prologue: list[tuple[Major, int, int]] = []
    if scatter:
        if prior_codes is None:
            raise SystemExit("a scatter case must declare the destination's prior rows")
        view_values = w.const_view(
            np.ascontiguousarray(payload_codes, dtype=np.uint16).tobytes(),
            DType.BF16, [slots, trailing], key="view.values",
        )
        view_dest = w.scratch_view(DType.BF16, [rows, trailing], key="view.dest")
        # A file-backed object is mapped read-only, so the destination cannot
        # start from real bytes by being one.  It is filled instead by a
        # DMA.TRANSFER that this same program issues from an immutable
        # constant, which is both what a real lane does and what makes the
        # prior contents a known quantity: they are the constant's bytes.  A
        # zero-filled destination would let a scatter that never read the
        # destination back pass anyway.
        view_prior = w.const_view(
            np.ascontiguousarray(prior_codes, dtype=np.uint16).tobytes(),
            DType.BF16, [rows, trailing], key="view.prior",
        )
        move_numeric = w.builder.numeric(
            contract="exact_index_select_v1",
            input_dtype=DType.BF16,
            output_dtype=DType.BF16,
            key="num.prologue",
        )
        seed = w.operator(
            engine_family=Major.DMA,
            engine_sub=int(Dma.TRANSFER),
            inputs=[view_prior],
            outputs=[view_dest],
            numeric_profile_id=move_numeric,
            counter_class_id=w.counters(CounterGroup.MEMORY, "ctr.dma"),
            source_kernel_id=0,
            key="op.seed",
        )
        prologue.append((Major.DMA, int(Dma.TRANSFER), seed))
        inputs = [view_index, view_values]
        outputs = [view_dest]
        operand1 = view_values
        prior_view = view_prior
        output_view = view_dest
    else:
        view_source = w.const_view(
            np.ascontiguousarray(payload_codes, dtype=np.uint16).tobytes(),
            DType.BF16, [rows, trailing], key="view.source",
        )
        view_out = w.scratch_view(DType.BF16, [slots, trailing], key="view.out")
        inputs = [view_index, view_source]
        outputs = [view_out]
        operand1 = view_source
        prior_view = NO_ID
        output_view = view_out
    numeric = w.builder.numeric(
        contract="exact_index_select_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        key="num.move",
    )
    sub = int(Dma.SCATTER) if scatter else int(Dma.GATHER)
    operator = w.operator(
        engine_family=Major.DMA,
        engine_sub=sub,
        inputs=inputs,
        outputs=outputs,
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.MEMORY, "ctr.dma"),
        source_kernel_id=0,
        key="op.move",
    )
    deployment = build_program(w, Major.DMA, sub, operator, prologue=prologue)
    return Case(
        name=name,
        note=note,
        family=int(Major.DMA),
        sub=sub,
        deployment=deployment,
        root=root,
        operand0_view=view_index,
        operand1_view=operand1,
        output_view=output_view,
        prior_view=prior_view,
        prior_payload=(
            None if prior_codes is None
            else np.ascontiguousarray(prior_codes, dtype=np.uint16)
        ),
        slots=slots,
        trailing=trailing,
        extent=rows,
        expect_fault=expect_fault,
        counter_names=(
            "dma.scatter_elements" if scatter else "dma.gather_elements",
            "dma.transfers",
        ),
    )


# ---------------------------------------------------------------------------
# The case set
# ---------------------------------------------------------------------------
def build_cases(capability: Capability, root: Path) -> list[Case]:
    rng = np.random.default_rng(20260831)
    cases: list[Case] = []

    # -- TENSOR.MATMUL, BF16 x BF16 -> BF16 ------------------------------
    cases.append(matmul_case(
        "matmul_bf16_small",
        "4 x 16 activations against 8 x 16 weights: the ordinary contraction",
        capability, root,
        activation_codes=random_bf16(rng, (4, 16)),
        weight_codes=random_bf16(rng, (8, 16)),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))
    cases.append(matmul_case(
        "matmul_bf16_tile_edge",
        "9 x 33 against 65 x 33: crosses the frozen kernel's 8-row and "
        "64-column work tile in both directions, so a tiling that leaked into "
        "the arithmetic would show here",
        capability, root,
        activation_codes=random_bf16(rng, (9, 33)),
        weight_codes=random_bf16(rng, (65, 33)),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))
    # 0x5f7f is 1.9921875 x 2**63 and 0x5d80 is 2**60; the first product is
    # 1.984436 x 2**127 and the second, against 0x5dcc = 1.59375 x 2**60, is
    # 0.012451 x 2**127.  Their ascending-K sum is 1.996887 x 2**127: inside
    # binary32, past the midpoint above the largest finite BF16, so the
    # accumulation succeeds and the single output rounding saturates.  The
    # other two weight columns are ordinary, so the saturation count is six of
    # twelve rather than all or none.
    saturating_activations = np.tile(
        np.array([0x5F7F, 0x5D80], dtype=np.uint16), (3, 1)
    )
    saturating_weights = np.array(
        [[0x5F7F, 0x5DCC],
         [0x5F7F, 0x5DCC],
         [0x3F80, 0x4000],
         [0xBF80, 0x4040]],
        dtype=np.uint16,
    )
    cases.append(matmul_case(
        "matmul_bf16_saturating",
        "an accumulator that stays inside binary32 and leaves the BF16 range: "
        "six of twelve outputs saturate to the largest finite code, and the "
        "saturation is counted rather than raised",
        capability, root,
        activation_codes=saturating_activations,
        weight_codes=saturating_weights,
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))
    zero_activations = np.zeros((4, 8), dtype=np.uint16)
    zero_activations[:, ::2] = 0x8000          # BF16 negative zero
    zero_weights = random_bf16(rng, (6, 8))
    zero_weights[:, 1::2] = 0x8000
    cases.append(matmul_case(
        "matmul_bf16_signed_zero",
        "every product is an exact zero of one sign or the other: the "
        "contract canonicalises them positive before accumulation, so the "
        "result must be +0 and not -0",
        capability, root,
        activation_codes=zero_activations,
        weight_codes=zero_weights,
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))
    # A contraction whose BF16 output *can* see its own reduction order.
    #
    # This case exists because a mutation test found that the others cannot.
    # Reordering a binary32 reduction perturbs the accumulator by about one
    # part in 2**24, and the output rounds to BF16, which resolves one part in
    # 2**8 -- so on ordinary operands ascending-K and descending-K produce the
    # same BF16 code at every output.  Running the whole positive set against a
    # deliberately reversed lane confirmed it: 147 of 585 accumulators in
    # `matmul_bf16_tile_edge` differ in binary32 and none of them differ after
    # the output rounding.  Without this case the campaign would check the
    # products, the accumulation width and the output rounding of
    # bf16_bf16_fp32_sequential_rne_v1, and *not* the ordering the contract is
    # named for.
    #
    # The construction is catastrophic cancellation with a small leading term:
    # products (2**j, 2**30, -2**30).  Ascending, 2**j is absorbed into 2**30
    # -- one part in 2**30, far below binary32's 2**-24 -- and the cancellation
    # then leaves exactly zero.  Descending, the cancellation happens first and
    # 2**j survives whole.  0x4700 is 2**15 and 0xc700 is -2**15.
    order_activations = np.array(
        [[0x3F80, 0x4700, 0x4700],   # 1
         [0x4000, 0x4700, 0x4700],   # 2
         [0x4080, 0x4700, 0x4700],   # 4
         [0x4100, 0x4700, 0x4700]],  # 8
        dtype=np.uint16,
    )
    order_weights = np.array(
        [[0x3F80, 0x4700, 0xC700],   # cancels: order-sensitive
         [0x3F80, 0x3F80, 0x3F80],   # ordinary: order-insensitive
         [0x4000, 0x4700, 0xC700],   # cancels, at twice the leading term
         [0xBF80, 0x4700, 0xC700]],  # cancels, negative leading term
        dtype=np.uint16,
    )
    cases.append(matmul_case(
        "matmul_bf16_reduction_order",
        "a contraction whose BF16 output distinguishes ascending-K from any "
        "other association: a small leading product, then an exact "
        "cancellation of two large ones.  Ascending absorbs the small term and "
        "returns zero; any order that cancels first returns it whole",
        capability, root,
        activation_codes=order_activations,
        weight_codes=order_weights,
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))
    # The same property on the other reference code path.  BF16 x BF16 runs
    # through the frozen kernel in runtime.tensor_accelerator.bf16; every other
    # operand pair runs through runtime.sim.backend.sequential_matmul_binary32,
    # and the two are separate implementations of one contract.
    # 0x01 is the smallest positive E4M3FN (2**-9) and 0x7e is the largest
    # finite (448); 448**2 is 2**17.6, so the leading product is 2**-30 of it.
    fp8_order_activations = np.array(
        [[0x01, 0x7E, 0x7E],
         [0x02, 0x7E, 0x7E],
         [0x04, 0x7E, 0x7E]],
        dtype=np.uint8,
    )
    fp8_order_weights = np.array(
        [[0x38, 0x7E, 0xFE],         # 1.0, 448, -448
         [0x38, 0x38, 0x38],         # ordinary
         [0x40, 0x7E, 0xFE]],        # 2.0 leading term
        dtype=np.uint8,
    )
    cases.append(matmul_case(
        "matmul_fp8_reduction_order",
        "the same order-sensitive construction on the FP8 path, which reaches "
        "runtime.sim.backend.sequential_matmul_binary32 rather than the frozen "
        "BF16 kernel -- two separate implementations of one contract, so both "
        "need an operand set that can see the order",
        capability, root,
        activation_codes=fp8_order_activations,
        weight_codes=fp8_order_weights,
        activation_dtype=DType.FP8_E4M3FN, weight_dtype=DType.FP8_E4M3FN,
    ))
    cases.append(matmul_case(
        "matmul_bf16_wide_reduction",
        "a 256-deep reduction, where an association error accumulates instead "
        "of cancelling",
        capability, root,
        activation_codes=random_bf16(rng, (2, 256)),
        weight_codes=random_bf16(rng, (4, 256)),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
    ))

    # -- TENSOR.MATMUL, FP8 E4M3FN x FP8 E4M3FN -> BF16 ------------------
    fp8_activations = rng.integers(0, 256, size=(4, 32), dtype=np.uint64).astype(np.uint8)
    fp8_activations[fp8_activations == 0x7F] = 0x30
    fp8_activations[fp8_activations == 0xFF] = 0xB0
    fp8_weights = rng.integers(0, 256, size=(8, 32), dtype=np.uint64).astype(np.uint8)
    fp8_weights[fp8_weights == 0x7F] = 0x38
    fp8_weights[fp8_weights == 0xFF] = 0xB8
    cases.append(matmul_case(
        "matmul_fp8_fp8",
        "FP8 E4M3FN on both sides: exact decode, exact products, the same "
        "ascending-K binary32 reduction",
        capability, root,
        activation_codes=fp8_activations, weight_codes=fp8_weights,
        activation_dtype=DType.FP8_E4M3FN, weight_dtype=DType.FP8_E4M3FN,
    ))
    big_a = rng.integers(0, 64, size=(64, 4), dtype=np.uint64).astype(np.uint8)
    big_b = rng.integers(0, 64, size=(128, 4), dtype=np.uint64).astype(np.uint8)
    cases.append(matmul_case(
        "matmul_fp8_k_major_schedule",
        "64 x 128 output over a 4-deep reduction: 8,192 output elements is "
        "exactly the tile at which runtime.sim.backend switches the sequential "
        "contraction from its K-last schedule to its K-major one.  The "
        "contract says the two agree bit for bit; this case is where the RTL "
        "checks that claim against the other schedule",
        capability, root,
        activation_codes=big_a, weight_codes=big_b,
        activation_dtype=DType.FP8_E4M3FN, weight_dtype=DType.FP8_E4M3FN,
    ))

    # -- TENSOR.MATMUL, block-scaled MXFP4 E2M1 x FP8 E4M3FN -> BF16 -----
    mx_rows, mx_cols, mx_depth, mx_block = 4, 8, 64, 32
    mx_activations = rng.integers(
        0, 16, size=(mx_rows, mx_depth), dtype=np.uint64
    ).astype(np.uint8)
    mx_weights = rng.integers(
        0, 256, size=(mx_cols, mx_depth), dtype=np.uint64
    ).astype(np.uint8)
    mx_weights[mx_weights == 0x7F] = 0x38
    mx_weights[mx_weights == 0xFF] = 0xB8
    mx_a_scales = rng.integers(
        120, 135, size=(mx_rows * (mx_depth // mx_block),), dtype=np.uint64
    ).astype(np.uint8)
    mx_b_scales = rng.integers(
        120, 135, size=(mx_cols * (mx_depth // mx_block),), dtype=np.uint64
    ).astype(np.uint8)
    cases.append(matmul_case(
        "matmul_mxfp4_fp8_block_scaled",
        "the pair the released DeepSeek MoE actually ships: MXFP4 E2M1 "
        "activations and FP8 E4M3FN weights, each with its own 32-element "
        "E8M0 block scale.  Amendment A8's one-dimensional block",
        capability, root,
        activation_codes=mx_activations, weight_codes=mx_weights,
        activation_dtype=DType.MXFP4_E2M1, weight_dtype=DType.FP8_E4M3FN,
        activation_scales=mx_a_scales, weight_scales=mx_b_scales,
        block_a=mx_block, block_b=mx_block,
    ))
    a15_cols, a15_depth, a15_block, a15_rows_block = 8, 64, 32, 4
    a15_weights = rng.integers(
        0, 256, size=(a15_cols, a15_depth), dtype=np.uint64
    ).astype(np.uint8)
    a15_weights[a15_weights == 0x7F] = 0x38
    a15_weights[a15_weights == 0xFF] = 0xB8
    a15_scales = rng.integers(
        120, 135,
        size=((a15_cols // a15_rows_block) * (a15_depth // a15_block),),
        dtype=np.uint64,
    ).astype(np.uint8)
    cases.append(matmul_case(
        "matmul_fp8_a15_block_rows",
        "amendment A15's two-dimensional scale block: one E8M0 code per "
        "4 x 32 tile of the weight, which is the shape the released DeepSeek "
        "FP8 linears use and the shape an A8-only reader addresses wrongly",
        capability, root,
        activation_codes=random_bf16(rng, (3, a15_depth)),
        weight_codes=a15_weights,
        activation_dtype=DType.BF16, weight_dtype=DType.FP8_E4M3FN,
        weight_scales=a15_scales,
        block_b=a15_block, block_rows_b=a15_rows_block,
    ))

    # -- TENSOR.MATMUL negative cases ------------------------------------
    nonfinite_activations = random_bf16(rng, (2, 8))
    nonfinite_activations[0, 0] = 0x7F80        # BF16 +infinity
    cases.append(matmul_case(
        "matmul_bf16_operand_nonfinite",
        "a BF16 infinity in the activation: the contraction is refused and "
        "the destination is left untouched",
        capability, root,
        activation_codes=nonfinite_activations,
        weight_codes=random_bf16(rng, (3, 8)),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
        expect_fault=True,
    ))
    reserved_weights = np.full((3, 8), 0x38, dtype=np.uint8)
    reserved_weights[0, 0] = 0x7F               # reserved E4M3FN encoding
    cases.append(matmul_case(
        "matmul_fp8_reserved_encoding",
        "the reserved E4M3FN encoding 0x7f is a poisoned block, not a value",
        capability, root,
        activation_codes=np.full((2, 8), 0x38, dtype=np.uint8),
        weight_codes=reserved_weights,
        activation_dtype=DType.FP8_E4M3FN, weight_dtype=DType.FP8_E4M3FN,
        expect_fault=True,
    ))
    cases.append(matmul_case(
        "matmul_bf16_product_overflow",
        "the largest finite BF16 squared leaves the binary32 range.  The "
        "offending product is the first reduction index of the first output "
        "element, which is where the two refusal orders coincide -- see the "
        "campaign's claim boundary",
        capability, root,
        activation_codes=np.full((2, 4), 0x7F7F, dtype=np.uint16),
        weight_codes=np.full((3, 4), 0x7F7F, dtype=np.uint16),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
        expect_fault=True,
    ))
    cases.append(matmul_case(
        "matmul_bf16_accumulate_overflow",
        "every product is finite and their ascending-K sum is not: 2**63 "
        "squared is 2**126, and four of them overflow binary32",
        capability, root,
        activation_codes=np.full((2, 4), 0x5F00, dtype=np.uint16),
        weight_codes=np.full((3, 4), 0x5F00, dtype=np.uint16),
        activation_dtype=DType.BF16, weight_dtype=DType.BF16,
        expect_fault=True,
    ))
    cases.append(matmul_case(
        "matmul_fp8_scale_overflow",
        "a legal E8M0 code of 2**127 against the largest finite E4M3FN value: "
        "the scale application itself leaves the binary32 range",
        capability, root,
        activation_codes=random_bf16(rng, (2, 32)),
        weight_codes=np.full((3, 32), 0x7E, dtype=np.uint8),
        activation_dtype=DType.BF16, weight_dtype=DType.FP8_E4M3FN,
        weight_scales=np.full((3,), 254, dtype=np.uint8),
        block_b=32,
        expect_fault=True,
    ))

    # -- VECTOR.ADD ------------------------------------------------------
    cases.append(vector_add_case(
        "vector_add_residual",
        "the residual add at a layer boundary: 6 x 64 BF16 through one "
        "binary32 rounding",
        capability, root,
        left_codes=random_bf16(rng, (6, 64)),
        right_codes=random_bf16(rng, (6, 64)),
    ))
    # 0x7f7f is the largest finite BF16, 1.9921875 x 2**127.  Adding 2**119
    # (0x7b00) lands on 1.99609375 x 2**127 -- inside binary32, and exactly the
    # midpoint between the largest finite BF16 and the BF16 infinity, so
    # ties-to-even rounds up and the conversion saturates.  Half the elements
    # do that and half do not, so the saturation count is a specific number
    # rather than "all" or "none".
    saturating_left = np.full((2, 16), 0x7F7F, dtype=np.uint16)
    saturating_right = np.tile(
        np.array([0x7B00, 0x3F80], dtype=np.uint16), (2, 8)
    )
    cases.append(vector_add_case(
        "vector_add_saturating",
        "a sum that stays inside binary32 and leaves the BF16 range: the "
        "saturated value is reported and the saturation counted, on exactly "
        "the sixteen elements where it happens",
        capability, root,
        left_codes=saturating_left, right_codes=saturating_right,
    ))
    cancelling_left = random_bf16(rng, (4, 32))
    cancelling_right = cancelling_left ^ np.uint16(0x8000)
    cases.append(vector_add_case(
        "vector_add_exact_cancellation",
        "every element cancels exactly against its own negation, so every "
        "result is a zero whose sign the contract canonicalises",
        capability, root,
        left_codes=cancelling_left, right_codes=cancelling_right,
    ))
    nonfinite_left = random_bf16(rng, (2, 8))
    nonfinite_left[0, 0] = 0xFF80               # BF16 -infinity
    cases.append(vector_add_case(
        "vector_add_nonfinite",
        "an infinite residual operand is refused rather than propagated",
        capability, root,
        left_codes=nonfinite_left, right_codes=random_bf16(rng, (2, 8)),
        expect_fault=True,
    ))

    # -- SELECTION.ARGMAX ------------------------------------------------
    logits = random_bf16(rng, (512,), scale=4.0)
    logits[311] = 0x4300                        # a single unambiguous maximum
    cases.append(selection_case(
        "selection_argmax_dense",
        "512 BF16 logits with one maximum: the token is the index of that "
        "maximum and the tie multiplicity is one",
        capability, root,
        logit_payload=np.ascontiguousarray(logits, dtype=np.uint16).tobytes(),
        logit_dtype=DType.BF16, count=512,
    ))
    tied = random_bf16(rng, (256,), scale=1.0)
    tied[np.abs(tied.astype(np.int32) - 0x4200) < 0] = 0     # no-op guard
    tied[17] = 0x4200
    tied[93] = 0x4200
    tied[201] = 0x4200
    tied[tied == 0x4200] = 0x4200
    cases.append(selection_case(
        "selection_argmax_lowest_id_wins",
        "three logits share the maximum: greedy_lowest_token_id_argmax must "
        "select 17 and publish a tie multiplicity of three.  A comparison "
        "that replaced the running best on equality would select 201 and "
        "still look like a maximum",
        capability, root,
        logit_payload=np.ascontiguousarray(tied, dtype=np.uint16).tobytes(),
        logit_dtype=DType.BF16, count=256,
    ))
    signed = np.full((64,), 0xBF80, dtype=np.uint16)   # -1.0 everywhere
    signed[40] = 0x8000                                 # BF16 negative zero
    signed[9] = 0x0000                                  # BF16 positive zero
    cases.append(selection_case(
        "selection_argmax_signed_zero_tie",
        "the maximum is zero and it appears as both +0 and -0.  They compare "
        "equal in binary32, so the token is the lower index and the tie "
        "multiplicity is two; a comparison keyed on the raw sign-magnitude "
        "pattern would rank -0 below +0 and get both wrong",
        capability, root,
        logit_payload=np.ascontiguousarray(signed, dtype=np.uint16).tobytes(),
        logit_dtype=DType.BF16, count=64,
    ))
    fp32_logits = rng.standard_normal(300).astype(np.float32)
    fp32_logits[123] = np.float32(12.5)
    cases.append(selection_case(
        "selection_argmax_binary32_partition",
        "a vocabulary partition that already produced binary32 logits, which "
        "the frozen rule reads without widening",
        capability, root,
        logit_payload=np.ascontiguousarray(fp32_logits, dtype=np.float32).tobytes(),
        logit_dtype=DType.FP32, count=300,
    ))
    poisoned = random_bf16(rng, (32,))
    poisoned[11] = 0x7FC0                       # BF16 NaN
    cases.append(selection_case(
        "selection_argmax_nonfinite",
        "a NaN logit is a numeric fault: no token may be selected from it",
        capability, root,
        logit_payload=np.ascontiguousarray(poisoned, dtype=np.uint16).tobytes(),
        logit_dtype=DType.BF16, count=32,
        expect_fault=True,
    ))

    # -- DMA.GATHER and DMA.SCATTER --------------------------------------
    source = random_bf16(rng, (32, 8))
    cases.append(dma_case(
        "dma_gather_rows",
        "twelve rows gathered out of thirty-two, which is the shape every "
        "KV read and every routed-expert weight read takes",
        capability, root, scatter=False,
        indices=rng.permutation(32)[:12].astype(np.uint32),
        rows=32, trailing=8, payload_codes=source,
    ))
    cases.append(dma_case(
        "dma_gather_repeated_index",
        "a repeated gather index is not an error: the same row is read twice",
        capability, root, scatter=False,
        indices=np.array([5, 5, 31, 0, 5, 17], dtype=np.uint32),
        rows=32, trailing=8, payload_codes=source,
    ))
    prior = random_bf16(rng, (24, 4))
    cases.append(dma_case(
        "dma_scatter_rows",
        "six rows written into a twenty-four-row destination whose other "
        "eighteen rows must survive unchanged.  The destination starts from "
        "real bytes, not zeros, so a datapath that forgot to read it back "
        "cannot pass",
        capability, root, scatter=True,
        indices=np.array([3, 19, 0, 11, 23, 7], dtype=np.uint32),
        rows=24, trailing=4,
        payload_codes=random_bf16(rng, (6, 4)), prior_codes=prior,
    ))
    cases.append(dma_case(
        "dma_scatter_repeated_index_last_wins",
        "slot 0 and slot 4 name the same destination row: ascending slot "
        "order makes the later slot the one that survives, deterministically",
        capability, root, scatter=True,
        indices=np.array([9, 2, 15, 9, 9, 0], dtype=np.uint32),
        rows=24, trailing=4,
        payload_codes=random_bf16(rng, (6, 4)), prior_codes=prior,
    ))
    cases.append(dma_case(
        "dma_gather_index_out_of_range",
        "an index one past the addressed extent: refused before anything "
        "moves, not clamped and not wrapped",
        capability, root, scatter=False,
        indices=np.array([1, 2, 32, 4], dtype=np.uint32),
        rows=32, trailing=8, payload_codes=source,
        expect_fault=True,
    ))
    cases.append(dma_case(
        "dma_scatter_index_out_of_range",
        "the same refusal on the write side, where a clamped index would "
        "corrupt a row nothing named",
        capability, root, scatter=True,
        indices=np.array([1, 2, 40, 4, 5, 6], dtype=np.uint32),
        rows=24, trailing=4,
        payload_codes=random_bf16(rng, (6, 4)), prior_codes=prior,
        expect_fault=True,
    ))
    return cases


# ---------------------------------------------------------------------------
# Golden execution
# ---------------------------------------------------------------------------
def as_words(array: np.ndarray) -> list[int]:
    """One element per 32-bit word, whatever the storage format is."""
    flat = np.ascontiguousarray(array).reshape(-1)
    if flat.dtype == np.float32:
        flat = flat.view(np.uint32)
    return [int(value) & 0xFFFFFFFF for value in flat.astype(np.uint64)]


def run_golden(case: Case, capability: Capability) -> dict[str, Any]:
    """Execute one real program on the functional device with real engines."""
    device = Device(case.deployment, capability, verify=False, trace=True)
    session = device.create_session()
    result = device.run_transaction(session, entrypoint_id=0, symbols=dict(case.symbols))
    entry = next(
        e for e in case.deployment.entrypoints if e["entrypoint_id"] == 0
    )
    symbols = dict(case.symbols)
    symbols.setdefault(0, int(entry["phase"]))
    counters = {k: int(v) for k, v in sorted(result.counters.items())}

    def read(view_id: int) -> np.ndarray | None:
        if view_id == NO_ID:
            return None
        view = device.views.resolve(view_id, {}, symbols)
        return np.ascontiguousarray(device.views.read_array(view))

    return {
        "status": int(result.status),
        "trap_class": int(result.trap_class),
        "message": result.message,
        "counters": counters,
        "operand0": read(case.operand0_view),
        "operand1": read(case.operand1_view),
        "output": read(case.output_view),
        "scale0": (
            None if case.scale0_object == NO_ID
            else np.frombuffer(
                device.memory[case.scale0_object].read(0, case.scale0_count),
                dtype=np.uint8,
            )
        ),
        "scale1": (
            None if case.scale1_object == NO_ID
            else np.frombuffer(
                device.memory[case.scale1_object].read(0, case.scale1_count),
                dtype=np.uint8,
            )
        ),
    }


# ---------------------------------------------------------------------------
# Storage-format decode probe
# ---------------------------------------------------------------------------
def decode_probe_entries() -> list[tuple[int, int, int, int]]:
    """``(format, word, error, binary32 code)`` straight from the tables.

    Exhaustive over the three block formats, whose decoders are the ones a
    hand-written RTL can plausibly get wrong, and over every BF16 exponent with
    four significands and both signs.  The expected values come from
    ``runtime.sim.formats``, whose tables are enumerated at import time from
    the exact ``fractions.Fraction`` decoders in ``runtime/reference``.
    """
    entries: list[tuple[int, int, int, int]] = []

    def append(format_id: int, word: int, value: np.floating) -> None:
        if bool(np.isnan(value)):
            entries.append((format_id, word, 1, 0))
            return
        code = int(np.float32(value).view(np.uint32))
        if code & 0x7FFFFFFF == 0:
            code = 0                     # canonical positive zero
        entries.append((format_id, word, 0, code))

    for code in range(256):
        append(int(DType.FP8_E4M3FN), code, sim_formats.E4M3FN_VALUES[code])
    for code in range(16):
        append(int(DType.MXFP4_E2M1), code, sim_formats.MXFP4_VALUES[code])
    for code in range(256):
        append(int(DType.E8M0_SCALE), code, sim_formats.E8M0_VALUES[code])
    for exponent in range(256):
        for significand in (0x00, 0x01, 0x40, 0x7F):
            for sign in (0, 1):
                pattern = (sign << 15) | (exponent << 7) | significand
                if exponent == 0xFF:
                    entries.append((int(DType.BF16), pattern, 1, 0))
                    continue
                widened = sim_formats.widen_bf16(
                    np.array([pattern], dtype=np.uint16)
                )
                append(int(DType.BF16), pattern, widened[0])
    return entries


# ---------------------------------------------------------------------------
# Binary32 arithmetic probe
# ---------------------------------------------------------------------------
#: Binary32 encodings that break a floating-point unit, if anything does:
#: both zeros, both smallest subnormals, the largest subnormal, the smallest
#: normal, one, two, the largest finite, and a spread of exponents that put a
#: pair on either side of every rounding boundary.
ARITH_CORNERS: tuple[int, ...] = (
    0x00000000, 0x80000000,          # +0, -0
    0x00000001, 0x80000001,          # smallest subnormals
    0x00400000, 0x807FFFFF,          # mid and largest subnormal
    0x00800000, 0x80800000,          # smallest normals
    0x00800001, 0x00FFFFFF,
    0x3F800000, 0xBF800000,          # +/-1
    0x3F800001, 0xBF7FFFFF,
    0x40000000, 0xC0000000,          # +/-2
    0x4B800000, 0xCB800000,          # 2**24, where a unit ulp disappears
    0x4B7FFFFF, 0x33800000,          # 2**24 - 1, 2**-24
    0x7F7FFFFF, 0xFF7FFFFF,          # largest finite, both signs
    0x7F000000, 0xFF000000,
    0x5F000000, 0x5F7F0000,          # BF16-representable large values
    0x7F7F0000, 0xFF7F0000,          # the largest finite BF16, widened
    0x00000002, 0x00000003,
    0x41200000, 0xC1200000,
    0x38800000, 0xB8800000,
    0x7E800000, 0xFE800000,
)


def arith_probe_entries() -> list[tuple[int, int, int, int, int, int, int, int]]:
    """``(a, b, add_err, add, mul_err, mul, bf16_err_sat, bf16)`` exactly.

    The engine cases exercise the binary32 adder and multiplier on the value
    distribution real operands produce -- normals of moderate exponent, mostly
    of the same magnitude.  That is the distribution under which a rounding or
    normalisation defect is least likely to show.  This sweep is the other
    distribution: every pair of the corner set, plus a seeded spread over
    BF16-widened codes, general binary32 codes and the subnormal range.

    The authority is ``runtime.reference.formats``, whose ``binary32_add`` and
    ``binary32_multiply`` compute with :class:`fractions.Fraction` and round
    once, so no host floating-point mode participates on the reference side.
    """
    rng = np.random.default_rng(1731205)
    left: list[int] = []
    right: list[int] = []
    for a in ARITH_CORNERS:
        for b in ARITH_CORNERS:
            left.append(a)
            right.append(b)
    # BF16-widened codes: the operands a contraction lane actually sees.
    widened = (
        rng.integers(0, 1 << 16, size=900, dtype=np.uint64).astype(np.uint32) << 16
    )
    left.extend(int(v) for v in widened)
    right.extend(int(v) for v in widened[::-1])
    # General binary32, including the nonfinite band, so the refusal is checked.
    general = rng.integers(0, 1 << 32, size=900, dtype=np.uint64).astype(np.uint32)
    left.extend(int(v) for v in general)
    right.extend(int(v) for v in general[::-1])
    # Subnormals and near-subnormal products, where an implementation that
    # normalises with a shift loop and one that uses a leading-zero count part
    # company.
    subnormal = rng.integers(0, 1 << 24, size=600, dtype=np.uint64).astype(np.uint32)
    left.extend(int(v) for v in subnormal)
    right.extend(int(v) for v in subnormal[::-1])

    entries: list[tuple[int, int, int, int, int, int, int, int]] = []
    for a, b in zip(left, right):
        add_err, add_value = _exact_binary(exact_formats.binary32_add, a, b)
        mul_err, mul_value = _exact_binary(exact_formats.binary32_multiply, a, b)
        try:
            narrowed = exact_formats.binary32_bits_to_bf16_rne(a)
        except exact_formats.NumericReferenceError:
            bf_field, bf_value = 2, 0          # error 1 in the top two bits
        else:
            bf_field = 1 if narrowed.saturated else 0
            bf_value = int(narrowed.code)
        entries.append(
            (a, b, add_err, add_value, mul_err, mul_value, bf_field, bf_value)
        )
    return entries


def _exact_binary(operation: Any, a: int, b: int) -> tuple[int, int]:
    """One exact binary32 operation, as ``(package error code, result)``.

    The package reports 1 for a nonfinite operand and 2 for a finite result
    that leaves the binary32 range, and the exact reference raises for both, so
    the two are distinguished here by which operand is nonfinite rather than by
    reading the message.
    """
    nonfinite = ((a >> 23) & 0xFF) == 0xFF or ((b >> 23) & 0xFF) == 0xFF
    if nonfinite:
        return 1, 0
    try:
        return 0, int(operation(a, b))
    except exact_formats.NumericReferenceError:
        return 2, 0


# ---------------------------------------------------------------------------
# Emission
# ---------------------------------------------------------------------------
def hex_lines(values: Sequence[int], width_bits: int, total: int, name: str) -> str:
    digits = width_bits // 4
    if len(values) > total:
        raise SystemExit(
            f"{name} overflow: {len(values)} words exceed the {total}-word image"
        )
    padded = list(values) + [0] * (total - len(values))
    return "".join(f"{value:0{digits}x}\n" for value in padded)


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)

    coverage = load_engines()
    if coverage["unavailable"]:
        raise SystemExit(
            "an engine module failed to load, so the correlation would be "
            f"against a partially built device: {coverage['unavailable']}"
        )
    capability = engine_capability()
    with tempfile.TemporaryDirectory(prefix="opentallas-abi3-engine-") as raw:
        root = Path(raw)
        cases = build_cases(capability, root)
        records, images = emit(cases, capability, out)
    summary = publish(cases, records, images, capability, out)
    print(
        f"abi3 engine vectors: cases={summary['case_count']} "
        f"families={summary['family_count']} "
        f"results={summary['result_word_count']} "
        f"macs={summary['mac_count']} faults={summary['fault_case_count']} "
        f"decodes={summary['decode_probe_count']} "
        f"arith={summary['arith_probe_count']}"
    )
    return 0


def emit(
    cases: list[Case], capability: Capability, out: Path
) -> tuple[list[dict[str, Any]], dict[str, list[int]]]:
    m0_words: list[int] = []
    m1_words: list[int] = []
    m2_words: list[int] = []
    m3_words: list[int] = []
    expect_words: list[int] = []
    case_words: list[int] = []
    records: list[dict[str, Any]] = []

    for case in cases:
        report = verify_deployment(case.deployment, capability)
        if report.admitted != case.expect_admitted:
            raise SystemExit(
                f"{case.name}: verifier admitted={report.admitted}, expected "
                f"{case.expect_admitted}: {report.errors}"
            )
        golden = run_golden(case, capability)
        faulted = golden["status"] != 0
        if faulted != case.expect_fault:
            raise SystemExit(
                f"{case.name}: golden status {golden['status']} "
                f"({golden['message']!r}) contradicts expect_fault="
                f"{case.expect_fault}"
            )

        a_base = len(m0_words)
        m0_words.extend(as_words(golden["operand0"]))
        b_base = len(m1_words)
        if golden["operand1"] is not None:
            m1_words.extend(as_words(golden["operand1"]))
        c_base = len(m1_words)
        if case.prior_payload is not None:
            m1_words.extend(as_words(case.prior_payload))
        scale_a_base = len(m2_words)
        if golden["scale0"] is not None:
            m2_words.extend(as_words(golden["scale0"]))
        scale_b_base = len(m3_words)
        if golden["scale1"] is not None:
            m3_words.extend(as_words(golden["scale1"]))

        # Where this case's results live in the shared result memory, and what
        # the checkers must find there.
        out_base = len(expect_words)
        if faulted:
            fault_code = classify_fault(golden["message"])
            # The whole destination window must still hold the unwritten
            # sentinel: a refusal that left part of a result behind is a
            # different refusal.
            window = destination_window(case)
            expect_words.extend([UNWRITTEN] * window)
            expect_count = window
            result_count = 0
            saturations = 0
            work = 0
            token = 0
            ties = 0
            flags = FLAG_EXPECT_UNTOUCHED
        else:
            fault_code = ERR_NONE
            output_words = as_words(golden["output"])
            expect_words.extend(output_words)
            expect_count = len(output_words)
            result_count, saturations, work, token, ties, flags = expectations(
                case, golden, expect_count
            )

        record_words = [
            case.family,
            case.sub,
            case.rows,
            case.cols,
            case.depth,
            case.count,
            view_dtype(case.deployment, case.operand0_view),
            view_dtype(case.deployment, case.operand1_view),
            a_base,
            b_base,
            c_base,
            out_base,
            1 if case.scale0_object != NO_ID else 0,
            1 if case.scale1_object != NO_ID else 0,
            case.block_a,
            case.block_b,
            case.block_rows_a,
            case.block_rows_b,
            scale_a_base,
            scale_b_base,
            case.slots,
            case.trailing,
            case.extent,
            fault_code,
            result_count,
            saturations,
            work,
            token,
            ties,
            out_base,
            expect_count,
            flags,
        ]
        if len(record_words) != CASE_STRIDE:
            raise SystemExit(
                f"case record is {len(record_words)} words, expected {CASE_STRIDE}"
            )
        case_words.extend(record_words)

        records.append({
            "name": case.name,
            "note": case.note,
            "family": case.family,
            "sub": case.sub,
            "golden_status": golden["status"],
            "golden_trap_class": golden["trap_class"],
            "golden_message": golden["message"],
            "golden_counters": golden["counters"],
            "expected_fault_code": fault_code,
            "expected_result_count": result_count,
            "expected_saturations": saturations,
            "expected_work": work,
            "expected_token": token,
            "expected_tie_multiplicity": ties,
            "expected_word_count": expect_count,
            "flags": flags,
            "rows": case.rows,
            "cols": case.cols,
            "depth": case.depth,
            "count": case.count,
            "slots": case.slots,
            "trailing": case.trailing,
            "extent": case.extent,
            "operand0_dtype": view_dtype(case.deployment, case.operand0_view),
            "operand1_dtype": view_dtype(case.deployment, case.operand1_view),
            "block_a": case.block_a,
            "block_b": case.block_b,
            "block_rows_a": case.block_rows_a,
            "block_rows_b": case.block_rows_b,
            "program_sha256": hashlib.sha256(case.deployment.program).hexdigest(),
            "descriptor_table_sha256": hashlib.sha256(
                case.deployment.table.encode()
            ).hexdigest(),
            "operand0_sha256": words_digest(as_words(golden["operand0"])),
            "operand1_sha256": (
                "" if golden["operand1"] is None
                else words_digest(as_words(golden["operand1"]))
            ),
            "expected_sha256": words_digest(
                expect_words[out_base : out_base + expect_count]
            ),
        })

    images = {
        "m0": m0_words,
        "m1": m1_words,
        "m2": m2_words,
        "m3": m3_words,
        "expect": expect_words,
        "case": case_words,
    }
    return records, images


def words_digest(words: Sequence[int]) -> str:
    payload = np.asarray(list(words), dtype=np.uint32).tobytes()
    return hashlib.sha256(payload).hexdigest()


def view_dtype(deployment: Deployment, view_id: int) -> int:
    if view_id == NO_ID:
        return 0
    from runtime.abi3.descriptors import ExtendedDescriptorType

    descriptor = deployment.table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW)
    return int(descriptor.payload["dtype"])


def destination_window(case: Case) -> int:
    """How many result words a refusal must leave untouched."""
    if case.family == int(Major.TENSOR):
        return case.rows * case.cols
    if case.family == int(Major.VECTOR):
        return case.count
    if case.family == int(Major.SELECTION):
        return 1
    if case.sub == int(Dma.SCATTER):
        return case.extent * case.trailing
    return case.slots * case.trailing


def expectations(
    case: Case, golden: dict[str, Any], written: int
) -> tuple[int, int, int, int, int, int]:
    """The counters and flags this case compares, from the golden counters.

    Nothing here is a number this file chose: every value is read out of the
    counter set the functional engine published, or is the element count of the
    view it wrote.
    """
    counters = golden["counters"]
    if case.family == int(Major.TENSOR):
        return (
            int(counters["tensor.output_elements"]),
            int(counters.get("tensor.saturations", 0)),
            case.rows * case.cols * case.depth,
            0,
            0,
            FLAG_COMPARE_WORK | FLAG_COMPARE_SATURATION,
        )
    if case.family == int(Major.VECTOR):
        elements = int(counters["vector.elements"])
        if elements != written:
            # The engine's element counter and the view it wrote must agree, or
            # one of the two is not describing this operation.
            raise SystemExit(
                f"{case.name}: the vector engine counted {elements} elements "
                f"and wrote {written}"
            )
        return (
            elements,
            int(counters.get("vector.saturations", 0)),
            elements,
            0,
            0,
            FLAG_COMPARE_WORK | FLAG_COMPARE_SATURATION,
        )
    if case.family == int(Major.SELECTION):
        if written != 1:
            raise SystemExit(
                f"{case.name}: selection wrote {written} elements; a token ID "
                "is exactly one"
            )
        return (
            written,
            0,
            int(counters["selection.vocabulary_elements"]),
            int(golden["output"].reshape(-1)[0]),
            int(counters["selection.tie_multiplicity"]),
            FLAG_COMPARE_WORK | FLAG_COMPARE_TOKEN,
        )
    moved = int(
        counters.get("dma.scatter_elements", counters.get("dma.gather_elements", 0))
    )
    return (moved, 0, case.slots, 0, 0, FLAG_COMPARE_WORK)


def publish(
    cases: list[Case],
    records: list[dict[str, Any]],
    images: dict[str, list[int]],
    capability: Capability,
    out: Path,
) -> dict[str, Any]:
    probe = decode_probe_entries()
    decode_words: list[int] = []
    for format_id, word, error, value in probe:
        decode_words.extend([format_id, word, error, value])
    arith = arith_probe_entries()
    arith_words: list[int] = []
    for entry in arith:
        arith_words.extend(entry)

    families = sorted({(case.family, case.sub) for case in cases})
    mac_count = sum(
        case.rows * case.cols * case.depth
        for case in cases
        if case.family == int(Major.TENSOR)
    )
    fault_count = sum(1 for case in cases if case.expect_fault)
    result_words = len(images["expect"])
    meta = [
        len(cases), len(families), result_words, mac_count,
        fault_count, len(probe), CASE_STRIDE, len(arith),
    ]

    files = {
        "e3_m0.hex": hex_lines(images["m0"], 32, M0_WORDS, "e3_m0"),
        "e3_m1.hex": hex_lines(images["m1"], 32, M1_WORDS, "e3_m1"),
        "e3_m2.hex": hex_lines(images["m2"], 32, M2_WORDS, "e3_m2"),
        "e3_m3.hex": hex_lines(images["m3"], 32, M3_WORDS, "e3_m3"),
        "e3_expect.hex": hex_lines(images["expect"], 32, RESULT_WORDS, "e3_expect"),
        "e3_case.hex": hex_lines(images["case"], 32, CASE_WORDS, "e3_case"),
        "e3_decode.hex": hex_lines(decode_words, 32, DECODE_WORDS, "e3_decode"),
        "e3_arith.hex": hex_lines(arith_words, 32, ARITH_WORDS, "e3_arith"),
        "e3_meta.hex": hex_lines(meta, 32, META_WORDS, "e3_meta"),
    }
    for name, payload in files.items():
        (out / name).write_text(payload, encoding="ascii")

    summary = {
        "schema": "opentallas.rtl.abi3_engine_vectors.v1",
        "abi": {"major": 3, "minor": 0},
        "capability_digest": capability.digest,
        "engine_policy": (
            "no engine is stubbed: every case is executed by "
            "runtime.sim.device.Device with the real implementations in "
            "runtime.sim.engines, and the operand and result images are read "
            "back out of device memory after the transaction"
        ),
        "case_count": len(cases),
        "family_count": len(families),
        "families": [
            {"family": family, "sub": sub} for family, sub in families
        ],
        "result_word_count": result_words,
        "mac_count": mac_count,
        "fault_case_count": fault_count,
        "positive_case_count": len(cases) - fault_count,
        "decode_probe_count": len(probe),
        "arith_probe_count": len(arith),
        "arith_reference": (
            "runtime.reference.formats binary32_add, binary32_multiply and "
            "binary32_bits_to_bf16_rne, which compute with fractions.Fraction "
            "and round once, so no host floating-point mode participates"
        ),
        "decode_reference": (
            "runtime.sim.formats E4M3FN_VALUES, MXFP4_VALUES and E8M0_VALUES, "
            "enumerated at import time from the exact fractions.Fraction "
            "decoders in runtime/reference/formats.py, plus "
            "runtime.sim.formats.widen_bf16"
        ),
        "numeric_reference": {
            "bf16_bf16_fp32_sequential_rne_v1": (
                "runtime.tensor_accelerator.bf16.dense_bf16_linear_bf16 for "
                "BF16 x BF16 -> BF16; runtime.sim.backend."
                "sequential_matmul_binary32 for every other operand pair"
            ),
            "bf16_add_rne_v1": (
                "runtime.tensor_accelerator.elementwise.bf16_add_rne"
            ),
            "greedy_lowest_token_id_argmax": (
                "runtime.sim.engines.selection.argmax"
            ),
            "exact_index_select_v1": "runtime.sim.engines.dma gather and scatter",
        },
        "required_marker": (
            f"PASS: ABI3 RTL engine datapaths cases={len(cases)} "
            f"families={len(families)} results={result_words} "
            f"macs={mac_count} faults={fault_count} decodes={len(probe)} "
            f"arith={len(arith)}"
        ),
        "geometry": {
            "m0_words": M0_WORDS,
            "m1_words": M1_WORDS,
            "m2_words": M2_WORDS,
            "m3_words": M3_WORDS,
            "result_words": RESULT_WORDS,
            "case_words": CASE_WORDS,
            "case_stride": CASE_STRIDE,
            "decode_words": DECODE_WORDS,
            "decode_words_used": len(decode_words),
            "decode_stride": 4,
            "arith_words": ARITH_WORDS,
            "arith_words_used": len(arith_words),
            "arith_stride": ARITH_STRIDE,
            "unwritten_sentinel": UNWRITTEN,
        },
        "flags": {
            "compare_work": FLAG_COMPARE_WORK,
            "compare_token": FLAG_COMPARE_TOKEN,
            "expect_untouched": FLAG_EXPECT_UNTOUCHED,
            "compare_saturation": FLAG_COMPARE_SATURATION,
        },
        "fault_codes": {
            "none": ERR_NONE,
            "operand_nonfinite": ERR_OPERAND_NONFINITE,
            "product_range": ERR_PRODUCT_RANGE,
            "accumulate_range": ERR_ACCUMULATE_RANGE,
            "index_range": ERR_INDEX_RANGE,
            "select_nonfinite": ERR_SELECT_NONFINITE,
            "scale_range": ERR_SCALE_RANGE,
            "shape": ERR_SHAPE,
        },
        "image_sha256": {
            name: hashlib.sha256(payload.encode("ascii")).hexdigest()
            for name, payload in sorted(files.items())
        },
        "cases": records,
    }
    (out / "abi3_engine_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    raise SystemExit(build())
