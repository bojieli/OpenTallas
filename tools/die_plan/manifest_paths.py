#!/usr/bin/env python3
"""Gate: an as-built bind manifest must name only repository-relative paths that stay inside the repository.

TOK-SCHED 10-25: the S81 main manifest read a frozen worktree (wt/tok-ds-bind178@650532346d) through absolute paths,
so main's strict bind checked 06:23 RTL and reported 12,800 false multi-driven nets.  A manifest that lives in the
repository is a source of record and must bind exactly the sources of the checkout it is in.

Rules (each path is resolved the way tools/die_plan/bind.py resolves it):
  - files / prefer / netlist / rtl_roots / hard_params: relative to `base` (base relative to the manifest directory;
    default = the repository root);
  - map_file: relative to the manifest directory (bind.py --asbuilt) or the repository root (in-plan section);
  - no path may be absolute, and none may resolve outside the repository (no `..` escape, no symlink escape).
Usage: manifest_paths.py MANIFEST.json [...]   (exit 1 and one line per bad path on failure)
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIST_KEYS = ("files", "prefer", "netlist", "rtl_roots", "hard_params")


def _inside(p, root):
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check(ab, manifest_dir, repo=REPO, override=True):
    """errors (list of str) for one as-built section `ab` whose file sits in `manifest_dir`."""
    repo = Path(repo)
    manifest_dir = Path(manifest_dir)
    errs = []
    b = ab.get("base")
    if b is None:
        base = repo
    elif Path(b).is_absolute():
        errs.append(f"base: absolute path {b!r}")
        base = Path(b)
    else:
        base = manifest_dir / b
        if not _inside(base, repo):
            errs.append(f"base: {b!r} resolves outside the repository ({base.resolve()})")
    for k in LIST_KEYS:
        v = ab.get(k) or []
        if isinstance(v, str):
            v = [v]
        for p in v:
            if not isinstance(p, str):
                continue
            if Path(p).is_absolute():
                errs.append(f"{k}: absolute path {p!r}")
            elif not _inside(base / p, repo):
                errs.append(f"{k}: {p!r} resolves outside the repository ({(base / p).resolve()})")
    mf = ab.get("map_file")
    if isinstance(mf, str):
        if Path(mf).is_absolute():
            errs.append(f"map_file: absolute path {mf!r}")
        else:
            r = (manifest_dir if override else repo) / mf
            if not _inside(r, repo):
                errs.append(f"map_file: {mf!r} resolves outside the repository ({r.resolve()})")
    return errs


def check_file(path, repo=REPO):
    path = Path(path)
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and isinstance(raw.get("asbuilt"), dict):
        return check(raw["asbuilt"], path.parent, repo, override=False)
    return check(raw, path.parent, repo, override=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    bad = 0
    for f in argv:
        errs = check_file(f)
        for e in errs:
            print(f"{f}: {e}")
        print(f"{f}: {'FAIL ' + str(len(errs)) + ' external path(s)' if errs else 'PASS repo-relative'}")
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
