#!/usr/bin/env python3 -I
"""tools_lag.py -- WAVE-FLOW-R2 11-17 (COORD, FABLE-FLOW-1300 item 2): TOOLS-LAG per die.

A die's current tree pins tools/ at a main sha (tools_sha, else the tree's v2 marker main_sha, else src_sha 'main@<sha>').  This lists the commits since
that pin that touch a die tool path (tools/die_plan, physical/common_flow) and, of those, the approved fixes: a commit message naming a COORD ruling
rNNN.  Output line: `TOOLS-LAG <die> N commits / missing r535 r554 ...`.

    tools_lag.py [--cfg kit_wave.json] [--repo GIT_DIR] [--main main] [--die D ...]
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DIE_TOOL_PATHS = ("tools/die_plan", "physical/common_flow")
DEFAULT_REPO = "/srv/opentallas-scratch2/git/OpenTallas.git"
RULING_RE = re.compile(r"\b(?:COORD\s+|RULING\s+)?(r\d{3,4})\b")
MAX_LISTED = 40
SEP_REC, SEP_FLD = "\x1e", "\x1f"


def run_git(repo, *args, timeout=120):
    r = subprocess.run(["git", "--git-dir", str(repo), *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode:
        raise ValueError(f"git {' '.join(args[:2])}: {r.stderr.strip()[:200]}")
    return r.stdout


def pin_of(d):
    """the main sha a die's tree pins its tools at: tools_sha, else the tree's v2 marker main_sha, else src_sha 'main@<sha>'; '' when unknown"""
    if d.get("tools_sha"):
        return str(d["tools_sha"])
    tree = d.get("src")
    if tree:
        try:
            m = json.loads((Path(tree) / ".src-manifest.json").read_text())
            if isinstance(m, dict) and m.get("main_sha"):
                return str(m["main_sha"])
        except (OSError, ValueError):
            pass
    s = str(d.get("src_sha") or "")
    return s.split("@", 1)[1] if s.startswith("main@") else (s if re.fullmatch(r"[0-9a-f]{7,40}", s) else "")


def parse_log(text):
    """git log text (see lag()) -> [(sha, subject, [ruling ids], [paths])]"""
    out = []
    for rec in text.split(SEP_REC):
        if not rec.strip():
            continue
        f = rec.split(SEP_FLD)
        if len(f) < 4:
            continue
        sha, subj, body, files = f[0].strip(), f[1], f[2], f[3]
        rules = sorted(set(RULING_RE.findall(subj + "\n" + body)), key=lambda x: int(x[1:]))
        out.append((sha, subj, rules, [x for x in files.split("\n") if x.strip()]))
    return out


def lag(repo, pin, main_ref="main", paths=DIE_TOOL_PATHS):
    """{pin, n_commits, missing: [rNNN], commits: [(sha12, subject, [rNNN])]} for the commits in pin..main_ref that touch a die tool path"""
    if not pin:
        return dict(pin="", n_commits=None, missing=[], commits=[], why="no tools pin known for this tree")
    text = run_git(repo, "log", f"--format={SEP_REC}%H{SEP_FLD}%s{SEP_FLD}%b{SEP_FLD}", "--name-only", f"{pin}..{main_ref}", "--", *paths)
    rows = parse_log(text)
    missing = sorted({r for _, _, rs, _ in rows for r in rs}, key=lambda x: int(x[1:]))
    return dict(pin=str(pin)[:12], n_commits=len(rows), missing=missing, commits=[(s[:12], subj, rs) for s, subj, rs, _ in rows if rs])


def line(die, res):
    if res.get("n_commits") is None:
        return f"TOOLS-LAG {die} unmeasured ({res.get('why')})"
    miss = res["missing"]
    shown = " ".join(miss[:MAX_LISTED]) + (f" +{len(miss) - MAX_LISTED} more" if len(miss) > MAX_LISTED else "")
    return f"TOOLS-LAG {die} {res['n_commits']} commits / missing {shown or 'none'}"


def measure(cfg, repo=DEFAULT_REPO, main_ref="main", dies=None):
    """{die: lag result} for every enabled die of a kit_wave config (errors are recorded per die, never raised)"""
    out = {}
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("enabled") or (dies and die not in dies):
            continue
        try:
            out[die] = lag(repo, pin_of(d), main_ref)
        except (ValueError, OSError, subprocess.TimeoutExpired) as e:
            out[die] = dict(pin=pin_of(d)[:12], n_commits=None, missing=[], commits=[], why=str(e)[:200])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--cfg", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--repo", default=os.environ.get("OT_TOOLS_LAG_REPO", DEFAULT_REPO))
    ap.add_argument("--main", default="main")
    ap.add_argument("--die", action="append")
    a = ap.parse_args(argv)
    res = measure(json.loads(Path(a.cfg).read_text()), a.repo, a.main, a.die)
    for die, r in res.items():
        print(line(die, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
