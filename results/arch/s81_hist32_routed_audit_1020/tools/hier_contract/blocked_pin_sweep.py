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

--all (2026-10-12, RELAUNCH 4): every CLOSED tile / leaf record (closure-loop jobs + closed archive), not only
route_master ones: child_lint (c) strap layer and (f) blocked-above on the exported view LEF (archive final/, else the
record's published dir on main, else --remote: the run's record/ on its host).  Notes whether the record went through
the loop's post-route hold ECO and whether that ECO ran before the keepout re-apply fix a804fc09b (ECO DRT put nets
back over the face pins: blocked_pin_sweep.json's 4 blocked tiles were exactly the 4 hold-ECO'd ones).  A record with
a parent (hier contract slot / cfg --macro-view) is "used"; a used view failing (c)/(f) is the action list: re-export
(ref_tile.py export) when only the view is wrong, else re-route on main >= a804fc09b.
Output: results/arch/hier_contract_1011/blocked_pin_sweep_all.json.
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


ECO_FIX, ECO_FIX_AT = "a804fc09b", "2026-10-12T00:15:23-07:00"   # daemon tree hold_eco.sh carries OT_ECO_PK from here


def lef_for(d: Path | None, man: dict, spec: dict, block: str, remote: bool) -> tuple[Path | None, str]:
    if d is not None:
        for p in [d / "final" / f"{block}.lef", *sorted((d / "final").glob("*.lef"))]:
            if p.exists() and "_bloat" not in p.name:
                return p, "archive"
    recs = (man.get("record") or []) + (spec.get("record") or [] if isinstance(spec.get("record"), list) else [])
    for rec in recs:
        to = rec.get("to")
        if not to or not (REPO / to).is_dir():
            continue
        hits = [h for h in sorted((REPO / to).rglob("*.lef")) if "_bloat" not in h.name and "/macros/" not in str(h)]
        pick = next((h for h in hits if h.stem == block), None) or (hits[0] if hits else None)
        if pick:
            return pick, "main"
    if remote:
        try:
            p = fetch_remote_lef(man, block)
        except Exception:  # noqa: BLE001
            p = None
        if p:
            return p, "remote"
    return None, ""


