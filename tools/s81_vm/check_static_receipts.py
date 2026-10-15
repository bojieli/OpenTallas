#!/usr/bin/env python3
"""Reuse counted, source-pinned VM component evidence without repeating a heavy run.
This verifier establishes component receipt identity only, never native-chip or
physical qualification. Any source, log, fixture or verdict mismatch fails.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re


def bound(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"receipt path leaves source tree: {relative}")
    return path


def check_hash(root, relative, expected):
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError(f"invalid SHA256: {relative}")
    path = bound(root, relative)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"SHA256 mismatch: {relative}")
    return path


def verify(root, manifest, gate, require_source=(), provenance=None, compiler_root=None):
    record = json.loads(bound(root, manifest).read_text())["gates"][gate]
    sources, logs = record["source_sha256"], record["log_sha256"]
    if not sources or not logs or not set(require_source) <= sources.keys():
        raise ValueError("missing required source or counted gate evidence")
    for path, digest in sources.items():
        check_hash(root, path, digest)
    positives = mutants = 0
    observations = []
    for path, digest in logs.items():
        text = check_hash(root, path, digest).read_text()
        positive = Path(path).stem.endswith("_base")
        verdict = "PASS" if positive else "FAIL"
        if not re.search(rf"(?m)^{verdict}$", text) or re.search(rf"(?m)^{'FAIL' if positive else 'PASS'}$", text):
            raise ValueError(f"missing or ambiguous expected verdict: {path}")
        if positive:
            counts = [int(n) for n in re.findall(r"(?:reads|writes|captures|drains|requests|restored|groups|checks)\s*(\d+)", text, re.I)]
            if not counts or max(counts) <= 0:
                raise ValueError(f"positive receipt has no actual observations: {path}")
            positives += 1
            observations.append(max(counts))
        else:
            if not re.search(r"bad\s*[1-9]\d*", text, re.I):
                raise ValueError(f"mutant has no observed mismatch count: {path}")
            mutants += 1
    if positives == 0 or mutants == 0:
        raise ValueError("both positive and observed mutant receipts are required")
    if provenance:
        if not compiler_root:
            raise ValueError("fixture provenance requires compiler itinerary directory")
        pp = bound(root, provenance)
        for layer, row in json.loads(pp.read_text()).items():
            check_hash(root, str(pp.parent.relative_to(root.resolve()) / f"{layer}.txt"), row["input_sha256"])
            digest = row.get("compiler_input_sha256", row.get("source_sha256"))
            check_hash(root, str(Path(compiler_root) / f"{layer}.json.gz"), digest)
    return dict(gate=gate, sources=len(sources), positives=positives, observed_mutants=mutants,
                minimum_positive_observations=min(observations), component_only=True,
                native_chip_qualified=False, physical_qualified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--manifest", default="results/rtl/s81_vm_static_1014/qualification_receipts.json")
    parser.add_argument("--gate", required=True)
    parser.add_argument("--require-source", action="append", default=[])
    parser.add_argument("--input-provenance")
    parser.add_argument("--compiler-itineraries")
    args = parser.parse_args()
    try:
        result = verify(args.root.resolve(), args.manifest, args.gate, args.require_source,
                        args.input_provenance, args.compiler_itineraries)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, f"STATIC_RECEIPT_FAIL {exc}\n")
    print("STATIC_RECEIPT_PASS " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
