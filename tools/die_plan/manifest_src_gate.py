#!/usr/bin/env python3
"""Source-identity gate for as-built bind manifests (COORD structural fix 11-12; S81 bound OLD RTL twice, 10-25 and 11-12).

Why: the manifest `files` / `prefer` lists select source files by absolute paths into old frozen trees or by
repo-relative paths that resolve against the manifest `base` (bind.plan_base), not against the bind source tree.  Both
silently bound old RTL while the fixed kits sat in the tree built from main.  manifest_paths.py checks only the SHAPE of
the paths; this gate checks the CONTENT: every selected file must be byte-identical (sha256) to the same repo-relative
path at a NAMED main sha.

Opt-in (a manifest with neither key and no --src-sha is not touched):
  asbuilt key `src_sha` (or bind.py --src-sha SHA): the main commit the bind source tree was built from.
  asbuilt key `declared_overrides`: [{"path": P, "reason": "..."}], P exactly as written in the manifest (or the
      resolved file path).  Special paths: "base" (base is a different tree than the bind source tree) and "tree" (the
      bind source tree HEAD is not src_sha).  A declared override passes, is recorded in provenance_bind.json and
      bind_report.json (source_gate.overrides) with the actual and the main sha256.
Checks (all fail closed, one line each):
  1. src_sha resolves to a commit in the bind source tree repository; the tree HEAD is that commit.
  2. the manifest base resolves to the bind source tree root.
  3. each literal file in files / prefer / netlist: sha256 equals the blob at src_sha.  A path outside the tree
     (absolute) can never match by identity: it fails (naming same-basename candidates in src_sha and their sha256)
     unless declared.
  4. (read-back) each file the bind actually read (out/asbuilt_sources.json full / lib / top / tops) that lies under the
     base or the tree is compared the same way; files in the output dir are generated and skipped; other outside files
     must be declared.
Library: check(ab, base, repo, src_sha) -> dict(src_sha, errors, overrides, checked); check_read(srcs, ...).
CLI (read-only dry run): manifest_src_gate.py MANIFEST.json --src-sha SHA [--repo R] [--base B] [--sources F.json]
"""
import argparse
import glob
import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LIST_KEYS = ("files", "prefer", "netlist")


def _git(repo, *args, raw=False):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=300)
    if r.returncode != 0:
        return None
    return r.stdout if raw else r.stdout.decode().strip()


def resolve_sha(repo, sha):
    return _git(repo, "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}") if sha else None


def _file_sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class Ref:
    """blob lookups at one commit of one repository (cached)."""

    def __init__(self, repo, full):
        self.repo, self.full, self._idx, self._sha = Path(repo), full, None, {}

    def sha(self, rel):
        if rel not in self._sha:
            b = _git(self.repo, "cat-file", "blob", f"{self.full}:{rel}", raw=True)
            self._sha[rel] = None if b is None else hashlib.sha256(b).hexdigest()
        return self._sha[rel]

    def by_basename(self, name):
        if self._idx is None:
            self._idx = {}
            out = _git(self.repo, "ls-tree", "-r", "--name-only", self.full) or ""
            for rel in out.splitlines():
                self._idx.setdefault(Path(rel).name, []).append(rel)
        return self._idx.get(name, [])


def declared(ab):
    """({path: reason}, errors) from ab['declared_overrides']; an entry without a reason is an error."""
    d, errs = {}, []
    for i, e in enumerate(ab.get("declared_overrides") or []):
        if not (isinstance(e, dict) and isinstance(e.get("path"), str) and isinstance(e.get("reason"), str)
                and e["reason"].strip()):
            errs.append(f"declared_overrides[{i}]: needs a string `path` and a non-empty `reason`")
        else:
            d[e["path"]] = e["reason"]
    return d, errs


def _inside(p, root):
    try:
        return Path(p).resolve().relative_to(Path(root).resolve())
    except ValueError:
        return None


