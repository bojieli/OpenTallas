#!/usr/bin/env python3
"""Gate-Rule guard (ROOT-RULETAG 2026-10-19): refuse a push to main that brings a commit touching a gate / daemon-overlay
helper file without a Gate-Rule classification.

Why: helper_overlay.rule_span classifies every commit on a helper file's chain between a gate's frozen blob and today's.
A commit with neither a 'Gate-Rule: relaxing|neutral|tightening' trailer nor a helper_overlay.RULE_COMMITS entry is
UNCLASSIFIED and every gate made before it is refused at submit (10-19: 96f1d6e0d and five more blocked every submit;
then 03c544ca1, b7918e979 and four view_export.py commits).  This guard moves that failure to merge time.

A non-merge commit in the pushed range (TIP ^BASE) that changes a GUARDED path passes when, for every guarded path it
changes, one of these holds:
  * its message has a 'Gate-Rule: relaxing|neutral|tightening' trailer (helper_overlay.TRAILER_RE);
  * its full sha is a RULE_COMMITS key in TIP's tools/closure_loop/helper_overlay.py (classify in the same push);
  * the change is comments / docstrings / blank lines only (helper_overlay.change_is_comment_only);
  * the new blob is a revision the path already had on BASE's history (a lane copying a tool from main).
Merge commits are skipped (rule_span lists their parents' commits; a non-clean merge it refuses on its own).

GUARDED = helper_overlay HELPERS / FLEET_RUN / PUBLISH_ONLY / LINT_ONLY, plus every non-test, non-doc file under
tools/closure_loop/, tools/ref_tile/, tools/hier_contract/, tools/tt_views/ and physical/common_flow/.

Usage: gate_rule_guard.py [--repo R] [--base origin/main] [--tip HEAD]       exit 0 PASS, 1 REFUSE, 2 usage/git error
Hook:  root_pre_push.sh (installed as .git/hooks/pre-push) runs it for every push to refs/heads/main.
Override (owner-approved emergencies only, logged in HANDOFF): OT_GATE_RULE_GUARD=off."""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GUARDED_DIRS = ("tools/closure_loop/", "tools/ref_tile/", "tools/hier_contract/", "tools/tt_views/",
                "physical/common_flow/")
ZERO = "0" * 40


def _ho(text=None):
    """helper_overlay module: from TEXT (the pushed tip's copy) when given, else the copy next to this file"""
    name = "ot_ho_guard"
    if text is None:
        spec = importlib.util.spec_from_file_location(name, HERE / "helper_overlay.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    mod = type(sys)(name)
    mod.__file__ = str(HERE / "helper_overlay.py")
    exec(compile(text, "helper_overlay.py@tip", "exec"), mod.__dict__)  # noqa: S102 -- repo's own tool
    return mod


def git(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=300)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args[:3])}: {p.stderr.strip()[:300]}")
    return p.stdout


def blob(repo, sha):
    p = subprocess.run(["git", "-C", str(repo), "cat-file", "blob", sha], capture_output=True, timeout=60)
    return None if p.returncode else p.stdout


def is_test_or_doc(rel):
    base = rel.rsplit("/", 1)[-1]
    return ("/tests/" in rel or "/test/" in rel or base.startswith("test_") or base.endswith(("_test.py", ".md", ".txt"))
            or base == "conftest.py")


def guarded_paths_fn(ho):
    exact = set(ho.helper_paths()) | set(getattr(ho, "FLEET_RUN", ())) | set(getattr(ho, "PUBLISH_ONLY", ())) \
        | set(getattr(ho, "LINT_ONLY", ()))

    def guarded(rel):
        return rel in exact or (rel.startswith(GUARDED_DIRS) and not is_test_or_doc(rel))
    return guarded


def registry_keys(text):
    """full shas that are RULE_COMMITS keys in a helper_overlay.py text"""
    m = re.search(r"^RULE_COMMITS\s*=\s*\{(.*?)^\}", text or "", re.S | re.M)
    return set(re.findall(r'"([0-9a-f]{40})"\s*:\s*dict\(', m.group(1))) if m else set()


