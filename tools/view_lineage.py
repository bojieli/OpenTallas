#!/usr/bin/env python3
"""Receipt-backed lineage for views that were NOT written by their closure-loop job's own export (ROOT 2026-10-16).

Die binders (tools/s81/view_binding_closed.py, the native pin audit) bind a view through the closure-loop job that
exported it (abstract.json orfs_dir -> /closure-loop/<job>/).  Two supported cases have no such job of their own:

  archive_reexport   the view was re-exported strictly from the CLOSED job's archived routed ODB (closed archive; no
                     re-route): abstract.json verdict.job names the CLOSED job, verdict.check replays its verdict.
  scalar_pin_rename  a derived copy of a CLOSED view in which recipe-3 pin-register exports named scalar RTL ports x[0]
                     (ot_pin_regs.tcl before e3919f90e) and the copy renames them x; geometry and arcs are unchanged.

`write` builds VIEW/view_lineage.json only when every gate passes; `verify` re-checks a receipt against the files on disk
(binders call verify(); any drift = not bound).  Gates:
  closed   the original job's loop state is CLOSED with TT >= 0, FF >= 0, DRC 0 (job state sha256 pinned)
  export   archive_reexport: verdict.check tt/ff ok and the four view files are the ones abstract.json recorded;
           scalar_pin_rename: the parent view passes its own gates and every file maps back to the parent's bytes
  native   tools/hier_contract/native_pin_audit.audit_one on this view: launch/capture/spread/comb numbers recorded
           (scalar_pin_rename: identical to the parent's numbers)
  files    sha256 of LEF + TT/FF/SS liberty + abstract.json pinned in the receipt

  view_lineage.py write archive-reexport VIEW_DIR --archive CLOSED_ARCHIVE_JOB_DIR
  view_lineage.py verify VIEW_DIR
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JOBS = Path.home() / ".local/state/closure_loop/jobs"
SCHEMA = "opentallas.view_lineage.v1"
RECEIPT = "view_lineage.json"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def view_files(d: Path, master: str) -> dict:
    out = {}
    for f in [f"{master}.lef", f"{master}_tt.lib", f"{master}_ff.lib", f"{master}_ss.lib", "abstract.json", "insertion.json"]:
        p = d / f
        if p.is_file():
            out[f] = sha(p)
    return out


def closed_job(job: str, jobs: Path = JOBS) -> tuple[bool, str, dict]:
    p = jobs / f"{job}.json"
    if not p.is_file():
        return False, f"no closure-loop job state for {job}", {}
    jd = json.loads(p.read_text())
    reason = jd.get("reason") or ""
    tt = re.search(r"TT \+?(-?[\d.]+)", reason)
    ff = re.search(r"FF \+?(-?[\d.]+)", reason)
    drc = re.search(r"DRC (\d+)", reason)
    info = dict(job=job, status=jd.get("status"), reason=reason[:200], state_sha256=sha(p))
    if jd.get("status") != "CLOSED":
        return False, f"job {job} status {jd.get('status')}", info
    if not (tt and ff and drc) or float(tt.group(1)) < 0 or float(ff.group(1)) < 0 or int(drc.group(1)) != 0:
        return False, f"job {job} verdict not TT>=0/FF>=0/DRC0: {reason[:80]}", info
    return True, "CLOSED", info


def native(d: Path, master: str) -> dict:
    sys.path.insert(0, str(ROOT / "tools/hier_contract"))
    import native_pin_audit as NPA
    r = NPA.audit_one((str(d), master, "."))
    keep = ("pass", "fail_why", "R_ps", "spread_ps", "launch_ps", "launch_pin", "capture_ps", "capture_pin",
            "launch_over", "capture_over", "comb_pins", "outputs", "inputs", "error")
    return {k: r.get(k) for k in keep if k in r}


def export_gate(d: Path, master: str, ab: dict) -> tuple[bool, str]:
    v = ab.get("verdict") if isinstance(ab.get("verdict"), dict) else {}
    chk = v.get("check") or {}
    bad = [c for c in ("tt", "ff") if not (chk.get(c) or {}).get("ok")]
    if not chk or bad or not ab.get("ok"):
        return False, f"verdict replay not ok ({bad or 'no verdict.check / record ok=false'})"
    for f in [f"{master}.lef"] + [f"{master}_{c}.lib" for c in ("tt", "ff", "ss")]:
        if not (d / f).is_file() or (ab.get("files") or {}).get(f) != sha(d / f):
            return False, f"{f} on disk is not the file the verdict-replay export recorded"
    return True, "verdict replay ok (TT %s / FF %s ps)" % (chk["tt"].get("export_ps"), chk["ff"].get("export_ps"))


def archive_gate(archive: Path | None, job: str, commit: str) -> dict:
    """Authenticate replay inputs against the immutable closed archive, including raw compressed bytes."""
    if archive is None:
        raise ValueError("closed archive required")
    man = archive / "manifest.json"
    m = json.loads(man.read_text())
    if m.get("job") != job or m.get("commit") != commit or (archive / "commit.txt").read_text().strip() != commit:
        raise ValueError("archive job/source commit mismatch")
    metrics = m.get("metrics") or {}
    if metrics.get("tt_ps", -1) < 0 or metrics.get("ff_ps", -1) < 0 or metrics.get("drc") != 0:
        raise ValueError("archive does not attest TT>=0/FF>=0/DRC0")
    required = [m["final_base"] + "/6_final." + ext for ext in ("odb", "sdc", "spef")]
    entries = {f["path"]: f for f in m["files"]}
    verified = {}
    for rel in required:
        f = entries.get(rel) or {}
        if not re.fullmatch(r"[0-9a-f]{64}", f.get("sha256", "")):
            raise ValueError(f"archive missing raw hash: {rel}")
        p = (archive / "run" / f["stored"]).resolve()
        if not p.is_relative_to((archive / "run").resolve()):
            raise ValueError("archive file escapes run directory")
        if f.get("compression") == "zstd":
            raw = subprocess.run(["zstd", "-dc", str(p)], capture_output=True, check=True).stdout
        elif not f.get("compression"):
            raw = p.read_bytes()
        else:
            raise ValueError("unsupported archive compression")
        if len(raw) != f.get("raw_size") or hashlib.sha256(raw).hexdigest() != f["sha256"]:
            raise ValueError(f"archive bytes changed: {rel}")
        verified[rel] = f["sha256"]
    return dict(path=str(archive), manifest_sha256=sha(man), commit=commit, replay_inputs=verified)


def build_archive_reexport(d: Path, archive: Path | None, jobs: Path = JOBS) -> dict:
    master = d.name
    ab = json.loads((d / "abstract.json").read_text())
    v = ab.get("verdict") if isinstance(ab.get("verdict"), dict) else {}
    job = v.get("job")
    why = []
    if not job:
        why.append("abstract.json verdict.job missing (not a job-replay export)")
    ok_c, txt_c, info = closed_job(job, jobs) if job else (False, "no job", {})
    if not ok_c:
        why.append(txt_c)
    ok_e, txt_e = export_gate(d, master, ab)
    if not ok_e:
        why.append(txt_e)
    arch = None
    try:
        arch = archive_gate(archive, job, v.get("commit"))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
        why.append(f"archive provenance: {e}")
    if not (d / "insertion.json").is_file():
        why.append("insertion.json missing")
    nat = native(d, master)
    if not nat.get("pass"):
        why.append(f"native audit: {nat.get('fail_why') or nat.get('error')}")
    return dict(schema=SCHEMA, kind="archive_reexport", master=master, view=str(d.relative_to(ROOT)) if d.is_relative_to(ROOT) else str(d),
                original_job=job, closed=info, export_check=dict(ok=ok_e, why=txt_e, verdict_commit=v.get("commit")),
                archive=arch, native_audit=nat, files=view_files(d, master),
                verdict="PASS" if not why else "FAIL", why=why,
                rule="archive re-export of a CLOSED job's routed ODB, no re-route: binds through original_job")


def verify(d: Path, jobs: Path = JOBS) -> tuple[bool, str, dict]:
    """(ok, why, receipt): the receipt exists, PASSed, its files are the files on disk and its job is still CLOSED"""
    p = d / RECEIPT
    if not p.is_file():
        return False, f"no {RECEIPT}", {}
    r = json.loads(p.read_text())
    if r.get("schema") != SCHEMA or r.get("verdict") != "PASS":
        return False, f"{RECEIPT} not a PASS {SCHEMA} receipt", r
    now = view_files(d, r.get("master") or d.name)
    if now != r.get("files"):
        return False, f"{RECEIPT}: view files changed since the receipt", r
    ok, txt, current = closed_job(r.get("original_job") or "", jobs)
    if not ok:
        return False, f"{RECEIPT}: {txt}", r
    if current.get("state_sha256") != (r.get("closed") or {}).get("state_sha256"):
        return False, f"{RECEIPT}: CLOSED job state changed since receipt", r
    if r.get("kind") == "archive_reexport":
        try:
            old = r.get("archive") or {}
            now_archive = archive_gate(Path(old["path"]), r["original_job"], r["export_check"]["verdict_commit"])
            if now_archive != old:
                raise ValueError("archive receipt differs from verified replay inputs")
        except (OSError, ValueError, KeyError, subprocess.SubprocessError) as e:
            return False, f"{RECEIPT}: archive provenance: {e}", r
    elif r.get("kind") != "scalar_pin_rename":
        return False, f"{RECEIPT}: unsupported lineage kind", r
    if r.get("kind") == "scalar_pin_rename":
        par = ROOT / (r.get("parent_view") or "")
        if not par.is_dir():
            return False, f"{RECEIPT}: parent view {r.get('parent_view')} missing", r
        pf = view_files(par, r.get("master") or d.name)
        if pf != r.get("parent_files"):
            return False, f"{RECEIPT}: parent view files changed since the receipt", r
    return True, f"{r.get('kind')} of CLOSED {r.get('original_job')}", r


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("write")
    w.add_argument("kind", choices=["archive-reexport"])
    w.add_argument("view")
    w.add_argument("--archive", help="closed archive job dir (…/closed_archive/<master>/<job>)")
    w.add_argument("--jobs", default=str(JOBS))
    v = sub.add_parser("verify")
    v.add_argument("view")
    v.add_argument("--jobs", default=str(JOBS))
    a = ap.parse_args(argv)
    d = Path(a.view).resolve()
    if a.cmd == "verify":
        ok, why, _ = verify(d, Path(a.jobs))
        print(("PASS " if ok else "FAIL ") + why)
        return 0 if ok else 1
    r = build_archive_reexport(d, Path(a.archive) if a.archive else None, Path(a.jobs))
    print(json.dumps({k: r[k] for k in ("master", "original_job", "verdict", "why")}))
    if r["verdict"] != "PASS":
        return 1
    (d / RECEIPT).write_text(json.dumps(r, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
