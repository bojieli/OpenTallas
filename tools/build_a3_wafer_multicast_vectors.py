#!/usr/bin/env python3
"""Build source-bound vectors for DeepSeek ROM ABI 3.0 PC-13 multicast.

The five positive records are extracted byte-for-byte from the admitted
``build/abi3/deepseek-v4-flash-rom/descriptors.bin`` table.  Negative semantic
cases edit one field and reseal the record CRC; stale-CRC cases are explicitly
the exception.  This keeps descriptor semantics and record-integrity failures
separate in the RTL campaign.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import Link, Major  # noqa: E402
from runtime.abi3.crc import record_crc  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.records import Instruction, split_program  # noqa: E402

DEFAULT_OUTPUT = ROOT / "testdata/rtl/a3_wafer_multicast"
BUNDLE = ROOT / "build/abi3/deepseek-v4-flash-rom"

EXPECTED_DEPLOYMENT = (
    "f239f8fede6963d3daebfe19e8771afad69cf09992e339a0191a1983518ae8a7"
)
EXPECTED_CAPABILITY = (
    "5abf26b4ef235d6083c6f6dbe48d7021068c59ecb451238569a2f660303d26b6"
)

PC = 13
COMM_ID = 368
TOPOLOGY_ID = 0
LOCAL_ID = 365
REMOTE_ID = 366
COUNTER_ID = 367

META_WORDS = 16
COMM_WORDS = 48
TOPOLOGY_WORDS = 64
OBJECT_WORDS = 32
COUNTER_WORDS = 32

REFUSE_NONE = 0
REFUSE_ISSUE_METADATA = 1
REFUSE_VIEW_CONTRACT = 2
REFUSE_STATE_CONTRACT = 3
REFUSE_COMM_RECORD = 4
REFUSE_COMM_SEMANTICS = 5
REFUSE_TOPOLOGY_RECORD = 6
REFUSE_TOPOLOGY = 7
REFUSE_LOCAL_RECORD = 8
REFUSE_REMOTE_RECORD = 9
REFUSE_MEMORY_BINDING = 10
REFUSE_COUNTER_RECORD = 11
REFUSE_COUNTER_BINDING = 12


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def raw_descriptor_records(blob: bytes) -> tuple[bytes, ...]:
    records: list[bytes] = []
    offset = 0
    while offset < len(blob):
        if offset + 12 > len(blob):
            raise ValueError("truncated descriptor table")
        size = int.from_bytes(blob[offset + 8 : offset + 12], "little")
        if size < 64 or size % 64 or offset + size > len(blob):
            raise ValueError(f"invalid descriptor size {size} at {offset}")
        records.append(blob[offset : offset + size])
        offset += size
    return tuple(records)


def read_instruction(pc: int) -> Instruction:
    _, body = split_program((BUNDLE / "program.bin").read_bytes())
    return Instruction.decode(body[pc * 32 : (pc + 1) * 32])


def u(record: bytes, offset: int, size: int) -> int:
    return int.from_bytes(record[offset : offset + size], "little")


def edit(
    record: bytes, offset: int, size: int, value: int, *, reseal: bool = True
) -> bytes:
    changed = bytearray(record)
    changed[offset : offset + size] = int(value).to_bytes(size, "little")
    if reseal:
        changed[48:52] = b"\x00" * 4
        changed[48:52] = record_crc(bytes(changed), 48).to_bytes(4, "little")
    return bytes(changed)


def words(record: bytes) -> list[int]:
    if len(record) % 4:
        raise ValueError("record is not word aligned")
    return [int.from_bytes(record[i : i + 4], "little") for i in range(0, len(record), 4)]


def write_hex(path: Path, values: list[int]) -> None:
    path.write_text("".join(f"{value & 0xffffffff:08x}\n" for value in values))


def source_records() -> dict[str, bytes]:
    deployment = Deployment.read(BUNDLE)
    if deployment.deployment_digest.hex() != EXPECTED_DEPLOYMENT:
        raise ValueError(
            f"DeepSeek ROM deployment is {deployment.deployment_digest.hex()}, "
            f"expected {EXPECTED_DEPLOYMENT}"
        )
    if deployment.capability_digest != EXPECTED_CAPABILITY:
        raise ValueError(
            f"DeepSeek ROM capability is {deployment.capability_digest}, "
            f"expected {EXPECTED_CAPABILITY}"
        )
    records = raw_descriptor_records((BUNDLE / "descriptors.bin").read_bytes())
    if len(records) != len(deployment.table):
        raise ValueError("raw descriptor count disagrees with decoded table")
    selected = {
        "communication": records[COMM_ID],
        "topology": records[TOPOLOGY_ID],
        "local": records[LOCAL_ID],
        "remote": records[REMOTE_ID],
        "counter": records[COUNTER_ID],
    }
    expected_lengths = {
        "communication": 192,
        "topology": 256,
        "local": 128,
        "remote": 128,
        "counter": 128,
    }
    for name, record in selected.items():
        if len(record) != expected_lengths[name]:
            raise ValueError(f"{name} record has {len(record)} bytes")
        if u(record, 48, 4) != record_crc(record, 48):
            raise ValueError(f"{name} record has stale CRC")
    return selected


def assert_exact_source(records: dict[str, bytes]) -> None:
    instruction = read_instruction(PC)
    if not (
        instruction.major == int(Major.LINK)
        and instruction.sub == int(Link.MULTICAST)
        and instruction.descriptor_id == COMM_ID
        and instruction.flags == 8
        and instruction.signal_event_id == 4
    ):
        raise ValueError(f"PC {PC} is not the frozen multicast instruction: {instruction}")

    comm = records["communication"]
    expected_comm = {
        (4, 2): 6,
        (16, 4): LOCAL_ID,
        (20, 4): REMOTE_ID,
        (32, 4): 35,
        (64, 1): 5,
        (65, 1): 2,
        (66, 1): 1,
        (67, 1): 0,
        (68, 2): 0,
        (70, 2): 0,
        (72, 4): 0,
        (76, 4): 0,
        (80, 4): LOCAL_ID,
        (84, 4): REMOTE_ID,
        (88, 8): 0,
        (96, 8): 0,
        (104, 8): 65536,
        (112, 4): 8,
        (116, 4): 3,
        (120, 4): 1,
        (124, 4): 0xFFFFFFFF,
        (128, 4): 0xFFFFFFFF,
        (132, 4): COUNTER_ID,
        (136, 4): 256,
        (140, 4): 4096,
        (144, 1): 2,
    }
    for (offset, size), expected in expected_comm.items():
        if u(comm, offset, size) != expected:
            raise ValueError(
                f"COMMUNICATION byte {offset} is {u(comm, offset, size)}, "
                f"expected {expected}"
            )

    topology = records["topology"]
    expected_topology = {
        (4, 2): 5,
        (8, 4): 256,
        (32, 4): 129,
        (44, 4): 192,
        (64, 1): 2,
        (66, 2): 1,
        (68, 2): 37,
        (70, 2): 256,
        (72, 2): 0,
        (74, 2): 0,
        (76, 2): 0,
        (78, 2): 3,
        (80, 4): 9300,
        (84, 4): 0,
        (88, 8): 1649267441664,
        (96, 8): 8589934592,
        (104, 4): 19072,
        (108, 4): 37,
        (112, 4): 1,
        (116, 4): 96,
    }
    for (offset, size), expected in expected_topology.items():
        if u(topology, offset, size) != expected:
            raise ValueError(f"TOPOLOGY byte {offset} does not match the frozen source")

    for name, permissions in (("local", 3), ("remote", 35)):
        record = records[name]
        expected_object = {
            (4, 2): 1,
            (8, 4): 128,
            (32, 4): permissions,
            (44, 4): 64,
            (64, 1): 1,
            (65, 1): 1,
            (66, 1): 6,
            (68, 2): 0xFFFF,
            (70, 2): 0xFFFF,
            (72, 8): 0,
            (80, 8): 16777216,
            (88, 4): 0xFFFFFFFF,
        }
        for (offset, size), expected in expected_object.items():
            if u(record, offset, size) != expected:
                raise ValueError(f"{name} MEMORY_OBJECT byte {offset} is not frozen")

    counter = records["counter"]
    expected_counter = {
        (4, 2): 12,
        (32, 4): 129,
        (64, 1): 10,
        (65, 1): 3,
        (72, 4): 0x0A000001,
        (76, 4): 0x0A000002,
        (80, 4): 0x0A000003,
    }
    for (offset, size), expected in expected_counter.items():
        if u(counter, offset, size) != expected:
            raise ValueError(f"COUNTER_CLASS byte {offset} is not frozen")


def build_cases(base: dict[str, bytes]) -> list[dict[str, Any]]:
    def case(label: str, reason: int, **changes: Any) -> dict[str, Any]:
        value: dict[str, Any] = {
            "label": label,
            "reason": reason,
            "admitted": reason == REFUSE_NONE,
            "inject_crc": False,
            "issue_pc": PC,
            "issue_major": int(Major.LINK),
            "issue_sub": int(Link.MULTICAST),
            "issue_descriptor_id": COMM_ID,
            "observed_view_count": 0,
            "state_descriptor_count": 0,
            "topology_descriptor_id": TOPOLOGY_ID,
            "local_object_descriptor_id": LOCAL_ID,
            "remote_object_descriptor_id": REMOTE_ID,
            "counter_descriptor_id": COUNTER_ID,
            **base,
        }
        value.update(changes)
        return value

    cases = [
        case("exact_pc13_multicast_crc_replay", REFUSE_NONE, inject_crc=True),
        case("wrong_pc", REFUSE_ISSUE_METADATA, issue_pc=14),
        case("wrong_major", REFUSE_ISSUE_METADATA, issue_major=0x20),
        case("wrong_subopcode", REFUSE_ISSUE_METADATA, issue_sub=2),
        case("wrong_communication_id", REFUSE_ISSUE_METADATA, issue_descriptor_id=369),
        case("nonzero_view_count", REFUSE_VIEW_CONTRACT, observed_view_count=1),
        case("nonzero_state_count", REFUSE_STATE_CONTRACT, state_descriptor_count=1),
        case(
            "communication_stale_crc",
            REFUSE_COMM_RECORD,
            communication=edit(base["communication"], 65, 1, 0, reseal=False),
        ),
        case(
            "communication_ordering",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 65, 1, 3),
        ),
        case(
            "communication_scope",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 144, 1, 1),
        ),
        case(
            "communication_participants",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 136, 4, 255),
        ),
        case(
            "communication_chunk",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 140, 4, 2048),
        ),
        case(
            "communication_extent",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 104, 8, 65532),
        ),
        case(
            "communication_local_object",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 80, 4, 364),
        ),
        case(
            "communication_source_outside_group",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 68, 2, 256),
        ),
        case(
            "communication_destination_outside_group",
            REFUSE_COMM_SEMANTICS,
            communication=edit(base["communication"], 70, 2, 256),
        ),
        case(
            "topology_stale_crc",
            REFUSE_TOPOLOGY_RECORD,
            topology=edit(base["topology"], 64, 1, 1, reseal=False),
        ),
        case(
            "topology_reserved_nonzero",
            REFUSE_TOPOLOGY_RECORD,
            topology=edit(base["topology"], 65, 1, 1),
        ),
        case(
            "topology_class",
            REFUSE_TOPOLOGY,
            topology=edit(base["topology"], 64, 1, 1),
        ),
        case(
            "topology_node_count",
            REFUSE_TOPOLOGY,
            topology=edit(base["topology"], 66, 2, 2),
        ),
        case(
            "topology_group_geometry",
            REFUSE_TOPOLOGY,
            topology=edit(base["topology"], 108, 4, 36),
        ),
        case(
            "topology_selected_group_inactive",
            REFUSE_TOPOLOGY,
            topology=edit(base["topology"], 80, 4, 255),
        ),
        case(
            "topology_selected_group_quarantined",
            REFUSE_TOPOLOGY,
            topology=edit(base["topology"], 84, 4, 1),
        ),
        case(
            "local_object_stale_crc",
            REFUSE_LOCAL_RECORD,
            local=edit(base["local"], 64, 1, 2, reseal=False),
        ),
        case(
            "local_object_reserved_nonzero",
            REFUSE_LOCAL_RECORD,
            local=edit(base["local"], 67, 1, 1),
        ),
        case(
            "remote_object_stale_crc",
            REFUSE_REMOTE_RECORD,
            remote=edit(base["remote"], 64, 1, 2, reseal=False),
        ),
        case(
            "remote_object_reserved_nonzero",
            REFUSE_REMOTE_RECORD,
            remote=edit(base["remote"], 67, 1, 1),
        ),
        case(
            "local_object_permissions",
            REFUSE_MEMORY_BINDING,
            local=edit(base["local"], 32, 4, 1),
        ),
        case(
            "remote_object_permissions",
            REFUSE_MEMORY_BINDING,
            remote=edit(base["remote"], 32, 4, 3),
        ),
        case(
            "local_object_id_sideband",
            REFUSE_MEMORY_BINDING,
            local_object_descriptor_id=364,
        ),
        case(
            "remote_object_id_sideband",
            REFUSE_MEMORY_BINDING,
            remote_object_descriptor_id=365,
        ),
        case(
            "local_object_range",
            REFUSE_MEMORY_BINDING,
            local=edit(base["local"], 80, 8, 65532),
        ),
        case(
            "remote_object_range",
            REFUSE_MEMORY_BINDING,
            remote=edit(base["remote"], 80, 8, 16777212),
        ),
        case(
            "counter_stale_crc",
            REFUSE_COUNTER_RECORD,
            counter=edit(base["counter"], 64, 1, 9, reseal=False),
        ),
        case(
            "counter_reserved_nonzero",
            REFUSE_COUNTER_RECORD,
            counter=edit(base["counter"], 66, 1, 1),
        ),
        case(
            "counter_id_sideband",
            REFUSE_COUNTER_BINDING,
            counter_descriptor_id=366,
        ),
        case(
            "counter_group",
            REFUSE_COUNTER_BINDING,
            counter=edit(base["counter"], 64, 1, 9),
        ),
        case(
            "counter_event_count",
            REFUSE_COUNTER_BINDING,
            counter=edit(base["counter"], 65, 1, 2),
        ),
    ]
    labels = [entry["label"] for entry in cases]
    if len(labels) != len(set(labels)):
        raise ValueError("duplicate case label")
    return cases


def build(output: Path) -> dict[str, Any]:
    base = source_records()
    assert_exact_source(base)
    cases = build_cases(base)
    output.mkdir(parents=True, exist_ok=True)

    meta: list[int] = []
    comm: list[int] = []
    topology: list[int] = []
    local: list[int] = []
    remote: list[int] = []
    counter: list[int] = []
    for entry in cases:
        meta.extend(
            [
                entry["issue_pc"],
                entry["issue_major"],
                entry["issue_sub"],
                entry["issue_descriptor_id"],
                entry["observed_view_count"],
                entry["state_descriptor_count"],
                entry["topology_descriptor_id"],
                entry["local_object_descriptor_id"],
                entry["remote_object_descriptor_id"],
                entry["counter_descriptor_id"],
                int(entry["admitted"]),
                entry["reason"],
                int(entry["inject_crc"]),
                0,
                0,
                0,
            ]
        )
        comm.extend(words(entry["communication"]))
        topology.extend(words(entry["topology"]))
        local.extend(words(entry["local"]))
        remote.extend(words(entry["remote"]))
        counter.extend(words(entry["counter"]))

    write_hex(output / "case_meta.hex", meta)
    write_hex(output / "communication.hex", comm)
    write_hex(output / "topology.hex", topology)
    write_hex(output / "local_object.hex", local)
    write_hex(output / "remote_object.hex", remote)
    write_hex(output / "counter.hex", counter)

    manifest = {
        "schema": "opentallas.rtl.a3_wafer_multicast_vectors.v1",
        "source": {
            "bundle": str(BUNDLE.relative_to(ROOT)),
            "deployment_sha256": EXPECTED_DEPLOYMENT,
            "capability_sha256": EXPECTED_CAPABILITY,
            "deployment_json_sha256": sha256(BUNDLE / "deployment.json"),
            "descriptors_bin_sha256": sha256(BUNDLE / "descriptors.bin"),
            "program_bin_sha256": sha256(BUNDLE / "program.bin"),
            "pc": PC,
            "communication_descriptor_id": COMM_ID,
            "topology_descriptor_id": TOPOLOGY_ID,
            "local_object_descriptor_id": LOCAL_ID,
            "remote_object_descriptor_id": REMOTE_ID,
            "counter_descriptor_id": COUNTER_ID,
            "raw_record_sha256": {
                name: hashlib.sha256(record).hexdigest()
                for name, record in base.items()
            },
            "communication_prefix_hex": base["communication"][:32].hex(),
        },
        "geometry": {
            "participants": 256,
            "rounds": 8,
            "messages": 255,
            "bytes_per_message": 65536,
            "payload_bytes": 16711680,
            "words_per_message": 16384,
            "payload_flits": 4177920,
            "remote_writes_including_root": 4194304,
        },
        "case_count": len(cases),
        "cases": [
            {
                "index": index,
                "label": entry["label"],
                "admitted": entry["admitted"],
                "refusal_reason": entry["reason"],
                "inject_crc": entry["inject_crc"],
            }
            for index, entry in enumerate(cases)
        ],
        "files": {
            name: {"sha256": sha256(output / name), "bytes": (output / name).stat().st_size}
            for name in (
                "case_meta.hex",
                "communication.hex",
                "topology.hex",
                "local_object.hex",
                "remote_object.hex",
                "counter.hex",
            )
        },
    }
    (output / "index.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        f"wrote {manifest['case_count']} wafer multicast cases to "
        f"{args.output.resolve()}"
    )


if __name__ == "__main__":
    main()
