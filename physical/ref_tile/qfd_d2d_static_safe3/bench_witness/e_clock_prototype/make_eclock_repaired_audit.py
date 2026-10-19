from pathlib import Path
p=Path('/home/ubuntu/scratch/codex-qw-ctlm-cones')
struct=r'''
proc ep_origin {net {seen {}}} {
 if {$net eq "NULL"} {return OPEN}
 set name [$net getName]
 if {$name in $seen} {error "canonical buffer loop $name"}
 lappend seen $name
 set ds {};foreach t [$net getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds]==0} {set out {};foreach t [$net getBTerms] {lappend out PORT:[$t getName]};return [lsort $out]}
 if {[llength $ds]!=1} {error "canonical multidriver $name"}
 set t [lindex $ds 0];set i [$t getInst];set m [[$i getMaster] getName]
 if {[string match BUF* $m] || [string match *INV* $m]} {
  set ins {};foreach a [$i getITerms] {if {[$a getIoType] eq "INPUT" && [$a getSigType] ni {POWER GROUND}} {lappend ins $a}}
  if {[llength $ins]==1} {set result [ep_origin [[lindex $ins 0] getNet] $seen];if {[string match *INV* $m]} {return [list INV $result]};return $result}
 }
 return [list PIN:[$i getName]/[[$t getMTerm] getName]]
}
proc ep_struct {label} {
 set block [ord::get_db_block];set out [open /data/repaired_${label}_structure.tsv w]
 foreach i [$block getInsts] {puts $out [join [list INST [$i getName] [[$i getMaster] getName] [$i getLocation] [$i getOrient]] \t]}
 foreach t [$block getBTerms] {puts $out [join [list PORT [$t getName] [$t getIoType] [$t getSigType]] \t]}
 set rcount 0
 foreach c [all_registers -cells] {
  set i [sta::sta_to_db_inst $c];incr rcount
  foreach t [$i getITerms] {if {[$t getIoType] eq "INPUT" && [$t getSigType] ni {POWER GROUND}} {puts $out [join [list FF_INPUT [$i getName] [[$t getMTerm] getName] [ep_origin [$t getNet]]] \t]}}
 }
 close $out
 puts "E_CLOCK_STRUCTURE label=$label regs=$rcount insts=[llength [$block getInsts]] ports=[llength [$block getBTerms]]"
}
'''
for corner in ('tt','ff'):
 s=(p/f'd2d_eclock_three_stage_{corner}.tcl').read_text()
 prefix=s.split('ep_snapshot before\n')[0]
 prefix=prefix.replace('read_db $base/4_1_cts.odb',struct+'\nread_db $base/4_1_cts.odb\nep_struct baseline\nread_db /data/eclock_three_stage_ff_hold_repaired.odb\nep_struct '+corner)
 out=prefix+'\nep_snapshot repaired_reload_'+corner+'\ncheck_placement -verbose\nset targets {}\n'
 out+=r'''
foreach name [dict keys $bnd] {
 set inst [sta::sta_to_db_inst [dict get $regs $name]]
 set box [$inst getBBox];set x [expr {([$box xMin]+[$box xMax])/2.0/$units}];set y [expr {([$box yMin]+[$box yMax])/2.0/$units}]
 if {475.2-$x<15 && 475.2-$x<$y && 475.2-$x<280.8-$y} {dict set targets $name 1}
}
if {[dict size $targets]!=64} {error "repaired E population mismatch"}
'''
 out+=s[s.index('set ep_Emin 1e20'):s.index('# Verify every target')]
 out+=r'''
foreach label {E_to_E other_to_other port_to_port} from [list $Ecp [concat $Ocp [all_inputs -no_clocks]] [all_inputs -no_clocks]] to [list $Edp [concat $Odp [all_outputs]] [all_outputs]] {
 foreach kind {min max} {
  set ps [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1]
  if {![llength $ps]} {puts "E_CLOCK_PATH_CLASS $label $kind no_path=1";continue}
  puts "E_CLOCK_PATH_CLASS $label $kind slack_ps=[get_property [lindex $ps 0] slack]"
  report_checks -from $from -to $to -path_delay $kind -group_path_count 1 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 4
 }
}
set ep_cache {};set out [open /data/repaired_CORNER_clockpaths.tsv w]
foreach c [all_registers -cells] {
 set i [sta::sta_to_db_inst $c];set term [$i findITerm CLK]
 if {$term eq "NULL"} continue
 set paths [ep_path [$term getNet]];set masters {};foreach n $paths {lappend masters [[[$b findInst $n] getMaster] getName]}
 puts $out [join [list [$i getName] [dict exists $targets [$i getName]] [llength $paths] $paths $masters] \t]
}
close $out
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 4
puts "E_CLOCK_REPAIRED_RELOAD corner=CORNER diagnostic_only=1 SDC/reserves/ports/FFedges=UNCHANGED"
'''.replace('CORNER',corner)
 (p/f'd2d_eclock_repaired_audit_{corner}.tcl').write_text(out)
