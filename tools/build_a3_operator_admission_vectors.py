#!/usr/bin/env python3
"""Build exact vectors for the six newly admitted ABI 3.0 operator families.

``rtl/abi3/ot_a3_engine_issue_bridge.sv`` admitted seven opcode forms and
returned TRAP_CAPABILITY for everything else.  Six of the families it refused
are families a Qwen3 decode cannot omit -- ``DMA.SCATTER``, ``ATTENTION.GQA``,
``VECTOR.ADD``, ``VECTOR.SILU_MUL``, ``SELECTION.ARGMAX`` and
``SELECTION.TOKEN_APPEND`` -- so the governed decode program could not be
issued past PC 32 at all.  These vectors drive the admitted bridge with the
*retained shipped* OPERATOR, TENSOR_VIEW, NUMERIC and GENERATION_POLICY
records of those exact program counters, the sequencer's resolved view stream
for each, and expected results computed by the independent scalar references
in ``runtime/reference`` -- never by the DUT and never by the functional
simulator's array kernels.

What the operands are, stated once and not softened:

* the attention query and the current key and value rows are the retained
  causal RTL results of the shipped decode prefix (PCs 26, 29 and 17), the
  same authentic activations the PC38 GQA campaign binds;
* the earlier KV context rows are deterministic permutations of that
  authentic row, exactly as the PC38 campaign constructs them, and are not
  model history;
* the residual, SwiGLU and logits operands are a seeded deterministic BF16
  spread over the governed shapes.  They are not checkpoint activations, and
  nothing here claims a layer, a token or a rate.  What they establish is that
  the RTL's arithmetic equals the golden model's, bit for bit, at the shapes
  the governed decode program issues.

Cases run in order against one bank that is loaded once, so a scatter's write
is the attention's read.  That is deliberate: an operator campaign that reloads
between operators cannot see a handoff.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    Dma,
    Major,
    NO_ID,
    Selection,
    Tensor,
    Vector,
)
from runtime.abi3.descriptors import (  # noqa: E402
    Descriptor,
    DESCRIPTOR_HEADER,
    ExtendedDescriptorType,
    Symbol,
)
from runtime.abi3.records import Instruction  # noqa: E402
from runtime.reference.tensor_accelerator_attention import (  # noqa: E402
    gqa_causal_attention_bf16,
    make_kv_snapshot,
    prepare_kv_append,
)
from runtime.reference.tensor_accelerator_elementwise import (  # noqa: E402
    bf16_add_rne,
    qwen3_silu_mul_bf16,
)
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    rms_norm_bf16,
)
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    dense_bf16_linear_bf16,
)
from runtime.reference.tensor_accelerator_rope import rope_bf16  # noqa: E402
from runtime.sim.memory import ViewResolver  # noqa: E402
from tools import build_a3_qwen_gqa_vectors as gqa  # noqa: E402
from tools.build_abi3_deployment_rtl_vectors import TARGETS as RTL_TARGETS  # noqa: E402
from tools import build_a3_qwen_kv_scatter_vectors as scatter  # noqa: E402


OUTPUT_ROOT = ROOT / "testdata/rtl/a3_operator_admission"
SCHEMA = "opentallas.rtl.a3_operator_admission_vectors.v1"

# The two Qwen lowerings this vehicle can be built for.  It was bound to the
# ROM key alone, which left the HBM lowering with no operator evidence at all
# and made rung G1a's hbm record an empty one.  The two lowerings are NOT
# interchangeable -- their governed descriptor ids differ at every PC, and at
# PCs 32/35 the DMA.SCATTER NUMERIC descriptor's input_dtype and
# second_input_dtype are swapped under one identical contract digest -- so
# each is built and simulated on its own bundle and neither borrows the
# other's result.
TARGETS = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}
DEFAULT_STORAGE_CLASS = "rom"
TARGET_KEY = TARGETS[DEFAULT_STORAGE_CLASS]


def output_root_for(storage_class: str) -> Path:
    """Where one storage class's vectors live.

    ``rom`` keeps the original path so the retained ROM images and every
    artifact that binds them stay exactly where they are.
    """

    if storage_class == DEFAULT_STORAGE_CLASS:
        return OUTPUT_ROOT
    return ROOT / f"testdata/rtl/a3_operator_admission_{storage_class}"

CASE_WORDS = 128
VIEW_SLOTS = 5
VIEW_WORDS = 8
# One entry per port of the bridge's object placement table.  It was 8, which
# is not a property of the design -- the bridge declares 32 -- but of this
# vector format, and it capped the number of objects any run could bind at
# once well below what a transformer layer names.  The map moves to word
# MAP_BASE so the 32 (object, base) pairs do not collide with the scalar
# fields, and CASE_WORDS grows with it.
MAP_ENTRIES = 32
MAP_BASE = 64

# The governed decode program counters of the six mapped families.
PC_SCATTER_KEY = 32
PC_SCATTER_VALUE = 35
PC_GQA = 38
PC_ADD_ATTENTION = 44
PC_SILU_MUL = 56
PC_ADD_MLP = 62
PC_ARGMAX = 70
PC_TOKEN_APPEND = 72

# The governed decode program counters of the four object-keyed families the
# bridge already admitted.  They are here for one reason: every one of them
# resolves its operands through the SAME object table the six mapped families
# use, so a case that issues one of them binds and resolves objects the six
# never name.  The layer's placement demand is a demand on that one table, and
# only a run that binds and resolves the objects can measure its depth.
PC_RMS_NORM_ATTENTION = 8
PC_HEAD_RMS_QUERY = 20
PC_HEAD_RMS_KEY = 23
PC_ROPE_QUERY = 26
PC_ROPE_KEY = 29
PC_RMS_NORM_MLP = 47
PC_RMS_NORM_HEAD = 66
# Three program counters of the same layer, and one of the head span, whose
# operand views this bridge does not admit at all.  They are issued here as
# fail-closed cases because the answer matters to the placement measurement:
# an object that no admitted operator can name is an object no run can ever
# resolve, and that is a bound on the table depth any campaign can reach.
PC_MATMUL_GATE = 50
PC_MATMUL_UP = 53
PC_MATMUL_DOWN = 59
PC_HEAD_GATHER = 68
# The prefix PCs whose retained golden write stream this campaign replays.
# PCs 47 and 66 are NOT among them: the shipped prefix stops at PC 32, so
# their RMSNorm gains are not in the retained source bank and their operands
# are a seeded spread with only the scalar oracle behind them.
# PC 1 appears twice over: its retained result is the coefficient row the two
# RoPE cases read, and the instruction itself is ALSO issued here, because
# G1a's per-campaign coverage rule needs one campaign to drive both operator
# descriptors of the ROM lowering's merged DMA.GATHER class.  The issued case
# does not gather the coefficient table -- see its own note.
PC_ROPE_COEFFICIENT_GATHER = 1
PC_EMBED_LOOKUP = 4
PC_MATMUL_QUERY = 11
PC_MATMUL_KEY = 14
PC_MATMUL_VALUE = 17
PREFIX_REPLAY_PCS = (
    PC_RMS_NORM_ATTENTION,
    PC_HEAD_RMS_QUERY,
    PC_HEAD_RMS_KEY,
    PC_ROPE_QUERY,
    PC_ROPE_KEY,
)

QUERY_HEADS = 32
KV_HEADS = 8
HEAD_WIDTH = 128
KV_PLANE_WORDS = KV_HEADS * HEAD_WIDTH
GQA_OUTPUT_WORDS = QUERY_HEADS * HEAD_WIDTH
KV_PLANE_ROWS = 19
ADD_WIDTH = 4096
SILU_WIDTH = 12288
VOCABULARY = 151936
EOS_TOKEN = 151645

# Compact verification-bank placement.  Each object of the governed program
# gets one base; the interleaved KV cache object gets one compact key plane and
# one compact value plane a fixed KV_PLANE_ROWS apart, which is exactly the
# remap the bridge performs from the view's resolved plane offset.
BASE_KV = 0
BASE_SCATTER_KEY_SOURCE = BASE_KV + 2 * KV_PLANE_ROWS * KV_PLANE_WORDS
BASE_SCATTER_VALUE_SOURCE = BASE_SCATTER_KEY_SOURCE + KV_PLANE_WORDS
# The governed program reuses two scratch objects: the RoPE'd query, the
# attention projection and the MLP down projection all land in one, and the
# attention result and the first residual sum land in the other.  One base per
# object is the only faithful layout, and it is exactly why an append cursor
# cannot place these operators.
BASE_SCRATCH_A = BASE_SCATTER_VALUE_SOURCE + KV_PLANE_WORDS
BASE_SCRATCH_B = BASE_SCRATCH_A + ADD_WIDTH
BASE_TRUNK = BASE_SCRATCH_B + ADD_WIDTH
BASE_SILU_GATE = BASE_TRUNK + ADD_WIDTH
BASE_SILU_UP = BASE_SILU_GATE + SILU_WIDTH
BASE_SILU_OUT = BASE_SILU_UP + SILU_WIDTH
BASE_LOGITS = BASE_SILU_OUT + SILU_WIDTH
BASE_TOKEN = BASE_LOGITS + VOCABULARY
BASE_RING = BASE_TOKEN + 1
# The generated-token ring is the ONE object whose extent is not the same on
# both lowerings.  The ROM lowering's PC-72 output view resolves at element
# offset 0, so one word held it; the HBM lowering's resolves at the generated
# position -- offset 17 at the governed context -- and a one-word ring made
# the bridge write past the end of the bank.  The ring is therefore sized from
# the resolved view itself, per lowering, and BANK_WORDS below is only the
# default for a lowering that resolves at offset 0.
BANK_WORDS = BASE_RING + 1
INDEX_WORDS = 64

# The four object-keyed families the bridge already admitted read a weight-side
# operand that is NOT in the result bank: `m1_reads_result` is low for a
# RMSNorm gain, so the gain lands in the source bank the vehicle stages, at the
# gain object's own base.  Two banks, one table: the bridge picks the bank from
# the reading slot and the base from the object, exactly as its header says.
# The dense row PC 68's DMA.GATHER selects.  ``cfg_source_base`` is a staged
# base and is NOT keyed by object (the role table of docs/CHIP_ARCHITECTURE
# _DESIGN.md section 13 item 27 says so), so a gather's source is a region
# this vehicle sweeps rather than object 45's home in the result bank.  The
# resolved index view names row 0, so the staged row sits at the front of
# this bank.  What is staged there is checked, at build time, to be word for
# word the PC 66 result the preceding case's RTL wrote into object 45.
BASE_SOURCE_GATHER_ROW = 0
BASE_SOURCE_RMS_GAIN_ATTENTION = BASE_SOURCE_GATHER_ROW + ADD_WIDTH
BASE_SOURCE_RMS_GAIN_MLP = BASE_SOURCE_RMS_GAIN_ATTENTION + ADD_WIDTH
BASE_SOURCE_RMS_GAIN_HEAD = BASE_SOURCE_RMS_GAIN_MLP + ADD_WIDTH
BASE_SOURCE_HEAD_GAIN_QUERY = BASE_SOURCE_RMS_GAIN_HEAD + ADD_WIDTH
BASE_SOURCE_HEAD_GAIN_KEY = BASE_SOURCE_HEAD_GAIN_QUERY + HEAD_WIDTH
SOURCE_WORDS = BASE_SOURCE_HEAD_GAIN_KEY + HEAD_WIDTH

TRAP_NONE = 0
TRAP_DESCRIPTOR = 3
TRAP_CAPABILITY = 4
TRAP_ENGINE = 8

LAUNCH_ADD = 0
LAUNCH_SILU = 1
LAUNCH_SCATTER = 2
LAUNCH_GQA = 3
LAUNCH_ARGMAX = 4
LAUNCH_TOKEN_APPEND = 5
LAUNCH_NONE = 6
LAUNCH_RMS_NORM = 7
LAUNCH_HEAD_RMS_NORM = 8
LAUNCH_ROPE = 9
LAUNCH_MATMUL = 10
LAUNCH_GATHER = 11
LAUNCH_EMBED = 12
LAUNCH_TRANSFER = 13

# Which of an operator's resolved views name an ABI object the bridge places
# through the table, per family.  Everything is object-keyed now except the
# three staged REGIONS the vehicle sweeps by launch counter -- a gather's index
# and source and an embedding's table -- and those are named here rather than
# assumed, so a case that used one could never be counted as placing an object.
UNKEYED_SLOTS: dict[tuple[int, int], tuple[int, ...]] = {
    (int(Major.DMA), int(Dma.GATHER)): (0, 1),
    (int(Major.DMA), int(Dma.TRANSFER)): (0, 1),
    (int(Major.TENSOR), int(Tensor.EMBED_LOOKUP)): (0, 1),
}

VECTOR_FILES = (
    "cases.hex",
    "views.hex",
    "descriptors.hex",
    "bank.hex",
    "index.hex",
    "source.hex",
    "preload.hex",
    "expected.hex",
    "weights.hex",
    "index.json",
)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bf16_to_float(code: int) -> float:
    return struct.unpack("<f", struct.pack("<I", (code & 0xFFFF) << 16))[0]


class Spread:
    """A seeded deterministic BF16 spread; no host float arithmetic decides it.

    The exponent is drawn from a bounded window around 1.0 so that products and
    sums stay well inside binary32, and the sign and significand are drawn from
    the same 64-bit LCG.  Reproducible from the seed alone.
    """

    def __init__(self, seed: int) -> None:
        self.state = seed & ((1 << 64) - 1)

    def next(self) -> int:
        self.state = (self.state * 6364136223846793005 + 1442695040888963407) & (
            (1 << 64) - 1
        )
        return self.state >> 33

    def code(self, *, low_exponent: int, high_exponent: int) -> int:
        raw = self.next()
        sign = raw & 1
        exponent = low_exponent + ((raw >> 1) % (high_exponent - low_exponent + 1))
        significand = (raw >> 9) & 0x7F
        return (sign << 15) | (exponent << 7) | significand

    def row(self, count: int, *, low_exponent: int, high_exponent: int) -> list[int]:
        return [
            self.code(low_exponent=low_exponent, high_exponent=high_exponent)
            for _ in range(count)
        ]


PREFIX_SOURCE = scatter.PREFIX_ROOT / "p3_source.hex"


def retained_prefix_results(
    target_key: str,
) -> tuple[dict[int, list[int]], list[int], dict[int, int]]:
    """The shipped prefix's golden write stream, source bank and placement.

    The four object-keyed families this campaign adds are replayed against the
    prefix's OWN retained evidence rather than against a seeded spread: each
    operator's input is the golden value the preceding operator wrote, its
    weight-side operand is the real checkpoint gain in the retained source
    bank, and its expected result is the golden write stream's own words for
    that program counter.  The expectation is nevertheless COMPUTED here by the
    independent scalar reference and then required to equal the retained
    golden; a disagreement is a refusal, not a preference for either.

    The witness is checked the way ``build_a3_qwen_kv_scatter_vectors.build``
    checks it -- schema, a passing integrated replay, and the digest of every
    image this function reads -- so a stale or edited upstream artifact refuses
    the build instead of silently changing what "authentic" means.
    """

    prefix = json.loads(scatter.PREFIX_MANIFEST.read_text())
    campaign = json.loads(scatter.PREFIX_CAMPAIGN.read_text())
    if (
        prefix.get("schema") != "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
        or campaign.get("status") != "pass"
        or not campaign.get("integrated_replay_passed")
        or campaign["vector_set"]["sha256"] != sha256_file(scatter.PREFIX_MANIFEST)
        or sha256_file(scatter.PREFIX_WRITES)
        != prefix["image_sha256"]["p3_writes.hex"]
        or sha256_file(PREFIX_SOURCE) != prefix["image_sha256"]["p3_source.hex"]
    ):
        raise RuntimeError("retained upstream RTL result witness is not current")

    words = scatter.prefix_write_values()
    source = scatter.read_hex(PREFIX_SOURCE)
    cursor = 0
    by_pc: dict[int, list[int]] = {}
    placement: dict[int, int] = {}
    for case in prefix["cases"]:
        count = int(case["expected"]["result_words"])
        if case["deployment"] == target_key:
            for pc, (start, length) in scatter.operation_word_ranges(case).items():
                by_pc[int(pc)] = words[cursor + start : cursor + start + length]
            placement = {
                int(entry["object_id"]): int(entry["base_words"])
                for entry in case["bank_mapping"]["object_placement"]
            }
        cursor += count
    if not by_pc or not placement:
        raise RuntimeError(
            f"the retained shipped prefix carries no case for {target_key}"
        )
    return by_pc, source, placement


def checkpoint_projection(
    target_key: str, deployment: dict[str, Any], object_id: int,
    *, rows: int, columns: int,
) -> tuple[list[int], dict[str, Any]]:
    """One complete layer-zero projection matrix, from the real checkpoint.

    Nothing about this matrix is typed here.  The retained deployment record
    names the directory and the digest of the deployment that produced the
    program these vectors issue; that deployment's own object table names the
    shard, the byte offset and the SHA-256 of every segment the object is
    built from, and the first segment of a Qwen projection object is its
    layer-zero matrix.  The bytes are re-read from the checkpoint and hashed
    against the digest the deployment declared, so a checkpoint that is not
    the one the program was compiled against is a build failure rather than a
    different set of numbers.  The matrix is staged rather than committed:
    8,388,608 bytes per projection is not a thing to put in Git, and the
    campaign binds the staged image by SHA-256 instead.
    """

    root = ROOT / str(deployment["deployment_dir"])
    record = json.loads((root / "deployment.json").read_text())
    if str(record["deployment_sha256"]) != str(deployment["deployment_sha256"]):
        raise SystemExit(
            f"{root}/deployment.json is deployment "
            f"{record['deployment_sha256'][:12]}, but the retained vector "
            f"manifest binds {deployment['deployment_sha256'][:12]}"
        )
    objects = {int(item["object_id"]): item for item in record["objects"]}
    if object_id not in objects:
        raise SystemExit(f"deployment object {object_id} is not in its own table")
    source = objects[object_id]["source"]
    if source.get("kind") != "segments" or not source.get("segments"):
        raise SystemExit(f"object {object_id} is not a segment-backed weight")
    segment = source["segments"][0]
    matrix_bytes = rows * columns * 2
    if int(segment["bytes"]) != matrix_bytes:
        raise SystemExit(
            f"object {object_id} first segment carries {segment['bytes']} "
            f"bytes; the resolved view says {rows} x {columns} BF16 = "
            f"{matrix_bytes}"
        )
    checkpoint = None
    for entry in RTL_TARGETS:
        if getattr(entry, "key", None) == target_key:
            checkpoint = Path(str(entry.checkpoint)).expanduser()
    if checkpoint is None:
        raise SystemExit(f"{target_key} names no checkpoint in the target table")
    path = checkpoint / str(segment["path"])
    offset = int(segment["offset"])
    if offset + matrix_bytes > path.stat().st_size:
        raise SystemExit("the selected matrix runs past its checkpoint shard")
    with path.open("rb") as handle:
        handle.seek(offset)
        payload = handle.read(matrix_bytes)
    if len(payload) != matrix_bytes:
        raise SystemExit("the checkpoint returned a short matrix segment")
    observed = hashlib.sha256(payload).hexdigest()
    if observed != str(segment["sha256"]):
        raise SystemExit(
            f"object {object_id} layer-zero segment hashes {observed[:12]}, "
            f"the deployment declares {str(segment['sha256'])[:12]}"
        )
    codes = list(struct.unpack(f"<{rows * columns}H", payload))
    return codes, {
        "object_id": object_id,
        "shape": [rows, columns],
        "dtype": "BF16",
        "checkpoint": str(checkpoint),
        "checkpoint_revision": checkpoint.name,
        "shard": str(segment["path"]),
        "segment_offset": offset,
        "segment_bytes": matrix_bytes,
        "segment_sha256": observed,
        "every_code_consumed": True,
    }


def narrow_fp32_to_bf16_rne(code: int) -> int:
    """The exact FP32 -> BF16 round-to-nearest-even the RoPE datapath performs.

    Written out rather than imported so the coefficient the oracle sees is
    derived here from the same FP32 words the bank hands the RTL.
    """

    low = code & 0xFFFF
    high = (code >> 16) & 0xFFFF
    if low > 0x8000 or (low == 0x8000 and (high & 1)):
        high += 1
    return high & 0xFFFF


def retained_program(
    target_key: str = TARGET_KEY,
) -> tuple[dict[str, Any], list[int], list[int], int, int]:
    manifest = json.loads(scatter.DEPLOYMENT_MANIFEST.read_text())
    descriptors = scatter.read_hex(scatter.DESCRIPTOR_IMAGE)
    programs = scatter.read_hex(scatter.PROGRAM_IMAGE)
    bases = scatter.deployment_bases(manifest)
    descriptor_base, program_base = bases[target_key]
    return manifest, descriptors, programs, descriptor_base, program_base


class RetainedTable:
    """The retained descriptor table, addressed exactly as the RTL ROM is.

    Descriptors that do not decode -- the 256-byte TOPOLOGY record does not fit
    the retained 192-byte beat and is not one this bridge ever reads -- are
    absent from the table and present in the image as their retained bytes.  A
    case that named one would fail the header check, which is the right answer.
    """

    def __init__(self, decoded: dict[int, Descriptor]) -> None:
        self._decoded = decoded

    def get(self, descriptor_id: int, expected_type: Any = None) -> Descriptor:
        descriptor = self._decoded[int(descriptor_id)]
        if expected_type is not None and descriptor.descriptor_type != int(
            expected_type
        ):
            raise RuntimeError(
                f"descriptor {descriptor_id} is type "
                f"{descriptor.descriptor_type:#06x}, expected {int(expected_type):#06x}"
            )
        return descriptor

    def __getitem__(self, descriptor_id: int) -> Descriptor:
        return self._decoded[int(descriptor_id)]

    def __contains__(self, descriptor_id: int) -> bool:
        return int(descriptor_id) in self._decoded

    def ids_of_type(self, descriptor_type: Any) -> list[int]:
        """Every descriptor id of one type, in ascending order."""

        return sorted(
            descriptor_id
            for descriptor_id, descriptor in self._decoded.items()
            if descriptor.descriptor_type == int(descriptor_type)
        )


def build_table(
    descriptors: list[int], descriptor_base: int, count: int
) -> tuple[RetainedTable, dict[int, bytes]]:
    decoded: dict[int, Descriptor] = {}
    records: dict[int, bytes] = {}
    for descriptor_id in range(count):
        beat = descriptors[descriptor_base + descriptor_id].to_bytes(
            scatter.DESCRIPTOR_BYTES, "little"
        )
        records[descriptor_id] = beat
        try:
            total = int(DESCRIPTOR_HEADER.decode(beat[:64])["total_bytes"])
            if total > scatter.DESCRIPTOR_BYTES:
                continue
            decoded[descriptor_id] = Descriptor.decode(beat[:total], descriptor_id)
        except Exception:
            continue
    return RetainedTable(decoded), records


def operator_at(
    programs: list[int], program_base: int, pc: int, expected: str
) -> Instruction:
    instruction = Instruction.decode(programs[program_base + pc].to_bytes(32, "little"))
    if instruction.mnemonic != expected:
        raise RuntimeError(
            f"retained PC {pc} is {instruction.mnemonic}, expected {expected}"
        )
    return instruction


def resolved_views(
    resolver: ViewResolver,
    table: DescriptorTable,
    operator_id: int,
    loops: dict[int, int],
    symbols: dict[int, int],
) -> list[dict[str, Any]]:
    operator = table.get(operator_id, ExtendedDescriptorType.OPERATOR)
    out: list[dict[str, Any]] = []
    fields = (
        "input_view_0",
        "input_view_1",
        "input_view_2",
        "input_view_3",
        "output_view_0",
    )
    for slot, field in enumerate(fields):
        view_id = int(operator.payload[field])
        if view_id == NO_ID:
            continue
        view = resolver.resolve(view_id, loops, symbols)
        out.append(
            {
                "slot": slot,
                "descriptor_id": view_id,
                "object_id": int(view.object_id),
                "dtype": int(view.dtype),
                "dims": [int(value) for value in view.dims],
                "strides": [int(value) for value in view.strides],
                "element_offset": int(view.element_offset),
                "extent_axis": int(view.extent_axis),
                "extent": int(view.dims[view.extent_axis]),
                "rank": len(view.dims),
            }
        )
    return out


def decode_argmax(codes: list[int]) -> tuple[int, int]:
    """greedy_lowest_token_id_argmax_v1 over widened BF16 logits."""

    best_value = None
    best_index = 0
    ties = 0
    for index, code in enumerate(codes):
        value = bf16_to_float(code)
        if value != value or value in (float("inf"), float("-inf")):
            raise RuntimeError("a logit is not finite")
        if best_value is None or value > best_value:
            best_value = value
            best_index = index
            ties = 1
        elif value == best_value:
            ties += 1
    return best_index, ties


class Builder:
    def __init__(self, storage_class: str = DEFAULT_STORAGE_CLASS) -> None:
        if storage_class not in TARGETS:
            raise SystemExit(
                f"unknown storage class {storage_class!r}; known: "
                f"{sorted(TARGETS)}"
            )
        self.storage_class = storage_class
        self.target_key = TARGETS[storage_class]
        (
            self.manifest,
            descriptors,
            self.programs,
            self.descriptor_base,
            self.program_base,
        ) = retained_program(self.target_key)
        deployment = next(
            item
            for item in self.manifest["deployments"]
            if item["key"] == self.target_key
        )
        self.deployment = deployment
        self.descriptor_count = int(deployment["descriptor_count"])
        self.table, self.records = build_table(
            descriptors, self.descriptor_base, self.descriptor_count
        )
        # The GENERATION_POLICY record SELECTION.ARGMAX and
        # SELECTION.TOKEN_APPEND run under, SEARCHED FOR in this deployment's
        # own descriptor table rather than typed here.  It was the constant 21,
        # which is the ROM lowering's id and is 219 on the HBM lowering; a
        # typed id is a lowering artefact that silently binds one generation of
        # one bundle.  Zero or more than one match is a refusal, not a guess.
        policies = self.table.ids_of_type(ExtendedDescriptorType.GENERATION_POLICY)
        if len(policies) != 1:
            raise SystemExit(
                f"{self.target_key}: the descriptor table carries "
                f"{len(policies)} GENERATION_POLICY records {policies}; the "
                "selection cases cannot be bound to a policy that cannot be "
                "identified"
            )
        self.generation_policy_id = policies[0]
        self.resolver = ViewResolver(SimpleNamespace(table=self.table), None)
        self.symbols = self._symbols()
        # Where PC 72 actually appends, and therefore how much bank the ring
        # object needs.  Read from the resolved view, not assumed.
        ring_view = next(
            view
            for view in self._operation(
                PC_TOKEN_APPEND, "SELECTION.TOKEN_APPEND", self.symbols_at(16)
            )["views"]
            if int(view["slot"]) == 4
        )
        self.ring_offset = int(ring_view["element_offset"])
        self.ring_words = self.ring_offset + int(ring_view["extent"])
        self.ring_slot = BASE_RING + self.ring_offset
        # The two regions the object-keyed families add to the result bank: the
        # rotated key object PC 23 writes and PC 29 reads, and the FP32
        # coefficient row PC 26 and PC 29 both read.  They are appended so no
        # existing base moves.
        self.base_head_key = BASE_RING + self.ring_words
        self.base_rope_coefficient = self.base_head_key + KV_PLANE_WORDS
        # The row PC 68's DMA.GATHER publishes: its own object, its own home.
        self.base_head_gather = self.base_rope_coefficient + 2 * HEAD_WIDTH
        self.bank_words = self.base_head_gather + ADD_WIDTH
        self.bank = [0] * self.bank_words
        self.initial_bank: list[int] = []
        self.source_bank = [0] * SOURCE_WORDS
        # The projection-matrix bank: a third address space, indexed by the
        # SAME object table, selected by the reading port rather than by the
        # base.  It stays empty until a TENSOR.MATMUL case stages a matrix.
        self.weight_bank: list[int] = []
        self.weight_sources: list[dict[str, Any]] = []
        self.index_bank = list(range(INDEX_WORDS))
        self.cases: list[dict[str, Any]] = []
        self.expected_words: list[int] = []
        self.extra_records: dict[int, bytes] = {}
        self.preload_words: list[int] = []
        self.next_synthetic_id = self.descriptor_count
        (
            self.prefix_results,
            self.prefix_source,
            self.prefix_placement,
        ) = retained_prefix_results(self.target_key)

    # -- retained request bindings -----------------------------------------
    def _symbols(self) -> dict[int, int]:
        case = next(
            item
            for item in self.manifest["cases"]
            if item.get("deployment") == self.target_key
            and item.get("request") == "decode"
        )
        return {int(key): int(value) for key, value in case["symbols"].items()}

    def symbols_at(self, position: int) -> dict[int, int]:
        values = dict(self.symbols)
        values[int(Symbol.POSITION_START)] = position
        values[int(Symbol.POSITION_END)] = position + 1
        values[int(Symbol.CONTEXT_LENGTH)] = position + 1
        return values

    # -- descriptor image ---------------------------------------------------
    def add_synthetic(self, record: bytes) -> int:
        descriptor_id = self.next_synthetic_id
        self.next_synthetic_id += 1
        self.extra_records[descriptor_id] = record
        return descriptor_id

    def descriptor_image(self) -> list[int]:
        total = self.next_synthetic_id
        words: list[int] = []
        for descriptor_id in range(total):
            record = self.records.get(descriptor_id) or self.extra_records.get(
                descriptor_id, b""
            )
            words.append(
                int.from_bytes(
                    record
                    if len(record) == scatter.DESCRIPTOR_BYTES
                    else scatter.padded_record(record),
                    "little",
                )
            )
        return words

    # -- case emission ------------------------------------------------------
    def emit(
        self,
        *,
        name: str,
        pc: int,
        family: int,
        sub: int,
        operator_id: int,
        views: list[dict[str, Any]],
        object_map: dict[int, int],
        context_length: int,
        kv_plane_rows: int,
        request_max_new_tokens: int,
        generated_before: int,
        expected_fault: bool,
        expected_trap: int,
        expected_result_count: int,
        expected_work_count: int,
        expected_write_count: int,
        expected_token: int,
        expected_tie_multiplicity: int,
        expected_eos_reason: int,
        expected_launch: int,
        compare_base: int,
        compare_words: list[int],
        preload: tuple[int, list[int]] | None = None,
        generation_policy_id: int | None = None,
        placement_valid: bool = True,
        note: str = "",
    ) -> None:
        if generation_policy_id is None:
            generation_policy_id = self.generation_policy_id
        if len(object_map) > MAP_ENTRIES:
            raise RuntimeError(f"{name}: object map exceeds {MAP_ENTRIES} entries")
        if len(views) > VIEW_SLOTS:
            raise RuntimeError(f"{name}: more resolved views than slots")
        self.cases.append(
            {
                "name": name,
                "pc": pc,
                "family": family,
                "sub": sub,
                "operator_descriptor_id": operator_id,
                "views": views,
                "object_map": dict(object_map),
                "objects_named": sorted(
                    {
                        int(view["object_id"])
                        for view in views
                        if int(view["slot"])
                        not in UNKEYED_SLOTS.get((int(family), int(sub)), ())
                    }
                ),
                "context_length": context_length,
                "kv_plane_rows": kv_plane_rows,
                "generation_policy_id": generation_policy_id,
                "placement_valid": bool(placement_valid),
                "request_max_new_tokens": request_max_new_tokens,
                "generated_before": generated_before,
                "expected": {
                    "fault": bool(expected_fault),
                    "trap_class": int(expected_trap),
                    "result_count": int(expected_result_count),
                    "work_count": int(expected_work_count),
                    "write_beats": int(expected_write_count),
                    "token": int(expected_token),
                    "tie_multiplicity": int(expected_tie_multiplicity),
                    "eos_reason": int(expected_eos_reason),
                    "launch": int(expected_launch),
                    "compare_base": int(compare_base),
                    "compare_count": len(compare_words),
                },
                "preload": (
                    None
                    if preload is None
                    else {
                        "base": int(preload[0]),
                        "count": len(preload[1]),
                        "offset": self._stage_preload(preload[1]),
                    }
                ),
                "note": note,
                "_compare_offset": len(self.expected_words),
            }
        )
        self.expected_words.extend(compare_words)

    def _stage_preload(self, words: list[int]) -> int:
        offset = len(self.preload_words)
        self.preload_words.extend(words)
        return offset

    def encoded_cases(self) -> list[int]:
        words: list[int] = []
        for item in self.cases:
            values = [0] * CASE_WORDS
            expected = item["expected"]
            values[0] = item["family"]
            values[1] = item["sub"]
            values[2] = item["operator_descriptor_id"]
            values[3] = len(item["views"])
            values[4] = item["context_length"]
            values[5] = item["kv_plane_rows"]
            values[6] = item["generation_policy_id"]
            values[7] = item["request_max_new_tokens"]
            values[8] = item["generated_before"]
            values[9] = int(expected["fault"])
            values[10] = expected["trap_class"]
            values[11] = expected["result_count"]
            values[12] = expected["work_count"]
            values[13] = expected["write_beats"]
            values[14] = expected["token"]
            values[15] = expected["eos_reason"]
            values[16] = expected["compare_base"]
            values[17] = expected["compare_count"]
            values[18] = expected["launch"]
            values[19] = expected["tie_multiplicity"]
            values[20] = item["_compare_offset"]
            preload = item["preload"]
            values[21] = preload["count"] if preload is not None else 0
            values[22] = preload["base"] if preload is not None else 0
            values[23] = preload["offset"] if preload is not None else 0
            values[40] = int(item["placement_valid"])
            entries = sorted(item["object_map"].items())
            for slot in range(MAP_ENTRIES):
                if slot < len(entries):
                    values[MAP_BASE + 2 * slot] = entries[slot][0]
                    values[MAP_BASE + 1 + 2 * slot] = entries[slot][1]
                else:
                    values[MAP_BASE + 2 * slot] = 0xFFFFFFFF
                    values[MAP_BASE + 1 + 2 * slot] = 0
            words.extend(value & 0xFFFFFFFF for value in values)
        return words

    def encoded_views(self) -> list[int]:
        words: list[int] = []
        for item in self.cases:
            by_slot = {int(view["slot"]): view for view in item["views"]}
            for slot in range(VIEW_SLOTS):
                view = by_slot.get(slot)
                if view is None:
                    words.extend([0] * VIEW_WORDS)
                    continue
                offset = int(view["element_offset"])
                words.extend(
                    [
                        1,
                        int(view["descriptor_id"]),
                        slot,
                        int(view["extent"]),
                        int(view["extent_axis"]),
                        offset & 0xFFFFFFFF,
                        (offset >> 32) & 0xFFFFFFFF,
                        int(view["rank"]),
                    ]
                )
        return [value & 0xFFFFFFFF for value in words]

    # -- the governed operator cases ---------------------------------------
    def build_cases(self) -> None:
        query, current_key, current_value = gqa.authentic_activations()

        def plane(current: list[int], *, value_plane: bool) -> list[list[int]]:
            head = gqa.rows_from_current(
                current, value_plane=value_plane, context=17
            )
            tail = gqa.rows_from_current(
                current, value_plane=value_plane, context=KV_PLANE_ROWS
            )
            rows = head + tail[16 : KV_PLANE_ROWS - 1]
            if len(rows) != KV_PLANE_ROWS:
                raise RuntimeError("compact KV plane row count is wrong")
            return rows

        key_rows = plane(current_key, value_plane=False)
        value_rows = plane(current_value, value_plane=True)
        # The two rows the scatters will write start empty, so a scatter that
        # does not happen shows as a zero row rather than as a value that was
        # already there.
        for row in (16, KV_PLANE_ROWS - 1):
            key_rows[row] = [0] * KV_PLANE_WORDS
            value_rows[row] = [0] * KV_PLANE_WORDS

        # The trunk activation is no longer a seeded row: it is the embedding
        # lookup's own golden output, so the RMSNorm this campaign now issues
        # at PC 8 reads what the shipped program's PC 4 wrote.
        trunk = list(self.prefix_results[PC_EMBED_LOOKUP])
        if len(trunk) != ADD_WIDTH:
            raise RuntimeError("the retained embedding row is not one model row")
        spread = Spread(0x5150_4F54_414C_4C41)
        attention_projection = spread.row(
            ADD_WIDTH, low_exponent=118, high_exponent=130
        )
        mlp_projection = spread.row(ADD_WIDTH, low_exponent=118, high_exponent=130)
        silu_gate = spread.row(SILU_WIDTH, low_exponent=120, high_exponent=131)
        silu_up = spread.row(SILU_WIDTH, low_exponent=120, high_exponent=131)
        logits = spread.row(VOCABULARY, low_exponent=118, high_exponent=131)
        # A deliberate duplicate maximum: greedy_lowest_token_id_argmax_v1 must
        # take the lower id, and a tie that is never present cannot prove it.
        logits[EOS_TOKEN] = 0x4300
        logits[EOS_TOKEN + 7] = 0x4300
        # The two RMSNorm gains the shipped prefix does not reach.  PCs 47 and
        # 66 lie past the prefix's PC-32 boundary, so their checkpoint gains
        # are not in the retained source bank; these are a seeded spread and
        # the campaign says so.  Their oracle is the same scalar reference.
        mlp_norm_gain = spread.row(ADD_WIDTH, low_exponent=118, high_exponent=130)
        head_norm_gain = spread.row(ADD_WIDTH, low_exponent=118, high_exponent=130)

        for row in range(KV_PLANE_ROWS):
            start = BASE_KV + row * KV_PLANE_WORDS
            self.bank[start : start + KV_PLANE_WORDS] = key_rows[row]
            start = BASE_KV + (KV_PLANE_ROWS + row) * KV_PLANE_WORDS
            self.bank[start : start + KV_PLANE_WORDS] = value_rows[row]
        self.bank[
            BASE_SCATTER_VALUE_SOURCE : BASE_SCATTER_VALUE_SOURCE + KV_PLANE_WORDS
        ] = current_value
        # Scratch A starts as the query PROJECTION, not the RoPE'd query: the
        # head RMSNorm at PC 20 and the RoPE at PC 26 now run in this vehicle
        # and produce the RoPE'd query themselves, into this same object.  The
        # key source object likewise starts as the key projection, which PC 23
        # and PC 29 turn into the key the scatter then moves.
        self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] = list(
            self.prefix_results[PC_MATMUL_QUERY]
        )
        self.bank[
            BASE_SCATTER_KEY_SOURCE : BASE_SCATTER_KEY_SOURCE + KV_PLANE_WORDS
        ] = list(self.prefix_results[PC_MATMUL_KEY])
        if list(self.prefix_results[PC_MATMUL_VALUE]) != list(current_value):
            raise RuntimeError(
                "the retained value projection and the authentic value row "
                "disagree; one of the two extractions is wrong"
            )
        self.bank[BASE_TRUNK : BASE_TRUNK + ADD_WIDTH] = trunk
        # The FP32 coefficient row PC 1's gather published, read by both RoPEs.
        coefficient_fp32 = list(
            self.prefix_results[PC_ROPE_COEFFICIENT_GATHER]
        )
        if len(coefficient_fp32) != 2 * HEAD_WIDTH:
            raise RuntimeError("the retained RoPE coefficient row changed shape")
        self.bank[
            self.base_rope_coefficient : self.base_rope_coefficient
            + 2 * HEAD_WIDTH
        ] = coefficient_fp32
        coefficient_bf16 = [
            narrow_fp32_to_bf16_rne(code) for code in coefficient_fp32
        ]
        self.bank[BASE_SILU_GATE : BASE_SILU_GATE + SILU_WIDTH] = silu_gate
        self.bank[BASE_SILU_UP : BASE_SILU_UP + SILU_WIDTH] = silu_up
        self.bank[BASE_LOGITS : BASE_LOGITS + VOCABULARY] = logits
        # The bank is loaded once and the cases then run in program order, so
        # this is the only snapshot the testbench ever loads.
        self.initial_bank = list(self.bank)

        base_symbols = self.symbols_at(16)

        # The object -> compact-bank map, one base per ABI object.  Slot roles
        # are not bases: the governed program writes two different operators'
        # results into the same object, and a campaign that gave each role its
        # own region would never see that.
        operations = {
            pc: self._operation(pc, mnemonic, base_symbols)
            for pc, mnemonic in (
                (PC_SCATTER_KEY, "DMA.SCATTER"),
                (PC_SCATTER_VALUE, "DMA.SCATTER"),
                (PC_GQA, "ATTENTION.GQA"),
                (PC_ADD_ATTENTION, "VECTOR.ADD"),
                (PC_SILU_MUL, "VECTOR.SILU_MUL"),
                (PC_ADD_MLP, "VECTOR.ADD"),
                (PC_ARGMAX, "SELECTION.ARGMAX"),
                (PC_TOKEN_APPEND, "SELECTION.TOKEN_APPEND"),
                (PC_RMS_NORM_ATTENTION, "VECTOR.RMS_NORM"),
                (PC_HEAD_RMS_QUERY, "VECTOR.HEAD_RMS_NORM"),
                (PC_HEAD_RMS_KEY, "VECTOR.HEAD_RMS_NORM"),
                (PC_ROPE_QUERY, "VECTOR.ROPE"),
                (PC_ROPE_KEY, "VECTOR.ROPE"),
                (PC_RMS_NORM_MLP, "VECTOR.RMS_NORM"),
                (PC_RMS_NORM_HEAD, "VECTOR.RMS_NORM"),
                (PC_MATMUL_KEY, "TENSOR.MATMUL"),
                (PC_MATMUL_VALUE, "TENSOR.MATMUL"),
                (PC_MATMUL_GATE, "TENSOR.MATMUL"),
                (PC_MATMUL_UP, "TENSOR.MATMUL"),
                (PC_MATMUL_DOWN, "TENSOR.MATMUL"),
                (PC_HEAD_GATHER, "DMA.GATHER"),
                (PC_ROPE_COEFFICIENT_GATHER, "DMA.GATHER"),
            )
        }

        def objects(pc: int) -> dict[int, int]:
            return {
                int(view["slot"]): int(view["object_id"])
                for view in operations[pc]["views"]
            }

        scatter_key = objects(PC_SCATTER_KEY)
        scatter_value = objects(PC_SCATTER_VALUE)
        attention = objects(PC_GQA)
        add_a = objects(PC_ADD_ATTENTION)
        silu = objects(PC_SILU_MUL)
        add_b = objects(PC_ADD_MLP)
        argmax = objects(PC_ARGMAX)
        append = objects(PC_TOKEN_APPEND)
        rms_attention = objects(PC_RMS_NORM_ATTENTION)
        head_rms_query = objects(PC_HEAD_RMS_QUERY)
        head_rms_key = objects(PC_HEAD_RMS_KEY)
        rope_query = objects(PC_ROPE_QUERY)
        rope_key = objects(PC_ROPE_KEY)
        rms_mlp = objects(PC_RMS_NORM_MLP)
        rms_head = objects(PC_RMS_NORM_HEAD)
        matmul_key = objects(PC_MATMUL_KEY)
        matmul_value = objects(PC_MATMUL_VALUE)
        matmul_gate = objects(PC_MATMUL_GATE)
        matmul_up = objects(PC_MATMUL_UP)
        matmul_down = objects(PC_MATMUL_DOWN)
        head_gather = objects(PC_HEAD_GATHER)
        coefficient_gather = objects(PC_ROPE_COEFFICIENT_GATHER)

        # The reuse this campaign exists to place correctly.  Each is a fact
        # about the shipped program, so an assertion is the right way to hold
        # it: if the compiler stops reusing these objects the campaign must be
        # rebuilt rather than silently keep testing a shape that is gone.
        if attention[0] != add_a[1] or add_a[1] != add_b[1]:
            raise RuntimeError(
                "the attention query, the attention projection and the MLP "
                "projection no longer share one scratch object"
            )
        if attention[4] != add_a[4] or add_a[4] != add_b[0]:
            raise RuntimeError("the attention result no longer feeds the residual")
        if add_b[4] != add_a[0]:
            raise RuntimeError(
                "the MLP residual no longer writes back over the trunk object "
                "the attention residual read"
            )
        if scatter_key[4] != scatter_value[4] or scatter_key[4] != attention[1]:
            raise RuntimeError("the scatters no longer write the attention's cache")
        if attention[1] != attention[2]:
            raise RuntimeError("PC 38 key and value views name different objects")
        # The same kind of fact for the four object-keyed families, and it is
        # the reason they are worth issuing here: their operands are the SAME
        # objects the six mapped families read and write, through the same
        # table, so the span's placement demand is one demand and not ten.
        if (
            rms_attention[0] != add_a[0]
            or rms_attention[4] != add_a[4]
            or rms_head[0] != add_a[0]
            or rms_head[4] != add_a[4]
            or rms_mlp[0] != add_a[4]
            or rms_mlp[4] != add_a[1]
        ):
            raise RuntimeError(
                "the layer's three RMSNorms no longer read and write the trunk "
                "and scratch objects the residual adds use"
            )
        if (
            head_rms_query[0] != add_a[1]
            or head_rms_query[4] != add_a[4]
            or head_rms_key[0] != scatter_key[1]
            or rope_query[0] != head_rms_query[4]
            or rope_query[4] != head_rms_query[0]
            or rope_key[0] != head_rms_key[4]
            or rope_key[4] != head_rms_key[0]
        ):
            raise RuntimeError(
                "the query and key head-norm and RoPE chain no longer lands in "
                "the objects the attention and the scatters read"
            )
        # The two projections this vehicle now issues in RTL read the trunk
        # norm's own result and write the two objects the head norms and the
        # scatters then read.  Both are facts about the shipped program, so a
        # compiler that stops arranging them this way must rebuild the
        # campaign rather than let it quietly test a different chain.
        if matmul_key[0] != add_a[4] or matmul_value[0] != add_a[4]:
            raise RuntimeError(
                "the key and value projections no longer read the object the "
                "attention-input RMSNorm writes"
            )
        if matmul_key[4] != scatter_key[1] or matmul_value[4] != scatter_value[1]:
            raise RuntimeError(
                "the key and value projections no longer write the objects "
                "the head norms and the two scatters read"
            )
        if rope_query[1] != rope_key[1]:
            raise RuntimeError("the two RoPEs no longer share one coefficient object")
        # PC 1 publishes the row the two RoPEs then read.  That is why the
        # coefficient object needs no second base for the gather's result: the
        # object the shipped PC 1 writes IS the object the shipped PCs 26 and
        # 29 read, and this campaign places it once.
        if coefficient_gather[4] != rope_query[1]:
            raise RuntimeError(
                "the shipped PC 1 gather no longer publishes into the object "
                "the RoPEs read their coefficient row from"
            )
        if len({
            rms_attention[1], rms_mlp[1], rms_head[1],
            head_rms_query[1], head_rms_key[1],
        }) != 5:
            raise RuntimeError("the five normalization gains are no longer distinct")

        # The two layer-zero projection matrices, read from the checkpoint
        # the deployment itself names and hashed against the digest that
        # deployment declared.  Each is staged whole because the operation
        # consumes every code in it.
        weight_base: dict[int, int] = {}
        for weight_pc, weight_slots in (
            (PC_MATMUL_KEY, matmul_key),
            (PC_MATMUL_VALUE, matmul_value),
        ):
            weight_view = next(
                view
                for view in operations[weight_pc]["views"]
                if int(view["slot"]) == 1
            )
            rows, columns = (int(value) for value in weight_view["dims"])
            codes, identity = checkpoint_projection(
                self.target_key, self.deployment, weight_slots[1],
                rows=rows, columns=columns,
            )
            identity["pc"] = weight_pc
            weight_base[weight_slots[1]] = len(self.weight_bank)
            self.weight_bank.extend(codes)
            self.weight_sources.append(identity)

        object_base = {
            scatter_key[0]: 0,
            # The projection matrices live in the weight bank; the object
            # table hands out the base and `m1_reads_matmul_weight` decides
            # which memory it indexes, which is the same one-table-two-banks
            # rule the normalization gains already run under.
            matmul_key[1]: weight_base[matmul_key[1]],
            matmul_value[1]: weight_base[matmul_value[1]],
            # The row the head span's gather publishes.
            head_gather[4]: self.base_head_gather,
            scatter_key[1]: BASE_SCATTER_KEY_SOURCE,
            scatter_value[1]: BASE_SCATTER_VALUE_SOURCE,
            scatter_key[4]: BASE_KV,
            add_a[0]: BASE_TRUNK,
            add_a[1]: BASE_SCRATCH_A,
            add_a[4]: BASE_SCRATCH_B,
            silu[0]: BASE_SILU_GATE,
            silu[1]: BASE_SILU_UP,
            silu[4]: BASE_SILU_OUT,
            argmax[0]: BASE_LOGITS,
            argmax[4]: BASE_TOKEN,
            append[4]: BASE_RING,
            head_rms_key[4]: self.base_head_key,
            rope_query[1]: self.base_rope_coefficient,
            # The five normalization gains are read through m1 with
            # `m1_reads_result` low, so their bases are addresses in the
            # SOURCE bank rather than the result bank.  One table, two banks:
            # the object decides the base and the reading slot decides which
            # memory that base indexes, which is exactly what lets object 4
            # and object 55 hold the same base value without colliding.
            rms_attention[1]: BASE_SOURCE_RMS_GAIN_ATTENTION,
            rms_mlp[1]: BASE_SOURCE_RMS_GAIN_MLP,
            rms_head[1]: BASE_SOURCE_RMS_GAIN_HEAD,
            head_rms_query[1]: BASE_SOURCE_HEAD_GAIN_QUERY,
            head_rms_key[1]: BASE_SOURCE_HEAD_GAIN_KEY,
        }
        if len(object_base) > MAP_ENTRIES:
            raise RuntimeError(
                f"the span names {len(object_base)} objects and the vector "
                f"format carries {MAP_ENTRIES} table entries"
            )

        def submap(*object_ids: int) -> dict[int, int]:
            return {value: object_base[value] for value in object_ids}

        def shared() -> dict[int, int]:
            """The one table every admitted case in this campaign runs under.

            The bridge places every operand and every result of every family
            through one 32-entry table, so the question a layer asks of it is
            not "can this role name its objects" but "can ONE binding name all
            of the span's objects at once".  Every positive case therefore
            carries the same table -- the whole set, identical word for word --
            and the objects it resolves out of that table are the objects its
            own operands name.  A per-case submap would have made each case
            pass while leaving the union unmeasured, which is the shortfall
            that keeps G1a and G1b red.
            """

            return dict(object_base)

        # The five gains, staged into the source bank at their objects' bases.
        # Three are the real checkpoint gains the shipped prefix retained; two
        # are the seeded spread, because the prefix stops before their program
        # counters.
        for gain_object, gain_words in (
            (rms_attention[1], list(self.prefix_source[
                self.prefix_placement[rms_attention[1]]
                : self.prefix_placement[rms_attention[1]] + ADD_WIDTH
            ])),
            (head_rms_query[1], list(self.prefix_source[
                self.prefix_placement[head_rms_query[1]]
                : self.prefix_placement[head_rms_query[1]] + HEAD_WIDTH
            ])),
            (head_rms_key[1], list(self.prefix_source[
                self.prefix_placement[head_rms_key[1]]
                : self.prefix_placement[head_rms_key[1]] + HEAD_WIDTH
            ])),
            (rms_mlp[1], mlp_norm_gain),
            (rms_head[1], head_norm_gain),
        ):
            base = object_base[gain_object]
            self.source_bank[base : base + len(gain_words)] = gain_words
        gains = {
            gain_object: list(
                self.source_bank[
                    object_base[gain_object] : object_base[gain_object] + width
                ]
            )
            for gain_object, width in (
                (rms_attention[1], ADD_WIDTH),
                (head_rms_query[1], HEAD_WIDTH),
                (head_rms_key[1], HEAD_WIDTH),
                (rms_mlp[1], ADD_WIDTH),
                (rms_head[1], ADD_WIDTH),
            )
        }

        def norm_case(
            *,
            name: str,
            pc: int,
            mnemonic: str,
            sub: int,
            rows: int,
            width: int,
            input_base: int,
            output_base: int,
            gain_object: int,
            golden_pc: int | None,
            note: str,
        ) -> None:
            """One VECTOR.RMS_NORM or VECTOR.HEAD_RMS_NORM of the layer."""

            operation = operations[pc]
            source = self.bank[input_base : input_base + rows * width]
            result = rms_norm_bf16(
                tuple(
                    tuple(source[row * width : (row + 1) * width])
                    for row in range(rows)
                ),
                gains[gain_object],
            )
            expected = [code for row in result.values for code in row]
            self._require_golden(pc, golden_pc, expected)
            self.emit(
                name=name,
                pc=pc,
                family=int(Major.VECTOR),
                sub=sub,
                operator_id=operation["operator_id"],
                views=operation["views"],
                object_map=shared(),
                context_length=17,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=False,
                expected_trap=TRAP_NONE,
                expected_result_count=rows * width,
                expected_work_count=rows * width,
                expected_write_count=rows * width,
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=(
                    LAUNCH_HEAD_RMS_NORM
                    if sub == int(Vector.HEAD_RMS_NORM)
                    else LAUNCH_RMS_NORM
                ),
                compare_base=output_base,
                compare_words=expected,
                note=note,
            )
            self.bank[output_base : output_base + len(expected)] = expected

        def rope_case(
            *,
            name: str,
            pc: int,
            rows: int,
            input_base: int,
            output_base: int,
            golden_pc: int,
            note: str,
        ) -> None:
            operation = operations[pc]
            source = self.bank[input_base : input_base + rows * HEAD_WIDTH]
            heads = tuple(
                tuple(source[row * HEAD_WIDTH : (row + 1) * HEAD_WIDTH])
                for row in range(rows)
            )
            result = rope_bf16(
                heads,
                heads,
                coefficient_bf16[:HEAD_WIDTH],
                coefficient_bf16[HEAD_WIDTH:],
            )
            expected = [code for row in result.query_values for code in row]
            self._require_golden(pc, golden_pc, expected)
            self.emit(
                name=name,
                pc=pc,
                family=int(Major.VECTOR),
                sub=int(Vector.ROPE),
                operator_id=operation["operator_id"],
                views=operation["views"],
                object_map=shared(),
                context_length=17,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=False,
                expected_trap=TRAP_NONE,
                expected_result_count=rows * HEAD_WIDTH,
                expected_work_count=rows * HEAD_WIDTH,
                expected_write_count=rows * HEAD_WIDTH,
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=LAUNCH_ROPE,
                compare_base=output_base,
                compare_words=expected,
                note=note,
            )
            self.bank[output_base : output_base + len(expected)] = expected

        def matmul_case(
            *, name: str, pc: int, slots: dict[int, int], note: str
        ) -> None:
            """One admitted TENSOR.MATMUL of the layer, on real weights.

            The activation is whatever the case before it left in the input
            object -- not a staged copy of it -- and the weight is the whole
            layer-zero matrix the deployment's own object record points at in
            the checkpoint.  The expectation is the independent scalar
            reference's, and it is required to equal the shipped prefix's own
            golden write stream for this program counter as well.
            """

            operation = operations[pc]
            view = next(
                item for item in operation["views"] if int(item["slot"]) == 1
            )
            rows, columns = (int(value) for value in view["dims"])
            input_base = object_base[slots[0]]
            output_base = object_base[slots[4]]
            activation = self.bank[input_base : input_base + columns]
            start = weight_base[slots[1]]
            codes = self.weight_bank[start : start + rows * columns]
            result = dense_bf16_linear_bf16(
                (tuple(activation),),
                tuple(
                    tuple(codes[row * columns : (row + 1) * columns])
                    for row in range(rows)
                ),
            )
            expected = list(result.values[0])
            self._require_golden(pc, pc, expected)
            self.emit(
                name=name,
                pc=pc,
                family=int(Major.TENSOR),
                sub=int(Tensor.MATMUL),
                operator_id=operation["operator_id"],
                views=operation["views"],
                object_map=shared(),
                context_length=17,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=False,
                expected_trap=TRAP_NONE,
                expected_result_count=rows,
                expected_work_count=rows * columns,
                expected_write_count=rows,
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=LAUNCH_MATMUL,
                compare_base=output_base,
                compare_words=expected,
                note=note,
            )
            self.bank[output_base : output_base + len(expected)] = expected

        def scatter_case(
            pc: int, position: int, source: list[int], rows: list[list[int]]
        ) -> None:
            operation = self._operation(pc, "DMA.SCATTER", self.symbols_at(position))
            slots = {
                int(view["slot"]): view for view in operation["views"]
            }
            plane_offset = int(slots[4]["element_offset"])
            if plane_offset not in (0, KV_PLANE_WORDS):
                raise RuntimeError(f"PC {pc} KV plane offset changed")
            compact = 0 if plane_offset == 0 else KV_PLANE_ROWS * KV_PLANE_WORDS
            destination = BASE_KV + compact + position * KV_PLANE_WORDS
            rows[position] = list(source)
            self.emit(
                name=(
                    f"dma_scatter_{'key' if plane_offset == 0 else 'value'}"
                    f"_position{position}"
                ),
                pc=pc,
                family=int(Major.DMA),
                sub=int(Dma.SCATTER),
                operator_id=operation["operator_id"],
                views=operation["views"],
                object_map=shared(),
                context_length=position + 1,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=False,
                expected_trap=TRAP_NONE,
                expected_result_count=KV_PLANE_WORDS,
                expected_work_count=1,
                expected_write_count=(
                    KV_PLANE_ROWS * KV_PLANE_WORDS + KV_PLANE_WORDS
                ),
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=LAUNCH_SCATTER,
                compare_base=destination,
                compare_words=list(source),
                note=(
                    "read-modify-write into a pre-existing plane: the "
                    "destination is republished from itself and only the "
                    "indexed row changes"
                ),
            )
            self.bank[destination : destination + KV_PLANE_WORDS] = list(source)

        def attention_case(position: int, preload: list[int] | None) -> None:
            operation = self._operation(
                PC_GQA, "ATTENTION.GQA", self.symbols_at(position)
            )
            slots = {int(view["slot"]): view for view in operation["views"]}
            context = position + 1
            if preload is not None:
                self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] = list(
                    preload
                )
            expected = self._reference_gqa(
                self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH],
                key_rows[:context],
                value_rows[:context],
                context,
            )
            self.emit(
                name=f"attention_gqa_context{context}",
                pc=PC_GQA,
                family=int(Major.ATTENTION),
                sub=1,
                operator_id=operation["operator_id"],
                views=operation["views"],
                object_map=shared(),
                context_length=context,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=False,
                expected_trap=TRAP_NONE,
                expected_result_count=GQA_OUTPUT_WORDS,
                expected_work_count=context * GQA_OUTPUT_WORDS,
                expected_write_count=GQA_OUTPUT_WORDS,
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=LAUNCH_GQA,
                compare_base=BASE_SCRATCH_B,
                compare_words=expected,
                preload=None if preload is None else (BASE_SCRATCH_A, list(preload)),
                note=(
                    "reads the rows the two scatters just wrote: an "
                    "RTL-to-RTL handoff inside one operand bank"
                ),
            )
            self.bank[BASE_SCRATCH_B : BASE_SCRATCH_B + ADD_WIDTH] = expected

        # -- program order: normalize, project, rotate, scatter, attend -----
        # The layer as the shipped program orders it.  Two of the three
        # projections between PC 8 and PC 20 are now issued in RTL against the
        # checkpoint's own layer-zero k_proj and v_proj -- 8,388,608 weight
        # bytes each, every one consumed -- so the objects those operations
        # name are objects this design RESOLVES rather than objects it merely
        # places.  The query projection at PC 11 is not issued: its weight is
        # [4096, 4096] and costs 16.8 x 10^6 MACs against the pair's 8.4, and
        # nothing in the span needs a third weight object.  Its output stays
        # the retained golden value, staged.  Everything else in this span is
        # issued, and every operator below reads what the operator before it
        # WROTE.
        norm_case(
            name="vector_rms_norm_attention_input",
            pc=PC_RMS_NORM_ATTENTION,
            mnemonic="VECTOR.RMS_NORM",
            sub=int(Vector.RMS_NORM),
            rows=1,
            width=ADD_WIDTH,
            input_base=BASE_TRUNK,
            output_base=BASE_SCRATCH_B,
            gain_object=rms_attention[1],
            golden_pc=PC_RMS_NORM_ATTENTION,
            note=(
                "the embedding row the shipped PC 4 wrote, normalized by the "
                "real checkpoint gain the retained source bank carries, "
                "against that program counter's own golden write stream"
            ),
        )
        matmul_case(
            name="tensor_matmul_key_projection",
            pc=PC_MATMUL_KEY,
            slots=matmul_key,
            note=(
                "the trunk norm's own RTL result against the real checkpoint "
                "k_proj of layer zero, read from the shard the deployment's "
                "object record names and hashed against the digest it "
                "declares; the 1,024 words it writes are compared against the "
                "shipped prefix's golden for this same program counter"
            ),
        )
        matmul_case(
            name="tensor_matmul_value_projection",
            pc=PC_MATMUL_VALUE,
            slots=matmul_value,
            note=(
                "the same activation object and a second weight object "
                "through the same table: v_proj of layer zero, and the object "
                "the value scatter reads next"
            ),
        )
        norm_case(
            name="vector_head_rms_norm_query",
            pc=PC_HEAD_RMS_QUERY,
            mnemonic="VECTOR.HEAD_RMS_NORM",
            sub=int(Vector.HEAD_RMS_NORM),
            rows=QUERY_HEADS,
            width=HEAD_WIDTH,
            input_base=BASE_SCRATCH_A,
            output_base=BASE_SCRATCH_B,
            gain_object=head_rms_query[1],
            golden_pc=PC_HEAD_RMS_QUERY,
            note=(
                "32 query heads normalized per head by the real checkpoint "
                "head gain; the result lands over the object the trunk norm "
                "just wrote, which is a rewrite an append cursor cannot place"
            ),
        )
        norm_case(
            name="vector_head_rms_norm_key",
            pc=PC_HEAD_RMS_KEY,
            mnemonic="VECTOR.HEAD_RMS_NORM",
            sub=int(Vector.HEAD_RMS_NORM),
            rows=KV_HEADS,
            width=HEAD_WIDTH,
            input_base=BASE_SCATTER_KEY_SOURCE,
            output_base=self.base_head_key,
            gain_object=head_rms_key[1],
            golden_pc=PC_HEAD_RMS_KEY,
            note="8 key heads, the second real checkpoint head gain",
        )
        rope_case(
            name="vector_rope_query",
            pc=PC_ROPE_QUERY,
            rows=QUERY_HEADS,
            input_base=BASE_SCRATCH_B,
            output_base=BASE_SCRATCH_A,
            golden_pc=PC_ROPE_QUERY,
            note=(
                "reads the head norm's own result and the FP32 coefficient "
                "row PC 1's gather published, and writes back into the object "
                "the query projection occupied"
            ),
        )
        rope_case(
            name="vector_rope_key",
            pc=PC_ROPE_KEY,
            rows=KV_HEADS,
            input_base=self.base_head_key,
            output_base=BASE_SCATTER_KEY_SOURCE,
            golden_pc=PC_ROPE_KEY,
            note=(
                "the same coefficient object, a second shape: one object read "
                "by two operators at two extents through one base"
            ),
        )
        # What the two RoPEs just produced is what the attention and the key
        # scatter read next.  They are no longer staged: this run computed
        # them, and if it computed anything else the campaign refuses here
        # rather than quietly testing a different activation.
        if (
            self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] != list(query)
            or self.bank[
                BASE_SCATTER_KEY_SOURCE : BASE_SCATTER_KEY_SOURCE + KV_PLANE_WORDS
            ]
            != list(current_key)
        ):
            raise RuntimeError(
                "the rotated query and key this vehicle produced are not the "
                "authentic activations the attention campaign binds"
            )

        scatter_case(PC_SCATTER_KEY, 16, current_key, key_rows)
        scatter_case(PC_SCATTER_VALUE, 16, current_value, value_rows)
        attention_case(16, None)

        mid = self._reference_add(
            self.bank[BASE_TRUNK : BASE_TRUNK + ADD_WIDTH], attention_projection
        )
        self.emit(
            name="vector_add_attention_residual",
            pc=PC_ADD_ATTENTION,
            family=int(Major.VECTOR),
            sub=int(Vector.ADD),
            operator_id=operations[PC_ADD_ATTENTION]["operator_id"],
            views=operations[PC_ADD_ATTENTION]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=ADD_WIDTH,
            expected_work_count=ADD_WIDTH,
            expected_write_count=ADD_WIDTH,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_ADD,
            compare_base=BASE_SCRATCH_B,
            compare_words=mid,
            preload=(BASE_SCRATCH_A, list(attention_projection)),
            note=(
                "the attention projection lands in the same scratch object the "
                "query occupied, and the sum lands over the attention result"
            ),
        )
        self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] = list(
            attention_projection
        )
        self.bank[BASE_SCRATCH_B : BASE_SCRATCH_B + ADD_WIDTH] = mid

        norm_case(
            name="vector_rms_norm_mlp_input",
            pc=PC_RMS_NORM_MLP,
            mnemonic="VECTOR.RMS_NORM",
            sub=int(Vector.RMS_NORM),
            rows=1,
            width=ADD_WIDTH,
            input_base=BASE_SCRATCH_B,
            output_base=BASE_SCRATCH_A,
            gain_object=rms_mlp[1],
            golden_pc=None,
            note=(
                "the residual sum the previous case produced, normalized by a "
                "gain object the shipped prefix never reaches: the gain is a "
                "seeded spread and only the scalar reference stands behind it"
            ),
        )

        gated = self._reference_silu(silu_gate, silu_up)
        self.emit(
            name="vector_silu_mul_swiglu",
            pc=PC_SILU_MUL,
            family=int(Major.VECTOR),
            sub=int(Vector.SILU_MUL),
            operator_id=operations[PC_SILU_MUL]["operator_id"],
            views=operations[PC_SILU_MUL]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=SILU_WIDTH,
            expected_work_count=2 * SILU_WIDTH,
            expected_write_count=SILU_WIDTH,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_SILU,
            compare_base=BASE_SILU_OUT,
            compare_words=gated,
            note="qwen3_silu_mul_bf16_v1 at the governed intermediate width",
        )
        self.bank[BASE_SILU_OUT : BASE_SILU_OUT + SILU_WIDTH] = gated

        trunk_after = self._reference_add(mid, mlp_projection)
        self.emit(
            name="vector_add_mlp_residual_read_modify_write",
            pc=PC_ADD_MLP,
            family=int(Major.VECTOR),
            sub=int(Vector.ADD),
            operator_id=operations[PC_ADD_MLP]["operator_id"],
            views=operations[PC_ADD_MLP]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=ADD_WIDTH,
            expected_work_count=ADD_WIDTH,
            expected_write_count=ADD_WIDTH,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_ADD,
            compare_base=BASE_TRUNK,
            compare_words=trunk_after,
            preload=(BASE_SCRATCH_A, list(mlp_projection)),
            note=(
                "writes back over the trunk object it read two operators "
                "earlier: mapped placement, not the append cursor"
            ),
        )
        self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] = list(mlp_projection)
        self.bank[BASE_TRUNK : BASE_TRUNK + ADD_WIDTH] = trunk_after

        norm_case(
            name="vector_rms_norm_final",
            pc=PC_RMS_NORM_HEAD,
            mnemonic="VECTOR.RMS_NORM",
            sub=int(Vector.RMS_NORM),
            rows=1,
            width=ADD_WIDTH,
            input_base=BASE_TRUNK,
            output_base=BASE_SCRATCH_B,
            gain_object=rms_head[1],
            golden_pc=None,
            note=(
                "the head span's norm, on the trunk object the MLP residual "
                "wrote back over: a fifth distinct gain object through the "
                "same table, seeded for the same reason as PC 47's"
            ),
        )

        # ------------------------------------------------- the head gather
        # PC 68 selects the current row out of the residual history.  Two
        # facts about this vehicle are stated rather than softened.  First,
        # the row is read from the STAGED source region, not from object 45's
        # home in the result bank, because `cfg_source_base` is not keyed by
        # object; the row staged there is required here to be word for word
        # what the PC 66 case's RTL just wrote into object 45, so the operand
        # is that result and not a different one.  Second, the resolved index
        # view names row 0 and the index image answers its own ordinal, so
        # the row the design selects is the row this bank stages at 0.
        gather_source_row = list(
            self.bank[
                object_base[rms_head[4]] : object_base[rms_head[4]] + ADD_WIDTH
            ]
        )
        self.source_bank[
            BASE_SOURCE_GATHER_ROW : BASE_SOURCE_GATHER_ROW + ADD_WIDTH
        ] = gather_source_row
        gather_operation = operations[PC_HEAD_GATHER]
        gather_output_view = next(
            item for item in gather_operation["views"] if int(item["slot"]) == 4
        )
        if [int(value) for value in gather_output_view["dims"]] != [1, ADD_WIDTH]:
            raise RuntimeError("PC 68 no longer publishes one model-width row")
        self.emit(
            name="dma_gather_head_row_select",
            pc=PC_HEAD_GATHER,
            family=int(Major.DMA),
            sub=int(Dma.GATHER),
            operator_id=gather_operation["operator_id"],
            views=gather_operation["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=ADD_WIDTH,
            expected_work_count=1,
            expected_write_count=ADD_WIDTH,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_GATHER,
            compare_base=self.base_head_gather,
            compare_words=gather_source_row,
            note=(
                "a BF16 dense-row DMA.GATHER under exact_index_select_v1, "
                "the same contract digest the shipped FP32 gather at PC 1 "
                "carries: a byte-preserving row copy, compared word by word "
                "at the result object's own base"
            ),
        )
        self.bank[
            self.base_head_gather : self.base_head_gather + ADD_WIDTH
        ] = gather_source_row

        # ------------------------------------------ the shipped PC 1 gather
        # The second DMA.GATHER of the governed decode program, and the reason
        # it is issued here is a property of rung G1a rather than of this
        # bridge.  G1a decides coverage PER CAMPAIGN: a class is covered only
        # if ONE campaign's positive cases drove EVERY operator descriptor the
        # class names.  On the ROM lowering PC 1 and PC 68 resolve to the same
        # shape -- (0,1,0,1), (1,8256,0,2), (4,1,0,2) -- under the same
        # exact_index_select_v1 digest, so they merge into ONE equivalence
        # class naming descriptors 32 and 190, and the two were driven by two
        # DIFFERENT vehicles: the integrated shipped-prefix campaign drove 32
        # and this campaign drove 190.  Neither campaign drove both, so the
        # class was uncovered while every one of its instances had in fact
        # been executed.  On the HBM lowering the two PCs resolve to extents
        # 8256 and 8704, stay two classes, and each is singly covered -- which
        # is exactly why the ROM record carried this uncovered class and the
        # HBM record did not.
        #
        # Two facts about the operand are stated rather than softened.  The
        # row this case selects is NOT the checkpoint RoPE coefficient table
        # row: `cfg_source_base` is a swept staged region and the bridge
        # addresses it by launch ordinal, so both gathers of this campaign
        # read the row this bank stages at 0 -- the PC 66 result the RTL wrote
        # -- and the width the SHIPPED PC 1 view declares selects its leading
        # 256 words.  What this case measures is therefore the admission and
        # the byte-preserving copy of the shipped descriptor at the shipped
        # resolved shape, on an operand the RTL itself produced; it is not a
        # second measurement of the coefficient row the integrated vehicle
        # already gathers at PC 1 against the real checkpoint.  And it runs
        # AFTER both RoPE cases on purpose: the object it publishes into is
        # the coefficient object those two read, so a case order that put it
        # first would replace their operand.
        coefficient_operation = operations[PC_ROPE_COEFFICIENT_GATHER]
        coefficient_output_view = next(
            item for item in coefficient_operation["views"] if int(item["slot"]) == 4
        )
        coefficient_width = 2 * HEAD_WIDTH
        if [int(value) for value in coefficient_output_view["dims"]] != [
            1, coefficient_width
        ]:
            raise RuntimeError("PC 1 no longer publishes one RoPE coefficient row")
        coefficient_gather_row = gather_source_row[:coefficient_width]
        # The comparison must be able to fail.  The region this case writes
        # holds the staged coefficient row until this case overwrites it, so
        # a gather that wrote nothing would leave words that are NOT the
        # expected ones.  If the two were ever equal the check would pass
        # without the engine doing anything, and that is a refusal.
        if list(
            self.bank[
                self.base_rope_coefficient
                : self.base_rope_coefficient + coefficient_width
            ]
        ) == coefficient_gather_row:
            raise RuntimeError(
                "the PC 1 gather's expected result already sits in the region "
                "it writes, so the comparison could not fail"
            )
        self.emit(
            name="dma_gather_rope_coefficient_row_select",
            pc=PC_ROPE_COEFFICIENT_GATHER,
            family=int(Major.DMA),
            sub=int(Dma.GATHER),
            operator_id=coefficient_operation["operator_id"],
            views=coefficient_operation["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=coefficient_width,
            expected_work_count=1,
            expected_write_count=coefficient_width,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_GATHER,
            compare_base=self.base_rope_coefficient,
            compare_words=coefficient_gather_row,
            note=(
                "the shipped decode program's PC 1 DMA.GATHER, issued with "
                "its own operator, view and NUMERIC records under the same "
                "exact_index_select_v1 contract digest PC 68 carries: an FP32 "
                "dense-row select of one 256-element row, compared word by "
                "word at the coefficient object's own base.  The row selected "
                "is the leading 256 words of the same staged source row PC 68 "
                "gathers -- the PC 66 result the RTL wrote -- because this "
                "bridge addresses a gather's source by launch ordinal and not "
                "by the object; it is not the checkpoint coefficient table"
            ),
        )
        self.bank[
            self.base_rope_coefficient
            : self.base_rope_coefficient + coefficient_width
        ] = coefficient_gather_row

        # -- the second generated token: contexts 18 and 19 --------------------
        last = KV_PLANE_ROWS - 1
        scatter_case(PC_SCATTER_KEY, last, current_key, key_rows)
        scatter_case(PC_SCATTER_VALUE, last, current_value, value_rows)
        attention_case(last, query)

        # -------------------------------------------------------------- ARGMAX
        token, ties = decode_argmax(logits)
        if token != EOS_TOKEN:
            raise RuntimeError("the seeded logits no longer select the tied maximum")
        self.emit(
            name="selection_argmax_lowest_tied_id",
            pc=PC_ARGMAX,
            family=int(Major.SELECTION),
            sub=int(Selection.ARGMAX),
            operator_id=operations[PC_ARGMAX]["operator_id"],
            views=operations[PC_ARGMAX]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=1,
            expected_work_count=VOCABULARY,
            expected_write_count=1,
            expected_token=token,
            expected_tie_multiplicity=ties,
            expected_eos_reason=0,
            expected_launch=LAUNCH_ARGMAX,
            compare_base=BASE_TOKEN,
            compare_words=[token],
            note=(
                "two logits hold the maximum; the frozen rule selects the "
                "lower token id and publishes the tie multiplicity"
            ),
        )
        self.bank[BASE_TOKEN] = token

        # --------------------------------------------------------- TOKEN_APPEND
        if append[0] != argmax[4]:
            raise RuntimeError("PC 72 no longer reads back the selected token")
        append_map = submap(append[0], append[4])
        self.emit(
            name="selection_token_append_official_eos",
            pc=PC_TOKEN_APPEND,
            family=int(Major.SELECTION),
            sub=int(Selection.TOKEN_APPEND),
            operator_id=operations[PC_TOKEN_APPEND]["operator_id"],
            views=operations[PC_TOKEN_APPEND]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=1,
            expected_work_count=1,
            expected_write_count=1,
            expected_token=token,
            expected_tie_multiplicity=0,
            expected_eos_reason=1,
            expected_launch=LAUNCH_TOKEN_APPEND,
            compare_base=self.ring_slot,
            compare_words=[token],
            note="the selected id is in the policy's EOS set: OFFICIAL_EOS",
        )
        self.bank[self.ring_slot] = token

        ordinary = 12345
        self.emit(
            name="selection_token_append_continues",
            pc=PC_TOKEN_APPEND,
            family=int(Major.SELECTION),
            sub=int(Selection.TOKEN_APPEND),
            operator_id=operations[PC_TOKEN_APPEND]["operator_id"],
            views=operations[PC_TOKEN_APPEND]["views"],
            object_map=shared(),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=3,
            generated_before=0,
            expected_fault=False,
            expected_trap=TRAP_NONE,
            expected_result_count=1,
            expected_work_count=1,
            expected_write_count=1,
            expected_token=ordinary,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_TOKEN_APPEND,
            compare_base=self.ring_slot,
            compare_words=[ordinary],
            preload=(BASE_TOKEN, [ordinary]),
            note="not EOS and below the request bound: the session continues",
        )
        self.bank[BASE_TOKEN] = ordinary
        self.bank[self.ring_slot] = ordinary

        # ------------------------------------------------------ fail-closed
        # Admission that only ever admits is not admission.  Each of these is
        # a different refusal, and every one must leave the bank as it was.
        untouched_trunk = self.bank[BASE_TRUNK : BASE_TRUNK + 64]
        self.emit(
            name="capability_refusal_vector_softmax",
            pc=PC_ADD_MLP,
            family=int(Major.VECTOR),
            sub=int(Vector.SOFTMAX),
            operator_id=operations[PC_ADD_MLP]["operator_id"],
            views=operations[PC_ADD_MLP]["views"],
            object_map=submap(add_b[0], add_b[1], add_b[4]),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_CAPABILITY,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=BASE_TRUNK,
            compare_words=untouched_trunk,
            note="VECTOR.SOFTMAX still has no datapath and is still refused",
        )

        _, mutated_operator_id = self._mutated_contract(
            operations[PC_ADD_MLP]["operator_id"]
        )
        self.emit(
            name="descriptor_refusal_mutated_add_contract",
            pc=PC_ADD_MLP,
            family=int(Major.VECTOR),
            sub=int(Vector.ADD),
            operator_id=mutated_operator_id,
            views=operations[PC_ADD_MLP]["views"],
            object_map=submap(add_b[0], add_b[1], add_b[4]),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_DESCRIPTOR,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=BASE_TRUNK,
            compare_words=untouched_trunk,
            note=(
                "one flipped bit in the NUMERIC contract digest, valid CRC: "
                "the dtype tuple is still bf16/bf16/bf16 and it is still "
                "refused"
            ),
        )

        unmapped = submap(add_b[0], add_b[1])
        self.emit(
            name="capability_refusal_unmapped_output_object",
            pc=PC_ADD_MLP,
            family=int(Major.VECTOR),
            sub=int(Vector.ADD),
            operator_id=operations[PC_ADD_MLP]["operator_id"],
            views=operations[PC_ADD_MLP]["views"],
            object_map=unmapped,
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_CAPABILITY,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=BASE_TRUNK,
            compare_words=untouched_trunk,
            note=(
                "an object with no bank bound to it is a capability this "
                "instance does not have; no operand address is formed and no "
                "read happens"
            ),
        )

        self.emit(
            name="capability_refusal_placement_not_configured",
            pc=PC_ADD_MLP,
            family=int(Major.VECTOR),
            sub=int(Vector.ADD),
            operator_id=operations[PC_ADD_MLP]["operator_id"],
            views=operations[PC_ADD_MLP]["views"],
            object_map=submap(add_b[0], add_b[1], add_b[4]),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_CAPABILITY,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=BASE_TRUNK,
            compare_words=untouched_trunk,
            placement_valid=False,
            note=(
                "the same admitted instruction on an instance that has not "
                "bound its operand banks: the previous TRAP_CAPABILITY, "
                "unchanged, which is what keeps an unwired integration's "
                "behaviour exactly what it was"
            ),
        )

        disagreeing = self._operation(PC_GQA, "ATTENTION.GQA", self.symbols_at(17))
        disagreeing_slots = {
            int(view["slot"]): view for view in disagreeing["views"]
        }
        untouched_attention = self.bank[BASE_SCRATCH_B : BASE_SCRATCH_B + 64]
        self.emit(
            name="descriptor_refusal_gqa_context_disagrees_with_index",
            pc=PC_GQA,
            family=int(Major.ATTENTION),
            sub=1,
            operator_id=disagreeing["operator_id"],
            views=disagreeing["views"],
            object_map=submap(
                int(disagreeing_slots[0]["object_id"]),
                int(disagreeing_slots[1]["object_id"]),
                int(disagreeing_slots[3]["object_id"]),
                int(disagreeing_slots[4]["object_id"]),
            ),
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_DESCRIPTOR,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=BASE_SCRATCH_B,
            compare_words=untouched_attention,
            note=(
                "the index view resolves to position 17 while the request "
                "declares context 17; the two must agree and neither is "
                "trusted alone"
            ),
        )

        self.emit(
            name="engine_refusal_token_outside_vocabulary",
            pc=PC_TOKEN_APPEND,
            family=int(Major.SELECTION),
            sub=int(Selection.TOKEN_APPEND),
            operator_id=operations[PC_TOKEN_APPEND]["operator_id"],
            views=operations[PC_TOKEN_APPEND]["views"],
            object_map=append_map,
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_ENGINE,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=self.ring_slot,
            compare_words=[ordinary],
            preload=(BASE_TOKEN, [VOCABULARY]),
            note="a token outside the policy's vocabulary is not appended",
        )
        self.bank[BASE_TOKEN] = VOCABULARY

        sampling_policy_id = self._sampling_policy()
        self.emit(
            name="capability_refusal_sampling_generation_policy",
            pc=PC_TOKEN_APPEND,
            family=int(Major.SELECTION),
            sub=int(Selection.TOKEN_APPEND),
            operator_id=operations[PC_TOKEN_APPEND]["operator_id"],
            views=operations[PC_TOKEN_APPEND]["views"],
            object_map=append_map,
            context_length=17,
            kv_plane_rows=KV_PLANE_ROWS,
            request_max_new_tokens=1,
            generated_before=0,
            expected_fault=True,
            expected_trap=TRAP_CAPABILITY,
            expected_result_count=0,
            expected_work_count=0,
            expected_write_count=0,
            expected_token=0,
            expected_tie_multiplicity=0,
            expected_eos_reason=0,
            expected_launch=LAUNCH_NONE,
            compare_base=self.ring_slot,
            compare_words=[ordinary],
            preload=(BASE_TOKEN, [ordinary]),
            generation_policy_id=sampling_policy_id,
            note=(
                "a policy naming a sampling mode is a capability refusal: "
                "this device implements no sampling contract, and the refusal "
                "happens before the token object is read"
            ),
        )
        self.bank[BASE_TOKEN] = ordinary

        # ---------------------------------------------------- what bounds it
        # The three operators below are shipped instructions of the governed
        # program that this bridge does not admit, and each is issued here so
        # the refusal is a measurement rather than a reading of the source.
        # They were four.  The fourth was the head span's DMA.GATHER at PC 68,
        # refused because `dense_row_source_ok` pinned a non-embedding
        # gather's source to FP32; that pin was an artefact of the one gather
        # the predicate had been written against and not a property of this
        # design -- `ot_a3_dma_index_mover` has no dtype port at all -- and
        # PC 68 is now issued as a PASSING case above rather than refused
        # here.  What remains is the three MLP projections, whose weight
        # objects are objects of the layer's own 23, and an object no
        # admitted operator can name is one no run of this design can ever
        # resolve.  The bases bound to the three refused weight objects are
        # the halfword bases they would occupy in a projection-matrix bank
        # this vehicle does not stage for them; nothing reads them, and they
        # are here so the refusal is attributable to the view SHAPE and not
        # to an unplaced object.
        refused_matmul_map = dict(object_base)
        refused_matmul_map[matmul_gate[1]] = 0
        refused_matmul_map[matmul_up[1]] = 12288 * ADD_WIDTH
        refused_matmul_map[matmul_down[1]] = 2 * 12288 * ADD_WIDTH
        for name, pc, weights in (
            ("gate", PC_MATMUL_GATE, matmul_gate),
            ("up", PC_MATMUL_UP, matmul_up),
            ("down", PC_MATMUL_DOWN, matmul_down),
        ):
            self.emit(
                name=f"descriptor_refusal_mlp_{name}_projection_weight_view",
                pc=pc,
                family=int(Major.TENSOR),
                sub=int(Tensor.MATMUL),
                operator_id=operations[pc]["operator_id"],
                views=operations[pc]["views"],
                object_map=refused_matmul_map,
                context_length=17,
                kv_plane_rows=KV_PLANE_ROWS,
                request_max_new_tokens=1,
                generated_before=0,
                expected_fault=True,
                expected_trap=TRAP_DESCRIPTOR,
                expected_result_count=0,
                expected_work_count=0,
                expected_write_count=0,
                expected_token=0,
                expected_tie_multiplicity=0,
                expected_eos_reason=0,
                expected_launch=LAUNCH_NONE,
                compare_base=BASE_TRUNK,
                compare_words=untouched_trunk,
                note=(
                    "the admitted TENSOR.MATMUL weight view is [n <= 4096, "
                    "4096]; this one is "
                    f"{operations[pc]['views'][1]['dims']!r} and the operator "
                    "is refused before a single weight halfword is read, so "
                    "object "
                    f"{weights[1]} is placed by the table and never resolved"
                ),
            )


    # -- helpers ------------------------------------------------------------
    def _require_golden(
        self, pc: int, golden_pc: int | None, expected: list[int]
    ) -> None:
        """The scalar reference and the retained golden must agree, or refuse.

        The expectation this campaign compares the RTL against is always the
        one the independent reference computed here from the staged operands.
        Where the shipped prefix also ran the operator, its golden write
        stream is a second, independently produced answer, and the two are
        required to be identical.  A disagreement is a build failure: it means
        either the staging or one of the two models is wrong, and there is no
        version of that in which the campaign should keep going.
        """

        if golden_pc is None:
            return
        golden = list(self.prefix_results[golden_pc])
        if golden != list(expected):
            raise RuntimeError(
                f"PC {pc}: the scalar reference and the retained golden write "
                f"stream of PC {golden_pc} disagree"
            )

    def _loops_at(self, pc: int) -> dict[int, int]:
        loops: dict[int, int] = {}
        for index in range(pc):
            instruction = Instruction.decode(
                self.programs[self.program_base + index].to_bytes(32, "little")
            )
            if instruction.mnemonic == "CONTROL.LOOP_SETUP":
                loop_id = int(instruction.control_id)
                descriptor = self.table.get(
                    loop_id, ExtendedDescriptorType.LOOP_CONTROL
                )
                loops[loop_id] = int(descriptor.payload["lower_bound"])
            elif instruction.mnemonic == "CONTROL.LOOP_NEXT":
                loops.pop(int(instruction.control_id), None)
        return loops

    def _operation(
        self, pc: int, mnemonic: str, symbols: dict[int, int]
    ) -> dict[str, Any]:
        instruction = operator_at(self.programs, self.program_base, pc, mnemonic)
        operator_id = int(instruction.descriptor_id)
        views = resolved_views(
            self.resolver, self.table, operator_id, self._loops_at(pc), symbols
        )
        return {"pc": pc, "operator_id": operator_id, "views": views}

    def _reference_add(self, left: list[int], right: list[int]) -> list[int]:
        return list(bf16_add_rne([left], [right]).values[0])

    def _reference_silu(self, gate: list[int], up: list[int]) -> list[int]:
        return list(qwen3_silu_mul_bf16([gate], [up]).values[0])

    def _reference_gqa(
        self,
        query: list[int],
        key_rows: list[list[int]],
        value_rows: list[list[int]],
        context: int,
    ) -> list[int]:
        def reshape(rows: list[list[int]]) -> list[list[list[int]]]:
            return [
                [
                    row[head * HEAD_WIDTH : (head + 1) * HEAD_WIDTH]
                    for head in range(KV_HEADS)
                ]
                for row in rows
            ]

        position = context - 1
        snapshot = make_kv_snapshot(
            resource_id="qwen.layer0.kv",
            generation=position,
            capacity=8192,
            key_values=reshape(key_rows[:-1]),
            value_values=reshape(value_rows[:-1]),
        )
        prepared = prepare_kv_append(
            snapshot,
            transaction_id=0x4154544E00000011,
            expected_generation=position,
            position_start=position,
            key_values=reshape(key_rows[-1:]),
            value_values=reshape(value_rows[-1:]),
        )
        result = gqa_causal_attention_bf16(
            [
                [
                    query[head * HEAD_WIDTH : (head + 1) * HEAD_WIDTH]
                    for head in range(QUERY_HEADS)
                ]
            ],
            snapshot,
            prepared,
        )
        if result.accounting.score_multiplications != context * GQA_OUTPUT_WORDS:
            raise RuntimeError("independent GQA accounting changed")
        return [code for head in result.output_values[0] for code in head]

    def _clone(self, descriptor: Descriptor, payload: dict[str, Any]) -> Descriptor:
        """A copy with an edited payload; the retained record is never mutated."""

        return Descriptor(
            descriptor_id=descriptor.descriptor_id,
            descriptor_type=descriptor.descriptor_type,
            payload=payload,
            flags=descriptor.flags,
            primary_object_id=descriptor.primary_object_id,
            secondary_object_id=descriptor.secondary_object_id,
            numeric_profile_id=descriptor.numeric_profile_id,
            schedule_id=descriptor.schedule_id,
            permissions=descriptor.permissions,
            owner_scope_id=descriptor.owner_scope_id,
        )

    def _mutated_contract(self, operator_id: int) -> tuple[int, int]:
        operator = self.table[operator_id]
        numeric_id = int(operator.payload["numeric_profile_id"])
        numeric = self.table[numeric_id]
        numeric_payload = dict(numeric.payload)
        digest = bytearray(numeric_payload["contract_digest"])
        digest[-1] ^= 1
        numeric_payload["contract_digest"] = bytes(digest)
        new_numeric_id = self.add_synthetic(
            self._clone(numeric, numeric_payload).encode()
        )
        operator_payload = dict(operator.payload)
        operator_payload["numeric_profile_id"] = new_numeric_id
        clone = self._clone(operator, operator_payload)
        clone.numeric_profile_id = new_numeric_id
        new_operator_id = self.add_synthetic(clone.encode())
        return new_numeric_id, new_operator_id

    def _sampling_policy(self) -> int:
        policy = self.table[self.generation_policy_id]
        payload = dict(policy.payload)
        payload["selection_mode"] = 1
        return self.add_synthetic(self._clone(policy, payload).encode())


def build(
    output: Path | None = None,
    storage_class: str = DEFAULT_STORAGE_CLASS,
) -> dict[str, Any]:
    if output is None:
        output = output_root_for(storage_class)
    builder = Builder(storage_class)
    builder.build_cases()
    output.mkdir(parents=True, exist_ok=True)

    images = {
        "cases.hex": scatter.hex_lines(builder.encoded_cases()),
        "views.hex": scatter.hex_lines(builder.encoded_views()),
        "descriptors.hex": scatter.hex_lines(builder.descriptor_image(), 1536),
        "bank.hex": scatter.hex_lines(builder.initial_bank),
        "index.hex": scatter.hex_lines(builder.index_bank),
        "source.hex": scatter.hex_lines(builder.source_bank),
        # The projection matrices.  Deterministically re-derived from the
        # pinned checkpoint by this builder and bound by SHA-256 below, and
        # deliberately not committed: 8,388,608 codes is not a thing to put
        # in Git, and the campaign regenerates and byte-compares it on every
        # run exactly as it does the committed images.
        "weights.hex": scatter.hex_lines(builder.weight_bank or [0]),
        "preload.hex": scatter.hex_lines(builder.preload_words or [0]),
        "expected.hex": scatter.hex_lines(builder.expected_words),
    }
    for name, payload in images.items():
        (output / name).write_text(payload, encoding="ascii")

    positive = [item for item in builder.cases if not item["expected"]["fault"]]
    negative = [item for item in builder.cases if item["expected"]["fault"]]
    families = sorted({(item["family"], item["sub"]) for item in positive})
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "target": builder.target_key,
        "deployment_sha256": builder.deployment["deployment_sha256"],
        "geometry": {
            "case_words": CASE_WORDS,
            "view_slots": VIEW_SLOTS,
            "view_words": VIEW_WORDS,
            "map_entries": MAP_ENTRIES,
            "map_base": MAP_BASE,
            "bank_words": builder.bank_words,
            "index_words": INDEX_WORDS,
            "source_words": SOURCE_WORDS,
            "weight_words": max(len(builder.weight_bank), 1),
            "descriptor_records": builder.next_synthetic_id,
            "expected_words": len(builder.expected_words),
            "preload_words": max(len(builder.preload_words), 1),
            "kv_plane_rows": KV_PLANE_ROWS,
            "vocabulary": VOCABULARY,
        },
        "admitted_families": [
            {"family": family, "sub": sub} for family, sub in families
        ],
        "governed_program_counters": sorted(
            {int(item["pc"]) for item in positive}
        ),
        "operands": {
            "attention_query_key_value": (
                "retained causal RTL results of shipped decode PCs 26, 29 and 17"
            ),
            "prior_kv_context": (
                "deterministic permutations of the authentic current row; not "
                "model history"
            ),
            "residual_swiglu_logits": (
                "seeded deterministic BF16 spread over the governed shapes; not "
                "checkpoint activations"
            ),
            "normalization_gains": (
                "the PC 8, PC 20 and PC 23 gains are the real checkpoint gains "
                "the retained shipped-prefix source bank carries, at their own "
                "objects' bases; the PC 47 and PC 66 gains are a seeded spread "
                "because the shipped prefix stops at PC 32 and never staged "
                "them"
            ),
            "rope_coefficients": (
                "the FP32 coefficient row the shipped PC 1 gather published, "
                "taken from the retained golden write stream and narrowed to "
                "BF16 by the same round-to-nearest-even the datapath performs. "
                "It is staged into the coefficient object and read there by "
                "both RoPE cases; the PC 1 gather case, which runs after them, "
                "then overwrites that object with the row it selects"
            ),
            "attention_projections": (
                "the key and value projections at PCs 14 and 17 are ISSUED "
                "here, in RTL, against the real checkpoint k_proj and v_proj "
                "of layer zero -- the shard, offset and SHA-256 the "
                "deployment's own object record declares, re-read and "
                "re-hashed at build time, every code consumed -- and their "
                "1,024-word results are required to equal the shipped "
                "prefix's golden write stream for those same program "
                "counters.  The query projection at PC 11 is not issued and "
                "its output is the retained golden value, staged"
            ),
            "head_gather_source_row": (
                "the row PC 68 selects is staged in the source bank because "
                "cfg_source_base is not keyed by object; the staged row is "
                "required at build time to be word for word the PC 66 result "
                "the preceding case's RTL wrote into object 45"
            ),
            "rope_coefficient_gather_source_row": (
                "PC 1 is issued here so ONE campaign drives both operator "
                "descriptors of the ROM lowering's merged DMA.GATHER class, "
                "which G1a decides per campaign.  The row it selects is NOT "
                "the checkpoint RoPE coefficient table: this bridge addresses "
                "a gather's source by launch ordinal, so both gathers read "
                "the row staged at 0 and the shipped PC 1 view's own 256-wide "
                "row selects that row's leading 256 words -- the PC 66 result "
                "the RTL produced.  The coefficient table row itself is "
                "gathered only by the integrated shipped-prefix vehicle, and "
                "this case does not restate that measurement.  The case runs "
                "after both RoPE cases because it publishes into the object "
                "they read"
            ),
        },
        "oracles": {
            "vector_add": "runtime/reference/tensor_accelerator_elementwise.py",
            "vector_silu_mul": "runtime/reference/tensor_accelerator_elementwise.py",
            "attention_gqa": "runtime/reference/tensor_accelerator_attention.py",
            "selection_argmax": "greedy_lowest_token_id_argmax_v1, computed here",
            "selection_token_append": "runtime/sim/engines/selection.py semantics",
            "dma_scatter": "byte-preserving row placement, computed here",
            "vector_rms_norm": "runtime/reference/tensor_accelerator_rmsnorm.py",
            "vector_head_rms_norm": (
                "runtime/reference/tensor_accelerator_rmsnorm.py"
            ),
            "vector_rope": "runtime/reference/tensor_accelerator_rope.py",
            "tensor_matmul": "runtime/reference/tensor_accelerator_bf16.py",
            "dma_gather": "byte-preserving row selection, computed here",
            "independent_of_dut": True,
            "cross_checked_against_the_retained_golden_write_stream": sorted(
                set(PREFIX_REPLAY_PCS) | {PC_MATMUL_KEY, PC_MATMUL_VALUE}
            ),
        },
        "checkpoint_weights": builder.weight_sources,
        "cases": [
            {
                "name": item["name"],
                "pc": item["pc"],
                "family": item["family"],
                "sub": item["sub"],
                "operator_descriptor_id": item["operator_descriptor_id"],
                "context_length": item["context_length"],
                "expected": item["expected"],
                # The table this case binds, and the objects its own operands
                # resolve out of it.  The second list is not the first: an
                # entry that no operand names is bound and not resolved, and
                # the campaign counts only what a case actually resolved.
                "object_map": {
                    str(key): value
                    for key, value in sorted(item["object_map"].items())
                },
                "objects_named": item["objects_named"],
                "placement_valid": item["placement_valid"],
                "note": item["note"],
            }
            for item in builder.cases
        ],
        "expected_pass": {
            "cases": len(builder.cases),
            "positive": len(positive),
            "negative": len(negative),
            "compared_words": sum(
                item["expected"]["compare_count"] for item in builder.cases
            ),
            "write_beats": sum(
                item["expected"]["write_beats"] for item in builder.cases
            ),
        },
        "claim_boundary": {
            "exact_shipped_operator_records": True,
            "exact_resolved_view_stream": True,
            "bit_exact_against_independent_reference": True,
            "six_previously_capability_trapped_families_admitted": True,
            "object_keyed_families_issued_through_one_shared_table": True,
            "real_checkpoint_normalization_gains": False,
            "three_of_five_normalization_gains_are_checkpoint": True,
            # Two of the layer's seven TENSOR.MATMULs are issued, on the
            # checkpoint's own layer-zero k_proj and v_proj.  Five are not:
            # PC 11 and PC 41 are admitted and simply cost 16.8 x 10^6 MACs
            # each with no object this run needs, and PCs 50, 53 and 59 are
            # refused by the weight-view predicate.  "issued" therefore stays
            # false and the count is stated instead.
            "layer_matmuls_issued": False,
            "layer_matmuls_issued_count": 2,
            "layer_matmul_count": 7,
            "real_checkpoint_projection_weights": True,
            "runtime_context_length": True,
            "read_modify_write_placement": True,
            "fail_closed_matrix": True,
            "authentic_prior_context_kv": False,
            "checkpoint_residual_swiglu_logits": False,
            "complete_layer": False,
            "model_token_generation": False,
            "tpot": False,
        },
        "upstream_dependency": {
            "deployment_manifest": str(
                scatter.DEPLOYMENT_MANIFEST.relative_to(ROOT)
            ),
            "deployment_manifest_sha256": sha256_file(scatter.DEPLOYMENT_MANIFEST),
            "descriptor_image": str(scatter.DESCRIPTOR_IMAGE.relative_to(ROOT)),
            "descriptor_image_sha256": sha256_file(scatter.DESCRIPTOR_IMAGE),
            "program_image": str(scatter.PROGRAM_IMAGE.relative_to(ROOT)),
            "program_image_sha256": sha256_file(scatter.PROGRAM_IMAGE),
            "prefix_expected": str(scatter.PREFIX_EXPECT.relative_to(ROOT)),
            "prefix_expected_sha256": sha256_file(scatter.PREFIX_EXPECT),
            "prefix_writes": str(scatter.PREFIX_WRITES.relative_to(ROOT)),
            "prefix_writes_sha256": sha256_file(scatter.PREFIX_WRITES),
            "prefix_source": str(PREFIX_SOURCE.relative_to(ROOT)),
            "prefix_source_sha256": sha256_file(PREFIX_SOURCE),
        },
    }
    manifest["image_sha256"] = {
        name: sha256_file(output / name)
        for name in VECTOR_FILES
        if name != "index.json"
    }
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--output", type=Path, default=None)
    result.add_argument(
        "--storage-class",
        choices=sorted(TARGETS),
        default=DEFAULT_STORAGE_CLASS,
        help=(
            "which Qwen lowering to build against.  The two are not "
            "interchangeable: their governed descriptor ids differ at every "
            "PC, so each storage class gets its own vector set and its own "
            "simulation."
        ),
    )
    result.add_argument(
        "--all",
        action="store_true",
        help="build every storage class in TARGETS",
    )
    return result


def main() -> int:
    args = parser().parse_args()
    classes = sorted(TARGETS) if args.all else [args.storage_class]
    if args.all and args.output is not None:
        raise SystemExit("--all writes one directory per storage class; drop --output")
    for storage_class in classes:
        manifest = build(args.output, storage_class)
        print(
            "built ABI3 operator-admission vectors "
            f"storage_class={storage_class} "
            f"target={manifest['target']} "
            f"deployment={manifest['deployment_sha256'][:12]} "
            f"cases={manifest['expected_pass']['cases']} "
            f"positive={manifest['expected_pass']['positive']} "
            f"words={manifest['expected_pass']['compared_words']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
