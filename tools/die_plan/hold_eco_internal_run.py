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
endpoint below the plan's selection threshold), 3 = a step failed, 4 = REFUSED by a limit (nothing was signed).
Result: OUTDIR/RESULT.json.

LIMITS (FABLE-CLOSURE-STRATEGY 11-17 lever 8: the ECO is for a few small near-misses, never a way to buy a bigger hold hole; it is the
automatic fallback after a routed FF-hold FAIL only inside these):
  worst internal FF hold >= -15 ps            (--max-worst-ps 15; port-start / port-end endpoints are the parent's and never count)
  padded ends <= 100                          (--max-ends 100)
  setup room on every padded end              (TT setup - n x HB4_TT_MAX_PS >= --min-setup-room-ps, default 0; no partial / skipped pad)
  no clock or port nets                       (every capture pin sits on an ordinary data net with no port: checked on the DB before the insert)
  no PG obstructions left in the DB           (the block's obstruction count after the route must equal the input DB's: the route step's
                                               temporary PG-track obstructions must all be gone)
A violation prints OT_LIMIT <name> ..., is written to RESULT.json and the exit code is 4.
"""
import math
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MARK = "# ---- KW-FIX-24 11-06: STD hold violators by startpoint kind"
FF_BLOCK = r'''proc so_ep_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f $t] }
set fh [open /out/ep_ff.tsv w]
puts $fh "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps"
foreach pe [find_timing_paths -path_delay min -slack_max 0 -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
  set e [get_property $pe endpoint]; set s [get_property $pe startpoint]
  set en [get_full_name $e]
  set sk [expr {[llength [get_ports -quiet [get_full_name $s]]] ? "port" : "reg"}]
  set ek [expr {[llength [get_ports -quiet $en]] ? "port" : "reg"}]
  puts $fh "$en\t[get_full_name $s]\t$sk\t$ek\t[so_ep_ps [get_property $pe slack]]"
}
close $fh
'''
TT_BLOCK = r'''proc so_ep_ps {t} { if {$t eq "" || [regexp -nocase {inf|nan} $t]} { return "nan" }; return [format %.2f $t] }
set fh [open /out/ep_tt.tsv w]
puts $fh "endpoint\ttt_setup_slack_ps"
foreach pe [find_timing_paths -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack] {
  puts $fh "[get_full_name [get_property $pe endpoint]]\t[so_ep_ps [get_property $pe slack]]"
}
close $fh
'''
DRV = '''foreach f [split [read [open /out/libs_std.txt r]] "\\n"] { if {$f ne ""} { read_liberty $f } }
read_db /in/6_final.odb
set ::env(OT_PRD_HOLD_PLAN) /out/plan.tsv
set ::env(RESULTS_DIR) /out
set blk [ord::get_db_block]
puts "DRV insts_before [llength [$blk getInsts]]"
source /out/netcheck.tcl
source /ro/hold_eco_internal_insert.tcl
puts "DRV insts_after [llength [$blk getInsts]]"
if {[catch {check_placement -verbose} m]} { puts "DRV check_placement FAIL: $m" } else { puts "DRV check_placement OK" }
write_db /out/ins.odb
puts "DRV done"
exit
'''
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
OBS = "read_db $::env(OBS_ODB)\nputs \"LIM obstructions [llength [[ord::get_db_block] getObstructions]]\"\nexit\n"
NETCHECK = r"""foreach row [split [read [open /out/plan.tsv r]] "\n"] {
  if {$row eq "" || [string index $row 0] eq "#"} continue
  lassign [split $row "\t"] pin n
  set p [get_pins -quiet $pin]
  if {[llength $p] != 1} { puts "OT_LIMIT unresolved capture pin $pin"; continue }
  set it [sta::sta_to_db_pin $p]; set net [$it getNet]
  if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} { puts "OT_LIMIT non-data net on $pin"; continue }
  if {[llength [$net getBTerms]]} { puts "OT_LIMIT port net on $pin"; continue }
  if {[[$it getMTerm] getName] in {CLK CLKN CK CKN}} { puts "OT_LIMIT clock pin $pin" }
}
"""


def check_limits(endpoints_tsv, plan_tsv, max_worst_ps=15.0, max_ends=100, min_room_ps=0.0, hb4_tt_ps=None):
    """pure: the violations (strings; empty = inside the limits) of a planned ECO.  endpoints_tsv is hold_endpoints.tsv (header line;
    ff_hold_slack_ps and tt_setup_slack_ps in ps), plan_tsv the hold_eco_internal.py plan (capture_pin TAB n_hb4 + a summary trailer)."""
    if hb4_tt_ps is None:
        sys.path.insert(0, str(HERE))
        import hold_eco_internal as HEI
        hb4_tt_ps = HEI.HB4_TT_MAX_PS
    viol, setup, worst = [], {}, None
    for i, line in enumerate(Path(endpoints_tsv).read_text().splitlines()):
        p = line.split("\t")
        if not i or len(p) < 6:
            continue
        ff, tt = float(p[4]), float(p[5])
        setup[p[0]] = tt
        if p[2] != "port" and p[3] != "port":
            worst = ff if worst is None else min(worst, ff)
    if worst is not None and worst < -abs(max_worst_ps):
        viol.append("worst_internal_ff_hold %.2f ps < -%g" % (worst, abs(max_worst_ps)))
    rows, summary, skipped_internal = [], {}, []
    for line in Path(plan_tsv).read_text().splitlines():
        if line.startswith("# summary"):
            summary = json.loads(line[len("# summary"):])
        elif line.startswith("# skipped "):
            # "# skipped <endpoint>: <reason>".  A port path (start or end at a port) is the parent's: advisory under R-MINIMAL, never padded and
            # never a limit (S81 col_pg3 had 110 of them and exited 4); only an INTERNAL end the plan could not pad counts.
            end, _, why = line[len("# skipped "):].partition(": ")
            if not why.startswith("port path"):
                skipped_internal.append((end, why))
        elif line and not line.startswith("#"):
            rows.append(line.split("\t"))
    if len(rows) > max_ends:
        viol.append("padded_ends %d > %d" % (len(rows), max_ends))
    for pin, n in rows:
        room = setup.get(pin, 1e6) - int(n) * hb4_tt_ps
        if room < min_room_ps:
            viol.append("setup_room %s %.1f ps < %g (TT setup %.1f, %s x %.1f)" % (pin, room, min_room_ps, setup.get(pin, 1e6), n, hb4_tt_ps))
    for end, why in skipped_internal:
        viol.append("internal end not padded: %s (%s)" % (end, why))
    if summary.get("partial") or summary.get("nets_left_unpadded"):
        viol.append("plan could not pad every internal end (partial %s unpadded %s)" % (summary.get("partial"), summary.get("nets_left_unpadded")))
    return viol


def libs_from_receipt(path):
    """(all liberty paths, the standard-cell ones) of a sign-off corner's libraries.json (the exact lists that corner was timed with)"""
    libs = [x["path"] for x in json.loads(Path(path).read_text())["libraries"]]
    if not libs:
        raise SystemExit("empty library list in %s" % path)
    # NOMCAP-1118 r708: /nomcap/ = the sign-off's nominal-clock-pin-cap copies of the stock INVBUF/SEQ libraries.
    # A kit-local sign-off writes those copies inside the kit (/work/nomcap/, the kit is mounted at /work in every container
    # of this tool): they are the same standard cells (INVBUF holds HB4), so they belong to the std list too (t49 11-21:
    # dropping them left 0 HB4 masters, "HB4 source is not unique").
    return libs, [x for x in libs if x.startswith(("/OpenROAD-flow-scripts/", "/nomcap/", "/work/nomcap/"))]