class _Gate:
    def __init__(self, ab, base, repo, src_sha):
        self.ab, self.base, self.repo = ab, Path(base), Path(repo)
        self.decl, self.errors = declared(ab)
        self.overrides, self.checked, self.used = [], 0, set()
        self.full = resolve_sha(self.repo, src_sha)
        self.ref = Ref(self.repo, self.full) if self.full else None
        if not self.full:
            self.errors.append(f"src_sha {src_sha!r} is not a commit in the bind source tree {self.repo}")

    def override(self, key, what, reason_key=None, **kw):
        k = reason_key or key
        if k in self.decl:
            self.used.add(k)
            self.overrides.append(dict(path=key, reason=self.decl[k], what=what, **kw))
            return True
        return False

    def tree(self):
        if not self.full:
            return
        head = _git(self.repo, "rev-parse", "HEAD")
        if head != self.full and not self.override("tree", f"tree HEAD {head}", actual=head, main=self.full):
            self.errors.append(f"tree: bind source tree {self.repo} is at {str(head)[:12]}, not src_sha "
                               f"{self.full[:12]} (declare path `tree` to override)")
        if _inside(self.base, self.repo) is None or Path(self.base).resolve() != self.repo.resolve():
            if not self.override("base", f"base {self.base}", base=str(self.base)):
                self.errors.append(f"base: manifest base {self.base} is not the bind source tree {self.repo} "
                                   f"(declare path `base` to override)")

    def one(self, label, p):
        """p: path as written (label) -> resolved file."""
        if not self.full:
            return
        f = Path(p) if Path(p).is_absolute() else self.base / p
        if not f.is_file():
            return
        self.checked += 1
        rel = _inside(f, self.base) or _inside(f, self.repo)
        have = _file_sha(f)
        if rel is None:
            cands = [(c, self.ref.sha(c)) for c in self.ref.by_basename(f.name)]
            near = "; ".join(f"{c} main {s[:12]}" for c, s in cands) or "no same-basename file in src_sha"
            if not (self.override(p, f"outside tree {f}", have=have[:12]) or self.override(str(f), f"outside tree {f}")):
                self.errors.append(f"{label}: {p} is outside the bind source tree (sha {have[:12]}; {near}); "
                                   f"declare it in declared_overrides or use the repo-relative path")
            return
        rel = str(rel)
        want = self.ref.sha(rel)
        if want == have:
            return
        if self.override(p, f"differs from main {rel}", actual=have[:12], main=(want or "absent")[:12], rel=rel) or \
                self.override(str(f), f"differs from main {rel}"):
            return
        self.errors.append(f"{label}: {rel} sha256 {have[:12]} differs from {self.full[:12]} "
                           f"{(want or 'ABSENT')[:12]} (declare it in declared_overrides with a reason or rebuild the "
                           f"bind tree from src_sha)")


def _summary(g):
    return dict(src_sha=g.full, errors=g.errors, checked=g.checked,
                overrides=g.overrides, unused_declared=sorted(set(g.decl) - g.used))


def check(ab, base, repo, src_sha):
    """gate the manifest's selected files; returns dict(src_sha, errors, overrides, checked, unused_declared)."""
    g = _Gate(ab, base, repo, src_sha)
    g.tree()
    for k in LIST_KEYS:
        v = ab.get(k) or []
        for p in ([v] if isinstance(v, str) else v):
            if isinstance(p, str) and not glob.has_magic(p):
                g.one(k, p)
    return _summary(g)


def check_read(ab, base, repo, src_sha, srcs, out):
    """gate the files the bind actually read (asbuilt_sources.json); output-dir files are generated and skipped."""
    g = _Gate(ab, base, repo, src_sha)
    seen = set()
    vals = []
    for k in ("full", "lib", "top", "tops"):
        v = srcs.get(k) or []
        vals += [v] if isinstance(v, str) else list(v)
    for p in vals:
        if not isinstance(p, str) or p in seen:
            continue
        seen.add(p)
        if out is not None and _inside(p, out) is not None:
            continue
        g.one("read", p)
    return _summary(g)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--src-sha", help="default: the manifest's src_sha")
    ap.add_argument("--repo", default=str(REPO), help="bind source tree (default: this checkout)")
    ap.add_argument("--base", help="override the base (default: manifest base like bind.plan_base, else repo)")
    ap.add_argument("--sources", help="out/asbuilt_sources.json of a bind: also gate the files it read")
    a = ap.parse_args(argv)
    mp = Path(a.manifest).resolve()
    raw = json.loads(mp.read_text())
    ab = raw["asbuilt"] if isinstance(raw.get("asbuilt"), dict) else raw
    sha = a.src_sha or ab.get("src_sha")
    if not sha:
        print(f"{a.manifest}: no src_sha (manifest key or --src-sha): gate not applicable")
        return 2
    if a.base:
        base = str(Path(a.base).resolve())
    elif ab.get("base"):                     # as bind.plan_base: relative to the manifest directory
        b = ab["base"]
        base = b if Path(b).is_absolute() else str((mp.parent / b).resolve())
    else:
        base = a.repo
    res = check(ab, base, a.repo, sha)
    if a.sources:
        r2 = check_read(ab, base, a.repo, sha, json.loads(Path(a.sources).read_text()), Path(a.sources).parent)
        res["errors"] += [e for e in r2["errors"] if e not in res["errors"]]
        res["overrides"] += r2["overrides"]
        res["checked"] += r2["checked"]
    for e in res["errors"]:
        print(f"{a.manifest}: {e}")
    for o in res["overrides"]:
        print(f"{a.manifest}: OVERRIDE {o['path']}: {o['reason']}")
    print(f"{a.manifest}: {'FAIL ' + str(len(res['errors'])) + ' problem(s)' if res['errors'] else 'PASS'} "
          f"({res['checked']} files checked at {str(res['src_sha'])[:12]}, {len(res['overrides'])} declared override(s))")
    return 1 if res["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
