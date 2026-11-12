#!/usr/bin/env python3
"""Read-only replay of core_tap_align OT_DTAP_ALIGN_ROBUST on a finished CTS log (HBM-CORES-B 11-12, class hbm-dtap-pad-depth).

usage: python3 -I dtap_replay.py 4_1_cts.log [pct] [outlier_ps]
Reads the r0 tap means (OT_DTAP_ALIGN r0 line, measured before any alignment cell) and each density tap net sink count
(CTS-0010 lines), runs the SAME Tcl procs as core_tap_align.tcl (extracted from the file, executed by tclsh) and prints, per
root, the predicted padding for the r0-max target and for the robust target.  No OpenROAD, no database writes."""
import re, subprocess, sys
from pathlib import Path

SRC = Path(__file__).with_name("core_tap_align.tcl").read_text()


def proc(name):
    i = SRC.index(f"proc {name} ")
    return SRC[i:SRC.index("\n}\n", i) + 3]


def load(log):
    t = Path(log).read_text()
    m = re.search(r"OT_DTAP_ALIGN r0 (.*?)\|", t)
    if not m:
        sys.exit("no OT_DTAP_ALIGN r0 line")
    means = {k: float(v) for k, v in re.findall(r"(\d+)=(\d+)\(", m.group(1))}
    cts = t[t.rfind("clock_tree_synthesis"):]
    sinks = {k: int(v) for k, v in re.findall(r"ot_dtap_net_(\d+)\" has (\d+) sinks", cts)}
    return means, sinks


def main():
    log = sys.argv[1]
    pct = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
    outps = float(sys.argv[3]) if len(sys.argv) > 3 else 40.0
    means, sinks = load(log)
    rec = " ".join("ot_dtap_%s {%s 0 0 %d}" % (k, v, sinks.get(k, 1)) for k, v in means.items())
    tcl = "\n".join(proc(n) for n in ("ta_root_of", "ta_main_root", "ta_robust_target", "ta_outliers", "ta_predict")) + f"""
set m [dict create {rec}]
set lead [dict create]
set mx 0.0; dict for {{n v}} $m {{ set mx [expr {{max($mx, [lindex $v 0])}}] }}
set tg [ta_robust_target $m $lead {pct} 2]
set out [ta_outliers $m $lead $tg {outps}]
puts "TARGET max [format %.1f $mx] robust [format %.1f $tg] main_root [ta_main_root $m] outliers [llength $out]: $out"
foreach {{tag t sk}} [list max $mx {{}} robust $tg $out] {{
  dict for {{r v}} [ta_predict $m $lead $t 15.3 $sk] {{ lassign $v nt c s x; puts "PRED $tag root $r taps $nt cells $c pad_sum_ps [format %.0f $s] pad_max_ps [format %.0f $x]" }}
}}
"""
    p = subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True)
    sys.stdout.write(p.stdout + p.stderr)
    sys.exit(p.returncode)


main()
