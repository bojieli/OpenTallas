#!/usr/bin/env python3
"""hold_eco_internal_run.py -- the post-route INTERNAL-endpoint hold ECO as one command (HOLD-FLOW-R 11-16, QC-TYPES-R3 11-17).

A routed block that fails only FF hold on a few internal endpoints (the extraction after the pre-route repair moves short paths
by 1-17 ps while they keep hundreds of ps of TT setup) goes through: first sign-off -> endpoint dump (FF hold < 0 and TT setup of
every endpoint) -> hold_eco_internal.py plan (HB4 count per capture pin) -> insert (hold_eco_internal_insert.tcl) -> incremental
route of only the touched nets (hold_eco_internal_route.tcl) -> final sign-off.  Nothing is copied by hand: the liberty lists come
from the sign-off's own tt/libraries.json, the Tcl is read from this checkout read-only (docker -v ...:ro), the insert driver is
generated here, and every container runs as the calling user (no root-owned files).  The routed DB and the kit are never changed.

  hold_eco_internal_run.py --base RESULTS_BASE --kit KITDIR --name NAME --out OUTDIR [--first-signoff DIR] [--threads 8]
                           [--image openroad/orfs:asap7lock] [--sign-image openroad/orfs:latest] [--dry-run]

  RESULTS_BASE   <run>/results/<platform>/<design>/base holding 6_final.odb, else 5_route.odb (a GOAL=route kit)
  KITDIR         the kit (constraint.sdc, config.mk, macros) mounted as /work
  --first-signoff  an existing signoff.py output dir of this DB (with tt/ and ff/ session dumps); absent = run it here
Run it on a build host through ot-run (it starts docker); exit 0 = final sign-off SIGNED, 1 = not signed, 2 = nothing to do (no
endpoint below the plan's selection threshold), 3 = a step failed.  Result: OUTDIR/RESULT.json.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "# ---- KW-FIX-24 11-06: STD hold violators by startpoint kind"
FF_BLOCK = r'''set fh [open /out/ep_ff.tsv w]
puts $fh "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps"
foreach pe [find_timing_paths -path_delay min -slack_max 0 -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
  set e [get_property $pe endpoint]; set s [get_property $pe startpoint]
  set en [get_full_name $e]
  set sk [expr {[llength [get_ports -quiet [get_full_name $s]]] ? "port" : "reg"}]
  set ek [expr {[llength [get_ports -quiet $en]] ? "port" : "reg"}]
  puts $fh "$en\t[get_full_name $s]\t$sk\t$ek\t[so_ps [get_property $pe slack]]"
}
close $fh
'''
TT_BLOCK = r'''set fh [open /out/ep_tt.tsv w]
puts $fh "endpoint\ttt_setup_slack_ps"
foreach pe [find_timing_paths -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
  puts $fh "[get_full_name [get_property $pe endpoint]]\t[so_ps [get_property $pe slack]]"
}
close $fh
'''
DRV = '''foreach f [split [read [open /out/libs_std.txt r]] "\\n"] { if {$f ne ""} { read_liberty $f } }
read_db /in/6_final.odb
set ::env(OT_PRD_HOLD_PLAN) /out/plan.tsv
set ::env(RESULTS_DIR) /out
set blk [ord::get_db_block]
puts "DRV insts_before [llength [$blk getInsts]]"
source /ro/hold_eco_internal_insert.tcl
puts "DRV insts_after [llength [$blk getInsts]]"
if {[catch {check_placement -verbose} m]} { puts "DRV check_placement FAIL: $m" } else { puts "DRV check_placement OK" }
write_db /out/ins.odb
puts "DRV done"
exit
'''
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"


def libs_from_receipt(path):
    """(all liberty paths, the standard-cell ones) of a sign-off corner's libraries.json (the exact lists that corner was timed with)"""
    libs = [x["path"] for x in json.loads(Path(path).read_text())["libraries"]]
    if not libs:
        raise SystemExit("empty library list in %s" % path)
    return libs, [x for x in libs if x.startswith("/OpenROAD-flow-scripts/")]


def patch_session(text, corner):
    """the sign-off session plus the endpoint dump (FF: hold violators with their start kind; TT: setup of every endpoint)"""
    if text.count(MARK) != 1:
        raise SystemExit("sign-off session.tcl has no unique %r marker (signoff.py version mismatch)" % MARK)
    return text.replace(MARK, (FF_BLOCK if corner == "ff" else TT_BLOCK) + MARK)


def retarget_cmd(cmd, old_dir, new_dir, tag):
    """a sign-off corner's docker command re-pointed at a copy of its dump dir, with a fresh container name"""
    if old_dir + ":/out" not in cmd:
        raise SystemExit("cmd.sh does not mount %s:/out" % old_dir)
    out = cmd.replace(old_dir + ":/out", new_dir + ":/out")
    import re
    return re.sub(r"--name \S+", "--name " + tag, out, count=1)


