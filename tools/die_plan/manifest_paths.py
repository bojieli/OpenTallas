#!/usr/bin/env python3
"""Evidence gate (closure order rule 3, OWNER 2026-10-25 18:45): a bind, LEC or token input manifest must name only
repository-relative paths inside the repository, and a bind, LEC or token result is evidence only if it names the
commit it was made at.

Why: the S81 main manifest read a frozen worktree (wt/tok-ds-bind178@650532346d) through absolute paths, so main's
strict bind checked 06:23 RTL and reported 12,800 false multi-driven nets.

Input manifests (any die: s81, qwen_compute, qwen_kvsys, hbm):
  --kind bind  : an as-built section (own file, or the `asbuilt` key of a die plan).  Each path is resolved the way
                 tools/die_plan/bind.py resolves it: files / prefer / netlist / rtl_roots / hard_params against `base`
                 (base relative to the manifest directory; default the repository root); map_file against the manifest
                 directory (own file) or the repository root (in-plan section).
  --kind lec / token / any (default `auto`: bind when the JSON has bind keys, else generic): every string value in the
                 JSON that is a path (absolute, ~/..., or relative with a `..` that leaves the repository) is checked.
  FAIL: an absolute path, or a path that resolves outside the repository.
Result records (--result): the JSON must carry a provenance commit (provenance.commit, or source_commit / commit /
  git_commit at the top level) that is a 7-40 hex sha, and (when the repository has git) that commit must exist here.
Usage: manifest_paths.py [--kind K] [--result] FILE.json [...]   exit 1 and one line per problem on failure.
Library: check(ab, dir) (bind section), check_generic(obj, dir), check_file(path, kind), provenance(repo),
  check_result(rec).
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIST_KEYS = ("files", "prefer", "netlist", "rtl_roots", "hard_params")
BIND_KEYS = ("netlist", "rtl_roots", "files", "prefer")
COMMIT_KEYS = ("source_commit", "commit", "git_commit")
SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")
# a string that is a path: absolute (/x/y), home (~/x), or relative containing a .. component
ABS_RE = re.compile(r"^(/[^/\s]+){2,}/?$|^~/")
REL_RE = re.compile(r"^[\w.+-]+(/[\w.+@-]+)+/?$")


def _inside(p, root):
    try:
        Path(p).resolve().relative_to(Path(root).resolve())
        return True
    except ValueError:
        return False


def check(ab, manifest_dir, repo=REPO, override=True):
    """errors (list of str) for one bind as-built section `ab` whose file sits in `manifest_dir`."""
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


def _strings(obj, where=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _strings(v, f"{where}.{k}" if where else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _strings(v, f"{where}[{i}]")
    elif isinstance(obj, str):
        yield where, obj


def check_generic(obj, manifest_dir, repo=REPO):
    """errors for any JSON input manifest (LEC kit/port-map/hints config, token recipe, cohort list): every path-like
    string must be repository-relative (relative paths resolve against the repository root or the manifest
    directory; either inside is accepted, an escape from both fails)."""
    errs = []
    for where, s in _strings(obj):
        if ABS_RE.match(s):
            errs.append(f"{where}: absolute path {s!r}")
        elif REL_RE.match(s) and ".." in s.split("/"):
            if not (_inside(Path(repo) / s, repo) or _inside(Path(manifest_dir) / s, repo)):
                errs.append(f"{where}: {s!r} resolves outside the repository")
    return errs


def _is_bind(raw):
    ab = raw.get("asbuilt") if isinstance(raw, dict) and isinstance(raw.get("asbuilt"), dict) else raw
    return isinstance(ab, dict) and any(k in ab for k in BIND_KEYS)


def check_file(path, repo=REPO, kind="auto"):
    path = Path(path)
    raw = json.loads(path.read_text())
    if kind == "bind" or (kind == "auto" and _is_bind(raw)):
        if isinstance(raw, dict) and isinstance(raw.get("asbuilt"), dict):
            return check(raw["asbuilt"], path.parent, repo, override=False)
        return check(raw, path.parent, repo, override=True)
    return check_generic(raw, path.parent, repo)


def provenance(repo=REPO):
    """{commit, dirty, repo} of the checkout the tools run from.  A staged cohort without .git names its commit in
    cohort.json (source_commit) or SOURCE_COMMIT; otherwise commit is None and the result fails the evidence gate."""
    repo = Path(repo)
    rec = dict(commit=None, dirty=None, source="none")
    try:
        r = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and SHA_RE.match(r.stdout.strip()):
            st = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, timeout=120)
            return dict(commit=r.stdout.strip(), dirty=bool(st.stdout.strip()) if st.returncode == 0 else None,
                        source="git")
    except (OSError, subprocess.SubprocessError):
        pass
    for f, key in ((repo / "cohort.json", "source_commit"), (repo / "SOURCE_COMMIT", None)):
        try:
            if key:
                c = json.loads(f.read_text()).get(key)
            else:
                c = f.read_text().strip()
        except (OSError, ValueError, AttributeError):
            continue
        if isinstance(c, str) and SHA_RE.match(c):
            return dict(commit=c, dirty=None, source=f.name)
    return rec


def check_result(rec, repo=REPO):
    """errors for a bind / LEC / token result record: it must name a commit (and not a dirty tree)."""
    errs = []
    p = rec.get("provenance") if isinstance(rec.get("provenance"), dict) else {}
    c = p.get("commit") or next((rec.get(k) for k in COMMIT_KEYS if isinstance(rec.get(k), str)), None)
    if not (isinstance(c, str) and SHA_RE.match(c)):
        errs.append("result names no commit (provenance.commit / source_commit)")
    else:
        if p.get("dirty"):
            errs.append(f"result made from a dirty tree at {c}")
        if (Path(repo) / ".git").exists():
            r = subprocess.run(["git", "-C", str(repo), "cat-file", "-e", c + "^{commit}"], capture_output=True)
            if r.returncode != 0:
                errs.append(f"result commit {c} is not in this repository (push it)")
    for k in ("inputs", "manifest", "asbuilt_manifest"):
        v = p.get(k)
        for s in ([v] if isinstance(v, str) else (v or [])):
            if isinstance(s, str) and (Path(s).is_absolute() or ".." in s.split("/")):
                errs.append(f"provenance.{k}: input {s!r} is not repository-relative")
    return errs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    ap.add_argument("--kind", choices=("auto", "bind", "lec", "token", "any"), default="auto")
    ap.add_argument("--result", action="store_true", help="the files are result records: require a named commit")
    a = ap.parse_args(argv)
    bad = 0
    for f in a.files:
        if a.result:
            errs = check_result(json.loads(Path(f).read_text()))
            ok = "PASS names its commit"
        else:
            errs = check_file(f, kind=a.kind)
            ok = "PASS repo-relative"
        for e in errs:
            print(f"{f}: {e}")
        print(f"{f}: {'FAIL ' + str(len(errs)) + ' problem(s)' if errs else ok}")
        bad += bool(errs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
