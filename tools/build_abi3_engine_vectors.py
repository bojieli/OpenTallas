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

``VECTOR.ADD`` and six bounded VECTOR forms
    The residual, at every layer boundary, under ``bf16_add_rne_v1``; unscaled
    one-input/one-output ``CONVERT``; constant and same-shape ``SCALE``;
    normalized 128-point ``HADAMARD``; four-head, unit-scale ``INDEX_SCORE``;
    ``COMPRESS_PROJECT``; and four-stream ``HYPER_CONNECT_POST``.  The generated
    ``vector_rtl_scope`` is the authority for the exact shape limits and names
    every unsupported form.  Out-of-bound and descriptor-inconsistent cases
    are retained as RTL-only ``ERR_SHAPE`` refusals even when the more general
    functional Device legitimately executes the same ABI 3.0 program.

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
from dataclasses import dataclass, field as dc_field, replace as dc_replace
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
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    LayoutClass,
    Phase,
)
from runtime.reference.compression import compress_project_bf16  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402
from runtime.reference import formats as exact_formats  # noqa: E402
from runtime.reference.index_score import index_score_bf16  # noqa: E402
from runtime.reference.vector import hc_post_bf16  # noqa: E402
from runtime.sim import formats as sim_formats  # noqa: E402
from runtime.sim.device import Device  # noqa: E402
from runtime.sim.engines import load_engines  # noqa: E402

OUTPUT_DIR = ROOT / "testdata/compiler/abi3_engine"
VECTOR_SCHEMA = "opentallas.rtl.abi3_engine_vectors.v2"

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
CASE_WORDS = 16384
DECODE_WORDS = 16384
ARITH_WORDS = 65536
ARITH_STRIDE = 12
META_WORDS = 8
CASE_STRIDE = 80

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
    # Selection and VECTOR operands use similar English around non-finites,
    # but they are different architectural refusals.  Resolve the explicitly
    # named VECTOR kernels before the legacy generic selection signatures.
    vector_labels = (
        "CONVERT source",
        "SCALE source",
        "SCALE factor",
        "HADAMARD source",
        "INDEX_SCORE query",
        "INDEX_SCORE key",
        "INDEX_SCORE head weight",
        "COMPRESS_PROJECT hidden",
        "COMPRESS_PROJECT KV projection",
        "COMPRESS_PROJECT gate projection",
        "HYPER_CONNECT_POST branch",
        "HYPER_CONNECT_POST residual",
        "HYPER_CONNECT_POST post",
        "HYPER_CONNECT_POST combination",
    )
    if any(label in message for label in vector_labels) and (
        "NaN" in message or "infinite" in message or "infinity" in message
    ):
        return ERR_OPERAND_NONFINITE
    if "qualified transform" in message:
        return ERR_SHAPE
    if "SCALE product" in message:
        return ERR_PRODUCT_RANGE
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
            "max_event_id": 511,
            "max_state_resources": 16,
            "max_outstanding_per_queue": 8,
            "max_context_positions": 256,
            "max_expert_ids": 1024,
            "max_topk": 16,
            "max_vocabulary": 4096,
            "max_sessions": 4,
            "max_nodes": 1,
        },
        numeric_contracts=(
            "identity_storage_v1",
            "bf16_bf16_fp32_sequential_rne_v1",
            "bf16_add_rne_v1",
            "bf16_mul_rne_v1",
            "bf16_scale_rne_v1",
            "bf16_to_fp32_exact_v1",
            "fp32_to_bf16_rne_v1",
            "fp8_e4m3fn_to_bf16_rne_v1",
            "deepseek_v4_hadamard_128_bf16_v1",
            "deepseek_v4_index_score_bf16_v1",
            "deepseek_v4_compress_project_binary32_v1",
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
    operand2_view: int = NO_ID
    operand3_view: int = NO_ID
    output_view: int = NO_ID
    output_dtype: int = 0
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
    #: When present, this literal occupies case-record field 10 instead of a
    #: scatter prior-image base.  SCALE and INDEX_SCORE use it for scale_bits.
    scalar_bits: int | None = None
    #: Human-readable, explicit documentation of every generic case-record
    #: field repurposed by a bounded VECTOR datapath.
    rtl_config: dict[str, Any] = dc_field(default_factory=dict)
    expect_admitted: bool = True
    expect_fault: bool = False
    #: A bounded RTL profile may intentionally refuse a deployment the
    #: general functional engine accepts (for example CONVERT count 513).
    #: This is distinct from ``expect_fault``, which describes Device.
    rtl_expected_fault_code: int | None = None
    #: Corrupt one independently derived descriptor-admission field while
    #: retaining the valid deployment and operands.  Every such case must be
    #: refused with ERR_SHAPE before an operand read or destination write.
    rtl_descriptor_overrides: dict[str, Any] = dc_field(default_factory=dict)
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
    int(DType.U16): 2,
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
    output_strides: tuple[int, int] | None = None,
    output_element_offset: int = 0,
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
    if output_strides is None and output_element_offset == 0:
        view_out = w.scratch_view(DType.BF16, [rows, cols], key="view.out")
    else:
        strides = output_strides or (cols, 1)
        if output_element_offset < 0 or any(v < 0 for v in strides):
            raise ValueError("Output offsets and strides must be unsigned")
        elements = output_element_offset + (rows-1)*strides[0] + (cols-1)*strides[1] + 1
        object_id = w.scratch(2*elements)
        view_out = w.builder.tensor_view(object_id=object_id, dtype=DType.BF16,
            dims=[rows, cols], strides=strides, element_offset=output_element_offset,
            permissions=READ_WRITE, key="view.out")
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


def _storage_payload(values: np.ndarray, dtype: DType) -> bytes:
    """Dense row-major bytes for one of the bounded VECTOR case operands."""
    array = np.ascontiguousarray(values)
    if dtype == DType.BF16:
        return array.astype(np.uint16, copy=False).tobytes()
    if dtype == DType.FP32:
        if array.dtype == np.uint32:
            return array.tobytes()
        return array.astype(np.float32, copy=False).tobytes()
    if dtype in (DType.FP8_E4M3FN, DType.U8, DType.E8M0_SCALE):
        return array.astype(np.uint8, copy=False).tobytes()
    if dtype == DType.U32:
        return array.astype(np.uint32, copy=False).tobytes()
    if dtype == DType.U16:
        return array.astype(np.uint16, copy=False).tobytes()
    if dtype == DType.MXFP4_E2M1:
        return pack_nibbles(array)
    raise SystemExit(f"no bounded VECTOR payload encoder for {dtype.name}")


def vector_convert_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    source: np.ndarray,
    input_dtype: DType,
    output_dtype: DType,
    contract: str,
    expect_fault: bool = False,
    rtl_expected_fault_code: int | None = None,
) -> Case:
    """Unscaled one-input/one-output VECTOR.CONVERT."""
    w = Workspace(name, capability, root)
    dims = list(source.shape)
    count = int(source.size)
    source_view = w.const_view(
        _storage_payload(source, input_dtype), input_dtype, dims, key="view.source"
    )
    output_view = w.scratch_view(output_dtype, dims, key="view.out")
    numeric = w.builder.numeric(
        contract=contract,
        input_dtype=input_dtype,
        output_dtype=output_dtype,
        key="num.convert",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.CONVERT),
        inputs=[source_view],
        outputs=[output_view],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.convert",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.CONVERT), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.CONVERT),
        deployment=deployment,
        root=root,
        operand0_view=source_view,
        output_view=output_view,
        output_dtype=int(output_dtype),
        count=count,
        block_a=int(output_dtype),
        expect_fault=expect_fault,
        rtl_expected_fault_code=rtl_expected_fault_code,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "unscaled_one_input_one_output",
            "cfg_block_a": "output_dtype",
            "output_dtype": int(output_dtype),
        },
    )


def vector_scale_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    source: np.ndarray,
    factors: np.ndarray | None = None,
    scale_bits: int = 0,
    expect_fault: bool = False,
) -> Case:
    """BF16 VECTOR.SCALE constant or same-shape elementwise form."""
    w = Workspace(name, capability, root)
    dims = list(source.shape)
    count = int(source.size)
    source_view = w.const_view(
        _storage_payload(source, DType.BF16), DType.BF16, dims, key="view.source"
    )
    if factors is None:
        factor_view = NO_ID
        inputs = [source_view]
        aux0 = 0
        contract = "bf16_scale_rne_v1"
    else:
        if factors.shape != source.shape:
            raise SystemExit(
                f"{name}: bounded elementwise SCALE requires a full-shape factor"
            )
        factor_view = w.const_view(
            _storage_payload(factors, DType.BF16),
            DType.BF16,
            dims,
            key="view.factor",
        )
        inputs = [source_view, factor_view]
        aux0 = 1
        contract = "bf16_mul_rne_v1"
    output_view = w.scratch_view(DType.BF16, dims, key="view.out")
    numeric = w.builder.numeric(
        contract=contract,
        input_dtype=DType.BF16,
        second_input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=int(scale_bits),
        key="num.scale",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.SCALE),
        inputs=inputs,
        outputs=[output_view],
        aux=[aux0, NO_ID, NO_ID, NO_ID],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.scale",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.SCALE), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.SCALE),
        deployment=deployment,
        root=root,
        operand0_view=source_view,
        operand1_view=factor_view,
        output_view=output_view,
        output_dtype=int(DType.BF16),
        count=count,
        block_a=aux0,
        scalar_bits=int(scale_bits),
        expect_fault=expect_fault,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "constant" if aux0 == 0 else "elementwise_full_shape",
            "cfg_block_a": "aux_id_0",
            "aux_id_0": aux0,
            "cfg_c_base": "scale_bits",
            "scale_bits": int(scale_bits),
        },
    )


