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
  $af_i setDoNotTouch 1
  dict set af_hits $af_n 1
}
if {$af_total !=31847} {error "allFF unexpected register cohort"}
if {[dict size $af_hits] !=31847} {error "allFF identities missing"}
puts "ALLFF guard31847 FIRM/dont_touch, exact master/location/orientation"
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

}
