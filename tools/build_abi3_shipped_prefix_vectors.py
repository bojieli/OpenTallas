#!/usr/bin/env python3
"""Build the smallest honest shipped-program sequencer/engine RTL witness.

The four shipped ABI 3.0 decode entrypoints all begin with a bounded sequence
that the RTL can execute without pretending an unsupported model operator
exists: Qwen has one real ``DMA.GATHER`` and DeepSeek has two.  The next engine
instruction is ``TENSOR.EMBED_LOOKUP``, for which this RTL has no datapath.

This generator retains those exact program and descriptor identities, resolves
their real views for the same 16-token decode request used by the deployment
campaign, materialises the generated RoPE source objects through the normal
``MemoryObject`` integrity boundary, and emits compact verification-bank data.
The hardware must copy all 1,024 authentic FP32 words and then fail closed at
the exact first unsupported instruction.  It does not claim a whole model,
prefill, token selection, or decoding result.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.abi3.constants import (  # noqa: E402
    Control,
    Dma,
    DType,
    Major,
    NO_ID,
    Tensor,
)
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import (  # noqa: E402
    ExtendedDescriptorType,
    SelectorKind,
    Symbol,
)
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.sim.memory import MemoryObject, ViewResolver  # noqa: E402
from tools.build_abi3_deployment_rtl_vectors import (  # noqa: E402
    CASE_STRIDE as DEPLOYMENT_CASE_STRIDE,
    TARGETS,
    certified_deployment_identity,
)


OUTPUT_DIR = ROOT / "testdata/compiler/abi3_shipped_prefix"
DEPLOYMENT_VECTOR_DIR = ROOT / "testdata/compiler/abi3_deployment"
DEPLOYMENT_VECTOR_JSON = (
    DEPLOYMENT_VECTOR_DIR / "abi3_deployment_rtl_vectors.json"
)

VECTOR_SCHEMA = "opentallas.rtl.abi3_shipped_prefix_vectors.v1"
CASE_STRIDE = 32
META_WORDS = 8
INDEX_WORDS = 64
SOURCE_WORDS = 32768
RESULT_WORDS = 2048
PROMPT_TOKENS = 16
INDEX_VALUE = 16
EXACT_INDEX_SELECT = hashlib.sha256(b"exact_index_select_v1").digest()

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
    "p3_meta.hex",
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hex_lines(
    values: list[int], width: int = 32, total: int | None = None
) -> str:
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
) -> list[dict[str, Any]]:
    operator = deployment.table.get(
        operator_id, ExtendedDescriptorType.OPERATOR
    )
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
    source = deployment.objects[object_id]
    if source.kind != "generated":
        raise SystemExit(
            f"source object {object_id} is {source.kind}, expected generated"
        )
    key = (source.digest, index, trailing)
    row = cache.get(key)
    if row is None:
        memory = MemoryObject(
            object_id,
            deployment.table[object_id],
            source,
            None,
            mappings={},
            verified_segments=set(),
        )
        row = memory.read(index * trailing * 4, trailing * 4)
        cache[key] = row
        del memory
        gc.collect()
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


def build(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)
    args.output.mkdir(parents=True, exist_ok=True)

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
    records: list[dict[str, Any]] = []
    row_cache: dict[tuple[str, int, int], bytes] = {}
    total_launches = 0
    total_views = 0

    for target_index, target in enumerate(TARGETS):
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
            item
            for item in deployment.entrypoints
            if int(item["entrypoint_id"]) == 1
        )
        entry_pc = int(entry["first_instruction"])
        if entry_pc != int(source_case[7]):
            raise SystemExit(f"{target.key}: decode entry PC changed")

        symbols = {
            int(key): int(value)
            for key, value in deployment_case["symbols"].items()
        }
        if symbols[int(Symbol.POSITION_START)] != INDEX_VALUE:
            raise SystemExit(
                f"{target.key}: decode position is not {INDEX_VALUE}"
            )

        loops: dict[int, int] = {}
        gathers: list[dict[str, Any]] = []
        prefix_views: list[dict[str, Any]] = []
        fetched = retired = issued = loop_iterations = signals = 0
        unsupported: dict[str, int] | None = None
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
                    if trip != 1:
                        raise SystemExit(
                            f"{target.key}: prefix loop {loop_id} has {trip} trips"
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
                deployment, int(instruction.descriptor_id), loops, symbols
            )
            prefix_views.extend({"pc": pc, **view} for view in resolved)
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
                    or output_view["dims"]
                    != [1, int(source_view["dims"][1])]
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
                        "_row_words": row_words,
                    }
                )
                if int(instruction.signal_event_id) != NO_ID:
                    signals += 1
                retired += 1
                pc += 1
                continue

            if major == int(Major.TENSOR) and sub == int(Tensor.EMBED_LOOKUP):
                unsupported = {
                    "pc": pc,
                    "family": major,
                    "sub": sub,
                    "descriptor_id": int(instruction.descriptor_id),
                    "trap_class": 4,
                }
                break
            raise SystemExit(
                f"{target.key}: first unsupported opcode is {major:#x}.{sub:#x}"
            )

        if unsupported is None:
            raise SystemExit(f"{target.key}: no fail-closed prefix boundary")
        expected_gathers = 1 if target_index < 2 else 2
        if len(gathers) != expected_gathers:
            raise SystemExit(
                f"{target.key}: expected {expected_gathers} gathers, found "
                f"{len(gathers)}"
            )
        trailing_values = {int(g["source_view"]["dims"][1]) for g in gathers}
        if len(trailing_values) != 1:
            raise SystemExit(f"{target.key}: prefix gather widths differ")
        trailing = trailing_values.pop()

        index_base = len(index_words)
        source_base = len(source_words)
        output_base = len(expected_words)
        source_stride = (INDEX_VALUE + 1) * trailing
        for launch, gather in enumerate(gathers):
            index_words.append(INDEX_VALUE)
            want_source_cursor = source_base + launch * source_stride
            if len(source_words) != want_source_cursor:
                raise SystemExit("source-bank cursor drift")
            source_words.extend([0] * (INDEX_VALUE * trailing))
            source_words.extend(gather.pop("_row_words"))
            expected_words.extend(
                source_words[-trailing:]
            )

        state_count = int(source_case[34])
        if state_count != 0:
            raise SystemExit(f"{target.key}: production profile contains STATE")
        expected_fault_pc = 4 if target_index < 2 else 7
        expected_counts = {
            "fetched": 5 if target_index < 2 else 8,
            "retired": 4 if target_index < 2 else 7,
            "issued": 2 if target_index < 2 else 3,
            "loop_iterations": 1 if target_index < 2 else 2,
            "signals": expected_gathers,
            "views": 6 if target_index < 2 else 9,
        }
        observed_counts = {
            "fetched": fetched,
            "retired": retired,
            "issued": issued,
            "loop_iterations": loop_iterations,
            "signals": signals,
            "views": len(prefix_views),
        }
        if unsupported["pc"] != expected_fault_pc:
            raise SystemExit(f"{target.key}: first unsupported PC changed")
        if observed_counts != expected_counts:
            raise SystemExit(
                f"{target.key}: prefix counts {observed_counts}, expected "
                f"{expected_counts}"
            )

        words = [
            int(source_case[0]),       # deployed program-image base
            int(source_case[1]),       # instruction count
            int(source_case[2]),       # descriptor-image base
            int(source_case[3]),       # descriptor count
            int(source_case[4]),       # symbol-image base
            int(source_case[5]),       # symbol bound mask
            entry_pc,
            int(source_case[8]),       # max retired work, low
            int(source_case[9]),       # max retired work, high
            state_count,
            index_base,
            source_base,
            source_stride,
            output_base,
            len(gathers),
            len(gathers) * trailing,
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
            trailing,
            target_index,
            1,                         # one capability response
            0,                         # descriptor/engine faults
            len(issue_words) // 4,     # expected response-stream base
        ]
        if len(words) != CASE_STRIDE:
            raise SystemExit("internal case-record length error")
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
                (unsupported["family"] << 8) | unsupported["sub"],
                unsupported["descriptor_id"],
                unsupported["pc"],
                unsupported["trap_class"],
            ]
        )
        total_launches += len(gathers)
        total_views += expected_counts["views"]
        records.append(
            {
                "name": case_name,
                "deployment": target.key,
                "deployment_sha256": deployment_sha,
                "deployment_identity_evidence": expected_identity.record(),
                "input_deployment_vector_case": deployment_case_index,
                "request": {
                    "entrypoint_id": 1,
                    "phase": "decode",
                    "prompt_tokens": PROMPT_TOKENS,
                    "position_start": INDEX_VALUE,
                    "symbols": {str(k): v for k, v in sorted(symbols.items())},
                },
                "bank_mapping": {
                    "index_base": index_base,
                    "source_base": source_base,
                    "source_launch_stride": source_stride,
                    "output_base": output_base,
                },
                "expected": {
                    **expected_counts,
                    "real_engine_launches": len(gathers),
                    "result_words": len(gathers) * trailing,
                    "trap_class": 4,
                    "first_fault_instruction": unsupported["pc"],
                    "complete": False,
                    "state_compat": 0,
                },
                "supported_prefix": [
                    {key: value for key, value in gather.items()}
                    for gather in gathers
                ],
                "first_unsupported": unsupported,
                "resolved_prefix_views": prefix_views,
            }
        )

    if total_launches != 6 or len(expected_words) != 1024:
        raise SystemExit(
            f"witness depth changed: launches={total_launches}, "
            f"words={len(expected_words)}"
        )
    files = {
        "p3_case.hex": _hex_lines(case_words),
        "p3_issue.hex": _hex_lines(issue_words),
        "p3_index.hex": _hex_lines(index_words, total=INDEX_WORDS),
        "p3_source.hex": _hex_lines(source_words, total=SOURCE_WORDS),
        "p3_expect.hex": _hex_lines(expected_words),
        "p3_meta.hex": _hex_lines(
            [
                len(records),
                total_launches,
                len(expected_words),
                total_views,
                CASE_STRIDE,
                INDEX_WORDS,
                SOURCE_WORDS,
                RESULT_WORDS,
            ]
        ),
    }
    for name, payload in files.items():
        (args.output / name).write_text(payload, encoding="ascii")

    marker = (
        "PASS: ABI3 shipped-prefix engine integration "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(expected_words)} capability_faults={len(records)}"
    )
    summary = {
        "schema": VECTOR_SCHEMA,
        "abi": {"major": 3, "minor": 0},
        "state_compat": 0,
        "request_scope": {
            "phase": "decode",
            "prompt_tokens": PROMPT_TOKENS,
            "position_start": INDEX_VALUE,
        },
        "claim": (
            "exact shipped decode-program prefixes: six real DMA.GATHER engine "
            "launches copy 1,024 authentic generated RoPE words, after which "
            "the first TENSOR.EMBED_LOOKUP fails closed with CAPABILITY; this "
            "is not a whole-model, prefill, token-selection, or decoding claim"
        ),
        "supported_profile": (
            "dense one-index FP32 DMA.GATHER, U32 resolved index view, matching "
            "dense output, unscaled views, no auxiliary operands, and exact "
            "SHA-256 binding of exact_index_select_v1"
        ),
        "unsupported_policy": (
            "every other family/subopcode returns CAPABILITY before any engine "
            "launch, result write, retirement, or signal publication"
        ),
        "case_count": len(records),
        "real_engine_launch_count": total_launches,
        "result_word_count": len(expected_words),
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
        "cases": records,
    }
    (args.output / "abi3_shipped_prefix_vectors.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "abi3 shipped-prefix vectors: "
        f"cases={len(records)} launches={total_launches} "
        f"words={len(expected_words)} views={total_views}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
