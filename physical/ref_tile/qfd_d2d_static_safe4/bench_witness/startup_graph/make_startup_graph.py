from pathlib import Path
p=Path(__file__).parent
prefix=(p/'d2d_baseline_electrical_ff.tcl').read_text().split('read_db ')[0]
body=(p/'control_independent_audit_body.tcl').read_text().split('set out [open /data/control16_')[0]
body+='''
set f [open /data/control16_actual_startup_equations.tsv w]
foreach i [$audit_block getInsts] {
 set m [[$i getMaster] getName]
 if {[control_transparent $m]} continue
 puts $f [join [list MASTER [$i getName] $m] \\t]
 foreach t [$i getITerms] {
  if {![$t isInputSignal]} continue
  puts $f [join [list INPUT [$i getName] [[$t getMTerm] getName] [control_canon [$t getNet] 0]] \\t]
 }
}
foreach t [$audit_block getBTerms] {
 if {[$t getIoType] eq "OUTPUT"} {puts $f [join [list OUTPUT [$t getName] [control_canon [$t getNet] 0]] \\t]}
}
close $f
puts "STARTUP_GRAPH actual_unaliased_nontransparent_equations=1 timing_rerun=0 mutation=0"
exit
'''
(p/'d2d_startup_graph.tcl').write_text(prefix+'read_db /data/eclock_control16_sramclk_hold_final_ff.odb\n'+body)
