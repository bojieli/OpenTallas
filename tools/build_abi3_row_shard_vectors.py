#!/usr/bin/env python3
"""Vectors for the row-shard vehicle: one operator, one range of output rows.

The governed Qwen decode program issues seven distinct ``TENSOR.MATMUL``
operators.  Three of them the integrated shipped-prefix vehicle already
executes whole; four it does not, and two of those four are refused by the
issue bridge outright because their weight view is ``[12288, 4096]`` or
``[151936, 4096]`` where the admitted predicate is ``[n <= 4096, 4096]``.

A row shard is the exact decomposition that reaches them.  Output row ``j`` of
a MATMUL is ``dot(activation, weight_row_j)`` over the whole reduction axis;
``ot_a3_mac_lane`` walks K in ascending order for one output row and carries no
state across a row boundary, so rows ``[r, r+n)`` computed alone are bit for
bit the rows ``[r, r+n)`` of the whole operator.  This builder emits, for one
such range:

* the retained OPERATOR, TENSOR_VIEW and NUMERIC records of that program
  counter, with EXACTLY TWO fields rewritten -- the weight view's ``dim0`` and
  the output view's ``dim1``/``stride0``, all three to the shard's row count.
  Every other field, the numeric contract digest included, is the shipped
  record byte for byte, and ``rewritten_fields`` in the manifest says so;
* the weight window base of the shard's first row inside that operator's own
  checkpoint segment, so the RTL reads the checkpoint's real bytes;
* the golden for the shard's rows, from the exact BF16 kernel, with a sample
  of rows independently recomputed by the scalar oracle in
  ``runtime/reference`` and required byte-identical.

What the activation is, stated once and not softened.  For the three program
counters the shipped prefix reaches (11, 14, 17) it is the layer-zero RMSNorm
result recomputed from the checkpoint here and checked against the shipped
prefix vector set's own committed digest, so the operand is the same authentic
activation the integrated run uses.  For every other program counter the
activation is a seeded deterministic BF16 spread: those activations are
produced by operators this vehicle does not run, and nothing here claims a
layer, a token or a rate.  What a shard establishes is that the RTL's
arithmetic equals the golden model's, bit for bit, on the checkpoint's own
weight bytes, at the shapes the governed program issues.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import DType, Major, NO_ID, Tensor  # noqa: E402
from runtime.abi3.deployment import Deployment, resolve_path  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    Descriptor,
    ExtendedDescriptorType,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.reference.tensor_accelerator_bf16 import (  # noqa: E402
    dense_bf16_linear_bf16 as scalar_dense_bf16_linear_bf16,
)
from runtime.reference.tensor_accelerator_rmsnorm import (  # noqa: E402
    rms_norm_bf16,
)
from runtime.sim.memory import ViewResolver  # noqa: E402
from runtime.tensor_accelerator.bf16 import (  # noqa: E402
    dense_bf16_linear_bf16,
)
from tools import build_a3_qwen_kv_scatter_vectors as scatter  # noqa: E402
from tools.build_a3_operator_admission_vectors import (  # noqa: E402
    build_table,
    retained_program,
)
from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    TARGETS as RTL_TARGETS,
    certified_deployment_identity,
)
from tools.abi3_row_shard import (  # noqa: E402
    ShardDescriptor,
    compose,
    plan_row_shards,
    plan_row_shards_of_size,
)

SCHEMA = "opentallas.rtl.abi3_row_shard_vectors.v1"
STORAGE_CLASSES = {
    "rom": "qwen3-8b-rom-single-chip",
    "hbm": "qwen3-8b-hbm-single-chip",
}
EMBEDDING_WIDTH = 4096
# The bridge's admitted MATMUL weight predicate: rank 2, dim1 == 4096, and
# dim0 in [1, 4096].  It is read here, not chosen: a shard wider than this is
# refused by the design and the campaign records the refusal.
MAX_ADMITTED_ROWS = EMBEDDING_WIDTH
# ot_a3_pkg::A3_TRAP_DESCRIPTOR.  A shard the bridge's weight or input
# predicate refuses is not a hole in this campaign; it is the measurement, and
# the case is emitted as a fail-closed one that must return exactly this class
# with zero launches, zero work and zero writes.
TRAP_DESCRIPTOR = 3

CASE_WORDS = 128
VIEW_SLOTS = 5
VIEW_WORDS = 8
MAP_BASE = 64
MAP_ENTRIES = 32
BANK_INPUT_BASE = 0
BANK_OUTPUT_BASE = 16384
DESC_RECORDS = 320
INDEX_WORDS = 64
SOURCE_WORDS = 16

# The shipped-prefix vector set's own committed digest of the layer-zero
# RMSNorm result, which is the activation PCs 11, 14 and 17 consume.
PREFIX_VECTORS = (
    ROOT / "testdata/compiler/abi3_shipped_prefix/abi3_shipped_prefix_vectors.json"
)
PREFIX_ACTIVATION_PCS = (11, 14, 17)


class BuildError(SystemExit):
    pass


def _target(storage_class: str):
    key = STORAGE_CLASSES[storage_class]
    for target in RTL_TARGETS:
        if target.key == key:
            return target
    raise BuildError(f"no RTL target named {key}")


def _seeded_bf16_row(seed: str, width: int) -> list[int]:
    """A deterministic BF16 spread, from SHA-256 and nothing else.

    Exponents are held in [120, 127] so a 4,096-term reduction of products of
    two such rows cannot leave binary32 range, and no reserved code (exponent
    0xFF) can be produced.  It depends on no library's random state, so the
    same seed gives the same row on any machine and any version.
    """

    codes: list[int] = []
    block = b""
    counter = 0
    while len(codes) < width:
        if not block:
            block = hashlib.sha256(
                seed.encode("utf-8") + counter.to_bytes(8, "little")
            ).digest()
            counter += 1
        raw = int.from_bytes(block[:2], "little")
        block = block[2:]
        sign = (raw >> 15) & 1
        exponent = 120 + ((raw >> 8) & 0x7)
        mantissa = raw & 0x7F
        codes.append((sign << 15) | (exponent << 7) | mantissa)
    return codes


def _checkpoint_rows(
    target: Any,
    deployment: Deployment,
    object_id: int,
    first_row: int,
    row_count: int,
    columns: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Read rows [first_row, first_row+row_count) of a checkpoint matrix.

    The object's FIRST segment is the layer-zero tensor, which is the one the
    governed layer-zero span names; the digest of the whole segment is the
    deployment's own and is recorded, and the read is bounded inside it.
    """

    source = deployment.objects[object_id]
    if source.kind != "segments" or not source.segments:
        raise BuildError(f"matrix object {object_id} is {source.kind}")
    segment = source.segments[0]
    row_bytes = columns * 2
    want = row_count * row_bytes
    at = int(segment.offset) + first_row * row_bytes
    if first_row < 0 or want <= 0 or (first_row + row_count) * row_bytes > int(
        segment.bytes
    ):
        raise BuildError(
            f"rows [{first_row}:{first_row + row_count}) leave the segment of "
            f"object {object_id}"
        )
    root = Path(target.checkpoint).expanduser()
    path = resolve_path(root, segment.path)
    with path.open("rb") as handle:
        handle.seek(at)
        payload = handle.read(want)
    if len(payload) != want:
        raise BuildError("checkpoint returned a short matrix range")
    codes = np.frombuffer(payload, dtype="<u2").reshape(row_count, columns)
    identity = {
        "object_id": object_id,
        "checkpoint": str(target.checkpoint),
        "checkpoint_revision": root.name,
        "shard": segment.path,
        "segment_offset": int(segment.offset),
        "segment_bytes": int(segment.bytes),
        "segment_sha256": str(segment.sha256),
        "read_offset": at,
        "read_bytes": want,
        "rows": [first_row, first_row + row_count],
    }
    return codes, identity


