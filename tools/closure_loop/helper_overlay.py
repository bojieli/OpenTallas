"""One effective helper resolver and immutable content plans for gates and routes."""
from __future__ import annotations
import hashlib
import json
import os
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
