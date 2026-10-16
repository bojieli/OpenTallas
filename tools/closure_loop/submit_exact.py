#!/usr/bin/env python3
"""submit_exact.py -- SUBMIT ORDER in one step: commit -> push -> gate on that exact commit -> submit, refused LOCALLY.

Why (ROOT, 2026-10-15): the daemon refuses ref_tile jobs whose committed gate result no longer binds to the route
source or to the gate-executed daemon overlays ("SUBMIT_LINT REF_GATE: source_binding ...").  Every refusal audited
was correct (a kit/spec/RTL edit after the gate, or a gate captured before main changed a gate-shipped overlay such
as tools/orfs_hold_mm.tcl), but each was found only after the job reached the daemon.  This helper runs the daemon's
own submit check (pre_route_gate.submit_check against the same repo and daemon tree) before the spec is dropped, prints
the exact differing files (and the main commits that moved an overlay), and optionally re-gates.

    tools/closure_loop/submit_exact.py SPEC.json                         # preflight + submit (no re-gate)
    tools/closure_loop/submit_exact.py SPEC.json --commit-paths P.. -m MSG  # commit those paths first (never -A)
    tools/closure_loop/submit_exact.py SPEC.json --regate [--gate-args "--remote auto --cts --mem 24"]
    tools/closure_loop/submit_exact.py SPEC.json --dry-run               # preflight only

Run it from the worktree that holds the spec's source commit.  Steps:
 1. optional commit by path (--commit-paths) and PUSH to origin/<source.branch> (--no-push to skip); the spec's
    source.commit / name suffix follow HEAD (--follow-head, the default when committing);
 2. fetch origin main (overlay resolution uses origin/main, exactly as the daemon does);
 3. refuse if any consumed path (kit dir, spec sources, source.extra_paths) is dirty in the worktree or differs from
    the spec commit;
 4. refuse unless the source commit is on origin/<source.branch> and every grant/provenance commit the kit names
    (m6_pin_grant source_commit, *grant_commit) exists and is on an origin branch; run the daemon's submit check; on a source_binding refusal print every differing file;
 5. --regate: run pre_route_gate.py <kit> --commit <C> <gate-args>, commit the gate result by path, move the spec to
    that commit, re-check;
 6. drop the spec atomically into the closure-loop drop dir (only after a PASS/WARN).
Exit 0 submitted (or dry-run PASS), 1 refused locally, 2 usage/git error.
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "ref_tile"))
DROP = Path(os.environ.get("CL_REVIEW", "/tmp/claude-review-20261003")) / "closure_jobs"
STATE = Path(os.environ.get("CL_STATE", str(Path.home() / ".local/state/closure_loop")))
SUFFIX = re.compile(r"-([0-9a-f]{7,40})$")


def git(root, *args, check=True):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=600)
    if check and p.returncode:
        raise SystemExit(f"submit_exact: git {' '.join(args)} failed: {p.stderr.strip()[:400]}")
    return p.stdout.strip()


def kit_of(spec):
    m = re.search(r"ref_route\.sh\s+(\S+)/kit\.env", ((spec.get("stages") or {}).get("route") or {}).get("cmd", ""))
    return m.group(1) if m else None


def consumed_paths(spec):
    src = spec.get("source") or {}
    out = [kit_of(spec)] + list(spec.get("sources") or []) + list(src.get("extra_paths") or [])
    return [p for p in out if p]


def move_spec(spec, commit):
    """spec at a new source commit; the conventional '-<commit>' name suffix follows it"""
    c9 = commit[:9]
    # a kit job.json written by `ref_tile.py gen` carries the literal placeholder COMMIT in its name and record paths
    # ("<name>-<tag>-COMMIT"): resolve it to the commit (S-NET+FILL 2026-10-15: five node jobs reached the daemon as
    # "...-n6-COMMIT-<c9>" with record paths ending in "-COMMIT")
    spec = json.loads(re.sub(r'-COMMIT(?=["/])', '-' + c9, json.dumps(spec)))
    spec.setdefault("source", {})["commit"] = c9
    m = SUFFIX.search(spec["name"])
    spec["name"] = (spec["name"][:m.start()] if m else spec["name"]) + "-" + c9
    return spec


def dirty(root, commit, paths):
    """(uncommitted, differs-from-commit) consumed paths"""
    # gate_layout/ (pre_route_gate layout PNGs) is never shipped nor gate-bound: an untracked copy is not a dirty kit
    unc = [ln.split(None, 1)[1] for ln in git(root, "status", "--porcelain", "--", *paths).splitlines()
           if ln.strip() and not (ln.startswith("??") and "/gate_layout/" in "/" + ln.split(None, 1)[1])]
    head = git(root, "rev-parse", "HEAD")
    diff = git(root, "diff", "--name-only", commit, head, "--", *paths).splitlines() if not head.startswith(commit) else []
    return unc, [d for d in diff if d]


def on_origin(root, commit, branch):
    """commit is an ancestor of origin/<branch> after a fresh fetch of that branch (the daemon's sync_source rule)"""
    git(root, "fetch", "-q", "origin", branch, check=False)
    return subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", commit, f"origin/{branch}"],
                          capture_output=True).returncode == 0


