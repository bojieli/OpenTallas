#!/usr/bin/env python3
"""Reproduce or verify the clean RTL implementation campaign.

The shared OpenTallas worktree intentionally contains user work.  This helper
does not stash, reset, clean, or commit that tree.  Instead, it copies exactly
the source inventory recorded by a technically passing noncanonical campaign
into a temporary repository, creates a deterministic root commit, requires the
same source/tool fingerprint, runs the complete campaign without
``--allow-dirty``, and archives both the clean result and the displaced dirty-
tree build evidence.  Once canonical evidence exists, the default behavior and
``--verify-existing`` are non-mutating: they validate the canonical result,
archived reference, replay record, reports, and referenced case artifacts rather
than attempting to archive or overwrite them again.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REFERENCE = ROOT / "results" / "rtl" / "implementation_campaign.json"
DEFAULT_REPLAY_RECORD = ROOT / "results" / "rtl" / "clean_baseline_replay.json"
FINGERPRINT_RE = re.compile(r"^[0-9a-f]{16}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ReplayError(RuntimeError):
    """The clean replay contract failed."""


def strict_json(path: Path) -> Any:
    duplicates: list[str] = []

    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                duplicates.append(key)
            result[key] = value
        return result

    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs)
    except (OSError, json.JSONDecodeError) as exc:
        raise ReplayError(f"cannot load {path}: {exc}") from exc
    if duplicates:
        raise ReplayError(f"duplicate JSON keys in {path}: {sorted(set(duplicates))}")
    return data


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    return {
        "path": str(path.resolve().relative_to(root.resolve())),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def verify_recorded_artifact(record: Any, *, label: str, root: Path = ROOT) -> Path:
    if not isinstance(record, dict):
        raise ReplayError(f"{label} artifact record is missing or malformed")
    path_text = record.get("path")
    digest = record.get("sha256")
    size = record.get("size_bytes")
    path_value = Path(path_text) if isinstance(path_text, str) else None
    if (
        path_value is None
        or path_value.is_absolute()
        or not path_value.parts
        or ".." in path_value.parts
        or not isinstance(digest, str)
        or SHA256_RE.fullmatch(digest) is None
        or not isinstance(size, int)
        or isinstance(size, bool)
        or size < 0
    ):
        raise ReplayError(f"{label} artifact record is invalid: {record!r}")
    path = (root / path_value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ReplayError(
            f"{label} artifact escapes the workspace: {path_text}"
        ) from exc
    if not path.is_file():
        raise ReplayError(f"{label} artifact is missing: {path_text}")
    if path.stat().st_size != size or sha256_file(path) != digest:
        raise ReplayError(
            f"{label} artifact does not match its replay record: {path_text}"
        )
    return path


def run(
    command: list[str],
    *,
    cwd: Path,
    capture: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        env=env,
    )
    if completed.returncode != 0:
        output = "" if completed.stdout is None else f"\n{completed.stdout}"
        raise ReplayError(
            f"command failed ({completed.returncode}): {' '.join(command)}{output}"
        )
    return completed


def safe_inventory_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ReplayError(f"unsafe source-inventory path {path_text!r}")
    source = (ROOT / path).resolve()
    try:
        source.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ReplayError(f"source inventory escapes workspace: {path_text}") from exc
    if not source.is_file() or source.is_symlink():
        raise ReplayError(f"source inventory is not a regular file: {path_text}")
    return source


def copy_exact_source_inventory(reference: dict[str, Any], snapshot: Path) -> None:
    inventory = reference.get("source_inventory")
    if not isinstance(inventory, list) or not inventory:
        raise ReplayError("reference result has no source inventory")
    seen: set[str] = set()
    for item in inventory:
        if not isinstance(item, dict):
            raise ReplayError("invalid source-inventory record")
        path_text = item.get("path")
        digest = item.get("sha256")
        size = item.get("size_bytes")
        if (
            not isinstance(path_text, str)
            or path_text in seen
            or not isinstance(digest, str)
            or not isinstance(size, int)
        ):
            raise ReplayError(f"invalid source-inventory record: {item!r}")
        seen.add(path_text)
        source = safe_inventory_path(path_text)
        if source.stat().st_size != size or sha256_file(source) != digest:
            raise ReplayError(
                f"current source differs from reference inventory: {path_text}"
            )
        destination = snapshot / path_text
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def initialize_clean_repository(snapshot: Path) -> dict[str, str]:
    run(["git", "init", "-q"], cwd=snapshot)
    run(["git", "config", "user.name", "OpenTallas Clean Replay"], cwd=snapshot)
    run(
        ["git", "config", "user.email", "clean-replay@opentallas.invalid"],
        cwd=snapshot,
    )
    run(["git", "add", "--all"], cwd=snapshot)
    commit_env = dict(os.environ)
    commit_env.update(
        {
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00",
        }
    )
    run(
        ["git", "commit", "-q", "-m", "Deterministic OpenTallas RTL replay snapshot"],
        cwd=snapshot,
        env=commit_env,
    )
    status = run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=snapshot,
        capture=True,
    ).stdout
    if status:
        raise ReplayError(f"new source snapshot is unexpectedly dirty:\n{status}")
    commit = run(
        ["git", "rev-parse", "HEAD"], cwd=snapshot, capture=True
    ).stdout.strip()
    tree = run(
        ["git", "rev-parse", "HEAD^{tree}"], cwd=snapshot, capture=True
    ).stdout.strip()
    return {"commit": commit, "tree": tree}


def closure_signature(result: dict[str, Any]) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for case in result.get("cases", []):
        synthesis = case["synthesis"]
        sta = case["sta"]
        physical = case["physical_proxy"]
        cases.append(
            {
                "name": case["name"],
                "mapping_profile": synthesis["mapping_profile"]["profile_id"],
                "mapped_internal_cells": synthesis["mapped_internal_cells"],
                "latches": synthesis["latches"],
                "blackboxes": synthesis["blackboxes"],
                "structural_problems": synthesis["structural_problems"],
                "unexpected_synthesis_warnings": synthesis["warnings"]["unexpected"],
                "sta_status": sta["status"],
                "proxy_constraint_coverage": sta["proxy_100mhz"]["constraint_coverage"],
                "generic_equivalence": case["equivalence_generic"]["status"],
                "mapped_equivalence": case["equivalence_mapped"]["status"],
                "physical": physical["status"],
                "postroute_equivalence": physical.get("postroute_equivalence", {}).get(
                    "status"
                ),
            }
        )
    return {"summary": result.get("summary"), "cases": cases}


def verify_case_artifacts(value: Any, root: Path) -> int:
    verified = 0
    if isinstance(value, dict):
        if set(("path", "sha256", "size_bytes")) <= set(value):
            path_text = value["path"]
            if not isinstance(path_text, str) or not path_text.startswith("rtl/build/"):
                raise ReplayError(f"unexpected campaign artifact path {path_text!r}")
            path = (root / path_text).resolve()
            try:
                path.relative_to(root.resolve())
            except ValueError as exc:
                raise ReplayError(f"artifact escapes result root: {path_text}") from exc
            if (
                not path.is_file()
                or path.stat().st_size != value["size_bytes"]
                or sha256_file(path) != value["sha256"]
            ):
                raise ReplayError(
                    f"campaign artifact does not match result: {path_text}"
                )
            return 1
        for child in value.values():
            verified += verify_case_artifacts(child, root)
    elif isinstance(value, list):
        for child in value:
            verified += verify_case_artifacts(child, root)
    return verified


def require_clean_result(
    reference: dict[str, Any], clean: dict[str, Any], snapshot_identity: dict[str, str]
) -> None:
    eligibility = clean.get("canonical_eligibility", {})
    if clean.get("status") != "pass" or not all(
        eligibility.get(field) is True
        for field in (
            "clean_source_tree",
            "complete_case_selection",
            "equivalence_enabled",
            "physical_flow_enabled",
            "technical_gates_pass",
        )
    ):
        raise ReplayError(f"clean campaign did not close canonically: {eligibility}")
    if clean.get("run_fingerprint") != reference.get("run_fingerprint"):
        raise ReplayError("clean and reference fingerprints differ")
    if clean.get("source_inventory") != reference.get("source_inventory"):
        raise ReplayError("clean and reference source inventories differ")
    if clean.get("toolchain") != reference.get("toolchain"):
        raise ReplayError("clean and reference toolchain identities differ")
    if closure_signature(clean) != closure_signature(reference):
        raise ReplayError("clean and reference technical closure signatures differ")
    baseline = clean.get("baseline", {})
    if (
        baseline.get("commit") != snapshot_identity["commit"]
        or baseline.get("dirty_paths") != []
    ):
        raise ReplayError("clean result does not bind to the clean snapshot commit")


def verify_existing_replay(
    canonical_path: Path = DEFAULT_REFERENCE,
    replay_path: Path = DEFAULT_REPLAY_RECORD,
    *,
    verify_case_files: bool = True,
) -> dict[str, Any]:
    """Verify promoted evidence without changing the repository."""

    canonical_path = canonical_path.resolve()
    replay_path = replay_path.resolve()
    canonical = strict_json(canonical_path)
    replay = strict_json(replay_path)
    fingerprint = canonical.get("run_fingerprint")
    if (
        canonical.get("status") != "pass"
        or not isinstance(fingerprint, str)
        or FINGERPRINT_RE.fullmatch(fingerprint) is None
    ):
        raise ReplayError("canonical implementation result is not a valid pass")
    if replay.get("status") != "pass" or replay.get("run_fingerprint") != fingerprint:
        raise ReplayError("clean replay record disagrees with the canonical result")

    comparisons = replay.get("comparisons", {})
    if not all(
        comparisons.get(field) is True
        for field in (
            "run_fingerprint_equal",
            "source_inventory_equal",
            "toolchain_identity_equal",
            "technical_closure_signature_equal",
        )
    ):
        raise ReplayError("clean replay comparison record is incomplete")
    if replay.get("summary") != canonical.get("summary"):
        raise ReplayError("clean replay summary disagrees with the canonical result")

    recorded_canonical = verify_recorded_artifact(
        replay.get("canonical_result"), label="canonical result"
    )
    if recorded_canonical != canonical_path:
        raise ReplayError(
            "requested canonical result is not the replay-recorded result"
        )
    canonical_report = verify_recorded_artifact(
        replay.get("canonical_report"), label="canonical report"
    )
    archived_result = verify_recorded_artifact(
        replay.get("archived_noncanonical_result"),
        label="archived noncanonical result",
    )
    verify_recorded_artifact(
        replay.get("archived_noncanonical_report"),
        label="archived noncanonical report",
    )
    reference = strict_json(archived_result)
    if (
        reference.get("status") != "partial_noncanonical"
        or reference.get("canonical_eligibility", {}).get("technical_gates_pass")
        is not True
    ):
        raise ReplayError(
            "archived reference is not a technically passing noncanonical result"
        )
    snapshot = replay.get("clean_snapshot")
    if (
        not isinstance(snapshot, dict)
        or not re.fullmatch(r"[0-9a-f]{40}", str(snapshot.get("commit", "")))
        or not re.fullmatch(r"[0-9a-f]{40}", str(snapshot.get("tree", "")))
    ):
        raise ReplayError("clean snapshot identity is missing or malformed")
    require_clean_result(reference, canonical, snapshot)

    report_text = canonical_report.read_text(encoding="utf-8", errors="replace")
    if "**Status:** PASS" not in report_text or fingerprint not in report_text:
        raise ReplayError("canonical Markdown report disagrees with the result")

    build_locations = replay.get("build_locations", {})
    for key in ("canonical", "archived_noncanonical"):
        path_text = (
            build_locations.get(key) if isinstance(build_locations, dict) else None
        )
        path_value = Path(path_text) if isinstance(path_text, str) else None
        if (
            path_value is None
            or path_value.is_absolute()
            or ".." in path_value.parts
            or not (ROOT / path_value).is_dir()
        ):
            raise ReplayError(f"recorded {key} build directory is missing or unsafe")

    expected_artifacts = replay.get("verified_case_artifacts")
    if (
        not isinstance(expected_artifacts, int)
        or isinstance(expected_artifacts, bool)
        or expected_artifacts < 1
    ):
        raise ReplayError("replay record has no valid verified-artifact count")
    verified_artifacts = expected_artifacts
    if verify_case_files:
        verified_artifacts = verify_case_artifacts(canonical.get("cases"), ROOT)
        if verified_artifacts != expected_artifacts:
            raise ReplayError(
                "canonical case-artifact count differs from the replay record"
            )

    return {
        "status": "pass",
        "run_fingerprint": fingerprint,
        "verified_case_artifacts": verified_artifacts,
        "clean_snapshot": snapshot,
        "archived_reference": str(archived_result.relative_to(ROOT)),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def archive_results(
    reference_path: Path,
    reference: dict[str, Any],
    clean_result_path: Path,
    snapshot: Path,
    snapshot_identity: dict[str, str],
    invocation_commit: str,
    verified_artifacts: int,
) -> dict[str, Any]:
    fingerprint = clean_result_path.name  # overwritten below for a guarded value
    clean = strict_json(clean_result_path)
    fingerprint = clean["run_fingerprint"]
    if (
        not isinstance(fingerprint, str)
        or FINGERPRINT_RE.fullmatch(fingerprint) is None
    ):
        raise ReplayError(f"unsafe run fingerprint {fingerprint!r}")
    reference_report = ROOT / "results" / "rtl" / "IMPLEMENTATION_REPORT.md"
    clean_report = snapshot / "results" / "rtl" / "IMPLEMENTATION_REPORT.md"
    if not reference_report.is_file() or not clean_report.is_file():
        raise ReplayError("implementation report is missing")

    historical_dir = ROOT / "results" / "rtl" / "noncanonical" / fingerprint
    historical_dir.mkdir(parents=True, exist_ok=True)
    historical_json = historical_dir / "implementation_campaign.json"
    historical_report = historical_dir / "IMPLEMENTATION_REPORT.md"
    for destination in (historical_json, historical_report):
        if destination.exists():
            raise ReplayError(
                f"refusing to overwrite historical evidence: {destination}"
            )
    shutil.copy2(reference_path, historical_json)
    shutil.copy2(reference_report, historical_report)

    build_parent = ROOT / "rtl" / "build" / "implementation_campaign"
    shared_build = build_parent / fingerprint
    clean_build = snapshot / "rtl" / "build" / "implementation_campaign" / fingerprint
    reference_commit = str(reference.get("baseline", {}).get("commit", "unknown"))
    suffix = (
        reference_commit[:12]
        if re.fullmatch(r"[0-9a-f]{40}", reference_commit)
        else "unknown"
    )
    historical_build = build_parent / f"{fingerprint}-noncanonical-{suffix}"
    if not shared_build.is_dir() or not clean_build.is_dir():
        raise ReplayError("clean or reference campaign build directory is missing")
    if historical_build.exists():
        raise ReplayError(f"refusing to overwrite historical build: {historical_build}")
    shared_build.rename(historical_build)
    try:
        shutil.move(str(clean_build), str(shared_build))
    except Exception:
        if not shared_build.exists() and historical_build.exists():
            historical_build.rename(shared_build)
        raise

    canonical_json = ROOT / "results" / "rtl" / "implementation_campaign.json"
    canonical_report = ROOT / "results" / "rtl" / "IMPLEMENTATION_REPORT.md"
    shutil.copy2(clean_result_path, canonical_json)
    shutil.copy2(clean_report, canonical_report)
    archived_verified = verify_case_artifacts(clean["cases"], ROOT)
    if archived_verified != verified_artifacts:
        raise ReplayError(
            "archived canonical artifact count differs from clean snapshot audit"
        )

    replay = {
        "schema_version": 1,
        "status": "pass",
        "run_fingerprint": fingerprint,
        "method": (
            "Copied only the reference result's exact fingerprinted source inventory "
            "to a new repository, created a deterministic clean root commit, required "
            "an equal validate-only fingerprint, then ran the full seven-case campaign "
            "without --allow-dirty, --case, --skip-equivalence, or --skip-physical."
        ),
        "shared_worktree_policy": (
            "No shared-worktree reset, clean, stash, checkout, or commit was performed."
        ),
        "invocation_workspace_commit": invocation_commit,
        "noncanonical_reference_baseline": reference.get("baseline"),
        "clean_snapshot": snapshot_identity,
        "comparisons": {
            "run_fingerprint_equal": True,
            "source_inventory_equal": True,
            "toolchain_identity_equal": True,
            "technical_closure_signature_equal": True,
        },
        "canonical_eligibility": clean["canonical_eligibility"],
        "summary": clean["summary"],
        "verified_case_artifacts": archived_verified,
        "canonical_result": artifact(canonical_json),
        "canonical_report": artifact(canonical_report),
        "archived_noncanonical_result": artifact(historical_json),
        "archived_noncanonical_report": artifact(historical_report),
        "build_locations": {
            "canonical": str(shared_build.relative_to(ROOT)),
            "archived_noncanonical": str(historical_build.relative_to(ROOT)),
            "artifact_path_relocation_note": (
                "The archived noncanonical JSON retains its original rtl/build paths; "
                "its raw build was preserved at the suffixed location above."
            ),
        },
    }
    replay_json = ROOT / "results" / "rtl" / "clean_baseline_replay.json"
    write_json(replay_json, replay)
    replay_report = ROOT / "results" / "rtl" / "CLEAN_BASELINE_REPLAY.md"
    replay_report.write_text(
        "\n".join(
            [
                "# Clean-baseline RTL implementation replay",
                "",
                "**Status:** **PASS**",
                "",
                f"Run fingerprint: `{fingerprint}`  ",
                f"Clean snapshot commit: `{snapshot_identity['commit']}`  ",
                f"Clean snapshot tree: `{snapshot_identity['tree']}`",
                "",
                "The exact fingerprinted source inventory was copied into an isolated "
                "repository and committed with deterministic identity. The complete "
                "seven-case campaign then ran without any dirty-tree or skip option.",
                "",
                "- Clean source tree: pass.",
                "- Equal source/tool fingerprint: pass.",
                "- Equal source inventory: pass.",
                "- Equal pinned toolchain identity: pass.",
                "- Equal technical closure signature: pass.",
                f"- Required cases: {clean['summary']['required_cases_passing']}/{clean['summary']['required_cases']}.",
                f"- Generic equivalence: {clean['summary']['generic_equivalence_passing']}/{clean['summary']['generic_equivalence_required']}.",
                f"- Mapped equivalence: {clean['summary']['mapped_equivalence_passing']}/{clean['summary']['mapped_equivalence_required']}.",
                f"- Physical proxies: {clean['summary']['physical_proxy_passing']}/{clean['summary']['physical_proxy_required']}.",
                f"- Post-route equivalence: {clean['summary']['postroute_equivalence_passing']}/{clean['summary']['postroute_equivalence_required']}.",
                f"- Hash-verified case artifacts after archival: {archived_verified}.",
                "",
                "The shared worktree was not reset, cleaned, stashed, checked out, or "
                "committed. Its unrelated and user-owned changes remain in place.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return replay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--replay-record", type=Path, default=DEFAULT_REPLAY_RECORD)
    parser.add_argument(
        "--verify-existing",
        action="store_true",
        help="verify already-promoted evidence without running or writing a campaign",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        reference_path = args.reference.resolve()
        reference = strict_json(reference_path)
        if args.verify_existing or reference.get("status") == "pass":
            if reference.get("status") == "pass" and not args.verify_existing:
                print(
                    "CLEAN REPLAY: canonical evidence already exists; "
                    "running non-mutating verification",
                    flush=True,
                )
            verified = verify_existing_replay(
                reference_path, args.replay_record.resolve()
            )
            print(
                "CLEAN RTL IMPLEMENTATION EVIDENCE PASS: "
                f"fingerprint {verified['run_fingerprint']}, "
                f"{verified['verified_case_artifacts']} artifacts verified"
            )
            return 0
        fingerprint = reference.get("run_fingerprint")
        if (
            not isinstance(fingerprint, str)
            or FINGERPRINT_RE.fullmatch(fingerprint) is None
        ):
            raise ReplayError("reference result has an invalid run fingerprint")
        if (
            reference.get("status") != "partial_noncanonical"
            or reference.get("canonical_eligibility", {}).get("technical_gates_pass")
            is not True
        ):
            raise ReplayError(
                "reference must be a technically passing partial_noncanonical result"
            )
        invocation_commit = run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture=True
        ).stdout.strip()
        with tempfile.TemporaryDirectory(prefix="opentallas-rtl-clean-replay-") as temp:
            snapshot = Path(temp) / "source"
            snapshot.mkdir()
            copy_exact_source_inventory(reference, snapshot)
            snapshot_identity = initialize_clean_repository(snapshot)
            runner = snapshot / "tools" / "rtl_implementation_campaign.py"
            validation = run(
                [sys.executable, str(runner), "--validate-only"],
                cwd=snapshot,
                capture=True,
            ).stdout
            print(validation, end="", flush=True)
            match = re.search(r"fingerprint ([0-9a-f]{16})", validation)
            if match is None or match.group(1) != fingerprint:
                raise ReplayError(
                    f"clean validate-only fingerprint differs from {fingerprint}"
                )
            print(
                f"CLEAN REPLAY: running full campaign from {snapshot_identity['commit']}",
                flush=True,
            )
            run([sys.executable, str(runner)], cwd=snapshot)
            clean_result_path = (
                snapshot / "results" / "rtl" / "implementation_campaign.json"
            )
            clean = strict_json(clean_result_path)
            require_clean_result(reference, clean, snapshot_identity)
            verified = verify_case_artifacts(clean["cases"], snapshot)
            if verified < 1:
                raise ReplayError("clean result declares no case artifacts")
            replay = archive_results(
                reference_path,
                reference,
                clean_result_path,
                snapshot,
                snapshot_identity,
                invocation_commit,
                verified,
            )
        print(
            "CLEAN RTL IMPLEMENTATION REPLAY PASS: "
            f"fingerprint {replay['run_fingerprint']}, "
            f"{replay['verified_case_artifacts']} artifacts verified"
        )
        return 0
    except ReplayError as exc:
        print(f"CLEAN RTL IMPLEMENTATION REPLAY FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
