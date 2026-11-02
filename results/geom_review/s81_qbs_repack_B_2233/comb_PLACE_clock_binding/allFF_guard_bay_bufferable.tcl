# Candidate allFF guard: run after native target application and at PRE_DETAIL_PLACE.
uplevel #0 {
set af_targets {}
set af_f [open /work/allFF_targets_actualFP.tsv r]
while {[gets $af_f af_l] >=0} {
  lassign [split $af_l "	"] af_n af_m af_x af_y af_o
  dict set af_targets $af_n [list $af_m $af_x $af_y $af_o]
}
close $af_f
if {[dict size $af_targets] !=31847} {error "allFF target cardinality"}
# Protect actual clock nets and their non-sink tree drivers. Data FF D pins must stay bufferable.
set af_clock_ff {}
set af_clock_nets 0
set af_b [ord::get_db_block]
set af_cb [$af_b findBTerm {ck}]
if {$af_cb eq "NULL" || $af_cb eq "" || [$af_cb getIoType] ne "INPUT"} {error "actual scalar clock BTerm ck missing"}
set af_root [$af_cb getNet]
if {$af_root eq "NULL" || $af_root eq ""} {error "actual ck net missing"}
set af_seen_clock {}; set af_clock_todo [list $af_root]
while {[llength $af_clock_todo]} {
 set af_net [lindex $af_clock_todo end]; set af_clock_todo [lrange $af_clock_todo 0 end-1]
 if {[dict exists $af_seen_clock [$af_net getName]]} continue
 dict set af_seen_clock [$af_net getName] 1
 $af_net setDoNotTouch 1
 incr af_clock_nets
 foreach af_t [$af_net getITerms] {
  set af_ci [$af_t getInst]; set af_cm [[$af_ci getMaster] getName]
  set af_cn [string map [list [format %c 92] {}] [$af_ci getName]]
  if {[$af_t isOutputSignal]} {
   if {[dict exists $af_targets $af_cn]} {dict set af_clock_ff $af_cn 1} else {$af_ci setDoNotTouch 1}
   continue
  }
  set af_cp [[$af_t getMTerm] getName]
  if {[regexp {^(BUF|INV|CKBUF|CKINV|HB)} $af_cm] || ([string match ICG* $af_cm] && $af_cp in {CLK CK})} {
   $af_ci setDoNotTouch 1
   foreach af_ot [$af_ci getITerms] {
    if {[$af_ot isOutputSignal] && [$af_ot getNet] ne "NULL"} {lappend af_clock_todo [$af_ot getNet]}
   }
  }
 }
}
if {$af_clock_nets<1} {error "actual clock-net classification missing"}
puts "HIST_CLOCK_PROTECT clock_nets=$af_clock_nets clock_driver_FFs=[dict size $af_clock_ff] data_FFs=[expr {31847-[dict size $af_clock_ff]}]"
set af_hits {}
set af_total 0
foreach af_i [[ord::get_db_block] getInsts] {
  if {[string match DFF* [[$af_i getMaster] getName]]} {incr af_total}
  set af_n [string map [list [format %c 92] {}] [$af_i getName]]
  if {![dict exists $af_targets $af_n]} continue
  if {[dict exists $af_hits $af_n]} {error "allFF duplicate identity $af_n"}
  lassign [dict get $af_targets $af_n] af_m af_x af_y af_o
  lassign [$af_i getLocation] af_ix af_iy
  if {[[$af_i getMaster] getName] ne $af_m || $af_ix !=$af_x || $af_iy !=$af_y || [$af_i getOrient] ne $af_o} {
    error "allFF native target moved/master/orientation changed $af_n"
  }
  $af_i setPlacementStatus FIRM
  if {[dict exists $af_clock_ff $af_n]} {$af_i setDoNotTouch 1} else {$af_i setDoNotTouch 0}
  dict set af_hits $af_n 1
}
if {$af_total !=31847} {error "allFF unexpected register cohort"}
if {[dict size $af_hits] !=31847} {error "allFF identities missing"}
puts "ALLFF guard31847 FIRM/exact-master; data-pin buffering enabled, exact master/location/orientation"
# Keep the reviewed clock-driver bay empty through GPL/DPL. No CTS release is authorized here.
set cb_want {321840 328320 326160 332640}
set cb_found 0
foreach cb [[ord::get_db_block] getBlockages] {
 set q [$cb getBBox]
 if {[list [$q xMin] [$q yMin] [$q xMax] [$q yMax]] eq $cb_want} {incr cb_found}
}
if {$cb_found==0} {lassign $cb_want x0 y0 x1 y1; odb::dbBlockage_create [ord::get_db_block] $x0 $y0 $x1 $y1; set cb_found 1}
if {$cb_found!=1} {error "clock bay blockage cardinality"}
puts "CLOCK_BAY protected exact4.32um reserve through PLACE; no CTS release"

source /work/ff_family_preserve.tcl

}
