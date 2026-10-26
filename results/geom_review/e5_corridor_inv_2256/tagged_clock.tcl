foreach f [lsort [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_*_RVT_TT_nldm_*.lib*]] {read_liberty $f}
foreach f [glob /work/macros/*_tt.lib] {read_liberty $f}
read_db /work/run/results/asap7/kr_dsdv_eng_rr_e_e5corr2144/base/4_cts.odb
read_sdc /work/constraint.sdc
source /work/setRC_rcx.tcl
set_propagated_clock [all_clocks]
estimate_parasitics -placement
find_timing_paths -group_path_count 1
source /work/clock_family.tcl
ot_cf_refresh
set clk [get_clocks clk];set b [ord::get_db_block]
proc io {i dir} {foreach p [$i getITerms] {if {[[$p getMTerm] getIoType] eq $dir && [[$p getMTerm] getSigType] ni {POWER GROUND}} {return $p}};error "no clockcell $dir"}
proc dep {i} {
 set n [$i getName];if {[dict exists $::depth $n]} {return [dict get $::depth $n]}
 set net [[io $i INPUT] getNet]
 if {[llength [$net getBTerms]]} {set d 1} else {
  set p "";foreach it [$net getITerms] {if {[$it isOutputSignal]} {set p [$it getInst];break}}
  if {$p eq ""} {error "missing actual parent $n"}
  set d [expr {1+[dep $p]}]
 }
 dict set ::depth $n $d;return $d
}
proc lp_cap {i it} {
 set m [[$i getMaster] getName];set p [[$it getMTerm] getName]
 set vals {};foreach l [get_lib_pins -quiet */$m/$p] {if {![catch {get_property $l capacitance} c]} {lappend vals $c}}
 if {![llength $vals]} {return NA};return [lindex $vals 0]
}
set f [open /work/tagged_trunk_tt.tsv w]
puts $f "name\tmaster\tdepth\tin_edge\tout_edge\tin_ps\tout_ps\tcell_ps\tout_slew_ps\tfanout\tload_pin_cap_ff"
set ::depth {}
foreach i [$b getInsts] {
 if {![string match ot_dtsh_* [$i getName]]} continue
 set d [dep $i];set in [io $i INPUT];set out [io $i OUTPUT]
 set ti [expr {$d%2 ? "rise":"fall"}];set to [expr {$d%2 ? "fall":"rise"}]
 set ip [get_pins [$i getName]/[[$in getMTerm] getName]];set op [get_pins [$i getName]/[[$out getMTerm] getName]]
 set ai [ot_cf_wire_transition $ip $clk $ti];set ao [ot_cf_wire_transition $op $clk $to]
 set s [get_property $op slew_max_$to];set n 0;set cap 0.0
 foreach it [[$out getNet] getITerms] {if {[$it isInputSignal]} {incr n;set c [lp_cap [$it getInst] $it];if {$c ne "NA"} {set cap [expr {$cap+$c}]}}}
 puts $f "[$i getName]\t[[$i getMaster] getName]\t$d\t$ti\t$to\t$ai\t$ao\t[expr {$ao-$ai}]\t$s\t$n\t$cap"
}
close $f
set f [open /work/tagged_taps_tt.tsv w]
puts $f "tap\tgeneric_rise_ps\ttagged_root_rise_ps\tdifference_ps"
set lo 1e99;set hi -1e99
foreach i [$b getInsts] {
 if {![regexp {^ot_dtap_[0-9]+$} [$i getName]]} continue
 set p [get_pins [$i getName]/[[[io $i INPUT] getMTerm] getName]]
 set a [get_property $p arrival_max_rise];set t [ot_cf_wire_transition $p $clk rise]
 puts $f "[$i getName]\t$a\t$t\t[expr {$a-$t}]"
 set lo [expr {min($lo,$t)}];set hi [expr {max($hi,$t)}]
}
close $f
foreach m {INVx13_ASAP7_75t_R BUFx24_ASAP7_75t_R} {foreach p [get_lib_pins -quiet */$m/A] {puts "CLOCK_INPUT_CAP [get_full_name $p] [get_property $p capacitance]"}}
puts "TAGGED_TAP_RANGE_TT $lo $hi spread[expr {$hi-$lo}]"
