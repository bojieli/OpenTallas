#!/usr/bin/env python3
"""seal_gate.py TREE WHO [--sub physical[,rtl]] [--skip run]: FLEET-OPS 11-25 (COORD F-06 hook; third recurrence of a fork / bind tree whose symlinks lead into another lane's scratch tree).
Same rule as `ot-tree-fork --seal-check` (kept in step by test_seal_gate.py): a symlink under TREE (only the --sub subtrees, default physical) whose target resolves into ANOTHER
/srv/opentallas-scratch*/claude tree, or a symlink named .fork.json, is an outside link.  REPORT-ONLY until SEAL_BLOCK_AFTER (an hour after the hook went live), then exit 4.
OT_SEAL_GATE=0 disables, OT_SEAL_GATE=report keeps it report-only, OT_SEAL_GATE=block blocks now.  A walk that exceeds 60 s is cut and reported, never fatal.  Stdlib only: the file is
copied into every kit (gen_phys) and imported by bind.py."""
import os
import re
import sys
import time

SEAL_BLOCK_AFTER = 1795633675          # epoch: report-only before this, blocking after
SCRATCH_TREE_RE = re.compile(r"^/srv/opentallas-scratch\d*/claude/")


def findings(tree, sub=("physical",), skip=("run",), budget_s=60.0):
    tree = os.path.realpath(tree)
    t0 = time.time()
    bad = []
    for s in sub:
        root = os.path.join(tree, s) if s else tree
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            if time.time() - t0 > budget_s:
                bad.append(f"(walk cut after {budget_s:.0f} s)")
                return bad
            if dp == tree:
                dn[:] = [d for d in dn if d not in skip]
            for n in list(dn) + list(fn):
                q = os.path.join(dp, n)
                if not os.path.islink(q):
                    continue
                rel = os.path.relpath(q, tree)
                res = os.path.realpath(q)
                inside = res == tree or res.startswith(tree + os.sep)
                if n == ".fork.json":
                    bad.append(f"{rel} is a symlink (-> {os.readlink(q)}): the provenance file must be a regular file")
                elif SCRATCH_TREE_RE.match(res) and not inside:
                    bad.append(f"{rel} -> {os.readlink(q)} (resolves to {res}, outside the tree)")
            dn[:] = [d for d in dn if not os.path.islink(os.path.join(dp, d))]
    return bad


def mode(now=None, env=None):
    env = os.environ if env is None else env
    v = (env.get("OT_SEAL_GATE") or "").lower()
    if v in ("0", "off"):
        return "off"
    if v == "report":
        return "report"
    if v == "block":
        return "block"
    return "block" if (time.time() if now is None else now) >= SEAL_BLOCK_AFTER else "report"


def gate(tree, who, sub=("physical",), skip=("run",), out=None, now=None, env=None):
    out = out or sys.stderr
    """-> 0 ok / report-only, 4 blocked"""
    m = mode(now, env)
    if m == "off":
        return 0
    try:
        bad = findings(tree, sub, skip)
    except OSError as e:
        print(f"SEAL-GATE {who}: could not check {tree}: {e}", file=out)
        return 0
    if not bad:
        return 0
    for b in bad[:20]:
        print(f"SEAL-GATE {who} {'BLOCK' if m == 'block' else 'REPORT-ONLY'}: {b}", file=out)
    print(f"SEAL-GATE {who}: {len(bad)} outside link(s) in {tree}"
          + ("; refused (OT_SEAL_GATE=0 disables)" if m == "block" else f"; becomes blocking at epoch {SEAL_BLOCK_AFTER} (OT_SEAL_GATE=block now, =0 off)"), file=out)
    return 4 if m == "block" else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sub, skip = ("physical",), ("run",)
    if "--sub" in a:
        i = a.index("--sub"); sub = tuple(x for x in a[i + 1].split(",") if x); del a[i:i + 2]
    if "--skip" in a:
        i = a.index("--skip"); skip = tuple(x for x in a[i + 1].split(",") if x); del a[i:i + 2]
    if len(a) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(gate(a[0], a[1], sub, skip))
