"""adv_define_noop.py -- PRECHECK ADV-DEFINE-NOOP (QC-INT-R2-COMBINE 11-26, class P-TREE-RTL-STALE; report only, never a gate).

A verilog define the plan SETS (partition_types.<t>.verilog_defines, or a die-wide define list) is a silent no-op when the bind
tree's RTL never tests it: QC C9 tree carried pre-366319e2e3b qfd_dv_s5_xhead3.sv / qfd_dv_s8_ce.sv / qfd_dv_stream_tile.sv, so
OT_QC_XH_SPLIT_FAULT (sle_hc0 cl38badc56) and OT_QC_STM_P2SEAT (sle_stm_v2 x2, sle_stm_v3) changed nothing and the scoped row
gates passed on the old netlist.  Per plan-set OT_* switch:
  NOOP    no tree rtl file tests it (`ifdef / `ifndef / `elsif / defined()) but main does: the files main tests it in are named
          with their state in the tree (LAG = an older main version, LOCAL = a private edit, MISSING)
  LAG     the tree tests it, but a tree file that tests it differs from main's copy and equals an older main version
  UNKNOWN neither the tree nor main tests it in rtl/ and no main tools/ or physical/ file names it (a typo or a removed switch);
          a switch only tools read (generator switches such as OT_ST_QNALT) is counted as tool-read, not listed
Main = the warm bare repo ($OT_ADV_MAIN_REPO, default as ADV-TREE-DRIFT) at its origin main ref; no main repo -> only tree-side
NOOP lines ("main not checked").  Stdlib only; never raises.
    findings(raw, plan_path=None, tree=None, main_repo=None, main_ref=None) -> [WARN lines]
"""
import os
import re
import subprocess
from pathlib import Path

CHECK = "ADV-DEFINE-NOOP"
MAX_LINES = 20
USE = re.compile(rb"(?:`\s*(?:ifn?def|elsif)\s+|defined\s*\(\s*)(OT_[A-Z0-9_]+)")
SUFFIX = (".sv", ".svh", ".v", ".vh")
WARM = "/srv/opentallas-scratch2/claude/warm/OpenTallas.git"
MAIN_REFS = ("refs/remotes/origin/main", "origin/main", "refs/heads/main", "main")


def _w(msg):
    return f"WARN {CHECK} {msg}"


def plan_switches(raw):
    """-> {OT_* switch: [types]} the plan sets"""
    out = {}
    for tn, t in (raw.get("partition_types") or {}).items():
        if isinstance(t, dict):
            for d in t.get("verilog_defines") or []:
                out.setdefault(str(d).split("=")[0].strip().lstrip("`+"), []).append(tn)
    for k in ("verilog_defines", "defines", "asbuilt_defines", "as_built_defines"):
        v = raw.get(k)
        for d in (v if isinstance(v, list) else list(v) if isinstance(v, dict) else []):
            out.setdefault(str(d).split("=")[0].strip().lstrip("`+"), [])
    return {s: sorted(set(t)) for s, t in out.items() if s.startswith("OT_")}


def tree_uses(tree, want):
    """-> {switch: [tree-relative rtl paths that test it]} for the switches in want"""
    hits = {s: [] for s in want}
    root = Path(tree) / "rtl"
    if not root.is_dir():
        return hits
    for dp, _dn, fn in os.walk(root):
        for f in fn:
            if not f.endswith(SUFFIX):
                continue
            p = Path(dp) / f
            try:
                b = p.read_bytes()
            except OSError:
                continue
            if b"OT_" not in b:
                continue
            for m in set(USE.findall(b)):
                s = m.decode()
                if s in hits:
                    hits[s].append(str(p.relative_to(tree)))
    return {s: sorted(v) for s, v in hits.items()}


def _git(repo, *args):
    r = subprocess.run(["git", "--git-dir", str(repo), *args], capture_output=True, timeout=120)
    return r.returncode, r.stdout


def _ref(repo, ref):
    for r in ([ref] if ref else []) + list(MAIN_REFS):
        if _git(repo, "rev-parse", "--verify", "-q", r + "^{commit}")[0] == 0:
            return r
    return None


