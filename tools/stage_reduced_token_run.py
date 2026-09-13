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
from runtime.abi3.constants import (  # noqa: E402
    DTYPE_BITS,
    DType,
    Attention, Dma, Major, Selection, Tensor, Vector,
)
from runtime.sim.generators import generate_bytes, digest_of  # noqa: E402

NO_OBJECT = 0xFFFFFFFF
PLACE_TABLE_ENTRIES = 32


#: WHICH BANK EACH PORT READS, per engine family.
#:
#: The verification top does not have one flat operand memory.  Operand port A
#: (``m0``) reads ``result_mem`` or the small ``index_mem``; operand port B
#: (``m1``) reads ``result_mem``, the matmul weight window, or ``source_mem``.
#: Which one is a fixed function of the operator family -- it is the bridge's
#: ``m0_reads_result`` / ``m1_reads_result`` / ``m1_reads_matmul_weight``
#: assignments, transcribed.  Staging everything into one flat space put the
#: gather index 1.9 M words up a 64-word bank, where it read as zero.
#:
#: (family, sub) -> (bank read by port A, bank read by port B)
BANK_BY_FAMILY: dict[tuple[int, int], tuple[str, str]] = {
    (int(Major.DMA), int(Dma.TRANSFER)): ("index", "result"),
    #: "result" matches the bridge elaborated with GATHER_READS_RESULT=1,
    #: which a gather selecting a computed row requires; pass
    #: --gather-source-bank source for the default elaboration.
    (int(Major.DMA), int(Dma.GATHER)): ("index", "result"),
    (int(Major.DMA), int(Dma.SCATTER)): ("index", "result"),
    (int(Major.TENSOR), int(Tensor.MATMUL)): ("result", "weight"),
    (int(Major.TENSOR), int(Tensor.EMBED_LOOKUP)): ("index", "source"),
    (int(Major.VECTOR), int(Vector.RMS_NORM)): ("result", "source"),
    (int(Major.VECTOR), int(Vector.HEAD_RMS_NORM)): ("result", "source"),
    (int(Major.VECTOR), int(Vector.ROPE)): ("result", "result"),
    (int(Major.VECTOR), int(Vector.ADD)): ("result", "result"),
    (int(Major.VECTOR), int(Vector.SILU_MUL)): ("result", "result"),
    (int(Major.ATTENTION), int(Attention.GQA)): ("result", "source"),
    (int(Major.SELECTION), int(Selection.ARGMAX)): ("result", "source"),
    (int(Major.SELECTION), int(Selection.TOKEN_APPEND)): ("result", "source"),
}

#: ATTENTION.GQA probes its position through slot 3, not slot 0
#: (``mapped_index_slot_base = attention_gqa_q ? slot3_base : slot0_base``), and
#: that probe always reads the index bank because ``bridge_index_read`` forces
#: ``m0_reads_result`` low.
INDEX_PROBE_SLOT: dict[tuple[int, int], int] = {
    (int(Major.ATTENTION), int(Attention.GQA)): 3,
}


def token_id_object(table: Any) -> int:
    """The object the host writes the request's token ids into.

    It is the object bound to slot 0 of ``TENSOR.EMBED_LOOKUP`` -- the index the
    lookup selects a row by. Its declared source is zeros precisely because the
    content is a property of the request and not of the deployment, so nothing
    stages it and a run that does not plant it embeds token 0 at every position.
    """
    found: set[int] = set()
    for op_id in table.ids_of_type(T.OPERATOR):
        payload = table[op_id].payload
        if (int(payload["engine_family"]) == int(Major.TENSOR)
                and int(payload["engine_sub"]) == int(Tensor.EMBED_LOOKUP)):
            view = payload["input_view_0"]
            if view != NO_OBJECT:
                oid = table[view].primary_object_id
                if oid not in (None, NO_OBJECT):
                    found.add(int(oid))
    if len(found) != 1:
        raise SystemExit(
            f"expected exactly one EMBED_LOOKUP index object, found {sorted(found)}"
        )
    return next(iter(found))


