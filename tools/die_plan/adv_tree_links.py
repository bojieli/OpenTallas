"""ADV-TREE-LINKS (FP-CONVERGE-QC 11-25, COORD after QC C1o v13 lost ~2.5 h; report only, never a gate).

The v13 bind ran on a launch tree whose rtl/ and qwen_compute/bind/ were symlinks into an older private tree (QC-CB-C1L) that predates
main 636f4081887: every fix on main was silently absent.  ADV-TREE-DRIFT compares file content of what the plan names; nothing looked at links.

  LINK-OUT      a directory (any depth <= 6 under rtl/, tools/, physical/, and the plan's own directory) or a file (under rtl/, tools/die_plan,
                the plan directory) that is a symlink resolving OUTSIDE the launch tree.  Line: path -> resolved target.
  CONTENT-RT    with a declared rt sha ($OT_TOOLS_SHA / $OT_RT_CURRENT / kw rt_sha) and its rt manifest on this host: tools/die_plan and
                physical/common_flow files of the tree whose sha256 differs from the manifest (tool_root.py's rule).
  CONTENT-MAIN  with a declared main sha (kw main_sha, $OT_MAIN_SHA, else the tree's .src-manifest.json main_sha / .fork.json src_main_sha):
                tools/die_plan/*.py (not test_), physical/common_flow/* and rtl/*.sv|v files whose git blob differs from that main commit
                (adv_tree_drift's blob rule), files only counted when main has the path.
findings(raw, plan_path, tree=None, **kw) -> WARN lines (+ LIST); never raises.  Fix: replace the symlink by a copy of the declared tree
(ot-tree-fork) or carry the files (event_adopt_diff.py carry).
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "ADV-TREE-LINKS"
MAX_EX = 6
MAX_DEPTH = 6
SCAN_DIRS = ("rtl", "tools", "physical")
FILE_LINK_DIRS = ("rtl", "tools/die_plan")
RTL_EXT = (".sv", ".v", ".svh", ".vh")


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def _inside(path, root):
    return path == root or path.startswith(root.rstrip("/") + "/")


def scan_links(tree, plan_dir=None):
    """-> [(kind 'dir'|'file', rel path, resolved target)] symlinks resolving outside the tree"""
    root = os.path.realpath(tree)
    out = []

    def walk(base, depth, files_too):
        try:
            ents = list(os.scandir(base))
        except OSError:
            return
        for e in ents:
            try:
                if e.is_symlink():
                    tgt = os.path.realpath(e.path)
                    isdir = os.path.isdir(tgt)
                    if (isdir or files_too) and not _inside(tgt, root):
                        out.append(("dir" if isdir else "file", os.path.relpath(e.path, tree), tgt))
                elif e.is_dir(follow_symlinks=False) and depth < MAX_DEPTH:
                    walk(e.path, depth + 1, files_too)
            except OSError:
                continue

    for d in SCAN_DIRS:
        p = os.path.join(tree, d)
        if os.path.islink(p):
            tgt = os.path.realpath(p)
            if not _inside(tgt, root):
                out.append(("dir", d, tgt))
            continue
        walk(p, 1, d in ("rtl",))
    p = os.path.join(tree, "tools/die_plan")
    if os.path.isdir(p) and not os.path.islink(p):
        walk(p, MAX_DEPTH, True)
    if plan_dir and os.path.isdir(plan_dir):
        pd = os.path.realpath(plan_dir)
        if _inside(pd, root):
            walk(plan_dir, 3, True)
    seen, res = set(), []
    for k in out:
        if k[1] not in seen:
            seen.add(k[1])
            res.append(k)
    return sorted(res, key=lambda k: k[1])


def content_rt(tree, rt_sha=None):
    """-> (declared sha or None, [rel] differing from the rt manifest, note)"""
    import tool_root as T
    sha, src = T.declared_sha(rt_sha, None)
    if sha is None:
        return None, [], src
    man = T.find_manifest(sha)
    if man is None:
        return sha, [], "no rt manifest on this host"
    files = json.loads(man.read_text()).get("files") or {}
    bad = []
    for rel, want in sorted(files.items()):
        if not rel.startswith(T.CONTENT_PREFIXES):
            continue
        p = Path(tree) / rel
        try:
            got = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            got = None
        if got != want:
            bad.append(rel + (" (missing)" if got is None else ""))
    return sha, bad, ""


def content_main(tree, main_sha, kw):
    """-> (repo, sha, [rel] whose blob differs from main_sha, note)"""
    import adv_tree_drift as D
    repo, head = D._repo_main(kw)
    if not repo:
        return None, main_sha, [], "no main repo on this host"
    import subprocess
    r = subprocess.run(["git", "--git-dir", repo, "rev-parse", "--verify", "-q", f"{main_sha}^{{commit}}"], capture_output=True, text=True, timeout=30)
    if r.returncode or not r.stdout.strip():
        return repo, main_sha, [], f"declared main {main_sha[:12]} not in {repo}"
    commit = r.stdout.strip()
    specs = ["tools/die_plan", "physical/common_flow", "rtl"]
    oids = D._ls_tree(repo, commit, specs, 120.0)
    bad = []
    for rel, oid in sorted(oids.items()):
        if rel.startswith("tools/die_plan/") and (rel.count("/") > 2 or os.path.basename(rel).startswith("test_") or not rel.endswith(".py")):
            continue
        if rel.startswith("rtl/") and not rel.endswith(RTL_EXT):
            continue
        p = os.path.join(tree, rel)
        if not os.path.lexists(p):
            continue
        try:
            if D._blob(p) != oid:
                bad.append(rel)
        except OSError:
            continue
    return repo, commit, bad, ""


def _tree_of(plan_path, tree):
    if tree:
        return str(tree)
    import adv_tree_drift as D
    return D._find_tree(plan_path) if plan_path else None


def findings(raw, plan_path=None, tree=None, **kw):
    try:
        tree = _tree_of(plan_path, tree)
        if not tree or not os.path.isdir(tree):
            return [_w("not checked: no launch tree (pass --tree)")]
        out, n = [], 0
        links = scan_links(tree, os.path.dirname(os.path.abspath(plan_path)) if plan_path else None)
        for kind, rel, tgt in links[:MAX_EX * 3]:
            out.append(_w("LINK-OUT", f"{rel} ({kind} symlink) -> {tgt} (outside launch tree {tree})"))
        if len(links) > MAX_EX * 3:
            out.append(_w("LINK-OUT", f"... {len(links) - MAX_EX * 3} more symlink(s)"))
        n += len(links)
        try:
            sha, bad, note = content_rt(tree, kw.get("rt_sha"))
            if bad:
                n += len(bad)
                out.append(_w("CONTENT-RT", f"{len(bad)} tool file(s) differ from declared rt {sha[:12]}: " + ", ".join(bad[:MAX_EX]) + (" ..." if len(bad) > MAX_EX else "")))
        except Exception as e:  # noqa: BLE001
            out.append(_w("CONTENT-RT", f"not checked ({type(e).__name__}: {str(e)[:120]})"))
        msha = kw.get("main_sha") or os.environ.get("OT_MAIN_SHA") or ""
        if not msha:
            import adv_tree_drift as D
            msha = D._pin(tree)
        if msha:
            try:
                repo, commit, bad, note = content_main(tree, msha, kw)
                if note:
                    out.append(_w("CONTENT-MAIN", f"not checked: {note}"))
                if bad:
                    n += len(bad)
                    out.append(_w("CONTENT-MAIN", f"{len(bad)} tool/RTL file(s) differ from declared main {commit[:12]}: " + ", ".join(bad[:MAX_EX]) + (" ..." if len(bad) > MAX_EX else "")))
            except Exception as e:  # noqa: BLE001
                out.append(_w("CONTENT-MAIN", f"not checked ({type(e).__name__}: {str(e)[:120]})"))
        if out:
            out.append(f"LIST {CHECK} {n} finding(s) in launch tree {tree} (fix: copy the declared tree, not a symlink into another lane's tree)")
        return out
    except Exception as e:  # noqa: BLE001 -- an estimator reports, never stops
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]
