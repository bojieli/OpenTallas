#!/usr/bin/env python3
"""flow_canary reaper (P-POSTPUBLISH-DISK): bound the disk the canary leaves behind.

    reaper.py [--root RUNS] [--ot-delete PATH] [--dry]      (also called from trigger.py main on every tick)

 1. a RUN dir is deleted RUN_TTL_S (24 h) after it closed; closed = canary.json exists or placement_reuse.json accepted, and
    the age is the mtime of that closing file.  A SOURCES/<sha> dir is deleted SRC_TTL_S (12 h) after release, only when no
    existing run dir references it (canary_meta "src") and its worktree lock is gone (trigger.unlock_completed_sources).
 2. a run closed > PRUNE_AFTER_S (1 h) is pruned to the placed odb (3_place.odb), reports/logs/json/rpt/log and the review
    renders; other files >= BIG bytes go through ot-delete (--dry pass first), then a .pruned marker is written.
Never touched: a run without a closing file, with harness/route_approval.json but no closing file, with a live client unit, with
a .keep, or the newest run per die.  ot-delete's own guard is the final check (a SKIP is fine).  OT_CANARY_REAPER=0 turns it off.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OT_DELETE = HERE.parent / "fleet" / "ot-delete"
RUN_TTL_S = 24 * 3600
SRC_TTL_S = 12 * 3600
PRUNE_AFTER_S = 3600
BIG = 1 << 20
CHUNK = 100
MARK = ".pruned"


def jload(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


def closing_file(run):
    for name in ("canary.json", "placement_reuse.json"):
        p = run / name
        if p.is_file():
            if name == "canary.json" or accepted(run):
                return p
    return None


def accepted(run):
    try:
        import importlib.util
        sp = importlib.util.spec_from_file_location("flow_canary_inputs", HERE / "placement_inputs.py")
        m = importlib.util.module_from_spec(sp)
        sp.loader.exec_module(m)
        return bool(m.accepted_reuse(run))
    except Exception:  # noqa: BLE001 -- unknown means open
        return False


def unit_active(unit):
    r = subprocess.run(["systemctl", "--user", "is-active", unit], capture_output=True, text=True)
    return r.stdout.strip() in ("active", "activating", "reloading", "deactivating")


def scan(root, is_closed=closing_file):
    """one record per run dir: path, meta, die, closing file, order key"""
    runs = []
    for p in sorted(Path(root).iterdir()) if Path(root).is_dir() else []:
        if not p.is_dir() or p.is_symlink():
            continue
        meta = jload(p / "canary_meta.json") or {}
        res = jload(p / "canary.json") or {}
        die = (meta.get("spec") or {}).get("die") or res.get("die")
        runs.append(dict(path=p, meta=meta, die=die, closed=is_closed(p),
                         key=meta.get("submitted_at") or p.stat().st_mtime))
    return runs


def newest_per_die(runs):
    best = {}
    for r in runs:
        if r["die"] and (r["die"] not in best or r["key"] > best[r["die"]]["key"]):
            best[r["die"]] = r
    return {str(r["path"]) for r in best.values()}


def busy(r, unit_alive):
    """open route/review: anything that makes the run not safely closed"""
    p = r["path"]
    if r["closed"] is None or (p / ".keep").exists() or (p / ".keep").is_symlink():
        return True
    unit = r["meta"].get("client_unit")
    return bool(unit and unit_alive(unit))


def plan(root, now=None, unit_alive=unit_active, is_closed=closing_file):
    """-> (run dirs to delete, run dirs to prune, source dirs to delete); pure decision, no side effects"""
    now = now or time.time()
    runs = scan(root, is_closed)
    keep_newest = newest_per_die(runs)
    del_runs, prune = [], []
    for r in runs:
        if busy(r, unit_alive) or str(r["path"]) in keep_newest:
            continue
        age = now - r["closed"].stat().st_mtime
        if age > RUN_TTL_S:
            del_runs.append(r["path"])
        elif age > PRUNE_AFTER_S and not (r["path"] / MARK).exists():
            prune.append(r["path"])
    gone = set(del_runs)
    still = set()
    for r in runs:
        if r["path"] not in gone and r["meta"].get("src"):
            still.add(Path(str(r["meta"]["src"])).name)
    srcs = []
    sources = Path(root).parent / "sources"
    for s in sorted(sources.iterdir()) if sources.is_dir() else []:
        if not s.is_dir() or s.is_symlink() or s.name in still or s.name[:12] in still:
            continue
        if locked(s) or now - s.stat().st_mtime < SRC_TTL_S:
            continue
        srcs.append(s)
    # the newest source (by mtime) stays: the trigger may be about to submit on it
    if srcs and sources.is_dir():
        newest = max((x for x in sources.iterdir() if x.is_dir()), key=lambda x: x.stat().st_mtime)
        srcs = [s for s in srcs if s != newest]
    return del_runs, prune, srcs


def locked(source):
    """a snapshot worktree still locked by the trigger is not released"""
    g = source / ".git"
    try:
        if g.is_file():
            text = g.read_text().strip()
            if text.startswith("gitdir: "):
                return (Path(text[8:]) / "locked").exists()
    except OSError:
        return True
    return False


def keep_file(run, f):
    rel = f.relative_to(run).parts
    n = f.name
    if n == "3_place.odb" and "results" in rel and "base" in rel:
        return True
    if any(x in ("logs", "reports", "layout_review") for x in rel[:-1]):
        return True
    if rel[:2] == ("gen", "placement_review") and (n.endswith((".png", ".json"))):
        return True
    return n.endswith((".json", ".rpt", ".log", ".png")) or n in (".keep", MARK)


def prune_files(run):
    out = []
    for dp, _dn, fn in os.walk(run):
        for n in fn:
            f = Path(dp) / n
            try:
                if f.is_symlink() or f.stat().st_size < BIG or keep_file(run, f):
                    continue
            except OSError:
                continue
            out.append(f)
    return out


def run_delete(ot_delete, paths, dry):
    if dry:
        return 0
    n = 0
    for i in range(0, len(paths), CHUNK):
        chunk = [str(p) for p in paths[i:i + CHUNK]]
        subprocess.run([sys.executable, "-I", str(ot_delete), "--dry"] + chunk, capture_output=True, text=True)
        r = subprocess.run([sys.executable, "-I", str(ot_delete)] + chunk, capture_output=True, text=True)
        n += r.returncode == 0
        for line in (r.stdout + r.stderr).splitlines():
            if line.startswith(("SKIP", "ot-delete:")):
                print(f"REAPER {line[:200]}")
    return n


def reap(root, ot_delete=OT_DELETE, dry=False, now=None, unit_alive=unit_active, is_closed=closing_file):
    del_runs, prune, srcs = plan(root, now, unit_alive, is_closed)
    tag = "DRY " if dry else ""
    for r in del_runs:
        print(f"REAPER {tag}delete run {r}")
        run_delete(ot_delete, [r], dry)
    nfiles = 0
    for r in prune:
        files = prune_files(r)
        nfiles += len(files)
        size = sum(f.stat().st_size for f in files if f.exists())
        print(f"REAPER {tag}prune run {r}: {len(files)} files {size >> 20} MiB")
        if not dry and files:
            run_delete(ot_delete, files, dry)
            (r / MARK).write_text("pruned by flow_canary reaper\n")
    for s in srcs:
        print(f"REAPER {tag}delete source {s}")
        run_delete(ot_delete, [s], dry)
    print(f"REAPER {tag}summary: runs {len(del_runs)} prune {len(prune)} ({nfiles} files) sources {len(srcs)}")
    return len(del_runs), len(prune), len(srcs)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default="/srv/opentallas-scratch2/claude/flow-canary/runs")
    ap.add_argument("--ot-delete", default=str(OT_DELETE))
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args(argv)
    if os.environ.get("OT_CANARY_REAPER") == "0":
        print("REAPER off (OT_CANARY_REAPER=0)")
        return 0
    reap(a.root, a.ot_delete, a.dry)
    return 0


if __name__ == "__main__":
    sys.exit(main())
