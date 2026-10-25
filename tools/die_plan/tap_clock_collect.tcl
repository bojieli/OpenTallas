# Read-only one-corner actual-CTS collector. Run only after checkpoint/image approval.
# OT_CC_KIT, OT_CC_ODB, OT_CC_OUT, OT_CORNER=TT|FF. No ETM or physical edits.
foreach key {OT_CC_KIT OT_CC_ODB OT_CC_OUT OT_CORNER} {
  if {![info exists ::env($key)]} {error "OT_CC missing $key"}
}
set kit $::env(OT_CC_KIT); set out $::env(OT_CC_OUT); set corner $::env(OT_CORNER)
if {$corner ni {TT FF}} {error "OT_CC only TT/FF supported"}
if {[file tail $::env(OT_CC_ODB)] ne "4_cts.odb"} {error "OT_CC requires terminal 4_cts.odb"}
file mkdir $out
read_db $::env(OT_CC_ODB)
# Use the canonical native-kit exact selector (dea197bb09). Installed-library
# globs can silently mix SIMPLE/SEQ generations and invalidate measurements.
set helper [file join [file dirname [info script]] timing_libs.tcl]
if {![file isfile $helper]} {error "OT_CC requires exact native timing_libs.tcl selector"}
source $helper
set libs [ot_lib_load $corner $out/libraries_${corner}.json $kit/config.mk]
if {[llength $libs] != 5} {error "OT_CC expected this macro-free kit's exact five standard-cell libraries"}
read_sdc $kit/constraint.sdc
set root [get_clocks -quiet clk]
if {[llength $root] != 1 || abs([get_property $root period]-833.0)>0.01} {error "OT_CC expected actual clk at833ps"}
set sources {}; foreach src [get_property $root sources] {lappend sources [get_full_name $src]}
if {$sources ne {tile_clk}} {error "OT_CC physical root source must be tile_clk, got $sources"}
# Preserve the configured virtual-clock binding and original 60/25ps constraints.
set fd [open $kit/config.mk]; set cfg [read $fd]; close $fd
if {![regexp -line "^export OT_VCLK_${corner} = (\\S+)" $cfg -> bound]} {error "OT_CC missing configured vclk bound"}
foreach c [all_clocks] {if {[get_full_name $c] ne "clk"} {set_clock_latency -source $bound $c}}
source $kit/setRC_rcx.tcl
set_propagated_clock $root
estimate_parasitics -placement
source $kit/clock_family.tcl
set ::ot_ps_lib_only 1
source $kit/pair_skew.tcl
ot_cf_refresh
sta::worst_slack_cmd max; sta::worst_slack_cmd min
set ::ot_ps_method tag
set block [ord::get_db_block]
foreach inst [$block getInsts] {if {[[$inst getMaster] isBlock]} {error "OT_CC vehicle unexpectedly has hard macro [$inst getName]"}}
proc cc_group {net seen} {
  if {$net eq "NULL" || $net eq ""} {error "OT_CC disconnected clock"}
  set name [$net getName]
  if {$name in $seen} {error "OT_CC clock net cycle $name"}
  lappend seen $name; set drivers {}
  foreach bt [$net getBTerms] {if {[$bt getIoType] eq "INPUT"} {lappend drivers ROOT}}
  foreach it [$net getITerms] {if {[$it isOutputSignal]} {lappend drivers $it}}
  if {[llength $drivers] != 1} {error "OT_CC clock $name has [llength $drivers] drivers"}
  set driver [lindex $drivers 0]
  if {$driver eq "ROOT"} {return ROOT}
  set inst [$driver getInst]; set nm [$inst getName]
  if {[regexp {^ot_dtap_([0-9]+)$} $nm]} {return $nm}
  if {![regexp {^(BUF|INV|HB)} [[$inst getMaster] getName]]} {error "OT_CC unsupported clock-path cell $nm"}
  set inputs {}; foreach it [$inst getITerms] {if {[$it isInputSignal] && [[$it getMTerm] getSigType] ni {POWER GROUND}} {lappend inputs $it}}
  if {[llength $inputs] != 1} {error "OT_CC nonunique clock buffer input $nm"}
  return [cc_group [[lindex $inputs 0] getNet] $seen]
}
set groups {}; set netreports {}; set taps 0
set ff [open $out/clock_pins_${corner}.tsv w]
puts $ff "group\tclass\tpin\tclock\tactive\tearly_ps\tlate_ps"
lassign [ot_cf_pins $root] pins owners
if {![llength $pins]} {error "OT_CC no actual clock pins"}
set bnd {}; set regs {}
foreach pin $pins {dict set regs [ot_ps_inst [get_full_name $pin]] $pin}
foreach pin [get_fanout -from [all_inputs -no_clocks] -flat -endpoints_only -trace_arcs all] {
  set nm [ot_ps_inst [get_full_name $pin]]; if {[dict exists $regs $nm]} {dict set bnd $nm I}
}
foreach pin [get_fanin -to [all_outputs] -flat -startpoints_only -trace_arcs all] {
  set nm [ot_ps_inst [get_full_name $pin]]; if {[dict exists $regs $nm]} {dict set bnd $nm [expr {[dict exists $bnd $nm] ? "IO" : "O"}]}
}
foreach pin $pins {
  set pn [get_full_name $pin]; set nm [ot_ps_inst $pn]
  set inst [$block findInst $nm]
  set it [$inst findITerm [lindex [split $pn /] end]]
  if {$it eq "NULL"} {error "OT_CC absent physical CK $pn"}
  set grp [cc_group [$it getNet] {}]
  set edge [ot_cf_active $pin]
  if {$edge ne "rise"} {error "OT_CC unexpected nonrise sequential pin $pn"}
  set late [ot_cf_wire $pin [dict get $owners $pn]]
  set early [ot_ps_ckarr $pin [dict get $owners $pn] min]
  if {$early eq ""} {error "OT_CC missing early clock arrival $pn"}
  set class [expr {[dict exists $bnd $nm] ? [dict get $bnd $nm] : "CORE"}]
  puts $ff [join [list $grp $class $pn clk $edge $early $late] \t]
  dict lappend groups $grp [list $early $late $class]
}
close $ff
set tf [open $out/taps_${corner}.tsv w]
puts $tf "group\tdirection\tpin\tlate_ps\tnet"
foreach inst [$block getInsts] {
  if {![regexp {^ot_dtap_[0-9]+$} [$inst getName]]} continue
  incr taps
  foreach it [$inst getITerms] {
    if {[[$it getMTerm] getSigType] in {POWER GROUND}} continue
    set pn "[$inst getName]/[[$it getMTerm] getName]"; set pin [get_pins -quiet $pn]
    if {[llength $pin]!=1} {error "OT_CC tap pin missing $pn"}
    set clocks [get_property $pin clocks]
    if {[llength $clocks]!=1 || [ot_cf_root [get_full_name [lindex $clocks 0]]] ne "clk"} {error "OT_CC tap clock ambiguous $pn"}
    set late [ot_cf_wire_transition $pin [lindex $clocks 0] rise]
    puts $tf [join [list [$inst getName] [[$it getMTerm] getIoType] $pn $late [[$it getNet] getName]] \t]
    set net [get_nets -quiet [[$it getNet] getName]]
    if {![llength $net]} {error "OT_CC tap physical net not present in STA $pn"}
    # Native report carries actual total/pin/wire capacitance and immediate fanout.
    report_net -connections -verbose $net > $out/load_${corner}_[$inst getName]_[[$it getMTerm] getName].rpt
  }
}
close $tf
if {$taps != 35} {error "OT_CC expected35 actual density taps, got$taps"}
# Include density taps with no surviving sinks; never silently omit a group.
foreach inst [$block getInsts] {
  set nm [$inst getName]
  if {[regexp {^ot_dtap_[0-9]+$} $nm] && ![dict exists $groups $nm]} {dict set groups $nm {}}
}
set sf [open $out/summary_${corner}.tsv w]
puts $sf "corner\tgroup\tpins\tmin_ps\tmax_ps\tmean_ps\tpinreg_n\tpinreg_mean_ps"
dict for {grp rows} $groups {
  set late {}; set early {}; set pr {}
  foreach row $rows {lappend early [lindex $row 0]; lappend late [lindex $row 1]; if {[lindex $row 2] ne "CORE"} {lappend pr [lindex $row 1]}}
  if {![llength $rows]} {puts $sf [join [list $corner $grp 0 NA NA NA 0 NA] \t]; continue}
  set sum [tcl::mathop::+ {*}$late]; set pm NA
  if {[llength $pr]} {set pm [expr {[tcl::mathop::+ {*}$pr]/double([llength $pr])}]}
  puts $sf [join [list $corner $grp [llength $rows] [tcl::mathfunc::min {*}$early] [tcl::mathfunc::max {*}$late] [expr {$sum/double([llength $rows])}] [llength $pr] $pm] \t]
}
close $sf
# Record original SDC and WNS before pair_skew's documented isolated uncertainty-zero measurement.
write_sdc $out/loaded_${corner}.sdc
report_checks -path_delay max -group_path_count 5 -format full_clock_expanded > $out/checks_${corner}_max.rpt
report_checks -path_delay min -group_path_count 5 -format full_clock_expanded > $out/checks_${corner}_min.rpt
set ::env(CORNER) $corner; set ::env(OT_PS_OUT) $out/pair_skew_${corner}.tsv
ot_ps_main
puts "OT_CC_DONE $corner taps$taps pins[llength $pins] (CTS placement RC only)"
exit
