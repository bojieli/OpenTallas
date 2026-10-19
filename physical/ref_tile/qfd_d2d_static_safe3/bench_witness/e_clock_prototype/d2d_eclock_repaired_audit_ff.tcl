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
ep_struct ff
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

ep_snapshot repaired_reload_ff
check_placement -verbose
set targets {}

foreach name [dict keys $bnd] {
 set inst [sta::sta_to_db_inst [dict get $regs $name]]
 set box [$inst getBBox];set x [expr {([$box xMin]+[$box xMax])/2.0/$units}];set y [expr {([$box yMin]+[$box yMax])/2.0/$units}]
 if {475.2-$x<15 && 475.2-$x<$y && 475.2-$x<280.8-$y} {dict set targets $name 1}
}
if {[dict size $targets]!=64} {error "repaired E population mismatch"}
set ep_Emin 1e20;set ep_Emax -1e20;set ep_Omin 1e20;set ep_Omax -1e20
set Ecp {};set Edp {};set Ocp {};set Odp {};set async {}
foreach pin [all_registers -async_pins] {dict set async [get_full_name $pin] 1}
foreach pin [all_registers -clock_pins] {
 set cell [get_full_name [get_cells -of_objects $pin]]
 if {[dict exists $targets $cell]} {lappend Ecp $pin} else {lappend Ocp $pin}
}
foreach pin [all_registers -data_pins] {
 if {[dict exists $async [get_full_name $pin]]} continue
 set cell [get_full_name [get_cells -of_objects $pin]]
 if {[dict exists $targets $cell]} {lappend Edp $pin} else {lappend Odp $pin}
}
foreach name [dict keys $bnd] {
 set pin [lindex [get_pins -of_objects [dict get $regs $name] -filter "direction==input && is_clock"] 0]
 set a [get_property $pin arrival_max_rise]
 if {[dict exists $targets $name]} {
  set ep_Emin [expr {min($ep_Emin,$a)}];set ep_Emax [expr {max($ep_Emax,$a)}]
 } else {
  set ep_Omin [expr {min($ep_Omin,$a)}];set ep_Omax [expr {max($ep_Omax,$a)}]
 }
}
set bounds {}
foreach label {E_to_other other_to_E} from [list $Ecp [concat $Ocp [all_inputs -no_clocks]]] to [list [concat $Odp [all_outputs]] $Edp] {
 foreach kind {min max} {
  set worst 1e20;set witness {}
  foreach path [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1 -endpoint_path_count 1] {
   set slack [get_property $path slack]
   if {$slack<$worst} {set worst $slack;set witness "[get_full_name [get_property $path startpoint]] -> [get_full_name [get_property $path endpoint]]"}
  }
  if {$worst>1e19} {error "E_CLOCK intervalmissingactualpath $label $kind"}
  dict set bounds $label $kind $worst
  puts "E_CLOCK_PATH_CLASS $label $kind slack_ps=$worst witness=$witness"
  report_checks -from $from -to $to -path_delay $kind -group_path_count 1 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 4
 }
}
set lo_spread [expr {$ep_Omax-80-$ep_Emin}]
set hi_spread [expr {$ep_Omin+80-$ep_Emax}]
set lo_data [expr {max(30-[dict get $bounds E_to_other min],-[dict get $bounds other_to_E max])}]
set hi_data [expr {min([dict get $bounds E_to_other max],[dict get $bounds other_to_E min]-30)}]
puts "E_CLOCK_INTERVAL actual_E=$ep_Emin..$ep_Emax actual_other=$ep_Omin..$ep_Omax uniform_delta_spread_ps=$lo_spread..$hi_spread uniform_delta_data_setup0_hold30_ps=$lo_data..$hi_data admissible_delta_ps=[expr {max($lo_spread,$lo_data)}]..[expr {min($hi_spread,$hi_data)}] phase/reserve_policy=UNCHANGED"


foreach label {E_to_E other_to_other port_to_port} from [list $Ecp [concat $Ocp [all_inputs -no_clocks]] [all_inputs -no_clocks]] to [list $Edp [concat $Odp [all_outputs]] [all_outputs]] {
 foreach kind {min max} {
  set ps [find_timing_paths -from $from -to $to -path_delay $kind -group_path_count 1]
  if {![llength $ps]} {puts "E_CLOCK_PATH_CLASS $label $kind no_path=1";continue}
  puts "E_CLOCK_PATH_CLASS $label $kind slack_ps=[get_property [lindex $ps 0] slack]"
  report_checks -from $from -to $to -path_delay $kind -group_path_count 1 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 4
 }
}
set ep_cache {};set out [open /data/repaired_ff_clockpaths.tsv w]
foreach c [all_registers -cells] {
 set i [sta::sta_to_db_inst $c];set term [$i findITerm CLK]
 if {$term eq "NULL"} continue
 set paths [ep_path [$term getNet]];set masters {};foreach n $paths {lappend masters [[[$b findInst $n] getMaster] getName]}
 puts $out [join [list [$i getName] [dict exists $targets [$i getName]] [llength $paths] $paths $masters] \t]
}
close $out
report_check_types -max_slew -max_capacitance -max_fanout -violators -digits 4
puts "E_CLOCK_REPAIRED_RELOAD corner=ff diagnostic_only=1 SDC/reserves/ports/FFedges=UNCHANGED"
