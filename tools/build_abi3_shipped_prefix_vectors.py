#!/usr/bin/env python3
"""Build the smallest honest shipped-program sequencer/engine RTL witness.

The four shipped ABI 3.0 decode entrypoints all begin with a bounded sequence
that the RTL can execute without pretending an unsupported model operator
exists: generated-row ``DMA.GATHER`` operations, one checkpoint-backed
``TENSOR.EMBED_LOOKUP``, then Qwen ``VECTOR.RMS_NORM`` and the complete
layer-zero query, key, and value ``TENSOR.MATMUL`` family plus query/key
``VECTOR.HEAD_RMS_NORM``, or DeepSeek stride-zero ``DMA.TRANSFER``.
Row movement lowers to the existing index mover; RMSNorm uses the independently
correlated exact arithmetic slice and MATMUL uses the existing ABI 3.0 MAC
lane's deterministic ascending-K association.

This generator retains those exact program and descriptor identities, resolves
their real views for the same 16-token decode request used by the deployment
campaign, materialises only the selected generated RoPE rows, and performs
bounded reads of token zero's BF16 checkpoint row and Qwen's layer-zero gains.
The complete 32 MiB query and two 8 MiB KV projection segments are re-read and
authenticated because every BF16 code is consumed.  The hardware must produce
every retained result word, then fail closed at the exact next unsupported
instruction.  It does not claim a whole model, prefill, token selection, or
decoding result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    Control,
    Dma,
    DType,
    Link,
    Major,
    NO_ID,
    Tensor,
    Vector,
)
from runtime.abi3.deployment import Deployment, resolve_path  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    CollectiveOp,
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.sim.generators import _rope_frequencies_binary32  # noqa: E402
from runtime.sim.formats import narrow_bf16_rne  # noqa: E402
from runtime.sim.memory import ViewResolver  # noqa: E402
from runtime.reference.tensor_accelerator_rope import (  # noqa: E402
    rope_bf16 as scalar_rope_bf16,
)
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    rms_norm_bf16,
)
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    dense_bf16_linear_bf16,
)
from runtime.tensor_accelerator.rope import (  # noqa: E402
    rope_bf16 as optimized_rope_bf16,
)
from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    CASE_STRIDE as DEPLOYMENT_CASE_STRIDE,
    TARGETS,
    certified_deployment_identity,
)


OUTPUT_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_VECTOR_JSON = DEPLOYMENT_VECTOR_DIR / "abi3_deployment_rtl_vectors.json"

VECTOR_SCHEMA = "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
# The case record carries the OBJECT PLACEMENT TABLE the issue bridge needs.
# Every operand and every result of every family is placed by object now, so
# the ten separate placement words this record used to carry -- three unkeyed
# bases, six per-role object tables and the appending output base -- are gone
# and one table replaces them.  Word 56 is NOT free: the exact multicast
# overlay writes its launch count there.
#
# Table size is the derived demand, not a round number.  The distinct ABI
# objects the governed decode program's issued operators name, counted from
# each deployment's own descriptors: 32 on the ROM lowering, 31 on the HBM
# lowering, 23 over one transformer layer on both.  32 entries, so nine spare
# over the layer and none over the whole program on ROM; a program naming a
# 33rd object fails admission rather than being mis-addressed.
CASE_STRIDE = 139
PLACE_SPAN_WORD = 57       # words this case's result region ALLOCATES
PLACE_VALID_WORD = 58      # this vector set supplied the object -> bank table
# Whether this vector set admits the six MAPPED families as well.  It is a
# separate word from the table above and always was a separate question: the
# table says where objects live, this says whether DMA.SCATTER, ATTENTION.GQA,
# VECTOR.ADD, VECTOR.SILU_MUL, SELECTION.ARGMAX and SELECTION.TOKEN_APPEND may
# run at all.  Collapsing the two would silently extend this campaign's span
# past its fail-stop boundary, on a vector set that carries no golden for the
# operators past it.
MAPPED_FAMILIES_WORD = 59
PLACE_TABLE_WORD = 60      # 32 x (object id, base words), interleaved
PLACE_TABLE_ENTRIES = 32
MAP_CONTEXT_WORD = 124     # the request's active context length
MAP_PLANE_ROWS_WORD = 125  # the compact KV bank's K-to-V plane stride, rows
MAP_POLICY_WORD = 126      # bound GENERATION_POLICY descriptor id
MAP_MAX_NEW_WORD = 127     # the request's authenticated max_new_tokens
MAP_GENERATED_WORD = 128   # tokens produced before this pass
MAP_LAUNCH_WORD = 129      # six expected per-family launch counts
MAP_TOKEN_WORD = 135       # expected selected token
MAP_TIE_WORD = 136         # expected tie multiplicity
MAP_EOS_WORD = 137         # expected EOS reason
MAP_RESERVED_WORD = 138    # reserved, must be zero
NO_OBJECT = 0xFFFF_FFFF
META_WORDS = 27
INDEX_WORDS = 64
SOURCE_WORDS = 65536
RESULT_WORDS = 98304
PROMPT_TOKENS = 16
INDEX_VALUE = 16
EMBED_TOKEN = 0
EMBED_WIDTH = 4096
KV_WIDTH = 1024
HEAD_WIDTH = 128
Q_HEADS = 32
KV_HEADS = 8
VOCABULARY = 151_936


@dataclass(frozen=True)
class TargetGeometry:
    """The model geometry this builder checks one target's views against.

    It used to be five module constants plus a `target_index < 2` discriminator,
    which is why a fifth target was walked with the DeepSeek identity set: the
    index, not the model, decided. Keying the geometry by target KEY means a
    second configuration of the same model is expressible, and a target with no
    entry is skipped rather than walked with another model's constants.

    Every field is checked against the deployment, not trusted: a wrong value here
    makes the builder refuse with "view profile changed", never emit wrong golden.
    """

    model_index: int          #: 0 selects the Qwen identity set, 1 DeepSeek
    embed_width: int
    kv_width: int
    head_width: int
    query_heads: int
    kv_heads: int
    vocabulary: int
    rope_aux0: int            #: the lowering's ROPE coefficient-row stride


#: rope_aux0 is a property of the LOWERING, not of the model -- the shipped ROM
#: bundle passes one head width and the HBM bundle two -- so each value here was
#: read out of its own deployment's ROPE operators rather than assumed:
#: shipped ROM 128, shipped HBM 256, reduced ROM 16.
TARGET_GEOMETRY: dict[str, TargetGeometry] = {
    "qwen3-8b-rom-single-chip": TargetGeometry(
        model_index=0, embed_width=4096, kv_width=1024, head_width=128,
        query_heads=32, kv_heads=8, vocabulary=151_936, rope_aux0=128,
    ),
    "qwen3-8b-hbm-single-chip": TargetGeometry(
        model_index=0, embed_width=4096, kv_width=1024, head_width=128,
        query_heads=32, kv_heads=8, vocabulary=151_936, rope_aux0=256,
    ),
    #: THE REDUCED TARGET'S GEOMETRY, deliberately NOT enabled here yet.
    #:
    #: hidden 128, 8 query heads, 2 KV heads, head_dim 16, vocab 4,096 -- from
    #: build/models/qwen3-reduced-v1/config.json, with kv_width = 2 x 16 and
    #: rope_aux0 read out of the deployment's own ROPE operators rather than assumed.
    #: Every value is checked against the deployment when it is enabled.
    #:
    #: Walking it here was tried and it works as far as this builder's fail-stop
    #: boundary -- geometry, identities, view profiles and every exact oracle resolve
    #: once the pins are per-target. What it does NOT do is reach a token, and that
    #: is the finding: the boundary is pc=32 DMA.SCATTER, which is
    #: MODEL-INDEPENDENT. A reduced prefix stops exactly where the shipped one does.
    #:
    #: So enabling it would add a fifth PREFIX case, not a token, while changing
    #: every aggregate witness-depth total, the campaign's required marker and its
    #: expected_cases. The token needs this builder to walk PAST the boundary through
    #: six operator families it has never walked -- DMA.SCATTER, ATTENTION.GQA,
    #: VECTOR.ADD, VECTOR.SILU_MUL, SELECTION.ARGMAX, SELECTION.TOKEN_APPEND -- each
    #: with identity resolution, view and numeric profile validation, and an exact
    #: oracle, which is the real content of "MAPPED_FAMILIES_WORD carries no golden
    #: past its fail-stop boundary".
    #:
    #: Uncomment to enable, once those six families are walked:
    # "qwen3-reduced-rom-single-chip": TargetGeometry(
    #     model_index=0, embed_width=128, kv_width=32, head_width=16,
    #     query_heads=8, kv_heads=2, vocabulary=4_096, rope_aux0=16,
    # ),
    "deepseek-v4-flash-rom-wafer": TargetGeometry(
        model_index=1, embed_width=4096, kv_width=1024, head_width=128,
        query_heads=32, kv_heads=8, vocabulary=129_280, rope_aux0=128,
    ),
    "deepseek-v4-flash-hbm-cluster": TargetGeometry(
        model_index=1, embed_width=4096, kv_width=1024, head_width=128,
        query_heads=32, kv_heads=8, vocabulary=129_280, rope_aux0=128,
    ),
}
EXACT_INDEX_SELECT = hashlib.sha256(b"exact_index_select_v1").digest()
QWEN_EMBED_CONTRACT = hashlib.sha256(b"bf16_payload_lookup_v1").digest()
DEEPSEEK_EMBED_CONTRACT = hashlib.sha256(b"lookup_bf16_token_embedding_v1").digest()
QWEN_RMS_CONTRACT = hashlib.sha256(b"qwen3_rmsnorm_fp32_bf16_v1").digest()
DEEPSEEK_TRANSFER_CONTRACT = hashlib.sha256(b"structural_hc_expand_bf16_v1").digest()
QWEN_MATMUL_CONTRACT = hashlib.sha256(b"bf16_bf16_fp32_blocked_rne_v1").digest()
QWEN_ROPE_CONTRACT = hashlib.sha256(b"qwen3_rope_fp32_bf16_v1").digest()
MATMUL_OUTPUT_SHA256 = {
    11: "b900b79fd38ff6a9bff470ac27e9672b0c3724b84f6a1f7e964c2ec0918ea0ff",
    14: "dd690fbd9886a0af94cc6b2477ef5bfcc84fe66cac66f345f2ec654a83b28403",
    17: "b07011da7a3d58dcccceb91e596ceebc2084ab3c2fc9d0b6a9a8704e91ef8dc5",
}
HEAD_RMS_OUTPUT_SHA256 = {
    20: "bf01d5254a7616bfffac6f789fbae1b94c68c5201944c8faf297b803987a401c",
    23: "71af5033456b74d137d248f4019f848aedb8c8f758f952612082ad48d50f6a66",
}
HEAD_RMS_MEAN_SHA256 = {
    20: "e10c17ec2a238ecebbad32e5c85a6822babfec8ac7650eb7bba2a67fc0003cb2",
    23: "b1d45efa4ea83b59c1638bf041adc2e30dfb98c8b4ea2d156c247213ff05f065",
}
HEAD_RMS_INVERSE_SHA256 = {
    20: "12a8e58463d481658ffee21140fd06ecc6ff799fcd27b2cab650aa7508f89aa9",
    23: "b088f0e2a9c0cb618be3df9e9752be637198b2eb8e1a457fa7862a12691f1d71",
}
ROPE_OUTPUT_SHA256 = {
    26: "f36db31b14aa59e0b0c7bc444403a7991063c3a0e874dcee151b7428b0ee8150",
    29: "b41de05c0a7f1f495ded2295c22781f4aa345136d2c572248469c422f266c406",
}
ROPE_COEFFICIENT_BF16_SHA256 = (
    "836c0e4d9ba8556db28ac7d300914b4cb42d15418e59c6550a693558252049f1"
)

# ---------------------------------------------------------------------------
# Descriptor resolution by identity, never by number
# ---------------------------------------------------------------------------
#
# A descriptor ID is a table index.  It records the order the backend happened
# to emit descriptors in and nothing whatever about the operation described.
# The governed prefix's IDs have moved three times inside this repository --
# ``build/abi3/qwen3-8b-rom-rowfold-v1``, the ``*-pre-am-e9`` pair, and the
# promoted AM-E9 v2 pair -- and every move silently invalidated a hand-written
# table of numbers without changing one bit of arithmetic.  Nothing below
# names a descriptor by number.
#
# Each governed operation is named by what it IS:
#
#   * the kernel of the CERTIFIED Kernel IR that it lowers, by that kernel's
#     ``kernel_id`` string.  The descriptor's ``source_kernel_id`` is that
#     kernel's ``index``, and both Qwen lowerings share one Kernel IR (as do
#     both DeepSeek lowerings), so the anchor is lowering-independent by
#     construction rather than by coincidence;
#   * the engine family and sub-opcode the operation issues to;
#   * the numeric contract its NUMERIC descriptor carries, cross-checked
#     against the same kernel's own declared ``numeric_contract`` name -- the
#     digest is SHA-256 of that name, so the two must agree or the derivation
#     is refused;
#   * ``aux_id_0`` where the family binds one, and the payload slots the
#     family must leave unbound.
#
# The ID is then SEARCHED FOR in the deployment's own descriptor table.  The
# search must return exactly one descriptor.  Zero matches and two matches are
# both refusals that name the ambiguity, because a governed operation that
# cannot be told apart from another one is not evidence about either.
#
# The two lowerings are NOT assumed to agree.  Every derivation runs against
# the bundle of the target being built, so the ROM and HBM vector sets carry
# different descriptor IDs wherever the lowerings differ -- which is at all
# eight governed Qwen PCs.  Where they differ in numeric CONTRACT under one
# contract digest, ``_audit_contract_agreement`` says so out loud instead of
# picking one and pretending it fits both.

QWEN_KV_APPEND_CONTRACT = hashlib.sha256(b"bf16_byte_preserving_state_v1").digest()
DEEPSEEK_HC_PRE_CONTRACT = hashlib.sha256(
    b"hyper_connection_hc_pre_bf16_v1"
).digest()

DEPLOYMENT_SCOPE = "deployment_descriptor_table"

# The payload slots each governed family must leave unbound.  These are the
# same lists the per-operation profile checks below assert; stating them in
# the identity as well is what lets the derivation tell two operations of one
# family apart without consulting the instruction that names either.
UNBOUND_BINARY = (
    "input_view_2",
    "input_view_3",
    "output_view_1",
    "aux_id_0",
    "aux_id_1",
    "aux_id_2",
    "aux_id_3",
)
UNBOUND_BINARY_WITH_AUX0 = (
    "input_view_2",
    "input_view_3",
    "output_view_1",
    "aux_id_1",
    "aux_id_2",
    "aux_id_3",
)
UNBOUND_UNARY = ("input_view_1",) + UNBOUND_BINARY

# The NUMERIC payload fields that make up a numeric contract.  Two descriptors
# that carry one contract digest and differ in any of these do not implement
# one contract, whatever the digest claims.
NUMERIC_SIGNATURE_FIELDS = (
    "input_dtype",
    "second_input_dtype",
    "accumulator_dtype",
    "output_dtype",
    "rounding_mode",
    "reduction_order",
    "saturate",
    "nan_policy",
    "epsilon_bits",
    "scale_bits",
    "flags",
)


# The Kernel IR spells dtypes; the descriptor encodes them.  Mapping one to
# the other is what lets the builder say which lowering's numeric payload
# agrees with the graph it was lowered from, instead of only that the two
# lowerings disagree with each other.
KERNEL_IR_DTYPES = {
    "u8": int(DType.U8),
    "i8": int(DType.I8),
    "u16": int(DType.U16),
    "i16": int(DType.I16),
    "u32": int(DType.U32),
    "i32": int(DType.I32),
    "u64": int(DType.U64),
    "i64": int(DType.I64),
    "bf16": int(DType.BF16),
    "fp16": int(DType.FP16),
    "fp32": int(DType.FP32),
    "fp64": int(DType.FP64),
}


@dataclass(frozen=True)
class OperatorIdentity:
    """One governed operation, stated without a descriptor number."""

    role: str
    kernel: str
    major: int
    sub: int
    contract: bytes
    unbound: tuple[str, ...]
    aux_0: int | None = None


@dataclass(frozen=True)
class BoundaryIdentity:
    """The first instruction the shipped prefix refuses, named the same way."""

    pc: int
    major: int
    sub: int
    opcode: str
    kernel: str | None = None
    contract: bytes | None = None
    collective_op: int | None = None


@dataclass(frozen=True)
class Resolution:
    """A descriptor ID DERIVED from identity, carrying its own derivation."""

    role: str
    kernel: str | None
    kernel_index: int | None
    descriptor_id: int
    numeric_profile_id: int | None
    numeric_signature: tuple[tuple[str, int], ...]
    contract_sha256: str | None
    resolution: str
    class_members: tuple[int, ...]
    considered: int
    declared_input_dtypes: tuple[int | None, ...] = ()

    def record(self) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "role": self.role,
            "kernel_id": self.kernel,
            "kernel_index": self.kernel_index,
            "derived_descriptor_id": self.descriptor_id,
            "numeric_profile_id": self.numeric_profile_id,
            "contract_sha256": self.contract_sha256,
            "search_scope": DEPLOYMENT_SCOPE,
            "descriptors_considered": self.considered,
            "resolution": self.resolution,
        }
        if self.resolution != "unique":
            entry["equivalence_class"] = list(self.class_members)
        if self.numeric_signature:
            entry["numeric_signature"] = {
                name: value for name, value in self.numeric_signature
            }
        if self.declared_input_dtypes:
            entry["kernel_declared_input_dtypes"] = list(self.declared_input_dtypes)
        return entry


# The six tables this file used to carry -- EMBED_DESCRIPTOR_IDS,
# RMS_DESCRIPTOR_IDS, TRANSFER_DESCRIPTOR_IDS, MATMUL_DESCRIPTOR_IDS,
# HEAD_RMS_DESCRIPTOR_IDS and ROPE_DESCRIPTOR_IDS -- and the descriptor IDs
# embedded in NEXT_BOUNDARIES are replaced by these identities.  Program
# counters stay: a PC is a position in the program, not a descriptor number,
# and the same PCs hold across every lowering observed.
EMBED_IDENTITIES = (
    OperatorIdentity(
        role="token_embedding",
        kernel="token_embedding",
        major=int(Major.TENSOR),
        sub=int(Tensor.EMBED_LOOKUP),
        contract=QWEN_EMBED_CONTRACT,
        unbound=UNBOUND_BINARY,
    ),
    OperatorIdentity(
        role="token_embedding",
        kernel="main.token_embed",
        major=int(Major.TENSOR),
        sub=int(Tensor.EMBED_LOOKUP),
        contract=DEEPSEEK_EMBED_CONTRACT,
        unbound=UNBOUND_BINARY,
    ),
)
RMS_IDENTITY = OperatorIdentity(
    role="attention_norm",
    kernel="layer.0.attention_norm",
    major=int(Major.VECTOR),
    sub=int(Vector.RMS_NORM),
    contract=QWEN_RMS_CONTRACT,
    unbound=UNBOUND_BINARY,
)
TRANSFER_IDENTITY = OperatorIdentity(
    role="hyper_connection_expand",
    kernel="main.hc_expand",
    major=int(Major.DMA),
    sub=int(Dma.TRANSFER),
    contract=DEEPSEEK_TRANSFER_CONTRACT,
    unbound=UNBOUND_UNARY,
)
MATMUL_PCS = (11, 14, 17)
MATMUL_IDENTITIES = tuple(
    OperatorIdentity(
        role=role,
        kernel=kernel,
        major=int(Major.TENSOR),
        sub=int(Tensor.MATMUL),
        contract=QWEN_MATMUL_CONTRACT,
        unbound=UNBOUND_BINARY,
    )
    for role, kernel in (
        ("query_projection", "layer.0.attention.query_projection"),
        ("key_projection", "layer.0.attention.key_projection"),
        ("value_projection", "layer.0.attention.value_projection"),
    )
)
HEAD_RMS_PCS = (20, 23)
HEAD_RMS_IDENTITIES = tuple(
    OperatorIdentity(
        role=role,
        kernel=kernel,
        major=int(Major.VECTOR),
        sub=int(Vector.HEAD_RMS_NORM),
        contract=QWEN_RMS_CONTRACT,
        unbound=UNBOUND_BINARY_WITH_AUX0,
        aux_0=heads,
    )
    for role, kernel, heads in (
        ("query_head_norm", "layer.0.attention.query_head_norm", Q_HEADS),
        ("key_head_norm", "layer.0.attention.key_head_norm", KV_HEADS),
    )
)


def head_rms_identities(geo: TargetGeometry) -> tuple[OperatorIdentity, ...]:
    """HEAD_RMS_NORM identities for one geometry.

    aux_0 on HEAD_RMS_NORM is the head COUNT, so these identities cannot be
    module constants once a second configuration exists.
    """
    return tuple(
        OperatorIdentity(
            role=role,
            kernel=kernel,
            major=int(Major.VECTOR),
            sub=int(Vector.HEAD_RMS_NORM),
            contract=QWEN_RMS_CONTRACT,
            unbound=UNBOUND_BINARY_WITH_AUX0,
            aux_0=heads,
        )
        for role, kernel, heads in (
            ("query_head_norm", "layer.0.attention.query_head_norm", geo.query_heads),
            ("key_head_norm", "layer.0.attention.key_head_norm", geo.kv_heads),
        )
    )
ROPE_PCS = (26, 29)
ROPE_IDENTITIES = tuple(
    OperatorIdentity(
        role=role,
        kernel=kernel,
        major=int(Major.VECTOR),
        sub=int(Vector.ROPE),
        contract=QWEN_ROPE_CONTRACT,
        unbound=UNBOUND_BINARY_WITH_AUX0,
    )
    for role, kernel in (
        ("query_rotation", "layer.0.attention.query_rotation"),
        ("key_rotation", "layer.0.attention.key_rotation"),
    )
)
# ``aux_id_0`` on ROPE is the coefficient-row stride, and the two Qwen
# lowerings choose different ones under one contract digest: the ROM bundle
# passes one head width, the HBM bundle two.  It is supplied per target rather
# than baked into the identity, so the derivation cannot silently accept the
# wrong lowering's operator.
ROPE_AUX0 = (HEAD_WIDTH, 2 * HEAD_WIDTH)
BOUNDARY_IDENTITIES = (
    BoundaryIdentity(
        pc=32,
        major=int(Major.DMA),
        sub=int(Dma.SCATTER),
        opcode="DMA.SCATTER",
        kernel="layer.0.attention.key_append",
        contract=QWEN_KV_APPEND_CONTRACT,
    ),
    BoundaryIdentity(
        pc=32,
        major=int(Major.DMA),
        sub=int(Dma.SCATTER),
        opcode="DMA.SCATTER",
        kernel="layer.0.attention.key_append",
        contract=QWEN_KV_APPEND_CONTRACT,
    ),
    BoundaryIdentity(
        pc=13,
        major=int(Major.LINK),
        sub=int(Link.MULTICAST),
        opcode="LINK.MULTICAST",
        collective_op=int(CollectiveOp.BROADCAST),
    ),
    BoundaryIdentity(
        pc=14,
        major=int(Major.VECTOR),
        sub=int(Vector.MHC),
        opcode="VECTOR.MHC",
        kernel="main.layer00.hc_attn_pre",
        contract=DEEPSEEK_HC_PRE_CONTRACT,
    ),
)


#: The fail-stop boundary and the prefix counters, keyed by TARGET rather than by
#: position in a tuple. The reduced configuration's program is structurally identical
#: to the shipped Qwen one -- same instruction count, same operator family/subopcode
#: census, same kernel ids -- so it takes the same boundary and the same counters, and
#: the builder VERIFIES both against the walk. If either is wrong it refuses and
#: reports the number it actually saw, which is how these get pinned rather than
#: guessed.
#: ORACLE PINS, per target. These are drift guards, not sources of truth: every one
#: of them is COMPUTED from the target's own deployment and checkpoint by an
#: independent reference (rms_norm_bf16 and friends), and the pin only asserts that
#: recomputing it gives the same answer. So a new target's pins can legitimately be
#: taken from its first run -- that is what "bootstrap" means here -- while a changed
#: pin on an existing target still means something moved.
#:
#: OT_A3_PREFIX_BOOTSTRAP=1 collects every pin a target is missing and prints them all
#: at the end instead of failing on the first, because each run of this builder is
#: minutes long and failing one pin at a time would take an afternoon.
import os as _os  # noqa: E402

BOOTSTRAP = _os.environ.get("OT_A3_PREFIX_BOOTSTRAP") == "1"
_BOOTSTRAP_OBSERVED: dict[str, dict[str, Any]] = {}


def oracle_pin(target_key: str, name: str, observed: Any, pinned: Any) -> bool:
    """True when ``observed`` matches the pin, or when bootstrapping a new target.

    In bootstrap mode the observation is recorded and accepted, so one run reports
    every missing pin for a new configuration at once.
    """
    if pinned is None:
        if not BOOTSTRAP:
            raise SystemExit(
                f"{target_key}: no pinned {name}; observed {observed!r}. "
                "Re-run with OT_A3_PREFIX_BOOTSTRAP=1 to collect every missing pin "
                "for this target, then add them to ORACLE_PINS."
            )
        _BOOTSTRAP_OBSERVED.setdefault(target_key, {})[name] = observed
        return True
    if observed != pinned:
        if BOOTSTRAP:
            _BOOTSTRAP_OBSERVED.setdefault(target_key, {})[name] = observed
            return True
        return False
    return True


ORACLE_PINS: dict[str, dict[str, Any]] = {
    "qwen3-8b-rom-single-chip": {
        "rms_mean_square_codes": (0x3A5BF2CA,),
        "rms_inverse_rms_codes": (0x420A0297,),
        "rms_result_sha256":
            "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58",
    },
    "qwen3-8b-hbm-single-chip": {
        "rms_mean_square_codes": (0x3A5BF2CA,),
        "rms_inverse_rms_codes": (0x420A0297,),
        "rms_result_sha256":
            "976d6de1a3ed91a066c7efed4354e578edf366a3b51a7e6077d68282981ffa58",
    },
    #: bootstrapped from this configuration's own first run
    "qwen3-reduced-rom-single-chip": {},
}


BOUNDARY_IDENTITIES_BY_TARGET: dict[str, BoundaryIdentity] = {
    "qwen3-8b-rom-single-chip": BOUNDARY_IDENTITIES[0],
    "qwen3-8b-hbm-single-chip": BOUNDARY_IDENTITIES[1],
    "qwen3-reduced-rom-single-chip": BOUNDARY_IDENTITIES[0],
    "deepseek-v4-flash-rom-wafer": BOUNDARY_IDENTITIES[2],
    "deepseek-v4-flash-hbm-cluster": BOUNDARY_IDENTITIES[3],
}

_QWEN_PREFIX_COUNTS = {
    "fetched": 33, "retired": 32, "issued": 11, "loop_iterations": 10,
    "wait_events": 9, "signals": 10, "views": 33,
}
EXPECTED_COUNTS_BY_TARGET: dict[str, dict[str, int]] = {
    "qwen3-8b-rom-single-chip": _QWEN_PREFIX_COUNTS,
    "qwen3-8b-hbm-single-chip": _QWEN_PREFIX_COUNTS,
    "qwen3-reduced-rom-single-chip": _QWEN_PREFIX_COUNTS,
    "deepseek-v4-flash-rom-wafer": {
        "fetched": 14, "retired": 13, "issued": 5, "loop_iterations": 4,
        "wait_events": 1, "signals": 4, "views": 11,
    },
    "deepseek-v4-flash-hbm-cluster": {
        "fetched": 15, "retired": 14, "issued": 5, "loop_iterations": 4,
        "wait_events": 2, "signals": 4, "views": 17,
    },
}


def _kernel_ir_index(target: Any, identity: Any) -> dict[str, Any]:
    """Load the target's Kernel IR and index it by ``kernel_id``.

    ``certified_deployment_identity`` has already bound this file's SHA-256
    through the deployment certificate and checked its graph and model IDs;
    both are re-checked here so a derivation can never read a Kernel IR that
    does not belong to the bundle it is resolving against.
    """
    path = ROOT / target.kernel_ir
    payload = path.read_bytes()
    document = json.loads(payload)
    if document.get("schema") != "opentallas.tensor_kernel_ir.v3":
        raise SystemExit(f"{target.key}: {target.kernel_ir} is not Kernel IR v3")
    if document.get("graph_id") != identity.graph_id:
        raise SystemExit(
            f"{target.key}: {target.kernel_ir} graph {document.get('graph_id')!r} "
            f"is not the certified graph {identity.graph_id!r}"
        )
    if document.get("model_id") != identity.model_id:
        raise SystemExit(
            f"{target.key}: {target.kernel_ir} model {document.get('model_id')!r} "
            f"is not the certified model {identity.model_id!r}"
        )
    kernels = document.get("kernels")
    if not isinstance(kernels, list):
        raise SystemExit(f"{target.key}: {target.kernel_ir} has no kernel list")
    by_id: dict[str, list[dict[str, Any]]] = {}
    for kernel in kernels:
        if isinstance(kernel, dict) and isinstance(kernel.get("kernel_id"), str):
            by_id.setdefault(kernel["kernel_id"], []).append(kernel)
    tensors = document.get("tensors")
    tensor_dtype: dict[str, str] = {}
    if isinstance(tensors, list):
        for tensor in tensors:
            if isinstance(tensor, dict) and isinstance(tensor.get("tensor_id"), str):
                tensor_dtype[tensor["tensor_id"]] = str(tensor.get("dtype"))
    return {
        "path": target.kernel_ir,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "graph_id": document.get("graph_id"),
        "model_id": document.get("model_id"),
        "by_id": by_id,
        "tensor_dtype": tensor_dtype,
        "kernel_count": len(kernels),
    }


def _kernel_input_dtypes(
    kernel_ir: dict[str, Any], kernel: dict[str, Any]
) -> list[int | None]:
    """The dtypes the Kernel IR declares for one kernel's inputs, in order.

    The ordered input list is the graph's own statement of which operand is
    which.  A NUMERIC descriptor whose ``input_dtype`` and
    ``second_input_dtype`` do not follow it has inverted its operands, and
    that is a fact about the lowering rather than a matter of taste.
    """
    inputs = kernel.get("inputs")
    if not isinstance(inputs, list):
        return []
    return [
        KERNEL_IR_DTYPES.get(kernel_ir["tensor_dtype"].get(str(name), ""))
        for name in inputs
    ]


def _governed_kernel(
    kernel_ir: dict[str, Any], kernel_id: str, label: str
) -> dict[str, Any]:
    matches = kernel_ir["by_id"].get(kernel_id, [])
    if len(matches) != 1:
        raise SystemExit(
            f"{label}: {kernel_ir['path']} names {len(matches)} kernels "
            f"{kernel_id!r}; an identity must select exactly one kernel"
        )
    return matches[0]


def _numeric_signature(payload: Any) -> tuple[tuple[str, int], ...]:
    return tuple((name, int(payload[name])) for name in NUMERIC_SIGNATURE_FIELDS)


def _operator_candidates(
    deployment: Any,
    *,
    kernel_index: int,
    major: int,
    sub: int,
    contract: bytes,
    aux_0: int | None,
    unbound: tuple[str, ...],
) -> tuple[list[tuple[int, int, Any]], int]:
    candidates: list[tuple[int, int, Any]] = []
    considered = 0
    for descriptor_id, descriptor in enumerate(deployment.table.descriptors()):
        if int(descriptor.descriptor_type) != int(ExtendedDescriptorType.OPERATOR):
            continue
        considered += 1
        payload = descriptor.payload
        if int(payload["source_kernel_id"]) != kernel_index:
            continue
        if int(payload["engine_family"]) != major or int(payload["engine_sub"]) != sub:
            continue
        numeric_id = int(payload["numeric_profile_id"])
        if numeric_id == NO_ID:
            continue
        numeric = deployment.table.get(numeric_id, ExtendedDescriptorType.NUMERIC)
        if bytes(numeric.payload["contract_digest"]) != contract:
            continue
        if aux_0 is not None and int(payload["aux_id_0"]) != aux_0:
            continue
        if any(int(payload[slot]) != NO_ID for slot in unbound):
            continue
        candidates.append((descriptor_id, numeric_id, numeric))
    return candidates, considered


def resolve_operator(
    deployment: Any,
    kernel_ir: dict[str, Any],
    identity: OperatorIdentity,
    *,
    target_key: str,
    aux_0: int | None = None,
) -> Resolution:
    """Derive one governed operation's descriptor ID from its identity.

    Refuses loudly, naming the ambiguity, when the identity selects anything
    other than exactly one descriptor.  That refusal is the point: the whole
    reason this function exists is that a number cannot tell you whether it
    still means the operation it meant three lowerings ago.
    """
    label = f"{target_key}: {identity.role}"
    kernel = _governed_kernel(kernel_ir, identity.kernel, label)
    kernel_index = int(kernel["index"])
    declared = kernel.get("numeric_contract")
    if hashlib.sha256(str(declared).encode()).digest() != identity.contract:
        raise SystemExit(
            f"{label}: Kernel IR kernel {identity.kernel!r} declares numeric "
            f"contract {declared!r}, whose digest is not the "
            f"{identity.contract.hex()[:16]}... this derivation names"
        )
    expected_aux = identity.aux_0 if aux_0 is None else aux_0
    candidates, considered = _operator_candidates(
        deployment,
        kernel_index=kernel_index,
        major=identity.major,
        sub=identity.sub,
        contract=identity.contract,
        aux_0=expected_aux,
        unbound=identity.unbound,
    )
    if len(candidates) != 1:
        why = (
            "no descriptor in this bundle is that operation, and absence of a "
            "derivation is a refusal, not a pass"
            if not candidates
            else "an operation that cannot be told apart from another one is "
            "not evidence about either"
        )
        raise SystemExit(
            f"{label}: identity (kernel {identity.kernel!r} index "
            f"{kernel_index}, opcode {identity.major:#04x}.{identity.sub:#04x}, "
            f"contract {identity.contract.hex()[:16]}, aux_id_0 "
            f"{expected_aux!r}) selects {len(candidates)} of {considered} "
            f"OPERATOR descriptors "
            f"{[entry[0] for entry in candidates]}; {why}"
        )
    descriptor_id, numeric_id, numeric = candidates[0]
    return Resolution(
        role=identity.role,
        kernel=identity.kernel,
        kernel_index=kernel_index,
        descriptor_id=descriptor_id,
        numeric_profile_id=numeric_id,
        numeric_signature=_numeric_signature(numeric.payload),
        contract_sha256=identity.contract.hex(),
        resolution="unique",
        class_members=(descriptor_id,),
        considered=considered,
    )


def resolve_boundary(
    deployment: Any,
    kernel_ir: dict[str, Any],
    identity: BoundaryIdentity,
    *,
    target_key: str,
    observed_descriptor_id: int,
) -> Resolution:
    """Derive the fail-stop boundary instruction's descriptor by identity.

    Boundary descriptors are not always separable.  ``LINK.MULTICAST`` on the
    DeepSeek ROM wafer lowers to three COMMUNICATION descriptors that are
    byte-identical in every payload field, so no identity can single one out
    and the honest derivation is the whole equivalence class: the observed
    descriptor must be a member, the class must be non-empty, and the record
    says the class has more than one member rather than implying a unique
    derivation it does not have.
    """
    label = f"{target_key}: fail-stop boundary {identity.opcode}"
    if identity.kernel is not None:
        kernel = _governed_kernel(kernel_ir, identity.kernel, label)
        kernel_index = int(kernel["index"])
        declared = kernel.get("numeric_contract")
        if hashlib.sha256(str(declared).encode()).digest() != identity.contract:
            raise SystemExit(
                f"{label}: Kernel IR kernel {identity.kernel!r} declares "
                f"numeric contract {declared!r}, which is not the contract "
                "this derivation names"
            )
        candidates, considered = _operator_candidates(
            deployment,
            kernel_index=kernel_index,
            major=identity.major,
            sub=identity.sub,
            contract=identity.contract,
            aux_0=None,
            unbound=(),
        )
        declared_inputs = _kernel_input_dtypes(kernel_ir, kernel)
        members = tuple(entry[0] for entry in candidates)
        numeric_id: int | None = None
        signature: tuple[tuple[str, int], ...] = ()
        for entry in candidates:
            if entry[0] == observed_descriptor_id:
                numeric_id = entry[1]
                signature = _numeric_signature(entry[2].payload)
    else:
        kernel_index = None
        members_list: list[int] = []
        considered = 0
        for descriptor_id, descriptor in enumerate(deployment.table.descriptors()):
            if int(descriptor.descriptor_type) != int(
                ExtendedDescriptorType.COMMUNICATION
            ):
                continue
            considered += 1
            if int(descriptor.payload["collective_op"]) != identity.collective_op:
                continue
            members_list.append(descriptor_id)
        members = tuple(members_list)
        numeric_id = None
        signature = ()
        declared_inputs = []
    if not members:
        raise SystemExit(
            f"{label}: identity selects no descriptor at all in "
            f"{deployment.table.digest.hex()[:16]}...; absence of a derivation "
            "is a refusal, not a pass"
        )
    if observed_descriptor_id not in members:
        raise SystemExit(
            f"{label}: PC {identity.pc} names descriptor "
            f"{observed_descriptor_id}, which is not in the derived identity "
            f"class {list(members)}"
        )
    if len(members) > 1:
        print(
            f"AMBIGUOUS {label}: identity class has {len(members)} members "
            f"{list(members)}, byte-identical under every field the identity "
            "can read; the boundary descriptor ID is recorded as a class "
            "member, not as a unique derivation",
            file=sys.stderr,
        )
    return Resolution(
        declared_input_dtypes=tuple(declared_inputs),
        role=f"boundary.{identity.opcode}",
        kernel=identity.kernel,
        kernel_index=kernel_index,
        # A singleton class IS the derivation; a larger one is only checked
        # for membership, and the record says which of the two happened.
        descriptor_id=members[0] if len(members) == 1 else observed_descriptor_id,
        numeric_profile_id=numeric_id,
        numeric_signature=signature,
        contract_sha256=identity.contract.hex() if identity.contract else None,
        resolution="unique" if len(members) == 1 else "equivalence_class",
        class_members=members,
        considered=considered,
    )


def resolve_governed_descriptors(
    deployment: Any,
    kernel_ir: dict[str, Any],
    *,
    target_key: str,
    target_index: int,
    geo: "TargetGeometry",
) -> dict[str, Resolution]:
    """Derive every governed descriptor ID for one lowering, up front.

    The derivation runs against this target's own bundle before the program
    is walked, so it cannot be contaminated by the instruction stream it is
    later used to check.  The walk then asserts that each governed
    instruction names the descriptor the identity derived.
    """
    #: The MODEL decides the identity set now, not the target's position.
    model_index = geo.model_index
    resolved: dict[str, Resolution] = {
        "embed": resolve_operator(
            deployment,
            kernel_ir,
            EMBED_IDENTITIES[model_index],
            target_key=target_key,
        )
    }
    if model_index == 0:
        resolved["rms"] = resolve_operator(
            deployment, kernel_ir, RMS_IDENTITY, target_key=target_key
        )
        for index, identity in enumerate(MATMUL_IDENTITIES):
            resolved[f"matmul.{index}"] = resolve_operator(
                deployment, kernel_ir, identity, target_key=target_key
            )
        for index, identity in enumerate(head_rms_identities(geo)):
            resolved[f"head_rms.{index}"] = resolve_operator(
                deployment, kernel_ir, identity, target_key=target_key
            )
        for index, identity in enumerate(ROPE_IDENTITIES):
            resolved[f"rope.{index}"] = resolve_operator(
                deployment,
                kernel_ir,
                identity,
                target_key=target_key,
                aux_0=geo.rope_aux0,
            )
    else:
        resolved["transfer"] = resolve_operator(
            deployment, kernel_ir, TRANSFER_IDENTITY, target_key=target_key
        )
    return resolved


def _audit_contract_agreement(
    observations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Name every contract digest that does not bind one numeric contract.

    Two descriptors may carry one ``contract_digest`` and still declare
    different numeric payloads.  When that happens the digest is not binding
    what it claims to bind, and the two lowerings do not implement one
    contract however identical their digests look.  Executed operations are
    refused outright; the fail-stop boundary is recorded, loudly, because the
    prefix never executes it -- and the record says so rather than leaving a
    reader to assume agreement.
    """
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in observations:
        if entry["contract_sha256"] is None or not entry["numeric_signature"]:
            continue
        by_key.setdefault((entry["role"], entry["contract_sha256"]), []).append(entry)
    disagreements: list[dict[str, Any]] = []
    for (role, contract), entries in sorted(by_key.items()):
        signatures = {entry["numeric_signature"] for entry in entries}
        if len(signatures) < 2:
            continue
        differing = sorted(
            {
                name
                for signature in signatures
                for name, value in signature
                if any(dict(other).get(name) != value for other in signatures)
            }
        )
        disagreements.append(
            {
                "role": role,
                "contract_sha256": contract,
                "executed": entries[0]["executed"],
                "differing_fields": differing,
                "per_target": [
                    {
                        "target": entry["target"],
                        "descriptor_id": entry["descriptor_id"],
                        "numeric_profile_id": entry["numeric_profile_id"],
                        "numeric_signature": dict(entry["numeric_signature"]),
                        "kernel_declared_input_dtypes": entry[
                            "kernel_declared_input_dtypes"
                        ],
                    }
                    for entry in entries
                ],
                "finding": (
                    "one contract digest, two numeric contracts: the digest "
                    "does not bind the fields listed in differing_fields"
                ),
            }
        )
    executed = [entry for entry in disagreements if entry["executed"]]
    if executed:
        raise SystemExit(
            "governed operations disagree on their numeric contract across "
            "lowerings under one contract digest: "
            + json.dumps(executed, sort_keys=True)
        )
    for entry in disagreements:
        print(
            f"CONTRACT DISAGREEMENT {entry['role']} digest "
            f"{entry['contract_sha256'][:16]}... differs at "
            f"{', '.join(entry['differing_fields'])} across "
            + ", ".join(item["target"] for item in entry["per_target"]),
            file=sys.stderr,
        )
    return disagreements

