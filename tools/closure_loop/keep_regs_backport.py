#!/usr/bin/env python3
"""FLOW-FIX-0410 2026-10-09: requeue a route on its OWN source commit with the keep-regs synthesis fix backported.

A job's source snapshot carries its own flow: a commit older than the keep-regs hook (main 0d3958d56, per-bit form
816a3bec0) synthesises with the stock ORFS opt_merge, which folds (* keep *) register copies back into one flop.  This
helper makes a minimal branch  claude/keepregs-<c9>-20261009  =  <source commit>
  + physical/common_flow/ot_keep_regs.tcl          (the current hook, taken from --hook-ref, default origin/main)
  + the SYNTH_CANONICALIZE_TCL config line          (tools/run_abi3_physical.py keep_regs_config_lines + the call in
                                                     run_pnr; tools/hbm_accel_smh_physical.py config_mk), inserted by
                                                     anchor (no context patch), skipped where the source has it already
  + optional --overlay PATH[@REF] files             (e.g. an attribute-only RTL fix: rtl/...sv@<commit>)
and pushes it.  RTL and every other file are byte-identical to the source commit, so the exact benches of the original
job still apply unchanged (an --overlay must be function-preserving; the job's own benches re-run on the new commit).

--requeue JOB [--as NAME] then writes a copy of that job's spec (from the loop's job state) to the intake drop dir with
the new source branch/commit, a new name (default <job>-kr, <= 100 chars) and a purpose note.  --dry-run prints the
spec instead of dropping it.

  keep_regs_backport.py --source <commit> [--overlay rtl/x.sv@<ref> ...] [--requeue JOB [--as NAME] ...] [--dry-run]
  keep_regs_backport.py --source <commit> --keep-source --requeue JOB --as NAME --why "..."   (plain requeue)
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
from pathlib import Path

REPO = Path(os.environ.get("OT_REPO", "/home/ubuntu/OpenTallas"))
JOBS = Path.home() / ".local/state/closure_loop/jobs"
DROP = Path("/tmp/claude-review-20261003/closure_jobs")
HOOK = "physical/common_flow/ot_keep_regs.tcl"
RUN = "tools/run_abi3_physical.py"
SMH = "tools/hbm_accel_smh_physical.py"
TRAILER = ("Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
           "Claude-Session: https://claude.ai/code/session_01NS3WNDSm3d3xCxNi9T5CWn")

RUN_FN = '''KEEP_REGS_HOOK = "/src/physical/common_flow/ot_keep_regs.tcl"


def keep_regs_config_lines(config: list[str]) -> list[str]:
    """FLOW-FIX-0410 2026-10-09 (keep-regs backport): (* keep *) register copies survive the ORFS yosys opt_merge.
    Default on; OT_KEEP_REGS=0 or a config that already names its own SYNTH_CANONICALIZE_TCL omits it."""
    if os.environ.get("OT_KEEP_REGS", "1").strip() == "0":
        return []
    if any(line.startswith("export SYNTH_CANONICALIZE_TCL") for line in config):
        return []
    if not (ROOT / "physical/common_flow/ot_keep_regs.tcl").is_file():
        return []
    return [f"export SYNTH_CANONICALIZE_TCL = {KEEP_REGS_HOOK}"]


'''
SMH_LINES = ('    # FLOW-FIX-0410: (* keep *) register copies survive yosys opt_merge (physical/common_flow/ot_keep_regs.tcl)\n'
             '    if os.environ.get("OT_KEEP_REGS", "1").strip() != "0" and "SYNTH_CANONICALIZE_TCL" not in extra:\n'
             '        lines.append("export SYNTH_CANONICALIZE_TCL = /src/physical/common_flow/ot_keep_regs.tcl")\n')


def git(*a, cwd=REPO, check=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise SystemExit(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout.strip()


def patch_run(text: str) -> str:
    """insert keep_regs_config_lines + its call in run_pnr; unchanged if the source has them"""
    if "def keep_regs_config_lines" not in text:
        anchor = "\ndef design_nickname("
        if anchor not in text:
            raise ValueError("run_abi3_physical.py: no `def design_nickname(` anchor")
        text = text.replace(anchor, "\n" + RUN_FN.rstrip("\n") + "\n\n\n" + anchor.lstrip("\n"), 1)
    if "config.extend(keep_regs_config_lines(config))" not in text:
        m = re.search(r"\n(\s*)config = orfs_config_lines\(\n(?:.*\n)*?\s*\)\n", text)
        if not m:
            raise ValueError("run_abi3_physical.py: no `config = orfs_config_lines(...)` call in run_pnr")
        text = text[:m.end()] + f"{m.group(1)}config.extend(keep_regs_config_lines(config))\n" + text[m.end():]
    if not re.search(r"^import os\b|^import .*\bos\b", text, re.M):
        raise ValueError("run_abi3_physical.py does not import os")
    return text


def patch_smh(text: str) -> str:
    if "SYNTH_CANONICALIZE_TCL" in text:
        return text
    anchor = '    lines += [f"export {k} = {v}" for k, v in extra.items()]\n'
    if anchor not in text:
        raise ValueError("hbm_accel_smh_physical.py: no extra-lines anchor in config_mk")
    return text.replace(anchor, anchor + SMH_LINES, 1)


def backport(source: str, hook_ref: str, overlays: list[str], push: bool = True) -> tuple[str, str]:
    full = git("rev-parse", f"{source}^{{commit}}")
    tag = full[:9]
    suffix = ("-ov" + hashlib.sha1("\n".join(sorted(overlays)).encode()).hexdigest()[:6]) if overlays else ""
    branch = f"claude/keepregs-{tag}{suffix}-20261009"
    git("fetch", "-q", "origin")
    if git("ls-remote", "--heads", "origin", branch):
        git("fetch", "-q", "origin", branch)
        return branch, git("rev-parse", f"origin/{branch}")
    wt = Path(tempfile.mkdtemp(prefix=f"kr-{tag}-", dir="/tmp/claude-1000"))
    git("worktree", "add", "-q", "--detach", str(wt), full)
    try:
        hook = git("show", f"{hook_ref}:{HOOK}")
        (wt / HOOK).parent.mkdir(parents=True, exist_ok=True)
        (wt / HOOK).write_text(hook + "\n")
        paths = [HOOK]
        for rel, fn in ((RUN, patch_run), (SMH, patch_smh)):
            p = wt / rel
            if p.is_file():
                new = fn(p.read_text())
                compile(new, rel, "exec")
                p.write_text(new)
                paths.append(rel)
        for ov in overlays:
            rel, _, ref = ov.partition("@")
            data = git("show", f"{ref or hook_ref}:{rel}")
            (wt / rel).parent.mkdir(parents=True, exist_ok=True)
            (wt / rel).write_text(data + "\n")
            paths.append(rel)
        git("add", "--", *paths, cwd=wt)
        if not git("diff", "--cached", "--name-only", cwd=wt):
            return "", full                      # the source already carries the current hook: requeue it as is
        msg = (f"keep-regs backport onto {tag}: (* keep *) register copies survive yosys opt_merge "
               f"({hook_ref} ot_keep_regs.tcl + SYNTH_CANONICALIZE_TCL config line)"
               + (f"; overlays {', '.join(overlays)}" if overlays else "; RTL unchanged") + "\n\n" + TRAILER)
        git("-c", "user.name=Bojie Li", "-c", "user.email=bojieli@gmail.com", "commit", "-q", "-m", msg, cwd=wt)
        head = git("rev-parse", "HEAD", cwd=wt)
        if push:
            git("push", "-q", "origin", f"HEAD:refs/heads/{branch}", cwd=wt)
        return branch, head
    finally:
        git("worktree", "remove", "--force", str(wt), check=False)


def requeue(job: str, new: str, branch: str, commit: str, why: str, dry: bool) -> dict:
    j = json.loads((JOBS / f"{job}.json").read_text())
    spec = json.loads(json.dumps(j.get("spec_submitted") or j["spec"]))
    spec["name"] = new
    spec["source"]["branch"] = branch or spec["source"].get("branch")
    spec["source"]["commit"] = commit
    spec["purpose"] = (f"FLOW-FIX-0410 keep-regs requeue of {job} on {commit[:9]} ({why}). " + spec.get("purpose", ""))[:2000]
    spec.pop("submit_lint", None)
    if dry:
        print(json.dumps({"name": new, "source": spec["source"]}, indent=1))
    else:
        DROP.mkdir(parents=True, exist_ok=True)
        if (DROP / f"{new}.json").exists() or (JOBS / f"{new}.json").exists():
            raise SystemExit(f"{new}: a job of that name exists")
        (DROP / f"{new}.json").write_text(json.dumps(spec, indent=1) + "\n")
    return spec


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--source", required=True)
    ap.add_argument("--hook-ref", default="origin/main")
    ap.add_argument("--overlay", action="append", default=[], help="PATH[@REF] copied onto the source (default REF = hook ref)")
    ap.add_argument("--requeue", action="append", default=[], help="job name to requeue on the backport")
    ap.add_argument("--as", dest="as_", action="append", default=[], help="new name per --requeue (default <job>-kr)")
    ap.add_argument("--why", default="replicas folded by opt_merge on the source flow")
    ap.add_argument("--keep-source", action="store_true",
                    help="no backport: requeue on the source commit as is (a daemon-side fix such as the io_ref active edge)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.keep_source:
        branch, commit = "", git("rev-parse", f"{a.source}^{{commit}}")
    else:
        branch, commit = backport(a.source, a.hook_ref, a.overlay, push=not a.dry_run)
    print(json.dumps({"branch": branch, "commit": commit}))
    for i, job in enumerate(a.requeue):
        new = a.as_[i] if i < len(a.as_) else (job[:97] + "-kr")
        requeue(job, new, branch, commit, a.why, a.dry_run)
        print(f"{'DRY ' if a.dry_run else ''}REQUEUED {job} -> {new} @ {commit[:9]}")


if __name__ == "__main__":
    main()