def _prefix_activation(
    target: Any, deployment: Deployment, resolver: ViewResolver, symbols: dict[int, int]
) -> tuple[list[int], dict[str, Any]]:
    """The layer-zero RMSNorm result, recomputed from the checkpoint.

    Its digest is compared against the shipped-prefix vector set's own
    committed ``expected_row_sha256`` for PC 8, so the activation this vehicle
    feeds PCs 11, 14 and 17 is provably the one the integrated vehicle feeds
    them.  A disagreement is a refusal, not a warning.
    """

    _, body = split_program(deployment.program)
    instructions = decode_body(body)
    embed_pc = None
    rms_pc = None
    for pc, instruction in enumerate(instructions):
        mnemonic = instruction.mnemonic
        if mnemonic == "TENSOR.EMBED_LOOKUP" and embed_pc is None:
            embed_pc = pc
        elif mnemonic == "VECTOR.RMS_NORM" and rms_pc is None:
            rms_pc = pc
        if embed_pc is not None and rms_pc is not None:
            break
    if embed_pc is None or rms_pc is None:
        raise BuildError("the decode prefix has no embedding or no RMSNorm")

    prefix = json.loads(PREFIX_VECTORS.read_text(encoding="utf-8"))
    case = next(
        item
        for item in prefix["cases"]
        if item["deployment_sha256"] == deployment.deployment_digest.hex()
    )
    embed_record = next(
        item for item in case["supported_prefix"] if item["pc"] == embed_pc
    )
    rms_record = next(
        item for item in case["supported_prefix"] if item["pc"] == rms_pc
    )

    embed_operator = deployment.table.get(
        int(instructions[embed_pc].descriptor_id), ExtendedDescriptorType.OPERATOR
    )
    table_view = deployment.table.get(
        int(embed_operator.payload["input_view_1"]),
        ExtendedDescriptorType.TENSOR_VIEW,
    )
    token_id = int(embed_record["token_id"])
    row, _ = _checkpoint_rows(
        target, deployment, table_view.primary_object_id, token_id, 1,
        EMBEDDING_WIDTH,
    )
    embed_words = tuple(int(code) for code in row[0])
    embed_digest = hashlib.sha256(
        b"".join(int(code).to_bytes(2, "little") for code in embed_words)
    ).hexdigest()
    if embed_digest != embed_record["expected_row_sha256"]:
        raise BuildError(
            "the embedding row disagrees with the shipped prefix's own digest"
        )

    rms_operator = deployment.table.get(
        int(instructions[rms_pc].descriptor_id), ExtendedDescriptorType.OPERATOR
    )
    gain_view = deployment.table.get(
        int(rms_operator.payload["input_view_1"]),
        ExtendedDescriptorType.TENSOR_VIEW,
    )
    gain, _ = _checkpoint_rows(
        target, deployment, gain_view.primary_object_id, 0, 1, EMBEDDING_WIDTH
    )
    gain_words = tuple(int(code) for code in gain[0])
    result = rms_norm_bf16((embed_words,), gain_words)
    words = [int(code) for code in result.values[0]]
    digest = hashlib.sha256(
        b"".join(code.to_bytes(2, "little") for code in words)
    ).hexdigest()
    if digest != rms_record["expected_row_sha256"]:
        raise BuildError(
            "the recomputed RMSNorm result disagrees with the shipped "
            "prefix's own committed digest"
        )
    return words, {
        "kind": "layer0_rms_norm_of_the_checkpoint_embedding_row",
        "is_checkpoint_derived": True,
        "embedding_program_counter": embed_pc,
        "rms_norm_program_counter": rms_pc,
        "token_id": token_id,
        "sha256": digest,
        "agrees_with": {
            "artifact": str(PREFIX_VECTORS.relative_to(ROOT)),
            "field": f"cases[].supported_prefix[pc={rms_pc}].expected_row_sha256",
        },
    }


