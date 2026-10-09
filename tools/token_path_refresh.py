#!/usr/bin/env python3
"""Token-path refresh: re-run the re-price and the token-path export whenever their inputs change on origin/main.

No LLM, no new model: this only re-drives the existing tools, in order,
  0. tools/unified_composition.py --check   (regenerates results/arch/unified_composition_20261007/ledger.json if stale)
  1. tools/reprice_20261008.py              (results/arch/reprice_20261008/reprice.json)
  2. tools/token_path_export.py             (results/arch/token_path_20261008/*.json, every design it defines --
                                             qwen_hbm is picked up the moment `def qwen_hbm()` merges)
in a dedicated clean worktree pinned at origin/main, and pushes the changed results to main with a provenance record
(results/arch/token_path_20261008/refresh.json) and a headline diff in the commit message.

Inputs are not a hand-kept list.  Every stage runs under a Python audit hook (also in its subprocesses, through a
generated sitecustomize) that records each repository file opened for reading and each directory listed; the tracked
ones become the input set, stored in refresh.json with their git blob / tree ids.  A refresh compares those ids at the
new origin/main (one `git ls-tree`, no run) and re-runs only when one moved, so the closure records, the cost ledgers,
the composition tools and the re-price items are all covered, and a new input a tool starts reading is picked up on its
first run.  The coverage ledgers (results/arch/coverage_20261008) are watched explicitly.

Outputs that differ only in volatile fields (repo_head) are not committed.  A failed `make check-figures` (pipefail)
blocks the push and is logged; the same input set is not retried until an input moves.

    python3 tools/token_path_refresh.py                 # one refresh (no-op when no input moved)
    python3 tools/token_path_refresh.py --force         # re-run even if no input moved
    python3 tools/token_path_refresh.py --no-push       # run + diff, leave the commit in the worktree
    python3 tools/token_path_refresh.py --status        # what would run, and why
    python3 tools/token_path_refresh.py --install-timer # systemd --user timer, every 15 min

Log: ~/.local/state/token-path-refresh/refresh.log (one block a run).
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("TPR_REPO", str(HOME / "OpenTallas")))
WT = Path(os.environ.get("TPR_WORKTREE", str(HOME / "wt-token-path-refresh")))
STATE_DIR = Path(os.environ.get("TPR_STATE", str(HOME / ".local/state/token-path-refresh")))
VIZ = HOME / ".local/share/fleet-viz/explorer/token"
REF, BRANCH = "origin/main", "main"
ME = "tools/token_path_refresh.py"
TP_OUT = "results/arch/token_path_20261008"
RP_OUT = "results/arch/reprice_20261008"
UNI_OUT = "results/arch/unified_composition_20261007"
PROV = f"{TP_OUT}/refresh.json"
OUT_DIRS = (TP_OUT, RP_OUT, UNI_OUT)
WATCH = ("results/arch/coverage_20261008", ME, "tools/token_path_export.py", "tools/reprice_20261008.py",
         "tools/unified_composition.py")
VOLATILE = ("repo_head",)
STAGES = (
    ("unified", ["tools/unified_composition.py", "--check"], ["tools/unified_composition.py"]),
    ("reprice", ["tools/reprice_20261008.py"], None),
    ("export", ["tools/token_path_export.py", "--viz-dir", "{viz}"], None),
)

SITECUSTOMIZE = r'''
import atexit, json, os, sys
_d = os.environ.get("TPR_TRACE_DIR")
if _d:
    _r, _w, _l = set(), set(), set()
    _WF = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC
    def _tpr_hook(ev, a):
        try:
            if ev == "open":
                p, m, f = a
                if p is None or isinstance(p, int):
                    return
                p = os.path.abspath(os.fsdecode(p))
                w = any(c in m for c in "wax+") if isinstance(m, str) else bool((f or 0) & _WF)
                (_w if w else _r).add(p)
            elif ev in ("os.listdir", "os.scandir"):
                p = a[0] if a else "."
                if p is None:
                    p = "."
                if not isinstance(p, int):
                    _l.add(os.path.abspath(os.fsdecode(p)))
        except Exception:
            pass
    sys.addaudithook(_tpr_hook)
    def _tpr_dump():
        try:
            with open(os.path.join(_d, "t%d.json" % os.getpid()), "w") as fh:
                json.dump(dict(read=sorted(_r), write=sorted(_w), listed=sorted(_l)), fh)
        except Exception:
            pass
    atexit.register(_tpr_dump)
'''


# ------------------------------------------------------------------------------------------------------------ helpers
def log(msg, fh=[None]):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S %Z')} {msg}"
    print(line, flush=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "refresh.log", "a") as f:
        f.write(line + "\n")


def git(*a, cwd=REPO, check=True, text=True):
    r = subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=text)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(a)}: {r.stderr.strip()}")
    return r.stdout if text else r


def show(commit, path):
    r = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def ids_at(commit, paths):
    """{path: git object id at commit or None}; one ls-tree for files and directories alike"""
    out = {p: None for p in paths}
    paths = sorted(paths)
    for i in range(0, len(paths), 500):
        for ln in git("ls-tree", "-z", "--full-tree", commit, "--", *paths[i:i + 500]).split("\0"):
            if "\t" in ln:
                meta, p = ln.split("\t", 1)
                if p in out:
                    out[p] = meta.split()[2]
    return out


def key_of(ids):
    return hashlib.sha256(json.dumps(ids, sort_keys=True).encode()).hexdigest()[:16]


def load_json(b):
    try:
        return json.loads(b) if b else None
    except ValueError:
        return None


def strip(o):
    if isinstance(o, dict):
        return {k: strip(v) for k, v in o.items() if k not in VOLATILE}
    if isinstance(o, list):
        return [strip(v) for v in o]
    return o


def state():
    try:
        return json.loads((STATE_DIR / "state.json").read_text())
    except (OSError, ValueError):
        return {}


def save_state(s):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    (STATE_DIR / "state.json").write_text(json.dumps(s, indent=1) + "\n")


# ----------------------------------------------------------------------------------------------------- input tracking
def input_set(commit, st):
    """the paths whose ids decide a re-run: the last traced set (local state or the committed provenance) + WATCH"""
    prov = load_json(show(commit, PROV)) or {}
    paths = set(WATCH)
    for src in (prov.get("inputs") or {}, st.get("inputs") or {}):
        paths |= set(src)
    return prov, sorted(paths)


def traced_inputs(trace_dir, wt, commit):
    tracked = set(git("ls-tree", "-r", "--name-only", "--full-tree", commit).splitlines())
    tdirs = {str(Path(p).parent) for p in tracked}
    tdirs |= {str(q) for p in list(tdirs) for q in Path(p).parents}
    reads, writes, listed = set(), set(), set()
    root = str(wt.resolve()) + os.sep
    for f in Path(trace_dir).glob("t*.json"):
        t = json.loads(f.read_text())
        for kind, acc in (("read", reads), ("write", writes), ("listed", listed)):
            for p in t[kind]:
                if p.startswith(root):
                    acc.add(p[len(root):])
    out_pfx = tuple(d + "/" for d in OUT_DIRS)
    files = {p for p in reads if p in tracked and not p.startswith(out_pfx)}
    dirs = {p for p in listed if p in tdirs and p != "." and not p.startswith(out_pfx)}
    return sorted(files | dirs), sorted(p for p in writes if p in tracked)


# ------------------------------------------------------------------------------------------------------------ diffing
def headline_rows(index):
    rows = {}
    for d in (index or {}).get("designs", []):
        rows[d["design"]] = dict(tok_s=d.get("tok_s"), cycles=d.get("cycles"),
                                 mtp_tok_s=(d.get("mtp") or {}).get("tok_s"))
    return rows


def flat_numbers(o, pfx=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from flat_numbers(v, f"{pfx}.{k}" if pfx else k)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield pfx, o


def pct(a, b):
    return None if not b else round(100 * (a / b - 1), 3)


def diff_summary(commit, wt):
    old_i = load_json(show(commit, f"{TP_OUT}/index.json"))
    new_i = load_json((wt / TP_OUT / "index.json").read_bytes()) if (wt / TP_OUT / "index.json").exists() else None
    o, n = headline_rows(old_i), headline_rows(new_i)
    heads = []
    for k in sorted(set(o) | set(n), key=lambda k: list(n).index(k) if k in n else 99):
        a, b = o.get(k), n.get(k)
        if a is None:
            heads.append(dict(design=k, new=True, after=b))
        elif b is None:
            heads.append(dict(design=k, removed=True, before=a))
        else:
            heads.append(dict(design=k, before=a, after=b, d_tok_s_pct=pct(b["tok_s"], a["tok_s"]),
                              d_mtp_tok_s_pct=pct(b["mtp_tok_s"], a["mtp_tok_s"]) if a["mtp_tok_s"] and b["mtp_tok_s"] else None))
    # group-level cycle movement per design (top 5)
    groups = {}
    for d in (new_i or {}).get("designs", []):
        f = d["file"]
        a = load_json(show(commit, f"{TP_OUT}/{f}")) or {}
        b = json.loads((wt / TP_OUT / f).read_text())
        ga = {g["id"]: g["cycles"] for g in a.get("groups", [])}
        gb = {g["id"]: g["cycles"] for g in b.get("groups", [])}
        mv = [(g, round(gb.get(g, 0) - ga.get(g, 0), 1)) for g in set(ga) | set(gb)]
        mv = sorted((x for x in mv if abs(x[1]) >= 0.05), key=lambda x: -abs(x[1]))[:5]
        if mv:
            groups[d["design"]] = mv
    # re-price: every changed tok/s leaf
    ra = dict(flat_numbers(load_json(show(commit, f"{RP_OUT}/reprice.json")) or {}))
    rb = dict(flat_numbers(load_json((wt / RP_OUT / "reprice.json").read_bytes()) or {}))
    rp = [dict(key=k, before=ra.get(k), after=rb.get(k)) for k in sorted(set(ra) | set(rb))
          if "tok_s" in k and ra.get(k) != rb.get(k)]
    lines = []
    for h in heads:
        if h.get("new"):
            lines.append(f"{h['design']}: NEW {h['after']['tok_s']} tok/s ({h['after']['cycles']:,} cyc)")
        elif h.get("removed"):
            lines.append(f"{h['design']}: REMOVED (was {h['before']['tok_s']} tok/s)")
        else:
            a, b = h["before"], h["after"]
            s = f"{h['design']}: {a['tok_s']} -> {b['tok_s']} tok/s ({h['d_tok_s_pct']:+.3f} %), {a['cycles']:,} -> {b['cycles']:,} cyc"
            if b["mtp_tok_s"] is not None:
                s += f"; MTP {a['mtp_tok_s']} -> {b['mtp_tok_s']}"
            lines.append(s)
    for k, mv in groups.items():
        lines.append(f"  {k} groups: " + ", ".join(f"{g} {c:+,.1f}" for g, c in mv))
    for r in rp[:12]:
        lines.append(f"  reprice {r['key']}: {r['before']} -> {r['after']}")
    if len(rp) > 12:
        lines.append(f"  reprice: {len(rp) - 12} more tok/s leaves changed")
    return dict(headlines=heads, groups=groups, reprice=rp, lines=lines)


# -------------------------------------------------------------------------------------------------------------- run
def ensure_worktree(commit):
    marker = WT / ".token-path-refresh-owned"
    if WT.resolve() == REPO.resolve():
        raise RuntimeError("refresh requires its own worktree, separate from the central checkout")
    if (WT / ".git").exists():
        if not marker.is_file() or marker.read_text().strip() != str(REPO.resolve()):
            raise RuntimeError(f"refusing to reset an existing unmanaged worktree: {WT}")
    else:
        git("worktree", "add", "--detach", str(WT), commit)
        marker.write_text(str(REPO.resolve()) + "\n")
    git("reset", "-q", "--hard", cwd=WT)
    git("clean", "-qfd", "--", *OUT_DIRS, "tools", cwd=WT)
    git("checkout", "-q", "--detach", commit, cwd=WT)


def run_stages(commit, tmp):
    tdir = tmp / "trace"
    tdir.mkdir()
    (tmp / "site").mkdir()
    (tmp / "site" / "sitecustomize.py").write_text(SITECUSTOMIZE)
    viz = tmp / "viz"
    env = dict(os.environ, TPR_TRACE_DIR=str(tdir), PYTHONDONTWRITEBYTECODE="1",
               PYTHONPATH=os.pathsep.join([str(tmp / "site")] + [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]))
    done = []
    for name, argv, fallback in STAGES:
        argv = [x.format(viz=viz) for x in argv]
        t0 = time.time()
        r = subprocess.run([sys.executable, *argv], cwd=WT, env=env, capture_output=True, text=True)
        rec = dict(stage=name, argv=argv, rc=r.returncode, seconds=round(time.time() - t0, 1),
                   stdout_tail=r.stdout.strip().splitlines()[-12:])
        if r.returncode and fallback:          # unified --check: stale ledger -> regenerate it
            t0 = time.time()
            r = subprocess.run([sys.executable, *fallback], cwd=WT, env=env, capture_output=True, text=True)
            rec.update(regenerated=True, regen_rc=r.returncode, seconds=round(rec["seconds"] + time.time() - t0, 1),
                       stdout_tail=r.stdout.strip().splitlines()[-12:])
        done.append(rec)
        log(f"  stage {name}: rc {r.returncode} in {rec['seconds']} s" + (" (ledger regenerated)" if rec.get("regenerated") else ""))
        if r.returncode:
            raise RuntimeError(f"stage {name} failed: {r.stderr.strip()[-2000:]}")
    inputs, wrote = traced_inputs(tdir, WT, commit)
    return done, inputs, wrote, viz


def changed_outputs(commit):
    """output files that differ from `commit` beyond VOLATILE fields; restores the volatile-only ones"""
    st = git("status", "--porcelain", "-uall", "--", *OUT_DIRS, cwd=WT).splitlines()
    real = []
    for ln in st:
        p = ln[3:]
        old = show(commit, p)
        new = (WT / p).read_bytes() if (WT / p).exists() else None
        if p.endswith(".json") and old is not None and new is not None:
            a, b = load_json(old), load_json(new)
            if a is not None and strip(a) == strip(b):
                git("checkout", "-q", commit, "--", p, cwd=WT)
                continue
        real.append(p)
    return real


def install_viz(viz, dest):
    if not dest or not (viz / "data").is_dir():
        return 0
    d = Path(dest) / "data"
    if not Path(dest).is_dir():
        return 0
    d.mkdir(exist_ok=True)
    n = 0
    for f in (viz / "data").glob("*.json"):
        if not (d / f.name).exists() or (d / f.name).read_bytes() != f.read_bytes():
            shutil.copy(f, d / f.name)
            n += 1
    return n


def check_figures():
    r = subprocess.run(["bash", "-c", "set -o pipefail; make check-figures 2>&1 | tail -20"], cwd=WT, capture_output=True, text=True)
    return r.returncode == 0, r.stdout.strip().splitlines()[-6:]


def push(msg, paths, base):
    git("add", "--", *paths, cwd=WT)
    git("-c", "user.name=OpenTallas token-path refresh", "commit", "-q", "-m", msg, cwd=WT)
    for attempt in range(6):
        r = git("push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}", cwd=WT, check=False, text=False)
        if r.returncode == 0:
            return git("rev-parse", "--short=9", "HEAD", cwd=WT).strip()
        git("fetch", "-q", "origin", BRANCH, cwd=WT)
        if git("rev-parse", REF, cwd=WT).strip() != base:
            # Rebasing stale generated numbers onto newer source would misstate
            # their provenance. The next refresh regenerates from the new base.
            raise RuntimeError("main advanced during refresh; regenerate from its new inputs before pushing")
        time.sleep(3 + 5 * attempt)
    raise RuntimeError("push rejected 6 times")


def refresh(a):
    git("fetch", "-q", "origin", BRANCH)
    commit = git("rev-parse", REF).strip()
    st = state()
    prov, paths = input_set(commit, st)
    ids = ids_at(commit, paths)
    key = key_of(ids)
    moved = sorted(p for p in paths if ids[p] != ((prov.get("inputs") or {}).get(p) or (st.get("inputs") or {}).get(p)))
    if a.status:
        print(json.dumps(dict(ref=commit[:9], key=key, last_key=st.get("last_key"), committed_key=prov.get("key"),
                              n_inputs=len(paths), would_run=a.force or key not in (st.get("last_key"), prov.get("key")),
                              moved=moved[:40]), indent=1))
        return 0
    if not a.force and key in (st.get("last_key"), prov.get("key")):
        if st.get("last_key") != key:
            st.update(last_key=key, inputs={p: ids[p] for p in paths}, last_commit=commit[:9], last_result="up to date")
            save_state(st)
        return 0
    log(f"refresh at {commit[:9]}: {len(moved)} of {len(paths)} inputs moved: {', '.join(moved[:12])}{' ...' if len(moved) > 12 else ''}")
    ensure_worktree(commit)
    if (WT / ME).read_bytes() != Path(__file__).read_bytes() and not a.no_reexec:
        log("  refresh tool changed on main: re-exec the new version")
        os.execv(sys.executable, [sys.executable, str(WT / ME), *sys.argv[1:], "--no-reexec"])
    t0 = time.time()
    with tempfile.TemporaryDirectory(prefix="tpr-") as td:
        stages, inputs, wrote, viz = run_stages(commit, Path(td))
        new_ids = ids_at(commit, sorted(set(inputs) | set(WATCH)))
        new_key = key_of(new_ids)
        outs = changed_outputs(commit)
        res = dict(commit=commit[:9], key=new_key, inputs=new_ids)
        if not outs:
            n = install_viz(viz, a.viz_dir)
            log(f"  no output change ({len(new_ids)} traced inputs; {time.time() - t0:.0f} s); viz files updated {n}")
            st.update(last_key=new_key, inputs=new_ids, last_commit=commit[:9], last_result="no output change")
            save_state(st)
            return 0
        summ = diff_summary(commit, WT)
        rec = dict(schema="opentallas.token_path.refresh.v1", tool=ME, base_commit=commit,
                   generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), key=new_key,
                   rule="re-runs unified_composition --check / reprice_20261008 / token_path_export, unchanged, whenever a "
                        "traced input moves on origin/main; no new model, no LLM",
                   moved_inputs=moved, stages=stages, outputs=sorted(outs), headlines=summ["headlines"],
                   group_moves=summ["groups"], reprice_changes=summ["reprice"], summary=summ["lines"], inputs=new_ids)
        (WT / PROV).write_text(json.dumps(rec, indent=1) + "\n")
        for ln in summ["lines"]:
            log("  " + ln)
        ok, tail = check_figures()
        log(f"  make check-figures (pipefail): {'PASS' if ok else 'FAIL'}" + ("" if ok else " | " + " | ".join(tail)))
        msg = ("token-path refresh (auto): re-export + re-price at " + commit[:9] + "\n\n" + "\n".join(summ["lines"])
               + f"\n\nmoved inputs ({len(moved)}): " + ", ".join(moved[:20]) + (" ..." if len(moved) > 20 else "")
               + "\ntool: tools/token_path_refresh.py (no LLM); provenance " + PROV + "\n")
        if not ok or a.no_push:
            res.update(last_result="check-figures FAIL" if not ok else "not pushed (--no-push)")
            st.update(last_key=new_key, inputs=new_ids, last_commit=commit[:9], last_result=res["last_result"])
            save_state(st)
            if a.no_push and ok:
                git("add", "--", *outs, PROV, cwd=WT)
                git("-c", "user.name=OpenTallas token-path refresh", "commit", "-q", "-m", msg, cwd=WT)
                log(f"  committed in {WT} (not pushed)")
            return 0 if ok else 2
        sha = push(msg, outs + [PROV], commit)
        n = install_viz(viz, a.viz_dir)
        log(f"  pushed main {sha} ({time.time() - t0:.0f} s); viz files updated {n}")
        st.update(last_key=new_key, inputs=new_ids, last_commit=commit[:9], last_result=f"pushed {sha}")
        save_state(st)
    return 0


UNIT = """[Unit]
Description=OpenTallas token-path refresh (re-price + token-path export on origin/main input change; no LLM)

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 {script}
Nice=10
CPUQuota=200%
MemoryMax=8G
TimeoutStartSec=3h
"""
TIMER = """[Unit]
Description=Token-path refresh every 15 min