def main_all(a) -> int:
    parents = parent_index()
    recs = {}
    for f in sorted(Path(a.jobs).glob("*.json")):
        try:
            j = json.load(open(f))
        except Exception:
            continue
        if j.get("status") == "CLOSED" and isinstance(j.get("spec"), dict):
            recs[j["name"]] = (None, {"job": j["name"], "element": j["spec"].get("block"), "owner": j["spec"].get("owner"),
                                      "record": [], "closed_at": j.get("updated"), "host": j.get("host"),
                                      "run_dir": j.get("run")}, j["spec"], j.get("commit_full") or "", j)
    for d in sorted(Path(a.archive).glob("*/*")):
        try:
            man = json.load(open(d / "manifest.json"))
            spec = json.load(open(d / "spec.json"))
        except Exception:
            continue
        if not str((man.get("metrics") or {}).get("reason", "")).startswith("CLOSED"):
            continue
        try:
            j = json.load(open(d / "job.json"))
        except Exception:
            j = {}
        recs[man.get("job") or d.name] = (d, man, spec, man.get("commit") or (spec.get("source") or {}).get("commit", ""), j)
    rows, lint_cache = [], {}
    for job, (d, man, spec, commit, j) in sorted(recs.items()):
        block = man.get("block") or spec.get("block")
        lef, src = lef_for(d, man, spec, block, a.remote)
        e = (j or {}).get("eco") or {}
        eco = bool(e.get("installed"))
        row = {"element": man.get("element") or block, "job": job, "block": block, "commit": (commit or "")[:11],
               "owner": man.get("owner") or spec.get("owner"), "closed_at": man.get("closed_at"),
               "ref_tile": bool(spec.get("ref_tile")), "hold_eco": eco,
               "hold_eco_started": e.get("started") if eco else None,
               "hold_eco_pre_fix": bool(eco and str(e.get("started") or "") < ECO_FIX_AT),
               "lef": str(lef) if lef else None, "lef_source": src}
        if lef:
            key = str(lef)
            if key not in lint_cache:
                try:
                    lint_cache[key] = child_lint.lint(key, skip=set("abdeg"))
                except Exception as ex:  # noqa: BLE001
                    lint_cache[key] = {"verdict": "ERROR", "fails": [f"lint error: {ex}"[:200]], "info": {}}
            res = lint_cache[key]
            fa = (res.get("info") or {}).get("face") or {}
            row.update(cell=(res.get("info") or {}).get("cell") or block,
                       strap_layer=(res.get("info") or {}).get("strap_layer"),
                       c_fail=any(x.startswith("(c)") for x in res["fails"]),
                       f_fail=any(x.startswith("(f)") for x in res["fails"]),
                       face_pin_rects=fa.get("face_pins"), blocked_above=fa.get("blocked_above"),
                       examples=(fa.get("examples") or [])[:3], fails=[x[:240] for x in res["fails"]])
        else:
            row.update(cell=block, error="no exported LEF (archive final/, main record dir" + (", remote record/" if a.remote else "") + ")")
        row["parent"] = parents.get(row.get("cell") or block) or parents.get(block) or []
        row["used"] = bool(row["parent"])
        bad = row.get("c_fail") or row.get("f_fail")
        if bad:
            # only the view is wrong when (c) alone fails (an export layer/OBS choice) or (f) on a view whose route was
            # never hold-ECO'd pre-fix (keepout lost in the abstract, not the wires) -- the routed db must be checked to
            # tell; ECO'd-pre-fix + (f) means the ECO's wires really sit over the pins -> re-route
            row["action"] = ("re-route on main >= a804fc09b (pre-fix hold ECO put wires over the face pins)"
                             if row.get("f_fail") and row["hold_eco_pre_fix"] else
                             "ref_tile export re-export (check routed db: wires vs abstract)")
        rows.append(row)
    linted = [r for r in rows if r.get("lef")]
    bad = [r for r in linted if r.get("c_fail") or r.get("f_fail")]
    out = {"schema": "opentallas.hier_contract.blocked_pin_sweep_all.v1", "eco_fix": ECO_FIX, "eco_fix_at": ECO_FIX_AT,
           "selection": "every CLOSED record (closure-loop jobs + closed archive); check = child_lint (c) strap and "
                        "(f) blocked-above on the exported view LEF",
           "closed_records": len(rows), "linted": len(linted), "distinct_lefs": len(lint_cache),
           "no_lef": len(rows) - len(linted), "fail_c": sum(1 for r in linted if r.get("c_fail")),
           "fail_f": sum(1 for r in linted if r.get("f_fail")), "fail_any": len(bad),
           "used_fail": sum(1 for r in bad if r["used"]),
           "f_fail_hold_eco_pre_fix": sum(1 for r in bad if r.get("f_fail") and r["hold_eco_pre_fix"]),
           "f_fail_no_eco": sum(1 for r in bad if r.get("f_fail") and not r["hold_eco"]),
           "records": rows}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    for r in sorted(bad, key=lambda r: (not r["used"], r["element"] or "")):
        print(f"{'USED ' if r['used'] else '     '}{(r['element'] or '')[:30]:30s} {r['job'][:50]:50s} c={int(bool(r.get('c_fail')))} "
              f"f={r.get('blocked_above')}/{r.get('face_pin_rects')} eco={'pre' if r['hold_eco_pre_fix'] else int(r['hold_eco'])} "
              f"parent={','.join(r['parent'])[:60] or '-'}")
    print(f"closed {len(rows)}; linted {len(linted)} ({len(lint_cache)} distinct LEFs); fail (c) {out['fail_c']} "
          f"(f) {out['fail_f']}; used+fail {out['used_fail']}; (f) with pre-fix hold ECO {out['f_fail_hold_eco_pre_fix']}, "
          f"(f) without ECO {out['f_fail_no_eco']} -> {a.out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--archive", default=str(ARCHIVE))
    ap.add_argument("--jobs", default=str(Path.home() / ".local/state/closure_loop/jobs"))
    ap.add_argument("--out", default=str(REPO / "results/arch/hier_contract_1011/blocked_pin_sweep.json"))
    ap.add_argument("--all", action="store_true", help="every CLOSED record, child_lint (c)+(f) (see module doc)")
    ap.add_argument("--remote", action="store_true", help="--all: fetch the run's record/ LEF from its host when not local")
    a = ap.parse_args(argv)
    if a.all:
        if a.out.endswith("blocked_pin_sweep.json"):
            a.out = a.out.replace("blocked_pin_sweep.json", "blocked_pin_sweep_all.json")
        return main_all(a)
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
