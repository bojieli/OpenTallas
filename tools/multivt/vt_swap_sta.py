#!/usr/bin/env python3
"""MULTI-VT (2026-10-07): same-hour upper bound of what a threshold-voltage swap buys on an EXISTING route.

Takes a routed block's own sign-off STA load (the w18_sta_ss.tcl / w18_sta_ff.tcl that tools/w18/corner_sta.py or
corner_sta_ref.py wrote into the ORFS dir: libs, LEFs, macros, odb, SDC, SPEF, post-SDCs), adds the ASAP7 LVT and SLVT
libraries/LEFs of the same corner, and then, with the routed SPEF kept (ASAP7 R/L/SL cells are geometry-identical: the
LEFs differ only in the VT implant OBS layer, so a footprint-for-footprint swap moves no pin, wire or DRC shape):

  phase LVT : repeat <= ROUNDS: every standard cell on every setup path with slack < TARGET (report_checks text, the
              launching register included) -> its _L twin; stop when SS WS >= TARGET or nothing new to swap
  phase SLVT: from the LVT state, the same with _R/_L -> _SL (the LVT+SLVT variant)

and reports per phase: SS setup WS/TNS/violators (signoff SDC), FF hold WS on the SAME swapped netlist (FF libs of
every VT), cell counts per VT (fillers/taps excluded) and report_power at TT (all VTs' TT libs; activity stated in the
record).  Nothing is written into the route: the ORFS dir and the source tree are mounted read-only.

    vt_swap_sta.py --orfs-dir <dir holding w18_sta_ss.tcl> --src <job src> --out <dir> [--target 15] [--rounds 8]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

IMAGE = "openroad/orfs:asap7lock"
PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
OR = "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad"
VTS = {"R": "RVT", "L": "LVT", "SL": "SLVT"}

SWAP_PROCS = r"""
set ot_blk [ord::get_db_block]
set ot_db [ord::get_db]
proc ot_vt_counts {} {
  set c [dict create R 0 L 0 SL 0]
  foreach i [$::ot_blk getInsts] {
    set m [[$i getMaster] getName]
    if {[regexp {^(FILLER|TAPCELL|DECAP)} $m]} continue
    if {[regexp {_ASAP7_75t_(R|L|SL)$} $m -> v]} { dict incr c $v }
  }
  return $c
}
proc ot_report {tag check} {
  puts "OTVT_$tag ws=[sta::worst_slack_cmd $check] tns=[sta::total_negative_slack_cmd $check] vt=[ot_vt_counts]"
}
# swap the cells on the violating setup paths (text report: PathEnd properties crash this OpenROAD build)
proc ot_swap_round {to target npaths log} {
  set f /tmp/ot_vt_paths.rpt
  report_checks -path_delay max -group_path_count $npaths -endpoint_path_count 1 -unique_paths_to_endpoint \
    -slack_max $target -format full > $f
  set fh [open $f r]; set txt [read $fh]; close $fh
  set n 0
  foreach line [split $txt "\n"] {
    if {![regexp {\s(\S+)/[^/\s]+\s+\((\S+)_ASAP7_75t_(R|L|SL)\)\s*$} $line -> inst base vt]} continue
    if {$vt eq $to} continue
    if {$to eq "L" && $vt eq "SL"} continue
    set di [$::ot_blk findInst $inst]
    if {$di eq "NULL" || $di eq ""} continue
    set cur [[$di getMaster] getName]
    if {![regexp {_ASAP7_75t_(R|L|SL)$} $cur -> cv] || $cv eq $to || ($to eq "L" && $cv eq "SL")} continue
    set nm [$::ot_db findMaster "${base}_ASAP7_75t_$to"]
    if {$nm eq "NULL" || $nm eq ""} continue
    $di swapMaster $nm
    puts $log "$inst ${base}_ASAP7_75t_$to"
    incr n
  }
  return $n
}
proc ot_phase {to target rounds npaths logfile} {
  set log [open $logfile w]
  for {set r 1} {$r <= $rounds} {incr r} {
    set ws [expr {[sta::worst_slack_cmd max] * 1e12}]
    if {$ws >= $target} break
    set n [ot_swap_round $to $target $npaths $log]
    puts "OTVT_ROUND $to $r swapped=$n ws_before=$ws ws_after=[expr {[sta::worst_slack_cmd max] * 1e12}]"
    if {$n == 0} break
  }
  close $log
}
proc ot_apply {logfile} {
  if {![file exists $logfile]} return
  set fh [open $logfile r]
  foreach line [split [read $fh] "\n"] {
    if {[llength $line] != 2} continue
    set di [$::ot_blk findInst [lindex $line 0]]
    set nm [$::ot_db findMaster [lindex $line 1]]
    if {$di ne "NULL" && $di ne "" && $nm ne "NULL" && $nm ne ""} { $di swapMaster $nm }
  }
  close $fh
}
"""


def load_part(tcl: str, corner: str) -> str:
    """The sign-off load of w18_sta_<corner>.tcl, with every VT of the corner and the LVT/SLVT LEFs added."""
    head = tcl.split('puts "OT_CORNER', 1)[0]
    out = []
    for line in head.splitlines():
        m = re.match(rf"read_liberty ({re.escape(PLAT)}/lib/NLDM/asap7sc7p5t_\w+?)_RVT_(SS|FF|TT)_(\S+)$", line)
        if m:
            for vt in VTS.values():
                out.append(f"read_liberty {m.group(1)}_{vt}_{m.group(2)}_{m.group(3)}")
            continue
        out.append(line)
        if line.startswith("read_db "):
            for t in ("L", "SL"):
                out.append(f"read_lef -library {PLAT}/lef/asap7sc7p5t_28_{t}_1x_220121a.lef")
    return "\n".join(out) + "\n"


def tt_load(ss_load: str, src: Path) -> str:
    """TT view for power: std-cell SS libs -> TT; a macro's _ss.lib -> _tt.lib when it exists, else dropped (its
    leakage is then not in the total; recorded as such)."""
    out = []
    for line in ss_load.splitlines():
        if line.startswith("read_liberty") and "/lib/NLDM/" in line:
            line = line.replace("_SS_", "_TT_")
        elif line.startswith("read_liberty /src/") and line.endswith("_ss.lib"):
            tt = line[len("read_liberty /src/"):-len("_ss.lib")] + "_tt.lib"
            line = f"read_liberty /src/{tt}" if (src / tt).is_file() else f"# no TT view: {line}"
        out.append(line)
    return "\n".join(out) + "\n"


POWER = """
set_power_activity -input -activity 0.1 -duty 0.5
report_power -digits 6 > /tmp/ot_pw.rpt
set fh [open /tmp/ot_pw.rpt r]; set t [read $fh]; close $fh
foreach l [split $t "\\n"] { if {[regexp {^Total\\s} $l]} { puts "OTVT_POWER_$tag $l" } }
"""


def run_tcl(orfs: Path, src: Path, out: Path, name: str, body: str) -> str:
    (out / f"{name}.tcl").write_text(body)
    cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work:ro", "-v", f"{src}:/src:ro", "-v", f"{out}:/out",
           IMAGE, "bash", "-lc", f"{OR} -no_init -exit /out/{name}.tcl"]
    p = subprocess.run(cmd, capture_output=True, text=True)
    log = (p.stdout or "") + (p.stderr or "")
    (out / f"{name}.log").write_text(log)
    return log


def parse(log: str) -> dict:
    r = {}
    for m in re.finditer(r"^OTVT_(\w+) ws=(\S+) tns=(\S+) vt=(.*)$", log, re.M):
        kv = m.group(4).split()
        r[m.group(1)] = dict(ws_ps=round(float(m.group(2)) * 1e12, 2), tns_ps=round(float(m.group(3)) * 1e12, 1),
                             vt=dict(zip(kv[::2], map(int, kv[1::2]))))
    for m in re.finditer(r"^OTVT_POWER_(\w+) Total\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", log, re.M):
        r.setdefault("power", {})[m.group(1)] = dict(internal_w=float(m.group(2)), switching_w=float(m.group(3)),
                                                    leakage_w=float(m.group(4)), total_w=float(m.group(5)))
    r["rounds"] = re.findall(r"^OTVT_ROUND .*$", log, re.M)
    r["errors"] = re.findall(r"\[ERROR[^\n]*", log)[:5]
    return r


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--target", type=float, default=15.0, help="ps")
    ap.add_argument("--rounds", type=int, default=8)
    ap.add_argument("--npaths", type=int, default=20000)
    ap.add_argument("--setup-corner", choices=("ss", "tt"), default="ss",
                    help="corner of the setup search/verify sessions (owner 2026-10-07 option B: setup signs off at TT); "
                         "tt = the SS sign-off load with TT std-cell libraries and the macros' _tt.lib views")
    ap.add_argument("--extra-setup-sdc", type=Path, default=None,
                    help="an SDC read after the setup load (e.g. physical/common_flow/link_budget_consistent.sdc: the "
                         "option-B die-link budget the TT re-status applies); setup sessions only")
    a = ap.parse_args(argv)
    orfs, src, out = a.orfs_dir.resolve(), a.src.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    ss = load_part((orfs / "w18_sta_ss.tcl").read_text(), "ss")
    ss_power = ss
    if a.setup_corner == "tt":
        ss = tt_load(ss, src)
    if a.extra_setup_sdc:
        shutil.copy(a.extra_setup_sdc, out / "extra_setup.sdc")
        ss += "read_sdc /out/extra_setup.sdc\n"
    ff = load_part((orfs / "w18_sta_ff.tcl").read_text(), "ff")
    t = a.target
    rec = dict(schema="opentallas.multivt.vt_swap_sta.v1", orfs_dir=str(orfs), target_ps=t, rounds=a.rounds,
               setup_corner=a.setup_corner,
               extra_setup_sdc=str(a.extra_setup_sdc) if a.extra_setup_sdc else None)
    ls = run_tcl(orfs, src, out, "ss", ss + SWAP_PROCS + f"""
