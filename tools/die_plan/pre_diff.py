#!/usr/bin/env python3
"""PRE-DIFF (COMPOSE-FAST 11-25, OWNER via COORD): plan_gate_pre judged against a BASE plan.

A row is drafted on a base that already carries FAIL findings (KV A5t7: 26 RSTREACH).  Every lane then ran PRE twice (base and
row, ~7 min each) and diffed the FAIL lines by hand (sort | comm -13).  `plan_gate_pre.py check ... --base BASE` does it in the
checker:

  * findings come from the same checker run on BASE, in --base-tree, with the same scope and effective options. A sealed
    source/runtime launch can reuse a completed baseline across private row attempts; the candidate always runs its checks.
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
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH_CACHE = "/srv/opentallas-scratch2/claude/.cache/pre-base"
VERSION = 2
# These change where the result or logs are written, or how a COW wrapper is mounted. All other OT_* options are kept.
NON_INPUT_ENV = frozenset({
    "OT_PRE_BASE_CACHE", "OT_PRE_BASE_PENDING", "OT_PRE_BASE_CHILD",
    "OT_PRE_RECORD_DIR", "OT_PRE_RECORD", "OT_PRE_SLOT_DIR", "OT_PRE_TIME_TRACE_S",
    "OT_ROW_GATE_COW_TREE", "OT_ROW_GATE_COW_LEDGER",
})
# None of these files participates in the standalone baseline check.
WRAPPERS = frozenset({"pre_diff.py", "row_gate.py", "row_gate_cow.py"})



def cache_dir():
    d = os.environ.get("OT_PRE_BASE_CACHE")
    if d:
        return Path(d)
    if os.path.isdir(os.path.dirname(SCRATCH_CACHE)) or os.path.isdir(os.path.dirname(os.path.dirname(SCRATCH_CACHE))):
        return Path(SCRATCH_CACHE)
    return Path.home() / ".cache" / "ot-pre-base"


def _resolve(path, root):
    if not path:
        return None
    p = Path(path)
    return p if p.is_absolute() else Path(root) / p


def file_stamp(path):
    if path is None:
        return None
    p = Path(path)
    try:
        stat = p.stat()
        return [str(p.resolve()), stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns]
    except OSError:
        return None


def sealed_launch(tree):
    """The launch stamp is already emitted by rt_launch_tree.sh for this launch."""
    try:
        stamp = json.loads((tree / ".rt_launch_ok").read_text())
        src, rt = (Path(stamp[n]).resolve(strict=True) for n in ("src", "rt"))
        marker = src / ".src-manifest.sha256"
        if not marker.is_file() or marker.stat().st_mode & 0o222 or (src / ".fork.json").exists():
            return None
        if not (rt / "tools").is_dir() or (rt / "tools").stat().st_mode & 0o222:
            return None
        return {
            "source": file_stamp(marker), "runtime": str(rt),
            "pins": stamp.get("pins", {}), "pin_runtime": stamp.get("pin_rt", ""),
        }
    except (AttributeError, KeyError, OSError, TypeError, ValueError):
        return None


def checker_files(tree):
    """Ordinary metadata for the checker's local modules and directly used preflight helpers."""
    paths = [(tree / "tools" / "die_plan", "*.py"), (tree / "tools" / "die_plan", "*.json"),
             (tree / "tools" / "precheck", "*.py")]
    artifacts = []
    for root, pattern in paths:
        for path in sorted(root.glob(pattern)):
            if path.name in WRAPPERS or path.name.startswith("test_"):
                continue
            value = file_stamp(path)
            if value is not None:
                # Runtime launch hard links have an attempt-specific path, but retain their inode.
                artifacts.append([str(path.relative_to(tree)), *value[1:]])
    return artifacts


def launch_dependencies(tree, launch, checker):
    """Use original input metadata across hard-link and fallback-copy launch trees."""
    if not launch:
        return None
    rt = Path(launch["runtime"])
    src = Path(launch["source"][0]).parent
    deps = []
    for name, *actual in checker_files(tree):
        rel = Path(name)
        if rel.parent == Path("tools/die_plan") and rel.name in launch["pins"]:
            origin = Path(launch["pin_runtime"]) / rel
        elif (rt / rel).is_file():
            origin = rt / rel
        else:
            origin = src / rel
        original = file_stamp(origin)
        if not original or actual[-2:] != original[-2:]:
            return None
        deps.append([name, *original[1:]])
    expected = next((d[1:] for d in deps if d[0] == "tools/die_plan/plan_gate_pre.py"), None)
    actual = file_stamp(checker)
    if expected is None or actual is None or actual[-2:] != expected[-2:]:
        return None
    return expected, deps


