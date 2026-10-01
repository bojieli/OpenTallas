"""Source-currency checks that accept an explicit stale marker instead of failing.

A record whose pinned sources moved after it was generated is either regenerated
on HEAD or carries a marker:

    "currency": {"state": "stale", "stale_since": "<commit>", "reason": "...",
                 "verdict_kept": <the historical verdict>, "marked": "..."}

The historical verdict is kept (failed or passed verdicts are never overwritten)
and the marker says why it was not re-run.  A drifted pin without a marker still
fails, and a marker on a record whose pins all match fails too, so the marker
cannot outlive its reason.
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def drifted(pins: dict[str, str]) -> list[str]:
    return sorted(p for p, d in pins.items()
                  if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != d)


def assert_current_or_marked_stale(rec: dict, pins: dict[str, str], name: str = "") -> None:
    moved = drifted(pins)
    cur = rec.get("currency")
    if not moved:
        assert cur is None, f"{name}: stale marker on a record whose pins all match; remove it"
        return
    assert cur is not None, f"{name}: pinned sources moved {moved} and the record carries no stale marker"
    assert cur.get("state") == "stale", (name, cur)
    assert cur.get("reason"), name
    assert "verdict_kept" in cur, name
    since = cur.get("stale_since", "")
    ok = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e", f"{since}^{{commit}}"],
                        capture_output=True).returncode == 0
    assert ok, f"{name}: stale_since {since!r} is not a commit"