def referenced_commits(root, commit, kit):
    """grant/provenance commits a kit names: every '*source_commit' / '*grant_commit' value in the kit's JSON files
    at the spec commit, plus the die-contract slot's m6_pin_grant (ref_tile.contract_slot)"""
    found = {}

    def walk(x, where):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, str) and k.endswith(("source_commit", "grant_commit")) and re.fullmatch(r"[0-9a-f]{7,40}", v):
                    found.setdefault(v, where + ":" + k)
                else:
                    walk(v, where)
        elif isinstance(x, list):
            for v in x:
                walk(v, where)
    for f in git(root, "ls-tree", "-r", "--name-only", commit, "--", kit).splitlines():
        if f.endswith(".json") and not f.endswith(("gate_result.json", "source_snapshot.json")):
            try:
                walk(json.loads(git(root, "show", f"{commit}:{f}")), f)
            except (SystemExit, ValueError):
                pass
    try:
        import ref_tile as RT
        spec = json.loads(git(root, "show", f"{commit}:{kit}/spec.json"))
        slot = RT.contract_slot(spec) or {}
        walk({"m6_pin_grant": slot.get("m6_pin_grant") or {}}, "die contract slot")
    except Exception:  # noqa: BLE001 -- best effort; the daemon's own check still runs below
        pass
    return found


def origin_problems(root, commit, spec, kit):
    out = []
    branch = (spec.get("source") or {}).get("branch")
    if not branch:
        out.append("spec source.branch missing")
    elif not on_origin(root, commit, branch):
        out.append(f"source commit {commit[:12]} is not on origin/{branch} (push it: --push)")
    for c, where in sorted(referenced_commits(root, commit, kit).items()) if kit else ():
        if subprocess.run(["git", "-C", str(root), "cat-file", "-e", c + "^{commit}"], capture_output=True).returncode:
            out.append(f"referenced commit {c} ({where}) does not exist")
        elif not git(root, "branch", "-r", "--contains", c, check=False):
            out.append(f"referenced commit {c} ({where}) is on no origin branch (push it)")
    return out


def binding_diff(root, kit, commit, daemon):
    """every file the committed gate result no longer binds to, with the reason (the daemon prints at most six)"""
    import hashlib
    import helper_overlay as HO
    rows = []
    try:
        d = json.loads(git(root, "show", f"{commit}:{kit}/gate_result.json"))
    except (SystemExit, ValueError):
        return ["(no committed gate_result.json at this commit: run with --regate)"]
    b = d.get("source_binding") or {}
    entries = b.get("files") or []
    used = set(((b.get("consumed") or {}).get("paths")) or [e["path"] for e in entries])
    frozen = b.get("route_overlay_plan") or {}
    gate_main = frozen.get("origin_main")
    ovl = [e["path"] for e in entries if e.get("source") == "daemon_overlay"]
    _, eff = HO.capture_plan(daemon, root, paths=[p for p in ovl if (Path(daemon) / p).is_file()])
    tree = {}
    for ln in git(root, "ls-tree", "-r", commit, "--", *sorted({e["path"] for e in entries if e.get("source") != "daemon_overlay"})).splitlines():
        meta, path = ln.split("\t", 1)
        tree[path] = meta.split()[2]
    for e in entries:
        p = e["path"]
        if e.get("source") == "daemon_overlay":
            now = hashlib.sha256(eff[p]).hexdigest() if p in eff else None
            if now != e["sha256"]:
                moved = git(root, "log", "--oneline", f"{gate_main}..origin/main", "--", p, check=False) if gate_main else ""
                rows.append(f"OVERLAY {p}: gate executed {e['git_blob'][:9]} (origin/main {str(gate_main)[:9]}), daemon now "
                            f"ships {HO.blob_id(eff[p])[:9] if p in eff else 'nothing'}"
                            + (f"; moved by: {' | '.join(moved.splitlines()[:4])}" if moved else ""))
        elif p in used and tree.get(p) != e["git_blob"]:
            rows.append(f"SOURCE  {p}: gate staged {e['git_blob'][:9]}, commit {commit[:9]} has {str(tree.get(p))[:9]}")
    return rows or ["(no per-file difference found; read the daemon message above)"]


