#!/usr/bin/env python3
"""PRE-DIFF (COMPOSE-FAST 11-25, OWNER via COORD): plan_gate_pre judged against a BASE plan.

A row is drafted on a base that already carries FAIL findings (KV A5t7: 26 RSTREACH).  Every lane then ran PRE twice (base and
row, ~7 min each) and diffed the FAIL lines by hand (sort | comm -13).  `plan_gate_pre.py check ... --base BASE` does it in the
checker:

  * the base findings come from the same checker run on BASE (with --baseline-plan BASE, in --base-tree, default --tree), started
    in a child process BESIDE the row check, or read from the cache (key: sha256 of BASE + as-built + the tools/die_plan sources of
    the base tree + the base tree path + the skipped classes), so a second row gate on the same base pays nothing for it;
  * a row FAIL line that equals a base FAIL line (plan / base / tree paths replaced by tokens) is INHERITED: listed
    (`LIST PRE-INHERITED ...`), never a failure;
  * every other row FAIL line fails: NEW (its class + subject is not in the base) or CHANGED (same class + subject, other text,
    e.g. a larger count);
  * base FAIL lines the row no longer has are counted (GONE);
  * a base check that cannot run is `FAIL PRE-DIFF-UNCHECKED` (fail closed, never a silent pass).

Cache: $OT_PRE_BASE_CACHE, else <scratch>/claude/.cache/pre-base, else ~/.cache/ot-pre-base.  Stdlib only."""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH_CACHE = "/srv/opentallas-scratch2/claude/.cache/pre-base"
VERSION = 1


def cache_dir():
    d = os.environ.get("OT_PRE_BASE_CACHE")
    if d:
        return Path(d)
    if os.path.isdir(os.path.dirname(SCRATCH_CACHE)) or os.path.isdir(os.path.dirname(os.path.dirname(SCRATCH_CACHE))):
        return Path(SCRATCH_CACHE)
    return Path.home() / ".cache" / "ot-pre-base"


def _sha_file(p):
    h = hashlib.sha256()
    try:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
    except OSError:
        return "missing"
    return h.hexdigest()


def tools_digest(tree):
    """sha256 over (name, sha256) of every tools/die_plan/*.py of the tree (the checker's own code and what it imports)"""
    h = hashlib.sha256()
    d = Path(tree) / "tools" / "die_plan"
    for p in sorted(d.glob("*.py")) if d.is_dir() else []:
        h.update(p.name.encode() + b"\0" + _sha_file(p).encode() + b"\n")
    return h.hexdigest()


def _resolve(path, root):
    if not path:
        return None
    p = Path(path)
    return p if p.is_absolute() else Path(root) / p


def cache_key(base, base_tree, asbuilt=None, sidecar=None, skip=(), types=None):
    parts = [f"v{VERSION}", _sha_file(_resolve(base, base_tree)), _sha_file(_resolve(asbuilt, base_tree)) if asbuilt else "-",
             _sha_file(_resolve(sidecar, base_tree)) if sidecar else "-", tools_digest(base_tree),
             os.path.realpath(base_tree), ",".join(sorted({s.upper() for s in skip})),
             os.environ.get("OT_PLAN_ABSPATH", ""), os.environ.get("OT_TAPNAME_ALL", ""), "types=" + str(types or "")]
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:32]


def base_cmd(base, base_tree, asbuilt=None, sidecar=None, skip=(), out_json=None, checker=None, types=None):
    cmd = [sys.executable, "-I", "-B", str(checker or (HERE / "plan_gate_pre.py")), "check", "--tree", str(base_tree),
           "--plan", str(base), "--baseline-plan", str(base), "--quiet"]
    if asbuilt:
        cmd += ["--asbuilt", str(asbuilt)]
    if sidecar:
        cmd += ["--sidecar", str(sidecar)]
    for s in skip:
        cmd += ["--skip", s]
    if types:
        cmd += ["--types", str(types)]
    if out_json:
        cmd += ["--json", str(out_json)]
    return cmd


