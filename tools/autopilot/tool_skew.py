#!/usr/bin/env python3
"""tool_skew: refuse a kit_wave launch whose die source tree carries private copies of the gen/bind tools.

TOOLS-CONVERGE-1115 (COORD ruling r203, FABLE-CENSUS-1815 section 3 item 2): the S81, KV, HEAD and QC source trees
differed from main in 227 gen/bind modules.  Every tool-skew failure class of 11-15 came from that (S81 gen_phys.py
writing a form its own sdc_lint.py cannot read; the KV tree mixing vintages; --src-tree; schema keys).  A die tree is
main tools + the die's plan, nothing else.

  closure   every *.py / *.sh / *.tcl under tools/die_plan and tools/autopilot (recursive, no tests, no caches)
  skew      a closure module whose bytes differ between the die tree and main, present only in the die tree
            (private tool) or missing from the die tree (stale tree)
  allowlist tools/autopilot/tool_skew_allow.json (reviewed with main):
              {"<die>": {"<tools/... module or fnmatch glob>": {"expires": "YYYY-MM-DD", "why": "unmerged die feature"}}}
            An entry covers a module only until its expiry date; an expired entry is a skew again and is reported.
  CLI       tool_skew.py manifest TREE      -> JSON {module: sha256} of the closure (also runs remotely over ssh stdin)
            tool_skew.py check DIE TREE [--main DIR] [--allow FILE] [--host H]
"""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

CLOSURE_DIRS = ("tools/die_plan", "tools/autopilot")
CLOSURE_EXT = (".py", ".sh", ".tcl")
ALLOW_REL = "tools/autopilot/tool_skew_allow.json"
# pin mode (FABLE-FLOWCLASS-TOOLSKEW-2030 section 2.1/4): the reference is the die's pinned tools_sha (rt/<sha12>.manifest.json), over the
# whole TOOLS scope, not main and not only the die_plan/autopilot closure
SCOPE = ("tools/", "physical/common_flow/", "rtl/lib/", "rtl/common/")
RT_ROOT = "/srv/opentallas-scratch2/claude/rt"
SRC_MANIFEST = ".src-manifest.json"


def in_scope(rel):
    return rel.startswith(SCOPE) and "__pycache__" not in rel and not rel.endswith((".pyc", ".orig", ".rej")) and ".bak" not in rel