[Timer]
OnCalendar=*:0/15
Persistent=true
RandomizedDelaySec=60

[Install]
WantedBy=timers.target
"""


def install_timer():
    if not (WT / ".git").exists():
        git("fetch", "-q", "origin", BRANCH)
        git("worktree", "add", "--detach", str(WT), REF)
    d = HOME / ".config/systemd/user"
    d.mkdir(parents=True, exist_ok=True)
    (d / "token-path-refresh.service").write_text(UNIT.format(script=WT / ME))
    (d / "token-path-refresh.timer").write_text(TIMER)
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "token-path-refresh.timer"], check=True)
    print(f"installed: {d}/token-path-refresh.{{service,timer}} running {WT / ME}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="re-run even if no input moved")
    ap.add_argument("--no-push", action="store_true", help="commit in the refresh worktree, do not push")
    ap.add_argument("--status", action="store_true", help="print the input check and exit")
    ap.add_argument("--viz-dir", default=str(VIZ) if VIZ.is_dir() else "",
                    help="installed token-view dir whose data/ gets the new records ('' = none)")
    ap.add_argument("--install-timer", action="store_true")
    ap.add_argument("--no-reexec", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    if a.install_timer:
        return install_timer()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATE_DIR / "lock", "w") as lk:
        try:
            fcntl.flock(lk, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("another refresh is running")
            return 0
        try:
            return refresh(a)
        except Exception as e:
            log(f"  ERROR {type(e).__name__}: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
