#!/usr/bin/env python3 -I
"""tools_lag.py -- WAVE-FLOW-R2 11-17 (COORD, FABLE-FLOW-1300 item 2; FABLE-FLOW-1700 item 1): TOOLS-LAG per die.

A die's current tree pins tools/ at a main sha (tools_sha, else the tree's v2 marker main_sha, else src_sha 'main@<sha>').  A ruling is a tool fix when
lanes/posts/COORD.md carries `COORD APPROVED: <branch> @<sha>` under its `RULING rNNN` line (same line or the lines after it, up to the next RULING).  No commit
message is parsed: the ruling's shas are tested by ancestry.  A ruling is MISSING from a die when every approved sha that main has merged touches a tool path
(tools/, physical/common_flow) and at least one of them is not an ancestor of the die's pin.  tree_has(pin, rNNN | sha) is the same test for hold release terms.
Output line: `TOOLS-LAG <die> N commits / missing r535 r554 ...`.

    tools_lag.py [--cfg kit_wave.json] [--repo GIT_DIR] [--main main] [--posts COORD.md] [--die D ...]
"""
import argparse
import functools
import json
import os
import re
import subprocess
import sys
from pathlib import Path

DIE_TOOL_PATHS = ("tools", "physical/common_flow")              # what a tools-only refresh packs (tools_refresh.TOOL_PATHS)
COORD_POSTS = os.path.expanduser("~/coord/lanes/posts/COORD.md")
DEFAULT_REPO = "/srv/opentallas-scratch2/git/OpenTallas.git"
RULING_HEAD_RE = re.compile(r"\bRULING (r\d{3,4})\b")
APPROVED_RE = re.compile(r"COORD APPROVED:\s*\S+\s*@([0-9a-f]{7,40})")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
RULING_ID_RE = re.compile(r"^r\d{3,4}$")
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


def ruling_shas(text):
    """{rNNN: [sha, ...]} from COORD.md: every `COORD APPROVED: <branch> @<sha>` belongs to the nearest RULING rNNN line before it (or on it)"""
    out, cur = {}, None
    for ln in (text or "").splitlines():
        m = RULING_HEAD_RE.search(ln)
        if m:
            cur = m.group(1)
        if cur:
            for sha in APPROVED_RE.findall(ln):
                if sha not in out.setdefault(cur, []):
                    out[cur].append(sha)
    return {r: v for r, v in out.items() if v}


def load_rulings(path=None):
    try:
        return ruling_shas(Path(path or COORD_POSTS).read_text(errors="replace"))
    except OSError:
        return {}


@functools.lru_cache(maxsize=None)
def _full(repo, sha):
    try:
        return run_git(repo, "rev-parse", "--verify", "-q", sha + "^{commit}").strip()
    except ValueError:
        return ""


@functools.lru_cache(maxsize=None)
def _is_ancestor(repo, a, b):
    r = subprocess.run(["git", "--git-dir", str(repo), "merge-base", "--is-ancestor", a, b], capture_output=True, timeout=60)
    return r.returncode == 0


def ruling_state(repo, pin, shas, main_ref="main", paths=DIE_TOOL_PATHS):
    """-> (state, why) for the approved shas of one ruling vs a tools base: 'has' | 'missing' | 'not_merged' | 'not_tool' (touches no tool path) | 'unknown'.
    Only shas main has merged count; a sha the repo does not know is 'unknown'."""
    full = [(s, _full(repo, s)) for s in shas]
    known = [f for _, f in full if f]
    if not known:
        return "unknown", "no approved sha is in the repo"
    merged = [f for f in known if _is_ancestor(repo, f, main_ref)]
    if not merged:
        return "not_merged", "no approved sha is in main yet"
    pinfull = _full(repo, pin)
    if not pinfull:
        return "unknown", f"pin {pin} not in the repo"
    tool = [f for f in merged if _touches(repo, f, main_ref, tuple(paths))]
    if not tool:
        return "not_tool", "no tool path in the approved branch"
    return ("has" if all(_is_ancestor(repo, f, pinfull) for f in tool) else "missing"), ""


@functools.lru_cache(maxsize=None)
def _touches(repo, sha, main_ref, paths):
    """the approved branch tip changes a tool path (its own commit, else its merge into main)"""
    try:
        if run_git(repo, "diff", "--name-only", f"{sha}^", sha, "--", *paths).strip():
            return True
    except ValueError:
        pass
    return _merge_touches(repo, sha, main_ref, paths)


def clear_caches():
    for f in (_full, _is_ancestor, _touches):
        f.cache_clear()


def _merge_touches(repo, sha, main_ref, paths):
    """a branch tip whose own commit touches no tool path but whose merge into main does (squash / multi-commit branch): the merge diff against its first parent"""
    try:
        out = run_git(repo, "rev-list", "--merges", "--parents", f"{sha}..{main_ref}")
    except ValueError:
        return False
    for ln in out.splitlines():
        f = ln.split()
        if len(f) >= 3 and f[2] == sha:
            return bool(run_git(repo, "diff", "--name-only", f[1], f[0], "--", *paths).strip())
    return False


