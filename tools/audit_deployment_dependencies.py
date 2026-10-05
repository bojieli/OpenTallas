#!/usr/bin/env python3
"""Audit serialized OPERATOR footprints for the four-range RTL contract.

This reads descriptors and manifests, never model payloads. Whole-object ranges
are conservative. A pass means overflow is identified and conservatively
protected by the reference policy, not that asynchronous RTL has been integrated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from runtime.abi3.dependence import compress_ranges, operator_whole_object_accesses  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.descriptors import ExtendedDescriptorType as T  # noqa: E402


def audit(root: Path) -> dict:
    d = Deployment.read(root)
    rows = []
    for op in d.table.descriptors():
        if op.descriptor_type != T.OPERATOR:
            continue
        accesses = operator_whole_object_accesses(d, op)
        footprint = compress_ranges(accesses)
        objects = sorted({r.object_id for r in accesses})
        mutable = [o for o in objects if d.table[o].permissions & 2]
        if footprint.wildcard:
            rows.append({"descriptor_id": op.descriptor_id, "family": op.payload["engine_family"],
                         "sub": op.payload["engine_sub"], "objects": objects, "mutable_objects": mutable,
                         "policy": "sticky_global_wildcard_until_completion"})
    return {"target_id": d.target_id, "descriptor_table_sha256": d.table.digest.hex(),
            "program_sha256": hashlib.sha256(d.program).hexdigest(),
            "overflow_operators": rows, "mutable_overflow_count": sum(len(r["mutable_objects"]) > 4 for r in rows),
            "rtl_integration_proven": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deployments", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = {"schema": "opentallas.deployment-dependence-audit.v1", "deployments": [audit(p) for p in args.deployments]}
    report["reference_sources"] = [{"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                   for p in [ROOT / "runtime/abi3/dependence.py", Path(__file__).resolve()]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    for d in report["deployments"]:
        print(f"{d['target_id']}: {len(d['overflow_operators'])} wildcard operations, "
              f"{d['mutable_overflow_count']} exceed four mutable objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