def nomcap_mount(cmd_sh):
    """the sign-off corner's /nomcap mount (r708 liberty copies), reused by every container that reads its libraries"""
    m = re.search(r"-v (\S+):/nomcap:ro", Path(cmd_sh).read_text()) if Path(cmd_sh).is_file() else None
    return ["-v", "%s:/nomcap:ro" % m.group(1)] if m else []


def patch_session(text, corner):
    """the sign-off session plus the endpoint dump (FF: hold violators with their start kind; TT: setup of every endpoint)"""
    if text.count(MARK) != 1:
        raise SystemExit("sign-off session.tcl has no unique %r marker (signoff.py version mismatch)" % MARK)
    if "/out/ep_%s.tsv" % corner in text:
        return text                      # ROUTE-LOSS 11-18: a current signoff.py writes the table itself (signoff.ep_dump_tcl)
    return text.replace(MARK, (FF_BLOCK if corner == "ff" else TT_BLOCK) + MARK)


def native_tables(so):
    """ROUTE-LOSS 11-18: True when the sign-off dir already holds both endpoint tables of its own sessions (ff/ep_ff.tsv, tt/ep_tt.tsv,
    each newer than its sta.log start = written by that session), so the two dump sessions are not run again"""
    so = Path(so)
    for c in ("ff", "tt"):
        f = so / c / ("ep_%s.tsv" % c)
        try:
            if not f.is_file() or len(f.read_text().splitlines()) < 1 or "SO EP_DUMP %s " % c not in (so / c / "sta.log").read_text(errors="replace"):
                return False
        except OSError:
            return False
    return True


