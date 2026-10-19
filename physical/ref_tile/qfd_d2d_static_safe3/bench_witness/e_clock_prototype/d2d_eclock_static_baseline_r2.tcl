# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain /work/objects/asap7/*/base/lib/*.lib $plat/lib/NLDM/*RVT_TT*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w] && [file exists $w]} { catch {read_liberty $w} }
  }
}

proc ep_origin {net {seen {}}} {
 if {$net eq "NULL"} {return OPEN}
 set name [$net getName]
 if {$name in $seen} {error "canonical buffer loop $name"}
 lappend seen $name
 set ds {};foreach t [$net getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend ds $t}}
 if {[llength $ds]==0} {set out {};foreach t [$net getBTerms] {lappend out PORT:[$t getName]};return [lsort $out]}
 if {[llength $ds]!=1} {error "canonical multidriver $name"}
 set t [lindex $ds 0];set i [$t getInst];set m [[$i getMaster] getName]
 if {[string match BUF* $m] || $m eq "HB4xp67_ASAP7_75t_R" || [string match *INV* $m]} {
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

read_db $base/4_1_cts.odb
set b [ord::get_db_block]
ep_struct baseline_hb
proc ep_driver {net} {
 set drivers {}
 foreach t [$net getITerms] {if {[$t getIoType] eq "OUTPUT"} {lappend drivers $t}}
 if {[llength $drivers]==0 && [llength [$net getBTerms]]>0} {return ""}
 if {[llength $drivers]!=1} {error "E_CLOCK multidriver/open [$net getName]"}
 return [lindex $drivers 0]
}
proc ep_input {inst} {
 set inputs {}
 foreach t [$inst getITerms] {if {[$t getIoType] eq "INPUT" && [$t getSigType] ni {POWER GROUND}} {lappend inputs $t}}
 if {[llength $inputs]!=1} {error "E_CLOCK nonbuffer input [$inst getName]"}
 return [lindex $inputs 0]
}
proc ep_path {net} {
 global ep_cache
 set n [$net getName]
 if {[dict exists $ep_cache $n]} {return [dict get $ep_cache $n]}
 set d [ep_driver $net]
 if {$d eq ""} {set answer {}} else {
  set inst [$d getInst];set master [[$inst getMaster] getName]
  if {![string match BUF* $master] && ![string match *INV* $master]} {error "E_CLOCK nonbufferclock $master"}
  set answer [linsert [ep_path [[ep_input $inst] getNet]] 0 [$inst getName]]
 }
 dict set ep_cache $n $answer
 return $answer
}


set ep_cache {};set out [open /data/baseline_clockpaths_static.tsv w]
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
  if {[string match BUF* $m] || $m eq "HB4xp67_ASAP7_75t_R" || [string match *INV* $m]} continue
  set root [ep_origin [$t getNet]];dict incr counts $root
 }
}
set maxload 0;set violations 0;set outputs 0;set out [open /data/baseline_native_ff_fanout.tsv w]
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
puts "E_CLOCK_NATIVE_FANOUT label=baseline ff_outputs=$outputs maximum_terminal_load=$maxload outputs_over32=$violations open_power_ground_pins=$openpg exact_buffer_collapsed=1"
check_placement -verbose