def preflight(spec, root, daemon):
    import pre_route_gate as PRG
    PRG.DAEMON_TREE = Path(daemon)
    cfg = {}
    try:
        cfg = json.loads((STATE / "ref_gate.json").read_text())
    except (OSError, ValueError):
        pass
    if spec.get("ref_gate") is False:
        return {"verdict": "SKIP", "message": "spec ref_gate false"}
    closed = False
    c9 = str(spec["source"]["commit"])[:9]
    for f in (STATE / "jobs").glob("*.json") if spec.get("ref_tile") else []:
        try:
            t = f.read_text()
            if f'"block": "{spec["block"]}"' not in t or '"CLOSED"' not in t:
                continue
            x = json.loads(t)
        except (OSError, ValueError):
            continue
        if x.get("status") == "CLOSED" and x["spec"].get("block") == spec["block"] \
                and str((x["spec"].get("source") or {}).get("commit", ""))[:9] == c9:
            closed = True
    kw = dict(closed_stands=closed, clock_mode=str(cfg.get("clock", "refuse"))) if spec.get("ref_tile") else {}
    return PRG.submit_check(spec, str(root), **kw)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--commit-paths", nargs="+", help="commit exactly these paths first (git add -- <paths>)")
    ap.add_argument("-m", "--message", help="commit message for --commit-paths / the gate-result commit")
    ap.add_argument("--follow-head", action="store_true", help="move the spec to HEAD (name suffix too) before checking")
    ap.add_argument("--regate", action="store_true", help="on a source_binding refusal run the gate on the exact commit")
    ap.add_argument("--gate-args", default="--remote auto --cts --mem 24")
    ap.add_argument("--no-push", dest="push", action="store_false",
                    help="do not push HEAD to origin/<source.branch> (default: push after every commit, before the gate)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--daemon-tree", default=os.environ.get("OT_CLOSURE_DAEMON_TREE", "/home/ubuntu/wt-claude-closure-daemon-1010"))
    a = ap.parse_args(argv)
    root = Path(git(Path.cwd(), "rev-parse", "--show-toplevel"))
    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    if a.commit_paths:
        if not a.message:
            raise SystemExit("submit_exact: --commit-paths needs -m")
        git(root, "add", "--", *a.commit_paths)
        if git(root, "diff", "--cached", "--name-only"):
            git(root, "commit", "-m", a.message, "--", *a.commit_paths)
        a.follow_head = True
    if a.follow_head:
        spec = move_spec(spec, git(root, "rev-parse", "HEAD"))

    def push():
        br = (spec.get("source") or {}).get("branch")
        if a.push and br:
            git(root, "push", "-q", "origin", f"HEAD:refs/heads/{br}")
    if a.commit_paths:
        push()
    git(root, "fetch", "-q", "origin", "main", check=False)
    for attempt in (1, 2):
        commit = git(root, "rev-parse", f"{spec['source']['commit']}^{{commit}}")
        paths = consumed_paths(spec)
        unc, diff = dirty(root, commit, paths)
        if unc or diff:
            print("REFUSED LOCALLY (SUBMIT ORDER): consumed paths are not exactly the spec commit "
                  f"{commit[:9]} -- commit first, then gate on that commit:")
            for x in unc:
                print(f"  uncommitted {x}")
            for x in diff:
                print(f"  HEAD differs from spec commit: {x}")
            return 1
        bad = origin_problems(root, commit, spec, kit_of(spec))
        if bad:
            print("REFUSED LOCALLY (not on origin): " + "; ".join(bad))
            return 1
        res = preflight(spec, root, a.daemon_tree)
        v, msg = res.get("verdict"), res.get("message", "")
        print(f"daemon submit check at {commit[:9]}: {v}: {msg[:1500]}")
        if v != "REFUSE":
            break
        kit = kit_of(spec)
        if "source_binding" in msg and kit:
            print("exact gate-binding differences:")
            for r in binding_diff(root, kit, commit, a.daemon_tree):
                print("  " + r)
        if not (a.regate and kit and "source_binding" in msg and attempt == 1):
            print("REFUSED LOCALLY: nothing was submitted" + ("" if a.regate else " (re-gate: add --regate)"))
            return 1
        cmd = [sys.executable, str(root / "tools/ref_tile/pre_route_gate.py"), kit, "--commit", commit,
               *shlex.split(a.gate_args)]
        print("re-gate on the exact commit: " + " ".join(cmd), flush=True)
        if subprocess.run(cmd, cwd=root).returncode:
            print("REFUSED LOCALLY: the gate failed; nothing was submitted")
            return 1
        out = [p for p in (f"{kit}/gate_result.json", f"{kit}/source_binding_history") if (root / p).exists()]
        git(root, "add", "--", *out)
        git(root, "commit", "-m", a.message or f"{kit}: gate result on {commit[:9]} (submit_exact)", "--", *out)
        spec = move_spec(spec, git(root, "rev-parse", "HEAD"))
        push()
    if a.dry_run:
        print(f"DRY RUN: would submit {spec['name']} at {spec['source']['commit']}")
        return 0
    DROP.mkdir(parents=True, exist_ok=True)
    tmp = DROP / f".{spec['name']}.json.tmp"
    tmp.write_text(json.dumps(spec, indent=1) + "\n")
    os.replace(tmp, DROP / f"{spec['name']}.json")
    if spec != json.loads(spec_path.read_text()):
        if root in spec_path.resolve().parents:
            print(f"note: the submitted spec moved to {spec['source']['commit']}; {spec_path} (in the worktree) left as is")
        else:
            spec_path.write_text(json.dumps(spec, indent=1) + "\n")
    print(f"SUBMITTED {spec['name']} (source {spec['source']['commit']}) -> {DROP}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