def _bound_input_dtypes(
    deployment: Any, descriptor_id: int
) -> list[int | None]:
    """The dtypes of the views an OPERATOR descriptor binds to in0 and in1.

    This reads the *emitted descriptor*, not the graph it came from: the
    dtype is taken from the TENSOR_VIEW each input slot actually names.  It
    is therefore a measurement of what the lowering produced, which is what
    an engine will read.
    """
    try:
        operator = deployment.table.get(
            descriptor_id, ExtendedDescriptorType.OPERATOR
        )
    except Exception:
        return []
    bound: list[int | None] = []
    for slot in range(2):
        view_id = int(operator.payload.get(f"input_view_{slot}", NO_ID))
        if view_id == NO_ID:
            bound.append(None)
            continue
        view = deployment.table.get(view_id, ExtendedDescriptorType.TENSOR_VIEW)
        bound.append(int(view.payload["dtype"]))
    return bound


#: The numeric-profile field that describes each ABI input slot.  This is not
#: a convention this file chose: every engine that reads the fields --
#: ``runtime/sim/engines/tensor.py`` and ``runtime/sim/engines/vector.py``,
#: twenty call sites, no exception -- checks ``profile.input_dtype`` against
#: ``ctx.input_view(operator, 0)`` and ``profile.second_input_dtype`` against
#: ``ctx.input_view(operator, 1)``.
_SLOT_DTYPE_FIELDS = ("input_dtype", "second_input_dtype")


