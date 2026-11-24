#!/usr/bin/env python3
"""tree_precheck: three seconds-scale checks of a gate tree, run FIRST in every gate (PRE-SCHEMA-KEYS 11-24, S81-ALLFIX-INT 09:34,
COORD flow review 10:5x).  REPORT ONLY (r703): every finding is a WARN line, the exit code is 0 whatever is found.

Three S81 forks (c9seal_tree, w69, the E7 serdes t2 fork 10:51) died at elab or after it, hours in, on a gate tree whose schema.py
predated the plan's keys (SELLK read_lockup / lane min_cycles), or whose *_sources/ folders were never copied.  The full
plan_gate_pre runs beside the bind and is read when the bind ends; these three run before the elab starts.

    python3 -I tools/die_plan/tree_precheck.py --tree TREE --plan PLAN.json [--asbuilt AB.json] [--out BINDOUT] [--rt RTROOT]
        [--checks SCHEMA-KEYS,TREE-SOURCES,TREE-FRESH] [--json OUT.json]

  SCHEMA-KEYS   every plan key is known to TREE/tools/die_plan/schema.py (the gate tree) AND to the launch rt's schema.py (--rt, default
                the repo this script runs from).  One line per unknown key path (partition type names folded to *), with the count,
                the first concrete path and which side knows it: "the launch rt knows it" = the tree is older than the plan.
  TREE-SOURCES  every path the as-built names (files / prefer / netlist / hard_params / rtl_roots / map_file / clock_landing_table,
                resolved as bind.py resolves them), every entry of a .f file list among them and of OUT/bind.f, and every *_sources/
                folder any of these or the plan names, exists in the tree.
  TREE-FRESH    TREE/.fork.json (ot-tree-fork) against its source NOW: the source's seal (.src-manifest.sha256) differs from the one
                recorded at fork time, the source was sealed after the fork, the source is gone, or (unsealed source) files under
                its tools/die_plan, rtl or the plan's folder are newer than the fork.  A remote source is asked over ssh (10 s connect).

Library: findings(tree, plan, asbuilt=None, out=None, rt=None, checks=None) -> [lines].  Stdlib only; never raises.
"""
import argparse
import hashlib
import json
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

CLASSES = ("SCHEMA-KEYS", "TREE-SOURCES", "TREE-FRESH")
PROBE_S = float(os.environ.get("OT_TREE_PRECHECK_PROBE_S", "90"))
SSH_S = float(os.environ.get("OT_TREE_PRECHECK_SSH_S", "60"))
MAX_LINES = 12
LIST_KEYS = ("files", "prefer", "netlist", "rtl_roots", "hard_params")
TERMINATED = set(filter(None, os.environ.get("OT_TERMINATED_HOSTS", "epyc3,epyc4,epyc5,epyc6").split(",")))
FRESH_DIRS = ("tools/die_plan", "rtl")
SOURCES_RE = re.compile(r"(?:^|[\s/\"'=])((?:[\w.+-]+/)*[\w.+-]*[A-Za-z0-9]_sources)(?=/)")   # a folder: <name>_sources/...

_PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import schema
obj = json.load(open(sys.argv[2]))
print(json.dumps({"errors": schema.validate_structure(obj)}))
"""


def _sha12(p):
    try:
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:12]
    except OSError:
        return "-"


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------- SCHEMA-KEYS
def schema_unknown(tools_dir, plan, timeout=PROBE_S):
    """-> ({key path: [concrete paths]}, error text or None) of the 'unknown key' errors schema.py in tools_dir gives the plan"""
    sd = Path(tools_dir)
    if not (sd / "schema.py").is_file():
        return None, f"{sd}/schema.py does not exist"
    try:
        r = subprocess.run([sys.executable, "-I", "-B", "-c", _PROBE, str(sd), str(plan)], capture_output=True, text=True,
                           timeout=timeout, cwd=str(sd))
    except subprocess.TimeoutExpired:
        return None, f"schema probe timed out ({timeout:.0f} s; OT_TREE_PRECHECK_PROBE_S overrides)"
    if r.returncode != 0:
        return None, "schema.py does not import: " + ((r.stderr.strip().splitlines() or ["?"])[-1])[:200]
    try:
        errs = json.loads(r.stdout.strip().splitlines()[-1])["errors"]
    except (ValueError, IndexError, KeyError):
        return None, "schema probe gave no result"
    out = {}
    for e in errs:
        m = re.match(r"(.*): unknown key '([^']+)'$", e)
        if m:
            out.setdefault(m.group(1) + "." + m.group(2), []).append(e)
    return out, None


def fold(path):
    """$.partition_types.<T>.x -> $.partition_types.*.x; list indices -> []"""
    p = re.sub(r"^\$\.partition_types\.[^.\[]+", "$.partition_types.*", path)
    return re.sub(r"\[\d+\]", "[]", p)


def check_schema_keys(tree, plan, rt):
    tsd, rsd = Path(tree) / "tools" / "die_plan", Path(rt) / "tools" / "die_plan"
    same = tsd.resolve() == rsd.resolve()
    import concurrent.futures as CF
    with CF.ThreadPoolExecutor(2) as ex:                # the two probes in parallel (a die plan validates in ~30 s each)
        ft = ex.submit(schema_unknown, tsd, plan)
        fr = None if same else ex.submit(schema_unknown, rsd, plan)
        tu, terr = ft.result()
        ru, rerr = (tu, terr) if same else fr.result()
    tsha, rsha = _sha12(tsd / "schema.py"), _sha12(rsd / "schema.py")
    out = []
    if terr:
        out.append(f"WARN SCHEMA-KEYS not checked against the gate tree: {terr}")
    if rerr and not same:
        out.append(f"WARN SCHEMA-KEYS not checked against the launch rt {rt}: {rerr}")
    tf, rf = {}, {}
    for src, dst in ((tu or {}, tf), (ru or {}, rf)):
        for k, es in src.items():
            dst.setdefault(fold(k), []).append(k)
    rows = []
    for fk in sorted(set(tf) | set(rf)):
        if fk in tf:
            who = ("unknown to the launch rt schema too" if fk in rf else "launch rt not checked" if rerr
                   else f"the launch rt {rt} schema.py {rsha} knows it (the gate tree is older than the plan)")
            rows.append(f"WARN SCHEMA-KEYS {fk} x{len(tf[fk])} unknown to gate tree {tree} schema.py {tsha}: {who} (first {tf[fk][0]})")
        else:
            rows.append(f"WARN SCHEMA-KEYS {fk} x{len(rf[fk])} unknown to the launch rt {rt} schema.py {rsha}: the gate tree "
                        f"schema.py {tsha} knows it (first {rf[fk][0]})")
    out += rows[:MAX_LINES]
    if len(rows) > MAX_LINES:
        out.append(f"WARN SCHEMA-KEYS ... and {len(rows) - MAX_LINES} more key path(s)")
    nt = sum(len(v) for v in tf.values())
    out.append(f"LIST SCHEMA-KEYS gate tree schema.py {tsha}: {'-' if terr else nt} unknown key(s); launch rt "
               f"{'= gate tree' if same else rt} schema.py {rsha}: {'-' if rerr else sum(len(v) for v in rf.values())}")
    return out


# ---------------------------------------------------------------- TREE-SOURCES
def asbuilt_paths(ab, mdir, tree):
    """(base, [(key, Path, kind)]) resolved as bind.py / plan_gate_pre.manifest_paths do"""
    tree, mdir = Path(tree), Path(mdir)
    b = ab.get("base")
    base = tree if b is None else (Path(b) if Path(b).is_absolute() else mdir / b)
    res = []

    def add(key, p, rel, kind="file"):
        if isinstance(p, str) and p:
            res.append((key, Path(p) if Path(p).is_absolute() else Path(rel) / p, kind))

    for k in LIST_KEYS:
        v = ab.get(k) or []
        for p in ([v] if isinstance(v, str) else v if isinstance(v, list) else []):
            add(k, p, base, "dir" if k == "rtl_roots" else "file")
    add("map_file", ab.get("map_file"), mdir)
    add("clock_landing_table", ab.get("clock_landing_table"), base)
    return base, res


def filelist_entries(f, base):
    """entries of a .f file list (comments, +incdir / +define / -options dropped; -f/-F nested lists not followed)"""
    out = []
    try:
        txt = Path(f).read_text(errors="replace")
    except OSError:
        return out
    for ln in txt.splitlines():
        ln = ln.split("//")[0].strip()
        if not ln or ln.startswith(("+", "#")):
            continue
        if ln.startswith("-"):
            continue
        for tok in ln.split():
            p = Path(tok)
            out.append(p if p.is_absolute() else (Path(base) / p if (Path(base) / p).exists() or not (Path(f).parent / p).exists()
                                                  else Path(f).parent / p))
    return out


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def sources_dirs(strings):
    out = set()
    for s in strings:
        if "_sources" not in s or len(s) > 400:
            continue
        for m in SOURCES_RE.finditer(s):
            out.add(m.group(1).lstrip("./") if not m.group(1).startswith("/") else m.group(1))
    return out


def check_tree_sources(tree, plan, raw, asbuilt=None, out=None):
    tree = Path(tree)
    if asbuilt:
        ab, mdir = _load(asbuilt), Path(asbuilt).resolve().parent
    else:
        ab, mdir = (raw or {}).get("asbuilt"), Path(plan).resolve().parent
    res = []
    miss = {}
    n = 0
    base = tree
    if isinstance(ab, dict):
        base, paths = asbuilt_paths(ab, mdir, tree)
        if not base.is_dir():
            res.append(f"WARN TREE-SOURCES base {base} is not a directory (as-built base {ab.get('base')!r})")
        for key, p, kind in paths:
            n += 1
            ok = p.is_dir() if kind == "dir" else p.exists()
            if not ok:
                miss.setdefault(key, []).append(str(p))
            elif p.suffix == ".f" and p.is_file():
                for q in filelist_entries(p, base):
                    n += 1
                    if not q.exists():
                        miss.setdefault(f"{key}:{p.name}", []).append(str(q))
    else:
        res.append(f"LIST TREE-SOURCES {plan} has no as-built section and no --asbuilt: only *_sources/ folders checked")
    bf = Path(out) / "bind.f" if out else None
    if bf and bf.is_file():
        for q in filelist_entries(bf, base):
            n += 1
            if not q.exists():
                miss.setdefault("OUT/bind.f", []).append(str(q))
    strs = list(_strings(ab)) if isinstance(ab, dict) else []
    strs += [s for s in _strings(raw or {}) if "_sources" in s]
    sd_miss = []
    sds = sources_dirs(strs)
    for d in sorted(sds):
        cands = [Path(d)] if d.startswith("/") else [base / d, tree / d]
        if not any(c.is_dir() for c in cands):
            sd_miss.append(str(cands[0]))
    for key, ps in sorted(miss.items()):
        res.append(f"WARN TREE-SOURCES {key} x{len(ps)} missing (base {base}): " + "; ".join(ps[:4])
                   + (f"; ... +{len(ps) - 4}" if len(ps) > 4 else ""))
    if sd_miss:
        res.append(f"WARN TREE-SOURCES *_sources folder x{len(sd_miss)} missing: " + "; ".join(sd_miss[:6])
                   + (f"; ... +{len(sd_miss) - 6}" if len(sd_miss) > 6 else ""))
    res.append(f"LIST TREE-SOURCES {n} path(s) + {len(sds)} *_sources folder(s) checked, "
               f"{sum(map(len, miss.values())) + len(sd_miss)} missing")
    return res


# ---------------------------------------------------------------- TREE-FRESH
def _local(host):
    return not host or host in ("localhost", socket.gethostname(), socket.gethostname().split(".")[0])


def default_runner(host, script, timeout=SSH_S):
    """-> (rc, stdout) of bash script, here or on host over ssh"""
    cmd = ["bash", "-c", script] if _local(host) else \
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, "bash -c " + shlex.quote(script)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout
    except (subprocess.TimeoutExpired, OSError) as e:
        return 124, f"ERR {type(e).__name__}"


def fork_source(rec):
    """(host, path) of the source a .fork.json names"""
    src = rec.get("src") or ""
    m = re.match(r"^([\w.-]+):(/.*)$", src)
    if m:
        return m.group(1), rec.get("src_real") or m.group(2)
    return rec.get("src_host") or "", rec.get("src_real") or src


def probe_script(src, since, rels):
    q = shlex.quote(src)
    dirs = " ".join(shlex.quote(r) for r in rels)
    return (f"cd {q} 2>/dev/null || {{ echo OT_GONE; exit 0; }}; echo OT_SEAL=$(cat .src-manifest.sha256 2>/dev/null | head -c 80); "
            f"test -w . && echo OT_WRITABLE; test -e .fork.json && echo OT_ISFORK; "
            f"for d in {dirs}; do test -d \"$d\" || continue; "
            f"l=$(find \"$d\" -maxdepth $( [ \"$d\" = rtl ] && echo 12 || echo 1) -type f -newermt @{int(since)} 2>/dev/null | head -200); "
            f"n=$(printf '%s\\n' \"$l\" | grep -c .); echo OT_NEWER $n \"$d\" $(printf '%s\\n' \"$l\" | head -3 | tr '\\n' ' '); done")


def check_tree_fresh(tree, plan, runner=default_runner):
    tree = Path(tree)
    fj = tree / ".fork.json"
    rec = _load(fj)
    if rec is None:
        seal = (tree / ".src-manifest.sha256")
        return [f"LIST TREE-FRESH {tree} is not an ot-tree-fork fork (no .fork.json)"
                + (f"; sealed tree {seal.read_text().strip()[:12]}" if seal.is_file() else "")]
    host, src = fork_source(rec)
    t_fork = rec.get("time_epoch") or 0
    when = rec.get("time_utc") or "?"
    was = (rec.get("src_manifest_hash") or "").strip()
    if host in TERMINATED:
        return [f"WARN TREE-FRESH source {host}:{src} is on a terminated host: the fork cannot be compared (forked {when})"]
    rels = list(FRESH_DIRS)
    try:
        pr = os.path.relpath(Path(plan).resolve().parent, tree.resolve())
        if not pr.startswith(".."):
            rels.append(pr)
    except (OSError, ValueError):
        pass
    rc, txt = runner(host, probe_script(src, t_fork, rels))
    where = f"{host}:{src}" if host and not _local(host) else src
    if rc == 124 or (rc and "OT_" not in txt):
        return [f"WARN TREE-FRESH source {where} not reachable ({txt.strip()[:80] or rc}): fork freshness unknown (forked {when})"]
    if "OT_GONE" in txt:
        return [f"WARN TREE-FRESH source {where} is gone: the fork (forked {when}) cannot be compared to it"]
    m = re.search(r"OT_SEAL=(\S*)", txt)
    now = m.group(1).strip() if m else ""
    out = []
    if was and now and now != was:
        out.append(f"WARN TREE-FRESH FORK-STALE source {where} seal is now {now[:12]}, the fork took {was[:12]} ({when}): "
                   f"the source was re-sealed after the fork; re-fork or diff before the gate")
    elif was and not now:
        out.append(f"WARN TREE-FRESH source {where} lost its seal (fork took {was[:12]}, {when}): it was unsealed or rewritten")
    elif now and not was:
        out.append(f"WARN TREE-FRESH source {where} was sealed {now[:12]} after the fork ({when}, unsealed then): the seal may "
                   f"carry changes the fork lacks")
    newer = []
    for ln in txt.splitlines():
        if ln.startswith("OT_NEWER "):
            parts = ln.split()
            if len(parts) >= 3 and parts[1].isdigit() and int(parts[1]) > 0:
                newer.append((parts[2], int(parts[1]), parts[3:6]))
    if newer and not (was and now == was):
        out.append(f"WARN TREE-FRESH SOURCE-NEWER source {where} has files newer than the fork ({when}): "
                   + "; ".join(f"{d} {n}{'+' if n >= 200 else ''} (e.g. {', '.join(ex)})" for d, n, ex in newer))
    out.append(f"LIST TREE-FRESH fork of {where} at {when}, seal then {was[:12] or '-'} now {now[:12] or '-'}"
               + (" (source is itself a fork)" if "OT_ISFORK" in txt else "") + (", fresh" if not out else ""))
    return out


# ---------------------------------------------------------------- driver
def findings(tree, plan, asbuilt=None, out=None, rt=None, checks=None, runner=default_runner):
    checks = [c.upper() for c in (checks or CLASSES)]
    rt = Path(rt) if rt else Path(__file__).resolve().parents[2]
    raw = _load(plan)
    res = []
    t0 = time.time()
    for c, fn in (("SCHEMA-KEYS", lambda: check_schema_keys(tree, plan, rt)),
                  ("TREE-SOURCES", lambda: check_tree_sources(tree, plan, raw, asbuilt, out)),
                  ("TREE-FRESH", lambda: check_tree_fresh(tree, plan, runner))):
        if c not in checks:
            continue
        try:
            res += fn()
        except Exception as e:  # noqa: BLE001 - report only: a crash names itself and never stops the gate
            res.append(f"WARN {c} not checked: {type(e).__name__}: {str(e)[:200]}")
    if raw is None:
        res.insert(0, f"WARN SCHEMA-KEYS plan {plan} does not read as json")
    res.append(f"LIST TREE-PRECHECK {len([x for x in res if x.startswith('WARN')])} warning(s) in {time.time() - t0:.1f} s (report only)")
    return res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tree_precheck", description=__doc__.split("\n\n")[0])
    ap.add_argument("--tree", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--asbuilt")
    ap.add_argument("--out", help="bind OUT dir (its bind.f is checked when present)")
    ap.add_argument("--rt", help="launch rt repo root (default: the repo this script runs from)")
    ap.add_argument("--checks", default=",".join(CLASSES))
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    if not Path(a.plan).is_file() or not Path(a.tree).is_dir():
        print(f"tree_precheck: need an existing --tree dir and --plan file", file=sys.stderr)
        return 2
    lines = findings(a.tree, a.plan, a.asbuilt, a.out, a.rt, a.checks.split(","))
    for x in lines:
        print(x)
    if a.json:
        Path(a.json).write_text(json.dumps({"tree": a.tree, "plan": a.plan, "findings": lines}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
