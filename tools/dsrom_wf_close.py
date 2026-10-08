#!/usr/bin/env python3
"""DS-ROM wavefront package controller closure (ot_rom_pkg_ctrl_wfc, WAVE=1) at 1.2 GHz, in context.

  route   one instance through tools/run_abi3_physical.py (ORFS, CORNER=WC synthesis/repair, hold repair at
          WC+BC, 833 ps, 60 ps setup / 25 ps hold uncertainty, IO at 20 % of the period, ADDER_MAP_FILE off),
          without the driver's wall-clock ceilings; then per-corner signoff STA on 6_final.odb + RCX spef
          (SS RVT libs: setup; FF RVT libs: hold) with tools/qwen_async_seq_incontext_physical.py sta.
              python3 tools/dsrom_wf_close.py route --inst src|stg --run-dir D [--util 40]
  stage   the wavefront stage bench (tools/dsrom_wavefront_rtl_campaign.py run-stage: package = layer 20, jobs
          0,1,2,3(corrupted),3(re-issue),4 bit-exact vs ISA) with ot_rom_pkg_ctrl_wfc in place of
          ot_rom_pkg_ctrl_wf (a module-renamed copy), from a prepared stage scratch (prepare_stage.json,
          stage_cfg.svh, cfg_stage/, roms/); compares the bench output with the reference run's.
              python3 tools/dsrom_wf_close.py stage --from PREPARED --scratch D [--wave 1|0]
  record  results/rtl/dsrom_wf_close_20261004/record.json from the route dirs, the equivalence logs and the
          screens.
              python3 tools/dsrom_wf_close.py record --dir D --out record.json

Instances (FULL_SHAPE die parameters, rtl/chip/ckvsel/ot_chip_v41x_die.sv): FLIT 512, NW 21, AW 30, VWA 15,
USER_W 10, MAXU 866, KVW 32768, WIN 6.  src = SOURCE 1 (embedding package: wavefront issue, verify, squash);
stg = SOURCE 0 (a stage package: HIDDEN rewind by up to WIN); RX/TX payload words of the L20 package (41 / 46).
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = "rtl/rom/wavefront/ot_rom_pkg_ctrl_wfc.sv"
COMMON = dict(WAVE=1, WIN=6, FLIT=512, NW=21, AW=30, VWA=15, USER_W=10, MAXU=866, KVW=32768,
              SEND_HIDDEN=1, HID_DEST=1, FWD_TOKEN=1)
INST = {"src": dict(COMMON, SOURCE=1, XWORDS=41, RXWORDS=41),
        "stg": dict(COMMON, SOURCE=0, XWORDS=46, RXWORDS=41)}


STA_TCL = r"""
set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [lsort [glob $P/lib/NLDM/*_RVT_$::env(WF_LIB)_*.lib*]] { read_liberty $f }
read_db $::env(WF_ODB)
read_sdc $::env(WF_SDC)
read_spef $::env(WF_SPEF)
set_propagated_clock [all_clocks]
set ck [get_clocks]
proc fails {} {
  set nv 0; set nh 0
  foreach p [concat [all_registers -data_pins] [all_outputs]] {
    set s [get_property $p slack_max]; if {$s != "INF" && $s < 0} { incr nv }
    set s [get_property $p slack_min]; if {$s != "INF" && $s < 0} { incr nh }
  }
  return "$nv $nh"
}
proc rep {tag} {
  puts "WFSTA $tag setup [sta::worst_slack_cmd max] hold [sta::worst_slack_cmd min] fails [fails]"
  puts "WFPATH $tag max"; report_checks -path_delay max -digits 1
  puts "WFPATH $tag min"; report_checks -path_delay min -digits 1
  puts "WFEND"
}
# insertion delay of the block's own tree (register clock pins)
set lmin 1e9; set lmax 0
foreach p [all_registers -clock_pins] {
  set a [get_property $p arrival_max_rise]; if {$a != "INF" && $a > $lmax} { set lmax $a }
  set a [get_property $p arrival_min_rise]; if {$a != "INF" && $a < $lmin} { set lmin $a }
}
puts "WFLAT $lmin $lmax"
rep block
# in context: the neighbours hang off the same die clock tree -> IO relative to a virtual clock that
# carries the block's own insertion delay (setup: launch late / capture early; hold: the reverse)
set per [get_property $ck period]
set io [expr 0.2 * $per]
set ins [lsearch -all -inline -not [all_inputs] [get_ports $::env(WF_CLK)]]
unset_input_delay $ins
unset_output_delay [all_outputs]
create_clock -name vclk -period $per
set_clock_latency -min $lmin [get_clocks vclk]
set_clock_latency -max $lmax [get_clocks vclk]
set_clock_uncertainty -setup $::env(WF_USETUP) [get_clocks vclk]
set_clock_uncertainty -hold $::env(WF_UHOLD) [get_clocks vclk]
set_input_delay $io -clock vclk $ins
set_output_delay $io -clock vclk [all_outputs]
rep incontext
set_false_path -from $ins
set_false_path -to [all_outputs]
rep reg2reg
puts "WFDONE"
"""


def corner_sta(work: Path, nick: str, out: Path):
    res = next(work.rglob(f"results/asap7/{nick}/base"))
    mount = res.parents[3]
    (mount / "wf_sta.tcl").write_text(STA_TCL)
    rel = lambda q: "/work/" + str(q.relative_to(mount))
    rec = dict(basis="OpenSTA on 6_final.odb + RCX 6_final.spef, one ASAP7 RVT liberty corner per run, propagated "
                     "clock. block = the routed SDC (IO at 20 % of the period vs an ideal clock); incontext = IO at "
                     "20 % vs a virtual clock carrying the block's own min/max insertion delay (same die tree as "
                     "the neighbours); reg2reg = IO false-pathed. 60 ps setup / 25 ps hold uncertainty.",
               artifacts_sha256={q.name: sha(res / q) for q in (Path("6_final.odb"), Path("6_final.sdc"),
                                                                 Path("6_final.spef"))}, corners={})
    import re
    for lib in ("SS", "FF"):
        c = ["docker", "run", "--rm", "-v", f"{mount}:/work", "-e", f"WF_LIB={lib}",
             "-e", f"WF_ODB={rel(res / '6_final.odb')}", "-e", f"WF_SDC={rel(res / '6_final.sdc')}",
             "-e", f"WF_SPEF={rel(res / '6_final.spef')}", "-e", "WF_CLK=clk", "-e", "WF_USETUP=60",
             "-e", "WF_UHOLD=25", "openroad/orfs:latest", "bash", "-lc",
             "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -no_splash /work/wf_sta.tcl"]
        p = subprocess.run(c, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"wf_sta_{lib}.log").write_text(log)
        r = dict(exit=p.returncode, done="WFDONE" in log)
        m = re.search(r"WFLAT (\S+) (\S+)", log)
        if m:
            r["insertion_ps"] = [round(float(m.group(1)), 1), round(float(m.group(2)), 1)]
        for m in re.finditer(r"WFSTA (\w+) setup (\S+) hold (\S+) fails (\d+) (\d+)", log):
            r[m.group(1)] = dict(setup_wns_ps=round(float(m.group(2)) * 1e12, 1),
                                 hold_wns_ps=round(float(m.group(3)) * 1e12, 1),
                                 failing_setup=int(m.group(4)), failing_hold=int(m.group(5)))
        for m in re.finditer(r"WFPATH (\w+) (max|min)\n(.*?)(?=WFPATH|WFEND)", log, re.S):
            # report_checks emits one path per group. The first may be a
            # passing recovery path; select the least slack across all groups.
            paths = []
            for text in re.split(r"(?=Startpoint:)", m.group(3)):
                sp = re.search(r"Startpoint: (\S+)", text)
                ep = re.search(r"Endpoint: (\S+)", text)
                sl = re.search(r"([-+]?\d+(?:\.\d+)?)\s+slack \((?:MET|VIOLATED)\)", text)
                group = re.search(r"Path Group: (\S+)", text)
                if sp and ep and sl:
                    paths.append((float(sl.group(1)), sp.group(1), ep.group(1), group and group.group(1)))
            if paths:
                slack, sp, ep, group = min(paths)
                mode = r.setdefault(m.group(1), {})
                mode[f"worst_{m.group(2)}_path"] = [sp, ep]
                mode[f"worst_{m.group(2)}_path_slack_ps"] = slack
                mode[f"worst_{m.group(2)}_path_group"] = group
        rec["corners"][lib] = r
    ss, ff = rec["corners"]["SS"], rec["corners"]["FF"]
    def met(mode):
        try:
            return ss[mode]["setup_wns_ps"] >= 0 and ff[mode]["hold_wns_ps"] >= 0 and ss[mode]["hold_wns_ps"] >= 0
        except (KeyError, TypeError):
            return None
    rec["signoff"] = {m: met(m) for m in ("block", "incontext", "reg2reg")}
    (out / "wf_sta.json").write_text(json.dumps(rec, indent=1) + "\n")
    return rec


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[name] = m
    spec.loader.exec_module(m)
    return m


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cmd_route(a):
    out = a.run_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("OT_ORFS_NUM_CORES", "20")
    drv = module("wf_physical", ROOT / "tools/run_abi3_physical.py")
    drv.run = lambda cmd, *, cwd=None, timeout=None: subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    drv.flow_timeout_seconds = lambda: None
    drv.synth_timeout_seconds = lambda: None
    args = ["--view", "asap7", "--top", "ot_rom_pkg_ctrl_wfc", "--source", SRC,
            "--clock-period-ns", "0.833", "--clock-uncertainty-ns", "0.060", "--clock-uncertainty-hold-ns", "0.025",
            "--orfs-corner", "WC", "--hold-corners", "WC,BC", "--stages", "pnr", "--io-delay-fraction", "0.2",
            "--max-transition-ns", "library", "--max-fanout", "32", "--core-utilization", str(a.util),
            "--nickname-tag", a.inst, "--keep-workdir", str(out / "work"), "--output", str(out / "physical.json")]
    for k, v in INST[a.inst].items():
        args += ["--param", f"{k}={v}"]
    if a.local_control:
        args += ["--param", "LOCAL_CONTROL=1"]
    for kv in a.orfs_var:
        args += ["--orfs-var", kv]
    (out / "route_args.json").write_text(json.dumps(dict(args=args, source_sha256=sha(ROOT / SRC)), indent=1))
    rc = drv.main(args)
    nick = None
    for p in (out / "work").rglob("6_final.odb"):
        nick = p.parent.parent.name
        break
    sta = None
    if nick:
        sta = corner_sta(out / "work", nick, out)["signoff"]
    (out / "done.json").write_text(json.dumps(dict(route_rc=rc, nickname=nick, sta_rc=sta)) + "\n")


def cmd_stage(a):
    import shutil
    src, scr = a.src.resolve(), a.scratch.resolve()
    scr.mkdir(parents=True, exist_ok=True)
    for f in ("prepare_stage.json", "stage_cfg.svh"):
        shutil.copy(src / f, scr / f)
    if not (scr / "cfg_stage").exists():
        shutil.copytree(src / "cfg_stage", scr / "cfg_stage")
    if not (scr / "roms").exists():
        (scr / "roms").symlink_to((src / "roms").resolve())
    ctrl = scr / "ot_rom_pkg_ctrl_wfc_as_wf.sv"
    text = (ROOT / SRC).read_text().replace("module ot_rom_pkg_ctrl_wfc #(", "module ot_rom_pkg_ctrl_wf #(")
    for d in a.define:   # e.g. OT_WFC_CONTROL_PIPE=1: the copy's default for that knob
        k, v = d.split("=")
        assert f"`define {k} 0" in text, k
        text = text.replace(f"`define {k} 0", f"`define {k} {v}")
    ctrl.write_text(text)
    sys.argv = [sys.argv[0]]
    sys.path.insert(0, str(ROOT / "tools"))
    W = importlib.import_module("dsrom_wavefront_rtl_campaign")
    W.CTRL = ctrl
    os.environ["OT_WF_STAGE_WAVE"] = str(a.wave)
    rc = W.run_stage(scr)
    out = (scr / f"out_stage_w{a.wave}.txt").read_text()
    ref = (src / f"out_stage_w{a.wave}.txt").read_text() if (src / f"out_stage_w{a.wave}.txt").is_file() else None
    res = dict(rc=rc, ctrl_sha256=sha(ROOT / SRC), defines=a.define, bench_out_sha256=hashlib.sha256(out.encode()).hexdigest(),
               ref_out_sha256=hashlib.sha256(ref.encode()).hexdigest() if ref else None,
               identical_to_reference_run=(out == ref) if ref is not None else None)
    (scr / f"stage_w{a.wave}.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res))


def _screen(d):
    f = Path(d) / "screen.json"
    if not f.is_file():
        return None
    j = json.loads(f.read_text())
    return {k: j.get(k) for k in ("top", "params", "ss_setup_wns_ps", "ff_hold_wns_ps", "cell_area_um2",
                                   "worst_start", "worst_end")} | {
        "worst_stages_ps": dict(list(j.get("worst_slack_by_stage_ps", {}).items())[:8])}


def _route(d):
    d = Path(d)
    if not (d / "physical.json").is_file():
        return None
    ph = json.loads((d / "physical.json").read_text())
    de, pr = ph.get("design", {}), ph.get("place_and_route", {})
    metrics = pr.get("metrics", {})
    sta = json.loads((d / "wf_sta.json").read_text()) if (d / "wf_sta.json").is_file() else {}
    args = json.loads((d / "route_args.json").read_text()) if (d / "route_args.json").is_file() else {}
    current_sha = sha(ROOT / SRC)
    corners = sta.get("corners", {})
    ss, ff = corners.get("SS", {}), corners.get("FF", {})
    def nonnegative(corner, mode, field):
        value = corner.get(mode, {}).get(field)
        return isinstance(value, (int, float)) and value >= 0
    timing_met = bool(ss.get("done") and ff.get("done") and
                      ss.get("exit") == 0 and ff.get("exit") == 0 and
                      all(nonnegative(ss, mode, "setup_wns_ps") for mode in ("incontext", "reg2reg")) and
                      all(nonnegative(ff, mode, "hold_wns_ps") for mode in ("block", "incontext", "reg2reg")))
    drc = metrics.get("drc_errors", de.get("drc"))
    antenna = metrics.get("antenna_violating_nets", de.get("antenna"))
    integrity = {key: metrics.get(key) for key in
                 ("max_slew_violations", "max_cap_violations", "max_fanout_violations")}
    integrity_met = all(value == 0 for value in integrity.values())
    source_matches = bool(args.get("source_sha256") == current_sha)
    return dict(route_args=args or None,
                route_source_sha256=args.get("source_sha256"), current_source_sha256=current_sha,
                current_source_matches=source_matches,
                flow_completed=ph.get("flow_completed"), driver_status=ph.get("status"),
                area_um2=metrics.get("standard_cell_area_um2", de.get("area_um2")),
                core_area_um2=metrics.get("core_area_um2", de.get("core_area_um2")),
                cells=metrics.get("standard_cell_count", de.get("cells")),
                utilization=metrics.get("utilization_fraction", de.get("utilization_fraction")),
                drc=drc, antenna=antenna, signal_integrity=integrity,
                signal_integrity_clean=integrity_met,
                orfs_setup_wns_ns=metrics.get("setup_wns_ns", de.get("setup_wns_ns")),
                orfs_hold_wns_ns=metrics.get("hold_wns_ns", de.get("hold_wns_ns")),
                synth=dict((k, ph.get("synthesis", {}).get(k)) for k in ("cell_area_um2", "cell_count",
                                                                         "sequential_cell_count")),
                elapsed_s=ph.get("elapsed_seconds"),
                signoff_sta=sta, closed_incontext=sta.get("signoff", {}).get("incontext"),
                routed_surrogate_timing_met=timing_met,
                routed_surrogate_physical_met=bool(ph.get("flow_completed") and timing_met and
                                                  drc == 0 and antenna == 0 and integrity_met),
                actual_parent_completion_binding=None,
                actual_parent_context_qualified=False,
                current_controller_adoptable=False)


def cmd_record(a):
    d = a.dir.resolve()
    eq = {}
    for f in sorted(d.glob("eq*/run.log")) + sorted(d.glob("eq_icarus/*.out")):
        lines = [l for l in f.read_text(errors="replace").splitlines() if l.startswith("EQUIV")]
        eq[str(f.relative_to(d))] = lines
    stage = {w: json.loads((d / f"stage_w{w}" / f"stage_w{w}.json").read_text())
             for w in (1, 0) if (d / f"stage_w{w}" / f"stage_w{w}.json").is_file()}
    rec = dict(schema="opentallas.rtl.dsrom_wf_close.v1",
               block="ot_rom_pkg_ctrl_wf (WAVE=1) -> closed implementation ot_rom_pkg_ctrl_wfc",
               source=SRC, source_sha256=sha(ROOT / SRC),
               reference="rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv",
               reference_sha256=sha(ROOT / "rtl/rom/wavefront/ot_rom_pkg_ctrl_wf.sv"),
               instances=INST, period_ps=833, setup_uncertainty_ps=60, hold_uncertainty_ps=25,
               screens={k: _screen(d / k) for k in a.screen},
               routes={k: _route(d / k) for k in a.route},
               equivalence=eq, stage_bench=stage)
    a.out.write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps({k: (v and {kk: v.get(kk) for kk in ("closed", "area_um2", "cells")}) for k, v in rec["routes"].items()}))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route")
    r.add_argument("--inst", choices=sorted(INST), required=True)
    r.add_argument("--run-dir", type=Path, required=True)
    r.add_argument("--util", type=int, default=40)
    r.add_argument("--orfs-var", action="append", default=[])
    r.add_argument("--local-control", action="store_true", help="opt-in same-edge local group-read and queue write-bank controls")
    t = sub.add_parser("stage")
    t.add_argument("--from", dest="src", type=Path, required=True)
    t.add_argument("--scratch", type=Path, required=True)
    t.add_argument("--wave", type=int, default=1)
    t.add_argument("--define", action="append", default=[], help="KNOB=V: default of an OT_WFC_* knob in the copy")
    c = sub.add_parser("record")
    c.add_argument("--dir", type=Path, required=True)
    c.add_argument("--screen", action="append", default=[])
    c.add_argument("--route", action="append", default=[])
    c.add_argument("--out", type=Path, required=True)
    q = sub.add_parser("sta")
    q.add_argument("--run-dir", type=Path, required=True)
    a = ap.parse_args()
    if a.cmd == "sta":
        nick = next((a.run_dir / "work").rglob("6_final.odb")).parent.parent.name
        print(json.dumps(corner_sta((a.run_dir / "work").resolve(), nick, a.run_dir.resolve()), indent=1)[:4000])
        return
    {"route": cmd_route, "stage": cmd_stage, "record": cmd_record}[a.cmd](a)


if __name__ == "__main__":
    main()
