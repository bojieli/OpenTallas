#!/usr/bin/env python3
"""One bundle path, three generations, and committed evidence on all three.

``build/abi3/deepseek-v4-flash-rom`` is a single path that eighteen committed
artifacts bind by digest -- and they do not agree on which bundle it holds.
Three distinct deployment digests are pinned across the tree, and only one of
them is reproducible from source at HEAD.

This was found by re-running the four campaigns whose ``--check`` reported a
stale source hash.  All four refused to run, correctly, and their refusals name
this:

    DeepSeek ROM deployment is a187b4d7..., expected 34ca189c...
    deepseek-v4-flash-hbm-cluster PC 14 does not name the expected MHC
    current HC_PRE target site drift: deepseek-v4-flash-hbm-cluster

The generations
---------------
``3a24098691...`` -- REPRODUCIBLE.  A rebuild from
``build/ir-v3/deepseek-v4-flash-0731/kernel_ir.v3.json`` against
``rom_deepseek_v4.json`` at HEAD produces exactly this digest, with capability
``5abf26b4...``.  Bound by ``rom_schedule_checks.json``, the shipped-prefix
campaign, and both committed vector trees.

``a187b4d7...`` -- what is ON DISK now.  Same capability digest.  Bound by the
deployment campaign, the vehicle reachability and entry probes, and -- this is
the one that matters -- ``abi3_g1a_operator_equivalence.json``.

``34ca189c...`` -- the OLDEST, and the most widely bound: ten artifacts,
including four ``testdata/rtl/*/index.json`` vector sets, four campaign
records, the multicast vectors, and a hardcoded ``EXPECTED_DEPLOYMENT``
constant in ``tools/build_a3_wafer_multicast_vectors.py``.

Why this is recorded rather than repaired
-----------------------------------------
The obvious repair is to install the reproducible rebuild at the bundle path.
That is wrong, and the reason is worth stating: it would stale the four
artifacts bound to ``a187b4d7``, one of which is G1a's, and G1a is on terminal
gate G1's critical path.  Trading a green rung for a tidy build directory is
not a repair.

The second obvious repair is to update the wafer builder's hardcoded constant
to whatever the rebuild produces.  That is the shape of gate-fitting: a pin
edited until it matches the artifact in front of it.  It might be defensible
here -- the committed deployment vectors independently agree with the rebuild,
which makes ``34ca189c`` the provable outlier -- but it is a deliberate
re-pinning of ten artifacts' worth of evidence and belongs in its own change
with its own campaign, not as a side effect of a sweep.

So the finding is the deliverable: most of the DeepSeek RTL evidence in this
repository is bound to deployments that no current source reproduces, and the
four campaigns that noticed are refusing to run rather than quietly re-pinning
themselves.  That refusal is the system working.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/derived/deepseek_rom_bundle_generations.json"

BUNDLE_PATH = "build/abi3/deepseek-v4-flash-rom"

GENERATIONS = {
    "3a24098691ec4ccb7e6ebc0732d787b6c1ec766840275b990a23bea32502e8b9": {
        "label": "reproducible-from-source-at-head",
        "note": (
            "a rebuild from the committed DeepSeek Kernel IR against "
            "rom_deepseek_v4.json produces exactly this digest"
        ),
    },
    "a187b4d7cae7a21b97068db583311c1b9fdcbdcb9f4fae5e88b05d4e05c7b723": {
        "label": "on-disk-now",
        "note": "what the bundle path currently holds; same capability digest",
    },
    "34ca189cd4082b21260c0c27920f6e46d821f6709003b84cacd86cd867ed3e42": {
        "label": "oldest-and-most-widely-bound",
        "note": (
            "hardcoded as EXPECTED_DEPLOYMENT in "
            "tools/build_a3_wafer_multicast_vectors.py"
        ),
    },
}

# The four campaigns whose --check reported a stale source hash, with the
# refusal each produced when re-run.
REFUSALS = {
    "rtl_a3_wafer_multicast_campaign": (
        "DeepSeek ROM deployment is a187b4d7..., expected 34ca189c..."
    ),
    "run_a3_hc_pre_t1_rtl_campaign": (
        "deepseek-v4-flash-hbm-cluster PC 14 does not name the expected MHC"
    ),
    "run_a3_mhc_pre_tile_rtl_campaign": (
        "deepseek-v4-flash-hbm-cluster PC 14 does not name the expected MHC"
    ),
    "run_a3_hc_softmax_sinkhorn20_rtl_campaign": (
        "current HC_PRE target site drift: deepseek-v4-flash-hbm-cluster"
    ),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
    }


def binders(digest: str) -> list[str]:
    """Every committed file that names this digest."""

    found: list[str] = []
    for root in ("results", "testdata", "tools", "configs", "docs"):
        base = ROOT / root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in {".json", ".py", ".md"}:
                continue
            try:
                if digest[:16] in path.read_text(errors="ignore"):
                    found.append(str(path.relative_to(ROOT)))
            except OSError:
                continue
    return sorted(found)


def build() -> dict[str, Any]:
    generations = []
    for digest, meta in GENERATIONS.items():
        bound = binders(digest)
        generations.append(
            {
                "deployment_sha256": digest,
                "label": meta["label"],
                "note": meta["note"],
                "committed_binders": bound,
                "binder_count": len(bound),
            }
        )
    generations.sort(key=lambda g: g["binder_count"], reverse=True)
    total = sum(g["binder_count"] for g in generations)
    reproducible = [
        g for g in generations if g["label"] == "reproducible-from-source-at-head"
    ]
    return {
        "schema": "opentallas.derived.deepseek_rom_bundle_generations.v1",
        "generated_by": "tools/audit_deepseek_rom_bundle_generations.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "bundle_path": BUNDLE_PATH,
        "question": (
            "do the artifacts that bind this bundle path agree on what it holds?"
        ),
        "answer": "no -- three distinct deployment digests are pinned",
        "generation_count": len(generations),
        "total_committed_binders": total,
        "generations": generations,
        "reproducible_generation": (
            reproducible[0]["deployment_sha256"] if reproducible else None
        ),
        "campaign_refusals": REFUSALS,
        "refusals": [
            {
                "id": "no-bundle-swap",
                "what": (
                    "the reproducible rebuild was NOT installed at the bundle "
                    "path"
                ),
                "why": (
                    "four artifacts bind the on-disk digest and one of them is "
                    "abi3_g1a_operator_equivalence.json, on terminal gate G1's "
                    "critical path.  Trading a green rung for a tidy build "
                    "directory is not a repair"
                ),
            },
            {
                "id": "no-pin-edit",
                "what": (
                    "the wafer builder's hardcoded EXPECTED_DEPLOYMENT was not "
                    "updated to match what the rebuild produces"
                ),
                "why": (
                    "that is a pin edited until it matches the artifact in "
                    "front of it.  It may well be right -- the committed "
                    "deployment vectors independently agree with the rebuild, "
                    "which makes the oldest generation the provable outlier -- "
                    "but it re-pins ten artifacts' worth of evidence and "
                    "belongs in its own change with its own campaign"
                ),
            },
        ],
        "what_the_refusals_mean": (
            "the four campaigns refused to run rather than re-pin themselves "
            "against whatever was on disk.  That is the source-currency "
            "governance working as designed: they would rather report nothing "
            "than report a measurement taken on a deployment they were not "
            "characterised against"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build()
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"
    print(f"{body['bundle_path']}: {body['answer']}")
    for gen in body["generations"]:
        print(
            f"  {gen['deployment_sha256'][:16]}  {gen['binder_count']:>2} binders  "
            f"{gen['label']}"
        )
    print(f"  total committed binders: {body['total_committed_binders']}")
    print(f"  campaigns refusing to run: {len(body['campaign_refusals'])}")
    for refusal in body["refusals"]:
        print(f"  refusal {refusal['id']}")

    if args.check:
        if not args.output.exists():
            print(f"{args.output} does not exist")
            return 1
        retained = json.loads(args.output.read_text())
        retained.pop("git", None)
        candidate = json.loads(rendered)
        candidate.pop("git", None)
        if retained != candidate:
            print(f"{args.output} does not match a fresh audit")
            return 1
        print(f"{args.output} reproduces (provenance excluded)")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered)
    print(f"wrote {args.output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