def retarget_cmd(cmd, old_dir, new_dir, tag):
    """a sign-off corner's docker command re-pointed at a copy of its dump dir, with a fresh container name"""
    if old_dir + ":/out" not in cmd:
        raise SystemExit("cmd.sh does not mount %s:/out" % old_dir)
    out = cmd.replace(old_dir + ":/out", new_dir + ":/out")
    import re
    return re.sub(r"--name \S+", "--name " + tag, out, count=1)


EP_LEGACY_SCALE_ABOVE = 1e6     # a table holding any |value| above this is a pre-EP-PS-UNIT one (ps x 1e12)


def ep_scale(values):
    """1e-12 for a legacy endpoint table (slack printed through so_ps twice: ps x 1e12), else 1.0 (real ps).  Per file: a
    real ps table never holds 1e6 ps, a legacy one holds |slack| x 1e12 on every row with |slack| >= 1e-6 ps."""
    return 1e-12 if any(math.isfinite(v) and abs(v) > EP_LEGACY_SCALE_ABOVE for v in values) else 1.0


def _ep_rows(path, nfield):
    out = []
    for i, line in enumerate(path.read_text().splitlines()):
        p = line.split("\t")
        if i and len(p) >= nfield:
            try:
                out.append((p, float(p[nfield - 1])))
            except ValueError:
                pass
    return out