def vector_hadamard_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    source: np.ndarray,
    expect_fault: bool = False,
    rtl_expected_fault_code: int | None = None,
) -> Case:
    w = Workspace(name, capability, root)
    if source.ndim != 2:
        raise SystemExit(f"{name}: bounded HADAMARD source must be rank two")
    rows, width = source.shape
    source_view = w.const_view(
        _storage_payload(source, DType.BF16),
        DType.BF16,
        [rows, width],
        key="view.source",
    )
    output_view = w.scratch_view(DType.BF16, [rows, width], key="view.out")
    numeric = w.builder.numeric(
        contract="deepseek_v4_hadamard_128_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        key="num.hadamard",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.HADAMARD),
        inputs=[source_view],
        outputs=[output_view],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.hadamard",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.HADAMARD), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.HADAMARD),
        deployment=deployment,
        root=root,
        operand0_view=source_view,
        output_view=output_view,
        output_dtype=int(DType.BF16),
        rows=int(rows),
        cols=int(width),
        count=int(source.size),
        expect_fault=expect_fault,
        rtl_expected_fault_code=rtl_expected_fault_code,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "normalized_128_point",
            "maximum_rows": 4,
            "width": 128,
        },
    )


def vector_index_score_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    query: np.ndarray,
    keys: np.ndarray,
    weights: np.ndarray,
    scale_bits: int = 0x3F800000,
    expect_fault: bool = False,
) -> Case:
    w = Workspace(name, capability, root)
    batch, span, heads, depth = query.shape
    key_batch, candidates, key_depth = keys.shape
    if batch != 1 or key_batch != batch or key_depth != depth:
        raise SystemExit(f"{name}: bounded INDEX_SCORE requires batch one")
    query_view = w.const_view(
        _storage_payload(query, DType.BF16),
        DType.BF16,
        list(query.shape),
        key="view.query",
    )
    key_view = w.const_view(
        _storage_payload(keys, DType.BF16),
        DType.BF16,
        list(keys.shape),
        key="view.keys",
    )
    weight_view = w.const_view(
        _storage_payload(weights, DType.BF16),
        DType.BF16,
        list(weights.shape),
        key="view.head_weights",
    )
    output_view = w.scratch_view(
        DType.BF16, [batch, span, candidates], key="view.out"
    )
    numeric = w.builder.numeric(
        contract="deepseek_v4_index_score_bf16_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.BF16,
        scale_bits=int(scale_bits),
        key="num.index_score",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.INDEX_SCORE),
        inputs=[query_view, key_view, weight_view],
        outputs=[output_view],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.index_score",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.INDEX_SCORE), operator)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.INDEX_SCORE),
        deployment=deployment,
        root=root,
        operand0_view=query_view,
        operand1_view=key_view,
        operand2_view=weight_view,
        output_view=output_view,
        output_dtype=int(DType.BF16),
        rows=int(span),
        cols=int(candidates),
        depth=int(depth),
        count=int(batch * span * candidates),
        slots=int(heads),
        scalar_bits=int(scale_bits),
        expect_fault=expect_fault,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "batch1_four_heads_scale_one",
            "batch": 1,
            "cfg_rows": "flattened_batch_times_span",
            "cfg_cols": "candidates",
            "cfg_depth": "head_dimension",
            "cfg_slots": "heads",
            "cfg_c_base": "scale_bits",
            "scale_bits": int(scale_bits),
            "cfg_scale_a_base": "operand2_head_weights_base",
        },
    )


def vector_compress_project_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    hidden: np.ndarray,
    kv_weights: np.ndarray,
    gate_weights: np.ndarray,
    expect_fault: bool = False,
) -> Case:
    w = Workspace(name, capability, root)
    batch, span, depth = hidden.shape
    cols, weight_depth = kv_weights.shape
    if weight_depth != depth or gate_weights.shape != kv_weights.shape:
        raise SystemExit(f"{name}: compressor projection shapes disagree")
    hidden_view = w.const_view(
        _storage_payload(hidden, DType.BF16),
        DType.BF16,
        list(hidden.shape),
        key="view.hidden",
    )
    kv_view = w.const_view(
        _storage_payload(kv_weights, DType.BF16),
        DType.BF16,
        list(kv_weights.shape),
        key="view.kv_weights",
    )
    gate_view = w.const_view(
        _storage_payload(gate_weights, DType.BF16),
        DType.BF16,
        list(gate_weights.shape),
        key="view.gate_weights",
    )
    output_view = w.scratch_view(
        DType.FP32, [batch, span, 2, cols], key="view.out"
    )
    numeric = w.builder.numeric(
        contract="deepseek_v4_compress_project_binary32_v1",
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        reduction_order=ReductionOrder.SEQUENTIAL_ASCENDING,
        key="num.compress_project",
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.COMPRESS),
        inputs=[hidden_view, kv_view, gate_view],
        outputs=[output_view],
        aux=[0, NO_ID, NO_ID, NO_ID],
        numeric_profile_id=numeric,
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.compress_project",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.COMPRESS), operator)
    rows = int(batch * span)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.COMPRESS),
        deployment=deployment,
        root=root,
        operand0_view=hidden_view,
        operand1_view=kv_view,
        operand2_view=gate_view,
        output_view=output_view,
        output_dtype=int(DType.FP32),
        rows=rows,
        cols=int(cols),
        depth=int(depth),
        count=rows * 2 * int(cols),
        block_a=0,
        expect_fault=expect_fault,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "COMPRESS_PROJECT",
            "cfg_block_a": "aux_id_0",
            "aux_id_0": 0,
            "cfg_rows": "flattened_batch_times_span",
            "cfg_scale_a_base": "operand2_gate_weights_base",
            "projection_order": "kv_then_gate",
        },
    )


def vector_mhc_post_case(
    name: str,
    note: str,
    capability: Capability,
    root: Path,
    *,
    branch: np.ndarray,
    residual: np.ndarray,
    post: np.ndarray,
    combination: np.ndarray,
    expect_fault: bool = False,
) -> Case:
    w = Workspace(name, capability, root)
    batch, span, hidden = branch.shape
    multiplier = int(residual.shape[2])
    branch_view = w.const_view(
        _storage_payload(branch, DType.BF16),
        DType.BF16,
        list(branch.shape),
        key="view.branch",
    )
    residual_view = w.const_view(
        _storage_payload(residual, DType.BF16),
        DType.BF16,
        list(residual.shape),
        key="view.residual",
    )
    post_view = w.const_view(
        _storage_payload(post, DType.FP32),
        DType.FP32,
        list(post.shape),
        key="view.post",
    )
    combination_view = w.const_view(
        _storage_payload(combination, DType.FP32),
        DType.FP32,
        list(combination.shape),
        key="view.combination",
    )
    output_view = w.scratch_view(
        DType.BF16, list(residual.shape), key="view.out"
    )
    operator = w.operator(
        engine_family=Major.VECTOR,
        engine_sub=int(Vector.MHC),
        inputs=[branch_view, residual_view, post_view, combination_view],
        outputs=[output_view],
        aux=[1, NO_ID, multiplier, NO_ID],
        counter_class_id=w.counters(CounterGroup.VECTOR_REDUCTION, "ctr.vector"),
        source_kernel_id=0,
        key="op.mhc_post",
    )
    deployment = build_program(w, Major.VECTOR, int(Vector.MHC), operator)
    sites = int(batch * span)
    return Case(
        name=name,
        note=note,
        family=int(Major.VECTOR),
        sub=int(Vector.MHC),
        deployment=deployment,
        root=root,
        operand0_view=branch_view,
        operand1_view=residual_view,
        operand2_view=post_view,
        operand3_view=combination_view,
        output_view=output_view,
        output_dtype=int(DType.BF16),
        rows=sites,
        cols=int(hidden),
        count=int(residual.size),
        slots=multiplier,
        block_a=1,
        block_b=multiplier,
        expect_fault=expect_fault,
        counter_names=("vector.elements", "vector.saturations"),
        rtl_config={
            "covered_form": "HYPER_CONNECT_POST",
            "cfg_block_a": "aux_id_0",
            "aux_id_0": 1,
            "cfg_block_b": "aux_id_2",
            "aux_id_2": multiplier,
            "cfg_slots": "multiplier",
            "cfg_scale_a_base": "operand2_post_base",
            "cfg_scale_b_base": "operand3_combination_base",
            "combination_order": "source_then_destination",
        },
    )


