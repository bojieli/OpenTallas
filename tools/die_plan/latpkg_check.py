#!/usr/bin/env python3
"""latpkg_check.py -- PRE / bind class LATPKG (STATION-MOVE-HELPER 11-24, COORD from FABLE-RC-ALL hub 46fa8c69).  REPORT ONLY (WARN, r703).

Class: a latency package (gen.py latency output: <die>_latency.json, schema opentallas.die_plan.latency.v1, and <pkg>_lat_pkg.sv,
header '(plan digest X)') is copied forward into a new tree / prep dir while the plan moved on.  HEAD w3 prep_r18w3c/lat held the
a74be4f5 package, 85 values behind the plan; S81 c8 seal tree held 11-16 packages, 787 of 873 cycle values behind p6w_sg.

For every package found next to the plan (the plan's own dir, depth <= 3 -- a prep dir's lat/ --, the lat/ and r8/ dirs of
its ancestors up to physical/die_plan/<die>, --dirs and $OT_LATPKG_DIRS) whose die is the plan's die, the embedded plan digest is compared with gen.plan_digest of the bound plan.  A
mismatch is WARN LATPKG with the stale value count (lanes missing / extra / cycles differing from the plan latency table) and the
READERS: RTL files of the tree that import / reference the package (`<pkg>::`, `import <pkg>`) mapped to the plan types whose
module they declare, and tool / script files naming the json.  One LIST LATPKG line counts files, stale files and readers.

    python3 -I tools/die_plan/latpkg_check.py --plan PLAN [--tree TREE] [--dirs D1,D2] [--no-readers]
    exit 0 always (report only); 2 = bad input.  plan_gate_pre runs it (class LATPKG, --skip LATPKG), so does the bind's PRE.
Fix: regenerate on the bound plan (python3 -I tools/die_plan/gen.py latency ... / the die's postbind_lat step), install by copy+mv;
station_move.py does it for every package next to its PLAN_OUT (--regen, default on).

Schedule receipts (form LATPKG-SCHED, report only): a plan-derived schedule receipt (schema opentallas.s81_head.schedule_constants.v1,
regen_schedule_constants.py: per-lane raw_cycles) next to the plan (same roots as the packages) or in <tree>/results/token_pass/*/
belongs to the plan when >= half its lanes are plan lanes.  When receipts of the die exist but NONE carries the plan's lane cycles,
one WARN names the closest receipt and its stale value count (HEAD head_nf15b_schedule_1116 predated the 11-19 stations: coll_WN0_d
5 cycles vs 8).  Older receipts beside a current one are history, never listed.  Fix: station_move.py --regen-schedule RECEIPT.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "opentallas.die_plan.latency.v1"
SV_HEAD = re.compile(r"from die_plan (\S+) \(plan digest ([0-9a-f]+)\)")
SV_PARAM = re.compile(r"localparam\s+int\s+(\w+)\s*=\s*(-?\d+)\s*;")
MAX_DEPTH = 3
SKIP_DIRS = {".git", "node_modules", "__pycache__", "runs", "results", "kits"}
MAX_READERS = 12


def plan_digest(raw):
    """== gen.plan_digest (test_latpkg_check pins the equality): sha256 of the plan minus its latency table, sorted keys"""
    r = dict(raw)
    r.pop("latency", None)
    return hashlib.sha256(json.dumps(r, sort_keys=True).encode()).hexdigest()[:16]


def die_name(raw):
    return str((raw.get("die") or {}).get("name") or raw.get("name") or "")


def _is_pkg(name):
    return name.endswith("_latency.json") or name.endswith("_lat_pkg.sv")


def _is_sched(name):
    return name.endswith("_schedule.json")


def _walk(root, depth=MAX_DEPTH, want=_is_pkg):
    root = Path(root)
    if not root.is_dir():
        return
    stack = [(root, 0)]
    while stack:
        d, k = stack.pop()
        try:
            ents = list(os.scandir(d))
        except OSError:
            continue
        for e in ents:
            if e.is_file(follow_symlinks=False) and want(e.name):
                yield Path(e.path)
            elif e.is_dir(follow_symlinks=False) and k < depth and e.name not in SKIP_DIRS:
                stack.append((Path(e.path), k + 1))


def _roots(plan, dirs=()):
    p = Path(plan).resolve()
    roots = [(p.parent, MAX_DEPTH)] + [(Path(d), MAX_DEPTH) for d in dirs if d]
    roots += [(Path(x), MAX_DEPTH) for x in (os.environ.get("OT_LATPKG_DIRS") or "").split(",") if x]
    for q in list(p.parents)[:4]:                 # the die's own lat/ + r8/ dirs (physical/die_plan/<die>/lat), never sibling preps
        roots += [(q / "lat", 1), (q / "r8", 1)]
        if q.parent.name == "die_plan":
            break
    return roots


def find_packages(plan, tree=None, dirs=(), want=_is_pkg, extra_roots=()):
    seen, out = set(), []
    for r, dep in _roots(plan, dirs) + list(extra_roots):
        for f in _walk(r, dep, want):
            rp = f.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(f)
    return sorted(out)


def read_package(f):
    """-> dict(kind, die, digest, values {lane or param: cycles}) or None (not a latency package)"""
    try:
        if f.suffix == ".json":
            j = json.loads(f.read_text())
            if j.get("schema") != SCHEMA:
                return None
            return dict(kind="json", die=j.get("die"), digest=j.get("plan_digest"),
                        values={l: d.get("cycles") for l, d in (j.get("lanes") or {}).items()})
        txt = f.read_text(errors="replace")
        m = SV_HEAD.search(txt[:4000])
        if not m:
            return None
        return dict(kind="sv", die=m.group(1), digest=m.group(2), pkg=f.stem, values=dict((a, int(b)) for a, b in SV_PARAM.findall(txt)))
    except (OSError, ValueError):
        return None


SCHED_SCHEMAS = ("opentallas.s81_head.schedule_constants.v1",)
SCHED_ROOTS = ("results/token_pass",)


def find_schedules(plan, tree=None, dirs=()):
    root = tree_root(plan, tree)
    return find_packages(plan, tree, dirs, want=_is_sched, extra_roots=[(root / r, 1) for r in SCHED_ROOTS])


def read_schedule(f):
    """-> dict(kind=json, values {lane: raw_cycles}, plan_sha256) or None (not a schedule receipt)"""
    try:
        j = json.loads(Path(f).read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(j, dict) or j.get("schema") not in SCHED_SCHEMAS or not isinstance(j.get("lanes"), dict):
        return None
    vals = {l: (d.get("raw_cycles", d.get("cycles")) if isinstance(d, dict) else None) for l, d in j["lanes"].items()}
    return dict(kind="json", values=vals, plan_sha256=(j.get("inputs") or {}).get("plan_sha256"))


def sched_findings(raw, plan, tree=None, dirs=()):
    """-> (lines, n receipts of this die, stale 0/1)"""
    lanes = (raw.get("latency") or {}).get("lanes") or {}
    if not lanes:
        return [], 0, 0
    try:
        sha = hashlib.sha256(Path(plan).read_bytes()).hexdigest()
    except OSError:
        sha = None
    mine = []
    for f in find_schedules(plan, tree, dirs):
        sc = read_schedule(f)
        if sc is None or not sc["values"] or len(set(sc["values"]) & set(lanes)) * 2 < len(sc["values"]):
            continue
        miss, extra, diff = stale_values(sc, raw)
        n = len(miss) + len(extra) + len(diff)
        if n == 0 or (sha and sc["plan_sha256"] == sha):
            return [], len(mine) + 1, 0
        mine.append((n, str(f), miss, extra, diff))
    if not mine:
        return [], 0, 0
    n, f, miss, extra, diff = min(mine)
    root = tree_root(plan, tree)
    rel = os.path.relpath(f, root) if str(Path(f).resolve()).startswith(str(root.resolve())) else f
    return [f"WARN LATPKG-SCHED no schedule receipt of the die carries the bound plan's lane cycles ({len(mine)} receipt(s)); closest "
            f"{rel}: {n} stale value(s) (missing {len(miss)}, extra {len(extra)}, cycles differ {len(diff)}"
            + (f", e.g. {(diff or miss)[:4]}" if (diff or miss) else "") + ")  (fix: station_move.py --regen-schedule / "
            "regen_schedule_constants.py on the bound plan)"], len(mine), 1


def stale_values(pk, raw):
    lanes = (raw.get("latency") or {}).get("lanes") or {}
    if pk["kind"] == "json":
        want = {l: d.get("cycles") for l, d in lanes.items()}
    else:
        want = {d.get("param"): d.get("cycles") for d in lanes.values() if d.get("param")}
        want.update({f"{d['param']}_WORD": None for d in lanes.values() if d.get("param") and d.get("beats")})
        have = pk["values"]
        pk = dict(pk, values={k: v for k, v in have.items() if k in want or k.startswith("LAT_")})
    have = pk["values"]
    missing = sorted(set(want) - set(have))
    extra = sorted(set(have) - set(want))
    diff = sorted(k for k in set(want) & set(have) if want[k] is not None and want[k] != have[k])
    return missing, extra, diff


def _grep(root, pattern, includes):
    if not Path(root).is_dir():
        return []
    cmd = ["grep", "-rlE", "--binary-files=without-match"] + [f"--include={i}" for i in includes] + \
          [f"--exclude-dir={d}" for d in sorted(SKIP_DIRS)] + [pattern, str(root)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=int(os.environ.get("OT_LATPKG_GREP_S", "120")))
    except (OSError, subprocess.TimeoutExpired):
        return None
    return [Path(x) for x in r.stdout.splitlines() if x]


MODULE = re.compile(r"^\s*module\s+(\w+)", re.M)


def readers(tree, raw, pk, f):
    """-> (types, modules, tool files) that read the package, or None when the search could not run"""
    tree = Path(tree)
    types, mods, tools = set(), set(), set()
    by_mod = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        by_mod.setdefault(t.get("module") or tn, set()).add(tn)
    if pk["kind"] == "sv":
        pat = rf"(import\s+{pk['pkg']}\b|\b{pk['pkg']}::)"
        hits = []
        for sub in ("rtl", "physical"):
            h = _grep(tree / sub, pat, ("*.sv", "*.v", "*.svh", "*.f"))
            if h is None:
                return None
            hits += h
        for h in hits:
            if h.resolve() == f.resolve():
                continue
            try:
                ms = MODULE.findall(h.read_text(errors="replace"))
            except OSError:
                ms = []
            for m in ms:
                mods.add(m)
                types |= by_mod.get(m, set())
    pat = re.escape(f.name)
    for sub in ("tools", "physical/common_flow"):
        h = _grep(tree / sub, pat, ("*.py", "*.sh", "*.tcl", "*.mk", "*.json"))
        if h is None:
            return None
        tools |= {str(x.relative_to(tree)) if tree in x.parents else str(x) for x in h}
    return sorted(types), sorted(mods), sorted(tools)


def tree_root(plan, tree=None):
    if tree:
        return Path(tree)
    p = Path(plan).resolve().parent
    for q in [p] + list(p.parents):
        if (q / "tools" / "die_plan").is_dir() or ((q / "physical").is_dir() and (q / "rtl").is_dir()):
            return q
    return p


def findings(raw, plan, tree=None, dirs=(), want_readers=True):
    dig, die = plan_digest(raw), die_name(raw)
    root = tree_root(plan, tree)
    out, n, stale, nread = [], 0, 0, 0
    for f in find_packages(plan, tree, dirs):
        pk = read_package(f)
        if pk is None or (die and pk.get("die") and pk["die"] != die):
            continue
        n += 1
        if pk.get("digest") == dig:
            continue
        stale += 1
        miss, extra, diff = stale_values(pk, raw)
        rd = readers(root, raw, pk, f) if want_readers else None
        if rd is None:
            who = "readers not searched" if not want_readers else "reader search failed (timeout)"
        else:
            ty, mo, to = rd
            nread += len(ty) + len(to)
            who = (f"types reading it: {ty[:MAX_READERS]}{' ...' if len(ty) > MAX_READERS else ''}" if ty else "no plan type's RTL reads it") + \
                  (f"; RTL modules {mo[:MAX_READERS]}" if mo and not ty else "") + \
                  (f"; tools naming it: {to[:MAX_READERS]}" if to else "; no tool names it")
        rel = os.path.relpath(f, root) if root in f.resolve().parents or root in f.parents else str(f)
        out.append(f"WARN LATPKG {rel}: package plan digest {pk.get('digest')} != bound plan {dig}; "
                   f"{len(miss) + len(extra) + len(diff)} stale value(s) (missing {len(miss)}, extra {len(extra)}, cycles differ {len(diff)}"
                   + (f", e.g. {(diff or miss)[:4]}" if (diff or miss) else "") + f"); {who}  (fix: regenerate on the bound plan, gen.py latency)")
    try:
        sl, ns, ss = sched_findings(raw, plan, tree, dirs)
    except Exception as e:  # noqa: BLE001 - names itself, never passes silently
        sl, ns, ss = [f"WARN LATPKG-SCHED not checked: {type(e).__name__}: {str(e)[:200]}"], 0, 0
    out += sl
    out.append(f"LIST LATPKG files={n} stale={stale} readers={nread} sched={ns} sched_stale={ss} plan_digest={dig} (report only, r703)")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tree")
    ap.add_argument("--dirs", default="")
    ap.add_argument("--no-readers", action="store_true")
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
    except (OSError, ValueError) as e:
        print(f"latpkg_check: bad input: {e}", file=sys.stderr)
        return 2
    print("\n".join(findings(raw, a.plan, a.tree, [d for d in a.dirs.split(",") if d], not a.no_readers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
