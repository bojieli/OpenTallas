"""One effective helper resolver and immutable content plans for gates and routes."""
from __future__ import annotations
import hashlib
import threading
import json
import os
import re
import stat
import subprocess
from pathlib import Path

HELPERS = ("eco_recovery.py", "path_summary.py", "macro_views.py", "ck_insertion.py", "hold_eco.sh", "hold_eco.tcl", "hold_eco_corner.tcl",
           "hold_eco_sdc.py", "hold_eco_window.tcl", "hold_corners_patch.py", "h1_patch.py", "cal_classify.sh", "resume_patch.py", "resume_check.sh",
           "../orfs_hold_mm.py", "../orfs_hold_mm.tcl", "tt_resta.sh", "meas_resta.py", "lane_kh_overlay.py",
           "../../physical/common_flow/io_ref_routed.sdc", "../fp_margin_lint.py", "../fp_margin_lint.tcl",
           "../preroute_gate.py", "../preroute_gate.tcl", "../textbook_lint.py", "tt_overlay.py", "vtswap_eco.sh", "vtswap_eco.tcl",
           "pinflop_overlay.py", "../../physical/qwen_die_masters/pinflop_ref.tcl", "../w18/corner_sta.py", "route_corner_check.py", "../hier_contract/child_lint.py",
           "../hier_contract/abstract_pin_stub.py", "../hier_contract/m6_pin_grant.py", "../../physical/common_flow/grt_macro_top_layer.tcl",
           "../tt_views/view_export.py",
           "../../physical/common_flow/grt_macro_top_layer_post.tcl",
           *(f"../../physical/common_flow/{n}" for n in ("cg_pushdown.tcl", "clk_net_protect.tcl", "link_budget_hook.tcl",
                                                          "link_budget_consistent.sdc", "nbr_clk_measured_ttb.sdc",
                                                          "macro_sliver_block.tcl", "edge_sliver_block.tcl",
                                                          "macro_cts_cluster.tcl")))

SCHEMA = "opentallas.closure_loop.helper_overlay_plan.v1"


def blob_id(data):
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def main_head(repo):
    p = subprocess.run(["git", "-C", str(repo), "rev-parse", "refs/remotes/origin/main"], capture_output=True, text=True)
    return p.stdout.strip() if not p.returncode else None


def resolve_bytes(daemon, repo, rel, head, cache=None, local_bytes=None):
    """Preserve closure-loop's existing same/stale/daemon-only resolution rules."""
    cache = {} if cache is None else cache
    local = (Path(daemon) / rel).read_bytes() if local_bytes is None else local_bytes
    if not head:
        return local, "no_git"
    key = (rel, head)
    if key not in cache:
        p = subprocess.run(["git", "-C", str(repo), "rev-parse", f"{head}:{rel}"], capture_output=True, text=True, timeout=60)
        cache[key] = p.stdout.strip() if not p.returncode else None
    tip = cache[key]
    lid = blob_id(local)
    if tip is None:
        return local, "not_on_main"
    if lid == tip:
        return local, "same"
    hk = ("inhist", rel, lid)
    if not cache.get(hk):
        p = subprocess.run(["git", "-C", str(repo), "log", "--format=", "--raw", "--no-abbrev", "--no-renames", head, "--", rel],
                           capture_output=True, text=True, timeout=180)
        cache[hk] = not p.returncode and lid in {ln.split()[3] for ln in p.stdout.splitlines()
                                               if ln.startswith(":") and len(ln.split()) >= 5}
    if cache[hk]:
        p = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", tip], capture_output=True, timeout=60)
        if not p.returncode:
            return p.stdout, "stale"
        return local, "no_git"
    return local, "daemon_only"


def helper_paths(helpers=None):
    return sorted({os.path.normpath("tools/closure_loop/" + h) for h in (HELPERS if helpers is None else helpers)})


def content_rows(files):
    return sorted([{k: f[k] for k in ("path", "sha256", "git_blob", "mode")} for f in files], key=lambda f: f["path"])


