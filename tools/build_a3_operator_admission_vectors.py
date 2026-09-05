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

from runtime.abi3.constants import Dma, Major, NO_ID, Selection, Vector  # noqa: E402
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
from runtime.sim.memory import ViewResolver  # noqa: E402
from tools import build_a3_qwen_gqa_vectors as gqa  # noqa: E402
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

CASE_WORDS = 64
VIEW_SLOTS = 5
VIEW_WORDS = 8
MAP_ENTRIES = 8

# The governed decode program counters of the six families.
PC_SCATTER_KEY = 32
PC_SCATTER_VALUE = 35
PC_GQA = 38
PC_ADD_ATTENTION = 44
PC_SILU_MUL = 56
PC_ADD_MLP = 62
PC_ARGMAX = 70
PC_TOKEN_APPEND = 72

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
BANK_WORDS = BASE_RING + 1
INDEX_WORDS = 64

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

VECTOR_FILES = (
    "cases.hex",
    "views.hex",
    "descriptors.hex",
    "bank.hex",
    "index.hex",
    "preload.hex",
    "expected.hex",
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
        self.bank = [0] * BANK_WORDS
        self.initial_bank: list[int] = []
        self.index_bank = list(range(INDEX_WORDS))
        self.cases: list[dict[str, Any]] = []
        self.expected_words: list[int] = []
        self.extra_records: dict[int, bytes] = {}
        self.preload_words: list[int] = []
        self.next_synthetic_id = self.descriptor_count

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
                    values[24 + 2 * slot] = entries[slot][0]
                    values[25 + 2 * slot] = entries[slot][1]
                else:
                    values[24 + 2 * slot] = 0xFFFFFFFF
                    values[25 + 2 * slot] = 0
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

        spread = Spread(0x5150_4F54_414C_4C41)
        trunk = spread.row(ADD_WIDTH, low_exponent=118, high_exponent=130)
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

        for row in range(KV_PLANE_ROWS):
            start = BASE_KV + row * KV_PLANE_WORDS
            self.bank[start : start + KV_PLANE_WORDS] = key_rows[row]
            start = BASE_KV + (KV_PLANE_ROWS + row) * KV_PLANE_WORDS
            self.bank[start : start + KV_PLANE_WORDS] = value_rows[row]
        self.bank[
            BASE_SCATTER_KEY_SOURCE : BASE_SCATTER_KEY_SOURCE + KV_PLANE_WORDS
        ] = current_key
        self.bank[
            BASE_SCATTER_VALUE_SOURCE : BASE_SCATTER_VALUE_SOURCE + KV_PLANE_WORDS
        ] = current_value
        # Scratch A holds the RoPE'd query when the attention runs.
        self.bank[BASE_SCRATCH_A : BASE_SCRATCH_A + ADD_WIDTH] = query
        self.bank[BASE_TRUNK : BASE_TRUNK + ADD_WIDTH] = trunk
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

        object_base = {
            scatter_key[0]: 0,
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
        }

        def submap(*object_ids: int) -> dict[int, int]:
            return {value: object_base[value] for value in object_ids}

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
                object_map=submap(
                    int(slots[0]["object_id"]),
                    int(slots[1]["object_id"]),
                    int(slots[4]["object_id"]),
                ),
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
                object_map=submap(
                    int(slots[0]["object_id"]),
                    int(slots[1]["object_id"]),
                    int(slots[3]["object_id"]),
                    int(slots[4]["object_id"]),
                ),
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

        # -- program order: scatter, attend, residual, SwiGLU, residual ------
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
            object_map=submap(add_a[0], add_a[1], add_a[4]),
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

        gated = self._reference_silu(silu_gate, silu_up)
        self.emit(
            name="vector_silu_mul_swiglu",
            pc=PC_SILU_MUL,
            family=int(Major.VECTOR),
            sub=int(Vector.SILU_MUL),
            operator_id=operations[PC_SILU_MUL]["operator_id"],
            views=operations[PC_SILU_MUL]["views"],
            object_map=submap(silu[0], silu[1], silu[4]),
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
            object_map=submap(add_b[0], add_b[1], add_b[4]),
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
            object_map=submap(argmax[0], argmax[4]),
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
            object_map=append_map,
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
            compare_base=BASE_RING,
            compare_words=[token],
            note="the selected id is in the policy's EOS set: OFFICIAL_EOS",
        )
        self.bank[BASE_RING] = token

        ordinary = 12345
        self.emit(
            name="selection_token_append_continues",
            pc=PC_TOKEN_APPEND,
            family=int(Major.SELECTION),
            sub=int(Selection.TOKEN_APPEND),
            operator_id=operations[PC_TOKEN_APPEND]["operator_id"],
            views=operations[PC_TOKEN_APPEND]["views"],
            object_map=append_map,
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
            compare_base=BASE_RING,
            compare_words=[ordinary],
            preload=(BASE_TOKEN, [ordinary]),
            note="not EOS and below the request bound: the session continues",
        )
        self.bank[BASE_TOKEN] = ordinary
        self.bank[BASE_RING] = ordinary

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
            compare_base=BASE_RING,
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
            compare_base=BASE_RING,
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

    # -- helpers ------------------------------------------------------------
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
            "bank_words": BANK_WORDS,
            "index_words": INDEX_WORDS,
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
        },
        "oracles": {
            "vector_add": "runtime/reference/tensor_accelerator_elementwise.py",
            "vector_silu_mul": "runtime/reference/tensor_accelerator_elementwise.py",
            "attention_gqa": "runtime/reference/tensor_accelerator_attention.py",
            "selection_argmax": "greedy_lowest_token_id_argmax_v1, computed here",
            "selection_token_append": "runtime/sim/engines/selection.py semantics",
            "dma_scatter": "byte-preserving row placement, computed here",
            "independent_of_dut": True,
        },
        "cases": [
            {
                "name": item["name"],
                "pc": item["pc"],
                "family": item["family"],
                "sub": item["sub"],
                "operator_descriptor_id": item["operator_descriptor_id"],
                "context_length": item["context_length"],
                "expected": item["expected"],
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
