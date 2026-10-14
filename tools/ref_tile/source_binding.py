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


def validate(binding, root, daemon, commit=None):
    """Match immutable staged contents against the requested route source and current tool overlay."""
    if not isinstance(binding, dict) or binding.get("schema") != SCHEMA:
        return False, "missing immutable source snapshot; legacy result is unqualified"
    entries = binding.get("files")
    if not entries or canonical_digest(entries) != binding.get("manifest_sha256"):
        return False, "source manifest missing or digest mismatch"
    tree = git_files(root, commit) if commit else None
    for e in entries:
        p = Path(e["path"])
        if p.is_absolute() or ".." in p.parts:
            return False, "unsafe manifest path"
        if e["source"] == "daemon_overlay":
            f = daemon / p
        elif tree is not None:
            if tree.get(str(p)) != e["git_blob"]:
                return False, f"route source differs from staged snapshot: {p}"
            continue
        else:
            f = root / p
        try:
            payload = str(f.readlink()).encode() if e["kind"] == "symlink" else f.read_bytes()
        except OSError:
            return False, f"staged source missing: {p}"
        if hashlib.sha256(payload).hexdigest() != e["sha256"]:
            return False, f"route source differs from staged snapshot: {p}"
    return True, "exact staged source and daemon overlay match"
