#!/usr/bin/env python3
"""Publish the machine-readable ABI 3.0 layout records under ``spec/abi3/``.

Section 12 of the frozen wire format names these files as the normative field
tables for the typed descriptor payloads.  They are generated from the encoder
so that the specification and the implementation cannot drift apart silently:
if a layout changes, this file changes, and the conformance suite compares the
result against the document's own tables.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from runtime.abi3 import constants, descriptors, records  # noqa: E402
from runtime.abi3.capability import canonical_json  # noqa: E402
from runtime.abi3.layout import Layout  # noqa: E402


def layout_record(layout: Layout) -> dict:
    return {
        "name": layout.name,
        "size_bytes": layout.size,
        "crc_field": layout.crc_field,
        "fields": [
            {
                "name": field.name,
                "offset": field.offset,
                "size": field.size,
                "kind": field.kind,
                **(
                    {"constant_ascii": field.constant.decode("latin-1")}
                    if field.constant is not None
                    else {}
                ),
            }
            for field in layout.fields
        ],
    }


def enum_record(enum_type) -> dict:
    return {member.name: int(member) for member in enum_type}


def build() -> dict[str, dict]:
    fixed = {
        constants.DescriptorType(t).name
        if t in {int(m) for m in constants.DescriptorType}
        else descriptors.ExtendedDescriptorType(t).name: layout_record(layout)
        for t, layout in descriptors.PAYLOAD_LAYOUTS.items()
    }
    return {
        "spec/abi3/records.json": {
            "contract": "TA-ABI3-WIRE-1",
            "abi": {"major": constants.ABI_MAJOR, "minor": constants.ABI_MINOR},
            "program_header": layout_record(records.PROGRAM_HEADER),
            "instruction": layout_record(records.INSTRUCTION),
            "submission": layout_record(records.SUBMISSION),
            "completion": layout_record(records.COMPLETION),
            "descriptor_header": layout_record(descriptors.DESCRIPTOR_HEADER),
        },
        "spec/abi3/descriptor_payloads.json": {
            "contract": "TA-ABI3-WIRE-1",
            "type_version": {
                "major": descriptors.TYPE_MAJOR,
                "minor": descriptors.TYPE_MINOR,
            },
            "descriptor_types": enum_record(descriptors.ExtendedDescriptorType),
            "payloads": {
                descriptors.ExtendedDescriptorType(t).name: layout_record(layout)
                for t, layout in sorted(descriptors.PAYLOAD_LAYOUTS.items())
            },
            "entrypoint_table": {
                "header": layout_record(descriptors.ENTRYPOINT_HEADER_PAYLOAD),
                "entry": layout_record(descriptors.ENTRYPOINT_ENTRY),
            },
            "limits": {
                "max_rank": descriptors.MAX_RANK,
                "max_dynamic_terms": descriptors.MAX_DYNAMIC_TERMS,
                "max_wait_producers": descriptors.MAX_WAIT_PRODUCERS,
                "max_eos_tokens": descriptors.MAX_EOS_TOKENS,
                "max_counters_per_class": descriptors.MAX_COUNTERS_PER_CLASS,
                "max_loop_depth": descriptors.MAX_LOOP_DEPTH,
            },
        },
        "spec/abi3/registries.json": {
            "contract": "TA-ABI3-WIRE-1",
            "major_opcodes": enum_record(constants.Major),
            "subopcodes": {
                constants.Major(family).name: enum_record(enum_type)
                for family, enum_type in constants.SUBOPCODES.items()
            },
            "instruction_flags": enum_record(constants.InstructionFlag),
            "permissions": enum_record(constants.Permission),
            "host_opcodes": enum_record(constants.HostOpcode),
            "completion_status": enum_record(constants.CompletionStatus),
            "submission_flags": enum_record(constants.SubmissionFlag),
            "completion_flags": enum_record(constants.CompletionFlag),
            "trap_classes": enum_record(constants.TrapClass),
            "topology_classes": enum_record(constants.TopologyClass),
            "scopes": enum_record(constants.Scope),
            # Amendment A14: what a collective's participants are.  Distinct
            # from "scopes", which names a memory and event scope.
            "participant_scopes": enum_record(constants.ParticipantScope),
            "ordering": enum_record(constants.Ordering),
            "features": enum_record(constants.Feature),
            "counter_groups": enum_record(constants.CounterGroup),
            "dtypes": enum_record(constants.DType),
            "dtype_bits": {
                constants.DType(k).name: v for k, v in constants.DTYPE_BITS.items()
            },
            "storage_classes": enum_record(constants.StorageClass),
            "integrity_modes": enum_record(constants.IntegrityMode),
            "rounding_modes": enum_record(constants.RoundingMode),
            "reduction_orders": enum_record(constants.ReductionOrder),
            "state_classes": enum_record(constants.StateClass),
            "runtime_symbols": enum_record(descriptors.Symbol),
            "selector_kinds": enum_record(descriptors.SelectorKind),
            "predicate_kinds": enum_record(descriptors.PredicateKind),
            "comparisons": enum_record(descriptors.Comparison),
            "collective_ops": enum_record(descriptors.CollectiveOp),
            "layout_classes": enum_record(descriptors.LayoutClass),
            "selection_modes": enum_record(descriptors.SelectionMode),
            "signature_schemes": enum_record(descriptors.SignatureScheme),
            "phases": enum_record(descriptors.Phase),
            "eos_reasons": {
                name: getattr(records.EosReason, name)
                for name in (
                    "NONE",
                    "OFFICIAL_EOS",
                    "MAX_NEW_TOKENS",
                    "TERMINATED_BY_TRAP",
                    "HOST_BOUND",
                )
            },
        },
        "spec/abi3/counters.json": _counter_registry(),
        "spec/abi3/numeric_contract_union.json": _numeric_union(),
    }


def _numeric_union() -> dict:
    """The numeric-contract union the shared chip must implement.

    Derived from the published neutral graphs rather than hand-listed: a
    hand-listed union goes stale the moment an exporter adds an operation, and
    the failure mode is an admission error at the end of a long build.
    """
    from compiler.ir.v3.numeric import capability_union, default_graph_paths

    paths = default_graph_paths()
    body = capability_union(paths)
    body["derived_from"] = [str(p.relative_to(REPO)) for p in paths]
    return body


def _counter_registry() -> dict:
    from runtime.sim.counters import COUNTERS

    return {
        "contract": "TA-ABI3-WIRE-1",
        "rule": "unsigned 64-bit saturating with sticky overflow",
        "counters": {
            f"{cid:#010x}": {
                "name": name,
                "group": (cid >> 24),
                "event": cid & 0xFFFFFF,
            }
            for cid, name in sorted(COUNTERS.items())
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if files differ")
    args = parser.parse_args()
    drifted = []
    for relative, body in build().items():
        path = REPO / relative
        payload = canonical_json(body)
        if args.check:
            if not path.exists() or path.read_bytes() != payload:
                drifted.append(relative)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        print(f"wrote {relative} ({len(payload)} bytes)")
    if drifted:
        print("spec drift in: " + ", ".join(drifted), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
