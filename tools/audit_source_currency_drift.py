#!/usr/bin/env python3
"""How much of the source-bound evidence still binds current sources.

This repository's governance rests on artifacts pinning the SHA-256 of every
source they were produced from: a campaign that binds a digest which no longer
matches is inadmissible, and several tools refuse to run rather than report a
measurement taken against sources they were not characterised on.  That
mechanism is thorough and it works -- four campaigns were observed refusing on
exactly this ground while this audit was being written.

It has also been outrun.  Of the artifacts under ``results/`` that pin a
``source_sha256`` map, the large majority no longer bind current sources.

This tool measures that, names the sources responsible, and separates drift
caused by recent work from drift accumulated earlier, so the number is
actionable rather than merely alarming.  It changes nothing.

What the measurement is
-----------------------
For every ``results/**/*.json`` carrying a ``source_sha256`` object, each entry
is re-hashed against the file on disk.  An artifact is DRIFTED if any pinned
source now hashes differently, and separately reports sources that no longer
exist at all.

Why this is not a list of bugs to fix one by one
------------------------------------------------
The dominant causes are a handful of widely-bound runtime and compiler files.
Editing one of them stales every artifact that names it, and the biggest are
named by a fifth of all pinning artifacts.  So drift is not a property of
individual campaigns that fell behind; it is what happens when broadly-bound
sources move and the campaigns that bind them are expensive to re-run.

The same effect makes DOCUMENTATION load-bearing in a way that is easy to
miss: artifacts bind ``docs/*.md`` too, so a one-sentence correction to a
design document stales every artifact that pins it.  That is not an argument
against correcting documents; it is an argument for knowing the cost before
doing it.

What this does NOT claim
------------------------
Drift is not wrongness.  A drifted artifact's measurements may be exactly
reproducible; what has lapsed is the guarantee that they were taken against
the sources now on disk.  Nothing here re-runs a campaign, and nothing here
should be read as saying a specific number is wrong.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "results/derived/source_currency_drift.json"

#: The commit this session began at, so drift it introduced can be separated
#: from drift it inherited.  Not a claim that everything after it is recent --
#: just the boundary the separation is drawn at.
SESSION_BASE = "221fe7d"


def sha256(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def git_state() -> dict[str, Any]:
    def run(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
        ).stdout.strip()

    return {
        "commit": run("rev-parse", "HEAD") or None,
        "worktree_dirty": bool(run("status", "--porcelain")),
    }


def changed_since(base: str) -> set[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", f"{base}..HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    return {line.strip() for line in out.splitlines() if line.strip()}


def survey() -> dict[str, Any]:
    recent = changed_since(SESSION_BASE)
    pinning = 0
    drifted: list[dict[str, Any]] = []
    stale_counter: Counter[str] = Counter()
    missing_counter: Counter[str] = Counter()

    for artifact in sorted((ROOT / "results").rglob("*.json")):
        try:
            body = json.loads(artifact.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(body, dict):
            continue
        sources = body.get("source_sha256")
        if not isinstance(sources, dict) or not sources:
            continue
        pinning += 1
        stale: list[str] = []
        missing: list[str] = []
        for relative, expected in sources.items():
            if not isinstance(relative, str) or not isinstance(expected, str):
                continue
            path = ROOT / relative
            if not path.is_file():
                missing.append(relative)
                continue
            if sha256(path) != expected:
                stale.append(relative)
        if not stale and not missing:
            continue
        stale_counter.update(stale)
        missing_counter.update(missing)
        drifted.append(
            {
                "artifact": str(artifact.relative_to(ROOT)),
                "pinned_sources": len(sources),
                "stale": sorted(stale),
                "missing": sorted(missing),
                "stale_only_from_recent_work": bool(stale)
                and all(s in recent for s in stale),
            }
        )

    drifted.sort(key=lambda row: (-len(row["stale"]), row["artifact"]))
    recent_causes = {s: n for s, n in stale_counter.items() if s in recent}
    return {
        "artifacts_pinning_source_sha256": pinning,
        "artifacts_with_drift": len(drifted),
        "drift_fraction": (
            round(len(drifted) / pinning, 4) if pinning else None
        ),
        "artifacts_drifted_only_by_recent_work": sum(
            1 for row in drifted if row["stale_only_from_recent_work"]
        ),
        "most_common_stale_sources": [
            {"source": source, "artifacts_staled": count}
            for source, count in stale_counter.most_common(12)
        ],
        "most_common_missing_sources": [
            {"source": source, "artifacts_affected": count}
            for source, count in missing_counter.most_common(6)
        ],
        "stale_sources_changed_since_session_base": [
            {"source": source, "artifacts_staled": count}
            for source, count in sorted(
                recent_causes.items(), key=lambda kv: -kv[1]
            )
        ],
        "drifted": drifted,
    }


def build() -> dict[str, Any]:
    body = survey()
    return {
        "schema": "opentallas.derived.source_currency_drift.v1",
        "generated_by": "tools/audit_source_currency_drift.py",
        "generated_by_sha256": sha256(Path(__file__)),
        "git": git_state(),
        "session_base": SESSION_BASE,
        "question": (
            "of the artifacts that pin source digests, how many still bind the "
            "sources on disk?"
        ),
        **body,
        "refusals": [
            {
                "id": "drift-is-not-wrongness",
                "what": "no measurement here is called incorrect",
                "why": (
                    "a drifted artifact's numbers may reproduce exactly; what "
                    "has lapsed is the guarantee that they were taken against "
                    "the sources now on disk"
                ),
            },
            {
                "id": "no-mass-regeneration",
                "what": "nothing is re-run and no pin is rewritten",
                "why": (
                    "re-running these is expensive and several depend on build "
                    "products that no longer exist; rewriting a pin to match "
                    "whatever is on disk is the failure mode the pins exist to "
                    "prevent"
                ),
            },
        ],
        "reading": (
            "the pinning mechanism is working -- campaigns were observed "
            "refusing to run on this ground -- but broadly-bound sources have "
            "moved faster than the campaigns binding them can be re-taken.  "
            "The practical consequence is that editing a widely-bound file, "
            "INCLUDING a design document, is a cascade whose size is worth "
            "knowing before the edit rather than after"
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    body = build()
    rendered = json.dumps(body, indent=2, sort_keys=True) + "\n"
    print(
        f"  {body['artifacts_with_drift']} of "
        f"{body['artifacts_pinning_source_sha256']} source-pinning artifacts "
        f"have drifted ({body['drift_fraction']:.0%})"
    )
    print("  most common cause:")
    for row in body["most_common_stale_sources"][:5]:
        print(f"    {row['artifacts_staled']:>3}x  {row['source']}")
    recent = body["stale_sources_changed_since_session_base"]
    print(f"  of which changed since {body['session_base']}: {len(recent)} source(s)")
    for row in recent[:6]:
        print(f"    {row['artifacts_staled']:>3}x  {row['source']}")
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