def _clone(descriptor: Descriptor, payload: dict[str, Any]) -> Descriptor:
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


def build(
    storage_class: str,
    program_counter: int,
    shard_count: int | None,
    rows_per_shard: int | None,
    output: Path,
) -> dict[str, Any]:
    target = _target(storage_class)
    identity = certified_deployment_identity(target)
    deployment = Deployment.read(ROOT / target.deployment)
    deployment_sha = deployment.deployment_digest.hex()
    if deployment_sha != identity.deployment_sha256:
        raise BuildError(f"{target.key}: deployment certificate is stale")

    manifest_json, descriptors_image, programs_image, descriptor_base, program_base = (
        retained_program(target.key)
    )
    entry = next(
        item for item in manifest_json["deployments"] if item["key"] == target.key
    )
    if entry["deployment_sha256"] != deployment_sha:
        raise BuildError(f"{target.key}: retained image is a different deployment")
    descriptor_count = int(entry["descriptor_count"])
    table, records = build_table(descriptors_image, descriptor_base, descriptor_count)
    if descriptor_count > DESC_RECORDS:
        raise BuildError("the retained table does not fit the vehicle's store")

    _, body = split_program(deployment.program)
    instructions = decode_body(body)
    if program_counter >= len(instructions):
        raise BuildError(f"PC {program_counter} is past the program")
    instruction = instructions[program_counter]
    if instruction.mnemonic != "TENSOR.MATMUL":
        raise BuildError(
            f"PC {program_counter} is {instruction.mnemonic}, not TENSOR.MATMUL"
        )
    operator_id = int(instruction.descriptor_id)
    operator = table.get(operator_id, ExtendedDescriptorType.OPERATOR)
    input_view_id = int(operator.payload["input_view_0"])
    weight_view_id = int(operator.payload["input_view_1"])
    output_view_id = int(operator.payload["output_view_0"])
    numeric_id = int(operator.payload["numeric_profile_id"])
    input_view = table.get(input_view_id, ExtendedDescriptorType.TENSOR_VIEW)
    weight_view = table.get(weight_view_id, ExtendedDescriptorType.TENSOR_VIEW)
    output_view = table.get(output_view_id, ExtendedDescriptorType.TENSOR_VIEW)

    declared_rows = int(weight_view.payload["dim0"])
    reduction = int(weight_view.payload["dim1"])
    if int(output_view.payload["dim1"]) != declared_rows:
        raise BuildError("the output view does not carry the weight's row count")
    input_columns = int(input_view.payload["dim1"])

    operator_key = f"{target.key}/pc{program_counter}/desc{operator_id}"

    # Which shards.  The bridge admits a weight view of at most 4,096 rows, so
    # a plan whose shards exceed that is a plan of refusals; the caller may ask
    # for one deliberately, and the campaign records what the design answered.
    if shard_count is not None and rows_per_shard is not None:
        raise BuildError("give a shard count or a shard size, not both")
    if shard_count is not None:
        shards = plan_row_shards(operator_key, declared_rows, shard_count)
    elif rows_per_shard is not None:
        shards = plan_row_shards_of_size(operator_key, declared_rows, rows_per_shard)
    else:
        shards = [ShardDescriptor(operator_key, 0, declared_rows)]

    # The activation.
    resolver = ViewResolver(deployment, None)
    if program_counter in PREFIX_ACTIVATION_PCS and input_columns == EMBEDDING_WIDTH:
        activation, activation_identity = _prefix_activation(
            target, deployment, resolver, {}
        )
    else:
        seed = f"opentallas/row-shard/{target.key}/pc{program_counter}/activation"
        activation = _seeded_bf16_row(seed, input_columns)
        activation_identity = {
            "kind": "seeded_deterministic_bf16_spread",
            "is_checkpoint_derived": False,
            "seed": seed,
            "generator": "sha256 stream, exponent held in [120, 127]",
            "sha256": hashlib.sha256(
                b"".join(int(code).to_bytes(2, "little") for code in activation)
            ).hexdigest(),
            "note": (
                "the operator that produces this activation in the governed "
                "program is not run by this vehicle; the golden is computed "
                "from these same words, so what the shard establishes is the "
                "RTL's arithmetic on the checkpoint's own weight bytes and "
                "not a layer, a token or a rate"
            ),
        }
    activation_codes = np.asarray(activation, dtype=np.uint16).reshape(
        1, input_columns
    )

    output.mkdir(parents=True, exist_ok=True)
    shard_records: list[dict[str, Any]] = []
    golden_by_shard: list[tuple[ShardDescriptor, list[int]]] = []
    differential_rows = 0
    weight_identity_all: dict[str, Any] | None = None

    for index, shard in enumerate(shards):
        weight_codes, weight_identity = _checkpoint_rows(
            target,
            deployment,
            weight_view.primary_object_id,
            shard.first_output_row,
            shard.row_count,
            reduction,
        )
        if weight_identity_all is None:
            weight_identity_all = {
                key: value
                for key, value in weight_identity.items()
                if key not in {"read_offset", "read_bytes", "rows"}
            }
        result = dense_bf16_linear_bf16(activation_codes, weight_codes)
        if int(result.output_saturated_element_count) != 0:
            raise BuildError(f"{shard.key}: the golden saturated on output")
        golden = [int(code) for code in result.values[0]]
        golden_by_shard.append((shard, golden))

        # The vectorised exact kernel is checked against the independent
        # scalar oracle on a sample of this shard's own rows -- the first, the
        # second and the last, which is where an off-by-one in the window base
        # or the row count would land.
        sample = sorted({0, min(1, shard.row_count - 1), shard.row_count - 1})
        scalar = scalar_dense_bf16_linear_bf16(
            tuple(tuple(int(code) for code in activation_codes[0]) for _ in range(1)),
            tuple(
                tuple(int(code) for code in weight_codes[row]) for row in sample
            ),
        )
        for position, row in enumerate(sample):
            if int(scalar.values[0][position]) != golden[row]:
                raise BuildError(
                    f"{shard.key}: the exact kernel and the scalar oracle "
                    f"disagree at row {shard.first_output_row + row}"
                )
        differential_rows += len(sample)

        shard_dir = output / f"shard_{index:03d}"
        shard_dir.mkdir(parents=True, exist_ok=True)
        rewritten = _emit_shard(
            shard_dir,
            table=table,
            records=records,
            descriptor_count=descriptor_count,
            operator=operator,
            operator_id=operator_id,
            input_view=input_view,
            input_view_id=input_view_id,
            weight_view=weight_view,
            weight_view_id=weight_view_id,
            output_view=output_view,
            output_view_id=output_view_id,
            numeric_id=numeric_id,
            shard=shard,
            reduction=reduction,
            activation=activation,
            golden=golden,
            target=target,
            deployment=deployment,
            segment=deployment.objects[weight_view.primary_object_id].segments[0],
            case_index=index,
            program_counter=program_counter,
            declared_rows=declared_rows,
        )
        shard_records.append(
            {
                "index": index,
                "directory": str(shard_dir.relative_to(output)),
                "first_output_row": shard.first_output_row,
                "row_count": shard.row_count,
                "operator": shard.operator,
                "key": shard.key,
                "weight_window_base_bytes": shard.first_output_row * reduction * 2,
                "expected_result_count": shard.row_count,
                "expected_work_count": shard.row_count * reduction,
                "expected_write_beats": shard.row_count,
                "multiply_accumulates": shard.row_count * reduction,
                "admitted_by_the_bridge_predicate": bool(
                    rewritten["admitted_by_the_bridge_predicate"]
                ),
                "expected_fault": rewritten["expected_fault"],
                "expected_trap_class": rewritten["expected_trap_class"],
                "drives_the_shipped_descriptor": rewritten[
                    "drives_the_shipped_descriptor"
                ],
                "golden_sha256": hashlib.sha256(
                    b"".join(code.to_bytes(2, "little") for code in golden)
                ).hexdigest(),
                "weight_source": weight_identity,
                "rewritten_fields": rewritten,
            }
        )

    composed = compose(declared_rows, golden_by_shard)

    # The whole operator's golden, walked in a DIFFERENT decomposition from
    # the shard plan -- 3,000-row chunks, which divides none of the shard
    # sizes this campaign uses -- and streamed into one digest.  Agreeing with
    # the shard composition is then a real statement about row independence in
    # the reference itself, and not the same partition compared with itself.
    # It is streamed because the LM head is 1.24 GB and holding it decoded is
    # 2.5 GB of float32 nobody needs.
    whole_digest = hashlib.sha256()
    chunk = 3000
    at = 0
    while at < declared_rows:
        rows = min(chunk, declared_rows - at)
        block, _ = _checkpoint_rows(
            target, deployment, weight_view.primary_object_id, at, rows, reduction
        )
        piece = dense_bf16_linear_bf16(activation_codes, block)
        if int(piece.output_saturated_element_count) != 0:
            raise BuildError("the whole-operator golden saturated on output")
        whole_digest.update(
            np.ascontiguousarray(piece.values, dtype="<u2").tobytes()
        )
        at += rows
    whole_sha = whole_digest.hexdigest()
    if composed.sha256 != whole_sha:
        raise BuildError(
            "the composition of the shard goldens is not the whole operator's "
            "golden; the decomposition is not exact"
        )

    manifest = {
        "schema": SCHEMA,
        "storage_class": storage_class,
        "target": target.key,
        "deployment_sha256": deployment_sha,
        "program_counter": program_counter,
        "operator_descriptor_id": operator_id,
        "operator_key": operator_key,
        "mnemonic": "TENSOR.MATMUL",
        "numeric_profile_id": numeric_id,
        "numeric_contract_sha256": bytes(
            table.get(numeric_id, ExtendedDescriptorType.NUMERIC).payload[
                "contract_digest"
            ]
        ).hex(),
        "declared_output_rows": declared_rows,
        "reduction": reduction,
        "multiply_accumulates": declared_rows * reduction,
        "whole_operator_golden_sha256": whole_sha,
        "composed_shard_golden_sha256": composed.sha256,
        "composition_equals_whole_operator_golden": composed.sha256 == whole_sha,
        "partition_proof": composed.partition_proof,
        "activation": activation_identity,
        "weight_source": weight_identity_all,
        "differential_rows_recomputed_by_the_scalar_oracle": differential_rows,
        "bridge_weight_row_limit": MAX_ADMITTED_ROWS,
        "whole_operator_admitted_by_the_bridge_predicate": bool(
            declared_rows <= MAX_ADMITTED_ROWS
            and int(input_view.payload["dim1"]) == EMBEDDING_WIDTH
            and reduction == EMBEDDING_WIDTH
        ),
        "whole_operator_golden_chunk_rows": 3000,
        "retained_images": {
            "a3_descriptor.hex": scatter.sha256_file(scatter.DESCRIPTOR_IMAGE)
            if hasattr(scatter, "sha256_file")
            else hashlib.sha256(scatter.DESCRIPTOR_IMAGE.read_bytes()).hexdigest(),
            "a3_program.hex": hashlib.sha256(
                scatter.PROGRAM_IMAGE.read_bytes()
            ).hexdigest(),
            "abi3_deployment_rtl_vectors.json": hashlib.sha256(
                scatter.DEPLOYMENT_MANIFEST.read_bytes()
            ).hexdigest(),
        },
        "geometry": {
            "case_words": CASE_WORDS,
            "view_slots": VIEW_SLOTS,
            "view_words": VIEW_WORDS,
            "map_entries": MAP_ENTRIES,
            "descriptor_records": DESC_RECORDS,
            "bank_input_base": BANK_INPUT_BASE,
            "bank_output_base": BANK_OUTPUT_BASE,
        },
        "shards": shard_records,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _emit_shard(
    shard_dir: Path,
    *,
    table: Any,
    records: dict[int, bytes],
    descriptor_count: int,
    operator: Descriptor,
    operator_id: int,
    input_view: Descriptor,
    input_view_id: int,
    weight_view: Descriptor,
    weight_view_id: int,
    output_view: Descriptor,
    output_view_id: int,
    numeric_id: int,
    shard: ShardDescriptor,
    reduction: int,
    activation: list[int],
    golden: list[int],
    target: Any,
    deployment: Deployment,
    segment: Any,
    case_index: int,
    program_counter: int,
    declared_rows: int,
) -> dict[str, Any]:
    """One shard's vector directory, and the fields it rewrote to make it."""

    next_id = descriptor_count
    extra: dict[int, bytes] = {}

    # A shard that IS the whole operator rewrites nothing, so it must not be
    # given a rewritten record either.  In that case the vehicle drives the
    # SHIPPED operator, weight-view and output-view descriptor ids, byte for
    # byte out of the retained image, and the run is a positive issue of the
    # governed program's own descriptor rather than of a copy of it.  This is
    # not a convenience: a coverage claim about descriptor 130 has to be a run
    # that fetched descriptor 130.
    drives_the_shipped_descriptor = (
        shard.first_output_row == 0 and shard.row_count == declared_rows
    )
    if drives_the_shipped_descriptor:
        shard_weight_id = weight_view_id
        shard_output_id = output_view_id
        shard_operator_id = operator_id
    else:
        weight_payload = dict(weight_view.payload)
        weight_payload["dim0"] = shard.row_count
        shard_weight_id = next_id
        extra[shard_weight_id] = _clone(weight_view, weight_payload).encode()
        next_id += 1

        output_payload = dict(output_view.payload)
        output_payload["dim1"] = shard.row_count
        output_payload["stride0"] = shard.row_count
        shard_output_id = next_id
        extra[shard_output_id] = _clone(output_view, output_payload).encode()
        next_id += 1

        operator_payload = dict(operator.payload)
        operator_payload["input_view_1"] = shard_weight_id
        operator_payload["output_view_0"] = shard_output_id
        shard_operator_id = next_id
        extra[shard_operator_id] = _clone(operator, operator_payload).encode()
        next_id += 1
        if next_id > DESC_RECORDS:
            raise BuildError("the shard records do not fit the vehicle's store")

    image: list[int] = []
    for descriptor_id in range(DESC_RECORDS):
        record = records.get(descriptor_id) or extra.get(descriptor_id, b"")
        image.append(
            int.from_bytes(
                record
                if len(record) == scatter.DESCRIPTOR_BYTES
                else scatter.padded_record(record),
                "little",
            )
        )

    # What the design's own predicates say about this shard, read off the
    # bridge's admitted MATMUL weight and input rules rather than assumed: the
    # weight view must be rank 2 with dim1 == 4,096 and dim0 in [1, 4,096],
    # and the input row must be 4,096 wide.  A shard outside them is issued
    # anyway, as a fail-closed case that must return TRAP_DESCRIPTOR with
    # nothing launched and nothing written.
    admitted = (
        shard.row_count <= MAX_ADMITTED_ROWS
        and int(input_view.payload["dim1"]) == EMBEDDING_WIDTH
        and int(weight_view.payload["dim1"]) == EMBEDDING_WIDTH
    )
    case = [0] * CASE_WORDS
    case[0] = int(Major.TENSOR)
    case[1] = int(Tensor.MATMUL)
    case[2] = shard_operator_id
    case[3] = 0 if admitted else 1                # expected fault
    case[4] = 0 if admitted else TRAP_DESCRIPTOR  # expected trap
    case[5] = shard.row_count if admitted else 0
    case[6] = shard.row_count * reduction if admitted else 0
    case[7] = shard.row_count if admitted else 0
    case[8] = BANK_OUTPUT_BASE                    # output base in the bank
    case[9] = shard.row_count if admitted else 0  # words to compare
    case[10] = 0                                  # base in expected.hex
    window_base = shard.first_output_row * reduction * 2
    case[11] = window_base & 0xFFFFFFFF
    case[12] = (window_base >> 32) & 0xFFFFFFFF
    case[13] = BANK_INPUT_BASE
    case[14] = declared_rows
    case[15] = shard.first_output_row
    case[16] = case_index
    case[17] = program_counter
    case[18] = operator_id                        # the SHIPPED operator id
    case[19] = shard.row_count                    # this shard's row count
    case[21] = len(activation)                    # preload word count
    case[22] = 0                                  # base in preload.hex
    case[24] = 0                                  # mapped families not admitted

    placement = [
        (input_view.primary_object_id, BANK_INPUT_BASE),
        (weight_view.primary_object_id, 0),
        (output_view.primary_object_id, BANK_OUTPUT_BASE),
    ]
    if len({object_id for object_id, _ in placement}) != len(placement):
        raise BuildError("this operator names one object in two roles")
    for slot in range(MAP_ENTRIES):
        if slot < len(placement):
            case[MAP_BASE + 2 * slot] = placement[slot][0]
            case[MAP_BASE + 2 * slot + 1] = placement[slot][1]
        else:
            case[MAP_BASE + 2 * slot] = 0xFFFFFFFF
            case[MAP_BASE + 2 * slot + 1] = 0

    views = [0] * (VIEW_SLOTS * VIEW_WORDS)

    def put(slot_index: int, slot: int, view_id: int, extent: int, rank: int) -> None:
        base = slot_index * VIEW_WORDS
        views[base + 0] = 1
        views[base + 1] = view_id
        views[base + 2] = slot
        views[base + 3] = extent
        views[base + 4] = 0
        views[base + 5] = 0
        views[base + 6] = 0
        views[base + 7] = rank

    put(0, 0, input_view_id, 1, int(input_view.payload["rank"]))
    put(1, 1, shard_weight_id, shard.row_count, int(weight_view.payload["rank"]))
    put(2, 4, shard_output_id, 1, int(output_view.payload["rank"]))

    (shard_dir / "cases.hex").write_text(scatter.hex_lines(case), encoding="ascii")
    (shard_dir / "views.hex").write_text(scatter.hex_lines(views), encoding="ascii")
    (shard_dir / "descriptors.hex").write_text(
        scatter.hex_lines(image, 1536), encoding="ascii"
    )
    (shard_dir / "index.hex").write_text(
        scatter.hex_lines(list(range(INDEX_WORDS))), encoding="ascii"
    )
    (shard_dir / "source.hex").write_text(
        scatter.hex_lines([0] * SOURCE_WORDS), encoding="ascii"
    )
    (shard_dir / "preload.hex").write_text(
        scatter.hex_lines(list(activation)), encoding="ascii"
    )
    # A refused shard compares nothing, and its expectation image is one word
    # rather than a range the vehicle's store cannot hold.
    (shard_dir / "expected.hex").write_text(
        scatter.hex_lines(list(golden) if admitted else [0]), encoding="ascii"
    )

    # The paged window's manifest: the image IS this operator's own checkpoint
    # segment, so the shard's window base is exactly its first row's byte
    # offset inside the tensor.
    root = Path(target.checkpoint).expanduser()
    path = resolve_path(root, segment.path)
    (shard_dir / "shard_weight_window.txt").write_text(
        f"0 {int(segment.bytes)} {int(segment.offset)} {path}\n", encoding="ascii"
    )
    return {
        "admitted_by_the_bridge_predicate": admitted,
        "expected_fault": case[3],
        "expected_trap_class": case[4],
        "drives_the_shipped_descriptor": drives_the_shipped_descriptor,
        "weight_view": {
            "descriptor_id": weight_view_id,
            "shard_descriptor_id": shard_weight_id,
            "dim0": [int(weight_view.payload["dim0"]), shard.row_count],
        },
        "output_view": {
            "descriptor_id": output_view_id,
            "shard_descriptor_id": shard_output_id,
            "dim1": [int(output_view.payload["dim1"]), shard.row_count],
            "stride0": [int(output_view.payload["stride0"]), shard.row_count],
        },
        "operator": {
            "descriptor_id": operator_id,
            "shard_descriptor_id": shard_operator_id,
            "input_view_1": [weight_view_id, shard_weight_id],
            "output_view_0": [output_view_id, shard_output_id],
        },
        "everything_else_is_the_shipped_record": True,
        "note": (
            "a shard that covers every row of the operator rewrites nothing "
            "and is issued against the shipped descriptor ids themselves"
            if drives_the_shipped_descriptor
            else "the weight view's row count and the output view's row count "
            "and row stride are this shard's; every other field, the numeric "
            "contract digest included, is the shipped record byte for byte"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-class", choices=sorted(STORAGE_CLASSES),
                        required=True)
    parser.add_argument("--pc", type=int, required=True)
    parser.add_argument("--shards", type=int, default=None)
    parser.add_argument("--rows-per-shard", type=int, default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = build(
        args.storage_class, args.pc, args.shards, args.rows_per_shard, args.output
    )
    print(
        f"row-shard vectors: {manifest['operator_key']} "
        f"rows={manifest['declared_output_rows']} "
        f"shards={len(manifest['shards'])} "
        f"macs={manifest['multiply_accumulates']} "
        f"golden={manifest['whole_operator_golden_sha256'][:12]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
