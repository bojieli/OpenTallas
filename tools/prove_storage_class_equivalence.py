#!/usr/bin/env python3
"""Prove that a ROM and an HBM deployment differ only in storage class.

The whole ROM-versus-HBM comparison rests on one property: for the same model,
the two backends must produce the same *program* and differ only in where the
immutable weights live. If anything else differed -- one operand view, one
numeric profile, one schedule -- a measured difference between the two targets
would be unattributable, and the comparison would be measuring the compiler
rather than the memory technology.

This tool asserts it mechanically rather than by inspection, by building the
same graph twice through one backend with only the weight storage class
changed, and reporting exactly what differs.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import StorageClass  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402

PRODUCTS = {
    "qwen3": (
        "compiler.backends.rom.qwen3",
        "build_qwen3_rom_deployment",
        "qwen3_rom_capability",
    ),
    "deepseek_v4": (
        "compiler.backends.rom.deepseek_v4",
        "build_deepseek_v4_rom_deployment",
        "deepseek_v4_rom_capability",
    ),
}


def prove(graph: KernelGraph, product: str) -> dict[str, Any]:
    import importlib

    module_name, builder_name, capability_name = PRODUCTS[product]
    module = importlib.import_module(module_name)
    build = getattr(module, builder_name)
    capability = getattr(module, capability_name)()

    rom, _ = build(graph, capability=capability, weight_storage_class=StorageClass.ROM)
    hbm, _ = build(graph, capability=capability, weight_storage_class=StorageClass.HBM)

    rom_header, rom_body = split_program(rom.program)
    hbm_header, hbm_body = split_program(hbm.program)

    table_rom = {d.descriptor_id: d for d in rom.table.descriptors()}
    table_hbm = {d.descriptor_id: d for d in hbm.table.descriptors()}
    shared = sorted(set(table_rom) & set(table_hbm))
    differing = [i for i in shared if table_rom[i].encode() != table_hbm[i].encode()]

    transitions: Counter[str] = Counter()
    non_storage: list[dict[str, Any]] = []
    for index in differing:
        left, right = table_rom[index], table_hbm[index]
        if left.type_name != "MEMORY_OBJECT":
            non_storage.append({"descriptor_id": index, "type": left.type_name})
            continue
        payload_left = dict(left.payload)
        payload_right = dict(right.payload)
        moved = payload_left.pop("storage_class"), payload_right.pop("storage_class")
        transitions[
            f"{StorageClass(moved[0]).name}->{StorageClass(moved[1]).name}"
        ] += 1
        # Permissions may legitimately differ with the storage class; nothing
        # else in the payload may.
        payload_left.pop("integrity_mode", None)
        payload_right.pop("integrity_mode", None)
        if payload_left != payload_right:
            non_storage.append(
                {
                    "descriptor_id": index,
                    "type": left.type_name,
                    "reason": "memory object differs beyond its storage class",
                }
            )

    return {
        "schema": "opentallas.abi3.storage_class_equivalence.v1",
        "product": product,
        "model_id": graph.model_id,
        "graph_id": graph.graph_id,
        "instruction_count": {
            "rom": rom_header.instruction_count,
            "hbm": hbm_header.instruction_count,
        },
        "instruction_body_identical": rom_body == hbm_body,
        "decoded_instructions_equal": decode_body(rom_body) == decode_body(hbm_body),
        "descriptor_count": {"rom": len(table_rom), "hbm": len(table_hbm)},
        "descriptors_only_in_one_build": {
            "rom": sorted(set(table_rom) - set(table_hbm)),
            "hbm": sorted(set(table_hbm) - set(table_rom)),
        },
        "differing_descriptor_count": len(differing),
        "differing_by_type": dict(Counter(table_rom[i].type_name for i in differing)),
        "storage_class_transitions": dict(transitions),
        "differences_beyond_storage_class": non_storage,
        "admitted": {
            "rom": verify_deployment(rom, capability).admitted,
            "hbm": verify_deployment(hbm, capability).admitted,
        },
        "holds": (
            rom_body == hbm_body
            and not non_storage
            and not (set(table_rom) ^ set(table_hbm))
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, required=True)
    parser.add_argument("--product", choices=sorted(PRODUCTS), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force", file=sys.stderr)
        return 1

    graph = KernelGraph.read(args.ir)
    body = prove(graph, args.product)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json(body))

    print(f"product              {body['product']}")
    print(f"instructions         rom {body['instruction_count']['rom']}  "
          f"hbm {body['instruction_count']['hbm']}")
    print(f"instruction body     identical={body['instruction_body_identical']}")
    print(f"descriptors          {body['descriptor_count']['rom']} each, "
          f"{body['differing_descriptor_count']} differing")
    print(f"differing by type    {body['differing_by_type']}")
    print(f"transitions          {body['storage_class_transitions']}")
    print(f"beyond storage class {len(body['differences_beyond_storage_class'])}")
    print(f"HOLDS                {body['holds']}")
    return 0 if body["holds"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
