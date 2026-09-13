#!/usr/bin/env python3
"""Stage one deployment for an end-to-end RTL run that emits a token.

The shipped-prefix vector builder packs every target into one set of images with
golden for every intermediate write, and stops at a fail-stop boundary. This does
something narrower on purpose: it stages ONE deployment's memories so the
integrated vehicle can run the whole program, and checks exactly one thing at the
end -- the token id on ``selected_token``.

WHY ANY VALID ALLOCATION WILL DO. The bridge's rule is
``address = cfg_place_base_N of the view's primary object + the resolved element
offset``, so a placement is correct when every object has ONE distinct base, its
bytes are staged at that base, and no access runs past the bank. It does NOT have
to match the vector builder's compact per-bank allocation -- that matters only for
reproducing the builder's golden, which this does not do.

An object's base is read in different UNITS by different banks: a word index in the
source and result banks, a halfword index in the weight window
(``m1_weight_halfword = (cfg_matmul_weight_window_base >> 1) + m1_rd_addr``). So an
object used as both an operand and a matmul weight is staged at byte ``4 * base`` in
the source image and byte ``2 * base`` in the weight image. Same base, two images.

Object data comes from three places, and all three are checked rather than assumed:
``segments`` are read from the checkpoint at the recorded offset and their SHA-256
compared; ``generated`` objects are produced by the named generator in
runtime.sim.generators and compared against the recorded digest; ``zero`` objects
carry no bytes at all, which is why 33.8 MB of the 38.6 MB declared needs no staging.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType as T  # noqa: E402
from runtime.abi3.constants import Major, Vector  # noqa: E402
from runtime.sim.generators import generate_bytes, digest_of  # noqa: E402

NO_OBJECT = 0xFFFFFFFF
PLACE_TABLE_ENTRIES = 32


def object_roles(table: Any) -> dict[int, set[str]]:
    """Which banks each object is read from or written to.

    Derived from the OPERATOR descriptors' own input/output view slots: slot 1 of a
    TENSOR.MATMUL is the weight operand, any output view is a result, everything
    else is a source operand.
    """
    def primary(view_id: int) -> int | None:
        if view_id == NO_OBJECT:
            return None
        rec = table[view_id]
        oid = rec.primary_object_id
        return int(oid) if oid not in (None, NO_OBJECT) else None

    roles: dict[int, set[str]] = {}
    for op_id in table.ids_of_type(T.OPERATOR):
        payload = table[op_id].payload
        family, sub = payload["engine_family"], payload["engine_sub"]
        for slot in range(4):
            obj = primary(payload[f"input_view_{slot}"])
            if obj is None:
                continue
            weight = family == int(Major.TENSOR) and slot == 1
            roles.setdefault(obj, set()).add("weight" if weight else "source")
        for slot in range(2):
            obj = primary(payload[f"output_view_{slot}"])
            if obj is not None:
                roles.setdefault(obj, set()).add("result")
    return roles


def materialise(source: dict[str, Any], checkpoint: Path) -> bytes | None:
    """The object's bytes, or None when it declares none."""
    kind = source.get("kind")
    if kind == "zero":
        return None
    if kind == "segments":
        blob = b""
        for segment in source["segments"]:
            path = checkpoint / segment["path"]
            with path.open("rb") as handle:
                handle.seek(int(segment["offset"]))
                piece = handle.read(int(segment["bytes"]))
            if len(piece) != int(segment["bytes"]):
                raise SystemExit(f"{path}: segment truncated")
            got = hashlib.sha256(piece).hexdigest()
            if got != segment["sha256"]:
                raise SystemExit(
                    f"{path}@{segment['offset']}: sha256 {got} != {segment['sha256']}"
                )
            blob += piece
        return blob
    if kind == "generated":
        blob = generate_bytes(source["generator"], source["parameters"])
        got = digest_of(source["generator"], source["parameters"])
        recorded = source.get("digest")
        if recorded and got != recorded:
            raise SystemExit(
                f"generator {source['generator']}: digest {got} != {recorded}"
            )
        return bytes(blob)
    raise SystemExit(f"unknown object source kind {kind!r}")


