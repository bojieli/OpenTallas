#!/usr/bin/env python3
"""PINFLOP-REF overlay (drive-0849 2026-10-10): bring a job snapshot's route-time IO reference SDCs up to the pin-flop
default of main 6cd79a9f8 (physical/qwen_die_masters/pinflop_ref.tcl) whatever the job's source commit, the way
tt_overlay.py brings the corner rule.  Patches, idempotently, in <SRC>:
  physical/qwen_die_masters/io_ref_skew.sdc        no / unmatched REFGLOB -> median input pin flop (else first register)
  physical/qwen_die_masters/mc/*/io_ref_skew.sdc   per clock: median pin flop of that clock's inputs
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
  foreach c [get_cells -quiet -hierarchical $ot_glob] {
    set p [get_pins -quiet "[get_full_name $c]/CLK"]
    if {[llength $p]} { set qdm_ref $p; break }
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


def patch(text, procs):
    if "proc ot_pf_ref" in text:
        # 6cd79a9f8-era snapshot: upgrade the glob test so REFGLOB='*' (no named reference) also gets the pin flops
        return text.replace(GLOB_OLD, GLOB_NEW, 1) if GLOB_OLD in text else None
    if text.count(MAIN_OLD) == 1:
        return text.replace(MAIN_OLD, procs + MAIN_NEW, 1)
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