def _rtl_negative_cases(positive: dict[str, Case]) -> list[Case]:
    """Descriptor-corruption matrix for every bounded VECTOR admission rule."""
    specs: list[tuple[str, str, str, dict[str, Any]]] = [
        # CONVERT: arity, scaling, shape identity, output dtype and bound.
        ("convert_extra_input", "convert", "second input is forbidden",
         {"input_valid": 0b0011}),
        ("convert_extra_output", "convert", "second output is forbidden",
         {"output_valid": 0b11}),
        ("convert_scaled_source", "convert", "source must be unscaled",
         {"input0_scaled": 1}),
        ("convert_scaled_output", "convert", "output must be unscaled",
         {"output0_scaled": 1}),
        ("convert_same_count_different_shape", "convert",
         "equal element counts do not prove equal shapes",
         {"output0_dims": (2, 3, 0, 0)}),
        ("convert_wrong_output_dtype", "convert", "output dtype is checked",
         {"output0_dtype": int(DType.BF16)}),
        ("convert_profile_mismatch", "convert", "profile dtype is checked",
         {"profile_output_dtype": int(DType.BF16)}),
        ("convert_non_rne", "convert", "rounding mode is checked",
         {"rounding_mode": 1}),
        ("convert_wrong_contract", "convert", "contract digest is checked",
         {"contract_digest": bytes(32)}),
        # SCALE: exact arity and complete shape/profile correlation.
        ("scale_constant_extra_operand", "scale_constant",
         "constant scale has one input", {"input_valid": 0b0011}),
        ("scale_elementwise_missing_operand", "scale_elementwise",
         "elementwise scale requires input 1", {"input_valid": 0b0001}),
        ("scale_trailing_broadcast", "scale_elementwise",
         "bounded RTL excludes trailing broadcast",
         {"input1_rank": 1, "input1_dims": (8, 0, 0, 0)}),
        ("scale_same_count_different_factor_shape", "scale_elementwise",
         "same count is not the same full shape",
         {"input1_dims": (8, 3, 0, 0)}),
        ("scale_wrong_output_dtype", "scale_constant", "output dtype is checked",
         {"output0_dtype": int(DType.FP32)}),
        ("scale_profile_input_mismatch", "scale_constant",
         "numeric input dtype is checked", {"profile_input_dtype": int(DType.FP32)}),
        ("scale_profile_second_mismatch", "scale_elementwise",
         "numeric second dtype is checked",
         {"profile_second_dtype": int(DType.FP32)}),
        ("scale_profile_output_mismatch", "scale_constant",
         "numeric output dtype is checked",
         {"profile_output_dtype": int(DType.FP32)}),
        ("scale_profile_accumulator_mismatch", "scale_constant",
         "numeric accumulator dtype is checked",
         {"profile_accumulator_dtype": int(DType.BF16)}),
        ("scale_profile_saturate", "scale_constant",
         "numeric saturate control is checked", {"profile_saturate": 1}),
        ("scale_profile_nan_policy", "scale_constant",
         "numeric NaN policy is checked", {"profile_nan_policy": 1}),
        ("scale_profile_epsilon", "scale_constant",
         "numeric epsilon is checked", {"profile_epsilon_bits": 1}),
        ("scale_profile_flags", "scale_constant",
         "numeric flags are checked", {"profile_flags": 1}),
        ("scale_non_rne", "scale_constant", "rounding mode is checked",
         {"rounding_mode": 1}),
        ("scale_wrong_contract", "scale_constant", "contract digest is checked",
         {"contract_digest": bytes(32)}),
        # HADAMARD: dtype/profile/rank/bounds.
        ("hadamard_wrong_output_dtype", "hadamard", "output dtype is checked",
         {"output0_dtype": int(DType.FP32)}),
        ("hadamard_profile_mismatch", "hadamard", "profile dtype is checked",
         {"profile_output_dtype": int(DType.FP32)}),
        ("hadamard_non_rne", "hadamard", "rounding mode is checked",
         {"rounding_mode": 1}),
        ("hadamard_rank_mismatch", "hadamard", "output rank is checked",
         {"output0_rank": 1, "output0_dims": (128, 0, 0, 0)}),
        ("hadamard_wrong_contract", "hadamard", "contract digest is checked",
         {"contract_digest": bytes(32)}),
        # INDEX: all operand dtypes, output, batch/head/scale/rank/relations.
        ("index_wrong_operand2_dtype", "index", "head-weight dtype is checked",
         {"input2_dtype": int(DType.FP32)}),
        ("index_wrong_output_dtype", "index", "output dtype is checked",
         {"output0_dtype": int(DType.FP32)}),
        ("index_profile_mismatch", "index", "profile dtype is checked",
         {"profile_input_dtype": int(DType.FP32)}),
        ("index_non_rne", "index", "rounding mode is checked",
         {"rounding_mode": 1}),
        ("index_non_unit_scale", "index", "scale one is checked",
         {"profile_scale_bits": 0x3F000000}),
        ("index_batch_two_flattened_rows", "index",
         "batch two cannot hide in a legal flattened row count",
         {"input0_dims": (2, 1, 4, 2), "input1_dims": (2, 1, 2, 0),
          "input2_dims": (2, 1, 4, 0), "output0_dims": (2, 1, 1, 0)}),
        ("index_wrong_head_count", "index", "four heads are required",
         {"input0_dims": (1, 1, 3, 2), "input2_dims": (1, 1, 3, 0)}),
        ("index_rank_mismatch", "index", "query rank is checked",
         {"input0_rank": 3, "input0_dims": (1, 4, 2, 0)}),
        ("index_key_shape_mismatch", "index", "key depth relation is checked",
         {"input1_dims": (1, 1, 3, 0)}),
        ("index_wrong_contract", "index", "contract digest is checked",
         {"contract_digest": bytes(32)}),
        # COMPRESS: operand/output dtype, profile/order, aux and projections.
        ("compress_wrong_operand2_dtype", "compress", "gate dtype is checked",
         {"input2_dtype": int(DType.FP32)}),
        ("compress_wrong_output_dtype", "compress", "output dtype is checked",
         {"output0_dtype": int(DType.BF16)}),
        ("compress_profile_mismatch", "compress", "profile dtype is checked",
         {"profile_output_dtype": int(DType.BF16)}),
        ("compress_non_rne", "compress", "rounding mode is checked",
         {"rounding_mode": 1}),
        ("compress_nonsequential", "compress", "reduction order is checked",
         {"reduction_order": 1}),
        ("compress_aux1", "compress", "aux1 must be absent",
         {"aux_valid": 0b0011, "aux1": 4}),
        ("compress_aux2", "compress", "aux2 must be absent",
         {"aux_valid": 0b0101, "aux2": 4}),
        ("compress_projection_shape", "compress",
         "projection depths must match hidden", {"input2_dims": (2, 3, 0, 0)}),
        ("compress_wrong_contract", "compress", "contract digest is checked",
         {"contract_digest": bytes(32)}),
        # MHC_POST: operand/output dtypes, aux/multiplier, ranks and relations.
        ("mhc_wrong_operand2_dtype", "mhc", "post dtype is checked",
         {"input2_dtype": int(DType.BF16)}),
        ("mhc_wrong_operand3_dtype", "mhc", "combination dtype is checked",
         {"input3_dtype": int(DType.BF16)}),
        ("mhc_wrong_output_dtype", "mhc", "output dtype is checked",
         {"output0_dtype": int(DType.FP32)}),
        ("mhc_wrong_aux0", "mhc", "POST selector is checked", {"aux0": 0}),
        ("mhc_missing_aux2", "mhc", "multiplier aux is required",
         {"aux_valid": 0b0001, "aux2": NO_ID}),
        ("mhc_wrong_multiplier", "mhc", "multiplier four is checked",
         {"aux2": 3}),
        ("mhc_rank_mismatch", "mhc", "residual rank is checked",
         {"input1_rank": 3, "input1_dims": (1, 1, 20, 0)}),
        ("mhc_shape_mismatch", "mhc", "post shape relation is checked",
         {"input2_dims": (1, 1, 3, 0)}),
        ("mhc_wrong_contract", "mhc", "contract digest is checked",
         {"contract_digest": bytes(32)}),
    ]
    cases: list[Case] = []
    for suffix, base_name, note, overrides in specs:
        base = positive[base_name]
        cases.append(dc_replace(
            base,
            name=f"vector_descriptor_refusal_{suffix}",
            note=f"fail-closed descriptor admission: {note}",
            rtl_expected_fault_code=ERR_SHAPE,
            rtl_descriptor_overrides=overrides,
        ))
    return cases


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

    # -- VECTOR.CONVERT, unscaled one-input/one-output ------------------
    cases.append(vector_convert_case(
        "vector_convert_bf16_to_fp32",
        "exact BF16 widening, including both signed-zero encodings and a "
        "subnormal; storage conversion must not inherit the arithmetic "
        "decoder's positive-zero canonicalisation",
        capability,
        root,
        source=np.array(
            [[0x3F80, 0xBF80, 0x0000, 0x8000, 0x3F81, 0x0001]],
            dtype=np.uint16,
        ),
        input_dtype=DType.BF16,
        output_dtype=DType.FP32,
        contract="bf16_to_fp32_exact_v1",
    ))
    cases.append(vector_convert_case(
        "vector_convert_fp32_to_bf16_rounding",
        "binary32-to-BF16 ties-to-even, ordinary rounding and a finite value "
        "that saturates at the BF16 storage boundary",
        capability,
        root,
        source=np.array(
            [[0x3F808000, 0x3F818000, 0xBF808001, 0x7F7F8000]],
            dtype=np.uint32,
        ),
        input_dtype=DType.FP32,
        output_dtype=DType.BF16,
        contract="fp32_to_bf16_rne_v1",
    ))
    cases.append(vector_convert_case(
        "vector_convert_fp8_to_bf16",
        "E4M3FN codes widen through the exhaustive format decoder and cross "
        "one BF16 boundary",
        capability,
        root,
        source=np.array([[0x00, 0x01, 0x38, 0x40, 0x7E, 0xB8]], dtype=np.uint8),
        input_dtype=DType.FP8_E4M3FN,
        output_dtype=DType.BF16,
        contract="fp8_e4m3fn_to_bf16_rne_v1",
    ))
    convert_poison = np.array(
        [[0x3F800000, 0x40000000, 0xBF000000, 0x7F800000]], dtype=np.uint32
    )
    cases.append(vector_convert_case(
        "vector_convert_late_nonfinite",
        "the final binary32 source is infinity: the complete preflight must "
        "leave every earlier destination word untouched",
        capability,
        root,
        source=convert_poison,
        input_dtype=DType.FP32,
        output_dtype=DType.BF16,
        contract="fp32_to_bf16_rne_v1",
        expect_fault=True,
    ))
    # The general Device legitimately supports this view, while the bounded
    # RTL profile is explicitly 1..512.  Keep the Device execution successful
    # and require the RTL's independent MAX_ELEMENTS gate to refuse it.
    cases.append(vector_convert_case(
        "vector_convert_count_513_refused_by_rtl",
        "one element beyond the bounded RTL profile is refused before any "
        "destination word is written",
        capability,
        root,
        source=np.arange(513, dtype=np.uint32).reshape(3, 171),
        input_dtype=DType.U32,
        output_dtype=DType.U32,
        contract="identity_storage_v1",
        rtl_expected_fault_code=ERR_SHAPE,
    ))

    # -- VECTOR.SCALE, constant and same-shape elementwise --------------
    cases.append(vector_scale_case(
        "vector_scale_constant_eighth",
        "BF16 values multiplied by the profile's exact binary32 0.125 "
        "constant, with one binary32 product and one BF16 rounding",
        capability,
        root,
        source=random_bf16(rng, (3, 9), scale=2.0),
        scale_bits=0x3E000000,
    ))
    cases.append(vector_scale_case(
        "vector_scale_constant_zero",
        "a zero scale remains the constant-scale sub-case because aux0, not "
        "scale_bits, selects the operation",
        capability,
        root,
        source=random_bf16(rng, (2, 7), scale=3.0),
        scale_bits=0,
    ))
    cases.append(vector_scale_case(
        "vector_scale_elementwise",
        "same-shape BF16 factors exercise signed products, cancellation and "
        "the elementwise aux0 selector",
        capability,
        root,
        source=random_bf16(rng, (3, 8), scale=2.0),
        factors=random_bf16(rng, (3, 8), scale=0.75),
    ))
    cases.append(vector_scale_case(
        "vector_scale_saturating",
        "finite binary32 products beyond the BF16 range saturate and are "
        "counted instead of being mistaken for arithmetic overflow",
        capability,
        root,
        source=np.array([[0x7F7F, 0xFF7F, 0x3F80, 0xBF80]], dtype=np.uint16),
        scale_bits=0x3F804040,
    ))
    scale_poison = random_bf16(rng, (2, 8))
    scale_poison[-1, -1] = 0x7F80
    cases.append(vector_scale_case(
        "vector_scale_late_nonfinite",
        "a BF16 infinity in the final source position proves that buffered "
        "SCALE does not commit its valid prefix",
        capability,
        root,
        source=scale_poison,
        scale_bits=0x3F000000,
        expect_fault=True,
    ))
    cases.append(vector_scale_case(
        "vector_scale_late_nonfinite_after_saturation",
        "the first finite result saturates but the final source is infinity; "
        "the refusal exposes neither writes nor the speculative saturation",
        capability,
        root,
        source=np.array([[0x7F7F, 0x3F80, 0x7F80]], dtype=np.uint16),
        scale_bits=0x3F808000,
        expect_fault=True,
    ))

    # -- VECTOR.HADAMARD, qualified 128-point transform -----------------
    cases.append(vector_hadamard_case(
        "vector_hadamard_random_rows",
        "two seeded 128-wide BF16 rows cover every ascending-stride "
        "butterfly stage and the exact 1/sqrt(128) normalisation",
        capability,
        root,
        source=random_bf16(rng, (2, 128), scale=0.5),
    ))
    hadamard_directed = np.zeros((1, 128), dtype=np.uint16)
    hadamard_directed[0, :8] = np.array(
        [0x3F80, 0xBF80, 0x4000, 0xC000, 0x4080, 0xBF00, 0x3E80, 0x8000],
        dtype=np.uint16,
    )
    cases.append(vector_hadamard_case(
        "vector_hadamard_directed",
        "an impulse-and-cancellation row makes butterfly signs, zero "
        "canonicalisation and the normalisation constant independently visible",
        capability,
        root,
        source=hadamard_directed,
    ))
    cases.append(vector_hadamard_case(
        "vector_hadamard_wrong_width",
        "a 64-point row is not silently treated as half a qualified transform",
        capability,
        root,
        source=random_bf16(rng, (1, 64), scale=0.5),
        expect_fault=True,
    ))
    hadamard_poison = random_bf16(rng, (2, 128), scale=0.5)
    hadamard_poison[-1, -1] = 0x7FC0
    cases.append(vector_hadamard_case(
        "vector_hadamard_late_nonfinite",
        "a NaN in the final element is found during the load preflight before "
        "any transformed row is committed",
        capability,
        root,
        source=hadamard_poison,
        expect_fault=True,
    ))
    cases.append(vector_hadamard_case(
        "vector_hadamard_five_rows_refused_by_rtl",
        "one row above the bounded four-row profile is refused",
        capability,
        root,
        source=random_bf16(rng, (5, 128), scale=0.25),
        rtl_expected_fault_code=ERR_SHAPE,
    ))

    # -- VECTOR.INDEX_SCORE, batch one / four heads / scale one ----------
    cases.append(vector_index_score_case(
        "vector_index_score_seeded",
        "the functional-test shape: two sites, four heads, five candidates "
        "and eight head channels, with every intermediate BF16 boundary",
        capability,
        root,
        query=random_bf16(rng, (1, 2, 4, 8), scale=1.5),
        keys=random_bf16(rng, (1, 5, 8), scale=1.25),
        weights=random_bf16(rng, (1, 2, 4), scale=2.0),
    ))
    directed_query = np.zeros((1, 1, 4, 4), dtype=np.uint16)
    directed_query[0, 0, :, 0] = np.array(
        [0x3F80, 0xBF80, 0x4000, 0xC000], dtype=np.uint16
    )
    directed_keys = np.zeros((1, 3, 4), dtype=np.uint16)
    directed_keys[0, :, 0] = np.array([0x3F80, 0xBF80, 0x4000], dtype=np.uint16)
    directed_weights = np.array(
        [[[0x3F80, 0xC000, 0x4000, 0xBF00]]], dtype=np.uint16
    )
    cases.append(vector_index_score_case(
        "vector_index_score_relu_tree",
        "directed positive and negative head dots expose the post-rounding "
        "ReLU and the balanced four-head reduction",
        capability,
        root,
        query=directed_query,
        keys=directed_keys,
        weights=directed_weights,
    ))
    fused_index_query = np.zeros((1, 1, 4, 2), dtype=np.uint16)
    fused_index_query[0, 0, 0] = np.array([0x2A7E, 0x1B83], dtype=np.uint16)
    fused_index_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    fused_index_weights[0, 0, 0] = 0x3F80
    cases.append(vector_index_score_case(
        "vector_index_score_exact_product_add",
        "the low exact-product bits of the second depth step round the head "
        "dot to 0x02be8001 and therefore BF16 0x02bf; a multiply-then-add "
        "implementation instead produces BF16 0x02be",
        capability,
        root,
        query=fused_index_query,
        keys=np.array([[[0x17C0, 0x1A83]]], dtype=np.uint16),
        weights=fused_index_weights,
    ))
    index_weighted_sat_query = np.zeros((1, 1, 4, 1), dtype=np.uint16)
    index_weighted_sat_query[0, 0, 0, 0] = 0x7F7E
    index_weighted_sat_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    index_weighted_sat_weights[0, 0, 0] = 0x3F81
    cases.append(vector_index_score_case(
        "vector_index_score_weighted_saturation",
        "a finite weighted head score crosses the BF16 boundary and must "
        "increment the architectural vector.saturations event",
        capability,
        root,
        query=index_weighted_sat_query,
        keys=np.array([[[0x3F80]]], dtype=np.uint16),
        weights=index_weighted_sat_weights,
    ))
    index_qk_sat_query = np.zeros((1, 1, 4, 2), dtype=np.uint16)
    index_qk_sat_query[0, 0, 0] = np.array([0x7F7F, 0x7B00], dtype=np.uint16)
    index_qk_sat_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    index_qk_sat_weights[0, 0, 0] = 0x3F80
    cases.append(vector_index_score_case(
        "vector_index_score_qk_saturation",
        "the ordered QK dot remains finite but its BF16 boundary saturates "
        "and increments vector.saturations",
        capability,
        root,
        query=index_qk_sat_query,
        keys=np.array([[[0x3F80, 0x3F80]]], dtype=np.uint16),
        weights=index_qk_sat_weights,
    ))
    index_output_sat_query = np.zeros((1, 1, 4, 1), dtype=np.uint16)
    index_output_sat_query[0, 0, 0, 0] = 0x7F7F
    index_output_sat_query[0, 0, 1, 0] = 0x7B00
    index_output_sat_weights = np.zeros((1, 1, 4), dtype=np.uint16)
    index_output_sat_weights[0, 0, :2] = 0x3F80
    cases.append(vector_index_score_case(
        "vector_index_score_output_saturation",
        "the balanced head sum remains binary32-finite but the final BF16 "
        "output boundary saturates and increments vector.saturations",
        capability,
        root,
        query=index_output_sat_query,
        keys=np.array([[[0x3F80]]], dtype=np.uint16),
        weights=index_output_sat_weights,
    ))
    index_query = random_bf16(rng, (1, 2, 4, 8))
    index_keys = random_bf16(rng, (1, 5, 8))
    index_keys[-1, -1, -1] = 0x7F80
    cases.append(vector_index_score_case(
        "vector_index_score_late_nonfinite",
        "the last key channel is infinity; the three-operand preflight leaves "
        "all site/candidate scores untouched",
        capability,
        root,
        query=index_query,
        keys=index_keys,
        weights=random_bf16(rng, (1, 2, 4)),
        expect_fault=True,
    ))

    # -- VECTOR.COMPRESS / COMPRESS_PROJECT -----------------------------
    cases.append(vector_compress_project_case(
        "vector_compress_project_seeded",
        "three hidden rows project into distinct KV and gate planes under "
        "strictly ascending reduction order",
        capability,
        root,
        hidden=random_bf16(rng, (1, 3, 8), scale=1.5),
        kv_weights=random_bf16(rng, (5, 8), scale=0.75),
        gate_weights=random_bf16(rng, (5, 8), scale=1.25),
    ))
    compress_hidden = np.array(
        [[[0x3F80, 0x4F00, 0x4F00, 0x4000]]], dtype=np.uint16
    )
    compress_kv = np.array(
        [[0x3F80, 0x4F00, 0xCF00, 0x0000],
         [0x4000, 0x3F80, 0xBF80, 0x3F00]],
        dtype=np.uint16,
    )
    compress_gate = np.array(
        [[0xBF80, 0x3F00, 0x3F00, 0x4000],
         [0x4040, 0xBF80, 0x3F80, 0xBF00]],
        dtype=np.uint16,
    )
    cases.append(vector_compress_project_case(
        "vector_compress_project_order",
        "catastrophic cancellation makes ascending reduction visible while "
        "deliberately different matrices make KV-then-gate plane order visible",
        capability,
        root,
        hidden=compress_hidden,
        kv_weights=compress_kv,
        gate_weights=compress_gate,
    ))
    cases.append(vector_compress_project_case(
        "vector_compress_project_exact_product_add",
        "a depth-two projection whose exact-product single-rounded result is "
        "0x0131b843; rounding the second product before adding produces the "
        "adjacent but incorrect 0x0131b842",
        capability,
        root,
        hidden=np.array([[[0xBFED, 0x8483]]], dtype=np.uint16),
        kv_weights=np.array([[0x80C0, 0x35F2]], dtype=np.uint16),
        gate_weights=np.zeros((1, 2), dtype=np.uint16),
    ))
    compress_gate_poison = random_bf16(rng, (4, 8))
    compress_gate_poison[-1, -1] = 0x7FC0
    cases.append(vector_compress_project_case(
        "vector_compress_project_late_nonfinite",
        "a NaN in the final gate-weight element is rejected before either "
        "projection plane is committed",
        capability,
        root,
        hidden=random_bf16(rng, (1, 2, 8)),
        kv_weights=random_bf16(rng, (4, 8)),
        gate_weights=compress_gate_poison,
        expect_fault=True,
    ))

    # -- VECTOR.MHC / HYPER_CONNECT_POST --------------------------------
    mhc_branch = random_bf16(rng, (1, 2, 6), scale=1.25)
    mhc_residual = random_bf16(rng, (1, 2, 4, 6), scale=1.5)
    mhc_post = rng.uniform(0.0, 2.0, size=(1, 2, 4)).astype(np.float32)
    mhc_combination = rng.uniform(-1.0, 1.0, size=(1, 2, 4, 4)).astype(np.float32)
    cases.append(vector_mhc_post_case(
        "vector_mhc_post_seeded",
        "two sites and four streams exercise the branch product, every "
        "combination coefficient and the balanced residual tree",
        capability,
        root,
        branch=mhc_branch,
        residual=mhc_residual,
        post=mhc_post,
        combination=mhc_combination,
    ))
    directed_combination = np.array(
        [[[[1.0, 2.0, 3.0, 4.0],
           [-0.5, 0.25, 1.5, -2.0],
           [0.75, -1.25, 0.5, 2.5],
           [3.0, 0.125, -0.75, 1.25]]]],
        dtype=np.float32,
    )
    cases.append(vector_mhc_post_case(
        "vector_mhc_post_matrix_order",
        "a nonsymmetric combination matrix distinguishes architectural "
        "comb[source][destination] addressing from its transpose",
        capability,
        root,
        branch=random_bf16(rng, (1, 1, 5)),
        residual=random_bf16(rng, (1, 1, 4, 5), scale=1.25),
        post=np.array([[[0.25, 0.5, 0.75, 1.0]]], dtype=np.float32),
        combination=directed_combination,
    ))
    cases.append(vector_mhc_post_case(
        "vector_mhc_post_output_saturation",
        "one finite post-scaled branch crosses the BF16 output boundary; the "
        "output saturates to 0x7f7f and vector.saturations increments once",
        capability,
        root,
        branch=np.array([[[0x7F7F]]], dtype=np.uint16),
        residual=np.zeros((1, 1, 4, 1), dtype=np.uint16),
        post=np.array(
            [[[0x3F808000, 0x00000000, 0x00000000, 0x00000000]]],
            dtype=np.uint32,
        ),
        combination=np.zeros((1, 1, 4, 4), dtype=np.uint32),
    ))
    mhc_combination_poison = rng.uniform(
        -1.0, 1.0, size=(1, 2, 4, 4)
    ).astype(np.float32)
    mhc_combination_poison[-1, -1, -1, -1] = np.nan
    cases.append(vector_mhc_post_case(
        "vector_mhc_post_late_nonfinite",
        "the last combination coefficient is NaN; four-operand preflight "
        "must preserve the entire residual-shaped destination",
        capability,
        root,
        branch=random_bf16(rng, (1, 2, 6)),
        residual=random_bf16(rng, (1, 2, 4, 6)),
        post=rng.uniform(0.0, 1.0, size=(1, 2, 4)).astype(np.float32),
        combination=mhc_combination_poison,
        expect_fault=True,
    ))

    # One-above-bound cases use otherwise valid descriptors and operands.  The
    # general Device can execute them; only the explicitly bounded RTL profile
    # must refuse them, before reading or writing anything.
    cases.append(dc_replace(vector_scale_case(
        "vector_scale_count_513_refused_by_rtl",
        "one element above SCALE's bounded element count",
        capability,
        root,
        source=random_bf16(rng, (513,), scale=0.25),
        scale_bits=0x3F800000,
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_index_score_case(
        "vector_index_score_span_5_refused_by_rtl",
        "one site above INDEX_SCORE's bounded site count",
        capability,
        root,
        query=random_bf16(rng, (1, 5, 4, 2), scale=0.25),
        keys=random_bf16(rng, (1, 1, 2), scale=0.25),
        weights=random_bf16(rng, (1, 5, 4), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_index_score_case(
        "vector_index_score_candidates_9_refused_by_rtl",
        "one candidate above INDEX_SCORE's bounded candidate count",
        capability,
        root,
        query=random_bf16(rng, (1, 1, 4, 2), scale=0.25),
        keys=random_bf16(rng, (1, 9, 2), scale=0.25),
        weights=random_bf16(rng, (1, 1, 4), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_index_score_case(
        "vector_index_score_depth_17_refused_by_rtl",
        "one channel above INDEX_SCORE's bounded reduction depth",
        capability,
        root,
        query=random_bf16(rng, (1, 1, 4, 17), scale=0.25),
        keys=random_bf16(rng, (1, 1, 17), scale=0.25),
        weights=random_bf16(rng, (1, 1, 4), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_compress_project_case(
        "vector_compress_project_rows_9_refused_by_rtl",
        "one flattened row above COMPRESS_PROJECT's bound",
        capability,
        root,
        hidden=random_bf16(rng, (1, 9, 2), scale=0.25),
        kv_weights=random_bf16(rng, (1, 2), scale=0.25),
        gate_weights=random_bf16(rng, (1, 2), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_compress_project_case(
        "vector_compress_project_cols_17_refused_by_rtl",
        "one output feature above COMPRESS_PROJECT's bound",
        capability,
        root,
        hidden=random_bf16(rng, (1, 1, 2), scale=0.25),
        kv_weights=random_bf16(rng, (17, 2), scale=0.25),
        gate_weights=random_bf16(rng, (17, 2), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_compress_project_case(
        "vector_compress_project_depth_65_refused_by_rtl",
        "one reduction channel above COMPRESS_PROJECT's bound",
        capability,
        root,
        hidden=random_bf16(rng, (1, 1, 65), scale=0.25),
        kv_weights=random_bf16(rng, (1, 65), scale=0.25),
        gate_weights=random_bf16(rng, (1, 65), scale=0.25),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_mhc_post_case(
        "vector_mhc_post_sites_5_refused_by_rtl",
        "one flattened site above HYPER_CONNECT_POST's bound",
        capability,
        root,
        branch=random_bf16(rng, (1, 5, 1), scale=0.25),
        residual=random_bf16(rng, (1, 5, 4, 1), scale=0.25),
        post=np.ones((1, 5, 4), dtype=np.float32),
        combination=np.zeros((1, 5, 4, 4), dtype=np.float32),
    ), rtl_expected_fault_code=ERR_SHAPE))
    cases.append(dc_replace(vector_mhc_post_case(
        "vector_mhc_post_hidden_33_refused_by_rtl",
        "one hidden channel above HYPER_CONNECT_POST's bound",
        capability,
        root,
        branch=random_bf16(rng, (1, 1, 33), scale=0.25),
        residual=random_bf16(rng, (1, 1, 4, 33), scale=0.25),
        post=np.ones((1, 1, 4), dtype=np.float32),
        combination=np.zeros((1, 1, 4, 4), dtype=np.float32),
    ), rtl_expected_fault_code=ERR_SHAPE))
    positive = {
        "convert": next(
            case for case in cases if case.name == "vector_convert_bf16_to_fp32"
        ),
        "scale_constant": next(
            case for case in cases if case.name == "vector_scale_constant_eighth"
        ),
        "scale_elementwise": next(
            case for case in cases if case.name == "vector_scale_elementwise"
        ),
        "hadamard": next(
            case for case in cases if case.name == "vector_hadamard_directed"
        ),
        "index": next(
            case for case in cases if case.name == "vector_index_score_relu_tree"
        ),
        "compress": next(
            case for case in cases if case.name == "vector_compress_project_order"
        ),
        "mhc": next(
            case for case in cases if case.name == "vector_mhc_post_matrix_order"
        ),
    }
    for label, base in positive.items():
        cases.append(dc_replace(
            base,
            name=f"vector_descriptor_refusal_{label}_inconsistent_count",
            note=(
                "fail-closed descriptor admission: cfg_count disagrees with "
                "the independently resolved output shape"
            ),
            count=base.count + 1,
            rtl_expected_fault_code=ERR_SHAPE,
        ))
    cases.extend(_rtl_negative_cases(positive))
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
        "operand2": read(case.operand2_view),
        "operand3": read(case.operand3_view),
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

# Exact halfway cases found by a deterministic rational search.  They are
# fixed here so the primitive's tie-to-even decision remains directly visible
# even if the surrounding random distribution changes.
PRODUCT_ADD_TIES: tuple[tuple[int, int, int], ...] = (
    (0x90F0CD7E, 0x837D, 0xCDF9),
    (0x3BE9002E, 0x3872, 0xBD91),
    (0x288142A9, 0x2D53, 0xB61D),
    (0xAB4C8472, 0x0C63, 0x5985),
    (0x13141ACA, 0x900C, 0x43A9),
    (0x16473E71, 0x182A, 0x3811),
    (0xCA183697, 0xD02F, 0xB44A),
    (0x7081A22A, 0xB9FF, 0x7146),
)


def product_add_probe_inputs() -> list[tuple[int, int, int]]:
    """Stratified and deterministic-random finite ordered-dot steps.

    The tuples are ``(binary32 accumulator, BF16 lhs, BF16 rhs)``.  They cover
    both signs of zero, exact cancellation, BF16 and binary32 subnormal/normal
    boundaries, exact halfway results, finite overflow, and a broad seeded
    sample over every finite exponent band.  No host floating operation is
    used to construct or judge an expected result.
    """
    entries: list[tuple[int, int, int]] = [
        # The two observed split-rounding failures, at their second step.
        (0x0131C000, 0x8483, 0x35F2),
        (0x02BE8000, 0x1B83, 0x1A83),
        # Signed-zero products and accumulators all canonicalise to +0.
        (0x00000000, 0x0000, 0x3F80),
        (0x80000000, 0x8000, 0xBF80),
        (0x80000000, 0x0000, 0xFF7F),
        # Exact signed cancellations.
        (0x3F800000, 0xBF80, 0x3F80),
        (0xBF800000, 0x3F80, 0x3F80),
        (0xC0400000, 0x3FC0, 0x4000),
        # Direct underflow and both finite-overflow signs.
        (0x00000000, 0x0001, 0x0001),
        (0x7F7FFFFF, 0x7F7F, 0x7F7F),
        (0xFF7FFFFF, 0xFF7F, 0x7F7F),
        *PRODUCT_ADD_TIES,
    ]
    bf16_strata = (
        0x0000, 0x8000, 0x0001, 0x8001, 0x007F, 0x807F,
        0x0080, 0x8080, 0x0081, 0x8081, 0x3E80, 0xBE80,
        0x3F00, 0xBF00, 0x3F7F, 0xBF7F, 0x3F80, 0xBF80,
        0x3F81, 0xBF81, 0x4000, 0xC000, 0x7F7F, 0xFF7F,
    )
    accumulator_strata = tuple(
        code for code in ARITH_CORNERS
        if ((code >> 23) & 0xFF) != 0xFF
    )
    for left_index, lhs in enumerate(bf16_strata):
        for right_index, rhs in enumerate(bf16_strata):
            selector = left_index * len(bf16_strata) + right_index
            entries.extend((
                (0, lhs, rhs),
                (accumulator_strata[selector % len(accumulator_strata)], lhs, rhs),
                (accumulator_strata[
                    (selector * 17 + 5) % len(accumulator_strata)
                ], lhs, rhs),
            ))

    # Add exact cancellations for representative normal BF16 products.  Only
    # products exactly representable in binary32 qualify, checked rationally.
    for lhs, rhs in (
        (0x3F80, 0x4000), (0xBF80, 0x4040), (0x3FC0, 0xBF00),
        (0x4120, 0x3D80), (0x0080, 0x3F80), (0x8080, 0xBF80),
    ):
        left_value = exact_formats.decode_bf16(lhs).value
        right_value = exact_formats.decode_bf16(rhs).value
        assert left_value is not None and right_value is not None
        exact_accumulator = -(left_value * right_value)
        accumulator = exact_formats.encode_binary32_rne(exact_accumulator)
        decoded = exact_formats.decode_binary32(accumulator).value
        if decoded != exact_accumulator:
            raise RuntimeError("product-add cancellation vector is not exact")
        entries.append((accumulator, lhs, rhs))

    # Deterministic random coverage across all *finite* exponent fields.
    rng = np.random.default_rng(0xA383F00D)
    while len(entries) < 5200:
        accumulator = (
            (int(rng.integers(0, 2)) << 31)
            | (int(rng.integers(0, 255)) << 23)
            | int(rng.integers(0, 1 << 23))
        )
        lhs = (
            (int(rng.integers(0, 2)) << 15)
            | (int(rng.integers(0, 255)) << 7)
            | int(rng.integers(0, 1 << 7))
        )
        rhs = (
            (int(rng.integers(0, 2)) << 15)
            | (int(rng.integers(0, 255)) << 7)
            | int(rng.integers(0, 1 << 7))
        )
        entries.append((accumulator, lhs, rhs))
    return entries


def product_add_probe_entries() -> list[tuple[int, int, int, int, int]]:
    """Return primitive inputs followed by exact error class and result."""
    return [
        (accumulator, lhs, rhs, *(_exact_product_add(accumulator, lhs, rhs)))
        for accumulator, lhs, rhs in product_add_probe_inputs()
    ]


def arith_probe_entries() -> list[tuple[int, ...]]:
    """Binary32 operations plus exact BF16-product accumulator steps.

    Each entry is ``(a, b, add_err, add, mul_err, mul, bf16_err_sat,
    bf16, accumulator, lhs_bf16 | rhs_bf16<<16, product_add_err,
    product_add)``.  The last operation is governed by
    :func:`runtime.reference.formats.binary32_product_add`; its first two
    entries are the concrete COMPRESS_PROJECT and INDEX_SCORE values that a
    separately rounded multiply/add gets wrong.

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

    fused_inputs = product_add_probe_inputs()
    while len(left) < len(fused_inputs):
        left.append(int(rng.integers(0, 1 << 32, dtype=np.uint64)))
        right.append(int(rng.integers(0, 1 << 32, dtype=np.uint64)))

    entries: list[tuple[int, ...]] = []
    for (a, b), (accumulator, lhs_bf16, rhs_bf16) in zip(
        zip(left, right, strict=True), fused_inputs, strict=True
    ):
        add_err, add_value = _exact_binary(exact_formats.binary32_add, a, b)
        mul_err, mul_value = _exact_binary(exact_formats.binary32_multiply, a, b)
        try:
            narrowed = exact_formats.binary32_bits_to_bf16_rne(a)
        except exact_formats.NumericReferenceError:
            bf_field, bf_value = 2, 0          # error 1 in the top two bits
        else:
            bf_field = 1 if narrowed.saturated else 0
            bf_value = int(narrowed.code)
        fused_err, fused_value = _exact_product_add(
            accumulator, lhs_bf16, rhs_bf16
        )
        entries.append((
            a, b, add_err, add_value, mul_err, mul_value, bf_field, bf_value,
            accumulator, lhs_bf16 | (rhs_bf16 << 16), fused_err, fused_value,
        ))
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


def _exact_product_add(
    accumulator: int, lhs_bf16: int, rhs_bf16: int
) -> tuple[int, int]:
    nonfinite = (
        ((accumulator >> 23) & 0xFF) == 0xFF
        or ((lhs_bf16 >> 7) & 0xFF) == 0xFF
        or ((rhs_bf16 >> 7) & 0xFF) == 0xFF
    )
    if nonfinite:
        return 1, 0
    lhs = exact_formats.decode_bf16(lhs_bf16).value
    rhs = exact_formats.decode_bf16(rhs_bf16).value
    assert lhs is not None and rhs is not None
    try:
        return 0, int(
            exact_formats.binary32_product_add(accumulator, lhs, rhs)
        )
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
        descriptor_words, descriptor_metadata = descriptor_admission(case)
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

        exact_words, exact_authority, exact_saturations = (
            _independent_exact_result(case, golden)
        )
        if exact_words is not None:
            device_words = as_words(golden["output"])
            if device_words != exact_words:
                mismatch = next(
                    index
                    for index, (device, exact) in enumerate(
                        zip(device_words, exact_words, strict=True)
                    )
                    if device != exact
                )
                raise SystemExit(
                    f"{case.name}: pending frozen-source repair: Device output "
                    f"word {mismatch} is 0x{device_words[mismatch]:08x}, but "
                    f"{exact_authority} requires 0x{exact_words[mismatch]:08x}. "
                    "Do not regenerate the canonical RTL campaign until the "
                    "runtime.sim implementation uses the exact-product, "
                    "single-rounded product-add contract."
                )
            if exact_saturations is not None:
                device_saturations = int(
                    golden["counters"].get("vector.saturations", 0)
                )
                if device_saturations != exact_saturations:
                    raise SystemExit(
                        f"{case.name}: pending frozen-source repair: Device "
                        f"reports vector.saturations={device_saturations}, but "
                        f"{exact_authority} requires {exact_saturations}. The "
                        "VECTOR_REDUCTION event-11 counter is architectural; "
                        "do not regenerate the canonical RTL campaign until "
                        "runtime.sim publishes every retained saturation."
                    )

        a_base = len(m0_words)
        m0_words.extend(as_words(golden["operand0"]))
        b_base = len(m1_words)
        if golden["operand1"] is not None:
            m1_words.extend(as_words(golden["operand1"]))
        c_base = len(m1_words)
        if case.prior_payload is not None:
            m1_words.extend(as_words(case.prior_payload))
        operand2_base = len(m2_words)
        if golden["operand2"] is not None and golden["scale0"] is not None:
            raise SystemExit(
                f"{case.name}: m2 cannot carry operand2 and MATMUL scales"
            )
        if golden["operand2"] is not None:
            m2_words.extend(as_words(golden["operand2"]))
        elif golden["scale0"] is not None:
            m2_words.extend(as_words(golden["scale0"]))
        operand3_base = len(m3_words)
        if golden["operand3"] is not None and golden["scale1"] is not None:
            raise SystemExit(
                f"{case.name}: m3 cannot carry operand3 and MATMUL scales"
            )
        if golden["operand3"] is not None:
            m3_words.extend(as_words(golden["operand3"]))
        elif golden["scale1"] is not None:
            m3_words.extend(as_words(golden["scale1"]))

        # Where this case's results live in the shared result memory, and what
        # the checkers must find there.
        out_base = len(expect_words)
        rtl_fault_code = case.rtl_expected_fault_code
        if case.rtl_descriptor_overrides:
            if rtl_fault_code not in (None, ERR_SHAPE):
                raise SystemExit(
                    f"{case.name}: descriptor corruption must map to ERR_SHAPE"
                )
            rtl_fault_code = ERR_SHAPE
        if faulted and rtl_fault_code is not None:
            raise SystemExit(
                f"{case.name}: one case cannot mix a Device fault and an "
                "RTL-only bounded/admission refusal"
            )
        expected_refusal = faulted or rtl_fault_code is not None
        if expected_refusal:
            fault_code = (
                classify_fault(golden["message"])
                if faulted else int(rtl_fault_code)
            )
            # The whole destination window must still hold the unwritten
            # sentinel: a refusal that left part of a result behind is a
            # different refusal.
            window = (
                destination_window(case)
                if faulted else len(as_words(golden["output"]))
            )
            expect_words.extend([UNWRITTEN] * window)
            expect_count = window
            result_count = 0
            saturations = 0
            work = 0
            token = 0
            ties = 0
            # Counters are architectural only for engines that publish them,
            # but a refused operation must never leak a speculative count.
            flags = FLAG_EXPECT_UNTOUCHED | FLAG_COMPARE_SATURATION
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
            c_base if case.scalar_bits is None else int(case.scalar_bits),
            out_base,
            1 if case.scale0_object != NO_ID else 0,
            1 if case.scale1_object != NO_ID else 0,
            case.block_a,
            case.block_b,
            case.block_rows_a,
            case.block_rows_b,
            operand2_base,
            operand3_base,
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
            *descriptor_words,
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
            "expectation_source": (
                "device_fault" if faulted
                else "rtl_descriptor_admission"
                if case.rtl_descriptor_overrides
                else "rtl_bounded_profile"
                if rtl_fault_code is not None
                else "device_and_independent_exact_reference"
                if exact_authority is not None
                else "device"
            ),
            "independent_exact_reference": exact_authority,
            "independent_exact_saturations": exact_saturations,
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
            "operand2_dtype": view_dtype(case.deployment, case.operand2_view),
            "operand3_dtype": view_dtype(case.deployment, case.operand3_view),
            "output_dtype": (
                case.output_dtype
                or view_dtype(case.deployment, case.output_view)
            ),
            "block_a": case.block_a,
            "block_b": case.block_b,
            "block_rows_a": case.block_rows_a,
            "block_rows_b": case.block_rows_b,
            "scalar_bits": case.scalar_bits,
            "rtl_config": {
                **case.rtl_config,
                "record": {
                    "cfg_rows": case.rows,
                    "cfg_cols": case.cols,
                    "cfg_depth": case.depth,
                    "cfg_count": case.count,
                    "cfg_c_base": (
                        c_base if case.scalar_bits is None else int(case.scalar_bits)
                    ),
                    "cfg_block_a": case.block_a,
                    "cfg_block_b": case.block_b,
                    "cfg_slots": case.slots,
                    "cfg_scale_a_base": operand2_base,
                    "cfg_scale_b_base": operand3_base,
                },
                "descriptor_admission": descriptor_metadata,
            },
            "program_sha256": hashlib.sha256(case.deployment.program).hexdigest(),
            "descriptor_table_sha256": hashlib.sha256(
                case.deployment.table.encode()
            ).hexdigest(),
            "operand0_sha256": words_digest(as_words(golden["operand0"])),
            "operand1_sha256": (
                "" if golden["operand1"] is None
                else words_digest(as_words(golden["operand1"]))
            ),
            "operand2_sha256": (
                "" if golden["operand2"] is None
                else words_digest(as_words(golden["operand2"]))
            ),
            "operand3_sha256": (
                "" if golden["operand3"] is None
                else words_digest(as_words(golden["operand3"]))
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
    descriptor = deployment.table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW)
    return int(descriptor.payload["dtype"])


def _operator_descriptor(case: Case) -> Any:
    """Return the sole operator the one-operation campaign case executes."""
    matches = [
        descriptor
        for descriptor in case.deployment.table.descriptors()
        if descriptor.descriptor_type == int(ExtendedDescriptorType.OPERATOR)
        and int(descriptor.payload["engine_family"]) == case.family
        and int(descriptor.payload["engine_sub"]) == case.sub
    ]
    if len(matches) != 1:
        raise SystemExit(
            f"{case.name}: expected one matching OPERATOR descriptor, found "
            f"{len(matches)}"
        )
    return matches[0]


def _view_admission(case: Case, view_id: int) -> dict[str, Any]:
    if view_id == NO_ID:
        return {"dtype": 0, "rank": 0, "dims": (0, 0, 0, 0), "scaled": 0}
    view = case.deployment.table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW)
    rank = int(view.payload["rank"])
    if case.family == int(Major.VECTOR) and case.sub in {
        int(Vector.CONVERT), int(Vector.SCALE), int(Vector.HADAMARD),
        int(Vector.INDEX_SCORE), int(Vector.COMPRESS), int(Vector.MHC),
    } and rank > 4:
        raise SystemExit(
            f"{case.name}: bounded VECTOR admission cannot encode rank {rank}"
        )
    dims = tuple(
        int(view.payload[f"dim{axis}"]) if axis < rank else 0
        for axis in range(4)
    )
    return {
        "dtype": int(view.payload["dtype"]),
        "rank": rank,
        "dims": dims,
        "scaled": int(int(view.payload["scale_object_id"]) != NO_ID),
    }


def descriptor_admission(case: Case) -> tuple[list[int], dict[str, Any]]:
    """Serialize independently derived descriptor metadata for RTL admission.

    The legacy geometry fields are convenient datapath controls; they are not
    proof of the issuing OPERATOR/TENSOR_VIEW/NUMERIC records.  This adapter
    therefore derives arity, every view's dtype/rank/dimensions/scaled state,
    the numeric profile, its complete contract digest, and every aux binding
    directly from the deployment table.  Negative cases override one derived
    field only after this derivation, so they exercise the RTL boundary rather
    than teaching the expected result to the functional Device.
    """
    operator = _operator_descriptor(case)
    inputs = [
        _view_admission(case, int(operator.payload[f"input_view_{slot}"]))
        for slot in range(4)
    ]
    outputs = [
        _view_admission(case, int(operator.payload[f"output_view_{slot}"]))
        for slot in range(2)
    ]
    input_valid = sum(
        (int(operator.payload[f"input_view_{slot}"]) != NO_ID) << slot
        for slot in range(4)
    )
    output_valid = sum(
        (int(operator.payload[f"output_view_{slot}"]) != NO_ID) << slot
        for slot in range(2)
    )
    aux = [int(operator.payload[f"aux_id_{slot}"]) for slot in range(4)]
    aux_valid = sum((value != NO_ID) << slot for slot, value in enumerate(aux))

    numeric_id = int(operator.payload["numeric_profile_id"])
    if numeric_id == NO_ID:
        profile_valid = 0
        profile_input = profile_second = profile_output = 0
        profile_accumulator = rounding = reduction = scale_bits = 0
        saturate = nan_policy = epsilon_bits = profile_flags = 0
        # HYPER_CONNECT_POST has no NUMERIC descriptor by architectural
        # design.  Bind the selected operator form itself instead of accepting
        # an uncorrelated all-zero digest as a generic "valid" signal.
        contract_digest = (
            hashlib.sha256(b"HYPER_CONNECT_POST").digest()
            if case.family == int(Major.VECTOR)
            and case.sub == int(Vector.MHC)
            and aux[0] == 1
            else bytes(32)
        )
    else:
        profile = case.deployment.table.get(
            numeric_id, ExtendedDescriptorType.NUMERIC
        )
        profile_valid = 1
        profile_input = int(profile.payload["input_dtype"])
        profile_second = int(profile.payload["second_input_dtype"])
        profile_output = int(profile.payload["output_dtype"])
        profile_accumulator = int(profile.payload["accumulator_dtype"])
        rounding = int(profile.payload["rounding_mode"])
        reduction = int(profile.payload["reduction_order"])
        scale_bits = int(profile.payload["scale_bits"])
        saturate = int(profile.payload["saturate"])
        nan_policy = int(profile.payload["nan_policy"])
        epsilon_bits = int(profile.payload["epsilon_bits"])
        profile_flags = int(profile.payload["flags"])
        contract_digest = bytes(profile.payload["contract_digest"])

    fields: dict[str, Any] = {
        "input_valid": input_valid,
        "output_valid": output_valid,
        "profile_valid": profile_valid,
        "profile_input_dtype": profile_input,
        "profile_second_dtype": profile_second,
        "profile_output_dtype": profile_output,
        "profile_accumulator_dtype": profile_accumulator,
        "rounding_mode": rounding,
        "reduction_order": reduction,
        "profile_scale_bits": scale_bits,
        "profile_saturate": saturate,
        "profile_nan_policy": nan_policy,
        "profile_epsilon_bits": epsilon_bits,
        "profile_flags": profile_flags,
        "contract_digest": contract_digest,
        "aux_valid": aux_valid,
    }
    for slot, metadata in enumerate(inputs):
        for name, value in metadata.items():
            fields[f"input{slot}_{name}"] = value
    for slot, metadata in enumerate(outputs):
        for name, value in metadata.items():
            fields[f"output{slot}_{name}"] = value
    for slot, value in enumerate(aux):
        fields[f"aux{slot}"] = value

    unknown = set(case.rtl_descriptor_overrides) - set(fields)
    if unknown:
        raise SystemExit(
            f"{case.name}: unknown RTL descriptor override(s): {sorted(unknown)}"
        )
    fields.update(case.rtl_descriptor_overrides)

    digest = fields["contract_digest"]
    if isinstance(digest, str):
        digest = bytes.fromhex(digest)
    if not isinstance(digest, bytes) or len(digest) != 32:
        raise SystemExit(f"{case.name}: contract digest must contain 32 bytes")
    contract_words = [
        int.from_bytes(digest[offset : offset + 4], "big")
        for offset in range(0, 32, 4)
    ]
    input_dtypes = sum(
        (int(fields[f"input{slot}_dtype"]) & 0xFF) << (8 * slot)
        for slot in range(4)
    )
    output_dtypes = sum(
        (int(fields[f"output{slot}_dtype"]) & 0xFF) << (8 * slot)
        for slot in range(2)
    )
    ranks = sum(
        (int(fields[f"input{slot}_rank"]) & 0xF) << (4 * slot)
        for slot in range(4)
    ) | sum(
        (int(fields[f"output{slot}_rank"]) & 0xF) << (16 + 4 * slot)
        for slot in range(2)
    )
    scaled = sum(
        (int(fields[f"input{slot}_scaled"]) & 1) << slot
        for slot in range(4)
    ) | sum(
        (int(fields[f"output{slot}_scaled"]) & 1) << (4 + slot)
        for slot in range(2)
    )
    profile_dtypes = (
        (int(fields["profile_input_dtype"]) & 0xFF)
        | ((int(fields["profile_second_dtype"]) & 0xFF) << 8)
        | ((int(fields["profile_output_dtype"]) & 0xFF) << 16)
        | ((int(fields["profile_accumulator_dtype"]) & 0xFF) << 24)
    )
    shape_words: list[int] = []
    for prefix in (
        "input0", "input1", "input2", "input3", "output0", "output1"
    ):
        dims = tuple(int(value) for value in fields[f"{prefix}_dims"])
        if len(dims) != 4 or any(not 0 <= value < 1 << 32 for value in dims):
            raise SystemExit(f"{case.name}: {prefix} dimensions do not fit")
        shape_words.extend(dims)
    words = [
        int(fields["input_valid"]),
        int(fields["output_valid"]),
        input_dtypes,
        output_dtypes,
        ranks,
        scaled,
        profile_dtypes,
        (int(fields["rounding_mode"]) & 0xFF)
        | ((int(fields["reduction_order"]) & 0xFF) << 8)
        | ((int(fields["profile_valid"]) & 1) << 16)
        | ((int(fields["profile_saturate"]) & 1) << 17)
        | ((int(fields["profile_nan_policy"]) & 0xFF) << 24),
        *shape_words,
        *contract_words,
        int(fields["aux_valid"]),
        *(int(fields[f"aux{slot}"]) & 0xFFFFFFFF for slot in range(4)),
        int(fields["profile_scale_bits"]) & 0xFFFFFFFF,
        int(fields["profile_epsilon_bits"]) & 0xFFFFFFFF,
        int(fields["profile_flags"]) & 0xFFFFFFFF,
    ]
    if len(words) != CASE_STRIDE - 32:
        raise SystemExit(
            f"{case.name}: descriptor extension is {len(words)} words, "
            f"expected {CASE_STRIDE - 32}"
        )
    published = {
        **fields,
        "contract_digest": digest.hex(),
        "record_words": words,
    }
    return words, published


def _independent_exact_result(
    case: Case, golden: dict[str, Any]
) -> tuple[list[int] | None, str | None, int | None]:
    """Return exact-reference output for governed ordered-dot VECTOR forms."""
    if golden["status"] != 0 or case.family != int(Major.VECTOR):
        return None, None, None
    if case.sub == int(Vector.COMPRESS):
        result = compress_project_bf16(
            golden["operand0"].astype(np.uint16).tolist(),
            golden["operand1"].astype(np.uint16).tolist(),
            golden["operand2"].astype(np.uint16).tolist(),
        )
        kv = np.asarray(result.kv, dtype=np.uint32)
        gate = np.asarray(result.scores, dtype=np.uint32)
        packed = np.stack((kv, gate), axis=2)
        return (
            as_words(packed),
            "runtime.reference.compression.compress_project_bf16",
            0,
        )
    if case.sub == int(Vector.INDEX_SCORE):
        result = index_score_bf16(
            golden["operand0"].astype(np.uint16).tolist(),
            golden["operand1"].astype(np.uint16).tolist(),
            golden["operand2"].astype(np.uint16).tolist(),
            scale_binary32=int(case.scalar_bits or 0),
        )
        return (
            as_words(np.asarray(result.values, dtype=np.uint16)),
            "runtime.reference.index_score.index_score_bf16",
            int(result.qk_saturated_element_count)
            + int(result.scaled_weight_saturated_element_count)
            + int(result.weighted_score_saturated_element_count)
            + int(result.output_saturated_element_count),
        )
    if case.sub == int(Vector.MHC):
        post_codes = np.ascontiguousarray(
            golden["operand2"], dtype=np.float32
        ).view(np.uint32)
        comb_codes = np.ascontiguousarray(
            golden["operand3"], dtype=np.float32
        ).view(np.uint32)
        result = hc_post_bf16(
            golden["operand0"].astype(np.uint16).tolist(),
            golden["operand1"].astype(np.uint16).tolist(),
            post_codes.tolist(),
            comb_codes.tolist(),
            hc_multiplier=int(case.slots),
        )
        return (
            as_words(np.asarray(result.output_codes, dtype=np.uint16)),
            "runtime.reference.vector.hc_post_bf16",
            int(result.output_saturation_count),
        )
    return None, None, None


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
    def require(name: str) -> int:
        """A counter the real engine must have published for this case.

        Absence does not mean zero.  It means the golden execution did not do
        the work -- most often because a *different* module bound the dispatch
        table to recording no-ops and never put it back, which is legal,
        silent, and yields an empty result rather than an error.  Refuse here,
        naming the cause, rather than failing later on a bare ``KeyError`` that
        says nothing about why.  Counters that are genuinely optional (a
        saturation count that is absent when nothing saturated) are read with
        ``.get`` and never come through here.
        """
        if name not in counters:
            raise SystemExit(
                f"{case.name}: the golden execution published no {name!r}; "
                f"status={golden['status']} trap_class={golden['trap_class']} "
                f"message={golden['message']!r}. This correlation is against "
                "the real engines by construction, so a stubbed or "
                "unimplemented engine may not stand in for one."
            )
        return int(counters[name])

    if case.family == int(Major.TENSOR):
        return (
            require("tensor.output_elements"),
            int(counters.get("tensor.saturations", 0)),
            case.rows * case.cols * case.depth,
            0,
            0,
            FLAG_COMPARE_WORK | FLAG_COMPARE_SATURATION,
        )
    if case.family == int(Major.VECTOR):
        elements = require("vector.elements")
        if case.sub == int(Vector.INDEX_SCORE):
            # INDEX_SCORE counts the query/key multiply-add work across heads,
            # candidates and depth, while it writes one score per candidate.
            return (
                written,
                int(counters.get("vector.saturations", 0)),
                elements,
                0,
                0,
                FLAG_COMPARE_WORK | FLAG_COMPARE_SATURATION,
            )
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
            require("selection.vocabulary_elements"),
            int(golden["output"].reshape(-1)[0]),
            require("selection.tie_multiplicity"),
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
    fault_count = sum(1 for record in records if record["expected_fault_code"])
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
        "schema": VECTOR_SCHEMA,
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
            "binary32_bits_to_bf16_rne, plus binary32_product_add for exact "
            "BF16 products accumulated with one final binary32 RNE rounding; "
            "all compute with fractions.Fraction, so no host floating-point "
            "mode participates"
        ),
        "descriptor_admission": {
            "schema": "operator_view_numeric_exact_v1",
            "derivation": (
                "each case record derives arity, every input/output dtype, "
                "rank and dimension, scaled state, numeric profile fields, "
                "complete contract digest and aux bindings independently "
                "from the admitted deployment descriptors"
            ),
            "negative_policy": (
                "negative cases alter one derived record field after "
                "derivation and require ERR_SHAPE with no result or "
                "speculative saturation count"
            ),
        },
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
            "unscaled_convert_one_input_one_output": (
                "runtime.sim.engines.vector._vector_convert using "
                "runtime.sim.formats widen/narrow; identity dtypes are copied"
            ),
            "bf16_mul_rne_v1_and_bf16_scale_rne_v1": (
                "runtime.sim.engines.vector._vector_scale using the selected "
                "backend's binary32 multiply and one output conversion"
            ),
            "deepseek_v4_hadamard_128_bf16_v1": (
                "runtime.sim.engines.vector._vector_hadamard and "
                "runtime.reference.hadamard"
            ),
            "deepseek_v4_index_score_bf16_v1": (
                "runtime.sim.engines.deepseek_vector.index_score and "
                "runtime.reference.index_score"
            ),
            "deepseek_v4_compress_project_binary32_v1": (
                "runtime.sim.engines.deepseek_vector._compress_project and "
                "runtime.reference.compression.compress_project_bf16"
            ),
            "HYPER_CONNECT_POST": (
                "runtime.sim.engines.deepseek_vector._mhc_post and "
                "runtime.reference.vector.hc_post_bf16"
            ),
            "greedy_lowest_token_id_argmax": (
                "runtime.sim.engines.selection.argmax"
            ),
            "exact_index_select_v1": "runtime.sim.engines.dma gather and scatter",
        },
        "vector_rtl_scope": {
            "newly_integrated": [
                {
                    "opcode": "CONVERT",
                    "sub": int(Vector.CONVERT),
                    "covered": "unscaled one-input/one-output form",
                    "bounds": "1..512 elements; supported identity formats or finite numeric input to BF16/FP32",
                    "uncovered_forms": [
                        "block dequantization",
                        "two-output block quantization",
                    ],
                },
                {
                    "opcode": "SCALE",
                    "sub": int(Vector.SCALE),
                    "covered": "aux0 0 constant and aux0 1 same-shape elementwise BF16-to-BF16",
                    "bounds": "1..512 elements",
                    "uncovered_forms": [
                        "aux0 2 logistic sigmoid",
                        "general trailing-axis factor broadcasting",
                    ],
                },
                {
                    "opcode": "HADAMARD",
                    "sub": int(Vector.HADAMARD),
                    "covered": "normalized 128-point BF16 transform",
                    "bounds": "1..4 rows, width exactly 128",
                    "uncovered_forms": [],
                },
                {
                    "opcode": "INDEX_SCORE",
                    "sub": int(Vector.INDEX_SCORE),
                    "covered": "batch one, four-head BF16 learned-index score at scale exactly 1.0",
                    "bounds": "1..4 sites, 1..8 candidates, 1..16 head channels",
                    "uncovered_forms": [
                        "non-unit learned-index scales",
                        "head counts other than four",
                        "batches greater than one",
                    ],
                },
                {
                    "opcode": "COMPRESS",
                    "sub": int(Vector.COMPRESS),
                    "covered": "aux0 0 COMPRESS_PROJECT with KV-then-gate FP32 output",
                    "bounds": "1..8 flattened rows, 1..16 outputs, 1..64 reduction channels",
                    "uncovered_forms": [
                        "aux0 1 COMPRESS_POOL",
                        "aux0 2 COMPRESS_STATE_UPDATE",
                    ],
                },
                {
                    "opcode": "MHC",
                    "sub": int(Vector.MHC),
                    "covered": "aux0 1 HYPER_CONNECT_POST with four streams",
                    "bounds": "1..4 flattened sites, 1..32 hidden channels, multiplier exactly four",
                    "uncovered_forms": [
                        "aux0 0 HYPER_CONNECT_PRE",
                        "aux0 2 HYPER_CONNECT_HEAD",
                    ],
                },
            ],
            "wholly_deferred_transcendental": [
                {
                    "opcode": "SILU_MUL",
                    "sub": int(Vector.SILU_MUL),
                    "reason": "needs correctly rounded sigmoid/exponential RTL",
                },
                {
                    "opcode": "SOFTMAX",
                    "sub": int(Vector.SOFTMAX),
                    "reason": "needs correctly rounded exponential and reciprocal RTL",
                },
                {
                    "opcode": "SQRT_SOFTPLUS",
                    "sub": int(Vector.SQRT_SOFTPLUS),
                    "reason": "needs correctly rounded exponential/logarithm/square-root RTL",
                },
            ],
            "standalone_outside_engine_array": [
                "RMS_NORM",
                "HEAD_RMS_NORM",
                "ROPE",
            ],
            "unsupported_policy": (
                "unsupported sub-cases and out-of-bound shapes raise ERR_SHAPE; "
                "no transcendental behavior is approximated or emulated"
            ),
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
