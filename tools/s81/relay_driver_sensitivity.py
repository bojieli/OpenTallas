#!/usr/bin/env python3
"""Native pin-local stronger output-driver sensitivity, preserving the CLOSED route.

Only diagnostic clone DBs/netlists/ETMs are written. Larger cells may overlap and
original RC does not describe moved pins: there is no placement/route closure or
native qualification. All payload AND fn0/fo0 clock output drivers are included.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

CANDIDATES = ['BUFx4_ASAP7_75t_R', 'BUFx8_ASAP7_75t_R', 'BUFx12f_ASAP7_75t_R', 'BUFx24_ASAP7_75t_R']


def stage(native, archive, survey, out):
    source = json.loads((native / 'stage.json').read_text())
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(native / 'base', out / 'base', dirs_exist_ok=True)
    facts = json.loads(survey.read_text())
    choices = {}
    for c in CANDIDATES + ['BUFx2_ASAP7_75t_R']:
        entries = [r for r in facts if r['cell'] == c]
        if len(entries) != 2 or not any('_TT_' in r['lib'] for r in entries) or not any('_FF_' in r['lib'] for r in entries):
            raise ValueError('missing characterized TT/FF native driver ' + c)
        choices[c] = entries
    native_view = archive / 'run' / 'record' / 'views' / 'dsfd_stnv_566x1'
    for corner in ('tt', 'ff', 'ss'):
        header = (native_view / f'export_{corner}.tcl').read_text().split('read_db ', 1)[0]
        tcl = header + '''read_db /work/base/6_final.odb
read_sdc /work/base/6_final.sdc
read_spef /work/base/6_final.spef
set_propagated_clock [all_clocks]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set drivers {}
set ports_seen {}
foreach bt [$block getBTerms] {
  set n [$bt getName]
  if {[$bt getIoType] ne "OUTPUT" || ![regexp {^(do0|fn0|fo0)\[} $n]} {continue}
  set found {}
  foreach it [[$bt getNet] getITerms] {
    if {[$it getIoType] eq "OUTPUT"} {lappend found [$it getInst]}
  }
  if {[llength $found] != 1} {error "output driver coverage failed $n"}
  set inst [lindex $found 0]
  if {[[$inst getMaster] getName] ne "BUFx2_ASAP7_75t_R"} {error "unexpected native source driver $n"}
  dict set drivers [$inst getName] $inst
  lappend ports_seen $n
}
if {[dict size $drivers] != 568 || [llength $ports_seen] != 568} {error "expected 566 data + 2 literal clock drivers"}
set f [open /work/drivers.tsv w]
foreach n [lsort [dict keys $drivers]] {
  set i [dict get $drivers $n]
  set m [$i getMaster]
  puts $f "$n [expr {[$m getWidth]/double($dbu)}] [expr {[$m getHeight]/double($dbu)}] [$i getLocation]"
}
close $f
set row_area 0
foreach row [$block getRows] {set box [$row getBBox]; set row_area [expr {$row_area + double([$box dx])*[$box dy]/$dbu/$dbu}]}
set original_area 0
set functional_area 0
foreach i [$block getInsts] {
 set m [$i getMaster]
 set a [expr {double([$m getWidth])*[$m getHeight]/$dbu/$dbu}]
 set original_area [expr {$original_area+$a}]
 if {[$m getType] ne "CORE_SPACER"} {set functional_area [expr {$functional_area+$a}]}
}
puts "OT_DRIVER_BASELINE functional_area_um2=$functional_area all_area_um2=$original_area row_area_um2=$row_area count=[dict size $drivers]"
'''
        for c in CANDIDATES:
            stem = c.split('_ASAP7')[0]
            tcl += f'''foreach n [dict keys $drivers] {{replace_cell $n {c}}}
set nm [[ord::get_db] findMaster {c}]
puts "OT_DRIVER_VARIANT {corner} {c} width_um=[expr {{[$nm getWidth]/double($dbu)}}] height_um=[expr {{[$nm getHeight]/double($dbu)}}]"
write_db /work/{stem}_{corner}.odb
write_verilog /work/{stem}_{corner}.v
write_timing_model -library_name dsfd_stnv_566x1_{corner} /work/{stem}_{corner}.lib
report_checks -path_delay max -format full_clock_expanded -group_path_count 1
report_check_types -max_slew -max_capacitance -violators
'''
        tcl += 'puts OT_DRIVER_SENSITIVITY_DONE\n'
        (out / f'{corner}.tcl').write_text(tcl)
    (out / 'run.sh').write_text('''#!/bin/bash
set -eu
B=$(cd "$(dirname "$0")" && pwd)
for c in tt ff ss; do
 docker run --rm --cpus=1 -v "$B":/work openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 1 -no_init -exit /work/$c.tcl > /work/$c.log 2>&1; chmod -R a+rwX /work"
 grep -q OT_DRIVER_SENSITIVITY_DONE "$B/$c.log"
done
''')
    receipt = dict(schema='opentallas.relay_driver_sensitivity_stage.v1', source_native_stage_sha256=hashlib.sha256((native/'stage.json').read_bytes()).hexdigest(),
                   source_job=source['job'], source_consumed=source['consumed'], driver_libs=choices,
                   scope='Unrouted native output buffer substitution sensitivity ONLY; 566 data and 2 clock outputs, no RTL cycle change, larger cells may overlap, RC/pin positions not re-extracted; original CLOSED route intact')
    (out/'stage.json').write_text(json.dumps(receipt, indent=2))
    print('staged four native driver choices, TT+FF+SS sensitivity; no routing or native qualification')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','archive','survey','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();stage(a.native,a.archive,a.survey,a.out)


if __name__=='__main__':main()