ot_report RVT max
ot_phase L {t} {a.rounds} {a.npaths} /out/swap_L.txt
ot_report LVT max
ot_phase SL {t} {a.rounds} {a.npaths} /out/swap_SL.txt
ot_report LVT_SLVT max
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
exit
""")
    rec["ss_setup"] = parse(ls)
    # every check of a swapped netlist in a FRESH session (swaps applied before any timing/power query): the
    # incremental swap session above is the search only (report_power after swapMaster in one session mis-propagates)
    applies = {"RVT": "", "LVT": "ot_apply /out/swap_L.txt\n",
               "LVT_SLVT": "ot_apply /out/swap_L.txt\not_apply /out/swap_SL.txt\n"}
    tt = tt_load(ss_power, src)
    jobs = []
    for tag, ap_ in applies.items():
        jobs.append(("ff", tag, ff + SWAP_PROCS + ap_ + f"ot_report {tag} min\n"
                     "report_checks -path_delay min -group_path_count 1 -format full_clock_expanded\nexit\n"))
        if tag != "RVT":
            jobs.append(("ssv", tag, ss + SWAP_PROCS + ap_ + f"ot_report {tag} max\n"
                         "report_checks -path_delay max -group_path_count 1 -format full_clock_expanded\nexit\n"))
        jobs.append(("tt", tag, tt + SWAP_PROCS + ap_ + f"set tag {tag}\n" + POWER + "exit\n"))
    with ThreadPoolExecutor(len(jobs)) as ex:
        logs = list(ex.map(lambda j: (j[0], run_tcl(orfs, src, out, f"{j[0]}_{j[1]}", j[2])), jobs))
    rec["ff_hold"], rec["ss_verify"], rec["tt_power"] = {}, {}, {}
    for kind, log in logs:
        p_ = parse(log)
        if kind == "tt":
            rec["tt_power"].update(p_.get("power") or {})
        else:
            dst = rec["ff_hold"] if kind == "ff" else rec["ss_verify"]
            dst.update({k: v for k, v in p_.items() if k not in ("rounds", "errors", "power")})
            dst.setdefault("errors", []).extend(p_["errors"])
    rec["tt_macro_views_missing"] = re.findall(r"# no TT view: (.*)", tt)
    if a.setup_corner == "tt" and rec["tt_macro_views_missing"]:
        rec["warning"] = "TT setup timed with a macro lacking a TT view (its liberty dropped): setup result incomplete"
    rec["activity"] = "OpenSTA vectorless: primary inputs toggle density 0.1, duty 0.5, propagated; clocks from SDC"
    rec["area_change_um2"] = 0.0
    rec["area_basis"] = "ASAP7 R/L/SL LEFs are identical except the VT implant OBS layer (diff = 0 after renaming)"
    (out / "vt_swap_sta.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec, indent=1))


if __name__ == "__main__":
    main()