def main_uses(repo, ref, want):
    """-> {switch: [rtl paths on main that test it]} via one git grep"""
    out = {s: [] for s in want}
    if not want:
        return out
    args = ["grep", "-l", "-E", "-e", r"(`[[:space:]]*(ifn?def|elsif)[[:space:]]+|defined[[:space:]]*\([[:space:]]*)(" + "|".join(sorted(want)) + r")\b",
            ref, "--", "rtl/"]
    rc, so = _git(repo, *args)
    if rc not in (0, 1):
        return None
    for line in so.decode(errors="replace").splitlines():
        path = line.split(":", 1)[1] if ":" in line else line
        rc2, body = _git(repo, "show", f"{ref}:{path}")
        if rc2:
            continue
        for m in set(USE.findall(body)):
            s = m.decode()
            if s in out:
                out[s].append(path)
    return {s: sorted(set(v)) for s, v in out.items()}


def _blob(path):
    r = subprocess.run(["git", "hash-object", str(path)], capture_output=True, timeout=60)
    return r.stdout.decode().strip() if r.returncode == 0 else None


def file_state(repo, ref, tree, path):
    """-> SAME | LAG | LOCAL | MISSING for a tree copy of a main rtl path"""
    p = Path(tree) / path
    if not p.is_file():
        return "MISSING"
    b = _blob(p)
    rc, so = _git(repo, "rev-parse", f"{ref}:{path}")
    if rc == 0 and so.decode().strip() == b:
        return "SAME"
    rc, so = _git(repo, "log", "--format=%H", "-n", "200", ref, "--", path)
    for c in so.decode().split():
        rc2, so2 = _git(repo, "rev-parse", f"{c}:{path}")
        if rc2 == 0 and so2.decode().strip() == b:
            return "LAG"
    return "LOCAL"


def _tree_of(plan_path, tree):
    if tree:
        return Path(tree)
    if plan_path:
        for p in Path(plan_path).resolve().parents:
            if (p / "rtl").is_dir() and (p / "physical").is_dir():
                return p
    return None


def findings(raw, plan_path=None, tree=None, main_repo=None, main_ref=None, **_kw):
    try:
        sw = plan_switches(raw)
        if not sw:
            return []
        t = _tree_of(plan_path, tree)
        if t is None:
            return [_w("not checked: no bind tree (rtl/ + physical/) above the plan")]
        tu = tree_uses(t, sw)
        repo = Path(main_repo or os.environ.get("OT_ADV_MAIN_REPO") or WARM)
        ref = _ref(repo, main_ref) if repo.exists() else None
        mu = main_uses(repo, ref, set(sw)) if ref else None
        out, n_noop, n_lag, n_unk, n_tool = [], 0, 0, 0, 0
        for s in sorted(sw):
            types = sw[s]
            tl = ", ".join(types[:4]) + (f" +{len(types) - 4}" if len(types) > 4 else "") if types else "die-wide"
            if not tu[s]:
                if mu is None:
                    n_noop += 1
                    out.append(_w(f"NOOP {s} (set on {tl}): no rtl file of the bind tree tests it; main not checked"))
                elif mu[s]:
                    n_noop += 1
                    st = [f"{p} {file_state(repo, ref, t, p)}" for p in mu[s][:4]]
                    out.append(_w(f"NOOP {s} (set on {tl}): no rtl file of the bind tree tests it, main does: {'; '.join(st)}"
                                  "; fix = carry those files into the tree (overlay) before bind, or drop the define"))
                elif _git(repo, "grep", "-q", "-w", "-e", s, ref, "--", "tools/", "physical/")[0] == 0:
                    n_tool += 1                 # a generator / tool switch (OT_ST_QNALT, OT_DLY_CPL): read by tools, not RTL
                else:
                    n_unk += 1
                    out.append(_w(f"UNKNOWN {s} (set on {tl}): neither the bind tree nor main tests it (typo or removed switch)"))
            elif mu:
                lag = [p for p in tu[s] if p in mu[s] and file_state(repo, ref, t, p) == "LAG"]
                if lag:
                    n_lag += 1
                    out.append(_w(f"LAG {s} (set on {tl}): tree copy older than main: {', '.join(lag[:4])}; fix = carry from main or record why"))
        if len(out) > MAX_LINES:
            out = out[:MAX_LINES] + [_w(f"... {len(out) - MAX_LINES} more")]
        out.append(_w(f"summary {len(sw)} plan-set switch(es): {n_noop} NOOP, {n_lag} LAG, {n_unk} UNKNOWN, {n_tool} tool-read"
                      + ("" if mu is not None else " (main not checked)") + " (report only)"))
        return out
    except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
        return [_w(f"not checked: {type(e).__name__}: {str(e)[:200]}")]


if __name__ == "__main__":
    import argparse
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--tree")
    ap.add_argument("--main-repo")
    a = ap.parse_args()
    for line in findings(json.loads(Path(a.plan).read_text()), a.plan, tree=a.tree, main_repo=a.main_repo):
        print(line)