class BaseRun:
    """the base findings: a cache hit, or a child plan_gate_pre run started now (call .result() after the row check)"""

    def __init__(self, base, base_tree, asbuilt=None, sidecar=None, skip=(), use_cache=True, checker=None, types=None):
        self.base, self.base_tree = str(base), str(base_tree)
        self.key = cache_key(base, base_tree, asbuilt, sidecar, skip, types)
        self.cfile = cache_dir() / f"{self.key}.json"
        self.proc, self.how, self.t0 = None, "", time.time()
        self.fails = None
        if use_cache:
            try:
                rec = json.loads(self.cfile.read_text())
                if rec.get("key") == self.key and isinstance(rec.get("fails"), list):
                    self.fails, self.how = rec["fails"], f"cache {self.cfile}"
                    return
            except (OSError, ValueError):
                pass
        self.tmp = self.cfile.with_name(f"{self.key}.{os.getpid()}.run.json")
        try:
            self.cfile.parent.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.tmp = Path(os.environ.get("TMPDIR", "/tmp")) / f"pre-base-{self.key}.{os.getpid()}.json"
        env = dict(os.environ, OT_PRE_BASE_CHILD="1")
        self.log = self.tmp.with_suffix(".log")
        try:
            with open(self.log, "w") as lf:
                self.proc = subprocess.Popen(base_cmd(base, base_tree, asbuilt, sidecar, skip, self.tmp, checker, types), cwd=self.base_tree,
                                             stdout=lf, stderr=subprocess.STDOUT, env=env)
        except OSError as e:
            self.how = f"base check not started: {e}"
            return
        self.how = f"run (pid {self.proc.pid}, log {self.log})"

    def result(self):
        """-> (fails list or None when the base check could not run, how)"""
        if self.fails is not None or self.proc is None:
            return self.fails, self.how                  # cache hit, or None (not started)
        rc = self.proc.wait()
        try:
            rec = json.loads(self.tmp.read_text())
        except (OSError, ValueError):
            rec = None
        if rc not in (0, 1) or not isinstance(rec, dict):
            tail = ""
            try:
                tail = self.log.read_text(errors="replace")[-300:].replace("\n", " | ")
            except OSError:
                pass
            return None, f"base check rc {rc}: {tail}"
        self.fails = list(rec.get("findings") or [])
        try:
            self.cfile.write_text(json.dumps(dict(key=self.key, base=self.base, base_tree=self.base_tree, fails=self.fails,
                                                  seconds=round(time.time() - self.t0, 1), made=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                                             indent=1) + "\n")
            self.tmp.unlink()
            self.log.unlink()
        except OSError:
            pass
        self.how += f", {time.time() - self.t0:.0f} s"
        return self.fails, self.how


def subs_for(plan=None, base=None, tree=None, base_tree=None):
    """[(text, token)] longest first: absolute and given forms of the plan, base and tree paths"""
    out = []
    for p, tok in ((plan, "<PLAN>"), (base, "<BASE>"), (tree, "<TREE>"), (base_tree, "<TREE>")):
        if not p:
            continue
        for form in {str(p), os.path.abspath(str(p)), os.path.realpath(str(p))}:
            if form and form not in ("/", "."):
                out.append((form.rstrip("/"), tok))
    return sorted(set(out), key=lambda x: -len(x[0]))


def norm(line, subs):
    s = line.rstrip()
    for a, b in subs:
        s = s.replace(a, b)
    return s


def subject(line):
    """class + subject of a finding line: `FAIL CLASS subject ...` -> (CLASS, subject-without-colon)"""
    t = line.split()
    return (t[1] if len(t) > 1 else "", t[2].rstrip(":") if len(t) > 2 else "")


def diff(row_fails, base_fails, row_subs=(), base_subs=()):
    """-> dict(new, changed, inherited, gone): lists of row lines (new / changed / inherited) and base lines (gone: no row line of
    the same text or the same class + subject)"""
    bn = {}
    for x in base_fails:
        bn.setdefault(norm(x, base_subs), x)
    bkeys = {subject(k) for k in bn}
    seen, ckeys, out = set(), set(), dict(new=[], changed=[], inherited=[], gone=[])
    for x in row_fails:
        k = norm(x, row_subs)
        if k in bn:
            out["inherited"].append(x)
            seen.add(k)
        elif subject(k) in bkeys:
            out["changed"].append(x)
            ckeys.add(subject(k))
        else:
            out["new"].append(x)
    out["gone"] = [v for k, v in bn.items() if k not in seen and subject(k) not in ckeys]
    return out


def lines(d, base, how):
    """the LIST lines PRE prints for a diff"""
    out = [f"LIST PRE-DIFF base={base} new={len(d['new'])} changed={len(d['changed'])} inherited={len(d['inherited'])} "
           f"gone={len(d['gone'])} (base findings: {how})"]
    out += ["LIST PRE-INHERITED " + x[5:] if x.startswith("FAIL ") else "LIST PRE-INHERITED " + x for x in d["inherited"]]
    out += ["LIST PRE-GONE " + (x[5:] if x.startswith("FAIL ") else x) for x in d["gone"]]
    return out
