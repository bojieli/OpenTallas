#!/usr/bin/env python3
"""Measure amendment AM-R1's landed half, and its bill.

Wire format section 12.21 makes two quantitative claims that a reader is
entitled to see re-derived rather than asserted:

*nothing already shipped moves*
    a capability that declares no ``fabric`` publishes no ``fabric`` key, so
    every committed capability record keeps the digest the committed evidence
    quotes for it, and every built deployment bound to one of those records is
    still admitted with the same named checks.

*the bill for the step that follows is this large*
    how many capability records, built bundles, committed artifacts and
    source-bound campaigns a re-emission would touch.

The digests are never typed in.  They are recomputed from the committed records
and compared against the digests committed evidence artifacts recorded when
they hashed the record they read, so a moved byte has nowhere to hide.

The cross-amendment comparison itself -- that the verifier's verdict on every
built bundle is byte-identical before and after AM-R1 -- needs a pre-amendment
tree and is therefore a session measurement made against a named baseline
commit, recorded here as ``baseline_comparison`` with that commit named, not as
something this tool can reproduce from one checkout.

Usage::

    python3 tools/check_amr1_topology_amendment.py --out results/abi3/amr1_topology_amendment.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from runtime.abi3.capability import Capability  # noqa: E402
from runtime.abi3.constants import NodeClass, ParticipantScope, TopologyClass  # noqa: E402
from runtime.abi3.deployment import Deployment  # noqa: E402
from runtime.abi3.verifier import Verifier  # noqa: E402

CAPABILITY_DIR = ROOT / "configs" / "hardware" / "abi3_capability"
BUNDLE_DIR = ROOT / "build" / "abi3"

#: The four sources AM-R1's landed half edits.  A campaign that hashes one of
#: them as a contract source records a digest that this amendment moves.
AMENDED_SOURCES = (
    "runtime/abi3/constants.py",
    "runtime/abi3/capability.py",
    "runtime/abi3/verifier.py",
    "runtime/sim/engines/link.py",
)


def _tracked(prefix: str) -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", prefix], cwd=ROOT, capture_output=True, text=True
    )
    return [line for line in out.stdout.split("\n") if line]


def _load_json(path: Path):
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _quoted_capability_digests() -> dict[str, sorted]:
    """(record path -> digests committed artifacts recorded for that record)."""
    found: dict[str, set[str]] = {}

    def walk(node) -> None:
        if isinstance(node, dict):
            path, sha = node.get("path"), node.get("sha256")
            if (
                isinstance(path, str)
                and isinstance(sha, str)
                and path.startswith("configs/hardware/abi3_capability/")
            ):
                found.setdefault(path, set()).add(sha)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for relative in _tracked("results"):
        if not relative.endswith(".json"):
            continue
        target = ROOT / relative
        if not target.exists() or target.stat().st_size > 40_000_000:
            continue
        body = _load_json(target)
        if body is not None:
            walk(body)
    return {path: sorted(shas) for path, shas in found.items()}


def _artifacts_quoting(digests: set[str]) -> list[str]:
    hits = []
    for relative in _tracked("results"):
        target = ROOT / relative
        if not target.exists() or target.stat().st_size > 40_000_000:
            continue
        try:
            text = target.read_text(errors="ignore")
        except Exception:
            continue
        if any(digest in text for digest in digests):
            hits.append(relative)
    return sorted(hits)


def _stale_source_bindings() -> dict:
    live = {
        source: hashlib.sha256((ROOT / source).read_bytes()).hexdigest()
        for source in AMENDED_SOURCES
    }
    recorded: dict[str, dict[str, str]] = {}

    def walk(node, relative: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in live and isinstance(value, str) and len(value) == 64:
                    recorded.setdefault(key, {}).setdefault(relative, value)
                if (
                    isinstance(value, dict)
                    and value.get("path") in live
                    and isinstance(value.get("sha256"), str)
                ):
                    recorded.setdefault(value["path"], {}).setdefault(
                        relative, value["sha256"]
                    )
                walk(value, relative)
        elif isinstance(node, list):
            for value in node:
                walk(value, relative)

    for relative in _tracked("results"):
        if not relative.endswith(".json"):
            continue
        target = ROOT / relative
        if not target.exists() or target.stat().st_size > 60_000_000:
            continue
        body = _load_json(target)
        if body is not None:
            walk(body, relative)

    per_source = {}
    every: set[str] = set()
    for source, hits in sorted(recorded.items()):
        stale = sorted(f for f, d in hits.items() if d != live[source])
        per_source[source] = {
            "recorded_in": len(hits),
            "stale_now": len(stale),
            "artifacts": sorted(hits),
        }
        every |= set(hits)
    return {
        "sources": per_source,
        "distinct_artifacts": sorted(every),
        "distinct_artifact_count": len(every),
    }


def _tools_hashing() -> dict[str, list[str]]:
    listed: dict[str, list[str]] = {source: [] for source in AMENDED_SOURCES}
    for relative in _tracked("tools"):
        if not relative.endswith(".py"):
            continue
        text = (ROOT / relative).read_text(errors="ignore")
        for source in AMENDED_SOURCES:
            if source in text:
                listed[source].append(relative)
    return {source: sorted(hits) for source, hits in listed.items()}


def build_report() -> dict:
    quoted = _quoted_capability_digests()

    records = []
    in_use: set[str] = set()
    for record in sorted(CAPABILITY_DIR.rglob("*.json")):
        relative = record.relative_to(ROOT).as_posix()
        capability = Capability.from_dict(json.loads(record.read_text()))
        body = capability.to_dict()
        entry = {
            "path": relative,
            "topology_class": TopologyClass(capability.topology_class).name,
            "max_nodes": int(capability.limits["max_nodes"]),
            "digest": capability.digest,
            "publishes_fabric_key": "fabric" in body,
            "quoted_by_committed_artifact": capability.digest
            in quoted.get(relative, []),
            "digests_committed_artifacts_recorded": quoted.get(relative, []),
        }
        if entry["quoted_by_committed_artifact"]:
            in_use.add(capability.digest)
        records.append(entry)

    by_digest = {entry["digest"]: entry for entry in records}
    bundles = []
    checks_compared = 0
    for bundle in sorted(p for p in BUNDLE_DIR.glob("*") if p.is_dir()):
        if not (bundle / "deployment.json").exists():
            continue
        row = {"bundle": bundle.name}
        try:
            deployment = Deployment.read(bundle)
        except Exception as exc:
            row["error"] = f"{type(exc).__name__}: {exc}"
            bundles.append(row)
            continue
        row["topology_class"] = TopologyClass(deployment.topology_class).name
        row["capability_digest"] = deployment.capability_digest
        match = by_digest.get(deployment.capability_digest)
        row["capability_record"] = match["path"] if match else None
        if match is None:
            bundles.append(row)
            continue
        capability = Capability.from_dict(
            json.loads((ROOT / match["path"]).read_text())
        )
        verifier = Verifier(deployment, capability)
        try:
            verifier.verify()
        except Exception:
            pass
        row["checks"] = len(verifier.checks)
        row["checks_failed"] = sorted(k for k, v in verifier.checks.items() if not v)
        checks_compared += len(verifier.checks)
        bundles.append(row)

    bound = [b for b in bundles if b.get("capability_record")]
    quoting = _artifacts_quoting(in_use)
    stale = _stale_source_bindings()
    tools = _tools_hashing()

    digest_stability_holds = all(
        (not entry["publishes_fabric_key"])
        and (
            entry["quoted_by_committed_artifact"]
            or not entry["digests_committed_artifacts_recorded"]
        )
        for entry in records
    )

    return {
        "schema": "opentallas.abi3.amr1_topology_amendment.v1",
        "amendment": "AM-R1",
        "defined_in": "docs/TENSOR_ACCELERATOR_ABI_3_WIRE_FORMAT.md section 12.21",
        "registry": {
            "topology_classes": {m.name: int(m) for m in TopologyClass},
            "node_classes": {m.name: int(m) for m in NodeClass},
            "participant_scopes": {m.name: int(m) for m in ParticipantScope},
        },
        "digest_stability": {
            "holds": digest_stability_holds,
            "rule": "a capability that declares no fabric publishes no fabric "
            "key, so its canonical bytes and therefore its digest do not move",
            "records_checked": len(records),
            "records_quoted_by_committed_evidence": sum(
                1 for e in records if e["quoted_by_committed_artifact"]
            ),
            "records": records,
        },
        "admission": {
            "bundles_present": len(bundles),
            "bundles_bound_to_a_committed_capability": len(bound),
            "checks_compared": checks_compared,
            "bundles_with_failing_checks": sorted(
                b["bundle"] for b in bound if b.get("checks_failed")
            ),
            "bundles": bundles,
        },
        "blast_radius": {
            "note": "nothing here is re-emitted by the landed half; this is the "
            "bill for the re-lowering step that follows it",
            "capability_records": len(records),
            "capability_digests_in_use": sorted(in_use),
            "committed_artifacts_quoting_those_digests": len(quoting),
            "artifacts": quoting,
            "tools_listing_an_amended_source": {
                source: len(hits) for source, hits in tools.items()
            },
            "tools": tools,
            "source_bound_evidence_now_stale": stale,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    report = build_report()
    text = json.dumps(report, indent=1, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text)
        print(f"wrote {args.out}")
    d = report["digest_stability"]
    a = report["admission"]
    b = report["blast_radius"]
    print(
        f"digest stability holds={d['holds']} over {d['records_checked']} records "
        f"({d['records_quoted_by_committed_evidence']} quoted by committed evidence)"
    )
    print(
        f"admission: {a['bundles_bound_to_a_committed_capability']} of "
        f"{a['bundles_present']} bundles, {a['checks_compared']} checks"
    )
    print(
        f"blast radius: {b['committed_artifacts_quoting_those_digests']} committed "
        f"artifacts quote a capability digest in use; "
        f"{b['source_bound_evidence_now_stale']['distinct_artifact_count']} record a "
        f"source digest this amendment moved"
    )
    return 0 if d["holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