def _audit_profile_slot_agreement(
    observations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Name every descriptor whose numeric profile contradicts its own views.

    The cross-lowering check above can only see a disagreement when the two
    backends differ.  It is blind, by construction, to a descriptor that is
    wrong the *same* way on both -- and that is not hypothetical: the
    DeepSeek pair carries 29 field-level cases where both lowerings declare
    an index operand's dtype as I32 over a U32 view, which no comparison of
    the two can detect.  This check needs no second lowering: a descriptor
    that says ``input_dtype = BF16`` while binding a U32 view in ``in0``
    contradicts itself, and one artifact is enough to say so.

    Executed operations are refused outright.  Anything else is recorded and
    printed, on the same reasoning ``_audit_contract_agreement`` uses for the
    fail-stop boundary: the prefix never runs it, so the honest record says
    what was observed rather than raising on an operation it did not execute.
    """
    findings: list[dict[str, Any]] = []
    for entry in observations:
        signature = dict(entry["numeric_signature"])
        bound = entry.get("bound_input_dtypes") or []
        if not signature or not bound:
            continue
        differing = [
            {
                "slot": slot,
                "field": field,
                "profile_says": int(signature[field]),
                "view_is": int(bound[slot]),
            }
            for slot, field in enumerate(_SLOT_DTYPE_FIELDS)
            if slot < len(bound)
            and bound[slot] is not None
            and field in signature
            and int(signature[field]) != int(bound[slot])
        ]
        if not differing:
            continue
        findings.append(
            {
                "target": entry["target"],
                "role": entry["role"],
                "executed": entry["executed"],
                "descriptor_id": entry["descriptor_id"],
                "numeric_profile_id": entry["numeric_profile_id"],
                "differing_slots": differing,
                "finding": (
                    "the numeric profile does not describe the operand views "
                    "this descriptor binds; input_dtype describes "
                    "input_view_0 and second_input_dtype input_view_1, which "
                    "is what every engine that reads them checks"
                ),
            }
        )
    executed = [entry for entry in findings if entry["executed"]]
    if executed:
        raise SystemExit(
            "governed operations carry a numeric profile that contradicts "
            "the operand views they bind: " + json.dumps(executed, sort_keys=True)
        )
    for entry in findings:
        slots = ", ".join(
            f"in{item['slot']} {item['field']} says "
            f"{DType(item['profile_says']).name} over a "
            f"{DType(item['view_is']).name} view"
            for item in entry["differing_slots"]
        )
        print(
            f"PROFILE/VIEW DISAGREEMENT {entry['target']} {entry['role']} "
            f"descriptor {entry['descriptor_id']}: {slots}",
            file=sys.stderr,
        )
    return findings


INPUT_IMAGES = (
    "a3_program.hex",
    "a3_descriptor.hex",
    "a3_symbol.hex",
)
OUTPUT_IMAGES = (
    "p3_case.hex",
    "p3_issue.hex",
    "p3_index.hex",
    "p3_source.hex",
    "p3_expect.hex",
    "p3_writes.hex",
    "p3_meta.hex",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex_lines(values: list[int], width: int = 32, total: int | None = None) -> str:
    if total is not None:
        if len(values) > total:
            raise SystemExit(
                f"image has {len(values)} words, exceeds its {total}-word RTL bound"
            )
        values = values + [0] * (total - len(values))
    digits = width // 4
    return "".join(f"{value & ((1 << width) - 1):0{digits}x}\n" for value in values)


def _deployment_vectors() -> tuple[dict[str, Any], list[int]]:
    if not DEPLOYMENT_VECTOR_JSON.is_file():
        raise SystemExit(
            "the shipped deployment vector set is missing; run "
            "tools/build_abi3_deployment_rtl_vectors.py"
        )
    vectors = json.loads(DEPLOYMENT_VECTOR_JSON.read_text(encoding="utf-8"))
    if vectors.get("schema") != "opentallas.rtl.abi3_deployment_vectors.v1":
        raise SystemExit("the shipped deployment vector set has an unknown schema")
    if vectors.get("prompt_tokens") != PROMPT_TOKENS:
        raise SystemExit(
            f"the shipped vector request has {vectors.get('prompt_tokens')} prompt "
            f"tokens; this witness requires {PROMPT_TOKENS}"
        )
    for name in INPUT_IMAGES:
        expected = vectors.get("image_sha256", {}).get(name)
        actual = _sha256_file(DEPLOYMENT_VECTOR_DIR / name)
        if actual != expected:
            raise SystemExit(
                f"{name} is not the image bound by {DEPLOYMENT_VECTOR_JSON}"
            )
    case_path = DEPLOYMENT_VECTOR_DIR / "a3_deployment_case.hex"
    expected_case = vectors.get("image_sha256", {}).get(case_path.name)
    if _sha256_file(case_path) != expected_case:
        raise SystemExit("the shipped deployment case image is stale")
    case_words = [
        int(line, 16)
        for line in case_path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]
    if len(case_words) != len(vectors["cases"]) * DEPLOYMENT_CASE_STRIDE:
        raise SystemExit("the shipped deployment case image has the wrong length")
    return vectors, case_words


def _resolved_views(
    deployment: Deployment,
    operator_id: int,
    loops: dict[int, int],
    symbols: dict[int, int],
    *,
    major: int,
) -> list[dict[str, Any]]:
    if major == int(Major.LINK):
        # LINK descriptors are COMMUNICATION records, not OPERATOR records,
        # and do not own tensor-view operands at the sequencer boundary.
        return []
    operator = deployment.table.get(operator_id, ExtendedDescriptorType.OPERATOR)
    resolver = ViewResolver(deployment, None)  # resolution does not read memory
    out: list[dict[str, Any]] = []
    fields = (
        "input_view_0",
        "input_view_1",
        "input_view_2",
        "input_view_3",
        "output_view_0",
        "output_view_1",
    )
    for slot, field in enumerate(fields):
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        resolved = resolver.resolve(view_id, loops, symbols)
        out.append(
            {
                "slot": slot,
                "descriptor_id": view_id,
                "object_id": int(resolved.object_id),
                "dtype": int(resolved.dtype),
                "dims": [int(value) for value in resolved.dims],
                "strides": [int(value) for value in resolved.strides],
                "element_offset": int(resolved.element_offset),
                "extent_axis": int(resolved.extent_axis),
                "extent": int(resolved.dims[resolved.extent_axis]),
            }
        )
    return out


def _loop_trip(payload: dict[str, Any], symbols: dict[int, int]) -> int:
    kind = int(payload["bound_selector_kind"])
    lower = int(payload["lower_bound"])
    step = int(payload["step"])
    if step <= 0:
        raise SystemExit("shipped prefix contains a non-positive loop step")
    if kind == int(SelectorKind.CONSTANT):
        upper = int(payload["upper_bound"])
    elif kind == int(SelectorKind.RUNTIME_SYMBOL):
        symbol = int(payload["bound_symbol_id"])
        if symbol not in symbols:
            raise SystemExit(f"shipped prefix loop names unbound symbol {symbol}")
        divisor = max(int(payload["bound_divisor"]), 1)
        upper = (int(symbols[symbol]) + divisor - 1) // divisor
    else:
        raise SystemExit("shipped prefix loop uses an unsupported selector")
    span = max(upper - lower, 0)
    return (span + step - 1) // step


def _generated_row(
    deployment: Deployment,
    object_id: int,
    index: int,
    trailing: int,
    cache: dict[tuple[str, int, int], bytes],
) -> tuple[bytes, dict[str, Any]]:
    """Materialise one generator row without allocating its complete table.

    The DeepSeek coefficient object is 128 MiB.  Generating all 262,144 rows
    to retain the one 512-byte row this RTL witness reads would make a focused
    vector rebuild contend with model-capture jobs.  These expressions are the
    selected-row forms of ``runtime.sim.generators`` and are source-bound by
    the campaign.  The retained row hashes remain byte-identical to the normal
    full-object generator boundary.
    """
    source = deployment.objects[object_id]
    if source.kind != "generated":
        raise SystemExit(
            f"source object {object_id} is {source.kind}, expected generated"
        )
    key = (source.digest, index, trailing)
    row = cache.get(key)
    if row is None:
        parameters = source.parameters
        if source.generator == "rope_coefficients_v1":
            head_dim = int(parameters["head_dim"])
            if trailing != 2 * head_dim:
                raise SystemExit("Qwen generated-row width changed")
            half = head_dim // 2
            theta = float(parameters["theta"])
            inverse = np.array(
                [
                    1.0 / (theta ** ((2.0 * channel) / head_dim))
                    for channel in range(half)
                ],
                dtype=np.float64,
            )
            angles = np.float64(index) * inverse
            cosine = np.cos(angles)
            sine = np.sin(angles)
            values = np.empty(trailing, dtype=np.float64)
            values[:half] = cosine
            values[half:head_dim] = cosine
            values[head_dim : head_dim + half] = sine
            values[head_dim + half :] = sine
            row = np.ascontiguousarray(values, dtype=np.float32).tobytes()
        elif source.generator == "deepseek_rope_coefficients_v1":
            rotary_width = int(parameters["rotary_width"])
            if trailing != 2 * rotary_width:
                raise SystemExit("DeepSeek generated-row width changed")
            frequencies = _rope_frequencies_binary32(
                parameters,
                rotary_width=rotary_width,
                theta=float(parameters["theta"]),
                scaling=str(parameters["position_scaling"]),
            )
            angles = np.asarray(np.float32(index) * frequencies, dtype=np.float32)
            cosine = np.asarray(
                np.cos(np.asarray(angles, dtype=np.float64)), dtype=np.float32
            )
            sine = np.asarray(
                np.sin(np.asarray(angles, dtype=np.float64)), dtype=np.float32
            )
            values = np.empty(trailing, dtype=np.float32)
            values[0:rotary_width:2] = cosine
            values[1:rotary_width:2] = cosine
            values[rotary_width::2] = sine
            values[rotary_width + 1 :: 2] = sine
            row = np.ascontiguousarray(values, dtype=np.float32).tobytes()
        else:
            raise SystemExit(f"unsupported selected-row generator {source.generator!r}")
        cache[key] = row
    if len(row) != trailing * 4:
        raise SystemExit("generated source row has the wrong byte count")
    return row, {
        "object_id": object_id,
        "kind": source.kind,
        "generator": source.generator,
        "parameters": dict(source.parameters),
        "object_sha256": source.digest,
        "row_index": index,
        "row_bytes": len(row),
        "row_sha256": hashlib.sha256(row).hexdigest(),
    }


def _checkpoint_row(
    target: Any,
    deployment: Deployment,
    object_id: int,
    token: int,
    width: int,
) -> tuple[bytes, dict[str, Any]]:
    """Read one BF16 row from the exact segment named by the deployment.

    This deliberately performs a bounded 8 KiB read.  The deployment and its
    retained certificate bind the complete segment digest; this witness binds
    the selected bytes again by their own SHA-256, but does not rescan a 1--4
    GiB checkpoint shard while another model-capture process is live.
    """
    source = deployment.objects[object_id]
    if source.kind != "segments":
        raise SystemExit(
            f"embedding object {object_id} is {source.kind}, expected segments"
        )
    row_bytes = width * 2
    logical_start = token * row_bytes
    logical_stop = logical_start + row_bytes
    cursor = 0
    selected = None
    selected_local = 0
    for segment in source.segments:
        stop = cursor + int(segment.bytes)
        if cursor <= logical_start and logical_stop <= stop:
            selected = segment
            selected_local = logical_start - cursor
            break
        cursor = stop
    if selected is None:
        raise SystemExit(
            f"embedding row {token} spans or exceeds declared source segments"
        )
    root = Path(target.checkpoint).expanduser()
    path = resolve_path(root, selected.path)
    file_offset = int(selected.offset) + selected_local
    if file_offset + row_bytes > path.stat().st_size:
        raise SystemExit("selected embedding row exceeds its checkpoint shard")
    with path.open("rb") as handle:
        handle.seek(file_offset)
        row = handle.read(row_bytes)
    if len(row) != row_bytes:
        raise SystemExit("checkpoint returned a short embedding row")
    memory = deployment.table.get(object_id, ExtendedDescriptorType.MEMORY_OBJECT)
    object_digest = bytes(memory.payload["content_digest"]).hex()
    if not object_digest or object_digest == "00" * 32:
        raise SystemExit("embedding MEMORY_OBJECT has no content digest")
    return row, {
        "object_id": object_id,
        "object_content_sha256": object_digest,
        "checkpoint_revision": root.name,
        "shard": selected.path,
        "declared_segment_offset": int(selected.offset),
        "declared_segment_bytes": int(selected.bytes),
        "declared_segment_sha256": str(selected.sha256),
        "selected_token_id": token,
        "selected_row_logical_offset": logical_start,
        "selected_row_segment_offset": selected_local,
        "selected_row_file_offset": file_offset,
        "selected_row_bytes": row_bytes,
        "selected_row_file_range": {
            "start": file_offset,
            "stop_exclusive": file_offset + row_bytes,
        },
        "selected_row_sha256": hashlib.sha256(row).hexdigest(),
        "authentication_boundary": (
            "only this selected byte range was re-read and hashed; complete "
            "segment identity and its declared SHA-256 are bound by the "
            "certified deployment but the complete segment was not rehashed"
        ),
    }


def _checkpoint_matrix(
    target: Any,
    deployment: Deployment,
    object_id: int,
    *,
    rows: int,
    columns: int,
    cache: dict[str, bytes],
) -> tuple[bytes, dict[str, Any]]:
    """Read and authenticate one complete BF16 matrix source segment.

    Each admitted Qwen projection consumes every weight in its selected
    layer-zero segment.  Unlike the bounded embedding and RMS gain probes,
    retaining only a row would not cover the operation.  The complete segment
    is therefore read, its declared digest is independently recomputed, and
    replay stages those same bytes from the checkpoint rather than committing
    duplicate model-weight artifacts to Git.
    """

    source = deployment.objects[object_id]
    if source.kind != "segments" or not source.segments:
        raise SystemExit(
            f"matrix object {object_id} is {source.kind}, expected segments"
        )
    matrix_bytes = rows * columns * 2
    segment = source.segments[0]
    if int(segment.bytes) != matrix_bytes:
        raise SystemExit(
            f"matrix object {object_id} first segment has {segment.bytes} "
            f"bytes, expected {matrix_bytes}"
        )
    declared_sha256 = str(segment.sha256)
    payload = cache.get(declared_sha256)
    root = Path(target.checkpoint).expanduser()
    path = resolve_path(root, segment.path)
    file_offset = int(segment.offset)
    if file_offset + matrix_bytes > path.stat().st_size:
        raise SystemExit("selected matrix exceeds its checkpoint shard")
    if payload is None:
        with path.open("rb") as handle:
            handle.seek(file_offset)
            payload = handle.read(matrix_bytes)
        if len(payload) != matrix_bytes:
            raise SystemExit("checkpoint returned a short matrix segment")
        observed_sha256 = hashlib.sha256(payload).hexdigest()
        if observed_sha256 != declared_sha256:
            raise SystemExit(
                "complete matrix segment differs from its deployment digest"
            )
        cache[declared_sha256] = payload
    memory = deployment.table.get(object_id, ExtendedDescriptorType.MEMORY_OBJECT)
    object_digest = bytes(memory.payload["content_digest"]).hex()
    if not object_digest or object_digest == "00" * 32:
        raise SystemExit("matrix MEMORY_OBJECT has no content digest")
    return payload, {
        "object_id": object_id,
        "object_content_sha256": object_digest,
        "checkpoint": str(target.checkpoint),
        "checkpoint_revision": root.name,
        "shard": segment.path,
        "declared_segment_offset": file_offset,
        "declared_segment_bytes": matrix_bytes,
        "declared_segment_sha256": declared_sha256,
        "selected_matrix_shape": [rows, columns],
        "selected_matrix_dtype": "BF16",
        "selected_matrix_file_range": {
            "start": file_offset,
            "stop_exclusive": file_offset + matrix_bytes,
        },
        "selected_matrix_sha256": hashlib.sha256(payload).hexdigest(),
        "authentication_boundary": (
            "the complete selected source segment was re-read and hashed; "
            f"all {rows * columns:,} BF16 codes are consumed by the RTL "
            "operation"
        ),
    }



# ---------------------------------------------------------------------------
# Rung G1e's golden artifacts, and the paged weight window's segment map.
#
# Everything below is derived from records the reference model produced when
# these vectors were built -- the issue stream, the resolved views, the
# expected result image and each operation's declared output view.  No RTL
# run is read.  The three files are what the verification top's checker
# consumes to run the whole workload's CONTROL path with the engine results
# injected at the engine result boundary, and to compare the RTL's issue
# trace against the model's element for element.
# ---------------------------------------------------------------------------
ISSUE_STRIDE = 4

# The elements the golden trace carries.  Gate G1e requires the opcode, the
# descriptor ids, the resolved view ids and addresses, the schedule id and the
# issue serial.  The first four are recorded by the reference model and are
# here.  ``queue`` (the schedule id the SCHEDULE record selects) and
# ``serial`` (the sequencer's program-order retirement serial) are emitted by
# the RTL but the reference model does not compute either, so they are not in
# this header and the checker reports them as NOT compared.
GOLDEN_ISSUE_FIELDS = ("family", "sub", "descriptor_id", "pc")
GOLDEN_VIEW_FIELDS = (
    "slot",
    "descriptor_id",
    "extent",
    "extent_axis",
    "element_offset",
    "rank",
)


def _read_hex_words(path: Path) -> list[int]:
    return [int(token, 16) for token in path.read_text().split()]


def _g1e_output_words(operation: dict[str, Any]) -> int:
    dims = operation["output_view"]["dims"]
    count = 1
    for dim in dims:
        count *= int(dim)
    return count


def emit_weight_window(vectors: dict[str, Any], destination: Path) -> int:
    """Map the addressed weight image onto the real checkpoint shards."""

    lines = [
        "# <image_base> <bytes> <file_offset> <shard path>",
        "# segments of the checkpoint itself; the window pages them in and "
        "holds a bounded working set, never the image",
    ]
    total = 0
    matmuls = [
        operation
        for operation in vectors["cases"][0]["supported_prefix"]
        if operation["kind"] == "tensor_matmul"
    ]
    for operation in matmuls:
        source = operation["weight_source"]
        base = int(operation["staged_weight_base_words"]) * 2
        if base != total:
            raise SystemExit(
                f"weight image is not contiguous at byte {total}: the "
                f"operation at PC {operation['pc']} declares base {base}"
            )
        shard = Path(source["checkpoint"]).expanduser() / source["shard"]
        lines.append(
            f"{base} {int(source['declared_segment_bytes'])} "
            f"{int(source['declared_segment_offset'])} {shard}"
        )
        total += int(source["declared_segment_bytes"])
    declared = int(vectors["staged_matmul_weight_layout"]["bytes"])
    if total != declared:
        raise SystemExit(
            f"weight window maps {total} bytes, the vector set declares "
            f"{declared}"
        )
    destination.write_text("\n".join(lines) + "\n", encoding="ascii")
    return total


def emit_golden(vectors: dict[str, Any], vector_dir: Path, out_dir: Path
                ) -> dict[str, int]:
    cases = _read_hex_words(vector_dir / "p3_case.hex")
    issues = _read_hex_words(vector_dir / "p3_issue.hex")
    # The golden RESULT stream is the WRITE stream, not the retained image:
    # a buffer the program rewrites holds only its last value in the image, so
    # replaying the image would hand a later operator's value to the earlier
    # one that actually wrote there.
    writes = _read_hex_words(vector_dir / "p3_writes.hex")
    write_cursor = 0

    trace_lines = [
        "FIELDS ISSUE " + " ".join(GOLDEN_ISSUE_FIELDS),
        "FIELDS VIEW " + " ".join(GOLDEN_VIEW_FIELDS),
    ]
    result_lines = [
        "# RESULT <family> <sub> <descriptor_id> <pc> <fault> <trap_class> "
        "<word count>, then that many WORD <address> <data> lines",
    ]
    issue_count = 0
    view_count = 0
    word_count = 0

    for index, case in enumerate(vectors["cases"]):
        record = cases[index * CASE_STRIDE : (index + 1) * CASE_STRIDE]
        response_base = record[31]
        response_count = record[21]
        output_base = record[13]

        views_by_pc: dict[int, list[dict[str, Any]]] = {}
        for view in case["resolved_prefix_views"]:
            views_by_pc.setdefault(int(view["pc"]), []).append(view)

        operations = list(case["supported_prefix"])
        operation_pcs = [int(operation["pc"]) for operation in operations]
        if len(set(operation_pcs)) != len(operation_pcs):
            raise SystemExit(
                "this generator groups resolved views by PC, and a PC repeats "
                "in the issue stream: the reference model must emit views per "
                "ISSUE before a looping program can be given a golden trace"
            )

        case_written = 0
        for position in range(response_count):
            offset = (response_base + position) * ISSUE_STRIDE
            opcode = issues[offset]
            family = (opcode >> 8) & 0xFF
            sub = opcode & 0xFF
            descriptor_id = issues[offset + 1]
            pc = issues[offset + 2]
            trap_class = issues[offset + 3]

            trace_lines.append(f"ISSUE {family} {sub} {descriptor_id} {pc}")
            issue_count += 1
            for view in sorted(views_by_pc.get(pc, []),
                               key=lambda entry: int(entry["slot"])):
                trace_lines.append(
                    "VIEW "
                    f"{int(view['slot'])} {int(view['descriptor_id'])} "
                    f"{int(view['extent'])} {int(view['extent_axis'])} "
                    f"{int(view['element_offset'])} {len(view['dims'])}"
                )
                view_count += 1

            operation = None
            for candidate in operations:
                if int(candidate["pc"]) == pc:
                    operation = candidate
                    break
            words = _g1e_output_words(operation) if operation is not None else 0
            fault = 1 if trap_class != 0 else 0
            result_lines.append(
                f"RESULT {family} {sub} {descriptor_id} {pc} {fault} "
                f"{trap_class} {words}"
            )
            for _ in range(words):
                if write_cursor + 2 > len(writes):
                    raise SystemExit(
                        f"case {index}: the golden write stream ran out while "
                        "replaying the issue stream"
                    )
                address = writes[write_cursor]
                value = writes[write_cursor + 1]
                write_cursor += 2
                result_lines.append(f"WORD {address} {value}")
            word_count += words
            case_written += words

        if case_written != record[15]:
            raise SystemExit(
                f"case {index} golden results cover {case_written} words, "
                f"the vector set declares {record[15]}"
            )

    if write_cursor != len(writes):
        raise SystemExit(
            f"the golden write stream has {len(writes) // 2} writes and the "
            f"issue stream replayed {write_cursor // 2}"
        )
    (out_dir / "p3_golden_trace.txt").write_text(
        "\n".join(trace_lines) + "\n", encoding="ascii"
    )
    (out_dir / "p3_golden_results.txt").write_text(
        "\n".join(result_lines) + "\n", encoding="ascii"
    )
    return {
        "issues": issue_count,
        "views": view_count,
        "result_words": word_count,
    }



def _derive_only(bundle: Path, target_key: str | None) -> int:
    """Print the governed descriptor IDs one bundle's identities resolve to.

    The identities are the same ones the build uses.  Pointing them at a
    bundle the build does not ship is the check that they derive rather than
    remember: a correct derivation reproduces each bundle's own numbering,
    including the numbering of bundles written before the ID tables this file
    used to carry were last edited.
    """
    if target_key is None:
        raise SystemExit("--derive-from requires --as-target")
    matches = [
        (index, target) for index, target in enumerate(TARGETS)
        if target.key == target_key
    ]
    if len(matches) != 1:
        raise SystemExit(f"{target_key!r} is not one of the four RTL targets")
    target_index, target = matches[0]
    identity = certified_deployment_identity(target)
    deployment = Deployment.read(bundle if bundle.is_absolute() else ROOT / bundle)
    kernel_ir = _kernel_ir_index(target, identity)
    derived = resolve_governed_descriptors(
        deployment,
        kernel_ir,
        target_key=f"{target_key}@{bundle}",
        target_index=target_index,
        geo=TARGET_GEOMETRY[target.key],
    )
    report = {
        "bundle": str(bundle),
        "as_target": target_key,
        "deployment_sha256": deployment.deployment_digest.hex(),
        "descriptor_table_sha256": deployment.table.digest.hex(),
        "descriptor_count": len(deployment.table),
        "kernel_ir": kernel_ir["path"],
        "kernel_ir_sha256": kernel_ir["sha256"],
        "derived": {
            slot: resolution.record()
            for slot, resolution in sorted(derived.items())
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--derive-from",
        type=Path,
        default=None,
        help=(
            "resolve the governed descriptor identities against an arbitrary "
            "deployment bundle and print the derived IDs, without building "
            "vectors.  This is how the derivation is checked against the "
            "preserved pre-promotion bundles under build/abi3/*-pre-am-e9: "
            "the identities are lowering-independent, so a correct derivation "
            "reproduces whatever IDs each bundle actually assigned."
        ),
    )
    parser.add_argument(
        "--as-target",
        default=None,
        help=(
            "the TARGETS key whose certified Kernel IR the --derive-from "
            "bundle is lowered from"
        ),
    )
    parser.add_argument(
        "--emit-g1e-from",
        type=Path,
        default=None,
        help=(
            "regenerate only the G1e golden artifacts and the weight-window "
            "segment map from an existing, committed vector set, without "
            "rebuilding the vectors themselves"
        ),
    )
    args = parser.parse_args(argv)
    if args.derive_from is not None:
        return _derive_only(args.derive_from, args.as_target)
    args.output.mkdir(parents=True, exist_ok=True)
    if args.emit_g1e_from is not None:
        vectors = json.loads(
            (args.emit_g1e_from / "abi3_shipped_prefix_vectors.json").read_text(
                encoding="utf-8"
            )
        )
        window_bytes = emit_weight_window(
            vectors, args.output / "p3_weight_window.txt"
        )
        golden = emit_golden(vectors, args.emit_g1e_from, args.output)
        print(
            f"abi3 shipped-prefix G1e golden: window_bytes={window_bytes} "
            f"issues={golden['issues']} views={golden['views']} "
            f"result_words={golden['result_words']}"
        )
        return 0

    deployment_vectors, deployment_case_words = _deployment_vectors()
    deployment_cases = deployment_vectors["cases"]
    deployment_records = {
        entry["key"]: entry for entry in deployment_vectors["deployments"]
    }

    case_words: list[int] = []
    issue_words: list[int] = []
    index_words: list[int] = []
    source_words: list[int] = []
    expected_words: list[int] = []
    # The result bank is placed BY OBJECT, so a buffer the program rewrites is
    # written twice at one address and the retained image holds only the last
    # value.  ``expected_words`` is therefore the image, and it is no longer
    # the record of what was computed: the write STREAM below is, one entry
    # per word the engines write, in launch order.  Both are published,
    # because an intermediate that a later operator overwrites can be compared
    # only against the stream.
    write_addr: list[int] = []
    write_data: list[int] = []
    records: list[dict[str, Any]] = []
    contract_observations: list[dict[str, Any]] = []
    row_cache: dict[tuple[str, int, int], bytes] = {}
    matrix_cache: dict[str, bytes] = {}
    matrix_staging: dict[str, dict[str, int | str]] = {}
    staged_matmul_bytes = 0
    total_launches = 0
    total_gathers = 0
    total_embeddings = 0
    total_rms_norms = 0
    total_head_rms_norms = 0
    total_rope_launches = 0
    total_transfers = 0
    total_matmuls = 0
    total_rope_words = 0
    total_rms_words = 0
    total_head_rms_words = 0
    total_rope_output_words = 0
    total_transfer_words = 0
    total_matmul_words = 0
    total_matmul_macs = 0
    total_embedding_checkpoint_bytes = 0
    total_rms_checkpoint_bytes = 0
    total_head_rms_checkpoint_bytes = 0
    total_matmul_checkpoint_bytes = 0
    total_checkpoint_bytes = 0
    total_views = 0

    #: TARGETS THIS BUILDER HAS GEOMETRY FOR. Its Qwen constants are the shipped
    #: release's -- HEAD_WIDTH 128 through ROPE_AUX0, vocabulary 151,936, and a model
    #: discriminator that reads `target_index < 2`. A second Qwen configuration, the
    #: reduced regression build, lowers through the same backend with head_dim 16 and
    #: vocabulary 4,096, so it needs its own geometry here before it can be walked.
    #: Until then it is SKIPPED EXPLICITLY rather than silently walked with the wrong
    #: constants -- which is exactly what happened first: the DeepSeek identity set
    #: was applied to a Qwen target because its index was >= 2, and the builder
    #: reported names 0 kernels main.token_embed.
    #:
    #: Skipping keeps the two layers consistent. The reduced target exists in the
    #: deployment vector set, whose images are append-only, and this builder output
    #: for the four targets it does know is unchanged.
    #: A target with no geometry entry is skipped rather than walked with another
    #: model's constants, which is what made a fifth target report
    #: "names 0 kernels main.token_embed" against a Qwen IR.
    global EMBED_WIDTH, KV_WIDTH, HEAD_WIDTH, Q_HEADS, KV_HEADS, VOCABULARY
    skipped_targets: list[str] = []

    for target_index, target in enumerate(TARGETS):
        geo = TARGET_GEOMETRY.get(target.key)
        if geo is None:
            skipped_targets.append(target.key)
            continue
        #: The walk reads these as module names in ~70 places. Rebinding them per
        #: target keeps that diff at one site instead of seventy; the builder
        #: processes one target at a time, so there is no interleaving.
        EMBED_WIDTH = geo.embed_width
        KV_WIDTH = geo.kv_width
        HEAD_WIDTH = geo.head_width
        Q_HEADS = geo.query_heads
        KV_HEADS = geo.kv_heads
        VOCABULARY = geo.vocabulary
        case_name = f"{target.key}/decode"
        matches = [
            (index, case)
            for index, case in enumerate(deployment_cases)
            if case.get("name") == case_name
        ]
        if len(matches) != 1:
            raise SystemExit(f"expected one shipped case named {case_name}")
        deployment_case_index, deployment_case = matches[0]
        base = deployment_case_index * DEPLOYMENT_CASE_STRIDE
        source_case = deployment_case_words[base : base + DEPLOYMENT_CASE_STRIDE]

        expected_identity = certified_deployment_identity(target)
        deployment = Deployment.read(ROOT / target.deployment)
        deployment_sha = deployment.deployment_digest.hex()
        if deployment_sha != expected_identity.deployment_sha256:
            raise SystemExit(f"{target.key}: deployment certificate is stale")
        if deployment_sha != deployment_case["deployment_sha256"]:
            raise SystemExit(f"{target.key}: shipped RTL vectors are stale")
        deployment_record = deployment_records[target.key]
        if deployment_record["deployment_sha256"] != deployment_sha:
            raise SystemExit(f"{target.key}: deployment identity disagreement")

        _, body = split_program(deployment.program)
        instructions = decode_body(body)
        entry = next(
            item for item in deployment.entrypoints if int(item["entrypoint_id"]) == 1
        )
        entry_pc = int(entry["first_instruction"])
        if entry_pc != int(source_case[7]):
            raise SystemExit(f"{target.key}: decode entry PC changed")

        symbols = {
            int(key): int(value) for key, value in deployment_case["symbols"].items()
        }
        if symbols[int(Symbol.POSITION_START)] != INDEX_VALUE:
            raise SystemExit(f"{target.key}: decode position is not {INDEX_VALUE}")

        # Every governed descriptor ID is DERIVED here, from this target's own
        # bundle and its own certified Kernel IR, before a single instruction
        # is walked.  Nothing below reads a descriptor number this file wrote
        # down, and the two lowerings are resolved independently -- their IDs
        # differ at all eight governed Qwen PCs and the derivation reports the
        # difference instead of assuming it away.
        kernel_ir = _kernel_ir_index(target, expected_identity)
        derived = resolve_governed_descriptors(
            deployment,
            kernel_ir,
            target_key=target.key,
            target_index=target_index,
            geo=geo,
        )

        loops: dict[int, int] = {}
        gathers: list[dict[str, Any]] = []
        embeddings: list[dict[str, Any]] = []
        rms_norms: list[dict[str, Any]] = []
        head_rms_norms: list[dict[str, Any]] = []
        ropes: list[dict[str, Any]] = []
        transfers: list[dict[str, Any]] = []
        matmuls: list[dict[str, Any]] = []
        prefix_views: list[dict[str, Any]] = []
        fetched = retired = issued = loop_iterations = wait_events = signals = 0
        unsupported: dict[str, Any] | None = None
        pc = entry_pc
        while pc < len(instructions):
            instruction = instructions[pc]
            fetched += 1
            major = int(instruction.major)
            sub = int(instruction.sub)
            if major == int(Major.CONTROL):
                if sub == int(Control.LOOP_SETUP):
                    loop_id = int(instruction.control_id)
                    descriptor = deployment.table.get(
                        loop_id, ExtendedDescriptorType.LOOP_CONTROL
                    )
                    trip = _loop_trip(descriptor.payload, symbols)
                    if trip == 0:
                        raise SystemExit(
                            f"{target.key}: prefix loop {loop_id} is empty"
                        )
                    loops[loop_id] = int(descriptor.payload["lower_bound"])
                elif sub == int(Control.LOOP_NEXT):
                    loop_id = int(instruction.control_id)
                    if loop_id not in loops:
                        raise SystemExit(f"{target.key}: unmatched LOOP_NEXT")
                    del loops[loop_id]
                    loop_iterations += 1
                else:
                    raise SystemExit(
                        f"{target.key}: unexpected CONTROL.{sub:#x} in prefix"
                    )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            issued += 1
            resolved = _resolved_views(
                deployment,
                int(instruction.descriptor_id),
                loops,
                symbols,
                major=major,
            )
            prefix_views.extend({"pc": pc, **view} for view in resolved)
            if int(instruction.wait_set_id) != NO_ID:
                wait_events += 1
            if major == int(Major.DMA) and sub == int(Dma.GATHER):
                if int(instruction.wait_set_id) != NO_ID:
                    raise SystemExit(f"{target.key}: gather unexpectedly waits")
                operator = deployment.table.get(
                    int(instruction.descriptor_id), ExtendedDescriptorType.OPERATOR
                )
                payload = operator.payload
                if [view["slot"] for view in resolved] != [0, 1, 4]:
                    raise SystemExit(f"{target.key}: gather arity changed")
                by_slot = {int(view["slot"]): view for view in resolved}
                index_view = by_slot[0]
                source_view = by_slot[1]
                output_view = by_slot[4]
                if (
                    index_view["dtype"] != int(DType.U32)
                    or index_view["dims"] != [1]
                    or source_view["dtype"] != int(DType.FP32)
                    or output_view["dtype"] != int(DType.FP32)
                    or len(source_view["dims"]) != 2
                    or output_view["dims"] != [1, int(source_view["dims"][1])]
                ):
                    raise SystemExit(f"{target.key}: gather shape changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                if bytes(numeric.payload["contract_digest"]) != EXACT_INDEX_SELECT:
                    raise SystemExit(f"{target.key}: gather contract changed")
                trailing = int(source_view["dims"][1])
                row, source_identity = _generated_row(
                    deployment,
                    int(source_view["object_id"]),
                    INDEX_VALUE,
                    trailing,
                    row_cache,
                )
                row_words = [
                    int.from_bytes(row[offset : offset + 4], "little")
                    for offset in range(0, len(row), 4)
                ]
                gathers.append(
                    {
                        "kind": "dma_gather",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "index_view": index_view,
                        "source_view": source_view,
                        "output_view": output_view,
                        "numeric_input_dtype": int(numeric.payload["input_dtype"]),
                        "contract": "exact_index_select_v1",
                        "contract_sha256": EXACT_INDEX_SELECT.hex(),
                        "source": source_identity,
                        "expected_row_sha256": hashlib.sha256(row).hexdigest(),
                        "_source_words": row_words,
                        "_expected_words": [
                            int.from_bytes(row[offset : offset + 4], "little")
                            for offset in range(0, len(row), 4)
                        ],
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.TENSOR) and sub == int(Tensor.EMBED_LOOKUP):
                if int(instruction.wait_set_id) != NO_ID:
                    raise SystemExit(
                        f"{target.key}: embedding lookup unexpectedly waits"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id) != derived["embed"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: embedding operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                index_view = by_slot[0]
                source_view = by_slot[1]
                output_view = by_slot[4]
                expected_vocabulary = geo.vocabulary
                if (
                    index_view["dtype"] != int(DType.U32)
                    or index_view["dims"] != [1]
                    or index_view["strides"] != [1]
                    or index_view["element_offset"] != 0
                    or source_view["dtype"] != int(DType.BF16)
                    or source_view["dims"] != [expected_vocabulary, EMBED_WIDTH]
                    or source_view["strides"] != [EMBED_WIDTH, 1]
                    or source_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, EMBED_WIDTH]
                    or output_view["strides"] != [EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(f"{target.key}: embedding view profile changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                expected_contract = (
                    QWEN_EMBED_CONTRACT if geo.model_index == 0
                    else DEEPSEEK_EMBED_CONTRACT
                )
                contract_name = (
                    "bf16_payload_lookup_v1"
                    if geo.model_index == 0
                    else "lookup_bf16_token_embedding_v1"
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.U32)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or any(
                        int(numeric_payload[field]) != 0
                        for field in (
                            "rounding_mode",
                            "reduction_order",
                            "saturate",
                            "nan_policy",
                            "epsilon_bits",
                            "scale_bits",
                            "flags",
                        )
                    )
                    or bytes(numeric_payload["contract_digest"]) != expected_contract
                ):
                    raise SystemExit(f"{target.key}: embedding numeric profile changed")
                row, source_identity = _checkpoint_row(
                    target,
                    deployment,
                    int(source_view["object_id"]),
                    EMBED_TOKEN,
                    EMBED_WIDTH,
                )
                embeddings.append(
                    {
                        "kind": "tensor_embed_lookup",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "index_view": index_view,
                        "source_view": source_view,
                        "output_view": output_view,
                        "token_id": EMBED_TOKEN,
                        "contract": contract_name,
                        "contract_sha256": expected_contract.hex(),
                        "source": source_identity,
                        "expected_row_sha256": hashlib.sha256(row).hexdigest(),
                        "_source_words": [
                            int.from_bytes(row[offset : offset + 2], "little")
                            for offset in range(0, len(row), 2)
                        ],
                        "_expected_words": [
                            int.from_bytes(row[offset : offset + 2], "little")
                            for offset in range(0, len(row), 2)
                        ],
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.VECTOR) and sub == int(Vector.RMS_NORM):
                if geo.model_index != 0 or len(embeddings) != 1:
                    raise SystemExit(
                        f"{target.key}: RMSNorm appeared outside the Qwen "
                        "post-embedding prefix"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id) != derived["rms"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(f"{target.key}: RMSNorm operator profile changed")
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                weight_view = by_slot[1]
                output_view = by_slot[4]
                embedding = embeddings[0]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != [1, EMBED_WIDTH]
                    or input_view["strides"] != [EMBED_WIDTH, 1]
                    or input_view["element_offset"] != 0
                    or input_view["object_id"] != embedding["output_view"]["object_id"]
                    or weight_view["dtype"] != int(DType.BF16)
                    or weight_view["dims"] != [EMBED_WIDTH]
                    or weight_view["strides"] != [1]
                    or weight_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, EMBED_WIDTH]
                    or output_view["strides"] != [EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(f"{target.key}: RMSNorm view profile changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["rounding_mode"]) != 0
                    or int(numeric_payload["reduction_order"]) != 1
                    or int(numeric_payload["saturate"]) != 0
                    or int(numeric_payload["nan_policy"]) != 0
                    or int(numeric_payload["epsilon_bits"]) != 0x358637BD
                    or int(numeric_payload["scale_bits"]) != 0
                    or int(numeric_payload["flags"]) != 0
                    or bytes(numeric_payload["contract_digest"]) != QWEN_RMS_CONTRACT
                ):
                    raise SystemExit(f"{target.key}: RMSNorm numeric profile changed")
                gain, gain_identity = _checkpoint_row(
                    target,
                    deployment,
                    int(weight_view["object_id"]),
                    0,
                    EMBED_WIDTH,
                )
                gain_words = tuple(
                    int.from_bytes(gain[offset : offset + 2], "little")
                    for offset in range(0, len(gain), 2)
                )
                input_words = tuple(int(code) for code in embedding["_expected_words"])
                result = rms_norm_bf16((input_words,), gain_words)
                result_words = list(result.values[0])
                result_bytes = b"".join(
                    code.to_bytes(2, "little") for code in result_words
                )
                _pins = ORACLE_PINS.get(target.key, {})
                if (
                    not oracle_pin(target.key, "rms_mean_square_codes",
                                   result.mean_square_codes,
                                   _pins.get("rms_mean_square_codes"))
                    or not oracle_pin(target.key, "rms_inverse_rms_codes",
                                      result.inverse_rms_codes,
                                      _pins.get("rms_inverse_rms_codes"))
                    or result.normalized_saturated_element_count != 0
                    or result.output_saturated_element_count != 0
                    or not oracle_pin(target.key, "rms_result_sha256",
                                      hashlib.sha256(result_bytes).hexdigest(),
                                      _pins.get("rms_result_sha256"))
                ):
                    raise SystemExit(
                        f"{target.key}: exact RMSNorm oracle result changed"
                    )
                rms_norms.append(
                    {
                        "kind": "vector_rms_norm",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "weight_view": weight_view,
                        "output_view": output_view,
                        "contract": "qwen3_rmsnorm_fp32_bf16_v1",
                        "contract_sha256": QWEN_RMS_CONTRACT.hex(),
                        "input_source": "prior_embedding_result_bank",
                        "weight_source": gain_identity,
                        "mean_square_code": result.mean_square_codes[0],
                        "inverse_rms_code": result.inverse_rms_codes[0],
                        "normalized_saturated_element_count": (
                            result.normalized_saturated_element_count
                        ),
                        "output_saturated_element_count": (
                            result.output_saturated_element_count
                        ),
                        "expected_row_sha256": hashlib.sha256(result_bytes).hexdigest(),
                        "_weight_words": list(gain_words),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.TENSOR) and sub == int(Tensor.MATMUL):
                matmul_index = len(matmuls)
                if geo.model_index != 0 or len(rms_norms) != 1:
                    raise SystemExit(
                        f"{target.key}: MATMUL appeared outside the "
                        "Qwen post-RMSNorm prefix"
                    )
                if matmul_index >= len(MATMUL_PCS) or pc != MATMUL_PCS[matmul_index]:
                    raise SystemExit(
                        f"{target.key}: Qwen MATMUL sequence changed at PC {pc}"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != derived[f"matmul.{matmul_index}"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} MATMUL operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                weight_view = by_slot[1]
                output_view = by_slot[4]
                rms_norm = rms_norms[0]
                output_columns = EMBED_WIDTH if matmul_index == 0 else KV_WIDTH
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != [1, EMBED_WIDTH]
                    or input_view["strides"] != [EMBED_WIDTH, 1]
                    or input_view["element_offset"] != 0
                    or input_view["object_id"] != rms_norm["output_view"]["object_id"]
                    or weight_view["dtype"] != int(DType.BF16)
                    or weight_view["dims"] != [output_columns, EMBED_WIDTH]
                    or weight_view["strides"] != [EMBED_WIDTH, 1]
                    or weight_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, output_columns]
                    or output_view["strides"] != [output_columns, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} MATMUL view profile changed"
                    )
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["rounding_mode"]) != 0
                    or int(numeric_payload["reduction_order"]) != 2
                    or int(numeric_payload["saturate"]) != 0
                    or int(numeric_payload["nan_policy"]) != 0
                    or int(numeric_payload["epsilon_bits"]) != 0
                    or int(numeric_payload["scale_bits"]) != 0
                    or int(numeric_payload["flags"]) != 0
                    or bytes(numeric_payload["contract_digest"]) != QWEN_MATMUL_CONTRACT
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} MATMUL numeric profile changed"
                    )
                weight_payload, weight_identity = _checkpoint_matrix(
                    target,
                    deployment,
                    int(weight_view["object_id"]),
                    rows=output_columns,
                    columns=EMBED_WIDTH,
                    cache=matrix_cache,
                )
                weight_digest = str(weight_identity["declared_segment_sha256"])
                staged = matrix_staging.get(weight_digest)
                if staged is None:
                    staged = {
                        "base_words": staged_matmul_bytes // 2,
                        "bytes": int(weight_identity["declared_segment_bytes"]),
                        "sha256": weight_digest,
                    }
                    matrix_staging[weight_digest] = staged
                    staged_matmul_bytes += int(staged["bytes"])
                elif int(staged["bytes"]) != int(
                    weight_identity["declared_segment_bytes"]
                ):
                    raise SystemExit("staged MATMUL matrix size disagreement")
                input_codes = np.asarray(
                    rms_norm["_expected_words"], dtype=np.uint16
                ).reshape(1, EMBED_WIDTH)
                weight_codes = np.frombuffer(weight_payload, dtype="<u2").reshape(
                    output_columns, EMBED_WIDTH
                )
                result = dense_bf16_linear_bf16(input_codes, weight_codes)
                result_words = [int(code) for code in result.values[0]]
                result_bytes = np.ascontiguousarray(
                    result.values, dtype="<u2"
                ).tobytes()
                result_sha256 = hashlib.sha256(result_bytes).hexdigest()
                if (
                    result.output_saturated_element_count != 0
                    or not oracle_pin(
                        target.key, f"matmul_sha256_pc{pc}", result_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            f"matmul_sha256_pc{pc}", MATMUL_OUTPUT_SHA256[pc])
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: exact PC-{pc} MATMUL oracle changed"
                    )
                matmuls.append(
                    {
                        "kind": "tensor_matmul",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "weight_view": weight_view,
                        "output_view": output_view,
                        "contract": "bf16_bf16_fp32_blocked_rne_v1",
                        "contract_sha256": QWEN_MATMUL_CONTRACT.hex(),
                        "executed_association": (
                            "ot_a3_mac_lane_single_lane_ascending_k_v1"
                        ),
                        "association_scope": {
                            "rows": 1,
                            "columns": output_columns,
                            "reduction": EMBED_WIDTH,
                            "lane_count": 1,
                            "reduction_order": "ascending_k",
                            "binary32_rounding": "rne_after_each_product_and_add",
                            "output_rounding": "bf16_rne_once",
                        },
                        "input_source": "prior_rms_norm_result_bank",
                        "weight_source": weight_identity,
                        "staged_weight_base_words": int(staged["base_words"]),
                        "mac_count": output_columns * EMBED_WIDTH,
                        "output_saturated_element_count": (
                            result.output_saturated_element_count
                        ),
                        "expected_row_sha256": result_sha256,
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.VECTOR) and sub == int(Vector.HEAD_RMS_NORM):
                head_index = len(head_rms_norms)
                if (
                    geo.model_index != 0
                    or len(matmuls) != 3
                    or head_index >= len(HEAD_RMS_PCS)
                    or pc != HEAD_RMS_PCS[head_index]
                ):
                    raise SystemExit(
                        f"{target.key}: head RMSNorm appeared outside the "
                        "Qwen post-QKV prefix"
                    )
                expected_heads = (Q_HEADS, KV_HEADS)[head_index]
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != derived[f"head_rms.{head_index}"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or int(payload["aux_id_0"]) != expected_heads
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} head RMSNorm operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                weight_view = by_slot[1]
                output_view = by_slot[4]
                matmul = matmuls[head_index]
                expected_shape = [1, expected_heads, HEAD_WIDTH]
                expected_strides = [expected_heads * HEAD_WIDTH, HEAD_WIDTH, 1]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != expected_shape
                    or input_view["strides"] != expected_strides
                    or input_view["element_offset"] != 0
                    or input_view["object_id"] != matmul["output_view"]["object_id"]
                    or weight_view["dtype"] != int(DType.BF16)
                    or weight_view["dims"] != [HEAD_WIDTH]
                    or weight_view["strides"] != [1]
                    or weight_view["element_offset"] != 0
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != expected_shape
                    or output_view["strides"] != expected_strides
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} head RMSNorm view profile changed"
                    )
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["rounding_mode"]) != 0
                    or int(numeric_payload["reduction_order"]) != 1
                    or int(numeric_payload["saturate"]) != 0
                    or int(numeric_payload["nan_policy"]) != 0
                    or int(numeric_payload["epsilon_bits"]) != 0x358637BD
                    or int(numeric_payload["scale_bits"]) != 0
                    or int(numeric_payload["flags"]) != 0
                    or bytes(numeric_payload["contract_digest"]) != QWEN_RMS_CONTRACT
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} head RMSNorm numeric profile changed"
                    )
                gain, gain_identity = _checkpoint_row(
                    target,
                    deployment,
                    int(weight_view["object_id"]),
                    0,
                    HEAD_WIDTH,
                )
                gain_words = tuple(
                    int.from_bytes(gain[offset : offset + 2], "little")
                    for offset in range(0, len(gain), 2)
                )
                input_words = tuple(int(code) for code in matmul["_expected_words"])
                input_rows = tuple(
                    input_words[offset : offset + HEAD_WIDTH]
                    for offset in range(0, len(input_words), HEAD_WIDTH)
                )
                if len(input_rows) != expected_heads:
                    raise SystemExit(f"{target.key}: PC-{pc} head row count changed")
                result = rms_norm_bf16(input_rows, gain_words)
                result_words = [int(code) for row in result.values for code in row]
                result_bytes = b"".join(
                    code.to_bytes(2, "little") for code in result_words
                )
                mean_bytes = b"".join(
                    code.to_bytes(4, "little") for code in result.mean_square_codes
                )
                inverse_bytes = b"".join(
                    code.to_bytes(4, "little") for code in result.inverse_rms_codes
                )
                result_sha256 = hashlib.sha256(result_bytes).hexdigest()
                mean_sha256 = hashlib.sha256(mean_bytes).hexdigest()
                inverse_sha256 = hashlib.sha256(inverse_bytes).hexdigest()
                if (
                    result.normalized_saturated_element_count != 0
                    or result.output_saturated_element_count != 0
                    or not oracle_pin(
                        target.key, f"head_rms_sha256_pc{pc}", result_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            f"head_rms_sha256_pc{pc}", HEAD_RMS_OUTPUT_SHA256[pc])
                    )
                    or not oracle_pin(
                        target.key, f"head_rms_mean_sha256_pc{pc}", mean_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            f"head_rms_mean_sha256_pc{pc}", HEAD_RMS_MEAN_SHA256[pc])
                    )
                    or not oracle_pin(
                        target.key, f"head_rms_inverse_sha256_pc{pc}", inverse_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            f"head_rms_inverse_sha256_pc{pc}",
                            HEAD_RMS_INVERSE_SHA256[pc])
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: exact PC-{pc} head RMSNorm oracle changed"
                    )
                head_rms_norms.append(
                    {
                        "kind": "vector_head_rms_norm",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "weight_view": weight_view,
                        "output_view": output_view,
                        "contract": "qwen3_rmsnorm_fp32_bf16_v1",
                        "contract_sha256": QWEN_RMS_CONTRACT.hex(),
                        "input_source": (
                            "prior_query_projection_result_bank"
                            if head_index == 0
                            else "prior_key_projection_result_bank"
                        ),
                        "weight_source": gain_identity,
                        "row_count": expected_heads,
                        "row_width": HEAD_WIDTH,
                        "mean_square_payload_sha256": mean_sha256,
                        "inverse_rms_payload_sha256": inverse_sha256,
                        "normalized_saturated_element_count": (
                            result.normalized_saturated_element_count
                        ),
                        "output_saturated_element_count": (
                            result.output_saturated_element_count
                        ),
                        "expected_payload_sha256": result_sha256,
                        "operator_aux_id_0": int(payload["aux_id_0"]),
                        "_weight_words": list(gain_words),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.VECTOR) and sub == int(Vector.ROPE):
                rope_index = len(ropes)
                if (
                    geo.model_index != 0
                    or len(head_rms_norms) != 2
                    or rope_index >= len(ROPE_PCS)
                    or pc != ROPE_PCS[rope_index]
                ):
                    raise SystemExit(
                        f"{target.key}: RoPE appeared outside the Qwen "
                        "post-head-normalization prefix"
                    )
                expected_heads = (Q_HEADS, KV_HEADS)[rope_index]
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != derived[f"rope.{rope_index}"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or int(payload["aux_id_0"]) != geo.rope_aux0
                    or [view["slot"] for view in resolved] != [0, 1, 4]
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} RoPE operator profile changed"
                    )
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                coefficient_view = by_slot[1]
                output_view = by_slot[4]
                head_rms_norm = head_rms_norms[rope_index]
                gather = gathers[0]
                expected_shape = [1, expected_heads, HEAD_WIDTH]
                expected_strides = [expected_heads * HEAD_WIDTH, HEAD_WIDTH, 1]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != expected_shape
                    or input_view["strides"] != expected_strides
                    or input_view["element_offset"] != 0
                    or input_view["object_id"]
                    != head_rms_norm["output_view"]["object_id"]
                    or coefficient_view["dtype"] != int(DType.FP32)
                    or coefficient_view["dims"] != [1, expected_heads, 2 * HEAD_WIDTH]
                    or coefficient_view["strides"] != [2 * HEAD_WIDTH, 0, 1]
                    or coefficient_view["element_offset"] != 0
                    or coefficient_view["object_id"]
                    != gather["output_view"]["object_id"]
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != expected_shape
                    or output_view["strides"] != expected_strides
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(f"{target.key}: PC-{pc} RoPE view profile changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or any(
                        int(numeric_payload[field]) != 0
                        for field in (
                            "rounding_mode",
                            "reduction_order",
                            "saturate",
                            "nan_policy",
                            "epsilon_bits",
                            "scale_bits",
                            "flags",
                        )
                    )
                    or bytes(numeric_payload["contract_digest"]) != QWEN_ROPE_CONTRACT
                ):
                    raise SystemExit(
                        f"{target.key}: PC-{pc} RoPE numeric profile changed"
                    )
                coefficient_fp32_words = np.asarray(
                    gather["_expected_words"], dtype=np.uint32
                )
                coefficient_codes, coefficient_saturations = narrow_bf16_rne(
                    coefficient_fp32_words.view(np.float32)
                )
                coefficient_codes = np.ascontiguousarray(
                    coefficient_codes, dtype=np.uint16
                )
                coefficient_sha256 = hashlib.sha256(
                    coefficient_codes.astype("<u2", copy=False).tobytes()
                ).hexdigest()
                if (
                    coefficient_saturations != 0
                    or coefficient_codes.shape != (2 * HEAD_WIDTH,)
                    or not oracle_pin(
                        target.key, "rope_coefficient_bf16_sha256",
                        coefficient_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            "rope_coefficient_bf16_sha256",
                            ROPE_COEFFICIENT_BF16_SHA256)
                    )
                ):
                    raise SystemExit(
                        f"{target.key}: exact PC-{pc} coefficient narrowing changed"
                    )
                input_codes = np.asarray(
                    head_rms_norm["_expected_words"], dtype=np.uint16
                ).reshape(expected_heads, HEAD_WIDTH)
                optimized = optimized_rope_bf16(
                    input_codes, input_codes, coefficient_codes
                )
                scalar = scalar_rope_bf16(
                    input_codes.tolist(),
                    input_codes.tolist(),
                    coefficient_codes[:HEAD_WIDTH].tolist(),
                    coefficient_codes[HEAD_WIDTH:].tolist(),
                )
                result_words = [int(code) for code in optimized.query_values.flat]
                scalar_words = [
                    int(code) for row in scalar.query_values for code in row
                ]
                result_bytes = np.ascontiguousarray(
                    optimized.query_values, dtype="<u2"
                ).tobytes()
                result_sha256 = hashlib.sha256(result_bytes).hexdigest()
                if (
                    result_words != scalar_words
                    or not oracle_pin(
                        target.key, f"rope_sha256_pc{pc}", result_sha256,
                        ORACLE_PINS.get(target.key, {}).get(
                            f"rope_sha256_pc{pc}", ROPE_OUTPUT_SHA256[pc])
                    )
                    or optimized.multiplication_saturated_element_count != 0
                    or optimized.addition_saturated_element_count != 0
                    or scalar.multiplication_saturated_element_count != 0
                    or scalar.addition_saturated_element_count != 0
                ):
                    raise SystemExit(f"{target.key}: exact PC-{pc} RoPE oracle changed")
                ropes.append(
                    {
                        "kind": "vector_rope",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "coefficient_view": coefficient_view,
                        "output_view": output_view,
                        "operator_aux_id_0": int(payload["aux_id_0"]),
                        "contract": "qwen3_rope_fp32_bf16_v1",
                        "contract_sha256": QWEN_ROPE_CONTRACT.hex(),
                        "input_source": (
                            "prior_query_head_rms_norm_result_bank"
                            if rope_index == 0
                            else "prior_key_head_rms_norm_result_bank"
                        ),
                        "coefficient_source": (
                            "prior_fp32_generated_row_dma_gather_result_bank"
                        ),
                        "coefficient_fp32_payload_sha256": gather[
                            "expected_row_sha256"
                        ],
                        "coefficient_bf16_payload_sha256": coefficient_sha256,
                        "coefficient_narrow_saturated_element_count": int(
                            coefficient_saturations
                        ),
                        "row_count": expected_heads,
                        "row_width": HEAD_WIDTH,
                        "multiplication_count": 2 * expected_heads * HEAD_WIDTH,
                        "addition_count": expected_heads * HEAD_WIDTH,
                        "multiplication_saturated_element_count": 0,
                        "addition_saturated_element_count": 0,
                        "expected_payload_sha256": result_sha256,
                        "oracle_agreement": (
                            "optimized_numpy_equals_independent_scalar_all_elements"
                        ),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.DMA) and sub == int(Dma.TRANSFER):
                if geo.model_index == 0 or len(embeddings) != 1:
                    raise SystemExit(
                        f"{target.key}: transfer appeared outside the "
                        "DeepSeek post-embedding prefix"
                    )
                operator = deployment.table.get(
                    int(instruction.descriptor_id),
                    ExtendedDescriptorType.OPERATOR,
                )
                payload = operator.payload
                if (
                    int(instruction.descriptor_id)
                    != derived["transfer"].descriptor_id
                    or int(payload["engine_family"]) != major
                    or int(payload["engine_sub"]) != sub
                    or int(payload["numeric_profile_id"]) == NO_ID
                    or [view["slot"] for view in resolved] != [0, 4]
                    or int(payload["input_view_1"]) != NO_ID
                    or any(
                        int(payload[field]) != NO_ID
                        for field in (
                            "input_view_2",
                            "input_view_3",
                            "output_view_1",
                            "aux_id_0",
                            "aux_id_1",
                            "aux_id_2",
                            "aux_id_3",
                        )
                    )
                ):
                    raise SystemExit(f"{target.key}: transfer operator profile changed")
                by_slot = {int(view["slot"]): view for view in resolved}
                input_view = by_slot[0]
                output_view = by_slot[4]
                embedding = embeddings[0]
                if (
                    input_view["dtype"] != int(DType.BF16)
                    or input_view["dims"] != [1, 4, EMBED_WIDTH]
                    or input_view["strides"] != [EMBED_WIDTH, 0, 1]
                    or input_view["element_offset"] != 0
                    or input_view["object_id"] != embedding["output_view"]["object_id"]
                    or output_view["dtype"] != int(DType.BF16)
                    or output_view["dims"] != [1, 4, EMBED_WIDTH]
                    or output_view["strides"] != [4 * EMBED_WIDTH, EMBED_WIDTH, 1]
                    or output_view["element_offset"] != 0
                    or any(view["extent_axis"] != 0 for view in resolved)
                ):
                    raise SystemExit(f"{target.key}: transfer view profile changed")
                numeric_id = int(payload["numeric_profile_id"])
                numeric = deployment.table.get(
                    numeric_id, ExtendedDescriptorType.NUMERIC
                )
                numeric_payload = numeric.payload
                if (
                    int(numeric_payload["input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["second_input_dtype"]) != int(DType.BF16)
                    or int(numeric_payload["accumulator_dtype"]) != int(DType.FP32)
                    or int(numeric_payload["output_dtype"]) != int(DType.BF16)
                    or any(
                        int(numeric_payload[field]) != 0
                        for field in (
                            "rounding_mode",
                            "reduction_order",
                            "saturate",
                            "nan_policy",
                            "epsilon_bits",
                            "scale_bits",
                            "flags",
                        )
                    )
                    or bytes(numeric_payload["contract_digest"])
                    != DEEPSEEK_TRANSFER_CONTRACT
                ):
                    raise SystemExit(f"{target.key}: transfer numeric profile changed")
                result_words = list(embedding["_expected_words"]) * 4
                result_bytes = b"".join(
                    code.to_bytes(2, "little") for code in result_words
                )
                transfers.append(
                    {
                        "kind": "dma_transfer",
                        "pc": pc,
                        "descriptor_id": int(instruction.descriptor_id),
                        "numeric_profile_id": numeric_id,
                        "input_view": input_view,
                        "output_view": output_view,
                        "contract": "structural_hc_expand_bf16_v1",
                        "contract_sha256": DEEPSEEK_TRANSFER_CONTRACT.hex(),
                        "lowering": {
                            "operation": "four_row_gather",
                            "indices": [0, 0, 0, 0],
                            "slots": 4,
                            "trailing": EMBED_WIDTH,
                            "extent": 1,
                            "source": "prior_embedding_result_bank",
                        },
                        "expected_payload_sha256": hashlib.sha256(
                            result_bytes
                        ).hexdigest(),
                        "_expected_words": result_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            unsupported = {
                "pc": pc,
                "family": major,
                "sub": sub,
                "opcode": str(instruction).split(maxsplit=1)[0],
                "descriptor_id": int(instruction.descriptor_id),
                "trap_class": 4,
            }
            break

        if unsupported is None:
            raise SystemExit(f"{target.key}: no fail-closed prefix boundary")
        expected_gathers = 1 if geo.model_index == 0 else 2
        if len(gathers) != expected_gathers:
            raise SystemExit(
                f"{target.key}: expected {expected_gathers} gathers, found "
                f"{len(gathers)}"
            )
        if len(embeddings) != 1:
            raise SystemExit(
                f"{target.key}: expected one embedding, found {len(embeddings)}"
            )
        if geo.model_index == 0:
            if (
                len(rms_norms) != 1
                or len(matmuls) != 3
                or len(head_rms_norms) != 2
                or len(ropes) != 2
                or transfers
            ):
                raise SystemExit(
                    f"{target.key}: expected one RMSNorm, three reusable "
                    "MATMUL launches, two reusable head RMSNorm launches, "
                    "two reusable RoPE launches, and no transfer"
                )
        elif len(transfers) != 1 or rms_norms or head_rms_norms or ropes or matmuls:
            raise SystemExit(f"{target.key}: expected one transfer and no RMSNorm")
        trailing_values = {int(g["source_view"]["dims"][1]) for g in gathers}
        if len(trailing_values) != 1:
            raise SystemExit(f"{target.key}: prefix gather widths differ")
        trailing = trailing_values.pop()

        index_base = len(index_words)
        source_base = len(source_words)
        output_base = len(expected_words)
        # One base per ABI object, allocated at the object's FIRST write and
        # reused by every later one.  A first write therefore lands exactly
        # where the retired append cursor put it, and the only addresses that
        # move are the second and later writes to a reused buffer -- which is
        # the whole point: those used to land somewhere else and be read back
        # from the wrong place.
        placement: dict[int, int] = {}
        placement_span: dict[int, int] = {}
        rewrite_count: dict[int, int] = {}

        def place(object_id: int, words: list[int]) -> int:
            """Write ``words`` into ``object_id`` and return its base."""
            object_id = int(object_id)
            if object_id == NO_OBJECT:
                raise SystemExit("a result view with no primary object")
            if object_id in placement:
                base = placement[object_id]
                if placement_span[object_id] != len(words):
                    raise SystemExit(
                        f"object {object_id} was allocated "
                        f"{placement_span[object_id]} words by its first "
                        f"write and is rewritten with {len(words)}: this "
                        "compact staging gives an object one span"
                    )
                for offset, word in enumerate(words):
                    expected_words[base + offset] = word
            else:
                base = len(expected_words)
                placement[object_id] = base
                placement_span[object_id] = len(words)
                expected_words.extend(words)
            rewrite_count[object_id] = rewrite_count.get(object_id, 0) + 1
            write_addr.extend(range(base, base + len(words)))
            write_data.extend(words)
            return base

        def bind(object_id: int, base: int) -> int:
            """Bind an object that lives in a bank this builder stages by hand.

            The weight-side operands are not results, so nothing writes them
            through ``place``; they are staged into the source bank or the
            paged weight window and their base is recorded here.  Two objects
            in different banks may share a base value.  One object may not be
            bound twice to different bases -- the bridge refuses such a table
            at admission, and this refuses to emit one.
            """
            object_id = int(object_id)
            if object_id == NO_OBJECT:
                raise SystemExit("a weight view with no primary object")
            if placement.get(object_id, base) != base:
                raise SystemExit(
                    f"object {object_id} is already placed at "
                    f"{placement[object_id]} and would be bound at {base}: "
                    "one object has one base"
                )
            placement[object_id] = base
            return base

        def agrees(name: str, object_id: int, legacy: int) -> None:
            """The retired per-role base and the object's base are the same.

            Every role port this record used to carry named a base that some
            operator had already written to, or that this builder had staged.
            Checking the two against each other is what makes the collapse
            onto one table a refactor of the addressing model rather than a
            new set of addresses: if any of these disagreed, the golden image
            would move and this build would stop rather than publish it.
            """
            actual = placed(object_id)
            if actual != legacy:
                raise SystemExit(
                    f"{name}: object {object_id} is placed at {actual} but the "
                    f"retired per-role base was {legacy}"
                )

        def placed(object_id: int) -> int:
            """Where an object already written lives; never a guess."""
            object_id = int(object_id)
            if object_id not in placement:
                raise SystemExit(
                    f"object {object_id} is read before anything wrote it, so "
                    "this vector set has no base to bind it to"
                )
            return placement[object_id]

        source_stride = (INDEX_VALUE + 1) * trailing
        for launch, gather in enumerate(gathers):
            index_words.append(INDEX_VALUE)
            want_source_cursor = source_base + launch * source_stride
            if len(source_words) != want_source_cursor:
                raise SystemExit("source-bank cursor drift")
            source_words.extend([0] * (INDEX_VALUE * trailing))
            source_words.extend(gather.pop("_source_words"))
            place(gather["output_view"]["object_id"],
                  list(gather.pop("_expected_words")))

        embedding = embeddings[0]
        embedding_source_base = len(source_words)
        index_words.append(EMBED_TOKEN)
        source_words.extend(embedding.pop("_source_words"))
        place(embedding["output_view"]["object_id"],
              list(embedding.pop("_expected_words")))
        case_rope_words = len(gathers) * trailing
        case_embedding_words = EMBED_WIDTH
        rms_input_base = output_base + case_rope_words
        rms_weight_base = 0
        transfer_index_base = 0
        transfer_source_base = output_base + case_rope_words
        case_rms_words = 0
        case_transfer_words = 0
        matmul_input_base = 0
        matmul_weight_mappings = []
        head_weight_mappings = []
        case_matmul_words = 0
        case_matmul_macs = 0
        case_head_rms_words = 0
        case_head_rms_checkpoint_bytes = 0
        case_rope_output_words = 0
        last_matmul_words = 0
        last_matmul_macs = 0
        last_result_words = 0
        last_work_count = 0
        if rms_norms:
            rms_norm = rms_norms[0]
            rms_weight_base = len(source_words)
            source_words.extend(rms_norm.pop("_weight_words"))
            bind(rms_norm["weight_view"]["object_id"], rms_weight_base)
            agrees("rms input", rms_norm["input_view"]["object_id"],
                   rms_input_base)
            rms_expected = list(rms_norm.pop("_expected_words"))
            place(rms_norm["output_view"]["object_id"], rms_expected)
            case_rms_words = len(rms_expected)
            matmul_input_base = output_base + case_rope_words + case_embedding_words
            for matmul in matmuls:
                agrees("matmul input", matmul["input_view"]["object_id"],
                       matmul_input_base)
            matmul_weight_mappings = [
                (
                    bind(matmul["weight_view"]["object_id"],
                         int(matmul["staged_weight_base_words"])),
                    int(matmul["staged_weight_base_words"]),
                )
                for matmul in matmuls
            ]
            last_matmul_words = len(matmuls[-1]["_expected_words"])
            last_matmul_macs = int(matmuls[-1]["mac_count"])
            last_result_words = len(head_rms_norms[-1]["_expected_words"])
            last_work_count = last_result_words
            matmul_output_bases = []
            for matmul in matmuls:
                matmul_expected = list(matmul.pop("_expected_words"))
                matmul_output_bases.append(
                    place(matmul["output_view"]["object_id"], matmul_expected)
                )
                case_matmul_words += len(matmul_expected)
                case_matmul_macs += int(matmul["mac_count"])
            for index, head in enumerate(head_rms_norms):
                agrees("head input", head["input_view"]["object_id"],
                       matmul_output_bases[index])
            head_weight_mappings = []
            head_output_bases = []
            for head in head_rms_norms:
                head_weight_base = len(source_words)
                source_words.extend(head.pop("_weight_words"))
                bind(head["weight_view"]["object_id"], head_weight_base)
                head_expected = list(head.pop("_expected_words"))
                head_output_bases.append(
                    place(head["output_view"]["object_id"], head_expected)
                )
                case_head_rms_words += len(head_expected)
                case_head_rms_checkpoint_bytes += int(
                    head["weight_source"]["selected_row_bytes"]
                )
            for index, rope in enumerate(ropes):
                agrees("rope input", rope["input_view"]["object_id"],
                       head_output_bases[index])
            agrees("rope coefficient",
                   ropes[0]["coefficient_view"]["object_id"], output_base)
            for rope in ropes:
                rope_expected = list(rope.pop("_expected_words"))
                place(rope["output_view"]["object_id"], rope_expected)
                case_rope_output_words += len(rope_expected)
            last_result_words = int(ropes[-1]["row_count"] * ropes[-1]["row_width"])
            last_work_count = last_result_words
        else:
            transfer = transfers[0]
            transfer_index_base = len(index_words)
            index_words.extend([0, 0, 0, 0])
            transfer_expected = list(transfer.pop("_expected_words"))
            place(transfer["output_view"]["object_id"], transfer_expected)
            case_transfer_words = len(transfer_expected)
            last_result_words = len(transfer_expected)
            last_work_count = 4
        case_launches = (
            len(gathers) + 2 + len(matmuls) + len(head_rms_norms) + len(ropes)
        )
        case_result_words = (
            case_rope_words
            + case_embedding_words
            + case_rms_words
            + case_transfer_words
            + case_matmul_words
            + case_head_rms_words
            + case_rope_output_words
        )

        state_count = int(source_case[34])
        if state_count != 0:
            raise SystemExit(f"{target.key}: production profile contains STATE")
        boundary_identity = BOUNDARY_IDENTITIES_BY_TARGET[target.key]
        derived["boundary"] = resolve_boundary(
            deployment,
            kernel_ir,
            boundary_identity,
            target_key=target.key,
            observed_descriptor_id=int(unsupported["descriptor_id"]),
        )
        expected_boundary = (
            boundary_identity.pc,
            boundary_identity.major,
            boundary_identity.sub,
            derived["boundary"].descriptor_id,
            boundary_identity.opcode,
        )
        expected_counts = EXPECTED_COUNTS_BY_TARGET[target.key]
        observed_counts = {
            "fetched": fetched,
            "retired": retired,
            "issued": issued,
            "loop_iterations": loop_iterations,
            "wait_events": wait_events,
            "signals": signals,
            "views": len(prefix_views),
        }
        for role, resolution in sorted(derived.items()):
            contract_observations.append(
                {
                    "target": target.key,
                    "role": resolution.role,
                    "executed": role != "boundary",
                    "descriptor_id": resolution.descriptor_id,
                    "numeric_profile_id": resolution.numeric_profile_id,
                    "numeric_signature": resolution.numeric_signature,
                    "contract_sha256": resolution.contract_sha256,
                    "kernel_declared_input_dtypes": list(
                        resolution.declared_input_dtypes
                    ),
                    # Read off the emitted descriptor, so the check below
                    # compares the profile with the operands it actually
                    # binds rather than with the graph it came from.
                    "bound_input_dtypes": _bound_input_dtypes(
                        deployment, resolution.descriptor_id
                    ),
                }
            )
        observed_boundary = (
            unsupported["pc"],
            unsupported["family"],
            unsupported["sub"],
            unsupported["descriptor_id"],
            unsupported["opcode"],
        )
        if observed_boundary != expected_boundary:
            raise SystemExit(
                f"{target.key}: next fail-stop boundary {observed_boundary}, "
                f"expected {expected_boundary}"
            )
        if observed_counts != expected_counts:
            raise SystemExit(
                f"{target.key}: prefix counts {observed_counts}, expected "
                f"{expected_counts}"
            )

        words = [
            int(source_case[0]),  # deployed program-image base
            int(source_case[1]),  # instruction count
            int(source_case[2]),  # descriptor-image base
            int(source_case[3]),  # descriptor count
            int(source_case[4]),  # symbol-image base
            int(source_case[5]),  # symbol bound mask
            entry_pc,
            int(source_case[8]),  # max retired work, low
            int(source_case[9]),  # max retired work, high
            state_count,
            index_base,
            source_base,
            source_stride,
            output_base,
            case_launches,
            case_result_words,
            unsupported["pc"],
            (unsupported["family"] << 8) | unsupported["sub"],
            unsupported["descriptor_id"],
            expected_counts["fetched"],
            expected_counts["retired"],
            expected_counts["issued"],
            expected_counts["loop_iterations"],
            expected_counts["signals"],
            expected_counts["views"],
            INDEX_VALUE,
            int(gathers[0]["source_view"]["dims"][0]),
            EMBED_WIDTH,
            target_index,
            1,  # one capability response
            0,  # descriptor/engine faults
            len(issue_words) // 4,  # expected response-stream base
            embedding_source_base,
            len(gathers),
            1,  # one embedding launch
            expected_counts["wait_events"],
            case_rope_words,
            case_embedding_words,
            EMBED_TOKEN,
            trailing,
            transfer_index_base,
            transfer_source_base,
            len(rms_norms),
            len(transfers),
            case_rms_words,
            case_transfer_words,
            len(matmuls),
            last_matmul_words,
            last_matmul_macs,
            len(head_rms_norms),
            last_result_words,
            last_work_count,
            case_head_rms_words,
            case_head_rms_checkpoint_bytes,
            len(ropes),
            case_rope_output_words,
            0,
        ]
        # -- the object placement table ---------------------------------
        # Emitted from the placement this case's own walk allocated, sorted by
        # object id so the record is a function of the walk and not of the
        # order the builder happened to visit the operators in.  Every object
        # the bridge will be asked to resolve is here, exactly once.
        words.append(len(expected_words) - output_base)  # PLACE_SPAN_WORD
        words.append(1)  # PLACE_VALID_WORD: this vector set supplied a table
        # This vector set stops at its fail-stop boundary and carries no
        # golden for the six mapped families, so it does not admit them.  The
        # refusal is a measurement the campaign records, not an unwired pin.
        words.append(0)  # MAPPED_FAMILIES_WORD
        if len(placement) > PLACE_TABLE_ENTRIES:
            raise SystemExit(
                f"{target.key}: this case names {len(placement)} distinct "
                f"objects and the bridge's table holds {PLACE_TABLE_ENTRIES}"
            )
        for object_id in sorted(placement):
            words.extend([int(object_id), int(placement[object_id])])
        for _ in range(PLACE_TABLE_ENTRIES - len(placement)):
            words.extend([NO_OBJECT, 0])
        words.extend([0] * (CASE_STRIDE - len(words)))
        if len(words) != CASE_STRIDE:
            raise SystemExit("internal case-record length error")
        if words[PLACE_SPAN_WORD] != len(expected_words) - output_base:
            raise SystemExit("the case result span word drifted")
        bound = [
            words[PLACE_TABLE_WORD + entry * 2]
            for entry in range(PLACE_TABLE_ENTRIES)
            if words[PLACE_TABLE_WORD + entry * 2] != NO_OBJECT
        ]
        if len(bound) != len(set(bound)):
            raise SystemExit(
                "the placement table names an object twice; the bridge "
                "refuses such a table and this builder will not emit one"
            )
        if sorted(bound) != sorted(placement):
            raise SystemExit(
                "the placement table and the walk's own placement disagree"
            )
        if words[MAP_RESERVED_WORD] != 0:
            raise SystemExit("the placement reserved word is not zero")
        case_words.extend(words)
        for gather in gathers:
            issue_words.extend(
                [
                    (int(Major.DMA) << 8) | int(Dma.GATHER),
                    int(gather["descriptor_id"]),
                    int(gather["pc"]),
                    0,
                ]
            )
        issue_words.extend(
            [
                (int(Major.TENSOR) << 8) | int(Tensor.EMBED_LOOKUP),
                int(embedding["descriptor_id"]),
                int(embedding["pc"]),
                0,
            ]
        )
        if rms_norms:
            rms_norm = rms_norms[0]
            issue_words.extend(
                [
                    (int(Major.VECTOR) << 8) | int(Vector.RMS_NORM),
                    int(rms_norm["descriptor_id"]),
                    int(rms_norm["pc"]),
                    0,
                ]
            )
            for matmul in matmuls:
                issue_words.extend(
                    [
                        (int(Major.TENSOR) << 8) | int(Tensor.MATMUL),
                        int(matmul["descriptor_id"]),
                        int(matmul["pc"]),
                        0,
                    ]
                )
            for head_rms_norm in head_rms_norms:
                issue_words.extend(
                    [
                        (int(Major.VECTOR) << 8) | int(Vector.HEAD_RMS_NORM),
                        int(head_rms_norm["descriptor_id"]),
                        int(head_rms_norm["pc"]),
                        0,
                    ]
                )
            for rope in ropes:
                issue_words.extend(
                    [
                        (int(Major.VECTOR) << 8) | int(Vector.ROPE),
                        int(rope["descriptor_id"]),
                        int(rope["pc"]),
                        0,
                    ]
                )
        else:
            transfer = transfers[0]
            issue_words.extend(
                [
                    (int(Major.DMA) << 8) | int(Dma.TRANSFER),
                    int(transfer["descriptor_id"]),
                    int(transfer["pc"]),
                    0,
                ]
            )
        issue_words.extend(
            [
                (unsupported["family"] << 8) | unsupported["sub"],
                unsupported["descriptor_id"],
                unsupported["pc"],
                unsupported["trap_class"],
            ]
        )
        total_launches += case_launches
        total_gathers += len(gathers)
        total_embeddings += 1
        total_rms_norms += len(rms_norms)
        total_head_rms_norms += len(head_rms_norms)
        total_rope_launches += len(ropes)
        total_transfers += len(transfers)
        total_matmuls += len(matmuls)
        total_rope_words += case_rope_words
        total_rms_words += case_rms_words
        total_head_rms_words += case_head_rms_words
        total_rope_output_words += case_rope_output_words
        total_transfer_words += case_transfer_words
        total_matmul_words += case_matmul_words
        total_matmul_macs += case_matmul_macs
        embedding_checkpoint_bytes = int(embedding["source"]["selected_row_bytes"])
        rms_checkpoint_bytes = (
            int(rms_norms[0]["weight_source"]["selected_row_bytes"]) if rms_norms else 0
        )
        total_embedding_checkpoint_bytes += embedding_checkpoint_bytes
        total_rms_checkpoint_bytes += rms_checkpoint_bytes
        total_head_rms_checkpoint_bytes += case_head_rms_checkpoint_bytes
        matmul_checkpoint_bytes = sum(
            int(matmul["weight_source"]["declared_segment_bytes"]) for matmul in matmuls
        )
        total_matmul_checkpoint_bytes += matmul_checkpoint_bytes
        total_checkpoint_bytes += (
            embedding_checkpoint_bytes
            + rms_checkpoint_bytes
            + case_head_rms_checkpoint_bytes
            + matmul_checkpoint_bytes
        )
        total_views += expected_counts["views"]
        records.append(
            {
                "name": case_name,
                "deployment": target.key,
                "deployment_sha256": deployment_sha,
                "deployment_identity_evidence": expected_identity.record(),
                "descriptor_derivation": {
                    "method": (
                        "every governed descriptor ID is derived from the "
                        "certified Kernel IR kernel it lowers, its engine "
                        "family and sub-opcode, its numeric contract digest "
                        "and its bound payload slots, then searched for in "
                        "this bundle's own descriptor table and required to "
                        "resolve uniquely; no descriptor ID is written down"
                    ),
                    "kernel_ir": kernel_ir["path"],
                    "kernel_ir_sha256": kernel_ir["sha256"],
                    "kernel_ir_graph_id": kernel_ir["graph_id"],
                    "descriptor_table_sha256": deployment.table.digest.hex(),
                    "operations": [
                        {"slot": slot, **resolution.record()}
                        for slot, resolution in sorted(derived.items())
                    ],
                },
                "input_deployment_vector_case": deployment_case_index,
                "request": {
                    "entrypoint_id": 1,
                    "phase": "decode",
                    "prompt_tokens": PROMPT_TOKENS,
                    "position_start": INDEX_VALUE,
                    "embedding_token_id": EMBED_TOKEN,
                    "embedding_probe_scope": (
                        "bounded synthetic legal-vocabulary probe; not a "
                        "natural-language or end-to-end model claim"
                    ),
                    "symbols": {str(k): v for k, v in sorted(symbols.items())},
                },
                "bank_mapping": {
                    # The four staged REGIONS the vehicle sweeps by launch
                    # counter, which are not ABI objects and have no entry in
                    # the placement table.
                    "index_base": index_base,
                    "source_base": source_base,
                    "source_launch_stride": source_stride,
                    "embedding_source_base": embedding_source_base,
                    "transfer_index_base": transfer_index_base,
                    "transfer_source_base": transfer_source_base,
                    # Everything else is one object -> base function, the same
                    # one the case record hands the bridge.  The nine per-role
                    # entries this block used to publish were nine views of
                    # this one table, and nothing made them agree.
                    "result_region_base": output_base,
                    "result_region_span": (
                        len(expected_words) - output_base
                    ),
                    "object_placement": [
                        {"object_id": object_id, "base_words": base_words}
                        for object_id, base_words in sorted(placement.items())
                    ],
                    "objects_written_more_than_once": sorted(
                        object_id for object_id, count in rewrite_count.items()
                        if count > 1
                    ),
                },
                "expected": {
                    **expected_counts,
                    "real_engine_launches": case_launches,
                    "dma_gather_launches": len(gathers),
                    "embedding_launches": 1,
                    "rms_norm_launches": len(rms_norms),
                    "head_rms_norm_launches": len(head_rms_norms),
                    "rope_launches": len(ropes),
                    "dma_transfer_launches": len(transfers),
                    "matmul_launches": len(matmuls),
                    "rope_coefficient_gather_result_words": case_rope_words,
                    "rope_result_words": case_rope_output_words,
                    "embedding_result_words": case_embedding_words,
                    "rms_norm_result_words": case_rms_words,
                    "head_rms_norm_result_words": case_head_rms_words,
                    "dma_transfer_result_words": case_transfer_words,
                    "matmul_result_words": case_matmul_words,
                    "matmul_mac_count": case_matmul_macs,
                    "selected_embedding_checkpoint_bytes": (embedding_checkpoint_bytes),
                    "selected_rms_checkpoint_bytes": rms_checkpoint_bytes,
                    "selected_head_rms_checkpoint_bytes": (
                        case_head_rms_checkpoint_bytes
                    ),
                    "selected_matmul_checkpoint_bytes": (matmul_checkpoint_bytes),
                    "selected_checkpoint_bytes": (
                        embedding_checkpoint_bytes
                        + rms_checkpoint_bytes
                        + case_head_rms_checkpoint_bytes
                        + matmul_checkpoint_bytes
                    ),
                    "result_words": case_result_words,
                    "trap_class": 4,
                    "first_fault_instruction": unsupported["pc"],
                    "complete": False,
                    "state_compat": 0,
                },
                "supported_prefix": [
                    {key: value for key, value in gather.items()} for gather in gathers
                ]
                + [{key: value for key, value in embedding.items()}]
                + [
                    {key: value for key, value in operation.items()}
                    for operation in (
                        rms_norms + matmuls + transfers + head_rms_norms + ropes
                    )
                ],
                "first_unsupported": unsupported,
                "resolved_prefix_views": prefix_views,
            }
        )

    if (
        total_launches != 28
        or total_gathers != 6
        or total_embeddings != 4
        or total_rms_norms != 2
        or total_head_rms_norms != 4
        or total_rope_launches != 4
        or total_transfers != 2
        or total_matmuls != 6
        or total_rope_words != 1_024
        or total_rms_words != 8_192
        or total_head_rms_words != 10_240
        or total_rope_output_words != 10_240
        or total_transfer_words != 32_768
        or total_matmul_words != 12_288
        or total_matmul_macs != 50_331_648
        or len(write_data) != 91_136
        or total_embedding_checkpoint_bytes != 32_768
        or total_rms_checkpoint_bytes != 16_384
        or total_head_rms_checkpoint_bytes != 1_024
        or total_matmul_checkpoint_bytes != 100_663_296
        or total_checkpoint_bytes != 100_713_472
        or staged_matmul_bytes != 50_331_648
        or total_views != 94
    ):
        raise SystemExit(
            "witness depth changed: "
            f"launches={total_launches}, gathers={total_gathers}, "
            f"embeddings={total_embeddings}, rope_words={total_rope_words}, "
            f"rms_norms={total_rms_norms}, transfers={total_transfers}, "
            f"head_rms_norms={total_head_rms_norms}, "
            f"ropes={total_rope_launches}, "
            f"matmuls={total_matmuls}, "
            f"rms_words={total_rms_words}, "
            f"head_rms_words={total_head_rms_words}, "
            f"rope_output_words={total_rope_output_words}, "
            f"transfer_words={total_transfer_words}, "
            f"matmul_words={total_matmul_words}, "
            f"matmul_macs={total_matmul_macs}, "
            f"writes={len(write_data)}, image={len(expected_words)}, "
            f"embedding_checkpoint_bytes={total_embedding_checkpoint_bytes}, "
            f"rms_checkpoint_bytes={total_rms_checkpoint_bytes}, "
            "head_rms_checkpoint_bytes="
            f"{total_head_rms_checkpoint_bytes}, "
            f"matmul_checkpoint_bytes={total_matmul_checkpoint_bytes}, "
            f"checkpoint_bytes={total_checkpoint_bytes}, views={total_views}"
        )
    files = {
        "p3_case.hex": _hex_lines(case_words),
        "p3_issue.hex": _hex_lines(issue_words),
        "p3_index.hex": _hex_lines(index_words, total=INDEX_WORDS),
        "p3_source.hex": _hex_lines(source_words, total=SOURCE_WORDS),
        "p3_expect.hex": _hex_lines(expected_words),
        # The write STREAM: one line per word the engines write, in launch
        # order, address first then value.  The retained image above is what
        # survives; this is what happened.  They differ exactly where the
        # program rewrites a buffer, and comparing only the image would stop
        # checking the value that was overwritten.
        "p3_writes.hex": _hex_lines(
            [word for pair in zip(write_addr, write_data) for word in pair]
        ),
        "p3_meta.hex": _hex_lines(
            [
                len(records),
                total_launches,
                len(write_data),
                total_views,
                CASE_STRIDE,
                INDEX_WORDS,
                SOURCE_WORDS,
                RESULT_WORDS,
                total_gathers,
                total_embeddings,
                total_rope_words,
                total_checkpoint_bytes,
                total_rms_norms,
                total_transfers,
                total_rms_words,
                total_transfer_words,
                total_matmuls,
                total_matmul_words,
                total_matmul_macs,
                total_matmul_checkpoint_bytes,
                total_head_rms_norms,
                total_head_rms_words,
                total_head_rms_checkpoint_bytes,
                total_rms_norms + total_head_rms_norms,
                total_rope_launches,
                total_rope_output_words,
                # meta[26]: words the retained image spans.  It is smaller
                # than meta[1]'s write count by exactly the words a rewritten
                # buffer gave up, and the two are separate because one is what
                # survives and the other is what ran.
                len(expected_words),
            ]
        ),
    }
    for name, payload in files.items():
        (args.output / name).write_text(payload, encoding="ascii")

    contract_disagreements = _audit_contract_agreement(contract_observations)
    profile_slot_disagreements = _audit_profile_slot_agreement(contract_observations)

    marker = (
        "PASS: ABI3 shipped-prefix engine integration "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(write_data)} capability_faults={len(records)}"
    )
    summary = {
        "schema": VECTOR_SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "state_compat": 0,
        "request_scope": {
            "phase": "decode",
            "prompt_tokens": PROMPT_TOKENS,
            "position_start": INDEX_VALUE,
            "embedding_token_id": EMBED_TOKEN,
            "embedding_probe_scope": (
                "bounded synthetic legal-vocabulary probe; not a "
                "natural-language or end-to-end model claim"
            ),
        },
        "claim": (
            "exact shipped decode-program prefixes: six real DMA.GATHER "
            "launches copy 1,024 authentic generated RoPE words and four "
            "TENSOR.EMBED_LOOKUP launches copy 16,384 BF16 codes from four "
            "bounded, authenticated checkpoint-row reads; two exact Qwen "
            "VECTOR.RMS_NORM launches produce 8,192 BF16 codes using two "
            "bounded gain reads, and two DeepSeek stride-zero DMA.TRANSFER "
            "launches produce 32,768 BF16 codes from the prior embedding "
            "result; six complete Qwen layer-zero query/key/value "
            "TENSOR.MATMUL launches consume 100,663,296 authenticated BF16 "
            "weight bytes, execute 50,331,648 MACs, and produce 12,288 BF16 "
            "codes; four Qwen weighted VECTOR.HEAD_RMS_NORM launches then "
            "normalize 40 independent 128-code heads and produce 10,240 "
            "BF16 codes from four bounded authenticated gain reads; four "
            "Qwen VECTOR.ROPE launches consume those exact results and the "
            "previously gathered FP32 coefficient row, agree with an "
            "independent scalar oracle, and produce 10,240 BF16 codes; Qwen "
            "then fails closed at DMA.SCATTER and DeepSeek at "
            "LINK.MULTICAST or VECTOR.MHC; this is not a whole-model, "
            "prefill, token-selection, or decoding claim"
        ),
        "supported_profile": (
            "dense one-index FP32 DMA.GATHER plus exact token-zero BF16 "
            "TENSOR.EMBED_LOOKUP with 4,096-code rows, exact one-row Qwen "
            "BF16 RMSNorm, three descriptor-driven Qwen 1x4096 query/key/value "
            "MATMUL launches with 4,096/1,024/1,024 output columns through the "
            "declared single-lane ascending-K association, plus weighted "
            "Qwen head RMSNorm over descriptor-selected 32x128 and 8x128 "
            "row sets, and Qwen whole-head RoPE with FP32-to-BF16 RNE "
            "coefficient narrowing over those same row sets, "
            "and DeepSeek four-copy stride-zero BF16 transfer; "
            "resolved views, unscaled operands, and numeric contracts are "
            "bound before each launch"
        ),
        "unsupported_policy": (
            "every other family/subopcode returns CAPABILITY before any engine "
            "launch, result write, retirement, or signal publication"
        ),
        "case_count": len(records),
        "real_engine_launch_count": total_launches,
        "dma_gather_launch_count": total_gathers,
        "embedding_launch_count": total_embeddings,
        "rms_norm_launch_count": total_rms_norms,
        "head_rms_norm_launch_count": total_head_rms_norms,
        "rope_launch_count": total_rope_launches,
        "dma_transfer_launch_count": total_transfers,
        "matmul_launch_count": total_matmuls,
        "rope_coefficient_gather_result_word_count": total_rope_words,
        "rope_result_word_count": total_rope_output_words,
        "embedding_result_word_count": total_embeddings * EMBED_WIDTH,
        "rms_norm_result_word_count": total_rms_words,
        "head_rms_norm_result_word_count": total_head_rms_words,
        "dma_transfer_result_word_count": total_transfer_words,
        "matmul_result_word_count": total_matmul_words,
        "matmul_mac_count": total_matmul_macs,
        "selected_embedding_checkpoint_byte_count": (total_embedding_checkpoint_bytes),
        "selected_rms_checkpoint_byte_count": total_rms_checkpoint_bytes,
        "selected_head_rms_checkpoint_byte_count": (total_head_rms_checkpoint_bytes),
        "selected_matmul_checkpoint_byte_count": (total_matmul_checkpoint_bytes),
        "selected_checkpoint_byte_count": total_checkpoint_bytes,
        "staged_matmul_weight_layout": {
            "bytes": staged_matmul_bytes,
            "matrices": sorted(
                matrix_staging.values(), key=lambda item: int(item["base_words"])
            ),
        },
        # The words the engines WRITE.  It is what it has always been and it
        # has not moved; what is new is that it is no longer the same number
        # as the retained image's extent, because the span rewrites three of
        # its buffers.
        "result_word_count": len(write_data),
        "retained_image_word_count": len(expected_words),
        "retained_image_note": (
            "the retained image holds each object's LAST value, so it is "
            "smaller than result_word_count by exactly the words a rewrite "
            "replaces. p3_writes.hex carries every write, address and value, "
            "in launch order; it is what an operator's own output has to be "
            "compared against once a later operator can overwrite it"
        ),
        "resolved_view_count": total_views,
        "capability_fault_count": len(records),
        "required_marker": marker,
        "geometry": {
            "case_stride": CASE_STRIDE,
            "index_words": INDEX_WORDS,
            "source_words": SOURCE_WORDS,
            "result_words": RESULT_WORDS,
            "case_words_used": len(case_words),
            "issue_words_used": len(issue_words),
            "issue_stride": 4,
            "index_words_used": len(index_words),
            "source_words_used": len(source_words),
            "expected_words_used": len(expected_words),
        },
        "input_deployment_vectors": {
            "path": str(DEPLOYMENT_VECTOR_JSON.relative_to(ROOT)),
            "sha256": _sha256_file(DEPLOYMENT_VECTOR_JSON),
            "images": {
                name: _sha256_file(DEPLOYMENT_VECTOR_DIR / name)
                for name in INPUT_IMAGES
            },
        },
        "image_sha256": {
            name: hashlib.sha256(payload.encode("ascii")).hexdigest()
            for name, payload in sorted(files.items())
        },
        "descriptor_derivation": {
            "claim": (
                "no descriptor ID in this builder is written down.  Every "
                "governed operation is resolved against its own bundle by "
                "identity -- the certified Kernel IR kernel it lowers, its "
                "engine family and sub-opcode, its numeric contract digest "
                "cross-checked against that kernel's declared contract name, "
                "its aux_id_0 and its unbound payload slots -- and the "
                "resolution is required to be unique.  Zero matches and two "
                "matches are both refusals."
            ),
            "does_not_establish": [
                "that a descriptor ID is stable across lowerings; it is not, "
                "and the per-case derivations record different IDs for the "
                "two Qwen lowerings at all eight governed PCs",
                "that a fail-stop boundary descriptor resolves uniquely.  "
                "Where the record says resolution equivalence_class the "
                "deployment holds byte-identical descriptors that no identity "
                "can separate, and the observed ID is checked for membership "
                "of that class only",
                "any property of an operation the prefix does not execute, "
                "including the numeric contract of the boundary descriptor "
                "named in numeric_contract_disagreements",
                "that a numeric profile is CORRECT, only that it agrees with "
                "the views its own descriptor binds; "
                "profile_slot_disagreements is a self-consistency "
                "measurement, and a profile can be self-consistent and still "
                "name the wrong contract",
            ],
            "numeric_contract_disagreements": contract_disagreements,
            "profile_slot_disagreements": profile_slot_disagreements,
        },
        "cases": records,
    }
    (args.output / "abi3_shipped_prefix_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    window_bytes = emit_weight_window(
        summary, args.output / "p3_weight_window.txt"
    )
    golden = emit_golden(summary, args.output, args.output)
    print(
        f"abi3 shipped-prefix G1e golden: window_bytes={window_bytes} "
        f"issues={golden['issues']} views={golden['views']} "
        f"result_words={golden['result_words']}"
    )
    if BOOTSTRAP and _BOOTSTRAP_OBSERVED:
        #: Written to a file rather than printed: these are the pins a new target
        #: needs, and a file can be diffed into ORACLE_PINS without retyping hashes.
        observed_path = args.output / "oracle_pins_observed.json"
        observed_path.write_text(
            json.dumps(
                {
                    key: {
                        name: (list(value) if isinstance(value, tuple) else value)
                        for name, value in sorted(pins.items())
                    }
                    for key, pins in sorted(_BOOTSTRAP_OBSERVED.items())
                },
                indent=2,
                sort_keys=True,
            )
            + "\n"
        )
        print(f"  OT_A3_PREFIX_BOOTSTRAP: wrote observed pins to {observed_path}")
    print(
        "abi3 shipped-prefix vectors: "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(expected_words)} views={total_views}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
