#!/usr/bin/env python3
"""PINFLOP-REF overlay (drive-0849 2026-10-10): bring a job snapshot's route-time IO reference SDCs up to the pin-flop
default of main 6cd79a9f8 (physical/qwen_die_masters/pinflop_ref.tcl) whatever the job's source commit, the way
tt_overlay.py brings the corner rule.  Patches, idempotently, in <SRC>:
  physical/qwen_die_masters/io_ref_skew.sdc        no / unmatched REFGLOB -> median input pin flop (else first register)
  physical/qwen_die_masters/mc/*/io_ref_skew.sdc   per clock: median pin flop of that clock's inputs
PF-HOLDPAD (NATIVE-REF 2026-10-18): a file already carrying an older generation of the procs (3-hop search, raw
hard-child clock pin arrival) has them replaced by PROCS_TCL's, and its reference arrival reads go through ot_pf_arr
(pin arrival + a hard child's internal insertion).
Sign-off SDCs are untouched.  usage: pinflop_overlay.py SRC PROCS_TCL   (prints one line per patched file)"""
import sys
from pathlib import Path

MAIN_OLD = '''set qdm_ref {}
foreach c [get_cells -quiet -hierarchical $ot_glob] {
  set p [get_pins -quiet "[get_full_name $c]/CLK"]
  if {[llength $p]} { set qdm_ref $p; break }
}
if {[llength $qdm_ref] == 0} { set qdm_ref [lindex [all_registers -clock_pins] 0] }
'''
MAIN_NEW = '''set qdm_ref {}
if {$ot_glob ne "" && $ot_glob ne "*"} {   ;# "*" names no reference: PINFLOP default
  set ot_gm {}
  foreach c [get_cells -quiet -hierarchical $ot_glob] {
    set p [get_pins -quiet "[get_full_name $c]/CLK"]
    if {[llength $p]} { lappend ot_gm $p }
  }
  if {[llength $ot_gm]} {
    if {[info exists ::env(OT_REF_PINFLOP)] && $::env(OT_REF_PINFLOP) eq "0"} { set qdm_ref [lindex $ot_gm 0] } else {
      set qdm_ref [ot_pf_median $ot_gm "REFGLOB $ot_glob"] }
  }
}
if {[llength $qdm_ref] == 0} { set qdm_ref [ot_pf_ref [all_inputs -no_clocks]] }
if {[llength $qdm_ref] == 0} { set qdm_ref [lindex [all_registers -clock_pins] 0] }
'''
KIT_OLD = '  set ref [lindex [all_registers -clock $clk -clock_pins] 0]\n'
KIT_NEW = ('  set ref {}\n  if {[llength $ins]} { set ref [ot_pf_ref [get_ports $ins]] }\n'
           '  if {![llength $ref]} { set ref [lindex [all_registers -clock $clk -clock_pins] 0] }\n')


GLOB_OLD = 'if {$ot_glob ne ""} {\n'
GLOB_NEW = 'if {$ot_glob ne "" && $ot_glob ne "*"} {   ;# "*" names no reference: PINFLOP default\n'


FALLBACK = "if {[llength $qdm_ref] == 0} { set qdm_ref [lindex [all_registers -clock_pins] 0] }"


MARK = "PF-HOLDPAD"
ARR = [("get_property $qdm_ref arrival_max_rise", "ot_pf_arr $qdm_ref max"),
       ("get_property $qdm_ref arrival_min_rise", "ot_pf_arr $qdm_ref min"),
       ("get_property $ref arrival_max_rise", "ot_pf_arr $ref max"),
       ("get_property $ref arrival_min_rise", "ot_pf_arr $ref min")]


def proc_end(lines, i):
    """index of the closing column-0 brace of the proc whose header is lines[i]"""
    return next(k for k in range(i + 1, len(lines)) if lines[k] == "}")


def refresh(text, procs):
    """PF-HOLDPAD: replace an older generation of the ot_pf_* procs by PROCS' and route the reference arrival reads
    through ot_pf_arr; None when nothing changes"""
    if MARK in text or "proc ot_pf_clks" not in text:
        return None
    lines = text.split("\n")
    i = next(k for k, l in enumerate(lines) if l.startswith("proc ot_pf_clks"))
    a = next((k for k in range(i - 1, -1, -1) if lines[k].startswith("# PINFLOP-REF (drive")), i)
    last = max(k for k, l in enumerate(lines) if l.startswith(("proc ot_pf_ref", "proc ot_pf_median")))
    b = proc_end(lines, last)
    out = "\n".join(lines[:a] + procs.rstrip("\n").split("\n") + lines[b + 1:])
    for o, n in ARR:
        out = out.replace(o, n)
    return out


def patch(text, procs):
    new = patch_gen(text, procs)
    if new is not None:
        r = refresh(new, procs)
        if MARK in procs and MARK in new:     # procs inserted by patch_gen: arrival reads only
            for o, n in ARR:
                new = new.replace(o, n)
        return new if r is None else r
    return refresh(text, procs)


def patch_gen(text, procs):
    lines = text.split("\n")
    if "proc ot_pf_median" not in text and "set qdm_ref {}" in lines and FALLBACK in lines:
        # the main die-master SDC, any generation (original / 6cd79a9f8 / e353cae1b): replace everything from the
        # PINFLOP-REF comment (or the reference selection) to the first-register fallback with the current procs +
        # selection (glob median, '*' = no reference, pin-flop default)
        a = next((i for i, l in enumerate(lines) if l.startswith("# PINFLOP-REF (drive")), lines.index("set qdm_ref {}"))
        b = lines.index(FALLBACK)
        return "\n".join(lines[:a] + procs.rstrip("\n").split("\n") + MAIN_NEW.rstrip("\n").split("\n") + lines[b + 1:])
    if "proc ot_pf_ref" in text:
        return None
    if text.count(KIT_OLD) == 1 and "$ins" in text:
        lines = text.split("\n")
        i = next(i for i, l in enumerate(lines) if not l.startswith("#"))
        return ("\n".join(lines[:i]) + "\n" + procs + "\n".join(lines[i:])).replace(KIT_OLD, KIT_NEW, 1)
    return None


def main(src, procs_path):
    procs = Path(procs_path).read_text()
    d = Path(src) / "physical/qwen_die_masters"
    for f in [d / "io_ref_skew.sdc", *sorted(d.glob("mc/*/io_ref_skew.sdc"))]:
        if f.is_file():
            new = patch(f.read_text(), procs)
            if new is not None:
                f.write_text(new)
                print(f"PINFLOP-REF overlay: {f.relative_to(src)}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
