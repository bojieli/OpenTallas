#!/usr/bin/env python3
"""ruling_holds.py: a ruling hold is a machine line, applied and released by a tool (FABLE-FLOW-1000 class 6; KIT-OPS-5).

A queue line carries the clause   MHOLD <die> <item-glob>[,<item-glob>...] until <merged-ref> [: reason]
  <die>         a die key of kit_wave.json (qwen_compute, s81, ...)
  <item-glob>   fnmatch pattern(s) of the items to hold (comma separated, no spaces)
  <merged-ref>  a branch name or commit sha; the hold is released when it is an ancestor of the main ref
apply() adds one hold_items entry per glob ("MHOLD <ref> (queue line N): reason") and deletes every MHOLD entry whose ref
merged.  Entries it did not write (no 'MHOLD ' prefix) are never touched.  The tool only edits a kit_wave.json copy; the
caller commits it with coord-commit.sh and verifies on origin/coord/state.
"""
import argparse, json, re, subprocess, sys

CLAUSE = re.compile(r"\bMHOLD\s+(?P<die>[A-Za-z0-9_]+)\s+(?P<items>\S+)\s+until\s+(?P<ref>[A-Za-z0-9_./@-]+)\s*(?::\s*(?P<why>.*))?$")
PREFIX = "MHOLD "


def parse_lines(lines):
    """-> [(lineno, die, [globs], ref, reason)] for every clause in the text lines"""
    out = []
    for n, line in enumerate(lines, 1):
        m = CLAUSE.search(line.rstrip("\n"))
        if m:
            out.append((n, m["die"], [g for g in m["items"].split(",") if g], m["ref"], (m["why"] or "").strip()))
    return out


def apply(cfg, clauses, merged):
    """cfg: parsed kit_wave.json (edited in place); merged(ref) -> bool.  -> (added, released) as lists of (die, glob)"""
    dies = cfg.get("dies") or {}
    added, released = [], []
    for die, d in dies.items():                                      # release first: a merged ref frees its entries
        h = d.get("hold_items") or {}
        for key in list(h):
            v = str(h[key])
            if v.startswith(PREFIX):
                ref = v[len(PREFIX):].split(" ", 1)[0]
                if merged(ref):
                    del h[key]
                    released.append((die, key))
    for n, die, globs, ref, why in clauses:
        if die not in dies or merged(ref):
            continue
        h = dies[die].setdefault("hold_items", {})
        for g in globs:
            if g not in h:
                h[g] = f"{PREFIX}{ref} (queue line {n}): {why or 'ruling hold'}. Released automatically when {ref} is on main."
                added.append((die, g))
    return added, released


def git_merged(repo, main_ref):
    def merged(ref):
        r = subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", ref, main_ref], capture_output=True)
        return r.returncode == 0
    return merged


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--queue", required=True)
    ap.add_argument("--config", required=True, help="kit_wave.json copy to edit in place")
    ap.add_argument("--repo", required=True, help="git repo that knows main and the refs")
    ap.add_argument("--main-ref", default="origin/main")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    cfg = json.load(open(a.config))
    clauses = parse_lines(open(a.queue, errors="replace").read().splitlines())
    added, released = apply(cfg, clauses, git_merged(a.repo, a.main_ref))
    print(f"MHOLD clauses {len(clauses)}: added {len(added)} {added[:20]}; released {len(released)} {released[:20]}")
    if (added or released) and not a.dry_run:
        json.dump(cfg, open(a.config, "w"), indent=1)
        open(a.config, "a").write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
