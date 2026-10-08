#!/usr/bin/env python3
"""End-to-end exactness regression harness (orchestrator; runs on the control host, benches run on the fleet).

    regress.py launch  --ref origin/main [--tier fast|nightly|all] [--bench B ...] [--wait]
    regress.py collect [--commit C]              # fetch finished results, compare, append rows to the log
    regress.py status
    regress.py bisect  --bench B --good G --bad B
    regress.py watch                             # loop: test every new RTL-touching main; nightly main + stream merge

Source under test = `git archive <commit>` of rtl/ tools/ physical memory macros (+ the reduced-vehicle model
configs and oracles), staged on the bench host under /srv/opentallas-scratch/claude/exactness/src/<commit>.
tools/exactness/ itself is overlaid from THIS checkout when the commit predates it (recorded as harness_overlay).
Each bench step runs under /srv/opentallas-scratch/admit.sh with its declared peak (benches.json peak_gb), one
bench at a time per host group, so concurrent sims stay far below 40% of available RAM.
Rows go to /home/ubuntu/claude-takeover-20261007/exactness.log as
  | time PT | bench | target | commit | last pass | result | cycles (expected) | note |
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("OT_REPO", "/home/ubuntu/OpenTallas"))
TAKEOVER = Path("/home/ubuntu/claude-takeover-20261007")
LOG = TAKEOVER / "exactness.log"
STATE = Path(os.path.expanduser("~/.local/state/exactness"))
REMOTE = "/srv/opentallas-scratch/claude/exactness"
ARCHIVE = ["rtl", "tools", "physical/asap7_memory_macros", "physical/hbm_accel_macros",
           "compiler/models/qwen3-reduced-v1", "compiler/models/deepseek-v4.1-flash-reduced-v2",
           ":(glob)results/abi3/*reference_oracle*", "AGENTS.md"]
BUILD_MODELS = REPO / "build/models"          # reduced-vehicle checkpoints (untracked, 43 MB)
STREAM_LOG = {"qwen_rom": "qwen-blocks.log", "hbm_qwen": "hbm-blocks.log", "hbm_ds": "hbm-blocks.log",
              "ds_v41": "s81-blocks.log"}
PT = dt.timezone(dt.timedelta(hours=-7))


def now():
    return dt.datetime.now(PT).strftime("%Y-%m-%d %H:%M PT")


def git(*a, cwd=REPO):
    return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def ssh(host, cmd, check=True, inp=None):
    p = subprocess.run(["ssh", "-o", "BatchMode=yes", host, cmd], capture_output=True, text=True, input=inp)
    if check and p.returncode:
        raise RuntimeError(f"ssh {host} failed: {p.stderr[-500:]}")
    return p.stdout


def merge_state(commit, runs=None, **fields):
    """Read-modify-write one commit's state record under a lock (launch and the watcher's collect race)."""
    import fcntl
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        p = STATE / f"{commit}.json"
        rec = json.loads(p.read_text()) if p.exists() else {"commit": commit, "runs": {}}
        rec.update(fields)
        for name, upd in (runs or {}).items():
            rec["runs"].setdefault(name, {}).update(upd)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec, indent=1) + "\n")
        tmp.replace(p)
        return rec


def manifest():
    return json.loads((HERE / "benches.json").read_text())["benches"]


def select(tier, names):
    bs = manifest()
    if names:
        return [b for b in bs if b["bench"] in names]
    return [b for b in bs if tier == "all" or b["tier"] == tier or (tier == "nightly" and b["tier"] == "fast")]


def stage(commit, host):
    """Export the commit's tree to the host (idempotent)."""
    d = f"{REMOTE}/src/{commit}"
    if ssh(host, f"test -f {d}/SOURCE_COMMIT && echo yes", check=False).strip() == "yes":
        return d
    tmp = f"{d}.part"
    # only the archive paths this commit has (older commits lack some); a failed export never gets a SOURCE_COMMIT
    paths = [a for a in ARCHIVE if a.startswith(":(") or not subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{a}"], cwd=REPO, capture_output=True).returncode]
    if "rtl" not in paths:
        raise RuntimeError(f"{commit} has no rtl/")
    arch = subprocess.Popen(["git", "archive", commit, "--", *paths], cwd=REPO, stdout=subprocess.PIPE)
    gz = subprocess.Popen(["gzip", "-1"], stdin=arch.stdout, stdout=subprocess.PIPE)
    arch.stdout.close()
    subprocess.run(["ssh", host, f"rm -rf {tmp} && mkdir -p {tmp} && tar -xz -C {tmp}"], stdin=gz.stdout, check=True)
    if arch.wait() or gz.wait():
        raise RuntimeError(f"git archive {commit} failed")
    overlay = False
    if subprocess.run(["git", "cat-file", "-e", f"{commit}:tools/exactness/bench.py"], cwd=REPO,
                      capture_output=True).returncode:
        overlay = True
    # The harness itself always comes from this checkout so every commit is measured the same way.
    tar = subprocess.Popen(["tar", "-c", "-C", str(HERE.parent.parent), "tools/exactness"], stdout=subprocess.PIPE)
    subprocess.run(["ssh", host, f"tar -x -C {tmp}"], stdin=tar.stdout, check=True)
    fix = f"{REMOTE}/fixtures/build"
    if ssh(host, f"test -d {fix}/models && echo yes", check=False).strip() != "yes":
        t = subprocess.Popen(["tar", "-c", "-C", str(BUILD_MODELS.parent), "models/qwen3-reduced-v1",
                              "models/deepseek-v4.1-flash-reduced-v2"], stdout=subprocess.PIPE)
        subprocess.run(["ssh", host, f"mkdir -p {fix} && tar -x -C {fix}"], stdin=t.stdout, check=True)
    ssh(host, f"ln -s {fix} {tmp}/build && echo {commit} > {tmp}/SOURCE_COMMIT && "
              f"echo {int(overlay)} > {tmp}/HARNESS_OVERLAY && mv {tmp} {d}")
    return d


def launch(ref, tier="fast", names=None, label=None):
    commit = git("rev-parse", "--short=12", ref)
    benches = select(tier, names)
    groups = {}
    for b in benches:
        groups.setdefault((b["host"], b["group"]), []).append(b)
    new_runs = {}
    for (host, group), bs in groups.items():
        src = stage(commit, host)
        run = f"{REMOTE}/runs/{commit}"
        lines = ["#!/bin/bash", f"cd {src}", "export OMP_NUM_THREADS=16"]
        for b in bs:
            w = f"{run}/{b['bench']}"
            lines += [f"echo running > {w}.state",
                      f"/srv/opentallas-scratch/admit.sh {b['peak_gb']} -- python3 tools/exactness/bench.py "
                      f"{b['bench']} --work {w} > {w}.out 2>&1; echo $? > {w}.exit; echo done > {w}.state"]
            new_runs[b["bench"]] = {"host": host, "work": w, "launched": now(), "logged": False, "label": label or ref,
                                    "verdict": None, "reason": ""}
        # a unique script per launch: bash reads its script lazily, so rewriting a running one corrupts it
        script = f"{run}/{group}-{int(time.time())}.sh"
        ssh(host, f"mkdir -p {run} && cat > {script} && chmod +x {script} && "
                  f"for b in {' '.join(b['bench'] for b in bs)}; do echo queued > {run}/$b.state; done && "
                  f"setsid -f nohup {script} > {script}.nohup 2>&1 < /dev/null", inp="\n".join(lines) + "\n")
    merge_state(commit, new_runs, ref=ref, label=label or ref, subject=git("log", "-1", "--format=%s", commit)[:120])
    print(f"launched {commit} ({tier}): {', '.join(b['bench'] for b in benches)}")
    return commit


def judge(b, r):
    """PASS / FAIL(reason) / ERROR(harness could not measure) against the manifest's expectation."""
    e = b["expect"]
    why = []
    if r.get("error") or (not r.get("exact") and r.get("cycles") is None and not r.get("runs")):
        return "ERROR", r.get("error") or "no measurement (build or harness failure; see the bench .out/logs)"
    if not r.get("exact"):
        why.append(r.get("error") or "not exact")
    for k in ("cycles", "token", "e2e_cycles", "generated", "winning_logit_bits", "logit_bits"):
        if k in e and r.get(k) != e[k]:
            why.append(f"{k} {r.get(k)} != {e[k]}")
    for k, v in e.get("runs_cycles", {}).items():
        got = (r.get("runs") or {}).get(k, {}).get("cycles")
        if got != v:
            why.append(f"{k} cycles {got} != {v}")
    return ("PASS", "") if not why else ("FAIL", "; ".join(why))


def log_row(cells):
    new = not LOG.exists()
    with LOG.open("a") as f:
        if new:
            f.write("# End-to-end exactness regression (stream exactness; harness tools/exactness/regress.py)\n"
                    "| time | bench | target | commit (label) | last pass | result | cycles (expected) | note |\n"
                    "|---|---|---|---|---|---|---|---|\n")
        f.write("| " + " | ".join(str(c) for c in cells) + " |\n")


def last_pass(bench):
    """Most recent PASS commit for the bench in the log, else the manifest's evidence commit."""
    if LOG.exists():
        for line in reversed(LOG.read_text().splitlines()):
            c = [x.strip() for x in line.strip("|").split("|")]
            if len(c) >= 6 and c[1] == bench and c[5] == "PASS":
                return c[3].split()[0]
    return next(b for b in manifest() if b["bench"] == bench)["last_pass"]["commit"]


def collect(commit=None, quiet=False):
    """Fetch finished runs; log each once.  Returns [(commit, bench, verdict, reason)] newly judged."""
    out = []
    by = {b["bench"]: b for b in manifest()}
    for p in sorted(STATE.glob("*.json")) if commit is None else [STATE / f"{commit}.json"]:
        rec = json.loads(p.read_text())
        for name, run in rec["runs"].items():
            if run.get("logged"):
                continue
            st = ssh(run["host"], f"cat {run['work']}.state 2>/dev/null", check=False).strip()
            if st != "done":
                continue
            raw = ssh(run["host"], f"cat {run['work']}/result.json 2>/dev/null", check=False)
            try:
                r = json.loads(raw)
            except ValueError:
                r = {"exact": False, "error": "no result.json (see " + run["work"] + ".out)"}
            b = by[name]
            verdict, why = judge(b, r)
            lp = last_pass(name)
            exp = b["expect"].get("cycles")
            cyc = f"{r.get('cycles'):,}" if isinstance(r.get("cycles"), int) else "-"
            note = why or (f"token {r.get('token')}" if r.get("token") is not None else "")
            if r.get("lint_clean") is False:
                note += " [campaign -Wall lint fails; exactness checks pass]"
            if r.get("bench_wall_seconds"):
                note += f" ({r['bench_wall_seconds'] / 60:.0f} min)"
            log_row([now(), name, b["target"], f"{rec['commit']} ({run.get('label', rec.get('label', ''))})", lp, verdict,
                     f"{cyc} ({exp:,})" if isinstance(exp, int) else cyc, note.strip()])
            run.update(logged=True, verdict=verdict, reason=why, result=r)
            merge_state(rec["commit"], {name: dict(logged=True, verdict=verdict, reason=why, result=r)})
            out.append((rec["commit"], name, verdict, why, run.get("label", rec.get("label", ""))))

    if not quiet:
        status()
    return out


def status():
    for p in sorted(STATE.glob("*.json"), key=lambda q: q.stat().st_mtime)[-6:]:
        rec = json.loads(p.read_text())
        for name, run in rec["runs"].items():
            st = run.get("verdict") or ssh(run["host"], f"cat {run['work']}.state 2>/dev/null", check=False).strip()
            print(f"{rec['commit']} {run.get('label', rec.get('label', '')):20s} {name:18s} {st:8s} {run.get('reason', '')[:100]}")


def pending(label):
    for p in STATE.glob("*.json"):
        rec = json.loads(p.read_text())
        if any(r.get("label", rec.get("label")) == label and not r.get("logged") for r in rec["runs"].values()):
            return True
    return False


def wait_for(commit, benches, poll=120):
    while True:
        rec = json.loads((STATE / f"{commit}.json").read_text())
        if all(rec["runs"].get(b, {}).get("logged") for b in benches):
            return {b: rec["runs"][b]["verdict"] for b in benches}
        collect(commit, quiet=True)
        time.sleep(poll)


def bench_paths(bench, commit):
    """Source paths that can change this bench's result: rtl/ physical/ and the bench's tools."""
    return ["rtl", "physical/asap7_memory_macros", "physical/hbm_accel_macros", "tools"]


def bisect(bench, good, bad):
    """First-parent bisection over commits that touch the bench's sources."""
    good, bad = git("rev-parse", "--short=12", good), git("rev-parse", "--short=12", bad)
    revs = git("rev-list", "--first-parent", "--reverse", f"{good}..{bad}", "--", *bench_paths(bench, bad)).split()
    revs = [r[:12] for r in revs]
    print(f"bisect {bench}: {len(revs)} candidate commits between {good} and {bad}")
    # the good end must PASS under THIS harness (the evidence commit's source was often a scratch snapshot)
    v = wait_for(launch(good, names=[bench], label=f"bisect {bench}"), [bench])[bench]
    if v != "PASS":
        raise RuntimeError(f"bisect {bench}: good end {good} is {v} under the harness; pick a harness-PASS commit")
    lo, hi = -1, len(revs) - 1        # revs[lo] good (good itself), revs[hi] bad
    skipped = set()
    while hi - lo > 1:
        cands = [i for i in range(lo + 1, hi) if i not in skipped]
        if not cands:
            break
        mid = min(cands, key=lambda i: abs(i - (lo + hi) // 2))
        v = wait_for(launch(revs[mid], names=[bench], label=f"bisect {bench}"), [bench])[bench]
        print(f"  {revs[mid]} -> {v}")
        if v == "PASS":
            lo = mid
        elif v == "FAIL":
            hi = mid
        else:
            skipped.add(mid)          # unmeasurable commit (like git bisect skip)
    culprit = revs[hi]
    if any(lo < i < hi for i in skipped):
        print(f"  range not fully resolved: first bad within {revs[lo + 1]}..{revs[hi]} (skipped unmeasurable)")
    msg = git("log", "-1", "--format=%h %an %ad %s", "--date=format:%m-%d %H:%M", culprit)
    print("first bad:", msg)
    return culprit, msg


def report(bench, culprit, msg, reason):
    b = next(x for x in manifest() if x["bench"] == bench)
    line = f"{now()} EXACTNESS {bench} ({b['target']}) FAILS from {msg[:160]}: {reason}\n"
    for name in {STREAM_LOG.get(b["target"], "integrate.log"), "integrate.log"}:
        with (TAKEOVER / name).open("a") as f:
            f.write(line)
    with (TAKEOVER / "READY_TO_MERGE.md").open("a") as f:
        f.write(f"\n## {now()} exactness -- BLOCK MERGE: {bench} ({b['target']}) not exact since {culprit}: "
                f"{reason}. Harness: tools/exactness/regress.py (branch claude/exactness-20261007); "
                f"row in exactness.log.\n")


def merged_streams():
    """Trial-merge every branch named in READY_TO_MERGE.md that is not yet in origin/main (no push)."""
    import re
    text = (TAKEOVER / "READY_TO_MERGE.md").read_text()
    branches = sorted(set(re.findall(r"\b((?:claude|codex)/[A-Za-z0-9._/-]+-20261\d{3}[a-z0-9-]*)", text)))
    subprocess.run(["git", "fetch", "-q", "origin"], cwd=REPO)
    wt = STATE / "trialmerge"
    if not wt.exists():
        git("worktree", "add", "--detach", str(wt), "origin/main")
    git("checkout", "-q", "--detach", "origin/main", cwd=wt)
    git("reset", "-q", "--hard", "origin/main", cwd=wt)
    merged, skipped = [], []
    for br in branches:
        ref = f"origin/{br}"
        if subprocess.run(["git", "rev-parse", "-q", "--verify", ref], cwd=REPO, capture_output=True).returncode:
            continue
        if not subprocess.run(["git", "merge-base", "--is-ancestor", ref, "origin/main"], cwd=REPO).returncode:
            continue
        p = subprocess.run(["git", "-c", "user.name=exactness", "-c", "user.email=exactness@localhost", "merge",
                            "-q", "--no-edit", ref], cwd=wt, capture_output=True, text=True)
        if p.returncode:
            subprocess.run(["git", "merge", "--abort"], cwd=wt)
            skipped.append(br)
        else:
            merged.append(br)
    return git("rev-parse", "--short=12", "HEAD", cwd=wt), merged, skipped


def watch(interval=600, nightly_hour=1):
    seen = STATE / "last_main"
    last_nightly = STATE / "last_nightly"
    while True:
        try:
            subprocess.run(["git", "fetch", "-q", "origin"], cwd=REPO)
            head = git("rev-parse", "--short=12", "origin/main")
            prev = seen.read_text().strip() if seen.exists() else None
            if head != prev and not pending("main"):
                # coalesce: while a main run is in flight, newer heads wait and the newest one is tested next
                touched = git("diff", "--name-only", prev, head, "--", "rtl", "physical/asap7_memory_macros",
                              "physical/hbm_accel_macros", "tools/runtime") if prev else "first"
                if touched:
                    launch(head, "fast", label="main")
                seen.write_text(head)
            today = dt.datetime.now(PT)
            if today.hour == nightly_hour and (not last_nightly.exists() or
                                               last_nightly.read_text().strip() != today.date().isoformat()):
                launch("origin/main", "nightly", names=["qwen_rom_full"], label="nightly main")
                c, merged, skipped = merged_streams()
                if merged:
                    launch(c, "fast", label="nightly main+streams")
                    with LOG.open("a") as f:
                        f.write(f"<!-- {now()} nightly trial merge {c}: {', '.join(merged)}; "
                                f"conflicts skipped: {', '.join(skipped) or 'none'} -->\n")
                last_nightly.write_text(today.date().isoformat())
            for commit, bench, verdict, why, label in collect(quiet=True):
                if verdict == "FAIL" and not label.startswith("bisect"):
                    good = last_pass(bench)
                    try:
                        culprit, msg = bisect(bench, good, commit)
                    except Exception as exc:
                        culprit, msg = commit, f"{good}..{commit} (bisect unresolved: {exc})"
                    report(bench, culprit, msg, why)
        except Exception as exc:  # keep watching; record the failure
            with LOG.open("a") as f:
                f.write(f"<!-- {now()} watch error: {exc!r} -->\n")
        time.sleep(interval)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("launch")
    a.add_argument("--ref", default="origin/main")
    a.add_argument("--tier", default="fast", choices=("fast", "nightly", "all"))
    a.add_argument("--bench", nargs="*")
    a.add_argument("--label")
    a.add_argument("--wait", action="store_true")
    c = sub.add_parser("collect")
    c.add_argument("--commit")
    sub.add_parser("status")
    b = sub.add_parser("bisect")
    b.add_argument("--bench", required=True)
    b.add_argument("--good", required=True)
    b.add_argument("--bad", required=True)
    b.add_argument("--report", action="store_true")
    w = sub.add_parser("watch")
    w.add_argument("--interval", type=int, default=600)
    x = ap.parse_args()
    if x.cmd == "launch":
        commit = launch(x.ref, x.tier, x.bench, x.label)
        if x.wait:
            print(wait_for(commit, [b["bench"] for b in select(x.tier, x.bench)]))
    elif x.cmd == "collect":
        collect(x.commit)
    elif x.cmd == "status":
        status()
    elif x.cmd == "bisect":
        culprit, msg = bisect(x.bench, x.good, x.bad)
        if x.report:
            report(x.bench, culprit, msg, "bisected")
    else:
        watch(x.interval)


if __name__ == "__main__":
    main()
