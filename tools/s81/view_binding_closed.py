#!/usr/bin/env python3
"""S81 die: bind every CLOSED exported view by master name (S-DIE 2026-10-16, ROOT 23:55: bind closed views in the trial).

Scans physical/ref_tile/*/views/<master>/abstract.json (the closure loop's record of one export: routed LEF + TT/FF/SS
ETM written from the closing ORFS run).  A master binds when ALL hold, read from the closure-loop job state of the
export's job (~/.local/state/closure_loop/jobs/<job>.json):

  closed   job status CLOSED, its verdict reason states TT setup >= 0, FF hold >= 0 and DRC 0
  export   every corner export returned 0 and the four files exist (sha256 pinned in the table)
  lint     child_lint has no fails (when the job ran it)
  bench    no expect-pass bench failed and no expect-fail bench passed
  current  the job is the latest CLOSED export of that master (newest finished_at); older views are listed, not bound

POST-STUB LINEAGE (--poststub-same-commit, S-DIE 0030 10-16): the closure loop's child-lint gate rewrites the exported LEF in
place with tools/hier_contract/abstract_pin_stub.py AFTER the export recorded its hashes (closure_loop.py pin_stub_fix), so
the LEF on disk legitimately differs from abstract.json's raw record.  Such a master binds (lineage POSTSTUB_SAME_COMMIT,
still DIAGNOSTIC_CLOSED) only when every other gate passes AND: the three corner libs ARE the recorded files, the LEF,
the libs and abstract.json were last written by ONE git commit (one export bundle, never a newer LEF over an older
record), the LEF is a fixed point of abstract_pin_stub (it is the post-processed form) and its MACRO / signal pin set
equals the TT liberty's cell / pin set.  Exact raw-replay recovery (export_manifest_0010) supersedes this lineage.

It never relaxes a gate: native launch/capture/spread audits and production-throughput qualification stay owed per tile
and are listed as open in the table ('native_open'). Rows use DIAGNOSTIC_CLOSED and require
OT_S81_DIAGNOSTIC_CLOSED_VIEWS=1, so a trial cannot promote them to native QUALIFIED.  The generator still refuses any binding whose pins / outline /
orientation do not fit the die (tools/dsrom_s81_fulldie.py apply_view_binding); with OT_S81_VIEW_BINDING_SKIP_MISFIT=1 a
pathfinding trial records such masters as misfits (pushed to their owners) instead of stopping.

  view_binding_closed.py --out results/arch/s81_native_20261013/view_binding_closed_<tag>.json
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import re
import subprocess
import sys
from view_binding import export_fix
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
JOBS = Path.home() / ".local/state/closure_loop/jobs"
SCHEMA = "s81-view-binding-v1"
S81 = re.compile(r"^(dsfd_|ot_s81|s81_)")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def job_of(abstract: dict) -> str | None:
    m = re.search(r"/closure-loop/([^/]+)/", abstract.get("orfs_dir", ""))
    return m.group(1) if m else None


def verdict_ok(reason: str):
    tt = re.search(r"TT \+?(-?[\d.]+)", reason or "")
    ff = re.search(r"FF \+?(-?[\d.]+)", reason or "")
    drc = re.search(r"DRC (\d+)", reason or "")
    if not (tt and ff and drc):
        return False, "verdict reason lacks TT/FF/DRC"
    t, f, d = float(tt.group(1)), float(ff.group(1)), int(drc.group(1))
    if t < 0 or f < 0 or d != 0:
        return False, f"TT {t} / FF {f} / DRC {d}"
    return True, f"TT +{t} / FF +{f} / DRC 0"


_LAST = None


def last_commits(paths):
    """{path: commit sha} of the last commit that wrote each view file (one git log over physical/ref_tile views)"""
    global _LAST
    if _LAST is None:
        _LAST = {}
        out = subprocess.run(["git", "-C", str(ROOT), "log", "--format=C %H", "--name-only", "--",
                              "physical/ref_tile/*/views/*/abstract.json", "physical/ref_tile/*/views/*/*.lef",
                              "physical/ref_tile/*/views/*/*.lib"], capture_output=True, text=True, check=True).stdout
        cur = None
        for ln in out.split("\n"):
            if ln.startswith("C "):
                cur = ln[2:].strip()
            elif ln and ln not in _LAST:
                _LAST[ln] = cur
    return [_LAST.get(p) for p in paths]


def poststub_lineage(master, d: Path, rec: dict):
    """(ok, why) of the POST-STUB lineage for an export whose only export_fix fault is the LEF hash"""
    sys.path.insert(0, str(ROOT / "tools/hier_contract"))
    import abstract_pin_stub as aps
    rel = d.relative_to(ROOT)
    files = rec.get("files") or {}
    for c in ("tt", "ff", "ss"):
        f = d / f"{master}_{c}.lib"
        if files.get(f.name) != sha(f):
            return False, f"{f.name} is not the recorded file"
    cs = last_commits([f"{rel}/abstract.json", f"{rel}/{master}.lef"] + [f"{rel}/{master}_{c}.lib" for c in ("tt", "ff", "ss")])
    if None in cs or len(set(cs)) != 1:
        return False, f"view files last written by different commits {sorted(set(map(str, cs)))[:3]}"
    lef = (d / f"{master}.lef").read_text()
    try:
        out, _msg = aps.process(lef)
    except Exception as e:  # noqa: BLE001
        return False, f"abstract_pin_stub failed on the LEF: {e}"
    if out != lef:
        return False, "LEF is not a fixed point of abstract_pin_stub (not the post-processed export)"
    macros = re.findall(r"^MACRO (\S+)", lef, re.M)
    if macros != [master]:
        return False, f"LEF MACRO {macros}"
    lpins = set()
    for pm in re.finditer(r"\n\s*PIN (\S+)\s*\n(.*?)\n\s*END \1", lef, re.S):
        if not re.search(r"USE\s+(POWER|GROUND)", pm.group(2)):
            lpins.add(pm.group(1))
    lib = (d / f"{master}_tt.lib").read_text(errors="ignore")
    if not re.search(r"^\s*cell\s*\(\s*\"?" + re.escape(master) + r"\"?\s*\)", lib, re.M):
        return False, "TT liberty has no cell of the master"
    bus = {}
    for bm in re.finditer(r"^\s*bus\s*\(\s*\"?(\S+?)\"?\s*\)\s*\{(.*?)\n\s*bus_type\s*:\s*\"?(\S+?)\"?\s*;", lib, re.M | re.S):
        bus[bm.group(1)] = bm.group(3)
    tpins = set(re.findall(r"^\s*pin\s*\(\s*\"?([^\s\"\)]+)\"?\s*\)", lib, re.M))
    types = {tm.group(1): (int(tm.group(2)), int(tm.group(3))) for tm in re.finditer(
        r"type\s*\(\s*\"?(\S+?)\"?\s*\)\s*\{[^}]*?bit_from\s*:\s*(\d+)\s*;[^}]*?bit_to\s*:\s*(\d+)\s*;", lib, re.S)}
    for b, ty in bus.items():
        if ty in types:
            lo, hi = sorted(types[ty])
            tpins |= {f"{b}[{i}]" for i in range(lo, hi + 1)}
    tpins = {p.replace("\\", "") for p in tpins}
    miss = sorted(lpins - tpins)
    if miss:
        return False, f"{len(miss)} LEF signal pins absent from the TT liberty, e.g. {miss[:3]}"
    return True, "POSTSTUB_SAME_COMMIT " + cs[0][:12]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    ap.add_argument("--jobs", default=str(JOBS))
    ap.add_argument("--poststub-same-commit", action="store_true",
                    help="accept the closure loop's in-place abstract_pin_stub LEF rewrite under the POST-STUB lineage rules")
    ap.add_argument("--exclude-master", action="append", default=[], help="Known functional/native defect: do not bind this master even diagnostically")
    a = ap.parse_args()
    cands = {}
    rejected = {}
    for ab in sorted(glob.glob(str(ROOT / "physical/ref_tile/*/views/*/abstract.json"))):
        ab = Path(ab)
        d = ab.parent
        master = d.name
        if not S81.match(master) or master in a.exclude_master:
            continue
        rel = d.relative_to(ROOT)
        try:
            rec = json.loads(ab.read_text())
        except Exception as e:  # noqa: BLE001
            rejected.setdefault(master, []).append(dict(export_dir=str(rel), why=f"abstract.json unreadable: {e}"))
            continue
        job = job_of(rec)
        why = []
        js = Path(a.jobs) / f"{job}.json" if job else None
        jd = json.loads(js.read_text()) if js and js.exists() else None
        if jd is None:
            why.append(f"no closure-loop job state for {job}")
        else:
            if jd.get("status") != "CLOSED":
                why.append(f"job status {jd.get('status')}")
            ok, txt = verdict_ok(jd.get("reason", ""))
            if not ok:
                why.append(txt)
            cl = jd.get("child_lint") or {}
            if cl.get("fails"):
                why.append(f"child_lint fails {cl['fails'][:3]}")
            for bn, b in (jd.get("benches") or {}).items():
                if not isinstance(b, dict) or "ok" not in b:
                    continue
                if not b.get("ok"):
                    why.append(f"bench {bn} not as expected ({b.get('expect')})")
        # Reuse the strict export identity gate: all bound ETMs must replay
        # their verdict SDC and match the files recorded by that export.
        ok_export, export_why = export_fix(dict(master=master, export_dir=str(rel)))
        lineage = "EXACT_EXPORT"
        if not ok_export and a.poststub_same_commit and export_why == f"{master}.lef on disk is not the file the verdict-replay export recorded":
            ok_ps, ps_why = poststub_lineage(master, d, rec)
            if ok_ps:
                ok_export, lineage = True, ps_why
            else:
                export_why += f"; post-stub lineage refused: {ps_why}"
        if not ok_export:
            why.append(export_why)
        files = {}
        for k, suf in (("lef", ".lef"), ("tt", "_tt.lib"), ("ff", "_ff.lib"), ("ss", "_ss.lib")):
            p = d / f"{master}{suf}"
            if not p.is_file():
                why.append(f"{k} file missing")
            else:
                files[k] = dict(path=str(p.relative_to(ROOT)), sha256=sha(p))
        for c, cr in (rec.get("corners") or {}).items():
            if cr.get("returncode") not in (0, None) or cr.get("done") is False:
                why.append(f"export {c} rc {cr.get('returncode')}")
        entry = dict(export_dir=str(rel), job=job, files=files, lineage=lineage,
                     finished_at=(jd or {}).get("finished_at") or (jd or {}).get("updated"),
                     closure=verdict_ok((jd or {}).get("reason", ""))[1])
        if why:
            rejected.setdefault(master, []).append(dict(entry, why=why))
        else:
            cands.setdefault(master, []).append(entry)
    bound, superseded = {}, {}
    for master, es in cands.items():
        es.sort(key=lambda e: str(e.get("finished_at") or ""), reverse=True)
        best = es[0]
        bound[master] = dict(verdict="DIAGNOSTIC_CLOSED", export_dir=best["export_dir"], job=best["job"], files=best["files"],
                             closure=best["closure"], lineage=best.get("lineage", "EXACT_EXPORT"), gate="closed+export+lint+bench+current (view_binding_closed.py)",
                             native_open="tile native launch/capture/spread audit and production-throughput bench stay "
                                         "with the tile owner; this binding is the die-context view, not qualification")
        if len(es) > 1:
            superseded[master] = [e["export_dir"] for e in es[1:]]
    out = dict(schema=SCHEMA, rule=__doc__.split("\n\n")[1].strip(), builder="tools/s81/view_binding_closed.py",
               bound=dict(sorted(bound.items())), superseded=superseded,
               excluded_masters=sorted(a.exclude_master),
               scope="CLOSED_ROUTE_DIAGNOSTIC_ONLY_NOT_NATIVE_QUALIFICATION",
               not_bound={k: v for k, v in sorted(rejected.items()) if k not in bound})
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(bound=len(bound), not_bound=len(out["not_bound"]), superseded=len(superseded))))


if __name__ == "__main__":
    main()
