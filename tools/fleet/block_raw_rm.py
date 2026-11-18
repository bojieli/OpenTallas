#!/usr/bin/env python3
"""PreToolUse hook (FLEET-OPS-R, COORD 11-17): refuse a raw recursive rm / find -delete / rmtree on /srv/opentallas-scratch*.
Deletion goes through ot-delete (ot_delete_guard).  Exit 2 + message = blocked; anything else passes.  Install in ~/.claude/settings.json next to block-pkill.py."""
import json, re, sys

SCRATCH = r"/srv/opentallas-scratch[0-9]*"
RM_R = re.compile(r"(?:^|[;&|(`\x27\x22\s])(?:sudo\s+)?(?:/bin/|/usr/bin/)?rm\s+(?:[^;&|\n]*?\s)?(?:-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)(?=\s)[^;&|\n]*" + SCRATCH)
FIND_DEL = re.compile(r"\bfind\s+[^;&|\n]*" + SCRATCH + r"[^;&|\n]*\s-delete\b")
RMTREE = re.compile(r"rmtree\([^)]*" + SCRATCH)


GIT_CLONE = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?clone\b[^;&|\n]*" + SCRATCH)
GIT_WT = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?worktree\s+add\b[^;&|\n]*" + SCRATCH)
SAFE_FLAGS = re.compile(r"--filter|--sparse|--depth|--no-checkout|--bare|--mirror|--reference|ot-lane-clone")


def raw_full_checkout(cmd):
    """a `git clone` / `git worktree add` into scratch that is not sparse / filtered / shallow / bare = a raw ~49 GB checkout (COORD FABLE-FLOW-0700 (3))"""
    return any((rx.search(seg) and not SAFE_FLAGS.search(seg)) for seg in re.split(r"[;&|\n]", cmd) for rx in (GIT_CLONE, GIT_WT))


DOCKER_PRUNE_ALL = re.compile(r"\bdocker\s+(?:image|system)\s+prune\b[^;&|\n]*\s(?:-[a-zA-Z]*a[a-zA-Z]*|--all)\b")


def blocked(cmd):
    if DOCKER_PRUNE_ALL.search(cmd):
        return True
    if raw_full_checkout(cmd):
        return True
    if "ot-delete" in cmd.split() and not RM_R.search(cmd):
        return False
    return bool(RM_R.search(cmd) or FIND_DEL.search(cmd) or RMTREE.search(cmd))


def main():
    try:
        d = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = str((d.get("tool_input") or {}).get("command", ""))
    if blocked(cmd):
        if DOCKER_PRUNE_ALL.search(cmd):
            print("BLOCKED: `docker image/system prune -a` removes flow images (epyc7 lost asap7lock-grtoff). Use tools/fleet/ot-docker-prune.", file=sys.stderr)
            return 2
        print("BLOCKED: raw recursive delete on /srv/opentallas-scratch*. Use `ot-delete TREE...` (ot_delete_guard: protected / live trees are skipped, "
              "whole trees only, df before/after).", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
