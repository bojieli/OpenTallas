#!/usr/bin/env python3
"""Do the shipped manifest's current-source claims still hold?

``configs/abi3/shipped_deployments.json`` registers four deployments, all
``pin_kind: frozen_evidence``.  Each pins the frozen bundle's digest AND
asserts a second one, ``current_source_deployment_sha256``: what re-lowering
from source would produce today.  That second field is an assertion about the
compiler, and it was measured once -- ``current_source_measured_at_commit:
58ce25b`` -- and never re-checked.

It is the load-bearing half.  The frozen digest says what the evidence was
taken against; the current-source digest is what tells a reader whether the
divergence is understood or has simply drifted further.  An assertion nobody
re-runs is exactly the kind of claim this repository refuses elsewhere.

This re-lowers all four from the manifest's own ``build_command`` and compares.
It changes nothing.

One trap, worth naming
----------------------
Each ``build_command`` writes to that registration's FROZEN ROOT -- running
them as written would overwrite the evidence they exist to describe, and one of
those roots is bound by ``abi3_g1a_operator_equivalence.json``, on terminal
gate G1's critical path.  Every build here is redirected to a scratch
directory and the frozen roots are never touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "configs/abi3/shipped_deployments.json"
DEFAULT_OUTPUT = ROOT / "results/derived/shipped_manifest_current_source_audit.json"


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


def rebuild(registration: dict[str, Any], into: Path) -> dict[str, Any]:
    from runtime.abi3.deployment import Deployment

    command = list(registration["build_command"])
    target = into / registration["registration_id"]
    redirected = False
    for flag in ("--output", "--out"):
        if flag in command:
            command[command.index(flag) + 1] = str(target)
            redirected = True
    if not redirected:
        return {
            "rebuilt": False,
            "why": "build_command names no output flag to redirect",
        }
    proc = subprocess.run(
        ["python3", *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=3600,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    if proc.returncode != 0 or not (target / "deployment.json").is_file():
        return {
            "rebuilt": False,
            "returncode": proc.returncode,
            "stderr_tail": (proc.stderr or "")[-300:],
        }
    return {
        "rebuilt": True,
        "deployment_sha256": Deployment.read(target).deployment_digest.hex(),
        "command": " ".join(shlex.quote(part) for part in command),
        "redirected_from": registration.get("root"),
    }


def build(work: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text())
    rows: list[dict[str, Any]] = []
    for registration in manifest.get("registrations", []):
        claim = registration.get("current_source_deployment_sha256")
        result = rebuild(registration, work)
        observed = result.get("deployment_sha256")
        rows.append(
            {
                "registration_id": registration.get("registration_id"),
                "pin_kind": registration.get("pin_kind"),
                "frozen_deployment_sha256": registration.get("deployment_sha256"),
                "claimed_current_source_sha256": claim,
                "rebuilt_sha256": observed,
                "claim_holds": bool(observed) and observed == claim,
                "claim_measured_at_commit": registration.get(
                    "current_source_measured_at_commit"
                ),
                "rebuild": {
                    key: value
                    for key, value in result.items()
                    if key != "deployment_sha256"
                },
            }
        )
    holding = [row for row in rows if row["claim_holds"]]
    return {
        "schema": "opentallas.derived.shipped_manifest_current_source.v1",
        "generated_by": "tools/audit_shipped_manifest_current_source.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "manifest": str(MANIFEST.relative_to(ROOT)),
        "manifest_sha256": sha256(MANIFEST),
        "question": (
            "does re-lowering each registration from source reproduce the "
            "current_source_deployment_sha256 the manifest asserts?"
        ),
        "registrations": len(rows),
        "claims_holding": len(holding),
        "claims_broken": len(rows) - len(holding),
        "answer": (
            "yes, all of them" if len(holding) == len(rows) else "no, see rows"
        ),
        "rows": rows,
        "why_this_was_worth_running": (
            "the claims were measured once, at 58ce25b, and never re-checked.  "
            "An assertion about what the compiler would produce, that nobody "
            "re-runs, is the kind of claim this repository refuses elsewhere"
        ),
        "refusals": [
            {
                "id": "frozen-roots-untouched",
                "what": (
                    "every build was redirected to scratch; no frozen root was "
                    "written"
                ),
                "why": (
                    "each build_command names that registration's own frozen "
                    "root as its output, so running the manifest's commands as "
                    "written would overwrite the evidence they describe -- and "
                    "one of those roots is bound by "
                    "abi3_g1a_operator_equivalence.json, on gate G1's critical "
                    "path"
                ),
            },
            {
                "id": "not-a-revalidation-of-the-frozen-evidence",
                "what": (
                    "this says nothing about whether the frozen bundles are "
                    "still the right evidence"
                ),
                "why": (
                    "it checks only the second field.  The frozen digests "
                    "differ from current source by design, which is what "
                    "frozen_evidence means"
                ),
            },
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="manifest-verify-") as name:
        body = build(Path(name))
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"
    print(
        f"  {body['claims_holding']} of {body['registrations']} current-source "
        f"claims hold ({body['answer']})"
    )
    for row in body["rows"]:
        mark = "holds " if row["claim_holds"] else "BROKEN"
        print(
            f"    {mark}  {str(row['registration_id']):<38} "
            f"{str(row['claimed_current_source_sha256'])[:16]}"
        )
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
