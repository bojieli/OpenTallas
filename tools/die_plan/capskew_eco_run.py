#!/usr/bin/env python3
"""capskew_eco_run.py -- the post-route capture-skew ECO as one command (CAPSKEW-ECO 11-17, FABLE-CLOSURE-STRATEGY 11-17 lever 6).

Origin: HEAD hd_serdes sd9f routed TT was -105.6 ps on ONE saturated data family against -16 at GRT (routed data wire delay about
12 % over).  FABLE-FIX-HEAD-SD9F closed it with per-register capture skew: 309 clock delay cells in front of 202 capture flops plus
43 hold pads, no existing cell moved, DRT 4 iterations, TT -20.79, internal FF hold 0.  This is that ECO as a reusable tool.

A routed DB that fails TT setup goes through: first sign-off -> endpoint dump (TT setup of every flop D endpoint, FF reg->reg hold
room, launch-side setup of every flop Q) -> plan (capture flops with TT setup < --cut-ps and positive hold room get a clock delay chain
sized from the setup deficit, capped by hold room - --hold-margin-ps; broken FF reg->reg holds get a D pad) -> insert on the clock
LEAF pin (capskew_eco_insert.tcl) -> guides + incremental detailed route of only the touched nets -> final sign-off.

  capskew_eco_run.py --base RESULTS_BASE --kit KITDIR --name NAME --out OUTDIR [--first-signoff DIR] [--db ROUTED.odb] [--threads 8]
                     [--image openroad/orfs:asap7lock] [--sign-image openroad/orfs:latest] [--dry-run]

  RESULTS_BASE   <run>/results/<platform>/<design>/base holding 5_2_route.odb (else 5_route.odb): a routed DB WITHOUT fillers
  KITDIR         the kit (constraint.sdc, config.mk, pg_connect.tcl) mounted as /work (read-only)
Run it on a build host through ot-run (it starts docker).  Exit 0 = final sign-off SIGNED, 1 = not signed, 2 = nothing to do (no flop
below --cut-ps and no broken hold), 3 = a step failed, 4 = REFUSED by a limit (nothing signed; a limit hit after the route is
reported the same way).  Result: OUTDIR/RESULT.json.

LIMITS (every one prints OT_LIMIT <name> ... , is written to RESULT.json and exits 4):
  capture flops <= 300           (--max-flops)
  delay per flop <= 130 ps TT    (--max-delay-ps; the delay ladder is BUFx4 20 / 2xBUFx4 42 / HB4 65 / HB4+BUFx4 86 / +2 BUFx4 107 / 2xHB4 130)
  leaf clock pins only           (checked on the DB before the insert: no port net, no tap/root net of ot_clock_taps.json, <= --max-leaf-fanout sinks)
  setup gain >= 0.7 x deficit    (--min-gain-frac; planned worst-slack gain before any route, measured gain in the final sign-off)
  PG obstruction count unchanged (the routed DB's obstructions in and out must be equal)
  hold pads <= 100               (--max-pads), launch room >= --min-launch-room-ps after the delay (when the STA can report pin slack)
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_eco_internal_run as HR  # noqa: E402  (signoff_cmd, libs_from_receipt, retarget_cmd, run: one pattern, one implementation)

B, H = "BUFx4_ASAP7_75t_R", "HB4xp67_ASAP7_75t_R"
TT_PS = {B: 20.0, H: 65.0}                 # measured TT delay of the cell on the sd9f clock leaf (FABLE-FIX-HEAD-SD9F q4)
FF_PAD_PS = {B: 12.0, H: 33.0}             # lower bound of the FF delay of a data pad cell
CK_STEPS = [(20, [B]), (42, [B, B]), (65, [H]), (86, [H, B]), (107, [H, B, B]), (130, [H, H])]
FF_RATIO = 0.65                            # FF delay of a clock chain <= this x its TT delay (BUFx4 12/20, HB4 33/65: <= 0.6 with margin)
MARK = HR.MARK
SLACK_MAX_PS = 150.0

# ---- STA dump blocks (spliced into the sign-off session at the KW-FIX-24 marker; get_property slack is already in the session's ps unit) ----------------------------
TT_BLOCK = r'''set fh [open /out/cs_tt.tsv w]
puts $fh "endpoint\ttt_setup_slack_ps"
foreach pe [find_timing_paths -path_delay max -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack -slack_max %(smax)s] {
  puts $fh "[get_full_name [get_property $pe endpoint]]\t[format %%.3f [get_property $pe slack]]"
}
close $fh
set fh [open /out/cs_q.tsv w]
puts $fh "pin\tslack_ps"
foreach p [all_registers -output_pins] {
  if {[catch {set s [get_property $p slack_max]}]} { set s "" }
  if {$s eq "" || [regexp -nocase {inf|nan} $s]} continue
  puts $fh "[get_full_name $p]\t[format %%.3f $s]"
}
close $fh
'''
FF_BLOCK = r'''set fh [open /out/cs_ff.tsv w]
puts $fh "endpoint\tff_hold_slack_ps"
foreach pe [find_timing_paths -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay min -group_path_count 1000000 -unique_paths_to_endpoint -sort_by_slack -slack_max %(smax)s] {
  puts $fh "[get_full_name [get_property $pe endpoint]]\t[format %%.3f [get_property $pe slack]]"
}
close $fh
'''
OBS = "read_db $::env(OBS_ODB)\nputs \"LIM obstructions [llength [[ord::get_db_block] getObstructions]]\"\nexit\n"
OPENROAD = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"


def patch_session(text, corner):
    """the sign-off session plus the capskew dump block of its corner"""
    if text.count(MARK) != 1:
        raise SystemExit("sign-off session.tcl has no unique %r marker (signoff.py version mismatch)" % MARK)
    blk = (TT_BLOCK if corner == "tt" else FF_BLOCK) % {"smax": "%g" % SLACK_MAX_PS}
    return text.replace(MARK, blk + MARK)


def read_tsv(path, ncol=2):
    """{key: float} of a two-column dump (header line skipped; nan rows dropped; the minimum wins on a repeated key)"""
    d = {}
    p = Path(path)
    if not p.is_file():
        return d
    for i, line in enumerate(p.read_text(errors="replace").splitlines()):
        f = line.split("\t")
        if not i or len(f) < ncol:
            continue
        try:
            v = float(f[1])
        except ValueError:
            continue
        if math.isnan(v):
            continue
        d[f[0]] = min(v, d.get(f[0], 1e9))
    return d


def inst_of(pin):
    return pin.rsplit("/", 1)[0]


def step_for(need_ps, room_ps, max_delay_ps):
    """(cells, tt_delay_ps) the smallest ladder step covering need_ps within the hold room (FF delay <= FF_RATIO x TT delay <= room)
    and the per-flop delay cap; when none covers it the LARGEST step inside both caps (a partial gain); (None, 0) when not even the
    first step fits."""
    best = None
    for lim, cells in CK_STEPS:
        if lim > max_delay_ps or FF_RATIO * lim > room_ps:
            break
        best = (cells, float(lim))
        if lim >= need_ps:
            return best
    return best if best else (None, 0.0)


def plan(tt, ff, q, cut_ps=-15.0, target_ps=-8.0, hold_margin_ps=10.0, max_delay_ps=130.0, hcut_ps=3.0, htarget_ps=8.0,
         min_launch_room_ps=10.0, min_pad_setup_room_ps=0.0, smax_ps=SLACK_MAX_PS):
    """pure: the ECO plan from the endpoint dumps.  tt: {endpoint pin: TT setup slack ps}; ff: {endpoint pin: FF reg->reg hold slack ps}
    (absent = at least smax_ps); q: {flop Q pin: TT slack of the paths launched there} ({} = not available).
    -> dict(ck=[(inst, slack, need, cells, gain)], pads=[(inst, pin, hold, cells)], skipped=[(why, pin, slack)],
            worst_before, worst_after_pred, deficit, gain_pred)."""
    ck, pads, skipped = [], [], []
    padded = set()
    for pin, h in sorted(ff.items(), key=lambda kv: kv[1]):
        if h >= hcut_ps:
            break
        need = htarget_ps - h
        cells = [B] if need <= FF_PAD_PS[B] else [H] if need <= FF_PAD_PS[H] else [H, H]
        room = tt.get(pin, smax_ps) - sum(TT_PS[c] for c in cells)
        if room < min_pad_setup_room_ps:
            skipped.append(("no TT setup room for the hold pad (room %.1f)" % room, pin, h))
            continue
        i, p = pin.rsplit("/", 1)
        pads.append((i, p, h, cells))
        padded.add(pin)
    gains = {}
    for pin, s in sorted(tt.items(), key=lambda kv: kv[1]):
        if s >= cut_ps:
            break
        i, p = pin.rsplit("/", 1)
        if p != "D":
            skipped.append(("setup endpoint is not a flop D pin", pin, s))
            continue
        if pin in padded:
            skipped.append(("capture flop is a hold-pad target", pin, s))
            continue
        need = target_ps - s
        room = ff.get(pin, smax_ps) - hold_margin_ps
        if room <= 0:
            skipped.append(("capture flop has no hold room (%.1f ps, margin %g)" % (ff.get(pin, smax_ps), hold_margin_ps), pin, s))
            continue
        cells, d = step_for(need, room, max_delay_ps)
        if cells is None:
            skipped.append(("hold room %.1f ps fits no delay step" % room, pin, s))
            continue
        qs = q.get(i + "/QN", q.get(i + "/Q"))
        if qs is not None and qs - d < min_launch_room_ps:
            skipped.append(("launch side keeps %.1f ps after +%g ps (< %g)" % (qs - d, d, min_launch_room_ps), pin, s))
            continue
        ck.append((i, s, need, cells, d))
        gains[pin] = d
    worst_before = min(tt.values()) if tt else None
    after = [s + gains.get(p, 0.0) for p, s in tt.items() if s < cut_ps]
    worst_after = min(after) if after else None
    deficit = max(0.0, -worst_before) if worst_before is not None else 0.0
    gain = (worst_after - worst_before) if after else 0.0
    return dict(ck=ck, pads=pads, skipped=skipped, worst_before=worst_before, worst_after_pred=worst_after, deficit=deficit,
                gain_pred=gain, unfixed=len([1 for p, s in tt.items() if s < cut_ps and p not in gains]))


def check_limits(pl, max_flops=300, max_pads=100, min_gain_frac=0.7):
    """pure: violation strings (empty = inside the limits) of a plan"""
    viol = []
    if len(pl["ck"]) > max_flops:
        viol.append("capture_flops %d > %d" % (len(pl["ck"]), max_flops))
    if len(pl["pads"]) > max_pads:
        viol.append("hold_pads %d > %d" % (len(pl["pads"]), max_pads))
    if pl["ck"] and pl["gain_pred"] < min_gain_frac * pl["deficit"]:
        viol.append("setup_gain planned %.1f ps < %g x deficit %.1f ps (worst %.1f -> predicted %.1f)" % (
            pl["gain_pred"], min_gain_frac, pl["deficit"], pl["worst_before"], pl["worst_after_pred"]))
    return viol


def list_rows(pl):
    """the eco_list.tsv text of a plan"""
    rows = ["CK\t%s\tCLK\t%s" % (i, ",".join(c)) for i, s, n, c, d in pl["ck"]]
    rows += ["D\t%s\t%s\t%s" % (i, p, ",".join(c)) for i, p, h, c in pl["pads"]]
    return "\n".join(rows) + ("\n" if rows else "")


def measured_gain(before_wns, after_wns, min_gain_frac=0.7):
    """(ok, gain, deficit): the final sign-off's measured setup gain against min_gain_frac x the pre-ECO deficit"""
    deficit = max(0.0, -before_wns)
    gain = after_wns - before_wns
    return gain >= min_gain_frac * deficit, gain, deficit


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--base", required=True)
    ap.add_argument("--kit", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--db", help="routed odb without fillers (default: BASE/5_2_route.odb, else BASE/5_route.odb)")
    ap.add_argument("--first-signoff")
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("--image", default="openroad/orfs:asap7lock")
    ap.add_argument("--sign-image", default="openroad/orfs:latest")
    ap.add_argument("--rt", default=str(HERE.parent.parent))
    ap.add_argument("--cut-ps", type=float, default=-15.0, help="capture flops with TT setup below this get a chain (default -15)")
    ap.add_argument("--target-ps", type=float, default=-8.0, help="setup the chain is sized to reach (default -8)")
    ap.add_argument("--hold-margin-ps", type=float, default=10.0, help="FF hold left on a capture flop after its chain (default 10)")
    ap.add_argument("--max-flops", type=int, default=300)
    ap.add_argument("--max-delay-ps", type=float, default=130.0)
    ap.add_argument("--max-pads", type=int, default=100)
    ap.add_argument("--max-leaf-fanout", type=int, default=100)
    ap.add_argument("--min-gain-frac", type=float, default=0.7)
    ap.add_argument("--min-launch-room-ps", type=float, default=10.0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    rt, base, kit, out = Path(a.rt), Path(a.base).resolve(), Path(a.kit).resolve(), Path(a.out).resolve()
    ro = rt / "tools/die_plan/post_route_drv"
    for need in (ro / "capskew_eco_insert.tcl", ro / "capskew_eco_route.tcl", ro / "capskew_eco_guides.py"):
        if not need.is_file():
            raise SystemExit("missing %s" % need)
    routed = Path(a.db).resolve() if a.db else next((p for p in (base / "5_2_route.odb", base / "5_route.odb") if p.is_file()), None)
    if routed is None or not routed.is_file():
        raise SystemExit("no routed odb without fillers (5_2_route.odb / 5_route.odb) in %s; pass --db" % base)
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

    def refuse(viol):
        res.setdefault("limits", {})["violations"] = viol
        for v in viol:
            print("OT_LIMIT", v)
        return finish(4, "REFUSED by limits: " + "; ".join(viol))

    # 1. first sign-off (its tt/ff session dumps carry the libraries and the STA session the endpoints are read from)
    so1 = Path(a.first_signoff).resolve() if a.first_signoff else out / "so_first"
    if not a.first_signoff:
        HR.run(HR.signoff_cmd(rt, base, kit, a.name, so1, a.sign_image), out / "so_first.log", dry,
               env=dict(os.environ, OT_SIGNOFF_PROFILE="minimal"), cwd=str(rt))
    for c in ("ff", "tt"):
        if not dry and not (so1 / c / "session.tcl").is_file():
            return finish(3, "first sign-off has no %s/session.tcl: %s" % (c, so1))
    if not dry:
        libs_all, libs_std = HR.libs_from_receipt(so1 / "tt" / "libraries.json")
        (out / "ins").mkdir(exist_ok=True)
        (out / "ins" / "libs.txt").write_text("\n".join(libs_all) + "\n")
        sj1 = so1 / "signoff.json"
        if sj1.is_file():
            res["first_signoff_tt_wns_ps"] = ((json.loads(sj1.read_text()).get("checks") or {}).get("setup_tt") or {}).get("wns_ps")

    # 2. endpoint dump from the sign-off's own sessions
    procs = []
    for c in ("ff", "tt"):
        d = out / "dump" / c
        if not dry:
            shutil.copytree(so1 / c, d)
            (d / "session.tcl").write_text(patch_session((so1 / c / "session.tcl").read_text(), c))
            (d / "cmd.sh").write_text(HR.retarget_cmd((so1 / c / "cmd.sh").read_text(), str(so1 / c), str(d), "cs_dump_%s_%d" % (c, os.getpid())))
            print("+ bash", d / "cmd.sh", flush=True)
            procs.append(subprocess.Popen(["bash", str(d / "cmd.sh")], stdout=open(d / "run.log", "w"), stderr=subprocess.STDOUT))
    if any(p.wait() for p in procs):
        return finish(3, "endpoint dump failed (dump/*/run.log)")
    if dry:
        return finish(0, "dry run")
    tt, ff, q = read_tsv(out / "dump/tt/cs_tt.tsv"), read_tsv(out / "dump/ff/cs_ff.tsv"), read_tsv(out / "dump/tt/cs_q.tsv")
    if not tt:
        return finish(3, "no TT endpoint rows in dump/tt/cs_tt.tsv")
    if res.get("first_signoff_tt_wns_ps") is not None and abs(min(tt.values()) - float(res["first_signoff_tt_wns_ps"])) > 1.0:
        return finish(3, "dump worst TT %.2f differs from the first sign-off %.2f (unit or frame mismatch)" % (
            min(tt.values()), float(res["first_signoff_tt_wns_ps"])))

    # 3. plan + limits (before any insert or route)
    pl = plan(tt, ff, q, a.cut_ps, a.target_ps, a.hold_margin_ps, a.max_delay_ps, min_launch_room_ps=a.min_launch_room_ps)
    res["steps"].update(tt_endpoints=len(tt), hold_endpoints=len(ff), launch_pins=len(q), capture_flops=len(pl["ck"]), clock_cells=sum(len(c[3]) for c in pl["ck"]),
                        hold_pads=len(pl["pads"]), pad_cells=sum(len(p[3]) for p in pl["pads"]), skipped=len(pl["skipped"]),
                        worst_before=pl["worst_before"], worst_after_predicted=pl["worst_after_pred"], launch_check=bool(q))
    (out / "skipped.tsv").write_text("".join("%s\t%s\t%.2f\n" % s for s in pl["skipped"]))
    if not pl["ck"] and not pl["pads"]:
        return finish(2, "nothing to do (no capture flop below %g ps with hold room, no broken reg->reg hold)" % a.cut_ps)
    res["limits"] = {"max_flops": a.max_flops, "max_delay_ps": a.max_delay_ps, "max_pads": a.max_pads, "min_gain_frac": a.min_gain_frac,
                     "hold_margin_ps": a.hold_margin_ps, "max_leaf_fanout": a.max_leaf_fanout}
    viol = check_limits(pl, a.max_flops, a.max_pads, a.min_gain_frac)
    if viol:
        return refuse(viol)
    (out / "eco_list.tsv").write_text(list_rows(pl))
    shutil.copy(out / "eco_list.tsv", out / "ins" / "eco_list.tsv")
    shutil.copy(routed, out / "in" / "5_2_route.odb")          # a copy: the routed DB itself is never opened for writing
    (out / "ins" / "obs.tcl").write_text(OBS)
    taps = base / "ot_clock_taps.json"
    names = sorted((json.loads(taps.read_text()).get("sinks") or {}).keys()) if taps.is_file() else []
    (out / "ins" / "taps.txt").write_text("\n".join(names) + ("\n" if names else ""))

    # 4. insert (leaf-pin limit checked in the Tcl), guides, incremental detailed route
    common = ["docker", "run", "--rm"] + user
    mounts = ["-v", "%s:/in:ro" % (out / "in"), "-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-v", "%s:/work:ro" % kit]
    env = ["-e", "E_IN=/in/5_2_route.odb", "-e", "E_OUT=/out/pre_drt.odb", "-e", "E_LIST=/out/eco_list.tsv", "-e", "E_DIR=/out",
           "-e", "E_PGDIR=/work", "-e", "E_TAPS=/out/taps.txt", "-e", "E_MAXFAN=%d" % a.max_leaf_fanout]
    HR.run(common + mounts + env + [a.image, OPENROAD, "-no_init", "-exit", "-threads", str(a.threads), "/ro/capskew_eco_insert.tcl"], out / "ins" / "insert.log")
    ilog = (out / "ins" / "insert.log").read_text(errors="replace")
    net_viol = [ln for ln in ilog.splitlines() if ln.startswith("OT_LIMIT")]
    if net_viol:
        return refuse(net_viol)
    if "CAPSKEW_INSERT_DONE" not in ilog:
        return finish(3, "insert failed (ins/insert.log)")
    if "CAPSKEW_MOVED 0 " not in ilog:
        res["steps"]["existing_cells_moved"] = re.search(r"CAPSKEW_MOVED (\d+)", ilog).group(1) if re.search(r"CAPSKEW_MOVED (\d+)", ilog) else "?"
    else:
        res["steps"]["existing_cells_moved"] = "0"
    gcmd = ["openroad", "-python", "-exit", "/ro/capskew_eco_guides.py", "/out/pre_drt.odb", "/out/guided.odb", "/out/moved.txt", "/out/ripped.txt"]
    HR.run(common + ["-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, a.image, "bash", "-c",
                     "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; " + " ".join(gcmd)], out / "ins" / "guides.log")
    if not (out / "ins" / "guided.odb").is_file():
        return finish(3, "guides failed (ins/guides.log)")
    HR.run(common + ["-v", "%s:/out" % (out / "ins"), "-v", "%s:/ro:ro" % ro, "-e", "X_IN=/out/guided.odb", "-e", "X_OUT=/out/5_2_route.odb",
                     "-e", "X_DIR=/out", "-e", "X_THREADS=%d" % a.threads, a.image, OPENROAD, "-no_init", "-exit", "/ro/capskew_eco_route.tcl"],
           out / "ins" / "route.log")
    rlog = (out / "ins" / "route.log").read_text(errors="replace")
    routed2 = out / "ins" / "5_2_route.odb"
    if not routed2.is_file() or "CAPSKEW_ROUTE_DONE" not in rlog:
        return finish(3, "incremental route failed (ins/route.log)")
    unrouted = (out / "ins" / "unrouted.txt").read_text().split()
    drc = (out / "ins" / "5_route_drc.rpt")
    ndrc = len(re.findall(r"violation type", drc.read_text(errors="replace"))) if drc.is_file() else None
    res["steps"].update(unrouted=len(unrouted), drc=ndrc)
    if unrouted or ndrc != 0:
        return finish(3, "incremental route left %d unrouted nets / %s DRC violations (ins/route.log)" % (len(unrouted), ndrc))

    def obstructions(odb_dir, odb_name):
        o = subprocess.run(["docker", "run", "--rm"] + user + ["-v", "%s:/d:ro" % odb_dir, "-v", "%s:/ro:ro" % (out / "ins"),
                           "-e", "OBS_ODB=/d/" + odb_name, a.image, OPENROAD, "-no_init", "-exit", "/ro/obs.tcl"],
                           capture_output=True, text=True).stdout
        for ln in o.splitlines():
            if ln.startswith("LIM obstructions"):
                return int(ln.split()[-1])
        return None
    obs_in, obs_out = obstructions(out / "in", "5_2_route.odb"), obstructions(out / "ins", "5_2_route.odb")
    res["limits"]["obstructions_in"], res["limits"]["obstructions_out"] = obs_in, obs_out
    if obs_in is None or obs_out is None or obs_in != obs_out:
        return refuse(["pg_obstructions input %s output %s (must be equal)" % (obs_in, obs_out)])

    # 5. final sign-off on the re-routed DB
    sr = out / "so_run"
    plat, des = base.parent.parent.name, base.parent.name
    b2 = sr / "results" / plat / des / "base"
    b2.mkdir(parents=True)
    (sr / "reports" / plat / des / "base").mkdir(parents=True)
    shutil.copy(kit / "config.mk", sr / "config.mk")
    shutil.copy(routed2, b2 / "6_final.odb")
    for f in base.iterdir():
        if f.is_file() and f.name in ("1_2_yosys.v", "6_final.v", "6_final.sdc", "clock_period.txt"):
            shutil.copy(f, b2 / f.name)
    shutil.copy(drc, sr / "reports" / plat / des / "base" / "5_route_drc.rpt")
    HR.run(HR.signoff_cmd(rt, b2, kit, a.name, out / "so_out", a.sign_image), out / "so.log", False,
           env=dict(os.environ, OT_SIGNOFF_PROFILE="minimal"), cwd=str(rt))
    sj = out / "so_out" / "signoff.json"
    if not sj.is_file():
        return finish(3, "final sign-off wrote no signoff.json (so.log)")
    rec = json.loads(sj.read_text())
    chk = rec.get("checks") or {}
    tt_after = (chk.get("setup_tt") or {}).get("wns_ps")
    res["steps"]["tt_after"] = tt_after
    res["steps"]["hold_ff_after"] = (chk.get("hold_ff") or {}).get("wns_ps")
    res["final_routed_db"] = str(b2 / "6_final.odb")
    if tt_after is not None and pl["worst_before"] is not None:
        ok, gain, deficit = measured_gain(pl["worst_before"], float(tt_after), a.min_gain_frac)
        res["steps"]["measured_gain_ps"], res["steps"]["deficit_ps"] = gain, deficit
        if not ok and pl["deficit"] > 0:
            print("OT_LIMIT measured setup gain %.1f ps < %g x deficit %.1f ps" % (gain, a.min_gain_frac, deficit))
            res["limits"]["violations"] = ["measured setup gain %.1f < %g x %.1f" % (gain, a.min_gain_frac, deficit)]
    code = subprocess.run([sys.executable, "-I", str(rt / "tools/die_plan/signoff.py"), "verdict", str(sj)], capture_output=True).returncode
    return finish(0 if code == 0 else 1, "SIGNED" if code == 0 else "NOT SIGNED (so.log)")


if __name__ == "__main__":
    sys.exit(main())
