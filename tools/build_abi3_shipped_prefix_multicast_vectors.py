#!/usr/bin/env python3
"""Build the frozen shipped-prefix overlay for exact wafer multicast.

This builder deliberately does not regenerate the canonical deployments.  It
extends the retained, already-checked shipped-prefix vector identity with the
first (exact) case of the independently qualified wafer-multicast vector set.
That narrow construction is necessary while the Qwen HBM deployment
certificate is source-stale.  The resulting evidence is therefore useful for
RTL integration, but is not promotable to a model-correctness or TPOT gate
until the owning deployment pipeline performs a canonical rebuild.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
BASE_JSON = BASE_DIR / "abi3_shipped_prefix_vectors.json"
MULTICAST_DIR = ROOT / "testdata/rtl/a3_wafer_multicast"
MULTICAST_JSON = MULTICAST_DIR / "index.json"
MULTICAST_CAMPAIGN = ROOT / "results/rtl/a3_wafer_multicast_campaign.json"
ADAPTER_SOURCE = ROOT / "rtl/abi3/ot_a3_wafer_multicast_adapter.sv"
OUTPUT_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix_multicast"

SCHEMA = "opentallas.rtl.abi3_shipped_prefix_multicast_vectors.v1"
BASE_SCHEMA = "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
MULTICAST_SCHEMA = "opentallas.rtl.a3_wafer_multicast_vectors.v1"
CASE_STRIDE = 80
ISSUE_STRIDE = 4
CASE_COUNT = 4
DEEPSEEK_ROM_CASE = 2
SOURCE_WORDS = 16_384

OVERLAY_FILES = (
    "p3_case.hex",
    "p3_issue.hex",
    "p3_meta.hex",
    "p3_multicast_communication.hex",
    "p3_multicast_topology.hex",
    "p3_multicast_local_object.hex",
    "p3_multicast_remote_object.hex",
    "p3_multicast_counter.hex",
    "p3_multicast_source.hex",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_hex(path: Path) -> list[int]:
    return [
        int(line, 16)
        for line in path.read_text(encoding="ascii").splitlines()
        if line.strip()
    ]


def hex_text(words: list[int]) -> str:
    return "".join(f"{word & 0xFFFF_FFFF:08x}\n" for word in words)


def payload_word(index: int) -> int:
    if not 0 <= index < SOURCE_WORDS:
        raise ValueError("multicast payload index is out of range")
    return (
        0x9E37_79B9
        ^ ((index * 0x045D_9F3B) & 0xFFFF_FFFF)
        ^ ((index << 18) | (index << 4) | (index & 0xF))
    ) & 0xFFFF_FFFF


def require_hashed_files(root: Path, hashes: dict[str, str]) -> None:
    for name, expected in hashes.items():
        path = root / name
        if not path.is_file() or sha256_file(path) != expected:
            raise SystemExit(f"frozen input changed: {path}")


def record_sha256(words: list[int]) -> str:
    return hashlib.sha256(
        b"".join(struct.pack("<I", word) for word in words)
    ).hexdigest()


def normalized_case(index: int, name: str, words: list[int]) -> dict[str, int | str]:
    return {
        "index": index,
        "name": name,
        "launches": words[14],
        "words": words[15],
        "responses": words[21],
        "trap": 4,
        "fault": words[16],
        "fetched": words[19],
        "retired": words[20],
        "issued": words[21],
        "views": words[24],
        "multicast_launches": words[79],
    }


def build(output: Path = OUTPUT_DIR) -> dict[str, Any]:
    base = json.loads(BASE_JSON.read_text(encoding="utf-8"))
    if base.get("schema") != BASE_SCHEMA or base.get("case_count") != CASE_COUNT:
        raise SystemExit("the frozen shipped-prefix base has an unknown geometry")
    require_hashed_files(BASE_DIR, base["image_sha256"])

    base_manifest_sha256 = sha256_file(BASE_JSON)
    base_case = read_hex(BASE_DIR / "p3_case.hex")
    base_issue = read_hex(BASE_DIR / "p3_issue.hex")
    base_meta = read_hex(BASE_DIR / "p3_meta.hex")
    if (
        len(base_case) != CASE_COUNT * CASE_STRIDE
        or len(base_issue) != 128
        or len(base_meta) != 26
        or base.get("real_engine_launch_count") != 28
        or base.get("result_word_count") != 91_136
        or base.get("resolved_view_count") != 94
        or base.get("rope_launch_count") != 4
        or base.get("rope_result_word_count") != 10_240
    ):
        raise SystemExit("the frozen shipped-prefix base geometry changed")

    multicast = json.loads(MULTICAST_JSON.read_text(encoding="utf-8"))
    if (
        multicast.get("schema") != MULTICAST_SCHEMA
        or multicast.get("case_count") != 38
        or multicast.get("cases", [{}])[0].get("label")
        != "exact_pc13_multicast_crc_replay"
        or not multicast["cases"][0].get("admitted")
        or not multicast["cases"][0].get("inject_crc")
    ):
        raise SystemExit("the qualified multicast vector identity changed")
    require_hashed_files(
        MULTICAST_DIR,
        {name: entry["sha256"] for name, entry in multicast["files"].items()},
    )

    source = multicast["source"]
    if (
        source.get("deployment_sha256")
        != base["cases"][DEEPSEEK_ROM_CASE]["deployment_sha256"]
        or source.get("pc") != 13
        or source.get("communication_descriptor_id") != 368
        or source.get("topology_descriptor_id") != 0
        or source.get("local_object_descriptor_id") != 365
        or source.get("remote_object_descriptor_id") != 366
        or source.get("counter_descriptor_id") != 367
    ):
        raise SystemExit("multicast qualification is not bound to the frozen ROM case")

    record_inputs = {
        "communication": ("communication.hex", 48),
        "topology": ("topology.hex", 64),
        "local": ("local_object.hex", 32),
        "remote": ("remote_object.hex", 32),
        "counter": ("counter.hex", 32),
    }
    exact_records: dict[str, list[int]] = {}
    for key, (name, count) in record_inputs.items():
        words = read_hex(MULTICAST_DIR / name)[:count]
        if (
            len(words) != count
            or record_sha256(words) != source["raw_record_sha256"][key]
        ):
            raise SystemExit(f"qualified exact multicast {key} record changed")
        exact_records[key] = words

    # Preserve each base response stream exactly, except that DeepSeek ROM's
    # former LINK capability response becomes a successful completion and the
    # precise PC-15 VECTOR.MHC capability response is appended.
    cases = [
        base_case[index * CASE_STRIDE : (index + 1) * CASE_STRIDE]
        for index in range(CASE_COUNT)
    ]
    streams: list[list[int]] = []
    for index, record in enumerate(cases):
        begin = record[31] * ISSUE_STRIDE
        end = begin + record[21] * ISSUE_STRIDE
        stream = base_issue[begin:end]
        if len(stream) != record[21] * ISSUE_STRIDE:
            raise SystemExit(f"frozen response stream {index} is truncated")
        streams.append(stream)

    old_tail = streams[DEEPSEEK_ROM_CASE][-ISSUE_STRIDE:]
    if old_tail != [0x9003, 368, 13, 4]:
        raise SystemExit("frozen DeepSeek ROM boundary is no longer LINK.MULTICAST")
    streams[DEEPSEEK_ROM_CASE][-ISSUE_STRIDE:] = [0x9003, 368, 13, 0]
    streams[DEEPSEEK_ROM_CASE].extend([0x3009, 381, 15, 4])

    rom = cases[DEEPSEEK_ROM_CASE]
    rom[14] = 5  # four prior engines plus exact multicast
    rom[16] = 15  # first unsupported instruction
    rom[17] = 0x3009  # VECTOR.MHC
    rom[18] = 381
    rom[19] = 16  # fetched
    rom[20] = 15  # retired
    rom[21] = 6  # issued/completion responses
    rom[22] = 4  # completed LOOP_NEXT operations
    rom[23] = 5  # successful signal publications
    rom[24] = 17  # 11 prior plus six MHC views
    rom[29] = 1  # one capability response
    rom[35] = 2  # transfer wait plus MHC wait
    rom[79] = 1  # reserved base word: exact multicast launches
    for index, record in enumerate(cases):
        if index != DEEPSEEK_ROM_CASE:
            record[79] = 0

    issue_words: list[int] = []
    for record, stream in zip(cases, streams, strict=True):
        record[31] = len(issue_words) // ISSUE_STRIDE
        issue_words.extend(stream)
    if len(issue_words) != 132:
        raise SystemExit("extended issue stream does not contain 33 responses")

    case_words = [word for record in cases for word in record]
    meta_words = copy.copy(base_meta)
    meta_words[1] = 29  # 28 base launches plus exact multicast
    meta_words[3] = 100  # 94 base views plus six MHC views

    payload = [payload_word(index) for index in range(SOURCE_WORDS)]
    files = {
        "p3_case.hex": hex_text(case_words),
        "p3_issue.hex": hex_text(issue_words),
        "p3_meta.hex": hex_text(meta_words),
        "p3_multicast_communication.hex": hex_text(exact_records["communication"]),
        "p3_multicast_topology.hex": hex_text(exact_records["topology"]),
        "p3_multicast_local_object.hex": hex_text(exact_records["local"]),
        "p3_multicast_remote_object.hex": hex_text(exact_records["remote"]),
        "p3_multicast_counter.hex": hex_text(exact_records["counter"]),
        "p3_multicast_source.hex": hex_text(payload),
    }
    if set(files) != set(OVERLAY_FILES):
        raise AssertionError("overlay file list drift")

    output.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (output / name).write_text(text, encoding="ascii")

    marker = (
        "PASS: ABI3 shipped-prefix multicast integration "
        "cases=4 launches=29 words=91136 capability_faults=4 multicasts=1"
    )
    normalized = [
        normalized_case(index, base["cases"][index]["name"], record)
        for index, record in enumerate(cases)
    ]
    summary: dict[str, Any] = {
        "schema": SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "state_compat": 0,
        "status": "frozen_identity_rtl_integration_only",
        "promotion_status": "blocked_on_canonical_deployment_rebuild",
        "promotion_blocker": (
            "the Qwen HBM deployment certificate records a 32992-byte IR kernel "
            "while the current source is 33234 bytes; this overlay neither "
            "bypasses nor relabels that source-currentness failure"
        ),
        "claim": (
            "the already-checked four-case shipped RTL prefix identity is "
            "extended only by the qualified exact DeepSeek ROM PC-13 "
            "LINK.MULTICAST; it completes one 256-participant, 64-KiB broadcast "
            "with CRC replay and then fails closed at PC-15 VECTOR.MHC"
        ),
        "does_not_establish": [
            "a source-current canonical compiler or deployment rebuild",
            "prefill, a whole model transaction, token selection, EOS, or decoded-token correctness",
            "architectural TPOT, physical timing, area, power, HBM timing, or SRAM timing",
            "simulator wall time as model performance",
        ],
        "base_vector_set": {
            "path": str(BASE_JSON.relative_to(ROOT)),
            "sha256": base_manifest_sha256,
            "schema": base["schema"],
            "image_sha256": base["image_sha256"],
            "input_deployment_vectors": base["input_deployment_vectors"],
        },
        "multicast_qualification": {
            "vector_manifest": str(MULTICAST_JSON.relative_to(ROOT)),
            "vector_manifest_sha256": sha256_file(MULTICAST_JSON),
            "campaign": str(MULTICAST_CAMPAIGN.relative_to(ROOT)),
            "campaign_sha256": sha256_file(MULTICAST_CAMPAIGN),
            "adapter_source": str(ADAPTER_SOURCE.relative_to(ROOT)),
            "adapter_source_sha256": sha256_file(ADAPTER_SOURCE),
            "source": source,
            "geometry": multicast["geometry"],
            "exact_case": multicast["cases"][0],
        },
        "case_count": CASE_COUNT,
        "case_stride": CASE_STRIDE,
        "issue_stride": ISSUE_STRIDE,
        "issue_count": len(issue_words) // ISSUE_STRIDE,
        "real_launch_count": 29,
        "multicast_launch_count": 1,
        "result_word_count": base["result_word_count"],
        "resolved_view_count": 100,
        "capability_fault_count": 4,
        "required_marker": marker,
        "exact_multicast": {
            "pc": 13,
            "family": 0x90,
            "sub": 3,
            "communication_descriptor_id": 368,
            "topology_descriptor_id": 0,
            "local_object_descriptor_id": 365,
            "remote_object_descriptor_id": 366,
            "counter_descriptor_id": 367,
            "payload_source": "deterministic_nonzero_live_scratch_object_365",
            "payload_function": (
                "0x9e3779b9 XOR (index * 0x045d9f3b) XOR "
                "concat(index[13:0], index[13:0], index[3:0])"
            ),
            "payload_words": SOURCE_WORDS,
            "next_unsupported": {
                "pc": 15,
                "family": 0x30,
                "sub": 9,
                "opcode": "VECTOR.MHC",
                "descriptor_id": 381,
                "trap_class": 4,
            },
        },
        "expected_cases": normalized,
        "image_sha256": {
            name: hashlib.sha256(text.encode("ascii")).hexdigest()
            for name, text in sorted(files.items())
        },
    }
    (output / "abi3_shipped_prefix_multicast_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    summary = build(args.output.resolve())
    print(
        "ABI3 frozen multicast overlay: "
        f"cases={summary['case_count']} launches={summary['real_launch_count']} "
        f"issues={summary['issue_count']} views={summary['resolved_view_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