def object_banks(table: Any) -> dict[int, str]:
    """The one bank each object must be placed in.

    An object read from two different banks is the case the bridge's header
    note calls out as unsupported -- "one object in two banks may not" -- so it
    is a hard error here rather than a base that is wrong for one of them.
    """
    def primary(view_id: int) -> tuple[int | None, int | None]:
        if view_id == NO_OBJECT:
            return None, None
        rec = table[view_id]
        oid = rec.primary_object_id
        if oid in (None, NO_OBJECT):
            return None, None
        return int(oid), int(rec.payload["dtype"])

    demands: dict[int, dict[str, list[str]]] = {}

    #: EACH BANK WORD HOLDS ONE ELEMENT, zero-extended -- a BF16 row occupies
    #: one 32-bit word per value, not two values per word.  The shipped vector
    #: builder shows the convention directly: it packs an FP32 row with
    #: ``range(0, len(row), 4)`` and a BF16 row with ``range(0, len(row), 2)``,
    #: both into 32-bit words.  Packing BF16 raw made every read of a BF16
    #: object return two elements glued together, which stayed finite for two
    #: transformer layers and then overflowed.
    widths: dict[int, set[int]] = {}

    def demand(obj: int, bank: str, why: str, dtype: int | None = None) -> None:
        demands.setdefault(obj, {}).setdefault(bank, []).append(why)
        if dtype is not None:
            widths.setdefault(obj, set()).add(DTYPE_BITS[DType(dtype)] // 8)

    for op_id in table.ids_of_type(T.OPERATOR):
        payload = table[op_id].payload
        family, sub = int(payload["engine_family"]), int(payload["engine_sub"])
        key = (family, sub)
        if key not in BANK_BY_FAMILY:
            raise SystemExit(
                f"operator {op_id}: family 0x{family:02x} sub 0x{sub:02x} has no "
                f"bank rule; add it to BANK_BY_FAMILY from the bridge's "
                f"m0_reads_result / m1_reads_result assignments"
            )
        port_a, port_b = BANK_BY_FAMILY[key]
        probe = INDEX_PROBE_SLOT.get(key)
        for slot in range(4):
            obj, dtype = primary(payload[f"input_view_{slot}"])
            if obj is None:
                continue
            if slot == probe:
                bank = "index"
            elif slot == 0:
                bank = port_a
            elif slot == 1:
                bank = port_b
            else:
                #: Only ATTENTION.GQA binds past slot 1, and it fetches every
                #: one of its planes through port A (``gqa_mem_req_addr`` is
                #: muxed onto ``m0``), so a third or fourth slot follows port A
                #: rather than naming a third port.
                bank = port_a
            demand(obj, bank, f"op{op_id} slot{slot}", dtype)
        for slot in range(2):
            obj, dtype = primary(payload[f"output_view_{slot}"])
            if obj is not None:
                demand(obj, "result", f"op{op_id} out{slot}", dtype)

    banks: dict[int, str] = {}
    for obj, wants in sorted(demands.items()):
        #: A produced value read back later is in result_mem for both, so
        #: "result" absorbs a co-occurring read of the same object.
        if len(wants) > 1 and set(wants) - {"result"} != set(wants):
            wants = {k: v for k, v in wants.items() if k == "result"}
        if len(wants) != 1:
            detail = "; ".join(f"{b} ({', '.join(w)})" for b, w in sorted(wants.items()))
            raise SystemExit(
                f"object {obj} is read from more than one bank: {detail}. The "
                f"bridge admits one object in one bank only."
            )
        banks[obj] = next(iter(wants))

    #: Objects some operator READS.  A result-bank object of this kind whose
    #: declared source is zeros must be staged as zeros: the verification top
    #: poisons the result bank with 0xdeadbeef so that a read of memory nothing
    #: declares is visible, and 0xdeadbeef's low half is a perfectly finite BF16.
    #: Leaving the KV cache poisoned let sixteen unwritten context rows dominate
    #: attention, and thirty-one of thirty-two input tokens then produced the
    #: same output token -- a wrong answer that looked like a dead datapath.
    read_objects = {
        obj for obj, wants in demands.items()
        if any(why.endswith(tuple(f"slot{i}" for i in range(4)))
               for whys in wants.values() for why in whys)
    }

    element_bytes: dict[int, int] = {}
    for obj in banks:
        seen = widths.get(obj) or {4}
        if len(seen) != 1:
            raise SystemExit(
                f"object {obj} is viewed at more than one element width "
                f"({sorted(seen)}); one base cannot serve both"
            )
        element_bytes[obj] = next(iter(seen))
    return banks, element_bytes, read_objects


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


def sparse_hex(placed: list[tuple[int, bytes, int]], words: int) -> str:
    """A $readmemh image with @address records, so zeros cost nothing.

    One element per 32-bit word, zero-extended: ``element_bytes`` says how wide
    the object's elements are, and each is widened to a word. That is the
    convention the shipped vector builder writes and the one the verification
    top's ``m0``/``m1`` word reads expect.
    """
    lines: list[str] = []
    for base_word, blob, element_bytes in placed:
        if not blob:
            continue
        lines.append(f"@{base_word:x}")
        pad = (-len(blob)) % element_bytes
        data = blob + bytes(pad)
        lines.extend(
            f"{int.from_bytes(data[i:i + element_bytes], 'little'):08x}"
            for i in range(0, len(data), element_bytes)
        )
    return "".join(line + "\n" for line in lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--deployment", type=Path, required=True)
    ap.add_argument("--checkpoint", type=Path, required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--align-words", type=int, default=64)
    ap.add_argument("--prompt-tokens", default=None,
                    help=("comma-separated token ids to plant in the embed-lookup "
                          "index object, or the path to a reference oracle whose "
                          "prompt_token_ids are used"))
    ap.add_argument("--case", default=None,
                    help=("a case name in the deployment vector set whose symbols and "
                          "entrypoint to bind, e.g. "
                          "'qwen3-reduced-rom-single-chip/decode'"))
    args = ap.parse_args()

    deployment = Deployment.read(args.deployment)
    table = deployment.table
    manifest = json.loads((args.deployment / "deployment.json").read_text())
    sources = {int(o["object_id"]): o["source"] for o in manifest["objects"]}

    banks, element_bytes, read_objects = object_banks(table)
    if len(banks) > PLACE_TABLE_ENTRIES:
        raise SystemExit(
            f"{len(banks)} objects are referenced and the bridge's placement table "
            f"holds {PLACE_TABLE_ENTRIES}"
        )

    #: One cursor PER BANK.  The banks are separate address spaces in the
    #: verification top, so an index object and a source object may hold the
    #: same base; what may not happen is one object needing two of them, and
    #: object_banks has already refused that.
    cursors = {"index": 0, "source": 0, "result": 0, "weight": 0}
    plan: list[dict[str, Any]] = []
    staged: dict[str, list[tuple[int, bytes, int]]] = {
        "index": [], "source": [], "result": [], "weight": [],
    }
    for obj in sorted(banks):
        bank = banks[obj]
        source = sources[obj]
        size = int(source.get("size_bytes") or 0)
        #: EACH BANK IS ADDRESSED IN ITS OWN UNIT.  index/source/result are
        #: 32-bit word arrays; the matmul weight window is indexed in HALFWORDS
        #: (``m1_weight_halfword = (window_base >> 1) + m1_rd_addr``).  Sizing
        #: the weight bank in words spaced its objects four times too tightly
        #: and every projection after the first overlapped the one before it.
        #: The weight window is a flat halfword-addressed byte image, so a BF16
        #: projection is packed two elements per 32-bit word there.  Every other
        #: bank is an array of 32-bit words holding ONE element each, so an
        #: object of N elements needs N words whatever its element width.
        elem = element_bytes[obj]
        elements = (size + elem - 1) // elem
        slots_needed = (size + 1) // 2 if bank == "weight" else elements
        base = cursors[bank]
        cursors[bank] += max(slots_needed, 1)
        cursors[bank] += (-cursors[bank]) % args.align_words
        blob = materialise(source, args.checkpoint)
        plan.append({
            "object_id": obj,
            "bank": bank,
            "element_bytes": elem,
            "elements": elements,
            "base": base,
            "size_bytes": size,
            "kind": source.get("kind"),
            "staged_bytes": len(blob) if blob else 0,
        })
        if blob is None and bank == "result" and obj in read_objects:
            #: Declared zeros, and something reads it: say so explicitly rather
            #: than inheriting the bank's poison.
            blob = bytes(size)
        if blob and bank in staged:
            #: base is already a halfword index for the weight window
            staged[bank].append((base, blob, elem if bank != "weight" else 0))

    index_words = max(cursors["index"], 1)
    source_words = max(cursors["source"], 1)
    result_words = max(cursors["result"], 1)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    #: The request's token ids.  Architecturally these are host input, not
    #: deployment content: the object declares zeros and the host writes them
    #: before the run.  One id per index-bank word, at consecutive offsets from
    #: the object's base, which is what the embed lookup's rank-1 extent-1 index
    #: view resolves over.
    prompt_tokens: list[int] = []
    if args.prompt_tokens:
        spec = args.prompt_tokens
        candidate = Path(spec)
        if candidate.is_file():
            body = json.loads(candidate.read_text())
            results = body.get("results") or {}
            if len(results) != 1:
                raise SystemExit(
                    f"{spec}: expected one result, found {sorted(results)}"
                )
            record = next(iter(results.values()))
            prompt_tokens = [int(t) for t in record["prompt_token_ids"]]
        else:
            prompt_tokens = [int(t) for t in spec.split(",") if t.strip()]
    if prompt_tokens:
        token_obj = token_id_object(table)
        entry = next(e for e in plan if e["object_id"] == token_obj)
        if entry["bank"] != "index":
            raise SystemExit(
                f"token-id object {token_obj} is in the {entry['bank']} bank, not index"
            )
        if len(prompt_tokens) > entry["elements"]:
            raise SystemExit(
                f"{len(prompt_tokens)} token ids do not fit object {token_obj}'s "
                f"{entry['elements']} elements"
            )
        staged["index"].append((
            entry["base"],
            b"".join(int(t).to_bytes(4, "little") for t in prompt_tokens),
            4,
        ))
        print(f"  prompt tokens      {len(prompt_tokens)} planted in object "
              f"{token_obj} at index-bank word {entry['base']}")

    (args.out_dir / "p3_index.hex").write_text(
        sparse_hex(staged["index"], index_words))
    (args.out_dir / "p3_source.hex").write_text(
        sparse_hex(staged["source"], source_words))
    #: Always written, even when empty: the top's $readmemh needs the file to
    #: exist, and an empty image simply leaves the bank at zero.
    (args.out_dir / "p3_result.hex").write_text(
        sparse_hex(staged["result"], result_words))

    #: the weight window is a flat byte image indexed in halfwords
    weight_bytes = bytearray()
    for half_base, blob, _ in sorted(staged["weight"]):
        start = half_base * 2
        end = start + len(blob)
        if len(weight_bytes) < end:
            weight_bytes.extend(bytes(end - len(weight_bytes)))
        if any(weight_bytes[start:end]):
            raise SystemExit(
                f"weight window: halfword {half_base} overlaps an object already "
                f"placed there"
            )
        weight_bytes[start:end] = blob
    (args.out_dir / "p3_matmul_weight.bin").write_bytes(bytes(weight_bytes))

    header = (args.deployment / "program.bin").read_bytes()[:256]
    config = {
        "instruction_count": int.from_bytes(header[16:20], "little"),
        "entrypoint_count": int.from_bytes(header[20:24], "little"),
        "max_retired_work": int.from_bytes(header[184:192], "little"),
        "descriptor_count": len(table),
        "state_count": len(table.ids_of_type(T.STATE)),
        "index_words": index_words,
        "source_words": source_words,
        "result_words": result_words,
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
        f"index_words {index_words}",
        f"source_words {source_words}",
        f"result_words {result_words}",
        f"weight_bytes {len(weight_bytes)}",
    ]
    #: The KV cache geometry the bridge admits a scatter against.  It is not a
    #: host choice: the cache object's own view states how many rows it holds,
    #: so read it off the scatter's destination rather than passing a number
    #: down and hoping the two agree.  cfg_kv_plane_rows left at zero makes
    #: mapped_context_ok reject every scatter and every attention.
    kv_plane_rows = 0
    for op_id in table.ids_of_type(T.OPERATOR):
        payload = table[op_id].payload
        if (payload["engine_family"] == int(Major.DMA)
                and payload["engine_sub"] == int(Dma.SCATTER)):
            out = payload["output_view_0"]
            if out != NO_OBJECT:
                rows = int(table[out].payload["dim0"])
                if kv_plane_rows and rows != kv_plane_rows:
                    raise SystemExit(
                        f"scatter destinations disagree on KV plane rows: "
                        f"{kv_plane_rows} then {rows}"
                    )
                kv_plane_rows = rows
    if not kv_plane_rows:
        raise SystemExit("no DMA.SCATTER destination found; cannot state KV plane rows")
    lines.append(f"kv_plane_rows {kv_plane_rows}")
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
    for name, count in (("index", index_words), ("source", source_words),
                        ("result", result_words)):
        print(f"  {name + ' bank':<18} {count:>12,} words  "
              f"({count * 4 / 1e6:.1f} MB)")
    print(f"  weight image       {len(weight_bytes):,} bytes")
    print(f"  instructions       {config['instruction_count']}")
    print(f"  descriptors        {config['descriptor_count']}")
    print(f"  state descriptors  {config['state_count']}")
    print(f"  wrote {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
