"""adv_unset_define.py -- PRECHECK ADV-UNSET-DEFINE (COORD 11-24, FABLE-RC-QC hub bc55ab84; report only).

A switch (`ifdef / `ifndef / `elsif / defined(OT_*)) ADDED on main in the last DAYS days (default 7) that this plan never sets: no type lists it in
partition_types.<t>.verilog_defines (name before '=') and no other top-level plan key names it.  Such a switch is dead code for this die until a row sets it
(OT_TP8S_RDPIPE / OT_TP8S_XEPRE sat unapplied for a day).  Per switch: first commit that added a use, file, the modules the file defines, and the plan types
whose module / contents name one of them = the types it targets.  kw days / main_repo / main_ref (as ADV-TREE-DRIFT).
findings(raw, plan_path, tree=None, **kw) -> WARN lines, never raises.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

CHECK = "ADV-UNSET-DEFINE"
MAX_LINES = 40
USE = re.compile(r"(?:`\s*(?:ifn?def|elsif)\s+|defined\s*\(\s*)(OT_[A-Z0-9_]+)")
MOD = re.compile(r"^\s*module\s+(\w+)", re.M)


def _w(*p):
    return " ".join(["WARN", CHECK] + [str(x) for x in p])


def plan_switches(raw):
    """-> {switch: [types]} every OT_* the plan sets (type verilog_defines names; any other top-level key mentioning one: types [])"""
    out = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        if isinstance(t, dict):
            for d in t.get("verilog_defines") or []:
                out.setdefault(str(d).split("=")[0].strip().lstrip("`+"), []).append(tn)
    for k in ("verilog_defines", "defines", "asbuilt_defines", "as_built_defines"):   # die-wide define lists (not free text: notes name signals / switches)
        v = raw.get(k)
        for d in (v if isinstance(v, list) else list(v) if isinstance(v, dict) else []):
            out.setdefault(str(d).split("=")[0].strip().lstrip("`+"), [])
    return out


def added_switches(log_text):
    """parse `git log -p -U0 --format=@@C %h %ad %s` -> {switch: (commit, date, file)} earliest commit adding a use"""
    out, cur, f = {}, None, None
    for ln in log_text.splitlines():
        if ln.startswith("@@C "):
            cur, f = ln[4:].split(" ", 2), None
        elif ln.startswith("+++ b/"):
            f = ln[6:]
        elif ln.startswith("+") and not ln.startswith("+++") and cur and f:
            for m in USE.finditer(ln):
                out[m.group(1)] = (cur[0], cur[1], f)     # newest first: the last overwrite is the earliest commit
    return out


def _git(gd, args, timeout=240):
    r = subprocess.run(["git", "--git-dir", gd] + args, capture_output=True, timeout=timeout)
    if r.returncode:
        raise RuntimeError(r.stderr.decode(errors="replace")[-200:])
    return r.stdout.decode(errors="replace")


def _findings(raw, plan_path, tree=None, **kw):
    import adv_tree_drift as T
    gd, ref = T._repo_main(kw)
    if not gd:
        return [_w("NOT-RUN: no main repo (kw main_repo / OT_ADV_MAIN_REPO)")]
    days = int(kw.get("days") or 7)
    log = _git(gd, ["log", f"--since={days}.days", ref, "-p", "-U0", "--no-color", "--date=short", "--format=@@C %h %ad %s", "-G", "OT_[A-Z0-9_]+",
                    "--", "*.sv", "*.v", "*.svh", "*.vh"])
    added = added_switches(log)
    have = plan_switches(raw)
    types = raw.get("partition_types") or {}
    bymod = {}
    for tn, t in types.items():
        if isinstance(t, dict):
            small = {k: v for k, v in t.items() if k in ("module", "contents", "cells", "note")}
            for m in set(re.findall(r"[A-Za-z_]\w+", json.dumps(small))):
                bymod.setdefault(m, []).append(tn)
    rows = []
    for sw, (c, d, f) in sorted(added.items()):
        if sw in have:
            continue
        try:
            mods = MOD.findall(_git(gd, ["show", f"{ref}:{f}"], 60))
        except Exception:  # noqa: BLE001
            mods = []
        tg = sorted({t for m in mods for t in bymod.get(m, [])})
        rows.append((sw, c, d, f, mods, tg))
    out = []
    for sw, c, d, f, mods, tg in rows[:MAX_LINES]:
        out.append(_w(f"{sw}: not set by this plan; added {d} in {c} file {f} (modules {','.join(mods[:3]) or '?'}); "
                      f"targets {len(tg)} type(s) here: {','.join(tg[:4]) or 'none instantiate its modules'}{' ...' if len(tg) > 4 else ''}"))
    hit = sum(1 for r in rows if r[5])
    out.append(_w("summary", f"{len(added)} switch(es) added on main in {days} d; {len(added) - len(rows)} set by this plan; {len(rows)} UNSET "
                  f"({hit} of them in a module this plan instantiates, {len(rows) - hit} elsewhere); main {ref[:10]}"))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], None):
        print(ln)
