# pre_route_gate.py --cts: worst setup path classes after CTS (placement parasitics).  Run in the ORFS image with the
# case dir at /work: groups the 300 worst setup endpoints by (start kind -> end kind), kind = in (port), reg, macro,
# out (port), and prints one GATE_PC line per class with the count and the worst slack.
# CROSS-CLOCK GATE (CX-IJ-ROOT 10-18): exception recorders first, so every read_sdc below is seen; GATE_XCLK at the end
set base [lindex [glob /work/results/asap7/*/base] 0]
set plat /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $plat/lef/asap7_tech_1x_201209.lef
read_lef $plat/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob -nocomplain $plat/lib/NLDM/*RVT_FF*] { catch {read_liberty $f} }
foreach l [split [exec sh -c "grep -h 'ADDITIONAL_LEFS\\|ADDITIONAL_LIBS' /work/config.mk || true"] "\n"] {
  foreach w [lrange [split $l " ="] 1 end] {
    if {[string match *.lef $w] && [file exists $w]} { catch {read_lef $w} }
    if {[string match *.lib $w]} {set w [string map {_tt.lib _ff.lib} $w];if {![file exists $w]} {error "missingactualFFlib $w"};read_liberty $w}
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

read_db /data/eclock_three_stage_ff_hold_repaired.odb
if {[file exists $base/4_cts.sdc]} { read_sdc $base/4_cts.sdc } else { read_sdc $base/3_place.sdc }
set_propagated_clock [all_clocks]
source $plat/setRC.tcl
estimate_parasitics -placement
# Classify the same die-context boundary constraints as signoff, after RC is
# available. The saved CTS SDC alone can restore plain, primary-clock IO budgets.
if {[info exists ::env(OT_GATE_SIGNOFF_SDC)]} {
  set ot_pc_sdc $::env(OT_GATE_SIGNOFF_SDC)
  if {![file isfile $ot_pc_sdc]} { error "GATE_PC: missing signoff SDC $ot_pc_sdc" }
  set ::ot_ce_corner ff
  read_sdc $ot_pc_sdc
  puts "GATE_PC constraints signoff $ot_pc_sdc (FF placement RC; diagnostic)"
} else {
  puts "GATE_PC constraints saved CTS SDC (diagnostic; no signoff boundary replay)"
}

foreach kind {min max} {find_timing_paths -path_delay $kind -group_path_count 1}
set regs {}
foreach cell [all_registers -clock core_clk -cells] {dict set regs [get_full_name $cell] $cell}

set bnd {}
set ot_ck_data {}
set ot_ck_async {}
foreach p [all_registers -async_pins] { dict set ot_ck_async [get_full_name $p] 1 }
foreach p [all_registers -data_pins] {
  set n [get_full_name $p]
  if {![dict exists $ot_ck_async $n]} { dict set ot_ck_data $n 1 }
}
set din [all_inputs -no_clocks]
if {[llength $din]} {
  foreach p [get_fanout -from $din -flat -endpoints_only -trace_arcs all] {
    set n [get_full_name $p]
    if {![dict exists $ot_ck_data $n]} continue
    set i [regsub {/[^/]+$} $n {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}
set dout [all_outputs]
if {[llength $dout]} {
  foreach p [get_fanin -to $dout -flat -startpoints_only -trace_arcs all] {
    set i [regsub {/[^/]+$} [get_full_name $p] {}]
    if {[dict exists $regs $i]} { dict set bnd $i 1 }
  }
}

set b [ord::get_db_block];set units [$b getDbUnitsPerMicron]
 
proc ep_connect {term net} {
 set inst [$term getInst];set istouch [$inst isDoNotTouch]
 set old [$term getNet];set oldtouch 0;set newtouch [$net isDoNotTouch]
 if {$old ne "NULL"} {set oldtouch [$old isDoNotTouch]}
 if {$istouch} {$inst setDoNotTouch false}
 if {$oldtouch} {$old setDoNotTouch false}
 if {$newtouch} {$net setDoNotTouch false}
 try {
  if {$old ne "NULL"} {odb::dbITerm_disconnect $term}
  odb::dbITerm_connect $term $net
 } finally {
  if {$oldtouch} {$old setDoNotTouch true}
  if {$newtouch} {$net setDoNotTouch true}
  if {$istouch} {$inst setDoNotTouch true}
 }
}
proc ep_snapshot {label} {
 global bnd regs
 foreach kind {min max} {find_timing_paths -path_delay $kind -group_path_count 1}
 set lo 1e20;set hi -1e20;set count 0
 foreach name [dict keys $bnd] {
  set cell [dict get $regs $name]
  set pin [lindex [get_pins -of_objects $cell -filter "direction==input && is_clock"] 0]
  set a [get_property $pin arrival_max_rise]
  if {[regexp -nocase {inf|nan} $a]} {error "E_CLOCK nonfinite $name"}
  if {$a<$lo} {set lo $a;set lname $name}
  if {$a>$hi} {set hi $a;set hname $name}
  incr count
 }
 puts "E_CLOCK_SNAPSHOT $label boundary=$count min=$lo mincell=$lname max=$hi maxcell=$hname spread=[expr {$hi-$lo}] setup_s=[sta::worst_slack_cmd max] hold_s=[sta::worst_slack_cmd min]"
}
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


set ::ot_control_copy_regexp {.}
set ::ot_control_copy_manifest /data/control16_replica_manifest.tcl
source /data/same_edge_control_copies.tcl
write_db /data/eclock_control16_prelegal_ff.odb
source /data/prune_unobserved_buffers.tcl
global_connect
detailed_placement
check_placement -verbose
estimate_parasitics -placement
read_sdc $::env(OT_GATE_SIGNOFF_SDC)
set_propagated_clock [all_clocks]
ep_snapshot after_recursive_control_replication
write_db /data/eclock_control16_ff.odb
puts "CONTROL_REPLICA_PROTOTYPE_DONE diagnostic_only=1 adoption=0"
