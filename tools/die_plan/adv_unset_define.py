"""adv_unset_define.py -- PRECHECK ADV-UNSET-DEFINE (COORD 11-24, FABLE-RC-QC hub bc55ab84; report only).

A switch (`ifdef / `ifndef / `elsif / defined(OT_*)) ADDED on main in the last DAYS days (default 7) that this plan never sets: no type lists it in
partition_types.<t>.verilog_defines (name before '=') and no other top-level plan key names it.  Such a switch is dead code for this die until a row sets it
(OT_TP8S_RDPIPE / OT_TP8S_XEPRE sat unapplied for a day).  Per switch: first commit that added a use, file, the modules the file defines, and the plan types
whose module / contents name one of them = the types it targets.  kw days / main_repo / main_ref (as ADV-TREE-DRIFT).
PRECHECK-R3 11-24: with a bind tree (kw tree / the tree above the plan) a switch counts only when its file is in the tree's RTL
closure of the plan's types (IN-BIND-RTL, the types that reach it listed) or a type names its module; switches in RTL the plan
never reaches (other dies) and mutation / test-bench controls are counted in the summary, not listed.
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


def is_control(sw, f):
    """mutation / negative-control switches and test-bench files: never meant for a plan row"""
    b = f.rsplit("/", 1)[-1]
    return (bool(re.search(r"(^|_)MUT(ANT)?(_|$)", sw[3:])) or b.startswith(("tb_", "test_")) or "/test/" in f or "/tb/" in f
            or f.startswith("results/"))          # archived reference copies (results/rtl/.../ref_old_src) are not build RTL


def family(sw):
    """OT_BKSEL_RC -> OT_BKSEL, OT_S81_KVLEAF_EXIT_RELAYS -> OT_S81_KVLEAF_EXIT (the name without its last token)"""
    return sw.rsplit("_", 1)[0] if sw.count("_") >= 2 else sw


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
    # the bind-tree RTL closure of the plan's types (ADV-TREE-DRIFT): a switch in a file the types reach is live code here
    tree = tree or kw.get("tree") or T._find_tree(plan_path)
    rtlix, closure = None, {}
    if tree and (Path(tree) / "rtl").is_dir():
        rtlix = T.rtl_index(tree)
        closure = T.rtl_closure(raw, tree, index=rtlix)
    rows, ctrl, else_names = [], 0, []
    for sw, (c, d, f) in sorted(added.items()):
        if sw in have:
            continue
        if is_control(sw, f):
            ctrl += 1
            continue
        try:
            mods = MOD.findall(_git(gd, ["show", f"{ref}:{f}"], 60))
        except Exception:  # noqa: BLE001
            mods = []
        tg = set(t for m in mods for t in bymod.get(m, []))
        inclo = f in closure
        if inclo:
            tg |= set(T.closure_types(raw, rtlix, [f]).get(f, []))
        fam = family(sw)
        sib = {t for h, ts in have.items() if h != sw and family(h) == fam for t in ts}
        if sib and not inclo:     # a sibling switch of the same family is set here (in the closure the reaching types are exact)
            tg |= sib
        tg = sorted(tg)
        if not tg and not inclo:
            else_names.append(sw)
            continue
        rows.append((sw, c, d, f, mods, tg, bool(sib), inclo))
    rows.sort(key=lambda r: (not r[7], not r[6], not r[5], r[0]))
    out = []
    for sw, c, d, f, mods, tg, sib, inclo in rows[:MAX_LINES]:
        out.append(_w(f"{sw}: not set by this plan; added {d} in {c} file {f} (modules {','.join(mods[:3]) or '?'}); "
                      f"{'IN-BIND-RTL ' if inclo else ''}{'SIBLING-SET ' if sib else ''}"
                      f"targets {len(tg)} type(s) here: {','.join(tg[:4]) or '-'}{' ...' if len(tg) > 4 else ''}; "
                      f"fix = a row sets it on the target types (verilog_defines) or record why this die keeps it off"))
    ninc = sum(1 for r in rows if r[7])
    out.append(_w("summary", f"{len(added)} switch(es) added on main in {days} d; {len(added) - len(rows) - ctrl - len(else_names)} set by this plan; "
                  f"{len(rows)} UNSET here ({ninc} in the bind-tree RTL closure of {len(closure)} file(s), {sum(1 for r in rows if r[6])} with a sibling of the same family set here, "
                  f"{len(rows) - ninc} by module name / sibling only); "
                  f"{ctrl} mutation/test control(s) skipped; {len(else_names)} in RTL this plan does not reach "
                  f"({','.join(else_names[:6])}{' ...' if len(else_names) > 6 else ''}); main {ref[:10]}"
                  + ("" if closure else "; no bind tree: targets by name only")))
    return out


def findings(raw, plan_path, tree=None, **kw):
    try:
        return _findings(raw, plan_path, tree, **kw)
    except Exception as e:  # noqa: BLE001
        return [_w("not checked", f"{type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    for ln in findings(json.load(open(sys.argv[1])), sys.argv[1], None):
        print(ln)