_HAS_CACHE = {}


def tree_has(repo, pin, token, rulings=None, main_ref="main", ttl=300, now=None):
    """WAVE-FLOW-R2 11-17 (FABLE-FLOW-1700 item 2): True only when the die's tools base `pin` contains the ruling rNNN (all its merged approved shas) or the commit sha.
    Cached 5 min per (pin, token)."""
    import time
    now = time.time() if now is None else now
    key = (str(pin), str(token), str(repo))
    hit = _HAS_CACHE.get(key)
    if hit and now - hit[0] < ttl:
        return hit[1]
    try:
        if SHA_RE.match(token or ""):
            f, pf = _full(repo, token), _full(repo, pin)
            res = bool(f and pf and _is_ancestor(repo, f, pf))
        elif RULING_ID_RE.match(token or ""):
            shas = (rulings if rulings is not None else load_rulings()).get(token) or []
            st, _ = ruling_state(repo, pin, shas, main_ref) if shas else ("unknown", "")
            res = st == "has"
        else:
            res = False
    except (ValueError, OSError, subprocess.TimeoutExpired):
        res = False
    _HAS_CACHE[key] = (now, res)
    return res


def lag(repo, pin, main_ref="main", paths=DIE_TOOL_PATHS, rulings=None):
    """{pin, n_commits, missing: [rNNN], shas: {rNNN: [sha12]}} = commits since the pin touching a tool path, and the approved rulings (COORD.md shas, by ancestry) whose
    tool fix the pin lacks"""
    if not pin:
        return dict(pin="", n_commits=None, missing=[], shas={}, why="no tools pin known for this tree")
    n = int(run_git(repo, "rev-list", "--count", f"{pin}..{main_ref}", "--", *paths).strip() or 0)
    rulings = load_rulings() if rulings is None else rulings
    missing, shas = [], {}
    for r, ss in rulings.items():
        st, _ = ruling_state(repo, pin, ss, main_ref, paths)
        if st == "missing":
            missing.append(r)
            shas[r] = [x[:12] for x in ss]
    missing.sort(key=lambda x: int(x[1:]))
    return dict(pin=str(pin)[:12], n_commits=n, missing=missing, shas=shas)


def line(die, res):
    if res.get("n_commits") is None:
        return f"TOOLS-LAG {die} unmeasured ({res.get('why')})"
    miss = res["missing"]
    shown = " ".join(miss[:MAX_LISTED]) + (f" +{len(miss) - MAX_LISTED} more" if len(miss) > MAX_LISTED else "")
    return f"TOOLS-LAG {die} {res['n_commits']} commits / missing {shown or 'none'}"


def measure(cfg, repo=DEFAULT_REPO, main_ref="main", dies=None, rulings=None, pins=None):
    """{die: lag result} for every enabled die of a kit_wave config (errors are recorded per die, never raised).
    TOOLS-LAG-RT-1122 (FLOW-OPS-R2): PINS {die: sha} = the tools a launch of that die actually runs (kit_wave passes the scheduler's
    rt/<sha> for every die that does not opt out with tools_from_rt false): s81 / qwen_compute were reported 'missing r708' from their
    stale tools_sha while every launch composed rt/current, which has r708.  A die without an entry falls back to pin_of."""
    out = {}
    clear_caches()                    # main moves: the per-sha answers are cached for one measurement only
    for die, d in (cfg.get("dies") or {}).items():
        if not isinstance(d, dict) or not d.get("enabled") or d.get("parked") or (dies and die not in dies):   # F4: a parked die is not measured
            continue
        try:
            pin = str((pins or {}).get(die) or "") or pin_of(d)
            out[die] = lag(repo, pin, main_ref, rulings=rulings)
            out[die]["pin_src"] = "rt" if (pins or {}).get(die) else "tree"
        except (ValueError, OSError, subprocess.TimeoutExpired) as e:
            out[die] = dict(pin=pin_of(d)[:12], n_commits=None, missing=[], shas={}, why=str(e)[:200])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--cfg", default=os.path.expanduser("~/coord/autopilot/kit_wave.json"))
    ap.add_argument("--repo", default=os.environ.get("OT_TOOLS_LAG_REPO", DEFAULT_REPO))
    ap.add_argument("--main", default="main")
    ap.add_argument("--die", action="append")
    ap.add_argument("--posts", default=COORD_POSTS)
    a = ap.parse_args(argv)
    res = measure(json.loads(Path(a.cfg).read_text()), a.repo, a.main, a.die, rulings=load_rulings(a.posts))
    for die, r in res.items():
        print(line(die, r))
    return 0


if __name__ == "__main__":
    sys.exit(main())