def digest(files):
    return hashlib.sha256(json.dumps(content_rows(files), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def capture_plan(daemon, repo, paths=None, head=None, cache=None):
    """Freeze one origin ref and the actual effective bytes; HEAD is provenance only."""
    head = main_head(repo) if head is None else head
    files, payloads = [], {}
    for rel in sorted(set(helper_paths() if paths is None else paths)):
        literal = (Path(daemon) / rel).read_bytes()
        data, state = resolve_bytes(daemon, repo, rel, head, cache, local_bytes=literal)
        payloads[rel] = data
        files.append({"path": rel, "sha256": hashlib.sha256(data).hexdigest(), "git_blob": blob_id(data),
                      "mode": (Path(daemon) / rel).stat().st_mode & 0o777, "resolution": state,
                      "literal_git_blob": blob_id(literal)})
    return {"schema": SCHEMA, "origin_main": head, "content_sha256": digest(files), "files": files}, payloads


def compare_plans(frozen, effective):
    if not isinstance(frozen, dict) or frozen.get("schema") != SCHEMA:
        return False, "missing frozen effective helper plan"
    try:
        if digest(frozen["files"]) != frozen.get("content_sha256"):
            return False, "frozen helper plan digest mismatch"
        old = {f["path"]: f for f in content_rows(frozen["files"])}
        new = {f["path"]: f for f in content_rows(effective["files"])}
    except (KeyError, TypeError, ValueError):
        return False, "malformed frozen helper plan"
    for rel in sorted(set(old) | set(new)):
        if old.get(rel) != new.get(rel):
            return False, f"effective route helper drift: {rel} (frozen {old.get(rel)}, current {new.get(rel)})"
    return True, "effective route helper bytes and modes match frozen plan"


def frozen_rows(plan):
    """Validate the recorded plan without consulting today's helper resolution."""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("missing frozen effective helper plan")
    try:
        rows = content_rows(plan["files"])
        if not rows or digest(rows) != plan.get("content_sha256"):
            raise ValueError("frozen helper plan digest mismatch")
        paths, names = set(), set()
        for row in rows:
            path = Path(row["path"])
            if path.is_absolute() or ".." in path.parts or str(path) != row["path"]:
                raise ValueError("unsafe frozen helper path")
            if row["path"] in paths or path.name in names:
                raise ValueError("duplicate frozen helper path or transport basename")
            paths.add(row["path"])
            names.add(path.name)
            if not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) or not re.fullmatch(r"[0-9a-f]{40}", row["git_blob"]):
                raise ValueError("invalid frozen helper hash")
            if type(row["mode"]) is not int or not 0 <= row["mode"] <= 0o777:
                raise ValueError("invalid frozen helper mode")
        return rows
    except (KeyError, TypeError, AttributeError) as ex:
        raise ValueError("malformed frozen helper plan") from ex


def committed_frozen_payloads(repo, plan, only=None):
    """Recover only bytes committed at each original path in the recorded tree.

    Git records the executable bit; the plan records the full transported POSIX
    mode (e.g. 0664). Both are checked independently of current main or daemon.
    Daemon-only/uncommitted content cannot enter this recovery path.
    """
    rows = frozen_rows(plan)
    head = plan.get("origin_main")
    if not isinstance(head, str) or not re.fullmatch(r"[0-9a-f]{40}", head):
        raise ValueError("frozen helper origin must be an explicit committed tree")
    kind = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", head], capture_output=True, timeout=60)
    if kind.returncode or kind.stdout.strip() != b"commit":
        raise ValueError("frozen helper committed tree unavailable")
    lineage = subprocess.run(["git", "-C", str(repo), "merge-base", "--is-ancestor", head,
                              "refs/remotes/origin/main"], capture_output=True, timeout=60)
    if lineage.returncode:
        raise ValueError("frozen helper origin is not retained main history")
    tree = subprocess.run(["git", "-C", str(repo), "ls-tree", "-rz", head], capture_output=True, timeout=60)
    if tree.returncode:
        raise ValueError("frozen helper committed tree unavailable")
    entries = {}
    for item in tree.stdout.split(b"\0"):
        if item:
            meta, path = item.split(b"\t", 1)
            entries[path.decode()] = meta.decode().split()
    payloads = {}
    for row in rows:
        if only is not None and row["path"] not in only:
            continue
        mode, kind, blob = entries.get(row["path"], (None, None, None))
        if kind != "blob" or mode not in ("100644", "100755") or blob != row["git_blob"]:
            raise ValueError(f"frozen helper committed tree mismatch: {row['path']}")
        if bool(row["mode"] & 0o111) != (mode == "100755"):
            raise ValueError(f"frozen helper committed executable mode mismatch: {row['path']}")
        data = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", blob], capture_output=True, timeout=60)
        if data.returncode or blob_id(data.stdout) != blob or hashlib.sha256(data.stdout).hexdigest() != row["sha256"]:
            raise ValueError(f"frozen helper committed bytes missing or tampered: {row['path']}")
        payloads[row["path"]] = data.stdout
    return payloads


def store_payloads(store, plan, payloads):
    """Keep every frozen helper byte-string in a content-addressed store (one file per sha256).

    The store lives in the loop's state directory (~/.local/state/closure_loop/frozen_helpers), which no run-root,
    scratch or worktree cleanup touches; run directories (where helpers execute) are disposable copies of it.
    """
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    for row in frozen_rows(plan):
        data = payloads[row["path"]]
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"frozen helper payload differs from plan: {row['path']}")
        dest = store / row["sha256"]
        if dest.exists() and hashlib.sha256(dest.read_bytes()).hexdigest() == row["sha256"]:
            continue
        # per-thread temp name: the daemon steps jobs in parallel threads of ONE process, and two jobs freezing the same
        # helper blob raced on a pid-only name (FileNotFoundError at os.replace, qfd_xcst_s_m5 17:12 10-15)
        tmp = store / f".{row['sha256']}.{os.getpid()}.{threading.get_ident()}.tmp"
        tmp.write_bytes(data)
        os.replace(tmp, dest)