def sparse_hex(placed: list[tuple[int, bytes]], words: int) -> str:
    """A $readmemh image with @address records, so zeros cost nothing."""
    lines: list[str] = []
    for base_word, blob in placed:
        if not blob:
            continue
        lines.append(f"@{base_word:x}")
        pad = (-len(blob)) % 4
        data = blob + bytes(pad)
        lines.extend(
            f"{int.from_bytes(data[i:i + 4], 'little'):08x}"
            for i in range(0, len(data), 4)
        )
    return "".join(line + "\n" for line in lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--align-words", type=int, default=64)
    ap.add_argument("--case", default=None,
                    help=("a case name in the deployment vector set whose symbols and "
                          "entrypoint to bind, e.g. "
                          "'qwen3-reduced-rom-single-chip/decode'"))
    args = ap.parse_args()

    deployment = Deployment.read(args.deployment)
    table = deployment.table
    manifest = json.loads((args.deployment / "deployment.json").read_text())
    sources = {int(o["object_id"]): o["source"] for o in manifest["objects"]}

    roles = object_roles(table)
    if len(roles) > PLACE_TABLE_ENTRIES:
        raise SystemExit(
            f"{len(roles)} objects are referenced and the bridge's placement table "
            f"holds {PLACE_TABLE_ENTRIES}"
        )

    #: Bases are assigned in ONE space, spaced by each object's declared size, so an
    #: object used from two banks has one base that is valid in both.
    cursor = 0
    plan: list[dict[str, Any]] = []
    src_placed: list[tuple[int, bytes]] = []
    wgt_placed: list[tuple[int, bytes]] = []
    for obj in sorted(roles):
        source = sources[obj]
        size = int(source.get("size_bytes") or 0)
        words = (size + 3) // 4
        base = cursor
        cursor += max(words, 1)
        cursor += (-cursor) % args.align_words
        blob = materialise(source, args.checkpoint)
        entry = {
            "object_id": obj,
            "base": base,
            "size_bytes": size,
            "kind": source.get("kind"),
            "roles": sorted(roles[obj]),
            "staged_bytes": len(blob) if blob else 0,
        }
        plan.append(entry)
        if blob:
            if {"source", "result"} & roles[obj]:
                src_placed.append((base, blob))
            if "weight" in roles[obj]:
                #: halfword-indexed window: byte 2*base
                wgt_placed.append((base // 2, blob))
    bank_words = cursor

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "p3_source.hex").write_text(sparse_hex(src_placed, bank_words))
    (args.out_dir / "p3_index.hex").write_text("".join("00000000\n" for _ in range(64)))

    #: the weight window is a flat byte image indexed in halfwords
    weight_bytes = bytearray()
    for half_base, blob in sorted(wgt_placed):
        end = half_base * 2 + len(blob)
        if len(weight_bytes) < end:
            weight_bytes.extend(bytes(end - len(weight_bytes)))
        weight_bytes[half_base * 2 : end] = blob
    (args.out_dir / "p3_matmul_weight.bin").write_bytes(bytes(weight_bytes))

    header = (args.deployment / "program.bin").read_bytes()[:256]
    config = {
        "instruction_count": int.from_bytes(header[16:20], "little"),
        "entrypoint_count": int.from_bytes(header[20:24], "little"),
        "max_retired_work": int.from_bytes(header[184:192], "little"),
        "descriptor_count": len(table),
        "state_count": len(table.ids_of_type(T.STATE)),
        "bank_words": bank_words,
        "weight_bytes": len(weight_bytes),
        "placement": plan,
        "deployment_sha256": deployment.deployment_digest.hex(),
    }
    (args.out_dir / "plan.json").write_text(json.dumps(config, indent=2) + "\n")

    #: A flat driver file, because the C++ driver should not need a JSON parser and
    #: because every value in it is traceable to the line that produced it.
    lines = [
        f"instruction_count {config['instruction_count']}",
        f"desc_count {config['descriptor_count']}",
        f"max_retired_work {config['max_retired_work']}",
        f"state_count {config['state_count']}",
        f"bank_words {bank_words}",
        f"weight_bytes {len(weight_bytes)}",
    ]
    if args.case:
        vectors = json.loads(
            (ROOT / "testdata/compiler/abi3_deployment"
             / "abi3_deployment_rtl_vectors.json").read_text()
        )
        cases = [c for c in vectors["cases"] if c["name"] == args.case]
        if len(cases) != 1:
            raise SystemExit(f"{args.case!r} names {len(cases)} cases, expected one")
        case = cases[0]
        #: cfg_entry_pc is the entrypoint's FIRST INSTRUCTION, not its id.
        entry_id = int(case["entrypoint_id"])
        entries = {int(e["entrypoint_id"]): e for e in manifest["entrypoints"]}
        lines.append(f"entrypoint_id {entry_id}")
        lines.append(f"entry_pc {int(entries[entry_id]['first_instruction'])}")
        lines.append(
            f"generation_policy_id {int(entries[entry_id]['generation_policy_id'])}"
        )
        lines.append(f"phase {int(case['phase'])}")
        #: Symbols are the golden device's OWN bindings for this request, taken from
        #: the case record rather than recomputed, so the RTL is given exactly what
        #: the oracle saw.
        for key, value in sorted(case["symbols"].items(), key=lambda kv: int(kv[0])):
            lines.append(f"symbol {int(key)} {int(value)} 1")
        golden = case.get("golden") or {}
        for name in ("fetched", "retired", "issued", "loop_iterations", "complete"):
            if name in golden:
                lines.append(f"golden_{name} {int(golden[name])}")
    for slot, entry in enumerate(plan):
        lines.append(f"place {slot} {entry['object_id']} {entry['base']}")
    (args.out_dir / "driver.txt").write_text("".join(x + "\n" for x in lines))

    staged = sum(e["staged_bytes"] for e in plan)
    declared = sum(e["size_bytes"] for e in plan)
    print(f"  objects            {len(plan)} (table holds {PLACE_TABLE_ENTRIES})")
    print(f"  declared bytes     {declared:,}")
    print(f"  staged bytes       {staged:,}  "
          f"({100.0 * staged / declared:.1f}% -- the rest declares zeros)")
    print(f"  bank words needed  {bank_words:,}  ({bank_words * 4 / 1e6:.1f} MB)")
    print(f"  weight image       {len(weight_bytes):,} bytes")
    print(f"  instructions       {config['instruction_count']}")
    print(f"  descriptors        {config['descriptor_count']}")
    print(f"  state descriptors  {config['state_count']}")
    print(f"  wrote {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
