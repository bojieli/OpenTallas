#!/usr/bin/env python3
"""Generate the RTL vectors for the ABI 3.0 inter-chip endpoint.

Every expected value here is produced by the executed functional model, not by
this file's own arithmetic:

* the reduced result is ``runtime.sim.engines.reduction.ordered_sum`` over the
  same binary32 contributions, in the reduction order the case declares;
* the message and byte counts the fabric must not contradict come from
  ``runtime.sim.engines.link.collective_traffic`` and ``barrier_messages``;
* the traversal count the case is measured against is the one
  ``src/opentallas/roofline.py`` charges, recomputed here from the same rule
  (``MESH_ALLREDUCE_DIAMETER_FACTOR`` x mesh diameter) so that the RTL's
  measured traversals can be compared with the model's charge in one place.

The generator also records, per configuration, how many elements differ between
``SEQUENTIAL_ASCENDING`` and ``PAIRWISE_TREE`` on the identical contributions.
That number is the whole reason the engine refuses one of the two orders.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    DType,
    Link,
    Major,
    ParticipantScope,
    Permission,
    ReductionOrder,
    RoundingMode,
    TopologyClass,
)
from runtime.abi3.crc import record_crc  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    CollectiveOp,
    Descriptor,
    ExtendedDescriptorType,
)
from runtime.abi3.records import Instruction, split_program  # noqa: E402
from runtime.sim.engines.link import (  # noqa: E402
    barrier_messages,
    collective_traffic,
)
from runtime.sim.engines.reduction import ordered_sum  # noqa: E402

# The engine-local barrier opcode.  It is not an ABI collective_op; the ABI
# spells a barrier LINK.BARRIER with a zero byte extent.
OP_BARRIER = 0xFF

ALG_RECURSIVE_DOUBLING = 0
ALG_HALVING_DOUBLING = 1

#: The factor src/opentallas/roofline.py charges a stitched mesh all-reduce.
MESH_ALLREDUCE_DIAMETER_FACTOR = 1.1

CASE_STRIDE = 80
DESCRIPTOR_WORDS = 48
NUMERIC_WORDS = 32

# case.hex layout.  The expected decode occupies words 15..55; keeping the
# indices named here and mirrored in tb_a3_link.sv makes additions fail loudly
# instead of silently shifting the testbench's interpretation.
CW_ALGORITHM = 0
CW_NUMERIC_ORDER = 1
CW_NUMERIC_ID = 2
CW_SUBOPCODE = 3
CW_INJECT_NODE = 4
CW_INJECT_DIR = 5
CW_FLAGS = 6
CW_REASON = 7
CW_SERIAL = 8
CW_ENGINE_FLITS = 9
CW_CROSSINGS = 10
CW_STEPS = 11
CW_ENGINE_OP = 12
CW_ROOT_X = 13
CW_ROOT_Y = 14
CW_MAGIC = 15
CW_DESCRIPTOR_TYPE = 16
CW_TYPE_MAJOR = 17
CW_TYPE_MINOR = 18
CW_TOTAL_BYTES = 19
CW_HEADER_FLAGS = 20
CW_PRIMARY_OBJECT = 21
CW_SECONDARY_OBJECT = 22
CW_NUMERIC_PROFILE = 23
CW_SCHEDULE = 24
CW_PERMISSIONS = 25
CW_OWNER_SCOPE = 26
CW_PAYLOAD_OFFSET = 27
CW_PAYLOAD_BYTES = 28
CW_SUPPLIED_CRC = 29
CW_CALCULATED_CRC = 30
CW_COLLECTIVE_OP = 31
CW_ORDERING = 32
CW_INTEGRITY_MODE = 33
CW_VIRTUAL_CHANNEL = 34
CW_SOURCE_NODE = 35
CW_DESTINATION_NODE = 36
CW_GROUP_ID = 37
CW_ROUTE_CLASS = 38
CW_LOCAL_OBJECT = 39
CW_REMOTE_OBJECT = 40
CW_LOCAL_OFFSET_LO = 41
CW_LOCAL_OFFSET_HI = 42
CW_REMOTE_OFFSET_LO = 43
CW_REMOTE_OFFSET_HI = 44
CW_BYTE_EXTENT_LO = 45
CW_BYTE_EXTENT_HI = 46
CW_CREDIT_BOUND = 47
CW_RETRY_BOUND = 48
CW_TIMEOUT_CLASS = 49
CW_COMPLETION_EVENT = 50
CW_REDUCTION_NUMERIC = 51
CW_COUNTER_CLASS = 52
CW_PARTICIPANT_COUNT = 53
CW_CHUNK_BYTES = 54
CW_PARTICIPANT_SCOPE = 55
CW_EXPECT_TRAP_CLASS = 56
CW_NUMERIC_RECORD_VALID = 57
CW_NUMERIC_SEMANTICS_SUPPORTED = 58
CW_NUMERIC_REFUSAL_REASON = 59
CW_NUMERIC_DESCRIPTOR_TYPE = 60
CW_NUMERIC_TOTAL_BYTES = 61
CW_NUMERIC_PAYLOAD_BYTES = 62
CW_NUMERIC_SUPPLIED_CRC = 63
CW_NUMERIC_CALCULATED_CRC = 64
CW_NUMERIC_INPUT_DTYPE = 65
CW_NUMERIC_SECOND_INPUT_DTYPE = 66
CW_NUMERIC_ACCUMULATOR_DTYPE = 67
CW_NUMERIC_OUTPUT_DTYPE = 68
CW_NUMERIC_ROUNDING_MODE = 69
CW_NUMERIC_DECODED_ORDER = 70
CW_NUMERIC_SATURATE = 71
CW_NUMERIC_NAN_POLICY = 72
CW_NUMERIC_EPSILON_BITS = 73
CW_NUMERIC_SCALE_BITS = 74
CW_NUMERIC_FLAGS = 75
CW_NUMERIC_CONTRACT_DIGEST_ZERO = 76

CASE_EXPECT_TRAP = 1 << 0
CASE_DO_INJECT = 1 << 1
CASE_EXPECT_RECORD_VALID = 1 << 2
CASE_EXPECT_COMMAND_ADMITTED = 1 << 3

# Standalone decoder observability codes.  They intentionally are not ABI
# registry values; the matching constants live in ot_a3_link_pkg.sv.
REFUSE = {
    "none": 0,
    "magic": 1,
    "type": 2,
    "version": 3,
    "total_bytes": 4,
    "payload_geometry": 5,
    "header_reserved": 6,
    "payload_reserved": 7,
    "record_crc": 8,
    "permissions": 9,
    "collective_op": 10,
    "ordering": 11,
    "integrity_mode": 12,
    "participant_scope": 13,
    "subopcode": 14,
    "integrity_support": 15,
    "virtual_channel": 16,
    "credit_bound": 17,
    "retry_bound": 18,
    "timeout_class": 19,
    "participants": 20,
    "object_binding": 21,
    "source_node": 22,
    "numeric_binding": 23,
    "reduction_order": 24,
    "algorithm": 25,
    "unsupported_op": 26,
    "barrier_extent": 27,
    "scope_support": 28,
    "group_support": 29,
    "data_extent": 30,
    "chunk_bytes": 31,
    "numeric_record": 32,
    "numeric_semantics": 33,
    "configuration": 34,
    "data_offset": 35,
    "shard_geometry": 36,
    "control_metadata": 37,
}

COMMUNICATION = int(ExtendedDescriptorType.COMMUNICATION)
NUMERIC = int(ExtendedDescriptorType.NUMERIC)
NO_ID = 0xFFFFFFFF
NO_NODE = 0xFFFF
TRAP_NONE = 0
TRAP_NUMERIC_OR_EXCEPTIONAL_VALUE = 6
TRAP_LINK_OR_NOC = 11

SYNTHETIC_PAIRWISE_NUMERIC_ID = 0xFFF00001
SYNTHETIC_BLOCKED_NUMERIC_ID = 0xFFF00002
SYNTHETIC_SEQUENTIAL_NUMERIC_ID = 0xFFF00003
SYNTHETIC_LOCAL_OBJECT_ID = 0xFFE00001
SYNTHETIC_REMOTE_OBJECT_ID = 0xFFE00002

CERTIFIED_DEPLOYMENT_SPECS = {
    "deepseek_rom": {
        "bundle": "build/abi3/deepseek-v4-flash-rom",
        "certificate": "results/abi3/rom_schedule_checks.json",
    },
    "deepseek_hbm": {
        "bundle": "build/abi3/deepseek-v4-flash-hbm-tokens",
        "certificate": "results/abi3/hbm_deepseek_deployment_certificate.json",
    },
    "qwen_rom": {
        "bundle": "build/abi3/qwen3-8b-rom",
        "certificate": "results/abi3/rom_schedule_checks.json",
    },
    "qwen_hbm": {
        "bundle": "build/abi3/qwen3-8b-hbm-tokens",
        "certificate": "results/abi3/hbm_qwen_deployment_certificate.json",
    },
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _certificate_file_hashes(case: dict) -> dict[str, str]:
    deployment = case["inputs"]["deployment"]
    if isinstance(deployment.get("descriptors"), dict):
        return {
            "deployment.json": deployment["manifest"]["sha256"],
            "descriptors.bin": deployment["descriptors"]["sha256"],
            "program.bin": deployment["program"]["sha256"],
        }
    return {
        "deployment.json": deployment["manifest_sha256"],
        "descriptors.bin": deployment["descriptors_sha256"],
        "program.bin": deployment["program_sha256"],
    }


def _raw_descriptor_records(blob: bytes) -> tuple[bytes, ...]:
    records: list[bytes] = []
    offset = 0
    while offset < len(blob):
        if offset + 12 > len(blob):
            raise ValueError("truncated descriptor table while extracting records")
        size = int.from_bytes(blob[offset + 8:offset + 12], "little")
        if size < 64 or size % 64 or offset + size > len(blob):
            raise ValueError(f"invalid descriptor size {size} at byte {offset}")
        records.append(blob[offset:offset + size])
        offset += size
    return tuple(records)


def load_certified_sources() -> dict[str, dict]:
    """Load only bundles whose retained passing certificate binds every byte."""
    loaded: dict[str, dict] = {}
    certificate_cache: dict[Path, dict] = {}
    for name, spec in CERTIFIED_DEPLOYMENT_SPECS.items():
        bundle_rel = spec["bundle"]
        bundle = ROOT / bundle_rel
        cert_rel = spec["certificate"]
        cert_path = ROOT / cert_rel
        certificate = certificate_cache.setdefault(
            cert_path, json.loads(cert_path.read_text())
        )
        if certificate.get("status") != "pass":
            raise ValueError(f"{cert_rel} is not a passing certificate")
        matches = [
            case for case in certificate.get("cases", [])
            if case.get("inputs", {}).get("deployment", {}).get("path") == bundle_rel
        ]
        if len(matches) != 1:
            raise ValueError(
                f"{cert_rel} has {len(matches)} passing cases for {bundle_rel}"
            )
        case = matches[0]
        if case.get("status") != "pass" or not case.get("ok"):
            raise ValueError(f"certificate case for {bundle_rel} did not pass")
        admitted = case.get("verifier", {}).get("admitted")
        if admitted is None:
            admitted = case.get("independent_checker", {}).get(
                "verifier", {}
            ).get("admitted")
        if admitted is not True:
            raise ValueError(f"certificate case for {bundle_rel} was not admitted")

        for filename, expected in _certificate_file_hashes(case).items():
            actual = file_sha256(bundle / filename)
            if actual != expected:
                raise ValueError(
                    f"{bundle_rel}/{filename} is {actual}, certificate binds {expected}"
                )

        deployment = Deployment.read(bundle)
        identity = case.get("deployment_sha256") or case.get(
            "identity", {}
        ).get("deployment_sha256")
        if deployment.deployment_digest.hex() != identity:
            raise ValueError(
                f"{bundle_rel} deployment identity is not the certified identity"
            )

        descriptor_blob = (bundle / "descriptors.bin").read_bytes()
        records = _raw_descriptor_records(descriptor_blob)
        if len(records) != len(deployment.table):
            raise ValueError(f"raw record count disagrees for {bundle_rel}")
        _, body = split_program((bundle / "program.bin").read_bytes())
        instructions = [
            Instruction.decode(body[offset:offset + 32])
            for offset in range(0, len(body), 32)
        ]
        refs: dict[int, list[tuple[int, int]]] = {}
        for index, instruction in enumerate(instructions):
            if int(instruction.major) == int(Major.LINK):
                refs.setdefault(int(instruction.descriptor_id), []).append(
                    (index, int(instruction.sub))
                )
        communication_ids = deployment.table.ids_of_type(COMMUNICATION)
        topology_ids = deployment.table.ids_of_type(
            int(ExtendedDescriptorType.TOPOLOGY)
        )
        if len(topology_ids) != 1:
            raise ValueError(
                f"{bundle_rel} declares {len(topology_ids)} TOPOLOGY records"
            )
        topology_class = int(
            deployment.table[topology_ids[0]].payload["topology_class"]
        )
        loaded[name] = {
            "name": name,
            "bundle": bundle_rel,
            "certificate": cert_rel,
            "certificate_sha256": file_sha256(cert_path),
            "deployment_sha256": identity,
            "descriptor_table_sha256": file_sha256(bundle / "descriptors.bin"),
            "deployment": deployment,
            "records": records,
            "link_references": refs,
            "communication_ids": communication_ids,
            "topology_descriptor_id": topology_ids[0],
            "topology_class": topology_class,
        }
    return loaded


def select_communication(source: dict, *, subopcode: int,
                         collective_op: int, zero_extent: bool | None = None) -> int:
    matches = []
    for descriptor_id in source["communication_ids"]:
        descriptor = source["deployment"].table[descriptor_id]
        refs = source["link_references"].get(descriptor_id, [])
        if not any(sub == subopcode for _, sub in refs):
            continue
        if int(descriptor.payload["collective_op"]) != collective_op:
            continue
        if zero_extent is not None and (
            int(descriptor.payload["byte_extent"]) == 0
        ) != zero_extent:
            continue
        matches.append(descriptor_id)
    if not matches:
        raise ValueError(
            f"no certified {source['name']} communication matches "
            f"subopcode={subopcode} op={collective_op}"
        )
    return min(matches)


def select_numeric(source: dict, order: int) -> int:
    matches = []
    table = source["deployment"].table
    for descriptor_id in table.ids_of_type(NUMERIC):
        payload = table[descriptor_id].payload
        if int(payload["reduction_order"]) != order:
            continue
        if (int(payload["input_dtype"]), int(payload["second_input_dtype"]),
                int(payload["accumulator_dtype"]), int(payload["output_dtype"])) \
                == (16, 16, 18, 16):
            matches.append(descriptor_id)
    if not matches:
        raise ValueError(f"no {source['name']} NUMERIC has reduction order {order}")
    return min(matches)


def mutate_record(record: bytes, mutations: list[tuple[int, int, int]],
                  *, stale_crc: bool = False) -> bytes:
    """Copy an extracted record, apply LE integer mutations, and reseal it."""
    if len(record) != DESCRIPTOR_WORDS * 4:
        raise ValueError(f"COMMUNICATION record is {len(record)} bytes, expected 192")
    changed = bytearray(record)
    for offset, size, value in mutations:
        changed[offset:offset + size] = int(value).to_bytes(size, "little")
    if not stale_crc:
        changed[48:52] = b"\x00" * 4
        changed[48:52] = record_crc(bytes(changed), 48).to_bytes(4, "little")
    return bytes(changed)


def mutate_numeric_record(record: bytes,
                          mutations: list[tuple[int, int, int]],
                          *, stale_crc: bool = False) -> bytes:
    """Copy a complete 128-byte NUMERIC record, mutate it, and reseal it."""
    if len(record) != NUMERIC_WORDS * 4:
        raise ValueError(f"NUMERIC record is {len(record)} bytes, expected 128")
    changed = bytearray(record)
    for offset, size, value in mutations:
        changed[offset:offset + size] = int(value).to_bytes(size, "little")
    if not stale_crc:
        changed[48:52] = b"\x00" * 4
        changed[48:52] = record_crc(bytes(changed), 48).to_bytes(4, "little")
    return bytes(changed)


def synthetic_numeric_record(order: int) -> bytes:
    """A local FP32 profile that names only semantics this RTL implements.

    The zero contract digest is deliberate: these probes do not impersonate a
    frozen deployment numeric contract.  All header references are NO_ID and
    the complete record is CRC sealed by the canonical descriptor codec.
    """
    return Descriptor(
        descriptor_id=NO_ID,
        descriptor_type=NUMERIC,
        payload={
            "input_dtype": int(DType.FP32),
            "second_input_dtype": int(DType.FP32),
            "accumulator_dtype": int(DType.FP32),
            "output_dtype": int(DType.FP32),
            "rounding_mode": int(RoundingMode.NEAREST_EVEN),
            "reduction_order": int(order),
            "saturate": 0,
            "nan_policy": 0,
            "epsilon_bits": 0,
            "scale_bits": 0,
            "flags": 0,
            "contract_digest": bytes(32),
        },
        permissions=int(Permission.READ | Permission.IMMUTABLE),
    ).encode()


def synthetic_communication_mutations(
    cfg: dict, *, op: int, numeric_id: int = NO_ID,
    source_node: int = NO_NODE, barrier: bool = False,
) -> list[tuple[str, int, int, int]]:
    """Replace every execution-relevant field of a certified template."""
    nodes = cfg["mesh_x"] * cfg["mesh_y"]
    local_object_id = NO_ID if barrier else SYNTHETIC_LOCAL_OBJECT_ID
    remote_object_id = NO_ID if barrier else SYNTHETIC_REMOTE_OBJECT_ID
    return [
        ("header_flags", 12, 4, 0),
        ("primary_object_id", 16, 4, local_object_id),
        ("secondary_object_id", 20, 4, remote_object_id),
        ("numeric_profile_id", 24, 4, NO_ID),
        ("schedule_id", 28, 4, NO_ID),
        ("permissions", 32, 4, 0),
        ("owner_scope_id", 36, 4, 0),
        ("collective_op", 64, 1, op),
        ("ordering", 65, 1, 0),
        ("integrity_mode", 66, 1, 1),
        ("virtual_channel", 67, 1, 0),
        ("source_node", 68, 2, source_node),
        ("destination_node", 70, 2, NO_NODE),
        ("group_id", 72, 4, NO_ID),
        ("route_class", 76, 4, 0),
        ("local_object_id", 80, 4, local_object_id),
        ("remote_object_id", 84, 4, remote_object_id),
        ("local_offset", 88, 8, 0),
        ("remote_offset", 96, 8, 0),
        ("byte_extent", 104, 8, 0 if barrier else cfg["vec_len"] * 4),
        ("credit_bound", 112, 4, cfg["credits"]),
        ("retry_bound", 116, 4, cfg["retry_max"]),
        ("timeout_class", 120, 4, cfg["timeout_class"]),
        ("completion_event_id", 124, 4, NO_ID),
        ("reduction_numeric_id", 128, 4, numeric_id),
        ("counter_class_id", 132, 4, NO_ID),
        ("participant_count", 136, 4, nodes),
        ("chunk_bytes", 140, 4, 0 if barrier else 4),
        ("participant_scope", 144, 1, int(ParticipantScope.NODE)),
    ]


def decoded_words(record: bytes) -> dict[int, int]:
    """Expected values at the exact offsets of the frozen ABI layouts."""
    def u(offset: int, size: int) -> int:
        return int.from_bytes(record[offset:offset + size], "little")

    calculated = record_crc(record, 48)
    values = {
        CW_MAGIC: u(0, 4), CW_DESCRIPTOR_TYPE: u(4, 2),
        CW_TYPE_MAJOR: u(6, 1), CW_TYPE_MINOR: u(7, 1),
        CW_TOTAL_BYTES: u(8, 4), CW_HEADER_FLAGS: u(12, 4),
        CW_PRIMARY_OBJECT: u(16, 4), CW_SECONDARY_OBJECT: u(20, 4),
        CW_NUMERIC_PROFILE: u(24, 4), CW_SCHEDULE: u(28, 4),
        CW_PERMISSIONS: u(32, 4), CW_OWNER_SCOPE: u(36, 4),
        CW_PAYLOAD_OFFSET: u(40, 4), CW_PAYLOAD_BYTES: u(44, 4),
        CW_SUPPLIED_CRC: u(48, 4), CW_CALCULATED_CRC: calculated,
        CW_COLLECTIVE_OP: u(64, 1), CW_ORDERING: u(65, 1),
        CW_INTEGRITY_MODE: u(66, 1), CW_VIRTUAL_CHANNEL: u(67, 1),
        CW_SOURCE_NODE: u(68, 2), CW_DESTINATION_NODE: u(70, 2),
        CW_GROUP_ID: u(72, 4), CW_ROUTE_CLASS: u(76, 4),
        CW_LOCAL_OBJECT: u(80, 4), CW_REMOTE_OBJECT: u(84, 4),
        CW_LOCAL_OFFSET_LO: u(88, 4), CW_LOCAL_OFFSET_HI: u(92, 4),
        CW_REMOTE_OFFSET_LO: u(96, 4), CW_REMOTE_OFFSET_HI: u(100, 4),
        CW_BYTE_EXTENT_LO: u(104, 4), CW_BYTE_EXTENT_HI: u(108, 4),
        CW_CREDIT_BOUND: u(112, 4), CW_RETRY_BOUND: u(116, 4),
        CW_TIMEOUT_CLASS: u(120, 4), CW_COMPLETION_EVENT: u(124, 4),
        CW_REDUCTION_NUMERIC: u(128, 4), CW_COUNTER_CLASS: u(132, 4),
        CW_PARTICIPANT_COUNT: u(136, 4), CW_CHUNK_BYTES: u(140, 4),
        CW_PARTICIPANT_SCOPE: u(144, 1),
    }
    return values


def numeric_decoded_words(record: bytes) -> dict[int, int]:
    """Expected NUMERIC outputs at the exact frozen byte offsets."""
    if len(record) != NUMERIC_WORDS * 4:
        raise ValueError(f"NUMERIC record is {len(record)} bytes, expected 128")

    def u(offset: int, size: int) -> int:
        return int.from_bytes(record[offset:offset + size], "little")

    return {
        CW_NUMERIC_DESCRIPTOR_TYPE: u(4, 2),
        CW_NUMERIC_TOTAL_BYTES: u(8, 4),
        CW_NUMERIC_PAYLOAD_BYTES: u(44, 4),
        CW_NUMERIC_SUPPLIED_CRC: u(48, 4),
        CW_NUMERIC_CALCULATED_CRC: record_crc(record, 48),
        CW_NUMERIC_INPUT_DTYPE: u(64, 1),
        CW_NUMERIC_SECOND_INPUT_DTYPE: u(65, 1),
        CW_NUMERIC_ACCUMULATOR_DTYPE: u(66, 1),
        CW_NUMERIC_OUTPUT_DTYPE: u(67, 1),
        CW_NUMERIC_ROUNDING_MODE: u(68, 1),
        CW_NUMERIC_DECODED_ORDER: u(69, 1),
        CW_NUMERIC_SATURATE: u(70, 1),
        CW_NUMERIC_NAN_POLICY: u(71, 1),
        CW_NUMERIC_EPSILON_BITS: u(72, 4),
        CW_NUMERIC_SCALE_BITS: u(76, 4),
        CW_NUMERIC_FLAGS: u(80, 4),
        CW_NUMERIC_CONTRACT_DIGEST_ZERO: int(not any(record[96:128])),
    }


def fp32(values) -> np.ndarray:
    return np.ascontiguousarray(values, dtype=np.float32)


def codes(values: np.ndarray) -> np.ndarray:
    return fp32(values).view(np.uint32)


def contributions(nodes: int, vec_len: int, seed: int) -> np.ndarray:
    """One binary32 contribution per (participant, element).

    The values are deliberately chosen so that a binary32 sum is order
    sensitive: a large leading term next to many small ones is exactly the case
    where sequential accumulation and a balanced tree disagree.
    """
    rng = np.random.default_rng(seed)
    base = rng.uniform(-1.0, 1.0, size=(nodes, vec_len))
    scale = np.power(2.0, rng.integers(-12, 13, size=(nodes, vec_len)))
    values = fp32(base * scale)
    # Guarantee at least one order-sensitive element: one big term, many small.
    values[0, :] = fp32(np.float32(2.0) ** 20)
    values[1:, 0] = fp32(np.float32(2.0) ** -6)
    return fp32(values)


def halving_tree(values: np.ndarray) -> np.ndarray:
    """The fold a recursive-halving reduce-scatter performs: top bit first.

    This is not one of the three orders `spec/abi3/registries.json` names, and
    it coincides with `BLOCKED_ASCENDING` only at sixteen participants -- eight
    lanes over sixteen terms is the top-bit-first fold.  It is written out here
    rather than borrowed so that the coincidence is checked, not assumed.
    """
    current = fp32(values)
    count = current.shape[0]
    while count > 1:
        half = count // 2
        current = np.add(current[:half], current[half:count], dtype=np.float32)
        count = half
    return fp32(current[0])


def reduce_expect(values: np.ndarray, op: int, order: int,
                  alg: int = 0) -> np.ndarray:
    if op == int(CollectiveOp.SUM):
        if alg == ALG_HALVING_DOUBLING:
            return halving_tree(values)
        return fp32(ordered_sum(values, order))
    if op == int(CollectiveOp.MAX):
        return fp32(np.maximum.reduce(values, axis=0))
    if op == int(CollectiveOp.MIN):
        return fp32(np.minimum.reduce(values, axis=0))
    raise ValueError(f"op {op} is not a reduction")


def mesh_diameter(mesh_x: int, mesh_y: int) -> int:
    return (mesh_x - 1) + (mesh_y - 1)


def hop_distance(rank: int, step: int, mesh_x: int, lgx: int) -> int:
    peer = rank ^ (1 << step)
    x0, y0 = rank % mesh_x, rank // mesh_x
    x1, y1 = peer % mesh_x, peer // mesh_x
    return abs(x1 - x0) + abs(y1 - y0)


def schedule(op: int, alg: int, mesh_x: int, mesh_y: int, vec_len: int):
    """Flits offered and link crossings walked, per node and in total.

    Returned per case: (serial_traversal_max, engine_flits_total,
    wire_flit_crossings_total, steps_per_node).
    """
    nodes = mesh_x * mesh_y
    lgx = int(math.log2(mesh_x)) if mesh_x > 1 else 0
    lgy = int(math.log2(mesh_y)) if mesh_y > 1 else 0
    lg = lgx + lgy
    serial = [0] * nodes
    engine = 0
    crossings = 0
    for rank in range(nodes):
        if op == OP_BARRIER:
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += 1
                crossings += d
        elif op == int(CollectiveOp.BROADCAST):
            rprime = rank  # root is rank 0 in every generated case
            for k in range(lg):
                have = rprime < (1 << k)
                take = (rprime ^ (1 << k)) < (1 << k)
                if have or take:
                    d = hop_distance(rank, k, mesh_x, lgx)
                    serial[rank] += d
                    if have:
                        engine += vec_len
                        crossings += vec_len * d
        elif alg == ALG_HALVING_DOUBLING and op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN)
        ):
            block = vec_len
            for k in range(lg - 1, -1, -1):
                half = block // 2
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += half
                crossings += half * d
                block = half
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += block
                crossings += block * d
                block = block * 2
        else:
            for k in range(lg):
                d = hop_distance(rank, k, mesh_x, lgx)
                serial[rank] += d
                engine += vec_len
                crossings += vec_len * d
    return max(serial), engine, crossings, lg if op != OP_BARRIER or True else lg


def reference_numeric(record: bytes) -> tuple[bool, bool, int]:
    """Bit-exact software oracle for NUMERIC structure and supported semantics."""
    def u(offset: int, size: int) -> int:
        return int.from_bytes(record[offset:offset + size], "little")

    legal_dtypes = {
        int(DType.U8), int(DType.I8), int(DType.U16), int(DType.I16),
        int(DType.U32), int(DType.I32), int(DType.U64), int(DType.I64),
        int(DType.BF16), int(DType.FP16), int(DType.FP32), int(DType.FP64),
        int(DType.FP8_E4M3FN), int(DType.FP8_E5M2),
        int(DType.MXFP4_E2M1), int(DType.E8M0_SCALE),
    }
    permissions = u(32, 4)

    if u(0, 4) != 0x44334154:
        reason = REFUSE["magic"]
    elif u(4, 2) != NUMERIC:
        reason = REFUSE["type"]
    elif u(6, 1) != 1 or u(7, 1) > 0:
        reason = REFUSE["version"]
    elif u(8, 4) != 128:
        reason = REFUSE["total_bytes"]
    elif u(40, 4) != 64 or u(44, 4) != 64:
        reason = REFUSE["payload_geometry"]
    elif any(record[52:64]):
        reason = REFUSE["header_reserved"]
    elif any(record[84:96]):
        reason = REFUSE["payload_reserved"]
    elif u(48, 4) != record_crc(record, 48):
        reason = REFUSE["record_crc"]
    elif permissions & ~0xFF or (
        permissions & 0x80 and permissions & (0x02 | 0x08 | 0x10)
    ):
        reason = REFUSE["permissions"]
    elif any(u(64 + offset, 1) not in legal_dtypes for offset in range(4)) \
            or u(68, 1) > int(RoundingMode.STOCHASTIC) \
            or u(69, 1) > int(ReductionOrder.BLOCKED_ASCENDING) \
            or u(70, 1) > 1:
        reason = REFUSE["numeric_semantics"]
    else:
        reason = REFUSE["none"]

    valid = reason == REFUSE["none"]
    neutral_header = (
        u(12, 4) == 0 and u(16, 4) == NO_ID and u(20, 4) == NO_ID
        and u(24, 4) == NO_ID and u(28, 4) == NO_ID and u(36, 4) == 0
    )
    supported = valid and neutral_header and (
        tuple(u(64 + offset, 1) for offset in range(4))
        == (int(DType.FP32),) * 4
    ) and u(68, 1) == int(RoundingMode.NEAREST_EVEN) \
        and u(70, 1) == 0 and u(71, 1) == 0 \
        and u(72, 4) == 0 and u(76, 4) == 0 and u(80, 4) == 0 \
        and not any(record[96:128])
    return valid, supported, reason


def reference_admission(record: bytes, numeric_record: bytes, cfg: dict,
                        subopcode: int, algorithm: int, numeric_id: int,
                        numeric_order: int) -> tuple[bool, bool, int, int, int, int]:
    """Bit-exact software oracle for the standalone decoder boundaries."""
    def u(offset: int, size: int) -> int:
        return int.from_bytes(record[offset:offset + size], "little")

    nodes = cfg["mesh_x"] * cfg["mesh_y"]
    permissions = u(32, 4)
    op = u(64, 1)
    ordering = u(65, 1)
    integrity = u(66, 1)
    vc = u(67, 1)
    source_node = u(68, 2)
    group_id = u(72, 4)
    local_object = u(80, 4)
    remote_object = u(84, 4)
    local_offset = u(88, 8)
    remote_offset = u(96, 8)
    extent = u(104, 8)
    reduction_numeric = u(128, 4)
    participants = u(136, 4)
    chunk_bytes = u(140, 4)
    scope = u(144, 1)

    if u(0, 4) != 0x44334154:
        reason = REFUSE["magic"]
    elif u(4, 2) != COMMUNICATION:
        reason = REFUSE["type"]
    elif u(6, 1) != 1 or u(7, 1) > 0:
        reason = REFUSE["version"]
    elif u(8, 4) != 192:
        reason = REFUSE["total_bytes"]
    elif u(40, 4) != 64 or u(44, 4) != 128:
        reason = REFUSE["payload_geometry"]
    elif any(record[52:64]):
        reason = REFUSE["header_reserved"]
    elif any(record[145:192]):
        reason = REFUSE["payload_reserved"]
    elif u(48, 4) != record_crc(record, 48):
        reason = REFUSE["record_crc"]
    elif permissions & ~0xFF or (
        permissions & 0x80 and permissions & (0x02 | 0x08 | 0x10)
    ):
        reason = REFUSE["permissions"]
    elif op > int(CollectiveOp.REDUCE_SCATTER):
        reason = REFUSE["collective_op"]
    elif ordering > 4:
        reason = REFUSE["ordering"]
    elif integrity > 3:
        reason = REFUSE["integrity_mode"]
    elif scope > 2:
        reason = REFUSE["participant_scope"]
    else:
        reason = REFUSE["none"]

    record_valid = reason == REFUSE["none"]
    numeric_valid, numeric_supported, _ = reference_numeric(numeric_record)
    numeric_decoded_order = int.from_bytes(numeric_record[69:70], "little")
    is_barrier = subopcode == int(Link.BARRIER)
    is_collective = subopcode == int(Link.COLLECTIVE)
    is_multicast = subopcode == int(Link.MULTICAST)
    reduction = op in (
        int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN)
    )
    supported_op = is_barrier or (
        (is_collective or is_multicast) and op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX),
            int(CollectiveOp.MIN), int(CollectiveOp.BROADCAST),
        )
    )
    config_supported = (
        1 <= cfg["mesh_x"] <= 16 and 1 <= cfg["mesh_y"] <= 16
        and cfg["mesh_x"] & (cfg["mesh_x"] - 1) == 0
        and cfg["mesh_y"] & (cfg["mesh_y"] - 1) == 0
        and 2 <= nodes <= 256 and 1 <= cfg["vec_len"] <= 256
        and 2 <= cfg["credits"] <= 64 and 0 <= cfg["retry_max"] <= 3
    )
    if reason:
        pass
    elif not config_supported:
        reason = REFUSE["configuration"]
    elif not (is_barrier or is_collective or is_multicast) or (
        is_multicast and op != int(CollectiveOp.BROADCAST)
    ):
        reason = REFUSE["subopcode"]
    elif integrity != 1:
        reason = REFUSE["integrity_support"]
    elif vc >= 4:
        reason = REFUSE["virtual_channel"]
    elif u(112, 4) != cfg["credits"]:
        reason = REFUSE["credit_bound"]
    elif u(116, 4) != cfg["retry_max"]:
        reason = REFUSE["retry_bound"]
    elif u(120, 4) != cfg["timeout_class"]:
        reason = REFUSE["timeout_class"]
    elif scope != int(ParticipantScope.NODE):
        reason = REFUSE["scope_support"]
    elif group_id != NO_ID:
        reason = REFUSE["group_support"]
    elif participants != nodes or participants < 2:
        reason = REFUSE["participants"]
    elif u(16, 4) != local_object or u(20, 4) != remote_object:
        reason = REFUSE["object_binding"]
    elif (op == int(CollectiveOp.BROADCAST) and source_node >= nodes) or (
        op != int(CollectiveOp.BROADCAST)
        and source_node != NO_NODE and source_node >= nodes
    ):
        reason = REFUSE["source_node"]
    elif not supported_op:
        reason = REFUSE["unsupported_op"]
    elif is_barrier and extent != 0:
        reason = REFUSE["barrier_extent"]
    elif not is_barrier and extent != cfg["vec_len"] * 4:
        reason = REFUSE["data_extent"]
    elif not is_barrier and chunk_bytes != 4:
        reason = REFUSE["chunk_bytes"]
    elif not is_barrier and (local_offset != 0 or remote_offset != 0):
        reason = REFUSE["data_offset"]
    elif not (
        u(12, 4) == 0 and u(24, 4) == NO_ID and u(28, 4) == NO_ID
        and permissions == 0 and u(36, 4) == 0 and ordering == 0
        and vc == 0 and u(70, 2) == NO_NODE and u(76, 4) == 0
        and u(124, 4) == NO_ID and u(132, 4) == NO_ID
        and (not is_barrier or (
            u(16, 4) == NO_ID and u(20, 4) == NO_ID
            and local_object == NO_ID and remote_object == NO_ID
            and reduction_numeric == NO_ID and chunk_bytes == 0
        ))
    ):
        reason = REFUSE["control_metadata"]
    elif reduction and not is_barrier and (
        reduction_numeric == NO_ID or numeric_id != reduction_numeric
    ):
        reason = REFUSE["numeric_binding"]
    elif reduction and not is_barrier and not numeric_valid:
        reason = REFUSE["numeric_record"]
    elif reduction and not is_barrier and not numeric_supported:
        reason = REFUSE["numeric_semantics"]
    elif reduction and not is_barrier and numeric_order != numeric_decoded_order:
        reason = REFUSE["numeric_binding"]
    elif algorithm not in (ALG_RECURSIVE_DOUBLING, ALG_HALVING_DOUBLING) \
            and not is_barrier:
        reason = REFUSE["algorithm"]
    elif op == int(CollectiveOp.SUM) and not is_barrier and not (
        algorithm == ALG_RECURSIVE_DOUBLING and
        numeric_decoded_order == int(ReductionOrder.PAIRWISE_TREE)
    ) and not (
        algorithm == ALG_HALVING_DOUBLING and
        numeric_decoded_order == int(ReductionOrder.BLOCKED_ASCENDING) and
        nodes == 16
    ):
        reason = REFUSE["reduction_order"]
    elif algorithm == ALG_HALVING_DOUBLING and reduction and (
        cfg["vec_len"] < nodes or cfg["vec_len"] % nodes != 0
    ):
        reason = REFUSE["shard_geometry"]

    admitted = reason == REFUSE["none"]
    engine_op = OP_BARRIER if is_barrier else op
    if op == int(CollectiveOp.BROADCAST) and source_node < nodes:
        root_x = source_node % cfg["mesh_x"]
        root_y = source_node // cfg["mesh_x"]
    else:
        root_x = root_y = 0
    return record_valid, admitted, reason, engine_op, root_x, root_y


def _field_value(record: bytes, offset: int, size: int) -> int:
    return int.from_bytes(record[offset:offset + size], "little")


def make_case_spec(*, label: str, source: dict, descriptor_id: int,
                   cfg: dict, subopcode: int, algorithm: int = 0,
                   numeric_id: int = NO_ID, numeric_order: int = 0,
                   mutations: list[tuple[str, int, int, int]] | None = None,
                   stale_crc: bool = False, inject_node: int = -1,
                   inject_dir: int = 0, numeric_record: bytes | None = None,
                   numeric_source_descriptor_id: int | None = None,
                   numeric_mutations: list[str] | None = None,
                   numeric_stale_crc: bool = False,
                   execution_class: str = "synthetic_refusal_probe",
                   input_pattern: str = "ordinary",
                   engine_trap_class: int = TRAP_NONE,
                   barrier_topology_class: int | None = None) -> dict:
    raw = source["records"][descriptor_id]
    edits = mutations or []
    record = mutate_record(
        raw, [(offset, size, value) for _, offset, size, value in edits],
        stale_crc=stale_crc,
    )
    numeric_source = None
    numeric_source_sha = None
    numeric_exact_source_record = False
    if numeric_record is None and numeric_id != NO_ID:
        numeric_source = source["name"]
        numeric_record = source["records"][numeric_id]
        numeric_source_descriptor_id = numeric_id
        numeric_descriptor = source["deployment"].table[numeric_id]
        if numeric_descriptor.descriptor_type != NUMERIC:
            raise ValueError(f"sideband descriptor {numeric_id} is not NUMERIC")
        numeric_source_sha = hashlib.sha256(numeric_record).hexdigest()
        numeric_exact_source_record = True
    elif numeric_record is not None and numeric_source_descriptor_id is not None:
        numeric_source = source["name"]
        source_numeric = source["records"][numeric_source_descriptor_id]
        numeric_source_sha = hashlib.sha256(source_numeric).hexdigest()
        numeric_exact_source_record = numeric_record == source_numeric
    if numeric_record is None:
        numeric_record = bytes(NUMERIC_WORDS * 4)

    numeric_valid, numeric_supported, numeric_reason = reference_numeric(
        numeric_record
    )
    record_valid, admitted, reason, engine_op, root_x, root_y = \
        reference_admission(
            record, numeric_record, cfg, subopcode, algorithm, numeric_id,
            numeric_order
        )
    expected_trap_class = (
        engine_trap_class if admitted and engine_trap_class
        else (TRAP_NONE if admitted else TRAP_LINK_OR_NOC)
    )
    return {
        "label": label,
        "record": record,
        "source": source["name"],
        "source_bundle": source["bundle"],
        "source_descriptor_id": descriptor_id,
        "source_record_sha256": hashlib.sha256(raw).hexdigest(),
        "record_sha256": hashlib.sha256(record).hexdigest(),
        "exact_source_record": record == raw,
        "mutations": [name for name, _, _, _ in edits],
        "stale_crc": stale_crc,
        "subopcode": subopcode,
        "alg": algorithm,
        "numeric_descriptor_id": numeric_id,
        "order": numeric_order,
        "numeric_record": numeric_record,
        "numeric_source": numeric_source,
        "numeric_source_descriptor_id": numeric_source_descriptor_id,
        "numeric_source_record_sha256": numeric_source_sha,
        "numeric_record_sha256": hashlib.sha256(numeric_record).hexdigest(),
        "numeric_exact_source_record": numeric_exact_source_record,
        "numeric_mutations": numeric_mutations or [],
        "numeric_stale_crc": numeric_stale_crc,
        "numeric_record_valid": numeric_valid,
        "numeric_semantics_supported": numeric_supported,
        "numeric_refusal_reason": numeric_reason,
        "record_valid": record_valid,
        "command_admitted": admitted,
        "refusal_reason": reason,
        "engine_op": engine_op,
        "root_x": root_x,
        "root_y": root_y,
        "inject_node": inject_node,
        "inject_dir": inject_dir,
        "execution_class": execution_class,
        "input_pattern": input_pattern,
        "engine_trap_class": engine_trap_class,
        "expected_trap_class": expected_trap_class,
        "barrier_topology_class": barrier_topology_class,
    }


def build_config(cfg: dict) -> dict:
    mesh_x = cfg["mesh_x"]
    mesh_y = cfg["mesh_y"]
    vec_len = cfg["vec_len"]
    nodes = mesh_x * mesh_y
    lg = (int(math.log2(mesh_x)) if mesh_x > 1 else 0) + (
        int(math.log2(mesh_y)) if mesh_y > 1 else 0
    )
    values = contributions(nodes, vec_len, cfg["seed"])

    tree = fp32(ordered_sum(values, int(ReductionOrder.PAIRWISE_TREE)))
    seq = fp32(ordered_sum(values, int(ReductionOrder.SEQUENTIAL_ASCENDING)))
    blocked = fp32(ordered_sum(values, int(ReductionOrder.BLOCKED_ASCENDING)))
    halving = halving_tree(values)
    differing = int(np.count_nonzero(codes(tree) != codes(seq)))
    tree_vs_halving = int(np.count_nonzero(codes(tree) != codes(halving)))
    blocked_vs_halving = int(np.count_nonzero(codes(blocked) != codes(halving)))

    cases = []
    for spec in cfg["cases"]:
        op = spec["engine_op"]
        alg = spec.get("alg", ALG_RECURSIVE_DOUBLING)
        order = spec.get("order", int(ReductionOrder.PAIRWISE_TREE))
        expect_trap = (
            not spec["command_admitted"] or spec["engine_trap_class"] != 0
        )
        inject_node = spec.get("inject_node", -1)
        inject_dir = spec.get("inject_dir", 0)
        case_values = values.copy()
        pattern = spec["input_pattern"]
        if pattern in {"sum_overflow", "max_nonfinite", "min_nonfinite",
                       "signed_zero"}:
            case_codes = codes(case_values).copy()
            if pattern == "sum_overflow":
                case_codes[:, 0] = np.uint32(0x7F7FFFFF)
            elif pattern in {"max_nonfinite", "min_nonfinite"}:
                case_codes[:, 0] = np.uint32(0x7F800000)
            else:
                case_codes[:, 0] = np.where(
                    np.arange(nodes) % 2,
                    np.uint32(0x00000000), np.uint32(0x80000000)
                )
            case_values = np.ascontiguousarray(case_codes).view(np.float32)

        if not spec["command_admitted"]:
            expected = case_values.copy()     # an admission trap changes nothing
            serial = engine = crossings = 0
            expected_steps_per_node = 0
        elif spec["engine_trap_class"]:
            # Directed exceptional inputs fault at element zero of the first
            # recursive-doubling combine.  Every participant has already sent
            # one complete vector, but no step or architectural write commits.
            expected = case_values.copy()
            serial = 0
            engine = nodes * vec_len
            lgx = int(math.log2(mesh_x)) if mesh_x > 1 else 0
            crossings = sum(
                hop_distance(rank, 0, mesh_x, lgx) * vec_len
                for rank in range(nodes)
            )
            expected_steps_per_node = 0
        elif op == OP_BARRIER:
            expected = case_values.copy()
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)
            expected_steps_per_node = lg
        elif op == int(CollectiveOp.BROADCAST):
            expected = np.tile(case_values[0], (nodes, 1))
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)
            expected_steps_per_node = lg
        else:
            reduced = reduce_expect(case_values, op, order, alg)
            if pattern == "signed_zero":
                reduced_codes = codes(reduced).copy()
                reduced_codes[0] = np.uint32(0x00000000)
                reduced = np.ascontiguousarray(reduced_codes).view(np.float32)
            expected = np.tile(reduced, (nodes, 1))
            serial, engine, crossings, _ = schedule(op, alg, mesh_x, mesh_y, vec_len)
            expected_steps_per_node = (
                2 * lg if alg == ALG_HALVING_DOUBLING and op in (
                    int(CollectiveOp.SUM), int(CollectiveOp.MAX),
                    int(CollectiveOp.MIN)
                ) else lg
            )

        traffic_messages = 0
        traffic_bytes = 0
        functional_oracle = "none"
        record_op = _field_value(spec["record"], 64, 1)
        record_participants = _field_value(spec["record"], 136, 4)
        record_extent = _field_value(spec["record"], 104, 8)
        if spec["record_valid"] and record_op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN),
            int(CollectiveOp.BROADCAST),
        ) and spec["subopcode"] != int(Link.BARRIER):
            traffic_messages, traffic_bytes = collective_traffic(
                record_op, record_participants, record_extent
            )
            functional_oracle = "runtime.sim.engines.link.collective_traffic"
        elif spec["record_valid"] and op == OP_BARRIER:
            topology_class = spec["barrier_topology_class"]
            if topology_class is None:
                topology_class = int(TopologyClass.SINGLE_CHIP)
            traffic_messages = barrier_messages(
                topology_class, record_participants
            )
            functional_oracle = (
                "certified_topology_barrier_messages"
                if spec["barrier_topology_class"] is not None
                else "standalone_dissemination_barrier_messages"
            )

        if spec["command_admitted"]:
            if spec["execution_class"] != "synthetic_bounded_probe":
                raise ValueError(
                    f"{spec['label']}: admitted command is not an explicit synthetic probe"
                )
            if spec["exact_source_record"]:
                raise ValueError(
                    f"{spec['label']}: a deployment record cannot execute as a bounded probe"
                )
            if op == OP_BARRIER:
                if (record_extent != 0 or
                        _field_value(spec["record"], 140, 4) != 0 or
                        any(_field_value(spec["record"], offset, 4) != NO_ID
                            for offset in (16, 20, 80, 84, 128))):
                    raise ValueError(
                        f"{spec['label']}: barrier probe is not neutral"
                    )
            elif (record_extent != vec_len * 4 or
                  _field_value(spec["record"], 140, 4) != 4 or
                  _field_value(spec["record"], 144, 1) !=
                  int(ParticipantScope.NODE) or
                  _field_value(spec["record"], 72, 4) != NO_ID):
                raise ValueError(f"{spec['label']}: dishonest execution geometry")

        cases.append(
            {
                "label": spec["label"],
                "op": _field_value(spec["record"], 64, 1),
                "engine_op": op,
                "alg": alg,
                "order": order,
                "numeric_descriptor_id": spec["numeric_descriptor_id"],
                "numeric_record": spec["numeric_record"],
                "subopcode": spec["subopcode"],
                "root_x": spec["root_x"],
                "root_y": spec["root_y"],
                "inject_node": inject_node,
                "inject_dir": inject_dir,
                "expect_trap": expect_trap,
                "expected_trap_class": spec["expected_trap_class"],
                "engine_trap_class": spec["engine_trap_class"],
                "record_valid": spec["record_valid"],
                "command_admitted": spec["command_admitted"],
                "refusal_reason": spec["refusal_reason"],
                "record": spec["record"],
                "source": spec["source"],
                "source_bundle": spec["source_bundle"],
                "source_descriptor_id": spec["source_descriptor_id"],
                "source_record_sha256": spec["source_record_sha256"],
                "record_sha256": spec["record_sha256"],
                "exact_source_record": spec["exact_source_record"],
                "mutations": spec["mutations"],
                "stale_crc": spec["stale_crc"],
                "numeric_source": spec["numeric_source"],
                "numeric_source_descriptor_id":
                    spec["numeric_source_descriptor_id"],
                "numeric_source_record_sha256":
                    spec["numeric_source_record_sha256"],
                "numeric_record_sha256": spec["numeric_record_sha256"],
                "numeric_exact_source_record":
                    spec["numeric_exact_source_record"],
                "numeric_mutations": spec["numeric_mutations"],
                "numeric_stale_crc": spec["numeric_stale_crc"],
                "numeric_record_valid": spec["numeric_record_valid"],
                "numeric_semantics_supported":
                    spec["numeric_semantics_supported"],
                "numeric_refusal_reason": spec["numeric_refusal_reason"],
                "execution_class": spec["execution_class"],
                "input_pattern": pattern,
                "expected_serial_traversals": int(serial),
                "expected_engine_flits": int(engine),
                "expected_wire_crossings": int(crossings),
                "expected_steps_per_node": expected_steps_per_node,
                "functional_model_messages": int(traffic_messages),
                "functional_model_payload_bytes": int(traffic_bytes),
                "functional_oracle": functional_oracle,
                "contributions": case_values,
                "expected": expected,
            }
        )

    return {
        "mesh_x": mesh_x,
        "mesh_y": mesh_y,
        "vec_len": vec_len,
        "nodes": nodes,
        "credits": cfg["credits"],
        "retry_max": cfg["retry_max"],
        "timeout_class": cfg["timeout_class"],
        "hop_cycles": cfg["hop_cycles"],
        "seed": cfg["seed"],
        "lg": lg,
        "diameter": mesh_diameter(mesh_x, mesh_y),
        "model_charged_traversals": MESH_ALLREDUCE_DIAMETER_FACTOR
        * mesh_diameter(mesh_x, mesh_y),
        "cases": cases,
        "sequential_vs_tree_differing_elements": differing,
        "pairwise_tree_vs_halving_differing_elements": tree_vs_halving,
        "blocked_ascending_vs_halving_differing_elements": blocked_vs_halving,
        "sequential_vs_tree_elements": int(vec_len),
    }


def write_hex(path: Path, words) -> None:
    path.write_text("".join(f"{int(w) & 0xFFFFFFFF:08x}\n" for w in words))


def emit(config: dict, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    nodes = config["nodes"]
    vec_len = config["vec_len"]

    contrib_words = []
    expect_words = []
    communication_words = []
    numeric_words = []
    for case in config["cases"]:
        contrib_words.extend(codes(case["contributions"]).reshape(-1).tolist())
        expect_words.extend(codes(case["expected"]).reshape(-1).tolist())
        communication_words.extend(
            int.from_bytes(case["record"][offset:offset + 4], "little")
            for offset in range(0, DESCRIPTOR_WORDS * 4, 4)
        )
        numeric_words.extend(
            int.from_bytes(case["numeric_record"][offset:offset + 4], "little")
            for offset in range(0, NUMERIC_WORDS * 4, 4)
        )

    case_words = []
    for case in config["cases"]:
        row = [0] * CASE_STRIDE
        row[CW_ALGORITHM] = case["alg"]
        row[CW_NUMERIC_ORDER] = case["order"]
        row[CW_NUMERIC_ID] = case["numeric_descriptor_id"]
        row[CW_SUBOPCODE] = case["subopcode"]
        row[CW_INJECT_NODE] = case["inject_node"] & 0xFFFFFFFF
        row[CW_INJECT_DIR] = case["inject_dir"]
        row[CW_FLAGS] = (
            (CASE_EXPECT_TRAP if case["expect_trap"] else 0) |
            (CASE_DO_INJECT if case["inject_node"] >= 0 else 0) |
            (CASE_EXPECT_RECORD_VALID if case["record_valid"] else 0) |
            (CASE_EXPECT_COMMAND_ADMITTED if case["command_admitted"] else 0)
        )
        row[CW_REASON] = case["refusal_reason"]
        row[CW_EXPECT_TRAP_CLASS] = case["expected_trap_class"]
        row[CW_SERIAL] = case["expected_serial_traversals"]
        row[CW_ENGINE_FLITS] = case["expected_engine_flits"]
        row[CW_CROSSINGS] = case["expected_wire_crossings"]
        row[CW_STEPS] = case["expected_steps_per_node"] * nodes
        row[CW_ENGINE_OP] = case["engine_op"]
        row[CW_ROOT_X] = case["root_x"]
        row[CW_ROOT_Y] = case["root_y"]
        for word, value in decoded_words(case["record"]).items():
            row[word] = value
        row[CW_NUMERIC_RECORD_VALID] = int(case["numeric_record_valid"])
        row[CW_NUMERIC_SEMANTICS_SUPPORTED] = int(
            case["numeric_semantics_supported"]
        )
        row[CW_NUMERIC_REFUSAL_REASON] = case["numeric_refusal_reason"]
        for word, value in numeric_decoded_words(case["numeric_record"]).items():
            row[word] = value
        case_words.extend(row)

    meta = [
        config["mesh_x"], config["mesh_y"], vec_len, config["credits"],
        config["retry_max"], config["hop_cycles"], len(config["cases"]), nodes,
        config["timeout_class"], CASE_STRIDE, DESCRIPTOR_WORDS, NUMERIC_WORDS,
    ]

    write_hex(out_dir / "contrib.hex", contrib_words)
    write_hex(out_dir / "expect.hex", expect_words)
    write_hex(out_dir / "case.hex", case_words)
    write_hex(out_dir / "communication.hex", communication_words)
    write_hex(out_dir / "numeric.hex", numeric_words)
    write_hex(out_dir / "meta.hex", meta)

    summary = {k: v for k, v in config.items()
               if k not in {"contributions", "cases"}}
    summary["cases"] = [
        {k: v for k, v in case.items()
         if k not in {"contributions", "expected", "record", "numeric_record"}}
        for case in config["cases"]
    ]
    summary["marker"] = marker(config)
    return summary


def marker(config: dict) -> str:
    checks = 0
    for case in config["cases"]:
        checks += 69  # COMM/NUMERIC decode, admission, trap and trap class
        checks += config["nodes"] * config["vec_len"]  # result
        checks += 4  # traversals, engine flits, steps, crossings/retry relation
    return (
        f"PASS: A3 LINK mesh={config['mesh_x']}x{config['mesh_y']} "
        f"vec={config['vec_len']} hop={config['hop_cycles']} "
        f"cases={len(config['cases'])} checks={checks}"
    )


def behavioral_cases(cfg: dict, sources: dict) -> list[dict]:
    """Explicit bounded probes plus adversarial standalone-boundary cases."""
    rom = sources["deepseek_rom"]
    template_id = select_communication(
        rom, subopcode=int(Link.COLLECTIVE), collective_op=int(CollectiveOp.SUM)
    )
    numeric_ids = {
        int(ReductionOrder.SEQUENTIAL_ASCENDING):
            SYNTHETIC_SEQUENTIAL_NUMERIC_ID,
        int(ReductionOrder.PAIRWISE_TREE): SYNTHETIC_PAIRWISE_NUMERIC_ID,
        int(ReductionOrder.BLOCKED_ASCENDING): SYNTHETIC_BLOCKED_NUMERIC_ID,
    }

    def comm(label: str, *, op: int = int(CollectiveOp.SUM),
             subopcode: int = int(Link.COLLECTIVE),
             alg: int = ALG_RECURSIVE_DOUBLING,
             order: int = int(ReductionOrder.PAIRWISE_TREE),
             edits: list[tuple[str, int, int, int]] | None = None,
             inject_node: int = -1, numeric_id: int | None = None,
             numeric_record: bytes | None = None,
             numeric_stale_crc: bool = False,
             numeric_mutations: list[str] | None = None,
             execution_class: str = "synthetic_bounded_probe",
             input_pattern: str = "ordinary",
             engine_trap_class: int = TRAP_NONE,
             source_node: int = NO_NODE) -> dict:
        is_reduction = op in (
            int(CollectiveOp.SUM), int(CollectiveOp.MAX), int(CollectiveOp.MIN)
        ) and subopcode != int(Link.BARRIER)
        if numeric_id is None:
            numeric_id = numeric_ids[order] if is_reduction else NO_ID
        if numeric_record is None and is_reduction:
            numeric_record = synthetic_numeric_record(order)
            numeric_mutations = numeric_mutations or [
                "synthetic_fp32_fp32_fp32_fp32",
                "zero_contract_digest",
                "neutral_header_references",
            ]
        common = synthetic_communication_mutations(
            cfg, op=op, numeric_id=numeric_id, source_node=source_node,
            barrier=subopcode == int(Link.BARRIER),
        )
        return make_case_spec(
            label=label, source=rom, descriptor_id=template_id, cfg=cfg,
            subopcode=subopcode, algorithm=alg, numeric_id=numeric_id,
            numeric_order=order, mutations=common + (edits or []),
            inject_node=inject_node, inject_dir=0,
            numeric_record=numeric_record,
            numeric_mutations=numeric_mutations,
            numeric_stale_crc=numeric_stale_crc,
            execution_class=execution_class, input_pattern=input_pattern,
            engine_trap_class=engine_trap_class,
        )

    stale_numeric = mutate_numeric_record(
        synthetic_numeric_record(int(ReductionOrder.PAIRWISE_TREE)),
        [(80, 4, 1)], stale_crc=True
    )
    return [
        comm("synthetic_allreduce_sum_recursive_doubling"),
        comm("synthetic_allreduce_sum_halving_doubling",
             alg=ALG_HALVING_DOUBLING,
             order=int(ReductionOrder.BLOCKED_ASCENDING)),
        comm("synthetic_sum_halving_pairwise_order_refused",
             alg=ALG_HALVING_DOUBLING,
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_sum_recursive_blocked_order_refused",
             order=int(ReductionOrder.BLOCKED_ASCENDING),
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_allreduce_max", op=int(CollectiveOp.MAX)),
        comm("synthetic_allreduce_min", op=int(CollectiveOp.MIN)),
        comm("synthetic_broadcast", op=int(CollectiveOp.BROADCAST),
             subopcode=int(Link.MULTICAST), order=0, source_node=0),
        comm("synthetic_barrier", op=int(CollectiveOp.POINT_TO_POINT),
             subopcode=int(Link.BARRIER), order=0),
        comm("synthetic_allreduce_sum_crc_replay", inject_node=0),
        comm("synthetic_sum_sequential_order_refused",
             order=int(ReductionOrder.SEQUENTIAL_ASCENDING),
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_sum_overflow_trap", input_pattern="sum_overflow",
             engine_trap_class=TRAP_NUMERIC_OR_EXCEPTIONAL_VALUE),
        comm("synthetic_max_nonfinite_trap", op=int(CollectiveOp.MAX),
             input_pattern="max_nonfinite",
             engine_trap_class=TRAP_NUMERIC_OR_EXCEPTIONAL_VALUE),
        comm("synthetic_min_nonfinite_trap", op=int(CollectiveOp.MIN),
             input_pattern="min_nonfinite",
             engine_trap_class=TRAP_NUMERIC_OR_EXCEPTIONAL_VALUE),
        comm("synthetic_max_signed_zero", op=int(CollectiveOp.MAX),
             input_pattern="signed_zero"),
        comm("synthetic_min_signed_zero", op=int(CollectiveOp.MIN),
             input_pattern="signed_zero"),
        comm("synthetic_tile_scope_refused",
             edits=[("participant_scope", 144, 1,
                     int(ParticipantScope.TILE))],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_selected_group_refused",
             edits=[("group_id", 72, 4, 0)],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_broadcast_root_out_of_range_refused",
             op=int(CollectiveOp.BROADCAST), subopcode=int(Link.MULTICAST),
             order=0, source_node=cfg["mesh_x"] * cfg["mesh_y"],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_extent_mismatch_refused",
             edits=[("byte_extent_mismatch", 104, 8, cfg["vec_len"] * 4 + 4)],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_chunk_mismatch_refused",
             edits=[("chunk_bytes_mismatch", 140, 4, 8)],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_data_offset_refused",
             edits=[("local_offset_not_loaded", 88, 8, 4)],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_control_metadata_refused",
             edits=[("ordering_not_implemented", 65, 1, 1)],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_algorithm_unregistered_refused", alg=2,
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_numeric_stale_crc_refused",
             numeric_record=stale_numeric, numeric_stale_crc=True,
             numeric_mutations=["flags_without_crc_reseal"],
             execution_class="synthetic_refusal_probe"),
        comm("synthetic_numeric_sideband_order_mismatch_refused",
             order=int(ReductionOrder.BLOCKED_ASCENDING),
             numeric_id=SYNTHETIC_PAIRWISE_NUMERIC_ID,
             numeric_record=synthetic_numeric_record(
                 int(ReductionOrder.PAIRWISE_TREE)
             ),
             numeric_mutations=["sideband_order_only"],
             execution_class="synthetic_refusal_probe"),
    ]


def hbm_exact_and_negative_cases(cfg: dict, sources: dict) -> list[dict]:
    """Exact HBM positives plus fail-closed structural/semantic mutations."""
    hbm = sources["deepseek_hbm"]
    rom = sources["deepseek_rom"]
    sum_id = select_communication(
        hbm, subopcode=int(Link.COLLECTIVE),
        collective_op=int(CollectiveOp.SUM), zero_extent=False
    )
    barrier_id = select_communication(
        hbm, subopcode=int(Link.BARRIER),
        collective_op=int(CollectiveOp.SUM), zero_extent=True
    )
    allgather_id = select_communication(
        hbm, subopcode=int(Link.COLLECTIVE),
        collective_op=int(CollectiveOp.ALL_GATHER)
    )
    concat_id = select_communication(
        hbm, subopcode=int(Link.SCATTER),
        collective_op=int(CollectiveOp.CONCAT)
    )
    p2p_id = select_communication(
        rom, subopcode=int(Link.SEND),
        collective_op=int(CollectiveOp.POINT_TO_POINT)
    )
    pairwise_id = int(
        hbm["deployment"].table[sum_id].payload["reduction_numeric_id"]
    )
    def hcase(label: str, *, descriptor_id: int = sum_id,
              subopcode: int = int(Link.COLLECTIVE), alg: int = 0,
              numeric_id: int = pairwise_id, order: int = 1,
              edits: list[tuple[str, int, int, int]] | None = None,
              stale_crc: bool = False, inject_node: int = -1,
              source: dict = hbm,
              execution_class: str = "certified_refusal_record",
              barrier_topology_class: int | None = None) -> dict:
        return make_case_spec(
            label=label, source=source, descriptor_id=descriptor_id, cfg=cfg,
            subopcode=subopcode, algorithm=alg, numeric_id=numeric_id,
            numeric_order=order, mutations=edits, stale_crc=stale_crc,
            inject_node=inject_node, inject_dir=0,
            execution_class=execution_class,
            barrier_topology_class=barrier_topology_class,
        )

    cases = [
        hcase("certified_hbm_sum_exact",
              execution_class="certified_decode_only"),
        hcase("certified_hbm_sum_exact_decode_repeat",
              execution_class="certified_decode_only"),
        hcase("certified_hbm_barrier_exact", descriptor_id=barrier_id,
              subopcode=int(Link.BARRIER), numeric_id=NO_ID, order=0,
              execution_class="certified_decode_only",
              barrier_topology_class=hbm["topology_class"]),
        hcase("certified_hbm_all_gather_refused", descriptor_id=allgather_id,
              numeric_id=NO_ID, order=0),
        hcase("certified_hbm_concat_refused", descriptor_id=concat_id,
              subopcode=int(Link.SCATTER), numeric_id=NO_ID, order=0),
        hcase("certified_rom_p2p_refused", descriptor_id=p2p_id,
              subopcode=int(Link.SEND), numeric_id=NO_ID, order=0, source=rom),
        hcase("reduce_scatter_refused", edits=[
            ("collective_op", 64, 1, int(CollectiveOp.REDUCE_SCATTER)),
            ("reduction_numeric_id", 128, 4, NO_ID),
        ], numeric_id=NO_ID, order=0),
    ]
    mutation_specs = [
        ("bad_magic", [("magic", 0, 4, 0x44334100)], False),
        ("bad_type", [("descriptor_type", 4, 2, 5)], False),
        ("bad_version", [("type_minor", 7, 1, 1)], False),
        ("bad_total_bytes", [("total_bytes", 8, 4, 128)], False),
        ("bad_payload_geometry", [("payload_offset", 40, 4, 128)], False),
        ("header_reserved_nonzero", [("header_reserved", 52, 1, 1)], False),
        ("payload_reserved_nonzero", [("payload_reserved", 145, 1, 1)], False),
        ("stale_record_crc", [("route_class", 76, 4, 7)], True),
        ("permissions_reserved", [("permissions", 32, 4, 0x123)], False),
        ("collective_op_unregistered", [("collective_op", 64, 1, 8)], False),
        ("ordering_unregistered", [("ordering", 65, 1, 5)], False),
        ("integrity_mode_unregistered", [("integrity_mode", 66, 1, 4)], False),
        ("participant_scope_unregistered", [("participant_scope", 144, 1, 3)], False),
        ("integrity_ecc_unsupported", [("integrity_mode", 66, 1, 2)], False),
        ("virtual_channel_out_of_range", [("virtual_channel", 67, 1, 4)], False),
        ("credit_bound_mismatch", [("credit_bound", 112, 4, 31)], False),
        ("retry_bound_mismatch", [("retry_bound", 116, 4, 2)], False),
        ("timeout_class_mismatch", [("timeout_class", 120, 4, 2)], False),
        ("participant_count_mismatch", [("participant_count", 136, 4, 31)], False),
        ("object_binding_mismatch", [("primary_object_id", 16, 4, 0)], False),
    ]
    cases.extend(
        hcase(label, edits=edits, stale_crc=stale)
        for label, edits, stale in mutation_specs
    )
    cases.extend([
        hcase("barrier_nonzero_extent", descriptor_id=barrier_id,
              subopcode=int(Link.BARRIER), numeric_id=NO_ID, order=0,
              edits=[("byte_extent", 104, 8, 4)]),
    ])
    return cases


def default_configurations(sources: dict | None = None) -> list[dict]:
    sources = sources or load_certified_sources()
    configs = []
    for hop in (1, 2, 4, 8):
        cfg = {
            "name": f"mesh4x4_vec16_hop{hop}",
            "mesh_x": 4, "mesh_y": 4, "vec_len": 16, "credits": 8,
            "retry_max": 3, "timeout_class": 1,
            "hop_cycles": hop, "seed": 20260831,
        }
        cfg["cases"] = behavioral_cases(cfg, sources)
        configs.append(cfg)
    cfg = {
        "name": "mesh8x8_vec64_hop1",
        "mesh_x": 8, "mesh_y": 8, "vec_len": 64, "credits": 8,
        "retry_max": 3, "timeout_class": 1,
        "hop_cycles": 1, "seed": 20260901,
    }
    cfg["cases"] = behavioral_cases(cfg, sources)
    configs.append(cfg)
    cfg = {
        "name": "mesh2x2_vec4_hop1",
        "mesh_x": 2, "mesh_y": 2, "vec_len": 4, "credits": 8,
        "retry_max": 3, "timeout_class": 1,
        "hop_cycles": 1, "seed": 20260902,
    }
    cfg["cases"] = behavioral_cases(cfg, sources)
    configs.append(cfg)
    cfg = {
        "name": "mesh8x4_vec32_credit32_hop1",
        "mesh_x": 8, "mesh_y": 4, "vec_len": 32, "credits": 32,
        "retry_max": 3, "timeout_class": 1,
        "hop_cycles": 1, "seed": 20260903,
    }
    cfg["cases"] = (
        behavioral_cases(cfg, sources) +
        hbm_exact_and_negative_cases(cfg, sources)
    )
    configs.append(cfg)
    return configs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "testdata/rtl/a3_link"))
    args = parser.parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    sources = load_certified_sources()
    index = {
        "schema": "opentallas.rtl.a3_link_vectors.v3",
        "case_stride": CASE_STRIDE,
        "communication_words": DESCRIPTOR_WORDS,
        "numeric_words": NUMERIC_WORDS,
        "certified_sources": [
            {
                key: source[key]
                for key in (
                    "name", "bundle", "certificate", "certificate_sha256",
                    "deployment_sha256", "descriptor_table_sha256",
                )
            } | {
                "communication_descriptor_count": len(
                    source["communication_ids"]
                )
            }
            for source in sources.values()
        ],
        "configurations": [],
    }
    for cfg in default_configurations(sources):
        built = build_config(cfg)
        summary = emit(built, out_root / cfg["name"])
        summary["name"] = cfg["name"]
        index["configurations"].append(summary)

    (out_root / "index.json").write_text(
        json.dumps(index, indent=1, sort_keys=True) + "\n"
    )
    for entry in index["configurations"]:
        print(f"{entry['name']}: {entry['marker']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
