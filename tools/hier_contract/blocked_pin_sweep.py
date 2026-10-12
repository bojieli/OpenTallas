#!/usr/bin/env python3
"""Sweep CLOSED route_master tile routes whose keepout hook was silently dropped, for child_lint (f) blocked face pins.

Background (main f4abe8c83): physical/qwen_die_masters/jobs/route_master.sh always overrode a cfg's own EXTRA
`--step-tcl PRE_GLOBAL_ROUTE=... / POST_DETAIL_ROUTE=...` (so a cfg's pin-keepout hook, e.g. stn_pin_keepout.tcl or
pin_access_pregrt.tcl, never ran), and dropped OT_RM_PK's keepout whenever PINKO was also set.  A tile routed that way
may have closed with its face pins covered on the layer above -> DRT-0073 (no access point) at parent / die assembly.

Selection: every CLOSED record (closure-loop jobs; closed archive /home/ubuntu/closed_archive/<element>/<job>/) whose route stage
runs route_master.sh and whose cfg (read at the job's own source commit) names a keepout hook on a route-owned step in
EXTRA, or which set OT_RM_PK=1 together with PINKO=1 (records come from the closure loop's CLOSED jobs and the
closed archive).  Closed route_master records whose keepout came from OT_RM_PK / PINKO alone are checked as a control.  Jobs whose source commit already contains f4abe8c83 are
listed but not flagged (their hook ran).

Check: tools/hier_contract/child_lint.py face_access ((f): signal face pins with OBS on the layer above) on the
exported LEF (archive final/<block>.lef, else the record's published LEF on main).

Output: results/arch/hier_contract_1011/blocked_pin_sweep.json (tile, job, pins blocked / total, parent, owner).
LEF parsing only: lightweight, runs locally.
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import child_lint  # noqa: E402

FIX = "f4abe8c83"
ARCHIVE = Path("/home/ubuntu/closed_archive")
HOOK_RE = re.compile(r"keepout|pin_access|pinko|_pk[_.]", re.I)
ROUTE_STEPS = ("PRE_GLOBAL_ROUTE", "POST_DETAIL_ROUTE")


def git(*a: str) -> str:
    r = subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else ""


def contains_fix(commit: str) -> bool:
    return subprocess.run(["git", "-C", str(REPO), "merge-base", "--is-ancestor", FIX, commit],
                          capture_output=True).returncode == 0


def cfg_extra(commit: str, cfg: str) -> tuple[list[str], str]:
    """EXTRA[] tokens and raw text of physical/qwen_die_masters/cfg/<cfg>.env at commit"""
    txt = git("show", f"{commit}:physical/qwen_die_masters/cfg/{cfg}.env")
    toks: list[str] = []
    for m in re.finditer(r"(?ms)^\s*EXTRA(\+?)=\((.*?)\)\s*$", txt):
        toks += re.findall(r"'[^']*'|\"[^\"]*\"|\S+", m.group(2))
    return [t.strip("'\"") for t in toks], txt


def dropped_hooks(cmd: str, commit: str) -> tuple[str | None, list[str]]:
    m = re.search(r"route_master\.sh\s+(\S+)", cmd)
    if not m:
        return None, []
    cfg = m.group(1)
    extra, txt = cfg_extra(commit, cfg)
    hooks = []
    for i, t in enumerate(extra[:-1]):
        if t == "--step-tcl" and extra[i + 1].split("=", 1)[0] in ROUTE_STEPS and HOOK_RE.search(extra[i + 1]):
            hooks.append(extra[i + 1])
    pinko = re.search(r"\bPINKO=1\b", cmd) or re.search(r"(?m)^\s*PINKO=1\b", txt)
    if re.search(r"\bOT_RM_PK=1\b", cmd) and pinko:
        hooks.append("OT_RM_PK=1 (dropped: PINKO=1)")
    return cfg, hooks


def find_lef(d: Path | None, man: dict, spec: dict, block: str) -> Path | None:
    if d is not None:
        for p in [d / "final" / f"{block}.lef", *sorted((d / "final").glob("*.lef"))]:
            if p.exists():
                return p
    for rec in (man.get("record") or []) + (spec.get("record") or [] if isinstance(spec.get("record"), list) else []):
        to = rec.get("to")
        if to:
            hits = sorted((REPO / to).glob("*.lef"))
            if hits:
                return hits[0]
    return fetch_remote_lef(man, block)


CACHE = Path("/tmp/claude-1000/blocked_pin_sweep_lefs")


def fetch_remote_lef(man: dict, block: str) -> Path | None:
    """the run's exported record/views LEF on its route host (job not yet archived)"""
    host, run = man.get("host"), man.get("run_dir")
    if not host or not run or host == "localhost":
        return None
    dst = CACHE / man["job"]
    hit = sorted(dst.glob("*.lef")) if dst.exists() else []
    if hit:
        return hit[0]
    ssh = ["ssh", "-o", "ControlPath=none", "-o", "ConnectTimeout=15", "-o", "BatchMode=yes", host]
    r = subprocess.run(ssh + [f"find {run}/record -name '*.lef' 2>/dev/null | grep -v -e _bloat -e /macros/ | head -20"],
                       capture_output=True, text=True, timeout=120)
    lefs = [l for l in r.stdout.split() if l.endswith(".lef")]
    pick = next((l for l in lefs if Path(l).stem == block), None) or (lefs[0] if lefs else None)
    if not pick:
        return None
    dst.mkdir(parents=True, exist_ok=True)
    out = dst / Path(pick).name
    r = subprocess.run(ssh + [f"cat {pick}"], capture_output=True, timeout=300)
    if r.returncode or not r.stdout:
        return None
    out.write_bytes(r.stdout)
    return out


