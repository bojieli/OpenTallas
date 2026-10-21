# Focused causal guard tests invoking the production cohort resolver. The tiny
# OpenDB-shaped fixture tests membership/guards, not physical signoff or CTS.
source [file join [file dirname [info script]] ../../../physical/common_flow/clock_spine_cohorts.tcl]
proc object {name values} {
  dict set ::objects $name $values
  if {[info commands $name] eq ""} {interp alias {} $name {} dispatch $name}
}
proc dispatch {obj method args} {
  if {![dict exists $::objects $obj $method]} {error "unsupported fixture call $obj $method"}
  return [dict get $::objects $obj $method]
}
proc fixture {} {
 set ::objects [dict create]
 object master [dict create isBlock 0 getName DFFASRHQNx1_ASAP7_75t_R]
 object clkpin [dict create getName CLK]
 object qpin [dict create getName QN]
 object resetpin [dict create getName RESETN]
 object datap [dict create getName D]
 object src [dict create getName src getMaster master getITerms {sc sq}]
 object dst [dict create getName dst getMaster master getITerms {dc dr}]
 object sc [dict create getInst src getIoType INPUT getMTerm clkpin getNet clknet getAvgXY {1 0 0}]
 object dc [dict create getInst dst getIoType INPUT getMTerm clkpin getNet clknet getAvgXY {1 100 100}]
 object sq [dict create getInst src getIoType OUTPUT getMTerm qpin getNet reset]
 object dr [dict create getInst dst getIoType INPUT getMTerm resetpin getNet reset]
 object reset [dict create getITerms {sq dr}]
 object clknet [dict create getITerms {sc dc}]
 object blk [dict create getInsts {src dst}]
 set ::ot_sp_cohorts [list [dict create name local source src receivers dst]]
}
proc expect {name needle body} {
 fixture
 set code [catch {uplevel 1 $body} msg]
 if {$needle eq "PASS"} {
   if {$code} {error "$name unexpected failure: $msg"}
 } elseif {!$code || [string first $needle $msg] < 0} {error "$name expected '$needle', got '$msg'"}
 puts "PASS $name"
}
expect default_absent PASS {unset ::ot_sp_cohorts; if {[dict size [ot_sp_cohort_bins blk clknet 1 16]]} {error changed}}
expect default_empty PASS {set ::ot_sp_cohorts {}; if {[dict size [ot_sp_cohort_bins blk clknet 1 16]]} {error changed}}
expect valid_exact PASS {set b [ot_sp_cohort_bins blk clknet 1 16]; if {[llength [dict get $b C:local]]!=2} {error membership}}
expect missing_source "source must match exactly one" {dict set ::objects src getName changed; ot_sp_cohort_bins blk clknet 1 16}
expect missing_receiver "missing receiver" {set ::ot_sp_cohorts [list [dict create name local source src receivers absent]]; ot_sp_cohort_bins blk clknet 1 16}
expect oversized "exceed LEAF_N" {ot_sp_cohort_bins blk clknet 1 1}
expect too_far "405um" {dict set ::objects dc getAvgXY {1 406 0}; ot_sp_cohort_bins blk clknet 1 16}
expect boundary405 PASS {dict set ::objects dc getAvgXY {1 405 0}; ot_sp_cohort_bins blk clknet 1 16}
expect crossroot "cross-root" {dict set ::objects clknet getITerms sc; ot_sp_cohort_bins blk clknet 1 16}
expect wrong_connection "direct async-reset" {dict set ::objects dr getNet unrelated; ot_sp_cohort_bins blk clknet 1 16}
expect data_connection "direct async-reset" {dict set ::objects dr getMTerm datap; ot_sp_cohort_bins blk clknet 1 16}
expect unplaced "unplaced" {dict set ::objects dc getAvgXY {0 0 0}; ot_sp_cohort_bins blk clknet 1 16}
expect duplicate_group "duplicate name" {lappend ::ot_sp_cohorts [lindex $::ot_sp_cohorts 0]; ot_sp_cohort_bins blk clknet 1 16}
expect overlap "overlapping member" {lappend ::ot_sp_cohorts [dict create name other source src receivers dst]; ot_sp_cohort_bins blk clknet 1 16}
expect duplicate_receiver "overlapping receiver" {set ::ot_sp_cohorts [list [dict create name local source src receivers {dst dst}]];ot_sp_cohort_bins blk clknet 1 16}
expect undeclared_receiver "undeclared immediate" {object extra [dict create getName extra];object er [dict create getIoType INPUT getMTerm resetpin getInst extra];dict set ::objects reset getITerms {sq dr er};ot_sp_cohort_bins blk clknet 1 16}
expect source_fanout "32 dynamic loads" {object data [dict create getIoType INPUT getMTerm datap getInst dst];dict set ::objects reset getITerms [concat {sq dr} [lrepeat 32 data]];ot_sp_cohort_bins blk clknet 1 16}
expect unknown_master "unsupported sequential" {dict set ::objects master getName UNKNOWN;ot_sp_cohort_bins blk clknet 1 16}
expect data_as_clock "data clock input" {dict set ::objects sc getMTerm datap;ot_sp_cohort_bins blk clknet 1 16}
expect wrong_source_output "supported source QN" {dict set ::objects sq getMTerm datap;ot_sp_cohort_bins blk clknet 1 16}
expect grouping PASS {
 set original [dict create b0 {{sc 0 0} {other 10 10}} b1 {{dc 100 100}} b2 {{untouched 200 200}}]
 if {[ot_sp_cohort_merge_bins $original {}] ne $original} {error "default bin bytes changed"}
 set c [ot_sp_cohort_bins blk clknet 1 16]
 set b [ot_sp_cohort_merge_bins $original $c]
 if {[dict get $b b0] ne {{other 10 10}} || [dict get $b b2] ne [dict get $original b2]} {error "undeclared bins changed"}
 if {[dict exists $b b1] || [dict get $b C:local] ne [dict get $c C:local]} {error "not atomic/exactly once"}
}
expect duplicate_spatial_sink "appears 2 times" {ot_sp_cohort_merge_bins [dict create b {{sc 0 0} {sc 0 0} {dc 100 100}}] [ot_sp_cohort_bins blk clknet 1 16]}
expect missing_spatial_sink "appears 0 times" {ot_sp_cohort_merge_bins [dict create b {{sc 0 0}}] [ot_sp_cohort_bins blk clknet 1 16]}
puts "PASS cohort cases=23; physical/clock paired signoff remains integration-owned"
