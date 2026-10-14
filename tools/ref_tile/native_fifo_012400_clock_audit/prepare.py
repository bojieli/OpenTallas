from pathlib import Path
import json
p=Path('/tmp/native-012400-audit');core=(p/'frozen_path_classes.tcl').read_text();ck=json.loads((p/'ck.json').read_text());measure=ck['clock_measurements'];expected={pin['pin']:source for source,m in measure.items() for pin in m['tt']['macros']['pins']};assert len(expected)==5
old=Path('/tmp/native-010028-audit/audit.tcl').read_text();extra=old[old.index('puts "NATIVE_AUDIT_CLOCKS"'):old.index('write_sdc')]
extra+='''
proc physical_source {net} {
 set seen [dict create]
 for {set depth 0} {$depth<64} {incr depth} {
  set id [$net getId];if {[dict exists $seen $id]} {error "physical clock cycle"};dict set seen $id 1
  set roots {};foreach b [$net getBTerms] {if {[$b getIoType] eq "INPUT"} {lappend roots [$b getName]}}
  if {[llength $roots]} {if {[llength $roots]!=1} {error "ambiguous clock source"};return [lindex $roots 0]}
  set drivers {};foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend drivers $it}}
  if {[llength $drivers]!=1} {error "missing/ambiguous physical clock driver"}
  set i [[lindex $drivers 0] getInst];set kind [[$i getMaster] getName]
  if {![string match BUF* $kind] && ![string match INV* $kind] && $kind ne "HB4xp67_ASAP7_75t_R"} {error "unknown physical clock driver $kind"}
  set inputs {};foreach it [$i getITerms] {if {[$it isInputSignal]} {lappend inputs $it}}
  if {[llength $inputs]!=1} {error "non-scalar clock buffer"}
  set net [[lindex $inputs 0] getNet]
 }
 error "physical clock depth exceeded"
}
proc root_metrics {tag} {
 foreach {clock source} {core_clk ck ckd ckd} {
  set pins [all_registers -clock_pins -clock [get_clocks $clock]]
  set sum 0.0;set min 1e30;set max -1e30;set count 0
  foreach pin $pins {
   set a [get_property $pin arrival_max_rise]
   if {![string is double -strict $a] || abs($a)>1e20} {error "unmeasured root pin"}
   set sum [expr {$sum+$a}];set min [expr {min($min,$a)}];set max [expr {max($max,$a)}];incr count
  }
  if {$count==0} {error "empty root"}
  puts "FIXED_ROOT $tag $source n=$count mean=[expr {$sum/$count}] min=$min max=$max"
 }
 puts "FIXED_WNS $tag setup=[sta::worst_slack_cmd max] hold=[sta::worst_slack_cmd min]"
}
'''
for pin,source in expected.items():
 inst,mp=pin.rsplit('/',1);extra+=f'''set i [$block findInst {{{inst}}}]
set it [$i findITerm {mp}]
set owner [physical_source [$it getNet]]
if {{$owner ne "{source}"}} {{error "wrong macro clock owner {pin}"}}
puts "FIXED_MACRO CORNER_NAME {{{pin}}} owner=$owner"
report_arrival -digits 6 [get_pins {{{pin}}}]
report_slews -digits 6 [get_pins {{{pin}}}]
'''
extra+='''root_metrics CORNER_NAME_source150
set baseline_setup [sta::worst_slack_cmd max]
set baseline_hold [sta::worst_slack_cmd min]
# Sensitivity only, fixed baseline IO/reference budgets. Not source qualification.
set_input_transition 0 [get_ports ckd]
root_metrics CORNER_NAME_source0_fixed_original_IO
set_input_transition 150 [get_ports ckd]
root_metrics CORNER_NAME_restored150
if {abs([sta::worst_slack_cmd max]-$baseline_setup)>1e-16 || abs([sta::worst_slack_cmd min]-$baseline_hold)>1e-16} {error "source150 restore differs"}
write_sdc /out/executed_CORNER_NAME.sdc
puts "FIXED_NATIVE_PASS CORNER_NAME actual150_clock_source_and_macro_owners"
exit
'''
for c in ['tt','ff','ss']:
 clone=core
 if c!='tt':
  clone=clone.replace('RVT_TT','RVT_'+c.upper()).replace('set ::ot_ce_corner tt','set ::ot_ce_corner '+c)
  needle='foreach w [lrange [split $l " ="] 1 end] {';assert needle in clone
  clone=clone.replace(needle,needle+f'\n    set w [string map {{_tt.lib _{c}.lib}} $w]')
  clone=clone.replace('catch {read_liberty $f}','read_liberty $f').replace('catch {read_liberty $w}','read_liberty $w')
 (p/f'canonical_{c}.tcl').write_text(clone)
 (p/f'audit_{c}.tcl').write_text('set ::env(OT_GATE_SIGNOFF_SDC) /src/physical/ref_tile/qfd_coll_xfifo_native/signoff.sdc\nsource /out/canonical_'+c+'.tcl\n'+extra.replace('CORNER_NAME',c))
(p/'expected_macro_owners.json').write_text(json.dumps(expected,indent=2)+'\n')
(p/'run_all.sh').write_text('''#!/bin/bash
set -euo pipefail
root=/srv/opentallas-scratch/claude/ref_gate/qfd_coll_xfifo_native-20261014-012400
image=sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
docker image inspect "$image" > /tmp/native-012400-audit/image_inspect.json
for c in tt ff ss; do
 docker run --rm -v "$root/routes/gate/work/orfs:/work:ro" -v "$root/src:/src:ro" -v /tmp/native-012400-audit:/out "$image" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "/out/audit_$c.tcl" > "/tmp/native-012400-audit/audit_$c.receipt.log" 2>&1
 grep -q "FIXED_NATIVE_PASS $c" "/tmp/native-012400-audit/audit_$c.receipt.log"
done
''')
print('PREPARED 3corner canonical + 5 actual macro owners, source150 baseline/restoration')