def main_blobs(repo, base, rel, cache):
    if rel not in cache:
        out = git(repo, "log", "--format=", "--raw", "--no-abbrev", "--no-renames", base, "--", rel, check=False)
        cache[rel] = {f[3] for ln in out.splitlines() if ln.startswith(":") for f in [ln.split()] if len(f) >= 5}
    return cache[rel]


def check(repo, base, tip, ho=None):
    """(ok, rows): rows = one dict per refused (commit, path) plus a summary row per passing commit"""
    tip_ho_text = git(repo, "show", f"{tip}:tools/closure_loop/helper_overlay.py", check=False)
    ho = ho or (_ho(tip_ho_text) if tip_ho_text else _ho())
    reg = registry_keys(tip_ho_text) | set(getattr(ho, "RULE_COMMITS", {}))
    guarded = guarded_paths_fn(ho)
    commits = git(repo, "rev-list", "--no-merges", tip, f"^{base}").split()
    rows, bad, cache = [], [], {}
    for c in commits:
        raw = git(repo, "diff-tree", "--no-commit-id", "-r", "--raw", "--no-abbrev", "--no-renames", c)
        files = []
        for ln in raw.splitlines():
            f = ln.split("\t")
            meta = f[0].split()
            if len(f) >= 2 and len(meta) >= 5 and guarded(f[1]):
                files.append((f[1], meta[2], meta[3]))
        if not files:
            continue
        msg = git(repo, "log", "-1", "--format=%B", c)
        trailer = ho.parse_rule_trailer(msg)
        if trailer or c in reg:
            rows.append(dict(commit=c, ok=True, how="trailer " + trailer["kind"] if trailer else "RULE_COMMITS",
                             paths=[p for p, _, _ in files]))
            continue
        for rel, pre, post in files:
            how = None
            if post == ZERO:
                how = "deleted"
            elif post in main_blobs(repo, base, rel, cache):
                how = "copy of a main revision"
            else:
                a, b = (blob(repo, pre) if pre != ZERO else b""), blob(repo, post)
                if a is not None and b is not None and ho.change_is_comment_only(rel, a, b):
                    how = "comment-only"
            if how is None:
                bad.append(dict(commit=c, path=rel, subject=msg.splitlines()[0][:100] if msg else ""))
        if not any(r["commit"] == c for r in bad):
            rows.append(dict(commit=c, ok=True, how="auto", paths=[p for p, _, _ in files]))
    return not bad, bad + rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".")
    ap.add_argument("--base", default="origin/main")
    ap.add_argument("--tip", default="HEAD")
    a = ap.parse_args(argv)
    if os.environ.get("OT_GATE_RULE_GUARD", "").lower() == "off":
        print("gate_rule_guard: OFF (OT_GATE_RULE_GUARD=off)", file=sys.stderr)
        return 0
    try:
        ok, rows = check(a.repo, a.base, a.tip)
    except Exception as ex:  # noqa: BLE001
        print(f"gate_rule_guard: ERROR {type(ex).__name__}: {ex}", file=sys.stderr)
        return 2
    for r in rows:
        if not r.get("ok"):
            print(f"gate_rule_guard: REFUSE {r['commit'][:9]} {r['path']} ({r['subject']})", file=sys.stderr)
    if not ok:
        print("gate_rule_guard: every commit changing a gate / daemon-overlay helper needs a 'Gate-Rule: "
              "relaxing|neutral|tightening' trailer (optional requires=<cond> applies-to=<prefixes>) or a "
              "tools/closure_loop/helper_overlay.py RULE_COMMITS entry; otherwise every older gate is refused at "
              "submit.  Amend/reword the commit or add the RULE_COMMITS entry (with a test) in this push.",
              file=sys.stderr)
        return 1
    n = sum(1 for r in rows if r.get("ok"))
    print(f"gate_rule_guard: PASS ({n} helper-touching commit(s) classified)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
