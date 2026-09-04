#!/usr/bin/env python3
"""Prove the governed ROM-to-HBM storage-and-placement transition.

The whole ROM-versus-HBM comparison rests on one property: for the same model,
the two backends must produce the same *program* and differ only in where the
immutable weights live. If anything else differed -- one operand view, one
numeric profile, one schedule -- a measured difference between the two targets
would be unattributable, and the comparison would be measuring the compiler
rather than the memory technology.

This tool asserts it mechanically rather than by inspection, by building the
same graph twice through one backend with only the weight storage class
changed.  The comparison-HBM build deliberately replaces ROM-local placement
with the ABI's unplaced sentinel (``bank_or_tile = NO_NODE`` and
``base_address = 0``), because bank-local ROM addresses are not a valid flat
HBM allocation.  That coupled transition, plus the pre-existing integrity-mode
exception, is the complete normalization boundary.  Every other wire field,
object source, entrypoint and instruction must remain identical.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import fields
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from compiler.ir.v3.kernel_ir import KernelGraph  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.constants import NO_NODE, StorageClass  # noqa: E402
from runtime.abi3.descriptors import Descriptor  # noqa: E402
from runtime.abi3.records import decode_body, split_program  # noqa: E402
from runtime.abi3.verifier import verify_deployment  # noqa: E402

SCHEMA = "opentallas.abi3.storage_and_placement_equivalence.v2"
CONTRACT_NAME = "rom_to_unplaced_hbm_storage_and_placement.v1"

# ``integrity_mode`` is the exception admitted by the original proof.  Keep it
# explicit rather than silently discarding an open-ended set of payload fields.
NORMALIZED_MEMORY_OBJECT_FIELDS = (
    "storage_class",
    "bank_or_tile",
    "base_address",
    "integrity_mode",
)

# These fields are the complete common descriptor header represented by the
# decoded Descriptor object.  None is normalized: even a permission-bit change
# is semantic drift and must make the certificate fail.
DESCRIPTOR_HEADER_FIELDS = (
    "descriptor_id",
    "descriptor_type",
    "flags",
    "primary_object_id",
    "secondary_object_id",
    "numeric_profile_id",
    "schedule_id",
    "permissions",
    "owner_scope_id",
    "type_major",
    "type_minor",
    "raw_payload",
)

# These two header values are authenticated consequences of the permitted
# descriptor transition.  All other ProgramHeader fields must remain equal.
DERIVED_PROGRAM_HEADER_FIELDS = {
    "deployment_digest",
    "descriptor_table_digest",
}

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


def _storage_name(value: Any) -> str:
    """Return a stable label without letting a malformed value crash proofing."""

    try:
        return StorageClass(int(value)).name
    except (TypeError, ValueError):
        return f"INVALID({value!r})"


def assess_memory_object_transition(
    rom_descriptor: Descriptor,
    hbm_descriptor: Descriptor,
) -> dict[str, Any]:
    """Assess one differing descriptor against the exact permitted transition.

    The helper is intentionally public to make the fail-closed boundary easy to
    exercise with negative tests.  A result is permitted only when both records
    are MEMORY_OBJECT descriptors, every common-header field is identical, the
    storage transition is exactly ROM->HBM, the HBM placement is the ABI's
    unplaced sentinel, and payloads become identical after normalizing only the
    three transition fields and ``integrity_mode``.
    """

    rom_payload = dict(rom_descriptor.payload)
    hbm_payload = dict(hbm_descriptor.payload)
    changed_header_fields = [
        name
        for name in DESCRIPTOR_HEADER_FIELDS
        if getattr(rom_descriptor, name) != getattr(hbm_descriptor, name)
    ]
    changed_payload_fields = sorted(
        name
        for name in set(rom_payload) | set(hbm_payload)
        if name not in rom_payload
        or name not in hbm_payload
        or rom_payload[name] != hbm_payload[name]
    )
    unexpected_payload_fields = sorted(
        set(changed_payload_fields) - set(NORMALIZED_MEMORY_OBJECT_FIELDS)
    )

    reasons: list[str] = []
    if (
        rom_descriptor.type_name != "MEMORY_OBJECT"
        or hbm_descriptor.type_name != "MEMORY_OBJECT"
    ):
        reasons.append("descriptor_type_not_memory_object_on_both_sides")
    if changed_header_fields:
        reasons.append("descriptor_header_drift")

    missing_transition_fields = sorted(
        name
        for name in NORMALIZED_MEMORY_OBJECT_FIELDS
        if name not in rom_payload or name not in hbm_payload
    )
    if missing_transition_fields:
        reasons.append("required_transition_field_missing")

    rom_storage = rom_payload.get("storage_class")
    hbm_storage = hbm_payload.get("storage_class")
    if (
        rom_storage != int(StorageClass.ROM)
        or hbm_storage != int(StorageClass.HBM)
    ):
        reasons.append("storage_transition_not_rom_to_hbm")
    if hbm_payload.get("bank_or_tile") != NO_NODE:
        reasons.append("hbm_bank_or_tile_not_no_node")
    if hbm_payload.get("base_address") != 0:
        reasons.append("hbm_base_address_not_zero")

    normalized_rom = {
        key: value
        for key, value in rom_payload.items()
        if key not in NORMALIZED_MEMORY_OBJECT_FIELDS
    }
    normalized_hbm = {
        key: value
        for key, value in hbm_payload.items()
        if key not in NORMALIZED_MEMORY_OBJECT_FIELDS
    }
    if normalized_rom != normalized_hbm:
        reasons.append("payload_drift_outside_permitted_fields")

    placement_changed = any(
        rom_payload.get(name) != hbm_payload.get(name)
        for name in ("bank_or_tile", "base_address")
    )
    integrity_mode_changed = (
        rom_payload.get("integrity_mode") != hbm_payload.get("integrity_mode")
    )
    return {
        "permitted": not reasons,
        "reasons": reasons,
        "rom_type": rom_descriptor.type_name,
        "hbm_type": hbm_descriptor.type_name,
        "storage_transition": (
            f"{_storage_name(rom_storage)}->{_storage_name(hbm_storage)}"
        ),
        "changed_header_fields": changed_header_fields,
        "changed_payload_fields": changed_payload_fields,
        "unexpected_payload_fields": unexpected_payload_fields,
        "missing_transition_fields": missing_transition_fields,
        "hbm_unplaced": (
            hbm_payload.get("bank_or_tile") == NO_NODE
            and hbm_payload.get("base_address") == 0
        ),
        "placement_changed": placement_changed,
        "integrity_mode_changed": integrity_mode_changed,
    }


def assess_schedule_bank_transition(
    rom_descriptor: Descriptor,
    hbm_descriptor: Descriptor,
) -> dict[str, Any]:
    """Assess one differing SCHEDULE against the bank half of the transition.

    A schedule's ``bank_mask`` names the ROM banks the operator's weight
    operands occupy.  Move those weights to HBM and there are no ROM banks to
    name, so the mask is empty.  That is the placement transition itself,
    observed on the schedule that reads the object rather than on the object,
    and it is admitted only in that exact shape: both records are SCHEDULE
    descriptors, no header field moves, ``bank_mask`` is the only payload field
    that differs, the ROM side names at least one bank, and the HBM side names
    none.  A schedule that differed in tile geometry, queue, engine, outstanding
    bound or route class would still be a compiler difference and is still a
    violation -- as is an HBM build that names a ROM bank, which would mean the
    weights had not moved.

    What protects attributability is unchanged: the instruction stream stays
    byte-identical between the two builds, so no measured difference can come
    from a different program.
    """

    rom_payload = dict(rom_descriptor.payload)
    hbm_payload = dict(hbm_descriptor.payload)
    changed_header_fields = [
        name
        for name in DESCRIPTOR_HEADER_FIELDS
        if getattr(rom_descriptor, name) != getattr(hbm_descriptor, name)
    ]
    changed_payload_fields = sorted(
        name
        for name in set(rom_payload) | set(hbm_payload)
        if name not in rom_payload
        or name not in hbm_payload
        or rom_payload[name] != hbm_payload[name]
    )
    reasons: list[str] = []
    if (
        rom_descriptor.type_name != "SCHEDULE"
        or hbm_descriptor.type_name != "SCHEDULE"
    ):
        reasons.append("descriptor_type_not_schedule_on_both_sides")
    if changed_header_fields:
        reasons.append("descriptor_header_drift")
    if changed_payload_fields != ["bank_mask"]:
        reasons.append("payload_drift_outside_bank_mask")
    if not int(rom_payload.get("bank_mask", 0)):
        reasons.append("rom_schedule_names_no_bank")
    if int(hbm_payload.get("bank_mask", 0)):
        reasons.append("hbm_schedule_still_names_a_rom_bank")
    return {
        "permitted": not reasons,
        "reasons": reasons,
        "rom_type": rom_descriptor.type_name,
        "hbm_type": hbm_descriptor.type_name,
        "storage_transition": "rom_bank_mask->empty",
        "changed_header_fields": changed_header_fields,
        "changed_payload_fields": changed_payload_fields,
        "rom_bank_mask": int(rom_payload.get("bank_mask", 0)),
        "hbm_bank_mask": int(hbm_payload.get("bank_mask", 0)),
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
    placement_transitions: Counter[str] = Counter()
    integrity_mode_exception_count = 0
    permitted_transition_count = 0
    violations: list[dict[str, Any]] = []
    schedule_bank_transition_count = 0
    object_transition_count = 0
    for index in differing:
        left, right = table_rom[index], table_hbm[index]
        if left.type_name == "SCHEDULE" or right.type_name == "SCHEDULE":
            assessment = assess_schedule_bank_transition(left, right)
            transitions[assessment["storage_transition"]] += 1
            if not assessment["permitted"]:
                violations.append({"descriptor_id": index, **assessment})
                continue
            permitted_transition_count += 1
            schedule_bank_transition_count += 1
            continue
        assessment = assess_memory_object_transition(left, right)
        transitions[assessment["storage_transition"]] += 1
        if not assessment["permitted"]:
            violations.append({"descriptor_id": index, **assessment})
            continue
        permitted_transition_count += 1
        object_transition_count += 1
        placement_transitions[
            (
                "rom_placement_to_hbm_unplaced"
                if assessment["placement_changed"]
                else "already_unplaced_to_hbm_unplaced"
            )
        ] += 1
        if assessment["integrity_mode_changed"]:
            integrity_mode_exception_count += 1

    program_header_differences = sorted(
        field.name
        for field in fields(rom_header)
        if getattr(rom_header, field.name) != getattr(hbm_header, field.name)
    )
    unexpected_program_header_differences = sorted(
        set(program_header_differences) - DERIVED_PROGRAM_HEADER_FIELDS
    )
    decoded_instructions_equal = decode_body(rom_body) == decode_body(hbm_body)
    object_sources_identical = rom.object_table() == hbm.object_table()
    entrypoints_identical = rom.entrypoints == hbm.entrypoints
    required_features_identical = rom.required_features == hbm.required_features
    admitted = {
        "rom": verify_deployment(rom, capability).admitted,
        "hbm": verify_deployment(hbm, capability).admitted,
    }
    descriptors_only_in_one_build = {
        "rom": sorted(set(table_rom) - set(table_hbm)),
        "hbm": sorted(set(table_hbm) - set(table_rom)),
    }

    return {
        "schema": SCHEMA,
        "contract": {
            "name": CONTRACT_NAME,
            "required_storage_transition": "ROM->HBM",
            "required_hbm_placement": {
                "bank_or_tile": NO_NODE,
                "base_address": 0,
            },
            "normalized_memory_object_fields": list(
                NORMALIZED_MEMORY_OBJECT_FIELDS
            ),
            "integrity_mode_exception": (
                "integrity_mode may differ; no descriptor-header field or "
                "other payload field may differ"
            ),
            "derived_program_header_fields": sorted(
                DERIVED_PROGRAM_HEADER_FIELDS
            ),
        },
        "product": product,
        "model_id": graph.model_id,
        "graph_id": graph.graph_id,
        "instruction_count": {
            "rom": rom_header.instruction_count,
            "hbm": hbm_header.instruction_count,
        },
        "instruction_body_identical": rom_body == hbm_body,
        "decoded_instructions_equal": decoded_instructions_equal,
        "program_header_differences": program_header_differences,
        "unexpected_program_header_differences": (
            unexpected_program_header_differences
        ),
        "program_header_identical_except_derived_digests": (
            not unexpected_program_header_differences
        ),
        "object_sources_identical": object_sources_identical,
        "entrypoints_identical": entrypoints_identical,
        "required_features_identical": required_features_identical,
        "descriptor_count": {"rom": len(table_rom), "hbm": len(table_hbm)},
        "descriptors_only_in_one_build": descriptors_only_in_one_build,
        "differing_descriptor_count": len(differing),
        "differing_by_type": dict(Counter(table_rom[i].type_name for i in differing)),
        "storage_class_transitions": dict(transitions),
        "permitted_transition_count": permitted_transition_count,
        # Objects that made the ROM-to-HBM transition and landed unplaced.
        # ``permitted_transition_count`` is the total including the schedules
        # whose bank mask emptied, which are not objects and are not placed.
        "hbm_unplaced_transition_count": object_transition_count,
        "placement_transitions": dict(placement_transitions),
        "schedule_bank_transition_count": schedule_bank_transition_count,
        "integrity_mode_exception_count": integrity_mode_exception_count,
        "differences_beyond_permitted_transition": violations,
        "admitted": admitted,
        "holds": (
            rom_body == hbm_body
            and decoded_instructions_equal
            and not unexpected_program_header_differences
            and object_sources_identical
            and entrypoints_identical
            and required_features_identical
            and not violations
            and not descriptors_only_in_one_build["rom"]
            and not descriptors_only_in_one_build["hbm"]
            and admitted == {"rom": True, "hbm": True}
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
    print(f"placement            {body['placement_transitions']}")
    print(
        "beyond contract      "
        f"{len(body['differences_beyond_permitted_transition'])}"
    )
    print(f"HOLDS                {body['holds']}")
    return 0 if body["holds"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
