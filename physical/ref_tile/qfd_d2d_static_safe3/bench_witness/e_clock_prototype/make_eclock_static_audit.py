from pathlib import Path
p=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones');s=(p/'d2d_eclock_repaired_audit_tt.tcl').read_text();head=s.split('read_db /data/')[0];procs=s[s.index('proc ep_driver'):s.index('ep_snapshot repaired_reload')]
for label,db in [('baseline','$base/4_1_cts.odb'),('repaired','/data/eclock_three_stage_ff_hold_repaired.odb')]:
 out=head+'read_db '+db+'\nset b [ord::get_db_block]\n'+procs+r'''
set ep_cache {};set out [open /data/LABEL_clockpaths_static.tsv w]
foreach c [all_registers -cells] {
 set i [sta::sta_to_db_inst $c];set term [$i findITerm CLK];if {$term eq "NULL"} continue
 set paths [ep_path [$term getNet]];set masters {};foreach n $paths {lappend masters [[[$b findInst $n] getMaster] getName]}
 puts $out [join [list [$i getName] [llength $paths] $paths $masters] \t]
}
close $out
set counts {};set openpg 0
foreach i [$b getInsts] {
 set m [[$i getMaster] getName]
 foreach t [$i getITerms] {
  if {[$t getSigType] in {POWER GROUND}} {if {[$t getNet] eq "NULL"} {incr openpg};continue}
  if {[$t getIoType] ne "INPUT"} continue
  if {[string match BUF* $m] || [string match *INV* $m]} continue
  set root [ep_origin [$t getNet]];dict incr counts $root
 }
}
set maxload 0;set violations 0;set outputs 0;set out [open /data/LABEL_native_ff_fanout.tsv w]
foreach c [all_registers -cells] {
 set i [sta::sta_to_db_inst $c]
 foreach t [$i getITerms] {
  if {[$t getIoType] ne "OUTPUT" || [$t getSigType] in {POWER GROUND}} continue
  set key [list PIN:[$i getName]/[[$t getMTerm] getName]];set n 0;if {[dict exists $counts $key]} {set n [dict get $counts $key]}
  incr outputs;set maxload [expr {max($maxload,$n)}];if {$n>32} {incr violations}
  puts $out [join [list [$i getName] [[$t getMTerm] getName] $n] \t]
 }
}
close $out
puts "E_CLOCK_NATIVE_FANOUT label=LABEL ff_outputs=$outputs maximum_terminal_load=$maxload outputs_over32=$violations open_power_ground_pins=$openpg exact_buffer_collapsed=1"
check_placement -verbose
'''.replace('LABEL',label)
 (p/f'd2d_eclock_static_{label}.tcl').write_text(out)
