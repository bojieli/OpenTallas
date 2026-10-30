from pathlib import Path
import json
r=Path('/srv/opentallas-scratch2/claude/codex-s81types-1030/iqf_current_bind/ff_fixture');k=r/'preserve';names=json.load(open(k/'fixture434_names.json'))
def tq(s):return '"'+s.replace('\\','\\\\').replace('"','\\"').replace('$','\\$').replace('[','\\[').replace(']','\\]')+'"'
t=['# ROOT-authorized fixture-only one actual long D net; no FF/BUF dont-touch policy.','set fixture_candidates [list '+' '.join(tq(n) for n in names)+']',r'''
set fixture_selected "";set fixture_distance 0;set fixture_selected_target ""
foreach name $fixture_candidates {
 set i [[ord::get_db_block] findInst $name]
 set d [$i findITerm D];set net [$d getNet];set drivers {}
 foreach p [$net getITerms] {if {[$p getIoType] eq "OUTPUT"} {lappend drivers [$p getInst]}}
 if {[llength $drivers]!=1 || [$net isDoNotTouch]} continue
 set driver [lindex $drivers 0];set a [$driver getBBox];set b [$i getBBox]
 set distance [expr {(abs(([$a xMin]+[$a xMax]-[$b xMin]-[$b xMax])/2.0)+abs(([$a yMin]+[$a yMax]-[$b yMin]-[$b yMax])/2.0))/[[ord::get_db_tech] getDbUnitsPerMicron]}]
 if {$distance>$fixture_distance} {set fixture_distance $distance;set fixture_selected $net;set fixture_selected_target $name}
}
if {$fixture_selected eq "" || $fixture_distance<=50.0} {error "FIXTURE no actual long repairable selected D net; preserve held, no global fallback"}
set fixture_saved {}
foreach net [[ord::get_db_block] getNets] {
 if {[$net getName] eq [$fixture_selected getName] || [$net isDoNotTouch]} continue
 $net setDoNotTouch 1
 lappend fixture_saved $net
}
puts "FIXTURE_SCOPE_ONE_ACTUAL_DNET target=$fixture_selected_target net=[$fixture_selected getName] length_um=$fixture_distance protected_other_nets=[llength $fixture_saved]"
set fixture_f [open $::env(RESULTS_DIR)/fixture_scoped_Dnet.tsv w]
puts $fixture_f "$fixture_selected_target\t[$fixture_selected getName]\t$fixture_distance\t[llength $fixture_saved]"
close $fixture_f
try {
 estimate_parasitics -placement
 repair_design -max_wire_length 50 -verbose
} finally {
 foreach net $fixture_saved {$net setDoNotTouch 0}
}
puts "FIXTURE_SCOPE_DNT_RESTORED all temporary other-net flags cleared; preexisting flags retained; no FF flags changed"
''']
(k/'fixture_scope_repair.tcl').write_text('\n'.join(t)+'\n')
p=k/'fixture_force_repair.tcl';old=p.read_text();(k/'fixture_force_repair.ORIGINAL_GLOBAL.txt').write_text(old);p.write_text('source /work/fixture_snapshot.tcl\nfile rename -force $::env(RESULTS_DIR)/fixture434_postresize.tsv $::env(RESULTS_DIR)/fixture434_preforced.tsv\nsource /work/fixture_scope_repair.tcl\nsource /work/fixture_snapshot.tcl\n')
print('futurepreservePOST_RESIZE hook scoped ONE nativeDnet; default/currentGPL untouched')