def merge_endpoints(dump, out_tsv):
    ttr = [(p, v) for p, v in _ep_rows(dump / "tt" / "ep_tt.tsv", 2) if len(p) == 2]
    k = ep_scale([v for _p, v in ttr])
    tt = {p[0]: v * k for p, v in ttr}
    rows = ["endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps"]
    n = 0
    ffr = _ep_rows(dump / "ff" / "ep_ff.tsv", 5)
    k = ep_scale([v for _p, v in ffr])
    for p, v in ffr:
        rows.append("\t".join(p[:4]) + "\t%.3f\t%.3f" % (v * k, tt.get(p[0], 1e6)))
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
    ap.add_argument("--max-worst-ps", type=float, default=15.0, help="refuse when the worst internal FF hold is below -this (default 15)")
    ap.add_argument("--max-ends", type=int, default=100, help="refuse when more ends than this would be padded (default 100)")
    ap.add_argument("--min-setup-room-ps", type=float, default=0.0, help="TT setup left on a padded end after its HB4s (default 0)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rt, base, kit, out = Path(a.rt), Path(a.base).resolve(), Path(a.kit).resolve(), Path(a.out).resolve()
    ro = rt / "tools/die_plan/post_route_drv"
    sys.path.insert(0, str(rt / "tools/die_plan"))      # hold_eco_internal (HB4 constants) of the SAME checkout as the Tcl, not of this file
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

    # 2. endpoint dump from the sign-off's own sessions (ROUTE-LOSS 11-18: a current sign-off already wrote both tables)
    procs = []
    native = (not dry) and native_tables(so1)
    res["steps"]["endpoint_tables"] = "signoff" if native else "dump"
    for c in ("ff", "tt"):
        d = out / "dump" / c
        if native:
            d.mkdir(parents=True, exist_ok=True)
            shutil.copy(so1 / c / ("ep_%s.tsv" % c), d / ("ep_%s.tsv" % c))
            continue
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
    viol = check_limits(out / "hold_endpoints.tsv", out / "plan.tsv", a.max_worst_ps, a.max_ends, a.min_setup_room_ps)
    res["limits"] = {"max_worst_ps": a.max_worst_ps, "max_ends": a.max_ends, "min_setup_room_ps": a.min_setup_room_ps, "violations": viol}
    if viol:
        for v in viol:
            print("OT_LIMIT", v)
        return finish(4, "REFUSED by limits: " + "; ".join(viol))
    shutil.copy(routed, out / "in" / "6_final.odb")           # a copy: the routed DB itself is never opened for writing
    shutil.copy(out / "plan.tsv", out / "ins" / "plan.tsv")
    (out / "ins" / "drv.tcl").write_text(DRV)
    (out / "ins" / "netcheck.tcl").write_text(NETCHECK)
    (out / "ins" / "obs.tcl").write_text(OBS)

    # 3. insert, 4. incremental route of the touched nets only
    common = ["docker", "run", "--rm"] + user + nomcap_mount(so1 / "tt" / "cmd.sh")
    if run(common + ["-v", "%s:/in:ro" % (out / "in"), "-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-v", "%s:/work:ro" % kit,
                     a.image, OPENROAD, "-no_init", "-exit", "/out/drv.tcl"], out / "ins" / "drv.log"):
        return finish(3, "insert failed (ins/drv.log)")
    drv_log = (out / "ins" / "drv.log").read_text()
    net_viol = [ln for ln in drv_log.splitlines() if ln.startswith("OT_LIMIT")]
    if net_viol:
        res["limits"]["violations"] = net_viol
        return finish(4, "REFUSED by limits: " + "; ".join(net_viol))
    if "DRV check_placement OK" not in drv_log:
        return finish(3, "check_placement did not pass after the insert (ins/drv.log)")
    (out / "ins" / "route").mkdir(exist_ok=True)
    env = ["-e", "OT_HEI_IN=/out/ins.odb", "-e", "OT_HEI_CELLS=/out/hold_eco_internal_cells.tsv", "-e", "OT_HEI_OUT=/out/route",
           "-e", "OT_HEI_LIBS=/out/libs.txt", "-e", "OT_HEI_PG_DIR=/work", "-e", "OT_HEI_THREADS=%d" % a.threads]
    run(common + ["-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-v", "%s:/work:ro" % kit] + env
        + [a.image, OPENROAD, "-no_init", "-exit", "/ro/hold_eco_internal_route.tcl"], out / "ins" / "route.log")
    routed2 = out / "ins" / "route" / "hei_routed.odb"
    if not routed2.is_file() or "OT_HEI_ROUTE_DONE" not in (out / "ins" / "route.log").read_text():
        return finish(3, "incremental route failed (ins/route.log)")

    def obstructions(odb_dir, odb_name):
        o = subprocess.run(["docker", "run", "--rm"] + user + ["-v", "%s:/d:ro" % odb_dir, "-v", "%s:/ro:ro" % (out / "ins"),
                           "-e", "OBS_ODB=/d/" + odb_name, a.image, OPENROAD, "-no_init", "-exit", "/ro/obs.tcl"],
                           capture_output=True, text=True).stdout
        for ln in o.splitlines():
            if ln.startswith("LIM obstructions"):
                return int(ln.split()[-1])
        return None
    obs_in, obs_out = obstructions(out / "in", "6_final.odb"), obstructions(out / "ins" / "route", "hei_routed.odb")
    res["limits"]["obstructions_in"], res["limits"]["obstructions_out"] = obs_in, obs_out
    if obs_in is None or obs_out is None or obs_in != obs_out:
        msg = "pg_obstructions_left input %s output %s (the route step's temporary PG obstructions must all be gone)" % (obs_in, obs_out)
        print("OT_LIMIT", msg)
        res["limits"]["violations"] = [msg]
        return finish(4, "REFUSED by limits: " + msg)

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
