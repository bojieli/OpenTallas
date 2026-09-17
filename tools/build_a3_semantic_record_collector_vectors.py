#!/usr/bin/env python3
"""Vectors for the semantic-record collector, from the shipped descriptor images.

The collector's claim is narrow and checkable: given the descriptors the
microsequencer walks past, it assembles the same 128 words the decoded path
assembles.  So the vectors are not synthesised -- they are the REAL raw
descriptors of both shipped programs' HC_PRE dispatches, and the expected record
is ``config_words``, the same function whose output
``tests/abi3/test_semantic_record.py`` proves equal to the raw reading.

Three files per store, all ``%08x`` words, one per line:

* ``meta``      -- the nine instruction/profile words the collector is given
                   directly, then the eleven descriptor ids in role order;
* ``descriptors`` -- eleven raw descriptors, 32 words each, in role order;
* ``expected``  -- the 128 words the collector must produce.

The descriptors are emitted in a DELIBERATELY SHUFFLED order in a second stream,
because the collector's design claim is that it matches by identity rather than by
arrival order.  A bench that presented them in the order the operator names them
would pass for a collector that just counted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build_a3_mhc_pre_tile_vectors as tile_vectors  # noqa: E402

OUTPUT_ROOT = ROOT / "testdata/rtl/a3_semantic_record"
ROLES = (
    "operator", "counter", "numeric", "schedule", "wait",
    "input0", "input1", "input2", "input3", "output0", "output1",
)
#: The order the bench presents them in.  The operator is FIRST because it is what
#: names the other ten -- a collector cannot recognise a counter class or a view by
#: id before it has read the descriptor that references it, and neither can the
#: microsequencer, which is why it fetches the operator first.  The remaining ten
#: are deliberately not in role order and not in the sequencer's order, so what is
#: tested is that they are matched by identity: a collector that merely counted
#: arrivals, or assumed the operator's own field order, would fail on this stream.
SHUFFLED = (
    "operator", "output1", "numeric", "input2", "wait", "schedule",
    "input0", "output0", "counter", "input3", "input1",
)
#: Descriptor records are VARIABLE LENGTH -- a 64-byte header then a payload whose
#: size the type decides, so the ones this record needs are 128 and 192 bytes.  The
#: microsequencer's ``desc_data`` port is 1,536 bits, the largest of them, and a
#: shorter record is presented zero-extended.  The stream is emitted at that width
#: so the bench drives exactly what the port carries.
DESCRIPTOR_WORDS = 48


def words_of(raw: bytes) -> list[int]:
    """One descriptor as 48 little-endian words, zero-extended to the port width."""
    if len(raw) > DESCRIPTOR_WORDS * 4:
        raise SystemExit(
            f"a descriptor is {len(raw)} bytes, wider than the "
            f"{DESCRIPTOR_WORDS * 4}-byte desc_data port"
        )
    padded = raw + bytes(DESCRIPTOR_WORDS * 4 - len(raw))
    return [
        int.from_bytes(padded[offset : offset + 4], "little")
        for offset in range(0, len(padded), 4)
    ]


def hex_lines(values: list[int]) -> str:
    return "".join(f"{value & 0xffffffff:08x}\n" for value in values)


def build(output: Path) -> dict[str, object]:
    manifest = json.loads(tile_vectors.DEPLOYMENT_MANIFEST.read_bytes())
    descriptors = tile_vectors.read_hex(tile_vectors.DESCRIPTOR_IMAGE)
    programs = tile_vectors.read_hex(tile_vectors.PROGRAM_IMAGE)
    bases = tile_vectors.deployment_bases(manifest)
    output.mkdir(parents=True, exist_ok=True)

    index: dict[str, object] = {
        "schema": "opentallas.a3_semantic_record_vectors.v1",
        "descriptor_words": DESCRIPTOR_WORDS,
        "record_words": 128,
        "presentation_order": list(SHUFFLED),
        "stores": {},
    }
    for target in tile_vectors.TARGETS:
        profile = tile_vectors.selected_profile(
            target, manifest, descriptors, programs, bases
        )
        expected = tile_vectors.config_words(profile, 1)
        instruction = profile["instruction"]
        ids = {"operator": int(profile["operator_id"])}
        ids.update({role: int(profile["ids"][role]) for role in ROLES if role != "operator"})

        meta = [
            int(target["profile"]),
            1,
            int(target["pc"]),
            int(instruction.flags),
            int(instruction.descriptor_id),
            int(instruction.wait_set_id),
            int(instruction.signal_event_id),
            int(instruction.control_id),
            int(instruction.source_operation_id),
        ] + [ids[role] for role in SHUFFLED]

        stream: list[int] = []
        for role in SHUFFLED:
            stream.extend(words_of(profile["records"][role]))

        store = "rom" if int(target["profile"]) == 0 else "hbm"
        files = {
            f"{store}_meta.hex": hex_lines(meta),
            f"{store}_descriptors.hex": hex_lines(stream),
            f"{store}_expected.hex": hex_lines(list(expected)),
        }
        for name, body in files.items():
            (output / name).write_text(body, encoding="utf-8")
        index["stores"][store] = {
            "key": target["key"],
            "program_counter": int(target["pc"]),
            "operator_descriptor_id": ids["operator"],
            "descriptor_ids_in_presentation_order": [ids[r] for r in SHUFFLED],
            "deployment_sha256": profile["deployment"]["deployment_sha256"],
            "expected_record_sha256": hashlib.sha256(
                b"".join(int(w).to_bytes(4, "little") for w in expected)
            ).hexdigest(),
            "files": {
                name: hashlib.sha256(body.encode()).hexdigest()
                for name, body in files.items()
            },
        }
    (output / "index.json").write_text(
        json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return index


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    index = build(args.output)
    for store, record in sorted(index["stores"].items()):
        print(
            f"{store}: pc {record['program_counter']} operator "
            f"{record['operator_descriptor_id']} record "
            f"{record['expected_record_sha256'][:16]}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