def stored_frozen_payloads(store, plan, only=None):
    """Recover the exact frozen bytes from the content store; every file re-verified against the plan."""
    payloads = {}
    for row in frozen_rows(plan):
        if only is not None and row["path"] not in only:
            continue
        try:
            data = (Path(store) / row["sha256"]).read_bytes()
        except OSError as ex:
            raise ValueError(f"frozen helper not in content store: {row['path']}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"frozen helper content store bytes tampered: {row['path']}")
        payloads[row["path"]] = data
    return payloads


UNCOMMITTED_RESOLUTIONS = ("daemon_only", "not_on_main", "no_git")


def recover_frozen_payloads(repo, store, plan):
    """Exact frozen bytes for a reinstall.  Returns (payloads, source).

    Rows frozen from committed main (resolution same/stale) come ONLY from the plan's committed origin tree, so a
    forged origin or a tree mismatch still refuses.  Rows that were legally uncommitted when frozen (daemon_only /
    not_on_main / no_git) come from the content-addressed store.  Every byte is verified (sha256 + git blob id)
    against the job's frozen plan, so a reinstall is identical to the original install or it does not happen.
    """
    rows = frozen_rows(plan)
    resolution = {f.get("path"): f.get("resolution") for f in plan.get("files", []) if isinstance(f, dict)}
    loose = {r["path"] for r in rows if resolution.get(r["path"]) in UNCOMMITTED_RESOLUTIONS}
    if not loose:
        return committed_frozen_payloads(repo, plan), "committed_origin"
    if store is None:
        raise ValueError("uncommitted frozen helpers need the content store")
    committed = {r["path"] for r in rows} - loose
    payloads = committed_frozen_payloads(repo, plan, only=committed) if committed else {}
    payloads.update(stored_frozen_payloads(store, plan, only=loose))
    return payloads, ("committed_origin+content_store" if committed else "content_store")


def verify_installed_plan(directory, plan):
    """Read-only verification of the original flattened route helper directory."""
    rows = frozen_rows(plan)
    directory = Path(directory)
    sidecar = directory / "helper_overlay_plan.json"
    if not sidecar.exists():
        if any((directory / Path(row["path"]).name).exists() for row in rows):
            raise ValueError("original helper files exist but frozen sidecar is missing")
        return {"status": "not_installed"}
    if not stat.S_ISREG(sidecar.lstat().st_mode):
        raise ValueError("original helper sidecar is not a regular file")
    if json.loads(sidecar.read_text()) != plan:
        raise ValueError("original helper sidecar differs from job frozen plan")
    for row in rows:
        path = directory / Path(row["path"]).name
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError(f"original helper is not a regular file: {row['path']}")
            if stat.S_IMODE(info.st_mode) != row["mode"]:
                raise ValueError(f"original helper mode mismatch: {row['path']}")
            data = path.read_bytes()
        except OSError as ex:
            raise ValueError(f"original helper missing: {row['path']}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"original helper bytes mismatch: {row['path']}")
    return {"status": "verified_original", "origin_main": plan["origin_main"],
            "content_sha256": plan["content_sha256"], "files": len(rows)}


def verify_staged_helpers(directory, plan, paths):
    """Verify the helpers actually shipped into an immutable gate source tree."""
    rows = {row["path"]: row for row in frozen_rows(plan)}
    if not paths or len(set(paths)) != len(paths) or any(path not in rows for path in paths):
        raise ValueError("gate executed helper paths missing or outside frozen plan")
    for rel in paths:
        row = rows[rel]
        path = Path(directory) / rel
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != row["mode"]:
                raise ValueError(f"original gate helper kind/mode mismatch: {rel}")
            data = path.read_bytes()
        except OSError as ex:
            raise ValueError(f"original gate helper missing: {rel}") from ex
        if hashlib.sha256(data).hexdigest() != row["sha256"] or blob_id(data) != row["git_blob"]:
            raise ValueError(f"original gate helper bytes mismatch: {rel}")
    return {"status": "verified_original_gate", "origin_main": plan["origin_main"],
            "content_sha256": plan["content_sha256"], "executed_paths": sorted(paths)}
