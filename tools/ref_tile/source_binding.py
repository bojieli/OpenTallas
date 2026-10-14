"""Content binding for the exact effective gate archive (including daemon overlays).

A commit is provenance only unless every shipped file matches it. Qualification
uses the immutable manifest, never a HEAD observed after the remote run.
"""
from __future__ import annotations

import hashlib
import io
import json
import subprocess
import tarfile
from pathlib import Path

SCHEMA = "opentallas.ref_tile.source_snapshot.v1"
EXCLUDED = {"gate_result.json", "source_snapshot.json"}


def git_head(repo):
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True)
    return p.stdout.strip() if p.returncode == 0 else None


def git_files(repo, commit):
    if not commit:
        return {}
    p = subprocess.run(["git", "-C", str(repo), "ls-tree", "-rz", commit], capture_output=True)
    if p.returncode:
        return {}
    return {path.decode(): meta.decode().split()[2] for row in p.stdout.split(b"\0") if row
            for meta, path in [row.split(b"\t", 1)]}


def blob_hash(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def canonical_digest(entries):
    return hashlib.sha256(json.dumps(entries, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def overlay_module():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "closure_loop"))
    import helper_overlay
    return helper_overlay


def snapshot(data, root, start_commit, daemon, daemon_commit, helpers):
    """Read the completed bytes, resolving duplicate tar members as extraction does."""
    current, overlays = git_files(root, start_commit), git_files(daemon, daemon_commit)
    files = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
        for m in tf:
            if not (m.isfile() or m.issym()):
                if m.islnk():
                    raise ValueError("hard links are unsupported in gate source snapshots")
                continue
            payload = m.linkname.encode() if m.issym() else tf.extractfile(m).read()
            source = "daemon_overlay" if m.name in helpers and (daemon / m.name).exists() else "working_tree"
            expected = (overlays if source == "daemon_overlay" else current).get(m.name)
            files[m.name] = {"path": m.name, "kind": "symlink" if m.issym() else "file",
                             "sha256": hashlib.sha256(payload).hexdigest(), "git_blob": blob_hash(payload),
                             "source": source, "matches_provenance_commit": expected == blob_hash(payload)}
    entries = [files[k] for k in sorted(files)]
    clean = all(e["matches_provenance_commit"] and current.get(e["path"]) == e["git_blob"] for e in entries)
    return {"schema": SCHEMA, "start_commit": start_commit, "commit": start_commit if clean else None,
            "identity": "commit" if clean else "exact_content_snapshot", "daemon_tree": str(daemon),
            "daemon_start_commit": daemon_commit, "daemon_overlays": sorted(set(helpers) & files.keys()),
            "archive_sha256": hashlib.sha256(data).hexdigest(), "manifest_sha256": canonical_digest(entries),
            "files": entries}


def validate(binding, root, daemon, commit=None, route_overlay=True, frozen_recovery=False):
    """Match immutable staged contents against the requested route source and current tool overlay."""
    if not isinstance(binding, dict) or binding.get("schema") != SCHEMA:
        return False, "missing immutable source snapshot; legacy result is unqualified"
    if frozen_recovery and not route_overlay:
        return False, "frozen helper recovery requires executed overlay verification"
    entries = binding.get("files")
    if not entries or canonical_digest(entries) != binding.get("manifest_sha256"):
        return False, "source manifest missing or digest mismatch"
    tree = git_files(root, commit) if commit else None
    effective = {}
    if route_overlay:
        HO = overlay_module()
        frozen = binding.get("route_overlay_plan")
        paths = None if frozen else [e["path"] for e in entries if e["source"] == "daemon_overlay"]
        try:
            if frozen_recovery:
                receipt = binding.get("helper_recovery") or {}
                executed = sorted(e["path"] for e in entries if e["source"] == "daemon_overlay")
                if ((binding.get("recovery") or {}).get("kind") != "full_original_snapshot_verified"
                        or not executed
                        or not binding.get("remote_archive_verified")
                        or receipt.get("status") != "verified_original_gate"
                        or receipt.get("content_sha256") != (frozen or {}).get("content_sha256")
                        or receipt.get("origin_main") != (frozen or {}).get("origin_main")
                        or receipt.get("executed_paths") != executed
                        or receipt.get("manifest_sha256") != binding["manifest_sha256"]):
                    return False, "original gate executed-helper verification missing or mismatched"
                effective = HO.committed_frozen_payloads(root, frozen)
            else:
                current, effective = HO.capture_plan(daemon, root, paths=paths)
        except (OSError, ValueError, subprocess.SubprocessError) as ex:
            return False, f"cannot resolve effective route helpers: {ex}"
        if frozen and not frozen_recovery:
            # Precise binding (2026-10-14): the gate is bound to what it EXECUTED -- the staged working-tree files
            # (checked against the route source commit below) and the daemon overlays it shipped (entries with
            # source "daemon_overlay", checked against today's effective bytes below).  The frozen route plan's other
            # helpers are route-only: their drift is reported, never a reason to invalidate the gate.  The frozen plan
            # itself must still be intact and agree with what the gate shipped.
            try:
                rows = {r["path"]: r for r in HO.frozen_rows(frozen)}
            except ValueError as ex:
                return False, str(ex)
            for e in entries:
                if e["source"] == "daemon_overlay" and e["path"] in rows and rows[e["path"]]["sha256"] != e["sha256"]:
                    return False, f"frozen route plan disagrees with the gate's staged overlay: {e['path']}"
    overlay_diff, source_diff, missing = [], [], []
    for e in entries:
        p = Path(e["path"])
        if p.is_absolute() or ".." in p.parts:
            return False, "unsafe manifest path"
        if e["source"] == "daemon_overlay" and route_overlay:
            if str(p) not in effective or hashlib.sha256(effective[str(p)]).hexdigest() != e["sha256"]:
                overlay_diff.append(str(p))
            continue
        if e["source"] == "daemon_overlay":
            f = daemon / p
        elif tree is not None:
            if tree.get(str(p)) != e["git_blob"]:
                source_diff.append(str(p))
            continue
        else:
            f = root / p
        try:
            payload = str(f.readlink()).encode() if e["kind"] == "symlink" else f.read_bytes()
        except OSError:
            missing.append(str(p))
            continue
        if hashlib.sha256(payload).hexdigest() != e["sha256"]:
            (overlay_diff if e["source"] == "daemon_overlay" else source_diff).append(str(p))
    if overlay_diff or source_diff or missing:
        def name(files):
            return ", ".join(files[:6]) + (f" (+{len(files) - 6} more)" if len(files) > 6 else "")
        parts = ([f"gate-executed daemon overlay changed: {name(overlay_diff)}"] if overlay_diff else []) + \
                ([f"route source differs from staged snapshot: {name(source_diff)}"] if source_diff else []) + \
                ([f"staged source missing: {name(missing)}"] if missing else [])
        return False, "; ".join(parts)
    if route_overlay and not frozen_recovery and binding.get("route_overlay_plan"):
        drift = route_only_drift(binding["route_overlay_plan"], current, entries)
        if drift:
            return True, "exact staged source and gate-executed overlays match; route-only helper drift (not gate-relevant): " + \
                ", ".join(drift)
    return True, ("exact original source and committed executed helpers match; current helpers unchanged"
                  if frozen_recovery else "exact staged source and daemon overlay match")


def gate_overlay_paths(binding):
    """The daemon overlays the gate shipped and executed (orfs_hold_mm, fp_margin_lint, textbook_lint,
    macro_cts_cluster: pre_route_gate.SHIP_HELPERS).  Every other route-plan helper is route-only for the gate; a
    gate-run helper that is not an overlay (ck_insertion.py, path_classes.tcl, ref_route.sh) is a working-tree entry
    bound to the route source commit."""
    return sorted(e["path"] for e in binding.get("files", []) if e.get("source") == "daemon_overlay")


def route_only_drift(frozen, current, entries):
    """Route-plan helpers whose effective content changed since the gate and that the gate did not execute."""
    gate = {e["path"] for e in entries if e.get("source") == "daemon_overlay"}
    old = {r["path"]: r for r in frozen.get("files", [])}
    new = {r["path"]: r for r in (current or {}).get("files", [])}
    keys = ("sha256", "git_blob", "mode")
    return sorted(p for p in set(old) | set(new) if p not in gate
                  and tuple((old.get(p) or {}).get(k) for k in keys) != tuple((new.get(p) or {}).get(k) for k in keys))


def recover_verified_snapshot(binding, staged_root, log_bytes, script_bytes):
    """Recover original source identity after a parser failure, never infer a later commit.

    This verifies the complete shipping sidecar, all extracted bytes, the exact
    executed script, its SOURCE_COMMIT marker, and the remote archive-digest log.
    The returned binding describes that original run; current route qualification
    must still compare it against the requested route commit and live overlays.
    """
    import copy
    import re
    ok, why = validate(binding, staged_root, staged_root, route_overlay=False)
    if not ok:
        raise ValueError(why)
    if hashlib.sha256(script_bytes).hexdigest() != binding.get("remote_script_sha256"):
        raise ValueError("executed script differs from shipping manifest")
    log = log_bytes.decode(errors="replace")
    hashes = re.findall(r"^GATE_SOURCE_ARCHIVE_SHA256=(\S+)\s*$", log, re.M)
    if hashes != [binding.get("archive_sha256")]:
        raise ValueError("archive verification absent, ambiguous, or mismatched in original log")
    identity = binding.get("commit") or "snapshot-sha256:" + binding["manifest_sha256"]
    if (staged_root / "SOURCE_COMMIT").read_text().strip() != identity:
        raise ValueError("original SOURCE_COMMIT marker differs from exact snapshot identity")
    recovered = copy.deepcopy(binding)
    recovered["remote_archive_verified"] = True
    recovered["runtime_tool_provenance"] = re.findall(r"^GATE_TOOL_.*$", log, re.M)
    recovered["recovery"] = {"kind": "full_original_snapshot_verified", "log_sha256": hashlib.sha256(log_bytes).hexdigest(),
                             "staged_root": str(staged_root), "qualification": "original_source_only_not_current_HEAD"}
    return recovered