def merge_endpoints(dump, out_tsv):
    tt = {}
    for i, line in enumerate((dump / "tt" / "ep_tt.tsv").read_text().splitlines()):
        p = line.split("\t")
        if i and len(p) == 2:
            try:
                tt[p[0]] = float(p[1]) * 1e-12
            except ValueError:
                pass
    rows = ["endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps"]
    n = 0
    for i, line in enumerate((dump / "ff" / "ep_ff.tsv").read_text().splitlines()):
        p = line.split("\t")
        if i and len(p) >= 5:
            rows.append("\t".join(p[:4]) + "\t%.3f\t%.3f" % (float(p[4]) * 1e-12, tt.get(p[0], 1e6)))
            n += 1
    out_tsv.write_text("\n".join(rows) + "\n")
    return n


def run(cmd, log=None, dry=False, **kw):
    print("+", " ".join(map(str, cmd)) if isinstance(cmd, list) else cmd, flush=True)
    if dry:
        return 0
    if log:
        with open(log, "w") as fh:
            return subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, **kw).returncode
    return subprocess.run(cmd, **kw).returncode


def signoff_cmd(rt, base, kit, name, out, image):
    return [sys.executable, "-I", str(rt / "tools/die_plan/signoff.py"), "run", "--base", str(base), "--kit", str(kit),
            "--sdc", str(kit / "constraint.sdc"), "--name", name, "--corners", "tt,ff", "--margin-policy", "nominal",
            "--image", image, "--docker", "docker", "--out", str(out)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--first-signoff")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--image", default="openroad/orfs:asap7lock")
    ap.add_argument("--sign-image", default="openroad/orfs:latest")
    ap.add_argument("--rt", default=str(HERE.parent.parent), help="checkout whose tools/die_plan is used (default: this one)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rt, base, kit, out = Path(a.rt), Path(a.base).resolve(), Path(a.kit).resolve(), Path(a.out).resolve()
    ro = rt / "tools/die_plan/post_route_drv"
    for need in (ro / "hold_eco_internal_insert.tcl", ro / "hold_eco_internal_route.tcl", rt / "tools/die_plan/hold_eco_internal.py"):
        if not need.is_file():
            raise SystemExit("missing %s" % need)
    routed = base / "6_final.odb"
    if not routed.is_file():
        routed = base / "5_route.odb"
    if not routed.is_file():
        raise SystemExit("no 6_final.odb / 5_route.odb in %s" % base)
    if out.exists() and any(out.iterdir()):
        raise SystemExit("%s exists and is not empty (never overwrite a previous ECO)" % out)
    user = ["-u", "%d:%d" % (os.getuid(), os.getgid())]
    dry = a.dry_run
    for d in ("in", "ins", "dump"):
        (out / d).mkdir(parents=True, exist_ok=True)
    res = {"base": str(base), "routed": str(routed), "kit": str(kit), "name": a.name, "steps": {}}

    def finish(code, why):
        res.update(exit=code, why=why)
        (out / "RESULT.json").write_text(json.dumps(res, indent=1) + "\n")
        print("RESULT", code, why)
        return code

    # 1. first sign-off (its tt/ff session dumps carry the exact libraries and the STA session the endpoints are read from)
    so1 = Path(a.first_signoff).resolve() if a.first_signoff else out / "so_first"
    if not a.first_signoff:
        env = dict(os.environ, OT_SIGNOFF_PROFILE="minimal")
        run(signoff_cmd(rt, base, kit, a.name, so1, a.sign_image), out / "so_first.log", dry, env=env, cwd=str(rt))
    for c in ("ff", "tt"):
        if not dry and not (so1 / c / "session.tcl").is_file():
            return finish(3, "first sign-off has no %s/session.tcl: %s" % (c, so1))
    libs_all, libs_std = ([], [])
    if not dry:
        libs_all, libs_std = libs_from_receipt(so1 / "tt" / "libraries.json")
        (out / "ins" / "libs.txt").write_text("\n".join(libs_all) + "\n")
        (out / "ins" / "libs_std.txt").write_text("\n".join(libs_std) + "\n")

    # 2. endpoint dump from the sign-off's own sessions
    procs = []
    for c in ("ff", "tt"):
        d = out / "dump" / c
        if not dry:
            shutil.copytree(so1 / c, d)
            (d / "session.tcl").write_text(patch_session((so1 / c / "session.tcl").read_text(), c))
            (d / "cmd.sh").write_text(retarget_cmd((so1 / c / "cmd.sh").read_text(), str(so1 / c), str(d), "hei_dump_%s_%d" % (c, os.getpid())))
            print("+ bash", d / "cmd.sh", flush=True)
            procs.append(subprocess.Popen(["bash", str(d / "cmd.sh")], stdout=open(d / "run.log", "w"), stderr=subprocess.STDOUT))
    if any(p.wait() for p in procs):
        return finish(3, "endpoint dump failed (dump/*/run.log)")
    if dry:
        return finish(0, "dry run")
    n = merge_endpoints(out / "dump", out / "hold_endpoints.tsv")
    res["steps"]["negative_hold_endpoints"] = n
    if run([sys.executable, "-I", str(rt / "tools/die_plan/hold_eco_internal.py"), "plan", str(out / "hold_endpoints.tsv"), str(out / "plan.tsv")],
           out / "plan.log"):
        return finish(3, "hold_eco_internal.py plan failed (plan.log)")
    rows = [ln for ln in (out / "plan.tsv").read_text().splitlines() if ln and not ln.startswith("#")]
    res["steps"]["plan_rows"] = len(rows)
    if not rows:
        return finish(2, "no endpoint selected by the plan (nothing to pad)")
    shutil.copy(routed, out / "in" / "6_final.odb")           # a copy: the routed DB itself is never opened for writing
    shutil.copy(out / "plan.tsv", out / "ins" / "plan.tsv")
    (out / "ins" / "drv.tcl").write_text(DRV)

    # 3. insert, 4. incremental route of the touched nets only
    common = ["docker", "run", "--rm"] + user
    if run(common + ["-v", "%s:/in:ro" % (out / "in"), "-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-v", "%s:/work:ro" % kit,
                     a.image, OPENROAD, "-no_init", "-exit", "/out/drv.tcl"], out / "ins" / "drv.log"):
        return finish(3, "insert failed (ins/drv.log)")
    if "DRV check_placement OK" not in (out / "ins" / "drv.log").read_text():
        return finish(3, "check_placement did not pass after the insert (ins/drv.log)")
    (out / "ins" / "route").mkdir(exist_ok=True)
    env = ["-e", "OT_HEI_IN=/out/ins.odb", "-e", "OT_HEI_CELLS=/out/hold_eco_internal_cells.tsv", "-e", "OT_HEI_OUT=/out/route",
           "-e", "OT_HEI_LIBS=/out/libs.txt", "-e", "OT_HEI_PG_DIR=/work", "-e", "OT_HEI_THREADS=%d" % a.threads]
    run(common + ["-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-v", "%s:/work:ro" % kit] + env
        + [a.image, OPENROAD, "-no_init", "-exit", "/ro/hold_eco_internal_route.tcl"], out / "ins" / "route.log")
    routed2 = out / "ins" / "route" / "hei_routed.odb"
    if not routed2.is_file() or "OT_HEI_ROUTE_DONE" not in (out / "ins" / "route.log").read_text():
        return finish(3, "incremental route failed (ins/route.log)")

    # 5. final sign-off on the re-routed DB
    sr = out / "so_run"
    b2 = sr / "results" / base.parent.parent.name / base.parent.name / "base"
    b2.mkdir(parents=True)
    (sr / "reports" / base.parent.parent.name / base.parent.name / "base").mkdir(parents=True)
    shutil.copy(kit / "config.mk", sr / "config.mk")
    shutil.copy(routed2, b2 / "6_final.odb")
    for f in base.iterdir():
        if f.is_file() and f.name in ("1_2_yosys.v", "6_final.v", "6_final.sdc", "clock_period.txt"):
            shutil.copy(f, b2 / f.name)
    shutil.copy(out / "ins" / "route" / "hei_drc.rpt", sr / "reports" / base.parent.parent.name / base.parent.name / "base" / "5_route_drc.rpt")
    env2 = dict(os.environ, OT_SIGNOFF_PROFILE="minimal")
    run(signoff_cmd(rt, b2, kit, a.name, out / "so_out", a.sign_image), out / "so.log", False, env=env2, cwd=str(rt))
    sj = out / "so_out" / "signoff.json"
    if not sj.is_file():
        return finish(3, "final sign-off wrote no signoff.json (so.log)")
    code = subprocess.run([sys.executable, "-I", str(rt / "tools/die_plan/signoff.py"), "verdict", str(sj)], capture_output=True).returncode
    res["final_routed_db"] = str(out / "so_run" / "results" / base.parent.parent.name / base.parent.name / "base" / "6_final.odb")
    return finish(0 if code == 0 else 1, "SIGNED" if code == 0 else "NOT SIGNED (so.log)")


if __name__ == "__main__":
    sys.exit(main())
