#!/usr/bin/env python3
"""Recover actual W10 routed abstracts into a new directory, without changing the run.

Default: preflight only. --extract reads the original ODB/SDC/SPEF read-only,
times SS/FF with each ROM's own libraries, and exports LEF and corner ETMs.
A POST_DONE marker is never evidence. This tool does not adopt or rebase a die.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from corner_sta import LIBS, PLAT


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def preflight(orfs, record, source_root):
    """Only source-pinned, complete final databases may be exported."""
    issues = []
    bases = sorted((orfs / "results/asap7").glob("*/base"))
    base = bases[0] if len(bases) == 1 else None
    if base is None:
        issues.append("expected exactly one ORFS result base")
    files = {}
    for name in ("6_final.odb", "6_final.sdc", "6_final.spef", "6_final.v"):
        p = base / name if base else None
        if p is None or not p.is_file() or p.stat().st_size == 0:
            issues.append(f"missing nonempty {name}")
        else:
            files[name] = dict(path=str(p), sha256=sha(p))
    if record.get("flow_completed") is not True:
        issues.append("route did not complete; terminal markers do not qualify")
    git = record.get("git", {})
    if git.get("worktree_dirty") is not False:
        issues.append("route source was dirty or cleanliness is unknown")
    head = subprocess.run(["git", "-C", str(source_root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()
    if git.get("commit") != head:
        issues.append("source worktree HEAD differs from route source pin")
    status = subprocess.run(["git", "-C", str(source_root), "status", "--porcelain",
                             "--untracked-files=no"], capture_output=True, text=True,
                            check=True).stdout
    if status.strip():
        issues.append("source worktree has tracked modifications")
    sources = record.get("design", {}).get("sources", [])
    if not sources:
        issues.append("route has no source hashes")
    checked = []
    for src in sources:
        p = source_root / src["path"]
        actual = sha(p) if p.is_file() else None
        match = actual is not None and actual == src.get("sha256")
        checked.append(dict(path=src["path"], expected=src.get("sha256"), actual=actual, matches=match))
        if not match:
            issues.append(f"source hash mismatch: {src['path']}")
    d = record.get("design", {})
    for field, expected in (("clock_uncertainty_ns", .06), ("clock_uncertainty_hold_ns", .025)):
        if d.get(field) != expected:
            issues.append(f"{field} does not match 60/25 ps policy")
    if record.get("target_clock_period_ns") != .833:
        issues.append("streaming target is not 0.833 ns")
    return dict(issues=issues, artifacts=files, sources=checked, source_commit=head), base


def timing(log, returncode):
    m = re.search(r"^OT_WS (\S+)", log, re.M)
    try:
        slack = float(m.group(1)) * 1e12 if m else None
    except ValueError:
        slack = None
    if slack is not None and not math.isfinite(slack):
        slack = None
    errors = re.findall(r"^.*\[ERROR[^\n]*", log, re.M)
    # Do not infer closure from a slack printed before a later Tcl/export error.
    complete = "OT_EXPORT_DONE" in log
    return dict(returncode=returncode, errors=errors, complete=complete,
                worst_slack_ps=slack,
                passes=returncode == 0 and not errors and complete and slack is not None and slack >= 0)


def tcl(corner, relbase, macros, name):
    # Paths and macro names are validated by main; no shell expansion is used.
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{x}" for x in LIBS[corner])
    mlibs = "\n".join(f"read_liberty /src/{m}/{Path(m).name}_{corner}.lib" for m in macros)
    check = "max" if corner == "ss" else "min"
    return f"""{libs}
{mlibs}
read_db /input/{relbase}/6_final.odb
read_sdc /input/{relbase}/6_final.sdc
read_spef /input/{relbase}/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd {check}]"
report_checks -path_delay {check} -group_path_count 5 -format full_clock_expanded
report_check_types -max_slew -max_capacitance -max_fanout -violators
write_timing_model -library_name {name}_{corner} /recovery/{name}_{corner}.lib
write_abstract_lef /recovery/{name}_{corner}.lef
puts "OT_EXPORT_DONE"
exit
"""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--route-record", type=Path, required=True)
    ap.add_argument("--source-root", type=Path, required=True)
    ap.add_argument("--macro", action="append", default=[])
    ap.add_argument("--name", required=True)
    ap.add_argument("--output-dir", type=Path, required=True, help="must not exist; evidence is immutable")
    ap.add_argument("--extract", action="store_true")
    ap.add_argument("--image", default="openroad/orfs:latest")
    a = ap.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a.name):
        ap.error("name must be a Verilog identifier")
    for m in a.macro:
        if not re.fullmatch(r"[A-Za-z0-9_/.-]+", m) or Path(m).is_absolute() or ".." in Path(m).parts:
            ap.error("macro must be a safe repo-relative path")
    orfs, src, out = a.orfs_dir.resolve(), a.source_root.resolve(), a.output_dir.resolve()
    if out == orfs or orfs in out.parents or out == src or src in out.parents:
        ap.error("output must be outside both the routed checkpoint and pinned source tree")
    out.mkdir(parents=True, exist_ok=False)
    record = json.loads(a.route_record.read_text())
    pf, base = preflight(orfs, record, src)
    if not a.macro:
        pf["issues"].append("W10 ROM macro corner views must be explicitly supplied")
    for m in a.macro:
        for suffix in ("ss.lib", "ff.lib", "lef"):
            p = src / m / f"{Path(m).name}_{suffix}" if suffix != "lef" else src / m / f"{Path(m).name}.lef"
            if not p.is_file():
                pf["issues"].append(f"missing macro view: {p}")
            else:
                pf.setdefault("macro_views", {})[str(p)] = sha(p)
    result = dict(schema="opentallas.w10_w18.actual_abstract_recovery.v1",
                  observed_at=datetime.now(timezone.utc).isoformat(),
                  tool_sha256=sha(__file__), route_record_sha256=sha(a.route_record),
                  preflight=pf, extracted=False, adopted=False, die_rebase_ready=False,
                  image=a.image, corners={},
                  remaining_gates=["same-source exactness and modeled measured latency",
                                   "ICG-to-ROM clock connectivity and power-pin accessibility",
                                   "hub routing-layer check and composed region/root SS/FF",
                                   "actual-element die route and IR stack"])
    if a.extract and not pf["issues"]:
        identity = subprocess.run(["docker", "image", "inspect", a.image, "--format", "{{.Id}}"],
                                  capture_output=True, text=True, check=True).stdout.strip()
        result["image_id"] = identity
        for corner in ("ss", "ff"):
            script = out / f"export_{corner}.tcl"
            script.write_text(tcl(corner, base.relative_to(orfs), a.macro, a.name))
            cmd = ["docker", "run", "--rm", "--cpus", "2", "--memory", "8g",
                   "-v", f"{orfs}:/input:ro", "-v", f"{src}:/src:ro",
                   "-v", f"{out}:/recovery", identity,
                   "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init",
                   "-threads", "2", "-exit", f"/recovery/{script.name}"]
            p = subprocess.run(cmd, capture_output=True, text=True)
            log = p.stdout + p.stderr
            (out / f"export_{corner}.log").write_text(log)
            result["corners"][corner] = timing(log, p.returncode)
        result["extracted"] = all((out / f"{a.name}_{c}.{ext}").is_file() and
                                  (out / f"{a.name}_{c}.{ext}").stat().st_size > 0
                                  for c in ("ss", "ff") for ext in ("lef", "lib"))
    result["element_timing_passes"] = bool(result["extracted"] and
                                           all(x["passes"] for x in result["corners"].values()))
    result["physically_clean_route"] = record.get("status") == "pass" and record.get("design", {}).get("closed") is True
    result["status"] = ("BLOCKED_INPUTS" if pf["issues"] else
                        "RECOVERED_CANDIDATE_ONLY" if result["extracted"] else "PREFLIGHT_ONLY")
    result["output_hashes"] = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
    (out / "recovery.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("status", "extracted", "element_timing_passes", "die_rebase_ready")}))
    return 1 if pf["issues"] or (a.extract and not result["extracted"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
