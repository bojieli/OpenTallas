"""Guard for in-place kit / src patch tools (WF-1 11-14): never rewrite a sha-pinned scheduler snapshot or a sealed ot-job input.

The 14:51 reg_fanout patch matched run_kit*.sh and rewrote 21 attempt_*/future_lec/run_kit_template.sh copies, whose sha the
lec_tools stage pins ("runner template differs from pinned scheduler snapshot", 16 items).  Every in-place patch tool filters its
candidates through is_patchable()."""
import os
import re

PINNED_PARTS = ("/future_lec/", "/.future_lec-", "/ot-jobs/")   # ot-jobs: sealed ot-run job inputs (hash-sealed)
PINNED_NAMES = re.compile(r"^(?:run_kit_template\.sh|TOOL\.json|kit_resume\.py|future_kit_lec\.py)(?:\..*)?$")
SKIP_SUFFIX = re.compile(r"\.(?:bak[^/]*|wf1new|orig|new|tmp)$")


def is_patchable(path):
    """False for a sha-pinned snapshot file (anything under future_lec/, the pinned template / tool names) and for backup artefacts"""
    p = str(path).replace("\\", "/")
    base = p.rsplit("/", 1)[-1]
    if any(part in p + "/" for part in PINNED_PARTS):
        return False
    if PINNED_NAMES.match(base) or SKIP_SUFFIX.search(base) or ".bak-" in base:
        return False
    return True


def filter_patchable(paths):
    return [p for p in paths if is_patchable(p)]


OWNER_CHECKOUTS = ("/home/ubuntu/OpenTallas", "/srv/opentallas-scratch2/claude/moved/home__ubuntu__OpenTallas")


def git_root(path):
    """nearest ancestor directory of path that holds a .git entry (a git checkout / worktree), or None"""
    d = os.path.dirname(str(path))
    while d and d != "/":
        if os.path.exists(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return None


def is_patchable_here(path, allow_roots=()):
    """is_patchable() plus: never a file inside a git checkout (the owner's /home/ubuntu/OpenTallas merge hub and every other worktree)
    unless the checkout root is named in allow_roots (the sanctioned wave-src trees, patched explicitly, never by discovery)"""
    p = str(path)
    if not is_patchable(p):
        return False
    if any(p == c or p.startswith(c + "/") for c in OWNER_CHECKOUTS):
        return False
    root = git_root(p)
    return root is None or any(root == a.rstrip("/") for a in allow_roots)