def parent_index() -> dict:
    """cell -> [parents]: hier contract slots, then cfgs that hard-place the cell as a macro"""
    idx: dict[str, set] = {}
    for f in glob.glob(str(REPO / "results/arch/hier_contract_1011/*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        slots = d.get("slots") or []
        names = {s.get("name"): s.get("cell") for s in slots if isinstance(s, dict)}
        for s in slots:
            if isinstance(s, dict) and s.get("cell") and s.get("parent"):
                idx.setdefault(s["cell"], set()).add(f"{d.get('die')}:{names.get(s['parent'], s['parent'])}")
    for f in glob.glob(str(REPO / "physical/qwen_die_masters/cfg/*.env")):
        t = Path(f).read_text(errors="replace")
        for c in re.findall(r"--macro-view\s+'?([A-Za-z0-9_]+)=", t):
            idx.setdefault(c, set()).add("cfg:" + Path(f).stem)
    return {k: sorted(v) for k, v in idx.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--archive", default=str(ARCHIVE))
    ap.add_argument("--jobs", default=str(Path.home() / ".local/state/closure_loop/jobs"))
    ap.add_argument("--out", default=str(REPO / "results/arch/hier_contract_1011/blocked_pin_sweep.json"))
    a = ap.parse_args(argv)
    parents = parent_index()
    rows, control, n_rm = [], [], 0
    recs = {}  # job -> (archive dir or None, manifest, spec, commit)
    for f in sorted(Path(a.jobs).glob("*.json")):
        try:
            j = json.load(open(f))
        except Exception:
            continue
        if j.get("status") == "CLOSED" and isinstance(j.get("spec"), dict):
            recs[j["name"]] = (None, {"job": j["name"], "element": j["spec"].get("block"), "owner": j["spec"].get("owner"),
                                      "record": [], "closed_at": j.get("updated"), "host": j.get("host"),
                                      "run_dir": j.get("run")}, j["spec"], j.get("commit_full") or "")
    for d in sorted(Path(a.archive).glob("*/*")):
        try:
            man = json.load(open(d / "manifest.json"))
            spec = json.load(open(d / "spec.json"))
        except Exception:
            continue
        if not str((man.get("metrics") or {}).get("reason", "")).startswith("CLOSED"):
            continue
        recs[man.get("job") or d.name] = (d, man, spec, man.get("commit") or (spec.get("source") or {}).get("commit", ""))
    for job, (d, man, spec, commit) in sorted(recs.items()):
        cmd = str(((spec.get("stages") or {}).get("route") or {}).get("cmd", ""))
        if "route_master.sh" not in cmd:
            continue
        n_rm += 1
        cfg, hooks = dropped_hooks(cmd, commit)
        knob = re.search(r"\b(OT_RM_PK|PINKO)=1\b", cmd + cfg_extra(commit, cfg or "")[1])
        if not hooks and not knob:
            continue
        block = man.get("block") or spec.get("block")
        lef = find_lef(d, man, spec, block)
        row = {"element": man.get("element"), "job": job, "archive": str(d) if d else None, "block": block, "cfg": cfg, "commit": commit[:11],
               "has_fix": contains_fix(commit), "dropped_hooks": hooks, "owner": man.get("owner") or spec.get("owner"),
               "closed_at": man.get("closed_at"), "lef": str(lef) if lef else None}
        if lef:
            m = child_lint.parse_lef(lef.read_text(errors="replace"))
            fa = child_lint.face_access(m)
            sig = {n for n, p in m["pins"].items() if not child_lint.is_pg(n, p)
                   and any(child_lint.face_of(r, m["W"], m["H"]) and child_lint.metal(r[0]) for r in p["rects"])}
            row.update(cell=m["name"], face_pins=len(sig), face_pin_rects=fa["face_pins"],
                       blocked_above=fa["blocked_above"], blocked=f"{fa['blocked_above']}/{len(sig)}",
                       examples=fa["examples"][:3])
        else:
            row.update(cell=block, error="no exported LEF in archive or record")
        row["parent"] = parents.get(row.get("cell") or block) or parents.get(block) or []
        row["needs_reroute"] = bool(hooks) and bool(row.get("blocked_above")) and not row["has_fix"]
        (rows if hooks else control).append(row)
    out = {"schema": "opentallas.hier_contract.blocked_pin_sweep.v1", "fix_commit": FIX, "archive": a.archive,
           "selection": "CLOSED route_master.sh records whose cfg EXTRA names a keepout hook on PRE_GLOBAL_ROUTE/"
                        "POST_DETAIL_ROUTE (or OT_RM_PK=1 with PINKO=1); check = child_lint (f) on the exported LEF",
           "route_master_closed": n_rm, "checked": len(rows),
           "with_blocked": sum(1 for r in rows if r.get("blocked_above")),
           "needs_reroute": sum(1 for r in rows if r["needs_reroute"]), "tiles": rows,
           "control_note": "closed route_master records whose keepout came from OT_RM_PK / PINKO (ran as intended; "
                           "informational, not in the affected set)",
           "control_checked": len(control), "control_with_blocked": sum(1 for r in control if r.get("blocked_above")),
           "control": control}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in rows + [c for c in control if c.get("blocked_above") or c.get("error")]:
        print(("" if r in rows else "[control] ") +f"{r['element']:28s} {r['job'][:48]:48s} {r.get('blocked', r.get('error'))} fix={r['has_fix']} "
              f"parent={','.join(r['parent']) or '-'}")
    print(f"checked {len(rows)} (of {n_rm} closed route_master records); blocked {out['with_blocked']}; "
          f"needs re-route {out['needs_reroute']}; "
          f"control {len(control)} checked, {out['control_with_blocked']} blocked -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