def scope_manifest(root):
    """{module: sha256} of every TOOLS-scope file under root (a tree without a src manifest is hashed)"""
    root = Path(root)
    m = {}
    for d in SCOPE:
        for dp, dn, fn in os.walk(root / d):
            dn[:] = sorted(x for x in dn if x != "__pycache__")
            for f in fn:
                p = Path(dp) / f
                rel = p.relative_to(root).as_posix()
                if in_scope(rel):
                    try:
                        m[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
                    except OSError:
                        pass
    return m


def pin_manifest(tools_sha, rt_root=RT_ROOT):
    """TOOLS-scope {module: sha256} of rt/<tools_sha[:12]>.manifest.json, or None (no such pin on this host)"""
    try:
        files = json.loads((Path(rt_root) / f"{str(tools_sha)[:12]}.manifest.json").read_text())["files"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {k: v for k, v in files.items() if in_scope(k)}


def tree_scope_manifest(tree):
    """TOOLS-scope manifest of a tree: its .src-manifest.json when it has one (the tree is read-only and verified at gen), else hashed"""
    try:
        files = json.loads((Path(tree) / SRC_MANIFEST).read_text())["files"]
        return {k: v for k, v in files.items() if in_scope(k)}
    except (OSError, ValueError, KeyError):
        return scope_manifest(tree)


def v2_marker(tree):
    """MANIFEST-V2-1116: the tree's own .src-manifest.json when it is a v2 manifest (declares main_sha), else None"""
    try:
        m = json.loads((Path(tree) / SRC_MANIFEST).read_text())
    except (OSError, ValueError):
        return None
    return m if isinstance(m, dict) and m.get("main_sha") else None


def closure_files(root):
    """-> sorted module paths (relative to root, posix) of the gen/bind tool closure under root"""
    root = Path(root)
    out = []
    for d in CLOSURE_DIRS:
        base = root / d
        for dp, dn, fn in os.walk(base):
            dn[:] = sorted(x for x in dn if x != "__pycache__")
            for f in fn:
                if f.endswith(CLOSURE_EXT) and not f.startswith("test_") and f != "conftest.py":
                    out.append((Path(dp) / f).relative_to(root).as_posix())
    return sorted(out)


def manifest(root):
    """-> {module: sha256 of its bytes}"""
    root = Path(root)
    m = {}
    for rel in closure_files(root):
        try:
            m[rel] = hashlib.sha256((root / rel).read_bytes()).hexdigest()
        except OSError:
            pass
    return m


def _remote_inventory(host, tree, mode, timeout=300):
    """manifest of a tree on another host: this file is piped to `python3 -I -` there.  -> dict, or None if unreachable"""
    if os.environ.get("OT_TOOL_SKEW_REMOTE") == "0":
        return None                                      # tests / offline runs never ssh
    try:
        p = subprocess.run(["ssh", "-T", "-o", "ControlPath=none", "-o", "BatchMode=yes", host,
                            "python3", "-I", "-", mode, str(tree)],
                           input=Path(__file__).read_bytes(), capture_output=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode:
        return None
    try:
        return json.loads(p.stdout)
    except ValueError:
        return None


def remote_manifest(host, tree, timeout=300):
    return _remote_inventory(host, tree, "manifest", timeout)


def remote_scope_manifest(host, tree, timeout=300):
    """Pin mode needs the same full-scope inventory and v2 marker remotely as locally."""
    data = _remote_inventory(host, tree, "scope-manifest", timeout)
    if not isinstance(data, dict) or not isinstance(data.get("files"), dict):
        return None
    return data


def diff(tree_m, main_m):
    """-> {module: 'differ' | 'only_die' | 'missing'}"""
    out = {}
    for rel, h in tree_m.items():
        if rel not in main_m:
            out[rel] = "only_die"
        elif main_m[rel] != h:
            out[rel] = "differ"
    for rel in main_m:
        if rel not in tree_m:
            out[rel] = "missing"
    return out


def load_allow(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return {}


def apply_allow(skew, die_allow, today):
    """-> (refused, allowed, expired): refused {module: kind} not covered by a live entry; allowed {module: why};
    expired {module: expiry} covered only by an entry past its date (those count as refused)"""
    refused, allowed, expired = {}, {}, {}
    for rel, kind in skew.items():
        hit = None
        for pat, ent in (die_allow or {}).items():
            if rel == pat or fnmatch.fnmatchcase(rel, pat):
                exp = str((ent or {}).get("expires", ""))
                if exp and exp >= today:
                    hit = (pat, ent)
                    break
                expired[rel] = exp or "no expiry"
        if hit:
            allowed[rel] = str((hit[1] or {}).get("why", ""))
        else:
            refused[rel] = kind
    return refused, allowed, expired


def check_die(die, tree, main_root, allow=None, host=None, today=None, tree_m=None, main_m=None, tools_sha=None,
              rt_root=RT_ROOT, strict=False, only=None):
    """-> dict(ok, measured, refused, allowed, expired, n_closure).  A tree that cannot be read is UNMEASURED and not
    refused (never block a launch on a host that is down); an empty closure (no tools/ in the tree) is a skew."""
    today = today or datetime.date.today().isoformat()
    if tools_sha:                                        # pin mode: reference = the die's pinned tools_sha, whole TOOLS scope
        ref = pin_manifest(tools_sha, rt_root)
        if ref is None:
            return dict(ok=not strict, measured=False, refused={f"rt/{str(tools_sha)[:12]}": "missing"} if strict else {},
                        allowed={}, expired={}, n_closure=0, pin=str(tools_sha)[:12])
        mk = v2_marker(tree) if Path(tree).is_dir() else None
        if tree_m is None and Path(tree).is_dir():
            tree_m = tree_scope_manifest(tree)
        if tree_m is None and host:
            remote = remote_scope_manifest(host, tree)
            if remote is not None:
                tree_m, mk = remote["files"], remote.get("marker")
        if tree_m is None:
            return dict(ok=not strict, measured=False, refused={str(tree): "unreadable"} if strict else {}, allowed={},
                        expired={}, n_closure=len(ref), pin=str(tools_sha)[:12])
        # MANIFEST-V2-1116 (FABLE-FLOW-0913): a v2 tree's manifest covers the whole source (17987 in-scope files) but the pin's rt manifest is
        # the v1 baseline (280 files): every other file read as 'only_die' ("17138 of 17987 differ", never a signal).  A v2 tree whose
        # marker main_sha is the pin is compared on the pin's own files; the files the baseline does not list are main's, not private.
        if mk and str(mk["main_sha"])[:12] == str(tools_sha)[:12]:
            tree_m = {k: v for k, v in tree_m.items() if k in ref}
        refused, allowed, expired = apply_allow(diff(tree_m, ref), (allow or {}).get(die) or {}, today)
        return dict(ok=not refused, measured=True, refused=refused, allowed=allowed, expired=expired, n_closure=len(ref),
                    pin=str(tools_sha)[:12])
    main_m = main_m if main_m is not None else manifest(main_root)
    if tree_m is None:
        if host and not Path(tree).is_dir():
            tree_m = remote_manifest(host, tree)
        elif Path(tree).is_dir():
            tree_m = manifest(tree)
    if tree_m is None:
        return dict(ok=True, measured=False, refused={}, allowed={}, expired={}, n_closure=len(main_m))
    if only is not None:                                 # one closure for the wave gate and the FLOW-HEALTH SKEW table (flow_guard.closure_files)
        main_m = {k: v for k, v in main_m.items() if k in only}
        tree_m = {k: v for k, v in tree_m.items() if k in only}
    refused, allowed, expired = apply_allow(diff(tree_m, main_m), (allow or {}).get(die) or {}, today)
    return dict(ok=not refused, measured=True, refused=refused, allowed=allowed, expired=expired, n_closure=len(main_m))


def signature(res):
    """stable id of a refusal set: one post per change, not one per tick"""
    return hashlib.sha256(json.dumps(sorted(res["refused"].items())).encode()).hexdigest()[:12]


def needs_lane_text(die, tree, res, owner=""):
    r = res["refused"]
    kinds = {k: sum(1 for v in r.values() if v == k) for k in ("differ", "only_die", "missing")}
    sample = ", ".join(sorted(r)[:8])
    return (f"NEEDS-LANE [KIT-WAVE -> COORD; owner {owner or die}] TOOL-SKEW refused launches on {die}: tree {tree} has "
            f"{len(r)} gen/bind module(s) that differ from main ({kinds['differ']} differ, {kinds['only_die']} private, "
            f"{kinds['missing']} missing; {len(res['expired'])} allowlist entries expired). First: {sample}. Fix: land the "
            f"die feature on main (TOOLS-CONVERGE-1115 branch), rebuild the tree as main tools + plan at the next plan event, "
            f"or declare the module in {ALLOW_REL} with an expiry. signature {signature(res)}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("manifest")
    m.add_argument("tree")
    sm = sub.add_parser("scope-manifest")
    sm.add_argument("tree")
    c = sub.add_parser("check")
    c.add_argument("die")
    c.add_argument("tree")
    c.add_argument("--main", default=None)
    c.add_argument("--allow", default=None)
    c.add_argument("--host", default=None)
    a = ap.parse_args(argv)
    if a.cmd == "manifest":
        print(json.dumps(manifest(a.tree)))
        return 0
    if a.cmd == "scope-manifest":
        marker = v2_marker(a.tree)
        if marker is not None:
            marker = {k: marker.get(k) for k in ("main_sha", "version", "manifest_hash")}
        print(json.dumps(dict(files=tree_scope_manifest(a.tree), marker=marker)))
        return 0
    a.main = a.main or str(Path(__file__).resolve().parents[2])
    allow = load_allow(a.allow or Path(a.main) / ALLOW_REL)
    res = check_die(a.die, a.tree, a.main, allow, a.host)
    print(json.dumps(res, indent=1, sort_keys=True))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