def base_context(base, base_tree, asbuilt=None, sidecar=None, skip=(), types=None, checker=None, env=None):
    env = os.environ if env is None else env
    tree = Path(base_tree).absolute()
    sealed = sealed_launch(tree)
    if checker is None:
        checker = HERE / "plan_gate_pre.py"
    dependencies = launch_dependencies(tree, sealed, checker)
    if dependencies is None:
        sealed = None
        dependencies = (file_stamp(checker) or [None])[1:], checker_files(tree)
    checker_stamp, related_files = dependencies
    def argument(value):
        if value is None:
            return None
        path = Path(value)
        return str(path.relative_to(tree)) if path.is_absolute() and path.is_relative_to(tree) else str(value)

    types_arg = str(types or "")
    type_files = [file_stamp(_resolve(item[1:], tree)) for spec in types_arg.split(",")
                  if (item := spec.strip()).startswith("@")]
    return {
        "version": VERSION,
        "launch": sealed,
        "tree": None if sealed else str(tree.resolve()),
        "args": [argument(value) for value in (base, asbuilt, sidecar)],
        "plan": file_stamp(_resolve(base, tree)),
        "asbuilt": file_stamp(_resolve(asbuilt, tree)),
        "sidecar": file_stamp(_resolve(sidecar, tree)),
        "checker": checker_stamp,
        "dependencies": related_files,
        "skip": sorted({s.upper() for s in skip}),
        "types": [types_arg, type_files],
        "runtime": file_stamp(sys.executable),
        "environment": context_key({k: v for k, v in env.items()
                                    if (k.startswith("OT_") and k not in NON_INPUT_ENV)
                                    or k in ("PATH", "LANG", "LC_ALL", "LC_CTYPE")}),
        "test_mode": "PYTEST_CURRENT_TEST" in env,
    }


def context_key(context):
    # Short filename from the small dependency record. No design or tool contents are read.
    return hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:32]


def cache_key(base, base_tree, asbuilt=None, sidecar=None, skip=(), types=None):
    return context_key(base_context(base, base_tree, asbuilt, sidecar, skip, types))


def completed_findings(result, findings):
    return (
        isinstance(findings, list)
        and (result == "FAIL" if findings else result == "PASS")
        and all(isinstance(line, str) and len(line.split()) > 2 and line.startswith("FAIL ")
                and not line.split()[1].endswith("-UNCHECKED") for line in findings)
    )


def write_record(dest, record, *, publish=False):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.NamedTemporaryFile(mode="w", dir=dest.parent, prefix=".", delete=False)
    try:
        with tmp:
            json.dump(record, tmp, indent=1)
            tmp.write("\n")
        if publish:
            Path(tmp.name).chmod(0o444)
            try:
                os.link(tmp.name, dest)
            except FileExistsError:
                pass
        else:
            os.replace(tmp.name, dest)
    finally:
        Path(tmp.name).unlink(missing_ok=True)


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
        self.context = base_context(base, base_tree, asbuilt, sidecar, skip, types, checker)
        self.key = context_key(self.context)
        self.cfile = cache_dir() / f"{self.key}.json"
        self.proc, self.how, self.t0 = None, "", time.time()
        self.fails = None
        if use_cache:
            try:
                rec = json.loads(self.cfile.read_text())
                if (rec.get("context") == self.context and completed_findings(rec.get("result"), rec.get("fails"))
                        and isinstance(rec.get("base_tree"), str) and rec["base_tree"]):
                    old_tree = rec["base_tree"]
                    self.fails = [line.replace(old_tree, self.base_tree) for line in rec["fails"]]
                    self.how = f"cache {self.cfile}"
                    return
            except (OSError, ValueError, AttributeError):
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
        if (rc not in (0, 1) or not isinstance(rec, dict)
                or not completed_findings(rec.get("result"), rec.get("findings"))
                or (rc == 1) != bool(rec["findings"])):
            tail = ""
            try:
                tail = self.log.read_text(errors="replace")[-300:].replace("\n", " | ")
            except OSError:
                pass
            return None, f"base check rc {rc}: {tail}"
        self.fails = rec["findings"]
        record = dict(key=self.key, context=self.context, base=self.base, base_tree=self.base_tree,
                      result=rec["result"], fails=self.fails, seconds=round(time.time() - self.t0, 1))
        try:
            write_record(self.cfile, record, publish=bool(self.context["launch"]))
            pending = os.environ.get("OT_PRE_BASE_PENDING")
            if pending and self.context["launch"] and self.context["plan"]:
                write_record(Path(pending) / self.cfile.name, record)
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
